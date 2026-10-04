"""
annotate.py — render-time annotation layer for vision-first scene looks.

Builds a DISPOSABLE set of objects that make a rendered image honest for a
vision-capable agent (blender-vision-kit D5):

  1. 1m ground grid  — scale + position cues (kills "how big is that?" and
     chirality misreads when paired with the axis gnomon)
  2. Axis gnomon     — 1m RGB axis arrows at world origin (X=red, Y=green,
     Z=blue); the vision agent confirms handedness via the gnomon (law L2)
  3. Object labels   — top-N objects by bbox diagonal get a FONT text
     billboard (id + index), aimed at the render camera per angle
  4. Flag boxes      — validator-flagged objects get a red wireframe bbox

LAW (D5): annotations are RENDER-TIME ONLY and are never saved. look.py
deletes the whole layer after rendering and provides NO way to save a
.blend. Every object carries the `KIT_ANNOT_` name prefix so a stray
survivor is trivially identified (and testable).

Design constraints:
  - Workbench renders GEOMETRY, not empties/overlays — so everything is
    real mesh geometry (thin boxes) or FONT objects.
  - FONT text renders with the built-in font in Workbench MATERIAL mode.
  - Labels aim per-angle: the caller calls `aim_labels_at(cam_loc)` before
    each render; look.py computes each angle's camera location with the
    same VIEW_ANGLES math as viewport_capture, so aim == render camera.
"""
import math

import bpy
from mathutils import Vector


ANNOT_PREFIX = "KIT_ANNOT_"

# Annotation materials are created once per layer and named (deleted with
# the layer). MATERIAL color_type reads mat.diffuse_color — set both it
# and Principled Base Color for engine parity (upstream law 6).
_COLORS = {
    "grid":    (0.45, 0.45, 0.48, 1.0),
    "axis_x":  (0.85, 0.12, 0.12, 1.0),
    "axis_y":  (0.15, 0.75, 0.20, 1.0),
    "axis_z":  (0.20, 0.35, 0.90, 1.0),
    "label":   (0.95, 0.85, 0.10, 1.0),
    "flag":    (0.95, 0.08, 0.08, 1.0),
}


def _make_mat(name: str):
    key = name.replace(ANNOT_PREFIX + "mat_", "")
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    try:
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf is not None and "Base Color" in bsdf.inputs:
            bsdf.inputs["Base Color"].default_value = _COLORS[key]
    except Exception:
        bsdf = None
    mat.diffuse_color = _COLORS[key]
    return mat


# ---------------------------------------------------------------------------
# D15 display-color sync (QA #4): workbench MATERIAL shading shows
# mat.diffuse_color, so node-authored Principled Base Colors (imported
# glTF/FBX, procedural authoring) render as default GRAY — the vision
# agent sees gray where the design intends red/blue and nothing detects
# the loss. These are STANDALONE functions (not part of the annotation
# layer) so `--no-annotate` looks stay honest too; look.py calls sync
# before the render pass and restore in its finally (zero-residue law).
# ---------------------------------------------------------------------------

# material.name -> color_source, read by look.py's manifest after sync
_COLOR_SOURCE = {}
_BSDF_DEFAULT_BASE = (0.8, 0.8, 0.8, 1.0)


