"""
edge_empty.py — degenerate-input fixture: a scene with NO objects.

Edge-suite target (HANDOFF gap C): look.py --scene must not crash on an
empty world (no meshes, no camera, no light). A vision agent legitimately
looks at an empty scene to confirm "did my clear actually work?" — the
tool must render 4 angles of nothing + an honest verdict, or fail with a
clean one-line message. A raw traceback is a bug.

Usage:
    ./scripts/blrun.sh --background --python scripts/look.py -- \
        --scene edge_empty --output output/edges/look_empty
"""
import bpy

from blender_kit import common_parser, script_argv, clear_scene, print_scene_summary


def build_scene():
    clear_scene()
    # Nothing. Bare world.
    return {}


def animate(ctx, *, start_frame=1, n_frames=24):
    pass


if __name__ == "__main__":
    argv = script_argv()
    parser = common_parser()
    args = parser.parse_args(argv)
    build_scene()
    print_scene_summary()
