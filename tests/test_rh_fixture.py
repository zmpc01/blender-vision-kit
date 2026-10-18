"""test_rh_fixture.py — the rh_canvas surface battery against the OFFLINE
fixture library (RH_CANVAS_LIB=/home/z/rh_fixture_lib by default).

Session-20 context: the real RH-canvas data source went dark (beulahkemp
repos 404; no forks/mirrors — see worklog). rh_canvas.py's surface
survives; the fixture library (scripts/rh_fixture_lib.py) rebuilds a
contract-conformant library so the module stays testable and
dog-foodable offline. THIS battery walks the module's public API against
that fixture: catalog laws, fetch-verify + poison-repair, import-clip
laws, mannequin census, bind + playback, teacher refusals, channel-match
guard, registry/fingerprint, fake-user hygiene, statue import + ground
band, GLB round-trip, and the placement_lib ARMATURE branches.

The fixture is SELF-VERIFYING: every row asserts against truth.json
(written by the generator's own re-import measurements) — no
hand-maintained pins. The documented deviations (obj scale 1.0, rot X 0
vs the platform's 0.01/90) live in truth.json['recipe'] + the generator
docstring; docs/rh_canvas.md laws keep authority on real clones.

Run:
  ./scripts/blrun.sh --background --python tests/test_rh_fixture.py --
Exit 0 = pass/skip; 1 = failures; 2 = environment error.
"""
import json
import math
import os
import shutil
import sys
import traceback

_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS = os.path.abspath(os.path.join(_HERE, "..", "scripts"))
for _p in (_SCRIPTS,):
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

import bpy  # noqa: E402
import rh_canvas  # noqa: E402
import placement_lib as pl  # noqa: E402
from mathutils import Vector  # noqa: E402

_REPO_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
_OUT_ROOT = os.environ.get("KIT_OUT", os.path.join(_REPO_ROOT, "output", "tests"))
OUT = os.path.join(_OUT_ROOT, "rh_fixture_results.json")
os.makedirs(os.path.dirname(OUT), exist_ok=True)

FIXTURE_ROOT = os.environ.get(
    "RH_FIXTURE_ROOT", "/home/z/rh_fixture_lib")
os.environ.setdefault("RH_CANVAS_LIB", FIXTURE_ROOT)

FAIL = []
ROWS = {}

TRUTH = None
if os.path.isfile(os.path.join(FIXTURE_ROOT, "truth.json")):
    with open(os.path.join(FIXTURE_ROOT, "truth.json")) as f:
        TRUTH = json.load(f)
LIB_OK = TRUTH is not None \
    and rh_canvas.discover_libraries().get("animations") is not None

PIN_WALK = "9001"
PIN_RUN = "9002"
PIN_JUMP = "9004"
PIN_SIT = "9005"
PIN_TPOSE = "9008"
PIN_STATUE = "Farmer"


def row(row_id, fn):
    if not LIB_OK:
        ROWS[row_id] = "skip"
        print(f"[SKIP] {row_id}: fixture library absent at {FIXTURE_ROOT} "
              f"— build it: ./scripts/blrun.sh --background --python "
              f"scripts/rh_fixture_lib.py --", flush=True)
        return
    try:
        fn()
        ROWS[row_id] = "pass"
        print(f"[row] {row_id}: PASS", flush=True)
    except Exception:                                # noqa: BLE001
        ROWS[row_id] = "fail"
        FAIL.append(row_id)
        print(f"[row] {row_id}: FAIL\n{traceback.format_exc(limit=4)}",
              flush=True)


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)


def near(a, b, tol, msg):
    check(abs(a - b) <= tol, f"{msg}: {a} vs {b} (tol {tol})")


def fresh_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def _fcurves(act):
    try:
        out = []
        for layer in act.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    out.extend(bag.fcurves)
        return out
    except AttributeError:
        return list(act.fcurves)


