# kb/s24_s27_session_laws.md — the s24-s27 session law archive (on-demand)

> Condensed OUT of SKILL.md (the 30k law). The blocks below are the
> full condensed forms as they stood; the one-line versions live in
> SKILL.md. Each law = a real failure that cost a cycle.

## SESSION 27 LAWS (the engine-map round — condensed; full: worklog s27 + HANDOFF s27 block)

- **THE ENGINE-MAP LAW**: a film module's _set_engine MUST carry an
  explicit CYCLES branch — a two-way eevee/workbench map silently
  renders workbench stills for --engine cycles, and WORKBENCH IS
  LIGHT-BLIND (gotcha 128): the "look regression" it produces is
  indistinguishable from an engine-swap tune loss. Four of six films
  shipped light-blind stills for two sessions; the certified two were
  exactly the two WITH a branch. AUDIT THE MAP whenever a film fails
  a LOOK gate with "everything flat".
- **THE ENGINE-CONDITIONAL TUNE IS INERT WITHOUT THE D2 HOIST**: a
  build-time `scene.render.engine` read sees the FACTORY default
  unless main() sets the engine BEFORE build_world
  (normalize_engine_id, the 3-line hoist). The tferry sky mirror
  never fired until s27.
- **THE BOTH-ENGINE MIRRORS (measured, s27)**: tferry/tgreen
  corpus-matched UNTOUCHED under real Cycles (the s26 ladders were
  chasing workbench ghosts); tsquall storm sky x3.0; tfog volume
  0.028 EEVEE / 0.040 CYCLES via fog_density_for_engine (Cycles
  single-scatter reads THINNER — the Cycles value is the HIGHER one).
  Copy the tferry_world mirror pattern; never a bare constant swap.
