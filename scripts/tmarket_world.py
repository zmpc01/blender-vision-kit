"""tmarket_world.py -- NIGHT MARKET's set: the lantern street (D-NM2).

CYCLES-NATIVE night (the s27 law: this film is BORN under the
corrected engine map): Nishita at sun -8 deg, strength 0.010 Cycles /
0.10 EEVEE mirror (the tferry pattern, BOTH-ENGINE pinned -- the
mirror is BUILD-TIME-READ and therefore inert without the D2 hoist;
main() sets scene.render.engine = normalize_engine_id BEFORE
build_world). ~14 stall lanterns are REAL point lights (warm 2800K)
+ 2 food-court sodium floods, with the measured BOTH-ENGINE mirror
`_lw = 3.5 if _cyc else 1.0` (the tferry_world receipt). The string
bulbs join the EMISSIVE-IS-LIGHT budget (under Cycles every emissive
surface IS a sampled light -- the audit P1): they light the aisle AND
add mesh-light sampling cost; 2 rows x 12 bulbs. Lantern materials
pin the glow-surface law (dark base + saturated Emission Color,
strength <= 0.95). Ground: damp cobble roughness 0.12 (the tsquall
wet-sheen class; Cycles glossy GI reads STRONGER than EEVEE SSR).
Steam: ONE gentle volume over the food court via fog_density_for_
engine at WISP scale (the tfog canonical 0.028/0.040; the wisp is
the 0.36 fraction: 0.010 EEVEE / 0.0145 Cycles).

Coordinate frame (the contract IS the authority): stalls rows
y = +-2.6; the spine between them; food court x 16..24; west plaza
x -26..-14; walkable y -6..6.6.
"""
from __future__ import annotations

import math

import bpy

from tdawn_actors import make_material

STALL_X = (-6.0, -4.0, -2.0, 0.0, 2.0, 4.0, 6.0)
DRESS_X = (-15.0, -13.0, 11.0)   # mirrors tmarket_contract._DRESS_X
ROW_Y = (2.6, -2.6)
FOOD_X = 20.0
CANOPY_Z = 2.35            # the tarp canopy height
COUNTER_H = 0.95           # the counter top (the barricade r 0.95 law)

WISP_RATIO = 0.36          # the tfog canonical fraction (0.010 / 0.0145)


def _box(name, sx, sy, sz, loc, mat):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    ob = bpy.context.active_object
    ob.name = name
    ob.scale = (sx, sy, sz)
    if mat is not None:
        ob.data.materials.append(mat)
    return ob


def _cyl(name, r, depth, loc, mat, verts=16):
    bpy.ops.mesh.primitive_cylinder_add(
        radius=r, depth=depth, location=loc, vertices=verts)
    ob = bpy.context.active_object
    ob.name = name
    if mat is not None:
        ob.data.materials.append(mat)
    return ob


