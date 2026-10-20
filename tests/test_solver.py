"""Small OR-Tools sanity check on a subset of the sample day (no network)."""
import json
import pytest
from planner import Day, optimize, simulate, greedy_route

N_REQ, N_DRV = 20, 2


@pytest.fixture
def tiny_day(root, tmp_path):
    d = json.load(open("data/day.json"))
    keep = [0] + list(range(1, N_REQ + 1))
    d["requests"] = d["requests"][:N_REQ]
    d["drivers"] = [{**drv, "capacity": 60} for drv in d["drivers"][:N_DRV]]
    for k in ("duration_s", "distance_m"):
        d[k] = [[d[k][i][j] for j in keep] for i in keep]
    p = tmp_path / "tiny.json"
    p.write_text(json.dumps(d))
    return Day(str(p))


def check(day, plans):
    seen = [n for p in plans for n in p]
    assert len(seen) == len(set(seen)), "stop served twice"
    for drv, plan in zip(day.drivers, plans):
        tl, back = simulate(day, 0, drv["shift_start"] * 60, plan)
        assert not any(e["late"] for e in tl), "time window violated"
        assert sum(day.req(n)["parcels"] for n in plan) <= drv["capacity"], "capacity exceeded"
        assert back <= drv["shift_end"] * 60, "back after shift end"


def test_optimizer_respects_constraints(tiny_day):
    starts = [(0, d["shift_start"] * 60, 0) for d in tiny_day.drivers]
    plans = optimize(tiny_day, starts, range(1, N_REQ + 1), seconds=1)
    assert len(plans) == N_DRV and any(plans)
    check(tiny_day, plans)


def test_optimizer_beats_or_matches_greedy(tiny_day):
    starts = [(0, d["shift_start"] * 60, 0) for d in tiny_day.drivers]
    opt = optimize(tiny_day, starts, range(1, N_REQ + 1), seconds=1)
    pool, greedy = set(range(1, N_REQ + 1)), []
    for d in tiny_day.drivers:
        r = greedy_route(tiny_day, d, 0, d["shift_start"] * 60, 0, pool)
        pool -= set(r); greedy.append(r)
    check(tiny_day, greedy)
    parcels = lambda plans: sum(tiny_day.req(n)["parcels"] for p in plans for n in p)
    assert parcels(opt) >= parcels(greedy)
