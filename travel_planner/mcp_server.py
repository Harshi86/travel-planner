import uuid
from datetime import date, timedelta

from mcp.server.fastmcp import FastMCP

from travel_planner.main import run
from travel_planner.schemas import TripRequest

mcp = FastMCP("travel-planner", stateless_http=True)

# Saved trips (lost when the server restarts; we can add a database later)
TRIPS: dict[str, dict] = {}


def _totals(state: dict) -> tuple[float, float, float]:
    req = state["request"]
    transport = state["transport"]
    hotel = state["hotel"].hotel
    acts = state["activities"].activities
    transport_total = transport.outbound.price + transport.inbound.price
    hotel_total = hotel.price_per_night * req.nights
    activity_total = sum(a.cost for a in acts)
    return transport_total, hotel_total, activity_total


def _short_summary(trip_id: str, state: dict) -> str:
    req = state["request"]
    hotel = state["hotel"].hotel
    acts = state["activities"].activities
    t, h, a = _totals(state)
    total = t + h + a
    text = (
        f"Your {req.nights}-night {req.destination} trip costs {total:,.0f} rupees "
        f"out of your {req.budget:,.0f} budget. "
        f"You will stay at {hotel.name} and do {len(acts)} activities. "
        f"Your trip ID is {trip_id}."
    )
    if state["feedback"]:
        text += " Warning: some problems could not be fixed. Ask me to check the budget for details."
    return text


async def _run_and_save(request: TripRequest, trip_id: str | None = None) -> str:
    try:
        state = await run(request)
    except Exception as e:
        return f"Sorry, I could not plan the trip right now: {e}"
    trip_id = trip_id or uuid.uuid4().hex[:8]
    TRIPS[trip_id] = state
    return _short_summary(trip_id, state)


@mcp.tool()
async def plan_trip(
    destination: str,
    nights: int,
    budget: float,
    start_date: str = "",
    origin: str = "Bengaluru",
    travelers: int = 1,
    preferences: list[str] | None = None,
) -> str:
    """Plan a trip within a budget in rupees. Destinations with data: Goa, Jaipur, Kochi.
    start_date is optional, in YYYY-MM-DD format. Returns a short summary and a trip ID."""
    if nights < 1:
        return "A trip needs at least one night."
    start = date.fromisoformat(start_date) if start_date else date.today() + timedelta(days=14)
    request = TripRequest(
        origin=origin,
        destination=destination,
        start=start,
        end=start + timedelta(days=nights),
        budget=budget,
        travelers=travelers,
        preferences=preferences or [],
    )
    return await _run_and_save(request)


@mcp.tool()
def get_trip_details(trip_id: str) -> str:
    """Get the full details of a planned trip: transport, hotel and activities."""
    state = TRIPS.get(trip_id)
    if not state:
        return f"I could not find a trip with ID {trip_id}."
    req = state["request"]
    transport = state["transport"]
    hotel = state["hotel"].hotel
    acts = state["activities"].activities

    lines = [f"Trip to {req.destination}, {req.nights} nights."]
    for leg in (transport.outbound, transport.inbound):
        lines.append(
            f"{leg.origin} to {leg.destination} by {leg.mode} with {leg.carrier}, "
            f"{leg.depart} to {leg.arrive}, {leg.price:,.0f} rupees."
        )
    lines.append(
        f"Hotel: {hotel.name} in {hotel.area}, {hotel.price_per_night:,.0f} rupees a night."
    )
    for a in acts:
        lines.append(f"Activity: {a.name} ({a.time_of_day}), {a.cost:,.0f} rupees.")
    return "\n".join(lines)


@mcp.tool()
def check_budget(trip_id: str) -> str:
    """Check a planned trip against its budget and list any unresolved problems."""
    state = TRIPS.get(trip_id)
    if not state:
        return f"I could not find a trip with ID {trip_id}."
    req, b = state["request"], state["budgets"]
    t, h, a = _totals(state)
    total = t + h + a
    status = "within" if total <= req.budget else "over"
    lines = [
        f"Total {total:,.0f} rupees, {status} your budget of {req.budget:,.0f}.",
        f"Transport {t:,.0f} of {b['transport']:,.0f}.",
        f"Stay {h:,.0f} of {b['stay']:,.0f}.",
        f"Activities {a:,.0f} of {b['activities']:,.0f}.",
    ]
    if state["feedback"]:
        lines.append("Unresolved problems:")
        for agent, msg in state["feedback"].items():
            lines.append(f"{agent}: {msg}")
    return "\n".join(lines)


@mcp.tool()
async def adjust_trip(
    trip_id: str,
    new_budget: float = 0,
    extra_preferences: list[str] | None = None,
) -> str:
    """Change a planned trip's budget in rupees or add preferences, then plan it again."""
    state = TRIPS.get(trip_id)
    if not state:
        return f"I could not find a trip with ID {trip_id}."
    old = state["request"]
    request = old.model_copy(
        update={
            "budget": new_budget or old.budget,
            "preferences": old.preferences + (extra_preferences or []),
        }
    )
    return await _run_and_save(request, trip_id)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
    