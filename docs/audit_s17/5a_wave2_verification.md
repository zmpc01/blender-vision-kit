# 5-a — Wave-2 VERIFICATION audit of the session-17 fix waves

Repo: /home/z/repos/blender-vision-kit @ d882d59 (main). Auditor: Task 5-a
(fresh context, adversarial mandate). Scope: everything in `49584e7..HEAD`
except the two film-lane doc commits (49584e7, a7beb1a). Method: full reads
of the 8 highest-risk fix sites + the three new suites + the wave-1 audit
docs (2a–2e); git-archaeology against `49584e7` for every "regression vs
old behavior" claim; pure-python suites re-run in this sandbox
(test_s17_infra 18/18, test_t10_preflight_prop 124/124 — both green).
Blender suites not run per brief (battery 29/29 already recorded); items
needing Blender are tagged UNVERIFIED-needs-Blender.

Severity: P0 crash/data-loss/silent-wrong-render on a documented path ·
P1 wrong result on plausible input / fail-open gate · P2 friction /
incomplete fix / stale claims · P3 nit.

**Bottom line:** the session-17 fix waves are substantially real — the 8
spot-audited mechanisms are mathematically correct at their core and the
three new suites contain no vacuous assertions. What the waves BROKE or
MISSED concentrates in one pattern: **each fix landed on its main path and
its twins were missed** (F2B-5's finite gate, F2B-8's basis-delta rebase,
F2B-24's bare-animate dispatch), plus one true regression introduced by the
seat_at rewrite (world scale forced to 1). No P0 found.

---

## Findings

### F5A-1 · P2 — F2B-5 (NaN gate) closure is INCOMPLETE: the audit's own named example `snap_z.target_z` still accepts NaN/Infinity silently

- **File**: `scripts/apply_patch.py:484` (`params["target_z"]` read raw);
  also `:227-231` (duplicate_object `location/rotation_deg/scale`), `:237`
  (set_camera_location), `:243` (`lens_mm`), `:256-268` (set_camera_dof
  `focus_distance`/`aperture_fstop`), `:327` (render_viewport `lens`),
  `:333` (`custom_loc`), `:357` (set_light_color `color`);
  `scripts/placement_lib.py:1420-1445` (no finite check in `snap_z` either);
  op layer also passes `seat_at.offset` (`:467`), `place_on.clearance/inset`
  (`:432/:436`) unfiltered.
- **Evidence**: `_finite_check` fires only inside `_require`
  (apply_patch.py:131). Every handler that reads `params[...]` /
  `params.get(...)` directly bypasses it. Chain for the cited example:
  `--patch-json '{"op":"snap_z","id":"X","target_z":NaN}'` →
  `_apply_snap_z` → `PL.snap_z(obj, nan)` → `_apply_translation(obj,
  nan-cur)` → `abs(nan) < 1e-12` is **False** → `_world_delta_to_local`
  returns (0,0,nan) → `obj.location += (0,0,nan)` → NaN world transform,
  `report["result_z"] = nan`, exit 0. Exactly the silent-corruption class
  F2B-5 was filed for — 2b's own excerpt named `snap_z.target_z`.
- **Why the suite didn't catch it**: test_s17_wave_a §5 exercises ONLY the
  `_require` path (`location`, `energy`) — the green check creates the
  impression F2B-5 is closed repo-wide.
- **Behavior-change question from the brief (answered)**: `_require`'s
  `expected_type=list` (line 127) rejects a tuple BEFORE `_finite_check`
  runs (line 131), and `_finite_check` itself does handle tuples
  (`isinstance(val, (list, tuple))`, line 108). This is NOT a behavior
  change: `expected_type=list` predates session-17 (present verbatim in
  the 2b excerpts of the pre-fix file) and JSON cannot carry tuples —
  only python-level callers could ever pass one, and they were rejected
  before s17 too. Nested lists are NOT recursed by `_finite_check`, but no
  documented param carries a nested numeric list, so that is latent, not
  live.
- **Fix**: route every direct numeric read through the shared validator
  (e.g. `_finite_check("snap_z", "target_z", params["target_z"])` at the
  top of each of the 8 handlers; validate `offset`/`clearance`/`inset` in
  the op layer) and extend test_s17_wave_a §5 to iterate ALL numeric
  params per op (the same AST sweep the parity test uses can enumerate
  them).

### F5A-2 · P2 — `seat_at(align=True)` silently forces the mover's WORLD SCALE to 1 (regression vs pre-session-17)

- **File**: `scripts/placement_lib.py:1285-1287`:
  ```python
  R4 = seat_mw.to_euler().to_matrix().to_4x4()
  obj.matrix_world = Matrix.Translation(obj.matrix_world.translation) @ R4
  ```
- **Why it is a regression**: the pre-fix code (verified at
  `git 49584e7:scripts/placement_lib.py`, seat_at body) wrote
  `obj.rotation_euler = seat_mw.to_euler()` — a ROTATION-only write; scale
  was untouched. The new absolute world-matrix write replaces the whole
  linear part with a pure rotation, so any mover whose world scale ≠ 1
  (vendor/UAL imports with baked-in scale, or any mover under a scaled
  parent chain — the pre-fix code preserved world scale in both cases) is
  silently rescaled to world-uniform-size during seating. The report
  carries no key; the post-contact audit can still read TOUCHING (the
  contact solve runs after the rescale), so nothing flags it.
- **Plausibility**: kit-created prims bake scale into mesh data (scale 1),
  so the kit's own tests cannot see this — but the documented seat_at
  consumer is "figure onto Jeep.SeatL" where figures are exactly the
  imported/parented asset class.
- **Correct parts (verified, for the record)**: the world-rotation
  ABSOLUTE semantics are right (the wave-A note about the stacked-yaw
  false start matches t9 S1b); the anchor translation afterwards is
  computed from the POST-align bbox (`_aabb` after `view_layer.update()`),
  so `R4`'s rotate-about-origin composition + translation reproduces the
  old landing semantics EXACTLY for the offset case — `offset` is applied
  in the EMPTY's space (`target_loc = seat_mw @ Vector(offset)`, line
  1290) AFTER align, matching the docstring; reference validation
  (F2B-6) and the 'centroid' implementation are correct.
