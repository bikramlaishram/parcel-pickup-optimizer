"""Parcel pickup planning: a manual-style baseline and an OR-Tools optimizer,
both run through the same simulated day with requests arriving in waves."""
import json, math
from ortools.constraint_solver import pywrapcp, routing_enums_pb2

TRAFFIC = 1.35          # assumption: city traffic slows free-flow road times by 35%
END_OF_DAY = 18 * 3600

class Day:
    def __init__(self, path="data/day.json"):
        d = json.load(open(path))
        self.raw = d
        self.drivers = d["drivers"]
        self.reqs = d["requests"]                     # node i+1 <-> reqs[i]
        self.n = len(self.reqs) + 1
        self.T = [[int(round(x * TRAFFIC)) for x in row] for row in d["duration_s"]]
        self.D = d["distance_m"]
        self.waves = d["waves"]

    def req(self, node): return self.reqs[node - 1]
    def service(self, node):
        return 0 if node == 0 else int((4 + 0.25 * self.req(node)["parcels"]) * 60)
    def tw(self, node):
        if node == 0: return (0, END_OF_DAY)
        r = self.req(node); return (r["tw_start"] * 60, r["tw_end"] * 60)
    def weight(self, node):
        r = self.req(node); return r["parcels"] * (2.5 if r["priority"] == "express" else 1.0)

def simulate(day, start_node, start_time, stops):
    """Timeline for a driver leaving start_node at start_time and visiting stops."""
    out, t, cur = [], start_time, start_node
    for s in stops:
        arr = t + day.T[cur][s]
        a, b = day.tw(s)
        begin = max(arr, a)
        dep = begin + day.service(s)
        out.append({"node": s, "arrive": arr, "start": begin, "depart": dep, "late": begin > b})
        t, cur = dep, s
    back = t + day.T[cur][0]
    return out, back

# ---------------------------------------------------------------- baseline
def bearing(day, node):
    r = day.req(node); d = day.raw["depot"]
    return math.atan2(r["lat"] - d["lat"], (r["lon"] - d["lon"]) * math.cos(math.radians(d["lat"])))

def make_zones(day, nodes, k):
    """Dispatcher-style zones: equal-count angular sectors around the depot."""
    order = sorted(nodes, key=lambda x: bearing(day, x))
    cuts = [bearing(day, order[int(len(order) * i / k)]) for i in range(1, k)]
    def zone(node):
        b = bearing(day, node)
        return sum(b >= c for c in cuts)
    return zone

def greedy_route(day, drv, start_node, start_time, load, pool):
    """Driver works through own zone: next stop = earliest it can be served, nearest on ties."""
    stops, t, cur, pool = [], start_time, start_node, set(pool)
    while True:
        best = None
        for s in pool:
            arr = t + day.T[cur][s]; a, b = day.tw(s)
            begin = max(arr, a)
            if begin > b or load + day.req(s)["parcels"] > drv["capacity"]:
                continue
            if begin + day.service(s) + day.T[s][0] > drv["shift_end"] * 60:
                continue
            key = (begin, day.T[cur][s])
            if best is None or key < best[0]: best = (key, s, begin)
        if best is None: return stops
        _, s, begin = best
        stops.append(s); pool.discard(s)
        t, cur, load = begin + day.service(s), s, load + day.req(s)["parcels"]

# ---------------------------------------------------------------- optimizer
REASSIGN_PENALTY = 1500   # seconds-equivalent cost for moving a planned stop to a different driver

def optimize(day, starts, pool, seconds, previous=None):
    """starts: per driver (node, time, load_used); previous: last plan per driver (keeps routes stable).
    Returns per-driver ordered stop lists."""
    pool = list(pool)
    local = [0] + sorted({s[0] for s in starts if s[0] != 0}) + pool
    li = {n: i for i, n in enumerate(local)}
    V = len(day.drivers)
    mgr = pywrapcp.RoutingIndexManager(len(local), V, [li[s[0]] for s in starts], [0] * V)
    rt = pywrapcp.RoutingModel(mgr)
    start_nodes = {s[0] for s in starts}

    def svc(n): return 0 if n in start_nodes else day.service(n)
    def travel(i, j):
        a, b = local[mgr.IndexToNode(i)], local[mgr.IndexToNode(j)]
        return day.T[a][b]
    def transit(i, j):
        a, b = local[mgr.IndexToNode(i)], local[mgr.IndexToNode(j)]
        return svc(a) + day.T[a][b]
    owner = {n: v for v, plan in enumerate(previous or []) for n in plan}
    def vehicle_cost(v):
        def f(i, j):
            b = local[mgr.IndexToNode(j)]
            moved = b in owner and owner[b] != v
            return travel(i, j) + (REASSIGN_PENALTY if moved else 0)
        return f
    keep = []
    for v in range(V):
        cb = vehicle_cost(v); keep.append(cb)
        rt.SetArcCostEvaluatorOfVehicle(rt.RegisterTransitCallback(cb), v)
    time_cb = rt.RegisterTransitCallback(transit)
    rt.AddDimension(time_cb, 3 * 3600, END_OF_DAY, False, "Time")
    td = rt.GetDimensionOrDie("Time")

    def demand(i):
        n = local[mgr.IndexToNode(i)]
        return 0 if (n == 0 or n in start_nodes) else day.req(n)["parcels"]
    dem_cb = rt.RegisterUnaryTransitCallback(demand)
    rt.AddDimensionWithVehicleCapacity(dem_cb, 0, [d["capacity"] - s[2] for d, s in zip(day.drivers, starts)], True, "Load")

    for n in pool:
        idx = mgr.NodeToIndex(li[n]); a, b = day.tw(n)
        td.CumulVar(idx).SetRange(a, b)
        rt.AddDisjunction([idx], int(1500 + 3000 * day.weight(n)))
    for v, (d, s) in enumerate(zip(day.drivers, starts)):
        td.CumulVar(rt.Start(v)).SetRange(s[1], s[1])
        td.CumulVar(rt.End(v)).SetMax(d["shift_end"] * 60)
        rt.AddVariableMinimizedByFinalizer(td.CumulVar(rt.End(v)))

    p = pywrapcp.DefaultRoutingSearchParameters()
    p.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION
    p.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    p.time_limit.seconds = seconds
    sol = None
    if previous:
        hint = [[li[n] for n in plan if n in li and n not in start_nodes] for plan in previous]
        init = rt.ReadAssignmentFromRoutes(hint, True)
        if init:
            sol = rt.SolveFromAssignmentWithParameters(init, p)
    if sol is None:
        sol = rt.SolveWithParameters(p)
    assert sol, "no solution"
    routes = []
    for v in range(V):
        i, r = rt.Start(v), []
        i = sol.Value(rt.NextVar(i))
        while not rt.IsEnd(i):
            r.append(local[mgr.IndexToNode(i)]); i = sol.Value(rt.NextVar(i))
        routes.append(r)
    return routes

