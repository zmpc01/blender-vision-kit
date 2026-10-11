# D18 probe 3b: GN node-tree INTERNAL object/collection references
# (modifier-level survey missed node-graph ID deps). Also checks the
# particle system's instance targets and modifier IDProp sockets.
import bpy, sys, json, os, argparse

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
p = argparse.ArgumentParser()
p.add_argument("--blend", required=True)
p.add_argument("--out", required=True)
a = p.parse_args(argv)

bpy.ops.wm.open_mainfile(filepath=a.blend)

def root_name(o):
    r = o
    while r.parent is not None:
        r = r.parent
    return r.name

rep = {"ng_scans": [], "mod_socket_refs": [], "particle_refs": []}

for ng in bpy.data.node_groups:
    if ng.library is not None:
        continue
    refs = []
    for nd in ng.nodes:
        for inp in nd.inputs:
            v = getattr(inp, "default_value", None)
            if hasattr(v, "name") and hasattr(v, "library") and v is not None:
                refs.append({"node": nd.name, "socket": inp.name,
                             "target": v.name, "is_linked_id": True})
    if refs:
        rep["ng_scans"].append({"ng": ng.name, "refs": refs[:10],
                                "n_refs": len(refs)})

for o in bpy.data.objects:
    for m in o.modifiers:
        if m.type != 'NODES':
            continue
        # ID-prop sockets (object/collection inputs stored on the modifier)
        try:
            for k, v in m.items():
                if hasattr(v, "name") and hasattr(v, "library"):
                    rep["mod_socket_refs"].append(
                        {"obj": o.name, "mod": m.name, "key": k, "target": v.name})
        except TypeError:
            rep["mod_socket_refs"].append(
                {"obj": o.name, "mod": m.name, "key": "UNAVAILABLE",
                 "target": "bpy 5.2: NodesModifier idprops not enumerable"})
    for ps in getattr(o, "particle_systems", []):
        st = ps.settings
        for gprop in ("instance_collection", "dupli_group"):
            g = getattr(st, gprop, None)
            if g is not None:
                rep["particle_refs"].append(
                    {"obj": o.name, "prop": gprop, "target": g.name,
                     "n_objects": len(g.all_objects) if hasattr(g, "all_objects") else -1})
        io_ = getattr(st, "instance_object", None)
        if io_ is not None:
            rep["particle_refs"].append(
                {"obj": o.name, "prop": "instance_object", "target": io_.name})

with open(a.out, "w") as f:
    json.dump(rep, f, indent=1)
print("[PROBE3B-WRITTEN]", a.out)
print(json.dumps(rep, indent=1, default=str)[:2500])
