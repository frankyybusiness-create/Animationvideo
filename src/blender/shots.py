"""The twelve 3D shots. Each function builds its set, cast, camera and acting
for local frames 1..nf (30 fps). Timings mirror config/timeline.json."""
import math
import random

from character import Character
from lib import FPS, empty, glow, kf, mat, rbox, sphere, world
from sets import (BRINDLE, LAY_FRONT, area, broom, lights_day, cam_move, camera, front_set,
                  garden_set, laying_gaps, lights_dusk, lights_night, mallet,
                  mascot, pallet_stack, spirit_level, town_set, van)


def F(t):
    """local seconds -> local frame (frame 1 = t 0)."""
    return int(round(t * FPS)) + 1


def night_world(scn):
    """Opening 'problem' scenes: overcast grey daytime."""
    world(scn, (0.42, 0.47, 0.55), (0.62, 0.64, 0.66), 1.0)
    lights_day(scn, overcast=True)


def dusk_world(scn):
    """'Solution' scenes: bright sunny daytime."""
    world(scn, (0.08, 0.28, 0.95), (0.5, 0.68, 0.98), 1.3)
    lights_day(scn)


def char_light(target, loc, energy=120, color=(1.0, 0.8, 0.62), size=1.5):
    return area("charkey", loc, target, energy, color, size)


