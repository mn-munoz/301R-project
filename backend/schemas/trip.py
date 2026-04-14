from pydantic import BaseModel, Field
from typing import Optional


class VehicleInfo(BaseModel):
    make: str
    model: str
    year: Optional[int] = None
    mpg: float
    tank_gallons: float


class TripBrief(BaseModel):
    """Structured data collected by the Intake Agent."""
    origin: str
    destination: str
    travel_dates: str
    num_travelers: int
    budget: str                     # e.g. "budget", "moderate", "luxury"
    interests: list[str]            # e.g. ["hiking", "local food", "history"]
    vehicle: VehicleInfo
    gas_price_estimate: float = 3.75  # dollars per gallon, user can override


class GasStopResult(BaseModel):
    total_miles: float = 0.0
    num_stops: int = 0
    stop_every_miles: float = 0.0
    total_gallons_needed: float = 0.0
    estimated_fuel_cost: float = 0.0
    stops_description: str = ""


class DayPlan(BaseModel):
    day: int
    location: str
    drive_miles: float = 0.0
    drive_hours: float = 0.0
    lodging: Optional[str] = None
    activities: list[str] = Field(default_factory=list)
    restaurants: list[str] = Field(default_factory=list)
    gas_stop: Optional[str] = None  # city/town name if a gas stop is needed


class TripPlan(BaseModel):
    """Final assembled plan returned to the user."""
    origin: str
    destination: str
    total_miles: float
    total_drive_hours: float
    travel_dates: str
    gas_summary: GasStopResult
    days: list[DayPlan]
    tips: list[str] = Field(default_factory=list)


class ChatMessage(BaseModel):
    role: str   # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    trip_plan: Optional[TripPlan] = None   # populated once planning is complete
    phase: str = "intake"                  # "intake" | "planning" | "done"
