"""tsquall_world.py -- SQUALL's set: the storm-dusk market plaza.

Self-contained bpy; materials via tdawn_actors.make_material (the
F-TD11 emission params: DARK base + saturated emission_color at the
pinned strength -- warm practicals own the arcade, cool strips own the
canopy). The set AGREES with the sim contract (docs/DESIGN_squall.md
REV-3): the M6 portal divider wall y=6 spanning x (-30,-5)|(5,30) with
the 10m doorway x (-5,5) COINCIDES with the entrance facade here; the
arrival box (+-5 around (0,0)) sits on the covered arcade floor; stall
barricades r=0.95 at (+-26, 1.5/3.5/5.5/7.5); fountain basin barricade
r=2.3 at (14, 7.5) with the ragdoll rim band 2.6-3.6m on the S/SW arc
kept clear of ground-level dress. NO rain, NO bystander, NO neon glyphs
in this module (rain layers / hero actor / title are scene-side); NO
water jet (spec).

Coordinate frame: ground z=0, meters; x east, y north. Plaza slab
x -34..34 / y -10..19 (3 tone-split slabs). Arcade footprint
x (-8,8), y (-6,6); roof z 4.0-4.3 on perimeter columns; entrance
facade y=6 with lintel over the doorway (10m wide x 3.6m high clear);
sign band x (-4.5,4.5), y (5.9,6.25), z 2.8-3.6 -- the TITLE CARRIER
(dark acrylic; the scene module ignites "SQUALL" at f1009). Food
window counter x (5.2,7.8) top z=1.1 with the warm serving panel
facing NORTH (the queue target; queue head slot (6.5,-4.6) clears it).
Stalls: 8 (west row faces EAST, east row faces WEST). North facades
y (15.5,17.5) -- BEYOND the walkable ceiling 15 (facade-swallow law).

Ladder protocol (tgreen convention): TSQ_SUN_STRENGTH / TSQ_SKY_STRENGTH
are module CONSTANTS so the scene module sweeps the storm-dusk ladder
by override BEFORE build_world:
    import tsquall_world; tsquall_world.TSQ_SUN_STRENGTH = 2.0

Deviations / ambiguity resolutions (recorded, the tgreen way):
1. THE PATTERN FILE HAS NO __main__ QA SECTION: tgreen_world.py is
   333 lines ending at build_world() -- no QA block, no kit-validator
   call, no smoke render. QA5's "run the kit validator IF tgreen's QA
   does" is therefore vacuously false as a GATE. Resolution: this
   module still ships a __main__ QA/smoke section (the task requires
   it) built from the repo's other QA idioms -- validate_scene.py's
   script_argv()/factory-purge pattern + scene_green_light.main()'s
   arg style -- and runs validate_scene.validate_scene() IN-PROCESS as
   an INFORMATIONAL scan (printed, not gating): world sets are
   dressing-dense and the AABB validator is interior-scoped -- proud
   panels, mounted signs and the water-disc-inside-the-ring all flag
   its floating/containment classes (tgreen's window/glyph plates
   would flag identically). P0/P1/P2 counts are printed for the record.
2. Column spacing: "corners + every ~5.3m along E/W edges" read
   literally from the south corner gives interior posts at y=-0.7 and
   y=4.6 (spacing 5.3/5.3) plus the y=6 corner -- a 1.4m end bay at
   the north corner. Kept (spec-literal).
3. Fountain z-pins disambiguated so solids never interpenetrate:
   "water disc at z=0.42" = disc CENTER (z 0.40-0.44, inside the ring);
   "ring cap at z=0.55" = cap BASE (z 0.55-0.63, sitting ON the ring
   0-0.55); the jet column (no z pin) bases on the cap top (z
   0.63-2.23). A center-read cap would shear 4cm into the ring.
4. Stall roof "at z~2.3": center z 2.26 with a 0.05rad tilt, posts
   0-2.2 -- keeps the sloped underside within the validator's 5cm
   support tolerance of the post tops (the roof is then SUPPORTED, not
   floating, and still reads z~2.3).
5. Sign band frame = 2 jambs + 1 head, ALL with z-min >= 2.80 so the
   QA2 lintel/band exemption stays honest (no frame geometry hangs
   below the exempt plane over the crowd path).
6. Crates are named TSQ.Crate.* (not TSQ.Stall.*) so QA3's
   stall-barricade disjointness actually TESTS them (they pass at
   1.39m from the nearest stall center; vendor spawn boxes are the
   1.2m squares at (+-24.9, y) per the design).
7. Budget trims to hold <200 objects: 5 bulbs/stall (spec 5-7),
   2 crates/stall (spec 2-3), 4 shutters/side (spec 4-6). Final count
   199 including the grounding plane + sun lamp.
8. Approach bollards ("3 more near the fountain approach, south
   side"): no coords given -- placed at (11.8,4.3)/(14.0,3.9)/(16.2,4.3)
   flanking the S approach, all z 0-0.9 (QA4 only bans z<0.1 dress in
   the rim band) and >=3.6m from the basin center.
9. NO SMOKE RENDER IN THIS MODULE (task 4-g): tgreen's QA shape is
   asserts+print only and the principal renders belong to the scene
   module -- the usual world-module smoke render is REPLACED by a
   print('[tsquall_world] smoke render skipped (principal renders)')
   so `--background --python scripts/tsquall_world.py` executes the
   QA block fast and exits 0 without touching a single pixel.
"""
from __future__ import annotations

