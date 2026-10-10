from agents import Agent, function_tool

from travel_planner.llm import get_model
from travel_planner.schemas import TransportPlan
from travel_planner.tools.mock_data import load_flights


@function_tool
def search_transport(origin: str, destination: str) -> list[dict]:
    """Search flight, train and bus options for ONE direction of travel.

    Args:
        origin: Departure city, for example "Bengaluru".
        destination: Arrival city, for example "Goa".
    """
    return load_flights(origin, destination)


flight_agent = Agent(
    name="Flight Agent",
    model=get_model(),
    instructions=(
        "You choose round-trip transport. Call search_transport once for the "
        "outbound direction and once for the return direction, and choose ONLY "
        "from the options returned. Rules: the combined price of the outbound "
        "and return options must not exceed the transport budget you are given; "
        "if the traveler says 'no early mornings', avoid options that depart "
        "before 09:00; otherwise prefer comfortable and convenient options "
        "within budget. Return the chosen options exactly as they appear."
    ),
    tools=[search_transport],
    output_type=TransportPlan,
)
