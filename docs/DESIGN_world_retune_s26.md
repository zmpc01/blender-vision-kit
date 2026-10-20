# DESIGN — s26: the Cycles world re-tune wave (+ the rig reconstruction unblock)

Status: REV-2 (audit round 1 folded: GO-WITH-CHANGES, 1 P0 + 6 P1 + 6 P2 + 7 P3 — all folded below with [A#] tags). Owner: session-26 orchestrator.
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

Decision D1-c [A6]: the both-engine delta is ENFORCED in the pin flow —
a film's CYCLES tune block is not "pinned" until its world module carries
a recorded BOTH-ENGINE delta line (the E1-style A/B numbers measured on
the FILM LOOK, D3's surface). A tune block without the delta line fails
the fold review (the s24 fail-open class: computed-printed-never-enforced
— here the enforcement site is the tune-block format itself: a missing
delta line is a visible, checkable absence in review). Softening rejected.
[A3] The tune surface is the FILM SCENE MODULE at certified settings
(the stills-runner invocation), NOT the world_look preview lanes — two
lanes hardcode EEVEE + private ladders (tfog's lane lamp 0.025 vs the
film's 0.40, its own strength-1.4 preview world) and two films have no
lane at all (tferry/tgreen). The lanes are DEMOTED to the D1-c delta
contract: they gain an --engine flag and render the film's own world
constants (or are rewritten to); they never substitute for the film look.
[A7] The per-film mechanism→knob map (the knob homes are NOT uniform):
  | film | broken mechanism | knob home |
  |------|------------------|-----------|
  | tferry | Nishita sun -6deg luminous in Cycles | sky strength in tferry_world.build_world (:251-255) + hardcoded spot/area energies (:290-341) |
  | tfog | flat background-color world + volume scatter + practicals under bright-sky-independent but scene-pinned values | SKY in tfog_scene.py (:783-795 TFG.BlueHour strength 1.0 — the SCENE module, not tfog_world!), lamps tfog_scene (:775-795), fog density tfog_world.py:65 (TFOG_FOG_DENSITY 0.028) |
  | tgreen | noon sun/shadow loss | tgreen_world.py sun block (:46-49) + module ladder constants (:292-305) |
  | tsquall | storm sky + wet sheen (EEVEE SSR envelope vs Cycles raytraced reflections) | scene module sky/lamps + the deck material roughness/reflection story (the SSR trace_max_roughness 0.5 class) |
[A12] The reference corpus per film = the film's EEVEE-era certified
package stills (previz-review/public/packages/<film>_1 or the certified
pre-humanoid rev) + their image_metrics stats — the CYCLES ladder
converges toward THAT corpus, measured, not vibes.

D1 rejection record: an automatic strength compensation HIDDEN INSIDE
add_sky_world was considered and rejected (it would have "fixed" tfog by
dimming the sky but the fog density ALSO needs re-derivation — two
coupled knobs need eyes on them; an auto-scalar would have shipped a
plausible-looking wrong fog). [A13f] The rejection does NOT cover a
MEASURED, EXPLICIT, module-local per-engine seed table (printed, from
the E1-style A/B) — films MAY adopt one to cut the ladder cold-start;
the numbers stay visible in the module. tfog's mechanism correction:
its sky is a FLAT BACKGROUND COLOR (not Nishita) — the root-cause
mechanism named in Evidence is the tferry case; tfog's white-out is the
volume scatter + practicals interaction measured under Cycles (E3), and
its knobs live in the scene module per A7.

## D2 — the rig reconstruction (unblock; mechanical, gate-checked)

RH-3d-assets is unreachable this session (the beulahkemp PAT died with
the wiped sandbox; checked: PAT repo list, release volumes, the vendored
clip's contents per E6). The staged packages carry 102-136 BOUND rig
assemblies each (scene.glb). Reconstruction: extract ONE assembly
(armature + its skinned meshes) from a staged scene.glb, rename meshes
to Beta_Joints/Beta_Surface (+ armature to the family's expected name),
restore the bind pose (inverse-bind matrices -> rest matrices), export
as FBX named x_bot.fbx (add_leaf_bones=False [A13c]), and serve it to
humanoid_crowd.crowd_family via RH_ASSETS — then COMMIT it as the
repo-local fallback [A2]: vendor/rh_rig/x_bot_reconstructed.fbx + a
sha256 + the committed extraction script, and crowd_family gains the
same env-wins/repo-fallback pattern the clips already have (the rig is
now load-bearing for five films; the next sandbox wipe must not re-block
the lane). Ledger the sanctioned delta.

[A1 — THE P0] prepare_template currently DECIMATES UNCONDITIONALLY at
ratio 0.14 before the POLY_BAND check (humanoid_crowd.py:116-156) — the
staged assemblies are ALREADY the post-decimate bind copies (combined
2000-3500 by construction), so 0.14 x ~2500 ≈ 350 verts would fail the
band deterministically and D2 dead-locks at step one. Kit amendment:
a deterministic pre-decimated path — if the raw imported combined verts
already fall inside [POLY_BAND[0], POLY_BAND[1]], SKIP decimate, record
"pre_decimated": true + the measured band in the report (numbers travel),
keep the sub-band hard fail. Update the module docstring + the
DESIGN_humanoid_crowd.md D6-4 note.

Acceptance gates (amended [A5], committed as a script + battery row
[A10] — humanoid_crowd has ZERO test coverage today; "presumed broken"):
G1 POLY_BAND via the pre-decimated path (measured band recorded);
G2 RIG_HEIGHT 2.051 measured band;
G3 the direct same-name bind census (mixamorig:65 = the clips' bones;
bind_crowd's census is subset-based so FBX leaf bones would pass
silently — add_leaf_bones=False keeps the claim clean [A13c]);
G4 ONE full bind_crowd + motion_gates on tdawn (129 rigs, gates green);
G5 MESH-VERTEX world-delta across one cycle for one bound agent —
catches weight/modifier loss that pose-bone gates cannot see (a statue
renders rigid while bind+gates go green);
G6 per-joint world-matrix diff, reconstruction vs the vendored 2899.fbx
clip driven at the same frame — pinned tolerance band (catches scale/Rz-
flip/bone-local-frame drift that hips-bob gates miss; anti-phase and
180-degree-backwards rigs pass G4's bob equally) — verify the 5.2 glTF
importer's bone-rest heuristic (posed node transforms vs inverse-bind
matrices) BEFORE trusting the rest recovery [A5b];
G7 the extracted meshes' tform group materials CLEARED (the no-tint
bind path must not leak pink) [A13d].
Mesh rename mapping (Body0->Beta_Joints / Body1->Beta_Surface) is
verified against prepare_template's printed per-mesh vert counts
(humanoid_crowd.py:153-154) [A13b]. The armature NAME is NOT a contract
(prepare_template takes the last imported armature) — no rename needed
[A13a].

Decision D2-a: reconstruct from tform_3's scene.glb (the byte-exact-
repro film; 102 rigs; known-good payload 9024057c lineage).

Risks (amended): R1 GLB round-trip weight fidelity (G5 catches);
R2 the staged meshes are in-band (the P0 — A1's pre-decimated path);
R3 scale/flip drift via the wrapper chain (FILM_HEIGHT/2.051 scale +
Rz(pi) compose into parent-inverse — G6 catches); R4 rest-pose recovery
(G6 + the importer-heuristic check).

## D3 — the per-film re-tune procedure (4 films: tferry, tgreen, tfog, tsquall)

Per film, on the FILM SCENE MODULE at certified settings [A3] (not the
preview lanes):
1. Bake the crowd cache (venv, native, seconds) AND compare the fresh
   bake's 8-hex pin against the film's recorded payload receipt (tdawn
   fb50b6b9 / tferry 9ae53649 / tgreen d9e2f234 / tsquall 2457bf87 /
   tfog 6b5b4313) BEFORE tuning — a moved pin = an accidental contract
   edit; STOP the film [A9].
2. PURGE output/<film>/stills first — the runners skip existing stills,
   a literal re-run re-renders nothing and the wave certifies stale
   broken images [A4]. Require the re-stage to copy a freshly
   timestamped set.
3. Render the 12-shot stills under CYCLES at previz res; tune the
   film's own world/lamp/material constants (the A7 knob map) with the
   eye + image_metrics converging toward the A12 corpus until the
   certified look's STORY reads (tferry: sodium pools + near-black sky;
   tfog: blue-hour + readable fog depth; tgreen: noon sun + hard
   shadows; tsquall: storm sky + wet sheen).
4. Pin the numbers as LOWERCASE in-module constants (the s32 discovery
   taxonomy — new unmapped uppercase constants fail the export
   fail-closed) with the BOTH-ENGINE delta line (D1-c, A6) recorded from
   the E1-style A/B on the film look.
5. Re-export the package (the canonical exporter), gates green. EXPECT
   previz.json world/lights/atmosphere blocks to change (_collect_world
   reads sky params + light energies; _collect_atmosphere reads fog
   density) — optionally assert the exported energies equal the pinned
   tune numbers [A8]. Filmstrips are WORKBENCH (world-blind) and need NO
   re-render [A8].
6. Re-stage + app-repo commit in the SAME micro-step (the STAGE-COMMIT
   law). Package rev bumps: tferry_3, tgreen_3, tfog_3, tsquall_3.
7. Browser playback smoke per re-exported film (new GLBs, same
   24fps law) [A13g].

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
