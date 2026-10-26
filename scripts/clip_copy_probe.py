#!/usr/bin/env python3
"""clip_copy_probe.py — isolate the idle-vs-walk action copy cost.

Imports the walk (2899) + idle (2781) clips exactly as bind_crowd does
(trims idle to IDLE_TRIM=64), reports keyframe census, then copies each
action 20x and reports the RSS delta per copy."""
import os
import sys


def rss_mb():
    with open("/proc/self/status") as f:
        for line in f:
            if line.startswith("VmRSS"):
                return int(line.split()[1]) / 1024.0
    return -1.0


def census(act, tag):
    import blender_kit
    fcs = list(blender_kit.iter_fcurves(act))
    keys = sum(len(fc.keyframe_points) for fc in fcs)
    mods = sum(len(fc.modifiers) for fc in fcs)
    print(f"[clip] {tag}: fcurves={len(fcs)} keys={keys} mods={mods} "
          f"range={tuple(round(v,1) for v in act.frame_range)} "
          f"rss={rss_mb():.0f}MB", flush=True)


HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import blender_kit                                      # noqa: E402
import humanoid_crowd as HC                             # noqa: E402
import bpy                                              # noqa: E402

CLIPS = os.path.join(os.path.dirname(HERE), "vendor", "rh_clips",
                     "assets", "fbx")
r0 = rss_mb()
print(f"[clip] start rss={r0:.0f}MB", flush=True)

acts = {}
for tag, fn in (("walk", "2899.fbx"), ("idle", "2781.fbx")):
    before, before_ob = set(bpy.data.actions), set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=os.path.join(CLIPS, fn))
    act = [a for a in bpy.data.actions if a not in before][0]
    for ob in [o for o in bpy.data.objects if o not in before_ob]:
        bpy.data.objects.remove(ob, do_unlink=True)
    census(act, tag + " raw")
    acts[tag] = act

HC._trim_action(acts["idle"], HC.IDLE_TRIM)
census(acts["idle"], "idle trimmed")

for tag in ("walk", "idle"):
    base = rss_mb()
    copies = []
    for k in range(20):
        copies.append(acts[tag].copy())
    d = (rss_mb() - base) / 20.0
    print(f"[clip] {tag}: 20 copies -> {d:.2f} MB/copy "
          f"(rss {base:.0f} -> {rss_mb():.0f}MB)", flush=True)
    for c in copies:
        bpy.data.actions.remove(c)
print(f"[clip] after removal rss={rss_mb():.0f}MB (start {r0:.0f})", flush=True)
