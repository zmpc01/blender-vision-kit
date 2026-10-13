# test_t10_export.py — D19.4 TIER 2: the export-lane subprocess suite.
#
# Walks the REAL exporter + the REAL preflight as subprocesses (the r9
# pattern: direct blender binary + --python-exit-code, foreground,
# generous timeouts — the harness reaps background processes).
#
# The fixture is a tiny escape-family scene module WRITTEN INTO scripts/
# (the exporter imports scene modules BY NAME from scripts/-only
# sys.path — a temp dir is unreachable; Blender background mode ignores
# PYTHONPATH). It self-verifies its ground truth and SATISFIES the
# exporter's own gates: markers at every f0 bound to CAM_*-named
# cameras, SHOTS spanning scene frame_start..frame_end exactly and
# contiguous, >=1 assigned action (gate 6), BOARD/DIALOG/CAMS_V3
# declared, sfx emitter conforming to {fps, events}.
#
# Run: ./run.sh --background --python tests/test_t10_export.py --
#      [out_dir]
# Convention: [t10] per check; ALL PASS at the end; exit 1 on failure.

import bpy
import json
import os
import subprocess
import sys
import tempfile

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = argv[0] if argv else tempfile.mkdtemp(prefix="t10_")
os.makedirs(OUT, exist_ok=True)
FAILS = []
NCHECK = 0

FIXTURE = "t10_fixture_scene"


def check(name, cond, detail=""):
    global NCHECK
    NCHECK += 1
    tag = "ok" if cond else "FAIL"
    print(f"[t10] {name}: {tag}" + (f" — {detail}" if not cond else ""),
          flush=True)
    if not cond:
        FAILS.append(name)


def blender_run(script, args, timeout=600):
    # Direct binary (r9 pattern) — but the exporter/preflight import
    # blender_kit at MODULE level, before their own main()-time sys.path
    # self-insert, so the subprocess needs PYTHONPATH + the
    # --python-use-system-env flag (Blender background mode ignores
    # PYTHONPATH without it). blrun.sh cannot be nested here (flock).
    env = dict(os.environ)
    env["PYTHONPATH"] = os.path.join(REPO, "scripts") + os.pathsep + \
        env.get("PYTHONPATH", "")
    cmd = [os.environ.get(
        "BLENDER_BIN", os.path.join(REPO, "tools", "blender", "blender")),
        "--background", "--factory-startup", "--python-use-system-env",
        "--python-exit-code", "1",
        "--python", script, "--"] + args
    return subprocess.run(cmd, capture_output=True, text=True,
                          cwd=REPO, timeout=timeout, env=env)


# --------------------------------------------------------------------------
# the fixture source (happy variant). Ground truth:
#   SHOTS_V3: S1 f1-24, S2 f25-48 (contiguous, spans 1..48)
#   scene.frame_start=1, frame_end=48, fps=24
#   markers at f1/f25 bound to CAM_S1/CAM_S2 (CAM_ prefix contract)
#   1 assigned action (gate 6), BOARD 1 entry (decodes), DIALOG 1 row,
#   sfx: 1 conforming event (kd_impact is in build_sfx.PATCHES)
# --------------------------------------------------------------------------
FIXTURE_SRC = '''
import bpy

FPS = 24
TOTAL_FRAMES_V3 = 48
SHOTS_V3 = [("S1", 1, 24, "establish"), ("S2", 25, 48, "push")]
CAMS_V3 = [
    ("CAM_S1", (6.0, -6.0, 3.0), (6.0, -6.0, 3.0), 50.0, (0, 0, 0), False, 0.0),
    ("CAM_S2", (7.0, -5.0, 3.5), (7.0, -5.0, 3.5), 50.0, (0, 0, 0), False, 0.0),
]
BOARD = {"Hero": ((30, 15, 45, None, 0.5, "idle"), (0.0,))}
DIALOG = [("line_one.wav", 6)]

SFX_DOC = {"fps": FPS, "meta": {"fixture": "t10"}, "events": [
    {"name": "kd_impact", "frame": 10}]}


def build_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps = FPS
    sc.frame_start = 1
    sc.frame_end = 48
    # subject + a second object so the scene is non-trivial
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0.5))
    cube = bpy.context.active_object
    cube.name = "T10Subject"
    cube.keyframe_insert(data_path="location", frame=1)
    cube.keyframe_insert(data_path="location", frame=48)  # >=1 action
    bpy.ops.mesh.primitive_plane_add(size=8, location=(0, 0, 0))
    # cameras + TRACK_TO aims
    for i, (nm, loc0, _loc1, _lens, _aim, _pj, _sh) in enumerate(CAMS_V3):
        cam_data = bpy.data.cameras.new(nm)
        cam = bpy.data.objects.new(nm, cam_data)
        sc.collection.objects.link(cam)
        cam.location = loc0
        bpy.ops.object.empty_add(location=(0, 0, 0.5))
        aim = bpy.context.active_object
        aim.name = f"Aim.S{i + 1}"
        con = cam.constraints.new(type="TRACK_TO")
        con.target = aim
        con.track_axis = "TRACK_NEGATIVE_Z"
        con.up_axis = "UP_Y"
        m = sc.timeline_markers.new(f"SHOT_S{i + 1}", frame=SHOTS_V3[i][1])
        m.camera = cam
    sc.camera = bpy.data.objects["CAM_S1"]
    return {"scene": sc}


def animate(ctx, start_frame=1, n_frames=None):
    pass


def emit_sfx_events(ctx, out_dir):
    import json as _json
    import os as _os
    with open(_os.path.join(out_dir, "sfx_events.json"), "w") as f:
        _json.dump(SFX_DOC, f)
'''

