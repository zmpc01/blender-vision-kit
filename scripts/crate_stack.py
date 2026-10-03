"""
crate_stack.py — usability study R2 scenario (session-5 dog-food, R2).

Physics-lane exercise (R1 covered static composition + one animated
slide): pallet + crates placed via physics ops, one deliberately
overhanging crate for physics_oracle to witness, physics_gate as the
scene-level rejection gate, then look/closeup/schema per the workflow.

Usage:
    ./scripts/blrun.sh --background --python scripts/crate_stack.py -- \
        --output output/crate_stack --dry-run --scene-name crate_stack
    ./scripts/blrun.sh --background --python scripts/look.py -- \
        --scene crate_stack --output output/crate_stack/look
"""
import math

import bpy

from blender_kit import (
    common_parser, script_argv, clear_scene, make_material,
    add_sky_world, print_scene_summary, configure_render, render,
)


def build_scene():
    clear_scene()

    bpy.ops.mesh.primitive_plane_add(size=14, location=(0, 0, 0))
    floor = bpy.context.active_object
    floor.name = "Floor"
    floor.data.materials.append(
        make_material("FloorMat", (0.28, 0.27, 0.26), roughness=0.9))

    # Pallet: flat slab on three runner blocks (composed)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0.07))
    deck = bpy.context.active_object
    deck.name = "PalletDeck"
    deck.scale = (1.2, 0.9, 0.04)
    deck.data.materials.append(
        make_material("PalletWood", (0.62, 0.48, 0.30), roughness=0.8))

    for i, (rx, ry) in enumerate([(-0.5, 0.0), (0.5, 0.0), (0.0, 0.38)]):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(rx, ry, 0.025))
        runner = bpy.context.active_object
        runner.name = f"PalletRunner{i+1}"
        runner.scale = (0.08, 0.9 if i < 2 else 0.08, 0.05)
        if i == 2:
            runner.scale = (1.2, 0.08, 0.05)
        runner.data.materials.append(
            make_material("PalletWood", (0.62, 0.48, 0.30), roughness=0.8))

    # Crates — hand-dumped near the pallet; physics will find their pose
    specs = [("CrateA", (-0.35, 0.0, 0.6), 0.34),
             ("CrateB", (0.30, 0.05, 0.6), 0.30),
             ("CrateC", (0.05, 0.42, 0.95), 0.26)]
    for name, loc, s in specs:
        bpy.ops.mesh.primitive_cube_add(size=s, location=loc)
        crate = bpy.context.active_object
        crate.name = name
        crate.rotation_euler = (0, 0, 0.15)
        crate.data.materials.append(
            make_material(f"{name}Mat", (0.72, 0.52, 0.20), roughness=0.75))

    # Overhang prop: a small box deliberately hanging half off the deck
    bpy.ops.mesh.primitive_cube_add(size=0.2, location=(0.72, -0.3, 0.25))
    tip = bpy.context.active_object
    tip.name = "TipBox"
    tip.data.materials.append(
        make_material("TipMat", (0.55, 0.20, 0.15), roughness=0.7))

    # Lights + camera
    bpy.ops.object.light_add(type='SUN', location=(3, -3, 5))
    sun = bpy.context.active_object
    sun.name = "KeyLight"
    sun.data.energy = 3.0
    sun.rotation_euler = (math.radians(50), math.radians(10), math.radians(30))

    bpy.ops.object.light_add(type='AREA', location=(-2, -2, 3))
    fill = bpy.context.active_object
    fill.name = "FillLight"
    fill.data.energy = 120.0
    fill.data.size = 2.5

    bpy.ops.object.camera_add(location=(2.6, -2.2, 1.7),
                              rotation=(math.radians(66), 0, math.radians(49)))
    cam = bpy.context.active_object
    cam.name = "MainCam"
    cam.data.lens = 45
    bpy.context.scene.camera = cam

    add_sky_world()
    return {}


def animate(ctx, *, start_frame=1, n_frames=24):
    scene = bpy.context.scene
    scene.frame_start = start_frame
    scene.frame_end = start_frame + n_frames - 1
    scene.frame_set(start_frame)


if __name__ == "__main__":
    p = common_parser()
    args = p.parse_args(script_argv())
    ctx = build_scene()
    animate(ctx, start_frame=args.start, n_frames=args.frames)
    configure_render(args)
    print_scene_summary(args.scene_name)
    render(args, scene_name=args.scene_name)
