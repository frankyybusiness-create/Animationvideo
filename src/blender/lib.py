"""Procedural 3D building blocks for the Fenland Drives & Patios ad.

Everything is generated in code with bpy (Blender as a Python module):
rounded-box "toy" primitives, stylised materials, the cartoon character rig,
the British house set, and block-paving geometry. Shots in shots.py combine
these pieces and keyframe them.
"""
import math
import random

import bmesh
import bpy
from mathutils import Euler, Vector

FPS = 30


# --------------------------------------------------------------------------
# Scene / render setup
# --------------------------------------------------------------------------
def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scn = bpy.context.scene
    scn.render.fps = FPS
    return scn


def setup_render(scn, res=(720, 1280), samples=24, motion_blur=True):
    scn.render.engine = "CYCLES"
    cy = scn.cycles
    cy.device = "CPU"
    cy.samples = samples
    cy.use_adaptive_sampling = True
    cy.adaptive_threshold = 0.05
    cy.use_denoising = True
    cy.denoiser = "OPENIMAGEDENOISE"
    cy.max_bounces = 4
    cy.diffuse_bounces = 2
    cy.glossy_bounces = 2
    cy.transmission_bounces = 2
    cy.transparent_max_bounces = 4
    cy.caustics_reflective = False
    cy.caustics_refractive = False
    cy.blur_glossy = 1.0
    cy.sample_clamp_indirect = 4.0
    scn.render.resolution_x, scn.render.resolution_y = res
    scn.render.resolution_percentage = 100
    scn.render.use_motion_blur = motion_blur
    scn.render.motion_blur_shutter = 0.5
    scn.render.image_settings.file_format = "PNG"
    scn.render.image_settings.color_mode = "RGB"
    scn.render.film_transparent = False
    scn.view_settings.view_transform = "AgX"
    scn.view_settings.look = "AgX - Medium High Contrast"
    scn.render.threads_mode = "AUTO"


def world(scn, top=(0.02, 0.03, 0.07), bottom=(0.01, 0.012, 0.02), strength=1.0):
    w = bpy.data.worlds.new("World")
    scn.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    grad = nt.nodes.new("ShaderNodeTexGradient")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    # vertical gradient on the view direction
    mp.inputs["Rotation"].default_value = (0, -math.pi / 2, 0)
    nt.links.new(tc.outputs["Generated"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], grad.inputs["Vector"])
    nt.links.new(grad.outputs["Fac"], ramp.inputs["Fac"])
    ramp.color_ramp.elements[0].color = (*bottom, 1)
    ramp.color_ramp.elements[1].color = (*top, 1)
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = strength
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    return w


# --------------------------------------------------------------------------
# Materials
# --------------------------------------------------------------------------
_MATS = {}


