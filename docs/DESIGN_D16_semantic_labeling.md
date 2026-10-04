# D16 — Semantic mesh labeling of imported scenes (DESIGN, pre-implementation)

> User-directed use case (session 6): imported scenes/meshes usually arrive
> as continuous or opaquely-named geometry ("Mesh.001…") with no semantic
> info. A VISION-NATIVE agent can identify WHAT each part is (pillar, pipe,
> stairs, wall, prop…) by looking at renders; the goal is to "parse" and
> "reverse" an opaque asset into semantically-named, structured objects that
> NON-VISION agents (planners, QA lanes, code-only actors) can then operate
> on through the kit's id-addressed tools (apply_patch ops address objects
> by NAME — unnamed imports are nearly inoperable for them).

## Problem statement

1. Imported GLB/FBX/OBJ: meshes named "Mesh.001/002…", or one merged
   mesh; apply_patch/validate/place ops all address by object id — an
   opaque import blocks every id-addressed workflow.
2. Vision agents CAN classify geometry from renders (that is our core
   competence) — but the kit currently has no workflow/op surface that
   TURNS a visual identification into a durable scene-state mutation.
3. Sub-agents and downstream planners consume the manifest JSON — the
   manifest should carry semantic labels once assigned.

## Design (v1 sketch, for critique)

### Loop: LOOK → NAME → LABEL → LOOK (verify) — the "semantic pass"

1. **Build the import surface** (existing): `import_gltf`/mesh import +
   `look.py --load-blend imported.blend` → annotated grid + manifest of
   opaque ids (Mesh.001...). The manifest already lists dims/centroid —
   geometry hints my eyes + the labeler use.
2. **Vision identification (the principal's job, not automatable)**:
   read the 4-angle grid (+ closeups via --closeup per object when the
   grid is ambiguous), and produce a label map
   `{id: {"label": "pillar", "confidence": "high|medium|low"}}`.
   Evidence discipline: labels recorded WITH the angle/frames seen.
3. **Kit op surface — `apply_patch` gains `label_objects`**:
   `{"op": "label_objects", "labels": {"Mesh.001": "pillar", ...}}`
   - writes `object["KIT_LABEL"] = label` (custom string prop; survives
     save/load; never touches mesh data)
   - sets `object.name = label` when unique (disambiguate
     `pillar`, `pillar.002`…) — renaming must be collision-safe
   - report lists renamed/kept + collisions; fail-closed on duplicate
     target names (offer `.NNN` suffixing via `on_collision: suffix)`
   - optionally writes into the manifest at next look.
4. **Merge/segment caveat (continuous meshes)**: a single merged mesh
   can only be LABELED (whole-mesh label) or SPLIT first (bpy
   `separate by loose parts` — new kit op `split_mesh` with a dry-run
   reporting part count/bboxes BEFORE mutation, because a bad split
   wrecks the asset). Order: look → (optional dry-run split) → split →
   re-look → label parts.
5. **Verification (vision + gate)**: re-look with labels visible
   (annotate's label layer already prints object names — labeled ids
   now read `pillar`/`stairs` right in the grid: self-verifying);
   `--closeup` per labeled group; manifest JSON carries the labels for
   non-vision consumers.
6. **Persistence**: `apply_patch --save-blend` (state carrier law) —
   the labeled state is THE deliverable; downstream agents work against
   it with existing id-addressed ops.

### Non-goals (v1)
- No automated mesh classification (no ML, no heuristics-first) — the
  vision principal IS the classifier; the kit provides the op surface.
- No UV/material inference, no LOD work.
- Crowd-scale labeling (1000s of parts) is out of scope until the
  manual loop is proven (batching by visual similarity is a v2 idea).

### Success criterion
A fresh sandbox, an opaque import → named, verified, saved state that a
NON-VISION sub-agent can then operate on purely through ids/labels in
apply_patch/validate ops (measured: sub-agent correctly addresses 3
labeled objects with no visual access).

## Audit (fresh-context critique round 1, session 6) — AMENDMENTS ADOPTED

Verdict: implement WITH amendments. The audit found one HIGH in-ecosystem
hazard and one HIGH split-mesh hazard, plus contract sharpening:

1. **[HIGH] Validator name-dependence** — validate_scene.py's
   CEILING_NAMES excludes objects by NAME token ("ceiling","sun",...):
   vision renames can silently strip gate coverage. Amendment: move
   semantic exclusions to a `kit_semantic` prop (written by the label
   op) or shape rules; names stop being load-bearing for gates.
2. **[HIGH] split_mesh preconditions** — refuse on multi-user mesh data
   (glTF shares meshes across nodes), modifier stacks (separate acts on
   the base mesh), armature/shape-key bindings, without explicit ack;
   dry-run = bmesh connected-components ONLY (no residue), reporting
   part count + per-part bboxes + which mesh (base vs evaluated) was
   analyzed + co-users + polycount + source disposition.
3. **Naming law**: persistent props are lowercase in this kit
   (`kit_atmo`, `kit_target`) — use `kit_label` + `kit_label_conf`;
   uppercase `KIT_*` is the disposable-object prefix (cleanup sweeps
   would hunt it).
4. **label_objects contract**: idempotent; all-or-nothing (validate all
   ids + simulate the whole-batch rename collisions — Blender's silent
   `.001` suffixing is "a lie" per apply_patch's own doc — then two-phase
   rename all→temp→final, re-read to verify); charset `[A-Za-z0-9_-]`
   (dots break three.js gotcha-48; spaces break --closeup); reject
   KIT_ANNOT_* labels (manifest filters that prefix); schema
   `{id: {label, confidence}}`; rename is OPT-IN (`rename:true`) — the
   additive `kit_label` prop is the durable identity in v1; audit-style
   JSON report written BEFORE any rename (crash-resume artifact).
5. **Manifest**: `kit_label` becomes a MANDATORY row field in look.py's
   `_manifest()` (else additive-only labels are invisible to non-vision
   consumers — the design's own success criterion).
6. **Verification honesty**: annotate billboards render INDEX numbers
   only (name↔index map is text) — the grid is a cross-check, the
   manifest JSON is the verification artifact.
7. **Doc duties**: PARAM_DOCS entry (else typo-warn protection is
   disabled for the new keys), --list, AGENTS.md op table.

## First-session scope (next session, M6)

1. `label_objects` op (additive kit_label + opt-in safe rename) + tests
2. look.py manifest kit_label field + v4-style suite coverage
3. Validator de-name-dependence (kit_semantic prop) + t-suite
4. split_mesh dry-run/mutate pair + tests
5. Dogfood: import an opaque multi-part scene (or build a nameless
   "city block" fixture: pillars/pipes/stairs as Mesh.001…), run the
   full LOOK→NAME→LABEL→LOOK→SAVE pass, then verify a NON-VISION
   sub-agent can address 3 labeled objects blind (success criterion).