# ---------------------------------------------------------------- the day
def run_day(day, strategy, solve_seconds=(20, 10)):
    V = len(day.drivers)
    known = [i + 1 for i, r in enumerate(day.reqs) if r["wave"] == 0]
    done = [[] for _ in range(V)]                 # executed timeline entries
    plans = [[] for _ in range(V)]                # future stops (node ids)
    starts = [(0, d["shift_start"] * 60, 0) for d in day.drivers]
    events, snapshots = [], []
    zone = make_zones(day, known, V) if strategy == "baseline" else None

    def plan(pool, seconds):
        if strategy == "optimized":
            return optimize(day, starts, pool, seconds, previous=plans if any(plans) else None)
        out = []
        for v, d in enumerate(day.drivers):
            mine = [n for n in pool if zone(n) == v]
            out.append(greedy_route(day, d, starts[v][0], starts[v][1], starts[v][2], mine))
        return out

    def pending():
        taken = {e["node"] for tl in done for e in tl} | {s[0] for s in starts}
        return [n for n in known if n not in taken]

    plans = plan(pending(), solve_seconds[0])
    snapshots.append({"time": 7 * 3600, "starts": list(starts), "plans": [list(p) for p in plans]})
    events.append({"time": 7 * 3600, "type": "plan", "new": len(known),
                   "planned": sum(map(len, plans)), "dropped": len(known) - sum(map(len, plans))})

    for w, tmin in enumerate(day.waves, start=1):
        T = tmin * 60
        prev_plans = [list(p) for p in plans]
        new_starts = []
        for v in range(V):
            node0, t0, load = starts[v]
            tl, back = simulate(day, node0, t0, plans[v])
            executed = [e for e in tl if e["depart"] <= T]
            rest = [e for e in tl if e["depart"] > T]
            done[v] += executed
            load += sum(day.req(e["node"])["parcels"] for e in executed)
            if rest:   # en route to / serving the next stop: that stop is committed
                c = rest[0]; done[v].append(c)
                load += day.req(c["node"])["parcels"]
                new_starts.append((c["node"], c["depart"], load))
            else:
                new_starts.append((0, max(T, back), load))
        starts = new_starts
        arrivals = [i + 1 for i, r in enumerate(day.reqs) if r["wave"] == w]
        known += arrivals
        plans = plan(pending(), solve_seconds[1])
        planned = set(n for p in plans for n in p)
        changes = []
        gone = {e["node"] for tl in done for e in tl}
        for v in range(V):
            before = [n for n in prev_plans[v] if n not in gone]
            added = [n for n in plans[v] if n not in before]
            removed = [n for n in before if n not in plans[v]]
            changes.append({"driver": day.drivers[v]["id"], "added": added, "removed": removed})
        events.append({"time": T, "type": "replan", "wave": w, "new": arrivals,
                       "new_assigned": [n for n in arrivals if n in planned], "changes": changes,
                       "pending_unplanned": [n for n in pending() if n not in planned]})
        snapshots.append({"time": T, "starts": list(starts), "plans": [list(p) for p in plans]})

    final = []
    for v in range(V):
        tl, back = simulate(day, starts[v][0], starts[v][1], plans[v])
        final.append({"driver": day.drivers[v]["id"], "stops": done[v] + tl, "return": back})
    return final, events, snapshots

def kpis(day, final):
    served = [e["node"] for r in final for e in r["stops"]]
    km, drive = 0.0, 0
    for r in final:
        seq = [0] + [e["node"] for e in r["stops"]] + [0]
        km += sum(day.D[a][b] for a, b in zip(seq, seq[1:])) / 1000
        drive += sum(day.T[a][b] for a, b in zip(seq, seq[1:]))
    hours = sum(r["return"] - d["shift_start"] * 60 for r, d in zip(final, day.drivers)) / 3600
    total = len(day.reqs)
    exp = [i + 1 for i, r in enumerate(day.reqs) if r["priority"] == "express"]
    return {
        "requests_total": total, "requests_served": len(served),
        "parcels_total": sum(r["parcels"] for r in day.reqs),
        "parcels_collected": sum(day.req(n)["parcels"] for n in served),
        "express_total": len(exp), "express_served": len([n for n in served if n in set(exp)]),
        "km": round(km, 1), "drive_hours": round(drive / 3600, 1),
        "late_stops": sum(e["late"] for r in final for e in r["stops"]),
        "driver_hours": round(hours, 1),
        "parcels_per_driver_hour": round(sum(day.req(n)["parcels"] for n in served) / hours, 1),
    }
