"""
keyframe_contact_sheet.py — stitch N keyframes into one image for animation/motion VLM verification.

VLMs can't natively process video. To verify animation, sample N keyframes
from the animation, render each at low quality, and stitch them into a single
grid image. The VLM sees the motion arc in one shot.

Usage:
    blrun.sh --background --python scripts/keyframe_contact_sheet.py -- \\
        --scene scene_template --output output/motion_check.png \\
        --frames 6 --grid-cols 3

    # Use the scene's existing active camera (default)
    blrun.sh --background --python scripts/keyframe_contact_sheet.py -- \\
        --scene scene_template --output output/motion_check.png \\
        --frames 6 --engine eevee --samples 4

    # Render with a custom orbit camera instead of the scene's camera
    blrun.sh --background --python scripts/keyframe_contact_sheet.py -- \\
        --scene scene_template --output output/motion_check.png \\
        --frames 8 --orbit
"""
import argparse
import math
import os
import sys
import tempfile

import bpy
from blender_kit import script_argv, clear_scene


def _normalize_engine_arg(v):
    """Argparse type: bridge raw Blender enum spellings to dispatch names."""
    from blender_kit import normalize_engine
    return normalize_engine(v)


def main():
    p = argparse.ArgumentParser(
        description="Render N keyframes as a contact sheet for animation verification.")
    p.add_argument("--scene", required=True,
                   help="Scene module name (e.g. scene_template)")
    p.add_argument("--output", required=True,
                   help="Output contact sheet PNG path")
    p.add_argument("--frames", type=int, default=6,
                   help="Number of keyframes to sample (default: 6)")
    p.add_argument("--start", type=int, default=None,
                   help="Start frame (default: scene's frame_start)")
    p.add_argument("--end", type=int, default=None,
                   help="End frame (default: scene's frame_end)")
    p.add_argument("--engine", default="workbench",
                   type=_normalize_engine_arg)
    p.add_argument("--samples", type=int, default=1)
    p.add_argument("--w", type=int, default=480,
                   help="Per-frame width (default: 480)")
    p.add_argument("--h", type=int, default=360,
                   help="Per-frame height (default: 360)")
    p.add_argument("--grid-cols", type=int, default=3,
                   help="Contact sheet grid columns (default: 3)")
    p.add_argument("--orbit", action="store_true",
                   help="Use an orbit camera (revolves around scene center) "
                        "instead of the scene's active camera")
    p.add_argument("--orbit-radius", type=float, default=6.0)
    p.add_argument("--orbit-height", type=float, default=3.0)
    args = p.parse_args(script_argv())

    # Import scene module and build the scene
    print(f"[contact_sheet] importing scene: {args.scene}")
    import importlib
    from blender_kit import safe_import_scene
    mod = safe_import_scene(args.scene)
    clear_scene()
    ctx = mod.build_scene()
    if hasattr(mod, "animate"):
        mod.animate(ctx, start_frame=1, n_frames=24)

    scene = bpy.context.scene
    start = args.start if args.start is not None else scene.frame_start
    end = args.end if args.end is not None else scene.frame_end
    if end <= start:
        print(f"[contact_sheet] ERROR: end ({end}) must be > start ({start})", file=sys.stderr)
        sys.exit(1)

    # Sample N frames evenly across the range
    n = args.frames
    if n < 1:
        print(f"[contact_sheet] ERROR: --frames must be >= 1, got {n}", file=sys.stderr)
        sys.exit(1)
    if n == 1:
        frame_nums = [start]
    else:
        step = (end - start) / (n - 1)
        frame_nums = [int(round(start + i * step)) for i in range(n)]

    print(f"[contact_sheet] sampling {n} frames: {frame_nums}")

    # Configure render engine
    if args.engine == "workbench":
        scene.render.engine = 'BLENDER_WORKBENCH'
        scene.display.shading.light = 'STUDIO'
        scene.display.shading.color_type = 'OBJECT'
        scene.display.shading.show_shadows = True
        scene.display.shading.show_cavity = True
    elif args.engine == "eevee":
        from blender_kit import EEVEE_ENGINE_ID
        scene.render.engine = EEVEE_ENGINE_ID
        scene.eevee.taa_render_samples = args.samples
    elif args.engine == "cycles":
        scene.render.engine = 'CYCLES'
        scene.cycles.device = 'CPU'
        scene.cycles.samples = args.samples
        scene.cycles.use_denoising = True

    scene.render.resolution_x = args.w
    scene.render.resolution_y = args.h
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'

    # Compute scene center for orbit camera
    meshes = [o for o in scene.objects if o.type == 'MESH']
    if meshes:
        xs, ys, zs = [], [], []
        for o in meshes:
            for corner in o.bound_box:
                world = o.matrix_world @ type(o.location)(corner)
                xs.append(world.x); ys.append(world.y); zs.append(world.z)
        target = (sum(xs)/len(xs), sum(ys)/len(ys), sum(zs)/len(zs))
    else:
        target = (0, 0, 0)

    # Set up orbit camera if requested
    orig_camera = scene.camera
    orbit_cam = None
    orbit_target_empty = None
    if args.orbit or scene.camera is None:
        cam_data = bpy.data.cameras.new("orbit_cam_data")
        cam_data.lens = 50
        orbit_cam = bpy.data.objects.new("orbit_cam", cam_data)
        bpy.context.collection.objects.link(orbit_cam)
        orbit_target_empty = bpy.data.objects.new("orbit_target", None)
        bpy.context.collection.objects.link(orbit_target_empty)
        orbit_target_empty.location = target
        constraint = orbit_cam.constraints.new(type='TRACK_TO')
        constraint.target = orbit_target_empty
        constraint.track_axis = 'TRACK_NEGATIVE_Z'
        constraint.up_axis = 'UP_Y'
        scene.camera = orbit_cam

    # Render each frame
    with tempfile.TemporaryDirectory() as tmpdir:
        out_paths = []
        for i, frame_num in enumerate(frame_nums):
            scene.frame_set(frame_num)

            # If orbit, also rotate the camera around target
            if orbit_cam is not None:
                t = i / max(1, n - 1)  # 0 to 1
                theta = math.radians(360 * t) - math.pi/2  # start from front
                orbit_cam.location = (
                    target[0] + args.orbit_radius * math.cos(theta),
                    target[1] + args.orbit_radius * math.sin(theta),
                    target[2] + args.orbit_height,
                )

            out_path = os.path.join(tmpdir, f"f{frame_num:04d}.png")
            scene.render.filepath = out_path
            bpy.ops.render.render(write_still=True)
            if not os.path.exists(out_path):
                print(f"[contact_sheet] ERROR: render failed for frame {frame_num}", file=sys.stderr)
                sys.exit(1)
            out_paths.append((frame_num, out_path))
            print(f"[contact_sheet]   frame {frame_num}: {os.path.getsize(out_path)} bytes")

        # Stitch with frame number labels
        from PIL import Image, ImageDraw, ImageFont
        imgs = [Image.open(p) for _, p in out_paths]
        w, h = imgs[0].size
        imgs = [im.resize((w, h)) for im in imgs]
        rows = (len(imgs) + args.grid_cols - 1) // args.grid_cols
        label_h = 28
        sheet = Image.new('RGB',
                          (args.grid_cols * w, rows * (h + label_h)),
                          (20, 20, 24))
        draw = ImageDraw.Draw(sheet)
        try:
            font = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
        except Exception:
            font = ImageFont.load_default()

        for i, ((frame_num, _), im) in enumerate(zip(out_paths, imgs)):
            col = i % args.grid_cols
            row = i // args.grid_cols
            x = col * w
            y = row * (h + label_h) + label_h
            sheet.paste(im, (x, y))
            # Label with frame number
            lbl = f"Frame {frame_num}"
            draw.rectangle([(x, y - label_h), (x + w, y)], fill=(20, 20, 24))
            # Center the text
            bbox = draw.textbbox((0, 0), lbl, font=font)
            text_w = bbox[2] - bbox[0]
            draw.text((x + (w - text_w) // 2, y - label_h + 5), lbl,
                      fill=(230, 230, 230), font=font)

        # Save final sheet
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        sheet.save(args.output)
        print(f"[contact_sheet] wrote {args.output}  "
              f"({os.path.getsize(args.output)} bytes, "
              f"{args.grid_cols}x{rows} grid of {len(imgs)} frames)")

    # Cleanup
    if orbit_cam is not None:
        bpy.data.objects.remove(orbit_cam, do_unlink=True)
        bpy.data.objects.remove(orbit_target_empty, do_unlink=True)
        scene.camera = orig_camera


if __name__ == "__main__":
    main()