def _build_materials():
    m = {}
    # the damp cobble (the tsquall wet-sheen class: DARK base +
    # roughness 0.12 -- Cycles glossy GI reflects the lanterns)
    m["cobble"] = make_material("TM.Cobble", (0.042, 0.038, 0.033), 0.12)
    m["cobble_dry"] = make_material("TM.CobbleDry", (0.034, 0.031, 0.028),
                                    0.55)
    # the stall set: wood counters, tarp canopies, poles
    m["wood"] = make_material("TM.Wood", (0.052, 0.038, 0.024), 0.7)
    m["tarp_n"] = make_material("TM.TarpN", (0.045, 0.028, 0.020), 0.8)
    m["tarp_s"] = make_material("TM.TarpS", (0.028, 0.034, 0.040), 0.8)
    m["pole"] = make_material("TM.Pole", (0.030, 0.028, 0.026), 0.6,
                              metallic=0.4)
    # the lantern glow (the glow-surface law: dark base + saturated
    # Emission Color, strength <= 0.95 -- the F-TD11 params)
    m["lantern"] = make_material(
        "TM.Lantern", (0.030, 0.014, 0.006), 0.4,
        emission_color=(1.0, 0.66, 0.28), emission_strength=0.95)
    # the string bulbs (the emissive-is-light budget members)
    m["bulb"] = make_material(
        "TM.Bulb", (0.020, 0.012, 0.005), 0.4,
        emission_color=(1.0, 0.72, 0.36), emission_strength=2.5)
    # the sodium floods (the tferry hue)
    m["sodium"] = make_material(
        "TM.Sodium", (0.010, 0.008, 0.005), 0.4,
        emission_color=(1.0, 0.62, 0.18), emission_strength=2.6)
    # the food-court set: steel counters + steam-lit awning
    m["steel"] = make_material("TM.Steel", (0.040, 0.042, 0.046), 0.35,
                               metallic=0.6)
    m["awning"] = make_material("TM.Awning", (0.050, 0.022, 0.018), 0.8)
    # dress: the shopfronts behind the rows (the south edge) + the
    # west plaza facade
    m["shop"] = make_material("TM.Shop", (0.036, 0.032, 0.030), 0.75)
    m["shop_win"] = make_material(
        "TM.ShopWin", (0.018, 0.014, 0.010), 0.3,
        emission_color=(1.0, 0.60, 0.26), emission_strength=0.55)
    m["planter"] = make_material("TM.Planter", (0.028, 0.036, 0.024), 0.8)
    m["leaf"] = make_material("TM.Leaf", (0.020, 0.038, 0.018), 0.7)
    return m


def fog_density_for_engine(scene=None):
    """The WISP-scale steam (D-NM2): the tfog BOTH-ENGINE delta at a
    0.36 fraction -- Cycles reads volume THINNER, so the Cycles value
    is the HIGHER one (0.010 EEVEE / 0.0145 Cycles)."""
    from blender_kit import normalize_engine_id
    eng = normalize_engine_id(
        (scene.render.engine if scene is not None
         else bpy.context.scene.render.engine))
    base = 0.010
    return base * (1.45 if eng.startswith("CYCLES") else 1.0)


