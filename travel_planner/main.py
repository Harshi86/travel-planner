import asyncio
import time
from datetime import date

from dotenv import load_dotenv

from travel_planner.orchestrator.graph import build_graph
from travel_planner.schemas import TripRequest

load_dotenv()


def print_plan(state: dict) -> None:
    req, b = state["request"], state["budgets"]
    transport, hotel = state["transport"], state["hotel"].hotel
    acts = state["activities"].activities

    t_total = transport.outbound.price + transport.inbound.price
    h_total = hotel.price_per_night * req.nights
    a_total = sum(a.cost for a in acts)

    print("\n=== TRANSPORT ===")
    for leg in (transport.outbound, transport.inbound):
        print(f"{leg.origin} -> {leg.destination}: {leg.carrier} ({leg.mode}) "
              f"{leg.depart}-{leg.arrive}, Rs {leg.price:.0f}")
    print(f"Subtotal: Rs {t_total:.0f} (budget Rs {b['transport']:.0f})")

    print("\n=== HOTEL ===")
    print(f"{hotel.name} ({hotel.area}), rating {hotel.rating}, "
          f"Rs {hotel.price_per_night:.0f}/night x {req.nights}")
    print(f"Subtotal: Rs {h_total:.0f} (budget Rs {b['stay']:.0f})")

    print("\n=== ACTIVITIES ===")
    for a in acts:
        print(f"- {a.name} ({a.area}, {a.time_of_day}) Rs {a.cost:.0f}")
    print(f"Subtotal: Rs {a_total:.0f} (budget Rs {b['activities']:.0f})")

    print(f"\nGRAND TOTAL: Rs {t_total + h_total + a_total:.0f} of Rs {req.budget:.0f}")
    print(f"Attempts used: {state['attempts']}")
    if state["feedback"]:
        print("\nWARNING: unresolved problems after the last attempt:")
        for agent, msg in state["feedback"].items():
            print(f"- {agent}: {msg}")


async def run(request: TripRequest) -> dict:
    return await build_graph().ainvoke({"request": request})


def main() -> None:
    request = TripRequest(
        origin="Bengaluru",
        destination="Goa",
        start=date(2026, 12, 20),
        end=date(2026, 12, 25),
        budget=22000,
        preferences=["beaches", "food", "no early mornings"],
    )
    started = time.perf_counter()
    state = asyncio.run(run(request))
    print_plan(state)
    print(f"Time taken: {time.perf_counter() - started:.1f}s")


if __name__ == "__main__":
    main()
