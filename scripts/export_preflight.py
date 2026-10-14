"""
export_preflight.py — pre-export contract gate for previz scene modules
(D19.1/D19.2, session-16 REV-2; session-17 REV-3 amendments).

Runs IN-BLENDER via blrun, BEFORE export_previz_package.py. It replays the
exporter's real consumption of a scene module against the module's declared
constants and its built scene, so every landmine surfaces at the cheap end
(seconds) instead of inside a full export+GLB+gates pipeline (minutes) —
or worse, as a green-but-broken review package.

session-17 REV-3 amendments (audit 2-c): S3 exact-name-missing demoted to
WARN with a paired Phase-B reject when the CAM_<sid> OBJECT is also missing
(F2C-3); vacuous modules now WARN with a coverage count in summary/JSON
(F2C-5); one-shot iterator constants are materialized once per phase
(F2C-9); unhashable CAMS names get an attributed reject (F2C-10); the
USD-sidecar RNA-kwarg drift was fixed in the EXPORTER
(blender_kit.filter_rna_kwargs, F2C-1).

Contract layers (who owns what):
  * export_previz_package._collect_story  — behavioral source of truth
    (STORY_SOURCES + the decoders are IMPORTED from it, never restated).
  * this tool (S1-S4, B1-B6)              — error QUALITY + pre-render
    coverage: every rejection names the constant, the row index, the
    expected shape, the got shape, and a fix hint. WARNs are compact
    one-liners, count-capped at 8 printed lines (look.py FLAG_CAP
    discipline) and never fail the run.
  * D19.2 parity guard (B5)               — drift-rot net: re-runs the
    exporter's own collector against the BUILT module state; a raise is
    differentially attributed (single-constant deletion) to one constant;
    BOARD key drops reject (P0-2).

Checks:
  S1  entry points: build_scene callable; animate dispatch replicated via
      inspect.Signature.bind (bool-is-int quirk preserved — a bare
      `def animate(ctx)` FAILS, the exporter's sentinel branch TypeErrors
      on it); emit_sfx_events optional-callable.
  S2  attributed schema pass over DECLARED constants only (absent
      constant = vacuous, law 20); arity table with >=n semantics mirroring
      the decoder casts (the decoder never width-checks, so neither do we —
      only castability); BEATS is a shape-only WARN (zero consumers here).
  S3  cross-table coherence: SHOTS contiguity; a shot with NO EXACT
      CAM_<sid> row is a WARN (REV-3/F2C-3: the exporter merges cam specs
      as an OPTIONAL exact-name merge — a spec-less shot exports green);
      containment matching remains FORBIDDEN — a substring-adjacent CAM_
      row is a WARN. The paired REJECT lives in Phase B (B3): if the
      camera OBJECT CAM_<sid> is ALSO missing from the built scene, both
      the spec and the object are gone and B3 rejects naming both checks.
      FPS cross-agreement among declared sources.
  S4  sfx stream shape: {name|kind} + integer frame (bool excluded);
      frame inside a SHOTS window (+/-4f) when SHOTS declared — applied
      to the DECLARED and the EMITTED streams alike (the emitted-file
      window check is deliberately STRICTER than exporter gate 15, which
      has no window rule — see b_sfx_emitter); unknown names vs
      build_sfx.PATCHES = compact WARN. SFX_EVENTS as a JSON path string
      validates the file ({fps, events} — fps required).
  B1  fresh empty blend -> mod.build_scene() -> ctx dict + non-empty scene
      (ctx.get("scene") fallback to bpy.context.scene, mirrored).
  B2  scene.render.fps == module FPS constant (when declared); fps_base
      must be 1.0 (the exporter stamps int(fps) and ignores fps_base).
  B3  markers mirror the exporter EXACTLY: marker at every f0,
      marker.camera set, marker.camera.name startswith "CAM_"; camera
      name == CAM_<sid> is a WARN only (marker NAMES are unconstrained).
      Plus the exporter's own span gate against the SCENE.
  B4  hidden sweep: no shot camera / Aim.* target / CAST root ("root"
      key) may be render-hidden (atmo_objects + KIT_ANNOT_* exempt).
  B5  parity guard (D19.2, runs HERE where real fps/frame_start exist):
      _collect_story(mod, float(fps), frame_start) on the BUILT state —
      raise => differential attribution; BOARD key-set parity
      (str()-cast) — any dropped entry rejects.
  B6  (opt-in --animate-dry) mod.animate(...) with the exporter's real
      dispatch and a small n_frames; a raise rejects. DEFAULT OFF: crowd
      modules need bakes and would false-fail — that is why it is opt-in.

Exit codes: 0 clean (WARNs print but never fail); 3 on any rejection
(look.py severity convention; blrun propagates). A preflight INTERNAL
error also exits 3 (fail-closed — a gate must never pass silently).

Usage:
    ./scripts/blrun.sh --background --python scripts/export_preflight.py -- \
        --module scripts/scene_my_film.py [--json out/preflight.json] \
        [--skip-build] [--animate-dry]

--skip-build runs Phase S ONLY; the parity guard (B5) does NOT run in that
mode (it needs the built scene's real fps/frame_start), so a clean
--skip-build is necessary, not sufficient.
"""

from __future__ import annotations

import argparse
import inspect
import json
import os
import sys
import tempfile
import traceback

PF = "[pf]"

# ---------------------------------------------------------------------------
# sys.path pin FIRST (REV-2 fix 6): Blender --background ignores PYTHONPATH
# and the exporter only self-inserts inside main():1010-1015. Everything
# below (blender_kit, export_previz_package, build_sfx, and the scene
# module's own `from blender_kit import ...`) depends on this.
# ---------------------------------------------------------------------------
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import bpy  # noqa: E402  (we are inside Blender)

from blender_kit import (  # noqa: E402
    _import_scene_file,
    atmo_objects,
    render_hidden_objects,
    script_argv,
)
import export_previz_package as _epp  # noqa: E402  (bpy import OK in Blender)

STORY_SOURCES = _epp.STORY_SOURCES  # the 21-entry map, imported — never restated

# sfx name vocabulary (escape-film synth patches). Unknown names are a
# compact WARN, never a rejection: film-lane markers legitimately fall
# outside the synth vocabulary.
try:
    from build_sfx import PATCHES as SFX_VOCAB
except Exception:  # numpy hiccup etc. — the vocab check degrades to a no-op
    SFX_VOCAB = None

WARN_CAP = 8          # look.py FLAG_CAP discipline
SFX_WINDOW_SLACK = 4  # frames of tolerance around each SHOTS window


# ---------------------------------------------------------------------------
# report plumbing
# ---------------------------------------------------------------------------

class Report:
    """Rejections (fail, printed in full immediately) + warnings (compact,
    capped at print time)."""

    def __init__(self):
        self.rejects: list[str] = []
        self.warns: list[str] = []

    def reject(self, msg: str) -> None:
        self.rejects.append(msg)
        print(f"{PF} REJECT {msg}", flush=True)

    def warn(self, msg: str) -> None:
        self.warns.append(msg)


def _tname(v) -> str:
    return type(v).__name__


def _shape(v) -> str:
    """Compact 'got' description for messages."""
    if isinstance(v, (list, tuple, str)):
        return f"{type(v).__name__}(len={len(v)})"
    if isinstance(v, dict):
        return f"dict(len={len(v)})"
    if v is None:
        return "None"
    return _tname(v)


def _can_int(x) -> bool:
    try:
        int(x)
        return True
    except Exception:
        return False


def _can_float(x) -> bool:
    try:
        float(x)
        return True
    except Exception:
        return False


def _is_frame_num(x) -> bool:
    """SHOTS f0/f1: int (bool excluded) or integral float. The exporter
    never casts these — it uses them as marker dict keys (hash equality
    with int marker frames) and in `f1 + 1` contiguity arithmetic, so a
    non-numeric value crashes gate 3 and a non-integral one never binds."""
    if isinstance(x, bool):
        return False
    if isinstance(x, int):
        return True
    if isinstance(x, float):
        return x.is_integer()
    return False


def _is_iterable(x) -> bool:
    try:
        iter(x)
        return True
    except Exception:
        return False


def _row(row, i):
    """row[i] with the failure captured (works for sequences; dicts/None
    return None instead of raising into the checker)."""
    try:
        return row[i]
    except Exception:
        return None


def _row_len(row):
    try:
        return len(row)
    except Exception:
        return None


