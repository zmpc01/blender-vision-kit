# test_s19_wave_pins.py — session-19 fix PINS (in-Blender, red-by-construction).
#
# Auditor A6 (docs/audit_s19/wave1_triage.md): the s18 fix wave was almost
# entirely UNPINNED — reverting most of the landed fixes failed no test,
# because the fixes existed only as diffs, not as behavior contracts. This
# suite pins the s19 wave-A mutation-surface fixes the same way the
# wave-B/C/D suites pin theirs: run the EXACT misuse the fix refuses, and
# assert the refusal names the real key/token (messages and return keys
# read from the current code, not invented — gotcha 11).
#
# Pins (triage owner-A rows; letter = the task's pin id):
#   a  _nonneg_mm NaN refusal (physics_settle tol_mm via a json NaN
#      literal — json.loads ACCEPTS NaN) + scene unchanged   (wave-2b family)
#   b  set_camera_dof aperture_fstop<=0 refused with the lens/(2*fstop)
#      message; use_dof stays False on the refusal path (s19-A8
#      validate-before-write)
#   c  physics_gate frames=0 refused with the >= 10 message (s19-E10)
#   d  set_rotation on a QUATERNION-mode object writes rotation_quaternion
#      and leaves rotation_euler untouched; world orientation matches the
#      requested euler->quat (s19-E2; the glTF silent no-op class)
#   e  set_rotation on a rotation-keyed object refused by default
#      (s19-E4); location-guard override token validated — "rebase"
#      refused with the valid-set message (s19-E3)
#   f  set_location on a location-keyed object refused by default;
#      override="keyframe" REBASES — evaluating the action at the current
#      frame yields the NEW location and a later key keeps the path shape
#      (s19-E4)
#   g  place_on(align_to_surface=True) idempotence: second call reports
#      the identity align delta (align_skip_reason) and world +Z still
#      matches the surface normal (s19-E9)
#   h  seam_views fill_frac=0 refused at the param layer — no
#      ZeroDivision mid-shoot (s19-A4)
#   i  heat_bake yellow_mm>=green_mm refused (s19-A9); empty others
#      refused (s19-E11)
#   j  audit sample token "verts_bogus" refused (s19-E8)
#   k  render_viewport engine="BLENDER_BOGUS" refused (s19-E20)
#   l  _nonneg_mm huge-int (10**400) refused WITHOUT OverflowError
#      (s19-A7)
#   m  snap_z on a posed armature mesh refused via the skinned guard
#      (s19-E15; _skinned_guard raises RuntimeError 'ANIMATED skinned
#      mesh' — the C6 pose-matrix probe class)
#   n  stale-depsgraph audit: [set_location -> audit] must see the
#      POST-move pose (s19-E1 flush at pair_contact entry) — a mover
#      driven into a wall reports PENETRATING, never the pre-move
#      vacuous CLEAR
#
# Battery row to register in scripts/suite_runner.sh (orchestrator-owned):
#   "test_s19_wave_pins|tests/test_s19_wave_pins.py|BL||0|\[test_s19p\] ALL PASS|session-19 fix pins (red-by-construction; s18 A6 + s19 wave-A)"
#
# Run: ./scripts/blrun.sh --background --python tests/test_s19_wave_pins.py
# Convention: prints [test_s19p] per check; ends with
# "[test_s19p] ALL PASS (N checks)" iff green; exit 1 on any failure.

import io
import json
import math
import os
import shutil
import sys
import tempfile
from contextlib import redirect_stdout

import bpy
from mathutils import Euler, Vector

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "scripts"))

import apply_patch as AP             # noqa: E402

PASS = []
FAIL = []

_TMP = tempfile.mkdtemp(prefix="s19p_")


def check(name, cond, detail=""):
    tag = "ok" if cond else "FAIL"
    print(f"[test_s19p] {name}: {tag}"
          + (f" — {detail}" if detail and not cond else ""))
    (PASS if cond else FAIL).append(name)


