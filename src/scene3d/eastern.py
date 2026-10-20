"""Eastern Counties Paving - shot definitions.

    python src/scene3d/eastern.py --shot e1 --pct 50 --samples 10 --out renders/eastern_counties/e1

Same harness conventions as shots.py: frames 1..N, N = duration*fps + 2*HANDLE.
"""
import argparse
import json
import math
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
import bpy  # noqa: E402

import lib as L  # noqa: E402
from lib import rad  # noqa: E402
from shots import focus_empty, idle  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TL = json.load(open(os.path.join(ROOT, "projects", "eastern_counties", "config", "timeline.json")))
FPS = TL["fps"]
HANDLE = 6
SHOTS = {}

DRIVE_O = (-3.3, -8.7, 0.0)
DRIVE_W, DRIVE_D = 6.6, 6.0
DMG_C = (-0.5, -6.6)
NEW_COLS = ("#a5523a", "#7b3f2e", "#c27a47", "#55504f")


def shot(fn):
    SHOTS[fn.__name__] = fn
    return fn


def span(shot_id):
    s = next(x for x in TL["shots"] if x["id"] == shot_id)
    return s, round((s["end"] - s["start"]) * FPS) + 2 * HANDLE


def F(t0, t):
    return round((t - t0) * FPS) + HANDLE + 1


# ---------------------------------------------------------------------------
# sets
# ---------------------------------------------------------------------------

def home_set(state="damaged", neighbours=True, extra_lights=True):
    L.build_ground()
    h = L.build_house(damage_level=0, new_roof=False, lit=(1, 1, 0, 1), brick="#8f4a2e", door="#24384a")
    if neighbours:
        L.build_house("nb", loc=(6.45, 0, 0), lit=(0, 1, 1, 0), detail=False, brick="#7e3624", door="#5c1f24")
        L.build_house("nb2", loc=(-8.2, 0.6, 0), lit=(1, 0, 0, 1), detail=False, brick="#7b3a28", door="#2c4a2c")
    L.build_background_street(y=16)
    L.bokeh_lights(70, center=(0, 34, 5), spread=(40, 8, 6))
    L.area_light("moon", (-6, 20, 18), (0, 0, 4), 4000, "#7c9cff", size=10)
    hedge = L.mat_knit("hedge_day", "#3d7a2f", scale=30)
    hedge.node_tree.nodes["Principled BSDF"].inputs["Sheen Weight"].default_value = 0.0
    for x in (-3.75, 3.75):
        L.rbox(f"hedge{x}", (0.6, 6.2, 1.1), 0.25, hedge, (x, -5.7, 0.55))
    dw = None
    if state == "damaged":
        dw = L.build_driveway("drive", DRIVE_O, DRIVE_W, DRIVE_D, worn=True, seed=4,
                              damage=dict(centre=DMG_C, radius=1.6, sink=0.1, missing=0.1, weeds=9, split=0.35))
    elif state in ("new", "prep", "bare"):
        dw = L.build_driveway("drive", DRIVE_O, DRIVE_W, DRIVE_D, cols=NEW_COLS, seed=5)
        if state in ("prep", "bare"):
            # street-side rows not laid yet: sand bed shows
            gone = [b for b in dw["blocks"] if state == "bare" or b["row"] < 13]
            dw["blocks"] = [b for b in dw["blocks"] if b not in gone]
            for b in gone:
                bpy.data.objects.remove(b)
    return h, dw


def key_rim(target, key=(-4.5, -11, 5), key_e=520, rim=(4.0, -3.3, 4.5), rim_e=420):
    L.area_light("key", key, target, key_e, "#ffc596", size=3.0)
    L.area_light("rimC", rim, target, rim_e, "#86a8ff", size=2.5)


def kneel(ch):
    ch.hips.location.z = 0.36
    for sd in ("L", "R"):
        ch.leg[sd].rotation_euler = rad(-12, 0, 0)
        ch.knee[sd].rotation_euler = rad(92, 0, 0)


