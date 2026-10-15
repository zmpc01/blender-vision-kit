# test_s18_wave_b.py — session-18 Wave-B fix regressions (in-Blender).
#
# Covers the wave-1-triage mutation-surface fixes assigned to Wave B:
#   1. B2: duplicate_object REFUSES an existing new_id (no silent .001
#      rename) and requires a non-empty string new_id.
#   2. B4: NaN/garbage refuses at the param layer — seat_at.offset,
#      place_on.clearance/inset/grid_n, audit.contact_band_mm (a NaN band
#      false-PASSES a penetrating scene: the bite check proves the
#      comparison still fires), physics_oracle.target/target_z,
#      render_viewport.custom_location/lens (target's sibling guards) —
#      each refusal leaves the scene unchanged.
#   3. B5: move_to refuses unknown reference tokens (placement_lib
#      falls through to bottom-center silently; Wave-C owns the lib side).
#   4. B6: audit refuses a typo'd scope id BEFORE the audit runs (the
#      old 0-pairs vacuous PASS of fail_on_penetration).
#   5. B11: heat_bake.others refuses a bare string / non-name entries;
#      seam_views.res requires [w, h] positive ints (no per-char atoms);
#      set_material_color validates shape and clamps to [0,1] like its
#      roughness/metallic siblings (Base Color is not an HDR channel in
#      this kit — glow goes through Emission Strength).
#   6. B12: split_mesh per-mode param sets — mode-mismatched params
#      (new_id / ack_risks / ack_many_parts) refuse naming the mode and
#      the valid params; valid combos still run.
#   7. B3: the chain-abort --save-blend save fires on SystemExit(2)
#      (physics gate fail_hard) — same save+message as the Exception
#      path, exit code 2 preserved; the Exception path still exits 1.
#   8. B8: scene_schema exports camera dof (use_dof/focus_distance/
#      aperture_fstop) and scene exposure — the write path (set_camera_dof
#      / set_exposure) is now visible to the read path (--export-schema).
#   9. B10: validate_scene dispatches a BARE `def animate(ctx)` scene
#      module (signature-bind split, the F2B-24 twin); sentinel modules
#      still receive start_frame/n_frames. Fixtures are WRITTEN INTO
#      scripts/ at runtime (fixture-location law: a temp dir is
#      unreachable by name-import — the t10 pattern) and cleaned up.
#
# Battery row to register in scripts/suite_runner.sh (orchestrator-owned):
#   "test_s18_wave_b|tests/test_s18_wave_b.py|BL||0|\[test_s18b\] ALL PASS|
#    session-18 wave-B mutation-surface regressions (in-Blender)"
#
# Run: ./scripts/blrun.sh --background --python tests/test_s18_wave_b.py
# Convention: prints [test_s18b] per check; "ALL PASS" at the end.

import io
import json
import os
import shutil
import sys
import tempfile
from contextlib import redirect_stdout, redirect_stderr

import bpy

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "scripts"))

import apply_patch as AP             # noqa: E402
import validate_scene as VS          # noqa: E402
import viewport_capture as VC        # noqa: E402

PASS = []
FAIL = []

NAN = float("nan")


def check(name, cond, detail=""):
    tag = "ok" if cond else "FAIL"
    print(f"[test_s18b] {name}: {tag}" + (f" — {detail}" if detail and not cond else ""))
    (PASS if cond else FAIL).append(name)


def wipe():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def expect_error(name, fn, *needles):
    """fn() must raise RuntimeError mentioning every needle."""
    try:
        fn()
    except RuntimeError as e:
        msg = str(e)
        missing = [n for n in needles if n not in msg]
        check(name, not missing, f"raised but missing {missing} in: {msg[:200]}")
        return msg
    except Exception as e:  # wrong exception class
        check(name, False, f"wrong exc {type(e).__name__}: {e}")
        return ""
    check(name, False, "no error raised")
    return ""


