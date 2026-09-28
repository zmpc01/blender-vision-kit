"""
export_gltf.py — export a scene defined by a scene script as a .glb file.

Usage:
    blrun.sh --background --python scripts/export_gltf.py -- \\
        --scene scene_template \\
        --output output/my_scene/my_scene.glb

The --scene argument is a module name (without .py) that must be importable
from scripts/ (PYTHONPATH is set by blrun.sh). The module must expose
build_scene() and animate() functions following the scene_template.py pattern.
"""
import argparse
import importlib
from blender_kit import safe_import_scene
import os
import sys

import bpy
from blender_kit import script_argv, clear_scene, export_gltf


def main():
    p = argparse.ArgumentParser(
        description="Export a Blender scene to .glb for web preview.")
    p.add_argument("--scene", default=None,
                   help="Scene module name (e.g. scene_template). "
                        "Must be importable from scripts/.")
    p.add_argument("--load-blend", default=None,
                   help="Load a .blend instead of building a scene module "
                        "(wave-3: exports patch-built state — the ship arc "
                        "of the load-blend loop)")
    p.add_argument("--output", required=True,
                   help="Output .glb path")
    p.add_argument("--frames", type=int, default=24,
                   help="Animation frame range to export (default: 24)")
    p.add_argument("--start", type=int, default=1,
                   help="Start frame (default: 1)")
    args = p.parse_args(script_argv())

    if not args.scene and not args.load_blend:
        print("[export_gltf] ERROR: --scene or --load-blend required",
              file=sys.stderr)
        sys.exit(1)

    # Validate output early (fail fast)
    from blender_kit import validate_output
    validate_output(args.output)
    if args.frames < 1:
        print(f"[export_gltf] ERROR: --frames must be >= 1, got {args.frames}",
              file=sys.stderr)
        sys.exit(1)

    if args.load_blend:
        import bpy
        print(f"[export_gltf] loading .blend: {args.load_blend}")
        bpy.ops.wm.open_mainfile(filepath=args.load_blend)
    else:
        print(f"[export_gltf] importing scene module: {args.scene}")
        mod = safe_import_scene(args.scene)

        # Build & animate
        ctx = mod.build_scene()
        if hasattr(mod, "animate"):
            mod.animate(ctx, start_frame=args.start, n_frames=args.frames)

    # Export
    out_path = export_gltf(args, out_path=args.output)
    print(f"[export_gltf] done: {out_path}")


if __name__ == "__main__":
    main()
