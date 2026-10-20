"""Procedural 3D cartoon building blocks for the Sureshield advert (Blender / bpy).

Visual language (matched to the Oct-20Footage1 reference):
  * chunky toy/clay characters: rounded-cube heads ~40% of body height,
    big glossy eyes, simple capsule limbs, soft subsurface skin
  * knit / tweed / fabric materials with visible bump texture
  * night-time British street, rain, warm practical lights vs. cool navy fill
  * shallow depth of field with warm bokeh in the background
"""
import math
import random

import bmesh
import bpy
from mathutils import Vector

# ----------------------------------------------------------------------------
# scene setup
# ----------------------------------------------------------------------------

def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scn = bpy.context.scene
    scn.render.engine = "CYCLES"
    scn.cycles.device = "CPU"
    scn.cycles.use_adaptive_sampling = True
    scn.cycles.adaptive_threshold = 0.03
    scn.cycles.use_denoising = True
    try:
        scn.cycles.denoiser = "OPENIMAGEDENOISE"
    except TypeError:
        pass
    scn.cycles.max_bounces = 5
    scn.cycles.diffuse_bounces = 2
    scn.cycles.glossy_bounces = 2
    scn.cycles.transmission_bounces = 4
    scn.cycles.transparent_max_bounces = 6
    scn.cycles.caustics_reflective = False
    scn.cycles.caustics_refractive = False
    scn.cycles.blur_glossy = 1.0
    scn.render.use_persistent_data = True
    scn.render.fps = 30
    scn.render.image_settings.file_format = "PNG"
    scn.render.image_settings.color_mode = "RGB"
    scn.render.film_transparent = False
    try:
        scn.view_settings.view_transform = "AgX"
        scn.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        pass
    world = bpy.data.worlds.new("World")
    scn.world = world
    world.use_nodes = True
    nt = world.node_tree
    bg = nt.nodes["Background"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = hexc("#1a2848")
    ramp.color_ramp.elements[1].position = 0.45
    ramp.color_ramp.elements[1].color = hexc("#03060f")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 1.0
    return scn


def set_world(strength=1.0):
    bpy.context.scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = strength


# ----------------------------------------------------------------------------
# materials
# ----------------------------------------------------------------------------

_MATS = {}


def hexc(h, a=1.0):
    h = h.lstrip("#")
    srgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in srgb]
    return (*lin, a)


def _principled(mat):
    nt = mat.node_tree
    return nt.nodes.get("Principled BSDF")


def mat_basic(name, color, rough=0.5, sss=0.0, coat=0.0, metal=0.0, emit=None, emit_strength=0.0, spec=0.5):
    if name in _MATS:
        return _MATS[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = _principled(m)
    p.inputs["Base Color"].default_value = hexc(color) if isinstance(color, str) else color
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    p.inputs["Specular IOR Level"].default_value = spec
    if sss:
        p.inputs["Subsurface Weight"].default_value = sss
        p.inputs["Subsurface Radius"].default_value = (0.9, 0.45, 0.3)
        p.inputs["Subsurface Scale"].default_value = 0.08
    if coat:
        p.inputs["Coat Weight"].default_value = coat
        p.inputs["Coat Roughness"].default_value = 0.08
    if emit:
        p.inputs["Emission Color"].default_value = hexc(emit) if isinstance(emit, str) else emit
        p.inputs["Emission Strength"].default_value = emit_strength
    _MATS[name] = m
    return m


def mat_emission(name, color, strength):
    if name in _MATS:
        return _MATS[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = hexc(color) if isinstance(color, str) else color
    em.inputs["Strength"].default_value = strength
    nt.links.new(em.outputs[0], out.inputs[0])
    _MATS[name] = m
    return m


def _bumped(m, tex_node, strength=0.4, dist=0.02, color_ramp=None):
    nt = m.node_tree
    p = _principled(m)
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = strength
    bump.inputs["Distance"].default_value = dist
    nt.links.new(tex_node.outputs["Fac"] if "Fac" in tex_node.outputs else tex_node.outputs[0], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], p.inputs["Normal"])
    return bump


def mat_knit(name, color, scale=38.0, rough=0.85):
    """Chunky rib-knit look (beanie / cardigan) using a wave texture bump."""
    if name in _MATS:
        return _MATS[name]
    m = mat_basic(name, color, rough=rough)
    m.node_tree.nodes["Principled BSDF"].inputs["Sheen Weight"].default_value = 0.6
    nt = m.node_tree
    tc = nt.nodes.new("ShaderNodeTexCoord")
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.wave_type = "BANDS"
    wave.bands_direction = "X"
    wave.inputs["Scale"].default_value = scale
    wave.inputs["Distortion"].default_value = 2.0
    wave.inputs["Detail"].default_value = 1.5
    nt.links.new(tc.outputs["Object"], wave.inputs["Vector"])
    _bumped(m, wave, strength=0.8, dist=0.04)
    return m


def mat_tweed(name, color, scale=90.0):
    if name in _MATS:
        return _MATS[name]
    m = mat_basic(name, color, rough=0.9)
    nt = m.node_tree
    p = _principled(m)
    p.inputs["Sheen Weight"].default_value = 0.5
    tc = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = scale
    noise.inputs["Detail"].default_value = 8
    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs["A"].default_value = hexc(color)
    base = hexc(color)
    mix.inputs["B"].default_value = (base[0] * 1.8, base[1] * 1.7, base[2] * 1.5, 1)
    nt.links.new(noise.outputs["Fac"], mix.inputs["Factor"])
    nt.links.new(mix.outputs["Result"], p.inputs["Base Color"])
    _bumped(m, noise, strength=0.35, dist=0.01)
    return m


def mat_fabric(name, color, rough=0.8, scale=140.0):
    if name in _MATS:
        return _MATS[name]
    m = mat_basic(name, color, rough=rough)
    nt = m.node_tree
    _principled(m).inputs["Sheen Weight"].default_value = 0.4
    tc = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = scale
    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
    _bumped(m, noise, strength=0.15, dist=0.01)
    return m


def mat_brick(name, brick="#8a3b26", mortar="#b9ab98", scale=6.0, rough=0.85):
    if name in _MATS:
        return _MATS[name]
    m = mat_basic(name, brick, rough=rough)
    nt = m.node_tree
    p = _principled(m)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (scale, scale, scale)
    br = nt.nodes.new("ShaderNodeTexBrick")
    b = hexc(brick)
    br.inputs["Color1"].default_value = b
    br.inputs["Color2"].default_value = (b[0] * 0.7, b[1] * 0.72, b[2] * 0.75, 1)
    br.inputs["Mortar"].default_value = hexc(mortar)
    br.inputs["Scale"].default_value = 1.0
    br.inputs["Mortar Size"].default_value = 0.025
    br.inputs["Brick Width"].default_value = 0.5
    br.inputs["Row Height"].default_value = 0.17
    br.offset = 0.5
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    add = nt.nodes.new("ShaderNodeMath")
    add.operation = "ADD"
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    nt.links.new(sep.outputs["X"], add.inputs[0])
    nt.links.new(sep.outputs["Y"], add.inputs[1])
    nt.links.new(add.outputs[0], comb.inputs["X"])
    nt.links.new(sep.outputs["Z"], comb.inputs["Y"])
    nt.links.new(comb.outputs[0], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], br.inputs["Vector"])
    nt.links.new(br.outputs["Color"], p.inputs["Base Color"])
    _bumped(m, br, strength=0.5, dist=0.03).invert = True
    return m