import math
import sys

import bpy
from mathutils import Vector

from tdawn_actors import make_material

# --- the storm-dusk ladder (module CONSTANTS; the scene module
# sweeps by override BEFORE build_world -- the tgreen law) -----------
TSQ_SUN_STRENGTH = 1.0    # dusk sun, the practicals own the arcade
TSQ_SKY_STRENGTH = 0.35   # storm ambient base
TSQ_SUN_ELEV_DEG = 10.0   # low dusk light
TSQ_SUN_AZ_DEG = 300.0    # WNW bearing (storm front rolls from the W)

# --- set frame (meters; z=0 ground) ---------------------------------
PLAZA_X0, PLAZA_X1 = -34.0, 34.0
PLAZA_Y0, PLAZA_Y1 = -10.0, 19.0
ARCADE_X = 8.0            # arcade footprint x (-8,8)
ARCADE_Y = 6.0            # arcade footprint y (-6,6)
DOOR_X = 5.0              # the 10m doorway x (-5,5)
FOUNTAIN_C = (14.0, 7.5)
FOUNTAIN_RING_R = 2.2
STALL_XS = (-26.0, 26.0)
STALL_YS = (1.5, 3.5, 5.5, 7.5)
SLIP_F, SLIP_R0, SLIP_R1 = FOUNTAIN_C, 2.6, 3.6   # the rim band
SLIP_ARC_DEG = (150.0, 285.0)   # S/SW arc: bearing 0=N,90=E,180=S,270=W
DOORWAY_REGION = ((-5.0, 5.0), (5.7, 6.3), (0.0, 3.5))  # the crowd path

# puddles: (name, x, y, r) -- 10 (spec 10-12): 3 clustered near the
# fountain (E/NE/NW arcs, >=1.0m clear of the ring r2.2), 2 at the
# doorway mouth, 5 scattered avoiding the arcade footprint
PUDDLES = (
    ("Cluster.1", 18.6, 6.9, 1.10),
    ("Cluster.2", 17.6, 10.6, 1.00),
    ("Cluster.3", 10.6, 10.9, 1.20),
    ("Door.1", -3.2, 7.7, 0.85),
    ("Door.2", 3.0, 8.1, 1.00),
    ("Scatter.1", -18.0, -3.0, 1.50),
    ("Scatter.2", 20.0, -4.0, 1.60),
    ("Scatter.3", -3.0, 12.0, 0.90),
    ("Scatter.4", 6.0, 13.0, 1.40),
    ("Scatter.5", -20.0, 12.0, 1.10),
)


def _box(name, sx, sy, sz, loc, mat):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    ob = bpy.context.active_object
    ob.name = name
    ob.scale = (sx, sy, sz)
    if mat is not None:
        ob.data.materials.append(mat)
    return ob


