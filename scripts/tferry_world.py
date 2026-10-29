"""tferry_world.py -- LAST FERRY's set: the night pier (D-TF1 REV-2).

Self-contained bpy; materials via tdawn_actors.make_material (the
F-TD11 emission params -- this film is the params' FIRST production
consumer: every glow surface is dark-base + saturated Emission Color,
the glow-surface law as an API).

Coordinate frame (REV-2): the gangway throat AT (0,0); deck y 0..42;
landing apron y -6..0 (x -2.2..2.2) -- the bridge's hardcoded walkable
reaches y=-6; water y -10..46 x -20..20; ferry hull y -10..-3; the
outboard margins x ±6.2..±13 are crowd-free by construction
(CROWD_X_RANGE) and carry the rails/bollards/lamps/crane track.
"""
from __future__ import annotations

import math

import bpy

from tdawn_actors import make_material

HALL_X = 13.0             # deck half-width (dressing to ±13)
DECK_Y0 = -6.0            # the landing apron's south edge
THROAT_Y = 0.0            # the gangway pinch AT the origin
DECK_Y1 = 42.0            # the pier head
WATER_Y0, WATER_Y1 = -10.0, 46.0
FREEBOARD = 1.4           # REV-2 F13: 0.55 reads from no aerial
DECK_TOP = 0.0
WATER_Z = DECK_TOP - FREEBOARD

GANGWAY_HW = 1.0          # the 2.0m clear choke (half-width)


def _box(name, sx, sy, sz, loc, mat):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    ob = bpy.context.active_object
    ob.name = name
    ob.scale = (sx, sy, sz)
    if mat is not None:
        ob.data.materials.append(mat)
    return ob


def _prim(kind, size, loc, rot=(0.0, 0.0, 0.0), verts=16, mat=None):
    fn = {"cyl": bpy.ops.mesh.primitive_cylinder_add,
          "sph": bpy.ops.mesh.primitive_uv_sphere_add,
          "cone": bpy.ops.mesh.primitive_cone_add}[kind]
    kw = {"location": loc, "rotation": rot, "vertices": verts}
    if kind == "cyl":
        kw["radius"] = size[0] / 2
        kw["depth"] = size[1]
    elif kind == "cone":
        kw["radius1"] = size[0] / 2
        kw["depth"] = size[1]
    else:
        kw["radius"] = size[0] / 2
    fn(**kw)
    ob = bpy.context.active_object
    if mat is not None:
        ob.data.materials.append(mat)
    return ob


def _build_materials():
    m = {}
    # the wet deck (L-TF3): DARK base + roughness 0.14 -- the SSR
    # envelope (trace_max_roughness 0.5) reflects the lamps/neon
    m["deck_wet"] = make_material("TF.DeckWet", (0.028, 0.030, 0.034),
                                  rough=0.14)
    m["apron"] = make_material("TF.Apron", (0.022, 0.024, 0.026), 0.12)
    m["water"] = make_material("TF.Water", (0.010, 0.012, 0.016), 0.06)
    m["steel"] = make_material("TF.Steel", (0.040, 0.042, 0.046), 0.55,
                               metallic=0.6)
    m["hull"] = make_material("TF.Hull", (0.016, 0.018, 0.022), 0.7)
    # --- the neon (L-TF1): DARK base + saturated Emission Color via the
    # F-TD11 params. Sweep starts at the review's ladder (0.95/1.9/3.9).
    m["neon_cyan"] = make_material(
        "TF.NeonCyan", (0.006, 0.010, 0.012), 0.4,
        emission_color=(0.05, 0.85, 0.95), emission_strength=1.2)
    m["neon_mag"] = make_material(
        "TF.NeonMag", (0.012, 0.006, 0.010), 0.4,
        emission_color=(0.95, 0.10, 0.45), emission_strength=1.9)
    # the sodium lamps (L-TF2): warm pools on the wet deck
    m["sodium"] = make_material(
        "TF.Sodium", (0.010, 0.008, 0.005), 0.4,
        emission_color=(1.0, 0.62, 0.18), emission_strength=2.6)
    # ferry windows: the warm cap law (never > 0.95 -- the tan law is
    # input-curve; night does not relax it). Sweep 0.45/0.70/0.95.
    m["ferry_win"] = make_material(
        "TF.FerryWin", (0.030, 0.024, 0.016), 0.3,
        emission_color=(1.0, 0.72, 0.34), emission_strength=0.70)
    m["kiosk"] = make_material("TF.Kiosk", (0.050, 0.048, 0.044), 0.6)
    # the board's FLIP row (its own material -- the f85 BOARDING key
    # lands here; the night close-up ceiling measured at ~1.3)
    m["sign_flip"] = make_material(
        "TF.SignFlip", (0.012, 0.006, 0.010), 0.4,
        emission_color=(0.95, 0.10, 0.45), emission_strength=0.06)
    m["crate"] = make_material("TF.Crate", (0.055, 0.048, 0.038), 0.75)
    m["title"] = make_material("TF.TitleCard", (1.0, 0.88, 0.70), 0.4)
    return m