def _vec_check(val, what: str, rep: Report, label: str,
               none_ok: bool = True) -> None:
    """A decoder vec field: `[_r3(x) for x in v]` — any iterable of
    float-castables. The decoder never width-checks (REV-2 law: an
    exact-width check would be stricter than the decoder and false-reject
    real modules), so len != 3 is a WARN, not a reject.
    none_ok=True preserves the BOARD seat_local contract (the decoder
    None-guards it); CAMS vec fields pass none_ok=False — the decoder
    does NOT guard those, a None raises TypeError (review 5-a P2-5)."""
    if val is None:
        if not none_ok:
            rep.reject(
                f"{label}: {what} must be an iterable of numbers (the "
                "decoder does NOT None-guard this field — a None raises "
                f"inside the collector); got None. Fix: use a 3-tuple like "
                "(0.0, 0.0, 1.0).")
        return
    if not _is_iterable(val):
        rep.reject(
            f"{label}: {what} must be an iterable of numbers (the decoder "
            f"iterates it); got {_shape(val)}. Fix: use a 3-tuple like "
            "(0.0, 0.0, 1.0).")
        return
    for item in val:
        if not _can_float(item):
            rep.reject(
                f"{label}: {what} must contain only float-castable numbers; "
                f"got {_shape(item)} inside {_shape(val)}. Fix: the decoder "
                "runs float() on every element.")
            return
    if isinstance(val, (list, tuple)) and len(val) != 3:
        rep.warn(f"{label}: {what} has {len(val)} elements (expected a "
                 "3-vector; the decoder accepts any width — verify intent)")


def _st(rep: Report, n_before: int) -> str:
    """Per-check status label (delta-based, so one check's rejection does
    not mislabel the ones after it)."""
    return "rejected" if len(rep.rejects) > n_before else "ok"


def _tb_tail() -> str:
    tb = sys.exc_info()
    return "".join(traceback.format_exception_only(tb[0], tb[1])
                   + traceback.format_tb(tb[2])[-3:])


# ---------------------------------------------------------------------------
# S1 — entry points (replicates the exporter's dispatch, 1040-1053)
# ---------------------------------------------------------------------------

def _animate_is_bare_branch(sig: inspect.Signature) -> bool:
    """The exporter's branch test, verbatim (bool-is-int quirk preserved:
    isinstance(True, int) is True, so `n_frames=True` takes the bare
    branch — that IS the exporter's real behavior)."""
    params = sig.parameters
    return "n_frames" in params and isinstance(params["n_frames"].default, int)


def s1_entry_points(mod, rep: Report) -> None:
    build = getattr(mod, "build_scene", None)
    if not callable(build):
        rep.reject(
            f"S1 build_scene: must be callable; got {_shape(build)}. Fix: "
            "define build_scene() — the exporter calls mod.build_scene() "
            "unguarded (exporter:1039).")

    emit = getattr(mod, "emit_sfx_events", None)
    if emit is not None and not callable(emit):
        rep.reject(
            f"S1 emit_sfx_events: optional, but if present it must be "
            f"callable; got {_shape(emit)}. Fix: define "
            "emit_sfx_events(ctx, out_dir) or remove it.")

    if not hasattr(mod, "animate"):
        return
    anim = mod.animate
    if not callable(anim):
        rep.reject(
            f"S1 animate: must be callable; got {_shape(anim)}. Fix: "
            "define def animate(ctx, ...) or remove it. (Note: animate = "
            "None still trips the exporter's hasattr dispatch — remove "
            "the attribute entirely.)")
        return
    try:
        sig = inspect.signature(anim)
    except (TypeError, ValueError) as e:
        rep.reject(
            f"S1 animate: inspect.signature failed ({_tname(e)}: {e}) — "
            "the exporter cannot dispatch it. Fix: use a plain "
            "def animate(ctx, *, start_frame=1, n_frames=None).")
        return
    bare = _animate_is_bare_branch(sig)
    try:
        if bare:
            sig.bind({})  # exporter: mod.animate(ctx)
        else:
            # exporter: mod.animate(ctx, start_frame=1, n_frames=None)
            sig.bind({}, start_frame=1, n_frames=None)
    except TypeError as e:
        rep.reject(
            "S1 animate: the exporter's dispatch cannot bind this "
            f"signature ({'bare' if bare else 'sentinel'} branch, "
            f"exporter:1035-1048): {e}. A bare `def animate(ctx)` "
            "TypeErrors the exporter's sentinel call "
            "mod.animate(ctx, start_frame=1, n_frames=None) — the P0-5 "
            "class. Fix: def animate(ctx, *, start_frame=1, n_frames=None) "
            "(or give n_frames an int default).")


# ---------------------------------------------------------------------------
# S2 — attributed schema pass (mirrors _collect_story:531-662 casts,
# >=n row semantics; absent constant = vacuous, law 20)
# ---------------------------------------------------------------------------

def _list_rows_check(val, label: str, rep: Report, min_len: int,
                     fields: str, cast_fields) -> None:
    """Shared list-of-rows shape: every row needs >=min_len indexable
    fields; the listed (index, castname, castfn) fields must survive the
    decoder's cast."""
    if not _is_iterable(val) or isinstance(val, (str, bytes, dict)):
        rep.reject(
            f"{label}: must be a list of rows; got {_shape(val)}. Fix: "
            "declare it as a list of tuples/lists.")
        return
    if not isinstance(val, (list, tuple)):
        rep.warn(f"{label}: is a {_tname(val)}, not a list/tuple — the "
                 "decoder will consume it once; declare a list/tuple so "
                 "the value survives repeated reads")
    for i, row in enumerate(val):
        rl = _row_len(row)
        if rl is None or rl < min_len:
            rep.reject(
                f"{label}[{i}]: row needs >= {min_len} fields ({fields}); "
                f"got {_shape(row)}. Fix: complete the row — the decoder "
                "indexes every field positionally.")
            continue
        for idx, castname, castfn in cast_fields:
            item = _row(row, idx)
            if not castfn(item):
                rep.reject(
                    f"{label}[{i}]: field {idx} must be {castname}; got "
                    f"{_shape(item)}. Fix: row shape is ({fields}) — the "
                    "decoder casts this field positionally.")


