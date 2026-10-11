"""r7_probe14.py — wide overviews of the stair quadrant."""
import os, sys
sys.path.insert(0, "/home/z/vision-work/scripts")
import bpy
import viewport_capture as vc

bpy.ops.wm.open_mainfile(filepath="/home/z/vision-work/output/r6/loft_cut_arch_lite.blend")
OUT = "/home/z/vision-work/output/r7/look_stairwell"
os.makedirs(OUT, exist_ok=True)
SHOTS = [
    ("wide_south", (0.2, 4.6, 2.6), (3.2, 8.9, 1.2), 20),
    ("wide_above_void", (0.8, 10.8, 4.2), (3.2, 8.6, 1.0), 20),
    ("wide_east", (3.2, 5.4, 2.4), (3.2, 9.0, 1.3), 24),
]
for name, loc, tgt, lens in SHOTS:
    p = os.path.join(OUT, f"{name}.png")
    vc.render_angle("custom", p, engine="workbench", samples=1,
                    width=960, height=640, target=tgt, lens=lens,
                    custom_location=loc, exposure=1.1)
    print(f"[probe14] rendered {name}", flush=True)
