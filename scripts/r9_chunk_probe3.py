# D18 probe v3 (critique-driven): (a) survey modifier/constraint/shape-key/
# particle classes + cross-subtree references; (b) write() with a closure
# containing a MISSING-library linked image; (c) world write->reopen closure.
import bpy, sys, json, os, tempfile, argparse

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
p = argparse.ArgumentParser()
p.add_argument("--blend", required=True)
p.add_argument("--out", required=True)
a = p.parse_args(argv)

import subprocess
def mem_mb():
    try:
        s = subprocess.run(["sh", "-c", "cat /proc/meminfo | grep MemAvailable"],
                           capture_output=True, text=True).stdout
        return int(s.split()[1]) // 1024
    except Exception:
        return -1
print(f"[MEM] MemAvailable={mem_mb()}MB before open", flush=True)

bpy.ops.wm.open_mainfile(filepath=a.blend)
print(f"[MEM] MemAvailable={mem_mb()}MB after open", flush=True)

rep = {}

# ---------- (a) ID-class survey ----------
mod_types, con_types, n_sk, n_ps = {}, {}, 0, 0
gn_users = []
for o in bpy.data.objects:
    for m in o.modifiers:
        mod_types[m.type] = mod_types.get(m.type, 0) + 1
        if m.type == 'NODES':
            gn_users.append(o.name)
    for c in o.constraints:
        con_types[c.type] = con_types.get(c.type, 0) + 1
    if o.type == 'MESH' and o.data.shape_keys is not None:
        n_sk += 1
    if hasattr(o, "particle_systems"):
        n_ps += len(o.particle_systems)
rep["modifiers"] = mod_types
rep["constraints"] = con_types
rep["objects_with_shapekeys"] = n_sk
rep["particle_systems"] = n_ps
rep["gn_modifier_users"] = gn_users[:10]

# mesh co-users (same mesh datablock used by >1 object)
from collections import Counter
mesh_users = Counter(o.data.name for o in bpy.data.objects
                     if o.type == 'MESH' and o.data)
rep["mesh_couser_groups"] = {k: v for k, v in mesh_users.items() if v > 1}
rep["n_mesh_couser_groups"] = len(rep["mesh_couser_groups"])

# cross-subtree object references via modifiers/constraints/particles
# (subtree = parent-root family)
root_of = {}
for o in bpy.data.objects:
    r, s = o, set()
    while r.parent is not None and r.parent.name not in s:
        s.add(r.parent.name)
        r = r.parent
    root_of[o.name] = r.name

cross = []
for o in bpy.data.objects:
    refs = []
    for m in o.modifiers:
        for prop in ("object", "target_object", "source_object"):
            v = getattr(m, prop, None)
            if v is not None:
                refs.append((m.name, prop, v.name))
    for c in o.constraints:
        v = getattr(c, "target", None)
        if v is not None:
            refs.append((c.name, "target", v.name))
    for ps in getattr(o, "particle_systems", []):
        for gprop in ("instance_collection", "dupli_group"):
            g = getattr(ps.settings, gprop, None)
            if g is not None:
                refs.append((ps.name, gprop, g.name))
        io_ = getattr(ps.settings, "instance_object", None)
        if io_ is not None:
            refs.append((ps.name, "instance_object", io_.name))
    for mname, prop, tgt in refs:
        if root_of.get(o.name) != root_of.get(tgt):
            cross.append({"obj": o.name, "mod": mname, "prop": prop,
                          "target": tgt, "obj_root": root_of[o.name],
                          "tgt_root": root_of.get(tgt)})
rep["cross_subtree_refs"] = cross

# object/mesh/material name uniqueness (the .001 law inputs)
for cls, attr in (("objects", bpy.data.objects), ("meshes", bpy.data.meshes),
                  ("materials", bpy.data.materials), ("images", bpy.data.images),
                  ("node_groups", bpy.data.node_groups)):
    names = [d.name for d in attr]
    dupes = {n: c for n, c in Counter(names).items() if c > 1}
    rep[f"{cls}_n"] = len(names)
    rep[f"{cls}_dupes"] = dupes

# image classes (critique #12)
img_classes = {"packed": [], "file_unpacked": [], "linked": [], "other": []}
for im in bpy.data.images:
    if im.library is not None:
        img_classes["linked"].append(im.name)
    elif im.packed_file is not None:
        img_classes["packed"].append(im.name)
    elif im.source == 'FILE':
        img_classes["file_unpacked"].append({"name": im.name,
                                             "path": im.filepath[:60]})
    else:
        img_classes["other"].append({"name": im.name, "source": im.source})
rep["image_classes"] = {k: (len(v) if k != "file_unpacked" else v)
                        for k, v in img_classes.items()}
rep["image_classes"]["linked_names"] = img_classes["linked"][:8]
rep["image_classes"]["file_unpacked_n"] = len(img_classes["file_unpacked"])
rep["image_classes"]["file_unpacked_sample"] = img_classes["file_unpacked"][:6]

# ---------- (b) write() with a MISSING-library linked image in closure ----------
# find an object whose material uses a linked image
victim = None
for o in bpy.data.objects:
    if o.type != 'MESH' or not o.data:
        continue
    for mat in o.data.materials:
        if mat and mat.library is None and mat.use_nodes and mat.node_tree:
            for nd in mat.node_tree.nodes:
                if nd.type == 'TEX_IMAGE' and nd.image and nd.image.library is not None:
                    victim = (o, mat, nd.image)
                    break
        if victim:
            break
    if victim:
        break

tmp = tempfile.mkdtemp(prefix="d18d_")
if victim:
    o, mat, lim = victim
    rep["victim"] = {"obj": o.name, "mat": mat.name, "linked_img": lim.name,
                     "img_lib": lim.library.filepath[:60] if lim.library else None}
    f1 = os.path.join(tmp, "miss_lib.blend")
    try:
        bpy.data.libraries.write(f1, {o})
        rep["write_missing_lib"] = {"ok": True, "size": os.path.getsize(f1)}
        inv = {}
        with bpy.data.libraries.load(f1, link=False) as (src, _):
            for attr in ("objects", "meshes", "materials", "images", "node_groups"):
                inv[attr] = list(getattr(src, attr))
        rep["write_missing_lib_inventory"] = inv
    except Exception as e:
        rep["write_missing_lib"] = {"ok": False, "error": str(e)}
else:
    rep["victim"] = None

# ---------- (c) world write->reopen closure ----------
w = bpy.context.scene.world
f2 = os.path.join(tmp, "world.blend")
try:
    bpy.data.libraries.write(f2, {w})
    rep["world_write"] = {"ok": True, "size": os.path.getsize(f2)}
    with bpy.data.libraries.load(f2, link=False) as (src, _):
        rep["world_reopen"] = {"worlds": list(src.worlds),
                               "images": list(src.images),
                               "node_groups": list(src.node_groups)}
except Exception as e:
    rep["world_write"] = {"ok": False, "error": str(e)}

with open(a.out, "w") as f:
    json.dump(rep, f, indent=1)
print("[PROBE3-WRITTEN]", a.out)
print(json.dumps({k: rep[k] for k in
    ("modifiers", "constraints", "objects_with_shapekeys", "particle_systems",
     "n_mesh_couser_groups", "cross_subtree_refs", "image_classes",
     "victim", "write_missing_lib", "world_write", "world_reopen")},
    indent=1, default=str)[:4000])
