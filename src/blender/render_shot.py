"""Render one 3D shot to PNG frames.

usage: python render_shot.py <shot> [--frames 1,40,80] [--samples 8]
                             [--res 540x960] [--out build/frames]
Frame count comes from config/timeline.json.
"""
import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

import bpy  # noqa: E402

from lib import reset_scene, setup_render  # noqa: E402
from shots import SHOTS  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("shot")
    ap.add_argument("--frames", default="")
    ap.add_argument("--samples", type=int, default=8)
    ap.add_argument("--res", default="540x960")
    ap.add_argument("--out", default=os.path.join(ROOT, "build", "frames"))
    ap.add_argument("--skip-existing", action="store_true")
    a = ap.parse_args()
    tl = json.load(open(os.path.join(ROOT, "config", "timeline.json")))
    shot = next(s for s in tl["shots"] if s["name"] == a.shot)
    nf = shot["frames"]
    scn = reset_scene()
    w, h = map(int, a.res.split("x"))
    setup_render(scn, (w, h), a.samples, motion_blur=False)
    scn.render.use_persistent_data = True
    SHOTS[a.shot](scn, nf)
    scn.frame_start, scn.frame_end = 1, nf
    out = os.path.join(a.out, a.shot)
    os.makedirs(out, exist_ok=True)
    frames = [int(x) for x in a.frames.split(",")] if a.frames else range(1, nf + 1)
    t0 = time.time()
    for f in frames:
        path = os.path.join(out, f"{f:04d}.png")
        if a.skip_existing and os.path.exists(path):
            continue
        scn.frame_set(f)
        scn.render.filepath = path
        bpy.ops.render.render(write_still=True)
    print(f"DONE {a.shot} {len(frames)} frames in {time.time() - t0:.1f}s", flush=True)


if __name__ == "__main__":
    main()
