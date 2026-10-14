# DESIGN_drill.md — Film 6: THE DRILL (tform_1) — REV-1

> Golden-hour citadel parade yard. A 24-agent drill column assembles,
> wheels across the yard in formation (TRANSFORM-sample layers — the
> first film-consumption of formation presets made REAL), halts, forms
> the circle, the officers' beat (bake_interaction), breaks off. The
> LOW RAKING SUN is the new regime; the formation layers are the kit
> showcase.

## 0. Identity

- **Film**: tform_1, title **THE DRILL** (the banner + drum platform).
- **Regime (new)**: GOLDEN HOUR — sun elevation ~6°, warm raking key,
  LONG shadows across stone, dust motes in the beam. The one sun regime
  the trilogy never touched (tdawn night / tferry dusk-afterglow /
  tgreen noon / tsquall storm-dusk).
- **Setting (new)**: a stone citadel parade yard — fortress wall with
  battlements, an inner colonnade (the tsquall axial-vantage class),
  drum platform, banner poles, cobbled ground. Closed-yard geometry
  (the camera mostly INSIDE, walls outside).
- **Time**: 540 ticks @ 12 Hz = 45 s, 12 shots.

## 1. Pinned laws this film inherits (research wave 5-a/b/c)

- **Formation emulation recipe (5-a)**: formation presets are meters
  (leader-relative line/V; center-relative circle) — validation only;
  REAL slots come from OUR math: per-agent layers.
  - HOLDS: one PIN layer per agent (`position:[x,y,0]`, single payload —
    never one layer for many agents).
  - MARCH/WHEEL: one TRANSFORM layer per agent, payload
    `{"operation":"absolute","samples":[{"tick","translation":[x,y,0]}...]}`,
    samples at EVERY tick in range (piecewise-CONSTANT hold — no interp),
    sample ticks strictly inside the layer tick_range.
  - Layer names unique across the WHOLE stack (`drill{n}_{kind}_a{id}`);
    distinct `priority` per phase; ranges ABUT exactly (t1+1 after t1) —
    boundary positions must MATCH or the column teleports.
  - Legs keep playing (clip flows through); **YAW NEVER COMPOSES** —
    the film needs the composed-yaw kit fix (§7 K1) or facing stays base.
- **No layer cap** (24 agents × ~5 phases ≈ 120 layers fine).
- **First-frame law**: target ids from `agent_ids(cache)` at tick_start;
  drill pop emits interval=1 (all visible at tick 0).
- **bake_interaction (5-b)**: hand-authorable — request (participants ≥2,
  root_constraints covering [tick_start,tick_end], contact_constraints
  non-empty, `base_cache_hash` = live blake3, `worker_protocol`
  "authored-paired-clip-v1") + layer (edits = per-(agent,tick)
  AnimationEdit, unique (agent,tick), provenance EXACT-match) + motion
  (7 keys, root samples within 0.25 m/10° of the request path — author
  both from the same numbers; contacts evidence `distance_m ≤ 0.15`,
  `required=True` needs observed match). Lands as `animation_fix`
  layers → film VISIBLE for phase always, clip only with
  `clip_source="channel"` (vocabulary {0,1,2}).
  THE BEAT: two officers converge (base-sim staged), hold clip 0 idle
  across the clasp window (per-tick edits), `clip_source="channel"` on
  the whole film's to_previz_cache. NOT a skeletal salute — honest note
  in the delivery.
- **Gate law**: the composed-aware ground-contact gate exempts the whole
  declared union window (marker `layout_composed`); TRANSFORM z-lifts
  would trip OUTSIDE the window — this film stays PLANAR (z=0) so the
  gate's planar teeth never engage. Keep every layer inside the export
  window (the empty-union vanish law: driver asserts the splice ran).
- **12 Hz cache law**; fresh-dir law; pin sha256 per stage.

## 2. Cast (contract-authoritative counts)

