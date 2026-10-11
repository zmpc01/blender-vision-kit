"""r7_probe15.py — tread map from BELOW the slab overhang (z_start 2.6)."""
import bpy
from mathutils import Vector

bpy.ops.wm.open_mainfile(filepath="/home/z/vision-work/output/r6/loft_cut_arch_lite.blend")
dg = bpy.context.evaluated_depsgraph_get()
sc = bpy.context.scene

print("[probe15] ray-down from z=2.60 (under the slab overhang):")
xs = [2.4 + 0.1 * i for i in range(12)]
print("[probe15] y\\x   " + "".join(f"{x:5.2f}" for x in xs))
for yi in range(16):
    y = 8.3 + 0.1 * yi
    row = f"{y:5.1f} "
    for x in xs:
        hit, loc, nrm, idx, obj, mat = sc.ray_cast(
            dg, Vector((x, y, 2.6)), Vector((0, 0, -1)))
        row += f"{loc.z:5.2f} " if hit else "    . "
    print("[probe15] " + row)
print("[probe15] (obj names on request; '.' = no surface below 2.6)")
