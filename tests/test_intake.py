import random
import pytest
from intake import compose, parse, hhmm, TEMPLATES

REQ = {"customer": "Pharmacy #042", "parcels": 7, "tw_start": 9 * 60, "tw_end": 12 * 60 + 30,
       "priority": "standard", "lat": 50.45012, "lon": 30.52341}


def test_hhmm():
    assert hhmm(0) == "00:00"
    assert hhmm(9 * 60 + 5) == "09:05"


@pytest.mark.parametrize("seed", range(20))
@pytest.mark.parametrize("priority", ["standard", "express"])
def test_round_trip(seed, priority):
    req = {**REQ, "priority": priority}
    p = parse(compose(req, random.Random(seed)))
    for k in ("customer", "parcels", "tw_start", "tw_end", "priority"):
        assert p[k] == req[k], k
    assert p["lat"] == pytest.approx(req["lat"], abs=1e-5)
    assert p["lon"] == pytest.approx(req["lon"], abs=1e-5)


def test_every_template_parses():
    for t in TEMPLATES:
        rnd = random.Random(0)
        rnd.choice = lambda seq, t=t: t if seq is TEMPLATES else seq[0]
        assert parse(compose(REQ, rnd))["parcels"] == 7


def test_round_trip_on_sample_day(root):
    import json
    day = json.load(open("data/day.json"))
    rnd = random.Random(1)
    for r in day["requests"]:
        p = parse(compose(r, rnd))
        assert (p["customer"], p["parcels"], p["tw_start"], p["tw_end"], p["priority"]) == \
               (r["customer"], r["parcels"], r["tw_start"], r["tw_end"], r["priority"])
