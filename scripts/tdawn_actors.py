"""tdawn_actors.py -- TERMINAL DAWN actor meshes (commuter + heroes).

The crowd anchors must satisfy TWO frozen contracts at once:

1. crowd_agents.add_shape_keys (the shape-key gait contract): arms are
   selected GEOMETRICALLY -- |x| in (0.15, 0.55), y > 0.05, z below
   the shoulder line (height * 1.35/1.75 + 0.02); body = the rest with
   z < height * 0.8. So the commuter mesh has two forward-reaching
   arm cylinders from the shoulders (the gait pumps them via the
   "swing" key) and a rounded torso the "lean" key bends.
2. bake2's yaw convention: the mesh FACES +Y at euler 0 (the frozen
   "faces +Y" law; bake2 writes yaw - 90 so the mesh's +Y forward
   lands on the sim heading).

Heroes use the same builder with a distinct material; their materials
are named CA.Body.<name> so the exporter's identity-color registry
finds them (export_previz_package.py:1233-1244).

This module is bpy-only and self-contained (D-TD6: no blender_kit
imports -- the export wrapper binds the previz superset copy and MY
scene must not care which copy is live).
"""
from __future__ import annotations

import math

import bpy

#: height the bridge declares for EVERY agent (previz_bridge.py:170
#: _DEFAULT_HEIGHT_M); bake2 keys shape-key bases at this height.
BRIDGE_HEIGHT_M = 1.75

#: the commuter palette (session-14 COLOR DISCIPLINE, user comment on
#: tdawn_2 S1: "too many colors for the population — color only for
#: characters we call out"). The crowd is a NEUTRAL register: value
#: variance only, no hue pop. Identity color is reserved for the heroes
#: (HERO_COLORS) and the chase group (CHASE_RGB -- one muted rust so
#: the antagonist pack reads as ONE group, still not a rainbow).
#: (r, g, b) 0-1 linear-ish sRGB; the same triple lands in Principled
#: base_color AND Workbench diffuse_color (gotcha 6).
COMMUTER_PALETTE = [
    (0.130, 0.130, 0.140),   # charcoal
    (0.220, 0.210, 0.200),   # dark taupe
    (0.160, 0.170, 0.190),   # graphite blue-gray
    (0.270, 0.250, 0.220),   # warm gray
    (0.100, 0.100, 0.110),   # near-black
    (0.200, 0.190, 0.180),   # stone
    (0.150, 0.160, 0.150),   # sage-gray
    (0.240, 0.230, 0.240),   # gray
    (0.180, 0.170, 0.160),   # bark
    (0.140, 0.145, 0.160),   # steel gray
]

#: the chase group's callout tone (ONE color for the whole group --
#: previz semantics: group identity, not fashion). Muted dark rust.
CHASE_RGB = (0.280, 0.130, 0.090)

HERO_COLORS = {
    "Master": (0.85, 0.42, 0.05),   # amber (the only hot body in frame)
    "Runner": (0.02, 0.45, 0.50),   # teal (cool counterpoint)
}


