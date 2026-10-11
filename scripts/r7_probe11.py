"""r7_probe11.py — enumerate Cube's up-facing faces in the stair region."""
import bpy
from mathutils import Vector

bpy.ops.wm.open_mainfile(filepath="/home/z/vision-work/output/r6/loft_cut_arch_lite.blend")
cube = bpy.data.objects["Cube"]
mw = cube.matrix_world
print("[probe11] Cube origin:", [round(v, 3) for v in mw.translation])
faces = []
for p in cube.data.polygons:
    n = (mw.to_3x3().inverted().transposed() @ p.normal).normalized()
    if abs(n.z) < 0.7:
        continue
    vs = [tuple(round(v, 3) for v in (mw @ cube.data.vertices[vi].co))
          for vi in p.vertices]
    # any vertex inside the stair volume?
    inbox = [v for v in vs
             if 2.85 < v[0] < 3.6 and 7.8 < v[1] < 9.5 and 0.03 < v[2] < 2.85]
    if not inbox:
        continue
    zs = [v[2] for v in vs]
    if max(zs) - min(zs) > 0.06:
        continue                     # not a near-flat tread-like face
    c = mw @ p.center
    faces.append((round(min(zs), 3), round(c.x, 2), round(c.y, 2),
                  len(vs), round(n.z, 2), vs))
faces.sort()
print(f"[probe11] {len(faces)} up-facing faces in stair region:")
for z, cx, cy, nv, nzs, vs in faces:
    print(f"[probe11] z={z:5.2f} c=({cx},{cy}) n={nv} nz={nzs}")
    print("[probe11]        verts:", vs)


# the mystery flat object at z~0.49
for ob in bpy.data.objects:
    if ob.type == "MESH" and ob.name.startswith("Pla"):
        bb = [Vector((ob.matrix_world @ Vector(c)).x,
                     (ob.matrix_world @ Vector(c)).y,
                     (ob.matrix_world @ Vector(c)).z)
              for c in ob.bound_box]
        xs = [v.x for v in bb]; ys = [v.y for v in bb]; zs = [v.z for v in bb]
        if min(xs) < 3.6 and max(xs) > 2.8 and min(ys) < 9.6 and max(ys) > 8.8:
            print(f"[probe11] PLA {ob.name}: x[{min(xs):.2f},{max(xs):.2f}] "
                  f"y[{min(ys):.2f},{max(ys):.2f}] z[{min(zs):.2f},{max(zs):.2f}]"
                  f" polys={len(ob.data.polygons)}")
