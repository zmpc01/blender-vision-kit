# DESIGN: physics-gated placement (physics_place module) — v3

> Status: v3 — post gate round 2 (verdict: AMEND, 8 text-level fixes,
> no architecture change; all incorporated). Design CONVERGED —
> implementation may proceed.
> v1→v2 headline: **F5 overturned by re-measurement** — bullet fully
> depenetrates flat contacts to exact rest (5/25/100mm → TOUCHING 0.0,
> displacement = penetration depth). Physics gains a third role:
> REPAIRER (explicit, recorded — never silent). v1's F5 was a stale
> point-cache artifact (the very hazard F8 names).
> v2→v3: place() audits full neighbor set; gate never repairs;
> REPAIR_SIMULATED vs REPAIRED_BY_PHYSICS; oracle target semantics
> pinned (bbox bottom, bottom-center move); lift clamp; teardown covers
> environment + timeline restore; PENETRATING_AT_END verdict;
> restitution=0 codified.

## Problem statement

Scenes built by agents still penetrate "a ton": the geometric tools
(place_on/audit) are precise but only check what the agent thinks to
check, pairwise, with the right pairs. The user's proposal: use the
physics engine so that *nothing can overlap* — place through physics,
gravity settles what floats, and if an object refuses to reach its
target, the physics outcome names the obstruction (jeep door, stair
nose). Goal: refine this into a rigorous, mm-honest toolset that
composes with placement_lib (not replaces it).

## Validated fact base (Blender 4.5.13, headless)

Provenance (gate B2): F3/F4/F5/F6(fix1 arm)/F8/F12 are backed by
committed probes + raw outputs under `experiments/physics_facts/`.
F1/F7/F9-F11 summarize uncommitted spike history — author-verified.
F13/F14 are gate-reviewer measurements, not yet committed; they become
self-verifying via T5 (frame_end handling; non-mesh abort in T5e).

| # | Fact | Source (file → output) |
|---|------|------------------------|
| F1 | No `bpy.ops.rigidbody.world_step` in 4.5; sim advances via `scene.frame_set()` | spike_v13_final.py → spike_v13_output.json (F1 err trace, spike v2 committed history) |
| F2 | `frame_set(1)` + re-step = deterministic re-sim; identical end poses | spike_v13_final.py D_determinism (via frame_set(1) reset; v5 F9 cache-wipe variant identical) |
| F3 | Rest precision: flat BOX mover on BOX floor lands **exact** (pair_contact TOUCHING 0.0), margins 1-20mm | spike_v13_output.json fix2_margin |
| F4 | CONVEX_HULL mover residual ≈ 1-2mm above exact (snap closes) | spike_v13_output.json b2_hull_mover (2.0mm), fix1_ico_convex (1.0mm) |
| F5 | **Bullet fully depenetrates resting overlaps** (flat contacts): 5/25/100mm all → exact rest, TOUCHING 0.0, displacement = penetration depth, no explosion. v1's "preserved" was stale-cache replay | probe_f5_reverdict.py → f5_reverdict_output.json |
| F6 | RB collision shapes snapshot the EVALUATED mesh at rb_add: object scale must be data-baked + view_layer.update() first, else shape ignores scale → no collision | spike_v13_output.json (v12 C all-shapes fail vs fix1 pass) |
| F7 | RB sim pose lives ONLY in matrix_world; RNA location stays at spawn; commit = capture mw → objects_remove → write mw → update → clear_bvh_cache | spike_v13_final.py commit() + v10 S5 history |
| F8 | Point cache persists across object teardown → ALWAYS `frame_set(1)` before a sim; one sim per world per process is the clean model | v13 anomalies (mid-air 233mm stop, frozen settles) → all cleared by reset; v12 D |
| F9 | GOTCHA #58: `transform_apply(scale=True)` in 4.5.13 also zeroes RNA location — never use in kit code; data-transform instead | /tmp/mini.py repro, kit gotcha #58 entry |
| F10 | rb ops poll fails on stale context after `read_factory_settings` unless selection+active are re-established; probe_f5_reverdict.py runs 3 factory-reset cases in one process successfully (deselect-all + set-active before every rb op) — keep that pattern everywhere | v10/v11 tracebacks + committed probe |
| F11 | `scene.rigidbody_world` / `obj.rigid_body` read-only RNA; teardown via ops only | v8/v11 AttributeErrors |
| F12 | After commit (rb removed), to_mesh is LOCAL again; placement_lib needs NO changes | v12 E_space, v13 all pair reads sane |
| F13 (new, gate B5) | Sim freezes at `point_cache.frame_end`; ops must assert `frame_end ≥ frames` | gate round-1 reviewer measurement (z=0.5209 with frame_end=4); codified in impl |
| F14 (new, gate B4) | A selected non-mesh object aborts `rigidbody.objects_add` for the WHOLE set ("Can't add Rigid Body to non mesh object") | gate round-1 reviewer measurement; impl: deselect-all + mesh-only sets |

