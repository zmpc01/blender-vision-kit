"""
apply_patch.py — apply a JSON patch to a scene without full rebuild.

This is the fast-iteration primitive. Instead of editing the scene script
and re-running build_scene + animate + render (which can take 10-30s),
the agent emits a small JSON patch describing the mutation, this script
loads the existing .blend file, applies the patch, and re-renders a
viewport screenshot.

Patch format (JSON):
    {
      "load_blend": "path/to/scene.blend",       # optional: load existing .blend
      "scene": "scene_template",                  # OR: rebuild from scene module
      "frames": 24,                                # if rebuilding
      "mutations": [
        {"op": "add_cube", "id": "Prop", "size": [0.4, 0.3, 0.2],
         "location": [1.0, 2.0, 0.1], "color": [0.8, 0.2, 0.2]},
        {"op": "set_location", "id": "Cube", "location": [1.0, 2.0, 0.5]},
        {"op": "set_rotation", "id": "Cube", "rotation_deg": [45, 0, 0]},
        {"op": "set_scale", "id": "Cube", "scale": [2.0, 2.0, 2.0]},
        {"op": "set_material_color", "id": "Cube", "color": [0.9, 0.2, 0.2]},
        {"op": "set_material_roughness", "id": "Cube", "roughness": 0.8},
        {"op": "delete_object", "id": "Sphere"},
        {"op": "duplicate_object", "id": "Cube", "new_id": "Cube.001",
         "location": [3, 0, 0.5]},
        {"op": "set_camera_location", "id": "MainCam", "location": [5, -5, 3]},
        {"op": "set_camera_lens", "id": "MainCam", "lens_mm": 35},
        {"op": "set_camera_dof", "id": "MainCam", "focus_distance": 2.5,
         "aperture_fstop": 2.8},
        {"op": "set_frame", "frame": 12},
        {"op": "render_viewport", "output": "check.png",
         "angle": "persp", "engine": "workbench"}
      ]
    }

add_* ops (add_cube / add_sphere / add_cylinder / add_cone / add_torus /
add_plane / add_empty):
    * "id" is REQUIRED and names the NEW object; the op REFUSES if the
      name already exists (Blender's silent .001 rename is a lie for
      patches). "location" is the primitive CENTER (origin == centroid),
      NOT the bottom — seat it afterwards with place_on / move_to /
      physics_place. "rotation_deg" and "color" (RGB(A)) are optional.
    * size params are FINAL world dimensions, data-baked at the mesh
      level (object scale stays 1,1,1 — never transform_apply, gotcha
      #58): add_cube takes "size" (scalar or [x,y,z]); add_plane "size"
      (scalar or [x,y] — planes are flat, a z component is refused;
      F2B-27 docstring sync); add_sphere "radius"; add_cylinder
      "radius"+"depth"; add_cone "radius1"(+"radius2" for truncated)
      +"depth"; add_torus "major_radius"+"minor_radius"; add_empty
      "empty_type"+"size".
    * every add SELF-VERIFIES its realized dims against the request and
      fails loudly on mismatch (a lying primitive poisons every
      downstream op). add_empty creates a seat_at anchor (no mesh).

Usage:
    blrun.sh --background --python scripts/apply_patch.py -- \\
        --patch patch.json

    # Or pass patch as inline JSON
    blrun.sh --background --python scripts/apply_patch.py -- \\
        --patch-json '{"mutations":[{"op":"set_location","id":"Cube","location":[1,2,0.5]}]}'

    # List all supported mutation ops:
    blrun.sh --background --python scripts/apply_patch.py -- --list

    # CLI shortcut: set camera DoF without writing mutations — the patch
    # MUST still carry load_blend or scene (the F2B-22 guard below refuses
    # the shortcut against a bare patch: "the current scene" there means
    # the factory startup scene, whose default camera is NOT a usable
    # target):
    blrun.sh --background --python scripts/apply_patch.py -- \
        --patch-json '{"load_blend": "smoke/smoke.blend"}' \
        --camera Camera --focus-distance 2.5 --aperture-fstop 2.8 \
        --save-blend out.blend

set_camera_dof notes:
    * "focus_distance" (m) sets cam.data.dof.focus_distance -- Blender's
      focus distance is the axial distance from the camera to the plane of
      sharp focus, the same semantics as webgpu-previz's canonical
      focus_distance_m.
    * "aperture_fstop" sets cam.data.dof.aperture_fstop -- Blender derives
      the aperture radius as lens/(2*fstop), the same formula as the
      canonical PhysicalCamera (aperture_radius_mm = focal/(2*f_stop)).
    * The op enables DoF (use_dof=True) and clears focus_object so the
      distance is authoritative. Both params are individually optional;
      at least one is required.
"""
import argparse
import json
import math
import os
import sys
from typing import Any, List

import bpy
from mathutils import Matrix, Vector
from blender_kit import script_argv, clear_scene


def _finite_check(op, key, val):
    """F2B-5: JSON documents happily carry NaN/Infinity (python's json
    accepts them by default) and a silent NaN location poisons the scene,
    every downstream audit, and every render — with exit 0. Refuse at the
    param layer."""
    def _bad(v):
        if isinstance(v, bool):
            return False
        if isinstance(v, float):
            return not math.isfinite(v)
        return False
    bad = _bad(val) if not isinstance(val, (list, tuple)) else any(
        _bad(x) for x in val)
    if bad:
        raise RuntimeError(
            f"op '{op}' key '{key}' contains NaN/Infinity — a non-finite "
            f"transform silently corrupts the scene (audits and renders "
            f"keep 'passing' on garbage). Fix the patch value.")


def _require(mut, key, op, *, expected_type=None, expected_len=None):
    """Extract a required key from a mutation dict, with a clean error message.

    Usage: loc = _require(mut, "location", "set_location", expected_type=list, expected_len=3)
    """
    if key not in mut:
        # wave-3: print the op's signature, not just the key name
        raise RuntimeError(f"op '{op}' missing required key '{key}' — "
                           f"signature: {PARAM_DOCS.get(op, '(see --list)')}")
    val = mut[key]
    if expected_type and not isinstance(val, expected_type):
        raise RuntimeError(f"op '{op}' key '{key}' must be {expected_type.__name__}, got {type(val).__name__}")
    if expected_len and isinstance(val, (list, tuple)) and len(val) != expected_len:
        raise RuntimeError(f"op '{op}' key '{key}' must have {expected_len} elements, got {len(val)}")
    _finite_check(op, key, val)
    return val


def _get_obj(obj_id: str, op: str = "?") -> bpy.types.Object:
    obj = bpy.data.objects.get(obj_id)
    if obj is None:
        avail = sorted(o.name for o in bpy.data.objects)
        hint = ""
        if avail:
            shown = ", ".join(avail[:15])
            hint = f"; scene objects: {shown}" + (" …" if len(avail) > 15 else "")
        raise RuntimeError(
            f"op '{op}': object '{obj_id}' not found in scene{hint}")
    return obj


def _apply_set_location(obj, params):
    rep = {}  # noqa (anchor for _get_obj placement)
    _PL._origin_centroid_warn(obj, rep)
    if "origin_offset_warning" in rep:
        print("[apply_patch] set_location WARNING:", rep["origin_offset_warning"])
    loc = _require(params, "location", "set_location", expected_type=list, expected_len=3)
    obj.location = tuple(loc)


def _apply_set_rotation(obj, params):
    rep = {}
    _PL._origin_centroid_warn(obj, rep)
    if "origin_offset_warning" in rep:
        print("[apply_patch] set_rotation WARNING:", rep["origin_offset_warning"])
    rot_deg = _require(params, "rotation_deg", "set_rotation", expected_type=list, expected_len=3)
    obj.rotation_euler = tuple(math.radians(v) for v in rot_deg)


def _apply_set_scale(obj, params):
    scale = _require(params, "scale", "set_scale", expected_type=list, expected_len=3)
    obj.scale = tuple(scale)


def _apply_set_material_color(obj, params):
    if obj.type != 'MESH' or not obj.data.materials:
        raise RuntimeError(f"Object {obj.name} has no materials to modify")
    mat = obj.data.materials[0]
    from blender_kit import ensure_use_nodes
    ensure_use_nodes(mat)
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is None:
        raise RuntimeError(f"No Principled BSDF in {mat.name}")
    color = params.get("color")
    if not isinstance(color, list):
        # name the shape — the generic _require message ("must be list")
        # made a consumer grep for the [r,g,b] contract in vain (s18 5i)
        raise RuntimeError(
            f"op 'set_material_color' key 'color' must be [r,g,b] or "
            f"[r,g,b,a] numbers (got {color!r})")
    color = _require(params, "color", "set_material_color",
                     expected_type=list)
    # s18 B11: 'color' had NO shape/type/range validation — a bare string
    # ("red") per-char-iterated into the BSDF channels, and out-of-range
    # components shipped silently (Base Color kept the raw value; Blender
    # clamps only the viewport diffuse_color). Siblings roughness/metallic
    # clamp to [0,1]; the in-repo glow law (tdawn_actors F-TD11) keeps
    # Base Color in range and carries HDR via Emission Strength — so a
    # clamp loses nothing legitimate. Non-finite is refused by
    # _require/_finite_check above (NaN would survive a clamp).
    if len(color) not in (3, 4) or any(
            isinstance(c, bool) or not isinstance(c, (int, float))
            for c in color):
        raise RuntimeError(
            f"op 'set_material_color' key 'color' must be [r,g,b] or "
            f"[r,g,b,a] numbers (got {color!r})")
    rgba = [max(0.0, min(1.0, float(c))) for c in color]
    if rgba != [float(c) for c in color]:
        print(f"[apply_patch] set_material_color: '{obj.name}' components "
              f"outside [0,1] clamped to {[round(c, 3) for c in rgba]} "
              f"(Base Color is not an HDR channel — glow goes through "
              f"Emission Strength)")
    if len(rgba) == 3:
        rgba = (*rgba, 1.0)
    bsdf.inputs["Base Color"].default_value = rgba
    # Also set diffuse_color — Workbench engine reads THIS, not BSDF (gotcha #56)
    mat.diffuse_color = rgba


def _apply_set_material_roughness(obj, params):
    # F2B-13: mirror set_material_color's guards (the sibling used to
    # raise raw AttributeError on non-mesh / use_nodes=False objects)
    if obj.type != 'MESH' or not obj.data.materials:
        raise RuntimeError(f"Object {obj.name} has no materials to modify")
    mat = obj.data.materials[0]
    from blender_kit import ensure_use_nodes
    ensure_use_nodes(mat)
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is None:
        raise RuntimeError(f"No Principled BSDF in {mat.name}")
    rough = _require(params, "roughness", "set_material_roughness")
    bsdf.inputs["Roughness"].default_value = max(0.0, min(1.0, float(rough)))