- **Fix**: preserve scale in the rotation write, e.g.
  `s = obj.matrix_world.to_scale()` then
  `obj.matrix_world = Translation(t) @ R4 @ Matrix.Diagonal((*s, 1.0))`
  (and set `report["world_scale_preserved"]` when `s != (1,1,1)`); or
  decompose/recompose. Add a wave-a-style test with a 0.5-scaled mover
  asserting `matrix_world.to_scale()` is unchanged by seat_at.

### F5A-3 · P2 — F2B-8 fix incomplete: `move_to` still rebases BASIS-space fcurves by the WORLD delta

- **File**: `scripts/placement_lib.py:1396-1401`:
  ```python
  obj.matrix_world = Matrix.Translation(delta) @ obj.matrix_world   # world write
  ...
  n, chans = _rebase_location_keys(obj, delta)                      # delta is WORLD
  ```
- **Why**: the s17 fix converted `_apply_translation` and `seat_at` to
  basis-space rebase deltas (`d_local`, and
  `matrix_basis.translation - _basis_before` respectively) with the
  comment "the fcurves are basis-space" — but `move_to` (the site that
  pioneered the world-space write in an earlier session) still passes the
  world `delta`. For a PARENTED animated mover with
  `override='keyframe'` under a rotated/scaled parent, every location
  keyframe is shifted by the wrong vector — later keys no longer preserve
  the relative placement, the exact usability-R1 mug-drift class the
  rebase was written to kill. Unparented objects are unaffected (A = I),
  which is why the battery stays green.
- **Fix**: in `move_to`, capture `before = obj.matrix_basis.translation`
  before the write and rebase with
  `obj.matrix_basis.translation - before` (the seat_at pattern verbatim).

### F5A-4 · P2 — F2B-24 fixed 2 of 3 bare-animate dispatch sites: `viewport_capture.py --scene` still TypeErrors on preflight-legal modules

- **File**: `scripts/viewport_capture.py:517-518`:
  ```python
  if hasattr(mod, "animate"):
      mod.animate(ctx, start_frame=1, n_frames=args.frames)
  ```
