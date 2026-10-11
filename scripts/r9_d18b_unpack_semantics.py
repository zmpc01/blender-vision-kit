# D18 probe 3: verify that unpacked (FILE-source) images write to chunks as
# PATH REFERENCES with no pixel payload, and that append resolves them.
import bpy, os, tempfile, json

tmp = tempfile.mkdtemp(prefix="d18b_")
res = {}

# synthetic: image packed (as if imported), material using it, cube using mat
bpy.ops.wm.read_factory_settings(use_empty=True)
img = bpy.data.images.new("probe_img", 128, 128)
# fill pixels so it has real payload, then pack
px = [0.5] * (128 * 128 * 4)
img.pixels.foreach_set(px)
img.pack()
me = bpy.data.meshes.new("cube_mesh")
bpy.ops.mesh.primitive_cube_add(size=1)
ob = bpy.context.active_object
ob.data = me
mat = bpy.data.materials.new("probe_mat")
mat.use_nodes = True
nt = mat.node_tree
tex = nt.nodes.new("ShaderNodeTexImage")
tex.image = img
nt.links.new(tex.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"])
me.materials.append(mat)

# 1) chunk WITH the image packed -> expect pixels inside (big file)
f_packed = os.path.join(tmp, "chunk_packed.blend")
bpy.data.libraries.write(f_packed, {ob}, compress=False)
res["packed_size"] = os.path.getsize(f_packed)

# 2) unpack: write pixel payload to a texture folder, flip to FILE source,
#    and store the path CHUNK-RELATIVE (//../loft_textures/<name>) so the
#    reference survives clone relocation (the whole tree can move).
texdir = os.path.join(tmp, "textures")
os.makedirs(texdir, exist_ok=True)
texpath = os.path.join(texdir, "probe_img.png")
img.filepath_raw = texpath
img.file_format = 'PNG'
img.save()
img.source = 'FILE'
img.unpack(method='REMOVE')
img.filepath = bpy.path.relpath(texpath, start=tmp)  # //textures/probe_img.png
img.reload()

# chunks are written "as if" they live in <tmp>/assets/loft_chunks/, so the
# texture relative to the CHUNK is //../textures/<name>
chunkdir = os.path.join(tmp, "assets", "loft_chunks")
os.makedirs(chunkdir, exist_ok=True)
img.filepath = "//../textures/probe_img.png"

f_unpacked = os.path.join(tmp, "chunk_unpacked.blend")
bpy.data.libraries.write(f_unpacked, {ob}, compress=False)
res["unpacked_size"] = os.path.getsize(f_unpacked)
res["size_drop_x"] = round(res["packed_size"] / max(res["unpacked_size"], 1), 1)

# 3) inventory of the unpacked chunk: image present as FILE ref?
inv = {}
with bpy.data.libraries.load(f_unpacked, link=False) as (src, _):
    inv["images"] = list(src.images)
    inv["materials"] = list(src.materials)
res["unpacked_inventory"] = inv

# 4) append in a FRESH session from a MOVED location (simulate clone):
#    move chunk + textures into a fake repo layout, open from elsewhere
repo = os.path.join(tmp, "repo", "assets", "loft_chunks")
os.makedirs(repo, exist_ok=True)
os.replace(f_unpacked, os.path.join(repo, "chunk_unpacked.blend"))
os.replace(texdir, os.path.join(tmp, "repo", "assets", "loft_textures"))
# NOTE: chunk was written with ABSOLUTE texture path; appending still works
# (absolute paths travel), relative-path hygiene is a save-time concern.
bpy.ops.wm.read_factory_settings(use_empty=True)
with bpy.data.libraries.load(os.path.join(repo, "chunk_unpacked.blend"),
                             link=False) as (src, ctx):
    ctx.objects = list(src.objects)
appended = bpy.data.objects.get("Cube")
res["append_ok"] = appended is not None
im2 = bpy.data.images.get("probe_img")
if im2 is not None:
    loaded = False
    try:
        loaded = im2.has_data and im2.size[0] > 0
    except Exception:
        loaded = False
    res["appended_image"] = {"source": im2.source,
                             "filepath": im2.filepath[:80],
                             "has_data": bool(im2.has_data),
                             "size": list(im2.size),
                             "pixels_loaded": loaded}
res["appended_mat_nodes"] = bpy.data.materials.get("probe_mat") is not None

out = "/home/z/work/bvk/output/r9/d18b_unpack_semantics.json"
with open(out, "w") as f:
    json.dump(res, f, indent=1, default=str)
print("[D18B-WRITTEN]", out)
print(json.dumps(res, indent=1, default=str))
