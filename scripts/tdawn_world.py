"""tdawn_world.py -- the TERMINAL DAWN set: a grand concourse hall.

Geometry (REV-2, matched to tdawn_contract):
  floor slab   x -12..12, y -8..32 (the walkable is x -10..10, y -6..27)
  side walls   x = +/-12, z 0..9
  far wall     y = 32 (holds the departure board + the incident windows)
  roof         open steel arches every 4 m + purlins (NO glass plane --
               the HDRI/sun light the hall naturally and Workbench
               stays readable; a glass surface would need transmission
               and would render opaque in workbench)
  the GATE     at y = 0 (the crowd's pursue target, origin): portal
               frame + emissive surround + two seal doors + dark
               threshold; the gate plaza = the sim's +/-5 m capacity box
  colonnades   x = +/-7 every 4 m (declared BARRICADES in the contract)
  dressing     benches, signage pylons, 3 luggage carts (the RB
               placeholders), far-end windows (the incident glow)

Naming hygiene: NO object/material name may match mist|fog|haze|atmo
(the exporter's atmosphere-exclusion regex would drop it from the GLB).

bpy-only, self-contained (D-TD6).
"""
from __future__ import annotations

import math

import bpy

from tdawn_actors import make_material

HALL_X = 12.0
HALL_Y0 = -8.0
HALL_Y1 = 32.0
WALL_H = 9.0
COLONNADE_X = 7.0
COLONNADE_YS = (6.0, 10.0, 14.0, 18.0, 22.0, 26.0)

# dawn key light
SUN_ELEV_DEG = 11.0
SUN_AZI_DEG = 115.0        # from the +x/-y quadrant: light rakes +y/-x
SUN_ENERGY = 4.0
SKY_STRENGTH = 0.4         # gotcha 128: 1.0 blows out EEVEE interiors


