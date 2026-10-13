"""scene_last_ferry.py -- LAST FERRY (tferry_1): the night-pier
converge film. D-TF1 REV-2; the scene module of the tdawn shape
(mapped vocabulary UPPERCASE only; internal wiring lowercase).

Session-14 slice: world + cameras + heroes + title + emission keys;
the crowd branch auto-detects the bake cache (absent -> pre-bake
looks work). The bake driver (tferry_bake.py) is the next session's
first item per HANDOFF.
"""
import math
import os
import sys
from pathlib import Path

import bpy

_here = str(Path(__file__).resolve().parent)
if _here not in sys.path:
    sys.path.insert(0, _here)

# the escape-previz scripts (crowd_kit plugin + crowd_v6 shared
# loader) -- sibling resolution first, the tdawn hardcode retired
# (the F-TF1 friction family; TPREVIZ_SCRIPTS still wins)
_lab = Path(__file__).resolve().parent.parent.parent
_sib = _lab / "blender-escape-previz" / "scripts"
_previz_scripts = os.environ.get(
    "TPREVIZ_SCRIPTS",
    str(_sib) if _sib.is_dir() else "/home/z/work/blender-escape-previz/scripts")
if _previz_scripts not in sys.path:
    sys.path.insert(0, _previz_scripts)

import tferry_world as W

FPS = 24
total_frames = 1080

SYNOPSIS = (
    "Night at a ferry pier in the rain. The neon flips to BOARDING and "
    "the crowd converges on the last gangway out. The Deckhand (amber) "
    "holds the two-meter throat; the Latecomer (crimson) sprints the "
    "pier edge to make the crossing. The ferry pulls; the pier empties; "
    "the lit windows recede. Nobody flees: the crowd is the tide, and "
    "the boat is the moon.")

SHOTS_V3 = [
    ("S1",  1,    84,  "aerial night establish: the pier strip, thin drift south"),
    ("S2",  85,   168, "the kiosk board flips to BOARDING (the call)"),
    ("S3",  169,  264, "the surge ignites: the far bands pour south"),
    ("S4",  265,  348, "the Latecomer enters at the pier head, breaks into a run"),
    ("S5",  349,  444, "lateral: the Latecomer cuts along the east rail line"),
    ("S6",  445,  528, "the Deckhand holds the throat; the crowd piles at the choke"),
    ("S7",  529,  624, "low tracker: the Latecomer slips the bollard line"),
    ("S8",  625,  720, "the Deckhand sees the Latecomer; holds the gap open"),
    ("S9",  721,  816, "the beat: through the maintenance gate, the crew wave"),
    ("S10", 817,  912, "the throat sealed by the Deckhand's arm; the pier quiets"),
    ("S11", 913,  1008, "the crane rises: the empty pier, the windows begin to move"),
    ("S12", 1009, 1080, "title frame: LAST FERRY over the receding windows"),
]

