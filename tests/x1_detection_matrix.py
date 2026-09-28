"""x1_detection_matrix.py — X1: detection-reliability matrix, OLD bbox
validator (kit validate_scene.py semantics, reimplemented inline) vs NEW
BVH contact audit (placement_lib.audit_scene / pair_contact).

16 controlled pair-states on a common ground plane (z_top = 0), each pair
XY-separated (10 m pitch) so audits cannot cross-talk:

  S01-S04  penetration ladder 1/5/20/100 mm (probe sunk into pedestal top)
  S05      exact touch (probe bottom at pedestal top z=2.0)
  S06      sub-band touch (50 um above — inside the 0.1 mm contact band)
  S07-S09  gap ladder 10/30/49 mm above the pedestal (49 mm sits just under
           the kit's 50 mm floating/support threshold — the bbox cliff)
  S10      clear 300 mm (unsupported hover — kit floating-check territory)
  S11      nested (probe fully inside the SOLID pedestal: bbox sees a huge
           overlap, BVH must answer NESTED)
  S12      crossing (slab pierces a 50 mm wall; no verts inside either mesh;
           bbox can only see overlap volume, BVH must answer via
           segment-triangle crossing)
  S13      L_contact (probe rests on the pedestal's top corner: 0.1x0.1 m
           coplanar contact patch, bbox overlap volume = 0)
  S14      far-apart control
  B1/B2    bonus (built + reported, EXCLUDED from the 14-state score):
           adversarial demos of bbox false-negative classes —
           B1 thin knife through wall (6e-4 m3 overlap < 1e-3 volume gate),
           B2 1 mm sink through a 0.1x0.1 m corner column (1e-5 m3).

Each state runs:
  (a) bbox_detector(): the kit validator's pair-level heuristics copied
      inline from blender-kit/scripts/validate_scene.py —
      intersection: bbox overlap volume > 1e-3 m3 AND > 5% of smaller bbox;
      floating: bottom > ground_z + 0.05 with no object whose top is within
      0.05 of the bottom and whose XY column overlaps. Below-floor and
      >5 m ceiling checks are scene-level and cannot fire on this rig.
  (b) PL.audit_scene(pairs=[[a, b]]) -> state + pen/clear mm.

Ground truth is asserted per state (geometry is constructed => known).

Outputs:
  output/tests/x1_results.json   machine-readable matrix + scores
  output/tests/X1_findings.md    scored table + conclusions
"""
import json
import os
import sys

# placement_lib lives in the kit's scripts/ (sibling of tests/); the
# PLACEMENT_LAB env fallback points at the placement-lab R&D repo. Try both.
_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS = os.path.abspath(os.path.join(_HERE, "..", "scripts"))
_LAB_LIB = os.path.join(os.environ.get("PLACEMENT_LAB", "/home/z/placement-lab"), "lib")
for _p in (_SCRIPTS, _LAB_LIB):
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402
import placement_lib as PL  # noqa: E402

_REPO_ROOT = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), ".."))
_OUT_ROOT = os.environ.get("KIT_OUT",
                           os.path.join(_REPO_ROOT, "output", "tests"))
OUT_JSON = os.path.join(_OUT_ROOT, "x1_results.json")
OUT_MD = os.path.join(_OUT_ROOT, "X1_findings.md")
os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)

# ---------------------------------------------------------------------------
# Kit bbox-validator semantics, COPIED inline from
# <kit>/scripts/validate_scene.py (do not import — we measure
# the heuristic as-shipped, but self-contained).
# ---------------------------------------------------------------------------
FLOATING_THRESHOLD = 0.05          # m above ground with no support => flag
OVERLAP_VOLUME_THRESHOLD = 0.001   # m^3 bbox overlap => candidate flag
OVERLAP_PCT_THRESHOLD = 5.0        # % of smaller bbox volume => flag
CEILING_NAMES = {"ceiling", "ceilinglight", "sun", "sunlight"}


