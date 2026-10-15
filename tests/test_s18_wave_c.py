# test_s18_wave_c.py — session-18 Wave-C fix regressions (in-Blender).
#
# Covers the wave-1 audit's wave-C rows (docs/audit_s18/wave1_triage.md):
#   C1: seat_at(align)/place_on(align_to_surface) ROTATION-key guards —
#       refusal naming the channels by default (and 'ignore' is NOT
#       honored), QUATERNION-mode active-action keys rebased under
#       override='keyframe' (q_new = q_offset @ q_key at EVERY key),
#       euler-mode keys refused even under override='keyframe'.
#   C2: physics_place._prep animated-exclusion covers ALL transform
#       channels (rotation-keyed mover AND rotation-keyed env) + the
#       parent chain.
#   C3: physics modifiers guard is REAL (was an `if False` stub):
#       modifier + unbaked scale -> "modifiers_block_bake" refusal;
#       allow_bake=True authorizes the bake and the sim proceeds.
#   C4: allow_bake on a multi-user mesh (users>1) bakes a PRIVATE
#       '.SimBake' datablock copy — the ORIGINAL datablock keeps its
#       scale (the old code rescaled shared data scene-wide).
#   C6: _skinned_guard fires on DRIVER-posed and MANUALLY-posed
#       armatures (zero action/NLA — the pose-matrix probe).
#   C7: seat_at gained _skinned_guard/force (was the only bare solver).
#   C9: align_to_surface works with footprint='grid' (footprint_pts is
#       filled; the report carries aligned_to_surface/align_skip_reason
#       explicitly and the rotation actually maps +Z onto the normal).
#   C10: place_on mode token validated (was a raw dict KeyError).
#   C11: contact_discs._kd_at_rest reads last_x/last_y AFTER the
#       frame_set (the parked-frame residue is gone).
#   C12: prop_carry.carry_keys keys rotation_quaternion on
#       QUATERNION-mode props (euler keys are dead on those).
#
# Run: blrun.sh --background --python tests/test_s18_wave_c.py
# Convention: prints [S18C] per check; ends with
#   "[S18C] ALL PASS (N checks)"  (grepped by scripts/suite_runner.sh)

import math
import os
import sys

import bpy
from mathutils import Quaternion, Vector

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "scripts"))

import placement_lib as PL             # noqa: E402
import physics_place as PP             # noqa: E402
import contact_discs                   # noqa: E402
from blender_kit import iter_fcurves, prop_carry as PC   # noqa: E402

PASS = []
FAIL = []


def check(name, cond, detail=""):
    tag = "ok" if cond else "FAIL"
    print(f"[S18C] {name}: {tag}" + (f" — {detail}" if detail and not cond else ""))
    (PASS if cond else FAIL).append(name)


def wipe():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def rot_fcurves(obj):
    ad = obj.animation_data
    if ad is None or ad.action is None:
        return {}
    return {fc.array_index: fc for fc in iter_fcurves(ad.action)
            if fc.data_path == "rotation_quaternion"}


def keyed_quat(fcs, frame):
    """The object's keyed quaternion at `frame` (all 4 channels share
    key times — the rebase refuses anything else)."""
    idx = [j for j, kp in enumerate(fcs[0].keyframe_points)
           if abs(kp.co.x - frame) < 0.5][0]
    return Quaternion(tuple(fcs[i].keyframe_points[idx].co.y
                            for i in range(4)))


# ================================================================== C1
# rotation-key refusal + override='keyframe' rebase via seat_at(align)
wipe()
scene = bpy.context.scene
bpy.ops.mesh.primitive_cube_add(size=0.5, location=(0, 0, 1))
mover = bpy.context.active_object
mover.name = "RotKeyed"
mover.rotation_mode = 'QUATERNION'
q1 = Quaternion((1, 0, 0, 0))
q12 = Quaternion((0.7071068, 0.7071068, 0, 0))     # 90 deg about X
q24 = Quaternion((0.7071068, 0, 0, 0.7071068))     # 90 deg about Z
for f, q in ((1, q1), (12, q12), (24, q24)):
    mover.rotation_quaternion = q
    mover.keyframe_insert(data_path="rotation_quaternion", frame=f)
