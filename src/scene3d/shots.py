"""Shot definitions.  Run with the bpy-enabled Python:

    python src/scene3d/shots.py --shot s1 --pct 66 --samples 20 --out renders/s1

Every shot renders frames 1..N where N = shot duration*fps + 2*HANDLE.  Frame
HANDLE+1 is the first frame on screen; the extra handle frames are used by the
compositor for whip-pan / blur transitions.
"""
import argparse
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import bpy  # noqa: E402

import lib as L  # noqa: E402
from lib import rad  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TL = json.load(open(os.path.join(ROOT, "config", "timeline.json")))
FPS = TL["fps"]
HANDLE = 6
SHOTS = {}


def shot(fn):
    SHOTS[fn.__name__] = fn
    return fn


def span(shot_id):
    s = next(x for x in TL["shots"] if x["id"] == shot_id)
    n = round((s["end"] - s["start"]) * FPS) + 2 * HANDLE
    return s, n


def F(shot_start, t):
    """absolute VO time (s) -> local frame number for a shot starting at shot_start."""
    return round((t - shot_start) * FPS) + HANDLE + 1


# ---------------------------------------------------------------------------
@shot
def test(n=1):
    L.build_ground()
    h = L.build_house(damage_level=2)
    L.build_garden()
    L.build_background_street(y=16)
    a = L.Character("arthur", "arthur", loc=(-1.0, -4.6, 0), rot_z=math.radians(10))
    a.rest_pose(1)
    a.brows_key(1, worry=1.0)
    a.set_mouth(-0.6, 1)
    a.look(1, 0.2, 0.6)
    a.pose_head(1, tilt=4, nod=-12)
    L.standard_night_lights(target=(-1, -4.6, 2.0), key_loc=(-3.5, -8, 3.5), key_e=700)
    cam = L.camera(lens=35, fstop=2.0, focus=a.head)
    L.cam_key(cam, 1, (0.0, -9.5, 2.6), (-0.4, -3, 3.6))
    return 1


@shot
def test_face(n=1):
    a = L.Character("arthur", "arthur")
    a.rest_pose(1)
    a.set_mouth(0.4, 1)
    L.bokeh_lights(80, center=(0, 12, 3), spread=(10, 3, 4))
    L.standard_night_lights(target=(0, 0, 2.0), key_loc=(-2.5, -4, 3), key_e=400, rim_loc=(3, 3, 4), rim_e=500)
    cam = L.camera(lens=50, fstop=1.8, focus=a.head)
    L.cam_key(cam, 1, (0.4, -5.2, 2.2), (0, 0, 2.0))
    return 1


# ---------------------------------------------------------------------------
# shared sets
# ---------------------------------------------------------------------------

def street_set(damage=2, new_roof=False, lit=(1, 1, 0, 1), garden=True, scaffold=False, roof_rows=None):
    L.build_ground()
    h = L.build_house(damage_level=damage, new_roof=new_roof, lit=lit, roof_rows=roof_rows)
    # attached neighbour (semi-detached) + next door
    L.build_house("nb", loc=(6.45, 0, 0), damage_level=0, lit=(0, 1, 1, 0), detail=False, brick="#7e3624",
                  door="#5c1f24")
    L.build_house("nb2", loc=(-8.2, 0.6, 0), damage_level=0, lit=(1, 0, 0, 1), detail=False, brick="#7b3a28",
                  door="#2c4a2c")
    if garden:
        L.build_garden()
    L.build_background_street(y=16)
    L.bokeh_lights(70, center=(0, 34, 5), spread=(40, 8, 6))
    # moon / sky rim from behind
    L.area_light("moon", (-6, 20, 18), (0, 0, 4), 4000, "#7c9cff", size=10)
    if scaffold:
        build_scaffold()
    return h


def build_scaffold(z=3.35, y=-3.9):
    m = L.mat_basic("scaf", "#9aa1a8", rough=0.35, metal=0.9)
    plank = L.mat_basic("plank", "#8a6a43", rough=0.7)
    for x in (-3.0, -1.0, 1.0, 3.0):
        for yy in (y - 0.6, y + 0.55):
            L.cyl(f"sc_p{x}_{yy}", 0.05, z + 1.4, m, (x, yy, (z + 1.4) / 2))
    L.rbox("sc_deck", (6.4, 1.3, 0.1), 0.02, plank, (0, y, z))
    L.cyl("sc_rail", 0.045, 6.4, m, (0, y - 0.6, z + 1.0), rad(0, 90, 0))
    L.cyl("sc_rail2", 0.045, 6.4, m, (0, y - 0.6, z + 0.5), rad(0, 90, 0))


def focus_empty(name, frames_locs):
    e = L.empty(name, frames_locs[0][1])
    for f, loc in frames_locs:
        L.key(e, "location", f, loc)
    return e


def idle(ch, f0, f1, seed=1, sway=1.5):
    """Subtle breathing, weight shift, blinks."""
    ch.blinks(f0, f1, seed=seed)
    ch.breathe(f0, f1)
    f = f0
    i = 0
    while f <= f1:
        ch.hips.rotation_euler = rad(0, sway * (1 if i % 2 else -1) * 0.5, 0)
        ch.hips.keyframe_insert("rotation_euler", frame=f)
        f += 45
        i += 1


