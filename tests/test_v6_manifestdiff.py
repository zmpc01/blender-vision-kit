"""
test_v6_manifestdiff.py — regression suite for manifest_diff (D16 handoff
audit G3: delegated work is verified by DIFF, not by trust).

Pure Python (no bpy) — runs with the system interpreter:
    python3 tests/test_v6_manifestdiff.py
(also harmless under blrun.sh; blender's python has json/math too)

Covers:
  M1  no-change manifests -> only 'unchanged', zero findings
  M2  moved row (bbox center shift > tol) -> 'moved' with delta+magnitude
  M3  sub-tolerance jitter (rounding noise) -> NOT moved
  M4  added / removed ids -> reported; renamed pair detected as
      geometric twin (same extent+center, different id) and NOT
      double-counted as added+removed
  M5  resized row -> 'resized'
  M6  label_changed -> reported with before/after
  M7  rotation-corrected bbox: a row whose world_bbox changed because
      the object was ROTATED (extent changed) is 'resized'+'moved' —
      the world_bbox law makes rotation visible to the diff
  M8  non-mesh row (LIGHT energy) change -> 'nonmesh_changed'
  M9  legacy manifests without world_bbox fall back to centroid
  M10 summarize() line count == findings count
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))) + "/scripts")
from manifest_diff import diff_manifests, summarize  # noqa: E402

FAILS = []


def check(name, got, want):
    ok = got == want
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: got {got!r}"
          f"{'' if ok else f', expected {want!r}'}")
    if not ok:
        FAILS.append(name)


def row(oid, bbox_min, bbox_max, label=None, typ="MESH"):
    r = {"id": oid, "type": typ,
         "world_bbox": {"min": bbox_min, "max": bbox_max},
         "dims_m": [b - a for a, b in zip(bbox_min, bbox_max)]}
    if typ == "MESH":
        r["kit_label"] = label
    return r


def main():
    # M1: no change
    A = [row("table", [0, 0, 0], [1, 1, 1], "table"),
         row("ball", [2, 0, 0], [2.5, 0.5, 0.5], "ball")]
    rep = diff_manifests(A, json.loads(json.dumps(A)))
    check("M1.zero_findings",
          (len(rep["moved"]) + len(rep["resized"]) + len(rep["added"])
           + len(rep["removed"]) + len(rep["renamed"])
           + len(rep["label_changed"])), 0)
    check("M1.unchanged", sorted(rep["unchanged"]), ["ball", "table"])

    # M2: moved
    B = json.loads(json.dumps(A))
    B[1]["world_bbox"] = {"min": [2, 0, 0.5], "max": [2.5, 0.5, 1.0]}
    rep = diff_manifests(A, B)
    check("M2.moved", [r["id"] for r in rep["moved"]], ["ball"])
    check("M2.delta", rep["moved"][0]["delta"], [0.0, 0.0, 0.5])
    check("M2.magnitude", rep["moved"][0]["magnitude_m"], 0.5)

    # M3: sub-tolerance jitter is NOT movement
    C = json.loads(json.dumps(A))
    C[0]["world_bbox"]["min"][0] += 0.002  # < default tol 0.005
    rep = diff_manifests(A, C)
    check("M3.jitter_ignored", rep["moved"], [])

    # M4: rename -> geometric twin, not added+removed
    D = json.loads(json.dumps(A))
    D[0]["id"] = "table_top"
    rep = diff_manifests(A, D)
    check("M4.renamed", rep["renamed"], [{"before": "table",
                                          "after": "table_top"}])
    check("M4.no_false_added", rep["really_added"], [])
    check("M4.no_false_removed", rep["removed"], [])

    # M5: resized
    E = json.loads(json.dumps(A))
    E[0]["world_bbox"] = {"min": [0, 0, 0], "max": [2, 1, 1]}
    rep = diff_manifests(A, E)
    check("M5.resized", [r["id"] for r in rep["resized"]], ["table"])

    # M6: label change
    F = json.loads(json.dumps(A))
    F[1]["kit_label"] = "sphere"
    rep = diff_manifests(A, F)
    check("M6.label_changed", rep["label_changed"],
          [{"id": "ball", "before": "ball", "after": "sphere"}])

    # M7: rotation changes world_bbox -> visible as resized; rotating
    # about the box's own center keeps the CENTER (resize only), while
    # a yaw about a distant origin moves it too (resize+moved)
    G = json.loads(json.dumps(A))
    G[0]["world_bbox"] = {"min": [-0.207, -0.207, 0],
                          "max": [1.207, 1.207, 1]}  # 45° yaw, own center
    rep = diff_manifests(A, G)
    check("M7.rot_resize", [r["id"] for r in rep["resized"]], ["table"])
    check("M7.rot_center_kept", rep["moved"], [])
    G.append(row("off", [0.707, 1.414, 0], [2.121, 2.828, 1], "off"))
    A2 = json.loads(json.dumps(A))
    A2.append(row("off", [2, 0, 0], [3, 1, 1], "off"))
    rep = diff_manifests(A2, G)
    check("M7.rot_center_moved",
          [r["id"] for r in rep["moved"]], ["off"])

    # M8: non-mesh change (LIGHT)
    H = [{"id": "Sun", "type": "LIGHT", "light": "SUN",
          "energy_W": 3.0}]
    H2 = [{"id": "Sun", "type": "LIGHT", "light": "SUN",
           "energy_W": 9.5}]
    rep = diff_manifests(H, H2)
    check("M8.nonmesh", [r["id"] for r in rep["nonmesh_changed"]],
          ["Sun"])

    # M9: legacy manifests (centroid only) still diff
    L1 = [{"id": "x", "type": "MESH", "dims_m": [1, 1, 1],
           "centroid": [0, 0, 0], "kit_label": None}]
    L2 = [{"id": "x", "type": "MESH", "dims_m": [1, 1, 1],
           "centroid": [0, 0, 2], "kit_label": None}]
    rep = diff_manifests(L1, L2)
    check("M9.legacy_move", [r["id"] for r in rep["moved"]], ["x"])

    # M10: summarize findings == count
    rep = diff_manifests(A, B)
    lines, n = summarize(rep)
    check("M10.count_matches",
          n, len(rep["moved"]) + len(rep["resized"])
          + len(rep["renamed"]) + len(rep["label_changed"])
          + len(rep["really_added"]) + len(rep["removed"])
          + len(rep["nonmesh_changed"]))
    check("M10.has_total", any("1 finding" in ln for ln in lines), True)

    print()
    if FAILS:
        print(f"[test_v6] FAILURES ({len(FAILS)}): {FAILS}")
        return 1
    print("[test_v6] ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
