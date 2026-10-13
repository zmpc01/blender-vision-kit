"""tgreen_world.py -- GREEN LIGHT's set: the mid-afternoon city crossing.

Self-contained bpy; materials via tdawn_actors.make_material (the
F-TD11 emission params). The two signal glyphs are this film's decouple
consumers: near-black base + saturated Emission Color at strength 3.9
(the REV-2 F11 NOON ceiling -- the night 1.1-1.3 distance ladder does
NOT transfer to daylight ambient).

Coordinate frame (REV-3): street level z=0; asphalt slab x -30..30 /
y -9..9; curbs N (y 3.2) + S (y -6.0) h 0.15; sidewalks beyond. The
SIM walkable is y -6..5.0 (F17) -- this module is DRESSING ONLY, zero
sim barricades in this film. The granite plaza apron (9x9, h 0.10 at
the origin) dresses the capacity freeze square (+-5) from the INSIDE:
the frozen crowd ring forms just off its rim. Zebra: 6 bars at
x +-6/+-12/+-18 (the spec's self-correction -- drop the x=0 bar, pull
the apron in to 9x9, so bars never overlap the apron), alternating the
two worn-paint whites (F10's 0.78/0.64 albedo rungs). TWO signal posts
at the CURB LIPS (NW (-4.2, 3.35) facing south, SE (4.2, -6.15)
facing north; the contract's sim keepout rows stay at
(-4.2, 2.8)/(4.2, -2.8) -- deliberately not mirrored here). E/W facade
blocks x +-28..34, h 11 carry the F9 shade wedge: sun 40 deg from WSW
(azimuth bearing 235) throws the W block's roof shadow 11/tan(40) =
13.1 m ENE, shading x -28..-17.3 -- the west third of the street.

Ladder protocol (F10/F11): TG_SUN_STRENGTH / TG_SKY_STRENGTH are
module CONSTANTS so the scene module sweeps the ladder by override
BEFORE build_world:
    import tgreen_world; tgreen_world.TG_SUN_STRENGTH = 2.0

Deviations from the build spec (recorded): the bus static moves from
x -27.0 to x -23.0 -- a 10 m body centered at -27 spans -32..-22 and
buries 4 m inside the W facade block (x -34..-28); the west end now
now stands 7m clear of the W facade face (x -30). Everything else is spec-literal.
"""
from __future__ import annotations

import math

import bpy
from mathutils import Vector

from tdawn_actors import make_material

# --- the daylight ladder (F10 sun 2.0/3.0/4.0 at sky 0.5; F11 glyph
# strength lives in the materials, swept by the scene module) --------
TG_SUN_STRENGTH = 5.0     # the ladder winner (sun5/sky0.15: deepest shadows, the two-tone read)
TG_SKY_STRENGTH = 0.15    # the ladder winner (the ambient was the wash: p95-p50 0.07 at 0.5)
TG_SUN_ELEV_DEG = 40.0    # 3-4pm light (F9)
TG_SUN_AZ_DEG = 235.0     # WSW bearing -> shadows fall ENE (~55 deg)

# --- set frame (meters; z=0 street level) ----------------------------
STREET_X, STREET_Y = 30.0, 9.0        # slab x -30..30 / y -9..9
WALK_Y0, WALK_Y1 = -6.0, 5.0          # the SIM walkable (reference only)
ZEBRA_XS = (-18.0, -12.0, -6.0, 6.0, 12.0, 18.0)   # spec-chosen 6 bars
APRON_HW = 4.5                        # 9x9 plaza apron (clear of +-6 bars)
POST_NW = (-4.2, 3.35)                # N curb/sidewalk lip
POST_SE = (4.2, -6.15)                # S curb/sidewalk lip
FACADE_X0, FACADE_X1 = 30.0, 36.0     # |x| band (moved 28->30: the 3-f
                                      # review find -- the spawn strips run
                                      # to |x|=30 and ~30 agents embedded in
                                      # the 28-band facades, walking out
                                      # through walls in the GLB first act)
