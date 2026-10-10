import argparse
import asyncio
import csv
import statistics
import time
from datetime import date, timedelta
from pathlib import Path

from travel_planner.orchestrator.graph import build_graph
from travel_planner.schemas import TripRequest

HERE = Path(__file__).parent
RESULTS = HERE / "results.csv"
SUMMARY = HERE / "summary.md"
START = date(2026, 12, 20)
FIELDS = ["id", "destination", "nights", "budget", "prefs", "stress", "total_cost",
          "within_budget", "constraints_ok", "attempts", "n_activities",
          "activities_per_day", "seconds", "error"]

# (id, destination, nights, budget, preferences, stress)
# stress=True means the budget is too low for any valid plan, so a clear warning is the right outcome
CASES = [
    (1, "Goa", 5, 60000, ["beach", "food", "no early mornings"], False),
    (2, "Jaipur", 4, 50000, ["culture", "shopping", "no early mornings"], False),
    (3, "Kochi", 3, 40000, ["nature", "food"], False),
    (4, "Goa", 5, 8000, ["beach", "food"], True),
    (5, "Jaipur", 5, 60000, ["adventure", "culture"], False),
    (6, "Kochi", 5, 55000, ["culture", "beach", "no early mornings"], False),
    (7, "Goa", 3, 35000, ["beach", "nightlife"], False),
    (8, "Jaipur", 3, 28000, ["shopping", "food", "no early mornings"], False),
    (9, "Kochi", 4, 45000, ["nature", "adventure"], False),
    (10, "Jaipur", 4, 12000, ["culture"], True),
    (11, "Goa", 7, 90000, ["culture", "nature", "food"], False),
    (12, "Kochi", 3, 6000, ["beach", "food"], True),
    (13, "Jaipur", 3, 40000, ["food", "culture"], False),
    (14, "Goa", 4, 45000, ["adventure", "beach", "no early mornings"], False),
    (15, "Kochi", 2, 22000, ["food", "culture"], False),
    (16, "Goa", 5, 30000, ["beach", "food"], False),
    (17, "Jaipur", 6, 80000, ["culture", "shopping", "food"], False),
    (18, "Kochi", 6, 70000, ["nature", "food", "shopping", "no early mornings"], False),
    (19, "Goa", 2, 25000, ["food", "shopping"], False),
    (20, "Kochi", 5, 35000, ["culture", "food", "no early mornings"], False),
]


def is_quota_error(text: str) -> bool:
    t = text.lower()
    return "429" in t or "resource_exhausted" in t or "quota" in t


def load_rows() -> dict[int, dict]:
    if not RESULTS.exists():
        return {}
    with RESULTS.open(newline="", encoding="utf-8") as f:
        return {int(r["id"]): r for r in csv.DictReader(f)}


def save_rows(rows: dict[int, dict]) -> None:
    with RESULTS.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for cid in sorted(rows):
            writer.writerow(rows[cid])


async def run_case(graph, case) -> tuple[dict, bool]:
    cid, dest, nights, budget, prefs, stress = case
    request = TripRequest(
        origin="Bengaluru", destination=dest, start=START,
        end=START + timedelta(days=nights), budget=budget, preferences=prefs,
    )
    row = {"id": cid, "destination": dest, "nights": nights, "budget": budget,
           "prefs": "; ".join(prefs), "stress": stress, "total_cost": "",
           "within_budget": "", "constraints_ok": "", "attempts": "",
           "n_activities": "", "activities_per_day": "",
           "seconds": "", "error": ""}
    started = time.perf_counter()
    try:
        state = await graph.ainvoke({"request": request})
    except Exception as exc:
        text = f"{type(exc).__name__}: {exc}".replace("\n", " ")
        row["error"] = text[:200]
        row["seconds"] = round(time.perf_counter() - started, 1)
        return row, is_quota_error(text)

    t = state["transport"]
    h = state["hotel"].hotel
    acts = state["activities"].activities
    # Total recomputed here in plain code, independent of the LLM
    total = t.outbound.price + t.inbound.price + h.price_per_night * nights + sum(a.cost for a in acts)
    row.update(
        total_cost=round(total),
        within_budget=total <= budget,
        constraints_ok=not state["feedback"],
        attempts=state["attempts"],
        n_activities=len(acts),
        activities_per_day=round(len(acts) / (nights + 1), 2),
        seconds=round(time.perf_counter() - started, 1),
    )
    return row, False


