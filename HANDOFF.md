# HANDOFF.md — blender-vision-kit (immediate next-session scope)

> Session close: 2026-10-04 (session 7). M6 D16 semantic mesh labeling
> IMPLEMENTED + dogfooded end-to-end (user's imported-asset use case,
> incl. welded continuous geometry via the region cut). Success
> criterion MET (blind sub-agent test). PLAN.md = long-horizon tracker.

## State at handoff

- Repo: https://github.com/zmpc01/blender-vision-kit (main). GitLab
  mirror gitlab.com/ansgareutychisO/blender-vision-kit — **BEHIND at
  session-7 close: the stored config token 401s and the real PAT was
  not recoverable in this session's context (sync tarballs sanitize
  credentials). Next session: supply the GitLab PAT, set
  `git remote set-url gitlab https://ansgareutychisO:<PAT>@gitlab.com/...`
  and push main (never force). GitHub = source of truth. NEVER force
  push.**
- SCOPE DOCTRINE (binding, owner-ruled): this kit is FOR vision-native
  agents ONLY. No VLM bridges, no ascii packs. Sub-agents: NON-VISUAL
  work only. The principal makes every visual verdict.
- Toolchain: NOT committed. Fresh sandbox: `bash install.sh` in
  FOREGROUND (harness reaps background processes). MemAvailable guard +
  honest Cycles verify + BLENDER_BIN override all in place.
- Regression battery (ALL GREEN at close): test_kit_scope,
  test_v1_look 27, test_v2_motion 27, test_v3_edges 20,
  test_v4_colorsync 29, **test_v5_labeling 58 checks (NEW — D16)**,
  t1–t6, t8 8/8, t9 chaos ALL PASS. t8/t9 need `-- --output
  output/tests/<t>`.

## Session-7 kit changes (evidence: docs/USABILITY_D16_dogfood.md)

