# DESIGN_express.md — Film 5: THE EXPRESS (tfog_1) — REV-1

> Blue-hour fog rail platform. The crowd waits; the express does not stop;
> the blast recoil is REAL (DANGER field, base bytes); the local train boards
> by groups. The fog regime is the film's reason to exist.

## 0. Identity

- **Film**: tfog_1, title **THE EXPRESS** (the departure board is the title
  card: `EXPRESS  PASSING WITHOUT STOP`).
- **Regime (new)**: BLUE HOUR + GROUND FOG — deep-blue ambient gradient,
  sodium platform lamps (warm pools), the express headlight cutting a
  volumetric cone through fog. Nothing in the trilogy touched volumetrics
  or a sub-dawn sky.
- **Setting (new)**: an island rail platform — canopy, benches, lamp posts,
  departure board, two track faces (the express face + the local face).
  Different geometry class from dock/ferry/plaza/arcade: LONG-THIN with a
  hard platform edge.
- **Time**: 540 ticks @ 12 Hz = 45 s, 12 shots (the standing film shape).

## 1. Pinned laws this film inherits (research wave 5-a/b/c, this session)

- **DANGER force fields are base-bytes VISIBLE** (no layer; fields_adapter
  ATTRACTION/REPULSION/DANGER with static center + strength>0 serialize
  into IR `fields`, the Rust bias applies per tick pre-steer). CAVEATS:
  explicit `t_active` REQUIRED (kit default `(0,45)` deactivates at 45 s —
  our window must be in SECONDS not ticks and must cover the blast);
  fields are ADVISORY under behavior graphs — the waiting crowd must be
  graph-light near the edge; driver captures `warnings.warn` drop
  accounting (FLOW/source_object drops are warnings-only).
- **Groups are runtime REAL** (shared destination + cohesion) on the v2
  path. Cohorts = families boarding the local together.
- **Queues runtime REAL** (portal + slots + admission) — the boarding
  press at the local's door reuses the tsquall pattern as a SECONDARY beat.
- **VIEW-invisible kinds** (do not design around them): GOAL, SPEED,
  TIMING, APPEARANCE, RENDER_TIER, GROUP layers, plus DISABLE/HIDE
  (partial: speed-0 statue). The film's sim story must live in BASE bytes.
- **Fidelity profile is SKIPPED** (m5_background_10_90 is v1-path only and
  the film reads no render_tier channel — dead zeros; honest scope note).
- **12 Hz cache law** (to_previz_cache refuses non-12 Hz).
- **F-TS5 loader override** (`expected_agents=`) + F-TS2 belt pins
  (`chase_frame="belt"`, interval=1, zone0-first, chase-last).
- **The marker-camera law** (probe tools null shot markers in `finally`).
- **The 3GB EEVEE law**: fog = ONE volume box hugging the platform, capped
  resolution/steps; one EEVEE process at a time; blrun.sh only.

## 2. Cast (contract-authoritative counts)

| pop | count | role | notes |
|-----|-------|------|-------|
| waiters | 66 | platform crowd, bench-standers + drifters | spawn across platform, v1-ish wander between two calm destinations |
| cohorts | 42 | M6 groups: 14 groups × 3 members | shared destinations = the three local-door zones (group cohesion law) |
| door queue | 18 | the boarding queue | Queue off the center-door portal, 9 slots, capacity 1 |
| chase | 9 | keyed hero lane | the LATE PASSENGER (keyed runner) + the STATIONMASTER (keyed walker w/ lantern) anchors |

Total declared: 135 (the trilogy shape; loader pin override 135 — F-TS5).
The two keyed heroes are 3 RB slots per the loader law (126 crowd + anchors).
Exact per-pop group member lists resolve from the base bake via
`agent_ids` (two-bake covenant; NEVER rebuild the scene).

## 3. The story spine (45 s)

| beat | ticks (12 Hz) | content |
|------|---------------|---------|
| S1-S2 establish | 0-96 | blue-hour platform, fog pools under sodium lamps; the board flips to `EXPRESS APPROACHING`; waiters drift |
| S3-S4 the wind | 96-168 | express headlight flares through fog (world-side: headlight keyframe); crowd begins to press BACK (implicit) |
| S5 blast | 168-264 | the express passes THROUGH at speed (train prop slide, no stop): the DANGER field window fires — crowd recoil from the edge is REAL base-sim displacement; keyed late-passenger sprints against it, misses |
| S6-S7 exhale | 264-336 | fog closes, dust settles; the board flips `LOCAL ARRIVING`; cohorts regroup (cohesion) |
| S8-S10 local + boarding | 336-456 | the local slides in and STOPS; door queue admits (read_events → sfx bell); cohorts board via shared destinations |
| S11-S12 depart | 456-540 | the local pulls out; platform nearly empty; the late passenger alone on the bench; board: `EXPRESS — PASSING WITHOUT STOP` (title card) |

The late passenger's sprint is keyed (hero lane, tgreen/tsquall pattern);
the blast recoil carries the drama WITHOUT keys — the honest sim beat.

## 4. Crowd plan (bake stages, the tsquall pattern)

- **Stage probe**: base bake ONLY (135 declared, interval=1, zone0-first,
  chase-last pins) → `agent_ids`, group member resolution, the DANGER
  recoil probe (measure max edge displacement during the window in cache
  bytes — deterministic verdict, no eye needed).
- **Stage groups**: `dataclasses.replace` + groups (14 × 3) + the Queue +
  graphs (queue graph on the 18; door destinations for cohorts; the
  waiters stay graph-free for clean DANGER response) → final bake.
