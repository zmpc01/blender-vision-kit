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