def _apply_set_material_metallic(obj, params):
    if obj.type != 'MESH' or not obj.data.materials:
        raise RuntimeError(f"Object {obj.name} has no materials to modify")
    mat = obj.data.materials[0]
    from blender_kit import ensure_use_nodes
    ensure_use_nodes(mat)
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is None:
        raise RuntimeError(f"No Principled BSDF in {mat.name}")
    metal = _require(params, "metallic", "set_material_metallic")
    bsdf.inputs["Metallic"].default_value = max(0.0, min(1.0, float(metal)))


def _apply_delete_object(obj, params):
    bpy.data.objects.remove(obj, do_unlink=True)


def _apply_duplicate_object(obj, params):
    # s18 B2: kit docstring law (see header: add ops REFUSE if the name
    # exists) — duplicate_object used to rename SILENTLY to '.001' when
    # new_id was taken (a lying name poisons every later op targeting
    # new_id) and a missing/non-string new_id died as a raw KeyError.
    new_id = params.get("new_id")
    if not new_id or not isinstance(new_id, str):
        raise RuntimeError(
            "op 'duplicate_object' requires a non-empty string 'new_id' "
            f"(the duplicate's name), got {new_id!r}")
    if bpy.data.objects.get(new_id) is not None:
        raise RuntimeError(
            f"duplicate_object refuses: '{new_id}' already exists "
            f"(Blender would silently rename the copy to '{new_id}.001' "
            f"— pick another name, or delete/rename the existing object)")
    new_obj = obj.copy()
    if obj.data:
        new_obj.data = obj.data.copy()
    bpy.context.collection.objects.link(new_obj)
    new_obj.name = new_id
    if "location" in params:
        _finite_check("duplicate_object", "location", params["location"])
        new_obj.location = tuple(params["location"])
    if "rotation_deg" in params:
        _finite_check("duplicate_object", "rotation_deg", params["rotation_deg"])
        new_obj.rotation_euler = tuple(math.radians(v) for v in params["rotation_deg"])
    if "scale" in params:
        _finite_check("duplicate_object", "scale", params["scale"])
        new_obj.scale = tuple(params["scale"])


def _apply_set_camera_location(obj, params):
    if obj.type != 'CAMERA':
        raise RuntimeError(f"{obj.name} is not a camera")
    _finite_check("set_camera_location", "location", params["location"])
    obj.location = tuple(params["location"])


def _apply_set_camera_lens(obj, params):
    if obj.type != 'CAMERA':
        raise RuntimeError(f"{obj.name} is not a camera")
    obj.data.lens = _require(params, "lens_mm", "set_camera_lens")


def _apply_set_camera_dof(obj, params):
    """Set camera depth-of-field (focus distance in m + aperture f-stop).

    Blender's dof.focus_distance is the axial distance to the plane of
    sharp focus (same semantics as the canonical webgpu-previz
    focus_distance_m); dof.aperture_fstop gives an aperture radius of
    lens/(2*fstop), matching the canonical aperture_radius_mm formula.
    """
    if obj.type != 'CAMERA':
        raise RuntimeError(f"{obj.name} is not a camera")
    focus = params.get("focus_distance", params.get("focus_distance_m"))
    fstop = params.get("aperture_fstop")
    if focus is None and fstop is None:
        raise RuntimeError(
            "set_camera_dof requires 'focus_distance' (m) and/or "
            "'aperture_fstop'")
    dof = obj.data.dof
    dof.use_dof = True
    dof.focus_object = None  # distance-based focus, not object-based
    if focus is not None:
        _finite_check("set_camera_dof", "focus_distance", focus)
        dof.focus_distance = float(focus)
    if fstop is not None:
        _finite_check("set_camera_dof", "aperture_fstop", fstop)
        dof.aperture_fstop = float(fstop)
    print(f"[apply_patch] set_camera_dof: {obj.name} "
          f"focus_distance={dof.focus_distance:.6g} m, "
          f"aperture_fstop={dof.aperture_fstop:.6g} (aperture radius "
          f"= lens/(2*fstop) = {obj.data.lens / (2.0 * dof.aperture_fstop):.6g} mm)")


def _apply_set_frame(obj, params):
    # obj is None for this op
    bpy.context.scene.frame_set(_require(params, "frame", "set_frame"))


def _apply_render_viewport(obj, params):
    # obj is None for this op
    # Lazy import to avoid circular dep
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from viewport_capture import render_angle, _compute_scene_center, image_readiness
    out = params["output"]
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    angle = params.get("angle", "persp")
    engine = params.get("engine", "workbench")
    # wave-1 friction #10: accept the doc vocabulary (BLENDER_EEVEE_NEXT /
    # BLENDER_EEVEE / BLENDER_WORKBENCH / CYCLES) — normalize to the
    # engine tokens render_angle understands.
    _ENGINE_ALIASES = {"BLENDER_EEVEE_NEXT": "eevee", "BLENDER_EEVEE": "eevee",
                       "BLENDER_WORKBENCH": "workbench", "CYCLES": "cycles",
                       "EEVEE": "eevee", "EEVEE_NEXT": "eevee",
                       "WORKBENCH": "workbench"}
    engine = _ENGINE_ALIASES.get(str(engine).upper(), engine)
    samples = params.get("samples", 1)
    width = params.get("width", 640)
    height = params.get("height", 480)
    # F2B-26: negative/zero samples or dims reached the raw render operator
    # and died in a C-level report; validate here in kit style instead.
    for _key, _val in (("samples", samples), ("width", width),
                       ("height", height)):
        if (isinstance(_val, bool) or not isinstance(_val, (int, float))
                or not float(_val).is_integer() or int(_val) < 1):
            raise RuntimeError(
                f"op 'render_viewport' key '{_key}' must be a positive "
                f"integer (got {_val!r})")
    samples, width, height = int(samples), int(width), int(height)
    target_str = params.get("target")
    if target_str:
        # F2B-26: a string target used to garble via tuple(target_str) into
        # per-character 'atoms' — require a real 3-number vector.
        if (not isinstance(target_str, (list, tuple)) or len(target_str) != 3
                or any(isinstance(c, bool) or not isinstance(c, (int, float))
                       for c in target_str)):
            raise RuntimeError(
                f"op 'render_viewport' key 'target' must be [x,y,z] "
                f"numbers (got {target_str!r})")
        if not all(math.isfinite(float(c)) for c in target_str):
            raise RuntimeError(
                f"op 'render_viewport' key 'target' contains "
                f"NaN/Infinity — scenes do not")
        target = tuple(float(c) for c in target_str)
    else:
        target = _compute_scene_center()
    lens = params.get("lens", 50)
    # s18 B4: a NaN/garbage lens silently rendered a poisoned frame —
    # validate like the sibling target guard below (F2B-26 style).
    if (isinstance(lens, bool) or not isinstance(lens, (int, float))
            or not math.isfinite(float(lens)) or float(lens) <= 0):
        raise RuntimeError(
            f"op 'render_viewport' key 'lens' must be a positive, finite "
            f"number in mm (got {lens!r})")
    lens = float(lens)
    # F2B-1 (P0): PARAM_DOCS documented `custom_loc` while the handler read
    # only `custom_location` — the documented spelling was SILENTLY DROPPED
    # (allowed-keys warning can't catch it: custom_loc is not a typo of
    # anything), so angle='custom' demanded a nonexistent CLI flag instead.
    # Accept both spellings; the docs keep canonical custom_location.
    custom_loc = params.get("custom_location", params.get("custom_loc"))
    if custom_loc is not None:
        # s18 B4: match the target guard above — angle='custom' with a
        # NaN/malformed custom_location silently rendered garbage.
        if (not isinstance(custom_loc, (list, tuple))
                or len(custom_loc) != 3
                or any(isinstance(c, bool) or not isinstance(c, (int, float))
                       for c in custom_loc)):
            raise RuntimeError(
                f"op 'render_viewport' key 'custom_location' must be "
                f"[x,y,z] numbers (got {custom_loc!r})")
        if not all(math.isfinite(float(c)) for c in custom_loc):
            raise RuntimeError(
                f"op 'render_viewport' key 'custom_location' contains "
                f"NaN/Infinity — scenes do not")
        custom_loc = tuple(float(c) for c in custom_loc)
    render_angle(angle, out, engine=engine, samples=samples,
                 width=width, height=height, target=target, lens=lens,
                 custom_location=custom_loc)
    print(f"[apply_patch] rendered viewport -> {out}  ({os.path.getsize(out)} bytes)")
    # wave-1: every kit image carries readiness stats (D6 forced pairing)
    r = image_readiness(out)
    if "error" not in r:
        fl = (" flags=" + ",".join(r["flags"])) if r["flags"] else ""
        print(f"[apply_patch] readiness {os.path.basename(out)} "
              f"luma={r['luma_mean']} clipped={r['clipped_pct']}% "
              f"dark={r['dark_pct']}% subject={r['subject_pct']}%{fl}")



def _apply_set_light_energy(obj, params):
    if obj.type != 'LIGHT':
        raise RuntimeError(f"{obj.name} is not a light")
    obj.data.energy = _require(params, "energy", "set_light_energy")


def _apply_set_light_color(obj, params):
    if obj.type != 'LIGHT':
        raise RuntimeError(f"{obj.name} is not a light")
    obj.data.color = tuple(_require(params, "color", "set_light_color"))




def _apply_set_world_strength(obj, params):
    """Set the World background strength (sky/HDRI intensity). obj is None."""
    scene = bpy.context.scene
    if not scene.world or scene.world.node_tree is None:
        raise RuntimeError("Scene has no node-based world")
    bg = scene.world.node_tree.nodes.get("Background")
    if bg is None:
        raise RuntimeError("World has no Background node")
    bg.inputs["Strength"].default_value = _require(params, "strength", "set_world_strength")


def _apply_set_exposure(obj, params):
    """Set the scene's render exposure (in EV stops). obj is None."""
    bpy.context.scene.view_settings.exposure = _require(params, "exposure", "set_exposure")



# ---------------------------------------------------------------------------
# Placement ops (placement_lib integration — placement-lab port)
# ---------------------------------------------------------------------------
# placement_lib lives in THIS scripts/ dir (blrun.sh already puts scripts/ on
# PYTHONPATH); the explicit sys.path entry is a safety net for direct blender
# invocation. <kit>/tests/ holds the demo scene modules for "scene": builds;
# PLACEMENT_LAB may point at the lab repo as a fallback source.

import os as _os
import sys as _sys
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_KIT_TESTS = _os.path.join(_os.path.dirname(_HERE), "tests")
_LAB = _os.environ.get("PLACEMENT_LAB", "/home/z/placement-lab")
for _p in (_HERE, _KIT_TESTS, _LAB):
    if _os.path.isdir(_p) and _p not in _sys.path:
        _sys.path.insert(0, _p)

import placement_lib as _PL
import physics_place as _PP
import json as _json

_LAST_REPORTS = {}
_PHYSICS_FAILURES = []


