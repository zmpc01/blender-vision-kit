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
| scripts/rh_canvas.py | mainline s40 (71eb1c3) via the s40 vendor round | 71eb1c3 | UA string only (zero code drift; the kit s40 carries the s20 manifest-tags/frames deltas natively — port-back CLOSED, pair zero-drift) |
| tests/test_rh_canvas.py | mainline s40 (14/14 incl. R9) | 71eb1c3 | none |
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
- NEW SANCTIONED DELTA (s22): rh_canvas library-split discovery — the
  2026-10-17 platform migration moved the director 3D assets OUT of
  RH-canvas-characters into beulahkemp/RH-3d-assets (manifest renamed
  director-gltf-manifest.json -> gltf-manifest.json; same join schema).
  Discovery now resolves THREE clones (animations / characters /
  models) with a legacy fallback probe; load_models + load_thumbnails
  read the models root. Landed here first (tested live: test_rh_canvas
  14/14 against the real repos), port-back queued for mainline.
- STATUS FLIP (s22): the RH data source is LIVE again (was "private,
  inaccessible" through s21): beulahkemp/RH-canvas-* + RH-3d-assets all
  resolve, the CDN serves real binaries (sha-verified 2,137/2,137 FBX
  locally), and test_rh_canvas now RUNS (was graceful-skip) — 14 rows
  against real data. The fixture library keeps its role: the offline
  determinism path + the CI-safe regression base.
