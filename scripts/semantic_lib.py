"""
semantic_lib.py — D16 semantic mesh labeling (label_objects + split_mesh).

The imported-asset problem: GLB/FBX/OBJ scenes arrive as opaque
"Mesh.001/002..." ids or ONE continuous mesh. Every id-addressed kit op
(apply_patch / place_on / validate) is inoperable on them. This module
turns a VISION agent's identification into durable scene-state:

  label_objects  write kit_label (+confidence) on existing objects;
                 optional two-phase safe RENAME with whole-batch
                 collision simulation (Blender's silent .001 suffixing
                 is a lie for patches — we pre-unique instead).
  split_mesh     dry-run (bmesh connected components, ZERO residue) /
                 split (separate by loose parts) so a continuous mesh
                 can become labelable parts FIRST.

Prop contract (lowercase law — KIT_* is the disposable-object prefix):
  kit_label       semantic label, e.g. "pillar"        (string, durable)
  kit_label_conf  "high" | "medium" | "low"            (string, optional)
  kit_semantic    written ONLY when the label matches a gate-exclusion
                  token (ceiling/sun/light) — validate_scene.py reads
                  THIS prop, never names, so vision renames can no
                  longer silently strip gate coverage (QA hazard #1 of
                  the D16 audit).

Label charset: [A-Za-z0-9_-]+  (dots break three.js gotcha-48, spaces
break --closeup). KIT_ANNOT_* rejected (manifest filters that prefix).

Crash-resume: the label/split report JSON is written BEFORE any rename
or separation, listing original names — a mid-mutation crash leaves a
recovery artifact instead of a mystery scene.
"""
import json
import os
import re
import time

import bmesh
import bpy

KIT_LABEL = "kit_label"
KIT_LABEL_CONF = "kit_label_conf"
KIT_SEMANTIC = "kit_semantic"

# Gate-exclusion vocabulary: a label containing one of these tokens makes
# the op write kit_semantic (validate_scene skips such objects for
# floating/below-floor/penetration/above-5m checks — same roles the
# legacy CEILING_NAMES covered).
SEMANTIC_TOKENS = ("ceiling", "sun", "light")

LABEL_RE = re.compile(r"^[A-Za-z0-9_-]+$")
_CONFIDENCE = {"high", "medium", "low"}


def semantic_role(label: str):
    """Return the label if it is gate-relevant (exclusion vocabulary)."""
    low = (label or "").lower()
    return label if any(t in low for t in SEMANTIC_TOKENS) else None


def _validate_batch(labels_map):
    """All-or-nothing validation. Returns normalized rows (no mutation)."""
    rows = []
    for obj_id, spec in labels_map.items():
        if isinstance(spec, str):
            label, conf = spec, None
        elif isinstance(spec, dict):
            label = spec.get("label")
            conf = spec.get("confidence")
        else:
            raise RuntimeError(
                f"label_objects: entry for '{obj_id}' must be a label "
                f"string or {{label, confidence}}, got {type(spec).__name__}")
        if not label or not LABEL_RE.fullmatch(label):
            raise RuntimeError(
                f"label_objects: label {label!r} for '{obj_id}' violates "
                f"charset law [A-Za-z0-9_-]+ (no dots/spaces; KIT_ANNOT* "
                f"and empty rejected)")
        if label.upper().startswith("KIT_ANNOT"):
            raise RuntimeError(
                f"label_objects: KIT_ANNOT* labels are reserved "
                f"(manifest filter prefix): {label!r}")
        if conf is not None and conf not in _CONFIDENCE:
            raise RuntimeError(
                f"label_objects: confidence {conf!r} not in "
                f"{sorted(_CONFIDENCE)} (id '{obj_id}')")
        obj = bpy.data.objects.get(obj_id)
        if obj is None:
            avail = sorted(o.name for o in bpy.data.objects)[:15]
            raise RuntimeError(
                f"label_objects: id '{obj_id}' not found; scene objects: "
                f"{avail} …")
        rows.append({"id": obj_id, "obj": obj, "label": label,
                     "confidence": conf})
    if not rows:
        raise RuntimeError("label_objects: empty labels map")
    return rows


def _unique_name(desired, occupied):
    """Charset-safe suffixing (_2, _3 …) — never Blender's .001 lie."""
    if desired not in occupied:
        return desired
    n = 2
    while f"{desired}_{n}" in occupied:
        n += 1
    return f"{desired}_{n}"


