"""r7_cam_persist.py — add both tracking cams to the FULL nav blend."""
import bpy

FULL = "/home/z/vision-work/output/r7/loft_nav.blend"
bpy.ops.wm.open_mainfile(filepath=FULL)
scene = bpy.context.scene
for name, loc in (("NavTrackCam", (0.4, 5.6, 2.4)),
                  ("NavVoidCam", (1.0, 11.0, 4.6))):
    if name in bpy.data.objects:
        continue
    cd = bpy.data.cameras.new(name)
    cd.lens = 30
    cam = bpy.data.objects.new(name, cd)
    cam.location = loc
    scene.collection.objects.link(cam)
    tc = cam.constraints.new(type="TRACK_TO")
    tc.target = bpy.data.objects["Driver.Root"]
    tc.track_axis = "TRACK_NEGATIVE_Z"
    tc.up_axis = "UP_Y"
scene.camera = bpy.data.objects["NavTrackCam"]
scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=FULL, compress=True)
print("[r7-cam] both tracking cams persisted; scene.camera = NavTrackCam")
