"""Builds output/live_preview.html: render progress + latest raw vs edited frame.

    python tools/live_preview.py --project projects/eastern_counties
"""
import base64
import io
import json
import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
proj = sys.argv[sys.argv.index("--project") + 1]
TL = json.load(open(os.path.join(ROOT, proj, "config", "timeline.json")))
RD = os.path.join(ROOT, TL["renders"])
FPS, H = TL["fps"], 6
sys.path.insert(0, os.path.join(ROOT, "src", "compose"))
sys.argv = [sys.argv[0], "--project", proj]
import compose as C  # noqa: E402
from PIL import Image  # noqa: E402


def b64(im, w=400):
    im = im.convert("RGB")
    im = im.resize((w, int(im.height * w / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=82)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


rows, done_total, need_total = [], 0, 0
latest = None
for s in TL["shots"]:
    n = round((s["end"] - s["start"]) * FPS) + 2 * H
    need = len(set(range(1, n + 1, s.get("step", 1))) | {n})
    d = os.path.join(RD, s["id"])
    have = sorted(f for f in os.listdir(d) if f.endswith(".png")) if os.path.isdir(d) else []
    done_total += min(len(have), need)
    need_total += need
    if have:
        latest = (s, int(have[-1][:4]))
    rows.append((s, len(have), need))

panes = ""
if latest:
    s, f = latest
    t = min(s["end"] - 0.01, max(s["start"], s["start"] + (f - H - 1) / FPS))
    raw = Image.open(os.path.join(RD, s["id"], f"{f:04d}.png"))
    try:
        fin = C.compose_frame(round(t * FPS))
    except FileNotFoundError:
        fin = raw
    panes = f"""<div class=panes>
<figure><figcaption>RAW 3D RENDER</figcaption><img src="{b64(raw)}"></figure>
<figure><figcaption>FINAL EDIT · {t:.1f}s</figcaption><img src="{b64(fin)}"></figure></div>
<p class=sub>Latest: shot <b>{s['id']}</b> frame {f} — {s['desc']}</p>"""

thumbs = ""
for s, have, need in rows:
    if have >= need:
        mid = (s["start"] + s["end"]) / 2
        try:
            thumbs += f'<figure class=th><img src="{b64(C.compose_frame(round(mid * FPS)), 160)}"><figcaption>{s["id"]}</figcaption></figure>'
        except FileNotFoundError:
            pass

bars = "".join(
    f'<div class=row><span class=id>{s["id"]}</span><div class=bar><i style="width:{100 * min(h, n) / n:.0f}%"></i></div>'
    f'<span class=n>{min(h, n)}/{n}</span><span class=d>{s["desc"]}</span></div>' for s, h, n in rows)
pct = 100 * done_total / need_total
html = f"""<!doctype html><html><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Live Render Preview</title><style>
:root{{--bg:#0d1017;--fg:#f2f2f2;--mut:#9aa0aa;--acc:#f76a32;--card:#171b24}}
body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.4 system-ui,sans-serif;padding:16px}}
h1{{font-size:20px;margin:0 0 4px}}.sub{{color:var(--mut);margin:6px 0 14px}}
.panes{{display:grid;grid-template-columns:1fr 1fr;gap:10px}}figure{{margin:0;background:var(--card);border-radius:12px;overflow:hidden}}
figure img{{width:100%;display:block}}figcaption{{font-weight:700;font-size:12px;letter-spacing:.08em;padding:8px 10px}}
.total{{height:10px;background:#252a35;border-radius:6px;overflow:hidden;margin:8px 0 2px}}.total i{{display:block;height:100%;background:var(--acc)}}
.row{{display:grid;grid-template-columns:42px 1fr 70px;gap:8px;align-items:center;margin:5px 0}}.row .d{{grid-column:2/4;color:var(--mut);font-size:12px;margin-top:-4px}}
.bar{{height:8px;background:#252a35;border-radius:5px;overflow:hidden}}.bar i{{display:block;height:100%;background:var(--acc)}}
.id{{font-weight:700}}.n{{color:var(--mut);font-size:12px;text-align:right}}
.thumbs{{display:flex;flex-wrap:wrap;gap:8px}}.th{{width:110px}}
</style></head><body>
<h1>Eastern Counties Paving — live preview</h1>
<div class=total><i style="width:{pct:.0f}%"></i></div><p class=sub>{done_total} / {need_total} frames rendered ({pct:.0f}%)</p>
{panes}
<h2 style="font-size:16px;margin:18px 0 6px">Finished shots</h2><div class=thumbs>{thumbs or '<span class=sub>none yet</span>'}</div>
<h2 style="font-size:16px;margin:18px 0 6px">Shots</h2>{bars}
</body></html>"""
out = os.path.join(ROOT, "output", "live_preview.html")
os.makedirs(os.path.dirname(out), exist_ok=True)
open(out, "w").write(html)
print(out, f"{pct:.0f}%")