# ---------------------------------------------------------------- helpers
def walk(ch, f0, f1, p0, p1, step=8, arms=True):
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    rz = math.atan2(dx, -dy)
    kf(ch.root, "location", f0, (*p0, 0), "LINEAR")
    kf(ch.root, "location", f1, (*p1, 0), "LINEAR")
    kf(ch.root, "rotation_euler", f0, (0, 0, rz))
    f = f0
    i = 0
    while f <= f1:
        s = 1 if i % 2 else -1
        kf(ch.legs[0], "rotation_euler", f, (s * 0.45, 0, 0))
        kf(ch.legs[1], "rotation_euler", f, (-s * 0.45, 0, 0))
        kf(ch.hips, "location", f, (0, 0, 0.52))
        kf(ch.hips, "location", f + step // 2, (0, 0, 0.55))
        if arms:
            ch.reach("L", f, (0.4, s * 0.16, -0.04), pole=(0.3, 0.5, 0))
            ch.reach("R", f, (-0.4, -s * 0.16, -0.04), pole=(-0.3, 0.5, 0))
        f += step
        i += 1
    for leg in ch.legs:
        kf(leg, "rotation_euler", f1 + 4, (0, 0, 0))
    kf(ch.hips, "location", f1 + 4, (0, 0, 0.52))
    return rz


def kneel(ch, frame, lean=0.25):
    kf(ch.hips, "location", frame, (0, 0, 0.27))
    for leg in ch.legs:
        kf(leg, "rotation_euler", frame, (1.25, 0, 0))
    kf(ch.torso, "rotation_euler", frame, (lean, 0, 0))


def idle(ch, nf, seed=0, blink_every=80):
    ch.blinks(1, nf, blink_every, seed)
    ch.breathe(1, nf, 56 + seed * 4)


# ---------------------------------------------------------------- shots
def s1_exterior(scn, nf):
    night_world(scn)
    front_set("old")
    tom = Character("tom", "homeowner", (0.5, -4.6, 0), rot_z=0.15)
    tom.arms_rest(1)
    tom.set_expression(1, "worry")
    tom.brows_pose(1, "worry")
    tom.head_pose(1, nod=0.38, tilt=0.06)
    tom.look(1, 0, -0.025)
    tom.head_pose(F(1.5), nod=0.42, turn=-0.12)
    tom.head_pose(F(2.0), nod=0.0, tilt=-0.1, turn=0.0)
    tom.look(F(1.7), 0, -0.025)
    tom.look(F(2.1), 0, 0.005)
    tom.arms_rest(F(2.0))
    tom.scratch_head(F(2.4))
    tom.reach("R", F(2.7), (-0.25, -0.02, 0.98), pole=(-1, 0.2, 0))
    tom.scratch_head(F(3.0))
    tom.brows_pose(F(2.2), "surprise")
    tom.brows_pose(F(2.6), "worry")
    tom.head_pose(F(3.8), nod=-0.02, tilt=0.12)
    idle(tom, nf, 1)
    tom.finalize()
    char_light((0.5, -4.6, 1.4), (-2.0, -8.5, 3.0), 160)
    cam, tg = camera(scn, 26, 2.8)
    cam_move(cam, tg, [(1, (3.0, -13.0, 2.9), (0.3, -3.6, 1.75), 28),
                       (nf, (1.3, -9.3, 1.85), (0.5, -4.6, 1.5), 36)])


def s2_worry(scn, nf):
    night_world(scn)
    front_set("old")
    tom = Character("tom", "homeowner", (0.5, -4.6, 0), rot_z=0.05)
    tom.arms_rest(1)
    tom.chin_hold(1)
    tom.reach("R", F(1.4), (-0.05, -0.37, 0.58), pole=(-0.6, -0.2, -1))
    tom.chin_hold(F(2.6))
    tom.set_expression(1, "worry")
    tom.brows_pose(1, "worry")
    tom.head_pose(1, tilt=0.12, nod=-0.05)
    tom.head_pose(nf, tilt=0.18, nod=-0.08, turn=0.05)
    tom.look(1, 0.025, 0.022)
    tom.look(F(1.1), 0.025, 0.03)
    tom.look(F(1.6), -0.01, 0.0)
    tom.look(F(2.2), 0.02, 0.025)
    idle(tom, nf, 2, 60)
    tom.finalize()
    char_light((0.5, -4.6, 1.5), (-1.5, -7.0, 2.6), 90)
    cam, tg = camera(scn, 45, 2.0)
    cam_move(cam, tg, [(1, (0.85, -7.4, 1.6), (0.48, -4.6, 1.78), 44),
                       (nf, (0.75, -6.9, 1.62), (0.48, -4.6, 1.76), 46)])


def s3_region(scn, nf):
    dusk_world(scn)
    town_set()
    pin = empty("pin", (0, -3.5, 9.0))
    orange = glow("PinOrange", (1.0, 0.33, 0.1), 2.0)
    sphere("pin_head", 1.0, orange, pin, (0, 0, 1.2))
    sphere("pin_dot", 0.4, mat("PinWhite", (1, 1, 1), emit=(1, 1, 1), emit_strength=3), pin,
           (0, -0.85, 1.25), scale=(1, 0.4, 1))
    from lib import cylinder
    cylinder("pin_tip", 0.85, 1.6, orange, pin, (0, 0, 0.1), r2=0.0, rot=(math.pi, 0, 0))
    for f in range(1, nf + 30, 30):
        kf(pin, "location", f, (0, -3.5, 9.0))
        kf(pin, "location", f + 15, (0, -3.5, 9.6))
    kf(pin, "rotation_euler", 1, (0, 0, -0.4))
    kf(pin, "rotation_euler", nf, (0, 0, 0.4))
    # pulsing rings on the ground
    from lib import _mesh_obj
    import bmesh
    for k in range(3):
        bm = bmesh.new()
        bmesh.ops.create_circle(bm, cap_ends=False, segments=64, radius=1.0)
        ring = _mesh_obj(f"ring{k}", bm, None, None, (0, -3.5, 0.15), (0, 0, 0), False)
        mod = ring.modifiers.new("w", "WIREFRAME")
        mod.thickness = 0.12
        ring.data.materials.append(glow("RingGlow", (1.0, 0.4, 0.12), 3.0))
        for c in range(3):
            f0 = 1 + k * 15 + c * 45
            kf(ring, "scale", f0, (0.5, 0.5, 1), "LINEAR")
            kf(ring, "scale", f0 + 44, (16, 16, 1), "LINEAR")
    cam, tg = camera(scn, 30, 8)
    cam.data.dof.use_dof = False
    cam_move(cam, tg, [(1, (14, -40, 30), (0, -3, 0), 28),
                       (nf, (4, -24, 13), (0, -3.5, 2.5), 30)])


def s4_team(scn, nf):
    dusk_world(scn)
    front_set("old")
    van("van", (-6.0, -12.6, 0), math.pi / 2)
    tom = Character("tom", "homeowner", (1.4, -4.1, 0), rot_z=-0.55)
    law = Character("law", "lawrence", (-4.5, -9.0, 0))
    crew = Character("crew", "crew", (-5.6, -10.2, 0))
    rz = walk(law, 1, F(1.5), (-4.5, -9.0), (-0.35, -4.9))
    walk(crew, 1, F(1.9), (-5.6, -10.2), (-1.7, -6.1))
    kf(law.root, "rotation_euler", F(1.6), (0, 0, rz))
    kf(law.root, "rotation_euler", F(2.0), (0, 0, 0.75))
    kf(crew.root, "rotation_euler", F(2.0), (0, 0, math.atan2(4.0, 4.1)))
    kf(crew.root, "rotation_euler", F(2.4), (0, 0, 0.35))
    law.arms_rest(F(1.6))
    end = law.wave(F(1.7), 3, "R", 10)
    law.arms_rest(end + 8)
    law.present(F(3.1), "L")
    law.arms_rest(F(3.9))
    law.set_expression(1, "smile")
    law.set_expression(F(1.6), "grin")
    law.brows_pose(1, "happy")
    crew.arms_rest(F(1.95))
    crew.hip_hand(F(2.4), "L")
    crew.set_expression(1, "smile")
    tom.arms_rest(1)
    tom.set_expression(1, "flat")
    tom.set_expression(F(1.4), "smile")
    tom.set_expression(F(2.6), "grin")
    tom.brows_pose(1, "neutral")
    tom.brows_pose(F(1.4), "happy")
    tom.head_pose(1, turn=0.0)
    tom.head_pose(F(2.5), nod=0.15, tilt=0.05)
    tom.head_pose(F(2.9), nod=-0.05, tilt=0.05)
    tom.head_pose(F(3.3), nod=0.12)
    tom.head_pose(F(3.7), nod=0.0)
    tom.thumbs_up(F(3.4))
    for c, s in ((tom, 1), (law, 2), (crew, 3)):
        idle(c, nf, s)
        c.finalize()
    char_light((0.4, -4.6, 1.4), (-1.0, -9.5, 3.0), 140)
    cam, tg = camera(scn, 30, 3.2)
    cam_move(cam, tg, [(1, (2.8, -13.8, 2.3), (-0.8, -5.2, 1.35), 30),
                       (nf, (1.7, -11.4, 1.95), (0.35, -4.6, 1.35), 34)])


def s5a_laying(scn, nf):
    dusk_world(scn)
    front_set("laying")
    pallet_stack("stack", (2.2, -2.6, -0.06))
    crew = Character("crew", "crew", (0.25, -4.75, 0), rot_z=math.pi + 0.25)
    kneel(crew, 1, lean=0.22)
    crew.set_expression(1, "flat")
    crew.brows_pose(1, "focus")
    crew.head_pose(1, nod=0.45)
    crew.look(1, 0, -0.03)
    m = mallet("mallet", crew.arms["R"]["hand"], (0, 0, -0.02), (math.pi, 0, 0))
    crew.reach("L", 1, (0.25, -0.5, -0.1), pole=(1, 0, -1))
    f = 1
    up = True
    while f < nf:
        z = 0.15 if up else -0.06
        crew.reach("R", f, (-0.2, -0.5, z), pole=(-1, 0.3, -0.5))
        f += 5 if up else 9
        up = not up
    crew.set_expression(F(2.0), "smile")
    idle(crew, nf, 3)
    crew.finalize()
    # pavers dropping into the gaps along the laying front
    gaps = laying_gaps()
    gaps = [g for g in gaps if -0.6 < (g[0] + g[2]) / 2 < 1.4]
    gaps.sort(key=lambda r: (r[0] + r[2]) / 2)
    rnd = random.Random(7)
    for i, (ax, ay, bx, by, o) in enumerate(gaps):
        c = rnd.choice(BRINDLE)
        p = rbox(f"lay{i}", (bx - ax - 0.006, by - ay - 0.006, 0.06),
                 mat(f"Stack{c}", c, rough=0.6), 0.12, 2, None)
        cx, cy = (ax + bx) / 2, (ay + by) / 2
        f0 = 2 + i * 3
        kf(p, "location", 1, (cx, cy, 0.9))
        kf(p, "location", f0, (cx, cy, 0.9))
        kf(p, "location", f0 + 7, (cx, cy, -0.03))
        kf(p, "location", f0 + 9, (cx, cy, -0.02))
        kf(p, "rotation_euler", f0, (rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3), 0))
        kf(p, "rotation_euler", f0 + 7, (0, 0, 0))
        kf(p, "scale", 1, (0.001, 0.001, 0.001), "CONSTANT")
        kf(p, "scale", f0, (1, 1, 1), "CONSTANT")
    char_light((0.25, -4.6, 0.9), (1.5, -2.0, 2.0), 110)
    cam, tg = camera(scn, 34, 2.2)
    cam_move(cam, tg, [(1, (1.5, -2.2, 0.45), (0.35, -4.15, 0.45), 32),
                       (nf, (1.0, -2.5, 0.6), (0.3, -4.2, 0.55), 36)])