def capture(fn):
    """Run fn() capturing stdout; return (returned, captured_string)."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        out = fn()
    return out, buf.getvalue()


def add_mesh(name, loc, size=0.4):
    bpy.ops.mesh.primitive_cube_add(size=size, location=loc)
    o = bpy.context.active_object
    o.name = name
    return o


def add_plane(name, size=4):
    bpy.ops.mesh.primitive_plane_add(size=size, location=(0, 0, 0))
    o = bpy.context.active_object
    o.name = name
    return o


def loc_of(name):
    return tuple(bpy.data.objects[name].location)


_TMP = tempfile.mkdtemp(prefix="s18b_")

# ======================================================= 1. B2 duplicate
wipe()
add_mesh("DupSrc", (0, 0, 0.2))
expect_error("s18_1a.duplicate_existing_refused",
             lambda: AP.apply_mutation(
                 {"op": "duplicate_object", "id": "DupSrc",
                  "new_id": "DupSrc"}),
             "refuses", "DupSrc", "already exists")
check("s18_1b.no_silent_dot001",
      not any(o.name.startswith("DupSrc.0") for o in bpy.data.objects),
      str([o.name for o in bpy.data.objects]))
expect_error("s18_1c.duplicate_missing_new_id",
             lambda: AP.apply_mutation(
                 {"op": "duplicate_object", "id": "DupSrc"}),
             "new_id")
expect_error("s18_1d.duplicate_empty_new_id",
             lambda: AP.apply_mutation(
                 {"op": "duplicate_object", "id": "DupSrc", "new_id": ""}),
             "non-empty string")
expect_error("s18_1e.duplicate_nonstring_new_id",
             lambda: AP.apply_mutation(
                 {"op": "duplicate_object", "id": "DupSrc", "new_id": 7}),
             "non-empty string")
_, out = capture(lambda: AP.apply_mutation(
    {"op": "duplicate_object", "id": "DupSrc", "new_id": "DupCopy",
     "location": [2, 0, 0.2]}))
check("s18_1f.duplicate_valid_still_works",
      bpy.data.objects.get("DupCopy") is not None
      and bpy.data.objects["DupCopy"].location.x == 2.0
      and "refuses" not in out, out[-160:])

# ====================================== 2. B4 NaN / garbage param refuses
wipe()
add_plane("Ground")
add_mesh("Mover", (0, 0, 0.2))
bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0, 0, 1))
bpy.context.active_object.name = "SeatAnchor"
_before = loc_of("Mover")

# seat_at.offset
expect_error("s18_2a.seat_offset_nan_refused",
             lambda: AP.apply_mutation(
                 {"op": "seat_at", "id": "Mover", "seat": "SeatAnchor",
                  "offset": [0, 0, NAN]}),
             "offset", "NaN")
check("s18_2b.seat_offset_nan_scene_unchanged", loc_of("Mover") == _before,
      str(loc_of("Mover")))
expect_error("s18_2c.seat_offset_string_refused",
             lambda: AP.apply_mutation(
                 {"op": "seat_at", "id": "Mover", "seat": "SeatAnchor",
                  "offset": "0,0,1"}),
             "offset")
expect_error("s18_2d.seat_offset_short_refused",
             lambda: AP.apply_mutation(
                 {"op": "seat_at", "id": "Mover", "seat": "SeatAnchor",
                  "offset": [0, 0]}),
             "offset")

# place_on.clearance / inset / grid_n
expect_error("s18_2e.place_on_clearance_nan",
             lambda: AP.apply_mutation(
                 {"op": "place_on", "id": "Mover", "supports": ["Ground"],
                  "clearance": NAN}),
             "clearance", "NaN")
expect_error("s18_2f.place_on_clearance_negative",
             lambda: AP.apply_mutation(
                 {"op": "place_on", "id": "Mover", "supports": ["Ground"],
                  "clearance": -0.01}),
             "clearance", ">= 0")
expect_error("s18_2g.place_on_inset_nan",
             lambda: AP.apply_mutation(
                 {"op": "place_on", "id": "Mover", "supports": ["Ground"],
                  "inset": NAN}),
             "inset", "NaN")
expect_error("s18_2h.place_on_grid_n_zero",
             lambda: AP.apply_mutation(
                 {"op": "place_on", "id": "Mover", "supports": ["Ground"],
                  "grid_n": 0}),
             "grid_n")
expect_error("s18_2i.place_on_grid_n_string",
             lambda: AP.apply_mutation(
                 {"op": "place_on", "id": "Mover", "supports": ["Ground"],
                  "grid_n": "12"}),
             "grid_n")
expect_error("s18_2j.place_on_grid_n_fraction",
             lambda: AP.apply_mutation(
                 {"op": "place_on", "id": "Mover", "supports": ["Ground"],
                  "grid_n": 8.5}),
             "grid_n")
check("s18_2k.place_on_refusals_scene_unchanged", loc_of("Mover") == _before,
      str(loc_of("Mover")))

# audit.contact_band_mm — NaN band would false-PASS every '>' comparison
expect_error("s18_2l.audit_nan_band_refused",
             lambda: AP.apply_mutation(
                 {"op": "audit", "pairs": ["Ground,Mover"],
                  "contact_band_mm": NAN}),
             "contact_band_mm", "NaN")
expect_error("s18_2m.audit_negative_band_refused",
             lambda: AP.apply_mutation(
                 {"op": "audit", "pairs": ["Ground,Mover"],
                  "contact_band_mm": -1.0}),
             "contact_band_mm", ">= 0")
# the bite check: with a VALID band the gate still fails a penetrating
# scene (proves the band comparison did not go all-False). s18 fix x2:
# (1) same-spot cubes are exact-coplanar full overlap -> TOUCHING (the
# coplanar contact law); (2) an AXIS-offset of identical boxes is also
# blind — every vert of A lies ON B's boundary or outside it, so the
# vert-sampling inside-test abstains and the coplanar edges abstain the
# crossing test (documented classifier bound). Offset DIAGONALLY so a
# vert of A lands strictly inside B -> unambiguous PENETRATING.
add_mesh("PenA", (3, 0, 0.2))
add_mesh("PenB", (3.05, 0.05, 0.35))   # diagonal: strict inside-vert
expect_error("s18_2n.audit_penetrating_still_bites",
             lambda: AP.apply_mutation(
                 {"op": "audit", "pairs": ["PenA,PenB"]}),
             "penetration detected")

# physics_oracle.target / target_z
expect_error("s18_2o.oracle_target_nan",
             lambda: AP.apply_mutation(
                 {"op": "physics_oracle", "id": "Mover",
                  "target": [NAN, 0, 0]}),
             "target", "NaN")
check("s18_2p.oracle_refusal_scene_unchanged", loc_of("Mover") == _before,
      str(loc_of("Mover")))
expect_error("s18_2q.oracle_target_shape",
             lambda: AP.apply_mutation(
                 {"op": "physics_oracle", "id": "Mover", "target": [1, 2]}),
             "target")
expect_error("s18_2r.oracle_targetz_nan",
             lambda: AP.apply_mutation(
                 {"op": "physics_oracle", "id": "Mover", "target_z": NAN}),
             "target_z")

# render_viewport.custom_location / lens (target's sibling guards)
_png = os.path.join(_TMP, "s18_nan.png")
expect_error("s18_2s.render_customloc_nan",
             lambda: AP.apply_mutation(
                 {"op": "render_viewport", "output": _png, "angle": "custom",
                  "custom_location": [NAN, 0, 0]}),
             "custom_location", "NaN")
expect_error("s18_2t.render_customloc_string",
             lambda: AP.apply_mutation(
                 {"op": "render_viewport", "output": _png, "angle": "custom",
                  "custom_location": "1,2,3"}),
             "custom_location")
expect_error("s18_2u.render_lens_nan",
             lambda: AP.apply_mutation(
                 {"op": "render_viewport", "output": _png, "lens": NAN}),
             "lens")
expect_error("s18_2v.render_lens_zero",
             lambda: AP.apply_mutation(
                 {"op": "render_viewport", "output": _png, "lens": 0}),
             "lens")
expect_error("s18_2w.render_lens_string",
             lambda: AP.apply_mutation(
                 {"op": "render_viewport", "output": _png, "lens": "50"}),
             "lens")
check("s18_2x.render_refusals_wrote_nothing", not os.path.exists(_png))
# valid lens/custom_location pass through to render_angle (spy — no render)
_seen = {}
_orig_render = VC.render_angle


def _spy_render(angle, out, **kw):
    _seen["angle"] = angle
    _seen.update(kw)
    with open(out, "wb") as f:      # image_readiness returns {"error":..}
        f.write(b"\x89PNG\r\n\x1a\n")


try:
    VC.render_angle = _spy_render
    _, out = capture(lambda: AP.apply_mutation(
        {"op": "render_viewport", "output": _png, "lens": 35,
         "custom_location": [1, 2, 3]}))
    check("s18_2y.render_valid_lens_passthrough",
          _seen.get("lens") == 35.0
          and _seen.get("custom_location") == (1.0, 2.0, 3.0),
          str(_seen))
finally:
    VC.render_angle = _orig_render
    if os.path.exists(_png):
        os.remove(_png)

# ================================================== 3. B5 move_to tokens
wipe()
add_mesh("Mv", (0, 0, 0.2))
_before = loc_of("Mv")
expect_error("s18_3a.move_to_unknown_reference",
             lambda: AP.apply_mutation(
                 {"op": "move_to", "id": "Mv", "target": [1, 0, 0.2],
                  "reference": "middle"}),
             "reference", "middle", "bottom-center")
check("s18_3b.move_to_refused_scene_unchanged", loc_of("Mv") == _before,
      str(loc_of("Mv")))
_, out = capture(lambda: AP.apply_mutation(
    {"op": "move_to", "id": "Mv", "target": [1, 0, 0.2],
     "reference": "origin"}))
check("s18_3c.move_to_origin_token_works",
      AP._LAST_REPORTS["move_to"]["reference"] == "origin"
      and abs(bpy.data.objects["Mv"].location.x - 1.0) < 1e-5,
      str(AP._LAST_REPORTS["move_to"])[:160])
_, out = capture(lambda: AP.apply_mutation(
    {"op": "move_to", "id": "Mv", "target": [1, 0, 0.5]}))
check("s18_3d.move_to_default_bottom_center",
      AP._LAST_REPORTS["move_to"]["reference"] == "bottom-center")

# ==================================================== 4. B6 audit scope
wipe()
add_plane("Ground")
add_mesh("SObj", (0, 0, 0.2))
expect_error("s18_4a.audit_unknown_scope_refused",
             lambda: AP.apply_mutation({"op": "audit", "id": "NopeScope"}),
             "scope id 'NopeScope'", "not found")
_, out = capture(lambda: AP.apply_mutation(
    {"op": "audit", "pairs": ["Ground,SObj"], "id": "SObj"}))
check("s18_4b.audit_valid_scope_runs",
      AP._LAST_REPORTS["audit"]["pairs_checked"] == 1
      and AP._LAST_REPORTS["audit"]["failed"] is False,
      str(AP._LAST_REPORTS["audit"])[:160])

# ================================== 5. B11 heat_bake / seam_views / color
wipe()
add_plane("Ground")
add_mesh("Hot", (0, 0, 0.2))
expect_error("s18_5a.heat_others_string_refused",
             lambda: AP.apply_mutation(
                 {"op": "heat_bake", "id": "Hot", "others": "Ground"}),
             "others", "list")
expect_error("s18_5b.heat_others_nonname_entry",
             lambda: AP.apply_mutation(
                 {"op": "heat_bake", "id": "Hot", "others": [7]}),
             "others", "strings")
_, out = capture(lambda: AP.apply_mutation(
    {"op": "heat_bake", "id": "Hot", "others": ["Ground"]}))
check("s18_5c.heat_bake_valid_runs",
      "bands" in AP._LAST_REPORTS.get("heat_bake", {}), out[-160:])

bpy.ops.object.camera_add(location=(3, -3, 2))
bpy.context.scene.camera = bpy.context.active_object
_seam_dir = os.path.join(_TMP, "seam")
expect_error("s18_5d.seam_res_string",
             lambda: AP.apply_mutation(
                 {"op": "seam_views", "a": "Hot", "b": "Ground",
                  "out_dir": _seam_dir, "res": "640x360"}),
             "res", "per-character")
expect_error("s18_5e.seam_res_len1",
             lambda: AP.apply_mutation(
                 {"op": "seam_views", "a": "Hot", "b": "Ground",
                  "out_dir": _seam_dir, "res": [640]}),
             "res")
expect_error("s18_5f.seam_res_fraction",
             lambda: AP.apply_mutation(
                 {"op": "seam_views", "a": "Hot", "b": "Ground",
                  "out_dir": _seam_dir, "res": [640.5, 360]}),
             "res")
expect_error("s18_5g.seam_res_zero",
             lambda: AP.apply_mutation(
                 {"op": "seam_views", "a": "Hot", "b": "Ground",
                  "out_dir": _seam_dir, "res": [0, 360]}),
             "res")
_, out = capture(lambda: AP.apply_mutation(
    {"op": "seam_views", "a": "Hot", "b": "Ground",
     "out_dir": _seam_dir, "res": [96, 54]}))
check("s18_5h.seam_res_valid_still_runs",
      len(AP._LAST_REPORTS["seam_views"]["views"]) == 4, out[-160:])

_clr = add_mesh("ClrObj", (1, 0, 0.2))
_cmat = bpy.data.materials.new("ClrMat")
_cmat.use_nodes = True
_clr.data.materials.append(_cmat)
_cbsdf = next(n for n in _cmat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
expect_error("s18_5i.color_string_refused",
             lambda: AP.apply_mutation(
                 {"op": "set_material_color", "id": "ClrObj",
                  "color": "red"}),
             "color", "[r,g,b")
_, out = capture(lambda: AP.apply_mutation(
    {"op": "set_material_color", "id": "ClrObj", "color": [0.5, 2.0, -0.3]}))
_bc = tuple(round(v, 4) for v in
            _cbsdf.inputs["Base Color"].default_value)
check("s18_5j.color_clamped_to_01",
      _bc == (0.5, 1.0, 0.0, 1.0)
      and tuple(round(v, 4) for v in _cmat.diffuse_color) == (0.5, 1.0, 0.0, 1.0),
      f"base={_bc}")
check("s18_5k.color_clamp_printed", "clamped" in out, out[-200:])
expect_error("s18_5l.color_nan_refused",
             lambda: AP.apply_mutation(
                 {"op": "set_material_color", "id": "ClrObj",
                  "color": [NAN, 0, 0]}),
             "NaN")

# ================================================= 6. B12 split_mesh
wipe()
add_mesh("Welded", (0, 0, 0.2))
_REGION = {"min": [-0.25, -0.25, -0.5], "max": [0.25, 0.25, 0.05]}
expect_error("s18_6a.split_dryrun_ack_refused",
             lambda: AP.apply_mutation(
                 {"op": "split_mesh", "id": "Welded", "mode": "dry-run",
                  "ack_risks": True}),
             "dry-run", "ack_risks", "valid params")
expect_error("s18_6b.split_region_ackmany_refused",
             lambda: AP.apply_mutation(
                 {"op": "split_mesh", "id": "Welded", "mode": "split-region",
                  "region": _REGION, "ack_many_parts": True}),
             "split-region", "ack_many_parts")
expect_error("s18_6c.split_split_newid_refused",
             lambda: AP.apply_mutation(
                 {"op": "split_mesh", "id": "Welded", "mode": "split",
                  "new_id": "Nope"}),
             "'split'", "new_id")
_, out = capture(lambda: AP.apply_mutation(
    {"op": "split_mesh", "id": "Welded", "mode": "dry-run"}))
check("s18_6d.split_dryrun_still_runs", "DRY-RUN" in out, out[-160:])
_, out = capture(lambda: AP.apply_mutation(
    {"op": "split_mesh", "id": "Welded", "mode": "dry-run",
     "region": _REGION}))
check("s18_6e.split_region_dryrun_still_runs",
      "REGION DRY-RUN" in out, out[-160:])
_, out = capture(lambda: AP.apply_mutation(
    {"op": "split_mesh", "id": "Welded", "mode": "split-region",
     "region": _REGION, "new_id": "WeldedCut", "ack_risks": True}))
check("s18_6f.split_region_valid_combo_runs",
      bpy.data.objects.get("WeldedCut") is not None
      and "does not take param" not in out, out[-200:])
expect_error("s18_6g.split_bad_mode_refused",
             lambda: AP.apply_mutation(
                 {"op": "split_mesh", "id": "Welded", "mode": "bogus"}),
             "mode must be dry-run|split|split-region")

# ============================ 7. B3 SystemExit chain-abort save (main())
blend1 = os.path.join(_TMP, "aborted.blend")
_orig_gate = AP._PP.gate


def _boom(**kw):
    raise SystemExit(2)   # physics_place.gate fail_hard contract


_old_argv = sys.argv
try:
    AP._PP.gate = _boom
    sys.argv = ["blender", "--", "--patch-json", json.dumps(
        {"mutations": [
            {"op": "add_cube", "id": "AbortCube"},
            {"op": "physics_gate", "fail_hard": True}]}),
        "--save-blend", blend1]
    _err = io.StringIO()
    _code = None
    try:
        with redirect_stdout(io.StringIO()), redirect_stderr(_err):
            AP.main()
        check("s18_7a.systemexit_propagates", False, "no SystemExit raised")
    except SystemExit as e:
        _code = e.code
    check("s18_7b.exit_code_2_preserved", _code == 2, f"code={_code}")
    check("s18_7c.chain_abort_blend_saved", os.path.isfile(blend1),
          f"{blend1} missing")
    _errtxt = _err.getvalue()
    check("s18_7d.chain_abort_message",
          "CHAIN ABORTED at mutation 2/2" in _errtxt
          and "SystemExit(2)" in _errtxt, _errtxt[-240:])

    # regression guard: the plain-Exception abort path still exits 1 + saves
    blend2 = os.path.join(_TMP, "aborted_exc.blend")
    sys.argv = ["blender", "--", "--patch-json", json.dumps(
        {"mutations": [
            {"op": "add_cube", "id": "AbortCube2"},
            {"op": "set_location", "id": "Nope", "location": [0, 0, 0]}]}),
        "--save-blend", blend2]
    _err2 = io.StringIO()
    _code2 = None
    try:
        with redirect_stdout(io.StringIO()), redirect_stderr(_err2):
            AP.main()
    except SystemExit as e:
        _code2 = e.code
    check("s18_7e.exception_path_exit1_and_saves",
          _code2 == 1 and os.path.isfile(blend2)
          and "CHAIN ABORTED at mutation 2/2" in _err2.getvalue(),
          f"code={_code2} err={_err2.getvalue()[-160:]}")
finally:
    sys.argv = _old_argv
    AP._PP.gate = _orig_gate
    AP._PHYSICS_FAILURES.clear()

# the saved state must carry the PRE-abort op's work (not an empty file)
bpy.ops.wm.open_mainfile(filepath=blend1)
check("s18_7f.saved_blend_has_pre_abort_state",
      bpy.data.objects.get("AbortCube") is not None,
      str([o.name for o in bpy.data.objects]))

# ============================= 8. B8 schema dof + exposure via --export
wipe()
bpy.ops.object.camera_add(location=(4, -4, 3))
bpy.context.active_object.name = "Cam"
add_plane("Floor")
blend3 = os.path.join(_TMP, "dof_scene.blend")
bpy.ops.wm.save_as_mainfile(filepath=blend3)
_schema_path = os.path.join(_TMP, "schema.json")
_old_argv = sys.argv
try:
    sys.argv = ["blender", "--", "--patch-json", json.dumps({
        "load_blend": blend3,
        "mutations": [
            {"op": "set_camera_dof", "id": "Cam",
             "focus_distance": 2.5, "aperture_fstop": 2.8},
            {"op": "set_exposure", "exposure": 0.7}]}),
        "--export-schema", _schema_path]
    with redirect_stdout(io.StringIO()):
        AP.main()
finally:
    sys.argv = _old_argv
schema = json.load(open(_schema_path))
cam_ent = next(e for e in schema["objects"] if e["id"] == "Cam")
dof = cam_ent.get("camera", {}).get("dof")
check("s18_8a.schema_dof_block",
      dof == {"use_dof": True, "focus_distance": 2.5, "aperture_fstop": 2.8},
      str(dof))
check("s18_8b.schema_exposure",
      schema.get("exposure") == 0.7, str(schema.get("exposure")))
check("s18_8c.schema_dof_plain_shapes",
      isinstance(dof.get("use_dof"), bool)
      and isinstance(dof.get("focus_distance"), float)
      and isinstance(dof.get("aperture_fstop"), float)
      and isinstance(schema.get("exposure"), float),
      str({k: type(v).__name__ for k, v in (dof or {}).items()}))

# ============== 9. B10 validate_scene bare animate(ctx) module dispatch
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX_BARE = "_s18_bare_animate_fixture"
FIX_SENT = "_s18_sentinel_animate_fixture"

BARE_SRC = '''"""s18 Wave-B fixture (DELETED by tests/test_s18_wave_b.py):
BARE `def animate(ctx)` — the validate_scene B10 contract (a bare module
must dispatch, not TypeError before any check runs)."""
import bpy

ANIMATE_CALLS = []


def build_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.mesh.primitive_plane_add(size=4, location=(0, 0, 0))
    bpy.context.active_object.name = "Floor"
    bpy.ops.mesh.primitive_cube_add(size=0.4, location=(0, 0, 0.2))
    bpy.context.active_object.name = "Box"
    return {"fixture": "s18-bare"}


def animate(ctx):            # BARE signature — no start_frame/n_frames
    ANIMATE_CALLS.append(("bare", dict(ctx)))
'''

SENT_SRC = '''"""s18 Wave-B fixture (DELETED by tests/test_s18_wave_b.py):
SENTINEL `def animate(ctx, *, start_frame, n_frames)` — the twin B10
contract (sentinel modules must still receive the frame kwargs)."""
import bpy

ANIMATE_CALLS = []


def build_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.mesh.primitive_plane_add(size=4, location=(0, 0, 0))
    bpy.context.active_object.name = "Floor"
    bpy.ops.mesh.primitive_cube_add(size=0.4, location=(0, 0, 0.2))
    bpy.context.active_object.name = "Box"
    return {"fixture": "s18-sentinel"}


def animate(ctx, *, start_frame=None, n_frames=None):
    ANIMATE_CALLS.append(("sentinel", start_frame, n_frames))
'''

_old_dwb = sys.dont_write_bytecode
sys.dont_write_bytecode = True   # no _s18_*.pyc leaks into scripts/__pycache__
_written = []
try:
    for _name, _src in ((FIX_BARE, BARE_SRC), (FIX_SENT, SENT_SRC)):
        _p = os.path.join(REPO, "scripts", _name + ".py")
        with open(_p, "w") as f:
            f.write(_src)
        _written.append(_p)

    _out1 = os.path.join(_TMP, "val_bare.json")
    _old_argv = sys.argv
    try:
        sys.argv = ["blender", "--", "--scene", FIX_BARE,
                    "--output", _out1]
        try:
            with redirect_stdout(io.StringIO()):
                VS.main()
            check("s18_9a.bare_animate_module_dispatches", True)
        except Exception as e:
            check("s18_9a.bare_animate_module_dispatches", False,
                  f"{type(e).__name__}: {e}")
    finally:
        sys.argv = _old_argv

    check("s18_9b.bare_report_written",
          os.path.isfile(_out1)
          and "issues_count" in json.load(open(_out1)))
    import importlib as _il
    _fmod = _il.import_module(FIX_BARE)
    check("s18_9c.fixture_animate_called_bare",
          len(_fmod.ANIMATE_CALLS) == 1
          and _fmod.ANIMATE_CALLS[0][0] == "bare",
          str(_fmod.ANIMATE_CALLS))

    _out2 = os.path.join(_TMP, "val_sentinel.json")
    _old_argv = sys.argv
    try:
        sys.argv = ["blender", "--", "--scene", FIX_SENT,
                    "--output", _out2, "--frames", "13"]
        try:
            with redirect_stdout(io.StringIO()):
                VS.main()
            check("s18_9d.sentinel_module_dispatches", True)
        except Exception as e:
            check("s18_9d.sentinel_module_dispatches", False,
                  f"{type(e).__name__}: {e}")
    finally:
        sys.argv = _old_argv
    _smod = _il.import_module(FIX_SENT)
    check("s18_9e.sentinel_gets_start_and_frames",
          _smod.ANIMATE_CALLS == [("sentinel", 1, 13)],
          str(_smod.ANIMATE_CALLS))
finally:
    sys.dont_write_bytecode = _old_dwb
    for _p in _written:
        try:
            os.remove(_p)
        except OSError:
            pass
    _pycache = os.path.join(REPO, "scripts", "__pycache__")
    if os.path.isdir(_pycache):
        for _f in os.listdir(_pycache):
            if _f.startswith("_s18_") and _f.endswith(".pyc"):
                try:
                    os.remove(os.path.join(_pycache, _f))
                except OSError:
                    pass
check("s18_9f.fixture_files_cleaned",
      not any(os.path.exists(p) for p in _written),
      str([p for p in _written if os.path.exists(p)]))

shutil.rmtree(_TMP, ignore_errors=True)

# ================================================================== end
print("=" * 60)
print(f"test_s18_wave_b: {len(PASS) - len(FAIL)}/{len(PASS) + len(FAIL)} checks passed")
if FAIL:
    print(f"[test_s18b] FAILED: {FAIL}")
    print("[test_s18b] RESULT: FAIL")
    sys.exit(1)
print("[test_s18b] ALL PASS")
sys.exit(0)