def _principled(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    p = nt.nodes.get("Principled BSDF")
    return m, nt, p


def mat(name, color, rough=0.5, metal=0.0, sss=0.0, coat=0.0, sheen=0.0,
        emit=None, emit_strength=0.0, bump=0.0, bump_scale=40.0, alpha=1.0):
    key = name
    if key in _MATS:
        return _MATS[key]
    m, nt, p = _principled(name)
    p.inputs["Base Color"].default_value = (*color, 1)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    if sss:
        p.inputs["Subsurface Weight"].default_value = sss
        p.inputs["Subsurface Radius"].default_value = (0.9, 0.35, 0.2)
        p.inputs["Subsurface Scale"].default_value = 0.05
    if coat:
        p.inputs["Coat Weight"].default_value = coat
        p.inputs["Coat Roughness"].default_value = 0.15
    if sheen:
        p.inputs["Sheen Weight"].default_value = sheen
    if emit is not None:
        p.inputs["Emission Color"].default_value = (*emit, 1)
        p.inputs["Emission Strength"].default_value = emit_strength
    if alpha < 1.0:
        p.inputs["Alpha"].default_value = alpha
    if bump:
        tex = nt.nodes.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = bump_scale
        tex.inputs["Detail"].default_value = 6
        bn = nt.nodes.new("ShaderNodeBump")
        bn.inputs["Strength"].default_value = bump
        nt.links.new(tex.outputs["Fac"], bn.inputs["Height"])
        nt.links.new(bn.outputs["Normal"], p.inputs["Normal"])
    _MATS[key] = m
    return m


def knit_mat(name, color, scale=60.0):
    """Chunky knitted jumper look: wave + noise bump, sheen."""
    if name in _MATS:
        return _MATS[name]
    m, nt, p = _principled(name)
    p.inputs["Base Color"].default_value = (*color, 1)
    p.inputs["Roughness"].default_value = 0.85
    p.inputs["Sheen Weight"].default_value = 0.6
    tc = nt.nodes.new("ShaderNodeTexCoord")
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.wave_type = "BANDS"
    wave.bands_direction = "X"
    wave.inputs["Scale"].default_value = scale
    wave.inputs["Distortion"].default_value = 2.0
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = scale * 2
    mix = nt.nodes.new("ShaderNodeMath")
    mix.operation = "MULTIPLY"
    bn = nt.nodes.new("ShaderNodeBump")
    bn.inputs["Strength"].default_value = 0.45
    nt.links.new(tc.outputs["Object"], wave.inputs["Vector"])
    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
    nt.links.new(wave.outputs["Fac"], mix.inputs[0])
    nt.links.new(noise.outputs["Fac"], mix.inputs[1])
    nt.links.new(mix.outputs["Value"], bn.inputs["Height"])
    nt.links.new(bn.outputs["Normal"], p.inputs["Normal"])
    _MATS[name] = m
    return m


def brick_mat(name="Brick", c1=(0.36, 0.13, 0.07), c2=(0.48, 0.2, 0.1),
              mortar=(0.32, 0.3, 0.27), scale=2.3, rough=0.85):
    if name in _MATS:
        return _MATS[name]
    m, nt, p = _principled(name)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    br = nt.nodes.new("ShaderNodeTexBrick")
    br.inputs["Color1"].default_value = (*c1, 1)
    br.inputs["Color2"].default_value = (*c2, 1)
    br.inputs["Mortar"].default_value = (*mortar, 1)
    br.inputs["Scale"].default_value = scale
    br.inputs["Mortar Size"].default_value = 0.012
    br.inputs["Brick Width"].default_value = 0.5
    br.inputs["Row Height"].default_value = 0.16
    br.inputs["Bias"].default_value = 0.1
    # walls are vertical: map (x + y, z) so front and side faces both tile
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    add = nt.nodes.new("ShaderNodeMath")
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    nt.links.new(sep.outputs["X"], add.inputs[0])
    nt.links.new(sep.outputs["Y"], add.inputs[1])
    nt.links.new(add.outputs["Value"], comb.inputs["X"])
    nt.links.new(sep.outputs["Z"], comb.inputs["Y"])
    nt.links.new(comb.outputs["Vector"], br.inputs["Vector"])
    # per-brick tone variation
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 3.0
    mixc = nt.nodes.new("ShaderNodeMix")
    mixc.data_type = "RGBA"
    mixc.blend_type = "MULTIPLY"
    mixc.inputs["Factor"].default_value = 0.35
    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
    nt.links.new(br.outputs["Color"], mixc.inputs[6])
    nt.links.new(noise.outputs["Color"], mixc.inputs[7])
    nt.links.new(mixc.outputs[2], p.inputs["Base Color"])
    bn = nt.nodes.new("ShaderNodeBump")
    bn.inputs["Strength"].default_value = 0.35
    bn.invert = True
    nt.links.new(br.outputs["Fac"], bn.inputs["Height"])
    nt.links.new(bn.outputs["Normal"], p.inputs["Normal"])
    p.inputs["Roughness"].default_value = rough
    _MATS[name] = m
    return m


def vcol_mat(name, attr="Col", rough=0.55, coat=0.15, bump=0.15):
    """Material that reads per-face colour attribute (used for paving)."""
    if name in _MATS:
        return _MATS[name]
    m, nt, p = _principled(name)
    at = nt.nodes.new("ShaderNodeAttribute")
    at.attribute_name = attr
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 90
    mul = nt.nodes.new("ShaderNodeMix")
    mul.data_type = "RGBA"
    mul.blend_type = "MULTIPLY"
    mul.inputs["Factor"].default_value = 0.25
    nt.links.new(at.outputs["Color"], mul.inputs[6])
    nt.links.new(noise.outputs["Color"], mul.inputs[7])
    nt.links.new(mul.outputs[2], p.inputs["Base Color"])
    p.inputs["Roughness"].default_value = rough
    p.inputs["Coat Weight"].default_value = coat
    if bump:
        bn = nt.nodes.new("ShaderNodeBump")
        bn.inputs["Strength"].default_value = bump
        nt.links.new(noise.outputs["Fac"], bn.inputs["Height"])
        nt.links.new(bn.outputs["Normal"], p.inputs["Normal"])
    _MATS[name] = m
    return m


def cracked_concrete_mat(name="OldConcrete"):
    if name in _MATS:
        return _MATS[name]
    m, nt, p = _principled(name)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    vor.feature = "DISTANCE_TO_EDGE"
    vor.inputs["Scale"].default_value = 1.6
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 3.0
    noise.inputs["Detail"].default_value = 8
    # distort voronoi with noise for organic cracks
    mixv = nt.nodes.new("ShaderNodeMix")
    mixv.data_type = "VECTOR"
    mixv.inputs["Factor"].default_value = 0.08
    nt.links.new(tc.outputs["Object"], mixv.inputs[4])
    nt.links.new(noise.outputs["Color"], mixv.inputs[5])
    nt.links.new(mixv.outputs[1], vor.inputs["Vector"])
    crack = nt.nodes.new("ShaderNodeMapRange")
    crack.inputs["From Min"].default_value = 0.0
    crack.inputs["From Max"].default_value = 0.025
    nt.links.new(vor.outputs["Distance"], crack.inputs["Value"])
    # stains
    stain = nt.nodes.new("ShaderNodeTexNoise")
    stain.inputs["Scale"].default_value = 1.2
    sramp = nt.nodes.new("ShaderNodeValToRGB")
    sramp.color_ramp.elements[0].color = (0.10, 0.10, 0.09, 1)
    sramp.color_ramp.elements[1].color = (0.30, 0.29, 0.27, 1)
    nt.links.new(stain.outputs["Fac"], sramp.inputs["Fac"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    nt.links.new(crack.outputs["Result"], mix.inputs["Factor"])
    mix.inputs[6].default_value = (0.02, 0.02, 0.02, 1)
    nt.links.new(sramp.outputs["Color"], mix.inputs[7])
    nt.links.new(mix.outputs[2], p.inputs["Base Color"])
    # puddle roughness: wet low areas glossy
    pud = nt.nodes.new("ShaderNodeTexNoise")
    pud.inputs["Scale"].default_value = 0.8
    pr = nt.nodes.new("ShaderNodeMapRange")
    pr.inputs["From Min"].default_value = 0.52
    pr.inputs["From Max"].default_value = 0.56
    pr.inputs["To Min"].default_value = 0.8
    pr.inputs["To Max"].default_value = 0.05
    nt.links.new(pud.outputs["Fac"], pr.inputs["Value"])
    nt.links.new(pr.outputs["Result"], p.inputs["Roughness"])
    bn = nt.nodes.new("ShaderNodeBump")
    bn.inputs["Strength"].default_value = 0.6
    nt.links.new(crack.outputs["Result"], bn.inputs["Height"])
    nt.links.new(bn.outputs["Normal"], p.inputs["Normal"])
    _MATS[name] = m
    return m


def lawn_mat(name="Lawn"):
    if name in _MATS:
        return _MATS[name]
    m, nt, p = _principled(name)
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 30
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.03, 0.09, 0.02, 1)
    ramp.color_ramp.elements[1].color = (0.09, 0.2, 0.04, 1)
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], p.inputs["Base Color"])
    p.inputs["Roughness"].default_value = 0.9
    p.inputs["Sheen Weight"].default_value = 0.5
    bn = nt.nodes.new("ShaderNodeBump")
    bn.inputs["Strength"].default_value = 0.8
    hn = nt.nodes.new("ShaderNodeTexNoise")
    hn.inputs["Scale"].default_value = 300
    nt.links.new(hn.outputs["Fac"], bn.inputs["Height"])
    nt.links.new(bn.outputs["Normal"], p.inputs["Normal"])
    _MATS[name] = m
    return m