def _prim(kind, size, loc, rot=(0.0, 0.0, 0.0), verts=16, mat=None,
          name=None):
    # NOTE vs tferry (the tgreen clone): per-kind kwargs (uv_sphere
    # takes segments/ring_count, NOT vertices) and a name arg -- the
    # TSQ.<Something> naming law means every created object is
    # explicitly named here.
    fn = {"cyl": bpy.ops.mesh.primitive_cylinder_add,
          "sph": bpy.ops.mesh.primitive_uv_sphere_add,
          "cone": bpy.ops.mesh.primitive_cone_add}[kind]
    kw = {"location": loc, "rotation": rot}
    if kind == "cyl":
        kw.update(radius=size[0] / 2, depth=size[1], vertices=verts)
    elif kind == "cone":
        kw.update(radius1=size[0] / 2, depth=size[1], vertices=verts)
    else:
        kw.update(radius=size[0] / 2, segments=verts,
                  ring_count=max(8, verts // 2))
    fn(**kw)
    ob = bpy.context.active_object
    if name:
        ob.name = name
    if mat is not None:
        ob.data.materials.append(mat)
    return ob


def _bounds(ob):
    """World-space AABB (min, max) -- the validate_scene idiom."""
    corners = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    mn = [min(c[i] for c in corners) for i in range(3)]
    mx = [max(c[i] for c in corners) for i in range(3)]
    return mn, mx


def _build_materials():
    """The storm-dusk palette (albedo, linear) + the F-TD11 practicals."""
    m = {}
    # the wet plaza (near-black, low rough -- the storm-dusk floor)
    m["concrete_a"] = make_material("TSQ.ConcreteA", (0.024, 0.024, 0.027),
                                    0.18)
    m["concrete_b"] = make_material("TSQ.ConcreteB", (0.028, 0.028, 0.031),
                                    0.20)
    m["concrete_c"] = make_material("TSQ.ConcreteC", (0.026, 0.026, 0.028),
                                    0.18)
    m["puddle"] = make_material("TSQ.Puddle", (0.018, 0.022, 0.032), 0.04)
    m["ground"] = make_material("TSQ.Ground", (0.05, 0.05, 0.052), 0.95)
    # the arcade shell
    m["roof"] = make_material("TSQ.RoofDark", (0.030, 0.030, 0.034), 0.7)
    m["column"] = make_material("TSQ.Column", (0.050, 0.050, 0.055), 0.6)
    m["wall"] = make_material("TSQ.WallDark", (0.040, 0.040, 0.046), 0.7)
    m["lintel"] = make_material("TSQ.Lintel", (0.060, 0.060, 0.066), 0.6)
    m["band"] = make_material("TSQ.SignBand", (0.015, 0.015, 0.020), 0.35)
    m["band_frame"] = make_material("TSQ.BandFrame", (0.25, 0.26, 0.28),
                                    0.4, metallic=0.6)
    # the shuttered shopfronts (muted, 4 tones cycling)
    m["shutter_a"] = make_material("TSQ.ShutterA", (0.10, 0.060, 0.050), 0.6)
    m["shutter_b"] = make_material("TSQ.ShutterB", (0.060, 0.080, 0.060), 0.6)
    m["shutter_c"] = make_material("TSQ.ShutterC", (0.120, 0.090, 0.040), 0.6)
    m["shutter_d"] = make_material("TSQ.ShutterD", (0.050, 0.060, 0.090), 0.6)
    # the food window (the queue target -- the warm glow)
    m["counter"] = make_material("TSQ.CounterWood", (0.090, 0.060, 0.040), 0.5)
    m["serving"] = make_material(
        "TSQ.ServingPanel", (0.050, 0.030, 0.020), 0.5,
        emission_color=(1.0, 0.55, 0.22), emission_strength=4.0)
    m["menu"] = make_material("TSQ.MenuBoard", (0.030, 0.030, 0.030), 0.5)
    # the canopy strips (cool fluorescent)
    m["strip"] = make_material(
        "TSQ.StripLight", (0.060, 0.070, 0.080), 0.4,
        emission_color=(0.75, 0.85, 1.0), emission_strength=3.5)
    # the stalls
    m["canvas_a"] = make_material("TSQ.CanvasRed", (0.28, 0.060, 0.050), 0.8)
    m["canvas_b"] = make_material("TSQ.CanvasRust", (0.30, 0.120, 0.050), 0.8)
    m["canvas_c"] = make_material("TSQ.CanvasOchre", (0.34, 0.200, 0.060), 0.8)
    m["bulb"] = make_material(
        "TSQ.Bulb", (0.050, 0.035, 0.020), 0.4,
        emission_color=(1.0, 0.62, 0.34), emission_strength=5.0)  # ~2800K
    m["crate_a"] = make_material("TSQ.CrateWoodA", (0.16, 0.110, 0.060), 0.7)
    m["crate_b"] = make_material("TSQ.CrateWoodB", (0.12, 0.080, 0.050), 0.7)
    # the fountain
    m["stone"] = make_material("TSQ.Stone", (0.16, 0.16, 0.15), 0.6)
    m["water"] = make_material("TSQ.Water", (0.010, 0.012, 0.016), 0.08)
    # the north facades + sparse warm windows
    m["building"] = make_material("TSQ.Building", (0.035, 0.035, 0.040), 0.8)
    m["winwarm"] = make_material(
        "TSQ.WinWarm", (0.040, 0.030, 0.020), 0.4,
        emission_color=(1.0, 0.60, 0.30), emission_strength=2.5)
    # the dressing
    m["bollard"] = make_material("TSQ.Bollard", (0.10, 0.10, 0.11), 0.5)
    m["bench"] = make_material("TSQ.Bench", (0.10, 0.080, 0.060), 0.6)
    m["planter"] = make_material("TSQ.Planter", (0.060, 0.050, 0.045), 0.7)
    m["foliage"] = make_material("TSQ.Foliage", (0.020, 0.045, 0.020), 0.9)
    m["trash"] = make_material("TSQ.Trash", (0.080, 0.090, 0.10), 0.5)
    return m


def _stall(scene_tag, sx, sy, idx, mats):
    """One market stall: counter + 4 posts + canvas roof + bulb string.

    The front faces the plaza center: west row (sx=-26) faces EAST,
    east row (sx=+26) faces WEST. Bulbs hang on a slight catenary
    under the roof FRONT edge."""
    front = 1.0 if sx < 0 else -1.0          # west -> +x (east)
    tilt = 0.05 * front                       # front edge dips
    px = sx + front * 1.10                    # crates flank the front
    # counter 1.6(N-S) x 0.7(E-W) x 0.95 -- the long face is the front
    _box(f"TSQ.Stall.{scene_tag}.Counter", 0.7, 1.6, 0.95,
         (sx, sy, 0.475), mats["counter"])
    for pi, (dx, dy) in enumerate(((-0.8, -0.8), (0.8, -0.8),
                                   (-0.8, 0.8), (0.8, 0.8))):
        _prim("cyl", (0.10, 2.2), (sx + dx, sy + dy, 1.1), verts=10,
              mat=mats["column"], name=f"TSQ.Stall.{scene_tag}.Post.{pi + 1}")
    roof = _box(f"TSQ.Stall.{scene_tag}.Roof", 2.2, 1.8, 0.06,
                (sx, sy, 2.26), mats["canvas_a" if idx % 3 == 0 else
                                    "canvas_b" if idx % 3 == 1 else
                                    "canvas_c"])
    roof.rotation_euler = (0.0, tilt, 0.0)
    # 5 bulbs on the catenary under the front edge (x = front rim)
    bx = sx + front * 0.98
    for bi in range(5):
        t = bi / 4.0
        bz = 2.08 - 0.13 * (1.0 - (2.0 * t - 1.0) ** 2)
        _prim("sph", (0.10,), (bx, sy - 0.75 + 1.5 * t, bz), verts=12,
              mat=mats["bulb"], name=f"TSQ.Stall.{scene_tag}.Bulb.{bi + 1}")
    # 2 crates beside the counter (named OUTSIDE TSQ.Stall.* so QA3
    # actually tests them against the vendor spawn boxes)
    big, small = (0.65, 0.55) if idx % 2 == 0 else (0.55, 0.65)
    _box(f"TSQ.Crate.{scene_tag}.1", big, big, big,
         (px, sy - 1.15, big / 2), mats["crate_a"])
    _box(f"TSQ.Crate.{scene_tag}.2", small, small, small,
         (px, sy + 1.15, small / 2), mats["crate_b"])


def build_world(scene):
    """Build the storm-dusk plaza; returns the parts dict."""
    mats = _build_materials()
    pre = set(scene.objects.keys())

    # --- the wet plaza slab (top z=0), 3 subtly-different tone bands --
    _box("TSQ.Slab.S", PLAZA_X1 - PLAZA_X0, -0.5 - PLAZA_Y0, 0.1,
         (0.0, (PLAZA_Y0 + -0.5) / 2, -0.05), mats["concrete_a"])
    _box("TSQ.Slab.M", PLAZA_X1 - PLAZA_X0, 9.5 - -0.5, 0.1,
         (0.0, (9.5 + -0.5) / 2, -0.05), mats["concrete_b"])
    _box("TSQ.Slab.N", PLAZA_X1 - PLAZA_X0, PLAZA_Y1 - 9.5, 0.1,
         (0.0, (PLAZA_Y1 + 9.5) / 2, -0.05), mats["concrete_c"])
    # the grounding plane UNDER everything (the tgreen ocean-horizon fix)
    _box("TSQ.GroundPlane", 500.0, 500.0, 0.02, (0.0, 0.0, -0.13),
         mats["ground"])

    # --- the puddle mirrors (flat discs, roughness 0.04) ---------------
    for tag, px, py, pr in PUDDLES:
        _prim("cyl", (2 * pr, 0.01), (px, py, 0.005), verts=24,
              mat=mats["puddle"], name=f"TSQ.Puddle.{tag}")

    # --- THE ARCADE (hero structure) -----------------------------------
    # roof slab z 4.0-4.3, overhanging the footprint by 0.4
    _box("TSQ.Arcade.Roof", 2 * ARCADE_X + 0.8, 2 * ARCADE_Y + 0.8,
         0.3, (0.0, 0.0, 4.15), mats["roof"])
    # perimeter columns r=0.22: 4 corners + interiors every 5.3m along
    # the E/W edges read from the south corner (y -0.7, 4.6; deviation 2)
    for tag, cx, cy in (("Corner.SE", ARCADE_X, -ARCADE_Y),
                        ("Corner.NE", ARCADE_X, ARCADE_Y),
                        ("Corner.SW", -ARCADE_X, -ARCADE_Y),
                        ("Corner.NW", -ARCADE_X, ARCADE_Y),
                        ("E.1", ARCADE_X, -0.7), ("E.2", ARCADE_X, 4.6),
                        ("W.1", -ARCADE_X, -0.7), ("W.2", -ARCADE_X, 4.6)):
        _prim("cyl", (0.44, 4.0), (cx, cy, 2.0), verts=14,
              mat=mats["column"], name=f"TSQ.Arcade.Column.{tag}")
    # entrance facade at y=6: wall segments beside the 10m doorway
    # (COINCIDES with the sim's M6 divider wall)
    for tag, cx in (("W", -(ARCADE_X + DOOR_X) / 2),
                    ("E", (ARCADE_X + DOOR_X) / 2)):
        _box(f"TSQ.Arcade.FacadeSeg.{tag}", ARCADE_X - DOOR_X, 0.3, 4.0,
             (cx, ARCADE_Y, 2.0), mats["wall"])
    # lintel over the doorway: 10m wide x 3.6m high clear opening
    _box("TSQ.Arcade.Lintel", 2 * DOOR_X, 0.3, 0.4,
         (0.0, ARCADE_Y, 3.8), mats["lintel"])
    # low shopfront walls beyond the arcade (x +-8..+-30, h 3.0)
    for tag, cx in (("W", -(ARCADE_X + 30.0) / 2),
                    ("E", (ARCADE_X + 30.0) / 2)):
        _box(f"TSQ.Arcade.Shopfront.{tag}", 30.0 - ARCADE_X, 0.3, 3.0,
             (cx, ARCADE_Y, 1.5), mats["wall"])
    # shutter panels, slightly proud of the north faces, muted cycle
    shutters = ("shutter_a", "shutter_b", "shutter_c", "shutter_d")
    for si, sx in enumerate((-27.5, -23.5, -19.5, -15.5)):
        _box(f"TSQ.Arcade.Shutter.W{si + 1}", 3.2, 0.12, 2.4,
             (sx, ARCADE_Y + 0.21, 1.35), mats[shutters[si % 4]])
    for si, sx in enumerate((11.5, 15.5, 19.5, 23.5)):
        _box(f"TSQ.Arcade.Shutter.E{si + 1}", 3.2, 0.12, 2.4,
             (sx, ARCADE_Y + 0.21, 1.35), mats[shutters[si % 4]])
    # back wall (south y=-6) + THE FOOD WINDOW (queue target)
    _box("TSQ.Arcade.BackWall", 2 * ARCADE_X, 0.3, 4.0,
         (0.0, -ARCADE_Y, 2.0), mats["wall"])
    _box("TSQ.Arcade.FoodCounter", 2.6, 0.4, 1.1,
         (6.5, -ARCADE_Y + 0.35, 0.55), mats["counter"])  # top z 1.1
    _box("TSQ.Arcade.ServingPanel", 2.6, 0.06, 1.3,
         (6.5, -ARCADE_Y + 0.15, 1.75), mats["serving"])  # z 1.1-2.4 N
    _box("TSQ.Arcade.MenuBoard", 2.6, 0.08, 0.6,
         (6.5, -ARCADE_Y + 0.15, 2.9), mats["menu"])      # z 2.6-3.2
    # canopy strip lights: 4 cool fixtures under the roof at z=3.9
    for si, sx in enumerate((-6.0, -2.0, 2.0, 6.0)):
        _box(f"TSQ.Arcade.Strip.{si + 1}", 0.1, 2.4, 0.06,
             (sx, 0.0, 3.9), mats["strip"])
    # SIGN BAND (the title carrier): dark acrylic protruding BOTH sides
    # of the facade line y=6 (x -4.5..4.5, y 5.9..6.25, z 2.8..3.6)
    _box("TSQ.Arcade.SignBand", 9.0, 0.35, 0.8,
         (0.0, ARCADE_Y + 0.075, 3.2), mats["band"])
    # thin metal frame: 2 jambs + 1 head, ALL z >= 2.80 (deviation 5)
    for tag, loc, size in (("Frame.L", (-4.53, ARCADE_Y + 0.075, 3.2),
                            (0.06, 0.43, 0.80)),
                           ("Frame.R", (4.53, ARCADE_Y + 0.075, 3.2),
                            (0.06, 0.43, 0.80)),
                           ("Frame.T", (0.0, ARCADE_Y + 0.075, 3.57),
                            (9.12, 0.43, 0.06))):
        _box(f"TSQ.Arcade.SignBand.{tag}", *size, loc,
             mats["band_frame"])
    # NOTE: arcade floor stays z=0 -- no plinth (spec).

    # --- THE 8 STALLS ---------------------------------------------------
    idx = 0
    for row, sx in (("W", STALL_XS[0]), ("E", STALL_XS[1])):
        for si, sy in enumerate(STALL_YS, start=1):
            idx += 1
            _stall(f"{row}{si}", sx, sy, idx, mats)

    # --- THE FOUNTAIN (14, 7.5) -- no water jet (spec) ------------------
    fx, fy = FOUNTAIN_C
    _prim("cyl", (2 * FOUNTAIN_RING_R, 0.55), (fx, fy, 0.275), verts=28,
          mat=mats["stone"], name="TSQ.Fountain.Ring")
    _prim("cyl", (3.8, 0.04), (fx, fy, 0.42), verts=28,
          mat=mats["water"], name="TSQ.Fountain.Water")   # center 0.42
    _prim("cyl", (2 * FOUNTAIN_RING_R, 0.08), (fx, fy, 0.59), verts=28,
          mat=mats["stone"], name="TSQ.Fountain.Cap")     # base 0.55
    _prim("cyl", (0.5, 1.6), (fx, fy, 1.43), verts=16,
          mat=mats["stone"], name="TSQ.Fountain.Column")  # base 0.63

    # --- NORTH FACADES (beyond the walkable ceiling 15) ----------------
    blocks = ((-30.0, -21.5, 4.2), (-21.5, -13.0, 5.1), (-13.0, -4.5, 3.8),
              (-4.5, 4.5, 5.5), (4.5, 13.5, 4.6), (13.5, 30.0, 4.4))
    for bi, (bx0, bx1, bh) in enumerate(blocks):
        _box(f"TSQ.North.Block.{bi + 1}", bx1 - bx0, 2.0, bh,
             ((bx0 + bx1) / 2, 16.5, bh / 2), mats["building"])
    # 9 sparse warm windows, proud of the south faces (y 15.5)
    wins = ((-27.0, 2.2), (-23.5, 3.0), (-18.0, 2.6), (-10.0, 2.0),
            (-6.5, 2.8), (1.5, 3.2), (8.5, 2.4), (18.0, 2.2), (24.0, 3.0))
    for wi, (wx, wz) in enumerate(wins):
        _box(f"TSQ.North.Win.{wi + 1}", 0.5, 0.06, 0.7,
             (wx, 15.47, wz), mats["winwarm"])

    # --- DRESSING -------------------------------------------------------
    # 5 bollards across the doorway mouth line (x -4..4 at y 7.5)
    for bi, bx in enumerate((-4.0, -2.0, 0.0, 2.0, 4.0)):
        _prim("cyl", (0.24, 0.9), (bx, 7.5, 0.45), verts=12,
              mat=mats["bollard"], name=f"TSQ.Bollard.Gate.{bi + 1}")
    # 3 more flanking the fountain approach (south side; deviation 8;
    # the 4-i P1-6: pulled to d>=4.2 from the basin -- the old middle
    # bollard reached r 3.48m INSIDE the declared-clear rim band where
    # the ragdoll slides)
    for bi, (bx, by) in enumerate(((11.0, 3.2), (14.0, 2.9), (17.0, 3.2))):
        _prim("cyl", (0.24, 0.9), (bx, by, 0.45), verts=12,
              mat=mats["bollard"], name=f"TSQ.Bollard.Fountain.{bi + 1}")
    # 3 slat benches against the facade north side (x -14..-10, 12..16)
    bench_x = ((-13.2, "W1"), (-10.8, "W2"), (14.0, "E1"))
    for bx, tag in bench_x:
        _box(f"TSQ.Bench.{tag}.Seat", 1.8, 0.5, 0.07,
             (bx, 6.67, 0.415), mats["bench"])            # top z 0.45
        for li, lx in ((1, -0.78), (2, 0.78)):
            _box(f"TSQ.Bench.{tag}.Leg.{li}", 0.08, 0.5, 0.38,
                 (bx + lx, 6.67, 0.19), mats["bench"])
    # 4 planter boxes (0.8^3) with dark green masses at the corners
    for pi, (px, py) in enumerate(((-9.6, 7.6), (9.6, 7.6),
                                   (-9.6, -7.6), (9.6, -7.6))):
        _box(f"TSQ.Planter.{pi + 1}", 0.8, 0.8, 0.8,
             (px, py, 0.4), mats["planter"])
        _box(f"TSQ.Planter.{pi + 1}.Green", 0.66, 0.66, 0.46,
             (px, py, 1.03), mats["foliage"])
    # 2 small trash cylinders near the stall rows
    for ti, tx in enumerate((-24.4, 24.4)):
        _prim("cyl", (0.5, 0.7), (tx, 9.5, 0.35), verts=14,
              mat=mats["trash"], name=f"TSQ.Trash.{ti + 1}")

    # --- the storm-dusk SUN (direction-only lamp; the tgreen idiom) ----
    ld = bpy.data.lights.new("TSQ.Sun", type='SUN')
    ld.energy = TSQ_SUN_STRENGTH * 1.0
    ld.angle = math.radians(2.0)          # haze-softened dusk shadow edges
    ld.color = (0.70, 0.78, 0.95)
    sun_ob = bpy.data.objects.new("TSQ.Sun", ld)
    sun_ob.location = (-18.0, -12.0, 14.0)   # label-only (direction-only)
    scene.collection.objects.link(sun_ob)
    elev = math.radians(TSQ_SUN_ELEV_DEG)
    az = math.radians(TSQ_SUN_AZ_DEG)
    to_sun = Vector((math.sin(az) * math.cos(elev),
                     math.cos(az) * math.cos(elev),
                     math.sin(elev)))
    sun_ob.rotation_euler = (-to_sun).to_track_quat('-Z', 'Y').to_euler()

    # --- the storm sky (kit helper; strength is the ladder constant) ---
    # s27 BOTH-ENGINE DELTA (the tferry_world pattern; corpus A/B
    # receipt in worklog s27): the certified bright-storm-sky (EEVEE
    # 0.35) reads dark charcoal under Cycles at the same strength —
    # Cycles x3.0 restores the certified near-white storm sky through
    # the shelter openings. EEVEE untouched (byte-repro revs).
    from blender_kit import add_sky_world, normalize_engine_id
    _cyc = normalize_engine_id(
        scene.render.engine).startswith("CYCLES")
    _sky = TSQ_SKY_STRENGTH * (3.0 if _cyc else 1.0)
    add_sky_world(sun_elevation_deg=TSQ_SUN_ELEV_DEG,
                  sun_rotation_deg=TSQ_SUN_AZ_DEG,
                  strength=_sky)
    if scene.world and scene.world.use_nodes:
        for n in scene.world.node_tree.nodes:
            if n.type == 'TEX_SKY' and hasattr(n, 'sun_disc'):
                n.sun_disc = False
                print(f"[tsquall_world] sky sun_disc -> off "
                      f"({n.sky_type})")

    bpy.context.view_layer.update()
    created = [ob for ob in scene.objects if ob.name not in pre]
    return {"parts": created, "sun": sun_ob, "mats": mats,
            "puddles": len(PUDDLES)}


# ======================================================================
# __main__ QA section (NON-VISUAL: asserts + prints, zero renders)
# (the pattern file tgreen_world.py ships NO __main__ section -- see
# docstring deviation 1: the asserts below follow the repo's other QA
# idioms; the kit validator runs INFORMATIONALLY, not as a gate)
# ======================================================================

def _ok(tag, cond, detail):
    print(f"[tsquall-qa] {'PASS' if cond else 'FAIL'} {tag}: {detail}")
    return 0 if cond else 1


def _qa(ctx):
    scene = bpy.context.scene
    parts = ctx["parts"]
    fails = 0

    # --- QA0: the object budget ----------------------------------------
    fails += _ok("budget", len(parts) < 200,
                 f"{len(parts)} parts (<200)")

    # --- QA1: object counts per group ----------------------------------
    groups = (("ground+puddles", ("TSQ.Slab", "TSQ.Puddle",
                                  "TSQ.GroundPlane")),
              ("arcade", ("TSQ.Arcade",)),
              ("stall parts", ("TSQ.Stall",)),
              ("stall crates", ("TSQ.Crate",)),
              ("fountain", ("TSQ.Fountain",)),
              ("north facades", ("TSQ.North",)),
              ("dressing", ("TSQ.Bollard", "TSQ.Bench", "TSQ.Planter",
                            "TSQ.Trash")))
    names = [ob.name for ob in parts]
    counts = {g: sum(n.startswith(p) for n in names for p in ps)
              for g, ps in groups}
    for g, c in counts.items():
        print(f"[tsquall-qa]   count {g}: {c}")
    n_stalls = sum(1 for n in names if n.endswith(".Counter")
                   and n.startswith("TSQ.Stall."))
    fails += _ok("stalls", n_stalls == 8, f"{n_stalls} stalls == 8")
    fails += _ok("puddles", 10 <= ctx["puddles"] <= 12,
                 f"{ctx['puddles']} puddles (spec 10-12)")
    fails += _ok("fountain parts", counts["fountain"] == 4,
                 f"{counts['fountain']} parts == 4")
    fails += _ok("groups populated",
                 all(c > 0 for c in counts.values()),
                 "all 7 groups non-empty")

    meshes = {ob.name: ob for ob in scene.objects if ob.type == 'MESH'}
    bnds = {n: _bounds(ob) for n, ob in meshes.items()}

    # --- QA2: the doorway crowd path must be clear below z 3.5 ---------
    (rx0, rx1), (ry0, ry1), (rz0, rz1) = DOORWAY_REGION
    viol, exempt = [], []
    for n, (mn, mx) in bnds.items():
        if not (mn[0] < rx1 and mx[0] > rx0 and
                mn[1] < ry1 and mx[1] > ry0 and
                mn[2] < rz1 and mx[2] > rz0):
            continue
        nl = n.lower()
        # float32 note: Blender's matrix_world is SINGLE-precision -- the
        # band's world min-z reads 2.79999995 (float32(2.8)), 4.8e-8
        # below the double literal, so the z>=2.8 exemption carries a
        # 1e-4 tolerance (representation noise, not real geometry).
        if ("lintel" in nl or "band" in nl) and mn[2] >= 2.8 - 1e-4:
            exempt.append(n)
        else:
            viol.append(n)
    fails += _ok("doorway clear", not viol,
                 f"{len(viol)} viol {sorted(viol)} / {len(exempt)} exempt "
                 f"(lintel/band z>=2.8: {sorted(exempt)})")

    # --- QA3: stall-barricade disjointness (vendor spawn boxes) --------
    centers = [(sx, sy) for sx in STALL_XS for sy in STALL_YS]
    mind, min_n = None, None
    for ob in scene.objects:
        if ob.name.startswith("TSQ.Stall."):
            continue                       # structural stall parts only
        ox, oy = ob.matrix_world.translation.x, \
            ob.matrix_world.translation.y
        d = min(math.hypot(ox - cx, oy - cy) for cx, cy in centers)
        if mind is None or d < mind:
            mind, min_n = d, ob.name
    fails += _ok("stall spawn clear", mind > 1.3,
                 f"min {mind:.2f}m > 1.3m (nearest '{min_n}')")

    # --- QA4: the fountain slip zone (ragdoll pavement) ----------------
    fx, fy = SLIP_F
    scanned, bad = 0, []
    for ob in scene.objects:
        # the 4-i P1-6: the ORIGIN z misses tall dress (bollard origin
        # 0.45); the BBOX MIN-z is the honest ground-presence test
        import mathutils
        bb = [ob.matrix_world @ mathutils.Vector(c) for c in ob.bound_box]
        oz = min(v.z for v in bb)
        if oz >= 0.1:
            continue                       # only ground-reaching dress
        ox = ob.matrix_world.translation.x
        oy = ob.matrix_world.translation.y
        d = math.hypot(ox - fx, oy - fy)
        if not (SLIP_R0 <= d <= SLIP_R1 + 0.4):
            continue
        scanned += 1
        bearing = math.degrees(math.atan2(ox - fx, oy - fy)) % 360.0
        if SLIP_ARC_DEG[0] <= bearing <= SLIP_ARC_DEG[1]:
            bad.append(f"{ob.name}@{d:.2f}m/{bearing:.0f}deg")
    fails += _ok("fountain rim clear", not bad,
                 f"{len(bad)} viol / {scanned} ground-level objects "
                 f"scanned in the annulus neighbourhood")

    # --- QA5: the kit validator (INFORMATIONAL -- deviation 1) ---------
    try:
        import validate_scene as V
        rep = V.validate_scene(ground_z=0.0)
        sev = rep["issues_by_severity"]
        print(f"[tsquall-qa]   validator (NOT a gate; world sets are "
              f"dressing-dense, the AABB classes flag proud panels / "
              f"mounted signs / water-in-ring by design): "
              f"P0={sev['P0']} P1={sev['P1']} P2={sev['P2']} "
              f"meshes={rep['mesh_objects_checked']}")
        for issue in rep["issues"][:6]:
            obj = issue.get("object",
                            " & ".join(issue.get("objects", [])))
            print(f"[tsquall-qa]     [{issue['severity']}] "
                  f"{issue['type']}: {obj}")
        fails += _ok("validator scan sanity",
                     rep["mesh_objects_checked"] >= 150,
                     f"{rep['mesh_objects_checked']} meshes scanned")
    except Exception as exc:               # noqa: BLE001 -- QA harness
        fails += _ok("validator scan sanity", False, f"raise: {exc}")

    print(f"[tsquall-qa] SUMMARY: "
          f"{'ALL PASS' if fails == 0 else f'{fails} FAIL(S)'} "
          f"(budget {len(parts)}, stalls {n_stalls}, puddles "
          f"{ctx['puddles']})")
    return fails


def main():
    from blender_kit import clear_scene, script_argv
    import argparse
    p = argparse.ArgumentParser(
        description="SQUALL world module: build + non-visual QA "
                    "(NO render -- the principal renders are scene-side)")
    p.parse_args(script_argv())

    clear_scene()                    # the factory-startup purge (kit law)
    scene = bpy.context.scene
    ctx = build_world(scene)
    fails = _qa(ctx)
    print("[tsquall_world] smoke render skipped (principal renders)")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