def make_material(name, rgb, rough=0.62, metallic=0.0,
                  emission_color=None, emission_strength=None):
    """One material serving BOTH engines (Principled + Workbench).

    Emission handling (F-TD11, the glow-surface law, measured on 5.2
    + AgX): the 5.x default Emission Color is WHITE — any glow material
    with strength > 0 added PURE WHITE and AgX clipped the whole surface
    to paper-white (measured on S6's throat plane, tdawn_1). So:

    - default: Emission Color is PINNED to the base rgb;
    - emission_color=(r,g,b): DECOUPLE — the glow-surface recipe is a
      DARK base + a warm emission color (a near-white base reflects
      ambient to paper even at modest strength, tdawn_2 S6/S8);
    - emission_strength: direct write (raises if the input is missing —
      never a silent no-op).

    Get-or-create: a cached material still gets any emission_* kwargs
    RE-APPLIED (the cached-return path used to silently drop them).
    Workbench diffuse_color stays the BASE color (no emission in
    workbench; dark-base glow reads dark there — expected)."""
    mat = bpy.data.materials.get(name)
    if mat is not None:
        bsdf = next((n for n in mat.node_tree.nodes
                     if n.type == "BSDF_PRINCIPLED"), None) \
            if mat.use_nodes else None
        if bsdf is not None and (emission_color is not None
                                 or emission_strength is not None):
            if emission_color is not None:
                try:
                    bsdf.inputs["Emission Color"].default_value = \
                        (*emission_color, 1.0)
                except KeyError:
                    pass
            if emission_strength is not None:
                bsdf.inputs["Emission Strength"].default_value = \
                    float(emission_strength)
        return mat
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is None:  # 5.x localized graph fallback
        bsdf = next(n for n in mat.node_tree.nodes
                    if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metallic
    try:
        bsdf.inputs["Emission Color"].default_value = \
            (*(emission_color if emission_color is not None else rgb), 1.0)
    except KeyError:
        pass
    if emission_strength is not None:
        bsdf.inputs["Emission Strength"].default_value = \
            float(emission_strength)
    mat.diffuse_color = (*rgb, 1.0)
    return mat


def _merge_objects(objs, name):
    """Join a list of mesh objects into one (the variant-mesh contract:
    add_shape_keys wants ONE merged mesh with geometric arm selection)."""
    bpy.ops.object.select_all(action="DESELECT")
    for ob in objs:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    joined = bpy.context.view_layer.objects.active
    joined.name = name
    return joined


def _prim(kind, size, loc, rot=(0.0, 0.0, 0.0), verts=16):
    """One primitive at world transform; returns the object."""
    fn = {"cyl": bpy.ops.mesh.primitive_cylinder_add,
          "sph": bpy.ops.mesh.primitive_uv_sphere_add,
          "cube": bpy.ops.mesh.primitive_cube_add}[kind]
    kw = {"location": loc, "rotation": rot}
    if kind == "cyl":
        kw.update(radius=size[0], depth=size[1], vertices=verts)
    elif kind == "sph":
        kw.update(radius=size, segments=verts, ring_count=max(6, verts // 2))
    else:
        kw.update(size=size)
    fn(**kw)
    return bpy.context.view_layer.objects.active


def build_commuter_mesh(name, height=BRIDGE_HEIGHT_M, mat_body=None):
    """Build ONE commuter humanoid (merged mesh, faces +Y, at origin).

    Proportions (scaled by height/1.75):
      torso cylinder r 0.24 z 0.80..1.35 + hip cylinder r 0.20 z 0.42
      + leg block + head sphere r 0.145 c z 1.53
      arms: r 0.065 cylinders shoulder->hand, constant-y walking carry
    """
    s = height / 1.75
    parts = [
        # legs mass (contact: the figure GROUNDS -- the validator's
        # floating check reads the bbox bottom; no legs = 0.3m float)
        _prim("cyl", (0.165 * s, 0.42 * s), (0.0, 0.0, 0.22 * s)),
        _prim("cyl", (0.24 * s, 0.58 * s), (0.0, 0.0, 1.06 * s)),   # torso
        _prim("cyl", (0.20 * s, 0.42 * s), (0.0, 0.0, 0.60 * s)),   # hips
        _prim("sph", 0.205 * s, (0.0, 0.0, 1.345 * s), verts=14),   # shoulders
        _prim("sph", 0.148 * s, (0.0, 0.01 * s, 1.53 * s), verts=14),  # head
    ]
    for sx in (-1.0, 1.0):
        # arm: shoulder (x .265, z 1.29) -> hand (x .30, y .12, z .74)
        # -- CONSTANT-y at 0.12: the whole arm keeps y > 0.05 (min
        # surface y = 0.12 - 0.065 radius = 0.055), so the gait's
        # rigid +/-0.28 Y-translation selects the WHOLE arm (a tapered
        # forward reach left 43% of the arm below the selection line
        # and tore a visible seam every step -- measured in review).
        # The pose reads "walking carry", not a zombie reach and not
        # the old backpack hunch.
        p0 = (0.265 * s * sx, 0.12 * s, 1.29 * s)
        p1 = (0.300 * s * sx, 0.12 * s, 0.74 * s)
        mid = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2, (p0[2] + p1[2]) / 2)
        dx, dy, dz = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
        ln = math.sqrt(dx * dx + dy * dy + dz * dz)
        rot_x = math.acos(max(-1.0, min(1.0, dz / ln)))       # from +Z
        # CR-TD2 P2: the Rz tilt maps (0,-1,0) to -(dx,dy)/|dxy| -- the
        # old -pi/2 MIRRORED the horizontal lean (both arms leaned
        # inward, <=3.6 deg). +pi/2 lands the axis on p0->p1 exactly.
        rot_z = math.atan2(dy, dx) + math.pi / 2              # from +X
        arm = _prim("cyl", (0.065 * s, ln), mid,
                    rot=(rot_x, 0.0, rot_z), verts=10)
        parts.append(arm)
    ob = _merge_objects(parts, name)
    if mat_body is not None:
        ob.data.materials.append(mat_body)
    return ob


def commuter_material(idx):
    """Palette material i (round-robin; cached by name)."""
    rgb = COMMUTER_PALETTE[idx % len(COMMUTER_PALETTE)]
    return make_material(f"CA.Commute.{idx % len(COMMUTER_PALETTE):02d}",
                         rgb)


def chase_material(_idx=None):
    """The chase group's ONE callout tone (session-14 color discipline:
    group identity color, muted; every chase agent shares it)."""
    return make_material("CA.Commute.Chase", CHASE_RGB)


def hero_material(name):
    """Hero identity material (CA.Body.<name> -- the exporter's
    identity-color registry reads exactly this prefix)."""
    return make_material(f"CA.Body.{name}", HERO_COLORS[name], rough=0.5)


def new_anchored_obj(name, mesh_ob, loc, yaw=0.0):
    """Instance a commuter at loc: LINKED mesh (bake2 copies it
    per-instance before adding shape keys), own transform."""
    ob = bpy.data.objects.new(name, mesh_ob.data)
    ob.location = loc
    ob.rotation_euler = (0.0, 0.0, yaw)
    bpy.context.scene.collection.objects.link(ob)
    return ob
