"""r7_probe12.py — which objects own faces in the stair volume?"""
import bpy
from mathutils import Vector

bpy.ops.wm.open_mainfile(filepath="/home/z/vision-work/output/r6/loft_cut_arch_lite.blend")

VOL = (2.9, 3.55, 7.9, 9.4, 0.05, 2.85)
def inbox(v):
    return (VOL[0] < v[0] < VOL[1] and VOL[2] < v[1] < VOL[3]
            and VOL[4] < v[2] < VOL[5])

stats = []
for ob in bpy.data.objects:
    if ob.type != "MESH":
        continue
    mw = ob.matrix_world
    n_in = 0
    flat_up = []       # near-flat faces w/ |nz|>0.7, a vert in volume
    for p in ob.data.polygons:
        vs = [mw @ ob.data.vertices[vi].co for vi in p.vertices]
        if not any(inbox(v) for v in vs):
            continue
        n_in += 1
        zs = [v.z for v in vs]
        if max(zs) - min(zs) < 0.06:
            n = (mw.to_3x3().inverted().transposed() @ p.normal).normalized()
            if abs(n.z) > 0.7:
                c = mw @ p.center
                flat_up.append((round(min(zs), 3), round(c.x, 2),
                                round(c.y, 2), round(n.z, 2)))
    if n_in:
        stats.append((n_in, ob.name, flat_up))
stats.sort(reverse=True)
for n_in, name, flat_up in stats[:8]:
    print(f"[probe12] {name}: {n_in} faces touch the stair volume, "
          f"{len(flat_up)} near-flat")
    flat_up.sort()
    for z, cx, cy, nz in flat_up[:14]:
        print(f"[probe12]    flat z={z:5.2f} c=({cx},{cy}) nz={nz}")