# ---------------------------------------------------------------------------
# Scene 1 - cracks, sinking, wear
# ---------------------------------------------------------------------------
@shot
def e1():
    sh, n = span("e1")
    t0 = sh["start"]
    home_set("damaged")
    a = L.Character("linda", "linda", loc=(-0.6, -5.15, 0), rot_z=math.radians(8))
    a.rest_pose(1)
    idle(a, 1, n, seed=3)
    a.pose_head(1, nod=24, tilt=4)
    a.look(1, 0.1, -1.0)
    a.brows_key(1, worry=1.0, raise_=0.3)
    a.set_mouth(-0.6, 1, open_=0.2)
    f = F(t0, 2.6)
    a.pose_arm("R", f - 8, fwd=4, out=8, elbow=10)
    a.pose_arm("R", f + 4, fwd=30, out=10, elbow=135, elbow_side=-20)
    a.pose_arm("R", n, fwd=32, out=10, elbow=135, elbow_side=-20)
    a.pose_head(F(t0, 3.3), nod=22, tilt=6)
    a.pose_head(n, nod=10, tilt=-6, turn=-8)
    a.look(n - 15, -0.2, -0.3)
    a.set_mouth(-0.9, F(t0, 3.4), open_=0.8)
    cam = L.camera(lens=42, fstop=0.5)
    fe = focus_empty("fo", [(1, (DMG_C[0], DMG_C[1], 0.05)), (int(n * 0.45), (DMG_C[0], DMG_C[1], 0.05)),
                            (int(n * 0.72), (-0.6, -5.15, 2.4)), (n, (-0.6, -5.15, 2.4))])
    cam.data.dof.focus_object = fe
    L.cam_key(cam, 1, (0.9, -8.9, 0.75), (DMG_C[0], DMG_C[1] + 0.3, 0.0))
    L.cam_key(cam, int(n * 0.42), (0.6, -8.5, 0.95), (DMG_C[0], DMG_C[1] + 0.2, 0.05))
    L.cam_key(cam, int(n * 0.75), (0.2, -10.6, 2.4), (-0.6, -4.6, 2.75))
    L.cam_key(cam, n, (0.1, -10.1, 2.3), (-0.6, -4.6, 2.65))
    key_rim((-0.6, -5.2, 1.8), key=(-3.5, -9, 3.6), key_e=300)
    L.area_light("keyGround", (1.5, -8.5, 2.5), (DMG_C[0], DMG_C[1], 0), 200, "#ffc596", size=2)
    return n


# ---------------------------------------------------------------------------
# Scene 2 - damage worsens
# ---------------------------------------------------------------------------
@shot
def e2():
    sh, n = span("e2")
    t0 = sh["start"]
    h, dw = home_set("damaged")
    cx, cy = DMG_C
    f_go = F(t0, 5.6)
    for b in dw["blocks"]:
        wx, wy = DRIVE_O[0] + b.location.x, DRIVE_O[1] + b.location.y
        d = math.hypot(wx - cx, wy - cy) / 1.9
        if d < 1:
            k = (1 - d) ** 1.2
            b.keyframe_insert("location", frame=f_go)
            b.keyframe_insert("rotation_euler", frame=f_go)
            b.location.z -= 0.09 * k
            b.rotation_euler.x += math.radians(6 * k * (1 if hash(b.name) % 2 else -1))
            b.keyframe_insert("location", frame=F(t0, 7.2))
            b.keyframe_insert("rotation_euler", frame=F(t0, 7.2))
    for o in bpy.data.objects:
        if "_weed" in o.name and o.parent and o.parent.name == "drive":
            L.key(o, "scale", 1, (0.6, 0.6, 0.6))
            L.key(o, "scale", f_go, (0.7, 0.7, 0.7))
            L.key(o, "scale", F(t0, 7.4), (1.5, 1.5, 1.7))
        if "_cr" in o.name and o.parent and o.parent.name == "drive":
            L.key(o, "scale", f_go, (1, 1, 1))
            L.key(o, "scale", F(t0, 7.2), (1.6, 1.3, 1))
    a = L.Character("linda", "linda", loc=(-0.2, -5.0, 0), rot_z=math.radians(-12))
    a.rest_pose(1)
    idle(a, 1, n, seed=7)
    a.pose_head(1, nod=22, tilt=-4)
    a.look(1, 0, -1)
    a.brows_key(1, worry=1.1)
    a.set_mouth(-0.7, 1)
    fw = F(t0, 6.8)
    a.brows_key(fw, worry=1.5, raise_=0.8)
    a.set_mouth(-1.0, fw, open_=1.2)
    a.pose_head(fw, nod=14, tilt=8)
    for sd in ("L", "R"):
        a.pose_arm(sd, fw - 6, fwd=4, out=8, elbow=10)
        a.pose_arm(sd, fw + 4, fwd=30, out=10, elbow=135, elbow_side=-20)
        a.pose_arm(sd, n, fwd=30, out=10, elbow=135, elbow_side=-20)
    a.blink(fw, 4)
    cam = L.camera(lens=36, fstop=0.45)
    fe = focus_empty("fo", [(1, (cx, cy, 0.05)), (fw - 10, (cx, cy, 0.05)), (fw + 6, (-0.2, -5.0, 2.5)),
                            (n, (-0.2, -5.0, 2.5))])
    cam.data.dof.focus_object = fe
    L.cam_key(cam, 1, (cx - 1.2, cy - 2.2, 0.55), (cx, cy + 1.0, 0.6))
    L.cam_key(cam, fw - 8, (cx - 0.9, cy - 2.0, 0.5), (cx, cy + 1.0, 0.75))
    L.cam_key(cam, n, (cx - 0.7, cy - 2.4, 0.45), (-0.2, -5.0, 2.0))
    key_rim((cx, cy + 0.5, 0.8), key=(-3, -9, 3), key_e=260)
    return n