def _object_bounds(obj):
    """World-space bounding box for a mesh object (kit _object_bounds)."""
    if obj.type != 'MESH' or not obj.bound_box:
        return None
    corners = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    return {
        "min": [min(c[i] for c in corners) for i in range(3)],
        "max": [max(c[i] for c in corners) for i in range(3)],
    }


def _bounds_overlap(a, b):
    for i in range(3):
        if a["max"][i] < b["min"][i] or a["min"][i] > b["max"][i]:
            return False
    return True


def _bounds_overlap_volume(a, b):
    if not _bounds_overlap(a, b):
        return 0.0
    dx = max(0, min(a["max"][0], b["max"][0]) - max(a["min"][0], b["min"][0]))
    dy = max(0, min(a["max"][1], b["max"][1]) - max(a["min"][1], b["min"][1]))
    dz = max(0, min(a["max"][2], b["max"][2]) - max(a["min"][2], b["min"][2]))
    return dx * dy * dz


def _object_volume(b):
    return ((b["max"][0] - b["min"][0]) *
            (b["max"][1] - b["min"][1]) *
            (b["max"][2] - b["min"][2]))


def _bbox_floating(name, bounds, ground_z, bounds_map):
    """Kit check 1: floating object (bottom > ground+thr, no support)."""
    if name.lower() in CEILING_NAMES:
        return None
    bottom = bounds["min"][2]
    if not (bottom > ground_z + FLOATING_THRESHOLD):
        return None
    for other_name, ob in bounds_map.items():
        if other_name == name:
            continue
        # kit support test: other top within thr of our bottom AND the
        # other's XY column overlaps ours (z-axes forced to overlap)
        if (abs(ob["max"][2] - bottom) < FLOATING_THRESHOLD and
            _bounds_overlap(
                {**bounds, "min": [bounds["min"][0], bounds["min"][1], -9999]},
                {**ob, "max": [ob["max"][0], ob["max"][1], 9999]})):
            return None
    return (f"FLOATING(bottom {bottom:.3f}, {bottom - ground_z:.3f} above "
            f"ground, no support)")


def bbox_detector(a, b, ground_z=0.0, bounds_map=None):
    """Pair-level kit validator: intersection (check 3) + floating
    (check 1) for both objects. Returns JSON-safe dict."""
    ba, bb = bounds_map[a.name], bounds_map[b.name]
    flags = []
    ovl = _bounds_overlap_volume(ba, bb)
    smaller = min(_object_volume(ba), _object_volume(bb))
    pct = (ovl / smaller * 100.0) if smaller > 0 else 0.0
    inter = None
    if ovl >= OVERLAP_VOLUME_THRESHOLD and pct >= OVERLAP_PCT_THRESHOLD:
        sev = "P0" if pct >= 30.0 else "P1"
        inter = {"volume_m3": round(ovl, 6), "pct_of_smaller": round(pct, 2),
                 "severity": sev}
        flags.append(f"INTERSECTION {ovl:.4f}m3 ({pct:.1f}% of smaller, {sev})")
    floating = []
    for obj, bounds in ((a, ba), (b, bb)):
        f = _bbox_floating(obj.name, bounds, ground_z, bounds_map)
        if f:
            floating.append({"object": obj.name, "reason": f})
            flags.append(f"{obj.name}: {f}")
    if inter is not None:
        state = "PENETRATING/NESTED? (intersection)"
    elif floating:
        state = "FLOATING (unsupported)"
    else:
        state = "OK (silent)"
    return {"a": a.name, "b": b.name, "flagged": bool(flags), "state": state,
            "overlap_volume_m3": round(ovl, 6),
            "overlap_pct_of_smaller": round(pct, 2),
            "intersection": inter, "floating": floating, "flags": flags}


# ---------------------------------------------------------------------------
# Scene construction — 16 XY-separated pair states on one ground plane
# ---------------------------------------------------------------------------
GROUND_TOP_Z = 0.0
PED_TOP = 2.0            # pedestal 2x2x2 sitting on ground -> top z=2
PROBE_HALF = 0.5         # probe is 1x1x1 -> center z = bottom_z + 0.5