- **Stage finish**: read_events (QUEUE_ADMITTED/RELEASED) → sfx rows;
  cast list; composed npz (F-TS1 path, no transform layers in this film —
  physics absent too unless a slip beat earns its place — NO, keep film 5
  layer-free: the layers are film 6's showcase; film 5's new surface is
  FIELDS + the fog regime).
- **DANGER field spec**: center on the express track face mid-platform,
  radius ~7 m, DANGER strength strong, `t_active=(14.0, 22.0)` seconds
  (the blast window) — VERIFY the seconds-vs-ticks unit at build (audit
  flagged fields_adapter t_active units; pin with a probe assert).
- Determinism pins: fresh bake dirs, pin sha256 recorded per stage.

## 5. World module (sub-agent build, my visual gate)

- Island platform ~64×8 m at z=0.9 (platform height), two track beds at
  z=0 flanking; canopy on columns over the platform; 6 sodium lamp posts;
  benches; the departure board (double-sided, glyph rows); fog volume box
  (192×24×10 m around the whole set, density tuned in the ladder); sky =
  MULTIPLE_SCATTERING blue-hour (sun below horizon or deep-blue preset —
  the ladder decides); express train = 8-car dark wedge with lit window
  strip (slides through, 30+ m/s); local train = 3-car warm-lit, decel
  stop, dwell, accel out. Track rails (glossy dark), ballast strip,
  distant signal gantry with red/green aspects (the glyph-color spine).
- Naming/consts: lowercase internal wiring (the exporter's
  unmapped-constant gate). Factory purge at scene-module level (caller
  purges law).
- Visual gate: 3-angle world probes (workbench first, then Standard
  previz-transform EEVEE) — the tsquall gate pattern; the CUBE law check
  (factory-purge).

## 6. Scene module

- Loader: `expected_agents=135` pin override; 126 crowd + keyed anchors;
  x-sign-free palette (platform split W/E: cool blue-gray / warm sodium
  tints); storm → no; per-zone speed map driver (bench zone slow, aisle
  fast).
- Cameras: 12 shots. Draft vantages (probe-driver adjudicates):
  S1 aerial SE down the platform axis (the LONG-THIN geometry law —
  the colonnade-axial class from tsquall applies: an opaque canopy may
  demand the along-axis crane), S2 lamp-pool close, S3 headlight through
  fog (the signature candidate), S4 the board close-up, S5 low blast
  (platform end, train streaking), S6 recoil wide, S7 bench exhale,
  S8 local arrival front, S9 door press, S10 interior through door,
  S11 pull-out rear, S12 title board + empty platform.
- Crane: the S5→S6 recoil pair or S8→S9 arrival pair gets the keyed
  crane (loc0→loc1 keyed — the crane law).
- sfx spine: events from read_events + authored beats (express pass rumble
  = rail clatter bed, the board flip tick, door bell, brake squeal, depart
  drone). `sfx_events.json` exporter gate fail-closed.

## 7. Light ladder (my eye, EEVEE, Standard transform for gates)

- Blue-hour sky: 3 candidates (deep-blue preset / sun at -4° / sun at -8°)
  × fog density 3 steps (0.02/0.05/0.09) on ONE critical frame (the S3
  headlight) + one wide. Sodium lamps: 3 intensities. Decide on the
  headlight-vs-ambient separation (the direct:ambient ratio law
  generalizes: the headlight must OWN the frame; sky ambient must sit
  back). Metrics travel with images (image_metrics luma/contrast).

## 8. Export + stage

- `tfog_1` rev 1 through preflight (D19): B3 span set at build time (the
  tsquall law); characters registry (CAST table in ctx); naming law;
  keepout rows COUPLED to any moving camera (F-TD13) — the S5 blast cam
  and the S8 arrival cam need keepout review; outboard cams delete rows.
- Stage into the review app (comments ON), filmstrips + stills per the
  staging convention.

## 9. Shot list (12)

1. S1 — aerial platform axis, blue hour establish
2. S2 — sodium lamp pool, waiters drift
3. S3 — headlight cone through fog (signature)
4. S4 — departure board `EXPRESS APPROACHING`
5. S5 — the blast: train streaks, crowd recoils (DANGER beat)
6. S6 — recoil wide: the platform holds its breath
7. S7 — the missed sprint: late passenger at the edge, express gone
8. S8 — the local arrives (headlight differs: warm, slower)
9. S9 — door press: queue + cohorts (group cohesion readable)
10. S10 — through the door: warm interior vs cold platform
11. S11 — pull-out rear: fog swallows the tail lights
12. S12 — title: `EXPRESS — PASSING WITHOUT STOP` on the board

## 10. Open questions for the audit round

- OQ1: t_active units (seconds vs ticks) — pin from source + probe assert.
- OQ2: DANGER under v2-path groups-only scenes — does the cohesion
  controller wash the recoil? Probe-assert the edge displacement.
- OQ3: bench SITTING — the kit has no sit clip (0/1/2 only): benches are
  atmosphere, sitters must NOT be attempted (honest scope) — confirm no
  fake-sit pattern is proposed.
- OQ4: fog cost — is a 192m volume box inside the 3GB law with 135
  capsule agents? Probe early (world-gate stage).
- OQ5: the board glyph row mechanism — reuse the tgreen glyph spine
  pattern (emissive text planes keyed), confirm no new exporter surface.
- OQ6: the express train prop motion — scene-side keyed slide (exporter
  carries it fine) vs crowd-side (never) — confirm scene-side keyed.
