import bpy, sys, os
sys.path.insert(0, '/home/z/repos/blender-vision-kit/scripts')
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath='/home/z/rh_fixture_lib/fbx/9001.fbx')
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
mw = arm.matrix_world
print('PROBE obj name:', arm.name)
print('PROBE matrix_world:', [[round(v,4) for v in r] for r in mw])
print('PROBE scale:', [round(c,5) for c in arm.scale])
print('PROBLE rot_euler deg:', [round(__import__('math').degrees(a),2) for a in arm.rotation_euler])
hips = arm.data.bones.get('mixamorig:Hips')
print('PROBE hips head_local:', [round(v,4) for v in hips.head_local])
print('PROBE hips world:', [round(v,4) for v in (mw @ hips.head_local)])
lh = arm.data.bones['mixamorig:LeftHand']; rh = arm.data.bones['mixamorig:RightHand']
print('PROBE LHand world:', [round(v,3) for v in (mw @ lh.head_local)])
print('PROBE RHand world:', [round(v,3) for v in (mw @ rh.head_local)])
ft = [b for b in arm.data.bones if b.name.endswith('Foot')][0]
print('PROBE foot world:', [round(v,4) for v in (mw @ ft.head_local)])
print('PROBE scene unit system:', bpy.context.scene.unit_settings.system, bpy.context.scene.unit_settings.scale_length)
ad = arm.animation_data
print('PROBE action:', ad.action.name if ad and ad.action else None)
if ad and ad.action:
    print('PROBE frames:', [int(v) for v in ad.action.frame_range])
bpy.ops.wm.quit_blender()
