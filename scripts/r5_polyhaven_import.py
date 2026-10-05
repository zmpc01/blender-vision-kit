"""r5_polyhaven_import.py — R5 lane: import a REAL downloaded asset.

Imports the fetched polyhaven CoffeeCart_01 glTF as-is (the honest
import state: vendor names, real transforms), then applies only the
normalization ANY agent must do with a downloaded model — measure,
scale to a sane size, ground to z=0 — and saves cart_import.blend for
the LOOK pass. No renaming, no splitting: the semantic pass treats it
as a foreign import.

Run:  ./scripts/blrun.sh --background --python scripts/r5_polyhaven_import.py
Requires: bash scripts/r5_polyhaven_fetch.sh first.
"""
import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import bpy

ASSETS = os.path.join(os.path.dirname(_HERE), "output", "r5", "assets")


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    gltf = os.path.join(ASSETS, "CoffeeCart_01_1k.gltf")
    if not os.path.exists(gltf):
        sys.exit(f"[r5] {gltf} missing — run scripts/r5_polyhaven_fetch.sh")
    bpy.ops.import_scene.gltf(filepath=gltf)
    imported = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    print(f"[r5] imported mesh objects: {[o.name for o in imported]}")
    print(f"[r5] as-imported dims: "
          f"{ {o.name: [round(v, 3) for v in o.dimensions] for o in imported} }")

    # normalize: scale so the largest dim ~ 1.6m, ground min-z to 0,
    # center on origin. Real downloads arrive in vendor units/orientations.
    bpy.ops.object.select_all(action="SELECT")
    bpy.context.view_layer.objects.active = imported[0]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    xs, ys, zs = [], [], []
    for o in imported:
        for c in o.bound_box:
            p = o.matrix_world @ type(o.location)(c)
            xs.append(p.x); ys.append(p.y); zs.append(p.z)
    largest = max(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))
    s = 1.6 / largest
    for o in imported:
        o.scale = (s, s, s)
    bpy.context.view_layer.update()
    xs, ys, zs = [], [], []
    for o in imported:
        for c in o.bound_box:
            p = o.matrix_world @ type(o.location)(c)
            xs.append(p.x); ys.append(p.y); zs.append(p.z)
    cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    for o in imported:
        o.location.x -= cx
        o.location.y -= cy
        o.location.z -= min(zs)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.context.view_layer.update()
    for o in imported:
        print(f"[r5] normalized {o.name}: dims="
              f"{[round(v, 3) for v in o.dimensions]} "
              f"loc={[round(v, 3) for v in o.location]}")

    bpy.ops.object.light_add(type="SUN", location=(3, -3, 5))
    bpy.context.active_object.data.energy = 3.0
    # the kit's look pass needs a camera — park one at a 3/4 view aimed
    # at the cart (the import itself has none)
    bpy.ops.object.camera_add(location=(1.8, -1.8, 1.4),
                              rotation=(math.radians(65), 0,
                                        math.radians(45)))
    bpy.context.scene.camera = bpy.context.active_object
    bpy.context.scene.name = "R5_PolyhavenImport"
    out = os.path.join(os.path.dirname(_HERE), "output", "r5")
    os.makedirs(out, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, "cart_import.blend"))
    print(f"[r5] saved: {os.path.join(out, 'cart_import.blend')}")


main()