def _prim(kind, name, size, loc, rot=(0.0, 0.0, 0.0), mat=None,
          verts=16, coll=None):
    fn = {"cyl": bpy.ops.mesh.primitive_cylinder_add,
          "sph": bpy.ops.mesh.primitive_uv_sphere_add,
          "cube": bpy.ops.mesh.primitive_cube_add,
          "plane": bpy.ops.mesh.primitive_plane_add}[kind]
    kw = {"location": loc, "rotation": rot}
    if kind == "cyl":
        kw.update(radius=size[0], depth=size[1], vertices=verts)
    elif kind == "sph":
        kw.update(radius=size, segments=verts, ring_count=max(6, verts // 2))
    elif kind == "plane":
        kw.update(size=size)
    elif kind == "cube":
        # primitive_cube_add.size is a FLOAT (edge length); exact dims
        # come from scale on a unit cube
        kw.update(size=1.0)
    fn(**kw)
    ob = bpy.context.view_layer.objects.active
    if kind == "cube":
        ob.scale = (size[0], size[1], size[2])
    ob.name = name
    if mat is not None:
        ob.data.materials.append(mat)
    return ob


def _box(name, sx, sy, sz, loc, mat, rot=(0.0, 0.0, 0.0)):
    """Cube scaled to exact dims (size kwarg is FULL size for cubes)."""
    return _prim("cube", name, (sx, sy, sz), loc, rot=rot, mat=mat)


def _build_materials():
    m = {}
    m["floor"] = make_material("TD.Stone", (0.230, 0.205, 0.182), 0.88)
    m["floor2"] = make_material("TD.StoneDark", (0.145, 0.132, 0.120), 0.9)
    m["wall"] = make_material("TD.Wall", (0.196, 0.180, 0.164), 0.85)
    m["steel"] = make_material("TD.Steel", (0.088, 0.092, 0.100), 0.45,
                               metallic=0.7)
    m["gate_glow"] = make_material("TD.GateGlow", (1.0, 0.88, 0.70), 0.4)
    m["gate_dark"] = make_material("TD.GateDark", (0.050, 0.036, 0.026),
                                   0.9)
    m["board"] = make_material("TD.Board", (0.55, 0.28, 0.05), 0.5)
    m["wood"] = make_material("TD.Wood", (0.145, 0.098, 0.062), 0.8)
    m["window"] = make_material("TD.WindowGlow", (0.85, 0.62, 0.38), 0.5)
    return m


def build_world(scene):
    """Build the hall; returns a ctx dict of everything created."""
    mats = _build_materials()
    parts = {}

    # --- floor (two tones: plaza slab + main field; BOTH tops at z=0
    # -- the validator reads the z=0 floor plane) ----------------------
    parts["floor_plaza"] = _box(
        "TD.FloorPlaza", 10.4, 11.0, 0.08, (0.0, 0.5, -0.04),
        mats["floor2"])
    parts["floor"] = _box(
        "TD.Floor", HALL_X * 2 + 0.4, HALL_Y1 - HALL_Y0 + 0.4, 0.08,
        (0.0, (HALL_Y0 + HALL_Y1) / 2, -0.04), mats["floor"])
    # plaza inlay ring (the gate threshold marking)
    for r, w in ((5.2, 0.16), (5.6, 0.08)):
        ring = _prim("cyl", f"TD.PlazaRing{int(r*10)}", (r, w),
                     (0.0, 0.0, 0.012), mat=mats["floor"], verts=48)
        ring.data.materials.clear()
        ring.data.materials.append(mats["floor2"])
        parts[f"ring_{r}"] = ring

    # --- side walls + far wall ----------------------------------------
    hall_len = HALL_Y1 - HALL_Y0
    parts["wall_left"] = _box(
        "TD.WallLeft", 0.4, hall_len, WALL_H,
        (-HALL_X - 0.2, (HALL_Y0 + HALL_Y1) / 2, WALL_H / 2),
        mats["wall"])
    parts["wall_right"] = _box(
        "TD.WallRight", 0.4, hall_len, WALL_H,
        (HALL_X + 0.2, (HALL_Y0 + HALL_Y1) / 2, WALL_H / 2),
        mats["wall"])
    parts["wall_far"] = _box(
        "TD.WallFar", HALL_X * 2 + 0.8, 0.4, WALL_H,
        (0.0, HALL_Y1 + 0.2, WALL_H / 2), mats["wall"])
    # near wall behind the gate (the gate is IN it)
    parts["wall_near"] = _box(
        "TD.WallNear", HALL_X * 2 + 0.8, 0.4, WALL_H,
        (0.0, HALL_Y0 - 0.2, WALL_H / 2), mats["wall"])

    # --- far-end windows (the incident glow, S2+) ----------------------
    win = []
    for i, wx in enumerate((-6.0, -2.0, 2.0, 6.0)):
        win.append(_box(
            f"TD.FarWindow{i + 1}", 3.0, 0.12, 3.4,
            (wx, HALL_Y1 - 0.05, 4.6), mats["window"]))
    parts["far_windows"] = win

    # --- the GATE at y=0 (faces +Y, toward the crowd) ------------------
    gw = 3.4          # portal half-width of the opening
    gh = 3.6          # opening height
    gate = {}
    # emissive surround: two jambs + header
    gate["jamb_l"] = _box("TD.GateJambL", 0.5, 0.9, gh + 0.5,
                          (-gw - 0.25, 0.0, (gh + 0.5) / 2),
                          mats["gate_glow"])
    gate["jamb_r"] = _box("TD.GateJambR", 0.5, 0.9, gh + 0.5,
                          (gw + 0.25, 0.0, (gh + 0.5) / 2),
                          mats["gate_glow"])
    gate["header"] = _box("TD.GateHeader", gw * 2 + 1.5, 0.9, 0.55,
                          (0.0, 0.0, gh + 0.28), mats["gate_glow"])
    # dark threshold (the depth beyond the gate)
    gate["void"] = _box("TD.GateVoid", gw * 2, 1.2, gh,
                        (0.0, -0.85, gh / 2), mats["gate_dark"])
    # seal doors: two panels sliding from the jambs (S9-S10 animation
    # keys them across the opening)
    gate["door_l"] = _box("TD.GateDoorL", gw, 0.22, gh,
                          (-gw / 2, 0.0, gh / 2), mats["gate_dark"])
    gate["door_r"] = _box("TD.GateDoorR", gw, 0.22, gh,
                          (gw / 2, 0.0, gh / 2), mats["gate_dark"])
    # doors START open (parked inside the jambs, hidden in the wall)
    for d, sx in ((gate["door_l"], -1.0), (gate["door_r"], 1.0)):
        d.location.x = sx * (gw + gw / 2)
        d.keyframe_insert(data_path="location", index=0, frame=1)
    parts["gate"] = gate

    # --- colonnades (match contract BARRICADES x=+/-7) -----------------
    cols = []
    for sx in (-1.0, 1.0):
        for i, cy in enumerate(COLONNADE_YS):
            c = _prim("cyl", f"TD.Column{'L' if sx < 0 else 'R'}{i + 1}",
                      (0.55, WALL_H), (sx * COLONNADE_X, cy, WALL_H / 2),
                      mat=mats["steel"], verts=20)
            cols.append(c)
    parts["columns"] = cols

    # --- roof arches + purlins (open steel, no glass) -------------------
    arches = []
    n_arch = int((HALL_Y1 - HALL_Y0) / 4.0) + 1
    for i in range(n_arch):
        ay = HALL_Y0 + i * 4.0
        arch = _prim("torus" if False else "cyl",
                     f"TD.Arch{i + 1:02d}", (0.16, HALL_X * 2 - 0.4),
                     (0.0, ay, WALL_H + 0.55),
                     rot=(0.0, math.pi / 2, 0.0), mat=mats["steel"],
                     verts=10)
        arches.append(arch)
    for i, py in enumerate((-0.0, 4.0, 8.0)):
        pass
    parts["arches"] = arches
    # ridge purlins along y (3 lines)
    purlins = []
    for pz in (WALL_H + 0.15, WALL_H + 0.55):
        for px in (-6.0, 0.0, 6.0):
            purlins.append(_prim(
                "cyl", f"TD.Purlin{int(px)}_{int(pz * 10)}",
                (0.09, hall_len), (px, (HALL_Y0 + HALL_Y1) / 2, pz),
                rot=(math.pi / 2, 0.0, 0.0), mat=mats["steel"], verts=8))
    parts["purlins"] = purlins

    # --- dressing: benches + signage pylons + carts ---------------------
    benches = []
    for i, (bx, by, rot) in enumerate((
            (-4.6, 12.0, 0.0), (4.6, 12.0, 0.0),
            (-4.6, 20.0, 0.0), (4.6, 20.0, 0.0))):
        benches.append(_box(f"TD.Bench{i + 1}", 2.6, 0.55, 0.10,
                            (bx, by, 0.48),
                            rot=(0.0, 0.0, rot), mat=mats["wood"]))
        for lx in (-1.1, 1.1):
            _prim("cyl", f"TD.BenchLeg{i}_{int(lx * 10)}",
                  (0.06, 0.46), (bx + lx, by, 0.23), mat=mats["steel"],
                  verts=8)
    parts["benches"] = benches

    pylons = []
    for i, (px, py) in enumerate(((-3.2, 8.6), (3.2, 8.6), (0.0, 24.0))):
        pylons.append(_box(f"TD.Pylon{i + 1}", 0.5, 0.24, 2.6,
                           (px, py, 1.3), mats["steel"]))
    parts["pylons"] = pylons

    # the 3 RB-placeholder luggage carts (grounded, static, plaza edge)
    carts = []
    for i, (cx, cy) in enumerate(((-4.4, 3.4), (4.5, 3.6), (-4.8, 5.2))):
        cart = _box(f"TD.Cart{i + 1}", 0.9, 0.62, 0.55,
                    (cx, cy, 0.28), mats["steel"])
        handle = _prim("cyl", f"TD.CartHandle{i + 1}", (0.03, 0.8),
                       (cx, cy - 0.45, 0.75),
                       rot=(math.pi / 2.6, 0.0, 0.0), mat=mats["steel"],
                       verts=8)
        carts.append((cart, handle))
    parts["carts"] = carts

    # --- lights --------------------------------------------------------
    sun = bpy.data.lights.new("TD.Sun", type="SUN")
    sun.energy = SUN_ENERGY
    sun.angle = math.radians(1.2)
    sun_ob = bpy.data.objects.new("TD.Sun", sun)
    scene.collection.objects.link(sun_ob)
    elev = math.radians(SUN_ELEV_DEG)
    azi = math.radians(SUN_AZI_DEG)
    # point the sun FROM (sin azi*cos elev, -cos azi*cos elev, -sin elev)
    # direction vector (light travels along -Z of its rotation)
    sun_ob.rotation_euler = (
        math.pi / 2 - elev, 0.0, math.pi - azi)
    sun_ob.location = (10.0, -6.0, 12.0)
    parts["sun"] = sun_ob

    # gate fill: an area light inside the portal (the goal is lit)
    gate_light = bpy.data.lights.new("TD.GateLight", type="AREA")
    gate_light.energy = 1600.0
    gate_light.size = 5.0
    gate_light.color = (1.0, 0.86, 0.66)
    gate_lo = bpy.data.objects.new("TD.GateLight", gate_light)
    scene.collection.objects.link(gate_lo)
    gate_lo.location = (0.0, -0.6, 1.9)
    gate_lo.rotation_euler = (math.radians(-90), 0.0, 0.0)
    parts["gate_light"] = gate_lo

    # dawn sky (Nishita) -- no download needed, physical dawn
    world = bpy.data.worlds.get("TD.World") or bpy.data.worlds.new(
        "TD.World")
    scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    sky = nt.nodes.new("ShaderNodeTexSky")
    # 5.x renamed NISHITA -> SINGLE_SCATTERING (best dawn model)
    sky.sky_type = "SINGLE_SCATTERING"
    sky.sun_elevation = elev
    sky.sun_rotation = math.radians(200.0)
    sky.altitude = 60.0
    sky.air_density = 1.4
    try:
        sky.dust_density = 2.2      # older builds; absent on 5.2
    except AttributeError:
        pass
    bg.inputs["Strength"].default_value = SKY_STRENGTH
    nt.links.new(sky.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    parts["world"] = world

    # EEVEE exposure baseline (-0.5 EV on 5.x, gotcha 5)
    try:
        scene.view_settings.exposure = -0.5
        scene.view_settings.view_transform = "AgX"
        scene.view_settings.look = "AgX - Medium High Contrast"
    except (AttributeError, TypeError):
        scene.view_settings.view_transform = "Filmic"
    parts["exposure"] = scene.view_settings.exposure

    return parts