| pop | count | role | notes |
|-----|-------|------|-------|
| drill | 24 | THE column | own population, interval=1, spawn at the north barracks gap |
| watchers | 72 | citizens on the colonnade shade line | v1 wander between shaded destinations (slow mu) |
| drummers | 4 | on the drum platform, HoldPosition graph | visual + sfx anchor |
| officers | 2 | the bake_interaction pair | converges mid-yard for the ceremony beat |
| chase | 6 | keyed hero lane | the STANDARD-BEARER (keyed, carries the banner across the yard) + the CAPTAIN (keyed) |

Total declared: 108 (a SMALLER film than the trilogy — deliberate: the
formation layers are per-agent; 24-agent precision is the stress, not
raw count; the yard reads fuller via the colonnade watchers + long
shadows). Loader pin override 108 — F-TS5.

## 3. The story spine (45 s)

| beat | ticks | content |
|------|-------|---------|
| S1-S2 yard establish | 0-96 | golden raking light, long shadows; watchers file along the colonnade; the banner reads `INSPECTION DAY` |
| S3 assembly | 96-168 | the drill squad marches in from the north gap (base sim), takes the LINE (PIN layers t≈120-168) |
| S4-S5 the wheel | 168-288 | the column WHEELS across the yard — TRANSFORM samples per agent along the arc (the signature move; drum beat on the sfx spine) |
| S6 halt + circle | 288-360 | HALT (PIN), then re-form to the CIRCLE (TRANSFORM to ring slots around the officers' point) |
| S7 the officers' beat | 360-408 | the two officers (base-sim convergence) meet center; bake_interaction idle-hold (clip 0) — the clasp; the squad holds the circle |
| S8-S9 break-off | 408-480 | the circle breaks to the dispersal line (TRANSFORM), then layers END → base resumes down the yard (film cut hides the seam: S9 is a close shot during the transition) |
| S10-S12 colors + depart | 480-540 | the standard-bearer crosses foreground (keyed); the yard empties; final wide: long shadows, the empty circle of disturbed dust (the circle mark = a darker stone ring prop, readable from the aerial) |

## 4. Crowd plan (bake stages)

- **Stage probe**: base bake (108, interval=1, pins) → ids; the wheel-slot
  math rehearsal (slots computed from formation presets + anchor reads at
  phase anchor ticks — `read_agent_at_tick` composed reads); assert the
  officers' convergence (spawn-box math so their base paths actually meet
  — the tsquall faller-picker pattern: measure, then place the beat where
  the sim agrees).
- **Stage layers**: apply the ~120 drill layers (holds/wheel/circle/
  dispersal) via `apply_layout_overrides` on the FINISHED bake (after
  groups… NO groups in this film — the drill is layer-precision, the
  watchers are base sim; queue not needed; graphs: HoldPosition for the
  drummers only). Re-assert inspect_layout conflicts == [].
- **Stage interaction**: resolve officer ids + their convergence tick from
  the cache; author request/layer/motion (the 5-b recipe, numbers from
  the SAME cache read); `bake_interaction`; assert receipt + sidecar
  layers count == 2×window_ticks.
- **Stage finish**: composed npz with `clip_source="channel"` (PROBE the
  mapping first: assert clip rows ∈ {0,1,2} mapped and the officers' hold
  window reads clip-0/idle); cast list; sfx rows (drum events authored +
  read_events if any graph events exist).
- Determinism: fresh dirs, pins recorded; the layers are pure functions
  of the base bake → re-bake reproducibility asserted (re-apply on a
  fresh clone dir, byte-compare the npz).

## 5. World module (sub-agent build, my visual gate)

- Yard ~56×40 m cobbled plane (two-tone cobble checker, warm); fortress
  wall N+E+W with battlements (modest height 6 m), inner colonnade along
  S (columns 4.5 m — the axial vantage + shade line for watchers); drum
  platform (2 m, E side); 4 banner poles with pennants (wind keys);
  the circle mark: a darker stone ring inlay (r=4 m) center-yard (the
  ceremony spot, also the final-shot payoff); dust = a light volume box
  LOW (2 m) + the golden sun; sky = MULTIPLE_SCATTERING low-sun preset
  candidates in the ladder; distant hills silhouette plane (N beyond
  wall) for the aerial.
- NO opaque roof over the yard (the tsquall axial-crane law — keep
  aerials legal); the colonnade is the shaded edge, not a lid.
