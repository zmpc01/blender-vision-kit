# Audit 2-c — D19 export preflight + t10 (fresh eyes, session-17)

Auditor: Task 2-c (READ-ONLY). Target: the session-16 D19 wave —
`scripts/export_preflight.py` (1373 l), `tests/test_t10_preflight_prop.py`
(236 l), `tests/test_t10_export.py` (287 l), and the exporter gates they
layer over (`export_previz_package.py` gate 15 / gate 4 / `_collect_story`),
plus the `export_usd.py` RNA-filter fix. Spec: `docs/DESIGN_D19_export_preflight.md`
(REV-2). Method: full read of all five files + the real film modules
(tdawn/lferry/tgreen BEATS, SHOTS, CAMS, emitters) + blender_kit helpers;
pure-python probes with stubbed bpy/blender_kit against the REAL
`_collect_story` and the REAL checker; `python3 tests/test_t10_preflight_prop.py`
run green (100 checks / 0 failed). Blender not run (not installed here) —
Blender-dependent items are tagged UNVERIFIED-needs-Blender.

Severity ladder per brief: P0 crash/data-loss/silent-wrong-render on
documented path; P1 wrong result on plausible input / fail-open gate;
P2 friction / doc-lies / wrong diagnostics; P3 nit.

---

## Findings

### F2C-1 — P1 (UNVERIFIED-needs-Blender): the RNA-kwarg fix landed on ONE of THREE `usd_export` call sites; `--usd-sidecar` still ships the unfiltered 4.5-calibrated set and should TypeError-crash on the kit's DEFAULT Blender (5.2.2)

- `scripts/export_previz_package.py:930-946` (`_export_usd_sidecar`):
  ```python
  bpy.ops.wm.usd_export(
      filepath=out_path,
      export_animation=True,
      ...
      export_textures=True,
      export_custom_properties=True,
      custom_properties_namespace="userProperties",
      ...
      triangulate_meshes=False,
  )
  ```
  No RNA filter, no TypeError retry (only `finally: unregister`).
- Evidence the kwarg set is wrong on 5.2.2 is IN-REPO: `scripts/export_usd.py:128-131` —
  "The battery caught the drift class on 5.2.2 (**export_textures
  unrecognized** — the 4.5-calibrated set is not stable across Blender
  versions…)"; ADR_BLENDERVERSION.md makes 5.2 LTS the shipped default.
- Why P1: `--usd-sidecar` is a documented exporter flag (`export_previz_package.py:962-964`,
  module docstring line 21-26). On the default toolchain the crash fires
  AFTER the GLB is written and BEFORE `previz.json` is dumped (dump at
  :1310), leaving an orphan GLB and a failed export — fail-closed, but the
  documented path dies on exactly the Blender the battery proved diverges.
  The fix comment in export_usd.py claims "version-proof by construction";
  the sidecar path — whose docstring says "same kwargs as
  scripts/export_usd.py, animation ON" (`:918-919`) — no longer is.
- Fix: extract the RNA filter (export_usd.py:166-173) into a shared helper
  (e.g. `blender_kit.filtered_usd_kwargs(**kw)`) and use it in BOTH
  `_export_usd_sidecar` and `blender_kit.export_usd` (see F2C-2); keep the
  NOTE-on-drop print so the parity gate's key loss is diagnosable.
- UNVERIFIED-needs-Blender: I could not run 5.2.2; the P1 rests on the
  battery's own recorded finding + code read. If 5.2.2's RNA does carry
  `export_textures`, downgrade to P2 (latent drift, no current crash).

### F2C-2 — P2: `blender_kit.export_usd` (second call site) is unfiltered and its TypeError fallback silently drops ~20 export settings

- `scripts/blender_kit/__init__.py:1052-1078` builds the same 4.5-calibrated
  dict (`export_textures=True` at :1073); `:1080-1090` catches TypeError and
  retries with ONLY `filepath/export_animation/export_cameras/export_lights`.
- Why: on a divergent Blender this silently loses `evaluation_mode='RENDER'`,
  `export_custom_properties` + `custom_properties_namespace` (the
  previz:entity carrier itself — UNVERIFIED whether the RNA defaults
  coincide), `export_uvmaps`, `export_normals`, `export_armatures`,
  `only_deform_bones`, `export_shapekeys`, `export_mesh_colors`,
  `triangulate_meshes`, etc. That is exactly the "silent quality loss"
  class the session-16 fix was written to kill, one helper away from the
  fixed file.
