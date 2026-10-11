"""r7_probe16.py — stair top end + slab coverage at arrival."""
import bpy
from mathutils import Vector

bpy.ops.wm.open_mainfile(filepath="/home/z/vision-work/output/r6/loft_cut_arch_lite.blend")
dg = bpy.context.evaluated_depsgraph_get()
sc = bpy.context.scene

print("[probe16] A) treads from z=2.60, x=2.96 column, y 9.9..14.2:")
for yi in range(44):
    y = 9.9 + 0.1 * yi
    hit, loc, nrm, idx, obj, mat = sc.ray_cast(
        dg, Vector((2.96, y, 2.6)), Vector((0, 0, -1)))
    if hit:
        print(f"[probe16]   y={y:5.1f} z={loc.z:5.2f} {obj.name}")
print("[probe16] B) from z=3.6 (slab level), x=2.96, y 13.0..15.5:")
for yi in range(26):
    y = 13.0 + 0.1 * yi
    hit, loc, nrm, idx, obj, mat = sc.ray_cast(
        dg, Vector((2.96, y, 3.6)), Vector((0, 0, -1)))
    if hit:
        print(f"[probe16]   y={y:5.1f} z={loc.z:5.2f} {obj.name}")
