"""
scene_v2_balanced.py — composed example scene (resting props, sky world,
rule-of-thirds framing, torus roll). Migrated to the kit driver
convention (QA #6): build_scene() returns a context dict and
animate(ctx, *, start_frame, n_frames) consumes it; the local NISHITA
sky helper (enum removed in Blender 5.x) is replaced by the kit's
version-safe add_sky_world.

Drive it with the perception tools:

    blrun.sh --background --python scripts/look.py -- \\
        --scene examples/scene_v2_balanced --output output/v2/look

Or render standalone:

    blrun.sh --background --python examples/scene_v2_balanced.py -- \\
        --output output/v2 --engine eevee --frames 24
"""
import math

import bpy
from blender_kit import (
    common_parser, script_argv, clear_scene, configure_render, render,
    make_material, shade_smooth, add_sky_world, print_scene_summary,
)


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
    bpy.ops.mesh.primitive_cube_add(size=cube_size, location=(0, 0, cube_size / 2))
    cube = bpy.context.active_object
    cube.name = "HeroCube"
    cube.data.materials.append(
        make_material("CubeMat", (0.95, 0.35, 0.15), roughness=0.35, metallic=0.1))

    # Sphere — RESTING on ground (z = radius)
    sphere_r = 0.45
    bpy.ops.mesh.primitive_uv_sphere_add(radius=sphere_r, location=(1.8, 0.6, sphere_r))
    sphere = bpy.context.active_object
    sphere.name = "Sphere"
    shade_smooth(sphere)
    sphere.data.materials.append(
        make_material("SphereMat", (0.20, 0.55, 0.95), roughness=0.25, metallic=0.4))

    # Torus — third object for composition balance
    torus_major = 0.45
    bpy.ops.mesh.primitive_torus_add(
        major_radius=torus_major, minor_radius=0.12,
        location=(-1.6, 0.4, torus_major))
    torus = bpy.context.active_object
    torus.name = "Torus"
    torus.rotation_euler = (math.radians(70), 0, math.radians(20))
    shade_smooth(torus)
    torus.data.materials.append(
        make_material("TorusMat", (0.95, 0.85, 0.20), roughness=0.3, metallic=0.6))

    # Key sun light
    bpy.ops.object.light_add(type='SUN', location=(4, -4, 6))
    sun = bpy.context.active_object
    sun.name = "KeyLight"
    sun.data.energy = 3.0
    sun.rotation_euler = (math.radians(55), math.radians(15), math.radians(35))

    # Fill area light
    bpy.ops.object.light_add(type='AREA', location=(-3, -2, 3))
    fill = bpy.context.active_object
    fill.name = "FillLight"
    fill.data.energy = 150.0
    fill.data.size = 3.0

    # Camera — tighter framing, rule of thirds
    bpy.ops.object.camera_add(location=(4.5, -4.5, 2.8),
                              rotation=(math.radians(72), 0, math.radians(45)))
    cam = bpy.context.active_object
    cam.name = "MainCam"
    cam.data.lens = 50
    bpy.context.scene.camera = cam

    # Sky world for HDRI-like ambient (version-safe: NISHITA removed in 5.x;
    # outdoors default strength is fine — see AGENTS.md gotcha 128)
    add_sky_world()

    return {"cube": cube, "sphere": sphere, "torus": torus,
            "cube_size": cube_size}


def animate(ctx, *, start_frame=1, n_frames=24):
    scene = bpy.context.scene
    scene.frame_start = start_frame
    scene.frame_end = start_frame + n_frames - 1
    scene.frame_set(start_frame)

    cube = ctx["cube"]
    sphere = ctx["sphere"]
    torus = ctx["torus"]
    cube_size = ctx["cube_size"]
    mid = start_frame + n_frames // 2
    end_frame = start_frame + n_frames - 1

    # Cube bounces up and rotates
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

    # Torus rolls
    torus.keyframe_insert("rotation_euler")
    torus.keyframe_insert("location", index=1)
    scene.frame_set(end_frame)
    torus.rotation_euler = (math.radians(70), math.radians(720), math.radians(20))
    torus.location.y = -1.0
    torus.keyframe_insert("rotation_euler")
    torus.keyframe_insert("location", index=1)

    # Bezier easing
    from blender_kit import iter_fcurves
    for obj in (cube, sphere, torus):
        if obj.animation_data and obj.animation_data.action:
            for fcurve in iter_fcurves(obj.animation_data.action):
                for kp in fcurve.keyframe_points:
                    kp.interpolation = 'BEZIER'
                    kp.easing = 'EASE_IN_OUT'

    scene.frame_set(start_frame)


def main():
    p = common_parser()
    args = p.parse_args(script_argv())
    print(f"[scene_v2] args: {args}")
    ctx = build_scene()
    animate(ctx, start_frame=args.start, n_frames=args.frames)
    configure_render(args)
    print_scene_summary(args.scene_name)
    render(args, scene_name=args.scene_name)


if __name__ == "__main__":
    main()