def s2_schema(mod, rep: Report) -> None:
    for attr, _key in STORY_SOURCES:
        val = getattr(mod, attr, None)
        if val is None:
            continue  # law 20: ABSENT constant = vacuous
        label = f"S2 {attr}"

        if attr == "DIALOG":
            # decoder: {"clip": str(d[0]), "onset_frame": int(d[1])} — FRAMES
            _list_rows_check(val, label, rep, 2,
                             "clip:str, onset_frame:int (FRAMES, not seconds)",
                             [(1, "int-castable", _can_int)])

        elif attr == "KNOCKDOWNS_V3":
            # decoder: id=str(k[0]), t_hit=float(k[1]), x_off=float(k[2]),
            #          style=str(k[3])
            _list_rows_check(val, label, rep, 4,
                             "id:str, t_hit:float-sec, x_off:float, style:str",
                             [(1, "float-castable", _can_float),
                              (2, "float-castable", _can_float)])

        elif attr == "CHASE_FALLS_V3":
            # decoder: for i, t in cf.items(): int(i), float(t)
            if not isinstance(val, dict):
                rep.reject(
                    f"{label}: must be a dict ({{chase_index: t_hit_sec}}); "
                    f"got {_shape(val)}. Fix: the decoder calls .items() on it.")
            else:
                for k, t in val.items():
                    if not _can_int(k):
                        rep.reject(
                            f"{label}[key {k!r}]: key must be int-castable "
                            f"(chase_index); got {_shape(k)}. Fix: key the "
                            "dict by int.")
                    if not _can_float(t):
                        rep.reject(
                            f"{label}[{k!r}]: value must be float-castable "
                            f"(t_hit, seconds); got {_shape(t)}. Fix: use a "
                            "number.")

        elif attr == "MUZZLE_BURSTS_V3":
            _list_rows_check(val, label, rep, 3, "f0:int, f1:int, every_n:int",
                             [(j, "int-castable", _can_int) for j in range(3)])

        elif attr == "JEEP_X_V3":
            _list_rows_check(val, label, rep, 2, "t:float-sec, x_off:float",
                             [(j, "float-castable", _can_float) for j in range(2)])

        elif attr == "_V3_SEG":
            _list_rows_check(val, label, rep, 4,
                             "t0:float, t1:float, v0:float, v1:float",
                             [(j, "float-castable", _can_float) for j in range(4)])

        elif attr == "BOARD":
            _s2_board(val, label, rep)

        elif attr == "RUN_PARAMS":
            # decoder: nested comprehension with float(vv) for non-str — a
            # None value raises float(None) and crashes the WHOLE collector.
            if not isinstance(val, dict):
                rep.reject(
                    f"{label}: must be a dict of dicts; got {_shape(val)}. "
                    "Fix: the decoder calls .items() on it and on every "
                    "inner value.")
                continue
            for k, v in val.items():
                if not isinstance(v, dict):
                    rep.reject(
                        f"{label}[{k!r}]: value must be a dict; got "
                        f"{_shape(v)}. Fix: {k!r}: {{param: value}}.")
                    continue
                for kk, vv in v.items():
                    if not isinstance(vv, str) and not _can_float(vv):
                        rep.reject(
                            f"{label}[{k!r}][{kk!r}]: value must be str or "
                            f"float-castable; got {_shape(vv)} (a None value "
                            "crashes the whole collector). Fix: use a number "
                            "or string.")

        elif attr == "MOTION_POLICY":
            # decoder uses .get() — needs a dict; intended_static is
            # iterated + str()'d; intended_subject_tree is str()'d (safe).
            if not isinstance(val, dict):
                rep.reject(
                    f"{label}: must be a dict (optional keys intended_static, "
                    f"intended_subject_tree); got {_shape(val)}. Fix: the "
                    "decoder calls .get() on it.")
            elif val.get("intended_static") is not None and \
                    not _is_iterable(val["intended_static"]):
                rep.reject(
                    f"{label}['intended_static']: must be an iterable of "
                    f"names; got {_shape(val['intended_static'])}. Fix: use "
                    "a list of strings.")

        elif attr == "FLATNESS_POLICY":
            if not isinstance(val, dict):
                rep.reject(
                    f"{label}: must be a dict ({{name: (f0, f1)}}); got "
                    f"{_shape(val)}. Fix: the decoder calls .items() on it.")
                continue
            for k, v in val.items():
                rl = _row_len(v)
                if rl is None or rl < 2:
                    rep.reject(
                        f"{label}[{k!r}]: value needs >= 2 fields (f0:int, "
                        f"f1:int); got {_shape(v)}. Fix: use an (f0, f1) "
                        "tuple of frames.")
                    continue
                if not _can_int(_row(v, 0)) or not _can_int(_row(v, 1)):
                    rep.reject(
                        f"{label}[{k!r}]: fields 0/1 must be int-castable "
                        f"frames; got {_shape(v)}. Fix: use (f0, f1) ints.")

        elif attr == "LUNGE_V3":
            if not isinstance(val, dict):
                rep.reject(
                    f"{label}: must be a dict; got {_shape(val)}. Fix: the "
                    "decoder calls .items() on it.")
                continue
            for k, v in val.items():
                if k == "y_offsets":
                    if not _is_iterable(v) or isinstance(v, (str, bytes, dict)):
                        rep.reject(
                            f"{label}['y_offsets']: must be a list of (t, y) "
                            f"rows; got {_shape(v)}. Fix: use "
                            "[(t_sec, y_off), ...].")
                        continue
                    for i, row in enumerate(v):
                        rl = _row_len(row)
                        if rl is None or rl < 2 \
                                or not _can_float(_row(row, 0)) \
                                or not _can_float(_row(row, 1)):
                            rep.reject(
                                f"{label}['y_offsets'][{i}]: row needs >= 2 "
                                "float-castable fields (t:float, y:float); "
                                f"got {_shape(row)}. Fix: use (t_sec, y_off) "
                                "number pairs.")
                elif not isinstance(v, (int, float)):
                    # the decoder silently DROPS these (625-627) — noted
                    # upstream, not fixed; WARN here so it is not silent.
                    rep.warn(
                        f"{label}[{k!r}]: value {_shape(v)} is not numeric — "
                        "the decoder silently DROPS it (_collect_story:625-"
                        "627); it will be absent from the JSON story")

        elif attr in ("RB_FALLS", "RB_KD"):
            # decoder: [str(x) if isinstance(x, str) else int(x) for x in v]
            # FLAT scalars — a tuple/None item crashes the collector.
            if not _is_iterable(val) or isinstance(val, (str, bytes, dict)):
                rep.reject(
                    f"{label}: must be a FLAT list of str|int scalars (NOT "
                    f"tuples); got {_shape(val)}. Fix: flatten it.")
                continue
            for i, item in enumerate(val):
                if isinstance(item, str):
                    continue
                if not _can_int(item):
                    rep.reject(
                        f"{label}[{i}]: item must be a str|int scalar (flat, "
                        f"not a tuple); got {_shape(item)}. Fix: use plain "
                        "ints/strings — the decoder runs int() on every "
                        "non-str item.")

        elif attr in ("T_DRIVE", "BARRICADE_T_V3", "BARRICADE_Y_V3",
                      "RUN_SPEED", "RUN_START_Y"):
            if not _can_float(val):
                rep.reject(
                    f"{label}: must be a float-castable scalar; got "
                    f"{_shape(val)}. Fix: the decoder runs float() on the "
                    "whole value.")

        elif attr == "TOTAL_FRAMES_V3":
            if not _can_int(val):
                rep.reject(
                    f"{label}: must be an int-castable scalar; got "
                    f"{_shape(val)}. Fix: the decoder runs int() on the "
                    "whole value.")

        elif attr == "HERO_MODE":
            # decoder: str(hm) — cannot fail for any object; vacuously OK.
            pass

        elif attr == "CAMS_V3":
            _s2_cams(val, label, rep)

        else:  # pragma: no cover — STORY_SOURCES grew past the S2 table
            rep.warn(f"{label}: no preflight shape rule for this constant "
                     "(STORY_SOURCES grew past the S2 table) — parity "
                     "guard B5 still covers it")


def _s2_board(board, label: str, rep: Report) -> None:
    """BOARD: dict name -> (MAIN, EXTRA). The decoder try/excepts PER ENTRY
    and NOTE-and-DROPS failures (580-596) — and the D19.4 tier-1 property
    demands decoder-drops be S2 rejects, so every per-entry deviation
    below rejects here (B5 parity re-checks the survivors at built state
    and catches post-import mutation)."""
    if not isinstance(board, dict):
        rep.reject(
            f"{label}: must be a dict (name -> (MAIN, EXTRA)); got "
            f"{_shape(board)}. Fix: the decoder calls .items() on it.")
        return
    for name, entry in board.items():
        el = _row_len(entry)
        if el is None or el < 2:
            # entry[1] raising is the real drop case (decoder:580)
            rep.reject(
                f"{label}[{name!r}]: entry must be a (MAIN, EXTRA) pair — "
                "missing the EXTRA slot at index 1 is the real drop case "
                f"(the decoder NOTEs and drops the entry); got "
                f"{_shape(entry)}. Fix: append an EXTRA element, e.g. "
                "(main, (0.25,)) — EXTRA may also be None/empty (offset 0.0).")
            continue
        main = _row(entry, 0)
        extra = _row(entry, 1)
        ml = _row_len(main)
        if ml is None or ml < 6:
            rep.reject(
                f"{label}[{name!r}]: MAIN needs >= 6 fields (run_end:int, "
                "apex:int, land:int, seat_local:vec3|None, yaw_end:float, "
                f"pose_name:str); got {_shape(main)}. Fix: complete MAIN to "
                "6 fields.")
            continue
        for idx in range(3):
            if not _can_int(_row(main, idx)):
                rep.reject(
                    f"{label}[{name!r}]: MAIN field {idx} must be "
                    f"int-castable; got {_shape(_row(main, idx))}. Fix: "
                    "(run_end, apex, land) are frame ints.")
        seat = _row(main, 3)
        if seat is not None:
            _vec_check(seat, "MAIN field 3 'seat_local'", rep,
                       f"{label}[{name!r}]")
        if not _can_float(_row(main, 4)):
            rep.reject(
                f"{label}[{name!r}]: MAIN field 4 'yaw_end' must be "
                f"float-castable; got {_shape(_row(main, 4))}.")
        # main[5]: str() — cannot fail
        if extra:  # falsy EXTRA -> offset 0.0 (decoder:587)
            if _row_len(extra) is None or _row_len(extra) < 1 \
                    or not _can_float(_row(extra, 0)):
                rep.reject(
                    f"{label}[{name!r}]: EXTRA must be falsy or a sequence "
                    f"whose [0] is float-castable; got {_shape(extra)}. Fix: "
                    "use (offset_float,) or None.")


