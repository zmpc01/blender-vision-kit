# test_t10_preflight_prop.py — D19.4 TIER 1: the decode-parity property test.
#
# PURE PYTHON (no Blender) — runs in milliseconds. Import the REAL
# _collect_story (exporter's decoders = behavioral source of truth) and the
# preflight's S2 checker under STUBBED bpy/blender_kit, then assert the
# drift-rot property in BOTH directions (critique 2-a §5):
#
#     decoder drops/raises  ==>  S2 rejects   (S2-looser rot is visible)
#     decoder accepts       ==>  S2 accepts   (S2-stricter rot is visible)
#
# The one AGREED exception: LUNGE_V3's silent value-drop (exporter:625-627)
# maps to a preflight WARN by design (D19 REV-2 notes it; not exporter-gated
# this wave).
#
# Run: python3 tests/test_t10_preflight_prop.py   (system python; no bpy)
# Convention: [t10p] per check; ALL PASS at the end; exit 1 on failure.

import sys
import os
import types
import traceback

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(REPO, "scripts")
sys.path.insert(0, SCRIPTS)

# ---- stubs BEFORE importing the kit modules (they import bpy at top) ----
if "bpy" not in sys.modules:
    _bpy = types.ModuleType("bpy")
    _bpy.ops = types.SimpleNamespace()
    sys.modules["bpy"] = _bpy
if "blender_kit" not in sys.modules:
    _bk = types.ModuleType("blender_kit")
    _bk._import_scene_file = lambda *a, **k: None
    _bk.atmo_objects = lambda scene: []
    _bk.render_hidden_objects = lambda scene: []
    _bk.script_argv = lambda: sys.argv[1:]
    # REV-3/F2C-1: export_previz_package now imports the shared RNA filter
    # at module level; the stub mirrors the identity behavior (no bpy RNA
    # here — the filter's real logic is exercised in-Blender by tier 2).
    _bk.filter_rna_kwargs = lambda op_id, kwargs, tag="": kwargs
    sys.modules["blender_kit"] = _bk
try:
    import build_sfx  # noqa: F401  (real PATCHES if numpy behaves)
except Exception:
    _bsfx = types.ModuleType("build_sfx")
    _bsfx.PATCHES = ()
    sys.modules["build_sfx"] = _bsfx

import export_preflight as PF          # noqa: E402
import export_previz_package as EPP    # noqa: E402

FAILS = []
NCHECK = 0


def check(name, cond, detail=""):
    global NCHECK
    NCHECK += 1
    tag = "ok" if cond else "FAIL"
    print(f"[t10p] {name}: {tag}" + (f" — {detail}" if not cond else ""))
    if not cond:
        FAILS.append(name)


def mod_with(**consts):
    m = types.ModuleType("pf_prop_mod")
    for k, v in consts.items():
        setattr(m, k, v)
    return m


def s2_rejects(m):
    """Run the S2 checks (schema + shots + beats) on a module; True iff any
    REJECT was recorded. WARNs never fail."""
    rep = PF.Report()
    try:
        PF.s2_schema(m, rep)
        PF.s2_shots(m, rep)
        PF.s2_beats(m, rep)
    except Exception:
        # a preflight crash on module input is ITSELF an S2 failure
        # (the exporter must never see the preflight die first)
        return True
    return bool(rep.rejects)


def decoder_outcome(m):
    """(kind, story) — kind in {raise, drop, accept} per the REAL
    _collect_story."""
    try:
        story = EPP._collect_story(m, 24.0, 1)
    except Exception:
        return "raise", None
    # per-entry/per-value DROPPERS (the only two in the collector):
    if getattr(m, "BOARD", None) and not story.get("board"):
        return "drop", story          # NOTE-and-drop (exporter:594-596)
    if getattr(m, "LUNGE_V3", None) is not None:
        declared_vals = len(m.LUNGE_V3)
        landed = len(story.get("lunge", {}))
        if landed < declared_vals:
            return "drop", story      # silent value-drop (exporter:625-627)
    return "accept", story


