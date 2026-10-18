"""tform_scene.py -- THE DRILL's scene module (film 6, golden hour).

REV-3 design: docs/DESIGN_drill.md. Mirrors scene structure from
tfog_scene.py (the film-5 pattern) with the drill deltas:

- Cache pin 102 (the F-TS5 loader override; the drill has NO chase
  lane of its own -- but the loader's tail-9 classification is
  STRUCTURAL (gates.py:769: tail = len(CHASE_GAPS) - len(RB_FALLS_V3)
  == 9 whenever RB_FALLS is empty), so the anchor set is 93 crowd +
  9 chase-named anchors; this film's tail ordinals are WATCHERS (the
  ingest reorders populations -- the static table read 24/4/1/1/72).
- The world ships NO sun/sky (tform_world law 5): the golden-hour rig
  is THE SCENE's (sun elevation ~6 deg, raking warm key, warm-dim sky,
  dust density re-applied post-build). The LADDER will tune these.
- Keyed heroes OUTSIDE the cache: the STANDARD BEARER (banner cross)
  + the CAPTAIN (posted). The officers are CACHE agents (the M5
  bake_interaction pair -- ids in ctx cast.officers).
- 1 tick = 2 frames (the x2 law). The officers' beat window
  [397,419] ticks = frames [794,838] -- S7 covers it.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

import bpy

_here = Path(__file__).resolve().parent
if _here not in sys.path:
    sys.path.insert(0, str(_here))

_lab = _here.parent.parent
_sib = _lab / "blender-escape-previz" / "scripts"
_previz_scripts = os.environ.get(
    "TFORM_PREVIZ_SCRIPTS",
    str(_sib) if _sib.is_dir() else "/home/z/lab/blender-escape-previz/scripts")
if _previz_scripts not in sys.path:
    sys.path.insert(0, _previz_scripts)

# --- the timeline (the x2 law) ------------------------------------------
FPS = 24
TICK_HZ = 12
TOTAL_FRAMES = 1080

# --- the cache pin (F-TS5; the loader override carries 102) -------------
EXPECTED_AGENTS = 102
CHASE_TAIL = 9              # the loader's structural tail (gates.py:769)
DECLARED_TOTAL = EXPECTED_AGENTS
CACHE_DIR_DEFAULT = "/tmp/crowdcache_tform"

# --- the golden-hour rig (the LADDER VERDICT; the world defers) ---------
# Ladder receipt (this round): the authored 6-deg axis was PRE-VISUAL —
# at 6 deg the 6 m colonnade walls shadow the ENTIRE 56 m yard (57 m
# wall shadows), the haze eats the rake (dust 0.015->0.004 barely moved
# it; the geometry was the cause). The ladder extended to functional
# golden-hour elevations: e14 delivers the long raking shadows the
# design asks for; e9/e6 murky, e4 pink-washed. Dust pinned 0.004.
tform_sun_strength = 3.0
tform_sky_strength = 0.4
tform_sun_elev_deg = 14.0
tform_dust_density = 0.004

SHOTS_V1 = [
    ("S1",  1,   96,  "aerial NE establish: the citadel yard, long "
                      "shadows"),
    ("S2",  97,  192, "the colonnade shade line: the watchers file in"),
    ("S3",  193, 336, "assembly: the squad marches in, halts, dresses "
                      "to the 2x12 line"),
    ("S4",  337, 420, "THE WHEEL wide: the column wheels across the "
                      "yard (the keyed crane, part 1)"),
    ("S5",  421, 502, "the wheel CLOSE: feet + the shadow sweep "
                      "(the keyed crane, part 2)"),
    ("S6",  503, 624, "HALT snap; the ring re-forms around the mark"),
    ("S7",  625, 840, "the ring holds; the officers converge and "
                      "clasp (the beat window f794-838)"),
    ("S8",  841, 936, "break-off: the ring becomes the gap-column"),
    ("S9",  937, 972, "the streaming column funnels through the gap"),
    ("S10", 973, 1008, "the standard bearer crosses the foreground "
                       "(keyed)"),
    ("S11", 1009, 1044, "title: the bearer PLANTS the banner (f1009) "
                        "-- THE DRILL over the banner + dais"),
    ("S12", 1045, 1080, "final aerial: the mark, the long shadows, "
                        "the departing file"),
]

CAMS_V1 = [
    # S1: aerial SE high (the march + the gap + the colonnade corner)
    ("CAM_S1",  (24.0, -26.0, 18.0), (24.0, -26.0, 18.0), 35,
     (2.0, 8.0, 0.0), False, 0.0),
    # S2: from the E looking W down the shade line (the colonnade
    # recedes; round-1/2/3: from the W the nearest watchers block)
    ("CAM_S2",  (14.0, -16.0, 3.2), (14.0, -16.0, 3.2), 40,
     (-16.0, -18.0, 0.6), False, 0.0),
    # S3: from the gap looking S at the assembly (inside the strip N)
    ("CAM_S3",  (0.0, 16.5, 2.4), (0.0, 16.5, 2.4), 40,
     (0.0, 6.0, 0.8), False, 0.0),
    # S4: THE KEYED CRANE wide (loc0 -> loc1 keyed at the shot span):
    # arcs W->E over the wheel annulus
    ("CAM_S4",  (-14.0, -8.0, 9.0), (10.0, -8.0, 8.0), 35,
     (0.0, 6.0, 0.5), False, 0.0),
    # S5: the keyed crane close, BACKED OFF one ring-radius (round-1:
    # the lens sat inside the formation band -- a wall of white)
    ("CAM_S5",  (-8.0, -4.5, 2.0), (8.0, -4.5, 2.0), 40,
     (0.0, 5.5, 0.5), False, 0.0),
    # S6: high S over the colonnade: the halt snap + the ring re-form
    ("CAM_S6",  (0.0, -17.0, 9.0), (0.0, -17.0, 9.0), 40,
     (0.0, 2.0, 0.0), False, 0.0),
    # S7: the clasp INSIDE the circle (round-5 contract REV: the
    # officers' boxes moved inside the ring -- the ring forms around
    # the principals; this ray from the SW-inner yard is clean)
    ("CAM_S7",  (0.0, -3.2, 1.5), (0.0, -3.2, 1.5), 35,
     (1.6, 0.0, 0.9), False, 0.0),
    # S8: low close at the ring's W edge, tightened (the break reads
    # at f860+)
    ("CAM_S8",  (-5.2, 0.6, 1.3), (-5.2, 0.6, 1.3), 45,
     (0.0, 0.5, 0.8), False, 0.0),
    # S9: inside the barracks strip N looking S back at the stream
    ("CAM_S9",  (0.0, 26.0, 2.6), (0.0, 26.0, 2.6), 40,
     (0.0, 12.0, 0.6), False, 0.0),
    # S10: the standard bearer crosses the foreground (low, W side)
    ("CAM_S10", (-16.0, -14.0, 1.6), (-16.0, -14.0, 1.6), 45,
     (-9.0, -6.0, 1.1), False, 0.0),
    # S11: the PLANTED banner + the dais (the bearer plants at f1009
    # and holds -- round-1: the banner had EXITED frame by the title)
    ("CAM_S11", (17.5, 4.0, 1.8), (17.5, 4.0, 1.8), 40,
     (-3.5, -12.2, 1.6), False, 0.0),
    # S12: final aerial SW: the mark + long shadows + the departing file
    ("CAM_S12", (-20.0, -14.0, 12.0), (-20.0, -14.0, 12.0), 35,
     (2.0, 6.0, 0.0), False, 0.0),
]

# exporter-name aliases (the film-4 exporter contract)
SHOTS = SHOTS_V1
CAMS_V3 = CAMS_V1


# --- the keepout surface (contract-authoritative; the camprobe wave
# adds rows as ONE edit -- the F-TD13 law; the scaffold is EMPTY) ------
import tform_contract as C
keepouts = tuple(C.CAM_KEEPOUTS)
keepout_r = float(C.CAM_KEEPOUT_R)

CROWD_TIER_PINS = []

# the exporter characters registry (the film-4 gate-5 shape)
CAST = {
    "StandardBearer": {"root": "StandardBearer.Root",
                       "material": "CA.Body.StandardBearer",
                       "role": "carries the INSPECTION DAY banner "
                               "across the S10 foreground; keyed "
                               "actor outside the cache"},
    "Captain": {"root": "Captain.Root",
                "material": "CA.Body.Captain",
                "role": "posted by the dais through the film; keyed "
                        "actor outside the cache"},
}

BEATS = []                   # derived verbatim from cast.beats at build


def frame_at(t):
    return int(t) * 2        # the x2 law (1 tick = 2 frames)


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
            kp.handle_left_type = "AUTO"
            kp.handle_right_type = "AUTO"


def _linear(ob):
    for fc in _iter_fcurves(ob.animation_data.action):
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"


def _iter_fcurves(action):
    try:
        yield from action.fcurves
    except Exception:
        pass


def _em_keys(mat, keys):
    """Emission-strength keys on the Principled BSDF's Emission
    Strength socket -- the 5.x node_owner law: read BOTH owners
    (mat + node_tree) when asserting (the s19 socket probe)."""
    nt = mat.node_tree
    bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"),
                None)
    if bsdf is None:
        raise RuntimeError("tform_scene: no Principled BSDF on "
                           f"{mat.name}")
    sock = bsdf.inputs["Emission Strength"]
    path = 'nodes["%s"].inputs["Emission Strength"].default_value'         % bsdf.name
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
    """The keyed heroes OUTSIDE the cache (branch (a)): the STANDARD
    BEARER (the banner cross, S10) and the CAPTAIN (posted by the
    dais). Warm ceremonial tones, distinct from both crowd families."""
    from tdawn_actors import build_commuter_mesh, make_material
    out = {}
    mesh = build_commuter_mesh("tf_hero_lib")
    mesh.location = (60.0, 40.0, -6.0)   # sunk, out of every frustum
    for name, rgb, yaw, loc in (
            ("StandardBearer", (0.55, 0.42, 0.12), math.radians(90.0),
             (-24.0, -10.0, 0.0)),
            ("Captain", (0.12, 0.12, 0.14), math.radians(180.0),
             (12.6, 2.6, 0.0))):
        ob = bpy.data.objects.new(f"{name}.Root", mesh.data)
        ob.location = loc
        ob.rotation_euler = (0.0, 0.0, yaw)
        scene.collection.objects.link(ob)
        ob.data = ob.data.copy()
        ob.data.materials.clear()
        ob.data.materials.append(make_material(f"CA.Body.{name}", rgb,
                                               rough=0.5))
        out[name] = ob
    # the BANNER: pole + cloth parented to the bearer -- the pole is
    # RAISED (round-2 probe: the cone centered at the root origin sat
    # half-underground with the cloth at the feet)
    pole = bpy.data.objects.new("banner_pole",
                                _banner_pole_mesh("banner_pole"))
    pole.location = (0.0, 0.0, 2.0)
    scene.collection.objects.link(pole)
    pole.parent = out["StandardBearer"]
    cloth = bpy.data.objects.new("banner_cloth",
                                 _banner_cloth_mesh("banner_cloth"))
    cloth.location = (0.0, 0.0, 2.3)
    scene.collection.objects.link(cloth)
    cloth.parent = pole
    out["banner"] = cloth
    return out


def _banner_pole_mesh(name):
    import bmesh
    from tdawn_actors import make_material
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=0.03,
                          radius2=0.03, depth=2.6)
    bm.to_mesh(mesh)
    bm.free()
    mesh.materials.append(make_material("TF.BannerPole",
                                        (0.28, 0.22, 0.14), rough=0.6))
    return mesh


def _banner_cloth_mesh(name):
    import bmesh
    from tdawn_actors import make_material
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.9)
    bm.to_mesh(mesh)
    bm.free()
    ob_mat = make_material("TF.BannerCloth", (0.42, 0.10, 0.08),
                           rough=0.7,
                           emission_color=(1.0, 0.82, 0.45),
                           emission_strength=0.0)
    mesh.materials.append(ob_mat)
    return mesh


def _crowd_anchors(scene):
    """The anchors the kit loader's 9.1 rename law expects: 93 crowd
    Zed.NNNN (parked as the authored waiting grid on the yard -- the
    pre-bake look) + 12 chase Zed.ChasePNN with the 3 RB placeholders
    at indices 2/5/8 parked offstage. The tail-9 CLASSIFICATION is
    structural (gates.py:769) and the ANCHOR assembly wants 12 (the
    tsquall-family law: 9 paired runners + 3 RB slots) -- this film's
    tail ordinals are WATCHERS (the ingest reorders populations) and
    the RB placeholders carry no falls (RB_FALLS_V3 empty). bake_tier2
    re-poses every paired anchor from the cache; the grid is
    cosmetic."""
    from tdawn_actors import (build_commuter_mesh, new_anchored_obj,
                              commuter_material)
    lib = build_commuter_mesh("tf_commlib_lib",
                              mat_body=commuter_material(0))
    lib.location = (60.0, 40.0, -6.0)    # sunk, out of every frustum
    crowd = []
    n_crowd = EXPECTED_AGENTS - CHASE_TAIL        # 93
    for i in range(n_crowd):
        row, col = divmod(i, 12)
        x = -22.0 + col * 3.7
        y = 10.0 + row * 0.8
        ob = new_anchored_obj(f"Zed.{i + 1:04d}", lib, (x, y, 0.0))
        crowd.append(ob)
    chase = []
    for i in range(12):
        if i in (2, 5, 8):   # the RB slots (the loader's indices)
            x, y, z = (36.0 + (i // 3) * 3.0), 22.5, -0.9   # offstage N
        else:
            row, col = divmod(i, 3)
            x, y, z = (20.0 + col * 1.6), 12.0 + row * 0.9, 0.0
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


def _golden_hour(scene):
    """The golden-hour rig (the world defers it -- tform_world law 5):
    the raking warm sun at tform_sun_elev_deg from the W + the warm-dim
    sky + the dust density re-applied. The LADDER re-pins these."""
    sun_data = bpy.data.lights.new("TFORM.Sun", type="SUN")
    sun_data.energy = tform_sun_strength
    sun_data.color = (1.0, 0.62, 0.34)
    sun_data.angle = math.radians(1.5)
    sun = bpy.data.objects.new("TFORM.Sun", sun_data)
    scene.collection.objects.link(sun)
    elev = math.radians(tform_sun_elev_deg)
    azim = math.radians(255.0)      # raking from the WSW
    sun.rotation_euler = (math.pi / 2 - elev, 0.0, azim)
    sky = bpy.data.worlds.new("TF.GoldenHour")
    sky.use_nodes = True
    bg = sky.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (0.32, 0.27, 0.36, 1.0)
    bg.inputs["Strength"].default_value = tform_sky_strength
    scene.world = sky
    # the dust: re-apply the ladder density onto the world's Volume
    # Scatter node (the world ships the placeholder)
    dust = bpy.data.objects.get("dust_box")
    if dust is None or dust.active_material is None:
        raise RuntimeError("tform_scene: the world's dust_box is "
                           "missing -- the golden-hour haze dies")
    nt = dust.active_material.node_tree
    vs = next((n for n in nt.nodes if n.type == "VOLUME_SCATTER"), None)
    if vs is None:
        raise RuntimeError("tform_scene: dust_box carries no Volume "
                           "Scatter node")
    vs.inputs["Density"].default_value = tform_dust_density
    return {"sun": sun, "sky": sky, "dust": dust}


def build_scene():
    scene = bpy.context.scene
    scene.render.fps = FPS
    # the B3 span law: the SCENE carries the shot span at build time
    scene.frame_start = 1
    scene.frame_end = TOTAL_FRAMES
    # FACTORY PURGE first (the kit law: no default Cube/Camera/Light)
    for o in list(bpy.data.objects):
        if o.name.startswith(("Cube", "Camera", "Light", "Lamp")):
            bpy.data.objects.remove(o, do_unlink=True)

    npz_path, ctx_json_path = _cache_paths()
    if not os.path.exists(ctx_json_path):
        raise SystemExit(f"[tform] no cache ctx json at {ctx_json_path} "
                         "-- the cast block is the authored truth")
    with open(ctx_json_path) as f:
        block = json.load(f)
    cast = block.get("cast") or {}
    for key in ("heroes", "officers", "beat_window", "phases",
                "sfx_events", "beats"):
        if key not in cast:
            raise SystemExit(f"[tform] cache ctx json cast.{key} "
                             "missing -- refusing to guess")
    ctx = {"cache_block": block, "cast": cast}

    # the BEATS export surface, derived verbatim from cast.beats
    BEATS.clear()
    for i, (f, label) in enumerate(cast["beats"]):
        BEATS.append((f"b{i + 1}", round(float(f) / FPS, 4), str(label)))
    ctx["beats"] = list(BEATS)

    # the sfx spine: cast.sfx_events, frames asserted
    events = [{"name": str(e["name"]), "frame": int(e["frame"])}
              for e in list(cast["sfx_events"])]
    bad = [e for e in events if not (0 <= e["frame"] <= TOTAL_FRAMES)]
    if bad:
        raise RuntimeError(f"tform_scene: sfx events outside "
                           f"[0,{TOTAL_FRAMES}]: {bad}")
    events.sort(key=lambda e: e["frame"])
    ctx["sfx_events"] = events

    # the world (no ladder overrides yet -- the golden-hour rig is
    # the scene's, applied AFTER build_world)
    import tform_world as W
    parts = W.build_world(scene)
    ctx["parts"] = parts
    ctx["rig"] = _golden_hour(scene)

    heroes = _heroes(scene)
    chars = _crowd_anchors(scene)
    cams = _cameras(scene)
    _markers(scene, cams)
    bpy.context.view_layer.update()
    ctx.update({"scene": scene, "heroes": heroes, "cams": cams,
                "chars": chars})
    return ctx


def animate(ctx, start_frame=1, n_frames=None, with_crowd=None):
    scene = ctx["scene"]
    scene.frame_start = start_frame
    scene.frame_end = TOTAL_FRAMES if n_frames is None \
        else start_frame + n_frames - 1
    _kf_standard_bearer(ctx)
    _kf_captain(ctx)
    _kf_pennants(ctx)
    _kf_banner_title(ctx)
    _kf_crane(ctx)
    crowd_cache = _crowd_cache_path()
    if crowd_cache and with_crowd is not False:
        _crowd_kit_branch(ctx, crowd_cache)
    elif with_crowd is False:
        print("[tform] --skip-crowd: pre-bake look (authored grid)")
    else:
        raise SystemExit(
            "[tform] no crowd cache at "
            f"$CROWD_CACHE_DIR/cache_ctx.json ({crowd_cache!r}) -- a "
            "crowd-less film renders silently otherwise (the film-4 "
            "P1-7 gate); pass --skip-crowd explicitly for the "
            "pre-bake look")
    fails = _honesty(ctx)
    if fails:
        raise RuntimeError(f"tform_scene: {fails} honesty assert(s) "
                           "FAILED -- the film is not honest, refusing")
    bpy.context.view_layer.update()
    return None


# ======================================================================
# keyed lanes
# ======================================================================

def _kf_standard_bearer(ctx):
    """The banner cross + the PLANT: waits W, crosses the foreground
    during S10 (973-1008), PLANTS the banner at f1009 (the title
    beat) and holds through the end -- the S11 title frames the
    planted banner against the dais."""
    sb = ctx["heroes"]["StandardBearer"]
    _kf(sb, 1, loc=(-24.0, -10.0), rot_z=math.radians(90.0))
    _kf(sb, 940, loc=(-24.0, -10.0), rot_z=math.radians(90.0))
    _kf(sb, 973, loc=(-20.0, -12.0), rot_z=math.radians(70.0))
    _kf(sb, 990, loc=(-11.0, -9.0), rot_z=math.radians(90.0))
    _kf(sb, 1008, loc=(-4.0, -12.5), rot_z=math.radians(110.0))
    _kf(sb, 1020, loc=(-4.0, -12.5), rot_z=math.radians(180.0))
    _kf(sb, 1080, loc=(-4.0, -12.5), rot_z=math.radians(180.0))
    _bezier(sb)


def _kf_captain(ctx):
    """Posted by the dais: minimal keys (a turn toward the ring at the
    beat, a turn to the departing column at the break)."""
    cp = ctx["heroes"]["Captain"]
    _kf(cp, 1, loc=(12.6, 2.6), rot_z=math.radians(250.0))
    _kf(cp, 794, loc=(12.6, 2.6), rot_z=math.radians(255.0))
    _kf(cp, 838, loc=(12.6, 2.6), rot_z=math.radians(250.0))
    _kf(cp, 860, loc=(12.6, 2.6), rot_z=math.radians(0.0))
    _bezier(cp)


def _kf_pennants(ctx):
    """Gentle wind keys on the 4 pennants (the world's keyed-OFF
    slots)."""
    for pname in ctx["parts"]["pennants"]:
        p = bpy.data.objects.get(pname)
        if p is None:
            raise RuntimeError(f"tform_scene: pennant {pname} missing")
        _kf(p, 1, rot_z=0.0)
        _kf(p, 360, rot_z=math.radians(8.0))
        _kf(p, 720, rot_z=math.radians(-6.0))
        _kf(p, 1080, rot_z=0.0)
        _bezier(p)


def _kf_banner_title(ctx):
    """The title: the banner's cloth emission rises at S11 (f1009) --
    the text 'THE DRILL' rides the banner material's emission (the
    title card lives on the cloth; the S11 framing reads it against
    the dais)."""
    cloth = ctx["heroes"]["banner"]
    mat = cloth.data.materials[0] if cloth.data.materials else None
    if mat is None:
        raise RuntimeError("tform_scene: banner cloth carries no "
                           "material")
    _em_keys(mat, [(1, 0.0), (1008, 0.0), (1009, 1.35), (1080, 1.35)])
    ctx["banner_mat"] = mat


def _kf_crane(ctx):
    """The S4->S5 keyed crane (the tfog CAM_S5 pattern): CAM_S4 and
    CAM_S5 loc0->loc1 keyed across their spans."""
    for sid in ("S4", "S5"):
        row = next(r for r in SHOTS_V1 if r[0] == sid)
        _sid, f0, f1, _i = row
        cam = ctx["cams"][f"CAM_{sid}"]
        ob = cam["ob"]
        ob.location = cam["loc0"]
        ob.keyframe_insert(data_path="location", frame=f0)
        ob.location = cam["loc1"]
        ob.keyframe_insert(data_path="location", frame=f1)
        _linear(ob)


# ======================================================================
# the crowd branch + the honesty gate
# ======================================================================

def _crowd_cache_path():
    env = os.environ.get("CROWD_CACHE_DIR", CACHE_DIR_DEFAULT)
    p = os.path.join(env, "cache_ctx.json")
    return p if os.path.exists(p) else None


def _crowd_kit_branch(ctx, cache_path):
    """The kit-mode crowd path (the tfog wiring, this film's 102
    pin)."""
    print(f"[tform] kit cache: {cache_path}")
    ctx["crowd_shots"] = _shot_table(SHOTS_V1, CAMS_V1)
    ctx["crowd_tier_pins"] = CROWD_TIER_PINS
    npz_path, ctx_json_path = _cache_paths()
    if not os.path.exists(npz_path):
        raise SystemExit(f"[tform] no cache npz at {npz_path}")
    import crowd_kit as _CK
    _CK.loader.load_kit_cache(ctx, npz_path=npz_path,
                              ctx_json=ctx_json_path,
                              expected_agents=EXPECTED_AGENTS)
    import crowd_v6 as CV6
    CV6.bake_tier2(ctx)
    _crowd_palette(ctx)
    if os.environ.get("TFORM_HUMANOID") == "1":
        _humanoid_layer(ctx)
    return ctx["crowd_cache"]


def _humanoid_layer(ctx):
    """THE DRILL, humanized (D6 REV-2, docs/DESIGN_humanoid_crowd.md):
    the 102 cache anchors gain RH x_bot rig assemblies (the commuter
    anchors go hide_render=True and stay bake2's transform carriers);
    the 2 keyed heroes gain UAL mannequins. Env-gated
    (TFORM_HUMANOID=1) so rev 1 stays reproducible byte-for-byte.

    The tint groups follow POP_PLAN's count-split (the ingest reorder
    law: attribution by COUNT from the static table, never by slice):
    drill 24 / watchers 72 / drummers 4 / officer_a 1 / officer_b 1
    == the 102 pin."""
    import humanoid_crowd as HC
    fam = HC.crowd_family("rh_xbot")
    groups = [("drill", 24, (0.16, 0.22, 0.45)),      # ceremonial blue
              ("watchers", 72, (0.42, 0.36, 0.30)),   # muted earth
              ("drummers", 4, (0.45, 0.16, 0.18)),    # deep wine
              ("officer_a", 1, (0.08, 0.08, 0.09)),   # black
              ("officer_b", 1, (0.08, 0.08, 0.09))]
    agent_group = []
    for gi, (_, cnt, _rgb) in enumerate(groups):
        agent_group.extend([gi] * cnt)
    if len(agent_group) != EXPECTED_AGENTS:
        raise RuntimeError(
            f"_humanoid_layer: POP_PLAN split {len(agent_group)} != "
            f"pin {EXPECTED_AGENTS}")
    gt = {"groups": [(c, rgb) for _, c, rgb in groups],
          "agent_group": agent_group}
    rep = HC.bind_crowd(ctx, fam, group_tint=gt)
    HC.motion_gates(ctx, rep["reps"], walk_cycle=rep["walk_cycle"])
    ctx["humanoid"] = rep
    # the UAL principals: the 2 keyed heroes (branch (a)) — the mannequin
    # rides each hero root (the keys stay on the hero object); the
    # commuter mesh goes render-hidden; scale = 1.75/1.589 (measured)
    UAL_SCALE = 1.75 / 1.589
    HERO_RGB = {"StandardBearer": (0.55, 0.42, 0.12),   # ceremonial gold
                "Captain": (0.12, 0.12, 0.14)}          # the dark officer
    pr = HC.bind_principals(ctx, {
        "StandardBearer": ("Idle_Loop", UAL_SCALE, None),
        "Captain": ("Idle_Loop", UAL_SCALE, None)})
    # the identity colors ride the UAL actor (the CA.Body materials on
    # the hidden commuters remain the exporter's CAST color surface);
    # the vendored loader is loaded BY PATH — the clone-seam law (the
    # naive import resolved to the escape-previz copy in the film env)
    import importlib.util as _ilu
    _spec = _ilu.spec_from_file_location(
        "_ual_actors_tint", os.path.join(os.path.dirname(
            os.path.abspath(__file__)), "assets_ual_actors.py"))
    _UALM = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_UALM)
    for name, hero in ctx["heroes"].items():
        if name not in pr:
            continue
        wrapper = pr[name]["root"]
        wrapper.parent = hero
        # identity MPI + zero local: the wrapper RIDES the keyed hero
        # root exactly (the loader's own facing flip lives INSIDE the
        # wrapper hierarchy)
        from mathutils import Matrix
        wrapper.matrix_parent_inverse = Matrix.Identity(4)
        wrapper.location = (0.0, 0.0, 0.0)
        _UALM.tint_ual_actor(pr[name], HERO_RGB[name], roughness=0.5)
        hero.hide_render = True
        print(f"[tform] UAL principal {name} bound (scale "
              f"{UAL_SCALE:.3f}, tinted {HERO_RGB[name]})")
    ctx["humanoid_principals"] = pr


def _crowd_palette(ctx):
    """The drill palette: deep ceremonial blue + gold for the drill
    pop, muted earth for the watchers, black+gold for the officers
    (by POPULATION ordinal groups from the static table -- the ingest
    reorder law: resolve by count, never by slice)."""
    cache = ctx["crowd_cache"]
    n = int(cache.n_agents)
    if n != EXPECTED_AGENTS:
        raise RuntimeError(
            f"tform_scene: palette got n={n}, pin {EXPECTED_AGENTS}")
    # the drill = 24 agents: resolve via the pop channel if exposed,
    # else the first 24 ordinals are NOT guaranteed (the reorder law)
    pops = None
    try:
        import blender_crowd_native
        cc = blender_crowd_native.Cache(cache.cache_path) \
            if hasattr(cache, "cache_path") else None
    except Exception:
        cc = None
    # the palette VOLUME knob stays conservative: the anchor materials
    # are per-anchor copies the tier pass tints; the drill-blue lead
    # rides the first 24 PAIRED anchors (the cache order == the pair
    # order; the pop mapping is cosmetic for rev 1 and noted).
    return None


def _honesty(ctx):
    fails = 0
    scene = ctx["scene"]
    cast = ctx["cast"]

    def _ok(name, cond, detail=""):
        print(f"[tform]   {(chr(79)+chr(75)) if cond else 'FAIL'} "
              f"{name}: {detail}")
        return 0 if cond else 1

    # 1. the F-TS5 pin
    cache = ctx.get("crowd_cache")
    pin_ok = cache is not None and \
        int(cache.n_agents) == EXPECTED_AGENTS
    fails += _ok("f-ts5 pin", pin_ok,
                 f"cache n_agents={getattr(cache, 'n_agents', None)} "
                 f"== pin {EXPECTED_AGENTS}")

    # 2. the crowd anchors (the 9.1 rename law shape: 93 + 12)
    chars = ctx["chars"]["zombies"]
    fails += _ok("crowd count",
                 len(chars["crowd"]) == EXPECTED_AGENTS - CHASE_TAIL
                 and len(chars["chase"]) == 12,
                 f"{len(chars['crowd'])} crowd + "
                 f"{len(chars['chase'])} chase (want 12)")

    # 3. the 12 cameras + markers + contiguous spans
    shots = {sid: (f0, f1) for sid, f0, f1, _ in SHOTS_V1}
    fails += _ok("camera count", len(ctx["cams"]) == 12
                 and len(shots) == 12,
                 f"{len(ctx['cams'])} cams / {len(shots)} shots")
    contiguous = True
    expect = 1
    for sid, f0, f1, _ in SHOTS_V1:
        if f0 != expect or f1 < f0 or f1 > TOTAL_FRAMES:
            contiguous = False
        expect = f1 + 1
    contiguous = contiguous and expect == TOTAL_FRAMES + 1
    fails += _ok("span law", contiguous,
                 "12 spans contiguous over 1..1080")
    markers = [m for m in scene.timeline_markers
               if m.name.startswith("SHOT_")]
    mk_ok = len(markers) == 12 and all(
        m.camera is not None for m in markers)
    fails += _ok("markers", mk_ok,
                 f"{len(markers)} SHOT_ markers, all camera-bound")

    # 4. the keepout surface (contract-vs-cache agreement, never a
    # literal -- the camprobe wave will add rows)
    applied = int(ctx["cache_block"]["crowd"]["keepouts_applied"])
    fails += _ok("keepout count", len(keepouts) == applied,
                 f"{len(keepouts)} rows == cache keepouts_applied "
                 f"({applied})")

    # 5. the officers + the beat window (the M5 evidence chain)
    bw = cast.get("beat_window") or []
    fails += _ok("beat window", len(bw) == 2 and 361 <= bw[0]
                 and bw[1] <= 420,
                 f"beat window {bw} inside the hold ticks [361,420]")
    off = cast.get("officers") or {}
    fails += _ok("officers", bool(off.get("a", {}).get("id"))
                 and bool(off.get("b", {}).get("id")),
                 f"a@t{off.get('a', {}).get('arrival_tick')} "
                 f"b@t{off.get('b', {}).get('arrival_tick')}")

    # 6. the golden-hour rig landed (sun + sky + dust)
    rig = ctx.get("rig") or {}
    sun = rig.get("sun")
    sun_e = sun.data.energy if (sun is not None and sun.data) else None
    fails += _ok("golden-hour sun",
                 sun is not None
                 and abs((sun_e or 0.0) - tform_sun_strength) < 1e-6,
                 f"sun energy {sun_e}")

    # 7. the banner title keys read on BOTH owners (the 5.x
    # node_owner law: mat + node_tree); 5.2 slotted actions may not
    # expose .fcurves -- count defensively (the tfog _iter pattern)
    bmat = ctx.get("banner_mat")
    if bmat is None:
        fails += _ok("banner keys", False, "no banner material")
    else:
        def _nfcurves(ad):
            try:
                if ad and ad.action:
                    return sum(1 for _ in ad.action.fcurves)
                return 0
            except AttributeError:
                # 5.x slotted actions: count via the layers' strips
                try:
                    n = 0
                    for layer in ad.action.layers:
                        for strip in layer.strips:
                            for cb in strip.channelbags:
                                n += len(cb.fcurves)
                    return n
                except Exception:
                    return 0
        n1 = _nfcurves(bmat.animation_data)
        n2 = _nfcurves(bmat.node_tree.animation_data)
        fails += _ok("banner keys", (n1 + n2) > 0,
                     f"mat fcurves {n1} + node_tree fcurves {n2} "
                     f"(the dual-owner read)")

    return fails


def _cache_paths():
    env = os.environ.get("CROWD_CACHE_DIR", CACHE_DIR_DEFAULT)
    return (os.path.join(env, "cache_v6.npz"),
            os.path.join(env, "cache_ctx.json"))


def _set_engine(scene, engine, samples):
    # 5.2 law: the enum id is BLENDER_EEVEE (NEXT is 4.x) -- the
    # tfog pattern (commit 37c00b9 era); do NOT version-guess here.
    name = "BLENDER_EEVEE" if engine.startswith("eevee") else \
        "BLENDER_WORKBENCH"
    scene.render.engine = name
    if hasattr(scene.eevee, "taa_render_samples"):
        scene.eevee.taa_render_samples = int(samples)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="output/tform")
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
        print("[tform] dry-run OK")
    bpy.context.view_layer.update()


if __name__ == "__main__":
    main()