def build_world(scene):
    """Build the pier set; returns the parts dict."""
    mats = _build_materials()
    parts = {"mats": mats}

    # --- water first (the ferry floats on it) --------------------------
    water = _box("TF.Water", 40.0, WATER_Y1 - WATER_Y0, 0.1,
                 (0.0, (WATER_Y0 + WATER_Y1) / 2, WATER_Z - 0.05),
                 mats["water"])
    parts["water"] = water

    # --- the deck + landing apron --------------------------------------
    deck = _box("TF.Deck", HALL_X * 2, DECK_Y1 - THROAT_Y, 0.12,
                (0.0, (THROAT_Y + DECK_Y1) / 2, DECK_TOP - 0.06),
                mats["deck_wet"])
    # the apron: x -2.2..2.2, y -6..0 (the walkable's legal south half;
    # the rest of the south edge is barricade-lined in the contract)
    apron = _box("TF.Apron", 4.4, THROAT_Y - DECK_Y0, 0.12,
                 (0.0, (THROAT_Y + DECK_Y0) / 2, DECK_TOP - 0.06),
                 mats["apron"])
    parts["deck"], parts["apron"] = deck, apron
    # the pier EDGE faces (the freeboard drop reads in the deck-level
    # lens: dark faces down to the water)
    edge_w = _box("TF.DeckEdgeW", 0.1, DECK_Y1 - THROAT_Y, FREEBOARD,
                  (-HALL_X, (THROAT_Y + DECK_Y1) / 2,
                   DECK_TOP - FREEBOARD / 2), mats["hull"])
    edge_e = _box("TF.DeckEdgeE", 0.1, DECK_Y1 - THROAT_Y, FREEBOARD,
                  (HALL_X, (THROAT_Y + DECK_Y1) / 2,
                   DECK_TOP - FREEBOARD / 2), mats["hull"])
    edge_s = _box("TF.DeckEdgeS", HALL_X * 2 - 4.4, 0.1, FREEBOARD,
                  (0.0, THROAT_Y, DECK_TOP - FREEBOARD / 2),
                  mats["hull"])
    parts["deck_edges"] = (edge_w, edge_e, edge_s)

    # --- the FERRY (the dark hull + lit cabin strips, y -10..-3) ------
    hull = _box("TF.FerryHull", 16.0, 7.0, 3.2,
                (0.0, -6.5, WATER_Z + 1.6), mats["hull"])
    # the bow ramp toward the apron (the gangway lands ON it)
    ramp = _box("TF.FerryRamp", 2.6, 2.2, 0.18,
                (0.0, -2.1, WATER_Z + 2.6), mats["steel"])
    parts["ferry_ramp"] = ramp
    win_strips = []
    # three PANES per strip (mullions between) so the cabins read as
    # windows, not one flat lightbar (f486 lesson)
    for i, wz in enumerate((2.6, 3.5)):
        for p in range(3):
            win_strips.append(_box(
                f"TF.FerryWin{i}{p}", 1.7, 0.08, 0.55,
                (-3.4 + p * 3.4, -3.02, WATER_Z + wz),
                mats["ferry_win"]))
    funnel = _prim("cyl", (1.6, 2.2), (3.4, -7.5, WATER_Z + 4.4),
                   mat=mats["hull"], verts=20)
    parts["ferry_funnel"] = funnel
    parts["ferry_hull"] = hull
    parts["ferry_windows"] = win_strips

    # --- the GANGWAY (the 2m throat AT (0,0)) ---------------------------
    gw = {}
    rail_h = 1.05
    for sgn, nm in ((-1, "L"), (1, "R")):
        gw[f"rail{nm}1"] = _box(
            f"TF.GangRail{nm}1", 0.09, 3.4, 0.09,
            (sgn * GANGWAY_HW, 1.7, rail_h), mats["steel"])
        gw[f"rail{nm}2"] = _box(
            f"TF.GangRail{nm}2", 0.07, 3.4, 0.07,
            (sgn * GANGWAY_HW, 1.7, rail_h - 0.45), mats["steel"])
        for k, py in enumerate((0.35, 1.7, 3.05)):
            gw[f"post{nm}{k}"] = _prim(
                "cyl", (0.09, rail_h),
                (sgn * GANGWAY_HW, py, rail_h / 2),
                mat=mats["steel"], verts=10)
    # the ramp deck of the gangway itself (slight rise toward the water)
    gw["deck"] = _box("TF.GangDeck", GANGWAY_HW * 2, 3.4, 0.08,
                      (0.0, 1.7, -0.06), mats["steel"])
    parts["gangway"] = gw

    # --- the ticket KIOSK (dressing beside the throat, declared) ------
    kiosk = _box("TF.Kiosk", 1.4, 1.6, 2.3, (3.1, 2.0, 1.15),
                 mats["kiosk"])
    # the BOARDING BOARD (north face): a dark panel + TWO neon rows --
    # row 1 (the line name) always on, row 2 (BOARDING) is the FLIP
    # (its own material so the f85 key is independent). The S2 probe's
    # single flat slab had no flip carrier -- the beat had nothing to
    # land on (L-TF1 close-up ceiling measured: rows cap ~1.1-1.3).
    board = _box("TF.KioskBoard", 1.5, 0.08, 0.9, (3.1, 2.86, 2.3),
                 mats["kiosk"])
    sign_row1 = _box("TF.SignRow1", 1.2, 0.06, 0.22,
                     (3.1, 2.92, 2.52), mats["neon_mag"])
    # fix-wave-2 audit round: widened 1.2 -> 1.44 so the 0.30-size
    # BOARDING word (1.49 m wide) rides INSIDE its glow strip
    sign_row2 = _box("TF.SignRow2", 1.44, 0.06, 0.22,
                     (3.1, 2.92, 2.14), mats["sign_flip"])
    # fix-wave-2 eyepass round 3 (S2): the BOARDING word itself. The
    # bar composition read as 'blank pink rectangles' at the closer
    # vantage — the film's inciting beat needs the word. The tdawn
    # title law (extruded FONT -> CONVERTED MESH, glTF-safe) lands it
    # ON the flip row, riding the row's own sign_flip material (dark
    # 0.06 pre-call, ignites 1.3 at f85 — the flip IS the light-up).
    import bpy
    crv = bpy.data.curves.new("TF.BoardingWord", type="FONT")
    crv.body = "BOARDING"
    # fix-wave-2 audit round: 0.155 put the word at 5.4% of frame
    # height from the 4.6 m lens -- the VLM could not read it
    # ('SONIC'). 0.30 (cap ~0.21 m, width ~1.5 m = the board face)
    # with the closer S2 lens below puts it near 17% -- a READABLE
    # call
    crv.size = 0.30
    crv.align_x = "CENTER"
    crv.align_y = "CENTER"
    crv.extrude = 0.015
    word = bpy.data.objects.new("TF.BoardingWord", crv)
    word.location = (3.1, 2.965, 2.14)
    # face the arriving crowd (the camera's north side): rx=-90 maps
    # the text normal (+Z) to +Y; rz aims it at the S2 camera
    _cx, _cy = 1.4, 7.2
    _nx, _ny = _cx - 3.1, _cy - 2.965
    word.rotation_euler = (-math.pi / 2, 0.0, math.atan2(-_nx, _ny))
    scene.collection.objects.link(word)
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = word
    word.select_set(True)
    bpy.ops.object.convert(target="MESH")
    word.data.materials.append(mats["sign_flip"])
    parts["kiosk"] = kiosk
    parts["kiosk_board"] = (board, sign_row1, sign_row2)

    # --- the neon: the ferry-line sign over the throat ------------------
    # (a bar composition -- text does not survive glTF as curves; the
    # title carries the only words, converted mesh, like tdawn)
    neon = []
    neon.append(_box("TF.NeonBarCyan", 3.6, 0.12, 0.5,
                     (0.0, 0.55, 3.9), mats["neon_cyan"]))
    neon.append(_box("TF.NeonBarMag", 2.2, 0.12, 0.34,
                     (-4.6, 0.55, 2.6), mats["neon_mag"]))
    parts["neon"] = neon

    # --- sodium lamp posts along the deck (L-TF2 pools) -----------------
    lamps = []
    for i, (lx, ly) in enumerate(((-5.6, 8.0), (5.6, 12.0),
                                  (-5.6, 20.0), (5.6, 24.0),
                                  (-5.6, 32.0), (5.6, 34.0))):
        lamps.append(_prim("cyl", (0.14, 4.6), (lx, ly, 2.3),
                           mat=mats["steel"], verts=10))
        head = _box(f"TF.LampHead{i + 1}", 0.5, 0.24, 0.16,
                    (lx - math.copysign(0.35, lx), ly, 4.62),
                    mats["sodium"])
        lamps.append(head)
    parts["lamps"] = lamps

    # --- pier rails (the outboard ±6.2 lines -- NO barricades needed,
    # CROWD_X_RANGE keeps the crowd inboard by construction) ------------
    rails = []
    for sgn in (-1, 1):
        rails.append(_box(f"TF.PierRail{'W' if sgn < 0 else 'E'}", 0.09,
                          DECK_Y1 - 2.0, 0.09,
                          (sgn * 6.2, (2.0 + DECK_Y1) / 2, 1.05),
                          mats["steel"]))
    parts["pier_rails"] = rails

    # --- bollards (declared) + crates (dressing, outboard) -------------
    bollards = []
    for bx in (-4.5, 4.5):
        for by in (8.0, 14.0, 20.0, 26.0):
            bollards.append(_prim("cyl", (0.5, 0.85), (bx, by, 0.42),
                                  mat=mats["steel"], verts=14))
    parts["bollards"] = bollards
    crates = []
    for i, (cx, cy, s) in enumerate(((-8.6, 10.0, 1.1), (-9.2, 12.4, 0.8),
                                     (8.8, 18.0, 1.2), (9.4, 20.2, 0.9),
                                     (8.4, 30.0, 1.0))):
        crates.append(_box(f"TF.Crate{i + 1}", s, s, s,
                           (cx, cy, s / 2), mats["crate"]))
    parts["crates"] = crates

    # --- the maintenance gate (S9's rail gap, NORTH of the capacity
    # box: y 7-9 on the EAST rail -- nothing routes there; verify on
    # the flow strip) ----------------------------------------------------
    gate = _box("TF.MaintGate", 0.9, 0.08, 1.05, (6.2, 8.0, 0.55),
                mats["steel"])
    parts["maint_gate"] = gate

    # --- night sky (L-TF4, ladder step 1: 0.04 measured DEAD — the
    # silhouette floor; sun BELOW the horizon for twilight blue) -------
    # s26 CYCLES RE-TUNE (DESIGN_world_retune_s26 A7/D1-c; the eye-gate
    # finding: the certified 0.12 renders FLAT GRAY under Cycles — the
    # Nishita atmosphere stays luminous at sun -6 deg while EEVEE goes
    # near-black). Engine-conditional: the certified EEVEE value is
    # untouched; Cycles drops the sky so the sodium practicals own the
    # night again.
    #   BOTH-ENGINE DELTA (measured s26, tferry S6 cylinder repro):
    #   EEVEE strength 0.12 -> near-black sky + sodium pools (certified
    #   tferry_1 look); Cycles strength 0.12 -> flat ~#8a8a8a wash
    #   (broken); Cycles strength 0.012 -> near-black + pools (the
    #   tune below; converges toward the tferry_1 corpus).
    from blender_kit import add_sky_world, normalize_engine_id
    _cycles = normalize_engine_id(
        scene.render.engine).startswith("CYCLES")
    add_sky_world(sun_elevation_deg=-6.0, sun_rotation_deg=200.0,
                  strength=0.012 if _cycles else 0.12)

    # --- the PRACTICALS (the f486 lesson: emissive materials glow but
    # do not LIGHT — every neon/lamp/window needs a real light object) --
    lights = []
    sodium = (1.0, 0.60, 0.22)

    # s26 CYCLES LIGHT COMPENSATION: the certified EEVEE energies read
    # ~2/3 dimmer under Cycles at the same wattage (measured S1/S3/S6
    # probes: the sodium pools barely fired while the sky fix read).
    # EEVEE untouched; Cycles x3.5 on every practical (2.2 measured still dim vs the tferry_1 corpus; 3.5 = the pool ladder's second rung) (the BOTH-ENGINE
    # delta lives in the sky block above).
    _cyc = normalize_engine_id(
        scene.render.engine).startswith("CYCLES")
    _lw = 3.5 if _cyc else 1.0

    def _spot(name, loc, energy, color, size_deg, blend):
        ld = bpy.data.lights.new(name, type='SPOT')
        ld.energy = energy * _lw
        ld.color = color
        ld.spot_size = math.radians(size_deg)
        ld.spot_blend = blend
        ld.shadow_soft_size = 0.25
        ob = bpy.data.objects.new(name, ld)
        ob.location = loc
        scene.collection.objects.link(ob)
        return ob

    def _area(name, loc, energy, color, size, size_y=None):
        energy = energy * _lw
        ld = bpy.data.lights.new(name, type='AREA')
        ld.energy = energy
        ld.color = color
        ld.shape = 'RECTANGLE' if size_y else 'SQUARE'
        ld.size = size
        if size_y:
            ld.size_y = size_y
        ob = bpy.data.objects.new(name, ld)
        ob.location = loc
        scene.collection.objects.link(ob)
        return ob

    # sodium lamp spots (down-cones onto the deck lanes). The east
    # 17.5 pool fills the y16-22 gap the S5 run lane crosses (the
    # eevee round: the Latecomer's mid-run stretch read murky)
    for i, (lx, ly) in enumerate(((-5.6, 8.0), (5.6, 12.0),
                                  (-5.6, 20.0), (5.6, 24.0),
                                  (-5.6, 32.0), (5.6, 34.0),
                                  (5.6, 17.5), (5.6, 7.0))):
        lights.append(_spot(f"TF.LampSpot{i + 1}",
                            (lx - math.copysign(0.35, lx), ly, 4.5),
                            420.0 if i == 1 else 320.0, sodium,
                            110.0 if i == 1 else 95.0, 0.35))
    # a sodium cone OVER THE GANGWAY itself (the S6/S8 EEVEE pass: the
    # pile read as black lumps -- the throat had no diegetic light of
    # its own; the queue + the Deckhand's callers need the pool)
    lights.append(_spot("TF.GangSpot", (0.0, 2.3, 4.4), 200.0,
                        sodium, 80.0, 0.4))
    # the maintenance gate's WORK LIGHT (the S9 beat happens HERE in
    # the dark east margin -- the crossing drowned at night; a work
    # light over the gate is diegetic and owns the beat)
    lights.append(_spot("TF.GateWorkLight", (6.2, 8.0, 3.6), 140.0,
                        sodium, 75.0, 0.45))
    # the neon spill over the throat (cyan bar + magenta kiosk).
    # f486 lesson: 42W CYAN flooded the amber Deckhand to GREEN —
    # spill energy stays LOW and the tilt steep (graze the deck,
    # never the hero's torso; amber + cyan = green mush).
    cyan_spill = _area("TF.NeonCyanSpill", (0.0, 0.9, 3.3), 14.0,
                       (0.10, 0.80, 0.95), 4.4, 0.5)
    cyan_spill.rotation_euler = (math.radians(58), 0.0, 0.0)
    mag_spill = _area("TF.NeonMagSpill", (3.1, 4.1, 2.0), 8.0,
                      (0.95, 0.12, 0.45), 1.2, 0.4)
    mag_spill.rotation_euler = (math.radians(-60), 0.0, 0.0)
    lights += [cyan_spill, mag_spill]
    # the ferry's warm interior wash over the apron (the recede beat's
    # key light source south of the throat)
    win_wash = _area("TF.FerryWash", (0.0, -2.9, 3.0), 130.0,
                     (1.0, 0.66, 0.30), 7.0, 1.2)
    win_wash.rotation_euler = (math.radians(-15), 0.0, 0.0)
    lights.append(win_wash)
    # a dim deck fill so silhouettes never fully die (L-TF4 ladder:
    # practicals model the crowd before exposure moves). f486 lesson 2:
    # a BLUE fill + the cyan bar swamped the amber hero to GREEN — the
    # fill goes neutral-cool gray and drops to 40W. The aerial
    # establish (S1) needed 70W: at 40 the pier shape read black from
    # above (the eevee round).
    fill = _area("TF.DeckFill", (0.0, 18.0, 12.0), 70.0,
                 (0.42, 0.45, 0.50), 20.0, 30.0)
    lights.append(fill)
    # the Deckhand's CHECKPOINT LANTERN (diegetic warm anchor at the
    # throat — the green-cast fix: his amber needs a warm key of its
    # own, the cyan bar alone owned his local environment)
    lantern = _area("TF.CheckpointLantern", (0.55, 1.35, 2.55), 45.0,
                    (1.0, 0.60, 0.26), 0.7, 0.7)
    lantern.rotation_euler = (math.radians(38), 0.0, math.radians(160))
    lights.append(lantern)
    parts["lights"] = lights

    return parts
