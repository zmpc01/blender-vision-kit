# USABILITY_TD1 — the vision-native film build (session 12)

> The user's mission: re-run the whole previz workflow with the
> VISION-native kit + dog-food the crowd kit, identify frictions,
> push visual quality. The film: TERMINAL DAWN (`tdawn_1`, staged in
> previz-review). This doc is the friction/finding record; the build
> log is worklog.md Task 12 entries; the design is
> DESIGN_terminal_dawn.md.

## What "vision-native" changed in practice (the headline)

The principal READ every look.py grid, every still, every flow strip
with its own eyes — no ASCII packs, no external VLM, no
programmatic-proxy verdicts for anything visual. Concretely:

1. **Camera framing became an eye-driven loop.** 6 of 12 shot cameras
   were reframed after the principal SAW the broken render (near-wall
   blocks the lens; a gate jamb dead-center; the lens buried in the
   crowd's backs; the roof arch plane bisecting an aerial). None of
   these were catchable by the validator (geometry was legal) or by
   readiness gates (luma/subject % were healthy). The blind-kit
   workflow would have shipped these framings.
2. **The flow strip replaced guesswork about sim coverage.** One
   top-down ortho sheet at f1/200/400/700/1000 answered "where is the
   crowd at each beat" — the L5 representation-split law applied to
   the film's own story: the surge mid-stream lands S3, the plaza jam
   lands S6, the empty-hall beat lands S11. Hero path timing was
   retimed 2.2 s earlier BY LOOKING at where the stream actually was.
3. **Materials/lighting were judged on stills, then anchored in
   numbers.** The AgX failure modes (below) were FOUND by eye
   (paper-white gate; tan slab) and CONFIRMED by input probes
   (emission values). Eyes triage; probes decide — the two-column law
   held.

## Frictions found (F-TD#), with disposition

- **F-TD1 — cross-kit wheel install is manual.** crowd-kit's
  `setup_native.sh` provisions only ITS OWN tools/ tree; using the
  vision kit's Blender means hand-installing the wheel + jsonschema
  into the OTHER kit's Blender python (exact --target path, no
  version pin check). DISPOSITION: documented in the runbook
  addition below; a `--blender-python PATH` flag on setup_native.sh
  would close it (filed to crowd kit as a candidate).
- **F-TD2 — validator noise on structurally-dressed scenes.** The
  hall's roof members/columns/walls intersect BY DESIGN: 184 flagged
  objects, P0 22→77 across iterations, drowning real findings. The
  D16 containment skip covers shell-vs-prop pairs, not
  structural-join pairs (arch-through-wall, column-through-floor).
  DISPOSITION: accepted for previz (the manifest carries the full
  set); a `kit_label` structural vocabulary (roof/structure/foundation
  → intersection-skip when both sides labeled) is the kit-side fix.
- **F-TD3 — marker-camera hijack bites ANY render pass on a
  marker-bound scene.** bpy render honors the ACTIVE marker's camera
  over scene.camera; my flow strip rendered shot cams instead of its
  ortho cam, AND clearing `marker.camera = None` MUTATES
  scene.camera (observed: fell back to the last shot cam). The
  viewport_capture fix (suppress-before-assign + finally-restore) is
  not enough — scene.camera must be RE-ASSERTED after the sweep.
  DISPOSITION: fixed in my tool (tdawn_flowstrip.py); look.py
  REMAINS VULNERABLE on marker-bound scenes (kit filing — the #11
  QA issue pattern, now with the scene.camera mutation wrinkle).
- **F-TD4 — the bake driver owns the keepout pass-through; nothing
  enforces it.** My first tdawn_bake call skipped
  `keepouts=contract.CAM_KEEPOUTS_V3` (the plugin's bake.py passes
  them; nothing failed — agents just walked through the low cams and
  I SAW the result as a capsule filling S7's frame). DISPOSITION:
  fixed in my driver; kit-side, `to_previz_cache` could WARN when a
  contract declares CAM_KEEPOUTS_V3 non-empty but keepouts=() was
  passed (cheap loud guard).
- **F-TD5 — view-layer staleness false-positives the #29 sweep
  (KIT BUG, the session's most important find).** `render_hidden_
  objects`' view-layer-excluded check compares scene.objects against
  `bpy.context.view_layer.objects`; a freshly-linked object (measured:
  Runner.Root, linked last in build) can lag the view-layer list →
  classified render-hidden → dropped from the GLB → gate 24 REJECTS
  the export ("declared references missing"). One
  `view_layer.update()` before the sweep closes it kit-side.
  DISPOSITION: scene-side sync duty added (build_scene ends with the
  update — the L19 law family); the kit-side fix should land in
  blender-agent-kit's blender_kit.render_hidden_objects (owner repo;
  vendors down). THIS SESSION DID NOT TOUCH THE OWNER REPO.
- **F-TD6 — the 5.2 Principled emission default is WHITE.** Any glow
  material with Emission Strength > 0 and default Emission Color
  adds pure white — AgX then clips the whole surface to paper (S6's
  gate read as a projection screen). Second AgX law measured:
  strength >~1.0 desaturates hot emission to TAN before clipping.
  DISPOSITION: make_material pins Emission Color to the base rgb +
  glow keys capped ≤0.95. Kit candidate: make_material should set
  Emission Color by default (both kit copies).
- **F-TD7 — the exporter's unmapped-constant gate is load-bearing
  and GOOD.** It caught HERE/PREVIZ_SCRIPTS/TOTAL_FRAMES (internal
  wiring) instantly with a teacher-grade message naming all three
  options. The scene-module naming law (uppercase = payload only) is
  now proven on a second, from-scratch scene.
- **F-TD8 — parallel-session git races are real.** The remote moved
  TWICE during bootstrap (D17/F22/F20 commits from a parallel
  session); GitLab and GitHub diverged by one commit mid-session.
  The sync_both.sh discipline (fetch-rebase-push, never force)
  absorbed all of it; one GitLab WAF window remains (retry cadence).

## Kit improvement filings (owner-repo candidates, not landed here)

1. render_hidden_objects: view_layer.update() before the #29 sweep
   (F-TD5 — export-blocking).
2. look.py: marker-camera suppression + scene.camera re-assert for
   marker-bound scenes (F-TD3; matches QA #11 on agent-kit).
3. to_previz_cache: loud WARN when the contract declares keepouts
   but keepouts=() was passed (F-TD4).
4. make_material: pin Emission Color to base rgb (F-TD6).
5. setup_native.sh: --blender-python PATH for cross-kit wheel
   installs (F-TD1).
6. validate_scene: structural-join vocabulary (roof/structure) as an
   intersection-skip class with visible counters, mirroring the D16
   containment-skip pattern (F-TD2).

## The vision-workflow ledger (what the kit gained)

- `tdawn_flowstrip.py` — top-down ortho flow sheet (marker-safe);
  generalizes to any marker-bound animated scene.
- `tdawn_filmstrips.py` — the 8-frame-per-shot strip pass (the
  deterministic renderer convention, one workbench process).
- `tdawn_stills.sh` — one-EEVEE-process-per-shot stills (the OOM law
  as a script).
- The REV-2 design fold record (DESIGN_terminal_dawn.md) — the
  peer-review → adoption trail for a from-scratch export-contract
  surface (markers + SHOTS_V3 + CAMS_V3 7-tuples + CAST roots +
  CA.Body.* + no star-imports).
