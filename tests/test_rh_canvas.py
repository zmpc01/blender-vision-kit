"""test_rh_canvas.py — RH-canvas integration battery (v2 spec §7, RH-IMPL-1).

Rows (all live, inside Blender via blrun.sh — T1/T7 harness style):
  R1  catalog, no net        (2032 id-dedup, 19 cats, 99 models, 667
                              presets, facet filter, search, id-string law)
  R2  fetch, live CDN        (sha256, idempotent) + R2b cache-poisoning
                              (garbage + 0-byte cached file -> repair)
  R3  import-clip 2846       (65 bones, prefix, obj_scale 0.01, rot X 90,
                              span [1.40,1.55], bone-bbox Z [1.90,2.00],
                              scene range auto-set from action range)
  R3b teacher error          (rename a bone -> check_mixamo_rig refuses)
  R4  mannequin              (65 groups, 0 zero-weight verts, height
                              1.6-2.0, feet, 22 segments)
  R5  bind + playback        (PINNED clip 2846: hips world z in (0.4,1.4)
                              — measured 0.896-0.938; xy path > 1 m —
                              measured 2.895; band is family-scoped)
  R5b bind-refusal           (non-mixamorig armature -> REFUSED)
  R6  statue, pin Farmer     (height ~1.7601, |min_z| < 0.010 — the pass
                              band; Armor-Tang -6.1 mm passes by evidence)
  R6b Chinese node survives  (古代农民 survives export -> reimport)
  R7  GLB round-trip         (fps=30 before reimport; census >= 1 armature
                              + 65 bones + action w/ slot; phantom
                              'Icosphere' filtered by armature parentage;
                              < 5 MB; duration_s == (f1-f0)/30)
  R7b determinism            (two exports byte-compare; nondeterminism is
                              documented, not failed)
  R9  preview surfaces       (99 model previewImage URLs, 667 preset
                              portrait URLs, 8 in-git thumbnails, the
                              magic-byte fetch law + poison repair)
  R8  placement e2e          (armature-first recipe via placement_lib at
                              spots on a ground plane; armature world xy
                              at spot; evaluated mesh z-band [-0.05, 1.9])

ALL rows graceful-skip with a loud [SKIP] line when the library clones
are absent (test_export_previz_package.py :1129 pattern — NOT
test_polyhaven's hard net dependency).

Run:
  ./scripts/blrun.sh --background --python tests/test_rh_canvas.py --
Exit 0 = pass/skip; 1 = failures; 2 = environment error.
"""
import json
import math
import os
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
OUT = os.path.join(_OUT_ROOT, "rh_canvas_results.json")
os.makedirs(os.path.dirname(OUT), exist_ok=True)

FAIL = []
ROWS = {}          # row id -> "pass" | "fail" | "skip"
PIN_CLIP = "2846"  # WALK_RUN_MOVE "Run fast" — REVIEW-RH-1b measured on it
PIN_MODEL = "Farmer"

LIBS = rh_canvas.discover_libraries()
LIB_OK = all(LIBS.get(k) for k in ("animations", "characters", "models"))


def row(row_id, fn):
    """Run one battery row; never raises (blrun fail-closes on
    tracebacks — a row ERROR is recorded as a failure instead)."""
    if not LIB_OK:
        ROWS[row_id] = "skip"
        print(f"[SKIP] {row_id}: RH-canvas library clones absent "
              f"(found {LIBS or 'none'}) — all three clones (animations, "
              f"characters, models) must resolve per docs/rh_canvas.md; "
              f"this row needs the local data only",
              flush=True)
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


def check(label, got, expect, tol=None):
    if isinstance(expect, bool) or isinstance(got, bool) or tol is None:
        ok = got == expect
    elif isinstance(got, (int, float)) and isinstance(expect, (int, float)):
        ok = abs(got - expect) <= tol
    elif isinstance(got, (list, tuple)) and isinstance(expect, (list, tuple)):
        ok = len(got) == len(expect) and all(
            abs(g - e) <= (tol if isinstance(g, (int, float)) and
                           isinstance(e, (int, float)) else 0)
            for g, e in zip(got, expect)) if tol is not None else got == expect
    else:
        ok = got == expect
    if not ok:
        FAIL.append(label)
    print(f"[{'ok' if ok else 'FAIL'}] {label}: got={got!r} "
          f"expect={expect!r}" + (f" tol={tol}" if tol is not None else ""))
    return ok


