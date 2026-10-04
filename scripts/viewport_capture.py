"""
viewport_capture.py — fast multi-angle viewport screenshots for visual verification.

The #1 insight from agent-driven 3D research (3D-Agent, DD3M, Scenethesis):
"Sending a viewport screenshot back to the model after each operation was the
single biggest quality improvement." Pure code-gen produces "geometry soup"
after 3-4 steps without visual verification.

This script captures the current scene from multiple angles using Workbench
engine (viewport-quality, ~0.1s/frame, no shader compile cost) or low-sample
EEVEE_NEXT, and optionally stitches them into a single contact sheet for
one-shot VLM analysis.

Usage:
    # Single perspective view from the scene's active camera
    blrun.sh --background --python scripts/viewport_capture.py -- \\
        --output output/check.png

    # 4-angle contact sheet (front/side/top/perspective) for spatial inspection
    blrun.sh --background --python scripts/viewport_capture.py -- \\
        --output output/check_grid.png --angles front,side,top,persp \\
        --grid 2x2

    # 6-angle ring around the scene at 60-degree increments
    blrun.sh --background --python scripts/viewport_capture.py -- \\
        --output output/ring.png --ring 6

    # Use Workbench (fastest, solid shading, no lighting)
    blrun.sh --background --python scripts/viewport_capture.py -- \\
        --output output/check.png --engine workbench

    # Use EEVEE_NEXT at 4 samples (shaded, with lighting)
    blrun.sh --background --python scripts/viewport_capture.py -- \\
        --output output/check.png --engine eevee --samples 4
"""
import argparse
import math
import os
import subprocess
import sys
import tempfile
from typing import List, Tuple

import bpy
from blender_kit import script_argv


# ---------------------------------------------------------------------------
# Standard view angles
# ---------------------------------------------------------------------------

# Each entry: (label, location_offset_from_target, rotation_euler_or_None)
# If rotation is None, we use Track To constraint pointing at target.
# Note: 'top' uses a slight Y offset to avoid gimbal-lock / up-axis ambiguity
# when the camera looks straight down (which would otherwise produce a blank
# or sideways-rotated image).
VIEW_ANGLES = {
    "front":  (0, -5, 2, "Track to origin"),
    "side":   (-5, 0, 2, "Track to origin"),
    "top":    (0.001, -0.5, 5, "Track to origin — slight Y offset to avoid straight-down gimbal lock"),
    "persp":  (4, -4, 3, "Track to origin — standard 3/4 view"),
    "back":   (0, 5, 2, "Track to origin"),
    "right":  (5, 0, 2, "Track to origin"),
}


def _compute_scene_center() -> Tuple[float, float, float]:
    """Compute the bounding-box center of all mesh objects in the scene."""
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    if not meshes:
        return (0.0, 0.0, 0.0)
    xs, ys, zs = [], [], []
    for o in meshes:
        for corner in o.bound_box:
            world = o.matrix_world @ type(o.location)(corner)
            xs.append(world.x); ys.append(world.y); zs.append(world.z)
    return (sum(xs)/len(xs), sum(ys)/len(ys), sum(zs)/len(zs))


def _add_temp_camera(name: str, location: Tuple[float, float, float],
                     target: Tuple[float, float, float], lens: int = 50):
    """Add a temp camera at `location` pointing at `target` via Track To constraint."""
    cam_data = bpy.data.cameras.new(name=f"{name}_data")
    cam_data.lens = lens
    cam = bpy.data.objects.new(name, cam_data)
    bpy.context.collection.objects.link(cam)
    cam.location = location

    # Add an empty at target for Track To
    target_empty = bpy.data.objects.new(f"{name}_target", None)
    bpy.context.collection.objects.link(target_empty)
    target_empty.location = target

    constraint = cam.constraints.new(type='TRACK_TO')
    constraint.target = target_empty
    constraint.track_axis = 'TRACK_NEGATIVE_Z'
    constraint.up_axis = 'UP_Y'

    return cam, target_empty