# variant builder: string replacements applied to FIXTURE_SRC
VARIANTS = {
    # t10.3: the F-TF4 repro — event keyed `id` (the app drops it 3/3)
    "sfx_id_key": (FIXTURE_SRC
                   .replace('{"name": "kd_impact", "frame": 10}',
                            '{"id": "kd_impact", "frame": 10}')),
    # t10.5: BOARD fully undecodable (every entry fails at entry[1])
    "board_undecodable": (FIXTURE_SRC
                          .replace('((30, 15, 45, None, 0.5, "idle"), (0.0,))',
                                   '((30, 15, 45, None, 0.5, "idle"),)')),
    # t10.7: bare animate — the exporter's sentinel branch TypeErrors on it
    "bare_animate": (FIXTURE_SRC
                     .replace("def animate(ctx, start_frame=1, n_frames=None):",
                              "def animate(ctx):")),
}

_write_paths = {}


def write_variant(name, src):
    path = os.path.join(REPO, "scripts", f"{name}.py")
    with open(path, "w") as f:
        f.write(src)
    _write_paths[name] = path
    return path


def cleanup_variants():
    for p in _write_paths.values():
        try:
            os.remove(p)
        except OSError:
            pass


def preflight(module_path, case_out):
    return blender_run(
        os.path.join(REPO, "scripts", "export_preflight.py"),
        ["--module", module_path, "--json",
         os.path.join(case_out, "preflight.json")])


def exporter(scene_name, case_out):
    return blender_run(
        os.path.join(REPO, "scripts", "export_previz_package.py"),
        ["--scene", scene_name, "--output", case_out,
         "--package-id", "t10_fixture", "--name", "t10 fixture"])


