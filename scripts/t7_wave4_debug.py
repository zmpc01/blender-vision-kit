"""
t7_wave4_debug.py — T7 wave-4 fixture: THREE planted condition classes
(vision-kit M5 wave-4 usability/debug vehicle).

A 4-prop mini scene, 40 frames, each prop exercises one detection path:

  - Door:   slides up f10-14 (opens), holds, closes f26-30 — NORMAL motion
  - Lamp:   rests on the Table f1-9, then SINKS THROUGH the tabletop
            f12-16 (intersects it), recovers by f20 — planted bug A:
            a short-window INTERSECTION transient (validator state radar)
  - Crate:  slides along the ground, then TELEPORTS +2m instantly at
            f23 (single-frame jump) — planted bug B: a POP (change
            radar / motion-table POP-FRAMES; validator sees nothing)
  - Hover:  an orb that hovers 0.8m above the ground for the WHOLE range
            (by design) — PERSISTENT baseline P1 floating: tests that
            the scan classifies it as baseline, NOT a transient

Usage:
    blrun.sh --background --python scripts/t7_wave4_debug.py -- \
        --output output/t7_wave4 --dry-run --scene-name t7_wave4
"""
import bpy
from mathutils import Matrix

from blender_kit import (
    common_parser, script_argv, clear_scene, make_material, shade_smooth,
    print_scene_summary, configure_render, render, iter_fcurves,
)


def build_scene():
    clear_scene()

    bpy.ops.mesh.primitive_plane_add(size=24, location=(0, 0, 0))
    ground = bpy.context.active_object
    ground.name = "Ground"
    ground.data.materials.append(
        make_material("GroundMat", (0.20, 0.22, 0.24), roughness=0.85))

    # Table: top slab at z=0.75. Mesh spans 0..1 local (data.transform),
    # scale z=0.75 -> world z 0..0.75 with LOCATION Z=0 (not 0.375: the
    # +0.5 data transform + scale already lift it — measured: z=0.375
    # made the table FLOAT 0.375m, polluting the fixture's own baseline)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
    table = bpy.context.active_object
    table.name = "Table"
    table.scale = (1.2, 0.8, 0.75)
    table.data.transform(Matrix.Translation((0, 0, 0.5)))  # mesh: 0..1 local
    table.data.materials.append(
        make_material("TableMat", (0.55, 0.38, 0.20), roughness=0.6))

    # Door: 0.9 wide, 2.0 tall panel sliding up (a gate)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(-2.5, 0, 1.0))
    door = bpy.context.active_object
    door.name = "Door"
    door.scale = (0.1, 0.9, 2.0)
    door.data.materials.append(
        make_material("DoorMat", (0.15, 0.45, 0.85), roughness=0.5))

    # Lamp: small cylinder that RESTS on the table (base z = tabletop 0.75)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.12, depth=0.35,
                                        location=(0.2, 0.1, 0.925))
    lamp = bpy.context.active_object
    lamp.name = "Lamp"
    shade_smooth(lamp)
    lamp.data.materials.append(
        make_material("LampMat", (0.95, 0.80, 0.20), roughness=0.4))

    # Crate: 0.4 box sliding along +X on the ground
    bpy.ops.mesh.primitive_cube_add(size=0.4, location=(-1.0, 1.4, 0.2))
    crate = bpy.context.active_object
    crate.name = "Crate"
    crate.data.materials.append(
        make_material("CrateMat", (0.65, 0.45, 0.15), roughness=0.7))

    # Hover: 0.25 sphere hovering at z=0.925 all range (by design)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.125, segments=24,
                                         ring_count=16,
                                         location=(2.2, -1.0, 0.925))
    hover = bpy.context.active_object
    hover.name = "Hover"
    shade_smooth(hover)
    hover.data.materials.append(
        make_material("HoverMat", (0.55, 0.20, 0.80), roughness=0.5))

    print_scene_summary()
    return {"table": table, "door": door, "lamp": lamp,
            "crate": crate, "hover": hover}


def animate(ctx, start_frame=1, n_frames=40):
    scene = bpy.context.scene
    scene.frame_start = start_frame
    scene.frame_end = start_frame + n_frames - 1
    s, e = start_frame, start_frame + n_frames - 1
    door, lamp, crate = ctx["door"], ctx["lamp"], ctx["crate"]

    # Door: closed -> open (f10-14) -> hold -> close (f26-30)
    door.location = (-2.5, 0, 1.0)
    door.keyframe_insert("location", frame=s + 9)
    door.location = (-2.5, 0, 3.1)
    door.keyframe_insert("location", frame=s + 13)
    door.keyframe_insert("location", frame=s + 25)
    door.location = (-2.5, 0, 1.0)
    door.keyframe_insert("location", frame=s + 29)

    # Lamp: rests on table -> SINKS THROUGH tabletop f12-16 -> recovers f20
    # tabletop surface at z=0.75; lamp center rest = 0.925; sunk center =
    # 0.55 (lamp body z 0.375..0.725 — fully inside the table slab)
    lamp.location = (0.2, 0.1, 0.925)
    lamp.keyframe_insert("location", frame=s + 9)
    lamp.location = (0.2, 0.1, 0.55)
    lamp.keyframe_insert("location", frame=s + 14)
    lamp.location = (0.2, 0.1, 0.925)
    lamp.keyframe_insert("location", frame=s + 19)

    # Crate: steady slide, then TELEPORT +2m at f22 (one-frame jump)
    crate.location = (-1.0, 1.4, 0.2)
    crate.keyframe_insert("location", frame=s + 1)
    crate.location = (0.5, 1.4, 0.2)
    crate.keyframe_insert("location", frame=s + 21)
    crate.location = (2.5, 1.4, 0.2)          # instant +2m jump
    crate.keyframe_insert("location", frame=s + 22)
    crate.location = (3.5, 1.4, 0.2)
    crate.keyframe_insert("location", frame=e)

    # Hover: static (its floating is DESIGN — persistent baseline)

    for ob in (door, lamp, crate):
        if ob.animation_data and ob.animation_data.action:
            for fc in iter_fcurves(ob.animation_data.action):
                for kp in fc.keyframe_points:
                    kp.interpolation = 'LINEAR'
    return ctx


def probe(ctx):
    print("[t7] T7 wave-4 fixture: Lamp table-intersection transient "
          "f10-18 (worst f14-15), Crate teleport pop at f23 (keys f22->f23), Hover "
          "persistent-baseline floating (design)")


def main():
    p = common_parser()
    args = p.parse_args(script_argv())
    print(f"[t7] args: {args}")
    ctx = build_scene()
    animate(ctx, start_frame=args.start, n_frames=args.frames)
    probe(ctx)
    if args.dry_run:
        print("[t7] --dry-run: scene built in-memory (no render/save)")
        return
    configure_render(args)
    print_scene_summary(args.scene_name)
    render(args, scene_name=args.scene_name)


if __name__ == "__main__":
    main()
