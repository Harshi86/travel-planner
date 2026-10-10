from agents import Agent, function_tool

from travel_planner.llm import get_model
from travel_planner.schemas import ActivityPlan
from travel_planner.tools.mock_data import load_activities


@function_tool
def search_activities(destination: str, categories: list[str]) -> list[dict]:
    """Search the activity database for a destination.

    Args:
        destination: Destination name, for example "Goa".
        categories: Categories to include. Allowed values: beach, food, culture,
            nature, adventure, nightlife, shopping. Pass an empty list for all.
    """
    return load_activities(destination, categories)


activity_agent = Agent(
    name="Activity Agent",
    model=get_model(),
    instructions=(
        "You plan activities for a trip. Always call search_activities first and "
        "choose ONLY from the activities it returns. Rules: the total cost of the "
        "chosen activities must not exceed the activity budget you are given; "
        "match the traveler's preferences; respect constraints such as 'no early "
        "mornings' by avoiding activities with time_of_day 'early_morning'; "
        "choose at most 3 activities per day of the trip. Return the chosen "
        "activities exactly as they appear in the search results."
    ),
    tools=[search_activities],
    output_type=ActivityPlan,
)
