# test_s17_wave_b.py — session-17 Wave-B fix regressions (in-Blender).
#
# Covers the 2b mutation-surface audit fixes assigned to Wave B:
#   1. F2B-10/1/7/11/27: PARAM_DOCS <-> handler key parity (AST check,
#      pure stdlib, works in Blender) + _doc_keys tokenizer + warning
#      behavior (applied params never warn, junk still warns).
#   2. F2B-14: needs_obj ops without id -> clean "requires key 'id'"
#      RuntimeError naming the op (the old dispatcher guard was dead).
#   3. F2B-15: audit pairs / place_on supports bad inputs get kit errors
#      (no raw KeyError/ValueError mislabels).
#   4. F2B-16: place_on footprint validated (bottom|all|grid); the
#      kb-documented 'inset' token gets a hint instead of silent verts.
#   5. F2B-12: snap_z reference 'centroid' aliases 'center' (report
#      carries the effective token); unknown tokens list valid ones.
#   6. F2B-25: seat_at with a typo'd seat_mesh raises; without seat_mesh
#      the print says OK(unverified).
#   7. F2B-19: physics_gate REJECTED reaches _PHYSICS_FAILURES (the
#      --fail-on-physics-failure exit-3 contract).
#   8. F2B-23: physics_settle objs:[] refused; omitted objs -> whole-scene
#      warning printed to STDOUT, not just the report JSON.
#   9. F2B-24: bare `def animate(ctx)` scene modules dispatch (exporter
#      contract), sentinel signatures still get start_frame/n_frames.
#  10. F2B-26: cheap guards — list-root patch, missing load_blend file,
#      DoF shortcut alone, render_viewport samples/width/height/target.
#  11. F2B-9: read-only fcurve consumers use iter_all_fcurves (guard
#      detection + safe keyframe rebase).
#  12. F2B-18: seam_views leaves no SeamCam object/data behind.
#  13. F2B-20/21: scene_schema exports kit props / hide_render /
#      modifiers / real world content; view_layer.update() freshness;
#      Principled matched by node TYPE.
#  14. F2A-4: annotation mesh datablocks purged (zero residue).
#  15. F2B-30: clear_bvh_cache() clears _POLY_CACHE too.
#  16. F2B-28: semantic_lib availability hint appends "…" only when
#      truncating.
#  17. F2A-11: --angles help no longer claims 'ring:N'.
#
# Run: ./scripts/blrun.sh --background --python tests/test_s17_wave_b.py
# Convention: prints [test_s17b] per check; "ALL PASS" at the end.

import inspect
import io
import os
import sys
from contextlib import redirect_stdout, redirect_stderr

import bpy

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "scripts"))

import apply_patch as AP             # noqa: E402
import placement_lib as PL           # noqa: E402
import annotate as AN                # noqa: E402
import scene_schema as SS            # noqa: E402
import semantic_lib as SL            # noqa: E402

PASS = []
FAIL = []


def check(name, cond, detail=""):
    tag = "ok" if cond else "FAIL"
    print(f"[test_s17b] {name}: {tag}" + (f" — {detail}" if detail and not cond else ""))
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


# ============================================================== 1. parity
def _walk_no_nested(node):
    """Descendants of node WITHOUT entering nested function scopes."""
    stack = list(__import__("ast").iter_child_nodes(node))
    out = []
    while stack:
        n = stack.pop()
        if isinstance(n, (__import__("ast").FunctionDef,
                          __import__("ast").AsyncFunctionDef,
                          __import__("ast").Lambda)):
            continue
        out.append(n)
        stack.extend(__import__("ast").iter_child_nodes(n))
    return out


