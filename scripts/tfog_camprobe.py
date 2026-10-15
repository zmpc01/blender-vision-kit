"""tfog_camprobe.py -- the framing-probe driver (THE EXPRESS).

Monkey-patches candidate cam rows over the scene module and renders
workbench stills per candidate (ONE Blender process, N candidates).
The EYES adjudicate; this tool only makes the candidates cheap.

    CROWD_CACHE_DIR=/tmp/crowdcache_tfog ./scripts/blrun.sh --background \
        --python scripts/tfog_camprobe.py -- --spec ALL

5.2 probe laws baked in (this session's flowstrip findings):
  - shot markers are DELETED + recreated (nulled markers still flip
    scene.camera at frame_set);
  - the fog box is HIDDEN (workbench renders its surface as an opaque
    64x10 slab — a probe artifact, not film truth); the canopy stays
    ON (framing must respect the real occlusion — the axial-crane law);
  - the crowd dots get the hot override (129 per-instance mesh data).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import bpy

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
OUT = HERE.parent / "output" / "tfog" / "probes"
OUT.mkdir(parents=True, exist_ok=True)

# candidate rows: (candidate, loc, lens, aim) — static cams only;
# cranes render at their keyed pose via the scene module.
CANDIDATES = {
    "S1": [
        ("S1a", (30.0, -18.0, 16.0), 30, (0.0, 0.0, 0.5)),
        ("S1b", (34.0, 16.0, 14.0), 28, (0.0, 0.0, 0.5)),
        ("S1c", (26.0, 0.0, 22.0), 26, (0.0, 0.0, 0.0)),
    ],
    "S2": [
        ("S2a", (-18.0, -1.5, 1.6), 35, (-20.0, -3.2, 0.7)),
        ("S2b", (-14.0, 2.8, 1.5), 40, (-19.0, -1.0, 0.6)),
        ("S2c", (-22.0, 0.5, 2.4), 30, (-15.0, -2.0, 0.5)),
    ],
    "S3": [
        ("S3a", (0.0, -14.0, 2.2), 40, (-28.0, -8.5, 1.5)),
        ("S3b", (-6.0, -10.0, 3.2), 35, (-30.0, -7.0, 1.2)),
        ("S3c", (8.0, -13.0, 4.0), 50, (-26.0, -8.0, 1.8)),
    ],
    "S4": [
        ("S4a", (5.0, 10.5, 2.6), 50, (0.0, 0.1, 2.6)),
        ("S4b", (-6.5, 9.0, 2.2), 45, (0.0, 0.1, 2.6)),
        ("S4c", (3.0, 6.0, 1.9), 40, (0.0, 0.2, 2.7)),
    ],
    "S5": [
        ("S5a", (-14.0, -12.0, 9.0), 35, (0.0, -3.0, 0.8)),
        ("S5b", (-20.0, -16.0, 7.0), 40, (2.0, -2.0, 0.8)),
        ("S5c", (0.0, -16.0, 11.0), 35, (0.0, -1.0, 0.6)),
    ],
    "S6": [
        ("S6g", (-8.0, -2.6, 1.6), 30, (2.0, 0.5, 0.8)),
        ("S6h", (-9.0, -2.2, 2.2), 30, (3.0, 0.2, 0.7)),
        ("S6i", (-7.0, -2.8, 1.5), 26, (4.0, 0.8, 0.8)),
    ],
    "S7": [
        ("S7a", (26.0, -12.5, 1.4), 40, (19.0, -3.0, 1.1)),
        ("S7b", (24.0, -10.0, 2.6), 35, (20.0, -3.4, 1.0)),
        ("S7c", (30.0, -8.0, 3.2), 45, (21.0, -3.2, 1.0)),
    ],
    "S8": [
        ("S8a", (12.0, -14.0, 6.0), 35, (-10.0, 8.5, 1.8)),
        ("S8b", (-2.0, -15.0, 4.0), 40, (-12.0, 7.5, 1.5)),
        ("S8c", (-16.0, -12.0, 2.4), 35, (2.0, 8.5, 1.6)),
    ],
    "S9": [
        ("S9a", (4.6, 1.0, 1.6), 35, (0.0, 3.2, 0.9)),
        ("S9b", (-3.0, -1.0, 2.2), 40, (1.0, 3.4, 0.9)),
        ("S9c", (2.0, -2.0, 3.4), 35, (0.5, 3.4, 0.7)),
    ],
    "S10": [
        ("S10j", (-21.5, -2.0, 1.6), 35, (-24.0, 4.6, 1.2)),
        ("S10k", (-20.0, -1.2, 1.7), 40, (-23.5, 4.4, 1.1)),
        ("S10l", (-23.5, -1.0, 1.6), 30, (-25.0, 4.8, 1.3)),
    ],
    "S11": [
        ("S11j", (-40.0, 7.0, 2.2), 35, (-20.0, 7.2, 1.5)),
        ("S11k", (-44.0, 5.0, 2.6), 35, (-24.0, 7.0, 1.4)),
        ("S11l", (-36.0, 9.0, 1.9), 30, (-18.0, 7.4, 1.6)),
    ],
    "S12": [
        ("S12m", (18.0, -7.0, 1.9), 35, (4.0, -1.2, 1.8)),
        ("S12n", (16.0, -6.0, 1.8), 40, (5.0, -1.0, 1.9)),
        ("S12o", (20.0, -8.0, 2.2), 30, (3.0, -1.5, 1.7)),
    ],
}

# representative frame per shot (the read moment)
FRAME = {"S1": 50, "S2": 140, "S3": 270, "S4": 320, "S5": 430,
         "S6": 570, "S7": 640, "S8": 740, "S9": 840, "S10": 910,
         "S11": 980, "S12": 1050}


def _script_args():
    argv = sys.argv
    return argv[argv.index("--") + 1:] if "--" in argv else []


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", default="ALL")
    args = ap.parse_args(_script_args())

    import tfog_scene as TF
    scene = bpy.context.scene
    ctx = TF.build_scene()
    TF.animate(ctx)
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "FLAT"
    scene.display.shading.color_type = "MATERIAL"
    scene.view_settings.view_transform = "Standard"
    scene.render.resolution_x = 640
    scene.render.resolution_y = 360

    # crowd dots (contrast) + fog box hide (workbench artifact)
    ov = bpy.data.materials.new("TFG.ProbeDot")
    ov.use_nodes = True
    nb = ov.node_tree.nodes.get("Principled BSDF")
    if nb:
        nb.inputs["Base Color"].default_value = (1.0, 0.35, 0.05, 1.0)
        nb.inputs["Emission Strength"].default_value = 0.5
    seen = set()
    for ob in bpy.data.objects:
        if ob.name.startswith("Zed.") and ob.type == 'MESH' \
                and ob.data.name not in seen:
            seen.add(ob.data.name)
            ob.data.materials.clear()
            ob.data.materials.append(ov)
    for ob in bpy.data.objects:
        nm = ob.name.lower()
        if "fog" in nm or "volume" in nm:
            ob.hide_render = True

    specs = list(CANDIDATES) if args.spec == "ALL" else \
        args.spec.split(",")
    marks = [(m.name, m.frame, m.camera)
             for m in scene.timeline_markers if m.camera]
    for m in list(scene.timeline_markers):
        scene.timeline_markers.remove(m)
    try:
        for spec in specs:
            f = FRAME[spec]
            scene.frame_set(f)          # pose the world ONCE per spec
            for cand, loc, lens, aim in CANDIDATES[spec]:
                cd = bpy.data.cameras.new(f"PROBE_{cand}")
                cd.lens = lens
                ob = bpy.data.objects.new(f"PROBE_{cand}", cd)
                scene.collection.objects.link(ob)
                ob.location = loc
                aim_ob = bpy.data.objects.new(f"PROBE_AIM_{cand}", None)
                scene.collection.objects.link(aim_ob)
                aim_ob.location = aim
                ob.constraints.new("TRACK_TO")
                ob.constraints[0].target = aim_ob
                ob.constraints[0].track_axis = "TRACK_NEGATIVE_Z"
                ob.constraints[0].up_axis = "UP_Y"
                scene.camera = ob
                scene.render.filepath = str(OUT / f"{cand}_f{f}.png")
                bpy.ops.render.render(write_still=True)
                print(f"[camprobe] {cand} f{f} loc={loc} lens={lens}")
    finally:
        for name, frame, cam_ob in marks:
            m = scene.timeline_markers.new(name, frame=frame)
            m.camera = cam_ob
    print(f"[camprobe] DONE -> {OUT}")


main()