- Lowercase wiring; factory purge at scene level; grounding plane.

## 6. Scene module

- Loader: `expected_agents=108`; palette: drill = deep ceremonial blue +
  gold trim (readable against warm stone), watchers = muted earth tones,
  officers = black+gold, standard-bearer = the banner carrier.
- Cameras: 12 shots. Drafts: S1 aerial NE (sun-side), S2 colonnade shade
  line (watchers + shafts), S3 assembly from the gap, S4 the wheel WIDE
  (the signature: whole column mid-arc, long shadows sweeping), S5 wheel
  CLOSE (feet + shadow sweep), S6 halt snap (the instant of PIN), S7
  officers' beat (tight pair, warm backlit), S8 circle overhead (the
  ring readable), S9 break-off close (the cut point), S10 standard-bearer
  crossing (keyed, foreground column), S11 emptying yard wide, S12 final
  aerial: the dark circle mark + long shadows + departing column.
- Crane: S4→S5 wheel crane (keyed loc0→loc1); keepout rows coupled
  (F-TD13).
- sfx spine: drum cadence (authored, ticks from the wheel), halt crack,
  the clasp beat (soft), dispersal wash, banner flutter. Fail-closed gate.

## 7. Kit lanes (this round's fixes, ordered by dependency)

- **K1 — composed-yaw (crowd-kit previz_bridge)**: inside the F-TS1
  composed windows, re-derive yaw from composed position DELTAS
  (smoothed; zero-delta → keep base yaw; speed < 0.3 → hold) + meta
  flag `layout_composed_yaw` + tests (unlayered byte-identity unchanged;
  wheel-facing assert). THE enabler for the wheel's readability.
  Design reviewed by audit before landing.
- **K2 — driver asserts (vision-kit film drivers)**: empty-union splice
  assert (the stdout-warn vanish law); warnings-capture around bake for
  field-drop accounting (film 5); layer-conflict assert.
- **K3 — filed, not landed**: `BakeResult.dropped_fields`; formations→
  layers helper promotion (film-side module this round; promote to the
  kit only if the audit argues it is general).

## 8. Light ladder (my eye)

- Sun elevation 4°/6°/9° × azimuth (raking across the wheel axis vs
  against it) × dust density 2 steps — ONE wheel-mid frame + one aerial.
  Decide on: shadow LENGTH readability (the film's visual currency),
  faces not crushed (fill via the warm bounce from the cobble — the
  direct:ambient ratio law at golden hour), Standard-transform gates.

## 9. Shot list (12)

As §6 drafts; the camprobe driver adjudicates (3+ candidates per failing
shot, the tsquall pattern). The S4 wheel-wide is the poster frame
candidate; S12 is the payoff frame.

## 10. Open questions for the audit round

- OQ1: wheel math — rigid-body arc around a moving pivot; verify the
  per-agent per-tick slot paths stay inside the yard bounds and the
  phase-boundary continuity (assembly-end == wheel-start positions).
- OQ2: does `clip_source="channel"` break the WATCHERS' clips (they are
  base 1/2 — mapped fine) and the keyed heroes (keyed RB lanes are
  Blender-side, not cache clips — confirm no interference).
- OQ3: the officers' convergence — can two v1 wanderers realistically
  meet center? If not: spawn them as a tiny population with destinations
  at the circle mark (spawn-side destination assignment — the SKILL #87
  law) — CONFIRM destination-boxes overlap the mark.
- OQ4: 24 PIN layers + 24×3 TRANSFORM layers + 48 interaction edits —
  sidecar size + compose cost per tick (read_tick × 540) — measure.
- OQ5: the banner-carry — the standard-bearer is a KEYED hero carrying a
  banner prop (prop_carry law, the kit's animated-prop placement rules) —
  confirm the PATH-REBASING law applies (the s5 law: animated-prop
  placement needs path rebasing, not current-frame re-keying).
- OQ6: drummers' HoldPosition graph on a 2 m platform — agent z on the
  platform vs the planar sim (z=0 law): the drum platform must be
  GROUND-LEVEL (a dais 0.15 m, not 2 m) or the drummers bake at z=0
  under it — CONFIRM and design accordingly.
