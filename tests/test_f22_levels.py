"""
test_f22_levels.py — F22 level-aware validator policy regression.

In-process (runs INSIDE Blender):

  F22.1  level-adjacency advisory: two abutting labeled level-family
         objects -> NO intersection issue, advisory recorded with depth
  F22.2  strict stays: unlabeled object overlapping a labeled family
         object -> still an intersection issue (gate bites)
  F22.3  containment extension: UNLABELED object FULLY inside a
         room-scale shell (volume ratio >= 50x) -> visible skip with
         'unverified' reason, no issue
  F22.3b same shell + small ratio (nested dup) -> still flags
  F22.4  gross escape: non-shell fam-fam near-coincident (depth>=0.5m,
         pct>=95) -> P1 issue, NOT an advisory
  F22.5  param override: level_families=set() disables the advisory
         (escape hatch for strict runs)

Run:
  ./scripts/blrun.sh --background --python tests/test_f22_levels.py --
"""
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


def check(label, got, expect):
    ok = got == expect
    if not ok:
        FAIL.append(f"{label}: got {got!r}, expected {expect!r}")
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}")


def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def box(name, size, loc):
    bpy.ops.mesh.primitive_cube_add(size=size, location=loc)
    o = bpy.context.active_object
    o.name = name
    return o


def issues_for(summ, pair):
    return [i for i in summ["issues"]
            if i["type"] == "intersection"
            and set(i["objects"]) == set(pair)]


def main():
    # ---------------- F22.1 adjacency advisory ----------------
    clear()
    box("KitA", 0.5, (0, 0, 0.25))
    box("KitB", 0.5, (0.48, 0, 0.25))   # 2cm overlap = vendor abutment
    SL.label_objects({"KitA": "kitchen_unit", "KitB": "kitchen_unit"})
    s = vs.validate_scene(ground_z=0.0)
    check("F22.1.no_issue", issues_for(s, ["KitA", "KitB"]), [])
    check("F22.1.advisory_count", s["adjacency_pairs_advisory"] >= 1, True)
    rec = [r for r in s["adjacency_worst"]
           if set(r["pair"]) == {"KitA", "KitB"}]
    check("F22.1.advisory_record", len(rec), 1)
    check("F22.1.advisory_depth", rec[0]["min_axis_depth_m"] > 0, True)

    # ---------------- F22.2 strict: unlabeled vs family ----------------
    clear()
    box("TableTop", 0.5, (0, 0, 0.4))
    box("Mug", 0.1, (0.03, 0, 0.62))    # sunk 3cm into the tabletop AABB
    SL.label_objects({"TableTop": "table"})
    s = vs.validate_scene(ground_z=0.0)
    check("F22.2.still_flags", len(issues_for(s, ["TableTop", "Mug"])), 1)

    # ---------------- F22.3 containment extension (unlabeled) --------
    clear()
    box("Shell", 10.0, (0, 0, 5.0))     # room-scale, 1000 m3
    box("Prop", 0.1, (0, 0, 0.05))      # 0.001 m3, fully inside
    SL.label_objects({"Shell": "room_shell"})
    s = vs.validate_scene(ground_z=0.0)
    check("F22.3.no_issue", issues_for(s, ["Shell", "Prop"]), [])
    sk = [x for x in s["contained_pairs_skipped"]
          if set(x["pair"]) == {"Shell", "Prop"}]
    check("F22.3.skip_visible", len(sk), 1)
    check("F22.3.unverified_reason",
          "unverified" in sk[0]["reason"] if sk else False, True)
    # F22.3b small ratio: nested dup inside a modest labeled shell still
    # flags (ratio 1.0/0.064 ~ 15.6 < 50)
    clear()
    box("MidShell", 1.0, (0, 0, 0.5))
    box("DupBox", 0.4, (0, 0, 0.4))
    SL.label_objects({"MidShell": "room_shell"})
    s = vs.validate_scene(ground_z=0.0)
    check("F22.3b.small_ratio_still_flags",
          len(issues_for(s, ["MidShell", "DupBox"])), 1)

    # ---------------- F22.4 gross escape ----------------
    clear()
    box("ChairA", 1.0, (0, 0, 0.5))
    box("TableB", 1.0, (0.02, 0, 0.5))  # depth .98, pct 98 -> GROSS
    SL.label_objects({"ChairA": "chair", "TableB": "table"})
    s = vs.validate_scene(ground_z=0.0)
    iss = issues_for(s, ["ChairA", "TableB"])
    check("F22.4.gross_flags", len(iss), 1)
    check("F22.4.gross_desc",
          "GROSS" in iss[0]["description"] if iss else False, True)
    check("F22.4.not_advisory",
          any(set(r["pair"]) == {"ChairA", "TableB"}
              for r in s["adjacency_worst"]), False)

    # ---------------- F22.5 param override ----------------
    clear()
    box("KitC", 0.5, (0, 0, 0.25))
    box("KitD", 0.5, (0.48, 0, 0.25))
    SL.label_objects({"KitC": "kitchen_unit", "KitD": "kitchen_unit"})
    s = vs.validate_scene(ground_z=0.0, level_families=set())
    check("F22.5.strict_override", len(issues_for(s, ["KitC", "KitD"])), 1)
    check("F22.5.no_advisory", s["adjacency_pairs_advisory"], 0)

    # --------------------------------------------------------------------
    print(f"\n[test_f22] {'ALL PASS' if not FAIL else 'FAILURES:'}")
    for f in FAIL:
        print(f"  [FAIL] {f}")
    if FAIL:
        sys.exit(1)


main()
