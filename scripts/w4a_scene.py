"""
w4a_scene.py — Wave 4a consumer usability-test scene (Task 4-c).

Three props, three motion archetypes, 24 frames, workbench-friendly
primitives (all verified on 5.2.2 per AGENTS.md gotcha 119):
  * SliderCyl — blue cylinder that SLIDES along +X at constant speed
  * BobSphere — orange sphere that BOBS up/down twice (eased)
  * SpinCube  — green cube that SPINS 360 deg around Z in place

All props rest on the ground at frame 1 (validator-clean pose).

Usage:
    blrun.sh --background --python scripts/w4a_scene.py -- \
        --output output/w4a_scene --dry-run --scene-name w4a_scene
"""
import math
import bpy
from blender_kit import (
    common_parser, script_argv, clear_scene, configure_render, render,
    make_material, shade_smooth, add_sky_world, print_scene_summary,
    iter_fcurves,
)


def build_scene():
    clear_scene()

    # Ground plane (flat slab, 20x20 — excluded from labeling per gotcha 112)
    bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, 0))
    plane = bpy.context.active_object
    plane.name = "Ground"
    plane.data.materials.append(
        make_material("GroundMat", (0.20, 0.22, 0.24), roughness=0.85))

    # Prop 1: SliderCyl — cylinder r=0.30 h=0.60, rests at z=h/2 (law 11)
    cyl_h = 0.60
    bpy.ops.mesh.primitive_cylinder_add(radius=0.30, depth=cyl_h,
                                        location=(-2.0, -1.2, cyl_h / 2))
    cyl = bpy.context.active_object
    cyl.name = "SliderCyl"
    shade_smooth(cyl)
    cyl.data.materials.append(
        make_material("CylMat", (0.20, 0.55, 0.95), roughness=0.3, metallic=0.2))

    # Prop 2: BobSphere — sphere r=0.35, rests at z=r
    sph_r = 0.35
    bpy.ops.mesh.primitive_uv_sphere_add(radius=sph_r,
                                         location=(1.6, 1.2, sph_r))
    sph = bpy.context.active_object
    sph.name = "BobSphere"
    shade_smooth(sph)
    sph.data.materials.append(
        make_material("SphMat", (0.95, 0.45, 0.10), roughness=0.35))

    # Prop 3: SpinCube — cube 0.7, rests at z=size/2
    cube_s = 0.70
    bpy.ops.mesh.primitive_cube_add(size=cube_s,
                                    location=(-1.4, 1.2, cube_s / 2))
    cube = bpy.context.active_object
    cube.name = "SpinCube"
    cube.data.materials.append(
        make_material("CubeMat", (0.25, 0.75, 0.35), roughness=0.4))

    # Sun + area fill (neutral bases, color law 39)
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

    add_sky_world()

    return {
        "cyl": cyl, "sph": sph, "cube": cube,
        "cyl_h": cyl_h, "sph_r": sph_r, "cube_s": cube_s,
    }


def animate(ctx, *, start_frame=1, n_frames=24):
    scene = bpy.context.scene
    scene.frame_start = start_frame
    scene.frame_end = start_frame + n_frames - 1
    end_frame = start_frame + n_frames - 1

    cyl = ctx["cyl"]
    sph = ctx["sph"]
    cube = ctx["cube"]
    cyl_h = ctx["cyl_h"]
    sph_r = ctx["sph_r"]
    cube_s = ctx["cube_s"]

    # --- SliderCyl: linear slide along +X, y/z constant (grounded) ---
    cyl.location = (-2.0, -1.2, cyl_h / 2)
    cyl.keyframe_insert("location", index=0)
    scene.frame_set(end_frame)
    cyl.location = (2.0, -1.2, cyl_h / 2)
    cyl.keyframe_insert("location", index=0)

    # --- SpinCube: 360 deg around Z in place (linear) ---
    scene.frame_set(start_frame)
    cube.rotation_euler = (0.0, 0.0, 0.0)
    cube.keyframe_insert("rotation_euler", index=2)
    scene.frame_set(end_frame)
    cube.rotation_euler = (0.0, 0.0, math.radians(360))
    cube.keyframe_insert("rotation_euler", index=2)

    # --- BobSphere: two eased bobs: ground -> up 0.9 -> ground -> up -> ground
    scene.frame_set(start_frame)
    bob_h = sph_r + 0.9
    keys = [
        (start_frame, sph_r),
        (start_frame + 6, bob_h),
        (start_frame + 12, sph_r),
        (start_frame + 18, bob_h),
        (end_frame, sph_r),
    ]
    for f, z in keys:
        scene.frame_set(int(f))          # law 11c: ints only
        sph.location.z = z
        sph.keyframe_insert("location", index=2)

    # Interpolation: LINEAR for slide+spin, BEZIER for the bob
    for obj, mode, easing in ((cyl, 'LINEAR', 'AUTO'), (cube, 'LINEAR', 'AUTO'),
                              (sph, 'BEZIER', 'EASE_IN_OUT')):
        if obj.animation_data and obj.animation_data.action:
            for fcurve in iter_fcurves(obj.animation_data.action):
                for kp in fcurve.keyframe_points:
                    kp.interpolation = mode
                    kp.easing = easing

    scene.frame_set(start_frame)


def main():
    p = common_parser()
    args = p.parse_args(script_argv())
    print(f"[w4a_scene] args: {args}")
    ctx = build_scene()
    animate(ctx, start_frame=args.start, n_frames=args.frames)
    configure_render(args)
    print_scene_summary(args.scene_name)
    render(args, scene_name=args.scene_name)


if __name__ == "__main__":
    main()
