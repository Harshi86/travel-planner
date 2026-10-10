from datetime import date

from pydantic import BaseModel


class TripRequest(BaseModel):
    origin: str
    destination: str
    start: date
    end: date
    budget: float
    travelers: int = 1
    preferences: list[str] = []

    @property
    def nights(self) -> int:
        return (self.end - self.start).days


class FlightOption(BaseModel):
    carrier: str
    price: float
    depart: str
    arrive: str


class HotelOption(BaseModel):
    name: str
    price_per_night: float
    area: str
    rating: float


class Activity(BaseModel):
    name: str
    area: str
    cost: float
    duration_hours: float
    category: str
    time_of_day: str


class ActivityPlan(BaseModel):
    activities: list[Activity]
    