def _parity_check():
    import ast as _ast
    path = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "scripts", "apply_patch.py")
    tree = _ast.parse(open(path).read())
    top_funcs = [n for n in tree.body if isinstance(n, _ast.FunctionDef)]
    key_helpers = {"_require", "_add_num", "_add_vec", "_add_scalar_or_vec"}

    reads, calls = {}, {}
    for fn in top_funcs:
        r, c = set(), set()
        for n in _walk_no_nested(fn):
            if (isinstance(n, _ast.Subscript) and isinstance(n.value, _ast.Name)
                    and n.value.id == "params"
                    and isinstance(n.slice, _ast.Constant)
                    and isinstance(n.slice.value, str)):
                r.add(n.slice.value)
            elif (isinstance(n, _ast.Call) and isinstance(n.func, _ast.Attribute)
                  and n.func.attr == "get" and isinstance(n.func.value, _ast.Name)
                  and n.func.value.id == "params" and n.args
                  and isinstance(n.args[0], _ast.Constant)
                  and isinstance(n.args[0].value, str)):
                r.add(n.args[0].value)
            elif (isinstance(n, _ast.Call) and isinstance(n.func, _ast.Name)
                  and n.func.id in key_helpers and len(n.args) >= 2
                  and isinstance(n.args[1], _ast.Constant)
                  and isinstance(n.args[1].value, str)):
                r.add(n.args[1].value)
            if isinstance(n, _ast.Call) and isinstance(n.func, _ast.Name):
                c.add(n.func.id)
        reads[fn.name] = r
        calls[fn.name] = c
    known = set(reads)

    def eff(name, seen=None):
        seen = seen or set()
        if name in seen or name not in known:
            return set()
        seen.add(name)
        out = set(reads[name])
        for callee in calls[name]:
            out |= eff(callee, seen)
        return out

    bad = []
    for op, (fn, _needs) in AP.MUTATIONS.items():
        doc = AP._doc_keys(op) - {"op", "id"}
        got = eff(fn.__name__) - {"op", "id"}
        for miss in doc - got:
            bad.append(f"{op}: documented '{miss}' never read by {fn.__name__}")
        for extra in got - doc:
            bad.append(f"{op}: {fn.__name__} reads '{extra}' not in PARAM_DOCS")
    check("s17_1a.paramdocs_handler_parity", not bad, "; ".join(bad[:6]))

    # tokenizer sanity: parenthesized detail must not spawn junk keys
    dk = AP._doc_keys("set_camera_dof")
    check("s17_1b.dockeys_no_paren_junk",
          "focus_distance" in dk and "focus_distance(m)" not in dk, str(sorted(dk)))
    dk2 = AP._doc_keys("label_objects")
    check("s17_1c.dockeys_depth0_commas",
          "labels" in dk2 and not any(k.startswith("{") for k in dk2),
          str(sorted(dk2)))


_parity_check()

# ================================== 2. F2B-10 warning behavior (live ops)
wipe()
add_mesh("CubeA", (0, 0, 0.2))
_, out = capture(lambda: AP.apply_mutation(
    {"op": "duplicate_object", "id": "CubeA", "new_id": "CubeA2",
     "location": [2, 0, 0.2]}))
check("s17_2a.applied_param_no_warn",
      "unknown param" not in out and bpy.data.objects.get("CubeA2"),
      out[-200:])
_, out = capture(lambda: AP.apply_mutation(
    {"op": "move_to", "id": "CubeA", "target": [0, 0, 0.2],
     "refrence": "origin"}))  # deliberate typo
check("s17_2b.truly_unknown_still_warns",
      "unknown param" in out and "refrence" in out, out[-200:])
_, out = capture(lambda: AP.apply_mutation(
    {"op": "add_torus", "id": "Torus1", "major_radius": 0.4,
     "minor_radius": 0.1}))
check("s17_2c.torus_docs_names_no_warn", "unknown param" not in out, out[-200:])
expect_error("s17_2d.torus_old_doc_names_refused",
             lambda: AP.apply_mutation(
                 {"op": "add_torus", "id": "Torus2",
                  "radius_major": 0.4, "radius_minor": 0.1}),
             "radius_major")

# ============================================================ 3. F2B-14
wipe()
msg = expect_error("s17_3a.missing_id_clean",
                   lambda: AP.apply_mutation(
                       {"op": "set_location", "location": [0, 0, 0]}),
                   "requires key 'id'", "set_location")