def _apply_move_to(obj, params):
    # s18 B5: placement_lib.move_to falls through ANY unknown reference
    # token to bottom-center while the report echoes the requested token
    # back — a lying report on a silently different placement. seat_at and
    # snap_z validate their tokens (F2B-6/F2B-12); mirror that here at the
    # handler layer (Wave-C owns the placement_lib-side validation).
    reference = params.get("reference", "bottom-center")
    if reference not in ("bottom-center", "centroid", "origin"):
        raise RuntimeError(
            f"op 'move_to': unknown reference {reference!r} — valid "
            f"tokens: 'bottom-center' (bbox bottom-xy-center), 'centroid', "
            f"'origin'")
    rep = _PL.move_to(obj, _require(params, "target", "move_to",
                                     expected_type=list, expected_len=3),
                      reference=reference,
                      override=params.get("override"),
                      output=params.get("output"))
    _LAST_REPORTS["move_to"] = rep
    print("[apply_patch] move_to:", rep["obj"], "target",
          rep["target"], "ref", rep["reference"],
          "(applied delta", [round(v, 3) for v in rep["applied_translation_m"]], ")")


def _apply_place_on(obj, params):
    raw_supports = params["supports"]
    # F2B-15: a bare string iterated per-character; an empty list reached
    # placement_lib's max() as 'max() arg is an empty sequence'. Validate.
    if isinstance(raw_supports, str) or not isinstance(raw_supports, (list, tuple)):
        raise RuntimeError("op 'place_on' key 'supports' must be a list of "
                           "support object names (got "
                           f"{type(raw_supports).__name__} — a bare string "
                           "would iterate per-character)")
    if not raw_supports:
        raise RuntimeError("op 'place_on' key 'supports' must name at least "
                           "one support object (the TOPMOST surface under "
                           "the mover)")
    supports = [_get_obj(s, "place_on") for s in raw_supports]
    # s18 B4: json.loads accepts NaN/Infinity literals — a NaN clearance or
    # inset silently solved a garbage placement that every later audit kept
    # 'passing'; a bare-string grid_n would per-char-iterate in the grid
    # sampler (the F2B-26 class). Validate at the param layer.
    clearance = params.get("clearance", 0.0)
    inset = params.get("inset", 0.0)
    for _key, _val in (("clearance", clearance), ("inset", inset)):
        if isinstance(_val, bool) or not isinstance(_val, (int, float)):
            raise RuntimeError(
                f"op 'place_on' key '{_key}' must be a number in meters "
                f"(got {_val!r})")
        if not math.isfinite(float(_val)):
            raise RuntimeError(
                f"op 'place_on' key '{_key}' contains NaN/Infinity — a "
                f"non-finite placement poisons the scene (audits and "
                f"renders keep 'passing' on garbage)")
        if float(_val) < 0.0:
            raise RuntimeError(
                f"op 'place_on' key '{_key}' must be >= 0 (got {_val}) — "
                f"negative clearance embeds below the surface, negative "
                f"inset expands the footprint past its bbox")
    grid_n = params.get("grid_n", 12)
    if (isinstance(grid_n, bool) or not isinstance(grid_n, (int, float))
            or not float(grid_n).is_integer() or int(grid_n) < 1):
        raise RuntimeError(
            f"op 'place_on' key 'grid_n' must be a positive integer "
            f"(got {grid_n!r})")
    grid_n = int(grid_n)
    rep = _PL.place_on(
        obj, *supports,
        clearance=clearance,
        footprint=params.get("footprint", "bottom"),
        mode=params.get("mode", "rest"),
        grid_n=grid_n,
        inset=inset,
        keep_xy=params.get("keep_xy", True),
        override=params.get("override"),
        contact_band_mm=params.get("contact_band_mm", 0.1),
        align_to_surface=params.get("align_to_surface", False),
        output=params.get("output"))
    _LAST_REPORTS["place_on"] = rep
    print("[apply_patch] place_on:", rep["obj"], "->",
          "OK" if rep.get("ok") else "CONTACT-ISSUES",
          "|", "; ".join(str(p.get("verdict")) for p in rep.get("post_contact", [])))
    if rep.get("slope_warning"):
        print("[apply_patch] place_on WARNING:", rep["slope_warning"])


def _apply_seat_at(obj, params):
    seat = _get_obj(params["seat"], "seat_at")
    # F2B-25: a typo'd seat_mesh used to resolve to None via
    # bpy.data.objects.get — the requested post-audit silently never ran
    # and the print defaulted to OK. Resolve loudly instead.
    seat_mesh_name = params.get("seat_mesh")
    if seat_mesh_name:
        if not isinstance(seat_mesh_name, str):
            raise RuntimeError("op 'seat_at' key 'seat_mesh' must be an "
                               f"object name (string), got "
                               f"{type(seat_mesh_name).__name__}")
        seat_mesh = _get_obj(seat_mesh_name, "seat_at")
    else:
        seat_mesh = None
    offset = params.get("offset")
    if offset is not None:
        # s18 B4: json.loads accepts NaN/Infinity — a NaN offset silently
        # seated the figure in a poisoned pose (and a bare string would
        # per-char-iterate inside Vector()). Validate shape + finiteness.
        if (not isinstance(offset, (list, tuple)) or len(offset) != 3
                or any(isinstance(c, bool) or not isinstance(c, (int, float))
                       for c in offset)):
            raise RuntimeError(
                f"op 'seat_at' key 'offset' must be [dx,dy,dz] numbers in "
                f"the empty's local space (got {offset!r})")
        _finite_check("seat_at", "offset", offset)
    rep = _PL.seat_at(
        obj, seat,
        reference=params.get("reference", "bottom"),
        offset=offset,
        align=params.get("align", True),
        override=params.get("override"),
        seat_mesh=seat_mesh,
        contact_band_mm=params.get("contact_band_mm", 0.1),
        output=params.get("output"))
    _LAST_REPORTS["seat_at"] = rep
    if "ok" in rep:
        verdict = "OK" if rep["ok"] else "CONTACT-ISSUES"
    else:
        # F2B-25: no seat_mesh -> no post-contact audit ran; the old
        # default-True print said OK for an unverified state.
        verdict = "OK(unverified — pass seat_mesh to post-audit contact)"
    print("[apply_patch] seat_at:", rep["obj"], "->", verdict)


def _apply_snap_z(obj, params):
    rep = _PL.snap_z(obj, _require(params, "target_z", "snap_z"),
                     reference=params.get("reference", "bottom"),
                     override=params.get("override"),
                     output=params.get("output"))
    _LAST_REPORTS["snap_z"] = rep
    print("[apply_patch] snap_z:", rep["obj"], "-> z =", rep["result_z"])


def _apply_audit(obj, params):
    # F2B-15: raw bpy.data.objects[p[0]] indexing inside audit_scene turned
    # a typo'd pair name into a KeyError that the friendly converter
    # mislabeled "missing/invalid param 'Nope'"; a 3-name 'A,B,C' entry
    # silently dropped the third name. Validate + resolve here.
    pairs = None
    raw_pairs = params.get("pairs")
    if raw_pairs is not None:
        if isinstance(raw_pairs, str) or not isinstance(raw_pairs, (list, tuple)) \
                or not raw_pairs:
            raise RuntimeError("op 'audit' key 'pairs' must be a non-empty "
                               "list of 'A,B' name strings")
        pairs = []
        for p in raw_pairs:
            if not isinstance(p, str):
                raise RuntimeError(
                    f"op 'audit' pairs entries must be 'A,B' name strings, "
                    f"got {p!r}")
            names = [s.strip() for s in p.split(",")]
            if len(names) != 2 or not all(names):
                raise RuntimeError(
                    f"op 'audit' pair {p!r} must be exactly 'A,B' (object "
                    f"names containing commas are not supported — rename "
                    f"the object)")
            _get_obj(names[0], "audit")
            _get_obj(names[1], "audit")
            pairs.append((names[0], names[1]))
    raw_exclude = params.get("exclude", ())
    if isinstance(raw_exclude, str):
        raise RuntimeError("op 'audit' key 'exclude' must be a list of "
                           "object names (a bare string would iterate "
                           "per-character)")
    exclude = tuple(raw_exclude)
    # s18 B4: a NaN contact band makes every '>' comparison False — the
    # fail_on_penetration gate false-PASSES a penetrating scene (and a
    # non-number band dies as a raw TypeError deep in the comparison).
    # Validate finite and >= 0 before the audit runs.
    band = params.get("contact_band_mm", 0.1)
    if (isinstance(band, bool) or not isinstance(band, (int, float))
            or not math.isfinite(float(band))):
        raise RuntimeError(
            f"op 'audit' key 'contact_band_mm' must be a finite number in "
            f"mm (got {band!r}) — NaN/Infinity makes every penetration "
            f"comparison False and false-PASSES the gate")
    if float(band) < 0.0:
        raise RuntimeError(
            f"op 'audit' key 'contact_band_mm' must be >= 0 (got {band})")
    band = float(band)
    # s18 B6: a typo'd scope id used to run the scene-wide audit, then
    # scope it down to 0 pairs — fail_on_penetration VACUOUSLY PASSED.
    # Refuse unknown ids before the (expensive) audit runs. The 'pairs'
    # names are already resolved loudly via _get_obj above (F2B-15).
    scope_id = params.get("id")
    if scope_id and bpy.data.objects.get(scope_id) is None:
        raise RuntimeError(
            f"op 'audit': scope id '{scope_id}' not found in scene")
    rep = _PL.audit_scene(pairs=pairs, exclude=exclude,
                          sample=params.get("sample", "verts"),
                          contact_band_mm=band,
                          clearance_pad_mm=params.get("clearance_pad_mm", 100.0),
                          force=params.get("force", False))
    if scope_id:
        # wave-1 friction #5: the id param was accepted but silently
        # non-scoping. Scope the VERDICT to pairs involving this object
        # (the pair search still runs scene-wide; the failure decision
        # and printed pairs now honor the scope).
        scoped = [p for p in rep["pairs"]
                  if p.get("a") == scope_id or p.get("b") == scope_id]
        rep = dict(rep)
        rep["pairs"] = scoped
        rep["pairs_checked"] = len(scoped)
        # session-16 fix: count the STATE enum, not the verdict string.
        # pair rows carry verdict = human string ("PENETRATING 8.0 mm — fix")
        # and state = enum — the unscoped path counts states (the rep key is
        # state_counts), and the doc's own law (AGENTS.md): exact-match the
        # pair's `state` field, never `verdict` — matching verdict here made
        # `failed` always False, so fail_on_penetration could never abort a
        # scoped audit.
        counts = {}
        for p in scoped:
            counts[p["state"]] = counts.get(p["state"], 0) + 1
        rep["state_counts"] = counts
        # match the unscoped path's rule (placement_lib.audit_scene): a
        # penetration counts only beyond the contact band — sub-band
        # micro-penetrations are advisory there and must stay advisory
        # here (review 5-a P2-7). `band` is the s18-B4-validated local.
        rep["failed"] = any(
            p["state"] == "PENETRATING" and
            (p.get("penetration_mm") is None or
             p["penetration_mm"] > band)
            for p in scoped)
    _LAST_REPORTS["audit"] = rep
    if params.get("output"):
        out = params["output"]
        _os.makedirs(_os.path.dirname(_os.path.abspath(out)), exist_ok=True)
        with open(out, "w") as f:
            _json.dump(rep, f, indent=2)
    print("[apply_patch] audit: pairs=%d counts=%s failed=%s" % (
        rep["pairs_checked"], rep["state_counts"], rep["failed"]))
    for pr in rep["pairs"][:6]:
        print("[apply_patch]   ", pr["a"], "x", pr["b"], "-", pr["verdict"])
    if rep["pairs_checked"] > 6:
        print(f"[apply_patch]   ... {rep['pairs_checked'] - 6} more pairs "
              f"(use the \"output\" param for the full JSON)")
    if params.get("fail_on_penetration", True) and rep["failed"]:
        raise RuntimeError("audit: penetration detected — patch chain aborted")


