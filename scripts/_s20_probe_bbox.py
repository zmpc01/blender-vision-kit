import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_cube_add(size=2)  # -1..1
o = bpy.context.active_object
print('CORNERS bound_box order:')
for i, c in enumerate(o.bound_box):
    print(f'  [{i}] ({c[0]:+.0f},{c[1]:+.0f},{c[2]:+.0f})')
print('LAW: i&1 -> +z? i&2 -> +y? i&4 -> +x? (blenlib BKE_boundbox_init_from_minmax bit-flag order)')
bpy.ops.wm.quit_blender()
