# test_v9_fixes_s16.py — session-16 fix regressions (in-Blender).
#
# Covers three Wave-A fixes:
#   1. F19 ack_many_parts: loose split of a >50-part mesh refuses
#      without the ack, splits with it (dry-run report carries part_count).
#   2. Scoped audit matches the STATE enum (not the verdict string):
#      a scoped audit over a penetrating pair must ABORT (RuntimeError
#      with fail_on_penetration default), a scoped audit over a clean
#      pair must pass. Pre-fix, `failed` was always False and the abort
#      never fired — the doc's own law (match `state`, never `verdict`)
#      was violated by the kit's own code.
#   3. F-TD5: render_hidden_objects sweeps the DEPSGRAPH — an object
#      linked+hidden within the same script run must be classified
#      render-hidden (a stale view layer would miss it and leak it into
#      the GLB), and must DROP OUT once unhidden in the same run.
#
# Run: blrun.sh --background --python tests/test_v9_fixes_s16.py
# Convention: prints [test_v9] per check; "ALL PASS" at the end.

import bmesh
import bpy
import sys

PASS = []
FAIL = []


def check(name, cond, detail=""):
    tag = "ok" if cond else "FAIL"
    print(f"[test_v9] {name}: {tag}" + (f" — {detail}" if detail and not cond else ""))
    (PASS if cond else FAIL).append(name)


def wipe():
    bpy.ops.wm.read_factory_settings(use_empty=True)


# ---------------------------------------------------------------- 1. F19
wipe()
N = 60
mesh = bpy.data.meshes.new("many_parts")
bm = bmesh.new()
for i in range(N):
    tmp = bmesh.new()
    bmesh.ops.create_cube(tmp, size=0.2)
    bmesh.ops.translate(tmp, vec=(i * 3.0, 0, 0), verts=tmp.verts)
    vmap = [bm.verts.new(v.co) for v in tmp.verts]
    for f in tmp.faces:
        bm.faces.new([vmap[v.index] for v in f.verts])
    bm.verts.index_update()
    tmp.free()
bm.to_mesh(mesh)
bm.free()

ob = bpy.data.objects.new("ManyParts", mesh)
bpy.context.scene.collection.objects.link(ob)

import semantic_lib as SL

dry = SL.analyze_split(ob)
check("f19.dry_run_reports_part_count", dry.get("part_count") == N,
      f"part_count={dry.get('part_count')}")

refused = False
try:
    SL.split_object(ob)
except RuntimeError as e:
    refused = "ack_many_parts" in str(e)
check("f19.refuses_without_ack_over_50", refused)

rep = SL.split_object(ob, ack_many_parts=True)
check("f19.splits_with_ack", rep.get("ok") is True and rep.get("part_count") == N,
      str({k: rep.get(k) for k in ("ok", "part_count")}))
check("f19.source_name_kept",
      rep.get("source") == "ManyParts" and "ManyParts" in bpy.data.objects.keys(),
      f"source={rep.get('source')}")

# ------------------------------------------------------------ 2. scoped audit
wipe()
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
a = bpy.context.active_object
a.name = "ScopedA"
# size 1.4 @ x=0.2: swallows four A verts strictly inside — the vert-sample
# audit classifies the pair PENETRATING (size-1 co-face-aligned cubes read
# boundary-ambiguous TOUCHING; probed)
bpy.ops.mesh.primitive_cube_add(size=1.4, location=(0.2, 0, 0))
b = bpy.context.active_object
b.name = "ScopedB"

import apply_patch as AP

aborted = False
try:
    AP.apply_mutation({"op": "audit", "id": "ScopedA"})
except RuntimeError as e:
    aborted = "penetration" in str(e).lower()
check("scoped_audit.aborts_on_penetration", aborted)
# Pre-fix this call printed failed=False and returned normally.

# clean pair: separate far away, scoped audit must pass
b.location = (10, 0, 0)
try:
    AP.apply_mutation({"op": "audit", "id": "ScopedA"})
    clean_ok = True
except RuntimeError:
    clean_ok = False
check("scoped_audit.clean_pair_passes", clean_ok)

# ------------------------------------------------------------------ 3. F-TD5
wipe()
import blender_kit as BK

me = bpy.data.meshes.new("helper")
bm = _bm = bmesh.new()
bmesh.ops.create_cube(bm, size=0.5)
bm.to_mesh(me)
bm.free()
helper = bpy.data.objects.new("SweepHelper", me)
helper.hide_render = True
bpy.context.scene.collection.objects.link(helper)  # linked in the SAME run

sweep = BK.render_hidden_objects(bpy.context.scene)
check("ftd5.fresh_hidden_object_swept", helper.name in [o.name for o in sweep],
      f"sweep={[o.name for o in sweep]}")

helper.hide_render = False
sweep2 = BK.render_hidden_objects(bpy.context.scene)
check("ftd5.unhidden_same_run_drops_out", helper.name not in [o.name for o in sweep2])

# --------------------------------------------------------------------- end
print(f"[test_v9] {len(PASS)} passed, {len(FAIL)} failed")
if FAIL:
    print("[test_v9] FAILURES:", FAIL)
    sys.exit(1)
print("[test_v9] ALL PASS")