def _resolve_objlist(names, op="?"):
    import bpy as _bpy
    return [_get_obj(n, op) for n in names] if names else None


def _physics_warn(rep):
    """Round-A usability: stdout said 'applied: op' + exit 0 even when the
    op's verdict was a failure — a stdout-driven pipeline accepted broken
    scenes. Failures now print a loud, grep-able line."""
    if isinstance(rep, dict) and rep.get("ok") is False:
        _PHYSICS_FAILURES.append(rep.get("verdict"))
        reason = rep.get("verdict_reason") or ""
        if not reason and rep.get("objects"):
            reason = "; ".join(
                f"{o.get('obj')}={o.get('verdict')}"
                for o in rep["objects"][:3])
        print(f"[apply_patch] !! PHYSICS-OP-FAILED verdict="
              f"{rep.get('verdict')} reason={reason or '(see report)'}"
              f" — inspect the report before continuing")


def _apply_physics_settle(obj, params):
    # F2B-23: [] and null used to be synonyms (both -> objs=None = settle
    # EVERY eligible mesh, the "almost never wanted" free-fall mode).
    # Refuse [] loudly; null/omitted keeps whole-scene semantics.
    raw_objs = params.get("objs")
    if raw_objs is not None and not isinstance(raw_objs, (list, tuple)):
        raise RuntimeError("op 'physics_settle' key 'objs' must be a list "
                           "of mover names (a bare string would iterate "
                           "per-character)")
    if isinstance(raw_objs, (list, tuple)) and not raw_objs:
        raise RuntimeError("op 'physics_settle': objs=[] is refused — name "
                           "at least one mover, or omit/null the key for "
                           "whole-scene settle")
    raw_env = params.get("environment")
    if raw_env is not None and not isinstance(raw_env, (list, tuple)):
        raise RuntimeError("op 'physics_settle' key 'environment' must be a "
                           "list of names (a bare string would iterate "
                           "per-character)")
    rep = _PP.settle(objs=_resolve_objlist(raw_objs, "physics_settle"),
                     environment=_resolve_objlist(raw_env) or [],
                     frames=params.get("frames", 45),
                     apply=params.get("apply", "end"),
                     tol_mm=params.get("tol_mm", 1.0),
                     repair_penetrations=params.get(
                         "repair_penetrations", "refuse"),
                     allow_bake=params.get("allow_bake", False),
                     allow_copy=params.get("allow_copy", False),
                     pad_mm=params.get("pad_mm", 150.0),
                     snap=params.get("snap", True),
                     snap_cap_mm=params.get("snap_cap_mm", 8.0),
                     output=params.get("output"))
    _LAST_REPORTS["physics_settle"] = rep
    print("[apply_patch] physics_settle:", rep.get("verdict"))
    if raw_objs is None and rep.get("whole_scene_warning"):
        # F2B-23: the whole-scene warning used to live only in the report
        # JSON — the stdout path a pipeline greps never saw it.
        print("[apply_patch] physics_settle WARNING:",
              rep["whole_scene_warning"])
    # wave-1 friction #6: the documented per-mover verdict tokens
    # (AT_REST/SETTLED/SLIPPED/TOPPLED/...) were JSON-only — print them
    for o in (rep.get("objects") or [])[:8]:
        print("[apply_patch]   settle:", o.get("obj"), "->", o.get("verdict"))
    _physics_warn(rep)


def _apply_physics_place(obj, params):
    import bpy as _bpy
    target = _get_obj(params["id"], "physics_place")
    rep = _PP.place(target,
                    drop_mm=params.get("drop_mm", 30.0),
                    frames=params.get("frames", 45),
                    snap=params.get("snap", True),
                    snap_cap_mm=params.get("snap_cap_mm", 8.0),
                    apply=params.get("apply", "end"),
                    tol_mm=params.get("tol_mm", 1.0),
                    allow_bake=params.get("allow_bake", False),
                    allow_copy=params.get("allow_copy", False),
                    pad_mm=params.get("pad_mm", 150.0),
                    output=params.get("output"))
    _LAST_REPORTS["physics_place"] = rep
    print("[apply_patch] physics_place:", rep.get("verdict"))
    _physics_warn(rep)


def _apply_physics_oracle(obj, params):
    import bpy as _bpy
    target = _get_obj(params["id"], "physics_oracle")
    # s18 B4: json.loads accepts NaN/Infinity — a NaN xyz target teleports
    # the mover into a poisoned pose the oracle then 'verifies' (and a
    # NaN target_z sinks it below the world). Validate at the param layer,
    # mirroring render_viewport's target guard.
    xyz = params.get("target")
    if xyz is not None:
        if (not isinstance(xyz, (list, tuple)) or len(xyz) != 3
                or any(isinstance(c, bool) or not isinstance(c, (int, float))
                       for c in xyz)):
            raise RuntimeError(
                f"op 'physics_oracle' key 'target' must be [x,y,z] "
                f"numbers (got {xyz!r})")
        if not all(math.isfinite(float(c)) for c in xyz):
            raise RuntimeError(
                f"op 'physics_oracle' key 'target' contains NaN/Infinity "
                f"— scenes do not")
    target_z = params.get("target_z")
    if target_z is not None:
        if isinstance(target_z, bool) or not isinstance(target_z, (int, float)) \
                or not math.isfinite(float(target_z)):
            raise RuntimeError(
                f"op 'physics_oracle' key 'target_z' must be a finite "
                f"number in meters (got {target_z!r})")
    rep = _PP.oracle(target,
                     target_z=target_z,
                     target=xyz,
                     frames=params.get("frames", 45),
                     pad_mm=params.get("pad_mm", 150.0),
                     tol_mm=params.get("tol_mm", 1.0),
                     intended_support=params.get("intended_support"),
                     allow_bake=params.get("allow_bake", False),
                     allow_copy=params.get("allow_copy", False),
                     output=params.get("output"))
    _LAST_REPORTS["physics_oracle"] = rep
    print("[apply_patch] physics_oracle:", rep.get("verdict"))
    _physics_warn(rep)


def _apply_physics_gate(obj, params):
    rep = _PP.gate(tol_mm=params.get("tol_mm", 1.0),
                   frames=params.get("frames", 45),
                   apply="none",
                   fail_hard=params.get("fail_hard", False),
                   pad_mm=params.get("pad_mm", 100.0),
                   audit_pad_mm=params.get("audit_pad_mm", 100.0),
                   verify_movers=_resolve_objlist(
                       params.get("verify_movers")),
                   output=params.get("output"))
    _LAST_REPORTS["physics_gate"] = rep
    print("[apply_patch] physics_gate:", rep.get("verdict"),
          "fix_queue:", len(rep.get("fix_queue", [])))
    for _q in rep.get("fix_queue", [])[:8]:
        print("[apply_patch]   queue:", _q.get("op", "(manual)"),
              _q.get("objs", ""), "-", _q.get("note", ""))
    # F2B-19: a fail_hard=false gate REJECTS with ok=False — that failure
    # never reached _PHYSICS_FAILURES, so --fail-on-physics-failure exited
    # 0 on a rejected scene (fail-open exit-code gate).
    _physics_warn(rep)


def _apply_seam_views(obj, params):
    a = _get_obj(params["a"], "seam_views")
    b = _get_obj(params["b"], "seam_views")
    # s18 B11: a bare-string res ('640x360') became per-character atoms
    # downstream and a wrong-length/wrong-type res died in render internals
    # (the F2B-26 class). Require [width, height] positive integers.
    raw_res = params.get("res", (640, 360))
    if (isinstance(raw_res, str) or not isinstance(raw_res, (list, tuple))
            or len(raw_res) != 2
            or any(isinstance(c, bool) or not isinstance(c, (int, float))
                   or not float(c).is_integer() or int(c) < 1
                   for c in raw_res)):
        raise RuntimeError(
            "op 'seam_views' key 'res' must be [width, height] positive "
            f"integers (got {raw_res!r} — a bare string would become "
            f"per-character atoms)")
    rep = _PL.seam_views(a, b, out_dir=params["out_dir"],
                         res=(int(raw_res[0]), int(raw_res[1])),
                         engine=params.get("engine", "workbench"),
                         contact_band_mm=params.get("contact_band_mm", 0.1),
                         fill_frac=params.get("fill_frac", 0.6))
    _LAST_REPORTS["seam_views"] = rep
    print("[apply_patch] seam_views:", json.dumps(rep["views"]))


def _apply_heat_bake(obj, params):
    # s18 B11: a bare string iterated per-character — each char became a
    # _get_obj lookup ('C', 'u', 'b'...). Require a real list of names.
    raw_others = params["others"]
    if isinstance(raw_others, str) or not isinstance(raw_others, (list, tuple)):
        raise RuntimeError(
            "op 'heat_bake' key 'others' must be a list of object names "
            f"(got {type(raw_others).__name__} — a bare string would "
            f"iterate per-character)")
    if any(not isinstance(n, str) for n in raw_others):
        raise RuntimeError(
            "op 'heat_bake' key 'others' entries must be object names "
            f"(strings), got {raw_others!r}")
    others = [_get_obj(n, "heat_bake") for n in raw_others]
    rep = _PL.heat_bake(obj, others,
                        yellow_mm=params.get("yellow_mm", 10.0),
                        green_mm=params.get("green_mm", 50.0))
    _LAST_REPORTS["heat_bake"] = rep
    print("[apply_patch] heat_bake:", obj.name, rep["bands"])


def _apply_clear_bvh_cache(obj, params):
    _PL.clear_bvh_cache()
    print("[apply_patch] bvh cache cleared")


