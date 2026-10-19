# DESIGN_crowd_vision_s24.md — the crowd-nav vision lane (crowd_look.py)

Status: DRAFT-2 (s24) — critique round 1 (agent-50ac1d9f) APPROVE-WITH-
AMENDMENTS: F1–F18 folded (2 P0 / 9 P1 / 5 P2 / nits); D9 DEFERRED.
Owner: vision-kit lane. Scope: the s41 crowd_obstacles bridge made crowd
obstacles DECLARED; nothing makes them SEEABLE. This design adds the
vision lane for crowd navigation/collision — the "apply native vision"
directive for the crowd/asset surfaces.

## The vision-agent story (why)

Today a vision agent authoring a crowd scene works blind on nav:
1. It scans placed geometry (`crowd_obstacles.py scan` → JSON rects).
2. It authors `CrowdScene(blocked=...)` and bakes.
3. It verifies numerically only (O11-style checks) — or worse, it
   renders a plain frame and "sees nothing wrong" (plain renders are
   UNDECIDABLE for nav geometry: a margin over-growth strangling a
   door, a blocked rect covering the only spawn exit, a walkable seam —
   none read in a plain render, all read in a purpose-built encoding).

Doctrine (SKILL): purpose-built encodings flip decidability; eyes
triage WHERE, numbers decide WHAT; overlays carry the SAME data the
engine consumes (L3 overlay-trust). The s41 engine audit adds the
headline: the engine has NO path planning — jams are expected until
routing lands (O11c pin). The eye must SEE the jam forming and the
numbers must say it is engine-truth, not an authoring bug.

## Inputs (the F1/F2 two-input contract)

- `--rects PATH` — the bridge scan output VERBATIM
  (`{"blocked": [...], "report": [...]}`; bounds are LISTS of lists —
  never assert tuple identity). These are the bytes the bake consumes.
- `--decls PATH` — CrowdScene authoring JSON. EXACT schema (N1; bounds
  are ALWAYS pair-of-pairs `[[minx,miny],[maxx,maxy]]` — the
  authoring-dataclass shape, same as --rects; the IR `{"min","max"}`
  emission form is REFUSED with a teacher message naming the one-line
  conversion): `{"walkables":[{"id":str,"bounds":bnd}],
  "destinations":[{"id":str,"walkable_id":str,"point":[x,y],
  "capacity_bounds":bnd}], "spawn_sources":[{"id":str,
  "walkable_id":str,"bounds":bnd,"start_tick":int?}],
  "populations":[{"id":str,"radius_m":[min,max]?, ...}?]}`. Unknown
  keys are IGNORED (the file is shared with real bake authoring);
  malformed pinned keys are REFUSED (exit 2). Radius provenance:
  `floor_p = 2·radius_m[1] + 0.24 m` per population (reproduces the
  1.0 m default at r_max 0.38), printed with its formula;
  `--corridor-floor` overrides. There is NO archetype radius field in
  the kit — radius lives per-population (Population.distributions.
  radius_m); any doc claiming otherwise is stale.
- `--load-blend PATH` (primary, state-carrier law) or `--scene MODULE`
  (fresh-only) — the navmap base render is the loaded scene; traj mode
  requires the blend whose bake produced the cache.
- `--bake-cache PATH` = the `bake()` result's `cache_path` (pinned:
  the exact value BakeResult.cache_path returns).

## Surface: `scripts/crowd_look.py` (one invocation, images + verdict)

### CL1 — `--navmap` (pre-bake: "is my declaration RIGHT?")
- Base render: crowd_look-owned ORTHO camera (F6 — render_angle has no
  ortho parameter; reuse its state snapshot/restore discipline only):
  `cam.type='ORTHO'`, ortho_scale = 1.2 × max(union_dx, union_dy)
  (N6), clip_start set under the measured 5.2 ortho near-plane
  bbox-cull law (placement_lib), z-lift for overlays ≥ 0.004 m
  (annotate grid precedent). Standard transform, 0 EV (F14 — no dim:
  exposure is view-transform-wide and would dim the overlays too),
  saturated opaque overlay palette (annotate precedent).
  Readiness self-assert (N2): the OVERLAY-VISIBILITY invariant, not
  whole-frame luminance — assert zero BLOWN-OUT / NEAR-EMPTY flags;
  NEAR-BLACK is expected-and-allowed for workbench base floors
  (documented exception: dark floor + saturated overlays); positive
  arm = ≥K pixels within each rendered kind's palette hue band
  (measured row).
