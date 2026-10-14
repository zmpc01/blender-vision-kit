# DESIGN — "SQUALL" (tsquall_1) — the fourth film

> REV-3 (FINAL — post audit round 2, task 4-f: the loader N-pin P0
> (load_kit_cache hard-pins 129 → the pin-override task), the ragdoll
> pick law re-pinned to the fountain RIM band (the barricade law makes
> a ≤1m approach impossible), vendor ids/boxes re-pinned (chase-last
> re-assert + spawn-box-vs-barricade disjointness), S5 re-aimed off the
> basin, S12 given its own key pair, probe gates sharpened).
> Round-1 folds: portal axis NORTH_SOUTH, ebb CUT, vendor interval=1,
> F-TS1 explicit. Research receipts: 4-a/4-b/4-c (2026-10-14).

## 1. Story and title

A market plaza at storm dusk. The sky has been threatening all evening;
the film OPENS on the first heavy drops (no delayed emission exists —
the crowd is already responding). Streams converge on the central
arcade (the shelter); the doorway chokes; a straggler hurrying against
the storm slips on the wet pavement beside the fountain and stays down;
a queue holds at the food window; the plaza empties into the shelter;
the storm eases; the crane rises over the packed arcade, the empty
rain-hazed plaza, and the still figure — and the last lightning flash
ignites the neon sign: **SQUALL**.

**THE HONEST CROWD LAW (audit 4-d P0 #2)**: the zombie FSM's flee/pursue
Navigate dispatches are MOTION-COSMETIC — every agent's goal is sampled
from its assigned destination's capacity at spawn and NEVER re-sampled
(spawn.rs:218-232, plan.rs:191-200, previz_bridge.py:203-222). There is
no mid-film ebb, no counter-flow, no panic wave: the crowd truth is
"everyone walks from their spawn strip to their spawn-sampled goal
inside the arrival box, once". The film embraces exactly that (the
tgreen lesson: design FROM the box mechanics): convergence → doorway
press → the fill → stillness. The drama lives in the EDges: the fast
band overtaking, the doorway press, the slip, the queue, the light.

The engine laws ARE the story:
- the ±5 arrival box (belt `hero_pos` (0,0) cap (±5,±5)) = the covered
  arcade floor — arrivals freeze INSIDE the shelter (the fill);
- the M6 portal divider wall (a REAL zero-thickness nav wall,
  concourse.rs:286-306) = the arcade facade line at y=6 — the sim wall
  and the set wall COINCIDE;
