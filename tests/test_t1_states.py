"""test_t1_states.py — T1 regression: R2's 7 ground-truth states through
placement_lib.pair_contact. Runs INSIDE Blender via run.sh."""
import sys, os, json
# placement_lib lives in the kit's scripts/ (sibling of tests/); the
# PLACEMENT_LAB env fallback points at the placement-lab R&D repo. Try both.
_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS = os.path.abspath(os.path.join(_HERE, "..", "scripts"))
_LAB_LIB = os.path.join(os.environ.get("PLACEMENT_LAB", "/home/z/placement-lab"), "lib")
for _p in (_SCRIPTS, _LAB_LIB):
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)
import bpy
from mathutils import Vector
import placement_lib as PL

_REPO_ROOT = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), ".."))
_OUT_ROOT = os.environ.get("KIT_OUT",
                           os.path.join(_REPO_ROOT, "output", "tests"))
OUT = os.path.join(_OUT_ROOT, "t1_results.json")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
FAIL = []


def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def box(name, size, loc):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc,
                                    scale=(size[0], size[1], size[2]))
    obj = bpy.context.active_object
    obj.name = name
    return obj


def check(label, got, expect, tol=None):
    ok = (abs(got - expect) <= tol) if tol is not None else (got == expect)
    if not ok:
        FAIL.append(f"{label}: got {got!r}, expected {expect!r}")
    return ok


def run_state(name, bloc, expect_state, pen_mm=None, clear_mm=None):
    clear()
    A = box("A", (2, 2, 2), (0, 0, 1))
    B = box("B", (1, 1, 1), bloc)
    bpy.context.view_layer.update()
    r = PL.pair_contact(A, B)
    checks = [
        check(f"{name}.state", r["state"], expect_state),
    ]
    if pen_mm is not None:
        checks.append(check(f"{name}.pen_mm", r.get("penetration_mm"),
                            pen_mm, tol=0.05))
    if clear_mm is not None:
        checks.append(check(f"{name}.clear_mm", r.get("clearance_mm"),
                            clear_mm, tol=1.0))
    print(f"[T1] {name}: {r['state']} pen={r.get('penetration_mm')} "
          f"clear={r.get('clearance_mm')} verdict='{r.get('verdict')}' "
          f"({'PASS' if all(checks) else 'FAIL'})")
    return r


def main():
    results = {}
    results["S1_separated"] = run_state("S1_separated", (0, 0, 2.55),
                                        "CLEAR", clear_mm=50.0)
    results["S2_touch"] = run_state("S2_touch", (0, 0, 2.5), "TOUCHING")
    results["S3_pen5mm"] = run_state("S3_pen5mm", (0, 0, 2.495),
                                     "PENETRATING", pen_mm=5.0)
    results["S4_pen50mm"] = run_state("S4_pen50mm", (0, 0, 2.45),
                                      "PENETRATING", pen_mm=50.0)
    results["S5_nested"] = run_state("S5_nested", (0, 0, 1.0), "NESTED",
                                     pen_mm=500.0)
    results["S6_sidegap"] = run_state("S6_sidegap", (2.03, 0, 0.5),
                                      "CLEAR", clear_mm=530.0)
    results["S7_floating"] = run_state("S7_floating", (4, 4, 3), "CLEAR",
                                       clear_mm=3570.71)

    # S8: spear-through (review blocker #2 regression): thin wall + slab
    # crossing it — no verts inside either object
    clear()
    wall = box("Wall", (0.1, 2, 2), (0, 0, 1))       # thin wall, x in [-.05,.05]
    slab = box("Slab", (1, 0.4, 0.4), (0, 0, 1))     # crosses wall
    bpy.context.view_layer.update()
    r = PL.pair_contact(wall, slab)
    results["S8_crossing"] = r
    check("S8_crossing.state", r["state"], "PENETRATING")
    print(f"[T1] S8_crossing: {r['state']} crossing={r.get('crossing')} "
          f"verdict='{r.get('verdict')}' "
          f"({'PASS' if r['state'] == 'PENETRATING' else 'FAIL'})")

    # S9: touching-in-cross config (coplanar faces, no crossing, no inside)
    clear()
    A = box("A", (2, 2, 2), (0, 0, 1))
    B = box("B", (1, 1, 1), (0, 0, 2.5))
    bpy.context.view_layer.update()
    r = PL.pair_contact(A, B)
    check("S9_touch_again", r["state"], "TOUCHING")

    # S10: far-tangent corner vs cylinder ring edge (u7 fixture lesson,
    # session 11): box corner level with a cylinder's bottom ring, 0.83m
    # away. find_nearest returns the ring-edge point with the bottom-cap
    # normal (perpendicular to the approach) -> true dotp = 0; float32
    # noise (~1e-6) must NOT tip it to 'inside' (EPS_TANGENT fix).
    # Regression of the fake 'PENETRATING 833 mm' bug.
    clear()
    shelf = box("Shelf", (1.2, 0.4, 0.03), (0, 0, 0.985))   # top z = 1.0
    bpy.ops.mesh.primitive_cylinder_add(radius=0.04, depth=0.095,
                                        location=(-0.25, 0, 1.0475))
    mug = bpy.context.active_object
    mug.name = "Mug"
    bpy.context.view_layer.update()
    r = PL.pair_contact(shelf, mug)
    results["S10_far_tangent"] = r
    check("S10_far_tangent.state", r["state"], "TOUCHING")
    print(f"[T1] S10_far_tangent: {r['state']} pen={r.get('penetration_mm')} "
          f"clear={r.get('clearance_mm')} "
          f"({'PASS' if r['state'] == 'TOUCHING' else 'FAIL'})")

    # audit_scene end-to-end on the S4 state (2 meshes only)
    clear()
    A = box("A", (2, 2, 2), (0, 0, 1))
    B = box("B", (1, 1, 1), (0, 0, 2.45))
    C = box("C", (1, 1, 1), (5, 5, 0.5))
    bpy.context.view_layer.update()
    audit = PL.audit_scene()
    results["audit"] = audit
    check("audit.failed", audit["failed"], True)
    check("audit.counts", audit["state_counts"].get("PENETRATING", 0), 1)
    print(f"[T1] audit_scene: pairs={audit['pairs_checked']} "
          f"counts={audit['state_counts']} failed={audit['failed']} "
          f"({'PASS' if audit['failed'] and audit['state_counts'].get('PENETRATING')==1 else 'FAIL'})")

    verdict = "FAIL:\n" + "\n".join(FAIL) if FAIL else "ALL PASS"
    with open(OUT, "w") as f:
        json.dump({"fail": FAIL, "states": {k: v for k, v in results.items()}},
                  f, indent=2, default=str)
    print(f"[T1] {verdict}")
    print(f"[T1] wrote {OUT}")


main()
