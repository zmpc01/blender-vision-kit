# VENDOR_LEDGER.md — the vision-kit's vendored-lineage provenance

> The vision kit is NOT a downstream repo in mainline's s33
> shared-manifest contract (it forked before s33 and is a VARIANT, not
> a scene repo). This ledger replaces the manifest mechanism here: it
> records WHERE every vendored file came from, at which upstream tip,
> and which deltas THIS tree carries. Refresh rule (s20/s21 pattern):
> re-vendor wholesale from the named tip; vision-side changes land as
> documented sanctioned deltas in the file itself + a row here.

## Ledger

| File | Vendored from | Tip | Vision deltas |
|------|---------------|-----|---------------|
| scripts/rh_canvas.py | mainline s41 (aa05cf3, the RH-3d-assets migration) via the film lane's 68fbb1e vendor round | aa05cf3 | UA string only (zero code drift; s23 validated 16/16 real + 14/14 fixture + crossval; s23 test-determinism fixes folded in-tree AND ported upstream 17e3ef1) |
| tests/test_rh_canvas.py | mainline s41 + s23 scoring/determinism fixes | aa05cf3 | s23: row() fail-on-check-FAIL scoring + R10b factory reset + R9g2 cold-cache purge (also ported upstream 17e3ef1) |
| docs/rh_canvas.md | mainline s40 + s20 amendments | 71eb1c3 | fixture-library + any-rig + placement sections |
| scripts/assets_ual_actors.py | mainline s33 port-back | 6943ab5 | none (provenance header only) |
| scripts/ual_bake.py | mainline s34 engine split (owner:kit) | 6943ab5 | none (provenance header only) |
| scripts/ual_test/ual_gauntlet.py | mainline v3.4 | 6943ab5 | none (provenance header only) |
| tests/test_ual_bake_laws.py | mainline | 6943ab5 | none (provenance header only) |
| scripts/hero_gates.py | mainline s32 | 6943ab5 | none (provenance header only) |
| tests/test_hero_gates.py | mainline | 6943ab5 | none (provenance header only) |
| scripts/oracle_frames.py | mainline | 6943ab5 | none (provenance header only) |
| docs/DESIGN_s32_export_reconciliation.md | mainline | 6943ab5 | — |
| docs/DESIGN_s33_shared_interop.md | mainline | 6943ab5 | — |
| docs/DESIGN_s34_ual_split.md | mainline | 6943ab5 | — |
| docs/SHARED_SYNC.md | mainline | 6943ab5 | reference only — the manifest contract does NOT govern this variant (see header) |
| docs/rh_fullwalk_s39.md | mainline | 6943ab5 | — |
| docs/daz3d-scene-modules.md | mainline | 6943ab5 | — |
| docs/previz_package.md | mainline | 6943ab5 | — |
| assets/vendor/quaternius/*.fbx + probes | blender-escape-previz project/research/_rig | previz HEAD (d29f19e/f82fae5) | — |
| scripts/crowd_obstacles.py | mainline s41 (5b49527, the scene→obstacle bridge + engine audit) — s24 sync vendor | 5b49527 | none (zero code drift; `blender_kit.iter_all_fcurves` resolves against THIS tree's shim — same name, VK-native) |
| scripts/crowd/__init__.py | mainline s41 (the 20-name vendored re-export package; VK previously had NO scripts.crowd surface — direct-submodule imports only) | 5b49527 | none (loader anchors at vendor/blender-crowd-kit — same layout; VK pin b4bf76e is 467 commits AHEAD of mainline's bc11fcb, 1.6.0 wheel — superset verified by the gate test live) |
| tests/test_crowd_obstacles.py | mainline s41 (O1–O11 incl. live bake + the ENGINE-GAP jam pin O11c) | 5b49527 | none — 11/11 PASS in this tree (VK pin) |
| tests/test_crowd_vendor_gate.py | mainline s41 (names+count+alias gate, fail-closed probe) | 5b49527 | none — ALL GREEN (VENDOR-PROBE-OK 1.6.0) |
| docs/crowd_system/STATUS.md | mainline s41 (the engine-truth section: no path planning → total jam 0/20; pressure-soft pushout 0.59 m; force_fields inert at bake; upstream issues #1–#8) | 5b49527 | none |

## Deliberately NOT vendored (scope doctrine)

- `scripts/ground_truth_export.py`, `scene_corpus.py`,
  `corpus_synthetic.py`, the ascii stack: the ascii-vision corpus lane
  is upstream's audience (vision kit = native-vision ONLY, session-4
  course correction).
- `tools/sync_shared.py` + `tools/shared_manifest.json`: the s33
  manifest governs kit↔previz; this variant is not a party. This
  ledger is the variant-appropriate provenance surface.
- Review round-trips (docs/reviews/s32..s34): design docs carry the
  folded law text; review history stays in mainline.

## Port-back bookings (vision → mainline)

- CLOSED (s40): rh_canvas s20 deltas + placement_lib VK s17-s20
  hardening port-back landed upstream (mainline aa4ea44, 985 lines;
  batteries decide) — placement_lib is now BYTE-IDENTICAL across both
  trees, and the kit s40 rh_canvas carries the s20 tags/frames deltas
  natively. Zero-drift pair restored.
- NOTE: the RH data source (beulahkemp/RH-canvas-*) went PRIVATE
  2026-10-16 (was 404) — still inaccessible; the fixture library
  remains the data layer.
- CLOSED-BY-UPSTREAM (s41 aa05cf3, vendored here 68fbb1e): the s22
  library-split discovery booking. Mainline's s41 landed a SUPERSET
  design (assets3d key; 5-field manifest drift guard; previews joined
  per-model; thumbnails + dummy-rigs surfaces; require_library total).
  The s22 'models' key + legacy-fallback probe were REPLACED by the
  vendor (no external callers; stale-clone serve -> the kit's
  fail-closed migration law). The s23 audit of the s22 delta (AUDIT-C)
  is retired with it — its P3s are moot upstream (P3-2 totality exists
  in s41; P3-1's warning was superseded by the refusal law).
- s23 residual upstream nit (filed, NOT blocking): mainline's
  discover_libraries docstring still says "Returns {animations,
  characters}" (missing assets3d). The require_library PRIVATE note
  is CORRECT as written (anonymous ls-remote still fails — verified
  s23; the repos need a token, the CDN binaries stay public).
- STATUS FLIP (s22): the RH data source is LIVE again (was "private,
  inaccessible" through s21): beulahkemp/RH-canvas-* + RH-3d-assets all
  resolve, the CDN serves real binaries (sha-verified 2,137/2,137 FBX
  locally), and test_rh_canvas now RUNS (was graceful-skip) — 14 rows
  against real data. The fixture library keeps its role: the offline
  determinism path + the CI-safe regression base.
