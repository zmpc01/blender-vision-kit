"""
export_usd.py — export a scene defined by a scene script as a USD file,
with previz:entity customData + previz:identityColor custom attr on every
wrapper prim (per issue #1).

Usage:
    blrun.sh --background --python scripts/export_usd.py -- \\
        --scene scene_template \\
        --output output/my_scene/my_scene.usda

    # Export the saved .blend instead of building from a scene module
    blrun.sh --background --python scripts/export_usd.py -- \\
        --load-blend path/to/scene.blend \\
        --output output/my_scene/scene.usda

The --scene argument is a module name (without .py) that must be importable
from scripts/ (PYTHONPATH is set by blrun.sh). The module must expose
build_scene() and animate() functions following the scene_template.py
pattern. If the module is importable, the USD hook reads its story-level
constants (SHOTS_V3, BOARD, _V3_SEG, etc.) and embeds them in the
previz:entity customData on /root.

For round-trip (Blender → WebPreviz), the .usda file (or .usd binary, or
.usdz archive) is consumable by the webpreviz USD↔scene.json converter.

USD-REVIEW-1 F26 fix: kwargs verified against Blender 4.5.13
WM_OT_usd_export RNA (via get_rna_type().properties).
"""
import argparse
import importlib
import os
import sys

import bpy
from blender_kit import script_argv, clear_scene


def main():
    p = argparse.ArgumentParser(
        description="Export a Blender scene to USD with previz:entity carrier.")
    src_group = p.add_mutually_exclusive_group(required=True)
    src_group.add_argument("--scene",
                           help="Scene module name (e.g. scene_template). "
                                "Must be importable from scripts/. "
                                "The module's story-level constants "
                                "(SHOTS_V3, BOARD, etc.) are embedded in "
                                "previz:entity customData.")
    src_group.add_argument("--load-blend",
                           help="Load this .blend file and export its state "
                                "(story-level customData will be empty "
                                "without --scene-module)")
    p.add_argument("--output", required=True,
                   help="Output USD path (.usda ASCII, .usd binary, .usdz archive)")
    p.add_argument("--frames", type=int, default=24,
                   help="Animation frame range to export (default: 24)")
    p.add_argument("--start", type=int, default=1,
                   help="Start frame (default: 1)")
    p.add_argument("--export-animation", action="store_true",
                   help="Export animation (default: False — static at frame 1)")
    p.add_argument("--scene-module",
                   help="Override the scene module name for previz:entity "
                        "story-data collection (defaults to --scene value). "
                        "Use with --load-blend to specify the scene module "
                        "the .blend was built from.")
    p.add_argument("--selected-only", action="store_true",
                   help="Export only selected objects (default: all)")
    p.add_argument("--visible-only", action="store_true",
                   help="Export only visible objects (default: all)")
    p.add_argument("--generate-preview", action="store_true",
                   help="Generate USD preview surface materials (slower)")
    args = p.parse_args(script_argv())

    # Determine scene module name (for previz:entity story-data collection)
    scene_module_name = args.scene_module or args.scene

    # Load or build the scene
    if args.load_blend:
        print(f"[export_usd] loading blend: {args.load_blend}")
        bpy.ops.wm.open_mainfile(filepath=args.load_blend)
    else:
        print(f"[export_usd] importing scene module: {args.scene}")
        mod = importlib.import_module(args.scene)
        clear_scene()
        ctx = mod.build_scene()
        # Session-21 law: animate() must run for BOTH static and animated
        # exports. The old guard (`and not args.export_animation`) was
        # INVERTED — passing --export-animation skipped animate() entirely,
        # so the "animated" USD shipped a static scene (0 timeSamples).
        # A static export still needs animate() too: it keys the frame
        # range + markers the hook reads for the timeline block.
        if hasattr(mod, "animate"):
            try:
                mod.animate(ctx, start_frame=args.start, n_frames=args.frames)
            except Exception as e:
                print(f"[export_usd] NOTE: animate() failed (non-fatal): {e}")

    # Set the frame to start (or frame 1) for the static export
    scene = bpy.context.scene
    scene.frame_set(args.start)
    bpy.context.view_layer.update()

    # Ensure output dir exists
    out_path = os.path.abspath(args.output)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    # Determine the USD format from extension
    ext = os.path.splitext(out_path)[1].lower()
    if ext not in (".usd", ".usda", ".usdc", ".usdz"):
        # Default to .usda (text — easier to inspect)
        new_path = out_path + ".usda"
        print(f"[export_usd] NOTE: '{ext}' not a USD extension; "
              f"appending .usda → {new_path}")
        out_path = new_path
        ext = ".usda"

    # Register the previz USD hook (fires during bpy.ops.wm.usd_export)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import previz_usd_hook
    previz_usd_hook.register(scene_module_name=scene_module_name)

    try:
        # Build the USD export kwargs — verified against Blender 4.5.13
        # WM_OT_usd_export RNA (via op.get_rna_type().properties).
        # USD-REVIEW-1 F26 fix: removed bogus kwargs (generate_preview_material,
        # export_curves_as_ribbons, export_material_bindings). Used the
        # actual RNA-confirmed kwargs.
        usd_kwargs = dict(
            filepath=out_path,
            export_animation=args.export_animation,
            export_meshes=True,
            export_lights=True,
            export_cameras=True,
            export_curves=True,
            export_points=True,
            export_volumes=False,
            export_materials=True,
            export_hair=False,
            export_uvmaps=True,
            export_mesh_colors=True,
            export_normals=True,
            export_armatures=True,
            only_deform_bones=False,
            export_shapekeys=True,
            use_instancing=False,
            evaluation_mode='RENDER',
            generate_preview_surface=args.generate_preview,
            generate_materialx_network=args.generate_preview,
            export_textures=True,
            export_custom_properties=True,
            custom_properties_namespace="userProperties",
            author_blender_name=True,
            selected_objects_only=args.selected_only,
            visible_objects_only=args.visible_only,
            triangulate_meshes=False,
        )

        try:
            bpy.ops.wm.usd_export(**usd_kwargs)
        except TypeError as e:
            # Older Blender versions may not have all kwargs; retry with minimum.
            print(f"[export_usd] NOTE: usd_export kwarg error ({e}); retrying with minimum")
            bpy.ops.wm.usd_export(
                filepath=out_path,
                export_animation=args.export_animation,
                export_cameras=True,
                export_lights=True,
            )

        size = os.path.getsize(out_path)
        print(f"[export_usd] USD exported: {out_path} "
              f"({size} bytes, {size/1024:.1f} KB)")
    finally:
        previz_usd_hook.unregister()

    print(f"[export_usd] done: {out_path}")


if __name__ == "__main__":
    main()
