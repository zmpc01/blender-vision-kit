# R9 D18 IMPLEMENTATION — asset partition, Run A (texture externalization)
# and Run B (chunk writing). Design: docs/DESIGN_D18_asset_partition.md REV-3.
#
# Run A: open the packed original -> export every packed image to
#        assets/loft/textures/<safe_name> (sha256 dedup, sanitized names) ->
#        flip to FILE-source //textures/<file> (correct at loft_ext's own
#        location) -> save assets/loft/loft_ext.blend (compress) -> report.
# Run B: open loft_ext -> re-point images to //../textures/<file> (the
#        chunk-baked form) -> pre-flight asserts -> user-less rider
#        enumeration -> bin-pack root subtrees (co-user merged) -> write
#        chunk_00 (scene: orphans+camera+world+riders) + chunk files ->
#        real-size gate <90MB -> mutation guard -> chunks_manifest.json.
#
# Both phases fail-closed: any invariant violation = exit 4 (STOP-AND-FLAG).
import bpy, sys, os, json, re, hashlib, argparse, subprocess

def mem_mb():
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemAvailable"):
                    return int(line.split()[1]) // 1024
    except Exception:
        pass
    return -1

def die(msg):
    print("[STOP-AND-FLAG]", msg, flush=True)
    sys.exit(4)

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def mesh_bytes(m):
    return len(m.vertices) * 32 + len(m.polygons) * 40 + len(m.loops) * 20

def safe_name(name):
    """[R2#N8] sanitizer: ext preserved, charset [A-Za-z0-9._ -], len<=120."""
    base, ext = os.path.splitext(name)
    base = re.sub(r"[^A-Za-z0-9._ -]", "_", base)[:110].strip() or "tex"
    ext = re.sub(r"[^A-Za-z0-9.]", "", ext)[:10]
    return base + ext

def root_name(o):
    r = o
    while r.parent is not None:
        r = r.parent
    return r

# ---------------------------------------------------------------- PHASE A
def phase_a(src, outdir):
    if mem_mb() < 2400:
        die(f"Run A mem guard: MemAvailable={mem_mb()}MB < 2400MB")
    print(f"[MEM] {mem_mb()}MB available before open", flush=True)
    bpy.ops.wm.open_mainfile(filepath=src)

    texdir = os.path.join(outdir, "textures")
    os.makedirs(texdir, exist_ok=True)
    loftdir = os.path.join(outdir)  # assets/loft/

    table = {}      # datablock name -> entry
    by_hash = {}    # sha256 -> filename (dedup)
    used_lower = {} # case-insensitive name registry
    skipped = []

    for im in bpy.data.images:
        if im.library is not None:
            skipped.append({"name": im.name, "why": "library-linked"})
            continue
        if im.packed_file is None:
            if im.source == 'FILE':
                skipped.append({"name": im.name, "why": "verbatim file stub",
                                "path": im.filepath[:100]})
            else:
                skipped.append({"name": im.name, "why": f"source={im.source}"})
            continue
        data = im.packed_file.data
        if not data:
            die(f"packed image {im.name} has no data")
        h = hashlib.sha256(data).hexdigest()
        if h in by_hash:
            fn = by_hash[h]
        else:
            fn = safe_name(im.name)
            # case-insensitive collision -> hash suffix
            key = fn.lower()
            if key in used_lower:
                stem, ext = os.path.splitext(fn)
                fn = f"{stem}_{h[:6]}{ext}"
            used_lower[fn.lower()] = True
            path = os.path.join(texdir, fn)
            with open(path, "wb") as f:
                f.write(data)
            by_hash[h] = fn
        table[im.name] = {"file": fn, "sha256": h, "bytes": len(data),
                          "colorspace": im.colorspace_settings.name}
        # flip to FILE-source, //textures/<file> — correct at loft_ext's own
        # location (assets/loft/) [R2#N5 flip-twice]
        im.filepath = f"//textures/{fn}"
        im.source = 'FILE'
        im.unpack(method='REMOVE')

    print(f"[A] exported {len(table)} packed images, "
          f"{len(by_hash)} unique files, skipped {len(skipped)}", flush=True)

    src_sha = sha256_file(src)
    ext_path = os.path.join(loftdir, "loft_ext.blend")
    # the vendor file ships with autopack ON — save would re-pack the
    # freshly-flipped FILE-source images from the ORIGINAL file's //
    # location and abort. Autopack stays off for the whole pipeline.
    bpy.data.use_autopack = False
    try:
        bpy.ops.wm.save_as_mainfile(filepath=ext_path, compress=True)
    except Exception as e:
        die(f"compressed save of loft_ext failed: {e}")
    print(f"[A] loft_ext.blend saved: {os.path.getsize(ext_path)/1e6:.1f}MB",
          flush=True)

    report = {
        "source": src, "source_sha256": src_sha,
        "loft_ext": ext_path,
        "texture_table": table,
        "skipped_images": skipped,
        "n_textures": len(table), "n_texture_files": len(by_hash),
        "total_texture_bytes": sum(e["bytes"] for e in table.values()),
    }
    rp = os.path.join(outdir, "..", "..", "output", "r9", "run_a_report.json")
    os.makedirs(os.path.dirname(rp), exist_ok=True)
    with open(rp, "w") as f:
        json.dump(report, f, indent=1)
    with open(os.path.join(loftdir, "texture_table.json"), "w") as f:
        json.dump(table, f, indent=1)
    print("[A-DONE]", flush=True)

