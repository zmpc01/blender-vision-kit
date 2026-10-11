"""r7_probe5.py — scene-level ray-cast: what IS the stair surface?"""
import bpy
from mathutils import Vector

ROOT = "/home/z/vision-work"
bpy.ops.wm.open_mainfile(filepath=f"{ROOT}/output/r6/loft_cut_arch.blend")
dg = bpy.context.evaluated_depsgraph_get()

print("[probe5] scene ray-down along the stair run (x across width):")
for y in [7.5, 7.8, 8.1, 8.4]:
    for x in [2.9, 3.1, 3.3, 3.4, 3.45]:
        hit, loc, nrm, idx, obj, mat = scene_ray = bpy.context.scene.ray_cast(
            dg, Vector((x, y, 3.6)), Vector((0, 0, -1)))
        if hit:
            print(f"[probe5]   ({x:.2f},{y:.2f}) -> z {loc.z:5.2f}  "
                  f"obj '{obj.name}'  n=({nrm.x:.2f},{nrm.y:.2f},{nrm.z:.2f})")
        else:
            print(f"[probe5]   ({x:.2f},{y:.2f}) -> MISS")
    print("[probe5]   ---")
