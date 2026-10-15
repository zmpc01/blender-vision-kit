"""tform_world.py -- THE DRILL's set: the golden-hour citadel parade yard.

Self-contained bpy; materials via tdawn_actors.make_material (arg3 =
ROUGHNESS; the F-TD11 emission kwargs are deliberately UNUSED here --
see deviation 6). The set AGREES with the sim contract (docs/
DESIGN_drill.md REV-2 §5): yard 56x40 m cobbled (two-tone warm checker),
fortress walls N/E/W with battlements and the NORTH GAP (x -3..3 -- the
march-in spawns and the dispersal marches OUT through it), colonnade
along S (10 columns 4.5 m + entablature beam, NO roof -- the
axial-vantage law), circle-mark ring inlay r=4 at (0,0) + dais inlay
3x2 at (10,0) (both 0.05 proud, VISUAL ONLY -- no blocked squares), 4
banner poles with pennants, 2 decorative drums, distant hills N, and a
LOW dust volume box (the scene module keys its density). NO sun lamp,
NO sky, NO crowd, NO banner text in this module (the ladder owns the
light rig + sky_strength axis; heroes/crowd/title are scene-side).

Coordinate frame: ground z=0, meters; x east, y north. Yard x
-28..28 / y -20..20 (top z=0). Walls 6 m tall, 2 m thick, bodies just
OUTSIDE the yard rect (deviation 1). Gap x -3..3 through the N wall
(clear height 4.0-4.58 m under the arch), dark backdrop plane 10 m
behind it. Colonnade columns 0.8 m square centered on y=-20.

build_world(scene) -> context dict: {"parts", "mats", "consts",
"pennants", "counts"}. The CONSTS are the RAW geometry frame
(yard_min/yard_max/gap_x_range/circle_center/circle_r/colonnade_y/
column_xs + wall/gate extras).

s19-B13 -- READ BEFORE AUTHORING THE tform CONTRACT (the contract
module does not exist yet): the crowd-side walkable is NOT
yard_min/yard_max. DESIGN_drill pins "walkable = the yard rect PULLED
SHORT of the column faces by half-width + inflation margin; columns =
Blocked squares FULLY inside the walkable", and the colonnade columns
STAND ON y=-20 (colonnade_y; column faces reach y -20.4..-19.6 across
the raw S edge). A walkable that runs to the raw edges would put the
column Blocked squares ON/OVER the boundary -> the E_InvalidRange
trap. Derive the walkable from these inputs (pull the S edge north of
the column faces by the inflation margin; keep N/E/W pulled short of
the wall inner faces for the same reason) -- the raw consts arm that
math, they are not the answer.

Deviations / ambiguity resolutions (recorded, the tgreen way):
1. "Walls N (y=20), E (x=28), W (x=-28)" read as the wall LINE standing
   on the yard boundary with the 2 m body OUTSIDE it (N wall y 20..22,
   E x 28..30, W x -30..-28; E/W run y -20..22 to seal the corners).
   The declared 56x40 cobbled yard stays fully clear and
   yard_max=(28,20) is exactly the wall inner-face line (no crowd clip).
   The gap-corridor QA (y 19..21) still crosses the wall band, so the
   gap assert keeps its teeth.
2. Merlons (1.2 x 0.8 x 1.0, every 2 m on the wall centerlines) march
   STRAIGHT ACROSS the gate (centers incl. x -3,-1,1,3): they stand on
   the arch band (voussoir tops z=6.0 = wall top) so nothing floats and
   the battlement line reads continuous; the passage corridor z 0..3.9
   stays clear.
3. The "arched gate opening" = 5 stepped voussoir boxes spanning the
   gap (underside arc 4.576 -> 4.0 m toward the jambs, tops flush at
   6.0) -- an arc silhouette on a 5-object budget, no booleans.
4. The pinned drum coords (10.8, +-0.8) stand ON the dais inlay
   footprint (dais x 8.5..11.5, y -1..1): the pins win. The dais is a
   0.05 m visual inlay (the planar-sim law -- no riser), so the prop
   stands rest on stone with no collision implication; the SIM drummers
   still spawn on the ground beside the dais (scene-side cast).
5. NO sun lamp, NO sky/world, NO ladder constants in this module
   (unlike tsquall_world): DESIGN_drill REV-2 gives the light rig, the
   sky_strength axis and the dust-density keying to the scene/ladder.
   This module ships geometry + the named dust BOX only; QA gates "no
   LIGHT objects, scene.world untouched".
6. Zero emission: the F-TD11 emission kwargs are intentionally unused
   -- golden-hour radiance is the ladder's sun. The pennant cloth is
   the designated EMISSIVE-OFF slot (QA asserts Emission Strength == 0).
7. circle_r=4.0 is the ring band CENTERLINE (r_in 3.85 / r_out 4.15,
   0.3 m wide) -- the agents' r=4 ring reads centered on the mark.
   Ring/dais tops 0.05 proud, bases 0.002 off the yard plane (no
   coplanar z-fight with the yard grid, grounded within tolerance).
8. Backdrop sized to cover ALL in-yard sightlines through the gap: from
   the yard's SE/NW corners the gap cone exits x ~+-28.9 at y=31, so
   the dark plane is 64 m wide (x -32..32, z 0..10) at y 30..32 --
   still 8+ m clear of the dispersal end positions past the gap.
9. The kit validator runs INFORMATIONALLY (printed, non-gating) per the
   tsquall_world deviation-1 precedent; its flags on THIS set are all
   by-design classes: below_floor = the grounding plane (the tgreen
   ocean-horizon fix), X & dust_box intersections = objects standing
   INSIDE the dust volume (the crowd walks through it), drum shell/head
   = the 1 cm seated-head overlap, floating = proud/mounted dressing
   (voussoirs, pennants). The task's assert list is the gate.
10. The N-gap assert = bounding-box corridor (x -3..3, y 19..21,
    z 0..3.9), run wall-scoped AND scene-global (dust_box exempted by
    name: its north face IS the y=20 yard line by spec -- a no-surface
    volume placeholder, not a wall). 1 mm eps: a boundary-face touch is
    not a "block" (float32-safe). Raycast rejected: the dust-box faces
    and the backdrop sit on the test line of sight and would need
    per-object exemptions that weaken the test.
"""
from __future__ import annotations

