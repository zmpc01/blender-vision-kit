"""
test_v1_look.py — regression suite for the vision-loop tooling (vision-kit).

Covers:
  1. annotate layer: build → render-visible → delete leaves ZERO residue
     (KIT_ANNOT_* objects, meshes, materials, curves)
  2. _readiness(): correct flags on synthetic bright/dark/normal images
  3. validator pairing: planted floater → P0 issue + flagged-id extraction
  4. look.py subprocess on a .blend with a planted floater → exit 3
  5. look.py subprocess on a clean scene → exit 0 + annotations deleted

Run:   ./scripts/blrun.sh --background --python tests/test_v1_look.py --
"""
import os
import subprocess
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

CHECKS = {"n": 0, "fail": []}


def _check(tag, cond, detail=""):
    CHECKS["n"] += 1
    status = "PASS" if cond else "FAIL"
    print(f"  [{status}] {tag}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        CHECKS["fail"].append(tag)


def _annot_residue():
    names = [o.name for o in bpy.data.objects
             if o.name.startswith("KIT_ANNOT_")]
    mats = [m.name for m in bpy.data.materials
            if m.name.startswith("KIT_ANNOT_")]
    curves = [c.name for c in bpy.data.curves
              if c.name.startswith("KIT_ANNOT_")]
    return names, mats, curves


def test_1_annotate_roundtrip():
    print("== 1. annotate layer build/delete roundtrip")
    import annotate
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0.5))
    cube = bpy.context.active_object
    cube.name = "TestCube"
    layer = annotate.build_annotation_layer(
        flagged_ids=["TestCube"], label_ids=[("TestCube", 1)],
        grid=True, gnomon=True)
    objs, mats, curves = _annot_residue()
    _check("layer built", len(objs) >= 15,
           f"only {len(objs)} KIT_ANNOT objects")
    _check("label curve created", len(curves) >= 1)
    _check("materials created", len(mats) >= 6)
    # labels aim without error
    annotate.aim_labels_at(layer["labels"], (4, -4, 3))
    annotate.aim_labels_at(layer["labels"], (0, 0, 50), flat=True)
    _check("aim_labels_at no error", True)
    removed = annotate.delete_annotation_layer(layer)
    _check("delete returns count", removed >= 15, f"removed={removed}")
    objs, mats, curves = _annot_residue()
    _check("zero object residue", len(objs) == 0, str(objs[:3]))
    _check("zero material residue", len(mats) == 0, str(mats[:3]))
    _check("zero curve residue", len(curves) == 0, str(curves[:3]))
    # cleanup scene
    bpy.data.objects.remove(cube, do_unlink=True)


def test_2_readiness():
    print("== 2. readiness headers on synthetic images")
    from PIL import Image
    import numpy as np
    # import look.py as a module (it's a script; guard against main())
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "lookmod", os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "scripts", "look.py"))
    lookmod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lookmod)

    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        p_bright = os.path.join(tmp, "bright.png")
        p_dark = os.path.join(tmp, "dark.png")
        p_norm = os.path.join(tmp, "norm.png")
        Image.new("RGB", (64, 64), (255, 255, 255)).save(p_bright)
        Image.new("RGB", (64, 64), (5, 5, 8)).save(p_dark)
        a = np.zeros((64, 64, 3), dtype=np.uint8)
        a[:, :] = (100, 100, 100)
        a[10:30, 10:30] = (220, 60, 40)   # subject patch ~10% of frame
        Image.fromarray(a).save(p_norm)

        r = lookmod._readiness(p_bright)
        _check("bright: BLOWN-OUT flagged", "BLOWN-OUT" in r.get("flags", []),
               str(r))
        r = lookmod._readiness(p_dark)
        _check("dark: NEAR-BLACK flagged", "NEAR-BLACK" in r.get("flags", []),
               str(r))
        r = lookmod._readiness(p_norm)
        _check("normal: no flags", r.get("flags") == [], str(r))
        _check("normal: subject ~10%", 5.0 < r.get("subject_pct", 0) < 20.0,
               str(r.get("subject_pct")))