def s5b_level(scn, nf):
    dusk_world(scn)
    front_set("new")
    law = Character("law", "lawrence", (-0.6, -5.0, 0), rot_z=0.0)
    kneel(law, 1, lean=0.35)
    lvl = spirit_level("level", None, (-0.6, -5.72, 0.035), (0, 0, 0), 1.0)
    law.reach("L", 1, (0.35, -0.6, -0.17), pole=(1, 0, -1))
    law.reach("R", 1, (-0.35, -0.6, -0.17), pole=(-1, 0, -1))
    law.reach("L", F(1.4), (0.36, -0.62, -0.15), pole=(1, 0, -1))
    law.head_pose(1, nod=0.42)
    law.look(1, 0, -0.03)
    law.set_expression(1, "flat")
    law.brows_pose(1, "focus")
    law.head_pose(F(1.6), nod=0.42)
    law.head_pose(F(2.0), nod=-0.05, tilt=0.08)
    law.look(F(1.8), 0, -0.03)
    law.look(F(2.1), 0, 0.0)
    law.set_expression(F(2.0), "grin")
    law.brows_pose(F(2.0), "happy")
    law.reach("R", F(1.9), (-0.35, -0.6, -0.17), pole=(-1, 0, -1))
    law.thumbs_up(F(2.35))
    idle(law, nf, 4)
    law.finalize()
    char_light((-0.6, -5.2, 0.8), (1.2, -7.5, 1.8), 100)
    cam, tg = camera(scn, 50, 1.8)
    cam_move(cam, tg, [(1, (0.5, -7.6, 0.32), (-0.6, -5.72, 0.16), 50),
                       (F(1.5), (0.35, -7.5, 0.42), (-0.6, -5.7, 0.2), 50),
                       (F(2.2), (0.1, -7.6, 0.75), (-0.6, -5.3, 0.85), 46),
                       (nf, (0.0, -7.4, 0.8), (-0.6, -5.2, 0.88), 46)])