def mat_wet_ground(name, color="#15171c", rough=0.18):
    """Wet tarmac: dark, glossy, with roughness variation for puddles."""
    if name in _MATS:
        return _MATS[name]
    m = mat_basic(name, color, rough=rough)
    nt = m.node_tree
    p = _principled(m)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 0.25
    noise.inputs["Detail"].default_value = 2
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.45
    ramp.color_ramp.elements[0].color = (0.06, 0.06, 0.06, 1)
    ramp.color_ramp.elements[1].position = 0.75
    ramp.color_ramp.elements[1].color = (0.3, 0.3, 0.3, 1)
    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], p.inputs["Roughness"])
    return m


def mat_tile(name, color="#b8532f", rough=0.32, wet=True):
    """Glossy clay roof tile with subtle colour variation per object."""
    if name in _MATS:
        return _MATS[name]
    m = mat_basic(name, color, rough=rough, coat=0.6 if wet else 0.0)
    nt = m.node_tree
    p = _principled(m)
    info = nt.nodes.new("ShaderNodeObjectInfo")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    c = hexc(color)
    ramp.color_ramp.elements[0].color = (c[0] * 0.8, c[1] * 0.75, c[2] * 0.75, 1)
    ramp.color_ramp.elements[1].color = (min(1, c[0] * 1.15), c[1] * 1.1, c[2] * 1.05, 1)
    nt.links.new(info.outputs["Random"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], p.inputs["Base Color"])
    if wet:
        tc = nt.nodes.new("ShaderNodeTexCoord")
        vor = nt.nodes.new("ShaderNodeTexVoronoi")
        vor.inputs["Scale"].default_value = 28
        vor.feature = "F1"
        nt.links.new(tc.outputs["Object"], vor.inputs["Vector"])
        r2 = nt.nodes.new("ShaderNodeValToRGB")
        r2.color_ramp.elements[0].position = 0.0
        r2.color_ramp.elements[0].color = (1, 1, 1, 1)
        r2.color_ramp.elements[1].position = 0.12
        r2.color_ramp.elements[1].color = (0, 0, 0, 1)
        nt.links.new(vor.outputs["Distance"], r2.inputs["Fac"])
        bump = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.35
        bump.inputs["Distance"].default_value = 0.01
        nt.links.new(r2.outputs["Color"], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], p.inputs["Coat Normal"])
    return m


# ----------------------------------------------------------------------------
# geometry helpers (meshes are cached so duplicates share data -> instancing)
# ----------------------------------------------------------------------------

_MESHES = {}


def rbox_mesh(sx, sy, sz, r, seg=4, key=None):
    key = key or f"rbox_{sx:.3f}_{sy:.3f}_{sz:.3f}_{r:.3f}_{seg}"
    if key in _MESHES:
        return _MESHES[key]
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= sx
        v.co.y *= sy
        v.co.z *= sz
    r = min(r, min(sx, sy, sz) * 0.499)
    bmesh.ops.bevel(bm, geom=list(bm.edges), offset=r, segments=seg, profile=0.5,
                    affect="EDGES", clamp_overlap=True)
    me = bpy.data.meshes.new(key)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    _MESHES[key] = me
    return me


def sphere_mesh(r=0.5, seg=32, key=None):
    key = key or f"sph_{r:.3f}_{seg}"
    if key in _MESHES:
        return _MESHES[key]
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=r)
    me = bpy.data.meshes.new(key)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    _MESHES[key] = me
    return me


def cyl_mesh(r, h, seg=32, r2=None, key=None):
    r2 = r if r2 is None else r2
    key = key or f"cyl_{r:.3f}_{r2:.3f}_{h:.3f}_{seg}"
    if key in _MESHES:
        return _MESHES[key]
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r2, depth=h)
    me = bpy.data.meshes.new(key)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = len(p.vertices) == 4
    _MESHES[key] = me
    return me


def prism_mesh(w, d, h):
    key = f"prism_{w:.3f}_{d:.3f}_{h:.3f}"
    if key in _MESHES:
        return _MESHES[key]
    bm = bmesh.new()
    vs = [bm.verts.new(v) for v in ((-w / 2, -d / 2, 0), (-w / 2, d / 2, 0), (-w / 2, 0, h),
                                     (w / 2, -d / 2, 0), (w / 2, d / 2, 0), (w / 2, 0, h))]
    for f in ((0, 2, 1), (3, 4, 5), (0, 1, 4, 3), (0, 3, 5, 2), (1, 2, 5, 4)):
        bm.faces.new([vs[i] for i in f])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(key)
    bm.to_mesh(me)
    bm.free()
    _MESHES[key] = me
    return me


def obj(name, mesh, mat=None, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1), parent=None, coll=None):
    o = bpy.data.objects.new(name, mesh)
    (coll or bpy.context.scene.collection).objects.link(o)
    o.location = loc
    o.rotation_euler = rot
    o.scale = scale
    if mat is not None:
        if not mesh.materials:
            mesh.materials.append(mat)
        else:
            o.material_slots[0].link = "OBJECT"
            o.material_slots[0].material = mat
    if parent is not None:
        o.parent = parent
    return o


def rbox(name, size, r, mat, loc=(0, 0, 0), rot=(0, 0, 0), parent=None, seg=4):
    return obj(name, rbox_mesh(*size, r, seg), mat, loc, rot, parent=parent)


def sphere(name, r, mat, loc=(0, 0, 0), scale=(1, 1, 1), parent=None, seg=32):
    return obj(name, sphere_mesh(r, seg), mat, loc, scale=scale, parent=parent)


def cyl(name, r, h, mat, loc=(0, 0, 0), rot=(0, 0, 0), parent=None, r2=None, seg=32):
    return obj(name, cyl_mesh(r, h, seg, r2), mat, loc, rot, parent=parent)


