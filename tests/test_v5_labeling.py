"""
test_v5_labeling.py — D16 semantic labeling regression (label_objects +
split_mesh + validator kit_semantic + manifest field).

In-process (runs INSIDE Blender like t/v-suites):

  L1  all-or-nothing: unknown id aborts, ZERO props written
  L2  charset law: space / dot / KIT_ANNOT* rejected
  L3  confidence vocabulary enforced
  L4  additive props (rename default false): kit_label(+conf) set, names kept
  L5  idempotent re-run: everything 'unchanged'
  L6  rename:true unique targets: Mesh.001 -> pillar
  L7  duplicate labels in batch -> _2 suffix; on_collision=fail raises
  L8  collision with existing scene object -> suffix / fail
  L9  two-phase rename verified by re-read; old ids gone
  L10 kit_semantic written for gate-relevant label, REMOVED on relabel
  L11 validator hazard regression: renamed ceiling STILL excluded (prop)
  L12 report JSON exists after success; failed plan leaves NO report
  L13 split dry-run: 3-box merged mesh -> part_count=3, zero residue
  L14 split mutate: source name on largest, _pNNN names, materials kept
  L15 preconditions: co-user + modifier refuse; ack_risks proceeds
  L16 single-component split refuses cleanly
  L17 manifest kit_label mandatory field (null when unlabeled)
  L18 apply_mutation end-to-end (op surface + PARAM_DOCS warn-keys)

Run:
  ./scripts/blrun.sh --background --python tests/test_v5_labeling.py --
"""
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS = os.path.abspath(os.path.join(_HERE, "..", "scripts"))
for _p in (_SCRIPTS,):
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

import bpy  # noqa: E402
import semantic_lib as SL  # noqa: E402
import validate_scene as vs  # noqa: E402

FAIL = []
_OUT = os.path.join(os.path.dirname(_HERE), "output", "tests", "v5")
os.makedirs(_OUT, exist_ok=True)


def check(label, got, expect):
    ok = got == expect
    if not ok:
        FAIL.append(f"{label}: got {got!r}, expected {expect!r}")
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}")


def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def make_merged_boxes(name="Level"):
    """Three disjoint boxes joined into ONE mesh (the 'continuous import')."""
    objs = []
    for i in range(3):
        bpy.ops.mesh.primitive_cube_add(size=0.4, location=(i * 2, 0, 0.2))
        objs.append(bpy.context.active_object)
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    objs[0].name = name
    return objs[0]


def opaque_pair():
    bpy.ops.mesh.primitive_cylinder_add(radius=0.1, depth=2.0,
                                        location=(1, -1, 1.0))
    bpy.context.active_object.name = "Mesh.001"
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.2, location=(-1, -1, 0.2))
    bpy.context.active_object.name = "Mesh.002"


def raises(fn):
    try:
        fn()
        return False
    except RuntimeError:
        return True


