import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "mock" / "activities.json"


def load_activities(destination: str, categories: list[str]) -> list[dict]:
    """Load activities for a destination, optionally filtered by category."""
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    items = data.get(destination.strip().lower(), [])
    if categories:
        wanted = {c.lower() for c in categories}
        matches = [a for a in items if a["category"].lower() in wanted]
        if matches:
            return matches
    return items