# ---------------------------------------------------------------------------
# Scene 2b - Essex street
# ---------------------------------------------------------------------------
@shot
def e3():
    sh, n = span("e3")
    L.build_ground()
    rnd = random.Random(2)
    bricks = ["#8a3b26", "#7e3624", "#93492c", "#74331f", "#8a4430"]
    doors = ["#1f3b4d", "#5c1f24", "#2c4a2c", "#232323", "#3d2b56"]
    for i in range(-4, 5):
        L.build_house(f"h{i}", loc=(i * 6.45, 0, 0), lit=tuple(rnd.random() < 0.6 for _ in range(4)),
                      detail=abs(i) <= 1, brick=bricks[i % 5], door=doors[i % 5], seed=i + 20)
        if abs(i) <= 2:
            L.build_driveway(f"d{i}", (i * 6.45 - 3.2, -8.4, 0), 6.4, 5.6, seed=i + 40,
                             cols=NEW_COLS if i % 2 else ("#8b8580", "#6d6966", "#a49c92", "#55504f"), border=True)
    for i in range(-4, 5):
        L.build_house(f"o{i}", loc=(i * 6.45 + 3, 22, 0), lit=tuple(rnd.random() < 0.5 for _ in range(4)),
                      detail=False, brick=bricks[(i + 2) % 5])
        bpy.data.objects[f"o{i}"].rotation_euler = rad(0, 0, 180)
    pole = L.mat_basic("pole", "#1a1c20", rough=0.4, metal=0.5)
    glow = L.mat_emission("street_glow", "#ffb35c", 40)
    for i in range(-3, 4):
        x = i * 9.0 + 2
        L.cyl(f"pole{i}", 0.07, 5.5, pole, (x, -9.5, 2.75))
        L.sphere(f"glow{i}", 0.25, glow, (x, -9.5, 5.6), seg=16)
        L.point_light(f"sl{i}", (x, -9.5, 5.3), 300, "#ffb35c", 0.3)
    L.toy_car("car1", (-6.45, -6.0, 0), 0.0, "#8a2b2b")
    L.toy_car("car2", (6.45, -6.2, 0), 0.0, "#2b5a8a")
    L.bokeh_lights(90, center=(0, 60, 8), spread=(60, 15, 8))
    L.area_light("moon", (-10, 30, 25), (0, 0, 4), 6000, "#7c9cff", size=12)
    cam = L.camera(lens=30, fstop=1.6, focus=16.0)
    L.cam_key(cam, 1, (-13, -16, 5.6), (2, -2, 3.6))
    L.cam_key(cam, n, (-9, -16.5, 5.4), (6, -2, 3.4))
    return n


# ---------------------------------------------------------------------------
# Scene 3 - the team arrives
# ---------------------------------------------------------------------------
@shot
def e4():
    sh, n = span("e4")
    t0 = sh["start"]
    home_set("damaged")
    p1 = L.Character("p1", "paver1", loc=(-0.2, -6.0, 0), rot_z=math.radians(10))
    p2 = L.Character("p2", "paver2", loc=(1.6, -5.4, 0), rot_z=math.radians(-20))
    a = L.Character("linda", "linda", loc=(-2.2, -6.5, 0), rot_z=math.radians(45))
    for ch, sd in ((p1, 2), (p2, 7), (a, 4)):
        ch.rest_pose(1)
        idle(ch, 1, n, seed=sd)
    L.tablet("tab", parent=p1.hand["L"], loc=(0.05, -0.12, -0.12), rot=rad(70, 0, -20))
    p1.pose_arm("L", 1, fwd=50, out=8, elbow=70, elbow_side=-30)
    p1.pose_head(1, nod=20, turn=-10)
    p1.look(1, 0, -1)
    p1.set_mouth(0.1, 1)
    f_up = F(t0, 12.6)
    p1.pose_head(f_up, nod=20, turn=-10)
    p1.pose_head(f_up + 12, nod=2, turn=-30, tilt=4)
    p1.look(f_up + 10, -0.6, 0)
    p1.set_mouth(0.8, f_up + 14)
    p1.brows_key(f_up + 14, raise_=0.6)
    f_nod = F(t0, 14.5)
    p1.pose_head(f_nod, nod=10, turn=-28, tilt=4)
    p1.pose_head(f_nod + 6, nod=-2, turn=-28, tilt=4)
    L.mallet("mal", parent=p2.hand["R"], loc=(0, -0.02, -0.08), rot=rad(80, 0, 0))
    p2.pose_arm("R", 1, fwd=20, out=10, elbow=40)
    p2.pose_head(1, nod=16, turn=10)
    p2.look(1, 0, -0.8)
    p2.set_mouth(0.3, 1)
    p2.pose_head(f_up + 8, nod=0, turn=-10, tilt=5)
    p2.look(f_up + 8, -0.4, 0)
    f_tu = F(t0, 14.5)
    p2.pose_arm("L", f_tu - 10, fwd=6, out=10, elbow=15)
    p2.pose_arm("L", f_tu, fwd=40, out=10, elbow=95, elbow_side=-20)
    p2.pose_arm("L", n, fwd=40, out=10, elbow=95, elbow_side=-20)
    p2.set_mouth(0.95, f_tu)
    a.pose_head(1, turn=4, nod=-2)
    a.look(1, 0.7, 0.1)
    a.brows_key(1, worry=0.7)
    a.set_mouth(-0.3, 1)
    a.brows_key(f_nod, worry=0.1, raise_=0.5)
    a.set_mouth(0.6, f_nod)
    cam = L.camera(lens=45, fstop=0.7)
    fe = focus_empty("fo", [(1, (0.0, -6.0, 2.4)), (n, (0.0, -6.0, 2.4))])
    cam.data.dof.focus_object = fe
    L.cam_key(cam, 1, (-0.4, -14.6, 3.1), (-0.3, -5.0, 3.6))
    L.cam_key(cam, n, (-0.5, -12.9, 2.6), (-0.3, -5.4, 3.0))
    key_rim((0, -6, 2.0))
    return n


