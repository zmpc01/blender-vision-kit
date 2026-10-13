"""tferry_flowstrip.py -- top-down orthographic flow strip (LAST FERRY).

One Blender process renders N frames from a top-down ortho camera
covering the pier deck, stitches them side-by-side (the L5 law: flow/
trajectory reads belong to a plan view, not perspective stills).

    CROWD_CACHE_DIR=/tmp/crowdcache_tferry ./scripts/blrun.sh --background \
        --python scripts/tferry_flowstrip.py -- --out output/tferry/flow.png \
        --frames 1,300,700,1000
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
    ap.add_argument("--out", default="output/tferry/flow.png")
    ap.add_argument("--frames", default="1,300,700,1000")
    ap.add_argument("--w", type=int, default=360)
    ap.add_argument("--h", type=int, default=900)
    args = ap.parse_args(_script_args())

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import scene_last_ferry as TF

    ctx = TF.build_scene()
    TF.animate(ctx)

    scene = bpy.context.scene
    # ortho top cam -- geometry RECOMPUTED for the pier set: the deck
    # spans x -13..13, y -6..42, so y is the LONG axis (48m of
    # interest) -- the mirror of the tdawn hall where x carried the
    # strip. Resolution is portrait 360x900; in Blender ortho_scale
    # applies to the LARGER of resolution_x/resolution_y, and here
    # h=900 > w=360, so ortho_scale maps to the VERTICAL dimension:
    #   ortho_scale=50 -> vertical span 50m: y 18+/-25 -> -7..43,
    #     which covers the deck's y -6..42 with 1m margin each end;
    #   horizontal span = 50 * 360/900 = 20m -> x +/-10. The deck
    #     dressing runs to x +/-13, but the crowd lives within +/-6;
    #     outboard dressing may clip -- acceptable for a flow strip.
    # Location: x=0, y=18 (the deck's y midpoint: (-6 + 42) / 2), and
    # z=40 kept (ortho: it only has to sit above the set). Rotation
    # (0,0,0) keeps it looking straight down.
    cd = bpy.data.cameras.new("TF.FlowCam")
    cd.type = "ORTHO"
    cd.ortho_scale = 50.0
    cam = bpy.data.objects.new("TF.FlowCam", cd)
    cam.location = (0.0, 18.0, 40.0)
    scene.collection.objects.link(cam)
    cam.rotation_euler = (0.0, 0.0, 0.0)   # looking straight down
    scene.camera = cam
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "FLAT"
    scene.display.shading.color_type = "MATERIAL"
    scene.view_settings.view_transform = "Standard"
    scene.render.resolution_x = args.w
    scene.render.resolution_y = args.h

    frames = [int(f) for f in args.frames.split(",")]
    # the scene binds 12 marker cameras (the shot cut); bpy render
    # respects the ACTIVE marker camera over scene.camera (AK-10
    # class gotcha) -- suppress ALL marker bindings for the strip,
    # restore after (the viewport_capture fix pattern)
    marks = [(m, m.camera) for m in scene.timeline_markers if m.camera]
    for m, _c in marks:
        m.camera = None
    # NOTE: clearing marker bindings MUTATES scene.camera (observed:
    # it fell back to the last shot cam) -- re-assert AFTER the sweep
    scene.camera = cam
    try:
        outs = []
        for f in frames:
            scene.frame_set(f)
            p = os.path.abspath(args.out.replace(".png", f"_{f:05d}.png"))
            scene.render.filepath = p
            bpy.ops.render.render(write_still=True)
            outs.append(p)
            print(f"[flowstrip] rendered f{f}")
    finally:
        for m, c in marks:
            m.camera = c

    # stitch
    from PIL import Image
    imgs = [Image.open(p) for p in outs]
    W = sum(i.width for i in imgs) + 4 * (len(imgs) - 1)
    H = max(i.height for i in imgs)
    sheet = Image.new("RGB", (W, H), (16, 16, 20))
    x = 0
    for i in imgs:
        sheet.paste(i, (x, 0))
        x += i.width + 4
    sheet.save(args.out)
    print(f"[flowstrip] sheet -> {args.out}")


main()