## Architecture: hybrid thesis (D1, amended)

**Geometry owns precision; physics owns topology and simple repairs.**

- place_lib = exact mm contact solve + audit; final word on contact state.
- physics roles:
  (a) SETTLER — finds support configuration (arbitrary shapes, stacks,
  tilted rest) without the agent solving it;
  (b) WITNESS — the outcome names obstructions (jeep-door oracle);
  (c) REPAIRER — depenetration (F5) resolves simple penetrations to
  exact rest; used ONLY in explicit repair modes, always recorded as a
  repair with start/end evidence, never laundered into "SETTLED";
  (d) GATE — whole-scene plausibility check.
- Physics output is NEVER trusted for mm: every op ends in audit +
  optional guarded snap (D7).

## Module: `scripts/physics_place.py`

Common machinery (shared by all ops):
- `_prep(objs)`: mesh-only filter (F14: deselect-all first; non-mesh →
  `excluded` with reason), animated/skinned objects refused via
  placement_lib `_guard_anim` (B3) → excluded with channel names;
  hidden/holdout excluded; parent-roots collapse: children of a mover
  ride along (selected root only, B4a); multi-user mesh data
  (`data.users > 1`) refused unless `allow_copy=True` (single-user copy,
  reported, B4b); modifiers present → scale-bake refused (audited
  geometry ≠ simulated shape, B4c); object scale ≠ 1 → refused with
  `scale_unbaked` list unless `allow_bake=True` (bakes via
  `mesh.transform`, no transform_apply — F9).
- `_sim(movers, env, frames)`: F8 reset (frame_set(1)), world ensure
  (create if missing; assert `point_cache.frame_end ≥ frames` — F13),
  rb_add all (view_layer.update before each — F6; shapes per D2),
  step frames with early-exit (D8: all movers < 0.1mm for 5
  consecutive frames; late-window creep check vs bullet deactivation,
  gate nb-2), read end matrices.
- `_teardown(restore=None)`: capture pre-sim matrices for ALL rb-added
  objects (movers AND PASSIVE environment); deselect-all (F14);
  `objects_remove` every rb-added object (environment included — rb
  settings persist on objects after `world_remove`); `world_remove`
  only if we created it; write matrices (restored pre-sim snapshots
  when `apply='none'` / restore mode); restore `scene.frame_current`
  to its entry value (stepping moved the timeline; animated bystanders
  would otherwise end displaced); view_layer.update();
  `clear_bvh_cache()`. Movers with verdict ESCAPED are additionally
  restored to pre-sim matrix when `apply='end'` — an escaped object
  must not be left wherever it flew; restore reported. UNCONDITIONAL
  (D4): every exit path tears down; T5 asserts no world + no rb left
  (on movers AND environment).
- Read-only verifier mode (`apply='none'`): scene restored to byte-equal
  pre-sim matrices (F7).

### Op 1 — `settle(objs=None, *, environment=(), frames=45, apply='end', tol_mm=1.0, repair_penetrations='refuse', output=None) → report`

