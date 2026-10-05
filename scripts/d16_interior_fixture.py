"""d16_interior_fixture.py — D16 dogfood fixture: an 'imported' interior.

Simulates a downloadable level/interior asset:
  Mesh.000  welded room shell: floor grid + 3.5 walls (doorway) — the
            wall boxes are integer-aligned and remove_doubles-welded to
            the floor, so it is ONE continuous component (no loose parts).
  Mesh.001  'props sheet': barrel + crate + table + ball + cone + bench
            joined into ONE object — 6 DISCONNECTED islands, one datablock.
  Mesh.002  lamp: post cylinder + head sphere joined (2 islands).

No semantic names anywhere. Saves interior_import.blend and exits — the
rest of the session treats it as a foreign import.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import bpy


def box(x0, x1, y0, y1, z0, z1):
    bpy.ops.mesh.primitive_cube_add(size=1,   # 1m cube -> scale == exact span
                                    location=((x0 + x1) / 2,
                                              (y0 + y1) / 2,
                                              (z0 + z1) / 2))
    o = bpy.context.active_object
    o.scale = ((x1 - x0), (y1 - y0), (z1 - z0))
    bpy.ops.object.transform_apply(scale=True)
    return o


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)

    # ---- Mesh.000: welded room shell (floor + walls + door post) ------
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=10, y_subdivisions=10,
                                    size=10, location=(0, 0, 0))
    shell = bpy.context.active_object
    parts = [shell,
             box(-5, -1, 4.8, 5.0, 0, 2.5),   # wall A (x -5..-1)
             box(-1, 1, 4.8, 5.0, 0, 2.5),    # door post block (welded)
             box(1, 5, 4.8, 5.0, 0, 2.5),     # wall B
             box(-5, 5, 4.8, 5.0, 2.0, 2.5),  # lintel over the doorway
             box(-5, -4.8, -5, 5, 0, 2.5),    # west wall
             box(4.8, 5, -5, 5, 0, 2.5),      # east wall
             box(1.2, 1.8, 3.8, 4.8, 0, 2.5)] # pillar engaged into wall B
    bpy.ops.object.select_all(action="DESELECT")
    for o in parts:
        o.select_set(True)
    bpy.context.view_layer.objects.active = shell
    bpy.ops.object.join()
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=0.01)   # weld floor<->walls
    bpy.ops.object.mode_set(mode="OBJECT")
    shell.name = "Mesh.000"

    # ---- Mesh.001: props sheet (6 disconnected islands, one object) ---
    props = []
    bpy.ops.mesh.primitive_cylinder_add(radius=0.25, depth=0.7,
                                        location=(-3, -3, 0.35),
                                        vertices=16)
    props.append(bpy.context.active_object)       # barrel
    bpy.ops.mesh.primitive_cube_add(size=0.6, location=(-1.5, -3, 0.3))
    props.append(bpy.context.active_object)       # crate
    bpy.ops.mesh.primitive_cube_add(location=(0.5, -3, 0.375))
    t = bpy.context.active_object                 # table top
    t.scale = (1.2, 0.7, 0.05)
    bpy.ops.object.transform_apply(scale=True)
    props.append(t)
    for lx in (-0.35, 0.35):
        for ly in (-0.25, 0.25):
            bpy.ops.mesh.primitive_cube_add(size=0.08,
                                            location=(0.5 + lx, -3 + ly,
                                                      0.15))
            props.append(bpy.context.active_object)   # table legs
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.25,
                                         location=(2.5, -3, 0.25))
    props.append(bpy.context.active_object)       # ball
    bpy.ops.mesh.primitive_cone_add(radius1=0.2, radius2=0.0, depth=0.5,
                                    location=(3.5, -3, 0.25))
    props.append(bpy.context.active_object)       # cone
    bpy.ops.mesh.primitive_cube_add(location=(-3, 0.5, 0.225))
    b = bpy.context.active_object                 # bench
    b.scale = (0.5, 1.2, 0.075)
    bpy.ops.object.transform_apply(scale=True)
    props.append(b)
    bpy.ops.object.select_all(action="DESELECT")
    for o in props:
        o.select_set(True)
    bpy.context.view_layer.objects.active = props[0]
    bpy.ops.object.join()
    bpy.context.active_object.name = "Mesh.001"

    # ---- Mesh.002: lamp (post + head, 2 islands) ----------------------
    lamps = []
    bpy.ops.mesh.primitive_cylinder_add(radius=0.06, depth=3.0,
                                        location=(-4.2, 2.0, 1.5),
                                        vertices=10)
    lamps.append(bpy.context.active_object)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.18,
                                         location=(-4.2, 2.0, 3.1))
    lamps.append(bpy.context.active_object)
    bpy.ops.object.select_all(action="DESELECT")
    for o in lamps:
        o.select_set(True)
    bpy.context.view_layer.objects.active = lamps[0]
    bpy.ops.object.join()
    bpy.context.active_object.name = "Mesh.002"

    out = os.path.join(os.path.dirname(_HERE), "output", "d16")
    os.makedirs(out, exist_ok=True)
    # camera + light for the look pass
    bpy.ops.object.light_add(type="SUN", location=(4, -4, 6))
    bpy.context.active_object.data.energy = 3.0
    bpy.context.scene.name = "ImportedInterior"
    bpy.ops.wm.save_as_mainfile(
        filepath=os.path.join(out, "interior_import.blend"))
    print(f"[fixture] saved: {sorted(o.name for o in bpy.data.objects)}")
    print(f"[fixture] blend: {os.path.join(out, 'interior_import.blend')}")


main()
