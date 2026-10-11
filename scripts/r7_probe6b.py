"""r7_probe6b.py — lite copy of cut_arch, then side rays + renders."""
import os
import sys

sys.path.insert(0, "/home/z/vision-work/scripts")
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402
import viewport_capture as vc  # noqa: E402

ROOT = "/home/z/vision-work"
LITE = f"{ROOT}/output/r6/loft_cut_arch_lite.blend"

if not os.path.exists(LITE):
    bpy.ops.wm.open_mainfile(filepath=f"{ROOT}/output/r6/loft_cut_arch.blend")
    for img in list(bpy.data.images):
        if img.name not in ("Render Result", "Viewer Node"):
            bpy.data.images.remove(img)
    bpy.data.orphans_purge(do_recursive=True)
    bpy.ops.wm.save_as_mainfile(filepath=LITE, compress=True)
    print(f"[probe6b] lite saved ({os.path.getsize(LITE) >> 20} MB)")

bpy.ops.wm.open_mainfile(filepath=LITE)
dg = bpy.context.evaluated_depsgraph_get()

OUT = f"{ROOT}/output/r7/look_stairwell"
os.makedirs(OUT, exist_ok=True)
SHOTS = [
    ("side_west", (2.2, 7.9, 1.55), (3.3, 7.9, 1.45)),
    ("over_top", (3.0, 9.6, 3.6), (3.4, 7.6, 0.8)),
    ("side_east_lite", (3.55, 7.9, 1.55), (2.95, 7.9, 1.45)),
]
for name, loc, tgt in SHOTS:
    p = os.path.join(OUT, f"{name}.png")
    if not os.path.exists(p):
        vc.render_angle("custom", p, engine="workbench", samples=1,
                        width=960, height=640, target=tgt, lens=28,
                        custom_location=loc, exposure=1.0)
        print(f"[probe6b] rendered {p}", flush=True)
print("[probe6b] done")
