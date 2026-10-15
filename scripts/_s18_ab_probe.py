"""_s18_ab_probe.py — does frame_set + workbench render actually change
pixels in one process? Render f1 and f24 back-to-back; diff."""
import bpy
bpy.ops.wm.open_mainfile(filepath="output/s18_eyecert/eyecert.blend")
scene = bpy.context.scene
scene.render.engine = 'BLENDER_WORKBENCH'
scene.render.resolution_x = 320
scene.render.resolution_y = 240
scene.render.resolution_percentage = 100
scene.render.filepath = "output/s18_eyecert/ab_f1.png"
scene.frame_set(1)
bpy.context.view_layer.update()
print("[ab] f1 cone world z:", scene.objects["MarkerCone"].matrix_world.translation.z)
bpy.ops.render.render(write_still=True)
scene.render.filepath = "output/s18_eyecert/ab_f24.png"
scene.frame_set(24)
bpy.context.view_layer.update()
print("[ab] f24 cone world z:", scene.objects["MarkerCone"].matrix_world.translation.z)
print("[ab] f24 anim_data:", scene.objects["MarkerCone"].animation_data,
      "action:", getattr(scene.objects["MarkerCone"].animation_data, "action", "NA"))
bpy.ops.render.render(write_still=True)
print("[ab] done")
