"""
t6_transient.py — T6 test scene: planted frame-transient glitch (vision-kit
M5 P3/P4 test vehicle).

Three moving props + one PLANTED transient that only exists on frames
15-17 (between keyframes — a keyframe contact sheet sampling 1/8/16/24
would catch it only by luck):

  - Ball:      parabola hop along +X (rises f1-12, lands f24)
  - Slider:    linear drift along +Y
  - GlitchBox: purple box that SINKS into the ground f15-17 (z dips -0.22)
               and recovers — the canonical transient (validator sees
               below-floor only at the sink bottom; contact sheets may
               sample around it)

Also the label-stick repro vehicle: look.py --frame 16 --closeup GlitchBox
must show the label readable AFTER refresh_labels (it rendered edge-on
before the fix — measured).

Usage:
    blrun.sh --background --python scripts/t6_transient.py -- \
        --output output/t6_transient --dry-run --scene-name t6_transient
"""
import math

import bpy
from mathutils import Matrix

from blender_kit import (
    common_parser, script_argv, clear_scene, make_material, shade_smooth,
    print_scene_summary,
)


def build_scene():
    clear_scene()

    bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, 0))
    ground = bpy.context.active_object
    ground.name = "Ground"
    ground.data.materials.append(
        make_material("GroundMat", (0.20, 0.22, 0.24), roughness=0.85))

    # Ball: 0.3m, parabola hop 1->12 rise, 12->24 land (peaks mid-shot)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.15, segments=24,
                                         ring_count=16, location=(-1.5, 0, 0.15))
    ball = bpy.context.active_object
    ball.name = "Ball"
    shade_smooth(ball)
    ball.data.materials.append(
        make_material("BallMat", (0.90, 0.25, 0.15), roughness=0.35))

    # Slider: 0.4m box drifting +Y
    bpy.ops.mesh.primitive_cube_add(size=0.4, location=(0.5, -1.0, 0.2))
    slider = bpy.context.active_object
    slider.name = "Slider"
    slider.data.materials.append(
        make_material("SliderMat", (0.15, 0.45, 0.90), roughness=0.5))

    # GlitchBox: 0.35m purple box, planted sink glitch f15-17
    bpy.ops.mesh.primitive_cube_add(size=0.35, location=(1.5, 0.8, 0.175))
    glitch = bpy.context.active_object
    glitch.name = "GlitchBox"
    glitch.data.materials.append(
        make_material("GlitchMat", (0.55, 0.20, 0.80), roughness=0.6))

    print_scene_summary()
    return {"ball": ball, "slider": slider, "glitch": glitch}


def animate(ctx, start_frame=1, n_frames=24):
    scene = bpy.context.scene
    scene.frame_start = start_frame
    scene.frame_end = start_frame + n_frames - 1
    end = start_frame + n_frames - 1
    mid = start_frame + n_frames // 2 - 1

    ball = ctx["ball"]
    slider = ctx["slider"]
    glitch = ctx["glitch"]

    # Ball: parabola via three keys (start, apex, end)
    ball.location = (-1.5, 0, 0.15)
    ball.keyframe_insert("location", frame=start_frame)
    ball.location = (0.0, 0, 1.35)
    ball.keyframe_insert("location", frame=mid)
    ball.location = (1.5, 0, 0.15)
    ball.keyframe_insert("location", frame=end)

    # Slider: linear drift
    slider.location = (0.5, -1.0, 0.2)
    slider.keyframe_insert("location", frame=start_frame)
    slider.location = (0.5, 1.0, 0.2)
    slider.keyframe_insert("location", frame=end)

    # GlitchBox: rest -> sunk (f16) -> rest. On LINEAR interp the sink
    # spans f14-18; the below-floor bottom lands f15-17.
    glitch.location = (1.5, 0.8, 0.175)
    glitch.keyframe_insert("location", frame=start_frame + 13)
    glitch.location = (1.5, 0.8, -0.05)   # top at ~0.125: buried slab
    glitch.keyframe_insert("location", frame=start_frame + 16)
    glitch.location = (1.5, 0.8, 0.175)
    glitch.keyframe_insert("location", frame=start_frame + 19)

    for ob in (ball, slider, glitch):
        from blender_kit import iter_fcurves
        for fc in iter_fcurves(ob.animation_data.action):
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'
    return ctx


def probe(ctx):
    print("[t6] T6 transient scene: planted GlitchBox sink f14-18 "
          "(bottom f15-17); Ball parabola; Slider drift")


def main():
    from blender_kit import configure_render, render
    p = common_parser()
    args = p.parse_args(script_argv())
    print(f"[t6] args: {args}")
    ctx = build_scene()
    animate(ctx, start_frame=args.start, n_frames=args.frames)
    probe(ctx)
    if args.dry_run:
        print("[t6] --dry-run: scene built in-memory (no render/save)")
        return
    configure_render(args)
    print_scene_summary(args.scene_name)
    render(args, scene_name=args.scene_name)


if __name__ == "__main__":
    main()