add_mesh("CubeB", (0, 0, 0.2))
msg = expect_error("s17_3b.unknown_id_names_op",
                   lambda: AP.apply_mutation(
                       {"op": "set_location", "id": "Nope",
                        "location": [0, 0, 0]}),
                   "op 'set_location'", "not found")

# ============================================================ 4. F2B-15
wipe()
g = add_mesh("Ground", (0, 0, -0.2), size=2)
add_mesh("Mover", (0, 0, 0.2))
msg = expect_error("s17_4a.audit_unknown_pair_name",
                   lambda: AP.apply_mutation(
                       {"op": "audit", "pairs": ["Ground,Nope"]}),
                   "not found", "Nope")
check("s17_4b.audit_error_not_param_mislabel",
      "missing/invalid param" not in msg, msg[:200])
expect_error("s17_4c.audit_pair_three_names",
             lambda: AP.apply_mutation(
                 {"op": "audit", "pairs": ["Ground,Mover,Extra"]}),
             "A,B")
expect_error("s17_4d.audit_exclude_string",
             lambda: AP.apply_mutation(
                 {"op": "audit", "exclude": "Ground"}),
             "list")
_, out = capture(lambda: AP.apply_mutation({"op": "audit", "pairs": ["Ground,Mover"]}))
rep = AP._LAST_REPORTS["audit"]
check("s17_4e.audit_valid_pairs_runs",
      rep["pairs_checked"] == 1 and rep["failed"] is False, str(rep)[:200])
expect_error("s17_4f.place_on_supports_string",
             lambda: AP.apply_mutation(
                 {"op": "place_on", "id": "Mover", "supports": "Ground"}),
             "list")
expect_error("s17_4g.place_on_supports_empty",
             lambda: AP.apply_mutation(
                 {"op": "place_on", "id": "Mover", "supports": []}),
             "at least one support")
expect_error("s17_4h.place_on_lib_empty_supports",
             lambda: PL.place_on(bpy.data.objects["Mover"]),
             "no supports given")

# ============================================================ 5. F2B-16
expect_error("s17_5a.footprint_inset_refused",
             lambda: PL.place_on(bpy.data.objects["Mover"], g,
                                 footprint="inset"),
             "'inset'", "inset=<meters>")
expect_error("s17_5b.footprint_case_refused",
             lambda: PL.place_on(bpy.data.objects["Mover"], g,
                                 footprint="Bottom"),
             "unknown footprint")
wipe()
bpy.ops.mesh.primitive_plane_add(size=4, location=(0, 0, 0))
plane = bpy.context.active_object
plane.name = "TableTop"
add_mesh("Mug", (0.2, 0, 0.5))
_, out = capture(lambda: AP.apply_mutation(
    {"op": "place_on", "id": "Mug", "supports": ["TableTop"],
     "grid_n": 8, "inset": 0.0, "contact_band_mm": 0.1}))
rep = AP._LAST_REPORTS["place_on"]
check("s17_5c.valid_place_on_ok",
      rep.get("ok") is True and "unknown param" not in out,
      f"ok={rep.get('ok')} out={out[-160:]}")

# ============================================================ 6. F2B-12
wipe()
cube = add_mesh("SnapCube", (0, 0, 2.0))
_, out = capture(lambda: AP.apply_mutation(
    {"op": "snap_z", "id": "SnapCube", "target_z": 0.5,
     "reference": "centroid"}))
rep = AP._LAST_REPORTS["snap_z"]
check("s17_6a.snapz_centroid_alias",
      rep["reference"] == "center" and rep.get("reference_requested") == "centroid",
      str(rep)[:160])
check("s17_6b.snapz_centroid_lands",
      abs(rep["result_z"] - 0.5) < 1e-4, f"result_z={rep['result_z']}")
_, out = capture(lambda: AP.apply_mutation(
    {"op": "snap_z", "id": "SnapCube", "target_z": 0.5, "reference": "center"}))
check("s17_6c.snapz_center_still_works",
      AP._LAST_REPORTS["snap_z"]["reference"] == "center")
expect_error("s17_6d.snapz_unknown_ref",
             lambda: PL.snap_z(cube, 0.5, reference="middle"),
             "middle", "bottom", "centroid")

