"""Generate the R6 labeling patch from the loft manifest (vision-decided schema).

Replay note (R7): this is the R6 generator committed verbatim PLUS the
post-blind-handoff label corrections integrated (marked CORRECTION
below). In the original R6 run the Sketchup family was mislabeled
lounge_chair/floor_lamp and the dining chairs + arc lamp were left null;
the fresh blind agent's spatial-anomaly report caught it and a fix patch
corrected 26 labels. Committing the corrected schema so the replay
produces the FINAL label state in one honest pass.

Run:  python3 scripts/gen_r6_labels.py   (pure Python; emits patch JSON)
Then: apply_patch --patch output/r6/patch_labels.json --save-blend ...
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAN = os.path.join(ROOT, "output/r6/look_import/look_manifest.json")
OUT = os.path.join(ROOT, "output/r6/patch_labels.json")

m = json.load(open(MAN))
ids = [r["id"] for r in m["manifest"] if r["type"] == "MESH"]
rows = {r["id"]: r for r in m["manifest"] if r["type"] == "MESH"}

labels = {}

def put(pattern_ids, label, conf):
    n = 0
    for i in pattern_ids:
        labels[i] = {"label": label, "confidence": conf}
        n += 1
    return n

counts = {}
# architecture (region-cut products + floor object) — render-verified HIGH
counts["floor"] = put(["Cube.001"], "floor", "high")
counts["wall"] = put(["Cube"], "wall", "high")
counts["ceiling"] = put(["ceiling_slab"], "ceiling", "high")
counts["mezzanine"] = put(["mezzanine_slab"], "mezzanine", "high")
# CORRECTION (R7, mesh-verified): Plane.003 is the ACTUAL climbable
# stair — 9 flat treads z 0.13->2.78 climbing +y from y 8.5 to y 13.7
# (tread map probe15/16: rise 0.34 / run 0.65, width x 2.6-3.4, arrives
# directly onto mezzanine_slab at y 13.8). The R6 schema labeled it
# "wall" (stairwell-wall guess) and labeled the x 3.3-3.5 y 7.3-8.5
# FRAGMENT object "stairs" — that object is the stair-shaft parapet
# (low wall z~0.3-0.4 + sloped top piece), NOT walkable. R7's nav
# attempt surfaced it: raycast-hug found no treads under the old label.
counts["stairs"] = put(["Plane.003"], "stairs", "high")
counts["wall"] = counts.get("wall", 0) + put(["stairs"], "wall", "medium")

fam = lambda p: [i for i in ids if i.startswith(p)]
counts["bed"] = put(fam("Bed"), "bed", "high")
counts["kitchen_unit"] = put(fam("kitchen"), "kitchen_unit", "high")
counts["partition_panel"] = put(fam("Panel_"), "partition_panel", "high")
counts["interior_window"] = put(fam("Window Panel") + ["Window"],
                                "interior_window", "high")
counts["sofa_module"] = put(fam("Object003."), "sofa_module", "high")
counts["shelf_unit"] = put(["Object001", "Object002", "Object003",
                            "Object004", "Object004.001", "Object004.002"],
                           "shelf_unit", "high")
counts["sideboard"] = put(["Chocofur_Free_Sideboard_01"], "sideboard", "high")
counts["rug"] = put(["Plane.002", "Object009"], "rug", "high")
counts["table"] = put(["Box015.017"], "table", "high")
counts["plant"] = put([i for i in ids if i.startswith(("Plant_", "Plant_Vase"))],
                      "plant", "high")

# CORRECTION (post-blind-handoff, R6): the Sketchup* cluster sits at
# y~0, z 2.7-5.1 with three glass globes on cables — it is the living-
# zone PENDANT LIGHT, not a lounge chair / floor lamp (the blind agent
# caught it from manifest reasoning; closeup render confirmed).
counts["pendant_light"] = put(fam("Sketchup"), "pendant_light", "high")
# CORRECTION: Cylinder.001 is the tall arc floor lamp by the sofa
# (survey render s1; was left unlabeled in the original pass).
counts["floor_lamp"] = put(["Cylinder.001"], "floor_lamp", "high")

# deco bulk (name-pattern families, not individually eyeballed)
deco = []
for p in ("Book_", "Vase_", "Cup_", "Candlestick_", "Glass_Board_",
          "Glass_", "Ball_Decor_", "Decor_", "Chocofur_Free_Details",
          "Chocofur_Free_25"):
    deco += fam(p)
counts["deco"] = put([i for i in deco if i not in labels], "deco", "medium")

# remaining architecture — geometry-derived (survey renders + bboxes)
counts["exterior_window"] = put(["Plane", "Plane.001"], "exterior_window", "high")
counts["ceiling"] = counts.get("ceiling", 0) + put(["Plane.004"], "ceiling", "high")
counts["ceiling"] = counts.get("ceiling", 0) + put(["Cube.003"], "ceiling", "medium")
counts["wall"] = counts.get("wall", 0) + put(
    ["Cube.002", "Cube.006"], "wall", "high")
rail_cands = ([f"Plane.{n:03d}" for n in range(8, 12)]
              + [f"Cube.{n:03d}" for n in range(7, 11)] + fam("Line"))
rail = [i for i in rail_cands if i in rows
        and rows[i]["world_bbox"]["min"][2] > 2.2
        and rows[i]["world_bbox"]["max"][2] < 3.95]
counts["railing"] = put(rail, "railing", "medium")
# Box015.* = ottomans/poufs completing the sectional (survey s1); .017 is
# the low coffee table in front of the sofa (white book on it in s1)
counts["sofa_module"] = counts.get("sofa_module", 0) + put(
    [i for i in fam("Box015") if i != "Box015.017"], "sofa_module", "medium")
counts["table"] = counts.get("table", 0) + put(["Box015.017"], "table", "medium")
# CORRECTION: Cube.004/005 are the two Windsor DINING CHAIRS in the
# dining zone (y~10.4-10.9; the blind agent reported them as unlabeled
# "pedestals" — closeup render identified them).
counts["chair"] = put(["Cube.004", "Cube.005"], "chair", "high")

mutations = [{"op": "delete_object", "id": "floor_slab"}]
# chunk the label op: one call, big map (op accepts arbitrary map size)
mutations.append({"op": "label_objects", "labels": labels,
                  "output": "output/r6/report_labels.json"})

json.dump({"load_blend": "output/r6/loft_cut_arch.blend",
           "mutations": mutations}, open(OUT, "w"))
print(f"labeled {len(labels)} of {len(ids)} meshes")
for k, v in counts.items():
    print(f"  {k:18s} {v}")
unlabeled = [i for i in ids if i not in labels]
print(f"unlabeled ({len(unlabeled)}): {unlabeled[:15]}")