- Fix: same shared RNA-filter helper as F2C-1; keep the min-kwargs retry
  as last resort.

### F2C-3 — P2 (false-REJECT vs the real exporter): S3 rejects a SHOTS row whose `CAM_<sid>` CAMS_V3 row is missing, but the exporter is green in that case

- `scripts/export_preflight.py:763-768`:
  ```python
  else:
      rep.reject(
          f"S3 CAMS: shot {sid!r} has no CAMS row named '{want}' — "
          "the exporter merges cam specs by exact object name "
          "(exporter:1151). Fix: add a ('{want}', loc0, loc1, lens, ...")
  ```
- Reality: the exporter treats a CAMS_V3 row as an OPTIONAL merge —
  `cams_spec.get(obj.name)` (:1151), `meta.update(...)` only when found
  (:1152-1159); gate 11 explicitly skips static cams; no gate requires a
  spec per shot. Verified by probe `partial_cams_v3` (SHOTS S1+S2, CAMS_V3
  with only CAM_S1): `_collect_story` accepts, and no exporter gate can
  fire — yet preflight exits 3. Plausible input: a module that authors its
  static cameras directly in `build_scene` and specs only the moving ones.
  Note the adjacent-row case ("CAM_S11" present, "CAM_S1" wanted) is only a
  WARN (:750-756) — same exporter outcome, different severity, which shows
  the reject is not decoder-derived.