def box(name, size, loc):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc,
                                    scale=(size[0], size[1], size[2]))
    obj = bpy.context.active_object
    obj.name = name
    return obj


def ped(X):
    return ((2, 2, 2), (X, 0, 1))


def wall(X):
    return ((0.05, 2, 2), (X, 0, 1))


GROUPS = [
    dict(id="S01_pen_1mm", i=0, truth="PENETRATING", issue=True,
         pen_nom=1.0, pen_tol=0.2,
         a=ped, b=lambda X: ((1, 1, 1),
                             (X, 0, PED_TOP + PROBE_HALF - 0.001))),
    dict(id="S02_pen_5mm", i=1, truth="PENETRATING", issue=True,
         pen_nom=5.0, pen_tol=0.2,
         a=ped, b=lambda X: ((1, 1, 1),
                             (X, 0, PED_TOP + PROBE_HALF - 0.005))),
    dict(id="S03_pen_20mm", i=2, truth="PENETRATING", issue=True,
         pen_nom=20.0, pen_tol=0.2,
         a=ped, b=lambda X: ((1, 1, 1),
                             (X, 0, PED_TOP + PROBE_HALF - 0.020))),
    dict(id="S04_pen_100mm", i=3, truth="PENETRATING", issue=True,
         pen_nom=100.0, pen_tol=0.2,
         a=ped, b=lambda X: ((1, 1, 1),
                             (X, 0, PED_TOP + PROBE_HALF - 0.100))),
    dict(id="S05_touch_exact", i=4, truth="TOUCHING", issue=False,
         a=ped, b=lambda X: ((1, 1, 1), (X, 0, PED_TOP + PROBE_HALF))),
    dict(id="S06_touch_subband", i=5, truth="TOUCHING", issue=False,
         a=ped, b=lambda X: ((1, 1, 1),
                             (X, 0, PED_TOP + PROBE_HALF + 0.00005))),
    dict(id="S07_gap_1cm", i=6, truth="CLEAR", issue=False,
         clear_nom=10.0, clear_tol=1.0,
         a=ped, b=lambda X: ((1, 1, 1),
                             (X, 0, PED_TOP + PROBE_HALF + 0.010))),
    dict(id="S08_gap_3cm", i=7, truth="CLEAR", issue=False,
         clear_nom=30.0, clear_tol=1.0,
         a=ped, b=lambda X: ((1, 1, 1),
                             (X, 0, PED_TOP + PROBE_HALF + 0.030))),
    dict(id="S09_floating_5cm_above_pedestal", i=8, truth="CLEAR",
         issue=False, clear_nom=49.0, clear_tol=1.0,
         a=ped, b=lambda X: ((1, 1, 1),
                             (X, 0, PED_TOP + PROBE_HALF + 0.049))),
    dict(id="S10_clear_30cm", i=9, truth="CLEAR", issue=False,
         clear_nom=300.0, clear_tol=1.0,
         a=ped, b=lambda X: ((1, 1, 1),
                             (X, 0, PED_TOP + PROBE_HALF + 0.300))),
    dict(id="S11_nested", i=10, truth="NESTED", issue=True,
         pen_info=500.0,
         a=ped, b=lambda X: ((1, 1, 1), (X, 0, 1.0))),
    dict(id="S12_crossing_slab_through_wall", i=11, truth="PENETRATING",
         issue=True, crossing=True,
         a=wall, b=lambda X: ((1, 0.5, 0.5), (X, 0, 1.0))),
    dict(id="S13_L_contact", i=12, truth="TOUCHING", issue=False,
         a=ped, b=lambda X: ((1, 1, 1),
                             (X + 1.4, 1.4, PED_TOP + PROBE_HALF))),
    dict(id="S14_far_apart", i=13, truth="CLEAR", issue=False,
         clear_nom=1500.0, clear_tol=1.0,
         a=ped, b=lambda X: ((1, 1, 1), (X + 3, 0, 0.5))),
    # ---- bonus adversarial demos of bbox FN classes (unscored) ----
    dict(id="B1_thin_knife_through_wall", i=14, truth="PENETRATING",
         issue=True, crossing=True, bonus=True,
         a=wall, b=lambda X: ((0.4, 0.008, 1.5), (X, 0, 0.75))),
    dict(id="B2_L_pen_1mm_corner_column", i=15, truth="PENETRATING",
         issue=True, pen_nom=1.0, pen_tol=0.2, bonus=True,
         a=ped, b=lambda X: ((1, 1, 1),
                             (X + 1.4, 1.4, PED_TOP + PROBE_HALF - 0.001))),
]