`objs=None` → all eligible mesh objects (B4 filters; `excluded` lists
the rest with reasons). `environment` names objects made PASSIVE.

Pre-flight (per mover): pair audit vs neighbors (pad 150mm).
`repair_penetrations`: `'refuse'` (default) → any penetrating mover
aborts the sim, report names pairs (D5 — displacement must never be a
side effect); `'physics'` → sim may depenetrate (F5); any mover that
started penetrating and ended moved > tol gets verdict
`REPAIRED_BY_PHYSICS` with `start_pen_mm` + `end_state` — RESERVED
for applied repairs (`apply='end'`). When `apply='none'` the sim
result is discarded (scene restored pre-sim, F7): such a mover's
verdict is `REPAIR_SIMULATED` with `applied: false` and
`scene_state: 'pre_sim_restored'` — it answers "would this repair
work?", not "is this scene repaired". `'lift'` → pre-lift mover by
pen + 1mm along +Z (recorded).

Per-mover verdicts (B6-amended):
- `AT_REST` — disp ≤ tol AND rotation ≤ 0.5deg.
- `SETTLED` — moved down, came to rest, rotation ≤ 10deg.
- `SLIPPED` — support unchanged (same named support), lateral disp
  > tol (dropped onto slope, slid — gate B6b).
- `TOPPLED` — rotation > 10deg (report `rotation_delta_deg` + both
  support states; gate nb-5).
- `REPAIRED_BY_PHYSICS` — started pen, moved (only in
  repair='physics' mode; else 'refuse' aborts earlier).
- `ESCAPED` — final AABB exits scene bounds OR still moving at cap
  (B6c: "toppled off the table and landed 1m lower" is a legal
  SETTLED with big displacement, not ESCAPED).
- `PENETRATING_AT_END` — mover was clear pre-sim but the final audit
  finds it penetrating (sim-induced; can never be reported as
  AT_REST/SETTLED).
- `FROZEN` is NOT an outcome: it is a pre-flight status
  (`shape_build_failed` / `never_activated`) reported per object
  (gate B6d). A mover jammed under an overhang with zero motion is
  legitimately AT_REST.
Scene verdict: PASS iff no ESCAPED, no un-repaired penetrating pair in
the final audit, no TOPPLED with `rest_pose_changed`; else FAIL +
fix queue.

### Op 2 — `place(obj, *, drop_mm=30, frames=45, snap=True, apply='end', output=None) → report`

Placement through physics for one object over its current (x,y).
1. Pre-flight: obj vs neighbors (pad 150mm); any PENETRATING → refuse
   (report pairs; suggest settle repair_penetrations='physics' or
   geometric repair).
2. Lift obj by `drop_mm` (30mm default).
3. Settle (obj = sole mover; everything else PASSIVE).
4. `snap=True`: guarded vertical nudge — contact-level gap metric
   (gate R1: min footprint-vertex clearance to the support, NOT
   bbox-bottom): if 0 < gap ≤ `snap_cap_mm` (3.0), translate down to
   exact contact, keep orientation, re-audit. Else report `snap_skipped`
   with the measured gap.
2a. **Lift clamp** (gate round-2 AM5): `lift_mm_used = max(drop_mm,
    max neighbor support-top under the footprint − obj bottom + 5mm)`
    via `support_heights` over pre-flight neighbors, reported.
    Without it, resting TOUCHING beside a lip taller than 30mm makes
    the default drop land ON the lip — a false NO_SUPPORT that leaves
    the scene worse than found.
5. Final audit vs the FULL pre-flight neighbor set (same pad): any
   PENETRATING pair → `PLACED_OVERLAP` with the pair named (not only
   the support); non-support neighbors at TOUCHING are reported as
   `incidental_contacts` and do not fail.

Verdicts (gate B7 — no BLOCKED here; that's oracle's):
`PLACED` (TOUCHING on a support), `PLACED_OVERLAP` (penetrating at
rest — pair attached), `NO_SUPPORT` (came to rest on an unintended
surface — name it + clearance to intended), `ESCAPED`.