CAMS_V3 = [
    # S1 aerial moved SW+higher so the FERRY establishes (the pier strip
    # alone read as "a queue somewhere")
    ("CAM_S1",  (-9.0, -9.0, 15.0), (-9.0, -9.0, 15.0), 26,
     (0.5, 20.0, 0.0), False, 0.0),
    # S2: the BOARDING sign was on the kiosk's SOUTH face (dead side --
    # the blank north slab filled the frame); sign flipped north (the
    # arriving crowd's side) + camera north looking south at it
    ("CAM_S2",  (0.9, 5.6, 2.2), (0.9, 5.6, 2.2), 40,
     (3.05, 2.75, 2.05), False, 0.0),
    ("CAM_S3",  (-2.0, 30.0, 5.0), (-2.0, 30.0, 5.0), 30,
     (0.2, 10.0, 1.0), False, 0.02),
    # S4: tighter on the Latecomer's entry (he was buried mid-crowd)
    ("CAM_S4",  (4.0, 36.0, 2.4), (4.0, 36.0, 2.4), 45,
     (4.9, 27.5, 1.2), False, 0.015),
    ("CAM_S5",  (2.2, 24.0, 1.9), (2.2, 24.0, 1.9), 30,
     (4.8, 16.0, 1.1), False, 0.025),
    # S6: the camera stood INSIDE the queue aiming at the EMPTY throat;
    # pulled west+north so the Deckhand AND the pile read together
    ("CAM_S6",  (-5.2, 7.0, 2.6), (-5.2, 7.0, 2.6), 40,
     (0.0, 2.5, 1.2), False, 0.018),
    # S7: aim was 4m north of the Latecomer's hold pose (f580 he holds
    # (4.8, 8.0))
    ("CAM_S7",  (-4.6, 14.0, 1.5), (-4.6, 14.0, 1.5), 35,
     (4.8, 9.0, 1.1), False, 0.03),
    # S8: the pairing shot -- Deckhand (0.3,0.7) + Latecomer (4.8,8)
    # in ONE frame from the west deck edge (was: empty throat)
    ("CAM_S8",  (-3.4, 0.6, 2.0), (-3.4, 0.6, 2.0), 35,
     (3.2, 5.2, 1.2), False, 0.012),
    # S9: aim past the subject (the maint gate) -- recentered on the
    # gate + his crossing path
    ("CAM_S9",  (2.6, 10.8, 2.3), (2.6, 10.8, 2.3), 32,
     (5.4, 7.6, 1.1), False, 0.0),
    ("CAM_S10", (-2.0, 3.4, 2.6), (-2.0, 3.4, 2.6), 26,
     (0.4, -0.6, 1.4), False, 0.0),
    # the CRANE (S11/S12): loc AND aim keyed -- over the outboard
    # margin/water (REV-2 F8); rises 3.2 -> 11.6 while drifting south
    ("CAM_S11", (-8.6, 18.0, 3.2), (-9.2, 10.0, 11.0), 30,
     (0.5, 10.0, 0.5), False, 0.0),
    ("CAM_S12", (-9.2, 10.0, 11.0), (-8.8, 8.0, 11.6), 35,
     (0.0, 1.0, 1.2), False, 0.0),
]

CAST = {
    "Deckhand": {"root": "Deckhand.Root", "material": "CA.Body.Deckhand"},
    "Latecomer": {"root": "Latecomer.Root", "material": "CA.Body.Latecomer"},
}

BEATS = [
    ("calm",       "S1",  1),
    ("boarding",   "S2",  85),
    ("surge",      "S3",  169),
    ("latecomer",  "S4",  265),
    ("the_line",   "S5",  349),
    ("the_choke",  "S6",  445),
    ("bollards",   "S7",  529),
    ("seen",       "S8",  625),
    ("the_gap",    "S9",  721),
    ("sealed",     "S10", 817),
    ("rising",     "S11", 913),
    ("title",      "S12", 1009),
]

CROWD_TIER_PINS = []       # kit mode: single tier, no director pins

_title_f0 = 1009           # the title sting


def frame_at(t):
    return int(round(t * FPS)) + 1


def _heroes(scene):
    """The authored heroes: Deckhand (amber, holds the throat) +
    Latecomer (crimson, the edge run). Capsule heroes via the tdawn
    actor builders (the shared mesh contract: CA.Body.<name>)."""
    from tdawn_actors import build_commuter_mesh, make_material
    HERO_COLORS = {
        "Deckhand": (0.85, 0.42, 0.05),
        "Latecomer": (0.62, 0.07, 0.10),   # crimson -- tdawn's Runner
    }                                       # was teal; different film,
    scene["HERO_COLORS"] = HERO_COLORS      # different callout
    mesh = build_commuter_mesh("TF.CommuterMesh")
    # PARK the source lib object outside every frustum (the tdawn law:
    # the builder leaves a scene-linked object at the origin — the
    # unparked source stood in the throat as a WHITE figure at f486)
    mesh.location = (0.0, 45.0, -2.5)
    mesh.hide_render = True
    heroes = {}
    for name, loc, yaw in (("Deckhand", (0.30, 0.70, 0.0), 0.0),
                           ("Latecomer", (4.90, 34.0, 0.0), math.pi)):
        ob = bpy.data.objects.new(f"{name}.Root", mesh.data)
        ob.location = loc
        ob.rotation_euler = (0.0, 0.0, yaw)
        scene.collection.objects.link(ob)
        ob.data = ob.data.copy()            # own material slots
        ob.data.materials.clear()
        # the exporter's identity-color registry reads CA.Body.<name>
        ob.data.materials.append(make_material(
            f"CA.Body.{name}", HERO_COLORS[name], rough=0.5))
        heroes[name] = ob
    return heroes


