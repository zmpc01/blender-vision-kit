"""r6_survey.py — R6: aimed interior survey shots for region identification.

The loft is a CLOSED 20m interior; the kit's 5m angle presets land inside
walls. This renders N wide-lens workbench shots from defined camera
positions at targets inside each zone (lower living / kitchen / upper
bedroom). Pure look — mutates nothing that persists.

Run:  ./scripts/blrun.sh --background --python scripts/r6_survey.py
"""
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
    # name, camera_loc, target
    ("s1_entry_downlength", (0.2, -1.5, 1.8), (0.2, 7.0, 1.0)),
    ("s2_lower_mid",        (2.8, 10.0, 1.8), (-1.0, 7.0, 1.0)),
    ("s3_lower_far_back",   (0.2, 11.5, 1.8), (0.2, 4.0, 1.2)),
    ("s4_upper_bedroom",    (2.2, 16.2, 4.4), (0.0, 12.5, 3.2)),
    ("s5_upper_from_stair", (0.2, 12.0, 4.0), (-2.0, 15.5, 3.2)),
]

bpy.ops.wm.open_mainfile(filepath=SRC)
scene = bpy.context.scene
os.makedirs(OUT, exist_ok=True)
for name, loc, tgt in SHOTS:
    p = os.path.join(OUT, f"{name}.png")
    vc.render_angle("custom", p, engine="workbench", samples=1,
                    width=960, height=560, target=tgt, lens=20,
                    custom_location=loc, exposure=1.0)
    print(f"[r6-survey] {name}: cam={loc} target={tgt} -> {p}", flush=True)
print(f"[r6-survey] done -> {OUT}")
