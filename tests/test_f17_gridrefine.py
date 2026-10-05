"""
test_f17_gridrefine.py — F17 regression: place_on footprint grid
refinement for narrow inset supports.

The D16 dogfood measured the failure: assembling a table — placing the
2.4x1.4 top ONTO its four 0.08m legs — every 12x12 cell center (0.2m
spacing) missed the leg spans [0.11,0.19]/[0.81,0.89] by 0.01m; the
blind agent had to fall back to snap_z. The fix refines the grid x4
until rays hit (cap 192x192).

Covers:
  F1  top onto 4 narrow legs, grid footprint: rests at leg-top height
      + report records the refinement (the exact dogfood repro)
  F2  wide support needs no refine (default density unchanged)
  F3  genuinely empty support still raises after refinement
  F4  refinement past one step: 1cm pin support found at 48x48

Run: ./scripts/blrun.sh --background --python tests/test_f17_gridrefine.py
"""
import sys, os

_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS = os.path.abspath(os.path.join(_HERE, "..", "scripts"))
for _p in (_SCRIPTS,):
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

import bpy
from blender_kit import clear_scene
import placement_lib as PL

FAILS = []


def check(name, got, want):
    ok = got == want
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: got {got!r}"
          f"{'' if ok else f', expected {want!r}'}")
    if not ok:
        FAILS.append(name)


def raises(fn):
    try:
        fn()
        return False
    except RuntimeError:
        return True


def zmin(o):
    return min((o.matrix_world @ type(o.location)(c)).z
               for c in o.bound_box)


def make_legs(leg=0.08, height=0.75, inset_x=0.30, inset_y=0.25,
              top_xy=(2.4, 1.4)):
    """4 narrow legs standing on the ground (no top yet)."""
    legs = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            lx = sx * (top_xy[0] / 2 - inset_x)
            ly = sy * (top_xy[1] / 2 - inset_y)
            bpy.ops.mesh.primitive_cube_add(
                size=1, location=(lx, ly, height / 2))
            lg = bpy.context.active_object
            lg.scale = (leg, leg, height)
            bpy.ops.object.transform_apply(scale=True)
            lg.name = f"Leg{sx}{sy}"
            legs.append(lg)
    return legs


def main():
    clear_scene()

    # ---------------- F1: top onto narrow legs (dogfood repro) ----------
    legs = make_legs()
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 1.4))
    top = bpy.context.active_object
    top.name = "TableTop"
    top.scale = (2.4, 1.4, 0.05)
    bpy.ops.object.transform_apply(scale=True)
    rep = PL.place_on(top, *legs, footprint='grid', keep_xy=True)
    check("F1.rests_on_legs", round(zmin(top) - 0.75, 4) <= 0.001, True)
    check("F1.support_found", rep["support_found"],
          sorted(l.name for l in legs))
    check("F1.refined_reported", "footprint_grid_refined" in rep, True)

    # ---------------- F2: wide support, no refine needed ----------------
    clear_scene()
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0.5))
    slab = bpy.context.active_object
    slab.name = "Slab"
    slab.scale = (1.5, 1.5, 0.5)
    bpy.ops.object.transform_apply(scale=True)
    bpy.ops.mesh.primitive_cube_add(size=0.6, location=(0, 0, 1.3))
    crate2 = bpy.context.active_object
    crate2.name = "Crate2"
    rep2 = PL.place_on(crate2, slab, footprint='grid', keep_xy=True)
    check("F2.no_refine", "footprint_grid_refined" not in rep2, True)
    check("F2.rests", round(zmin(crate2) - 1.0, 4) <= 0.001, True)

    # ---------------- F3: empty support still raises --------------------
    clear_scene()
    bpy.ops.mesh.primitive_cube_add(size=1, location=(6, 6, 0.25))
    far_slab = bpy.context.active_object
    far_slab.name = "FarSlab"
    far_slab.scale = (0.5, 0.5, 0.5)
    bpy.ops.object.transform_apply(scale=True)
    bpy.ops.mesh.primitive_cube_add(size=0.6, location=(0, 0, 1.4))
    floater = bpy.context.active_object
    floater.name = "Floater"
    check("F3.empty_support_raises",
          raises(lambda: PL.place_on(floater, far_slab,
                                     footprint='grid')),
          True)

    # ---------------- F4: refinement past one step (1cm pin) ------------
    # pin deliberately OFF every 12x12 column center of the saucer bbox
    # (columns at x 0.0/0.0333, y 0.0033/0.0367): (0.012,0.014) is
    # inside NO base cell but inside a 48x48 cell.
    clear_scene()
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0.012, 0.014, 0.485))
    pin = bpy.context.active_object
    pin.name = "Pin"
    pin.scale = (0.01, 0.01, 0.97)          # 1cm pin, z 0..0.97
    bpy.ops.object.transform_apply(scale=True)
    bpy.ops.mesh.primitive_cube_add(size=0.4, location=(0.05, 0.02, 1.3))
    saucer = bpy.context.active_object
    saucer.name = "Saucer"
    rep4 = PL.place_on(saucer, pin, footprint='grid', keep_xy=True,
                       grid_n=12)
    check("F4.pin_found", round(zmin(saucer) - 0.97, 4) <= 0.001, True)
    check("F4.refined", "footprint_grid_refined" in rep4, True)

    print()
    if FAILS:
        print(f"[test_f17] FAILURES ({len(FAILS)}): {FAILS}")
        sys.exit(1)
    print("[test_f17] ALL PASS")


main()