def plan_label_batch(labels_map, rename=False, on_collision="suffix"):
    """Pure plan: validate everything, simulate the whole-batch rename,
    resolve collisions. NO scene mutation. Raises on any violation
    (all-or-nothing law)."""
    if on_collision not in ("suffix", "fail"):
        raise RuntimeError(
            f"label_objects: on_collision must be suffix|fail, "
            f"got {on_collision!r}")
    rows = _validate_batch(labels_map)
    occupied = {o.name for o in bpy.data.objects}
    batch_ids = {r["id"] for r in rows}
    # ids being renamed away free their current names
    if rename:
        for r in rows:
            if not _already_final(r, rename):
                occupied.discard(r["id"])
    for r in rows:
        cur = r["obj"]
        want_label = cur.get(KIT_LABEL) != r["label"] or (
            cur.get(KIT_LABEL_CONF) != r["confidence"])
        r["props_change"] = want_label
        r["unchanged"] = (not want_label and
                          (not rename or cur.name == r["label"]))
        if not rename:
            r["final_name"] = None
            continue
        if cur.name == r["label"] and not r["props_change"]:
            r["final_name"] = cur.name  # already correct, keep it
            occupied.add(cur.name)
            continue
        if cur.name == r["label"]:  # name right, props differ
            r["final_name"] = cur.name
            occupied.add(cur.name)
            continue
        final = _unique_name(r["label"], occupied)
        if final != r["label"] and on_collision == "fail":
            raise RuntimeError(
                f"label_objects: rename target '{r['label']}' collides "
                f"with an existing name (on_collision=fail)")
        r["final_name"] = final
        occupied.add(final)
    return rows


def _already_final(row, rename):
    return rename and row["obj"].name == row["label"]


def label_objects(labels_map, rename=False, on_collision="suffix",
                  report_path=None):
    """label_objects op body. Writes props on ALL rows; two-phase rename
    when requested. Returns the report dict. The report file is written
    BEFORE any rename (crash-resume)."""
    rows = plan_label_batch(labels_map, rename=rename,
                            on_collision=on_collision)
    report = {
        "tool": "label_objects",
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "rename": rename,
        "on_collision": on_collision,
        "rows": [{
            "id": r["id"], "label": r["label"],
            "confidence": r["confidence"],
            "current_name": r["obj"].name,
            "final_name": r["final_name"] if rename else r["obj"].name,
            "kit_semantic": semantic_role(r["label"]) is not None,
            "unchanged": r["unchanged"],
        } for r in rows],
    }
    if report_path is None:
        report_path = os.path.join("output", "labels_report.json")
    d = os.path.dirname(os.path.abspath(report_path))
    os.makedirs(d, exist_ok=True)
    with open(report_path, "w") as f:  # BEFORE mutation (crash-resume)
        json.dump(report, f, indent=2)

    renamed, kept, unchanged = [], [], []
    for r in rows:
        obj = r["obj"]
        if r.get("unchanged"):
            unchanged.append(obj.name)
        # props FIRST (additive identity survives even a rename crash)
        obj[KIT_LABEL] = r["label"]
        if r["confidence"] is not None:
            obj[KIT_LABEL_CONF] = r["confidence"]
        else:
            for key in (KIT_LABEL_CONF,):
                if key in obj.keys():
                    del obj[key]
        role = semantic_role(r["label"])
        if role is not None:
            obj[KIT_SEMANTIC] = role
        elif KIT_SEMANTIC in obj.keys():
            del obj[KIT_SEMANTIC]  # stale marker must not survive relabel
        if not rename:
            kept.append(obj.name)

    if rename:
        todo = [r for r in rows if r["final_name"] != r["obj"].name]
        # phase A: everything out of the way (temp names are guaranteed
        # fresh — refuse instead of colliding)
        scene_names = {o.name for o in bpy.data.objects}
        temps = {}
        for i, r in enumerate(todo):
            tmp = f"__lbl_tmp{i:02d}__"
            if tmp in scene_names:
                raise RuntimeError(
                    f"label_objects: temp name {tmp} already taken — "
                    f"scene carries leftover temps from a crashed run")
            temps[r["id"]] = tmp
        for r in todo:
            r["obj"].name = temps[r["id"]]
        # phase B: finals (plan already pre-uniqued against the ORIGINAL
        # occupancy; temp names can't collide with finals)
        for r in todo:
            r["obj"].name = r["final_name"]
        # verify by RE-READ (trust nothing in-flight)
        for r in todo:
            chk = bpy.data.objects.get(r["final_name"])
            if chk is None or chk.get(KIT_LABEL) != r["label"]:
                raise RuntimeError(
                    f"label_objects: rename verify FAILED for "
                    f"'{r['id']}' -> '{r['final_name']}' (report: "
                    f"{report_path})")
            renamed.append({"from": r["id"], "to": r["final_name"]})

    report["renamed"] = renamed
    report["kept"] = kept
    report["unchanged"] = unchanged
    report["semantic_marked"] = [r["obj"].name for r in rows
                                 if semantic_role(r["label"])]
    report["ok"] = True
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    return report


