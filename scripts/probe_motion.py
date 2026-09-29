"""probe_motion.py — debug the missing trajectories/slider ghosts (M5)."""
import os
import sys

import bpy

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))

from blender_kit import safe_import_scene, clear_scene

mod = safe_import_scene("t6_transient")
clear_scene()
ctx = mod.build_scene()
mod.animate(ctx, start_frame=1, n_frames=24)

import motion_study as ms

objs = [ctx["ball"], ctx["slider"], ctx["glitch"]]
made_traj = ms.build_trajectories(objs, 1, 24, coarse=48)
made_onion = ms.build_onion_skin(objs, [1, 4, 7, 10, 14, 17, 20, 24])
bpy.context.view_layer.update()

print("PROBE traj objects:", len(made_traj))
for o in made_traj[:4]:
    print("  ", o.name, "loc", tuple(round(v, 3) for v in o.location),
          "scale", tuple(round(v, 3) for v in o.scale),
          "mats", [m.name for m in o.data.materials] if o.type == 'MESH' else "-")
print("PROBE onion objects:", len(made_onion))
for o in made_onion:
    nm = o.name
    if "Slider" in nm:
        print("  ", nm, "loc", tuple(round(v, 3) for v in o.matrix_world.translation),
              "hide_render", o.hide_render)
print("PROBE real objs:", [(o.name, o.hide_render) for o in objs])
traj_in_scene = [o.name for o in bpy.context.scene.objects
                 if o.name.startswith("KIT_MOTION_traj")]
print("PROBE traj in scene:", len(traj_in_scene), traj_in_scene[:3])

# BISECT 2: run motion_study.main() in-process with patched argv
# (probe builds above contaminate the scene — rebuild fresh first)
import motion_study as ms2
sys.argv = ["blender", "--", "--scene", "t6_transient", "--start", "1",
            "--end", "24", "--out", "/tmp/motion_bisect"]
# choose variant via env: SKIP_TABLE=1 skips motion_numbers
os.environ.setdefault("SKIP_TABLE", "1")
_orig_numbers = ms2.motion_numbers
if os.environ["SKIP_TABLE"] == "1":
    ms2.motion_numbers = lambda *a, **k: []
ms2.main()
ms2.motion_numbers = _orig_numbers

import numpy as np
import PIL.Image as Image
arr = np.asarray(Image.open("/tmp/motion_bisect/onion_traj.png").convert("RGB"),
                 dtype=np.int16)
h, w, _ = arr.shape
top = arr[:, :w // 2]
r, g, b = top[..., 0], top[..., 1], top[..., 2]
green = int(((g > r + 25) & (g > b + 25)).sum())
red = int(((r > g + 35) & (r > b + 35)).sum())
print(f"PROBE-BISECT green={green} red={red}")


# visibility forensics for every KIT_MOTION object
for o in bpy.context.scene.objects:
    if not o.name.startswith("KIT_MOTION_"):
        continue
    if "Slider" in o.name or "traj" in o.name[:22]:
        cols = [c.name for c in bpy.data.collections if o.name in c.objects]
        print(f"PROBE-VIS {o.name} hide_r={o.hide_render} hide_v={o.hide_viewport} "
              f"parent={o.parent} cols={cols} polys={len(o.data.polygons)}")

# render a top view right here and histogram hues
import viewport_capture as vc

# BISECT: replicate main() exactly — objs order from _pick_objects, hide reals
objs2 = ms._pick_objects(3)
print("PROBE order:", [o.name for o in objs2])
made2 = ms.build_trajectories(objs2, 1, 24, coarse=48) + \
    ms.build_onion_skin(objs2, [1, 4, 7, 10, 14, 17, 20, 24])
bpy.context.view_layer.update()
for o in objs2:
    o.hide_render = True
vc.render_angle("top", "/tmp/probe_top2.png", engine="workbench",
                width=640, height=480)
arr = np.asarray(Image.open("/tmp/probe_top2.png").convert("RGB"), dtype=np.int16)
r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
green = int(((g > r + 30) & (g > b + 30)).sum())
red = int(((r > g + 40) & (r > b + 40)).sum())
print(f"PROBE-PIX2 green={green} red={red} total={arr.shape[0]*arr.shape[1]}")


