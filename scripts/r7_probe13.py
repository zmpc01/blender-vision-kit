"""r7_probe13.py — Plane.003 full tread map (wide region)."""
import bpy
from mathutils import Vector

bpy.ops.wm.open_mainfile(filepath="/home/z/vision-work/output/r6/loft_cut_arch_lite.blend")
ob = bpy.data.objects["Plane.003"]
mw = ob.matrix_world
bb = [mw @ Vector(c) for c in ob.bound_box]
print("[probe13] Plane.003 bbox: "
      f"x[{min(v.x for v in bb):.2f},{max(v.x for v in bb):.2f}] "
      f"y[{min(v.y for v in bb):.2f},{max(v.y for v in bb):.2f}] "
      f"z[{min(v.z for v in bb):.2f},{max(v.z for v in bb):.2f}] "
      f"polys={len(ob.data.polygons)}")

flats = []
for p in ob.data.polygons:
    vs = [mw @ ob.data.vertices[vi].co for vi in p.vertices]
    zs = [v.z for v in vs]
    if max(zs) - min(zs) > 0.06:
        continue
    n = (mw.to_3x3().inverted().transposed() @ p.normal).normalized()
    if n.z < 0.7:
        continue
    c = mw @ p.center
    if not (2.2 < c.x < 3.7 and 7.7 < c.y < 9.7 and 0.0 < c.z < 2.95):
        continue
    xs = [v.x for v in vs]; ys = [v.y for v in vs]
    flats.append((round(min(zs), 3), round(c.x, 2), round(c.y, 2),
                  (round(min(xs), 2), round(max(xs), 2)),
                  (round(min(ys), 2), round(max(ys), 2))))
flats.sort()
print(f"[probe13] {len(flats)} up-facing near-flat faces (tread tops):")
for z, cx, cy, xr, yr in flats:
    print(f"[probe13] z={z:5.2f} c=({cx},{cy}) x{xr} y{yr}")
