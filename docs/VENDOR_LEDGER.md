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
| scripts/rh_canvas.py | mainline s38/s39 lineage | 6943ab5 | s20 sanctioned: data-driven tags/frames in tests, --tag/--max-frames filters, UA/provenance header (BOOKED for port-back, see rows below) |
| tests/test_rh_canvas.py | mainline | 6943ab5 | none (byte-identical) |
| docs/rh_canvas.md | mainline | 6943ab5 | s20 amendments (fixture library + any-rig + placement sections) |
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

- rh_canvas.py s20 deltas (data-driven tags/frames, --tag/--max-frames)
  + docs/rh_canvas.md s20 amendments → mainline ledger row (s21 queue;
  land as a mainline commit, then BOTH trees byte-identical again).
