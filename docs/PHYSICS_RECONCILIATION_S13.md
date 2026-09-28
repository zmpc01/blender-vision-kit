# PHYSICS_RECONCILIATION_S13 — two lineages, one measurement campaign

> Session-14 record. Resolves the physics-law discrepancies between the
> GitHub session-13 lineage (physics_place + 4-round usability program) and
> the GitLab session-13-rebuild lineage (re-derived 22/22 fact base +
> DESIGN_physics_ops_v4 proposal), per the reconciliation rule in
> docs/RECONSTRUCTION_S12.md ("re-run the probes and let the measurements
> decide").

## Verdict: the rebuild's fact base wins on the three disputed laws

`experiments/probe_physics_facts.py` (the rebuild's probe, preserved in
placement-lab) re-run on THIS build (Blender 4.5.13 LTS, same container
class): **ALL PASS, 22/22**, JSON at placement-lab
`output/probes/physics_facts.json`.

| Law (as recorded) | GitHub session-13 | GitLab rebuild + re-measure | Verdict |
|---|---|---|---|
| Margin pop | "~2.0 mm per contact level, compounding in stacks" | margin=1mm → pop ≤0.5mm (sub-noise); margin=2mm → pops {0.0, −0.01, −0.02} mm — **did not reproduce** | REFINED: raw Bullet does not pop per-level. The observed 2mm/level was (a) the SNAP-REPAIR layer compounding (own code, round-A note "pop compounds ~2mm/level" was about `snap` chains), plus (b) margin-config dependence in some setups. Keep directional tolerance (never-SINKS assertion) but drop the fixed 2mm expectation. |
| Commit pattern | "capture matrix_world → REMOVE rb components → write matrices" | `rb.enabled=False` suffices — 4.5 has NO data-level rb/world removal (`obj.rigid_body`, `scene.rigidbody_world` are read-only) | REFINED: disable + write matrix_world. The removal step was ops-level at best; inert-disable is the supported pattern (P7, P9 prove persistence + reload stability). |
| Scale & shapes | "collision shapes snapshot the evaluated mesh at rb_add — bake scale first" | HULL and BOX honor live scale (no bake needed); MESH remains a snapshot + thin-shell pass-through (never use) | REFINED: bake only needed for CONVEX_HULL/MESH paths with pre-rb_add scale changes — and MESH is banned anyway. The universal bake advice is over-broad but harmless. |

## What this means for the current kit code

- `scripts/physics_place.py` (round-D converged) remains the production
  implementation — its verdicts, gate semantics and usability-proven queue
  flow are intact and its directional tolerances stay SAFE under the
  refined laws (they were calibrated to a pop that turns out sub-mm in raw
  sims — i.e. they are conservative, not wrong).
- The snap cap (8mm) and margin-pop notes in AGENTS.md gotchas #58–62 now
  carry their true mechanism (repair-layer compounding, not engine law).
- `docs/DESIGN_physics_ops_v4.md` (the rebuild's 12-decision proposal:
  direction-aware verdicts, guarded snap, pre-sim NESTED refusal gate,
  non-vision-first print UX) is factually grounded in the re-measured
  base. Adopting v4 is a design-implement-review cycle for a future
  session (Track P), NOT an emergency — the current ops pass their suites.

## Lineage archaeology (for the record)

- 08:00–08:29 UTC — GitHub session-13 (physics program, usability rounds).
- 09:42–10:04 UTC — GitLab session-13-rebuild (no GitHub PAT available;
  rebuilt the fact base from the session-11 GitLab base 7eaf8dc, wrote
  DESIGN v4, stopped before implementing physics_place).
- 10:10+ — this session: repo surgery (REPO_HYGIENE_v2) on the GitHub
  line, then this merge + tiebreak.
- Merge commit keeps GitHub's production libs (strictly newer than the
  rebuild base), preserves the rebuild's docs, routes its probes to
  placement-lab (kit-scope policy).

## ADDENDUM (session-14b): the margin-pop verdict was one layer of a two-layer law

The "Margin pop" verdict above ("raw Bullet does not pop per-level —
did not reproduce") was measured on BOX-shaped stacks. The session-14b
matrix probe (placement-lab experiments/physics_facts/probe_hull_pop.py:
{BOX, CONVEX_HULL} x {margin 1, 2 mm} x {levels 1,2,3,5}, committed raw
output) refines it:

- primitive (BOX) contacts rest EXACT — the verdict above holds for BOX;
- hull contacts rest separated by ~SUM of the two bodies' margins
  (hull-primitive ~1x the hull's margin, hull-hull ~2x margin), scaling
  with margin config and accumulating per stack level (5-stack @1 mm =
  8.3 mm top drift). The rebuild lineage's "2 mm/level" was this layer.

So BOTH lineages were right about the layer they measured. Production
consequences shipped this session: physics_place gained an explicit
_RB_MARGIN constant and the oracle pop tolerance now derives from it
(max(2.5, 2*margin*1000 + 0.6) mm); T5r regression-locks the law at
margin 2 mm. The "Scale & shapes" verdict's HULL caveat is also
over-broad — probe_hull_pop section 2 measures scale honored by HULL
with AND without view_layer.update() on 4.5.13; only MESH (banned)
remains a snapshot.