# ---------------------------------------------------------------------------
# Scene 1 - compromised roof, introduce Arthur
# ---------------------------------------------------------------------------
@shot
def poses():
    names = ["chin", "alarm", "shrug", "thumb", "wave", "heart", "point"]
    chars = []
    for i, nm in enumerate(names):
        c = L.Character(nm, "arthur", loc=((i - 3) * 1.6, 0, 0))
        c.rest_pose(1)
        chars.append(c)
    P = dict(zip(names, chars))
    P["chin"].pose_arm("R", 1, fwd=35, out=0, elbow=125, elbow_side=-30)
    for sd in ("L", "R"):
        P["alarm"].pose_arm(sd, 1, fwd=30, out=10, elbow=135, elbow_side=-20)
        P["shrug"].pose_arm(sd, 1, fwd=20, out=30, elbow=80, elbow_side=30)
    P["thumb"].pose_arm("R", 1, fwd=40, out=10, elbow=95, elbow_side=-20)
    P["wave"].pose_arm("R", 1, fwd=10, out=100, elbow=0)
    P["wave"].elbow["R"].rotation_euler = rad(0, 60, 0)
    P["wave"].elbow["R"].keyframe_insert("rotation_euler", frame=1)
    P["heart"].pose_arm("R", 1, fwd=40, out=-10, elbow=110, elbow_side=-40)
    P["point"].pose_arm("R", 1, fwd=150, out=20, elbow=10)
    L.standard_night_lights(target=(0, 0, 1.8), key_loc=(-3, -9, 4), key_e=500)
    cam = L.camera(lens=50, fstop=8, focus=12)
    L.cam_key(cam, 1, (0, -16, 2.2), (0, 0, 1.6))
    bpy.context.scene["res"] = (1920, 700)
    return 1


@shot
def s1():
    sh, n = span("s1")
    t0 = sh["start"]
    street_set(damage=3)
    a = L.Character("arthur", "arthur", loc=(-0.9, -5.1, 0), rot_z=math.radians(12))
    a.rest_pose(1)
    idle(a, 1, n, seed=3)
    # looking up at the roof, worried
    a.pose_head(1, nod=-22, tilt=3, turn=-6)
    a.look(1, 0.1, 1.0)
    a.brows_key(1, worry=1.0, raise_=0.4)
    a.set_mouth(-0.5, 1, open_=0.4)
    f_scr = F(t0, 2.2)
    a.pose_head(f_scr - 8, nod=-20, tilt=4, turn=-4)
    a.pose_arm("R", f_scr - 10, fwd=4, out=8, elbow=10)
    # hand up to scratch the back of the cap ("unreliable contractor?")
    a.pose_arm("R", f_scr + 6, fwd=35, out=0, elbow=125, elbow_side=-30)
    a.pose_arm("R", f_scr + 30, fwd=36, out=0, elbow=127, elbow_side=-30)
    a.pose_head(f_scr + 10, nod=-4, tilt=-8, turn=10)
    a.look(f_scr + 8, -0.4, 0.0)
    a.brows_key(f_scr + 10, worry=1.2, raise_=0.2)
    a.set_mouth(-0.8, f_scr + 10)
    a.pose_arm("R", n, fwd=35, out=0, elbow=125, elbow_side=-30)
    a.pose_head(n, nod=-2, tilt=-10, turn=12)
    # camera: start on the damaged tiles, crane down to Arthur
    cam = L.camera(lens=45, fstop=0.55)
    fe = focus_empty("fo", [(1, (-0.4, -1.6, 6.1)), (int(n * 0.38), (-0.4, -1.6, 6.1)), (int(n * 0.62), (-0.9, -5.1, 2.3)), (n, (-0.9, -5.1, 2.3))])
    cam.data.dof.focus_object = fe
    L.cam_key(cam, 1, (0.9, -5.6, 7.6), (-0.4, -1.4, 6.0))
    L.cam_key(cam, int(n * 0.36), (0.6, -6.6, 7.0), (-0.4, -1.6, 5.9))
    L.cam_key(cam, int(n * 0.7), (0.2, -10.4, 2.6), (-0.8, -4.6, 3.2))
    L.cam_key(cam, n, (0.1, -9.9, 2.4), (-0.8, -4.6, 3.05))
    L.area_light("key", (-3.5, -8.5, 3.2), (-0.9, -5.1, 2.2), 260, "#ffc596", size=2.0)
    L.area_light("rimC", (2.5, -3.3, 4.5), (-0.9, -5.1, 2.0), 380, "#86a8ff", size=2.0)
    L.area_light("roofK", (-3, -6, 9), (-0.4, -1.5, 6.0), 350, "#ffb47a", size=3)
    return n


