"""test_t6_add_ops.py — T6 regression: Track I add-primitive patch ops.

Locks the design-gate corrections (fresh-context audit + live 4.5.13
probes, kit worklog Task 2):
  - size params are FINAL world dims, data-baked, scale stays (1,1,1)
  - self-verify runs BEFORE rotation (oriented AABB would lie)
  - chord-aware tolerance for polygonal radial kinds
  - fail-closed: name collision (no silent .001), NaN/Infinity, bool,
    zero/negative, unknown keys — scene unchanged on refusal
  - material contract: use_nodes + Principled Base Color AND
    diffuse_color (gotcha #56), get-or-create (no .001 leak)
  - composition: add -> place_on / physics_place / seat_at / schema
  - rider: physics ops refuse non-mesh movers honestly (no AttributeError)

Runs INSIDE Blender via run.sh (T5 harness style: one process, factory
settings between scenes, check()/FAIL, results JSON).
"""
import sys, os, json, math, subprocess

_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS = os.path.abspath(os.path.join(_HERE, "..", "scripts"))
_LAB_LIB = os.path.join(os.environ.get("PLACEMENT_LAB", "/home/z/placement-lab"), "lib")
for _p in (_SCRIPTS, _LAB_LIB):
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

import bpy
from mathutils import Vector, Matrix
import apply_patch as AP
import physics_place as PP

_REPO_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
_OUT_ROOT = os.environ.get("KIT_OUT", os.path.join(_REPO_ROOT, "output", "tests"))
OUT = os.path.join(_OUT_ROOT, "t6_results.json")
TMP = os.path.join(_OUT_ROOT, "t6_tmp")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
os.makedirs(TMP, exist_ok=True)
FAIL = []


def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def check(label, got, expect, tol=1e-6):
    ok = False
    if (isinstance(expect, (int, float)) and isinstance(got, (int, float))):
        ok = abs(got - expect) <= tol
    elif (isinstance(expect, (list, tuple)) and isinstance(got, (list, tuple))
          and len(expect) == len(got)
          and all(isinstance(v, (int, float)) for v in got)):
        ok = all(abs(g - e) <= tol for g, e in zip(got, expect))
    else:
        ok = got == expect
    print(f"[T6] {label}: got={got!r} expect={expect!r} -> "
          f"{'PASS' if ok else 'FAIL'}")
    if not ok:
        FAIL.append(label)


def aabb(obj):
    bpy.context.view_layer.update()  # matrix_world is stale after rotation writes
    pts = [obj.matrix_world @ Vector(v.co) for v in obj.data.vertices]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts),
                 min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts),
                 max(p.z for p in pts)))
    return mn, mx


def dims_of(obj):
    mn, mx = aabb(obj)
    return [round(v, 5) for v in (mx - mn)]


def expect_error(label, fn, *needles):
    """The op must raise RuntimeError mentioning every needle."""
    try:
        fn()
    except RuntimeError as e:
        msg = str(e)
        missing = [n for n in needles if n not in msg]
        check(label, missing, [], )
        return
    except Exception as e:  # wrong exception class
        print(f"[T6] {label}: WRONG EXC {type(e).__name__}: {e} -> FAIL")
        FAIL.append(label)
        return
    print(f"[T6] {label}: NO ERROR RAISED -> FAIL")
    FAIL.append(label)


# ---------------------------------------------------------------- T6a
clear()
AP.apply_mutation({"op": "add_cube", "id": "PropA", "size": [0.4, 0.3, 0.2],
                   "location": [3, 2, 1]})
o = bpy.data.objects["PropA"]
check("T6a name exact (no .001)", o.name, "PropA")
check("T6a dims data-baked", dims_of(o), [0.4, 0.3, 0.2], tol=5e-4)
check("T6a scale untouched", [round(v, 6) for v in o.scale], [1.0, 1.0, 1.0])
mn, mx = aabb(o)
ctr = (mn + mx) / 2
check("T6a origin==center at location",
      [round(v, 4) for v in (Vector((3, 2, 1)) - ctr)],
      [0.0, 0.0, 0.0], tol=1e-3)
