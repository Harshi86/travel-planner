from agents import Agent, function_tool

from travel_planner.llm import get_model
from travel_planner.schemas import HotelPlan
from travel_planner.tools.mock_data import load_hotels


@function_tool
def search_hotels(destination: str) -> list[dict]:
    """Search hotels for a destination.

    Args:
        destination: Destination name, for example "Goa".
    """
    return load_hotels(destination)


hotel_agent = Agent(
    name="Hotel Agent",
    model=get_model(),
    instructions=(
        "You choose ONE hotel. Call search_hotels first and choose ONLY from "
        "the hotels returned. Rules: the hotel's price_per_night must not exceed "
        "the maximum nightly price you are given; among hotels within that "
        "limit, pick the one whose tags best match the traveler's preferences, "
        "using rating to break ties. Return the chosen hotel exactly as it "
        "appears in the search results."
    ),
    tools=[search_hotels],
    output_type=HotelPlan,
)
