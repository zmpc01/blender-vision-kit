"""
scene_interior_room.py — interior room scene with furniture for previz.

A more complex previz use case: a furnished living room with walls, floor,
ceiling, sofa, coffee table, TV unit, rug, and a window. Tests the kit's
ability to handle precise placement, spatial relationships, and visual
verification through viewport captures + VLM.

Usage:
    # Dry-run to inspect scene structure
    blrun.sh --background --python scripts/scene_interior_room.py -- \\
        --output /tmp/room --dry-run --scene-name living_room

    # Quick viewport check (workbench, 4-angle grid)
    blrun.sh --background --python scripts/viewport_capture.py -- \\
        --scene scene_interior_room --output /tmp/room/grid.png \\
        --angles front,side,top,persp --engine workbench

    # Single still with EEVEE_NEXT for VLM iteration
    blrun.sh --background --python scripts/scene_interior_room.py -- \\
        --output /tmp/room --engine BLENDER_EEVEE_NEXT --still 1 \\
        --quality preview --scene-name living_room

    # Full animation (slow camera dolly through the room)
    blrun.sh --background --python scripts/scene_interior_room.py -- \\
        --output /tmp/room --engine BLENDER_EEVEE_NEXT --frames 48 \\
        --quality preview --encode-mp4 --scene-name living_room
"""
import math
import bpy
from blender_kit import (
    common_parser, script_argv, clear_scene, configure_render, render,
    make_material, shade_smooth, add_sky_world, print_scene_summary,
)


# Room dimensions (meters)
ROOM_W = 6.0   # X
ROOM_D = 5.0   # Y
ROOM_H = 3.0   # Z
WALL_T = 0.1   # wall thickness