# ---------------------------------------------------------------------------
# split_mesh — dry-run / split pair for continuous meshes
# ---------------------------------------------------------------------------

def _region_mask(obj, region):
    """Faces fully inside a world-space box. Returns (face_indices,
    verts_in_box, captured_bbox). 'Fully inside' is the honest cut unit:
    a face straddling the box belongs to BOTH visual parts conceptually
    — giving it to either side silently deforms one of them, so we leave
    it with the source and report the count instead (the principal
    narrows the box). Indices (not BMFace refs) so they survive the
    internal bmesh being freed."""
    rmin = region["min"]
    rmax = region["max"]
    if len(rmin) != 3 or len(rmax) != 3:
        raise RuntimeError(
            f"split_mesh: region needs min:[x,y,z] max:[x,y,z], got {region!r}")
    lo = [min(a, b) for a, b in zip(rmin, rmax)]
    hi = [max(a, b) for a, b in zip(rmin, rmax)]
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    mw = obj.matrix_world
    in_box = [all(lo[i] - 1e-6 <= (mw @ v.co)[i] <= hi[i] + 1e-6
                  for i in range(3)) for v in bm.verts]
    face_idx = [f.index for f in bm.faces
                if all(in_box[v.index] for v in f.verts)]
    n_in = sum(in_box)
    pts = [mw @ v.co for v, ok in zip(bm.verts, in_box) if ok]
    bm.free()
    captured = None
    if pts:
        captured = {"min": [round(min(p[i] for p in pts), 4) for i in range(3)],
                    "max": [round(max(p[i] for p in pts), 4) for i in range(3)]}
    return face_idx, n_in, captured


def analyze_region(obj, region) -> dict:
    """Vision-driven region dry-run: what WOULD a world-box cut capture?
    ZERO residue. The principal reads the render, boxes what they
    identified (pillar, pipe…), and this reports the capture BEFORE any
    mutation — the way to break apart WELDED/continuous level geometry
    that has no loose parts at all."""
    if obj.type != "MESH":
        raise RuntimeError(f"split_mesh: '{obj.name}' is {obj.type}, "
                           f"not MESH")
    faces, n_in, captured = _region_mask(obj, region)
    return {
        "tool": "split_mesh", "mode": "dry-run-region",
        "source": obj.name,
        "region": {"min": list(region["min"]), "max": list(region["max"])},
        "verts_in_region": n_in,
        "faces_to_cut": len(faces),
        "captured_bbox": captured,
        "cut_unit": "faces fully inside the box (straddling faces stay "
                    "with the source — narrow the box to capture them)",
        "risks": _split_risks(obj),
    }


