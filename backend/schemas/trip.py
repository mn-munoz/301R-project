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
    gas_price_estimate: float = 3.75


class GasStopResult(BaseModel):
    total_miles: float = 0.0
    num_stops: int = 0
    stop_every_miles: float = 0.0
    total_gallons_needed: float = 0.0
    estimated_fuel_cost: float = 0.0
    stops_description: str = ""


class Place(BaseModel):
    """A real, named place returned by the Google Maps Places API."""
    name: str
    rating: Optional[float] = None      # 1.0 – 5.0
    address: Optional[str] = None       # formatted street address
    price_level: Optional[str] = None   # "$" | "$$" | "$$$" | "$$$$"
    maps_url: Optional[str] = None      # deep-link to Google Maps


class DayPlan(BaseModel):
    day: int
    location: str
    drive_miles: float = 0.0
    drive_hours: float = 0.0
    lodging: Optional[Place] = None
    activities: list[Place] = Field(default_factory=list)
    restaurants: list[Place] = Field(default_factory=list)
    gas_stop: Optional[str] = None
    weather_note: Optional[str] = None


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
    role: str
    content: str


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    trip_plan: Optional[TripPlan] = None
    phase: str = "intake"