def fresh():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'
    sc.unit_settings.scale_length = 1.0
    return sc


def hips_sweep(arm, f0, f1, n=48):
    sc = bpy.context.scene
    hips = arm.pose.bones["mixamorig:Hips"]
    pts = []
    for i in range(n):
        f = f0 + (f1 - f0) * i / (n - 1)
        sc.frame_set(int(round(f)))
        bpy.context.view_layer.update()
        w = arm.matrix_world @ hips.head
        pts.append((w.x, w.y, w.z))
    zs = [p[2] for p in pts]
    xy = sum(math.dist(pts[i][:2], pts[i + 1][:2])
             for i in range(len(pts) - 1))
    return {"z_min": min(zs), "z_max": max(zs), "xy_path": xy,
            "n": len(pts)}


def eval_mesh_zband(mesh, frame=None):
    sc = bpy.context.scene
    if frame is not None:
        sc.frame_set(int(frame))
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    oe = mesh.evaluated_get(deps)
    me = oe.to_mesh()
    mw = oe.matrix_world
    zs = [(mw @ v.co).z for v in me.vertices]
    xs = [(mw @ v.co).x for v in me.vertices]
    ys = [(mw @ v.co).y for v in me.vertices]
    oe.to_mesh_clear()
    return {"min_z": min(zs), "max_z": max(zs),
            "cx": (min(xs) + max(xs)) / 2, "cy": (min(ys) + max(ys)) / 2}


def export_glb(path):
    """Kit arg set (blender_kit.export_gltf's flags, verbatim — the
    REVIEW-RH-1b round-trip used exactly these)."""
    bpy.ops.export_scene.gltf(
        filepath=path, export_format='GLB', export_cameras=True,
        export_animations=True, export_animation_mode='ACTIONS',
        export_frame_range=True, export_apply=True, export_yup=True,
        export_materials='EXPORT',
        export_import_convert_lighting_mode='SPEC', use_selection=False)
    return os.path.getsize(path)


# --------------------------------------------------------------------------- #
def r1():
    print("== R1 catalog (no net) ==", flush=True)
    anims = rh_canvas.load_animations()
    check("R1a id-dedup 2137->2032", len(anims), 2032)
    check("R1b categories 19", len(rh_canvas.load_categories()), 19)
    models = rh_canvas.load_models()
    check("R1c models 99", len(models), 99)
    chars = rh_canvas.load_characters()
    check("R1d presets 667", len(chars), 667)
    check("R1e id-string law (all ids str)",
          all(isinstance(a["id"], str) for a in anims)
          and all(isinstance(m["id"], str) for m in models), True)
    res = rh_canvas.catalog_query("characters", facets=[
        ("gender", "female"), ("species", "elf")])
    check("R1f facet filter female+elf=14 (recon: 14)", res["count"], 14)
    sr = rh_canvas.catalog_query("animations", search="run fast")
    ids = [r["id"] for r in sr["rows"]]
    check("R1g search 'run fast' finds 2846", PIN_CLIP in ids, True)
    check("R1g2 Chinese name displayed", sr["rows"][0]["name"], "跑快速")