def glow(name, color, strength):
    return mat(name, color, emit=color, emit_strength=strength, rough=0.4)


# --------------------------------------------------------------------------
# Geometry primitives
# --------------------------------------------------------------------------
TARGET = {"coll": None}


def build_into(coll):
    """Route newly created objects into coll (None = scene collection)."""
    TARGET["coll"] = coll


def _link(obj, parent=None, coll=None):
    (coll or TARGET["coll"] or bpy.context.scene.collection).objects.link(obj)
    if parent is not None:
        obj.parent = parent
    return obj


def empty(name, loc=(0, 0, 0), parent=None, rot=(0, 0, 0)):
    e = bpy.data.objects.new(name, None)
    e.empty_display_size = 0.1
    e.location = loc
    e.rotation_euler = rot
    return _link(e, parent)


def _mesh_obj(name, bm, material, parent, loc, rot, smooth=True):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if smooth:
        me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    if material is not None:
        me.materials.append(material)
    ob = bpy.data.objects.new(name, me)
    ob.location = loc
    ob.rotation_euler = rot
    return _link(ob, parent)


def rbox(name, size, material=None, bevel=0.3, segs=5, parent=None,
         loc=(0, 0, 0), rot=(0, 0, 0), origin=(0, 0, 0)):
    """Rounded box. bevel is a fraction (0..0.5) of the smallest dimension.
    origin shifts the pivot, in units of half-size (e.g. (0,0,1) = top)."""
    sx, sy, sz = size
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x = v.co.x * sx - origin[0] * sx / 2
        v.co.y = v.co.y * sy - origin[1] * sy / 2
        v.co.z = v.co.z * sz - origin[2] * sz / 2
    ob = _mesh_obj(name, bm, material, parent, loc, rot)
    if bevel > 0:
        mod = ob.modifiers.new("bevel", "BEVEL")
        mod.width = min(size) * bevel
        mod.segments = segs
        mod.limit_method = "NONE"
        mod.harden_normals = False
    return ob