# --------------------------------------------------------------------------- #
#  F1 catalog
# --------------------------------------------------------------------------- #

def f10_rh3d_layout():
    """s41 RH-3d-assets layout contract (offline): discovery of the
    third repo, the flat models manifest, the sha256 preview law
    (ok-git materialize + poison repair), thumbnails, the rigs
    manifest, and the family-gate bind on the fixture rig."""
    libs = rh_canvas.discover_libraries()
    check(libs.get("assets3d") is not None,
          f"assets3d not discovered: {libs}")
    res = rh_canvas.catalog_query("models")
    check(res["count"] == 3, f"models rows {res['count']} != 3")
    check(all(m.get("preview_local") and m.get("preview_sha256")
              for m in res["rows"]),
          "models missing preview_local/preview_sha256 join")
    # the sha-law: cold cache materializes from the in-git copy
    cache = os.path.join(FIXTURE_ROOT, "_cache_s41")
    import shutil as _sh
    _sh.rmtree(cache, ignore_errors=True)
    model = next(m for m in rh_canvas.load_models() if m["name"] == "Farmer")
    out = rh_canvas.fetch_previews(["Farmer"], cache=cache)
    check(out[0]["status"] == "ok-git",
          f"cold preview status {out[0]['status']} != ok-git")
    out2 = rh_canvas.fetch_previews(["Farmer"], cache=cache)
    check(out2[0]["status"] == "ok-cached", "idempotent ok-cached")
    with open(out[0]["dest"], "wb") as fh:
        fh.write(b"POISON")
    out3 = rh_canvas.fetch_previews(["Farmer"], cache=cache)
    check(out3[0]["status"] == "re-fetched(repaired)",
          f"poison repair status {out3[0]['status']}")
    thumbs = rh_canvas.load_thumbnails()
    check(len(thumbs) == 8 and all(os.path.isfile(t["path"]) for t in thumbs),
          f"thumbnails {len(thumbs)} != 8")
    rigs = rh_canvas.load_rigs()
    check(len(rigs) == 3 and {r["name"] for r in rigs} ==
          {"male_body", "female_body", "x_bot"},
          f"rigs rows: {[r['name'] for r in rigs]}")
    q = rh_canvas.catalog_query("rigs")
    check(q["count"] == 3, f"catalog rigs {q['count']}")
    # the live fixture-rig round-trip: import-rig (family gate, stub
    # hygiene — the fixture rig is the 65-bone rest rig, 0 meshes) +
    # bind the pinned walk clip onto it
    arm, rep = rh_canvas.import_rig("x_bot", at=(1.0, 0.0, 0.0),
                                    rot_z_deg=90.0, cache=cache)
    check(rep["bones"] == 65,
          f"fixture rig bones {rep['bones']} != 65")
    rep_bind = rh_canvas.bind(arm, PIN_WALK, cache=cache)
    m_matched, m_total = (int(v) for v in
                          rep_bind["channels_matched"].split("/"))
    check(m_matched == m_total and rep_bind["orphaned_channels"] == 0,
          f"fixture rig bind {rep_bind['channels_matched']} "
          f"orphans={rep_bind['orphaned_channels']}")