check("T6a data name", o.data.name, "PropA")

# scalar size
AP.apply_mutation({"op": "add_cube", "id": "PropA2", "size": 0.25})
check("T6a scalar size", dims_of(bpy.data.objects["PropA2"]),
      [0.25, 0.25, 0.25], tol=5e-4)

# ---------------------------------------------------------------- T6b
clear()
AP.apply_mutation({"op": "add_sphere", "id": "Ball", "radius": 0.5})
check("T6b sphere dims", dims_of(bpy.data.objects["Ball"]),
      [1.0, 1.0, 1.0], tol=6e-3)
AP.apply_mutation({"op": "add_cylinder", "id": "Can", "radius": 0.6,
                   "depth": 1.2})
check("T6b cylinder dims", dims_of(bpy.data.objects["Can"]),
      [1.2, 1.2, 1.2], tol=6e-3)
AP.apply_mutation({"op": "add_cone", "id": "Cone", "radius1": 0.2,
                   "radius2": 0.6, "depth": 0.8})
check("T6b truncated cone reads max(r1,r2)",
      dims_of(bpy.data.objects["Cone"]), [1.2, 1.2, 0.8], tol=6e-3)
AP.apply_mutation({"op": "add_cone", "id": "Spike", "radius1": 0.3,
                   "depth": 0.5})
check("T6b pointy cone default r2", dims_of(bpy.data.objects["Spike"]),
      [0.6, 0.6, 0.5], tol=6e-3)
AP.apply_mutation({"op": "add_torus", "id": "Ring"})
check("T6b torus defaults", dims_of(bpy.data.objects["Ring"]),
      [2.5, 2.5, 0.5], tol=8e-3)

# ---------------------------------------------------------------- T6c
clear()
AP.apply_mutation({"op": "add_plane", "id": "Pad", "size": [3, 2]})
p = bpy.data.objects["Pad"]
check("T6c plane dims", dims_of(p), [3.0, 2.0, 0.0], tol=5e-4)
check("T6c plane normal +Z",
      tuple(round(v, 4) for v in p.data.polygons[0].normal), (0.0, 0.0, 1.0))
AP.apply_mutation({"op": "add_plane", "id": "Pad2", "size": 1.5})
check("T6c plane scalar", dims_of(bpy.data.objects["Pad2"]),
      [1.5, 1.5, 0.0], tol=5e-4)

# ---------------------------------------------------------------- T6d
clear()
AP.apply_mutation({"op": "add_empty", "id": "Anchor",
                   "location": [1, 2, 0.5], "size": 0.3})
e = bpy.data.objects["Anchor"]
check("T6d empty type", e.type, "EMPTY")
check("T6d display default", e.empty_display_type, "PLAIN_AXES")
check("T6d display size", round(e.empty_display_size, 3), 0.3)
check("T6d location", [round(v, 3) for v in e.location], [1.0, 2.0, 0.5])
for t in ("ARROWS", "SINGLE_ARROW", "CIRCLE", "CUBE", "SPHERE", "CONE"):
    AP.apply_mutation({"op": "add_empty", "id": f"Anchor_{t}",
                       "empty_type": t})
    check(f"T6d type {t}", bpy.data.objects[f"Anchor_{t}"].empty_display_type, t)
expect_error("T6d SINGLE_AXIS rejected",
             lambda: AP.apply_mutation({"op": "add_empty", "id": "Bad1",
                                        "empty_type": "SINGLE_AXIS"}),
             "PLAIN_AXES")
expect_error("T6d IMAGE rejected",
             lambda: AP.apply_mutation({"op": "add_empty", "id": "Bad2",
                                        "empty_type": "IMAGE"}),
             "IMAGE")
