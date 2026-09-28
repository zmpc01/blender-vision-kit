"""test_t4_table.py — T4: table + mug placement, the classic failures.

Scene: Ground + Table (top 1.2x0.8x0.05 @ z[0.70,0.75] + 4 legs
0.06x0.06x0.7 at the corners, joined as ONE object "Table" — selection-
leak guarded per T2) + Mug (cylinder r=0.04 h=0.09) + Fruit Bowl
(uv_sphere r=0.08, z-scaled 0.5, center at tabletop +0.02 -> pole 20mm
into the tabletop: INTENTIONAL bug to exercise the detection threshold +
one-shot repair).

  1. place_on(Mug, Table, clearance=0)     -> bottom 0.75 +-1.5mm, state
     TOUCHING, and NOT on the floor (supports=[Table] is one joined object
     incl. legs; z_bottom > 0.7 asserted)
  2. place_on(Mug, Table, clearance=0.002) -> CLEAR 2mm
  3. "cup left on the floor under the table" classic: mug parked on the
     floor under the tabletop -> pair (Mug, Table) CLEAR with big
     clearance; then mug top raised to the tabletop underside and pushed
     10mm up -> PENETRATING ~10mm (the through-the-tabletop case).
     NOTE: the task spec said "top 10mm above floor"; the load-bearing
     assertions are CLEAR+big-gap, then PEN~10mm after a 10mm push — the
     latter requires the pre-push top at the underside (z=0.70), so the
     faithful classic (mug standing on the floor, top at 0.09) is what we
     test for the CLEAR stage.
  4. bowl sunk 20mm (intentional) -> PENETRATING ~20mm; then
     place_on(Bowl, Table, clearance=0) -> TOUCHING/CLEAR (one-shot
     repair of the classic "sunk into table" bug)
  5. audit_scene() whole scene at 3 stages -> counts + failed as expected
  6. ascii_pair_map(Mug, Table) -> 'X' while the mug is over the table;
     after mug.location.x += 0.7 -> no 'X' (A/B separated)
Runs INSIDE Blender via run.sh:
  cd <kit-checkout> && bash run.sh --background \
      --python tests/test_t4_table.py
"""
import sys, json, os
# placement_lib lives in the kit's scripts/ (sibling of tests/); the
# PLACEMENT_LAB env fallback points at the placement-lab R&D repo. Try both.
_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS = os.path.abspath(os.path.join(_HERE, "..", "scripts"))
_LAB_LIB = os.path.join(os.environ.get("PLACEMENT_LAB", "/home/z/placement-lab"), "lib")
for _p in (_SCRIPTS, _LAB_LIB):
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)
import bpy
import placement_lib as PL

_REPO_ROOT = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), ".."))
_OUT_ROOT = os.environ.get("KIT_OUT",
                           os.path.join(_REPO_ROOT, "output", "tests"))
OUT = os.path.join(_OUT_ROOT, "t4_results.json")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
FAILS = []

TABLE_TOP_Z = 0.75


def check(label, got, expect, tol=None):
    ok = (abs(got - expect) <= tol) if tol is not None else (got == expect)
    if not ok:
        FAILS.append(f"{label}: got {got!r} expected {expect!r}")
    return ok


def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def box(name, size, loc, color=(0.6, 0.6, 0.65)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc,
                                    scale=(size[0], size[1], size[2]))
    o = bpy.context.active_object
    o.name = name
    m = bpy.data.materials.new(name + "_m")
    m.diffuse_color = (*color, 1.0)
    o.data.materials.append(m)
    return o


def build_table():
    """Top + 4 legs joined into ONE object 'Table' (world-baked)."""
    top = box("TableTop", (1.2, 0.8, 0.05), (0, 0, 0.725),
              (0.45, 0.3, 0.15))
    legs = [box(f"Leg{sx}{sy}", (0.06, 0.06, 0.7),
                (sx * 0.54, sy * 0.34, 0.35), (0.3, 0.2, 0.1))
            for sx in (-1, 1) for sy in (-1, 1)]
    bpy.ops.object.select_all(action='DESELECT')  # critical: Ground is
    bpy.context.view_layer.objects.active = top   # still selected here!
    for o in [top] + legs:
        o.select_set(True)
    bpy.ops.object.join()
    table = bpy.context.active_object
    table.name = "Table"
    # bake mesh into world coords (join keeps the top's offset origin)
    bpy.ops.object.transform_apply(location=True, scale=True)
    for o in bpy.data.objects:
        o.select_set(False)
    return table


