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


async def _reverse_geocode(client: httpx.AsyncClient, lat: float, lng: float) -> str:
    """Convert lat/lng to a human-readable city name."""
    resp = await client.get(
        GEOCODE_BASE,
        params={
            "latlng": f"{lat},{lng}",
            "result_type": "locality",
            "key": GOOGLE_API_KEY,
        },
        timeout=10,
    )
    data = resp.json()
    if data.get("results"):
        return data["results"][0].get("formatted_address", f"{lat:.3f},{lng:.3f}")
    return f"{lat:.3f},{lng:.3f}"


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
        "X-Goog-FieldMask": (
            "routes.duration,routes.distanceMeters,"
            "routes.legs,routes.description"
        ),
    }
    body = {
        "origin":      {"address": origin},
        "destination": {"address": destination},
        "travelMode":  "DRIVE",
    }

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(ROUTES_BASE, json=body, headers=headers, timeout=15)
            resp.raise_for_status()
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
                "origin":       origin,
                "destination":  destination,
                "total_miles":  total_miles,
                "total_hours":  total_hours,
                "summary":      route.get("description", ""),
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
                "origin":      {"address": origin},
                "destination": {"address": destination},
                "travelMode":  "DRIVE",
            }
            route_resp = await client.post(ROUTES_BASE, json=body, headers=headers, timeout=15)
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
        location: City used to bias results geographically (e.g. "Flagstaff, AZ").

    Returns:
        Dict with up to 5 matching places, each with name, rating, address,
        price_level, and a direct Google Maps URL.
    """
    async with httpx.AsyncClient() as client:
        try:
            # Geocode the city for location bias
            loc = await _geocode(client, location)

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

            body: dict = {
                "textQuery":      query,
                "maxResultCount": 5,
                "languageCode":   "en",
            }

            # If we have coordinates, add a location bias so results are near the city
            if loc:
                body["locationBias"] = {
                    "circle": {
                        "center": {"latitude": loc["lat"], "longitude": loc["lng"]},
                        "radius": 30000,   # 30 km bias radius
                    }
                }

            resp = await client.post(
                PLACES_TEXT_BASE, json=body, headers=headers, timeout=15
            )
            resp.raise_for_status()
            data = resp.json()

            if "error" in data:
                return {"error": data["error"].get("message", "Places API error"), "results": []}

            results = []
            for place in data.get("places", []):
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
