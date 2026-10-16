import bpy, sys, os, math
sys.path.insert(0, '/home/z/repos/blender-vision-kit/scripts')
os.environ.setdefault('RH_CANVAS_LIB', '/home/z/rh_fixture_lib')
import rh_canvas, placement_lib as pl

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, 0))
ground = bpy.context.active_object
bpy.ops.object.light_add(type='SUN', location=(4, -6, 8))
bpy.ops.mesh.primitive_cube_add(size=1, location=(6, 3, 0.5))
pl2 = bpy.context.active_object
bpy.ops.mesh.primitive_cube_add(size=1, location=(-3, 4, 0.25))
bench = bpy.context.active_object
bench.scale = (1.6, 0.5, 0.5)
bpy.context.view_layer.update()

arm, rep = rh_canvas.import_clip("9005", name="Actor_Sit")
arm.rotation_euler.rotate_axis('Z', math.radians(180.0))
bpy.context.view_layer.update()
print('PROBE1 obj loc:', [round(v,3) for v in arm.location], 'frame', bpy.context.scene.frame_current)
pl.move_to(arm, (-3, 4, 0.0), reference='bottom-center', override='keyframe')
bpy.context.view_layer.update()
print('PROBE2 loc after move:', [round(v,3) for v in arm.matrix_world.translation])
mn, mx = pl._aabb(arm)
print('PROBE2 aabb:', [round(v,3) for v in mn], [round(v,3) for v in mx])
pts = pl.surface_samples(arm, mode='bottom')
print('PROBE3 bottom pts:', len(pts), 'z range', round(min(p.z for p in pts),3), round(max(p.z for p in pts),3))
print('PROBE3 xy sample:', [(round(p.x,2), round(p.y,2)) for p in pts[:6]])
try:
    rep = pl.place_on(arm, bench, footprint='grid', override='keyframe')
    print('PROBE4 place_on OK:', {k: rep[k] for k in ('landed_semantic','applied_translation_m') if k in rep})
    mn, mx = pl._aabb(arm)
    print('PROBE4 aabb after:', [round(v,3) for v in mn], [round(v,3) for v in mx])
except Exception as e:
    print('PROBE4 place_on FAILED:', e)
    # raycast diagnostic
    dg = bpy.context.evaluated_depsgraph_get()
    for p in pts[:5]:
        hit, loc, n, idx, obj, mat = bpy.context.scene.ray_cast(dg, p + __import__('mathutils').Vector((0,0,2)), __import__('mathutils').Vector((0,0,-1)))
        print('  ray from', (round(p.x,2), round(p.y,2), round(p.z,2)), '->', obj.name if obj else None, round(loc.z,3) if hit else None)
bpy.ops.wm.quit_blender()