# ---- VALID base values (one per STORY_SOURCES constant + the tables) ----
BASE = {
    "DIALOG": [("clip_a.wav", 10)],
    "KNOCKDOWNS_V3": [("kd1", 1.0, 0.5, "sweep")],
    "CHASE_FALLS_V3": {0: 1.5},
    "MUZZLE_BURSTS_V3": [(10, 20, 3)],
    "JEEP_X_V3": [(0.0, 0.5)],
    "_V3_SEG": [(0.0, 1.0, 1.0, 2.0)],
    "BOARD": {"B1": ((30, 15, 45, None, 0.5, "pose"), (0.0,))},
    "RUN_PARAMS": {"hero": {"speed": 1.2, "style": "walk"}},
    "MOTION_POLICY": {"intended_static": ["a"], "intended_subject_tree": "t"},
    "FLATNESS_POLICY": {"A": (10, 20)},
    "LUNGE_V3": {"y_offsets": [(0.0, 0.1)], "speed": 1.0},
    "RB_FALLS": ["rb1", 3],
    "RB_KD": ["rb2"],
    "T_DRIVE": 12.0,
    "BARRICADE_T_V3": 1.0,
    "BARRICADE_Y_V3": -2.0,
    "RUN_SPEED": 1.0,
    "RUN_START_Y": 0.0,
    "TOTAL_FRAMES_V3": 48,
    "HERO_MODE": "off",
    "CAMS_V3": [("CAM_S1", (0, 0, 5), (0, 0, 0), 50.0, (0, 0, 0), False, 0.1)],
    "SHOTS_V3": [("S1", 1, 48, "test")],   # not in STORY_SOURCES; s2_shots
}

# ---- 1. base direction: decoder accepts ==> S2 accepts (per constant) ----
for attr, val in BASE.items():
    m = mod_with(**{attr: val})
    kind, _ = decoder_outcome(m)
    rejects = s2_rejects(m)
    check(f"base.{attr}.decoder_accepts", kind == "accept",
          f"decoder outcome={kind}")
    check(f"base.{attr}.s2_accepts", not rejects,
          "S2 rejected a VALID base value")

# ---- 2. drop/raise direction: decoder fails ==> S2 rejects ----
# Variants: (name, attr, broken_value, expected_decoder_outcome)
VARIANTS = [
    ("board_entry_missing_extra", "BOARD",
     {"B1": ((30, 15, 45, None, 0.5, "pose"),)}, "drop"),
    ("board_main_bad_cast", "BOARD",
     {"B1": (("x", 15, 45, None, 0.5, "pose"), (0.0,))}, "drop"),
    ("board_not_a_dict", "BOARD", [("B1", ((30, 15, 45, None, 0.5, "pose"),
                                           (0.0,)))], "raise"),
    ("runparams_none_value", "RUN_PARAMS",
     {"hero": {"speed": None}}, "raise"),
    ("runparams_flat_value", "RUN_PARAMS", {"hero": "flat"}, "raise"),
    ("rb_falls_none_item", "RB_FALLS", ["rb1", None], "raise"),
    ("rb_kd_none_item", "RB_KD", [None], "raise"),
    ("chase_falls_not_a_dict", "CHASE_FALLS_V3", [(0, 1.5)], "raise"),
    ("chase_falls_bad_key", "CHASE_FALLS_V3", {"x": 1.5}, "raise"),
    ("motion_policy_not_a_dict", "MOTION_POLICY", [("a",)], "raise"),
    ("flatness_bad_row", "FLATNESS_POLICY", {"A": (10,)}, "raise"),
    ("dialog_short_row", "DIALOG", [("clip_only",)], "raise"),
    ("dialog_bad_cast", "DIALOG", [("clip", None)], "raise"),
    ("knockdowns_short_row", "KNOCKDOWNS_V3", [("kd1", 1.0, 0.5)], "raise"),
    ("muzzle_short_row", "MUZZLE_BURSTS_V3", [(10, 20)], "raise"),
    ("jeep_short_row", "JEEP_X_V3", [(0.0,)], "raise"),
    ("seg_short_row", "_V3_SEG", [(0.0, 1.0, 1.0)], "raise"),
    ("cams_short_row", "CAMS_V3",
     [("CAM_S1", (0, 0, 5), (0, 0, 0), 50.0)], "raise"),
    ("cams_none_vec", "CAMS_V3",
     [("CAM_S1", None, (0, 0, 0), 50.0, (0, 0, 0), False, 0.0)], "raise"),
    # NOTE: SHOTS_V3 is NOT consumed by _collect_story — its real consumer
    # is the shot-table assembly in main() (exporter:1120-1131, row[3]
    # IndexError). The decoder-outcome property does not apply; the S2
    # rejection is asserted directly in 2b below.
    ("t_drive_bad_scalar", "T_DRIVE", {}, "raise"),
    ("total_frames_bad_scalar", "TOTAL_FRAMES_V3", "many", "raise"),
]
for name, attr, broken, expect in VARIANTS:
    m = mod_with(**{attr: broken})
    kind, _ = decoder_outcome(m)
    check(f"variant.{name}.decoder_{expect}", kind == expect,
          f"decoder outcome={kind}, expected {expect}")
    if kind in ("raise", "drop"):
        check(f"variant.{name}.s2_rejects", s2_rejects(m),
              "decoder fails but S2 accepted — S2-looser rot")

