"""r7_probe6.py — side-ray profile + aimed renders of the stairwell."""
import os
import sys

sys.path.insert(0, "/home/z/vision-work/scripts")
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402
import viewport_capture as vc  # noqa: E402

ROOT = "/home/z/vision-work"
bpy.ops.wm.open_mainfile(filepath=f"{ROOT}/output/r6/loft_cut_arch.blend")
dg = bpy.context.evaluated_depsgraph_get()

print("[probe6] horizontal rays from x=3.6 walking -x (stair cross-section):")
for y in [7.6, 7.9, 8.2]:
    for z in [0.3, 0.8, 1.3, 1.8, 2.3, 2.8]:
        hit, loc, nrm, idx, obj, mat = bpy.context.scene.ray_cast(
            dg, Vector((3.6, y, z)), Vector((-1, 0, 0)))
        if hit:
            print(f"[probe6]   y={y} z={z}: hit x={loc.x:.2f} z={loc.z:.2f} "
                  f"'{obj.name}' n=({nrm.x:.2f},{nrm.y:.2f},{nrm.z:.2f})")
        else:
            print(f"[probe6]   y={y} z={z}: MISS (open to +x)")
    print("[probe6]   ---")

OUT = f"{ROOT}/output/r7/look_stairwell"
os.makedirs(OUT, exist_ok=True)
SHOTS = [
    ("side_east", (3.55, 7.9, 1.55), (2.95, 7.9, 1.45)),   # cross-section
    ("side_west", (2.2, 7.9, 1.55), (3.3, 7.9, 1.45)),     # from living side
    ("over_top", (3.0, 9.6, 3.6), (3.4, 7.6, 0.8)),        # from band, down
]
for name, loc, tgt in SHOTS:
    p = os.path.join(OUT, f"{name}.png")
    vc.render_angle("custom", p, engine="workbench", samples=1,
                    width=960, height=640, target=tgt, lens=28,
                    custom_location=loc, exposure=1.0)
    print(f"[probe6] rendered {p}", flush=True)