import bmesh
import json
import math
import sys

import bpy
from mathutils import Vector

from tdawn_actors import make_material

# --- set frame (meters; z=0 ground) ---------------------------------
YARD_X0, YARD_X1 = -28.0, 28.0
YARD_Y0, YARD_Y1 = -20.0, 20.0
WALL_T = 2.0               # wall thickness
WALL_H = 6.0               # wall top z
GAP_X0, GAP_X1 = -3.0, 3.0  # the north gap (6 m)
ARCH_Z0 = 4.6              # arch underside at the gap center
ARCH_DROP = 0.6            # underside drop to the jambs (4.0 m there)
CIRCLE_C = (0.0, 0.0)
CIRCLE_R = 4.0             # the ring band CENTERLINE (deviation 7)
RING_BAND = 0.15           # band half-width -> r_in 3.85 / r_out 4.15
INLAY_TOP = 0.05           # inlays 0.05 proud (planar-sim law)
INLAY_BASE = 0.002         # off the yard plane (no coplanar z-fight)
COLONNADE_Y = -20.0
COLUMN_N = 10
COLUMN_X0, COLUMN_X1 = -25.0, 25.0
COLUMN_SIZE = 0.8
COLUMN_H = 4.5
POLE_XS = (-14.0, 14.0)
POLE_YS = (-12.0, 12.0)
POLE_H = 7.0
DRUM_X = 10.8
DRUM_YS = (-0.8, 0.8)
MERLON_ALONG, MERLON_ACROSS, MERLON_H = 1.2, 0.8, 1.0
MERLON_STEP = 2.0
DUST_BOX_NAME = "dust_box"
TFORM_DUST_DENSITY = 0.015  # placeholder; the SCENE module keys density

# 10 columns at x -25..25, step 50/9 = 5.5556 ("step ~5.5")
COLUMN_XS = [round(COLUMN_X0 + i * (COLUMN_X1 - COLUMN_X0) / (COLUMN_N - 1),
                   4) for i in range(COLUMN_N)]

# two-tone warm stone (linear); the checker drives between them
COBBLE_A = (0.30, 0.235, 0.165)
COBBLE_B = (0.21, 0.16, 0.115)

# the QA gap corridor: the passage through the wall band, up to below
# the arch springing (voussoir undersides >= 4.0)
GAP_CORRIDOR = ((GAP_X0, GAP_X1), (19.0, 21.0), (0.0, 3.9))
GAP_EPS = 1e-3   # 1 mm: a boundary-face touch is not a "block"

# Factory-default object names (s19-B15a, the tfog_world pattern):
# EXACT stems, NOT prefixes -- a scene-side "Cube_hall" or "Camera_rig"
# must survive a rebuild purge. Only bare factory names and their
# Blender numeric duplicates ("Cube.001") match _is_factory_name().
FACTORY_NAMES = {"Cube", "Camera", "Light", "Lamp"}


def _is_factory_name(name):
    stem, _, suffix = name.partition(".")
    return stem in FACTORY_NAMES and (not suffix or suffix.isdigit())


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
    # lowercase naming law means every created object is explicitly
    # named here.
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


