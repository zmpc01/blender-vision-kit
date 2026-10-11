"""scene_terminal_dawn.py -- TERMINAL DAWN, the vision-native previz short.

45 s @ 24 fps, 1080 frames, 12 shots. Built FROM SCRATCH with the
blender-vision-kit (vision-native principal, every step LOOK-verified);
crowd = blender-crowd-kit via the escape-previz `kit` plugin (the
kit-mode branch below mirrors scene_escape_v5.py:1256-1274).

Export (the deliverable is a previz-review package `tdawn_1`):
    the agent-kit exporter, kit crowd mode, via the crowd-kit wrapper
    (the binding law). See docs/DESIGN_terminal_dawn.md section 5.

Story: dawn. A grand terminal. The crowd surges toward the LAST GATE
OUT (world origin -- the sim's pursue target). The Master (amber)
holds the gate; the Runner (teal) pushes AGAINST the flow from the far
end. The threat is never shown: crowd pressure + light carry the film.

Module-contract notes (the exporter's unmapped-story-constant gate):
  * UPPERCASE names here are ONLY the mapped vocabulary (SHOTS_V3,
    CAMS_V3, CAST, SYNOPSIS, BEATS, CROWD_TIER_PINS) -- the crowd
    payload constants live in tdawn_contract.py (module-imported,
    never star-imported).
  * everything else scene-internal is lowercase.
"""
from __future__ import annotations

import math
import os
import sys
from pathlib import Path

import bpy

_here = str(Path(__file__).resolve().parent)
if _here not in sys.path:
    sys.path.insert(0, _here)

_previz_scripts = os.environ.get(
    "TPREVIZ_SCRIPTS", "/home/z/work/blender-escape-previz/scripts")
if _previz_scripts not in sys.path:
    sys.path.insert(0, _previz_scripts)

FPS = 24                  # mapped vocabulary (known non-story)
total_frames = 1080

# --- the mapped story vocabulary (exporter-known names) ---------------

SYNOPSIS = (
    "Dawn at a grand terminal. The city outside has gone silent and "
    "everyone in the hall knows what that means. The crowd surges "
    "toward the last gate out. The Master (station staff, amber) holds "
    "the line; the Runner (teal) pushes against the flow -- the only "
    "body moving the wrong way -- to reach the gate before it seals. "
    "The threat is never shown: the crowd is the antagonist.")

SHOTS_V3 = [
    ("S1",  1,    84,  "aerial dawn establish: hall + thin early flow"),
    ("S2",  85,   168, "departure board flickers; far windows glow wrong"),
    ("S3",  169,  264, "the surge ignites: flow accelerates, density jumps"),
    ("S4",  265,  348, "the Runner enters far end, turns against the flow"),
    ("S5",  349,  444, "lateral: the Runner jostles through the stream"),
    ("S6",  445,  528, "the Master holds the gate line; crowd piles up"),
    ("S7",  529,  624, "low tracker: the Runner stumbles, nearly lost"),
    ("S8",  625,  720, "the Master sees the Runner; holds the vault open"),
    ("S9",  721,  816, "the dive: the Runner through the sealing vault"),
    ("S10", 817,  912, "vault sealed; crowd held; the hall quiets"),
    ("S11", 913,  1008, "pull-back: dawn light floods the empty hall"),
    ("S12", 1009, 1080, "title frame: TERMINAL DAWN over the still hall"),
]

