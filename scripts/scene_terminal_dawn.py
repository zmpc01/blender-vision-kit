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

_lab = Path("/home/z/lab")
_sib = _lab / "blender-escape-previz" / "scripts"
_previz_scripts = os.environ.get(
    "TPREVIZ_SCRIPTS",
    str(_sib) if _sib.is_dir() else "/home/z/work/blender-escape-previz/scripts")
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
    # audit-round honesty edit: the horde is HELD at the sealed vault
    # -- the hall SETTLES (mean crowd speed 0.68 -> 0.14 m/s), it never
    # empties (the vault seals the only exit; an empty hall would be
    # the WRONG story). The still frame moved 1002 -> 1008 (the
    # pull-back's very end = the most-settled moment in-window).
    ("S11", 913,  1008, "pull-back: dawn floods the settling hall -- the surge spent, the horde held at the seal"),
    ("S12", 1009, 1080, "title frame: TERMINAL DAWN over the still hall"),
]

# (name, loc0, loc1, lens_mm, aim, parent_jeep, shake_amp)
# parent_jeep is the escape-film vocabulary (no jeep here -- always
# False; the mover stays False so TRACK_TO aiming is live on every cam).
# iter-2: S5/S7/S10 became STATIC pans (a dolly exits its own keepout
# circle -- review), S1 cleared the y=-4 roof arch off the lens, S3
# aim lifted off the floor smear, S6 raised above crowd heads, S8
# re-aimed at the Master/gate (the old north aim showed an empty hall),
# S9 aim centered on the throat, S10 pulled back to frame the seal.
CAMS_V3 = [
    ("CAM_S1",  (7.5, -6.0, 7.6), (6.0, -4.2, 7.0), 24,
     (0.0, 12.0, 1.2), False, 0.0),
    # fix-wave-2 eyepass (S2 re-frame: the 38mm close-up had no
    # environmental context and no crowd — pull back + widen so the
    # board sits in the upper frame over the concourse's early flow)
    ("CAM_S2",  (3.2, 15.5, 2.6), (3.2, 15.5, 2.6), 28,
     (-0.3, 29.0, 5.0), False, 0.012),
    ("CAM_S3",  (0.0, -5.5, 8.4), (0.0, -4.8, 8.0), 28,
     (0.0, 15.0, 1.3), False, 0.0),
    # fix-wave-2 eyepass (S4 re-frame: the north vantage put a
    # colonnade pillar across the Runner's far-end entry — a 3/4 from
    # the NW keeps him unobstructed mid-frame with the flow context)
    ("CAM_S4",  (-6.5, 27.0, 3.2), (-6.5, 27.0, 3.2), 34,
     (1.0, 19.5, 1.1), False, 0.02),
    # session-14 reframe v2 (user comment on tdawn_2 S5: "the model
    # looks very strange" — v1's west vantage fought the x=-7 colonnade
    # line AND missed the Runner (he walks y 15.1→8.9 while S5 spans
    # f349-444; the v1 aim sat 7m north of his f396 position). v2: a
    # NORTH vantage straight down the stream axis (x≈0.3, no column
    # crossing), the far-glow gate as backdrop, the crowd streaming
    # away below, the teal Runner mid-frame at his f396 (0.91, 11.3).
    # fix-wave-2 eyepass (S5 re-frame: the v2 north vantage read as a
    # centered frontal — the intent is LATERAL. The east-side vantage
    # (x=10.5, inside the hall, 1.5m off the east wall) looks due
    # west ACROSS the stream: the Runner mid-frame crossing laterally,
    # the west colonnade + far glow as depth behind him)
    ("CAM_S5",  (10.5, 11.5, 2.2), (10.5, 11.5, 2.2), 40,
     (0.5, 11.5, 1.1), False, 0.025),
    # fix-wave-2 eyepass round 2 (S6 re-aim: the Master read at the
    # frame EDGE — the aim sat on the throat, 1.9 m right of him. Aim
    # between the Master and the gate so he reads left-third with the
    # pile depth beyond; 42mm for the pile context)
    ("CAM_S6",  (-5.2, 7.0, 2.6), (-5.2, 7.0, 2.6), 42,
     (-1.0, 1.5, 1.3), False, 0.018),
    # fix-wave-2 eyepass (S7 re-frame: the west vantage lost the
    # stumble in the crowd — closer + tighter on the Runner's dip at
    # his f580 position, the low tracker angle kept)
    # fix-wave-2 eyepass round 2 (S7: STILL flagged — the aim targeted
    # the dip key (f535) but the STILL rendered f580 where the Runner
    # had already recovered 1.7 m south, off-aim and crowd-masked.
    # The still frame now renders the dip itself (f540) and the camera
    # closes to 4.4 m so the low tracker reads him big mid-frame)
    ("CAM_S7",  (-3.8, 6.6, 1.6), (-3.8, 6.6, 1.6), 50,
     (-0.5, 4.6, 0.9), False, 0.034),
    ("CAM_S8",  (-4.5, 4.0, 2.5), (-4.5, 4.0, 2.5), 32,
     (0.7, 1.1, 1.2), False, 0.012),
    # fix-wave-2 eyepass (S9 re-frame: too low/wide, the dive read
    # flat — a 3/4 from behind-right, tighter, the vault throat
    # beyond the arc peak)
    # fix-wave-2 eyepass round 2 (S9: STILL flagged static + the Master
    # read as a 'duplicate' — both figures crammed at the old aim.
    # Lower + closer on the arc peak (dz 0.38 mid-air at f750) so the
    # diving pose carries the frame; the Master falls to the left
    # third watching, the closing doors beyond)
    ("CAM_S9",  (2.8, 2.8, 1.6), (2.8, 2.8, 1.6), 40,
     (0.5, -0.35, 1.0), False, 0.022),
    # session-14 reframe (user comment on tdawn_2 S10: "spatial
    # separation unclear — lack of even a wall"; the probe named the
    # center ray ON TD.GateTunnelL — the frame was centered on the
    # tunnel EDGE with the throat glow filling the opening as a blank
    # screen). New: a shallower 3/4 from the SW so the gate WALL PLANE
    # reads with the SEALED doors + the hot seal-edge slit in frame;
    # tdawn_world's new pilasters + exit sign give the wall scale.
    # fix-wave-2 eyepass (S10: raise the vantage — the SW 3/4 read
    # cluttered by foreground geometry; looking DOWN over it centers
    # the sealed doors + the seal-edge slit)
    # fix-wave-2 eyepass round 2 (S10: STILL flagged — the raised
    # distant vantage 'diminishes the vault'. Lower + closer from the
    # NW, inside the hall: the sealed vault face carries the frame,
    # the Master small before it, the held crowd the foreground
    # texture — the 'quiets' read is the scale contrast)
    ("CAM_S10", (-5.8, 2.8, 2.8), (-5.8, 2.8, 2.8), 32,
     (0.2, 0.5, 1.4), False, 0.0),
    # fix-wave-2 eyepass (S11 re-aim: the crane looked north OVER the
    # held crowd filling the foreground — the intent is the EMPTY
    # hall. Aim deeper north + end higher so the held crowd reads
    # small at the gate and the emptied concourse carries the frame)
    # fix-wave-2 eyepass round 2 (S11: the crane PATH was right but the
    # still rendered mid-pull (f960) while the hall was still thinning
    # — the empty-hall payoff is the crane's HIGH END. The still frame
    # now renders f1002; the camera itself is UNCHANGED)
    ("CAM_S11", (2.0, 10.0, 2.2), (6.5, 3.0, 9.5), 30,
     (0.0, 12.0, 1.8), False, 0.0),
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
    ("stumble",    22.4, "the Runner is driven to a knee, nearly lost"),
    ("seen",       23.0, "the Master sees the Runner; holds the vault"),
    ("the_dive",   31.2, "the Runner dives through the sealing vault"),
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
    (21.20, -0.4, 5.4, 0.0, 160.0),
    (22.30, -0.5, 4.7, -0.18, 166.0),  # the stumble dips (S7's window)
    (22.95, -0.4, 4.3, -0.02, 163.0),
    (23.80, 0.2, 3.6, 0.0, 150.0),
    (28.00, 1.1, 1.3, 0.0, 118.0),    # holds at the line, screen-left
                                      # of the Master (S8 reads both)
    (30.40, 1.1, 1.3, 0.0, 108.0),
    (31.21, 0.4, -0.35, 0.38, 95.0),  # the dive arc peak EXACTLY f750
                                      # (the S9 still frame; inside the
                                      # portal throat)
    (31.90, 0.2, -1.85, 0.0, 90.0),   # through; doors seal behind
                                      # (y -1.85 clears the new glow
                                      # wall at -1.41)
    (45.00, 0.2, -1.85, 0.0, 90.0),
]

