# DESIGN_humanoid_rollout_s25.md — the humanoid rollout to all films + the collision/nav round

> Session-25 design (REV-2 — the audit folds; REV-1's force-field
> section was re-derived on corrected engine truth, see §0a). The user directives driving this doc:
> (1) "apply to other films" — the humanoid crowd layer goes to the
> five non-humanoid films; (2) "make sure you also get the latest kits
> ... dog-food the latest" — port the s42 upstream improvements;
> (3) "many of your crowd animation walk straight through some
> obstacles which should be generally avoided" — the collision/nav
> round; (4) "make sure all the animation replacements (with humanoid)
> ... polished and visual issue free" — the full visual gate per film.
> Companion: docs/DESIGN_humanoid_crowd.md (D6 REV-2, the tform_2
> worked example — the layer itself is NOT redesigned here).

## 0. The recovered facts this design stands on

- The humanoid layer is KIT-LEVEL: `scripts/humanoid_crowd.py`
  (crowd_family / prepare_template / bind_crowd / bind_principals /
  motion_gates). tform_scene._humanoid_layer is the worked example.
- **tform_2's PACKAGE IS LOST** (the third GIT-IS-THE-DISK casualty):
  the app repo (previz-review) origin tip is 844ed3a = tform_1; the
  tform_2 staging was live-only, never committed. The committed chain
  (bake scripts + humanoid layer + runners) rebuilds it
  deterministically. LAW (new, enforced this session): **the app repo
  gets a staging commit in the SAME micro-step as the stage**.
- The five films share the anchor contract
  (`_crowd_anchors -> {"zombies": {"crowd": [...], "chase": [...]}}`)
  and the kit-mode loader; their caches rebuild from committed bake
  scripts (tdawn/tferry/tgreen/tsquall/tfog_bake.py).
- All five films have keyed capsule heroes (the branch-a law applies:
  UAL principal rides the hero root, hero mesh becomes a carrier).
- Engine truth (crowd-kit, live-measured s41/s42 + crowd-kit issue
  #15 OPEN with 8 gaps): NO path planning (point-target only; an
  obstacle fully across a spawn->destination line = total jam);
  pressure-soft pushout (agents penetrate up to ~0.59 m under jam);
  crowd_obstacles.py is the scene-geometry -> Blocked bridge.
