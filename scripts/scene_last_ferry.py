"""scene_last_ferry.py -- LAST FERRY (tferry_1): the night-pier
converge film. D-TF1 REV-2; the scene module of the tdawn shape
(mapped vocabulary UPPERCASE only; internal wiring lowercase).

Session-14 slice: world + cameras + heroes + title + emission keys;
the film is COMPLETE end-to-end (bake driver -> flow strip -> shot
cams -> EEVEE night pass -> export tferry_1 -> staged). The crowd
branch auto-detects the bake cache (absent -> pre-bake looks work
with the anchors at their authored grid).
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
    ("S5",  349,  444, "head-on: the Latecomer's run reads down the east rail"),
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
    # fix-wave-2 eyepass round 2 (S2: the flip read ILLEGIBLE at 28mm
    # from 5.9 m — the story beat IS the sign. Closer + 45mm: the
    # board fills the upper frame, the queue context below it)
    ("CAM_S2",  (1.4, 7.2, 2.4), (1.4, 7.2, 2.4), 45,
     (3.0, 2.9, 2.2), False, 0.0),
    ("CAM_S3",  (-2.0, 30.0, 5.0), (-2.0, 30.0, 5.0), 30,
     (0.2, 10.0, 1.0), False, 0.02),
    # S4: pulled back + wider (38mm, cam north at y38) -- the entry
    # reads WITH depth (the 45mm tight row buried him among beige backs:
    # session-16 probe round, the flood class again), the amber Deckhand
    # visible top-center, the band small-but-glowing under EEVEE
    ("CAM_S4",  (4.0, 38.0, 2.8), (4.0, 38.0, 2.8), 38,
     (4.9, 27.0, 1.6), False, 0.015),
    # S5: the OUTBOARD head-on -- he runs INTO the lens down the east
    # rail (the raised lateral buried him in the capsule flood: probe
    # round g1-g4, 8 candidates; S5g full-body no-pole cert)
    ("CAM_S5",  (8.4, 8.2, 2.9), (8.4, 8.2, 2.9), 42,
     (4.8, 17.0, 1.0), False, 0.025),
    # S6: the camera stood INSIDE the queue aiming at the EMPTY throat;
    # pulled west+north so the Deckhand AND the pile read together
    # fix-wave-2 eyepass round 2 (S6: the Deckhand read ISOLATED — the
    # eye-level vantage showed the pile as sparse 'background figures'.
    # Raised + on the queue axis: the pile's density reads as SHAPE
    # filling the south frame, the Deckhand holding beyond it)
    ("CAM_S6",  (-1.8, 7.8, 4.2), (-1.8, 7.8, 4.2), 40,
     (0.4, 1.8, 1.0), False, 0.018),
    # S7: the OUTBOARD SE cam -- the Latecomer's hold reads against the
    # streaming crowd (the inboard NW view buried him among bollards)
    ("CAM_S7",  (6.6, 5.2, 1.9), (6.6, 5.2, 1.9), 35,
     (4.8, 8.2, 1.0), False, 0.03),
    # S8: the pairing shot -- Deckhand (0.3,0.7) + Latecomer (4.8,8)
    # BOTH read from the raised outboard SE (the west deck edge view
    # buries the Deckhand behind the pile: eye round 3)
    # fix-wave-2 eyepass round 2 (S8: the Latecomer still read small
    # and undefined — closer to his rail hold + 36mm so he carries the
    # foreground-right, the Deckhand's hold mid-left)
    ("CAM_S8",  (6.8, 9.8, 3.0), (6.8, 9.8, 3.0), 36,
     (2.0, 3.6, 1.05), False, 0.012),
    # S9: the OUTBOARD cam ON THE GATE (the prior aim drifted north of
    # the subject and the EEVEE night drowned it -- nothing read): the
    # gate + the Latecomer's crossing centered, the Deckhand beyond
    # fix-wave-2 eyepass round 2 (S9: the rail line crossed the view
    # obscuring the lower bodies + the crossing read distant. Higher
    # (shoots OVER the rail) + 38mm + the aim on his f735 crossing
    # point (4.1, 7.1), not his f700 hold)
    ("CAM_S9",  (10.5, 4.2, 4.6), (10.5, 4.2, 4.6), 38,
     (4.0, 7.2, 1.0), False, 0.0),
    # fix-wave-2 eyepass round 2 (S10: the vantage stood EAST of the
    # throat BARRIER looking over its top edge — half the frame was
    # the barrier's dark slab and the heroes read as 'floating
    # spheres' beyond it. NEW vantage: down the QUEUE AXIS from the
    # north — the ray crosses the barrier line INSIDE the 2 m throat
    # gap (x 0.28 at y0.7), the stepped-aside Deckhand frames the
    # sealed gap, the Latecomer beyond on the ramp, the quieted queue
    # as foreground depth)
    ("CAM_S10", (0.9, 4.8, 2.4), (0.9, 4.8, 2.4), 40,
     (0.25, 0.5, 1.1), False, 0.0),
    # the CRANE (S11/S12): loc AND aim keyed -- over the outboard
    # margin/water (REV-2 F8); rises 3.2 -> 11.6 while drifting south
    ("CAM_S11", (-8.6, 18.0, 3.2), (-9.2, 10.0, 11.0), 30,
     (0.5, 10.0, 0.5), False, 0.0),
    ("CAM_S12", (-9.2, 10.0, 11.0), (-8.8, 8.0, 11.6), 35,
     (0.0, 1.0, 1.2), False, 0.0),
]

CAST = {
    "Deckhand": {"root": "Deckhand.Root", "material": "CA.Body.Deckhand",
                 "role": "holds the two-meter throat"},
    "Latecomer": {"root": "Latecomer.Root",
                  "material": "CA.Body.Latecomer",
                  "role": "sprints the pier edge to make the crossing"},
}

# BEATS rows are (label, shot_id, t_seconds) -- the exporter maps
# label<-b[0], shot<-b[1], kind<-b[2]... (verified against
# export_previz_package.py's beat mapping; the tuple ORDER below is
# (label, shot, frame-at-shot-start))
BEATS = [
    # the exporter's story shape: (id, t_seconds, label) -- t =
    # (f-1)/24 for the shot's opening frame (the float(b[1]) law)
    ("calm",       0.0,  "the pier strip at night; a thin drift south"),
    ("boarding",   3.5,  "the kiosk board flips to BOARDING (the call)"),
    ("surge",      7.0,  "the surge ignites: the far bands pour south"),
    ("latecomer",  11.0, "the Latecomer enters at the pier head, breaks into a run"),
    ("the_line",   14.5, "the Latecomer's run down the east rail line"),
    ("the_choke",  18.5, "the Deckhand holds the throat; the crowd piles"),
    ("bollards",   22.0, "the Latecomer holds at the east rail; the stream jostles past"),
    ("seen",       26.0, "the Deckhand sees the Latecomer; holds the gap open"),
    ("the_gap",    30.0, "the beat: through the maintenance gate, the crew wave"),
    ("sealed",     34.0, "the throat sealed; the pier quiets"),
    ("rising",     38.0, "the crane rises: the Latecomer aboard, the windows move"),
    ("title",      42.0, "LAST FERRY over the receding windows"),
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
    }                                       # was teal; different callout
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
    mat = make_material("TF.TitleCard", (1.0, 0.88, 0.70), 0.4,
                        emission_color=(1.0, 0.88, 0.70),
                        emission_strength=0.9)   # under the 1.0 tan cap
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
    head (4.9,34) f265 -> the east rail line (4.8,8) f500 -> holds
    (idle sway) -> the maintenance gate f721-760 -> the choke approach
    -> through the throat -> the ferry ramp by f900. fix-wave-1: the
    rail-line cut f348->444 read 4.5 m/s (18 m in 4 s); the same 18 m
    over f348->500 reads 2.8 m/s -- he now arrives mid-S6 (off-camera:
    CAM_S6 frames the throat) and is on the rail hold for S7's
    tracker."""
    dh = ctx["heroes"]["Deckhand"]
    lc = ctx["heroes"]["Latecomer"]
    _kf(dh, 1, loc=(0.30, 0.70))
    _kf(dh, 760, loc=(0.30, 0.70), rot_z=0.0)
    _kf(dh, 800, loc=(-0.45, 0.85), rot_z=0.5)    # steps aside
    _kf(dh, 1080, loc=(-0.45, 0.85), rot_z=0.5)
    for ob in (dh, lc):
        _bezier(ob)
    run = [(265, (4.90, 34.0)), (348, (4.85, 26.0)), (500, (4.80, 8.0)),
           (700, (4.80, 8.0)), (760, (3.40, 6.2)), (816, (0.60, 1.4)),
           (880, (0.20, -1.1)), (900, (0.05, -2.2)), (1080, (0.05, -2.2))]
    for f, loc in run:
        _kf(lc, f, loc=loc)
    # fix-wave-1 D2: the Latecomer never carried a rotation channel
    # (his yaw froze at the spawn pi for the whole film) -- seed the
    # authored spawn yaw once so face_tangent has the fcurve to rewrite
    lc.rotation_euler = (0.0, 0.0, math.pi)
    lc.keyframe_insert(data_path="rotation_euler", index=2, frame=265)
    _bezier(lc)
    # fix-wave-1 D2: re-derive facing from the path tangents (the
    # tdawn pattern) -- the Latecomer is the mover (full tangent on
    # his pier run); the Deckhand the watcher (only his 0.45 m/s
    # step-aside moves, and it sits under the 0.55 gate so his
    # authored holds stay)
    import humanoid_crowd as _HC
    _HC.face_tangent(lc, min_mps=0.45)
    _HC.face_tangent(dh, min_mps=0.55)


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
    # the SIGN rows are CLOSE-UP subjects: 1.9 clipped to a pastel
    # pink monolith in the S2 EEVEE probe (the night ceiling is
    # distance-dependent -- the far cyan BAR holds 1.9, the near board
    # rows cap ~1.1-1.3). Row 1 (the line name) rides modest; row 2 is
    # the FLIP (0.06 -> 1.3 at the call). L-TF1 measured.
    _em_keys(mats["neon_mag"], [(1, 0.5), (1080, 0.5)])
    _em_keys(mats["sign_flip"], [(1, 0.06), (85, 1.3), (1080, 1.3)])
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
    scene.render.fps = FPS      # the exporter stamps the package
                                # timeline from render.fps (do not rely
                                # on the --factory-startup default)
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
    # the exporter's ctx contract (tdawn shape): 'scene' is LOAD-BEARING
    # (export_previz_package.py:2736 reads ctx["scene"])
    return {"scene": scene, "parts": parts, "heroes": heroes,
            "cams": cams, "chars": chars, "title": title}


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
    they stand -- so they are authored OUTBOARD (x +-7.5, past the
    rail line: dressing-plausible statics on the margin; a review
    round caught the first draft parking them mid-grid where agents
    path, undeclared)."""
    from tdawn_actors import (build_commuter_mesh, new_anchored_obj,
                              commuter_material)
    lib = build_commuter_mesh("TF.CommuteLib",
                              mat_body=commuter_material(0))
    # PARK the library mesh outside every frustum + hide_render (the
    # tdawn law: the unparked source stood in-frame as a WHITE figure)
    lib.location = (0.0, 45.0, -2.5)
    lib.hide_render = True
    crowd = []
    # 120 anchors, a 12-wide x 10-row grid spanning y 32 -> 11 (rows
    # 0-4 in the far band, 5-9 in the mid band) -- PRE-BAKE dressing
    # only (bake2 re-keys every one of them from tick 0)
    for i in range(120):
        row = i // 12
        col = i % 12
        y = 32.0 - row * 2.1 if row < 5 else 20.0 - (row - 5) * 2.1
        x = ((col - 5.5) * 0.95)
        crowd.append(new_anchored_obj(
            f"Zed.{i + 1:04d}", lib, (x, y, 0.0),
            yaw=math.pi))       # facing south, toward the throat
    chase = []
    for i in range(12):
        if i in (2, 5, 8):
            # the RB slots: parked OUTBOARD (the rail line is at
            # +-6.2; x 7.5 is crowd-free by construction) -- they stay
            # motionless post-bake and must never stand mid-crowd
            x = 7.5 if i == 5 else -7.5
            y = 30.0 + (i // 6) * 2.0
        else:
            x = ((i % 6) - 2.5) * 1.3
            y = 30.0 + (i // 6) * 2.0
        chase.append(new_anchored_obj(
            f"Zed.ChaseP{i + 1:02d}", lib, (x, y, 0.0), yaw=math.pi))
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
    if os.environ.get("TFERRY_HUMANOID") == "1":
        _humanoid_layer(ctx)
    return ctx["crowd_cache"]


def _humanoid_layer(ctx):
    """LAST FERRY, humanized (s25 rollout -- the D6 pattern, the tdawn
    worked example): the 129 cache anchors gain RH x_bot rig
    assemblies; the 2 keyed heroes gain UAL mannequins. Env-gated
    (TFERRY_HUMANOID=1) so tferry_1 rev2 stays reproducible
    byte-for-byte.

    POP_PLAN (the ordinal law: zones in CONTRACT order, chase LAST --
    the bridge's ingest order; tferry_contract ZONES rows 44/40/36,
    the verbatim-129 law 120 zone + 9 tail):
      zone0 44 deck_fore ink / zone1 40 deck_mid drab /
      zone2 36 deck_aft slate / chase 9 crew oilskin amber-drab
      (group identity, the film's previz semantics).
    """
    import humanoid_crowd as HC
    fam = HC.crowd_family("rh_xbot")
    groups = [("deck_fore", 44, (0.16, 0.18, 0.22)),
              ("deck_mid", 40, (0.24, 0.23, 0.21)),
              ("deck_aft", 36, (0.20, 0.22, 0.24)),
              ("crew", 9, (0.35, 0.30, 0.18))]
    agent_group = []
    for gi, (_, cnt, _rgb) in enumerate(groups):
        agent_group.extend([gi] * cnt)
    if len(agent_group) != 129:
        raise RuntimeError(
            f"_humanoid_layer: POP_PLAN split {len(agent_group)} != pin 129")
    gt = {"groups": [(c, rgb) for _, c, rgb in groups],
          "agent_group": agent_group}
    rep = HC.bind_crowd(ctx, fam, group_tint=gt)
    HC.motion_gates(ctx, rep["reps"], walk_cycle=rep["walk_cycle"])
    ctx["humanoid"] = rep
    # the UAL principals: Deckhand (amber) + Latecomer (crimson) -- the
    # identity colors from _heroes (:156-157), the branch-a law
    UAL_SCALE = 1.75 / 1.589
    # fix-wave-1 D2: clip=None -> AUTO (path-speed matched; the
    # Latecomer sprinted the pier on a standing idle before -- the
    # moonwalk class; the Deckhand's step-aside reads as a slow walk)
    pr = HC.bind_principals(ctx, {
        "Deckhand": (None, UAL_SCALE, None),
        "Latecomer": (None, UAL_SCALE, None)})
    ctx["humanoid_principals"] = HC.ride_principals(ctx, pr, {
        "Deckhand": (0.85, 0.42, 0.05),
        "Latecomer": (0.62, 0.07, 0.10)})


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
    # the app's sfx contract: {name|kind, frame} objects -- the "id"
    # key was dropped 3/3 by the app's loader (the in-app find)
    events = [
        {"name": "chime", "frame": 85, "label": "boarding chime"},
        {"name": "clang", "frame": 721, "label": "gangway clang"},
        {"name": "horn", "frame": 913, "label": "departure horn"},
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
    # s27 D2 hoist: the engine-conditional world tune (sky 0.012/0.12,
    # practicals x3.5) reads scene.render.engine at BUILD time — set
    # it here so build_world sees the true engine (the render-time
    # _set_engine re-applies idempotently).
    from blender_kit import normalize_engine_id
    scene.render.engine = normalize_engine_id(args.engine)
    ctx = build_scene()
    animate(ctx, with_crowd=not args.skip_crowd)
    # the caller owns the dir (the tdawn law; the stills scripts pass
    # --output <stillwork-dir> directly)
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
        print("[tferry] dry-run OK")
    bpy.context.view_layer.update()


def _set_engine(scene, engine, samples):
    # s27 engine-map law (DESIGN_engine_map_s27 D1/D2, audited REV-2):
    # the old two-way map sent --engine cycles to WORKBENCH — the
    # stills lane silently rendered light-blind workbench frames (the
    # 4-film look failure's root cause). Cycles branch = the tform
    # canonical (bounded bounces, CPU, denoise). The exposure tail
    # stays ENGINE-UNCONDITIONAL (the certified look rides it).
    engine = (engine or "").lower()
    if engine.startswith("cycles"):
        scene.render.engine = 'CYCLES'
        scene.cycles.samples = int(samples)
        scene.cycles.use_denoising = True
        scene.cycles.device = 'CPU'
        scene.cycles.max_bounces = 4
        scene.cycles.transmission_bounces = 2
        scene.cycles.volume_bounces = 1
        print(f"[tferry] engine={scene.render.engine} samples={samples} "
              "denoise on CPU (s27 engine-map law)")
        return
    name = "BLENDER_EEVEE" if engine.startswith("eevee") else \
        "BLENDER_WORKBENCH"
    scene.render.engine = name
    if engine.startswith("eevee"):
        scene.eevee.use_raytracing = True   # L-TF3: the 5.2 SSR knob
        if hasattr(scene.eevee, "taa_render_samples"):
            scene.eevee.taa_render_samples = samples
    scene.view_settings.exposure = 0.3  # L-TF4 fixed at +0.3


if __name__ == "__main__":
    main()