def s6a_drive(scn, nf):
    dusk_world(scn)
    front_set("new")
    tom = Character("tom", "homeowner", (1.3, -3.4, 0), rot_z=math.pi - 0.3)
    tom.arms_rest(1)
    tom.hip_hand(1, "L")
    tom.hip_hand(1, "R")
    tom.head_pose(1, nod=-0.1, turn=0.1)
    tom.head_pose(nf, nod=-0.15, turn=-0.15)
    idle(tom, nf, 5)
    tom.finalize()
    cam, tg = camera(scn, 28, 4.0)
    cam_move(cam, tg, [(1, (0.6, -7.2, 0.45), (0.4, -4.2, 0.25), 26),
                       (nf, (2.4, -13.8, 4.0), (0.0, -3.0, 1.5), 28)])


def s6b_patio(scn, nf):
    dusk_world(scn)
    garden_set()
    cam, tg = camera(scn, 30, 3.5)
    cam_move(cam, tg, [(1, (-3.4, -6.4, 1.7), (-0.9, -2.1, 0.55), 30),
                       (nf, (-1.4, -6.7, 1.5), (0.2, -1.9, 0.55), 30)])


def s6c_hardland(scn, nf):
    dusk_world(scn)
    garden_set()
    cam, tg = camera(scn, 28, 3.5)
    cam_move(cam, tg, [(1, (4.6, -6.6, 0.7), (3.6, -2.6, 0.55), 30),
                       (nf, (2.9, -7.2, 1.0), (2.2, -3.2, 0.4), 30)])