# ---- 3. accept-set superset: decoder's LENIENCY must not be over-gated ----
# >=n semantics: extra row fields are silently ignored by the decoders —
# S2 must NOT reject them (an exact-width check would false-reject real
# modules; critique 2-a arity-table preamble).
LENIENCY = [
    ("dialog_extra_field", "DIALOG", [("clip_a.wav", 10, "extra")]),
    ("knockdowns_extra_field", "KNOCKDOWNS_V3",
     [("kd1", 1.0, 0.5, "sweep", "extra")]),
    ("cams_extra_field", "CAMS_V3",
     [("CAM_S1", (0, 0, 5), (0, 0, 0), 50.0, (0, 0, 0), False, 0.1, 9)]),
    ("lunge_extra_key", "LUNGE_V3", {"y_offsets": [(0.0, 0.1)], "junk": 1}),
]
for name, attr, val in LENIENCY:
    m = mod_with(**{attr: val})
    kind, _ = decoder_outcome(m)
    check(f"leniency.{name}.decoder_accepts", kind == "accept",
          f"decoder outcome={kind}")
    check(f"leniency.{name}.s2_accepts", not s2_rejects(m),
          "S2 stricter than the decoder — S2-stricter rot")

# ---- 4. the AGREED LUNGE exception: decoder value-drop ==> S2 warns ----
m = mod_with(LUNGE_V3={"y_offsets": [(0.0, 0.1)], "speed": "fast"})
kind, _ = decoder_outcome(m)
check("lunge_exception.decoder_drops", kind == "drop",
      f"decoder outcome={kind}")
rep = PF.Report()
PF.s2_schema(m, rep)
check("lunge_exception.s2_warns_not_rejects",
      not rep.rejects and any("LUNGE" in w for w in rep.warns),
      f"rejects={rep.rejects} warns={len(rep.warns)}")

# ---- 5. preflight never crashes on garbage input (fail-closed contract) --
for name, attr, junk in [
        ("garbage_list", "DIALOG", [None]),
        ("garbage_none", "KNOCKDOWNS_V3", None),
        ("garbage_scalar", "RUN_SPEED", object())]:
    m = mod_with(**{attr: junk})
    try:
        r = s2_rejects(m)
        check(f"garbage.{name}.no_crash", True)
    except Exception as e:
        check(f"garbage.{name}.no_crash", False, repr(e))

# ---- 2b. SHOTS short row: S2 rejects directly (its consumer is the
# shot-table assembly in main(), exporter:1120-1131 — outside the
# collector, so the decoder-outcome property does not apply).
m = mod_with(SHOTS_V3=[("S1", 1, 48)])
check("variant.shots_short_row.s2_rejects", s2_rejects(m),
      "short SHOTS row must reject (the real consumer IndexErrors opaquely)")