def f1_catalog():
    res = rh_canvas.catalog_query("categories")
    check(res["count"] == len(TRUTH and set(
        c["category"] for c in TRUTH["clips"].values())),
        f"category count {res['count']}")
    codes = {r["code"] for r in res["rows"]}
    check("action_stunt" in codes and "dance_move" in codes,
          f"fixture categories missing: {sorted(codes)[:4]}")
    res = rh_canvas.catalog_query("animations")
    check(res["count"] == len(TRUTH["clips"]),
          f"animation rows {res['count']} != truth {len(TRUTH['clips'])}")
    by_id = {r["id"]: r for r in res["rows"]}
    check(all(isinstance(k, str) for k in by_id), "id-string law")
    # tags from the truth
    tags_9004 = by_id[PIN_JUMP].get("tags", [])
    check("elevated_root_motion" in tags_9004,
          f"9004 tags missing elevated_root_motion: {tags_9004}")
    tags_9008 = by_id[PIN_TPOSE].get("tags", [])
    check("static_pose" in tags_9008, "9008 static_pose tag")
    # durations (the s39-U1 frictionless ask)
    check(by_id[PIN_WALK].get("frames") == 48,
          f"browse frames {by_id[PIN_WALK].get('frames')}")
    check(abs(by_id[PIN_WALK]["duration_s"] - 48 / 30) < 1e-6,
          "duration_s = frames/30")
    # category filter + search
    res = rh_canvas.catalog_query("animations", category="SPORTS_MOVE")
    check(res["count"] == 1 and res["rows"][0]["id"] == PIN_RUN,
          "category filter (case-insensitive code)")
    res = rh_canvas.catalog_query("animations", search="wave")
    check(res["count"] == 1 and res["rows"][0]["id"] == "9006",
          "nameEn search")
    # facets
    res = rh_canvas.catalog_query("characters", facets=[("gender", "female")])
    check(res["count"] == 1 and res["rows"][0]["id"] == "7002",
          "facet filter")
    try:
        rh_canvas.catalog_query("characters", facets=[("gender", "robot")])
        raise AssertionError("unknown facet value must refuse")
    except rh_canvas.RHRefused:
        pass
    res = rh_canvas.catalog_query("models")
    check(res["count"] == 3, f"model rows {res['count']}")
    # s20 filters (the docs-only drive's F3 ask): tag + max-frames
    res = rh_canvas.catalog_query("animations", tag="elevated_root_motion")
    check(res["count"] == 1 and res["rows"][0]["id"] == PIN_JUMP,
          f"--tag filter: {res['count']}")
    res = rh_canvas.catalog_query("animations", max_frames=30)
    check(all(r["frames"] <= 30 for r in res["rows"]) and res["count"] >= 1,
          f"--max-frames filter: {[r['frames'] for r in res['rows']]}")


# --------------------------------------------------------------------------- #
#  F2 fetch-verify + poison repair
# --------------------------------------------------------------------------- #

def f2_fetch_verify():
    cache = os.path.join(FIXTURE_ROOT, "_cache_test")
    shutil.rmtree(cache, ignore_errors=True)
    results = rh_canvas.fetch_ids([PIN_WALK, PIN_STATUE], cache=cache)
    check(len(results) == 2, "fetch walk + statue")
    check(all(r["status"] == "ok" for r in results),
          f"fresh statuses: {[r['status'] for r in results]}")
    r2 = rh_canvas.fetch_ids([PIN_WALK], cache=cache)
    check(r2[0]["status"] == "ok-cached", "idempotent cache hit")
    # poison: garbage bytes -> repair
    dest = rh_canvas.animation_cache_path(
        cache, rh_canvas._find_animation(PIN_WALK))
    with open(dest, "wb") as f:
        f.write(b"GARBAGE")
    r3 = rh_canvas.fetch_ids([PIN_WALK], cache=cache)
    check(r3[0]["status"] == "re-fetched(repaired)", "poison repair")
    # poison: 0-byte
    open(dest, "wb").close()
    r4 = rh_canvas.fetch_ids([PIN_WALK], cache=cache)
    check(r4[0]["status"] == "re-fetched(repaired)", "0-byte repair")
    # unknown id refuses (fail closed)
    try:
        rh_canvas.fetch_ids(["999999"], cache=cache)
        raise AssertionError("unknown id must refuse")
    except rh_canvas.RHRefused:
        pass
    shutil.rmtree(cache, ignore_errors=True)


# --------------------------------------------------------------------------- #
#  F3 import-clip laws vs truth
# --------------------------------------------------------------------------- #

