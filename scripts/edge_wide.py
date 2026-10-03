"""
edge_wide.py — degenerate-input fixture: extreme WIDE aspect ratio.

Edge-suite target (HANDOFF gap C): nine cubes in a row spanning
x = -7..+7 (14 m wide, 0.4 m deep, no ground plane). The scene bbox is
35:1 — 4-angle framing must keep the row readable in at least the side
and top angles instead of framing a sliver.

Usage:
    ./scripts/blrun.sh --background --python scripts/look.py -- \
        --scene edge_wide --output output/edges/look_wide
"""
import bpy

from blender_kit import common_parser, script_argv, clear_scene, make_material


def build_scene():
    clear_scene()
    mat = make_material("WideMat", (0.2, 0.55, 0.75), roughness=0.5)
    ids = []
    for i in range(9):
        x = -7.0 + i * 1.75
        bpy.ops.mesh.primitive_cube_add(size=0.4, location=(x, 0.0, 0.2))
        ob = bpy.context.active_object
        ob.name = f"W{i}"
        ob.data.materials.append(mat)
        ids.append(ob.name)
    return {"ids": ids}


def animate(ctx):
    pass


if __name__ == "__main__":
    argv = script_argv()
    parser = common_parser("edge_wide — extreme wide-aspect fixture")
    args = parser.parse_args(argv)
    build_scene()