def _cleanup_temp_camera(cam, target_empty):
    """Remove temp camera + target empty. Safe to call even if already removed."""
    def safe_remove(obj, is_data=False):
        if obj is None:
            return
        try:
            # Accessing .name raises ReferenceError if the RNA struct is gone
            _ = obj.name
        except ReferenceError:
            return
        try:
            if is_data:
                if obj.users == 0:
                    bpy.data.cameras.remove(obj)
            else:
                bpy.data.objects.remove(obj, do_unlink=True)
        except (ReferenceError, Exception):
            pass

    cam_data = None
    try:
        cam_data = cam.data if cam else None
    except ReferenceError:
        cam_data = None

    safe_remove(target_empty)
    safe_remove(cam)
    safe_remove(cam_data, is_data=True)


# ---------------------------------------------------------------------------
# Render one angle
# ---------------------------------------------------------------------------

def render_angle(angle_label: str, out_path: str, *,
                 engine: str = "workbench",
                 samples: int = 1,
                 width: int = 480,
                 height: int = 360,
                 target: Tuple[float, float, float] = (0, 0, 0),
                 lens: int = 50,
                 custom_location: Tuple[float, float, float] = None,
                 light: str = None,
                 color_type: str = None,
                 shadows: bool = None,
                 cavity: bool = None,
                 exposure: float = None) -> str:
    """Render the scene from a single angle. Returns the output path.

    `angle_label` can be one of VIEW_ANGLES keys, OR 'active' to use the
    scene's existing active camera, OR 'custom' (requires custom_location).

    Workbench shading overrides (vision-kit M5 tuning): light/color_type/
    shadows/cavity default to the tuned kit defaults below; `exposure` is a
    view_settings exposure lift in EV stops (None = scene untouched).
    Measured (docs/TUNING_perception_v1.md): workbench STUDIO renders ~98%
    of pixels in the darkest third of the range; +1.0 EV roughly doubles
    usable contrast (stdev 42->54, edge energy 2.3->3.2) without washing
    material colors. look.py passes exposure=1.0 on workbench by default.
    """
    scene = bpy.context.scene

    # Pick / create the camera
    cleanup = None
    if angle_label == "active":
        if scene.camera is None:
            raise RuntimeError("No active camera in scene — use a different --angles value")
        cam = scene.camera
    elif angle_label == "custom":
        if custom_location is None:
            raise RuntimeError("custom angle requires --custom-loc X,Y,Z")
        cam, target_empty = _add_temp_camera(
            "temp_custom_cam", custom_location, target, lens)
        cleanup = lambda: _cleanup_temp_camera(cam, target_empty)
    elif angle_label in VIEW_ANGLES:
        loc = VIEW_ANGLES[angle_label][:3]
        # Translate by target so the view orbits the scene center
        loc = (loc[0] + target[0], loc[1] + target[1], loc[2] + target[2])
        cam, target_empty = _add_temp_camera(
            f"temp_{angle_label}_cam", loc, target, lens)
        cleanup = lambda: _cleanup_temp_camera(cam, target_empty)
    else:
        raise RuntimeError(f"Unknown angle: {angle_label}. "
                           f"Choose from: {list(VIEW_ANGLES.keys())}, 'active', 'custom'")

    # Configure render
    if engine == "workbench":
        scene.render.engine = 'BLENDER_WORKBENCH'
        # Workbench-specific: solid shading with material colors visible.
        # Per session-5 worklog: OBJECT color_type shows flat gray, hiding
        # material-based color coding. Use MATERIAL instead.
        scene.display.shading.light = light or 'STUDIO'
        # MATERIAL shows real material base colors (needed to verify
        # color-coded previz assets); OBJECT only uses obj.color RGBA.
        scene.display.shading.color_type = color_type or 'MATERIAL'
        scene.display.shading.show_shadows = True if shadows is None else shadows
        scene.display.shading.show_cavity = True if cavity is None else cavity
        # Per session-5 worklog: AgX crushes low-chroma colors in previz.
        # Use Standard so authored material colors read true.
        try:
            scene.view_settings.view_transform = 'Standard'
        except AttributeError:
            pass
        if exposure is not None:
            scene.view_settings.exposure = exposure
    elif engine == "eevee":
        from blender_kit import EEVEE_ENGINE_ID
        scene.render.engine = EEVEE_ENGINE_ID
        scene.eevee.taa_render_samples = samples
        if exposure is not None:
            scene.view_settings.exposure = exposure
    elif engine == "cycles":
        scene.render.engine = 'CYCLES'
        scene.cycles.device = 'CPU'
        scene.cycles.samples = samples
        scene.cycles.use_denoising = True
    else:
        raise RuntimeError(f"Unknown engine: {engine}")

    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.filepath = out_path

    # Temporarily swap the scene's active camera
    orig_camera = scene.camera
    scene.camera = cam

    try:
        bpy.ops.render.render(write_still=True)
    finally:
        scene.camera = orig_camera
        if cleanup:
            cleanup()

    if not os.path.exists(out_path):
        raise RuntimeError(f"Render failed silently — no output at {out_path}")
    _warn_if_clipped(out_path, engine)
    return out_path


