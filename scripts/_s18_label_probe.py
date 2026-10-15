"""_s18_label_probe.py — numeric ground truth for the label-position
anomaly the principal's eye flagged in the s18 eyecert top panel.

Rebuilds the annotation layer exactly as look.py does, then prints for
each label: its world location, its target's bbox top-center, and the
projection into the TOP camera's pixel space. If the label's projected
pixel is NOT where the glyph visually is, the eye finding is real.
"""
import bpy
import sys
from mathutils import Vector

bpy.ops.wm.open_mainfile(filepath="output/s18_eyecert/eyecert.blend")
scene = bpy.context.scene

import annotate
meshes = [o for o in scene.objects if o.type == 'MESH'
          and not o.name.startswith(annotate.ANNOT_PREFIX)]


def groundlike(o):
    return o.dimensions.z <= 0.05 and (o.dimensions.x * o.dimensions.y) >= 6.0

ranked = sorted((o for o in meshes if not groundlike(o)),
                key=lambda o: -o.dimensions.length)
label_ids = [(o.name, i + 1) for i, o in enumerate(ranked[:8])]
layer = annotate.build_annotation_layer(flagged_ids=["FloatBox", "MarkerCone", "Ground"],
                                        label_ids=label_ids, grid=True, gnomon=True)
bpy.context.view_layer.update()

# the TOP camera: reproduce viewport_capture's VIEW_ANGLES top angle
import viewport_capture as vc
print("[probe] VIEW_ANGLES:", {k: v[:3] for k, v in vc.VIEW_ANGLES.items()})

# add the top temp camera the way render_angle does
loc = vc.VIEW_ANGLES["top"][:3]
cam_data = bpy.data.cameras.new("probe_top_cam")
cam = bpy.data.objects.new("probe_top_cam", cam_data)
bpy.context.collection.objects.link(cam)
target = Vector((0, 0, 0))
d = target - Vector(loc)
cam.location = loc
cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
scene.camera = cam
scene.render.resolution_x = 640
scene.render.resolution_y = 480
scene.render.resolution_percentage = 100

from bpy_extras.object_utils import world_to_camera_view
print("[probe] label world positions vs top-cam projection (640x480):")
for txt in layer["labels"]:
    tname = txt.get("kit_target", "?")
    tgt = scene.objects.get(tname)
    rv = world_to_camera_view(scene, cam, txt.location)
    px = (rv.x * 640, (1.0 - rv.y) * 480)
    # where refresh_labels would put it
    corners = [tgt.matrix_world @ type(tgt.location)(cc) for cc in tgt.bound_box]
    cx = sum(c.x for c in corners) / 8.0
    cy = sum(c.y for c in corners) / 8.0
    top = max(c.z for c in corners)
    print(f"  {tname}: txt@({txt.location.x:.2f},{txt.location.y:.2f},"
          f"{txt.location.z:.2f}) target-center=({cx:.2f},{cy:.2f}) "
      f"top={top:.2f} -> px=({px[0]:.0f},{px[1]:.0f})")

# and render the top panel at full res for the eye to compare
scene.render.filepath = "output/s18_eyecert/probe_top.png"
bpy.ops.render.render(write_still=True)
print("[probe] wrote output/s18_eyecert/probe_top.png")