# ---------------------------------------------------------------------------
# Scene 2a - careless contractor, Arthur alarmed
# ---------------------------------------------------------------------------
@shot
def s2a():
    sh, n = span("s2a")
    t0 = sh["start"]
    street_set(damage=3)
    L.ladder("ladder", (2.6, -3.5, 0), height=5.6, lean=-13)
    c = L.Character("cowboy", "cowboy", loc=(1.5, -4.1, 0), rot_z=math.radians(-24))
    a = L.Character("arthur", "arthur", loc=(-1.0, -7.4, 0), rot_z=math.radians(42))
    for ch in (a, c):
        ch.rest_pose(1)
    idle(a, 1, n, seed=5)
    idle(c, 1, n, seed=9, sway=3)
    # contractor: careless shrug + grin, slouched
    c.pose_body(1, lean=-6, side=4)
    c.pose_head(1, tilt=10, turn=-10, nod=4)
    c.set_mouth(0.9, 1)
    c.brows_key(1, worry=-0.2, raise_=0.6)
    c.look(1, -0.6, 0.0)
    f_sh = F(t0, 4.6)
    for side in ("L", "R"):
        c.pose_arm(side, f_sh - 6, fwd=4, out=8, elbow=10)
        c.pose_arm(side, f_sh + 6, fwd=20, out=45, elbow=95, elbow_side=-30)
        c.pose_arm(side, f_sh + 26, fwd=20, out=45, elbow=95, elbow_side=-30)
        c.pose_arm(side, f_sh + 40, fwd=10, out=20, elbow=60)
    c.pose_head(f_sh + 8, tilt=16, turn=-14, nod=2)
    c.pose_head(n, tilt=12, turn=-20, nod=0)
    # falling tile
    tm = L.mat_tile("tile", "#a9502f")
    tile = L.obj("fall_tile", L.tile_mesh(), tm)
    tile.scale = (1.2, 1.2, 1.2)
    f_fall = F(t0, 4.9)
    f_hit = F(t0, 5.35)
    L.key(tile, "location", 1, (0.9, -2.75, 5.12))
    L.key(tile, "rotation_euler", 1, rad(48, 0, 0))
    L.key(tile, "location", f_fall, (0.9, -2.8, 5.1))
    L.key(tile, "rotation_euler", f_fall, rad(48, 0, 0))
    L.key(tile, "location", f_hit, (0.4, -4.9, 0.12))
    L.key(tile, "rotation_euler", f_hit, rad(300, 40, 70))
    L.key(tile, "hide_render", f_hit, False)
    L.key(tile, "hide_render", f_hit + 1, True)
    halves = []
    for i, (dx, dy, rz) in enumerate(((-0.35, -0.3, 30), (0.4, -0.15, -50))):
        hm = L.rbox_mesh(0.2, 0.34, 0.06, 0.02, 3)
        hv = L.obj(f"half{i}", hm, tm)
        L.key(hv, "hide_render", 1, True)
        L.key(hv, "hide_render", f_hit, False)
        L.key(hv, "location", f_hit, (0.4, -4.9, 0.05))
        L.key(hv, "rotation_euler", f_hit, rad(0, 0, rz))
        L.key(hv, "location", f_hit + 8, (0.4 + dx, -4.9 + dy, 0.04))
        L.key(hv, "rotation_euler", f_hit + 8, rad(0, 0, rz * 2))
    # Arthur: concern -> flinch at the crash
    a.pose_head(1, turn=6, nod=-6, tilt=4)
    a.look(1, 0.6, 0.3)
    a.brows_key(1, worry=1.0)
    a.set_mouth(-0.6, 1)
    a.look(f_fall, 0.5, 0.6)
    a.pose_head(f_hit - 2, turn=8, nod=-10, tilt=4)
    a.pose_head(f_hit + 4, turn=10, nod=8, tilt=-6)
    a.brows_key(f_hit + 3, worry=1.4, raise_=1.0)
    a.set_mouth(-0.9, f_hit + 3, open_=1.4)
    for side in ("L", "R"):
        a.pose_arm(side, f_hit - 1, fwd=4, out=8, elbow=10)
        a.pose_arm(side, f_hit + 5, fwd=55, out=15, elbow=120, elbow_side=-25)
        a.pose_arm(side, n, fwd=52, out=15, elbow=118, elbow_side=-25)
    a.look(f_hit + 4, 0.7, -0.6)
    a.blink(f_hit + 1, 3)
    cam = L.camera(lens=44, fstop=0.6)
    fe = focus_empty("fo", [(1, (1.5, -4.1, 2.2)), (F(t0, 5.2), (1.5, -4.1, 2.2)), (F(t0, 5.5), (-1.0, -7.4, 2.2)), (n, (-1.0, -7.4, 2.2))])
    cam.data.dof.focus_object = fe
    L.cam_key(cam, 1, (0.5, -13.4, 2.5), (0.3, -4.0, 3.55))
    L.cam_key(cam, n, (0.3, -12.7, 2.45), (0.2, -4.2, 3.45))
    L.area_light("key", (-4, -11, 4), (-0.5, -6, 2.0), 380, "#ffc596", size=2.5)
    L.area_light("keyC", (-1, -8, 4), (1.5, -4.1, 2.0), 200, "#ffc596", size=2)
    L.area_light("rimC", (4.0, -3.2, 4.5), (0, -5, 2.0), 380, "#86a8ff", size=2.5)
    return n


# ---------------------------------------------------------------------------
# Scene 2b - wide street: "across the region"
# ---------------------------------------------------------------------------
@shot
def s2b():
    sh, n = span("s2b")
    L.build_ground()
    import random as _r
    rnd = _r.Random(2)
    bricks = ["#8a3b26", "#7e3624", "#93492c", "#74331f", "#8a4430"]
    doors = ["#1f3b4d", "#5c1f24", "#2c4a2c", "#232323", "#3d2b56"]
    for i in range(-4, 5):
        L.build_house(f"h{i}", loc=(i * 6.45, 0, 0), damage_level=0, lit=tuple(rnd.random() < 0.6 for _ in range(4)),
                      detail=abs(i) <= 1, brick=bricks[i % 5], door=doors[i % 5], seed=i + 20)
    for i in range(-4, 5):
        L.build_house(f"o{i}", loc=(i * 6.45 + 3, 20, 0), damage_level=0,
                      lit=tuple(rnd.random() < 0.5 for _ in range(4)), detail=False, brick=bricks[(i + 2) % 5])
        bpy.data.objects[f"o{i}"].rotation_euler = rad(0, 0, 180)
    pole = L.mat_basic("pole", "#1a1c20", rough=0.4, metal=0.5)
    glow = L.mat_emission("street_glow", "#ffb35c", 40)
    for i in range(-3, 4):
        x = i * 9.0 + 2
        L.cyl(f"pole{i}", 0.07, 5.5, pole, (x, -6.5, 2.75))
        L.sphere(f"glow{i}", 0.25, glow, (x, -6.5, 5.6), seg=16)
        L.point_light(f"sl{i}", (x, -6.5, 5.3), 300, "#ffb35c", 0.3)
    L.bokeh_lights(90, center=(0, 60, 8), spread=(60, 15, 8))
    L.area_light("moon", (-10, 30, 25), (0, 0, 4), 6000, "#7c9cff", size=12)
    cam = L.camera(lens=30, fstop=1.6, focus=16.0)
    L.cam_key(cam, 1, (-13, -14, 5.2), (2, 0, 4.2))
    L.cam_key(cam, n, (-8, -14.5, 5.0), (7, 0, 4.0))
    return n


