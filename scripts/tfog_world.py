"""tfog_world.py -- THE EXPRESS's set: the blue-hour fog island platform.

Self-contained bpy; materials via tdawn_actors.make_material (arg3 =
roughness; F-TD11 glow-surface law: DARK base + saturated
emission_color, every keyed slot shipped at strength 0.0 -- OFF, the
scene module keys the flips). The set AGREES with the sim contract
(docs/DESIGN_express.md §5, z INVERTED): island platform slab top z=0,
64x8 m (x -32..32, y -4..4), face walls down to z=-0.9; track beds
z=-0.9 N (y -13..-4, rails centered y=-8.5) and S (y 4..13, y=+8.5),
gauge +-0.72; canopy roof z=3.4 on 6 columns over the platform ONLY
(no roof over the track faces -- the aerial law); 6 sodium lamp posts;
double-sided departure board at x=0, center z=2.6, 4 glyph rows per
face; benches x4, bins x2, kiosk at (26,-2); signal gantry x=-34 over
the N track (red/green aspects); express = 8-car dark wedge parented
to the EMPTY express_root at (-120, -8.5, -0.9); local = 3-car warm on
local_root at (-90, 8.5, -0.9) -- the scene module keys the slides.
ONE fog volume: fog_box 64x10x6 over the platform (z 0..6), Volume
Scatter density TFOG_FOG_DENSITY=0.05 (the 192 m box is KILLED -- the
audit P1 fold). NO sky, NO sun, NO camera, NO bystanders (the scene
module owns the light ladder + cameras).

Coordinate frame: platform top z=0, world floor (track beds + grounding
plane top) z=-0.9; x east; N track/face is y<0, S face y>0 (spec
convention; every _n/_s name follows it). Internal object names are
ALL LOWERCASE (this film's naming law).

Deviations / ambiguity resolutions (the tgreen ledger way):
1. "Face walls down to z=-0.9": the slab is ONE solid 64x8x0.9 box --
   its N/S sides ARE the face walls (a skin would duplicate faces).
2. Sleepers via the CHEAP path: linked-duplicate cross bars (2 unique
   mesh datablocks, 52 zero-cost copies @2.5 m pitch) over a wave-
   texture plane -- zero shader-node version risk (4.x/5.x Mix churn).
   Stack: ballast top -0.74, sleepers -0.74..-0.69, rails -0.69..-0.55;
   car bottoms land ON the rail tops (z=-0.55).
3. Board support: panel top z=3.25 EXACTLY meets the roof underside
   (3.25) -- hung, not floating (no-floaters law), no silly 5 cm rods.
4. Canopy strip panels x=-27,-21,-9,-3,3,9,21,27 (8): the naive even
   grid put panels INSIDE columns at x=+-5; shifted clear.
5. Aspect discs hang on stems off the gantry beam underside (beam
   center z=4.5, discs z=3.95) -- mounted, not floating.
6. Trains parked per the pinned roots (express spans x -128..+7 at
   the park: the HEAD -- the leading E end -- is the ON-STAGE end,
   over the platform's E half; the tail is far offstage W. The scene
   keys the slides. s19-B11: the old "-128..15 / tail brushes the
   platform W end" note had the span end AND the head/tail roles
   wrong).
7. Ladder: TFOG_* are module CONSTANTS (density + 5 keyed OFF
   strengths); the scene module overrides BEFORE build_world, the
   tgreen/tsquall way. Lamp POINT lights ship energy 0.
8. NO render here (task: textual asserts only); --dry-run is an
   accepted no-op (this module never renders anything).
"""
from __future__ import annotations

import argparse
import math
import sys

import bpy

from tdawn_actors import make_material

