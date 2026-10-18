"""s23_gait_locus.py — where does the UAL walk's gait live?

Replays Walk_Loop on the SOURCE rig three ways and samples feet/hips
world z:
  A. as-authored (all channels)
  B. rotation channels only (locations zeroed)
  C. location channels only (rotations identity)
Prints GLOC lines.
"""
import bpy, os, sys
from mathutils import Quaternion

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))
import assets_ual_actors as ual  # noqa: E402
import blender_kit  # noqa: E402


def P(*a):
    print("GLOC", *a, flush=True)


bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.render.fps = 30
u = ual._import_actor("Driver", ual.ACTOR_SCALE)
arm = u["armature"]
walk = u["actions"]["Walk_Loop"]

fcs = list(blender_kit.iter_fcurves(walk))
P("total fcurves:", len(fcs))
loc = [fc for fc in fcs if fc.data_path.endswith(".location")]
rot = [fc for fc in fcs if fc.data_path.endswith(".rotation_quaternion")]
P("loc fcurves:", len(loc), "rot fcurves:", len(rot))
# magnitude census: which bones carry NONZERO location deltas?
import collections
locmag = {}
for fc in loc:
    bone = fc.data_path.split('"')[1]
    vals = [kp.co[1] for kp in fc.keyframe_points]
    span = max(vals) - min(vals)
    locmag.setdefault(bone, 0.0)
    locmag[bone] = max(locmag[bone], span)
big = {b: round(v, 4) for b, v in sorted(locmag.items(), key=lambda kv: -kv[1])[:8]}
P("top location spans:", big)
rotmag = {}
for fc in rot:
    bone = fc.data_path.split('"')[1]
    vals = [kp.co[1] for kp in fc.keyframe_points]
    span = max(vals) - min(vals)
    rotmag.setdefault(bone, 0.0)
    rotmag[bone] = max(rotmag[bone], span)
P("top rot spans (raw q components):",
  {b: round(v, 3) for b, v in sorted(rotmag.items(), key=lambda kv: -kv[1])[:6]})

sc = bpy.context.scene
ad = arm.animation_data


def feet_and_hips(tag):
    seq_f, seq_h = [], []
    for f in range(1, 41, 4):
        sc.frame_set(f)
        bpy.context.view_layer.update()
        fz = []
        for pb in arm.pose.bones:
            if "foot" in pb.name.lower() and not pb.name.lower().endswith("_end"):
                fz.append((arm.matrix_world @ pb.matrix).translation.z)
        hz = (arm.matrix_world @ arm.pose.bones["DEF-hips"].matrix).translation.z
        seq_f.append([round(v, 4) for v in fz])
        seq_h.append(round(hz, 4))
    flat = [z for pair in seq_f for z in pair]
    P(f"{tag}: feet min/max {min(flat):.4f}/{max(flat):.4f} "
      f"hips {min(seq_h):.4f}-{max(seq_h):.4f}")


def _assign(act):
    ad.action = act
    if act is not None and act.slots:
        ad.action_slot = act.slots[0]


# A: as-authored
_assign(walk)
feet_and_hips("A as-authored")

# B: rotations only — build a stripped copy
b_act = walk.copy()
b_act.name = "Walk_rotOnly"
for fc in list(blender_kit.iter_fcurves(b_act)):
    if fc.data_path.endswith(".location"):
        b_act.fcurves.remove(fc) if hasattr(b_act, 'fcurves') else None
# 5.x: remove via the channelbag
try:
    bag = b_act.layers[0].strips[0].channelbag(b_act.slots[0])
    for fc in list(bag.fcurves):
        if fc.data_path.endswith(".location"):
            bag.fcurves.remove(fc)
except Exception as e:
    P("rot-only strip failed:", repr(e))
_assign(b_act)
feet_and_hips("B rot-only")

# C: locations only
c_act = walk.copy()
c_act.name = "Walk_locOnly"
try:
    bag = c_act.layers[0].strips[0].channelbag(c_act.slots[0])
    for fc in list(bag.fcurves):
        if not fc.data_path.endswith(".location"):
            bag.fcurves.remove(fc)
except Exception as e:
    P("loc-only strip failed:", repr(e))
_assign(c_act)
feet_and_hips("C loc-only")

_assign(None)
P("PROBE-DONE")