# ---------------------------------------------------------------------------
# Scene 3 - Sureshield team arrives and inspects
# ---------------------------------------------------------------------------
@shot
def s3():
    sh, n = span("s3")
    t0 = sh["start"]
    street_set(damage=3)
    L.ladder("ladder", (2.7, -3.4, 0), height=5.6, lean=-13)
    r1 = L.Character("r1", "roofer1", loc=(-0.55, -5.4, 0), rot_z=math.radians(8))
    r2 = L.Character("r2", "roofer2", loc=(1.25, -4.7, 0), rot_z=math.radians(-18))
    a = L.Character("arthur", "arthur", loc=(-2.6, -6.1, 0), rot_z=math.radians(48))
    for ch, sd in ((r1, 2), (r2, 7), (a, 4)):
        ch.rest_pose(1)
        idle(ch, 1, n, seed=sd)
    tb = L.tablet("tab", parent=r1.hand["L"], loc=(0.05, -0.12, -0.12), rot=rad(70, 0, -20))
    # r1: inspecting tablet, looks up at roof, then turns to camera, nods
    r1.pose_arm("L", 1, fwd=50, out=8, elbow=70, elbow_side=-30)
    r1.pose_arm("R", 1, fwd=6, out=10, elbow=15)
    r1.pose_head(1, nod=-26, turn=-6)
    r1.look(1, 0.0, 1.0)
    r1.brows_key(1, worry=-0.2, raise_=0.3)
    r1.set_mouth(0.1, 1)
    f_look = F(t0, 11.2)
    r1.pose_head(f_look, nod=-26, turn=-6)
    r1.pose_head(f_look + 12, nod=4, turn=4, tilt=-3)
    r1.look(f_look + 10, 0.0, -0.1)
    r1.set_mouth(0.8, f_look + 14)
    r1.brows_key(f_look + 14, worry=0.0, raise_=0.6)
    f_nod = F(t0, 13.5)
    r1.pose_head(f_nod, nod=10, turn=4, tilt=-3)
    r1.pose_head(f_nod + 6, nod=-2, turn=4, tilt=-3)
    r1.pose_head(n, nod=0, turn=4, tilt=-2)
    # r2: pointing up at the roof, then thumbs up on "trust"
    r2.pose_head(1, nod=-25, turn=8)
    r2.look(1, 0.0, 1.0)
    r2.pose_arm("R", 1, fwd=150, out=20, elbow=10)
    r2.pose_arm("R", f_look, fwd=150, out=20, elbow=10)
    r2.set_mouth(0.3, 1)
    r2.pose_head(f_look + 14, nod=0, turn=-14, tilt=4)
    r2.look(f_look + 12, -0.5, 0.0)
    f_tu = F(t0, 13.45)
    r2.pose_arm("R", f_tu - 10, fwd=10, out=12, elbow=20)
    r2.pose_arm("R", f_tu, fwd=40, out=10, elbow=95, elbow_side=-20)
    r2.pose_arm("R", n, fwd=40, out=10, elbow=95, elbow_side=-20)
    r2.set_mouth(0.95, f_tu)
    r2.brows_key(f_tu, raise_=0.8)
    # Arthur: hopeful, looking at the team
    a.pose_head(1, turn=4, nod=-4)
    a.look(1, 0.7, 0.1)
    a.brows_key(1, worry=0.6)
    a.set_mouth(-0.2, 1)
    a.brows_key(f_nod, worry=0.1, raise_=0.5)
    a.set_mouth(0.5, f_nod)
    cam = L.camera(lens=45, fstop=0.7)
    fe = focus_empty("fo", [(1, (0.0, -5.2, 2.4)), (n, (0.0, -5.2, 2.4))])
    cam.data.dof.focus_object = fe
    L.cam_key(cam, 1, (-0.2, -13.6, 3.0), (-0.5, -4.2, 3.7))
    L.cam_key(cam, n, (-0.4, -11.9, 2.5), (-0.6, -4.6, 3.05))
    L.area_light("key", (-4.5, -11, 5), (0, -5, 2.0), 520, "#ffc596", size=3.5)
    L.area_light("rimC", (4.0, -3.3, 4.5), (0, -5, 2.0), 420, "#86a8ff", size=2.5)
    return n


