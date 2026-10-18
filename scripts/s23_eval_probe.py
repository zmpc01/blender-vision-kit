"""s23_eval_probe.py — is pose evaluation broken at import, wrapper, or
always? Three arms: raw FBX import / loader-wrapped / UAL glTF.
Manual thigh rotation + world-foot read on each.
"""
import bpy, os, sys, math
from mathutils import Quaternion

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))


def P(*a):
    print("EVAL", *a, flush=True)


def foot_z(arm):
    return [round((arm.matrix_world @ pb.matrix).translation.z, 4)
            for pb in arm.pose.bones
            if "foot" in pb.name.lower()
            and not pb.name.lower().endswith("_end")]


def manual_test(tag, arm, thigh_name):
    P(f"--- {tag} ({arm.name}) ---")
    sc = bpy.context.scene
    ad = arm.animation_data
    P("action:", ad.action.name if ad and ad.action else None,
      "nla tracks:", len(ad.nla_tracks) if ad else 0)
    sc.frame_set(1)
    bpy.context.view_layer.update()
    z0 = foot_z(arm)
    pb = arm.pose.bones.get(thigh_name)
    pb.rotation_quaternion = Quaternion((0.866, 0.5, 0, 0))
    sc.frame_set(1)
    bpy.context.view_layer.update()
    z1 = foot_z(arm)
    P("rest:", z0, "after 60deg:", z1, "moved:", z0 != z1)
    P("quat now:", tuple(round(v, 3) for v in pb.rotation_quaternion),
      "matrix_basis rot w:", round(pb.matrix_basis.to_quaternion().w, 3),
      "pb.matrix t:", tuple(round(v, 3)
                            for v in pb.matrix.translation),
      "rest t:", tuple(round(v, 3)
                       for v in arm.data.bones[pb.name].matrix_local.translation))
    pb.rotation_quaternion = Quaternion((1, 0, 0, 0))
    sc.frame_set(1)
    bpy.context.view_layer.update()


# A. raw FBX import
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=os.path.join(
    _REPO, "assets", "vendor", "quaternius", "Male_Casual.fbx"))
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
manual_test("A raw FBX", arm, "UpperLeg.L")

# B. loader-wrapped
bpy.ops.wm.read_factory_settings(use_empty=True)
import assets_quaternius  # noqa: E402
rep = assets_quaternius.load("male", "HeroQ")
manual_test("B loader-wrapped", rep["arm"], "UpperLeg.L")

# C. UAL mannequin
bpy.ops.wm.read_factory_settings(use_empty=True)
import assets_ual_actors as ual  # noqa: E402
u = ual._import_actor("Driver", ual.ACTOR_SCALE)
manual_test("C UAL", u["armature"], "DEF-thigh.L")

# A2. pose_position check + flip
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=os.path.join(
    _REPO, "assets", "vendor", "quaternius", "Male_Casual.fbx"))
armP = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
P("A2 pose_position on import:", armP.data.pose_position)
armP.data.pose_position = 'POSE'
sc3 = bpy.context.scene
sc3.frame_set(1)
bpy.context.view_layer.update()
pbP = armP.pose.bones["UpperLeg.L"]
pbP.rotation_quaternion = Quaternion((0.866, 0.5, 0, 0))
bpy.context.view_layer.update()
P("A2 after POSE + manual:", foot_z(armP), "moved:",
  foot_z(armP) != [0.0542, 0.0542])
# A3: force-eval triggers
armP.update_tag()
bpy.context.view_layer.update()
P("A3 after update_tag:", foot_z(armP), "moved:",
  foot_z(armP) != [0.0542, 0.0542])
bpy.context.evaluated_depsgraph_get()
P("A3 after depsgraph_get:", foot_z(armP), "moved:",
  foot_z(armP) != [0.0542, 0.0542])
sc3.frame_set(2)
sc3.frame_set(1)
bpy.context.view_layer.update()
P("A3 after frame bounce:", foot_z(armP), "moved:",
  foot_z(armP) != [0.0542, 0.0542])
armP.pose.bones["UpperLeg.L"].matrix_basis = (
    armP.pose.bones["UpperLeg.L"].matrix_basis @
    __import__('mathutils').Matrix.Rotation(0.6, 4, 'X'))
bpy.context.view_layer.update()
P("A3 matrix_basis direct:", foot_z(armP), "moved:",
  foot_z(armP) != [0.0542, 0.0542])

# H. hierarchy check on the raw FBX rig
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=os.path.join(
    _REPO, "assets", "vendor", "quaternius", "Male_Casual.fbx"))
armH = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
for nm in ("UpperLeg.L", "LowerLeg.L", "Foot.L", "Hips", "Body", "Bone"):
    b = armH.data.bones.get(nm)
    P(f"H {nm}: parent={b.parent.name if b and b.parent else None} "
      f"children={[c.name for c in b.children] if b else None}")

# D. raw import -> clear action ONLY (no loader) -> manual pose
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=os.path.join(
    _REPO, "assets", "vendor", "quaternius", "Male_Casual.fbx"))
armD = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
adD = armD.animation_data
P("D slot before clear:", str(adD.action_slot) if adD.action_slot else None)
adD.action = None
P("D slot after clear:", str(adD.action_slot) if adD.action_slot else None,
  "action_slot ptr set:", adD.action_slot is not None)
sc2 = bpy.context.scene
sc2.frame_set(1)
bpy.context.view_layer.update()
pbD = armD.pose.bones["UpperLeg.L"]
pbD.rotation_quaternion = Quaternion((0.866, 0.5, 0, 0))
bpy.context.view_layer.update()
P("D after clear+manual:", foot_z(armD), "moved:",
  foot_z(armD) != [0.0542, 0.0542])
# E. then explicitly null the slot and retry
try:
    adD.action_slot = None
    P("E slot nulled ok")
except Exception as e:
    P("E slot null failed:", repr(e))
bpy.context.view_layer.update()
P("E after slot null:", foot_z(armD), "moved:",
  foot_z(armD) != [0.0542, 0.0542])
P("PROBE-DONE")