# ---------------------------------------------------------------------------
# Add-primitive ops (Track I — the patch protocol can now CREATE geometry)
# ---------------------------------------------------------------------------
# Design-gated (fresh-context audit + live 4.5.13 probes, worklog Task 2).
# Semantics locked to the fixture-builder discipline
# (scripts/scene_physics_usability.py):
#   * size params are FINAL world dims, data-baked via
#     obj.data.transform(Matrix.Diagonal(...)) — object scale stays (1,1,1),
#     NEVER transform_apply (gotcha #58: it also zeroes location in 4.5.13)
#   * location is the primitive CENTER (= origin == centroid), not the
#     bottom — seat with place_on/move_to/physics_place afterwards
#   * self-verification runs BEFORE rotation (oriented AABB would lie),
#     with chord-aware tolerance for polygonal radial kinds
#   * materials are get-or-create keyed on the id (no .001 leak on patch
#     re-runs), use_nodes=True + Principled Base Color AND viewport
#     diffuse_color (gotcha #56: workbench reads diffuse_color only)
#   * every numeric param is isfinite-validated (json.loads accepts
#     NaN/Infinity; NaN silently passes naive tolerance checks)

_ADD_EMPTY_TYPES = ("PLAIN_AXES", "ARROWS", "SINGLE_ARROW", "CIRCLE",
                    "CUBE", "SPHERE", "CONE")  # no IMAGE: useless unbound
_ADD_KEYS_BASE = {"op", "id", "location", "rotation_deg", "color"}


def _add_num(params, key, *, positive=False, nonneg=False):
    v = params.get(key)
    if v is None:
        return None
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise RuntimeError(f"[apply_patch] add op param '{key}' must be a "
                           f"number (got {type(v).__name__}: {v!r})")
    v = float(v)
    if not math.isfinite(v):
        raise RuntimeError(f"[apply_patch] add op param '{key}' must be "
                           f"finite (got {v}) — json accepts NaN/Infinity, "
                           f"scenes do not")
    if positive and v <= 0.0:
        raise RuntimeError(f"[apply_patch] add op param '{key}' must be "
                           f"> 0 (got {v})")
    if nonneg and v < 0.0:
        raise RuntimeError(f"[apply_patch] add op param '{key}' must be "
                           f">= 0 (got {v})")
    return v


def _add_vec(params, key, n, default=None, nonneg=False, positive=False):
    v = params.get(key, default)
    if v is None:
        return None
    if (not isinstance(v, (list, tuple)) or len(v) != n
            or any(isinstance(c, bool) or not isinstance(c, (int, float))
                   for c in v)):
        raise RuntimeError(f"[apply_patch] add op param '{key}' must be "
                           f"{n} numbers (got {v!r})")
    out = []
    for c in v:
        c = float(c)
        if not math.isfinite(c):
            raise RuntimeError(f"[apply_patch] add op param '{key}' must be "
                               f"finite (got {c})")
        if positive and c <= 0.0:
            raise RuntimeError(f"[apply_patch] add op param '{key}' must "
                               f"be > 0 (got {c}) — degenerate dims poison "
                               f"every downstream op")
        if nonneg and c < 0.0:
            raise RuntimeError(f"[apply_patch] add op param '{key}' must "
                               f"be >= 0 (got {c})")
        out.append(c)
    return out


def _add_scalar_or_vec(params, key, n, default, positive=True):
    """size semantics: scalar s -> [s]*n, or an n-vector of final dims.
    Sizes must be strictly positive — a zero axis is a degenerate
    primitive that poisons every downstream op."""
    v = params.get(key, default)
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return [_add_num({key: v}, key, positive=positive)] * n
    return _add_vec(params, key, n, default=default, positive=positive)


def _add_id(params, allowed_keys):
    extra = set(params) - set(allowed_keys)
    if extra:
        raise RuntimeError(
            f"[apply_patch] add op got unknown param(s) {sorted(extra)}; "
            f"valid params: {sorted(set(allowed_keys))}")
    obj_id = params.get("id")
    if not obj_id or not isinstance(obj_id, str):
        raise RuntimeError("[apply_patch] add op requires a string 'id' "
                           "(the new object's name)")
    if bpy.data.objects.get(obj_id) is not None:
        raise RuntimeError(
            f"[apply_patch] add op refuses: object '{obj_id}' already "
            f"exists (Blender would silently rename the new one to "
            f"'{obj_id}.001' — delete/rename it first, or use "
            f"duplicate_object)")
    return obj_id


def _add_chord_tol(extent, n, base=0.0005):
    """Polygonal radial kinds undershoot their nominal extent by up to
    extent*(1-cos(pi/n)) (worst-case vertex offset from the axis; the
    true worst bound is cos(pi/(2n)) — this is 2x looser, by design).
    +1mm cushion. Verified live: cyl v7 measured 2.5% short of nominal."""
    if not n or n < 3:
        return base
    return max(base, extent * (1.0 - math.cos(math.pi / n)) + 0.001)


def _add_selfverify(obj, expect, tols):
    """Fail-loud realized-vs-requested dims check (data verts x
    matrix_world — bound_box is stale-prone, gotcha file #41-era).
    Runs BEFORE rotation is applied (F15: an oriented AABB reads
    [1.414, 1.414, 1.0] for a rotated unit cube)."""
    bpy.context.view_layer.update()
    pts = [obj.matrix_world @ Vector(v.co) for v in obj.data.vertices]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts),
                 min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts),
                 max(p.z for p in pts)))
    got = mx - mn
    for ax in range(3):
        if abs(got[ax] - expect[ax]) > tols[ax]:
            raise RuntimeError(
                f"[apply_patch] add self-verify FAILED: "
                f"{'xyz'[ax]} built {got[ax]:.6f} m, requested "
                f"{expect[ax]:.6f} m (tol {tols[ax]:.6f}) — refusing to "
                f"ship a lying primitive")
    return got


def _add_material(obj, obj_id, params):
    color = params.get("color")
    if color is None:
        return
    rgba = _add_vec({"color": color}, "color", 4
                    if len(color) == 4 else 3)
    rgba = rgba + [1.0] * (4 - len(rgba))
    mat = bpy.data.materials.get(obj_id + "_mat") \
        or bpy.data.materials.new(obj_id + "_mat")
    mat.use_nodes = True  # 4.5.13 default False (design-gate F17)
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = rgba
    mat.diffuse_color = rgba  # workbench reads THIS (gotcha #56)
    if obj.data is not None and not obj.data.materials:
        obj.data.materials.append(mat)


def _add_finalize(obj, obj_id, params, expect=None, tols=None):
    """Shared tail: rename, data-name, material, self-verify, rotate."""
    obj.name = obj_id
    if obj.data is not None:
        obj.data.name = obj_id  # readable .blend data names (cosmetic)
    _add_material(obj, obj_id, params)
    got = None
    if expect is not None:
        got = _add_selfverify(obj, expect, tols)
    if params.get("rotation_deg") is not None:
        rot = _add_vec(params, "rotation_deg", 3)
        obj.rotation_euler = tuple(math.radians(v) for v in rot)
    loc = _add_vec(params, "location", 3, default=[0.0, 0.0, 0.0])
    if loc != [0.0, 0.0, 0.0]:
        obj.location = loc
    return got


def _apply_add_cube(obj, params):
    obj_id = _add_id(params, _ADD_KEYS_BASE | {"size"})
    dims = _add_scalar_or_vec(params, "size", 3, default=1.0)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
    o = bpy.context.active_object
    o.data.transform(Matrix.Diagonal((*dims, 1.0)))
    got = _add_finalize(o, obj_id, params, expect=dims,
                        tols=[0.0005] * 3)
    print(f"[apply_patch] add_cube: '{obj_id}' dims="
          f"{[round(v, 4) for v in got]} m "
          f"center={[round(v, 4) for v in o.location]}")


def _apply_add_sphere(obj, params):
    allowed = _ADD_KEYS_BASE | {"radius", "segments", "ring_count"}
    obj_id = _add_id(params, allowed)
    r = _add_num(params, "radius", positive=True) or 0.5
    seg = int(_add_num(params, "segments", positive=True) or 32)
    rings = int(_add_num(params, "ring_count", positive=True) or 16)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, segments=seg,
                                         ring_count=rings,
                                         location=(0, 0, 0))
    o = bpy.context.active_object
    t = _add_chord_tol(2 * r, seg)
    got = _add_finalize(o, obj_id, params, expect=[2 * r] * 3,
                        tols=[t, t, 0.0005])
    print(f"[apply_patch] add_sphere: '{obj_id}' dims="
          f"{[round(v, 4) for v in got]} m radius={r}")


def _apply_add_cylinder(obj, params):
    allowed = _ADD_KEYS_BASE | {"radius", "depth", "vertices"}
    obj_id = _add_id(params, allowed)
    r = _add_num(params, "radius", positive=True) or 0.5
    d = _add_num(params, "depth", positive=True) or 1.0
    verts = int(_add_num(params, "vertices", positive=True) or 32)
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=d, vertices=verts,
                                        location=(0, 0, 0))
    o = bpy.context.active_object
    t = _add_chord_tol(2 * r, verts)
    got = _add_finalize(o, obj_id, params, expect=[2 * r, 2 * r, d],
                        tols=[t, t, 0.0005])
    print(f"[apply_patch] add_cylinder: '{obj_id}' dims="
          f"{[round(v, 4) for v in got]} m radius={r} depth={d}")


def _apply_add_cone(obj, params):
    allowed = _ADD_KEYS_BASE | {"radius1", "radius2", "depth", "vertices"}
    obj_id = _add_id(params, allowed)
    r1 = _add_num(params, "radius1", positive=True) or 0.5
    r2 = _add_num(params, "radius2", nonneg=True)
    r2 = 0.0 if r2 is None else r2  # 0 = point (legal default)
    d = _add_num(params, "depth", positive=True) or 1.0
    verts = int(_add_num(params, "vertices", positive=True) or 32)
    bpy.ops.mesh.primitive_cone_add(radius1=r1, radius2=r2, depth=d,
                                    vertices=verts, location=(0, 0, 0))
    o = bpy.context.active_object
    rad = 2.0 * max(r1, r2)  # F14: truncated cone reads max(r1, r2)
    t = _add_chord_tol(rad, verts)
    got = _add_finalize(o, obj_id, params, expect=[rad, rad, d],
                        tols=[t, t, 0.0005])
    print(f"[apply_patch] add_cone: '{obj_id}' dims="
          f"{[round(v, 4) for v in got]} m r1={r1} r2={r2} depth={d}")


def _apply_add_torus(obj, params):
    allowed = _ADD_KEYS_BASE | {"major_radius", "minor_radius"}
    obj_id = _add_id(params, allowed)
    R = _add_num(params, "major_radius", positive=True) or 1.0
    r = _add_num(params, "minor_radius", positive=True) or 0.25
    if r >= R:
        raise RuntimeError(f"[apply_patch] add_torus refuses: "
                           f"minor_radius ({r}) must be < major_radius "
                           f"({R}) — otherwise the surface self-intersects")
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r,
                                     location=(0, 0, 0))
    o = bpy.context.active_object
    tx = _add_chord_tol(2 * (R + r), 48)   # major_segments default 48
    tz = _add_chord_tol(2 * r, 12)         # minor_segments default 12
    got = _add_finalize(o, obj_id, params,
                        expect=[2 * (R + r), 2 * (R + r), 2 * r],
                        tols=[tx, tx, tz])
    print(f"[apply_patch] add_torus: '{obj_id}' dims="
          f"{[round(v, 4) for v in got]} m major={R} minor={r}")


