"""Stylised chunky-toy cartoon characters.

Same design principles as the reference (oversized rounded-block head, big
glossy eyes, small soft body, tactile fabric materials) but an original cast:

* homeowner  - "Tom": swept chestnut quiff, rosy cheeks, forest-green knit
               jumper with white collar, jeans. No hat, no glasses.
* lawrence   - navy cap, short dark beard, hi-vis yellow vest over navy polo.
* crew       - ginger hair, hi-vis vest, grey work trousers.
"""
import math

import bpy
from mathutils import Quaternion, Vector

from lib import (_principled, cylinder, empty, kf, knit_mat, mat, rbox,
                 sphere, tube, visible, _MATS)


def hivis_mat():
    """Yellow hi-vis with two reflective bands (object-space Z stripes)."""
    if "HiVis" in _MATS:
        return _MATS["HiVis"]
    m, nt, p = _principled("HiVis")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "CONSTANT"
    el = ramp.color_ramp.elements
    el[0].position = 0.0
    el[0].color = (0, 0, 0, 1)
    for pos, v in ((0.30, 1), (0.40, 0), (0.62, 1), (0.72, 0)):
        e = el.new(pos)
        e.color = (v, v, v, 1)
    mr = nt.nodes.new("ShaderNodeMapRange")  # z -0.21..0.21 -> 0..1
    mr.inputs["From Min"].default_value = -0.21
    mr.inputs["From Max"].default_value = 0.21
    nt.links.new(sep.outputs["Z"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], ramp.inputs["Fac"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs[6].default_value = (0.9, 0.78, 0.02, 1)
    mix.inputs[7].default_value = (0.62, 0.63, 0.66, 1)
    nt.links.new(ramp.outputs["Color"], mix.inputs["Factor"])
    nt.links.new(mix.outputs[2], p.inputs["Base Color"])
    p.inputs["Emission Color"].default_value = (0.5, 0.45, 0.0, 1)
    p.inputs["Emission Strength"].default_value = 0.15
    mr2 = nt.nodes.new("ShaderNodeMapRange")
    mr2.inputs["To Min"].default_value = 0.6
    mr2.inputs["To Max"].default_value = 0.2
    nt.links.new(ramp.outputs["Color"], mr2.inputs["Value"])
    nt.links.new(mr2.outputs["Result"], p.inputs["Roughness"])
    nt.links.new(ramp.outputs["Color"], p.inputs["Metallic"])
    _MATS["HiVis"] = m
    return m


L1, L2 = 0.26, 0.27

SKIN = (0.84, 0.45, 0.27)

STYLES = {
    "homeowner": dict(
        hair=(0.16, 0.07, 0.03), top=("knit", (0.05, 0.18, 0.09)),
        legs=(0.06, 0.10, 0.22), shoes=(0.18, 0.08, 0.04),
        cap=None, beard=False, vest=False, collar=True, hairstyle="quiff"),
    "lawrence": dict(
        hair=(0.05, 0.035, 0.025), top=("fabric", (0.03, 0.05, 0.16)),
        legs=(0.05, 0.05, 0.06), shoes=(0.05, 0.04, 0.03),
        cap=(0.03, 0.06, 0.2), beard=True, vest=True, collar=False,
        hairstyle="short"),
    "crew": dict(
        hair=(0.35, 0.10, 0.02), top=("fabric", (0.08, 0.08, 0.09)),
        legs=(0.12, 0.12, 0.13), shoes=(0.06, 0.04, 0.03),
        cap=None, beard=False, vest=True, collar=False, hairstyle="crop"),
}


class Character:
    def __init__(self, name, style="homeowner", loc=(0, 0, 0), rot_z=0.0):
        st = STYLES[style]
        self.name = name
        self.style = style
        skin = mat("Skin", SKIN, rough=0.45, sss=0.25, coat=0.1)
        hair = mat(f"Hair_{style}", st["hair"], rough=0.6, bump=0.5,
                   bump_scale=120)
        kind, tcol = st["top"]
        top = (knit_mat(f"Top_{style}", tcol) if kind == "knit" else
               mat(f"Top_{style}", tcol, rough=0.8, sheen=0.4, bump=0.15,
                   bump_scale=200))
        legs_m = mat(f"Legs_{style}", st["legs"], rough=0.75, bump=0.2,
                     bump_scale=150)
        shoe = mat(f"Shoe_{style}", st["shoes"], rough=0.35, coat=0.3)
        white = mat("EyeWhite", (0.92, 0.92, 0.9), rough=0.15, coat=0.6)
        iris = mat(f"Iris_{style}", (0.10, 0.06, 0.03), rough=0.1, coat=1.0)
        pupil = mat("Pupil", (0.005, 0.005, 0.005), rough=0.05, coat=1.0)
        spec = mat("EyeSpec", (1, 1, 1), emit=(1, 1, 1), emit_strength=6)
        mouth = mat("Mouth", (0.12, 0.02, 0.02), rough=0.4)
        blush = mat("Blush", (0.85, 0.30, 0.25), rough=0.6, alpha=1.0)

        self.root = empty(f"{name}_root", loc, rot=(0, 0, rot_z))
        r = self.root
        # ---- legs
        self.hips = empty(f"{name}_hips", (0, 0, 0.52), r)
        self.legs = []
        for side, x in (("L", 0.13), ("R", -0.13)):
            piv = empty(f"{name}_leg{side}", (x, 0, 0), self.hips)
            rbox(f"{name}_thigh{side}", (0.19, 0.2, 0.5), legs_m, 0.45,
                 parent=piv, loc=(0, 0, -0.24))
            rbox(f"{name}_shoe{side}", (0.22, 0.32, 0.12), shoe, 0.45,
                 parent=piv, loc=(0, -0.05, -0.48))
            self.legs.append(piv)
        # ---- torso
        self.torso = empty(f"{name}_torso", (0, 0, 0.0), self.hips)
        rbox(f"{name}_body", (0.6, 0.4, 0.55), top, 0.42,
             parent=self.torso, loc=(0, 0, 0.26))
        if st["vest"]:
            rbox(f"{name}_vest", (0.63, 0.43, 0.42), hivis_mat(), 0.4,
                 parent=self.torso, loc=(0, 0, 0.3))
        if st["collar"]:
            shirt = mat("Shirt", (0.9, 0.9, 0.88), rough=0.7)
            for side in (1, -1):
                rbox(f"{name}_collar{side}", (0.14, 0.05, 0.09), shirt, 0.3,
                     parent=self.torso, loc=(side * 0.07, -0.17, 0.52),
                     rot=(0.3, 0, side * 0.5))
        # ---- arms (shoulder -> elbow -> hand)
        self.arms = {}
        for side, x in (("L", 0.33), ("R", -0.33)):
            sh = empty(f"{name}_sh{side}", (x, 0, 0.46), self.torso)
            rbox(f"{name}_upper{side}", (0.15, 0.15, 0.3), top, 0.48,
                 parent=sh, loc=(0, 0, -0.12))
            el = empty(f"{name}_el{side}", (0, 0, -0.26), sh)
            rbox(f"{name}_fore{side}", (0.14, 0.14, 0.26), top, 0.48,
                 parent=el, loc=(0, 0, -0.1))
            hand = empty(f"{name}_hand{side}", (0, 0, -0.27), el)
            sphere(f"{name}_palm{side}", 0.085, skin, hand, scale=(1, 0.8, 1.05))
            # thumb
            rbox(f"{name}_thumb{side}", (0.05, 0.05, 0.1), skin, 0.48,
                 parent=hand, loc=(-math.copysign(0.065, x), -0.03, 0.02),
                 rot=(0, math.copysign(0.5, x), 0))
            self.arms[side] = dict(sh=sh, el=el, hand=hand)
        # ---- head
        self.neck = empty(f"{name}_neck", (0, 0, 0.55), self.torso)
        self.head = empty(f"{name}_head", (0, 0, 0.0), self.neck)
        h = self.head
        rbox(f"{name}_neckm", (0.18, 0.18, 0.12), skin, 0.45, parent=h,
             loc=(0, 0, 0.03))
        rbox(f"{name}_skull", (0.66, 0.6, 0.64), skin, 0.33, segs=6,
             parent=h, loc=(0, 0, 0.36))
        for side in (1, -1):  # ears
            sphere(f"{name}_ear{side}", 0.07, skin, h,
                   loc=(side * 0.33, 0.02, 0.36), scale=(0.5, 0.8, 1.1))
            sphere(f"{name}_cheek{side}", 0.06, blush, h,
                   loc=(side * 0.19, -0.292, 0.25), scale=(1.2, 0.15, 0.7))
        sphere(f"{name}_nose", 0.055, skin, h, loc=(0, -0.31, 0.30),
               scale=(1.0, 0.9, 0.85))
        # ---- eyes (group empties so we can blink / look)
        self.eyes = []
        for side in (1, -1):
            eg = empty(f"{name}_eye{side}", (side * 0.135, -0.27, 0.40), h)
            sphere(f"{name}_white{side}", 0.085, white, eg,
                   scale=(1, 0.55, 1.12))
            look = empty(f"{name}_look{side}", (0, 0, 0), eg)
            sphere(f"{name}_iris{side}", 0.06, iris, look, loc=(0, -0.03, -0.005),
                   scale=(1, 0.5, 1.08))
            sphere(f"{name}_pupil{side}", 0.034, pupil, look,
                   loc=(0, -0.052, -0.005), scale=(1, 0.4, 1.08))
            sphere(f"{name}_spec{side}", 0.014, spec, look,
                   loc=(0.022, -0.068, 0.028), segs=12, rings=8)
            sphere(f"{name}_spec2{side}", 0.007, spec, look,
                   loc=(-0.02, -0.066, -0.025), segs=8, rings=6)
            self.eyes.append((eg, look))
        # ---- brows
        self.brows = []
        bcol = mat(f"Brow_{style}", tuple(c * 0.8 for c in st["hair"]), rough=0.7)
        for side in (1, -1):
            bp = empty(f"{name}_browp{side}", (side * 0.135, -0.29, 0.52), h)
            rbox(f"{name}_brow{side}", (0.13, 0.035, 0.035), bcol, 0.48, parent=bp)
            self.brows.append(bp)
        # ---- mouths (swapped per expression)
        self.mouths = {}
        y = -0.302
        self.mouths["smile"] = tube(f"{name}_msmile", [
            (-0.07, y, 0.20), (-0.035, y - 0.005, 0.175), (0.035, y - 0.005, 0.175),
            (0.07, y, 0.20)], 0.012, mouth, h)
        self.mouths["worry"] = tube(f"{name}_mworry", [
            (-0.06, y, 0.17), (-0.03, y - 0.004, 0.188), (0.03, y - 0.004, 0.188),
            (0.06, y, 0.17)], 0.011, mouth, h)
        self.mouths["flat"] = tube(f"{name}_mflat", [
            (-0.05, y, 0.185), (0.0, y - 0.004, 0.18), (0.05, y, 0.185)],
            0.011, mouth, h)
        grin = empty(f"{name}_grin", (0, y + 0.012, 0.19), h)
        sphere(f"{name}_mopen", 0.075, mouth, grin, scale=(1.0, 0.25, 0.55),
               loc=(0, 0, -0.012))
        teeth = mat("Teeth", (0.95, 0.94, 0.9), rough=0.3)
        rbox(f"{name}_teeth", (0.11, 0.03, 0.022), teeth, 0.45, parent=grin,
             loc=(0, -0.012, 0.012))
        tongue = mat("Tongue", (0.75, 0.22, 0.2), rough=0.4)
        sphere(f"{name}_tongue", 0.035, tongue, grin, loc=(0, -0.008, -0.03),
               scale=(1.2, 0.4, 0.5))
        self.mouths["grin"] = grin
        if st["beard"]:
            for m in self.mouths.values():
                m.location.y -= 0.012
        # ---- hair / beard / cap
        hs = st["hairstyle"]
        if hs == "quiff":
            rbox(f"{name}_hairtop", (0.69, 0.63, 0.16), hair, 0.45, parent=h,
                 loc=(0, 0.01, 0.66))
            rbox(f"{name}_quiff", (0.42, 0.24, 0.16), hair, 0.48, parent=h,
                 loc=(0.06, -0.2, 0.74), rot=(0.35, 0, -0.15))
            rbox(f"{name}_quiff2", (0.3, 0.2, 0.12), hair, 0.48, parent=h,
                 loc=(-0.14, -0.18, 0.72), rot=(0.25, 0.2, 0.2))
            rbox(f"{name}_hairback", (0.69, 0.2, 0.42), hair, 0.45, parent=h,
                 loc=(0, 0.23, 0.5))
            for side in (1, -1):
                rbox(f"{name}_side{side}", (0.06, 0.36, 0.3), hair, 0.45, parent=h,
                     loc=(side * 0.325, 0.08, 0.52))
        elif hs == "short":
            rbox(f"{name}_hairtop", (0.69, 0.63, 0.12), hair, 0.45, parent=h,
                 loc=(0, 0.02, 0.64))
            rbox(f"{name}_hairback", (0.69, 0.2, 0.4), hair, 0.45, parent=h,
                 loc=(0, 0.23, 0.48))
        else:  # crop
            rbox(f"{name}_hairtop", (0.7, 0.64, 0.14), hair, 0.45, parent=h,
                 loc=(0, 0.0, 0.66))
            rbox(f"{name}_fringe", (0.6, 0.12, 0.1), hair, 0.48, parent=h,
                 loc=(0, -0.27, 0.64), rot=(0.2, 0, 0))
            rbox(f"{name}_hairback", (0.7, 0.2, 0.4), hair, 0.45, parent=h,
                 loc=(0, 0.23, 0.5))
        if st["beard"]:
            beard = mat(f"Beard_{style}", st["hair"], rough=0.8, bump=0.6,
                        bump_scale=150)
            rbox(f"{name}_beard", (0.68, 0.5, 0.2), beard, 0.45, parent=h,
                 loc=(0, 0.02, 0.12))
            for side in (1, -1):
                rbox(f"{name}_burn{side}", (0.06, 0.3, 0.26), beard, 0.45, parent=h,
                     loc=(side * 0.325, 0.02, 0.27))
            rbox(f"{name}_tache", (0.2, 0.06, 0.05), beard, 0.48, parent=h,
                 loc=(0, -0.3, 0.235))
        if st["cap"]:
            capm = mat(f"Cap_{style}", st["cap"], rough=0.7, sheen=0.3, bump=0.15,
                       bump_scale=200)
            rbox(f"{name}_cap", (0.71, 0.65, 0.24), capm, 0.45, parent=h,
                 loc=(0, 0.01, 0.7))
            rbox(f"{name}_peak", (0.5, 0.3, 0.04), capm, 0.45, parent=h,
                 loc=(0, -0.38, 0.6), rot=(-0.12, 0, 0))
        self._expr_keys = []
        self.set_expression(1, "smile")

    # ------------------------------------------------------------------
    def set_expression(self, frame, expr):
        """expr in smile / worry / flat / grin. Records a range switch."""
        self._expr_keys.append((frame, expr))

    def finalize(self, last_frame=10000):
        keys = sorted(self._expr_keys)
        for m in self.mouths:
            ranges = []
            for i, (f, e) in enumerate(keys):
                end = keys[i + 1][0] if i + 1 < len(keys) else last_frame
                if e == m:
                    ranges.append((f, end))
            objs = [self.mouths[m]] + list(self.mouths[m].children_recursive)
            for ob in objs:
                if ob.type in ("MESH", "CURVE"):
                    visible(ob, ranges)

    def brows_pose(self, frame, kind):
        # worried: inner ends up; happy: raised; angry/focus: inner down
        pose = {"neutral": (0.0, 0.0), "worry": (0.32, 0.02), "happy": (-0.08, 0.035),
                "focus": (-0.2, -0.01), "surprise": (0.0, 0.05)}[kind]
        for side, bp in zip((1, -1), self.brows):
            kf(bp, "rotation_euler", frame, (0, side * pose[0], 0))
            kf(bp, "location", frame, (side * 0.135, -0.29, 0.52 + pose[1]))

    def blink(self, frame):
        for eg, _ in self.eyes:
            for f, s in ((frame - 2, 1.0), (frame, 0.08), (frame + 3, 1.0)):
                kf(eg, "scale", f, (1, 1, s))

    def blinks(self, start, end, every=75, seed=0):
        import random
        rnd = random.Random(seed)
        f = start + rnd.randint(10, 30)
        while f < end - 4:
            self.blink(f)
            f += every + rnd.randint(-25, 25)

    def look(self, frame, dx=0.0, dz=0.0):
        for _, lk in self.eyes:
            kf(lk, "location", frame, (dx, 0, dz))

    def pose_arm(self, side, frame, sh=(0, 0, 0), el=(0, 0, 0), hand=(0, 0, 0)):
        a = self.arms[side]
        kf(a["sh"], "rotation_euler", frame, sh)
        kf(a["el"], "rotation_euler", frame, el)
        kf(a["hand"], "rotation_euler", frame, hand)

    def reach(self, side, frame, target, pole=(0, 0.6, -1.0), hand=(0, 0, 0)):
        """2-bone IK: put the hand at target (torso space), elbow toward pole."""
        a = self.arms[side]
        S = Vector(a["sh"].location)
        T = Vector(target) - S
        d = min(T.length, (L1 + L2) * 0.999)
        T = T.normalized() * d
        # elbow position via law of cosines in plane (T, pole)
        cos_a = (L1 * L1 + d * d - L2 * L2) / (2 * L1 * d)
        ang = math.acos(max(-1, min(1, cos_a)))
        tdir = T.normalized()
        pv = Vector(pole) - tdir * Vector(pole).dot(tdir)
        if pv.length < 1e-4:
            pv = Vector((0, 0, -1))
        pv.normalize()
        u = (tdir * math.cos(ang) + pv * math.sin(ang)).normalized()
        E = u * L1
        f = (T - E).normalized()
        down = Vector((0, 0, -1))
        q1 = down.rotation_difference(u)
        q2 = down.rotation_difference(q1.inverted() @ f)
        for ob, q in ((a["sh"], q1), (a["el"], q2)):
            ob.rotation_mode = "QUATERNION"
            ob.rotation_quaternion = q
            ob.keyframe_insert("rotation_quaternion", frame=frame)
        h = a["hand"]
        h.rotation_euler = hand
        h.keyframe_insert("rotation_euler", frame=frame)

    def arm_rest(self, side, frame):
        s = 1 if side == "L" else -1
        self.reach(side, frame, (s * 0.4, -0.04, -0.06), pole=(s * 0.3, 0.5, 0))

    def arms_rest(self, frame):
        self.arm_rest("L", frame)
        self.arm_rest("R", frame)

    def chin_hold(self, frame, side="R"):
        s = 1 if side == "L" else -1
        self.reach(side, frame, (s * 0.06, -0.36, 0.6), pole=(s * 0.6, -0.2, -1))

    def hip_hand(self, frame, side="L"):
        s = 1 if side == "L" else -1
        self.reach(side, frame, (s * 0.33, -0.02, 0.12), pole=(s * 1, 0.3, 0))

    def thumbs_up(self, frame, side="R"):
        s = 1 if side == "L" else -1
        self.reach(side, frame, (s * 0.3, -0.42, 0.42), pole=(s * 0.5, 0.2, -1),
                   hand=(0, 0, 0))

    def scratch_head(self, frame, side="R"):
        s = 1 if side == "L" else -1
        self.reach(side, frame, (s * 0.3, -0.05, 1.0), pole=(s * 1, 0.2, 0))

    def wave(self, start, cycles=3, side="L", period=10):
        s = 1 if side == "L" else -1
        f = start
        for i in range(cycles):
            self.reach(side, f, (s * 0.55, -0.12, 0.85), pole=(s * 1, 0.3, -0.5))
            self.reach(side, f + period // 2, (s * 0.38, -0.16, 0.92),
                       pole=(s * 1, 0.3, -0.5))
            f += period
        self.reach(side, f, (s * 0.55, -0.12, 0.85), pole=(s * 1, 0.3, -0.5))
        return f

    def present(self, frame, side="L"):
        s = 1 if side == "L" else -1
        self.reach(side, frame, (s * 0.62, -0.3, 0.3), pole=(s * 0.4, 0.4, -1))

    def breathe(self, start, end, period=60, amp=0.012, seed=0):
        f = start
        i = 0
        while f <= end + period:
            z = 0.0 + (amp if i % 2 else 0.0)
            kf(self.torso, "scale", f, (1 + z * 0.5, 1, 1 + z))
            f += period // 2
            i += 1

    def head_pose(self, frame, tilt=0.0, turn=0.0, nod=0.0):
        kf(self.head, "rotation_euler", frame, (nod, tilt, turn))

    def body_turn(self, frame, rz):
        kf(self.root, "rotation_euler", frame, (0, 0, rz))
