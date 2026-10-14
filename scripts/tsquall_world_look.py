"""tsquall_world_look.py -- the principal's eye probe on the SQUALL world.

Builds the world module and renders 3 EEVEE stills (aerial, street-N,
arcade interior) at 640x360 for the principal's visual gate. ONE Blender
process (the one-EEVEE law). Usage (via blrun):

  ./scripts/blrun.sh --background --python scripts/tsquall_world_look.py
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import bpy

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import tsquall_world as W  # noqa: E402
from blender_kit import clear_scene  # noqa: E402  (the factory-purge law)

OUT = HERE.parent / "output" / "tsquall_world_look"
OUT.mkdir(parents=True, exist_ok=True)


def _cam(name, loc, aim, lens=35.0):
    cam_data = bpy.data.cameras.new(name)
    cam_data.lens = lens
    cam = bpy.data.objects.new(name, cam_data)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = loc
    direction = (aim[0] - loc[0], aim[1] - loc[1], aim[2] - loc[2])
    import mathutils
    rot = mathutils.Vector(direction).to_track_quat("-Z", "Y").to_euler()
    cam.rotation_euler = rot
    return cam


def main():
    clear_scene()  # the factory-startup purge (the default Cube class)
    ctx = W.build_world(bpy.context.scene)
    scene = bpy.context.scene
    scene.render.resolution_x = 640
    scene.render.resolution_y = 360
    scene.render.engine = "BLENDER_EEVEE"
    # previz-look law: Standard view transform (AgX is for finals)
    scene.view_settings.view_transform = "Standard"
    # storm-dusk preview world: dark overcast ambient + a low sun
    world = bpy.data.worlds.new("TSQ_storm_preview")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0.05, 0.06, 0.085, 1.0)
        bg.inputs[1].default_value = 1.6
    # a few practicals are emissive already (bulbs, strips, window)
    sun = bpy.data.lights.new("TSQ_previz_sun", "SUN")
    sun.energy = 4.0
    sun.color = (1.0, 0.75, 0.5)
    sun_obj = bpy.data.objects.new("TSQ_previz_sun", sun)
    scene.collection.objects.link(sun_obj)
    sun_obj.rotation_euler = (math.radians(75), 0, math.radians(-35))
    sun.angle = math.radians(30)

    views = [
        ("aerial", (-24, -22, 18), (2, 1, 0), 24),
        ("street_n", (2, 14.5, 3.0), (-1, 2, 1.0), 30),
        ("arcade_int", (3.0, -4.5, 1.7), (-2, 6, 1.6), 22),
        ("fountain", (19.0, 11.5, 2.4), (14.0, 7.2, 0.7), 35),
        ("doorway", (0, 12.0, 1.7), (0, -2, 1.2), 35),
    ]
    for name, loc, aim, lens in views:
        cam = _cam(f"LOOK_{name}", loc, aim, lens)
        scene.camera = cam
        scene.render.filepath = str(OUT / f"tsquall_world_{name}.png")
        bpy.ops.render.render(write_still=True)
        print(f"[tsquall_look] wrote {name}")
    print(f"[tsquall_look] DONE -> {OUT}")


if __name__ == "__main__":
    main()
