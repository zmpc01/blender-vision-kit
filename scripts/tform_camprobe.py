"""tform_camprobe.py -- the framing probe (one process per shot, the
OOM law; tiles review sheets).

    CROWD_CACHE_DIR=/tmp/crowdcache_tform ./scripts/blrun.sh --background \
        --python scripts/tform_camprobe.py -- --sheet S1,S2,S3,S4,S5,S6

Each cell = the shot's CURRENT committed camera at --frame (default:
the shot's mid-span), 480x270 workbench (the eye gate's fast path).
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
    ap.add_argument("--sheet", required=True,
                    help="comma list of shot ids to render+tile")
    ap.add_argument("--frame", type=int, default=None,
                    help="override frame (default: mid-span)")
    ap.add_argument("--out", default=None)
    ap.add_argument("--w", type=int, default=480)
    ap.add_argument("--h", type=int, default=270)
    ap.add_argument("--dust", action="store_true",
                    help="keep the dust box (default: hide it -- the "
                         "workbench volume law)")
    args = ap.parse_args(_script_args())

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import tform_scene as TF

    ctx = TF.build_scene()
    TF.animate(ctx)
    scene = ctx["scene"]

    # the crowd dot override (the strip law: the commuter palette
    # reads yard-stone in workbench MATERIAL mode)
    ov = bpy.data.materials.new("TF.ProbeDot")
    ov.use_nodes = True
    nb = ov.node_tree.nodes.get("Principled BSDF")
    if nb:
        nb.inputs["Base Color"].default_value = (1.0, 0.35, 0.05, 1.0)
    seen = set()
    for ob in bpy.data.objects:
        if ob.name.startswith("Zed.") and ob.type == 'MESH' \
                and ob.data.name not in seen:
            seen.add(ob.data.name)
            ob.data.materials.clear()
            ob.data.materials.append(ov)
    if not args.dust:
        for ob in bpy.data.objects:
            if "dust" in ob.name.lower() or "volume" in ob.name.lower():
                ob.hide_render = True

    # THE MARKER-CAMERA LAW (5.2): DELETE + recreate faithfully
    marks = [(m.name, m.frame, m.camera) for m in scene.timeline_markers
             if m.camera]
    for m in list(scene.timeline_markers):
        scene.timeline_markers.remove(m)

    import tempfile
    from PIL import Image, ImageDraw
    sids = [s.strip() for s in args.sheet.split(",") if s.strip()]
    spans = {sid: (f0, f1) for sid, f0, f1, _ in TF.SHOTS_V1}
    paths = []
    tmpd = tempfile.mkdtemp(prefix="tform_probe_")
    try:
        for sid in sids:
            if sid not in spans:
                raise SystemExit(f"[probe] unknown shot {sid}")
            f0, f1 = spans[sid]
            f = args.frame if args.frame else (f0 + f1) // 2
            cam = ctx["cams"][f"CAM_{sid}"]["ob"]
            scene.camera = cam
            scene.frame_set(f)
            scene.render.engine = "BLENDER_WORKBENCH"
            scene.display.shading.light = "FLAT"
            scene.display.shading.color_type = "MATERIAL"
            scene.view_settings.view_transform = "Standard"
            scene.render.resolution_x = args.w
            scene.render.resolution_y = args.h
            p = os.path.join(tmpd, f"{sid}.png")
            scene.render.filepath = p
            bpy.ops.render.render(write_still=True)
            if not os.path.isfile(p) or os.path.getsize(p) == 0:
                raise RuntimeError(f"probe: {sid} produced no output")
            paths.append((sid, f, p))
        w, h = args.w, args.h
        cols = 3
        rows = (len(paths) + cols - 1) // cols
        label_h = 24
        sheet = Image.new("RGB", (cols * w, rows * (h + label_h)),
                          (14, 13, 11))
        dr = ImageDraw.Draw(sheet)
        for k, (sid, f, p) in enumerate(paths):
            cx, cy = (k % cols) * w, (k // cols) * (h + label_h)
            im = Image.open(p).convert("RGB")
            sheet.paste(im, (cx, cy + label_h))
            dr.text((cx + 8, cy + 5),
                    f"{sid} @ f{f}", fill=(240, 240, 240))
        out = args.out or f"output/tform/probe_{'-'.join(sids)}.png"
        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
        sheet.save(out)
        print(f"[tform_camprobe] wrote {out} ({len(paths)} cells)")
    finally:
        for name, frame, cam_ob in marks:
            m = scene.timeline_markers.new(name, frame=frame)
            m.camera = cam_ob


if __name__ == "__main__":
    main()