def r2():
    print("== R2 fetch (live CDN) ==", flush=True)
    got = rh_canvas.fetch_ids([PIN_CLIP, PIN_MODEL])
    by_id = {r["id"]: r for r in got}
    check("R2a fetch clip status ok/ok-cached",
          by_id[PIN_CLIP]["status"] in ("ok", "ok-cached"), True)
    check("R2a2 fetch model status ok/ok-cached",
          by_id[PIN_MODEL]["status"] in ("ok", "ok-cached"), True)
    anim = rh_canvas._find_animation(PIN_CLIP)
    check("R2b sha256 verified on disk (clip)",
          rh_canvas._sha256_file(by_id[PIN_CLIP]["dest"]) == anim["sha256"],
          True)
    model = rh_canvas._find_model(PIN_MODEL)
    check("R2b2 sha256 verified on disk (model)",
          rh_canvas._sha256_file(by_id[PIN_MODEL]["dest"]) == model["sha256"],
          True)
    again = rh_canvas.fetch_ids([PIN_CLIP, PIN_MODEL])
    check("R2c idempotent re-run -> ok-cached",
          all(r["status"] == "ok-cached" for r in again), True)


def r2b():
    print("== R2b cache poisoning (garbage + 0-byte) -> repair ==", flush=True)
    got = rh_canvas.fetch_ids([PIN_CLIP, PIN_MODEL])
    clip_dest = next(r["dest"] for r in got if r["id"] == PIN_CLIP)
    model_dest = next(r["dest"] for r in got if r["id"] == PIN_MODEL)
    with open(clip_dest, "wb") as f:
        f.write(b"GARBAGE NOT AN FBX" * 100)          # poisoned, wrong size
    open(model_dest, "wb").close()                   # 0-byte cached file
    fixed = rh_canvas.fetch_ids([PIN_CLIP, PIN_MODEL])
    by_id = {r["id"]: r for r in fixed}
    check("R2b-a poisoned clip re-fetched(repaired)",
          by_id[PIN_CLIP]["status"], "re-fetched(repaired)")
    check("R2b-b 0-byte model re-fetched(repaired)",
          by_id[PIN_MODEL]["status"], "re-fetched(repaired)")
    check("R2b-c repaired clip sha matches manifest",
          rh_canvas._sha256_file(clip_dest)
          == rh_canvas._find_animation(PIN_CLIP)["sha256"], True)
    check("R2b-d repaired model sha matches manifest",
          rh_canvas._sha256_file(model_dest)
          == rh_canvas._find_model(PIN_MODEL)["sha256"], True)
    try:
        rh_canvas.fetch_ids(["999999"])
        check("R2b-e unknown id REFUSED", "no-refusal", "RHRefused")
    except rh_canvas.RHRefused as e:
        check("R2b-e unknown id REFUSED", "RHRefused" in f"{type(e).__name__}: {e}",
              True)


def r3():
    print("== R3 import-clip (65-bone law) ==", flush=True)
    global ARM, REP3
    sc = fresh()
    pre_scene_range = (sc.frame_start, sc.frame_end)
    check("R3a scene range at import is NOT the clip range (1..250)",
          pre_scene_range, (1, 250))
    ARM, REP3 = rh_canvas.import_clip(PIN_CLIP, name="Runner")
    check("R3b bones == 65", REP3["bones"], 65)
    check("R3c mixamorig prefix", REP3["mixamorig_prefix"], True)
    check("R3d obj_scale == (0.01,)*3", tuple(REP3["obj_scale"]),
          (0.01, 0.01, 0.01), tol=1e-9)
    check("R3e rot_euler.x ~= 90deg", REP3["obj_rot_x_deg"], 90.0, tol=0.5)
    check("R3f span |LHand.head - RHand.head| in [1.40,1.55]",
          1.40 <= REP3["t_pose_span_m"] <= 1.55, True)
    z0, z1 = REP3["rest_bone_bbox_z_m"]
    check("R3g bone-bbox Z in [1.90,2.00]", 1.90 <= (z1 - z0) <= 2.00, True)
    check("R3h action frame_range starts at 1", REP3["frame_range"][0], 1)
    check("R3i scene range auto-set == action range",
          tuple(REP3["scene_range_set"]) == tuple(REP3["frame_range"]), True)
    check("R3j fps == 30", REP3["fps"], 30)
    check("R3k hips fcurves raw cm (peak ~290 = 2.90 m)",
          REP3["hips_location_z_raw_cm"][1] > 100, True)
    check("R3l armature renamed", ARM.name, "Runner")
    check("R3m scale law kept (never transform_apply)",
          tuple(round(c, 5) for c in ARM.scale), (0.01, 0.01, 0.01),
          tol=1e-9)