# ---------------------------------------------------------------------------
# Scene 4 - careful workmanship close-up (lower half; cards float above)
# ---------------------------------------------------------------------------
@shot
def s4():
    sh, n = span("s4")
    t0 = sh["start"]
    h = street_set(damage=0, lit=(1, 1, 1, 1), scaffold=True, garden=False)
    # remove one tile near the eave to be replaced
    gap = (1, 8)
    bpy.context.view_layer.update()
    t_gap = h["tiles"].pop(gap)
    gloc = t_gap.matrix_world.translation.copy()
    grot = t_gap.matrix_world.to_euler()
    bpy.data.objects.remove(t_gap)
    r1 = L.Character("r1", "roofer1", loc=(gloc.x + 0.1, -3.95, 3.4), rot_z=math.radians(180 + 8))
    r1.rest_pose(1)
    idle(r1, 1, n, seed=12, sway=0.6)
    r1.pose_body(1, lean=-14)
    tm = L.mat_tile("tile_new", "#c0582f")
    nt = L.obj("new_tile", L.tile_mesh(), tm)
    f_in = F(t0, 15.2)
    f_set = F(t0, 16.5)
    # tile glides in from the roofer's hands and settles precisely
    start = (gloc.x + 0.15, gloc.y - 0.55, gloc.z + 0.35)
    L.key(nt, "location", 1, start)
    L.key(nt, "rotation_euler", 1, (grot.x - math.radians(25), grot.y, grot.z + math.radians(6)))
    L.key(nt, "location", f_in, start)
    L.key(nt, "rotation_euler", f_in, (grot.x - math.radians(25), grot.y, grot.z + math.radians(6)))
    L.key(nt, "location", f_set - 8, (gloc.x, gloc.y - 0.06, gloc.z + 0.05))
    L.key(nt, "rotation_euler", f_set - 8, (grot.x, grot.y, grot.z + math.radians(1)))
    L.key(nt, "location", f_set, tuple(gloc))
    L.key(nt, "rotation_euler", f_set, tuple(grot))
    for side in ("L", "R"):
        r1.pose_arm(side, 1, fwd=70, out=14, elbow=40, elbow_side=-20)
        r1.pose_arm(side, f_in, fwd=70, out=14, elbow=40, elbow_side=-20)
        r1.pose_arm(side, f_set, fwd=95, out=10, elbow=20, elbow_side=-25)
        r1.pose_arm(side, f_set + 18, fwd=92, out=10, elbow=22, elbow_side=-25)
    r1.pose_arm("L", f_set + 30, fwd=20, out=12, elbow=30)
    r1.pose_arm("L", n, fwd=20, out=12, elbow=30)
    r1.pose_head(1, nod=-28, turn=0)
    r1.look(1, 0.0, -1.0)
    r1.brows_key(1, worry=-0.4)
    r1.set_mouth(0.0, 1, open_=0.0)
    r1.set_mouth(-0.1, f_set - 4)
    f_sm = F(t0, 17.6)
    r1.pose_head(f_sm, nod=-18, turn=0)
    r1.pose_head(f_sm + 14, nod=-6, turn=-8, tilt=6)
    r1.look(f_sm + 12, -0.2, 0.0)
    r1.set_mouth(0.85, f_sm + 14)
    r1.brows_key(f_sm + 14, worry=0, raise_=0.5)
    r1.pose_head(n, nod=-4, turn=-10, tilt=7)
    cam = L.camera(lens=40, fstop=0.45)
    fe = focus_empty("fo", [(1, (gloc.x, gloc.y - 0.6, gloc.z + 0.4)), (f_set, (gloc.x, gloc.y - 0.5, gloc.z + 0.3)),
                            (f_sm + 10, (gloc.x + 0.1, -3.9, 5.6)), (n, (gloc.x + 0.1, -3.9, 5.6))])
    cam.data.dof.focus_object = fe
    tgt = (gloc.x + 0.1, gloc.y - 0.7, gloc.z + 0.35)
    L.cam_key(cam, 1, (gloc.x - 1.0, gloc.y + 2.3, gloc.z + 2.7), (tgt[0], tgt[1] + 0.1, tgt[2] + 0.55))
    L.cam_key(cam, n, (gloc.x - 0.7, gloc.y + 1.9, gloc.z + 2.4), (tgt[0], tgt[1], tgt[2] + 0.6))
    L.area_light("key", (gloc.x - 2.5, gloc.y + 1.5, gloc.z + 3.5), tgt, 260, "#ffc596", size=2.0)
    L.area_light("rimC", (gloc.x + 2.0, -6.5, 7.0), tgt, 400, "#86a8ff", size=2.0)
    return n


# ---------------------------------------------------------------------------
# Scene 5a - background behind the inspection panel (blurred)
# ---------------------------------------------------------------------------
@shot
def s5a():
    sh, n = span("s5a")
    street_set(damage=3, scaffold=True, garden=True)
    r1 = L.Character("r1", "roofer1", loc=(-0.4, -3.95, 3.4), rot_z=math.radians(-25))
    r1.rest_pose(1)
    idle(r1, 1, n, seed=21)
    r1.pose_arm("R", 1, fwd=40, out=75, elbow=50)
    r1.set_mouth(0.3, 1)
    torch = L.mat_emission("torch", "#ffe8c0", 40)
    L.cyl("torch", 0.05, 0.25, L.mat_basic("tcase", "#222222", rough=0.4), (0, 0, -0.08), parent=r1.hand["R"])
    L.sphere("torchg", 0.05, torch, (0, 0, -0.22), parent=r1.hand["R"], seg=12)
    L.point_light("torchL", (-0.4, -2.9, 5.6), 60, "#ffe8c0", 0.05)
    r1.pose_head(1, nod=-12, turn=-25)
    r1.look(1, -0.6, 0.6)
    cam = L.camera(lens=45, fstop=0.35, focus=4.0)
    L.cam_key(cam, 1, (0.6, -9.0, 5.2), (-0.3, -2.5, 5.6))
    L.cam_key(cam, n, (0.0, -8.6, 5.3), (-0.3, -2.5, 5.6))
    L.area_light("key", (-4, -8, 6), (0, -3.5, 5), 500, "#ffc596", size=3)
    return n


@shot
def roofdetail():
    """Still for the inspection panel image: wet tiles with a displaced section."""
    scn = bpy.context.scene
    scn["res"] = (1000, 760)
    L.build_ground()
    h = L.build_house(damage_level=3)
    L.bokeh_lights(40, center=(0, 20, 9), spread=(20, 4, 4))
    L.area_light("moon", (-6, 20, 18), (0, 0, 4), 3000, "#7c9cff", size=10)
    L.area_light("key", (-3, -5, 9), (-0.4, -1.5, 6.1), 220, "#ffc596", size=2)
    L.area_light("keySpec", (1.5, 2.5, 9.5), (-0.4, -1.5, 6.1), 500, "#9fb8ff", size=4)
    cam = L.camera(lens=50, fstop=1.2, focus=3.6)
    L.cam_key(cam, 1, (0.4, -4.4, 7.8), (-0.3, -1.4, 6.1))
    return 1


