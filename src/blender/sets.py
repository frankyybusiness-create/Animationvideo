"""Environment sets, props, lights and camera helpers."""
import math
import random

import bmesh
import bpy
from mathutils import Vector

from lib import (_link, _mesh_obj, brick_mat, build_into, cracked_concrete_mat,
                 cylinder, empty, glow, kf, lawn_mat, mat, plane, rbox, sphere,
                 vcol_mat)


# --------------------------------------------------------------------------
# Lights & camera
# --------------------------------------------------------------------------
def aim(ob, target):
    d = Vector(target) - Vector(ob.location)
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def area(name, loc, target, energy, color=(1, 1, 1), size=2.0):
    d = bpy.data.lights.new(name, "AREA")
    d.energy = energy
    d.color = color
    d.size = size
    o = bpy.data.objects.new(name, d)
    o.location = loc
    o.visible_camera = False
    o.visible_glossy = False
    _link(o)
    aim(o, target)
    return o


def point(name, loc, energy, color=(1, 0.7, 0.4), radius=0.1):
    d = bpy.data.lights.new(name, "POINT")
    d.energy = energy
    d.color = color
    d.shadow_soft_size = radius
    o = bpy.data.objects.new(name, d)
    o.location = loc
    o.visible_camera = False
    o.visible_glossy = False
    return _link(o)


def sun(name, rot, energy, color):
    d = bpy.data.lights.new(name, "SUN")
    d.energy = energy
    d.color = color
    d.angle = math.radians(3)
    o = bpy.data.objects.new(name, d)
    o.rotation_euler = rot
    return _link(o)


def camera(scn, lens=35, fstop=2.8):
    c = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    c.data.lens = lens
    c.data.sensor_width = 36
    c.data.sensor_fit = "VERTICAL"
    c.data.sensor_height = 36
    c.data.dof.use_dof = True
    c.data.dof.aperture_fstop = fstop
    c.data.clip_end = 400
    _link(c)
    scn.camera = c
    tgt = empty("cam_target", (0, 0, 1))
    con = c.constraints.new("TRACK_TO")
    con.target = tgt
    con.track_axis = "TRACK_NEGATIVE_Z"
    con.up_axis = "UP_Y"
    c.data.dof.focus_object = tgt
    return c, tgt


def cam_move(cam, tgt, keys):
    """keys: list of (frame, cam_loc, target_loc[, lens])."""
    for k in keys:
        f, cl, tl = k[0], k[1], k[2]
        kf(cam, "location", f, cl)
        kf(tgt, "location", f, tl)
        if len(k) > 3:
            cam.data.lens = k[3]
            cam.data.keyframe_insert("lens", frame=f)


def lights_night(scn):
    scn.view_settings.exposure = -1.6
    area("key", (-4, -6, 4), (0, 0, 1.2), 260, (1.0, 0.72, 0.48), 3)
    area("rim", (4, 5, 4), (0, 0, 1.2), 700, (0.4, 0.55, 1.0), 3)
    area("fill", (5, -5, 2), (0, 0, 1), 35, (0.5, 0.6, 1.0), 4)


def lights_dusk(scn):
    scn.view_settings.exposure = -1.1
    sun("sun", (math.radians(80), 0, math.radians(-55)), 1.1, (1.0, 0.55, 0.28))
    area("key", (-4, -6, 4), (0, 0, 1.2), 240, (1.0, 0.8, 0.6), 3)
    area("rim", (4, 5, 4), (0, 0, 1.2), 500, (0.55, 0.6, 1.0), 3)


# --------------------------------------------------------------------------
# Block paving (90 degree herringbone, axis aligned so edges cut cleanly)
# --------------------------------------------------------------------------
BRINDLE = [(0.30, 0.09, 0.045), (0.22, 0.07, 0.04), (0.36, 0.14, 0.06),
           (0.27, 0.11, 0.06), (0.17, 0.06, 0.04), (0.40, 0.17, 0.08)]
CHARCOAL = [(0.15, 0.14, 0.13), (0.17, 0.16, 0.15), (0.13, 0.125, 0.12)]


def _herringbone_rects(x0, y0, x1, y1, w):
    """Yield (ax, ay, bx, by, orient) clipped rectangles covering region."""
    out = []
    n_range = int((x1 - x0 + y1 - y0) / w) + 6
    for n in range(-n_range, n_range):
        for m in range(-n_range, n_range):
            ox = (n + 2 * m) * w + x0
            oy = (n - 2 * m) * w + y0
            for (dx, dy, sx, sy, o) in ((0, 0, 2 * w, w, "H"), (0, w, w, 2 * w, "V")):
                ax, ay = ox + dx, oy + dy
                bx, by = ax + sx, ay + sy
                cax, cay = max(ax, x0), max(ay, y0)
                cbx, cby = min(bx, x1), min(by, y1)
                if cbx - cax > 0.02 and cby - cay > 0.02:
                    out.append((cax, cay, cbx, cby, o))
    return out


