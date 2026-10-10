import asyncio
from typing import TypedDict

from agents import Runner
from openai import RateLimitError
from langgraph.graph import END, START, StateGraph

from travel_planner.agents.activity import activity_agent
from travel_planner.agents.flight import flight_agent
from travel_planner.agents.hotel import hotel_agent
from travel_planner.orchestrator.budget import split_budget
from travel_planner.orchestrator.validator import validate
from travel_planner.schemas import ActivityPlan, HotelPlan, TransportPlan, TripRequest

MAX_ATTEMPTS = 3

async def run_with_retry(agent, prompt: str, retries: int = 3):
    """Run an agent; if the free per-minute quota is hit, wait and try again."""
    for attempt in range(retries + 1):
        try:
            return await Runner.run(agent, prompt)
        except RateLimitError as exc:
            # Only wait for per-minute limits. A daily limit won't clear in a minute.
            if "PerMinute" not in str(exc) or attempt == retries:
                raise
            await asyncio.sleep(60 + 10 * attempt)
            


class PlanState(TypedDict, total=False):
    request: TripRequest
    budgets: dict[str, float]
    transport: TransportPlan
    hotel: HotelPlan
    activities: ActivityPlan
    feedback: dict[str, str]  # {agent: what to fix}; empty when the plan is valid
    attempts: int


def _needs_run(state: PlanState, key: str, agent: str) -> bool:
    """Run an agent the first time, or again only if the validator flagged it."""
    return key not in state or agent in state.get("feedback", {})


def _with_feedback(prompt: str, state: PlanState, agent: str) -> str:
    note = state.get("feedback", {}).get(agent)
    if note:
        prompt += f"\n\nYour previous answer was rejected: {note}\nFix this and answer again."
    return prompt


def allocate(state: PlanState) -> dict:
    return {"budgets": split_budget(state["request"]), "attempts": 0, "feedback": {}}


def start_round(state: PlanState) -> dict:
    return {"attempts": state["attempts"] + 1}


async def flight_node(state: PlanState) -> dict:
    if not _needs_run(state, "transport", "flight"):
        return {}
    r, b = state["request"], state["budgets"]
    prompt = (
        f"Origin: {r.origin}\nDestination: {r.destination}\n"
        f"Transport budget (round trip total): Rs {b['transport']:.0f}\n"
        f"Preferences: {', '.join(r.preferences)}"
    )
    result = await run_with_retry(flight_agent, _with_feedback(prompt, state, "flight"))
    return {"transport": result.final_output}


async def hotel_node(state: PlanState) -> dict:
    if not _needs_run(state, "hotel", "hotel"):
        return {}
    r, b = state["request"], state["budgets"]
    prompt = (
        f"Destination: {r.destination}\nNights: {r.nights}\n"
        f"Maximum price per night: Rs {b['max_nightly']:.0f}\n"
        f"Preferences: {', '.join(r.preferences)}"
    )
    result = await run_with_retry(hotel_agent, _with_feedback(prompt, state, "hotel"))
    return {"hotel": result.final_output}


async def activity_node(state: PlanState) -> dict:
    if not _needs_run(state, "activities", "activity"):
        return {}
    r, b = state["request"], state["budgets"]
    prompt = (
        f"Destination: {r.destination}\nTrip length: {r.nights} nights\n"
        f"Activity budget: Rs {b['activities']:.0f}\n"
        f"Preferences: {', '.join(r.preferences)}"
    )
    result = await run_with_retry(activity_agent, _with_feedback(prompt, state, "activity"))
    return {"activities": result.final_output}


def validate_node(state: PlanState) -> dict:
    feedback = validate(
        state["request"], state["budgets"],
        state["transport"], state["hotel"], state["activities"],
    )
    return {"feedback": feedback}


def route(state: PlanState) -> str:
    if state["feedback"] and state["attempts"] < MAX_ATTEMPTS:
        return "retry"
    return "done"


def build_graph():
    # Node names must differ from state keys, so these end in _node
    g = StateGraph(PlanState)
    g.add_node("allocate", allocate)
    g.add_node("start_round", start_round)
    g.add_node("flight_node", flight_node)
    g.add_node("hotel_node", hotel_node)
    g.add_node("activity_node", activity_node)
    g.add_node("validate_node", validate_node)

    g.add_edge(START, "allocate")
    g.add_edge("allocate", "start_round")
    for name in ("flight_node", "hotel_node", "activity_node"):
        g.add_edge("start_round", name)  # these three run in parallel
    g.add_edge(["flight_node", "hotel_node", "activity_node"], "validate_node")
    g.add_conditional_edges("validate_node", route, {"retry": "start_round", "done": END})
    return g.compile()
