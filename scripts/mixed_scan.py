#!/usr/bin/env python3
"""mixed_scan.py — scan the FULL built scene for channels with MIXED
interpolation (the glTF bake trigger; the export OOM root-cause hunt).
Reports action name + channel path for every offender."""
import os
import sys


def rss_mb():
    with open("/proc/self/status") as f:
        for line in f:
            if line.startswith("VmRSS"):
                return int(line.split()[1]) / 1024.0
    return -1.0


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blender_kit                                      # noqa: E402
import scene_night_market as SNM                        # noqa: E402

FILM = os.environ.get("MIXED_FILM", "scene_night_market")
print(f"[mixed] start rss={rss_mb():.0f}MB", flush=True)
ctx = SNM.build_scene()
SNM.animate(ctx, with_crowd=True)
print(f"[mixed] after animate rss={rss_mb():.0f}MB — scanning", flush=True)

import bpy                                              # noqa: E402
n_mixed = 0
for act in bpy.data.actions:
    try:
        fcs = list(blender_kit.iter_fcurves(act))
    except Exception:
        continue
    for fc in fcs:
        modes = {kp.interpolation for kp in fc.keyframe_points}
        if len(modes) > 1:
            n_mixed += 1
            if n_mixed <= 12:
                print(f"[mixed] {act.name}: {fc.data_path}"
                      f"[{fc.array_index}] {sorted(modes)}", flush=True)
print(f"[mixed] TOTAL mixed channels: {n_mixed}", flush=True)

# also the OBJECT-level animation_data (anchors' ad carry the bake2 keys)
for ob in bpy.data.objects:
    ad = getattr(ob, "animation_data", None)
    if not ad or not ad.action:
        continue
    for fc in blender_kit.iter_fcurves(ad.action):
        modes = {kp.interpolation for kp in fc.keyframe_points}
        if len(modes) > 1:
            n_mixed += 1
            if n_mixed <= 24:
                print(f"[mixed-obj] {ob.name} ({ad.action.name}): "
                      f"{fc.data_path}[{fc.array_index}] {sorted(modes)}",
                      flush=True)
print(f"[mixed] scan done rss={rss_mb():.0f}MB", flush=True)