# ---------------------------------------------------------------------------
# Scene 4 - careful laying, benefit cards above
# ---------------------------------------------------------------------------
@shot
def e5():
    sh, n = span("e5")
    t0 = sh["start"]
    h, dw = home_set("prep", neighbours=False)
    # blocks of row 12 at x in a window land one by one in front of the paver
    row = [b for b in dw["blocks"] if b["row"] == 13]
    row.sort(key=lambda b: b.location.x)
    target = [b for b in row if 2.2 < b.location.x < 4.4]
    p = L.Character("p2", "paver2", loc=(DRIVE_O[0] + 3.2, DRIVE_O[1] + 13 * L.BLOCK_W - 0.55, 0), rot_z=math.radians(180))
    kneel(p)
    p.rest_pose(1)
    idle(p, 1, n, seed=12, sway=0.4)
    p.pose_body(1, lean=-24)
    L.mallet("mal", parent=p.hand["R"], loc=(0, -0.02, -0.08), rot=rad(80, 0, 0))
    p.pose_head(1, nod=30)
    p.look(1, 0, -1)
    p.brows_key(1, worry=-0.4)
    for i, b in enumerate(target):
        fl = F(t0, 15.5 + i * 0.75)
        base = b.location.copy()
        b.keyframe_insert("location", frame=fl)
        b.keyframe_insert("scale", frame=fl)
        b.location = (base.x, base.y + 0.25, base.z + 0.45)
        b.scale = (0.001, 0.001, 0.001)
        b.keyframe_insert("location", frame=fl - 10)
        b.keyframe_insert("scale", frame=fl - 10)
        b.scale = (1, 1, 1)
        b.location = (base.x, base.y + 0.15, base.z + 0.35)
        b.keyframe_insert("location", frame=fl - 8)
        b.keyframe_insert("scale", frame=fl - 8)
        b.location = base
    # left hand places, right taps with the mallet
    f = 1
    up = True
    while f <= n:
        p.pose_arm("R", f, fwd=95 if up else 55, out=14, elbow=80 if up else 30, elbow_side=-10)
        p.pose_arm("L", f, fwd=60, out=8, elbow=30, elbow_side=-20)
        f += 11
        up = not up
    f_sm = F(t0, 18.6)
    p.pose_head(f_sm, nod=28)
    p.pose_head(f_sm + 12, nod=4, turn=14, tilt=-6)
    p.look(f_sm + 10, 0.3, 0)
    p.set_mouth(0.85, f_sm + 12)
    p.brows_key(f_sm + 12, worry=0, raise_=0.5)
    px, py = p.root.location.x, p.root.location.y
    L.block_pallet("pal", (px + 1.9, py - 1.6, 0))
    cam = L.camera(lens=38, fstop=0.5)
    fe = focus_empty("fo", [(1, (px, py + 0.5, 1.0)), (n, (px, py + 0.4, 1.5))])
    cam.data.dof.focus_object = fe
    L.cam_key(cam, 1, (px - 1.6, py + 3.6, 1.5), (px, py + 0.2, 1.25))
    L.cam_key(cam, n, (px - 1.2, py + 3.1, 1.4), (px, py + 0.2, 1.3))
    L.area_light("key", (px - 2.5, py + 3, 3.5), (px, py, 1), 280, "#ffc596", size=2)
    L.area_light("rimC", (px + 2.5, py - 2.5, 3.5), (px, py, 1), 380, "#86a8ff", size=2)
    return n


# ---------------------------------------------------------------------------
# Scene 4b/5 - seasonal bookings (panel background) and weather turning
# ---------------------------------------------------------------------------
@shot
def e6a():
    sh, n = span("e6a")
    home_set("prep")
    L.block_pallet("pal", (2.2, -7.6, 0))
    L.wheelbarrow("wb", (-1.8, -7.4, 0), math.radians(30))
    p1 = L.Character("p1", "paver1", loc=(0.6, -6.6, 0), rot_z=math.radians(-15))
    p1.rest_pose(1)
    idle(p1, 1, n, seed=21)
    p1.set_mouth(0.4, 1)
    cam = L.camera(lens=40, fstop=0.35, focus=5.0)
    L.cam_key(cam, 1, (0.6, -13.5, 2.6), (0.3, -5, 2.6))
    L.cam_key(cam, n, (0.3, -13.0, 2.6), (0.3, -5, 2.6))
    key_rim((0.5, -6.6, 2.0))
    return n


