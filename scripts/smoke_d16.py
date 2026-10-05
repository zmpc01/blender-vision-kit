"""smoke_d16.py — first-fire smoke of semantic_lib (label_objects + split_mesh).
Runs inside Blender; NOT a regression suite (that's test_v5_labeling)."""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import bpy
import semantic_lib as SL


def build_fixture():
    """Three disjoint boxes as ONE merged mesh + two separate opaque ids."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.mesh.primitive_cube_add(size=0.4, location=(0, 0, 0.2))
    a = bpy.context.active_object
    bpy.ops.mesh.primitive_cube_add(size=0.4, location=(2, 0, 0.2))
    b = bpy.context.active_object
    bpy.ops.mesh.primitive_cube_add(size=0.4, location=(4, 0, 0.2))
    c = bpy.context.active_object
    # merge a+b+c into one object (the "continuous imported mesh")
    bpy.ops.object.select_all(action="DESELECT")
    for o in (a, b, c):
        o.select_set(True)
    bpy.context.view_layer.objects.active = a
    bpy.ops.object.join()
    a.name = "Level_Merged"
    # two opaque separate meshes (the "Mesh.001" style import)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.1, depth=2.0,
                                        location=(1, -1, 1.0))
    bpy.context.active_object.name = "Mesh.001"
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.2, location=(-1, -1, 0.2))
    bpy.context.active_object.name = "Mesh.002"
    return a


def main():
    build_fixture()
    dry = SL.analyze_split(bpy.data.objects["Level_Merged"])
    print(f"[smoke] dry-run part_count={dry['part_count']} "
          f"risks={dry['risks']}")
    assert dry["part_count"] == 3, dry["part_count"]
    n_before = len(bpy.context.scene.objects)
    assert n_before == 3  # zero residue

    rep = SL.split_object(bpy.data.objects["Level_Merged"])
    names = sorted(p["name"] for p in rep["parts"])
    print(f"[smoke] split -> {names}")
    assert rep["part_count"] == 3
    assert "Level_Merged" in names, names  # source name preserved
    assert len(bpy.context.scene.objects) == 5  # 3 parts + 2 opaque

    lab = SL.label_objects({
        "Mesh.001": {"label": "pillar", "confidence": "high"},
        "Mesh.002": "ball",
        names[names.index("Level_Merged")]: {"label": "wall"},
        names[0] if names[0] != "Level_Merged" else names[1]: "slab",
    }, rename=True)
    print(f"[smoke] label+rename ok={lab['ok']} "
          f"renamed={lab['renamed']}")
    assert bpy.data.objects["pillar"].get("kit_label") == "pillar"
    assert bpy.data.objects["wall"].get("kit_label") == "wall"
    # idempotent re-run
    lab2 = SL.label_objects({"pillar": {"label": "pillar",
                                        "confidence": "high"},
                             "ball": "ball"}, rename=True)
    assert len(lab2["unchanged"]) == 2, lab2["unchanged"]
    # semantic marker + validator interplay
    o = bpy.data.objects["pillar"]
    assert o.get("kit_semantic") is None  # 'pillar' not gate-relevant
    SL.label_objects({"ball": "ceiling_lamp"}, rename=True)
    assert bpy.data.objects["ceiling_lamp"].get("kit_semantic") == \
        "ceiling_lamp"
    import validate_scene as vs
    v = vs.validate_scene()
    fl = [i for i in v["issues"] if i["type"] == "floating"]
    print(f"[smoke] validator floating issues: {[i['object'] for i in fl]}")
    assert not any(i["object"] == "ceiling_lamp" for i in fl)
    # rename a ceiling: coverage must SURVIVE (the D16 audit hazard)
    SL.label_objects({"ceiling_lamp": "hanging_thing"}, rename=True)
    v2 = vs.validate_scene()
    fl2 = [i for i in v2["issues"] if i["type"] == "floating"]
    assert not any(i["object"] == "hanging_thing" for i in fl2)
    print("[smoke] rename-strips-coverage hazard: FIXED (prop carries it)")
    print("[smoke] ALL SMOKE CHECKS PASS")


def welded_fixture():
    """The user's hard case: floor + pillar WELDED into one connected
    mesh (level/interior style). Loose-parts split must report 1 part;
    the REGION cut is the way out."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=10, y_subdivisions=10,
                                    size=6, location=(0, 0, 0))
    floor = bpy.context.active_object
    bpy.ops.mesh.primitive_cylinder_add(radius=0.3, depth=2.4,
                                        location=(1.5, 0, 1.2),
                                        vertices=12)
    pil = bpy.context.active_object
    # weld: join + merge-by-distance at the shared ring (pillar base
    # touches floor at z=0) -> one truly continuous component
    bpy.ops.object.select_all(action="DESELECT")
    floor.select_set(True)
    pil.select_set(True)
    bpy.context.view_layer.objects.active = floor
    bpy.ops.object.join()
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=0.001)
    bpy.ops.object.mode_set(mode="OBJECT")
    floor.name = "LevelWelded"
    return floor


def welded_checks():
    src = welded_fixture()
    dry = SL.analyze_split(src)
    assert dry["part_count"] == 1, f"welded mesh found {dry['part_count']} parts"
    print("[smoke] welded mesh: loose-parts dry-run reports part_count=1 "
          "(correct — nothing loose)")
    # vision-driven region cut: I 'looked' — the pillar sits at x=1.5,y=0
    region = {"min": [1.1, -0.45, -0.01], "max": [1.9, 0.45, 2.5]}
    rdry = SL.analyze_region(src, region)
    print(f"[smoke] region dry-run: verts={rdry['verts_in_region']} "
          f"faces_to_cut={rdry['faces_to_cut']} "
          f"bbox={rdry['captured_bbox']}")
    assert rdry["faces_to_cut"] > 0
    rep = SL.split_region(src, region, new_id="pillar")
    print(f"[smoke] region cut -> '{rep['new_object']}' "
          f"({rep['faces_cut']} faces cut)")
    assert bpy.data.objects.get("pillar") is not None
    assert bpy.data.objects.get("LevelWelded") is not None
    # the cut object is now labelable like any other
    SL.label_objects({"pillar": {"label": "pillar", "confidence": "high"}})
    assert bpy.data.objects["pillar"].get("kit_label") == "pillar"
    print("[smoke] welded-interior region cut: PASS (continuous geometry "
          "is now breakable + labelable)")


welded_checks()

main()
