"""Re-run the whole comparison on several independently generated sample days."""
import json, os, subprocess, sys
sys.path.insert(0, "src")
from planner import Day, run_day, kpis
rows = []
for seed in [11, 23, 42, 77, 101]:
    path = f"data/day_seed{seed}.json"
    if not os.path.exists(path):
        subprocess.run([sys.executable, "src/gen_data.py"], env={**os.environ, "SEED": str(seed), "OUT": path}, check=True)
    day = Day(path)
    k = {s: kpis(day, run_day(day, s)[0]) for s in ["baseline", "optimized"]}
    b, o = k["baseline"], k["optimized"]
    row = {"seed": seed, "parcels_total": b["parcels_total"], "base": b["parcels_collected"], "opt": o["parcels_collected"],
           "gain_pct": round((o["parcels_collected"] / b["parcels_collected"] - 1) * 100, 1),
           "km_saved_pct": round((1 - o["km"] / b["km"]) * 100, 1), "express": (b["express_served"], o["express_served"], o["express_total"]),
           "late": (b["late_stops"], o["late_stops"])}
    print(row, flush=True); rows.append(row)
json.dump(rows, open("out/robustness.json", "w"), indent=1)
