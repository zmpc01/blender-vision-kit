"""tgreen_camprobe.py -- multi-candidate framing probes in ONE Blender
process (the framing-round law: workbench first, EEVEE only to certify).

Usage (via blrun.sh, from the repo root):
  blrun.sh --background --factory-startup --python scripts/tgreen_camprobe.py -- \
      --still 396 --cands S5a=9.5,17.0,4.2:4.8,14.5,1.0:45 S5b=... --out output/tgreen/probe

Each candidate: SID=camx,camy,camz:aimx,aimy,aimz:lens. The scene builds
ONCE (crowd ON), then per candidate we move CAM_<sid> + Aim.CAM_<sid>,
set lens, frame_set, render workbench still probe_<sid>.png.
"""
import bpy
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)


def _script_args():
    argv = sys.argv
    return argv[argv.index("--") + 1:] if "--" in argv else []


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--still", type=int, required=True)
    p.add_argument("--cands", nargs="+", required=True,
                   help="SID=camx,camy,camz:aimx,aimy,aimz:lens")
    p.add_argument("--out", default="output/tgreen/probe")
    p.add_argument("--samples", type=int, default=16)
    args = p.parse_args(_script_args())

    import scene_last_ferry as M

    scene = bpy.context.scene
    ctx = M.build_scene()
    M.animate(ctx)

    # candidate SIDs map to the real cam names (S5a -> CAM_S5)
    out = args.out
    os.makedirs(out, exist_ok=True)
    for cand in args.cands:
        tag, spec = cand.split("=", 1)
        cam_part, aim_part, lens_part = spec.split(":")
        cam_loc = tuple(float(v) for v in cam_part.split(","))
        aim_loc = tuple(float(v) for v in aim_part.split(","))
        lens = float(lens_part)
        base = tag.rstrip("abcdefghij")
        cam_ob = bpy.data.objects[f"CAM_{base}"]
        aim_ob = bpy.data.objects[f"Aim.CAM_{base}"]
        cam_ob.location = cam_loc
        aim_ob.location = aim_loc
        cam_ob.data.lens = lens
        bpy.context.view_layer.update()
        scene.frame_set(args.still)
        M._set_engine(scene, "workbench", args.samples)
        scene.render.resolution_x = 640
        scene.render.resolution_y = 360
        scene.render.filepath = os.path.join(out, f"probe_{tag}.png")
        bpy.ops.render.render(write_still=True)
        print(f"[camprobe] {tag} cam={cam_loc} aim={aim_loc} "
              f"lens={lens} -> probe_{tag}.png")

    bpy.context.view_layer.update()


if __name__ == "__main__":
    main()
