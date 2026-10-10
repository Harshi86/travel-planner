from travel_planner.schemas import TripRequest

SPLIT = {"transport": 0.35, "stay": 0.40, "activities": 0.25}


def split_budget(request: TripRequest) -> dict[str, float]:
    """Split the total budget across categories. Plain code, no LLM."""
    budgets = {name: request.budget * share for name, share in SPLIT.items()}
    budgets["max_nightly"] = budgets["stay"] / max(request.nights, 1)
    return budgets
