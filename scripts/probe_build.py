"""probe_build.py — bisect scene-build variant (n_frames=24 vs 64)."""
import os
import sys

import bpy
import numpy as np
import PIL.Image as Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from blender_kit import safe_import_scene, clear_scene
import motion_study as ms
import viewport_capture as vc


def hist(path):
    arr = np.asarray(Image.open(path).convert("RGB"), dtype=np.int16)
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    return (int(((g > r + 25) & (g > b + 25)).sum()),
            int(((r > g + 35) & (r > b + 35)).sum()))


def variant(tag, n_frames):
    mod = safe_import_scene("t6_transient")
    clear_scene()
    ctx = mod.build_scene()
    mod.animate(ctx, start_frame=1, n_frames=n_frames)
    objs = [ctx["ball"], ctx["slider"], ctx["glitch"]]
    made = ms.build_trajectories(objs, 1, 24, coarse=48) + \
        ms.build_onion_skin(objs, [1, 4, 7, 10, 14, 17, 20, 24])
    bpy.context.view_layer.update()
    for o in objs:
        o.hide_render = True
    vc.render_angle("top", f"/tmp/pv_{tag}.png", engine="workbench",
                    width=640, height=480)
    g, r = hist(f"/tmp/pv_{tag}.png")
    n_traj = len([o for o in bpy.context.scene.objects
                  if o.name.startswith("KIT_MOTION_traj")])
    print(f"PROBE-VARIANT {tag}: n_frames={n_frames} traj_objs={n_traj} "
          f"green={g} red={r}")
    # cleanup for next variant
    for o in made:
        try:
            bpy.data.objects.remove(o, do_unlink=True)
        except Exception:
            pass


variant("n24", 24)
variant("n64", 64)
