"""test_t5_physics.py — T5 regression: physics_place ops (design v3 D10).
Runs INSIDE Blender. One process, multiple scenes (probe_f5 proved
factory-reset + rb ops works with deselect-all discipline).

  a: float -> settle exact (SETTLED, TOUCHING 0.0, orientation kept)
  b: penetration repair='physics' apply='end' -> REPAIRED_BY_PHYSICS;
     apply='none' -> REPAIR_SIMULATED + scene restored;
     repair='refuse' -> REFUSED_PENETRATING
  c: 3-book stack -> no pen, all AT_REST/SETTLED, orientation kept
  d: oracle block (mug + lip) -> BLOCKED, blocked_by names lip
  e: gate on mixed scene (float + pen + light) -> REJECTED with fix
     items; non-mesh objects must not abort (F14/R4)
  f: determinism + teardown invariants (sim chain, no rb left)
  g: animated mover -> refused with channel names
  r: margin-sum law (probe_hull_pop): hull-hull rest pops ~SUM(margins);
     with _RB_MARGIN=2mm a 4mm pop must read REACHED (margin-derived
     tolerance), not BLOCKED (the old fixed 2.5mm guard)
"""
import sys, os, json, math
_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS = os.path.abspath(os.path.join(_HERE, "..", "scripts"))
for _p in (_SCRIPTS,):
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)
import bpy
from mathutils import Matrix, Vector
import placement_lib as PL
import physics_place as PP

_REPO_ROOT = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), ".."))
_OUT_ROOT = os.environ.get("KIT_OUT",
                           os.path.join(_REPO_ROOT, "output", "tests"))
OUT = os.path.join(_OUT_ROOT, "t5_results.json")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
FAIL = []


def check(label, got, expect, tol=None):
    ok = (abs(got - expect) <= tol) if tol is not None else (got == expect)
    if not ok:
        FAIL.append(f"{label}: got {got!r}, expected {expect!r}")
    return ok


def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.gravity = (0, 0, -9.81)
    # kill any rb world carried by the factory scene
    if sc.rigidbody_world is not None:
        PP._remove_world()


def box(name, size, loc):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.data.transform(Matrix.Diagonal((size[0], size[1], size[2], 1.0)))
    return o


def cyl(name, r, depth, loc):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth,
                                        vertices=24, location=loc)
    o = bpy.context.active_object
    o.name = name
    return o


def teardown_invariants(tag):
    sc = bpy.context.scene
    check(f"{tag}.no_world", sc.rigidbody_world is None, True)
    check(f"{tag}.no_rb",
          any(o.rigid_body is not None for o in sc.objects), False)


