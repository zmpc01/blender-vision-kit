"""tdawn_filmstrips.py -- the review-app timeline strips.

One workbench process renders 8 frames per shot at 192x108 (the
deterministic renderer convention: f(k) = f0 + round(k*(span-1)/7),
file = {sid}_{k:02d}.jpg) into the package's filmstrips/ dir.

    CROWD_CACHE_DIR=/tmp/crowdcache_tdawn ./scripts/blrun.sh --background \
        --python scripts/tdawn_filmstrips.py -- --pkg output/tdawn/pkg
"""
import bpy
import os
import sys


def _script_args():
    argv = sys.argv
    return argv[argv.index("--") + 1:] if "--" in argv else []


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--pkg", default="output/tdawn/pkg")
    ap.add_argument("--w", type=int, default=192)
    ap.add_argument("--h", type=int, default=108)
    args = ap.parse_args(_script_args())

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import scene_terminal_dawn as TD

    ctx = TD.build_scene()
    TD.animate(ctx)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.view_settings.view_transform = "Standard"
    scene.render.resolution_x = args.w
    scene.render.resolution_y = args.h
    scene.render.image_settings.file_format = "JPEG"

    out_dir = os.path.join(args.pkg, "filmstrips")
    os.makedirs(out_dir, exist_ok=True)

    # the marker cameras hijack renders (AK-10) -- suppress + reassert
    marks = [(m, m.camera) for m in scene.timeline_markers if m.camera]
    for m, _c in marks:
        m.camera = None
    scene.camera = None  # marker resolution off; bind per shot

    n = 8
    count = 0
    try:
        for sid, f0, f1, _intent in TD.SHOTS_V3:
            cam = ctx["cams"][f"CAM_{sid}"]["cam"]
            scene.camera = cam
            span = f1 - f0 + 1
            for k in range(n):
                f = f0 + round(k * (span - 1) / (n - 1))
                scene.frame_set(f)
                scene.render.filepath = os.path.join(
                    out_dir, f"{sid}_{k:02d}.jpg")
                bpy.ops.render.render(write_still=True)
                count += 1
            print(f"[strips] {sid}: {n} frames")
    finally:
        for m, c in marks:
            m.camera = c
    print(f"[strips] DONE {count} strips -> {out_dir}")


main()