_master_path = [
    (0.0, -1.9, 1.7, 0.0, 96.0),      # gate-left, watching the hall
    (21.0, -1.9, 1.7, 0.0, 96.0),
    (23.0, -0.9, 1.2, 0.0, 80.0),     # steps out to read the surge
    (27.0, 0.4, 0.9, 0.0, 60.0),      # to the throat, arm to the crowd
    (32.6, 0.4, 0.9, 0.0, 60.0),      # holds it through the dive
    (34.5, -0.6, 0.9, 0.0, 75.0),     # back as the doors close
    (45.0, -0.6, 0.9, 0.0, 75.0),
]

# the vault seal: doors slide from parked (x +/-5.1) to closed (x +/-1.7)
# iter-2: f730-780 -- the Runner crosses the door plane ~f746 through a
# ~4.6 m gap and the f750 still reads a VISIBLY closing portal (the old
# 760/812 sealed too late: the representative frames showed a wall)
_door_open_x = 5.1
_door_closed_x = 1.7
_seal_f0 = 730          # doors start closing (t 30.4 s, the dive commit)
_seal_f1 = 780          # sealed
_title_f0 = 1009        # the title sting: the card lights up here

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

    iter-2 (G1 fix): the per-agent PALETTE lands POST-LOAD (see
    _crowd_kit_branch) -- writing materials here mutated the SHARED
    library datablock (every anchor links the same mesh), collapsing
    all 132 agents to one color. The lib carries palette[0] so
    pre-bake looks still see a commuter material.
    """
    from tdawn_actors import (build_commuter_mesh, commuter_material,
                              new_anchored_obj, BRIDGE_HEIGHT_M)
    lib = build_commuter_mesh("TD.CommuteLib", BRIDGE_HEIGHT_M,
                              mat_body=commuter_material(0))
    lib.location = (0.0, -40.0, 0.0)     # park the library mesh off-set
    crowd = []
    for i in range(120):
        crowd.append(new_anchored_obj(
            f"Zed.{i + 1:04d}", lib,
            (((i % 12) - 5.5) * 1.5, 8.0 + (i // 12) * 1.45, 0.0),
            yaw=math.radians(180.0)))
    chase = []
    for i in range(12):
        chase.append(new_anchored_obj(
            f"Zed.ChaseP{i + 1:02d}", lib,
            (((i % 6) - 2.5) * 1.2, 21.0 + (i // 6) * 2.0, 0.0),
            yaw=math.radians(180.0)))
    return {"crowd": crowd, "chase": chase}


def _title_card(scene):
    """The TERMINAL DAWN title card (S12): text converted to mesh
    (curves do not export to glTF), warm cream emissive keyed 0 ->
    0.55 at the sting (f1009), hide_render keyed False there too so
    it photobombs no earlier shot (S5/S11 both have it in frustum).
    The GLB keeps the card visible-but-dark (material emission does
    not export to glTF) -- the stills are authoritative for the
    sting."""
    from tdawn_actors import make_material
    # 0.40: the Bfont advance is ~0.91 em/char (measured in probe-1:
    # 0.55 gave a 6.5 m line that clipped "TE" off CAM_S12's 6.3 m
    # frame) -- 0.40 -> ~4.7 m = 75% of frame width
    size = 0.30
    tx, ty, tz = 2.2, 10.6, 3.2
    mat = make_material("TD.TitleCard", (1.0, 0.88, 0.70), 0.4)
    crv = bpy.data.curves.new("TD.TitleCard", type="FONT")
    crv.body = "TERMINAL DAWN"
    crv.size = size
    crv.align_x = "CENTER"
    crv.align_y = "CENTER"
    crv.extrude = 0.02
    ob = bpy.data.objects.new("TD.TitleCard", crv)
    ob.location = (tx, ty, tz)
    scene.collection.objects.link(ob)
    # face CAM_S12's dolly END pose (the still frame). CR-TD2 P2: a
    # live lookup reads build-time loc0 (8.0,18.0) — the dolly keys
    # don't exist yet — and mis-aims the card ~9-10°; pin the end pose.
    cx, cy = 7.4, 15.5
    nx, ny = cx - tx, cy - ty
    # rx=90 maps the text normal (+Z) to -Y; rz then aims it at the
    # cam: Rz*(0,-1,0) = (sin rz, -cos rz) = n/|n|  =>  rz = atan2(nx,-ny)
    ob.rotation_euler = (math.pi / 2, 0.0, math.atan2(nx, -ny))
    # convert text -> mesh ALONE (convert bakes every selected object)
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.convert(target="MESH")
    ob.data.materials.append(mat)
    # the sting (session-14, the user's tdawn_2 S12 comment: the card is
    # "constantly visible" in the app — keyframed hide_render does NOT
    # export to glTF (the s35 round-6 finding, user-visible now). The
    # export-safe pattern is SCALE keys: TRS animation survives the
    # exporter, and a 0.001-scale card renders as nothing in EEVEE too.
    # The emission keys still drive the still-side glow at the sting.
    ob.scale = (0.001, 0.001, 0.001)
    ob.keyframe_insert(data_path="scale", frame=1)
    ob.keyframe_insert(data_path="scale", frame=_title_f0 - 1)
    ob.scale = (1.0, 1.0, 1.0)
    ob.keyframe_insert(data_path="scale", frame=_title_f0)
    ob.keyframe_insert(data_path="scale", frame=1080)
    return ob


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
    # THE FACTORY-SCENE PURGE (the probe-3 law): `--factory-startup`
    # loads Blender's default Cube + Camera + Light — the cube sat in
    # the gate mouth in every probe render and the default 1000 W point
    # light polluted the exposure. Previous sandboxes were masked by a
    # saved cube-free startup file; a fresh sandbox must purge.
    for ob in list(scene.objects):
        if ob.name.split(".")[0] in ("Cube", "Camera", "Light"):
            bpy.data.objects.remove(ob, do_unlink=True)
    scene.render.fps = FPS
    scene.frame_start = 1
    scene.frame_end = total_frames

    import tdawn_world
    world = tdawn_world.build_world(scene)
    cams = _cameras(scene)
    chars = {"zombies": _anchors(scene)}
    heroes = _heroes(scene)
    title = _title_card(scene)

    # view-layer SYNC duty (L19 law family): the last-linked objects
    # (Runner.Root measured) can lag the view-layer object list -- the
    # exporter's #29 sweep then false-positives them as view-layer
    # excluded and gate 24 rejects the package (refs-without-node).
    # One forced update closes it scene-side (F-TD5; the kit-side fix
    # belongs in render_hidden_objects -- see the frictions doc).
    bpy.context.view_layer.update()
    return {"scene": scene, "world": world, "cams": cams,
            "chars": chars, "humans": heroes, "title": title}


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
    # fix-wave-1 D2: re-derive facing from the path tangents — the
    # hand-authored yaws drifted up to ~150deg from their own tangents
    # (the Runner is a mover: full tangent; the Master a watcher: only
    # his walking segments re-face, the gate-watching holds stay)
    import humanoid_crowd as _HC
    _HC.face_tangent(runner, min_mps=0.45)
    _HC.face_tangent(master, min_mps=0.55)
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
    # S5: the aim target tracks the Runner with a 0.35 s LEAD (the
    # pan frames where he is GOING, not where he was; x 1.2 keeps the
    # stream mass on the lens)
    t5 = cams["CAM_S5"]["tgt"]
    for f in range(349, 445, 6):
        t = (f - 1) / FPS
        y = _hero_y_at(t + 0.35)
        t5.location = (1.2, y, 1.2)
        t5.keyframe_insert(data_path="location", frame=f)
    _linear(t5)


def _hero_y_at(t):
    for (t0, x0, y0, _z0, _y0), (t1, x1, y1, _z1, _y1) in zip(
            _hero_path, _hero_path[1:]):
        if t0 <= t <= t1:
            k = 0.0 if t1 == t0 else (t - t0) / (t1 - t0)
            return y0 + (y1 - y0) * k
    return _hero_path[-1][2]


def _em_keys(mat, keys):
    """Keyframe a material's Emission Strength through (frame, value)
    pairs (the single-source pattern: every seal-anchored glow key is
    derived from _seal_f0/_seal_f1 so the retimes cannot drift)."""
    if not (mat and mat.use_nodes):
        return
    bsdf = next(n for n in mat.node_tree.nodes
                if n.type == "BSDF_PRINCIPLED")
    em = bsdf.inputs["Emission Strength"]
    for f, v in keys:
        em.default_value = v
        em.keyframe_insert(data_path="default_value", frame=f)


def _kf_set_pieces(ctx):
    """Gate seal + window glow + board flicker + seal edges + title
    sting (iter-2: all seal-anchored keys single-sourced from
    _seal_f0/_seal_f1)."""
    for d, sx in ((ctx["world"]["gate"]["door_l"], -1.0),
                  (ctx["world"]["gate"]["door_r"], 1.0)):
        d.location.x = sx * _door_closed_x
        d.keyframe_insert(data_path="location", index=0, frame=_seal_f1)
        d.location.x = sx * _door_open_x
        d.keyframe_insert(data_path="location", index=0, frame=_seal_f0)
        d.keyframe_insert(data_path="location", index=0, frame=1)
        _linear(d)

    # far-window incident glow: dawn warmth from f1, the S2 "wrong"
    # pulse (the old keys started at f169 -- the S2 windows sat dead),
    # then the ignition surge
    _em_keys(bpy.data.materials.get("TD.WindowGlow"),
             [(1, 0.35), (85, 0.5), (120, 0.95), (150, 1.15),
              (168, 0.9), (200, 1.3), (_glow_f1, 1.6),
              (900, 1.1), (1009, 0.7), (1080, 0.7)])

    # departure board rows: TWO alternating amber flickers (A/B) so
    # the shimmer is not a uniform strobe; both die at the surge.
    # CR-TD2 P1: the range step is 7, so phase 3 never crossed a block
    # boundary ((f+3)//7 == f//7 for every key) — the A/B sets were
    # IDENTICAL. Phase 7 = exactly one block: always anti-phase.
    f_a, f_b, die = _board_flick
    for nm, phase in (("TD.BoardRowA", 0), ("TD.BoardRowB", 7)):
        keys = [(f, 2.1 if ((f + phase) // 7) % 3 else 0.35)
                for f in range(f_a, f_b, 7)]
        _em_keys(bpy.data.materials.get(nm),
                 keys + [(die, 0.0), (1080, 0.0)])

    # the throat glow (the tunnel's back wall): rises with the seal
    _em_keys(bpy.data.materials.get("TD.ThroatGlow"),
             [(1, 0.28), (625, 0.4), (_seal_f0, 0.6), (_seal_f1, 0.7),
              (912, 0.45), (1009, 0.35), (1080, 0.35)])

    # gate surround: capped at the AgX warm law 0.95 (the old 1.4 key
    # white-clipped the jambs -- the S6 projection-screen read)
    _em_keys(bpy.data.materials.get("TD.GateGlow"),
             [(1, 0.25), (625, 0.5), (_seal_f1, 0.8), (912, 0.6),
              (1080, 0.45)])

    # the seal edges (door leading edges): dim telegraph while parked,
    # HOT through the close (tiny area + brief: 1.3 is inside the
    # measured small-accent tolerance; look-verify the slit)
    _em_keys(bpy.data.materials.get("TD.SealEdge"),
             [(1, 0.25), (700, 0.35), (_seal_f0, 0.9), (_seal_f1, 1.3),
              (830, 0.8), (912, 0.45), (1080, 0.45)])

    # the title sting (the card's hide keys live in _title_card)
    _em_keys(bpy.data.materials.get("TD.TitleCard"),
             [(1, 0.15), (_title_f0, 0.55), (1080, 0.55)])


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

    iter-2 (G1): the commuter PALETTE lands HERE, post-materialize:
    bake_tier2 gives every sim agent a private mesh copy (users==1,
    shape-keyed); the 3 RB-placeholder carts keep the shared lib mesh
    (users>1) and get a copy first. Assigning before this point
    mutated the SHARED library datablock and collapsed the crowd to
    one color (the clone-army read in every tdawn_1 still).
    """
    ctx["crowd_shots"] = _shot_table(SHOTS_V3, CAMS_V3)
    ctx["crowd_tier_pins"] = CROWD_TIER_PINS
    import crowd_kit as _CK
    _CK.loader.load_kit_cache(ctx)
    import crowd_v6 as CV6
    CV6.bake_tier2(ctx)
    _crowd_palette(ctx)
    if os.environ.get("TDAWN_HUMANOID") == "1":
        _humanoid_layer(ctx)
    return ctx["crowd_cache"]


