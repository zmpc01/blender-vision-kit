"""
look.py — the ONE vision-loop command (blender-vision-kit D4/D6).

Bundles the perception round into a single Blender invocation:
  multi-angle renders + validator verdict + object manifest + readiness
  headers, printed BESIDE the images. One cold start instead of three.

    blrun.sh --background --python scripts/look.py -- \
        --load-blend work.blend \
        [--angles front,side,top,persp] [--frame 1] [--engine workbench] \
        [--annotate|--no-annotate] [--labels 8] [--closeup Table] \
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
  1m ground grid, RGB axis gnomon at origin (confirm handedness — law L2),
  top-N object labels, red bbox wireframes on validator-flagged objects.

Exit codes: 0 = clean/WARN, 3 = validator P0 present, 1 = operational error.
"""
import argparse
import json
import math
import os
import sys

import bpy

# Law 107: entry scripts own their sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from blender_kit import script_argv, validate_output, validate_resolution  # noqa: E402
import viewport_capture as vc  # noqa: E402
import validate_scene as vs  # noqa: E402
import annotate  # noqa: E402


def _manifest() -> dict:
    """Compact object-id manifest: the ids the next patch needs."""
    out = []
    for o in bpy.context.scene.objects:
        if o.name.startswith(annotate.ANNOT_PREFIX):
            continue  # annotation layer is render-time only, never manifest
        if o.type == 'MESH':
            c = [round(v, 3) for v in (
                sum((o.matrix_world @ type(o.location)(cc)).x for cc in o.bound_box) / 8.0,
                sum((o.matrix_world @ type(o.location)(cc)).y for cc in o.bound_box) / 8.0,
                sum((o.matrix_world @ type(o.location)(cc)).z for cc in o.bound_box) / 8.0)]
            out.append({"id": o.name, "type": "MESH",
                        "dims_m": [round(v, 3) for v in o.dimensions],
                        "centroid": c})
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
                   choices=["workbench", "eevee", "cycles"])
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

    # ---- output location -------------------------------------------------
    if args.output:
        outdir = args.output
    else:
        base = args.scene or os.path.splitext(os.path.basename(args.load_blend))[0]
        outdir = os.path.join("output", base, "look")
    os.makedirs(outdir, exist_ok=True)
    validate_output(os.path.join(outdir, "grid.png"))

    # ---- annotations (render-time only; deleted before any return) -------
    layer = {"objects": [], "labels": []}
    annotated = False
    if not args.no_annotate:
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

    try:
        # ---- angle list (mirrors viewport_capture main) -------------------
        angle_labels = [a.strip() for a in args.angles.split(",") if a.strip()]
        if angle_labels == ["none"]:
            angle_labels = []  # closeup-only look
        for lbl in angle_labels:
            if lbl not in vc.VIEW_ANGLES and lbl not in ("active", "custom"):
                print(f"[look] ERROR: unknown angle '{lbl}'")
                sys.exit(1)

        # ---- render angles ------------------------------------------------
        import tempfile
        per_angle = {}
        if args.no_grid:
            for lbl in angle_labels:
                out_path = os.path.join(outdir, f"{lbl}.png")
                if annotated:
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
        man = _manifest()
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
            visible = 2 * 5.0 * _math.atan(18.0 / max(args.lens, 1))
            if diag > visible * 1.4:
                print(f"[look] HINT: SUBJECT-OVERFLOW (cluster diag {diag:.1f}m "
                      f"> visible ~{visible:.1f}m at {args.lens}mm/5m offset) "
                      "— aim with --target/--lens or --closeup for readable frames")
        print("=" * 64)

        with open(os.path.join(outdir, "look_manifest.json"), "w") as f:
            json.dump({"engine": args.engine, "frame": args.frame,
                       "validator": report, "images": ready,
                       "manifest": man, "labels": lbl_map}, f, indent=2)

        if (p0 or p1) and args.fail_on_issues:
            sys.exit(3)
    finally:
        # LAW (D5): annotations are render-time only — delete unconditionally.
        if annotated:
            removed = annotate.delete_annotation_layer(layer)
            print(f"[look] annotation layer deleted ({removed} objects)")


if __name__ == "__main__":
    main()
