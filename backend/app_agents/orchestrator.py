"""
Orchestrator — output parsing helpers
--------------------------------------
The orchestrator agent's CONFIG (name, model, prompt, tools) now lives in
agents.yaml.  This file only contains the Python-side helpers that convert
the orchestrator's final text output into a validated TripPlan object.
"""

import json
import re
from schemas.trip import TripBrief, TripPlan, GasStopResult, DayPlan, Place


def build_trip_plan(orchestrator_text: str, trip_brief: TripBrief) -> TripPlan:
    """
    Parse the orchestrator agent's final JSON text into a validated TripPlan.
    The orchestrator LLM is responsible for merging route + experience data;
    this function only handles JSON extraction and Pydantic validation.
    """
    data = _extract_json(orchestrator_text)

    days = []
    for i, day_data in enumerate(data.get("days", [])):
        days.append(DayPlan(
            day=day_data.get("day") or (i + 1),
            location=day_data.get("location") or "Unknown",
            drive_miles=day_data.get("drive_miles") or 0,
            drive_hours=day_data.get("drive_hours") or 0,
            lodging=_parse_place(day_data.get("lodging")),
            activities=[p for p in (_parse_place(a) for a in (day_data.get("activities") or [])) if p],
            restaurants=[p for p in (_parse_place(r) for r in (day_data.get("restaurants") or [])) if p],
            gas_stop=day_data.get("gas_stop"),
            weather_note=day_data.get("weather_note"),
        ))

    gas_raw = data.get("gas_summary") or {}
    gas_summary = GasStopResult(
        total_miles=data.get("total_miles") or 0,
        num_stops=gas_raw.get("num_stops") or 0,
        stop_every_miles=gas_raw.get("stop_every_miles") or 0,
        total_gallons_needed=gas_raw.get("total_gallons_needed") or 0,
        estimated_fuel_cost=gas_raw.get("estimated_fuel_cost") or 0,
        stops_description=gas_raw.get("stops_description") or "",
    )

    return TripPlan(
        origin=data.get("origin") or trip_brief.origin,
        destination=data.get("destination") or trip_brief.destination,
        total_miles=data.get("total_miles") or 0,
        total_drive_hours=data.get("total_drive_hours") or 0,
        travel_dates=data.get("travel_dates") or trip_brief.travel_dates,
        gas_summary=gas_summary,
        days=days,
        tips=data.get("tips") or [],
    )


def _parse_place(raw) -> Place | None:
    """Convert a dict or string from agent output into a Place object."""
    if not raw:
        return None
    if isinstance(raw, str):
        return Place(name=raw) if raw.strip() else None
    if isinstance(raw, dict):
        name = raw.get("name") or ""
        if not name:
            return None
        return Place(
            name=name,
            rating=raw.get("rating"),
            address=raw.get("address"),
            price_level=raw.get("price_level"),
            maps_url=raw.get("maps_url") or (
                f"https://www.google.com/maps/search/?api=1&query={name.replace(' ', '+')}"
                if name else None
            ),
        )
    return None


def _extract_json(text: str) -> dict:
    """Extract the first JSON object found in a string."""
    try:
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            return json.loads(match.group())
    except (json.JSONDecodeError, AttributeError):
        pass
    return {}
