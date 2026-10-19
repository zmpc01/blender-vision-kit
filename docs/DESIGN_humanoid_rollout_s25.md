# DESIGN_humanoid_rollout_s25.md — the humanoid rollout to all films + the collision/nav round

> Session-25 design (REV-1). The user directives driving this doc:
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
- **The force-field seam discovery (this session)**: at the vendored
  pin b4bf76e the ENGINE has the seam (sim.rs:712
  `apply_field_bias`) but the PYTHON bake never calls
  `split_bake_fields` (fields inert — what the s41 doc measured).
  At crowd-kit HEAD (92e5f33, 131 commits ahead of the pin) the bake
  wiring EXISTS (`_disposition_force_fields` -> `kwargs["force_fields"]
  = _eligible`). REPULSION/DANGER fields compile into IR at both.
  => A pin bump may light up real steering. PROBE FIRST (D2).

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
3. `vendor/blender-crowd-kit` submodule pin: b4bf76e -> decision in D2
   (bump only with the probe green + the wheel ABI check).

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

**The film-lane fix, per film:**
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
6. Verify: the crowd_obstacles scan re-run on the BAKED cache
   (zero-violation target on the declared rects) + crowd_look nav
   encodings (the s24 lane) + the stills eye pass.

**The force-field probe (before any pin decision):**
- Tiny scene: one Blocked rect + one REPULSION field on the line;
  20 agents; bake at the PIN (fields inert expected) and at a
  TEMP checkout of HEAD's bake.py over the pin's engine (the wiring
  is python-side). Measure: mean trajectory bend around the field
  center + penetration depth.
- GREEN (agents bend, wheel parses the IR): bump the pin to the
  commit that wired the bake (92e5f33 or the minimal ancestor),
  re-run the wheel ABI check (the manylinux wheel at HEAD
  ce485ead 18,035,558 B), adopt REPULSION fields per film for the
  top obstacle clusters (the biggest penetration risks).
- RED: keep the pin, document, Blocked-only per film, and the issue
  #15 comment carries the measured result instead.

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
    group; the M5 slip performers stay RB (never rigged).
  - tfog (THE EXPRESS, blue-hour platform): platform drab + rail
    staff; the heroes per tfog's cast block.
- `bind_crowd(ctx, fam, group_tint, rb_exclusions=None)`: NEW
  optional parameter — the RB placeholder chase indices are
  FILM-SPECIFIC (escape's RB_FALLS_V3=(2,5,8) is not universal).
  Default stays RB_FALLS_V3 (backward compat); the film modules pass
  their own. The `from crowd_v6.contract import RB_FALLS_V3` import
  goes LAZY (only when the default is used) — the clone-seam law
  (that import is an escape-previz dependency).
- Heroes: bind_principals per film's cast (the Idle_Loop +
  film UAL_SCALE + identity tints), hero mesh -> degenerate carrier.
- Motion gates run per film (the s20 two-column law; the anchor
  gate + the bob gate with 5 samples).

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

- A1 (audit): THIS design doc, fresh context, attack mandate — the
  P0s come back before implementation.
- A2 (code review): the bind_crowd rb_exclusions change + the per-
  film layer modules, after implementation, before the first bake.
- B-lane (non-visual QA per film): bake receipts, gate outputs,
  scan JSONs — sub-agent verifiable.
- The principal keeps ALL visual verdicts (the M5 division of
  labor) + the orchestrator-level probes.

## Open questions for the audit round

- Q1: does the pin bump risk the film bakes' determinism story
  (the wheel ABI change re-orders float paths)? Mitigation: the new
  pins are recorded per film regardless; the bump happens BEFORE
  the six bakes, never mid-family.
- Q2: tsquall's RB slip performers — rig or not? Proposal: NEVER
  (they are physics performers; rigging a ragdoll is a D6 scope
  breach). The audit may know a better read.
- Q3: the filmstrip dot override on rig bodies needs the bodies'
  world positions at strip time — the tform implementation is the
  source; confirm it ports without the per-film camera table
  knowledge.