def s7_finish(scn, nf):
    dusk_world(scn)
    front_set("new")
    law = Character("law", "lawrence", (-0.5, -4.7, 0), rot_z=0.35)
    kneel(law, 1, lean=0.35)
    spirit_level("level", None, (-0.73, -5.3, 0.035), (0, 0, 0.35), 1.0)
    law.reach("L", 1, (0.35, -0.6, -0.17), pole=(1, 0, -1))
    law.reach("R", 1, (-0.35, -0.6, -0.17), pole=(-1, 0, -1))
    law.head_pose(1, nod=0.42)
    law.look(1, 0, -0.03)
    law.set_expression(1, "flat")
    law.brows_pose(1, "focus")
    law.head_pose(F(2.6), nod=0.42)
    law.head_pose(F(3.1), nod=0.0, turn=-0.2)
    law.set_expression(F(3.0), "grin")
    law.brows_pose(F(3.0), "happy")
    law.reach("R", F(2.9), (-0.35, -0.6, -0.17), pole=(-1, 0, -1))
    law.thumbs_up(F(3.4))
    crew = Character("crew", "crew", (1.5, -6.1, 0), rot_z=-0.5)
    br = broom("broom", crew.arms["R"]["hand"], (0, 0, -0.05), (math.pi * 0.85, 0, 0))
    crew.reach("L", 1, (0.12, -0.35, 0.22), pole=(1, 0, -0.5))
    f = 1
    i = 0
    while f < nf:
        y = -0.55 if i % 2 else -0.25
        crew.reach("R", f, (-0.15, y, 0.05), pole=(-1, 0.3, -0.5))
        kf(crew.torso, "rotation_euler", f, (0.25 if i % 2 else 0.12, 0, 0))
        f += 12
        i += 1
    crew.head_pose(1, nod=0.35)
    crew.set_expression(1, "smile")
    for c, s in ((law, 6), (crew, 7)):
        idle(c, nf, s)
        c.finalize()
    char_light((0.4, -5.2, 1.0), (-1.5, -9.0, 2.8), 140)
    cam, tg = camera(scn, 32, 3.0)
    cam_move(cam, tg, [(1, (-2.6, -9.6, 1.5), (0.2, -5.3, 0.75), 34),
                       (nf, (2.2, -9.8, 1.7), (0.4, -5.3, 0.85), 36)])