def sync_display_colors(threshold: float = 0.05) -> dict:
    """Make workbench MATERIAL renders show node-authored base colors.

    Judges each UNIQUE material used by non-annotation mesh slots:
      - 'node': use_nodes + UNLINKED Principled 'Base Color' that is not
        the untouched default gray and differs from diffuse_color by more
        than `threshold` on any channel -> diffuse_color is overridden
        (RGB only, alpha forced 1.0); original captured for
        restore_display_colors().
      - 'nontrivial': linked/texture-driven or otherwise non-syncable —
        counted so the agent knows color identity is unreliable there.
      - 'linked': library-linked material — read-only, counted.
      - 'viewport': diffuse_color already honest (nothing to do).
    Returns {"synced": [...], "nontrivial": [...], "linked": [...],
    "originals": {mat_name: (material, rgba_tuple)}}. Never raises on an
    individual material (per-material try/except)."""
    _COLOR_SOURCE.clear()
    seen, originals = set(), {}
    synced, nontrivial, linked = [], [], []
    for o in bpy.context.scene.objects:
        if o.name.startswith(ANNOT_PREFIX) or o.type != 'MESH':
            continue
        for slot in o.material_slots:
            mat = slot.material
            if mat is None or mat.name in seen:
                continue
            seen.add(mat.name)
            try:
                if mat.library is not None:
                    linked.append(mat.name)
                    _COLOR_SOURCE[mat.name] = "linked"
                    continue
                base = None
                if mat.use_nodes and mat.node_tree:
                    bsdf = mat.node_tree.nodes.get("Principled BSDF")
                    if bsdf is not None and "Base Color" in bsdf.inputs:
                        inp = bsdf.inputs["Base Color"]
                        if inp.is_linked:
                            _COLOR_SOURCE[mat.name] = "nontrivial"
                            nontrivial.append(mat.name)
                            continue
                        base = tuple(inp.default_value)
                if base is None:
                    _COLOR_SOURCE[mat.name] = "viewport"
                    continue
                dc = tuple(mat.diffuse_color)
                untouched_default = all(abs(base[i] - _BSDF_DEFAULT_BASE[i]) < 1e-3
                                        for i in range(4))
                if untouched_default or all(
                        abs(base[i] - dc[i]) <= threshold for i in range(3)):
                    _COLOR_SOURCE[mat.name] = "viewport"
                    continue  # author never touched it, or already honest
                originals[mat.name] = (mat, dc)
                mat.diffuse_color = (base[0], base[1], base[2], 1.0)
                synced.append(mat.name)
                _COLOR_SOURCE[mat.name] = "node"
            except Exception:
                _COLOR_SOURCE.setdefault(mat.name, "nontrivial")
                if mat.name not in nontrivial and mat.name not in linked \
                        and mat.name not in synced:
                    nontrivial.append(mat.name)
    return {"synced": synced, "nontrivial": nontrivial, "linked": linked,
            "originals": originals}


def restore_display_colors(state: dict) -> int:
    """Restore pre-sync diffuse_colors (D15 zero-residue half)."""
    n = 0
    for mat_name, (mat, rgba) in (state or {}).get("originals", {}).items():
        try:
            mat.diffuse_color = rgba
            n += 1
        except Exception:
            pass
    return n


def _thin_box(name: str, p0, p1, thickness: float, mat) -> bpy.types.Object:
    """Axis-aligned thin box from p0 to p1 (world coords), origin at midpoint."""
    p0 = Vector(p0)
    p1 = Vector(p1)
    mid = (p0 + p1) / 2.0
    dims = [max(abs(p1[i] - p0[i]), thickness) for i in range(3)]
    # Don't let a long axis get clamped to thickness
    for i in range(3):
        span = abs(p1[i] - p0[i])
        dims[i] = span if span > thickness else thickness
    mesh = bpy.data.meshes.new(name)
    cube = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(cube)
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bm.to_mesh(mesh)
    bm.free()
    cube.scale = dims  # scale stays on the annotation object; it is disposable
    cube.location = mid
    cube.data.materials.append(mat)
    return cube


def _scene_bounds(meshes) -> tuple:
    """(min, max) world bounds over meshes; None if no meshes."""
    pts = []
    for o in meshes:
        for corner in o.bound_box:
            pts.append(o.matrix_world @ type(o.location)(corner))
    if not pts:
        return None
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return mn, mx


