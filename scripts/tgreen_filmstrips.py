"""tgreen_filmstrips.py -- the review-app timeline strips (GREEN LIGHT).

One workbench process renders 8 frames per shot at 192x108 (the
deterministic renderer convention: f(k) = f0 + round(k*(span-1)/7),
file = {sid}_{k:02d}.jpg) into the package's filmstrips/ dir.

    CROWD_CACHE_DIR=/tmp/crowdcache_tgreen ./scripts/blrun.sh --background \
        --python scripts/tgreen_filmstrips.py -- --pkg output/tgreen/pkg
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
    ap.add_argument("--pkg", default="output/tgreen/pkg")
    ap.add_argument("--w", type=int, default=192)
    ap.add_argument("--h", type=int, default=108)
    args = ap.parse_args(_script_args())

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import scene_green_light as TG

    ctx = TG.build_scene()
    TG.animate(ctx)
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
        for sid, f0, f1, _intent in TG.SHOTS_V3:
            # scene_last_ferry stores the camera OBJECT under "ob"
            # (tdawn's dict key was "cam") -- same object the markers
            # bind in _markers().
            cam = ctx["cams"][f"CAM_{sid}"]["ob"]
            scene.camera = cam
            span = f1 - f0 + 1
            for k in range(n):
                f = f0 + round(k * (span - 1) / (n - 1))
                _out = os.path.join(out_dir, f"{sid}_{k:02d}.jpg")
                if os.path.isfile(_out) and os.path.getsize(_out) > 0:
                    continue  # s27 idempotent resume (the chunked-wave law)
                scene.frame_set(f)
                scene.render.filepath = _out
                bpy.ops.render.render(write_still=True)
                count += 1
            print(f"[strips] {sid}: {n} frames")
    finally:
        for m, c in marks:
            m.camera = c
    print(f"[strips] DONE {count} strips -> {out_dir}")


main()