- **THE PORTAL AXIS LAW (audit 4-d P0 #1)**: `PortalAxis` names the
  CROSSING direction — `NORTH_SOUTH` builds the wall that runs E-W at
  y=center.y with an x-gap (concourse.rs:297-306; nav/portal.rs:20-28).
  `EAST_WEST` would build a wall at x=0 THROUGH the arrival box. The
  design pins `axis=NORTH_SOUTH, center=(0,6), width_m=10` → wall
  y=6 spanning x∈(-30,-5)∪(5,30), doorway x∈(-5,5).

## 2. Why this pushes the kit (the dog-food ledger)

| New surface | First film use | Evidence |
|---|---|---|
| M6 Queue (runtime REAL) | 9-agent line at the food window; admission events drive sfx | 4-b: advanced.py:64-134, social.rs:51-118 |
| M6 Portal | the arcade entrance (divider wall + 10m doorway) | 4-b/4-d: environment.py:105-123, concourse.rs:286-306 |
| BehaviorGraph #2 | `Sequence(QueueNode, Navigate)` bound to the chase tail | 4-b: bake.py:245-301 |
| HoldPosition population | 6 vendors standing at stall posts (count-1 pops, interval pinned 1) | 4-b: behavior.py:800-820; 4-d P0 #3 |
| M5 ragdoll | ONE straggler slips by the fountain, stays down to film end | 4-c: ragdoll.py:109-210, layout.rs:823-833 |
| read_events → sfx | QUEUE_ADMITTED/RELEASED ticks → frames → the sfx spine | 4-b: advanced.py:1865-1962 |
| Groups (two-bake) | 4 clusters among drifters (kind + shared_destination required) | 4-b: bake.py:331-408 |
| **F-TS1 bridge fix** | sidecar-gated composition post-pass + real z in the npz VIEW — the ragdoll beat's ENABLER (explicit task, §7) | 4-a: previz_bridge.py:832-866, 1032-1047 |
| **F-TS2 chase_frame pin** | explicit `chase_frame="belt"` in ALL film drivers (the r109 default-flip determinism trap) | 4-d P2 + bridge:291 |

NEW KIT FILINGS from the audits (kb entries, this round):
- **F-TS3 the portal-axis naming trap**: PortalAxis names the CROSSING,
  not the wall run (nav/portal.rs:20-28). Documented in kb + worklog
  for the crowd-kit lane's FEATURE_REFERENCE.
- **F-TS4 the emission-interval hijack**: the native reads ONE global
  interval from the ID-SORTED populations[0] (concourse.rs:201-202,
  spawn.rs:100-110, bake.py:808-821) — an appended low-id population
  with the build_zombie_population default interval 5 silently re-times
  the whole film (the plaza would be near-empty at f1). Driver-side
  law: pin interval=1 on every appended pop + assert.

FILED, NOT CHASED (honest scope): SPEED (playback_rate) and GOAL
(destination_id) layers are VIEW-invisible channels (4-a:
layout.rs:802-817 vs previz_bridge.py:837-845); DISABLE/HIDE likewise.
Un-admitted queue agents FREEZE where caught (runtime_behavior.rs:468-471)
— the design gives the queue 9 slots so all 9 admit (no strays).

## 3. Frame (belt mode — chase_frame="belt" EXPLICITLY)

Walkable: `((x_lo, -6.0), (x_hi, y_hi_all + 1.0))` = (-30,-6)..(30,15)
(previz_bridge.py:484-487). `CROWD_X_RANGE = (-30.0, 30.0)`.

Destinations (belt defaults, previz_bridge.py:495-506):
- `hero_pos` point (0,0), capacity (±5,±5) — THE ARCADE FLOOR; the set
  roof covers x∈(-8,8), y∈(-6,6) ⊇ the box; the corrected wall (y=6)
  touches neither the box nor its sampled goals.
- `flee_target` (0,14) — dispatch-only scenery (the honest-crowd law).

Portal: `Portal(id="arcade_gate", from_walkable_id="street",
to_walkable_id="street", center=(0.0,6.0), width_m=10.0,
axis=PortalAxis.NORTH_SOUTH)` — the facade line + doorway (§1).
Sim wall is zero-thickness; the SET carries the visual thickness.

Queue: `Queue(id="window_q", portal_id="arcade_gate",
admission_capacity=1, slots=<9 slots>)` — slots raw meters (world XY),
a single-file line ALONG the window counter (audit 4-e F10): the
counter is at x=6.5 facing north; slots[0]=(6.5,-4.6) is the HEAD at
the counter, then y = -3.3, -2.0, -0.7, 0.6, 1.9, 3.2, 4.5, 5.6 (last
slot 0.4m off the wall). All 9 chase agents admit (9 slots; capacity 1
spreads admission over 9 ticks). The line DRAINS from the head as each
agent reaches slots[0] (release → Navigate → the agent's spawn-sampled
box goal). Drain timeline is a flow-strip tuning knob (chase mu).

Queue graph: `BehaviorGraph(id="queue_window", root=Sequence(id="qs",
children=[QueueNode(id="qn", queue_id="window_q"),
Navigate(id="qr", destination_id="hero_pos")]))` — bound to the chase
tail `zombies_zz_chase` (9 agents, spawns in zone0's strips — the
nearest band). CAVEAT (audit 4-d): slot steering is a DIRECT steer, not
a nav route — an eastern-spawned queue agent may press the wall and
slide to the gap on avoidance; the INGEST PROBE gates this (§7 step 5).

Vendor graph: `BehaviorGraph(id="vendor_hold", root=HoldPosition())`,
bound to SIX count-1 populations, ids `zombies_stall1..stall6` (sort
BEFORE the chase id — 's' < 'z' — audit 4-f P1-1; they also sort first
overall, which is HARMLESS because the driver pins their interval to
1, neutralizing the F-TS4 id-sorted-interval hijack). Spawn boxes:
1.2m squares OFFSET from the stall centers on the plaza-facing side
(e.g. stall (-26, y) → box centered (-24.9, y)) — DISJOINT from the
barricade squares inflated by radius+margin, because the spawn
sampler ignores walls (spawn.rs:37-58; audit 4-f P1-2). Driver laws:
EVERY vendor pop gets `emission_interval_ticks=1` + hygiene replaces
(distributions + destinations); the driver RE-RUNS the chase-last
predicate after the appends (ingest's assert ran before them) and
asserts `all(p.emission_interval_ticks==1)` and
`scene.populations[0].id == "zombies_zone0"` (the envelope cap reads
DECLARED list order — vendor appends go at the TAIL; audit 4-e F16).

Groups: base bake of the post-ingest scene (queues+portals+graphs
attached — v1 IR identical, bake.py:1006-1013) →
`visible_agent_ids(base, tick=300)` → 4 clusters (2 couples, 2
families; members from zone1/zone2; leader = first member;
max_separation_m=2.0; shared_destination_id="hero_pos"; kind REQUIRED)
→ `dataclasses.replace(scene, groups=...)` → final bake.

## 4. Populations and the envelope law

Zones (y_lo, y_hi, count, min_abs_x, x_jitter) — spawn strips
|x| ∈ (min_abs_x, 30), y = the band (belt grammar):

- zone0 `(10.3, 11.5, 44, 2.5, 0.35)` — the NEAREST band = the FAST
  population: mu 2.0 σ 0.25 (cap owner; jog-clip share ~79% — eye-gate).
  (y_lo 10.3: the fountain wall top reaches y 9.9 — the 0.1m seam
  class is not worth a spawn-radius pop; audit 4-f P2-3.)
- zone1 `(11.5, 13.0, 40, 2.5, 0.35)` — the middle strollers: mu 1.2 σ 0.2.
- zone2 `(13.0, 14.0, 36, 2.5, 0.35)` — the far band: mu 1.35 σ 0.2.
- chase 9 (queue-bound): mu 0.9 σ 0.15 (a queue walks calmly; the low
  mu also slows the drain so the line holds into S10 — flow-strip knob).
- vendors 6 (HoldPosition): interval 1, hygiene replaced, speed inert.
- **N_RELEASE = 135 = (44+40+36+9 verbatim 129) + 6 vendors.** The
  driver calls `ingest_contract(C, count=129)` (the verbatim case — no
  largest-remainder rescale, tgreen's verbatim-count law) THEN appends
  the 6 vendor pops; asserts 135 after appends. The loader pin consumes
  the FINAL cache (141≠135 — audit 4-d P1 resolved: 135 exactly).

ENVELOPE LAW: cap = DECLARED populations[0].mu+3σ = 2.0+0.75 = 2.75
(previz_bridge.py:742-744). zone2 max 1.95 ✓, chase 1.35 ✓. Asserts:
zone0-first (F16), per-population speed landed, all intervals 1.

BARRICADES (belt consumes them, previz_bridge.py:489-494): stall
counters r=0.95 at (±26, 1.5/3.5/5.5/7.5) — pitch 2.0 > 2r=1.9 ✓ (the
overlap fix); fountain basin r=2.3 at (14, 7.5) (shrunken per audit
4-f P0-1 so the rim band 2.6-3.4m from center is reachable). All
squares ≥2m apart, ≥2.9m from the walkable edge (the sealed-pocket
law). Spawn bands (y≥10.3) clear every set piece.

**THE RAGDOLL PICK LAW (audit 4-f P0-1)**: no agent can pass within
1m of the basin center — the barricade square (11.7,5.2)-(16.3,9.8)
walls them out; the closest possible approach is ≈2.6-2.7m. The
faller is picked from the flow data as the agent whose path GRAZES
THE RIM BAND (closest approach 2.6-3.4m from (14,7.5), S/SW arc
preferred — that pavement is the S5 frame) near the beat tick. The
slip reads as catching the wet rim pavement; the S5 aim (§6) frames
that pavement.

## 5. Set (world module — sub-agent built, eye-gated)

Palette: storm-dusk market — dark wet ground (low-rough dark concrete),
warm stall bulbs, cool fluorescent canopy strips, red/rust canvas,
puddle mirrors. AgX discipline: warm practicals own the arcade; the
sky owns the ambient base; the ladder decides the ratio; cert stills
measure in the SHIPPING transform (AgX final, audit 4-e F18).

- Ground z=0, wet look (SSR knob + puddle discs).
- THE ARCADE: x∈(-8,8), y∈(-6,6); roof slab z≈4.2 on perimeter columns;
  entrance facade at y=6: columns at x=±5..±8, lintel over the 10m
  opening (x∈(-5,5)) — COINCIDES with the sim divider; back wall
  (south y=-6) with the FOOD WINDOW counter at x≈6.5 facing north
  (warm interior glow = the queue target); fluorescent strip fixtures
  under the canopy; sign band over the entrance (the TITLE CARRIER —
  dark acrylic until the f1009 lightning flash ignites neon "SQUALL").
- STALLS: 4 west (x≈-26) + 4 east (x≈+26) at y = 1.5/3.5/5.5/7.5 —
  counter + canvas roof + bulb string + crates.
- FOUNTAIN: circular basin at (14, 7.5), r≈2.2 — low ring wall, dark
  water disc, center jet column. The slip happens on the pavement
  beside it (NOT in the basin).
- North facades: low shopfront strip at y ≥ 15.5 (BEYOND the walkable
  ceiling 15 — the facade-swallow law).
- Bollards + benches + planters as dressing (outside flow lanes or
  barricade-backed).
- NO rain in the world module (rain layers are scene-side); NO
  bystander figure in the world module (the bystander is a scene-side
  hero-actor with a crouch key — §6).

## 6. The film (12 shots; boundaries 84/96/72 per the house grid)

| Shot | f0-f1 | Intent | Vantage (loc→aim, lens) |
|---|---|---|---|
| S1 | 1-84 | aerial: first heavy drops; the SLOW bands drift (framing shows zone1/2 strips — the edit grammar: motion starts calm) | high S aerial over the plaza, 24mm |
| S2 | 85-168 | the thunder hit: stall lights flicker; the FAST band overtakes (zone0 crossing frame); storm sky visible (streaks need a dark field) | low W oblique with sky + stall string in frame, 35mm |
| S3 | 169-264 | the streams merge toward the arcade mouth | N-edge elevated, 40mm |
| S4 | 265-348 | the doorway choke — shot from INSIDE looking out (faces rim-lit by the storm sky, not backs; the queue line at x=6.5 visible frame-right) | interior S, (2,-4,1.6)→(0,6,1.4), 35mm |
| S5 | 349-444 | THE BEAT: the slip-and-fall beside the fountain (fall at f380, thud f385, the HOLD after) | low SE of fountain (17,3.0,1.2)→(14,4.8,0.6), 50mm — RE-AIMED off the basin (the REV-2 aim was 0.5m INSIDE it; audit 4-f P1-3): the faller crosses the SOUTH pavement L→R, silhouetted on wet ground, doorway glow rim |
| S6 | 445-528 | the queue holds: side-on line against the dark east columns, warm window glow pooling right | (1.5,1.0,1.7)→(6.5,1.5,0.9), 50mm |
| S7 | 529-624 | the fill: under the canopy — exterior through the east colonnade under the eave; foreground rain sheet off the roof edge, packed interior midground, doorway glow behind | (9.5,8.0,3.2)→SW, 35mm |
| S8 | 625-720 | the plaza empties: the last stragglers cross the north plaza, rain haze thickens (the honest beat — no counter-flow) | N-edge wide, 28mm |
| S9 | 721-816 | the peak-as-equilibrium: the packed box seen through the open east colonnade from high-E oblique; the fountain pair (bystander crouch + still faller) in the empty plaza right — crescendo AND callback in one shot | (20,2,11)→(4,3,0), 35mm |
| S10 | 817-912 | the storm eases: light warms; the last queue releases | interior, doorway + window glow, 40mm |
| S11 | 913-1008 | the crane rises on the EAST flank: packed arcade left through the colonnade, the fountain pair right, empty plaza beyond; ray-cast sight line at loc0 AND loc1 (the roof occlusion check) | (13,-2,2.5)→(11,-2,11) looking N |
| S12 | 1009-1080 | title: loc0 = S11 loc1 (continuity, no cut), then the crane descends and sweeps north-above the doorway; at f1009 the last lightning flash blows the frame white 2-3f, on decay the sign band's neon ignites "SQUALL" (two flickers f1009/f1021, then steady; emission+scale keys, F-TD11 decouple). NOTE (audit 4-f): from S11's loc1 the roof BLOCKS the band — S12 owns its second key; the ray-cast gate decides the final pose (candidate loc1 (6,9.5,5.0)→(0,6.2,3.2), the band's north face) | loc0=(11,-2,11) → loc1=(6,9.5,5.0), aim (0,6.2,3.2) |

Ragdoll beat: faller = ONE agent picked AFTER the bake from the flow
data (≥1 agent passes within ~1m of (14,7.5) near the beat tick) AND
the palette key (the driver writes the cast list — faller name + the
queue/vendor names — into the ctx json; the scene module palette-keys
the faller from S2 on so the eye tracks "the one hurrying too fast").
`tick_start=190` (fall at f380-381; thud f385), `tick_end=539` (cache
end → STAYS DOWN to picture end), `drop_height_m=0.45,
impact_vz_mps=-0.6, restitution_millionths=0,
zero_horizontal_velocity=False`, `incoming_velocity=(vx_cache, 0,
-0.6)` — vx read from the KIT cache via inspect_agent (the npz has no
vx). The walk-clip-while-down class (4-c risk 2): mitigated by the S5
framing (the only horizontal capsule in frame), rain streaks, the
slide, and the cut at f444; S9/S11 see the still figure small.

sfx spine: rain hiss keyed to the intensity arc 0.5 (f1) → 1.0 (f85) →
1.15 peak (f529-816) → 0.6 (f817) → 0.25 (f1009); thunder CRACKS at
f85 and f625 (the last crack decays into the ease) + a low rumble at
f529; the fall thud f385; QUEUE_ADMITTED/RELEASED events → window-bell
ticks (read_events on the final cache, tick = frame//2, one-frame
convention noted); canopy murmur bed; title sting f1009.

Rain visibility per shot (the doorway rain curtain is the recurring
interior motif — every interior frame keeps the backlit threshold at
frame edge): S1/S11 aerials = puddle-impact rings (not streaks);
S2 = streaks against storm sky + stall-string flicker (export-safe
scale/emission keys — hide_render does not export); S4/S6/S7/S10 =
the threshold sheet; S5 = streaks against the basin + backlit door;
S8 = haze thickens; S9 = the colonnade sheet edge; S12 = the flash.

## 7. The build order (the green-light recipe + this film's deltas)

1. ~~research wave~~ DONE (4-a/4-b/4-c).
2. ~~design audit round 1~~ DONE (4-d/4-e) → REV-2 (this doc) →
   round 2 (focused: REV-2's remaining unknowns) → REV-3 final.
3. world module (sub-agent, non-visual QA + my eye on the smoke render).
4. **F-TS1 bridge fix (me, BEFORE the driver)**: the sidecar-gated
   composition post-pass in to_previz_cache (set_layout_layers +
   read_tick splice over the union of layer tick ranges, composed
   BEFORE the pre-spawn hold / keepout clamp / world transform) + real
   z from composed frames; GATED on a non-empty sidecar so unlayered
   films stay byte-identical (the r054 suite stays green); new test
   for the layered path (physics layer → npz z≠0, position composed).
   **F-TS5 loader pin override (audit 4-f P0-2)**: crowd_kit/loader.py
   :234-243 asserts npz n_agents == crowd_v6.contract.N_RELEASE (129 —
   the tgreen pin). Parameterize load_kit_cache with an explicit pin
   override (kwarg, default = the current 129 behavior); the SQUALL
   driver passes 135. Never edit crowd_v6/contract.py in place (the
   tgreen build shares it).
5. contract module (me): zones, barricades, keepouts, N_RELEASE=135,
   CROWD_SEED, chase_frame="belt".
6. INGEST PROBE (the round-3 pattern, sharpened per audit 4-f): ingest
   count=129 → attach portal/queue/graphs/vendor pops (interval 1) →
   compile → verdicts: (a) tile connectivity THROUGH the doorway (the
   reachability preflight passes trivially for street→street portals —
   a sealed door surfaces only as runtime A* failures; the probe
   checks nav tiles itself); (b) the box survives south of y=6; (c)
   the queue admits AND ≥1 QueueReleased event by a target tick (the
   head-stuck gate — no release ⇒ no drain, no sfx motif); (d) vendor
   pops keep chase-last + zone0-first after the appends; (e) spawn
   boxes disjoint from Blocked squares.
7. bake driver (me): per-zone speed map, envelope asserts, vendor
   pops, base bake → groups → final bake → ragdoll attach → the cast
   list (faller etc.) → npz via the F-TS1-composed to_previz_cache.
8. scene module (me): loader branch, palette (faller key from the cast
   list), cams per §6, sfx (events-driven), rain layers, thunder keys,
   the bystander actor (crouch key f470), the neon title.
9. flow strip FIRST (the seam detector + the queue-drain tuning knob)
   → framing probes → the storm-dusk ladder (new law family) → 12
   EEVEE stills (eye gate) → export → stage → in-app verify.

## 8. Open risks (post-audit)

- R1: the corrected-axis divider's empirical behavior — does the
  doorway route without unnatural funneling? (Probe resolves; the axis
  law itself is source-confirmed.)
- R2: ~~the ebb~~ CUT (the honest-crowd law). Residual risk: the fill
  may read static after f500 — mitigated by the queue drain, the rain
  arc, and the light warm-up.
- R3: the walk-clip-while-down class — mitigations pinned (§6).
- R4: 135 agents + composition + rain on the 3GB sandbox — the
  composition is one-time at conversion (single-digit seconds); rain
  = camera-prox layers measured in the ladder.
- R5: the two-bake pattern (base → groups → final) — fresh dirs, pins
  recorded per stage.
- R6: queue drain timeline — the chase mu 0.9 knob; the flow strip
  decides before cameras.
- R7: ~~N_RELEASE~~ resolved (129 verbatim + 6 = 135).
- R8: F-TS2 — all four drivers get the explicit belt pin this round.
- R9 (new, from 4-d): the direct-steer queue agents pressing the wall
  — the probe gates; if eastern-spawned chase agents fail to reach
  slots, re-aim the chase spawn or accept the wall-slide (it reads as
  joining the queue through the door). The head-stuck gate (≥1
  QueueReleased by the target tick) is the hard gate.
- R10 (new): zone0's jog-clip share at mu 2.0 (~79% sprint clip) — the
  eye gate on the flow strip decides whether zone0 reads as "hurrying"
  or "jogging"; mu 1.8 is the fallback.
- R11 (4-f P2-5): the S12 second key is a candidate pose — the
  camprobe ray-cast gate decides the final numbers before the stills
  round.
- R12 (4-f P1-1): vendor ids zombies_stall1..6 + the driver's
  chase-last re-assert post-append — the naming law is only as strong
  as its last re-check.