def sphere(name, radius, material=None, parent=None, loc=(0, 0, 0),
           scale=(1, 1, 1), rot=(0, 0, 0), segs=32, rings=16):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings, radius=radius)
    for v in bm.verts:
        v.co.x *= scale[0]
        v.co.y *= scale[1]
        v.co.z *= scale[2]
    return _mesh_obj(name, bm, material, parent, loc, rot)


def cylinder(name, radius, depth, material=None, parent=None, loc=(0, 0, 0),
             rot=(0, 0, 0), segs=32, r2=None, bevel=0.0):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=segs, radius1=radius,
                          radius2=radius if r2 is None else r2, depth=depth)
    ob = _mesh_obj(name, bm, material, parent, loc, rot)
    if bevel:
        mod = ob.modifiers.new("bevel", "BEVEL")
        mod.width = bevel
        mod.segments = 3
        mod.angle_limit = math.radians(40)
    return ob


def tube(name, pts, radius, material=None, parent=None, loc=(0, 0, 0)):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = radius
    cu.bevel_resolution = 4
    cu.use_fill_caps = True
    sp = cu.splines.new("NURBS")
    sp.points.add(len(pts) - 1)
    for i, p in enumerate(pts):
        sp.points[i].co = (*p, 1)
    sp.use_endpoint_u = True
    sp.order_u = min(4, len(pts))
    sp.resolution_u = 12
    ob = bpy.data.objects.new(name, cu)
    if material:
        cu.materials.append(material)
    ob.location = loc
    return _link(ob, parent)


def plane(name, size, material=None, loc=(0, 0, 0), rot=(0, 0, 0), parent=None):
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5)
    for v in bm.verts:
        v.co.x *= size[0]
        v.co.y *= size[1]
    return _mesh_obj(name, bm, material, parent, loc, rot, smooth=False)


# --------------------------------------------------------------------------
# Keyframe helpers
# --------------------------------------------------------------------------
def kf(obj, path, frame, value, interp="BEZIER", index=-1):
    setattr_path(obj, path, value)
    obj.keyframe_insert(data_path=path, frame=frame, index=index)
    _set_interp(obj, path, frame, interp)


def setattr_path(obj, path, value):
    if path in ("location", "rotation_euler", "scale"):
        setattr(obj, path, value)
    else:
        setattr(obj, path, value)


def _set_interp(obj, path, frame, interp):
    ad = obj.animation_data
    if not ad or not ad.action:
        return
    for fc in _fcurves(ad.action):
        if fc.data_path == path:
            for k in fc.keyframe_points:
                if abs(k.co[0] - frame) < 0.01:
                    k.interpolation = interp
                    if interp == "BEZIER":
                        k.easing = "AUTO"


def _fcurves(action):
    # Blender 4.4+ layered actions
    if hasattr(action, "fcurves") and len(getattr(action, "fcurves", [])):
        return list(action.fcurves)
    out = []
    for layer in getattr(action, "layers", []):
        for strip in layer.strips:
            for cb in strip.channelbags:
                out.extend(cb.fcurves)
    return out


def visible(obj, frames_on):
    """frames_on: list of (start, end) ranges where object renders."""
    obj.hide_render = True
    obj.keyframe_insert("hide_render", frame=-100)
    for a, b in frames_on:
        obj.hide_render = False
        obj.keyframe_insert("hide_render", frame=a)
        obj.hide_render = True
        obj.keyframe_insert("hide_render", frame=b)
    for fc in _fcurves(obj.animation_data.action):
        if fc.data_path == "hide_render":
            for k in fc.keyframe_points:
                k.interpolation = "CONSTANT"


def apply_children_visibility(root, frames_on):
    for ob in [root] + list(root.children_recursive):
        if ob.type in ("MESH", "CURVE"):
            visible(ob, frames_on)


def sec(t):
    return int(round(t * FPS)) + 1