def _title_card(scene):
    """LAST FERRY over the receding windows -- the export-safe pattern
    (scale keys; converted mesh; the tdawn_2 'constantly visible' law
    from birth)."""
    from tdawn_actors import make_material
    size = 0.44                 # 11.6m crane distance: 0.30 read small
    tx, ty, tz = 0.0, 2.2, 3.0
    mat = make_material("TF.TitleCard", (1.0, 0.88, 0.70), 0.4)
    crv = bpy.data.curves.new("TF.TitleCard", type="FONT")
    crv.body = "LAST FERRY"
    crv.size = size
    crv.align_x = "CENTER"
    crv.align_y = "CENTER"
    crv.extrude = 0.02
    ob = bpy.data.objects.new("TF.TitleCard", crv)
    ob.location = (tx, ty, tz)
    scene.collection.objects.link(ob)
    # face the S12 crane END pose (-8.8, 8.0, 11.6) looking at (0,2.5,.5)
    cx, cy, cz = -8.8, 8.0, 11.6
    nx, ny = cx - tx, cy - ty
    ob.rotation_euler = (math.atan2(cz - tz, math.hypot(nx, ny)),
                         0.0, math.atan2(ny, nx) + math.pi / 2)
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.convert(target="MESH")
    ob.data.materials.append(mat)
    ob.scale = (0.001, 0.001, 0.001)
    ob.keyframe_insert(data_path="scale", frame=1)
    ob.keyframe_insert(data_path="scale", frame=_title_f0 - 1)
    ob.scale = (1.0, 1.0, 1.0)
    ob.keyframe_insert(data_path="scale", frame=_title_f0)
    ob.keyframe_insert(data_path="scale", frame=1080)
    return ob


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
    # the Aim empties (gate 2: every camera needs Aim.<CAM>, TRACK_TO)
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
    """One timeline marker per shot at f0, camera-bound (the exporter
    hard-fails without them)."""
    out = []
    for sid, f0, f1, _intent in SHOTS_V3:
        m = scene.timeline_markers.new(f"SHOT_{sid}", frame=f0)
        m.camera = cams[f"CAM_{sid}"]["ob"]
        out.append(m)
    return out


def _iter_fcurves(action):
    """The 4.x/5.x fcurve iterator (the tdawn-vetted helper; 5.2
    slotted actions carry fcurves in channelbags, not on the action)."""
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


def _bezier(obj):
    """BEZIER + AUTO easing on all of obj's fcurves (4.x + 5.x)."""
    if obj.animation_data is None or obj.animation_data.action is None:
        return
    for fc in _iter_fcurves(obj.animation_data.action):
        for kp in fc.keyframe_points:
            kp.interpolation = "BEZIER"
            kp.easing = "AUTO"


def _kf(obj, f, loc=None, rot_z=None):
    if loc is not None:
        obj.location = (loc[0], loc[1],
                        loc[2] if len(loc) > 2 else obj.location.z)
        obj.keyframe_insert(data_path="location", frame=f)
    if rot_z is not None:
        obj.rotation_euler = (0.0, 0.0, rot_z)
        obj.keyframe_insert(data_path="rotation_euler", index=2, frame=f)