def build_mug(loc):
    bpy.ops.mesh.primitive_cylinder_add(radius=0.04, depth=0.09,
                                        location=loc, vertices=32)
    o = bpy.context.active_object
    o.name = "Mug"
    m = bpy.data.materials.new("Mug_m")
    m.diffuse_color = (0.8, 0.8, 0.85, 1.0)
    o.data.materials.append(m)
    return o


def build_bowl(loc):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.08, location=loc,
                                         segments=32, ring_count=16)
    o = bpy.context.active_object
    o.name = "Bowl"
    o.scale = (1.0, 1.0, 0.5)   # half-sunken fruit bowl (intentional bug)
    m = bpy.data.materials.new("Bowl_m")
    m.diffuse_color = (0.7, 0.25, 0.15, 1.0)
    o.data.materials.append(m)
    return o


def mug_bottom_z():
    mn, _ = PL._aabb(bpy.data.objects["Mug"])
    return mn.z


def audit_summary(tag, expect_pen=None, expect_failed=None):
    """Whole-scene audit with counts/failed printed + asserted (test 5)."""
    a = PL.audit_scene()
    pen = a["state_counts"].get("PENETRATING", 0)
    print(f"[T4] {tag}: audit pairs={a['pairs_checked']} "
          f"counts={a['state_counts']} failed={a['failed']}")
    if expect_pen is not None:
        check(f"{tag}.pen_count", pen, expect_pen)
    if expect_failed is not None:
        check(f"{tag}.failed", a["failed"], expect_failed)
    return a