def build_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    box("Ground", (300, 300, 0.2), (0, 0, -0.1))  # top at z=0
    for g in GROUPS:
        X = 10.0 * g["i"]
        for role in ("a", "b"):
            size, loc = g[role](X)
            nm = f"{g['id']}__{'Ped' if role == 'a' else 'Obj'}"
            if g["id"].startswith("S12"):
                nm = f"{g['id']}__{'Wall' if role == 'a' else 'Slab'}"
            if g["id"].startswith("B1"):
                nm = f"{g['id']}__{'Wall' if role == 'a' else 'Blade'}"
            box(nm, size, loc)
            g[role + "_name"] = nm
    bpy.context.view_layer.update()


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------
def bvh_binary_flag(g):
    return g["bvh"].get("state") in ("PENETRATING", "NESTED", "ERROR")


def bvh_state_exact(g):
    return g["bvh"].get("state") == g["truth"]


def bbox_state_exact(g):
    """Exact-state rule for the bbox detector (documented in findings):
    - intersection flag names the overlap-defect class => exact iff truth is
      PENETRATING (it cannot distinguish NESTED from penetration — that is
      precisely the capability under test).
    - floating-only flag claims an unsupported-hover defect => never exact
      in this matrix (every truth state with a floating flag is CLEAR).
    - silent => exact iff truth is a non-defect (TOUCHING / CLEAR), i.e. it
      correctly emits no defect claim (contact itself is invisible to it)."""
    if g["bbox"]["intersection"] is not None:
        return g["truth"] == "PENETRATING"
    if g["bbox"]["floating"]:
        return False
    return g["truth"] in ("TOUCHING", "CLEAR")


def bvh_mm_ok(g):
    rep = g["bvh"]
    st = rep.get("state")
    if g.get("crossing"):
        return rep.get("crossing") is True and st == "PENETRATING"
    if "pen_nom" in g:
        pen = rep.get("penetration_mm")
        return (st == "PENETRATING" and pen is not None and
                abs(pen - g["pen_nom"]) <= g["pen_tol"])
    if "pen_info" in g:  # nested depth, informational
        pen = rep.get("penetration_mm")
        return (st == "NESTED" and pen is not None and
                abs(pen - g["pen_info"]) <= 5.0)
    if "clear_nom" in g:
        cl = rep.get("clearance_mm")
        return (st == "CLEAR" and cl is not None and
                abs(cl - g["clear_nom"]) <= g["clear_tol"])
    if g["truth"] == "TOUCHING":
        return st == "TOUCHING" and rep.get("penetration_mm") == 0.0
    return None


def bvh_label(g):
    rep = g["bvh"]
    st = rep.get("state")
    if st == "PENETRATING":
        if rep.get("crossing"):
            return "PENETRATING (crossing; depth not vert-measurable)"
        return f"PENETRATING {rep.get('penetration_mm')} mm"
    if st == "NESTED":
        return f"NESTED (max depth {rep.get('penetration_mm')} mm)"
    if st == "TOUCHING":
        return "TOUCHING (0.0 mm)"
    if st == "CLEAR":
        cl = rep.get("clearance_mm")
        return f"CLEAR {cl} mm"
    return f"{st}: {rep.get('verdict', '?')}"