def build_world(scene):
    """Build the lantern street; returns the parts dict."""
    mats = _build_materials()
    parts = {"mats": mats, "lights": []}

    # --- the ground: the damp cobble street ----------------------------
    ground = _box("TM.Ground", 60.0, 18.0, 0.12, (0.0, 0.5, -0.06),
                  mats["cobble"])
    parts["ground"] = ground

    # --- the stall rows (the contract's barricade squares ARE these) ---
    from blender_kit import normalize_engine_id
    _cyc0 = normalize_engine_id(
        scene.render.engine).startswith("CYCLES")
    _lw0 = 3.5 if _cyc0 else 1.0   # the BOTH-ENGINE mirror (the receipt;
                                   # the lanterns ride it like the sodium)
    lantern_i = 0
    for sy in ROW_Y:
        tarp = mats["tarp_n"] if sy > 0 else mats["tarp_s"]
        for x in STALL_X:
            _box(f"TM.Counter_{x:+.0f}_{sy:+.1f}", 1.9, 0.8, COUNTER_H,
                 (x, sy, COUNTER_H / 2), mats["wood"])
            # the canopy: a tarp plane on 4 poles (the stall silhouette;
            # SMALLER than the light spread so the pools peek from the
            # aerial -- the s28 eye-ladder receipt)
            _box(f"TM.Canopy_{x:+.0f}_{sy:+.1f}", 1.5, 0.9, 0.06,
                 (x, sy, CANOPY_Z), tarp)
            for px in (x - 0.65, x + 0.65):
                for py in (sy - 0.35, sy + 0.35):
                    _cyl(f"TM.Pole_{px:+.1f}_{py:+.1f}", 0.035, CANOPY_Z,
                         (px, py, CANOPY_Z / 2), mats["pole"], verts=8)
            # the LANTERN (the lit 7 per row): a small emissive sphere
            # under the canopy + the REAL point light (the f486 lesson:
            # emissive glows, the light LIGHTS)
            lz = CANOPY_Z - 0.28
            _cyl(f"TM.LanternMesh_{x:+.0f}_{sy:+.1f}", 0.09, 0.22,
                 (x + 0.55, sy + 0.28, lz), mats["lantern"], verts=10)
            ld = bpy.data.lights.new(
                f"TM.LanternLight_{lantern_i:02d}", type='POINT')
            ld.energy = 90.0 * _lw0     # the s28 eye-ladder rung 2 (45
                                        # read dim from the aerial)
            ld.color = (1.0, 0.70, 0.42)
            ld.shadow_soft_size = 0.12
            lob = bpy.data.objects.new(
                f"TM.LanternLight_{lantern_i:02d}", ld)
            lob.location = (x + 0.55, sy + 0.28, lz - 0.1)
            scene.collection.objects.link(lob)
            parts["lights"].append(lob)
            lantern_i += 1
        # the dress carts (unlit; the row continues west/east)
        for x in DRESS_X:
            _box(f"TM.Dress_{x:+.0f}_{sy:+.1f}", 1.9, 0.8, COUNTER_H,
                 (x, sy, COUNTER_H / 2), mats["wood"])

    # --- the string bulbs (2 rows, catenary between the canopies) -----
    # The EMISSIVE-IS-LIGHT budget: 24 small emissive spheres join the
    # Cycles light sampling (the audit P1) -- they add the aisle's
    # ambient warmth; the lanterns own the pools.
    for sy in ROW_Y:
        zs = CANOPY_Z + 0.32
        for i in range(12):
            x = -13.0 + i * (26.0 / 11.0)
            droop = 0.14 * math.sin(math.pi * i / 11.0)
            _cyl(f"TM.Bulb_{sy:+.1f}_{i:02d}", 0.035, 0.10,
                 (x, sy, zs - droop), mats["bulb"], verts=8)

    # --- the food court (the east end) ---------------------------------
    for sy in (2.6, -2.6):
        _box(f"TM.FoodCounter_{sy:+.1f}", 0.8, 1.9, COUNTER_H,
             (FOOD_X, sy, COUNTER_H / 2), mats["steel"])
        _box(f"TM.Awning_{sy:+.1f}", 1.6, 2.3, 0.06,
             (FOOD_X, sy, CANOPY_Z + 0.15), mats["awning"])
    # the 2 SODIUM FLOODS (the tferry hue; the food-court pools)
    _cyc = None
    from blender_kit import normalize_engine_id
    _cyc = normalize_engine_id(scene.render.engine).startswith("CYCLES")
    _lw = 3.5 if _cyc else 1.0     # the BOTH-ENGINE mirror (the receipt)
    for i, sy in enumerate((1.2, -1.2)):
        _cyl(f"TM.SodiumMesh_{i}", 0.10, 0.16, (FOOD_X - 0.2, sy, 2.5),
             mats["sodium"], verts=10)
        ld = bpy.data.lights.new(f"TM.SodiumLight_{i}", type='AREA')
        ld.energy = 120.0 * _lw
        ld.color = (1.0, 0.62, 0.22)
        ld.size = 0.5
        ld.shadow_soft_size = 0.2
        sob = bpy.data.objects.new(f"TM.SodiumLight_{i}", ld)
        sob.location = (FOOD_X - 0.4, sy, 2.55)
        scene.collection.objects.link(sob)
        parts["lights"].append(sob)

    # --- the noodle serving window (DRESS-ONLY: the contract keeps the
    # rails OUT of the barricade table -- the s28 bisect measured the
    # reachability swing; the SIM's admission portal resolves from its
    # point/width alone. The meshes sell the window.) ------------------
    for rx in (-2.81, -1.19):
        _box(f"TM.NoodleRail_{rx:+.2f}", 0.20, 0.16, 1.05,
             (rx, 1.58, 1.05 / 2 + 0.55), mats["wood"])

    # --- the west plaza (the arrival edge) ------------------------------
    # a low facade wall + the two planters (the contract's barricades)
    _box("TM.WestWall", 0.3, 8.0, 3.2, (-27.5, 0.0, 1.6), mats["shop"])
    for wx in range(-3):
        _box(f"TM.WestWin_{wx}", 0.1, 1.4, 1.5,
             (-27.3, -3.0 + wx * 3.0, 1.1), mats["shop_win"])
    for px, py in ((-24.5, 3.0), (-24.5, -3.0)):
        _box(f"TM.PlanterBox_{px:+.1f}_{py:+.1f}", 1.0, 1.0, 0.6,
             (px, py, 0.3), mats["planter"])
        _cyl(f"TM.Leafball_{px:+.1f}_{py:+.1f}", 0.42, 0.7,
             (px, py, 0.95), mats["leaf"], verts=10)
    for px, py in ((15.5, 3.0), (15.5, -3.0)):
        _box(f"TM.PlanterBox_{px:+.1f}_{py:+.1f}", 1.0, 1.0, 0.6,
             (px, py, 0.3), mats["planter"])
        _cyl(f"TM.Leafball_{px:+.1f}_{py:+.1f}", 0.42, 0.7,
             (px, py, 0.95), mats["leaf"], verts=10)

    # --- the shopfront dress (the south edge behind the stall rows) ---
    _box("TM.SouthShops", 52.0, 0.3, 3.4, (0.0, -6.6, 1.7), mats["shop"])
    for i in range(9):
        _box(f"TM.SouthWin_{i}", 2.2, 0.1, 1.3,
             (-20.0 + i * 5.0, -6.42, 1.15), mats["shop_win"])

    # --- the TITLE GANTRY (the west entrance; the scene module hangs
    # the neon sign on it) ----------------------------------------------
    for px in (-16.2, -13.8):
        _cyl(f"TM.GantryPost_{px:+.1f}", 0.09, 5.0, (px, 0.0, 2.5),
             mats["pole"], verts=10)
    _box("TM.GantryBeam", 2.9, 0.22, 0.22, (-15.0, 0.0, 4.85),
         mats["pole"])

    # --- the STEAM volume over the food court (the wisp) ---------------
    from blender_kit import normalize_engine_id  # noqa: F811
    eng = normalize_engine_id(scene.render.engine)
    density = fog_density_for_engine(scene)
    print(f"[tmarket_world] steam wisp density {density:.4f} "
          f"({eng.split('_')[-1] if '_' in eng else eng})")
    vol_mat = bpy.data.materials.new("TM.Steam")
    vol_mat.use_nodes = True
    nt = vol_mat.node_tree
    for n in list(nt.nodes):
        if n.type != 'OUTPUT_MATERIAL':
            nt.nodes.remove(n)
    out = nt.nodes.get("Material Output")
    sc = nt.nodes.new("ShaderNodeVolumeScatter")
    sc.inputs["Density"].default_value = density
    sc.inputs["Color"].default_value = (0.82, 0.80, 0.78, 1.0)
    sc.inputs["Anisotropy"].default_value = 0.3
    nt.links.new(sc.outputs["Volume"], out.inputs["Volume"])
    steam = _box("TM.SteamBox", 9.0, 8.0, 3.4, (19.0, 0.0, 1.9), vol_mat)
    steam.visible_shadow = False
    parts["steam"] = steam

    # --- the SKY (the D-NM2 ladder; BOTH-ENGINE, build-time-read) ------
    # UNMEASURED at -8 (tferry's 0.012/0.12 was measured at -6): the
    # ladder's FIRST gate is 2-3 probe stills BOTH engines vs the
    # tferry corpus (R1 measure-first).
    from blender_kit import add_sky_world
    _cycles2 = normalize_engine_id(
        scene.render.engine).startswith("CYCLES")
    add_sky_world(sun_elevation_deg=-8.0, sun_rotation_deg=205.0,
                  strength=0.010 if _cycles2 else 0.10)
    print(f"[tmarket_world] sky: Nishita -8deg strength "
          f"{0.010 if _cycles2 else 0.10} (cycles={_cycles2})")

    bpy.context.view_layer.update()
    return parts
