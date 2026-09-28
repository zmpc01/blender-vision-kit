"""scene_scenarios.py — previz-realistic scenario fixtures (session 15).

Usage (inside Blender via blrun):
  --scenario kitchen_counter | warehouse_cratestack | living_room
  --output <path>            : save the .blend here (optional)

Built with the fixture-builder discipline (NEVER transform_apply —
gotcha #58; data-baked sizes; ground-truth `gt` custom prop) and the
round-E lesson: every planted value is SELF-VERIFIED against the built
geometry at build time — a lying fixture poisons usability rounds.
"""
import bpy, sys, json, os
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(flag, default=None):
    if flag in argv:
        return argv[argv.index(flag) + 1]
    return default


def box(name, size, loc, rot_z_deg=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.data.transform(Matrix.Diagonal((size[0], size[1], size[2], 1.0)))
    if rot_z_deg:
        o.rotation_euler = (0, 0, rot_z_deg * 3.14159265 / 180.0)
    return o


def cyl(name, r, depth, loc):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth,
                                        vertices=24, location=loc)
    o = bpy.context.active_object
    o.name = name
    return o


def _aabb(obj):
    pts = [obj.matrix_world @ Vector(v.co) for v in obj.data.vertices]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts),
                 min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts),
                 max(p.z for p in pts)))
    return mn, mx


def _check(tag, got, expect, tol=0.0015):
    if abs(got - expect) > tol:
        raise RuntimeError(
            f"[fixture] GROUND-TRUTH MISMATCH {tag}: built {got:.4f}, "
            f"planted {expect:.4f} (tol {tol}) — fix the arithmetic, "
            f"never ship a lying fixture")


def _assert_scene_clean(allowed=()):
    """Round-G lesson (sC burned its whole budget repairing MY sloppy
    fixture): a usability fixture must be gate-clean EXCEPT its planted
    defects. Runs the real mesh-level audit at build time and ignores
    ONLY the explicitly-allowed pairs — a fixture that fails its own
    gate never ships. (audit_scene's `exclude` drops whole OBJECTS —
    too blunt for planted single-pair defects.)"""
    import placement_lib as _pl
    allowed_pairs = {frozenset(p) for p in allowed}
    rep = _pl.audit_scene()
    for p in rep["pairs"]:
        mm = (f"pen {p.get('penetration_mm')} mm"
              if p.get("penetration_mm") is not None
              else f"gap {p.get('clearance_mm')} mm")
        print(f"[fixture]   pair {p['a']} x {p['b']}: {p['verdict']} "
              f"({mm})")
    bad = [f"{p['a']}x{p['b']}={p['verdict']}"
           for p in rep["pairs"]
           if p["verdict"] in ("PENETRATING", "NESTED", "CROSSING")
           and frozenset((p["a"], p["b"])) not in allowed_pairs]
    if bad:
        raise RuntimeError(
            f"[fixture] SCENE NOT CLEAN (planted-defects-only rule): "
            f"{bad[:6]} — fix the arithmetic, never ship a fixture that "
            f"fails its own gate")


def fresh():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.gravity = (0, 0, -9.81)
    sc.unit_settings.system = 'METRIC'
    return sc


