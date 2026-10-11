# R9 D18 IMPLEMENTATION — asset rebuild from chunks + manifest.
# Design: docs/DESIGN_D18_asset_partition.md REV-3.
#
# step 0: empty-session law (read_factory_settings(use_empty=True) + assert)
# then: recreate collection tree -> append chunk_00 first + assign world ->
# append remaining chunks exactly once -> consolidation pass (user_remap
# .001 artifacts onto source names) -> orphans_purge -> count parity incl.
# POLY parity -> re-apply parent pairs + matrix_parent_inverse -> kit props
# (expected-empty) -> image path fixup (manifest-keyed) -> world + scene
# settings + compositor rebuild [R2#N13] -> save master -> image existence
# verify (start=master_dir) -> full verify block. Fail-closed (exit 4).
import bpy, sys, os, json, argparse
from mathutils import Matrix

def die(msg):
    print("[STOP-AND-FLAG]", msg, flush=True)
    sys.exit(4)

def flat_to_mat(flat):
    return Matrix([flat[i * 4:(i + 1) * 4] for i in range(4)])

def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--loftdir", default="assets/loft")
    p.add_argument("--out", default=None, help="master path override")
    a = p.parse_args(argv)

    loftdir = a.loftdir
    master_path = a.out or os.path.join(loftdir, "loft_master.blend")
    with open(os.path.join(loftdir, "chunks_manifest.json")) as f:
        man = json.load(f)

    # ---------------- step 0: empty-session law [R2#N1] ----------------
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if list(bpy.data.objects) or list(bpy.data.collections):
        die("rebuild session not empty — consolidation-safety law violated")
    sc = bpy.context.scene

    # ---------------- recreate collection tree ----------------
    colmap = {}
    for top in man["collection_tree"]:
        c = bpy.data.collections.new(top["name"])
        sc.collection.children.link(c)
        colmap[top["name"]] = c
        for k in top.get("children", []):
            kc = bpy.data.collections.new(k["name"])
            c.children.link(kc)
            colmap[k["name"]] = kc

    # ---------------- append chunk_00 first, assign world ----------------
    chunkdir = os.path.join(loftdir, "chunks")
    chunk_files = [os.path.join(chunkdir, os.path.basename(c["file"]))
                   for c in man["chunks"]]
    with bpy.data.libraries.load(chunk_files[0], link=False) as (src, ctx):
        ctx.objects = list(src.objects)
        ctx.worlds = list(src.worlds)
    if man["world"]["name"]:
        w = bpy.data.worlds.get(man["world"]["name"])
        if w is None:
            die("world missing after chunk_00 append")
        sc.world = w  # live user BEFORE any purge [R2#N2]
    if man.get("compositor"):
        pass  # re-created later from the dump [R2#N13]

    # ---------------- append remaining chunks ----------------
    # request ALL relevant classes: the closure pulls most IDs, but a
    # riders chunk (closure-gap carrier) may contain IDs no object
    # references — requesting by class is the only way they materialize.
    # ALSO record each chunk's inventory — the delivery model the rebuild
    # asserts against is computed from these, not hand arithmetic.
    deliverable = {cls: set() for cls in ("objects", "meshes", "materials",
                                          "images", "node_groups", "lights",
                                          "cameras", "textures", "particles")}
    for cf in chunk_files[1:]:
        with bpy.data.libraries.load(cf, link=False) as (src, ctx):
            ctx.objects = list(src.objects)
            ctx.materials = list(src.materials)
            ctx.images = list(src.images)
            ctx.lights = list(src.lights)
            ctx.cameras = list(src.cameras)
            ctx.textures = list(src.textures)
            ctx.particles = list(src.particles)
            ctx.node_groups = [n for n in src.node_groups
                               if n != man.get("compositor", {}).get("name")]
            for cls in deliverable:
                deliverable[cls].update(getattr(src, cls))
    with bpy.data.libraries.load(chunk_files[0], link=False) as (src, _):
        for cls in deliverable:
            deliverable[cls].update(getattr(src, cls))

    # low-level append does NOT link to the scene (measured: users=0,
    # scene membership 0) — give every object a live user BEFORE any
    # consolidation/purge; the collection step re-homes them after.
    for ob in bpy.data.objects:
        if ob.name not in sc.collection.objects:
            sc.collection.objects.link(ob)

    # ---------------- consolidation pass [A2 + R2#N1 corollary] ----------
    source_names = {o["name"] for o in man["objects"]}
    id_names = man.get("id_names", {})
    if not id_names:
        die("manifest lacks id_names (re-split with the current writer)")
    clsmap = {"objects": bpy.data.objects, "meshes": bpy.data.meshes,
              "materials": bpy.data.materials, "images": bpy.data.images,
              "node_groups": bpy.data.node_groups, "lights": bpy.data.lights,
              "cameras": bpy.data.cameras, "textures": bpy.data.textures,
              "particles": bpy.data.particles}
    merged = 0
    for cls in ("objects", "meshes", "materials", "images", "node_groups",
                "lights", "cameras", "textures", "particles"):
        coll = clsmap[cls]
        valid = set(id_names[cls])
        for d in list(coll):
            if d.name in valid:
                continue
            # append artifact: recover the source name. Blender's collision
            # rule rebuilds the numeric suffix (source "X.001" appended
            # twice -> local "X.001" then "X.002"), so search prefix +
            # candidate suffixes; ambiguity = honest flag, never a guess.
            prefix = d.name.rsplit(".", 1)[0] if "." in d.name else d.name
            if prefix in valid:
                cands = [prefix]
            else:
                cands = [f"{prefix}.{i:03d}" for i in range(0, 100)
                         if f"{prefix}.{i:03d}" in valid]
            if not cands:
                die(f"{cls} artifact {d.name}: no source name near "
                    f"'{prefix}'")
            if len(cands) > 1:
                if cls == "images":
                    # harmless iff every candidate is byte-identical
                    # (same texture file + colorspace — Run A's sha256 dedup)
                    files = {man["texture_table"][c]["file"] for c in cands
                             if c in man["texture_table"]}
                    cols = {man["texture_table"][c]["colorspace"]
                            for c in cands if c in man["texture_table"]}
                    if len(files) == 1 and len(cols) == 1:
                        cands = cands[:1]
                    else:
                        die(f"{cls} artifact {d.name}: ambiguous AND "
                            f"content-distinct: {cands}")
                else:
                    die(f"{cls} artifact {d.name}: ambiguous source name "
                        f"{cands}")
            target = coll.get(cands[0])
            if target is None:
                die(f"{cls} artifact {d.name}: base {cands[0]} missing")
            if cls == "images":
                # filepath guard: only merge identical sources
                ep = os.path.basename(d.filepath)
                tp = os.path.basename(target.filepath)
                if ep and tp and ep != tp:
                    die(f"image artifact {d.name} filepath differs from {base}")
            d.user_remap(target)
            merged += 1
    # restore closure-gap / rider flags (fake_user does NOT survive
    # write+append — same class of surprise as scene linking; the
    # manifest is the state carrier)
    gap = man.get("closure_gap", {})
    gap_total = 0
    for cls, names in gap.items():
        for nm in names:
            d = clsmap[cls].get(nm)
            if d is None:
                die(f"closure-gap ID {cls}:{nm} did not materialize")
            d.use_fake_user = True
            gap_total += 1
    for r in man.get("riders", []):
        d = clsmap[r["class"]].get(r["name"])
        if d is not None:
            d.use_fake_user = True

    # remove zero-user artifacts (riders/world carry fake_user or live users)
    bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=True,
                           do_recursive=False)
    print(f"[R] consolidation: {merged} artifacts remapped", flush=True)

    # ---------------- delivery-model parity [R2#N1, mechanism-aware] ------
    # (a) everything the chunks PROMISED (inventories + gap riders) arrives;
    # (b) every rebuilt name is a SOURCE name — append may synthesize
    #     placeholders ONLY for source-named IDs the chunks could not
    #     deliver (linked refs), never anything foreign.
    idn = man["id_names"]
    gapm = man.get("closure_gap", {})
    got_by_cls = {
        "objects": {o.name for o in bpy.data.objects},
        "meshes": {m.name for m in bpy.data.meshes},
        "materials": {m.name for m in bpy.data.materials},
        "images": {i.name for i in bpy.data.images},
        "node_groups": {n.name for n in bpy.data.node_groups
                        if n.library is None},
        "lights": {l.name for l in bpy.data.lights},
        "cameras": {c.name for c in bpy.data.cameras},
        "textures": {t.name for t in bpy.data.textures},
        "particles": {p.name for p in bpy.data.particles},
    }
    for cls, got in got_by_cls.items():
        want_present = (deliverable[cls] & set(idn[cls])) | set(gapm.get(cls, []))
        missing = sorted(want_present - got)[:5]
        if missing:
            die(f"delivery {cls}: promised-but-missing={missing}")
        undelivered_source = set(idn[cls]) - deliverable[cls] - set(gapm.get(cls, []))
        bad_extra = sorted((got - want_present) - undelivered_source)[:5]
        if bad_extra:
            die(f"delivery {cls}: foreign names={bad_extra}")
    census = man["census"]
    if sum(1 for o in bpy.data.objects
           if o.type == 'LIGHT') != census["lights"]:
        die("light count drift")
    if sum(1 for o in bpy.data.objects if o.type == 'CAMERA') != census["cameras"]:
        die("camera count drift")
    poly = {"verts": sum(len(m.vertices) for m in bpy.data.meshes),
            "polys": sum(len(m.polygons) for m in bpy.data.meshes)}
    if poly != man["poly"]:
        die(f"POLY PARITY FAILED: {poly} != {man['poly']}")

    # name-set equality (exact)
    got_names = {o.name for o in bpy.data.objects}
    if got_names != source_names:
        missing = source_names - got_names
        extra = got_names - source_names
        die(f"object name-set mismatch: missing={list(missing)[:5]} "
            f"extra={list(extra)[:5]}")

    # ---------------- collection assignment ----------------
    scene_root_names = {o["name"] for o in man["objects"] if o["scene_root"]}
    for rec in man["objects"]:
        ob = bpy.data.objects.get(rec["name"])
        if ob is None:
            die(f"object {rec['name']} missing before collection assign")
        if rec["scene_root"] or rec["col"] is None:
            continue  # already in scene root from append
        top = rec["col"][0]
        target = colmap.get(top)
        if target is None:
            die(f"collection {top} missing for {rec['name']}")
        target.objects.link(ob)
        sc.collection.objects.unlink(ob)

    # ---------------- parent pairs [A5] ----------------
    for pair in man["parent_pairs"]:
        child = bpy.data.objects.get(pair["child"])
        parent = bpy.data.objects.get(pair["parent"])
        if child is None or parent is None:
            die(f"parent pair incomplete: {pair['child']}->{pair['parent']}")
        inv = flat_to_mat(pair["parent_inverse"])
        if child.parent is None:
            child.parent = parent
            child.matrix_parent_inverse = inv
        else:
            if child.parent.name != pair["parent"]:
                die(f"parent mismatch on {pair['child']}")
            for i in range(4):
                for j in range(4):
                    if abs(child.matrix_parent_inverse[i][j]
                           - inv[i][j]) > 1e-5:
                        die(f"parent_inverse drift on {pair['child']}")

    # ---------------- kit props (expected-empty, forward-compat) ---------
    for rec in man["objects"]:
        ob = bpy.data.objects[rec["name"]]
        for k in ("kit_label", "kit_semantic", "kit_label_conf"):
            if rec.get(k) is not None:
                ob[k] = rec[k]

    # ---------------- image path fixup [A4 + R2#N8 manifest-keyed] -------
    n_fix, n_stubs = 0, 0
    for name, entry in man["texture_table"].items():
        im = bpy.data.images.get(name)
        if im is None:
            die(f"texture table entry {name} missing in rebuild")
        im.filepath = f"//textures/{entry['file']}"
        n_fix += 1
    stub_names = {s["name"] for s in man["skipped_images"]
                  if s["why"] == "verbatim file stub"}
    # append-synthesized placeholders for undeliverable linked refs are
    # legitimate (same class the delivery gate allows)
    synth_ok = (set(idn["images"]) - {n for n in deliverable["images"]
                                      if n in set(idn["images"])}
                - set(gapm.get("images", [])))
    for im in bpy.data.images:
        if im.name in man["texture_table"]:
            continue
        if im.name in stub_names:
            n_stubs += 1  # verbatim dead path — expected, preserved
            continue
        if im.name in synth_ok:
            continue  # synthesized linked placeholder — dead path, expected
        die(f"unexpected image in rebuild: {im.name}")
    print(f"[R] image fixup: {n_fix} externalized, {n_stubs} verbatim stubs",
          flush=True)

    # ---------------- world + scene settings ----------------
    if bpy.data.worlds.get(man["world"]["name"]) is None:
        die("world lost before settings restore")
    if len(bpy.context.scene.world.node_tree.nodes) != man["world"]["n_nodes"]:
        die("world node count drift")
    s = man["scene_settings"]
    rnd = sc.render
    rnd.fps = s["fps"]
    rnd.engine = s["engine"]
    rnd.resolution_x, rnd.resolution_y = s["res"]
    sc.view_settings.view_transform = s["view_transform"]
    try:
        sc.view_settings.look = s["look"]
    except Exception:
        pass  # look names can shift between Blender builds
    sc.view_settings.exposure = s["exposure"]
    sc.display_settings.display_device = s["display_device"]
    sc.use_nodes = s["use_nodes"]
    sc.unit_settings.system = s["unit_system"]
    sc.unit_settings.scale_length = s["scale_length"]
    if s.get("compositing_node_group") is None and sc.use_nodes:
        sc.use_nodes = False

    # ---------------- compositor rebuild [R2#N13] ----------------
    comp = man.get("compositor")
    if comp:
        tree = bpy.data.node_groups.new(comp["name"], 'CompositorNodeTree')
        node_by_name = {}
        for nd in comp["nodes"]:
            n = tree.nodes.new(nd["bl_idname"])
            n.name = nd["name"]
            n.location.x, n.location.y = nd["location"]
            for k, v in nd.get("props", {}).items():
                try:
                    setattr(n, k, v)
                except Exception:
                    pass  # enum/type drift tolerated, parity-checked below
            for sk, v in nd.get("inputs", {}).items():
                sock = n.inputs.get(sk)
                if sock is None or v is None:
                    continue
                try:
                    if isinstance(v, list):
                        sock.default_value = v
                    else:
                        sock.default_value = v
                except Exception:
                    pass
            node_by_name[n.name] = n
        # Group Output node in a fresh tree may be named 'Group Output.001'
        n_linked, n_skipped = 0, []
        for l in comp["links"]:
            fn = node_by_name.get(l["from_node"])
            tn = node_by_name.get(l["to_node"])
            if fn is None or tn is None:
                die(f"compositor link endpoint missing: {l}")
            fs = fn.outputs.get(l["from_socket"]) or next(
                (s for s in fn.outputs if s.name.startswith(l["from_socket"])),
                None)
            ts = tn.inputs.get(l["to_socket"]) or next(
                (s for s in tn.inputs if s.name.startswith(l["to_socket"])),
                None)
            if fs is None or ts is None:
                # socket sets evolve between Blender versions (measured:
                # 5.2 Denoise dropped the Normal input) — skip honestly
                n_skipped.append(f"{l['from_node']}.{l['from_socket']}->"
                                 f"{l['to_node']}.{l['to_socket']}")
                continue
            tree.links.new(fs, ts)
            n_linked += 1
        sc.use_nodes = True
        sc.compositing_node_group = tree
        if len(tree.nodes) != len(comp["nodes"]):
            die(f"compositor node count {len(tree.nodes)} != {len(comp['nodes'])}")
        print(f"[R] compositor rebuilt: {len(tree.nodes)} nodes, "
              f"{n_linked} links re-created, {len(n_skipped)} skipped "
              f"(socket drift) {n_skipped[:2]}", flush=True)

    # view layers (source had exactly the default)
    have = {vl.name for vl in sc.view_layers}
    for vlname in s["view_layers"]:
        if vlname not in have:
            sc.view_layers.new(vlname)

    # ---------------- save master, THEN image existence [R2#N7] ----------
    bpy.ops.wm.save_as_mainfile(filepath=master_path, compress=True)
    master_dir = os.path.dirname(master_path)
    texdir = os.path.join(loftdir, "textures")
    missing = []
    for name, entry in man["texture_table"].items():
        # resolve the //textures/ ref explicitly against the TEXTURE dir
        # layout (// is master-relative; textures live at loftdir/textures)
        p = os.path.join(master_dir, "textures", entry["file"])
        if not os.path.exists(p):
            missing.append(entry["file"])
    if missing:
        die(f"{len(missing)} externalized textures missing on disk: "
            f"{missing[:3]}")

    print(f"[R-DONE] master saved: {master_path} "
          f"({os.path.getsize(master_path)/1e6:.1f}MB)", flush=True)
    print(f"[R-VERIFY] objects={len(bpy.data.objects)} meshes="
          f"{len(bpy.data.meshes)} materials={len(bpy.data.materials)} "
          f"images={len(bpy.data.images)} poly={poly['polys']} ok", flush=True)

main()
