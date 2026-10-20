"""Thin client for an OSRM routing server (road distances, durations, geometry)."""
import json, time, urllib.request

OSRM = "https://router.project-osrm.org"

def _get(url, tries=3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return json.loads(r.read())
        except Exception as e:  # network hiccup: back off and retry
            if i == tries - 1:
                raise
            time.sleep(2 + 2 * i)

def _coords(points):
    return ";".join(f"{lon:.6f},{lat:.6f}" for lat, lon in points)

def snap(points, chunk=90):
    """Snap points to the road network. Returns [(lat, lon, snap_distance_m)]."""
    out = []
    for i in range(0, len(points), chunk):
        part = points[i:i + chunk]
        pts = part + [part[0]]
        url = f"{OSRM}/table/v1/driving/{_coords(pts)}?sources={';'.join(map(str, range(len(part))))}&destinations={len(part)}"
        res = _get(url)
        for s in res["sources"]:
            lon, lat = s["location"]
            out.append((lat, lon, s["distance"]))
        time.sleep(1)
    return out

def matrix(points, block=45):
    """Full duration (s) and distance (m) matrices via blocked OSRM table calls."""
    n = len(points)
    dur = [[0.0] * n for _ in range(n)]
    dist = [[0.0] * n for _ in range(n)]
    blocks = [list(range(i, min(i + block, n))) for i in range(0, n, block)]
    for src in blocks:
        for dst in blocks:
            idx = src + [j for j in dst if j not in src]
            pts = [points[k] for k in idx]
            s_ix = [idx.index(k) for k in src]
            d_ix = [idx.index(k) for k in dst]
            url = (f"{OSRM}/table/v1/driving/{_coords(pts)}?sources={';'.join(map(str, s_ix))}"
                   f"&destinations={';'.join(map(str, d_ix))}&annotations=duration,distance")
            res = _get(url)
            for a, i in enumerate(src):
                for b, j in enumerate(dst):
                    dur[i][j] = res["durations"][a][b] or 0.0
                    dist[i][j] = res["distances"][a][b] or 0.0
            time.sleep(1)
    return dur, dist

def route_geometry(points):
    """Road geometry for an ordered list of stops as [[lat, lon], ...]."""
    if len(points) < 2:
        return [[p[0], p[1]] for p in points]
    url = f"{OSRM}/route/v1/driving/{_coords(points)}?overview=simplified&geometries=geojson"
    res = _get(url)
    return [[round(lat, 5), round(lon, 5)] for lon, lat in res["routes"][0]["geometry"]["coordinates"]]