def _warn_if_clipped(out_path: str, engine: str) -> None:
    """Loudly report blown-out renders (session-16 subject v1: a high-key
    bedroom went full white on 5.2 EEVEE — 5.x EEVEE renders ~5-12% brighter
    than 4.5 on identical scenes, enough to clip high-key scenes). Consumers
    staring at a white frame deserve a diagnosis, not silence."""
    try:
        import numpy as np
        img = bpy.data.images.load(out_path, check_existing=False)
        w, h = img.size
        ch = img.channels
        buf = np.empty(w * h * ch, dtype=np.float32)
        img.pixels.foreach_get(buf)
        bpy.data.images.remove(img)
        frame = buf.reshape(-1, ch)[..., :3]
        clipped = float((frame.min(axis=1) >= 0.98).mean() * 100.0)
        mean = float(frame.mean())
        if clipped > 25.0:
            print(f"[viewport] WARNING: {clipped:.0f}% of pixels are clipped "
                  f"white (mean luma {mean:.2f}) — the render is likely "
                  f"blown out. Known law: 5.x EEVEE renders brighter than "
                  f"4.5 on identical scenes (sky+sun compound it). Fix via "
                  f"the set_exposure patch op (~-0.5 EV on 5.x high-key "
                  f"scenes) or lower sun/light energy ~20%.", flush=True)
    except Exception as e:      # never let a diagnostic break a render
        print(f"[viewport] (clip-check skipped: {e})", flush=True)


def image_readiness(path: str) -> dict:
    """Per-image vision-readiness header (vision-kit D6; wave-1 fixed).

    Shared by look.py's verdict block and apply_patch's render_viewport op
    so EVERY image the kit writes carries its own trustworthiness stats:
    luma mean, clipped/dark percentages, subject coverage (RGB distance
    from corner-estimated background — luma-only missed red-on-gray),
    and BLOWN-OUT / NEAR-BLACK / NEAR-EMPTY flags.
    """
    try:
        from PIL import Image
        import numpy as np
        im = Image.open(path).convert("RGB")
        w, h = im.size
        a = np.asarray(im, dtype=np.float32) / 255.0
        luma = a @ [0.2126, 0.7152, 0.0722]
        clipped = float((luma >= 0.98).mean() * 100.0)
        dark = float((luma <= 0.08).mean() * 100.0)
        corners = (a[2, 2] + a[2, -3] + a[-3, 2] + a[-3, -3]) / 4.0
        subj = float((np.abs(a - corners).sum(axis=2) > 0.25).mean() * 100.0)
        flags = []
        if clipped > 25.0:
            flags.append("BLOWN-OUT")
        if dark > 40.0:
            flags.append("NEAR-BLACK")
        if subj < 1.5:
            flags.append("NEAR-EMPTY")
        return {"path": path, "w": w, "h": h,
                "luma_mean": round(float(luma.mean()), 3),
                "clipped_pct": round(clipped, 1),
                "dark_pct": round(dark, 1),
                "subject_pct": round(subj, 1),
                "flags": flags}
    except Exception as e:  # never let a diagnostic break a render
        return {"path": path, "error": str(e)}


# ---------------------------------------------------------------------------
# Contact sheet stitching
# ---------------------------------------------------------------------------