def empty(name, loc=(0, 0, 0), rot=(0, 0, 0), parent=None):
    e = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(e)
    e.location = loc
    e.rotation_euler = rot
    if parent is not None:
        e.parent = parent
    return e


def curve_obj(name, pts, bevel, mat, parent=None, loc=(0, 0, 0)):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = bevel
    cu.bevel_resolution = 4
    cu.use_fill_caps = True
    sp = cu.splines.new("BEZIER")
    sp.bezier_points.add(len(pts) - 1)
    for bp, p in zip(sp.bezier_points, pts):
        bp.co = p
        bp.handle_left_type = "AUTO"
        bp.handle_right_type = "AUTO"
    o = bpy.data.objects.new(name, cu)
    bpy.context.scene.collection.objects.link(o)
    cu.materials.append(mat)
    o.location = loc
    if parent is not None:
        o.parent = parent
    return o


# ----------------------------------------------------------------------------
# keyframing
# ----------------------------------------------------------------------------

def key(o, path, frame, value, index=-1):
    if path == "location":
        o.location = value
    elif path == "rotation_euler":
        o.rotation_euler = value
    elif path == "scale":
        o.scale = value
    else:
        setattr(o, path, value)
    o.keyframe_insert(path, frame=frame, index=index)


def keys(o, path, frames_values):
    for f, v in frames_values:
        key(o, path, f, v)


def rad(*a):
    return tuple(math.radians(x) for x in a)


# ----------------------------------------------------------------------------
# lighting / camera
# ----------------------------------------------------------------------------

def area_light(name, loc, target, energy, color="#ffb070", size=2.0, shape="DISK", glossy=None):
    ld = bpy.data.lights.new(name, "AREA")
    ld.energy = energy
    ld.color = hexc(color)[:3]
    ld.shape = shape
    ld.size = size
    o = bpy.data.objects.new(name, ld)
    bpy.context.scene.collection.objects.link(o)
    o.location = loc
    o.visible_camera = False
    # key lights keep their specular highlight (toy/clay sheen); others don't
    # reflect in the wet ground as big blobs
    o.visible_glossy = name.startswith("key") if glossy is None else glossy
    look_at(o, target)
    return o


def point_light(name, loc, energy, color="#ffa860", radius=0.2):
    ld = bpy.data.lights.new(name, "POINT")
    ld.energy = energy
    ld.color = hexc(color)[:3]
    ld.shadow_soft_size = radius
    o = bpy.data.objects.new(name, ld)
    bpy.context.scene.collection.objects.link(o)
    o.location = loc
    return o


def look_at(o, target):
    d = Vector(target) - Vector(o.location)
    o.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def camera(name="Cam", lens=50, fstop=2.8, focus=None, sensor=36):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.sensor_width = sensor
    cd.sensor_fit = "HORIZONTAL"
    cd.dof.use_dof = True
    cd.dof.aperture_fstop = fstop
    cd.dof.aperture_blades = 0
    c = bpy.data.objects.new(name, cd)
    bpy.context.scene.collection.objects.link(c)
    bpy.context.scene.camera = c
    if focus is not None:
        if isinstance(focus, bpy.types.Object):
            cd.dof.focus_object = focus
        else:
            cd.dof.focus_distance = focus
    return c


def cam_key(cam, frame, loc, target, lens=None):
    cam.location = loc
    look_at(cam, target)
    cam.keyframe_insert("location", frame=frame)
    cam.keyframe_insert("rotation_euler", frame=frame)
    if lens is not None:
        cam.data.lens = lens
        cam.data.keyframe_insert("lens", frame=frame)


# ----------------------------------------------------------------------------
# characters
# ----------------------------------------------------------------------------

CHARACTERS = {
    # Main character: original British homeowner. Same toy/clay rendering
    # language as the reference, but a distinct identity: tweed flat cap,
    # grey moustache & sideburns, no glasses, mustard knit cardigan.
    "arthur": dict(
        skin="#f2b899", head=(1.0, 0.88, 1.02), hat="flatcap", hat_col="#6a5b44",
        hair="#bfbab3", hair_style="sides", brows="#a9a39b", moustache="#9d968d", beard=None,
        top="cardigan", top_col="#2f6b5a", shirt="#efe6d6", trousers="#3a3f4a", shoes="#4a2e1d",
        eye_iris="#3b2618", glasses=False,
    ),
    # Fictional careless contractor (generic, not based on any real person)
    "cowboy": dict(
        skin="#d99a73", head=(0.96, 0.86, 1.0), hat="cap_back", hat_col="#a8322a",
        hair="#3b2a20", hair_style="none", brows="#2e2019", moustache=None, beard="stubble",
        top="hoodie", top_col="#6b6e73", shirt=None, trousers="#2c3e5a", shoes="#2a2420",
        eye_iris="#1f1a17", glasses=False,
    ),
    # Sureshield roofers: navy workwear + hi-vis, white hard hats
    "roofer1": dict(
        skin="#c98563", head=(1.0, 0.88, 1.0), hat="hardhat", hat_col="#f2f0ea",
        hair="#3a2a1e", hair_style="none", brows="#2d2018", moustache=None, beard="full",
        beard_col="#4a3324", top="workwear", top_col="#1f2a44", vest="#d9f22c", shirt=None,
        trousers="#1c2233", shoes="#222222", eye_iris="#2a1a10", glasses=False,
    ),
    "roofer2": dict(
        skin="#f0b48e", head=(0.98, 0.86, 1.04), hat="hardhat", hat_col="#f2f0ea",
        hair="#c06a2e", hair_style="none", brows="#a85a26", moustache=None, beard=None,
        top="workwear", top_col="#1f2a44", vest="#d9f22c", shirt=None,
        trousers="#1c2233", shoes="#222222", eye_iris="#2c4a5e", glasses=False,
    ),
}


