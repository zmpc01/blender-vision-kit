# D17 — Seat protocol for rigged actors on real labeled furniture (R8)

> Design note for R8 ("the level INHABITED"). Status: REV-2 — critique
> round 1 (agent R8-2) adopted; all MUST-FIXes integrated. Chain state
> replayed this session (R8-1: 11/11 checkpoints exact).

## Goal

Complete the inhabit chain: walk → navigate (R7, proven) → **SIT**.
Prove that a seat surface can be derived from LABELED furniture by
probes (no manual box guessing), the kit can pose a rigged actor into
it with measured math, and the result is certified numerically like
every other mm-class claim. Fold in the F20–F23 + VK-10 friction batch
(F22 FIRST — see D17.7).

## Decisions (REV-2 amendments marked ▲)

**D17.1 — Seat derivation is probe-based, label-filtered, windowed.**
`seat_probe(target_family, approach_hint)`:
- Ray grid (pitch 0.03–0.05 m, cap 192² — F17 precedent) down through
  the family bbox union; FIRST hit per ray only; every hit classified
  by the hit object's kit_label. Only seat-family hits feed plane
  clustering. Non-family hits inside the domain at seat height =
  **contamination → STOP-AND-FLAG (exit 4)**, never silent union.
- ▲ Local floor anchor derived from LABELS (nearest floor /
  mezzanine_slab top beneath the family bbox), not rays. Seat-height
  plausibility window = [floor+0.25, floor+0.80] — kills the 0.91 m
  bed headboard shell, accepts the 0.505 m mattress.
- ▲ bbox-top plane is a LEGAL candidate (confidence penalty) for
  backless/edge surfaces.
- ▲ z-cluster tolerance 0.02 m; hits cluster in xy into seat
  CANDIDATES; one SeatSpec per candidate; pick by proximity to the
  approach target; log the rest. Handles 31-part families with
  chaise/ottoman multi-planes.
- SeatSpec: {mode: chair|edge, seat_z, plan min/max, front_edge,
  backrest_cluster?, n_hits, confidence} with the CONCRETE rule:
  n_hits ≥ 25; footprint ≥ 0.09 m² AND ≥ 0.25 family footprint;
  cluster z-stdev ≤ 0.02; second candidate share < 0.8× or
  separation ≥ 0.10 m; backrest = tall-hit cluster (seat_z+0.25…+1.0)
  behind the plane, share ≥ 0.05. Any violation → low confidence +
  STOP-AND-FLAG.
- Ships as R8 script (r8_seat.py) first; kit promotion post-study.

**D17.2 — Rigged sit = wrapper pose + ONE NLA track, three copied
strips. ▲ no base action, ever.**
- ▲ Walk copy → Sitting_Enter copy → Sitting_Idle_Loop copy sequenced
  on a single NLA track via frame_start offsets; armature base action
  None throughout (R7 strip-only law); idle strip frame_end extended
  to scene end (law 106). Kills the slot-pinning dance, the strip
  mutex, and base-action leak windows in one move. Fresh-bake law:
  copies, never imported actions.
- ▲ Wrapper z/xy keyed ACROSS the Enter window (walk-end floor pose →
  seated solve) so the clip never stands on the cushion nor hovers.
- ▲ Cut-boundary frame probe REQUIRED before the protocol freezes
  (evaluate the junction frame; assert exactly one strip drives; print
  which). Authorized fallback if boundaries are ugly: bake ONE
  composite action (walk×N + Enter + Idle×M) via ual_bake machinery /
  fcurves_new (5.x-safe).
- Pose pops at hard cuts: declared in the report (honesty); the
  two-track use_auto_blend crossfade recipe is documented as the
  future fix, not implemented this round.
- ▲ Sitting_Exit tail INCLUDED: Enter → Idle×N → Exit → stand
  (wrapper returns to floor z); exit-final ≈ standing is a free
  reverse validation of the D17.3 math.

**D17.3 — Pelvis math by MEASUREMENT.**
- Probe per actor (both are scale 1.05 — measure once, assert shared):
  wrapper at z=0, apply Sitting_Enter copy, frame_set(final), read
  evaluated DEF-hips world z (=H) + xy offset (=O) + ▲ min-z of
  pelvis-region evaluated mesh verts relative to hips (=flesh offset
  c, replaces the arbitrary 5–10 mm) + ▲ foot-bone z relative
  (=foot_z_rel, floor-clearance precondition).