def f3_import_clip():
    fresh_scene()
    arm, rep = rh_canvas.import_clip(PIN_WALK)
    t = TRUTH["clips"][PIN_WALK]
    check(rep["bones"] == 65, f"bones {rep['bones']}")
    check(rep["obj_scale"] == t["obj_scale"],
          f"obj_scale vs truth: {rep['obj_scale']} vs {t['obj_scale']}")
    check(rep["mixamorig_prefix"] is True, "prefix law")
    check(rep["fps"] == 30, f"fps law {rep['fps']}")
    check(rep["frame_range"] == t["frames"],
          f"frame range {rep['frame_range']} vs truth {t['frames']}")
    sc = bpy.context.scene
    check([sc.frame_start, sc.frame_end] == t["frames"],
          "scene range auto-set from action")
    # upright meters figure (the fixture's pinned import state)
    near(rep["rest_feet_z_m"], 0.0, 0.06, "feet at ground")
    near(rep["t_pose_span_m"], 1.4, 0.05, "t-pose span")
    check(rep["action"] is not None, "action bound")


def f3b_teacher_refusal():
    fresh_scene()
    arm, _ = rh_canvas.import_clip(PIN_WALK)
    arm.data.bones[0].name = "renamed_bone"
    try:
        rh_canvas.check_mixamo_rig(arm, "f3b")
        raise AssertionError("renamed bone must refuse")
    except rh_canvas.RHRefused:
        pass


# --------------------------------------------------------------------------- #
#  F4 mannequin
# --------------------------------------------------------------------------- #

def f4_mannequin():
    fresh_scene()
    arm, _ = rh_canvas.import_clip(PIN_WALK)
    mesh, rep = rh_canvas.build_mannequin(arm, "F4Mannequin")
    check(rep["vertex_groups"] == 65, f"65 groups {rep['vertex_groups']}")
    check(rep["zero_weight_verts"] == 0, "no zero-weight verts")
    check(1.5 <= rep["rest_height_m"] <= 2.1,
          f"rest height {rep['rest_height_m']}")
    check(rep["segments"] == 22, f"22 capsules {rep['segments']}")


# --------------------------------------------------------------------------- #
#  F5 bind + playback vs truth
# --------------------------------------------------------------------------- #

def f5_bind_playback():
    fresh_scene()
    arm, _ = rh_canvas.import_clip(PIN_WALK)
    mesh, _ = rh_canvas.build_mannequin(arm, "F5Mannequin")
    rep = rh_canvas.bind(mesh, PIN_RUN)        # mesh arg auto-resolves
    check(rep["armature"] == arm.name, "mesh arg resolved to armature")
    check(rep["slot_assigned"] is True, "slot assigned")
    check(rep["orphaned_channels"] == 0, "clean channel match")
    sc = bpy.context.scene
    t = TRUTH["clips"][PIN_RUN]
    check([sc.frame_start, sc.frame_end] == t["frames"],
          f"scene range from run action {t['frames']}")
    # playback: hips travel ~truth xy over the clip
    mw = arm.matrix_world
    x0 = (mw @ arm.pose.bones["mixamorig:Hips"].matrix.translation).copy()
    sc.frame_set(t["frames"][1])
    bpy.context.view_layer.update()
    x1 = (arm.matrix_world
          @ arm.pose.bones["mixamorig:Hips"].matrix.translation)
    travel = (x1 - x0).length
    near(travel, t["xy_path_m"], 0.6,
         f"run travel vs truth {t['xy_path_m']}")


