# R9 probe: loft.blend structure survey for the asset-partition design (D18).
# Answers: parenting shape, collections, packed images, per-root size estimates,
# shared-datablock fan-out — the data that decides the chunking strategy.
#
# Run: ./run.sh --background --python scripts/r9_chunk_probe.py -- \
#        --blend polyhaven_cache/loft/loft.blend --out output/r9/chunk_probe.json
import bpy, sys, json, os, argparse

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
p = argparse.ArgumentParser()
p.add_argument("--blend", required=True)
p.add_argument("--out", required=True)
a = p.parse_args(argv)

rep = {"file": os.path.basename(a.blend), "bytes": os.path.getsize(a.blend)}

# --- load (open, don't rebuild) ---
bpy.ops.wm.open_mainfile(filepath=a.blend)

objs = list(bpy.data.objects)
rep["n_objects"] = len(objs)
rep["n_mesh"] = len(bpy.data.meshes)
rep["n_materials"] = len(bpy.data.materials)
rep["n_images"] = len(bpy.data.images)
rep["n_armatures"] = len(bpy.data.armatures)
rep["n_node_groups"] = len(bpy.data.node_groups)
rep["n_scenes"] = len(bpy.data.scenes)

# scenes and their object membership
rep["scenes"] = []
for sc in bpy.data.scenes:
    rep["scenes"].append({"name": sc.name, "objects": len(sc.objects),
                          "collections": len(sc.collection.children)})

# top-level collections (in the primary scene)
sc = bpy.context.scene
def col_tree(c, depth=0, out=None):
    out = out if out is not None else []
    kids = [col_tree(k, depth + 1) for k in c.children]
    node = {"name": c.name, "depth": depth, "n_objects": len(c.objects),
            "children": kids}
    out.append(node)
    return node
rep["collection_tree"] = [col_tree(c) for c in sc.collection.children]

# parenting
roots = [o for o in objs if o.parent is None]
rep["n_roots"] = len(roots)
rep["n_parented"] = len(objs) - len(roots)
rep["parent_types"] = {}
for o in objs:
    if o.parent is not None:
        t = o.parent.type
        rep["parent_types"][t] = rep["parent_types"].get(t, 0) + 1

# packed images: count + bytes + largest
packed = [im for im in bpy.data.images
          if im.source == 'FILE' and im.packed_file is not None]
unpacked = [im for im in bpy.data.images
            if im.source == 'FILE' and im.packed_file is None]
rep["images_packed"] = len(packed)
rep["images_unpacked"] = len(unpacked)
rep["packed_bytes"] = sum(im.packed_file.size for im in packed)
rep["largest_packed"] = sorted(
    [{"name": im.name, "mb": round(im.packed_file.size / 1e6, 1)}
     for im in packed], key=lambda d: -d["mb"])[:8]

# per-root subtree: object count + estimated bytes (mesh verts*12 + packed imgs
# attributed once per unique image within the subtree)
def subtree_bytes(root):
    stack, seen = [root], set()
    imgs, tot_mesh_bytes, n = set(), 0, 0
    while stack:
        o = stack.pop()
        if o.name in seen:
            continue
        seen.add(o.name)
        n += 1
        if o.type == 'MESH' and o.data:
            tot_mesh_bytes += len(o.data.vertices) * 32 + len(o.data.polygons) * 24
            for ms in o.data.materials:
                if ms and ms.use_nodes:
                    for nd in ms.node_tree.nodes:
                        if nd.type == 'TEX_IMAGE' and nd.image and nd.image.source == 'FILE':
                            if nd.image.packed_file is not None:
                                imgs.add(nd.image.name)
        stack.extend(o.children)
    return n, tot_mesh_bytes + sum(
        bpy.data.images[i].packed_file.size for i in imgs), len(imgs)

roots_info = []
for r in roots:
    n, b, ni = subtree_bytes(r)
    roots_info.append({"name": r.name, "type": r.type, "n_sub": n,
                       "est_mb": round(b / 1e6, 1), "n_img": ni})
roots_info.sort(key=lambda d: -d["est_mb"])
rep["roots_top20"] = roots_info[:20]
rep["n_roots_over_1mb"] = sum(1 for r in roots_info if r["est_mb"] > 1.0)
rep["sum_root_est_mb"] = round(sum(r["est_mb"] for r in roots_info) / 1e6 * 1e6 / 1e6, 1)

# material fan-out (shared materials across objects)
mat_users = {}
for o in objs:
    if o.type == 'MESH' and o.data:
        for m in o.data.materials:
            if m:
                mat_users[m.name] = mat_users.get(m.name, 0) + 1
rep["n_mats_used"] = len(mat_users)
rep["mat_max_users"] = max(mat_users.values()) if mat_users else 0

# world / lights / cameras
rep["n_lights"] = sum(1 for o in objs if o.type == 'LIGHT')
rep["n_cameras"] = sum(1 for o in objs if o.type == 'CAMERA')
rep["has_world"] = sc.world is not None

# library links (external .blend deps)
rep["n_libraries"] = len(list(bpy.data.libraries))

os.makedirs(os.path.dirname(a.out), exist_ok=True)
with open(a.out, "w") as f:
    json.dump(rep, f, indent=1)
print("[PROBE-WRITTEN]", a.out)
print(json.dumps({k: rep[k] for k in
    ("n_objects","n_mesh","n_materials","n_images","n_roots","n_parented",
     "images_packed","packed_bytes","n_libraries","has_world")}, indent=1))
