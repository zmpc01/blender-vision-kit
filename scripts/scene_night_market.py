"""scene_night_market.py -- NIGHT MARKET (tmarket_1), the seventh film.

A lantern-lit night market street: the crowd BROWSES in slow lanes
between the stall rows (the native per-agent weighted-anchor
assignment) and LINGERS at the stall fronts while a late-delivery
runner threads the spine against the grain (the teal callout) and a
vendor's lost child moment resolves at the food court (the amber
callout, a UAL principal at 0.78xUAL_SCALE -- no gate drama, the
D-NM1 audit P1).

Design of record: docs/DESIGN_night_market.md REV-2. Contract:
tmarket_contract.py (the single crowd authority). World:
tmarket_world.py (the CYCLES-native lantern night, BOTH-ENGINE
mirrors). The scene module shape throughout: scene_squall.py (the
s27-corrected sibling -- the canonical Cycles branch + the D2 hoist
ARE the law here; this film never renders Workbench by accident).

Export contract: build_scene returns ctx["scene"]; BEATS
(id, t_seconds, label); sfx {name|kind, frame}; render.fps pinned
here; the title = export-safe SCALE keys (hide_render does not
export -- the S12 law from the user's tdawn_2 review).
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
    "TMARKET_PREVIZ_SCRIPTS",
    str(_sib) if _sib.is_dir() else "/home/z/work/blender-escape-previz/scripts")
if _previz_scripts not in sys.path:
    sys.path.insert(0, _previz_scripts)

FPS = 24
total_frames = 1080
tm_exposure = 0.85           # the s28 eye-ladder rung 3: the lantern
                             # night owns the frame; the sky residue is
                             # the contrast floor

_here = os.path.dirname(os.path.abspath(__file__))

# --- shots (id, f0, f1, intent) -- the D-NM4 vantage table ------------
SHOTS_V3 = [
    ("S1",  1,    84,  "aerial: the lantern street establishes"),
    ("S2",  85,   168, "the lantern board close-up (the designed beat)"),
    ("S3",  169,  258, "aisle-level counter-flow in the spine"),
    ("S4",  259,  348, "the noodle queue starts forming"),
    ("S5",  349,  438, "the food court: steam, sodium, the apron crowd"),
    ("S6",  439,  528, "THE RUNNER enters the spine from the east"),
    ("S7",  529,  618, "the squeeze: the runner threads the queue"),
    ("S8",  619,  708, "the CHILD lost in the south walk"),
    ("S9",  709,  798, "the child looks around (the lost beat holds)"),
    ("S10", 799,  888, "the reunion at the food court"),
    ("S11", 889,  978, "the pull-back crane on the whole street"),
    ("S12", 979,  1080, "title: NIGHT MARKET ignites on the gantry"),
]

CAMS_V3 = [
    # S1: the high-SE aerial (the whole street; the lantern rows read
    # as two warm boards; motion starts calm -- the edit grammar)
    ("CAM_S1",  (16.0, -17.0, 17.0), (16.0, -17.0, 17.0), 28,
     (-2.0, 0.5, 0.0), False, 0.0),
    # S2: the lantern BOARD (inside the north aisle looking WEST along
    # the canopy line -- the s28 eye gate: the outside-north vantage
    # read the stall BACKS; the board is the along-aisle bokeh)
    ("CAM_S2",  (9.0, 4.4, 2.0), (9.0, 4.4, 2.0), 40,
     (-6.0, 2.3, 1.8), False, 0.0),
    # S3: the spine counter-flow (west-looking-east, lens level)
    ("CAM_S3",  (-12.0, 0.0, 1.7), (-12.0, 0.0, 1.7), 32,
     (8.0, 0.2, 1.1), False, 0.0),
    # S4: the queue forming (from the south walk across the row S
    # gap to the noodle front)
    ("CAM_S4",  (8.0, -2.8, 1.8), (8.0, -2.8, 1.8), 35,
     (-1.5, 1.4, 1.0), False, 0.0),
    # S5: the food-court apron (steam + sodium + the linger crowd;
    # above agent height -- row-free)
    ("CAM_S5",  (14.5, 4.5, 2.3), (14.5, 4.5, 2.3), 34,
     (19.5, -0.8, 1.0), False, 0.0),
    # S6: the runner enters (ahead of him, low; he approaches the
    # lens against the eastward browse drift)
    ("CAM_S6",  (13.0, 1.1, 1.5), (13.0, 1.1, 1.5), 36,
     (21.5, -0.3, 0.9), False, 0.0),
    # S7: the squeeze (the runner passes the queue stretch; the teal
    # against the milling amber-lit crowd)
    ("CAM_S7",  (6.0, -2.2, 1.7), (6.0, -2.2, 1.7), 34,
     (-1.0, 0.9, 1.0), False, 0.0),
    # S8: the child lost (the small amber figure in the south walk,
    # the crowd flows past -- the isolation read)
    ("CAM_S8",  (14.5, -1.0, 2.4), (14.5, -1.0, 2.4), 36,
     (9.5, -4.5, 0.7), False, 0.0),
    # S9: the child close (low, the lost beat holds)
    ("CAM_S9",  (11.3, -3.1, 1.25), (11.3, -3.1, 1.25), 42,
     (9.9, -4.55, 0.75), False, 0.0),
    # S10: the reunion (low from the south walk looking NE -- the s28
    # eye gate: the old SE vantage buried the child in the apron blob;
    # this isolates the child + the counter + the vendor behind)
    ("CAM_S10", (17.2, -4.9, 1.45), (17.2, -4.9, 1.45), 38,
     (20.1, -1.4, 0.9), False, 0.0),
    # S11: the pull-back crane (the s28 eye gate: the old loc0 sat
    # BEHIND the 3.4m south shopfront -- black frame; start ABOVE it
    # and rise; keyed in _kf_crane)
    ("CAM_S11", (2.0, -11.0, 5.2), (2.0, -13.5, 9.0), 30,
     (0.0, 0.0, 1.0), False, 0.0),
    # S12: the title push (west along the spine to the igniting
    # gantry sign)
    ("CAM_S12", (-4.5, 0.5, 1.7), (-9.5, 0.3, 2.1), 34,
     (-15.0, 0.4, 4.3), False, 0.0),
]

BEATS = [
    ("open",    0.0,   "market open (f1)"),
    ("browse",  3.50,  "the aisles fill (f85)"),
    ("counter", 7.0,   "the spine counter-flow (f169)"),
    ("queue",   11.0,  "the noodle queue forms (f265)"),
    ("food",    14.5,  "the food court (f349)"),
    ("runner",  18.25, "the runner enters (f439)"),
    ("squeeze", 22.0,  "the squeeze (f529)"),
    ("lost",    25.75, "the child lost (f619)"),
    ("looks",   29.5,  "the child looks (f709)"),
    ("reunion", 33.25, "the reunion (f799)"),
    ("pull",    37.0,  "the pull-back (f889)"),
    ("title",   40.75, "NIGHT MARKET ignites (f979)"),
]

CROWD_TIER_PINS = []

# the callout colors (the user's color law: the population stays the
# NEUTRAL CLAY register; color = callouts ONLY)
RUNNER_TEAL = (0.10, 0.52, 0.50)
CHILD_AMBER = (0.85, 0.55, 0.14)
RUNNER_SCALE = 1.75 / 1.589        # the family UAL principal scale
CHILD_SCALE = RUNNER_SCALE * 0.78  # the D-NM1 audit P1 (no gate drama)

CAST = {
    "Runner": {"root": "Runner.Root",
               "material": "CA.Body.Runner",
               "role": "the late-delivery runner threading the spine "
                       "against the grain (the teal callout)"},
    "Child": {"root": "Child.Root",
              "material": "CA.Body.Child",
              "role": "the vendor's lost child; the lost beat in the "
                      "south walk, the reunion at the food court "
                      "(the amber callout, UAL at 0.78xUAL_SCALE)"},
}


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


def _yaw_to(from_xy, to_xy):
    """The facing yaw for a keyed move (the +X-facing convention the
    UAL import arrives in; the facing_sign flip lives INSIDE the
    wrapper hierarchy -- the keyed ROOT yaw stays geometry-frame)."""
    return math.atan2(to_xy[1] - from_xy[1], to_xy[0] - from_xy[0])


def _heroes(scene):
    """The two keyed principal carriers (the ride_principals law: the
    UAL wrappers parent onto THESE; the commuter mesh degenerates to
    the GLB carrier -- hide_render excludes it, the node survives)."""
    from tdawn_actors import build_commuter_mesh, make_material
    out = {}
    lib = build_commuter_mesh("TM.HeroLib")
    lib.location = (60.0, 0.0, -2.5)
    lib.hide_render = True
    for name, loc, rgb in (
            ("Runner", (23.5, -0.4, 0.0), RUNNER_TEAL),
            ("Child", (10.0, -4.6, 0.0), CHILD_AMBER)):
        ob = bpy.data.objects.new(f"{name}.Root", lib.data)
        ob.location = loc
        scene.collection.objects.link(ob)
        ob.data = ob.data.copy()
        ob.data.materials.clear()
        ob.data.materials.append(make_material(
            f"CA.Body.{name}", rgb, rough=0.5))
        ob.hide_render = True          # the carrier law (the UAL
                                       # wrapper renders, not this)
        out[name] = ob
    return out


def _crowd_anchors(scene):
    """The anchors the kit-mode loader's rename law expects: the
    ingest ordinals map 1:1 to anchors in the loader's population
    order = ID-SORT (the s19-B4 law): ling_* (30) -> vend_* (6) ->
    zone0/1/2 (120) -> zz_chase (9). The anchor grid: the south walk
    band rows, then the spine, then the north walk, then the queue
    tail at the noodle front."""
    from tdawn_actors import (build_commuter_mesh, new_anchored_obj)
    lib = build_commuter_mesh("TM.CommlibLib")
    lib.location = (60.0, 0.0, -2.5)
    lib.hide_render = True
    crowd = []
    n = 0
    # 30 linger + 6 vendor + 120 zones = 156 grid anchors, then the
    # 9 queue anchors at the noodle front (the loader pairs by
    # ordinal; the grid is a PARKING lot -- the cache drives motion)
    for row_y in (-4.75, -4.35, 0.45, 0.0, -0.45, 4.75, 4.35, 5.15):
        for col in range(20):
            x = -24.0 + col * 2.5
            ob = new_anchored_obj(f"Zed.{n + 1:04d}", lib, (x, row_y, 0.0))
            crowd.append(ob)
            n += 1
            if n >= 156:
                break
        if n >= 156:
            break
    chase = []
    for i in range(12):
        # the loader's chase census: TWELVE chase objects with the RB
        # slots at indices 2/5/8 (the loader law; tsquall parked them
        # outboard) -- the 9 queue agents + the 3 RB carriers.
        if i in (2, 5, 8):
            x, y = (24.5 + (i // 3) * 2.0), -4.5   # outboard east
        else:
            j = i - (1 if i > 2 else 0) - (1 if i > 5 else 0) \
                - (1 if i > 8 else 0)
            x, y = (4.6 + j * 1.3), 0.75           # the queue stretch
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


def _title(scene):
    """NIGHT MARKET on the west gantry (the S12 law: export-safe
    SCALE keys -- dark until f979, ignite, two flickers, steady)."""
    from tdawn_actors import make_material
    mat = make_material(
        "TM.NeonTitle", (0.05, 0.04, 0.04), 0.4,
        emission_color=(1.0, 0.55, 0.18), emission_strength=5.0)
    crv = bpy.data.curves.new("TM.Title", type="FONT")
    crv.body = "NIGHT MARKET"
    crv.size = 0.34
    crv.align_x = "CENTER"
    crv.align_y = "CENTER"
    crv.extrude = 0.012
    ob = bpy.data.objects.new("TM.Title", crv)
    ob.location = (-15.0, 0.0, 4.35)    # proud of the gantry beam
    # (90, 0, 180): upright, facing EAST into the street (readable
    # from the S12 push lens inside the market)
    ob.rotation_euler = (math.pi / 2, 0.0, math.pi / 2)
    scene.collection.objects.link(ob)
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.convert(target="MESH")
    ob.data.materials.append(mat)
    _kf(ob, 1, scale=(0.001, 0.001, 0.001))
    _kf(ob, 979, scale=(0.001, 0.001, 0.001))
    _kf(ob, 983, scale=(1.0, 1.0, 1.0))      # ignite
    _kf(ob, 988, scale=(0.001, 0.001, 0.001))   # flicker out
    _kf(ob, 993, scale=(1.0, 1.0, 1.0))      # flicker in
    _kf(ob, 1080, scale=(1.0, 1.0, 1.0))
    _bezier(ob)
    return ob


def _kf_loc3(ob, frame, loc):
    """The FULL-location key (the crane's z MUST land -- the _kf
    helper preserves z by design for the ground-locked principals; the
    s28 eye gate caught the crane stuck at its build z behind the
    shopfront)."""
    ob.location = loc
    ob.keyframe_insert(data_path="location", frame=frame)


def _kf_crane(ctx):
    """The S11 pull-back crane (the tsquall pattern: the keyed camera
    rise; the s28 eye gate caught the UNKEYED crane sitting behind the
    south shopfront -- black frame)."""
    ob = ctx["cams"]["CAM_S11"]["ob"]
    _kf_loc3(ob, 889, (2.0, -11.0, 5.2))
    _kf_loc3(ob, 978, (2.0, -13.5, 9.0))
    _kf_loc3(ob, 1080, (2.0, -13.5, 9.0))
    _bezier(ob)


def _runner_keys(ctx):
    """The runner's keyed path (the teal callout): the delivery beat
    at the food court, the east staging, then the WEST thread through
    the spine (f439-720, ~4 m/s jog) -- against the eastward browse
    drift (the D-NM1 logline)."""
    ob = ctx["heroes"]["Runner"]
    path = [
        (1,   (23.5, -0.4), -1.8),
        (60,  (21.6, 0.9), 2.4),      # the delivery approach
        (140, (21.4, 1.3), 2.6),      # the hand-off hold
        (220, (23.5, -0.6), -1.6),    # back to the staging
        (430, (22.0, -0.3), -1.9),    # the thread start pose
        (500, (12.0, 0.35), -1.75),
        (560, (2.0, -0.35), -1.85),   # the queue stretch (south side)
        (620, (-8.0, 0.3), -1.7),
        (690, (-20.0, -0.2), -1.6),
        (730, (-24.5, 1.0), -0.9),    # the west exit/park
        (1080, (-24.5, 1.0), -0.9),
    ]
    for f, loc, rz in path:
        _kf(ob, f, loc=loc, rot_z=rz)
    _bezier(ob)


def _child_keys(ctx):
    """The child's keyed path (the amber callout): lost in the south
    walk (the look-around micro-beats), the scurry east to the food
    court (f780-870, ~2.8 m/s), the reunion hold at the counter."""
    ob = ctx["heroes"]["Child"]
    path = [
        (1,   (10.0, -4.6), 0.6),
        (300, (10.0, -4.6), 1.8),      # the look west
        (310, (10.0, -4.6), 0.6),
        (500, (10.0, -4.6), -0.9),     # the look east
        (510, (10.0, -4.6), 0.6),
        (700, (10.0, -4.6), 2.6),      # the lost beat holds
        (710, (10.0, -4.6), 0.5),
        (780, (10.4, -4.5), 0.15),     # the scurry starts
        (830, (15.5, -3.4), 0.02),
        (870, (19.8, -1.5), 0.35),     # the counter front
        (890, (20.1, -1.25), 0.9),     # facing the vendor
        (1080, (20.1, -1.25), 0.9),    # the reunion hold
    ]
    for f, loc, rz in path:
        _kf(ob, f, loc=loc, rot_z=rz)
    _bezier(ob)


def build_scene():
    scene = bpy.context.scene
    scene.render.fps = FPS
    # the B3 span law: the SCENE carries the shot span at build time
    scene.frame_start = 1
    scene.frame_end = total_frames
    for o in list(bpy.data.objects):
        if o.name.startswith(("Cube", "Camera", "Light", "Lamp")):
            bpy.data.objects.remove(o, do_unlink=True)
    import tmarket_world as W
    parts = W.build_world(scene)
    heroes = _heroes(scene)
    chars = _crowd_anchors(scene)
    cams = _cameras(scene)
    _markers(scene, cams)
    title = _title(scene)
    bpy.context.view_layer.update()
    return {"scene": scene, "parts": parts, "heroes": heroes,
            "cams": cams, "chars": chars, "title": title}


def animate(ctx, start_frame=1, n_frames=None, with_crowd=None):
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = total_frames
    _runner_keys(ctx)
    _child_keys(ctx)
    _kf_crane(ctx)
    crowd_cache = _crowd_cache_path()
    if crowd_cache and with_crowd is not False:
        _crowd_kit_branch(ctx, crowd_cache)
    elif with_crowd is False:
        print("[tmarket] --skip-crowd: pre-bake look (authored grid)")
    else:
        raise SystemExit(
            "[tmarket] no crowd cache at "
            f"$CROWD_CACHE_DIR/cache_ctx.json ({crowd_cache!r}) -- a "
            "crowd-less film renders silently otherwise (the 4-i P1-7 "
            "gate); pass --skip-crowd explicitly for the pre-bake look")
    bpy.context.view_layer.update()
    return None


def _crowd_cache_path():
    env = os.environ.get("CROWD_CACHE_DIR", "/tmp/crowdcache_tmarket")
    p = os.path.join(env, "cache_ctx.json")
    return p if os.path.exists(p) else None


def _crowd_kit_branch(ctx, cache_path):
    """The kit-mode crowd path -- the loader pin override carries 165
    (129 ingest + 30 linger + 6 vendors; the contract ledger)."""
    print(f"[tmarket] kit cache: {cache_path}")
    ctx["crowd_shots"] = _shot_table(SHOTS_V3, CAMS_V3)
    ctx["crowd_tier_pins"] = CROWD_TIER_PINS
    import crowd_kit as _CK
    _CK.loader.load_kit_cache(ctx, expected_agents=165)
    with open(cache_path) as f:
        ctx["cast"] = json.load(f).get("cast", {})
    import crowd_v6 as CV6
    CV6.bake_tier2(ctx)
    _crowd_palette(ctx)
    if os.environ.get("TMARKET_HUMANOID") == "1":
        _humanoid_layer(ctx)
    return ctx["crowd_cache"]


def _humanoid_layer(ctx):
    """NIGHT MARKET, humanized (the s25 D6 pattern, the market POP_PLAN):

    THE ORDINAL LAW (the s19-B4 id-sort): the loader reads populations
    ID-SORTED -- ling_* (6 pops x 5 = ordinals 0-29), vend_* (6 x 1 =
    30-35), zone0/1/2 (40 each = 36-155), zz_chase (9 = 156-164).

    The COLOR LAW (the user's tdawn_2 review, s27-verified): the
    population stays the NEUTRAL CLAY register; the callouts are the
    teal Runner + the amber Child (UAL principals) -- the lanterns may
    tint the GROUND, never the crowd materials.
    """
    import humanoid_crowd as HC
    fam = HC.crowd_family("rh_xbot")
    # THE ORDINAL LAW (id-sort): ling_* (0-29), vend_* (30-35),
    # zone0/1/2 (36-155 -- zone0 = THE SPINE, the chase host; the
    # s28 zone-order receipt), zz_chase (156-164).
    groups = [("linger", 30, (0.24, 0.22, 0.20)),     # warm grey clay
              ("vendors", 6, (0.45, 0.30, 0.14)),     # tarp ochre
              ("zone0_spine", 40, (0.30, 0.28, 0.26)),
              ("zone1_south", 40, (0.28, 0.26, 0.24)),
              ("zone2_north", 40, (0.26, 0.25, 0.27)),
              ("queue", 9, (0.18, 0.20, 0.24))]       # the queue dark
    agent_group = []
    for gi, (_, cnt, _rgb) in enumerate(groups):
        agent_group.extend([gi] * cnt)
    if len(agent_group) != 165:
        raise RuntimeError(
            f"_humanoid_layer: POP_PLAN split {len(agent_group)} != pin 165")
    gt = {"groups": [(c, rgb) for _, c, rgb in groups],
          "agent_group": agent_group}
    rep = HC.bind_crowd(ctx, fam, group_tint=gt)
    # the queue agents PARK at the slots by film end (the QueueNode
    # hold) -- the motion gates see them walk then stop; no exempt
    # rows (the tsquall faller class does not exist in this film)
    HC.motion_gates(ctx, rep["reps"], walk_cycle=rep["walk_cycle"])
    ctx["humanoid"] = rep
    # the TWO UAL principals (the D-NM1 cast): the Runner at the
    # family scale + the Child at 0.78 (the object-level rider law --
    # the scale rides matrix_parent_inverse, never keyed)
    pr = HC.bind_principals(ctx, {
        "Runner": ("Jog_Fwd_Loop", RUNNER_SCALE, None),
        "Child": ("Walk_Loop", CHILD_SCALE, None)})
    ctx["humanoid_principals"] = HC.ride_principals(ctx, pr, {
        "Runner": RUNNER_TEAL, "Child": CHILD_AMBER})


def _crowd_palette(ctx):
    """The market palette (the COLOR LAW): the crowd in muted clay
    tones ONLY -- the lanterns tint the ground, the callouts are the
    principals. The linger ordinals 0-29 + vendors 30-35 read by the
    same clay register (the vendor ochre is the one warm note, the
    tsquall vendor convention)."""
    from tdawn_actors import make_material
    CROWD_TONES = [(0.28, 0.26, 0.24), (0.30, 0.28, 0.26),
                   (0.26, 0.25, 0.27), (0.24, 0.22, 0.20)]
    VENDOR_TONES = [(0.42, 0.30, 0.16), (0.36, 0.24, 0.12)]
    QUEUE_TONES = [(0.24, 0.30, 0.40), (0.18, 0.23, 0.32)]
    chars = ctx["chars"]["zombies"]
    n = {"c": 0, "q": 0, "v": 0, "l": 0}
    bpy.context.scene.frame_set(1)
    # the anchor grid is ID-ORDERED by construction (the _crowd_anchors
    # law): ordinals 0-29 linger, 30-35 vendors, 36+ zones -- the same
    # id-sort the loader uses.
    for ob in chars["crowd"]:
        if ob.data.users > 1:
            ob.data = ob.data.copy()
        ob.data.materials.clear()
        if n["c"] < 30:
            tone = CROWD_TONES[n["c"] % 2]           # the linger clay
            ob.data.materials.append(make_material(
                f"CA.Comm.TM.Linger.{n['l'] % 2}", tone))
            n["l"] += 1
        elif n["c"] < 36:
            ob.data.materials.append(make_material(
                f"CA.Comm.TM.Vendor.{n['v'] % 2}",
                VENDOR_TONES[n['v'] % 2]))
            n["v"] += 1
        else:
            ob.data.materials.append(make_material(
                f"CA.Comm.TM.Crowd.{n['c'] % 4}",
                CROWD_TONES[n['c'] % 4]))
        n["c"] += 1
    for ob in chars["chase"]:
        if ob.data.users > 1:
            ob.data = ob.data.copy()
        ob.data.materials.clear()
        ob.data.materials.append(make_material(
            f"CA.Comm.TM.Queue.{n['q'] % 2}", QUEUE_TONES[n['q'] % 2]))
        n["q"] += 1
    print(f"[tmarket] palette: {n['l']} linger / {n['v']} vendors / "
          f"{n['c'] - 36} zones / {n['q']} queue (clay register)")


def emit_sfx_events(ctx, out_dir):
    events = list(json.loads(json.dumps(
        __import__("tmarket_contract").SFX_EVENTS)))
    cast = ctx.get("cast") or {}
    for b in cast.get("queue_bell_events", []):
        events.append({"name": b["name"], "frame": int(b["frame"])})
    events.sort(key=lambda e: e["frame"])
    with open(os.path.join(out_dir, "sfx_events.json"), "w") as f:
        json.dump({"fps": FPS, "meta": {"scene": "scene_night_market"},
                   "events": events}, f, indent=1)
    return events


def _script_args():
    argv = sys.argv
    return argv[argv.index("--") + 1:] if "--" in argv else []


def _set_engine(scene, engine, samples):
    # s27 engine-map law (DESIGN_engine_map_s27 D1/D2, audited REV-2):
    # the canonical Cycles branch (the tform shape) -- this film is
    # BORN under the corrected engine map; there is no Workbench
    # accident here. The exposure tail stays ENGINE-UNCONDITIONAL.
    engine = (engine or "").lower()
    if engine.startswith("cycles"):
        scene.render.engine = 'CYCLES'
        scene.cycles.samples = int(samples)
        scene.cycles.use_denoising = True
        scene.cycles.device = 'CPU'
        scene.cycles.max_bounces = 4
        scene.cycles.transmission_bounces = 2
        scene.cycles.volume_bounces = 1
        print(f"[tmarket] engine={scene.render.engine} samples={samples} "
              "denoise on CPU (s27 engine-map law)")
        return
    name = "BLENDER_EEVEE" if engine.startswith("eevee") else \
        "BLENDER_WORKBENCH"
    scene.render.engine = name
    if engine.startswith("eevee"):
        scene.eevee.use_raytracing = True
        if hasattr(scene.eevee, "taa_render_samples"):
            scene.eevee.taa_render_samples = samples
    scene.view_settings.exposure = tm_exposure


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="output/tmarket")
    p.add_argument("--engine", default="cycles")
    p.add_argument("--w", type=int, default=640)
    p.add_argument("--h", type=int, default=360)
    p.add_argument("--still", type=int, default=None)
    p.add_argument("--samples", type=int, default=24)
    p.add_argument("--skip-crowd", action="store_true")
    args = p.parse_args(_script_args())

    scene = bpy.context.scene
    # s27 D2 hoist (enabler): the engine-conditional world tunes read
    # scene.render.engine at BUILD time -- set it here so build_world
    # sees the true engine (the DESIGN_engine_map_s27 REV-2 law).
    from blender_kit import normalize_engine_id
    scene.render.engine = normalize_engine_id(args.engine)
    ctx = build_scene()
    animate(ctx, with_crowd=not args.skip_crowd)
    out = args.output
    os.makedirs(out, exist_ok=True)
    if args.still is not None:
        scene.frame_set(args.still)
        _set_engine(scene, args.engine, args.samples)
        scene.render.resolution_x = args.w
        scene.render.resolution_y = args.h
        scene.render.filepath = os.path.join(
            out, f"still_{args.still:05d}.png")
        bpy.ops.render.render(write_still=True)
    else:
        print("[tmarket] dry-run OK")
    bpy.context.view_layer.update()


if __name__ == "__main__":
    main()