- **Why**: F2B-24's whole premise is that the exporter contract accepts a
  bare `def animate(ctx)` (preflight S1 validates the bare branch as
  PASSING), and apply_patch got `_animate_scene_module` (signature-bind →
  bare fallback). `scene_schema.py` got the twin too (see F5A-5).
  `viewport_capture.py` main() was missed: the same module that passes
  `export_preflight` crashes `vc --scene <module>` with
  `TypeError: animate() takes 1 positional argument but 3 were given`
  before any capture. UNVERIFIED-needs-Blender only in the trivial sense
  (the dispatch logic itself is pure python and proven by
  test_s17_wave_b §10 for the apply_patch twin).
- **Fix**: import and reuse `apply_patch._animate_scene_module` (it takes
  `(mod, ctx, frames)`), or copy the 8-line bind/fallback.

### F5A-5 · P3 — scene_schema's F2B-24 twin retries bare-animate after an IN-BODY TypeError (double execution of partial side effects)

- **File**: `scripts/scene_schema.py:319-325`:
  ```python
  try:
      _inspect.signature(mod.animate).bind(ctx, start_frame=1, n_frames=args.frames)
      mod.animate(ctx, start_frame=1, n_frames=args.frames)   # CALL inside the try
  except TypeError:
      mod.animate(ctx)
  ```
- **Why**: apply_patch's `_animate_scene_module` deliberately keeps the
  CALL outside the bind-try ("A TypeError raised INSIDE animate still
  propagates loudly") and test_s17_wave_b §10c pins exactly that
  (s17_10c). The scene_schema twin put the call inside the try: an
  animate() that raises TypeError mid-body (internal bug, bad key) is
  swallowed, then re-run via the bare branch — any side effects before
  the raise (keyframe_insert, crowd bakes, file writes) execute TWICE.
  Divergent twins for the same contract, and the suite only pins the
  apply_patch side.
- **Fix**: split bind from call exactly like
  `apply_patch._animate_scene_module` (or import it).

### F5A-6 · P3 — render_angle's marker restore swallows failures silently; the finally order is only safe under an UNVERIFIED reading of Blender's marker.camera RNA

- **File**: `scripts/viewport_capture.py:302-315`.
- **Verified-correct core**: sweep → `scene.camera = cam` re-assert AFTER
  the sweep (matches the kit's own observed mutation note,
  tdawn_flowstrip.py:61-63) — the setup order is right under either
  reading; restore is idempotent and ReferenceError-guarded; cleanup runs
  regardless; a multi-angle loop cannot race (single-threaded: each
  render_angle fully restores before the next sweeps — no marker-carryover
  found).
- **Issue (a)**: `restore_markers()` is wrapped in `except Exception:
  pass` (lines 310-313). If a restore write fails (marker RNA gone,
  camera object freed mid-run), ALL swept markers stay unbound and the
  failure is silent — subsequent renders use scene.camera, the session
  looks healthy, and a later `--save-blend` persists the destroyed shot
  cut (data loss on the canonical state carrier). The comment says the
  swallow protects the render's error — it should still PRINT.
- **Issue (b)**: the finally restores `scene.camera` BEFORE re-binding
  markers. Blender's `TimelineMarker.camera` RNA write mutating
  `scene.camera` is claimed by the kit's own flowstrip notes (clearing
  observed to "fall back to the last shot cam") but was never
  demonstrated for RE-binding; standard RNA has no such write-back, and
  under that reading the current order is fine. Under the flowstrip
  reading, re-binding leaves `scene.camera` pointing at the last restored
  marker cam after render_angle returns — a state leak into the next op
  in an apply_patch chain. One probe settles it (UNVERIFIED-needs-Blender:
  bind a marker cam ≠ scene.camera, call render_angle, assert
  `scene.camera == orig` after).
- **Fix**: print on restore failure; re-assert `scene.camera =
  orig_camera` AFTER `restore_markers()` (free, and correct under both
  readings); add the probe to test_s17_wave_a §1.

### F5A-7 · P3 — F2C-6 (stale exporter line anchors) got WORSE, not fixed: the remaining cites now drift by −24..−29 lines

