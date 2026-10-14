"""scene_squall.py -- SQUALL (tsquall_1), the fourth film.

Storm-dusk market plaza: the first heavy drops open the film, streams
converge on the central arcade (the +/=5 arrival box IS the covered
floor), the doorway chokes, a straggler slips beside the fountain and
stays down, a queue holds at the food window, the plaza empties, and
the last lightning flash ignites the neon SQUALL over the entrance.

Design of record: docs/DESIGN_squall.md REV-3. Contract:
tsquall_contract.py (zones/speeds/keepouts/seed/portal/queue -- the
single crowd authority). World: tsquall_world.py. The honest-crowd law:
everyone walks to their spawn-sampled box goal once -- the drama is in
the EDGES (the overtake, the choke, the slip, the queue, the light).

The scene_green_light module shape throughout (the loader owns the
crowd chain). Export contract: build_scene returns ctx["scene"]; BEATS
(id, t_seconds, label); sfx {name|kind, frame}; render.fps pinned here.
"""
from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

import bpy

_here = str(Path(__file__).resolve().parent)
if _here not in sys.path:
    sys.path.insert(0, _here)

_lab = Path(__file__).resolve().parent.parent.parent
_sib = _lab / "blender-escape-previz" / "scripts"
_previz_scripts = os.environ.get(
    "TSQUALL_PREVIZ_SCRIPTS",
    str(_sib) if _sib.is_dir() else "/home/z/work/blender-escape-previz/scripts")
if _previz_scripts not in sys.path:
    sys.path.insert(0, _previz_scripts)

FPS = 24
total_frames = 1080
ts_exposure = 0.0            # the storm-dusk ladder sweeps sun/sky/practicals
# the LADDER VERDICT (scripts/tsquall_ladder.py, the eye picked it):
# sun5/sky0.15/82deg -- the moody storm-dusk; the practicals own the
# interior; the sun lamp is nearly inert below energy 7 (the tgreen
# sky-ambient law reconfirmed in the storm regime)
TS_SUN_ENERGY = 5.0
TS_SUN_ELEV = 82.0
TS_SUN_COLOR = (1.0, 0.70, 0.45)
TS_SKY_COLOR = (0.045, 0.055, 0.078)
TS_SKY_STRENGTH = 0.15
TS_THUNDER = (85, 625, 1009)   # the flash frames (the title flash last)

_here = os.path.dirname(os.path.abspath(__file__))

# --- shots (id, f0, f1, intent) -- the REV-3 vantage table ------------
SHOTS_V3 = [
    ("S1",  1,    84,  "aerial: first heavy drops; the slow bands drift"),
    ("S2",  85,   168, "the thunder hit: strings flicker; the fast band shows"),
    ("S3",  169,  264, "the streams merge toward the arcade mouth"),
    ("S4",  265,  348, "the doorway choke, from INSIDE looking out"),
    ("S5",  349,  444, "THE BEAT: the slip-and-fall beside the fountain"),
    ("S6",  445,  528, "the queue holds at the food window (side-on)"),
    ("S7",  529,  624, "the fill: under-canopy through the east colonnade"),
    ("S8",  625,  720, "the plaza empties (the honest beat)"),
    ("S9",  721,  816, "the peak-as-equilibrium: packed box + the fountain pair"),
    ("S10", 817,  912, "the storm eases: light warms; the last queue releases"),
    ("S11", 913,  1008, "the crane rises on the east flank"),
    ("S12", 1009, 1080, "title: the flash ignites the neon SQUALL"),
]

