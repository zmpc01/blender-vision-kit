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
      #58): add_cube/add_plane take "size" (scalar or [x,y(,z)]);
      add_sphere "radius"; add_cylinder "radius"+"depth"; add_cone
      "radius1"(+"radius2" for truncated)+"depth"; add_torus
      "major_radius"+"minor_radius"; add_empty "empty_type"+"size".
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

    # CLI shortcut: set camera DoF without writing a patch JSON (applies to
    # the current scene, or the one loaded via --patch/--patch-json):
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
    color = params["color"]
    if len(color) == 3:
        color = (*color, 1.0)
    bsdf.inputs["Base Color"].default_value = color
    # Also set diffuse_color — Workbench engine reads THIS, not BSDF (gotcha #56)
    mat.diffuse_color = color


def _apply_set_material_roughness(obj, params):
    mat = obj.data.materials[0]
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Roughness"].default_value = params["roughness"]


def _apply_set_material_metallic(obj, params):
    mat = obj.data.materials[0]
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Metallic"].default_value = params["metallic"]


def _apply_delete_object(obj, params):
    bpy.data.objects.remove(obj, do_unlink=True)


def _apply_duplicate_object(obj, params):
    new_obj = obj.copy()
    if obj.data:
        new_obj.data = obj.data.copy()
    bpy.context.collection.objects.link(new_obj)
    new_obj.name = params["new_id"]
    if "location" in params:
        new_obj.location = tuple(params["location"])
    if "rotation_deg" in params:
        new_obj.rotation_euler = tuple(math.radians(v) for v in params["rotation_deg"])
    if "scale" in params:
        new_obj.scale = tuple(params["scale"])


def _apply_set_camera_location(obj, params):
    if obj.type != 'CAMERA':
        raise RuntimeError(f"{obj.name} is not a camera")
    obj.location = tuple(params["location"])


def _apply_set_camera_lens(obj, params):
    if obj.type != 'CAMERA':
        raise RuntimeError(f"{obj.name} is not a camera")
    obj.data.lens = params["lens_mm"]


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
        dof.focus_distance = float(focus)
    if fstop is not None:
        dof.aperture_fstop = float(fstop)
    print(f"[apply_patch] set_camera_dof: {obj.name} "
          f"focus_distance={dof.focus_distance:.6g} m, "
          f"aperture_fstop={dof.aperture_fstop:.6g} (aperture radius "
          f"= lens/(2*fstop) = {obj.data.lens / (2.0 * dof.aperture_fstop):.6g} mm)")


def _apply_set_frame(obj, params):
    # obj is None for this op
    bpy.context.scene.frame_set(params["frame"])


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
    target_str = params.get("target")
    if target_str:
        target = tuple(target_str)
    else:
        target = _compute_scene_center()
    lens = params.get("lens", 50)
    custom_loc = params.get("custom_location")
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
    obj.data.energy = params["energy"]


def _apply_set_light_color(obj, params):
    if obj.type != 'LIGHT':
        raise RuntimeError(f"{obj.name} is not a light")
    obj.data.color = tuple(params["color"])




def _apply_set_world_strength(obj, params):
    """Set the World background strength (sky/HDRI intensity). obj is None."""
    scene = bpy.context.scene
    if not scene.world or scene.world.node_tree is None:
        raise RuntimeError("Scene has no node-based world")
    bg = scene.world.node_tree.nodes.get("Background")
    if bg is None:
        raise RuntimeError("World has no Background node")
    bg.inputs["Strength"].default_value = params["strength"]


def _apply_set_exposure(obj, params):
    """Set the scene's render exposure (in EV stops). obj is None."""
    bpy.context.scene.view_settings.exposure = params["exposure"]



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
    rep = _PL.move_to(obj, _require(params, "target", "move_to",
                                     expected_type=list, expected_len=3),
                      reference=params.get("reference", "bottom-center"),
                      override=params.get("override"),
                      output=params.get("output"))
    _LAST_REPORTS["move_to"] = rep
    print("[apply_patch] move_to:", rep["obj"], "target",
          rep["target"], "ref", rep["reference"],
          "(applied delta", [round(v, 3) for v in rep["applied_translation_m"]], ")")


