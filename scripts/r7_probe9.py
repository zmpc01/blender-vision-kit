"""r7_probe9.py — tread z-vs-y profile: which end is the stair bottom?"""
import bpy
from mathutils import Vector

ROOT = "/home/z/vision-work"
bpy.ops.wm.open_mainfile(filepath=f"{ROOT}/output/r6/loft_cut_arch_lite.blend")
dg = bpy.context.evaluated_depsgraph_get()
sc = bpy.context.scene

import math
CAM = Vector((0.9, 6.2, 1.8))
TGT = Vector((3.32, 7.9, 1.5))
LENS_MM, W, H = 28.0, 960, 640
fwd = (TGT - CAM).normalized()
sensor_w = 36.0
aspect = H / W
sensor_h = sensor_w * aspect
right = fwd.cross(Vector((0, 0, 1))).normalized()
up = right.cross(fwd).normalized()

rows = {}
for ui in range(0, 40):
    for vi in range(20, 80):
        u = (ui / 40 - 0.2) * 2.0
        v = (vi / 80 - 0.5) * 2.0
        d = (fwd + right * (u * sensor_w / 2 / LENS_MM)
             + up * (v * sensor_h / 2 / LENS_MM)).normalized()
        hit, loc, nrm, idx, obj, mat = sc.ray_cast(dg, CAM, d)
        if hit and obj.name == "Cube" and 0.1 < loc.z < 2.8 \
                and 2.9 < loc.x < 3.55 and 7.9 < loc.y < 9.4:
            b = rows.setdefault(round(loc.y, 1),
                                {"zs": [], "xs": []})
            b["zs"].append(round(loc.z, 2))
            b["xs"].append(round(loc.x, 2))
            b.setdefault("nz", []).append(round(nrm.z, 2))

print("[probe9] y -> surface z (Cube, tread band, all normals):")
for y in sorted(rows):
    zs = rows[y]["zs"]
    xs = rows[y]["xs"]
    nz = rows[y].get("nz", [])
    up = len([n for n in nz if n > 0.5])
    print(f"[probe9]   y={y:4.1f}: z {sorted(set(zs))[:8]} n={len(zs):3d} "
          f"up={up}  x[{min(xs):.2f},{max(xs):.2f}]")
