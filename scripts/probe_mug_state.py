"""probe_mug_state.py — why doesn't the validator see the sunken mug?"""
import bpy, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
bpy.ops.wm.open_mainfile(filepath="/home/z/vision-work/blender-vision-kit/output/reading_nook/work.blend")
scene = bpy.context.scene
scene.frame_set(1)
bpy.context.view_layer.update()
bpy.context.view_layer.update()

mug = bpy.data.objects["Mug"]
table = bpy.data.objects["TableTop"]

def zmin(o):
    return min((o.matrix_world @ v.co).z for v in o.data.vertices)
def zmax(o):
    return max((o.matrix_world @ v.co).z for v in o.data.vertices)

print("[probe] frame", scene.frame_current)
print("[probe] mug zmin", round(zmin(mug), 4), "zmax", round(zmax(mug), 4),
      "origin z", round(mug.matrix_world.translation.z, 4))
print("[probe] table zmin", round(zmin(table), 4), "zmax", round(zmax(table), 4))
print("[probe] sink_mm", round((zmin(table) - zmin(mug)) * 1000, 2))

scene.frame_set(24)
bpy.context.view_layer.update()
print("[probe] f24 mug zmin", round(zmin(mug), 4), "x", round(mug.matrix_world.translation.x, 4))

import validate_scene as vs
scene.frame_set(1)
bpy.context.view_layer.update()
rep = vs.validate_scene()
for iss in rep.get("issues", []):
    print("[probe] validator:", iss.get("severity"), iss.get("type"),
          iss.get("ids", iss.get("objects", "")))
print("[probe] validator counts: P0", rep.get("P0", rep.get("p0")),
      "P1", rep.get("P1", rep.get("p1")))