# ===========================================================================
# REV-3 sections (session-17, audit 2-c). These cover S3/B3/coverage —
# ALL outside the _collect_story oracle (like 2b above), so each check
# asserts the preflight behavior directly against the exporter behavior
# established by probe/code-read, not via the decoder property.
# ===========================================================================

# ---- 6. F2C-3 flip: a shot with no exact CAM_<sid> row is a WARN (the
# exporter merges cam specs as an OPTIONAL exact-name merge, so the shot
# exports green); the paired REJECT moved to B3, firing only when the
# camera OBJECT CAM_<sid> is missing from the built scene too.
m = mod_with(SHOTS_V3=[("S1", 1, 48, "test")],
             CAMS_V3=[("CAM_S9", (0, 0, 5), (0, 0, 0), 50.0,
                       (0, 0, 0), False, 0.1)])
rep = PF.Report()
missing, legacy = PF.s3_coherence(m, [("S1", 1, 48)], rep)
check("s3flip.no_reject", not rep.rejects,
      f"exact-name-missing must WARN now; rejects={rep.rejects}")
check("s3flip.warns_missing_row",
      any("no CAMS row named 'CAM_S1'" in w for w in rep.warns),
      f"warns={rep.warns}")
check("s3flip.missing_list_returned", missing == ["S1"] and legacy is False,
      f"missing={missing} legacy={legacy}")

m = mod_with(SHOTS_V3=[("S1", 1, 48, "test")],
             CAMS_V3=[("CAM_S1", (0, 0, 5), (0, 0, 0), 50.0,
                       (0, 0, 0), False, 0.1)])
rep = PF.Report()
missing, legacy = PF.s3_coherence(m, [("S1", 1, 48)], rep)
check("s3exact.silent_when_row_present",
      not rep.rejects and not rep.warns and missing == [],
      f"rejects={rep.rejects} warns={rep.warns} missing={missing}")

m = mod_with(SHOTS_V3=[("S1", 1, 48, "test")],
             CAMS_V3=[("CAM_S11", (0, 0, 5), (0, 0, 0), 50.0,
                       (0, 0, 0), False, 0.1)])
rep = PF.Report()
missing, _legacy = PF.s3_coherence(m, [("S1", 1, 48)], rep)
check("s3adjacent.still_warn_only",
      not rep.rejects and missing == ["S1"]
      and any("substring-adjacent" in w for w in rep.warns),
      f"rejects={rep.rejects} warns={rep.warns}")


# ---- 6b. F2C-3 Phase-B half: B3 rejects ONLY on row+object both missing.
class _FakeCam:
    def __init__(self, name):
        self.name = name


class _FakeMarker:
    def __init__(self, frame, camera):
        self.frame, self.camera = frame, camera


class _FakeScene:
    """Just enough scene for b3_markers: timeline_markers, objects.get,
    frame_start/frame_end (span gate)."""

    def __init__(self, markers, objects, f_start=1, f_end=48):
        self.timeline_markers = markers
        self.objects = {o.name: o for o in objects}
        self.frame_start, self.frame_end = f_start, f_end


_CAM_ROW_S1 = [("CAM_S1", (0, 0, 5), (0, 0, 0), 50.0, (0, 0, 0), False, 0.1)]
_SHOTS_2 = [("S1", 1, 24), ("S2", 25, 48)]

# (a) both missing -> REJECT naming BOTH checks (S2 reuses S1's camera;
#     no CAM_S2 row, no CAM_S2 object — the misname/rename class).
m = mod_with(SHOTS_V3=_SHOTS_2, CAMS_V3=_CAM_ROW_S1)
scene = _FakeScene(
    [_FakeMarker(1, _FakeCam("CAM_S1")), _FakeMarker(25, _FakeCam("CAM_S1"))],
    [_FakeCam("CAM_S1")])
