# D19 — EXPORT PREFLIGHT + t10 REGRESSION SUITE (design, session-16)

> Status: DRAFT-1 for critique. Standing law 2: fresh-agent critique round
> BEFORE implementation. Scope doctrine: this session is the KIT-QUALITY
> lane — no film building, no scene-module work (parallel lane owns that).

## Problem (evidence: session-16 audit 1-a)

The export/package lane has **zero test coverage** and keeps producing
scene-side landmines (R4 NameError in gate 14 crashed EVERY run; tferry
session hit THREE contract landmines in one session: `ctx["scene"]`,
BEATS shape, sfx `{name,frame}` keys dropped silently by the app).
Every landmine was discovered LATE — after bakes, framing rounds, and
night-lighting passes — when the fix costs the most. The audits also
found: shape crashes are opaque and unattributed (P0-1), BOARD entries
silently drop (P0-2), the sfx stream has no producer-side gate (P0-3),
film modules export green-but-story-empty through THIS tree's exporter
(P0-4), module entry-point mismatches crash opaquely (P0-5).

## Goals

1. **Move contract failure to the CHEAP end**: validate the scene module
   against the export contract BEFORE any bake/render/reframe work.
2. **Make t10 real**: an in-Blender regression suite that walks the
   exporter end-to-end on a synthetic fixture, including negative cases.
3. **Fail-closed with teacher-grade errors**: every rejection names the
   constant, the row index, the expected shape, and the fix.

## Non-goals

- No film-vocabulary port into this tree's exporter (CAST/SYNOPSIS/BEATS
  mapping stays in the canonical agent-kit copy — different lane).