def _kf_heroes(ctx):
    """The authored paths. Deckhand: holds (0.30,0.70) facing the
    crowd; steps aside for the Latecomer at S9-S10. Latecomer: pier
    head (4.9,34) f265 -> the east rail line (4.8,8) f444 -> holds
    (idle sway) -> the maintenance gate f721-760 -> the choke approach
    -> through the throat -> the ferry ramp by f900."""
    dh = ctx["heroes"]["Deckhand"]
    lc = ctx["heroes"]["Latecomer"]
    _kf(dh, 1, loc=(0.30, 0.70))
    _kf(dh, 760, loc=(0.30, 0.70), rot_z=0.0)
    _kf(dh, 800, loc=(-0.45, 0.85), rot_z=0.5)    # steps aside
    _kf(dh, 1080, loc=(-0.45, 0.85), rot_z=0.5)
    for ob in (dh, lc):
        _bezier(ob)
    run = [(265, (4.90, 34.0)), (348, (4.85, 26.0)), (444, (4.80, 8.0)),
           (700, (4.80, 8.0)), (760, (3.40, 6.2)), (816, (0.60, 1.4)),
           (880, (0.20, -1.1)), (900, (0.05, -2.2)), (1080, (0.05, -2.2))]
    for f, loc in run:
        _kf(lc, f, loc=loc)
    _bezier(lc)


def _em_keys(mat, keys):
    """Emission-strength keys (the BOARDING flip; the window recede).
    Values stay in the measured bands (warm <= 0.95; neon 0.95-3.9)."""
    track = mat.node_tree.nodes
    bsdf = next(n for n in track if n.type == "BSDF_PRINCIPLED")
    for f, v in keys:
        bsdf.inputs["Emission Strength"].default_value = float(v)
        bsdf.inputs["Emission Strength"].keyframe_insert("default_value",
                                                         frame=f)


def _kf_set_pieces(ctx):
    """The BOARDING flip (the kiosk sign's magenta neon ignites at the
    call) + the S11 window recede (strength keyed DOWN)."""
    mats = ctx["parts"]["mats"]
    _em_keys(mats["neon_mag"], [(1, 0.25), (85, 1.9), (1080, 1.9)])
    _em_keys(mats["neon_cyan"], [(1, 0.35), (85, 1.9), (1080, 1.9)])
    _em_keys(mats["ferry_win"], [(1, 0.70), (912, 0.70), (1008, 0.45),
                                 (1080, 0.45)])
    # the crane: loc0 -> loc1 with ease (S11 f913-1008; S12 continues
    # to its end pose by f1030)
    c11 = ctx["cams"]["CAM_S11"]["ob"]
    c11.location = ctx["cams"]["CAM_S11"]["loc0"]
    c11.keyframe_insert(data_path="location", frame=913)
    c11.location = ctx["cams"]["CAM_S11"]["loc1"]
    c11.keyframe_insert(data_path="location", frame=1008)
    c12 = ctx["cams"]["CAM_S12"]["ob"]
    c12.location = ctx["cams"]["CAM_S12"]["loc0"]
    c12.keyframe_insert(data_path="location", frame=1009)
    c12.location = ctx["cams"]["CAM_S12"]["loc1"]
    c12.keyframe_insert(data_path="location", frame=1030)
    for c in (c11, c12):
        _bezier(c)
    # the Aim.<CAM_S11> empty drifts down+SOUTH with the rise (the
    # look-at keys: (0.5,10,0.5) -> (0,-1.0,0.5) -- the S11 intent is
    # 'the windows begin to move': the FERRY must own the frame end;
    # the deck queue falls out of the tight frustum)
    a11 = bpy.data.objects.get("Aim.CAM_S11")
    a11.location = (0.5, 10.0, 0.5)
    a11.keyframe_insert(data_path="location", frame=913)
    a11.location = (0.0, -1.0, 0.5)
    a11.keyframe_insert(data_path="location", frame=1008)