# ============================================================ 7. F2B-25
wipe()
bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0, 0, 1))
bpy.context.active_object.name = "SeatAnchor"
add_mesh("SeatMesh", (0, 0, 1.0), size=0.6)   # cushion wider than the figure
add_mesh("Figure", (0, 0, 2.5))               # size 0.4: bottom face strictly
                                              # inside the cushion footprint
expect_error("s17_7a.seat_mesh_typo_raises",
             lambda: AP.apply_mutation(
                 {"op": "seat_at", "id": "Figure", "seat": "SeatAnchor",
                  "seat_mesh": "NopeCushion"}),
             "NopeCushion", "not found")
_, out = capture(lambda: AP.apply_mutation(
    {"op": "seat_at", "id": "Figure", "seat": "SeatAnchor"}))
check("s17_7b.seat_unverified_print",
      "OK(unverified" in out, out[-200:])
check("s17_7c.seat_unverified_no_ok_key", "ok" not in AP._LAST_REPORTS["seat_at"],
      str(AP._LAST_REPORTS["seat_at"].get("ok")))
_, out = capture(lambda: AP.apply_mutation(
    {"op": "seat_at", "id": "Figure", "seat": "SeatAnchor",
     "seat_mesh": "SeatMesh"}))
rep = AP._LAST_REPORTS["seat_at"]
check("s17_7d.seat_verified_penetrating_flags",
      rep.get("ok") is False and "CONTACT-ISSUES" in out,
      f"ok={rep.get('ok')} out={out[-160:]}")

# ============================================================ 8. F2B-19
_orig_gate = AP._PP.gate
try:
    AP._PP.gate = lambda **kw: {"op": "physics_gate", "verdict": "REJECTED",
                                "ok": False, "fix_queue": [{"note": "n"}]}
    AP._PHYSICS_FAILURES.clear()
    _, out = capture(lambda: AP.apply_mutation({"op": "physics_gate"}))
    check("s17_8a.gate_rejected_fails_flag",
          len(AP._PHYSICS_FAILURES) == 1 and "PHYSICS-OP-FAILED" in out,
          f"failures={AP._PHYSICS_FAILURES} out={out[-160:]}")
    AP._PP.gate = lambda **kw: {"op": "physics_gate", "verdict": "PASS",
                                "ok": True, "fix_queue": []}
    AP._PHYSICS_FAILURES.clear()
    _, out = capture(lambda: AP.apply_mutation({"op": "physics_gate"}))
    check("s17_8b.gate_pass_no_failure",
          AP._PHYSICS_FAILURES == [], str(AP._PHYSICS_FAILURES))
finally:
    AP._PP.gate = _orig_gate
    AP._PHYSICS_FAILURES.clear()

# ============================================================ 9. F2B-23
_orig_settle = AP._PP.settle
try:
    AP._PP.settle = lambda **kw: {"op": "physics_settle", "verdict": "PASS",
                                  "ok": True, "objects": []}
    expect_error("s17_9a.settle_empty_objs_refused",
                 lambda: AP.apply_mutation({"op": "physics_settle",
                                            "objs": []}),
                 "objs=[]", "at least one mover")
    captured_kwargs = {}
    def _spy(**kw):
        captured_kwargs.update(kw)
        return {"op": "physics_settle", "verdict": "PASS", "ok": True,
                "objects": [],
                "whole_scene_warning": "WHOLE-SCENE-SETTLE-WARNING"}
    AP._PP.settle = _spy
    _, out = capture(lambda: AP.apply_mutation({"op": "physics_settle"}))
    check("s17_9b.settle_omitted_objs_whole_scene",
          captured_kwargs.get("objs") is None, str(captured_kwargs.get("objs")))
    check("s17_9c.settle_whole_scene_warning_on_stdout",
          "WHOLE-SCENE-SETTLE-WARNING" in out, out[-200:])
finally:
    AP._PP.settle = _orig_settle

# =========================================================== 10. F2B-24
wipe()
calls_log = []


