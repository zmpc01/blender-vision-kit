"""r7_nav_shots.py — R7 verification: aimed shots + tracking camera.

Static verification shots at route keyframes (sightline-checked against
the real geometry — the R6 wall-blocking lesson), plus a TRACKING camera
(Track-To constraint on Driver.Root, keyed by the constraint per frame)
rendered at 5 timeline positions. The tracking cam is SAVED into the
blend — part of the usable scene state (camera kit on the labeled level).

Run:  ./scripts/blrun.sh --background --python scripts/r7_nav_shots.py
Pre:  output/r7/loft_nav.blend + nav_report.json (frame count)
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402
import viewport_capture as vc  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "output", "r7", "loft_nav.blend")
OUT = os.path.join(ROOT, "output", "r7", "look_nav")
REP = json.load(open(os.path.join(ROOT, "output", "r7", "nav_report.json")))
N_FRAMES = REP["frames"]

bpy.ops.wm.open_mainfile(filepath=SRC)
scene = bpy.context.scene
dg = bpy.context.evaluated_depsgraph_get()


def visible(loc, tgt):
    d = Vector(tgt) - Vector(loc)
    dist = d.length
    hit, l, n, i, obj, m = scene.ray_cast(dg, Vector(loc), d.normalized())
    return (not hit) or (Vector(loc) - l).length >= dist - 0.3


def frame_for_progress(u):
    return max(1, min(N_FRAMES, int(1 + u * (N_FRAMES - 1))))


SHOTS = [
    # (name, cam, target, progress u of the timeline)
    ("n1_approach", (0.2, 4.6, 2.0), (2.9, 8.2, 0.8), 0.20),
    ("n2_climb_low", (3.15, 6.2, 2.1), (2.96, 9.6, 0.8), 0.32),
    ("n3_climb_mid", (1.2, 8.0, 1.9), (2.96, 11.5, 1.7), 0.50),
    ("n4_arrival", (0.5, 15.6, 3.9), (2.96, 14.2, 2.95), 0.88),
    ("n5_walkin_girl", (2.2, 15.8, 3.7), (-1.5, 12.8, 3.4), 0.99),
]
os.makedirs(OUT, exist_ok=True)
for name, loc, tgt, u in SHOTS:
    f = frame_for_progress(u)
    ok = visible(loc, tgt)
    note = "" if ok else " [SIGHTLINE BLOCKED — render anyway]"
    print(f"[r7-shots] {name}: frame {f} visible={ok}{note}", flush=True)
    scene.frame_set(f)
    p = os.path.join(OUT, f"{name}.png")
    vc.render_angle("custom", p, engine="workbench", samples=1,
                    width=960, height=560, target=tgt, lens=26,
                    custom_location=loc, exposure=1.1)

# --- tracking camera (saved into the blend) ---
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
for u in (0.02, 0.25, 0.5, 0.75, 0.99):
    f = frame_for_progress(u)
    scene.frame_set(f)
    p = os.path.join(OUT, f"track_{int(u * 100):02d}.png")
    vc.render_angle("custom", p, engine="workbench", samples=1,
                    width=960, height=560, target=None, lens=30,
                    custom_location=cam.location, exposure=1.1)
    print(f"[r7-shots] track frame {f} rendered", flush=True)

bpy.ops.wm.save_as_mainfile(filepath=SRC, compress=True)
print(f"[r7-shots] tracking cam saved into {SRC}")
