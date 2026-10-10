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
    mode: str  # flight, train or bus
    carrier: str
    origin: str
    destination: str
    depart: str  # HH:MM
    arrive: str
    price: float


class TransportPlan(BaseModel):
    outbound: FlightOption
    inbound: FlightOption


class HotelOption(BaseModel):
    name: str
    area: str
    price_per_night: float
    rating: float
    tags: list[str]


class HotelPlan(BaseModel):
    hotel: HotelOption


class Activity(BaseModel):
    name: str
    area: str
    cost: float
    duration_hours: float
    category: str
    time_of_day: str


class ActivityPlan(BaseModel):
    activities: list[Activity]
    