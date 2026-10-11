"""tdawn_flowstrip.py -- top-down orthographic flow strip.

One Blender process renders N frames from a top-down ortho camera
covering the hall, stitches them side-by-side (the L5 law: flow/trajectory
reads belong to a plan view, not perspective stills).

    CROWD_CACHE_DIR=/tmp/crowdcache_tdawn ./scripts/blrun.sh --background \
        --python scripts/tdawn_flowstrip.py -- --out output/tdawn/flow.png \
        --frames 1,200,400,700,1000
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
    ap.add_argument("--out", default="output/tdawn/flow.png")
    ap.add_argument("--frames", default="1,200,400,700,1000")
    ap.add_argument("--w", type=int, default=440)
    ap.add_argument("--h", type=int, default=760)
    args = ap.parse_args(_script_args())

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import scene_terminal_dawn as TD

    ctx = TD.build_scene()
    TD.animate(ctx)

    scene = bpy.context.scene
    # ortho top cam
    cd = bpy.data.cameras.new("TD.FlowCam")
    cd.type = "ORTHO"
    cd.ortho_scale = 30.0
    cam = bpy.data.objects.new("TD.FlowCam", cd)
    cam.location = (0.0, 12.0, 40.0)
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
    sheet = Image.new("RGB", (W, H), (24, 24, 24))
    x = 0
    for i in imgs:
        sheet.paste(i, (x, 0))
        x += i.width + 4
    sheet.save(args.out)
    print(f"[flowstrip] sheet -> {args.out}")


main()