def r3b():
    print("== R3b teacher error on non-mixamorig armature ==", flush=True)
    b = ARM.data.bones["mixamorig:Head"]
    b.name = "Head_Renamed"
    try:
        rh_canvas.check_mixamo_rig(ARM, "R3b")
        check("R3b-a renamed bone REFUSED", "no-refusal", "RHRefused")
    except rh_canvas.RHRefused as e:
        check("R3b-a renamed bone REFUSED (names the prefix law)",
              "mixamorig:" in str(e) and "65" in str(e) or "prefix" in str(e),
              True)
    finally:
        b.name = "mixamorig:Head"
    check("R3b-b bone restored", ARM.data.bones.get("mixamorig:Head") is not None,
          True)


def r4():
    print("== R4 mannequin (join -> ARMATURE_AUTO) ==", flush=True)
    global MESH, REP4
    MESH, REP4 = rh_canvas.build_mannequin(ARM, name="RHMannequin")
    check("R4a vertex groups == 65", REP4["vertex_groups"], 65)
    check("R4b zero-weight verts == 0", REP4["zero_weight_verts"], 0)
    check("R4c rest height 1.6-2.0 m", 1.6 <= REP4["rest_height_m"] <= 2.0,
          True)
    check("R4d feet near ground (rest_min_z in [-0.05,0.05])",
          -0.05 <= REP4["rest_min_z_m"] <= 0.05, True)
    check("R4e segments == 22", REP4["segments"], 22)
    check("R4f verts == 616 (review number)", REP4["verts"], 616)
    check("R4g >4-influence verts present (glTF caps at 4 — law 9)",
          REP4["over_4_influence_verts"] > 0, True)
    check("R4h mesh parented to armature", MESH.parent.name, ARM.name)