bpy.ops.object.empty_add(location=(1, 1, 1))
anchor = bpy.context.active_object
anchor.name = "SeatAnchor"
anchor.rotation_euler = (0.3, 0.2, 0.7)
bpy.context.view_layer.update()
q_anchor = anchor.matrix_world.to_quaternion().copy()

err_default = None
try:
    PL.seat_at(mover, anchor, align=True)
    check("C1a.rot_keys_refused_default", False, "no exception raised")
except RuntimeError as e:
    err_default = str(e)
    check("C1a.rot_keys_refused_default",
          "rotation animation" in err_default and "seat_at" in err_default,
          err_default[:110])
check("C1c.refusal_names_rotation_channels",
      err_default is not None and "rotation_quaternion" in err_default,
      "the refusal must name the found channel tags (action:rotation_quaternion[i])")
try:
    PL.seat_at(mover, anchor, align=True, override='ignore')
    check("C1b.rot_keys_refused_ignore", False, "'ignore' honored for rotation")
except RuntimeError as e:
    check("C1b.rot_keys_refused_ignore",
          "rotation animation" in str(e), str(e)[:110])

# override='keyframe' on the QUATERNION-mode mover: rebases EVERY key by
# the align delta. q_offset captured at the parked frame (f12) is
# q_anchor @ q12^-1; the law is q_new = q_offset @ q_key, so the f12 key
# becomes q_anchor exactly and the f1 key q_anchor @ q12^-1 @ q1.
scene.frame_set(12)
bpy.context.view_layer.update()
rep = PL.seat_at(mover, anchor, align=True, override='keyframe')
check("C1d.keyframe_rebase_reported",
      rep.get("rotation_keyframes_rebased") == 12,
      f"rebased={rep.get('rotation_keyframes_rebased')} (expect 3 keys x 4)")
fcs = rot_fcurves(mover)
q12_new = keyed_quat(fcs, 12) if len(fcs) == 4 else None
q1_new = keyed_quat(fcs, 1) if len(fcs) == 4 else None
if q12_new is None:
    check("C1e.mid_key_equals_offset_times_key", False,
          "partial/absent rotation_quaternion fcurves after rebase")
else:
    err12 = q12_new.rotation_difference(q_anchor).angle
    check("C1e.mid_key_equals_offset_times_key", err12 < 1e-4,
          f"f12 key off anchor quat by {err12:.2e} rad")
    want1 = (q_anchor @ q12.inverted() @ q1).normalized()
    err1 = q1_new.rotation_difference(want1).angle
    check("C1f.first_key_offset_times_key_law", err1 < 1e-4,
          f"f1 key off q_offset@q_key by {err1:.2e} rad")

# euler-mode keys: refused even under override='keyframe' (C1 twin)
wipe()
bpy.ops.mesh.primitive_cube_add(size=0.5, location=(0, 0, 1))
eul = bpy.context.active_object
eul.name = "EulerKeyed"                     # rotation_mode stays 'XYZ'
eul.keyframe_insert(data_path="rotation_euler", frame=1)
bpy.ops.object.empty_add(location=(1, 1, 1))
an2 = bpy.context.active_object
an2.name = "AnchorE"
an2.rotation_euler = (0.3, 0.2, 0.7)
bpy.context.view_layer.update()
try:
    PL.seat_at(eul, an2, align=True, override='keyframe')
    check("C1g.euler_refused_even_keyframe", False, "euler keys accepted")
except RuntimeError as e:
    check("C1g.euler_refused_even_keyframe",
          "rotation" in str(e) and "QUATERNION" in str(e), str(e)[:110])

# ================================================================== C2
# physics_place._prep animated exclusion: ALL transform channels + env
# lane + parent chain
wipe()
bpy.ops.mesh.primitive_cube_add(location=(0, 0, 1))
rmover = bpy.context.active_object
rmover.name = "RotMover"
rmover.keyframe_insert(data_path="rotation_euler", frame=1)
rmover.rotation_euler[2] = 1.0
rmover.keyframe_insert(data_path="rotation_euler", frame=20)
movers, env, excluded = PP._prep([rmover])
row = [e for e in excluded if e["obj"] == "RotMover"]
check("C2a.rotation_keyed_mover_excluded",
      not movers and bool(row) and
      any(r.startswith("animated:") for r in row[0]["reasons"]),
      f"movers={[m.name for m in movers]} excluded={excluded}")
