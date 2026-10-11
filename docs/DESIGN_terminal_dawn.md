# DESIGN — TERMINAL DAWN (session 12, the vision-native build)

> The session-12 film: a FROM-SCRATCH previz short built with the
> blender-vision-kit by a vision-native agent, dog-fooding the
> blender-crowd-kit for the crowd, exported to previz-review as
> package `tdawn_1` for A/B against Last Ride Out v3_4..v6_1.
> This doc is the design-of-record; the build log lives in worklog.md.

## 1. Concept

**TERMINAL DAWN** — 45 s @ 24 fps, 1080 frames, 12 shots.

Dawn. A grand railway terminal. The city outside is silent in the
wrong way, and everyone in the hall knows what silence means. The
surge toward the last gate out builds from a morning trickle into a
wall of bodies. Two figures carry the story against that wall:

- **The Master** (amber capsule) — station staff at the Gate. Holds
  the line as long as the vault stays open. Visible from f1.
- **The Runner** (teal capsule) — enters at the far end AFTER the
  surge ignites, and pushes AGAINST the flow — the only body in the
  hall moving the wrong way — to reach the gate before it seals.

The threat is never shown. No monster, no explosion: the storytelling
carries entirely on crowd pressure, light, and the two heroes. This is
the deliberate break from Last Ride Out (whose threat is literal
zombies + a jeep): the spin is that the CROWD is the antagonist.

### Why this concept (decision D-TD1)

The crowd-kit previz bridge (`scripts/crowd/previz_bridge.py`)
hard-pins the integration shape: crowd agents spawn in zone bands and
PURSUE `hero_pos` = world origin (capacity ±5 m), 12 Hz sim, 541
ticks, 24 fps, 1080 frames. Last Ride Out used that shape as "horde
converges on the jeep". TERMINAL DAWN re-reads the SAME motion
grammar as **commuters converging on a gate** — zero bridge code
changes, a completely different film. The 9-deep chase tail
(Zed.Chase01..09) reads as the sprinting tail-enders; the 3 RB-slot
placeholders (Zed.RB.Chase03/06/09) become grounded luggage carts.
The 45 s/1080-frame footprint matches every previous package 1:1, so
the review-app A/B stays apples-to-apples.

## 2. Architecture (who owns what)

```
blender-vision-kit (THIS repo)
  scripts/scene_terminal_dawn.py     the scene module (build+animate+emit)
  scripts/tdawn_contract.py          the crowd contract (duck-typed, bridge-shape)
  scripts/tdawn_bake.py              headless bake driver (venv, pure CPython)
  scripts/tdawn_world.py             environment builder (hall, gate, board, light)
  scripts/tdawn_stills.py            per-shot still renderer (EEVEE, one process/shot)
  output/tdawn/                      build + look artifacts (not committed)
  docs/DESIGN_terminal_dawn.md       this doc

blender-escape-previz (PATH-LOADED, not modified)
  scripts/crowd_kit/                 the `kit`-mode crowd plugin (ENGINE record,
                                     loader, gates, clips, contract)
  scripts/crowd_v6/                  shared sim loader + cache naming + gates

blender-crowd-kit (read-only)
  scripts/crowd/previz_bridge.py     ingest_contract → bake → to_previz_cache

blender-agent-kit (read-only)
  scripts/export_previz_package.py   the canonical exporter (schema 2.3)

blender-crowd-kit scripts/previz_kit_export_wrapper.py
                                     the binding-law wrapper (anchors the
                                     previz superset blender_kit copy)
previz-review
  public/packages/tdawn_1/           the staged package (the deliverable)
```

### The contract (tdawn_contract.py)