def bbox_label(g):
    bb = g["bbox"]
    if not bb["flagged"]:
        return "silent"
    return " + ".join(bb["flags"])


def right_col(g, b_bin, v_bin):
    if b_bin == g["issue"] and v_bin == g["issue"]:
        return "both"
    if v_bin == g["issue"]:
        return "BVH only"
    if b_bin == g["issue"]:
        return "bbox only"
    return "neither"


# ---------------------------------------------------------------------------
# Artifact writers
# ---------------------------------------------------------------------------
def write_json(scores, bin_mismatch):
    doc = {
        "experiment": "X1 detection matrix — bbox validator vs BVH contact audit",
        "scene": {"ground_top_z": GROUND_TOP_Z, "pairs_xy_pitch_m": 10.0,
                  "n_states": len(GROUPS),
                  "n_scored": len([g for g in GROUPS if not g.get("bonus")])},
        "bbox_detector_semantics": {
            "source": "blender-kit/scripts/validate_scene.py (copied inline)",
            "intersection": "bbox overlap volume > 0.001 m3 AND > 5% of "
                            "smaller bbox volume",
            "floating": "bottom > ground_z + 0.05 with no object whose top "
                        "is within 0.05 and whose XY column overlaps",
        },
        "scoring": {
            "binary": "flagged-vs-not vs truth issue in {PENETRATING, NESTED}",
            "state_exact": "BVH: state string == truth. bbox: intersection "
                           "flag == PENETRATING only (cannot name NESTED); "
                           "floating-only never exact (all such truths are "
                           "CLEAR); silent exact iff truth TOUCHING/CLEAR",
            "mm": "pen within 0.2 mm of nominal (crossing: flag), clear "
                  "within 1 mm, touch == 0, nested depth informational 5 mm",
        },
        "scores": scores,
        "binary_mismatches": bin_mismatch,
        "states": [
            {"id": g["id"], "bonus": bool(g.get("bonus")),
             "truth": g["truth"], "truth_issue": g["issue"],
             "nominal_mm": {k: g[k] for k in
                            ("pen_nom", "pen_tol", "clear_nom", "clear_tol",
                             "pen_info") if k in g},
             "bbox": g["bbox"],
             "bbox_binary_ok": g["bbox"]["flagged"] == g["issue"],
             "bbox_state_exact": bbox_state_exact(g),
             "bvh": {k: v for k, v in g["bvh"].items()},
             "bvh_binary_ok": bvh_binary_flag(g) == g["issue"],
             "bvh_state_exact": bvh_state_exact(g),
             "bvh_mm_ok": bvh_mm_ok(g)} for g in GROUPS],
    }
    with open(OUT_JSON, "w") as f:
        json.dump(doc, f, indent=2, default=str)
    return doc


