"""
r3_turntable.py — R3 dog-food scene: EEVEE product-turntable lane.

Three hero props (metallic chrome ball, rough red plastic cube, green
glass-ish cylinder) on a dark studio ground, 3-point lighting, slow
turntable orbit of the camera + a slider prop that travels the table.

Usage:
    blrun.sh --background --python scripts/r3_turntable.py -- \
        --output output/r3_turntable --engine eevee --still 1 --samples 16
    blrun.sh --background --python scripts/r3_turntable.py -- \
        --output output/r3_turntable --engine eevee --frames 24 --encode-mp4
"""
import math
import bpy
from blender_kit import (
    common_parser, script_argv, clear_scene, configure_render, render,
    make_material, shade_smooth, add_sky_world, print_scene_summary,
)


def build_scene():
    clear_scene()

    # Studio ground — dark, slightly glossy
    bpy.ops.mesh.primitive_plane_add(size=14, location=(0, 0, 0))
    plane = bpy.context.active_object
    plane.name = "Ground"
    plane.data.materials.append(
        make_material("GroundMat", (0.10, 0.10, 0.12), roughness=0.4))

    # Prop 1: chrome ball
    ball_r = 0.35
    bpy.ops.mesh.primitive_uv_sphere_add(radius=ball_r,
                                         location=(-1.4, 0.2, ball_r))
    ball = bpy.context.active_object
    ball.name = "ChromeBall"
    shade_smooth(ball)
    ball.data.materials.append(
        make_material("ChromeMat", (0.85, 0.85, 0.88),
                      roughness=0.08, metallic=1.0))

    # Prop 2: red plastic cube
    cube_s = 0.6
    bpy.ops.mesh.primitive_cube_add(size=cube_s, location=(0.1, -0.35, cube_s / 2))
    cube = bpy.context.active_object
    cube.name = "RedCube"
    cube.data.materials.append(
        make_material("RedPlasticMat", (0.75, 0.08, 0.06), roughness=0.55))

    # Prop 3: green cylinder
    cyl_r, cyl_h = 0.28, 0.75
    bpy.ops.mesh.primitive_cylinder_add(radius=cyl_r, depth=cyl_h,
                                        location=(1.3, 0.25, cyl_h / 2))
    cyl = bpy.context.active_object
    cyl.name = "GreenCyl"
    shade_smooth(cyl)
    cyl.data.materials.append(
        make_material("GreenMat", (0.10, 0.55, 0.22), roughness=0.3))

    # Slider prop — the animated one (travels across the table)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.16, location=(-2.2, -0.6, 0.16))
    slider = bpy.context.active_object
    slider.name = "Slider"
    shade_smooth(slider)
    slider.data.materials.append(
        make_material("SliderMat", (0.95, 0.75, 0.10), roughness=0.35,
                      metallic=0.2))

    # 3-point lighting (key sun + area fill + rim)
    bpy.ops.object.light_add(type='SUN', location=(4, -4, 6))
    sun = bpy.context.active_object
    sun.name = "KeyLight"
    sun.data.energy = 2.2
    sun.rotation_euler = (math.radians(50), math.radians(10), math.radians(30))

    bpy.ops.object.light_add(type='AREA', location=(-3.5, -2.5, 3.2))
    fill = bpy.context.active_object
    fill.name = "FillLight"
    fill.data.energy = 120.0
    fill.data.size = 3.5

    bpy.ops.object.light_add(type='AREA', location=(1.5, 3.5, 2.6))
    rim = bpy.context.active_object
    rim.name = "RimLight"
    rim.data.energy = 70.0
    rim.data.size = 2.0

    # Camera (turntable target: animate rotation_z around scene origin)
    bpy.ops.object.empty_add(location=(0, 0, 0.4))
    pivot = bpy.context.active_object
    pivot.name = "TurntablePivot"

    bpy.ops.object.camera_add(location=(0, -4.6, 1.7),
                              rotation=(math.radians(70), 0, 0))
    cam = bpy.context.active_object
    cam.name = "TurntableCam"
    cam.data.lens = 55
    cam.parent = pivot
    bpy.context.scene.camera = cam

    add_sky_world(strength=0.35)

    return {"slider": slider, "pivot": pivot}


def animate(ctx, *, start_frame=1, n_frames=24):
    scene = bpy.context.scene
    scene.frame_start = start_frame
    scene.frame_end = start_frame + n_frames - 1
    scene.frame_set(start_frame)

    slider = ctx["slider"]
    pivot = ctx["pivot"]
    end_frame = start_frame + n_frames - 1

    # Turntable: camera pivot orbits 90° over the shot
    pivot.keyframe_insert("rotation_euler", index=2)
    scene.frame_set(end_frame)
    pivot.rotation_euler = (0, 0, math.radians(90))
    pivot.keyframe_insert("rotation_euler", index=2)

    # Slider crosses the table and comes back halfway (non-linear path)
    slider.keyframe_insert("location")
    mid = start_frame + n_frames // 2
    scene.frame_set(mid)
    slider.location = (0.0, -1.7, 0.16)
    slider.keyframe_insert("location")
    scene.frame_set(end_frame)
    slider.location = (2.2, -0.6, 0.16)
    slider.keyframe_insert("location")

    from blender_kit import iter_fcurves
    for obj in (slider, pivot):
        if obj.animation_data and obj.animation_data.action:
            for fcurve in iter_fcurves(obj.animation_data.action):
                for kp in fcurve.keyframe_points:
                    kp.interpolation = 'BEZIER'

    scene.frame_set(start_frame)


def main():
    p = common_parser()
    args = p.parse_args(script_argv())
    print(f"[r3_turntable] args: {args}")
    ctx = build_scene()
    animate(ctx, start_frame=args.start, n_frames=args.frames)
    configure_render(args)
    print_scene_summary(args.scene_name)
    render(args, scene_name=args.scene_name)


if __name__ == "__main__":
    main()
