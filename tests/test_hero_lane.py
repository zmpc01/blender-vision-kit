"""test_hero_lane.py — the s21-D hero lane battery (wrapper + loader +
retarget + staging world gates).

Rows (honest-skip when the vendored assets are absent — exit 2):
  H1  wrapper_rig laws: refusals (non-ARMATURE / parented / name
      collision), wrap() on the Quaternius male, probe report (sign,
      bone, fwd), scale lives in the MPI (never keyed), mesh rides.
  H2  assets_quaternius loader: male+female load, 42-bone census, 11-
      action pool with stripped keys, height/feet gates, recolor sweep.
  H3  rig_retarget UAL Walk_Loop -> Quaternius male: coverage, formula
      closure (staging-immune), teleport guard, fresh-bake-only name,
      source action unmutated, fake_user False pre-bind.
  H4  retarget refusals: non-QUATERNION target mode; stale output name.
  H5  staging world gates: the retargeted walk staged through the
      wrapper reads feet world-z in the ground band + a gait-class
      hips span (two-column law: numbers HERE, strips in the lab).
  H6  bind-and-play: assign the retargeted action, frame-evaluate the
      wrapper-staged rig, world hips z sane across the range.

Prints [hero] lines; exit 0 + ALL PASS.
"""
import os
import sys
import math
import traceback

import bpy
from mathutils import Matrix, Vector

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import wrapper_rig            # noqa: E402
import assets_quaternius      # noqa: E402
import rig_retarget           # noqa: E402

FAIL = []
ROWS = {}
_MALE = os.path.join(_REPO, "assets", "vendor", "quaternius",
                     "Male_Casual.fbx")
_FEMALE = os.path.join(_REPO, "assets", "vendor", "quaternius",
                       "Female_Casual.fbx")
if not (os.path.isfile(_MALE) and os.path.isfile(_FEMALE)):
    print("[hero] SUITE-SKIP: vendored Quaternius FBXs absent")
    sys.exit(2)


def check(label, got, expect, tol=None):
    ok = (got == expect) if tol is None else abs(got - expect) <= tol
    print(f"[hero] {'PASS' if ok else 'FAIL'}: {label} "
          f"(got {got!r}, expect {expect!r})", flush=True)
    if not ok:
        FAIL.append(label)


def row(row_id, fn):
    n0 = len(FAIL)
    try:
        fn()
        if len(FAIL) > n0:
            ROWS[row_id] = "fail"
            print(f"[hero] [row] {row_id}: FAIL (check failures)",
                  flush=True)
        else:
            ROWS[row_id] = "pass"
            print(f"[hero] [row] {row_id}: PASS", flush=True)
    except Exception:                                # noqa: BLE001
        ROWS[row_id] = "fail"
        FAIL.append(row_id)
        print(f"[hero] [row] {row_id}: FAIL\n"
              f"{traceback.format_exc(limit=4)}", flush=True)


def fresh():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    sc = bpy.context.scene
    sc.render.fps = 30


def world_z(arm, bone_sub):
    for pb in arm.pose.bones:
        n = pb.name.lower()
        if bone_sub in n and not n.endswith("_end"):
            return (arm.matrix_world @ pb.matrix).translation.z
    return None