- Code-vs-design: the code faithfully implements DESIGN_D19 S3 ("every sid
  has a CAMS row whose name is EXACTLY CAM_<sid>"); this is a spec-vs-
  exporter defect the property test cannot see (S3 is outside the
  `_collect_story` oracle; tests/test_t10_preflight_prop.py:69-81 runs only
  s2_schema/s2_shots/s2_beats).
- Fix (design change): demote the missing-row reject to the same WARN the
  legacy path got (5-a P2-11), or reject only when the marker-bound camera
  object ALSO does not exist (that is the exporter's real gate-1 failure);
  update DESIGN_D19 S3 accordingly.

### F2C-4 — P2 (doc-lies): DESIGN_D19.3 says gate-15 files "has `fps` + `events`" (fps required); the shipped gate tolerates fps-MISSING

- Spec: `docs/DESIGN_D19_export_preflight.md:142-144` — "Gate 15 …: after
  emit_sfx_events, if `<out_dir>/sfx_events.json` exists → file has `fps` +
  `events`; every event has `name|kind` + integer `frame`; file fps ==
  scene.render.fps."
- Code: `scripts/export_previz_package.py:1200-1203` — "fps is checked for
  AGREEMENT WHEN PRESENT (a fps-MISMATCH rejects; fps-missing is tolerated
  for old-format files — review 5-a P2-3: the words, not the code, said
  'required')" and `:1242-1248` implements exactly that; preflight
  `_sfx_check_file(require_fps=False)` mirrors it (export_preflight.py:847-890).
- The REV-2 design doc was never amended after 5-a, so the "FINAL" design
  now misdescribes the shipped gate. The preflight's own docstring/header
  still sells "{fps, events} — fps required" for the SFX_EVENTS-as-path case
  only (where require_fps=True — that part matches).
- Fix: one-line design-doc patch (or make gate 15 actually require fps for
  emitted files — both real producers write it — but that is a behavior
  change, not a doc fix).

### F2C-5 — P2: vacuous pass is silent, not loud — a module with NO SHOTS/BOARD/CAMS gets a full-fat "PASS" with zero signal

- `scripts/export_preflight.py` Phase flow: S2 skips absent constants
  (`:356-358` "law 20"), S3 returns on `shots == []`/`cams is None`
  (`:681-683`, `:731-733`), B3 runs nothing when `shots` empty (`:978`),
  B5 parity on an empty story dict passes trivially (`:1090-1105`).
  Probe: a module declaring none of the story tables (e.g. scene_template.py
  shape) yields `S1=ok S2=ok S3=ok S4=ok B1=ok B2=ok B3=ok B4=ok B5=ok
  B-sfx=ok … rejections: 0 warnings: 0 / RESULT: PASS`.
- Why P2: the tool's contract is "replays the exporter's REAL consumption";
  here ~all of that replay was vacuous and nothing distinguishes "checked
  clean" from "nothing to check". An agent that passes the wrong `--module`
  (template instead of its film) gets green confidence. Law 20 makes
  vacuous CORRECT — but it should be loud.
- Fix: when zero STORY_SOURCES constants AND no SHOTS/CAMS are declared,
  emit one WARN (e.g. "S2: module declares NO story tables — preflight
  coverage is near-vacuous; verify --module") and add a `coverage` count
  to the summary/JSON (`checks` dict + write_json).

### F2C-6 — P3 (wrong diagnostics): the stale exporter line-anchor cluster (−5 drift), already flagged by review 2-a and not fixed in REV-2

Messages debug agents; these anchors point at the wrong construct today
(verified against the current file):

| Cite (export_preflight.py) | Says | Actual |
|---|---|---|
| :256 header | dispatch "1040-1053" | 1035-1048 |
| :273, :1295 | build_scene unguarded "exporter:1039" | 1034 (`ctx = mod.build_scene()`) |
| :1306 | ctx fallback "exporter:1056" | 1051 |
| :957 | cannot-bind "exporter:1124-1126" | 1118-1121 |
| :966 | unbound-marker skip "exporter:1123-1126" | `_marker_bindings` 109-112 / fail 1118-1121 |
| :971 | CAM_ prefix "exporter:1117-1129" | 1122-1124 |
| :983 | gate-3 span "exporter:1332-1334" | 1339-1340 |
| :672 | CAMS read "exporter:1134" | 1129 |
| :1102 (B4 docstring) | atmo exclusion "1100-1108" | 1095-1103 |
| :497 (LUNGE warn text) | "_collect_story:625-627" | 617-622 |
| :547 (BOARD docstring) | "(580-596)" | 578-591 |
| :1090 (B5 comment) | "decoder:586" | 581 |
| DESIGN_D19 S2 table (all rows) | e.g. DIALOG "544-547" | 539-542 (whole table −5) |
| AGENTS.md:212 | CAM_ check "exporter:1117" | 1122-1124 |

Correct ones verified: exporter:1117 (unpack), 1115 (fallback), 1151-1159,
1176 (fps stamp), 1209 (emitter call), 1245-1252, _collect_story:645, 580,
587. Fix: one mechanical pass re-anchoring to the 5-line-shifted truth (or
cite function names + grep tokens instead of raw line numbers so they rot
slower).

### F2C-7 — P3 (false-REJECT, implausible input): `RB_FALLS`/`RB_KD` declared as a bare string, and `SFX_EVENTS` as a tuple — both decode-or-are-ignored by the exporter, both reject in preflight

- `RB_FALLS="rb1"`: decoder `export_previz_package.py:627` iterates ANY
  iterable — `[str(x) if isinstance(x,str) else int(x) for x in "rb1"]`
  lands `["r","b","1"]` (accept); preflight `:502-506` rejects strings
  outright (probe: `rb_falls_bare_string` → S2 reject / decoder accept).
- `SFX_EVENTS` tuple: nothing in the exporter reads `SFX_EVENTS` at all
  (grep: only preflight + docs); preflight `:908-914` rejects a tuple.
- Why P3 only: no real module declares either shape; the reject errs
  closed. Fix if touched: allow str in the RB check to match the decoder,
  or accept any sequence in S4.

### F2C-8 — P3: `CAMS_V3=[]` + legacy `CAMS` defeats the legacy demotion (`is None` vs falsy) → false-REJECT

- `export_preflight.py:740`: `legacy = getattr(mod, "CAMS_V3", None) is None`
  but `cam_table` (:669-674) falls through `CAMS_V3 or CAMS` — an EMPTY
  CAMS_V3 selects the legacy table while `legacy` stays False, so legacy
  rows get the exact-name REJECT (:763-768) even though the exporter reads
  `CAMS_V3=[]` → green (probe `empty_cams_v3_plus_legacy_cams`).
- Fix: `legacy = not getattr(mod, "CAMS_V3", None)` to match cam_table's
  own falsy-fallthrough. Implausible combo today; one-token fix.

### F2C-9 — P3: one-shot iterables (generators) are consumed by S2, then S3 "rejects" with a lying fix-hint

- `s2_schema` iterates `CAMS_V3` to validate rows; if the constant is a
  generator, `cam_table`/S3 re-iterate an EXHAUSTED generator → "shot 'S1'
  has no CAMS row named 'CAM_S1' … Fix: add a ('CAM_S1', …) row" (probe
  `generator_cams`) — the row exists. `_collect_story` itself would accept
  (single consume). The `_list_rows_check` "consumed once" WARN exists
  (:333-336) but `_s2_cams` has no equivalent.
- Fix: `cams = list(cams)` (and `val = list(val)` in the row checkers)
  once per check phase, or warn+skip on non-re-iterables.

### F2C-10 — P3 (false-PASS on garbage): unhashable `CAMS_V3[i][0]` passes S2/B5 and TypeErrors the exporter's cam-map build

- Exporter `:1129` `cams_spec = {c[0]: c for c in (getattr(mod, "CAMS_V3",
  None) or [])}` requires hashable field 0; `_collect_story` does
  `str(c[0])` (accept anything); S2 `_s2_cams` never inspects field 0
  (probe `unhashable_cam_name`: S2 accept, decoder accept, exporter
  `TypeError: unhashable type: 'list'` at the cam map). The B5 parity
  guard mirrors only `_collect_story`, so it cannot catch this either.
- Why P3: garbage input only. Fix: add "field 0 must be hashable" to
  `_s2_cams` (a one-line `try: hash(name)` check), which also future-proofs
  S3's `exact_names` set.

### F2C-11 — P3 (test hygiene): t10 tier-2 leaks fixture bytecode into `scripts/__pycache__/` and an mkdtemp OUT dir

- `tests/test_t10_export.py:160-165` removes only the fixture `.py` files;
  the exporter imports them by name (`importlib.import_module`), so
  `scripts/__pycache__/t10_fixture_*.pyc` survives the `finally` (gitignored,
  but a stale-bytecode landmine for a later same-name fixture, and repo
  hygiene). Also `:29` `OUT = … else tempfile.mkdtemp(prefix="t10_")` is
  never removed on the default path.
- Fix: `finally` should also `shutil.rmtree(scripts/__pycache__, ignore_errors=True)`
  filtered by fixture prefix (or run with `sys.dont_write_bytecode`), and
  mkdtemp the default OUT inside the same try/finally.

### F2C-12 — P3 (message overstates / micro-strictness notes, bundled)

- B1 zero-objects reject (`:1311-1314`): "the exporter would package an
  empty GLB" — not true; exporter gate 1 (no cameras) and gate 6 (no
  actions) would REJECT the export (`export_previz_package.py:1322-1327,
  1383-1385`). The preflight is right to stop early; the message should say
  the exporter's gates would reject, not that it would ship an empty GLB.
- `f0=True` (bool frame): preflight rejects (`_is_frame_num` bool-exclusion,
  `:170-181`); the exporter actually accepts `True` (hash/`==` equal to 1,
  probe `shots_f0_bool`). Absurd input; the bool exclusion is the right
  call — noting for the parity ledger.
- S4 window rule is applied to the EMITTED file in Phase B
  (`:1131-1133` → `_sfx_check_events` window reject) while exporter gate 15
  has no window rule — preflight-stricter-than-exporter on the emitted
  stream, design-mandated only for the DECLARED stream (D19.1 S4). No real
  module trips it (tdawn 85..1009, ferry 85/721/913, green 85/445/1009 all
  in-window); docstring "mirrors gate 15" (:1110) is slightly inaccurate —
  it is S4+gate-15 hybrid.
- t10.3's assertion `("name" in r3p.stdout and ("kind" in r3p.stdout))`
  (`tests/test_t10_export.py:222-223`) is near-vacuous (both words appear in
  unrelated stdout); the exporter-side assertion is the strong one. Tighten
  to `"lacks both 'name' and 'kind'"`.

---

## Checked and CLEAN

- **S1 dispatch parity** (`export_preflight.py:259-315` vs exporter
  1035-1048): branch test verbatim incl. bool-is-int quirk; bare→`bind({})`,
  sentinel→`bind({}, start_frame=1, n_frames=None)`; signature-failure and
  `animate=None` both reject (exporter would crash on both). Probes: tdawn
  signature (`start_frame=1, n_frames=None, with_crowd=None`) → sentinel
  branch, binds; template signature (`*, start_frame=1, n_frames=24`) →
  bare branch, binds; required-`n_frames` signature binds the sentinel.
- **S2 arity/cast parity vs `_collect_story` (526-657)**: every row
  minimum = the decoder's max index + 1 (DIALOG 2, KNOCKDOWNS 4, MUZZLE 3,
  JEEP 2, _V3_SEG 4, SHOTS 4, BOARD MAIN 6); ≥n semantics (extra fields
  accepted — probes); None-tolerance exactly per consumer: CAMS vecs
  `none_ok=False` (:621-623 — decoder has no None-guard, whole-collector
  TypeError), BOARD seat_local `none_ok=True` (:583-586 — decoder
  None-guards); bool/str-number castability matches `int()`/`float()`
  semantics ("2.5" accepted for KNOCKDOWNS t_hit both sides; "10.5" for
  DIALOG onset rejected both sides — `int("10.5")` raises).
