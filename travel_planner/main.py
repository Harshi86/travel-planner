from datetime import date

from agents import Runner
from dotenv import load_dotenv

from travel_planner.agents.activity import activity_agent
from travel_planner.agents.flight import flight_agent
from travel_planner.agents.hotel import hotel_agent
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
    prefs = ", ".join(request.preferences)

    # Budget split and math are done in code, not by the LLM
    transport_budget = request.budget * 0.35
    stay_budget = request.budget * 0.40
    activity_budget = request.budget * 0.25
    max_nightly = stay_budget / request.nights

    transport = Runner.run_sync(
        flight_agent,
        f"Origin: {request.origin}\nDestination: {request.destination}\n"
        f"Transport budget (round trip total): Rs {transport_budget:.0f}\n"
        f"Preferences: {prefs}",
    ).final_output

    hotel = Runner.run_sync(
        hotel_agent,
        f"Destination: {request.destination}\nNights: {request.nights}\n"
        f"Maximum price per night: Rs {max_nightly:.0f}\n"
        f"Preferences: {prefs}",
    ).final_output

    activities = Runner.run_sync(
        activity_agent,
        f"Destination: {request.destination}\n"
        f"Trip length: {request.nights} nights\n"
        f"Activity budget: Rs {activity_budget:.0f}\n"
        f"Preferences: {prefs}",
    ).final_output

    transport_total = transport.outbound.price + transport.inbound.price
    stay_total = hotel.hotel.price_per_night * request.nights
    activity_total = sum(a.cost for a in activities.activities)
    grand_total = transport_total + stay_total + activity_total

    print("\n=== TRANSPORT ===")
    for leg in (transport.outbound, transport.inbound):
        print(f"{leg.origin} -> {leg.destination}: {leg.carrier} ({leg.mode}) "
              f"{leg.depart}-{leg.arrive}, Rs {leg.price:.0f}")
    print(f"Subtotal: Rs {transport_total:.0f} (budget Rs {transport_budget:.0f})")

    print("\n=== HOTEL ===")
    print(f"{hotel.hotel.name} ({hotel.hotel.area}), rating {hotel.hotel.rating}, "
          f"Rs {hotel.hotel.price_per_night:.0f}/night x {request.nights}")
    print(f"Subtotal: Rs {stay_total:.0f} (budget Rs {stay_budget:.0f})")

    print("\n=== ACTIVITIES ===")
    for a in activities.activities:
        print(f"- {a.name} ({a.area}, {a.time_of_day}) Rs {a.cost:.0f}")
    print(f"Subtotal: Rs {activity_total:.0f} (budget Rs {activity_budget:.0f})")

    print(f"\nGRAND TOTAL: Rs {grand_total:.0f} of Rs {request.budget:.0f}")


if __name__ == "__main__":
    main()
    