def _apply_add_plane(obj, params):
    obj_id = _add_id(params, _ADD_KEYS_BASE | {"size"})
    dims = _add_scalar_or_vec(params, "size", 2, default=1.0)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0))
    o = bpy.context.active_object
    o.data.transform(Matrix.Diagonal((dims[0], dims[1], 1.0, 1.0)))
    got = _add_finalize(o, obj_id, params,
                        expect=[dims[0], dims[1], 0.0],
                        tols=[0.0005] * 3)
    print(f"[apply_patch] add_plane: '{obj_id}' dims="
          f"{[round(v, 4) for v in got]} m center="
          f"{[round(v, 4) for v in o.location]}")


def _apply_add_empty(obj, params):
    allowed = _ADD_KEYS_BASE | {"empty_type", "size"}
    obj_id = _add_id(params, allowed)
    et = params.get("empty_type", "PLAIN_AXES")
    if et not in _ADD_EMPTY_TYPES:
        raise RuntimeError(
            f"[apply_patch] add_empty: empty_type {et!r} not supported "
            f"(valid: {list(_ADD_EMPTY_TYPES)}; IMAGE excluded — useless "
            f"without a bound image)")
    size = _add_num(params, "size", positive=True) or 0.5
    bpy.ops.object.empty_add(type=et, radius=size, location=(0, 0, 0))
    o = bpy.context.active_object
    # no mesh: the AABB self-verify does not apply (design-gate corr. #7);
    # verify type/display/size instead
    o.empty_display_size = size
    if o.type != 'EMPTY' or o.empty_display_type != et:
        raise RuntimeError(f"[apply_patch] add_empty self-verify FAILED "
                           f"for '{obj_id}' (type={o.type}, "
                           f"display={o.empty_display_type})")
    _add_finalize(o, obj_id, params, expect=None)
    print(f"[apply_patch] add_empty: '{obj_id}' display={et} "
          f"size={size} center={[round(v, 4) for v in o.location]} "
          f"(no mesh — use as seat_at anchor, not as a mover)")


def _apply_label_objects(_obj, params):
    """D16: turn a VISION agent's identification into durable scene
    state. Additive kit_label/kit_label_conf props on every id; optional
    two-phase rename (whole-batch collision simulation, charset law
    [A-Za-z0-9_-]+); kit_semantic marker when the label is
    gate-relevant; report JSON written BEFORE any rename."""
    import semantic_lib as _SL
    labels = _require(params, "labels", "label_objects", expected_type=dict)
    rep = _SL.label_objects(
        labels,
        rename=bool(params.get("rename", False)),
        on_collision=params.get("on_collision", "suffix"),
        report_path=params.get("output"))
    print(f"[apply_patch] label_objects: {len(rep['rows'])} ids | "
          f"renamed {len(rep['renamed'])} | kept {len(rep['kept'])} | "
          f"unchanged {len(rep['unchanged'])} | semantic-marked "
          f"{len(rep['semantic_marked'])}")
    for rn in rep["renamed"][:8]:
        print(f"[apply_patch]   rename: {rn['from']} -> {rn['to']}")
    if len(rep["renamed"]) > 8:
        print(f"[apply_patch]   ... {len(rep['renamed']) - 8} more "
              f"(full JSON: {params.get('output') or 'output/labels_report.json'})")


def _apply_split_mesh(obj, params):
    """D16: break a mesh into labelable parts. Loose-parts path:
    mode=dry-run (default) / split. WELDED continuous geometry (no
    loose parts — typical level/interior imports): vision-driven REGION
    cut, mode=dry-run-region / split-region with a world-space
    {min,max} box the principal reads off the render."""
    import semantic_lib as _SL
    mode = params.get("mode", "dry-run")
    region = params.get("region")
    if region is not None and not isinstance(region, dict):
        raise RuntimeError("split_mesh: region must be "
                           "{'min':[x,y,z], 'max':[x,y,z]}")
    if mode not in ("dry-run", "split", "split-region"):
        raise RuntimeError(f"split_mesh: mode must be dry-run|split|"
                           f"split-region (region implies its own "
                           f"dry-run), got {mode!r}")
    if mode == "split" and region is not None:
        raise RuntimeError("split_mesh: loose-parts split takes no "
                           "region — use mode split-region")
    # s18 B12: params read only in some modes were silently accepted (and
    # ignored) in the others — new_id only feeds split-region, ack_risks
    # only split/split-region, ack_many_parts only split. A patch carrying
    # ack_risks on a dry-run LOOKED acknowledged and wasn't. Per-mode
    # allowed-key set; extras refuse naming the mode and the valid params.
    allowed = {"output"}
    if region is not None:
        allowed.add("region")
    if mode == "split":
        allowed |= {"ack_risks", "ack_many_parts"}
    elif mode == "split-region":
        allowed |= {"new_id", "ack_risks"}
    # 'mode' is the SELECTOR — it is always legal regardless of its value
    # (s18 battery: the L13 dry-run contract regression caught this).
    extra = set(params) - allowed - {"op", "id", "mode"}
    if extra:
        raise RuntimeError(
            f"split_mesh: mode {mode!r} does not take param(s) "
            f"{sorted(extra)} — valid params for this mode: "
            f"{sorted(allowed | {'id'})} (plus 'op')")
    if mode == "dry-run":
        if region is not None:
            rep = _SL.analyze_region(obj, region)
            rep["mode"] = "dry-run-region"
        else:
            rep = _SL.analyze_split(obj)
    elif mode == "split":
        rep = _SL.split_object(obj, ack_risks=bool(params.get("ack_risks",
                                                              False)),
                               ack_many_parts=bool(params.get(
                                   "ack_many_parts", False)))
    else:  # split-region (mode validity enforced above)
        if region is None:
            raise RuntimeError("split_mesh: split-region requires the "
                               "region param (run a dry-run first)")
        rep = _SL.split_region(obj, region, new_id=params.get("new_id"),
                               ack_risks=bool(params.get("ack_risks",
                                                         False)))
    out = params.get("output")
    if out:
        d = os.path.dirname(os.path.abspath(out))
        os.makedirs(d, exist_ok=True)
        with open(out, "w") as f:
            json.dump(rep, f, indent=2)
    if mode in ("dry-run", "dry-run-region"):
        if region is not None:
            print(f"[apply_patch] split_mesh REGION DRY-RUN "
                  f"'{obj.name}': verts_in_region={rep['verts_in_region']}, "
                  f"faces_to_cut={rep['faces_to_cut']}, "
                  f"captured_bbox={rep['captured_bbox']}, "
                  f"risks={rep['risks'] or 'none'}")
            if rep["faces_to_cut"]:
                print("[apply_patch]   re-run with \"mode\":\"split-region\" "
                      "to cut it out")
            return
        print(f"[apply_patch] split_mesh DRY-RUN '{obj.name}': "
              f"{rep['part_count']} component(s), co_users={rep['co_users']}, "
              f"risks={rep['risks'] or 'none'}")
        for i, p in enumerate(rep["parts"][:6], 1):
            print(f"[apply_patch]   part{i}: faces={p['n_faces']} "
                  f"dims={p['dims']}")
        if rep["part_count"] > 1:
            print("[apply_patch]   re-run with \"mode\":\"split\" to "
                  "separate (read the risks first); welded geometry with "
                  "part_count=1 needs a REGION cut instead")
    elif mode == "split-region":
        print(f"[apply_patch] split_mesh REGION CUT '{rep['source']}': "
              f"{rep['faces_cut']} faces -> '{rep['new_object']}' "
              f"bbox={rep['new_object_bbox']}")
        print(f"[apply_patch]   next: {rep['next']}")
        for w in rep["warnings"]:
            print(f"[apply_patch]   WARNING {w}")
    else:
        print(f"[apply_patch] split_mesh SPLIT '{rep['source']}': "
              f"{rep['part_count']} parts "
              f"(materials inherited: {rep['materials_inherited']})")
        for p in rep["parts"][:8]:
            print(f"[apply_patch]   {p['old_name']} -> {p['name']} "
                  f"(faces={p['n_faces']})")
        for w in rep["warnings"]:
            print(f"[apply_patch]   WARNING {w}")


def _apply_mesh_prepare(obj, params):
    """R6: pre-welded-import geometry for region cuts (triangulate fused
    n-gons). Run BEFORE split_mesh when a dry-run reports verts_in_region
    but 0 faces_to_cut — the fused-face signature."""
    import semantic_lib as _SL
    rep = _SL.prepare_mesh(obj, mode=params.get("mode", "triangulate"))
    out = params.get("output")
    if out:
        d = os.path.dirname(os.path.abspath(out))
        os.makedirs(d, exist_ok=True)
        with open(out, "w") as f:
            json.dump(rep, f, indent=2)
    print(f"[apply_patch] mesh_prepare '{obj.name}': "
          f"{rep['ngons_triangulated']} n-gons triangulated "
          f"({rep['faces_before']} -> {rep['faces_after']} faces)")


MUTATIONS = {
    "set_location":             (_apply_set_location, True),
    "move_to":                  (_apply_move_to, True),
    "set_rotation":             (_apply_set_rotation, True),
    "set_scale":                (_apply_set_scale, True),
    "set_material_color":       (_apply_set_material_color, True),
    "set_material_roughness":   (_apply_set_material_roughness, True),
    "set_material_metallic":    (_apply_set_material_metallic, True),
    "delete_object":            (_apply_delete_object, True),
    "duplicate_object":         (_apply_duplicate_object, True),
    "set_camera_location":      (_apply_set_camera_location, True),
    "set_camera_lens":          (_apply_set_camera_lens, True),
    "set_camera_dof":           (_apply_set_camera_dof, True),
    "set_light_energy":         (_apply_set_light_energy, True),
    "set_light_color":          (_apply_set_light_color, True),
    "set_world_strength":      (_apply_set_world_strength, False),
    "set_exposure":            (_apply_set_exposure, False),
    "set_frame":                (_apply_set_frame, False),
    "render_viewport":          (_apply_render_viewport, False),
    "place_on":                 (_apply_place_on, True),
    "seat_at":                  (_apply_seat_at, True),
    "snap_z":                   (_apply_snap_z, True),
    "heat_bake":                (_apply_heat_bake, True),
    "audit":                    (_apply_audit, False),
    "seam_views":               (_apply_seam_views, False),
    "clear_bvh_cache":          (_apply_clear_bvh_cache, False),
    "physics_settle":           (_apply_physics_settle, False),
    "physics_place":            (_apply_physics_place, True),
    "physics_oracle":           (_apply_physics_oracle, True),
    "physics_gate":             (_apply_physics_gate, False),
    "add_cube":                 (_apply_add_cube, False),
    "add_sphere":               (_apply_add_sphere, False),
    "add_cylinder":             (_apply_add_cylinder, False),
    "add_cone":                 (_apply_add_cone, False),
    "add_torus":                (_apply_add_torus, False),
    "add_plane":                (_apply_add_plane, False),
    "add_empty":                (_apply_add_empty, False),
    "label_objects":            (_apply_label_objects, False),
    "split_mesh":               (_apply_split_mesh, True),
    "mesh_prepare":             (_apply_mesh_prepare, True),
}

