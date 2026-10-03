"""
edge_anim.py — degenerate-input fixture: a NORMAL 24-frame animation
used to probe motion_study / transient_scan with DEGENERATE frame
sweeps (--frames 1, --frames 2).

Edge-suite target (HANDOFF gap D): 1-frame timelines have no adjacent
pairs to diff — the scan must fail CLEAN (one-line reason) or degrade
gracefully, never traceback. 2-frame timelines have exactly one diff —
MAD floor is degenerate but defined.

Usage:
    ./scripts/blrun.sh --background --python scripts/motion_study.py -- \
        --scene edge_anim --frames 1 --out output/edges/motion_f1
"""
import math

import bpy

from blender_kit import (
    common_parser, script_argv, clear_scene, make_material,
)


def build_scene():
    clear_scene()
    bpy.ops.mesh.primitive_plane_add(size=12, location=(0, 0, 0))
    ground = bpy.context.active_object
    ground.name = "Ground"
    ground.data.materials.append(
        make_material("GroundMat", (0.20, 0.22, 0.24), roughness=0.85))

    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.3, location=(-2, 0, 0.3))
    ball = bpy.context.active_object
    ball.name = "Roller"
    ball.data.materials.append(
        make_material("RollerMat", (0.85, 0.55, 0.15), roughness=0.35))
    ball.keyframe_insert(data_path="location", frame=1)
    ball.location = (2.0, 0.0, 0.3)
    ball.keyframe_insert(data_path="location", frame=24)
    return {"ball": ball.name}


def animate(ctx, *, start_frame=1, n_frames=24):
    pass


if __name__ == "__main__":
    argv = script_argv()
    parser = common_parser("edge_anim — animation fixture for frame-edge sweeps")
    args = parser.parse_args(argv)
    build_scene()
