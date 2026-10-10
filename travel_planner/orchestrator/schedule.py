from travel_planner.schemas import Activity

SLOT_ORDER = {"early_morning": 0, "morning": 1, "afternoon": 2, "evening": 3, "night": 4}


def _slot(activity: Activity) -> int:
    return SLOT_ORDER.get(activity.time_of_day, 5)


def schedule_by_day(activities: list[Activity], days: int) -> list[list[Activity]]:
    """Spread activities over the days, grouped by area, ordered by time of day."""
    if not activities:
        return []
    ordered = sorted(activities, key=lambda a: (a.area, _slot(a)))
    per_day = -(-len(ordered) // max(days, 1))  # ceiling division
    chunks = [ordered[i:i + per_day] for i in range(0, len(ordered), per_day)]
    return [sorted(chunk, key=_slot) for chunk in chunks]