def _s2_cams(cams, label: str, rep: Report) -> None:
    """CAMS_V3 rows >= 7: (name:str, loc0:vec3, loc1:vec3, lens:num,
    aim:vec3, parent_jeep:bool, shake_amp:num). Decoder casts: float(c[3]),
    float(c[6]), vec-iterates c[1]/c[2]/c[4]; bool(c[5]) and str(c[0])
    cannot fail. DELIBERATELY stricter than the collector on field 0
    (F2C-10): the collector str()s it, but the exporter's cam-map build
    (`cams_spec = {c[0]: c ...}`) needs it HASHABLE — an unhashable name
    TypeErrors the whole build, so it rejects here."""
    if not _is_iterable(cams) or isinstance(cams, (str, bytes, dict)):
        rep.reject(
            f"{label}: must be a list of 7-field rows; got {_shape(cams)}. "
            "Fix: declare it as a list of tuples.")
        return
    if not isinstance(cams, (list, tuple)):
        # F2C-9: a one-shot iterator is consumed by THIS loop; materialize
        # (and say so) — main() normalizes the table constants before the
        # phases, so this is the direct-call safety net.
        rep.warn(f"{label}: is a {_tname(cams)}, not a list/tuple — the "
                 "decoder will consume it once; declare a list/tuple so "
                 "the value survives repeated reads")
        cams = list(cams)
    for i, row in enumerate(cams):
        rl = _row_len(row)
        if rl is None or rl < 7:
            rep.reject(
                f"{label}[{i}]: row needs >= 7 fields (name:str, loc0:vec3, "
                "loc1:vec3, lens:num, aim:vec3, parent_jeep:bool, "
                f"shake_amp:num); got {_shape(row)}. Fix: complete the row — "
                "the decoder indexes c[0]..c[6] (_collect_story:645-660, "
                "exporter:1151-1159).")
            continue
        # F2C-10: field 0 keys the exporter's cam-map dict — unhashable
        # names crash it (garbage-in guard; the collector's str() would
        # silently accept and the crash would surface unattributed).
        name0 = _row(row, 0)
        try:
            hash(name0)
        except TypeError:
            rep.reject(
                f"{label}[{i}]: field 0 (cam name) must be HASHABLE — the "
                "exporter builds its cam map keyed by it "
                "(`cams_spec = {c[0]: c ...}`, exporter:1129) and an "
                f"unhashable name TypeErrors the whole build; got "
                f"{_shape(name0)}. Fix: use a string name like 'CAM_S1'.")
            continue
        for idx, what in ((1, "loc0"), (2, "loc1"), (4, "aim")):
            _vec_check(_row(row, idx), f"field {idx} '{what}'", rep,
                       f"{label}[{i}]", none_ok=False)
        if not _can_float(_row(row, 3)):
            rep.reject(
                f"{label}[{i}]: field 3 'lens' must be float-castable; got "
                f"{_shape(_row(row, 3))}. Fix: lens in mm.")
        if not _can_float(_row(row, 6)):
            rep.reject(
                f"{label}[{i}]: field 6 'shake_amp' must be float-castable; "
                f"got {_shape(_row(row, 6))}.")


def s2_beats(mod, rep: Report) -> None:
    """BEATS (if declared): shape-only WARN — each row >= 3, field 1
    numeric. NO timing rules (the t==(f0-1)/FPS opener rule false-rejects
    tdawn) and NO rejection: BEATS has ZERO consumers in this exporter
    (it is the canonical agent-kit copy's contract, validated for THAT
    lane)."""
    beats = getattr(mod, "BEATS", None)
    if beats is None:
        return
    label = "S2 BEATS"
    if not _is_iterable(beats) or isinstance(beats, (str, bytes, dict)):
        rep.warn(f"{label}: declared but not a list of rows; got "
                 f"{_shape(beats)} — shape-only WARN (zero consumers in "
                 "this exporter; canonical-copy lane contract)")
        return
    for i, row in enumerate(beats):
        rl = _row_len(row)
        if rl is None or rl < 3 or not _can_float(_row(row, 1)):
            rep.warn(
                f"{label}[{i}]: row needs >= 3 fields with field 1 numeric "
                f"(canonical shape: (id, t_seconds, label)); got "
                f"{_shape(row)} — shape-only WARN "
                "(zero consumers in this exporter)")


# ---------------------------------------------------------------------------
# SHOTS/CAMS tables (exporter's exact fallbacks)
# ---------------------------------------------------------------------------

def shots_table(mod):
    """getattr(SHOTS_V3) or getattr(SHOTS) — replicated verbatim from
    exporter:1115 (the `or` means an empty SHOTS_V3 falls back to SHOTS)."""
    return getattr(mod, "SHOTS_V3", None) or getattr(mod, "SHOTS", [])


def cam_table(mod):
    """CAMS_V3 rows, CAMS as legacy fallback (design table 'CAMS_V3/CAMS').
    NOTE: the exporter itself only ever reads CAMS_V3 (_collect_story:645,
    exporter:1134); the CAMS fallback is a preflight-only courtesy for
    legacy modules."""
    return getattr(mod, "CAMS_V3", None) or getattr(mod, "CAMS", None)


def s2_shots(mod, rep: Report):
    """SHOTS rows >= 4 (sid:str, f0:int, f1:int, intent:str). Returns the
    validated (sid, f0, f1) triples for S3/B3."""
    table = shots_table(mod)
    out = []
    if not table:
        return out
    if not _is_iterable(table) or isinstance(table, (str, bytes, dict)):
        attr = "SHOTS_V3" if getattr(mod, "SHOTS_V3", None) is not None \
            else "SHOTS"
        rep.reject(
            f"S2 {attr}: must be a list of rows; got {_shape(table)}. Fix: "
            "declare it as a list of (sid, f0, f1, intent) tuples.")
        return out
    attr = "SHOTS_V3" if getattr(mod, "SHOTS_V3", None) else "SHOTS"
    for i, row in enumerate(table):
        rl = _row_len(row)
        if rl is None or rl < 4:
            rep.reject(
                f"S2 {attr}[{i}]: row needs >= 4 fields (sid:str, f0:int, "
                f"f1:int, intent:str); got {_shape(row)}. Fix: complete the "
                "row — the exporter unpacks sid, f0, f1, intent "
                "positionally (exporter:1117).")
            continue
        f0, f1 = _row(row, 1), _row(row, 2)
        for idx, nm in ((1, "f0"), (2, "f1")):
            if not _is_frame_num(_row(row, idx)):
                rep.reject(
                    f"S2 {attr}[{i}]: field {idx} '{nm}' must be an int "
                    f"frame; got {_shape(_row(row, idx))}. Fix: the exporter "
                    "uses it as a timeline-marker key and in f1+1 contiguity "
                    "arithmetic (exporter:1117, 1340-1341).")
        if _is_frame_num(f0) and _is_frame_num(f1):
            out.append((str(_row(row, 0)), int(f0), int(f1)))
    return out


# ---------------------------------------------------------------------------
# S3 — cross-table coherence
# ---------------------------------------------------------------------------

