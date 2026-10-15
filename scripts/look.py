"""
look.py — the ONE vision-loop command (blender-vision-kit D4/D6).

Bundles the perception round into a single Blender invocation:
  multi-angle renders + validator verdict + object manifest + readiness
  headers, printed BESIDE the images. One cold start instead of three.

    blrun.sh --background --python scripts/look.py -- \
        --load-blend work.blend \
        [--angles front,side,top,persp] [--frame 1] [--engine workbench] \
        [--no-annotate] [--labels 8] [--closeup Table] \
        [--grid-cols 2] [--lens 50] [--target X,Y,Z] [--w 640 --h 480] \
        [--output output/my_scene/look]

    # Fresh iteration only (REBUILDS and discards patch-applied state —
    # the canonical state carrier is --load-blend after apply_patch
    # --save-blend; see AGENTS.md "The vision loop"):
    blrun.sh --background --python scripts/look.py -- --scene my_scene ...

What you always get (forced pairing — you cannot look without the numbers):
  [look] verdict block: engine/frame/bounds, validator P0/P1/P2 lines,
  per-image readiness (luma/clipped/dark/subject coverage), object-id
  manifest (id/type/dims/centroid — the ids your next patch needs), and
  the written image paths.

Annotations (default ON, render-time only, NEVER saved into any .blend):
  1m ground grid, RGB axis gnomon SW of scene center at (cx-1.5, cy-1.5)
  (confirm handedness — law L2), top-N object labels, red bbox wireframes
  on validator-flagged objects.

Exit codes: 0 = PASS (no P0/P1), 3 = validator P0 **or P1** present (with
--fail-on-issues, the default — WARN-level issues fail closed), 4 = an
image-readiness row errored (unreadable/empty output — that look is
INVALID), 1 = operational error.

Camera occlusion probe (F-TD12, D-TD22): --probe-camera NAME[,...] (or
'all') casts each scene camera's center ray and NAMES what it hits first
— the recession-occlusion class (a wall/tunnel between the lens and its
subject) is invisible to every other check. Probe rows go to stdout AND
look_manifest.json ('camera_probes'). The probe mutates nothing and
never affects exit codes (an informational tool; exit 3 may co-occur).
Probe-only invocation: --probe-camera ... --angles none.
"""
import argparse
import json
import math
import os
import sys

import bpy
from mathutils import Vector

# Law 107: entry scripts own their sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from blender_kit import script_argv, validate_output, validate_resolution  # noqa: E402
import viewport_capture as vc  # noqa: E402
import validate_scene as vs  # noqa: E402
import annotate  # noqa: E402


def _camera_forward(mw) -> Vector:
    """Camera view direction: world -Z axis, normalized.

    Kit-canonical form (occlusion_gate.py:223). The col[2].xyz*-1
    spelling elsewhere is the SAME axis with a negation trap — do not
    mix them per-object."""
    return (mw.to_3x3() @ Vector((0.0, 0.0, -1.0))).normalized()


def _render_hidden(ob) -> bool:
    """The Street.Mist law (contact_audit.py:158): scene.ray_cast hits
    render-hidden geometry — an atmosphere box flags every camera.
    Flag hits that would never render; the caller may re-cast past them
    but keeps the context (the agent decides)."""
    try:
        if ob.hide_render:
            return True
        if ob.hide_viewport:
            return True
        if getattr(ob, "visible_camera", True) is False:
            return True
    except ReferenceError:
        return True
    return False


