"""tfog_world_look.py -- the principal's eye probe on the EXPRESS world.

Builds the world module and renders 4 EEVEE stills (aerial, track-level N,
platform W, board close) at 640x360 for the visual gate. ONE Blender
process (the one-EEVEE law). Usage:

  ./scripts/blrun.sh --background --python scripts/tfog_world_look.py
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import bpy

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import tfog_world as W  # noqa: E402
from blender_kit import clear_scene, normalize_engine_id  # noqa: E402
# (clear_scene = the factory-purge law; normalize_engine_id = the
# version-safe engine id -- no hardcoded BLENDER_EEVEE, s19-B15b)

OUT = HERE.parent / "output" / "tfog_world_look"
# s19-B15c: NO mkdir at import time (imports must stay side-effect-free);
# main() creates the dir right before the first render.


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
    clear_scene()  # the factory-startup purge (the default Cube class)
    # practicals ON for the probe: flip the world's keyed-OFF emission
    # consts BEFORE the build (build_world reads them at build time).
    for attr, val in (("TFOG_LAMP_STRENGTH", 0.025), ("TFOG_STRIP_STRENGTH", 1.2),
                      ("TFOG_GLYPH_STRENGTH", 1.5), ("TFOG_WINDOW_STRENGTH", 1.0),
                      ("TFOG_ASPECT_STRENGTH", 1.0)):
        if hasattr(W, attr):
            setattr(W, attr, val)
    ctx = W.build_world(bpy.context.scene)
    scene = bpy.context.scene
    scene.render.resolution_x = 640
    scene.render.resolution_y = 360
    scene.render.engine = normalize_engine_id("BLENDER_EEVEE")
    scene.view_settings.view_transform = "Standard"
    # blue-hour preview world: deep blue ambient (the ladder refines later)
    world = bpy.data.worlds.new("TFOG_bluehour_preview")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0.05, 0.08, 0.16, 1.0)
        bg.inputs[1].default_value = 1.4
    # train window strips + lamps are emissive now; park trains ON-STAGE for
    # the look (express mid-platform, local at the S face) to see them lit.
    for name, x in (("express_root", -20.0), ("local_root", -15.0)):
        root = bpy.data.objects.get(name)
        if root:
            root.location = (x, root.location.y, root.location.z)
            root.keyframe_insert("location")  # static park pose
    # fog ON at preview density
    fog = bpy.data.objects.get("fog_box")
    if fog:
        fog.hide_render = False
    # fill light from the north so the platform reads (blue-hour fill)
    sun = bpy.data.lights.new("TFOG_previz_fill", "SUN")
    sun.energy = 1.2
    sun.color = (0.55, 0.65, 1.0)
    sun_obj = bpy.data.objects.new("TFOG_previz_fill", sun)
    scene.collection.objects.link(sun_obj)
    sun_obj.rotation_euler = (math.radians(70), 0, math.radians(160))
    sun.angle = math.radians(40)

    views = [
        ("aerial", (-38, -20, 20), (0, 0, 0), 24),
        ("track_n", (6, -12.5, 1.2), (-6, -2, 1.8), 30),
        ("platform_w", (-24, 0.0, 1.7), (10, 0.5, 1.6), 28),
        ("board_close", (3.5, -2.5, 2.2), (0, 0.5, 2.6), 40),
    ]
    for name, loc, aim, lens in views:
        cam = _cam(f"LOOK_{name}", loc, aim, lens)
        scene.camera = cam
        scene.render.filepath = str(OUT / f"tfog_world_{name}.png")
        bpy.ops.render.render(write_still=True)
        print(f"[tfog_look] wrote {name}")
    print(f"[tfog_look] DONE -> {OUT}")


if __name__ == "__main__":
    main()
