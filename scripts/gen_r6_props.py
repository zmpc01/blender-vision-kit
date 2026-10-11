"""Generate the R6 props placement patch (label-driven placement demo).

Replay note (R7): recreates the 4 R6 compose placements. Prop geometry
is kit primitives (the originals were identical in spirit; exact mesh
provenance is irrelevant to the placement protocol being exercised).
Support xy centers are read from the import manifest / cut reports —
center placements are the law (R6 edge-overhang lesson).

Run:  python3 scripts/gen_r6_props.py   (pure Python; emits patch JSON)
Then: apply_patch --patch output/r6/patch_props.json --save-blend ...
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAN = json.load(open(os.path.join(
    ROOT, "output/r6/look_import/look_manifest.json")))["manifest"]
MEZ = json.load(open(os.path.join(
    ROOT, "output/r6/report_cut_mezzanine.json")))

rows = {r["id"]: r for r in MAN if r["type"] == "MESH"}

def center_top(rid):
    bb = rows[rid]["world_bbox"]
    cx = (bb["min"][0] + bb["max"][0]) / 2
    cy = (bb["min"][1] + bb["max"][1]) / 2
    return cx, cy, bb["max"][2]

sx, sy, st = center_top("Chocofur_Free_Sideboard_01")   # sideboard top
tx, ty, tt = center_top("Box015.017")                   # coffee table top
fx, fy, ft = center_top("Cube.001")                     # floor (real floor)
mb = MEZ["new_object_bbox"]
mx = (mb["min"][0] + mb["max"][0]) / 2
my = (mb["min"][1] + mb["max"][1]) / 2
mz = mb["max"][2]                                       # mezzanine top

def loc(x, y, z_top):
    return [round(x, 3), round(y, 3), round(z_top + 0.5, 3)]

mutations = [
    # book_red -> sideboard
    {"op": "add_cube", "id": "book_red", "size": [0.21, 0.15, 0.03],
     "location": loc(sx, sy, st), "color": [0.75, 0.1, 0.1]},
    {"op": "place_on", "id": "book_red",
     "supports": ["Chocofur_Free_Sideboard_01"],
     "output": "output/r6/report_place_book.json"},
    # ball -> floor
    {"op": "add_sphere", "id": "ball", "radius": 0.11,
     "location": loc(-1.8, 3.0, ft), "color": [0.9, 0.6, 0.1]},
    {"op": "place_on", "id": "ball", "supports": ["Cube.001"],
     "output": "output/r6/report_place_ball.json"},
    # lantern -> mezzanine
    {"op": "add_cylinder", "id": "lantern", "radius": 0.09, "depth": 0.26,
     "location": loc(mx, my, mz), "color": [0.85, 0.65, 0.25]},
    {"op": "place_on", "id": "lantern", "supports": ["mezzanine_slab"],
     "output": "output/r6/report_place_lantern.json"},
    # mug -> coffee table (clearance: uneven recessed top, R6 lesson)
    {"op": "add_cylinder", "id": "mug", "radius": 0.043, "depth": 0.095,
     "location": loc(tx, ty, tt), "color": [0.15, 0.3, 0.7]},
    {"op": "place_on", "id": "mug", "supports": ["Box015.017"],
     "clearance": 0.006,
     "output": "output/r6/report_place_mug.json"},
]

json.dump({"load_blend": "output/r6/loft_labeled.blend",
           "mutations": mutations},
          open(os.path.join(ROOT, "output/r6/patch_props.json"), "w"))
print(f"props patch written: 4 add + 4 place_on")
print(f"  sideboard top {st:.3f} at ({sx:.2f},{sy:.2f})")
print(f"  table top     {tt:.3f} at ({tx:.2f},{ty:.2f})")
print(f"  floor top     {ft:.3f} at ({fx:.2f},{fy:.2f})")
print(f"  mezzanine top {mz:.3f} at ({mx:.2f},{my:.2f})")