check("T6d no object left by rejects",
      "Bad1" in bpy.data.objects or "Bad2" in bpy.data.objects, False)

# ---------------------------------------------------------------- T6e/f/g
clear()
AP.apply_mutation({"op": "add_cube", "id": "Prop", "size": 0.2})
n_before = len(bpy.data.objects)
expect_error("T6e name collision refuses",
             lambda: AP.apply_mutation({"op": "add_cube", "id": "Prop",
                                        "size": 0.2}),
             "Prop", "already exists")
check("T6e no silent .001",
      "Prop.001" in bpy.data.objects, False)
check("T6e scene unchanged", len(bpy.data.objects), n_before)
# T6f: re-running the same patch re-raises (idempotent-re-run discipline)
expect_error("T6f patch re-run refuses",
             lambda: AP.apply_mutation({"op": "add_cube", "id": "Prop",
                                        "size": 0.2}),
             "already exists")
# T6g: delete then re-add in one chain works
AP.apply_mutation({"op": "delete_object", "id": "Prop"})
AP.apply_mutation({"op": "add_cube", "id": "Prop", "size": 0.2})
check("T6g delete+re-add", "Prop" in bpy.data.objects, True)

# ---------------------------------------------------------------- T6h
clear()
n0 = len(bpy.data.objects)
expect_error("T6h missing id",
             lambda: AP.apply_mutation({"op": "add_cube", "size": 0.2}),
             "'id'")
expect_error("T6h unknown key",
             lambda: AP.apply_mutation({"op": "add_cube", "id": "X",
                                        "size": 0.2, "colr": [1, 0, 0]}),
             "colr")
expect_error("T6h negative size",
             lambda: AP.apply_mutation({"op": "add_cube", "id": "X",
                                        "size": -0.2}),
             "> 0")
expect_error("T6h zero size",
             lambda: AP.apply_mutation({"op": "add_cube", "id": "X",
                                        "size": 0.0}),
             ">")
expect_error("T6h zero component in vector",
             lambda: AP.apply_mutation({"op": "add_cube", "id": "X",
                                        "size": [0, 1, 1]}),
             "> 0")
expect_error("T6h NaN size",
             lambda: AP.apply_mutation({"op": "add_cube", "id": "X",
                                        "size": float("nan")}),
             "finite")
expect_error("T6h Infinity size",
             lambda: AP.apply_mutation({"op": "add_cube", "id": "X",
                                        "size": float("1e999")}),
             "finite")
expect_error("T6h bool size",
             lambda: AP.apply_mutation({"op": "add_cube", "id": "X",
                                        "size": True}),
             "number")
expect_error("T6h bool in vector",
             lambda: AP.apply_mutation({"op": "add_cube", "id": "X",
                                        "size": [True, 1, 1]}),
             "numbers")
check("T6h scene unchanged after all refusals", len(bpy.data.objects), n0)
# json pipeline really can deliver NaN (why the isfinite guard exists)
nan_patch = json.loads('{"op": "add_cube", "id": "X", "size": NaN}')
expect_error("T6h NaN via json.loads",
             lambda: AP.apply_mutation(nan_patch), "finite")

# ---------------------------------------------------------------- T6i
clear()
AP.apply_mutation({"op": "add_cube", "id": "Mug", "size": [0.16, 0.16, 0.2],
                   "color": [0.8, 0.2, 0.2]})
mat = bpy.data.objects["Mug"].data.materials[0]
check("T6i use_nodes on", mat.use_nodes, True)
bsdf = mat.node_tree.nodes.get("Principled BSDF")
check("T6i Principled present", bsdf is not None, True)
bc = tuple(round(v, 3) for v in bsdf.inputs["Base Color"].default_value)
check("T6i Base Color set", bc[:3], (0.8, 0.2, 0.2))
dc = tuple(round(v, 3) for v in mat.diffuse_color)
check("T6i diffuse_color set (workbench reads THIS)", dc[:3], (0.8, 0.2, 0.2))
# composable with set_material_color
AP.apply_mutation({"op": "set_material_color", "id": "Mug",
                   "color": [0.1, 0.7, 0.3]})
