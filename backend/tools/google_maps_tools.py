"""
Google Maps Tools — code-as-tool via Google Maps Platform (New APIs)
---------------------------------------------------------------------
Uses:
  - Routes API           → get_route(), get_midpoint_cities()
  - Places API (New)     → search_places()
  - Geocoding API        → lat/lng lookups used internally

CLASS CONCEPTS: Tool Calling (code-as-tool) + Hallucination Control
  - All route data comes from the API, never invented by the model.
  - All place recommendations come from search_places() results only.
"""

import re
import httpx
from config import GOOGLE_API_KEY

ROUTES_BASE      = "https://routes.googleapis.com/directions/v2:computeRoutes"
PLACES_TEXT_BASE = "https://places.googleapis.com/v1/places:searchText"
GEOCODE_BASE     = "https://maps.googleapis.com/maps/api/geocode/json"

# Price level mapping from the Places API enum to human-readable symbols
PRICE_SYMBOLS = {
    "PRICE_LEVEL_FREE":             "Free",
    "PRICE_LEVEL_INEXPENSIVE":      "$",
    "PRICE_LEVEL_MODERATE":         "$$",
    "PRICE_LEVEL_EXPENSIVE":        "$$$",
    "PRICE_LEVEL_VERY_EXPENSIVE":   "$$$$",
}


# ── Internal helper ──────────────────────────────────────────────────────────

async def _geocode(client: httpx.AsyncClient, address: str) -> dict | None:
    """Convert an address string to {lat, lng}. Returns None on failure."""
    resp = await client.get(
        GEOCODE_BASE,
        params={"address": address, "key": GOOGLE_API_KEY},
        timeout=10,
    )
    data = resp.json()
    if data.get("status") == "OK":
        loc = data["results"][0]["geometry"]["location"]
        return {"lat": loc["lat"], "lng": loc["lng"]}
    return None


def _extract_city_state(components: list) -> str:
    """Pull a clean 'City, ST' string out of Geocoding API address_components."""
    name = state = ""
    for comp in components:
        types = comp.get("types", [])
        # Accept the most specific place name available
        if not name and any(t in types for t in (
            "locality", "administrative_area_level_3", "administrative_area_level_2"
        )):
            name = comp["short_name"]
        if not state and "administrative_area_level_1" in types:
            state = comp["short_name"]
    if name and state:
        return f"{name}, {state}"
    return name  # may be empty string


async def _reverse_geocode(client: httpx.AsyncClient, lat: float, lng: float) -> str:
    """
    Convert lat/lng to a human-readable 'City, ST' string.

    Never returns raw coordinates — always finds a named place.
    Strategy:
      1. Try Geocoding API with locality (proper city)
      2. Try Geocoding API with county/level-2 (rural areas)
      3. Try unrestricted reverse geocode and scan all components
      4. Use Places text search to find nearest city (handles ocean coordinates)
      5. Last resort: 'Intermediate Stop'
    """
    # ── Steps 1 & 2: filtered result_type lookups ───────────────────────────
    for result_type in ("locality", "administrative_area_level_2"):
        resp = await client.get(
            GEOCODE_BASE,
            params={"latlng": f"{lat},{lng}", "result_type": result_type,
                    "key": GOOGLE_API_KEY},
            timeout=10,
        )
        results = resp.json().get("results", [])
        if not results:
            continue
        city_state = _extract_city_state(results[0].get("address_components", []))
        if city_state:
            return city_state

    # ── Step 3: unrestricted reverse geocode — scan multiple results ─────────
    resp = await client.get(
        GEOCODE_BASE,
        params={"latlng": f"{lat},{lng}", "key": GOOGLE_API_KEY},
        timeout=10,
    )
    for result in resp.json().get("results", [])[:5]:
        city_state = _extract_city_state(result.get("address_components", []))
        if city_state:
            return city_state

    # ── Step 4: Places text search — nearest city within 500 km ─────────────
    # This handles coordinates over water (Gulf of Mexico, etc.) where the
    # Geocoding API returns nothing.
    try:
        nearby = await client.post(
            PLACES_TEXT_BASE,
            json={
                "textQuery":      "city",
                "maxResultCount": 1,
                "locationBias": {
                    "circle": {
                        "center": {"latitude": lat, "longitude": lng},
                        "radius": 500_000,   # 500 km — wide enough to reach land from the Gulf
                    }
                },
            },
            headers={
                "Content-Type":    "application/json",
                "X-Goog-Api-Key":  GOOGLE_API_KEY,
                "X-Goog-FieldMask": "places.displayName,places.addressComponents",
            },
            timeout=10,
        )
        places = nearby.json().get("places", [])
        if places:
            # addressComponents uses camelCase keys in Places API (New)
            comps = [
                {"short_name": c.get("shortText", ""), "types": c.get("types", [])}
                for c in places[0].get("addressComponents", [])
            ]
            city_state = _extract_city_state(comps)
            if city_state:
                print(f"[_reverse_geocode] Ocean fallback: ({lat:.3f},{lng:.3f}) → {city_state}")
                return city_state
            display = places[0].get("displayName", {}).get("text", "")
            if display:
                return display
    except Exception as exc:
        print(f"[_reverse_geocode] Places fallback failed: {exc}")

    # ── Step 5: absolute last resort ─────────────────────────────────────────
    print(f"[_reverse_geocode] All lookups failed for ({lat:.3f},{lng:.3f}), using generic name")
    return "Intermediate Stop"