def _probe_one_cam(scene, cam, frame) -> dict:
    """One camera's center-ray probe. Reads only; never raises; never
    mutates (no camera creation/binding, no scene.camera writes — the
    AK-10 marker-hijack class cannot fire because nothing renders)."""
    row = {"camera": cam.name, "frame": frame}
    try:
        # The dep.update() ritual (occlusion_gate.py:212-220, measured):
        # constraint-driven (track-to) cameras return STALE matrix_world
        # with only view_layer.update() — phantom hits. Order matters:
        # depsgraph update BEFORE the matrix read.
        dep = bpy.context.evaluated_depsgraph_get()
        dep.update()
        mw = cam.matrix_world.copy()
        origin = mw.translation.copy()
        direction = _camera_forward(mw)
        hit = scene.ray_cast(dep, origin, direction)
        if not hit[0] or hit[4] is None:
            row.update({"status": "clear", "object": None,
                        "distance_m": None, "point": None,
                        "render_hidden": False, "recasts": 0})
            return row
        obj, loc = hit[4], hit[1].copy()
        hidden = _render_hidden(obj)
        recasts = 0
        # Bounded re-cast past render-hidden hits: name the first RENDERED
        # hit; the hidden one stays as context (never silently dropped).
        while hidden and recasts < 8:
            recasts += 1
            hit2 = scene.ray_cast(dep, loc + direction * 1e-4, direction)
            if not hit2[0] or hit2[4] is None:
                break
            obj, loc = hit2[4], hit2[1].copy()
            hidden = _render_hidden(obj)
        dist = (loc - origin).length
        row.update({"status": "hit", "object": obj.name,
                    "distance_m": round(dist, 4),
                    "point": [round(v, 4) for v in loc],
                    "render_hidden": hidden, "recasts": recasts})
    except Exception as e:  # noqa: BLE001 — informational tool, never raise
        row.update({"status": "error", "error": repr(e)})
    return row


def _probe_cam_names(scene, requested_items):
    """Resolve --probe-camera values (repeatable, comma-split, 'all'
    sentinel) to camera objects; unknown names map to None (a
    status:'missing' row, never an exit — the probe is informational)."""
    names = []
    for item in requested_items or []:
        names.extend(s.strip() for s in item.split(",") if s.strip())
    if not names:
        return []
    if "all" in names:
        cams = [o for o in scene.objects if o.type == 'CAMERA'
                and not o.name.startswith("temp_")
                and not o.name.startswith(annotate.ANNOT_PREFIX)]
        return [(c.name, c) for c in sorted(cams, key=lambda o: o.name)]
    by_name = {o.name: o for o in scene.objects if o.type == 'CAMERA'}
    return [(n, by_name.get(n)) for n in names]


def _manifest(probe_only: bool = False) -> dict:
    """Compact object-id manifest: the ids the next patch needs."""
    # world_bbox law: matrices/bound_box are evaluated lazily — right
    # after in-process mutation they are STALE (a 45°-yawed cube reads
    # unrotated). Force the depsgraph so every row reflects true state.
    bpy.context.view_layer.update()
    out = []
    for o in bpy.context.scene.objects:
        if o.name.startswith(annotate.ANNOT_PREFIX):
            continue  # annotation layer is render-time only, never manifest
        if o.type == 'MESH':
            c = [round(v, 3) for v in (
                sum((o.matrix_world @ type(o.location)(cc)).x for cc in o.bound_box) / 8.0,
                sum((o.matrix_world @ type(o.location)(cc)).y for cc in o.bound_box) / 8.0,
                sum((o.matrix_world @ type(o.location)(cc)).z for cc in o.bound_box) / 8.0)]
            row = {"id": o.name, "type": "MESH",
                   "dims_m": [round(v, 3) for v in o.dimensions],
                   "centroid": c}
            # D16 handoff law: world-space AABB per row. dims_m is the
            # LOCAL bbox size — under rotation, centroid ± dims/2 is the
            # WRONG box, and a non-vision consumer has no other way to
            # know. This is the geometric ground truth the blind agent
            # reasons from (fits/gaps/containment all derive from it).
            _bb = [o.matrix_world @ type(o.location)(cc)
                   for cc in o.bound_box]
            row["world_bbox"] = {
                "min": [round(min(p[i] for p in _bb), 3) for i in range(3)],
                "max": [round(max(p[i] for p in _bb), 3) for i in range(3)]}
            # D16: kit_label is a MANDATORY row field (null when
            # unlabeled) — non-vision consumers key on it, so the key
            # must always exist, not appear only when set
            row["kit_label"] = o.get("kit_label")
            # D15: per-object color identity source (first slot's material;
            # 'viewport' default when no material or pre-sync run)
            mats = [s.material for s in o.material_slots if s.material]
            if mats:
                # A10 (session-18): probe-only runs skip sync_display_colors,
                # so _COLOR_SOURCE is empty — the old default stamped
                # node-authored materials as "viewport" (a lie). Unknown
                # must be null, not a wrong answer.
                row["color_source"] = annotate._COLOR_SOURCE.get(
                    mats[0].name) if probe_only else \
                    annotate._COLOR_SOURCE.get(mats[0].name, "viewport")
            out.append(row)
        elif o.type == 'LIGHT':
            out.append({"id": o.name, "type": "LIGHT",
                        "light": o.data.type, "energy_W": round(o.data.energy, 1)})
        elif o.type == 'CAMERA':
            out.append({"id": o.name, "type": "CAMERA"})
    return out


