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

print(f"[t10p] {NCHECK} checks, {len(FAILS)} failed")
if FAILS:
    print("[t10p] FAILURES:", FAILS)
    sys.exit(1)
print("[t10p] ALL PASS")
