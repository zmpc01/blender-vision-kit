# D18 probe 2: precise per-collection mesh bytes, largest images, parenting
# map, and the missing-library inventory — final inputs for the design.
import bpy, sys, json, os, argparse

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
p = argparse.ArgumentParser()
p.add_argument("--blend", required=True)
p.add_argument("--out", required=True)
a = p.parse_args(argv)

bpy.ops.wm.open_mainfile(filepath=a.blend)

def mesh_bytes(m):
    return len(m.vertices) * 32 + len(m.polygons) * 40 + len(m.loops) * 20

def img_bytes(im):
    return im.packed_file.size if im.packed_file is not None else 0

def img_users(im):
    n = 0
    for mat in bpy.data.materials:
        if mat.use_nodes and mat.node_tree:
            for nd in mat.node_tree.nodes:
                if nd.type == 'TEX_IMAGE' and nd.image == im:
                    n += 1
                    break
    return n

imgs = sorted(
    [{"name": im.name, "mb": round(img_bytes(im) / 1e6, 2), "users": img_users(im),
      "pinned": im.source}
     for im in bpy.data.images if im.source in ('FILE', 'GENERATED')],
    key=lambda d: -d["mb"])
rep = {"largest_images": imgs[:12],
       "n_images_ge_50mb": sum(1 for x in imgs if x["mb"] >= 50),
       "total_img_mb": round(sum(x["mb"] for x in imgs) / 1, 2)}

# per top-level collection (recursive): objects + mesh bytes + unique images
def walk_col(c, acc):
    acc["objs"].extend(c.objects)
    for k in c.children:
        walk_col(k, acc)

sc = bpy.context.scene
cols = []
for c in sc.collection.children:
    acc = {"objs": []}
    walk_col(c, acc)
    mb = sum(mesh_bytes(o.data) for o in acc["objs"] if o.type == 'MESH' and o.data)
    imset = set()
    for o in acc["objs"]:
        if o.type == 'MESH' and o.data:
            for m in o.data.materials:
                if m and m.use_nodes and m.node_tree:
                    for nd in m.node_tree.nodes:
                        if nd.type == 'TEX_IMAGE' and nd.image:
                            imset.add(nd.image.name)
    imb = sum(img_bytes(bpy.data.images[n]) for n in imset)
    cols.append({"name": c.name, "n_obj": len(acc["objs"]), "mesh_mb": round(mb / 1e6, 1),
                 "uniq_imgs": len(imset), "uniq_img_mb": round(imb / 1e6, 1)})
rep["collections"] = cols

# objects NOT in any top-level collection (scene root level)
known = set()
for c in sc.collection.children:
    acc = {"objs": []}
    walk_col(c, acc)
    known.update(o.name for o in acc["objs"])
orphans = [o.name for o in sc.collection.objects if o.name not in known]
rep["root_level_orphans"] = {"n": len(orphans), "names": orphans[:30]}

# biggest single-object meshes (chunk floor)
big = sorted(({"name": o.name, "mb": round(mesh_bytes(o.data) / 1e6, 1)}
              for o in bpy.data.objects if o.type == 'MESH' and o.data),
             key=lambda d: -d["mb"])
rep["largest_meshes"] = big[:10]
rep["n_meshes_ge_20mb"] = sum(1 for x in big if x["mb"] >= 20)

# parenting pairs (all 25)
pairs = []
for o in bpy.data.objects:
    if o.parent is not None:
        pairs.append({"child": o.name, "parent": o.parent.name,
                      "ptype": o.parent_type if hasattr(o, "parent_type") else "?"})
rep["parent_pairs"] = pairs

# library / missing-link inventory
libs = []
for lib in bpy.data.libraries:
    libs.append({"name": lib.name, "filepath": lib.filepath[:80]})
rep["libraries"] = libs
linked_ids = {"objects": 0, "meshes": 0, "materials": 0, "images": 0, "node_groups": 0}
for attr in linked_ids:
    linked_ids[attr] = sum(1 for d in getattr(bpy.data, attr) if d.library is not None)
rep["linked_ids"] = linked_ids

# non-mesh objects inventory by type
types = {}
for o in bpy.data.objects:
    types[o.type] = types.get(o.type, 0) + 1
rep["object_types"] = types

# worlds + scene render settings that rebuild must restore
w = sc.world
rep["world"] = {"name": w.name if w else None,
                "uses_nodes": bool(w and w.use_nodes),
                "n_nodes": len(w.node_tree.nodes) if w and w.use_nodes else 0}
rep["scene_settings"] = {"fps": sc.render.fps, "engine": sc.render.engine,
                         "res": [sc.render.resolution_x, sc.render.resolution_y]}

with open(a.out, "w") as f:
    json.dump(rep, f, indent=1)
print("[PROBE2-WRITTEN]", a.out)
print(json.dumps({k: rep[k] for k in ("collections", "largest_images", "largest_meshes",
                                      "n_meshes_ge_20mb", "linked_ids", "object_types",
                                      "root_level_orphans")}, indent=1)[:3000])
