"""r7_probe4.py — dump the stairs object's 14 faces (world space)."""
import bpy

ROOT = "/home/z/vision-work"
bpy.ops.wm.open_mainfile(filepath=f"{ROOT}/output/r7/loft_nav.blend")

st = bpy.data.objects["stairs"]
mw = st.matrix_world
print(f"[probe4] {len(st.data.polygons)} faces:")
for i, p in enumerate(st.data.polygons):
    vs = [tuple(round(v, 2) for v in (mw @ st.data.vertices[vi].co))
          for vi in p.vertices]
    n = (mw.to_3x3().inverted().transposed() @ p.normal).normalized()
    ctr = mw @ p.center
    print(f"[probe4] f{i}: center=({ctr.x:.2f},{ctr.y:.2f},{ctr.z:.2f}) "
          f"normal=({n.x:.2f},{n.y:.2f},{n.z:.2f})\n          verts={vs}")