def paving(name, x0, y0, x1, y1, w=0.1, h=0.06, gap=0.006, border=True,
           seed=1, palette=None, z=0.0, keep=None):
    """Build one mesh of individual pavers with per-paver colour.
    drop: optional (dx, dy) laying direction; returns list of paver centres
    so shots can spawn the "being laid" pavers individually."""
    rnd = random.Random(seed)
    palette = palette or BRINDLE
    rects = []
    if border:
        bw = 2 * w
        # soldier course border in charcoal
        rects += [(x0, y, x0 + bw, y + w, "B") for y in _steps(y0, y1, w)]
        rects += [(x1 - bw, y, x1, y + w, "B") for y in _steps(y0, y1, w)]
        rects += [(x, y0, x + w, y0 + bw, "B") for x in _steps(x0 + bw, x1 - bw, w)]
        rects += [(x, y1 - bw, x + w, y1, "B") for x in _steps(x0 + bw, x1 - bw, w)]
        rects += _herringbone_rects(x0 + bw, y0 + bw, x1 - bw, y1 - bw, w)
    else:
        rects += _herringbone_rects(x0, y0, x1, y1, w)
    if keep is not None:
        rects = [r for r in rects if keep(r)]
    bm = bmesh.new()
    col = bm.loops.layers.float_color.new("Col")
    g = gap / 2
    for (ax, ay, bx, by, o) in rects:
        hz = h * (1 + rnd.uniform(-0.03, 0.03))
        c = rnd.choice(CHARCOAL if o == "B" else palette)
        k = rnd.uniform(0.85, 1.15)
        c = (c[0] * k, c[1] * k, c[2] * k, 1)
        vs = [bm.verts.new((x, y, zz)) for zz in (z - hz, z) for (x, y) in
              ((ax + g, ay + g), (bx - g, ay + g), (bx - g, by - g), (ax + g, by - g))]
        faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5),
                 (2, 3, 7, 6), (3, 0, 4, 7)]
        for fidx in faces:
            f = bm.faces.new([vs[i] for i in fidx])
            for lp in f.loops:
                lp[col] = c
    ob = _mesh_obj(name, bm, vcol_mat("Paving"), None, (0, 0, 0), (0, 0, 0),
                   smooth=False)
    mod = ob.modifiers.new("bevel", "BEVEL")
    mod.width = 0.008
    mod.segments = 2
    mod.limit_method = "ANGLE"
    # joint sand bed below
    plane(name + "_sand", (x1 - x0, y1 - y0), mat("JointSand", (0.16, 0.13, 0.09),
          rough=0.95, bump=0.3, bump_scale=200),
          loc=((x0 + x1) / 2, (y0 + y1) / 2, z - h * 0.6))
    return ob, rects


def _steps(a, b, w):
    out = []
    v = a
    while v < b - 1e-6:
        out.append(v)
        v += w
    return out


def slabs(name, x0, y0, x1, y1, size=0.6, seed=3, z=0.04):
    """Natural sandstone patio slabs (random-ish buff colours)."""
    rnd = random.Random(seed)
    bm = bmesh.new()
    col = bm.loops.layers.float_color.new("Col")
    tones = [(0.55, 0.45, 0.32), (0.62, 0.52, 0.38), (0.48, 0.40, 0.30),
             (0.58, 0.50, 0.40), (0.66, 0.56, 0.42)]
    y = y0
    row = 0
    while y < y1 - 0.01:
        x = x0 - (size / 2 if row % 2 else 0)
        while x < x1 - 0.01:
            ax, ay, bx, by = max(x, x0), y, min(x + size, x1), min(y + size, y1)
            g = 0.006
            c = (*rnd.choice(tones), 1)
            hz = 0.04
            vs = [bm.verts.new((px, py, zz)) for zz in (z - hz, z) for (px, py) in
                  ((ax + g, ay + g), (bx - g, ay + g), (bx - g, by - g), (ax + g, by - g))]
            for fidx in [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5),
                         (2, 3, 7, 6), (3, 0, 4, 7)]:
                f = bm.faces.new([vs[i] for i in fidx])
                for lp in f.loops:
                    lp[col] = c
            x += size
        y += size
        row += 1
    ob = _mesh_obj(name, bm, vcol_mat("Sandstone", rough=0.8, coat=0.0, bump=0.4),
                   None, (0, 0, 0), (0, 0, 0), smooth=False)
    mod = ob.modifiers.new("bevel", "BEVEL")
    mod.width = 0.01
    mod.segments = 2
    plane(name + "_grout", (x1 - x0, y1 - y0), mat("Grout", (0.18, 0.17, 0.16), rough=0.9),
          loc=((x0 + x1) / 2, (y0 + y1) / 2, z - 0.025))
    return ob