def build_annotation_layer(flagged_ids=None, label_ids=None,
                           grid=True, gnomon=True) -> dict:
    """Build the annotation layer in the current scene.

    flagged_ids: iterable of object names to outline in red (validator P0/P1)
    label_ids:   iterable of (name, index) pairs, top-N by bbox diagonal
    Returns {"objects": [...], "labels": [...]} for later aiming/deletion.
    """
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH'
              and not o.name.startswith(ANNOT_PREFIX)]
    bounds = _scene_bounds(meshes)
    mats = {k: _make_mat(f"{ANNOT_PREFIX}mat_{k}") for k in _COLORS}
    made = {"objects": [], "labels": []}
    if bounds is None:
        return made
    mn, mx = bounds
    margin = 1.0
    x0, x1 = math.floor(mn.x - margin), math.ceil(mx.x + margin)
    y0, y1 = math.floor(mn.y - margin), math.ceil(mx.y + margin)
    z_floor = 0.0

    # --- ground grid: 1m lines (thin boxes 4mm above floor to avoid z-fight)
    gz = z_floor + 0.004
    t = 0.006
    if grid:
        for gx in range(x0, x1 + 1):
            made["objects"].append(_thin_box(
                f"{ANNOT_PREFIX}grid_x{gx}", (gx, y0, gz), (gx, y1, gz), t,
                mats["grid"]))
        for gy in range(y0, y1 + 1):
            made["objects"].append(_thin_box(
                f"{ANNOT_PREFIX}grid_y{gy}", (x0, gy, gz), (x1, gy, gz), t,
                mats["grid"]))

    # --- axis gnomon near the scene center, offset to the SW so it lands
    # inside standard 4-angle framing but off the center object (a gnomon
    # at world origin sits INSIDE the centered subject; at the scene min
    # corner it is out of frame for large grounds — both measured).
    if gnomon:
        g = 0.03
        cx_off = (mn.x + mx.x) / 2.0 - 1.5
        cy_off = (mn.y + mx.y) / 2.0 - 1.5
        made["objects"].append(_thin_box(
            f"{ANNOT_PREFIX}axis_X", (cx_off, cy_off, 0.005), (cx_off + 1, cy_off, 0.005),
            g, mats["axis_x"]))
        made["objects"].append(_thin_box(
            f"{ANNOT_PREFIX}axis_Y", (cx_off, cy_off, 0.005), (cx_off, cy_off + 1, 0.005),
            g, mats["axis_y"]))
        made["objects"].append(_thin_box(
            f"{ANNOT_PREFIX}axis_Z", (cx_off, cy_off, 0.005), (cx_off, cy_off, 1.005),
            g, mats["axis_z"]))

    # --- red flag boxes (12 thin edges per flagged object's world bbox)
    for name in (flagged_ids or []):
        obj = bpy.context.scene.objects.get(name)
        if obj is None or obj.type != 'MESH':
            continue
        corners = [obj.matrix_world @ type(obj.location)(c) for c in obj.bound_box]
        xs = [c.x for c in corners]; ys = [c.y for c in corners]; zs = [c.z for c in corners]
        bmin = Vector((min(xs), min(ys), min(zs)))
        bmax = Vector((max(xs), max(ys), max(zs)))
        pad = 0.01
        bmin -= Vector((pad, pad, pad)); bmax += Vector((pad, pad, pad))
        c = [Vector((x, y, z)) for x in (bmin.x, bmax.x)
             for y in (bmin.y, bmax.y) for z in (bmin.z, bmax.z)]
        # corner index bits: (x:4, y:2, z:1)
        edges = [(0, 1), (2, 3), (4, 5), (6, 7),      # along Z
                 (0, 2), (1, 3), (4, 6), (5, 7),      # along Y
                 (0, 4), (1, 5), (2, 6), (3, 7)]      # along X
        for e_i, (a, b) in enumerate(edges):
            made["objects"].append(_thin_box(
                f"{ANNOT_PREFIX}flag_{name}_{e_i}", c[a], c[b], 0.012,
                mats["flag"]))

    # --- labels: FONT billboards at top of each labeled object's bbox
    for name, idx in (label_ids or []):
        obj = bpy.context.scene.objects.get(name)
        if obj is None or obj.type != 'MESH':
            continue
        top = max((obj.matrix_world @ type(obj.location)(cc)).z for cc in obj.bound_box)
        diag = obj.dimensions.length
        size = min(max(diag * 0.18, 0.06), 0.4)  # capped: giant billboards block views
        curve = bpy.data.curves.new(name=f"{ANNOT_PREFIX}lbl_{idx}", type='FONT')
        curve.body = str(idx)
        curve.size = size
        curve.align_x = 'CENTER'
        curve.align_y = 'CENTER'
        txt = bpy.data.objects.new(f"{ANNOT_PREFIX}lbl_{idx}_{name}", curve)
        txt["kit_target"] = name  # refresh_labels() reads this (robust to
        # underscores in object names — the name-suffix parse is NOT)
        bpy.context.collection.objects.link(txt)
        center_xy = (obj.matrix_world @ type(obj.location)(Vector(obj.bound_box[0])))
        cx = sum((obj.matrix_world @ type(obj.location)(cc)).x for cc in obj.bound_box) / 8.0
        cy = sum((obj.matrix_world @ type(obj.location)(cc)).y for cc in obj.bound_box) / 8.0
        txt.location = (cx, cy, top + size * 0.9)
        txt.data.materials.append(mats["label"])
        made["labels"].append(txt)
        made["objects"].append(txt)

    return made


