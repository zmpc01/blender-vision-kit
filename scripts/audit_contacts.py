"""
audit_contacts.py — mesh-level contact audit CLI for the blender-agent-kit.

MM-exact contact auditing from placement_lib (also shipped in this kit's
scripts/; it was developed in the placement-lab R&D repo, where this CLI
also exists under lib/audit_contacts.py).

Mirrors the kit's validate_scene.py CLI contract (argparse over
script_argv(), --scene/--load-blend/--output/--fail-on-*), but reports
MM-EXACT contact states from placement_lib instead of bbox heuristics:

  per pair: PENETRATING / TOUCHING / CLEAR / NESTED / CROSSING with
  penetration_mm / clearance_mm, worst-first, plus a whole-scene
  failed verdict. JSON report on disk; optional ASCII maps and
  seam-inspection renders for the worst pair; optional non-zero exit
  on penetration so agents/CI can gate on it.

Usage:
    cd <kit-checkout> && bash run.sh --background --python \\
        scripts/audit_contacts.py -- \\
        --scene scene_cli_demo --output /tmp/audit.json \\
        --fail-on-penetration --report-stdout

    # from a saved .blend:
    cd <kit-checkout> && bash run.sh --background --python \\
        scripts/audit_contacts.py -- \\
        --load-blend /tmp/cli_demo.blend --output /tmp/audit.json \\
        --fail-on-penetration --report-stdout

    # current scene (whatever Blender has loaded), all bells on:
    ... -- --output /tmp/audit.json --ascii --seam-views /tmp/seam \\
        --pairs "Mug,Table;Bowl,Table" --exclude "Ground" \\
        --sample verts+edges --contact-band-mm 0.1

Exit codes: 0 ok (or no penetration when --fail-on-penetration), 1
penetration detected (--fail-on-penetration), 2 usage/scene error.
"""
import argparse
import importlib
import json
import os
import sys

# --- make placement_lib + scene modules importable from anywhere ----------
# placement_lib lives in THIS scripts/ dir (blrun.sh/run.sh already put
# scripts/ on PYTHONPATH; the explicit entry is a safety net for direct
# blender invocation). Demo scene modules live in <kit>/tests/. The
# PLACEMENT_LAB env fallback allows running against the placement-lab
# R&D repo (where this CLI also lives) without breaking the kit path.
_HERE = os.path.dirname(os.path.abspath(__file__))        # .../blender-kit/scripts
_KIT_ROOT = os.path.dirname(_HERE)                        # .../blender-kit
_KIT_TESTS = os.path.join(_KIT_ROOT, "tests")             # demo scene modules
_LAB = os.environ.get("PLACEMENT_LAB", "/home/z/placement-lab")
for _p in (_HERE, _KIT_TESTS, _LAB, os.path.join(_LAB, "lib")):
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

import bpy

try:  # kit helpers (available when launched via run.sh / blrun.sh)
    from blender_kit import script_argv, clear_scene
except ImportError:  # standalone fallbacks, same semantics
    def script_argv():
        argv = sys.argv
        return argv[argv.index("--") + 1:] if "--" in argv else []

    def clear_scene():
        bpy.ops.wm.read_factory_settings(use_empty=True)

import placement_lib as PL


def parse_pairs(spec):
    """'A,B; C,D' -> [['A','B'], ['C','D']]"""
    pairs = []
    for chunk in spec.split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        names = [n.strip() for n in chunk.split(",") if n.strip()]
        if len(names) != 2:
            raise ValueError(f"--pairs entry {chunk!r} must be 'A,B'")
        pairs.append(names)
    return pairs


