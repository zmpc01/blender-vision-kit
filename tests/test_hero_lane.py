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
import rig_family_quaternius as assets_quaternius      # noqa: E402
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
    check("H2 male pool identity", set(rep["pool"]),
          set(assets_quaternius.EXPECTED_ACTION_KEYS))
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
    # the A2a P3-12 fold: the female row was under-pinned (a Female_
    # prefix drift sailed); pool identity + feet now pinned too
    check("H2 female pool identity", set(repf["pool"]),
          set(assets_quaternius.EXPECTED_ACTION_KEYS))
    check("H2 female feet band", abs(repf["feet_z"]) <= 0.15, True)
    check("H2 female datablocks distinct from male's",
          repf["arm"] is not rep["arm"], True)


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
    # audit A1 P2-6: a degenerate/empty source action refuses (the old
    # code scored coverage 1.0 and baked a vacuous rest pose)
    empty = bpy.data.actions.new("EmptyProbe")
    try:
        rig_retarget.retarget(src_arm, empty, tgt_arm)
        raise AssertionError("empty source action accepted")
    except rig_retarget.RetargetRefused:
        pass
    bpy.data.actions.remove(empty)
    r = rig_retarget.retarget(src_arm, walk, tgt_arm)
    # audit A1 P2-9: a keyed path that does not resolve on the target
    # refuses at the census (was an unguarded KeyError). The injection
    # goes through blender_kit.fcurves_new — a raw action.fcurves.new
    # would land in a legacy slot iter_fcurves never returns on 5.x.
    import blender_kit
    stale_fc = blender_kit.fcurves_new(
        r["action"], 'pose.bones["__Nope__"].rotation_quaternion', 0)
    stale_fc.keyframe_points.add(1)
    stale_fc.keyframe_points[0].co = (r["frames"][0], 1.0)
    try:
        rig_retarget._run_closure(src_arm, walk, tgt_arm, r["action"],
                                  {}, [r["frames"][0], r["frames"][1]], 1)
        raise AssertionError("stale keyed path accepted")
    except rig_retarget.RetargetRefused:
        pass
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