def build_scene():
    clear_scene()

    # ---- Floor (wood) --------------------------------------------------
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0))
    floor = bpy.context.active_object
    floor.name = "Floor"
    floor.scale = (ROOM_W, ROOM_D, 1)
    floor.data.materials.append(
        make_material("WoodFloor", (0.55, 0.40, 0.25), roughness=0.7))

    # ---- Ceiling -------------------------------------------------------
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, ROOM_H))
    ceiling = bpy.context.active_object
    ceiling.name = "Ceiling"
    ceiling.scale = (ROOM_W, ROOM_D, 1)
    ceiling.data.materials.append(
        make_material("Ceiling", (0.92, 0.92, 0.92), roughness=0.95))

    # ---- Walls (back + left, leave front + right open for camera) -----
    # Back wall (negative Y)
    bpy.ops.mesh.primitive_cube_add(
        size=1, location=(0, -ROOM_D/2 - WALL_T/2, ROOM_H/2))
    back_wall = bpy.context.active_object
    back_wall.name = "WallBack"
    back_wall.scale = (ROOM_W + 2*WALL_T, WALL_T, ROOM_H)
    back_wall.data.materials.append(
        make_material("Wall", (0.85, 0.83, 0.78), roughness=0.9))

    # Left wall (negative X)
    bpy.ops.mesh.primitive_cube_add(
        size=1, location=(-ROOM_W/2 - WALL_T/2, 0, ROOM_H/2))
    left_wall = bpy.context.active_object
    left_wall.name = "WallLeft"
    left_wall.scale = (WALL_T, ROOM_D + 2*WALL_T, ROOM_H)
    left_wall.data.materials.append(
        make_material("Wall", (0.85, 0.83, 0.78), roughness=0.9))

    # ---- Window on back wall ------------------------------------------
    # A simple frame: 4 thin cubes forming a rectangle
    win_w, win_h = 1.6, 1.2
    win_z = 1.4  # center height
    win_y = -ROOM_D/2 - WALL_T/2
    frame_t = 0.06
    frame_mat = make_material("WindowFrame", (0.95, 0.95, 0.95), roughness=0.6)

    # Top + bottom of frame
    for z_offset, name in [(win_z + win_h/2, "WinFrameTop"),
                            (win_z - win_h/2, "WinFrameBot")]:
        bpy.ops.mesh.primitive_cube_add(
            size=1, location=(0, win_y, z_offset))
        o = bpy.context.active_object
        o.name = name
        o.scale = (win_w + 2*frame_t, WALL_T*1.2, frame_t)
        o.data.materials.append(frame_mat)

    # Left + right of frame
    for x_offset, name in [(-win_w/2, "WinFrameL"), (win_w/2, "WinFrameR")]:
        bpy.ops.mesh.primitive_cube_add(
            size=1, location=(x_offset, win_y, win_z))
        o = bpy.context.active_object
        o.name = name
        o.scale = (frame_t, WALL_T*1.2, win_h)
        o.data.materials.append(frame_mat)

    # Window glass (just a slightly transparent bluish plane)
    bpy.ops.mesh.primitive_plane_add(
        size=1, location=(0, win_y, win_z),
        rotation=(math.radians(90), 0, 0))
    glass = bpy.context.active_object
    glass.name = "WindowGlass"
    glass.scale = (win_w, 1, win_h)
    glass_mat = make_material("Glass", (0.6, 0.75, 0.95), roughness=0.05)
    glass.data.materials.append(glass_mat)

    # ---- Sofa (3-seater against back wall) ----------------------------
    sofa_w, sofa_d, sofa_h = 2.4, 0.9, 0.5  # seat dimensions
    sofa_x, sofa_y, sofa_z = 0, -ROOM_D/2 + sofa_d/2, sofa_h/2

    # Base
    bpy.ops.mesh.primitive_cube_add(
        size=1, location=(sofa_x, sofa_y, sofa_z))
    sofa_base = bpy.context.active_object
    sofa_base.name = "SofaBase"
    sofa_base.scale = (sofa_w, sofa_d, sofa_h)
    sofa_mat = make_material("SofaFabric", (0.30, 0.45, 0.55), roughness=0.85)
    sofa_base.data.materials.append(sofa_mat)

    # Backrest
    bpy.ops.mesh.primitive_cube_add(
        size=1, location=(sofa_x, sofa_y - sofa_d/2 + 0.1, sofa_h + 0.3))
    backrest = bpy.context.active_object
    backrest.name = "SofaBackrest"
    backrest.scale = (sofa_w, 0.2, 0.7)
    backrest.data.materials.append(sofa_mat)

    # Arms (left + right)
    for x_off, name in [(-sofa_w/2 + 0.1, "SofaArmL"), (sofa_w/2 - 0.1, "SofaArmR")]:
        bpy.ops.mesh.primitive_cube_add(
            size=1, location=(sofa_x + x_off, sofa_y, sofa_h + 0.15))
        o = bpy.context.active_object
        o.name = name
        o.scale = (0.2, sofa_d, 0.4)
        o.data.materials.append(sofa_mat)

    # ---- Coffee table (in front of sofa) ------------------------------
    # Table top is a thin slab at table_h. Legs support it from below.
    # LEG BUG FIX (session 4 retro): legs were depth=table_h-0.05=0.35,
    # located at z=(table_h-0.05)/2=0.175 → legs span z=[0, 0.35] which
    # pokes THROUGH the table top (z=[0.175, 0.225]) by 0.125m, making
    # the table look upside down. Correct: leg top meets table bottom.
    table_w, table_d, table_h = 1.2, 0.6, 0.4
    top_thickness = 0.05
    table_x = 0
    table_y = sofa_y + sofa_d/2 + 0.8 + table_d/2
    table_top_z = table_h  # top surface at table_h, slab centered at table_h - top_thickness/2
    bpy.ops.mesh.primitive_cube_add(
        size=1, location=(table_x, table_y, table_top_z - top_thickness/2))
    table_top = bpy.context.active_object
    table_top.name = "CoffeeTable"
    table_top.scale = (table_w, table_d, top_thickness)
    table_top.data.materials.append(
        make_material("TableWood", (0.20, 0.15, 0.10), roughness=0.4, metallic=0.0))

    # Table legs (4 cylinders) — leg top at z = table_top_z - top_thickness
    leg_height = table_top_z - top_thickness  # 0.35
    leg_z = leg_height / 2  # 0.175
    for x_off, y_off in [(-table_w/2 + 0.05, -table_d/2 + 0.05),
                         (table_w/2 - 0.05, -table_d/2 + 0.05),
                         (-table_w/2 + 0.05, table_d/2 - 0.05),
                         (table_w/2 - 0.05, table_d/2 - 0.05)]:
        bpy.ops.mesh.primitive_cylinder_add(
            radius=0.03, depth=leg_height,
            location=(table_x + x_off, table_y + y_off, leg_z))
        leg = bpy.context.active_object
        leg.name = f"TableLeg_{x_off:+.2f}_{y_off:+.2f}"
        leg.data.materials.append(
            make_material("TableLeg", (0.15, 0.12, 0.10), roughness=0.4, metallic=0.6))

    # ---- Rug (under coffee table) -------------------------------------
    rug_w, rug_d = 2.6, 1.6
    bpy.ops.mesh.primitive_plane_add(
        size=1, location=(0, table_y, 0.005))
    rug = bpy.context.active_object
    rug.name = "Rug"
    rug.scale = (rug_w, rug_d, 1)
    rug.data.materials.append(
        make_material("Rug", (0.55, 0.30, 0.25), roughness=0.95))

    # ---- TV unit (against left wall, opposite sofa angle) -------------
    tv_w, tv_d, tv_h = 1.6, 0.4, 0.5
    tv_x = -ROOM_W/2 + tv_d/2 + 0.05
    tv_y = 0.5
    bpy.ops.mesh.primitive_cube_add(
        size=1, location=(tv_x, tv_y, tv_h/2))
    tv_unit = bpy.context.active_object
    tv_unit.name = "TVUnit"
    tv_unit.scale = (tv_d, tv_w, tv_h)
    tv_unit.data.materials.append(
        make_material("TVUnit", (0.18, 0.18, 0.20), roughness=0.5))

    # TV screen (flat panel on top)
    screen_w, screen_h = 1.4, 0.8
    bpy.ops.mesh.primitive_cube_add(
        size=1, location=(tv_x - tv_d/2 - 0.03, tv_y, tv_h + screen_h/2 + 0.05))
    screen = bpy.context.active_object
    screen.name = "TVScreen"
    screen.scale = (0.05, screen_w, screen_h)
    screen.data.materials.append(
        make_material("TVScreen", (0.02, 0.02, 0.03), roughness=0.1, metallic=0.8))

    # ---- Floor lamp (corner) -----------------------------------------
    lamp_x, lamp_y = ROOM_W/2 - 0.4, -ROOM_D/2 + 0.4
    bpy.ops.mesh.primitive_cylinder_add(
        radius=0.04, depth=1.6, location=(lamp_x, lamp_y, 0.8))
    lamp_pole = bpy.context.active_object
    lamp_pole.name = "FloorLampPole"
    lamp_pole.data.materials.append(
        make_material("LampMetal", (0.3, 0.3, 0.3), roughness=0.3, metallic=0.9))

    # Lamp shade (cone)
    bpy.ops.mesh.primitive_cone_add(
        radius1=0.2, radius2=0.15, depth=0.3,
        location=(lamp_x, lamp_y, 1.7))
    shade = bpy.context.active_object
    shade.name = "FloorLampShade"
    shade.data.materials.append(
        make_material("LampShade", (0.95, 0.90, 0.75), roughness=0.7))

    # Actual light bulb (point light)
    bpy.ops.object.light_add(
        type='POINT', location=(lamp_x, lamp_y, 1.65))
    lamp_light = bpy.context.active_object
    lamp_light.name = "FloorLampLight"
    lamp_light.data.energy = 60.0
    lamp_light.data.color = (1.0, 0.92, 0.78)

    # ---- Ceiling light ------------------------------------------------
    bpy.ops.object.light_add(
        type='AREA', location=(0, 0, ROOM_H - 0.05))
    ceil_light = bpy.context.active_object
    ceil_light.name = "CeilingLight"
    ceil_light.data.energy = 200.0
    ceil_light.data.size = 1.5
    ceil_light.data.color = (1.0, 0.96, 0.88)

    # ---- Sun light (through window) ----------------------------------
    bpy.ops.object.light_add(
        type='SUN', location=(4, -6, 5))
    sun = bpy.context.active_object
    sun.name = "SunLight"
    sun.data.energy = 2.5
    sun.rotation_euler = (math.radians(55), math.radians(15), math.radians(35))

    # ---- Camera (door position, looking in) ---------------------------
    bpy.ops.object.camera_add(
        location=(ROOM_W/2 + 1.5, ROOM_D/2 + 1.5, 1.7),
        rotation=(math.radians(80), 0, math.radians(225)))
    cam = bpy.context.active_object
    cam.name = "MainCam"
    cam.data.lens = 24  # wide-angle to capture the room
    bpy.context.scene.camera = cam

    # ---- World (sky for window view) ---------------------------------
    add_sky_world(sun_elevation_deg=25, sun_rotation_deg=45, strength=1.5)

    return {
        "camera": cam,
        "room_dims": (ROOM_W, ROOM_D, ROOM_H),
    }