check("C2b.reason_names_rotation_channel",
      bool(row) and "rotation_euler" in ",".join(row[0]["reasons"]),
      f"reasons={row[0]['reasons'] if row else None}")
# env lane: a rotation-keyed PASSIVE body is NOT static (TB4) — must be
# excluded as animated_env (pre-fix the location-only filter passed it)
bpy.ops.mesh.primitive_cube_add(location=(3, 0, 0))
renv = bpy.context.active_object
renv.name = "RotEnv"
renv.keyframe_insert(data_path="rotation_euler", frame=1)
movers2, env2, excluded2 = PP._prep([rmover], environment=[renv])
env_row = [e for e in excluded2 if e["obj"] == "RotEnv"]
check("C2c.rotation_keyed_env_excluded",
      not env2 and bool(env_row) and "animated_env" in env_row[0]["reasons"],
      f"env={[e.name for e in env2]} excluded={excluded2}")
# parent chain: a keyed ANCESTOR drags the whole subtree (C2)
bpy.ops.object.empty_add(location=(0, 0, 0))
rig = bpy.context.active_object
rig.name = "KeyedRig"
rig.keyframe_insert(data_path="location", frame=1)
bpy.ops.mesh.primitive_cube_add(location=(0, 0, 1.2))
kid = bpy.context.active_object
kid.name = "KidOfKeyed"
kid.parent = rig
bpy.context.view_layer.update()
movers3, env3, excluded3 = PP._prep([kid])
kid_row = [e for e in excluded3 if e["obj"] == "KidOfKeyed"]
check("C2d.animated_parent_chain_excluded",
      bool(kid_row) and any(r.startswith("parent_animated:KeyedRig")
                            for r in kid_row[0]["reasons"]),
      f"excluded={excluded3}")

# ================================================================== C3
# modifiers guard: real refusal + allow_bake proceeds
wipe()
bpy.ops.mesh.primitive_cube_add(location=(0, 0, 1.5))
mcube = bpy.context.active_object
mcube.name = "ModCube"
bev = mcube.modifiers.new("Bev", 'BEVEL')
bev.width = 0.02
mcube.scale = (2.0, 2.0, 2.0)
bpy.ops.mesh.primitive_plane_add(size=10)
floor = bpy.context.active_object
floor.name = "Floor"
rep = PP.settle(objs=[mcube], environment=[floor], allow_bake=False, frames=8)
ex = {e["obj"]: e["reasons"] for e in rep.get("excluded", [])}
check("C3a.modifiers_block_bake_reason",
      "modifiers_block_bake" in ex.get("ModCube", []),
      f"excluded={rep.get('excluded')}")
check("C3b.refusal_short_circuits_sim",
      rep.get("movers") == [] and rep.get("ok") is False,
      f"movers={rep.get('movers')} ok={rep.get('ok')}")
rep2 = PP.settle(objs=[mcube], environment=[floor], allow_bake=True, frames=12)
check("C3c.allow_bake_proceeds",
      "ModCube" in rep2.get("movers", [])
      and "ModCube" in rep2.get("scale_baked", []),
      f"movers={rep2.get('movers')} baked={rep2.get('scale_baked')} "
      f"verdict={rep2.get('verdict')}")
check("C3d.no_block_reason_when_allowed",
      "modifiers_block_bake" not in
      [r for e in rep2.get("excluded", []) for r in e["reasons"]],
      f"excluded={rep2.get('excluded')}")

# ================================================================== C4
# multi-user bake: private '.SimBake' copy, original datablock untouched
wipe()
bpy.ops.mesh.primitive_cube_add(location=(0, 0, 1.5))
c1 = bpy.context.active_object
c1.name = "Shared1"
c1.scale = (2.0, 2.0, 2.0)
bpy.ops.mesh.primitive_cube_add(location=(5, 5, 0.5))
c2 = bpy.context.active_object
c2.name = "Shared2"
c2.data = c1.data                     # linked duplicate: users == 2
c1.data.name = "SharedMesh"
orig = [v.co.copy() for v in c1.data.vertices]
baked, copies = PP._bake_scales([c1], [], True)
check("C4a.private_copy_made",
      c1.name in copies and c1.data.users == 1 and c2.data.users == 1,
      f"copies={copies} c1.users={c1.data.users} c2.users={c2.data.users}")