- **File**: `scripts/export_preflight.py:271` ("1040-1053" → actual
  dispatch ~1064-1077), `:288` and `:1478` ("exporter:1039" →
  `ctx = mod.build_scene()` is at exporter:1063), `:712`
  ("exporter:1134" → `cams_spec` at exporter:1158), `:825`
  ("exporter:1151-1159" → the merge loop now ~1158+), `:1087`
  ("1100-1108"), `:1184` ("decoder:586"), `:1485/:1490`
  ("exporter:1056").
- **Why**: the wave-C sidecar edits added ~29 lines above the dispatch,
  shifting every anchor the F2C-6 table listed. Commit 6400af1 ("line
  anchors re-verified by grep") re-verified exactly FOUR cites
  (`exporter:1205 int(fps)` ✓, `_marker_bindings 109-112` ✓,
  `AGENTS.md:212 → exporter:1151-1153` ✓ verified correct at tip,
  B3-mirror span) and left the rest. The preflight's messages now point
  debuggers ~25 lines off in both directions.
- **Fix**: the F2C-6 original recommendation stands — cite function names
  + grep tokens, not raw line numbers; one mechanical pass over the
  remaining ~10 cites.

### F5A-8 · P3 — F2E-19 half-open: the export lane still writes no metadata.json

- **File**: `scripts/export_previz_package.py` (grep `metadata.json` → 0
  hits). The `viewer-three.html` dead pointer half was fixed
  (viewer/index.html:132 now says the lane is *planned*, accurate).
  Pairing the viewer with an export package still loses the whole info
  panel ("No metadata.json found" — graceful, but the render-lane/export
  -lane asymmetry stands).
- **Fix**: emit a minimal metadata.json from the package writer, or teach
  index.html to render previz.json's provenance block (original 2-e
  suggestion, unchanged).

### F5A-9 · P3 — F2B-29 residue: the viewport-quality atmo fallback still matches by NAME (the fix added a count-log, not per-name logging or a volume-only restriction)

- **File**: `scripts/blender_kit/__init__.py:736-745` —
  `if ob.get("kit_atmo") or _atmo.search(ob.name): ob.hide_render = True`
  with only `hid N atmosphere object(s)` printed (count, never names).
  A prop named `Fog_Machine` is still silently render-hidden under
  `--quality viewport`. NOTE: the audit's secondary sting (schema said
  `visible: true`) is now RESOLVED as a side effect of F2B-20b (schema
  exports `hide_render`), which lowers this to P3-residue.
- **Fix**: original suggestion stands — restrict to volume-only materials
  (the `atmo_objects` triple-check at :876-909 exists) or log each hidden
  NAME.

### F5A-10 · P3 — F2A-12 half-open: blrun still leaks BLRUN_OUT/BLRUN_ERR on the signal path

- **File**: `scripts/blrun.sh:187-204` (`cleanup` removes only
  `WARM_SCRIPT` — the F2E-17 half) vs `:285-286` (both mktemp logs created
  AFTER the trap is installed) and `:307` (rm on the NORMAL path only).
  SIGINT/TERM/HUP between line 285 and 307 leaks both logs. The
  warm-cache temp script (the other half of F2A-12) IS fixed and
  `--warm-cache` still works (verified: WARM_SCRIPT created after the
  trap, rm'd in cleanup; fixed render path documented deliberate).
- **Fix**: add `rm -f "$BLRUN_OUT" "$BLRUN_ERR" 2>/dev/null || true` to
  `cleanup()` (guarded — the vars are empty before 285).

---

## Cross-fix interactions (checked; one class, no new breaks)

- **F2B-22 (DoF guard) × F2B-24 (bare-animate dispatch), both in
  `main()`**: compose correctly — shortcut-only refuses before any scene
  work (apply_patch.py:1482-1488), `--scene` builds via
  `_animate_scene_module` (:1514), the DoF shortcut appends AFTER the
  patch's mutations. No ordering hole.
- **F2B-20/21 (schema additive fields + depsgraph freshness) ×
  export_preflight / manifest_diff**: **no reader of the changed shapes**.
  manifest_diff reads look_manifest.json rows (id/type/centroid —
  untouched); export_preflight reads module constants and the BUILT
  scene, never scene_schema output. The exporter's own `schema_version`
  ("2.1", exporter:1197) and the USD carrier's ("1.0") are unrelated to
  scene_schema's "1.1". The world-shape change (`background_color` →
  `color_source`/`background_strength`) has no in-repo consumer of the
  old key (exporter/previz_usd_hook compute their own). **Explicit
  result: no issue.**