- **BOARD per-entry parity**: every decoder drop case maps to an S2 reject
  (entry<2, MAIN<6, int/float field casts, EXTRA truthy-with-bad-[0],
  EXTRA=5 int subscript, str-row MAIN) — pinned by tier-1 variants;
  falsy-EXTRA→0.0 both sides; property suite 100/100 green in this sandbox.
- **RUN_PARAMS / MOTION_POLICY / FLATNESS_POLICY / RB_* / scalars /
  HERO_MODE**: dict-of-dicts, None-value crash, `.get()` dict requirement,
  flat-list str|int, scalar float/int casts, `str(hm)` cannot-fail — all
  match; LUNGE silent-drop → WARN is the documented agreed exception and
  the property test pins it in both directions.
- **SHOTS fallback** `getattr(SHOTS_V3) or getattr(SHOTS, [])` replicated
  verbatim (:663-666 = exporter:1115); `_is_frame_num` integral-float
  tolerance matches marker-key hash equality and `f1+1` arithmetic;
  dict-rows and string-rows rejected consistently with the unpack crash.
- **BEATS**: shape-only WARN, no timing rules; real film shapes
  (scene_terminal_dawn.py:126-139, scene_last_ferry.py:124-139,
  scene_green_light.py:118-128, tgreen_contract.py:89-99 — all
  `(id, t_seconds, label)`) pass silently; `(label, shot, frame)` and
  short rows warn with the correct canonical-shape text; never rejects.
  (The t==(f0-1)/FPS opener rule false-reject hazard named in REV-2 fix 2
  is genuinely absent.)
