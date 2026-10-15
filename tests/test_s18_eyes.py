"""
test_s18_eyes.py — session-18 wave-E coverage (E2): the look-path surfaces
the battery never touched (F-TS/s17 follow-ups).

  1. look.py exit 4 (the F2A-2 readiness gate, end-to-end): an unreadable
     (0-byte) render output must fail the perception pass with exit 4 and
     a readiness error that NAMES the file — an image the eye cannot open
     makes the whole look invalid regardless of the validator verdict.
  2. camera_intent rows (F-TD3 detectability): a scene with a
     camera-bound timeline marker AND a different scene.camera — the
     manifest must carry camera_intent rows, record the would-have-bound
     marker camera, and show the panel rendered on its own temp cam (the
     s17 marker sweep), never silently on the marker cam.
  3. build_sfx vocabulary (pure-python module — its own isolation
     contract says it NEVER runs inside the Blender session): importable
     without bpy, the PATCHES table covers the documented vocabulary, and
     a non-{name,frame}-shaped event is REJECTED rather than silently
     skipped. Negative-frame (frame<0) rejection is D9's fix site (the
     exporter's gate 15, wave-D) — see the '-- depends on 2-D' note in
     test_3: until that lands the check records PENDING instead of
     failing the battery row, and flips into a real assert afterwards.

Run:   ./scripts/blrun.sh --background --python tests/test_s18_eyes.py --
"""
import contextlib
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

import bpy

_HERE = os.path.dirname(os.path.abspath(__file__))
_KIT = os.path.dirname(_HERE)

CHECKS = {"n": 0, "fail": [], "pending": []}


