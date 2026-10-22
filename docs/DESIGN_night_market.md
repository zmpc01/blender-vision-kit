# DESIGN — NIGHT MARKET (the seventh film — the diversity queue's uncovered regime)

> Status: REV-2 (audit round 1 folded — GO-WITH-CHANGES, 6 P1
> amendments: the behavior-attachment plan + market-shaped probe gates;
> the D2 hoist named in the build order; the Cycles emissive-is-light
> budget + the x3.5 practicals mirror; the walkable/contract geometry
> block; the CHILD as a UAL principal (no gate drama); the export
> template gaps (the tmarket env branch + the governed-pin assert).
> P2 folds: both-engine sky probes at -8 BEFORE the eye gate; the
> steam via fog_density_for_engine wisp-scale; the linger via
> HoldPosition/Navigate attachments (NOT the tform K1 layer stack);
> the export-contract checklist + sfx spine + lowercase-knobs + the
> stills-JPG contract appended; vendor pops decision pinned; R1
> measure-first (the 60s number was invented); the s27 worklog block
> must land BEFORE this ladder starts.
> The regime: a NIGHT MARKET — the one surface none of the six films
> touches: warm dense artisan lighting at head height, narrow aisles,
> commerce beats (browsing, hawking, queueing at stalls), food steam,
> and a crowd that LINGERS (not commutes). The kit's laws to exploit:
> the night family (tferry's practicals law, tsquall's wet sheen), the
> humanoid crowd (the original x_bot FBX — RESTORED s27), and the
> corrected Cycles lane (s27 engine-map law — this film is BORN under
> the corrected engine, so its world tune is CYCLES-NATIVE with an
> EEVEE-conditional mirror pinned where the corpus needs it).

## D-NM1 — The film identity
- id: tmarket_1; name: "NIGHT MARKET (humanoid)". Module:
  scripts/scene_night_market.py (+ tmarket_contract.py / tmarket_world.py,
  the film-family shape). Span f1-f1080 (45 s @ 24 fps — the family law).
- Logline: a lantern-lit night market street; the crowd BROWSES in
  slow lanes between the stall rows while a late-delivery runner
  threads the aisles against the grain (the callout), and a vendor's
  lost child moment resolves at the food court (the second callout).
- CAST (2 principals, the family convention): RUNNER (teal — the
  against-grain threader) + CHILD (amber — the lost-and-found beat).
  THE CHILD IS A UAL PRINCIPAL at UAL_SCALE x 0.78 (audit P1: UAL
  riders sit OUTSIDE the crowd gates — POLY_BAND/RIG_HEIGHT bind the
  RH crowd template only; the scale rides matrix_parent_inverse,
  object-level, never keyed — the s26 object-fit law, not s27). Zero
  kit changes, zero gate-band rows. The 0.78-band row exists only in
  the cache-agent contingency (per-agent wrap scale + a documented
  row) — not this film's path.

## D-NM2 — The world (CYCLES-NATIVE night, the s27 law)
- Sky: Nishita at sun -8 deg (deep dusk, not black — the market glows
  AGAINST a dark blue residue; strength 0.010 Cycles / 0.10 EEVEE
  engine-conditional mirror, the tferry pattern pinned BOTH-ENGINE —
  the mirror is BUILD-TIME-READ and therefore inert without the D2
  hoist: main() sets scene.render.engine = normalize_engine_id(...)
  BEFORE build_world (the s27 scene_squall shape). UNMEASURED at -8
  (tferry's 0.012/0.12 was measured at -6): the ladder's FIRST gate is
  2-3 probe stills BOTH engines at -8 vs the tferry corpus.
- Practicals: ~14 stall lanterns = REAL point lights (warm 2700-3000K)
  + 2 food-court sodium floods (the tferry hue), with the measured
  BOTH-ENGINE mirror `_lw = 3.5 if _cyc else 1.0` (the tferry_world
  pattern — the s27 corpus-matched receipt). THE EMISSIVE-IS-LIGHT
  CORRECTION (audit P1): "emissive glows but does not LIGHT" is an
  EEVEE-era finding — under Cycles every emissive surface IS a sampled
  light, so the string-bulb Catmull loops join the light BUDGET (they
  light the aisle AND add mesh-light sampling cost; count them).
  Lantern materials pin the AgX emission caps (Emission Color = base
  rgb, strength <= ~0.95, the kb glow-surface law).
- Ground: damp cobble roughness 0.10-0.14 (the tsquall wet-sheen
  class — Cycles glossy GI reads STRONGER than EEVEE SSR; tune to the
  corpus, not to 1.0 mirror).
- Volumes: ONE gentle steam volume over the food court via
  fog_density_for_engine at a WISP-scale base (the tfog canonical is
  0.028 EEVEE / 0.040 CYCLES — Cycles reads volume THINNER, so the
  Cycles value is the HIGHER one; a flat 0.012 risks the invisible
  end). A steam-visibility row joins the eye gate. volume_bounces 1
  is the lane canonical.

## D-NM3 — The crowd contract (the s27-verified stack)
- 129 agents (the family pin), original x_bot FBX via RH_ASSETS
  (env-wins; the reconstruction .blend stays the fallback), walk 2899
  / idle 2781, _fps_guard at every import (the 24fps law).
- CONTRACT GEOMETRY BLOCK (audit P1 — the walkable is where the rects
  live): declare CROWD_X_RANGE + SPAWN_ZONES_V5 explicitly; the belt
  walkable is ((x_lo, -6.0), (x_hi, y_hi+1.0)) with y0=-6 HARDCODED in
  the bridge — so the S stall rows CLIP to z >= -6 (the south half is
  dress geometry, not interactive) unless the tform custom-walkable
  fork is consciously chosen. Blocked rects must fit FULLY inside
  walkable (E_InvalidRange refuses).
- BEHAVIOR ATTACHMENTS (audit P1 — the kit-mode default ingest is
  CHASE-shaped: build_zombie_behavior_graph pursues hero_pos and flees
  north — the commute/stream contract, the opposite of browsing).
  Per-population re-bind via the tsquall attachment pattern
  (dataclasses.replace(behavior_graph_id=...)): aisle populations get
  Navigate-to-stall-anchor destinations (capacities sized to the
  aisle widths), linger populations get HoldPosition pops at stall
  anchors, the runner stays graph-default on the keyed hero path.
  PROBE GATES re-author MARKET-SHAPED (the chase probes assert
  in_box >= 60 at the pursuit box — meaningless here): arrivals-per-
  aisle + the linger fraction + the queue band.
- The linger mechanism is the attachment pattern itself (HoldPosition
  pops put agents at anchors; the speed channel auto-selects the idle
  clip at STATIONARY_MPS 0.05) — NOT the tform K1 layer stack (bespoke
  film code, not a reusable class). K1 compose is reserved for
  pause-mid-walk only, or cut.
- VENDORS (audit P2): either 6 count-1 HoldPosition vendor pops (the
  tsquall F-TS4 pattern: loader pin 129->135, interval=1, honesty
  asserts) or declare stall keepers static dress — PICK ONE in the
  contract; this doc picks the vendor pops (the stalls read dead
  otherwise).
- Obstacles: the stall ROWS as blocked rects (the tsquall exact-rect
  class, clipped into walkable), the food court counter, 2 planter
  rows. ARRIVAL-DELTA GATE on any change (the zero-jam law).
- Queue beat: one popular stall grows a 4-6 agent queue (the tsquall
  window-queue class: releases + in-line asserts, band calibrated on
  the s27 engine — measure, never inherit).

## D-NM4 — The shots (12, the family convention)
Aerial establishing (S1) → the lantern board close-up (S2, the
designed beat) → aisle-level counter-flow (S3-S5) → the runner
against-grain (S6-S7) → the child lost beat (S8-S9) → the reunion at
the food court (S10) → pull-back (S11) → title (S12, "NIGHT MARKET",
the export-safe SCALE-keys law — hide_render does not export).

## D-NM4b — The export-contract checklist (audit P2 — every film needed these)
- a timeline MARKER per shot at f0, camera-bound to CAM_<sid>
  (the exporter hard-fails without them); CAMS_V3 7-tuple rows;
  Aim.<CAM> empties + TRACK_TO; CAST explicit roots + CA.Body.<name>
  material registry; build_scene ends with view_layer.update()
  (the gate-24 stale-depsgraph class); 12 SHOTS_V3 rows with f0/f1;
  the title = export-safe SCALE keys (hide_render does not export).
- sfx spine: emit_sfx_events (the queue beat feeds a bell/hawkers
  vocabulary; the preflight WARNs unknown names — legitimate).
- LOWERCASE KNOBS: uppercase in the scene module = the STORY_SOURCES
  vocabulary or KNOWN_NON_STORY-with-destination, else the s32
  discovery gate fail-closes — the film-specific knobs go lowercase
  in-module (the tform worked example).
- STILLS CONTRACT: the runner writes shot_<ID>.png mid-shot; the
  export consumes shot_<ID>.jpg (PNG->JPG q92, the s27 export script's
  conversion step); filmstrips pin file_format="JPEG" (the ext-replace
  law — the tsquall png class).
- The export template (scripts/s27_export_film.sh) needs: a TMARKET
  env branch (TMARKET_HUMANOID=1), the governed-pin ASSERT (git
  rev-parse HEAD == fca46ca in agent-kit before the run), and a fresh
  tmarket_filmstrips.py (the clone-seam law).

## D-NM5 — The certification ladder (s27-native)
- Build order: contract → world → scene → bake (venv, the pinned
  s26 engine 0054486) → look.py EARLY → flow strip → shot cams →
  Cycles stills 24 samples 640x360 (the s27 lane) → eye gate vs the
  corpus A/B (tferry night for the practicals, tsquall for the sheen,
  tgreen for the callout discipline) → preflight --animate-dry (the
  s27 post-animate span gate) → canonical export (agent-kit @fca46ca,
  the governed pin, ASSERTED) → filmstrips (JPEG, the sibling
  convention) → STAGE-COMMIT same micro-step → browser smoke (fps 24
  + strips 200).
- R1 MEASURE-FIRST (audit P2): the "60s lane budget" was invented —
  the family default is the runner's SAMPLES env; measure S1 first,
  ladder samples before cutting lights. The tferry_3 precedent: ~15
  real lights at x3.5 corpus-matched under Cycles.
- The color-discipline LAW from the user's tdawn_2 review (s27
  verified): the population stays the neutral clay register; color =
  callouts ONLY (teal runner, amber child). The stall lanterns may
  tint the GROUND, never the crowd materials.

## Risks / audit asks
- R1: 14 point lights + 2 floods under Cycles CPU at 24 samples —
  render time per still may exceed the 60s lane budget; mitigation:
  the light importance sampling is default-on in 5.2; measure S1
  first, ladder samples before cutting lights.
- R2: the linger micro-beats (idle overlays on walking agents) — the
  K1 class needs the compose contract from tform; if the compose
  doesn't bind on the first try, ship the walk-only lanes (the beat
  degrades gracefully) and file the compose for the next rev.
- R3: the child rig at 0.78 scale — the POLY_BAND/height gates and
  the motion gates assume the 2.051 rig; the scale must ride the
  family's height law (object-level, the s27 object-fit law) and the
  gates get a documented 0.78-band row, not a silent skip.
- R4: the aisle widths must hold the crowd's per-agent clearance at
  129 agents — the plinth-envelope lesson (tgreen: 0.90 failed at
  129, 0.55 held): measure the aisle at the bake, not by eye.