# --------------------------------------------------------------------------
# House
# --------------------------------------------------------------------------
def window(name, w, h, parent, loc, lit=True, warm=1.3):
    frame_m = mat("uPVC", (0.85, 0.85, 0.83), rough=0.35, coat=0.3)
    glass = (glow("WinLit", (1.0, 0.5, 0.18), warm) if lit else
             mat("WinDark", (0.02, 0.025, 0.04), rough=0.05, coat=1.0))
    rbox(name + "_fr", (w + 0.12, 0.12, h + 0.12), frame_m, 0.15, 3, parent, loc)
    plane(name + "_gl", (w, h), glass, (loc[0], loc[1] - 0.065, loc[2]),
          (math.pi / 2, 0, 0), parent)
    # curtains drawn to the sides (sell an interior behind the glass)
    cur = mat("Curtain", (0.32, 0.05, 0.04) if lit else (0.05, 0.06, 0.1), rough=0.9,
              sheen=0.5)
    for sx in (-1, 1):
        rbox(name + f"_cur{sx}", (w * 0.2, 0.03, h * 0.96), cur, 0.3, 2, parent,
             (loc[0] + sx * w * 0.39, loc[1] - 0.05, loc[2]))
    # mullion + sill
    rbox(name + "_mu", (0.05, 0.03, h), frame_m, 0.2, 2, parent,
         (loc[0], loc[1] - 0.075, loc[2]))
    rbox(name + "_sill", (w + 0.25, 0.2, 0.06), mat("Sill", (0.7, 0.68, 0.64), rough=0.6),
         0.2, 2, parent, (loc[0], loc[1] - 0.08, loc[2] - h / 2 - 0.08))


def house(name, x=0.0, lit=(True, True, True, False), door_col=(0.02, 0.06, 0.16),
          brick=None, mirror=False, porch_light=True, simple=False):
    """Two-storey British semi. Front face at y=0, house extends +y.
    Footprint 6 wide (x-3..3) x 7 deep."""
    root = empty(name, (x, 0, 0))
    root.scale = (-1 if mirror else 1, 1, 1)
    bm_ = brick or brick_mat()
    W, D, H = 6.0, 7.0, 5.4
    rbox(name + "_walls", (W, D, H), bm_, 0.002, 1, root, (0, D / 2, H / 2))
    # plinth course
    rbox(name + "_plinth", (W + 0.04, D + 0.04, 0.3), brick_mat("BrickDark",
         (0.18, 0.06, 0.04), (0.24, 0.09, 0.05)), 0.01, 1, root, (0, D / 2, 0.15))
    # roof (gable, ridge along x)
    roof_m = mat("Slate", (0.06, 0.065, 0.075), rough=0.55, bump=0.25, bump_scale=8)
    for side in (1, -1):
        r = rbox(name + f"_roof{side}", (W + 0.5, 4.3, 0.14), roof_m, 0.1, 2, root,
                 (0, D / 2 - side * 1.75, H + 1.25), (side * math.radians(38), 0, 0))
    # gable triangle walls
    bm = bmesh.new()
    for sx in (-W / 2 + 0.01, W / 2 - 0.01):
        vs = [bm.verts.new((sx, 0.05, H)), bm.verts.new((sx, D - 0.05, H)),
              bm.verts.new((sx, D / 2, H + 2.6))]
        bm.faces.new(vs)
    _mesh_obj(name + "_gable", bm, bm_, root, (0, 0, 0), (0, 0, 0), smooth=False)
    rbox(name + "_chimney", (0.7, 0.5, 1.6), bm_, 0.02, 1, root,
         (W / 2 - 0.5, D / 2, H + 2.6))
    for i in (-0.15, 0.15):
        cylinder(name + f"_pot{i}", 0.09, 0.35, mat("Pot", (0.3, 0.1, 0.05)), root,
                 (W / 2 - 0.5 + i, D / 2, H + 3.55))
    rbox(name + "_ridge", (W + 0.5, 0.25, 0.18), roof_m, 0.3, 2, root, (0, D / 2, H + 2.55))
    # fascia / gutter
    rbox(name + "_gutter", (W + 0.4, 0.18, 0.16), mat("uPVC", (0.85, 0.85, 0.83)),
         0.3, 2, root, (0, -0.2, H - 0.05))
    # windows
    ww, wh = 1.5, 1.25
    window(name + "_w1", ww, wh, root, (-1.4, -0.0, 3.9), lit[0])
    window(name + "_w2", ww, wh, root, (1.4, -0.0, 3.9), lit[1])
    window(name + "_w3", 1.9, 1.35, root, (-1.2, -0.0, 1.5), lit[2])
    # door + canopy
    door_m = mat(f"Door{door_col}", door_col, rough=0.3, coat=0.6)
    rbox(name + "_doorfr", (1.15, 0.14, 2.2), mat("uPVC", (0.85, 0.85, 0.83)),
         0.1, 2, root, (1.6, -0.0, 1.1))
    rbox(name + "_door", (0.95, 0.1, 2.05), door_m, 0.05, 2, root, (1.6, -0.06, 1.05))
    plane(name + "_doorgl", (0.5, 0.35), glow("DoorGlass", (1.0, 0.7, 0.35), 3.0),
          (1.6, -0.115, 1.75), (math.pi / 2, 0, 0), root)
    sphere(name + "_knob", 0.04, mat("Brass", (0.8, 0.55, 0.2), metal=1, rough=0.25),
           root, (1.95, -0.13, 1.0))
    rbox(name + "_canopy", (1.6, 0.8, 0.12), mat("Canopy", (0.12, 0.12, 0.13), rough=0.4),
         0.2, 2, root, (1.6, -0.4, 2.45), (math.radians(-8), 0, 0))
    if porch_light:
        sphere(name + "_lamp", 0.07, glow("Lamp", (1.0, 0.75, 0.4), 12), root,
               (2.35, -0.12, 2.1))
        point(name + "_lampL", (x + (2.35 * (-1 if mirror else 1)), -0.4, 2.1), 30,
              (1.0, 0.7, 0.4), 0.1)
    return root


