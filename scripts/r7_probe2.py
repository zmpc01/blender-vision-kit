"""r7_probe2.py — map the mezzanine slab's true top surface (stair zone).

Dense world-space ray-down grid from above the slab (z=3.7), ASCII map
of hit z. Runs on loft_nav.blend (same geometry as compose).
"""
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = "/home/z/vision-work"
bpy.ops.wm.open_mainfile(filepath=f"{ROOT}/output/r7/loft_nav.blend")

slab = bpy.data.objects["mezzanine_slab"]
dg = bpy.context.evaluated_depsgraph_get()
tree = BVHTree.FromObject(slab, dg)
mw = slab.matrix_world
inv = mw.inverted()

print("[probe2] world-space ray-down at x 2.0..3.5 step 0.1, "
      "y 8.3..12.3 step 0.2 (from z 3.7):")
hdr = "y\\x " + "".join(f"{x:4.1f}" for x in
                        [i / 10 for i in range(20, 36, 2)])
print("[probe2] " + hdr)
for yi in range(83, 124, 2):
    y = yi / 10
    row = f"{y:4.1f} "
    for xi in range(20, 36, 2):
        x = xi / 10
        o = inv @ Vector((x, y, 3.7))
        d = inv.to_3x3() @ Vector((0, 0, -1))
        h = tree.ray_cast(o, d)
        row += "   . " if h[0] is None else f"{(mw @ h[0]).z:4.2f}"
    print("[probe2] " + row)