check("C4b.copy_named_SimBake", c1.data.name.endswith(".SimBake"),
      c1.data.name)
check("C4c.original_datablock_untouched",
      c2.data is not c1.data
      and max((a.co - b.co).length for a, b in
              zip(c2.data.vertices, orig)) < 1e-9,
      "the SHARED datablock kept its pre-bake vertices")
check("C4d.bake_landed_on_private_copy",
      tuple(round(v, 6) for v in c1.scale) == (1.0, 1.0, 1.0)
      and max(abs(v.co.x) for v in c1.data.vertices) > 0.9,
      f"c1.scale={tuple(c1.scale)} (private copy carries the baked scale)")

# same law through the real settle entry point (allow_copy authorizes
# the users>1 mover; the bake swaps the private copy in)
wipe()
bpy.ops.mesh.primitive_cube_add(location=(0, 0, 1.5))
s1 = bpy.context.active_object
s1.name = "Shared1"
s1.scale = (2.0, 2.0, 2.0)
bpy.ops.mesh.primitive_cube_add(location=(5, 5, 0.5))
s2 = bpy.context.active_object
s2.name = "Shared2"
s2.data = s1.data
bpy.ops.mesh.primitive_plane_add(size=10)
floor4 = bpy.context.active_object
floor4.name = "Floor"
rep4 = PP.settle(objs=[s1], environment=[floor4], allow_bake=True,
                 allow_copy=True, frames=10)
check("C4e.settle_reports_simbake_copies",
      "Shared1" in rep4.get("simbake_data_copies", []),
      f"simbake={rep4.get('simbake_data_copies')} "
      f"verdict={rep4.get('verdict')}")
check("C4f.object_on_private_copy_after_settle",
      s1.data.name.endswith(".SimBake") and s2.data is not s1.data,
      f"s1.data={s1.data.name}")

# ================================================================== C6
# skinned guard: driver-posed and manually-posed armatures (zero anim)
wipe()
bpy.ops.object.armature_add(location=(0, 0, 0))
arm_obj = bpy.context.active_object
arm_obj.name = "RigDriver"
eb = arm_obj.data.edit_bones[0]
eb.head = (0, 0, 0)
eb.tail = (0, 0, 1)
bpy.ops.object.mode_set(mode='OBJECT')
pb = arm_obj.pose.bones["Bone"]
fcd = pb.driver_add("location", 0)     # DRIVER-posed: zero action/NLA
fcd.driver.type = 'SCRIPTED'
fcd.driver.expression = "0.5"
bpy.ops.mesh.primitive_cube_add(location=(0, 0, 1.2))
fig6 = bpy.context.active_object
fig6.name = "FigDriver"
fig6.parent = arm_obj
bpy.ops.mesh.primitive_plane_add(size=6)
floor6 = bpy.context.active_object
floor6.name = "Floor6"
bpy.context.view_layer.update()
try:
    PL.place_on(fig6, floor6)
    check("C6a.driver_posed_refused", False, "driver-posed rig passed the guard")
except RuntimeError as e:
    check("C6a.driver_posed_refused", "ANIMATED skinned" in str(e), str(e)[:110])

# manually-posed armature (no animation data AT ALL): only the C6
# pose-matrix probe can catch this class
bpy.ops.object.armature_add(location=(3, 0, 0))
arm2 = bpy.context.active_object
arm2.name = "RigManual"
eb2 = arm2.data.edit_bones[0]
eb2.head = (3, 0, 0)
eb2.tail = (3, 0, 1)
bpy.ops.object.mode_set(mode='OBJECT')
pb2 = arm2.pose.bones["Bone"]
pb2.rotation_euler = (0.0, 0.6, 0.0)   # bent in place, zero keyframes
bpy.ops.mesh.primitive_cube_add(location=(3, 0, 1.2))
fig6b = bpy.context.active_object
fig6b.name = "FigManual"
fig6b.parent = arm2
bpy.context.view_layer.update()
check("C6b.pose_probe_decisive", PL._armature_pose_offset(arm2) is True,
      "pose-bone matrix probe must flag a manually-posed rig")
