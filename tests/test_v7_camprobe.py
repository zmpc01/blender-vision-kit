"""test_v7_camprobe.py — V7 regression: look.py --probe-camera (F-TD12,
D-TD22 REV-2). The recession-occlusion class: a depth structure between
a camera and its subject must be NAMED by the probe, and the S9 class
(animated occluder) must resolve across frames.

Fixture (peer-review coordinates, validator-clean):
  Ground        plane size 10 @ origin
  SubjectCube   cube 1.2 @ (0, 1, 0.6)      — spans y 0.4..1.6, z 0..1.2
  OccluderWall  cube scaled (2, 0.05, 2) @ (0, -3, 1.0) — GROUND-STANDING
                (a floating plane would trip the validator's floating P1
                and exit-3 would break the probe-only assertions)
  BlockedCam    @ (0, -4, 1.0) rot (90,0,0)   → +Y ray at z=1 → wall @0.975
  ClearCam      @ (0, -4, 1.0) rot (90,0,180) → -Y ray → clear (sky)
  SideCam       @ (3, 1, 0.8) rot (90,0,-90)  → -X ray → SubjectCube @2.4

Animated (the S9 class): the wall's location.x is keyed 0 @f1 → 5 @f24
(off the x=0 ray) — probe at f1 names the wall, at f24 names the cube.

Runs look.py as a subprocess (v1 convention) + --factory-startup
(r9 robustness) with a raised timeout (two nested Blender invocations).
"""
import json
import os
import subprocess
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS = os.path.abspath(os.path.join(_HERE, "..", "scripts"))
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for _p in (_SCRIPTS,):
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

OUT = os.path.join(_REPO_ROOT, "output", "tests", "v7_results.json")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
FAIL = []
BLENDER_BIN = os.environ.get(
    "BLENDER_BIN",
    os.path.join(_REPO_ROOT, "tools", "blender", "blender"))
if not os.path.exists(BLENDER_BIN):  # sibling fallback (agent-kit layout)
    ALT = "/home/z/blender-agent-kit/tools/blender/blender"
    if os.path.exists(ALT):
        BLENDER_BIN = ALT

FIXTURE = os.path.join(tempfile.gettempdir(), "test_v7_camprobe_fixture.blend")
# the look runs write their manifest under output/<fixture-base>/look
MANIFEST = os.path.join(_REPO_ROOT, "output", "test_v7_camprobe_fixture",
                        "look", "look_manifest.json")


def _drop_stale_manifest():
    """F8 (s19 triage): output/ is NOT wiped between battery runs, and the
    old code read the manifest through `if os.path.exists(...)` fallbacks
    (incl. a legacy output/look_test_v7 path) — so V7d-V7o could green on
    the PREVIOUS battery's manifest when a look died before writing.
    Delete-before-run: after each run_look the manifest must EXIST again
    (a fresh write), else the checks fail loudly. Existence-after-delete
    is the freshness proof; no mtime window needed."""
    if os.path.exists(MANIFEST):
        os.remove(MANIFEST)


def check(label, got, expect, tol=None):
    ok = False
    if tol is not None and isinstance(got, (int, float)) \
            and isinstance(expect, (int, float)):
        ok = abs(got - expect) <= tol
    else:
        ok = got == expect
    if not ok:
        FAIL.append(label)
    print(f"[{'ok' if ok else 'FAIL'}] {label}: got={got} expect={expect}")
    return ok


def build_fixture():
    """Build the fixture scene in-process (this file runs inside Blender)."""
    import bpy
    import math
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.mesh.primitive_plane_add(size=10, location=(0, 0, 0))
    bpy.context.active_object.name = "Ground"
    bpy.ops.mesh.primitive_cube_add(size=1.2, location=(0, 1, 0.6))
    bpy.context.active_object.name = "SubjectCube"
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, -3, 1.0))
    wall = bpy.context.active_object
    wall.name = "OccluderWall"
    wall.scale = (2.0, 0.05, 2.0)
    # the animated (S9-class) leg: slide the wall off the x=0 ray by f24
    wall.location.x = 0.0
    wall.keyframe_insert(data_path="location", index=0, frame=1)
    wall.location.x = 5.0
    wall.keyframe_insert(data_path="location", index=0, frame=24)

    def cam(name, loc, rot):
        bpy.ops.object.camera_add(location=loc, rotation=rot)
        c = bpy.context.active_object
        c.name = name
        return c

    cam("BlockedCam", (0, -4, 1.0), (math.radians(90), 0, 0))
    cam("ClearCam", (0, -4, 1.0), (math.radians(90), 0, math.radians(180)))
    cam("SideCam", (3, 1, 0.8), (math.radians(90), 0, math.radians(90)))
    bpy.context.scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=FIXTURE)


