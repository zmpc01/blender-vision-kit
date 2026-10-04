# HANDOFF.md — blender-vision-kit (immediate next-session scope)

> Session close: 2026-10-04 (session 6). QA-lane fix wave #1–#6 →
> dog-food R3 (EEVEE lane) + R4 (export/previz lane) → D16 semantic
> mesh labeling DESIGN+AUDIT (implementation = M6, next session).
> PLAN.md = long-horizon tracker. Upstream snapshot preserved at
> docs/UPSTREAM_HANDOFF_snapshot.md.

## State at handoff

- Repo: https://github.com/zmpc01/blender-vision-kit (main; session-6
  head = c37cb4f + wrap-up commits). GitLab mirror
  gitlab.com/ansgareutychisO/blender-vision-kit (PAT namespace is
  ansgareutychisO; WAF 403s probabilistic — retry). GitHub = source of
  truth. NEVER force push.
- SCOPE DOCTRINE (binding, owner-ruled): this kit is FOR vision-native
  agents ONLY. No VLM bridges, no ascii packs. Sub-agents: NON-VISUAL
  QA only. The principal makes every visual verdict.
- Toolchain: NOT committed. Fresh sandbox: `bash install.sh` in
  FOREGROUND (the harness reaps background processes — setsid/nohup
  do NOT survive; burned two bootstraps this way). install.sh now
  honors BLENDER_BIN (zero-download reuse) and skips EEVEE warm-cache
  below 2400 MB MemAvailable (QA #2, verified live at 2245 MB).
- Regression battery (ALL GREEN at close): test_kit_scope, test_v1_look
  27/27, test_v2_motion 27/27, test_v3_edges 20/20, test_v4_colorsync
  29 checks (NEW), t1-t6 placement suites (T5z positive TOPPLED added),
  t8 8/8, t9_chaos_fuzz ALL PASS. t8/t9 need `-- --output output/tests/<t>`.
- Multi-remote hygiene: QA lane pushed MID-SESSION (R22 dispatch) and
  my push was rejected non-fast-forward — fetched, verified theirs was
  HANDOFF-only, rebased, pushed. Expect this to recur; never force.

## Session-6 kit changes (evidence: docs/USABILITY_R3.md + R4 + D16 doc)

1. D15 display-color sync (QA #4): `annotate.sync_display_colors()` /
   `restore_display_colors()` standalone (outside the annotation layer);
   look.py calls sync pre-render + restore in finally; manifest rows
   carry `color_source`. Workbench MATERIAL now shows node-authored
   colors (visually verified RGB cubes, 4 angles).
2. Engine-vocabulary bridge: `blender_kit.normalize_engine()` (short
   names for perception CLIs) + common_parser normalizes through
   `normalize_engine_id` (raw ids for the ship family). Every CLI
   accepts every spelling; defaults unchanged (argparse bypasses type).
3. motion_study animated-first pick (R3 F7: statics crowded out the
   only mover — second consumer hit).
4. keyframe_contact_sheet: MATERIAL + D15 sync (was OBJECT color mode —
   all-gray sheets).
5. export_previz_package dual-lane (template-family scenes now work:
   inspect-based animate bridge, ctx.get("scene") fallback, shots/
   characters gates lane-aware) + FIXED pre-existing `blob` NameError
   blocker at gate 14 (crashed EVERY run of ANY scene — R4 F10b).
6. safe_import_scene path-tolerant (QA #1): bare names, ./examples/
   fallback, explicit paths — examples/ + README verified working.
7. install.sh/blrun.sh: MemAvailable guard + honest Cycles verify +
   BLENDER_BIN override (QA #2/#3, closed by QA R22).
8. Examples migrated to driver convention (QA #6): build_scene()->ctx,
   animate(ctx,*), version-safe sky; v1's floating cube fixed.

## Immediate next-session TODO (in order)

1. **M6: implement D16** — semantic mesh labeling per
   docs/DESIGN_D16_semantic_labeling.md (amendments ADOPTED, first-
   session scope listed there): `label_objects` apply_patch op
   (additive `kit_label` + opt-in two-phase rename, idempotent,
   all-or-nothing) → look.py manifest `kit_label` field → validator
   de-name-dependence (CEILING_NAMES → kit_semantic prop) → split_mesh
   dry-run/mutate pair → dogfood pass on an opaque fixture (build a
   nameless "city block": pillars/pipes/stairs as Mesh.001…) →
   blind sub-agent addresses 3 labeled objects (success criterion).
   Doc duties: PARAM_DOCS + --list + AGENTS.md op table.
2. R5 dog-food candidate: polyhaven/import lane (pairs with M6's
   dogfood — one pass can serve both).
3. Candidate t10: export_previz_package regression suite (R4 F10b
   lesson: the tool had ZERO coverage and shipped a total blocker).
4. Keep the friction-log discipline (docs/USABILITY_R5.md); run the
   regression battery after each kit change.
5. Milestone backup: /home/sync copy + both remotes (commands in PLAN
   M4). Session-6 close backup taken at c37cb4f+wrap-up.

## Known-open friction (triaged, NOT yet fixed)

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
