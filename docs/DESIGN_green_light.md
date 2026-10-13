# DESIGN: GREEN LIGHT (tgreen_1) — the crossing-jam film

Status: REV-2 (post-audit; 2 auditors + 1 research note, all folds
adopted). Third film in the vision-kit lineage. Sibling films:
TERMINAL DAWN (tdawn_3), LAST FERRY (tferry_1 rev 2).

## REV-2 — the audit folds (ADOPTED, all)

- **F1 (P0, the freeze law)**: the bridge's capacity box is an
  ARRIVAL TRIGGER, not a container — an agent freezes (velocity 0,
  GHOST: excluded from neighbor lists and steering risk) the moment
  its position enters x ±5 (source: spawn.rs:218-231, decide.rs:36-48,
  perceive.rs:94-101). The crowd NEVER reaches a small island; the
  two-rank freeze line IS x≈±5. FIX (geometry = behavior): the
  crossing center is a **10m PLAZA** whose blocked-square perimeter
  coincides with the ±5 box edge — barricade (0,0,r=5.0) → Blocked
  bounds (−5,−5)..(5,5), legal (inside walkable, project.rs:820-829).
  The plaza rim IS the freeze line: streams press against the rim.
  FALLBACK (if the bake shows GIVEUP-gridlock mess instead of a
  press): drop the plaza barricade and re-scope S5/S6/S10 to the
  source-true two-rank freeze (facing ranks at x≈±5, ghosts
  interpenetrating) — the eye gate adjudicates on the FIRST flow
  strip, before any EEVEE work. OPEN RISK (auditor-flagged): the
  destination point (0,0) now sits INSIDE the blocked square —
  REV-2-round-2 must probe the native validator for a
  destination-in-blocked refusal BEFORE build (if refused: fallback).
- **F2 (P0, the envelope law)**: there is NO global 2.65 cap —
  max_speed = populations[0]'s mu+3σ applied to ALL agents
  (previz_bridge.py:169, 581-607). GREEN LIGHT's own cap:
  zone0 (1.42, 0.40) → 1.42+3(0.40) = **2.62**; chase (2.30, 0.10)
  → 2.60 ≤ 2.62 ✓ (the tferry driver assert clones with the
  tgreen numbers). Sprint-band law: VIEW speed ≥ 1.8 → Sprint_Loop
  (chase samples 2.0-2.6 sprint ✓; zone0's σ0.40 lets ~10% of
  civilians cross 1.8 — accepted, eye call). Native clamps: samples
  in [0.4, 2×mu], playback ≤ 1.5×preferred.
- **F3 (P1)**: walkable y_hi = max over ALL zones + 1 = zone2's
  2.2+1.0 = **3.2** (not 2.6). Walkable = x −30..30, y −6.0..3.2.
  North posts legal (2.8+0.35=3.15 < 3.2).
- **F4 (P1, the spawn law)**: NO delayed emission exists — all
  populations spawn at t0 (~1.4s ramp; emission_interval_ticks=1
  hard-pinned, start_tick silently inert). The film OPENS with the
  pour already igniting: S1 establishes the spawn ramp mid-motion;
  the f85 green-glyph ignition rides over a crowd already walking
  (the light changes WITH the flow — the city gave the walk and the
  crowd took it). No stationary-curb promise anywhere.
- **F5 (P1, the hero law)**: kit mode has NO hero-lane pushout
  (F-TF6); sim agents are NOT heroes. The chase 9 are the **sprint
  wave** (the vanguard that reaches the plaza rim FIRST — f~300;
  stream-toned, NOT red). The "last runner" story is carried by a
  KEYED hero (below).
