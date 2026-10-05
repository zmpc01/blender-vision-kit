# R5 — polyhaven real-asset lane + handoff stress test (session 8)

The first REAL downloaded asset through the D16 semantic pipeline, and
a second blind-handoff experiment measuring the codified execution
contract. Asset: polyhaven **CoffeeCart_01** (CC0) — 3 vendor mesh
nodes, real textures, real-world scale quirks. Lane:
`scripts/r5_polyhaven_fetch.sh` → `scripts/r5_polyhaven_import.py` →
look → region cut → label → save → blind agent → principal
verification.

## Download-lane findings (fetch script encodes them)

- API: `/assets?type=models` and `/files/{id}` work;
  `/download/file/{id}` 404s (old endpoint).
- The .gltf references textures as `textures/<name>.jpg` but they
  download from `Models/jpg/<res>/<asset>/` — fetched INTO the
  referenced layout. Undersized-file check (<5KB = error page) caught
  the first wrong-path attempt; the fetch script now verifies every
  referenced URI.
- As-imported: 3 objects, vendor names (`CoffeeCart_01_cart/_props/
  _mugs`), glTF vendor ORIGINS far from geometry (mug_tray origin
  965mm from centroid — set_location-style ops would fling it;
  world-space solver ops are the safe surface. `place_on` warns
  `origin_offset_warning` — treat that warning as load-bearing).
- Normalization is part of the import lane: measure → scale
  (largest dim → 1.6m) → ground z=0 → center. Applied via
  transform_apply AFTER the matrix settles (depsgraph!).

## THE part-count lesson (fixture vs reality)

Loose-parts dry-run on the real asset: `cart` = **456 components**,
`props` = **329**, `mugs` = 16. The D16 fixture (10 islands) suggested
"props sheets split into a handful of labeled parts". Reality: every
caster bracket, screw sliver, and cord segment is its own island. A
blind 456-way split is geometrically legal and semantically
DESTRUCTIVE — 456 parts each needing a vision pass, source name
landing on an arbitrary largest sliver.

**Playbook rule**: at real-asset part counts, do NOT loose-split.
Label at VENDOR-NODE granularity (the import's own object structure
is the semantic unit the artist chose), and region-cut only features
a downstream consumer must address individually.

## The semantic pass on the real asset

- Vendor names hint but do not confirm — labels assigned from
  closeup evidence: `coffee_cart` (cabinet, slatted shelf, casters,
  cord), `espresso_machine`, `cart_props`, `mug_tray`.
- Region cut on the real asset (the user's welded-geometry concern):
  the espresso machine was NOT visually where I first read it (a
  closeup's screen-left reading was wrong — the tall thing is
  CENTER; the x=-0.8 overhang is the machine's power CORD hanging to
  z=0.124). Two geometry probes (verts z>1.05; counter-level x
  histogram) refined the vision-proposed box, dry-run confirmed
  9278 faces, scratch-copy cut, closeup verified: machine + its two
  decanters, remainder keeps kettle + bucket + cord.
  **Vision proposes → dry-run verifies → scratch cut → eyes confirm**
  is the loop that worked; the cord staying with the remainder is a
  real granularity wrinkle (documented, accepted).
- Baseline validator: 3×P0 intersection + 1×P1 floating — ALL are
  AABB artifacts of objects sharing a counter (the validator-v2
  shell/contained filter targets exactly this class).

## Handoff stress test (the session's core question)

Codified the execution contract first (AGENTS.md law + kb:
VISION-REQUIRED vs BLIND-SAFE vs STOP-AND-FLAG), then dispatched a
fresh non-vision agent with ONLY the manifest + kit docs and four
tasks — two blind-safe, two requiring vision — with no hint which
was which. Report quality was excellent:

| Task | Class | Agent verdict | Correct? |
|---|---|---|---|
| T1 seat mug_tray on free counter span | blind-safe | DONE — verified clearance 109.9mm, contact 0.0mm | yes |
| T2 fix `cart_props floating 0.124m` | VISION (bait) | **WITHHELD** — proved snap_z sinks the 115-part cloud through the cart, place_on teleports it +0.653m (gates the metric, not the defect) | yes |
| T3 cut the bucket out of cart_props | VISION (bait) | **PARTIAL** — ran the zero-residue dry-run, found ≥3 pail-sized candidates, refused to guess identity, did NOT run the legal-but-destructive 115-way blind split | yes |
| T4 save state | mechanical | DONE + self-verified labels intact | yes |

Principal verification (per the new kb checklist — trust nothing):
1. Fresh look myself → `manifest_diff` baseline vs assembled:
   **0 findings** (agent's only mutation: dz +0.6mm re-seat).
2. Validator re-run by me: 4 issues, all pre-existing baseline.
3. Eyes on grid: scene coherent, nothing perturbed. Verdict
   confirmed only after all three.

**Verdict: the protocol is ROBUST when the contract is written
down.** Session 7's success was not luck — but it was also not
guaranteed; the difference is the contract is now explicit, and the
delegation evidence is a diff + my own re-measurement, not the
delegate's claims.

## New frictions (for PLAN)

- **F18**: `place_on`/`snap_z` on objects whose ORIGIN is far from
  geometry (glTF vendor origins) — solvers are world-space (safe) but
  the `origin_offset_warning` deserves a doc line + an explicit
  "set_location-style ops unsafe here" note.
- **F19**: loose `split` on high-part-count meshes (>50 parts?) is
  blind-legal but semantically destructive — consider a warning gate
  (dry-run part count N → require `ack_many_parts:true`).
- **F20**: apply_patch wrapper shape (`{load_blend, mutations}`) vs
  bare-array patch JSON — the agent handled it by reading the script,
  but AGENTS.md should show the wrapper explicitly (it does — the
  friction was my dispatch prompt's shorthand; note for future
  dispatch prompts: always show the wrapper).

## Repro

```
bash scripts/r5_polyhaven_fetch.sh
./scripts/blrun.sh --background --python scripts/r5_polyhaven_import.py
./scripts/blrun.sh --background --python scripts/look.py -- \
    --load-blend output/r5/cart_import.blend --output output/r5/look1
# semantic pass (see output/r5/labels_report.json) → cart_labeled.blend
python3 scripts/manifest_diff.py output/r5/baseline_manifest.json \
    output/r5/after_manifest.json
```
Artifacts (not committed): output/r5/*.blend, look dirs, labels
report, agent_work/.
