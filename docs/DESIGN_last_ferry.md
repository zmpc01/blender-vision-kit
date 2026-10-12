# DESIGN: LAST FERRY (tferry_1) — the night-pier converge film

> Session-14 spin-off per the user directive: "once you exhaust the
> next steps on this test scene, go spin off another (and different)
> one to continue stress test the kit."
>
> DIFFERENT-BY-DESIGN vs TERMINAL DAWN (tdawn): night vs dawn, converge
> vs flee, 2m choke vs 6.8m gate, neon saturation vs warm glow, wet
> SSR deck vs dry diffuse floor, a keyed crane vs static pans. Same
> kit, same exporter, same review app — different physics of light.

## 1. The story (45s / 12 shots / 1080f @ 24fps, schema 2.3)

A night ferry pier in the rain. The BOARDING CALL lights the neon; the
crowd converges on the gangway; the DECKHAND holds the choke; the
LATECOMER sprints the pier edge and boards last; the ferry pulls out;
the pier empties; the lit windows recede.

- **S1** (1-84) aerial: the pier at night, thin early drift toward the
  gate — the neon reads first (calm)
- **S2** (85-168) the departure board flips to BOARDING (the call)
- **S3** (169-264) the surge ignites: the far bands pour south
- **S4** (265-348) the Latecomer enters at the pier head, checks the
  board, breaks into a run
- **S5** (349-444) lateral: the Latecomer cuts along the rail line
- **S6** (445-528) the Deckhand holds the gangway throat; the crowd
  piles into the ticket choke
- **S7** (529-624) low tracker: the Latecomer slips the bollard line
- **S8** (625-720) the Deckhand sees the Latecomer; holds the gate open
- **S9** (721-816) the beat: the Latecomer through the rail gap, the
  Deckhand waves them through (the pairing shot)
- **S10** (817-912) gangway sealed by the deckhand's arm; the crowd
  held; the pier quiets
- **S11** (913-1008) pull-back crane UP: dawn-cold streetlight floods
  the empty pier; the ferry's lit windows begin to move
- **S12** (1009-1080) title frame: LAST FERRY over the receding windows

Heroes: **Deckhand** (amber CA.Body.Deckhand — the only hot body at the
choke) + **Latecomer** (crimson CA.Body.Latecomer — the runner).
Chase-group equivalent: none — this is a CONVERGE film; the callout
group is the **crew** (4 dark-blue agents at the gangway, one tone).

## 2. The crowd shape (bridge-compatible, ZERO fork)

The bridge bakes ONE pursue target (hero_pos 0,0 ±5m capacity) — the
converge shape IS the bridge's native shape (tdawn reused it as a gate
convergence; LAST FERRY uses it as a BOARDING convergence).

