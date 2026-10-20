import json
t = open("src/dashboard_template.html").read()
data = open("out/dashboard_data.json").read()
bm = json.load(open("out/basemap.json"))
t = t.replace("__DATA__", data).replace("__BASEMAP__", json.dumps(bm))
# self-contained page served by GitHub Pages and opened locally
open("index.html", "w").write('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"></head><body style="margin:0">' + t + "</body></html>")
print(len(t)//1024, "KB")
