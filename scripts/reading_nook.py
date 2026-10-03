"""
reading_nook.py — usability study R1 scenario (session-5 dog-food).

A reading nook vignette composed from primitives, following the
AGENTS.md canonical workflow: build with hand-estimated z, then let the
patch chain do all real placement (place_on/seat_at/audit).

Props: floor, round rug, armchair (seat/back/2 arms), cushion, side
table + mug, book stack, floor lamp. Animation: mug slides 15cm across
the side table.

Usage:
    ./scripts/blrun.sh --background --python scripts/reading_nook.py -- \
        --output output/reading_nook --dry-run --scene-name reading_nook
    ./scripts/blrun.sh --background --python scripts/look.py -- \
        --scene reading_nook --output output/reading_nook/look
"""
import math

import bpy

from blender_kit import (
    common_parser, script_argv, clear_scene, make_material, shade_smooth,
    add_sky_world, print_scene_summary, configure_render, render,
)


def _mat(name, rgba, rough=0.6):
    return make_material(name, rgba, roughness=rough)


def build_scene():
    clear_scene()

    # Floor
    bpy.ops.mesh.primitive_plane_add(size=16, location=(0, 0, 0))
    floor = bpy.context.active_object
    floor.name = "Floor"
    floor.data.materials.append(_mat("FloorMat", (0.30, 0.28, 0.25), 0.85))

    # Round rug — laid at floor level (half-embed intent)
    bpy.ops.mesh.primitive_cylinder_add(radius=1.3, depth=0.02,
                                        location=(0.2, 0.3, 0.01))
    rug = bpy.context.active_object
    rug.name = "Rug"
    rug.data.materials.append(_mat("RugMat", (0.45, 0.18, 0.22), 0.95))

    # Armchair (composed) — hand-estimated z for now; patch chain will place
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0.0, 0.5, 0.25))
    seat = bpy.context.active_object
    seat.name = "ChairSeat"
    seat.scale = (0.62, 0.55, 0.16)
    seat.data.materials.append(_mat("FabricBlue", (0.16, 0.28, 0.45), 0.9))

    bpy.ops.mesh.primitive_cube_add(size=1, location=(0.0, 0.78, 0.55))
    back = bpy.context.active_object
    back.name = "ChairBack"
    back.scale = (0.62, 0.14, 0.55)
    back.data.materials.append(_mat("FabricBlue", (0.16, 0.28, 0.45), 0.9))

    bpy.ops.mesh.primitive_cube_add(size=1, location=(-0.36, 0.5, 0.38))
    arm_l = bpy.context.active_object
    arm_l.name = "ChairArmL"
    arm_l.scale = (0.11, 0.55, 0.22)
    arm_l.data.materials.append(_mat("FabricBlue", (0.16, 0.28, 0.45), 0.9))

    bpy.ops.mesh.primitive_cube_add(size=1, location=(0.36, 0.5, 0.38))
    arm_r = bpy.context.active_object
    arm_r.name = "ChairArmR"
    arm_r.scale = (0.11, 0.55, 0.22)
    arm_r.data.materials.append(_mat("FabricBlue", (0.16, 0.28, 0.45), 0.9))

    # Cushion (to be seat_at'd onto the chair via anchor)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(1.2, -1.0, 0.06))
    cushion = bpy.context.active_object
    cushion.name = "Cushion"
    cushion.scale = (0.42, 0.42, 0.10)
    cushion.data.materials.append(_mat("FabricAmber", (0.75, 0.55, 0.25), 0.95))

    # Side table: leg + top
    bpy.ops.mesh.primitive_cylinder_add(radius=0.05, depth=0.55,
                                        location=(1.15, 0.45, 0.275))
    leg = bpy.context.active_object
    leg.name = "TableLeg"
    leg.data.materials.append(_mat("WoodDark", (0.35, 0.24, 0.15), 0.6))

    bpy.ops.mesh.primitive_cylinder_add(radius=0.30, depth=0.04,
                                        location=(1.15, 0.45, 0.57))
    table_top = bpy.context.active_object
    table_top.name = "TableTop"
    table_top.data.materials.append(_mat("WoodDark", (0.35, 0.24, 0.15), 0.6))

    # Mug on the table
    bpy.ops.mesh.primitive_cylinder_add(radius=0.05, depth=0.10,
                                        location=(1.15, 0.45, 0.64))
    mug = bpy.context.active_object
    mug.name = "Mug"
    mug.data.materials.append(_mat("MugRed", (0.70, 0.15, 0.12), 0.35))

    # Book stack on the chair seat
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0.0, 0.5, 0.36))
    book1 = bpy.context.active_object
    book1.name = "Book1"
    book1.scale = (0.22, 0.30, 0.03)
    book1.rotation_euler = (0, 0, math.radians(8))
    book1.data.materials.append(_mat("BookGreen", (0.15, 0.40, 0.25), 0.7))

    bpy.ops.mesh.primitive_cube_add(size=1, location=(0.03, 0.48, 0.39))
    book2 = bpy.context.active_object
    book2.name = "Book2"
    book2.scale = (0.20, 0.27, 0.03)
    book2.rotation_euler = (0, 0, math.radians(-14))
    book2.data.materials.append(_mat("BookRust", (0.55, 0.25, 0.15), 0.7))

    # Floor lamp: pole + shade
    bpy.ops.mesh.primitive_cylinder_add(radius=0.025, depth=1.45,
                                        location=(-1.0, -0.3, 0.725))
    pole = bpy.context.active_object
    pole.name = "LampPole"
    pole.data.materials.append(_mat("LampMetal", (0.75, 0.72, 0.68), 0.3))

    bpy.ops.mesh.primitive_cone_add(radius1=0.16, radius2=0.10, depth=0.22,
                                    location=(-1.0, -0.3, 1.52))
    shade = bpy.context.active_object
    shade.name = "LampShade"
    shade.data.materials.append(_mat("ShadeCream", (0.85, 0.80, 0.65), 0.8))

    # Lights + camera (from template)
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

    bpy.ops.object.camera_add(location=(3.2, -2.6, 1.9),
                              rotation=(math.radians(68), 0, math.radians(52)))
    cam = bpy.context.active_object
    cam.name = "MainCam"
    cam.data.lens = 42
    bpy.context.scene.camera = cam

    add_sky_world()

    return {"mug": mug.name}


def animate(ctx, *, start_frame=1, n_frames=24):
    scene = bpy.context.scene
    scene.frame_start = start_frame
    scene.frame_end = start_frame + n_frames - 1
    scene.frame_set(start_frame)

    mug = bpy.data.objects[ctx["mug"]]
    end_frame = start_frame + n_frames - 1

    mug.keyframe_insert(data_path="location", frame=start_frame)
    mug.location.x += 0.15
    mug.keyframe_insert(data_path="location", frame=end_frame)
    scene.frame_set(start_frame)


if __name__ == "__main__":
    p = common_parser()
    args = p.parse_args(script_argv())
    ctx = build_scene()
    animate(ctx, start_frame=args.start, n_frames=args.frames)
    configure_render(args)
    print_scene_summary(args.scene_name)
    render(args, scene_name=args.scene_name)