FACADE_H = 11.0
BUS_CENTER = (-23.0, -7.5)            # spec -27.0 buried the bus in the W
                                      # facade; west end abuts x -28 instead


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
    # NOTE vs tferry: per-kind kwargs (uv_sphere takes segments/ring_count,
    # NOT vertices) and a name arg -- the TG.<Something> naming law means
    # every created object is explicitly named here.
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


def _join_pieces(pieces, name):
    """Join silhouette pieces into ONE mesh per glyph.

    The scale-key law (F8): the scene module keys 0.001<->1.0 on the
    returned object, so the rest state MUST be object scale (1,1,1)
    (source-piece scales are applied into the mesh) with the origin at
    the plate center (origin_set MEDIAN) -- otherwise the scale keys
    would distort the silhouette or shrink it toward a stale origin."""
    bpy.ops.object.select_all(action='DESELECT')
    for ob in pieces:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = pieces[0]
    if len(pieces) > 1:
        bpy.ops.object.join()
    ob = bpy.context.active_object
    bpy.ops.object.transform_apply(location=False, rotation=False,
                                   scale=True)
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')
    ob.name = name
    return ob


def _build_materials():
    """The F12 palette (albedo, linear) + the F11 glyph decouple."""
    m = {}
    # the road layer
    m["asphalt"] = make_material("TG.Asphalt", (0.10, 0.10, 0.11), 0.95)
    m["sidewalk"] = make_material("TG.Sidewalk", (0.26, 0.25, 0.24), 0.9)
    m["curb"] = make_material("TG.Curb", (0.22, 0.22, 0.21), 0.85)
    # TWO worn-paint whites (F10: 0.78/0.64 ALTERNATING -- the
    # blow-out ladder needs the two tones; the drop path 0.72/0.62
    # re-keys these materials, not the meshes)
    m["stripe_a"] = make_material("TG.StripeA", (0.78, 0.78, 0.76), 0.85)
    m["stripe_b"] = make_material("TG.StripeB", (0.64, 0.64, 0.62), 0.85)
    # the plaza (dressing only -- F17)
    m["granite"] = make_material("TG.Granite", (0.30, 0.29, 0.28), 0.7)
    m["granite_dark"] = make_material("TG.GraniteDark", (0.24, 0.24, 0.23),
                                      0.7)
    m["hatch"] = make_material("TG.Hatch", (0.60, 0.60, 0.58), 0.85)
    # the shade-wedge facades
    m["facade"] = make_material("TG.Facade", (0.34, 0.31, 0.28), 0.8)
    m["glass"] = make_material("TG.Glass", (0.03, 0.035, 0.045), 0.2)
    # the signal spine (F8)
    m["housing"] = make_material("TG.Housing", (0.02, 0.02, 0.02), 0.4)
    m["pole"] = make_material("TG.PoleSteel", (0.35, 0.36, 0.38), 0.5)
    # the F-TD11 decouple: DARK base + saturated Emission Color at 3.9
    # (F11 noon ladder 1.9/3.9/5.5 -- the scene module re-keys these)
    m["glyph_walk"] = make_material(
        "TG.Glyph.Walk", (0.02, 0.05, 0.03), 0.4,
        emission_color=(0.08, 0.62, 0.22), emission_strength=3.9)
    m["glyph_hand"] = make_material(
        "TG.Glyph.Hand", (0.06, 0.03, 0.01), 0.4,
        emission_color=(0.90, 0.38, 0.05), emission_strength=3.9)
    # the W-end bus static + bollard steel
    m["bus_body"] = make_material("TG.BusBody", (0.75, 0.74, 0.72), 0.5)
    m["bus_win"] = make_material("TG.BusWin", (0.04, 0.05, 0.06), 0.25)
    m["bollard"] = make_material("TG.Bollard", (0.30, 0.31, 0.33), 0.6)
    # the grounding plane (the eye round's find: beyond the set the
    # void rendered as an OCEAN HORIZON at street level -- S6/S7/S10
    # read 'coastal boulevard' unintentionally). A huge neutral plane
    # grounds the set; the horizon becomes hazy city-edge.
    m["ground"] = make_material("TG.Ground", (0.085, 0.085, 0.09), 0.95)
    return m


