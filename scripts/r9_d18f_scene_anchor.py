# D18 probe 5: which ID pulls the SCENE into the write closure?
# Candidates: world / compositor group / plain light object.
import bpy, os, tempfile, json

tmp = tempfile.mkdtemp(prefix="d18f_")
res = {}
bpy.ops.wm.open_mainfile(filepath="assets/loft/loft_ext.blend")

def inv(path):
    d = {}
    with bpy.data.libraries.load(path, link=False) as (src, _):
        for attr in ("objects", "meshes", "materials", "images", "worlds",
                     "node_groups", "scenes", "collections"):
            d[attr] = len(list(getattr(src, attr)))
    return d

sc = bpy.context.scene
w = sc.world
cg = sc.compositing_node_group
light = bpy.data.objects["Area"]

f1 = os.path.join(tmp, "w_world.blend")
bpy.data.libraries.write(f1, {w}, compress=True)
res["world_only"] = inv(f1)

f2 = os.path.join(tmp, "w_comp.blend")
bpy.data.libraries.write(f2, {cg}, compress=True)
res["comp_only"] = inv(f2)

f3 = os.path.join(tmp, "w_light.blend")
bpy.data.libraries.write(f3, {light}, compress=True)
res["light_only"] = inv(f3)

f4 = os.path.join(tmp, "w_world_light.blend")
bpy.data.libraries.write(f4, {w, light}, compress=True)
res["world_plus_light"] = inv(f4)

out = "/home/z/work/bvk/output/r9/d18f_scene_anchor.json"
with open(out, "w") as f:
    json.dump(res, f, indent=1)
print("[D18F-WRITTEN]", out)
print(json.dumps(res, indent=1))
