# DESIGN_express.md — Film 5: THE EXPRESS (tfog_1) — REV-3

> Blue-hour fog rail platform. The crowd waits; the express does not stop;
> the blast recoil is REAL (DANGER field, base bytes); the local train boards
> by groups. REV-2 folds audit round 1 (2 P0s: the arrived-statue waiter
> mechanism; the ingest fork).
>
> **s19 AMENDMENT (2026-10-15, audit wave-D — counts reconciled to the
> contract):** scripts/tfog_contract.py pins the cache at **126 = 66
> waiters + 51 cohorts + 9 doorq** (N_CACHE=126; loader pin override
> 126, F-TS5). The chase lane is NOT a cached population: the two
> heroes (LATE PASSENGER, STATIONMASTER) are Blender-side keyed actors
> OUTSIDE the cache (the drill's branch-(a) law). The earlier
> 66/42/18/9 = 135 cast table (and the 135 loader pin) was written
> before the contract and is WRONG — §2, §5 and §6 below carry the
> corrected numbers. (Doc-audit trail: counts amended, not silently
> rewritten.)

## 0. Identity

- **Film**: tfog_1, title **THE EXPRESS** (the departure board is the title
  card: `EXPRESS  PASSING WITHOUT STOP`).
- **Regime (new)**: BLUE HOUR + GROUND FOG — deep-blue ambient gradient,
  sodium platform lamps (warm pools), the express headlight cutting a
  volumetric cone through fog.
- **Setting (new)**: an island rail platform — canopy, benches, lamp posts,
  double-sided departure board, TWO track faces (express = N face, local =
  S face). Long-thin geometry with a hard edge.
- **Timeline law (the ×2 law)**: cache 541 ticks @ 12 Hz = 45 s; the film
  runs 24 fps / 1080 frames; **1 tick = 2 frames**. ALL exported surfaces
  (shot spans, sfx frames, keepout rows, keyed board flips, train slides)
  are authored in FRAMES. `t_active` stays seconds (14 s = tick 168 =
  frame 336 — consistent).

## 1. Pinned laws this film inherits (research wave 5-a/b/c + audit round 1)

- **DANGER fields are base-bytes VISIBLE**; `strength` is a desired-velocity
  in m/s at field center (added to des_vel, clamped to max_speed — NOT a
  force); falloff SMOOTH; `t_active` = (start_s, end_s) seconds inclusive;
  kit-default `(0,45)` trap avoided by explicit window.
- **The bias is scene-global pre-controller; the wash is per-population**:
  graph-free pops keep the bias; Navigate-bound pops keep it; Queue/Hold/
  Wait/Reserve zero des_vel (a queue HOLDS through the blast — discipline
  contrast, by design); **arrived agents are field-immune** (the P0 law:
  the blast crowd must be un-arrived at tick 168).
- **The ingest fork (P0)**: this film authors a CUSTOM CrowdScene (an
  island platform fits NO hard-coded ingest band — belt mode hard-codes
  walkable south edge y=-6, world mode spawn strip y[16,22]). The driver
  pins `project_id=PREVIZ_PROJECT_PIN`, `tick_hz=12`, per-pop
  `emission_interval_ticks=1` and re-asserts the ingest-contract laws
  (12Hz / 541 ticks / 24 fps / 1080 frames / seed) manually.
- Groups runtime REAL; queue slots raw meters (never validated inside the
  walkable — author them ON the platform); PortalAxis names the CROSSING
  (NORTH_SOUTH = wall at constant y — correct for the E-W door face).
- VIEW-invisible kinds: GOAL, SPEED, TIMING, APPEARANCE, RENDER_TIER,
  GROUP layers. The film is LAYER-FREE by design (fields + base bytes).
- 12 Hz cache law; F-TS5 loader override; F-TS2 belt pins re-asserted
  post-replace (interval=1, zone0-first, chase-last); envelope cap owner =
  ingest-order populations[0] (waiters own the cap — mu chosen moderate).
- The express cannot drive the field by motion (source_object fields are
  bake-dropped with a warnings-only accounting): the recoil is a STATIC
  window-synchronized field, not a pressure wave. The driver captures
  bake warnings (drop accounting + the default-window warning).
- 3GB EEVEE law; marker-camera law; factory purge; lowercase wiring.

## 2. Cast (contract-authoritative counts)

| pop | ingest order | count | role | notes |
|-----|--------------|-------|------|-------|
| waiters | 1st (owns envelope cap) | 66 | platform crowd | Navigate-graph bound with the HORIZON-ROUTE law (round-2 R1: the destination-pair option is DEAD — goals are spawn-sampled, never re-sampled): spawn band E ~x=18, the single destination's capacity_bounds rect at the W end — min(spawn→goal) ≥ 40 m so nobody arrives inside the film; zero-arrived assert at EVERY tick in [168,264] |
| cohorts | 2nd | 51 | M6 groups: 17 × 3 | Navigate graph to door destinations; group cohesion additive (survives the field) |
| door queue | 3rd | 9 | Sequence(QueueNode, Navigate) | portal at the center door (S face), 9 slots ON the platform (1 agent/slot), capacity 1; HOLDS through the blast (des_vel zeroed — the disciplined line) |
| chase | — (no cache pop) | 2 keyed | keyed hero lane | LATE PASSENGER (keyed sprint) + STATIONMASTER (keyed lantern walk); Blender-side keyed actors OUTSIDE the cache (the drill's branch-(a) law; N_CACHE excludes them) |

Total declared: **126 cached = 66 + 51 + 9** (loader pin override 126 —
F-TS5); the 2 keyed heroes live outside the cache. Groups resolve
member ids from the probe bake (two-bake covenant; never rebuild).
(s19 amendment: 66/42/18/9 = 135 was the pre-contract draft — the
contract's POP_PLAN/N_CACHE are authoritative.)

## 3. The story spine (FRAMES, 1080 @ 24 fps)

| beat | frames | content |
|------|--------|---------|
| S1-S2 establish | 0-192 | blue-hour platform, fog pools under sodium lamps; board flips `EXPRESS APPROACHING` (keyed emission flip, tferry pattern); waiters drift (Navigate, un-arrived) |
| S3-S4 the wind | 192-336 | express headlight flares through fog (keyed lamp + emission); the board flickers; crowd begins to slow |
| S5 blast | 336-528 | the express slides THROUGH N-face at speed (keyed loc path); DANGER window (t=14-22s = frames 336-528) — the loose crowd presses BACK from the N edge (real base displacement); the queue HOLDS; keyed late passenger sprints against it, misses |
| S6-S7 exhale | 528-672 | fog closes; the recoil decays (field window ends); cohorts regroup (cohesion); board flips `LOCAL ARRIVING` |
| S8-S10 local + boarding | 672-912 | the local decelerates in and STOPS at the S face (keyed path); door bell (read_events or authored); queue admits; cohorts board via shared door destinations; arrival ghosts read as boarded silhouettes IN the dark doorway (framing law: door zone visually dark interior; scale-key hide available) |
| S11-S12 depart | 912-1080 | the local pulls out; platform nearly empty; the late passenger alone on the bench; board: `EXPRESS — PASSING WITHOUT STOP` (title) |

## 4. Crowd plan (bake stages, tsquall pattern + the audit folds)

- **Stage probe**: custom CrowdScene (ingest fork pins) → base bake
  (interval=1, zone0-first, chase-last; waiters=populations[0]) → ids;
  group member resolution; **the recoil probe**: max N-edge displacement
  of UN-ARRIVED waiters inside the window in cache bytes (deterministic
  verdict) + the zero-arrived assert at EVERY tick in [168,264]; the
  field magnitude is tuned HERE (strength 3.5 m/s, radius 7.5, SMOOTH;
  target a 1-2 m press-back at the edge band); **field center pinned
  (round-2 R2): on the N face at the S5 camera x-band, radius 7.5
  covers the full 8 m platform depth there**; keepout circles
  (r=1.3+agent_r) asserted ∩ queue slots / door destinations = ∅
  (round-2 R5 — the clamp is post-splice and hard-pushes xy).
- **Stage groups**: `dataclasses.replace` + groups + queue + graphs;
  re-assert interval/order pins (F-TS4); final bake; fresh dirs; pin
  sha256 per stage.
- **Stage finish**: read_events (QUEUE_ADMITTED/RELEASED) → sfx rows
  (frames = tick×2); cast list; composed npz (unlayered path — byte-law
  untouched); bake warnings captured.
- Displacement probe filters to un-arrived slots (the decide.rs:114 law).

## 5. World module (sub-agent build, my visual gate)

- **z INVERTED (audit P0-follow)**: platform top z=0 (64×8 m slab); track
  beds z=-0.9 N and S (rails, ballast, sleepers); canopy on columns over
  the platform; 6 sodium lamp posts; benches; double-sided departure
  board; **inset Blocked strips along BOTH platform faces** (the 0.9 m
  edge containment; centers ≤ walkable−r law); distant signal gantry
  (red/green aspects — the glyph-color spine); no roof over the track
  faces (aerials stay legal; the canopy is the S1 axial-crane class).
- **Fog (audit P1 fold)**: ONE camera-prox volume box ~64×10×6 m hugging
  the platform (the 192 m box is KILLED); `volumetric_end` 25-40 m,
  `volumetric_tile_size` 8 (4 for the S3 close-up), minimal steps; world
  volume OFF; OOM probe at world-gate (one frame with volume + 126
  anchors + RSS check) BEFORE the ladder. The measured recipe becomes
  the film-5 SKILL law.
- Express = 8-car dark wedge, lit window strip, keyed loc slide (N face);
  local = 3-car warm-lit, keyed decel-stop-depart path (S face).
  **Export probe (audit P2 fold)**: no translating large prop exists in
  any prior film — world-gate asserts export→reimport key survival for
  both trains before the stills stage.
- Sky: blue-hour candidates in the ladder; sodium practicals warm pools.

## 6. Scene module

- Loader: `expected_agents=126`; palette W/E split (cool blue-gray /
  warm sodium); per-zone speed map driver (bench zone slow, aisle fast);
  crane: S5 blast cam or S8 arrival cam keyed loc0→loc1 (the crane law).
- Cameras: 12 shots; keepout rows for ALL ground lenses inside the
  walkable + the S10 swept-span moving cam (F-TD13/F20/F-TS7: row +
  camprobe cert move as ONE edit); CAST rows for LATE PASSENGER +
  STATIONMASTER (rename-law pairing; 3 RB slots).
- sfx spine: rail clatter bed (the blast), brake squeal, board flip tick,
  door bell (event-driven), depart drone. Fail-closed gate.
- **Flow strip FIRST** (the seam detector, before cameras); clone-seam
  hygiene grep for any cloned runner.

## 7. Light ladder (my eye, EEVEE, Standard transform gates)

- Blue-hour sky 3 candidates × fog density 3 steps on the S3 headlight
  frame + one wide; sodium 3 intensities; decide on headlight-vs-ambient
  separation (the ratio law: the headlight OWNS the frame). Metrics
  travel with the images.

## 8. Export + stage

- `tfog_1` rev 1 through preflight (B3 span set at build time; characters
  registry; naming law; sfx fail-closed). Stage into the review app
  (comments ON), filmstrips + stills.

## 9. Shot list (12) — FRAMES

1. S1 — aerial platform axis, blue hour establish
2. S2 — sodium lamp pool, waiters drift
3. S3 — headlight cone through fog (signature)
4. S4 — departure board `EXPRESS APPROACHING`
5. S5 — the blast: train streaks, crowd presses back, queue holds
6. S6 — recoil wide: the platform holds its breath
7. S7 — the missed sprint: late passenger at the edge
8. S8 — the local arrives (warm headlight, slower)
9. S9 — door press: queue + cohorts (cohesion readable)
10. S10 — through the door: warm interior vs cold platform (moving cam,
     swept keepout)
11. S11 — pull-out rear: fog swallows the tail lights; doorway ghosts
12. S12 — title: `EXPRESS — PASSING WITHOUT STOP`

## 10. Round-2 folds (REV-3)

- R1: horizon-route law replaces the destination pair; zero-arrived
  asserts every tick in [168,264].
- R2: DANGER center pinned on the N face at the S5 x-band.
- R5: keepout ∩ {queue slots, door dests} = ∅ assert in the driver.

## 11. Resolved questions (audit round 1)

- RQ1: t_active = seconds — design consistent; strength is m/s; probe
  asserts magnitude.
- RQ2: wash is per-population; waiters Navigate-bound + un-arrived law.
- RQ3: portal = driver-side declaration (tsquall shape), NORTH_SOUTH axis.
- RQ4: ingest fork adopted (custom scene + manual pins); z inverted;
  Blocked edge strips.
- RQ5: keyed trains = new export surface; world-gate key-survival probe.
- RQ6: fog recipe + OOM probe at world-gate.
- RQ7: queue holds through the blast (discipline contrast, by design);
  boarding ghosts framed as doorway silhouettes.