# ---------------------------------------------------------------------------
def build_kitchen_counter():
    """Realistic kitchen strip: counter slab on a base cabinet with a
    backsplash. Props wait loose on the floor in front. Tasks: dress the
    counter (kettle + pot + 3 jars in a row), gate fail_hard PASS."""
    sc = fresh()
    floor = box("Floor", (8, 8, 0.2), (0, 0, -0.1))            # top 0.0
    cabinet = box("Counter_Cabinet", (2.4, 0.6, 0.86), (0, 0.15, 0.43))
    slab = box("Counter_Slab", (2.4, 0.65, 0.06), (0, 0.15, 0.89))
    splash = box("Backsplash", (2.4, 0.06, 0.6), (0, 0.445, 1.22))
    kettle = cyl("Kettle", 0.09, 0.22, (1.6, -0.9, 0.11))
    pot = cyl("Pot", 0.11, 0.14, (0.0, -0.9, 0.07))
    j1 = cyl("Jar_1", 0.045, 0.12, (-1.0, -0.85, 0.06))
    j2 = cyl("Jar_2", 0.045, 0.12, (-1.2, -0.95, 0.06))
    j3 = cyl("Jar_3", 0.045, 0.12, (-1.4, -0.8, 0.06))
    sc["gt"] = json.dumps({
        "counter_top_z": 0.92, "cabinet_top_z": 0.86,
        "props_on_floor": True, "prop_names":
            ["Kettle", "Pot", "Jar_1", "Jar_2", "Jar_3"]})
    _check("cabinet_rest", _aabb(cabinet)[0].z, 0.0)
    _check("cabinet_top", _aabb(cabinet)[1].z, 0.86)
    _check("slab_bottom_on_cabinet",
           _aabb(slab)[0].z - _aabb(cabinet)[1].z, 0.0)
    _check("counter_top", _aabb(slab)[1].z, 0.92)
    _check("splash_bottom_on_slab",
           _aabb(splash)[0].z - _aabb(slab)[1].z, 0.0)
    for p in (kettle, pot, j1, j2, j3):
        _check(f"{p.name}_rest", _aabb(p)[0].z, 0.0)
    _assert_scene_clean()
    return sc


# ---------------------------------------------------------------------------
def build_warehouse_cratestack():
    """Three pallets against a wall. Stack A floats its top crate,
    stack B's crate penetrates its pallet, stack C is correct but
    UNDER-height. Tasks: repair A (float), repair B (penetration),
    then ADD a new crate on stack C (patch-authored, Track I), gate
    fail_hard PASS."""
    sc = fresh()
    floor = box("Floor", (8, 8, 0.2), (0, 0, -0.1))
    wall = box("Wall", (7, 0.15, 2.0), (0, 1.4, 1.0))
    pa = box("Pallet_A", (0.9, 0.9, 0.12), (-2, 0, 0.06))
    pb = box("Pallet_B", (0.9, 0.9, 0.12), (0, 0, 0.06))
    pc = box("Pallet_C", (0.9, 0.9, 0.12), (2, 0, 0.06))
    a1 = box("Crate_A1", (0.7, 0.7, 0.5), (-2, 0, 0.37))    # on pallet A
    a2 = box("Crate_A2", (0.7, 0.7, 0.5), (-2.02, 0.03, 0.93))  # FLOAT 60mm
    b1 = box("Crate_B1", (0.7, 0.7, 0.5), (0, 0, 0.33))     # PEN 40mm
    c1 = box("Crate_C1", (0.7, 0.7, 0.5), (2, 0, 0.37))     # correct
    sc["gt"] = json.dumps({
        "pallet_top_z": 0.12, "crate_h": 0.5,
        "a1_ok": True, "a2_float_mm": 60.0, "b1_pen_mm": 40.0,
        "c1_ok": True, "stack_c_needs": 2})
    _check("pallet_a_top", _aabb(pa)[1].z, 0.12)
    _check("pallet_b_top", _aabb(pb)[1].z, 0.12)
    _check("pallet_c_top", _aabb(pc)[1].z, 0.12)
    _check("a1_on_pallet", _aabb(a1)[0].z - 0.12, 0.0)
    _check("a2_float_mm", (_aabb(a2)[0].z - _aabb(a1)[1].z) * 1000, 60.0)
    _check("b1_pen_mm", (0.12 - _aabb(b1)[0].z) * 1000, 40.0)
    _check("c1_on_pallet", _aabb(c1)[0].z - 0.12, 0.0)
    _assert_scene_clean(allowed=[("Crate_B1", "Pallet_B")])
    return sc


