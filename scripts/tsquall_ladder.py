"""tsquall_ladder.py -- the storm-dusk light ladder (SQUALL).

The fourth light regime (dawn / night / noon precede). The ladders
measure, the eye decides: EEVEE stills at the three light-critical
frames with printed metrics (the tgreen ladder protocol), sweeping the
DIRECT:AMBIENT ratio (the tgreen noon law's lever) plus the practical
floor. Output: output/tsquall/ladder/ + a metrics line per combo.

    ./scripts/blrun.sh --background --python scripts/tsquall_ladder.py
"""
from __future__ import annotations

import math
import os
import sys
from pathlib import Path

import bpy

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
OUT = HERE.parent / "output" / "tsquall" / "ladder"
OUT.mkdir(parents=True, exist_ok=True)

# the ladder: (name, sun_energy, sun_deg_elev, sun_color, sky_strength,
#              warm_boost) -- the practicals' emission rides warm_boost
# via their materials' emission_strength multiplier is NOT re-authorable
# cheaply; the practical floor is the SKY's job here. The lever set:
# sun energy x elevation x sky strength (the direct:ambient ratio).
COMBOS = [
    ("sun2_sky40",  2.0, 78, (1.0, 0.72, 0.48), 0.40),
    ("sun3_sky40",  3.0, 78, (1.0, 0.72, 0.48), 0.40),
    ("sun3_sky25",  3.0, 78, (1.0, 0.72, 0.48), 0.25),
    ("sun5_sky25",  5.0, 78, (1.0, 0.72, 0.48), 0.25),
    ("sun5_sky15",  5.0, 82, (1.0, 0.70, 0.45), 0.15),
    ("sun7_sky15",  7.0, 82, (1.0, 0.68, 0.42), 0.15),
]

FRAMES = (570,)            # the fill -- the light-critical frame
                           # (the other beats certify in the stills round)


def _set_sky(scene, sky_strength, sun_energy, elev_deg, color):
    world = scene.world
    world.use_nodes = True
    nt = world.node_tree
    bg = nt.nodes.get("Background")
    if not bg:
        bg = nt.nodes.new("ShaderNodeBackground")
        out = next(n for n in nt.nodes if n.type == "OUTPUT_WORLD")
        nt.links.new(bg.outputs[0], out.inputs[0])
    # the storm sky: a dark blue-grey ambient (the overcast law -- the
    # sky owns the ambient, the sun owns the direction)
    bg.inputs[0].default_value = (0.045, 0.055, 0.078, 1.0)
    bg.inputs[1].default_value = sky_strength
    # the key: a slightly warm LOW storm sun (the ladder lever)
    sun = bpy.data.lights.get("TSQ.LadderSun") or \
        bpy.data.lights.new("TSQ.LadderSun", "SUN")
    sun.energy = sun_energy
    sun.color = color
    sun.angle = math.radians(4.0)
    ob = bpy.data.objects.get("TSQ.LadderSun")
    if not ob:
        ob = bpy.data.objects.new("TSQ.LadderSun", sun)
        scene.collection.objects.link(ob)
    ob.data = sun
    ob.rotation_euler = (math.radians(90.0 - elev_deg), 0.0,
                         math.radians(-38.0))


def main():
    sys.path.insert(0, str(HERE))
    import scene_squall as TS

    scene = bpy.context.scene
    ctx = TS.build_scene()
    TS.animate(ctx)
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.use_raytracing = True
    if hasattr(scene.eevee, "taa_render_samples"):
        scene.eevee.taa_render_samples = 32
    scene.view_settings.view_transform = "AgX"   # the SHIPPING transform
    scene.view_settings.exposure = TS.ts_exposure
    scene.render.resolution_x = 640
    scene.render.resolution_y = 360

    cam = bpy.data.cameras.new("TSQ.LadderCam")
    cam.lens = 35
    ob = bpy.data.objects.new("TSQ.LadderCam", cam)
    scene.collection.objects.link(ob)
    ob.location = (-24.0, -20.0, 15.0)
    aim = bpy.data.objects.new("TSQ.LadderAim", None)
    scene.collection.objects.link(aim)
    aim.location = (2.0, 1.0, 0.0)
    ob.constraints.new("TRACK_TO")
    ob.constraints[0].target = aim
    ob.constraints[0].track_axis = "TRACK_NEGATIVE_Z"
    ob.constraints[0].up_axis = "UP_Y"
    scene.camera = ob
    # the MARKER-CAMERA LAW: shot markers override scene.camera at any
    # frame inside their span (the flowstrip nulls them for the same
    # reason). 3 ladder runs rendered CAM_S7's keyed pose before this.
    _marks = [(m, m.camera) for m in scene.timeline_markers if m.camera]
    for m, _c in _marks:
        m.camera = None
    scene.camera = ob

    import numpy as np
    for name, se, elev, col, sky in COMBOS:
        _set_sky(scene, sky, se, elev, col)
        for f in FRAMES:
            scene.frame_set(f)
            scene.render.filepath = str(OUT / f"{name}_f{f}.png")
            bpy.ops.render.render(write_still=True)
        # the metrics on the middle frame
        from PIL import Image
        img = np.asarray(Image.open(OUT / f"{name}_f{FRAMES[0]}.png")
                         .convert("L"), dtype=np.float32) / 255.0
        print(f"[ladder] {name}: mean={img.mean():.3f} "
              f"p50={np.percentile(img, 50):.3f} "
              f"p95={np.percentile(img, 95):.3f} "
              f"p05={np.percentile(img, 5):.3f} "
              f"range={np.percentile(img, 95) - np.percentile(img, 5):.3f}")
    for m, c in _marks:
        m.camera = c
    print(f"[ladder] DONE -> {OUT}")


main()