def main():
    results = {}

    # ---------------- T5a: float -> settle exact ----------------
    clear()
    floor = box("Floor", (4, 4, 0.2), (0, 0, -0.1))
    cube = box("Cube", (0.3, 0.3, 0.3), (0, 0, 0.5))   # 200mm above
    bpy.context.view_layer.update()
    r = PP.settle(objs=[cube], environment=[floor], apply='end')
    check("T5a.verdict", r["verdict"], "PASS")
    v = r["objects"][0]
    check("T5a.mover_verdict", v["verdict"], "SETTLED")
    check("T5a.tilt_kept", v["rotation_tilt_deg"], 0.0, tol=0.5)
    post = PL.pair_contact(floor, cube)
    check("T5a.contact", post["state"], "TOUCHING")
    check("T5a.exact", post.get("clearance_mm"), 0.0, tol=0.05)
    teardown_invariants("T5a")
    results["T5a"] = r["verdict"]

    # ---------------- T5b: penetration repair modes ----------------
    for mode, expect, apply_mode in (
            ("physics_end", "REPAIRED_BY_PHYSICS", 'end'),
            ("physics_none", "REPAIR_SIMULATED", 'none')):
        clear()
        floor = box("Floor", (4, 4, 0.2), (0, 0, -0.1))
        cube = box("Cube", (0.3, 0.3, 0.3), (0, 0, 0.15 - 0.025))  # 25mm in
        bpy.context.view_layer.update()
        r = PP.settle(objs=[cube], environment=[floor],
                      repair_penetrations='physics', apply=apply_mode)
        v = r["objects"][0]
        check(f"T5b.{mode}.verdict", v["verdict"], expect)
        if mode == "physics_end":
            post = PL.pair_contact(floor, cube)
            check("T5b.physics_end.contact", post["state"], "TOUCHING")
            check("T5b.physics_end.pen0_reported",
                  v.get("start_pen_mm") is not None, True)
        else:
            post = PL.pair_contact(floor, cube)
            check("T5b.physics_none.restored", post["state"],
                  "PENETRATING")
            check("T5b.physics_none.pen",
                  post.get("penetration_mm"), 25.0, tol=0.5)
    clear()
    floor = box("Floor", (4, 4, 0.2), (0, 0, -0.1))
    cube = box("Cube", (0.3, 0.3, 0.3), (0, 0, 0.125))
    bpy.context.view_layer.update()
    r = PP.settle(objs=[cube], environment=[floor],
                  repair_penetrations='refuse')
    check("T5b.refuse.verdict", r["verdict"], "REFUSED_PENETRATING")
    teardown_invariants("T5b")
    results["T5b"] = "ok"

    # ---------------- T5c: 3-book stack ----------------
    clear()
    desk = box("Desk", (2, 2, 0.1), (0, 0, 0.45))
    b1 = box("Book1", (0.4, 0.3, 0.05), (0, 0, 0.55))
    b2 = box("Book2", (0.35, 0.28, 0.04), (0.01, 0.005, 0.595))
    b3 = box("Book3", (0.32, 0.26, 0.04), (-0.005, 0.01, 0.635))
    bpy.context.view_layer.update()
    r = PP.settle(objs=[b1, b2, b3], environment=[desk], apply='end')
    check("T5c.verdict", r["verdict"], "PASS")
    for v in r["objects"]:
        check(f"T5c.{v['obj']}.verdict_ok",
              v["verdict"] in ("AT_REST", "SETTLED"), True)
        check(f"T5c.{v['obj']}.tilt", v["rotation_tilt_deg"], 0.0,
              tol=0.5)
    post = PL.audit_scene(clearance_pad_mm=50)
    check("T5c.no_pen", post["failed"], False)
    teardown_invariants("T5c")
    results["T5c"] = r["verdict"]

    # ---------------- T5d: oracle witness (two cases) ----------------
    # d1: request INSIDE the lip -> REFUSED_PENETRATING naming Lip
    #     (the "jeep door is stopping it" witness)
    clear()
    ground = box("Ground", (6, 6, 0.2), (0, 0, -0.1))
    lip = box("Lip", (0.5, 0.5, 0.12), (0, 0, 0.06))   # top at 0.12
    mug = box("Mug", (0.16, 0.16, 0.2), (0, 0.3, 0.32))  # above lip column? no:
    # move mug xy INTO the lip column first (oracle request is z-only)
    mug.location = (0, 0, 0.32)
    bpy.context.view_layer.update()
    r = PP.oracle(mug, target_z=0.05)   # request: bottom INSIDE the lip
    check("T5d1.verdict", r["verdict"], "REFUSED_PENETRATING")
    witness = json.dumps(r.get("penetrating_pairs", []))
    check("T5d1.names_lip", "Lip" in witness, True)
    teardown_invariants("T5d1")

    # d2: mug balanced half-off the lip edge at its supported height ->
    #     tips off, lands lower, and the lip must surface as a contact
    #     witness (blocked_by or contacts_lateral) — the obstruction is
    #     named either way
    clear()
    ground = box("Ground", (6, 6, 0.2), (0, 0, -0.1))
    lip = box("Lip", (0.5, 0.5, 0.12), (0, 0, 0.06))
    mug = box("Mug", (0.16, 0.16, 0.2), (0.28, 0, 0.22))  # half over edge
    bpy.context.view_layer.update()
    req_z = PL._aabb(mug)[0].z
    r = PP.oracle(mug, target_z=req_z)
    check("T5d2.settled_lower", r["disp_z_mm"] < -5.0, True)
    witness = json.dumps(r.get("blocked_by", [])) + \
        json.dumps(r.get("contacts_lateral", []))
    check("T5d2.lip_witness", "Lip" in witness, True)
    teardown_invariants("T5d2")
    results["T5d"] = "ok"

    # ---------------- T5e: gate on mixed scene ----------------
    clear()
    floor = box("Floor", (4, 4, 0.2), (0, 0, -0.1))
    good = box("Good", (0.3, 0.3, 0.3), (0.8, 0, 0.15))   # resting
    floater = box("Floater", (0.2, 0.2, 0.2), (-0.8, 0, 0.5))  # floating
    sunk = box("Sunk", (0.2, 0.2, 0.2), (0, 0, 0.05))     # 50mm into floor
    light = box("LightBox", (0.05, 0.05, 0.05), (0, 0, 2.0))
    light.select_set(False)
    bpy.ops.object.light_add(type='POINT', location=(0, 0, 3))
    bpy.context.view_layer.update()
    r = PP.gate()
    check("T5e.verdict", r["verdict"], "REJECTED")
    fq = json.dumps(r["fix_queue"])
    check("T5e.float_item", "Floater" in fq, True)
    check("T5e.pen_item", "Sunk" in fq, True)
    check("T5e.no_crash_nonmesh", r["verdict"] == "REJECTED", True)
    teardown_invariants("T5e")
    results["T5e"] = r["verdict"]

    # ---------------- T5f: determinism + sim chain ----------------
    clear()
    floor = box("Floor", (4, 4, 0.2), (0, 0, -0.1))
    cube = box("Cube", (0.3, 0.3, 0.3), (0, 0, 0.7))
    bpy.context.view_layer.update()
    r1 = PP.settle(objs=[cube], environment=[floor], apply='none')
    z1 = r1["objects"][0]["end_bottom_z"]
    # chained second sim in the SAME process (D3) + geometric op after
    r2 = PP.settle(objs=[cube], environment=[floor], apply='none')
    z2 = r2["objects"][0]["end_bottom_z"]
    check("T5f.determinism", round(abs(z1 - z2), 5), 0.0, tol=0.001)
    check("T5f.scene_restored", PL.pair_contact(floor, cube)["state"],
          "CLEAR")
    # geometric op after physics ops still exact (F12/F7)
    PL.place_on(cube, floor, override='keyframe')
    post = PL.pair_contact(floor, cube)
    check("T5f.place_after_physics", post["state"], "TOUCHING")
    teardown_invariants("T5f")
    results["T5f"] = "ok"

    # ---------------- T5g: animated mover refused ----------------
    clear()
    floor = box("Floor", (4, 4, 0.2), (0, 0, -0.1))
    cube = box("Cube", (0.3, 0.3, 0.3), (0, 0, 0.7))
    cube.keyframe_insert(data_path="location", index=2, frame=1)
    cube.keyframe_insert(data_path="location", index=2, frame=30)
    bpy.context.view_layer.update()
    r = PP.settle(objs=[cube], environment=[floor])
    check("T5g.refused", r["verdict"], "NO_MOVERS")
    check("T5g.excluded_reason",
          any("animated" in json.dumps(e) for e in r["excluded"]), True)
    teardown_invariants("T5g")
    results["T5g"] = r["verdict"]

    # ---------------- T5h: place() auto-env (mug -> desk exact) ----
    # (usability round A: place() gave the world no colliders -> the mug
    # void-fell 16.85m and read NO_SUPPORT)
    clear()
    desk = box("Desk", (2, 1, 0.08), (0, 0, 0.46))     # top 0.50
    mug = cyl("Mug", 0.07, 0.18, (0.3, 0.0, 0.59))     # 90mm above desk
    bpy.context.view_layer.update()
    r = PP.place(mug)
    check("T5h.verdict", r["verdict"], "PLACED")
    check("T5h.rests_on", r.get("rests_on"), "Desk")
    post = PL.pair_contact(desk, mug)
    check("T5h.contact", post["state"] in ("TOUCHING", "CLEAR"), True)
    check("T5h.gap", (post.get("clearance_mm") or 0), 0.0, tol=0.5)
    teardown_invariants("T5h")

    # ---------------- T5i: oracle auto-env + full restore ----------
    clear()
    ground = box("Ground", (6, 6, 0.2), (0, 0, -0.1))
    lip = box("Lip", (0.5, 0.5, 0.12), (0, 0, 0.06))
    mug = box("Mug", (0.16, 0.16, 0.2), (0, 0.3, 0.1))
    bpy.context.view_layer.update()
    pre_z = round(mug.matrix_world.translation.z, 5)
    pre_keys = mug.animation_data is not None
    r = PP.oracle(mug, target_z=0.4)   # above the lip column: air
    check("T5i.not_freefall", abs(r["disp_z_mm"]) < 1000.0, True)
    check("T5i.scene_restored_z",
          round(mug.matrix_world.translation.z, 5), pre_z, tol=1e-4)
    check("T5i.no_keys_added", mug.animation_data is not None, pre_keys)
    teardown_invariants("T5i")

    # ---------------- T5j: gate auto-lane on the janitor fixture ---
    # (floor must stay passive; floats/pens caught; PASS not vacuous)
    clear()
    floor = box("Floor", (8, 8, 0.2), (0, 0, -0.1))
    desk = box("Desk", (2, 1, 0.08), (0, 0, 0.46))
    lamp = box("Lamp", (0.18, 0.18, 0.45), (0.5, 0.2, 0.7775))  # float 55
    mug = box("Mug", (0.16, 0.16, 0.2), (-0.5, -0.2, 0.42))     # pen 12
    crate = box("Crate", (0.5, 0.5, 0.5), (1.5, 0, 0.25))       # ok
    bpy.context.view_layer.update()
    r = PP.gate()
    check("T5j.verdict", r["verdict"], "REJECTED")
    fq = json.dumps(r["fix_queue"])
    check("T5j.names_mug", "Mug" in fq, True)
    check("T5j.names_lamp", "Lamp" in fq, True)
    check("T5j.no_floor_escape",
          "escaped during verify" not in fq, True)
    check("T5j.no_world",
          any(o.rigid_body is None for o in
              (floor, desk, lamp, mug, crate)), True)
    teardown_invariants("T5j")

    # ---------------- T5k: overhang stack settle (round A gaps) ----
    clear()
    desk = box("Desk", (2, 1, 0.08), (0, 0, 0.46))
    # planted: Book1 floats 20mm above desk top (bottom 0.52 vs 0.50);
    # books 2/3 rest exactly on the book below (b1 top 0.57, b2 top 0.61)
    b1 = box("Book1", (0.4, 0.3, 0.05), (0.0, 0.0, 0.545))
    b2 = box("Book2", (0.36, 0.28, 0.04), (0.02, 0.01, 0.59))
    b3 = box("Book3", (0.32, 0.26, 0.04), (-0.015, 0.008, 0.63))
    bpy.context.view_layer.update()
    r = PP.settle(objs=[b1, b2, b3], environment=[desk], apply='end')
    check("T5k.verdict", r["verdict"], "PASS")
    post = PL.audit_scene(clearance_pad_mm=50)
    check("T5k.no_pen", post["failed"], False)
    # every book must be within the touch band of its support
    for pair in post["pairs"]:
        names = {pair["a"], pair["b"]}
        if names in ({"Desk", "Book1"}, {"Book1", "Book2"},
                     {"Book2", "Book3"}):
            check(f"T5k.{pair['a']}x{pair['b']}",
                  pair["state"], "TOUCHING")
    teardown_invariants("T5k")

    # ---------------- T5l: import-style scaled mover (tiebreak TB1) --
    # session-13b: object scale is HONORED by rb shapes in every
    # construction path measured — scaled objects are sim-ready as-is
    # (the old scale_unbaked exclusion was friction against GLTF imports)
    clear()
    desk = box("Desk", (2, 1, 0.08), (0, 0, 0.46))     # top 0.50
    mug = cyl("Mug", 0.07, 0.18, (0.3, 0.0, 0.70))
    mug.scale = (1.5, 1.0, 1.0)                        # import-style scale
    bpy.context.view_layer.update()
    r = PP.place(mug)
    check("T5l.verdict", r["verdict"], "PLACED")
    check("T5l.rests_on", r.get("rests_on"), "Desk")
    check("T5l.no_scale_exclusion",
          all("scale" not in json.dumps(e) for e in r["excluded"]), True)
    teardown_invariants("T5l")

    # ---------------- T5m: off-origin env stays faithful (TB3/A1) ----
    # BOX collision is origin-centered; off-origin env must fall back to
    # CONVEX_HULL (origin-independent) — a ball rests on the VISUAL top
    clear()
    slab = box("Slab", (1, 1, 0.3), (0, 0, 0))
    slab.data.transform(Matrix.Translation((0, 0, 0.15)))  # visual z 0..0.3
    slab.location = (0, 0, 0)                              # origin at bottom
    ball = box("Ball", (0.1, 0.1, 0.1), (0, 0, 1.0))
    bpy.context.view_layer.update()
    r = PP.place(ball)
    check("T5m.verdict", r["verdict"], "PLACED")
    check("T5m.rests_on", r.get("rests_on"), "Slab")
    post = PL.pair_contact(slab, ball)
    check("T5m.contact", post["state"], "TOUCHING")
    teardown_invariants("T5m")

    # ---------------- T5n: multi-level snap discrimination (A6) ------
    # The sim legitimately collapses tilted rests to single-support
    # equilibria, so the HELPER is unit-tested with constructed poses:
    # (n1) tray contacting two books of different heights -> multi=True
    # (n2) tray flat on one book, cantilevered over the other -> False
    # (n3) place() e2e on the same scene stays PLACED with no burial.
    clear()
    import math as _math
    desk = box("Desk", (2, 1, 0.08), (0, 0, 0.46))        # top 0.50
    book_hi = box("BookHi", (0.4, 0.3, 0.06), (-0.25, 0, 0.53))  # top .56
    book_lo = box("BookLo", (0.4, 0.3, 0.045), (0.25, 0, 0.5225))  # .545
    tray = box("Tray", (0.9, 0.2, 0.04), (0, 0, 0.75))
    bpy.context.view_layer.update()
    # n1: tilt so both ends contact their book tops (15mm over 0.5m)
    ang = _math.atan2(0.015, 0.5)
    tray.rotation_euler = (0, ang, 0)
    tray.location = (0, 0, 0.5745)
    bpy.context.view_layer.update()
    others = [o for o in bpy.context.scene.objects
              if o.type == 'MESH' and o.name != 'Tray']
    sup, below, multi = PP._snap_supports(tray, others, 150.0, 8.0)
    check("T5n1.multi", multi, True)
    check("T5n1.both_books",
          {o.name for o in sup} >= {"BookHi", "BookLo"}, True)
    # n2: flat tray resting on BookHi only (cantilever over BookLo)
    tray.rotation_euler = (0, 0, 0)
    tray.location = (-0.2, 0, 0.582)   # right half over BookLo, 20mm above
    bpy.context.view_layer.update()
    sup2, below2, multi2 = PP._snap_supports(tray, others, 150.0, 8.0)
    check("T5n2.single_support", multi2, False)
    # n3: e2e place() on the same scene
    clear()
    desk = box("Desk", (2, 1, 0.08), (0, 0, 0.46))
    book_hi = box("BookHi", (0.4, 0.3, 0.06), (-0.25, 0, 0.53))
    book_lo = box("BookLo", (0.4, 0.3, 0.045), (0.25, 0, 0.5225))
    tray = box("Tray", (0.9, 0.2, 0.04), (0, 0, 0.72))
    bpy.context.view_layer.update()
    r = PP.place(tray)
    check("T5n3.verdict", r["verdict"], "PLACED")
    post = PL.audit_scene(clearance_pad_mm=50)
    check("T5n3.no_burial", post["failed"], False)
    teardown_invariants("T5n")

    # ---------------- T5o: gate rejects NESTED (mission) -------------
    # mug fully inside a closed crate is overlapping even with no
    # face-pair overlap — "absolutely nothing can overlap, we reject"
    clear()
    floor = box("Floor", (4, 4, 0.2), (0, 0, -0.1))
    crate = box("Crate", (0.5, 0.5, 0.5), (0, 0, 0.25))
    inner = box("Inner", (0.2, 0.2, 0.2), (0, 0, 0.25))
    bpy.context.view_layer.update()
    r = PP.gate()
    check("T5o.verdict", r["verdict"], "REJECTED")
    check("T5o.nested_reported", len(r.get("nested_pairs", [])) >= 1, True)
    fq = json.dumps(r["fix_queue"])
    check("T5o.nested_in_queue", "NESTED" in fq or "contained" in fq, True)
    teardown_invariants("T5o")

    # ---------------- T5p: margin-pop rest reads REACHED (round B) ---
    # a demanded pose that ends 2mm above request with NO contact-distance
    # pair is the hull-margin pop (gotcha #61), not BLOCKED; blocked_by
    # must stay empty (no nearest-neighbour directory)
    clear()
    ground = box("Ground", (6, 6, 0.2), (0, 0, -0.1))
    plate = box("Plate", (1.2, 0.5, 0.05), (0, 0, 0.975))   # top 1.0
    post = box("Post", (0.08, 0.5, 1.0), (-0.6, 0, 0.5))
    crate = box("Crate", (0.3, 0.3, 0.3), (0.0, 0.0, 0.15))
    crate.location = (0.0, 0.0, 0.15)
    bpy.context.view_layer.update()
    r = PP.oracle(crate, target_z=1.0)
    check("T5p.verdict", r["verdict"], "REACHED")
    check("T5p.margin_pop", (r.get("margin_pop_mm") or 99) <= 2.5, True)
    check("T5p.no_blocked", not r.get("blocked_by"), True)
    check("T5p.restored",
          round(crate.matrix_world.translation.z, 4), 0.15, tol=1e-3)
    teardown_invariants("T5p")

    # ---------------- T5q: mid-air demand falls -> FELL_BELOW (rnd C) --
    clear()
    ground = box("Ground", (6, 6, 0.2), (0, 0, -0.1))
    crate = box("Crate", (0.3, 0.3, 0.3), (0.4, 0.0, 0.15))
    bpy.context.view_layer.update()
    r = PP.oracle(crate, target_z=0.5)   # nothing under (0.4, 0) at 0.5
    check("T5q.verdict", r["verdict"], "FELL_BELOW")
    check("T5q.rests_on", r.get("rests_on"), "Ground")
    check("T5q.restored",
          round(crate.matrix_world.translation.z, 4), 0.15, tol=1e-3)
    teardown_invariants("T5q")

    # ---------------- T5r: margin-sum law (probe_hull_pop, s14b) ------
    # hull-hull rest separation ~= SUM of the two bodies' margins. With
    # _RB_MARGIN retargeted to 2mm, a demanded rest on a hull support
    # pops ~4mm — above the round-B 2.5mm floor — and must read REACHED
    # via the margin-derived tolerance (the old fixed 2.5mm guard read
    # BLOCKED here: a legitimate rest reported as an obstruction).
    clear()
    PP._RB_MARGIN = 0.002
    try:
        ground = box("Ground", (6, 6, 0.2), (0, 0, -0.1))
        pier = cyl("Pier", 0.04, 0.08, (0, 0, 0.04))    # hull env, top 0.08
        disc = cyl("Disc", 0.03, 0.06, (0, 0, 0.15))    # hull mover
        bpy.context.view_layer.update()
        r = PP.oracle(disc, target_z=0.08)              # exact contact request
        check("T5r.verdict", r["verdict"], "REACHED")
        check("T5r.margin_pop",
              3.0 <= (r.get("margin_pop_mm") or 0.0) <= 5.5, True)
        check("T5r.no_blocked", not r.get("blocked_by"), True)
        check("T5r.restored",
              round(disc.matrix_world.translation.z, 4), 0.15, tol=1e-3)
    finally:
        PP._RB_MARGIN = 0.001
    teardown_invariants("T5r")

    # ---------------- T5s: crossing demand refuses (round E) ----------
    # a demand teleported INTO a wall is a face-CROSSING penetration
    # (penetration_mm None, crossing_depth_mm set) — the pre-flight must
    # refuse it BEFORE the sim (the old filter let it run and the wedged
    # eject flung the object meters away)
    clear()
    ground = box("Ground", (6, 6, 0.2), (0, 0, -0.1))
    wall = box("Wall", (0.1, 2.0, 1.0), (0, 0, 0.5))
    crate = box("Crate", (0.3, 0.3, 0.3), (1.5, 0, 0.15))
    bpy.context.view_layer.update()
    r = PP.oracle(crate, target=(0.0, 0.0, 0.35))   # centered IN the wall
    check("T5s.verdict", r["verdict"], "REFUSED_PENETRATING")
    check("T5s.pairs", len(r.get("penetrating_pairs") or []), 1)
    check("T5s.restored",
          round(crate.matrix_world.translation.z, 4), 0.15, tol=1e-3)
    teardown_invariants("T5s")

    # ---------------- T5t: custom lane keeps supports (round E) -------
    # verify_movers=[disc] where disc rests ON a pier (not grounded):
    # the pier must stay in the verify sim as terrain — the old lane
    # dropped it and the disc "fell" 400mm inside the verify, falsely
    # REJECTing a perfectly-resting mover
    clear()
    ground = box("Ground", (6, 6, 0.2), (0, 0, -0.1))
    pier = box("Pier", (0.6, 0.6, 0.8), (0, 0, 0.4))      # top 0.8
    disc = box("Disc", (0.3, 0.3, 0.1), (0, 0, 0.85))     # bottom 0.8: resting
    bpy.context.view_layer.update()
    r = PP.gate(verify_movers=[bpy.data.objects["Disc"]])
    check("T5t.verdict", r["verdict"], "PASS")
    check("T5t.lane", r.get("settle_verify_lane"), "custom")
    check("T5t.terrain_has_pier", "Pier" in (r.get("settle_verify_terrain") or []),
          True)
    teardown_invariants("T5t")

    # ---------------- T5u: rests_on = settled support (round E) -------
    # a demand that falls BELOW the request but lands on an ELEVATED
    # support must name that support (the old code read rests_on after
    # the restore — at the spawn pose — naming Floor for a crate that
    # settled on the table)
    clear()
    ground = box("Ground", (6, 6, 0.2), (0, 0, -0.1))
    table = box("Table", (0.8, 0.8, 0.5), (0, 0, 0.25))   # top 0.5
    crate = box("Crate", (0.3, 0.3, 0.3), (1.5, 0, 0.15))  # spawned on floor
    bpy.context.view_layer.update()
    r = PP.oracle(crate, target=(0.0, 0.0, 0.7))   # above the table
    check("T5u.verdict", r["verdict"], "FELL_BELOW")
    check("T5u.rests_on", r.get("rests_on"), "Table")
    check("T5u.settled_rests_on", r.get("settled_rests_on"), "Table")
    check("T5u.restored",
          round(crate.matrix_world.translation.z, 4), 0.15, tol=1e-3)
    teardown_invariants("T5u")

    # ------- T5v: exact lateral wedge must not deadlock the gate (H1) ---
    # round-H subject h1: a part resting on a base AND exactly touching
    # two side walls is margin-inflated ~2mm too wide — bullet ejects it
    # UP+SIDEWAYS. The gate used to read that as "floating/unsupported",
    # queued a settle that re-commits the same contact, and deadlocked
    # (REJECT loop the queue can never satisfy). Floats never move UP:
    # upward-dominant ejection is now recorded as sim_ejections (info),
    # not a rejection — unless it is a real launch (> 50mm).
    clear()
    box("Floor", (6, 6, 0.2), (0, 0, -0.1))
    base = box("Sofa_Base", (1.4, 0.75, 0.35), (0, 0, 0.175))
    box("Sofa_ArmL", (0.2, 0.75, 0.55), (-0.8, 0, 0.275))
    box("Sofa_ArmR", (0.2, 0.75, 0.55), (0.8, 0, 0.275))
    back = box("Sofa_Back", (1.4, 0.2, 0.5), (0, 0, 0.60))  # ON base, wedged
    bpy.context.view_layer.update()
    r = PP.gate(fail_hard=False)
    check("T5v.verdict", r["verdict"], "PASS")
    ej = (r.get("sim_ejections") or [])
    for e in ej:
        check(f"T5v.eject_up_dominant_{e.get('obj')}",
              e.get("disp_z_mm", 0) > 0, True)
    check("T5v.no_toppled",
          any(i.get("verdict") == "TOPPLED"
              for i in r.get("instability_pairs", [])), False)
    check("T5v.back_not_rejected",
          "Sofa_Back" in [i.get("obj")
                          for i in r.get("instability_pairs", [])], False)
    teardown_invariants("T5v")

    # ------- T5w: hidden production internals never gate a rest-verify --
    # escape-previz integration: productions hide rig machinery (e.g.
    # zombie variant prototype meshes left at the world origin INSIDE the
    # hero jeep). A hidden overlapping object must produce no audit
    # pairs, never become terrain, and never reject a rest-verify.
    clear()
    box("Floor", (6, 6, 0.2), (0, 0, -0.1))
    table = box("Table", (0.8, 0.8, 0.5), (0, 0, 0.25))   # top 0.5
    prop = box("Prop", (0.2, 0.2, 0.2), (0, 0, 0.6))      # ON table
    junk = box("RigPrototype", (0.3, 0.3, 0.3), (0, 0, 0.6))  # same spot
    junk.hide_render = True
    junk.hide_set(True)
    bpy.context.view_layer.update()
    r = PP.gate(verify_movers=[prop], fail_hard=False)
    check("T5w.verdict", r["verdict"], "PASS")
    check("T5w.hidden_recorded",
          "RigPrototype" in (r.get("hidden_excluded") or []), True)
    check("T5w.no_junk_pairs",
          any("RigPrototype" in (p.get("a"), p.get("b"))
              for p in (r.get("post_audit") or {}).get("pairs", [])), False)
    teardown_invariants("T5w")

    # ---------------- T5x: sign-test INSIDE claims are parity-verified
    # (session-16 subject v2: closed CONE bowl — sign test read a far
    # corner 'inside' at the FULL distance -> impossible 1088mm pen;
    # parity is ground truth. A genuinely sunk cone must report its
    # honest depth, a far corner must read CLEAR.)
    clear()
    counter = box("Counter", (3.0, 3.0, 0.9), (0, 0, 0.45))   # top z=0.9
    bpy.ops.mesh.primitive_cone_add(vertices=32, radius1=0.12, radius2=0.0,
                                    depth=0.1, location=(0.6, -0.6, 0.9))
    sunk = bpy.context.active_object
    sunk.name = "ConeSunk"          # base ring z=0.85 — 50mm REAL sink
    bpy.ops.mesh.primitive_cone_add(vertices=32, radius1=0.12, radius2=0.0,
                                    depth=0.1, location=(-0.9, 0.9, 0.95))
    resting = bpy.context.active_object
    resting.name = "ConeRest"       # base ring z=0.90 — exact contact
    bpy.context.view_layer.update()
    r_sunk = PL.pair_contact(counter, sunk)
    check("T5x.sunk_state", r_sunk["state"], "PENETRATING")
    check("T5x.sunk_depth", r_sunk.get("penetration_mm"), 50.0, tol=6.0)
    r_rest = PL.pair_contact(counter, resting)
    check("T5x.rest_state", r_rest["state"], "TOUCHING")
    teardown_invariants("T5x")

    # ---------------- T5y: BVH cache must not serve pre-commit trees
    # (session-16 subject v3: in-process audit after a physics-style
    # commit read a stale rotated tree -> phantom penetration. The key
    # must hash the POST-depsgraph matrix; no-motion lookups still hit.)
    clear()
    base = box("Base", (2.0, 2.0, 0.2), (0, 0, -0.1))
    rot = box("Rotor", (0.4, 0.4, 0.4), (0.6, 0.0, 0.3))  # bottom 0.1 = CLEAR
    bpy.context.view_layer.update()
    r1 = PL.pair_contact(base, rot)
    check("T5y.pre_state", r1["state"], "CLEAR")
    t1 = PL.world_bvh(rot)
    hit_no_motion = PL.world_bvh(rot) is t1
    check("T5y.cache_hit_no_motion", hit_no_motion, True)
    # commit a 90deg rotation the way the physics teardown does
    from mathutils import Matrix as _M
    rot.matrix_world = _M.Translation((0.6, 0.0, 0.3)) @ \
        _M.Rotation(math.radians(90.0), 4, 'Z')
    bpy.context.view_layer.update()
    r2 = PL.pair_contact(base, rot)
    r3 = PL.pair_contact(base, rot)   # fresh read, same process
    check("T5y.post_consistent", r2["state"], r3["state"])
    check("T5y.post_not_stale",
          r2.get("clearance_mm"), r3.get("clearance_mm"), tol=0.05)
    check("T5y.post_clear", r2["state"], "CLEAR")
    check("T5y.cache_hit_after", PL.world_bvh(rot) is PL.world_bvh(rot), True)
    teardown_invariants("T5y")

    # ------- T5z: positive TOPPLED coverage (QA #5 test-gap) ------------
    # T5v asserts the NEGATIVE (no TOPPLED in a healthy scene); nothing
    # asserted the POSITIVE classification: an off-balance tall box must
    # topple in sim (end tilt > 10 deg -> verdict TOPPLED), and with
    # apply='none' the pre-sim pose must be EXACTLY restored (pure
    # verifier contract). QA probe verified the path fires at 12 deg;
    # this pins it as a regression gate.
    clear()
    floor = box("Floor", (6, 6, 0.2), (0, 0, -0.1))
    tall = box("Tower", (0.25, 0.25, 1.2), (0, 0, 0.75))
    tall.matrix_world = Matrix.Translation((0, 0, 0.75)) @ \
        Matrix.Rotation(math.radians(15), 4, 'Y')
    # 15-deg tilt dips the low corner to z=0.138 (floor top is z=0) — the
    # box starts CLEAR (a tilted box at rest-height would self-penetrate
    # and the refuse-default pre-check would abort before any topple).
    bpy.context.view_layer.update()
    pre_mw = tall.matrix_world.copy()
    r = PP.settle(objs=[tall], environment=[floor], apply='none')
    check("T5z.op_verdict_fail", r["verdict"], "FAIL")  # topple = detected failure
    v = next(o for o in r["objects"] if o["obj"] == "Tower")
    check("T5z.toppled_positive", v["verdict"], "TOPPLED")
    check("T5z.tilt_large", v["rotation_tilt_deg"] > 45.0, True)
    d = (tall.matrix_world.translation - pre_mw.translation).length
    check("T5z.apply_none_restore", d < 1e-6, True)
    check("T5z.teardown_restored",
          r["teardown"]["rb_removed"], 2)
    check("T5z.no_escape", v.get("verdict") != "ESCAPED", True)
    teardown_invariants("T5z")

    # ---------------- summary ----------------
    print(f"[T5] FAILURES: {len(FAIL)}")
    for f in FAIL:
        print(f"[T5]   {f}")
    if not FAIL:
        print("[T5] ALL PASS")
    with open(OUT, "w") as fh:
        json.dump({"failures": FAIL, "results": results}, fh, indent=1)
    print(f"[T5] wrote {OUT}")


main()