def _fresh_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def test_3_validator_pairing():
    print("== 3. validator pairing on planted floater")
    import validate_scene as vs
    _fresh_scene()
    bpy.ops.mesh.primitive_plane_add(size=10, location=(0, 0, 0))
    bpy.ops.mesh.primitive_cube_add(size=0.5, location=(2, 2, 1.2))  # floats 0.95m
    report = vs.validate_scene()
    p0 = report["issues_by_severity"]["P0"]
    p1 = report["issues_by_severity"]["P1"]
    _check("floater flagged", (p0 + p1) >= 1,
           f"P0={p0} P1={p1} issues={report['issues']}")
    _check("floating type present",
           any(i["type"] == "floating" for i in report["issues"]))
    # flagged-id extraction (mirrors look.py main)
    flagged = []
    for issue in report["issues"]:
        if issue["severity"] in ("P0", "P1"):
            if "object" in issue:
                flagged.append(issue["object"])
            elif "objects" in issue:
                flagged.extend(issue["objects"])
    _check("floater id extracted", "Cube" in flagged, str(flagged))


def _run_look(subprocess_args):
    blender_bin = os.environ.get("BLENDER_BIN")
    if not blender_bin:
        # inside Blender: find the binary from sys.argv[0] fallback
        blender_bin = bpy.app.binary_path
    cmd = [blender_bin, "--background", "--python", "scripts/look.py", "--",
           ] + subprocess_args
    return subprocess.run(cmd, capture_output=True, text=True,
                          cwd=os.path.dirname(os.path.dirname(
                              os.path.abspath(__file__))),
                          timeout=240)


def test_4_look_exit3_on_floater():
    print("== 4. look.py exit 3 on P1 floater .blend")
    _fresh_scene()
    bpy.ops.mesh.primitive_plane_add(size=10, location=(0, 0, 0))
    bpy.ops.mesh.primitive_cube_add(size=0.5, location=(2, 2, 1.2))
    out_blend = "/tmp/test_look_floater.blend"
    bpy.ops.wm.save_as_mainfile(filepath=out_blend)
    r = _run_look(["--load-blend", out_blend,
                   "--output", "/tmp/test_look_floater_out"])
    # upstream validate_scene severities: floating = P1 (P0 = below-floor /
    # >=30% intersection). look exits 3 on P0 OR P1 (fail-on-issues parity).
    _check("exit code 3 on P1 floater", r.returncode == 3,
           f"rc={r.returncode} tail={r.stdout[-400:] if r.stdout else ''}")
    _check("verdict WARN printed", "VERDICT: WARN" in r.stdout, "")
    _check("P1 count in verdict", "P1=1" in r.stdout, "")
    grid = "/tmp/test_look_floater_out/grid.png"
    _check("grid written", os.path.exists(grid)
           and os.path.getsize(grid) > 5000)
    man = "/tmp/test_look_floater_out/look_manifest.json"
    _check("manifest json written", os.path.exists(man))
    if os.path.exists(man):
        import json
        with open(man) as f:
            data = json.load(f)
        ids = [m["id"] for m in data["manifest"]]
        _check("manifest excludes KIT_ANNOT",
               not any(i.startswith("KIT_ANNOT") for i in ids), str(ids))
        _check("manifest has floater", "Cube" in ids, str(ids))
    _check("annotation cleanup printed", "annotation layer deleted" in r.stdout)


def test_5_look_clean_exit0():
    print("== 5. look.py exit 0 on clean scene")
    _fresh_scene()
    bpy.ops.mesh.primitive_plane_add(size=10, location=(0, 0, 0))
    bpy.ops.mesh.primitive_cube_add(size=0.5, location=(0, 0, 0.25))
    out_blend = "/tmp/test_look_clean.blend"
    bpy.ops.wm.save_as_mainfile(filepath=out_blend)
    r = _run_look(["--load-blend", out_blend,
                   "--output", "/tmp/test_look_clean_out"])
    _check("exit code 0 clean", r.returncode == 0,
           f"rc={r.returncode} tail={r.stdout[-300:] if r.stdout else ''}")
    _check("verdict PASS", "VERDICT: PASS" in r.stdout, "")
    _check("readiness header printed", "luma=" in r.stdout, "")
    _check("manifest printed", "manifest (" in r.stdout, "")


def main():
    print("=" * 60)
    print("test_v1_look: vision-loop tooling regression")
    print("=" * 60)
    test_1_annotate_roundtrip()
    test_2_readiness()
    test_3_validator_pairing()
    test_4_look_exit3_on_floater()
    test_5_look_clean_exit0()
    print("=" * 60)
    print(f"test_v1_look: {CHECKS['n'] - len(CHECKS['fail'])}/{CHECKS['n']} checks passed")
    if CHECKS["fail"]:
        print(f"FAILED: {CHECKS['fail']}")
        print("test_v1_look: FAIL")
        sys.exit(1)
    print("test_v1_look: ALL PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