- N = 129 (the loader's hard pin; density via geometry)
- Zones: far bands at the pier head (y 24..34), mid bands (12..20),
  near pockets (6..10) — same (y_lo, y_hi, count, min_abs_x, jitter)
  row shape, far-band FIRST
- Speed plan (a BOARDING crowd, not a flee): far (1.30, 0.45), near
  (1.15, 0.35), crew/latecomer tail (3.40, 0.40); max envelope =
  populations[0].mu + 3sigma >= tail mu+3sigma (fail-closed law)
- 12 Hz sim / N_TICKS 541 / FPS 24 / TOTAL 1080 (all fail-closed)
- BARRICADES: pier rails (x=±6.2 lines), bollards, the kiosk —
  DECLARED or agents walk through them (the tdawn pilaster lesson)
- CAM_KEEPOUTS: (name, px, py, f0, f1) in FRAMES (the F-TD13 law from
  birth), ground cams only, one row per ground lens + the crane's
  landing pose

## 3. The light (the kit-stress core: night AgX, measured from zero)

tdawn measured the GLOW/HOT end of AgX (emission > 1.0 desaturates to
tan; white default clips). LAST FERRY lives at the DARK end — deep
blue-black ambience, saturated neon, sodium pools. Laws to measure:

- **L-TF1**: neon signs = the glow-surface law via the NEW
  make_material(emission_color=..., emission_strength=...) params —
  dark base + saturated Emission Color, strength 2-6. First production
  consumer of F-TD11. Measure the AgX saturation ceiling for cyan and
  magenta (tdawn only measured warm).
- **L-TF2**: sodium lamp pools = warm spot cones on the wet deck; the
  POOL sells "rain" without rain geometry (no particles — they do not
  export and they OOM the 3-4GB box).
- **L-TF3**: the wet deck = dark base + roughness 0.10-0.18 + EEVEE
  SSR (screen-space reflections ON in stills; glTF loses it — the
  stills are authoritative, same as tdawn's emission).
- **L-TF4**: sky strength 0.02-0.08 (night) + exposure +0.3 — measure
  the floor where the crowd silhouette dies (tdawn's 0.35-0.5 day law
  does NOT transfer down two orders of magnitude).
- Palette discipline from birth (the user's S1 law): neutral crowd
  register, identity color ONLY for Deckhand/Latecomer/crew tone.

## 4. The set (world module)

- Concrete pier deck 26 x 44 (x ±13, y -2..42) over a water plane
  (y -2..42, extends past the pier sides) — the deck sits at z=0,
  water at z=-0.55 with a visible edge (the drop reads)
- The **ferry**: a dark hull silhouette docked at the south end (y<-2),
  lit cabin windows (warm strips), the funnel; it does NOT move in
  camera (the recede is S11/S12 framing + light, not animation)
- The **gangway**: the 2m choke at (0, 2) — rails both sides, the
  ticket kiosk beside it, the crew line
- Neon: the ferry-line sign (cyan, "HARBOR LINE" as a bar composition
  — text objects do not survive glTF as curves; convert to mesh like
  the tdawn title), the BOARDING board (magenta), the lamp posts
  (sodium amber)
- Rails + bollards + kiosk + stacked crates (dressing with keepouts)
- The title card: SAME export-safe pattern (scale keys, converted
  mesh, warm cream against the dark)

## 5. The camera grammar (different: a keyed crane)

- Ground lenses at 1.6-3.0m (the choke shots), one LOW water-level
  lens (z=0.45 — the reflections read), and the S11/S12 CRANE: loc +
  aim BOTH keyed (a real ascending dolly, 2 keys + ease) — exercises
  the exporter's animated-cam TRS path harder than tdawn's single
  ground dolly
- Every ground cam gets its F-TD13-form keepout row (frames, not
  seconds — from birth)
- The pipeline uses look.py --probe-camera on every reframe (F-TD12
  as a standard tool, not a forensic)

## 6. The export contract surface (same binding law)

- SHOTS_V3 rows (id, f0, f1, intent); CAMS_V3 7-tuples; markers per
  shot; CAST roots Deckhand.Root / Latecomer.Root; CA.Body.* materials
- UPPERCASE = mapped vocabulary ONLY (the unmapped-constant gate);
  internal wiring lowercase
- build_scene ends with view_layer.update() (F-TD5, now kit-fixed
  upstream but the scene-side sync stays — cheap insurance)
- make_material emission params for ALL glow surfaces (L-TF1)
- emit_sfx_events: the boarding chime (f85), the gangway clang (f721),
  the horn (f913)

## 7. Session-14 slice (what THIS session ships)

Design (this doc, reviewed) → contract module → world module (deck,
water, ferry, gangway, neon via the new params) → **first LOOK
(no crowd)**: does the night read? Is the neon saturated not clipped?
Does the wet deck reflect? — then commit + hand the build order
(bake → flow-strip → shot cams → EEVEE pass → stills → export) to the
next session via HANDOFF. The vertical slice proves the RISKIEST laws
(L-TF1..4) before the crowd work lands.

## 8. Rejected alternatives

- **Crossflow** (two streams crossing): needs a bridge fork (two
  pursue targets) — against the zero-fork pattern; converge is native.
- **Rain particles**: no glTF export, OOM class on 4GB — the wet deck
  + lamp pools carry the weather honestly.
- **Ferry departure animation**: the hull moving reads as a slide
  without wake/sound mass; the recede is better sold by light + framing.
- **A second film at dawn**: tdawn already owns that light; the dark
  end is the unmeasured regime.

## REV-2 — the peer-review folds (ADOPT-WITH-CHANGES, all adopted)

- **[P0] speed envelope**: tail → **(2.30, 0.10)** = 2.60 ≤ envelope
  2.65 (populations[0] mu+3σ is a GLOBAL cap — the bridge silently
  clamps; tdawn passed by equality). All-tail ≥ 1.8 keeps Sprint_Loop.
  The Latecomer's sprint is AUTHORED (hero), not a sim population.
- **[P0] the throat is AT (0,0)**: the bridge hardcodes hero_pos
  (0,0)±5 capacity — the gangway pinch point moves to the origin; the
  kiosk stays as dressing beside it (y≈2).
- **[P0] the walkable reaches y=−6** (hardcoded): the deck gains a
  LANDING APRON y −6..−2 at the choke; the rest of the south edge is
  barricade-lined; water extends y −10..46 (the hull floats on
  something; the recede reads).
- **[P1] crew = the pinned 9-deep tail** (CHASE_TAIL=9, far-band
  spawn), ONE dark-blue tone, restaged as "crew answering the call
  from the pier head". No 4-agent fiction.
- **[P1] zone rows pinned**: (24,34,44,1.4,0.5) / (12,20,40,1.4,0.5) /
  (6,10,36,1.2,0.5) — sums 120; min_abs_x shapes the spawn strips.
- **[P1] CROWD_X_RANGE = (−6.0, 6.0)**: the outboard margin is
  crowd-free BY CONSTRUCTION — the ±6.2 rails need NO barricade rows;
  the margin carries bollards/lamps/crates/crane track/the low lens.
- **[P1] gangway-rail barricade centers x=±1.55** (2r-wide square
  inflation would strangle a ±1.0 declaration → 0.9m channel; ±1.55
  keeps 2.0m clear). Verify on the first flow strip.
- **[P1] the crane flies over the outboard margin/water** (x≈−9):
  zero keepout rows, the "keepout under the aerial" lesson never
  fires. The z=0.45 water-level lens keeps its row.
- **[P1] SSR knob measured**: 5.2's `use_ssr` does not exist — the
  scene sets `scene.eevee.use_raytracing = True` (+ screen_trace
  quality); roughness 0.10-0.18 < trace_max_roughness 0.5 ✓.
- **[P1] night sky**: `sun_elevation_deg ≈ −6` (twilight blue —
  strength alone over a 25° day sky reads dim DAY); sweep strength
  0.02/0.04/0.08 at exposure +0.3, one variable at a time; silhouette
  ladder: sky→0.12-0.15, then sodium-pool spot energy on crowd lanes,
  then exposure +0.5 max.
- **[P1] ferry window strips**: warm emission sweep 0.45/0.70/0.95,
  never >0.95 (the tan law is input-curve, night does not relax it);
  the S11/S12 recede = strength keyed DOWN; emission-key plan: board
  flip @f85, window recede @f913+.
- **[P2] neon sweep 0.95/1.9/3.9** (doubling from the warm cap —
  expect the cyan/magenta ceiling 1.9-3.9; 6 washes to white).
- **[P2] S1 composes ALONG the 44m axis** (a strip, not a slab);
  freeboard 1.2-1.8m (0.55 reads from no aerial); "water-level lens"
  renamed deck-level lens z=0.45 over water z=−0.55; pier head
  y 35..42 is dressing-only (walkable tops at y_hi_all+1=35).
- **[P2] SAMPLES law bound in**: tferry_stills.sh clones tdawn_stills
  verbatim (one EEVEE process per shot + SAMPLES override); S11/S12/
  deck-level lens pre-tagged reduced-sample.
- **[P2] slice scope fixed**: 6-10 stand-in capsules at three depths
  (the L-TF4 silhouette floor needs agents to measure); the
  Latecomer's authored path keyed in-slice; contract pins (CROWD_X_
  RANGE, zones, keepouts incl. crane strategy, CROWD_SEED = a NEW
  identity ≠ 2026) land WITH the slice; BEATS rows spelled; S9's rail
  gap sits NORTH of the capacity box (y 7-9 east rail, nothing routes
  there) with the choke-staging fallback.