# wave-1 friction #2/#11: param schemas were only discoverable by
# trial-and-error KeyError. One-line-per-op signature for --list and
# for friendly error conversion in apply_mutation.
# F2B-10: this dict is the ALLOWED-KEY source of truth for
# _warn_unknown_keys — every key listed here must be a key the handler
# actually reads, and every key a handler reads must be listed here
# (enforced bidirectionally by tests/test_s17_wave_b.py's AST parity
# check). The tokenizer in _doc_keys splits ONLY on depth-0 commas, so
# parenthesized/bracketed detail is safe.
PARAM_DOCS = {
    "set_location":       "id, location:[x,y,z]",
    "move_to":            "id, target:[x,y,z], reference?(bottom-center|centroid|origin), override?, output?",
    "set_rotation":       "id, rotation_deg:[rx,ry,rz]",
    "set_scale":          "id, scale:[sx,sy,sz]",
    "set_material_color": "id, color:[r,g,b(,a)]",
    "set_material_roughness": "id, roughness:float",
    "set_material_metallic":  "id, metallic:float",
    "delete_object":      "id",
    "duplicate_object":   "id, new_id, location?, rotation_deg?, scale?",
    "set_camera_location": "id, location:[x,y,z]",
    "set_camera_lens":    "id, lens_mm:float",
    "set_camera_dof":     "id, focus_distance(m), focus_distance_m?(legacy alias), aperture_fstop",
    "set_light_energy":   "id, energy:float(watts)",
    "set_light_color":    "id, color:[r,g,b]",
    "set_world_strength": "strength:float",
    "set_exposure":       "exposure:float (EV shift)",
    "set_frame":          "frame:int",
    "render_viewport":    "output:path, angle?(persp|front|side|top|back|right|active|custom), engine?(workbench|eevee|cycles), width?, height?, samples?, target?:[x,y,z], lens?, custom_location?, custom_loc?(legacy alias — F2B-1)",
    "place_on":           "id, supports:[names..] (name the TOPMOST surface!), clearance?, footprint?(bottom|all|grid), mode?(rest|sink|p25|p50|p75), grid_n?, inset?(meters), keep_xy?(true only — false refused, F2B-4), align_to_surface?, override?(keyframe=REBASE animation path), contact_band_mm?, output?",
    "seat_at":            "id, seat:anchor-empty-name, reference?(bottom|origin|centroid), offset?:[dx,dy,dz] (empty's local space), align?(bool), seat_mesh?, override?(keyframe=REBASE animation path), contact_band_mm?, output?",
    "snap_z":             "id, target_z:float, reference?(bottom|origin|centroid), override?, output?",
    "heat_bake":          "id, others:[names..], yellow_mm?, green_mm?",
    "audit":              "pairs?:['A,B',..], id?(scope report to this object), exclude?:[names], sample?(verts|verts+edges|bottom), contact_band_mm?, clearance_pad_mm?, force?(bool — audit skinned/animated pairs anyway), fail_on_penetration?(bool, default true), output?",
    "seam_views":         "a:name, b:name, out_dir:path, res?:[w,h], engine?, contact_band_mm?, fill_frac?",
    "clear_bvh_cache":    "-",
    "physics_settle":     "objs?:[names] (null=whole scene; [] refused — F2B-23), environment?:[names], frames?, apply?, repair_penetrations?(refuse|physics), tol_mm?, allow_bake?, allow_copy?, pad_mm?, snap?, snap_cap_mm?, output?",
    "physics_place":      "id, drop_mm?, frames?, snap?, snap_cap_mm?, apply?, tol_mm?, allow_bake?, allow_copy?, pad_mm?, output?",
    "physics_oracle":     "id, target_z?:float, target?:[x,y,z], frames?, pad_mm?, tol_mm?, intended_support?:name, allow_bake?, allow_copy?, output?",
    "physics_gate":       "fail_hard?(bool), verify_movers?:[names], tol_mm?, frames?, pad_mm?, audit_pad_mm?, output?",
    "add_cube":           "id, size?(scalar|[x,y,z]), location?(CENTER!), rotation_deg?, color?",
    "add_sphere":         "id, radius?(default 0.5), segments?, ring_count?, location?(CENTER!), rotation_deg?, color?",
    "add_cylinder":       "id, radius, depth, location?(CENTER!), vertices?, rotation_deg?, color?",
    "add_cone":           "id, radius1, radius2?, depth, vertices?, location?(CENTER!), rotation_deg?, color?",
    "add_torus":          "id, major_radius, minor_radius, location?(CENTER!), rotation_deg?, color?",
    "add_plane":          "id, size?(scalar|[x,y] — flat), location?(CENTER!), rotation_deg?, color?",
    "add_empty":          "id, location, empty_type?, size?, rotation_deg?, color?",
    "label_objects":      "labels:{id: label|{label,confidence}}, rename?(bool, default false — additive kit_label is the v1 identity), on_collision?(suffix|fail), output?(report json; default output/labels_report.json)",
    "split_mesh":         "id, mode?(dry-run|split|split-region, default dry-run; region param implies region dry-run), region?({min:[x,y,z],max:[x,y,z]} world box — vision-driven cut for WELDED geometry), new_id?(region-cut name), ack_risks?(bool — required when co-users/modifiers/shape-keys/armature present), ack_many_parts?(bool — required when loose parts > 50, F19: prefer vendor-node granularity or a region cut), output?(report json)",
    "mesh_prepare":       "id, mode?(triangulate — the only mode; pre-welded-import n-gon triangulation so region cuts can capture fused floor/wall faces), output?(report json)",
}


def _doc_keys(op: str) -> set:
    """Extract the real param-key set from an op's PARAM_DOCS signature.

    F2B-10: the allowed set for _warn_unknown_keys used to come from a
    naive doc.split(",") — parenthesized detail leaked in as junk tokens
    (set_camera_dof's "focus_distance(m)" never matched the live
    focus_distance key, so the warning claimed an APPLIED param was
    ignored) and list literals spawned phantom keys. Split only on
    depth-0 commas; a key is the token up to its first : ( ? or !.
    Shared with the test suite's AST parity check (single source of
    truth)."""
    keys = {"op", "id"}
    doc = PARAM_DOCS.get(op)
    if not doc:
        return keys
    tokens = []
    token = ""
    depth = 0
    for ch in doc:
        if ch in "([{":
            depth += 1
        elif ch in ")]}" and depth > 0:
            depth -= 1
        if ch == "," and depth == 0:
            tokens.append(token)
            token = ""
        else:
            token += ch
    if token.strip():
        tokens.append(token)
    for tok in tokens:
        cut = len(tok)
        for sep in ":?!(":
            i = tok.find(sep)
            if i != -1:
                cut = min(cut, i)
        name = tok[:cut].strip()
        if name and name.isidentifier():
            keys.add(name)
    return keys


def _warn_unknown_keys(op: str, mut: dict):
    """wave-3: a misspelled OPTIONAL key (refrence vs reference) silently
    fell back to the default — placement semantics changed with zero
    warning. F2B-10: the allowed set now derives from _doc_keys (the same
    tokenizer the parity test uses) over a PARAM_DOCS that lists every
    key the handler reads — so a warning means the key is TRULY unknown
    (undocumented AND unread), not merely missing from stale prose."""
    allowed = _doc_keys(op)
    unknown = [k for k in mut if k not in allowed]
    if unknown:
        print(f"[apply_patch] WARNING: op '{op}' got unknown param(s) "
              f"{sorted(unknown)} (ignored — check spelling); "
              f"signature: {PARAM_DOCS.get(op, '(see --list)')}")


def apply_mutation(mut: dict):
    op = mut.get("op")
    if op not in MUTATIONS:
        raise RuntimeError(f"Unknown mutation op: {op}. "
                           f"Known: {list(MUTATIONS.keys())}")
    fn, needs_obj = MUTATIONS[op]
    # F2B-14: the old guard (`obj is None and "id" in mut`) was DEAD code —
    # _get_obj raises instead of returning None, so a missing id reached the
    # handler as obj=None and died on a raw AttributeError (or worse, a
    # swallowed one). Make the intended guard live and name the op.
    obj = None
    if needs_obj:
        if "id" not in mut:
            raise RuntimeError(
                f"op '{op}' requires key 'id' (the target object name); "
                f"signature: {PARAM_DOCS.get(op, '(see --list)')}")
        obj = _get_obj(mut["id"], op)
    _warn_unknown_keys(op, mut)
    try:
        fn(obj, mut)
    except KeyError as e:
        # wave-1: bare KeyError('target') taught consumers nothing —
        # convert to the op's signature (add_* ops raise their own
        # friendly errors already).
        raise RuntimeError(
            f"op '{op}' missing/invalid param {e}; signature: "
            f"{PARAM_DOCS.get(op, '(see --list)')}") from None
    print(f"[apply_patch] applied: {op}" +
          (f" on '{mut['id']}'" if needs_obj and obj else ""))


def _read_patch(args) -> dict:
    """Parse --patch / --patch-json into the patch dict.

    Extracted from main() (F2B-26) so the JSON-shape guards are unit-
    testable; behavior unchanged. Exits 1 with a clean message on:
    invalid JSON, --patch file not found, --patch-json that is neither
    inline JSON nor a .json path (D1 fallback), and a non-object JSON
    root (a list root used to crash later with AttributeError on
    patch.get)."""
    if args.patch_json:
        src = args.patch_json
        # D1 (session 16): consumers confuse --patch (file) with
        # --patch-json (inline). A .json path in --patch-json parses
        # as "Expecting value: line 1 column 1" — accept the file.
        try:
            if src.lstrip().startswith("{"):
                patch = json.loads(src)
            elif os.path.isfile(src) and src.endswith(".json"):
                patch = json.load(open(src))
                print(f"[apply_patch] --patch-json resolved as file path: {src}")
            else:
                print("[apply_patch] ERROR: --patch-json is not inline JSON "
                      "and not a path to an existing .json file — use "
                      "--patch for patch files", file=sys.stderr)
                sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"[apply_patch] ERROR: invalid JSON in patch: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        if not os.path.isfile(args.patch):
            print(f"[apply_patch] ERROR: patch file not found: {args.patch}",
                  file=sys.stderr)
            sys.exit(1)
        with open(args.patch) as f:
            try:
                patch = json.load(f)
            except json.JSONDecodeError as e:
                print(f"[apply_patch] ERROR: invalid JSON in patch: {e}",
                      file=sys.stderr)
                sys.exit(1)
    if not isinstance(patch, dict):
        # F2B-26: a JSON-array root crashed with AttributeError on
        # patch.get("mutations") — a patch is an OBJECT.
        print(f"[apply_patch] ERROR: patch JSON must be an object "
              f'{{"mutations": [...], ...}}, got root type '
              f"{type(patch).__name__}", file=sys.stderr)
        sys.exit(1)
    return patch


