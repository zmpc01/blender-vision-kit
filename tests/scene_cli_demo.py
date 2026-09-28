"""scene_cli_demo.py — demo scene for audit_contacts.py CLI tests.

A table + mug scene in a FIXED buggy state: mug 10mm into the tabletop,
bowl sunk 20mm into the tabletop. audit_contacts.py puts this tests/ dir
on sys.path (so `--scene scene_cli_demo` resolves); also importable
directly. Same scene as placement-lab experiments/scene_cli_demo.py.
"""
import bpy


def _box(name, size, loc, color=(0.6, 0.5, 0.4)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc,
                                    scale=(size[0], size[1], size[2]))
    o = bpy.context.active_object
    o.name = name
    m = bpy.data.materials.new(name + "_m")
    m.diffuse_color = (*color, 1.0)
    o.data.materials.append(m)
    return o


def build_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _box("Ground", (8, 8, 0.1), (0, 0, -0.05), (0.35, 0.4, 0.35))
    top = _box("TableTop", (1.2, 0.8, 0.05), (0, 0, 0.725), (0.55, 0.4, 0.3))
    legs = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            legs.append(_box(f"Leg{sx}{sy}", (0.06, 0.06, 0.7),
                             (sx * 0.52, sy * 0.32, 0.35), (0.45, 0.33, 0.25)))
    bpy.ops.object.select_all(action='DESELECT')
    for o in [top] + legs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = top
    bpy.ops.object.join()
    table = bpy.context.active_object
    table.name = "Table"
    bpy.ops.object.transform_apply(location=True, scale=True)

    # Mug: 10mm INTO the tabletop (top of mug pokes through)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.04, depth=0.09,
                                        location=(0.2, 0.1, 0.735))
    mug = bpy.context.active_object
    mug.name = "Mug"
    mm = bpy.data.materials.new("Mug_m")
    mm.diffuse_color = (0.8, 0.8, 0.85, 1.0)
    mug.data.materials.append(mm)

    # Bowl: sunk 20mm into the tabletop
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.08, segments=24,
                                         ring_count=12,
                                         location=(-0.2, -0.1, 0.715))
    bowl = bpy.context.active_object
    bowl.name = "Bowl"
    bowl.scale = (1.0, 1.0, 0.5)
    bm = bpy.data.materials.new("Bowl_m")
    bm.diffuse_color = (0.7, 0.5, 0.2, 1.0)
    bowl.data.materials.append(bm)

    bpy.context.view_layer.update()
    return {"objects": ["Ground", "Table", "Mug", "Bowl"]}


def animate(ctx, *, start_frame=1, n_frames=24):
    pass
