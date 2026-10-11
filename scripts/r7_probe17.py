"""r7_probe17.py — dissect the 0.846 float at frame 349."""
import sys
sys.path.insert(0, "/home/z/vision-work/scripts")
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

bpy.ops.wm.open_mainfile(filepath="/home/z/vision-work/output/r7/loft_nav.blend")
dg = bpy.context.evaluated_depsgraph_get()
sc = bpy.context.scene
sc.frame_set(349)
root = bpy.data.objects["Driver.Root"]
loc = root.matrix_world.translation
print(f"[probe17] frame 349 root at ({loc.x:.3f},{loc.y:.3f},{loc.z:.3f})")

for oid in ("Cube.001", "Plane.003", "mezzanine_slab"):
    ob = bpy.data.objects[oid]
    tree = BVHTree.FromObject(ob, dg)
    inv = ob.matrix_world.inverted()
    o = inv @ Vector((loc.x, loc.y, loc.z + 0.08))
    d = inv.to_3x3() @ Vector((0, 0, -1))
    h = tree.ray_cast(o, d)
    if h[0] is not None:
        print(f"[probe17] {oid}: hit z {(ob.matrix_world @ h[0]).z:.3f} "
              f"(local origin {[round(v,2) for v in ob.matrix_world.translation]})")
    else:
        print(f"[probe17] {oid}: MISS")
# scene-level truth at that xy
hit, l, n, i, ob, m = sc.ray_cast(dg, Vector((loc.x, loc.y, loc.z + 0.08)),
                                  Vector((0, 0, -1)))
print(f"[probe17] scene ray: z {l.z:.3f} '{ob.name}'" if hit
      else "[probe17] scene ray: MISS")
# path truth: what does the route say near y=loc.y?
import json
route = json.load(open("/home/z/vision-work/output/r7/route_request.json"))
print("[probe17] W3 ramp: base", route["waypoints"][2]["xy"],
      "top", route["waypoints"][3]["xy"])