CAMS_V3 = [
    # S1: high-S aerial over the plaza (the slow bands: the edit
    # grammar -- motion starts calm)
    ("CAM_S1",  (-14.0, -20.0, 18.0), (-14.0, -20.0, 18.0), 24,
     (2.0, 1.0, 0.0), False, 0.0),
    # S2: low W oblique with storm sky + a stall string in frame
    ("CAM_S2",  (-18.0, 2.0, 1.8), (-18.0, 2.0, 1.8), 35,
     (2.0, 6.0, 2.4), False, 0.0),
    # S3: N-edge elevated; the merge reads down the approach
    ("CAM_S3",  (-6.0, 13.0, 4.5), (-6.0, 13.0, 4.5), 40,
     (0.0, 3.0, 0.8), False, 0.0),
    # S4: the doorway press from the WINDOW side (the S4b probe cert:
    # the press reads with shape + depth; S4a/c were the band-dominant
    # flood class)
    ("CAM_S4",  (5.0, -3.5, 1.6), (5.0, -3.5, 1.6), 35,
     (-2.0, 5.0, 1.2), False, 0.0),
    # S5: THE NADIR (the S5a probe cert: the amber faller isolated
    # mid-fall above the dark basin at f372, the prone hold at f430,
    # the crowd as muted texture -- the tgreen S5 law at storm scale)
    ("CAM_S5",  (14.8, 7.0, 11.0), (14.8, 7.0, 11.0), 40,
     (14.3, 9.8, 0.0), False, 0.0),
    # S6: side-on from the arcade floor; the line crosses frame
    # horizontally, window glow pooling right
    ("CAM_S6",  (1.5, 1.0, 1.7), (1.5, 1.0, 1.7), 50,
     (6.5, 1.5, 0.9), False, 0.0),
    # S7: exterior through the east colonnade under the eave -- three
    # graphic layers (rain sheet fg / packed interior / doorway glow)
    ("CAM_S7",  (9.5, 8.0, 3.2), (9.5, 8.0, 3.2), 35,
     (-2.0, 0.0, 1.2), False, 0.0),
    # S8: N-edge wide; the last stragglers cross, haze thickens
    ("CAM_S8",  (-8.0, 13.5, 2.6), (-8.0, 13.5, 2.6), 28,
     (6.0, 4.0, 0.8), False, 0.0),
    # S9: high-E oblique through the colonnade; the fountain pair in
    # frame right (the crescendo AND the callback)
    ("CAM_S9",  (20.0, 2.0, 11.0), (20.0, 2.0, 11.0), 35,
     (4.0, 3.0, 0.0), False, 0.0),
    # S10: interior; doorway + window glow; the light warms
    ("CAM_S10", (-3.0, 2.5, 1.6), (-3.0, 2.5, 1.6), 40,
     (5.0, -3.0, 1.2), False, 0.0),
    # the CRANE (S11): east flank rise (the ray-cast gate re-verifies)
    ("CAM_S11", (13.0, -2.0, 2.5), (11.0, -2.0, 11.0), 30,
     (2.0, 4.0, 0.8), False, 0.0),
    # S12: loc0 = S11 loc1 (continuity), then the descend+push north
    # above the doorway to the igniting band (audit 4-f: the roof
    # blocks the band from S11's loc1 -- S12 owns its second key)
    ("CAM_S12", (11.0, -2.0, 11.0), (6.0, 9.5, 5.0), 35,
     (0.0, 6.2, 3.2), False, 0.0),
]

BEATS = [
    ("drops",   0.0,  "the first heavy drops (f1)"),
    ("thunder", 3.50, "the thunder hit (f85)"),
    ("merge",   7.0,  "the streams merge (f169)"),
    ("choke",  11.0,  "the doorway press (f265)"),
    ("slip",   15.5,  "the slip-and-fall (f372)"),
    ("queue",  18.5,  "the queue holds (f445)"),
    ("fill",   22.0,  "the fill under the canopy (f529)"),
    ("drain",  26.0,  "the plaza empties (f625)"),
    ("peak",   30.0,  "the peak-as-equilibrium (f721)"),
    ("ease",   34.0,  "the storm eases (f817)"),
    ("crane",  38.0,  "the crane rises (f913)"),
    ("title",  42.0,  "the neon ignites (f1009)"),
]

CROWD_TIER_PINS = []


def frame_at(t):
    return int(round(t * FPS)) + 1


def _kf(ob, frame, loc=None, rot_z=None, scale=None):
    if loc is not None:
        ob.location = (loc[0], loc[1], ob.location.z)
        ob.keyframe_insert(data_path="location", frame=frame)
    if rot_z is not None:
        ob.rotation_euler = (0.0, 0.0, rot_z)
        ob.keyframe_insert(data_path="rotation_euler", frame=frame)
    if scale is not None:
        ob.scale = scale
        ob.keyframe_insert(data_path="scale", frame=frame)


