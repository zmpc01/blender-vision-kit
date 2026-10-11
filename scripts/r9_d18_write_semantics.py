# D18 research: what does bpy.data.libraries.write actually include?
# Test matrix: write [object] / [mesh] / [material] / [image] / [collection]
# -> re-open each file -> inventory what came along.
# Also: linked-datablock refusal test, and append-with-existing-name dedup.
import bpy, os, tempfile, json

tmp = tempfile.mkdtemp(prefix="d18_")
res = {}

def inventory(path):
    ids = {}
    with bpy.data.libraries.load(path, link=False) as (src, _):
        for attr in ("objects", "meshes", "materials", "images", "collections",
                     "node_groups", "lights", "cameras", "worlds", "texts"):
            ids[attr] = list(getattr(src, attr))
    return ids

# ---------- build a synthetic scene ----------
bpy.ops.wm.read_factory_settings(use_empty=True)
img = bpy.data.images.new("testimg", 64, 64)
img.packed_file  # force-pack via save? images.new packs on save of file
mat = bpy.data.materials.new("testmat")
mat.use_nodes = True
nt = mat.node_tree
tex = nt.nodes.new("ShaderNodeTexImage")
tex.image = img
bsdf = nt.nodes["Principled BSDF"]
nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
me = bpy.data.meshes.new("testmesh")
ob = bpy.data.objects.new("testobj", me)
bpy.context.scene.collection.objects.link(ob)
me.materials.append(mat)
child = bpy.data.objects.new("testchild", None)
bpy.context.scene.collection.objects.link(child)
child.parent = ob
col = bpy.data.collections.new("testcol")
bpy.context.scene.collection.children.link(col)

# must save the host file once so the image gets packed
host = os.path.join(tmp, "host.blend")
bpy.ops.wm.save_as_mainfile(filepath=host, compress=True)

# ---------- test 1: write [object] only ----------
f1 = os.path.join(tmp, "t1_obj.blend")
try:
    bpy.data.libraries.write(f1, {ob})
    res["t1_size"] = os.path.getsize(f1) if os.path.exists(f1) else -1
    res["write_object_only"] = inventory(f1)
except Exception as e:
    res["write_object_only_ERROR"] = str(e)
    try:
        res["t1_size"] = os.path.getsize(f1) if os.path.exists(f1) else -1
    except Exception:
        pass

# ---------- test 2: write [material] only ----------
f2 = os.path.join(tmp, "t2_mat.blend")
try:
    bpy.data.libraries.write(f2, {mat})
    res["write_material_only"] = inventory(f2)
except Exception as e:
    res["write_material_only_ERROR"] = str(e)

# ---------- test 3: write [collection] ----------
f3 = os.path.join(tmp, "t3_col.blend")
try:
    bpy.data.libraries.write(f3, {col})
    res["write_collection_only"] = inventory(f3)
except Exception as e:
    res["write_collection_only_ERROR"] = str(e)

# ---------- test 4: write [mesh] only ----------
f4 = os.path.join(tmp, "t4_mesh.blend")
try:
    bpy.data.libraries.write(f4, {me})
    res["write_mesh_only"] = inventory(f4)
except Exception as e:
    res["write_mesh_only_ERROR"] = str(e)

# ---------- test 5: MISSING dep (no image in file) ----------
bpy.ops.wm.read_factory_settings(use_empty=True)
img2 = bpy.data.images.new("orphan_img", 32, 32)
# do NOT pack/save it — check images.new + write works
f5 = os.path.join(tmp, "t5_img.blend")
try:
    bpy.data.libraries.write(f5, {img2})
    res["write_image_only"] = inventory(f5)
except Exception as e:
    res["write_image_only_ERROR"] = str(e)

# ---------- test 6: linked datablock refusal ----------
f6 = os.path.join(tmp, "t6_link.blend")
try:
    with bpy.data.libraries.load(host, link=True) as (src, _):
        pass
    # link the object from host
    with bpy.data.libraries.load(host, link=True) as (src, ctx):
        ctx.objects = ["testobj"]
    linked = bpy.data.objects.get("testobj")
    if linked is not None and linked.library is not None:
        try:
            bpy.data.libraries.write(f6, {linked})
            res["write_linked"] = {"size": os.path.getsize(f6), "NOTE": "wrote a linked ID?"}
        except Exception as e:
            res["write_linked_ERROR"] = str(e)
    else:
        res["write_linked_ERROR"] = f"link failed (found={linked is not None}, lib={getattr(linked,'library',None)})"
except Exception as e:
    res["write_linked_ERROR"] = str(e)

# ---------- test 7: append same names twice (dedup semantics) ----------
try:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for i in range(2):
        with bpy.data.libraries.load(f1, link=False) as (src, ctx):
            ctx.objects = ["testobj", "testchild"]
        names = [o.name for o in bpy.data.objects]
        res[f"append_pass_{i+1}"] = {"objects": names}
    # after pass2: does testobj exist once (dedup) or as .001?
    res["append_dedup"] = {
        "testobj_count": sum(1 for o in bpy.data.objects if o.name == "testobj"),
        "testobj_dot001": sum(1 for o in bpy.data.objects if o.name.startswith("testobj.")),
    }
    # parenting across the two appends: pass-2 child still points at pass-1 obj?
    o1 = bpy.data.objects.get("testobj")
    c1 = bpy.data.objects.get("testchild")
    res["append_parenting"] = {"child_parent": c1.parent.name if c1 and c1.parent else None}
except Exception as e:
    res["append_test_ERROR"] = str(e)

# ---------- test 8: compress=True size effect on a chunk ----------
try:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(host, link=False) as (src, ctx):
        ctx.objects = ["testobj"]
    ob2 = bpy.data.objects["testobj"]
    fc = os.path.join(tmp, "t8_comp.blend")
    fo = os.path.join(tmp, "t8_plain.blend")
    bpy.data.libraries.write(fc, {ob2}, compress=True)
    bpy.data.libraries.write(fo, {ob2}, compress=False)
    res["compress_effect"] = {"compressed": os.path.getsize(fc), "plain": os.path.getsize(fo)}
except Exception as e:
    res["compress_test_ERROR"] = str(e)

out = "/home/z/work/bvk/output/r9/d18_write_semantics.json"
with open(out, "w") as f:
    json.dump(res, f, indent=1, default=str)
print("[D18-WRITTEN]", out)
print(json.dumps(res, indent=1, default=str))
