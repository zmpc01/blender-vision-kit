"""r6_compose_shots.py — R6: verify compose state visually (3 aimed shots)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
import viewport_capture as vc  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "output", "r6", "compose")
SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "output", "r6", "loft_compose.blend")

SHOTS = [
    ("c1_living_driver", (-0.2, 0.8, 1.75), (0.4, 6.0, 1.1)),
    ("c2_mezzanine_girl", (1.8, 15.6, 4.6), (-1.5, 12.4, 3.6)),
    ("c3_walk_corridor", (0.8, 4.2, 1.5), (-0.8, 7.4, 1.0)),
]

bpy.ops.wm.open_mainfile(filepath=SRC)
scene = bpy.context.scene
os.makedirs(OUT, exist_ok=True)
for name, loc, tgt in SHOTS:
    p = os.path.join(OUT, f"{name}.png")
    vc.render_angle("custom", p, engine="workbench", samples=1,
                    width=960, height=560, target=tgt, lens=24,
                    custom_location=loc, exposure=1.0)
    print(f"[r6-compose] {name}", flush=True)
print("[r6-compose] done")
