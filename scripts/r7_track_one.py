"""r7_track_one.py — ONE tracking shot per process (OOM discipline).

Usage: blrun.sh --background --python scripts/r7_track_one.py -- --u 0.25
Renders NavTrackCam's view at progress u of the nav timeline.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
import viewport_capture as vc  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LITE = os.path.join(ROOT, "output", "r7", "loft_nav_lite.blend")
OUT = os.path.join(ROOT, "output", "r7", "look_nav")
REP = json.load(open(os.path.join(ROOT, "output", "r7", "nav_report.json")))
N = REP["frames"]

U = float(os.environ.get("R7_U", "0.02"))

bpy.ops.wm.open_mainfile(filepath=LITE)
scene = bpy.context.scene

cam_data = bpy.data.cameras.new("NavTrackCam")
cam_data.lens = 30
cam = bpy.data.objects.new("NavTrackCam", cam_data)
# two vantages: the south tracking cam loses the actor behind the
# slab band on the upper route (fixed-cam occlusion, seen live at
# u>=0.75) — the void cam above the stair covers the climb + arrival.
CAM_POS = (0.4, 5.6, 2.4) if os.environ.get("R7_CAM", "south") == "south" \
    else (1.0, 11.0, 4.6)
cam.location = CAM_POS
scene.collection.objects.link(cam)
tc = cam.constraints.new(type="TRACK_TO")
tc.target = bpy.data.objects["Driver.Root"]
tc.track_axis = "TRACK_NEGATIVE_Z"
tc.up_axis = "UP_Y"
scene.camera = cam

f = max(1, min(N, int(1 + U * (N - 1))))
scene.frame_set(f)
p = os.path.join(OUT, f"track_{os.environ.get("R7_CAM", "south")}_{int(U * 100):02d}.png")
vc.render_angle("active", p, engine="workbench", samples=1,
                width=960, height=560, lens=30, exposure=1.1)
print(f"[r7-track] u={U} frame {f} -> {p}", flush=True)