def run_look(extra, timeout=600):
    # Through blrun.sh: the render path needs its libEGL/LD_LIBRARY_PATH
    # (workbench renders fail with "Couldn't open libEGL.so.1" when the
    # binary is invoked directly). blrun also sets PYTHONPATH=scripts.
    cmd = [os.path.join(_REPO_ROOT, "scripts", "blrun.sh"),
           "--background", "--factory-startup",
           "--python", os.path.join(_SCRIPTS, "look.py"), "--",
           "--load-blend", FIXTURE] + extra
    env = dict(os.environ)
    env["BLENDER_BIN"] = BLENDER_BIN
    # F-TD10 flock bypass: nested blrun under the outer blrun-held lock
    # (the battery proved rc=90 LOCK-HELD without it — suite 8 artifact)
    env["BLRUN_FORCE"] = "1"
    return subprocess.run(cmd, capture_output=True, text=True,
                          timeout=timeout, env=env)


if __name__ == "__main__" and os.environ.get("V7_PARENT") is None:
    # -------- parent mode: build fixture, run child looks, assert --------
    build_parent = [BLENDER_BIN, "--background", "--factory-startup",
                    "--python-use-system-env", "--python", os.path.abspath(__file__)]
    r = subprocess.run(build_parent, capture_output=True, text=True,
                       timeout=300, env={**os.environ, "V7_PARENT": "1",
                                         "PYTHONPATH": _SCRIPTS})
    if r.returncode != 0:
        FAIL.append("fixture build failed")
        print(r.stderr[-2000:])

    # probe-only run at f1 (the wall blocks BlockedCam)
    _drop_stale_manifest()
    r1 = run_look(["--frame", "1", "--angles", "none",
                   "--probe-camera", "BlockedCam,ClearCam,SideCam",
                   "--probe-camera", "NoSuchCam", "--no-fail-on-issues"])
    check("V7a probe-only run exit 0", r1.returncode, 0)
    check("V7b stdout names the wall first",
          "PROBE cam=BlockedCam" in r1.stdout
          and "object=OccluderWall" in r1.stdout, True)
    check("V7c ClearCam reads clear", "cam=ClearCam frame=1 status=clear"
          in r1.stdout.replace("[look] ", ""), True)
    # F8: no fallback reads — the probe run must have freshly re-written
    # the manifest we deleted above
    man1 = json.load(open(MANIFEST)) if os.path.exists(MANIFEST) else None
    if man1 is None:
        FAIL.append("V7-manifest missing after delete-before-run (run_look "
                    "did not write it — look crashed pre-write?)")
        print("manifest not found at", MANIFEST)
    else:
        rows = {r["camera"]: r for r in man1.get("camera_probes", [])}
        check("V7d manifest carries camera_probes", len(rows) >= 4, True)
        w = rows.get("BlockedCam", {})
        check("V7e f1 wall hit object", w.get("object"), "OccluderWall")
        check("V7f f1 wall distance 0.975", w.get("distance_m"), 0.975, tol=0.02)
        check("V7g ClearCam clear row", rows.get("ClearCam", {}).get("status"),
              "clear")
        s = rows.get("SideCam", {})
        check("V7h SideCam names the subject", s.get("object"), "SubjectCube")
        check("V7i SideCam distance 2.4", s.get("distance_m"), 2.4, tol=0.05)
        check("V7j unknown camera = missing row, no exit",
              rows.get("NoSuchCam", {}).get("status"), "missing")

    # probe at f24 (the wall slid off-ray: BlockedCam now sees the cube)
    _drop_stale_manifest()
    r2 = run_look(["--frame", "24", "--angles", "none",
                   "--probe-camera", "BlockedCam", "--no-fail-on-issues"])
    check("V7k f24 probe exit 0", r2.returncode, 0)
    if os.path.exists(MANIFEST):
        man2 = json.load(open(MANIFEST))
    else:
        man2 = {}
        FAIL.append("V7-manifest(f24) missing after delete-before-run")
    row2 = (man2.get("camera_probes") or [{}])[0]
    check("V7l f24 wall moved away — subject named",
          row2.get("object"), "SubjectCube")
    check("V7m f24 subject distance 4.4", row2.get("distance_m"), 4.4, tol=0.05)

    # render-path sanity: a normal (non-probe) run must still work
    _drop_stale_manifest()   # F8: V7o must read r3's OWN manifest
    r3 = run_look(["--frame", "1", "--angles", "front",
                   "--w", "320", "--h", "240"])
    check("V7n normal look still exit 0", r3.returncode, 0)
    check("V7o normal manifest has empty camera_probes key",
          json.load(open(MANIFEST)).get("camera_probes")
          if os.path.exists(MANIFEST) else None, [])

    results = {"suite": "V7 camprobe", "fail": FAIL, "n_cases": 15}
    with open(OUT, "w") as f:
        json.dump(results, f, indent=2)
    print(f"[V7] {'ALL PASS' if not FAIL else 'FAILURES: ' + str(FAIL)}")
    if FAIL:
        raise SystemExit(1)
else:
    # -------- child mode: just build the fixture, exit --------
    build_fixture()
    print("[V7] fixture built:", FIXTURE)