- Overlay geometry (F16 single purge regime: all datablocks named
  `KIT_ANNOT_crowd_*` so annotate.delete_annotation_layer's 4-datablock
  prefix sweep purges them; deleted in `finally`, never saved; a test
  row asserts zero KIT_ANNOT_crowd_ residue):
  - walkable rects → green outlines; blocked (from --rects) → red
    outlines; destinations → blue; spawn sources → yellow. Outline-
    only rects (F15 — alpha fills are an UNMEASURED workbench claim;
    either a measured check row proves a 0.12-alpha tint or v1 ships
    outline-only with counts in the verdict block).
  - Labels (F17 cap): strangle-involved + P1-flagged rects first,
    then up to N=8 others; ALL ids appear in the verdict block.
- Verdict + numbers printed BESIDE the image (two-column law):
  rect counts per kind; blocked/walkable area ratio; **gap findings**:
  every rect-vs-rect and rect-vs-walkable-boundary edge gap below
  `--corridor-floor` (default 1.0 m; when --decls carries per-
  population radius_m, floor_p = 2·radius_m[1] + 0.24 m is derived
  AND its provenance printed — N1; no silent fake derivation)
  → WARN rows with coordinates.
  - P1 only when it MATTERS (F3/N3 — the exact grid-BFS spec): per
    walkable w, per distinct floor f (deduped population floors from
    --decls, else --corridor-floor): cell = f/4; grid anchored at
    floor(w.min/cell)·cell spanning w.bounds + one ring. Cell is WALL
    iff Euclidean distance(cell_center, any blocked rect on w, closed
    AABB) < f/2 (STRICT — gap == floor stays passable, matching
    "below floor"). Cell is FREE iff center ∈ w.bounds; NO boundary
    erosion (rect-vs-boundary gaps are the WARN class; WallHug stays
    WARN by design). 4-connected components; components < 4 cells
    discarded as rasterization noise. SEVERED iff ≥ 2 surviving
    components → ONE P1 row (walkable id, component count/areas,
    frontier rect ids). Reachability on the same graph: every spawn
    source's component must contain ≥ 1 destination (dest.point
    snapped to nearest FREE cell; snap distance > f ⇒
    declared-unreachable P1). ONE implementation, called from CL1 and
    CL2.
  - **Overlap class (F5/N6)**: any blocked rect intersecting a spawn
    source bounds or a destination capacity bounds, OR containing a
    dest.point (a rect can cover the goal point while missing the
    capacity box) = P1 with both ids and coordinates
    (exit-covered / declared-unreachable).
- Refusals (fail-closed, exit 2, teacher-grade): missing/unparseable
  --rects or --decls; navmap without walkables; blocked rect outside
  every walkable (the Rust compiler refuses the bake anyway — refuse
  here with the same class of message).

### CL2 — `--traj --bake-cache PATH` (post-bake: "did agents behave?")
- Decode contract (F9/N4): probe the chunk at runtime — if
  `rng["agent_count"]` exists use it and derive components =
  len(position)//4 // (tick_count·agent_count) ∈ {2,3} (use XY of 3;
  the pinned wheel's z is forced 0.0); else derive slots per the O11
  pattern. Refuse ambiguous chunks with a teacher message. A
  self-verifying decode fixture row (planted bytes → decoded shape
  asserted) makes a wheel update flip loudly. GHOST RULE (N4): a slot
  is unspawned at tick t iff its XY == the exact float32 zero pair
  (0.0, 0.0) — applied identically in density exclusion, reach, and
  displacement.
- **Telemetry at FULL resolution** (F8): decode read_range once;
  reach/penetration-max/displacement/density all compute on the full
  array; the ≤64-tick subsample applies ONLY to polyline geometry.
- Two SEPARATE passes (split-passes law):
  1. TRAJECTORY pass: base top ortho + per-agent polylines — poly
     curves WITH `bevel_depth ≥ 0.01` and z-lift ≥ 0.004 (F12: naked
     splines render nothing in workbench); spawn dots green /
     destination dots blue. A measured check row asserts colored
     pixels along a planted path (visibility, not just existence).
  2. DENSITY pass (F7/N6): per-agent-normalized occupancy over the
     full tick range — EXCLUDE tick 0 (spawn burst), EXCLUDE unspawned
     slots (the N4 ghost rule), MASK decl spawn/destination rects.
     Bin size = corridor-floor/4, anchored at the decls-union min
     corner. Single-hue monotonic ramp (named: dark→red,
     alpha-composited in Pillow; image_metrics has no colormap API —
     the ramp lives here). "Jam centroid" = argmax of the MASKED
     histogram, reported with its mask denominator. A healthy-bake
     control row (no jam planted → no saturated zone outside decls)
     guards the encoding.
- Telemetry block beside BOTH images: `reach_capacity` (final cache
  tick ∩ destination capacity bounds), `reach_ever` (any-tick
  O11c-style threshold derived from decls: dest.point ± corridor),
  max penetration into blocked cores (O11d formula), median
  displacement, jam centroid + mask denominator. "Final tick" = the
  cache tick grid (`rng["tick_count"]`), NOT scene frame_end (F19).