def s3_coherence(mod, shots, rep: Report):
    """Cross-table coherence. Returns (missing_exact, legacy_cams) where
    missing_exact lists the shot sids with NO exact CAM_<sid> row (S3
    WARNs them; Phase B's B3 turns them into a paired REJECT when the
    camera OBJECT is missing too — F2C-3) and legacy_cams says the table
    came from the preflight-only CAMS fallback (the exporter never reads
    it, so B3 only WARNs there)."""
    # contiguity (mirrors exporter gate 3 arithmetic, 1340-1344)
    for i in range(1, len(shots)):
        if shots[i][1] != shots[i - 1][2] + 1:
            rep.reject(
                f"S3 SHOTS: not contiguous at {shots[i][0]!r} "
                f"(f{shots[i][1]} after f{shots[i - 1][2]}) — exporter "
                "gate 3 rejects this at export time. Fix: make each f0 the "
                "previous f1 + 1.")

    # sid -> CAMS row named EXACTLY CAM_<sid>. Containment ("S1" in
    # "CAM_S11") is FORBIDDEN as a check; a mismatching-but-CAM_-prefixed
    # row is a WARN.
    cams = cam_table(mod)
    if cams is None:
        return [], True
    if not _is_iterable(cams) or isinstance(cams, (str, bytes, dict)):
        return [], True  # already rejected in S2
    # F2C-9: never iterate a one-shot twice — S2 may have drained it; this
    # list() is per-phase (main() normalizes the module constants first,
    # so this is the direct-call safety net).
    cams = list(cams)
    # review 5-a P2-11: the exporter reads ONLY CAMS_V3 — a legacy-CAMS-only
    # module exports green (vacuous), so S3 must not be stricter than that.
    # Demote every cam-name rejection to a WARN when the table is the
    # preflight-only legacy fallback. F2C-8: falsy CAMS_V3 ([] / "" / ())
    # falls through to CAMS in cam_table above — the legacy path — so the
    # test here must be falsiness, not `is None`.
    legacy = not getattr(mod, "CAMS_V3", None)
    names = []
    for r in cams:
        if (_row_len(r) or 0) >= 1 and _row(r, 0) is not None:
            names.append(str(_row(r, 0)))
    exact_names = set(names)
    missing_exact = []
    for sid, _f0, _f1 in shots:
        want = f"CAM_{sid}"
        if want in exact_names:
            continue
        missing_exact.append(sid)
        adjacent = [n for n in names if n.startswith(want)]
        if adjacent:
            rep.warn(
                f"S3 CAMS: shot {sid!r} has no exact '{want}' row but "
                f"{adjacent[:2]} exist — substring-adjacent names never "
                "match (the exporter merges cam specs by exact name, "
                "exporter:1151; the shot gets no motion spec). WARN only.")
        elif legacy:
            rep.warn(
                f"S3 CAMS: shot {sid!r} has no row named '{want}' — "
                "but the table here is the LEGACY 'CAMS' fallback, which "
                "the exporter never reads (CAMS_V3 only, _collect_story:645); "
                "the export is vacuous either way. WARN only.")
        else:
            # REV-3/F2C-3: the exporter merges cam specs as an OPTIONAL
            # exact-name merge — a shot without a CAMS row exports green
            # (no motion spec; gate 11 only inspects rows that EXIST), so
            # this used to be a false-REJECT. WARN here; Phase B (B3)
            # rejects when the camera OBJECT CAM_<sid> is also missing.
            rep.warn(
                f"S3 CAMS: shot {sid!r} has no CAMS row named '{want}' — "
                "the exporter merges cam specs as an OPTIONAL exact-name "
                "merge (exporter:1151-1159), so the shot exports green with "
                "no motion spec. WARN only — BUT if the camera OBJECT "
                f"'{want}' is also missing from the built scene, Phase B "
                "rejects (B3 names both checks). Fix: add a "
                f"('{want}', loc0, loc1, lens, aim, parent_jeep, shake_amp) "
                "row, or verify the shot reuses another CAM_* camera.")

    # FPS cross-agreement among DECLARED sources (render.fps itself is
    # checked in Phase B against the built scene).
    fps_const = getattr(mod, "FPS", None)
    rp = getattr(mod, "RUN_PARAMS", None)
    rp_fps = rp.get("fps") if isinstance(rp, dict) else None
    if fps_const is not None and rp_fps is not None:
        if not _can_int(fps_const):
            rep.warn(f"S3 FPS: constant is not int-castable "
                     f"({_shape(fps_const)})")
        elif not _can_float(rp_fps):
            rep.warn(f"S3 FPS: RUN_PARAMS['fps'] is not numeric "
                     f"({_shape(rp_fps)})")
        elif int(fps_const) != int(float(rp_fps)):
            rep.warn(
                f"S3 FPS: module FPS={fps_const} disagrees with "
                f"RUN_PARAMS['fps']={rp_fps} — the exporter stamps the "
                "timeline from scene.render.fps; one of these is stale.")
    return missing_exact, legacy


# ---------------------------------------------------------------------------
# S4 — sfx stream shape
# ---------------------------------------------------------------------------

def _sfx_check_events(events, source: str, rep: Report, shots,
                      scene_fps=None) -> None:
    """Shared per-event validator (S4 shape; per-event part mirrors
    exporter gate 15). Rejections: event shape + frame window. WARN:
    unknown names vs build_sfx.PATCHES."""
    if not isinstance(events, list):
        rep.reject(
            f"S4 sfx {source}: 'events' must be a list; got "
            f"{_shape(events)}. Fix: write {{'fps': N, 'events': [...]}}.")
        return
    windows = [(f0, f1) for _sid, f0, f1 in shots] if shots else None
    unknown = []
    for i, ev in enumerate(events):
        if not isinstance(ev, dict):
            rep.reject(
                f"S4 sfx {source}: event[{i}] must be an object; got "
                f"{_shape(ev)}. Fix: the review app drops non-object events "
                "(the F-TF4 class).")
            continue
        if not ("name" in ev or "kind" in ev):
            rep.reject(
                f"S4 sfx {source}: event[{i}] lacks both 'name' and 'kind' "
                f"(keys: {sorted(ev)[:4]}) — the review app drops events "
                "without one 3/3 (the F-TF4 class). Fix: key it 'name' or "
                "'kind'.")
            continue
        fr = ev.get("frame")
        if not isinstance(fr, int) or isinstance(fr, bool):
            rep.reject(
                f"S4 sfx {source}: event[{i}] 'frame' must be an integer "
                f"(bool excluded); got {_shape(fr)}={fr!r}. Fix: stamp an "
                "int frame.")
            continue
        if windows and not any(f0 - SFX_WINDOW_SLACK <= fr <= f1 + SFX_WINDOW_SLACK
                               for f0, f1 in windows):
            rep.reject(
                f"S4 sfx {source}: event[{i}] frame {fr} falls outside every "
                f"SHOTS window (+/-{SFX_WINDOW_SLACK}f; table spans "
                f"{shots[0][0]}@f{shots[0][1]}..{shots[-1][0]}@f{shots[-1][2]})"
                " — the event cannot attach to a shot in the review "
                "timeline. Fix: move it into a shot window or extend SHOTS.")
        nm = ev.get("name", ev.get("kind"))
        if SFX_VOCAB is not None and isinstance(nm, str) \
                and nm not in SFX_VOCAB:
            unknown.append(nm)
    if unknown:
        uniq = sorted(set(unknown))
        rep.warn(
            f"S4 sfx {source}: {len(unknown)}/{len(events)} event names "
            f"unknown to build_sfx.PATCHES (first 3: "
            f"{', '.join(uniq[:3])}) — film-lane markers are legitimate; "
            "the synth lane will skip them (WARN only)")


def _sfx_check_file(path: str, source: str, rep: Report, shots,
                    require_fps: bool, scene_fps=None) -> None:
    """Validate an sfx_events.json file. require_fps=True enforces the
    {fps, events} schema (SFX_EVENTS-as-path case: fps is contract, not
    accident). The gate-15-mirrored emitted-file case passes fps=None
    through vacuously, exactly like exporter:1245-1252. NOTE (F2C-12):
    the per-event SHAPE + fps agreement mirror gate 15, but the ±4f
    SHOTS-window rule (in _sfx_check_events) is STRICTER than gate 15 by
    design — the exporter has no window rule; the preflight applies S4's
    declared-stream window to the emitted stream too, because the review
    app must attach events to shots either way."""
    try:
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
    except Exception as e:
        rep.reject(
            f"S4 sfx {source}: unreadable/unparseable JSON ({_tname(e)}). "
            "Fix: the file must be {'fps': N, 'events': "
            "[{name|kind, frame}, ...]}.")
        return
    if not isinstance(doc, dict):
        rep.reject(
            f"S4 sfx {source}: top level must be an object with 'fps' and "
            f"'events'; got {_shape(doc)}.")
        return
    fps = doc.get("fps")
    if fps is None and require_fps:
        rep.reject(
            f"S4 sfx {source}: missing 'fps' — both real producers write "
            "it; it is contract, not accident (D19 S4). Fix: add "
            "{'fps': <int>, 'events': [...]}.")
    elif fps is not None:
        if not _can_int(fps):
            rep.reject(
                f"S4 sfx {source}: 'fps' must be int-castable; got "
                f"{_shape(fps)}.")
        elif scene_fps is not None and int(fps) != int(scene_fps):
            rep.reject(
                f"S4 sfx {source}: fps={fps} disagrees with "
                f"scene.render.fps={int(scene_fps)} — the app stamps the "
                "timeline from the scene; events would land at wrong times "
                "(gate-15 parity).")
    if require_fps and "events" not in doc:
        rep.reject(
            f"S4 sfx {source}: missing 'events' — the {'{fps, events}'} "
            "schema requires both keys. Fix: add an 'events' list "
            "(empty is fine).")
        return
    _sfx_check_events(doc.get("events", []), source, rep, shots, scene_fps)