def aim_labels_at(labels, cam_loc, flat=False):
    """Rotate FONT billboards to face a camera location (per-angle aim).

    Text objects face +Z by default; track +Z toward the camera with +Y up.
    `flat=True` (or a nearly-overhead camera) lays the label flat so it
    reads like a map label instead of an edge-on stroke (measured).
    """
    cam = Vector(cam_loc)
    for txt in labels:
        d = (cam - txt.location)
        if d.length < 1e-6:
            continue
        d.normalize()
        if flat or d.z > 0.95:
            txt.rotation_euler = (0.0, 0.0, 0.0)
        else:
            txt.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()


def refresh_labels(layer):
    """Re-evaluate label POSITIONS from their target objects at the CURRENT
    frame state (M5 label-stick fix, measured: a look built at f1 then
    rendered at f16 left labels at f1 positions — the billboard for a
    moved object aimed from a stale offset rendered edge-on).

    Call (+ view_layer.update()) before EVERY aim_labels_at / render: cheap
    (<=8 labels), and makes labels frame-safe for animated scenes.
    """
    scene = bpy.context.scene
    for txt in layer.get("labels", []):
        try:
            target_name = txt["kit_target"]
        except KeyError:
            continue
        obj = scene.objects.get(target_name)
        if obj is None or obj.type != 'MESH':
            continue
        mw = obj.matrix_world
        corners = [mw @ type(obj.location)(cc) for cc in obj.bound_box]
        top = max(c.z for c in corners)
        cx = sum(c.x for c in corners) / 8.0
        cy = sum(c.y for c in corners) / 8.0
        size = txt.data.size
        txt.location = (cx, cy, top + size * 0.9)


def delete_annotation_layer(layer: dict) -> int:
    """Delete every annotation object + material. Returns count removed."""
    n = 0
    for obj in layer.get("objects", []):
        try:
            _ = obj.name
        except ReferenceError:
            continue
        try:
            bpy.data.objects.remove(obj, do_unlink=True)
            n += 1
        except Exception:
            pass
    for mat_name in list(bpy.data.materials.keys()):
        if mat_name.startswith(f"{ANNOT_PREFIX}mat_"):
            try:
                bpy.data.materials.remove(bpy.data.materials[mat_name])
            except Exception:
                pass
    # FONT curve data outlives its object unless purged by name
    # (caught by test_v1_look #1: KIT_ANNOT_lbl_1 residue)
    for curve_name in list(bpy.data.curves.keys()):
        if curve_name.startswith(ANNOT_PREFIX):
            try:
                bpy.data.curves.remove(bpy.data.curves[curve_name])
            except Exception:
                pass
    return n
