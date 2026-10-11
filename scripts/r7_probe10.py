"""r7_probe10.py — down-ray grid over the uncovered strip y 9.0-9.35."""
import bpy
from mathutils import Vector

bpy.ops.wm.open_mainfile(filepath="/home/z/vision-work/output/r6/loft_cut_arch_lite.blend")
dg = bpy.context.evaluated_depsgraph_get()
sc = bpy.context.scene

print("[probe10] scene ray-down grid (z of first hit / obj):")
hdr = "y\\x   " + "".join(f"{x:9.2f}" for x in
                          [2.95 + 0.05 * i for i in range(12)])
print("[probe10] " + hdr)
for yi in range(18):
    y = 9.0 + 0.02 * yi
    row = f"{y:5.2f} "
    for i in range(12):
        x = 2.95 + 0.05 * i
        hit, loc, nrm, idx, obj, mat = sc.ray_cast(
            dg, Vector((x, y, 3.6)), Vector((0, 0, -1)))
        row += f"{loc.z:6.2f} {obj.name[:3]:>3}" if hit else "     .    "
    print("[probe10] " + row)