# --- the fog ladder (module CONSTANTS; the scene module sweeps by
# override BEFORE build_world -- the tgreen/tsquall law) --------------
TFOG_FOG_DENSITY = 0.028   # Volume Scatter density in fog_box
                           # (session-19 stills gate: 0.05 swallowed the S5
                           # blast wide at 15 m — the beat died in haze;
                           # 0.028 keeps the pools + reads the crowd)
                           # s27 BOTH-ENGINE DELTA (the tferry pattern;
                           # corpus A/B in worklog s27): Cycles renders
                           # the volume thinner than the EEVEE corpus —
                           # the Cycles lane serves 0.040 (see
                           # fog_density_for_engine below; the 0.05
                           # swallow guard: the S5 blast window is
                           # re-checked by eye on the Cycles probe).
TFOG_LAMP_STRENGTH = 0.0   # sodium point lights, W-scale multiplier
# The lamp W-scale multiplier (s19-B15e, named out of the worklog):
# fog multiplies emission, so the ladder authors lamp strengths at
# ~W/800 -- the probe-const law (a 40 W probe read as a blowout; 0.025
# x 800 = 20 W reads as a sodium pool at blue hour; see tfog_world_look).
TFOG_LAMP_W_SCALE = 800.0
TFOG_STRIP_STRENGTH = 0.0  # canopy strip panels
TFOG_GLYPH_STRENGTH = 0.0  # departure-board glyph rows
TFOG_ASPECT_STRENGTH = 0.0  # gantry red/green discs
TFOG_WINDOW_STRENGTH = 0.0  # train window strips

# --- set frame (meters; platform top z=0, world floor z=-0.9) --------
PLAT_X, PLAT_Y = 32.0, 4.0         # slab x -32..32, y -4..4
BED_Z = -0.9                       # track-bed / world-floor level
TRACK_Y = 8.5                      # |y| of both track centers
GAUGE = 0.72                       # rails at TRACK_Y +- GAUGE
BALLAST_TOP, SLEEPER_TOP = -0.74, -0.69
RAIL_TOP = -0.55
ROOF_Z, ROOF_T = 3.4, 0.3          # roof slab center z / thickness
CAR_L, CAR_W, CAR_H = 16.0, 2.8, 3.2
CAR_GAP = 1.0
CAR_PITCH = CAR_L + CAR_GAP        # 17 m
CAR_LIFT = 1.95                    # car-center z above the root EMPTY
COL_XS = (-25.0, -15.0, -5.0, 5.0, 15.0, 25.0)
STRIP_XS = (-27.0, -21.0, -9.0, -3.0, 3.0, 9.0, 21.0, 27.0)
LAMP_XS = (-20.0, 0.0, 20.0)
BENCH_XS = (-12.0, 12.0)
BOARD_Z = 2.6                      # board panel center z
GLYPH_ZS = (2.15, 2.45, 2.75, 3.05)
EXPRESS_N_CARS, LOCAL_N_CARS = 8, 3

FACTORY_NAMES = {"Cube", "Camera", "Light", "Lamp", "Sphere", "Circle",
                 "Cone", "Cylinder", "Plane", "Icosphere", "Torus"}


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
    from mathutils import Vector
    corners = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    mn = [min(c[i] for c in corners) for i in range(3)]
    mx = [max(c[i] for c in corners) for i in range(3)]
    return mn, mx