def main():
    # ---------------- L1: all-or-nothing -------------------------------
    clear()
    opaque_pair()
    if raises(lambda: SL.label_objects({"Mesh.001": "pillar",
                                        "Nope": "ghost"})):
        check("L1.abort", bpy.data.objects["Mesh.001"].get("kit_label"),
              None)
    else:
        check("L1.abort", "no-raise", "RuntimeError")

    # ---------------- L2: charset law ----------------------------------
    for bad in ("my label", "pillar.x", "KIT_ANNOT_evil"):
        ok = raises(lambda b=bad: SL.label_objects({"Mesh.001": b}))
        check(f"L2.reject({bad!r})", ok, True)

    # ---------------- L3: confidence vocabulary ------------------------
    check("L3.bad_conf",
          raises(lambda: SL.label_objects(
              {"Mesh.001": {"label": "pillar", "confidence": "sure"}})),
          True)

    # ---------------- L4: additive props (default no rename) -----------
    clear()
    opaque_pair()
    rep = SL.label_objects({"Mesh.001": {"label": "pillar",
                                         "confidence": "high"},
                            "Mesh.002": "crate"})
    check("L4.prop", bpy.data.objects["Mesh.001"].get("kit_label"),
          "pillar")
    check("L4.conf", bpy.data.objects["Mesh.001"].get("kit_label_conf"),
          "high")
    check("L4.names_kept", bpy.data.objects["Mesh.001"].name, "Mesh.001")
    check("L4.kept_count", len(rep["kept"]), 2)

    # ---------------- L5: idempotent re-run ----------------------------
    rep2 = SL.label_objects({"Mesh.001": {"label": "pillar",
                                          "confidence": "high"},
                             "Mesh.002": "crate"})
    check("L5.unchanged", sorted(rep2["unchanged"]),
          ["Mesh.001", "Mesh.002"])
    check("L5.no_renames", rep2["renamed"], [])

    # ---------------- L6: rename unique --------------------------------
    clear()
    opaque_pair()
    SL.label_objects({"Mesh.001": "pillar"}, rename=True)
    check("L6.renamed", bpy.data.objects.get("pillar") is not None, True)
    check("L6.old_gone", bpy.data.objects.get("Mesh.001"), None)
    check("L6.prop_carried",
          bpy.data.objects["pillar"].get("kit_label"), "pillar")

    # ---------------- L7: duplicate labels in batch --------------------
    clear()
    opaque_pair()
    SL.label_objects({"Mesh.001": "pillar", "Mesh.002": "pillar"},
                     rename=True)
    names = sorted(o.name for o in bpy.data.objects if o.type == "MESH")
    check("L7.suffixed", names, ["pillar", "pillar_2"])
    check("L7.fail_mode",
          raises(lambda: SL.label_objects(
              {"Mesh.001": "crate", "Mesh.002": "crate"},
              rename=True, on_collision="fail")), True)

    # ---------------- L8: collision with existing object ---------------
    clear()
    opaque_pair()
    bpy.ops.mesh.primitive_cube_add(size=0.3, location=(5, 5, 0.15))
    bpy.context.active_object.name = "pillar"
    SL.label_objects({"Mesh.001": "pillar"}, rename=True)
    check("L8.suffix", "pillar_2" in
          [o.name for o in bpy.data.objects], True)
    check("L8.fail_mode",
          raises(lambda: SL.label_objects(
              {"Mesh.002": "pillar"}, rename=True, on_collision="fail")),
          True)

    # ---------------- L9: two-phase verify by re-read ------------------
    clear()
    opaque_pair()
    rep = SL.label_objects({"Mesh.001": "pillar", "Mesh.002": "ball"},
                           rename=True)
    check("L9.renamed_pairs", rep["renamed"],
          [{"from": "Mesh.001", "to": "pillar"},
           {"from": "Mesh.002", "to": "ball"}])
    check("L9.props_after_rename",
          (bpy.data.objects["pillar"].get("kit_label"),
           bpy.data.objects["ball"].get("kit_label")),
          ("pillar", "ball"))

    # ---------------- L10: kit_semantic write/remove -------------------
    clear()
    opaque_pair()
    SL.label_objects({"Mesh.001": "ceiling_lamp"}, rename=True)
    check("L10.marked",
          bpy.data.objects["ceiling_lamp"].get("kit_semantic"),
          "ceiling_lamp")
    SL.label_objects({"ceiling_lamp": "chair"}, rename=True)
    check("L10.cleared", bpy.data.objects["chair"].get("kit_semantic"),
          None)

    # ---------------- L11: validator hazard regression -----------------
    clear()
    opaque_pair()
    SL.label_objects({"Mesh.001": "ceiling_lamp"}, rename=True)
    v = vs.validate_scene()
    check("L11.labeled_excluded",
          any(i["object"] == "ceiling_lamp" for i in v["issues"]), False)
    SL.label_objects({"ceiling_lamp": "hanging_thing"}, rename=True)
    v2 = vs.validate_scene()
    check("L11.rename_kept_exclusion",
          any(i["object"] == "hanging_thing" for i in v2["issues"]),
          False)
    # legacy fallback: unlabeled scene with a NAME-matched ceiling
    clear()
    bpy.ops.mesh.primitive_cube_add(size=4, location=(0, 0, 2.6))
    bpy.context.active_object.name = "Ceiling"
    v3 = vs.validate_scene()
    check("L11.legacy_fallback",
          any(i["object"] == "Ceiling" for i in v3["issues"]), False)

    # ---------------- L12: report artifacts ----------------------------
    clear()
    opaque_pair()
    rp = os.path.join(_OUT, "labels_L12.json")
    SL.label_objects({"Mesh.001": "pillar"}, rename=True,
                     report_path=rp)
    data = json.load(open(rp))
    check("L12.report_rows", data["rows"][0]["current_name"], "Mesh.001")
    check("L12.report_ok", data["ok"], True)
    check("L12.fail_leaves_no_report",
          raises(lambda: SL.label_objects(
              {"Mesh.002": "crate", "Nope": "x"},
              report_path=os.path.join(_OUT, "should_not_exist.json"))),
          True)
    check("L12.no_partial_report",
          os.path.exists(os.path.join(_OUT, "should_not_exist.json")),
          False)

    # ---------------- L13: split dry-run --------------------------------
    clear()
    make_merged_boxes()
    dry = SL.analyze_split(bpy.data.objects["Level"])
    check("L13.part_count", dry["part_count"], 3)
    check("L13.zero_residue", len(bpy.context.scene.objects), 1)
    check("L13.risks_empty", dry["risks"], [])

    # ---------------- L14: split mutate ---------------------------------
    clear()
    src = make_merged_boxes()
    red = bpy.data.materials.new("Red")
    red.diffuse_color = (0.9, 0.1, 0.1, 1.0)
    src.data.materials.append(red)
    rep = SL.split_object(src)
    names = sorted(p["name"] for p in rep["parts"])
    check("L14.names", names,
          ["Level", "Level_p002", "Level_p003"])
    check("L14.count", rep["part_count"], 3)
    check("L14.materials", rep["materials_inherited"], True)
    check("L14.objects", len(bpy.context.scene.objects), 3)

    # ---------------- L15: preconditions --------------------------------
    clear()
    a = make_merged_boxes("Shared")
    b = make_merged_boxes("CoUser")
    b.data = a.data  # glTF-style co-user mesh data
    check("L15.couser_refused",
          raises(lambda: SL.split_object(a)), True)
    check("L15.couser_ack_ok", SL.split_object(a, ack_risks=True)["ok"],
          True)
    check("L15.couser_single_user", a.data.users, 1)
    clear()
    make_merged_boxes("Modded")
    bpy.data.objects["Modded"].modifiers.new("S", "SUBSURF")
    check("L15.modifier_refused",
          raises(lambda: SL.split_object(bpy.data.objects["Modded"])),
          True)

    # ---------------- L16: single component refuses ---------------------
    clear()
    bpy.ops.mesh.primitive_cube_add(size=0.5, location=(0, 0, 0.25))
    bpy.context.active_object.name = "Solid"
    check("L16.dry_one",
          SL.analyze_split(bpy.data.objects["Solid"])["part_count"], 1)
    check("L16.split_refused",
          raises(lambda: SL.split_object(bpy.data.objects["Solid"])),
          True)

    # ---------------- L17: manifest kit_label field ---------------------
    clear()
    opaque_pair()
    import look
    rows = {r["id"]: r for r in look._manifest() if r["type"] == "MESH"}
    check("L17.key_present_unlabeled",
          all("kit_label" in r for r in rows.values()), True)
    check("L17.unlabeled_null",
          all(r["kit_label"] is None for r in rows.values()), True)
    SL.label_objects({"Mesh.001": "pillar"})
    rows2 = {r["id"]: r for r in look._manifest() if r["type"] == "MESH"}
    check("L17.labeled_value", rows2["Mesh.001"]["kit_label"], "pillar")

    # ---------------- L19: manifest world_bbox (handoff law) ------------
    # A non-vision consumer reasons ONLY from the manifest; dims_m is
    # local size and goes WRONG under rotation, so every MESH row must
    # carry the world-space AABB. Rotated fixture proves it.
    clear()
    bpy.ops.mesh.primitive_cube_add(size=1, location=(2, 0, 0.5))
    rot = bpy.context.active_object
    rot.name = "RotBox"
    rot.rotation_euler = (0, 0, 3.14159 / 4)  # 45° yaw — AABB ≠ dims
    rows3 = {r["id"]: r for r in look._manifest() if r["type"] == "MESH"}
    wb = rows3["RotBox"]["world_bbox"]
    import math as _math
    half_diag = 0.5 * _math.sqrt(2)  # 45° yaw AABB half-extent in XY
    ok_min = all(abs(a - b) < 0.01 for a, b in zip(
        wb["min"], [2 - half_diag, -half_diag, 0.0]))
    ok_max = all(abs(a - b) < 0.01 for a, b in zip(
        wb["max"], [2 + half_diag, half_diag, 1.0]))
    check("L19.world_bbox_present",
          all("world_bbox" in r for r in rows3.values()), True)
    check("L19.world_bbox_rotated_min", ok_min, True)
    check("L19.world_bbox_rotated_max", ok_max, True)
    # under 45° yaw the naive centroid±dims/2 box would be 1x1x1 — the
    # bug class this field kills:
    naive_wrong = (abs((wb["max"][0] - wb["min"][0]) - 1.0) > 0.3)
    check("L19.world_bbox_not_naive_dims", naive_wrong, True)

    # ---------------- L18: op surface end-to-end ------------------------
    clear()
    opaque_pair()
    import apply_patch as AP
    AP.apply_mutation({"op": "label_objects",
                       "labels": {"Mesh.001": "pillar",
                                  "Mesh.002": "ball"},
                       "rename": True})
    check("L18.renamed", bpy.data.objects.get("pillar") is not None, True)
    AP.apply_mutation({"op": "split_mesh", "id": "ball",
                       "mode": "dry-run"})  # Mesh.002 was renamed 'ball'
    check("L18.dry_no_residue", len(bpy.context.scene.objects), 2)

    # ---------------- L19-21: region cut (welded geometry) --------------
    clear()
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=10, y_subdivisions=10,
                                    size=6, location=(0, 0, 0))
    floor = bpy.context.active_object
    bpy.ops.mesh.primitive_cylinder_add(radius=0.3, depth=2.4,
                                        location=(1.5, 0, 1.2),
                                        vertices=12)
    pil = bpy.context.active_object
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
    w = bpy.data.objects["LevelWelded"]
    check("L19.welded_one_component", SL.analyze_split(w)["part_count"], 1)
    region = {"min": [1.1, -0.45, -0.01], "max": [1.9, 0.45, 2.5]}
    rdry = SL.analyze_region(w, region)
    check("L20.region_faces", rdry["faces_to_cut"] > 0, True)
    check("L20.zero_residue", len(bpy.context.scene.objects), 1)
    check("L20.new_id_charset",
          raises(lambda: SL.split_region(
              w, region, new_id="bad.id")), True)
    rep = SL.split_region(w, region, new_id="pillar")
    check("L21.cut_object", bpy.data.objects.get("pillar") is not None,
          True)
    check("L21.source_kept",
          bpy.data.objects.get("LevelWelded") is not None, True)
    check("L21.new_bbox",
          rep["new_object_bbox"]["min"][2] >= -0.01, True)
    SL.label_objects({"pillar": "pillar"})
    check("L21.labelable", bpy.data.objects["pillar"].get("kit_label"),
          "pillar")

    # --------------------------------------------------------------------
    print(f"\n[test_v5] {'ALL PASS' if not FAIL else 'FAILURES:'}")
    for f in FAIL:
        print(f"  [FAIL] {f}")
    if FAIL:
        sys.exit(1)


main()