- Verdict classes (D7 as amended by F13) — machine-routable:
  - exit 0 = PASS or ENGINE_GAP_JAM (jam WITH the F5 overlap checks
    clean — the O11c law: expected until upstream routing lands);
  - exit 2 = refusal; exit 3 = AUTHORING_P1 (strangle severance,
    overlap class, spawn-in-obstacle, agent-off-walkable at t>0);
    exit 4 = readiness failure (look.py law).
  - `--json` artifact (N5): when passed, written on EVERY exit class
    — `verdict_class ∈ {PASS, ENGINE_GAP_JAM, REFUSED, AUTHORING_P1,
    READINESS_FAIL}` — so automation routes refusals/P1s too (exit
    codes give the coarse route; the artifact gives findings[]). Test
    rows assert verdict_class, never exit code alone.

## Decisions (as amended — attack these)

- **D1 DATA-SOURCE LAW**: each overlay kind renders only from its own
  consuming surface (blocked from --rects, walkables/dests/spawns from
  --decls, trajectories from the cache) — never re-derived from scene
  geometry for display.
- **D2 CAMERA/RENDER**: crowd_look-owned ortho cam (F6); state
  snapshot/restore discipline borrowed from render_angle; Standard
  transform 0 EV; readiness-clean self-assert.
- **D3 OVERLAY GEOMETRY**: KIT_ANNOT_crowd_* prefix (single purge
  regime, F16); outlines first (F15 measured-alpha escape hatch);
  beveled poly curves for trajectories (F12); label cap (F17).
- **D4 DENSITY PASS**: masked per-agent occupancy (F7); Pillow
  composite; named ramp; healthy-control guard row.
- **D5 TELEMETRY**: `trajectory_telemetry(positions: np.ndarray
  (ticks, agents, comp), decls: dict) -> dict` is ARRAY-BASED (F18 —
  synthetic fixtures need no wheel); full-resolution inputs (F8);
  reports BOTH reach_capacity and reach_ever with the invariant
  `reach_capacity ≤ reach_ever` (F11 — cross-checks assert the
  INVARIANT, never equality; definitional divergence is documented,
  same-definition numeric divergence is a bug). The O-battery keeps
  its independent pins.
- **D6 CLI/CONTRACT**: the two-input + scene-source contract above
  (F1/F2); --rects+--decls REQUIRED for --traj unless `--telemetry
  none` is passed explicitly, which prints WHICH stats were dropped
  and why (F10).
- **D7 VERDICT/EXIT TABLE**: 0 pass/engine-gap-jam; 2 refusal; 3
  authoring-P1; 4 readiness; machine-readable --json verdict (F13).
- **D8 TESTS**: `tests/test_crowd_look.py`, every row on the
  check()-raises pattern (n0=len(FAILURES) delta — the s23
  vacuous-score law); fixtures: planted numpy cache (one reaches, one
  penetrates, one unspawned ghost, planted jam), planted rects
  (lists-of-lists), planted strangle pair, planted overlap pair,
  healthy-bake control; one GATED row runs the real Cache decode
  (loud skip without the wheel). Battery → 41 suites.
- **D9 CATALOG SHEET**: DEFERRED (critique concurrence).
- **D10 OUT-OF-SCOPE (cross-ref)**: previz ports (ab_evaluate native
  seam, previz_canon, comments schema) are separate small rounds.

## Critique trail
- Round 1 (agent-50ac1d9f): APPROVE-WITH-AMENDMENTS, F1–F18 folded.
- Round 2 (agent-349c015a): FINAL-APPROVE conditional on N1–N6 —
  folded verbatim above (N1 the --decls schema P0; N2 the readiness
  exception; N3 the grid-BFS spec; N4 the ghost rule; N5 JSON-on-
  every-exit; N6 dest.point + bin anchor + ortho_scale). The critic
  verified live: the pinned wheel's Cache.read_range carries
  agent_count + 3×f32 positions (z forced 0.0); delete_annotation_
  layer is the 4-datablock prefix sweep; the 5.2 near-plane law is
  real (placement_lib:2258–2271).
- Implementation row order (front-loaded risk discovery): parse
  refusals → geometric battery (gaps/overlap/BFS) → decode probe →
  telemetry → density host-side → ortho-cam probe → overlays →
  traj/density passes → readiness row → CLI routing → gated real-
  cache row.

## Non-goals
- No path-planning claims: the engine gap is upstream's (issue #15);
  this lane VISUALIZES truth, it does not simulate routing.
- No new engine knobs, no force-field surfaces (M2.5 unwired — s41).
- No VLM bridges (scope doctrine).