### Op 3 — `oracle(obj, *, target_z=None, frames=45, pad_mm=150, tol_mm=1.0, output=None) → report`

The jeep-door witness. Agent moves obj to the requested pose (or pass
`target_z`: executed as
`move_to(obj, (x, y, target_z), reference='bottom-center')` — pure
translation, orientation never altered; the op already exists in
placement_lib). `requested_z` and `settled_z` are both the object's
world bbox **bottom**. Op gains optional `intended_support`; when
omitted it is inferred as the pre-sim `support_heights` hit under
(x,y); the B6b blocker-exclusion rule uses it — without this the
intended floor gets ranked as a blocker. Settle (obj = sole
mover). Classification (gate B6a):
- `BLOCKED` iff settled_z > requested_z (tol): resting on something
  below the request — `blocked_by` = contact-ranked neighbors at
  settled pose (contact first, then min clearance; NEVER the support
  it was intended for — exclusion rule B6b); `contacts_lateral`
  always emitted (walls/niches surface regardless of classification).
- `FELL_BELOW` iff settled_z ≤ requested_z − tol: was floating, or
  slid off — support named.
- `REACHED` — disp ≤ tol and z within tol of request.
- `SLIPPED` — landed on the INTENDED support but lateral disp > tol
  (slope slide).
- `PRESERVED_OVERLAP` is impossible (pre-flight refuses) — the
  pre-flight report carries it instead.
Report includes `disp_xy_mm`, `disp_z_mm`, `rotation_delta_deg` (R2)
so agents can reclassify edge cases.

### Op 4 — `gate(*, tol_mm=1.0, frames=45, apply='none', fail_hard=False, repair_penetrations='refuse', output=None) → report`

Scene-level REJECTION gate; pure verifier by default (apply='none'):
1. Static audit: `audit_scene` (pad 100mm) → penetrating pairs.
2. Settle-verify (apply='none'): if step 1 found penetrating pairs,
   those objects are removed from the settle-verify mover set (already
   REJECTED; their fix items run first). Settle-verify runs on the
   pen-free subset with `repair_penetrations` forced to `'refuse'`
   (passing 'physics'/'lift' to gate raises ValueError — a verifier
   never repairs). Sim-induced NEW penetrating pairs between
   formerly-clear movers during verify are instability findings →
   REJECTED, fix item `physics_settle` on that pair.
3. Verdict `PASS` | `REJECTED` + fix queue of **executable patch
   fragments** (gate nb-1):
   `[{"op": "place_on", "obj": "Mug", "supports": ["Desk"]},
     {"op": "physics_settle", "objs": ["Book3"],
      "repair_penetrations": "physics"}, ...]`
   — each item is directly runnable through apply_patch.
4. `fail_hard=True` → non-zero exit (shell pipelines reject).

## Design decisions (all gate-amended)

- **D2 shape policy**: movers `auto` = CONVEX_HULL if verts ≤ 5000
  else BOX; environment = BOX if bbox-fill > 0.9 else CONVEX_HULL;
  never MESH (concave receivers = agent-modeled compounds, documented).
  Scale/data/modifier/multi-user guards per `_prep` above (B4).
- **D3 process model (rewritten, gate nb-6)**: physics ops run
  one-shot per Blender process (kit patch-op model) — the clean case;
  a process MAY chain multiple physics ops, each F8-disciplined
  (frame_set(1) before every sim); T5f covers sim→sim→geometric chain.
- **D4 teardown unconditional** (unchanged; F14 deselect-all inside).
- **D5 pre-flight refuse default** (re-justified: depenetration
  displaces movers by an uncontrolled amount/direction in general
  geometry — flat contacts go up, wedged contacts can jet laterally;
  default refuses, explicit modes record the repair).
- **D6 blocker ranking by contact evidence** (unchanged + B6b
  exclusion: never rank the intended support as blocker).
