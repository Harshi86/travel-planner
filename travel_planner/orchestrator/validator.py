from travel_planner.schemas import ActivityPlan, HotelPlan, TransportPlan, TripRequest
from travel_planner.tools.mock_data import load_activities, load_flights, load_hotels


def _avoid_early(request: TripRequest) -> bool:
    return any("early" in p.lower() for p in request.preferences)


def check_transport(request: TripRequest, budgets: dict, plan: TransportPlan) -> list[str]:
    problems = []
    legs = [plan.outbound, plan.inbound]
    total = sum(leg.price for leg in legs)
    if total > budgets["transport"]:
        problems.append(
            f"Round-trip total Rs {total:.0f} exceeds the transport budget of "
            f"Rs {budgets['transport']:.0f}. Choose cheaper options (a train or bus is fine)."
        )
    if _avoid_early(request):
        for leg in legs:
            if leg.depart < "09:00":
                problems.append(
                    f"{leg.carrier} departs at {leg.depart}, which is too early. "
                    "Choose a departure at 09:00 or later."
                )
    real_out = {(o["carrier"], o["depart"], o["price"])
                for o in load_flights(request.origin, request.destination)}
    real_in = {(o["carrier"], o["depart"], o["price"])
               for o in load_flights(request.destination, request.origin)}
    if (plan.outbound.carrier, plan.outbound.depart, plan.outbound.price) not in real_out:
        problems.append("The outbound option is not in the search results. Choose only from them.")
    if (plan.inbound.carrier, plan.inbound.depart, plan.inbound.price) not in real_in:
        problems.append("The return option is not in the search results. Choose only from them.")
    return problems


def check_hotel(request: TripRequest, budgets: dict, plan: HotelPlan) -> list[str]:
    problems = []
    h = plan.hotel
    if h.price_per_night > budgets["max_nightly"]:
        problems.append(
            f"{h.name} costs Rs {h.price_per_night:.0f}/night, above the maximum of "
            f"Rs {budgets['max_nightly']:.0f}. Choose a cheaper hotel."
        )
    real = {(x["name"], x["price_per_night"]) for x in load_hotels(request.destination)}
    if (h.name, h.price_per_night) not in real:
        problems.append("That hotel is not in the search results. Choose only from them.")
    return problems


def check_activities(request: TripRequest, budgets: dict, plan: ActivityPlan) -> list[str]:
    problems = []
    acts = plan.activities
    total = sum(a.cost for a in acts)
    if total > budgets["activities"]:
        problems.append(
            f"Activities total Rs {total:.0f}, above the budget of "
            f"Rs {budgets['activities']:.0f}. Remove or swap the expensive ones."
        )
    days = request.nights + 1
    if len(acts) > 3 * days:
        problems.append(f"{len(acts)} activities is too many. Choose at most {3 * days}.")
    if _avoid_early(request) and any(a.time_of_day == "early_morning" for a in acts):
        problems.append("Remove activities with time_of_day 'early_morning'.")
    real = {(x["name"], x["cost"]) for x in load_activities(request.destination, [])}
    if any((a.name, a.cost) not in real for a in acts):
        problems.append("Some activities are not in the search results. Choose only from them.")
    return problems


def validate(request: TripRequest, budgets: dict, transport: TransportPlan,
             hotel: HotelPlan, activities: ActivityPlan) -> dict[str, str]:
    """Return {agent: feedback}. An empty dict means the plan is valid."""
    results = {
        "flight": check_transport(request, budgets, transport),
        "hotel": check_hotel(request, budgets, hotel),
        "activity": check_activities(request, budgets, activities),
    }
    return {agent: " ".join(p) for agent, p in results.items() if p}
