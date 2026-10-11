"""r7_probe8.py — which object owns the visible treads? (frustum scan)"""
import bpy
from mathutils import Vector

ROOT = "/home/z/vision-work"
bpy.ops.wm.open_mainfile(filepath=f"{ROOT}/output/r6/loft_cut_arch_lite.blend")
dg = bpy.context.evaluated_depsgraph_get()
sc = bpy.context.scene

CAM = Vector((0.9, 6.2, 1.8))
TGT = Vector((3.32, 7.9, 1.5))
LENS_MM = 28.0
W, H = 960, 640

fwd = (TGT - CAM).normalized()
# Blender sensor: default 36mm width; lens 28mm -> fov = 2*atan(18/28)
import math
sensor_w = 36.0
aspect = H / W
sensor_h = sensor_w * aspect
right = fwd.cross(Vector((0, 0, 1))).normalized()
up = right.cross(fwd).normalized()

hist = {}
for ui in range(0, 40):          # left 40% of the frame
    for vi in range(20, 80):     # middle 60% vertically
        u = (ui / 40 - 0.2) * 2.0     # -0.4..0.4 of half-width
        v = (vi / 80 - 0.5) * 2.0
        d = (fwd + right * (u * sensor_w / 2 / LENS_MM)
             + up * (v * sensor_h / 2 / LENS_MM)).normalized()
        hit, loc, nrm, idx, obj, mat = sc.ray_cast(dg, CAM, d)
        if hit:
            key = obj.name
            z = loc.z
            h = hist.setdefault(key, {"n": 0, "zmin": 9, "zmax": -9,
                                      "pts": []})
            h["n"] += 1
            h["zmin"] = min(h["zmin"], round(z, 2))
            h["zmax"] = max(h["zmax"], round(z, 2))
            if len(h["pts"]) < 400:
                h["pts"].append((round(loc.x, 2), round(loc.y, 2),
                                 round(z, 2)))

for k, h in sorted(hist.items(), key=lambda kv: -kv[1]["n"]):
    print(f"[probe8] {k}: {h['n']} rays, z [{h['zmin']},{h['zmax']}]")
    if k in ("stairs", "Cube") or h["n"] > 5:
        xs = [p[0] for p in h["pts"]]
        ys = [p[1] for p in h["pts"]]
        print(f"[probe8]    xy extent x[{min(xs)},{max(xs)}] "
              f"y[{min(ys)},{max(ys)}]")
