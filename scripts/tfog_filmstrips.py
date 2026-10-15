"""tfog_filmstrips.py -- the review-app timeline strips (THE EXPRESS).

Written FRESH for THIS film (the clone-seam law). One workbench process
renders 8 frames per shot at 192x108 (f(k) = f0 + round(k*(span-1)/7),
file = {sid}_{k:02d}.jpg) into the package's filmstrips/ dir.

    CROWD_CACHE_DIR=/tmp/crowdcache_tfog ./scripts/blrun.sh --background \
        --python scripts/tfog_filmstrips.py -- --pkg output/tfog/pkg
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
    ap.add_argument("--pkg", default="output/tfog/pkg")
    ap.add_argument("--w", type=int, default=192)
    ap.add_argument("--h", type=int, default=108)
    args = ap.parse_args(_script_args())

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import tfog_scene as TF

    ctx = TF.build_scene()
    TF.animate(ctx)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "FLAT"
    scene.display.shading.color_type = "MATERIAL"
    scene.view_settings.view_transform = "Standard"
    scene.render.resolution_x = args.w
    scene.render.resolution_y = args.h
    strips = os.path.join(args.pkg, "filmstrips")
    os.makedirs(strips, exist_ok=True)
    marks = [(m.name, m.frame, m.camera)
             for m in scene.timeline_markers if m.camera]
    try:
        n = 0
        for sid, f0, f1, _intent in TF.SHOTS_V1:
            cam_name = f"CAM_{sid}"
            if cam_name not in ctx["cams"]:
                raise KeyError(cam_name)
            scene.camera = ctx["cams"][cam_name]["ob"]
            for k in range(8):
                f = f0 + round(k * (f1 - f0) / 7)
                scene.frame_set(f)
                scene.render.filepath = os.path.join(
                    strips, f"{sid}_{k:02d}.jpg")
                bpy.ops.render.render(write_still=True)
                n += 1
            print(f"[filmstrips] {sid} done")
    finally:
        for name, frame, cam_ob in marks:
            m = scene.timeline_markers.new(name, frame=frame)
            m.camera = cam_ob
    print(f"[filmstrips] {n} strips -> {strips}")


main()
