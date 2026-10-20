import json, sys, time
sys.path.insert(0, "src")
from planner import Day, run_day, kpis
day = Day()
res = {}
for strat in ["baseline", "optimized"]:
    t = time.time()
    final, events, snaps = run_day(day, strat)
    k = kpis(day, final)
    res[strat] = {"final": final, "events": events, "snapshots": snaps, "kpis": k}
    print(strat, round(time.time() - t, 1), "s", k)
json.dump(res, open("out/results.json", "w"))