def low_wall(name, x0, x1, y, h=0.55):
    bm_ = brick_mat()
    rbox(name, (x1 - x0, 0.25, h), bm_, 0.02, 1, None, ((x0 + x1) / 2, y, h / 2))
    rbox(name + "_cap", (x1 - x0 + 0.04, 0.32, 0.07), mat("Coping", (0.45, 0.43, 0.4), rough=0.7),
         0.2, 2, None, ((x0 + x1) / 2, y, h + 0.03))


def hedge(name, loc, size, seed=0):
    m = mat("Hedge", (0.025, 0.08, 0.02), rough=0.85, bump=1.0, bump_scale=25)
    return rbox(name, size, m, 0.45, 4, None, loc)


def street(length=40, y=-9.5):
    """Road, kerb, pavement in front of the houses."""
    road = mat("Tarmac", (0.025, 0.025, 0.028), rough=0.35, bump=0.3, bump_scale=60)
    plane("road", (length, 8), road, (0, y - 4, -0.12))
    rbox("kerb", (length, 0.3, 0.14), mat("Kerb", (0.35, 0.34, 0.33), rough=0.7),
         0.15, 2, None, (0, y, -0.06))
    plane("pavement", (length, 1.6), mat("Flags", (0.22, 0.21, 0.2), rough=0.6,
          bump=0.2, bump_scale=10), (0, y + 0.9, 0.0))
    # road markings
    for i in range(-length // 2, length // 2, 4):
        plane(f"mark{i}", (1.8, 0.12), mat("Paint", (0.8, 0.8, 0.75), rough=0.5),
              (i, y - 4, -0.115))


def street_lamp(name, loc, energy=300):
    pole = mat("LampPole", (0.05, 0.06, 0.06), rough=0.4, metal=0.5)
    cylinder(name + "_pole", 0.07, 5.0, pole, None, (loc[0], loc[1], 2.5))
    rbox(name + "_arm", (0.15, 0.9, 0.12), pole, 0.3, 2, None, (loc[0], loc[1] + 0.4, 5.0))
    sphere(name + "_bulb", 0.2, glow("StreetLamp", (1.0, 0.65, 0.3), 30), None,
           (loc[0], loc[1] + 0.75, 4.85), scale=(1, 1, 0.6))
    point(name + "_L", (loc[0], loc[1] + 0.75, 4.6), energy, (1.0, 0.62, 0.3), 0.3)


def front_set(state="old", neighbours=True, seed=0, lit=True):
    """Street of semis. Hero house at x=0, driveway in front (x 0.2..4.8?).
    Driveway region: x -2.6..2.6, y -8.6..-0.3  (state: old / laying / new)."""
    house("hero", 0.0, lit=(lit, True, lit, False))
    if neighbours:
        house("nbL", -6.4, lit=(False, True, True, False), door_col=(0.25, 0.03, 0.03),
              brick=brick_mat("Brick2", (0.42, 0.18, 0.09), (0.5, 0.25, 0.12)))
        house("nbR", 6.4, lit=(True, False, True, False), door_col=(0.05, 0.12, 0.06),
              brick=brick_mat("Brick3", (0.3, 0.12, 0.07), (0.4, 0.17, 0.09)))
        house("nbL2", -12.8, lit=(True, True, False, False))
        house("nbR2", 12.8, lit=(False, True, True, False))
        # houses across the road (window bokeh when looking back)
        for i, x in enumerate((-9.6, -3.2, 3.2, 9.6)):
            h = house(f"opp{i}", x, lit=((True, False, True, False), (False, True, True, False),
                                          (True, True, False, False), (False, True, True, False))[i],
                      porch_light=False)
            h.location.y = -19.0
            h.rotation_euler.z = math.pi
    street()
    street_lamp("lamp1", (-4.2, -9.0, 0))
    street_lamp("lamp2", (8.5, -9.0, 0), 200)
    # garden lawn either side of driveway
    plane("lawnL", (2.8, 8.5), lawn_mat(), (-4.6, -4.3, 0.0))
    plane("lawnR", (2.0, 8.5), lawn_mat(), (4.4, -4.3, 0.0))
    plane("ground", (80, 30), mat("Ground", (0.02, 0.025, 0.02), rough=0.9), (0, 5, -0.02))
    low_wall("wallL", -6.2, -3.4, -8.55)
    hedge("hedgeR", (5.4, -4.3, 0.45), (0.6, 8.0, 0.9))
    hedge("hedgeL", (-6.2, -4.3, 0.4), (0.4, 8.0, 0.8))
    driveway(state, seed)


DRIVE = (-3.2, -8.65, 3.2, -0.25)


def driveway(state, seed=0):
    x0, y0, x1, y1 = DRIVE
    if state == "old":
        rbox("oldslab", (x1 - x0, y1 - y0, 0.1), cracked_concrete_mat(), 0.01, 1, None,
             ((x0 + x1) / 2, (y0 + y1) / 2, -0.05))
        rnd = random.Random(seed)
        weed = mat("Weed", (0.05, 0.2, 0.03), rough=0.7)
        for i in range(45):
            x, y = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
            for j in range(rnd.randint(3, 6)):
                s = rnd.uniform(0.025, 0.06)
                sphere(f"weed{i}_{j}", s, weed, None,
                       (x + rnd.uniform(-0.12, 0.12), y + rnd.uniform(-0.12, 0.12), s * 0.6),
                       scale=(0.5, 0.5, 1.6), rot=(rnd.uniform(-0.5, 0.5), rnd.uniform(-0.5, 0.5), 0),
                       segs=8, rings=6)
        # broken chunks / sunken patch
        chunk = cracked_concrete_mat()
        for i in range(14):
            x, y = rnd.uniform(x0 + 0.5, x1 - 0.5), rnd.uniform(y0 + 1, y1 - 1)
            rbox(f"chunk{i}", (rnd.uniform(0.2, 0.6), rnd.uniform(0.2, 0.5), 0.08), chunk,
                 0.1, 2, None, (x, y, 0.0),
                 (rnd.uniform(-0.15, 0.15), rnd.uniform(-0.15, 0.15), rnd.uniform(0, 3)))
        # puddles
        water = mat("Puddle", (0.02, 0.022, 0.025), rough=0.12, coat=0.5)
        for i, (px, py, s) in enumerate(((-1.6, -3.2, 0.5), (1.6, -6.2, 0.4))):
            sphere(f"puddle{i}", s, water, None, (px, py, 0.003), scale=(1.3, 0.8, 0.004))
    elif state == "new":
        paving("drive", x0, y0, x1, y1, seed=seed)
    elif state == "laying":
        # paved up to LAY_FRONT; sand screed beyond, gaps to be filled by shot
        paving("drive", x0, y0, x1, y1, seed=seed,
               keep=lambda r: r[4] == "B" and r[1] < LAY_FRONT or (r[1] + r[3]) / 2 < LAY_FRONT)
        plane("screed", (x1 - x0, y1 - LAY_FRONT), mat("Screed", (0.42, 0.33, 0.2), rough=0.95,
              bump=0.4, bump_scale=120), loc=((x0 + x1) / 2, (LAY_FRONT + y1) / 2, -0.055))
    return DRIVE


LAY_FRONT = -4.0


def laying_gaps(seed=0):
    """Rects just beyond the laying front (to animate dropping in)."""
    x0, y0, x1, y1 = DRIVE
    rects = _herringbone_rects(x0 + 0.2, y0 + 0.2, x1 - 0.2, y1 - 0.2, 0.1)
    return [r for r in rects if LAY_FRONT <= (r[1] + r[3]) / 2 < LAY_FRONT + 0.3]


def town_set():
    """Aerial neighbourhood made of instanced houses (blue hour)."""
    import bpy as _bpy
    variants = []
    for i, lit in enumerate(((True, False, True, False), (False, True, True, False),
                             (True, True, False, False))):
        coll = _bpy.data.collections.new(f"HouseV{i}")
        build_into(coll)
        house(f"hv{i}", 0.0, lit=lit, porch_light=False,
              door_col=((0.02, 0.06, 0.16), (0.25, 0.03, 0.03), (0.05, 0.12, 0.06))[i],
              brick=brick_mat(f"BrickV{i}", *(((0.36, 0.13, 0.07), (0.48, 0.2, 0.1)),
                                                ((0.42, 0.18, 0.09), (0.5, 0.25, 0.12)),
                                                ((0.3, 0.12, 0.07), (0.4, 0.17, 0.09)))[i]))
        plane(f"hvlawn{i}", (6.2, 8.5), lawn_mat(), (0, -4.3, 0.0))
        build_into(None)
        variants.append(coll)
    rnd = random.Random(5)
    k = 0
    for row_y, rot in ((0.0, 0.0), (-19.0, math.pi), (21.0, math.pi), (40.0, 0.0)):
        for i in range(-7, 8):
            x = i * 6.4
            if row_y == 0.0 and i == 0:
                continue  # hero house built for real
            inst = empty(f"inst{k}", (x, row_y, 0), rot=(0, 0, rot))
            inst.instance_type = "COLLECTION"
            inst.instance_collection = variants[rnd.randrange(3)]
            k += 1
    house("hero", 0.0, lit=(True, True, True, False))
    driveway("old")
    for y in (-9.5,):
        street(120, y)
    plane("road2", (120, 8), mat("Tarmac", (0.025, 0.025, 0.028)), (0, 13.5 - 4, -0.12))
    plane("ground", (200, 200), mat("Ground", (0.02, 0.025, 0.02), rough=0.9), (0, 5, -0.03))
    for i in range(-6, 7, 2):
        street_lamp(f"tl{i}", (i * 6.4 + 3.2, -9.0, 0), 250)
        street_lamp(f"tlb{i}", (i * 6.4, -10.5, 0), 250)
    trunk = mat("Trunk", (0.1, 0.06, 0.03))
    leaf = mat("Leaf", (0.02, 0.07, 0.02), rough=0.8, bump=0.6, bump_scale=10)
    for i in range(24):
        x, y = rnd.uniform(-45, 45), rnd.choice((-12.5, 9.0, 30.0)) + rnd.uniform(-1, 1)
        cylinder(f"trunk{i}", 0.15, 2.4, trunk, None, (x, y, 1.2))
        sphere(f"crown{i}", rnd.uniform(1.2, 1.8), leaf, None, (x, y, 3.2), segs=16, rings=10)


# --------------------------------------------------------------------------
# Props
# --------------------------------------------------------------------------
def mallet(name, parent=None, loc=(0, 0, 0), rot=(0, 0, 0)):
    root = empty(name, loc, parent, rot)
    cylinder(name + "_handle", 0.022, 0.38, mat("Wood", (0.45, 0.25, 0.1), rough=0.6),
             root, (0, 0, 0.0))
    cylinder(name + "_head", 0.06, 0.2, mat("Rubber", (0.02, 0.02, 0.02), rough=0.5),
             root, (0, 0, 0.2), (0, math.pi / 2, 0), bevel=0.01)
    return root


def spirit_level(name, parent=None, loc=(0, 0, 0), rot=(0, 0, 0), length=1.0):
    root = empty(name, loc, parent, rot)
    rbox(name + "_body", (length, 0.04, 0.07), mat("LevelYellow", (0.9, 0.6, 0.02), rough=0.35,
         coat=0.4), 0.2, 2, root)
    rbox(name + "_vial", (0.09, 0.045, 0.03), glow("Vial", (0.3, 1.0, 0.2), 1.5), 0.4, 3,
         root, (0, 0, 0.0))
    return root


def pallet_stack(name, loc, rows=4, seed=4):
    root = empty(name, loc)
    rbox(name + "_pallet", (1.0, 1.0, 0.12), mat("PalletWood", (0.5, 0.36, 0.2), rough=0.8),
         0.05, 1, root, (0, 0, 0.06))
    rnd = random.Random(seed)
    for r in range(rows):
        for i in range(5):
            c = rnd.choice(BRINDLE)
            rbox(f"{name}_b{r}_{i}", (0.95, 0.18, 0.06), mat(f"Stack{c}", c, rough=0.6),
                 0.1, 2, root, (0, -0.4 + i * 0.2, 0.15 + r * 0.065))
    return root


def van(name, loc, rot_z=0.0):
    root = empty(name, loc, rot=(0, 0, rot_z))
    body = mat("VanWhite", (0.8, 0.8, 0.8), rough=0.2, coat=0.8)
    glassm = mat("VanGlass", (0.01, 0.012, 0.02), rough=0.05, coat=1.0)
    rbox(name + "_body", (2.0, 4.8, 1.9), body, 0.12, 4, root, (0, 0, 1.3))
    rbox(name + "_cab", (2.0, 1.3, 1.1), body, 0.25, 4, root, (0, -2.6, 0.95))
    rbox(name + "_wind", (1.85, 0.6, 0.7), glassm, 0.2, 3, root, (0, -2.75, 1.65),
         (math.radians(-30), 0, 0))
    for sx in (1, -1):
        rbox(name + f"_side{sx}", (0.02, 0.9, 0.55), glassm, 0.2, 2, root, (sx * 1.0, -2.3, 1.75))
    tyre = mat("Tyre", (0.015, 0.015, 0.015), rough=0.6)
    for sx in (0.95, -0.95):
        for sy in (-2.3, 1.6):
            cylinder(f"{name}_w{sx}{sy}", 0.38, 0.28, tyre, root, (sx, sy, 0.38),
                     (0, math.pi / 2, 0), bevel=0.05)
    for sx in (0.75, -0.75):
        sphere(f"{name}_hl{sx}", 0.12, glow("HeadL", (1, 0.95, 0.85), 8), root,
               (sx, -3.26, 0.75), scale=(1.3, 0.3, 0.7))
    return root


def broom(name, parent=None, loc=(0, 0, 0), rot=(0, 0, 0)):
    root = empty(name, loc, parent, rot)
    cylinder(name + "_h", 0.02, 1.3, mat("Wood", (0.45, 0.25, 0.1)), root, (0, 0, 0))
    rbox(name + "_head", (0.55, 0.14, 0.1), mat("BroomBlock", (0.5, 0.3, 0.12), rough=0.5), 0.3, 2,
         root, (0, 0, -0.66))
    rbox(name + "_bristle", (0.52, 0.12, 0.14), mat("BroomHead", (0.06, 0.05, 0.04), rough=0.9,
         bump=1.0, bump_scale=300), 0.2, 2, root, (0, 0, -0.77))
    return root


# --------------------------------------------------------------------------
# Back garden: patio + hard landscaping
# --------------------------------------------------------------------------
def garden_set():
    """Back garden behind hero house (we reuse house front as back wall).
    Patio: x -3..3, y -4..-0.2 ; lawn beyond; raised beds + steps."""
    house("hero", 0.0, lit=(True, True, True, False), porch_light=False)
    house("gnL", -6.4, lit=(False, True, True, False), porch_light=False,
          brick=brick_mat("Brick2", (0.42, 0.18, 0.09), (0.5, 0.25, 0.12)))
    house("gnR", 6.4, lit=(True, False, True, False), porch_light=False,
          brick=brick_mat("Brick3", (0.3, 0.12, 0.07), (0.4, 0.17, 0.09)))
    slabs("patio", -3.0, -4.2, 3.0, -0.2, size=0.6)
    # step down to lawn
    stone = mat("StepStone", (0.42, 0.38, 0.32), rough=0.75, bump=0.3, bump_scale=20)
    rbox("step1", (2.4, 0.45, 0.16), stone, 0.08, 2, None, (0.3, -4.45, -0.08))
    plane("lawn", (30, 14), lawn_mat(), (0, -11.5, -0.175))
    # raised brick planters with sleeper edging & plants
    for i, (x, w) in enumerate(((-4.2, 2.2), (4.3, 2.4))):
        rbox(f"bed{i}", (w, 3.6, 0.6), brick_mat(), 0.02, 1, None, (x, -2.2, 0.3))
        rbox(f"bedcap{i}", (w + 0.08, 3.68, 0.07), mat("Coping", (0.45, 0.43, 0.4)), 0.2, 2,
             None, (x, -2.2, 0.62))
        plane(f"soil{i}", (w - 0.2, 3.4), mat("Soil", (0.05, 0.03, 0.02), rough=1), (x, -2.2, 0.6))
        rnd = random.Random(i)
        for j in range(9):
            s = rnd.uniform(0.18, 0.32)
            sphere(f"shrub{i}_{j}", s, mat("Shrub", (0.03, 0.12, 0.03), rough=0.8, bump=0.8,
                   bump_scale=30), None,
                   (x + rnd.uniform(-w / 2 + 0.3, w / 2 - 0.3), -2.2 + rnd.uniform(-1.4, 1.4),
                    0.6 + s * 0.6), scale=(1, 1, 0.85), segs=16, rings=10)
            if j % 3 == 0:
                sphere(f"flower{i}_{j}", 0.06, glow("Flower", (0.9, 0.35, 0.5), 0.3), None,
                       (x + rnd.uniform(-w / 2 + 0.3, w / 2 - 0.3),
                        -2.2 + rnd.uniform(-1.4, 1.4), 0.95), segs=10, rings=6)
    # path to the bottom of garden (block paving strip)
    paving("path", -0.6, -12.0, 1.2, -4.7, border=True, seed=8, z=-0.13)
    # fence panels
    fence = mat("Fence", (0.2, 0.12, 0.06), rough=0.8, bump=0.3, bump_scale=6)
    for side in (-1, 1):
        rbox(f"fence{side}", (0.08, 14.0, 1.8), fence, 0.05, 1, None,
             (side * 6.3, -6.0, 0.9))
    rbox("fenceback", (12.6, 0.08, 1.8), fence, 0.05, 1, None, (0, -13.0, 0.9))
    # garden furniture: table + chairs
    wood = mat("Teak", (0.35, 0.18, 0.08), rough=0.45, coat=0.3)
    cylinder("table_top", 0.55, 0.06, wood, None, (-1.0, -2.3, 0.75))
    cylinder("table_leg", 0.05, 0.72, wood, None, (-1.0, -2.3, 0.38))
    for k, (dx, dy, rz) in enumerate(((-0.9, 0, 1.57), (0.9, 0, -1.57), (0, -0.9, 0))):
        c = empty(f"chair{k}", (-1.0 + dx, -2.3 + dy, 0), rot=(0, 0, rz))
        rbox(f"chair{k}_seat", (0.5, 0.5, 0.06), wood, 0.2, 2, c, (0, 0, 0.45))
        rbox(f"chair{k}_back", (0.5, 0.06, 0.5), wood, 0.2, 2, c, (0, 0.24, 0.72))
        for lx in (-0.2, 0.2):
            for ly in (-0.2, 0.2):
                rbox(f"chair{k}_l{lx}{ly}", (0.05, 0.05, 0.45), wood, 0.3, 1, c,
                     (lx, ly, 0.22))
    # festoon string lights (warm bulbs along a catenary)
    for line, (xa, xb, y) in enumerate(((-6.2, 6.2, -3.6), (-6.2, 6.2, -6.2))):
        n = 16
        for i in range(n + 1):
            t = i / n
            x = xa + (xb - xa) * t
            z = 2.6 - 0.6 * math.sin(math.pi * t)
            sphere(f"bulb{line}_{i}", 0.04, glow("Festoon", (1.0, 0.7, 0.35), 15), None,
                   (x, y, z), segs=10, rings=6)
        point(f"festoonL{line}", (0, y, 2.1), 60, (1.0, 0.68, 0.35), 0.5)
    # outdoor wall lights
    for x in (-2.5, 2.5):
        sphere(f"wl{x}", 0.06, glow("Lamp", (1.0, 0.75, 0.4), 12), None, (x, -0.1, 2.2))
        point(f"wlL{x}", (x, -0.5, 2.2), 35, (1.0, 0.7, 0.4), 0.1)


# --------------------------------------------------------------------------
# Mascot: a cheerful block paver
# --------------------------------------------------------------------------
def mascot(name="paver", loc=(0, 0, 0)):
    clay = mat("PaverClay", (0.5, 0.13, 0.05), rough=0.35, sss=0.15, coat=0.5)
    root = empty(name, loc)
    body = empty(name + "_body", (0, 0, 0), root)
    rbox(name + "_block", (1.0, 0.5, 1.5), clay, 0.22, 6, body)
    # chamfer groove (spacer nibs) like a real paver
    for z in (-0.4, 0.4):
        for sx in (-1, 1):
            rbox(f"{name}_nib{z}{sx}", (0.04, 0.2, 0.18), clay, 0.4, 3, body,
                 (sx * 0.51, 0, z))
    white = mat("EyeWhite", (0.92, 0.92, 0.9), rough=0.15, coat=0.6)
    pupil = mat("Pupil", (0.005, 0.005, 0.005), rough=0.05, coat=1.0)
    spec = mat("EyeSpec", (1, 1, 1), emit=(1, 1, 1), emit_strength=6)
    face = empty(name + "_face", (0, -0.25, 0.1), body)
    eyes = []
    for sx in (-1, 1):
        eg = empty(f"{name}_eye{sx}", (sx * 0.21, 0, 0.14), face)
        sphere(f"{name}_pup{sx}", 0.115, pupil, eg, scale=(1, 0.4, 1.15))
        sphere(f"{name}_sp{sx}", 0.034, spec, eg, loc=(0.04, -0.045, 0.05), segs=12, rings=8)
        sphere(f"{name}_sp2{sx}", 0.016, spec, eg, loc=(-0.04, -0.045, -0.045), segs=8, rings=6)
        eyes.append(eg)
    blush = mat("Blush", (0.85, 0.30, 0.25), rough=0.6)
    for sx in (-1, 1):
        sphere(f"{name}_bl{sx}", 0.09, mat("MBlush", (0.9, 0.35, 0.3), rough=0.6), face,
               (sx * 0.3, 0.0, -0.06), scale=(1.2, 0.12, 0.65))
    mouth = empty(name + "_mouth", (0, -0.005, -0.1), face)
    sphere(name + "_mo", 0.13, mat("Mouth", (0.12, 0.02, 0.02)), mouth, scale=(0.9, 0.15, 0.7),
           loc=(0, 0, -0.02))
    sphere(name + "_tg", 0.05, mat("Tongue", (0.75, 0.22, 0.2)), mouth, loc=(0, -0.012, -0.06),
           scale=(1.1, 0.3, 0.5))
    # wink lid: a closed-eye arc for the right eye, toggled with visibility
    from lib import tube
    wink = tube(name + "_wink", [(0.11, -0.01, 0.13), (0.21, -0.025, 0.19), (0.31, -0.01, 0.13)],
                0.022, pupil, face)
    # stubby limbs
    arms = []
    for sx in (-1, 1):
        a = empty(f"{name}_arm{sx}", (sx * 0.5, 0, -0.05), body)
        rbox(f"{name}_armm{sx}", (0.13, 0.13, 0.32), clay, 0.48, 4, a, (sx * 0.06, 0, -0.12),
             (0, sx * 0.5, 0))
        arms.append(a)
    for sx in (-1, 1):
        rbox(f"{name}_leg{sx}", (0.15, 0.15, 0.3), clay, 0.48, 4, body, (sx * 0.22, 0, -0.85))
    return dict(root=root, body=body, eyes=eyes, wink=wink, arms=arms, face=face)
