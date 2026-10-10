import json
from pathlib import Path

MOCK_DIR = Path(__file__).resolve().parents[2] / "data" / "mock"


def _load(filename: str) -> dict:
    return json.loads((MOCK_DIR / filename).read_text(encoding="utf-8"))


def load_activities(destination: str, categories: list[str]) -> list[dict]:
    """Load activities for a destination, optionally filtered by category."""
    items = _load("activities.json").get(destination.strip().lower(), [])
    if categories:
        wanted = {c.lower() for c in categories}
        matches = [a for a in items if a["category"].lower() in wanted]
        if matches:
            return matches
    return items


def load_flights(origin: str, destination: str) -> list[dict]:
    """Load transport options (flight, train, bus) for one direction."""
    key = f"{origin.strip().lower()}-{destination.strip().lower()}"
    return _load("flights.json").get(key, [])


def load_hotels(destination: str) -> list[dict]:
    """Load hotels for a destination."""
    return _load("hotels.json").get(destination.strip().lower(), [])

def available_destinations(origin: str = "Bengaluru") -> list[str]:
    """Destinations that have activities, hotels and transport both ways."""
    o = origin.strip().lower()
    flights = _load("flights.json")
    both = set(_load("activities.json")) & set(_load("hotels.json"))
    return sorted(
        d.title() for d in both if f"{o}-{d}" in flights and f"{d}-{o}" in flights
    )