# ---------------------------------------------------------------- PHASE B
def phase_b(outdir):
    if mem_mb() < 2400:
        die(f"Run B mem guard: MemAvailable={mem_mb()}MB < 2400MB")
    ext_path = os.path.join(outdir, "loft_ext.blend")
    with open(os.path.join(outdir, "texture_table.json")) as f:
        table = json.load(f)
    with open(os.path.join(outdir, "..", "..", "output", "r9",
                           "run_a_report.json")) as f:
        report_a = json.load(f)

    bpy.ops.wm.open_mainfile(filepath=ext_path)
    print(f"[MEM] {mem_mb()}MB after loft_ext open", flush=True)

    # [R2#N5] flip-twice: re-point all externalized images to the chunk-baked form
    n_repoint = 0
    for name, entry in table.items():
        im = bpy.data.images.get(name)
        if im is None:
            die(f"texture table name {name} missing in loft_ext session")
        if im.library is not None:
            die(f"texture table name {name} became linked?!")
        im.filepath = f"//../textures/{entry['file']}"
        n_repoint += 1
    print(f"[B] re-pointed {n_repoint} images to //../textures/", flush=True)

    # ---------------- pre-flight asserts (survey invariants) ----------------
    objs = list(bpy.data.objects)
    census = {
        "objects": len(objs), "meshes": len(bpy.data.meshes),
        "materials": len(bpy.data.materials), "images": len(bpy.data.images),
        "node_groups_local": sum(1 for n in bpy.data.node_groups
                                 if n.library is None),
        "node_groups_linked": sum(1 for n in bpy.data.node_groups
                                  if n.library is not None),
        "lights": sum(1 for o in objs if o.type == 'LIGHT'),
        "cameras": sum(1 for o in objs if o.type == 'CAMERA'),
        "n_parented": sum(1 for o in objs if o.parent is not None),
    }
    if census["objects"] != 1225:
        die(f"object census drift: {census['objects']} != 1225")
    if census["meshes"] != 1184 or census["materials"] != 180:
        die(f"mesh/material census drift: {census}")
    if census["lights"] != 4 or census["cameras"] != 1:
        die(f"light/camera census drift: {census}")
    if any(c for o in objs for c in o.constraints):
        die("constraints appeared (survey said none)")
    if any(o.type == 'MESH' and o.data.shape_keys is not None
           for o in objs):
        die("shape keys appeared (survey said none)")
    sc = bpy.context.scene
    # N10 (as amended after the flag fired live): the loft DOES carry a
    # compositor tree ("Compositing Nodetree", 5 nodes, scene-referenced).
    # It is handled, not skipped: written into chunk_00, restored +
    # asserted by the rebuild.
    comp_group = sc.compositing_node_group
    # LOCAL-ID name uniqueness [R2#N9]
    for cls in ("objects", "meshes", "materials"):
        names = [d.name for d in getattr(bpy.data, cls) if d.library is None]
        if len(names) != len(set(names)):
            die(f"local {cls} names not unique")
    # texture coverage cross-check
    n_ext = sum(1 for im in bpy.data.images
                if im.library is None and im.filepath.startswith("//../textures/"))
    if n_ext != len(table):
        die(f"externalized image count {n_ext} != table {len(table)}")

    # light census pattern [R2#N3]: 2 scene-root orphan lights + 2 elsewhere
    scene_root = {o.name for o in sc.collection.objects}
    root_lights = [o.name for o in objs
                   if o.type == 'LIGHT' and o.name in scene_root]
    if len(root_lights) != 2:
        die(f"expected 2 scene-root orphan lights, got {root_lights}")

    # ---------------- user-less riders [R2#N2] ----------------
    riders = []
    for cls in ("materials", "meshes", "images", "node_groups"):
        for d in getattr(bpy.data, cls):
            if d.library is not None or d.users > 0 or d.use_fake_user:
                continue
            d.use_fake_user = True
            riders.append({"class": cls, "name": d.name})
    print(f"[B] user-less riders: {len(riders)}", flush=True)

    # ---------------- bin packing [A1 + A6 + R2#N11] ----------------
    # co-user mesh groups -> union-find over roots
    parent = {}
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    roots = [o for o in objs if o.parent is None]
    for r in roots:
        parent[r.name] = r.name
    mesh_roots = {}
    for o in objs:
        if o.type == 'MESH' and o.data is not None:
            r = root_name(o).name
            mesh_roots.setdefault(o.data.name, set()).add(r)
    for data_name, rs in mesh_roots.items():
        rs = list(rs)
        for x in rs[1:]:
            union(rs[0], x)

    units = {}  # root-name -> subtree object list
    subtree_objs = {r.name: [] for r in roots}
    for o in objs:
        subtree_objs[root_name(o).name].append(o)
    unit_est = {}
    for rname, ol in subtree_objs.items():
        est = sum(mesh_bytes(o.data) for o in ol
                  if o.type == 'MESH' and o.data) * 1.5
        if est < 0:
            die("negative unit estimate")
        units[rname] = ol
        unit_est[rname] = est
    total_est = sum(unit_est.values())
    if total_est <= 0:
        die(f"packer self-total assert failed: {total_est}")

    # merge via union-find (co-user groups)
    merged = {}
    for rname in subtree_objs:
        key = find(rname)
        merged.setdefault(key, []).append(rname)

    bin_units = []
    for key, members in merged.items():
        ol = [o for m in members for o in subtree_objs[m]]
        est = sum(unit_est[m] for m in members)
        bin_units.append({"members": members, "objs": ol, "est": est})
    bin_units.sort(key=lambda u: -u["est"])

    BUDGET = 60e6
    bins = []
    for u in bin_units:
        for b in bins:
            if b["est"] + u["est"] <= BUDGET:
                b["units"].extend(u["members"])
                b["objs"].extend(u["objs"])
                b["est"] += u["est"]
                break
        else:
            bins.append({"units": list(u["members"]), "objs": list(u["objs"]),
                         "est": u["est"]})
    bins.sort(key=lambda b: -b["est"])
    print(f"[B] packing: {len(roots)} roots -> {len(bin_units)} units -> "
          f"{len(bins)} bins (est total {total_est/1e6:.0f}MB)", flush=True)

    # ---------------- chunk_00 (scene) [R2#N3] ----------------
    cam = [o for o in objs if o.type == 'CAMERA']
    if len(cam) != 1:
        die(f"expected exactly 1 camera, got {len(cam)}")
    scene_set = [o for o in objs if o.name in root_lights] + cam
    world = sc.world
    if world is None:
        die("scene has no world")
    chunk00_ids = set(scene_set) | {world}
    # [R2#N13] compositor group does NOT ride chunks: scene-owned
    # CompositorNodeTree IDs drag the whole Scene through write()'s
    # closure (measured 3 ways: direct, severed-user, copy). It is
    # dumped to the manifest and re-created by the rebuild.
    chunk00_ids |= {d for cls in ("materials", "meshes", "images", "node_groups")
                    for d in getattr(bpy.data, cls)
                    if d.library is None and d.use_fake_user}

    # ---------------- write chunks ----------------
    chunkdir = os.path.join(outdir, "chunks")
    os.makedirs(chunkdir, exist_ok=True)
    counts_before = {cls: len(list(getattr(bpy.data, cls)))
                     for cls in ("objects", "meshes", "materials", "images",
                                 "node_groups", "worlds", "lights", "cameras")}
    fake_flags = {(cls, d.name): d.use_fake_user
                  for cls in ("materials", "meshes", "images", "node_groups")
                  for d in getattr(bpy.data, cls)}

    chunks = []
    GATE = 90e6

    def write_chunk(fname, ids, label):
        path = os.path.join(chunkdir, fname)
        bpy.data.libraries.write(path, ids, compress=True)
        size = os.path.getsize(path)
        if size > GATE:
            die(f"chunk {fname} {size/1e6:.1f}MB > 90MB gate "
                f"({label}) — operator re-bin required [R2#N11]")
        chunks.append({"file": f"chunks/{fname}", "bytes": size,
                       "label": label})
        print(f"[B] wrote {fname}: {size/1e6:.1f}MB ({len(ids)} top-ids)",
              flush=True)

    write_chunk("loft_chunk_00_scene.blend", chunk00_ids, "scene")

    for i, b in enumerate(bins, start=1):
        write_chunk(f"loft_chunk_{i:02d}.blend", set(b["objs"]),
                    "bins:" + ",".join(b["units"][:3]) +
                    ("…" if len(b["units"]) > 3 else ""))

    # mutation guard [R2#N12]
    for cls, n in counts_before.items():
        now = len(list(getattr(bpy.data, cls)))
        if now != n:
            die(f"mutation guard: {cls} {n} -> {now} during writes")

    # ---------------- closure-gap riders (N2 v2, self-verifying) ----------
    # write() walks SOME edges only — an ID can have users yet be
    # unreachable from every chunk (measured: 1 material). Inventory the
    # WRITTEN chunk files, diff against source locals, ship the gap.
    reachable = {cls: set() for cls in ("objects", "meshes", "materials",
                                        "images", "node_groups")}
    for c in chunks:
        path = os.path.join(chunkdir, os.path.basename(c["file"]))
        with bpy.data.libraries.load(path, link=False) as (src, _):
            for cls in reachable:
                reachable[cls].update(getattr(src, cls))
    locals_by_cls = {
        "objects": [o for o in bpy.data.objects],
        "meshes": [m for m in bpy.data.meshes if m.library is None],
        "materials": [m for m in bpy.data.materials if m.library is None],
        "images": [i for i in bpy.data.images if i.library is None],
        "node_groups": [n for n in bpy.data.node_groups
                        if n.library is None],
    }
    gap = {}
    for cls, ids in locals_by_cls.items():
        miss = []
        for d in ids:
            if d.name in reachable[cls]:
                continue
            # runtime images are never written or expected (parity 130
            # excludes them); the scene-owned compositor tree is
            # un-writable [R2#N13] and is re-created by the rebuild
            if cls == "images" and d.source in ('RENDER_RESULT', 'VIEWER'):
                continue
            if cls == "node_groups" and d is comp_group:
                continue
            miss.append(d.name)
        if miss:
            gap[cls] = miss
    riders_chunk = None
    if gap:
        print(f"[B] closure gap: " +
              " ".join(f"{cls}={len(names)}" for cls, names in gap.items()),
              flush=True)
        for cls, names in gap.items():
            print(f"[B]   gap {cls}: {names[:8]}{'…' if len(names) > 8 else ''}",
                  flush=True)
        gap_ids = set()
        for cls, names in gap.items():
            for nm in names:
                d = next(x for x in locals_by_cls[cls] if x.name == nm)
                d.use_fake_user = True
                gap_ids.add(d)
        riders_chunk = {"file": "chunks/loft_chunk_13_riders.blend"}
        write_chunk("loft_chunk_13_riders.blend", gap_ids,
                    "closure-gap riders")
        # verify the gap is now closed
        with bpy.data.libraries.load(
                os.path.join(chunkdir, "loft_chunk_13_riders.blend"),
                link=False) as (src, _):
            for cls, names in gap.items():
                got = set(getattr(src, cls))
                miss2 = [n for n in names if n not in got]
                if miss2:
                    die(f"riders chunk failed to carry {cls}: {miss2}")
        print(f"[B] closure-gap riders: {sum(len(v) for v in gap.values())} "
              f"IDs in loft_chunk_13_riders.blend", flush=True)

    # ---------------- manifest ----------------
    scene_root = {o.name for o in sc.collection.objects}
    col_path = {}
    def walk(c, path):
        for o in c.objects:
            col_path[o.name] = path + [c.name]
        for k in c.children:
            walk(k, path + [c.name])
    for c in sc.collection.children:
        walk(c, [])

    def flat16(m):
        return [round(v, 6) for row in m for v in row]

    parent_pairs = []
    for o in objs:
        if o.parent is not None:
            parent_pairs.append({"child": o.name, "parent": o.parent.name,
                                 "parent_inverse": flat16(
                                     o.matrix_parent_inverse)})

    obj_records = []
    for o in objs:
        obj_records.append({
            "name": o.name, "type": o.type,
            "col": col_path.get(o.name),
            "scene_root": o.name in scene_root,
            "parent": o.parent.name if o.parent is not None else None,
            "kit_label": o.get("kit_label"),
            "kit_semantic": o.get("kit_semantic"),
            "kit_label_conf": o.get("kit_label_conf"),
        })
    poly = {"verts": sum(len(m.vertices) for m in bpy.data.meshes),
            "polys": sum(len(m.polygons) for m in bpy.data.meshes)}
    settings = {
        "fps": sc.render.fps, "engine": sc.render.engine,
        "res": [sc.render.resolution_x, sc.render.resolution_y],
        "view_transform": sc.view_settings.view_transform,
        "look": sc.view_settings.look, "exposure": sc.view_settings.exposure,
        "display_device": sc.display_settings.display_device,
        "use_nodes": sc.use_nodes,
        "compositing_node_group": (sc.compositing_node_group.name
                                   if sc.compositing_node_group else None),
        "unit_system": sc.unit_settings.system,
        "scale_length": sc.unit_settings.scale_length,
        "view_layers": [vl.name for vl in sc.view_layers],
    }
    linked_dropped = [{"class": "images" if im.library else "?", "name": d.name}
                      for d in list(bpy.data.images) + list(bpy.data.node_groups)
                      if d.library is not None]

    # [R2#N13] generic compositor-tree dump (simple types only)
    def dump_socket_val(s):
        v = getattr(s, "default_value", None)
        if v is None:
            return None
        if hasattr(v, "__len__"):
            try:
                return [round(float(x), 6) for x in v]
            except Exception:
                return None
        if isinstance(v, (int, float, bool, str)):
            return v
        return None

    def dump_node_props(n):
        props = {}
        for p in n.bl_rna.properties:
            pid = p.identifier
            if pid.startswith("bl_") or pid in ("rna_type", "name", "label",
                                                 "location", "width", "height",
                                                 "color", "select", "mute",
                                                 "show_options", "show_preview",
                                                 "show_toggle", "inputs", "outputs",
                                                 "inputs", "outputs", "image", "scene"):
                continue
            if p.is_readonly or getattr(p, "is_library_defined", False):
                continue
            try:
                v = getattr(n, pid)
            except Exception:
                continue
            if isinstance(v, (int, float, bool, str)):
                props[pid] = v
            elif hasattr(v, "__len__") and not isinstance(v, str):
                try:
                    props[pid] = [float(x) for x in v][:16]
                except Exception:
                    pass
        return props

    comp_dump = None
    if comp_group is not None:
        nodes = []
        for n in comp_group.nodes:
            nodes.append({
                "name": n.name, "bl_idname": n.bl_idname,
                "location": [n.location.x, n.location.y],
                "props": dump_node_props(n),
                "inputs": {s.name: dump_socket_val(s) for s in n.inputs
                           if not s.is_linked and hasattr(s, "default_value")},
            })
        links = [{"from_node": l.from_node.name,
                  "from_socket": l.from_socket.name,
                  "to_node": l.to_node.name,
                  "to_socket": l.to_socket.name}
                 for l in comp_group.links]
        comp_dump = {"name": comp_group.name, "nodes": nodes, "links": links}

    # per-class source ID name sets (rebuild consolidation input)
    id_names = {
        "objects": sorted(o.name for o in bpy.data.objects),
        "meshes": sorted(m.name for m in bpy.data.meshes),
        "materials": sorted(m.name for m in bpy.data.materials
                            if m.library is None),
        # images + node_groups include LINKED source names: write() may
        # localize them into chunks (Metal09_* measured), and the rebuild
        # must keep source-named IDs rather than treat them as artifacts
        "images": sorted(i.name for i in bpy.data.images),
        "node_groups": sorted(n.name for n in bpy.data.node_groups),
    }

    # [data-derived expectation] what the chunks + gap riders can actually
    # deliver, per class — the rebuild asserts name-set equality against
    # this (stronger and self-consistent, no hand arithmetic)
    expected_ids = {}
    for cls in ("objects", "meshes", "materials", "images", "node_groups"):
        deliver = set(reachable[cls]) & set(id_names[cls])
        deliver |= set(gap.get(cls, []))
        expected_ids[cls] = sorted(deliver)

    manifest = {
        "design": "D18 REV-3", "source": report_a["source"],
        "source_sha256": report_a["source_sha256"],
        "census": census, "poly": poly, "scene_settings": settings,
        "world": {"name": world.name, "n_nodes": len(world.node_tree.nodes)},
        "compositor": comp_dump if comp_group is not None else None,
        "texture_table": table,
        "skipped_images": report_a["skipped_images"],
        "linked_dropped": linked_dropped,
        "riders": riders,
        "closure_gap": gap,
        "id_names": id_names,
        "expected_ids": expected_ids,
        "parent_pairs": parent_pairs,
        "objects": obj_records,
        "chunks": chunks,
        "collection_tree": [
            {"name": c.name,
             "children": [{"name": k.name, "children": []}
                          for k in c.children]}
            for c in sc.collection.children],
    }
    with open(os.path.join(outdir, "chunks_manifest.json"), "w") as f:
        json.dump(manifest, f, indent=1)
    total = sum(c["bytes"] for c in chunks)
    print(f"[B-DONE] {len(chunks)} chunks, {total/1e6:.0f}MB total", flush=True)

def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--phase", choices=["a", "b"], required=True)
    p.add_argument("--src", default="polyhaven_cache/loft/loft.blend")
    p.add_argument("--outdir", default="assets/loft")
    a = p.parse_args(argv)
    if a.phase == "a":
        phase_a(a.src, a.outdir)
    else:
        phase_b(a.outdir)

main()