def build_scene():
    """Build the pier set + heroes + cameras + markers. Ends with the
    F-TD5 view-layer sync (cheap insurance even with the kit fix)."""
    scene = bpy.context.scene
    for o in list(bpy.data.objects):
        if o.name.startswith(("Cube", "Camera", "Light", "Lamp")):
            bpy.data.objects.remove(o, do_unlink=True)
    parts = W.build_world(scene)
    heroes = _heroes(scene)
    chars = _crowd_anchors(scene)
    cams = _cameras(scene)
    _markers(scene, cams)
    title = _title_card(scene)
    bpy.context.view_layer.update()
    return {"parts": parts, "heroes": heroes, "cams": cams,
            "chars": chars, "title": title}


def animate(ctx, start_frame=1, n_frames=None, with_crowd=None):
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = total_frames
    _kf_heroes(ctx)
    _kf_set_pieces(ctx)
    crowd_cache = _crowd_cache_path()
    if crowd_cache and with_crowd is not False:
        _crowd_kit_branch(ctx, crowd_cache)
    else:
        print("[tferry] no crowd (cache absent or --skip-crowd) -- "
              "pre-bake look (anchors at authored grid)")
    bpy.context.view_layer.update()
    return None


def _crowd_cache_path():
    env = os.environ.get("CROWD_CACHE_DIR", "/tmp/crowdcache_tferry")
    p = os.path.join(env, "cache_ctx.json")
    return p if os.path.exists(p) else None