- **S4**: {name|kind}+int-frame (bool excluded) matches gate 15 exactly;
  unknown-name vocabulary is WARN-only and never rejects; SFX_EVENTS
  as-path enforces {fps, events}; gate-15 mirror (emitted file) tolerates
  fps-missing exactly like exporter:1242-1253; real film emitters
  (tdawn:646-671, ferry:544-555, green:544-553) all conform and sit inside
  shot windows.
- **B1/B2**: ctx-dict + `ctx.get("scene") or bpy.context.scene` fallback
  mirrored (exporter:1051); empty-scene reject; fps-agreement reject;
  fps_base==1.0 reject is design-mandated and the exporter genuinely has
  zero fps_base references (grep verified).
- **B3**: marker-at-f0 / camera-bound / CAM_ prefix reject set mirrors
  exporter 1113-1124; exact-match demoted to WARN; marker NAMES
  unconstrained (fix 1 honored); span gate from the SCENE (exporter
  1339-1340), never a module constant.
- **B4**: rejection set = shot cameras + `CAM_<sid>` objects + `Aim.*` +
  CAST dict-of-dicts roots; atmo exemption uses the REAL
  `atmo_objects` (blender_kit:876-909) and KIT_ANNOT_*; `render_hidden_objects`
  self-updates the view layer (blender_kit:932).
- **B5**: parity guard runs in Phase B with real `float(fps)`/`int(frame_start)`
  (fix 6); differential attribution restores every attr via `finally`
  (re-read twice, no leak path); naming message carries BOTH the scene-bug
  and schema-gap classes (fix 7); BOARD key-set parity uses the `str()`
  cast (:1090-1105); B5 runs BEFORE the sfx emitter (5-a P2-9 ordering).
- **b_sfx_emitter**: temp-dir `try/finally shutil.rmtree` (5-a P2-9 leak
  fixed); emitter-raise reject ("the exporter calls it unguarded" — true,
  :1209); wrote-nothing → WARN parity with gate 15:1257-1260.
- **B6**: opt-in, skips on earlier rejections / missing animate, mirrors
  the dispatch shapes; default-off rationale documented.