class Character:
    """A simple hierarchical toy rig built from rounded primitives."""

    def __init__(self, name, style, loc=(0, 0, 0), rot_z=0.0):
        self.name = name
        s = CHARACTERS[style]
        self.s = s
        pre = name + "_"
        skin = mat_basic(pre + "skin", s["skin"], rough=0.55, sss=0.25)
        white = mat_basic("eye_white", "#f7f4ef", rough=0.15, coat=1.0)
        iris = mat_basic(pre + "iris", s["eye_iris"], rough=0.1, coat=1.0)
        black = mat_basic("pupil_black", "#050505", rough=0.1, coat=1.0)
        hl = mat_emission("eye_hl", "#ffffff", 6.0)
        dark = mat_basic("mouth_dark", "#3a1410", rough=0.5)

        self.root = empty(pre + "root", loc, (0, 0, rot_z))
        self.hips = empty(pre + "hips", (0, 0, 0.62), parent=self.root)
        # torso -------------------------------------------------------------
        self.torso = empty(pre + "torso", (0, 0, 0.0), parent=self.hips)
        top = s["top"]
        if top == "cardigan":
            tm = mat_knit(pre + "top", s["top_col"], scale=24)
        elif top == "hoodie":
            tm = mat_fabric(pre + "top", s["top_col"], rough=0.9)
        else:
            tm = mat_fabric(pre + "top", s["top_col"], rough=0.75)
        rbox(pre + "body", (0.86, 0.56, 0.78), 0.22, tm, (0, 0, 0.36), parent=self.torso)
        if s.get("shirt"):
            sh = mat_fabric(pre + "shirt", s["shirt"], rough=0.7)
            rbox(pre + "shirtV", (0.16, 0.05, 0.26), 0.03, sh, (0, -0.272, 0.6), parent=self.torso)
            for sx in (-1, 1):
                rbox(pre + f"collar{sx}", (0.15, 0.04, 0.09), 0.02, sh, (sx * 0.08, -0.29, 0.72),
                     rot=rad(0, sx * 28, 0), parent=self.torso)
            bm = mat_basic("btn", "#5a3a1c", rough=0.3, coat=0.5)
            for i in range(3):
                sphere(pre + f"btn{i}", 0.028, bm, (0.0, -0.3, 0.33 - i * 0.12), parent=self.torso, seg=16)
        if top == "hoodie":
            rbox(pre + "hood", (0.7, 0.3, 0.2), 0.1, tm, (0, 0.2, 0.78), parent=self.torso)
            rbox(pre + "pocket", (0.5, 0.05, 0.2), 0.05, tm, (0, -0.285, 0.2), parent=self.torso)
            lace = mat_basic("lace", "#e8e4dc", rough=0.6)
            for x in (-0.08, 0.08):
                cyl(pre + f"lace{x}", 0.012, 0.2, lace, (x, -0.29, 0.6), parent=self.torso, seg=8)
        if s.get("vest"):
            vm = mat_basic(pre + "vest", s["vest"], rough=0.55, emit=s["vest"], emit_strength=0.15)
            refl = mat_basic("reflect", "#c9ccd2", rough=0.25, metal=0.6)
            rbox(pre + "vestL", (0.3, 0.6, 0.66), 0.12, vm, (-0.27, 0.0, 0.38), parent=self.torso)
            rbox(pre + "vestR", (0.3, 0.6, 0.66), 0.12, vm, (0.27, 0.0, 0.38), parent=self.torso)
            for zz in (0.24, 0.44):
                rbox(pre + f"refl{zz}", (0.9, 0.6, 0.055), 0.025, refl, (0, 0.0, zz), parent=self.torso)
        # legs ---------------------------------------------------------------
        trous = mat_fabric(pre + "trousers", s["trousers"], rough=0.8)
        shoe = mat_basic(pre + "shoes", s["shoes"], rough=0.35, coat=0.3)
        self.leg = {}
        self.knee = {}
        for side, x in (("L", 0.2), ("R", -0.2)):
            hip = empty(pre + "hip" + side, (x, 0, 0.05), parent=self.hips)
            rbox(pre + "thigh" + side, (0.27, 0.29, 0.36), 0.12, trous, (0, 0, -0.16), parent=hip)
            knee = empty(pre + "knee" + side, (0, 0, -0.3), parent=hip)
            rbox(pre + "shin" + side, (0.25, 0.27, 0.3), 0.11, trous, (0, 0, -0.12), parent=knee)
            rbox(pre + "shoe" + side, (0.28, 0.4, 0.14), 0.07, shoe, (0, -0.06, -0.3), parent=knee)
            self.leg[side] = hip
            self.knee[side] = knee
        # arms ---------------------------------------------------------------
        self.shoulder = {}
        self.elbow = {}
        self.hand = {}
        glove = s.get("vest") is not None
        hand_m = mat_basic(pre + "glove", "#3a3f46", rough=0.7) if glove else skin
        for side, x in (("L", 0.5), ("R", -0.5)):
            sh = empty(pre + "shoulder" + side, (x, 0, 0.62), parent=self.torso)
            rbox(pre + "uarm" + side, (0.22, 0.24, 0.36), 0.1, tm, (0, 0, -0.14), parent=sh)
            el = empty(pre + "elbow" + side, (0, 0, -0.28), parent=sh)
            rbox(pre + "farm" + side, (0.21, 0.23, 0.3), 0.1, tm, (0, 0, -0.12), parent=el)
            hd = empty(pre + "hand" + side, (0, 0, -0.32), parent=el)
            rbox(pre + "palm" + side, (0.2, 0.15, 0.2), 0.075, hand_m, (0, 0, -0.04), parent=hd)
            rbox(pre + "thumb" + side, (0.07, 0.07, 0.12), 0.035, hand_m,
                 (-math.copysign(0.0, x), -0.09, 0.0), rot=rad(25, 0, 0), parent=hd)
            self.shoulder[side] = sh
            self.elbow[side] = el
            self.hand[side] = hd
        # head ---------------------------------------------------------------
        hw, hd_, hh = s["head"]
        self.neck = empty(pre + "neck", (0, 0, 0.78), parent=self.torso)
        rbox(pre + "neckM", (0.3, 0.3, 0.12), 0.05, skin, (0, 0, 0.02), parent=self.neck)
        self.head = empty(pre + "head", (0, 0, 0.06), parent=self.neck)
        self.head.scale = (1.22, 1.22, 1.22)
        hc = hh / 2
        self.head_mesh = rbox(pre + "headM", (hw, hd_, hh), 0.26, skin, (0, 0, hc), parent=self.head, seg=6)
        fy = -hd_ / 2
        # ears
        for x in (hw / 2, -hw / 2):
            rbox(pre + f"ear{x}", (0.1, 0.16, 0.22), 0.05, skin, (x * 1.02, 0.02, hc - 0.02), parent=self.head)
        # eyes (groups so we can blink / look)
        self.eyes = []
        self.pupils = []
        for x in (0.2, -0.2):
            eg = empty(pre + f"eye{x}", (x, fy + 0.01, hc + 0.06), parent=self.head)
            sphere(pre + f"ew{x}", 0.125, white, (0, 0, 0), scale=(1.0, 0.45, 1.1), parent=eg)
            pg = empty(pre + f"pg{x}", (0, -0.03, 0), parent=eg)
            sphere(pre + f"iris{x}", 0.078, iris, (0, -0.03, -0.005), scale=(1, 0.45, 1.05), parent=pg)
            sphere(pre + f"pup{x}", 0.045, black, (0, -0.052, -0.005), scale=(1, 0.4, 1), parent=pg)
            sphere(pre + f"hl{x}", 0.02, hl, (0.03, -0.07, 0.035), parent=pg, seg=12)
            self.eyes.append(eg)
            self.pupils.append(pg)
        # brows
        brow_m = mat_basic(pre + "brow", s["brows"], rough=0.9)
        self.brows = []
        for x in (0.2, -0.2):
            b = empty(pre + f"browP{x}", (x, fy - 0.01, hc + 0.25), parent=self.head)
            rbox(pre + f"brow{x}", (0.24, 0.07, 0.065), 0.03, brow_m, (0, 0, 0), parent=b)
            self.brows.append(b)
        # nose
        sphere(pre + "nose", 0.085, skin, (0, fy - 0.04, hc - 0.08), scale=(1.0, 0.9, 0.85), parent=self.head)
        # cheeks blush
        blush = mat_basic(pre + "blush", "#e07a6a", rough=0.6, sss=0.2)
        for x in (0.3, -0.3):
            sphere(pre + f"cheek{x}", 0.07, blush, (x, fy + 0.012, hc - 0.12), scale=(1, 0.2, 0.7), parent=self.head)
        # mouth: bezier curve; middle point animates for smile / frown
        mz = hc - 0.27
        self.mouth = curve_obj(pre + "mouth", [(-0.11, 0, 0.02), (0, 0, -0.03), (0.11, 0, 0.02)], 0.018, dark,
                               parent=self.head, loc=(0, fy - 0.012, mz))
        if s.get("moustache"):
            mm = mat_knit(pre + "mous", s["moustache"], scale=140, rough=0.95)
            for x, r in ((0.11, -16), (-0.11, 16)):
                rbox(pre + f"mous{x}", (0.25, 0.1, 0.1), 0.048, mm, (x, fy - 0.035, hc - 0.175),
                     rot=rad(0, r, 0), parent=self.head)
        if s.get("beard") == "full":
            bmat = mat_knit(pre + "beard", s.get("beard_col", "#4a3324"), scale=120, rough=0.95)
            rbox(pre + "beard", (hw * 0.98, hd_ * 0.6, 0.36), 0.16, bmat, (0, fy * 0.45 - 0.02, 0.12), parent=self.head)
            rbox(pre + "mous", (0.36, 0.08, 0.08), 0.04, bmat, (0, fy - 0.03, hc - 0.19), parent=self.head)
            self.mouth.location.y -= 0.035
        elif s.get("beard") == "stubble":
            st = mat_basic(pre + "stub", "#7c5a48", rough=0.9, sss=0.1)
            rbox(pre + "stub", (hw * 0.96, hd_ * 0.6, 0.3), 0.14, st, (0, fy * 0.45 + 0.005, 0.13), parent=self.head)
        # hair
        hair = mat_knit(pre + "hair", s["hair"], scale=160, rough=0.95)
        if s["hair_style"] == "sides":
            for x in (hw / 2, -hw / 2):
                rbox(pre + f"hairS{x}", (0.1, 0.5, 0.38), 0.05, hair, (x * 1.01, 0.12, hc + 0.18), parent=self.head)
            rbox(pre + "hairB", (hw * 0.92, 0.1, 0.42), 0.05, hair, (0, -fy * 1.01, hc + 0.16), parent=self.head)
        # hats
        hat = s["hat"]
        if hat == "flatcap":
            tw = mat_tweed(pre + "cap", s["hat_col"])
            rbox(pre + "capC", (hw * 1.06, hd_ * 1.08, 0.24), 0.11, tw, (0, 0.02, hh - 0.02), parent=self.head, seg=5)
            rbox(pre + "capT", (hw * 1.02, hd_ * 1.22, 0.16), 0.08, tw, (0, -0.1, hh + 0.07),
                 rot=rad(-11, 0, 0), parent=self.head, seg=5)
            rbox(pre + "capB", (hw * 0.9, 0.34, 0.05), 0.024, tw, (0, fy - 0.16, hh - 0.03),
                 rot=rad(14, 0, 0), parent=self.head)
            btn = mat_tweed(pre + "cap", s["hat_col"])
            sphere(pre + "capBtn", 0.04, btn, (0, -0.05, hh + 0.16), parent=self.head, seg=16)
        elif hat == "hardhat":
            hm = mat_basic(pre + "hhat", s["hat_col"], rough=0.25, coat=0.7)
            dome = sphere(pre + "hhD", 0.56, hm, (0, 0.0, hh - 0.08), scale=(hw * 1.0, hd_ * 1.12, 0.62), parent=self.head)
            cyl(pre + "hhB", 0.6, 0.04, hm, (0, -0.05, hh - 0.1), parent=self.head).scale = (hw, hd_ * 1.25, 1)
            rbox(pre + "hhR", (0.1, hd_ * 1.0, 0.07), 0.035, hm, (0, 0, hh + 0.24), parent=self.head)
        elif hat == "cap_back":
            cm = mat_fabric(pre + "cap", s["hat_col"], rough=0.8)
            sphere(pre + "capD", 0.53, cm, (0, 0.02, hh - 0.08), scale=(hw * 1.03, hd_ * 1.12, 0.55), parent=self.head)
            rbox(pre + "capBr", (0.5, 0.36, 0.05), 0.024, cm, (0.05, -fy + 0.2, hh - 0.1),
                 rot=rad(-10, 0, 8), parent=self.head)
        self.set_mouth(0.0)

    # -- expression controls ---------------------------------------------------
    def set_mouth(self, smile, frame=None, open_=0.0):
        """smile: -1 (frown) .. 1 (big smile)."""
        pts = self.mouth.data.splines[0].bezier_points
        pts[0].co = (-0.11, 0, 0.025 * smile)
        pts[2].co = (0.11, 0, 0.025 * smile)
        pts[1].co = (0, 0, -0.05 * smile - open_ * 0.04)
        if frame is not None:
            for p in pts:
                p.keyframe_insert("co", frame=frame)

    def brows_key(self, frame, worry=0.0, raise_=0.0):
        """worry > 0 : inner ends up (sad/concerned); < 0 : angry."""
        for b, sgn in zip(self.brows, (1, -1)):
            b.rotation_euler = (0, math.radians(18 * worry) * sgn, 0)
            b.location.z = (self.s["head"][2] / 2) + 0.25 + 0.05 * raise_
            b.keyframe_insert("rotation_euler", frame=frame)
            b.keyframe_insert("location", frame=frame)

    def look(self, frame, x=0.0, z=0.0):
        for p in self.pupils:
            p.location = (x * 0.045, -0.03, z * 0.04)
            p.keyframe_insert("location", frame=frame)

    def blink(self, frame, dur=4):
        for e in self.eyes:
            e.scale = (1, 1, 1)
            e.keyframe_insert("scale", frame=frame - 1)
            e.scale = (1, 1, 0.08)
            e.keyframe_insert("scale", frame=frame + dur // 2)
            e.scale = (1, 1, 1)
            e.keyframe_insert("scale", frame=frame + dur)

    def blinks(self, start, end, every=70, seed=1):
        rnd = random.Random(seed)
        f = start + rnd.randint(10, 30)
        while f < end - 6:
            self.blink(f)
            f += every + rnd.randint(-20, 25)

    def breathe(self, start, end, period=60, amp=0.012):
        f = start
        i = 0
        while f <= end:
            self.torso.scale = (1, 1, 1 + (amp if i % 2 else 0))
            self.torso.keyframe_insert("scale", frame=f)
            f += period // 2
            i += 1

    def pose_arm(self, side, frame, fwd=0.0, out=0.0, twist=0.0, elbow=0.0, elbow_side=0.0):
        """Angles in degrees. fwd: raise toward camera(-Y); out: abduct sideways; elbow: bend."""
        sgn = 1 if side == "L" else -1
        sh = self.shoulder[side]
        sh.rotation_euler = rad(-fwd, -sgn * out, twist)
        sh.keyframe_insert("rotation_euler", frame=frame)
        el = self.elbow[side]
        el.rotation_euler = rad(-elbow, -sgn * elbow_side, 0)
        el.keyframe_insert("rotation_euler", frame=frame)

    def pose_head(self, frame, tilt=0.0, nod=0.0, turn=0.0):
        self.head.rotation_euler = rad(nod, tilt, turn)
        self.head.keyframe_insert("rotation_euler", frame=frame)

    def pose_body(self, frame, lean=0.0, side=0.0, turn=0.0, z=None):
        self.torso.rotation_euler = rad(lean, side, turn)
        self.torso.keyframe_insert("rotation_euler", frame=frame)

    def sit(self):
        for side in ("L", "R"):
            self.leg[side].rotation_euler = rad(-88, 0, 0)
            self.knee[side].rotation_euler = rad(92, 0, 0)

    def rest_pose(self, frame):
        for side in ("L", "R"):
            self.pose_arm(side, frame, fwd=4, out=8, elbow=10)
        self.pose_head(frame)
        self.brows_key(frame)
        self.look(frame)


# ----------------------------------------------------------------------------
# props
# ----------------------------------------------------------------------------

def ladder(name, loc, height=6.0, lean=15, rot_z=0.0):
    m = mat_basic("ladder", "#b7bcc2", rough=0.35, metal=0.8)
    root = empty(name, loc, rad(-lean, 0, rot_z))
    for x in (-0.28, 0.28):
        rbox(f"{name}_rail{x}", (0.07, 0.1, height), 0.025, m, (x, 0, height / 2), parent=root)
    n = int(height / 0.32)
    for i in range(1, n):
        cyl(f"{name}_rung{i}", 0.025, 0.56, m, (0, 0, i * 0.32), rad(0, 90, 0), parent=root, seg=12)
    return root


def hammer(name, parent=None, loc=(0, 0, 0), rot=(0, 0, 0)):
    wood = mat_basic("wood", "#a8743f", rough=0.5)
    steel = mat_basic("steel", "#8b9198", rough=0.25, metal=1.0)
    root = empty(name, loc, rot, parent=parent)
    rbox(name + "_h", (0.05, 0.05, 0.42), 0.02, wood, (0, 0, -0.16), parent=root)
    rbox(name + "_head", (0.22, 0.07, 0.08), 0.02, steel, (0.03, 0, 0.06), parent=root)
    return root


def tablet(name, parent=None, loc=(0, 0, 0), rot=(0, 0, 0)):
    case = mat_basic("tab_case", "#222631", rough=0.4)
    scr = mat_emission("tab_scr", "#9cc8ff", 2.0)
    root = empty(name, loc, rot, parent=parent)
    rbox(name + "_c", (0.36, 0.03, 0.26), 0.02, case, (0, 0, 0), parent=root)
    rbox(name + "_s", (0.32, 0.01, 0.22), 0.01, scr, (0, -0.017, 0), parent=root)
    return root


def mug(name, parent=None, loc=(0, 0, 0), color="#e9e2d6"):
    m = mat_basic("mug_" + color, color, rough=0.2, coat=0.6)
    tea = mat_basic("tea", "#6b3d1e", rough=0.1)
    root = empty(name, loc, parent=parent)
    cyl(name + "_b", 0.1, 0.22, m, (0, 0, 0), parent=root)
    cyl(name + "_t", 0.085, 0.01, tea, (0, 0, 0.1), parent=root)
    rbox(name + "_hd", (0.05, 0.04, 0.12), 0.02, m, (0.12, 0, 0), parent=root)
    return root


# ----------------------------------------------------------------------------
# environment: British semi with real tile geometry
# ----------------------------------------------------------------------------

TILE_W, TILE_L, TILE_T = 0.44, 0.36, 0.06


def tile_mesh():
    return rbox_mesh(TILE_W - 0.03, TILE_L, TILE_T, 0.025, 3, key="roof_tile")


def build_roof_slope(name, origin, width, length, pitch_deg, mat, rows=None, damage=None, seed=3,
                     missing=(), parent=None, visible_rows=None, row_offset_fn=None):
    """Tiles laid in staggered rows on a plane.  origin = eave-left corner; the
    slope rises toward +Y.  Returns (root, {(r,c): obj})."""
    root = empty(name, origin, rad(-(90 - 90) + pitch_deg, 0, 0), parent=parent)
    # local frame: X along eave, Y up the slope
    step_r = TILE_L * 0.78
    n_r = rows or int(length / step_r)
    n_c = int(width / TILE_W) + 2
    me = tile_mesh()
    rnd = random.Random(seed)
    tiles = {}
    under = mat_basic("underlay", "#1a1714", rough=0.9)
    rbox(name + "_deck", (width + 0.2, length + 0.1, 0.05), 0.01, under, (width / 2, length / 2, -0.02), parent=root)
    for r in range(n_r):
        if visible_rows and r not in visible_rows:
            continue
        off = (TILE_W / 2) * (r % 2)
        for c in range(n_c):
            x = c * TILE_W - off
            if x < -0.05 or x > width + 0.05:
                continue
            if (r, c) in missing:
                continue
            t = obj(f"{name}_t{r}_{c}", me, mat, parent=root)
            t.location = (x, r * step_r + TILE_L / 2, 0.035 + 0.012 * (r % 2) * 0)
            t.rotation_euler = (math.radians(-4), 0, math.radians(rnd.uniform(-0.6, 0.6)))
            if damage and (r, c) in damage:
                dx, dy, dz, rx, ry, rz = damage[(r, c)]
                t.location.x += dx
                t.location.y += dy
                t.location.z += dz
                t.rotation_euler = rad(-4 + rx, ry, rz)
            tiles[(r, c)] = t
    return root, tiles


def window(name, loc, w, h, parent=None, lit=True, warm=1.0, frame_col="#efeee9", depth=0.12):
    fm = mat_basic("win_frame_" + frame_col, frame_col, rough=0.35)
    if lit:
        gm = mat_emission(f"glass_lit_{warm:.2f}", (1.0, 0.5, 0.18, 1), 0.7 * warm)
    else:
        gm = mat_basic("glass_dark", "#0c1220", rough=0.05, coat=1.0)
    root = empty(name, loc, parent=parent)
    rbox(name + "_g", (w, 0.04, h), 0.01, gm, (0, 0.0, 0), parent=root)
    if lit:
        cm = mat_fabric("curtain", "#7a2f2a", rough=0.9)
        for sx in (-1, 1):
            rbox(name + f"_cur{sx}", (w * 0.2, 0.03, h * 0.95), 0.01, cm, (sx * w * 0.38, -0.025, 0), parent=root)
    t = 0.09
    rbox(name + "_t", (w + t, depth, t), 0.03, fm, (0, 0, h / 2), parent=root)
    rbox(name + "_b", (w + 2 * t, depth * 1.6, t * 1.2), 0.03, fm, (0, -0.04, -h / 2 - 0.02), parent=root)
    rbox(name + "_l", (t, depth, h), 0.03, fm, (-w / 2, 0, 0), parent=root)
    rbox(name + "_r", (t, depth, h), 0.03, fm, (w / 2, 0, 0), parent=root)
    rbox(name + "_m", (0.05, depth * 0.7, h), 0.02, fm, (0, -0.01, 0), parent=root)
    rbox(name + "_x", (w, depth * 0.7, 0.05), 0.02, fm, (0, -0.01, h * 0.2), parent=root)
    return root


def build_house(name="house", loc=(0, 0, 0), damage_level=0, lit=(1, 1, 0, 1), seed=5, detail=True,
                brick="#8a3b26", door="#1f3b4d", new_roof=False, roof_rows=None):
    """British two-storey red-brick semi.  Front faces -Y.  Returns dict."""
    W, D, H = 6.4, 5.0, 5.0
    root = empty(name, loc)
    br = mat_brick("brick_" + brick, brick)
    rbox(name + "_walls", (W, D, H), 0.04, br, (0, 0, H / 2), parent=root)
    # front wall sits slightly proud so windows read as recessed
    fwall = rbox(name + "_fw", (W, 0.1, H), 0.02, br, (0, -D / 2 + 0.06, H / 2), parent=root)
    # gable roof: slope from front eave (y=-D/2-0.3, z=H) to ridge (y=0, z=H+2.6)
    rise = 2.6
    run = D / 2 + 0.35
    pitch = math.degrees(math.atan2(rise, run))
    length = math.hypot(rise, run) + 0.15
    tile_m = mat_tile("tile_new" if new_roof else "tile", "#c0582f" if new_roof else "#a9502f")
    dmg = {}
    missing = set()
    if damage_level:
        rnd = random.Random(seed)
        hot = [(5, 6), (5, 7), (6, 6), (4, 7), (6, 8), (7, 7), (5, 9), (8, 4), (3, 10)]
        for i, rc in enumerate(hot[: 3 + damage_level * 3]):
            dmg[rc] = (rnd.uniform(-0.12, 0.12), rnd.uniform(-0.25, 0.05), rnd.uniform(0.04, 0.16),
                       rnd.uniform(-25, 10), rnd.uniform(-18, 18), rnd.uniform(-25, 25))
        missing = {(6, 7), (5, 8)} if damage_level >= 2 else {(6, 7)}
    front = None
    tiles = {}
    if detail:
        front, tiles = build_roof_slope(name + "_rf", (-W / 2 - 0.25, -D / 2 - 0.35, H - 0.05), W + 0.5, length,
                                        pitch, tile_m, damage=dmg, missing=missing, seed=seed, parent=root,
                                        rows=roof_rows)
    else:
        pl = rbox(name + "_rfp", (W + 0.5, length, 0.12), 0.03, mat_tile("tile_flat", "#7d3b26", wet=False),
                  (0, -run / 2 - 0.0, H + rise / 2), rad(pitch, 0, 0), parent=root)
    # back slope (simple)
    rbox(name + "_rb", (W + 0.5, length, 0.12), 0.03, mat_tile("tile_flat", "#7d3b26", wet=False),
         (0, run / 2, H + rise / 2 - 0.05), rad(-pitch, 0, 0), parent=root)
    # gable end walls (triangular) approximated by a scaled, rotated box clipped inside roof
    obj(name + "_gable", prism_mesh(W - 0.05, D, rise), br, (0, 0, H - 0.02), parent=root)
    # ridge
    ridge_m = mat_tile("ridge", "#8e3f25", wet=True)
    cyl(name + "_ridge", 0.16, W + 0.6, ridge_m, (0, 0.0, H + rise + 0.08), rad(0, 90, 0), parent=root)
    # chimney
    ch = rbox(name + "_ch", (0.9, 0.7, 2.0), 0.03, br, (W / 2 - 1.0, 0.2, H + rise + 0.4), parent=root)
    pot = mat_basic("pot", "#9a4a2c", rough=0.6)
    for x in (-0.2, 0.2):
        cyl(name + f"_pot{x}", 0.11, 0.45, pot, (W / 2 - 1.0 + x, 0.2, H + rise + 1.6), parent=root, r2=0.09)
    # gutter + fascia
    fas = mat_basic("fascia", "#ecebe6", rough=0.4)
    rbox(name + "_fascia", (W + 0.6, 0.06, 0.24), 0.02, fas, (0, -D / 2 - 0.38, H - 0.08), parent=root)
    gut = mat_basic("gutter", "#1b1d22", rough=0.3)
    cyl(name + "_gutter", 0.08, W + 0.6, gut, (0, -D / 2 - 0.46, H - 0.22), rad(0, 90, 0), parent=root)
    cyl(name + "_down", 0.05, H, gut, (W / 2 + 0.15, -D / 2 - 0.1, H / 2), parent=root)
    # windows (front face y=-D/2)
    fy = -D / 2 - 0.02
    window(name + "_w1", (-1.6, fy, 3.7), 1.4, 1.2, parent=root, lit=bool(lit[0]), warm=0.9)
    window(name + "_w2", (1.5, fy, 3.7), 1.4, 1.2, parent=root, lit=bool(lit[1]), warm=0.75)
    window(name + "_w3", (-1.6, fy, 1.5), 1.9, 1.5, parent=root, lit=bool(lit[3]), warm=1.0)
    # door + porch
    dm = mat_basic("door_" + door, door, rough=0.3, coat=0.6)
    rbox(name + "_door", (1.0, 0.12, 2.1), 0.03, dm, (1.5, fy + 0.02, 1.05), parent=root)
    rbox(name + "_dframe", (1.24, 0.1, 2.3), 0.03, fas, (1.5, fy + 0.06, 1.12), parent=root)
    brass = mat_basic("brass", "#c9a24a", rough=0.25, metal=1.0)
    sphere(name + "_knob", 0.05, brass, (1.85, fy - 0.07, 1.05), parent=root, seg=16)
    porch = rbox(name + "_porch", (1.6, 0.7, 0.12), 0.03, fas, (1.5, fy - 0.3, 2.45), rad(-8, 0, 0), parent=root)
    pl = point_light(name + "_porchL", (loc[0] + 1.5, loc[1] + fy - 0.4, loc[2] + 2.25), 25, "#ffb066", 0.08)
    lamp = mat_emission("lamp_glow", "#ffc78a", 12)
    sphere(name + "_lamp", 0.08, lamp, (1.5, fy - 0.45, 2.28), parent=root, seg=16)
    rbox(name + "_step", (1.4, 0.5, 0.15), 0.03, mat_basic("stone", "#6d6a66", rough=0.6), (1.5, fy - 0.25, 0.075), parent=root)
    return dict(root=root, tiles=tiles, front=front, W=W, D=D, H=H, rise=rise, pitch=pitch, roof_len=length)


def build_ground(size=80, wet=True):
    g = mat_wet_ground("ground_wet") if wet else mat_basic("ground", "#1d2018", rough=0.8)
    me = rbox_mesh(size, size, 0.1, 0.01, 1, key="ground")
    return obj("ground", me, g, (0, 0, -0.05))


def build_garden(house_loc=(0, 0, 0)):
    x0, y0, _ = house_loc
    grass = mat_fabric("grass", "#16240f", rough=0.9, scale=60)
    grass.node_tree.nodes["Principled BSDF"].inputs["Sheen Weight"].default_value = 0.0
    rbox("lawn", (7.0, 4.0, 0.1), 0.03, grass, (x0 - 1.0, y0 - 4.6, 0.02))
    path = mat_basic("path", "#2e2d2c", rough=0.25)
    rbox("path", (1.3, 4.2, 0.08), 0.02, path, (x0 + 1.5, y0 - 4.6, 0.04))
    hedge = mat_knit("hedge", "#1f3a1e", scale=30)
    rbox("hedge", (0.6, 4.0, 1.1), 0.25, hedge, (x0 - 4.2, y0 - 4.6, 0.55))


def build_background_street(y=14.0, n=9, seed=11, spread=4.2, z0=0.0, lit_prob=0.65):
    """Far terraced houses with warm lit windows -> bokeh in DOF."""
    rnd = random.Random(seed)
    br = mat_brick("brick_far", "#5e2a1c", scale=4)
    roof = mat_basic("roof_far", "#2a1e1c", rough=0.6)
    for i in range(n):
        x = (i - n / 2) * spread * 1.6
        h = 5.0 + rnd.uniform(-0.3, 0.6)
        rbox(f"bg_h{i}", (spread * 1.55, 4, h), 0.05, br, (x, y, h / 2 + z0))
        rbox(f"bg_r{i}", (spread * 1.6, 3.2, 0.2), 0.04, roof, (x, y - 0.6, h + 1.0 + z0), rad(38, 0, 0))
        cyl(f"bg_ch{i}", 0.3, 1.6, br, (x + 1.5, y + 0.4, h + 1.8 + z0))
        for j, (wx, wz) in enumerate(((-1.6, 1.4), (1.6, 1.4), (-1.6, 3.6), (1.6, 3.6))):
            lit = rnd.random() < lit_prob
            col = (1.0, rnd.uniform(0.5, 0.68), rnd.uniform(0.18, 0.3), 1)
            m = mat_emission(f"bgwin_{i}_{j}", col, rnd.uniform(3.5, 9.0)) if lit else mat_basic("bgwin_dark", "#0b0f18", rough=0.1)
            rbox(f"bg_w{i}_{j}", (1.0, 0.1, 1.0), 0.02, m, (x + wx, y - 2.03, wz + z0))
    # street lamps
    pole = mat_basic("pole", "#1a1c20", rough=0.4, metal=0.5)
    glow = mat_emission("street_glow", "#ffb35c", 30)
    for i in range(-3, 4):
        x = i * 9.0 + 3
        cyl(f"pole{i}", 0.06, 5.5, pole, (x, y - 6.5, 2.75))
        sphere(f"glow{i}", 0.22, glow, (x, y - 6.5, 5.6), seg=16)


def bokeh_lights(n=60, center=(0, 30, 6), spread=(40, 10, 8), seed=4, strength=(4, 14)):
    rnd = random.Random(seed)
    for i in range(n):
        warm = rnd.random() < 0.85
        col = (1.0, rnd.uniform(0.5, 0.72), rnd.uniform(0.2, 0.35), 1) if warm else (0.45, 0.6, 1.0, 1)
        m = mat_emission(f"bk{i}", col, rnd.uniform(*strength))
        sphere(f"bk{i}", rnd.uniform(0.06, 0.16), m,
               (center[0] + rnd.uniform(-1, 1) * spread[0], center[1] + rnd.uniform(-1, 1) * spread[1],
                center[2] + rnd.uniform(-1, 1) * spread[2]), seg=12)


def standard_night_lights(target=(0, 0, 1.5), key_loc=(-4, -6, 5), key_e=900, rim_loc=(5, 6, 6), rim_e=1500,
                          fill_e=120):
    area_light("key", key_loc, target, key_e, "#ffc596", size=3.0)
    area_light("rim", rim_loc, target, rim_e, "#7fa6ff", size=3.0)
    area_light("fill", (6, -8, 2), target, fill_e, "#5a78c8", size=6.0)


def render_settings(res_pct=50, samples=24, frame_start=1, frame_end=1, out="//render/"):
    scn = bpy.context.scene
    scn.render.resolution_x = 1080
    scn.render.resolution_y = 1920
    scn.render.resolution_percentage = res_pct
    scn.cycles.samples = samples
    scn.frame_start = frame_start
    scn.frame_end = frame_end
    scn.render.filepath = out
