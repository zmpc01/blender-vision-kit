"""fix1_probe_scene.py -- in-Blender ground-truth probe for issues 1/2/5.

Builds a film scene (import the module, build_scene + animate WITH
crowd), then measures on the LIVE scene:

  1. FACING: for every crowd anchor + hero root that has location
     keys, the world-space local +Y forward vs the object's own
     velocity (keyed location derivative). Histogram of angle error.
     Ground truth for "everyone moves facing the wrong direction".
  2. ANIMATION: for every rig assembly under the anchors: the bound
     action name + slot + the world-z span of the HIPS-equivalent
     (root bone head) over the timeline -> frozen vs animated.
     Ground truth for "ZERO walk animation".
  3. HEROES: same two measurements for the UAL principals.

Usage (blrun):
  TDAWN_HUMANOID=1 CROWD_CACHE_DIR=/tmp/crowdcache_tdawn \
  ./scripts/blrun.sh --background --factory-startup \
    --python scripts/fix1_probe_scene.py -- scene_terminal_dawn
"""
from __future__ import annotations

import math
import os
import sys
from pathlib import Path

import bpy

HERE = Path(bpy.path.abspath(__file__)).parent
sys.path.insert(0, str(HERE))

FILM = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else \
    "scene_terminal_dawn"


def _loc_keys(obj):
    """frame -> (x, y, z) from location fcurves (linear read)."""
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


def _vel_at(obj, frame, keys):
    fs = sorted(keys)
    if frame in keys:
        i = fs.index(frame)
    else:
        i = min(range(len(fs)), key=lambda j: abs(fs[j] - frame))
    if i + 1 < len(fs):
        f0, f1 = fs[i], fs[i + 1]
        p0, p1 = keys[f0], keys[f1]
        dt = (f1 - f0) / 24.0
        return ((p1[0] - p0[0]) / dt, (p1[1] - p0[1]) / dt)
    if i > 0:
        f0, f1 = fs[i - 1], fs[i]
        p0, p1 = keys[f0], keys[f1]
        dt = (f1 - f0) / 24.0
        return ((p1[0] - p0[0]) / dt, (p1[1] - p0[1]) / dt)
    return (0.0, 0.0)


def _wrap180(a):
    return (a + 180.0) % 360.0 - 180.0


def probe_facing(sample_frames):
    errs, details = [], []
    for ob in bpy.data.objects:
        if not (ob.name.endswith(".Root") or
                ob.name.startswith(("Zed.", "Master.", "Runner.",
                                    "Driver.", "Girl.", "Gunner.",
                                    "StandardBearer."))):
            continue
        if ob.name.startswith("Zed.RB"):
            continue
        keys = _loc_keys(ob)
        if len(keys) < 3:
            continue
        ob_eval = ob.evaluated_get(bpy.context.view_layer.depsgraph)
        for f in sample_frames:
            v = _vel_at(ob, f, keys)
            sp = math.hypot(v[0], v[1])
            if sp < 0.35:
                continue
            bpy.context.scene.frame_set(f)
            bpy.context.view_layer.update()
            mw = ob_eval.matrix_world
            fwd = (mw.to_3x3() @ mathutils.Vector((0.0, 1.0, 0.0)))
            vel_ang = math.degrees(math.atan2(v[1], v[0]))
            fwd_ang = math.degrees(math.atan2(fwd.y, fwd.x))
            err = abs(_wrap180(fwd_ang - vel_ang))
            errs.append(err)
            if err > 60:
                details.append((ob.name, f, round(err), round(sp, 2)))
    return errs, details


def _anchor_of(ob):
    """Walk up to the keyed anchor object (Zed.* or hero root)."""
    p = ob
    for _ in range(6):
        p = p.parent
        if p is None:
            return None
        if p.animation_data and p.animation_data.action:
            return p
    return None