try:
    PL.place_on(fig6b, floor6)
    check("C6c.manual_pose_refused", False, "manually-posed rig passed")
except RuntimeError as e:
    check("C6c.manual_pose_refused", "ANIMATED skinned" in str(e), str(e)[:110])

# ================================================================== C7
# seat_at: skinned object refuses without force, force=True proceeds
wipe()
arm7 = bpy.data.armatures.new("Arm7")
arm7_obj = bpy.data.objects.new("ArmRig7", arm7)
bpy.context.collection.objects.link(arm7_obj)
arm7_obj.location = (0, 0, 5)
arm7_obj.keyframe_insert(data_path="location", frame=1)
bpy.ops.mesh.primitive_cube_add(location=(0.2, 0, 0))
fig7 = bpy.context.active_object
fig7.name = "SkinnedFig"
fig7.parent = arm7_obj
bpy.ops.object.empty_add(location=(1, 2, 3))
anchor7 = bpy.context.active_object
anchor7.name = "SeatAnchor7"
bpy.context.view_layer.update()
try:
    PL.seat_at(fig7, anchor7)
    check("C7a.seat_skinned_refused", False, "no guard on seat_at")
except RuntimeError as e:
    check("C7a.seat_skinned_refused", "ANIMATED skinned" in str(e),
          str(e)[:110])
rep7 = PL.seat_at(fig7, anchor7, force=True)
check("C7b.seat_force_proceeds",
      rep7.get("op") == "seat_at" and "applied_translation_m" in rep7,
      f"report keys={sorted(rep7)[:8]}")

# ================================================================== C9
# align_to_surface on footprint='grid' (the silent no-op class)
wipe()
bpy.ops.mesh.primitive_plane_add(size=10)
ramp = bpy.context.active_object
ramp.name = "Ramp"
ramp.rotation_euler = (math.radians(12.0), 0, 0)   # 12 deg incline
bpy.ops.mesh.primitive_cube_add(size=0.6, location=(0, 0, 1.2))
box9 = bpy.context.active_object
box9.name = "Box9"
bpy.context.view_layer.update()
q_pre = box9.matrix_world.to_quaternion().copy()
rep9 = PL.place_on(box9, ramp, footprint='grid', align_to_surface=True)
check("C9a.aligned_reported_true", rep9.get("aligned_to_surface") is True,
      f"aligned_to_surface={rep9.get('aligned_to_surface')} "
      f"skip={rep9.get('align_skip_reason')}")
check("C9b.report_carries_slope_and_quat",
      isinstance(rep9.get("slope_deg"), float) and rep9["slope_deg"] > 5.0
      and "aligned_rotation_q" in rep9,
      f"slope_deg={rep9.get('slope_deg')}")
bpy.context.view_layer.update()
q_post = box9.matrix_world.to_quaternion()
turn = q_pre.rotation_difference(q_post).angle
check("C9c.rotation_actually_changed", turn > math.radians(5.0),
      f"world rotation moved {math.degrees(turn):.2f} deg (0 == silent no-op)")
n_ramp = (ramp.matrix_world.to_3x3() @ Vector((0, 0, 1))).normalized()
z_box = (box9.matrix_world.to_3x3() @ Vector((0, 0, 1))).normalized()
check("C9d.box_z_maps_to_surface_normal", z_box.dot(n_ramp) > 0.99,
      f"dot={z_box.dot(n_ramp):.4f} (T2 law: +Z onto the normal)")
check("C9e.no_skip_reason_on_real_align", "align_skip_reason" not in rep9,
      f"skip={rep9.get('align_skip_reason')}")

# ================================================================== C10
# place_on mode token validated (was a raw dict KeyError)
wipe()
bpy.ops.mesh.primitive_cube_add(size=0.5, location=(0, 0, 2))
b10 = bpy.context.active_object
b10.name = "Box10"
bpy.ops.mesh.primitive_plane_add(size=6)
f10 = bpy.context.active_object
f10.name = "Floor10"
bpy.context.view_layer.update()
try:
    PL.place_on(b10, f10, mode='median')
    check("C10.mode_median_refused", False, "'median' accepted")
