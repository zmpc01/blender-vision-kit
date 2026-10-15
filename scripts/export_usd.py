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
from blender_kit import (clear_scene, filter_rna_kwargs, iter_all_fcurves,
                         script_argv)


def _carrier_stage_keys(usd_path: str) -> list:
    """D11 (session-18): top-level keys of the STAGE previz:entity payload
    in the WRITTEN usd — the post-export proof the carrier landed.

    Prefers pxr (format-agnostic: .usda/.usd/.usdc/.usdz), guarded by
    try/import (pxr needs bpy.utils.expose_bundled_modules() on 4.x+ and
    may be absent entirely); falls back to
    export_previz_package._usd_customdata_keys (the .usda text scanner —
    lives there, not in previz_usd_hook) when pxr is unavailable.
    Returns [] when neither can read the payload — the caller fails
    closed on empty.
    """
    try:
        try:
            bpy.utils.expose_bundled_modules()
        except Exception:
            pass  # older Blender: pxr is already importable
        from pxr import Usd
        stage = Usd.Stage.Open(usd_path)
        if stage is not None:
            root = stage.GetPrimAtPath("/root")
            if not root or not root.IsValid():
                dp = stage.GetDefaultPrim()
                root = dp if (dp and dp.IsValid()) else None
            if root is not None:
                data = root.GetCustomData() or {}
                ent = data.get("previz:entity")
                if ent is None and isinstance(data.get("previz"), dict):
                    ent = data["previz"].get("entity")
                if isinstance(ent, dict) and ent:
                    return sorted(str(k) for k in ent.keys())
    except Exception as e:
        print(f"[export_usd] NOTE: pxr carrier read unavailable ({e})")
    # Text-scan fallback (.usda ASCII only).
    try:
        sys_path = os.path.dirname(os.path.abspath(__file__))
        if sys_path not in sys.path:
            sys.path.insert(0, sys_path)
        from export_previz_package import _usd_customdata_keys
        return _usd_customdata_keys(usd_path)
    except Exception as e:
        print(f"[export_usd] NOTE: text carrier read unavailable ({e})")
        return []


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
                if args.export_animation:
                    # D2 (session-18): an "animated" export whose animate()
                    # died used to ship a STATIC USD with exit 0 — the NOTE
                    # swallowed the failure and the exporter still ran with
                    # export_animation=True (the exact session-21 class the
                    # comment above documents). Fail closed when the file
                    # is labelled animated.
                    raise RuntimeError(
                        "[export_usd] FAIL: animate() raised on an "
                        f"--export-animation run ({e}) — refusing to ship "
                        "a static file labelled animated") from e
                print(f"[export_usd] NOTE: animate() failed (non-fatal "
                      f"for a static export): {e}")

    if args.export_animation:
        # D2 belt-and-braces: a clean animate() return is not proof of
        # keys. Verify at least one action in the file actually carries
        # fcurves before the exporter is allowed to label the file
        # animated (covers the --load-blend path too).
        n_animated = 0
        for act in bpy.data.actions:
            try:
                if any(True for _ in iter_all_fcurves(act)):
                    n_animated += 1
            except Exception:
                continue
        if n_animated == 0:
            raise RuntimeError(
                "[export_usd] FAIL: --export-animation is set but NO "
                "action in the file carries fcurves — refusing to export "
                "a static scene as animated (D2: the old NOTE-swallow "
                "shipped static USDs with exit 0)")

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
        #
        # session-16: kwargs are RNA-FILTERED at runtime. The battery
        # caught the drift class on 5.2.2 (export_textures unrecognized —
        # the 4.5-calibrated set is not stable across Blender versions;
        # the same unexercised-lane class as the R4 exporter NameError).
        # The filter keeps exactly the kwargs the RUNNING Blender's RNA
        # declares and NOTEs the drops — version-proof by construction
        # (the _safe_set philosophy, applied to operator kwargs).
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

        # F2C-2 (session-17): one SHARED filter for every usd_export call
        # site (this script, export_previz_package --usd-sidecar,
        # blender_kit.export_usd). The old inline filter's TypeError
        # fallback silently dropped ~20 export settings; the shared filter
        # drops only what this Blender's RNA lacks, with a NOTE.
        usd_kwargs = filter_rna_kwargs(
            "usd_export", usd_kwargs, tag="export_usd")
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

        # D11 (session-18): register() swallows a failed hook install and
        # on_export is WARN-and-continue — a carrier-less USD used to ship
        # exit 0. Verify the stage payload actually landed in the WRITTEN
        # file (the decoder is the oracle) before declaring success.
        carrier_keys = _carrier_stage_keys(out_path)
        if not carrier_keys:
            raise RuntimeError(
                "[export_usd] FAIL: previz:entity stage payload did NOT "
                f"land in {out_path} (0 carrier keys — register() swallows "
                "install failures and on_export is WARN-and-continue; see "
                "the [previz_usd_hook] lines above). Stage payload "
                "broken — refusing to ship.")
        print(f"[export_usd] carrier verified: previz:entity stage keys "
              f"{carrier_keys}")
    finally:
        previz_usd_hook.unregister()

    print(f"[export_usd] done: {out_path}")


if __name__ == "__main__":
    main()