def _ring_mesh(name, r_in, r_out, z0, z1, seg=48, mat=None):
    """A flat solid annulus (the circle-mark inlay): top/bottom rings +
    outer/inner walls, outward-consistent normals, built at the origin
    (local coords == world; the radial QA reads vertices directly)."""
    bm = bmesh.new()
    ang = [2.0 * math.pi * i / seg for i in range(seg)]
    rings = {}
    for tag, r, z in (("bo", r_out, z0), ("to", r_out, z1),
                      ("bi", r_in, z0), ("ti", r_in, z1)):
        rings[tag] = [bm.verts.new((r * math.cos(a), r * math.sin(a), z))
                      for a in ang]
    bo, to, bi, ti = (rings["bo"], rings["to"], rings["bi"], rings["ti"])
    for i in range(seg):
        j = (i + 1) % seg
        bm.faces.new((bo[i], bo[j], to[j], to[i]))    # outer wall
        bm.faces.new((ti[i], ti[j], bi[j], bi[i]))    # inner wall
        bm.faces.new((to[i], to[j], ti[j], ti[i]))    # top annulus
        bm.faces.new((bi[i], bi[j], bo[j], bo[i]))    # bottom annulus
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    if mat is not None:
        me.materials.append(mat)
    return ob


def _pennant(name, loc, mat):
    """One flat cloth triangle (the emissive-off slot), hoist on the
    pole's east face, tip drooping -- the scene module owns wind keys."""
    me = bpy.data.meshes.new(name)
    me.from_pydata([(0.0, 0.0, 0.05), (1.1, 0.0, -0.16),
                    (0.03, 0.0, -0.36)], [], [(0, 1, 2)])
    me.update()
    ob = bpy.data.objects.new(name, me)
    ob.location = loc
    if mat is not None:
        me.materials.append(mat)
    return ob