- **F2B-10 `_doc_keys` tokenizer × PARAM_DOCS**: verified the depth-0
  comma splitter against the trickiest entries (render_viewport's legacy
  alias, seat_at's `offset?:[dx,dy,dz] (empty's local space)`,
  physics_settle's parenthesized refuse-note) — no phantom keys; the AST
  parity test enforces it bidirectionally.
- **F-TD3 marker sweep × look.py label aiming / annotate**: labels are
  aimed per-angle BEFORE render_angle; the sweep touches only
  timeline_markers + scene.camera. No interaction.
- **F2E-17 warm-script cleanup × blrun trap ordering**: WARM_SCRIPT is
  assigned after the trap is installed and read by cleanup at exit —
  correct.
- **The one real interaction class** is the pattern of F5A-1/3/4
  themselves: each wave-B/C fix landed on its flagship call site while a
  sibling call site of the SAME contract kept the old behavior (finite
  gate, basis-delta rebase, bare-animate dispatch). The contract tests
  pin the flagship only.

## Test honesty (the three new suites)

**No vacuous assertions found.** Specifically checked for: tautologies,
wrong-key reads, checks that cannot fail, except-branches that pass
vacuously. Every check reads REAL return keys (e.g. s17_15e reads
`schema["world"]["color_source"]["type"]` — the key `_world_to_dict`
actually writes; s17_6a reads `rep["reference"]`/`reference_requested` —
the keys snap_z writes; s17_9c asserts a stdout substring the spy
plants). The suite also does real differential work where it matters
(s17_1b renders panel-vs-marker-cam and diffs pixels; s17_7 builds a
genuinely erroring skinned pair). Honest self-labeling exists too
(test_s17_wave_a §1 comment explicitly declares the F2A-9 leak "unfixed
by design in this wave"). Two nits, neither a false pass in practice:

1. test_s17_wave_a §5 covers ONLY the `_require` finite path — green
   while 8+ handlers remain unguarded (this is the F5A-1 blind spot, a
   coverage gap, not a tautology).
2. test_s17_wave_b s17_12c's `except ImportError → pass` branch would be
   a vacuous pass if blender_kit were absent — unreachable in the blrun
   harness (PYTHONPATH guarantees the import), so latent only.

Both pure-python suites re-ran green in this sandbox: test_s17_infra
18/18, test_t10_preflight_prop 124/124.

## Open-P3 residue — the definitive list (verified in situ)

Closed P3s verified: F2A-11, F2A-13, F2A-15, F2B-26 (mostly — the
scene_schema `type(obj.location)` obscurity remains, works), F2B-27,
F2B-28, F2B-30, F2C-8, F2C-9, F2C-10, F2C-11, F2C-12, F2D-13 (verified
correct at tip), F2D-14, F2D-15, F2D-16, F2D-17 (file deleted), F2D-18
(second header relabeled "historical"), F2E-1, F2E-7, F2E-8 (refuses on
shared-symlink), F2E-12 (sha256 pinned), F2E-13, F2E-17, F2E-18, F2E-22,
F2E-23.

**OPEN (unfixed in code):**

| ID | One-liner | Evidence |
|---|---|---|
| F2A-9 | render_angle leaks global render/shading state (documented open by design; test comment admits it) | viewport_capture.py:258-296; test_s17_wave_a.py:83-85 |
| F2A-10 | FLAG_CAP comment says "P0 first, then largest overlap"; code is alphabetical-after-P0 | look.py:328-336 |
| F2A-14 | annotation grid hardcodes z_floor = 0.0 | annotate.py:211 |
| F2A-16 | angle→location math still triplicated | look.py `_camera_loc_for_angle`, viewport_capture.py:247-252, :555-558 |
| F2A-17 | stitch resizes ignoring aspect (vc:407); --no-grid multi-angle creates a dir named like a file (vc:568-570) | viewport_capture.py |
| F2A-18 | no end-to-end blrun exit-code test (v1_look test_4 still invokes raw blender) | tests/test_v1_look.py:135-145 |
| F2C-6 | stale exporter/decoder line anchors, now −24..−29 off (see F5A-7) | export_preflight.py:271,288,712,825,1087,1184,1485 |
| F2C-7 (half) | SFX_EVENTS tuple still rejected (stricter than a decoder that never reads it); the RB_FALLS bare-string half IS fixed | export_preflight.py:978-985 vs :514-530 |
| F2E-20 | t6-style `BLENDER_BIN or sys.argv[0]` fragile fallbacks; suite naming drift; usd SKIP counted as PASS | tests/test_t6_add_ops.py:346 |
| F2E-21 | blrun traceback gate patterns still unanchored (false-close on honest output; escape hatch exists) | blrun.sh:301-306 |

**PARTIAL (see F5A-8/9/10 + F2B-29 note above):** F2A-12, F2E-19, F2B-29.

**Dispositioned upstream (documented, not fixable here):** F2E-5 (P1),
F2E-15, F2E-16 — all three written up in docs/FINDINGS_upstream.md with
line refs; the sync_shared port-direction note (F2E-14) landed in
HANDOFF.md:33-34. Verified.

## Anything else the wave-1 auditors missed (new-bug sweep of the biggest touched files)

Beyond F5A-1..6 (which are themselves in this category — incomplete-fix
and regression classes): scene_schema.py, daemonize.py, chunked_dl.sh,
suite_runner.sh, export_usd.py, blender_kit.filter_rna_kwargs, and the
install.sh wave-D edits were read in full. Additional observations that
did NOT rise to findings:

- `filter_rna_kwargs`'s docstring says "the caller's own TypeError retry
  remains the fallback" — true only for export_usd.py:172-182;
  blender_kit.export_usd dropped its retry (deliberately, F2C-2) and the
  sidecar never had one. On any Blender where `get_rna_type()` raises
  while the op exists (not a reachable state), blender_kit.export_usd
  would crash where the pre-s17 code degraded gracefully. Doc-lie only;
  no reachable failure path found.
- render_daemon `--first-chunk` boundary honesty: verified the wipe
  window == the re-render window exactly (per/ceil arithmetic, `f_start >
  f_end` break, counted_range disclosure). Residual nits only: a resume
  with a CHANGED `--chunks` value re-wipes overlap frames of the old
  chunking (honest per counted_range, surprising to operators), and
  `--first-chunk >= chunks` produces an inverted `counted_range` with
  frames_done=0 (honest-but-odd). Not filed.
- chunked_dl.sh rewrite, daemonize.py, suite_runner enumeration: clean.
- Hygiene note (not a code finding): the working tree carries an
  untracked stray directory `out=output/` (containing a file `b4`) —
  shell-quoting debris from an earlier session; safe to delete, does not
  affect any suite (output/ is gitignored, and this sibling is not).

## UNVERIFIED-needs-Blender (this audit)

1. F5A-6(b): whether re-binding `marker.camera` mutates `scene.camera`
   (one render_angle probe settles the finally-order question).
2. F5A-2's blast radius on a real imported figure (the matrix algebra is
   static-verified; a 0.5-scale mover seat_at would confirm).
3. F5A-4's crash on a real bare-animate module through `vc --scene`
   (dispatch logic proven pure-python on the apply_patch twin).

## Summary

| Severity | IDs |
|---|---|
| P0 | none found |
| P1 | none found (F5A-2 is the closest; held at P2 because kit-created movers are scale-1) |
| P2 | F5A-1, F5A-2, F5A-3, F5A-4 |
| P3 | F5A-5, F5A-6, F5A-7, F5A-8, F5A-9, F5A-10 |

**Next actions (ordered by value):**
1. Close the twins: finite-gate the 8 unguarded handlers (F5A-1), basis-
   delta move_to rebase (F5A-3), reuse `_animate_scene_module` in
   viewport_capture (F5A-4) — each is a ≤10-line change plus one suite
   section.
2. Fix seat_at's scale preservation (F5A-2) before the next vendor-asset
   lane.
3. One mechanical anchor pass (F5A-7) + the three one-line P3s (F5A-6
   print/re-assert, F5A-10 cleanup rm, F5A-5 bind/call split).
