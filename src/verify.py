"""Independent check of the exported plans against the raw day data (no planner code used)."""
import json
day = json.load(open("data/day.json")); out = json.load(open("out/dashboard_data.json"))
reqs = {r["id"]: (i + 1, r) for i, r in enumerate(day["requests"])}
T = [[round(x * 1.35) for x in row] for row in day["duration_s"]]
problems = 0
def bad(msg):
    global problems; problems += 1; print("FAIL", msg)
for s, st in out["strategies"].items():
    seen, parcels = set(), 0
    for r, drv in zip(st["routes"], day["drivers"]):
        node, t, load = 0, drv["shift_start"] * 60, 0
        for sp in r["stops"]:
            n, q = reqs[sp["id"]]
            if sp["id"] in seen: bad(f"{s} {sp['id']} served twice")
            seen.add(sp["id"])
            arr = t + T[node][n]
            if abs(arr // 60 - sp["arrive"]) > 1: bad(f"{s} {sp['id']} arrival {sp['arrive']} vs recomputed {arr//60}")
            begin = max(arr, q["tw_start"] * 60)
            if begin > q["tw_end"] * 60: bad(f"{s} {sp['id']} outside window")
            if q["wave"] and t < q["arrives"] * 60: bad(f"{s} {sp['id']} driver headed there before request existed")
            load += q["parcels"]; parcels += q["parcels"]
            t, node = begin + int((4 + 0.25 * q["parcels"]) * 60), n
        back = t + T[node][0]
        if back > drv["shift_end"] * 60: bad(f"{s} {r['driver']} back at {back/60:.0f} after shift end")
        if load > drv["capacity"]: bad(f"{s} {r['driver']} load {load} > capacity")
    if parcels != st["kpis"]["parcels_collected"]: bad(f"{s} parcel total {parcels} != kpi {st['kpis']['parcels_collected']}")
    print(s, "stops", len(seen), "parcels", parcels)
print("problems:", problems)
