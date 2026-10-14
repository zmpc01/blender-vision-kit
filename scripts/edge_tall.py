"""
edge_tall.py — degenerate-input fixture: extreme TALL aspect ratio.

Edge-suite target (HANDOFF gap C): a 0.15 x 0.15 x 6 m tower (40:1
vertical). Elevation-style angles must frame the full height; the top
angle sees a dot. Companion to edge_wide.

Usage:
    ./scripts/blrun.sh --background --python scripts/look.py -- \
        --scene edge_tall --output output/edges/look_tall
"""
import bpy

from blender_kit import common_parser, script_argv, clear_scene, make_material


def build_scene():
    clear_scene()
    # s17: the tower HOVERS 300mm above the ground (bottom z = 0.3). At the
    # old z=3.0 the bottom sat EXACTLY on the ground plane — legitimately
    # seated, so the v3_edges C4 floating-law check was red-by-construction
    # (masked all session-16 by the rc=90 lock failures). Hovering is what
    # the suite's intent describes: a lone tower with NOTHING below it.
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.0, 0.0, 3.3))
    tower = bpy.context.active_object
    tower.name = "Tower"
    tower.scale = (0.15, 0.15, 6.0)
    tower.data.materials.append(
        make_material("TallMat", (0.75, 0.25, 0.45), roughness=0.4))
    return {"tower": tower.name}


def animate(ctx, *, start_frame=1, n_frames=24):
    pass


if __name__ == "__main__":
    argv = script_argv()
    parser = common_parser()
    args = parser.parse_args(argv)
    build_scene()
