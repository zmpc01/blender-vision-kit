# RECONSTRUCTION_S12 — session-12 physics lineage rebuilt from GitLab base

> **Why this file exists.** Session 12 (the physics-engine placement
> iteration: `physics_place.py` 4 ops, T5 suite, AGENTS physics docs,
> 4 usability rounds A–D) was pushed to **GitHub only**; its GitLab
> mirror stalled at the session-11 HEAD (`7eaf8dc`). Session 13 started
> in a completely fresh sandbox WITHOUT the GitHub PAT (only the GitLab
> PAT is in scope), so the GitHub-only commits are unreachable. Rather
> than stall, session 13 **rebuilds the physics layer on the GitLab
> session-11 base**, using the session-12 recap as the design spec and
> re-deriving every physics fact with fresh probes.

## Reconciliation rule (NEVER force)

When the GitHub PAT resurfaces in a future session:

1. `git remote add github https://<PAT>@github.com/zmpc01/blender-agent-kit`
2. `git fetch github`
3. Diff `github/main` vs local `reconstructed-physics` lineage:
   - physics behavior identical (expected — same Blender 4.5.13) →
     prefer the GitHub artifacts where they are richer (usability
     findings A–D are primary evidence), port anything the rebuild
     improved on top of them, then merge the two lines on main.
   - physics behavior differs → the fresh probes in
     `tests/test_t5_physics.py` + `scripts/probe_physics_facts.py` are
     the ground truth (they run on THIS Blender build); re-run them and
     let the measurements decide.
4. NEVER force-push either remote (standing rule #2).

## What session 12 measured (spec used for the rebuild)

All facts re-verified by session 13 probes before implementation:

- **F1** — sim advances only via `frame_set()` + the rigidbody point
  cache (no `world_step` in 4.5).
- **F2** — the sim pose lives in `matrix_world` ONLY; RNA `location`
  stays at spawn. Every RNA-based reader (and the evaluated mesh
  composition) disagrees with the sim until you **commit the pose**:
  read `matrix_world`, remove the RB, write the matrix back.
- **F3** — deep overlap ejects violently (150 mm overlap → ~12 m/s
  ejection measured): the explosion hazard is real, so pre-flight
  refusal (physics_gate) matters.
- **F5** — **bullet depenetrates flat contacts to exact rest**
  (displacement = penetration depth, post-pair TOUCHING 0.0 mm) —
  verdict `REPAIRED_BY_PHYSICS`. (The original "no depenetration" read
  was a stale point-cache artifact: frames 2–N replayed the previous
  sim's cache and the new movers were never simulated.)
- **F4** — hull/mesh collision shapes are built from the evaluated mesh
  AT `rb object add` time; unapplied object scale is ignored (stale
  pre-scale shape → pass-through). Fix: bake scale at the DATA level
  before enabling RB (or use BOX shapes for box-like objects).
- **F7** — collision margin: 1–20 mm margins land mm-exact rest;
  a 40 mm margin on a 30 cm body never activates (freeze). Margin must
  be small relative to the body.
- **Cache law** — the point cache persists across object teardown
  inside one rigidbody world: new sims in the same world replay the
  old cache (mid-air stops, "freezes"). Production rule: **one sim per
  process** (the kit's one-shot patch-op model), `frame_set(1)` before
  stepping, `frame_end >= frames`.
- **Margin-pop law** — a resting body pops UP ~2 mm per stack level
  (compounding: ~8 mm at stack depth 3), never down. Verdict
  classification and the guarded snap read upward pop as rest;
  downward displacement as float/void.
- **Gotcha #58** — Blender 4.5.13 `transform_apply(scale=True)` ALSO
  zeroes `location` (4.2 did not). Kit geometry builders avoid
  `transform_apply` entirely (scale lives in the object matrix).

## Ops rebuilt (scripts/physics_place.py)

- `physics_settle` — gravity finds rest poses for named movers
  (environment auto-added as PASSIVE terrain), commit + verdict
  (SETTLED / REPAIRED_BY_PHYSICS / SLIPPED / TOPPLED / NO_SUPPORT) +
  guarded snap (closes the ≤8 mm margin pop against the measured
  support plane).
- `physics_place` — placement THROUGH physics: lift mover over the
  target xy, settle, guarded snap, post audit (one-shot solver with
  physics as the oracle).
- `physics_oracle` — the "X−5 stopped" witness: attempt the move,
  physics stops it, report NAMES the obstruction (what body/pair
  blocked the path, final gap). Refused paths restore the original
  pose (no pose leak).
- `physics_gate` — the "nothing can overlap, we simply reject" scene
  gate: pre-flight audit (incl. NESTED refusal) → sim → post audit +
  displacement checks → PASS or REJECTED with an **executable fix
  queue** (apply_patch mutations). Verify displacements feed REJECTED —
  a PASS with a contradictory queue is impossible by construction.

## Session-13 delta (improvements over the recap, if any)

Logged in worklog.md as they land. Known so far: none — the rebuild
targets behavioral parity, verified by T5 + X1 + fresh usability
rounds.