# ---------------------------------------------------------------------------
# Scene 5b - repair
# ---------------------------------------------------------------------------
@shot
def s5b():
    sh, n = span("s5b")
    t0 = sh["start"]
    h = street_set(damage=2, scaffold=False, garden=False)
    pitch = math.radians(h["pitch"])
    d = 1.6  # distance up the slope from the eave
    base = (-0.6, -2.85 + d * math.cos(pitch), 4.95 + d * math.sin(pitch) + 0.05)
    r2 = L.Character("r2", "roofer2", loc=base, rot_z=math.radians(12))
    r2.root.rotation_euler = (math.radians(-10), 0, math.radians(12))
    r2.hips.location.z = 0.3
    for sd in ("L", "R"):
        r2.leg[sd].rotation_euler = rad(-70, 0, 0)
        r2.knee[sd].rotation_euler = rad(40, 0, 0)
    r2.rest_pose(1)
    idle(r2, 1, n, seed=31, sway=0.3)
    r2.pose_body(1, lean=14)
    L.hammer("hammer", parent=r2.hand["R"], loc=(0, -0.02, -0.08), rot=rad(80, 0, 0))
    r2.pose_arm("L", 1, fwd=55, out=10, elbow=50, elbow_side=-20)
    r2.pose_head(1, nod=22, turn=-6)
    r2.look(1, 0.0, -0.9)
    r2.brows_key(1, worry=-0.5)
    r2.set_mouth(0.2, 1)
    f = 1
    up = True
    while f <= n:
        r2.pose_arm("R", f, fwd=95 if up else 45, out=12, elbow=80 if up else 25, elbow_side=-10)
        f += 7
        up = not up
    f_end = F(t0, 22.9)
    r2.pose_head(f_end, nod=20, turn=-6)
    r2.pose_head(f_end + 10, nod=2, turn=4, tilt=5)
    r2.look(f_end + 8, 0, 0)
    r2.set_mouth(0.85, f_end + 10)
    r2.brows_key(f_end + 10, raise_=0.6)
    cam = L.camera(lens=40, fstop=0.7)
    tgt = (base[0], base[1], base[2] + 1.2)
    fe = focus_empty("fo", [(1, tgt), (n, tgt)])
    cam.data.dof.focus_object = fe
    L.cam_key(cam, 1, (base[0] + 1.2, base[1] - 5.0, base[2] + 0.4), (tgt[0], tgt[1], tgt[2] + 0.4))
    L.cam_key(cam, n, (base[0] + 0.9, base[1] - 4.4, base[2] + 0.35), (tgt[0], tgt[1], tgt[2] + 0.35))
    L.area_light("key", (base[0] - 3, base[1] - 3.5, base[2] + 2.5), tgt, 260, "#ffc596", size=2)
    L.area_light("rimC", (base[0] + 2.5, base[1] + 1.5, base[2] + 2.5), tgt, 380, "#86a8ff", size=2)
    return n


# ---------------------------------------------------------------------------
# Scene 5c - new roof installation: rows of fresh tiles drop into place
# ---------------------------------------------------------------------------
@shot
def s5c():
    sh, n = span("s5c")
    h = street_set(damage=0, new_roof=True, garden=False, scaffold=True)
    tiles = h["tiles"]
    rows = sorted({r for r, c in tiles})
    maxr = max(rows)
    for (r, c), t in tiles.items():
        # rows land from the eave upward; each tile drops in from above
        f_land = 4 + r * 4 + (c % 3)
        base = t.location.copy()
        t.keyframe_insert("location", frame=f_land)
        t.keyframe_insert("scale", frame=f_land)
        t.location.z = base.z + 0.9
        t.scale = (0.001, 0.001, 0.001)
        t.keyframe_insert("location", frame=f_land - 7)
        t.keyframe_insert("scale", frame=f_land - 7)
        t.location = base
        t.scale = (1, 1, 1)
    cam = L.camera(lens=30, fstop=0.9)
    fe = focus_empty("fo", [(1, (-0.5, -1.6, 6.0)), (n, (-0.5, -1.6, 6.0))])
    cam.data.dof.focus_object = fe
    L.cam_key(cam, 1, (1.6, -8.4, 9.4), (-0.2, -1.2, 5.6))
    L.cam_key(cam, n, (0.9, -8.9, 8.8), (-0.3, -1.3, 5.7))
    L.area_light("key", (-4, -7, 9), (0, -1.5, 6), 600, "#ffc596", size=3)
    return n


