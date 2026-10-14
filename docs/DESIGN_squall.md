# DESIGN — "SQUALL" (tsquall_1) — the fourth film

> REV-1 (pre-audit). The storm-dusk regime: RAIN + wet ground + overcast
> dusk + warm practicals — the fourth light/weather family (dawn / night
> / noon precede). The kit-push film: first film use of M6 Queue + Portal
> divider, HoldPosition vendors, Groups (two-bake), M5 ragdoll slip beat,
> and sim-events→sfx. Built on the three research receipts of 2026-10-14
> (tasks 4-a/4-b/4-c, file:line-cited below).

## 1. Story and title

A market plaza at storm dusk. The sky has been threatening all evening;
the film OPENS on the first heavy drops (no delayed emission exists —
the crowd is already responding). Streams converge on the central arcade
(the shelter); the entrance doorway chokes; a dasher slips on the wet
pavement by the fountain and stays down; a queue forms at the food
window; the storm eases; the crane rises over the packed arcade and the
empty rain-hazed plaza. Title: **SQUALL**.

The engine laws ARE the story again (the tgreen lesson):
- the ±5 arrival box (belt-mode `hero_pos` (0,0) cap (±5,±5)) = the
  covered arcade floor — arrivals freeze INSIDE the shelter (ghost
  ranks under the canopy = the fill);
- the zombie FSM flee (≥8 neighbors → flee_target north (0, 14)) = the
  ebb: overloaded shelter-dwellers push back OUT through the doorway
  against the inflow — the counter-flow beat;
- the M6 portal divider wall (REAL nav wall + doorway, concourse.rs
  append_portal_divider) = the arcade facade line — the sim wall and
  the set wall COINCIDE (the sim-vs-set agreement law).

## 2. Why this pushes the kit (the dog-food ledger)

| New surface | First film use | Evidence |
|---|---|---|
| M6 Queue (runtime REAL) | 9-agent line at the food window; admission events drive sfx | 4-b: advanced.py:64-134, social.rs:51-118 |
| M6 Portal | the arcade entrance (divider wall + 10m doorway) | 4-b: environment.py:105-123, concourse.rs:278-308 |
| BehaviorGraph #2 | `Sequence(QueueNode, Navigate)` bound to the chase tail | 4-b: bake.py:268-298 (multi-graph legal) |
| HoldPosition population | 6 vendors standing at stall posts (tiny per-vendor spawn boxes) | 4-b: behavior.py:800-820, runtime_behavior.rs:441-449 |
| M5 ragdoll | ONE dasher slips at the fountain, stays down to film end | 4-c: ragdoll.py:109-210, layout.rs:823-833 |
| read_events → sfx | QUEUE_ADMITTED/RELEASED ticks → frames → the sfx spine | 4-b: advanced.py:1865-1962 |
| Groups (two-bake) | 4 clusters among drifters (cohesion + shared destination) | 4-b: bake.py:331-408 |
| Bridge composition fix | F-TS1: sidecar layers + real z into the npz VIEW (gated) | 4-a: previz_bridge.py:832-866 |
| chase_frame pin | F-TS2: explicit `chase_frame="belt"` in all film drivers (the r109 default-flip trap) | 4-a/4-b receipts |

FILED, NOT CHASED (honest scope): SPEED (playback_rate) and GOAL
(destination_id) layers are VIEW-invisible channels (4-a:
layout.rs:802-817 vs previz_bridge.py:837-845) — a mid-film panic wave
is NOT layer-expressible on the film path; the panic reads through
per-population speed plans + edit instead. DISABLE/HIDE likewise
(no visible column in the v6 tick channels).

## 3. Frame (belt mode — chase_frame="belt" EXPLICITLY)

Walkable: `((x_lo, -6.0), (x_hi, y_hi_all + 1.0))` — belt grammar
(previz_bridge.py:503-508). `CROWD_X_RANGE = (-30.0, 30.0)`;
zones' y_hi_all = 14.0 → walkable y ∈ (-6, 15).

Destinations (belt defaults, previz_bridge.py:510-522):
- `hero_pos` point (0,0), capacity (±5, ±5) — THE ARCADE FLOOR. The set
  roof covers x∈(-8,8), y∈(-6,6) ⊇ the box.
- `flee_target` point (0, 14), capacity (x_lo+0.5, 13.0)..(x_hi-0.5, 14.5)
  — the north plaza (the ebb target).

Portal (the one divider): `Portal(id="arcade_gate",
from_walkable_id="street", to_walkable_id="street", center=(0.0, 6.0),
width_m=10.0, axis=EAST_WEST)` — a full-width nav wall at y=6 with a
10m doorway at center. The SET builds the facade line at y=6 with the
matching opening. 4-b: from==to=="street" is legal
(environment.py:105-123); the divider is REAL (concourse.rs:27-35).