@shot
def e6b():
    sh, n = span("e6b")
    t0 = sh["start"]
    home_set("prep")
    L.block_pallet("pal", (2.6, -5.6, 0))
    L.wheelbarrow("wb", (-2.4, -7.9, 0), math.radians(25))
    for i, x in enumerate((-3.0, 3.0)):
        L.traffic_cone(f"cone{i}", (x, -8.9, 0))
    p1 = L.Character("p1", "paver1", loc=(-0.2, -6.3, 0), rot_z=math.radians(-10))
    p2 = L.Character("p2", "paver2", loc=(2.7, -6.6, 0), rot_z=math.radians(210))
    kneel(p2)
    a = L.Character("linda", "linda", loc=(-2.3, -5.3, 0), rot_z=math.radians(25))
    for ch, sd in ((p1, 31), (p2, 32), (a, 33)):
        ch.rest_pose(1)
        idle(ch, 1, n, seed=sd)
    p2.pose_body(1, lean=-20)
    L.mallet("mal", parent=p2.hand["R"], loc=(0, -0.02, -0.08), rot=rad(80, 0, 0))
    f = 1
    up = True
    while f <= n:
        p2.pose_arm("R", f, fwd=95 if up else 55, out=14, elbow=80 if up else 30)
        f += 10
        up = not up
    p1.pose_arm("R", 1, fwd=150, out=20, elbow=10)
    p1.pose_head(1, nod=-25, turn=10)
    p1.look(1, 0.2, 1)
    fw = F(t0, 25.5)
    p1.pose_arm("R", fw, fwd=150, out=20, elbow=10)
    p1.pose_arm("R", fw + 12, fwd=8, out=10, elbow=20)
    p1.pose_head(fw + 10, nod=0, turn=-10)
    p1.look(fw + 10, -0.3, 0)
    p1.set_mouth(0.7, fw + 12)
    a.pose_head(1, nod=-20, turn=-6)
    a.look(1, 0, 1)
    a.brows_key(1, worry=0.6)
    a.pose_head(fw + 8, nod=0, turn=6)
    a.look(fw + 8, 0.4, 0)
    a.set_mouth(0.5, fw + 12)
    # wind-blown autumn leaves
    rnd = random.Random(9)
    leafm = [L.mat_basic(f"leaf{c}", c, rough=0.6, sss=0.2) for c in ("#c4642a", "#d99a2b", "#8f3a1c")]
    for i in range(36):
        lf = L.sphere(f"leaf{i}", 0.07, leafm[i % 3], scale=(1, 0.6, 0.12), seg=12)
        y = rnd.uniform(-9, -3)
        z0 = rnd.uniform(1.5, 6.0)
        st = rnd.randint(1, n // 2)
        L.key(lf, "location", 1, (-9, y, z0))
        L.key(lf, "location", st, (-8 + rnd.uniform(-1, 1), y, z0))
        L.key(lf, "location", min(n, st + rnd.randint(40, 70)), (rnd.uniform(4, 9), y + rnd.uniform(-1, 1), max(0.05, z0 - rnd.uniform(1, 3))))
        L.key(lf, "rotation_euler", 1, (0, 0, 0))
        L.key(lf, "rotation_euler", n, (rnd.uniform(5, 15), rnd.uniform(5, 15), rnd.uniform(0, 6)))
    cam = L.camera(lens=36, fstop=0.8)
    fe = focus_empty("fo", [(1, (0.2, -6.9, 1.8)), (n, (0.2, -6.9, 1.8))])
    cam.data.dof.focus_object = fe
    L.cam_key(cam, 1, (0.4, -12.8, 3.2), (0.0, -5.0, 2.7))
    L.cam_key(cam, n, (0.6, -14.0, 3.6), (0.0, -5.0, 2.9))
    key_rim((0, -6.5, 1.8))
    return n


# ---------------------------------------------------------------------------
# Scene 6 - transformation, patio, precision repair
# ---------------------------------------------------------------------------
@shot
def e7a():
    sh, n = span("e7a")
    t0 = sh["start"]
    h, dw = home_set("new")
    L.reveal_rows(dw["blocks"], F(t0, 27.6), per_row=2, drop=0.9, dur=8, reverse=True)
    cam = L.camera(lens=34, fstop=1.2)
    fe = focus_empty("fo", [(1, (0, -5.7, 0.2)), (n, (0, -5.7, 0.2))])
    cam.data.dof.focus_object = fe
    L.cam_key(cam, 1, (3.8, -13.0, 7.6), (-0.2, -5.0, 0.8))
    L.cam_key(cam, n, (2.6, -13.6, 6.6), (-0.2, -5.0, 1.2))
    L.area_light("key", (-4, -11, 7), (0, -5.7, 0), 600, "#ffc596", size=3)
    L.area_light("fillB", (3, -3.5, 5), (0, -5.7, 0), 250, "#ffc596", size=3)
    return n


@shot
def e7b():
    sh, n = span("e7b")
    L.build_ground()
    L.build_house(damage_level=0, lit=(1, 1, 1, 1), brick="#8f4a2e")
    grass = L.mat_fabric("grass2", "#2a4a22", rough=0.9, scale=60)
    L.rbox("lawn", (12, 10, 0.1), 0.03, grass, (0, -8, 0.0))
    pt = L.build_patio("patio", (-3.0, -7.4, 0.02), 6.0, 4.6)
    L.reveal_rows(pt["slabs"], 2, per_row=4, drop=0.8, dur=6, reverse=True)
    pot = L.mat_basic("pot_t", "#a5532f", rough=0.6)
    bush = L.mat_knit("bush", "#2f5a2a", scale=26)
    for x in (-3.5, 3.5):
        L.cyl(f"pot{x}", 0.32, 0.6, pot, (x, -3.6, 0.3), r2=0.25)
        L.sphere(f"bush{x}", 0.45, bush, (x, -3.6, 0.9))
    cam = L.camera(lens=34, fstop=1.2)
    fe = focus_empty("fo", [(1, (0, -5.2, 0.1)), (n, (0, -5.2, 0.1))])
    cam.data.dof.focus_object = fe
    L.cam_key(cam, 1, (-1.4, -10.6, 4.4), (0.0, -4.9, 0.9))
    L.cam_key(cam, n, (-0.9, -10.4, 4.1), (0.0, -4.9, 1.0))
    L.area_light("key", (-4, -10, 6), (0, -5, 0), 520, "#ffc596", size=3)
    L.area_light("moon", (-6, 20, 18), (0, 0, 4), 3000, "#7c9cff", size=10)
    L.bokeh_lights(40, center=(0, 30, 5), spread=(30, 6, 4))
    return n


@shot
def e7c():
    sh, n = span("e7c")
    h, dw = home_set("new", neighbours=False)
    # one block lifted, then tapped down flush
    b = min(dw["blocks"], key=lambda o: math.hypot(DRIVE_O[0] + o.location.x - 0.0, DRIVE_O[1] + o.location.y + 6.0))
    base = b.location.copy()
    L.key(b, "location", 1, (base.x, base.y, base.z + 0.06))
    L.key(b, "rotation_euler", 1, (math.radians(5), math.radians(-4), b.rotation_euler.z))
    for i, f in enumerate((10, 20, 30)):
        L.key(b, "location", f, (base.x, base.y, base.z + 0.06 * (1 - (i + 1) / 3)))
        L.key(b, "rotation_euler", f, (math.radians(5 * (1 - (i + 1) / 3)), math.radians(-4 * (1 - (i + 1) / 3)), b.rotation_euler.z))
    bx, by = DRIVE_O[0] + base.x, DRIVE_O[1] + base.y
    p = L.Character("p1", "paver1", loc=(bx + 0.1, by + 0.75, 0), rot_z=math.radians(8))
    kneel(p)
    p.rest_pose(1)
    p.pose_body(1, lean=-26)
    L.mallet("mal", parent=p.hand["R"], loc=(0, -0.02, -0.08), rot=rad(80, 0, 0))
    p.pose_head(1, nod=34)
    p.look(1, 0, -1)
    p.brows_key(1, worry=-0.5)
    p.pose_arm("L", 1, fwd=50, out=12, elbow=25)
    for i, f in enumerate(range(1, n + 1, 5)):
        p.pose_arm("R", f, fwd=88 if i % 2 == 0 else 60, out=10, elbow=70 if i % 2 == 0 else 35)
    cam = L.camera(lens=40, fstop=0.5)
    fe = focus_empty("fo", [(1, (bx, by + 0.2, 0.3)), (n, (bx, by + 0.2, 0.3))])
    cam.data.dof.focus_object = fe
    L.cam_key(cam, 1, (bx + 0.35, by - 1.5, 0.42), (bx, by + 0.5, 0.75))
    L.cam_key(cam, n, (bx + 0.3, by - 1.35, 0.4), (bx, by + 0.5, 0.75))
    L.area_light("key", (bx - 1.5, by - 1.5, 2.0), (bx, by, 0), 120, "#ffc596", size=1.5)
    L.area_light("rimC", (bx + 1.5, by + 2, 2.5), (bx, by, 0.5), 200, "#86a8ff", size=1.5)
    return n


# ---------------------------------------------------------------------------
# Scene 6c - finished driveway, team + delighted Linda
# ---------------------------------------------------------------------------
@shot
def e8():
    sh, n = span("e8")
    t0 = sh["start"]
    home_set("new")
    p1 = L.Character("p1", "paver1", loc=(0.2, -6.4, 0), rot_z=math.radians(-6))
    p2 = L.Character("p2", "paver2", loc=(1.9, -6.0, 0), rot_z=math.radians(-20))
    a = L.Character("linda", "linda", loc=(-1.7, -6.9, 0), rot_z=math.radians(20))
    for ch, sd in ((p1, 51), (p2, 52), (a, 53)):
        ch.rest_pose(1)
        idle(ch, 1, n, seed=sd)
        ch.set_mouth(0.85, 1)
        ch.brows_key(1, raise_=0.4)
    a.pose_head(1, nod=20, turn=-4)
    a.look(1, 0, -1)
    a.set_mouth(0.5, 1, open_=0.3)
    ft = F(t0, 34.0)
    a.pose_head(ft, nod=18)
    a.pose_head(ft + 12, nod=0, turn=6, tilt=-6)
    a.look(ft + 10, 0.1, 0)
    a.set_mouth(1.0, ft + 12)
    a.pose_arm("R", ft + 4, fwd=10, out=8, elbow=15)
    a.pose_arm("R", ft + 16, fwd=40, out=-10, elbow=110, elbow_side=-40)
    a.pose_arm("R", n, fwd=40, out=-10, elbow=110, elbow_side=-40)
    p1.pose_head(1, nod=-2, turn=12)
    p1.look(1, 0.4, 0)
    w0 = F(t0, 33.3)
    p2.pose_arm("R", w0, fwd=10, out=10, elbow=10)
    for i in range(6):
        p2.pose_arm("R", w0 + 8 + i * 7, fwd=30, out=95, elbow=60 + (25 if i % 2 else -10))
    p2.pose_arm("R", w0 + 60, fwd=12, out=10, elbow=15)
    cam = L.camera(lens=42, fstop=0.8)
    fe = focus_empty("fo", [(1, (0, -6.4, 2.3)), (n, (0, -6.4, 2.3))])
    cam.data.dof.focus_object = fe
    L.cam_key(cam, 1, (0.4, -12.0, 6.8), (0.0, -5.0, 1.8))
    L.cam_key(cam, n, (0.1, -14.0, 2.9), (0.0, -5.6, 2.9))
    key_rim((0, -6.4, 2.0), key_e=560)
    return n


# ---------------------------------------------------------------------------
# Scene 6d - background for the paving check panel + its still
# ---------------------------------------------------------------------------
@shot
def e9():
    sh, n = span("e9")
    home_set("damaged")
    a = L.Character("linda", "linda", loc=(-0.6, -5.3, 0), rot_z=math.radians(-10))
    a.rest_pose(1)
    idle(a, 1, n, seed=61)
    a.pose_arm("R", 1, fwd=60, out=10, elbow=10)
    a.pose_head(1, nod=16)
    a.brows_key(1, worry=0.8)
    a.set_mouth(-0.4, 1)
    cam = L.camera(lens=40, fstop=0.35, focus=4.5)
    L.cam_key(cam, 1, (0.3, -11.5, 2.6), (-0.4, -5, 2.0))
    L.cam_key(cam, n, (0.0, -11.0, 2.5), (-0.4, -5, 2.0))
    key_rim((-0.6, -5.3, 1.8))
    return n


@shot
def pavedetail():
    bpy.context.scene["res"] = (1000, 760)
    home_set("damaged", neighbours=False)
    cx, cy = DMG_C
    L.area_light("keySpec", (cx + 1.2, cy + 2.5, 2.5), (cx, cy, 0), 260, "#9fb8ff", size=2)
    L.area_light("key", (cx - 2, cy - 2.5, 3), (cx, cy, 0), 160, "#ffc596", size=2)
    cam = L.camera(lens=50, fstop=1.6, focus=2.4)
    L.cam_key(cam, 1, (cx + 0.3, cy - 1.9, 1.5), (cx, cy + 0.1, 0.0))
    return 1


# ---------------------------------------------------------------------------
# Scene 7 - closing composition
# ---------------------------------------------------------------------------
@shot
def e10():
    sh, n = span("e10")
    home_set("new")
    L.toy_car("car", (-1.6, -4.6, 0), math.radians(180), "#2b5a8a")
    a = L.Character("linda", "linda", loc=(0.9, -6.9, 0), rot_z=math.radians(-8))
    a.rest_pose(1)
    idle(a, 1, n, seed=71)
    a.set_mouth(0.95, 1)
    a.brows_key(1, raise_=0.4)
    f = 25
    a.pose_arm("R", f, fwd=10, out=10, elbow=10)
    for i in range(6):
        a.pose_arm("R", f + 8 + i * 7, fwd=25, out=100, elbow=55 + (25 if i % 2 else -10))
    a.pose_arm("R", f + 60, fwd=10, out=10, elbow=15)
    a.pose_head(1, tilt=-5)
    a.pose_head(f + 20, tilt=6)
    a.pose_head(n, tilt=2)
    cam = L.camera(lens=44, fstop=1.0)
    fe = focus_empty("fo", [(1, (0.9, -6.9, 2.3)), (n, (0.9, -6.9, 2.3))])
    cam.data.dof.focus_object = fe
    # Linda framed in the upper-middle so the CTA block below never covers her
    L.cam_key(cam, 1, (-0.3, -15.6, 1.2), (0.5, -3.0, 1.55))
    L.cam_key(cam, n, (0.1, -14.4, 1.15), (0.6, -3.0, 1.45))
    L.area_light("key", (-4, -12, 4), (0.9, -6.9, 2.2), 420, "#ffc596", size=3)
    L.area_light("rimC", (3.5, -4.8, 4.5), (0.9, -6.9, 2.2), 380, "#86a8ff", size=2.5)
    L.area_light("houseK", (-3, -10, 8), (0, -4, 2.5), 600, "#ffc596", size=4)
    return n


# ---------------------------------------------------------------------------
# daytime relight (applied to every shot after it is built)
# ---------------------------------------------------------------------------

def daytime(dim_from=None):
    """Turn the night set into a bright, soft British daytime.

    Keeps the reference's dimensional clay look: a warm sun key, soft blue sky
    fill, gentle contrast and shallow depth of field; removes the night-only
    practical lights (bokeh, lit windows, street lamps, moonlight).
    """
    scn = bpy.context.scene
    nt = scn.world.node_tree
    ramp = next(n for n in nt.nodes if n.type == "VALTORGB")
    ramp.color_ramp.elements[0].color = L.hexc("#cfe3f2")
    ramp.color_ramp.elements[1].color = L.hexc("#5d97d6")
    bg = nt.nodes["Background"]
    bg.inputs["Strength"].default_value = 1.6
    for o in list(bpy.data.objects):
        n = o.name
        if (n.startswith("bk") and n[2:].isdigit()) or n.startswith("glow") or n.startswith("sl") and o.type == "LIGHT":
            bpy.data.objects.remove(o)
        elif o.type == "LIGHT" and (n == "moon" or n.endswith("_porchL") or n == "lightning"):
            bpy.data.objects.remove(o)
        elif o.type == "LIGHT" and o.data.type == "AREA":
            o.data.energy *= 0.35  # character fill only
    for m in bpy.data.materials:
        if m.name.startswith(("glass_lit", "bgwin_")) or m.name in ("lamp_glow", "street_glow"):
            nodes = m.node_tree.nodes
            em = next((x for x in nodes if x.type == "EMISSION"), None)
            if em:
                em.inputs["Color"].default_value = L.hexc("#2a3a4e")
                em.inputs["Strength"].default_value = 0.35
        if m.name == "ground_wet":
            r = next(x for x in m.node_tree.nodes if x.type == "VALTORGB")
            r.color_ramp.elements[0].color = (0.45, 0.45, 0.45, 1)
            r.color_ramp.elements[1].color = (0.7, 0.7, 0.7, 1)
            m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = L.hexc("#3a3c40")
        if m.name.startswith(("drive_", "pallet_blocks", "patio_", "d")) and "Principled BSDF" in m.node_tree.nodes:
            m.node_tree.nodes["Principled BSDF"].inputs["Coat Weight"].default_value = 0.0
    sun_d = bpy.data.lights.new("sun", "SUN")
    sun_d.energy = 4.2
    sun_d.angle = math.radians(4)
    sun_d.color = L.hexc("#fff1dc")[:3]
    sun = bpy.data.objects.new("sun", sun_d)
    scn.collection.objects.link(sun)
    sun.rotation_euler = rad(52, 0, -38)
    if dim_from is not None:  # "before the weather turns": clouds roll in
        f0, f1 = dim_from
        for f, se, be in ((f0, 4.2, 1.6), (f1, 1.2, 0.9)):
            sun_d.energy = se
            sun_d.keyframe_insert("energy", frame=f)
            bg.inputs["Strength"].default_value = be
            bg.inputs["Strength"].keyframe_insert("default_value", frame=f)
    try:
        scn.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        pass


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shot", required=True)
    ap.add_argument("--pct", type=int, default=50)
    ap.add_argument("--samples", type=int, default=10)
    ap.add_argument("--frames", default=None)
    ap.add_argument("--step", type=int, default=1)
    ap.add_argument("--lean", action="store_true", help="fewer light bounces (faster at high resolution)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    L.reset_scene()
    n = SHOTS[a.shot]()
    if a.shot == "e6b":
        sh, _ = span("e6b")
        daytime(dim_from=(F(sh["start"], 25.3), F(sh["start"], 26.6)))
    else:
        daytime()
    L.render_settings(a.pct, a.samples, 1, n)
    scn = bpy.context.scene
    if a.lean:
        scn.cycles.max_bounces = 3
        scn.cycles.diffuse_bounces = 1
        scn.cycles.glossy_bounces = 1
        scn.cycles.transmission_bounces = 2
        scn.cycles.adaptive_threshold = 0.05
    if "res" in scn.keys():
        scn.render.resolution_x, scn.render.resolution_y = scn["res"]
    os.makedirs(a.out, exist_ok=True)
    if a.frames == "preview":
        frames = [HANDLE + 1, n // 3, (2 * n) // 3, n - HANDLE] if n > 1 else [1]
    elif a.frames:
        frames = [int(x) for x in a.frames.split(",")]
    else:
        frames = sorted(set(list(range(1, n + 1, a.step)) + [n]))
    for f in frames:
        path = os.path.join(a.out, f"{f:04d}.png")
        if os.path.exists(path):
            continue
        t = time.time()
        scn.frame_set(f)
        scn.render.filepath = path
        bpy.ops.render.render(write_still=True)
        print(f"[{a.shot}] frame {f}/{n} {time.time() - t:.1f}s", flush=True)


if __name__ == "__main__":
    main()
