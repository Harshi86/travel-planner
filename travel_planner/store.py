import json
import sqlite3
from contextlib import closing
from pathlib import Path

from travel_planner.schemas import ActivityPlan, HotelPlan, TransportPlan, TripRequest

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "trips.db"


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS trips (
            trip_id TEXT PRIMARY KEY,
            state TEXT NOT NULL,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    return conn


def save_trip(trip_id: str, state: dict) -> None:
    data = {
        "request": state["request"].model_dump(mode="json"),
        "budgets": state["budgets"],
        "transport": state["transport"].model_dump(mode="json"),
        "hotel": state["hotel"].model_dump(mode="json"),
        "activities": state["activities"].model_dump(mode="json"),
        "attempts": state.get("attempts", 1),
        "feedback": state.get("feedback") or {},
    }
    with closing(_connect()) as conn, conn:
        conn.execute(
            """
            INSERT INTO trips (trip_id, state, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(trip_id) DO UPDATE SET
                state = excluded.state,
                updated_at = CURRENT_TIMESTAMP
            """,
            (trip_id, json.dumps(data)),
        )


def load_trip(trip_id: str) -> dict | None:
    with closing(_connect()) as conn:
        row = conn.execute(
            "SELECT state FROM trips WHERE trip_id = ?", (trip_id,)
        ).fetchone()
    if row is None:
        return None
    data = json.loads(row[0])
    return {
        "request": TripRequest.model_validate(data["request"]),
        "budgets": data["budgets"],
        "transport": TransportPlan.model_validate(data["transport"]),
        "hotel": HotelPlan.model_validate(data["hotel"]),
        "activities": ActivityPlan.model_validate(data["activities"]),
        "attempts": data["attempts"],
        "feedback": data["feedback"],
    }