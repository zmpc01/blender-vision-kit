"""tfog_flowstrip.py -- top-down orthographic flow strip (THE EXPRESS).

One Blender process renders N frames from a top-down ortho camera
covering the platform + both track faces, stitches them side-by-side.

    CROWD_CACHE_DIR=/tmp/crowdcache_tfog ./scripts/blrun.sh --background \
        --python scripts/tfog_flowstrip.py -- --out output/tfog/flow.png \
        --frames 1,200,336,430,528,600,750,900,1000,1075

Geometry: the platform slab spans x -32..32 (the LONG axis) and
y -4..4; track beds N (y ~ 5..9) and S (y ~ -9..-5). Landscape
1400x360; ortho_scale applies to the LARGER dimension (w=1400):
scale 72 -> horizontal span 72m (x -36..36), vertical = 72*360/1400
= 18.5m (y -9.25..9.25 centered on cam y 0) -- covers the slab + both
track faces with margin.

--hide-canopy: hides the canopy roof + fog volume (workbench ignores
volumes anyway) so the under-canopy platform fill is adjudicable; run
both modes before certifying (the SQUALL axial-crane law).
"""
import bpy
import math
import os
import sys


def _script_args():
    argv = sys.argv
    return argv[argv.index("--") + 1:] if "--" in argv else []


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="output/tfog/flow.png")
    ap.add_argument("--frames",
                    default="1,200,336,430,528,600,750,900,1000,1075")
    ap.add_argument("--w", type=int, default=1400)
    ap.add_argument("--h", type=int, default=360)
    ap.add_argument("--hide-canopy", action="store_true")
    args = ap.parse_args(_script_args())

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import tfog_scene as TF

    ctx = TF.build_scene()
    TF.animate(ctx)

    scene = bpy.context.scene
    # crowd contrast: the commuter palette reads slab-white in
    # workbench MATERIAL mode — override the shared mesh data with a
    # hot dot material for the strip (in-process probe only).
    ov = bpy.data.materials.new("TFG.FlowDot")
    ov.use_nodes = True
    nb = ov.node_tree.nodes.get("Principled BSDF")
    if nb:
        nb.inputs["Base Color"].default_value = (1.0, 0.35, 0.05, 1.0)
        nb.inputs["Emission Color"].default_value = (1.0, 0.35, 0.05, 1.0)
        nb.inputs["Emission Strength"].default_value = 0.6
    ndot = 0
    seen = set()
    for ob in scene.collection.objects:
        if ob.name.startswith("Zed.") and ob.type == 'MESH' \
                and ob.data.name not in seen:
            seen.add(ob.data.name)
            ob.data.materials.clear()
            ob.data.materials.append(ov)
            ndot += 1
    print(f"[tfog_flowstrip] crowd dot override on {ndot} mesh data(s)")
    if args.hide_canopy:
        hidden = 0
        for ob in bpy.data.objects:   # world objects live in nested collections — scene.collection.objects is direct-members only
            nm = ob.name.lower()
            if ("canopy" in nm or "roof" in nm or "fog" in nm
                    or "volume" in nm):
                ob.hide_render = True
                hidden += 1
        print(f"[tfog_flowstrip] hid {hidden} canopy/roof/fog object(s)")
    cd = bpy.data.cameras.new("TFG.FlowCam")
    cd.type = "ORTHO"
    cd.ortho_scale = 72.0
    cam = bpy.data.objects.new("TFG.FlowCam", cd)
    cam.location = (0.0, 0.0, 40.0)
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
    # THE MARKER-CAMERA LAW (5.2 form): nulling marker.camera is NOT
    # enough — a still-present marker flips scene.camera at frame_set
    # even with the binding cleared (probed this session: nulled
    # markers rebased scene.camera to the LAST marker's cam). DELETE
    # the markers for the strip and recreate them faithfully after.
    marks = [(m.name, m.frame, m.camera) for m in scene.timeline_markers
             if m.camera]
    for m in list(scene.timeline_markers):
        scene.timeline_markers.remove(m)
    try:
        from scripts.image_metrics import _validate_outputs  # noqa: F401
    except Exception:
        pass
    import tempfile
    from PIL import Image, ImageDraw
    paths = []
    tmpd = tempfile.mkdtemp(prefix="tfog_flow_")
    try:
        for f in frames:
            scene.frame_set(f)
            p = os.path.join(tmpd, f"f{f:04d}.png")
            scene.render.filepath = p
            bpy.ops.render.render(write_still=True)
            if not os.path.isfile(p) or os.path.getsize(p) == 0:
                raise RuntimeError(f"flowstrip: frame {f} produced no "
                                   f"output (the 0-byte class)")
            paths.append((f, p))
        w, h = args.w, args.h
        label_h = 28
        sheet = Image.new("RGB", (w * len(paths), h + label_h),
                          (12, 12, 14))
        dr = ImageDraw.Draw(sheet)
        for k, (f, p) in enumerate(paths):
            im = Image.open(p).convert("RGB")
            sheet.paste(im, (k * w, label_h))
            dr.text((k * w + 10, 6), f"f{f}", fill=(240, 240, 240))
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        sheet.save(args.out)
        print(f"[tfog_flowstrip] wrote {args.out} "
              f"({len(paths)} cells, canopy_hidden={args.hide_canopy})")
    finally:
        for name, frame, cam_ob in marks:
            m = scene.timeline_markers.new(name, frame=frame)
            m.camera = cam_ob


if __name__ == "__main__":
    main()
