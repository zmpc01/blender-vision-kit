"""
scene_cornell.py — canonical Cornell Box for WebGPU PreViz A/B parity
(IMPL-BL-PREP / track B17 "identical geometry" closure).

Builds the EXACT canonical Cornell scene in Blender:
  * geometry: imported from the OBJ exported by
    webgpu-previz/python/oracle-mitsuba/export_cornell_obj.py
    (the same tessellated mesh the Mitsuba oracle + WebGPU candidate
    consume). Vertex/face counts and the geometry multiset are verified
    against the canonical tessellation rebuilt from the scene JSON.
    Fallback (no --obj): the canonical mesh is rebuilt directly from the
    scene JSON via bmesh (identical topology/vertex order; normals are
    Blender-smooth instead of the imported custom normals).
  * camera: EXACT canonical thin-lens parameters (sensor 36mm horizontal
    fit, focal length, focus distance, f-stop) with a look-at rotation
    derived from eye/target/up (see add_canonical_camera).
  * light: an AREA light emitting the canonical radiance, converted to
    Blender's Watt-based energy (see radiance_to_area_light_energy for
    the conversion + caveats).
  * materials: Principled-BSDF approximations of the canonical Mitsuba
    BSDFs (documented in the result JSON notes).

Usage (via the kit wrapper):
    ./scripts/blrun.sh --background --python scripts/scene_cornell.py -- \\
        --scene-json smoke/cornell.obj.scene.json \\
        --obj smoke/cornell.obj \\
        --engine CYCLES --resolution 256 256 --samples 16 \\
        --out smoke/cornell_cycles.png [--exr smoke/cornell_cycles.exr]

    # or with hardcoded canonical fallback values (warns):
    ./scripts/blrun.sh --background --python scripts/scene_cornell.py -- \\
        --defaults --engine EEVEE_NEXT --out smoke/cornell_eevee.png

Outputs:
    <out>.png           render (Standard view transform / sRGB)
    <out>.exr           optional (see --exr): RAW scene-linear float32
                        (EXR bypasses the view transform)
    <out>.json          result JSON next to the PNG: engine, resolution,
                        samples, render_seconds, camera params used,
                        mesh verification, non-black check, conversion notes
Exit codes: 0 = OK, 1 = render/verification failure, 2 = usage error.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from collections import Counter

import bpy
import mathutils
from mathutils import Matrix, Vector

from blender_kit import script_argv, clear_scene


TAG = "[scene_cornell]"

# ---------------------------------------------------------------------------
# Canonical scene fallback (mirrors webgpu-previz default_scene.py) — only
# used with --defaults (emits a warning).
# ---------------------------------------------------------------------------

CANONICAL_DEFAULTS = {
    "camera": {
        "eye": [0.0, 0.6, 3.2], "target": [0.0, -0.1, 0.0], "up": [0.0, 1.0, 0.0],
        "sensor_width_mm": 36.0, "sensor_height_mm": 24.0, "focal_length_mm": 35.0,
        "focus_distance_m": 2.5, "f_stop": 2.8, "near_m": 0.05, "far_m": 100.0,
    },
    "light": {
        "center_xyz": [0.0, 0.999, 0.0], "width_m": 0.5, "height_m": 0.5,
        "radiance_rgb": [15.0, 15.0, 15.0], "emit_y": 0.998, "normal": [0.0, -1.0, 0.0],
    },
    "box": {
        "size_m": 1.0,
        "left_rgb": [0.85, 0.10, 0.10], "right_rgb": [0.10, 0.20, 0.85],
        "back_rgb": [0.80, 0.80, 0.80], "ceiling_rgb": [0.80, 0.80, 0.80],
        "floor_rgb": [0.80, 0.80, 0.80],
    },
    "spheres": [
        {"center_xyz": [-0.30, -0.45, 0.10], "radius_m": 0.30, "material": "diffuse",
         "base_color_rgb": [0.85, 0.85, 0.85], "roughness": 0.05,
         "eta_rgb": [0.18299, 0.42108, 1.37340], "k_rgb": [3.42420, 2.34580, 1.77040]},
        {"center_xyz": [0.35, -0.55, -0.20], "radius_m": 0.20, "material": "conductor",
         "base_color_rgb": [0.7, 0.7, 0.7], "roughness": 0.05,
         "eta_rgb": [0.25486, 0.65147, 0.84259], "k_rgb": [3.17985, 2.45184, 2.18415]},
    ],
    "materials": [
        {"id": 0, "name": "floor", "kind": "diffuse", "color": [0.80, 0.80, 0.80]},
        {"id": 1, "name": "ceiling", "kind": "diffuse", "color": [0.80, 0.80, 0.80]},
        {"id": 2, "name": "back", "kind": "diffuse", "color": [0.80, 0.80, 0.80]},
        {"id": 3, "name": "left", "kind": "diffuse", "color": [0.85, 0.10, 0.10]},
        {"id": 4, "name": "right", "kind": "diffuse", "color": [0.10, 0.20, 0.85]},
        {"id": 5, "name": "ceiling_light", "kind": "emitter", "radiance": [15.0, 15.0, 15.0]},
        {"id": 6, "name": "diff_sphere", "kind": "diffuse", "color": [0.85, 0.85, 0.85]},
        {"id": 7, "name": "cond_sphere", "kind": "conductor", "color": [0.7, 0.7, 0.7],
         "roughness": 0.05, "eta": [0.18299, 0.42108, 1.37340],
         "k": [3.42420, 2.34580, 1.77040]},
    ],
    "mesh": {"sphere_lat_segments": 16, "sphere_lon_segments": 32},
}

MATERIAL_MAPPING_NOTES = (
    "Canonical Mitsuba BSDFs -> Blender Principled BSDF approximations: "
    "diffuse (walls, diff_sphere): Base Color = canonical color, Metallic 0, "
    "Roughness 0.0, Specular IOR Level 0.0 -> pure Lambertian lobe (matches "
    "Mitsuba 'diffuse'); NOTE Blender's Principled diffuse is Lambert at "
    "roughness 0, tiny implementation differences possible. "
    "conductor (cond_sphere): Metallic 1.0, Base Color = canonical base_color, "
    "Roughness = canonical roughness (both sides use GGX alpha = roughness^2); "
    "Mitsuba's explicit eta/k (copper IOR) is NOT mapped -- Blender's artistic "
    "metallic F0 differs; exact conductor-BSDF mapping is a follow-up. "
    "emitter (light quad, mat_5): the mesh quad does NOT emit (a Blender area "
    "light object provides ALL illumination); the quad shows the canonical "
    "radiance to camera rays only, via Emission shader gated by Light Path "
    "'Is Camera Ray' (camera rays -> Emission radiance 15; all other rays -> "
    "black diffuse, matching Mitsuba where the emitter surface is not a "
    "reflector). Cycles renders area lights invisible to camera rays by "
    "default (visible_camera=False), so the visible bright rect in Cycles "
    "comes from the quad; in EEVEE the same quad is visible to camera."
)

LIGHT_CONVERSION_NOTES = (
    "Canonical radiance L (W/sr/m^2) -> Blender area light energy E (W). "
    "Conversion used: E = pi * A * L, where A = width_m * height_m is the "
    "light area. Rationale (empirically calibrated in this container, "
    "Blender 4.5.13 LTS, Cycles CPU, EXR linear readback): a differential "
    "measurement of floor irradiance under an area light (energy E) vs an "
    "equal-size Emission mesh plane (strength S = radiance exactly) gave "
    "c = floor(E=1W)/floor(S=1) = 1.2668 for A=0.25 m^2, vs 1/(pi*A) = "
    "1.2732 predicted by the 'energy = total radiant flux' model "
    "(L = E/(pi*A) for a Lambertian emitter) -- within ~0.5%; energy scales "
    "linearly in radiance (measured exactly) and as 1/A at fixed radiance. "
    "VALIDATED: full-scene A/B vs the Mitsuba oracle (same mesh, 256x256, "
    "16 spp, EXR linear): mean-luminance ratio Blender/Mitsuba = 1.001 "
    "(0.1416 vs 0.1415), p50/p90 within ~1%, max 15.0 == 15.0 (the visible "
    "light-rect radiance is exact via the Emission shader). "
    "CAVEATS: (1) Cycles is calibrated to ~0.1% at these settings; EEVEE's "
    "area-light intensity model is NOT identical (EEVEE renders visibly "
    "dimmer, roughly 2/3 of Cycles at the same energy in this scene) -- "
    "exact per-engine radiometric mapping is a follow-up task; (2) the area "
    "light sits --light-offset-m (default 0.5 mm) BELOW the canonical light "
    "quad so it cannot be shadow-occluded by the (black) quad; (3) area "
    "light spread is Blender's default 180 deg (Lambertian, matching the "
    "canonical one-sided diffuse emitter); (4) colored radiance beyond "
    "scale-by-max-component is a follow-up. Canonical case: L=15, A=0.25 "
    "-> E = 11.781 W."
)


# ---------------------------------------------------------------------------
# Canonical tessellation (mirror of cornell_triangles.py formulas) — used to
# VERIFY imported OBJ geometry and to build the fallback mesh.
# ---------------------------------------------------------------------------

def canonical_mesh_triangles(spec: dict):
    """Rebuild the canonical Cornell mesh from the scene JSON spec.

    Returns (verts, tris, tri_mats):
      verts    : list of (x, y, z) — canonical vertex order
      tris     : list of (i0, i1, i2) — canonical winding
      tri_mats : list of mat_id per triangle
    """
    box = spec["box"]
    light = spec["light"]
    S = float(box["size_m"])
    lat = int(spec.get("mesh", {}).get("sphere_lat_segments", 16))
    lon = int(spec.get("mesh", {}).get("sphere_lon_segments", 32))

    verts = []
    tris = []
    tri_mats = []

    def add_vertex(pos):
        verts.append((float(pos[0]), float(pos[1]), float(pos[2])))
        return len(verts) - 1

    def add_quad(p0, p1, p2, p3, mat_id):
        i0 = add_vertex(p0)
        i1 = add_vertex(p1)
        i2 = add_vertex(p2)
        i3 = add_vertex(p3)
        tris.extend([(i0, i1, i2), (i0, i2, i3)])
        tri_mats.extend([mat_id, mat_id])

    # 5 walls (CCW front faces point into the box interior — canonical order).
    add_quad((-S, -S, S), (S, -S, S), (S, -S, -S), (-S, -S, -S), 0)   # floor
    add_quad((-S, S, -S), (S, S, -S), (S, S, S), (-S, S, S), 1)       # ceiling
    add_quad((-S, -S, -S), (S, -S, -S), (S, S, -S), (-S, S, -S), 2)   # back
    add_quad((-S, -S, -S), (-S, S, -S), (-S, S, S), (-S, -S, S), 3)   # left
    add_quad((S, -S, S), (S, S, S), (S, S, -S), (S, -S, -S), 4)       # right

    # Light rectangle (XZ plane, normal -Y, just below the ceiling).
    lw = float(light["width_m"]) / 2.0
    lh = float(light["height_m"]) / 2.0
    lx = float(light["center_xyz"][0])
    ly = float(light.get("emit_y", float(light["center_xyz"][1]) - 0.001))
    lz = float(light["center_xyz"][2])
    add_quad((lx - lw, ly, lz - lh), (lx + lw, ly, lz - lh),
             (lx + lw, ly, lz + lh), (lx - lw, ly, lz + lh), 5)

    # Spheres (UV tessellation, canonical winding).
    for sphere_idx, sp in enumerate(spec["spheres"]):
        mat_id = 6 if sp["material"] == "diffuse" else 7
        cx, cy, cz = (float(v) for v in sp["center_xyz"])
        r = float(sp["radius_m"])
        base = len(verts)
        for i in range(lat + 1):
            theta = math.pi * i / lat
            sin_t, cos_t = math.sin(theta), math.cos(theta)
            for j in range(lon + 1):
                phi = 2.0 * math.pi * j / lon
                px = cx + r * sin_t * math.cos(phi)
                py = cy + r * cos_t
                pz = cz + r * sin_t * math.sin(phi)
                verts.append((px, py, pz))
        for i in range(lat):
            for j in range(lon):
                v0 = base + i * (lon + 1) + j
                v1 = base + (i + 1) * (lon + 1) + j
                v2 = base + (i + 1) * (lon + 1) + j + 1
                v3 = base + i * (lon + 1) + j + 1
                tris.extend([(v0, v1, v2), (v0, v2, v3)])
                tri_mats.extend([mat_id, mat_id])

    return verts, tris, tri_mats


# ---------------------------------------------------------------------------
# Geometry: OBJ import (preferred) or canonical bmesh fallback
# ---------------------------------------------------------------------------

def import_obj_geometry(obj_path: str):
    """Import the exported canonical OBJ. Returns list of imported objects.

    Blender 4.5's OBJ importer (measured in this container) applies the
    OBJ Y-up -> Blender Z-up axis conversion as an OBJECT ROTATION
    (rotation_euler = (90deg, 0, 0)) while keeping the file coordinates in
    LOCAL space — i.e. local vertex positions/normals equal the canonical
    OBJ values exactly. We reset matrix_world to identity so WORLD
    coordinates are the canonical ones (matching the canonical camera and
    light, which are placed in canonical/world space). The scene-level
    verify_geometry() then asserts the world-space geometry against the
    canonical tessellation, so any import quirk fails loudly instead of
    silently shifting the scene.
    """
    before = set(bpy.data.objects.keys())
    bpy.ops.wm.obj_import(filepath=os.path.abspath(obj_path))
    new_objs = [bpy.data.objects[n] for n in sorted(set(bpy.data.objects.keys()) - before)]
    meshes = [o for o in new_objs if o.type == 'MESH']
    if not meshes:
        raise RuntimeError(f"OBJ import produced no mesh objects: {obj_path}")
    for o in meshes:
        o.matrix_world = Matrix.Identity(4)
        o.name = "CornellMesh" if len(meshes) == 1 else o.name
    bpy.context.view_layer.update()
    return meshes


def build_fallback_geometry(spec: dict):
    """Build the canonical mesh directly from the scene JSON via bmesh.

    Same vertex/triangle order as the canonical tessellation (B17 topology
    closure). Normals: smooth shading for the spheres (Blender-computed —
    approximately the canonical per-vertex radial normals), flat walls.
    """
    verts, tris, tri_mats = canonical_mesh_triangles(spec)
    import bmesh
    me = bpy.data.meshes.new("CornellMesh")
    bm = bmesh.new()
    bm_verts = [bm.verts.new(v) for v in verts]
    for (i0, i1, i2), mat_id in zip(tris, tri_mats):
        f = bm.faces.new((bm_verts[i0], bm_verts[i1], bm_verts[i2]))
        f.material_index = mat_id
        # Sphere faces smooth (canonical uses smooth per-vertex normals),
        # walls flat (canonical normals are per-face constants anyway).
        f.smooth = mat_id in (6, 7)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new("CornellMesh", me)
    bpy.context.scene.collection.objects.link(obj)
    return [obj]


def verify_geometry(mesh_objs, spec: dict) -> dict:
    """Verify imported geometry against the canonical tessellation.

    Fatal checks: vertex/face counts, vertex-coordinate multiset (spatial
    hash match, 1e-5 tolerance), face multiset via matched vertex indices
    (winding-insensitive). Diagnostic: winding_match_fraction = fraction of
    imported faces whose corner ORDER equals the canonical (v0,v1,v2)
    winding (informational — Blender renders both faces; the canonical
    winding itself is asserted by the exporter's round-trip tests).
    """
    exp_verts, exp_tris, _tri_mats = canonical_mesh_triangles(spec)

    imp_verts = []
    imp_poly_idx = []   # per polygon: global indices (into imp_verts) of corners
    imp_poly_count = 0
    for o in mesh_objs:
        mw = o.matrix_world
        base = len(imp_verts)
        for v in o.data.vertices:
            w = mw @ v.co
            imp_verts.append((w.x, w.y, w.z))
        for p in o.data.polygons:
            imp_poly_idx.append(tuple(base + vi for vi in p.vertices))
            imp_poly_count += 1

    stats = {
        "expected_vertex_count": len(exp_verts),
        "expected_triangle_count": len(exp_tris),
        "imported_vertex_count": len(imp_verts),
        "imported_polygon_count": imp_poly_count,
    }
    errors = []
    if len(imp_verts) != len(exp_verts):
        errors.append(f"vertex count {len(imp_verts)} != canonical {len(exp_verts)}")
    if imp_poly_count != len(exp_tris):
        errors.append(f"face count {imp_poly_count} != canonical {len(exp_tris)}")

    # Tolerance vertex matching (float32-imported vs float64-recompute) via a
    # spatial hash. Sorting near-equal float32/float64 values can permute
    # differently between the two lists, so sorted-zip comparison produces
    # spurious mismatches — greedy bucket matching does not.
    tol = 1e-5
    cell = 1e-4  # spatial hash cell (10x tol)

    def _bucket_key(p):
        return (int(math.floor(p[0] / cell)),
                int(math.floor(p[1] / cell)),
                int(math.floor(p[2] / cell)))

    if not errors:
        buckets_v = {}
        for qi, q in enumerate(imp_verts):
            buckets_v.setdefault(_bucket_key(q), []).append(qi)
        used_imp = set()

        def match_vertex(p):
            kx, ky, kz = _bucket_key(p)
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for dz in (-1, 0, 1):
                        for qi in buckets_v.get((kx + dx, ky + dy, kz + dz), ()):
                            if qi in used_imp:
                                continue
                            q = imp_verts[qi]
                            if (abs(p[0] - q[0]) <= tol
                                    and abs(p[1] - q[1]) <= tol
                                    and abs(p[2] - q[2]) <= tol):
                                used_imp.add(qi)
                                return qi
            return None

        vertex_remap = {}
        bad = 0
        for pi, p in enumerate(exp_verts):
            qi = match_vertex(p)
            if qi is None:
                bad += 1
            else:
                vertex_remap[pi] = qi
        stats["vertex_multiset_mismatches"] = bad
        if bad:
            errors.append(f"{bad} vertices have no canonical counterpart")

        # Face multiset + winding, compared via matched vertex INDICES
        # (exact — no float tolerance needed once vertices are matched).
        # Unordered key = frozenset of the 3 corner indices (degenerate
        # index-triples do not occur in the canonical mesh).
        imp_face_counter = Counter(frozenset(gi) for gi in imp_poly_idx)
        imp_ordered_counter = Counter(imp_poly_idx)
        bad_f = 0
        winding_matches = 0
        for (i0, i1, i2) in exp_tris:
            if i0 not in vertex_remap or i1 not in vertex_remap \
                    or i2 not in vertex_remap:
                bad_f += 1
                continue
            j = (vertex_remap[i0], vertex_remap[i1], vertex_remap[i2])
            key = frozenset(j)
            if imp_face_counter.get(key, 0) > 0:
                imp_face_counter[key] -= 1
                if imp_ordered_counter.get(j, 0) > 0:
                    imp_ordered_counter[j] -= 1
                    winding_matches += 1
            else:
                bad_f += 1
        stats["face_multiset_mismatches"] = bad_f
        if bad_f:
            errors.append(f"{bad_f} faces have no canonical counterpart")
        stats["winding_matching_faces"] = winding_matches
        stats["winding_match_fraction"] = round(
            winding_matches / max(1, imp_poly_count), 4)

    stats["verified"] = not errors
    stats["errors"] = errors
    return stats


# ---------------------------------------------------------------------------
# Materials
# ---------------------------------------------------------------------------

def _set_bsdf_input(bsdf, names, value):
    """Set a Principled BSDF input tolerating Blender 4.x renames."""
    for n in names:
        if n in bsdf.inputs:
            bsdf.inputs[n].default_value = value
            return n
    return None


def build_canonical_materials(spec: dict) -> dict:
    """Create the 8 canonical materials (cornell_mat_<id>) and return them
    keyed by mat id. Approximations documented in MATERIAL_MAPPING_NOTES."""
    mats = {}
    for m in spec["materials"]:
        mat_id = int(m["id"])
        kind = m["kind"]
        mat = bpy.data.materials.new(f"cornell_mat_{mat_id}")
        mat.use_nodes = True
        nt = mat.node_tree
        if kind == "emitter":
            # Light quad: camera-gated Emission (canonical radiance), black
            # diffuse for every other ray. The area light object provides
            # ALL illumination (avoids double emission in Cycles).
            for n in list(nt.nodes):
                nt.nodes.remove(n)
            out = nt.nodes.new("ShaderNodeOutputMaterial")
            emis = nt.nodes.new("ShaderNodeEmission")
            radiance = m.get("radiance", [1.0, 1.0, 1.0])
            # Emission radiance = Color * Strength; use Color = radiance,
            # Strength = 1 (radiance values may exceed 1).
            emis.inputs["Color"].default_value = (radiance[0], radiance[1], radiance[2], 1.0)
            emis.inputs["Strength"].default_value = 1.0
            black = nt.nodes.new("ShaderNodeBsdfDiffuse")
            black.inputs["Color"].default_value = (0.0, 0.0, 0.0, 1.0)
            mix = nt.nodes.new("ShaderNodeMixShader")
            lp = nt.nodes.new("ShaderNodeLightPath")
            nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs["Fac"])
            nt.links.new(black.outputs["BSDF"], mix.inputs[1])   # Fac=0: non-camera
            nt.links.new(emis.outputs["Emission"], mix.inputs[2])  # Fac=1: camera
            nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
        else:
            bsdf = nt.nodes.get("Principled BSDF")
            assert bsdf is not None
            color = m.get("color", [0.7, 0.7, 0.7])
            bsdf.inputs["Base Color"].default_value = (color[0], color[1], color[2], 1.0)
            _set_bsdf_input(bsdf, ["Metallic"], 1.0 if kind == "conductor" else 0.0)
            if kind == "conductor":
                rough = float(m.get("roughness", 0.05))
                _set_bsdf_input(bsdf, ["Roughness"], rough)
            else:
                # Pure Lambertian: roughness 0 + no dielectric specular.
                _set_bsdf_input(bsdf, ["Roughness"], 0.0)
                _set_bsdf_input(bsdf, ["Specular IOR Level", "Specular"], 0.0)
        mats[mat_id] = mat
    return mats


def assign_materials(mesh_objs, mats: dict):
    """Replace imported MTL material slots with the canonical materials.

    Imported slots are named mat_<id> by the exporter's MTL. Also removes
    the now-unused imported materials to keep the .blend clean.
    """
    imported_materials = set()
    for o in mesh_objs:
        for slot in o.material_slots:
            old = slot.material
            if old is not None:
                imported_materials.add(old.name)
                m = _parse_mat_id(old.name)
                if m is None or m not in mats:
                    raise RuntimeError(
                        f"cannot map imported material {old.name!r} to a "
                        f"canonical mat id (expected mat_0..mat_7)")
                slot.material = mats[m]
    for name in sorted(imported_materials):
        mat = bpy.data.materials.get(name)
        if mat is not None and mat.users == 0:
            bpy.data.materials.remove(mat)


def _parse_mat_id(name: str):
    if name.startswith("mat_") and name[4:].isdigit():
        return int(name[4:])
    return None


# ---------------------------------------------------------------------------
# Light
# ---------------------------------------------------------------------------

def radiance_to_area_light_energy(radiance_rgb, width_m: float, height_m: float):
    """Canonical radiance (W/sr/m^2) -> Blender area light energy (W).

    Model: E = pi * A * L_max, light color = L / L_max. See
    LIGHT_CONVERSION_NOTES for the calibration and caveats. Returns
    (energy_watts, color_rgb).
    """
    area = width_m * height_m
    lmax = max(float(c) for c in radiance_rgb)
    if lmax <= 0.0:
        return 0.0, (1.0, 1.0, 1.0)
    energy = math.pi * area * lmax
    color = tuple(float(c) / lmax for c in radiance_rgb)
    return energy, color


def add_canonical_light(spec: dict, light_offset_m: float):
    """Area light emitting the canonical radiance (see notes)."""
    light = spec["light"]
    w = float(light["width_m"])
    h = float(light["height_m"])
    cx, cy, cz = (float(v) for v in light["center_xyz"])
    emit_y = float(light.get("emit_y", cy - 0.001))
    # Placed slightly BELOW the (black, non-emitting) mesh light quad so it
    # is never shadow-occluded by it; canonical quad stays at emit_y.
    ly = emit_y - light_offset_m

    ld = bpy.data.lights.new("CornellLight", type='AREA')
    if abs(w - h) < 1e-9:
        ld.shape = 'SQUARE'
        ld.size = w
    else:
        ld.shape = 'RECTANGLE'
        ld.size_x = w
        ld.size_y = h
    energy, color = radiance_to_area_light_energy(light["radiance_rgb"], w, h)
    ld.energy = energy
    ld.color = color
    lo = bpy.data.objects.new("CornellLightObj", ld)
    lo.location = (cx, ly, cz)
    # Area light emits along local -Z; canonical light normal is (0,-1,0).
    # Rx(-90deg) maps local -Z -> world -Y and local +Y -> world -Z, so
    # size_x spans world X (width) and size_y spans world Z (height).
    lo.rotation_euler = (math.radians(-90.0), 0.0, 0.0)
    bpy.context.scene.collection.objects.link(lo)
    return lo, {"energy_watts": energy, "color": list(color), "location": [cx, ly, cz],
                "size_m": [w, h], "area_m2": w * h,
                "offset_below_quad_m": light_offset_m}


# ---------------------------------------------------------------------------
# Camera
# ---------------------------------------------------------------------------

def add_canonical_camera(spec: dict, enable_dof: bool = True):
    """Create the canonical thin-lens camera.

    LOOK-AT CONVENTION (matches the canonical Mitsuba/WebGPU basis):
        forward = normalize(target - eye)
        right   = cross(forward, up)
        cam_up  = cross(right, forward)
    Blender cameras look along local -Z with local +Y up, so the
    camera-to-world rotation columns are:
        X_cam = right, Y_cam = cam_up, Z_cam = -forward
    (Compare Mitsuba: +Z local is forward — render_oracle.py uses columns
    right/cam_up/forward; we only flip the third column.)

    FOV: sensor_fit HORIZONTAL + sensor_width from the spec so Blender's
    horizontal FOV = canonical fov_x = 2*atan(sensor_w/(2*focal)) EXACTLY;
    vertical FOV follows the render aspect (same convention as the
    WebGPU candidate: fov_x primary).
    """
    cam = spec["camera"]
    eye = Vector((float(cam["eye"][0]), float(cam["eye"][1]), float(cam["eye"][2])))
    target = Vector((float(cam["target"][0]), float(cam["target"][1]), float(cam["target"][2])))
    up = Vector((float(cam["up"][0]), float(cam["up"][1]), float(cam["up"][2])))

    forward = (target - eye).normalized()
    right = forward.cross(up).normalized()
    cam_up = right.cross(forward)

    # Rows of R are (right, cam_up, -forward) components arranged so that
    # R's COLUMNS are right / cam_up / -forward (camera-space -> world).
    R = Matrix((
        (right.x, cam_up.x, -forward.x),
        (right.y, cam_up.y, -forward.y),
        (right.z, cam_up.z, -forward.z),
    ))

    cam_data = bpy.data.cameras.new("CornellCamera")
    cam_data.sensor_fit = 'HORIZONTAL'
    cam_data.sensor_width = float(cam["sensor_width_mm"])
    cam_data.lens = float(cam["focal_length_mm"])
    cam_data.clip_start = float(cam["near_m"])
    cam_data.clip_end = float(cam["far_m"])

    dof_info = {"use_dof": False}
    if enable_dof:
        # Blender DoF: focus_distance is the axial distance from the camera
        # to the plane of sharp focus (same semantics as the canonical
        # focus_distance_m); aperture_fstop sets aperture radius =
        # lens / (2 * fstop) — the same formula the canonical camera uses
        # (aperture_radius_mm = focal / (2 * f_stop)).
        cam_data.dof.use_dof = True
        cam_data.dof.focus_distance = float(cam["focus_distance_m"])
        cam_data.dof.aperture_fstop = float(cam["f_stop"])
        dof_info = {
            "use_dof": True,
            "focus_distance_m": cam_data.dof.focus_distance,
            "aperture_fstop": cam_data.dof.aperture_fstop,
        }

    cam_obj = bpy.data.objects.new("Camera", cam_data)
    cam_obj.location = eye
    cam_obj.rotation_mode = 'QUATERNION'
    cam_obj.rotation_quaternion = R.to_quaternion()
    bpy.context.scene.collection.objects.link(cam_obj)
    bpy.context.scene.camera = cam_obj
    bpy.context.view_layer.update()

    # Verify the look-at (all-black renders = wrong look direction).
    q = cam_obj.matrix_world.to_quaternion()
    got_fwd = (q @ Vector((0.0, 0.0, -1.0))).normalized()
    got_up = (q @ Vector((0.0, 1.0, 0.0))).normalized()
    fwd_err = math.degrees(got_fwd.angle(forward))
    up_err = math.degrees(got_up.angle(cam_up))
    fov_x_blender = math.degrees(2.0 * math.atan(
        cam_data.sensor_width / (2.0 * cam_data.lens)))
    verification = {
        "forward_error_deg": round(fwd_err, 6),
        "up_error_deg": round(up_err, 6),
        "lookat_verified": fwd_err < 1e-3 and up_err < 1e-3,
        "blender_fov_x_deg": round(fov_x_blender, 6),
    }
    if not verification["lookat_verified"]:
        raise RuntimeError(f"camera look-at verification failed: {verification}")

    return cam_obj, {
        "eye": list(cam["eye"]),
        "target": list(cam["target"]),
        "up": list(cam["up"]),
        "forward": [round(c, 6) for c in forward],
        "right": [round(c, 6) for c in right],
        "cam_up": [round(c, 6) for c in cam_up],
        "rotation_quaternion": [round(c, 6) for c in cam_obj.rotation_quaternion],
        "sensor_fit": "HORIZONTAL",
        "sensor_width_mm": cam_data.sensor_width,
        "lens_mm": cam_data.lens,
        "clip_start_m": cam_data.clip_start,
        "clip_end_m": cam_data.clip_end,
        "dof": dof_info,
        "verification": verification,
    }


# ---------------------------------------------------------------------------
# World / render settings
# ---------------------------------------------------------------------------

def add_black_world():
    world = bpy.data.worlds.new("CornellWorld")
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (0.0, 0.0, 0.0, 1.0)
    bg.inputs["Strength"].default_value = 0.0
    bpy.context.scene.world = world


ENGINE_ALIASES = {
    "CYCLES": "CYCLES",
    "EEVEE_NEXT": "BLENDER_EEVEE_NEXT",
    "EEVEE": "BLENDER_EEVEE_NEXT",
    "BLENDER_EEVEE_NEXT": "BLENDER_EEVEE_NEXT",
    "WORKBENCH": "BLENDER_WORKBENCH",
    "BLENDER_WORKBENCH": "BLENDER_WORKBENCH",
}


def configure_render(engine_id: str, width: int, height: int, samples: int,
                     denoise: bool, max_bounces: int):
    scene = bpy.context.scene
    scene.render.engine = engine_id
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    # Kit convention: Standard view transform so authored colors read true
    # in the PNG (display-referred). EXR output bypasses the view transform
    # (raw scene-linear) — see save_render_outputs.
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'

    if engine_id == "CYCLES":
        scene.cycles.device = 'CPU'
        scene.cycles.samples = samples
        scene.cycles.use_denoising = bool(denoise)
        # Deterministic sample count (no adaptive early-out).
        scene.cycles.use_adaptive_sampling = False
        scene.cycles.max_bounces = max_bounces
        # Mitsuba oracle uses a box reconstruction filter.
        try:
            scene.cycles.filter_type = 'BOX'
        except Exception as e:  # noqa: BLE001
            print(f"{TAG} note: could not set Cycles BOX filter: {e}")
    elif engine_id == "BLENDER_EEVEE_NEXT":
        scene.eevee.taa_render_samples = samples
    else:  # WORKBENCH — fast framing debug (no light transport)
        scene.display.shading.light = 'STUDIO'
        scene.display.shading.color_type = 'MATERIAL'
        scene.display.shading.show_shadows = True


def save_render_outputs(png_path: str, exr_path=None) -> dict:
    """Render once per requested file format (PNG display-referred via
    Standard view transform; EXR raw scene-linear float32 — Blender's EXR
    writer bypasses the view transform, verified: emission strength 15
    reads back as exactly 15.0)."""
    scene = bpy.context.scene
    paths = {}
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.filepath = png_path
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    paths["png"] = os.path.abspath(png_path)
    if exr_path:
        scene.render.image_settings.file_format = 'OPEN_EXR'
        scene.render.image_settings.color_depth = '32'
        scene.render.filepath = exr_path
        bpy.ops.render.render(write_still=True)
        paths["exr"] = os.path.abspath(exr_path)
    return {"render_seconds": round(time.time() - t0, 3), "paths": paths}


def check_non_black(png_path: str, threshold: float = 0.05) -> dict:
    """Verify >threshold of pixels in the SAVED PNG are non-black.

    Prefers Pillow (kit-installed) on the actual file; falls back to
    reading the PNG through Blender's imbuf if Pillow is unavailable.
    """
    try:
        from PIL import Image
        im = Image.open(png_path).convert("RGB")
        pixels = im.getdata()
        total = im.width * im.height
        non_black = sum(1 for p in pixels if max(p) > 0)
    except ImportError:
        img = bpy.data.images.load(os.path.abspath(png_path))
        px = list(img.pixels)
        channels = img.channels
        total = img.size[0] * img.size[1]
        non_black = sum(
            1 for i in range(total)
            if max(px[i * channels:i * channels + 3]) > 0.0)
        bpy.data.images.remove(img)
    fraction = non_black / max(1, total)
    return {
        "total_pixels": total,
        "non_black_pixels": non_black,
        "non_black_fraction": round(fraction, 5),
        "threshold": threshold,
        "pass": fraction > threshold,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args(argv):
    p = argparse.ArgumentParser(
        description="Render the canonical Cornell scene (WebGPU PreViz parity).")
    src = p.add_mutually_exclusive_group()
    src.add_argument("--scene-json", help="path to the .scene.json sidecar "
                                          "from export_cornell_obj.py")
    src.add_argument("--defaults", action="store_true",
                     help="use hardcoded canonical values (WARNs)")
    p.add_argument("--obj", default=None,
                   help="path to the exported canonical OBJ (preferred: "
                        "identical-geometry closure). If omitted, the "
                        "canonical mesh is rebuilt from the scene JSON.")
    p.add_argument("--engine", default="CYCLES",
                   choices=["CYCLES", "EEVEE_NEXT", "EEVEE",
                            "BLENDER_EEVEE_NEXT", "WORKBENCH",
                            "BLENDER_WORKBENCH"],
                   help="render engine (default CYCLES; EEVEE_NEXT needs "
                        "Xvfb via blrun.sh)")
    p.add_argument("--resolution", nargs=2, type=int, metavar=("W", "H"),
                   default=[256, 256], help="render resolution (default 256 256)")
    p.add_argument("--samples", type=int, default=16,
                   help="render samples (Cycles spp / EEVEE TAA samples)")
    p.add_argument("--out", required=True, metavar="PNG",
                   help="output PNG path (result JSON is written next to it)")
    p.add_argument("--exr", default=None, metavar="EXR",
                   help="optional raw scene-linear EXR output path")
    p.add_argument("--denoise", action="store_true",
                   help="enable Cycles denoising (default off: keeps the "
                        "output statistically comparable to the oracle)")
    p.add_argument("--max-bounces", type=int, default=6,
                   help="Cycles total max bounces (default 6, canonical "
                        "intent; Mitsuba max_depth = bounces + 1)")
    p.add_argument("--no-dof", action="store_true",
                   help="disable depth of field (default: canonical DoF from "
                        "the scene JSON; useful for framing/parity debug)")
    p.add_argument("--light-offset-m", type=float, default=0.0005,
                   help="area light offset below the mesh light quad in "
                        "meters (default 0.0005; avoids self-occlusion)")
    return p.parse_args(argv)


def main() -> int:
    args = parse_args(script_argv())
    print(f"{TAG} args: {vars(args)}")

    # --- scene spec ------------------------------------------------------
    if args.scene_json:
        with open(args.scene_json) as f:
            spec = json.load(f)
        print(f"{TAG} scene spec: {args.scene_json} "
              f"(scene_hash={spec.get('scene_hash')})")
    elif args.defaults:
        spec = CANONICAL_DEFAULTS
        print(f"{TAG} WARNING: --defaults — using hardcoded canonical "
              f"fallback values (not the exported sidecar). Prefer "
              f"--scene-json from export_cornell_obj.py.")
    else:
        print(f"{TAG} ERROR: --scene-json or --defaults required", file=sys.stderr)
        return 2

    # --- build -----------------------------------------------------------
    clear_scene()
    add_black_world()

    mesh_objs = None
    geometry_source = None
    if args.obj:
        if not os.path.exists(args.obj):
            print(f"{TAG} ERROR: --obj not found: {args.obj}", file=sys.stderr)
            return 2
        mesh_objs = import_obj_geometry(args.obj)
        geometry_source = "obj_import"
        print(f"{TAG} imported OBJ {args.obj} -> "
              f"{[o.name for o in mesh_objs]}")
    else:
        mesh_objs = build_fallback_geometry(spec)
        geometry_source = "canonical_bmesh_fallback"
        print(f"{TAG} WARNING: no --obj given; built canonical mesh from the "
              f"scene JSON (topology identical; normals are Blender-smooth "
              f"approximations of the canonical per-vertex normals)")

    mats = build_canonical_materials(spec)
    assign_materials(mesh_objs, mats)

    light_obj, light_info = add_canonical_light(spec, args.light_offset_m)
    cam_obj, cam_info = add_canonical_camera(spec, enable_dof=not args.no_dof)

    # --- geometry verification (B17 closure) ------------------------------
    geo_stats = verify_geometry(mesh_objs, spec)
    print(f"{TAG} geometry verification ({geometry_source}): "
          f"verts {geo_stats['imported_vertex_count']}/"
          f"{geo_stats['expected_vertex_count']}, "
          f"faces {geo_stats['imported_polygon_count']}/"
          f"{geo_stats['expected_triangle_count']}, "
          f"verified={geo_stats['verified']}, "
          f"winding_match={geo_stats.get('winding_match_fraction')}")
    if not geo_stats["verified"]:
        for e in geo_stats["errors"]:
            print(f"{TAG} GEOMETRY ERROR: {e}", file=sys.stderr)
        return 1

    # --- render -----------------------------------------------------------
    engine_id = ENGINE_ALIASES[args.engine]
    width, height = args.resolution
    configure_render(engine_id, width, height, args.samples,
                     args.denoise, args.max_bounces)

    png_path = os.path.abspath(args.out)
    out_dir = os.path.dirname(png_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    exr_path = os.path.abspath(args.exr) if args.exr else None

    print(f"{TAG} rendering: engine={engine_id} {width}x{height} "
          f"samples={args.samples} dof={cam_info['dof']['use_dof']} -> {png_path}")
    try:
        result = save_render_outputs(png_path, exr_path)
    except RuntimeError as e:
        print(f"{TAG} ERROR: render failed: {e}", file=sys.stderr)
        return 1

    png_path = result["paths"]["png"]
    exr_path = result["paths"].get("exr")
    if not os.path.exists(png_path) or os.path.getsize(png_path) == 0:
        print(f"{TAG} ERROR: PNG output missing/empty: {png_path}", file=sys.stderr)
        return 1

    non_black = check_non_black(png_path)
    print(f"{TAG} non-black check: {non_black['non_black_pixels']}/"
          f"{non_black['total_pixels']} pixels "
          f"({non_black['non_black_fraction']:.1%}) — "
          f"{'PASS' if non_black['pass'] else 'FAIL'}")
    if not non_black["pass"]:
        print(f"{TAG} ERROR: render is (nearly) all-black — camera look-at or "
              f"winding problem. Debug hints: try --engine WORKBENCH to check "
              f"framing, or render without --obj.", file=sys.stderr)
        return 1

    # --- result JSON ------------------------------------------------------
    report = {
        "engine": engine_id,
        "engine_arg": args.engine,
        "blender_version": bpy.app.version_string,
        "resolution": [width, height],
        "samples": args.samples,
        "denoising": bool(args.denoise),
        "max_bounces": args.max_bounces if engine_id == "CYCLES" else None,
        "render_seconds": result["render_seconds"],
        "png_path": png_path,
        "exr_path": exr_path,
        "png_color": "display-referred (Standard view transform + sRGB OETF)",
        "exr_color": "raw scene-linear float32 (view transform bypassed)",
        "scene_json": os.path.abspath(args.scene_json) if args.scene_json else None,
        "scene_hash": spec.get("scene_hash"),
        "geometry_source": geometry_source,
        "geometry_verification": geo_stats,
        "camera_params_used": cam_info,
        "light_params_used": light_info,
        "material_mapping_notes": MATERIAL_MAPPING_NOTES,
        "light_conversion_notes": LIGHT_CONVERSION_NOTES,
        "non_black": non_black,
    }
    json_path = os.path.splitext(png_path)[0] + ".json"
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2, sort_keys=True)
    print(f"{TAG} wrote {json_path}")
    print(f"{TAG} done: {png_path} "
          f"({non_black['non_black_fraction']:.1%} non-black, "
          f"{result['render_seconds']}s render)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
