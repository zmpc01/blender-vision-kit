"""r6_survey2.py — R6: second aimed survey (back-lower, upper floor, stairs)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
import viewport_capture as vc  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "output", "r6", "survey")
SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "output", "r6", "loft_look.blend")

SHOTS = [
    ("s6_back_lower",   (0.0, 10.2, 1.7), (0.0, 15.0, 1.1)),
    ("s7_upper_floor",  (0.0, 15.0, 4.3), (0.0, 10.0, 3.4)),
    ("s8_stairs_zone",  (0.6, 5.8, 1.7), (2.9, 8.8, 1.4)),
    ("s9_kitchen_seek", (0.0, 7.2, 1.9), (-1.0, 11.0, 1.0)),
]

bpy.ops.wm.open_mainfile(filepath=SRC)
scene = bpy.context.scene
os.makedirs(OUT, exist_ok=True)
for name, loc, tgt in SHOTS:
    p = os.path.join(OUT, f"{name}.png")
    vc.render_angle("custom", p, engine="workbench", samples=1,
                    width=960, height=560, target=tgt, lens=20,
                    custom_location=loc, exposure=1.0)
    print(f"[r6-survey2] {name}: cam={loc} target={tgt}", flush=True)
print("[r6-survey2] done")