rep = PF.Report()
PF.b3_markers(m, rep, scene, _SHOTS_2, missing_cam_rows=["S2"],
              legacy_cams=False)
check("b3pair.rejects_when_both_missing",
      len(rep.rejects) == 1 and "B3 cam-presence" in rep.rejects[0],
      f"rejects={rep.rejects}")
check("b3pair.names_both_checks",
      bool(rep.rejects) and "NO CAMS row named 'CAM_S2'" in rep.rejects[0]
      and "no camera object named 'CAM_S2'" in rep.rejects[0],
      f"rejects={rep.rejects}")

# (b) row missing but OBJECT present -> NO Phase-B reject (the F2C-3
#     false-reject case: exporter merges specs optionally, gate 11 skips
#     static/absent specs — a spec-less shot is green).
m = mod_with(SHOTS_V3=_SHOTS_2, CAMS_V3=_CAM_ROW_S1)
scene = _FakeScene(
    [_FakeMarker(1, _FakeCam("CAM_S1")), _FakeMarker(25, _FakeCam("CAM_S2"))],
    [_FakeCam("CAM_S1"), _FakeCam("CAM_S2")])
rep = PF.Report()
PF.b3_markers(m, rep, scene, _SHOTS_2, missing_cam_rows=["S2"],
              legacy_cams=False)
check("b3pair.object_present_no_reject", not rep.rejects,
      f"rejects={rep.rejects}")

# (c) legacy CAMS table -> paired outcome stays WARN (the exporter never
#     reads the legacy table, so it cannot fail on it — 5-a P2-11 parity).
m = mod_with(SHOTS_V3=[("S1", 1, 48)], CAMS_V3=[],
             CAMS=[("CAM_S9", (0, 0, 5), (0, 0, 0), 50.0,
                    (0, 0, 0), False, 0.1)])
scene = _FakeScene([_FakeMarker(1, _FakeCam("CAM_S9"))],
                   [_FakeCam("CAM_S9")], f_start=1, f_end=48)
rep = PF.Report()
PF.b3_markers(m, rep, scene, [("S1", 1, 48)], missing_cam_rows=["S1"],
              legacy_cams=True)
check("b3pair.legacy_warns_not_rejects",
      not rep.rejects and any("legacy CAMS table" in w for w in rep.warns),
      f"rejects={rep.rejects} warns={rep.warns}")

# ---- 7. F2C-8: CAMS_V3=[] + populated legacy CAMS must take the LEGACY
# path (cam_table's falsy fallthrough) — the old `is None` test defeated
# the demotion and rejected legacy rows.
m = mod_with(SHOTS_V3=[("S1", 1, 48, "test")], CAMS_V3=[],
             CAMS=[("CAM_OTHER", (0, 0, 5), (0, 0, 0), 50.0,
                    (0, 0, 0), False, 0.1)])
rep = PF.Report()
missing, legacy = PF.s3_coherence(m, [("S1", 1, 48)], rep)
check("legacy.empty_v3_uses_legacy_path", legacy is True,
      f"legacy={legacy} (False = the F2C-8 `is None` bug)")
check("legacy.no_reject_and_legacy_warn",
      not rep.rejects and any("LEGACY" in w for w in rep.warns),
      f"rejects={rep.rejects} warns={rep.warns}")
check("legacy.missing_list_still_returned", missing == ["S1"],
      f"missing={missing}")

# ---- 8. F2C-10: unhashable CAMS_V3[i][0] — the collector str()s it
# (accept), but the exporter's cam-map build TypeErrors; S2 must reject
# with the attribution. DELIBERATE S2-stricter exception to the decoder
# property (the collector's accept is a false-accept; the REAL consumer
# is the `{c[0]: c}` dict build).
m = mod_with(CAMS_V3=[(["bad"], (0, 0, 5), (0, 0, 0), 50.0,
                       (0, 0, 0), False, 0.1)])
kind, _ = decoder_outcome(m)
check("unhashable.collector_accepts", kind == "accept",
      f"decoder outcome={kind} (str() cast — the false-accept)")
