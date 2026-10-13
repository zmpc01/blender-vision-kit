"""tgreen_flowstrip.py -- top-down orthographic flow strip (GREEN LIGHT).

One Blender process renders N frames from a top-down ortho camera
covering the crossing, stitches them side-by-side (the L5 law).

    CROWD_CACHE_DIR=/tmp/crowdcache_tgreen ./scripts/blrun.sh --background \
        --python scripts/tgreen_flowstrip.py -- --out output/tgreen/flow.png \
        --frames 1,100,200,300,400,500,700,1000

Geometry: the street spans x -30..30 (the LONG axis, 60m) and y -6..5
(walkable); landscape 900x360; ortho_scale applies to the LARGER
dimension (w=900): scale 64 -> horizontal span 64m (x -32..32), vertical
= 64*360/900 = 25.6m (y -10..15.6 centered on cam y 2.8) -- covers the
street + both sidewalks with margin.
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
    ap.add_argument("--out", default="output/tgreen/flow.png")
    ap.add_argument("--frames", default="1,100,200,300,400,500,700,1000")
    ap.add_argument("--w", type=int, default=900)
    ap.add_argument("--h", type=int, default=360)
    args = ap.parse_args(_script_args())

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import scene_green_light as TG

    ctx = TG.build_scene()
    TG.animate(ctx)

    scene = bpy.context.scene
    cd = bpy.data.cameras.new("TG.FlowCam")
    cd.type = "ORTHO"
    cd.ortho_scale = 64.0
    cam = bpy.data.objects.new("TG.FlowCam", cd)
    cam.location = (0.0, 2.8, 40.0)
    scene.collection.objects.link(cam)
    cam.rotation_euler = (0.0, 0.0, 0.0)
    scene.camera = cam
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "FLAT"
    scene.display.shading.color_type = "MATERIAL"
    scene.view_settings.view_transform = "Standard"
    scene.render.resolution_x = args.w
    scene.render.resolution_y = args.h

    frames = [int(f) for f in args.frames.split(",")]
    marks = [(m, m.camera) for m in scene.timeline_markers if m.camera]
    for m, _c in marks:
        m.camera = None
    scene.camera = cam
    try:
        outs = []
        for f in frames:
            scene.frame_set(f)
            base = os.path.splitext(args.out)[0]   # the 3-g find: --out without .png no-ops the replace
            p = os.path.abspath(f"{base}_{f:05d}.png")
            scene.render.filepath = p
            bpy.ops.render.render(write_still=True)
            outs.append(p)
            print(f"[flowstrip] rendered f{f}")
    finally:
        for m, c in marks:
            m.camera = c

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