def stitch_contact_sheet(image_paths: List[str], output_path: str,
                         grid_cols: int = 2, *, label: bool = True) -> str:
    """Stitch multiple PNGs into a single grid image with optional labels.

    Uses Pillow (already installed via z-ai SDK deps). Falls back to
    ImageMagick `montage` if Pillow is missing.
    """
    if not image_paths:
        raise RuntimeError("No images to stitch")

    try:
        from PIL import Image, ImageDraw, ImageFont
        imgs = [Image.open(p) for p in image_paths]
        w, h = imgs[0].size
        # Normalize all to first image's size
        imgs = [im.resize((w, h)) for im in imgs]

        rows = (len(imgs) + grid_cols - 1) // grid_cols
        # Add space for labels at top of each cell
        label_h = 24 if label else 0
        sheet = Image.new('RGB',
                          (grid_cols * w, rows * (h + label_h)),
                          (20, 20, 24))
        draw = ImageDraw.Draw(sheet)
        try:
            font = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
        except Exception:
            font = ImageFont.load_default()

        for i, (im, path) in enumerate(zip(imgs, image_paths)):
            col = i % grid_cols
            row = i // grid_cols
            x = col * w
            y = row * (h + label_h) + label_h
            sheet.paste(im, (x, y))
            if label:
                # Label is the angle name from the path
                lbl = os.path.basename(path).replace(".png", "").replace("_", " ")
                # Black background for label
                draw.rectangle([(x, y - label_h), (x + w, y)], fill=(20, 20, 24))
                draw.text((x + 6, y - label_h + 4), lbl, fill=(230, 230, 230), font=font)

        sheet.save(output_path)
        return output_path
    except ImportError:
        # Fall back to ImageMagick montage
        cmd = ["montage"] + image_paths + [
            "-tile", f"{grid_cols}x",
            "-geometry", "+2+2",
            "-label", "%f",
            output_path]
        subprocess.run(cmd, check=True)
        return output_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _normalize_engine_arg(v):
    """Argparse type: bridge raw Blender enum spellings to dispatch names."""
    from blender_kit import normalize_engine
    return normalize_engine(v)


