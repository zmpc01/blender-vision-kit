"""scene_green_light.py -- GREEN LIGHT (tgreen_1), the third film.

Noon-afternoon city crossing: two streams pour in on the walk signal,
converge on the plaza, and FREEZE mid-crossing (the engine's two-rank
ghost freeze -- REV-3 F18: the still IS the third act). A gold living
statue holds the plaza center; a keyed crimson runner threads the
frozen field to reach him as the signal counts down.

Design of record: docs/DESIGN_green_light.md REV-3. Contract:
tgreen_contract.py (zones/speeds/keepouts/seed -- the single crowd
authority). World: tgreen_world.py (the set + sun + glyph plates).

The tferry module shape throughout (the loader owns the crowd chain;
scenes never hand-roll it). Export contract: build_scene returns
ctx["scene"]; BEATS (id, t_seconds, label); sfx {name|kind, frame};
render.fps pinned here.
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

# the escape-previz scripts (crowd_kit plugin + crowd_v6 shared
# loader) -- sibling resolution first (the F-TF1 family; the env
# override still wins)
_lab = Path(__file__).resolve().parent.parent.parent
_sib = _lab / "blender-escape-previz" / "scripts"
_previz_scripts = os.environ.get(
    "TGREEN_PREVIZ_SCRIPTS",
    str(_sib) if _sib.is_dir() else "/home/z/work/blender-escape-previz/scripts")
if _previz_scripts not in sys.path:
    sys.path.insert(0, _previz_scripts)

FPS = 24
total_frames = 1080
_title_f0 = 1009            # the title sting == the light reset (F8)
tg_exposure = 0.0           # F10: the day ladder sweeps sun/sky, never
                            # exposure (the night L-TF4 law inverted)

_here = os.path.dirname(os.path.abspath(__file__))

# --- shots (id, f0, f1, intent) -------------------------------------
SHOTS_V3 = [
    ("S1",  1,    84,  "aerial: the pour ignites as the light gives"),
    ("S2",  85,   168, "the green MAN ignites (the call)"),
    ("S3",  169,  264, "shade into sun: the W knot steps into light; the first rank freezes"),
    ("S4",  265,  348, "the gap closes; the sprint wave reaches the plaza"),
    ("S5",  349,  444, "THE STILL completes: the crossing freezes on camera"),
    ("S6",  445,  528, "the flip-back: the hand blinks over the still"),
    ("S7",  529,  624, "the runner breaks -- the flip is his deadline"),
    ("S8",  625,  720, "the runner vs the closing stream"),
    ("S9",  721,  816, "the hesitate at the plaza edge, then the thread"),
    ("S10", 817,  912, "the hold: the hand blinks over the silence"),
    ("S11", 913,  1008, "the crane rises: the frozen field, the wedge"),
    ("S12", 1009, 1080, "title: GREEN LIGHT as the system resets"),
]

CAMS_V3 = [
    # S1: the high-S aerial WIDE enough for both knots (52m apart):
    # 26mm from (0,-36,32) covers +-27m at street (the S1a/b/c probe
    # ladder -- the knots cropped at every tighter pose)
    ("CAM_S1",  (0.0, -36.0, 32.0), (0.0, -36.0, 32.0), 26,
     (0.0, 0.0, 0.0), False, 0.012),
    # S2: the glyph close-up from the CROSSING side (the plates face S
    # toward the street -- the N-side cam saw the head's blank back:
    # probe S2b lesson); the green MAN reads (S2c cert)
    ("CAM_S2",  (-4.8, -0.8, 2.2), (-4.8, -0.8, 2.2), 40,
     (-4.2, 3.35, 2.5), False, 0.0),
    # fix-wave-2 eyepass round 2 (S3: the NW signal pole crossed the
    # foreground — stepped east+north so the westward view down the
    # shade/sun line reads clean; same 40mm read of the W knot)
    # fix-wave-2 eyepass round 3 (S3: 'no focal anchor' — the cache
    # probe: the W knot = 41 agents x<-15 spread along the street.
    # Lower + closer on the knot's LEAD RANK at its east edge, the
    # knot receding west behind it)
    ("CAM_S3",  (-8.0, 4.8, 1.8), (-8.0, 4.8, 1.8), 50,
     (-16.5, 0.8, 1.1), False, 0.015),
    # S4: high oblique SW over the crossing, looking W down the street
    ("CAM_S4",  (1.5, -2.0, 6.5), (1.5, -2.0, 6.5), 35,
     (-6.0, 0.5, 0.8), False, 0.012),
    # S5: the nadir -- the freeze completing ON CAMERA (the signature)
    ("CAM_S5",  (0.0, 2.5, 16.0), (0.0, 2.5, 16.0), 40,
     (0.0, 0.5, 0.0), False, 0.0),
    # fix-wave-2 eyepass round 2 (S6: the hand read TINY and edge-placed
    # — closer vantage + the aim lowered to the HAND glyph itself (z
    # 2.34, not the head's 2.55 center) + 50mm: the blinking palm
    # carries the upper frame over the frozen crossing)
    # fix-wave-2 eyepass round 3 (S6: the closer vantage stood INSIDE
    # the crowd band — '0 figures, barren plane'. The hand (0.16 m)
    # and the still cannot share a tight frame; S6 now owns THE STILL
    # (the crossing band across mid-frame, the signal + hand upper-
    # left) while S10's close-up owns the hand itself)
    ("CAM_S6",  (1.2, -5.2, 2.0), (1.2, -5.2, 2.0), 45,
     (-2.5, 0.8, 1.7), False, 0.018),
    # S7: his journey reads AHEAD of him (the S7a probe had the crowd
    # behind-camera -- the story inverted); his back + the plaza + the
    # frozen field beyond
    ("CAM_S7",  (21.5, 3.2, 1.8), (21.5, 3.2, 1.8), 50,
     (16.5, 0.8, 0.95), False, 0.02),
    ("CAM_S8",  (27.0, 6.0, 3.6), (27.0, 6.0, 3.6), 45,
     (18.0, 0.8, 1.0), False, 0.015),
    # S9: raised + pulled back over the field (the 65mm at-rim pose
    # was the flood class -- his body invisible behind frozen capsules;
    # S9b cert: the red head clear + the statue beyond; the cam is
    # OUTBOARD now (y 6.0 > walkable 5.0) -- its keepout row DROPPED)
    ("CAM_S9",  (8.0, 6.0, 3.2), (8.0, 6.0, 3.2), 55,
     (4.0, 1.4, 1.0), False, 0.01),
    # S10: the NW head + blinking hand dominate, the still below
    # fix-wave-2 eyepass round 3 (S10: the 85mm frame carried ONLY the
    # head ('a generic geometric object') — the hold needs the hand
    # AND the silence it holds. Pull back to 65mm: the hand prominent
    # on the head, the emptied street reading below it)
    ("CAM_S10", (-2.8, -2.2, 2.0), (-2.8, -2.2, 2.0), 65,
     (-4.2, 3.29, 2.38), False, 0.008),
    # the CRANE (S11/S12): loc keyed in _kf_crane -- S11 rises from the
    # S margin to the certified (−8,−5,9) pose; S12 settles gently
    ("CAM_S11", (-8.6, -14.0, 3.2), (-8.0, -5.0, 9.0), 30,
     (0.0, 0.0, 0.8), False, 0.0),
    ("CAM_S12", (-8.0, -5.0, 9.0), (-7.9, -4.9, 9.4), 40,
     (0.0, 0.0, 0.5), False, 0.0),
]

CAST = {
    "Statue": {"root": "Statue.Root", "material": "CA.Body.Statue",
               "role": "the living statue; holds the plaza center"},
    "Runner": {"root": "Runner.Root", "material": "CA.Body.Runner",
               "role": "gambles on the dying light; threads the still"},
}

BEATS = [
    ("pour",      0.0,  "the pour ignites with the light"),
    ("call",      3.50, "the green MAN ignites (f85)"),
    ("freeze",    7.25, "the first rank freezes (f175)"),
    ("still",    14.5,  "the still completes (f349)"),
    ("flip",     18.5,  "the hand blinks against them (f445)"),
    ("break",    22.0,  "the runner gambles (f529)"),
    ("hesitate", 30.0,  "the hesitate at the plaza edge (f721)"),
    ("reach",    33.5,  "he reaches the statue (f805)"),
    ("reset",    42.0,  "the light resets (f1009)"),
]

CROWD_TIER_PINS = []       # kit mode: single tier, no director pins


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


def _bezier_guarded(ob):
    """BEZIER + AUTO easing with the unkeyed-object guard (the tferry
    shape; a future _bezier on an unkeyed object must no-op, not
    AttributeError)."""
    if ob.animation_data is None or ob.animation_data.action is None:
        return
    for fc in _iter_fcurves(ob.animation_data.action):
        for kp in fc.keyframe_points:
            kp.interpolation = "BEZIER"
            kp.easing = "AUTO"


def _iter_fcurves(action):
    """The 4.x/5.x fcurve iterator (the tdawn-vetted helper, verbatim
    from scene_last_ferry; 5.2 slotted actions carry fcurves in
    channelbags, not on the action)."""
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
    """The authored heroes (F7): Statue (gold, the plaza center, ON
    the plinth top z 0.32) + Runner (crimson, the gamble). Capsule
    heroes via the tdawn actor builders (CA.Body.<name> = the
    exporter's identity registry)."""
    from tdawn_actors import build_commuter_mesh, make_material
    HERO_COLORS = {
        "Statue": (0.72, 0.55, 0.22),      # gold
        "Runner": (0.62, 0.07, 0.10),      # crimson (the proven callout)
    }
    mesh = build_commuter_mesh("TG.HeroMesh")
    mesh.location = (60.0, 0.0, -2.5)      # PARK beyond the E facades
    mesh.hide_render = True                # (F15: the aerial sees y -41)
    heroes = {}
    for name, loc, yaw in (("Statue", (0.0, 0.25, 0.32), 0.0),
                           ("Runner", (24.0, 0.5, 0.0), math.pi / 2)):
        ob = bpy.data.objects.new(f"{name}.Root", mesh.data)
        ob.location = loc
        ob.rotation_euler = (0.0, 0.0, yaw)
        scene.collection.objects.link(ob)
        ob.data = ob.data.copy()
        ob.data.materials.clear()
        ob.data.materials.append(make_material(
            f"CA.Body.{name}", HERO_COLORS[name], rough=0.5))
        heroes[name] = ob
    return heroes


def _crowd_anchors(scene):
    """The 132 placeholder anchors the kit-mode loader's rename law
    expects: 120 crowd Zed.NNNN + 12 chase Zed.ChasePNN (3 RB slots;
    loader.py:530-560 is the law). Pre-bake dressing only -- bake2
    re-keys all 129 non-RB anchors from tick 0. The 3 RB placeholders
    stay put: authored OUTBOARD on the closed S lane (y -7.6, past
    the walkable y -6 floor: dressing-plausible statics; the review
    round law from tferry)."""
    from tdawn_actors import (build_commuter_mesh, new_anchored_obj,
                              commuter_material)
    lib = build_commuter_mesh("TG.CommlibLib",
                              mat_body=commuter_material(0))
    lib.location = (60.0, 0.0, -2.5)
    lib.hide_render = True
    crowd = []
    # 120 anchors: 12 cols x 10 rows spanning the street (x -27.5..27.5
    # step 5, y 0.0..2.2) -- pre-bake positions only
    for i in range(120):
        row, col = divmod(i, 12)
        x = -27.5 + col * 5.0
        y = 0.0 + row * 0.245
        ob = new_anchored_obj(f"Zed.{i + 1:04d}", lib, (x, y, 0.0))
        crowd.append(ob)
    chase = []
    # 12 chase placeholders near the E curb (9 pair with the sim's
    # sprint wave; 3 are RB slots -> parked outboard on the S lane)
    for i in range(12):
        if i in (2, 5, 8):   # the RB slots (the loader's indices)
            x, y = (10.0 + (i // 3) * 4.0), -7.6   # S lane, in-world
        else:
            x, y = (26.0 - i * 0.8), 1.0
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
    """The ShotCam rows the tiering/stash contract carries (the tferry
    shape verbatim -- the 3-f review's shape-regression find: the kit
    chain never reads it today, but wiring tiering onto a kit scene
    must not AttributeError)."""
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


def _glyph_keys(ctx):
    """The signal spine (F8), export-safe SCALE keys (the
    hide_render-does-not-export law from birth):
      f85   walk glyphs ignite (0.001 -> 1.0)
      f445  walk out + hand in, blinking 1.0/0.001 every 12f
      f1008 hand out; f1009 walk re-ignites (the reset) to 1080."""
    g = ctx["parts"]["glyphs"]
    walks = (g["walk_nw"], g["walk_se"])
    hands = (g["hand_nw"], g["hand_se"])
    for ob in walks:
        _kf(ob, 1, scale=(0.001, 0.001, 0.001))
        _kf(ob, 84, scale=(0.001, 0.001, 0.001))
        _kf(ob, 85, scale=(1.0, 1.0, 1.0))
        _kf(ob, 444, scale=(1.0, 1.0, 1.0))
        _kf(ob, 445, scale=(0.001, 0.001, 0.001))
        _kf(ob, 1008, scale=(0.001, 0.001, 0.001))
        _kf(ob, 1009, scale=(1.0, 1.0, 1.0))
        _kf(ob, 1080, scale=(1.0, 1.0, 1.0))
        _bezier(ob)
    for ob in hands:
        _kf(ob, 1, scale=(0.001, 0.001, 0.001))
        _kf(ob, 444, scale=(0.001, 0.001, 0.001))
        f = 445
        on = True
        while f <= 1008:
            _kf(ob, f, scale=(1.0, 1.0, 1.0) if on
                else (0.001, 0.001, 0.001))
            on = not on
            f += 12
        _kf(ob, 1008, scale=(0.001, 0.001, 0.001))
        _kf(ob, 1080, scale=(0.001, 0.001, 0.001))
        _bezier(ob)


def _kf_heroes(ctx):
    """The authored paths (F7). Statue: the plinth (0,0.25); flinch
    at the freeze beat (f355 -- the pop now SPANS f355->361, 0.3 m
    over 6 frames = 1.2 m/s; fix-wave-1: the old 1-frame pop read
    7.2 m/s), performance pose f470, beckon NE f760, final pose
    facing the runner f816+. Runner: E-curb hold f1-529, the gamble,
    the hesitate HOLD (4.6,2.6) f721-750 (S9's aim), the thread
    through the frozen field (retime fix-wave-1: the apron hop now
    spans f750->816 at ~1.9 m/s -- the old f790->800 key read
    6.9 m/s), the reach f816, hold to end."""
    st = ctx["heroes"]["Statue"]
    rn = ctx["heroes"]["Runner"]
    _kf(st, 1, loc=(0.0, 0.25), rot_z=0.0)
    _kf(st, 354, loc=(0.0, 0.25), rot_z=0.0)
    _kf(st, 361, loc=(0.0, 0.55), rot_z=0.15)     # the flinch (6f span)
    _kf(st, 400, loc=(0.0, 0.30), rot_z=0.0)
    _kf(st, 470, loc=(0.0, 0.25), rot_z=0.5)      # performance pose
    _kf(st, 759, loc=(0.0, 0.25), rot_z=0.5)
    _kf(st, 760, loc=(0.0, 0.25), rot_z=-0.6)     # beckon NE
    _kf(st, 815, loc=(0.0, 0.25), rot_z=-0.6)
    _kf(st, 816, loc=(0.0, 0.25), rot_z=0.35)     # final: face him
    _kf(st, 1080, loc=(0.0, 0.25), rot_z=0.35)
    _bezier(st)
    run = [
        (1,   (24.0, 0.5), math.pi / 2),    # E curb, facing W
        (529, (24.0, 0.5), math.pi / 2),    # hold (the light flips)
        (560, (20.0, 0.6), math.pi / 2),
        (620, (14.0, 1.6), math.pi / 2 + 0.1),
        (700, (7.0, 2.2), math.pi / 2 + 0.2),
        (721, (4.6, 2.6), math.pi / 2 + 0.4),   # the hesitate HOLD
        (750, (4.6, 2.6), math.pi / 2 + 0.4),
        (776, (2.5, 3.0), math.pi / 2 - 0.2),   # the thread, N flank
        (811, (0.9, 0.6), math.pi / 2 - 0.3),   # onto the apron
        (816, (0.6, 0.35), 0.35),               # the reach
        (1080, (0.6, 0.35), 0.35),
    ]
    for f, loc, rz in run:
        _kf(rn, f, loc=loc, rot_z=rz)
    _bezier(rn)
    # fix-wave-1 D2: re-derive facing from the path tangents (the
    # tdawn pattern) -- the Runner is the mover (the gamble run + the
    # thread to the apron); the Statue a watcher (the flinch/pose
    # beats sit still, so their authored yaws stay)
    import humanoid_crowd as _HC
    _HC.face_tangent(rn, min_mps=0.45)
    _HC.face_tangent(st, min_mps=0.55)


def _title_card(scene):
    """GREEN LIGHT over the frozen field -- export-safe scale keys.
    WHITE over the dark asphalt (the noon-contrast inversion: cream-
    on-dark worked at night; at noon the dark street IS the contrast
    field -- the F15 charcoal plan failed its probe, invisible on the
    mid-gray read)."""
    from tdawn_actors import make_material
    size = 0.52                 # 11 chars, Bfont advance 0.91-1.1em/char
    tx, ty, tz = 2.2, 0.2, 2.2  # z 2.2: the 2.7 card clipped at frame top
    # at the card's distance (the 4.2 card rendered ABOVE the frame --
    # the eye round's invisible-title find)
    mat = make_material("TG.TitleCard", (0.82, 0.82, 0.80), 0.4)
    crv = bpy.data.curves.new("TG.TitleCard", type="FONT")
    crv.body = "GREEN LIGHT"
    crv.size = size
    crv.align_x = "CENTER"
    crv.align_y = "CENTER"
    crv.extrude = 0.02
    ob = bpy.data.objects.new("TG.TitleCard", crv)
    ob.location = (tx, ty, tz)
    scene.collection.objects.link(ob)
    # face the S12 crane END pose (the 3-f review: keep the constant
    # bound to the ROW, not a hand-copied number)
    cx, cy, cz = CAMS_V3[-1][2]   # CAM_S12 loc1
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


def build_scene():
    """Build the crossing set + heroes + cameras + markers + the
    signal spine. Ends with the F-TD5 view-layer sync."""
    scene = bpy.context.scene
    scene.render.fps = FPS      # the exporter stamps the timeline
    for o in list(bpy.data.objects):
        if o.name.startswith(("Cube", "Camera", "Light", "Lamp")):
            bpy.data.objects.remove(o, do_unlink=True)
    import tgreen_world as W
    parts = W.build_world(scene)
    heroes = _heroes(scene)
    chars = _crowd_anchors(scene)
    cams = _cameras(scene)
    _markers(scene, cams)
    title = _title_card(scene)
    bpy.context.view_layer.update()
    return {"scene": scene, "parts": parts, "heroes": heroes,
            "cams": cams, "chars": chars, "title": title}


def animate(ctx, start_frame=1, n_frames=None, with_crowd=None):
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = total_frames
    _kf_heroes(ctx)
    _glyph_keys(ctx)
    _kf_crane(ctx)
    crowd_cache = _crowd_cache_path()
    if crowd_cache and with_crowd is not False:
        _crowd_kit_branch(ctx, crowd_cache)
    else:
        print("[tgreen] no crowd (cache absent or --skip-crowd) -- "
              "pre-bake look (anchors at authored grid)")
    bpy.context.view_layer.update()
    return None


def _kf_crane(ctx):
    """The crane rise (the tferry pattern): S11 keys its span
    (f913-1008, loc0 -> loc1 with the aim drifting down to the plaza),
    S12 continues to its settle pose by f1030."""
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
    a11 = bpy.data.objects.get("Aim.CAM_S11")
    a11.location = (0.0, 0.0, 0.8)
    a11.keyframe_insert(data_path="location", frame=913)
    a11.location = (0.0, 0.0, 0.5)
    a11.keyframe_insert(data_path="location", frame=1008)
    a12 = bpy.data.objects.get("Aim.CAM_S12")
    a12.location = (0.0, 0.0, 0.5)
    a12.keyframe_insert(data_path="location", frame=1009)
    a12.keyframe_insert(data_path="location", frame=1080)
    _bezier(a11)
    _bezier(a12)


def _crowd_cache_path():
    env = os.environ.get("CROWD_CACHE_DIR", "/tmp/crowdcache_tgreen")
    p = os.path.join(env, "cache_ctx.json")
    return p if os.path.exists(p) else None


def _crowd_kit_branch(ctx, cache_path):
    """The kit-mode crowd path (the tferry shape -- the loader owns
    the chain: honesty asserts + rename law + bake2 pairing)."""
    print(f"[tgreen] kit cache: {cache_path}")
    ctx["crowd_shots"] = _shot_table(SHOTS_V3, CAMS_V3)
    ctx["crowd_tier_pins"] = CROWD_TIER_PINS
    import crowd_kit as _CK
    _CK.loader.load_kit_cache(ctx)
    import crowd_v6 as CV6
    CV6.bake_tier2(ctx)
    _crowd_palette(ctx)
    if os.environ.get("TGREEN_HUMANOID") == "1":
        _humanoid_layer(ctx)
    return ctx["crowd_cache"]


def _humanoid_layer(ctx):
    """GREEN LIGHT, humanized (s25 rollout -- the D6 pattern, the tdawn
    worked example): the 129 cache anchors gain RH x_bot rig
    assemblies; the 2 keyed heroes gain UAL mannequins. Env-gated
    (TGREEN_HUMANOID=1) so tgreen_1 rev2 stays reproducible
    byte-for-byte.

    POP_PLAN (the ordinal law: zones in CONTRACT order, chase LAST --
    the bridge's ingest order; tgreen_contract SPAWN_ZONES_V5 rows
    40/36/44, the verbatim-129 law 120 zone + 9 tail):
      zone0 40 stream_n / zone1 36 stream_s / zone2 44 cross_wait /
      chase 9 crew (group identity, the film's previz semantics).
    """
    import humanoid_crowd as HC
    fam = HC.crowd_family("rh_xbot")
    groups = [("stream_n", 40, (0.28, 0.30, 0.34)),
              ("stream_s", 36, (0.34, 0.30, 0.26)),
              ("cross_wait", 44, (0.22, 0.26, 0.24)),
              ("crew", 9, (0.40, 0.28, 0.16))]
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
    # the UAL principals: Statue (gold) + Runner (crimson) -- the
    # identity colors from _heroes (:204-205), the branch-a law
    UAL_SCALE = 1.75 / 1.589
    # fix-wave-1 D2: the Runner goes AUTO (path-speed matched -- he
    # glided on a standing idle before, the moonwalk class). The
    # Statue KEEPS Idle_Loop by design: his one move is the flinch
    # lean (now spanned f355->361 at 1.2 m/s -- fix-wave-1 killed
    # the old 1-frame 7.2 m/s pop) -- a posed statue on a plinth
    # must not pick up a gait cycle
    pr = HC.bind_principals(ctx, {
        "Statue": ("Idle_Loop", UAL_SCALE, None),
        "Runner": (None, UAL_SCALE, None)})
    ctx["humanoid_principals"] = HC.ride_principals(ctx, pr, {
        "Statue": (0.72, 0.55, 0.22),
        "Runner": (0.62, 0.07, 0.10)})


def _crowd_palette(ctx):
    """The x-sign palette split (F5/F12): east warm gray / west cool
    slate, TWO value-separated tones each; the sprint wave (chase)
    inherits its SIDE's tone (never red -- red is the Runner alone).
    The split keys on the agent's SPAWN x sign (frame-1 location;
    bake2 keyed positions -- frame 1 IS the spawn pose).

    bake2 gives every sim agent a private mesh (users==1); the 3 RB
    placeholders keep the shared lib mesh (copy first -- the
    clone-army law)."""
    from tdawn_actors import make_material
    WEST = [(0.36, 0.41, 0.48), (0.24, 0.28, 0.34)]   # cool slate pair
    EAST = [(0.56, 0.50, 0.43), (0.43, 0.38, 0.32)]   # warm gray pair
    chars = ctx["chars"]["zombies"]
    n = {"W": 0, "E": 0}
    bpy.context.scene.frame_set(1)   # hoisted (the 3-f review: one
    # depsgraph eval, not 132 -- bake2 keys tick 0 at f1 for every
    # agent, so the spawn-pose read holds for all of them)
    for kind in ("crowd", "chase"):
        for ob in chars[kind]:
            if ob.data.users > 1:
                ob.data = ob.data.copy()
            side = "E" if ob.matrix_world.translation.x >= 0 else "W"
            tones = EAST if side == "E" else WEST
            i = n[side]
            ob.data.materials.clear()
            ob.data.materials.append(make_material(
                f"CA.Comm.TG.{side}.{i % 2}", tones[i % 2]))
            n[side] += 1
    print(f"[tgreen] crowd palette: {n['W']} west / {n['E']} east "
          "(value-split streams)")


def emit_sfx_events(ctx, out_dir):
    import json
    events = [
        {"name": "chime", "frame": 85, "label": "the walk signal"},
        {"name": "tick", "frame": 445, "label": "the countdown begins"},
        {"name": "chime", "frame": 1009, "label": "the light resets"},
    ]
    with open(os.path.join(out_dir, "sfx_events.json"), "w") as f:
        json.dump({"fps": FPS, "meta": {"scene": "scene_green_light"},
                   "events": events}, f, indent=1)


def _script_args():
    argv = sys.argv
    return argv[argv.index("--") + 1:] if "--" in argv else []


def _set_engine(scene, engine, samples):
    # s27 engine-map law (DESIGN_engine_map_s27 D1/D2, audited REV-2):
    # the old two-way map sent --engine cycles to WORKBENCH — the
    # stills lane silently rendered light-blind workbench frames.
    # Cycles branch = the tform canonical (bounded bounces, CPU,
    # denoise). The exposure tail stays ENGINE-UNCONDITIONAL.
    engine = (engine or "").lower()
    if engine.startswith("cycles"):
        scene.render.engine = 'CYCLES'
        scene.cycles.samples = int(samples)
        scene.cycles.use_denoising = True
        scene.cycles.device = 'CPU'
        scene.cycles.max_bounces = 4
        scene.cycles.transmission_bounces = 2
        scene.cycles.volume_bounces = 1
        print(f"[tgreen] engine={scene.render.engine} samples={samples} "
              "denoise on CPU (s27 engine-map law)")
        return
    name = "BLENDER_EEVEE" if engine.startswith("eevee") else \
        "BLENDER_WORKBENCH"
    scene.render.engine = name
    if engine.startswith("eevee"):
        scene.eevee.use_raytracing = True   # the 5.2 SSR knob
        if hasattr(scene.eevee, "taa_render_samples"):
            scene.eevee.taa_render_samples = samples
    scene.view_settings.exposure = tg_exposure   # F10: pinned 0


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="output/tgreen")
    p.add_argument("--engine", default="workbench")
    p.add_argument("--w", type=int, default=640)
    p.add_argument("--h", type=int, default=360)
    p.add_argument("--still", type=int, default=None)
    p.add_argument("--samples", type=int, default=32)
    p.add_argument("--skip-crowd", action="store_true")
    args = p.parse_args(_script_args())

    scene = bpy.context.scene
    # s27 D2 hoist (enabler): the planned engine-conditional world
    # tunes read scene.render.engine at BUILD time — set it here so
    # build_world sees the true engine.
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
        print("[tgreen] dry-run OK")
    bpy.context.view_layer.update()


if __name__ == "__main__":
    main()
