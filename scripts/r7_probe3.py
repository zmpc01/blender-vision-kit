"""r7_probe3.py — ground-truth tread profile of the stairs object."""
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = "/home/z/vision-work"
bpy.ops.wm.open_mainfile(filepath=f"{ROOT}/output/r7/loft_nav.blend")

st = bpy.data.objects["stairs"]
dg = bpy.context.evaluated_depsgraph_get()
tree = BVHTree.FromObject(st, dg)
mw = st.matrix_world
inv = mw.inverted()
print("[probe3] stairs origin:", [round(v, 3) for v in mw.translation],
      "polys:", len(st.data.polygons))

# full surface map: x 3.30..3.50 step 0.04, y 7.30..8.50 step 0.04
xs = [3.30 + 0.04 * i for i in range(6)]
print("[probe3]      " + "".join(f"x={x:.2f}  " for x in xs))
for yi in range(31):
    y = 7.30 + 0.04 * yi
    row = f"y={y:.2f} "
    for x in xs:
        o = inv @ Vector((x, y, 3.7))
        d = inv.to_3x3() @ Vector((0, 0, -1))
        h = tree.ray_cast(o, d)
        row += "  ---  " if h[0] is None else f"{(mw @ h[0]).z:5.2f}  "
    print("[probe3] " + row)