def split_region(obj, region, new_id=None, ack_risks=False) -> dict:
    """Cut the region OUT as a new object (bpy separate by selected
    faces). The source keeps its identity; the new object is ready for
    label_objects. Preconditions identical to loose-parts split."""
    if obj.type != "MESH":
        raise RuntimeError(f"split_mesh: '{obj.name}' is {obj.type}, "
                           f"not MESH")
    risks = _split_risks(obj)
    fatal = [r for r in risks if r.startswith("library-linked")]
    if fatal:
        raise RuntimeError(f"split_mesh: REFUSED — {fatal[0]}")
    if risks and not ack_risks:
        raise RuntimeError(
            f"split_mesh: REFUSED on unacknowledged risks {risks} — "
            f"re-run with \"ack_risks\": true after reading the dry-run")
    dry = analyze_region(obj, region)
    if dry["faces_to_cut"] == 0:
        raise RuntimeError(
            f"split_mesh: region captures 0 fully-inside faces — nothing "
            f"to cut (adjust the box; run mode dry-run again)")
    if new_id is None:
        new_id = f"{obj.name}_cut"
    if not LABEL_RE.fullmatch(new_id):
        raise RuntimeError(
            f"split_mesh: new_id {new_id!r} violates charset law "
            f"[A-Za-z0-9_-]+")
    warnings = [f"ack: {r}" for r in risks] if ack_risks else []
    if obj.data.users > 1:
        obj.data = obj.data.copy()
        warnings.append("data made single-user (copy) before cut")

    source_name = obj.name
    pre_names = {o.name for o in bpy.context.scene.objects}
    if bpy.context.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bm = bmesh.from_edit_mesh(obj.data)
    face_idx, _, _ = _region_mask(obj, region)
    for f in bm.faces:
        f.select_set(False)
    for v in bm.verts:
        v.select_set(False)
    for f in bm.faces:
        if f.index in face_idx:
            f.select_set(True)
    bmesh.update_edit_mesh(obj.data)
    bpy.ops.mesh.separate(type="SELECTED")
    bpy.ops.object.mode_set(mode="OBJECT")

    new_names = [o.name for o in bpy.context.scene.objects
                 if o.name not in pre_names]
    if len(new_names) != 1:
        raise RuntimeError(
            f"split_mesh: expected exactly 1 new object after region cut, "
            f"got {new_names} — aborting (scene may need manual check)")
    new_obj = bpy.data.objects[new_names[0]]
    occupied = {o.name for o in bpy.context.scene.objects} - {new_obj.name}
    final = _unique_name(new_id, occupied)
    new_obj.name = final
    chk = bpy.data.objects.get(final)
    if chk is None:
        raise RuntimeError(f"split_mesh: rename verify FAILED for "
                           f"'{new_id}' (report source {source_name})")
    mw = chk.matrix_world
    pts = [mw @ type(chk.location)(c) for c in chk.bound_box]
    return {
        "tool": "split_mesh", "mode": "split-region", "ok": True,
        "source": source_name,
        "region": dry["region"],
        "faces_cut": dry["faces_to_cut"],
        "verts_cut": dry["verts_in_region"],
        "new_object": chk.name,
        "new_object_bbox": {"min": [round(min(p[i] for p in pts), 4)
                                    for i in range(3)],
                            "max": [round(max(p[i] for p in pts), 4)
                                    for i in range(3)]},
        "remaining_object": source_name,
        "warnings": warnings,
        "next": f"label_objects {{{final!r}: <your-label>}}",
    }


def _components(bm):
    """Connected components of a bmesh (verts joined by edges; loose
    verts count as singleton components). Returns list of vert-sets."""
    seen = set()
    comps = []
    adj = {v: [] for v in bm.verts}
    for e in bm.edges:
        adj[e.verts[0]].append(e.verts[1])
        adj[e.verts[1]].append(e.verts[0])
    for v0 in bm.verts:
        if v0 in seen:
            continue
        comp, stack = set(), [v0]
        seen.add(v0)
        while stack:
            v = stack.pop()
            comp.add(v)
            for n in adj[v]:
                if n not in seen:
                    seen.add(n)
                    stack.append(n)
        comps.append(comp)
    return comps


def analyze_split(obj) -> dict:
    """Dry-run: bmesh connected components on the BASE mesh (the mesh
    bpy.ops.mesh.separate will actually cut). ZERO residue. Reports part
    count, per-part world bboxes, co-users, and every split risk."""
    if obj.type != "MESH":
        raise RuntimeError(f"split_mesh: '{obj.name}' is {obj.type}, "
                           f"not MESH")
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    comps = _components(bm)
    mw = obj.matrix_world
    parts = []
    for comp in comps:
        faces = sum(1 for f in bm.faces if all(v in comp for v in f.verts))
        pts = [mw @ v.co for v in comp]
        lo = [round(min(p[i] for p in pts), 4) for i in range(3)]
        hi = [round(max(p[i] for p in pts), 4) for i in range(3)]
        parts.append({"n_verts": len(comp), "n_faces": faces,
                      "bbox_min": lo, "bbox_max": hi,
                      "dims": [round(h - l, 4) for h, l in zip(hi, lo)]})
    bm.free()
    parts.sort(key=lambda p: -p["n_faces"])  # deterministic order
    risks = _split_risks(obj)
    return {
        "tool": "split_mesh", "mode": "dry-run",
        "source": obj.name, "analyzed": "base",
        "part_count": len(parts), "parts": parts,
        "polycount_base": len(me.polygons),
        "co_users": max(me.users - 1, 0),
        "risks": risks,
        "split_would_refuse": bool(risks) and True,
    }