- ▲ Prior sanity gate: H ≈ 0.5415 × 1.05 ≈ 0.5686 ±2% — deviation
  means the slot/pose did not apply (free correctness gate).
- wrapper_z = seat_top + c − H; wrapper_xy = sit_target_xy − R(yaw)·O.
- ▲ Idle-truth fallback: re-verify H AND xy at Idle start; mismatch →
  Idle wins, logged.

**D17.4 — Facing.** ▲ Precedence law: DERIVED facing wins. chair mode:
away from backrest cluster; edge mode: outward edge normal, sit_target
inset 0.10–0.15 m from the front edge (never bbox center on a 2 m
bed). approach_hint used only for depth axis + candidate tie-break;
disagreement > ±90° → STOP-AND-FLAG.

**D17.5 — Seated audit (numeric two-lane + renders).**
- ▲ Lane 1 (numeric truth): sphere proxies from evaluated pose-bone
  matrices vs STATIC seat-family BVHs (find_nearest from ~6 centers —
  cheap, no skinned operand): pelvis (r 0.08), thighs L/R (r 0.06),
  ▲ lumbar (DEF-spine, r 0.07).
- ▲ Lane 2 (secondary, labeled): actor evaluated mesh vs seat
  pair_contact with force=True → rows marked `unreliable-skinned`.
- Checks: ▲ |hips_z − (seat_top + c)| ≤ tol (tol = max(0.02, 2×
  measured idle hip-z range)); ▲ pelvis-to-front-edge ∈ [0.05,
  0.45×seat_depth]; ▲ thigh vs front edge + nearest labeled obstacle
  (table) in front; ▲ backrest_gap reported (TOUCHING–0.15 good,
  0.4 = floating); ▲ idle drift: hips xy ≤ 0.03, z in tol; ▲ facing:
  dot(actor_forward, away_from_backrest/edge_normal) > 0; feet:
  foot_z vs label-derived local floor (penetration forbidden, dangling
  legal; wrapper origin below floor is NOT a finding); wrapper
  upright (yaw only).
- Renders: principal's eyes (approach, contact, idle, exit) —
  vision-required. Mid-Enter cushion intersections pre-declared
  excused (law 117 analogy).

**D17.6 — Seats + preconditions (measured before commit).**
- Driver: sofa_module (living floor) — walk-then-sit chain.
- Girl: bed (mezzanine) — ▲ short straight slab walk (nav reuse on a
  second actor) then edge-sit; fallback teleport+Enter logged if slab
  clutter blocks the path.
- ▲ Preconditions verified from probe+manifest BEFORE the sit: (i)
  bed_top − H ∈ [−0.15, +0.10]; (ii) sofa: foot_z_rel ≥ H − c −
  seat_top (floor clearance); (iii) ≥ 0.5 m approach clearance along
  the walk (table is labeled — manifest query).

**D17.7 — Friction batch, ORDERED.**
1. ▲ **F22 FIRST** (own commit + own test + validator re-baseline):
   level-aware relative thresholds, calibrated from the replayed
   manifests (measure the corpus — 734-P0 adjacency noise); must
   explicitly classify actor-vs-seat-family pairs (seated AABB overlap
   is adjacency, pre-declared, not silently excused penetration).
2. F20 (AGENTS.md wrapper-shape law line), F21 (kb gap-semantics
   line), VK-10 (examples/scene_v1_basic.py drift hunk + test).
3. ▲ F23 ledger STARTS early, COMPLETES at R8 close (nav rows +
   seat rows: label → exercised_by → outcome).

**D17.8 — ▲ Session seams (stated).** Entry state =
output/r6/loft_compose.blend (pre-nav, reproducible; nav state stays
reproducible via committed scripts). Regression suite:
tests/test_r8_seat.py — synthetic hit sets (31-part sofa union, bed
shells 0.505/0.91, coffee-table contamination, two-candidate
tie-break, boundary-frame probe, wrapper math incl. yaw+flip), pure
Python where possible, Blender-dependent lane behind a probed fixture
(test_r7_route.py pattern). Artifacts: seatspec JSONs + seat reports
committed; manifest_diff at close shows only Driver/Girl rows changed.

## Risks / unknowns (residual)
- NLA junction-frame semantics — probed before freeze (D17.2).
- Sofa approach clearance / coffee table — precondition (D17.6).
- fps read at runtime (scene.render.fps).
- Memory: renders from the lite copy, one render per process.
