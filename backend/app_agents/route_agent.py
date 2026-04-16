"""
Route Agent
-----------
CLASS CONCEPTS DEMONSTRATED:
  ✅ Tool Calling (code-as-tool) — get_route() and get_midpoint_cities() call the
                                   Google Maps HTTP API directly; calculate_gas_stops()
                                   does deterministic fuel math in pure Python.
  ✅ Hallucination control       — all distances/times come from the API tools,
                                   never from the model's training memory.
  ✅ Prompt Engineering          — strict JSON output schema enforced via system prompt.

This agent receives the structured TripBrief and:
  1. Calls get_route() to get real distance and drive time from Google Maps
  2. Calls get_midpoint_cities() if the trip needs overnight stops
  3. Calls calculate_gas_stops() to figure out fuel logistics
  4. Returns a structured route object for the Orchestrator
"""

from run_agent import Agent
from config import ROUTE_MODEL

ROUTE_SYSTEM_PROMPT = """
You are the Route & Logistics specialist for RoadWise, a road trip planning app.

You will receive a JSON object containing the user's trip details (TripBrief).
Your job is to figure out the driving logistics for the trip.

=== YOUR TASKS ===
1. Call get_route(origin, destination) to get the real distance and drive time.
   Use the exact origin and destination strings from the TripBrief.

2. If total_hours > 6, call get_midpoint_cities(origin, destination, num_stops)
   to find natural overnight stop cities. Use num_stops = ceil(total_hours / 5) - 1.
   Aim for driving legs no longer than 4–5 hours per day.

3. Call calculate_gas_stops(total_miles, mpg, tank_gallons, gas_price_per_gallon)
   using the vehicle data from the TripBrief. This gives the fuel stop plan.

=== OUTPUT FORMAT ===
Return ONLY a valid JSON object — no prose, no explanation, no markdown fences:

{
  "total_miles": <number>,
  "total_drive_hours": <number>,
  "daily_legs": [
    {
      "day": 1,
      "from": "<city>",
      "to": "<city>",
      "miles": <number>,
      "drive_hours": <number>
    }
  ],
  "gas_summary": {
    "num_stops": <number>,
    "stop_every_miles": <number>,
    "total_gallons_needed": <number>,
    "estimated_fuel_cost": <number>,
    "stops_description": "<string>"
  }
}

CRITICAL: Never invent distance or drive time values. Always use the get_route tool.
If a tool returns an error, include the error text in stops_description and use 0 for numbers.
"""


def create_route_agent() -> Agent:
    return Agent(
        name="route_agent",
        description=(
            "Plans the full driving route for a road trip. "
            "Pass the TripBrief JSON as input. "
            "Returns a JSON object with daily_legs, total_miles, total_drive_hours, and gas_summary."
        ),
        model=ROUTE_MODEL,
        prompt=ROUTE_SYSTEM_PROMPT,
        tools=["get_route", "get_midpoint_cities", "calculate_gas_stops"],
        kwargs={},
    )