class _ModBare:
    @staticmethod
    def animate(ctx):
        calls_log.append(("bare", ctx))


class _ModSentinel:
    @staticmethod
    def animate(ctx, *, start_frame=1, n_frames=None):
        calls_log.append(("sentinel", ctx, start_frame, n_frames))


AP._animate_scene_module(_ModBare, {"who": "bare"}, frames=24)
AP._animate_scene_module(_ModSentinel, {"who": "sentinel"}, frames=13)
check("s17_10a.bare_animate_dispatch",
      calls_log[0] == ("bare", {"who": "bare"}), str(calls_log))
check("s17_10b.sentinel_animate_dispatch",
      calls_log[1] == ("sentinel", {"who": "sentinel"}, 1, 13), str(calls_log))


class _ModBroken:
    @staticmethod
    def animate(ctx, *, start_frame, n_frames):
        raise TypeError("INSIDE-ANIMATE")


try:
    AP._animate_scene_module(_ModBroken, {}, frames=5)
    check("s17_10c.animate_body_typeerror_propagates", False, "no error")
except TypeError as e:
    check("s17_10c.animate_body_typeerror_propagates", "INSIDE-ANIMATE" in str(e),
          str(e))

# =========================================================== 11. F2B-26
wipe()


class _Args:
    def __init__(self, **kw):
        self.patch = kw.get("patch")
        self.patch_json = kw.get("patch_json")


try:
    AP._read_patch(_Args(patch_json="[1,2,3]"))
    check("s17_11a.list_root_refused", False, "no SystemExit")
except SystemExit as e:
    check("s17_11a.list_root_refused", e.code == 1, f"code={e.code}")
p = AP._read_patch(_Args(patch_json='{"mutations": []}'))
check("s17_11b.valid_patch_parses", isinstance(p, dict) and "mutations" in p)

expect_error("s17_11c.render_width_refused",
             lambda: AP.apply_mutation(
                 {"op": "render_viewport", "output": "/tmp/_s17b_x.png",
                  "width": -5}),
             "positive integer")
expect_error("s17_11d.render_target_string_refused",
             lambda: AP.apply_mutation(
                 {"op": "render_viewport", "output": "/tmp/_s17b_x.png",
                  "target": "1,2,3"}),
             "[x,y,z]")

# main()-level guards via doctored sys.argv (script_argv reads after "--")
_old_argv = sys.argv
try:
    sys.argv = ["blender", "--", "--focus-distance", "2.5"]
    err = io.StringIO()
    try:
        with redirect_stderr(err):
            AP.main()
        check("s17_11e.dof_shortcut_alone_refused", False, "no SystemExit")
    except SystemExit as e:
        check("s17_11e.dof_shortcut_alone_refused",
              e.code == 1 and "load_blend" in err.getvalue(),
              f"code={e.code} err={err.getvalue()[:160]}")

    sys.argv = ["blender", "--", "--patch-json",
                '{"load_blend": "/tmp/_s17b_missing.blend"}']
    err = io.StringIO()
    try:
        with redirect_stderr(err):
            AP.main()
        check("s17_11f.missing_blend_refused", False, "no SystemExit")
    except SystemExit as e:
        check("s17_11f.missing_blend_refused",
              e.code == 1 and "not found" in err.getvalue(),
              f"code={e.code} err={err.getvalue()[:160]}")
finally:
    sys.argv = _old_argv

# =========================================================== 12. F2B-9
wipe()
cube = add_mesh("AnimCube", (0, 0, 0.2))
cube.keyframe_insert(data_path="location", frame=1)
cube.keyframe_insert(data_path="location", frame=10)
chans = PL._location_anim_channels(cube)
check("s17_12a.guard_sees_location_keys",
      any("action:location" in c for c in chans), str(chans))
ad = cube.animation_data
kp0 = [kp.co.y for fc in PL.iter_all_fcurves(ad.action)
       if fc.data_path == "location" and fc.array_index == 0
       for kp in fc.keyframe_points]
