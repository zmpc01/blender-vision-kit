"""_s18_strip_probe.py — why does the static AmberSlab slide across
filmstrip cells? Project its center from the fixed persp camera at f1
and f24; also dump every camera/constraint/animation in the scene."""
import bpy
from mathutils import Vector

bpy.ops.wm.open_mainfile(filepath="output/s18_eyecert/eyecert.blend")
scene = bpy.context.scene

print("[probe2] cameras + constraints + anim:")
from blender_kit import iter_fcurves
for o in scene.objects:
    if o.type == 'CAMERA':
        print(f"  cam {o.name}: loc={tuple(round(v,2) for v in o.location)} "
              f"constraints={[c.type for c in o.constraints]} "
              f"anim={bool(o.animation_data)}")
    if o.animation_data and o.animation_data.action:
        paths = sorted({fc.data_path for fc in iter_fcurves(o.animation_data.action)})
        print(f"  anim on {o.name}: paths={paths}")

from bpy_extras.object_utils import world_to_camera_view
# reconstruct the persp temp camera exactly like _add_temp_camera
import viewport_capture as vc
import inspect
src = inspect.getsource(vc._add_temp_camera)
print("[probe2] _add_temp_camera aims by:", "constraint" if "constraint" in src else "rotation-euler")

loc = tuple(vc.VIEW_ANGLES["persp"][:3])
cam_data = bpy.data.cameras.new("probe2_cam")
cam = bpy.data.objects.new("probe2_cam", cam_data)
bpy.context.collection.objects.link(cam)
target = Vector((0, 0, 0))
d = target - Vector(loc)
cam.location = loc
cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
scene.camera = cam
scene.render.resolution_x = 480
scene.render.resolution_y = 360
scene.render.resolution_percentage = 100

for f in (1, 10, 24):
    scene.frame_set(f)
    bpy.context.view_layer.update()
    dep = bpy.context.evaluated_depsgraph_get()
    dep.update()
    for name in ("AmberSlab", "FloatBox", "MarkerCone", "RedCube"):
        o = scene.objects.get(name)
        rv = world_to_camera_view(scene, cam, o.matrix_world.translation)
        print(f"[probe2] f{f} {name}: world=({o.matrix_world.translation.x:.2f},"
              f"{o.matrix_world.translation.y:.2f},{o.matrix_world.translation.z:.2f}) "
              f"ndc=({rv.x:.3f},{rv.y:.3f},z={rv.z:.3f})")