def _build_materials():
    """The blue-hour palette + the keyed-OFF glow slots (F-TD11)."""
    m = {}
    m["concrete"] = make_material("tfg_concrete", (0.085, 0.085, 0.092), 0.75)
    m["tactile"] = make_material("tfg_tactile_yellow", (0.42, 0.32, 0.045), 0.7)
    m["ballast"] = make_material("tfg_ballast", (0.042, 0.042, 0.045), 0.95)
    m["sleeper"] = make_material("tfg_sleeper", (0.028, 0.024, 0.020), 0.9)
    m["rail"] = make_material("tfg_rail", (0.020, 0.020, 0.023), 0.15,
                              metallic=0.8)          # glossy dark
    m["roof"] = make_material("tfg_roof", (0.030, 0.030, 0.034), 0.6)
    m["column"] = make_material("tfg_column", (0.050, 0.050, 0.055), 0.5,
                                metallic=0.3)
    m["strip"] = make_material("tfg_strip_light", (0.060, 0.070, 0.080),
                               0.4, emission_color=(0.75, 0.85, 1.0),
                               emission_strength=TFOG_STRIP_STRENGTH)
    m["lamp_head"] = make_material("tfg_lamp_head", (0.045, 0.045, 0.050), 0.5)
    m["board"] = make_material("tfg_board", (0.012, 0.012, 0.015), 0.4)
    m["glyph"] = make_material("tfg_glyph", (0.010, 0.010, 0.012), 0.5,
                               emission_color=(1.0, 0.75, 0.30),
                               emission_strength=TFOG_GLYPH_STRENGTH)
    m["bench"] = make_material("tfg_bench", (0.090, 0.060, 0.040), 0.7)
    m["bin"] = make_material("tfg_bin", (0.050, 0.060, 0.065), 0.6)
    m["kiosk"] = make_material("tfg_kiosk", (0.040, 0.050, 0.060), 0.7)
    m["steel"] = make_material("tfg_steel", (0.030, 0.032, 0.035), 0.5,
                               metallic=0.4)
    m["aspect_red"] = make_material("tfg_aspect_red", (0.10, 0.010, 0.010),
                                    0.4, emission_color=(1.0, 0.08, 0.05),
                                    emission_strength=TFOG_ASPECT_STRENGTH)
    m["aspect_green"] = make_material("tfg_aspect_green",
                                      (0.010, 0.080, 0.020), 0.4,
                                      emission_color=(0.10, 1.0, 0.15),
                                      emission_strength=TFOG_ASPECT_STRENGTH)
    m["express"] = make_material("tfg_express_body", (0.012, 0.013, 0.016),
                                 0.35, metallic=0.5)   # the dark wedge
    m["local"] = make_material("tfg_local_body", (0.12, 0.045, 0.030),
                               0.45)                 # the warm 3-car
    m["win_express"] = make_material("tfg_win_express",
                                     (0.015, 0.015, 0.018), 0.4,
                                     emission_color=(1.0, 0.85, 0.60),
                                     emission_strength=TFOG_WINDOW_STRENGTH)
    m["win_local"] = make_material("tfg_win_local", (0.020, 0.015, 0.012),
                                   0.4, emission_color=(1.0, 0.70, 0.40),
                                   emission_strength=TFOG_WINDOW_STRENGTH)
    m["backdrop"] = make_material("tfg_backdrop", (0.014, 0.015, 0.018), 0.95)
    m["ground"] = make_material("tfg_ground", (0.030, 0.030, 0.032), 0.95)
    return m


def fog_density_for_engine(scene=None):
    """s27 BOTH-ENGINE DELTA (the tferry_world pattern): the certified
    fog look (EEVEE, 0.028) renders THINNER under Cycles (path-traced
    single-scatter vs the rasterized veil) — the Cycles lane serves
    0.040. The S5 blast-window swallow guard (0.05-class) is re-checked
    by eye on the Cycles probe before the stills wave."""
    from blender_kit import normalize_engine_id
    eng = normalize_engine_id(
        (scene.render.engine if scene is not None
         else bpy.context.scene.render.engine))
    return TFOG_FOG_DENSITY * (1.45 if eng.startswith("CYCLES") else 1.0)


