# D18 probe 4: does libraries.write embed PACKED pixel buffers?
# Incompressible noise image: if packed_size >> unpacked_size, pixels travel.
import bpy, os, tempfile, json, random

tmp = tempfile.mkdtemp(prefix="d18c_")
res = {}
bpy.ops.wm.read_factory_settings(use_empty=True)
img = bpy.data.images.new("noise_img", 256, 256)
px = [random.random() for _ in range(256 * 256 * 4)]
img.pixels.foreach_set(px)
img.pack()
me = bpy.data.meshes.new("m")
bpy.ops.mesh.primitive_cube_add(size=1)
ob = bpy.context.active_object
ob.data = me
mat = bpy.data.materials.new("m_mat")
mat.use_nodes = True
nt = mat.node_tree
tex = nt.nodes.new("ShaderNodeTexImage")
tex.image = img
nt.links.new(tex.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"])
me.materials.append(mat)

f1 = os.path.join(tmp, "packed.blend")
bpy.data.libraries.write(f1, {ob})
res["packed_chunk_size"] = os.path.getsize(f1)

img.unpack(method='REMOVE')  # now FILE-source, no pack
f2 = os.path.join(tmp, "unpacked.blend")
bpy.data.libraries.write(f2, {ob})
res["unpacked_chunk_size"] = os.path.getsize(f2)
res["delta_bytes"] = res["packed_chunk_size"] - res["unpacked_chunk_size"]
res["verdict"] = ("PIXELS TRAVEL in packed chunks" if res["delta_bytes"] > 50000
                  else "write() does NOT embed packed pixels — externalize textures")

out = "/home/z/work/bvk/output/r9/d18c_packed_payload.json"
with open(out, "w") as f:
    json.dump(res, f, indent=1)
print("[D18C-WRITTEN]", out)
print(json.dumps(res, indent=1))