def _bezier(ob):
    for fc in _iter_fcurves(ob.animation_data.action):
        for kp in fc.keyframe_points:
            kp.interpolation = "BEZIER"
            kp.handle_left_type = "AUTO_CLAMPED"
            kp.handle_right_type = "AUTO_CLAMPED"


def _iter_fcurves(action):
    """The 4.x/5.x fcurve iterator (the tdawn-vetted helper)."""
    try:
        from blender_kit import iter_fcurves
        return list(iter_fcurves(action))
    except Exception:
        pass
    fcurves = getattr(action, "fcurves", None)
    if fcurves is not None:
        return list(fcurves)
    out = []
    slots = list(getattr(action, "slots", []) or [])
    for layer in getattr(action, "layers", []) or []:
        for strip in getattr(layer, "strips", []) or []:
            bag = getattr(strip, "channelbag", None)
            if callable(bag):
                for slot in slots or [None]:
                    try:
                        b = bag(slot) if slot is not None else bag()
                    except TypeError:
                        continue
                    if b is not None and getattr(b, "fcurves", None):
                        out.extend(b.fcurves)
    return out


def _heroes(scene):
    """The keyed BYSTANDER (the 4-e F2b fold): a vendor-adjacent figure
    under the arcade eave who CROUCHES to the fallen stranger at f470
    and stays -- the witness that makes the fall a story. Warm amber
    coat (distinct from the muted crowd)."""
    from tdawn_actors import build_commuter_mesh, make_material
    mesh = build_commuter_mesh("TS.HeroMesh")
    mesh.location = (60.0, 0.0, -2.5)
    mesh.hide_render = True
    ob = bpy.data.objects.new("Bystander.Root", mesh.data)
    ob.location = (10.6, -1.2, 0.0)
    ob.rotation_euler = (0.0, 0.0, math.radians(125))
    scene.collection.objects.link(ob)
    ob.data = ob.data.copy()
    ob.data.materials.clear()
    ob.data.materials.append(make_material(
        "CA.Body.Bystander", (0.62, 0.42, 0.16), rough=0.5))
    return {"Bystander": ob}


