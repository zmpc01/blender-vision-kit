"""
save_blend.py — save a .blend file (and optionally a high-quality Cycles still)
from a scene defined by a scene script.

Usage:
    blrun.sh --background --python scripts/save_blend.py -- \\
        --scene scene_template \\
        --blend-out output/my_scene/my_scene.blend \\
        --still-frame 12 --still-out output/my_scene/still_12.png

The --scene argument is a module name (without .py) that must be importable
from scripts/ (PYTHONPATH is set by blrun.sh).
"""
import argparse
import importlib
from blender_kit import safe_import_scene
import os
import sys

import bpy
from blender_kit import script_argv


def main():
    p = argparse.ArgumentParser(
        description="Save a Blender scene as .blend + optional high-quality still.")
    p.add_argument("--scene", required=True,
                   help="Scene module name (e.g. scene_template)")
    p.add_argument("--blend-out", required=True,
                   help="Output .blend path")
    p.add_argument("--still-frame", type=int, default=None,
                   help="If set, render this frame as a high-quality Cycles still")
    p.add_argument("--still-out", default=None,
                   help="Output PNG path for the still (default: <blend>_still_<frame>.png)")
    p.add_argument("--still-samples", type=int, default=64)
    p.add_argument("--still-w", type=int, default=960)
    p.add_argument("--still-h", type=int, default=540)
    p.add_argument("--frames", type=int, default=24,
                   help="Animation frame range to set in the .blend (default: 24)")
    p.add_argument("--start", type=int, default=1)
    args = p.parse_args(script_argv())

    print(f"[save_blend] importing scene module: {args.scene}")
    mod = safe_import_scene(args.scene)

    ctx = mod.build_scene()
    if hasattr(mod, "animate"):
        mod.animate(ctx, start_frame=args.start, n_frames=args.frames)

    # Save .blend
    os.makedirs(os.path.dirname(os.path.abspath(args.blend_out)), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=args.blend_out)
    print(f"[save_blend] saved {args.blend_out} "
          f"({os.path.getsize(args.blend_out)} bytes)")

    # Render still
    if args.still_frame is not None:
        out = args.still_out or (
            os.path.splitext(args.blend_out)[0]
            + f"_still_{args.still_frame:04d}.png")
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)

        scene = bpy.context.scene
        scene.frame_set(args.still_frame)
        scene.render.engine = 'CYCLES'
        scene.cycles.device = 'CPU'
        scene.cycles.samples = args.still_samples
        scene.cycles.use_denoising = True
        scene.render.resolution_x = args.still_w
        scene.render.resolution_y = args.still_h
        scene.render.filepath = out
        bpy.ops.render.render(write_still=True)
        print(f"[save_blend] still -> {out} ({os.path.getsize(out)} bytes)")


if __name__ == "__main__":
    main()