# ------------------------------------------------------------------ #
def h7_loader_and_wrapper_laws():
    """The A2a+A2b audit folds' probes (s24): the loader refusals roll
    back (retry-clean), the pool keys survive a double import, the
    unskinned/derived-name/scale refusals fire pre-import, the T4
    unlinked refusal + child-collection clause are exercised, and the
    lab's world-band assert rejects a planted bad table."""
    fresh()
    # 7a: derived-name refusal (P2-5) — pre-import, no leak
    bpy.ops.mesh.primitive_cube_add(size=0.1, location=(99, 99, 99))
    blocker = bpy.context.active_object
    blocker.name = "HeroX.Body"
    try:
        assets_quaternius.load("male", "HeroX")
        raise AssertionError("derived-name collision not refused")
    except assets_quaternius.LoadRefused as e:
        check("H7a derived-name refusal names .Body", "HeroX.Body" in str(e),
              True)
    bpy.data.objects.remove(blocker, do_unlink=True)

    # 7b: scale>0 refusal (P2-6)
    try:
        assets_quaternius.load("male", "HeroNeg", scale=-0.3718)
        raise AssertionError("negative scale not refused")
    except assets_quaternius.LoadRefused as e:
        check("H7b negative scale refused pre-import", "must be > 0"
              in str(e), True)

    # 7c: rollback + retry-clean (P1-1) — force a census refusal via a
    # monkeypatched BONE_CENSUS, then verify the retry succeeds clean
    import importlib
    orig_census = assets_quaternius.BONE_CENSUS
    try:
        assets_quaternius.BONE_CENSUS = 41
        try:
            assets_quaternius.load("male", "HeroR")
            raise AssertionError("census mismatch not refused")
        except assets_quaternius.LoadRefused:
            pass
        leaked = [o for o in bpy.data.objects
                  if o.name.startswith(("HeroR.", "HumanArmature"))]
        check("H7c rollback: no leaked rig objects", leaked, [])
        leaked_acts = [a.name for a in bpy.data.actions
                       if "HumanArmature" in a.name]
        check("H7c rollback: no leaked actions", leaked_acts, [])
    finally:
        assets_quaternius.BONE_CENSUS = orig_census
    rep = assets_quaternius.load("male", "HeroR")
    check("H7c retry after rollback succeeds", len(rep["pool"]), 11)

    # 7d: double same-family import keeps the CLEAN pool keys (P1-2)
    rep2 = assets_quaternius.load("male", "HeroR2")
    check("H7d second import clean keys", set(rep2["pool"]),
          set(assets_quaternius.EXPECTED_ACTION_KEYS))
    check("H7d second import binds ITS OWN datablocks",
          all(a is not rep["pool"][k] for k, a in rep2["pool"].items()),
          True)

    # 7e: the T4 unlinked refusal + child-collection clause (A2b P2-1)
    bpy.ops.wm.read_homefile(use_empty=True)
    unlinked_arm = bpy.data.armatures.new("UnlinkedArm")
    unlinked_obj = bpy.data.objects.new("UnlinkedArm", unlinked_arm)
    # deliberately NOT linked into any collection
    try:
        wrapper_rig.wrap(unlinked_obj, "HeroU")
        raise AssertionError("unlinked armature not refused")
    except RuntimeError as e:
        check("H7e unlinked armature refused", "linked" in str(e).lower(),
              True)
    sub = bpy.data.collections.new("Sub")
    bpy.context.scene.collection.children.link(sub)
    linked_ok = bpy.data.objects.new("SubArm", unlinked_arm)
    sub.objects.link(linked_ok)
    # a rest bone whose +Y is horizontal and Y-dominant — the probe
    # needs a real foot-like bone (a boneless armature is a REFUSAL)
    bpy.context.view_layer.objects.active = linked_ok
    bpy.ops.object.mode_set(mode='EDIT')
    eb = unlinked_arm.edit_bones.new("Foot.L")
    eb.head = (0.0, 0.0, 0.0)
    eb.tail = (0.0, 0.2, 0.0)          # +Y toe direction at rest
    bpy.ops.object.mode_set(mode='OBJECT')
    r = wrapper_rig.wrap(linked_ok, "HeroU", scale=1.0)
    check("H7e child-collection wrap succeeds (the T4 fix body)",
          r["root"] is not None, True)
    check("H7e probe_source reported", r.get("probe_source") in
          ("explicit", "auto"), True)

    # 7f: the lab's world-band assert rejects a planted bad table
    # (A2b P1-1 — the enforcement probe; _assert_hero_bands is pure)
    import scene_motion_lab as lab
    good = {"feet_z": [[0.02, 0.22]] * 5,
            "hips_z": [0.9, 1.0, 0.95, 1.05, 0.9]}
    v = lab._assert_hero_bands("ProbeHero", good)
    check("H7f good table passes", v.startswith("PASS"), True)
    bad = {"feet_z": [[-0.3, -0.1]] * 5,   # underground + frozen span
           "hips_z": [0.2, 0.25, 0.2, 0.3, 0.2]}
    try:
        lab._assert_hero_bands("ProbeHero", bad)
        raise AssertionError("bad table not refused")
    except RuntimeError as e:
        # the planted table's span (0.2) is legal — the refusal names
        # the two REAL violations (underground feet + collapsed hips)
        check("H7f bad table refused with numbers",
              "underground" in str(e) and "outside" in str(e), True)


def main() -> int:
    for rid, fn in (("H1", h1_wrapper_laws), ("H2", h2_loader),
                    ("H3", h3_retarget), ("H4", h4_refusals),
                    ("H5", h5_world_gates), ("H6", h6_bind_and_play),
                    ("H7", h7_loader_and_wrapper_laws)):
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
