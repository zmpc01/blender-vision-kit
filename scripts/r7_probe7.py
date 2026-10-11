"""r7_probe7.py — s8-identical vantage + sightline-checked closeups."""
import os
import sys

sys.path.insert(0, "/home/z/vision-work/scripts")
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402
import viewport_capture as vc  # noqa: E402

ROOT = "/home/z/vision-work"
bpy.ops.wm.open_mainfile(filepath=f"{ROOT}/output/r6/loft_cut_arch_lite.blend")
dg = bpy.context.evaluated_depsgraph_get()


def visible(loc, tgt):
    d = Vector(tgt) - Vector(loc)
    dist = d.length
    hit, l, n, i, obj, m = bpy.context.scene.ray_cast(
        dg, Vector(loc), d.normalized())
    # visible if first hit is at/after the target (or nothing solid before)
    return (not hit) or (Vector(loc) - l).length >= dist - 0.25


OUT = f"{ROOT}/output/r7/look_stairwell"
CANDS = [
    (0.6, 5.8, 1.7), (0.9, 6.2, 1.8), (1.2, 6.6, 1.8), (1.5, 7.0, 1.9),
    (0.8, 7.0, 2.2), (1.6, 7.6, 2.4), (2.0, 7.0, 2.0), (2.4, 6.6, 1.8),
    (1.8, 6.0, 2.6), (2.6, 7.4, 2.6),
]
TGT = (3.32, 7.9, 1.5)
good = [c for c in CANDS if visible(c, TGT)]
print(f"[probe7] visible vantages for {TGT}: {good}")

SHOTS = [("s8_ident", (0.6, 5.8, 1.7), (2.9, 8.8, 1.4))]
for i, c in enumerate(good[:3]):
    SHOTS.append((f"close{i}", c, TGT))
for name, loc, tgt in SHOTS:
    p = os.path.join(OUT, f"{name}.png")
    vc.render_angle("custom", p, engine="workbench", samples=1,
                    width=960, height=640, target=tgt, lens=28,
                    custom_location=loc, exposure=1.0)
    print(f"[probe7] rendered {name} from {loc}", flush=True)