except RuntimeError as e:
    check("C10.mode_median_refused",
          "median" in str(e) and "'rest'" in str(e) and "'p50'" in str(e),
          str(e)[:130])

# ================================================================== C11
# contact_discs._kd_at_rest reads last_x/last_y AFTER the frame_set
wipe()
scene = bpy.context.scene
bpy.ops.object.empty_add(location=(0, 0, 0))
belt = bpy.context.active_object
belt.name = "Belt"
bpy.ops.mesh.primitive_cube_add(location=(5, 1, 0.2))
zed = bpy.context.active_object
zed.name = "Zed.A"
zed.keyframe_insert(data_path="location", index=0, frame=1)   # x=5
zed.location.x = 10.0
zed.keyframe_insert(data_path="location", index=0, frame=100)  # x=10
scene.frame_set(1)                     # parked at f1: location reads x=5
bpy.context.view_layer.update()
ctx = {"belt": belt, "scene": scene,
       "chars": {"zombies": {"kd": [zed]}}}
made = contact_discs._kd_at_rest(ctx, contact_discs._mat(), [0],
                                 [("A", 1.0, 0.0, "fall")], frame_at=None)
check("C11a.kd_disc_created",
      len(made) == 1 and made[0].name == "Contact.KD.A",
      f"made={[o.name for o in made]}")
dx = made[0].location.x if made else float("nan")
check("C11b.disc_at_last_keyed_x", abs(dx - 10.0) < 1e-5,
      f"disc x={dx:.4f} — 5.0 would be the pre-fix parked-frame residue")

# ================================================================== C12
# prop_carry keys rotation_quaternion on a QUATERNION-mode prop
wipe()
scene = bpy.context.scene
bpy.ops.object.empty_add(location=(0, 0, 1))
wrap = bpy.context.active_object
wrap.name = "Wrap"
wrap.keyframe_insert(data_path="location", frame=1)
wrap.location = (2.0, 0, 1)
wrap.keyframe_insert(data_path="location", frame=8)
bpy.ops.mesh.primitive_cube_add(size=0.3, location=(0, 0, 1))
prop = bpy.context.active_object
prop.name = "Prop12"
prop.rotation_mode = 'QUATERNION'
scene.frame_set(1)
prop.parent = wrap
prop.matrix_parent_inverse = wrap.matrix_world.inverted()
prop.location = (0.0, 0.0, 0.0)   # post-parenting basis == I (carry contract)
bpy.context.view_layer.update()
W1 = PC.capture_anchor(wrap, scene, 1)
# ride law (module docstring pattern): des(f) = wrap(f) @ carry_local must
# equal the prop's natural parented world W0(f) = wrap(f) @ P (basis == I),
# so carry_local == P == W1^-1 here — carry_keys' blend_to identity check
# then holds at every keyed frame.
carry_local = W1.inverted() @ prop.matrix_world.copy()
issues = PC.carry_keys(prop, scene, frames=range(1, 9),
                       desired_world=lambda: wrap.matrix_world @ carry_local,
                       blend_from=1, blend_to=8, end_frame=16)
check("C12a.carry_clean", issues == [], str(issues)[:140])
rot_paths = set()
if prop.animation_data is not None and prop.animation_data.action is not None:
    rot_paths = {fc.data_path for fc in
                 iter_fcurves(prop.animation_data.action)}
check("C12b.quaternion_fcurves_present",
      "rotation_quaternion" in rot_paths, f"paths={sorted(rot_paths)}")
check("C12c.euler_fcurves_absent",
      "rotation_euler" not in rot_paths,
      f"paths={sorted(rot_paths)} (pre-fix keyed euler unconditionally)")

# ================================================================== end
print("=" * 60)
print(f"[S18C] {len(PASS)} passed, {len(FAIL)} failed")
if FAIL:
    print(f"[S18C] FAILED: {FAIL}")
    sys.exit(1)
print(f"[S18C] ALL PASS ({len(PASS)} checks)")
sys.exit(0)