def _crowd_anchors(scene):
    """The anchors the kit-mode loader's rename law expects: 126 crowd
    Zed.NNNN (the first 6 are the VENDORS -- parked at their stall
    posts) + 12 chase Zed.ChasePNN (3 RB slots per the loader law,
    parked outboard beyond the east stall row)."""
    from tdawn_actors import (build_commuter_mesh, new_anchored_obj,
                              commuter_material)
    lib = build_commuter_mesh("TS.CommlibLib",
                              mat_body=commuter_material(0))
    lib.location = (60.0, 0.0, -2.5)
    lib.hide_render = True
    crowd = []
    vendor_posts = ((-24.0, 1.5), (-24.0, 3.5), (-24.0, 5.5),
                    (24.0, 1.5), (24.0, 3.5), (24.0, 5.5))
    for i in range(126):
        if i < 6:
            x, y = vendor_posts[i]
        else:
            row, col = divmod(i - 6, 12)
            x = -26.0 + col * 4.4
            y = 10.5 + row * 0.28
        ob = new_anchored_obj(f"Zed.{i + 1:04d}", lib, (x, y, 0.0))
        crowd.append(ob)
    chase = []
    for i in range(12):
        if i in (2, 5, 8):   # the RB slots (the loader's indices)
            x, y = (30.5 + (i // 3) * 4.0), 9.0   # outboard east
        else:
            x, y = (6.5 - i * 0.8), 7.5
        ob = new_anchored_obj(f"Zed.ChaseP{i + 1:02d}", lib, (x, y, 0.0))
        chase.append(ob)
    return {"zombies": {"crowd": crowd, "chase": chase}}


def _cameras(scene):
    cams = {}
    for row in CAMS_V3:
        name, loc0, loc1, lens, aim, _, _shake = row
        cam = bpy.data.cameras.new(name)
        cam.lens = lens
        ob = bpy.data.objects.new(name, cam)
        ob.location = loc0
        scene.collection.objects.link(ob)
        cams[name] = {"ob": ob, "loc0": loc0, "loc1": loc1, "aim": aim}
    for name, c in cams.items():
        aim = bpy.data.objects.new(f"Aim.{name}", None)
        aim.location = c["aim"]
        scene.collection.objects.link(aim)
        c["ob"].constraints.new("TRACK_TO")
        c["ob"].constraints[0].target = aim
        c["ob"].constraints[0].track_axis = "TRACK_NEGATIVE_Z"
        c["ob"].constraints[0].up_axis = "UP_Y"
    return cams


def _markers(scene, cams):
    out = []
    for sid, f0, f1, _intent in SHOTS_V3:
        m = scene.timeline_markers.new(f"SHOT_{sid}", frame=f0)
        m.camera = cams[f"CAM_{sid}"]["ob"]
        out.append(m)
    return out


def _shot_table(shots, cams):
    by_name = {c[0]: c for c in cams}
    out = []
    for sid, f0, f1, _intent in shots:
        nm = f"CAM_{sid}"
        c = by_name.get(nm)
        if c is None:
            raise KeyError(f"shot {sid}: no {nm} row in the cam table")
        _name, loc0, loc1, lens, aim, pj, _shake = c
        out.append({"shot_id": sid, "f0": int(f0), "f1": int(f1),
                    "loc0": tuple(float(v) for v in loc0),
                    "loc1": tuple(float(v) for v in loc1),
                    "lens_mm": float(lens),
                    "aim": None if pj else tuple(float(v) for v in aim),
                    "parent_jeep": bool(pj)})
    return out


def _rain(scene):
    """The rain: one shared drop mesh, 550 instanced drops in a
    64x34x10 volume, TWO root groups offset half-cycle (the wrap law:
    each root falls 10m over 36f linear and snaps back -- the two
    roots alternate so the sky never empties). The drop material's
    alpha carries the INTENSITY ARC keys (previz dressing; the GLB
    export drops it honestly)."""
    from tdawn_actors import make_material
    mat = make_material("TS.RainDrop", (0.55, 0.62, 0.72), 0.15)
    # the arc keys ride the material alpha via a value node the
    # make_material Principled exposes (previz-only; export drops it)
    drops_root = []
    mesh = bpy.data.meshes.new("TS.RainMesh")
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bm.to_mesh(mesh)
    bm.free()
    mesh.materials.append(mat)
    n_total = 550
    for gi in range(2):
        root = bpy.data.objects.new(f"TS.RainRoot.{gi}", None)
        scene.collection.objects.link(root)
        for i in range(n_total // 2):
            d = bpy.data.objects.new(f"TS.Drop.{gi}.{i:03d}", mesh)
            d.location = (-32.0 + (i * 37 % 64) + gi * 0.9,
                          -17.0 + (i * 53 % 34),
                          -5.0 + (i * 89 % 100) / 10.0)
            d.scale = (0.012, 0.012, 0.30)
            d.parent = root
            scene.collection.objects.link(d)
        drops_root.append(root)
    # each root: fall 10m over 36f, snap back -- offset half-cycle
    for gi, root in enumerate(drops_root):
        f0 = 1 + gi * 18
        root.location = (0.0, 0.0, 0.0)
        root.keyframe_insert(data_path="location", frame=f0)
        root.location = (0.0, 0.0, -10.0)
        root.keyframe_insert(data_path="location", frame=f0 + 35)
        root.location = (0.0, 0.0, 0.0)
        root.keyframe_insert(data_path="location", frame=f0 + 36)
        for fc in _iter_fcurves(root.animation_data.action):
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"
    return {"roots": drops_root, "mat": mat, "n": n_total}


def _neon_title(scene):
    """The neon SQUALL on the sign band (the 4-e F14 carrier): a FONT
    mesh on the band's north face, warm-neon emission, export-safe
    SCALE keys: dark until f1009 (the flash), ignite on the decay,
    two flickers, steady."""
    from tdawn_actors import make_material
    size = 0.42
    tx, ty, tz = 0.0, 6.05, 3.2
    mat = make_material(
        "TS.NeonTitle", (0.06, 0.05, 0.05), 0.4,
        emission_color=(1.0, 0.45, 0.15), emission_strength=5.5)
    crv = bpy.data.curves.new("TS.NeonTitle", type="FONT")
    crv.body = "SQUALL"
    crv.size = size
    crv.align_x = "CENTER"
    crv.align_y = "CENTER"
    crv.extrude = 0.015
    ob = bpy.data.objects.new("TS.NeonTitle", crv)
    ob.location = (tx, ty, tz)
    ob.rotation_euler = (math.pi / 2, 0.0, 0.0)   # face north
    scene.collection.objects.link(ob)
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.convert(target="MESH")
    ob.data.materials.append(mat)
    _kf(ob, 1, scale=(0.001, 0.001, 0.001))
    _kf(ob, 1009, scale=(0.001, 0.001, 0.001))
    _kf(ob, 1011, scale=(1.0, 1.0, 1.0))     # ignite on the decay
    _kf(ob, 1016, scale=(0.001, 0.001, 0.001))   # flicker out
    _kf(ob, 1021, scale=(1.0, 1.0, 1.0))     # flicker in
    _kf(ob, 1080, scale=(1.0, 1.0, 1.0))
    _bezier(ob)
    return ob


def _storm_sky(scene):
    """The ladder-pinned storm sky + the thunder flashes. The world's
    Background strength keys the flashes: base 0.15 -> spike 2.6 with a
    2f/4f decay at each thunder frame (the title flash the biggest)."""
    world = scene.world
    if world is None:
        world = bpy.data.worlds.new("TSQ.StormSky")
        scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    bg = nt.nodes.get("Background")
    if not bg:
        bg = nt.nodes.new("ShaderNodeBackground")
        out = next(n for n in nt.nodes if n.type == "OUTPUT_WORLD")
        nt.links.new(bg.outputs[0], out.inputs[0])
    bg.inputs[0].default_value = (*TS_SKY_COLOR, 1.0)
    bg.inputs[1].default_value = TS_SKY_STRENGTH
    sun = bpy.data.lights.get("TSQ.StormSun") or \
        bpy.data.lights.new("TSQ.StormSun", "SUN")
    sun.energy = TS_SUN_ENERGY
    sun.color = TS_SUN_COLOR
    sun.angle = math.radians(4.0)
    ob = bpy.data.objects.get("TSQ.StormSun")
    if not ob:
        ob = bpy.data.objects.new("TSQ.StormSun", sun)
        scene.collection.objects.link(ob)
    ob.data = sun
    ob.rotation_euler = (math.radians(90.0 - TS_SUN_ELEV), 0.0,
                         math.radians(-38.0))
    # the thunder flashes on the world strength
    bg.inputs[1].default_value = TS_SKY_STRENGTH
    bg.inputs[1].keyframe_insert(data_path="default_value", frame=1)
    for i, f in enumerate(TS_THUNDER):
        peak = 2.6 if f == 1009 else 1.8
        bg.inputs[1].default_value = TS_SKY_STRENGTH
        bg.inputs[1].keyframe_insert(data_path="default_value",
                                     frame=f - 1)
        bg.inputs[1].default_value = peak
        bg.inputs[1].keyframe_insert(data_path="default_value",
                                     frame=f)
        bg.inputs[1].default_value = peak * 0.35
        bg.inputs[1].keyframe_insert(data_path="default_value",
                                     frame=f + 2)
        bg.inputs[1].default_value = TS_SKY_STRENGTH
        bg.inputs[1].keyframe_insert(data_path="default_value",
                                     frame=f + 5)
    bg.inputs[1].default_value = TS_SKY_STRENGTH
    return world


def build_scene():
    scene = bpy.context.scene
    scene.render.fps = FPS
    for o in list(bpy.data.objects):
        if o.name.startswith(("Cube", "Camera", "Light", "Lamp")):
            bpy.data.objects.remove(o, do_unlink=True)
    import tsquall_world as W
    parts = W.build_world(scene)
    heroes = _heroes(scene)
    chars = _crowd_anchors(scene)
    cams = _cameras(scene)
    _markers(scene, cams)
    rain = _rain(scene)
    neon = _neon_title(scene)
    _storm_sky(scene)
    bpy.context.view_layer.update()
    return {"scene": scene, "parts": parts, "heroes": heroes,
            "cams": cams, "chars": chars, "rain": rain, "neon": neon}


def animate(ctx, start_frame=1, n_frames=None, with_crowd=None):
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = total_frames
    _kf_bystander(ctx)
    _kf_crane(ctx)
    crowd_cache = _crowd_cache_path()
    if crowd_cache and with_crowd is not False:
        _crowd_kit_branch(ctx, crowd_cache)
    else:
        print("[tsquall] no crowd (cache absent or --skip-crowd) -- "
              "pre-bake look (anchors at authored grid)")
    bpy.context.view_layer.update()
    return None


def _kf_bystander(ctx):
    """The witness: stands under the eave; the fall at f372 turns him;
    f470 the crouch (a keyed z drop + turn); holds to the end."""
    bs = ctx["heroes"]["Bystander"]
    _kf(bs, 1, loc=(10.6, -1.2), rot_z=math.radians(125))
    _kf(bs, 371, loc=(10.6, -1.2), rot_z=math.radians(125))
    _kf(bs, 385, loc=(10.6, -1.0), rot_z=math.radians(95))   # turns to it
    _kf(bs, 469, loc=(10.6, -1.0), rot_z=math.radians(95))
    _kf(bs, 470, loc=(10.6, -0.6), rot_z=math.radians(80))   # the crouch
    _kf(bs, 1080, loc=(10.6, -0.6), rot_z=math.radians(80))
    _bezier(bs)


def _kf_crane(ctx):
    """S11 keys its rise (f913-1008); S12 continues loc0->loc1 by
    f1035 (the descend + push north to the band)."""
    c11 = ctx["cams"]["CAM_S11"]["ob"]
    c11.location = ctx["cams"]["CAM_S11"]["loc0"]
    c11.keyframe_insert(data_path="location", frame=913)
    c11.location = ctx["cams"]["CAM_S11"]["loc1"]
    c11.keyframe_insert(data_path="location", frame=1008)
    c12 = ctx["cams"]["CAM_S12"]["ob"]
    c12.location = ctx["cams"]["CAM_S12"]["loc0"]
    c12.keyframe_insert(data_path="location", frame=1009)
    c12.location = ctx["cams"]["CAM_S12"]["loc1"]
    c12.keyframe_insert(data_path="location", frame=1035)
    for c in (c11, c12):
        _bezier(c)
    a11 = bpy.data.objects.get("Aim.CAM_S11")
    a11.location = (2.0, 4.0, 0.8)
    a11.keyframe_insert(data_path="location", frame=913)
    a11.location = (2.0, 4.0, 0.6)
    a11.keyframe_insert(data_path="location", frame=1008)
    a12 = bpy.data.objects.get("Aim.CAM_S12")
    a12.location = (2.0, 4.0, 0.6)
    a12.keyframe_insert(data_path="location", frame=1009)
    a12.location = (0.0, 6.2, 3.2)
    a12.keyframe_insert(data_path="location", frame=1035)
    a12.location = (0.0, 6.2, 3.2)
    a12.keyframe_insert(data_path="location", frame=1080)
    _bezier(a11)
    _bezier(a12)


def _crowd_cache_path():
    env = os.environ.get("CROWD_CACHE_DIR", "/tmp/crowdcache_tsquall")
    p = os.path.join(env, "cache_ctx.json")
    return p if os.path.exists(p) else None


def _crowd_kit_branch(ctx, cache_path):
    """The kit-mode crowd path -- the F-TS5 pin override carries 135."""
    print(f"[tsquall] kit cache: {cache_path}")
    ctx["crowd_shots"] = _shot_table(SHOTS_V3, CAMS_V3)
    ctx["crowd_tier_pins"] = CROWD_TIER_PINS
    import crowd_kit as _CK
    _CK.loader.load_kit_cache(ctx, expected_agents=135)
    # the cast list rides the ctx json (the loader surfaces only its
    # own keys -- the film-specific block is read here, 4-f #6: extra
    # keys are inert to the loader)
    with open(cache_path) as f:
        ctx["cast"] = json.load(f).get("cast", {})
    import crowd_v6 as CV6
    CV6.bake_tier2(ctx)
    _crowd_palette(ctx)
    return ctx["crowd_cache"]


def _crowd_palette(ctx):
    """The storm-dusk market palette: the crowd in four muted
    wet-weather tones; the VENDORS (ordinals 0-5, the stall posts) in
    warm apron tones; the QUEUE (chase) in a cool blue-grey pair; the
    FALLER keyed amber (the cast list from the bake driver)."""
    from tdawn_actors import make_material
    CROWD_TONES = [(0.30, 0.32, 0.36), (0.22, 0.26, 0.24),
                   (0.36, 0.28, 0.22), (0.26, 0.22, 0.28)]
    QUEUE_TONES = [(0.24, 0.30, 0.40), (0.18, 0.23, 0.32)]
    VENDOR_TONES = [(0.42, 0.30, 0.16), (0.36, 0.24, 0.12)]
    FALLER_TONE = (0.78, 0.48, 0.14)   # amber: the one the eye tracks
    chars = ctx["chars"]["zombies"]
    cast = ctx.get("cast", {})
    faller = cast.get("faller")
    n = {"c": 0, "q": 0, "v": 0}
    bpy.context.scene.frame_set(1)
    for ob in chars["crowd"]:
        if ob.data.users > 1:
            ob.data = ob.data.copy()
        ob.data.materials.clear()
        if faller and ob.name == faller:
            ob.data.materials.append(make_material(
                "CA.Comm.TS.Faller", FALLER_TONE))
        elif ob.name.startswith("Zed.000") and n["v"] < 6:
            ob.data.materials.append(make_material(
                f"CA.Comm.TS.Vendor.{n['v'] % 2}",
                VENDOR_TONES[n["v"] % 2]))
            n["v"] += 1
        else:
            ob.data.materials.append(make_material(
                f"CA.Comm.TS.Crowd.{n['c'] % 4}",
                CROWD_TONES[n['c'] % 4]))
            n["c"] += 1
    for ob in chars["chase"]:
        if ob.data.users > 1:
            ob.data = ob.data.copy()
        ob.data.materials.clear()
        ob.data.materials.append(make_material(
            f"CA.Comm.TS.Queue.{n['q'] % 2}", QUEUE_TONES[n['q'] % 2]))
        n["q"] += 1
    print(f"[tsquall] crowd palette: {n['c']} crowd / {n['q']} queue / "
          f"{n['v']} vendors; faller={faller}")


def emit_sfx_events(ctx, out_dir):
    events = list(json.loads(json.dumps(
        __import__("tsquall_contract").SFX_EVENTS)))
    cast = ctx.get("cast") or {}
    for b in cast.get("queue_bell_events", []):
        events.append({"name": b["name"], "frame": int(b["frame"])})
    events.sort(key=lambda e: e["frame"])
    with open(os.path.join(out_dir, "sfx_events.json"), "w") as f:
        json.dump({"fps": FPS, "meta": {"scene": "scene_squall"},
                   "events": events}, f, indent=1)
    return events


def _script_args():
    argv = sys.argv
    return argv[argv.index("--") + 1:] if "--" in argv else []


def _set_engine(scene, engine, samples):
    name = "BLENDER_EEVEE" if engine.startswith("eevee") else \
        "BLENDER_WORKBENCH"
    scene.render.engine = name
    scene.eevee.use_raytracing = True   # the 5.2 SSR knob (wet ground)
    if hasattr(scene.eevee, "taa_render_samples"):
        scene.eevee.taa_render_samples = samples
    scene.view_settings.exposure = ts_exposure


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="output/tsquall")
    p.add_argument("--engine", default="workbench")
    p.add_argument("--w", type=int, default=640)
    p.add_argument("--h", type=int, default=360)
    p.add_argument("--still", type=int, default=None)
    p.add_argument("--samples", type=int, default=32)
    p.add_argument("--skip-crowd", action="store_true")
    args = p.parse_args(_script_args())

    scene = bpy.context.scene
    ctx = build_scene()
    animate(ctx, with_crowd=not args.skip_crowd)
    out = args.output
    os.makedirs(out, exist_ok=True)
    if args.still:
        scene.frame_set(args.still)
        _set_engine(scene, args.engine, args.samples)
        scene.render.resolution_x = args.w
        scene.render.resolution_y = args.h
        scene.render.filepath = os.path.join(
            out, f"still_{args.still:05d}.png")
        bpy.ops.render.render(write_still=True)
    else:
        print("[tsquall] dry-run OK")
    bpy.context.view_layer.update()


if __name__ == "__main__":
    main()