- **Fail-closed plumbing**: internal error → traceback + exit 3
  (:1363-1372); import failure and missing file both reject with traceback
  tail (:1246-1259); Phase-S reject short-circuits Phase B (build never
  runs on a rejected module) and still exits 3; `--skip-build` prints
  "necessary, not sufficient" in checks; WARN cap 8 in the summary.
- **Blender-side helpers**: `script_argv` `--` handling (blender_kit:272-275);
  `_import_scene_file` path-dedupe (278-290, matches the design's cite);
  `bpy` imported only in-Blender paths.
- **Exporter gate 15 / gate 4 (D19.3)**: first-bad-event break with index
  named; `n_sfx` counted after the isinstance gate (5-a P2-10); guarded
  fps cast; gate-4 strengthening fires only on declared-non-empty BOARD
  with 100% decode failure (partial boards keep NOTEs) — matches design.
- **Real film modules are S2/S3/S4-clean**: tdawn/lferry/green declare
  full CAM_S1..S12 maps (no partial-CAMS trip), contiguous SHOTS 1..1080,
  conforming emitters; template lane is vacuous (see F2C-5 for the
  loudness gap).
- **t10 tier-1**: ran green here (100 checks, 0 failed, milliseconds) —
  pure-python stubbing correct (bpy/blender_kit stubbed BEFORE kit import;
  build_sfx fallback), exception-during-S2 counts as reject (fail-closed),
  SHOTS handled outside the decoder oracle with an honest comment.
- **t10 tier-2 (code read)**: fixture written into `scripts/` under a non-
  escape name so `_latest_scene_module` drift-gate stays out of the way
  (critique fix 4); `--python-use-system-env` + PYTHONPATH + cwd=REPO
  subprocess env; try/finally wraps ALL cases; 19 checks as advertised;
  fixture satisfies markers/span/gate-6/gate-5/gate-15 ground truth.
- **Docs**: AGENTS.md ship-and-verify loop, marker-name law, sfx contract
  and BEATS law all present and (except the line-anchor nit in F2C-6)
  accurate; USABILITY_S16_session16.md records the tier-2 wall time (7.5 s).

## UNVERIFIED-needs-Blender

1. **F2C-1's crash itself** — `bpy.ops.wm.usd_export(export_textures=True)`
   TypeError on 5.2.2 (evidence is in-repo; needs one `blrun --background
   --python` run of `export_previz_package --usd-sidecar` on 5.2.2 to
   confirm).
2. **Exit-code propagation through the test harness** — that Blender
   (`--python-exit-code 1`) surfaces the preflight's `sys.exit(3)` as
   returncode 3 (t10.3/5/6/7 assert it; cannot execute Blender here; the
   session-16 worklog claims the tier ran green).
3. **blender_kit.export_usd fallback semantics** — whether the RNA defaults
   for `export_custom_properties`/`custom_properties_namespace`/`evaluation_mode`
   coincide with the calibrated values (decides whether F2C-2's silent
   fallback loses the previz:entity carrier or only perf/quality knobs).
4. **`bpy.ops.wm.usd_export.get_rna_type().properties.keys()`** behavior on
   the oldest supported Blender (AttributeError inside the try would
   bypass the TypeError fallback and crash export_usd.py; kit targets
   4.5+/5.2 so likely fine).
5. **B4 sweep on a real built scene** — depsgraph freshness and
   `visible_camera` reads were verified by reading blender_kit:912-934 only.
6. **read_factory_settings(use_empty=True) then build_scene** under a
   module with import-time bpy side effects (preflight wipes them, the
   exporter would not — no known module does this).

## Summary counts

| Severity | IDs |
|---|---|
| P0 | none |
| P1 | F2C-1 (UNVERIFIED-needs-Blender) |
| P2 | F2C-2, F2C-3, F2C-4, F2C-5 |
| P3 | F2C-6 … F2C-12 |

The D19 core (S2 decoder-parity, B5 differential attribution, gate 15/4
hardenings, both test tiers) is solid — the property suite passes and every
hunt category (arity, None-tolerance, CAM_ prefix, BEATS shapes, atmo/sfx
exemptions) checked out against the real decoders and real film modules.
The residual risk concentrates in the USD sidecar's unfixed twin of the
RNA-kwarg drift (F2C-1/2) and the S3 rule that is stricter than the
exporter it guards (F2C-3).