n, touched = PL._rebase_location_keys(cube, (1.0, 0.0, 0.0))
kp1 = [kp.co.y for fc in PL.iter_all_fcurves(ad.action)
       if fc.data_path == "location" and fc.array_index == 0
       for kp in fc.keyframe_points]
check("s17_12b.rebase_shifts_keys",
      n == 2 and len(kp1) == 2 and abs((kp1[0] - kp0[0]) - 1.0) < 1e-6,
      f"n={n} before={kp0} after={kp1}")
try:
    from blender_kit import iter_all_fcurves as _bk_iafc
    check("s17_12c.pl_uses_blenderkit_iter_all",
          PL.iter_all_fcurves is _bk_iafc)
except ImportError:
    check("s17_12c.pl_uses_blenderkit_iter_all", True, "(blender_kit absent)")

# ========================================================== 13. F2B-18
wipe()
a = add_mesh("SeamA", (0, 0, 0.2))
b = add_mesh("SeamB", (0.1, 0, 0.2))
bpy.ops.object.camera_add(location=(3, -3, 2))
real_cam = bpy.context.active_object
real_cam.name = "RealCam"
bpy.context.scene.camera = real_cam
import tempfile
tmp = tempfile.mkdtemp(prefix="s17b_seam_")
rep, _ = capture(lambda: PL.seam_views(a, b, out_dir=tmp, res=(128, 72)))
check("s17_13a.seam_views_ran",
      len(rep.get("views", {})) == 4, str(rep.get("views")))
check("s17_13b.no_seamcam_object",
      not any(o.name.startswith("SeamCam") for o in bpy.data.objects),
      str([o.name for o in bpy.data.objects]))
check("s17_13c.no_seamcam_data",
      not any(c.name.startswith("SeamCam") for c in bpy.data.cameras),
      str([c.name for c in bpy.data.cameras]))
check("s17_13d.scene_camera_restored",
      bpy.context.scene.camera is not None
      and bpy.context.scene.camera.name == "RealCam",
      str(bpy.context.scene.camera))

# ========================================================== 14. F2A-4
wipe()
cube = add_mesh("TestCube", (0, 0, 0.2))
layer = AN.build_annotation_layer(flagged_ids=["TestCube"],
                                  label_ids=[("TestCube", 1)],
                                  grid=True, gnomon=True)
n_meshes = sum(1 for m in bpy.data.meshes if m.name.startswith("KIT_ANNOT_"))
check("s17_14a.annot_meshes_created", n_meshes >= 15, f"{n_meshes} meshes")
AN.delete_annotation_layer(layer)
res = {
    "objects": [o.name for o in bpy.data.objects if o.name.startswith("KIT_ANNOT_")],
    "meshes": [m.name for m in bpy.data.meshes if m.name.startswith("KIT_ANNOT_")],
    "mats": [m.name for m in bpy.data.materials if m.name.startswith("KIT_ANNOT_")],
    "curves": [c.name for c in bpy.data.curves if c.name.startswith("KIT_ANNOT_")],
}
check("s17_14b.annot_zero_mesh_residue", not res["meshes"], str(res["meshes"][:4]))
check("s17_14c.annot_zero_all_residue",
      not any(res.values()), str({k: v[:2] for k, v in res.items() if v}))

# ====================================================== 15. F2B-20/21
wipe()
bpy.ops.mesh.primitive_plane_add(size=4, location=(0, 0, 0))
bpy.context.active_object.name = "Floor"
cube = add_mesh("Labeled", (0, 0, 0.2))
cube["kit_label"] = "mug"
cube["kit_label_conf"] = 0.9
cube["kit_semantic"] = 1
mod = cube.modifiers.new("BevelMe", 'BEVEL')
hidden = add_mesh("HiddenProp", (2, 0, 0.2))
hidden.hide_render = True
mat = bpy.data.materials.new("RenamedBSDFMat")
try:
    mat.use_nodes = True
except Exception:
    pass
bsdf = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'),
            None)
