# DESIGN_drill.md — Film 6: THE DRILL (tform_1) — REV-2

> Golden-hour citadel parade yard. A 24-agent drill column assembles,
> wheels across the yard in formation (per-agent TRANSFORM-sample layers),
> halts, forms the circle, the officers' beat (bake_interaction), breaks
> off and marches out — the layers NEVER end mid-film. REV-2 folds audit
> round 1 (3 P0s: mid-film seam; wheel moonwalk; phase-table undercount).

## 0. Identity

- **Film**: tform_1, title **THE DRILL** (banner + drum platform).
- **Regime (new)**: GOLDEN HOUR — sun elevation ~6°, warm raking key, LONG
  shadows, low dust. Ladder axes: elevation {4,6,9}° × azimuth {raking /
  against} × **sky_strength {1.0, 0.4, 0.15}** × dust {on, off};
  exposure = late tie-breaker only (the tgolden analog of the tsquall
  sun5/sky0.15 pin — expect sun-full/sky~0.15-0.4 + warm bounce).
- **Setting**: stone citadel parade yard ~56×40 m; fortress wall N/E/W
  with battlements (6 m); inner colonnade along S (columns 4.5 m — shade
  line + the axial-vantage class); drum platform = a ≤0.05 m stone inlay
  (the planar-sim law: no risers) with drummers on the ground beside it;
  4 banner poles; the circle mark = darker stone ring inlay (r=4 m).
  **Walkable = the yard rect pulled short of the column faces by
  half-width + inflation margin; columns = Blocked squares fully inside
  the walkable; the inlays are visual-only** (no blocked squares past the
  walkable edge — the E_InvalidRange class).
- **Timeline law (the ×2 law)**: cache 541 ticks @ 12 Hz; film 24 fps /
  1080 frames; **1 tick = 2 frames**; all exported surfaces in FRAMES.

## 1. Pinned laws (research wave + audit round 1 folds)

- **Layers**: one layer per agent; PIN holds single position; TRANSFORM
  samples `{"operation":"absolute","samples":[{tick,translation:[x,y,0]}…]}`,
  ABSOLUTE cache ticks, one sample PER TICK, strictly inside the layer
  range; layer names unique across the whole stack; ranges ABUT exactly;
  `conflicts == []` asserted at EVERY phase boundary (priorities stay
  equal — no overlap resolution is expected; a conflict = authoring bug).
- **Continuity law (base↔layer included)**: every boundary — base→layer,
  layer→layer, layer→base — position-continuous within one tick step;
  the assembly PIN payload = each agent's MEASURED base position at the
  pre-tick (halt-in-place, zero teleport) then a short dress TRANSFORM.
- **No mid-film seam (P0)**: the dispersal layer extends to tick 539,
  marching the column out the north gap; the film ends before any
  layer-end exists.
