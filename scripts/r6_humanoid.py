"""r6_humanoid.py — R6 compose: rigged UAL actors on the labeled level.

Places 2 rigged Quaternius UAL mannequins (the kit's vendored hero lane)
into the labeled loft:
  Driver  — living-zone floor (y 4.2, on the rug edge), idle, facing +y
            (toward the kitchen), then a short treadmill walk toward it
  Girl    — mezzanine floor (y 12.6, z 2.91), idle, facing the void (-y)

The UAL wrapper contract: yaw 0 = faces +Y; feet-origin at wrapper z 0.
Level labels are NOT needed to stand them (z is known from the manifest:
floor top 0.0, mezzanine top 2.91) — that IS the handoff protocol working.

Run:  ./scripts/blrun.sh --background --python scripts/r6_humanoid.py
Pre:  output/r6/loft_props.blend (props placed)
Post: output/r6/loft_compose.blend
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import bpy  # noqa: E402
import assets_ual_actors as UA  # noqa: E402

OUT = os.path.join(os.path.dirname(_HERE), "output", "r6")
SRC = os.path.join(OUT, "loft_props.blend")
DST = os.path.join(OUT, "loft_compose.blend")


def pick_action(pool, *tokens):
    """Find an action whose original name matches any token (ci)."""
    for name in pool:
        low = name.lower()
        if any(t in low for t in tokens):
            return name, pool[name]
    return None, None


def stand(actor, loc, yaw_deg=0.0, act=None):
    root = actor["root"]
    root.location = loc
    root.rotation_euler = (0.0, 0.0, __import__("math").radians(yaw_deg))
    if act is not None:
        arm = actor["armature"]
        if arm.animation_data is None:
            arm.animation_data_create()
        arm.animation_data.action = act
        print(f"[r6-human] {root.name}: action={act.name} "
              f"frames {act.frame_range[0]:.0f}..{act.frame_range[1]:.0f} "
              f"at {[round(v, 2) for v in loc]}")


def main():
    bpy.ops.wm.open_mainfile(filepath=SRC)
    scene = bpy.context.scene

    driver = UA._import_actor("Driver", UA.ACTOR_SCALE)
    girl = UA._import_actor("Girl", UA.ACTOR_SCALE)

    d_idle_name, d_idle = pick_action(driver["actions"], "idle")
    g_idle_name, g_idle = pick_action(girl["actions"], "idle")
    print(f"[r6-human] idle actions: Driver={d_idle_name} Girl={g_idle_name}")

    stand(driver, (-1.2, 4.2, 0.0), 0.0, d_idle)
    stand(girl, (-1.5, 12.6, 2.91), 180.0, g_idle)

    # treadmill walk demo: Driver walks in place while the wrapper
    # translates +y 1.8m across the walk clip (kit treadmill technique)
    walk_name, walk = pick_action(driver["actions"], "walk")
    if walk is not None:
        arm = driver["armature"]
        arm.animation_data.action = walk
        f0, f1 = int(walk.frame_range[0]), int(walk.frame_range[1])
        scene.frame_start, scene.frame_end = f0, f0 + (f1 - f0)
        root = driver["root"]
        root.location = (-0.8, 5.4, 0.0)
        root.keyframe_insert("location", frame=f0)
        root.location = (-0.8, 7.2, 0.0)
        root.keyframe_insert("location", frame=f0 + (f1 - f0))
        print(f"[r6-human] walk: {walk_name} frames {f0}..{f1}, "
              f"wrapper -0.8,5.4 -> -0.8,7.2")
    scene.frame_set(scene.frame_start)

    bpy.ops.wm.save_as_mainfile(filepath=DST, compress=True)
    print(f"[r6-human] saved {DST}")


main()
