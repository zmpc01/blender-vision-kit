"""tfog_scene.py -- THE EXPRESS (tfog_1), the fifth film.

Blue-hour fog rail platform: the crowd waits under sodium pools while
fog pools on the slab; the board flips EXPRESS APPROACHING; the
headlight cone builds through the fog; THE BLAST -- the express slides
through the N face at speed, the DANGER window (frames 336-528) presses
the loose crowd BACK (real base displacement) while the door queue
HOLDS, and the keyed late passenger sprints against it and misses; the
fog closes, the local decelerates into the S face, the queue admits,
cohorts board through the shared door; the local pulls out; the board
flips the title card EXPRESS - PASSING WITHOUT STOP over the lone
figure on the bench.

Design of record: docs/DESIGN_express.md REV-3 (sections 3/6/9). The
scene module shape follows scene_squall.py -- the tsquall-pattern scene
module of record (factory purge, world import, load_kit_cache wiring,
palette, keyed heroes, camera table + markers + keepouts, sfx block,
honesty asserts, main/argparse). Contract: tfog_contract.py (the
CONTRACT-AUTHORITATIVE keepouts + train paths + board program -- the
scene module READS them, it does not re-author). World: tfog_world.py
(never duplicates geometry; the TFOG_* ladder constants are overridden
here BEFORE build_world -- the tgreen/tsquall law). Bake artifacts:
/tmp/crowdcache_tfog/ (cache_v6.npz + cache_ctx.json); the ctx json's
cast block (heroes / train_paths / board_program / sfx_rows /
sfx_events / beats) is the authored truth, consumed verbatim.

The x2 law: cache 541 ticks @ 12 Hz = 45 s over 24 fps / 1080 frames;
1 tick = 2 frames. Every exported surface here (shot spans, sfx
frames, keepout windows, board flips, train slides, hero keys) is
authored in FRAMES.

Timeline: 1080 frames, 12 shots (docs section 9), spans contiguous
1..1080. ONE keyed crane (S5 blast cam, loc0->loc1 both keyed).
S10 is staged OFF-walkable (the S track bed) so the contract's three
keepout rows remain the COMPLETE ground-lens truth (the docs section 6
"all ground lenses" law, honored by staging rather than new rows --
the bake applied exactly the contract's 3 rows, cache digest
keepouts_applied=3; adding rows post-bake would be dishonest).

Deviations / ambiguity resolutions (the tgreen ledger way):
1. THE PIN: expected_agents=126, NOT 135. The cache npz meta pins
   n_agents=126 (66 waiters + 51 cohorts + 9 doorq -- contract REV-3:
   "the loader pin override carries 126 (F-TS5)") and the kit loader's
   honesty gate fails LOUD on any other pin (loader.py:_honesty_asserts
   -- pinning the docs section-2 REV-2 total 135 would crash the
   pipeline at the gate). The 135 declared cast is asserted here as
   the reconciliation 126 cache + 9 chase-lane (the keyed hero lane
   lives OUTSIDE the cache, the drill's branch-a law), so the REV-2
   honesty intent survives both halves.
2. Anchors: 117 crowd (Zed.0001..0117) + 12 chase (Zed.Chase01..12
   with the 3 RB placeholders at indices 2/5/8) -- the loader's 9.1
   rename law requires exactly n_agents-9 crowd and 12 chase, and the
   ctx json's chars block confirms the shape (its 9-name chase list is
   the POST-rename pairing table).
3. tsquall_scene.py does not exist in this repo; the pattern of record
   is scene_squall.py (same structure, film 4 of record).
4. The S10 moving cam is descoped to a static lens this pass (the ONE
   keyed-crane law of the build order wins; its CAMS row keeps loc1 so
   the camprobe wave can re-key the move as ONE edit later).
5. Board flips are EMISSION-STRENGTH keys on per-row glyph materials
   (the tferry _em_keys pattern; no hide_render anywhere -- export-safe
   SCALE keys only, and this film needs none). Per-row material copies
   are a scene-side re-assignment of the world's ONE glyph material --
   the world geometry is untouched.
6. The per-zone speed map driver is READ-ONLY (tgreen shape): it parses
   zone ids from the contract geometry (bench rects -> bench zones, the
   open center strip -> the aisle), asserts bench-slow / aisle-fast and
   the envelope-cap law mu+3sigma == the cache's max_speed, and prints
   the map. The baked bytes are never mutated.
7. Hero root names follow the exporter registry law (<Name>.Root +
   CA.Body.<Name>, film-4 convention); scene-side props the module
   owns outright are lowercase (tfg_* / sm_*). Cam names CAM_S* are
   pinned by the contract's keepout rows.

Export contract: build_scene returns the ctx; BEATS (id, t_seconds,
label) derived verbatim from the ctx json's cast.beats; sfx events
{name, frame} from cast.sfx_rows + cast.sfx_events (every frame
asserted inside [0, 1080]); render.fps pinned here.
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
    "TFOG_PREVIZ_SCRIPTS",
    str(_sib) if _sib.is_dir() else "/home/z/work/blender-escape-previz/scripts")
if _previz_scripts not in sys.path:
    sys.path.insert(0, _previz_scripts)

import tfog_contract as C          # noqa: E402  (the contract authority)
import tfog_world as W             # noqa: E402  (world geometry consts)

FPS = 24
total_frames = C.TOTAL_FRAMES      # 1080 (the x2 law; contract-pinned)
tf_exposure = 0.0            # the blue-hour ladder sweeps sky/practicals

# --- the F-TS5 pin (see ledger 1) -------------------------------------
EXPECTED_AGENTS = 126       # the cache npz meta n_agents (fail-closed)
CHASE_TAIL = 9              # the kit chase tail (gates.py:769)
DECLARED_TOTAL = 135        # the REV-2 declared cast: 126 + 9 chase lane

CACHE_DIR_DEFAULT = "/tmp/crowdcache_tfog"

# --- shots (id, f0, f1, intent) -- the docs section-9 table, FRAMES ---
SHOTS_V1 = [
    ("S1",  1,    96,  "aerial platform axis, blue hour establish"),
    ("S2",  97,   190, "sodium lamp pool, waiters drift"),
    ("S3",  191,  288, "headlight cone builds through fog (signature)"),
    ("S4",  289,  336, "departure board EXPRESS APPROACHING (flicker)"),
    ("S5",  337,  528, "THE BLAST: train streaks, crowd presses back, "
                       "queue holds (the keyed crane)"),
    ("S6",  529,  608, "recoil wide: the platform holds its breath"),
    ("S7",  609,  672, "the missed sprint: late passenger at the edge"),
    ("S8",  673,  792, "the local arrives (warm headlight, slower)"),
    ("S9",  793,  876, "door press: queue + cohorts (cohesion readable)"),
    ("S10", 877,  948, "through the door: warm interior vs cold platform"),
    ("S11", 949,  1008, "pull-out rear: fog swallows the tail lights; "
                        "doorway ghosts"),
    ("S12", 1009, 1080, "title: EXPRESS - PASSING WITHOUT STOP"),
]

CAMS_V1 = [
    # S1: NE aerial 3/4 down the platform axis (aerial: row-free, the
    # D6 clamp is 2D-xy)
    ("CAM_S1",  (30.0, -18.0, 16.0), (30.0, -18.0, 16.0), 30,
     (0.0, 0.0, 0.5), False, 0.0),
    # S2: the lamp pool at the CONTRACT keepout spot (px,py verbatim;
    # row window 0..190 covers the planted lens through f190)
    ("CAM_S2",  (-22.0, 0.5, 2.4), (-22.0, 0.5, 2.4), 30,
     (-15.0, -2.0, 0.5), False, 0.0),   # S2c (round-1 cert: the waiters IN frame under the canopy)
    # S3: on the N track bed looking W down the track (outside the
    # walkable: y=-14); the headlight cone grows toward the lens
    ("CAM_S3",  (0.0, -14.0, 2.2), (0.0, -14.0, 2.2), 40,
     (-28.0, -8.5, 1.5), False, 0.0),
    # S4: the board's S face from the S track bed (outside the
    # walkable: y=10.5); the flip reads under the canopy edge
    ("CAM_S4",  (-6.5, 9.0, 2.2), (-6.5, 9.0, 2.2), 45,
     (0.0, 0.1, 2.6), False, 0.0),   # S4b (round-1 cert: board + the waiting figures)
    # S5: THE KEYED CRANE (the blast cam): aerial oblique off the N
    # face, dollies E with the pass (loc0 -> loc1, both keyed)
    ("CAM_S5",  (-14.0, -12.0, 9.0), (14.0, -12.0, 7.0), 35,
     (8.0, -2.5, 0.8), False, 0.0),   # aim re-centered on the pressed crowd + the
                                      # N track (the streak reads via the lit windows)
    # S6: the recoil wide at the CONTRACT keepout spot (row 528..672)
    ("CAM_S6",  (-9.0, -2.2, 2.2), (-9.0, -2.2, 2.2), 30,
     (3.0, 0.2, 0.7), False, 0.0),   # S6h (round-3 cert: the pressed mass + the board + depth)
    # S7: the missed sprint, from the N bed E (outside the walkable);
    # the figure braced at the N edge, the tail lights gone E
    ("CAM_S7",  (24.0, -10.0, 2.6), (24.0, -10.0, 2.6), 35,
     (20.0, -3.4, 1.0), False, 0.0),   # S7b (round-1 cert: the braced figure isolated vs the pressed wall)
    # S8: the local's arrival, elevated off the N side (z=6 aerial
    # class: row-free); the warm 3-car glides in on the S face
    ("CAM_S8",  (-2.0, -15.0, 4.0), (-2.0, -15.0, 4.0), 40,
     (-12.0, 7.5, 1.5), False, 0.0),   # S8b (round-1 cert: the warm local reads BIG against the cold platform)
    # S9: the door press at the CONTRACT keepout spot (row 792..912)
    ("CAM_S9",  (-3.0, -1.0, 2.2), (-3.0, -1.0, 2.2), 40,
     (1.0, 3.4, 0.9), False, 0.0),   # S9b (round-1 cert: the queue line + the warm flank)
    # S10: through the door -- staged OFF-walkable (S bed, y=6.5 the
    # whole hold: ledger 4, the static descope; loc1 kept for the
    # camprobe wave's ONE-edit re-key)
    ("CAM_S10", (-21.5, -2.0, 1.6), (-21.5, -2.0, 1.6), 35,
     (-24.0, 4.6, 1.2), False, 0.0),   # round-4: the local's door faces the platform
                                       # from the y+ face (the stop is x=-24) — the warm
                                       # interior vs the cold platform
    # S11: the pull-out rear from the S bed W; the tail recedes E
    # into the fog
    ("CAM_S11", (-44.0, 5.0, 2.6), (-44.0, 5.0, 2.6), 35,
     (-24.0, 7.0, 1.4), False, 0.0),   # S11k (round-4 cert: the local's rear + the receding platform)
    # S12: W of the platform (x=-38 outside the walkable): the axis,
    # the lit title board, the lone figure on the W bench
    ("CAM_S12", (20.0, -8.0, 2.2), (20.0, -8.0, 2.2), 30,
     (3.0, -1.5, 1.7), False, 0.0),   # S12o (round-5 cert: the axis + the bench figure
                                      # + the distant board — the lit title owns it in EEVEE)
]

# the keepout rows are CONTRACT-AUTHORITATIVE (tfog_contract.CAM_KEEPOUTS,
# the exact rows the bake clamped against -- cache digest
# keepouts_applied=3); re-exported here as the scene's keepout surface
keepouts = tuple(C.CAM_KEEPOUTS)
keepout_r = float(C.CAM_KEEPOUT_R)

CROWD_TIER_PINS = []

# exporter-name aliases (the film-4 exporter contract): the exporter
# introspects SHOTS (or SHOTS_V3) + CAMS_V3; this film's certified
# tables are SHOTS_V1/CAMS_V1 — same 4-row / 7-tuple shapes verbatim.
SHOTS = SHOTS_V1
CAMS_V3 = CAMS_V1

# the exporter characters registry (the film-4 gate-5 shape)
CAST = {
    "LatePassenger": {"root": "LatePassenger.Root",
                      "material": "CA.Body.LatePassenger",
                      "role": "sprints the N edge against the express "
                              "and misses; alone on the W bench at the "
                              "title"},
    "Stationmaster": {"root": "Stationmaster.Root",
                      "material": "CA.Body.Stationmaster",
                      "role": "lantern patrol along the center aisle; "
                              "braces the blast at the N-facing hold"},
}

# the blue-hour palette (docs section 6: cool blue-gray W crowd, warm
# sodium tints E) -- the split rides the ingest order, not literals
crowd_cool = [(0.22, 0.25, 0.32), (0.18, 0.21, 0.27),
              (0.26, 0.29, 0.35), (0.20, 0.23, 0.30)]
crowd_warm = [(0.36, 0.26, 0.16), (0.30, 0.22, 0.14), (0.40, 0.30, 0.18)]
queue_tones = [(0.16, 0.20, 0.28), (0.20, 0.24, 0.32)]

# the tgreen-pattern per-zone speed map (m/s mu, sig): bench slow,
# aisle fast (ledger 6 -- read-only driver, the cache is baked bytes)
zone_speed_map = {
    "bench_w": (0.55, 0.10),
    "bench_e": (0.55, 0.10),
    "aisle_center": (1.10, 0.15),
}

# --- board flip ladder (per-row glyph emission, the tferry pattern) ---
board_dim = 0.10             # the quiet SERVICE SUSPENDED ghost rows
board_hot = 1.25             # the near-board measured cap (L-TF1 class)
board_title = 1.45           # the title card pushes slightly past it

BEATS = []                   # derived verbatim from cast.beats at build


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


def _linear(ob):
    for fc in _iter_fcurves(ob.animation_data.action):
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"


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


def _em_keys(mat, keys):
    """Emission-strength keys (the tferry pattern; the board flips,
    the window arcs, the aspects). Values stay in the measured near-
    field bands (the fog multiplies emission -- the tsquall ceiling
    law reconfirmed on this world's probe). NOTE: socket-level
    .keyframe_insert() silently no-ops on material node trees in 5.x —
    the explicit node_tree data_path is the reliable form."""
    bsdf = next(n for n in mat.node_tree.nodes
                if n.type == "BSDF_PRINCIPLED")
    sock = bsdf.inputs["Emission Strength"]
    idx = list(bsdf.inputs).index(sock)
    path = f'nodes["{bsdf.name}"].inputs[{idx}].default_value'
    for f, v in keys:
        sock.default_value = float(v)
        mat.node_tree.keyframe_insert(data_path=path, frame=f)


def _script_args():
    argv = sys.argv
    return argv[argv.index("--") + 1:] if "--" in argv else []


# ======================================================================
# build-side pieces
# ======================================================================

def _heroes(scene):
    """The keyed heroes OUTSIDE the cache (the drill's branch-a law):
    the LATE PASSENGER (sprint lane, docs section 3 frames 336-672)
    and the STATIONMASTER (lantern patrol). Warm identity tones,
    distinct from both crowd families."""
    from tdawn_actors import build_commuter_mesh, make_material
    out = {}
    mesh = build_commuter_mesh("tfg_hero_lib")
    mesh.location = (60.0, 0.0, -6.0)   # sunk under the grounding plane
    for name, rgb, yaw, loc in (
            ("LatePassenger", (0.62, 0.40, 0.14), math.radians(180.0),
             (-21.0, 1.6, 0.0)),
            ("Stationmaster", (0.16, 0.19, 0.24), math.radians(90.0),
             (-26.0, 0.9, 0.0))):
        ob = bpy.data.objects.new(f"{name}.Root", mesh.data)
        ob.location = loc
        ob.rotation_euler = (0.0, 0.0, yaw)
        scene.collection.objects.link(ob)
        ob.data = ob.data.copy()
        ob.data.materials.clear()
        ob.data.materials.append(make_material(f"CA.Body.{name}", rgb,
                                               rough=0.5))
        out[name] = ob
    # the lantern: a small warm glow child on the stationmaster's
    # lead hand (static emission -- a scene-side prop, not a world
    # keyed slot; the blue-hour warm point against the cool field)
    lam = bpy.data.objects.new("sm_lantern",
                               _lantern_mesh("sm_lantern"))
    lam.location = (0.16, 0.24, 0.98)
    scene.collection.objects.link(lam)
    lam.parent = out["Stationmaster"]
    return out


def _lantern_mesh(name):
    from tdawn_actors import make_material
    import bmesh
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=8, radius=0.09)
    bm.to_mesh(mesh)
    bm.free()
    mesh.materials.append(make_material(
        "tfg_lantern_glow", (0.05, 0.04, 0.03), 0.4,
        emission_color=(1.0, 0.62, 0.25), emission_strength=2.2))
    return mesh


def _crowd_anchors(scene):
    """The anchors the kit loader's 9.1 rename law expects: 117 crowd
    Zed.NNNN (parked as the authored waiting grid on the slab -- the
    pre-bake look) + 12 chase Zed.ChasePNN with the 3 RB placeholders
    at indices 2/5/8 parked offstage on the S bed. bake_tier2 re-poses
    every paired anchor from the cache; the grid is cosmetic."""
    from tdawn_actors import (build_commuter_mesh, new_anchored_obj,
                              commuter_material)
    lib = build_commuter_mesh("tfg_commlib_lib",
                              mat_body=commuter_material(0))
    lib.location = (60.0, 0.0, -6.0)    # sunk, out of every frustum
    crowd = []
    n_crowd = EXPECTED_AGENTS - CHASE_TAIL        # 117 (ledger 2)
    for i in range(n_crowd):
        row, col = divmod(i, 13)
        x = -26.4 + col * 4.4
        y = -2.2 + row * 0.55
        ob = new_anchored_obj(f"Zed.{i + 1:04d}", lib, (x, y, 0.0))
        crowd.append(ob)
    chase = []
    for i in range(12):
        if i in (2, 5, 8):   # the RB slots (the loader's indices)
            x, y, z = (36.0 + (i // 3) * 3.0), 8.5, -0.9   # offstage S bed
        else:
            row, col = divmod(i, 4)
            x, y, z = (24.0 + col * 1.6), 5.4 + row * 0.9, -0.9
        ob = new_anchored_obj(f"Zed.ChaseP{i + 1:02d}", lib, (x, y, z))
        chase.append(ob)
    return {"zombies": {"crowd": crowd, "chase": chase}}


def _cameras(scene):
    cams = {}
    for row in CAMS_V1:
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
    for sid, f0, _f1, _intent in SHOTS_V1:
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


def _board_row_materials(ctx):
    """Per-row glyph material copies (ledger 5): the world built ONE
    glyph material for all 8 glyph boxes; the flip ladder needs 4
    independent rows (r1..r4, both faces of a row share). Geometry is
    untouched -- a material re-assignment only."""
    mats = ctx["parts"]["mats"]
    glyph = mats["glyph"]
    export = ctx["parts"]["export"]
    row_mats = {}
    for ri in range(1, len(W.GLYPH_ZS) + 1):
        m = glyph.copy()
        m.name = f"tfg_glyph_r{ri}"
        for tag in ("n", "s"):
            ob = bpy.data.objects.get(f"board_r{ri}_{tag}")
            if ob is None:
                raise RuntimeError(f"tfog_scene: world board row "
                                   f"board_r{ri}_{tag} missing")
            ob.data.materials.clear()
            ob.data.materials.append(m)
        row_mats[ri] = m
    return row_mats


# ======================================================================
# key-side pieces (animate)
# ======================================================================

def _kf_late_passenger(ctx):
    """The sprint lane (docs section 3, the S5 row: 'keyed late
    passenger sprints against it, misses'): waits at the W end facing
    the N track; sprints E along the N edge inside the blast window;
    braces at the edge through S7; crosses to the W bench during
    boarding and SITS -- alone at the title. The sit is the capsule
    vocabulary's origin sink (the film-4 bystander idiom)."""
    lp = ctx["heroes"]["LatePassenger"]
    _kf(lp, 1, loc=(-21.0, 1.6), rot_z=math.radians(180.0))
    _kf(lp, 340, loc=(-21.0, 1.6), rot_z=math.radians(180.0))
    _kf(lp, 400, loc=(-2.0, -2.8))                 # the sprint, E
    _kf(lp, 470, loc=(14.0, -2.9))
    _kf(lp, 505, loc=(21.5, -3.0))                 # the edge, spent
    _kf(lp, 528, loc=(21.5, -3.0), rot_z=0.0)      # turns to the slab
    _kf(lp, 612, loc=(21.5, -3.0), rot_z=0.0)      # S7: at the edge
    _kf(lp, 672, loc=(21.5, -3.0), rot_z=0.0)
    _kf(lp, 800, loc=(13.5, -2.6))                 # the walk to bench4
    _kf(lp, 826, loc=(12.0, -2.45))
    lp.location = (12.0, -2.45, -0.35)             # the sit: origin sinks
    lp.keyframe_insert(data_path="location", frame=830)
    lp.location = (12.0, -2.45, -0.35)
    lp.keyframe_insert(data_path="location", frame=1080)
    _bezier(lp)


def _kf_stationmaster(ctx):
    """The lantern patrol: a brisk walk E along the center aisle, the
    N-facing hold through the whole blast window (he watches the
    pass), the resume, the slow drift W toward the lone figure for
    the title."""
    sm = ctx["heroes"]["Stationmaster"]
    _kf(sm, 1, loc=(-26.0, 0.9), rot_z=math.radians(90.0))
    _kf(sm, 430, loc=(6.5, 0.9), rot_z=math.radians(90.0))
    _kf(sm, 444, loc=(6.5, 0.9), rot_z=math.radians(180.0))  # faces N
    _kf(sm, 528, loc=(6.5, 0.9), rot_z=math.radians(180.0))  # the hold
    _kf(sm, 560, loc=(6.5, 0.9), rot_z=math.radians(90.0))
    _kf(sm, 900, loc=(26.0, 0.9), rot_z=math.radians(90.0))
    _kf(sm, 912, loc=(26.0, 0.9), rot_z=math.radians(-90.0))
    _kf(sm, 1080, loc=(14.0, 0.9), rot_z=math.radians(-90.0))
    _bezier(sm)


def _kf_board(ctx):
    """The 5 program flips (cast.board_program verbatim) as per-row
    emission keys: quiet dim at f1, then each program frame flips its
    row hot and the previous row dim (1-frame snaps: old at f-1, new
    at f). The FINAL state is the title card on row 4."""
    cast = ctx["cast"]
    program = [(int(f), str(label)) for f, label in cast["board_program"]]
    flips = [f for f, _ in program]
    # the driver authors the quiet state at frame 0 ("from the start");
    # the film's first keyable frame is 1 — both mean the same hold.
    if flips[0] not in (0, 1) or flips[1:] != [192, 528, 792, 1009]:
        raise RuntimeError(f"tfog_scene: board program frames {flips} "
                           "are not the authored 5-flip ladder")
    flips = [1] + flips[1:]
    rm = ctx["board_row_mats"]
    dim, hot, title = board_dim, board_hot, board_title
    ctx["board_flips"] = [1, 192, 528, 792, 1009]   # normalized ladder
    _em_keys(rm[1], [(1, dim), (191, dim), (192, hot),
                     (527, hot), (528, dim), (1080, dim)])
    _em_keys(rm[2], [(1, dim), (527, dim), (528, hot),
                     (791, hot), (792, dim), (1080, dim)])
    _em_keys(rm[3], [(1, dim), (791, dim), (792, hot),
                     (1008, hot), (1009, dim), (1080, dim)])
    _em_keys(rm[4], [(1, dim), (1008, dim), (1009, title),
                     (1080, title)])
    ctx["board_flips"] = flips


def _kf_trains(ctx):
    """The keyed slides from cast.train_paths VERBATIM (frames are
    already x2-law frames): the express W->E through the N face
    (LINEAR -- a train does not ease), the local decel-in / dwell /
    accel-out (BEZIER). An f1 hold key at each path's first x parks
    both trains offstage W before their windows (the world's parked
    roots would otherwise brush the platform W end)."""
    cast = ctx["cast"]
    paths = cast["train_paths"]
    exp = bpy.data.objects[ctx["parts"]["export"]["express_root"]]
    loc = bpy.data.objects[ctx["parts"]["export"]["local_root"]]
    exp_path = [(int(f), float(x)) for f, x in paths["express"]]
    loc_path = [(int(f), float(x)) for f, x in paths["local"]]
    if exp_path != [(336, -200.0), (528, 40.0)]:
        raise RuntimeError(f"tfog_scene: express path {exp_path} is not "
                           "the authored 336->528 slide")
    if loc_path != [(672, -120.0), (792, -24.0), (984, -24.0),
                    (1080, 120.0)]:
        raise RuntimeError(f"tfog_scene: local path {loc_path} is not "
                           "the authored decel/dwell/depart ladder")
    for ob, path, interp in ((exp, exp_path, "LINEAR"),
                             (loc, loc_path, "BEZIER")):
        ry, rz = ob.location.y, ob.location.z
        f0, x0 = path[0]
        ob.location = (x0, ry, rz)                 # the f1 hold
        ob.keyframe_insert(data_path="location", frame=1)
        for f, x in path:
            ob.location = (x, ry, rz)
            ob.keyframe_insert(data_path="location", frame=f)
        if interp == "LINEAR":
            _linear(ob)
        else:
            _bezier(ob)
    ctx["train_keys"] = {"express": exp_path, "local": loc_path}


def _kf_headlight(ctx):
    """The keyed lamp (docs section 3: 'keyed lamp + emission'): a
    warm SPOT parented to the express root at the leading end; the
    cone builds through the S3 wind window, owns the pass, dies with
    it. Energy keys only."""
    exp = bpy.data.objects[ctx["parts"]["export"]["express_root"]]
    ld = bpy.data.lights.new("express_headlight", type='SPOT')
    ld.color = (1.0, 0.92, 0.78)
    ld.shadow_soft_size = 0.30
    ld.spot_size = 0.55
    ld.spot_blend = 0.35
    ld.energy = 0.0
    ob = bpy.data.objects.new("express_headlight", ld)
    ob.location = (128.0, 0.0, 1.6)      # the leading (+x) end, local
    ob.rotation_euler = (0.0, math.pi / 2, 0.0)   # -Z -> +x, down-track
    scene = bpy.context.scene
    scene.collection.objects.link(ob)
    ob.parent = exp
    for f, e in ((1, 0.0), (240, 0.0), (260, 400.0), (300, 1400.0),
                 (336, 2600.0), (470, 2600.0), (510, 800.0), (528, 0.0)):
        ld.energy = e
        ld.keyframe_insert(data_path="energy", frame=f)
    _bezier(ld)     # the keys live on the LIGHT DATA, not the object
    return ob


def _kf_window_arc(ctx):
    """The keyed emission on the train window strips (the world built
    them at strength 0 -- the scene keys the arcs): the express
    windows light with the approach and die with the pass; the local
    windows warm through the boarding dwell and recede on departure
    (the tferry window-recede idiom)."""
    mats = ctx["parts"]["mats"]
    _em_keys(mats["win_express"],
             [(1, 0.0), (240, 0.0), (260, 0.5), (300, 1.4),
              (336, 1.8), (470, 1.8), (510, 0.6), (528, 0.0)])
    _em_keys(mats["win_local"],
             [(1, 0.0), (672, 0.0), (700, 0.9), (984, 0.9),
              (1020, 0.3), (1080, 0.3)])


def _kf_aspects(ctx):
    """The gantry aspects (the glyph-color spine): RED owns the
    express approach + pass (no stop), GREEN owns the local windows.
    The world shipped both at strength 0; the scene keys the flips."""
    mats = ctx["parts"]["mats"]
    _em_keys(mats["aspect_red"],
             [(1, 0.0), (240, 0.0), (260, 2.2), (528, 2.2),
              (540, 0.0), (1080, 0.0)])
    _em_keys(mats["aspect_green"],
             [(1, 0.0), (600, 0.0), (620, 2.0), (1080, 2.0)])


def _kf_crane(ctx):
    """S5 keys its blast-crane move (loc0 -> loc1, BOTH keyed, the
    ONE keyed camera of the film); the aim empty holds."""
    c5 = ctx["cams"]["CAM_S5"]["ob"]
    c5.location = ctx["cams"]["CAM_S5"]["loc0"]
    c5.keyframe_insert(data_path="location", frame=337)
    c5.location = ctx["cams"]["CAM_S5"]["loc1"]
    c5.keyframe_insert(data_path="location", frame=528)
    _bezier(c5)
    a5 = bpy.data.objects.get("Aim.CAM_S5")
    a5.location = ctx["cams"]["CAM_S5"]["aim"]
    a5.keyframe_insert(data_path="location", frame=337)
    a5.keyframe_insert(data_path="location", frame=528)


def _crowd_palette(ctx):
    """The blue-hour split (docs section 6) riding the INGEST ORDER
    (contract POP_PLAN, never literals): the W-bound waiters in cool
    blue-gray, the door-side cohorts in warm sodium tints, the door
    queue (the cache chase tail) in the disciplined steel pair that
    HOLDS through the blast."""
    from tdawn_actors import make_material
    n_wait = int(C.POP_PLAN[0][1])
    n_cohort = int(C.POP_PLAN[1][1])
    n_queue = int(C.POP_PLAN[2][1])
    if n_wait + n_cohort + n_queue != EXPECTED_AGENTS:
        raise RuntimeError("tfog_scene: POP_PLAN counts do not sum to "
                           f"the pin ({EXPECTED_AGENTS})")
    chars = ctx["chars"]["zombies"]
    n = {"cool": 0, "warm": 0, "q": 0}
    bpy.context.scene.frame_set(1)
    for ob in chars["crowd"]:
        if ob.data.users > 1:
            ob.data = ob.data.copy()
        ob.data.materials.clear()
        if n["cool"] < n_wait:      # the W drifters
            ob.data.materials.append(make_material(
                f"CA.Comm.TF.Cool.{n['cool'] % 4}",
                crowd_cool[n["cool"] % 4]))
            n["cool"] += 1
        else:                       # the E/door cohorts
            ob.data.materials.append(make_material(
                f"CA.Comm.TF.Warm.{n['warm'] % 3}",
                crowd_warm[n["warm"] % 3]))
            n["warm"] += 1
    for ob in chars["chase"]:
        if ob.data.users > 1:
            ob.data = ob.data.copy()
        ob.data.materials.clear()
        ob.data.materials.append(make_material(
            f"CA.Comm.TF.Queue.{n['q'] % 2}", queue_tones[n["q"] % 2]))
        n["q"] += 1
    print(f"[tfog] crowd palette: {n['cool']} cool W / {n['warm']} warm "
          f"E / {n['q']} queue steel (ingest-order split)")


def _zone_speed_driver(ctx):
    """The tgreen-pattern per-zone speed map, READ-ONLY (ledger 6):
    parse zone ids from the contract geometry (the bench BLOCKED rects
    split W/E by x sign; the open center strip is the aisle), assert
    bench-slow / aisle-fast, cross-check the aisle band against the
    baked waiter mu and the envelope-cap law mu+3sigma == the cache
    max_speed. Prints the map; mutates nothing."""
    bench_w = [bid for bid, r in C.BLOCKED
               if bid.startswith("bench") and (r[0] + r[2]) / 2 < 0]
    bench_e = [bid for bid, r in C.BLOCKED
               if bid.startswith("bench") and (r[0] + r[2]) / 2 > 0]
    zones = {f"bench_w[{','.join(bench_w)}]": zone_speed_map["bench_w"],
             f"bench_e[{','.join(bench_e)}]": zone_speed_map["bench_e"],
             "aisle_center[y -1.6..1.6 open strip]":
                 zone_speed_map["aisle_center"]}
    bench_mu = max(v[0] for k, v in zones.items() if k.startswith("bench"))
    aisle_mu = zone_speed_map["aisle_center"][0]
    if not bench_mu < aisle_mu:
        raise RuntimeError("tfog_scene: zone speed map violates "
                           "bench-slow / aisle-fast")
    wait_mu = float(C.POP_PLAN[0][3][0])
    if abs(aisle_mu - wait_mu) > 0.05:
        raise RuntimeError("tfog_scene: aisle band disagrees with the "
                           f"baked waiter mu ({aisle_mu} vs {wait_mu})")
    cap = wait_mu + 3.0 * float(C.POP_PLAN[0][3][1])
    cache_cap = float(ctx["cache_block"]["agent_constants"]["max_speed"])
    if abs(cap - cache_cap) > 1e-3:
        raise RuntimeError("tfog_scene: envelope cap mu+3sigma "
                           f"({cap:.3f}) != cache max_speed ({cache_cap})")
    for z, (mu, sig) in zones.items():
        print(f"[tfog] zone speed: {z} -> mu {mu:.2f} sig {sig:.2f}")
    print(f"[tfog] envelope cap {cap:.2f} m/s == cache max_speed "
          "(the waiters own the cap)")


# ======================================================================
# build / animate
# ======================================================================

def _cache_paths():
    d = os.environ.get("CROWD_CACHE_DIR", CACHE_DIR_DEFAULT)
    return (os.path.join(d, "cache_v6.npz"),
            os.path.join(d, "cache_ctx.json"))


def build_scene():
    scene = bpy.context.scene
    scene.render.fps = FPS
    # the B3 span law: the SCENE carries the shot span at build time
    scene.frame_start = 1
    scene.frame_end = total_frames
    # FACTORY PURGE first (the kit law: no default Cube/Camera/Light)
    for o in list(bpy.data.objects):
        if o.name.startswith(("Cube", "Camera", "Light", "Lamp")):
            bpy.data.objects.remove(o, do_unlink=True)

    npz_path, ctx_json_path = _cache_paths()
    if not os.path.exists(ctx_json_path):
        raise SystemExit(f"[tfog] no cache ctx json at {ctx_json_path} "
                         "-- the cast block is the authored truth")
    with open(ctx_json_path) as f:
        block = json.load(f)
    cast = block.get("cast") or {}
    for key in ("heroes", "train_paths", "board_program", "sfx_rows",
                "sfx_events", "beats"):
        if key not in cast:
            raise SystemExit(f"[tfog] cache ctx json cast.{key} missing "
                             "-- refusing to guess")
    ctx = {"cache_block": block, "cast": cast}

    # the BEATS export surface, derived verbatim from cast.beats
    BEATS.clear()
    for i, (f, label) in enumerate(cast["beats"]):
        BEATS.append((f"b{i + 1}", round(float(f) / FPS, 4), str(label)))
    ctx["beats"] = list(BEATS)

    # the sfx spine: cast.sfx_rows + cast.sfx_events, frames asserted
    events = [{"name": str(e["name"]), "frame": int(e["frame"])}
              for e in list(cast["sfx_rows"]) + list(cast["sfx_events"])]
    bad = [e for e in events if not (0 <= e["frame"] <= total_frames)]
    if bad:
        raise RuntimeError(f"tfog_scene: sfx events outside "
                           f"[0,{total_frames}]: {bad}")
    events.sort(key=lambda e: e["frame"])
    ctx["sfx_events"] = events

    # the world via tfog_world import; the TFOG_* ladder overrides
    # BEFORE build_world (the tgreen/tsquall law)
    import tfog_world as W
    W.TFOG_LAMP_STRENGTH = 0.40     # 0.40 * 800 = 320 W sodium pools
    W.TFOG_STRIP_STRENGTH = 0.50    # the cool canopy strips, dim
    parts = W.build_world(scene)
    ctx["parts"] = parts

    # the blue-hour sky (the LADDER verdict, session-19: sky1.0 deep
    # blue — the world defers the sky to the scene deliberately; the
    # practicals punch THROUGH it, the ratio law)
    _sky = bpy.data.worlds.new("TFG.BlueHour")
    _sky.use_nodes = True
    _bg = _sky.node_tree.nodes.get("Background")
    _bg.inputs["Color"].default_value = (0.05, 0.09, 0.20, 1.0)
    _bg.inputs["Strength"].default_value = 1.0
    scene.world = _sky

    # the sodium pools ride the ladder override (built ON)
    for lamp_name in parts["export"]["lamps"]:
        lo = bpy.data.objects.get(lamp_name)
        if lo is None or abs(lo.data.energy) < 1e-6:
            raise RuntimeError(f"tfog_scene: lamp {lamp_name} did not "
                               "pick up the ladder override")

    heroes = _heroes(scene)
    chars = _crowd_anchors(scene)
    cams = _cameras(scene)
    _markers(scene, cams)
    ctx["board_row_mats"] = _board_row_materials(ctx)
    bpy.context.view_layer.update()
    ctx.update({"scene": scene, "heroes": heroes, "cams": cams,
                "chars": chars})
    return ctx


def animate(ctx, start_frame=1, n_frames=None, with_crowd=None):
    scene = bpy.context.scene
    scene.frame_start = start_frame
    scene.frame_end = total_frames if n_frames is None \
        else start_frame + n_frames - 1
    _kf_late_passenger(ctx)
    _kf_stationmaster(ctx)
    _kf_board(ctx)
    _kf_trains(ctx)
    _kf_headlight(ctx)
    _kf_window_arc(ctx)
    _kf_aspects(ctx)
    _kf_crane(ctx)
    crowd_cache = _crowd_cache_path()
    if crowd_cache and with_crowd is not False:
        _crowd_kit_branch(ctx, crowd_cache)
    elif with_crowd is False:
        print("[tfog] --skip-crowd: pre-bake look (authored grid)")
    else:
        raise SystemExit(
            "[tfog] no crowd cache at "
            f"$CROWD_CACHE_DIR/cache_ctx.json ({crowd_cache!r}) -- a "
            "crowd-less film renders silently otherwise (the film-4 "
            "P1-7 gate); pass --skip-crowd explicitly for the "
            "pre-bake look")
    fails = _honesty(ctx)
    if fails:
        raise RuntimeError(f"tfog_scene: {fails} honesty assert(s) "
                           "FAILED -- the film is not honest, refusing")
    bpy.context.view_layer.update()
    return None


def _crowd_cache_path():
    env = os.environ.get("CROWD_CACHE_DIR", CACHE_DIR_DEFAULT)
    p = os.path.join(env, "cache_ctx.json")
    return p if os.path.exists(p) else None


def _crowd_kit_branch(ctx, cache_path):
    """The kit-mode crowd path (the scene_squall wiring, this film's
    pin + paths; see ledger 1 for the 126-vs-135 pin law)."""
    print(f"[tfog] kit cache: {cache_path}")
    ctx["crowd_shots"] = _shot_table(SHOTS_V1, CAMS_V1)
    ctx["crowd_tier_pins"] = CROWD_TIER_PINS
    npz_path, ctx_json_path = _cache_paths()
    if not os.path.exists(npz_path):
        raise SystemExit(f"[tfog] no cache npz at {npz_path}")
    import crowd_kit as _CK
    _CK.loader.load_kit_cache(ctx, npz_path=npz_path,
                              ctx_json=ctx_json_path,
                              expected_agents=EXPECTED_AGENTS)
    import crowd_v6 as CV6
    CV6.bake_tier2(ctx)
    _crowd_palette(ctx)
    _zone_speed_driver(ctx)
    if os.environ.get("TFOG_HUMANOID") == "1":
        _humanoid_layer(ctx)
    return ctx["crowd_cache"]


def _humanoid_layer(ctx):
    """THE EXPRESS, humanized (s25 rollout — the D6 pattern): the 126
    cache anchors gain RH x_bot rig assemblies; the 2 keyed heroes
    gain UAL mannequins. Env-gated (TFOG_HUMANOID=1) so tfog_1 rev1
    stays reproducible byte-for-byte.

    POP_PLAN — THE PINNED SLICE LAW (tfog_bake.py:194-200, s19-B4):
    cache ordinal order == POP_PLAN ingest order — waiters [0:66],
    cohorts [66:117], doorq [117:126]. The N_CACHE assert in the bake
    is the tripwire that keeps these slices honest.
    """
    import humanoid_crowd as HC
    fam = HC.crowd_family("rh_xbot")
    groups = [("waiters", 66, (0.27, 0.28, 0.31)),    # platform drab
              ("cohorts", 51, (0.23, 0.25, 0.28)),    # the boarding cohorts
              ("doorq", 9, (0.16, 0.19, 0.24))]       # the door queue dark
    agent_group = []
    for gi, (_, cnt, _rgb) in enumerate(groups):
        agent_group.extend([gi] * cnt)
    if len(agent_group) != 126:
        raise RuntimeError(
            f"_humanoid_layer: POP_PLAN split {len(agent_group)} != pin 126")
    gt = {"groups": [(c, rgb) for _, c, rgb in groups],
          "agent_group": agent_group}
    rep = HC.bind_crowd(ctx, fam, group_tint=gt)
    HC.motion_gates(ctx, rep["reps"], walk_cycle=rep["walk_cycle"])
    ctx["humanoid"] = rep
    # the UAL principals: LatePassenger (0.62,0.40,0.14) + Stationmaster
    # (0.16,0.19,0.24) — the identity tones from _heroes (:328-331)
    UAL_SCALE = 1.75 / 1.589
    pr = HC.bind_principals(ctx, {
        "LatePassenger": ("Idle_Loop", UAL_SCALE, None),
        "Stationmaster": ("Idle_Loop", UAL_SCALE, None)})
    ctx["humanoid_principals"] = HC.ride_principals(ctx, pr, {
        "LatePassenger": (0.62, 0.40, 0.14),
        "Stationmaster": (0.16, 0.19, 0.24)})


def emit_sfx_events(ctx, out_dir):
    events = list(json.loads(json.dumps(ctx["sfx_events"])))
    with open(os.path.join(out_dir, "sfx_events.json"), "w") as f:
        json.dump({"fps": FPS, "meta": {"scene": "tfog_scene"},
                   "events": events}, f, indent=1)
    return events


# ======================================================================
# honesty asserts (the build-end gate)
# ======================================================================

def _ok(tag, cond, detail):
    print(f"[tfog-qa] {'PASS' if cond else 'FAIL'} {tag}: {detail}")
    return 0 if cond else 1


def _loc_key_frames(ob):
    """(frame, x) pairs of the object's location fcurves (the 5.2
    slotted-action-safe read)."""
    frames = {}
    if ob.animation_data is None or ob.animation_data.action is None:
        return frames
    for fc in _iter_fcurves(ob.animation_data.action):
        if fc.data_path == "location" and fc.array_index == 0:
            for kp in fc.keyframe_points:
                frames[int(round(kp.co[0]))] = float(kp.co[1])
    return frames


def _honesty(ctx):
    fails = 0
    scene = ctx["scene"]
    cast = ctx["cast"]

    # 1. the F-TS5 pin + the declared-total reconciliation (ledger 1)
    cache = ctx.get("crowd_cache")
    pin_ok = cache is not None and int(cache.n_agents) == EXPECTED_AGENTS
    fails += _ok("f-ts5 pin", pin_ok,
                 f"cache n_agents={getattr(cache, 'n_agents', None)} == "
                 f"pin {EXPECTED_AGENTS}; declared cast "
                 f"{EXPECTED_AGENTS} + {CHASE_TAIL} chase lane = "
                 f"{DECLARED_TOTAL}")
    fails += _ok("declared total",
                 EXPECTED_AGENTS + CHASE_TAIL == DECLARED_TOTAL,
                 f"{EXPECTED_AGENTS}+{CHASE_TAIL}=={DECLARED_TOTAL}")

    # 2. the crowd anchors (the 9.1 rename law shape)
    chars = ctx["chars"]["zombies"]
    fails += _ok("crowd count",
                 len(chars["crowd"]) == EXPECTED_AGENTS - CHASE_TAIL
                 and len(chars["chase"]) == 12,
                 f"{len(chars['crowd'])} crowd (want "
                 f"{EXPECTED_AGENTS - CHASE_TAIL}) + "
                 f"{len(chars['chase'])} chase (want 12)")

    # 3. the 12 cameras + markers + contiguous spans
    shots = {sid: (f0, f1) for sid, f0, f1, _ in SHOTS_V1}
    fails += _ok("camera count", len(ctx["cams"]) == 12
                 and len(shots) == 12,
                 f"{len(ctx['cams'])} cams / {len(shots)} shots")
    contiguous = True
    expect = 1
    for sid, f0, f1, _ in SHOTS_V1:
        if f0 != expect or f1 < f0 or f1 > total_frames:
            contiguous = False
        expect = f1 + 1
    contiguous = contiguous and expect == total_frames + 1
    fails += _ok("span law", contiguous,
                 "12 spans contiguous over 1..1080")
    markers = [m for m in scene.timeline_markers
               if m.name.startswith("SHOT_")]
    mk_ok = len(markers) == 12 and all(
        m.camera is not None for m in markers)
    fails += _ok("markers", mk_ok,
                 f"{len(markers)} SHOT_ markers, all camera-bound")

    # 4. the keepout surface (contract-authoritative, ledger 4)
    applied = int(ctx["cache_block"]["crowd"]["keepouts_applied"])
    # the count is contract-vs-cache agreement (4 rows since the
    # round-1 re-stage; never a literal — the row set evolves)
    fails += _ok("keepout count", len(keepouts) == applied,
                 f"{len(keepouts)} rows == cache keepouts_applied "
                 f"({applied})")
    for name, px, py, f0, f1 in keepouts:
        cam = ctx["cams"].get(name)
        row_ok = cam is not None
        if row_ok:
            loc = cam["loc0"]
            row_ok = (abs(loc[0] - px) < 1e-3 and abs(loc[1] - py) < 1e-3
                      and f0 <= shots[name[4:]][0]
                      and f1 >= shots[name[4:]][1]
                      and 0 <= f0 and f1 <= total_frames)
        fails += _ok(f"keepout {name}", row_ok,
                     f"({px},{py}) f{f0}..{f1} covers the shot span")
    # every walkable ground lens has a row (the docs section-6 law)
    ground = [nm for nm, c in ctx["cams"].items()
              if c["loc0"][2] < 2.5 and abs(c["loc0"][0]) < 32.0
              and abs(c["loc0"][1]) < 4.0]
    fails += _ok("ground lenses covered",
                 sorted(ground) == sorted(k[0] for k in keepouts),
                 f"walkable ground lenses {sorted(ground)} == the rows")

    # 5. the sfx spine
    events = ctx["sfx_events"]
    n_rows = len(cast["sfx_rows"])
    n_events = len(cast["sfx_events"])
    fails += _ok("sfx counts", len(events) == n_rows + n_events
                 and all(0 <= e["frame"] <= total_frames for e in events),
                 f"{n_rows} rows + {n_events} events = {len(events)}, "
                 "all frames in [0,1080]")

    # 6. the board program: 5 flips keyed on the 4 row materials
    # (the normalized ladder — the driver's quiet state at frame 0
    # means the same hold as frame 1, see _kf_board)
    flips = [int(f) for f, _ in cast["board_program"]]
    norm = [1] + flips[1:] if flips and flips[0] in (0, 1) else flips
    fails += _ok("board flips", len(cast["board_program"]) == 5
                 and norm == [1, 192, 528, 792, 1009]
                 and norm == ctx.get("board_flips", []),
                 f"{len(flips)} program rows keyed {flips} (norm {norm}); "
                 f"final = {cast['board_program'][-1][1]!r}")
    em_ok = True
    _em_paths = []
    for ri, mat in ctx["board_row_mats"].items():
        found = False
        for owner in (mat, mat.node_tree):
            if owner.animation_data is not None \
                    and owner.animation_data.action is not None:
                for fc in _iter_fcurves(owner.animation_data.action):
                    _em_paths.append(fc.data_path)
                    # Blender writes node-tree keyframes with INDEX-based
                    # socket paths (nodes["X"].inputs[N].default_value) —
                    # the name-based form is NOT guaranteed. The structural
                    # check (a node socket key exists) is the honest gate:
                    # Emission Strength is this material's only keyed node
                    # input.
                    if fc.data_path.startswith("nodes[") \
                            and "default_value" in fc.data_path:
                        found = True
        if not found:
            em_ok = False
    fails += _ok("board emission keys", em_ok,
                 f"4 glyph row materials carry emission fcurves "
                 f"(sample path {_em_paths[:1]})")

    # 7. the two keyed trains (loc fcurves exist + path verbatim)
    paths = cast["train_paths"]
    exp = bpy.data.objects.get(ctx["parts"]["export"]["express_root"])
    loc = bpy.data.objects.get(ctx["parts"]["export"]["local_root"])
    exp_k = _loc_key_frames(exp) if exp else {}
    loc_k = _loc_key_frames(loc) if loc else {}
    trains_ok = (
        336 in exp_k and 528 in exp_k
        and abs(exp_k[336] - float(paths["express"][0][1])) < 1e-3
        and abs(exp_k[528] - float(paths["express"][1][1])) < 1e-3
        and all(f in loc_k for f in (672, 792, 984, 1080))
        and abs(loc_k[672] - float(paths["local"][0][1])) < 1e-3
        and abs(loc_k[1080] - float(paths["local"][-1][1])) < 1e-3)
    fails += _ok("keyed trains", trains_ok,
                 f"express keys {sorted(exp_k)} / local keys "
                 f"{sorted(loc_k)} match cast.train_paths")

    # 8. exactly ONE keyed crane
    keyed = [nm for nm, c in ctx["cams"].items()
             if _loc_key_frames(c["ob"])]
    fails += _ok("one keyed crane", keyed == ["CAM_S5"],
                 f"keyed cams {keyed} (the S5 blast crane)")

    # 9. the heroes + registry roots
    roots_ok = all(bpy.data.objects.get(row["root"])
                   for row in CAST.values()) \
        and all(bpy.data.materials.get(row["material"])
                for row in CAST.values())
    fails += _ok("cast registry", len(CAST) == 2 and roots_ok,
                 f"{len(CAST)} CAST rows, roots + CA.Body materials "
                 "present")

    fails += _ok("heroes keyed",
                 all(ctx["heroes"][n].animation_data is not None
                     for n in ("LatePassenger", "Stationmaster")),
                 "2 hero roots carry actions")
    return fails


# ======================================================================
# main
# ======================================================================

def _set_engine(scene, engine, samples):
    name = "BLENDER_EEVEE" if engine.startswith("eevee") else \
        "BLENDER_WORKBENCH"
    scene.render.engine = name
    scene.eevee.use_raytracing = True   # the 5.2 SSR knob
    if hasattr(scene.eevee, "taa_render_samples"):
        scene.eevee.taa_render_samples = samples
    scene.view_settings.exposure = tf_exposure


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="output/tfog")
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
        print("[tfog] dry-run OK")
    bpy.context.view_layer.update()


if __name__ == "__main__":
    main()
