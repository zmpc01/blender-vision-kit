"""tform_flowstrip.py -- top-down orthographic flow strip (THE DRILL).

Written FRESH for THIS film (the clone-seam law). One Blender process
renders N frames from a top-down ortho camera covering the yard + the
barracks strip (the dispersal exits N), stitches them side-by-side.

    CROWD_CACHE_DIR=/tmp/crowdcache_tform ./scripts/blrun.sh --background \
        --python scripts/tform_flowstrip.py -- --out output/tform/flow.png \
        --frames 1,260,420,560,700,830,900,1000,1060

Geometry: the yard spans x -28..28, y -20..20; the gap + barracks
strip carry the dispersal to y ~26. Landscape 1500x420; ortho_scale
applies to the LARGER dimension (w=1500): scale 66 -> horizontal span
66 m (x -33..33), vertical = 66*420/1500 = 18.5 m -- TOO NARROW for
the yard (40 m). So PORTRAIT-ish geometry instead: w=420 h=1500 puts
the 66 m span on the VERTICAL (y -13..53 centered on cam y 20 --
covers the colonnade -20..the barracks 26 with margin) and 18.5 m on
the horizontal (x -9.2..9.2 -- the formation column lives within it;
the shade line clips, noted).

--hide-roof: hides the walls' battlement caps + backdrop so the gap
read stays clean (workbench renders them opaque from above).
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
    ap.add_argument("--out", default="output/tform/flow.png")
    ap.add_argument("--frames",
                    default="1,260,420,560,700,830,900,1000,1060")
    ap.add_argument("--w", type=int, default=420)
    ap.add_argument("--h", type=int, default=1500)
    ap.add_argument("--hide-roof", action="store_true")
    args = ap.parse_args(_script_args())

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import tform_scene as TF

    ctx = TF.build_scene()
    TF.animate(ctx)

    scene = ctx["scene"]
    # crowd contrast: the commuter palette reads yard-stone in
    # workbench MATERIAL mode -- override the shared mesh data with a
    # hot dot material for the strip (in-process probe only).
    ov = bpy.data.materials.new("TF.FlowDot")
    ov.use_nodes = True
    nb = ov.node_tree.nodes.get("Principled BSDF")
    if nb:
        nb.inputs["Base Color"].default_value = (1.0, 0.35, 0.05, 1.0)
        nb.inputs["Emission Color"].default_value = (1.0, 0.35, 0.05,
                                                     1.0)
        nb.inputs["Emission Strength"].default_value = 0.6
    ndot = 0
    seen = set()
    # s25: the strip law — post-bind, the crowd surface is the RIG
    # BODIES (the Zed.* anchors are 1-vert carriers and an anchor-only
    # dot override renders an EMPTY strip). The kit helper dots the
    # Hum.* rig-body data (shared per group: one write per group) AND
    # the anchor data (harmless pre-bind: keeps the legacy behavior).
    import humanoid_crowd as _HC
    _cen = _HC.strip_dot_override(ov, anchor_prefix="Zed.")
    ndot = _cen["bodies"] + _cen["anchors"]
    print(f"[tform_flowstrip] crowd dot override on {ndot} mesh data(s) "
          f"(bodies {_cen['bodies']} / anchors {_cen['anchors']})")
    if args.hide_roof:
        hidden = 0
        for ob in bpy.data.objects:
            nm = ob.name.lower()
            if ("battlement" in nm or "backdrop" in nm or "wall" in nm
                    or "hills" in nm or "dust" in nm or "volume" in nm):
                ob.hide_render = True
                hidden += 1
        print(f"[tform_flowstrip] hid {hidden} wall/backdrop/dust "
              f"object(s)")
    cd = bpy.data.cameras.new("TF.FlowCam")
    cd.type = "ORTHO"
    cd.ortho_scale = 66.0
    cam = bpy.data.objects.new("TF.FlowCam", cd)
    cam.location = (0.0, 20.0, 40.0)
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
    # enough -- a still-present marker flips scene.camera at frame_set.
    # DELETE the markers for the strip and recreate them faithfully
    # after.
    marks = [(m.name, m.frame, m.camera) for m in scene.timeline_markers
             if m.camera]
    for m in list(scene.timeline_markers):
        scene.timeline_markers.remove(m)
    import tempfile
    from PIL import Image, ImageDraw
    paths = []
    tmpd = tempfile.mkdtemp(prefix="tform_flow_")
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
                          (14, 13, 11))
        dr = ImageDraw.Draw(sheet)
        for k, (f, p) in enumerate(paths):
            im = Image.open(p).convert("RGB")
            sheet.paste(im, (k * w, label_h))
            dr.text((k * w + 10, 6), f"f{f}", fill=(240, 240, 240))
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        sheet.save(args.out)
        print(f"[tform_flowstrip] wrote {args.out} "
              f"({len(paths)} cells, roof_hidden={args.hide_roof})")
    finally:
        for name, frame, cam_ob in marks:
            m = scene.timeline_markers.new(name, frame=frame)
            m.camera = cam_ob


if __name__ == "__main__":
    main()
