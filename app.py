import time
from datetime import date, timedelta

import streamlit as st

from travel_planner.orchestrator.graph import build_graph
from travel_planner.orchestrator.schedule import schedule_by_day
from travel_planner.runner import run_async
from travel_planner.schemas import TripRequest
from travel_planner.tools.mock_data import available_destinations

CATEGORIES = ["beach", "food", "culture", "nature", "adventure", "nightlife", "shopping"]

st.set_page_config(page_title="AI Travel Planner", page_icon="🧳", layout="wide")
st.title("🧳 Multi-Agent Travel Planner")
st.caption("Transport, hotel and activity agents work in parallel. A validator checks the budget and sends fixes back.")

with st.sidebar:
    st.header("Your trip")
    origin = st.selectbox("From", ["Bengaluru"])
    destination = st.selectbox("Destination", available_destinations(origin))
    start = st.date_input("Start date", value=date.today() + timedelta(days=30), min_value=date.today())
    nights = st.number_input("Number of nights", min_value=1, max_value=14, value=5)
    budget = st.number_input("Total budget (₹)", min_value=10000, max_value=500000, value=60000, step=5000)
    picks = st.multiselect("Interests", CATEGORIES, default=["food", "culture"])
    avoid_early = st.checkbox("No early mornings", value=True)
    run_clicked = st.button("Plan my trip", type="primary", use_container_width=True)

if run_clicked:
    prefs = picks + (["no early mornings"] if avoid_early else [])
    request = TripRequest(
        origin=origin,
        destination=destination,
        start=start,
        end=start + timedelta(days=int(nights)),
        budget=float(budget),
        preferences=prefs,
    )
    with st.spinner("Transport, hotel and activity agents are working..."):
        try:
            started = time.perf_counter()
            state = run_async(build_graph().ainvoke({"request": request}))
            st.session_state["plan"] = state
            st.session_state["seconds"] = time.perf_counter() - started
        except Exception as exc:  # show quota/network problems instead of crashing
            st.session_state.pop("plan", None)
            st.error(f"Planning failed: {exc}")


def show_plan(state: dict) -> None:
    req, b = state["request"], state["budgets"]
    transport, hotel = state["transport"], state["hotel"].hotel
    acts = state["activities"].activities

    t_total = transport.outbound.price + transport.inbound.price
    h_total = hotel.price_per_night * req.nights
    a_total = sum(a.cost for a in acts)
    grand = t_total + h_total + a_total

    st.subheader(f"{req.origin} → {req.destination} · {req.start:%d %b} to {req.end:%d %b} ({req.nights} nights)")

    rows = [
        ("Transport", t_total, b["transport"]),
        ("Stay", h_total, b["stay"]),
        ("Activities", a_total, b["activities"]),
        ("Total", grand, req.budget),
    ]
    for col, (label, spent, limit) in zip(st.columns(4), rows):
        col.metric(label, f"₹{spent:,.0f}")
        col.caption(f"Budget ₹{limit:,.0f}")

    if state["feedback"]:
        st.warning(
            "The agents could not fully fix these problems within 3 attempts:\n\n"
            + "\n".join(f"- **{agent}**: {msg}" for agent, msg in state["feedback"].items())
        )
    else:
        st.success(f"All checks passed after {state['attempts']} attempt(s).")

    tab_days, tab_transport, tab_hotel, tab_budget = st.tabs(
        ["Itinerary", "Transport", "Hotel", "Budget"]
    )

    with tab_days:
        for i, day in enumerate(schedule_by_day(acts, req.nights + 1), start=1):
            when = req.start + timedelta(days=i - 1)
            st.markdown(f"**Day {i} · {when:%a %d %b}**")
            st.markdown("\n".join(
                f"- {a.name} ({a.area}, {a.time_of_day.replace('_', ' ')}) · ₹{a.cost:,.0f}"
                for a in day
            ))

    with tab_transport:
        for title, leg in (("Outbound", transport.outbound), ("Return", transport.inbound)):
            st.markdown(
                f"**{title}:** {leg.origin} → {leg.destination} · {leg.carrier} ({leg.mode}) · "
                f"{leg.depart} → {leg.arrive} · ₹{leg.price:,.0f}"
            )

    with tab_hotel:
        st.markdown(f"**{hotel.name}** · {hotel.area} · rating {hotel.rating}")
        st.markdown(f"₹{hotel.price_per_night:,.0f} per night × {req.nights} nights = ₹{h_total:,.0f}")
        st.caption("Tags: " + ", ".join(hotel.tags))

    with tab_budget:
        st.table([
            {"Category": label, "Budget": f"₹{limit:,.0f}", "Spent": f"₹{spent:,.0f}"}
            for label, spent, limit in rows
        ])
        st.caption(f"Planned in {st.session_state.get('seconds', 0):.1f}s using parallel agents.")


if "plan" in st.session_state:
    show_plan(st.session_state["plan"])
else:
    st.info("Choose your trip in the sidebar and click **Plan my trip**.")
    