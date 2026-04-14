"""
Orchestrator
------------
CLASS CONCEPTS DEMONSTRATED:
  ✅ Multiple Agents (agent-as-tool pattern) — Route Agent and Experience Agent are
     invoked as sub-agents by the Orchestrator, each with a focused responsibility.

The Orchestrator receives the completed TripBrief and coordinates:
  1. Route Agent  → driving legs + gas plan
  2. Experience Agent → lodging + activities + food
  3. Assembles both results into the final TripPlan JSON
"""

import json
import re
from agents import Agent, Runner
from config import ORCHESTRATOR_MODEL
from schemas.trip import TripBrief, TripPlan, GasStopResult, DayPlan


ORCHESTRATOR_SYSTEM_PROMPT = """
You are the Orchestrator for RoadWise, a road trip planning app.

You will receive a TripBrief JSON. Your job is to coordinate two specialist agents
and assemble their outputs into a final unified trip plan.

Step 1: Call the route_agent tool with the full TripBrief JSON as input.
        It will return route details (daily legs, total miles, gas summary).

Step 2: Call the experience_agent tool with both the TripBrief JSON AND the
        route output from Step 1 as input.
        It will return a day-by-day itinerary with lodging, activities, and food.

Step 3: Merge the results and return a single JSON object in this structure:

{
  "origin": "<string>",
  "destination": "<string>",
  "total_miles": <number>,
  "total_drive_hours": <number>,
  "travel_dates": "<string>",
  "gas_summary": { ...from route agent... },
  "days": [ ...merged from route agent legs + experience agent days... ],
  "tips": [ ...from experience agent... ]
}

Each day object in "days" must include ALL of these fields:
  day, location, drive_miles, drive_hours, lodging, activities, restaurants,
  gas_stop, weather_note

Return ONLY the final JSON. No prose, no explanation.
"""


async def run_orchestrator(
    trip_brief: TripBrief,
    route_agent: Agent,
    experience_agent: Agent,
) -> TripPlan:
    """
    Runs the full planning pipeline:
      TripBrief → Route Agent → Experience Agent → TripPlan
    """
    brief_json = trip_brief.model_dump_json(indent=2)

    # ── Step 1: Route Agent ──────────────────────────────────────────────────
    route_result = await Runner.run(
        route_agent,
        input=f"Plan the route for this trip:\n{brief_json}",
    )
    route_text = route_result.final_output

    # ── Step 2: Experience Agent ─────────────────────────────────────────────
    experience_input = (
        f"Trip brief:\n{brief_json}\n\n"
        f"Route plan:\n{route_text}\n\n"
        f"Build the day-by-day itinerary."
    )
    experience_result = await Runner.run(
        experience_agent,
        input=experience_input,
    )
    experience_text = experience_result.final_output

    # ── Step 3: Merge into TripPlan ──────────────────────────────────────────
    # Parse route output
    route_data = _extract_json(route_text)
    exp_data = _extract_json(experience_text)

    # Build merged day plans
    days = []
    route_legs = route_data.get("daily_legs", [])
    exp_days = exp_data.get("days", [])

    for i, leg in enumerate(route_legs):
        exp_day = exp_days[i] if i < len(exp_days) else {}
        days.append(DayPlan(
            day=leg.get("day") or (i + 1),
            location=leg.get("to") or exp_day.get("location") or "Unknown",
            drive_miles=leg.get("miles") or 0,
            drive_hours=leg.get("drive_hours") or 0,
            lodging=exp_day.get("lodging"),
            activities=exp_day.get("activities") or [],
            restaurants=exp_day.get("restaurants") or [],
            gas_stop=exp_day.get("gas_stop"),
        ))

    gas_raw = route_data.get("gas_summary") or {}
    gas_summary = GasStopResult(
        total_miles=route_data.get("total_miles") or 0,
        num_stops=gas_raw.get("num_stops") or 0,
        stop_every_miles=gas_raw.get("stop_every_miles") or 0,
        total_gallons_needed=gas_raw.get("total_gallons_needed") or 0,
        estimated_fuel_cost=gas_raw.get("estimated_fuel_cost") or 0,
        stops_description=gas_raw.get("stops_description") or "",
    )

    return TripPlan(
        origin=trip_brief.origin,
        destination=trip_brief.destination,
        total_miles=route_data.get("total_miles") or 0,
        total_drive_hours=route_data.get("total_drive_hours") or 0,
        travel_dates=trip_brief.travel_dates,
        gas_summary=gas_summary,
        days=days,
        tips=exp_data.get("tips") or [],
    )


def _extract_json(text: str) -> dict:
    """Extract the first JSON object found in a string."""
    try:
        # Try to find a JSON block
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            return json.loads(match.group())
    except (json.JSONDecodeError, AttributeError):
        pass
    return {}