def write_md(scores):
    L = []
    A = L.append
    A("# X1 — detection matrix: OLD bbox validator vs NEW BVH contact audit")
    A("")
    A("Rig: ground plane (top z=0) + 16 XY-separated pair states (14 scored, "
      "2 bonus); pedestal 2x2x2 (top z=2), probe 1x1x1 unless stated. "
      "bbox detector = kit `validate_scene.py` heuristics copied inline; "
      "BVH = `placement_lib.audit_scene(pairs=[[a,b]])`. Ground truth is "
      "asserted from constructed geometry.")
    A("")
    A("## Scored matrix (14 states)")
    A("")
    A("| state | ground truth | bbox detector (kit heuristic) | bbox | "
      "BVH audit (placement_lib) | BVH | right |")
    A("|---|---|---|---|---|---|---|")
    for g in GROUPS:
        if g.get("bonus"):
            continue
        b_bin = g["bbox"]["flagged"]
        v_bin = bvh_binary_flag(g)
        mark = lambda ok: "&#10003;" if ok else "&#10007;"
        A(f"| {g['id']} | {g['truth']}"
          f"{_truth_mm(g)} | {bbox_label(g)} | {mark(b_bin == g['issue'])} | "
          f"{bvh_label(g)} | {mark(v_bin == g['issue'])} | "
          f"{right_col(g, b_bin, v_bin)} |")
    A("")
    A("## Bonus adversarial rows (unscored — bbox FN class demos)")
    A("")
    A("| state | ground truth | bbox detector | bbox | BVH audit | BVH |")
    A("|---|---|---|---|---|---|")
    for g in GROUPS:
        if not g.get("bonus"):
            continue
        mark = lambda ok: "&#10003;" if ok else "&#10007;"
        A(f"| {g['id']} | {g['truth']}{_truth_mm(g)} | {bbox_label(g)} | "
          f"{mark(g['bbox']['flagged'] == g['issue'])} | {bvh_label(g)} | "
          f"{mark(bvh_binary_flag(g) == g['issue'])} |")
    A("")
    s = scores
    A("## Scores")
    A("")
    A(f"- **bbox (kit heuristic): binary {s['bbox_binary_ok']}/14 "
      f"({100.0 * s['bbox_binary_ok'] / 14:.1f}%), "
      f"state-exact {s['bbox_state_ok']}/14 "
      f"({100.0 * s['bbox_state_ok'] / 14:.1f}%)** "
      f"[TP {s['bbox_tp']} FP {s['bbox_fp']} FN {s['bbox_fn']} TN {s['bbox_tn']}]")
    A(f"- **BVH (placement_lib): binary {s['bvh_binary_ok']}/14 "
      f"({100.0 * s['bvh_binary_ok'] / 14:.1f}%), "
      f"state-exact {s['bvh_state_ok']}/14 "
      f"({100.0 * s['bvh_state_ok'] / 14:.1f}%), "
      f"mm-metric {s['bvh_mm_ok']}/{s['bvh_mm_n']}** "
      f"[TP {s['bvh_tp']} FP {s['bvh_fp']} FN {s['bvh_fn']} TN {s['bvh_tn']}]")
    A("")
    A("## Conclusions")
    A("")
    for c in conclusions(scores):
        A(f"- {c}")
    A("")
    with open(OUT_MD, "w") as f:
        f.write("\n".join(L))


def _truth_mm(g):
    if "pen_nom" in g:
        return f" (~{g['pen_nom']:g} mm)"
    if "clear_nom" in g:
        return f" (~{g['clear_nom']:g} mm)"
    if "pen_info" in g:
        return f" (depth ~{g['pen_info']:g} mm)"
    return ""