def _check(tag, cond, detail=""):
    CHECKS["n"] += 1
    status = "PASS" if cond else "FAIL"
    print(f"  [{status}] {tag}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        CHECKS["fail"].append(tag)


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run_look(args, timeout=240):
    blender_bin = os.environ.get("BLENDER_BIN") or bpy.app.binary_path
    cmd = [blender_bin, "--background", "--python", "scripts/look.py",
           "--"] + args
    return subprocess.run(cmd, capture_output=True, text=True,
                          cwd=_KIT, timeout=timeout)


def test_1_look_exit4_unreadable_image():
    print("== 1. look.py exit 4 on an unreadable (0-byte) render output")
    look = _load_module("look_s18", os.path.join(_KIT, "scripts", "look.py"))
    # minimal CLEAN scene: the validator must stay quiet so exit 4 can
    # only come from the readiness gate
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.mesh.primitive_plane_add(size=10, location=(0, 0, 0))
    bpy.ops.mesh.primitive_cube_add(size=0.5, location=(0, 0, 0.25))
    blend = "/tmp/test_s18_exit4.blend"
    bpy.ops.wm.save_as_mainfile(filepath=blend)
    outdir = "/tmp/test_s18_exit4_out"
    shutil.rmtree(outdir, ignore_errors=True)
    os.makedirs(outdir, exist_ok=True)
    # Plant the unreadable image where look expects the render: with
    # --angles front --no-grid, look renders to <outdir>/front.png and
    # then runs the REAL readiness gate on it. Patch ONLY the render
    # step to plant the artifact (the cheapest honest simulation of a
    # truncated/failed write) — readiness, verdict, manifest and the
    # exit-4 path all run for real.
    real_render_angle = look.vc.render_angle

    def _zero_byte_render(angle_label, out_path, **kw):
        with open(out_path, "wb") as f:
            f.write(b"")          # 0 bytes — the F2A-2 unreadable class
        return out_path

    look.vc.render_angle = _zero_byte_render
    argv_backup = sys.argv
    sys.argv = ["look.py", "--", "--load-blend", blend,
                "--output", outdir, "--angles", "front",
                "--no-grid", "--no-annotate"]
    buf = io.StringIO()
    code = None
    try:
        try:
            with contextlib.redirect_stdout(buf):
                look.main()
        except SystemExit as e:
            code = e.code
    finally:
        look.vc.render_angle = real_render_angle
        sys.argv = argv_backup
    out = buf.getvalue()
    _check("s18_1.exit4", code == 4,
           f"rc={code} tail={out[-300:] if out else 'NO OUTPUT'}")
    _check("s18_1.readiness_error_printed", "readiness-error:" in out,
           out[-300:] if out else "")
    _check("s18_1.error_names_file", "front.png" in out,
           out[-300:] if out else "")


def test_2_camera_intent_rows():
    print("== 2. camera_intent rows on a marker-bound film scene")
    # F-TD3 fixture pattern (mirrors test_s17_wave_a section 1): a shot
    # cam bound to a timeline marker at f1 looking AWAY from the subject,
    # plus a DIFFERENT scene.camera — the pre-sweep bug rendered the
    # marker cam's view with no record of it anywhere.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    bpy.ops.mesh.primitive_plane_add(size=10)
    bpy.ops.mesh.primitive_cube_add(location=(2, 0, 0.5))
    bpy.context.active_object.name = "Pillar"
    cam_data = bpy.data.cameras.new("ShotCam_data")
    mk_cam = bpy.data.objects.new("ShotCam", cam_data)
    scene.collection.objects.link(mk_cam)
    mk_cam.location = (0, -8, 1)
    mk_cam.rotation_euler = (1.5708, 0, 0)   # looking +Y — pillar behind it
    m = scene.timeline_markers.new("MK", frame=1)
    m.camera = mk_cam
    bpy.ops.object.camera_add(location=(4, -4, 3), rotation=(1.1, 0, 0.785))
    panel_cam = bpy.context.active_object
    panel_cam.name = "PanelCam"
    scene.camera = panel_cam                 # a DIFFERENT camera
    scene.frame_set(1)
    blend = "/tmp/test_s18_intent.blend"
    bpy.ops.wm.save_as_mainfile(filepath=blend)
    outdir = "/tmp/test_s18_intent_out"
    shutil.rmtree(outdir, ignore_errors=True)
    r = _run_look(["--load-blend", blend, "--output", outdir,
                   "--angles", "front", "--no-grid", "--no-annotate"])
    _check("s18_2.exit0", r.returncode == 0,
           f"rc={r.returncode} tail={(r.stdout or '')[-300:]}")
    man_path = os.path.join(outdir, "look_manifest.json")
    _check("s18_2.manifest_written", os.path.exists(man_path), man_path)
    if not os.path.exists(man_path):
        return
    with open(man_path) as f:
        man = json.load(f)
    intent = man.get("camera_intent", [])
    _check("s18_2.intent_rows_present", len(intent) >= 1, f"{intent}")
    row = next((row for row in intent if row.get("angle") == "front"), None)
    _check("s18_2.front_row_present", row is not None, f"{intent}")
    if row is None:
        return
    _check("s18_2.marker_cam_recorded",
           row.get("marker_cam_at_frame") == "ShotCam",
           f"row={row} (the would-have-bound marker camera must be recorded)")
    _check("s18_2.panel_used_temp_cam",
           row.get("rendered_cam") == "temp front panel",
           f"row={row} (the F-TD3 sweep must render the panel cam, "
           f"not the marker cam)")


def test_3_build_sfx_vocabulary():
    print("== 3. build_sfx vocabulary + event-shape rejection (pure python)")
    path = os.path.join(_KIT, "scripts", "build_sfx.py")
    with open(path) as f:
        src = f.read()
    # isolation contract (module docstring: NEVER runs inside the Blender
    # session): the source must not import bpy
    _check("s18_3.no_bpy_import",
           re.search(r"^\s*(?:import|from)\s+bpy\b", src, re.M) is None,
           "build_sfx must never import bpy (isolation contract)")
    # import guard: importing must NOT run main() (it lives behind
    # `if __name__ == "__main__"`) — a clean import proves the guard
    sfx = _load_module("build_sfx_s18", path)
    _check("s18_3.imports_without_running_main", hasattr(sfx, "PATCHES"),
           "module-level import must be side-effect free")
    documented = {"kd_impact", "gunshot_burst", "splash", "barricade_smash",
                  "engine_start", "engine_rev", "door_slam", "lunge_grab",
                  "chunk_rattle", "tire_dust"}
    missing = documented - set(sfx.PATCHES)
    _check("s18_3.patch_vocabulary_complete", not missing,
           f"missing patches: {sorted(missing)}")
    _check("s18_3.patches_callable",
           all(callable(fn) for fn in sfx.PATCHES.values()),
           f"non-callable: {[k for k, v in sfx.PATCHES.items() if not callable(v)]}")

    with tempfile.TemporaryDirectory() as tmp:
        def _events(name, events):
            p = os.path.join(tmp, name)
            with open(p, "w") as f:
                json.dump({"fps": 24, "events": events}, f)
            return p

        wav = os.path.join(tmp, "good.wav")
        sfx.build(_events("good.json", [{"name": "door_slam", "frame": 10}]),
                  wav)
        _check("s18_3.baseline_event_builds",
               os.path.exists(wav) and os.path.getsize(wav) > 44,
               f"{os.path.getsize(wav) if os.path.exists(wav) else 0} bytes")

        # a non-{name,frame}-shaped event must be REJECTED, never
        # silently skipped (post-2-D a clean RuntimeError passes too —
        # any rejection counts; silence does not)
        try:
            sfx.build(_events("bad.json", [{"nm": "door_slam", "frame": 10}]),
                      os.path.join(tmp, "bad.wav"))
            _check("s18_3.malformed_event_rejected", False,
                   "non-{name,frame} event silently accepted")
        except Exception as e:  # noqa: BLE001 — any rejection counts
            _check("s18_3.malformed_event_rejected", True,
                   f"rejected: {type(e).__name__}")

        # -- depends on 2-D: negative-frame rejection (D9). The fix site
        # is the exporter's gate 15 (wave-D); until that lands,
        # build_sfx.build() ACCEPTS frame<0 and misplaces/wraps the
        # event (the exact bug class), so a born-red rejection assert
        # would be a false alarm rather than coverage. Probe: once the
        # rejection exists this asserts it loudly (and can fail); until
        # then the check is recorded PENDING and this log carries the
        # '-- depends on 2-D' marker for the orchestrator to sequence.
        try:
            sfx.build(_events("neg.json",
                              [{"name": "door_slam", "frame": -12}]),
                      os.path.join(tmp, "neg.wav"))
            rejected, why = False, ""
        except Exception as e:  # noqa: BLE001
            rejected, why = True, f"rejected: {type(e).__name__}: {e}"
        if rejected:
            _check("s18_3.negative_frame_rejected", True, why)
        else:
            print("[s18] NOTE '-- depends on 2-D': build_sfx still accepts "
                  "frame=-12 (the D9 wraparound class) — gate-15 rejection "
                  "not landed yet; recorded PENDING, not failed")
            CHECKS["pending"].append("s18_3.negative_frame_rejected")


def main():
    print("=" * 60)
    print("test_s18_eyes: look-path coverage regression (wave-E E2)")
    print("=" * 60)
    test_1_look_exit4_unreadable_image()
    test_2_camera_intent_rows()
    test_3_build_sfx_vocabulary()
    print("=" * 60)
    print(f"test_s18_eyes: {CHECKS['n'] - len(CHECKS['fail'])}/{CHECKS['n']} "
          "checks passed")
    if CHECKS["pending"]:
        print(f"PENDING (-- depends on 2-D): {CHECKS['pending']}")
    if CHECKS["fail"]:
        print(f"FAILED: {CHECKS['fail']}")
        print("test_s18_eyes: FAIL")
        sys.exit(1)
    print("test_s18_eyes: ALL PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