def _readiness(path: str) -> dict:
    """Shared per-image readiness (single implementation in viewport_capture)."""
    return vc.image_readiness(path)


def _camera_loc_for_angle(label: str, target) -> tuple:
    """Mirror viewport_capture's camera math so label aim == render camera."""
    if label == "active":
        cam = bpy.context.scene.camera
        if cam is not None:
            return tuple(cam.matrix_world.translation)
        return tuple(target)
    if label in vc.VIEW_ANGLES:
        loc = vc.VIEW_ANGLES[label][:3]
        return (loc[0] + target[0], loc[1] + target[1], loc[2] + target[2])
    return tuple(target)


def _normalize_engine_arg(v):
    """Argparse type: bridge raw Blender enum spellings to dispatch names."""
    from blender_kit import normalize_engine
    return normalize_engine(v)


def _default_exposure(args) -> float:
    """M5 tuning: workbench STUDIO renders ~98% of pixels in the darkest
    third of the range (docs/TUNING_perception_v1.md). Lift workbench by
    +1.0 EV by default; eevee/cycles already expose the scene lighting."""
    if args.exposure is not None:
        return args.exposure
    return 1.0 if args.engine == "workbench" else 0.0


def main():
    p = argparse.ArgumentParser(
        description="look.py — one-invocation perceive+verify for vision agents")
    p.add_argument("--scene", default=None,
                   help="Scene module name (FRESH build; discards patch state)")
    p.add_argument("--load-blend", default=None,
                   help="Load a .blend (DEFAULT state carrier after patches)")
    p.add_argument("--frames", type=int, default=24)
    p.add_argument("--frame", type=int, default=None,
                   help="Frame to evaluate (default: scene start)")
    p.add_argument("--angles", default="front,side,top,persp",
                   help="Comma list, or 'none' to skip grid renders "
                        "(closeup-only look — L1 image budget)")
    p.add_argument("--engine", default="workbench",
                   type=_normalize_engine_arg,
                   help="Render engine: workbench|eevee|cycles (raw Blender "
                        "enums like BLENDER_EEVEE_NEXT accepted)")
    p.add_argument("--exposure", type=float, default=None,
                   help="View exposure lift in EV. Default: +1.0 on "
                        "workbench (tuned: docs/TUNING_perception_v1.md), "
                        "0.0 on eevee/cycles")
    p.add_argument("--samples", type=int, default=1)
    p.add_argument("--w", type=int, default=640)
    p.add_argument("--h", type=int, default=480)
    p.add_argument("--lens", type=int, default=50)
    p.add_argument("--target", default=None, help="X,Y,Z look-at (default scene center)")
    p.add_argument("--grid-cols", type=int, default=2)
    p.add_argument("--no-grid", action="store_true",
                   help="Individual angle files instead of one stitched grid")
    p.add_argument("--no-annotate", action="store_true",
                   help="Disable the annotation layer (grid/gnomon/labels/flags)")
    p.add_argument("--labels", type=int, default=8,
                   help="Top-N objects (by bbox diagonal) to index-label")
    p.add_argument("--closeup", default=None,
                   help="Object id: extra auto-framed macro render (answers WHAT "
                        "after the grid answers WHERE)")
    p.add_argument("--closeup-fill", type=float, default=1.5,
                   help="Closeup framing factor over the object's bbox diagonal")
    p.add_argument("--output", default=None,
                   help="Output dir (default: output/look/<stamp>)")
    p.add_argument("--fail-on-issues", action="store_true", default=True,
                   help="Exit 3 on P0/P1 validator issues (parity with "
                        "validate_scene --fail-on-issues; --no-fail-on-issues "
                        "to disable)")
    p.add_argument("--no-fail-on-issues", dest="fail_on_issues",
                   action="store_false")
    p.add_argument("--probe-camera", action="append", default=None,
                   help="Camera occlusion probe (F-TD12): name the scene "
                        "camera(s) whose center ray to cast — repeatable, "
                        "comma-separated, or 'all'. Rows print to stdout and "
                        "land in look_manifest.json ('camera_probes'). Use "
                        "--angles none for a probe-only run.")
    args = p.parse_args(script_argv())

    if not args.load_blend and not args.scene:
        print("[look] ERROR: --load-blend (canonical) or --scene (fresh) required")
        sys.exit(1)
    validate_resolution(args.w, args.h)

    # ---- load / build -----------------------------------------------------
    if args.load_blend:
        print(f"[look] loading .blend: {args.load_blend}")
        bpy.ops.wm.open_mainfile(filepath=args.load_blend)
    else:
        from blender_kit import safe_import_scene, clear_scene
        print(f"[look] building scene: {args.scene} (fresh build)")
        mod = safe_import_scene(args.scene)
        clear_scene()
        ctx = mod.build_scene()
        if hasattr(mod, "animate"):
            mod.animate(ctx, start_frame=1, n_frames=args.frames)

    scene = bpy.context.scene
    if args.frame is not None:
        scene.frame_set(args.frame)
    else:
        args.frame = scene.frame_start

    # ---- camera target BEFORE annotations (grid must not skew the center)
    if args.target:
        from blender_kit import parse_vec3
        target = parse_vec3(args.target, "target")
    else:
        target = vc._compute_scene_center()

    # ---- validator (numbers BEFORE images: forced pairing by construction)
    report = vs.validate_scene()
    p0 = report["issues_by_severity"]["P0"]
    p1 = report["issues_by_severity"]["P1"]
    p2 = report["issues_by_severity"]["P2"]
    flagged = []
    for issue in report["issues"]:
        if issue["severity"] in ("P0", "P1"):
            if "object" in issue:
                flagged.append(issue["object"])
            elif "objects" in issue:
                flagged.extend(issue["objects"])
    flagged = sorted(set(flagged))
    # R6 (huge-scene robustness, measured on the 1200-mesh loft import):
    # ~1000 flagged objects × 12 wireframe boxes each = 12k+ annotation
    # objects — depsgraph re-evaluation per angle OOMs a 4GB box AND the
    # render degrades to unreadable red spaghetti. Cap the outlines to the
    # most significant (issue order: P0 first, then largest overlap);
    # the full flagged set stays in look_manifest.json.
    FLAG_CAP = 60
    flag_note = ""
    if len(flagged) > FLAG_CAP:
        sev0 = {i.get("object") for i in report["issues"]
                if i["severity"] == "P0" and "object" in i}
        ordered = sorted(flagged, key=lambda n: n not in sev0)
        flagged = ordered[:FLAG_CAP]
        flag_note = f" (capped {FLAG_CAP} of {len(ordered)} flagged — full set in manifest)"

    # ---- output location -------------------------------------------------
    if args.output:
        outdir = args.output
    else:
        base = args.scene or os.path.splitext(os.path.basename(args.load_blend))[0]
        outdir = os.path.join("output", base, "look")
    os.makedirs(outdir, exist_ok=True)
    validate_output(os.path.join(outdir, "grid.png"))

    # ---- annotations (render-time only; deleted before any return) -------
    # stale-read law (kit's own prop_carry.py:53): re-issue frame_set +
    # double view_layer update before ANY matrix read. The validator ran
    # in between and depsgraph state must be pinned to args.frame again.
    if args.frame is not None:
        scene.frame_set(args.frame)
    bpy.context.view_layer.update()
    bpy.context.view_layer.update()
    # ---- camera occlusion probe (F-TD12, D-TD22) -------------------------
    # Slot law (peer-review finding 3): AFTER the re-pin double update
    # (fresh matrices) and BEFORE sync_display_colors / the annotation
    # build — annotation meshes are real geometry a ray would hit first.
    angle_labels_probe = [a.strip() for a in (args.angles or "").split(",") if a.strip()]
    if angle_labels_probe == ["none"]:
        angle_labels_probe = []
    probe_requested = bool(args.probe_camera)
    probe_only = probe_requested and not angle_labels_probe and not args.closeup
    probe_rows = []
    if probe_requested:
        probe_cams = _probe_cam_names(scene, args.probe_camera)
        for name, cam in probe_cams:
            if cam is None:
                probe_rows.append({"camera": name, "frame": args.frame,
                                   "status": "missing"})
                continue
            probe_rows.append(_probe_one_cam(scene, cam, args.frame))
        for r in probe_rows:
            if r["status"] == "hit":
                print(f"[look] PROBE cam={r['camera']} frame={r['frame']} "
                      f"status=hit object={r['object']} "
                      f"dist={r['distance_m']}m point={r['point']} "
                      f"render_hidden={r['render_hidden']} recasts={r['recasts']}")
            else:
                print(f"[look] PROBE cam={r['camera']} frame={r['frame']} "
                      f"status={r['status']}")
        if probe_only:
            print("[look] probe-only run (--angles none): skipping renders "
                  "and annotation")

    # D15 (QA #4): honest workbench MATERIAL colors — node-authored
    # Principled Base Colors are invisible to workbench (it reads
    # mat.diffuse_color) so imported scenes look ALL-GRAY. Sync for the
    # render, restore in finally (standalone so --no-annotate looks stay
    # honest too; annotation materials are dual-set consistent, no-op).
    color_sync = annotate.sync_display_colors() if not probe_only \
        else {"synced": [], "nontrivial": [], "linked": []}
    if not probe_only and (color_sync["synced"] or color_sync["nontrivial"] or color_sync["linked"]):
        print(f"[look] display-color sync: {len(color_sync['synced'])} node-authored"
              f" -> viewport; {len(color_sync['nontrivial'])} non-trivially-authored"
              f" (color identity unreliable there)"
              + (f"; {len(color_sync['linked'])} linked read-only"
                 if color_sync["linked"] else ""))
    layer = {"objects": [], "labels": []}
    annotated = False
    if not args.no_annotate and not probe_only:
        # A12 (session-18): this block used to sit OUTSIDE the zero-residue
        # finally — an exception mid-build leaked a partial KIT_ANNOT_*
        # layer (in-memory; blrun fail-closed turns it into exit 1, but the
        # residue would poison any same-process continuation). Purge on
        # the raise path too.
        try:
            from viewport_capture import _compute_scene_center
            center = _compute_scene_center()
            meshes = [o for o in scene.objects if o.type == 'MESH'
                      and not o.name.startswith(annotate.ANNOT_PREFIX)]
            # top-N labels by bbox diagonal, EXCLUDING ground-like slabs
            # (a 20x20m ground "label" renders as a giant billboard that blocks
            # the whole top view — measured on the first look_test run)
            def groundlike(o):
                return o.dimensions.z <= 0.05 and (o.dimensions.x * o.dimensions.y) >= 6.0
            ranked = sorted((o for o in meshes if not groundlike(o)),
                            key=lambda o: -o.dimensions.length)
            label_ids = [(o.name, i + 1) for i, o in enumerate(ranked[:args.labels])]
            layer = annotate.build_annotation_layer(
                flagged_ids=flagged, label_ids=label_ids, grid=True, gnomon=True)
            annotated = True
            view_layer = bpy.context.view_layer
            view_layer.update()
        except BaseException:
            # wave-2a: `layer` only rebinds AFTER the builder returns — a
            # MID-BUILD raise left the partial objects unreachable here
            # (the purge iterated zero objects). Sweep by the ANNOT prefix
            # instead, which delete_annotation_layer also uses for its
            # datablock purge.
            try:
                import bpy as _bpy
                for _o in list(_bpy.context.scene.objects):
                    if _o.name.startswith(annotate.ANNOT_PREFIX):
                        _bpy.data.objects.remove(_o, do_unlink=True)
            except Exception:
                pass
            # A3 (session-19): the object sweep above leaves the zero-user
            # DATABLOCK residue behind (KIT_ANNOT_mat_* materials, KIT_ANNOT_*
            # curves + meshes — the F2A-4 class, up to ~40 mesh datablocks
            # per run). delete_annotation_layer purges all three families by
            # the ANNOT prefix; {"objects": []} skips its (already-done)
            # object sweep. Still best-effort: a cleanup error must never
            # mask the original raise below.
            try:
                annotate.delete_annotation_layer({"objects": []})
            except Exception:
                pass
            raise

    try:
        # ---- angle list (mirrors viewport_capture main) -------------------
        angle_labels = [a.strip() for a in args.angles.split(",") if a.strip()]
        if angle_labels == ["none"]:
            angle_labels = []  # closeup-only look
        for lbl in angle_labels:
            if lbl not in vc.VIEW_ANGLES and lbl != "active":
                print(f"[look] ERROR: unknown angle '{lbl}'")
                if lbl == "custom":
                    print("[look] (look.py has no --custom-loc — use "
                          "--closeup <obj> for a macro of one object, or "
                          "call viewport_capture.py directly for custom "
                          "viewpoints)")
                sys.exit(1)

        # ---- render angles ------------------------------------------------
        import tempfile
        per_angle = {}
        if args.no_grid:
            for lbl in angle_labels:
                out_path = os.path.join(outdir, f"{lbl}.png")
                if annotated:
                    annotate.refresh_labels(layer)
                    bpy.context.view_layer.update()
                    annotate.aim_labels_at(layer["labels"],
                                           _camera_loc_for_angle(lbl, target),
                                           flat=(lbl == "top"))
                vc.render_angle(lbl, out_path, engine=args.engine,
                                samples=args.samples, width=args.w,
                                height=args.h, target=target, lens=args.lens,
                                exposure=_default_exposure(args))
                per_angle[lbl] = out_path
            images = list(per_angle.values())
        else:
            images = []
            if angle_labels:
                with tempfile.TemporaryDirectory() as tmp:
                    for lbl in angle_labels:
                        tmp_path = os.path.join(tmp, f"{lbl}.png")
                        if annotated:
                            annotate.refresh_labels(layer)
                            bpy.context.view_layer.update()
                            annotate.aim_labels_at(layer["labels"],
                                                   _camera_loc_for_angle(lbl, target),
                                                   flat=(lbl == "top"))
                        vc.render_angle(lbl, tmp_path, engine=args.engine,
                                        samples=args.samples, width=args.w,
                                        height=args.h, target=target, lens=args.lens,
                                        exposure=_default_exposure(args))
                        per_angle[lbl] = tmp_path
                    grid_path = os.path.join(outdir, "grid.png")
                    vc.stitch_contact_sheet(list(per_angle.values()), grid_path,
                                            grid_cols=args.grid_cols)
                    images.append(grid_path)

        # ---- closeup (auto-framed macro of one object) --------------------
        if args.closeup:
            obj = scene.objects.get(args.closeup)
            if obj is None or obj.type != 'MESH':
                print(f"[look] ERROR: closeup target '{args.closeup}' is not a mesh object")
                sys.exit(1)
            corners = [obj.matrix_world @ type(obj.location)(c) for c in obj.bound_box]
            cx = sum(c.x for c in corners) / 8.0
            cy = sum(c.y for c in corners) / 8.0
            cz = sum(c.z for c in corners) / 8.0
            diag = obj.dimensions.length or 0.5
            dist = diag * args.closeup_fill
            closeup_loc = (cx + dist * 0.85, cy - dist * 0.85, cz + dist * 0.6)
            if annotated:
                annotate.refresh_labels(layer)
                bpy.context.view_layer.update()
                annotate.aim_labels_at(layer["labels"], closeup_loc)
            closeup_path = os.path.join(outdir, f"closeup_{args.closeup}.png")
            vc.render_angle("custom", closeup_path, engine=args.engine,
                            samples=args.samples, width=args.w, height=args.h,
                            target=(cx, cy, cz), lens=args.lens,
                            custom_location=closeup_loc,
                            exposure=_default_exposure(args))
            images.append(closeup_path)

        # ---- readiness headers -------------------------------------------
        ready = [_readiness(ip) for ip in images]

        # ---- verdict block (the numbers beside the images) ----------------
        mn, mx = (None, None)
        meshes = [o for o in scene.objects if o.type == 'MESH'
                  and not o.name.startswith(annotate.ANNOT_PREFIX)]
        if meshes:
            pts = [o.matrix_world @ type(o.location)(c) for o in meshes
                   for c in o.bound_box]
            mn = (round(min(p.x for p in pts), 2), round(min(p.y for p in pts), 2),
                  round(min(p.z for p in pts), 2))
            mx = (round(max(p.x for p in pts), 2), round(max(p.y for p in pts), 2),
                  round(max(p.z for p in pts), 2))

        verdict = "FAIL" if p0 else ("WARN" if p1 else "PASS")
        n_annot = sum(1 for o in scene.objects
                      if o.name.startswith(annotate.ANNOT_PREFIX))
        n_scene = len(scene.objects) - n_annot
        print("=" * 64)
        print(f"[look] VERDICT: {verdict}"
              f"  engine={args.engine} frame={args.frame}"
              f"  objects={n_scene}" +
              (f" (+{n_annot} annot, render-time only)" if n_annot else ""))
        if mn:
            print(f"[look] scene bounds min={mn} max={mx}")
        print(f"[look] validator: P0={p0} P1={p1} P2={p2}"
              + ("  [validator ran]" if True else ""))
        _adj = report.get("adjacency_pairs_advisory") or 0
        if _adj:
            print(f"[look] level-adjacency advisories: {_adj} "
                  f"(fam-fam AABB composition — F22, see report "
                  f"adjacency_worst)")
        for issue in report["issues"][:12]:
            who = issue.get("object", " & ".join(issue.get("objects", [])))
            print(f"[look]   [{issue['severity']}] {issue['type']:14s} {who}: "
                  f"{issue['description']}")
        for r in ready:
            fl = (" flags=" + ",".join(r["flags"])) if r.get("flags") else ""
            if "error" in r:
                print(f"[look] image {r['path']} readiness-error: {r['error']}")
            else:
                print(f"[look] image {os.path.basename(r['path'])} "
                      f"{r['w']}x{r['h']} luma={r['luma_mean']} "
                      f"clipped={r['clipped_pct']}% dark={r['dark_pct']}% "
                      f"subject={r['subject_pct']}%{fl}")
        man = _manifest(probe_only=probe_only)
        mesh_rows = [m for m in man if m["type"] == "MESH"]
        print(f"[look] manifest ({len(man)} objects; meshes {len(mesh_rows)}):")
        for m in man[:24]:
            if m["type"] == "MESH":
                print(f"[look]   {m['id']:24s} dims_m={m['dims_m']} centroid={m['centroid']}")
            else:
                print(f"[look]   {m['id']:24s} {m['type']}"
                      + (f" {m.get('light')} {m.get('energy_W')}W" if m.get("light") else ""))
        if len(man) > 24:
            print(f"[look]   ... {len(man) - 24} more (manifest JSON: "
                  f"{os.path.join(outdir, 'look_manifest.json')})")
        print(f"[look] annotations: {'grid+gnomon+labels(top-%d)+flags(%s)' % (args.labels, len(flagged)) if annotated else 'OFF'}"
              f"{flag_note}"
              "  [render-time only, never saved]")
        if annotated and label_ids:
            lbl_map = [{"index": i, "id": name} for name, i in label_ids]
            print("[look] labels: " + " ".join(
                f"[{e['index']}]={e['id']}" for e in lbl_map))
        else:
            lbl_map = []
        # wave-3 T6: fixed 5m camera offsets clip large subject clusters
        # while readiness scores clean — add an overflow hint
        if meshes and mn:
            import math as _math
            diag = _math.dist(mn, mx)
            # F2A-15: exact half-width = dist * (sensor/2)/lens (no atan —
            # the atan form was ~4% conservative). Distance = the front
            # offset's MAGNITUDE (s17 fix: front[0] is the x component,
            # which is 0 — the old arithmetic made visible ~0.0 and fired
            # the hint on every scene); sensor half-width 18mm = bpy's
            # default, the same constant the temp cameras use.
            _front = vc.VIEW_ANGLES["front"][:3]
            _dist = _math.sqrt(sum(v * v for v in _front))
            _sensor_half = 18.0
            visible = 2 * _dist * _sensor_half / max(args.lens, 1)
            if diag > visible * 1.4:
                print(f"[look] HINT: SUBJECT-OVERFLOW (cluster diag {diag:.1f}m "
                      f"> visible ~{visible:.1f}m at {args.lens}mm/5m offset) "
                      "— aim with --target/--lens or --closeup for readable frames")
        print("=" * 64)

        # F-TD3 detectability: record which camera each panel intended,
        # and which camera a timeline marker WOULD have bound at this frame
        # (the pre-fix hijack class — film scenes bind every shot cam to a
        # marker; bpy.ops.render.render prefers the marker over
        # scene.camera). render_angle sweeps the markers, but the manifest
        # row makes any future regression VISIBLE instead of silent.
        def _marker_cam_at(fr):
            best = None
            for m in scene.timeline_markers:
                if m.camera is not None and m.frame <= fr:
                    if best is None or m.frame > best.frame:
                        best = m
            return best.camera.name if best is not None else None

        intent = []
        _fr = bpy.context.scene.frame_current
        _no_grid = args.no_grid
        for lbl, path in per_angle.items():
            # A10 (session-18): grid-path panels are written to a temp dir
            # that dies with the with-block — recording "front.png" gave
            # consumers dead references. The deliverable is grid.png; name
            # it plus the panel label it became.
            _img = (os.path.basename(path) if _no_grid
                    else f"grid.png#{lbl}")
            row = {"image": _img, "angle": lbl,
                   "rendered_cam": ("scene.camera" if lbl == "active"
                                    else f"temp {lbl} panel")}
            if not _no_grid:
                row["panel"] = lbl
                row["image_is_temp_panel"] = True
            mk = _marker_cam_at(_fr)
            if mk:
                row["marker_cam_at_frame"] = mk
            intent.append(row)
        if args.closeup:
            intent.append({"image": os.path.basename(closeup_path),
                           "angle": "custom", "rendered_cam": "temp closeup panel",
                           **({"marker_cam_at_frame": _marker_cam_at(_fr)}
                              if _marker_cam_at(_fr) else {})})

        with open(os.path.join(outdir, "look_manifest.json"), "w") as f:
            json.dump({"engine": args.engine, "frame": args.frame,
                       "validator": report, "images": ready,
                       "manifest": man, "labels": lbl_map,
                       "camera_intent": intent,
                       "camera_probes": probe_rows}, f, indent=2)

        # F2A-2: a readiness row with "error" means an image the eye
        # cannot open — that is a FAILED perception pass, not a warnable
        # one. Exit 4 (distinct from the validator's 3).
        if any("error" in r for r in ready):
            print("[look] ERROR: image readiness failed on one or more "
                  "outputs (unreadable/empty file) — treat this look as "
                  "invalid, exit 4")
            sys.exit(4)

        if (p0 or p1) and args.fail_on_issues:
            sys.exit(3)
    finally:
        # LAW (D5): annotations are render-time only — delete unconditionally.
        if annotated:
            removed = annotate.delete_annotation_layer(layer)
            print(f"[look] annotation layer deleted ({removed} objects)")
        # LAW (D15): display-color sync is render-time only — restore
        # unconditionally, gated on sync having produced originals.
        restored = annotate.restore_display_colors(color_sync)
        if restored:
            print(f"[look] display-color sync restored ({restored} materials)")


if __name__ == "__main__":
    main()