- **The force-field truth (REV-2 correction — the audit's P0-1/P0-2,
  both verified against the trees)**: the bake wiring is LIVE at the
  vendored pin b4bf76e (`bake.py:81` import, `:874-891`
  `_disposition_force_fields`, `:989-1040` the IR hand-off; f7688a6
  "stale inertness docs superseded" is an ancestor) AND at the
  standalone HEAD. tfog_bake.py:158-181 already authors a DANGER
  field whose recoil probe passes because fields are live. The s41
  bridge docstring's "inert" claim is STALE DOC (superseded in-code).
  REV-1's pin-bump-for-fields rationale is DEAD (zero functional
  gain) and the probe-as-designed would misfire. What actually needs
  measuring: per-film REPULSION adoption on V2 scenes, where
  behavior controllers make fields ADVISORY-ONLY (`bake.py:995-1006`)
  and the t_active=45 s trap can read false-RED (issue #7).
- **The bake lane does NOT run the vendored pin (the audit's P0-2)**:
  the film bake drivers bootstrap the STANDALONE clone
  `/home/z/lab/blender-crowd-kit` (HEAD 92e5f33) + escape-previz
  (tfog_bake.py:49-61, tsquall_bake.py:60-68); tdawn/tferry/tgreen
  hardcode /home/z/work with a sibling fallback. `import scripts.crowd`
  resolves to the standalone. Consequence: the submodule pin is
  irrelevant to the bake lane; determinism rides the per-bake payload
  pins + a RECORDED WHEEL SHA per film (the venv wheel 1.6.0, pin-era,
  is what the engine actually loads). NO pin bump this session.

## D1 — The kit dog-food port (upstream s42 -> vision-kit)

The upstream agent-kit s42 nav-lane friction round (db0142d + aca3634
+ a17c4e7) postdates the s24 vendor round. Drift measured this
session:

1. `scripts/crowd_obstacles.py`: 127 diff lines — the doc corrections
   (issue #15 gap numbering, the saved-blend scan recipe), the
   Walkable boundary validation at the kit boundary (nav-F7:
   flat/inverted/NaN bounds previously died as a bare unpack
   ValueError deep in the clip loop).
2. `scripts/crowd/__init__.py` re-export: agent-kit s42 is a 30-name
   surface; vision-kit pins 24 (+4 sanctioned deltas documented).
   Port = adopt the 30-name surface + re-derive the sanctioned-delta
   note (VK's +4 authoring names stay documented in lockstep).
3. `vendor/blender-crowd-kit` submodule pin: NO BUMP (the audit's
   P0-1/P0-2: the fields wiring is already at the pin; the bakes run
   the standalone anyway). The pin advances only at a WRAP-time sync
   round with its own receipt, per the s22 law.

Port discipline: zero-drift vendored rounds with the sanctioned-delta
notes re-derived, battery green before close (the M16 law).

## D2 — The collision/nav round (film-lane scope; engine gaps stay filed)

**Ownership split (the user's law, refined by the s22 HANDOFF queue):**
- crowd-kit ENGINE gaps (path planning, hard walls, animated
  obstacles) = issue #15, OPEN upstream, the engine lane's own
  receipts say "NO feature work" — NOT reimplemented in the film
  lane. The upstream request EXISTS; this session ADDS the
  fields-seam evidence to it (comment on #15) if the probe proves
  the seam.
- FILM-LANE gaps (which obstacles the sim knows about) = OURS. Fix
  per film THIS session.

**The film-lane fix, per film (REV-2 additions folded):**
1. Census the film's statics that agents plausibly cross (colonnade
   walls, kiosks, stalls, benches, the drum, platform furniture,
   gate pylons, board) — the placed mesh collections.
2. Run the crowd_obstacles `scan` (Blender-side, --collection /
   --prefixes, z-band law) -> Blocked rects.
3. Wire the rects into the film's bake authoring
   (`CrowdScene(blocked=...)`) — contract-authored rows (the
   contract stays authoritative; the scan EMITS the rows, the film
   module PINS them as data, keeping the bake deterministic).
4. The JAM law: review each film's spawn->destination pairs against
   the new rects — an obstacle fully across a line routes nobody.
   Adjust destinations/spawn rows in the CONTRACT where needed
   (film-story authority; the layout intent stays).
5. Re-bake -> new payload pins per film (the byte-determinism claim
   moves to the NEW pin; documented per film).
6. Verify (REV-2, the audit's P1-4): the CACHE-SIDE violation scan
   is `crowd_look.py` (the nav lane's cache-decode arm), NOT
   crowd_obstacles (which scans SCENE geometry pre-bake); zero-
   violation target on the declared rects + **the arrival/state
   delta gate**: per film, the arrival counts and per-agent state
   distribution at the NEW pin vs the old recorded bake — a rect
   that seals a spawn->destination line total-jams a population
   while the geometry scan stays green (the no-path-planning
   engine truth); the arrival delta is the tripwire that catches
   it. THEN crowd_look nav encodings + the stills eye pass.

**The force-field adoption measurement (REV-2 — replaces the dead
pin-vs-HEAD probe):**
- Per film that adopts REPULSION: one measurement bake on the film's
  OWN scene (V2 semantics — fields are ADVISORY-ONLY under behavior
  controllers, bake.py:995-1006) with the field t_active span
  covering the film's FULL tick range (the 45 s trap), vs the same
  bake without the field. Measure: mean trajectory bend around the
  obstacle cluster + penetration telemetry. Adopt where the bend is
  material (>half a personal-space radius at the cluster approach);
  record both payloads in the film receipt.
- The wheel under test is NAMED in the receipt (venv 1.6.0 sha) per
  the audit's Q1 answer — a GREEN/RED without the wheel identity is
  meaningless.

## D3 — The humanoid rollout (five films + the tform rebuild)

**Per-film humanoid layer (the tform pattern, film-authored):**
- Env gate `<FILM>_HUMANOID=1` (TFORM_HUMANOID precedent) — rev N
  stays reproducible without the layer; the humanoid rev flips it.
- POP_PLAN tint groups per film story (count-split by population
  ordinal, the ingest reorder law: attribution by COUNT from the
  static table, never by slice). Proposed palettes (story-first,
  eye-tuned at the still pass):
  - tdawn (terminal dawn, the exodus): muted cool commuters + one
    warm-staff group at the gate; heroes keep their identity colors.
  - tferry (LAST FERRY, night deck): deckhands' ink + passenger
    drab + the crimson Latecomer / amber Deckhand as UAL principals.
  - tgreen (GREEN LIGHT, noon crossing): the x-sign stream split
    (two stream tints), statue+runner heroes as UAL principals.
  - tsquall (SQUALL, storm market): vendor tarp colors + the queue
    group; the slip faller is rigged with the documented gate
    exemption (below — the audit's Q2 correction).
  - tfog (THE EXPRESS, blue-hour platform): platform drab + rail
    staff; the heroes per tfog's cast block.
- RB placeholders (REV-2, the audit's P1-1): the rb_exclusions
  parameter is DROPPED — every film authors chase RB slots at
  exactly (2,5,8) (verified in all five scene modules + tform), so
  the universal default IS the per-film truth. The
  `from crowd_v6.contract import RB_FALLS_V3` import (an
  escape-previz dependency — the clone-seam hazard) is replaced by
  a LOCAL constant + a fail-closed assert: the film's Zed.RB.*
  anchor count must equal len(RB_FALLS_V3) (mismatch = the bake
  pairing moved; refuse loudly).
- Heroes: bind_principals per film's cast (the Idle_Loop +
  film UAL_SCALE + identity tints), hero mesh -> degenerate carrier.
- Motion gates run per film (the s20 two-column law; the anchor
  gate + the bob gate with 5 samples). REV-2 (the audit's P2):
  tsquall's SLIP FALLER is a cache agent (scene_squall.py:507-519)
  and WILL be rigged — its hips-bob gate is special-cased under
  the film's tumble overlay (a documented exemption row, not a
  silent skip).
- **The flowstrip/filmstrip rig-body override is NEW per-film work
  (REV-2, the audit's P1-2)**: the committed tform_flowstrip dot-
  override targets the Zed.* anchors — which the humanoid layer
  turns into 1-vert carriers; the strips would go BLANK. The
  override is re-derived (name-prefix find of the rig bodies +
  object-level slot links, position-free — no camera table needed,
  the audit's Q3), lands as a KIT-LEVEL helper all five films +
  tform share, and gets the A2 code review before the first strip
  render.
- **Per-film ingest-order tripwire (REV-2, the audit's P1-3)**:
  the count-split palettes ride ingest order; tfog pins the law
  (spawn-table = add order + N_CACHE tripwire). The other four
  drivers get the same documented alignment BEFORE their POP_PLAN
  palettes land.

**Cache/speed/phase channels**: the five films' bakes carry the
tick speed channel (clip_source="speed"); the K1 tick phase channel
exists only where layout layers were authored (tform). The films
take the LOUD ordinal-stride fallback (module-designed, warns) —
the walk variety comes from the speed-channel clip split (walk vs
idle) + per-agent wrap phase from the ordinal law. ACCEPTED for
this rollout (documented per film report); layout-layer phase
re-derivation stays a tform-era capability, not a rollout blocker.

**Versions**: tdawn_4 / tferry_2 / tgreen_2 / tsquall_2 / tfog_2 /
tform_3 (humanized + obstacle-aware; the bake changes -> the payload
pin moves; the rev-2 rebuild receipt documents the loss honestly).

**Runners**: the tform laws port to all five stills/filmstrips
runners — the CYCLES ENGINE LAW (skinned crowds OOM EEVEE; the
_set_engine normalizer + CPU + denoise), the rig-body flowstrip
override (dots win at OBJECT level on the rig bodies), the hide
filter (name check, no bpy_types import), the filmstrip crowd
override law. Export: the DEGENERATE CARRIER law holds everywhere
(anchor identity survives gates 17/24); the per-group mesh-data
tint law holds everywhere.

## D4 — The verification gauntlet (per film, fail-closed)

1. Bake gates: n_agents pins; payload pin recorded at the new rev.
2. Humanoid gates: motion_gates PASS (anchor/cache-xy/bob) + bind
   report numbers in the receipt.
3. Obstacle gates: the declared-rect scan on the baked cache —
   zero violations on declared rects (the penetration telemetry is
   REPORTED; the soft-pushout residual is a known engine class —
   documented, not hidden).
4. Stills: 12/12 Cycles golden/night/fog regimes, EYE-certified by
   the principal (the vision-native law — the principal looks at
   every frame; sub-agents do non-visual QA only).
5. Filmstrips: 96 strips, the rig bodies visible (the override law).
6. Export: all gates green (the newest exporter), GLB size sane
   (~0.27MB/agent decimated + the principals).
7. Stage + the app repo COMMIT (same micro-step) + browser smoke
   (the viewer plays the skinned crowd) + the comment mirror export.

## D5 — The orchestration map (sub-agent lanes)

- A1 (audit): DONE (GO-WITH-CHANGES; both P0s + 5 P1s + 3 P2s
  folded into this REV-2).
- A2 (code review): the humanoid_crowd amendments + the kit-level
  strip-override helper + the first film layer, before the first
  bake consumes them.
- B-lane (non-visual QA per film): bake receipts, gate outputs,
  scan JSONs — sub-agent verifiable.
- The principal keeps ALL visual verdicts (the M5 division of
  labor) + the orchestrator-level probes.

## Audit answers (closed)

- Q1: the bakes never consult the vendored pin (P0-2) — determinism
  rides the per-bake payload pins + the recorded wheel sha per
  film. The pin-bump risk question is moot this session.
- Q2: there ARE no RB slip performers — the slip is a cache-agent
  faller + film tumble keys; the faller is rigged with the
  documented gate exemption (D3).
- Q3: no camera table needed — name-prefix find of the rig bodies
  + object-level slot links; the tform source was never committed
  (§0), so the helper is re-derived fresh + A2-reviewed.