- **THE PREFLIGHT ORDER LAW**: span/animation-dependent gates run
  POST-animate (the exporter's real order); a pre-animate REJECT that
  skips the animate-dry check DEADLOCKS the preflight. And the
  animate-dry check must use the exporter's REAL dispatch
  (n_frames=None) — a truncation breaks the humanoid anchor-vs-cache
  gate's frame coherence (the dx=18.6m false-fail class).
- **THE GOVERNED EXPORT PIN**: the kit-export wrapper sha-pins
  agent-kit's blender_kit against shared_manifest.json — a moved
  agent-kit HEAD refuses the export. The s27 export vintage is
  fca46ca; ASSERT the pin in the export script.
- **THE FILMSTRIPS RESUME + FORMAT LAW**: 96-strip runs span tool-call
  windows — skip existing non-empty files (idempotent resume); pin
  image_settings.file_format="JPEG" or Blender replaces the .jpg ext
  with .png (the tsquall class).
- **THE BAND-AMEND RECEIPT LAW (re-proven)**: an engine move can land
  a calibrated gate one step off (tsquall in-line 4->3 at the pinned
  engine); amend the band WITH the recorded cause + the fresh receipts,
  never silently.
- **THE OOM KNOB ORDER** (the audit's correction): memory_limit >
  cast reduction > resolution > samples/bounces — bounces are TIME
  levers, not memory levers.

## SESSION 26 LAWS (the eye-gate verdict + the rig reconstruction — condensed; full: worklog s26 + HANDOFF s26 block)

- **THE ENGINE-SWAP LOOK LAW**: a render-engine swap INVALIDATES every
  pinned look tune — a look verdict carries its engine id; swapping
  the engine re-opens the tune (the s25 Cycles swap silently broke 4
  of 6 films; the eye gate caught what the gates could not).
- **THE ARMATURE APPLY SILENT-RESET**: transform_apply on an ARMATURE
  resets the object scale WITHOUT baking the data — all armature
  transforms go through edit-bone surgery (a probe-proven law).
- **THE OBJECT-LEVEL FIT LAW**: baking an imported armature's object
  matrix (rot+scale) into data TWISTS every bone frame (roll does not
  follow a data rotation) — fit imported rigs at OBJECT level only.
- **THE CHANNEL-COHERENCE LAW**: an imported clip skeleton's rest-
  scales + cm channels + data are ONE coherent system — data-space
  rescale lands the action translations 100x; the object matrix is
  the only safe scale knob.
- **THE BASIS-PAIRING LAW**: skinned meshes ride coherent skinning
  only when mesh basis = arm_world^-1 @ mesh_world (the rot90X cm
  import convention included) — scale-only pairings leave the
  rotation mismatch and explode the skin.
- **THE DANGLING-MODIFIER STATUE CLASS**: clearing an armature
  modifier at isolation and then "retargeting" it ships REST-POSE
  statues — bind green, gates green, skin dead; the multi-vertex
  evaluated-mesh probe (G5) is the catcher.
- **THE ALIASING GATE LAW**: sparse gate sampling lies about
  oscillating signals (5 samples read hips bob 0.018; the TRUE
  excursion 0.045 across 37 frames) — sample dense enough to bound
  the extremes before believing a FAIL.
- **THE WOLD-SPACE-CORRECTION LAW**: a world-space correction stored
  as an object LOCATION gets rotated by downstream parent chains —
  corrections bake into the DATA (and a round-trip assert on the
  re-appended artifact must confirm the world effect BEFORE saving).
- **THE SYSTEMEXIT SWALLOW**: Blender swallows SystemExit messages —
  a "silent crash" with no traceback may be your OWN gate firing;
  wrap main in a traceback-to-stdout dump while iterating.
- **THE STALE-ARTIFACT LAW**: every intermediate render made with a
  since-replaced artifact is STALE — re-render after the artifact
  lands, never certify mid-ladder frames.
- **THE RIG-SERVING FALLBACK LAW**: load-bearing assets serve through
  env-wins/repo-fallback (the clips' pattern generalized): the rig
  lives at vendor/rh_rig/ (a lossless .blend, committed + sha'd);
  RH_ASSETS wins when the checkout exists.
- **THE EYE-GATE SHEET PIPELINE**: scripts/s26_eye_sheets.py rebuilds
  the per-film sheets from the COMMITTED packages (the /home/sync
  copies die with the sandbox — the app repo is the durable source).

## SESSION 25 LAWS (the humanoid rollout + collision/nav round — condensed; full: kb/s25_humanoid_rollout.md)

- **THE 24FPS TIMEBASE LAW**: the FBX imports (rig/walk/idle/UAL)
  SILENTLY flip scene.render.fps 24→30 — the GLB plays at the SCENE
  fps, so the film exports playing 1.25x fast. _fps_guard
  saves+restores around EVERY import; the gate that catches it:
  key-interval bands (apparent speed = sim × 1.25 — tform_2 slipped
  UNDER the band at drill speeds and SHIPPED the latent look bug;
  tform_3 re-export carries the fix).
- **THE DATA-NAME LAW**: structural finders must resolve at the
  mesh-DATA level — per-group copies rename BOTH object and data
  (Object.copy SHARES data; the rename happens on the unique data
  copy, else the finder matches 0 bodies).
- **THE ARRIVAL-DELTA GATE**: any obstacle-declaration change proves
  baseline-vs-new probe arrivals MATCH before the geometry scan is
  trusted — a sealing rect jams silently (tsquall 84/38 identical).
- **THE ANIMATION-BAKE OOM LEVER**: export_frame_step=2 at the
  bake's own 12Hz halves the 28M-key bake; gates are interval-
  normalized.
- **THE STAGE-COMMIT LAW**: stage and the app-repo commit in the
  SAME micro-step — the tform_2 loss class (a staged package without
  its commit is unreproducible; the sandbox wipe proved it).
- **THE EXEMPT-ROW LAW**: film overlay performers (the tsquall slip
  faller's tumble) get documented EXEMPT rows, never silent skips;
  the report printer is shape-agnostic (the 5-d KeyError class).

## SESSION 24 LAWS (the sync + vision-lane round — condensed)

- **Probe before you clone**: the credential matrix AND the repo
  locations drift between sessions (vision-kit is zmpc01's, not
  beulahkemp's — a lossy summary said otherwise; the direct API probe
  settled it in one call). Re-verify every "known" fact against the
  remote.
- **A runner-shaped hole is a tool**: the suite_runner the worklog
  recorded was absent from the tree — every re-land re-derived the
  loop by hand. Restored as scripts/run_battery.sh with BOTH
  invocation contracts (bpy suites via blrun; bpy-less vendored
  unittest via host python3 — unittest.main consumes blrun's flags).
  Sweep tests/ for bpy-less files before trusting a blrun-only runner.
- **The sync law bites on PARTIAL vendors**: a lane's "kit s41
  wholesale" vendor carried rh_canvas only — the crowd_obstacles
  bridge never arrived. Diff the SOURCE commit's file list against
  the vendored tree, never trust the vendor message's scope claim.
- **Submodule pin supersets are safe to vendor against**: VK's pin
  (b4bf76e) is 467 commits AHEAD of mainline's — the vendor gate +
  battery verify the superset live. Newer-pin vendors need a gate run,
  not a pin downgrade.
- **AUDITS read code; CONSUMERS read docs** (the U1 law): four
  blockers no code audit saw (argparse vs blender argv — always
  script_argv(); a CLI that cannot see a scene; an undiscoverable
  answers schema; an ImportError in the vendored guide's own
  snippet). Run a docs-only consumer wave on EVERY new CLI surface.
- **The fail-open class recurs wherever gates meet callers** (third
  occurrence): computed-printed-never-enforced (the lab's world
  gates). The fix is ALWAYS the same shape: assert at the collection
  site, carry the verdict into the artifact.
- **A gate's strict form is falsified by the happy path** (second
  proof): slotless-over-LIVE refuses, but a FRESH slotless bind is
  the legitimate bake shape. Measure the refusal against the real
  path before landing it (the connected-location lesson, again).
- **Render-encoding laws are measured, never assumed**: 0.012m
  outlines anti-alias away; an outline at floor z is OCCLUDED by its
  own object; a fixed bevel is 0.5px at 19m ortho; RGB-distance
  visibility never fires on AA-blended pixels (hue bands do). Probe
  render, LOOK at the probe, then pin the law in the module.
- **Sanctioned deltas travel in lockstep**: the +4 re-export names
  touched the re-export, BOTH gate tests (count pins), the ledger
  row, and the O8a pin — one contract, N pins, update N sites or
  the battery lies.
