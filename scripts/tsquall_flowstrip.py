"""tsquall_flowstrip.py -- top-down orthographic flow strip (SQUALL).

One Blender process renders N frames from a top-down ortho camera
covering the plaza, stitches them side-by-side (the L5 law). THE SEAM
DETECTOR: run BEFORE cameras.

    CROWD_CACHE_DIR=/tmp/crowdcache_tsquall ./scripts/blrun.sh --background \
        --python scripts/tsquall_flowstrip.py -- --out output/tsquall/flow.png \
        --frames 1,100,200,300,400,500,700,1000

Geometry: the plaza spans x -30..30 (60m) and y -6..15 (21m);
landscape 900x360; ortho_scale applies to the LARGER dimension
(w=900): scale 68 -> horizontal span 68m (x -34..34), vertical =
68*360/900 = 27.2m (y -4.6..22.6 centered on cam y 9) -- covers the
plaza + the arcade + the north strip with margin.
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
    ap.add_argument("--out", default="output/tsquall/flow.png")
    ap.add_argument("--frames", default="1,100,200,300,400,500,700,1000")
    ap.add_argument("--w", type=int, default=900)
    ap.add_argument("--h", type=int, default=360)
    ap.add_argument("--hide-roof", action="store_true",
                    help="hide the arcade roof+sign so the fill under "
                         "the canopy is visible in the ortho view")
    args = ap.parse_args(_script_args())

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import scene_squall as TS

    ctx = TS.build_scene()
    TS.animate(ctx)
    if args.hide_roof:
        hidden = 0
        for o in bpy.data.objects:
            if o.type == 'MESH' and o.name.startswith(
                    ("TSQ.Arcade.Roof", "TSQ.SignBand", "TSQ.BandFrame",
                     "TSQ.Lintel")):
                o.hide_render = True
                o.hide_viewport = True
                hidden += 1
        print(f"[flowstrip] hid {hidden} roof/band objects")

    scene = bpy.context.scene
    cd = bpy.data.cameras.new("TS.FlowCam")
    cd.type = "ORTHO"
    cd.ortho_scale = 68.0
    cam = bpy.data.objects.new("TS.FlowCam", cd)
    cam.location = (0.0, 9.0, 40.0)
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
            base = os.path.splitext(args.out)[0]
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
