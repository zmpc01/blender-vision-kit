"""
scene_dense_crowd.py — T6 dense-scene vision test fixture.

A "crowd-like" field of 120 capsule-ish agents (cylinder body r=0.18 h=0.9
+ sphere head r=0.12, JOINED into one object per agent — primitive_capsule
does not exist on 5.2.2 per AGENTS.md law 11b/119) on a jittered 12x10 grid
across 12x12m, on a 20x20m ground plane. 3 color groups (40 red / 40 green
/ 40 blue bodies — color laws 37/38). Deterministic: random.seed(7).

agent_077 is deliberately FLOATING 0.4m above the ground (planted floater).

Usage:
    ./scripts/blrun.sh --background --python scripts/scene_dense_crowd.py -- \
        --output output/scene_dense_crowd --dry-run --scene-name scene_dense_crowd
    ./scripts/blrun.sh --background --python scripts/look.py -- \
        --scene scene_dense_crowd --output output/scene_dense_crowd/look
"""
import math
import random
import bpy
from blender_kit import (
    common_parser, script_argv, clear_scene, configure_render,
    make_material, shade_smooth, add_sky_world, print_scene_summary, render,
)

N_AGENTS = 120
COLS, ROWS = 12, 10            # 12 x 10 grid across 12 x 12 m
FIELD = 12.0
JITTER = 0.35                  # meters, seeded
FLOATER_ID = "agent_077"
FLOATER_LIFT = 0.4             # meters above ground (deliberate defect)

BODY_R, BODY_H = 0.18, 0.9
HEAD_R = 0.12

COLOR_GROUPS = [
    ("AgentRed",   (0.85, 0.15, 0.12), range(0, 40)),
    ("AgentGreen", (0.15, 0.65, 0.20), range(40, 80)),
    ("AgentBlue",  (0.15, 0.35, 0.90), range(80, 120)),
]


def _group_of(i):
    for name, rgb, span in COLOR_GROUPS:
        if i in span:
            return name, rgb
    return COLOR_GROUPS[-1][0], COLOR_GROUPS[-1][1]


def build_scene():
    clear_scene()

    # Ground plane 20x20 m (neutral achromatic value ladder — law 37)
    bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, 0))
    ground = bpy.context.active_object
    ground.name = "Ground"
    ground.data.materials.append(
        make_material("GroundMat", (0.45, 0.46, 0.48), roughness=0.85))

    # 3 shared chromatic materials (law 38: one color per body, 3 classes)
    mats = {}
    for name, rgb, _span in COLOR_GROUPS:
        mats[name] = make_material(name, rgb, roughness=0.5)

    rng = random.Random(7)     # deterministic placement (brief: seed 7)
    agents = {}
    for i in range(N_AGENTS):
        col, row = i % COLS, i // COLS
        x = -FIELD / 2 + (col + 0.5) * (FIELD / COLS) + rng.uniform(-JITTER, JITTER)
        y = -FIELD / 2 + (row + 0.5) * (FIELD / ROWS) + rng.uniform(-JITTER, JITTER)
        lifted = (i == 77)
        z_body = 0.45 + (FLOATER_LIFT if lifted else 0.0)

        # body: cylinder r=0.18 h=0.9, bottom resting on z=0 (center z=0.45)
        bpy.ops.mesh.primitive_cylinder_add(
            radius=BODY_R, depth=BODY_H, location=(x, y, z_body),
            vertices=24)
        body = bpy.context.active_object
        body.name = f"agent_{i:03d}"
        shade_smooth(body)

        # head: sphere r=0.12 tangent on top of the cylinder
        bpy.ops.mesh.primitive_uv_sphere_add(
            radius=HEAD_R, segments=24, ring_count=12,
            location=(x, y, z_body + BODY_H / 2 + HEAD_R))
        head = bpy.context.active_object
        shade_smooth(head)

        # JOIN head into body -> one object per agent (clean manifest id)
        bpy.ops.object.select_all(action='DESELECT')
        head.select_set(True)
        body.select_set(True)
        bpy.context.view_layer.objects.active = body
        bpy.ops.object.join()

        _, rgb = _group_of(i)
        body.data.materials.append(mats[_group_of(i)[0]])
        body["kit_color"] = rgb
        agents[body.name] = body

    # Neutral key light + fill (law 39: light bases stay neutral)
    bpy.ops.object.light_add(type='SUN', location=(4, -4, 6))
    sun = bpy.context.active_object
    sun.name = "KeyLight"
    sun.data.energy = 3.0
    sun.rotation_euler = (math.radians(55), math.radians(15), math.radians(35))

    bpy.ops.object.light_add(type='AREA', location=(-6, -8, 6))
    fill = bpy.context.active_object
    fill.name = "FillLight"
    fill.data.energy = 300.0
    fill.data.size = 8.0

    # Camera (look.py/viewport_capture use their own cameras; this is for
    # the shipped still)
    bpy.ops.object.camera_add(location=(9, -9, 5.5),
                              rotation=(math.radians(65), 0, math.radians(45)))
    cam = bpy.context.active_object
    cam.name = "MainCam"
    cam.data.lens = 35
    bpy.context.scene.camera = cam

    add_sky_world()

    return {"agents": agents, "floater": FLOATER_ID}


def animate(ctx, *, start_frame=1, n_frames=24):
    # Static scene — no-op is legal per AGENTS.md quick-start note.
    scene = bpy.context.scene
    scene.frame_start = start_frame
    scene.frame_end = start_frame + n_frames - 1
    scene.frame_set(start_frame)


def main():
    p = common_parser()
    args = p.parse_args(script_argv())
    print(f"[scene_dense_crowd] args: {args}")
    ctx = build_scene()
    animate(ctx, start_frame=args.start, n_frames=args.frames)
    configure_render(args)
    print_scene_summary(args.scene_name)
    render(args, scene_name=args.scene_name)


if __name__ == "__main__":
    main()
