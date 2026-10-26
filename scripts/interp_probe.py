#!/usr/bin/env python3
"""interp_probe.py — which channels carry MIXED interpolation methods
(the glTF exporter's bake trigger: one channel with BEZIER+LINEAR keys
forces the per-frame sampling bake of EVERY animation — at 129 unique
rigs that bake is the export OOM)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import blender_kit                                      # noqa: E402
import humanoid_crowd as HC                             # noqa: E402
import bpy                                              # noqa: E402

CLIPS = os.path.join(os.path.dirname(HERE), "vendor", "rh_clips",
                     "assets", "fbx")


def mixed_channels(act):
    out = []
    for fc in blender_kit.iter_fcurves(act):
        modes = {kp.interpolation for kp in fc.keyframe_points}
        if len(modes) > 1:
            out.append((fc.data_path.split('"')[1] if '"' in fc.data_path
                        else fc.data_path, fc.array_index, modes))
    return out


acts = {}
for tag, fn in (("walk", "2899.fbx"), ("idle", "2781.fbx")):
    before, before_ob = set(bpy.data.actions), set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=os.path.join(CLIPS, fn))
    act = [a for a in bpy.data.actions if a not in before][0]
    for ob in [o for o in bpy.data.objects if o not in before_ob]:
        bpy.data.objects.remove(ob, do_unlink=True)
    acts[tag] = act
    m = mixed_channels(act)
    print(f"[interp] {tag} RAW: {len(m)} mixed channels "
          f"(of {sum(1 for _ in blender_kit.iter_fcurves(act))})", flush=True)
    for dp, idx, modes in m[:6]:
        print(f"    {dp}[{idx}]: {modes}")

comp = HC._compact_action(acts["idle"], HC.IDLE_TRIM)
m = mixed_channels(comp)
print(f"[interp] idle COMPACT: {len(m)} mixed channels", flush=True)
for dp, idx, modes in m[:6]:
    print(f"    {dp}[{idx}]: {modes}")

w = HC._wrap_action(acts["walk"], "wrapped_test", 0.3, 38, 1, 39)
m = mixed_channels(w)
print(f"[interp] walk WRAPPED: {len(m)} mixed channels", flush=True)
for dp, idx, modes in m[:6]:
    print(f"    {dp}[{idx}]: {modes}")