- No changes to gate semantics 1–14 beyond the two named hardenings below.
- No scene-module edits (parallel lane's files).

## Design

### D19.1 — `scripts/export_preflight.py` (new tool, runs IN-BLENDER via blrun)

Two phases, both in-Blender (scene modules import bpy):

**Phase S (static):** import the module (`importlib.util.spec_from_file_location`),
then, WITHOUT calling build_scene:
- **S1 entry points**: `build_scene` callable; `animate` absent OR its
  signature accepts `(ctx)` plus optional `start_frame`/`n_frames` kwargs
  (the exporter's two dispatch shapes — exporter:1040-1053); optional
  `emit_sfx_events(ctx, out_dir)` callable.
- **S2 attributed schema pass** over DECLARED constants only (lane-aware,
  law 20 — a constant that doesn't exist is vacuous, never an error):
  - `SHOTS`/`SHOTS_V3`: each row len 4, `(sid:str, f0:int, f1:int,
    intent:str)`, f0 < f1.
  - `CAMS`/`CAMS_V3`: each row len 7, fields 1-2 are 3-vecs of numbers,
    lens numeric.
  - `BEATS` (if declared): each row len 3 `(id, t_seconds: float,
    label)`; t strictly increasing; t == (f0-1)/FPS for the shot it
    opens (±1 frame tolerance) when SHOTS also declared.
  - `BOARD` (if declared): dict; each entry decodes as `(main[0..5],
    extra)` — reuse the exporter's own BOARD decode by importing the
    exporter module and calling its per-entry parse if it is
    function-shaped, else replicate leniently and PARITY-CHECK (D19.2).
  - `DIALOG`/`KNOCKDOWNS_V3`/`MUZZLE_BURSTS_V3`/`JEEP_X_V3`/
    `_V3_SEG`/`RB_FALLS`/`RB_KD`/`BARRICADE_T_V3`/`BARRICADE_Y_V3`:
    arity checks matching STORY_SOURCES consumption (exact arity table
    maintained in the preflight source, citing exporter lines).
  - `CHASE_FALLS_V3`: dict-of-pairs. `RUN_PARAMS`: dict of dicts.
    `MOTION_POLICY`/`FLATNESS_POLICY`: dicts with the exporter's inner keys.
  - Every failure message: `"<CONSTANT>[<row>]: expected <shape>, got
    <shape> — <fix>"`.
- **S3 cross-table coherence**: SHOTS contiguous + spans total_frames
  (if declared); every sid has a CAMS row whose name contains sid;
  FPS agreement — module `FPS`/`FPS_HZ` constant vs `RUN_PARAMS[...]["fps"]`
  (if present) vs `render.fps` (Phase B) — mismatches are rejections.
- **S4 sfx stream shape** (if module declares `SFX_EVENTS` or defines
  `emit_sfx_events`): validate the declared event list shape — every
  event dict has `name` or `kind`, plus integer `frame`; `name` should
  be in `build_sfx.PATCHES` ∪ a known-marker allowlist (unknown → WARN
  listing the synth names); every `frame` inside some SHOTS window (±4f)
  when SHOTS declared. If the module ships a JSON path instead, validate
  the file.

**Phase B (build, flag `--skip-build` to omit):** fresh empty blend →
call `mod.build_scene()` →
- **B1 ctx**: return value is a dict; `ctx.get("scene")` is a scene with
  ≥1 object, or bpy.context.scene has ≥1 object.
- **B2 fps**: `scene.render.fps == module FPS constant` (when declared);
  `fps_base == 1.0` (else reject — the exporter casts int(fps) and
  ignores fps_base, exporter:1181).
- **B3 markers**: for each SHOTS row, a timeline marker exists at f0 and
  `marker.camera` is set and `sid in marker.camera.name` (the name
  convention is NOT enforced — tdawn uses CAM_*, tferry SHOT_* —
  containment only, P1-3).
- **B4 hidden-sweep**: `view_layer.update()` + `render_hidden_objects(scene)`;
  REJECT if any shot camera, any CAST/characters root (when CAST
  declared), or any CAMS-named object is in the exclusion set (P1-1).
- **B5 (opt-in `--animate-dry`)**: call
  `mod.animate(ctx, start_frame=1, n_frames=<small>)` when the sentinel
  dispatch shape applies. DEFAULT OFF — crowd scenes need bakes; the
  sentinel path may legitimately fail without caches. When on, a raise
  is a rejection with the traceback.

**Exit codes**: 0 clean (prints WARNs if any); 3 on any rejection
(matches look.py severity convention; blrun propagates).

**CLI**: `blrun.sh --background --python scripts/export_preflight.py --
  --module <path> [--json <out>] [--skip-build] [--animate-dry]`.

### D19.2 — decode-parity guard (the drift killer)

After S2 passes, the preflight imports `export_previz_package` and calls
its `_collect_story(mod, fps, frame_start)` inside a try/except:
- It raising = an exporter-side decode bug OR a shape the preflight's
  schema missed → REJECT with the full traceback (labeled "decode-parity
  failure: report the constant; this is a preflight-schema gap").
- `set(BOARD.keys())` vs `set(story["board"].keys())` diff → any dropped
  entry REJECTS (the P0-2 silent-drop detector, gate-quality).
- Rationale: the exporter's decoders stay the single behavioral source
  of truth; preflight owns ERROR QUALITY (attribution) and adds
  pre-render coverage. Schema drift between the two layers is caught by
  the parity call itself, and by t10 negative cases.

### D19.3 — exporter hardenings (two, minimal, lane-aware)

- **Gate 15 (sfx conformance, fail-closed)**: after
  `emit_sfx_events`, if `sfx_events.json` exists in out_dir → every
  event has `name|kind` + integer `frame`; file fps == scene fps.
  Missing file → pass vacuously (template lane has no sfx — law 20).
  Malformed → `EXPORT REJECTED` naming the first bad event index.
  (The F-TF4 class can never again export green.)
- **Gate 4 strengthening**: if `BOARD` is declared non-empty but
  `story["board"]` decoded empty → fail. Per-entry NOTEs stay (leniency
  for partial boards), but a 100% decode failure now rejects.

### D19.4 — `tests/test_t10_export.py` (regression suite)

Fixture: a tiny synthetic scene module WRITTEN BY THE TEST to a temp dir
(escape-family shapes: SHOTS_V3 + CAMS_V3 + BOARD + DIALOG + sfx
events; 2 shots, 2 cams, ~48 frames, no crowd, no skins). The test runs
REAL subprocesses (the r9 chunking pattern: real scripts +
`--python-exit-code`):

- **t10.1 happy path**: exporter on the fixture → exit 0; previz.json
  story keys present; GLB exists with cameras; sfx_events.json conforms.
- **t10.2 preflight happy**: preflight on the fixture → exit 0.
- **t10.3 negative: malformed sfx** (event with `id` key — the F-TF4
  repro): preflight exit 3 AND (post-fix) exporter gate 15 rejects.
- **t10.4 negative: BEATS wrong shape** (`(label, shot, frame)` — the
  session-15 repro): preflight exit 3 naming BEATS[row].
- **t10.5 negative: BOARD fully undecodable**: gate 4 (strengthened)
  rejects the exporter; preflight parity also rejects.
- **t10.6 negative: short CAMS row**: preflight exit 3 naming
  `CAMS_V3[<i>]` (the P0-1 attribution requirement — the error must
  name the constant+row, assert the message content).
- **t10.7 decode-parity sentinel**: a fixture whose BOARD decodes in
  S2 but drops in _collect_story would be an exporter bug — assert the
  parity guard fires (fixture: an entry type S2 accepts and the
  exporter NOTEs-and-drops; if the exporter decodes it fine, this case
  asserts the clean path instead — implemented as: assert parity diff
  is empty on the happy fixture, and the strengthened gate 4 covers the
  drop case).

Runtime budget: every case is a fresh Blender process ≈ 5-10 s; total
< 2 min. No renders (exporter does not render; stills skipped).

### D19.5 — docs

- AGENTS.md: new "Ship & verify (review lane)" section — preflight
  BEFORE export as the standard loop, exporter flags/gates summary,
  sfx contract `{name|kind, frame}`, BEATS shape law.
- kb/tdawn_vision_film.md: add the preflight step to the recipe (step
  between framing and export).
- docs/USABILITY_S16_session16.md: the friction record for this wave.

## Review questions for the critique round

1. Is the S2 arity table a SECOND source of truth that will rot? (Is
   D19.2's parity guard sufficient to catch the rot early?)
2. Should gate 15 live in the exporter (fail-closed at export) vs
   preflight only? Any escape-lane scene that ships a malformed sfx
   stream LEGITIMATELY?
3. Is B4's rejection set right (shot cams + CAST roots + CAMS-named)?
   What else legitimately hides render objects that must NOT trip it?
4. t10.7 as designed is weak — is there a sharper decode-parity test?
5. Anything in the sentinel/animate dispatch the preflight should
   verify but doesn't?