def _split_risks(obj) -> list:
    risks = []
    me = obj.data
    if me.library or obj.library:
        risks.append("library-linked data (read-only — never splittable)")
    if me.users > 1:
        risks.append(f"mesh data shared by {me.users} objects (glTF-style) "
                     f"— separate would mutate co-users' geometry")
    if obj.modifiers:
        risks.append("modifier stack present — separate cuts the BASE "
                     "mesh, evaluated geometry differs")
    if me.shape_keys is not None and len(me.shape_keys.key_blocks) > 0:
        risks.append("shape keys bound — separation may orphan them")
    if obj.find_armature() or (obj.parent and
                               obj.parent.type == "ARMATURE"):
        risks.append("armature binding — parts lose their deform source")
    return risks


def split_object(obj, ack_risks=False) -> dict:
    """Separate by loose parts. Refuses on risks without ack_risks=true.
    The source object KEEPS its name on the largest part (id stays
    addressable); the rest become <name>_pNNN (charset-safe)."""
    if obj.type != "MESH":
        raise RuntimeError(f"split_mesh: '{obj.name}' is {obj.type}, "
                           f"not MESH")
    risks = _split_risks(obj)
    fatal = [r for r in risks if r.startswith("library-linked")]
    if fatal:
        raise RuntimeError(f"split_mesh: REFUSED — {fatal[0]}")
    if risks and not ack_risks:
        raise RuntimeError(
            f"split_mesh: REFUSED on unacknowledged risks {risks} — "
            f"re-run with \"ack_risks\": true only after reading the "
            f"dry-run report (a bad split wrecks the asset)")
    dry = analyze_split(obj)
    if dry["part_count"] < 2:
        raise RuntimeError(
            f"split_mesh: '{obj.name}' is one connected component "
            f"(part_count=1) — nothing to split")
    warnings = [f"ack: {r}" for r in risks] if ack_risks else []
    if obj.data.users > 1:  # ack path: make single-user first
        obj.data = obj.data.copy()
        warnings.append("data made single-user (copy) before cut")

    pre_names = {o.name for o in bpy.context.scene.objects}
    pre_mats = [m.name for m in obj.data.materials if m]
    source_name = obj.name
    if bpy.context.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.separate(type="LOOSE")
    bpy.ops.object.mode_set(mode="OBJECT")

    new_names = [o.name for o in bpy.context.scene.objects
                 if o.name not in pre_names]
    parts = [obj] + [bpy.data.objects[n] for n in sorted(new_names)]
    # largest part wins the SOURCE name — but separate() may leave the
    # original object holding a SMALLER component, so the name moves via
    # a two-phase pass (same anti-.001 law as label_objects)
    parts.sort(key=lambda o: -len(o.data.polygons))
    olds = [p.name for p in parts]
    scene_names = {o.name for o in bpy.context.scene.objects}
    temps = [f"__spl_tmp{i:02d}__" for i in range(len(parts))]
    for t in temps:
        if t in scene_names:
            raise RuntimeError(
                f"split_mesh: temp name {t} already taken — leftover "
                f"temps from a crashed run; resolve manually first")
    for p, t in zip(parts, temps):
        p.name = t
    occupied = {o.name for o in bpy.context.scene.objects}
    report_parts = []
    for idx, p in enumerate(parts):
        desired = source_name if idx == 0 else _unique_name(
            f"{source_name}_p{idx + 1:03d}", occupied)
        p.name = desired
        occupied.add(desired)
        pb = p.bound_box
        mw = p.matrix_world
        pts = [mw @ type(p.location)(cc) for cc in pb]
        lo = [round(min(q[i] for q in pts), 4) for i in range(3)]
        hi = [round(max(q[i] for q in pts), 4) for i in range(3)]
        report_parts.append({"old_name": olds[idx], "name": p.name,
                             "n_faces": len(p.data.polygons),
                             "bbox_min": lo, "bbox_max": hi,
                             "kept_source_name": idx == 0})
    mats_now = [m.name for m in parts[0].data.materials if m]
    report = {
        "tool": "split_mesh", "mode": "split", "ok": True,
        "source": source_name, "part_count": len(parts),
        "parts": report_parts, "warnings": warnings,
        "materials_inherited": sorted(set(pre_mats) & set(mats_now)) ==
                               sorted(set(pre_mats)),
        "source_note": f"'{source_name}' now names the largest part "
                       f"({parts[0].name}); kit_label was NOT propagated "
                       f"(parts need their own vision pass)",
    }
    return report