# ---------------------------------------------------------------------------
# Scene 6a - finished roof, team + relieved Arthur
# ---------------------------------------------------------------------------
@shot
def s6a():
    sh, n = span("s6a")
    t0 = sh["start"]
    street_set(damage=0, new_roof=True, lit=(1, 1, 1, 1))
    r1 = L.Character("r1", "roofer1", loc=(-0.1, -5.0, 0), rot_z=math.radians(-6))
    r2 = L.Character("r2", "roofer2", loc=(1.75, -4.6, 0), rot_z=math.radians(-20))
    a = L.Character("arthur", "arthur", loc=(-1.95, -5.6, 0), rot_z=math.radians(22))
    for ch, sd in ((r1, 51), (r2, 52), (a, 53)):
        ch.rest_pose(1)
        idle(ch, 1, n, seed=sd)
        ch.set_mouth(0.85, 1)
        ch.brows_key(1, raise_=0.4)
    # Arthur looks up at the finished roof, then beams at camera
    a.pose_head(1, nod=-22, turn=-4)
    a.look(1, 0, 1)
    a.set_mouth(0.4, 1, open_=0.3)
    f_turn = F(t0, 27.3)
    a.pose_head(f_turn, nod=-20, turn=-4)
    a.pose_head(f_turn + 12, nod=2, turn=6, tilt=-6)
    a.look(f_turn + 10, 0.1, 0.0)
    a.set_mouth(1.0, f_turn + 12)
    a.brows_key(f_turn + 12, worry=0.4, raise_=0.6)
    # hand on heart (relief)
    a.pose_arm("R", f_turn + 4, fwd=10, out=8, elbow=15)
    a.pose_arm("R", f_turn + 16, fwd=40, out=-10, elbow=110, elbow_side=-40)
    a.pose_arm("R", n, fwd=40, out=-10, elbow=110, elbow_side=-40)
    # team: r1 nods, r2 waves
    r1.pose_head(1, nod=-4, turn=10)
    r1.look(1, 0.4, 0)
    r1.pose_head(f_turn + 10, nod=0, turn=0, tilt=4)
    r1.look(f_turn + 10, 0, 0)
    w0 = F(t0, 26.0)
    r2.pose_arm("R", w0, fwd=10, out=10, elbow=10)
    for i in range(6):
        r2.pose_arm("R", w0 + 8 + i * 7, fwd=30, out=95, elbow=60 + (25 if i % 2 else -10), elbow_side=0)
    r2.pose_arm("R", w0 + 60, fwd=12, out=10, elbow=15)
    r2.pose_head(1, tilt=6, turn=-6)
    cam = L.camera(lens=42, fstop=0.8)
    fe = focus_empty("fo", [(1, (-0.2, -5.2, 2.4)), (n, (-0.2, -5.2, 2.4))])
    cam.data.dof.focus_object = fe
    L.cam_key(cam, 1, (0.2, -9.0, 8.6), (0.0, -2.0, 6.0))
    L.cam_key(cam, int(n * 0.5), (0.1, -12.5, 5.0), (-0.1, -4.0, 4.0))
    L.cam_key(cam, n, (0.0, -13.2, 2.8), (-0.1, -4.6, 3.6))
    L.area_light("key", (-4.5, -11, 6), (0, -5, 2.0), 560, "#ffc596", size=3.5)
    L.area_light("rimC", (4.0, -3.3, 4.5), (0, -5, 2.0), 420, "#86a8ff", size=2.5)
    L.area_light("roofK", (-3, -7, 10), (0, -1.5, 6.0), 350, "#ffb47a", size=3)
    return n


# ---------------------------------------------------------------------------
# Scene 6b - Arthur cosy indoors while the weather turns
# ---------------------------------------------------------------------------
@shot
def s6b():
    sh, n = span("s6b")
    t0 = sh["start"]
    wall = L.mat_fabric("wallpaper", "#3a2f3a", rough=0.85, scale=40)
    floor = L.mat_basic("floorwood", "#4a2f1e", rough=0.35)
    L.rbox("floor", (12, 12, 0.1), 0.01, floor, (0, 0, -0.05))
    # back wall with a window opening (built from 4 blocks)
    L.rbox("wallL", (3.6, 0.3, 6), 0.02, wall, (-3.3, 2.5, 3))
    L.rbox("wallR", (3.6, 0.3, 6), 0.02, wall, (3.3, 2.5, 3))
    L.rbox("wallB", (3.0, 0.3, 1.4), 0.02, wall, (0, 2.5, 0.7))
    L.rbox("wallT", (3.0, 0.3, 1.6), 0.02, wall, (0, 2.5, 5.2))
    fr = L.mat_basic("win_frame", "#efeee9", rough=0.35)
    for x in (-1.5, 1.5, 0):
        L.rbox(f"wf{x}", (0.12, 0.2, 3.0), 0.03, fr, (x, 2.4, 2.9))
    for z in (1.4, 4.4, 2.9):
        L.rbox(f"wfh{z}", (3.1, 0.2, 0.12), 0.03, fr, (0, 2.4, z))
    L.rbox("sill", (3.4, 0.5, 0.12), 0.03, fr, (0, 2.2, 1.36))
    glass = L.mat_basic("glass_in", "#0a1220", rough=0.0, coat=1.0)
    glass.node_tree.nodes["Principled BSDF"].inputs["Transmission Weight"].default_value = 1.0
    # outside: night street bokeh
    L.build_background_street(y=16, n=7)
    L.bokeh_lights(80, center=(0, 22, 4), spread=(14, 6, 4), strength=(6, 18))
    flash = L.area_light("lightning", (-4, 30, 20), (0, 2, 3), 0, "#c9d8ff", size=20)
    f_l = F(t0, 30.62)
    for f, e in ((1, 0), (f_l - 1, 0), (f_l, 40000), (f_l + 2, 3000), (f_l + 4, 30000), (f_l + 9, 0), (n, 0)):
        flash.data.energy = e
        flash.data.keyframe_insert("energy", frame=f)
    # armchair
    chair = L.mat_knit("chair", "#2f5d62", scale=22, rough=0.9)
    L.rbox("ch_seat", (2.0, 1.6, 0.6), 0.2, chair, (0.0, -0.1, 0.65))
    L.rbox("ch_back", (2.0, 0.5, 1.9), 0.24, chair, (0.0, 0.7, 1.4))
    for x in (-1.05, 1.05):
        L.rbox(f"ch_arm{x}", (0.45, 1.7, 1.0), 0.2, chair, (x, -0.05, 0.95))
    # side table + lamp
    wood = L.mat_basic("wood_t", "#5a3a22", rough=0.4)
    L.rbox("table", (0.8, 0.8, 1.0), 0.05, wood, (1.85, -0.2, 0.5))
    shade = L.mat_emission("shade", "#ffb066", 6)
    L.cyl("lamp_base", 0.1, 0.7, L.mat_basic("brass", "#c9a24a", rough=0.25, metal=1.0), (1.85, -0.2, 1.35))
    L.cyl("lamp_shade", 0.32, 0.45, shade, (1.85, -0.2, 1.85), r2=0.22)
    L.point_light("lampL", (1.85, -0.4, 1.8), 120, "#ffad5c", 0.3)
    a = L.Character("arthur", "arthur", loc=(0.0, -0.05, 0.38), rot_z=math.radians(0))
    a.sit()
    a.rest_pose(1)
    idle(a, 1, n, seed=61, sway=0)
    a.pose_body(1, lean=-6)
    mg = L.mug("mug", parent=a.hand["L"], loc=(0.0, -0.12, -0.05))
    a.pose_arm("L", 1, fwd=50, out=-12, elbow=95, elbow_side=-35)
    a.pose_arm("R", 1, fwd=30, out=10, elbow=60, elbow_side=-20)
    a.pose_head(1, nod=4, tilt=-6, turn=4)
    a.set_mouth(0.9, 1)
    a.brows_key(1, worry=0.4, raise_=0.2)
    # contented closed eyes, then glance back at the storm and smile
    for e in a.eyes:
        L.key(e, "scale", 1, (1, 1, 0.12))
        L.key(e, "scale", f_l - 6, (1, 1, 0.12))
        L.key(e, "scale", f_l + 2, (1, 1, 1))
    a.look(f_l + 2, 0.5, 0.4)
    a.pose_head(f_l + 4, nod=-4, tilt=4, turn=-22)
    a.pose_head(n, nod=-2, tilt=2, turn=-26)
    cam = L.camera(lens=45, fstop=0.8)
    fe = focus_empty("fo", [(1, (0, -0.4, 2.2)), (n, (0, -0.4, 2.2))])
    cam.data.dof.focus_object = fe
    L.cam_key(cam, 1, (-0.5, -6.4, 2.1), (0.15, 0.5, 2.45))
    L.cam_key(cam, n, (-0.3, -5.5, 2.05), (0.15, 0.5, 2.4))
    L.area_light("key", (2.8, -2.5, 2.6), (0, 0, 2), 380, "#ffad5c", size=2.0)
    L.area_light("fillB", (-3, -4, 3), (0, 0, 2), 80, "#5a78c8", size=4)
    L.area_light("rimW", (-1.0, 1.5, 3.6), (0, 0, 2.2), 200, "#86a8ff", size=1.5)
    return n


