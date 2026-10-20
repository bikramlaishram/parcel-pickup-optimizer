"""Fetch a small set of OpenStreetMap tiles once and stitch a static basemap for the demo page.
Map data and tiles: OpenStreetMap contributors (ODbL)."""
import json, math, io, urllib.request, time, base64
from PIL import Image, ImageEnhance

Z = 13
def px(lat, lon, z=Z):
    n = 256 * 2 ** z
    x = (lon + 180) / 360 * n
    y = (1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * n
    return x, y

d = json.load(open("out/dashboard_data.json"))
lats = [r["lat"] for r in d["requests"]] + [d["depot"]["lat"]]
lons = [r["lon"] for r in d["requests"]] + [d["depot"]["lon"]]
for s in d["strategies"].values():
    for r in s["routes"]:
        lats += [p[0] for p in r["geometry"]]; lons += [p[1] for p in r["geometry"]]
x0, y0 = px(max(lats), min(lons)); x1, y1 = px(min(lats), max(lons))
pad = 40; x0, y0, x1, y1 = int(x0 - pad), int(y0 - pad), int(x1 + pad), int(y1 + pad)
img = Image.new("RGB", (x1 - x0, y1 - y0))
for tx in range(x0 // 256, x1 // 256 + 1):
    for ty in range(y0 // 256, y1 // 256 + 1):
        req = urllib.request.Request(f"https://tile.openstreetmap.org/{Z}/{tx}/{ty}.png",
                                     headers={"User-Agent": "parcel-pickup-demo/1.0 (one-off static demo render)"})
        tile = Image.open(io.BytesIO(urllib.request.urlopen(req, timeout=30).read())).convert("RGB")
        img.paste(tile, (tx * 256 - x0, ty * 256 - y0)); time.sleep(0.3)
img = ImageEnhance.Color(img).enhance(0.35)          # mute colours so routes stand out
buf = io.BytesIO(); img.save(buf, "JPEG", quality=72, optimize=True)
json.dump({"zoom": Z, "x0": x0, "y0": y0, "w": x1 - x0, "h": y1 - y0,
           "img": "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()}, open("out/basemap.json", "w"))
img.save("out/basemap_preview.jpg")
print(img.size, len(buf.getvalue()) // 1024, "KB")