def s4_sfx(mod, shots, rep: Report, module_dir: str) -> None:
    """Phase-S half: the declared SFX_EVENTS constant (list or JSON path).
    The emit_sfx_events stream is validated in Phase B (it needs ctx)."""
    sfx = getattr(mod, "SFX_EVENTS", None)
    if sfx is None:
        return
    if isinstance(sfx, str):
        path = sfx if os.path.isabs(sfx) else os.path.join(module_dir, sfx)
        if not os.path.isfile(path):
            rep.reject(
                f"S4 SFX_EVENTS: JSON path does not exist: {path} (resolved "
                "against the module's directory). Fix: ship the file or "
                "declare SFX_EVENTS as a list of event dicts.")
            return
        _sfx_check_file(path, "SFX_EVENTS file", rep, shots, require_fps=True)
    elif isinstance(sfx, list):
        _sfx_check_events(sfx, "SFX_EVENTS", rep, shots)
    else:
        rep.reject(
            f"S4 SFX_EVENTS: must be a list of event dicts or a JSON path "
            f"string; got {_shape(sfx)}. Fix: "
            "[{'name': ..., 'frame': int}, ...] or 'events.json'.")


# ---------------------------------------------------------------------------
# Phase B
# ---------------------------------------------------------------------------

def b2_fps(mod, rep: Report, scene) -> None:
    """B2 — fps agreement. The exporter stamps int(fps) and IGNORES
    fps_base (verified zero fps_base references), so fps_base MUST be 1.0
    for the stamped rate to be the real rate."""
    fps = scene.render.fps
    fps_const = getattr(mod, "FPS", None)
    if fps_const is not None and not _can_int(fps_const):
        rep.warn(f"B2 fps: module FPS constant is not int-castable "
                 f"({_shape(fps_const)}) — cannot compare against "
                 "scene.render.fps")
    elif fps_const is not None and int(fps_const) != int(fps):
        rep.reject(
            f"B2 fps: scene.render.fps={int(fps)} != module FPS constant "
            f"{int(fps_const)} — the exporter stamps the review timeline "
            "from the SCENE (exporter:1176). Fix: set render.fps in "
            "build_scene (or fix the FPS constant).")
    if float(scene.render.fps_base) != 1.0:
        rep.reject(
            f"B2 fps: scene.render.fps_base={scene.render.fps_base} != 1.0 "
            "— the exporter casts int(fps) and IGNORES fps_base "
            "(exporter:1176), so the stamped rate would differ from the "
            "real rate. Fix: leave fps_base at 1.0.")


def b3_markers(mod, rep: Report, scene, shots,
               missing_cam_rows=(), legacy_cams=False) -> dict:
    """B3 — markers, mirroring exporter:1118-1124 EXACTLY (marker NAMES
    are unconstrained; only the bound CAMERA name carries the CAM_
    contract). Plus the exporter's own span gate (gate 3) against the
    SCENE. Plus the REV-3/F2C-3 paired check: a shot whose CAMS table has
    no exact CAM_<sid> row (S3 WARNed) AND whose built scene has no
    camera OBJECT named CAM_<sid> rejects — spec and object both missing
    is the misname/rename class. (Legacy-CAMS modules keep WARN parity:
    the exporter never reads the legacy table, so it cannot fail on it.)
    Returns {frame: marker} for B4."""
    all_marks = {m.frame: m for m in scene.timeline_markers}
    for sid, f0, _f1 in shots:
        m = all_marks.get(f0)
        if m is None:
            rep.reject(
                f"B3 markers: no timeline marker at f{f0} for shot {sid!r} "
                "— the exporter cannot bind a camera and exits "
                "(exporter:1119-1121). Fix: add a marker at f" + str(f0) +
                " bound to the shot camera "
                "(scene.timeline_markers.new(name, frame=" + str(f0) +
                ").camera = cam).")
        elif m.camera is None:
            rep.reject(
                f"B3 markers: the marker at f{f0} (shot {sid!r}) binds NO "
                "camera — _marker_bindings skips unbound markers "
                "(exporter:109-112), so the export fails identically at "
                "the no-marker raise (exporter:1119-1121). Fix: set "
                "marker.camera.")
        elif not m.camera.name.startswith("CAM_"):
            rep.reject(
                f"B3 markers: the marker at f{f0} (shot {sid!r}) binds "
                f"{m.camera.name!r} — expected a CAM_* object "
                "(exporter:1122-1124). Fix: name the camera CAM_<sid>.")
        elif m.camera.name != f"CAM_{sid}":
            rep.warn(
                f"B3 markers: shot {sid!r} binds camera {m.camera.name!r} "
                f"!= 'CAM_{sid}' — exact-match is the real convention in "
                "both films; WARN only (the exporter only requires the "
                "CAM_ prefix).")
    # REV-3/F2C-3 paired check — the Phase-B half of S3's demotion.
    for sid in missing_cam_rows:
        if scene.objects.get(f"CAM_{sid}") is None:
            msg = (
                f"B3 cam-presence: shot {sid!r} has NO CAMS row named "
                f"'CAM_{sid}' (S3 WARN) AND no camera object named "
                f"'CAM_{sid}' in the built scene — BOTH the exporter's "
                "optional cam-spec merge (exporter:1151-1159) and the "
                "CAM_<sid> object convention fail together (the "
                "misname/rename class; the shot's framing would come from "
                "whatever the f0 marker binds). Fix: name the shot camera "
                f"'CAM_{sid}' and add the matching CAMS_V3 row, or point "
                "the f0 marker at an existing CAM_* camera.")
            if legacy_cams:
                rep.warn(msg + " (legacy CAMS table: exporter reads "
                         "CAMS_V3 only — WARN parity)")
            else:
                rep.reject(msg)
    if shots:
        if shots[0][1] != scene.frame_start or shots[-1][2] != scene.frame_end:
            rep.reject(
                f"B3 span: the shot table spans f{shots[0][1]}–"
                f"f{shots[-1][2]} but the scene spans f{scene.frame_start}–"
                f"{scene.frame_end} — exporter gate 3 rejects this "
                "(exporter:1332-1334). Fix: set frame_start/frame_end to "
                "the shot span (or vice versa). Span comes from the SCENE, "
                "never a module constant.")
    return all_marks


def b4_hidden_sweep(mod, rep: Report, scene, shots, all_marks) -> None:
    """B4 — no shot camera / Aim.* target / CAST root may be render-hidden.
    EXEMPT: atmo_objects(scene) names (volume shells are SUPPOSED to be
    render-hidden — the exporter excludes them by design, 1100-1108) and
    KIT_ANNOT_* (never saved). render_hidden_objects() already does
    view_layer.update() (F-TD5 wave A)."""
    hidden = render_hidden_objects(scene)
    hidden_names = {ob.name for ob in hidden}
    exempt = {ob.name for ob in atmo_objects(scene)}
    exempt |= {n for n in hidden_names if n.startswith("KIT_ANNOT_")}

    protected: dict[str, str] = {}  # name -> why
    for sid, f0, _f1 in shots:
        m = all_marks.get(f0)
        if m is not None and m.camera is not None:
            protected.setdefault(m.camera.name, f"shot camera of {sid!r}")
        ob = scene.objects.get(f"CAM_{sid}")
        if ob is not None:
            protected.setdefault(ob.name, f"shot camera CAM_{sid}")
    for ob in scene.objects:
        if ob.name.startswith("Aim."):
            protected[ob.name] = "Aim.* target (gate-2 class)"
    cast = getattr(mod, "CAST", None)
    if cast is not None:
        if isinstance(cast, dict):
            for actor, spec in cast.items():
                if isinstance(spec, dict) and spec.get("root"):
                    protected.setdefault(str(spec["root"]),
                                         f"CAST root of {actor!r}")
        else:
            rep.warn(
                "B4 CAST: expected a dict of dicts with a 'root' key; got "
                f"{_shape(cast)} — preflight could not check its roots "
                "(CAST is a scene-side convention, not exporter-consumed)")
    for name, why in sorted(protected.items()):
        if name in hidden_names and name not in exempt:
            rep.reject(
                f"B4 hidden-sweep: {name!r} ({why}) is render-hidden "
                "(visible_camera=False or hide_render=True) — the GLB "
                "export silently EXCLUDES it (session-23 law), so the shot "
                "loses its camera/aim/actor (blank-shot and gate-2 class). "
                "Fix: clear the flags, or tag genuine atmosphere with the "
                "kit_atmo custom prop (atmo objects are exempt).")


