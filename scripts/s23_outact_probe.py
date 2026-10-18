"""s23_outact_probe.py — inspect the retargeted OUTPUT action directly.

Census: fcurve count, per-class channel presence, sampled values on
the leg chain; then replay it on the wrapped rig with explicit
slot-pinned assignment and sample world feet z.
"""
import bpy, os, sys
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))
import assets_ual_actors as ual   # noqa: E402
import assets_quaternius          # noqa: E402
import rig_retarget               # noqa: E402
import blender_kit                # noqa: E402


def P(*a):
    print("OACT", *a, flush=True)


bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.render.fps = 30
u = ual._import_actor("Driver", ual.ACTOR_SCALE)
rep = assets_quaternius.load("male", "HeroQ")
r = rig_retarget.retarget(u["armature"], u["actions"]["Walk_Loop"],
                          rep["arm"])
out = r["action"]
fcs = list(blender_kit.iter_fcurves(out))
P("out fcurves:", len(fcs))
paths = sorted({fc.data_path for fc in fcs})
P("distinct paths:", len(paths))
for want in ("Foot.L", "UpperLeg.L", "LowerLeg.L", "Hips"):
    hit = [p for p in paths if f'"{want}"' in p]
    P(f"channels for {want}:", hit)
# sampled values on Foot.L rotation w-channel
for fc in fcs:
    if '"Foot.L"' in fc.data_path and fc.data_path.endswith(
            "rotation_quaternion") and fc.array_index == 0:
        vals = [round(kp.co[1], 4) for kp in fc.keyframe_points[:6]]
        P("Foot.L quat-w first keys:", vals,
          "frames:", [round(kp.co[0], 1) for kp in fc.keyframe_points[:6]])
        break
# frame range
P("out frame_range:", tuple(out.frame_range))

# replay with explicit pin
arm = rep["arm"]
ad = arm.animation_data or arm.animation_data_create()
ad.action = out
if out.slots:
    ad.action_slot = out.slots[0]
P("assigned; slot count:", len(out.slots))
sc = bpy.context.scene
seq = []
for f in range(0, 40, 4):
    sc.frame_set(f)
    bpy.context.view_layer.update()
    fz = []
    for pb in arm.pose.bones:
        if "foot" in pb.name.lower() and not pb.name.lower().endswith("_end"):
            fz.append(round((arm.matrix_world @ pb.matrix).translation.z, 4))
    seq.append(fz)
P("world feet z seq (wrapper-scaled):", seq)

# DECISIVE: manually drive the thigh 60deg — do feet move?
import math
from mathutils import Quaternion
ad.action = None
thigh = arm.pose.bones["UpperLeg.L"]
thigh.rotation_quaternion = Quaternion((1, 0, 0, 0))
sc.frame_set(1)
bpy.context.view_layer.update()
P("manual rest thigh foot z:",
  [round((arm.matrix_world @ pb.matrix).translation.z, 4)
   for pb in arm.pose.bones
   if "foot" in pb.name.lower() and not pb.name.lower().endswith("_end")])
thigh.rotation_quaternion = Quaternion((0.866, 0.5, 0, 0))  # 60deg about X
bpy.context.view_layer.update()
P("manual 60deg thigh foot z:",
  [round((arm.matrix_world @ pb.matrix).translation.z, 4)
   for pb in arm.pose.bones
   if "foot" in pb.name.lower() and not pb.name.lower().endswith("_end")])
# and with an action assigned, is the pose OVERRIDDEN at frame_set?
ad.action = out
if out.slots:
    ad.action_slot = out.slots[0]
sc.frame_set(10)
bpy.context.view_layer.update()
P("f10 thigh quat (action-driven):",
  tuple(round(v, 4) for v in arm.pose.bones["UpperLeg.L"].rotation_quaternion))
P("f10 foot z:",
  [round((arm.matrix_world @ pb.matrix).translation.z, 4)
   for pb in arm.pose.bones
   if "foot" in pb.name.lower() and not pb.name.lower().endswith("_end")])
P("PROBE-DONE")
