"""s23_fcurve_probe.py — the 5.x slotted-action write-path probe.

Which target does channelbag.fcurves.new() resolve pose-bone paths
against on a FRESH action (no assignee)? Prints FPROBE lines.
"""
import bpy, os, sys
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))
import blender_kit  # noqa: E402


def P(*a):
    print("FPROBE", *a, flush=True)


bpy.ops.wm.read_factory_settings(use_empty=True)
# two armatures with DIFFERENT bone names
ad = bpy.data.armatures.new("A1")
ob1 = bpy.data.objects.new("Rig1", ad)
bpy.context.scene.collection.objects.link(ob1)
bpy.context.view_layer.objects.active = ob1
bpy.ops.object.mode_set(mode='EDIT')
b1 = ad.edit_bones.new("BoneAlpha")
b1.head, b1.tail = (0, 0, 0), (0, 0, 1)
bpy.ops.object.mode_set(mode='OBJECT')
ad2 = bpy.data.armatures.new("A2")
ob2 = bpy.data.objects.new("Rig2", ad2)
bpy.context.scene.collection.objects.link(ob2)
bpy.context.view_layer.objects.active = ob2
bpy.ops.object.mode_set(mode='EDIT')
b2 = ad2.edit_bones.new("BoneBeta")
b2.head, b2.tail = (0, 0, 0), (0, 0, 1)
bpy.ops.object.mode_set(mode='OBJECT')
bpy.context.view_layer.update()

act = bpy.data.actions.new("ProbeAct")
fcs = blender_kit.iter_fcurves(act)
P("scaffold ok")
slot = act.slots[0]
try:
    P("slot:", slot.name, "target id type:", slot.target_id_type)
except Exception as e:
    P("slot attrs failed:", repr(e))
try:
    P("context object:", bpy.context.object.name if bpy.context.object else None)
except Exception as e:
    P("context object failed:", repr(e))
try:
    P("active object:", bpy.context.view_layer.objects.active.name
      if bpy.context.view_layer.objects.active else None)
except Exception as e:
    P("active object failed:", repr(e))
try:
    fc = fcs.new('pose.bones["BoneBeta"].rotation_quaternion', index=0)
    P("new fcurve OK (active=Rig2):", fc.data_path)
except Exception as e:
    P("new fcurve FAILED (active=Rig2):", repr(e))
    P("switching active to Rig1 and retrying")
    bpy.context.view_layer.objects.active = ob1
    try:
        fc2 = fcs.new('pose.bones["BoneBeta"].rotation_quaternion', index=0)
        P("new fcurve OK (active=Rig1, path names BoneBeta):", fc2.data_path)
    except Exception as e2:
        P("failed with active=Rig1 too:", repr(e2))
P("PROBE-DONE")