def s8_reveal(scn, nf):
    dusk_world(scn)
    front_set("new")
    tom = Character("tom", "homeowner", (0.7, -4.6, 0), rot_z=-0.1)
    law = Character("law", "lawrence", (-0.8, -4.9, 0), rot_z=0.35)
    crew = Character("crew", "crew", (-2.0, -5.5, 0), rot_z=0.45)
    tom.arms_rest(1)
    tom.set_expression(1, "grin")
    tom.brows_pose(1, "happy")
    tom.thumbs_up(F(0.3))
    tom.thumbs_up(F(0.6), "L")
    kf(tom.hips, "location", F(0.5), (0, 0, 0.52))
    kf(tom.hips, "location", F(0.7), (0, 0, 0.66))
    kf(tom.hips, "location", F(0.9), (0, 0, 0.52))
    tom.head_pose(1, tilt=0.1)
    tom.head_pose(F(1.5), tilt=-0.08)
    tom.head_pose(nf, tilt=0.06)
    law.arms_rest(1)
    end = law.wave(F(0.6), 4, "R", 11)
    law.arms_rest(end + 8)
    law.set_expression(1, "grin")
    law.brows_pose(1, "happy")
    crew.arms_rest(1)
    crew.hip_hand(1, "L")
    crew.thumbs_up(F(1.2))
    crew.set_expression(1, "grin")
    for c, s in ((tom, 8), (law, 9), (crew, 10)):
        idle(c, nf, s)
        c.finalize()
    char_light((0.0, -4.8, 1.4), (0.5, -9.0, 3.0), 160)
    cam, tg = camera(scn, 34, 3.5)
    cam_move(cam, tg, [(1, (0.5, -9.4, 1.7), (-0.1, -4.8, 1.55), 34),
                       (nf, (1.9, -14.6, 3.3), (0.0, -3.8, 1.9), 29)])


def s9_cta(scn, nf):
    world(scn, (0.012, 0.018, 0.045), (0.004, 0.005, 0.012))
    scn.view_settings.exposure = -0.6
    m = mascot("paver", (0, 0, 1.55))
    area("key", (-3, -4, 4), (0, 0, 1.5), 420, (1, 0.85, 0.7), 2)
    area("rim", (3, 3, 3), (0, 0, 1.5), 900, (1, 0.55, 0.25), 2)
    area("rim2", (-3, 3, 2), (0, 0, 1.5), 500, (0.4, 0.5, 1.0), 2)
    root, body = m["root"], m["body"]
    for f in range(1, nf + 40, 40):
        kf(root, "location", f, (0, 0, 1.55))
        kf(root, "location", f + 20, (0, 0, 1.68))
    for f in range(1, nf + 60, 60):
        kf(body, "rotation_euler", f, (0.05, 0.10, -0.12))
        kf(body, "rotation_euler", f + 30, (-0.03, -0.08, 0.12))
    # entrance: pop in
    kf(root, "scale", 1, (0.2, 0.2, 0.2))
    kf(root, "scale", 9, (1.08, 1.08, 1.08))
    kf(root, "scale", 14, (1, 1, 1))
    # wave arms
    for f in range(1, nf, 12):
        kf(m["arms"][1], "rotation_euler", f, (0, -0.2, 0))
        kf(m["arms"][1], "rotation_euler", f + 6, (0, -1.1, 0))
    kf(m["arms"][0], "rotation_euler", 1, (0, 0.3, 0))
    # wink at ~33.5 s global (local 1.85 s) and again near the end
    from lib import visible
    wink_ranges = [(F(1.85), F(2.35)), (F(4.2), F(4.6))]
    visible(m["wink"], wink_ranges)
    right_eye = m["eyes"][1]
    for ob in [right_eye] + list(right_eye.children_recursive):
        if ob.type == "MESH":
            on = [(1, wink_ranges[0][0]), (wink_ranges[0][1], wink_ranges[1][0]),
                  (wink_ranges[1][1], nf + 10)]
            visible(ob, on)
    for eg in m["eyes"]:
        for f in (F(3.2),):
            for ff, s in ((f - 2, 1.0), (f, 0.1), (f + 3, 1.0)):
                kf(eg, "scale", ff, (1, 1, s))
    cam, tg = camera(scn, 50, 4.0)
    cam_move(cam, tg, [(1, (0, -7.6, 1.3), (0, 0, 1.0), 50),
                       (nf, (0, -7.0, 1.3), (0, 0, 1.02), 50)])


SHOTS = {f.__name__: f for f in (s1_exterior, s2_worry, s3_region, s4_team, s5a_laying,
                                  s5b_level, s6a_drive, s6b_patio, s6c_hardland, s7_finish,
                                  s8_reveal, s9_cta)}