_COORD_RE = re.compile(r"^(-?\d+\.?\d*),\s*(-?\d+\.?\d*)$")


def _build_waypoint(location: str) -> dict:
    """
    Build a Routes API waypoint from either an address string or a 'lat,lng' string.
    The Routes API rejects raw 'lat,lng' strings in the `address` field — they must
    be passed as location.latLng objects instead.
    """
    m = _COORD_RE.match(location.strip())
    if m:
        return {
            "location": {
                "latLng": {
                    "latitude":  float(m.group(1)),
                    "longitude": float(m.group(2)),
                }
            }
        }
    return {"address": location}


# ── Public tools ─────────────────────────────────────────────────────────────

async def get_route(origin: str, destination: str) -> dict:
    """
    Get driving route details between two locations using the Google Maps Routes API.

    Args:
        origin: Starting location (e.g. "Provo, UT")
        destination: Ending location (e.g. "Las Vegas, NV")

    Returns:
        Dict with total_miles, total_hours, origin, destination, and summary.
    """
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_API_KEY,
        "X-Goog-FieldMask": "routes.duration,routes.distanceMeters",
    }
    body = {
        "origin":      _build_waypoint(origin),
        "destination": _build_waypoint(destination),
        "travelMode":  "DRIVE",
    }

    async with httpx.AsyncClient() as client:
        try:
            print(f"[get_route] Sending request: origin={origin!r}, destination={destination!r}")
            print(f"[get_route] API key present: {bool(GOOGLE_API_KEY)}, key prefix: {GOOGLE_API_KEY[:8] if GOOGLE_API_KEY else 'MISSING'}")
            resp = await client.post(ROUTES_BASE, json=body, headers=headers, timeout=15)
            if not resp.is_success:
                error_body = resp.text
                print(f"[get_route] Routes API {resp.status_code} error body: {error_body}")
                return {"error": f"Routes API {resp.status_code}: {error_body}"}
            data = resp.json()

            if not data.get("routes"):
                return {"error": f"Routes API returned no routes. Response: {data}"}

            route = data["routes"][0]
            total_meters  = route.get("distanceMeters", 0)
            duration_str  = route.get("duration", "0s")          # e.g. "12345s"
            total_seconds = int(duration_str.rstrip("s")) if duration_str else 0
            total_miles   = round(total_meters / 1609.34, 1)
            total_hours   = round(total_seconds / 3600, 2)

            return {
                "origin":      origin,
                "destination": destination,
                "total_miles": total_miles,
                "total_hours": total_hours,
            }

        except Exception as e:
            return {"error": str(e)}


async def get_midpoint_cities(origin: str, destination: str, num_stops: int = 1) -> dict:
    """
    Find good overnight stop cities evenly spaced along a long driving route.

    Args:
        origin: Starting city (e.g. "Salt Lake City, UT")
        destination: Ending city (e.g. "Los Angeles, CA")
        num_stops: Number of overnight stops needed (e.g. 1 for a 2-day trip)

    Returns:
        Dict with total_miles, total_hours, and suggested_stops list.
    """
    async with httpx.AsyncClient() as client:
        try:
            origin_loc = await _geocode(client, origin)
            dest_loc   = await _geocode(client, destination)

            if not origin_loc or not dest_loc:
                return {"error": "Could not geocode origin or destination."}

            # Get total route stats via Routes API directly
            headers = {
                "Content-Type": "application/json",
                "X-Goog-Api-Key": GOOGLE_API_KEY,
                "X-Goog-FieldMask": "routes.duration,routes.distanceMeters",
            }
            body = {
                "origin":      _build_waypoint(origin),
                "destination": _build_waypoint(destination),
                "travelMode":  "DRIVE",
            }
            route_resp = await client.post(ROUTES_BASE, json=body, headers=headers, timeout=15)
            if not route_resp.is_success:
                error_body = route_resp.text
                print(f"[get_midpoint_cities] Routes API {route_resp.status_code} error body: {error_body}")
                return {"error": f"Routes API {route_resp.status_code}: {error_body}"}
            route_data = route_resp.json()
            total_miles = 0.0
            total_hours = 0.0
            if route_data.get("routes"):
                r = route_data["routes"][0]
                total_miles = round(r.get("distanceMeters", 0) / 1609.34, 1)
                dur = r.get("duration", "0s")
                total_hours = round(int(dur.rstrip("s")) / 3600, 2)

            # Compute evenly-spaced intermediate lat/lng points
            stops = []
            for i in range(1, num_stops + 1):
                fraction = i / (num_stops + 1)
                mid_lat  = origin_loc["lat"] + fraction * (dest_loc["lat"] - origin_loc["lat"])
                mid_lng  = origin_loc["lng"] + fraction * (dest_loc["lng"] - origin_loc["lng"])
                city     = await _reverse_geocode(client, mid_lat, mid_lng)
                stops.append({
                    "stop_number":            i,
                    "city":                   city,
                    "approx_miles_from_start": round(total_miles * fraction, 1),
                    "approx_hours_from_start": round(total_hours * fraction, 2),
                })

            return {
                "origin":          origin,
                "destination":     destination,
                "total_miles":     total_miles,
                "total_hours":     total_hours,
                "suggested_stops": stops,
            }

        except Exception as e:
            return {"error": str(e)}


