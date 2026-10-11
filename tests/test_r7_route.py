"""test_r7_route.py — pure-Python regression for the blind route planner.

Covers the direction-inference rules WITH the live R7 cases (the
mislabel saga), the vision-override path, the slab-bounds clamp, and
bed-avoidance. No bpy (planner is pure Python).

Run:  python3 tests/test_r7_route.py   (ALL PASS marker convention)
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "scripts"))

import r7_route_planner as RP  # noqa: E402

FAILS = []


def check(name, cond, detail=""):
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}"
          + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        FAILS.append(name)


def row(rid, label, bb, kind="MESH"):
    return {"id": rid, "type": kind, "kit_label": label,
            "world_bbox": {"min": bb[0], "max": bb[1]}}


def mesh_row(rid, label, bb):
    return row(rid, label, bb)


# ------------------------------------------------------------- fixtures
# live R7 geometry (post-correction labels)
ACTOR = mesh_row("Driver.Mannequin", None,
                 ([-1.1, 4.87, -0.01], [-0.43, 5.95, 1.86]))
FLOOR = mesh_row("Cube.001", "floor", ([-3.05, -2.93, 0.0], [3.5, 15.97, 0.0]))
MEZZ = mesh_row("mezzanine_slab", "mezzanine",
                ([-3.05, 8.47, 2.7], [3.5, 15.97, 2.92]))
STAIR_REAL = mesh_row("Plane.003", "stairs",
                      ([2.5, 8.49, 0.10], [3.43, 13.76, 2.81]))
# the R6-era WRONG stair label (fragment abutting the slab from outside)
STAIR_FRAG = mesh_row("stairs", "stairs",
                      ([3.3, 7.31, 0.0], [3.5, 8.48, 2.91]))
BED = mesh_row("Bed02", "bed", ([-2.47, 9.47, 2.93], [-0.35, 11.13, 3.39]))

OVERRIDE = {"top_at_max_end": True, "evidence": "test tread map"}

print("test_r7_route")
print("1. infer_stair_direction — abut-from-outside (R6 fragment)")
ax, top = RP.infer_stair_direction(STAIR_FRAG, MEZZ)
check("run axis = y", ax == 1)
check("top at max end (adjacent-to-slab rule)", top is True)

print("2. infer_stair_direction — overlap/under-slab (real Plane.003)")
ax, top = RP.infer_stair_direction(STAIR_REAL, MEZZ)
check("bbox-ambiguous -> None (STOP-AND-FLAG class)", ax is None and top
      is None)

print("3. plan() blind on ambiguous stair -> STOP-AND-FLAG")
route = RP.plan([FLOOR, MEZZ, STAIR_REAL, ACTOR])
check("flag present", len(route["stop_and_flag"]) == 1)
check("no waypoints emitted", not route["waypoints"])
check("names the ambiguity", "cannot be derived" in
      route["stop_and_flag"][0]["why"])

print("4. plan() with vision override -> correct +y route")
route = RP.plan([FLOOR, MEZZ, STAIR_REAL, ACTOR], vision_override=OVERRIDE)
check("vision_assisted recorded", route["vision_assisted"] is True)
wp = {w["name"]: w for w in route["waypoints"]}
check("5 waypoints + walkin", len(route["waypoints"]) == 6)
check("stair base at min-y end", wp["W2_stair_base"]["xy"][1] == 8.49)
check("stair top at max-y end", wp["W3_stair_top"]["xy"][1] == 13.76)
check("base z = floor top", wp["W2_stair_base"]["z"] == 0.0)
check("top z = mezz top - 0.01 (top tread below slab)",
      abs(wp["W3_stair_top"]["z"] - 2.91) < 1e-9)
check("arrival beyond top (+y)", wp["W4_mezzanine"]["xy"][1] == 14.96)

print("5. walk-in clamped inside the slab bbox")
short_slab = mesh_row("mezzanine_slab", "mezzanine",
                      ([-3.05, 8.47, 2.7], [3.5, 12.2, 2.92]))
route = RP.plan([FLOOR, short_slab, STAIR_REAL, ACTOR],
                vision_override=OVERRIDE)
wp = {w["name"]: w for w in route["waypoints"]}
check("walkin clamped to slab max - 0.3",
      abs(wp["W5_walkin"]["xy"][1] - (12.2 - 0.3)) < 1e-6,
      str(wp["W5_walkin"]))

print("6. bed-avoidance shortens the walk-in")
# bed right where the walk-in would land (x near stair center 2.96)
bed2 = mesh_row("Bed99", "bed", ([2.7, 15.2, 2.93], [3.4, 16.0, 3.39]))
route = RP.plan([FLOOR, MEZZ, STAIR_REAL, ACTOR, bed2],
                vision_override=OVERRIDE)
wp = {w["name"]: w for w in route["waypoints"]}
check("walkin shortened to arrival + 0.3",
      abs(wp["W5_walkin"]["xy"][1] - (14.96 + 0.3)) < 1e-6,
      str(wp["W5_walkin"]))

print("7. missing labels -> STOP-AND-FLAG with missing list")
route = RP.plan([FLOOR, ACTOR])
check("flags missing stairs+mezzanine",
      sorted(route["stop_and_flag"][0]["missing"]) == ["mezzanine",
                                                       "stairs"])

print("8. labels_used resolved by label (largest footprint wins)")
dup_floor = mesh_row("other_floor", "floor", ([0, 0, 0], [0.1, 0.1, 0]))
route = RP.plan([dup_floor, FLOOR, MEZZ, STAIR_REAL, ACTOR],
                vision_override=OVERRIDE)
check("floor -> Cube.001", route["labels_used"]["floor"] == "Cube.001")

print()
if FAILS:
    print(f"FAILED: {len(FAILS)} — {FAILS}")
    sys.exit(1)
print("ALL PASS")