def f5b_bind_refusals():
    fresh_scene()
    # non-mixamo armature refuses
    ad = bpy.data.armatures.new("NotMixamo")
    ob = bpy.data.objects.new("NotMixamo", ad)
    bpy.context.scene.collection.objects.link(ob)
    try:
        rh_canvas.bind(ob, PIN_WALK)
        raise AssertionError("non-mixamo bind must refuse")
    except rh_canvas.RHRefused:
        pass
    # channel-match: rename ALL bones -> 0/N matched = REFUSED (s39-U2 P1)
    fresh_scene()
    arm, _ = rh_canvas.import_clip(PIN_WALK)
    for b in arm.data.bones:
        b.name = "x" + b.name
    # census now fails first (count still 65 but prefix broken) — the
    # channel-match guard's decoy needs prefix-correct names:
    fresh_scene()
    arm, _ = rh_canvas.import_clip(PIN_WALK)
    # count+prefix stay legal; the NAMES break -> the channel-match
    # guard (0/N matched) is the layer that must refuse (s39-U2 P1 —
    # the decoy must reach THAT guard, not the prefix census).
    # TRAP (probe-verified): renaming a pose bone AUTO-REMAPS the bound
    # action's fcurve data_paths (Blender's rename fixup) — binding the
    # SAME clip would re-match 1:1. The decoy binds a DIFFERENT clip:
    # its fresh import targets the ORIGINAL names -> 0/N -> refuse.
    for b in arm.data.bones:
        b.name = b.name + "X"          # mixamorig:Hips -> mixamorig:HipsX
    try:
        rh_canvas.bind(arm, PIN_SIT)   # fresh import, original names
        raise AssertionError("name-broken bind must refuse via "
                             "channel-match")
    except rh_canvas.RHRefused:
        pass


def f5c_swap_unpin():
    """bind A then B: the replaced action must drop its fake_user pin
    (the s39 'air dance' class); purge_unassigned removes PINNED
    strays (an unpinned stray is Blender's normal garbage — not the
    leak class)."""
    fresh_scene()
    arm, _ = rh_canvas.import_clip(PIN_WALK)
    act_a = arm.animation_data.action
    check(act_a.use_fake_user, "importer pins the action")
    rh_canvas.bind(arm, PIN_SIT)
    check(not act_a.use_fake_user,
          "replaced action auto-unpinned")
    # a pinned-but-unassigned stray (the real leak class): a copy keeps
    # the pin while nothing references it
    stray = act_a.copy()
    stray.use_fake_user = True                 # the pinned-stray leak class
    check(stray.use_fake_user, "stray carries the pin")
    stray_name = stray.name                    # purge invalidates the datablock
    rep = rh_canvas.purge_unassigned()
    check(stray_name in rep["removed"],
          f"purge removed the pinned stray: {rep['removed']}")


def f5d_registry_fingerprint():
    """The registry must not mis-bind after a scene reset (the s39 decoy
    law: every Mixamo action shares one name)."""
    fresh_scene()
    arm, _ = rh_canvas.import_clip(PIN_RUN)
    rh_canvas._CLIP_ACTION_REGISTRY.clear()   # simulate a lost registry
    rep = rh_canvas.bind(arm, PIN_SIT)        # fresh import path
    check(rep["action"] is not None, "bind after registry clear")
    check(rep["armature"] == arm.name, "same armature")


# --------------------------------------------------------------------------- #
#  F6 statue
# --------------------------------------------------------------------------- #

def f6_statue():
    fresh_scene()
    objs, rep = rh_canvas.import_statue(PIN_STATUE)
    check(rep["meshes"] >= 1, "statue meshes")
    near(rep["height_m"], TRUTH["statues"][PIN_STATUE]["height_m"], 0.01,
         f"statue height vs truth {rep['height_m']}")
    check(abs(rep["feet_min_z_m"]) < 0.010,
          f"ground band {rep['feet_min_z_m']}")
    check(rep["grounding"].startswith("PASS"), "grounding verdict")


# --------------------------------------------------------------------------- #
#  F7 GLB round-trip
# --------------------------------------------------------------------------- #

