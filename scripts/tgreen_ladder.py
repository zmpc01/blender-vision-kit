"""tgreen_ladder.py -- the daylight measured ladder (F10) in ONE
Blender process: for each (sun, sky) combo, patch the world constants,
build+animate once, render the three light-critical frames (EEVEE),
print the anchor metrics. The EYE picks; the numbers anchor.

    CROWD_CACHE_DIR=/tmp/crowdcache_tgreen ./scripts/blrun.sh --background \
        --factory-startup --python scripts/tgreen_ladder.py
"""
import bpy
import os
import sys


def _script_args():
    argv = sys.argv
    return argv[argv.index("--") + 1:] if "--" in argv else []


def _metrics(path):
    from PIL import Image
    import numpy as np
    im = np.asarray(Image.open(path).convert("L"), dtype=np.float32) / 255.0
    clipped = float((im > 0.98).mean()) * 100.0
    dark = float((im < 0.03).mean()) * 100.0
    return (f"clipped%={clipped:.2f} dead%={dark:.2f} "
            f"mean={im.mean():.3f} p95={np.percentile(im, 95):.3f} "
            f"p50={np.percentile(im, 50):.3f}")


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="output/tgreen/ladder")
    ap.add_argument("--frames", default="60,400,1050")
    args = ap.parse_args(_script_args())

    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
    os.makedirs(args.out, exist_ok=True)
    frames = [int(f) for f in args.frames.split(",")]

    import tgreen_world as W
    import scene_green_light as TG

    scene = bpy.context.scene
    for sun, sky in ((4.0, 0.2), (5.0, 0.15), (6.0, 0.2)):
        W.TG_SUN_STRENGTH = sun
        W.TG_SKY_STRENGTH = sky
        # fresh factory purge between combos (build_scene purges the
        # factory trio; the previous combo's TG.* objects must GO)
        for o in list(bpy.data.objects):
            bpy.data.objects.remove(o, do_unlink=True)
        for blk in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras,
                    bpy.data.lights, bpy.data.curves, bpy.data.actions):
            for x in list(blk):
                if x.users == 0:
                    blk.remove(x)
        ctx = TG.build_scene()
        TG.animate(ctx)
        marks = [(m, m.camera) for m in scene.timeline_markers if m.camera]
        for m, _c in marks:
            m.camera = None
        scene.camera = None
        try:
            for f in frames:
                sid = f"sun{sun}_sky{sky}"
                scene.frame_set(f)
                # the shot cam active at f (marker restored temporarily)
                for m, c in marks:
                    if m.frame <= f:
                        best = (m.frame, c)
                scene.camera = best[1]
                TG._set_engine(scene, "eevee", 24)
                scene.render.resolution_x = 640
                scene.render.resolution_y = 360
                p = os.path.abspath(os.path.join(
                    args.out, f"{sid}_f{f:05d}.png"))
                scene.render.filepath = p
                bpy.ops.render.render(write_still=True)
                print(f"[ladder] {sid} f{f}: {_metrics(p)}")
        finally:
            for m, c in marks:
                m.camera = c
        print(f"[ladder] combo sun={sun} sky={sky} DONE")
    bpy.context.view_layer.update()


if __name__ == "__main__":
    main()