rep = PF.Report()
PF.s2_schema(m, rep)
check("unhashable.s2_rejects", bool(rep.rejects),
      "S2 must reject what the cam-map build cannot consume")
check("unhashable.attributed_to_cam_map",
      bool(rep.rejects) and "HASHABLE" in rep.rejects[0]
      and "cam map" in rep.rejects[0],
      f"rejects={rep.rejects}")

# ---- 9. F2C-9: one-shot iterators. materialize_table_iterators() is the
# main()-time fix (normalize in place + WARN); s2/s3 keep per-phase
# list() safety nets so a drained generator can only ever WARN, never
# produce the old lying reject.
def _gen(rows):
    yield from rows


_ROWS = [("CAM_S1", (0, 0, 5), (0, 0, 0), 50.0, (0, 0, 0), False, 0.1)]
m = mod_with(CAMS_V3=_gen(_ROWS), SHOTS_V3=[("S1", 1, 48, "test")])
rep = PF.Report()
PF.materialize_table_iterators(m, rep)
check("generator.materialized_in_place", isinstance(m.CAMS_V3, list),
      f"type={type(m.CAMS_V3).__name__}")
check("generator.warned", any("one-shot iterator" in w for w in rep.warns),
      f"warns={rep.warns}")
rep = PF.Report()
missing, _legacy = PF.s3_coherence(m, [("S1", 1, 48)], rep)
check("generator.s3_finds_row_after_materialize",
      missing == [] and not rep.rejects and not rep.warns,
      f"missing={missing} rejects={rep.rejects} warns={rep.warns}")

# drained-generator safety net: S2 consumes a raw generator, then S3 must
# WARN (never the old "has no CAMS row … Fix: add a (…) row" reject for a
# row that exists).
m = mod_with(CAMS_V3=_gen(_ROWS), SHOTS_V3=[("S1", 1, 48, "test")])
PF.s2_schema(m, PF.Report())          # drains the generator (with its warn)
rep = PF.Report()
missing, _legacy = PF.s3_coherence(m, [("S1", 1, 48)], rep)
check("generator.drained_s3_never_rejects",
      not rep.rejects and missing == ["S1"],
      f"rejects={rep.rejects} missing={missing}")

# ---- 10. F2C-5: vacuous coverage — an empty module must report
# vacuous=True (and the summary must say so LOUDLY), a populated one must
# report real counts.
cov = PF.coverage_summary(mod_with())
check("coverage.empty.vacuous", cov.get("vacuous") is True, f"cov={cov}")
check("coverage.empty.zeros",
      cov["shots"] == 0 and cov["cams"] == 0 and cov["board"] == 0
      and cov["story_constants"] == 0, f"cov={cov}")

m = mod_with(**BASE)
cov = PF.coverage_summary(m)
check("coverage.full.counts",
      not cov["vacuous"] and cov["shots"] == 1 and cov["cams"] == 1
      and cov["board"] == 1 and cov["story_constants"] == 21, f"cov={cov}")

m = mod_with(SHOTS_V3=[("S1", 1, 48, "test")])
cov = PF.coverage_summary(m)
check("coverage.shots_only_not_vacuous",
      not cov["vacuous"] and cov["shots"] == 1 and cov["cams"] == 0,
      f"cov={cov}")

import contextlib
import io as _io
buf = _io.StringIO()
with contextlib.redirect_stdout(buf):
    rc = PF.print_summary(PF.Report(), "m.py", {}, {"S2": "ok"},
                          coverage={"shots": 0, "cams": 0, "board": 0,
                                    "story_constants": 0, "vacuous": True})
out = buf.getvalue()
check("coverage.summary_loud_vacuous",
      rc == 0 and "VACUOUS" in out and "shots=0" in out
      and "verify --module" in out, f"rc={rc} out={out!r}")

print(f"[t10p] {NCHECK} checks, {len(FAILS)} failed")
if FAILS:
    print("[t10p] FAILURES:", FAILS)
    sys.exit(1)
print("[t10p] ALL PASS")