- **The moonwalk law (P0 + round-2 R3)**: TRANSFORM writes position
  only — composed velocity AND composed PHASE stay BASE, and bake2 legs
  are PHASE-driven (`swing = f(phase)`; base phase is frozen under
  layer windows because advance is displacement-driven). The film needs
  ALL of: (a) **K1 (§7) re-derives composed SPEED + YAW + PHASE** from
  composed position deltas inside composed windows (φ_t = φ_{t−1} +
  |Δp|/stride, seeded from the pre-window base phase, EXCLUDING rows
  whose clip/phase came from interaction Animation edits — the
  officers' authored pin is protected), AND (b) the wheel is TIMED to
  the walk speed so slot speed ≡ base walk speed (belt and braces).
- **The wheel spec (P1 folds + round-2 R4 exact numbers)**: 12 slots on
  the line (half-span **5.5 m**, spacing 1.0 m), 2 ranks deep (half
  **0.5 m**); **pivot = the 2×12 formation CENTROID (between files 6/7
  and the ranks) — a slot pivot breaks the walk-speed law
  (r=6.083 → 1.39 m/s)**; r_max = √(5.5²+0.5²) = **5.523 m**; window
  [169,251] = 83 samples = 82 intervals → ω = (π/2)/82 =
  **0.019157 rad/tick (0.2299 rad/s)**; v_max = 0.2299×5.523 =
  **1.270 ≤ 1.3** ✓; per-tick outer-slot step 0.106 m; rigid rotation
  preserves all pairwise distances (min spacing stays 1.0 m); per-tick
  absolute samples; monotone-by-angle slot assignment for the
  circle/dispersal re-forms; **spacing assert ≥ 0.7 m at EVERY sampled
  tick of EVERY layered phase (round-2 R6 — the pinch phase is the
  dispersal morph, not the wheel)**; the swept annulus stays ≥ 1.5 m
  clear of the colonnade shade line and the dais inlay.
- **bake_interaction (5-b recipe)**: request (2 participants, root
  constraints covering the interval, ≥1 contact, live blake3
  base_cache_hash, worker_protocol "authored-paired-clip-v1") + layer
  (edits per (agent,tick), unique pairs, provenance exact-match) + motion
  (7 keys; root samples from the SAME numbers; contact evidence
  distance_m ≤ 0.15). Officers' beat: converge sub-window = phase FLOWS
  (cache-read per tick); clasp-hold sub-window = phase PINNED neutral
  (a held stance — not a floor-rate shuffle). 2×window-ticks layers.
- **clip_source="channel"**: the film bake module calls
  `bridge.to_previz_cache(..., clip_source="channel")` DIRECTLY (never
  the crowd_kit CLI — it hard-codes speed_band); receipt assert
  `digest["clip_source"]=="channel"`; the mapping probe asserts clip
  rows ∈ mapped vocabulary and the officers' hold window reads clip 0.
- 12 Hz law; fresh-dir law; pin sha256 per stage; compose cost measured
  (order 1-3 s one-time in the bridge; no per-frame cost).

## 2. Cast (contract-authoritative counts)

| pop | count | role | notes |
|-----|-------|------|-------|
| drill | 24 | THE column (2×12) | own population, interval=1, spawns at the north barracks gap; base march toward the yard; dispersal marches them OUT through the same gap |
| watchers | 72 | colonnade shade line | slow-mu Navigate between shaded destinations |
| drummers | 4 | HoldPosition graph | on the ground beside the dais inlay (E side) |
| officers | 2 | the bake_interaction pair | TWO 1-agent pops with adjacent destination boxes (~0.9 m apart, facing); arrival = the stop (ghost law reads as standing); beat window = MEASURED arrival tick |

Cache total: **102** (loader pin override 102 — F-TS5).
**Keyed heroes (branch (a) — OUTSIDE the cache)**: the STANDARD-BEARER
(Blender-side keyed actor mesh, NOT a cache agent) carries the banner via
prop_carry path-rebasing (`carry_keys` along the hero's per-frame world
path; verify_riding + gate 14 green); the CAPTAIN is the second keyed
actor. No double-drive risk (the cache never references them). CAST rows
for both keyed heroes + the two officers (resolved Zed names).

## 3. The story spine (TICKS @ 12 Hz; exported surfaces ×2 = frames)

| phase | ticks | layer state |
|-------|-------|-------------|
| march-in | 0-119 | BASE sim (spawn at the gap, destinations at the assembly area) |
| assembly dress | 120-168 | halt-in-place PIN at measured positions [120,131] → dress TRANSFORM to the 2×12 line [132,168] |
| the wheel | 169-251 | TRANSFORM wheel, 90°, ω = 0.019157 rad/tick, CENTROID pivot (R4) |
| halt | 252-299 | PIN at the halt slots |
| circle re-form | 300-360 | TRANSFORM to the ring (monotone-by-angle; chord 1.05 m) |
| circle hold | 361-420 | PIN ring (the officers' beat lives here) |
| dispersal march | 421-539 | TRANSFORM from ring slots out through the north gap at **1.55 m/s attention-march (round-2 R7: the phase-honest speed via K1-phase; end-state = head past the gap, tail stringing back mid-yard — S12 reframed as the streaming column)** |

| beat | frames | content |
|------|--------|---------|
| S1-S2 yard | 0-192 | golden raking light, long shadows; watchers file the shade line; banner `INSPECTION DAY` |
| S3 assembly | 192-336 | the squad marches in, halts, dresses ranks |
| S4-S5 the wheel | 336-504 | the column wheels across the yard (drum cadence on the sfx spine) |
| S6 halt + circle | 504-720 | HALT snap → the ring re-forms around the circle mark |
| S7 the officers' beat | 720-840 | the officers converge (measured arrival), clasp hold; the ring holds |
| S8-S9 break-off | 840-960 | the ring breaks to the dispersal line and marches out (ALL layered, no seam) |
| S10-S12 colors + the outgoing column | 960-1080 | the standard-bearer crosses foreground (keyed); the column STREAMS OUT through the gap (tail mid-yard at the cut); final aerial: long shadows + the dark circle mark + the departing file |

## 4. Crowd plan (bake stages)

- **Stage probe**: base bake (102, interval=1, pins) → ids; MEASURED
  positions at phase anchor ticks (`read_agent_at_tick`); the officers'
  arrival ticks; the wheel-slot rehearsal (spacing assert ≥ 0.7 m at
  every sampled tick; annulus clearance assert); the assembly-geometry
  check (the march window covers the gap→line distance at walk speed).
- **Stage layers**: apply the 144 drill layers (dress 24 + wheel 24 +
  halt 24 + circle 24 + hold 24 + dispersal 24) via
  `apply_layout_overrides`; `inspect_layout.conflicts == []` asserted at
  every boundary tick (not once); **keepout circles asserted ∩ layer
  samples = ∅ (round-2 R5 — the post-splice clamp would corrupt the
  formation after the pre-clamp asserts)**.
- **Stage interaction**: resolve officer ids + arrival tick; author
  request/layer/motion from the SAME cache numbers; `bake_interaction`;
  assert receipt + sidecar layer count == 2×window; unique (agent,tick).
- **Stage finish**: composed npz with `clip_source="channel"` + the
  mapping probe; cast list; sfx rows (drum cadence authored on the wheel
  + halt crack + clasp beat + dispersal wash); determinism: re-apply the
  full layer set on a fresh clone dir → byte-compare the npz.

## 5. World module (sub-agent build, my visual gate)

- Yard 56×40 m cobbled (two-tone warm checker); fortress walls N/E/W +
  battlements; colonnade S (columns 4.5 m, Blocked squares inside the
  walkable); dais inlay ≤0.05 m; circle-mark ring inlay (r=4 m); 4
  banner poles with pennants (wind keys); dust = LOW-density volume box
  2 m (the washed-pastel class guard: dust low until the aerial proves
  otherwise); distant hills silhouette N; NO roof over the yard.
- Lowercase wiring; factory purge at scene level; grounding plane.

## 6. Scene module

- Loader: `expected_agents=102`; palette: drill deep ceremonial blue +
  gold; watchers muted earth; officers black+gold; keyed heroes own
  materials.
- Cameras: 12 shots (probe-driver adjudicates): S1 aerial NE sun-side;
  S2 colonnade shade line; S3 assembly from the gap; S4 wheel WIDE (the
  signature: whole column mid-arc, shadows sweeping); S5 wheel CLOSE
  (feet + shadow sweep); S6 halt snap; S7 officers' beat (tight pair,
  warm backlit); S8 circle overhead (the ring readable); S9 break-off
  close; S10 standard-bearer crossing (keyed, foreground column; keepout
  row + camprobe cert as ONE edit); S11 emptying yard wide; S12 final
  aerial (the mark + long shadows). Crane: S4→S5 keyed loc0→loc1.
- sfx spine fail-closed.

## 7. Kit lanes (this round's fixes, dependency-ordered)

- **K1 — composed-SPEED + YAW + PHASE (crowd-kit previz_bridge)**:
  inside the F-TS1 composed windows, re-derive per-agent SPEED, YAW and
  PHASE from composed position deltas (computed on POST-clamp xy):
  speed = |Δp|·tick_hz (smoothed 3-tick); yaw = atan2(Δ) with
  **zero-delta → HOLD the last derived yaw (temporal carry), seeded
  ONCE from the pre-window base yaw (round-2 R8)**; **phase =
  φ_{t−1} + |Δp|/stride, seeded from the pre-window base phase,
  EXCLUDING interaction-edited rows (round-2 R3)**; meta flag
  `layout_composed_motion`; unlayered byte-identity unchanged; belt
  path guard comment; tests (r054 + TS1 + a wheel-facing + a
  phase-advance assert). THE enabler for honest layered motion.
- **K2 — driver asserts (vision-kit film drivers)**: empty-union splice
  assert; bake-warnings capture; conflicts==[] at boundaries; the
  clip_source receipt assert.
- **K3 — filed, not landed**: BakeResult.dropped_fields;
  formations→layers helper promotion.

## 8. Export + stage

- `tform_1` rev 1 through preflight (B3 span at build; CAST rows from
  resolved officer names + keyed heroes; naming law; sfx fail-closed);
  stage into the review app (comments ON), filmstrips + stills.

## 9. Round-2 folds (REV-3)

- R1-R8 consumed: R4 (centroid pivot + exact ω/r_max), R3 (K1 phase),
  R5 (keepout∩samples), R6 (spacing assert every phase), R7 (dispersal
  1.55 m/s + S12 reframe), R8 (yaw seed), R2 (field center — express
  doc), R1 (horizon route — express doc).

## 10. Resolved questions (audit round 1)

- RQ1: no mid-film seam (dispersal to 539).
- RQ2: K1 = speed + yaw re-derivation; wheel ALSO timed to walk speed.
- RQ3: full phase table (§3) with all PIN phases; conflicts asserts.
- RQ4: base↔layer continuity via measured halt-in-place.
- RQ5: wheel = 2×12, center pivot, ω from the walk-speed law.
- RQ6: absolute ticks; operation absolute asserted in the builder.
- RQ7: K1 yaw temporal carry; ring faces center for free (monotone
  radial approach).
- RQ8: officers' beat = flow-then-pin phases; honest note in delivery.
- RQ9: officers = two 1-agent pops, adjacent boxes; measured window.
- RQ10: clip_source="channel" via direct bridge call + asserts.
- RQ11: walkable short of columns; columns Blocked inside; dais inlay.
- RQ12: ladder adds sky_strength axis.
- RQ13: heroes = keyed actors outside the cache (branch (a)).
- RQ14: compose cost recorded (1-3 s one-time); no 10K-tick films
  without re-measurement.