def pct(n: int, d: int) -> str:
    return f"{100 * n / d:.0f}% ({n}/{d})" if d else "n/a"


def avg(xs: list[float]) -> str:
    return f"{statistics.mean(xs):.1f}" if xs else "n/a"


def summarize(rows: dict[int, dict]) -> list[str]:
    done = [r for r in rows.values() if not r["error"]]
    normal = [r for r in done if r["stress"] != "True"]
    stress = [r for r in done if r["stress"] == "True"]
    ok = lambda r: r["constraints_ok"] == "True"
    attempts = lambda r: int(r["attempts"])
    secs = [float(r["seconds"]) for r in done]

    lines = [
        "# Evaluation summary", "",
        f"Cases completed: {len(done)} of {len(CASES)} "
        f"({len(rows) - len(done)} errored and will be retried)", "",
        f"## Normal requests ({len(normal)})",
        f"- Total cost within budget: {pct(sum(r['within_budget'] == 'True' for r in normal), len(normal))}",
        f"- All validator rules satisfied: {pct(sum(ok(r) for r in normal), len(normal))}",
        f"- Passed on the first attempt: {pct(sum(ok(r) and attempts(r) == 1 for r in normal), len(normal))}",
        f"- Fixed by the feedback loop (needed 2+ attempts): {pct(sum(ok(r) and attempts(r) > 1 for r in normal), len(normal))}",
        f"- Average attempts: {avg([attempts(r) for r in normal])}",
        f"- Average activities per day: {avg([float(r['activities_per_day']) for r in normal])}", "",
        f"## Impossible-budget stress cases ({len(stress)})",
        f"- Finished with a clear warning instead of crashing: {pct(sum(not ok(r) for r in stress), len(stress))}", "",
        "## Speed",
        f"- Median time per plan: {statistics.median(secs):.1f}s" if secs else "- Median time per plan: n/a",
        f"- Slowest plan: {max(secs):.1f}s" if secs else "- Slowest plan: n/a",
    ]
    return lines


async def main(args: argparse.Namespace) -> None:
    rows = {} if args.fresh else load_rows()
    pending = [c for c in CASES if c[0] not in rows or rows[c[0]]["error"]]
    batch = pending[: args.limit]
    graph = build_graph()

    for i, case in enumerate(batch, start=1):
        print(f"[{i}/{len(batch)}] case {case[0]}: {case[1]}, {case[2]} nights, Rs {case[3]}")
        row, quota_hit = await run_case(graph, case)
        rows[case[0]] = row
        save_rows(rows)
        if row["error"]:
            print("   -> ERROR", row["error"])
        else:
            print(f"   -> rules_ok={row['constraints_ok']} attempts={row['attempts']} {row['seconds']}s")
        if quota_hit:
            print("\nFree quota reached. Progress is saved. Run the same command later to continue.")
            break
        if i < len(batch):
            await asyncio.sleep(args.pause)

    lines = summarize(rows)
    SUMMARY.write_text("\n".join(lines), encoding="utf-8")
    print("\n" + "\n".join(lines))
    left = [c for c in CASES if c[0] not in rows or rows[c[0]]["error"]]
    if left:
        print(f"\n{len(left)} case(s) still to run. Run the same command again to continue.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=5, help="max new cases to run this session")
    parser.add_argument("--pause", type=float, default=15, help="seconds to wait between cases")
    parser.add_argument("--fresh", action="store_true", help="ignore saved results and start over")
    asyncio.run(main(parser.parse_args()))
    