# ---------------------------------------------------------------------------
# Scene 7 - closing composition
# ---------------------------------------------------------------------------
@shot
def s7():
    sh, n = span("s7")
    street_set(damage=0, new_roof=True, lit=(1, 1, 1, 1))
    a = L.Character("arthur", "arthur", loc=(0.35, -6.6, 0.0), rot_z=math.radians(-6))
    a.rest_pose(1)
    idle(a, 1, n, seed=71)
    a.set_mouth(0.9, 1)
    a.brows_key(1, raise_=0.4)
    f = 30
    a.pose_arm("R", f, fwd=10, out=10, elbow=10)
    for i in range(6):
        a.pose_arm("R", f + 8 + i * 7, fwd=25, out=100, elbow=55 + (25 if i % 2 else -10))
    a.pose_arm("R", f + 60, fwd=10, out=10, elbow=15)
    a.pose_head(1, tilt=-5)
    a.pose_head(f + 20, tilt=6)
    a.pose_head(n, tilt=2)
    cam = L.camera(lens=46, fstop=1.0)
    fe = focus_empty("fo", [(1, (0.35, -6.6, 2.3)), (n, (0.35, -6.6, 2.3))])
    cam.data.dof.focus_object = fe
    L.cam_key(cam, 1, (-0.6, -14.6, 2.2), (0.2, -3.0, 4.1))
    L.cam_key(cam, n, (-0.1, -13.4, 2.1), (0.3, -3.0, 3.95))
    L.area_light("key", (-4, -11, 4), (0.35, -6.6, 2.2), 420, "#ffc596", size=3)
    L.area_light("rimC", (3.5, -4.5, 4.5), (0.35, -6.6, 2.2), 380, "#86a8ff", size=2.5)
    L.area_light("houseK", (-3, -9, 8), (0, -2.5, 4.5), 500, "#ffc596", size=4)
    return n


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shot", required=True)
    ap.add_argument("--pct", type=int, default=50)
    ap.add_argument("--samples", type=int, default=20)
    ap.add_argument("--frames", default=None, help="e.g. 1-40 or 1,20,40")
    ap.add_argument("--out", required=True)
    ap.add_argument("--blend", default=None)
    ap.add_argument("--step", type=int, default=1, help="render every Nth frame (compositor blends the gaps)")
    ap.add_argument("--threads", type=int, default=0)
    a = ap.parse_args()
    L.reset_scene()
    n = SHOTS[a.shot]()
    L.render_settings(a.pct, a.samples, 1, n)
    scn = bpy.context.scene
    if "res" in scn.keys():
        scn.render.resolution_x, scn.render.resolution_y = scn["res"]
    os.makedirs(a.out, exist_ok=True)
    if a.blend:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(a.blend))
    if a.frames == "preview":
        frames = [HANDLE + 1, n // 3, (2 * n) // 3, n - HANDLE] if n > 1 else [1]
    elif a.frames:
        if "-" in a.frames:
            s, e = map(int, a.frames.split("-"))
            frames = range(s, e + 1)
        else:
            frames = [int(x) for x in a.frames.split(",")]
    else:
        frames = sorted(set(list(range(1, n + 1, a.step)) + [n]))
    if a.threads:
        scn.render.threads_mode = "FIXED"
        scn.render.threads = a.threads
    import time
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