def _fog_material(scene=None):
    """fog_box: pure Volume Scatter (density = the ladder constant).

    s19-B7: the density is re-applied on the CACHED path too (the
    tform_world._dust_material twin) -- a rebuild that skips the
    orphan purge must not silently keep the previous rung's fog
    density (the ladder overrides the module const, not the datablock).
    """
    mat = bpy.data.materials.get("tfg_fog")
    if mat is None:
        mat = bpy.data.materials.new("tfg_fog")
    mat.use_nodes = True
    nt = mat.node_tree
    for n in [n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"]:
        nt.nodes.remove(n)              # pure volume, no surface shader
    out = next((n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"), None)
    if out is None:
        out = nt.nodes.new("ShaderNodeOutputMaterial")
    sc = next((n for n in nt.nodes if n.type == "VOLUME_SCATTER"), None)
    if sc is None:
        sc = nt.nodes.new("ShaderNodeVolumeScatter")
        sc.inputs["Color"].default_value = (0.70, 0.75, 0.85, 1.0)
        nt.links.new(sc.outputs["Volume"], out.inputs["Volume"])
    sc.inputs["Density"].default_value = fog_density_for_engine(scene)
    return mat


def _train(root, n_cars, body_mat, strip_mat, strip_side, tag):
    """n_cars parented to root (IDENTITY matrix_parent_inverse: child
    locs are plain offsets in the root's axis-aligned frame)."""
    names = []
    for i in range(n_cars):
        cx = i * CAR_PITCH
        car = _box(f"{tag}_car_{i + 1}", CAR_L, CAR_W, CAR_H,
                   (cx, 0.0, CAR_LIFT), body_mat)
        car.parent = root
        strip = _box(f"{tag}_strip_{i + 1}", CAR_L - 2.0, 0.06, 0.8,
                     (cx, strip_side * (CAR_W / 2 + 0.03),
                      CAR_LIFT + 0.35), strip_mat)
        strip.parent = root
        names += [car.name, strip.name]
    # fix-wave-2 eyepass (tfog S10, THE DOORWAY): the intent 'through
    # the door: warm interior vs cold platform' had NO carrier — the
    # car side is a continuous wall (the VLM: 'reposition the camera
    # OR OPEN THE DOOR'). The local's car_2 east end (root-relative
    # x=24; absolute x~0 at the dwell, where the S9-cert queue
    # presses) gets a REAL opening: a tall warm emissive panel on the
    # platform face (the strips' own proud-panel construction — the
    # car's dark body is the surround) — parented to the root so it
    # rides the slide keys.
    if tag == "local":
        glow = _box("TF.LocalDoorGlow", 1.0, 0.06, 2.0,
                    (24.0, strip_side * (CAR_W / 2 + 0.04),
                     1.28), _door_glow_material())
        glow.parent = root
        names.append(glow.name)
    return names


def _door_glow_material():
    """The warm interior seen through the open door (the L-TF1 close-
    up ceiling class: near emissive rows cap ~1.1-1.3; the door reads
    at 1.15 warm amber)."""
    import bpy
    mat = bpy.data.materials.new("tfg_door_glow")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.55, 0.36, 0.16, 1.0)
    bsdf.inputs["Emission Color"].default_value = (0.9, 0.62, 0.30, 1.0)
    bsdf.inputs["Emission Strength"].default_value = 1.15
    return mat


def build_world(scene):
    """Build the fog platform; returns the parts/export ctx dict."""
    mats = _build_materials()
    pre = set(scene.objects.keys())
    export = {"windows": [], "lamps": [], "lights_strip": [],
              "board_rows_n": [], "board_rows_s": [],
              "aspects": ["aspect_red", "aspect_green"]}

    # --- grounding plane + the island platform slab (top z=0; its N/S
    # sides are the face walls down to z=-0.9 -- ledger 1) -------------
    _box("ground_plane", 700.0, 700.0, 0.04, (0.0, 0.0, -0.92),
         mats["ground"])
    _box("platform_slab", 2 * PLAT_X, 2 * PLAT_Y, -BED_Z,
         (0.0, 0.0, BED_Z / 2), mats["concrete"])
    for tag, cy in (("n", -PLAT_Y + 0.3), ("s", PLAT_Y - 0.3)):
        _box(f"tactile_{tag}", 2 * PLAT_X, 0.4, 0.02,
             (0.0, cy, 0.01), mats["tactile"])         # 0.4 m inset band

    # --- the two track beds (z=-0.9) -----------------------------------
    for tag, cy in (("n", -TRACK_Y), ("s", TRACK_Y)):
        _box(f"ballast_{tag}", 2 * PLAT_X, 9.0, 0.16,
             (0.0, cy, BED_Z + 0.08), mats["ballast"])
        bar = None
        for si in range(26):
            sx = -31.25 + si * 2.5
            if bar is None:
                bar = _box(f"sleeper_{tag}_1", 0.22, 9.0, 0.05,
                           (sx, cy, BED_Z + 0.185), mats["sleeper"])
            else:   # linked duplicate: 1 mesh datablock per bed
                d = bar.copy()
                d.name = f"sleeper_{tag}_{si + 1}"
                d.location = (sx, cy, BED_Z + 0.185)
                scene.collection.objects.link(d)
        for ri, ry in enumerate((cy - GAUGE, cy + GAUGE), start=1):
            _box(f"rail_{tag}_{ri}", 2 * PLAT_X, 0.14, 0.14,
                 (0.0, ry, BED_Z + 0.28), mats["rail"])

    # --- the canopy (columns 0..3.25, roof 3.25..3.55) ------------------
    _box("canopy_roof", 2 * PLAT_X, 7.6, ROOF_T, (0.0, 0.0, ROOF_Z),
         mats["roof"])
    for ci, cx in enumerate(COL_XS, start=1):
        _prim("cyl", (0.32, ROOF_Z - ROOF_T / 2),
              (cx, 0.0, (ROOF_Z - ROOF_T / 2) / 2), verts=12,
              mat=mats["column"], name=f"canopy_col_{ci}")
    for si, cx in enumerate(STRIP_XS, start=1):        # emissive OFF
        _box(f"lights_strip_{si}", 2.4, 1.2, 0.06, (cx, 0.0, 3.22),
             mats["strip"])
        export["lights_strip"].append(f"lights_strip_{si}")

    # --- 6 sodium lamp posts + OFF point lights -------------------------
    li = 0
    for lx in LAMP_XS:
        for ly in (-3.2, 3.2):
            li += 1
            _prim("cyl", (0.12, 3.0), (lx, ly, 1.5), verts=10,
                  mat=mats["lamp_head"], name=f"lamp_post_{li}")
            _box(f"lamp_head_{li}", 0.34, 0.34, 0.14, (lx, ly, 3.03),
                 mats["lamp_head"])
            ld = bpy.data.lights.new(f"lamp_{li}", type='POINT')
            ld.energy = TFOG_LAMP_STRENGTH * TFOG_LAMP_W_SCALE   # OFF
            ld.color = (1.0, 0.62, 0.30)                # ~sodium
            ld.shadow_soft_size = 0.15
            lo = bpy.data.objects.new(f"lamp_{li}", ld)
            lo.location = (lx, ly, 2.9)
            scene.collection.objects.link(lo)
            export["lamps"].append(f"lamp_{li}")

    # --- the double-sided departure board (hangs INTO the roof) ---------
    _box("board_panel", 3.0, 0.15, 1.25, (0.0, 0.0, 2.625),
         mats["board"])               # z 2.0..3.25 -> meets roof 3.25
    for ri, gz in enumerate(GLYPH_ZS, start=1):
        # s19-B8: N face is y<0 (the module frame law in the docstring
        # header: "N track/face is y<0, S face y>0"; tactile_n/ballast_n
        # follow it) — the "n" glyph rows must sit on the board's
        # N-facing side (-y), the "s" rows on the S-facing side (+y).
        # The old tuple had them swapped against that frame.
        for tag, gy in (("n", -0.085), ("s", 0.085)):
            _box(f"board_r{ri}_{tag}", 2.6, 0.02, 0.18,
                 (0.0, gy, gz), mats["glyph"])
            export[f"board_rows_{tag}"].append(f"board_r{ri}_{tag}")

    # --- dressing: benches x4, bins x2, kiosk ---------------------------
    bi = 0
    for bx in BENCH_XS:
        for by in (-2.4, 2.4):
            bi += 1
            _box(f"bench_{bi}_seat", 1.8, 0.5, 0.06, (bx, by, 0.42),
                 mats["bench"])
            for leg_i, leg in enumerate((-0.78, 0.78), start=1):
                _box(f"bench_{bi}_leg_{leg_i}", 0.08, 0.44, 0.42,
                     (bx + leg, by, 0.21), mats["bench"])
    for bi, (bx, by) in enumerate(((18.5, 0.9), (-18.5, -0.9)), start=1):
        _prim("cyl", (0.56, 0.75), (bx, by, 0.375), verts=12,
              mat=mats["bin"], name=f"bin_{bi}")
    _box("kiosk", 2.6, 2.0, 2.6, (26.0, -2.0, 1.3), mats["kiosk"])

    # --- the W exit stairs (the waiters' west_exit destination) ---------
    # Descending stair block + side walls at the W end, x -35..-32,
    # y -1.6..1.6 (OUTSIDE the walkable rect -- no sim blocked needed;
    # agents ghost at the dest before the edge).
    for si in range(6):
        _box(f"wexit_stair_{si + 1}", 0.5, 3.2, 0.9 - si * 0.15,
             (-32.25 - si * 0.5, 0.0, (0.9 - si * 0.15) / 2 - 0.9),
             mats["concrete"])
    _box("wexit_frame_l", 0.4, 0.25, 2.4, (-32.1, -1.7, 0.3), mats["steel"])
    _box("wexit_frame_r", 0.4, 0.25, 2.4, (-32.1, 1.7, 0.3), mats["steel"])
    _box("wexit_frame_t", 0.4, 3.65, 0.25, (-32.1, 0.0, 1.4), mats["steel"])

    # --- signal gantry over the N track (x=-34) --------------------------
    for tag, gy in (("w", -13.5), ("e", -3.5)):
        _box(f"gantry_post_{tag}", 0.3, 0.3, 5.4, (-34.0, gy, 1.8),
             mats["steel"])
    _box("gantry_beam", 0.3, 10.2, 0.3, (-34.0, -8.5, 4.5),
         mats["steel"])
    for tag, ay, mat in (("red", -TRACK_Y - GAUGE, mats["aspect_red"]),
                         ("green", -TRACK_Y + GAUGE,
                          mats["aspect_green"])):
        _box(f"aspect_{tag}_stem", 0.05, 0.05, 0.22,
             (-33.85, ay, 4.28), mats["steel"])
        _prim("cyl", (0.44, 0.12), (-33.85, ay, 3.95),
              rot=(0.0, math.radians(90.0), 0.0), verts=20, mat=mat,
              name=f"aspect_{tag}")

    # --- the two keyed trains (scene module owns the slides) ------------
    # side=+1 -> N track (y=-8.5), strip on the +y platform face;
    # side=-1 -> S track (y=+8.5), strip on the -y platform face
    for tag, rx, n, body, win, side in (
            ("express", -120.0, EXPRESS_N_CARS, mats["express"],
             mats["win_express"], 1.0),
            ("local", -90.0, LOCAL_N_CARS, mats["local"],
             mats["win_local"], -1.0)):
        bpy.ops.object.empty_add(type='PLAIN_AXES',
                                 location=(rx, -side * TRACK_Y, BED_Z))
        root = bpy.context.active_object
        root.name = f"{tag}_root"
        root.empty_display_size = 2.0
        export[f"{tag}_root"] = root.name
        export[f"{tag}_cars"] = _train(root, n, body, win, side, tag)
        export["windows"] += export[f"{tag}_cars"][1::2]

    # --- the ONE fog volume (the 192 m box is KILLED) --------------------
    _box("fog_box", 64.0, 10.0, 6.0, (0.0, 0.0, 3.0), _fog_material(scene))

    # --- far N/S silhouette planes (dark matte, grounded) ----------------
    for tag, by in (("n", 45.0), ("s", -45.0)):
        _box(f"backdrop_{tag}", 340.0, 1.5, 22.0, (0.0, by, 10.1),
             mats["backdrop"])

    bpy.context.view_layer.update()
    created = [ob for ob in scene.objects if ob.name not in pre]
    export["fog_box"] = "fog_box"
    export["fog_density"] = TFOG_FOG_DENSITY
    return {"parts": created, "mats": mats, "export": export,
            "consts": {"fog_density": TFOG_FOG_DENSITY,
                       "lamp": TFOG_LAMP_STRENGTH,
                       "strip": TFOG_STRIP_STRENGTH,
                       "glyph": TFOG_GLYPH_STRENGTH,
                       "aspect": TFOG_ASPECT_STRENGTH,
                       "window": TFOG_WINDOW_STRENGTH}}


# ======================================================================
# __main__ QA (NON-VISUAL: asserts + prints, ZERO renders)
# ======================================================================

def _ok(tag, cond, detail):
    print(f"[tfog-qa] {'PASS' if cond else 'FAIL'} {tag}: {detail}")
    return 0 if cond else 1


def _qa(ctx):
    scene = bpy.context.scene
    parts, export = ctx["parts"], ctx["export"]
    fails = 0
    names = {ob.name for ob in parts}

    # QA0: factory purge -- no factory survivor, no orphan
    survivors = sorted(names & FACTORY_NAMES)
    fails += _ok("factory purge", not survivors and
                 names == {ob.name for ob in scene.objects},
                 f"0 factory survivors / {len(parts)} parts, "
                 f"orphans {survivors}")

    # QA1: every mesh has a material
    naked = [ob.name for ob in scene.objects
             if ob.type == 'MESH' and not ob.data.materials]
    fails += _ok("mesh materials", not naked,
                 f"{len(naked)} naked {[naked[:5]]}")

    # QA2: the keyed export surface (lamp/board/strip/aspect/window)
    want = (export["lamps"] + export["lights_strip"] +
            export["board_rows_n"] + export["board_rows_s"] +
            export["aspects"] + export["windows"])
    missing = [n for n in want if n not in names]
    fails += _ok("export names", not missing,
                 f"{len(want)} keyed names, missing {missing[:5]}")

    # QA3: the two trains: roots + 8/3 cars, pinned roots, seated cars
    exp = bpy.data.objects.get("express_root")
    loc = bpy.data.objects.get("local_root")
    root_ok = (exp is not None and loc is not None and
               all(abs(a - b) < 1e-4 for a, b in
                   zip(exp.location, (-120.0, -8.5, BED_Z))) and
               all(abs(a - b) < 1e-4 for a, b in
                   zip(loc.location, (-90.0, 8.5, BED_Z))))
    fails += _ok("train roots", root_ok,
                 f"express {tuple(exp.location) if exp else None} / "
                 f"local {tuple(loc.location) if loc else None}")
    n_exp = sum(1 for n in export.get("express_cars", [])
                if "_car_" in n)
    n_loc = sum(1 for n in export.get("local_cars", [])
                if "_car_" in n)
    fails += _ok("train cars", n_exp == 8 and n_loc == 3,
                 f"express {n_exp}/8, local {n_loc}/3")
    car_z = [_bounds(bpy.data.objects[n])[0][2]
             for n in export["express_cars"][0::2]]
    fails += _ok("cars seated on rails",
                 all(abs(z - RAIL_TOP) < 5e-3 for z in car_z),
                 f"car min-z {min(car_z):.3f}~{max(car_z):.3f} "
                 f"(rail top {RAIL_TOP})")

    # QA4: fog_box -- present, volume-scatter material, density pinned
    fb = bpy.data.objects.get("fog_box")
    fog_ok = False
    if fb is not None and fb.type == 'MESH' and fb.data.materials:
        nt = fb.data.materials[0].node_tree
        vol = [l.from_node for l in nt.links
               if l.to_node.type == 'OUTPUT_MATERIAL'
               and l.to_socket.name == "Volume"]
        dens = next((n for n in nt.nodes
                     if n.type == 'VOLUME_SCATTER'), None)
        fog_ok = (vol and dens is not None and
                  abs(dens.inputs["Density"].default_value -
                      TFOG_FOG_DENSITY) < 1e-6)
    fails += _ok("fog_box volume", fog_ok,
                 f"density {TFOG_FOG_DENSITY}, 64x10x6 @z 0..6")

    # QA5: no floaters -- key props seated on their surfaces (float32
    # note: 5e-3 tolerance covers single-precision matrix noise)
    seated = {"canopy_col_1": ("min", 0.0), "canopy_roof": ("min", 3.25),
              "lamp_post_1": ("min", 0.0), "kiosk": ("min", 0.0),
              "bin_1": ("min", 0.0), "bench_1_seat": ("min", 0.39),
              "gantry_post_w": ("min", BED_Z), "ballast_n": ("min", BED_Z),
              "rail_n_1": ("min", -0.69), "sleeper_n_1": ("min", -0.74),
              "backdrop_n": ("min", BED_Z), "fog_box": ("min", 0.0),
              "platform_slab": ("max", 0.0),
              "board_panel": ("max", ROOF_Z - ROOF_T / 2)}
    floaters = []
    for n, (edge, want_z) in seated.items():
        ob = bpy.data.objects.get(n)
        z = _bounds(ob)[0 if edge == "min" else 1][2] if ob else None
        if z is None or abs(z - want_z) > 5e-3:
            floaters.append(f"{n}:{edge}z={z}")
    fails += _ok("seated (no floaters)", not floaters,
                 f"{len(seated)} anchors, bad {floaters}")

    # QA6: counts + the keyed-OFF state
    n_mesh = sum(1 for ob in scene.objects if ob.type == 'MESH')
    n_light = sum(1 for ob in scene.objects if ob.type == 'LIGHT')
    fails += _ok("counts", n_mesh < 200 and n_light == 6,
                 f"{len(parts)} objects ({n_mesh} meshes, {n_light} "
                 f"point lights) <200 budget")
    fails += _ok("keyed slots OFF",
                 all(ob.data.energy == 0.0 for ob in
                     bpy.data.objects if ob.type == 'LIGHT'),
                 "6 point lights energy 0 (scene module keys them)")

    manifest = {"module": "tfog_world",
                "counts": {"objects": len(parts), "meshes": n_mesh,
                           "lights": n_light,
                           "express_cars": n_exp, "local_cars": n_loc,
                           "lamps": len(export["lamps"]),
                           "strips": len(export["lights_strip"]),
                           "board_rows": len(export["board_rows_n"]) +
                           len(export["board_rows_s"]),
                           "benches": 4, "bins": 2},
                "consts": ctx["consts"],
                "exported": export}
    print(f"[tfog_world] manifest = {manifest}")
    print(f"[tfog-qa] SUMMARY: "
          f"{'ALL PASS' if fails == 0 else f'{fails} FAIL(S)'}")
    return fails


def main():
    from blender_kit import clear_scene, script_argv
    p = argparse.ArgumentParser(
        description="EXPRESS world: build + non-visual QA (no render)")
    p.add_argument("--dry-run", action="store_true",
                   help="accepted no-op: this module never renders")
    p.parse_args(script_argv())

    clear_scene()                    # the factory-startup purge (kit law)
    scene = bpy.context.scene
    fails = _ok("purge clean", len(scene.objects) == 0,
                f"{len(scene.objects)} objects after clear_scene")
    ctx = build_world(scene)
    fails += _qa(ctx)
    print("[tfog_world] smoke render skipped (principal renders are "
          "scene-side; textual asserts only)")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
