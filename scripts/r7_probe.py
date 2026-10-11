"""r7_probe.py — ground truth on the mezzanine slab near the stair."""
import os
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = "/home/z/vision-work"
bpy.ops.wm.open_mainfile(filepath=os.path.join(
    ROOT, "output", "r7", "loft_nav.blend"))

slab = bpy.data.objects["mezzanine_slab"]
dg = bpy.context.evaluated_depsgraph_get()
tree = BVHTree.FromObject(slab, dg)
mw = slab.matrix_world
print("[probe] slab matrix_world.translation:",
      [round(v, 3) for v in mw.translation])
print("[probe] slab scale:", [round(v, 4) for v in mw.to_scale()])
print("[probe] slab polys:", len(slab.data.polygons))

# polygon center world distribution
zs = {}
for p in slab.data.polygons:
    wz = (mw @ p.center).z
    zs[round(wz, 1)] = zs.get(round(wz, 1), 0) + 1
print("[probe] poly center z histogram:", zs)

# where does the slab exist along x=3.398?
print("[probe] ray-down hits at x=3.398:")
for y in [8.6, 9.0, 9.4, 9.7, 10.0, 10.9, 12.0]:
    inv = mw.inverted()
    o = inv @ Vector((3.398, y, 3.7))
    d = inv.to_3x3() @ Vector((0, 0, -1))
    h = tree.ray_cast(o, d)
    if h[0] is not None:
        wz = (mw @ h[0]).z
        print(f"   y={y}: world z {wz:.3f}")
    else:
        print(f"   y={y}: MISS")

# also scan a grid to map slab xy extent (z band 2.5..3.3)
hits = 0
minx, maxx, miny, maxy = 99, -99, 99, -99
for xi in range(-30, 36, 2):
    for yi in range(85, 162, 2):
        x, y = xi / 10, yi / 10
        inv = mw.inverted()
        o = inv @ Vector((x, y, 3.3))
        d = inv.to_3x3() @ Vector((0, 0, -1))
        h = tree.ray_cast(o, d)
        if h[0] is not None and 2.5 < (mw @ h[0]).z < 3.3:
            hits += 1
            minx, maxx = min(minx, x), max(maxx, x)
            miny, maxy = min(miny, y), max(maxy, y)
print(f"[probe] slab top-surface hits {hits}/1080; x [{minx},{maxx}] "
      f"y [{miny},{maxy}]")