1. **`label_objects` op** (semantic_lib.py): kit_label/kit_label_conf
   props; opt-in `rename:true` with two-phase rename + whole-batch
   collision simulation (deterministic `_2/_3` suffixes — never
   Blender's silent `.001`); charset `[A-Za-z0-9_-]+`; KIT_ANNOT*
   rejected; idempotent; all-or-nothing; report JSON written BEFORE any
   rename (crash-resume).
2. **`split_mesh` op**: loose-parts `dry-run`/`split` (bmesh connected
   components, zero-residue preview, per-part bboxes, risk refusal on
   co-users/modifiers/shape-keys/armature without `ack_risks`) +
   **`split-region`** for WELDED continuous geometry (vision-driven
   world-box, faces-fully-inside cut unit, straddlers stay with source;
   region+default mode = region dry-run). Source name lands on the
   largest part; rest `<id>_pNNN`; region cut names via `new_id`.
3. **Validator de-name-dependence** (D16 audit HIGH #1): gate
   exclusions (floating/below-floor/penetration/above-5m) honor the
   `kit_semantic` PROP (written by label_objects when the label
   contains ceiling/sun/light); legacy names = fallback only. Renaming
   a labeled ceiling can no longer strip gate coverage (regression
   L11).
4. **Manifest**: every MESH row carries `kit_label` (null when
   unlabeled) — the durable identity for non-vision consumers.
5. Docs: AGENTS.md D16 op section + two laws (gate exclusions SEMANTIC;
   consumers read manifest kit_label); kb/semantic_labeling.md (full
   pass + box-isolatability law); fixture-authoring gotchas in the
   dogfood doc (cube size=2 default, coplanar-weld not box-cutable).

## Dogfood artifacts (output/d16/, NOT committed — reproducible)

- interior_import.blend (fixture: welded shell 1 component + props
  sheet 10 islands + lamp 2) → interior_split.blend →
  interior_labeled.blend (14 parts, all labeled) →
  interior_assembled.blend (blind agent's work; audit 0.0mm).
- labels_report.json, audit_assembled.json, look_1/2/3 + closeups.
- Fixture: scripts/d16_interior_fixture.py.

## Immediate next-session TODO (in order)

1. **F17 fix (measured in dogfood)**: place_on footprint auto-widen
   grid misses small inset supports (leg spans 0.01m outside 12×12
   sample columns). Options: support-size-adaptive density, or raycast
   the mover's bottom perimeter downward. Add a t-suite case.
2. **Validator v2**: skip shell-vs-contained-prop intersection pairs
   (label contains room/shell/floor/wall AND other's centroid inside).
   Careful: only when BOTH sides are labeled (prop-based, not lexical).
3. **R5 dog-food: polyhaven import lane** (real online asset end-to-end:
   download → import → LOOK → label pass → save → blind consumer).
   This is the REAL-asset validation the fixture only simulates.
4. Keep QA lane running (it has commit access; expect mid-session
   pushes — fetch+rebase, never force).
5. Open items in PLAN.md: t10 export-package suite, t6 ship, upstream
   D11 PR, crowd T3 (upstream-gated).

## Standing gotchas (do not relearn)

- Work in /home/z/vision-work clone (watchdog resets /home/z/my-project);
  Write tool only under /home/z/.
- "File content impossible" errors = harness display mangling — verify
  with ast.parse / od, trust the file.
- bmesh: never return BMFace refs after bm.free() (indices only).
- bound_box corners are prop arrays — wrap with Vector before @ matrix.
- primitive_cube_add defaults size=2; scale-span helpers must pass
  size=1.
- MultiEdit on argparse blocks can mangle neighbors — re-verify with
  ast.parse after every structural edit.
- GitLab push prints storage warnings even on success — verify HEAD.
- F6 residue: `add_sky_world()` DEFAULT strength (1.0) still blows out
  EEVEE studio stills — template now passes 0.5 + gotcha 128 written;
  changing the library default would alter every existing scene (needs
  an owner ruling).
- look SUBJECT-OVERFLOW hint fires on large ground planes inflating
  cluster diag (R1 carry-over).
- export_previz_package "0 shots" path prints crowd-flavored gate
  summary lines (cosmetic once lane-aware gates pass vacuously).
- transient_scan 1-frame timeline message could say WHY (no adjacent
  pairs) (edges carry-over).
- AGENTS.md documents the previz-package lane nowhere (R4 F9 doc gap).

## Worklog + artifacts

- Repo worklog.md has the session-6 record (also replicate into
  /home/z/my-project/worklog.md — harness dir does not survive resets).
- Study artifacts: docs/USABILITY_R1..R4.md; study scenes
  scripts/r3_turntable.py + reading_nook.py + crate_stack.py; design
  docs/DESIGN_D16_semantic_labeling.md (amendments adopted).
- Multi-agent QA protocol: fresh-context sub-agents do NON-VISUAL
  review only; the D16 audit (round 1) is the pattern to reuse for the
  implementation review.

## QA-LANE DISPATCH R23 (auto)
- #6 fix-verify at c37cb4f: VERIFIED (v1_basic PASS 6 obj, v2_balanced PASS 7 obj through look.py; README line now true) — CLOSED by QA. VK era total: #1/#2/#3/#5 closed R22 + #6 closed R23. Remaining open-ours: #4 only (==AK-15 workbench-gray).

## QA-LANE DISPATCH R26
- NEW #7 [P2][robustness]: look.py total-fails on a fresh container — renders
  succeed into a /tmp tempdir, then stitch_contact_sheet hits ImportError
  (Pillow absent from Blender bundled python3.13; blrun.sh injects only
  $SCRIPT_DIR) -> ImageMagick montage fallback (also absent) -> uncaught
  FileNotFoundError -> rc=1, output dir EMPTY, verdict/manifest never printed.
  The renders are lost with the tempdir. Likely first live-fire of look.py
  (S5 untouched 25 rounds). Fix sketch: copy renders to --output right after
  render; try/except the stitch (WARN + continue); install.sh provision
  Pillow into bundled python and/or guard montage with shutil.which.
  Evidence: freshbook docs/qa-blender-kit/evidence/qa-r026/ (commit 04280e94).
- R26 follow-up #8 [P3][design-gap]: look.py default framing clips off-center
  objects (S5 fixture: cone/cube reduced to edge slivers in front+persp) while
  readiness prints subject_pct=93.7 flags=[] — image adequacy is exposure-only
  and never cross-references the object-id manifest against the frame bounds.
  Fix sketch: project each manifest bbox via world_to_camera_view, WARN on
  frame-contact/clipping. Evidence: freshbook qa-r026 (REPORT-R26-S5-AB.md).

## QA-LANE DISPATCH R28
- NEW #9 [P3][false-positive]: validate_scene floor_penetration flags the
  scene's OWN ground slab (>=5cm thick, top at z=0) as penetrating the floor
  100% — _is_ground_like height gate (<=0.05) excludes every solid ground
  slab; 0.05m boundary arm also fires on float dust. look.py runs VERDICT
  WARN + P1 on clean scenes; --fail-on-issues would fail them. Boundary
  proof: 0.2m fires / 0.05m fires / 0.04m clean. Twin rule vendored in
  agent-kit validate_scene.py:68-73 — mirror the fix. S7 TOPPLED receipt
  (same round): verdict-eye agreement 2/2 (TOPPLED/90deg = tower lying in
  render; SETTLED control upright).

## QA-LANE DISPATCH R32 (auto)
- #8 evidence comment (5980562329): S5-dense A/B (48-cone 6×8 formation, look.py defaults) — default camera lands INSIDE the crowd on both tiles, yet VERDICT PASS + subject=98.6% (frame-coverage metric inverts truth at density); SUBJECT-OVERFLOW HINT fires via bounds math but does not gate. Ask upgraded: manifest-vs-frame-bounds cross-ref in readiness + surface the hint as a WARN + crowd-aware default camera (auto dolly-out / min height / --topdown). Evidence: freshbook docs/qa-blender-kit/evidence/qa-r032/look_grid.png (filed by QA lane)

## QA-LANE DISPATCH R36
- #10 [P3][example-bug] quickstart examples/scene_v1_basic.py: sphere drift DEAD — first keyframe_insert runs at end_frame (cube section leaves it there), start key overwritten by end key at f24 → fcurve=[(24,−2.0)], evaluated x=−2.0 ALL frames. Probe+one-line-fix control proven (frame_set(start) → keys [(1,+2.0),(24,−2.0)], drift lives). look.py render/manifest CORRECT — example is the defect. Fix: scene.frame_set(start_frame) before first sphere key. Evidence+control: freshbook evidence/qa-r036/REPORT-S10.md. Found via S10 determinism pass (look.py byte-exact, MAD 0.0 — baseline refinement noted in same report).

## QA-LANE DISPATCH R39 (auto)
- #7 CLOSED-VERIFIED R39 (comment 5984216760): filing condition pre-empted — install.sh:137 now auto-provisions Pillow into the bundled python (landed silently; never commented). Fresh-container receipt: labeled PIL-hidden sim reproduces the exact R26 chain (renders succeed → PIL ImportError → montage FileNotFoundError → empty output dir, rc=1); post-canonical-install look.py rc=0 VERDICT: PASS validator P0=0. Residual hardening note (not re-filed): error-handling chain unchanged (missing-PIL post-install still total-fails uncaught) — optional polish. Evidence: freshbook docs/qa-blender-kit/evidence/qa-r039/VK7_*.txt + REPORT-R39.md. (filed by QA lane)

## QA-LANE DISPATCH R46
- #11 [P2][bug] look.py --angles panels pixel-identical when loaded .blend has camera-bound timeline markers (marker camera hijack at render time — AK-10 class; agent-kit viewport_capture fixed it via suppress-BEFORE-assign + finally-restore, look.py has no marker handling). Repro: blend with markers S1@f1->CAM_A, saved frame 24, --angles front,persp -> meanAbsDiff 0.002 (38/307200 px), captions still say front/persp, manifest healthy with no per-panel camera recorded. Evidence: freshbook docs/qa-blender-kit/evidence/qa-r046/{grid.png,look_manifest.json,r046_main.log}.