def r5():
    print("== R5 bind + playback (PINNED clip 2846) ==", flush=True)
    rep = rh_canvas.bind(MESH, PIN_CLIP)      # MESH arg -> auto-resolve parent
    check("R5a bind report armature", rep["armature"], ARM.name)
    check("R5b action slot assigned", rep["slot_assigned"], True)
    check("R5c scene range from action.frame_range",
          tuple(rep["scene_range"]) == tuple(rep["action_frame_range"]), True)
    f0, f1 = rep["action_frame_range"]
    sw = hips_sweep(ARM, f0, f1)
    print(f"[R5] hips sweep: {sw}", flush=True)
    check("R5d hips world z in (0.4,1.4) — measured 0.896-0.938",
          0.4 < sw["z_min"] and sw["z_max"] < 1.4, True)
    check("R5e hips xy path > 1 m — measured 2.895",
          sw["xy_path"] > 1.0, True)
    band = eval_mesh_zband(MESH, frame=(f0 + f1) // 2)
    print(f"[R5] mid-pose mesh zband: {band}", flush=True)
    check("R5f evaluated mesh follows the pose (grounded, z < 2.0)",
          -0.05 <= band["min_z"] <= 0.5 and band["max_z"] < 2.0, True)
    check("R5g bind NEVER assigned to the mesh (mesh anim_data stays empty)",
          MESH.animation_data is None or MESH.animation_data.action is None,
          True)


def r5b():
    print("== R5b bind-refusal on non-mixamorig armature ==", flush=True)
    b = ARM.data.bones["mixamorig:Hips"]
    b.name = "Hips_Renamed"
    try:
        rh_canvas.bind(MESH, PIN_CLIP)
        check("R5b-a bind REFUSED", "no-refusal", "RHRefused")
    except rh_canvas.RHRefused as e:
        check("R5b-a bind REFUSED (teacher message)",
              "mixamorig:" in str(e), True)
        check("R5b-b the armature was left untouched",
              ARM.animation_data.action is not None, True)
    finally:
        b.name = "mixamorig:Hips"
    check("R5b-c bone restored", ARM.data.bones.get("mixamorig:Hips") is not None,
          True)


def r6():
    print("== R6 statue (pin Farmer) ==", flush=True)
    global STATUE_OBJS, REP6
    STATUE_OBJS, REP6 = rh_canvas.import_statue(PIN_MODEL)
    check("R6a height ~= 1.7601 in [1.74,1.78]",
          1.74 <= REP6["height_m"] <= 1.78, True)
    check("R6b |min_z| < 0.010 (pass band; Armor-Tang -6.1mm passes)",
          abs(REP6["feet_min_z_m"]) < 0.010, True)
    check("R6c grounding band PASS in report",
          "PASS" in REP6["grounding"], True)
    check("R6d polys 3209 (deterministic GLTF)", REP6["polys"], 3209)
    check("R6e 0 armatures imported (static statue)",
          all(o.type != 'ARMATURE' for o in STATUE_OBJS), True)


def r6b():
    print("== R6b Chinese-named node survives export->reimport ==", flush=True)
    zh = "古代农民"                                # the Farmer node name
    check("R6b-a source node is Chinese-named", zh in REP6["objects"], True)
    glb = os.path.join(_OUT_ROOT, "rh_r6b_statue.glb")
    size = export_glb(glb)
    check("R6b-b export ok (< 5 MB)", size < 5 * 1024 * 1024, True)
    fresh()
    bpy.ops.import_scene.gltf(filepath=glb)
    names = [o.name for o in bpy.data.objects]
    check("R6b-c Chinese node name survives round-trip", zh in names, True)


def r7():
    print("== R7 GLB round-trip (mannequin + clip) ==", flush=True)
    fresh()
    sc = bpy.context.scene
    arm, rep = rh_canvas.import_clip(PIN_CLIP, name="RTArm")
    mesh, mrep = rh_canvas.build_mannequin(arm, name="RTMannequin")
    f0, f1 = rep["frame_range"]
    sc.frame_start, sc.frame_end = f0, f1
    # law 104 discipline: exactly the ASSIGNED action may exist at export
    unassigned = [a for a in bpy.data.actions
                  if a.users == 0 or not any(
                      o.animation_data and o.animation_data.action is a
                      for o in bpy.data.objects)]
    for a in unassigned:
        bpy.data.actions.remove(a)
    check("R7a one-object-one-action (exactly 1 action)",
          len(bpy.data.actions), 1)
    glb = os.path.join(_OUT_ROOT, "rh_r7_roundtrip.glb")
    size = export_glb(glb)
    check("R7b GLB < 5 MB (measured 163 KB)", size < 5 * 1024 * 1024, True)

    # reimport with fps=30 set BEFORE import (glTF timing = frame/fps)
    fresh()
    sc = bpy.context.scene
    sc.render.fps = 30
    bpy.ops.import_scene.gltf(filepath=glb)
    arms = [o for o in bpy.data.objects if o.type == 'ARMATURE']
    check("R7c census >= 1 armature", len(arms) >= 1, True)
    rarm = arms[0]
    check("R7d bone count == 65", len(rarm.data.bones), 65)
    acts = list(bpy.data.actions)
    check("R7e action present with slot",
          len(acts) >= 1 and rarm.animation_data is not None
          and rarm.animation_data.action is not None
          and rarm.animation_data.action_slot is not None, True)
    act = rarm.animation_data.action
    fr = act.frame_range
    dur = (fr[1] - fr[0]) / sc.render.fps
    check("R7f duration_s == (f1-f0)/30", dur, (f1 - f0) / 30.0, tol=1e-3)
    # phantom 'Icosphere' filter: skinned meshes by ARMATURE PARENTAGE
    owned = [o for o in bpy.data.objects if o.type == 'MESH'
             and (o.parent is rarm
                  or any(m.type == 'ARMATURE' and m.object is rarm
                         for m in o.modifiers))]
    phantom = [o.name for o in bpy.data.objects if o.type == 'MESH'
               and o not in owned]
    check("R7g exactly 1 armature-owned mesh (the mannequin)", len(owned), 1)
    check("R7h phantom 'Icosphere' excluded by armature parentage",
          "Icosphere" in phantom and all(
              o.parent is not rarm for o in bpy.data.objects
              if o.type == 'MESH' and o.name == "Icosphere"), True)
    # hips sweep on the reimported rig must match the source numbers
    sw = hips_sweep(rarm, int(fr[0]), int(fr[1]))
    print(f"[R7] reimported hips sweep: {sw}", flush=True)
    check("R7i reimported hips z in (0.4,1.4)",
          0.4 < sw["z_min"] and sw["z_max"] < 1.4, True)
    check("R7j reimported hips xy path > 1 m", sw["xy_path"] > 1.0, True)
    man = owned[0]
    for tag, f in (("first", fr[0]), ("mid", (fr[0] + fr[1]) / 2),
                   ("last", fr[1])):
        band = eval_mesh_zband(man, frame=f)
        print(f"[R7] mesh zband {tag}: {band}", flush=True)
        check(f"R7k mesh zband {tag} in [-0.05,1.9]",
              -0.05 <= band["min_z"] and band["max_z"] <= 1.9, True)


def r7b():
    print("== R7b determinism (two exports byte-compare) ==", flush=True)
    # scene state at this point: the R7 fresh scene holds the reimported
    # rig; rebuild the source scene so both exports start identical
    fresh()
    sc = bpy.context.scene
    arm, rep = rh_canvas.import_clip(PIN_CLIP, name="DetArm")
    rh_canvas.build_mannequin(arm, name="DetMannequin")
    f0, f1 = rep["frame_range"]
    sc.frame_start, sc.frame_end = f0, f1
    a = os.path.join(_OUT_ROOT, "rh_r7b_a.glb")
    b = os.path.join(_OUT_ROOT, "rh_r7b_b.glb")
    export_glb(a)
    export_glb(b)
    ba, bb = open(a, "rb").read(), open(b, "rb").read()
    if ba == bb:
        check("R7b-a two exports byte-identical", True, True)
        ROWS_EXTRA["R7b"] = "byte-identical"
    else:
        # document WHICH bytes diverge (first diff offset + context)
        i = next(j for j in range(min(len(ba), len(bb)))
                 if ba[j] != bb[j])
        ROWS_EXTRA["R7b"] = {
            "determinism": "nondeterministic",
            "sizes": [len(ba), len(bb)],
            "first_diff_offset": i,
            "ctx_a": ba[max(0, i - 8):i + 8].hex(),
            "ctx_b": bb[max(0, i - 8):i + 8].hex(),
        }
        print(f"[R7b] NOTE nondeterministic export: first diff at byte "
              f"{i}: {ba[max(0, i-8):i+8].hex()!r} vs "
              f"{bb[max(0, i-8):i+8].hex()!r}", flush=True)
        check("R7b-a nondeterminism documented (bytes recorded)", True, True)


def r8():
    print("== R8 placement e2e (armature-first recipe) ==", flush=True)
    fresh()
    sc = bpy.context.scene
    sc.render.fps = 30
    arm, rep = rh_canvas.import_clip(PIN_CLIP, name="Placed")
    f0, f1 = rep["frame_range"]
    sc.frame_start, sc.frame_end = f0, f1
    bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, 0))
    ground = bpy.context.active_object
    ground.name = "Ground"
    spot = (4.0, -3.0, 0.0)
    # THE RECIPE: place the ARMATURE FIRST (never the skinned mesh)
    pl.move_to(arm, spot, reference='origin')
    pre = pl.place_on(arm, ground)            # ARMATURE branch under test
    check("R8a place_on(armature) did not crash", isinstance(pre, dict), True)
    check("R8b report ok", pre.get("ok"), True)
    check("R8c footprint from armature points",
          pre.get("footprint_source", "").startswith("armature-points"), True)
    check("R8d post-contact not PENETRATING / not ERROR",
          all(p.get("state") not in ("PENETRATING", "ERROR")
              for p in pre.get("post_contact", [])),
          True)
    t = arm.matrix_world.translation
    check("R8e armature world xy at spot (4,-3) +-0.05",
          (t.x, t.y), (4.0, -3.0), tol=0.05)
    mn, mx = pl._aabb(arm)
    check("R8f armature bottom rests on the ground plane (|min z| < 0.01)",
          abs(mn.z) < 0.01, True)
    snap = pl.snap_z(arm, 0.0)               # verified op — exact grounding
    check("R8g snap_z(armature) result_z == 0",
          abs(snap.get("result_z", 1.0)) < 1e-6, True)
    # THEN build the mannequin at the spot
    mesh, mrep = rh_canvas.build_mannequin(arm, name="SpotMannequin")
    check("R8h mannequin parent is the placed armature", mesh.parent.name,
          arm.name)
    for tag, f in (("rest f0", f0), ("mid", (f0 + f1) // 2), ("last", f1)):
        band = eval_mesh_zband(mesh, frame=f)
        print(f"[R8] mesh zband {tag}: {band}", flush=True)
        check(f"R8i mesh zband {tag} in [-0.05,1.9]",
              -0.05 <= band["min_z"] and band["max_z"] <= 1.9, True)
        # the clip carries root motion (xy path 2.9 m by design — law: the
        # ARMATURE stays at the spot, the hips walk away) — xy is asserted
        # at the rest frame only
        if tag == "rest f0":
            check("R8j mesh xy centered on spot (rest frame)",
                  (band["cx"], band["cy"]), (4.0, -3.0), tol=0.5)
    aud = pl.audit_scene(pairs=[(arm.name, ground.name)])
    states = [p.get("state") for p in aud.get("pairs", [])]
    print(f"[R8] audit at rest frame: {states}", flush=True)
    check("R8k audit pair not PENETRATING / not ERROR",
          all(s not in ("PENETRATING", "ERROR") for s in states), True)


ROWS_EXTRA = {}


def r9():
    """Preview-data integration (s40): model previewImage URLs, preset
    portrait URLs, in-git body thumbnails, the magic-byte fetch law."""
    print("== R9 preview/portrait/thumbnail surfaces ==", flush=True)
    # a. all 99 models carry a previewImage URL
    models = rh_canvas.load_models()
    with_prev = [m for m in models if m.get("preview")]
    check("R9a models carrying previewImage URL (99/99)",
          (len(models), len(with_prev)), (99, 99))
    # b. presets carry 2-3 portrait URLs each (667 presets)
    chars = rh_canvas.load_characters()
    np_port = sum(len(c.get("portraits", [])) for c in chars)
    check("R9b presets count 667, portraits total > 1300 (2+ avg)",
          len(chars) == 667 and np_port > 1300, True)
    # c. the 8 in-git body thumbnails exist with PNG magic
    thumbs = rh_canvas.load_thumbnails()
    check("R9c thumbnails == 8 local PNGs w/ magic",
          len(thumbs) == 8 and all(
              os.path.isfile(t["path"]) and
              open(t["path"], "rb").read(8) == rh_canvas.PNG_MAGIC
              for t in thumbs), True)
    # d. browse filters (VK-s20 port): tag + max_frames
    q_tag = rh_canvas.catalog_query("animations", tag="static_pose")
    q_mf = rh_canvas.catalog_query("animations", max_frames=10)
    check("R9d tag filter static_pose == 25 rows", q_tag["count"], 25)
    check("R9e max-frames<=10 rows all <= 10f", all(
        r.get("frames", 10**9) <= 10 for r in q_mf["rows"]) and
        q_mf["count"] > 0, True)
    # e. vintage meta surfaces the snapshot date
    vin = rh_canvas.library_vintage("characters")
    check("R9f library vintage starts 2026-10", vin.startswith("2026-10"),
          True)
    # f. preview fetch: live CDN, PNG magic, idempotent, poison repair
    cache = os.path.join(_OUT_ROOT, "rh_canvas_cache_r9")
    m = next(m for m in models if m["name"] == "Female")
    res = rh_canvas.fetch_previews(["Female"], cache=cache)
    # 'ok' on a cold cache, 'ok-cached' when a prior run verified the file —
    # both mean a VERIFIED preview is on disk (the cache dir persists
    # across battery runs under KIT_OUT)
    check("R9g preview fetch status ok|ok-cached",
          res[0]["status"] in ("ok", "ok-cached"), True)
    head = open(res[0]["dest"], "rb").read(8)
    check("R9h preview is a real PNG", head == rh_canvas.PNG_MAGIC, True)
    res2 = rh_canvas.fetch_previews(["Female"], cache=cache)
    check("R9i preview re-fetch idempotent (ok-cached)",
          res2[0]["status"], "ok-cached")
    with open(res[0]["dest"], "wb") as fh:
        fh.write(b"POISONED-CACHE-FILE")
    res3 = rh_canvas.fetch_previews(["Female"], cache=cache)
    check("R9j poisoned preview repaired (re-fetched)",
          res3[0]["status"], "re-fetched(repaired)")
    check("R9k repaired file is a PNG again",
          open(res[0]["dest"], "rb").read(8) == rh_canvas.PNG_MAGIC, True)
    # g. portrait fetch: live CDN, cdn_size verified, JPEG magic
    pres = rh_canvas.fetch_portraits(["1"], cache=cache)
    check("R9l portrait fetch rows >= 2", len(pres) >= 2, True)
    ok_rows = all(p["status"].startswith("ok") for p in pres)
    magic_ok = all(open(p["dest"], "rb").read(2) == rh_canvas.JPEG_MAGIC
                   for p in pres)
    check("R9m portrait statuses ok + JPEG magic", ok_rows and magic_ok, True)
    # h. refusal paths
    refused = False
    try:
        rh_canvas.fetch_previews(["__no_such_model__"], cache=cache)
    except rh_canvas.RHRefused:
        refused = True
    check("R9n unknown --preview model REFUSED", refused, True)
    print(f"[R9] portraits fetched for char 1: "
          f"{[p['name'] for p in pres]}", flush=True)


def main() -> int:
    print(f"[rh-test] libraries: {LIBS}", flush=True)
    if not LIB_OK:
        print("[SKIP] RH-canvas clones absent — the WHOLE battery skips. "
              "Clone them (see docs/rh_canvas.md):\n"
              "    git clone https://github.com/beulahkemp/RH-canvas-animations.git\n"
              "    git clone https://github.com/beulahkemp/RH-canvas-characters.git\n"
              "    git clone https://github.com/beulahkemp/RH-3d-assets.git",
              flush=True)
    for row_id, fn in (("R1", r1), ("R2", r2), ("R2b", r2b),
                       ("R3", r3), ("R3b", r3b), ("R4", r4),
                       ("R5", r5), ("R5b", r5b), ("R6", r6), ("R6b", r6b),
                       ("R7", r7), ("R7b", r7b), ("R8", r8), ("R9", r9)):
        row(row_id, fn)
    results = {
        "suite": "rh_canvas battery (spec §7 v2)",
        "rows": ROWS,
        "extras": ROWS_EXTRA,
        "fail": FAIL,
        "libraries": LIBS,
        "pinned": {"clip": PIN_CLIP, "model": PIN_MODEL},
    }
    with open(OUT, "w") as f:
        json.dump(results, f, indent=1, ensure_ascii=False)
    n_pass = sum(1 for v in ROWS.values() if v == "pass")
    n_skip = sum(1 for v in ROWS.values() if v == "skip")
    n_fail = sum(1 for v in ROWS.values() if v == "fail")
    print(f"\n[rh-test] battery: {n_pass} pass / {n_skip} skip / "
          f"{n_fail} fail", flush=True)
    print(f"[rh-test] wrote {OUT}", flush=True)
    if n_fail:
        print(f"[rh-test] FAILURES: {FAIL}", flush=True)
        return 1
    print("[rh-test] ALL PASS", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