def _apply_place_on(obj, params):
    supports = [_get_obj(s, "place_on") for s in params["supports"]]
    rep = _PL.place_on(
        obj, *supports,
        clearance=params.get("clearance", 0.0),
        footprint=params.get("footprint", "bottom"),
        mode=params.get("mode", "rest"),
        grid_n=params.get("grid_n", 12),
        inset=params.get("inset", 0.0),
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
    rep = _PL.seat_at(
        obj, seat,
        reference=params.get("reference", "bottom"),
        offset=params.get("offset"),
        align=params.get("align", True),
        override=params.get("override"),
        seat_mesh=bpy.data.objects.get(params["seat_mesh"]) if params.get("seat_mesh") else None,
        contact_band_mm=params.get("contact_band_mm", 0.1),
        output=params.get("output"))
    _LAST_REPORTS["seat_at"] = rep
    print("[apply_patch] seat_at:", rep["obj"], "->",
          "OK" if rep.get("ok", True) else "CONTACT-ISSUES")


def _apply_snap_z(obj, params):
    rep = _PL.snap_z(obj, params["target_z"],
                     reference=params.get("reference", "bottom"),
                     override=params.get("override"),
                     output=params.get("output"))
    _LAST_REPORTS["snap_z"] = rep
    print("[apply_patch] snap_z:", rep["obj"], "-> z =", rep["result_z"])


def _apply_audit(obj, params):
    pairs = None
    if params.get("pairs"):
        pairs = [tuple(p.split(",")) for p in params["pairs"]]
    exclude = tuple(params.get("exclude", ()))
    rep = _PL.audit_scene(pairs=pairs, exclude=exclude,
                          sample=params.get("sample", "verts"),
                          contact_band_mm=params.get("contact_band_mm", 0.1),
                          clearance_pad_mm=params.get("clearance_pad_mm", 100.0),
                          force=params.get("force", False))
    scope_id = params.get("id")
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
        counts = {}
        for p in scoped:
            counts[p["verdict"]] = counts.get(p["verdict"], 0) + 1
        rep["state_counts"] = counts
        rep["failed"] = any(p["verdict"] == "PENETRATING" for p in scoped)
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
    rep = _PP.settle(objs=_resolve_objlist(params.get("objs"), "physics_settle") or None,
                     environment=_resolve_objlist(
                         params.get("environment")) or [],
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
    rep = _PP.oracle(target,
                     target_z=params.get("target_z"),
                     target=params.get("target"),
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


def _apply_seam_views(obj, params):
    a = _get_obj(params["a"], "seam_views")
    b = _get_obj(params["b"], "seam_views")
    rep = _PL.seam_views(a, b, out_dir=params["out_dir"],
                         res=tuple(params.get("res", (640, 360))),
                         engine=params.get("engine", "workbench"),
                         contact_band_mm=params.get("contact_band_mm", 0.1),
                         fill_frac=params.get("fill_frac", 0.6))
    _LAST_REPORTS["seam_views"] = rep
    print("[apply_patch] seam_views:", json.dumps(rep["views"]))


def _apply_heat_bake(obj, params):
    others = [_get_obj(n, "heat_bake") for n in params["others"]]
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
    """D16: break a continuous mesh into labelable parts. mode=dry-run
    (default) analyzes connected components with ZERO residue; mode=split
    separates by loose parts (refuses on unacknowledged risks)."""
    import semantic_lib as _SL
    mode = params.get("mode", "dry-run")
    if mode == "dry-run":
        rep = _SL.analyze_split(obj)
    elif mode == "split":
        rep = _SL.split_object(obj, ack_risks=bool(params.get("ack_risks",
                                                              False)))
    else:
        raise RuntimeError(f"split_mesh: mode must be dry-run|split, "
                           f"got {mode!r}")
    out = params.get("output")
    if out:
        d = os.path.dirname(os.path.abspath(out))
        os.makedirs(d, exist_ok=True)
        with open(out, "w") as f:
            json.dump(rep, f, indent=2)
    if mode == "dry-run":
        print(f"[apply_patch] split_mesh DRY-RUN '{obj.name}': "
              f"{rep['part_count']} component(s), co_users={rep['co_users']}, "
              f"risks={rep['risks'] or 'none'}")
        for i, p in enumerate(rep["parts"][:6], 1):
            print(f"[apply_patch]   part{i}: faces={p['n_faces']} "
                  f"dims={p['dims']}")
        if rep["part_count"] > 1:
            print("[apply_patch]   re-run with \"mode\":\"split\" to "
                  "separate (read the risks first)")
    else:
        print(f"[apply_patch] split_mesh SPLIT '{rep['source']}': "
              f"{rep['part_count']} parts "
              f"(materials inherited: {rep['materials_inherited']})")
        for p in rep["parts"][:8]:
            print(f"[apply_patch]   {p['old_name']} -> {p['name']} "
                  f"(faces={p['n_faces']})")
        for w in rep["warnings"]:
            print(f"[apply_patch]   WARNING {w}")


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
}

# wave-1 friction #2/#11: param schemas were only discoverable by
# trial-and-error KeyError. One-line-per-op signature for --list and
# for friendly error conversion in apply_mutation.
PARAM_DOCS = {
    "set_location":       "id, location:[x,y,z]",
    "move_to":            "id, target:[x,y,z], reference?(bottom-center|centroid|origin), override?, output?",
    "set_rotation":       "id, rotation_deg:[rx,ry,rz]",
    "set_scale":          "id, scale:[sx,sy,sz]",
    "set_material_color": "id, color:[r,g,b(,a)], match?(name-regex)",
    "set_material_roughness": "id, roughness:float",
    "set_material_metallic":  "id, metallic:float",
    "delete_object":      "id",
    "duplicate_object":   "id, new_id",
    "set_camera_location": "id, location:[x,y,z]",
    "set_camera_lens":    "id, lens_mm:float",
    "set_camera_dof":     "id, focus_distance(m), aperture_fstop",
    "set_light_energy":   "id, energy:float(watts)",
    "set_light_color":    "id, color:[r,g,b]",
    "set_world_strength": "strength:float",
    "set_exposure":       "exposure:float (EV shift)",
    "set_frame":          "frame:int",
    "render_viewport":    "output:path, angle?(persp|front|side|top|back|right|active|custom), engine?(workbench|eevee|cycles), width?, height?, samples?, target?, custom_loc?",
    "place_on":           "id, supports:[names..] (name the TOPMOST surface!), clearance?, footprint?, mode?, keep_xy?, align_to_surface?, override?(keyframe=REBASE animation path), output?",
    "seat_at":            "id, seat:anchor-empty-name, reference?(bottom), offset?, align?(bool), seat_mesh?, override?(keyframe=REBASE animation path), output?",
    "snap_z":             "id, target_z:float, reference?(bottom|origin|centroid), override?, output?",
    "heat_bake":          "id",
    "audit":              "pairs?:['A,B',..], id?(scope report to this object), exclude?:[names], fail_on_penetration?(bool, default true), output?",
    "seam_views":         "id, supports",
    "clear_bvh_cache":    "-",
    "physics_settle":     "objs?:[names] (null=whole scene, almost never wanted), environment?:[names], frames?, apply?, repair_penetrations?(refuse|physics), snap?, output?",
    "physics_place":      "id, drop_mm?, snap?, output?",
    "physics_oracle":     "id, target_z:float, output?",
    "physics_gate":       "fail_hard?(bool), verify_movers?:[names], output?",
    "add_cube":           "id, size?(scalar|[x,y,z]), location?(CENTER!), rotation_deg?, color?",
    "add_sphere":         "id, radius, location?(CENTER!), segments?, color?",
    "add_cylinder":       "id, radius, depth, location?(CENTER!), vertices?, color?",
    "add_cone":           "id, radius1, radius2?, depth, location?(CENTER!), color?",
    "add_torus":          "id, radius_major, radius_minor, location?(CENTER!), color?",
    "add_plane":          "id, size, location?(CENTER!), color?",
    "add_empty":          "id, location, empty_type?, size?, rotation_deg?",
    "label_objects":      "labels:{id: label|{label,confidence}}, rename?(bool, default false — additive kit_label is the v1 identity), on_collision?(suffix|fail), output?(report json; default output/labels_report.json)",
    "split_mesh":         "id, mode?(dry-run|split, default dry-run), ack_risks?(bool — required when co-users/modifiers/shape-keys/armature present), output?(report json)",
}


def _warn_unknown_keys(op: str, mut: dict):
    """wave-3: a misspelled OPTIONAL key (refrence vs reference) silently
    fell back to the default — placement semantics changed with zero
    warning. Parse the op's PARAM_DOCS signature and warn on extras."""
    doc = PARAM_DOCS.get(op)
    if not doc:
        return
    allowed = {"op", "id"}
    for token in doc.split(","):
        token = token.strip()
        if not token:
            continue
        name = token.split(":")[0].split("?")[0].split("!")[0].strip()
        if name:
            allowed.add(name)
    unknown = [k for k in mut if k not in allowed]
    if unknown:
        print(f"[apply_patch] WARNING: op '{op}' got unknown param(s) "
              f"{sorted(unknown)} (ignored — check spelling); "
              f"signature: {doc}")


def apply_mutation(mut: dict):
    op = mut.get("op")
    if op not in MUTATIONS:
        raise RuntimeError(f"Unknown mutation op: {op}. "
                           f"Known: {list(MUTATIONS.keys())}")
    fn, needs_obj = MUTATIONS[op]
    obj = _get_obj(mut["id"]) if needs_obj and "id" in mut else None
    if needs_obj and obj is None and "id" in mut:
        raise RuntimeError(f"op '{op}' requires object id '{mut['id']}' but not found")
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
    # patch's own mutations (a patch can load/build the scene first; the
    # patch itself is optional when only the shortcut is used).
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
        try:
            if args.patch_json:
                src = args.patch_json
                # D1 (session 16): consumers confuse --patch (file) with
                # --patch-json (inline). A .json path in --patch-json parses
                # as "Expecting value: line 1 column 1" — accept the file.
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
            else:
                if not os.path.isfile(args.patch):
                    print(f"[apply_patch] ERROR: patch file not found: {args.patch}",
                          file=sys.stderr)
                    sys.exit(1)
                with open(args.patch) as f:
                    patch = json.load(f)
        except json.JSONDecodeError as e:
            print(f"[apply_patch] ERROR: invalid JSON in patch: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        patch = {}
    if dof_shortcut:
        patch.setdefault("mutations", []).append(dof_shortcut)

    # Load or build scene
    _patch_had_load_blend = False
    if "load_blend" in patch:
        _patch_had_load_blend = True
        blend_path = patch["load_blend"]
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
        if hasattr(mod, "animate"):
            mod.animate(ctx, start_frame=1, n_frames=patch.get("frames", 24))
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
    for i, mut in enumerate(mutations):
        try:
            apply_mutation(mut)
        except Exception as e:
            print(f"[apply_patch] ERROR on mutation {i+1}/{len(mutations)}: {e}",
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
                print(f"[apply_patch] CHAIN ABORTED at mutation {i+1}; "
                      f"scene state SAVED to {args.save_blend} anyway "
                      f"(the aborting op's change may be incomplete — "
                      f"verify with physics_gate)", file=sys.stderr)
            sys.exit(1)

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
