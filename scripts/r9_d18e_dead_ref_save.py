# D18 probe N6: does save_as_mainfile(compress=True) abort when FILE-source
# images point at dead paths? (R6 recorded an abort; verify mechanism + fallback)
import bpy, os, tempfile, json

tmp = tempfile.mkdtemp(prefix="d18e_")
res = {}
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_cube_add(size=1)
ob = bpy.context.active_object
mat = bpy.data.materials.new("dead_mat")
mat.use_nodes = True
nt = mat.node_tree
tex = nt.nodes.new("ShaderNodeTexImage")
img = bpy.data.images.new("dead_img", 32, 32)
img.source = 'FILE'
img.filepath = "/nonexistent/dead/vendor_path.png"  # dead absolute path
tex.image = img
nt.links.new(tex.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"])
ob.data.materials.append(mat)

f1 = os.path.join(tmp, "dead_ref.blend")
try:
    bpy.ops.wm.save_as_mainfile(filepath=f1, compress=True)
    res["compress_save_with_dead_ref"] = {"ok": True, "size": os.path.getsize(f1)}
except Exception as e:
    res["compress_save_with_dead_ref"] = {"ok": False, "error": str(e)}

# and libraries.write with the same closure
f2 = os.path.join(tmp, "dead_ref_chunk.blend")
try:
    bpy.data.libraries.write(f2, {ob}, compress=True)
    res["write_with_dead_ref"] = {"ok": True, "size": os.path.getsize(f2)}
except Exception as e:
    res["write_with_dead_ref"] = {"ok": False, "error": str(e)}

out = "/home/z/work/bvk/output/r9/d18e_dead_ref_save.json"
with open(out, "w") as f:
    json.dump(res, f, indent=1)
print("[N6-WRITTEN]", out)
print(json.dumps(res, indent=1))