async def search_places(query: str, location: str) -> dict:
    """
    Search for places (hotels, restaurants, attractions) near a city using
    the Google Maps Places API Text Search.

    Args:
        query: What to search for, including location context.
               Examples:
                 "budget hotel in Flagstaff AZ"
                 "best hiking trails near Sedona AZ"
                 "highly rated Mexican restaurant in Albuquerque NM"
                 "things to do in Santa Fe NM"
        location: City used to restrict results geographically (e.g. "Flagstaff, AZ").

    Returns:
        Dict with up to 5 matching places, each with name, rating, address,
        price_level, and a direct Google Maps URL.
    """
    async with httpx.AsyncClient() as client:
        try:
            # Geocode the city to enforce a hard geographic boundary.
            # If geocoding fails, we fall back to a locationBias (soft hint) so
            # we still get some results — better than returning an error which
            # causes the LLM to hallucinate place descriptions.
            loc = await _geocode(client, location)
            if not loc:
                print(f"[search_places] Geocoding failed for: {location!r} — falling back to text-only search")

            headers = {
                "Content-Type": "application/json",
                "X-Goog-Api-Key": GOOGLE_API_KEY,
                "X-Goog-FieldMask": (
                    "places.displayName,"
                    "places.rating,"
                    "places.formattedAddress,"
                    "places.priceLevel,"
                    "places.googleMapsUri,"
                    "places.editorialSummary"
                ),
            }

            # Build the search radius list.
            # If geocoding succeeded: try 50 km (tight), then 100 km (wide) with a hard boundary.
            # If geocoding failed: make one unrestricted text search — the city name in the
            # query still provides location context, and it's better than returning no results.
            raw_places: list = []
            radius_list = [50_000, 100_000] if loc else [None]

            for radius_m in radius_list:
                body: dict = {
                    "textQuery":      query,
                    "maxResultCount": 5,
                    "languageCode":   "en",
                }
                if loc and radius_m:
                    # Hard geographic boundary — never returns results outside this circle.
                    body["locationRestriction"] = {
                        "circle": {
                            "center": {
                                "latitude":  loc["lat"],
                                "longitude": loc["lng"],
                            },
                            "radius": radius_m,
                        }
                    }

                resp = await client.post(
                    PLACES_TEXT_BASE, json=body, headers=headers, timeout=15
                )
                if not resp.is_success:
                    print(f"[search_places] Places API {resp.status_code}: {resp.text}")
                    return {"results": [], "count": 0, "location": location, "query": query}
                data = resp.json()

                if "error" in data:
                    print(f"[search_places] Places API error: {data['error']}")
                    return {"results": [], "count": 0, "location": location, "query": query}

                raw_places = data.get("places", [])
                if raw_places:
                    break   # found results at this radius — no need to widen further

            results = []
            for place in raw_places:
                price_raw = place.get("priceLevel", "")
                results.append({
                    "name":        place.get("displayName", {}).get("text", "Unknown"),
                    "rating":      place.get("rating"),
                    "address":     place.get("formattedAddress"),
                    "price_level": PRICE_SYMBOLS.get(price_raw),
                    "maps_url":    place.get("googleMapsUri"),
                    "description": place.get("editorialSummary", {}).get("text"),
                })

            return {
                "location": location,
                "query":    query,
                "results":  results,
                "count":    len(results),
            }

        except Exception as e:
            return {"error": str(e), "results": []}
