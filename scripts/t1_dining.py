"""
t1_dining.py — T1 placement usability scene.

Table (1.6 x 0.9 top, height 0.75) + 4 stool chairs (spawned aside, to be
seated via patch ops) + lamp (spawned aside, to be placed ON tabletop via
patch) + mug (spawned aside, to be snapped to z=0.75 via patch).

Usage:
    blrun.sh --background --python scripts/t1_dining.py -- \
        --output output/t1 --dry-run --scene-name t1_dining
"""
import math
import bpy
from blender_kit import (
    common_parser, script_argv, clear_scene, configure_render, render,
    make_material, add_sky_world, print_scene_summary,
)


def build_scene():
    clear_scene()

    # Ground plane
    bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, 0))
    plane = bpy.context.active_object
    plane.name = "Ground"
    plane.data.materials.append(
        make_material("GroundMat", (0.20, 0.22, 0.24), roughness=0.85))

    # --- Table: top 1.6 x 0.9 x 0.05, top surface at z=0.75 ---
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0.725))
    top = bpy.context.active_object
    top.name = "TableTop"
    top.scale = (1.6, 0.9, 0.05)
    top.data.materials.append(
        make_material("WoodMat", (0.55, 0.38, 0.20), roughness=0.6))

    leg_h = 0.725
    for i, (sx, sy) in enumerate([(-1, -1), (1, -1), (-1, 1), (1, 1)], 1):
        bpy.ops.mesh.primitive_cube_add(
            size=1, location=(sx * 0.7, sy * 0.35, leg_h / 2))
        leg = bpy.context.active_object
        leg.name = f"TableLeg{i}"
        leg.scale = (0.06, 0.06, leg_h)
        leg.data.materials.append(
            make_material("WoodDarkMat", (0.35, 0.24, 0.13), roughness=0.7))

    # --- 4 chairs (stools 0.4 x 0.4 x 0.45), spawned aside in a row ---
    for i, y in enumerate((-1.2, -0.4, 0.4, 1.2), 1):
        bpy.ops.mesh.primitive_cube_add(
            size=1, location=(2.6, y, 0.225))
        chair = bpy.context.active_object
        chair.name = f"Chair{i}"
        chair.scale = (0.4, 0.4, 0.45)
        chair.data.materials.append(
            make_material(f"ChairMat{i}", (0.85, 0.30, 0.20), roughness=0.5))

    # --- Lamp (small cylinder base + cone shade, joined), spawned aside ---
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.06, depth=0.02, location=(2.6, 1.8, 0.01))
    base = bpy.context.active_object
    base.name = "LampBase"
    base.data.materials.append(
        make_material("LampMat", (0.15, 0.15, 0.18), roughness=0.4, metallic=0.5))
    bpy.ops.mesh.primitive_cone_add(
        radius1=0.09, radius2=0.02, depth=0.12, location=(2.6, 1.8, 0.08))
    shade = bpy.context.active_object
    shade.name = "LampShade"
    shade.data.materials.append(
        make_material("ShadeMat", (0.90, 0.75, 0.35), roughness=0.6))
    bpy.ops.object.select_all(action='DESELECT')
    base.select_set(True)
    shade.select_set(True)
    bpy.context.view_layer.objects.active = base
    bpy.ops.object.join()
    lamp = bpy.context.active_object
    lamp.name = "Lamp"

    # --- Mug (cylinder r=0.04 h=0.1), spawned aside on the floor ---
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.04, depth=0.1, location=(2.6, 2.4, 0.05))
    mug = bpy.context.active_object
    mug.name = "Mug"
    mug.data.materials.append(
        make_material("MugMat", (0.85, 0.85, 0.90), roughness=0.3))

    # Light + world
    bpy.ops.object.light_add(type='SUN', location=(4, -4, 6))
    sun = bpy.context.active_object
    sun.name = "KeyLight"
    sun.data.energy = 3.0
    sun.rotation_euler = (math.radians(55), 0, math.radians(35))

    add_sky_world()

    return {"top": top, "lamp": lamp}


def animate(ctx, *, start_frame=1, n_frames=24):
    # Static scene — no animation (placement ops refuse animated movers).
    bpy.context.scene.frame_start = start_frame
    bpy.context.scene.frame_end = start_frame + n_frames - 1
    bpy.context.scene.frame_set(start_frame)


def main():
    p = common_parser()
    args = p.parse_args(script_argv())
    print(f"[t1_dining] args: {args}")
    ctx = build_scene()
    animate(ctx, start_frame=args.start, n_frames=args.frames)
    configure_render(args)
    print_scene_summary(args.scene_name)
    render(args, scene_name=args.scene_name)


if __name__ == "__main__":
    main()
