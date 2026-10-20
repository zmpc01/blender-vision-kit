# DESIGN — s26: the Cycles world re-tune wave (+ the rig reconstruction unblock)

Status: REV-1 for audit. Owner: session-26 orchestrator.
Trigger: THE EYE GATE (s26) — 2/6 certified; 4 films' certified looks broken
by the s25 engine swap. This doc covers D1 (the kit world law), D2 (the rig
reconstruction), D3 (the per-film re-tune procedure), D4 (the re-ship path).
Night-market (D5) is designed separately AFTER D1 lands — it is the first
film born under the corrected Cycles night laws.

## Evidence base (measured this session, repro'd live)

- E1. tferry S6, cylinder crowd, IDENTICAL world build, engine the only
  variable: EEVEE = the certified night (near-black sky, sodium pools,
  glowing boards); Cycles = flat gray (background ~#8a8a8a, no pools).
- E2. The s25 stills runner rendered ALL humanoid films in Cycles at
  640x360 (--engine cycles, samples 24). tdawn (dawn sky, sun above
  horizon) + tform (golden hour) survived; tferry (sun -6 deg night),
  tfog (blue hour + volume-scatter fog), tgreen (noon) did not.
- E3. tfog_2: the fog volume under the bright Cycles sky washes 5+ of
  12 frames to near-white (S4/S5/S7/S8/S10 unreadable).
- E4. tgreen_2: noon renders as flat overcast — no sun shadows at all
  (tgreen_1 certified AgX-noon with hard shadows).
- E5. tsquall_2: storm-dark base right, but the certified bright-storm-
  sky + wet-ground sheen (glossy floor reflection of the sky) dimmed.
- E6. The vendored walk clip (2899.fbx) imports a 65-bone mixamorig
  armature with NO skin — the x_bot.fbx rig MESH is not in it.

## Root cause statement

The per-film worlds were tuned and certified UNDER EEVEE (s14-s19: the
night laws, the AgX-noon tune, the blue-hour verdict sky1.0/lamps0.40/
fog0.05->0.028). The s25 CYCLES ENGINE LAW (skinned crowds OOM EEVEE —
measured, correct, staying) changed the RENDERER without re-deriving the
worlds. Nishita sky luminance at/below the horizon differs drastically
between engines; volume scatter compounds it (E3); the noon sun/shadow
loss (E4) needs its own measurement (sun lamp vs sky strength split).

Law this writes (kit level): **A RENDER-ENGINE SWAP INVALIDATES EVERY
PINNED LOOK TUNE — a look verdict carries its engine id; swapping the
engine re-opens the tune.** (Extends the s24 render-encoding law family.)

## D1 — the kit-level world law (design)

Decision D1-a: NO automatic engine compensation inside add_sky_world
(magic rescaling hides the physical story: a -6 deg Nishita sun in Cycles
is a DIFFERENT lighting situation, not a scaled one; films must re-derive
pools/silhouette/fill per the existing L-TF4 ladder discipline).

Decision D1-b: films carry EXPLICIT per-engine world params in their own
world modules (the pattern already exists: tsquall_world_look.py /
tfog_world.py / tform_world_look.py probe lanes). Each affected film's
world module gains a CYCLES tune block (strengths/exposures/fog density),
measured via its world_look lane + image_metrics + the eye, pinned with
numbers in the module comment (the s24 law: pin the law in the module).

Decision D1-c: the kit gains ONE helper — `engine_id(scene)` already
exists (normalize_engine_id); the new piece is `cycles_world_note()` — no.
Actually: the kit gains NOTHING structural. The world modules already
receive the engine argument (they can read scene.render.engine). The kit
change is DOCUMENTATION + the probe-lane contract: each film's world_look
lane must run BOTH engines and print the side-by-side delta when a look
verdict is pinned. SKILL/kb carry the law.

D1 rejection record: an automatic strength compensation was considered
and rejected (it would have "fixed" tfog by dimming the sky but the fog
density ALSO needs re-derivation — two coupled knobs need eyes on them;
an auto-scalar would have shipped a plausible-looking wrong fog).

## D2 — the rig reconstruction (unblock; mechanical, gate-checked)

RH-3d-assets is unreachable this session (the beulahkemp PAT died with
the wiped sandbox; checked: PAT repo list, release volumes, the vendored
clip's contents per E6). The staged packages carry 102-136 BOUND rig
assemblies each (scene.glb). Reconstruction: extract ONE assembly
(armature + its skinned meshes) from a staged scene.glb, rename meshes
to Beta_Joints/Beta_Surface (+ armature to the family's expected name),
restore the bind pose (inverse-bind matrices -> rest matrices), export
as FBX named x_bot.fbx, and serve it to humanoid_crowd.crowd_family via
RH_ASSETS. Acceptance gates (all existing): POLY_BAND (2000-3500
combined verts), RIG_HEIGHT 2.051 measured band, the direct same-name
bind (mixamorig:65 = the clips' bones), prepare_template probe, ONE full
bind_crowd + motion_gates on tdawn (the certified film — a reconstruction
that binds tdawn's 129 rigs with gates green is proven).

Risks: R1 GLB round-trip weight fidelity (acceptance: motion gates);
R2 decimation state of the staged meshes (acceptance: POLY_BAND — if the
staged meshes are OUTSIDE the band, the band documents the ORIGINAL and
the reconstruction records its own measured band as a sanctioned delta,
noted in the ledger); R3 scale drift (acceptance: RIG_HEIGHT probe);
R4 bind-pose recovery errors (acceptance: the bind probe + gates).

Decision D2-a: reconstruct from tform_3's scene.glb (the byte-exact-
repro film; 102 rigs; known-good payload 9024057c lineage).

## D3 — the per-film re-tune procedure (4 films: tferry, tgreen, tfog, tsquall)

Per film, in the film's own world module + look lanes:
1. Bake the crowd cache (venv, native, seconds).
2. Render the world_look probe set under CYCLES at previz res (the
   existing lane) + the 12-shot stills set.
3. Tune with the eye + image_metrics (the s24 calibration discipline:
   measure the corpus, pick the separating statistic) until the certified
   look's STORY reads (tferry: sodium pools + near-black sky; tfog:
   blue-hour + readable fog depth; tgreen: noon sun + hard shadows;
   tsquall: storm sky + wet sheen).
4. Pin the numbers in the module comment; run the look lane under BOTH
   engines and record the delta (D1-c).
5. Re-export the package (the canonical exporter), gates green.
6. Re-stage + app-repo commit in the SAME micro-step (the STAGE-COMMIT
   law). Package rev bumps: tferry_3, tgreen_3, tfog_3, tsquall_3.

Decision D3-a: stills stay 640x360 Cycles samples-24 (the s25 shape) —
the fix is the WORLD, not the sampler.

Decision D3-b: the export chain runs per film AFTER its tune lands
(no batch re-export — each film's tune is eye-in-loop, mine).

## D4 — the re-ship path

Order: D2 rig (unblocks everything) -> D1 law text + kb -> per-film
D3 tunes (tferry first — the cleanest repro) -> re-exports staged ->
the eye gate RE-RUNS on the four films (the same sheets pipeline) ->
HANDOFF/PLAN/worklog updates.

## What this wave does NOT do

- No re-render of tdawn_4/tform_3 (certified; their packages stay).
- No EEVEE-vs-Cycles A/B of the exporter path (the s25 export round is
  orthogonal; the exports re-run only to carry the fixed worlds).
- No night-market design here (D5 separate doc after D1).
