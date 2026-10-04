"""
scene_v1_basic.py — minimal example scene (plane + cube + sphere + lights).

Migrated to the kit driver convention (QA #6): build_scene() returns a
context dict and animate(ctx, *, start_frame, n_frames) consumes it —
the SAME contract look.py / motion_study / transient_scan expect when
driving a scene module directly:

    blrun.sh --background --python scripts/look.py -- \\
        --scene examples/scene_v1_basic --output output/v1/look

Standalone rendering works too:

    blrun.sh --background --python examples/scene_v1_basic.py -- \\
        --output output/v1 --engine eevee --frames 24 --encode-mp4
"""
import math

import bpy
from blender_kit import (
    common_parser, script_argv, clear_scene, configure_render, render,
    make_material, print_scene_summary,
)


def build_scene():
    clear_scene()

    # Ground plane
    bpy.ops.mesh.primitive_plane_add(size=10, location=(0, 0, 0))
    plane = bpy.context.active_object
    plane.name = "Ground"
    plane.data.materials.append(
        make_material("GroundMat", (0.18, 0.20, 0.22), roughness=0.9))

    # Hero cube
    bpy.ops.mesh.primitive_cube_add(size=1.2, location=(0, 0, 0.6))  # rests: z = size/2
    cube = bpy.context.active_object
    cube.name = "HeroCube"
    cube.data.materials.append(
        make_material("CubeMat", (0.95, 0.35, 0.15), roughness=0.35,
                      metallic=0.1))

    # Secondary sphere
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.4, location=(2.0, 0, 0.4))
    sphere = bpy.context.active_object
    sphere.name = "Sphere"
    sphere.data.materials.append(
        make_material("SphereMat", (0.20, 0.55, 0.95), roughness=0.25,
                      metallic=0.4))

    # Key light (sun) + fill (area)
    bpy.ops.object.light_add(type='SUN', location=(4, -4, 6))
    sun = bpy.context.active_object
    sun.name = "KeyLight"
    sun.data.energy = 4.0
    sun.rotation_euler = (math.radians(50), math.radians(20), math.radians(35))

    bpy.ops.object.light_add(type='AREA', location=(-3, -2, 3))
    fill = bpy.context.active_object
    fill.name = "FillLight"
    fill.data.energy = 200.0
    fill.data.size = 3.0

    # Camera
    bpy.ops.object.camera_add(location=(5.0, -5.0, 3.2),
                              rotation=(math.radians(65), 0, math.radians(45)))
    cam = bpy.context.active_object
    cam.name = "MainCam"
    cam.data.lens = 35
    bpy.context.scene.camera = cam

    # Dark ambient world (studio look — see AGENTS.md gotcha 128 for the
    # sky-world x EEVEE exposure trap)
    world = bpy.data.worlds.new("World") if not bpy.data.worlds \
        else bpy.data.worlds[0]
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (0.04, 0.05, 0.07, 1.0)
    bg.inputs["Strength"].default_value = 1.0

    return {"cube": cube, "sphere": sphere}


def animate(ctx, *, start_frame=1, n_frames=24):
    scene = bpy.context.scene
    scene.frame_start = start_frame
    scene.frame_end = start_frame + n_frames - 1
    scene.frame_set(start_frame)

    cube = ctx["cube"]
    sphere = ctx["sphere"]
    end_frame = start_frame + n_frames - 1

    # Cube bounces up and rotates
    cube.keyframe_insert("location", index=2)              # z at start
    cube.keyframe_insert("rotation_euler")                  # rotation at start

    mid = start_frame + n_frames // 2
    scene.frame_set(mid)
    cube.location.z = 2.4
    cube.rotation_euler = (math.radians(180), 0, math.radians(90))
    cube.keyframe_insert("location", index=2)
    cube.keyframe_insert("rotation_euler")

    scene.frame_set(end_frame)
    cube.location.z = 0.6
    cube.rotation_euler = (math.radians(360), 0, math.radians(180))
    cube.keyframe_insert("location", index=2)
    cube.keyframe_insert("rotation_euler")

    # Make the bounce a bit snappier
    from blender_kit import iter_fcurves
    if cube.animation_data and cube.animation_data.action:
        for fcurve in iter_fcurves(cube.animation_data.action):
            for kp in fcurve.keyframe_points:
                kp.interpolation = 'BEZIER'
                kp.easing = 'EASE_OUT'

    # Sphere drifts left
    sphere.keyframe_insert("location", index=0)
    scene.frame_set(end_frame)
    sphere.location.x = -2.0
    sphere.keyframe_insert("location", index=0)

    scene.frame_set(start_frame)


def main():
    p = common_parser()
    args = p.parse_args(script_argv())
    print(f"[scene_basic] args: {args}")
    ctx = build_scene()
    animate(ctx, start_frame=args.start, n_frames=args.frames)
    configure_render(args)
    print_scene_summary(args.scene_name)
    render(args, scene_name=args.scene_name)


if __name__ == "__main__":
    main()
