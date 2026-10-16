import bpy, bmesh
from mathutils import Vector
bpy.ops.wm.read_factory_settings(use_empty=True)
bm = bmesh.new()
bmesh.ops.create_cube(bm, size=1.0)
print('CUBE_FACES bmesh create_cube order (world dirs of a unit cube at origin, size=1 => +-0.5):')
for i, f in enumerate(bm.faces):
    c = f.calc_center_median()
    n = f.normal
    print(f'  [{i}] center=({c.x:+.1f},{c.y:+.1f},{c.z:+.1f}) normal=({n.x:+.0f},{n.y:+.0f},{n.z:+.0f}) verts={len(f.verts)}')
bm.free()
bpy.ops.wm.quit_blender()