# ------------------------------------------------------------------ #
def h1_wrapper_laws():
    fresh()
    bpy.ops.import_scene.fbx(filepath=_MALE)
    arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    arm.name = "HumanArmature"

    # refusals (the canonical wrapper raises RuntimeError fail-closed)
    try:
        wrapper_rig.wrap(None, "Nope")
        raise AssertionError("wrap accepted None")
    except RuntimeError:
        pass
    wrapper_rig.wrap(arm, "HeroA", scale=1.0)
    try:
        wrapper_rig.wrap(arm, "HeroB")   # already parented now
        raise AssertionError("wrap accepted a parented armature")
    except RuntimeError:
        pass
    try:
        e = bpy.data.objects.new("Collide.Root", None)
        bpy.context.scene.collection.objects.link(e)
        wrapper_rig.wrap(arm, "Collide")
        raise AssertionError("wrap accepted a name collision")
    except RuntimeError:
        pass

    # the male rig faces -Y (measured) -> sign -1, flip MPI
    fresh()
    bpy.ops.import_scene.fbx(filepath=_MALE)
    arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    r = wrapper_rig.wrap(arm, "Hero", scale=0.5)
    # the canonical wrapper's facing contract: probe_axis = WHICH LOCAL
    # AXIS is the toe axis (+1 = local +Y — its measured world forward
    # is (0.377, -0.926, ...) on this rig). CROSS-LANE NOTE (s22): the
    # UAL module's older semantics flip on the WORLD facing (fwd.y<0 ->
    # flip) — the two conventions diverge for +Y-axis/-Y-world rigs;
    # the lab stages yaw per-hero anyway (wrapper law), flagged in the
    # design doc D-revision 3.
    check("H1 probe axis +1 (toe axis is local +Y)", r["probe_axis"], 1)
    check("H1 probe bone Foot.L", r["probe_bone"], "Foot.L")
    check("H1 probe fwd y-dominant", abs(r["fwd"][1]) >= 0.5, True)
    check("H1 root exists", r["root"].name, "Hero.Root")
    check("H1 meshes discovered", [m.name for m in r["meshes"]],
          ["BaseHuman"])
    check("H1 mesh rides armature",
          r["meshes"][0].parent.name, arm.name)
    # D1b refusal: unparent the skinned mesh at scale != 1
    fresh()
    bpy.ops.import_scene.fbx(filepath=_MALE)
    arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    mesh = next(o for o in bpy.data.objects if o.type == 'MESH')
    mesh.parent = None
    try:
        wrapper_rig.wrap(arm, "HeroD", scale=0.5)
        raise AssertionError("D1b: unparented mesh at scale!=1 accepted")
    except RuntimeError:
        pass
    # restore the ride, then the MPI check
    mesh.parent = arm
    mesh.matrix_parent_inverse = Matrix()
    r2 = wrapper_rig.wrap(arm, "Hero", scale=0.5)
    mpi = arm.matrix_parent_inverse
    check("H1 MPI carries 0.5", round(mpi.median_scale, 4), 0.5, 1e-3)
    check("H1 wrapper not keyed", r2["root"].animation_data is None
          or r2["root"].animation_data.action is None, True)


def h2_loader():
    fresh()
    rep = assets_quaternius.load("male", "HeroM")
    check("H2 male bones", len(rep["arm"].data.bones), 42)
    check("H2 male pool", sorted(rep["pool"]),
          sorted(["Walk", "Idle", "Jump", "Death", "Clapping", "Punch",
                  "Run", "RunningJump", "Sitting", "Standing",
                  "SwordSlash"]))
    check("H2 male height band", 1.2 <= rep["height"] <= 2.2, True)
    check("H2 male feet band", abs(rep["feet_z"]) <= 0.15, True)
    check("H2 pool actions are THIS import's datablocks",
          all(a.name.startswith("HumanArmature|")
              for a in rep["pool"].values()), True)
    check("H2 import slot cleared (loader policy)",
          rep["import_slot_cleared"] is not None
          and "Man_Clapping" in rep["import_slot_cleared"], True)
    # recolor sweep (BEFORE the next purge — object refs die with it)
    assets_quaternius.recolor(rep, (0.8, 0.2, 0.2))
    slots = rep["mesh"].material_slots
    landed = [bool(s.material and s.material.diffuse_color[0] > 0.7)
              for s in slots]
    print(f"[hero] H2 recolor slots={len(slots)} landed={landed} "
          f"node_trees={[bool(s.material and s.material.use_nodes) for s in slots]}",
          flush=True)
    check("H2 recolor landed", all(landed) if landed else False, True)
    fresh()
    repf = assets_quaternius.load("female", "HeroF")
    check("H2 female bones", len(repf["arm"].data.bones), 42)
    check("H2 female height band", 1.2 <= repf["height"] <= 2.2, True)


def h3_retarget():
    fresh()
    import assets_ual_actors as ual
    u = ual._import_actor("Driver", ual.ACTOR_SCALE)
    src_arm = u["armature"]
    walk = u["actions"]["Walk_Loop"]
    src_fc_count = len(list(rig_retarget._iter_fcurves(walk)))

    rep = assets_quaternius.load("male", "HeroQ")
    tgt_arm = rep["arm"]
    r = rig_retarget.retarget(src_arm, walk, tgt_arm)
    print(f"[hero] H3 gates: {r['gates']}", flush=True)
    check("H3 coverage 1.0", r["coverage"], 1.0, 1e-6)
    check("H3 mapped classes", r["mapped"], 19)   # 19 shared classes
    check("H3 drives ok", r["gates"]["drives_ok"], True)
    check("H3 drive err < 1e-4", r["gates"]["drive_err_max"] < 1e-4,
          True)
    check("H3 teleport ok", r["gates"]["teleport_ok"], True)
    check("H3 pose actually moves", r["gates"]["max_qdelta_deg"] > 5.0,
          True)
    check("H3 fresh-bake name", r["name"], f"{walk.name}__rt_HeroQ.Rig")
    check("H3 fake_user False pre-bind", r["action"].use_fake_user,
          False)
    check("H3 source action unmutated",
          len(list(rig_retarget._iter_fcurves(walk))), src_fc_count)
    # fps pinned from the scene at bake (the glTF import may re-pin it)
    check("H3 fps recorded", r["fps"], bpy.context.scene.render.fps)


