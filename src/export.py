"""Build the compact JSON the dashboard reads (routes, road geometry, events, intake, notifications)."""
import json, random, sys
sys.path.insert(0, "src")
from planner import Day, simulate
from osrm import route_geometry
from intake import compose, parse, hhmm

day = Day(); res = json.load(open("out/results.json"))
rid = lambda n: day.req(n)["id"]
depot = (day.raw["depot"]["lat"], day.raw["depot"]["lon"])
rnd = random.Random(3)

out = {"city": day.raw["city"], "depot": day.raw["depot"], "waves": day.waves,
       "drivers": [{"id": d["id"], "name": d["name"], "start": d["shift_start"], "end": d["shift_end"], "capacity": d["capacity"]} for d in day.drivers],
       "requests": [{k: r[k] for k in ("id", "lat", "lon", "parcels", "tw_start", "tw_end", "priority", "customer", "wave", "arrives")} for r in day.reqs],
       "assumptions": {"traffic_factor": 1.35, "service_min": "4 + 0.25 per parcel", "road_data": "OSRM on OpenStreetMap"},
       "strategies": {}}

for strat, r in res.items():
    routes = []
    for route in r["final"]:
        seq = [e["node"] for e in route["stops"]]
        pts = [depot] + [(day.req(n)["lat"], day.req(n)["lon"]) for n in seq] + [depot]
        routes.append({"driver": route["driver"], "return": route["return"] // 60,
                       "stops": [{"id": rid(e["node"]), "arrive": e["arrive"] // 60, "start": e["start"] // 60, "depart": e["depart"] // 60} for e in route["stops"]],
                       "geometry": route_geometry(pts)})
    events = []
    for ev, snap in zip(r["events"], r["snapshots"]):
        if ev["type"] == "plan":
            events.append({"time": ev["time"] // 60, "type": "plan", "planned": ev["planned"], "dropped": ev["dropped"]}); continue
        notes = []
        for v, ch in enumerate(ev["changes"]):
            if not ch["added"] and not ch["removed"]: continue
            node0, t0, _ = snap["starts"][v]
            tl, _ = simulate(day, node0, t0, snap["plans"][v])
            at = {e["node"]: e["start"] for e in tl}
            notes.append({"driver": ch["driver"],
                          "added": [{"id": rid(n), "customer": day.req(n)["customer"], "parcels": day.req(n)["parcels"], "eta": at[n] // 60, "express": day.req(n)["priority"] == "express"} for n in ch["added"]],
                          "removed": [{"id": rid(n), "customer": day.req(n)["customer"],
                                       "to": next((day.drivers[u]["id"] for u, pl in enumerate(snap["plans"]) if n in pl), None)} for n in ch["removed"]],
                          "next_stops": len(snap["plans"][v])})
        events.append({"time": ev["time"] // 60, "type": "replan", "wave": ev["wave"],
                       "new": [rid(n) for n in ev["new"]], "new_assigned": [rid(n) for n in ev["new_assigned"]],
                       "unplanned": [rid(n) for n in ev["pending_unplanned"]], "notifications": notes})
    out["strategies"][strat] = {"kpis": r["kpis"], "routes": routes, "events": events}

out["intake"] = []
for rq in day.reqs:
    if rq["wave"] == 0: continue
    msg = compose(rq, rnd); p = parse(msg)
    out["intake"].append({"id": rq["id"], "wave": rq["wave"], "arrives": rq["arrives"], "message": msg, "parsed": p})
json.dump(out, open("out/dashboard_data.json", "w"), separators=(",", ":"))
print("ok", len(json.dumps(out)) // 1024, "KB")
