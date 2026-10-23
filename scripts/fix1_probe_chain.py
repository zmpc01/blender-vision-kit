"""fix1_probe_chain.py -- localize the facing-rotation break.

For sampled anchors + heroes: dump the parent chain rotations, the
anchor's keyed rotation_euler.z vs its velocity angle, and each
child mesh/armature local rotation + world forward. Pinpoints which
transform layer injects the error.

Usage:
  TDAWN_HUMANOID=1 CROWD_CACHE_DIR=... ./scripts/blrun.sh --background \
    --factory-startup --python scripts/fix1_probe_chain.py -- scene_terminal_dawn
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import bpy
import mathutils

HERE = Path(bpy.path.abspath(__file__)).parent
sys.path.insert(0, str(HERE))
import blender_kit as _BK  # noqa: E402

FILM = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else \
    "scene_terminal_dawn"

SAMPLES = ["Zed.0001", "Zed.0005", "Zed.0017", "Zed.0086", "Zed.0110",
           "Master.Root", "Runner.Root"]


def _loc_keys(obj):
    ad = obj.animation_data
    if not ad or not ad.action:
        return {}
    out = {}
    for fc in _BK.iter_fcurves(ad.action):
        if fc.data_path != "location":
            continue
        for kp in fc.keyframe_points:
            out.setdefault(int(round(kp.co.x)), {})[fc.array_index] = \
                kp.co.y
    return {f: (d.get(0, 0.0), d.get(1, 0.0), d.get(2, 0.0))
            for f, d in out.items() if len(d) == 3}


def _rot_keys(obj):
    ad = obj.animation_data
    if not ad or not ad.action:
        return {}
    out = {}
    for fc in _BK.iter_fcurves(ad.action):
        if fc.data_path != "rotation_euler":
            continue
        for kp in fc.keyframe_points:
            out.setdefault(int(round(kp.co.x)), {})[fc.array_index] = \
                kp.co.y
    return {f: d.get(2, None) for f, d in out.items() if 2 in d}


def main():
    import importlib
    film = importlib.import_module(FILM)
    ctx = film.build_scene()
    film.animate(ctx, with_crowd=True)
    scene = bpy.context.scene
    bpy.context.view_layer.update()

    for want in SAMPLES:
        ob = bpy.data.objects.get(want)
        if ob is None:
            print(f"\n### {want}: NOT FOUND")
            continue
        keys = _loc_keys(ob)
        rots = _rot_keys(ob)
        print(f"\n### {want}  (type={ob.type}, keys={len(keys)})")
        # parent chain
        chain = []
        p = ob.parent
        while p:
            r = tuple(round(math.degrees(v), 1)
                      for v in p.rotation_euler)
            chain.append(f"{p.name}@{r}")
            p = p.parent
        print(f"  parents: {' <- '.join(chain) or '(none)'}")
        if not keys:
            continue
        fs = sorted(keys)
        for f in (fs[len(fs) // 3], fs[2 * len(fs) // 3]):
            if f + 4 in keys:
                p0, p1 = keys[f], keys[f + 4]
                dt = 4 / 24.0
                vx, vy = (p1[0] - p0[0]) / dt, (p1[1] - p0[1]) / dt
            else:
                continue
            sp = math.hypot(vx, vy)
            if sp < 0.3:
                continue
            vel_ang = math.degrees(math.atan2(vy, vx))
            keyed = rots.get(f)
            own = tuple(round(math.degrees(v), 1)
                       for v in ob.rotation_euler)
            # world forward of the anchor's local +Y
            scene.frame_set(f)
            bpy.context.view_layer.update()
            mw = ob.evaluated_get(
                bpy.context.view_layer.depsgraph).matrix_world
            fwd = (mw.to_3x3() @ mathutils.Vector((0, 1, 0)))
            fwd_ang = math.degrees(math.atan2(fwd.y, fwd.x))
            # children world forwards
            kids = []
            for c in ob.children:
                cw = c.matrix_world
                cf = (cw.to_3x3() @ mathutils.Vector((0, 1, 0)))
                kids.append(f"{c.name}[{c.type}]"
                            f"rot={tuple(round(math.degrees(v)) for v in c.rotation_euler)} "
                            f"fwd={round(math.degrees(math.atan2(cf.y, cf.x)))}")
            print(f"  f{f}: vel_ang={vel_ang:.0f} keyed_rot_z="
                  f"{None if keyed is None else round(math.degrees(keyed))} "
                  f"cur_euler={own} anchor_fwd={fwd_ang:.0f} "
                  f"speed={sp:.2f}")
            for k in kids:
                print(f"      child {k}")
        scene.frame_set(1)

    print("\n[probe] done")


if __name__ == "__main__":
    main()