# ---------------------------------------------------------------------------
def build_living_room():
    """Coffee table, sofa (base+back+arms), TV stand + TV, plant pot.
    A book and a remote are misplaced on the floor/rug. Tasks: book
    onto the coffee table, remote onto a sofa ARM (narrow support),
    plant pot into the floor gap between sofa and TV stand, gate
    fail_hard PASS."""
    sc = fresh()
    floor = box("Floor", (8, 8, 0.2), (0, 0, -0.1))            # top 0.0
    rug = box("Rug", (2.2, 1.4, 0.015), (0, -0.2, 0.0075))     # top 0.015
    ttop = box("Table_Top", (1.0, 0.55, 0.05), (0, -0.2, 0.425))
    legs = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            legs.append(box(f"Table_Leg{sx}{sy}", (0.05, 0.05, 0.385),
                            (sx * 0.45, -0.2 + sy * 0.22, 0.2075)))
    # legs rest ON the rug (0.015..0.40) — a coffee table standing on a
    # rug is the realistic arrangement (round-G sC inferred this itself);
    # through-the-rug legs were an unplanned penetration the gate caught
    base = box("Sofa_Base", (1.4, 0.75, 0.35), (0, 1.1, 0.175))
    back = box("Sofa_Back", (1.4, 0.2, 0.5), (0, 1.38, 0.60))
    armL = box("Sofa_ArmL", (0.2, 0.75, 0.55), (-0.8, 1.1, 0.275))
    armR = box("Sofa_ArmR", (0.2, 0.75, 0.55), (0.8, 1.1, 0.275))
    # sofa parts span BETWEEN the arms: base/back are 1.4 wide, arm inner
    # faces sit exactly at x=±0.7 → TOUCHING, never overlapping (the old
    # 1.8-wide parts intersected both the arms and each other)
    stand = box("TV_Stand", (1.2, 0.4, 0.45), (0, -1.2, 0.225))
    tv = box("TV", (1.1, 0.06, 0.65), (0, -1.25, 0.775))
    plant = cyl("Plant_Pot", 0.14, 0.3, (1.8, 0.6, 0.15))
    book = box("Book", (0.25, 0.18, 0.04), (-1.4, -0.5, 0.02))
    remote = box("Remote", (0.16, 0.06, 0.03), (0.3, -0.35, 0.03))
    sc["gt"] = json.dumps({
        "table_top_z": 0.45, "arm_top_z": 0.55, "stand_top_z": 0.45,
        "legs_rest_z": 0.015, "legs_rest_on": "Rug",
        "book_on_floor": True, "remote_on_rug": True,
        "pot_on_floor": True})
    _check("rug_top", _aabb(rug)[1].z, 0.015)
    _check("table_top", _aabb(ttop)[1].z, 0.45)
    for lg in legs:
        _check(f"{lg.name}_rest", _aabb(lg)[0].z, 0.015)
        _check(f"{lg.name}_under_top",
               _aabb(ttop)[0].z - _aabb(lg)[1].z, 0.0)
    _check("sofa_rest", _aabb(base)[0].z, 0.0)
    _check("back_on_base", _aabb(back)[0].z - _aabb(base)[1].z, 0.0)
    _check("armL_touches_base", _aabb(armL)[1].x + 0.7, 0.0)
    _check("armR_touches_base", 0.7 - _aabb(armR)[0].x, 0.0)
    _check("arm_top", _aabb(armL)[1].z, 0.55)
    _check("stand_top", _aabb(stand)[1].z, 0.45)
    _check("tv_on_stand", _aabb(tv)[0].z - _aabb(stand)[1].z, 0.0)
    _check("pot_rest", _aabb(plant)[0].z, 0.0)
    _check("book_rest", _aabb(book)[0].z, 0.0)
    _check("remote_rest", _aabb(remote)[0].z, 0.015)
    _assert_scene_clean()
    return sc


# ---------------------------------------------------------------------------
scenario = arg("--scenario", "kitchen_counter")
builders = {"kitchen_counter": build_kitchen_counter,
            "warehouse_cratestack": build_warehouse_cratestack,
            "living_room": build_living_room}
if scenario not in builders:
    raise RuntimeError(f"unknown scenario {scenario!r}; "
                       f"known: {list(builders)}")
sc = builders[scenario]()

out = arg("--output")
if out:
    d = os.path.dirname(out)
    if d:
        os.makedirs(d, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=out)
    print(f"[fixture] saved {out}")
print(f"[fixture] scenario={scenario} objects="
      f"{[o.name for o in sc.objects]}")
