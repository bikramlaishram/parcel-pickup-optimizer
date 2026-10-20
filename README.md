# Parcel Pickup Planner (demo)

A working demo of automated parcel pickup planning: requests come in, an optimizer assigns them to drivers within customer time windows, and the plan re-solves itself when new requests arrive during the day. The same day is also run through a manual-style plan so the two can be compared.

Everything here uses sample data. Locations are random points in Kyiv placed on real streets. Road distances and drive times come from OpenStreetMap through the OSRM routing engine.

## Result on the sample day

| | Manual-style | Optimized |
|---|---|---|
| Parcels collected (of 1,080) | 992 | 1,073 |
| Pickups served (of 152) | 139 | 148 |
| Express served (of 40) | 39 | 40 |
| Distance driven, km | 755 | 603 |
| Late pickups | 0 | 0 |

On five other generated days the optimized plan collected 4.8% to 10.9% more parcels and drove 2% to 13% less (`python3 src/robustness.py`).

## How it works

1. `src/gen_data.py` builds a sample day: 6 drivers (08:00–17:00, 260-parcel vans), 120 requests known at 07:00 and 32 more arriving at 10:30, 12:30 and 14:00, each with parcels, a time window and a priority. It fetches a road travel-time matrix from OSRM.
2. `src/planner.py` runs the day twice.
   - Manual-style: each driver owns a fixed area around the hub and always goes to the pickup they can reach soonest.
   - Optimized: Google OR-Tools vehicle routing with time windows, capacity and priority weights. It maximizes parcels collected, then minimizes driving. At each wave it re-solves in 10 seconds from the drivers' current positions, locks stops already under way, and adds a cost for moving a stop to another driver so routes stay stable.
3. `src/intake.py` turns free-text customer messages into structured requests. The demo uses a deterministic parser; a production build would use an LLM with a strict JSON schema and keep this parser as a check.
4. `src/export.py`, `src/basemap.py` and `src/build_page.py` produce the interactive page in `out/standalone.html`.
5. `src/verify.py` re-checks every exported route against the raw data: time windows, travel times, shift ends, van capacity, no stop served twice, and no driver heading to a request before it existed.

## Run it

```
pip install ortools pillow
python3 src/gen_data.py      # needs internet for OSRM
python3 src/run.py
python3 src/export.py && python3 src/basemap.py && python3 src/build_page.py
python3 src/verify.py
```

Assumptions: drive times are OSRM free-flow times raised 35% for traffic; each pickup takes 4 minutes plus 15 seconds per parcel. Map tiles and road data: OpenStreetMap contributors (ODbL).

Author: Bikram Laishram