# (name, loc0, loc1, lens_mm, aim, parent_jeep, shake_amp)
# parent_jeep is the escape-film vocabulary (no jeep here -- always
# False; the mover stays False so TRACK_TO aiming is live on every cam).
CAMS_V3 = [
    ("CAM_S1",  (6.5, -6.5, 8.2), (5.0, -4.0, 7.4), 24,
     (0.0, 12.0, 1.2), False, 0.0),
    ("CAM_S2",  (3.2, 12.0, 2.6), (3.2, 12.0, 2.6), 38,
     (-0.5, 30.8, 5.4), False, 0.012),
    ("CAM_S3",  (0.0, -5.5, 8.4), (0.0, -4.8, 8.0), 28,
     (0.0, 15.0, 0.6), False, 0.0),
    ("CAM_S4",  (-2.5, 29.5, 2.6), (-2.5, 29.5, 2.6), 34,
     (1.5, 20.0, 1.0), False, 0.02),
    ("CAM_S5",  (8.4, 19.5, 1.8), (8.4, 13.0, 1.8), 38,
     (1.0, 18.0, 1.2), False, 0.025),
    ("CAM_S6",  (-5.6, 7.6, 1.65), (-5.6, 7.6, 1.65), 45,
     (0.0, 1.6, 1.4), False, 0.018),
    ("CAM_S7",  (-8.8, 11.5, 2.6), (-8.4, 9.5, 2.6), 35,
     (0.0, 6.5, 1.1), False, 0.034),
    ("CAM_S8",  (0.0, 3.2, 2.4), (0.0, 3.2, 2.4), 40,
     (0.0, 12.0, 1.1), False, 0.012),
    ("CAM_S9",  (0.4, -7.2, 3.4), (0.4, -7.2, 3.4), 24,
     (0.0, 2.0, 1.0), False, 0.022),
    ("CAM_S10", (-6.5, -2.6, 2.0), (-6.0, -2.0, 2.0), 35,
     (0.0, 4.0, 1.5), False, 0.0),
    ("CAM_S11", (2.0, 10.0, 2.2), (6.0, 2.0, 9.0), 30,
     (0.0, 8.0, 2.0), False, 0.0),
    ("CAM_S12", (8.0, 18.0, 3.4), (7.4, 15.5, 3.1), 35,
     (0.0, 9.0, 2.2), False, 0.0),
]

CAST = {
    "Master": {"role": "station master, holds the gate",
               "root": "Master.Root"},
    "Runner": {"role": "late commuter, pushes against the flow",
               "root": "Runner.Root"},
}

BEATS = [
    ("calm",       1.0,  "dawn trickle: the early flow moves quietly"),
    ("omen",       3.5,  "the board stutters; the far windows glow wrong"),
    ("surge",      7.0,  "the surge ignites: the hall turns into a stream"),
    ("runner_in",  8.8,  "the Runner enters at the far end, turns back"),
    ("against",    12.3, "the Runner pushes against the flow"),
    ("the_line",   16.5, "the Master holds the gate line under pressure"),
    ("stumble",    19.8, "the Runner is driven to a knee, nearly lost"),
    ("seen",       23.0, "the Master sees the Runner; holds the vault"),
    ("the_dive",   30.2, "the Runner dives through the sealing vault"),
    ("seal",       33.8, "the vault seals; the crowd is held"),
    ("dawn",       38.0, "the light turns; the hall empties into silence"),
    ("title",      42.0, "TERMINAL DAWN"),
]

CROWD_TIER_PINS = []       # kit mode: single tier, no director pins

# --- lowercase scene internals -----------------------------------------

_hero_path = [  # (t_seconds, x, y, dz, yaw_deg) -- the Runner's authored run
    (8.80, 2.5, 27.0, 0.0, 180.0),    # enters at the far end
    (10.80, 2.0, 23.5, 0.0, 176.0),   # turns against the flow
    (12.30, 1.2, 19.5, 0.0, 172.0),
    (14.30, -1.2, 15.5, 0.0, 168.0),
    (16.30, 1.0, 11.5, 0.0, 176.0),   # weaving the stream
    (19.60, -0.8, 7.6, 0.0, 170.0),
    (19.80, -0.9, 7.2, -0.18, 170.0),  # the stumble dips
    (20.40, -0.8, 6.2, -0.02, 168.0),
    (21.20, -0.4, 5.4, 0.0, 160.0),
    (23.80, 0.2, 3.6, 0.0, 150.0),
    (27.00, 0.4, 1.8, 0.0, 120.0),
    (30.20, 0.4, 0.2, 0.35, 100.0),   # the dive arc (vault throat)
    (31.00, 0.2, -1.6, 0.0, 90.0),    # through; doors seal behind
    (45.00, 0.2, -1.6, 0.0, 90.0),
]

