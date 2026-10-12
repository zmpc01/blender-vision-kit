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

## Session-13 additions (the iteration round — new frictions + closures)

- **F-TD5 CLOSED upstream** (agent-kit commit e4450a3): the #29 sweep
  now forces view_layer.update(); regression A19f (freshly-linked-last
  CAST root must ship) is red/green proven. VENDORED DOWN the same day
  (the wrapper's governed-pair guard refused the export on the sha
  drift — the discipline working as designed).
- **F-TD9 (new): the factory-scene leak.** `--factory-startup` loads
  the default Cube+Camera+Light into the built scene; a fresh sandbox's
  startup file is factory while an old one may be cube-free (masked for
  sessions). Scene-side purge landed (build_scene). install.sh's
  Pillow loop also probes py3.11 paths — 5.2 bundles 3.13 (manual
  install needed; a --blender-python-aware fix belongs in install.sh).
- **F-TD10 (new): concurrent blrun = silent EEVEE death.** Two
  pipelines both start Xvfb on :99; the second's startup kills the
  first's display with NO traceback. Serialize Blender work in a
  sandbox.
- **F-TD11 (new): the glow-surface white void.** Emission keys were
  innocent — the near-white ALBEDO (make_material's design) reflected
  the ambient to paper. The fix is the base/emission DECOUPLE (dark
  base, warm Emission Color) — make_material should grow a
  `emission_color` param (both kit copies; filed).
- **F-TD12 (new): recessions occlude their own cameras.** A depth
  structure built on the camera's side of an opening hides everything
  inside it (ray-cast proven). The kit candidate: a shot-cam occlusion
  probe in the look tooling (cast the camera's center ray, name what it
  hits).
- **Stills script**: tdawn_stills.sh gained --factory-startup (its
  absence was a latent tdawn_1 landmine) + a SAMPLES env override (the
  S10 heavy-class OOM at 32).

## Session-14 closures (the kit-side trio + the user comment round)

- **F-TD10 CLOSED** (D-TD20): all four blrun.sh copies carry a
  cooperative per-display flock (exit 90 + `LOCK-HELD` marker on
  contention; fd 9 closed in the Xvfb/blender children so KEEP_XVFB
  reuse does not inherit-and-hold; BLRUN_FORCE=1 bypass; agent-kit's
  --version short-circuit relocated above the lock). Acceptance:
  contention rc=90+marker, KEEP_XVFB-twice green, --help pre-lock.
  agent-kit (owner) vendored down to the escape repo — 40/40 IN-SYNC.
- **F-TD11 CLOSED** (D-TD21): make_material grew `emission_color` +
  `emission_strength` (both kit copies + the tdawn_actors twin, which
  now RE-APPLIES emission kwargs on cached materials). Default pins
  Emission Color to base (the white-void law); strength is a direct
  write (raises — never a silent no-op). Tests: agent-kit t7 +
  vision-kit v8, ALL PASS on 5.2.2; twin re-apply probe green.
- **F-TD12 CLOSED** (D-TD22): look.py `--probe-camera NAME|all` casts
  the center ray per scene camera (dep.update() ritual for
  constraint-driven cams; render_hidden flag + bounded re-cast for the
  Street.Mist class; ANNOT/temp_ filters; unknown name = missing row,
  never an exit; probe-only = `--angles none`; rows in
  look_manifest.json `camera_probes`). Tests: test_v7_camprobe 14/14
  incl. the animated-occluder S9 class (wall keyed off-ray f1→f24:
  wall named at f1, subject named at f24).