- **F6 (P1, the freeze law)**: post-arrival the FSM settles
  IDLE/GIVEUP (statues) UNLESS the plaza keeps agents alive
  (F1's press hypothesis). S6/S10 are designed for the press;
  the eye gate re-cuts to the freeze if that's what the bake
  delivers. Camera + edit rhythm carry the hold either way.
- **F7 (P0, the hero set)** — both films carried TWO keyed heroes;
  GREEN LIGHT:
  - **THE STATUE** — gold living-statue performer, keyed actor at
    the plaza center (0, 0.25, 0.22). Poses: f1 statue-still;
    f355 flinch-step-back (the collide beat); f470 performance pose
    (arm raised into the crush); f760 beckon NE; f816+ final pose.
    The plaza barricade guarantees agents never reach him.
  - **THE RUNNER** — crimson keyed hero (0.62, 0.07, 0.10): E curb
    hold (24, 0.5) f1-529 (loiter poses) → break f529 (the flip-back
    is his deadline) → (14, 1.6) → (7, 2.2) → **hesitate HOLD
    (4.6, 2.6) f721-750** (S9's aim target — the HOLD law) → threads
    the N flank → steps onto the plaza f~790 → reach-to-statue f800
    → HOLD (0.6, 0.35, 0.22) f816-1080. Honesty note: the keyed
    runner threads BETWEEN live sim capsules with no collision —
    route through the thin N flank, probe 3-4 frames, never promise
    pixel-perfect avoidance.
- **F8 (P0, the signal spine)**: WALK = **green MAN glyph**;
  DON'T WALK = **orange hand**, blinking. Export-safe SCALE keys
  (0.001↔1.0) on the glyphs; three events: **f85** green ignites on
  BOTH heads (S2 = the NW head close-up); **f445** green out, orange
  hand blinks (1.0/0.001 every ~12f — the countdown clock); **f1009**
  green re-ignites under the title (the system resets, the next wave
  gathers). Fixes the title carrier + the red/orange collision + the
  S6 sag + the runner's motivation in one spine.
- **F9 (P1, the light)**: sun elevation **40° WSW** (3-4pm light;
  the title is about the signal, not the clock). The E/W facades
  throw a ~13m shade wedge across the west third: the W knot waits
  in shade and steps INTO sun during the pour (S3's free lighting
  event); capsule shadows ~1.2× height (the rosette reads as
  bodies, not disks); the statue casts a needle across the plaza.
  S11/S12's crane rides the wedge.
- **F10 (P1, the ladder protocol)**: probes at f60/f300/f400/f480/
  f760/f1050 (image_metrics: clipped% full-frame AND stripe-ROI,
  stripe mean/max luma, crowd-vs-asphalt mean-luma delta pass ≥ 0.15,
  shadow-edge stddev across a 3px band). Ladder: sun 2.0/3.0/4.0 at
  sky 0.5, then sky 0.35/0.5/0.7 at the winning sun; exposure
  pinned 0. Stripe albedo drop path 0.85 → 0.72 → 0.62 if stripe-ROI
  clipped% > 2 — never pull exposure down; worn-paint albedos
  0.78/0.64 ALTERNATING per slab (texture at the bright end).
- **F11 (P1, the emission ladder)**: the glyph is F-TD11 decouple
  (near-black housing + saturated Emission Color); strength swept
  1.9/3.9/5.5 on the f85 close-up — the night distance-ceiling
  (1.1-1.3) does NOT transfer to noon ambient. Pass = the glyph is
  the brightest saturated element in S2 with no AgX tan.
- **F12 (P1, the palette)** (albedo, linear; value-split streams):
  - West slate: (0.36,0.41,0.48) / (0.24,0.28,0.34)
  - East warm gray: (0.56,0.50,0.43) / (0.43,0.38,0.32)
  - Runner: (0.62,0.07,0.10) · Statue gold: (0.72,0.55,0.22)
  - Signal: WALK green (0.08,0.62,0.22) · hand orange (0.90,0.38,0.05)
  - Env: asphalt (0.10,0.10,0.11) · stripes 0.78/0.64 · granite
    (0.30,0.29,0.28)
  - Callout ledger per frame: red + gold + ≤1 signal color.
- **F13 (P1, geometry)**: plaza slab 10m×10m (x ±5, y ±5 — VISUAL
  differs from the barricade square: the blocked square is
  axis-aligned ±5.0; the slab dresses it with a granite apron +
  painted hatching so the square void reads diegetic). Statue
  plinth at center. TWO signal posts: NW (−4.2, 2.8) + SE
  (4.2, −2.8), rows r 0.35 (3.15 < 3.2 walkable ✓). S6 = the ONLY
  ground keepout row: (S6, 0.0, −5.2, 445, 528). S3/S9 outboard
  (N sidewalk), zero rows.
- **F14 (P1, crowd numbers)**: CROWD_X_RANGE (−30, 30). Zones:
  zone0 (y −1.6..1.6, 40, max_abs_x 20.0), zone1 (y −1.0..1.0, 36,
  23.0), zone2 (y 0.2..2.2, 44, 25.0) — 60/side, density staggered
  OFF the packing ceiling (zone2 2.2/m²; spawn-pair overlap possible
  — flow-strip check). Arrival ledger: first rim arrivals ~f300
  (sprint wave), zone0 f300-460, zone2 tail ~f508; the meet builds
  through S5 (349-444) ✓. CROWD_SEED = **8123** (new; tdawn 2026,
  tferry 4711). N_RELEASE=129 load-bearing (loader pin).
- **F15 (P2, hygiene)**: factory purge + _iter_fcurves named in the
  build order; lib commuter mesh parked at x +60 (beyond E facades,
  the aerial/crane can see y −41); no concurrent EEVEE; SAMPLES
  48-64 ONLY on S5/S6 if the f400/f480 probe shows shadow-edge AA
  noise; the bus static at the W end (x ≈ −27.5, outboard) dresses
  the closed lane; the seconds column rides the shot table below.
- **F16 (P2, M5 research verdict)**: bake_interaction is
  RECORDED-ONLY for the film chain — the bridge's read_range is
  no-compose BY DESIGN (lib.rs), the clip vocabulary is frozen to
  {3,7} at all three gates, AnimationEdit cannot displace agents.
  Filed as a kit finding (the promotion glue list: composed range
  read + clip-vocab widening + displacement channel; >1 week).
  GREEN LIGHT ships with zero interaction beats.

## 1. The story (45s / 1080f @ 24fps)

A city crossing feeds a granite plaza where a living statue performs.
The light gives the walk (green MAN, f85) with the pour already
igniting (F4 honesty); two streams converge on the plaza and PRESS
against its rim (the jam); the signal flips against them (f445, the
blinking hand — the clock); a runner gambles on the dying light,
hesitates at the plaza edge, threads the north flank and reaches the
statue as the crowd holds; the light resets (f1009) and GREEN LIGHT
titles over the rosette of bodies around the gold figure.

## 2. The crowd shape (source-probed, zero fork)

See F14 (numbers) + F1 (the plaza law) + F2 (the envelope law) +
F4 (t0 spawn) + F5 (sprint wave) + the palette split: east/west
stream identity is applied SCENE-SIDE by the SIGN of the agent's
spawn x at materialize time (per-agent meshes users==1 — the
session-13 palette law; the split is palette keying, not a sim
concept).

## 3. The shot table (spans + seconds; vantages pinned)

| # | f0-f1 | s | intent | vantage (loc → aim, lens) |
|---|-------|---|--------|---------------------------|
| S1 | 1-84 | 3.5 | the pour ignites: two knots step off as the light gives | aerial high S: (0,-26,18) → (0,2,0), 35mm |
| S2 | 85-168 | 3.5 | the green MAN ignites (the call) | NW head close-up: (−4.6,4.6,2.9) → (−4.2,2.8,2.55), 55mm |
| S3 | 169-264 | 4.0 | shade → sun: the W knot steps into light | N sidewalk: (−2,4.6,1.7) → (−16,0,1.0), 40mm |
| S4 | 265-348 | 3.5 | the gap closes; the sprint wave reaches the statue | high oblique SW: (1.5,−2.0,6.5) → (−6,0.5,0.8), 35mm |
| S5 | 349-444 | 4.0 | THE PRESS: the rim ring forms | TOP-DOWN nadir: (0,2.5,16) → (0,0.5,0), 40mm |
| S6 | 445-528 | 3.5 | the flip-back: the hand blinks, the crush holds | S margin (KEEPOUT ROW): (0,−5.2,1.6) → (0,1.5,1.4), 35mm |
| S7 | 529-624 | 4.0 | the runner breaks — the flip is his deadline | N sidewalk 3/4: (10,4.4,1.8) → (20,0.8,1.0), 50mm |
| S8 | 625-720 | 4.0 | the runner vs the closing stream | outboard E elevated: (27,6,3.6) → (18,0.8,1.0), 45mm |
| S9 | 721-816 | 4.0 | the hesitate, then the thread | N sidewalk long: (6.2,4.2,1.5) → (4.6,2.6,1.0), 65mm |
| S10 | 817-912 | 4.0 | the hold: the hand blinks over the silence | SE head foreground: (3.0,3.6,1.55) → (4.2,−3.0,2.6), 50mm |
| S11 | 913-1008 | 4.0 | the crane rises: the rosette, the wedge | crane over S margin: (−8.6,−14,3.2)→(−9.2,−6,11.0) keyed |
| S12 | 1009-1080 | 3.0 | title: GREEN LIGHT as the system resets | crane settle (keyed, per F8 re-ignition) |

Laws: aim at HOLD poses (the runner's hesitate f721-750; the
statue's f816+ final pose); the probe tool on EVERY reframe
(F-TD12 probe-camera + tferry_camprobe.py, proven and generic).

## 4. The set (world module — tgreen_world.py)

Street slab x −30..30 / y −9..9 (visual), zebra stripes y −2.2..2.2
(alternating worn 0.78/0.64), curbs N+S (h 0.15), sidewalks (N y
3.2..9, S y −9..−6 dressing), **the plaza** (10m granite apron x ±5,
h 0.10 + painted hatch border + the statue plinth at center),
2 signal posts + heads (NW/SE per F13), E/W facade blocks (x ±(28..34),
3-storey, window grids — the shade wedge), bus static at W end
(x −27.5), bollards both curbs. Factory purge + lib-mesh park at
x +60 ride in the scene module, not here.

## 5. The export contract surface (same binding law)

build_scene → ctx["scene"]; BEATS (id, t_s, label); sfx
{name|kind, frame}; render.fps pinned; exporter invocation:
--scene-dir vision-kit/scripts --crowd-mode kit --crowd-plugin
escape-previz/scripts/crowd_kit (the session-16 invocation);
package tgreen_1; stills 640×360 jpg; 96 filmstrips. Title card:
text→convert MESH→scale keys f1=0.001/f1009=1.0, charcoal
(0.07,0.07,0.08) composed over the shade wedge, Bfont advance
0.91-1.1em/char, ray-cast the sight line.

## 6. The build order (tgreen names)

1. tgreen_contract.py — ME (contract-authority; F14 numbers)
2. tgreen_world.py — SUB-AGENT build per spec §4+F12, I review
3. scene_green_light.py — ME (loader branch + palette split +
   heroes F7 + cams §3 + signal spine F8 + title F15)
4. tgreen_bake.py — ME (tferry_bake clone; envelope assert F2)
5. flow strip FIRST — THE PLAZA EXPERIMENT (press vs GIVEUP vs
   freeze; F1 fallback decision)
6. camprobe framing rounds — my eyes on every cert
7. daylight ladder (F10/F11) — the L-TG law family measured
8. stills → export → stage tgreen_1 → in-app verify

## 7. Rejected alternatives

- N-S axis (south zones outside walkable y_lo −6.0 — bridge
  hardcode); flow-through crossing (pursue target hardcoded);
  vehicles (no vehicle sim); M5 interaction beat (F16:
  recorded-only); noon sun (F9: 40° WSW wins on composition).

## REV-3 — the round-2 folds (ADOPTED; the story re-scopes on the freeze)

The round-2 source probe (task 3-d) refused the plaza THREE ways and
the re-scope it forces is a BETTER film — the freeze becomes the act,
not a defect:

- **F17 (P0, triple refusal)**: (a) the plaza barricade (−5..5)² has
  max.y 5.0 > walkable 3.2 → E_InvalidRange (project.rs:820-829);
  (b) the HARDCODED capacity box (−5,−5)..(5,5) demands walkable
  y_hi ≥ 4.0 — the fallback dies at ingest too (project.rs:869-881);
  (c) any plaza-scale centered barricade seals a nav pocket →
  UnreachableDestination at scene compile (scene.rs:335-358). FIX:
  zone2 y_hi 2.2 → **4.0** (walkable y −6..**5.0**; capacity box
  5.0 ≤ 5.0 inclusive-legal per contains_bounds) and **ZERO sim
  barricades** (the freeze line IS the statue's protection; the
  granite plaza slab is DRESSING only). The two signal-post rows
  stay (3.15 < 5.0 ✓).
- **F18 (P0, the story re-scope)**: the source-true behavior is the
  **two-rank ghost freeze** — agents freeze on first contact with
  the ±5 box, later agents ghost-walk THROUGH the frozen (arrived
  agents are steering-ghosts, perceive.rs:94-101). The film's third
  act: **the crowd stills mid-crossing** — a frozen field of
  capsule statues around the gold performer, and the keyed runner
  (immune — heroes are not sim agents) threads the still to reach
  him. The press/jam language is STRUCK; "the still" replaces it.
  The nadir S5 signature frame: the freeze completing ON CAMERA.
- **F19 (P1, the speed map)**: the driver clones with PER-ZONE
  keys (not the tferry far/near pair): far (1.42, 0.40) → cap
  **2.62**; near1 (1.30, 0.12); near2 (1.18, 0.10); chase (2.30,
  0.10) → 2.60 ≤ 2.62 ✓. Zone2 y-band now 0.2..4.0: density
  22/side in 5m×3.8m = 1.16/m² (the ceiling worry dissolves).
- **F20 (P1, keepout ledger re-derived)**: the walkable grew to
  y 5.0 — the N-sidewalk ground cams are now INSIDE it. Rows
  (FRAMES; r 1.3): S2 (−4.6,4.6, 85,168), S3 (−2.0,4.6, 169,264),
  S6 (0.0,−5.2, 445,528), S7 (10.0,4.4, 529,624), S9 (6.2,4.2,
  721,816), S10 (3.0,3.6, 817,912). Aerials row-free (the hole
  law): S1/S4(z 6.5)/S5/S11/S12. S8 (27,6) outside y ✓.
- **F21 (P1, the timing ledger)**: first arrivals ~f170 (S3 — the
  freeze BEGINS on camera), the mass stills through S4-S5, the
  last by ~f577. The runner breaks f529 into the stilling crowd;
  his hesitate hold f721-750 sits INSIDE a frozen field; statue
  flinch pose re-timed to f355 (the still completes).
- **F22 (P2, the probe recipe)**: ingest IS the F17 test (seconds,
  no bake): ingest_contract(tgreen, 129, seed 8123) must pass
  clean; then a 20-agent mini-bake + flow strip certifies the
  freeze look BEFORE any EEVEE work.

VERDICT HISTORY: REV-1 GO-WITH-CHANGES (2 P0s) → REV-2 folds →
REV-3: the plaza experiment is closed by source; the freeze film is
the design of record. Round-3 verification = the ingest probe on
the real contract (empirical, cheaper than another audit).

## REV-4 — the certified-round folds (the doc catches up to the build)

The build ran three certified rounds after REV-3 (framing probes,
the daylight ladder, the eye certifications); the 3-i audit mapped
the drift. Camera truth = scene_green_light.py CAMS_V3 / the staged
previz.json (the doc table below §3 is the REV-1 plan, kept for the
audit trail). The certified deltas:

- **Framing** (commits bd62820, 2dc5099-era): S1 (0,−36,32) 26mm
  (the 52m knot span); S2 from the CROSSING side (−4.4,1.2,2.6) —
  the glyph plates face S, the N-side cam saw the blank back; S6
  aim (0.4,0.8,1.0) 35mm; S7 (24,5.5,2.2)→(10,1.2,0.9) 40mm (his
  journey ahead); S9 (8,6,3.2)→(4,1.4,1.0) 55mm (the flood class
  at-rim); S10 (−1.5,−3.8,1.9)→(−4.2,3.35,2.55) 60mm; the crane
  keyed (S11 (−8.6,−14,3.2)→(−8,−5,9); S12 settles (−7.9,−4.9,9.4)).
- **Keepouts**: 4 rows (S2 (−4.4,1.2) / S3 / S6 / S10 (−1.5,−3.8));
  S7/S9 rows DROPPED (cams outboard, y 5.5/6.0 > walkable 5.0).
  F13's "S6 only" leftover superseded by F20, now by this.
- **Light**: the ladder winner sun 5.0 / sky 0.15 / angle 1° /
  disc-off (F-TG4's ratio law; F10's 2/3/4 ladder was the diagnostic
  that found the lever). Glyph emission pinned 3.9 (the middle rung).
- **Geometry drift**: posts at the curb lips (−4.2,3.35)/(4.2,−6.15);
  plaza apron 9×9 (clear of the ±6 bars); facades |x| 30..36 (the
  3-f review: the spawn strips run to |x|=30); bus at (−23,−7.5);
  grounding plane 500m (the ocean-horizon fix); title WHITE (0.82)
  at (2.2,0.2,2.2) (charcoal probe-failed; z 4.2/2.7 both clipped).
- **Heroes**: statue z 0.32 (plinth top), runner z 0.0; the reach
  key f816 (the BEATS label says 805 — payload text only).
- **Provenance**: rev 2 stamp 2c21c26b3a494f23, git_sha 3e852da
  (the exporter's git_sha lags HEAD by the in-flight fixes — the
  harness's dirty-at-export pattern, cross-bound by commit messages).

Design-of-record status: REV-4 == the built truth; the ledger
(docs/USABILITY_TG1_green_light.md) carries the frictions.