Duck-typed per previz_bridge._REQUIRED_CONTRACT_ATTRS. The world is a
long hall along +Y: `CROWD_X_RANGE = (-10, 10)`; spawn zones are three
bands y ∈ [8, 26] (far-band-FIRST — the chase tail spawns in
zones[0]'s strips, so the tail-enders start deepest);
`flee_target` lands at (0, 26) — inside the far band; the pursue
target `hero_pos` (0,0) is the GATE. Columns + carts inside the
walkable are declared as `BARRICADES` (the bridge makes them Blocked
squares — agents route around, never through).

Population speed distributions are MUTATED post-ingest via
`dataclasses.replace` (the classes are frozen; my bake driver owns
the chain, constants hard-coded — D-TD2): far zone (μ=2.0, σ=1.0)
≈ mixed walk/jog; near zones (μ=1.75, σ=0.75) ≈ 47% sprint at the
1.8 m/s clip band; chase tail (μ=3.8, σ=0.4) all-sprint with
μ+3σ = 5.0 ≤ the populations[0] max_speed envelope (5.0).
CAM_KEEPOUTS_V3 = ground-level shot cams only — high/aerial cams get
NO keepout (the D6 clamp is 2D-xy; a keepout under an aerial punches
a visible hole in the crowd).

### REV-2 folds (peer review TD-REVIEW-1, all adopted)

1. **N=129 (120 crowd + 9 chase), density via geometry** — the loader
   fail-closes on `n_agents != crowd_v6.contract.N_RELEASE (129)`
   (crowd_kit/loader.py:234-244); the anchor arithmetic (120 Zed.NNNN
   + 12 chase) only adds up at 129. The hall shrinks to 24×40 m
   (floor x ±12, y -8..32); zones y ∈ [8, 26]; the ±5 m gate plaza
   funnels 129 agents into a REAL jam (~1.65 agents/m² at the seal).
   GLB ~20 MB (v6_1 parity), 1:1 A/B preserved, zero kit forks.
2. **D-TD2 corrected**: (μ,σ) tuples only (no lo/hi — the distribution
   is an untruncated normal); frozen dataclasses → `dataclasses.replace`;
   deterministic hard-coded constants (an unseeded RNG would drift
   params_sha); chase μ+3σ ≤ zone0 μ+3σ (max_speed reads
   populations[0] only — cosmetic overflow, documented).
3. **D-TD4 corrected**: THREE RB slots (CHASE_RB_INDICES = (2,5,8));
   the 3 carts sit OUTSIDE the walkable OR are declared BARRICADES.
4. **Export-contract surface** (was missing entirely): 12 timeline
   markers bound to CAM_S* at each shot f0 (the exporter hard-fails
   without markers); `SHOTS_V3` rows (id, f0, f1, intent);
   `CAMS_V3` rows are 7-TUPLES (name, loc0, loc1, lens_mm, aim,
   parent_jeep, shake_amp); `CAST` with explicit roots + hero
   materials named `CA.Body.TD.Master` / `CA.Body.TD.Runner` (the
   identity-color registry reads CA.Body.*); tdawn_contract is
   module-imported, NEVER star-imported (the unmapped-story-constant
   gate fail-closes on uppercase payload-shaped names in the SCENE
   module); scene-module constants lowercase or mapped.
5. **Gates 18-21 reason fixed**: they skip NOT for a missing
   hero_gates.py (the agent-kit's own scripts dir ships it) but for
   absent Gunner/boards_at, absent FX_EVENT_WINDOWS, and gate 21
   returning [] with no JeepRoot node. Non-blocking, documented.
6. **EEVEE discipline**: HDRI strength 0.35-0.5 (gotcha 128: strength
   1.0 blows out interiors), -0.5 EV on 5.x, `clipped%` verified via
   image_metrics, single process per shot, 8.5 s/frame budget.
   ALL stills EEVEE (no Cycles — AgX vs Standard would split the A/B
   palette).
7. **Naming hygiene**: no object/material name may match
   `mist|fog|haze|atmo` (the atmosphere exclusion regex would remove
   it from the GLB). Stills named `stills/shot_<id>.jpg`, ids S1..S12.
8. **Wrapper env**: `KIT_EXPORTER` must be set explicitly (the
   /home/sync probe is dead post-wipe).

### The scene module

Self-contained imports (bpy + tdawn_world + frozen `crowd_agents`
shape-key bases via the previz repo's scripts on sys.path). Build:

1. Hall shell: floor slab 34×64 m, side walls, glass roof with steel
   arches (barrel section), end wall with the incident windows.
2. The Gate at origin: a lit portal frame (emissive surround + dark
   interior), the vault "seal" doors (animated), gate plaza floor
   marking (capacity box ±5 m).
3. Departure board at the far end: emissive panel, flicker animation
   (S2).
4. Columns: two colonnades flanking the central axis (rhythm for the
   camera moves).
5. Set dressing: benches, signage pylons, the 3 RB-placeholder luggage
   carts (grounded, static, near the gate).
6. Crowd anchors: N capsule anchors (Zed.NNNN) with the frozen
   shape-key bases + 12 chase capsules (2 RB slots at 2/5/8 → the
   carts displace 3; see D-TD4).
7. Heroes: TD.Master (amber, gate-side choreography) + TD.Runner
   (teal, far-end → gate authored run with a stumble beat). Capsule
   actors, keyed on the 1080-frame grid.
8. Cameras: 12 shot cams (CAM_S1..CAM_S12) + Aim.* empties, TRACK_TO
   constrained (the exporter gate requires Aim nodes in the GLB).
9. World: dawn HDRI (Poly Haven CC0) + sun; exposure tuned by the
   vision loop with image_metrics readiness numbers.
10. `emit_sfx_events()` — board chime, rumble, surge swell, vault
    seal, title sting (frame-stamped).

### Crowd count (D-TD3, REV-2): 129 agents (120 crowd + 9 tail)

The loader pins n_agents == 129 (the anchor arithmetic: 120 Zed.NNNN
+ 12 chase objects, 9 non-RB). Density is bought with GEOMETRY: the
hall is 24×40 m (vs Last Ride Out's ~40×60 street), so 129 agents
read as a packed terminal, and the ±5 m gate plaza produces the jam
the story needs. GLB ~20 MB — v6_1 parity, no GitHub blob risk.

## 3. Visual design (the "next level" brief)

- **Lighting**: low dawn sun through the glass roof (long shadows
  across the floor, the whole film is backlit haze); HDRI sky fill;
  the Gate is the brightest surface in frame from S6 on (the goal is
  always lit). Emergency phase (S3+) trades sun warmth for amber
  practicals at the columns.
- **Palette (D-TD5)**: environment = warm stone + steel (greys with
  warm bounce); crowd capsules = varied muted commuter colors (navy,
  rust, olive, charcoal, bone — no uniform green); Master amber;
  Runner teal (the only saturated subjects — the eye finds them in
  every frame); gate emissive = warm white.
- **Camera grammar**: S1 aerial; S2-S3 slow push-ins; S4-S5 lateral
  tracking against the flow (the Runner crossing frame); S6 static
  gate hero; S7 handheld-feel low tracker at the stumble; S8-S9 the
  vault; S10-S12 the emptying pull-back. Aim targets + lens per shot
  in CAMS table; every camera gets a CAM_KEEPOUT row.
- **Quality bar**: EEVEE stills per shot (preview preset, single
  process per shot — the OOM law), Cycles ONLY for the 3 key frames
  (S1 establish, S9 dive, S12 title) if time allows. Filmstrips at
  workbench previz res.

## 4. Shot list (12 shots / 1080 f)

| id  | f0    | f1    | camera     | intent |
|-----|-------|-------|------------|--------|
| S1  | 1     | 84    | CAM_S1     | aerial dawn establish: hall + thin early flow |
| S2  | 85    | 168   | CAM_S2     | departure board flickers; far windows glow wrong |
| S3  | 169   | 264   | CAM_S3     | the surge ignites: flow accelerates, density jumps |
| S4  | 265   | 348   | CAM_S4     | the Runner enters far end, turns against the flow |
| S5  | 349   | 444   | CAM_S5     | lateral: Runner jostling through the stream |
| S6  | 445   | 528   | CAM_S6     | the Master holds the gate line; crowd piles up |
| S7  | 529   | 624   | CAM_S7     | low tracker: the Runner stumbles, nearly lost |
| S8  | 625   | 720   | CAM_S8     | Master sees the Runner; holds the vault open |
| S9  | 721   | 816   | CAM_S9     | the dive: Runner through the sealing vault |
| S10 | 817   | 912   | CAM_S10    | vault sealed; crowd held; hall quiets |
| S11 | 913   | 1008  | CAM_S11    | pull-back: dawn light floods the empty hall |
| S12 | 1009  | 1080  | CAM_S12    | title frame: TERMINAL DAWN over the still hall |

Story beats export via the session-33 portable vocabulary:
`synopsis` + `beats[]` + `cast{}` (no chase-era constants needed —
the exporter's _collect_story collects what the module DECLARES).

## 5. Export & staging

```bash
# 1. fresh bake (fresh-dir law):
/home/z/.venv/bin/python3 scripts/tdawn_bake.py --out /tmp/crowdcache_tdawn
# 2. export (wrapper = the binding law; CWD = vision kit for provenance):
CROWD_CACHE_DIR=/tmp/crowdcache_tdawn RB_CACHE_DIR=/tmp/rbcache \
bash ../blender-crowd-kit/scripts/blrun.sh --background --factory-startup \
  --python ../blender-crowd-kit/scripts/previz_kit_export_wrapper.py -- \
  --scene scene_terminal_dawn --scene-dir /home/z/work/blender-vision-kit/scripts \
  --crowd-mode kit --crowd-plugin ../blender-escape-previz/scripts/crowd_kit \
  --output output/tdawn/pkg --package-id tdawn_1 \
  --name "TERMINAL DAWN (vision-native crowd-kit build)"
# 3. stills (one EEVEE process per shot), filmstrips, manifest rebuild
# 4. stage into previz-review/public/packages/tdawn_1/ + commit
```

Known export deltas vs Last Ride Out (accepted, documented): gates
18-21 SKIP (hero_gates.py absent from the vision-kit scripts dir —
loud WARN, non-blocking); agents carry the Zed.NNNN naming law
(internal names; the app shows them only in crowd chips).

## 6. Decision record

- **D-TD1 concept-through-the-bridge**: reuse the pursue-origin
  motion grammar as a gate convergence; zero bridge forks.
- **D-TD2 speed mix**: post-ingest distribution mutation in MY bake
  driver (walk/jog/run mix, hi kept at 5.5 for the tail-enders).
- **D-TD3 (REV-2) 129 agents, density via geometry** (was 200 —
  folded by TD-REVIEW-1: the loader fail-closes at N≠129; a runtime
  contract patch would fork the kit identity pin for a quality win
  geometry can buy for free).
- **D-TD4 RB placeholders become luggage carts**: the loader demands
  12 chase objects with RB slots at 2/5/8; the 3 RB-named objects are
  grounded static carts (bake2 skips them; they export as set
  dressing, not crowd).
- **D-TD5 palette**: commuters varied muted; heroes the only saturated
  bodies; environment neutral-warm; gate always brightest.
- **D-TD6 scene module self-contained**: no vision-kit blender_kit
  imports inside the scene (the wrapper binds the previz superset
  copy — MY scene avoids the binding question entirely by importing
  only bpy + its own siblings).
- **D-TD7 vision-first build order**: every build step lands as
  look.py renders READ BY THE PRINCIPAL before the next step (world →
  gate → crowd → heroes → cameras → lighting pass → polish). No
  batch-blind building; frictions logged per step in worklog.

## 7. Risks

- **EEVEE + 129 shape-keyed capsules + HDRI on 4 GB** — stills one
  process per shot; HDRI 0.35-0.5 strength; fall back to sun-sky only.
- **The wrapper's superset gate** — binds the PREVIZ blender_kit; my
  scene must not import vision-kit-only blender_kit symbols (D-TD6).
- **The unmapped-story-constant gate** — every uppercase constant in
  the SCENE module must be a mapped name or it fail-closes the export.
- **Parallel session races** — sync_both.sh before every push; never
  force; rebase onto remote tip.
- **The sim's flee_target ebb** — accept what the shared behavior
  graph gives; judge on the first bake receipt + look, not in theory.
