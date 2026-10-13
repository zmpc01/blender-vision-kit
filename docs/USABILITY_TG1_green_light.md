# USABILITY_TG1_green_light.md — the GREEN LIGHT friction ledger
# (session 16, the third film: tgreen_1 — the DAYLIGHT film)

Siblings: USABILITY_TD1* (the first film), USABILITY_TF1_last_ferry.md
(the second). The kit-push thesis this film rode: a NEW crowd shape
(two opposing streams), a NEW light regime (afternoon sun), and the
NEWEST crowd-kit capability surface (M5) evaluated honestly.

## F-TG1 — the capacity box is an ARRIVAL TRIGGER, not a container
## (CLOSED by design, before any bake — the audit round's P0)

The bridge's hero_pos capacity_bounds (−5,−5)..(5,5) is written
per-agent at spawn as the arrival rectangle; an agent freezes
(velocity 0, GHOST — excluded from neighbor lists and steering risk)
the moment its position ENTERS the box (spawn.rs:218-231,
decide.rs:36-48, perceive.rs:94-101). "Pile into a 5m box" is not a
sim concept. Design consequence: the freeze line IS x≈±5, arrived
agents are ghosts later agents ghost-walk THROUGH, and any
plaza-scale barricade at the box (a) dies at ingest when its bounds
exceed the walkable, (b) seals a nav pocket → UnreachableDestination
at scene compile (scene.rs:335-358). THE LAW: converge-film design
must derive its centerpiece geometry from the box-arrival mechanics,
not from intuition about "crushes". GREEN LIGHT's third act (the
still) is the source-true behavior embraced as story — the strongest
design move of the trilogy.

## F-TG2 — the speed envelope is PER-FILM (CLOSED, the F2 fold)

There is no global cap: the bridge pins max_speed = populations[0]'s
mu+3σ on EVERY agent (previz_bridge.py:169, 581-607). A film's zone0
plan IS the global cap; the sprint tail must fit it or the bake
assert (cloned from tferry) fires. GREEN LIGHT: far (1.42, 0.40) →
cap 2.62 ≥ chase 2.60. Coupled native clamps: samples in [0.4, 2×mu],
playback ≤ 1.5×preferred, the sprint band at VIEW ≥ 1.8 (Sprint_Loop).

## F-TG3 — no delayed emission exists (CLOSED, the F4 fold)

Every population spawns at t0 (emission_interval_ticks=1 hard-pinned;
start_tick silently inert at interval 1). "A crowd waits at the curb
until the light flips" is UNAUTHORABLE in kit mode. Films must open
with motion already underway; beat carriers (signals/boards) key over
a moving crowd. The film's honesty fix: the light gives the walk as
the pour ignites.

## F-TG4 — the daylight look is an AMBIENT-RATIO problem (the L-TG law
## family, measured)

The first ladder's wash (pastel, contrast-free: p95−p50 = 0.07) was
NOT the sky's sun disc (disc-off changed nothing — EEVEE's world
irradiance sampling ignores the tiny disc) and NOT exposure (no
clipping anywhere). It was the SKY AMBIENT swamping the sun. The cure
is the direct:ambient RATIO: sun 5.0 / sky 0.15 / angle 1° won
(measured 12 combos). AgX-noon laws: (1) tune the ratio, never
exposure; (2) the sky disc is innocent; (3) white cards need a DARK
field at noon (the night cream-on-dark law INVERTED — the charcoal
plan failed its probe); (4) glyph emission: the night distance-ceiling
(1.1-1.3) does not transfer — noon sweep 1.9/3.9/5.5, 3.9 reads.

## F-TG5 — the x-sign palette split (NEW kit pattern, proven)

Two opposing streams from ONE population set (the V5 zone row spawns
symmetric E+W strips — asymmetric x-spawn is not expressible). The
east/west identity is applied SCENE-SIDE at materialize time by the
SIGN of the agent's frame-1 x (bake2 keys tick 0 at f1 = the spawn
pose for every agent). Per-agent meshes users==1 hold; the 3 RB
statics copy-first. 65W/67E landed. The two-tone value split (cool
slate pair vs warm gray pair) reads at 640×360 where hue-only would
smear.

## F-TG6 — the review wave's catches (CLOSED, 3-f/3-g/3-h/3-i)

Zero P0s, 3 P1s + ~15 P2s across four parallel reviewers:
- the dead --seed flag (the bridge compares the CONTRACT attr — the
  override must move C.CROWD_SEED, not the call arg);
- the per-zone speed map indexed by enumerate order (a zero-count
  zone shifts every later zone silently) — now keyed by PARSED ZONE
  ID with a per-population landed-assert;
- the facades at |x| 28 swallowed the spawn strips' far end (agents
  embedded in buildings, walking out through walls in the GLB's
  first act — invisible at every certified vantage, fatal at any
  reframe) — moved to |x| ≥ 30; re-exported rev 2;
- the ladder's uninit `best`, the marker purge, the stills log
  collision (still_tf_ vs still_tg_), the flowstrip splitext nit;
- DOC drift: the design doc lagged three certified rounds (framing,
  ladder, eye) — REV-4 folds the ledger (below).

## F-TG7 — determinism re-proven + the honest-drift protocol (3-h)

tgreen pin 9f6ea8fa reproduced byte-identical in fresh reruns; tferry
8b7d4d8e reproduced cross-session. The run-1/2 pin drift was an
UNCOMMITTED draft keepout table (git-reconstructed; no 5-row state
ever committed). Hardening adopted: never reuse the default --out
across runs (it destroyed run-1 evidence); a future digest should
carry keepouts_sha256 + a per-row bite census (all 4 current rows
bite ZERO samples — pin-invisible dead weight is real).

## F-TG8 — M5 bake_interaction is RECORDED-ONLY for the film chain
## (CLOSED, the 3-c research verdict)

The bridge's read_range is no-compose BY DESIGN (lib.rs); the clip
vocabulary is frozen to {3,7} at all three gates (bridge → loader);
AnimationEdit cannot displace agents. Promotion glue (if ever):
a composed range read surface, clip-vocab widening on three gates, a
displacement channel under the frozen payload pins — >1 week, a new
contract. GREEN LIGHT shipped with zero interaction beats.

## What the third film proved about the workflow

- The design-audit-before-build discipline PAID TWICE: the two P0s
  (the freeze law + the envelope law) were caught from source before
  a line of the film existed; the plaza experiment closed in the doc
  instead of at a burned bake.
- The probe tool (tferry_camprobe → tgreen_camprobe) compressed the
  framing round to ~6x (12 shots + 9 candidates in 8 process
  launches); the stills-runner scene-path bug (the clone seam that
  rendered the FERRY's shots) was caught by the eye gate in review —
  impossible for any sub-agent (they cannot see).
- The daylight regime is now a captured law family (F-TG4); the
  trilogy spans dawn / night / afternoon.
- Sub-agent count this session: 9 (3-a..3-e, 3-f..3-i) — honest
  count; the visual gate + critical paths stayed with the principal.
