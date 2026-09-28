"""
scene_template.py — copy this file to start a new scene.

Minimal example: a cube on a plane, with a sun light and camera.

Usage:
    blrun.sh --background --python scripts/scene_template.py -- \\
        --output output/my_scene \\
        --engine BLENDER_EEVEE_NEXT \\
        --still 1 --samples 16

    # Full animation + MP4:
    blrun.sh --background --python scripts/scene_template.py -- \\
        --output output/my_scene \\
        --engine BLENDER_EEVEE_NEXT \\
        --frames 24 --encode-mp4

    # Export glTF for web preview:
    blrun.sh --background --python scripts/scene_template.py -- \\
        --output output/my_scene --dry-run
    blrun.sh --background --python scripts/export_gltf.py -- \\
        --scene scene_template --output output/my_scene/my_scene.glb
"""
import math
import bpy
from blender_kit import (
    common_parser, script_argv, clear_scene, configure_render, render,
    make_material, shade_smooth, add_sky_world, print_scene_summary,
)


# ---------------------------------------------------------------------------
# Build the static scene (no animation). Return a context dict the animate()
# function will use to find the objects it needs to keyframe.
# ---------------------------------------------------------------------------

def build_scene():
    clear_scene()

    # Ground plane
    bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, 0))
    plane = bpy.context.active_object
    plane.name = "Ground"
    plane.data.materials.append(
        make_material("GroundMat", (0.20, 0.22, 0.24), roughness=0.85))

    # Hero cube — RESTING on ground (z = size/2)
    cube_size = 1.2
    bpy.ops.mesh.primitive_cube_add(size=cube_size,
                                    location=(0, 0, cube_size / 2))
    cube = bpy.context.active_object
    cube.name = "HeroCube"
    cube.data.materials.append(
        make_material("CubeMat", (0.95, 0.35, 0.15),
                       roughness=0.35, metallic=0.1))

    # Sphere — RESTING on ground (z = radius)
    sphere_r = 0.45
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=sphere_r, location=(1.8, 0.6, sphere_r))
    sphere = bpy.context.active_object
    sphere.name = "Sphere"
    shade_smooth(sphere)
    sphere.data.materials.append(
        make_material("SphereMat", (0.20, 0.55, 0.95),
                       roughness=0.25, metallic=0.4))

    # Sun + area fill
    bpy.ops.object.light_add(type='SUN', location=(4, -4, 6))
    sun = bpy.context.active_object
    sun.name = "KeyLight"
    sun.data.energy = 3.0
    sun.rotation_euler = (math.radians(55), math.radians(15), math.radians(35))

    bpy.ops.object.light_add(type='AREA', location=(-3, -2, 3))
    fill = bpy.context.active_object
    fill.name = "FillLight"
    fill.data.energy = 150.0
    fill.data.size = 3.0

    # Camera
    bpy.ops.object.camera_add(location=(4.5, -4.5, 2.8),
                              rotation=(math.radians(72), 0, math.radians(45)))
    cam = bpy.context.active_object
    cam.name = "MainCam"
    cam.data.lens = 50
    bpy.context.scene.camera = cam

    # HDRI-like ambient sky
    add_sky_world()

    # Return a context dict so animate() can find objects + dimensions
    return {
        "cube": cube,
        "sphere": sphere,
        "cube_size": cube_size,
        "sphere_r": sphere_r,
    }


# ---------------------------------------------------------------------------
# Animation. Use ctx dict from build_scene().
# ---------------------------------------------------------------------------

def animate(ctx, *, start_frame=1, n_frames=24):
    scene = bpy.context.scene
    scene.frame_start = start_frame
    scene.frame_end = start_frame + n_frames - 1
    scene.frame_set(start_frame)

    cube = ctx["cube"]
    sphere = ctx["sphere"]
    cube_size = ctx["cube_size"]
    end_frame = start_frame + n_frames - 1
    mid = start_frame + n_frames // 2

    # Cube bounces up and rotates 360°
    cube.keyframe_insert("location", index=2)
    cube.keyframe_insert("rotation_euler")
    scene.frame_set(mid)
    cube.location.z = 1.8
    cube.rotation_euler = (math.radians(180), 0, math.radians(90))
    cube.keyframe_insert("location", index=2)
    cube.keyframe_insert("rotation_euler")
    scene.frame_set(end_frame)
    cube.location.z = cube_size / 2
    cube.rotation_euler = (math.radians(360), 0, math.radians(180))
    cube.keyframe_insert("location", index=2)
    cube.keyframe_insert("rotation_euler")

    # Sphere drifts left
    sphere.keyframe_insert("location", index=0)
    scene.frame_set(end_frame)
    sphere.location.x = -1.8
    sphere.keyframe_insert("location", index=0)

    # Bezier easing on all keyframes
    from blender_kit import iter_fcurves
    for obj in (cube, sphere):
        if obj.animation_data and obj.animation_data.action:
            for fcurve in iter_fcurves(obj.animation_data.action):
                for kp in fcurve.keyframe_points:
                    kp.interpolation = 'BEZIER'
                    kp.easing = 'EASE_IN_OUT'

    scene.frame_set(start_frame)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main():
    p = common_parser()
    args = p.parse_args(script_argv())
    print(f"[scene_template] args: {args}")
    ctx = build_scene()
    animate(ctx, start_frame=args.start, n_frames=args.frames)
    configure_render(args)
    print_scene_summary(args.scene_name)
    render(args, scene_name=args.scene_name)


if __name__ == "__main__":
    main()