def _walk_glyph(name, cx, cy, zc, mat):
    """The green MAN silhouette: sphere head + torso + two legs, joined."""
    pieces = [_box(name + ".Torso", 0.14, 0.03, 0.16, (cx, cy, zc + 0.01),
                   mat)]
    pieces.append(_prim("sph", (0.14,), (cx, cy, zc + 0.17), mat=mat,
                        verts=16, name=name + ".Head"))
    for sgn, tag in ((-1, "L"), (1, "R")):
        pieces.append(_box(f"{name}.Leg{tag}", 0.05, 0.03, 0.11,
                           (cx + sgn * 0.033, cy, zc - 0.125), mat))
    return _join_pieces(pieces, name)


def _hand_glyph(name, cx, cy, zc, mat):
    """The orange HAND silhouette: flat palm + 4 fingers, joined (crude)."""
    pieces = [_box(name + ".Palm", 0.16, 0.02, 0.14, (cx, cy, zc), mat)]
    for i, fx in enumerate((-0.057, -0.019, 0.019, 0.057)):
        pieces.append(_box(f"{name}.F{i + 1}", 0.03, 0.02, 0.06,
                           (cx + fx, cy, zc + 0.10), mat))
    return _join_pieces(pieces, name)


def build_world(scene):
    """Build the crossing set; returns the parts dict."""
    mats = _build_materials()
    glyphs = {}
    pre = set(scene.objects.keys())

    # --- the street slab (top at z=0) ----------------------------------
    _box("TG.Street", STREET_X * 2, STREET_Y * 2, 0.1,
         (0.0, 0.0, -0.05), mats["asphalt"])
    # the grounding plane UNDER everything (the ocean-horizon fix)
    _box("TG.GroundPlane", 500.0, 500.0, 0.02, (0.0, 0.0, -0.13),
         mats["ground"])

    # --- the zebra (6 longitudinal bars, y -2.2..2.2, h 0.012 on the
    # asphalt; the two worn whites ALTERNATE per bar -- F10) ------------
    for i, zx in enumerate(ZEBRA_XS):
        _box(f"TG.Zebra.{i + 1}", 0.6, 4.4, 0.012, (zx, 0.0, 0.006),
             mats["stripe_a"] if i % 2 == 0 else mats["stripe_b"])

    # --- curbs (h 0.15, top z 0.15) + sidewalks -------------------------
    _box("TG.CurbN", STREET_X * 2, 0.3, 0.15, (0.0, 3.2, 0.075),
         mats["curb"])
    _box("TG.CurbS", STREET_X * 2, 0.3, 0.15, (0.0, -6.0, 0.075),
         mats["curb"])
    _box("TG.SidewalkN", STREET_X * 2, 9.0 - 3.35, 0.15,
         (0.0, (3.35 + 9.0) / 2, 0.075), mats["sidewalk"])
    _box("TG.SidewalkS", STREET_X * 2, -6.15 - (-9.0), 0.15,
         (0.0, (-9.0 + -6.15) / 2, 0.075), mats["sidewalk"])

    # --- THE PLAZA (dressing only, F17: the freeze square +-5 is the
    # protection; the apron dresses it from the inside). 9x9 sits clear
    # of the +-6 zebra bars; the curb ridge pokes 0.05 through its north
    # band -- accepted dressing artifact, the sim never touches it ------
    _box("TG.PlazaApron", APRON_HW * 2, APRON_HW * 2, 0.10,
         (0.0, 0.0, 0.05), mats["granite"])
    # hatch border: 4 flat strips 0.3 wide on the asphalt (z 0.012)
    _box("TG.Hatch.N", APRON_HW * 2 + 0.6, 0.3, 0.012,
         (0.0, APRON_HW + 0.15, 0.006), mats["hatch"])
    _box("TG.Hatch.S", APRON_HW * 2 + 0.6, 0.3, 0.012,
         (0.0, -(APRON_HW + 0.15), 0.006), mats["hatch"])
    _box("TG.Hatch.E", 0.3, APRON_HW * 2, 0.012,
         (APRON_HW + 0.15, 0.0, 0.006), mats["hatch"])
    _box("TG.Hatch.W", 0.3, APRON_HW * 2, 0.012,
         (-(APRON_HW + 0.15), 0.0, 0.006), mats["hatch"])
    # the statue PLINTH only -- the hero statue is the scene module's
    _box("TG.Plinth", 1.2, 1.2, 0.22, (0.0, 0.0, 0.21),
         mats["granite_dark"])   # top z 0.32

    # --- the TWO signal posts at the curb lips (F13/NW-SE) --------------
    # NW (-4.2, 3.35) faces SOUTH; SE (4.2, -6.15) faces NORTH. The
    # contract's keepout rows at (-4.2, 2.8)/(4.2, -2.8) are the sim's
    # business, not this module's. Pole bases bury into curb/apron --
    # standard previz dressing.
    for tag, (px, py) in (("NW", POST_NW), ("SE", POST_SE)):
        _prim("cyl", (0.12, 2.6), (px, py, 1.3), mat=mats["pole"],
              verts=12, name=f"TG.SignalPole.{tag}")
        _box(f"TG.SignalHead.{tag}", 0.5, 0.3, 0.7, (px, py, 2.55),
             mats["housing"])
    # glyph plates: flat silhouettes 0.02 thick, mounted 5 mm off the
    # head's road-facing face (NW face y 3.20 -> plates at y 3.185; SE
    # face y -6.00 -> plates at y -5.985). Walk above, hand below; the
    # SCENE MODULE scale-keys these four (F8: 0.001<->1.0).
    glyphs["walk_nw"] = _walk_glyph("TG.WalkGlyph.NW", POST_NW[0], 3.185,
                                    2.66, mats["glyph_walk"])
    glyphs["hand_nw"] = _hand_glyph("TG.HandGlyph.NW", POST_NW[0], 3.185,
                                    2.34, mats["glyph_hand"])
    glyphs["walk_se"] = _walk_glyph("TG.WalkGlyph.SE", POST_SE[0], -5.985,
                                    2.66, mats["glyph_walk"])
    glyphs["hand_se"] = _hand_glyph("TG.HandGlyph.SE", POST_SE[0], -5.985,
                                    2.34, mats["glyph_hand"])

    # --- the facades (the F9 shade wedge): E/W blocks x +-30..36 ---
    _box("TG.Facade.E", FACADE_X1 - FACADE_X0, STREET_Y * 2, FACADE_H,
         ((FACADE_X0 + FACADE_X1) / 2, 0.0, FACADE_H / 2), mats["facade"])
    _box("TG.Facade.W", FACADE_X1 - FACADE_X0, STREET_Y * 2, FACADE_H,
         (-(FACADE_X0 + FACADE_X1) / 2, 0.0, FACADE_H / 2), mats["facade"])
    # window grids: 3 storeys x 8 per street-facing face (48 plates),
    # 1.4 x 1.6 glass, 0.02 thick, floating 5 mm off the surface
    for sgn, side in ((1, "E"), (-1, "W")):
        face_x = sgn * FACADE_X0
        for si, wz in enumerate((2.2, 5.2, 8.2)):
            for k in range(8):
                wy = -7.875 + k * 2.25
                _box(f"TG.Win.{side}{si}{k}", 0.02, 1.4, 1.6,
                     (face_x - sgn * 0.015, wy, wz), mats["glass"])

    # --- the bus static (dressing, S margin OUTSIDE the walkable).
    # DEVIATION: spec x -27.0 puts a 10 m body 4 m inside the W facade
    # block; centered at -23.0 the west end abuts the facade face.
    _box("TG.BusBody", 10.0, 2.5, 3.0,
         (BUS_CENTER[0], BUS_CENTER[1], 0.15 + 1.5), mats["bus_body"])
    _box("TG.BusWinN", 8.6, 0.06, 1.0,
         (BUS_CENTER[0], BUS_CENTER[1] + 1.28, 2.4), mats["bus_win"])
    _box("TG.BusWinS", 8.6, 0.06, 1.0,
         (BUS_CENTER[0], BUS_CENTER[1] - 1.28, 2.4), mats["bus_win"])

    # --- bollards: both curb lips, x -28..28 every 4.0 (15 + 15) --------
    for by, tag in ((3.35, "N"), (-6.15, "S")):
        for i, bx in enumerate(range(-28, 29, 4)):
            _prim("cyl", (0.16, 0.9), (float(bx), by, 0.6),
                  mat=mats["bollard"], verts=12,
                  name=f"TG.Bollard.{tag}{i:02d}")

    # --- the SUN (the film is DAYLIGHT -- the anti-tferry): a real SUN
    # lamp at 40 deg elevation from WSW (bearing 235). The lamp's -Z is
    # aimed along the light travel vector (ENE + down), so shadows fall
    # ENE and the W facades shade the west third (13.1 m wedge).
    # energy = TG_SUN_STRENGTH (module constant -- the ladder override
    # must reach the lamp, hence read at CALL time, not def time).
    ld = bpy.data.lights.new("TG.Sun", type='SUN')
    ld.energy = TG_SUN_STRENGTH * 1.0
    ld.angle = math.radians(1.0)          # crisper edges (the ladder find: 2 deg read too soft at 16m)
    ld.color = (1.0, 0.96, 0.90)
    sun_ob = bpy.data.objects.new("TG.Sun", ld)
    sun_ob.location = (-18.0, -12.0, 14.0)   # label-only (direction-only)
    scene.collection.objects.link(sun_ob)
    elev = math.radians(TG_SUN_ELEV_DEG)
    az = math.radians(TG_SUN_AZ_DEG)
    to_sun = Vector((math.sin(az) * math.cos(elev),
                     math.cos(az) * math.cos(elev),
                     math.sin(elev)))
    sun_ob.rotation_euler = (-to_sun).to_track_quat('-Z', 'Y').to_euler()

    # --- the DAYLIGHT sky (kit helper; strength 0.5 so sky:sun = 0.5:3.0
    # and the sun owns the shadows -- F10's ladder anchor) --------------
    from blender_kit import add_sky_world
    add_sky_world(sun_elevation_deg=TG_SUN_ELEV_DEG,
                  sun_rotation_deg=TG_SUN_AZ_DEG,
                  strength=TG_SKY_STRENGTH)
    # KILL THE SKY'S OWN SUN DISC (the first ladder's find): the
    # MULTIPLE_SCATTERING disc is physically brilliant -- its irradiance
    # washed every frame pastel and dwarfed the lamp (the sun 2->4 ladder
    # moved mean luma 0.707->0.724, i.e. nothing). The TG.Sun lamp is
    # the SOLE direct light; the sky is atmosphere-only fill.
    if scene.world and scene.world.use_nodes:
        for n in scene.world.node_tree.nodes:
            if n.type == 'TEX_SKY' and hasattr(n, 'sun_disc'):
                n.sun_disc = False
                print(f"[tgreen_world] sky sun_disc -> off "
                      f"({n.sky_type})")

    bpy.context.view_layer.update()
    created = [ob for ob in scene.objects if ob.name not in pre]
    return {"parts": created, "glyphs": glyphs, "sun": sun_ob,
            "mats": mats}
