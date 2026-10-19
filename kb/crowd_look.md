# kb/crowd_look.md — the crowd-nav vision lane (s24)

> Consumer-facing reference for `scripts/crowd_look.py`. Design (with
> the full critique trail): `docs/DESIGN_crowd_vision_s24.md`. The
> obstacle bridge it visualizes: `scripts/crowd_obstacles.py` (s41) +
> `docs/crowd_system/STATUS.md` (the engine-truth section).

## What it is

ONE invocation renders crowd-navigation truth as purpose-built
encodings WITH the numbers beside them. The doctrine it implements:
purpose-built encodings flip decidability (a strangled corridor, an
exit-covering rect, a jam — none read in a plain render; all read
here); overlays carry the SAME data the engine consumes, never a
re-derivation.

## The two-input contract (the part people get wrong)

- `--rects` = the **bridge scan output VERBATIM** (`crowd_obstacles.py
  scan --json`): `{"blocked": [...], "report": [...]}`. Bounds are
  LISTS of lists. These are the bytes the bake consumes.
- `--decls` = the **CrowdScene authoring JSON** with the EXACT schema:
  `{"walkables": [{"id", "bounds"}], "destinations": [{"id",
  "walkable_id", "point", "capacity_bounds"}], "spawn_sources":
  [{"id", "walkable_id", "bounds"}], "populations": [{"id",
  "radius_m": [min, max]?}]}`. Bounds are ALWAYS pair-of-pairs
  `[[minx,miny],[maxx,maxy]]` — the IR `{"min","max"}` emission form is
  REFUSED with the one-line conversion in the message.
- Scene source: `--load-blend PATH` (primary) or `--scene MODULE`
  (fresh-only). An empty factory scene is refused — it renders a void.

## Modes

- `--navmap` (pre-bake): top-down ortho map of the declaration — green
  walkable / red blocked / blue destination / yellow spawn outlines,
  capped flat labels (full ids live in the verdict block). Findings:
  sub-floor gaps and wallhugs = WARN rows with coordinates; P1 (exit 3)
  ONLY for what matters: walkable SEVERANCE (grid-BFS at floor/4
  cells, strict < floor/2 walls, ONE row per severance with frontier
  rects) and the overlap class (blocked ∩ spawn / ∩ destination
  capacity / covering dest.point).
- `--traj --bake-cache <BakeResult.cache_path>` (post-bake): TWO
  separate passes — (1) trajectory polylines (scale-aware bevel; the
  subsample feeds GEOMETRY only), (2) a masked per-agent occupancy
  heat pass composited in Pillow (tick 0 + ghost slots excluded, decl
  rects masked; jam centroid = masked argmax with its denominator).
  Telemetry at FULL resolution beside both: reach_capacity (final
  cache tick ∩ capacity bounds), reach_ever (any tick within
  dest.point ± corridor), max penetration into blocked cores (the O11d
  formula), median displacement, ghosts_frac. The invariant
  `reach_capacity ≤ reach_ever` holds by construction; its violation
  is a bug, not a finding.

## Verdict classes / exit table (machine-routable; --json on EVERY exit)

| exit | verdict_class | meaning |
|------|---------------|---------|
| 0 | PASS | authoring clean, agents reached |
| 0 | ENGINE_GAP_JAM | reach 0 WITH authoring checks clean — the O11c law: the engine has no path planning until upstream routing lands; NOT an authoring bug |
| 2 | REFUSED | teacher-grade input/schema refusal (incl. the IR-shape bounds, ambiguous cache chunks) |
| 3 | AUTHORING_P1 | severance, overlap class, agent-off-walkable |
| 4 | READINESS_FAIL | the tool's own output failed overlay-visibility |

## The measured laws (why the render looks like it does)

- **0.012 m outlines anti-alias away** at scene scale — rect outlines
  are 0.03 m (walkable 0.06 m, it is the reference frame) and the
  visibility gate matches HUE BANDS (RGB distance never fires on
  anti-aliased pixels blended with the gray floor).
- **A blocked outline at floor z is OCCLUDED by its own object** (the
  kiosk box swallowed its outline) — overlay z clears the scene's top
  geometry.
- **A fixed 0.015 bevel is 0.5 px** at a 19 m ortho scale — trajectory
  bevel is scale-aware (`ortho_scale / 240`).
- **Ghost slots sit at the exact float32 (0.0, 0.0)** — the density
  pass would plant a phantom blob at the world origin without the
  exclusion (the vendored kit's own viewer refuses to paper over this
  class; so does ours).

## Battery

`tests/test_crowd_look.py` — L1 contracts, L2/L2b geometry+BFS, L3
decode probe, L4 telemetry (planted, self-computing truth), L5 density,
L6 ortho near-plane probe, L7/L8 overlays + residue, L9 CLI routing +
zero-residue-after-main contract, L10 the REAL-bake O11c cross-check
(LOUD skip without the native wheel). Battery suite 41.