def h4_refusals():
    fresh()
    import assets_ual_actors as ual
    u = ual._import_actor("Driver", ual.ACTOR_SCALE)
    src_arm = u["armature"]
    walk = u["actions"]["Walk_Loop"]
    rep = assets_quaternius.load("male", "HeroQ")
    tgt_arm = rep["arm"]
    r = rig_retarget.retarget(src_arm, walk, tgt_arm)
    # stale output name refuses
    try:
        rig_retarget.retarget(src_arm, walk, tgt_arm)
        raise AssertionError("stale-bake rebake accepted")
    except rig_retarget.RetargetRefused:
        pass
    # non-QUATERNION target mode refuses
    fresh()
    u2 = ual._import_actor("Driver", ual.ACTOR_SCALE)
    rep2 = assets_quaternius.load("male", "HeroQ2")
    rep2["arm"].pose.bones["Hips"].rotation_mode = 'XYZ'
    try:
        rig_retarget.retarget(u2["armature"],
                              u2["actions"]["Walk_Loop"],
                              rep2["arm"])
        raise AssertionError("EULER-mode target accepted")
    except rig_retarget.RetargetRefused:
        pass


def h5_world_gates():
    fresh()
    import assets_ual_actors as ual
    u = ual._import_actor("Driver", ual.ACTOR_SCALE)
    rep = assets_quaternius.load("male", "HeroQ")
    r = rig_retarget.retarget(u["armature"], u["actions"]["Walk_Loop"],
                              rep["arm"])
    # stage the retargeted action on the wrapped rig
    ad = rep["arm"].animation_data or rep["arm"].animation_data_create()
    ad.action = r["action"]
    rows = rig_retarget.run_world_gates(rep["arm"], r["action"],
                                        sample_stride=2)
    flat = [z for pair in rows["feet_z"] for z in pair]
    # the ground law is the FLOOR (feet never below ground); the lift
    # ceiling is gait-dependent (the measured UAL walk lifts to ~0.25
    # wrapper-scaled) — an absolute 0.15 ceiling would fail real walks
    check("H5 feet ground floor", all(z >= -0.08 for z in flat), True)
    check("H5 feet lift plausible", max(flat) <= 0.6, True)
    check("H5 gait-class feet anti-phase",
          max(flat) - min(flat) >= 0.02, True)
    hz = [v for v in rows["hips_z"] if v is not None]
    check("H5 hips span measured", len(hz) > 4, True)
    check("H5 hips human band", all(0.6 <= v <= 1.4 for v in hz), True)
    print(f"[hero] H5 feet min/max {min(flat):.3f}/{max(flat):.3f} "
          f"hips {min(hz):.3f}-{max(hz):.3f} (numbers travel)", flush=True)


def h6_bind_and_play():
    fresh()
    import assets_ual_actors as ual
    u = ual._import_actor("Driver", ual.ACTOR_SCALE)
    rep = assets_quaternius.load("male", "HeroQ")
    r = rig_retarget.retarget(u["armature"], u["actions"]["Walk_Loop"],
                              rep["arm"])
    # bind (the D5a one-process lifecycle: fake_user pins at bind)
    ad = rep["arm"].animation_data or rep["arm"].animation_data_create()
    ad.action = r["action"]
    r["action"].use_fake_user = True
    sc = bpy.context.scene
    lo, hi = [int(v) for v in r["frames"]]
    seq = []
    for f in range(lo, hi + 1, max(1, (hi - lo) // 8 or 1)):
        sc.frame_set(f)
        bpy.context.view_layer.update()
        seq.append(round(world_z(rep["arm"], "hips"), 4))
    check("H6 hips z sampled across range", len(seq) >= 6, True)
    check("H6 hips z all sane", all(0.5 <= v <= 1.5 for v in seq), True)
    print(f"[hero] H6 hips-z world seq {seq}", flush=True)


def main() -> int:
    for rid, fn in (("H1", h1_wrapper_laws), ("H2", h2_loader),
                    ("H3", h3_retarget), ("H4", h4_refusals),
                    ("H5", h5_world_gates), ("H6", h6_bind_and_play)):
        row(rid, fn)
    print(f"[hero] SUMMARY: "
          f"{sum(1 for v in ROWS.values() if v == 'pass')} pass, "
          f"{len(FAIL)} fail", flush=True)
    for rid, v in ROWS.items():
        print(f"[hero]   {rid}: {v}", flush=True)
    if FAIL:
        print(f"[hero] ALL FAIL: {FAIL}", flush=True)
        return 1
    print("[hero] ALL PASS", flush=True)
    return 0


sys.exit(main())