def animate(ctx, *, start_frame=1, n_frames=48):
    """Slow camera dolly through the room: from door position to opposite corner."""
    scene = bpy.context.scene
    scene.frame_start = start_frame
    scene.frame_end = start_frame + n_frames - 1
    scene.frame_set(start_frame)

    cam = ctx["camera"]
    end_frame = start_frame + n_frames - 1

    # Start position (door)
    cam.keyframe_insert("location")
    cam.keyframe_insert("rotation_euler")

    # Mid-point (looking at sofa from center of room)
    mid = start_frame + n_frames // 2
    scene.frame_set(mid)
    cam.location = (0, ROOM_D/2 + 0.5, 1.7)
    cam.rotation_euler = (math.radians(80), 0, math.radians(180))
    cam.keyframe_insert("location")
    cam.keyframe_insert("rotation_euler")

    # End position (looking back from corner near TV)
    scene.frame_set(end_frame)
    cam.location = (-ROOM_W/2 + 0.5, ROOM_D/2 - 0.5, 1.7)
    cam.rotation_euler = (math.radians(80), 0, math.radians(135))
    cam.keyframe_insert("location")
    cam.keyframe_insert("rotation_euler")

    # Smooth easing
    from blender_kit import iter_fcurves
    if cam.animation_data and cam.animation_data.action:
        for fcurve in iter_fcurves(cam.animation_data.action):
            for kp in fcurve.keyframe_points:
                kp.interpolation = 'BEZIER'
                kp.easing = 'EASE_IN_OUT'

    scene.frame_set(start_frame)


def main():
    p = common_parser()
    args = p.parse_args(script_argv())
    print(f"[scene_interior_room] args: {args}")
    ctx = build_scene()
    animate(ctx, start_frame=args.start, n_frames=args.frames)
    configure_render(args)
    print_scene_summary(args.scene_name)
    render(args, scene_name=args.scene_name)


if __name__ == "__main__":
    main()