def b5_parity(mod, rep: Report, scene) -> None:
    """D19.2 — the exporter's own collector against the BUILT state.

    A raise here means S2 accepted something the decoder rejects (schema
    gap) or build_scene mutated a constant (scene-data bug). Differential
    attribution: re-run with ONE declared constant set to None at a time
    (the collector skips constants whose getattr is None) — <=21
    pure-getattr iterations, no bpy.
    """
    fps = float(scene.render.fps)
    fstart = int(scene.frame_start)
    try:
        story = _epp._collect_story(mod, fps, fstart)
    except Exception:
        rep.reject(
            "B5 parity: _collect_story RAISED on the built module state "
            "(S2 passed at import time) — traceback tail on the next line. "
            "Differential attribution follows.")
        rep.reject("B5 traceback tail:\n" + _tb_tail())

        saved = [(name, getattr(mod, name, None))
                 for name, _key in STORY_SOURCES
                 if getattr(mod, name, None) is not None]
        offender = None
        try:
            for name, val in saved:
                setattr(mod, name, None)  # collector skips None constants
                try:
                    _epp._collect_story(mod, fps, fstart)
                except Exception:
                    setattr(mod, name, val)  # not the offender — restore
                else:
                    setattr(mod, name, val)
                    offender = name
                    break
        finally:
            for name, val in saved:
                setattr(mod, name, val)
        if offender is not None:
            rep.reject(
                f"B5 parity: differential attribution names {offender} — "
                f"EITHER (a) a scene-data bug in {offender} (its value "
                "changed after import — build_scene must not mutate module "
                "constants), OR (b) a preflight-schema gap (S2 accepted "
                "what the decoder rejects) — report it against "
                "export_preflight S2.")
        else:
            rep.reject(
                "B5 parity: single-constant deletion could NOT isolate the "
                "raise (multi-constant interaction or non-story cause) — "
                "EITHER (a) a scene-data bug in the built module state, OR "
                "(b) a preflight-schema gap — report it against "
                "export_preflight S2.")
        return

    # BOARD key-set parity (P0-2): keys are str()-cast at decoder:586.
    board = getattr(mod, "BOARD", None)
    if board is not None:
        declared_keys = set(str(k) for k in board)
        landed_keys = set(story.get("board", {}).keys())
        dropped = sorted(declared_keys - landed_keys)
        if dropped:
            rep.reject(
                "B5 parity: BOARD entries would be silently DROPPED from "
                f"the review JSON (P0-2): {dropped} — declared "
                f"{len(declared_keys)} key(s), the decoder lands "
                f"{len(landed_keys)} (per-entry parse failures; the "
                "exporter's gate-4 strengthening rejects a 100% failure, "
                "partial boards keep only a NOTE). Fix: repair the listed "
                "BOARD entries to the (MAIN(6), EXTRA) shape — every entry "
                "must decode.")


def b_sfx_emitter(mod, rep: Report, ctx, scene, shots) -> None:
    """Phase-B half of S4: call the module's own emitter into a temp dir
    and validate what it wrote. Per-event shape + fps agreement mirror
    gate 15 WITHOUT running the export; the ±4f SHOTS-window rule is
    STRICTER than gate 15 BY DESIGN (D19.1 S4's declared-stream window
    also guards the emitted stream — the exporter has no window rule, the
    review app needs events attachable to shots either way; documented
    REV-3/F2C-12, not relaxed). The exporter calls emit_sfx_events
    unguarded, so a raise here would crash the export. NOTE: this runs
    AFTER b5_parity (main() ordering) — the exporter reads scene
    fps/frame_start BEFORE its own emitter call, and an emitter that
    mutates the scene must not shift what the parity guard snapshots
    (review 5-a P2-9)."""
    emit = getattr(mod, "emit_sfx_events", None)
    if not callable(emit):
        return
    tmp = tempfile.mkdtemp(prefix="pf_sfx_")
    try:
        try:
            emit(ctx, tmp)
        except Exception:
            rep.reject(
                "B sfx: emit_sfx_events(ctx, out_dir) RAISED — the exporter "
                "calls it unguarded (exporter:1209), so the export would "
                "crash. Traceback tail on the next line.")
            rep.reject("B sfx traceback tail:\n" + _tb_tail())
            return
        path = os.path.join(tmp, "sfx_events.json")
        if os.path.isfile(path):
            _sfx_check_file(path, "sfx_events.json (emitted)", rep, shots,
                            require_fps=False, scene_fps=scene.render.fps)
        else:
            rep.warn(
                "B sfx: module defines emit_sfx_events but wrote no "
                "sfx_events.json (a scene may defer sfx — gate-15 WARN "
                "parity; verify this is intended)")
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)  # review 5-a P2-9: no leak


def b6_animate_dry(mod, rep: Report, ctx) -> None:
    """Opt-in: run animate with the exporter's real dispatch and a small
    n_frames. DEFAULT OFF — crowd modules need bakes and would false-fail;
    S1's bind check already proves the signature dispatches."""
    sig = inspect.signature(mod.animate)
    if _animate_is_bare_branch(sig):
        mod.animate(ctx)  # exporter's bare branch (module decides timeline)
    else:
        mod.animate(ctx, start_frame=1, n_frames=8)  # sentinel + small run


def materialize_table_iterators(mod, rep: Report) -> None:
    """F2C-9: one-shot iterators in the TABLE constants drain on first
    read — S2 consumes them, then S3/B3/B5 re-read an EXHAUSTED iterator
    and 'reject' rows that exist, with a lying fix-hint. Materialize each
    to a list ONCE, here, and WARN. The exporter consumes each constant
    exactly once, so this matches exporter semantics (it never mutates
    the module the exporter sees — the exporter imports its own copy)."""
    for attr in ("SHOTS_V3", "SHOTS", "CAMS_V3", "CAMS"):
        val = getattr(mod, attr, None)
        if val is None or isinstance(val, (list, tuple, dict, str)):
            continue
        if not _is_iterable(val):
            continue  # not iterable at all — the shape checks reject it
        try:
            setattr(mod, attr, list(val))
        except Exception:
            continue  # unreadable iterator — the shape checks handle it
        rep.warn(
            f"import: {attr} is a one-shot iterator ({_tname(val)}) — "
            "materialized to a list for checking (the exporter consumes it "
            "exactly once; declare a list/tuple so repeated reads see the "
            "value)")


def coverage_summary(mod) -> dict:
    """F2C-5: what the preflight actually had to check. 'vacuous' = the
    module declares none of the story tables — every check passed with
    ZERO coverage (law 20 makes that CORRECT, but it must be LOUD, not a
    full-fat PASS)."""
    def _n(v):
        if v is None:
            return 0
        if isinstance(v, (list, tuple, dict, str)):
            return len(v)
        return 1  # declared but unmeasurable (scalar / one-shot iterator)

    board = getattr(mod, "BOARD", None)
    cov = {
        "shots": _n(shots_table(mod)),
        "cams": _n(cam_table(mod)),
        "board": _n(board),
        "story_constants": sum(
            1 for a, _k in STORY_SOURCES
            if getattr(mod, a, None) is not None),
    }
    cov["vacuous"] = not any(
        cov[k] for k in ("shots", "cams", "board", "story_constants"))
    return cov


# ---------------------------------------------------------------------------
# CLI + summary
# ---------------------------------------------------------------------------

def parse_args(argv):
    p = argparse.ArgumentParser(
        prog="export_preflight.py",
        description="D19 pre-export contract gate for previz scene modules.")
    p.add_argument("--module", required=True,
                   help="path to the scene module .py (imported by PATH)")
    p.add_argument("--json", dest="json_out", default=None,
                   help="write a machine-readable summary to this path")
    p.add_argument("--skip-build", action="store_true",
                   help="Phase S only (no scene build; parity guard B5 does "
                        "NOT run in this mode)")
    p.add_argument("--animate-dry", action="store_true",
                   help="after B checks pass, dry-run mod.animate with a "
                        "small n_frames (opt-in: crowd modules need bakes)")
    return p.parse_args(argv)


def print_summary(rep: Report, mod_path: str, flags: dict,
                  checks: dict, coverage: dict | None = None) -> int:
    print(f"{PF} ---- PREFLIGHT SUMMARY ----", flush=True)
    print(f"{PF} module: {mod_path}  flags: {flags}", flush=True)
    print(f"{PF} checks: " + "  ".join(f"{k}={v}" for k, v in checks.items()),
          flush=True)
    if coverage is not None:
        cov_line = "  ".join(f"{k}={v}" for k, v in coverage.items()
                             if k != "vacuous")
        if coverage.get("vacuous"):
            # F2C-5: a vacuous pass must never look like a checked-clean one.
            print(f"{PF} coverage: {cov_line}  VACUOUS — the module declares "
                  "NO story tables; every check passed with nothing to check "
                  "(verify --module)", flush=True)
        else:
            print(f"{PF} coverage: {cov_line}", flush=True)
    if rep.warns:
        shown = rep.warns[:WARN_CAP]
        for w in shown:
            print(f"{PF} WARN {w}", flush=True)
        extra = len(rep.warns) - len(shown)
        if extra > 0:
            print(f"{PF} WARN ... +{extra} more (capped at {WARN_CAP} lines; "
                  "full list via --json)", flush=True)
    print(f"{PF} rejections: {len(rep.rejects)}  warnings: "
          f"{len(rep.warns)} (WARNs never fail the run)", flush=True)
    if rep.rejects:
        print(f"{PF} RESULT: REJECTED (exit 3)", flush=True)
        return 3
    print(f"{PF} RESULT: PASS", flush=True)
    return 0