bc2 = tuple(round(v, 3) for v in bsdf.inputs["Base Color"].default_value)
check("T6i set_material_color composable", bc2[:3], (0.1, 0.7, 0.3))
# re-run material: no .001 leak (get-or-create)
AP.apply_mutation({"op": "add_cube", "id": "Mug2", "size": 0.1,
                   "color": [0.2, 0.2, 0.8]})
check("T6i no material .001 leak",
      any(m.name.startswith("Mug2_mat.") for m in bpy.data.materials), False)

# ---------------------------------------------------------------- T6j
clear()
AP.apply_mutation({"op": "add_cube", "id": "Rot", "size": 1.0,
                   "rotation_deg": [0, 0, 45]})
o = bpy.data.objects["Rot"]
check("T6j scale stays 1 under rotation",
      [round(v, 6) for v in o.scale], [1.0, 1.0, 1.0])
check("T6j oriented AABB (check ran PRE-rotation)",
      dims_of(o), [round(math.sqrt(2), 5), round(math.sqrt(2), 5), 1.0],
      tol=1e-3)

# ---------------------------------------------------------------- T6k
clear()
def box(name, size, loc):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.data.transform(Matrix.Diagonal((*size, 1.0)))
    return o

table = box("TableTop", [1.2, 0.8, 0.05], (0, 0, 0.725))
box("Ground", [8, 8, 0.1], (0, 0, -0.05))
AP.apply_mutation({"op": "add_cube", "id": "MugP", "size": [0.16, 0.16, 0.2],
                   "location": [0.3, 0.1, 0.9]})
AP.apply_mutation({"op": "physics_place", "id": "MugP"})
check("T6k physics_place PLACED on fresh add",
      AP._LAST_REPORTS["physics_place"].get("verdict"), "PLACED")
mr = AP._LAST_REPORTS["physics_place"]
check("T6k rests_on Table", mr.get("rests_on"), "TableTop")
AP.apply_mutation({"op": "add_cube", "id": "BowlP", "size": [0.2, 0.2, 0.1],
                   "location": [-0.3, -0.1, 1.0]})
AP.apply_mutation({"op": "place_on", "id": "BowlP", "supports": ["TableTop"]})
pr = AP._LAST_REPORTS["place_on"]
check("T6k place_on TOUCHING", pr.get("ok"), True)
AP.apply_mutation({"op": "audit", "pairs": ["MugP,TableTop",
                                            "BowlP,TableTop"],
                   "fail_on_penetration": False})
check("T6k audit no penetration", AP._LAST_REPORTS["audit"]["failed"], False)

# ---------------------------------------------------------------- T6l
clear()
box("Floor", [8, 8, 0.1], (0, 0, -0.05))
fig = box("Figure", [0.3, 0.3, 0.6], (2.0, 0, 1.2))  # floating somewhere
AP.apply_mutation({"op": "add_empty", "id": "SeatAnchor",
                   "location": [0, 0, 0.5]})
AP.apply_mutation({"op": "seat_at", "id": "Figure", "seat": "SeatAnchor"})
mn, mx = aabb(fig)
check("T6l seat_at lands bottom at anchor z", round(mn.z, 4), 0.5, tol=5e-4)

# ---------------------------------------------------------------- T6o
clear()
AP.apply_mutation({"op": "add_cylinder", "id": "Hept", "radius": 0.5,
                   "depth": 1.0, "vertices": 7})
check("T6o v7 chord shortfall accepted honestly",
      dims_of(bpy.data.objects["Hept"]), [1.0, 1.0, 1.0], tol=0.101)

# ---------------------------------------------------------------- T6p
clear()
box("Ground", [8, 8, 0.1], (0, 0, -0.05))
AP.apply_mutation({"op": "add_empty", "id": "Anchor",
                   "location": [0, 0, 0.4]})