_master_path = [
    (0.0, -1.9, 1.7, 0.0, 96.0),      # gate-left, watching the hall
    (21.0, -1.9, 1.7, 0.0, 96.0),
    (23.0, -0.9, 1.2, 0.0, 80.0),     # steps out to read the surge
    (27.0, 0.4, 0.9, 0.0, 60.0),      # to the throat, arm to the crowd
    (31.5, 0.4, 0.9, 0.0, 60.0),
    (34.5, -0.6, 0.9, 0.0, 75.0),     # back as the doors close
    (45.0, -0.6, 0.9, 0.0, 75.0),
]

# the vault seal: doors slide from parked (x +/-5.1) to closed (x +/-1.7)
_door_open_x = 5.1
_door_closed_x = 1.7
_seal_f0 = 760          # doors start closing (t 31.58 s, S9 mid-dive)
_seal_f1 = 812          # sealed

# the far-window incident glow rises from the S3 ignition
_glow_f0 = 169
_glow_f1 = 264

# the board flicker window (S2) then dies at the surge
_board_flick = (85, 168, 233)


def frame_at(t):
    return int(round(t * FPS)) + 1


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------

def _cameras(scene):
    from tdawn_actors import make_material
    cams = {}
    for name, loc0, loc1, lens, aim, _pj, _sh in CAMS_V3:
        cd = bpy.data.cameras.new(name)
        cd.lens = lens
        cam = bpy.data.objects.new(name, cd)
        cam.location = loc0
        scene.collection.objects.link(cam)
        tgt = bpy.data.objects.new(f"Aim.{name}", None)
        tgt.location = aim
        tgt.empty_display_size = 0.3
        scene.collection.objects.link(tgt)
        c = cam.constraints.new(type="TRACK_TO")
        c.target = tgt
        c.track_axis = "TRACK_NEGATIVE_Z"
        c.up_axis = "UP_Y"
        cams[name] = {"cam": cam, "tgt": tgt,
                      "loc0": loc0, "loc1": loc1}
    scene.camera = cams["CAM_S1"]["cam"]
    for shot_id, f0, _f1, _d in SHOTS_V3:
        m = scene.timeline_markers.new(f"CAM_{shot_id}", frame=f0)
        m.camera = cams[f"CAM_{shot_id}"]["cam"]
    return cams


