"""tform_world_look.py -- the principal's eye probe on the DRILL world.

Builds the world module and renders 4 EEVEE stills (aerial, gap, colonnade,
circle mark) at 640x360 for the visual gate. ONE Blender process.

  ./scripts/blrun.sh --background --python scripts/tform_world_look.py
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import bpy

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import tform_world as W  # noqa: E402
from blender_kit import clear_scene, normalize_engine_id  # noqa: E402
# (s19-B15b: normalize_engine_id -- no hardcoded BLENDER_EEVEE;
#  s19-B15c: the output mkdir moves into main(), import stays clean)

OUT = HERE.parent / "output" / "tform_world_look"


def _cam(name, loc, aim, lens=35.0):
    cam_data = bpy.data.cameras.new(name)
    cam_data.lens = lens
    cam = bpy.data.objects.new(name, cam_data)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = loc
    import mathutils
    direction = (aim[0] - loc[0], aim[1] - loc[1], aim[2] - loc[2])
    rot = mathutils.Vector(direction).to_track_quat("-Z", "Y").to_euler()
    cam.rotation_euler = rot
    return cam


def main():
    OUT.mkdir(parents=True, exist_ok=True)  # import stays side-effect-free
    clear_scene()
    ctx = W.build_world(bpy.context.scene)
    scene = bpy.context.scene
    scene.render.resolution_x = 640
    scene.render.resolution_y = 360
    scene.render.engine = normalize_engine_id("BLENDER_EEVEE")
    scene.view_settings.view_transform = "Standard"
    # golden-hour preview: LOW warm sun raking across the yard + warm sky
    sun = bpy.data.lights.new("TFORM_previz_sun", "SUN")
    sun.energy = 6.0
    sun.color = (1.0, 0.62, 0.32)
    sun_obj = bpy.data.objects.new("TFORM_previz_sun", sun)
    scene.collection.objects.link(sun_obj)
    sun_obj.rotation_euler = (math.radians(84), 0, math.radians(35))
    sun.angle = math.radians(2.5)
    world = bpy.data.worlds.new("TFORM_golden_preview")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0.35, 0.22, 0.12, 1.0)
        bg.inputs[1].default_value = 1.0

    views = [
        ("aerial", (-34, -26, 22), (0, 0, 0), 24),
        ("gap_view", (0, 2, 2.2), (0, 22, 2.0), 30),
        ("colonnade", (-14, -16.5, 1.65), (8, -6, 1.6), 30),
        ("circle_mark", (10, -8, 3.0), (0, 0, 0.4), 35),
    ]
    for name, loc, aim, lens in views:
        cam = _cam(f"LOOK_{name}", loc, aim, lens)
        scene.camera = cam
        scene.render.filepath = str(OUT / f"tform_world_{name}.png")
        bpy.ops.render.render(write_still=True)
        print(f"[tform_look] wrote {name}")
    print(f"[tform_look] DONE -> {OUT}")


if __name__ == "__main__":
    main()
