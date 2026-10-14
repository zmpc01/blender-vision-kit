"""tsquall_camprobe.py -- the framing-probe driver (SQUALL).

Monkey-patches candidate cam rows over the scene module and renders
workbench stills per candidate (the fast framing-round law: workbench,
ONE Blender process, N candidates). The EYES adjudicate; this tool only
makes the candidates cheap.

    CROWD_CACHE_DIR=/tmp/crowdcache_tsquall ./scripts/blrun.sh --background \
        --python scripts/tsquall_camprobe.py -- --spec S5
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import bpy

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
OUT = HERE.parent / "output" / "tsquall" / "probes"
OUT.mkdir(parents=True, exist_ok=True)

# candidate rows: (candidate, loc0, loc1, lens, aim)
CANDIDATES = {
    "S5": [
        # a: the nadir over the basin -- the amber body against the
        # dark ring water, the crowd as texture (the tgreen S5 law)
        ("S5a", (14.8, 7.0, 11.0), (14.8, 7.0, 11.0), 40,
         (14.3, 9.8, 0.0)),
        # b: tight tele from the raised NE -- the faller + basin only
        ("S5b", (20.5, 12.8, 2.7), (20.5, 12.8, 2.7), 85,
         (14.5, 10.1, 0.5)),
        # c: low across the basin from the east -- the ring foreground,
        # the faller beyond; the wall zone keeps the crowd thin
        ("S5c", (17.6, 5.4, 1.5), (17.6, 5.4, 1.5), 50,
         (14.6, 9.9, 0.7)),
        # d: nadir variant wider -- the basin + the slide + the plaza
        ("S5d", (15.2, 5.6, 9.0), (15.2, 5.6, 9.0), 35,
         (14.2, 10.0, 0.0)),
    ],
    "S4": [
        # a: the REV-3 interior-S (the spec row)
        ("S4a", (2.0, -4.0, 1.6), (2.0, -4.0, 1.6), 35,
         (0.0, 6.0, 1.4)),
        # b: from the window side -- the doorway + the press, the
        # window glow right
        ("S4b", (5.0, -3.5, 1.6), (5.0, -3.5, 1.6), 35,
         (-2.0, 5.0, 1.2)),
        # c: higher interior -- the press seen over heads
        ("S4c", (1.5, -4.5, 2.6), (1.5, -4.5, 2.6), 30,
         (0.0, 5.5, 1.0)),
    ],
}


def _script_args():
    argv = sys.argv
    return argv[argv.index("--") + 1:] if "--" in argv else []


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", default="S5")
    ap.add_argument("--frames", default="372,400")
    args = ap.parse_args(_script_args())

    import scene_squall as TS
    cands = CANDIDATES[args.spec]
    frames = [int(f) for f in args.frames.split(",")]

    scene = bpy.context.scene
    ctx = TS.build_scene()
    TS.animate(ctx)
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "FLAT"
    scene.display.shading.color_type = "MATERIAL"
    scene.view_settings.view_transform = "Standard"
    scene.render.resolution_x = 640
    scene.render.resolution_y = 360

    marks = [(m, m.camera) for m in scene.timeline_markers if m.camera]
    for m, _c in marks:
        m.camera = None
    try:
        for cand, loc0, _loc1, lens, aim in cands:
            cd = bpy.data.cameras.new(f"PROBE_{cand}")
            cd.lens = lens
            ob = bpy.data.objects.new(f"PROBE_{cand}", cd)
            scene.collection.objects.link(ob)
            ob.location = loc0
            aim_ob = bpy.data.objects.new(f"PROBE_AIM_{cand}", None)
            scene.collection.objects.link(aim_ob)
            aim_ob.location = aim
            ob.constraints.new("TRACK_TO")
            ob.constraints[0].target = aim_ob
            ob.constraints[0].track_axis = "TRACK_NEGATIVE_Z"
            ob.constraints[0].up_axis = "UP_Y"
            scene.camera = ob
            for f in frames:
                scene.frame_set(f)
                scene.render.filepath = str(OUT / f"{cand}_f{f}.png")
                bpy.ops.render.render(write_still=True)
                print(f"[camprobe] {cand} f{f}")
    finally:
        for m, c in marks:
            m.camera = c
    print(f"[camprobe] DONE -> {OUT}")


main()