def _anchors(scene):
    """The crowd capsule anchors: 120 Zed.NNNN + 12 chase placeholders.

    ONE library mesh shared by all (bake2 copies per-instance before
    adding shape keys). Spawn poses approximate the contract zones;
    bake2 overwrites them with the sim keys from f1.
    """
    from tdawn_actors import (build_commuter_mesh, commuter_material,
                              new_anchored_obj, BRIDGE_HEIGHT_M)
    lib = build_commuter_mesh("TD.CommuteLib", BRIDGE_HEIGHT_M)
    lib.location = (0.0, -40.0, 0.0)     # park the library mesh off-set
    crowd = []
    for i in range(120):
        ob = new_anchored_obj(
            f"Zed.{i + 1:04d}", lib,
            (((i % 12) - 5.5) * 1.5, 8.0 + (i // 12) * 1.45, 0.0),
            yaw=math.radians(180.0))
        ob.data.materials.clear()
        ob.data.materials.append(commuter_material(i))
        crowd.append(ob)
    chase = []
    for i in range(12):
        ob = new_anchored_obj(
            f"Zed.ChaseP{i + 1:02d}", lib,
            (((i % 6) - 2.5) * 1.2, 21.0 + (i // 6) * 2.0, 0.0),
            yaw=math.radians(180.0))
        ob.data.materials.clear()
        ob.data.materials.append(commuter_material(i + 5))
        chase.append(ob)
    return {"crowd": crowd, "chase": chase}


def _heroes(scene):
    from tdawn_actors import (build_commuter_mesh, hero_material,
                              new_anchored_obj)
    heroes = {}
    for name, loc, h in (("Master", (-1.9, 1.7, 0.0), 1.78),
                         ("Runner", (2.5, 27.0, 0.0), 1.72)):
        lib = build_commuter_mesh(f"TD.HeroLib.{name}", h,
                                  mat_body=hero_material(name))
        lib.location = (0.0, -41.0, 0.0)
        root = new_anchored_obj(f"{name}.Root", lib, loc,
                                yaw=math.radians(96))
        root.data.materials.clear()
        root.data.materials.append(hero_material(name))
        heroes[name] = root
    return heroes


def build_scene():
    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.frame_start = 1
    scene.frame_end = total_frames

    import tdawn_world
    world = tdawn_world.build_world(scene)
    cams = _cameras(scene)
    chars = {"zombies": _anchors(scene)}
    heroes = _heroes(scene)

    # view-layer SYNC duty (L19 law family): the last-linked objects
    # (Runner.Root measured) can lag the view-layer object list -- the
    # exporter's #29 sweep then false-positives them as view-layer
    # excluded and gate 24 rejects the package (refs-without-node).
    # One forced update closes it scene-side (F-TD5; the kit-side fix
    # belongs in render_hidden_objects -- see the frictions doc).
    bpy.context.view_layer.update()
    return {"scene": scene, "world": world, "cams": cams,
            "chars": chars, "humans": heroes}


# ---------------------------------------------------------------------------
# animation
# ---------------------------------------------------------------------------

def _kf(obj, f, loc=None, rot_z=None, z=None):
    if loc is not None:
        obj.location = loc
        obj.keyframe_insert(data_path="location", frame=f)
    if z is not None:
        obj.location.z = z
        obj.keyframe_insert(data_path="location", index=2, frame=f)
    if rot_z is not None:
        obj.rotation_euler = (0.0, 0.0, math.radians(rot_z))
        obj.keyframe_insert(data_path="rotation_euler", index=2, frame=f)


def _iter_fcurves(action):
    """The 4.x/5.x fcurve iterator -- the vetted blender_kit helper
    first (both kit copies carry it: previz superset under the export
    wrapper, vision-kit copy under blrun/look), local fallback second
    (5.2 slotted actions: channelbag takes a SLOT object, not an int)."""
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


def _linear(obj):
    """LINEAR interpolation on all of obj's fcurves (4.x + 5.x)."""
    if obj.animation_data is None or obj.animation_data.action is None:
        return
    for fc in _iter_fcurves(obj.animation_data.action):
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"


def _kf_heroes(ctx):
    """Authored hero paths (belt-free world-space; both heroes are
    grounded -- z keys only for the stumble dip + the dive arc)."""
    runner = ctx["humans"]["Runner"]
    master = ctx["humans"]["Master"]
    for t, x, y, dz, yaw in _hero_path:
        _kf(runner, frame_at(t), loc=(x, y, 0.0 + dz), rot_z=yaw)
    for t, x, y, _dz, yaw in _master_path:
        _kf(master, frame_at(t), loc=(x, y, 0.0), rot_z=yaw)
    # idle sway keys (subtle life at the gate): tiny z bobs
    for f in range(1, total_frames, 12):
        master.location.z = 0.012 * math.sin(f * 0.55)
        master.keyframe_insert(data_path="location", index=2, frame=f)
    _linear(runner)
    _linear(master)
    # linear interpolation OFF for the idle sway (smooth sine reads
    # better than a linear zigzag at 12-frame spacing)
    _smooth(master)


def _smooth(obj):
    if obj.animation_data is None or obj.animation_data.action is None:
        return
    for fc in _iter_fcurves(obj.animation_data.action):
        if fc.data_path == "location" and fc.array_index == 2:
            for kp in fc.keyframe_points:
                kp.interpolation = "SINE"


def _kf_cameras(ctx):
    scene = ctx["scene"]
    cams = ctx["cams"]
    for name, info in cams.items():
        c, l0, l1 = info["cam"], info["loc0"], info["loc1"]
        if tuple(l0) != tuple(l1):
            c.location = l0
            c.keyframe_insert(data_path="location", frame=1)
            # the move runs across the SHOT window (find it by name)
            sid = name.replace("CAM_", "")
            row = next(r for r in SHOTS_V3 if r[0] == sid)
            c.location = l1
            c.keyframe_insert(data_path="location", frame=row[2])
        _linear(c)
    # S5: the aim target tracks the Runner laterally
    t5 = cams["CAM_S5"]["tgt"]
    for f in range(349, 445, 6):
        t = (f - 1) / FPS
        y = _hero_y_at(t)
        t5.location = (0.6, y, 1.2)
        t5.keyframe_insert(data_path="location", frame=f)
    _linear(t5)


def _hero_y_at(t):
    for (t0, x0, y0, _z0, _y0), (t1, x1, y1, _z1, _y1) in zip(
            _hero_path, _hero_path[1:]):
        if t0 <= t <= t1:
            k = 0.0 if t1 == t0 else (t - t0) / (t1 - t0)
            return y0 + (y1 - y0) * k
    return _hero_path[-1][2]


def _kf_set_pieces(ctx):
    """Gate seal + window glow + board flicker."""
    scene = ctx["scene"]
    gate = ctx["world"]["gate"]
    for d, sx in ((gate["door_l"], -1.0), (gate["door_r"], 1.0)):
        d.location.x = sx * _door_closed_x
        d.keyframe_insert(data_path="location", index=0, frame=_seal_f1)
        d.location.x = sx * _door_open_x
        d.keyframe_insert(data_path="location", index=0, frame=_seal_f0)
        d.keyframe_insert(data_path="location", index=0, frame=1)
    _linear(gate["door_l"])
    _linear(gate["door_r"])

    # far-window incident glow: strength 0 -> 3.2 across the ignition
    glow_mat = bpy.data.materials.get("TD.WindowGlow")
    if glow_mat and glow_mat.use_nodes:
        bsdf = next(n for n in glow_mat.node_tree.nodes
                    if n.type == "BSDF_PRINCIPLED")
        em = bsdf.inputs["Emission Strength"]
        em.default_value = 0.0
        em.keyframe_insert(data_path="default_value", frame=_glow_f0)
        for f, v in ((_glow_f0 + 20, 0.8), (_glow_f1, 1.6),
                     (900, 1.1), (1009, 0.7), (1080, 0.7)):
            em.default_value = v
            em.keyframe_insert(data_path="default_value", frame=f)

    # departure board: flicker through S2 then dies at the surge
    board_mat = bpy.data.materials.get("TD.Board")
    if board_mat and board_mat.use_nodes:
        bsdf = next(n for n in board_mat.node_tree.nodes
                    if n.type == "BSDF_PRINCIPLED")
        em = bsdf.inputs["Emission Strength"]
        f_a, f_b, die = _board_flick
        for f in range(f_a, f_b, 7):
            em.default_value = 2.4 if (f // 7) % 3 else 0.7
            em.keyframe_insert(data_path="default_value", frame=f)
        for f, v in ((die, 0.0), (1080, 0.0)):
            em.default_value = v
            em.keyframe_insert(data_path="default_value", frame=f)

    # the throat glow rises as the seal approaches
    throat_mat = bpy.data.materials.get("TD.ThroatGlow")
    if throat_mat and throat_mat.use_nodes:
        bsdf = next(n for n in throat_mat.node_tree.nodes
                    if n.type == "BSDF_PRINCIPLED")
        em = bsdf.inputs["Emission Strength"]
        em.default_value = 0.0
        bsdf.inputs["Base Color"].default_value = (1.0, 0.80, 0.55, 1.0)
        # AgX desaturates hot emission to tan — keep <= ~1.7 so the
        # throat reads warm-golden, never crushed brown (measured)
        for f, v in ((1, 0.55), (625, 0.75), (760, 0.9), (816, 0.95),
                     (912, 0.6), (1009, 0.45), (1080, 0.45)):
            em.default_value = v
            em.keyframe_insert(data_path="default_value", frame=f)

    # gate glow brightens as the story reaches the seal
    gate_mat = bpy.data.materials.get("TD.GateGlow")
    if gate_mat and gate_mat.use_nodes:
        bsdf = next(n for n in gate_mat.node_tree.nodes
                    if n.type == "BSDF_PRINCIPLED")
        em = bsdf.inputs["Emission Strength"]
        for f, v in ((1, 0.35), (625, 0.7), (816, 1.4), (912, 0.8),
                     (1080, 0.6)):
            em.default_value = v
            em.keyframe_insert(data_path="default_value", frame=f)


def animate(ctx, start_frame=1, n_frames=None, with_crowd=None):
    """look.py-compatible signature (start_frame/n_frames accepted;
    the animation is the fixed 1080-frame grid). with_crowd=None
    auto-detects the kit cache (CROWD_CACHE_DIR or /tmp/crowdcache_tdawn)
    so PRE-BAKE looks still render heroes + cameras + set pieces."""
    if with_crowd is None:
        cache_dir = os.environ.get("CROWD_CACHE_DIR",
                                   "/tmp/crowdcache_tdawn")
        with_crowd = os.path.isfile(
            os.path.join(cache_dir, "cache_v6.npz"))
        if not with_crowd:
            print("[tdawn] animate: no kit cache found -- crowd branch "
                  "skipped (heroes/cameras/set pieces only)")
    _kf_heroes(ctx)
    _kf_cameras(ctx)
    _kf_set_pieces(ctx)
    if with_crowd:
        _crowd_kit_branch(ctx)
    return ctx


def _crowd_kit_branch(ctx):
    """The kit-mode crowd path (mirrors scene_escape_v5.py:1256-1274).

    The bake itself runs EARLIER, headless (tdawn_bake.py, venv);
    this branch loads the converted cache + materializes keys.
    """
    ctx["crowd_shots"] = _shot_table(SHOTS_V3, CAMS_V3)
    ctx["crowd_tier_pins"] = CROWD_TIER_PINS
    import crowd_kit as _CK
    _CK.loader.load_kit_cache(ctx)
    import crowd_v6 as CV6
    CV6.bake_tier2(ctx)
    return ctx["crowd_cache"]


def _shot_table(shots, cams):
    """The ShotCam rows the tiering/stash contract carries (same shape
    as crowd_v6.tiering.shot_table; kept local so the scene module
    stays independent of the v6 import order)."""
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


# ---------------------------------------------------------------------------
# sfx
# ---------------------------------------------------------------------------

def emit_sfx_events(ctx, out_dir):
    """Frame-stamped event stream (the sfx_events.json contract:
    {"fps", "meta", "events": [{name, frame, ...}]})."""
    events = [
        {"name": "board_chime", "frame": 85},
        {"name": "board_stutter", "frame": 150},
        {"name": "rumble", "frame": 169, "strength": 0.6},
        {"name": "surge_swell", "frame": 220, "strength": 1.0},
        {"name": "jostle", "frame": 352, "n": 10},
        {"name": "jostle", "frame": 470, "n": 14},
        {"name": "stumble", "frame": 560},
        {"name": "gate_hold", "frame": 625},
        {"name": "vault_seal", "frame": 790, "dur": 2.4},
        {"name": "quiet", "frame": 860},
        {"name": "dawn_swell", "frame": 913},
        {"name": "title_sting", "frame": 1009},
    ]
    path = os.path.join(out_dir, "sfx_events.json")
    os.makedirs(out_dir, exist_ok=True)
    import json
    with open(path, "w") as fh:
        json.dump({"fps": FPS,
                   "meta": {"scene": "terminal_dawn",
                            "shots": len(SHOTS_V3)},
                   "events": events}, fh, indent=1)
    print(f"[tdawn] sfx event stream: {len(events)} events -> {path}")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def _script_args():
    argv = sys.argv
    if "--" in argv:
        return argv[argv.index("--") + 1:]
    return []


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True)
    ap.add_argument("--engine", default="eevee")
    ap.add_argument("--frames", type=int, default=total_frames)
    ap.add_argument("--start", type=int, default=1)
    ap.add_argument("--samples", type=int, default=16)
    ap.add_argument("--w", type=int, default=640)
    ap.add_argument("--h", type=int, default=360)
    ap.add_argument("--still", type=int, default=None)
    ap.add_argument("--quality", default="preview")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--encode-mp4", action="store_true")
    ap.add_argument("--skip-crowd", action="store_true",
                    help="build + animate WITHOUT the crowd cache "
                         "(world/hero look iterations before the bake)")
    ap.add_argument("--scene-name", default="terminal_dawn")
    args = ap.parse_args(_script_args())

    os.makedirs(args.output, exist_ok=True)
    ctx = build_scene()

    if args.dry_run:
        n_obs = len(bpy.context.scene.collection.all_objects)
        print(f"[tdawn] DRY-RUN OK: {n_obs} objects, "
              f"{len(ctx['chars']['zombies']['crowd'])} crowd anchors, "
              f"{len(ctx['chars']['zombies']['chase'])} chase, "
              f"{len(ctx['cams'])} cams, {len(SHOTS_V3)} shots")
        return

    if not args.skip_crowd:
        animate(ctx)
    else:
        animate(ctx, with_crowd=False)

    emit_sfx_events(ctx, args.output)
    _render(ctx, args)


def _split_args(argv):
    """(kept for tooling compat) args after '--'."""
    return _script_args()


def _set_engine(scene, engine, samples):
    if engine == "workbench":
        scene.render.engine = "BLENDER_WORKBENCH"
        scene.display.shading.light = "STUDIO"
        scene.display.shading.color_type = "MATERIAL"
        scene.display.shading.show_shadows = True
        scene.view_settings.view_transform = "Standard"
    elif engine in ("eevee", "eevee_next"):
        # 5.x reverted the id to BLENDER_EEVEE (4.2-era was _NEXT)
        try:
            scene.render.engine = "BLENDER_EEVEE"
        except TypeError:
            scene.render.engine = "BLENDER_EEVEE_NEXT"
        try:
            scene.eevee.taa_render_samples = samples
        except AttributeError:
            pass
    else:
        scene.render.engine = "CYCLES"
        scene.cycles.samples = samples
        scene.cycles.use_denoising = True


def _render(ctx, args):
    scene = ctx["scene"]
    scene.render.resolution_x = args.w
    scene.render.resolution_y = args.h
    scene.render.image_settings.file_format = "PNG"
    _set_engine(scene, args.engine.lower(), args.samples)

    if args.still is not None:
        scene.frame_set(args.still)
        scene.render.filepath = os.path.join(
            args.output, f"still_{args.still:05d}.png")
        bpy.ops.render.render(write_still=True)
        print(f"[tdawn] still f{args.still} -> {scene.render.filepath}")
        return

    for f in range(args.start, min(args.start + args.frames,
                                   total_frames + 1)):
        scene.frame_set(f)
        scene.render.filepath = os.path.join(
            args.output, f"frame_{f:05d}.png")
        bpy.ops.render.render(write_still=True)
        if f % 48 == 0:
            print(f"[tdawn] rendered f{f}")


if __name__ == "__main__":
    main()