def _crowd_anchors(scene):
    """The 132 placeholder anchors the kit-mode loader's rename law
    expects: 120 crowd Zed.NNNN (named to the cache-name law up front)
    + 12 chase Zed.ChasePNN (3 of them are RB slots the loader renames
    to Zed.RB.ChaseNN; 9 get positionally renamed Zed.Chase01..09 and
    pair with the sim's crew tail). loader.py:530-560 is the law.

    Pre-bake positions: the zone rows (the crowd grid) and the pier
    head (the crew answering the call). bake2 overwrites all 129
    non-RB anchors with keyed TRS; the 3 RB placeholders stay where
    they stand (outboard pier head -- dressing-plausible statics)."""
    from tdawn_actors import (build_commuter_mesh, new_anchored_obj,
                              commuter_material)
    lib = build_commuter_mesh("TF.CommuteLib",
                              mat_body=commuter_material(0))
    # PARK the library mesh outside every frustum + hide_render (the
    # tdawn law: the unparked source stood in-frame as a WHITE figure)
    lib.location = (0.0, 45.0, -2.5)
    lib.hide_render = True
    crowd = []
    # 120 anchors in the zone-row shape (24-34 / 12-20 / 6-10), a
    # 12-wide grid reading as the pre-call drift
    for i in range(120):
        row = i // 12
        col = i % 12
        y = 32.0 - row * 2.1 if row < 5 else 20.0 - (row - 5) * 2.1
        if row >= 10:
            y = 10.0 - (row - 10) * 1.2
        x = ((col - 5.5) * 0.95)
        crowd.append(new_anchored_obj(
            f"Zed.{i + 1:04d}", lib, (x, y, 0.0),
            yaw=math.pi))       # facing south, toward the throat
    chase = []
    for i in range(12):
        chase.append(new_anchored_obj(
            f"Zed.ChaseP{i + 1:02d}", lib,
            (((i % 6) - 2.5) * 1.3, 30.0 + (i // 6) * 2.0, 0.0),
            yaw=math.pi))
    return {"zombies": {"crowd": crowd, "chase": chase}}


def _shot_table(shots, cams):
    """The ShotCam rows the tiering/stash contract carries (the tdawn
    shape; kept local so the scene module stays independent of the v6
    import order)."""
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


def _crowd_kit_branch(ctx, cache_path):
    """The kit-mode crowd path (the tdawn shape, mirrors
    scene_escape_v5.py:1256-1274): loader honesty asserts + anchor
    rename law + bake2 pairing + the tferry palette.

    F-TF2 (the slice's gap): this branch originally hand-rolled a
    json read of a chars shape that does not exist and skipped the
    anchor assembly + bake_tier2 entirely -- the scene module was
    'export-complete' on paper only. The kit loader owns this chain;
    scenes must NEVER hand-roll it."""
    print(f"[tferry] kit cache: {cache_path}")
    ctx["crowd_shots"] = _shot_table(SHOTS_V3, CAMS_V3)
    ctx["crowd_tier_pins"] = CROWD_TIER_PINS
    import crowd_kit as _CK
    _CK.loader.load_kit_cache(ctx)
    import crowd_v6 as CV6
    CV6.bake_tier2(ctx)
    _crowd_palette(ctx)
    return ctx["crowd_cache"]


def _crowd_palette(ctx):
    """Per-agent palette assignment (the user's color-discipline law
    from birth here): the population is a NEUTRAL register -- value
    variance only; identity color is for call-outs. The crew tail
    shares ONE dark-blue tone (group identity, previz semantics).

    bake2 gives every sim agent a private mesh copy (users==1); the 3
    RB placeholders keep the shared lib mesh (users>1 -> copy first).
    Assigning earlier would mutate the SHARED library datablock (the
    tdawn_1 clone-army lesson)."""
    from tdawn_actors import make_material
    NEUTRALS = [(0.13, 0.13, 0.14), (0.22, 0.21, 0.20),
                (0.16, 0.17, 0.19), (0.27, 0.25, 0.22),
                (0.10, 0.10, 0.11), (0.20, 0.19, 0.18)]
    CREW = (0.09, 0.11, 0.20)   # the crew: ONE dark-blue callout tone
    chars = ctx["chars"]["zombies"]
    n = 0
    for i, ob in enumerate(chars["crowd"]):
        if ob.data.users > 1:
            ob.data = ob.data.copy()
        ob.data.materials.clear()
        ob.data.materials.append(make_material(
            f"CA.Commute.TF0.{i % len(NEUTRALS)}",
            NEUTRALS[i % len(NEUTRALS)]))
        n += 1
    for i, ob in enumerate(chars["chase"]):
        if ob.data.users > 1:
            ob.data = ob.data.copy()
        ob.data.materials.clear()
        ob.data.materials.append(make_material(
            f"CA.Commute.TF1.{i % len(NEUTRALS)}", CREW))
        n += 1
    print(f"[tferry] crowd palette: {n} anchors "
          f"(neutral crowd + dark-blue crew)")


def emit_sfx_events(ctx, out_dir):
    import json
    events = [
        {"id": "chime", "frame": 85, "label": "boarding chime"},
        {"id": "clang", "frame": 721, "label": "gangway clang"},
        {"id": "horn", "frame": 913, "label": "departure horn"},
    ]
    with open(os.path.join(out_dir, "sfx_events.json"), "w") as f:
        json.dump({"fps": FPS, "meta": {"scene": "scene_last_ferry"},
                   "events": events}, f, indent=1)


def _script_args():
    argv = sys.argv
    return argv[argv.index("--") + 1:] if "--" in argv else []


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="output/tferry")
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
    out = os.path.join(args.output, "stillwork")
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
        print("[tferry] dry-run OK")
    bpy.context.view_layer.update()


def _set_engine(scene, engine, samples):
    name = "BLENDER_EEVEE" if engine.startswith("eevee") else \
        "BLENDER_WORKBENCH"
    scene.render.engine = name
    scene.eevee.use_raytracing = True   # L-TF3: the 5.2 SSR knob
    if hasattr(scene.eevee, "taa_render_samples"):
        scene.eevee.taa_render_samples = samples
    scene.view_settings.exposure = 0.3  # L-TF4 fixed at +0.3


if __name__ == "__main__":
    main()