def expect_error(name, fn, *needles):
    """fn() must raise RuntimeError mentioning every needle."""
    try:
        fn()
    except RuntimeError as e:
        msg = str(e)
        missing = [n for n in needles if n not in msg]
        check(name, not missing,
              f"raised but missing {missing} in: {msg[:220]}")
        return msg
    except Exception as e:  # wrong exception class
        check(name, False, f"wrong exc {type(e).__name__}: {e}")
        return ""
    check(name, False, "no error raised")
    return ""


def run_op(mut):
    """apply_mutation with its stdout captured (keeps this log readable)."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        AP.apply_mutation(mut)
    return buf.getvalue()


def add_mesh(name, loc, size=0.4):
    bpy.ops.mesh.primitive_cube_add(size=size, location=loc)
    o = bpy.context.active_object
    o.name = name
    return o


def pose_snapshot():
    return {o.name: tuple(round(v, 6) for v in o.location)
            for o in bpy.data.objects if o.type == 'MESH'}


# ====================================================== one shared fixture
# All pins run against THIS scene (A6's lean-suite law): every fixture
# lives at its own XY slot so audits/pairs never cross.
bpy.ops.wm.read_factory_settings(use_empty=True)

bpy.ops.mesh.primitive_plane_add(size=8, location=(0, 0, 0))
bpy.context.active_object.name = "Ground"

box = add_mesh("Box", (0, 0, 0.5))                       # quat + token pins

mover = add_mesh("KeyedMover", (4, 0, 0.5))              # s19-E3/E4 pins
mover.location = (4, 0, 0.5)
mover.keyframe_insert(data_path="location", frame=1)
mover.location = (6, 0, 0.5)
mover.keyframe_insert(data_path="location", frame=24)
mover.rotation_euler = (0, 0, 0)
mover.keyframe_insert(data_path="rotation_euler", frame=1)
mover.rotation_euler = (0, 0, math.radians(90))
mover.keyframe_insert(data_path="rotation_euler", frame=24)
bpy.context.scene.frame_set(1)

bpy.ops.object.camera_add(location=(0, -3, 1.2),
                          rotation=(math.radians(90), 0, 0))
cam = bpy.context.active_object
cam.name = "PinCam"

add_mesh("E1Mover", (2, 0, 0.5), size=0.5)               # s19-E1 pin
add_mesh("E1Wall", (5, 0, 0.5), size=1.0)

arm_data = bpy.data.armatures.new("Rig")
arm_obj = bpy.data.objects.new("Rig", arm_data)          # s19-E15 pin
arm_obj.location = (-4, 0, 0)
bpy.context.collection.objects.link(arm_obj)
bpy.context.view_layer.objects.active = arm_obj
bpy.ops.object.mode_set(mode='EDIT')
eb = arm_data.edit_bones.new("Bone")
eb.head = (0, 0, 0)          # armature-LOCAL coords (arm_obj sits at x=-4)
eb.tail = (0, 0, 0.5)
bpy.ops.object.mode_set(mode='OBJECT')
rig = add_mesh("RiggedCube", (-4, 0, 0.4), size=0.4)
_mod = rig.modifiers.new("Arm", 'ARMATURE')
_mod.object = arm_obj
bpy.context.view_layer.objects.active = arm_obj
bpy.ops.object.mode_set(mode='POSE')
arm_obj.pose.bones["Bone"].location = (0, 0, 0.25)   # manual pose (C6 class)
bpy.ops.object.mode_set(mode='OBJECT')

ramp = add_mesh("AlignRamp", (-8, 0, 0.35), size=2.0)    # s19-E9 pin
ramp.rotation_euler = (0, math.radians(15), 0)
add_mesh("AlignCrate", (-8, 0, 2.0), size=0.5)
bpy.context.view_layer.update()

# ============================================ a / l / c — param-layer guards
# (a): json.loads ACCEPTS NaN literals — the wire format really delivers
# one; _nonneg_mm must refuse it naming the key (wave-2b family, kept
# honest by A6: a revert made every verdict comparison silently False).
_snapshot_before = pose_snapshot()
_nan_mut = json.loads('{"op":"physics_settle","tol_mm":NaN}')
expect_error("pin_a.nan_tol_mm_refused",
             lambda: run_op(_nan_mut), "tol_mm", "NaN")
# (l): a huge int overflows float() — the s19-A7 fix routes OverflowError
# into the same finite refusal (a bare OverflowError would be a raw,
# unattributed crash — and 10**400 must not slip through as a number).
_huge_mut = json.loads('{"op":"physics_settle","tol_mm":' + "1" * 400 + '}')
expect_error("pin_l.huge_int_tol_mm_refused",
             lambda: run_op(_huge_mut), "tol_mm", "finite")
# (c): frames=0 ran a zero-frame sim and verdicted the SPAWN pose
# (s19-E10) — the guard demands an integer >= 10.
expect_error("pin_c.frames_zero_refused",
             lambda: run_op({"op": "physics_gate", "frames": 0}),
             "frames", ">= 10")
check("pin_a.scene_unchanged_after_param_refusals",
      pose_snapshot() == _snapshot_before,
      "a param-layer refusal must never touch the scene")

# ==================================== b — set_camera_dof validate-BEFORE-write
# (b): fstop<=0 is a ZeroDivision in the op's own lens/(2*fstop) print AND
# physically meaningless; s19-A8 moved validation BEFORE the first write,
# so the refusal path must leave use_dof untouched (False).
expect_error("pin_b.fstop_zero_and_negative_refused",
             lambda: (
                 run_op({"op": "set_camera_dof", "id": "PinCam",
                         "aperture_fstop": 0}),
                 run_op({"op": "set_camera_dof", "id": "PinCam",
                         "aperture_fstop": -1})),
             "aperture_fstop", "lens/(2*fstop)")
check("pin_b.use_dof_stays_false_on_refusal",
      cam.data.dof.use_dof is False,
      "a refused dof op must not enable dof (partial mutation on the "
      "error path = the s19-A8 class)")
run_op({"op": "set_camera_dof", "id": "PinCam",
        "focus_distance": 2.5, "aperture_fstop": 2.8})
check("pin_b.valid_fstop_still_applies",
      cam.data.dof.use_dof is True
      and abs(cam.data.dof.aperture_fstop - 2.8) < 1e-6,
      "use_dof=%r fstop=%r" % (cam.data.dof.use_dof,
                               cam.data.dof.aperture_fstop))

# ====================================== d — set_rotation on QUATERNION mode
# (d): rotation_euler is STORED-BUT-UNUSED on QUATERNION-mode objects
# (every glTF import) — the pre-E2 op wrote it, printed applied, and the
# scene kept the old orientation.
box.rotation_mode = 'QUATERNION'
_euler_before = tuple(box.rotation_euler)
_expected_q = Euler((0, 0, math.radians(90)), 'XYZ').to_quaternion()
run_op({"op": "set_rotation", "id": "Box", "rotation_deg": [0, 0, 90]})
_q_written = box.rotation_quaternion
_q_diff = _q_written.rotation_difference(_expected_q).angle
check("pin_d.quat_channel_written_euler_untouched",
      _q_diff < 1e-6 and tuple(box.rotation_euler) == _euler_before,
      f"quat-vs-expected angle={_q_diff:.2e} "
      f"euler_before={_euler_before} euler_now={tuple(box.rotation_euler)}")
bpy.context.view_layer.update()
_w_diff = box.matrix_world.to_quaternion().rotation_difference(
    _expected_q).angle
check("pin_d.quat_orientation_matches_request", _w_diff < 1e-5,
      f"world-vs-expected angle={_w_diff:.2e}")

# ================================== e — keyed-object refusal + token guard
# (e/E4): set_rotation on a rotation-keyed object is refused by default —
# the keys would snap the orientation back at the next frame_set.
expect_error("pin_e.rotation_keyed_set_rotation_refused",
             lambda: run_op({"op": "set_rotation", "id": "KeyedMover",
                             "rotation_deg": [0, 0, 45]}),
             "rotation animation", "set_rotation")
# (e/E3): the location guard's override token is validated — any junk
# (the docs' own "rebase" verb included) used to fall through to 'ignore'
# semantics (a fail-open lie).
expect_error("pin_e.rebase_override_token_refused",
             lambda: run_op({"op": "set_location", "id": "Box",
                             "location": [1, 1, 1],
                             "override": "rebase"}),
             "not valid", "keyframe", "ignore")

# ============================== f — set_location on a keyed object (E4)
# default: refuse naming the animation; override="keyframe": REBASE the
# whole path by the write's world delta.
expect_error("pin_f.location_keyed_set_location_refused",
             lambda: run_op({"op": "set_location", "id": "KeyedMover",
                             "location": [4.5, 1.0, 0.5]}),
             "location animation")
run_op({"op": "set_location", "id": "KeyedMover",
        "location": [4.5, 1.0, 0.5], "override": "keyframe"})
# the op re-evaluates at the current frame after the rebase; assert BOTH
# ends of the path: f24 keeps its relative shape (orig (6,0,.5)+delta)
# and f1 (the write's frame) reads the NEW location — the naive
# 're-key current frame only' override left later keys behind (K4).
bpy.context.scene.frame_set(24)
bpy.context.view_layer.update()
_got_f24 = tuple(round(v, 5) for v in
                 bpy.data.objects["KeyedMover"].matrix_world.translation)
bpy.context.scene.frame_set(1)
bpy.context.view_layer.update()
_got_f1 = tuple(round(v, 5) for v in
                bpy.data.objects["KeyedMover"].matrix_world.translation)
check("pin_f.keyframe_rebase_current_and_path",
      all(abs(a - b) < 1e-4 for a, b in zip(_got_f1, (4.5, 1.0, 0.5)))
      and all(abs(a - b) < 1e-4 for a, b in zip(_got_f24, (6.5, 1.0, 0.5))),
      f"eval@f1={_got_f1} (expect (4.5,1,0.5)) "
      f"eval@f24={_got_f24} (expect (6.5,1,0.5))")

# ============================== g — place_on align idempotence (E9)
# The absolute premultiply rotated the object AGAIN on every re-run; the
# fix composes the DELTA from the current +Z, so a re-run reports the
# identity delta and the pose is stable.
run_op({"op": "place_on", "id": "AlignCrate", "supports": ["AlignRamp"],
        "clearance": 0.0, "align_to_surface": True})
rep1 = AP._LAST_REPORTS.get("place_on", {})
crate = bpy.data.objects["AlignCrate"]
_n1 = Vector(rep1.get("surface_normal", (0, 0, 1)))
_wz1 = (crate.matrix_world.to_3x3() @ Vector((0, 0, 1))).normalized()
check("pin_g.align_first_call_aligns",
      rep1.get("aligned_to_surface") is True and _wz1.dot(_n1) > 0.9,
      f"aligned={rep1.get('aligned_to_surface')} "
      f"+Z.normal={_wz1.dot(_n1):.3f}")
run_op({"op": "place_on", "id": "AlignCrate", "supports": ["AlignRamp"],
        "clearance": 0.0, "align_to_surface": True})
rep2 = AP._LAST_REPORTS.get("place_on", {})
_skip = rep2.get("align_skip_reason", "")
bpy.context.view_layer.update()
_n2 = Vector(rep2.get("surface_normal", _n1))
_wz2 = (crate.matrix_world.to_3x3() @ Vector((0, 0, 1))).normalized()
check("pin_g.align_second_call_identity_and_plusZ",
      "identity" in _skip and _wz2.dot(_n2) > 0.9,
      f"align_skip_reason={_skip!r} +Z.normal={_wz2.dot(_n2):.3f}")

# ============================================ h — seam_views fill_frac (A4)
# fill_frac=0 passed the old >=0 gate and divided by zero MID-SHOOT; the
# s19-A4 bound is strict (0, 1] at the param layer, own message.
expect_error("pin_h.fill_frac_zero_refused",
             lambda: run_op({"op": "seam_views", "a": "Box", "b": "Ground",
                             "out_dir": _TMP, "fill_frac": 0}),
             "fill_frac", "(0, 1]")

# ================================================ i — heat_bake bands (A9/E11)
# inverted bands silently ate every distance into YELLOW (the elif order)
# and left GREEN unreachable; empty others rendered a vacuous all-GRAY map.
expect_error("pin_i.heat_band_inversion_refused",
             lambda: run_op({"op": "heat_bake", "id": "Box",
                             "others": ["Ground"],
                             "yellow_mm": 50, "green_mm": 10}),
             "yellow_mm", "green_mm")
expect_error("pin_i.heat_empty_others_refused",
             lambda: run_op({"op": "heat_bake", "id": "Box", "others": []}),
             "others", "empty")

# ============================================== j — audit sample token (E8)
# unknown tokens silently degraded to plain-vert sampling while the row
# reported the requested mode.
expect_error("pin_j.audit_sample_token_refused",
             lambda: run_op({"op": "audit", "pairs": ["Box,Ground"],
                             "sample": "verts_bogus"}),
             "sample", "verts")

# ========================================== k — render_viewport engine (E20)
# an alias-miss used to render the scene's CURRENT engine
# (accepted-but-unimplemented = the fail-open-lie law).
expect_error("pin_k.render_engine_token_refused",
             lambda: run_op({"op": "render_viewport",
                             "output": os.path.join(_TMP, "s19_bogus.png"),
                             "engine": "BLENDER_BOGUS"}),
             "unknown engine", "BLENDER_BOGUS")

# ================================= m — snap_z skinned guard (E15)
# snap_z was the ONLY solver without _skinned_guard: a posed rigged mesh
# reads its bind-pose bbox and snaps to a wrong z silently. The rig above
# is MANUALLY posed (zero animation data — the C6 pose-matrix-probe class).
expect_error("pin_m.snap_z_skinned_guard_refuses",
             lambda: run_op({"op": "snap_z", "id": "RiggedCube",
                             "target_z": 1.5}),
             "skinned")

# ================================= n — stale-depsgraph audit (E1, the P1)
# pair_contact read matrix_world BEFORE the first depsgraph flush: a
# [set_location -> audit] chain branched the AABB prefilter on the
# PRE-move pose -> moved-into-wall classified CLEAR -> fail_on_penetration
# FALSE-PASS. Pre-move the pair is 2.7m apart (a vacuous CLEAR); post-move
# E1Mover PARTIALLY overlaps E1Wall's x=4.5 face (mover spans 4.45..4.95
# against the wall's 4.5..5.5) — face pairs + contained verts =
# PENETRATING. A FULLY-inside pose would classify NESTED (severity=info,
# the legitimate nested-container state — fail_on_penetration rightly
# does not abort on it).
run_op({"op": "set_location", "id": "E1Mover",
        "location": [4.7, 0.05, 0.5]})
expect_error("pin_n.post_move_audit_bites",
             lambda: run_op({"op": "audit", "pairs": ["E1Mover,E1Wall"]}),
             "penetration detected")
run_op({"op": "audit", "pairs": ["E1Mover,E1Wall"],
        "fail_on_penetration": False})
_nrep = AP._LAST_REPORTS.get("audit", {})
_npairs = _nrep.get("pairs", [])
_nstate = _npairs[0].get("state") if _npairs else "NO-PAIRS"
check("pin_n.post_move_pair_not_vacuous_clear",
      _nrep.get("pairs_checked") == 1
      and _nstate in ("PENETRATING", "TOUCHING"),
      f"pairs_checked={_nrep.get('pairs_checked')} state={_nstate!r} "
      f"(the pre-E1 chain read the PRE-move pose here: vacuous CLEAR)")

# ================================================================== end
print("=" * 60)
print(f"test_s19_wave_pins: {len(PASS) - len(FAIL)}/"
      f"{len(PASS) + len(FAIL)} checks passed")
shutil.rmtree(_TMP, ignore_errors=True)
if FAIL:
    print(f"[test_s19p] FAILED: {FAIL}")
    print("[test_s19p] RESULT: FAIL")
    sys.exit(1)
print(f"[test_s19p] ALL PASS ({len(PASS)} checks)")
sys.exit(0)