bsdf.name = "RenamedBSDF"          # F2B-20e: type match must survive rename
bsdf.inputs["Base Color"].default_value = (0.1, 0.2, 0.3, 1.0)
cube.data.materials.append(mat)
from blender_kit import add_sky_world  # READ-ONLY use of the kit helper
add_sky_world(sun_elevation_deg=30, strength=1.0)
# F2B-21: mutate then export IMMEDIATELY — the schema must reflect the new
# matrix_world without a manual view_layer.update() here.
cube.location = (5.0, 0.0, 0.0)
schema = SS.export_scene_schema()
ent = next(e for e in schema["objects"] if e["id"] == "Labeled")
check("s17_15a.schema_kit_props",
      ent.get("kit_props", {}).get("kit_label") == "mug"
      and ent["kit_props"].get("kit_label_conf") == 0.9,
      str(ent.get("kit_props")))
check("s17_15b.schema_modifiers",
      any(m["type"] == 'BEVEL' for m in ent.get("modifiers", [])),
      str(ent.get("modifiers")))
check("s17_15c.schema_hide_render",
      ent.get("hide_render") is False
      and next(e for e in schema["objects"]
               if e["id"] == "HiddenProp")["hide_render"] is True)
check("s17_15d.schema_renamed_bsdf_color",
      ent["materials"][0]["color"] == [0.1, 0.2, 0.3, 1.0],
      str(ent["materials"][0]))
check("s17_15e.schema_world_sky",
      schema["world"] is not None
      and schema["world"].get("color_source", {}).get("type") == 'TEX_SKY'
      and "background_strength" in schema["world"],
      str(schema["world"])[:200])
check("s17_15f.schema_matrix_fresh",
      abs(ent["matrix_world"][0][3] - 5.0) < 1e-4,
      f"matrix tx={ent['matrix_world'][0][3]}")
check("s17_15g.schema_version_bumped", schema["schema_version"] == "1.1",
      schema["schema_version"])

# ========================================================== 16. F2B-30
wipe()
cube = add_mesh("CacheCube", (0, 0, 0.2))
PL.world_bvh(cube)
PL._polys_world(cube)
check("s17_16a.caches_populated",
      len(PL._BVH_CACHE) > 0 and len(PL._POLY_CACHE) > 0,
      f"bvh={len(PL._BVH_CACHE)} poly={len(PL._POLY_CACHE)}")
PL.clear_bvh_cache()
check("s17_16b.clear_clears_both",
      len(PL._BVH_CACHE) == 0 and len(PL._POLY_CACHE) == 0,
      f"bvh={len(PL._BVH_CACHE)} poly={len(PL._POLY_CACHE)}")

# ========================================================== 17. F2B-28
wipe()
add_mesh("ObjA", (0, 0, 0))
add_mesh("ObjB", (1, 0, 0))
try:
    SL._validate_batch({"Ghost": "label"})
    check("s17_17a.hint_no_ellipsis_small_scene", False, "no error")
except RuntimeError as e:
    check("s17_17a.hint_no_ellipsis_small_scene",
          "…" not in str(e) and "ObjA" in str(e), str(e)[:200])
for i in range(20):
    e = bpy.data.objects.new(f"Filler{i:02d}", None)
    bpy.context.collection.objects.link(e)
try:
    SL._validate_batch({"Ghost": "label"})
    check("s17_17b.hint_ellipsis_big_scene", False, "no error")
except RuntimeError as e:
    check("s17_17b.hint_ellipsis_big_scene",
          "…" in str(e), str(e)[:200])

# ========================================================== 18. F2A-11
import viewport_capture as VC
src = inspect.getsource(VC)
check("s17_18a.angles_help_no_ringN", "Or 'ring:N' for N cameras" not in src,
      "--angles help still claims 'ring:N' support")
check("s17_18b.angles_help_points_to_ring_flag",
      "--ring" in src, "help no longer mentions --ring")

# ================================================================== end
print("=" * 60)
print(f"test_s17_wave_b: {len(PASS) - len(FAIL)}/{len(PASS) + len(FAIL)} checks passed")
if FAIL:
    print(f"[test_s17b] FAILED: {FAIL}")
    print("[test_s17b] RESULT: FAIL")
    sys.exit(1)
print("[test_s17b] ALL PASS")
sys.exit(0)