def main():
    p = argparse.ArgumentParser(
        description="Capture multi-angle viewport screenshots for visual verification.")
    p.add_argument("--scene", default=None,
                   help="Scene module name to build before capturing (e.g. scene_template). "
                        "If omitted, captures the currently-loaded scene.")
    p.add_argument("--frames", type=int, default=24,
                   help="Animation frames to pass to scene's animate() (default: 24)")
    p.add_argument("--output", required=True,
                   help="Output PNG path. For multi-angle, this is the contact sheet path.")
    p.add_argument("--angles", default="persp",
                   help="Comma-separated list of angles. Options: "
                        "front,side,top,persp,back,right,active,custom. "
                        "Or 'ring:N' for N cameras around the scene. "
                        "Default: persp")
    p.add_argument("--ring", type=int, default=None,
                   help="Generate N cameras in a ring around the scene (alternative to --angles)")
    p.add_argument("--custom-loc", default=None,
                   help="X,Y,Z location for 'custom' angle")
    p.add_argument("--engine", default="workbench",
                   type=_normalize_engine_arg,
                   help="Render engine: workbench|eevee|cycles (raw Blender "
                        "enums like BLENDER_EEVEE_NEXT accepted)")
    p.add_argument("--samples", type=int, default=1,
                   help="Samples for eevee/cycles (default: 1)")
    p.add_argument("--w", type=int, default=640)
    p.add_argument("--h", type=int, default=480)
    p.add_argument("--lens", type=int, default=50,
                   help="Camera lens in mm (default: 50)")
    p.add_argument("--target", default=None,
                   help="X,Y,Z look-at target (default: scene bounding box center)")
    p.add_argument("--grid-cols", type=int, default=2,
                   help="Contact sheet grid columns (default: 2)")
    p.add_argument("--no-grid", action="store_true",
                   help="Don't stitch a contact sheet; output individual files "
                        "(output path becomes a directory)")
    p.add_argument("--load-blend", default=None,
                   help="Load a .blend file before capturing (alternative to --scene)")
    args = p.parse_args(script_argv())

    # Validate output + resolution early (fail fast)
    from blender_kit import validate_output, validate_resolution
    validate_output(args.output)
    validate_resolution(args.w, args.h)

    # Load or build scene
    if args.load_blend:
        print(f"[viewport] loading .blend: {args.load_blend}")
        bpy.ops.wm.open_mainfile(filepath=args.load_blend)
    elif args.scene:
        import importlib
        from blender_kit import safe_import_scene
        print(f"[viewport] building scene: {args.scene}")
        from blender_kit import clear_scene
        mod = safe_import_scene(args.scene)
        clear_scene()
        ctx = mod.build_scene()
        if hasattr(mod, "animate"):
            mod.animate(ctx, start_frame=1, n_frames=args.frames)
    else:
        print("[viewport] using currently-loaded scene")

    # Compute target
    if args.target:
        from blender_kit import parse_vec3
        target = parse_vec3(args.target, "target")
    else:
        target = _compute_scene_center()
        print(f"[viewport] using scene center as target: {target}")

    # Build angle list
    if args.ring is not None:
        if args.ring < 1:
            print(f"[viewport] ERROR: --ring must be >= 1, got {args.ring}", file=sys.stderr)
            sys.exit(1)
        n = args.ring
        angles = []
        for i in range(n):
            theta = 2 * math.pi * i / n
            radius = 5.0
            loc = (target[0] + radius * math.cos(theta),
                   target[1] + radius * math.sin(theta),
                   target[2] + 2.0)
            angles.append(("ring_%02d" % i, loc))
    else:
        angle_labels = args.angles.split(",")
        angles = []
        for lbl in angle_labels:
            lbl = lbl.strip()
            if lbl == "custom":
                if not args.custom_loc:
                    print("[viewport] ERROR: --custom-loc required for 'custom' angle", file=sys.stderr)
                    sys.exit(1)
                loc = tuple(float(v) for v in args.custom_loc.split(","))
                angles.append(("custom", loc))
            elif lbl in VIEW_ANGLES:
                base = VIEW_ANGLES[lbl][:3]
                loc = (base[0] + target[0], base[1] + target[1], base[2] + target[2])
                angles.append((lbl, loc))
            elif lbl == "active":
                angles.append(("active", None))
            else:
                print(f"[viewport] ERROR: unknown angle '{lbl}'", file=sys.stderr)
                sys.exit(1)

    print(f"[viewport] capturing {len(angles)} angle(s) with {args.engine} engine")

    # Render each angle
    if args.no_grid and len(angles) > 1:
        # Multiple angles, no stitching → output is a directory
        os.makedirs(args.output, exist_ok=True)
        out_paths = []
        for label, loc in angles:
            out_path = os.path.join(args.output, f"{label}.png")
            custom = loc if label == "custom" or label.startswith("ring_") else None
            render_angle(label if label not in ("custom",) and not label.startswith("ring_") else "custom",
                         out_path,
                         engine=args.engine, samples=args.samples,
                         width=args.w, height=args.h,
                         target=target, lens=args.lens,
                         custom_location=custom)
            print(f"[viewport]   -> {out_path}  ({os.path.getsize(out_path)} bytes)")
            out_paths.append(out_path)
        print(f"[viewport] wrote {len(out_paths)} individual files to {args.output}")
    elif args.no_grid and len(angles) == 1:
        # Single angle, no stitching → output is a file
        label, loc = angles[0]
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        custom = loc if label == "custom" or label.startswith("ring_") else None
        render_angle(label if label not in ("custom",) and not label.startswith("ring_") else "custom",
                     args.output,
                     engine=args.engine, samples=args.samples,
                     width=args.w, height=args.h,
                     target=target, lens=args.lens,
                     custom_location=custom)
        print(f"[viewport] -> {args.output}  ({os.path.getsize(args.output)} bytes)")
    else:
        # Stitch into contact sheet
        with tempfile.TemporaryDirectory() as tmpdir:
            out_paths = []
            for label, loc in angles:
                out_path = os.path.join(tmpdir, f"{label}.png")
                custom = loc if label == "custom" or label.startswith("ring_") else None
                render_angle(label if label not in ("custom",) and not label.startswith("ring_") else "custom",
                             out_path,
                             engine=args.engine, samples=args.samples,
                             width=args.w, height=args.h,
                             target=target, lens=args.lens,
                             custom_location=custom)
                out_paths.append(out_path)

            stitch_contact_sheet(out_paths, args.output, grid_cols=args.grid_cols)
            print(f"[viewport] contact sheet: {args.output}  "
                  f"({os.path.getsize(args.output)} bytes)")


if __name__ == "__main__":
    main()