def _dust_material():
    """The dust volume: Volume Scatter ONLY (no surface shader -- the
    box faces render nothing; the scene module keys the density)."""
    mat = bpy.data.materials.get("tform_dust")
    if mat is None:
        mat = bpy.data.materials.new("tform_dust")
    mat.use_nodes = True
    nt = mat.node_tree
    for n in [n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"]:
        nt.nodes.remove(n)              # NO surface shader (deviation 10)
    out = next((n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"), None)
    if out is None:
        out = nt.nodes.new("ShaderNodeOutputMaterial")
    sc = next((n for n in nt.nodes if n.type == "VOLUME_SCATTER"), None)
    if sc is None:
        sc = nt.nodes.new("ShaderNodeVolumeScatter")
        sc.inputs["Color"].default_value = (1.0, 0.88, 0.75, 1.0)
        sc.inputs["Anisotropy"].default_value = 0.0
        nt.links.new(sc.outputs["Volume"], out.inputs["Volume"])
    sc.inputs["Density"].default_value = TFORM_DUST_DENSITY
    return mat


def _build_materials():
    """The golden-hour stone palette. All make_material (arg3 =
    roughness); NO emission kwargs anywhere (deviation 6)."""
    m = {}
    # the cobbled yard: ONE grid + procedural checker (the cheap route)
    m["cobble"] = make_material("tform_cobble", COBBLE_A, 0.9)
    nt = m["cobble"].node_tree
    if not any(n.type == "TEX_CHECKER" for n in nt.nodes):
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        co = nt.nodes.new("ShaderNodeTexCoord")
        mp = nt.nodes.new("ShaderNodeMapping")
        # Generated spans 0..1 over the 56x40 grid -> 2 m cells
        mp.inputs["Scale"].default_value = (28.0, 20.0, 1.0)
        ck = nt.nodes.new("ShaderNodeTexChecker")
        ck.inputs["Color1"].default_value = (*COBBLE_A, 1.0)
        ck.inputs["Color2"].default_value = (*COBBLE_B, 1.0)
        ck.inputs["Scale"].default_value = 1.0
        nt.links.new(co.outputs["Generated"], mp.inputs["Vector"])
        nt.links.new(mp.outputs["Vector"], ck.inputs["Vector"])
        nt.links.new(ck.outputs["Color"], bsdf.inputs["Base Color"])
    # the fortress shell
    m["wall"] = make_material("tform_stone", (0.16, 0.148, 0.128), 0.85)
    # the colonnade limestone
    m["column"] = make_material("tform_limestone", (0.30, 0.26, 0.20), 0.8)
    # the inlays (darker stone, distinct from the yard + walls)
    m["inlay"] = make_material("tform_inlay_dark", (0.085, 0.075, 0.062),
                               0.9)
    # the banner poles + pennants (cloth is the EMISSIVE-OFF slot)
    m["iron"] = make_material("tform_iron", (0.05, 0.05, 0.055), 0.5,
                              metallic=0.6)
    m["cloth"] = make_material("tform_pennant_cloth", (0.32, 0.045, 0.035),
                               0.85)
    # the drum props
    m["drum_wood"] = make_material("tform_drum_wood", (0.14, 0.09, 0.05),
                                   0.6)
    m["drum_head"] = make_material("tform_drum_head", (0.55, 0.48, 0.38),
                                   0.7)
    # the silhouettes (backdrop behind the gap; hills beyond the wall)
    m["backdrop"] = make_material("tform_backdrop", (0.012, 0.012, 0.014),
                                  1.0)
    m["hills"] = make_material("tform_hills", (0.022, 0.024, 0.021), 1.0)
    # the grounding plane (the tgreen ocean-horizon fix)
    m["ground"] = make_material("tform_ground", (0.045, 0.04, 0.034), 0.95)
    # the dust volume (manual -- make_material is a SURFACE factory)
    m["dust"] = _dust_material()
    return m


def build_world(scene):
    """Build the citadel parade yard; returns the context dict."""
    # the FACTORY-PURGE LAW at scene level (no factory default
    # survives; the scene module may call this on a factory scene).
    # s19-B15a: EXACT factory names only (the tfog_world FACTORY_NAMES
    # pattern) -- the old startswith("Cube"/"Camera"/...) prefix purge
    # would delete SCENE-SIDE objects sharing those stems on a rebuild.
    for ob in list(bpy.data.objects):
        if _is_factory_name(ob.name):
            bpy.data.objects.remove(ob, do_unlink=True)

    mats = _build_materials()
    pre = set(scene.objects.keys())

    # --- the grounding plane UNDER everything --------------------------
    _box("tform_ground_plane", 500.0, 500.0, 0.1, (0.0, 0.0, -0.06),
         mats["ground"])

    # --- the cobbled yard: ONE subdivided grid, procedural checker -----
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=28, y_subdivisions=20,
                                    size=1, location=(0.0, 0.0, 0.0))
    yard = bpy.context.active_object
    yard.name = "tform_yard"
    yard.scale = (YARD_X1 - YARD_X0, YARD_Y1 - YARD_Y0, 1.0)   # top z=0
    yard.data.materials.append(mats["cobble"])

    # --- THE FORTRESS WALLS (bodies outside the yard; deviation 1) -----
    wall = mats["wall"]
    # N wall as TWO segments leaving the gap x -3..3 (the north gap)
    _box("tform_wall_n_w", GAP_X0 - YARD_X0, WALL_T, WALL_H,
         ((YARD_X0 + GAP_X0) / 2, YARD_Y1 + WALL_T / 2, WALL_H / 2), wall)
    _box("tform_wall_n_e", YARD_X1 - GAP_X1, WALL_T, WALL_H,
         ((GAP_X1 + YARD_X1) / 2, YARD_Y1 + WALL_T / 2, WALL_H / 2), wall)
    # E/W walls run y -20..22 to seal the corners against the N band
    _box("tform_wall_e", WALL_T, YARD_Y1 - YARD_Y0 + WALL_T, WALL_H,
         (YARD_X1 + WALL_T / 2, (YARD_Y0 + YARD_Y1 + WALL_T) / 2,
          WALL_H / 2), wall)
    _box("tform_wall_w", WALL_T, YARD_Y1 - YARD_Y0 + WALL_T, WALL_H,
         (YARD_X0 - WALL_T / 2, (YARD_Y0 + YARD_Y1 + WALL_T) / 2,
          WALL_H / 2), wall)

    # --- the gate ARCH over the gap (5 stepped voussoirs; deviation 3) -
    for i, cx in enumerate((-2.4, -1.2, 0.0, 1.2, 2.4), start=1):
        edge = abs(cx) + 0.6
        zb = ARCH_Z0 - ARCH_DROP * (edge / -GAP_X0) ** 2
        _box(f"tform_gate_voussoir_{i}", 1.2, WALL_T, WALL_H - zb,
             (cx, YARD_Y1 + WALL_T / 2, (zb + WALL_H) / 2), wall)

    # --- BATTLEMENTS (merlon cubes every 2 m on the wall centerlines;
    # the row crosses the gate standing on the arch band; deviation 2) --
    merlon_xy = ([(float(x), YARD_Y1 + WALL_T / 2)
                  for x in range(-27, 28, 2)]
                 + [(YARD_X1 + WALL_T / 2, float(y))
                    for y in range(-19, 22, 2)]
                 + [(YARD_X0 - WALL_T / 2, float(y))
                    for y in range(-19, 22, 2)])
    for i, (mx, my) in enumerate(merlon_xy, start=1):
        along_across = ((MERLON_ALONG, MERLON_ACROSS)
                        if abs(my - (YARD_Y1 + WALL_T / 2)) < 1e-6
                        else (MERLON_ACROSS, MERLON_ALONG))
        _box(f"tform_merlon_{i:03d}", along_across[0], along_across[1],
             MERLON_H, (mx, my, WALL_H + MERLON_H / 2), wall)

    # --- the dark BACKDROP behind the gap + the distant HILLS ----------
    _box("tform_backdrop", 64.0, 2.0, 10.0, (0.0, 31.0, 5.0),
         mats["backdrop"])
    _box("tform_hills", 280.0, 2.0, 26.0, (0.0, 45.0, 13.0), mats["hills"])

    # --- THE COLONNADE along S (NO roof -- the axial-vantage law) ------
    for i, cx in enumerate(COLUMN_XS, start=1):
        _box(f"tform_column_{i:02d}", COLUMN_SIZE, COLUMN_SIZE, COLUMN_H,
             (cx, COLONNADE_Y, COLUMN_H / 2), mats["column"])
    # the entablature beam connecting the column tops (a BEAM, not a
    # roof: 0.8 m tall band z 4.5..5.3, resting on all 10 columns)
    _box("tform_entablature", (COLUMN_X1 - COLUMN_X0) + 2 * COLUMN_SIZE,
         1.0, 0.8, (0.0, COLONNADE_Y, COLUMN_H + 0.4), mats["column"])

    # --- the CIRCLE MARK ring inlay (r=4 centerline, 0.05 proud) -------
    ring = _ring_mesh("tform_circle_mark", CIRCLE_R - RING_BAND,
                      CIRCLE_R + RING_BAND, INLAY_BASE, INLAY_TOP, seg=48,
                      mat=mats["inlay"])
    scene.collection.objects.link(ring)

    # --- the DAIS inlay (3x2 at (10,0), visual only) --------------------
    _box("tform_dais", 3.0, 2.0, INLAY_TOP - INLAY_BASE,
         (10.0, 0.0, (INLAY_BASE + INLAY_TOP) / 2), mats["inlay"])

    # --- the 4 BANNER POLES + pennants (the emissive-off slot) ---------
    pole_xy = [(POLE_XS[0], POLE_YS[0]), (POLE_XS[1], POLE_YS[0]),
               (POLE_XS[0], POLE_YS[1]), (POLE_XS[1], POLE_YS[1])]
    for i, (px, py) in enumerate(pole_xy, start=1):
        _prim("cyl", (0.14, POLE_H), (px, py, POLE_H / 2), verts=12,
              mat=mats["iron"], name=f"tform_pole_{i}")
        scene.collection.objects.link(
            _pennant(f"pennant_{i}", (px + 0.08, py, POLE_H - 0.15),
                     mats["cloth"]))

    # --- the drum props (decorative; deviation 4) -----------------------
    for i, dy in enumerate(DRUM_YS, start=1):
        _prim("cyl", (0.12, 0.55), (DRUM_X, dy, 0.275), verts=10,
              mat=mats["iron"], name=f"tform_drum_{i}_stand")
        _prim("cyl", (0.72, 0.50), (DRUM_X, dy, 0.80), verts=20,
              mat=mats["drum_wood"], name=f"tform_drum_{i}_shell")
        _prim("cyl", (0.70, 0.03), (DRUM_X, dy, 1.055), verts=20,
              mat=mats["drum_head"], name=f"tform_drum_{i}_head")

    # --- the LOW DUST volume (the scene module keys the density) -------
    _box(DUST_BOX_NAME, YARD_X1 - YARD_X0, YARD_Y1 - YARD_Y0, 2.0,
         (0.0, 0.0, 1.0), mats["dust"])

    bpy.context.view_layer.update()
    created = [ob for ob in scene.objects if ob.name not in pre]

    consts = {
        # s19-B13: RAW geometry frame, NOT the crowd walkable. The
        # colonnade columns stand ON y=-20, so a walkable pulled to
        # these edges puts the column Blocked squares ON the boundary
        # (the E_InvalidRange trap). The (future) tform contract module
        # must derive the walkable PULLED SHORT of the column faces
        # (DESIGN_drill: columns = Blocked squares FULLY inside).
        "yard_min": (YARD_X0, YARD_Y0),
        "yard_max": (YARD_X1, YARD_Y1),
        "gap_x_range": (GAP_X0, GAP_X1),
        "circle_center": CIRCLE_C,
        "circle_r": CIRCLE_R,
        "colonnade_y": COLONNADE_Y,
        "column_xs": list(COLUMN_XS),
        # extras for the scene/ladder (not the walkable contract)
        "wall_top_z": WALL_H,
        "wall_thickness": WALL_T,
        "gate_clear_z": round(ARCH_Z0 - ARCH_DROP, 6),  # min clear (jambs)
        "colonnade_face_y": COLONNADE_Y + COLUMN_SIZE / 2,
        "dust_density": TFORM_DUST_DENSITY,
    }
    names = [ob.name for ob in created]
    counts = {
        "walls": sum(n.startswith("tform_wall") for n in names),
        "gate_voussoirs":
            sum(n.startswith("tform_gate_voussoir") for n in names),
        "merlons": sum(n.startswith("tform_merlon") for n in names),
        "columns": sum(n.startswith("tform_column") for n in names),
        "entablature": sum(n.startswith("tform_entablature")
                           for n in names),
        "circle_mark": sum(n.startswith("tform_circle_mark")
                           for n in names),
        "dais": sum(n.startswith("tform_dais") for n in names),
        "poles": sum(n.startswith("tform_pole") for n in names),
        "pennants": sum(n.startswith("pennant_") for n in names),
        "drums": sum(n.startswith("tform_drum") for n in names),
        "yard": sum(n.startswith("tform_yard") for n in names),
        "ground_plane": sum(n.startswith("tform_ground_plane")
                            for n in names),
        "backdrop": sum(n.startswith("tform_backdrop") for n in names),
        "hills": sum(n.startswith("tform_hills") for n in names),
        "dust_box": sum(n.startswith(DUST_BOX_NAME) for n in names),
    }
    return {"parts": created, "mats": mats, "consts": consts,
            "pennants": ["pennant_1", "pennant_2", "pennant_3",
                         "pennant_4"],
            "counts": counts}


# ======================================================================
# __main__ QA section (NON-VISUAL: asserts + prints, zero renders --
# the principal does all visual gates; --dry-run is accepted and IS
# the only mode: this module never renders, never saves)
# ======================================================================

def _ok(tag, cond, detail):
    print(f"[tform-qa] {'PASS' if cond else 'FAIL'} {tag}: {detail}")
    return 0 if cond else 1


def _blocks(bbox, box, eps=GAP_EPS):
    """True if a world AABB eats into the (eps-shrunk) corridor box --
    a boundary-face TOUCH is not a block (float32-safe)."""
    (x0, x1), (y0, y1), (z0, z1) = box
    mn, mx = bbox
    return (mn[0] < x1 - eps and mx[0] > x0 + eps and
            mn[1] < y1 - eps and mx[1] > y0 + eps and
            mn[2] < z1 - eps and mx[2] > z0 + eps)


def _qa(ctx):
    scene = bpy.context.scene
    parts = ctx["parts"]
    consts = ctx["consts"]
    names = [ob.name for ob in parts]
    fails = 0

    # --- QA0: the object budget ----------------------------------------
    fails += _ok("budget", len(parts) < 200,
                 f"{len(parts)} parts (<200)")

    # --- QA1: factory purge (no factory default survives; the SAME
    # exact-name predicate as the build_world purge, s19-B15a -- a
    # prefix check here would false-alarm on scene-side stems) --------
    factory = [ob.name for ob in scene.objects
               if _is_factory_name(ob.name)]
    fails += _ok("factory purge", not factory,
                 f"{len(factory)} factory survivors {factory}")
    owns = set(ob.name for ob in scene.objects) == set(names)
    fails += _ok("scene ownership", owns,
                 "every scene object is a module part (QA flow)")

    # --- QA2: the lowercase naming law ---------------------------------
    import re
    bad_names = [n for n in names if not re.fullmatch(r"[a-z0-9_]+", n)]
    fails += _ok("lowercase names", not bad_names,
                 f"{len(bad_names)} offenders {bad_names[:4]}")

    # --- QA3: materials on ALL meshes ----------------------------------
    no_mat = [ob.name for ob in scene.objects if ob.type == 'MESH'
              and not (ob.data.materials
                       and all(ob.data.materials))]
    fails += _ok("materials on meshes", not no_mat,
                 f"{len(no_mat)} unmaterialized {no_mat[:4]}")

    # --- QA4: the part counts ------------------------------------------
    expect = {"walls": 4, "gate_voussoirs": 5, "merlons": 70,
              "columns": 10, "entablature": 1, "circle_mark": 1,
              "dais": 1, "poles": 4, "pennants": 4, "drums": 6,
              "yard": 1, "ground_plane": 1, "backdrop": 1, "hills": 1,
              "dust_box": 1}
    counts = ctx["counts"]
    bad_counts = {k: counts.get(k) for k, v in expect.items()
                  if counts.get(k) != v}
    fails += _ok("part counts", not bad_counts,
                 f"{len(bad_counts)} off {bad_counts} "
                 f"(total {sum(counts.values())})")
    fails += _ok("count coverage", sum(counts.values()) == len(parts),
                 f"sum {sum(counts.values())} == {len(parts)} parts")

    meshes = {ob.name: ob for ob in scene.objects if ob.type == 'MESH'}
    bnds = {n: _bounds(ob) for n, ob in meshes.items()}

    # --- QA5: the circle-mark ring inlay --------------------------------
    ring = bpy.data.objects.get("tform_circle_mark")
    ring_ok = False
    ring_detail = "missing"
    if ring is not None and ring.type == 'MESH':
        rs = [math.hypot(v.co.x, v.co.y) for v in ring.data.vertices]
        rmin, rmax = min(rs), max(rs)
        mn, mx = bnds["tform_circle_mark"]
        top = mx[2]
        # rmin > 0 proves a RING (a disc would span the center); the
        # band hugs the r=4.0 centerline (3.85..4.15)
        ring_ok = (3.7 < rmin < 3.95 and 4.05 < rmax < 4.25
                   and 0.045 < top < 0.055
                   and abs((mn[0] + mx[0]) / 2) < 1e-4
                   and abs((mn[1] + mx[1]) / 2) < 1e-4)
        ring_detail = (f"r {rmin:.3f}..{rmax:.3f} (centerline "
                       f"{(rmin + rmax) / 2:.3f}), top z {top:.3f}")
    fails += _ok("circle mark ring", ring_ok, ring_detail)

    # --- QA6: the dais inlay --------------------------------------------
    dais_ok = "tform_dais" in bnds
    if dais_ok:
        (x0, y0, _), (x1, y1, z1) = bnds["tform_dais"]
        dais_ok = (abs(x0 - 8.5) < 1e-3 and abs(x1 - 11.5) < 1e-3
                   and abs(y0 + 1.0) < 1e-3 and abs(y1 - 1.0) < 1e-3
                   and 0.045 < z1 < 0.055)
    fails += _ok("dais inlay", dais_ok,
                 f"bbox {bnds.get('tform_dais')}")

    # --- QA7: the north gap is REAL (deviation 10) ----------------------
    wall_bad = sorted(n for n, b in bnds.items()
                      if n.startswith("tform_wall")
                      and _blocks(b, GAP_CORRIDOR))
    fails += _ok("gap clear (wall meshes)", not wall_bad,
                 f"{len(wall_bad)} blockers {wall_bad} in "
                 f"x -3..3 @ y 19..21, z 0..3.9")
    global_bad = sorted(
        n for n, b in bnds.items()
        if n != DUST_BOX_NAME and _blocks(b, GAP_CORRIDOR))
    fails += _ok("gap clear (whole scene)", not global_bad,
                 f"{len(global_bad)} blockers {global_bad} "
                 f"(dust_box exempted: no-surface volume)")

    # --- QA8: the exported consts ---------------------------------------
    need = {"yard_min": (YARD_X0, YARD_Y0), "yard_max": (YARD_X1, YARD_Y1),
            "gap_x_range": (GAP_X0, GAP_X1),
            "circle_center": CIRCLE_C, "circle_r": CIRCLE_R,
            "colonnade_y": COLONNADE_Y}

    def _same(a, b):
        if isinstance(a, (tuple, list)):
            return tuple(a) == tuple(b)
        return a == b                       # scalars (circle_r)

    bad_consts = {k: consts.get(k) for k, v in need.items()
                  if not _same(consts.get(k), v)}
    xs = consts.get("column_xs") or []
    xs_ok = (len(xs) == COLUMN_N and xs[0] == COLUMN_X0
             and xs[-1] == COLUMN_X1
             and all(xs[i] < xs[i + 1] for i in range(len(xs) - 1)))
    fails += _ok("const exports", not bad_consts and xs_ok,
                 f"bad {bad_consts}; column_xs n={len(xs)} "
                 f"[{xs[0] if xs else None}..{xs[-1] if xs else None}]")
    # cross-check: the BUILT columns sit at the exported xs
    col_c = sorted(round((bnds[n][0][0] + bnds[n][1][0]) / 2, 2)
                   for n in bnds if n.startswith("tform_column_"))
    fails += _ok("columns at exported xs",
                 col_c == [round(x, 2) for x in xs],
                 f"{len(col_c)} built vs {len(xs)} exported")

    # --- QA9: the pennants (named + emissive-off) ------------------------
    pen_ok = sorted(ob.name for ob in parts
                    if ob.name.startswith("pennant_")) == ctx["pennants"]
    emitters = []
    for pname in ctx["pennants"]:
        ob = bpy.data.objects.get(pname)
        if ob is None or ob.type != 'MESH' or not ob.data.materials:
            pen_ok = False
            continue
        bsdf = next((n for n in ob.data.materials[0].node_tree.nodes
                     if n.type == "BSDF_PRINCIPLED"), None)
        es = bsdf.inputs.get("Emission Strength") if bsdf else None
        if es is not None and abs(es.default_value) > 1e-9:
            emitters.append(pname)
    fails += _ok("pennants named + emissive-off",
                 pen_ok and not emitters,
                 f"{ctx['pennants']}; emitters {emitters}")

    # --- QA10: the dust box (named, volume-only, placeholder density) ---
    dust = bpy.data.objects.get(DUST_BOX_NAME)
    dust_ok = False
    dust_detail = "missing"
    if dust is not None and dust.type == 'MESH' and dust.data.materials:
        mat = dust.data.materials[0]
        sc = next((n for n in mat.node_tree.nodes
                   if n.type == "VOLUME_SCATTER"), None)
        out = next((n for n in mat.node_tree.nodes
                    if n.type == "OUTPUT_MATERIAL"), None)
        (x0, y0, z0), (x1, y1, z1) = bnds[DUST_BOX_NAME]
        surface_free = out is not None and not out.inputs["Surface"].is_linked
        dens = sc.inputs["Density"].default_value if sc else None
        dust_ok = (sc is not None and surface_free
                   and dens is not None
                   and abs(dens - TFORM_DUST_DENSITY) < 1e-6
                   and abs(x0 - YARD_X0) < 1e-3 and abs(x1 - YARD_X1) < 1e-3
                   and abs(y0 - YARD_Y0) < 1e-3 and abs(y1 - YARD_Y1) < 1e-3
                   and abs(z0) < 1e-3 and abs(z1 - 2.0) < 1e-3)
        dust_detail = (f"density {dens}, surface-free {surface_free}, "
                       f"bbox ({x0:.1f}..{x1:.1f}, {y0:.1f}..{y1:.1f}, "
                       f"{z0:.2f}..{z1:.2f})")
    fails += _ok("dust box", dust_ok, dust_detail)

    # --- QA11: the ladder owns the light rig (no sun, no sky) -----------
    lamps = [ob.name for ob in scene.objects
             if ob.type in ('LIGHT', 'LAMP')]
    fails += _ok("no light rig", not lamps and scene.world is None,
                 f"{len(lamps)} lamps {lamps}; world {scene.world}")

    # --- QA12: grounded (the no-floater cheap sweep) ---------------------
    floaters = [n for n, (mn, _) in bnds.items()
                if n != "tform_ground_plane" and mn[2] < -0.02]
    fails += _ok("grounded", not floaters,
                 f"{len(floaters)} below-ground {floaters[:4]}")

    # --- QA13: the kit validator (INFORMATIONAL -- deviation 9) ---------
    try:
        import validate_scene as V
        rep = V.validate_scene(ground_z=0.0)
        sev = rep["issues_by_severity"]
        print(f"[tform-qa]   validator (NOT a gate; proud world dressing "
              f"is the tsquall deviation-1 flag class): "
              f"P0={sev['P0']} P1={sev['P1']} P2={sev['P2']} "
              f"meshes={rep['mesh_objects_checked']}")
        for issue in rep["issues"][:6]:
            obj = issue.get("object",
                            " & ".join(issue.get("objects", [])))
            print(f"[tform-qa]     [{issue['severity']}] "
                  f"{issue['type']}: {obj}")
        fails += _ok("validator scan sanity",
                     rep["mesh_objects_checked"] >= 100,
                     f"{rep['mesh_objects_checked']} meshes scanned")
    except Exception as exc:               # noqa: BLE001 -- QA harness
        fails += _ok("validator scan sanity", False, f"raise: {exc}")

    print(f"[tform-qa] SUMMARY: "
          f"{'ALL PASS' if fails == 0 else f'{fails} FAIL(S)'} "
          f"(budget {len(parts)}, merlons {counts['merlons']}, "
          f"columns {counts['columns']})")
    return fails


def main():
    from blender_kit import clear_scene, script_argv
    import argparse
    p = argparse.ArgumentParser(
        description="DRILL world module: build + non-visual QA "
                    "(NO render -- the principal does all visual gates)")
    p.add_argument("--dry-run", action="store_true",
                   help="accepted and ALWAYS true: this module is "
                        "build+assert only (renders are scene-side)")
    p.parse_args(script_argv())

    clear_scene()                    # the factory-startup purge (kit law)
    scene = bpy.context.scene
    ctx = build_world(scene)
    fails = _qa(ctx)
    manifest = {"module": "tform_world", "n_parts": len(ctx["parts"]),
                "counts": ctx["counts"], "consts": ctx["consts"],
                "pennants": ctx["pennants"],
                "dust_density": TFORM_DUST_DENSITY}
    print("[tform_world] MANIFEST " + json.dumps(manifest))
    print("[tform_world] no render (principal renders)")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