def write_json(path, mod_path, flags, checks, rep, scene=None,
               coverage=None) -> None:
    doc = {
        "tool": "export_preflight (D19 REV-3)",
        "module": mod_path,
        "flags": flags,
        "checks": checks,
        "status": "rejected" if rep.rejects else "pass",
        "rejections": rep.rejects,
        "warnings": rep.warns,
    }
    if coverage is not None:
        doc["coverage"] = coverage  # F2C-5: vacuous passes are visible here
    if scene is not None:
        doc["scene"] = {
            "fps": int(scene.render.fps),
            "fps_base": float(scene.render.fps_base),
            "frame_start": int(scene.frame_start),
            "frame_end": int(scene.frame_end),
            "n_objects": len(scene.objects),
        }
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=1)
        print(f"{PF} JSON summary -> {path}", flush=True)
    except OSError as e:
        print(f"{PF} WARN could not write --json {path}: {e}", flush=True)


def _finish(rep, args, mod_path, flags, checks, scene,
            coverage=None) -> int:
    rc = print_summary(rep, mod_path, flags, checks, coverage=coverage)
    if args.json_out:
        write_json(args.json_out, mod_path, flags, checks, rep, scene=scene,
                   coverage=coverage)
    return rc


def main() -> int:
    args = parse_args(script_argv())
    mod_path = os.path.abspath(args.module)
    flags = {"skip_build": args.skip_build, "animate_dry": args.animate_dry}
    print(f"{PF} export_preflight (D19 REV-3): module={mod_path} "
          f"flags={flags}", flush=True)

    rep = Report()
    checks: dict[str, str] = {}
    scene = None
    ctx = None
    coverage = None

    # ---- module import (by PATH — this tool's job; the EXPORTER's
    # name-only import constraint applies to t10 fixtures, not here) ----
    if not os.path.isfile(mod_path):
        rep.reject(f"module: file not found: {mod_path}. Fix: pass the .py "
                   "path to --module (preflight imports by PATH).")
        checks["import"] = "rejected"
        return _finish(rep, args, mod_path, flags, checks, scene,
                       coverage=coverage)
    try:
        mod = _import_scene_file(mod_path)
        checks["import"] = "ok"
    except Exception:
        rep.reject("module: import RAISED — fix the module first "
                   "(traceback tail on the next line).")
        rep.reject("import traceback tail:\n" + _tb_tail())
        checks["import"] = "rejected"
        return _finish(rep, args, mod_path, flags, checks, scene,
                       coverage=coverage)

    # F2C-9: normalize one-shot iterator TABLE constants BEFORE any phase
    # reads them (materialized in place; see materialize_table_iterators).
    materialize_table_iterators(mod, rep)

    # ---- Phase S (no bpy scene state touched) ----
    n = len(rep.rejects)
    s1_entry_points(mod, rep)
    checks["S1"] = _st(rep, n)

    n = len(rep.rejects)
    shots = s2_shots(mod, rep)
    s2_schema(mod, rep)
    s2_beats(mod, rep)
    checks["S2"] = _st(rep, n)

    n = len(rep.rejects)
    missing_cam_rows, legacy_cams = s3_coherence(mod, shots, rep)
    checks["S3"] = _st(rep, n)

    n = len(rep.rejects)
    s4_sfx(mod, shots, rep, os.path.dirname(mod_path))
    checks["S4"] = _st(rep, n)

    # F2C-5: coverage count + the loud vacuous WARN (WARNs never fail the
    # run — law 20 says vacuous is CORRECT, it just must not be silent).
    coverage = coverage_summary(mod)
    if coverage["vacuous"]:
        rep.warn(
            "coverage: the module declares NO story tables (0 shots, 0 cam "
            "rows, 0 BOARD entries, 0 story constants) — preflight coverage "
            "is VACUOUS (every check passed with nothing to check; law 20) "
            "— verify --module points at the intended film module")

    if args.skip_build:
        checks["B"] = "skipped (--skip-build: parity guard B5 does NOT run)"
        return _finish(rep, args, mod_path, flags, checks, scene,
                       coverage=coverage)
    if rep.rejects:
        # A module that fails Phase S is not safe to build — stop here.
        checks["B"] = "skipped (Phase S rejected)"
        return _finish(rep, args, mod_path, flags, checks, scene,
                       coverage=coverage)

    # ---- Phase B: fresh empty blend -> build_scene ----
    bpy.ops.wm.read_factory_settings(use_empty=True)
    try:
        ctx = mod.build_scene()
    except Exception:
        rep.reject(
            "B1 build_scene: RAISED (traceback tail on the next line) — "
            "the exporter calls it unguarded (exporter:1039).")
        rep.reject("B1 traceback tail:\n" + _tb_tail())
        checks["B1"] = "rejected"
        checks["B2-B6"] = "skipped"
        return _finish(rep, args, mod_path, flags, checks, scene,
                       coverage=coverage)

    # B1 — ctx dict + scene non-empty (exporter:1056 fallback mirrored)
    if not isinstance(ctx, dict):
        rep.reject(
            f"B1 ctx: build_scene() must return a dict; got {_shape(ctx)} — "
            "the exporter reads ctx.get('scene') and falls back to "
            "bpy.context.scene (exporter:1056). Fix: return a ctx dict.")
        checks["B1"] = "rejected"
        checks["B2-B6"] = "skipped"
        return _finish(rep, args, mod_path, flags, checks, scene,
                       coverage=coverage)
    scene = ctx.get("scene") or bpy.context.scene
    if len(scene.objects) == 0:
        # F2C-12 reword: the exporter would NOT ship an empty GLB — its own
        # fail-closed gates (1 and 6) reject first. Stop early with the
        # honest reason.
        rep.reject(
            "B1 ctx: the built scene has 0 objects — the exporter's own "
            "fail-closed gates would reject the package (gate 1: zero "
            "cameras in the GLB; gate 6: empty actions manifest), so "
            "nothing reviewable would ship. Fix: build_scene must add "
            "objects.")
        checks["B1"] = "rejected"
        checks["B2-B6"] = "skipped"
        return _finish(rep, args, mod_path, flags, checks, scene,
                       coverage=coverage)
    checks["B1"] = "ok"

    n = len(rep.rejects)
    b2_fps(mod, rep, scene)
    checks["B2"] = _st(rep, n)

    n = len(rep.rejects)
    all_marks = b3_markers(mod, rep, scene, shots,
                           missing_cam_rows=missing_cam_rows,
                           legacy_cams=legacy_cams)
    checks["B3"] = _st(rep, n)

    n = len(rep.rejects)
    b4_hidden_sweep(mod, rep, scene, shots, all_marks)
    checks["B4"] = _st(rep, n)

    n = len(rep.rejects)
    b5_parity(mod, rep, scene)   # BEFORE B-sfx: snapshot fps/frame_start
    checks["B5"] = _st(rep, n)   # before any emitter can mutate the scene

    n = len(rep.rejects)
    b_sfx_emitter(mod, rep, ctx, scene, shots)
    checks["B-sfx"] = _st(rep, n)

    if args.animate_dry:
        if rep.rejects:
            checks["B6"] = "skipped (earlier rejections)"
        elif not callable(getattr(mod, "animate", None)):
            checks["B6"] = "skipped (no animate)"
        else:
            try:
                b6_animate_dry(mod, rep, ctx)
                checks["B6"] = "ok"
            except Exception:
                rep.reject(
                    "B6 animate-dry: mod.animate(ctx, start_frame=1, "
                    "n_frames=8) RAISED (opt-in check; crowd modules need "
                    "bakes — that is why this flag is default-off). "
                    "Traceback tail on the next line.")
                rep.reject("B6 traceback tail:\n" + _tb_tail())
                checks["B6"] = "rejected"
    else:
        checks["B6"] = "skipped (--animate-dry off)"

    return _finish(rep, args, mod_path, flags, checks, scene,
                   coverage=coverage)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        # fail-closed: a gate must never pass (or crash ambiguously)
        traceback.print_exc()
        print(f"{PF} INTERNAL ERROR (fail-closed) — exiting 3", flush=True)
        sys.exit(3)