def _humanoid_layer(ctx):
    """TERMINAL DAWN, humanized (s25 rollout — the D6 pattern, the
    tform worked example): the 129 cache anchors gain RH x_bot rig
    assemblies; the 2 keyed heroes gain UAL mannequins. Env-gated
    (TDAWN_HUMANOID=1) so tdawn_3 stays reproducible byte-for-byte.

    POP_PLAN (the ordinal law: zones in contract order, chase LAST —
    the bridge's ingest order; zone sizes equal 40 so the zone slice
    ambiguity is moot, the chase tail is NOT):
      zone0 40 cool slate / zone1 40 blue-gray / zone2 40 warm drab /
      chase 9 muted rust (group identity, the film's previz semantics).
    """
    import humanoid_crowd as HC
    fam = HC.crowd_family("rh_xbot")
    groups = [("commute_far", 40, (0.30, 0.32, 0.36)),
              ("commute_near", 40, (0.26, 0.28, 0.33)),
              ("commute_near2", 40, (0.33, 0.31, 0.29)),
              ("chase", 9, (0.45, 0.22, 0.16))]
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
    # the UAL principals: Master (amber) + Runner (teal) — the identity
    # colors from tdawn_actors (:58-61), the branch-a law
    UAL_SCALE = 1.75 / 1.589
    # fix-wave-1 D2: clip=None -> AUTO (path-speed matched; the Runner
    # glided on a standing idle before — the moonwalk class)
    pr = HC.bind_principals(ctx, {
        "Master": (None, UAL_SCALE, None),
        "Runner": (None, UAL_SCALE, None)})
    ctx["humanoid_principals"] = HC.ride_principals(ctx, pr, {
        "Master": (0.85, 0.42, 0.05),
        "Runner": (0.02, 0.45, 0.50)})


def _crowd_palette(ctx):
    """Per-agent palette assignment (session-14 COLOR DISCIPLINE, the
    user's tdawn_2 S1 comment: the population is a NEUTRAL register --
    value variance only; identity color is for call-outs. The chase
    group shares ONE muted rust (group identity, previz semantics).

    mesh.copy() preserves the shape-key Key datablock (verified in
    review); materials.clear() never touches shape keys.
    """
    from tdawn_actors import commuter_material, chase_material
    chars = ctx["chars"]["zombies"]
    groups = ((chars["crowd"], commuter_material),
              (chars["chase"], chase_material))
    n = 0
    for group, mat_fn in groups:
        for i, ob in enumerate(group):
            if ob.data.users > 1:
                ob.data = ob.data.copy()
            ob.data.materials.clear()
            ob.data.materials.append(mat_fn(i))
            n += 1
    print(f"[tdawn] crowd palette: {n} agents (neutral crowd + rust chase)")


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
        {"name": "stumble", "frame": 539},
        {"name": "gate_hold", "frame": 625},
        {"name": "vault_seal", "frame": 730, "dur": 2.1},
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