def _animate_scene_module(mod, ctx, frames=24):
    """Bind+call mod.animate under BOTH exporter contracts (F2B-24).

    export_preflight S1 accepts a bare `def animate(ctx)` module (the
    exporter's sentinel dispatch, export_previz_package.py:1043-1048),
    but this call site used to pass start_frame/n_frames unconditionally
    — the module TypeErrored BEFORE any mutation ran. Signature-bind the
    sentinel call; fall back to the bare branch when it cannot bind (the
    module owns its timeline). A TypeError raised INSIDE animate still
    propagates loudly (the call sits outside the bind try)."""
    if not hasattr(mod, "animate"):
        return
    import inspect as _inspect
    sentinel = {"start_frame": 1, "n_frames": frames}
    bindable = False
    try:
        _inspect.signature(mod.animate).bind(ctx, **sentinel)
        bindable = True
    except TypeError:
        bindable = False
    if bindable:
        mod.animate(ctx, **sentinel)
    else:
        mod.animate(ctx)


def main():
    p = argparse.ArgumentParser(
        description="Apply a JSON patch to a Blender scene for fast iteration.")
    p.add_argument("--patch", help="Path to JSON patch file")
    p.add_argument("--patch-json", help="Inline JSON patch string")
    p.add_argument("--save-blend", default=None,
                   help="Save the resulting scene to this .blend path")
    p.add_argument("--export-schema", default=None,
                   help="Export the resulting scene schema to this JSON path")
    p.add_argument("--fail-on-physics-failure", action="store_true",
                   help="exit 3 if any physics_* mutation ended with "
                        "ok=false (default: warn only; gate fail_hard "
                        "always exits 2 on REJECTED)")
    p.add_argument("--with-bounds", action="store_true",
                   help="include world-space bounds in --export-schema output")
    p.add_argument("--list", action="store_true",
                   help="List all supported mutation ops and exit")
    p.add_argument("--camera", default=None,
                   help="Camera object name for the set_camera_dof CLI "
                        "shortcut (default: 'Camera')")
    p.add_argument("--focus-distance", type=float, default=None,
                   dest="focus_distance", metavar="M",
                   help="set_camera_dof CLI shortcut: focus distance in "
                        "meters (axial distance to the plane of sharp focus)")
    p.add_argument("--aperture-fstop", type=float, default=None,
                   dest="aperture_fstop", metavar="N",
                   help="set_camera_dof CLI shortcut: aperture f-stop "
                        "(aperture radius = lens/(2*fstop))")
    args = p.parse_args(script_argv())

    if args.list:
        print("[apply_patch] supported mutation ops (op: id? | params):")
        for op, (_fn, needs_obj) in sorted(MUTATIONS.items()):
            if op.startswith("add_"):
                tag = "required (op creates it)"
            else:
                tag = "required" if needs_obj else "optional"
            print(f"  {op:24s} id={tag}")
            doc = PARAM_DOCS.get(op)
            if doc:
                print(f"{'':26s}{doc}")
        print("[apply_patch] set_camera_dof params: focus_distance (m), "
              "aperture_fstop — or CLI: --camera --focus-distance "
              "--aperture-fstop")
        return

    # CLI shortcut: synthesize a set_camera_dof mutation, appended AFTER the
    # patch's own mutations (a patch can load/build the scene first). The
    # patch is REQUIRED to carry load_blend/scene — the shortcut alone would
    # target a cleared factory scene (F2B-22 guard below).
    dof_shortcut = None
    if args.focus_distance is not None or args.aperture_fstop is not None:
        dof_shortcut = {
            "op": "set_camera_dof",
            "id": args.camera if args.camera else "Camera",
        }
        if args.focus_distance is not None:
            dof_shortcut["focus_distance"] = args.focus_distance
        if args.aperture_fstop is not None:
            dof_shortcut["aperture_fstop"] = args.aperture_fstop
        print(f"[apply_patch] CLI shortcut: {dof_shortcut}")

    if not args.patch and not args.patch_json and not dof_shortcut:
        print("[apply_patch] ERROR: --patch or --patch-json required "
              "(or --focus-distance/--aperture-fstop for the DoF shortcut)",
              file=sys.stderr)
        sys.exit(1)

    if args.patch or args.patch_json:
        patch = _read_patch(args)
    else:
        patch = {}
    if dof_shortcut:
        patch.setdefault("mutations", []).append(dof_shortcut)
        # F2B-22: the shortcut alone used to clear the FACTORY scene (the
        # fresh-scene path below) and then fail "object 'Camera' not found"
        # — a guaranteed-fail path the comment above claimed was supported.
        # Refuse with guidance instead of clearing.
        if "load_blend" not in patch and "scene" not in patch:
            print("[apply_patch] ERROR: the DoF CLI shortcut needs a scene "
                  "with a camera — combine it with a patch that has "
                  "load_blend or scene, e.g.\n  apply_patch --patch-json "
                  "'{\"load_blend\": \"scene.blend\"}' --focus-distance 2.5",
                  file=sys.stderr)
            sys.exit(1)

    # Load or build scene
    _patch_had_load_blend = False
    if "load_blend" in patch:
        _patch_had_load_blend = True
        blend_path = patch["load_blend"]
        # F2B-26: a missing file used to surface as a raw wm.open_mainfile
        # operator error; fail in kit style instead.
        if not isinstance(blend_path, str) or not os.path.isfile(blend_path):
            print(f"[apply_patch] ERROR: load_blend file not found: "
                  f"{blend_path}", file=sys.stderr)
            sys.exit(1)
        print(f"[apply_patch] loading .blend: {blend_path}")
        bpy.ops.wm.open_mainfile(filepath=blend_path)
        try:  # stale BVH trees cannot survive a file load
            import placement_lib as _pl0
            _pl0.clear_bvh_cache()
        except ImportError:
            pass
    elif "scene" in patch:
        from blender_kit import safe_import_scene
        print(f"[apply_patch] building scene from module: {patch['scene']}")
        mod = safe_import_scene(patch["scene"])
        clear_scene()
        ctx = mod.build_scene()
        _animate_scene_module(mod, ctx, frames=patch.get("frames", 24))
    else:
        # Fresh-scene patch (no load_blend / scene field): the bare
        # blender process starts from the FACTORY startup scene, which
        # contains a 2 m default Cube (+ camera + light). The Cube
        # poisons every downstream op — audits report Cube x <anything>
        # penetrations, physics refuses movers as REFUSED_PENETRATING
        # against phantom terrain (session-16 subject v3, 5.2.2).
        # A patch workflow never wants the factory contents.
        from blender_kit import clear_scene as _clear_scene
        _clear_scene()
        print("[apply_patch] using fresh scene (factory startup objects "
              "cleared: default Cube/camera/light)")

    # Apply mutations in order
    mutations: List[dict] = patch.get("mutations", [])
    print(f"[apply_patch] applying {len(mutations)} mutation(s)...")

    def _chain_abort(i, total, reason):
        """Shared chain-abort tail for BOTH abort classes (s18 B3): a
        plain RuntimeError AND a physics gate fail_hard SystemExit(2) —
        the gate's sys.exit is a BaseException, so the old `except
        Exception` never saw it and exactly the scenario --save-blend was
        built for (abort after in-memory placement) lost the save."""
        print(f"[apply_patch] ERROR on mutation {i+1}/{total}: {reason}",
              file=sys.stderr)
        if args.save_blend:
            # round-E subject B (W1): a fail_hard gate aborts the
            # chain AFTER in-memory placement — silently losing the
            # work cost a full re-invocation. Ops commit atomically,
            # so the state at the abort is consistent (possibly
            # mid-op for the aborting one) — save it and say so.
            os.makedirs(os.path.dirname(os.path.abspath(args.save_blend)),
                        exist_ok=True)
            bpy.ops.wm.save_as_mainfile(filepath=args.save_blend)
            print(f"[apply_patch] CHAIN ABORTED at mutation {i+1}/{total}; "
                  f"scene state SAVED to {args.save_blend} anyway "
                  f"(the aborting op's change may be incomplete — "
                  f"verify with physics_gate)", file=sys.stderr)

    for i, mut in enumerate(mutations):
        try:
            apply_mutation(mut)
        except Exception as e:
            _chain_abort(i, len(mutations), e)
            sys.exit(1)
        except SystemExit as e:
            # s18 B3: physics gate fail_hard raises SystemExit(2)
            # (physics_place.gate) — run the SAME save+message, then
            # re-raise so the exit code stays 2 (converting it to a
            # different code would lie to shell pipelines that grep it).
            _chain_abort(i, len(mutations),
                         f"SystemExit({e.code}) — a fail-hard op aborted "
                         f"the chain (its verdict line is above)")
            raise

    # Optional save
    if args.save_blend:
        os.makedirs(os.path.dirname(os.path.abspath(args.save_blend)), exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=args.save_blend)
        print(f"[apply_patch] saved {args.save_blend}")
    elif _patch_had_load_blend:
        # W1 (session 16): mutations live in memory only; downstream tools
        # that re-read the on-disk .blend (scene_schema, oracle, another
        # patch) see the STALE pre-patch state. Say so, loudly.
        print("[apply_patch] WARNING: mutations applied in MEMORY only — "
              "no --save-blend given, so the on-disk .blend still holds "
              "the pre-patch state. Pass --save-blend to persist before "
              "scene_schema/oracle/gate re-reads.", file=sys.stderr)

    # Optional schema export
    if args.export_schema:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from scene_schema import export_scene_schema
        schema = export_scene_schema(with_bounds=args.with_bounds)
        os.makedirs(os.path.dirname(os.path.abspath(args.export_schema)), exist_ok=True)
        with open(args.export_schema, "w") as f:
            json.dump(schema, f, indent=2)
        print(f"[apply_patch] exported schema -> {args.export_schema}")

    print("[apply_patch] done.")
    if args.fail_on_physics_failure and _PHYSICS_FAILURES:
        print(f"[apply_patch] exiting 3: "
              f"{len(_PHYSICS_FAILURES)} physics op(s) not ok: "
              f"{_PHYSICS_FAILURES}")
        sys.exit(3)


if __name__ == "__main__":
    main()
