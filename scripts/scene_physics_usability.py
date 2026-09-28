"""scene_physics_usability.py — fixture scenes for physics usability rounds.
Usage (inside Blender via blrun):
  --scenario gate_janitor   : hostile scene — floats, penetrations, a stack
  --scenario oracle_door    : driver blocked from a cabin by a closed door
  --scenario physics_place  : mug + shelf + books for placement tasks
  --output <path>           : save the .blend here (optional)
Each scenario is built with plain bpy + data-baked sizes (NEVER
transform_apply — gotcha #58) and carries planted ground truth in the
scene's custom properties (`gt` key) for the harness to verify.
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
    """Exact world AABB from data verts x matrix_world (bound_box is
    stale-prone in background mode)."""
    from mathutils import Vector
    pts = [obj.matrix_world @ Vector(v.co) for v in obj.data.vertices]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts),
                 min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts),
                 max(p.z for p in pts)))
    return mn, mx


def _check(tag, got, expect, tol=0.0015):
    """Fixture ground-truth discipline (round-B lesson, encoded): a
    fixture whose planted gt drifts from what it actually builds POISONS
    usability rounds — the subjects report honest tool outputs and we
    debug the wrong layer. Fail loudly at build time instead."""
    if abs(got - expect) > tol:
        raise RuntimeError(
            f"[fixture] GROUND-TRUTH MISMATCH {tag}: built {got:.4f}, "
            f"planted {expect:.4f} (tol {tol}) — fix the arithmetic, "
            f"never ship a lying fixture")


def fresh():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.gravity = (0, 0, -9.81)
    sc.unit_settings.system = 'METRIC'
    return sc


def build_gate_janitor():
    """Planted problems (ground truth in scene['gt']):
    - Lamp FLOATS 55mm above the desk
    - Mug PENETRATES the desk 12mm
    - BookStack: 3 books, bottom one FLOATS 30mm above the desk,
      the two above it rest on each other (stack is coherent)
    - Crate rests correctly on the floor (innocent)
    """
    sc = fresh()
    floor = box("Floor", (8, 8, 0.2), (0, 0, -0.1))
    desk = box("Desk", (2, 1, 0.5), (0, 0, 0.25))           # top 0.50
    # (round-B catch: the "desk" was a floating slab at z=0.42-0.50 with
    # nothing under it — the gate's verify notes were RIGHT; ground truth
    # discipline applies to fixtures too)
    lamp = box("Lamp", (0.18, 0.18, 0.45), (0.5, 0.2, 0.78))    # bot 0.555: float 55mm
    mug = box("Mug", (0.16, 0.16, 0.2), (-0.5, -0.2, 0.588))  # bot 0.488: 12mm pen
    b1 = box("Book1", (0.4, 0.3, 0.05), (-0.5, 0.25, 0.555))   # bot 0.53: float 30mm
    b2 = box("Book2", (0.36, 0.28, 0.04), (-0.49, 0.26, 0.60))  # bot 0.58: on b1
    b3 = box("Book3", (0.33, 0.26, 0.04), (-0.51, 0.24, 0.64))  # bot 0.62: on b2
    crate = box("Crate", (0.5, 0.5, 0.5), (1.5, 0, 0.25))      # on floor
    sc["gt"] = json.dumps({
        "lamp_float_mm": 55.0, "mug_pen_mm": 12.0,
        "book1_float_mm": 30.0, "books_on_each_other": True,
        "crate_ok": True})
    # self-verify the planted values against the built geometry
    dt = _aabb(desk)[1].z
    _check("desk_top", dt, 0.50)
    _check("lamp_float_mm", (_aabb(lamp)[0].z - dt) * 1000, 55.0)
    _check("mug_pen_mm", (dt - _aabb(mug)[0].z) * 1000, 12.0)
    _check("book1_float_mm", (_aabb(b1)[0].z - dt) * 1000, 30.0)
    _check("book2_on_book1", _aabb(b1)[1].z - _aabb(b2)[0].z, 0.0)
    _check("book3_on_book2", _aabb(b2)[1].z - _aabb(b3)[0].z, 0.0)
    _check("crate_rest", _aabb(crate)[0].z, 0.0)
    return sc


def build_oracle_door():
    """A cabin with a closed DOOR panel. The driver capsule stands beside
    the cabin; the task: get the driver INSIDE the cabin at seat height
    (bottom z = 0.5). The closed door + sill make that impossible to
    reach from outside; physics should name the obstruction."""
    sc = fresh()
    floor = box("Floor", (8, 8, 0.2), (0, 0, -0.1))
    # cabin: floor pan + roof + 3 walls (back/left/right), door side open
    pan = box("Cabin_Pan", (2, 1.2, 0.1), (0, 0, 0.35))        # top 0.40
    roof = box("Cabin_Roof", (2, 1.2, 0.08), (0, 0, 1.44))     # under 1.40
    back = box("Cabin_Back", (0.08, 1.2, 1.0), (-0.96, 0, 0.9))
    left = box("Cabin_Left", (2, 0.08, 1.0), (0, 0.56, 0.9))
    right = box("Cabin_Right", (2, 0.08, 1.0), (0, -0.56, 0.9))
    # the DOOR: closed panel filling the front opening (x=+0.96), seated
    # ON the sill (self-verify caught door/sill overlapping 50mm) and
    # reaching the roof so the entry is fully sealed (the old door left
    # a 150mm gap under the roof that a 600mm driver still cannot pass)
    door = box("Cabin_Door", (0.08, 0.7, 0.9), (0.96, 0, 0.95))
    # sill: raised strip under the door opening
    sill = box("Cabin_Sill", (0.08, 0.7, 0.1), (0.96, 0, 0.45))
    # wheels (round-E subject B: the cabin hovered 300mm with nothing
    # under it — the whole-scene gate HONESTLY rejected the fixture's
    # own floats; ground the car so the driver task is gate-reachable)
    for nm, wx, wy in (("Cabin_WheelFL", -0.85, 0.45),
                       ("Cabin_WheelFR", 0.85, 0.45),
                       ("Cabin_WheelRL", -0.85, -0.45),
                       ("Cabin_WheelRR", 0.85, -0.45)):
        box(nm, (0.12, 0.12, 0.3), (wx, wy, 0.15))     # top 0.30 = pan bottom
    driver = box("Driver", (0.3, 0.3, 0.6), (2.0, 0, 0.3))     # outside
    sc["gt"] = json.dumps({
        "seat_target_z": 0.5,
        "obstructions": ["Cabin_Door"],
        "door_closed": True,
        "car_grounded": True,
        "seat_support": "Cabin_Pan"})
    # self-verify: pan/roof/walls are grounded via wheels; the door seals
    # the entry plane
    _check("wheel_top_pan", _aabb(pan)[0].z - 0.30, 0.0)
    for w in ("Cabin_WheelFL", "Cabin_WheelFR",
              "Cabin_WheelRL", "Cabin_WheelRR"):
        _check(f"{w}_rest", _aabb(sc.objects[w])[0].z, 0.0)
    _check("door_seal_bottom", _aabb(door)[0].z - _aabb(sill)[1].z, 0.0)
    return sc


def build_physics_place():
    """Shelf unit + mug + 3 loose books. Tasks: put the mug ON the shelf,
    build a neat book stack on the desk, nothing floating/penetrating.
    Books/Mug rest loose on the floor NEXT TO the desk (round-E: they
    used to sit inside the desk slab's footprint — a solid 0.5m slab on
    the floor — so 'books on the floor' built as full-height desk
    penetrations)."""
    sc = fresh()
    floor = box("Floor", (8, 8, 0.2), (0, 0, -0.1))
    desk = box("Desk", (2, 1, 0.5), (0, 0, 0.25))             # top 0.50
    shelf = box("Shelf", (1.6, 0.4, 0.05), (0, 1.2, 0.945))   # top 0.97 (legs now reach it)
    leg1 = box("Shelf_LegL", (0.08, 0.4, 0.92), (-0.72, 1.2, 0.46))
    leg2 = box("Shelf_LegR", (0.08, 0.4, 0.92), (0.72, 1.2, 0.46))
    mug = cyl("Mug", 0.07, 0.18, (1.2, -0.5, 0.09))           # on floor
    book_a = box("BookA", (0.4, 0.3, 0.05), (-1.0, -0.75, 0.025))
    book_b = box("BookB", (0.34, 0.26, 0.04), (-0.2, -0.8, 0.02))
    book_c = box("BookC", (0.3, 0.24, 0.035), (0.6, -0.75, 0.0175))
    sc["gt"] = json.dumps({
        "shelf_top_z": 0.970, "desk_top_z": 0.50,
        "mug_on_floor": True, "books_on_floor": True,
        "books_clear_of_desk": True})
    # self-verify
    _check("shelf_top", _aabb(shelf)[1].z, 0.970)
    _check("desk_top", _aabb(desk)[1].z, 0.50)
    _check("leg_top_shelf", _aabb(shelf)[0].z - _aabb(leg1)[1].z, 0.0)
    for b in (book_a, book_b, book_c):
        _check(f"{b.name}_rest", _aabb(b)[0].z, 0.0)
        bm = _aabb(b)
        dm = _aabb(desk)
        xy_overlap = (bm[0].x < dm[1].x and bm[1].x > dm[0].x
                      and bm[0].y < dm[1].y and bm[1].y > dm[0].y)
        if xy_overlap:
            raise RuntimeError(
                f"[fixture] {b.name} overlaps the desk footprint — "
                f"'books on the floor' must not intersect the slab")
    return sc


scenario = arg("--scenario", "gate_janitor")
builders = {"gate_janitor": build_gate_janitor,
            "oracle_door": build_oracle_door,
            "physics_place": build_physics_place}
if scenario not in builders:
    raise RuntimeError(f"unknown scenario {scenario!r}; "
                       f"known: {list(builders)}")
sc = builders[scenario]()

out = arg("--output")
if out:
    d = os.path.dirname(out)
    if d:                      # bare relative filename must not crash
        os.makedirs(d, exist_ok=True)   # (round-E subjects A/B/C hit
    bpy.ops.wm.save_as_mainfile(filepath=out)   # makedirs('') here)
    print(f"[fixture] saved {out}")
print(f"[fixture] scenario={scenario} objects="
      f"{[o.name for o in sc.objects]}")
