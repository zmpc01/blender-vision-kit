"""r7_nav_shots2.py — remaining shots from a LITE nav copy (OOM-safe)."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402
import viewport_capture as vc  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FULL = os.path.join(ROOT, "output", "r7", "loft_nav.blend")
LITE = os.path.join(ROOT, "output", "r7", "loft_nav_lite.blend")
OUT = os.path.join(ROOT, "output", "r7", "look_nav")
REP = json.load(open(os.path.join(ROOT, "output", "r7", "nav_report.json")))
N_FRAMES = REP["frames"]


def frame_for_progress(u):
    return max(1, min(N_FRAMES, int(1 + u * (N_FRAMES - 1))))


if not os.path.exists(LITE):
    bpy.ops.wm.open_mainfile(filepath=FULL)
    for img in list(bpy.data.images):
        if img.name not in ("Render Result", "Viewer Node"):
            bpy.data.images.remove(img)
    bpy.data.orphans_purge(do_recursive=True)
    bpy.ops.wm.save_as_mainfile(filepath=LITE, compress=True)
    print(f"[r7-shots2] lite saved ({os.path.getsize(LITE) >> 20} MB)",
          flush=True)

bpy.ops.wm.open_mainfile(filepath=LITE)
scene = bpy.context.scene

# build the tracking cam NOW (on the lite state) so the shots use it
cam_data = bpy.data.cameras.new("NavTrackCam")
cam_data.lens = 30
cam = bpy.data.objects.new("NavTrackCam", cam_data)
cam.location = (0.4, 5.6, 2.4)
scene.collection.objects.link(cam)
tc = cam.constraints.new(type="TRACK_TO")
tc.target = bpy.data.objects["Driver.Root"]
tc.track_axis = "TRACK_NEGATIVE_Z"
tc.up_axis = "UP_Y"
scene.camera = cam

SHOTS = [
    ("n4_arrival", (0.5, 15.6, 3.9), (2.96, 14.2, 2.95), 0.88, 26),
    ("n5_walkin_girl", (2.2, 15.8, 3.7), (-1.5, 12.8, 3.4), 0.99, 26),
]
for name, loc, tgt, u, lens in SHOTS:
    f = frame_for_progress(u)
    scene.frame_set(f)
    p = os.path.join(OUT, f"{name}.png")
    if not os.path.exists(p):
        vc.render_angle("custom", p, engine="workbench", samples=1,
                        width=960, height=560, target=tgt, lens=lens,
                        custom_location=loc, exposure=1.1)
        print(f"[r7-shots2] {name} frame {f} rendered", flush=True)

for u in (0.02, 0.25, 0.5, 0.75, 0.99):
    f = frame_for_progress(u)
    scene.frame_set(f)
    p = os.path.join(OUT, f"track_{int(u * 100):02d}.png")
    if not os.path.exists(p):
        vc.render_angle("custom", p, engine="workbench", samples=1,
                        width=960, height=560, target=None, lens=30,
                        custom_location=cam.location, exposure=1.1)
        print(f"[r7-shots2] track {int(u * 100)}% frame {f} rendered",
              flush=True)
print("[r7-shots2] renders done")
