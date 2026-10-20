"""Generate a reproducible synthetic day of parcel pickup requests for a demo city.

Everything here is sample data. Coordinates are random points in Kyiv snapped to
the road network; customer names are generic placeholders.
"""
import json, random, math, sys
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from osrm import snap, matrix

import os
SEED = int(os.environ.get("SEED", 7))
OUT = os.environ.get("OUT", "data/day.json")
random.seed(SEED)
DEPOT = (50.4275, 30.6420)          # demo hub on the left bank
BBOX = (50.385, 50.515, 30.395, 30.665)
N_INITIAL, WAVES = 120, [(10 * 60 + 30, 10), (12 * 60 + 30, 12), (14 * 60, 10)]
DRIVERS = [
    {"id": f"D{i+1}", "name": n, "shift_start": 8 * 60, "shift_end": 17 * 60, "capacity": 260}
    for i, n in enumerate(["Driver 1", "Driver 2", "Driver 3", "Driver 4", "Driver 5", "Driver 6"])
]
KINDS = ["E-commerce seller", "Pharmacy", "Print shop", "Electronics store", "Florist",
         "Bookshop", "Clothing boutique", "Auto parts", "Cosmetics shop", "Home goods"]
WINDOWS = [(9 * 60, 12 * 60), (12 * 60, 15 * 60), (14 * 60, 17 * 60), (9 * 60, 17 * 60),
           (10 * 60, 13 * 60), (13 * 60, 16 * 60)]

def candidate():
    return (random.uniform(BBOX[0], BBOX[1]), random.uniform(BBOX[2], BBOX[3]))

total = N_INITIAL + sum(n for _, n in WAVES)
cands = [candidate() for _ in range(int(total * 1.5))]
snapped = [p for p in snap(cands) if p[2] < 120]
assert len(snapped) >= total, len(snapped)
pts = [(round(a, 6), round(b, 6)) for a, b, _ in snapped[:total]]

def parcels():
    return max(1, min(30, int(random.lognormvariate(1.9, 0.7))))

reqs = []
k = 0
for i in range(N_INITIAL):
    lo, hi = random.choice(WINDOWS)
    reqs.append({"id": f"R{k+1:03d}", "arrives": 7 * 60, "wave": 0, "lat": pts[k][0], "lon": pts[k][1],
                 "parcels": parcels(), "tw_start": lo, "tw_end": hi,
                 "priority": "express" if random.random() < 0.18 else "standard",
                 "customer": f"{random.choice(KINDS)} #{k+1:03d}"})
    k += 1
for w, (t, n) in enumerate(WAVES, start=1):
    for _ in range(n):
        start = max(t + 30, random.choice([t + 30, t + 60, t + 90]))
        start = int(math.ceil(start / 30) * 30)
        end = min(17 * 60, start + random.choice([90, 120, 180]))
        reqs.append({"id": f"R{k+1:03d}", "arrives": t, "wave": w, "lat": pts[k][0], "lon": pts[k][1],
                     "parcels": parcels(), "tw_start": start, "tw_end": end,
                     "priority": "express" if random.random() < 0.35 else "standard",
                     "customer": f"{random.choice(KINDS)} #{k+1:03d}"})
        k += 1

points = [DEPOT] + [(r["lat"], r["lon"]) for r in reqs]
dur, dist = matrix(points)
json.dump({"city": "Kyiv (demo city, synthetic requests)", "depot": {"lat": DEPOT[0], "lon": DEPOT[1]},
           "drivers": DRIVERS, "requests": reqs, "waves": [t for t, _ in WAVES],
           "duration_s": dur, "distance_m": dist}, open(OUT, "w"))
print("requests", len(reqs), "parcels", sum(r["parcels"] for r in reqs))
