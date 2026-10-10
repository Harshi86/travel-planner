from datetime import date

from agents import Runner
from dotenv import load_dotenv

from travel_planner.agents.activity import activity_agent
from travel_planner.schemas import TripRequest

load_dotenv()


def main() -> None:
    request = TripRequest(
        origin="Bengaluru",
        destination="Goa",
        start=date(2026, 12, 20),
        end=date(2026, 12, 25),
        budget=60000,
        preferences=["beaches", "food", "no early mornings"],
    )

    # Budget math is done in code, not by the LLM
    activity_budget = request.budget * 0.25

    prompt = (
        f"Destination: {request.destination}\n"
        f"Trip length: {request.nights} nights\n"
        f"Activity budget: Rs {activity_budget:.0f}\n"
        f"Preferences: {', '.join(request.preferences)}"
    )

    result = Runner.run_sync(activity_agent, prompt)
    plan = result.final_output

    total = sum(a.cost for a in plan.activities)
    print(f"\nActivities chosen ({len(plan.activities)}):")
    for a in plan.activities:
        print(f"- {a.name} ({a.area}, {a.time_of_day}) Rs {a.cost:.0f}")
    print(f"\nTotal: Rs {total:.0f} of Rs {activity_budget:.0f} budget")


if __name__ == "__main__":
    main()
    