- **D7 guarded snap** (unchanged + R1 contact-level gap metric).
- **D8 early exit** (unchanged + creep check + fps-derived frame
  budget: `frames` derived from `sim_seconds` target × scene fps,
  reported — gate nb-3). `_sim` bodies: restitution=0.0, friction=0.6,
  high damping (spike values); early-exit soundness ASSUMES
  restitution=0. If a pre-existing world has
  `point_cache.frame_end < frames`, EXTEND it and record
  `frame_end_extended` (F13 hard-assert only for worlds we cannot
  extend).
- **D9 integration surface (amended, gate nb-7)**: `physics_settle`,
  `physics_place`, `physics_oracle`, `physics_gate` registered as
  `(fn, False)` scene-level ops in apply_patch MUTATIONS (obj arrives
  via params; document that `id` is unused for them). AGENTS.md: new
  "physics as oracle/gate" decision-tree section + gotchas #58-#62
  (#58 transform_apply, #59 cache discipline, #60 scale snapshot,
  #61 teardown, #62 non-mesh selection aborts rb ops).
- **D10 tests (T5 series, amended)**:
  - a: float→settle exact (SETTLED, TOUCHING 0.0) **+ orientation
    unchanged assert** (T2 lesson).
  - b: penetration + settle repair='physics' apply='end' →
    REPAIRED_BY_PHYSICS, end TOUCHING 0.0, displacement = start_pen;
    repair='physics' apply='none' → REPAIR_SIMULATED, scene restored;
    repair='refuse' → abort with pairs.
  - c: 3-book stack → no pen, all AT_REST/SETTLED; orientation
    asserted.
  - d: oracle block (mug + lip) → BLOCKED, blocked_by names lip,
    contacts_lateral sane.
  - e: mixed 25-object scene + planted float + planted pen + planted
    toppler → gate REJECTED with exactly those fix items (executable
    fragments validate against apply_patch), PASS after repairs;
    non-mesh objects present in scene (light/empty) must not abort
    (R4/F14); fail_hard exit code asserted.
  - f: determinism + teardown: sim→sim→geometric chain; identical
    matrices; post: no world, no rb, RNA == report.
  - g (B3): keyframed mover → refused, channels named.
- **D11 UX contracts**: unchanged (JSON-first; fix queue executable;
  vision flow = seam_views/heat_bake to *choose* pairs, numbers
  decide mm).

## Out of scope (v1)

Dynamics-for-animation, soft body/cloth/fluids, auto-compound
decomposition, friction/mass realism (settle uses high damping; the
report flags non-dissipated motion instead of simulating realism).

## Implementation notes (gate round-2, must not forget)

- `allow_copy` must do `obj.copy()` AND `obj.data.copy()` — `obj.copy()`
  alone shares mesh data, still multi-user (apply_patch
  `duplicate_object` is the pattern).
- `view_layer.update()` before every `rb_add`; deselect-all + set
  active before every rb op, including inside `_prep` probes and
  teardown (F10/F14 pattern from probe_f5_reverdict.py).
- Never read `obj.location` for verdicts — RNA stays at spawn post-sim
  (F7); use captured `matrix_world`.
- `audit_scene` silently skips names starting "Cam"/"Temp" —
  `objs=None` mover discovery defines its own filter and documents it.
- T5a-g in one process: feasible (probe_f5 ran 3 factory resets + rb
  ops); T5f must NOT factory-reset between chained sims (that IS the
  D3 test); T5e validates fix fragments by calling
  `apply_patch.apply_mutation` directly; assert no `rigid_body` on env
  objects post-teardown.
- Report always includes: `start_pen_mm`, `disp_xy_mm`,
  `rotation_delta_deg`, `lift_mm_used`, `frame_end_extended`,
  `sim_frames_used`, `excluded`.

## Residual risks (post-gate)

- R2 residual: TOPPLED threshold 10deg is a heuristic; disp_xy_mm +
  rotation_delta_deg are always reported for reclassification.
- Wedged-contact depenetration direction is not controlled (jetting);
  mitigated by refuse-default + escape caps + explicit repair modes.
- `settle(objs=None)` on huge scenes: report-only default (gate),
  explicit movers for mutations; `excluded` keeps root-collapse
  semantics visible.