try:
    rep = PP.place(bpy.data.objects["Anchor"])
    exc = None
except Exception as e:
    rep, exc = None, e
check("T6p physics_place(empty) no crash", exc is None, True)
if rep is not None:
    excl = rep.get("excluded", [])
    check("T6p honest non_mesh exclusion",
          any("non_mesh" in x.get("reasons", []) for x in excl), True)

# ------------------------------------------------- T6m/T6n (CLI subprocess)
# Uses the blender binary directly (sys.executable inside Blender); the
# nested run is --background (no display needed), HOME redirected to the
# kit's .blender-home (set by run.sh) so no config is written elsewhere.
env = os.environ.copy()
env.setdefault("HOME", os.environ.get("BLENDER_HOME", TMP))
# blrun normally puts scripts/ on PYTHONPATH (blender_kit import at the
# top of apply_patch.py needs it); a direct binary call must set it.
env["PYTHONPATH"] = _SCRIPTS + os.pathsep + env.get("PYTHONPATH", "")

# T6m: --export-schema after add (+ EMPTY bounds null)
schema_out = os.path.join(TMP, "schema.json")
patch_json = json.dumps({"mutations": [
    {"op": "add_cube", "id": "Prop", "size": [0.4, 0.3, 0.2],
     "location": [0, 0, 0.1]},
    {"op": "add_empty", "id": "Anchor", "location": [0, 0, 1]}]})
r = subprocess.run(
    [os.environ.get("BLENDER_BIN") or sys.argv[0], "--python-use-system-env", "--background", "--python",
     os.path.join(_SCRIPTS, "apply_patch.py"), "--",
     "--patch-json", patch_json, "--export-schema", schema_out,
     "--with-bounds"],
    capture_output=True, text=True, env=env, timeout=300)
check("T6m CLI exit 0", r.returncode, 0)
if r.returncode == 0:
    sch = json.load(open(schema_out))
    names = {o.get("id"): o for o in sch.get("objects", [])}
    check("T6m schema has added MESH", "Prop" in names, True)
    check("T6m schema has added EMPTY", "Anchor" in names, True)
    check("T6m EMPTY bounds null",
          names.get("Anchor", {}).get("bounds") is None, True)
    ps = (names.get("Prop", {}).get("bounds") or {}).get("size")
    check("T6m mesh bounds.size correct",
          [round(v, 4) for v in (ps or [])], [0.4, 0.3, 0.2], tol=1e-3)

# T6n: W1 abort-save (collision mid-chain -> exit 1, blend saved)
blend_out = os.path.join(TMP, "aborted.blend")
patch_json = json.dumps({"mutations": [
    {"op": "add_cube", "id": "Prop", "size": 0.2},
    {"op": "add_cube", "id": "Prop", "size": 0.2}]})
r = subprocess.run(
    [os.environ.get("BLENDER_BIN") or sys.argv[0], "--python-use-system-env", "--background", "--python",
     os.path.join(_SCRIPTS, "apply_patch.py"), "--",
     "--patch-json", patch_json, "--save-blend", blend_out],
    capture_output=True, text=True, env=env, timeout=300)
check("T6n CLI exit 1 on collision", r.returncode, 1)
check("T6n blend saved anyway", os.path.exists(blend_out), True)
check("T6n no silent .001 in stderr/stdout flow",
      "already exists" in (r.stderr + r.stdout), True)

# ---------------------------------------------------------------- wrap-up
results = {"suite": "T6 add-primitive patch ops", "fail": FAIL,
           "n_cases": 16}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w") as f:
    json.dump(results, f, indent=2)
print(f"[T6] {'ALL PASS' if not FAIL else 'FAILURES: ' + str(FAIL)}")
print(f"[T6] wrote {OUT}")
if FAIL:
    raise SystemExit(1)