Queue: `Queue(id="window_q", portal_id="arcade_gate",
admission_capacity=1, slots=<6 slots along the window>)` — slots raw
meters, world XY (advanced.py:91-93): a single-file line at x=6.5,
y = -2.0, -0.5, 1.0, 2.5, 4.0, 5.5 (inside the arcade, south of the
wall). admission_capacity=1 keeps the line alive most of the film.

Queue graph: `BehaviorGraph(id="queue_window",
root=Sequence(id="qs", children=[QueueNode(id="qn",
queue_id="window_q"), Navigate(id="qr", destination_id="hero_pos")]))`
— released heads join the shelter (4-b: behavior.rs:377-380). Bound to
the chase tail population `zombies_zz_chase` (9 agents, spawns in
zone0's strips — the nearest band).

Vendor graph: `BehaviorGraph(id="vendor_hold", root=HoldPosition())`,
bound to SIX count-1 populations (one per stall post; spawn box =
the post's 1.2m square). Population ids `zombies_v01..v06` sort before
`zombies_zone0` ('v' < 'z') and after nothing that matters; the chase
tail still sorts LAST (the naming law, previz_bridge.py:586-594).

Groups: base bake of the post-ingest scene (queues+portals+graphs
attached — v1 IR identical, 4-b: bake.py:1006-1013) →
`visible_agent_ids(base, tick≈300)` → 4 clusters (2 couples, 2
families, members from zone1/zone2 populations, leader = first member,
max_separation_m=2.0, shared_destination_id="hero_pos") →
`dataclasses.replace(scene, groups=...)` → final bake. The two-bake
covenant (4-b: FEATURE_REFERENCE.md:452-474).

## 4. Populations and the envelope law

Zones (y_lo, y_hi, count, min_abs_x, x_jitter) — spawn strips
|x| ∈ (min_abs_x, 30), y = the band (belt grammar):

- zone0 `(10.0, 11.5, 44, 2.5, 0.35)` — the NEAREST band = the FAST
  population (the first to reach the mouth): mu 2.0 σ 0.25.
- zone1 `(11.5, 13.0, 40, 2.5, 0.35)` — the middle strollers: mu 1.2 σ 0.2.
- zone2 `(13.0, 14.0, 36, 2.5, 0.35)` — the far band: mu 1.35 σ 0.2.
- chase 9 (queue-bound): mu 1.1 σ 0.15 (a queue walks calmly).
- vendors 6 (HoldPosition): speed irrelevant.
- **N_RELEASE = 44+40+36+9+6 = 135.**

ENVELOPE LAW (the F2 fold): populations[0].mu+3σ is the global cap —
zone0 IS populations[0] → cap 2.75. Check: zone2 max 1.95 ✓, chase
max 1.55 ✓. The driver asserts per-population BEFORE baking.

Spawn-band vs set-dressing seam (the F-TG lesson inverted): stall rows
at x≈±26, y∈(1..8) and the fountain at (14, 7.5) are all OUTSIDE the
spawn bands (y ≥ 10) — no agent spawns inside set geometry. Stall
counters and the fountain basin get contract BARRICADES squares
(belt mode consumes them, previz_bridge.py:505-509): stalls r=1.1 at
(±26, 1.5/3.5/5.5/7.5), fountain r=2.4 at (14, 7.5). All squares ≥ 2m
from each other and from the walkable edge (the sealed-pocket law —
no plaza-scale unions).

## 5. Set (world module — sub-agent built, eye-gated)

Palette: storm-dusk market — dark wet ground (low-rough dark concrete),
warm stall bulbs, cool fluorescent canopy strips, red/rust canvas,
puddle mirrors. The AgX discipline: warm practicals own the arcade;
the sky owns the ambient base; the ladder decides the ratio.

- Ground z=0, wet look (the SSR knob + puddle discs).
- THE ARCADE: x∈(-8,8), y∈(-6,6); roof slab z≈4.2 on perimeter columns;
  entrance facade at y=6: columns at x=±5..±8, lintel over the 10m
  opening (x∈(-5,5)) — the sim divider doorway COINCIDES; back wall
  (south y=-6) with the FOOD WINDOW counter at x≈6.5 facing north
  (warm interior glow = the queue target); fluorescent strip fixtures
  under the canopy; sign band over the entrance.
- STALLS: 4 west (x≈-26) + 4 east (x≈+26) at y = 1.5/3.5/5.5/7.5 —
  counter + canvas roof + bulb string + crates. (Sim barricades at the
  same coords, §4.)
- FOUNTAIN: circular basin at (14, 7.5), r≈2.2 — low ring wall, dark
  water disc, center jet column. The slip happens on the pavement
  beside it (NOT in the basin).
- North facades: low shopfront strip at y ≥ 15.5 (BEYOND the walkable
  ceiling 15 — the facade-swallow law), x full width; silhouetted
  against the storm sky.
- Bollards + benches + planters as dressing (outside flow lanes or
  barricade-backed).
- Title card carrier for S12 (the tgreen lesson: verify visibility by
  probe, not by math).
- NO rain in the world module (rain layers are scene-side).

## 6. The film (12 shots × 90f, 1080f @ 24fps = 45s)

| Shot | f0-f1 | Intent |
|---|---|---|
| S1 | 1-84 | aerial: first heavy drops on the plaza; the drift begins |
| S2 | 85-168 | the thunder hit: stall lights flicker; the dashers break |
| S3 | 169-264 | the streams merge toward the arcade mouth |
| S4 | 265-348 | the doorway choke: the press at the entrance |
| S5 | 349-444 | THE BEAT: the slip-and-fall beside the fountain (ragdoll) |
| S6 | 445-528 | the queue forms at the food window |
| S7 | 529-624 | under the canopy: the packed shelter, sheeting rain off the roof edge |
| S8 | 625-720 | the ebb: fleers push back out north against the inflow |
| S9 | 721-816 | the density peak: the box filled, ranks spilling |
| S10 | 817-912 | the storm eases: light warms; the queue drains forward |
| S11 | 913-1008 | the crane rises: packed arcade + empty plaza + the still figure |
| S12 | 1009-1080 | title: SQUALL |

Ragdoll beat: faller = a zone0 dasher whose path crosses the fountain
pavement at the beat (picked AFTER the bake from the flow data; name↔
ordinal↔id correlation per 4-c). `tick_start = 210` (f420),
`tick_end = 539` (cache end → STAYS DOWN to picture end, 4-c Q4),
`drop_height_m=0.45, impact_vz_mps=-0.6, restitution=0,
zero_horizontal_velocity=False` (the wet slide sells the slip),
`incoming_velocity=(vx_cache≈2.0, 0, -0.6)` — read the actual cache vx
at the beat and author it explicitly. Floor: the pavement beside the
fountain is z=0 ✓ (4-c risk 5).

sfx spine (events-driven where possible): rain hiss ramps f1+;
thunder cracks at f85 / f529 / f817; QUEUE_ADMITTED/RELEASED events →
window-bell ticks (read_events on the final cache, tick = frame//2);
the fall thud f425; canopy murmur bed; title sting.

## 7. The build order (the green-light recipe + this film's deltas)

1. ~~research wave~~ DONE (4-a/4-b/4-c).
2. design audits: round 1 (this doc, 2 auditors) → REV-2 → round 2
   (focused: portal-divider geometry + the ingest probe's empirical
   verdict) → REV-3 final.
3. world module (sub-agent, non-visual QA + my eye on the smoke render).
4. contract module (me): zones, barricades, keepouts, N_RELEASE=135,
   CROWD_SEED; the chase_frame="belt" pin.
5. INGEST PROBE (the round-3 pattern): ingest → attach portal/queue/
   graphs/vendor pops → compile → the divider's empirical verdict
   (does the doorway route? does the box survive south of the wall?).
6. bake driver (me): per-zone speed map, envelope asserts, vendor pops,
   base bake → groups → final bake → ragdoll attach → npz via the
   F-TS1-composed to_previz_cache.
7. scene module (me): loader branch, palette, cams, sfx (events-driven),
   rain layers, thunder keys.
8. flow strip FIRST (the seam detector) → framing probes → the
   storm-dusk ladder (new law family) → 12 EEVEE stills (eye gate).
9. export (agent-kit canonical exporter) → stage → in-app verify.

## 8. Open risks (for the auditors to attack)

- R1: the portal divider's empirical behavior — full-width wall at y=6
  across a 60m walkable: does the compiler accept same-walkable
  portals in belt mode? Does the doorway route without unnatural
  funneling artifacts? (Probe resolves.)
- R2: the zombie FSM's flee threshold (≥8 neighbors) under the arcade
  roof — the box holds ~arrivals; flee stormers cross the doorway
  northward — counter-flow is WANTED but could ping-pong (flee →
  re-pursue → flee). Mitigation: it's a 45s film; the ebb is one beat.
- R3: the ragdoll walk-clip-while-down class (4-c risk 2) — the faller
  keeps playing the walk cycle while the origin slides. Mitigations:
  mid-shot framing, rain streaks, the slide, cut away at f444; the
  S11 crane sees the still figure small.
- R4: 135 agents + composition pass + rain layers on the 3GB sandbox —
  the OOM law. Mitigation: the composition pass is one-time at
  conversion (single-digit seconds, few MB); rain = camera-prox layer
  geometry + shader cost measured in the ladder.
- R5: the two-bake pattern doubles bake time; determinism: both bakes
  fresh-dir (the fresh-dir law), the pin recorded per stage.
- R6: vendor spawn boxes (count-1 populations) — 6 extra populations ×
  alphabetical rank shift — the chase-last assert still holds (v < z <
  zz). Verify in the probe.
- R7: QUEUE release semantics — released agents resume their
  spawn-assigned hero_pos goal (4-b caveat: goals never re-sampled) —
  released queue-walkers join the box ranks ✓ (that IS the intent).
- R8: the r109 default-flip trap (F-TS2): ALL drivers (existing 3 +
  this film) must pass chase_frame EXPLICITLY.
