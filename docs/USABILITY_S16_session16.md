# USABILITY_S16 — the KIT-QUALITY wave (session 16, 2026-10-13)

> Scope doctrine this session (user-ruled): NO film building — the parallel
> lane owns scene work. This lane = audit / test / review / refine the kit
> itself + stress-test coverage for the kit's workflow. The export/package
> lane was chosen as the target because the audits proved it had ZERO test
> coverage while generating landmines every film session (R4 NameError;
> tferry's three contract landmines in one session).

## The audit wave (3 parallel read-only sub-agents — ROI evidence)

| Audit | Method | Top yield |
|---|---|---|
| 1-a exporter contract inventory | full read of export_previz_package.py + ledgers | 0 tests on the export lane; 5 P0 landmine classes (opaque shape crashes, silent BOARD drops, ungated sfx stream, film modules green-but-story-empty, entry-point mismatches); **TWO-exporter scoping finding** (this tree = escape/template lane; film lanes use the canonical agent-kit copy via KIT_EXPORTER) |
| 1-b ledger triage | all USABILITY_* ledgers vs current code | F-TF5 still open (TF1 ledger said CLOSED — doc debt); F-TD9 + QA-R69 verified; doc-debt map (7 filings closed-in-code but open-on-paper) |
| 1-c AGENTS.md drift | every literal doc claim vs argparse | 1 crash-a-consumer defect (`--annotate` doesn't exist); 4 stale claims; **1 real code bug** (scoped audit matched `verdict` not `state` → fail_on_penetration could never abort a scoped audit) |

Lesson: three cheap read-only audits produced one real bug, the whole D19
spec, and the session's priority list — audit BEFORE implement.

## Fixes shipped (Wave A — all with regression coverage, test_v9 8/8)

- **F-TD5 ported to THIS tree**: `render_hidden_objects` now sweeps the
  DEPSGRAPH (`view_layer.update()` at the sweep). The film modules'
  caller-side compensation becomes law at the sweep itself.
- **Scoped-audit state fix** (apply_patch): counts/matches the `state`
  enum like the unscoped path, honoring the contact band (review P2-7) —
  `fail_on_penetration` can now actually abort a scoped audit.
- **F19**: `split_mesh` refuses loose splits >50 parts without
  `ack_many_parts` (the 456-part lesson is now a gate).
- **F20-R6**: place_on's error teaches the occluded-support class.
- **F-TD9 + QA-R69** (install.sh): Pillow resolution is AUTHORITATIVE
  (BLENDER_PY override → BLENDER_BIN probe → tools/blender probe →
  newest-glob fallback) and the skip path is a loud named WARNING;
  dangling `tools/local-libs` symlinks are healed before dpkg-deb.
- **F-TF5 closed**: vendor wheel re-synced 1.0.0 → 1.5.5 (governed;
  provenance README in wheels/; crowd-kit's tree is the source of truth).

## The flagship: D19 export preflight + t10 (design REV-2 → implemented → tested)

- **Design discipline held**: DRAFT-1 → fresh-agent critique (ADOPT-WITH-
  CHANGES, 7 blocking fixes, every claim verified file:line) → REV-2 →
  implementation. The critique caught: B3 had to MIRROR the exporter
  (CAM_ prefix lives on the CAMERA object; marker names are free);
  the BEATS timing rule false-rejected tdawn (demoted to shape-only
  WARN); the t10 fixture was unreachable from a temp dir (fixtures go
  into scripts/); B4 needed the atmo exemption; the parity guard needed
  Phase-B inputs; S1 must replicate the dispatch (Signature.bind,
  bool-is-int quirk).
- **`scripts/export_preflight.py`** (~1360 lines): Phase S (entry points,
  attributed schema over all 21 imported STORY_SOURCES, coherence, sfx
  shape) + Phase B (build dry-run: ctx/fps/markers/hidden-sweep/parity
  guard). Exit 0/3; every rejection names constant+row+expected+got+fix.
- **The decode-parity guard** (B5): re-runs the exporter's OWN
  `_collect_story` against the built module; opaque crashes are
  differentially attributed (single-constant deletion); BOARD key-set
  drops reject (the P0-2 silent-drop detector).
- **t10 tier 1** (`test_t10_preflight_prop.py`, pure python, 0.2 s,
  100 checks): the drift-rot property BOTH directions — decoder
  drops/raises ⇒ S2 rejects; decoder accepts ⇒ S2 accepts — with the
  REAL decoder as oracle under stubbed imports. The one agreed
  exception: LUNGE_V3's silent value-drop maps to WARN (documented).
- **t10 tier 2** (`test_t10_export.py`, subprocess, 7.5 s wall): exporter
  happy path + 5 negatives (F-TF4 sfx class → preflight AND gate 15 both
  reject; BOARD undecodable → gate 4 + preflight; short CAMS row →
  attribution asserted; bare `def animate(ctx)` → S1).
- **Exporter hardenings**: gate 15 (sfx stream conformance, fail-closed,
  fps-MISMATCH rejects / fps-missing tolerated for old-format files) +
  gate 4 strengthening (declared non-empty BOARD that decodes to zero
  entries now rejects).

## Battery findings (Wave D — the suite-level yield)

- **usd_export kwarg rot on 5.2.2**: the 4.5-calibrated kwarg set
  TypeErrors (`export_textures`). Fix: RNA-FILTER at runtime against
  `get_rna_type().properties` (export_usd.py + the test) — version-proof
  by construction. Same unexercised-lane class as the R4 NameError.
- **The F-TD10 flock broke four suites' documented run mode** (v2/v3/v4/
  v7 nest blrun under an outer blrun): nested calls now carry
  `BLRUN_FORCE=1` (the documented bypass — the nested call is the test's
  own tool invocation, not a competing pipeline). All four re-verified.
- **Scope hygiene**: a session-12 probe leftover (`probe_crowd_bake.py`)
  sat in scripts/ violating the `probe_` ban — moved to `smoke/crowd/`.
- **Review P2s adopted**: `_vec_check(none_ok=False)` for CAMS vecs;
  `animate=None` hasattr fix; `split_would_refuse` includes the F19
  count; gate-15 n_sfx ordering + guarded fps cast; B5 runs BEFORE the
  sfx emitter (an emitter can no longer shift the parity snapshot) +
  tempdir cleanup; legacy CAMS fallback WARN-only; exporter line-refs
  corrected after the docstring edit shifted them −5.

## Environment finding (session-critical)

**The GitHub PAT died (401 Bad credentials) before this session's first
push.** Reads kept working (public repo, anonymous). GitLab's PAT is
alive and GitLab carried the session as the authoritative target. Law:
verify BOTH PATs at session start (2-line curl check) before planning
pushes; a dead GitHub PAT converts "push to both" into "GitLab primary,
GitHub flagged for rotation".
