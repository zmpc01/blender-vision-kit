# D18 probe 5b: sever the scene back-edge — set scene.compositing_node_group
# = None before write, restore after. If the closure then stays local, the
# compositor group can ride chunk_00 like any other node group.
import bpy, os, tempfile, json

tmp = tempfile.mkdtemp(prefix="d18g_")
res = {}
bpy.ops.wm.open_mainfile(filepath="assets/loft/loft_ext.blend")
sc = bpy.context.scene
cg = sc.compositing_node_group
w = sc.world

# sever
sc.compositing_node_group = None
cg.use_fake_user = True

f1 = os.path.join(tmp, "w_severed.blend")
bpy.data.libraries.write(f1, {cg, w, bpy.data.objects["Area"]}, compress=True)

d = {}
with bpy.data.libraries.load(f1, link=False) as (src, _):
    for attr in ("objects", "meshes", "materials", "images", "worlds",
                 "node_groups", "scenes"):
        d[attr] = len(list(getattr(src, attr)))
res["severed_comp_write"] = d

# restore
sc.compositing_node_group = cg
cg.use_fake_user = False
res["restored_ok"] = sc.compositing_node_group is cg
res["nodes_in_group"] = [(n.name, n.bl_idname) for n in cg.nodes]
# links for the manifest/rebuild honesty
res["node_links"] = sum(1 for _ in cg.links)
out = "/home/z/work/bvk/output/r9/d18g_severed_comp.json"
with open(out, "w") as f:
    json.dump(res, f, indent=1)
print("[D18G-WRITTEN]", out)
print(json.dumps(res, indent=1))