def write_json(report, path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w") as f:
        json.dump(report, f, indent=2)


def main():
    p = argparse.ArgumentParser(
        description="MM-exact mesh contact audit (placement_lib) for the "
                    "current scene, a scene module, or a .blend file.")
    p.add_argument("--scene", default=None,
                   help="Scene module name with build_scene() to build "
                        "before auditing (searched on kit tests/ + "
                        "scripts/, plus PLACEMENT_LAB fallback)")
    p.add_argument("--load-blend", default=None,
                   help="Load a .blend file before auditing")
    p.add_argument("--output", required=True,
                   help="Output JSON path for the audit report")
    p.add_argument("--pairs", default=None,
                   help="Explicit pairs \"A,B;C,D\" (default: all "
                        "AABB-overlapping mesh pairs)")
    p.add_argument("--exclude", default="",
                   help="Comma-separated object names to exclude")
    p.add_argument("--clearance-pad-mm", type=float, default=100.0,
                   help="pair-discovery pad: objects within this AABB gap "
                        "get a clearance report (usability round-3/U8)")
    p.add_argument("--sample", choices=("verts", "verts+edges"),
                   default="verts",
                   help="Surface sampling mode (verts+edges subdivides "
                        "edges to ~1cm)")
    p.add_argument("--contact-band-mm", type=float, default=0.1,
                   help="|gap| <= this counts as TOUCHING (default 0.1)")
    p.add_argument("--ascii", action="store_true",
                   help="Print the scene height map + pair maps for "
                        "problem pairs (VLM-blind check)")
    p.add_argument("--seam-views", default=None, metavar="OUT_DIR",
                   help="Render the 4 seam-inspection views for the "
                        "worst pair into OUT_DIR")
    p.add_argument("--report-stdout", action="store_true",
                   help="Print one verdict line per pair")
    p.add_argument("--fail-on-penetration", action="store_true",
                   help="Exit 1 if any pair is PENETRATING")
    args = p.parse_args(script_argv())

    # ---- load / build scene ------------------------------------------
    try:
        if args.load_blend:
            print(f"[audit] loading .blend: {args.load_blend}")
            bpy.ops.wm.open_mainfile(filepath=args.load_blend)
        elif args.scene:
            print(f"[audit] building scene: {args.scene}")
            mod = importlib.import_module(args.scene)
            clear_scene()
            mod.build_scene()
        else:
            print("[audit] using currently-loaded scene")
    except Exception as e:  # noqa: BLE001
        print(f"[audit] ERROR building/loading scene: {e!r}")
        print(f"[audit] sys.path: {sys.path}")
        sys.exit(2)
    bpy.context.view_layer.update()

    # ---- audit ---------------------------------------------------------
    PL.clear_bvh_cache()
    try:
        pairs = parse_pairs(args.pairs) if args.pairs else None
    except ValueError as e:
        print(f"[audit] ERROR: {e}")
        sys.exit(2)
    if pairs:
        missing = sorted({n for pr in pairs for n in pr
                          if n not in bpy.data.objects})
        if missing:
            print(f"[audit] ERROR: --pairs names not in scene: {missing}")
            sys.exit(2)
    exclude = [n.strip() for n in args.exclude.split(",") if n.strip()]
    report = PL.audit_scene(clearance_pad_mm=args.clearance_pad_mm, pairs=pairs, exclude=exclude,
                            sample=args.sample,
                            contact_band_mm=args.contact_band_mm)
    report["source"] = args.load_blend or args.scene or "current-scene"
    report["exclude"] = exclude
    worst = report["pairs"][0] if report["pairs"] else None
    report["worst_pair"] = (f"{worst['a']} x {worst['b']}: "
                            f"{worst['verdict']}" if worst else None)
    write_json(report, args.output)

    # ---- stdout summary --------------------------------------------------
    print(f"[audit] source: {report['source']}")
    print(f"[audit] pairs checked: {report['pairs_checked']}  "
          f"counts: {report['state_counts']}  failed: {report['failed']}")
    if worst:
        print(f"[audit] worst: {worst['a']} x {worst['b']} — "
              f"{worst['verdict']}")
    if args.report_stdout:
        for r in report["pairs"]:
            print(f"[audit] pair {r['a']} x {r['b']}: "
                  f"{r.get('verdict', r.get('state'))}")
    print(f"[audit] report: {args.output}")

    # ---- optional ASCII maps (VLM-blind) ---------------------------------
    if args.ascii:
        txt, legend = PL.ascii_height_map(grid=48)
        print(f"[audit] height map:\n{txt}\n{legend}")
        for r in report["pairs"]:
            if r.get("severity") != "ok":
                a = bpy.data.objects.get(r["a"])
                b = bpy.data.objects.get(r["b"])
                if a and b:
                    t2, l2 = PL.ascii_pair_map(a, b)
                    print(f"[audit] pair map {r['a']} x {r['b']}:\n"
                          f"{t2}\n{l2}")

    # ---- optional seam views for the worst pair ---------------------------
    if args.seam_views and worst:
        a = bpy.data.objects.get(worst["a"])
        b = bpy.data.objects.get(worst["b"])
        try:
            sv = PL.seam_views(a, b, out_dir=args.seam_views,
                               contact_band_mm=args.contact_band_mm)
            report["seam_views"] = sv
            write_json(report, args.output)  # rewrite with render paths
            print(f"[audit] seam views: {sv['views']}")
        except Exception as e:  # noqa: BLE001
            report["seam_views_error"] = repr(e)
            write_json(report, args.output)
            print(f"[audit] seam views FAILED: {e!r}")

    # ---- exit code ---------------------------------------------------------
    if args.fail_on_penetration and report["failed"]:
        print("[audit] FAIL: penetration detected (exit 1)")
        sys.exit(1)
    print("[audit] OK: no penetration"
          if args.fail_on_penetration else "[audit] done")


if __name__ == "__main__":
    main()
