# HANDOFF.md — blender-vision-kit (immediate next-session scope)

> Session close: 2026-10-04 (session 7). M6 D16 semantic mesh labeling
> IMPLEMENTED + dogfooded end-to-end (user's imported-asset use case,
> incl. welded continuous geometry via the region cut). Success
> criterion MET (blind sub-agent test). PLAN.md = long-horizon tracker.

## State at handoff

- Repo: https://github.com/zmpc01/blender-vision-kit (main). GitLab
  mirror gitlab.com/ansgareutychisO/blender-vision-kit (PAT namespace
  ansgareutychisO; WAF 403s probabilistic — retry, verify remote HEAD).
  GitHub = source of truth. NEVER force push.
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