def probe_animation():
    """Per armature: action name, slot, hips world-z span + visible
    facing (armature world +Y vs anchor velocity)."""
    rows = []
    scene = bpy.context.scene
    for ob in bpy.data.objects:
        if ob.type != "ARMATURE":
            continue
        nm = ob.name
        anchor = _anchor_of(ob)
        if anchor is None and not nm.startswith(("Driver.", "Master.",
                                                 "Runner.")):
            continue
        ad = ob.animation_data
        act = ad.action if ad else None
        try:
            _s = ad.action_slot
            slot = (_s.name if hasattr(_s, "name") else
                    (_s.identifier if hasattr(_s, "identifier")
                     else repr(_s))) if _s else None
        except Exception:
            slot = None
        # hips-equivalent: root bone (no parent)
        zmin, zmax = None, None
        root_bones = [b for b in ob.pose.bones if not b.parent]
        if root_bones and act:
            bone = root_bones[0]
            for f in (1, 120, 240, 360, 480, 600, 720, 840, 960, 1080):
                scene.frame_set(f)
                bpy.context.view_layer.update()
                m = ob.matrix_world @ bone.matrix
                z = m.translation.z
                zmin = z if zmin is None else min(zmin, z)
                zmax = z if zmax is None else max(zmax, z)
            scene.frame_set(1)
        # visible facing: armature world +Y vs anchor velocity
        vis_err = None
        if anchor is not None:
            akeys = _loc_keys(anchor)
            fs = sorted(akeys)
            if len(fs) > 4:
                f = fs[len(fs) // 2]
                i = fs.index(f)
                if i + 1 < len(fs):
                    p0, p1 = akeys[fs[i]], akeys[fs[i + 1]]
                    dt = (fs[i + 1] - fs[i]) / 24.0
                    vx, vy = (p1[0] - p0[0]) / dt, (p1[1] - p0[1]) / dt
                    if math.hypot(vx, vy) > 0.35:
                        scene.frame_set(f)
                        bpy.context.view_layer.update()
                        fwy = (ob.matrix_world.to_3x3() @ mathutils.Vector((0, 1, 0)))
                        vis_err = round(abs(_wrap180(
                            math.degrees(math.atan2(fwy.y, fwy.x)) -
                            math.degrees(math.atan2(vy, vx)))))
        rows.append((nm, act.name if act else None, slot,
                     None if zmax is None else round(zmax - zmin, 4),
                     len(root_bones), vis_err, anchor.name if anchor else None))
    return rows


def main():
    import importlib
    film = importlib.import_module(FILM)
    print(f"[probe] building {FILM} ...")
    ctx = film.build_scene()
    print(f"[probe] animate (with crowd) ...")
    film.animate(ctx, with_crowd=True)

    scene = bpy.context.scene
    sample_frames = [80, 200, 320, 440, 560, 680, 800, 920, 1040]
    print("\n===== FACING (world +Y-forward vs own velocity) =====")
    errs, details = probe_facing(sample_frames)
    if errs:
        errs.sort()
        n = len(errs)
        print(f"n={n}  p10={errs[n//10]:.0f}  p50={errs[n//2]:.0f}  "
              f"p90={errs[9*n//10]:.0f} deg")
        b = [0, 10, 30, 60, 90, 150, 180]
        import collections
        hist = collections.Counter(
            next((b[i] for i in range(len(b) - 1)
                  if errs_i < b[i + 1]), 180) for errs_i in errs)
        print("bins:", {f"{b[i]}-{b[i+1]}": hist.get(b[i], 0)
                        for i in range(len(b) - 1)})
        print("worst offenders (name, frame, err, speed):",
              details[:12])
    else:
        print("no keyed movers found")

    print("\n===== ANIMATION (rigs: action/slot/hips-z-span) =====")
    rows = probe_animation()
    frozen = [r for r in rows if r[3] is not None and r[3] < 0.01]
    live = [r for r in rows if r[3] is not None and r[3] >= 0.01]
    noact = [r for r in rows if r[3] is None]
    print(f"total rigs={len(rows)}  animated(zspan>=1cm)={len(live)}  "
          f"FROZEN={len(frozen)}  no-action={len(noact)}")
    import collections
    act_names = collections.Counter(r[1] for r in rows)
    print("action name census:", dict(act_names))
    verrs = sorted(r[4] for r in rows if r[4] is not None)
    if verrs:
        n = len(verrs)
        print(f"VISIBLE rig-facing err (armature +Y vs anchor vel): "
              f"n={n} p50={verrs[n//2]} p90={verrs[9*n//10]}")
        b = [0, 10, 30, 60, 90, 150, 181]
        hist = collections.Counter(
            next((b[i] for i in range(len(b)-1) if v < b[i+1]), 180)
            for v in verrs)
        print("bins:", {f"{b[i]}-{b[i+1]}": hist.get(b[i], 0)
                        for i in range(len(b)-1)})
    print("sample live:", live[:4])
    print("sample frozen:", frozen[:4])
    # slot audit
    noslot = [r for r in rows if r[1] and not r[2]]
    print(f"actions WITHOUT slot pin: {len(noslot)}",
          noslot[:5])


import mathutils  # noqa: E402  (after bpy import path setup)
import blender_kit as _BK  # noqa: E402

if __name__ == "__main__":
    main()