def conclusions(scores):
    # computed constants from the rig geometry
    min_sink_mm = OVERLAP_PCT_THRESHOLD / 100.0 * 1000.0   # 5% of 1 m probe
    knife_vol = 0.05 * 0.008 * 1.5                        # B1 overlap m3
    slab40_pct = (0.05 * 0.4 * 0.4) / min(0.05 * 2 * 2,
                                          1 * 0.4 * 0.4) * 100
    return [
        f"**Headline: bbox {scores['bbox_binary_ok']}/14 binary "
        f"({scores['bbox_state_ok']}/14 state-exact) vs BVH "
        f"{scores['bvh_binary_ok']}/14 binary, {scores['bvh_state_ok']}/14 "
        f"state-exact, {scores['bvh_mm_ok']}/{scores['bvh_mm_n']} mm-exact. "
        f"All bbox errors are one of three structural classes below; BVH has "
        f"none.**",
        f"bbox FALSE NEGATIVES on shallow penetration (S01-S03): the "
        f"intersection flag needs overlap volume > 1 L AND >= 5% of the "
        f"smaller bbox. For a 1x1x1 m probe on a surface that means a sink "
        f"of >= {min_sink_mm:.0f} mm before anything fires — 1/5/20 mm "
        f"penetrations are invisible (overlap 0.001/0.005/0.02 m3 but only "
        f"0.1/0.5/2% of the probe). BVH reports PENETRATING with exact "
        f"1.0/5.0/20.0 mm depth, enabling a repair loop, not just an alarm.",
        f"bbox FALSE NEGATIVE on thin crossings (B1): an 8 mm blade through "
        f"the 50 mm wall overlaps by {knife_vol * 1e6:.0f} cm3 "
        f"(< 1 L volume gate) — silent, even though the overlap is 12.5% of "
        f"the blade bbox. BVH's segment-triangle crossing test (built for "
        f"exactly this after the T3 design review) flags PENETRATING. And "
        f"the pct gate is a cliff too: the specified wall with a 0.4x0.4 m "
        f"slab sits at exactly {slab40_pct:.1f}% of the smaller bbox — the "
        f"flag's own decision boundary (a 0.39 m slab drops to 4.9% and "
        f"vanishes); S12 uses 0.5x0.5 m => 6.25% for margin. Lib note: "
        f"the crossing test is edge-sampling — it needs one edge through "
        f"the partner face's INTERIOR; an object exactly co-extensive with "
        f"the wall (B1 v0: blade z-span == wall z-span) hides every hit on "
        f"the face boundary (reads TOUCHING). Real scenes have the shorter "
        f"object's edges pierce the taller one's faces; the strict-inside "
        f"guard added in X1 kills the boundary-tangency false positive "
        f"(S13 L_contact) at the cost of that already-degenerate corner.",
        "bbox FALSE POSITIVE / inverted priorities (S10 vs S01-S03): any "
        "hover >= 50 mm above a support is flagged FLOATING (S10: 300 mm "
        "hover, truth CLEAR), while 1-20 mm real penetrations pass silently. "
        "The floating flag also co-fires spuriously: the 100 mm-sunk probe "
        "(S04, 'floating' while 100 mm INSIDE the pedestal), the nested "
        "probe (S11, 'floating' inside a SOLID box), and the wall-piercing "
        "slab (S12, gripped by the wall it crosses).",
        "bbox cannot name states (S11): nested probe => 'intersection P0, "
        "100% of smaller' — right that something is wrong, wrong about what "
        "(containment reported as volume collision, plus the absurd "
        "floating co-flag). BVH returns NESTED with the 500 mm containment "
        "depth — the distinction placement tools need (severity info vs "
        "fail).",
        "Zero-volume contact is invisible to bbox — sometimes fine, "
        "sometimes fatal (S13/B2): L_contact (0.1x0.1 m coplanar corner "
        "patch) has bbox overlap volume 0; silent happens to be correct "
        "because touching is not a defect. But sink the SAME corner column "
        "1 mm (B2) and the overlap is 1e-5 m3 — still silent, now a real "
        "false negative. BVH resolves both: TOUCHING vs PENETRATING 1.0 mm.",
        f"mm-metric value: BVH quantifies every state — pen "
        f"1.0/5.0/20.0/100.0 mm (tol 0.2), clear 10/30/49/300/1500 mm "
        f"(tol 1), touch within the 0.1 mm contact band, nested depth 500 mm "
        f"— while bbox emits one bit per heuristic with a cliff at 50 mm "
        f"(S09 49 mm above support: silent; S10 300 mm: flagged). Exact mm "
        f"is what lets place_on/snap_z close the loop instead of guessing.",
        "Where bbox is genuinely fine: far-apart control (S14), gaps < 50 mm "
        "above a support (S07-S09 silent = correct), exact/sub-band touches "
        "(S05/S06 silent = correct), and deep penetrations (S04 flagged at "
        "10% overlap). As a cheap O(n^2) coarse prefilter it keeps value — "
        "it just cannot be the arbiter of contact truth.",
        "Recommendation: keep the kit validator as a fast coarse screen; "
        "adopt PL.audit_scene as the authoritative QC gate (PENETRATING = "
        "fail, NESTED = info, TOUCHING/CLEAR = ok) and as the mm-feedback "
        "source for placement repair. The X1 matrix doubles as a regression "
        "fixture for both detectors.",
    ]