def f7_glb_roundtrip():
    fresh_scene()
    arm, _ = rh_canvas.import_clip(PIN_JUMP)
    rh_canvas.build_mannequin(arm, "F7Mannequin")
    sc = bpy.context.scene
    sc.render.fps = 30
    out = os.path.join(_OUT_ROOT, "rh_fixture_f7.glb")
    bpy.ops.export_scene.gltf(filepath=out, export_format='GLB')
    check(os.path.getsize(out) < 5e6, f"glb size {os.path.getsize(out)}")
    fresh_scene()
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=out)
    new = [o for o in bpy.data.objects if o not in before]
    arms = [o for o in new if o.type == 'ARMATURE']
    check(len(arms) >= 1, "round-trip armature")
    a = arms[0]
    check(len(a.data.bones) == 65,
          f"round-trip bones {len(a.data.bones)}")
    check(a.animation_data is not None
          and a.animation_data.action is not None,
          "round-trip action present")


# --------------------------------------------------------------------------- #
#  F8 placement e2e (the ARMATURE branches)
# --------------------------------------------------------------------------- #

def f8_placement():
    fresh_scene()
    # ground plane
    bpy.ops.mesh.primitive_plane_add(size=20)
    ground = bpy.context.active_object
    ground.name = "F8Ground"
    arm, _ = rh_canvas.import_clip(PIN_TPOSE)
    # move_to the armature (the ARMATURE vs-guard: .data is truthy)
    pl.move_to(arm, (5.0, 0.0, 0.0), reference="origin",
               override="keyframe")  # the action carries object-level root-motion
               # channels (platform-faithful); rebase keeps placement.
               # x/y over the bench: place_on raycasts the CURRENT xy
    mw = arm.matrix_world
    near(mw.translation.x, 5.0, 1e-3, "move_to x")
    near(mw.translation.y, 0.0, 1e-3, "move_to y")
    # place_on the armature onto a bench
    bpy.ops.mesh.primitive_cube_add(size=1, location=(5, 0, 0.25))
    bench = bpy.context.active_object
    bench.scale = (2, 0.5, 0.5)
    bench.name = "F8Bench"
    bpy.context.view_layer.update()
    rep = pl.place_on(arm, bench, footprint='bottom', override='keyframe')
    check(rep.get("footprint_source") == 
          "armature-points (pose bone head/tail + bound_box corners)",
          f"footprint_source row: {rep.get('footprint_source')}")
    # seated: hips above the bench top, feet above ground
    arm_vec = arm.matrix_world.translation
    check(0.3 <= arm_vec.z <= 1.2, f"armature z after seat {arm_vec.z}")
    # the armature's AABB rests on the bench
    mn, mx = pl._aabb(arm)
    check(abs(mn.z - 0.5) < 0.15,
          f"armature bbox bottom near bench top: {mn.z}..{mx.z}")
    # pair_contact works on the armature (box BVH proxy) — the report's
    # real keys (gotcha-11), then TEETH (s20-A2 T-P1 + s20-A3 P2):
    rep_pc = pl.pair_contact(arm, bench)
    check(rep_pc.get("state") == "TOUCHING",
          f"seated armature vs bench must read TOUCHING, got "
          f"{rep_pc.get('state')!r}")
    # the armature poly set == the AABB's 6 planes (the s20-A3
    # alignment law: _polys_world quads == _armature_box_bvh faces)
    from mathutils import Vector as _V
    polys = pl._polys_world(arm)
    check(len(polys) == 6, f"6 armature quads, got {len(polys)}")
    for poly in polys:
        n = (poly[1] - poly[0]).cross(poly[2] - poly[0]).normalized()
        d = n.dot(poly[0])
        corners = [abs(n.dot(_V(c)) - d) for c in poly]
        check(max(corners) < 1e-4, f"quad not planar: {corners}")
    # known-bad case: a thin spear THROUGH the bench box must read
    # PENETRATING (the crossing branch on MESH-vs-MESH sanity — the
    # armature-vs-support pair above must not have broken the branch)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(5.0, 0.0, 0.25))
    spear = bpy.context.active_object
    spear.scale = (2.2, 0.04, 0.04)     # a skewer through the bench
    bpy.context.view_layer.update()
    rep_spear = pl.pair_contact(spear, bench)
    check(rep_spear.get("state") == "PENETRATING",
          f"spear-through-bench must PENETRATE, got "
          f"{rep_spear.get('state')!r}")


