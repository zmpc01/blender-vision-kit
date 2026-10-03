"""
edge_offorigin.py — degenerate-input fixture: ONE object, far off-origin.

Edge-suite target (HANDOFF gap C): a single small cube at (9, -6, 0.5)
exercises look.py subject detection + framing when the scene bbox center
is nowhere near the world origin and the bbox is tiny (no ground plane).
Framing must still find and center the subject; annotations must be
legible at that distance.

Usage:
    ./scripts/blrun.sh --background --python scripts/look.py -- \
        --scene edge_offorigin --output output/edges/look_offorigin
"""
import bpy

from blender_kit import common_parser, script_argv, clear_scene, make_material


def build_scene():
    clear_scene()
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(9.0, -6.0, 0.5))
    cube = bpy.context.active_object
    cube.name = "LoneCube"
    cube.data.materials.append(
        make_material("LoneMat", (0.85, 0.45, 0.15), roughness=0.4))
    return {"cube": cube.name}


def animate(ctx, *, start_frame=1, n_frames=24):
    pass


if __name__ == "__main__":
    argv = script_argv()
    parser = common_parser()
    args = parser.parse_args(argv)
    build_scene()
