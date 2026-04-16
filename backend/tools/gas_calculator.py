"""
Gas Stop Calculator — code-as-tool
-----------------------------------
Given trip distance, vehicle MPG, and tank size, this tool calculates
how many gas stops are needed, how often to stop, and estimated fuel cost.

This is a pure-Python "code-as-tool" — the agent calls it like a function,
gets back a structured result, and uses that data in its response.
No hallucination possible here: the math is deterministic.
"""

import math


def calculate_gas_stops(
    total_miles: float,
    mpg: float,
    tank_gallons: float,
    gas_price_per_gallon: float = 3.75,
) -> dict:
    """
    Calculate gas stops required for a road trip.

    Args:
        total_miles: Total trip distance in miles.
        mpg: Vehicle miles per gallon (fuel efficiency).
        tank_gallons: Total tank capacity in gallons.
        gas_price_per_gallon: Current gas price estimate (default $3.75).

    Returns:
        A dict with num_stops, stop_every_miles, total_gallons, estimated cost,
        and a human-readable description.
    """
    # Use 80% of tank capacity as the effective range — always stop before empty
    safe_range = mpg * tank_gallons * 0.80

    # How many times do we need to refuel? (subtract 1 because we start full)
    num_stops = max(0, math.ceil(total_miles / safe_range) - 1)

    total_gallons = total_miles / mpg
    estimated_cost = round(total_gallons * gas_price_per_gallon, 2)
    stop_every = round(safe_range, 1)

    if num_stops == 0:
        description = (
            f"Great news — you can make the full {total_miles:.0f}-mile trip on one tank! "
            f"Estimated fuel cost: ${estimated_cost:.2f}."
        )
    else:
        description = (
            f"Plan for {num_stops} gas stop(s) roughly every {stop_every} miles. "
            f"Total fuel needed: ~{total_gallons:.1f} gallons. "
            f"Estimated fuel cost at ${gas_price_per_gallon}/gal: ${estimated_cost:.2f}."
        )

    return {
        "total_miles": total_miles,
        "num_stops": num_stops,
        "stop_every_miles": stop_every,
        "total_gallons_needed": round(total_gallons, 1),
        "estimated_fuel_cost": estimated_cost,
        "stops_description": description,
    }
