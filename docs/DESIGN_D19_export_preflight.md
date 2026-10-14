# D19 — EXPORT PREFLIGHT + t10 REGRESSION SUITE (design REV-3, session-17)

> REV-3 (session-17, wave-1 self-audit F2C-3/4/5): (1) S3's exact
> CAM_<sid>-row-missing demoted from REJECT to WARN — the exporter
> treats cam specs as an optional merge (exporter:1151-1159) and gate
> 11 skips static cams, so the spec was stricter than the thing it
> guards; S3 now REJECTS only when the shot's camera OBJECT is also
> missing from the scene. (2) Gate-15 wording: fps OPTIONAL in the
> shipped sfx-file check (5-a P2-3 was already the code's behavior).
> (3) Vacuous pass is loud: a module with no SHOTS/BOARD/CAMS gets a
> WARN + a coverage count in summary/JSON. Line anchors re-verified
> against tip (F2C-6, verified by grep, never from memory).
> REV-2: incorporates critique round 2-a (ADOPT-WITH-CHANGES, 7 blocking
> fixes — all verified against exporter code). Status: FINAL for
> implementation. Scope doctrine: KIT-QUALITY lane — no scene-module work.
> Critique evidence: worklog Task 2-a.

## Problem (audit 1-a, verified)

The export/package lane has zero test coverage and keeps producing
scene-side landmines discovered LATE (R4 gate-14 NameError; the tferry
session's three contract landmines: ctx["scene"], BEATS shape, sfx
`{name,frame}` keys). The audits ranked 5 P0s: opaque unattributed shape
crashes (P0-1), silent BOARD entry drops (P0-2), ungated sfx stream
(P0-3), film modules exporting green-but-story-empty through THIS
exporter (P0-4 — canonical copy is agent-kit's; out of scope here),
opaque entry-point mismatches (P0-5).

## Design REV-2

### D19.1 — `scripts/export_preflight.py` (new tool, runs IN-BLENDER via blrun)

**Phase S (static):** import the module via `blender_kit._import_scene_file`
(already implements sys.modules dedupe — blender_kit:278-290); insert
`scripts_dir` into `sys.path` FIRST (Blender ignores PYTHONPATH in
background mode and the exporter only adds it inside main():1010-1015).
Without calling build_scene:

- **S1 entry points**: `build_scene` callable. `animate` (if present):
  replicate the exporter's dispatch EXACTLY (exporter:1035-1048) via
  `inspect.Signature(...).bind`: if an `n_frames` param exists and its
  default passes `isinstance(default, int)` (bool-is-int quirk
  preserved — it's the exporter's real behavior), then
  `bind(ctx)` must succeed; else `bind(ctx, start_frame=1,
  n_frames=None)` must succeed. A bare `def animate(ctx)` therefore
  FAILS S1 (the exporter's sentinel branch TypeErrors on it — the P0-5
  class, pinned by a t10 case). Optional `emit_sfx_events(ctx, out_dir)`
  callable.
- **S2 attributed schema pass** over DECLARED constants only (law 20:
  absent constant = vacuous). The constant→key map is IMPORTED from the
  exporter's `STORY_SOURCES` (81-103) — never restated. Arity table
  (all 21 entries, ≥n semantics — the decoder never width-checks; an
  exact-width check would be stricter than the decoder and false-reject
  real modules). Derived from _collect_story (531-662) + 1120-1131:

  | Constant | Real consumption shape | Lines |
  |---|---|---|
  | `CAMS_V3`/`CAMS` | list; row ≥7: (name:str, loc0:3-num, loc1:3-num, lens:num, aim:3-num, parent_jeep:bool, shake_amp:num) | 650-660 |
  | `SHOTS_V3`/`SHOTS` | rows ≥4 (sid:str, f0:int, f1:int, intent:str); `getattr(SHOTS_V3) or getattr(SHOTS)` fallback replicated (1120-1122) | 1120-1131 |
  | `DIALOG` | list; row ≥2 (clip:str, onset_frame:int) — FRAMES not seconds | 544-547 |
  | `KNOCKDOWNS_V3` | list; row ≥4 (id:str, t_hit:float-sec, x_off:float, style:str) | 549-556 |
  | `CHASE_FALLS_V3` | dict {int-able key: t:float-sec} | 558-562 |
  | `MUZZLE_BURSTS_V3` | list; row ≥3 ints (f0,f1,every_n) | 564-567 |
  | `JEEP_X_V3` | list; row ≥2 floats (t,x_off) | 569-572 |
  | `_V3_SEG` | list; row ≥4 floats (t0,t1,v0,v1) | 574-578 |
  | `BOARD` | dict name→(MAIN, EXTRA); MAIN ≥6-seq (int,int,int,vec3|None,float,str); EXTRA seq with [0] float-or-falsy; missing EXTRA[1] is the real drop case | 580-596 |
  | `RUN_PARAMS` | dict str→dict str→(str|float); a None value crashes the whole collector | 598-603 |
  | `MOTION_POLICY` | dict; optional intended_static:list[str], intended_subject_tree:str | 605-612 |
  | `FLATNESS_POLICY` | dict str→≥2 ints (f0,f1) | 614-617 |
  | `LUNGE_V3` | dict; y_offsets→list of (t:float,y:float); other values numeric→float; non-numeric silently DROPPED (625-627 — next gate-4-class candidate, noted not fixed) | 619-627 |
  | `RB_FALLS`/`RB_KD` | FLAT list of str|int scalars — NOT tuples; a None item crashes the collector | 629-633 |
  | `T_DRIVE`/`BARRICADE_T_V3`/`BARRICADE_Y_V3`/`RUN_SPEED`/`RUN_START_Y` | single scalar → float | 635-644 |
  | `TOTAL_FRAMES_V3` | single scalar → int | 641 |
  | `HERO_MODE` | single scalar → str | 646-648 |

  `BEATS` (if declared): **shape-only WARN** (each row ≥3, field 1
  numeric). NO timing rules — the t==(f0-1)/FPS opener rule
  false-rejects tdawn (BEATS are narrative beats, not shot boundaries;
  tdawn BEATS[0]=("calm",1.0,...) with S1 at f1) and BEATS has ZERO
  consumers in this exporter (it is the canonical agent-kit copy's
  contract — validated for THAT lane, documented as such).
- **S3 cross-table coherence**: SHOTS contiguous; every sid has a CAMS
  row whose name is EXACTLY `CAM_<sid>` — containment ("S1" ⊂
  "CAM_S11") is FORBIDDEN as a check; a mismatching-but-CAM_-prefixed
  row is a WARN. FPS agreement (module constant vs RUN_PARAMS fps when
  present; render.fps checked in Phase B). Span claims derive from the
  SCENE (frame_start/frame_end — the exporter's own span gate,
  1284-1290), never a module constant.
- **S4 sfx stream shape** (if the module declares `SFX_EVENTS` or
  defines `emit_sfx_events`): every event dict has `name` or `kind` +
  integer `frame`; `frame` inside some SHOTS window (±4f) when SHOTS
  declared. Name vocabulary: WARN COMPACTLY (one line: count + first 3
  unknowns) against `build_sfx.PATCHES` — the escape film's synth
  vocab; film-lane markers legitimately fall outside it, so unknown
  names are never rejections. If the module ships a JSON path instead,
  validate the file (`{fps?, events}` schema — REV-3: fps is OPTIONAL in
  the shipped gate (5-a P2-3); `name|kind` + integer `frame` are the
  required core, and fps AGREEMENT is checked only when fps is present —
  both real producers write it, but a missing fps no longer rejects).

**Phase B (build, flag `--skip-build`):** fresh empty blend →
`mod.build_scene()` →
- **B1 ctx**: dict; `ctx.get("scene")` or bpy.context.scene has ≥1 object.
- **B2 fps**: `scene.render.fps == module FPS constant` (when declared);
  `fps_base == 1.0` (exporter:1205 casts int(fps), ignores fps_base —
  verified zero fps_base references; REV-3 re-anchor).
- **B3 markers** (mirror the exporter EXACTLY, 1142-1153 — REV-3
  re-anchor; `_marker_bindings` def at 109-112): for each
  SHOTS row, a timeline marker exists at f0, `marker.camera` is set,
  and `marker.camera.name.startswith("CAM_")`. Marker NAMES are
  unconstrained (tferry names them SHOT_* — only the CAMERA name is
  contracted). Camera-vs-sid match `marker.camera.name == f"CAM_{sid}"`
  is a WARN (real convention in both films), never a rejection.
- **B4 hidden-sweep**: `render_hidden_objects(scene)` (it already does
  view_layer.update() — F-TD5 wave A). REJECT if any of: shot cameras,
  `Aim.*` targets (a hidden aim target is a guaranteed gate-2 failure —
  catch it at the cheap end), CAST roots (CAST spec: dict of dicts with
  a `"root"` key — scene_terminal_dawn.py:119-124) are in the
  exclusion set. EXEMPT: `atmo_objects(scene)` names (blender_kit:876-909
  — volume shells are SUPPOSED to be render-hidden; the exporter
  excludes them by design, 1100-1108), KIT_ANNOT_* (never saved).
- **B5 parity guard** (runs HERE, in Phase B, where real fps/frame_start
  exist — critique fix): import export_previz_package (bpy import OK in
  Blender), call `_collect_story(mod, float(scene.render.fps),
  scene.frame_start)`:
  - raise → **differential attribution**: re-run with one declared
    constant deleted at a time (≤21 iterations, pure getattr, no bpy)
    to name the offending constant; message says BOTH "scene data bug
    in <CONSTANT>" and "if preflight S2 accepted it, this is also a
    preflight-schema gap — report it".
  - `set(str(k) for k in mod.BOARD)` vs `set(story["board"].keys())`
    (keys are str()-cast at 586) — any dropped entry REJECTS (P0-2).
- **B6 (opt-in `--animate-dry`)**: `mod.animate(ctx, start_frame=1,
  n_frames=<small>)` for sentinel-shape modules. DEFAULT OFF (crowd
  scenes need bakes). A raise = rejection with traceback. Even when
  OFF, S1's bind check already proves the signature accepts the
  dispatch.

**Exit codes**: 0 clean (WARNs printed); 3 on any rejection (look.py
severity convention; blrun propagates).
**CLI**: `blrun.sh --background --python scripts/export_preflight.py --
  --module <path> [--json <out>] [--skip-build] [--animate-dry]`.

### D19.2 — decode-parity guard semantics

= B5 above (Phase B, real fps/frame_start, BOARD key-set diff,
differential attribution). The exporter's decoders stay the single
behavioral source of truth; preflight owns ERROR QUALITY + pre-render
coverage. Drift rot: S2-looser-than-decoder is caught by B5 raising;
S2-stricter-than-decoder (false rejections) is caught by the t10
property test below.

### D19.3 — exporter hardenings (two, minimal, lane-aware)

- **Gate 15 (sfx conformance, fail-closed)**: after emit_sfx_events,
  if `<out_dir>/sfx_events.json` exists → file has `fps` + `events`;
  every event has `name|kind` + integer `frame`; file fps ==
  scene.render.fps. Missing file OR module has no emit_sfx_events →
  pass vacuously (template lane, law 20). `emit_sfx_events` exists but
  writes nothing → WARN (a scene may defer sfx), not reject. Malformed
  → `EXPORT REJECTED` naming the first bad event index. (The F-TF4
  class can never again export green; SKILL mistake 10: fail-closed.)
- **Gate 4 strengthening**: BOARD declared non-empty but
  `story["board"]` empty → fail (the only NOTE-and-drop decoder is
  BOARD; LUNGE_V3's silent value-drop is noted in preflight S2, not
  exporter-gated this wave).

### D19.4 — tests (two tiers)

**Tier 1 — `tests/test_t10_preflight_prop.py` (pure pytest, no Blender,
milliseconds):** import `_collect_story` under stubbed
`bpy`/`blender_kit` in sys.modules; for every STORY_SOURCES constant,
generate decoder-dropping variants (BOARD entry missing EXTRA[1], RUN_PARAMS
None value, RB_FALLS None item, short rows, wrong types) and assert the
property: **decoder drops/raises ⇒ S2 rejects** and **decoder accepts ⇒
S2 accepts** (accept-set superset, both drift directions). This replaces
the weak t10.7.

**Tier 2 — `tests/test_t10_export.py` (subprocess, r9 pattern: real
scripts + `--python-exit-code`, foreground, generous timeouts):**
fixture = a tiny escape-family scene module WRITTEN BY THE TEST into
`scripts/` (the exporter imports scene modules by NAME from
scripts/-only sys.path — a temp dir is UNREACHABLE, Blender ignores
PYTHONPATH: critique fix), named non-`scene_escape_v*`; try/finally
removes it. The fixture self-verifies its ground truth and SATISFIES
the exporter's own gates: markers at every f0 bound to CAM_*-named
cameras; SHOTS spanning scene frame_start..frame_end exactly and
contiguous; ≥1 ASSIGNED action (gate 6 — the happy path dies on an
empty actions manifest without this); 2 shots, 2 cams, ~48 frames, no
crowd/skins. Cases:
- t10.1 happy path: exporter → exit 0; previz.json story keys; GLB
  with cameras; sfx_events.json conforms to {fps, events}.
- t10.2 preflight happy: exit 0.
- t10.3 negative: malformed sfx (event with `id` key — F-TF4 repro):
  preflight exit 3 AND exporter gate 15 rejects.
- t10.4 negative: BEATS wrong shape ((label, shot, frame) — the
  session-15 repro): preflight WARN-level (shape-only) — assert the
  WARN text names BEATS; the canonical-copy shape stays out of this
  tree's contracts.
- t10.5 negative: BOARD fully undecodable: exporter gate 4
  (strengthened) rejects; preflight B5 parity also rejects.
- t10.6 negative: short CAMS row: preflight exit 3 with message naming
  `CAMS_V3[<i>]` (P0-1 attribution asserted on message content).
- t10.7 negative: bare `def animate(ctx)`: preflight S1 exit 3 (the
  sentinel-TypeError class, caught pre-render).

Runtime budget: 7 fresh Blender processes ≈ 5-10 s each; MEASURE the
total once and record the number here (calibration law). No renders.

### D19.5 — docs

- AGENTS.md "Ship & verify (review lane)" section: preflight BEFORE
  export as the standard loop; exporter flags/gates summary; sfx
  contract `{name|kind, frame}` + `{fps, events}` file schema; BEATS
  shape law (canonical-copy lane); **marker NAMES unconstrained — only
  the CAMERA name carries the CAM_ contract** (write it down or the
  next film reintroduces the confusion).
- kb/tdawn_vision_film.md: preflight step between framing and export.
- docs/USABILITY_S16_session16.md: the wave's friction record.

## REV-2 blocking fixes from critique (all incorporated)

1. B3 rewritten to mirror the exporter (CAM_ prefix on the CAMERA name;
   sid-match demoted to exact-match WARN; `sid in name` deleted).
2. S2-BEATS demoted to shape-only WARN (false-rejects tdawn; zero
   consumers in this tree).
3. S1 replicates the dispatch via Signature.bind (bool-is-int quirk;
   catches bare `def animate(ctx)`; t10.7 pins it).
4. t10 fixture written into scripts/ under non-escape name; fixture
   satisfies gates (markers/span/gate-6 actions).
5. B4 rejection set: atmo exemption + Aim.* + CAST dict-of-dicts spec;
   redundant update() dropped.
6. Parity guard moved to Phase B (real fps/frame_start); BOARD key-set
   comparison (str()-cast); sys.path pin before exporter import.
7. Parity-raise attribution via differential deletion; message names
   both scene-bug and schema-gap classes.
