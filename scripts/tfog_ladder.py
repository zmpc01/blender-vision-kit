"""tfog_ladder.py -- the blue-hour light ladder (THE EXPRESS).

Renders the ladder candidates on the SIGNATURE frame (S3 headlight
f270) + the wide (S1 f50) in EEVEE, one FULL REBUILD per combo (the
world bakes the TFOG_* strengths into its materials at build time —
the module-constant override + rebuild is the honest knob).

    CROWD_CACHE_DIR=/tmp/crowdcache_tfog ./scripts/blrun.sh --background \
        --python scripts/tfog_ladder.py -- --combos ALL

The AgX-noon law: the ratio is the lever — the blue-hour sky owns the
ambient; the sodiums must punch THROUGH it.
"""
import os
import sys
from pathlib import Path

import bpy

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
OUT = HERE.parent / "output" / "tfog" / "ladder"
OUT.mkdir(parents=True, exist_ok=True)

# (tag, sky_strength, lamp_mult, strip_mult)
COMBOS = [
    ("sky100_l40_s50", 1.00, 0.40, 0.50),
    ("sky040_l40_s50", 0.40, 0.40, 0.50),
    ("sky015_l40_s50", 0.15, 0.40, 0.50),
    ("sky015_l80_s50", 0.15, 0.80, 0.50),
    ("sky040_l80_s80", 0.40, 0.80, 0.80),
    ("sky100_l80_s80", 1.00, 0.80, 0.80),
]

POSES = {50: ((30.0, -18.0, 16.0), (0.0, 0.0, 0.5)),     # S1 wide
         270: ((-6.0, -10.0, 3.2), (-30.0, -7.0, 1.2))}  # S3 track axis


def _add_sky(strength):
    w = bpy.data.worlds.new("TFG.Sky")
    w.use_nodes = True
    bg = w.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (0.05, 0.09, 0.20, 1.0)
    bg.inputs["Strength"].default_value = strength
    bpy.context.scene.world = w


def _metrics(path):
    if not os.path.isfile(path):
        return "no-file"
    import numpy as np
    from PIL import Image
    im = np.asarray(Image.open(path).convert("RGB"), dtype=np.float64) / 255
    lum = 0.2126 * im[..., 0] + 0.7152 * im[..., 1] + 0.0722 * im[..., 2]
    return (f"mean {lum.mean():.3f} p95 {np.percentile(lum, 95):.3f} "
            f"p50 {np.percentile(lum, 50):.3f}")


def _wipe():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for m in list(bpy.data.materials):
        bpy.data.materials.remove(m)
    for me in list(bpy.data.meshes):
        bpy.data.meshes.remove(me)
    for a in list(bpy.data.actions):
        bpy.data.actions.remove(a)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--combos", default="ALL")
    ap.add_argument("--frames", default="270,50")
    args = ap.parse_args(sys.argv[sys.argv.index("--") + 1:])

    scene = bpy.context.scene
    scene.render.resolution_x = 640
    scene.render.resolution_y = 360

    combos = COMBOS if args.combos == "ALL" else [
        c for c in COMBOS if c[0] in args.combos.split(",")]
    frames = [int(f) for f in args.frames.split(",")]

    import tfog_scene as TF
    for tag, sky, lamp, strip in combos:
        _wipe()   # also clears the previous combo's ladder cam — recreate
        cam = bpy.data.objects.new("TFG.LadderCam",
                                   bpy.data.cameras.new("TFG.LadderCam"))
        scene.collection.objects.link(cam)
        aim = bpy.data.objects.new("TFG.LadderAim", None)
        scene.collection.objects.link(aim)
        cam.constraints.new("TRACK_TO")
        cam.constraints[0].target = aim
        cam.constraints[0].track_axis = "TRACK_NEGATIVE_Z"
        cam.constraints[0].up_axis = "UP_Y"
        ctx = TF.build_scene()      # the film's authored 0.40/0.50 build
        TF.animate(ctx)
        # the ladder knob: scale the BUILT lights/materials post-build
        # (the scene module re-pins W.* inside build_scene — the module
        # constant is NOT the honest knob; the built result is)
        BASE_LAMP, BASE_STRIP = 0.40, 0.50
        for ld in bpy.data.lights:
            if ld.name.startswith("lamp_"):
                ld.energy = ld.energy * (lamp / BASE_LAMP)
        for m in bpy.data.materials:
            if m.name.startswith("tfg_strip"):
                b = m.node_tree.nodes.get("Principled BSDF")
                if b:
                    b.inputs["Emission Strength"].default_value = \
                        b.inputs["Emission Strength"].default_value \
                        * (strip / BASE_STRIP)
        _add_sky(sky)
        for f in frames:
            loc, tgt = POSES[f]
            cam.location = loc
            aim.location = tgt
            scene.camera = cam
            scene.frame_set(f)
            p = str(OUT / f"{tag}_f{f}.png")
            scene.render.filepath = p
            bpy.ops.render.render(write_still=True)
            print(f"[ladder] {tag} f{f}: {_metrics(p)}")
    print(f"[ladder] DONE -> {OUT}")


main()
