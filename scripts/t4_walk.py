"""
t4_walk.py — capsule actor walk cycle (T4 animated usability test).

A simple "character" from primitives:
  - Body: capsule ~0.92m tall, object ORIGIN AT PELVIS (z=0.45), mesh above origin
  - LegL/LegR: cylinders 0.45m, origin at hip (pelvis), mesh hangs below origin
  - Walk: legs swing rotation_euler.x +-25deg (2 steps over 24 frames, LINEAR),
    body moves forward +1.2m along X, slight z bob (±0.02m).

Usage:
    blrun.sh --background --python scripts/t4_walk.py -- \\
        --output output/t4_walk --dry-run --scene-name t4_walk
"""
import math
import bpy
from mathutils import Matrix, Vector
from blender_kit import (
    common_parser, script_argv, clear_scene, configure_render, render,
    make_material, shade_smooth, add_sky_world, print_scene_summary,
    iter_fcurves,
)

WALK_DISTANCE = 1.2   # body forward travel over the shot (m)
PELVIS_Z = 0.45       # pelvis / hip height (m)
LEG_LEN = 0.45
SWING_DEG = 25.0


# ---------------------------------------------------------------------------
# Build the static scene. Return context dict for animate() + probe().
# ---------------------------------------------------------------------------

def build_scene():
    clear_scene()

    # Ground plane
    bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, 0))
    plane = bpy.context.active_object
    plane.name = "Ground"
    plane.data.materials.append(
        make_material("GroundMat", (0.20, 0.22, 0.24), roughness=0.85))

    # Body cylinder ~0.92m — origin AT PELVIS (0,0,0.45), mesh spans 0..0.92 above origin
    # (NOTE: primitive_capsule_add does not exist in this Blender 5.2 build)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.16, depth=0.92,
                                        location=(0, 0, PELVIS_Z + 0.46))
    body = bpy.context.active_object
    body.name = "Body"
    body.data.transform(Matrix.Translation((0, 0, 0.46)))  # mesh: 0..0.92 local
    body.location = (0, 0, PELVIS_Z)                       # origin at pelvis
    shade_smooth(body)
    body.data.materials.append(
        make_material("BodyMat", (0.95, 0.35, 0.15), roughness=0.4))

    # Legs — origin AT HIP (pelvis height), mesh spans 0..-LEG_LEN below origin
    legs = {}
    for side, x in (("L", -0.09), ("R", 0.09)):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.07, depth=LEG_LEN,
                                            location=(x, 0, PELVIS_Z - LEG_LEN / 2))
        leg = bpy.context.active_object
        leg.name = f"Leg{side}"
        leg.data.transform(Matrix.Translation((0, 0, -LEG_LEN / 2)))  # mesh: -0.45..0
        leg.location = (x, 0, PELVIS_Z)                               # origin at hip
        shade_smooth(leg)
        leg.data.materials.append(
            make_material(f"LegMat{side}", (0.85, 0.30, 0.10), roughness=0.5))
        # Parent leg to body (keep world pose) so legs TRAVEL with the body
        leg.parent = body
        leg.matrix_parent_inverse = body.matrix_world.inverted()
        legs[side] = leg

    # Sun + area fill
    bpy.ops.object.light_add(type='SUN', location=(4, -4, 6))
    sun = bpy.context.active_object
    sun.name = "KeyLight"
    sun.data.energy = 3.0
    sun.rotation_euler = (math.radians(55), 0, math.radians(35))

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
        "body": body,
        "legL": legs["L"],
        "legR": legs["R"],
        "leg_len": LEG_LEN,
    }


# ---------------------------------------------------------------------------
# Animation: 2 steps over 24 frames, LINEAR interpolation everywhere.
# Legs swing about the hip (origin) ±25°; body advances 1.2m + z bob.
# ---------------------------------------------------------------------------

def animate(ctx, *, start_frame=1, n_frames=24):
    scene = bpy.context.scene
    scene.frame_start = start_frame
    scene.frame_end = start_frame + n_frames - 1

    body = ctx["body"]
    legL = ctx["legL"]
    legR = ctx["legR"]

    swing = math.radians(SWING_DEG)
    q = n_frames / 4.0  # quarter-cycle spacing
    f1, f2, f3, f4, f5 = (int(start_frame),
                          int(start_frame + q),
                          int(start_frame + 2 * q),
                          int(start_frame + 3 * q),
                          int(start_frame + n_frames - 1))

    # Body: forward march + slight bob (z lowest at contacts, highest mid-swing)
    body_path = [
        (f1, 0.0, PELVIS_Z),
        (f2, WALK_DISTANCE * 0.25, PELVIS_Z + 0.02),
        (f3, WALK_DISTANCE * 0.5, PELVIS_Z),
        (f4, WALK_DISTANCE * 0.75, PELVIS_Z + 0.02),
        (f5, WALK_DISTANCE, PELVIS_Z),
    ]
    for f, x, z in body_path:
        scene.frame_set(f)
        body.location = (x, 0, z)
        body.keyframe_insert("location")

    # Legs: opposite-phase swing about the hip, full cycle over the shot.
    # Swing axis = Y (travel is +X): rotation about X would swing legs sideways.
    leg_phase = {
        legL: [(f1, swing), (f3, -swing), (f5, swing)],
        legR: [(f1, -swing), (f3, swing), (f5, -swing)],
    }
    for leg, keys in leg_phase.items():
        for f, ang in keys:
            scene.frame_set(f)
            leg.rotation_euler = (0, ang, 0)
            leg.keyframe_insert("rotation_euler", index=1)

    # LAW (gotcha 16/17): force LINEAR interpolation on every keyframe
    for obj in (body, legL, legR):
        if obj.animation_data and obj.animation_data.action:
            for fcurve in iter_fcurves(obj.animation_data.action):
                for kp in fcurve.keyframe_points:
                    kp.interpolation = 'LINEAR'

    scene.frame_set(start_frame)


# ---------------------------------------------------------------------------
# Programmatic motion probe (law 110: live-read with frame_set + update)
# ---------------------------------------------------------------------------

def probe(ctx):
    scene = bpy.context.scene
    print("T4PROBE begin")
    for f in (1, 6, 12, 18, 24):
        scene.frame_set(f)
        bpy.context.view_layer.update()
        b = ctx["body"].matrix_world.translation
        tip_l = ctx["legL"].matrix_world @ Vector((0, 0, -ctx["leg_len"]))
        tip_r = ctx["legR"].matrix_world @ Vector((0, 0, -ctx["leg_len"]))
        print(f"T4PROBE f={f} body=({b.x:.4f},{b.y:.4f},{b.z:.4f}) "
              f"tipL=({tip_l.x:.4f},{tip_l.y:.4f},{tip_l.z:.4f}) "
              f"tipR=({tip_r.x:.4f},{tip_r.y:.4f},{tip_r.z:.4f})")
    scene.frame_set(1)
    print("T4PROBE end")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main():
    p = common_parser()
    args = p.parse_args(script_argv())
    print(f"[t4_walk] args: {args}")
    ctx = build_scene()
    animate(ctx, start_frame=args.start, n_frames=args.frames)
    probe(ctx)
    configure_render(args)
    print_scene_summary(args.scene_name)
    render(args, scene_name=args.scene_name)


if __name__ == "__main__":
    main()
