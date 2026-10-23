"""tmarket_filmstrips.py -- the review-app timeline strips (NIGHT MARKET).

Written FRESH for THIS film (the clone-seam law). One workbench process
renders 8 frames per shot at 192x108 (f(k) = f0 + round(k*(f1-f0)/7),
both endpoints inclusive -- the proven linspace-inclusive law;
file = {sid}_{k:02d}.jpg) into the package's filmstrips/ dir.

    CROWD_CACHE_DIR=/tmp/crowdcache_tmarket ./scripts/blrun.sh --background \
        --python scripts/tmarket_filmstrips.py -- --pkg output/tmarket/pkg
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
    ap.add_argument("--pkg", default="output/tmarket/pkg")
    ap.add_argument("--w", type=int, default=192)
    ap.add_argument("--h", type=int, default=108)
    args = ap.parse_args(_script_args())

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import scene_night_market as TM

    ctx = TM.build_scene()
    TM.animate(ctx)
    scene = bpy.context.scene
    # the module-level timing law from scene_night_market (FPS=24 /
    # total_frames=1080): every strip window must live inside the reel
    assert TM.SHOTS_V3[-1][2] <= TM.total_frames, (
        f"last shot f1 {TM.SHOTS_V3[-1][2]} exceeds total_frames {TM.total_frames}")
    scene.render.fps = TM.FPS
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "FLAT"
    scene.display.shading.color_type = "MATERIAL"
    scene.view_settings.view_transform = "Standard"
    # s28 (the ext-replace law, carried from the s27 fix): JPEG must be
    # pinned BEFORE any strip renders -- Blender swaps the ext per
    # file_format, so the strips land as .jpg not .png
    scene.render.image_settings.file_format = "JPEG"
    scene.render.resolution_x = args.w
    scene.render.resolution_y = args.h
    strips = os.path.join(args.pkg, "filmstrips")
    os.makedirs(strips, exist_ok=True)
    marks = [(m, m.camera) for m in scene.timeline_markers if m.camera]
    try:
        n = 0
        for sid, f0, f1, _intent in TM.SHOTS_V3:
            cam_name = f"CAM_{sid}"
            if cam_name not in ctx["cams"]:
                raise KeyError(cam_name)
            scene.camera = ctx["cams"][cam_name]["ob"]
            for k in range(8):
                f = f0 + round(k * (f1 - f0) / 7)
                _out = os.path.join(strips, f"{sid}_{k:02d}.jpg")
                if os.path.isfile(_out) and os.path.getsize(_out) > 0:
                    continue  # s27 idempotent resume (the chunked-wave law)
                scene.frame_set(f)
                scene.render.filepath = _out
                bpy.ops.render.render(write_still=True)
                n += 1
            print(f"[filmstrips] {sid} done")
    finally:
        for m, c in marks:
            m.camera = c
    print(f"[filmstrips] {n} strips -> {strips}")


main()