def main():
    R = {}
    clear()
    box("Ground", (12, 12, 0.1), (0, 0, -0.05), (0.35, 0.4, 0.35))
    build_table()
    mug = build_mug((0.25, 0.15, 0.4))            # mid-air, below the top
    build_bowl((-0.3, -0.2, TABLE_TOP_Z + 0.02))  # pole 20mm into the top
    bpy.context.view_layer.update()
    PL.clear_bvh_cache()

    # -- 5a. initial audit: bowl penetrating, scene failed -------------------
    R["audit_initial"] = audit_summary("audit.initial", expect_pen=1,
                                       expect_failed=True)

    # -- 1. one-shot: mug rests on the tabletop, exact contact ---------------
    r1 = PL.place_on(mug, bpy.data.objects["Table"], clearance=0.0,
                     footprint='bottom')
    z1 = mug_bottom_z()
    st1 = r1["post_contact"][0]["state"]
    print(f"[T4] place_on rest: z_bottom={z1:.5f} (expect {TABLE_TOP_Z}) "
          f"state={st1} ok={r1['ok']} multi_level={r1['multi_level']} "
          f"timings={r1['timings_ms']}ms")
    check("rest.bottom_z", round(z1, 4), round(TABLE_TOP_Z, 4), tol=0.0015)
    check("rest.above_floor", z1 > 0.7, True)     # NOT resting on the floor
    check("rest.state", st1, "TOUCHING")
    check("rest.ok", r1["ok"], True)
    check("rest.multi_level", r1["multi_level"], False)
    R["rest"] = r1

    # -- 2. 2mm clearance -----------------------------------------------------
    r2 = PL.place_on(mug, bpy.data.objects["Table"], clearance=0.002,
                     footprint='bottom')
    z2 = mug_bottom_z()
    st2 = r2["post_contact"][0]["state"]
    cl2 = r2["post_contact"][0]["clearance_mm"]
    print(f"[T4] place_on 2mm: z_bottom={z2:.5f} (expect 0.752) "
          f"state={st2} clear={cl2}mm")
    check("clear2.bottom_z", round(z2, 4), round(TABLE_TOP_Z + 0.002, 4),
          tol=0.0015)
    check("clear2.state", st2, "CLEAR")
    check("clear2.clearance_mm", cl2, 2.0, tol=0.5)
    R["clear2"] = r2

    # -- 3a. mug parked on the floor UNDER the table (classic) -----------------
    mug.location = (0.25, 0.15, 0.045)   # bottom on floor, top at 0.09
    bpy.context.view_layer.update()
    PL.clear_bvh_cache()
    a3 = PL.audit_scene(pairs=[["Mug", "Table"]])
    p3 = a3["pairs"][0]
    print(f"[T4] under-table: {p3['state']} clear={p3['clearance_mm']}mm "
          f"(tabletop far above the parked mug)")
    check("under.state", p3["state"], "CLEAR")
    check("under.big_clearance", (p3["clearance_mm"] or 0) > 200.0, True)
    R["under_floor"] = p3

    # -- 3b. push the mug 10mm up THROUGH the tabletop -------------------------
    mug.location.z = 0.655                # top exactly at underside (0.70)
    bpy.context.view_layer.update()
    PL.clear_bvh_cache()
    mug.location.z += 0.01                # +10mm -> top 0.71, 10mm inside
    bpy.context.view_layer.update()
    PL.clear_bvh_cache()
    a3b = PL.audit_scene(pairs=[["Mug", "Table"]])
    p3b = a3b["pairs"][0]
    print(f"[T4] through-table: {p3b['state']} "
          f"pen={p3b['penetration_mm']}mm (expect ~10)")
    check("through.state", p3b["state"], "PENETRATING")
    check("through.pen_mm", p3b["penetration_mm"], 10.0, tol=0.5)
    R["through_table"] = p3b

    # -- 5b. mid audit: mug AND bowl both penetrating ---------------------------
    R["audit_mid"] = audit_summary("audit.mid", expect_pen=2,
                                   expect_failed=True)

    # -- 4a. bowl intentional partial embed --------------------------------------
    a4 = PL.audit_scene(pairs=[["Bowl", "Table"]])
    p4 = a4["pairs"][0]
    print(f"[T4] bowl sunk: {p4['state']} pen={p4['penetration_mm']}mm "
          f"(expect ~20 — half-sunken bowl)")
    check("bowl.state", p4["state"], "PENETRATING")
    check("bowl.pen_mm", p4["penetration_mm"], 20.0, tol=0.5)
    R["bowl_sunk"] = p4

    # -- 4b. one-shot repair of the classic "sunk into table" bug ----------------
    r4b = PL.place_on(bpy.data.objects["Bowl"], bpy.data.objects["Table"],
                      clearance=0.0, footprint='bottom')
    st4b = r4b["post_contact"][0]["state"]
    print(f"[T4] bowl repaired: state={st4b} "
          f"pen={r4b['post_contact'][0]['penetration_mm']} "
          f"clear={r4b['post_contact'][0]['clearance_mm']} ok={r4b['ok']}")
    check("bowl_repair.ok", r4b["ok"], True)
    check("bowl_repair.state", st4b in ("TOUCHING", "CLEAR"), True)
    R["bowl_repaired"] = r4b

    # -- 5c. repair the mug too, then final audit: all clean ----------------------
    r5 = PL.place_on(mug, bpy.data.objects["Table"], clearance=0.0,
                     footprint='bottom')
    check("mug_repair.ok", r5["ok"], True)
    R["mug_repaired_state"] = r5["post_contact"][0]["state"]
    R["audit_final"] = audit_summary("audit.final", expect_failed=False)
    check("audit.final.no_pen",
          "PENETRATING" in R["audit_final"]["state_counts"], False)

    # -- 6. ascii pair maps: XY overlap on/off -------------------------------------
    table = bpy.data.objects["Table"]
    txt1, leg1 = PL.ascii_pair_map(mug, table)
    print(f"[T4] pair map (mug over table):\n{txt1}\n{leg1}")
    check("asciimap.overlap_X", "X" in txt1, True)
    mug.location.x += 0.7                 # 0.25 -> 0.95: off the edge
    bpy.context.view_layer.update()
    txt2, leg2 = PL.ascii_pair_map(mug, table)
    print(f"[T4] pair map (mug off edge):\n{txt2}\n{leg2}")
    check("asciimap.no_X", "X" in txt2, False)
    check("asciimap.both_present", ("A" in txt2 and "B" in txt2), True)
    R["ascii_maps"] = {"over": {"map": txt1, "legend": leg1},
                       "off_edge": {"map": txt2, "legend": leg2}}

    verdict = "FAIL:\n" + "\n".join(FAILS) if FAILS else "ALL PASS"
    with open(OUT, "w") as f:
        json.dump({"fail": FAILS, "results": R}, f, indent=2, default=str)
    print(f"[T4] {verdict}")
    print(f"[T4] wrote {OUT}")


main()