# ==========================================================================
# t10.1 + t10.2 — happy path (exporter green AND preflight green)
# ==========================================================================
try:
    happy_path = write_variant(FIXTURE, FIXTURE_SRC)
    case1 = os.path.join(OUT, "t1_export")
    r = exporter(FIXTURE, case1)
    check("t1.export_exit0", r.returncode == 0,
          f"rc={r.returncode} tail={r.stdout[-400:] or r.stderr[-400:]}")
    previz_path = os.path.join(case1, "previz.json")
    check("t1.previz_json_exists", os.path.isfile(previz_path))
    if os.path.isfile(previz_path):
        with open(previz_path) as _pf:
            pv = json.load(_pf)
        check("t1.story_keys_present",
              "board" in pv.get("story", {}) and "dialog" in pv.get("story", {}),
              f"story keys={sorted(pv.get('story', {}).keys())}")
        check("t1.n_sfx_events_1", pv.get("n_sfx_events") == 1,
              f"n_sfx_events={pv.get('n_sfx_events')}")
        check("t1.gates_green", "all gates green" in r.stdout,
              r.stdout[-300:])
    check("t1.sfx_file_conforms", os.path.isfile(
        os.path.join(case1, "sfx_events.json")))
    glb = [f for f in os.listdir(case1) if f.endswith(".glb")] \
        if os.path.isdir(case1) else []
    check("t1.glb_exists", bool(glb), str(glb))
    case2 = os.path.join(OUT, "t2_preflight")
    rp = preflight(happy_path, case2)
    check("t2.preflight_exit0", rp.returncode == 0,
          f"rc={rp.returncode} tail={(rp.stdout + rp.stderr)[-500:]}")

    # ==========================================================================
    # t10.3 — malformed sfx stream (F-TF4 repro): preflight rejects AND
    # exporter gate 15 rejects
    # ==========================================================================
    case3 = os.path.join(OUT, "t3_sfx")
    v3 = write_variant(FIXTURE + "_sfxid", VARIANTS["sfx_id_key"])
    r3p = preflight(v3, case3)
    check("t3.preflight_rejects", r3p.returncode == 3,
          f"rc={r3p.returncode}")
    check("t3.preflight_names_event", "name" in r3p.stdout and
          ("kind" in r3p.stdout), (r3p.stdout)[-300:])
    r3e = exporter(FIXTURE + "_sfxid", case3)
    check("t3.exporter_gate15_rejects", r3e.returncode != 0
          and "sfx_events.json: event[0]" in r3e.stdout,
          f"rc={r3e.returncode} tail={r3e.stdout[-400:]}")

    # ==========================================================================
    # t10.4 — BEATS wrong shape: shape-only WARN (never a rejection here —
    # BEATS is the canonical-copy lane's contract, zero consumers in this
    # exporter); the WARN text must name BEATS
    # ==========================================================================
    case4 = os.path.join(OUT, "t4_beats")
    src4 = FIXTURE_SRC + '\nBEATS = [("calm", "S1", 1)]\n'
    v4 = write_variant(FIXTURE + "_beats", src4)
    r4 = preflight(v4, case4)
    check("t4.beats_warn_not_reject", r4.returncode == 0,
          f"rc={r4.returncode}")
    check("t4.beats_warn_names_beats", "BEATS" in r4.stdout, r4.stdout[-300:])

    # ==========================================================================
    # t10.5 — BOARD fully undecodable: gate 4 (strengthened) rejects the
    # exporter; preflight S2 rejects too
    # ==========================================================================
    case5 = os.path.join(OUT, "t5_board")
    v5 = write_variant(FIXTURE + "_board", VARIANTS["board_undecodable"])
    r5e = exporter(FIXTURE + "_board", case5)
    check("t5.exporter_gate4_rejects", r5e.returncode != 0
          and "every entry" in r5e.stdout and "BOARD" in r5e.stdout,
          f"rc={r5e.returncode} tail={r5e.stdout[-400:]}")
    r5p = preflight(v5, case5)
    check("t5.preflight_rejects", r5p.returncode == 3,
          f"rc={r5p.returncode}")

    # ==========================================================================
    # t10.6 — short CAMS row: preflight exit 3, message names CAMS_V3[i]
    # ==========================================================================
    case6 = os.path.join(OUT, "t6_cams")
    src6 = FIXTURE_SRC.replace(
        '("CAM_S2", (7.0, -5.0, 3.5), (7.0, -5.0, 3.5), 50.0, (0, 0, 0), False, 0.0),',
        '("CAM_S2", (7.0, -5.0, 3.5), (7.0, -5.0, 3.5), 50.0),')
    v6 = write_variant(FIXTURE + "_cams", src6)
    r6 = preflight(v6, case6)
    check("t6.preflight_rejects", r6.returncode == 3, f"rc={r6.returncode}")
    check("t6.message_names_constant_row", "CAMS_V3[1]" in r6.stdout,
          r6.stdout[-300:])

    # ==========================================================================
    # t10.7 — bare `def animate(ctx)`: preflight S1 rejects (the exporter's
    # sentinel branch would TypeError post-render)
    # ==========================================================================
    case7 = os.path.join(OUT, "t7_animate")
    v7 = write_variant(FIXTURE + "_bare", VARIANTS["bare_animate"])
    r7 = preflight(v7, case7)
    check("t7.preflight_rejects", r7.returncode == 3, f"rc={r7.returncode}")
    check("t7.message_names_animate", "animate" in r7.stdout, r7.stdout[-300:])

finally:
    cleanup_variants()


print(f"[t10] {NCHECK} checks, {len(FAILS)} failed")
if FAILS:
    print("[t10] FAILURES:", FAILS)
    sys.exit(1)
print("[t10] ALL PASS")