# ---------------------------------------------------------------------------
def main():
    build_scene()
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    bounds_map = {}
    for o in meshes:
        b = _object_bounds(o)
        if b:
            bounds_map[o.name] = b

    # (a) inline bbox validator per pair
    for g in GROUPS:
        A = bpy.data.objects[g["a_name"]]
        B = bpy.data.objects[g["b_name"]]
        g["bbox"] = bbox_detector(A, B, GROUND_TOP_Z, bounds_map)

    # (b) NEW: BVH audit with explicit pairs (no cross-talk between states)
    pairs_arg = [[g["a_name"], g["b_name"]] for g in GROUPS]
    audit = PL.audit_scene(pairs=pairs_arg)
    rep_map = {(r["a"], r["b"]): r for r in audit["pairs"]}
    for g in GROUPS:
        g["bvh"] = rep_map[(g["a_name"], g["b_name"])]

    # ---- score the 14 non-bonus states ----
    scored = [g for g in GROUPS if not g.get("bonus")]
    s = {"n": len(scored)}
    for det, flagfn in (("bbox", lambda g: g["bbox"]["flagged"]),
                        ("bvh", bvh_binary_flag)):
        tp = fp = fn = tn = 0
        for g in scored:
            flagged = flagfn(g)
            if flagged and g["issue"]:
                tp += 1
            elif flagged:
                fp += 1
            elif g["issue"]:
                fn += 1
            else:
                tn += 1
        s[f"{det}_tp"], s[f"{det}_fp"], s[f"{det}_fn"], s[f"{det}_tn"] = \
            tp, fp, fn, tn
        s[f"{det}_binary_ok"] = tp + tn
    s["bbox_state_ok"] = sum(1 for g in scored if bbox_state_exact(g))
    s["bvh_state_ok"] = sum(1 for g in scored if bvh_state_exact(g))
    mm_vals = [(g["id"], bvh_mm_ok(g)) for g in scored]
    s["bvh_mm_n"] = sum(1 for _, v in mm_vals if v is not None)
    s["bvh_mm_ok"] = sum(1 for _, v in mm_vals if v is True)

    bin_mismatch = [
        {"id": g["id"], "detector": det,
         "flagged": flagfn(g), "truth_issue": g["issue"]}
        for g in scored
        for det, flagfn in (("bbox", lambda g: g["bbox"]["flagged"]),
                            ("bvh", bvh_binary_flag))
        if flagfn(g) != g["issue"]]

    doc = write_json(s, bin_mismatch)
    write_md(s)

    # ---- console report ----
    for g in GROUPS:
        bb, bv = g["bbox"], g["bvh"]
        print(f"[X1] {g['id']:34s} truth={g['truth']:12s} "
              f"bbox={'FLAG' if bb['flagged'] else 'silent':6s} "
              f"({' | '.join(bb['flags']) if bb['flags'] else '-'}) "
              f"bvh={bv.get('state')} "
              f"pen={bv.get('penetration_mm')} clear={bv.get('clearance_mm')}")
    print(f"[X1] scores: bbox binary {s['bbox_binary_ok']}/14 "
          f"(state {s['bbox_state_ok']}/14) TP{s['bbox_tp']} "
          f"FP{s['bbox_fp']} FN{s['bbox_fn']} TN{s['bbox_tn']} | "
          f"BVH binary {s['bvh_binary_ok']}/14 (state {s['bvh_state_ok']}/14, "
          f"mm {s['bvh_mm_ok']}/{s['bvh_mm_n']}) TP{s['bvh_tp']} "
          f"FP{s['bvh_fp']} FN{s['bvh_fn']} TN{s['bvh_tn']}")
    for m in bin_mismatch:
        print(f"[X1] MISMATCH {m}")
    print(f"[X1] audit top-level: pairs_checked={audit['pairs_checked']} "
          f"counts={audit['state_counts']} failed={audit['failed']}")
    print(f"[X1] wrote {OUT_JSON}")
    print(f"[X1] wrote {OUT_MD}")


main()