# --------------------------------------------------------------------------- #
#  F9 multi-actor ensemble (the s39 multi-character recipe)
# --------------------------------------------------------------------------- #

def f9_ensemble():
    fresh_scene()
    ids = [PIN_WALK, PIN_RUN, "9006"]
    arms = []
    for i, cid in enumerate(ids):
        arm, rep = rh_canvas.import_clip(cid, name=f"F9Actor{i}")
        rh_canvas.build_mannequin(arm, f"F9Body{i}")
        pl.move_to(arm, (i * 2.0, 0, 0), reference="origin",
                   override="keyframe")
        arms.append(arm)
    # union scene range (the recipe law)
    lo = min(int(a.animation_data.action.frame_range[0]) for a in arms)
    hi = max(int(a.animation_data.action.frame_range[1]) for a in arms)
    sc = bpy.context.scene
    sc.frame_start, sc.frame_end = lo, hi
    check(sc.frame_end >= 49, f"union range end {sc.frame_end}")
    # all three animate at mid-range
    sc.frame_set((lo + hi) // 2)
    bpy.context.view_layer.update()
    moved = 0
    for a in arms:
        pb = a.pose.bones["mixamorig:Hips"]
        if pb.matrix.translation.length > 1e-6:
            moved += 1
    check(moved == 3, f"all actors posed at mid-range ({moved}/3)")
    # fake-user hygiene across the ensemble
    purged = rh_canvas.purge_unassigned()
    check(isinstance(purged, dict), "purge runs on the ensemble")


ROWS_SPEC = [
    ("F1_catalog", f1_catalog),
    ("F2_fetch_verify", f2_fetch_verify),
    ("F3_import_clip", f3_import_clip),
    ("F3b_teacher_refusal", f3b_teacher_refusal),
    ("F4_mannequin", f4_mannequin),
    ("F5_bind_playback", f5_bind_playback),
    ("F5b_bind_refusals", f5b_bind_refusals),
    ("F5c_swap_unpin", f5c_swap_unpin),
    ("F5d_registry_fingerprint", f5d_registry_fingerprint),
    ("F6_statue", f6_statue),
    ("F7_glb_roundtrip", f7_glb_roundtrip),
    ("F8_placement", f8_placement),
    ("F9_ensemble", f9_ensemble),
    ("F10_rh3d_layout", f10_rh3d_layout),
]

for rid, fn in ROWS_SPEC:
    row(rid, fn)

n_pass = sum(1 for v in ROWS.values() if v == 'pass')
n_fail = sum(1 for v in ROWS.values() if v == 'fail')
n_skip = sum(1 for v in ROWS.values() if v == 'skip')
print(f"\n[test_rh_fix] SUMMARY: {n_pass} pass, {n_fail} fail, "
      f"{n_skip} skip", flush=True)
for rid in ROWS_SPEC:
    print(f"  {rid[0]}: {ROWS.get(rid[0], 'missing')}", flush=True)

with open(OUT, "w") as f:
    json.dump({"rows": ROWS, "failures": FAIL}, f, indent=1)

if not LIB_OK:
    # the honest-skip protocol (suite_runner lines 215-223): exit 2 +
    # the SUITE-SKIP marker — a zero-coverage run must NOT score PASS
    print("SUITE-SKIP: fixture library absent — build it first "
          "(scripts/rh_fixture_lib.py)", flush=True)
    sys.exit(2)
if FAIL:
    print(f"[test_rh_fix] ALL FAIL: {FAIL}", flush=True)
    sys.exit(1)
print("[test_rh_fix] ALL PASS", flush=True)
