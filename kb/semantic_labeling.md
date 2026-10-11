# Semantic Mesh Labeling (D16) — Deep Reference

Imported assets (GLB/FBX/OBJ from online sources) arrive as
`Mesh.001/002…` or ONE continuous mesh. Every id-addressed kit op
(`apply_patch`, `place_on`, `validate_scene`) is inoperable on opaque
ids. The VISION agent is the classifier; these tools make its judgment
durable and machine-consumable.

## The semantic pass (LOOK → NAME → LABEL → LOOK → SAVE)

1. **LOOK** — `look.py --load-blend imported.blend` (or import first via
   a scene module). The manifest lists every opaque id with dims +
   centroid + `kit_label` (null until labeled). Read the 4-angle grid;
   use `--closeup` when the grid is ambiguous.
2. **NAME** (the principal's eyes, NOT automatable) — build a label map
   `{id: {"label": "pillar", "confidence": "high"}}`. Record labels WITH
   the angle evidence you saw. Continuous mesh? → step 2b.
   **2b. SPLIT** — `{"op":"split_mesh","id":"Level","mode":"dry-run"}`
   reads the connected-component report (part count, per-part bboxes,
   co-users, risks — ZERO residue). If the parts are what you expect:
   `{"op":"split_mesh","id":"Level","mode":"split"}`. The source name
   lands on the LARGEST part; the rest become `<id>_pNNN`. Re-look:
   parts need their OWN vision pass (kit_label is never propagated).
3. **LABEL** — `{"op":"label_objects","labels":{...},"rename":true,
   "output":"output/labels_report.json"}`. Additive `kit_label` /
   `kit_label_conf` props on every id; two-phase rename with whole-batch
   collision simulation (Blender's silent `.001` suffixing is a lie for
   patches — the op pre-uniques with `_2/_3`). The report JSON is
   written BEFORE any rename — a mid-crash leaves a recovery artifact.
4. **LOOK (verify)** — re-look the saved state: the manifest JSON now
   carries every `kit_label` (that is the verification artifact —
   annotate billboards render INDEX numbers, the grid is only a
   cross-check). Validator verdict must be unchanged from the labeled
   baseline unless you introduced a real defect.
5. **SAVE** — `apply_patch --save-blend labeled.blend`. The labeled
   state is THE deliverable; downstream non-vision agents address
   objects by name/label through existing ops.

## label_objects contract

```json
{"op":"label_objects",
 "labels":{"Mesh.001":{"label":"pillar","confidence":"high"},
           "Mesh.002":"crate"},
 "rename":true, "on_collision":"suffix", "output":"output/labels_report.json"}
```
- Idempotent: re-running the same batch reports everything `unchanged`.
- All-or-nothing: unknown ids, bad charset, or `fail`-mode collisions
  abort BEFORE any mutation.
- Charset `[A-Za-z0-9_-]+` (dots break three.js gotcha-48; spaces break
  `--closeup`). `KIT_ANNOT*` rejected (manifest filter prefix).
- `rename` is OPT-IN — the additive `kit_label` prop is the durable
  identity in v1; rename is a readability convenience.

## split_mesh preconditions (D16 audit HIGH #2)

`split` REFUSES without `ack_risks:true` when: mesh data shared by
multiple objects (glTF shares datablocks across nodes — co-users'
geometry would mutate), modifier stack present (the cut hits the BASE
mesh, evaluated geometry differs), shape keys, armature binding.
Library-linked data is refused outright. Read the dry-run FIRST: a bad
split wrecks the asset. `dry-run` runs anywhere — it never mutates.

## WELDED geometry: the region cut (mode=split-region)

Loose-parts split finds NOTHING on welded/continuous level geometry
(floor+walls sharing verts — one component). The way out is the
VISION-driven region cut: the principal looks at the render, boxes the
feature they identified, and the kit cuts those faces out as a new
object:

```json
{"op":"split_mesh","id":"Mesh.000","mode":"split-region",
 "region":{"min":[1.15,3.75,-0.01],"max":[1.85,4.85,2.6]},
 "new_id":"pillar"}
```
- Passing `region` with the default mode = REGION DRY-RUN (verts in
  box, faces-to-cut, captured bbox — zero residue). Run it first.
- Cut unit = faces FULLY inside the box; straddling faces stay with the
  source (narrow the box to capture them). Report says exactly what
  will move before anything mutates.
- Preconditions identical to loose split (ack_risks on co-users etc.).
- The cut object is labelable immediately: `label_objects
  {"pillar": {...}}`.
- Box-isolatability law: a welded feature is only box-cutable if its
  footprint PROTRUDES from its host (engaged pillar: yes; lintel flush
  with wall tops: no — the wall-top faces fall inside any lintel box).
  On real imports, expect per-feature judgment; measure with the
  dry-run before cutting.

## Delegation contract (who may run what)

Delegation across the vision boundary is the failure mode the kit is
built to prevent: a non-vision agent holding only a manifest has
geometry + names, NOTHING else. The classes (AGENTS.md law, restated
here for the operator's checklist):

- **VISION-REQUIRED (principal only)**: region-cut box selection
  (a blind agent cannot know where to cut — that box is READ OFF A
  RENDER); label/naming assignment; every visual verdict; verification
  of delegated work (below).
- **BLIND-SAFE (from manifest + docs)**: loose-parts dry-run/split;
  `label_objects` with labels GIVEN to it; placement ops with
  manifest-derived numeric targets; audit tools; look.py runs (JSON
  consumers — renders belong to the principal).
- The manifest is the WHOLE world of a blind consumer. Everything it
  needs must be IN the manifest (`kit_label`, `world_bbox`, dims,
  centroid). Anything not derivable from it → the delegate STOPs and
  flags back. Guessing is a protocol violation, not a workstyle.

## Verify-delegated-work checklist (the principal runs this)

"Trust but verify" is not enough — VERIFY, with numbers you produced:

1. **Baseline before delegating**: fresh `look.py` run → its
   `look_manifest.json` is the before-state.
2. **Diff after return**: re-run look yourself → diff with
   `python3 scripts/manifest_diff.py before.json after.json`
   (`--expect-clean` when the task should move nothing). EVERY finding
   must map 1:1 onto a task the delegate was GIVEN — anything else is
   unauthorized mutation; reject the work.
3. **Re-measure yourself**: re-run `audit_contacts`/`validate_scene`
   on the returned state. The delegate's claimed numbers are a claim,
   not evidence — even kit-generated JSON in its output dir could be
   stale or from a pre-final state. Your run is the evidence.
4. **Closeup every touched object** — not just the hero shot. A
   delegate can nail the headline while scraping a bystander.
5. **Verdict only after 1–4.** "It said it did X" is never a verdict.

## Gate-exclusion law (validator)

A label containing `ceiling` / `sun` / `light` writes `kit_semantic`;
validate_scene excludes such objects by PROP for floating /
below-floor / floor-penetration / above-5m checks. Legacy name matching
("Ceiling", "SunLight"…) remains only as fallback for scenes that never
ran the label op. Consequence: relabeling a ceiling to anything still
excludes it IF it was labeled via the op — but hand-authored scenes
that RENAME a ceiling without labeling DO lose coverage (label it, or
set `kit_semantic`, to keep the exclusion).

## Props (lowercase law)

`kit_label` (string) · `kit_label_conf` (high|medium|low) ·
`kit_semantic` (set/removed by the op; presence = gate exclusion).
`KIT_*` uppercase remains RESERVED for disposable objects — cleanup
sweeps hunt that prefix; never write props named `KIT_*`.

## R6 — the playbook on a REAL stitched interior level (loft demo)

The Blender Foundation "Loft" demo (download.blender.org/demo/cycles,
CC demo file) is the first REAL level run through the full pipeline:
6.5 x 20 x 6.7 m two-level apartment, 1200 mesh objects, 3.97M polys.
Lane scripts `r6_loft_*.py`, state chain output/r6/loft_import →
loft_look → loft_cut_arch → loft_labeled → loft_props → loft_compose →
loft_final.blend. Everything below was measured, not assumed.

### What a real level actually looks like
- NOT one welded blob: 1200 SEPARATE vendor objects (kitchen.* x841,
  Panel_* x145, beds, sofa modules...) at fine granularity — the R5
  "vendor-node granularity" lesson holds. The welding is SELECTIVE:
  the architectural shell `Cube` (floor band + walls + mezzanine slab +
  ceiling in ONE 193-face mesh) and, per the manifest, the real walkable
  floor `Cube.001` is its OWN full-extent zero-thickness plane. Never
  assume where the floor lives — read it from the render + bbox.
- Vendor quirks are the norm: 45 texture refs pointing at the AUTHOR's
  disk (2010-era paths, 3ds-max "Map #..." names) + 9 missing addon
  libraries. Honest normalization = detach broken refs, record, move on.

### Huge-scene LOOK economics
- look.py flag-wireframe CAP at 60 (was: ~1198 flagged x 12 boxes =
  12k annotation objects → OOM + red spaghetti). Full flagged set stays
  in the manifest JSON.
- Packed textures are dead weight for workbench LOOK: strip images +
  orphans_purge into a look-lite .blend (561MB → 99MB) — materials keep
  basecolor identity via the D15 sync.
- Preset 5m angle offsets land INSIDE walls on 20m interiors. The
  region-identification pass = aimed survey shots (camera→target pairs
  through vc.render_angle custom) + frustum RAYCASTS from a survey
  camera to answer "which object is that pixel" without more renders.

### Region cuts on the welded shell (the flagship)
4 cuts, each dry-run → split-region → render-verified:
floor band (5 faces), ceiling (18), mezzanine slab (42), stairs (14 —
a 68-degree space-saver run hiding inside the shell, found by frustum
raycast, confirmed by pre/post cut renders). Cut order matters when
boxes overlap: cut the unambiguous slabs first, the ambiguous one last.

### mesh_prepare — the fused-face pathology and its signature
Symptom: region dry-run reports verts_in_region > 0 but faces_to_cut
= 0 no matter how the box is drawn. Cause: floor+wall fused into
wrapped faces (verts shared across a 90-degree fold) — "faces fully
inside" is unsatisfiable. Fix: `mesh_prepare(id, mode:"triangulate")`
(n-gons → tris; 19 n-gons on the loft shell made the front floor band
cuttable... and revealed the front floor was never IN the shell: the
real floor was the separate Cube.001 plane all along). Lesson: when a
cut refuses, ASK whether the geometry is fused or simply elsewhere —
one more survey shot is cheaper than a wrong cut.

### Labeling 1200 objects (schema at scale)
One label_objects patch, 1155 rows, generated programmatically from
the manifest: architecture from the cuts (floor/wall/ceiling/mezzanine/
stairs) + name-family batches verified per FAMILY by closeup
(kitchen_unit x841, partition_panel x145, bed x12, sofa_module,
shelf_unit, rug, table, plant, deco x63...) + geometry-derived labels
(exterior_window = tall glazing on the -x wall, railing = the z 2.9-3.9
band). Confidence is HONEST: high = render-verified, medium =
name-pattern/bbox-derived. ~4% left null (truly unresolved) — an
honest null beats a wrong label; the blind handoff proves it.

### The handoff catches YOUR label errors (measured)
The R6 blind agent, reasoning ONLY from the manifest, flagged that the
`lounge_chair`/`floor_lamp` labels sat at y≈0, z 2.7-5.1 — nowhere near
the mezzanine chair the task described. Closeup confirmed: that cluster
is a pendant light (three glass globes on cables); the labels were
wrong, and were corrected (pendant_light x23, floor_lamp → the real arc
lamp, chair x2 = the dining chairs the blind agent had flagged as
"unlabeled pedestals"). A blind agent cannot see, but it CAN do
consistency checks the principal's eyes skip — encourage it to report
spatial anomalies against the task description.

### Blind stress test on the level (protocol v2, all green)
T1 place a book on the upstairs bed: the bed is 12 stacked shells
(differing tops 3.415..3.82) — two honest failed attempts (support
occluded by interposed shells; corner-first rest on a 13.6-deg slope),
resolved by topmost-surface law + align_to_surface, audit CLEAR 0.27mm.
T2 cushion on the mezzanine: TOUCHING, 2.36m from the standing actor.
T3 BAIT "place a mug on the dining table": correctly WITHHELD — the
manifest shows exactly one table-labeled object at y≈2 (not the dining
zone y≈8-12) and the real dining chairs UNLABELED; the agent refused to
guess identity (vision-required) and returned the zone evidence instead.
manifest_diff: 2 findings (the two additions), 1209 rows unchanged.

## R7 — navigation validates labels (the Plane.003 lesson)

R7 attempted floor-to-floor actor navigation on the labeled loft and
the attempt IMMEDIATELY exposed a wrong label: the raycast tread-hug
found no walkable surface under the `stairs`-labeled object. Probes
(mesh face enumeration, under-overhang ray maps, frustum scans through
render pixels) established:
- the `stairs`-labeled object = a 14-face stair-shaft PARAPET (low wall
  + sloped top piece) — correctly `wall`;
- the real stair = `Plane.003` (labeled `wall` in the R6 schema): 9
  flat treads, rise 0.34 / run 0.65 (~31°, NOT 68° — the R6 reading was
  parallax from the fragment's bbox), climbing +y UNDER the mezzanine
  slab band with ~1.9 m headroom, arriving directly onto the slab at
  y 13.8.

Labeling lessons:
1. Rendering verifies APPEARANCE, not WALKABILITY. The R6 render check
   ("stair survived the cut perfectly") verified the stair was not
   DAMAGED, not that the label covered the stair. Only USE exercises
   adjacency/direction/support. Navigation is the strongest label
   validator in the kit.
2. Family/name-pattern labeling stays medium-confidence until used; the
   corrected schema now records the evidence inline
   (gen_r6_labels.py comments carry the tread map numbers).
3. Stair-direction from bboxes: decidable ONLY when the stair abuts
   the slab from OUTSIDE its span (touch end = top). A stair inside
   the slab span is ambiguous (it may run under it) — blind STOP-
   AND-FLAG + vision_stair_override.json (evidence recorded in the
   route as vision_assisted).
4. Manifest consumers should treat `kit_label_conf` as "what the
   principal could verify AT LABEL TIME" — usage may upgrade or
   overturn it. (F23 queued: unexercised-label confidence reporting.)
