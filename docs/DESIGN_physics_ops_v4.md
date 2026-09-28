# DESIGN — physics-assisted placement ops (session-13 rebuild, v4.1)

> Status: fact base re-derived (22/22 PASS, `scripts/probe_physics_facts.py`,
> `output/probes/physics_facts.json`). Review gate 1 returned AMEND with
> 11 amendments (all applied; probe-verified where marked). Implementation
> contract for `scripts/physics_place.py`. Gate 2 verifies this doc.

## Mission (the user's seeding ideas, operantionalized)

1. "Turn on physics so nothing CAN overlap — we simply reject."
   → `physics_gate`: scene-level gate; PASS is trustworthy.
2. "Placing goes THROUGH physics: put it too high and gravity takes over."
   → `physics_settle` / `physics_place`: gravity is the placement solver.
3. "When I try to go to X and it stops at X−5, I check and it tells me
   whether the jeep door or the stairs blocked it."
   → `physics_oracle`: the blocker is NAMED in the report.

## Design decisions (each with rationale; reviewer attacks these)

### D1 — Bullet (Blender rigid body) is a SOLVER, not a validator
placement_lib stays the measurement authority (mm-exact pair_contact /
audit_scene). Physics proposes poses (settle/depenetrate); placement_lib
disposes (audit verdicts). No physics-derived "trust" without an audit
pair behind it. Rationale: the two systems have different failure modes
(bullet: tunneling, margin gaps, solver drift, collision-shape
approximation; lib: sampling, tangency); cross-validation is the whole
point. Post-commit audit correctness does not depend on manual
`clear_bvh_cache()`: placement_lib's BVH cache key includes the
world-matrix hash + frame_current + filepath, so a committed pose
self-invalidates; ops still call `clear_bvh_cache()` after
`open_mainfile` (apply_patch already does) and after any data-level
mesh edit. No invalidation is needed between sim and commit-audit.

### D2 — One op = one process; EVERY sim entry disciplines the cache
The point cache persists across object teardown within a world (P4:
naive second sim leaves the body frozen mid-air at its spawn z) AND
across the .blend round-trip (gate-1 probe: a saved file reopens with
frame_current=60 and point_cache.frame_end=60; a new active body
stepped without discipline freezes at spawn — the P4 signature;
disciplined it rests exactly). Therefore EVERY sim entry runs:
`point_cache.frame_end = frames` + `frame_set(1)` before stepping —
including the FIRST sim of an op that adopted a rigidbody_world from
a loaded .blend. Multi-phase sims re-apply the same discipline before
each re-step. `bpy.ops.rigidbody.world_add()` RAISES RuntimeError when
a world already exists — ops must ADOPT `scene.rigidbody_world` when
present, create via `world_add()` only when absent. An op asked to
re-step without discipline is a coding error: `_sim_step` asserts the
invariant (resets unconditionally — the discipline IS the reset).

### D3 — The commit pattern (F2) + op-exit frame hygiene
The sim pose lives ONLY in `matrix_world` during the sim; RNA location
stays at spawn. Every RNA reader (placement_lib BVH, audit, saved
.blend) sees the spawn pose until commit. Commit = capture
`matrix_world` → `rb.enabled = False` (4.5: `obj.rigid_body` and
`scene.rigidbody_world` are READ-ONLY; there is no data-level
removal) → write the matrix back into RNA. P9 proves the committed
pose survives save + reload + arbitrary frame_sets, and the inert rb
component in the saved .blend is inert (no active sim state).
Measured bonus (gate-1): inert bodies remain static colliders for
LATER sims (a committed book is terrain the next op can stack on) —
this is the cross-op composition semantic, pinned by test o.
Op exit hygiene: after committing all movers, `scene.frame_set(1)` so
the saved .blend does not reopen parked at the sim's last frame
(save carries frame_current=60, point_cache.frame_end=60 — harmless
for inert bodies, breaks the next undisciplined sim).

### D4 — Environment auto-discovery (exact rule)
`environment` (passive terrain) defaults to: every MESH object except
(a) this op's movers, (b) non-MESH types, (c) objects whose name
starts with `Cam` or `Temp` (the exact `audit_scene` exclusion set —
"kit internals" made implementable), (d) objects with
location/rotation animation channels, or whose parent chain has them
(per `placement_lib._location_anim_channels`) — reported as
`env_skipped_animated`, never silently added (a passive body on an
animated parent is a MOVING collider and voids the P8 determinism
claim). Linked duplicates are fine (one body per object). Far-away
objects (100 km) become cost-free passive bodies — bullet broadphase
and the audit AABB prefilter ignore them; no special case. If the
caller names `environment` explicitly, the default is replaced.
Movers are NEVER part of their own environment (T5h lesson: the mug
was its own floor). Environment bodies are PASSIVE with `enabled` on,
so movers can rest on them. Objects with an existing `rigid_body` are
left alone unless `rebuild_rb: true`.

### D5 — Verdict classification (total, mutually exclusive, direction-aware)
Per mover, evaluated in this order (first match wins — makes the set
total): from start→end pose + post-audit pairs:
- `STUCK` — post-audit pair is PENETRATING (started clear, ended
  jammed, or depenetration failed). Instability + queue item.
- `REPAIRED_BY_PHYSICS` — started PENETRATING (pre-flight audit),
  ended TOUCHING with penetration_mm ≤ band. (P2: bullet ejects flat
  overlaps to exact rest — displacement == penetration depth.)
- `TOPPLED` — up-axis angle > topple_deg (default 5°): angle between
  the start and end of the object's local +Z in world space (yaw drift
  excluded by construction — a 30° yaw with upright +Z is NOT a
  topple). Instability + queue item (fix queue proposes a settle
  re-run with `upright_lock: true`).
- `NO_SUPPORT` — no post-sim pair with state TOUCHING.
  `reason: void` when the end bottom is > 25 mm below the start
  support plane (start support = highest `support_heights` hit under
  the footprint at the spawn pose; when the spawn had no support —
  the normal drop-in case — `void` when the end bottom is
  >`capture_zone_mm` (param, default 250) below the spawn bottom),
  else `reason: no_contact` (frozen mid-air — the stale-cache
  signature). Instability + queue item.
- `SLIPPED` — lateral displacement > slip_mm (default 5 mm) but
  landed TOUCHING and upright. Info for settle/place; physics_gate
  promotes SLIPPED to a fix-queue item and withholds PASS (D9). This
  is the single rule; D9's list is the gate's view of it.
- `SETTLED` — ended TOUCHING on a support, lateral displacement ≤
  slip_mm, upright. Success.
Rotation/translation noise floors: sub-0.1° upright jitter and
sub-0.1 mm translations are absorbed (P6: pops are sub-noise at
margin=1 mm; 0.1 mm = the lib's contact band).

### D6 — Collision shape policy
`BOX` only for near-box meshes that are ALSO origin-centered: all
|scale| within 2×, bbox aspect < 2, AND object origin within 5 mm of
the bbox center. Otherwise `CONVEX_HULL`. Never `MESH` (slow,
brittle). Why the origin guard (gate-1 probe): bullet's BOX shape is
centered on the object ORIGIN, not the bbox — a slab spanning z
0..0.3 with origin at z=0 gets a collision box spanning z −0.15..+0.15
(a dropped ball rests at z=0.19 instead of 0.34 — a 150 mm
collision/visual mismatch → post-audit PENETRATING); CONVEX_HULL
rests exactly on the visual top. HULL is always safe; BOX only on
origin-centered geometry. Both allowed shapes fill concavities: a
U-cradle phantom-rests a dropped ball on the wall tops — phantom
rests have no TOUCHING pair, so D5 reports NO_SUPPORT (loud, not
silent). Acceptable for previz; documented. Margin = 1 mm default
(P3/P6: exact rest, no pop, even on stacks; ratio insensitivity
measured to 2:1 margin:body). Object scale is honored by bullet (P5:
no data bake needed — user geometry is never mutated).
`mass = max(0.1, volume_estimate_kg)` with volume from the bbox ×
fill 0.5 — only relative masses matter for settling.

### D7 — The guarded snap
Bullet rests can carry a sub-mm-to-mm gap vs the TRUE surface (margin
geometry). After commit, measure the support plane under the mover's
footprint (`support_heights`, placement_lib) and, if the bottom sits
within `snap_cap_mm` (default 8.0) ABOVE the support plane, translate
down onto the plane exactly (place semantics: bottom = plane +
clearance 0). Support set = the objects the mover landed ON: pair
TOUCHING AND support surface below the mover's bottom + guard
(from_z starts just below the mover's own bottom). Movers ARE
eligible supports — a book on a book must snap against the book below
it (gate-1 probe: guarded `support_heights([book_below], pts,
from_z=bottom+5mm)` returns the below-book top exactly; test j's
from_z guard excludes the book ABOVE geometrically, not by mover
exclusion). Multi-level support (per-grid-point spread > 5 mm, e.g.
half on book / half on desk): snap is SKIPPED, report
`snap: "skipped_multi_level"` + spread — never pick a plane (snapping
to the max buries the low half; to the min, the top half floats);
keep the bullet pose (sub-margin gap is previz-acceptable). The snap
NEVER pulls a mover down more than the measured gap (no burying), and
only fires for movers whose verdict is SETTLED /
REPAIRED_BY_PHYSICS / SLIPPED. Snap fires once per mover per op; the
post-snap audit is the final word.

### D8 — physics_oracle (the witness)
Params: mover id, `target` (xyz), `lift` (default 80 mm above target —
the drop-in height), `frames`, `environment`, `arrive_xy_mm` (10).
Flow: pre-flight audit (mover × all) — if the pre-flight is failing,
REFUSED with the failing pairs (no sim; pose untouched). Sim: mover
teleported (RNA write BEFORE rb add) to above-target, environment
passive (D4), cache-disciplined settle (D2), commit (D3). Then
classify:
- Arrived (bottom-center within `arrive_xy_mm` of target xy AND
  verdict SETTLED/REPAIRED) → `result: ARRIVED` + post-audit.
- Stopped short (lateral gap > arrive_xy_mm) → `result: BLOCKED` +
  **witness**: `blocked_by` from the mover's audit pairs EXCLUDING
  its final support set (its up-facing bottom contact is the floor it
  RESTS on — without this exclusion a mover deflected sideways names
  the floor as primary obstruction). Sort key: PENETRATING
  (penetration desc) > TOUCHING > CLEAR (clearance asc); first entry
  = primary obstruction; this makes two-blocker scenes (wall AND
  floor) deterministic. If no qualifying pair remains (slipped away,
  rests clear), `blocked_by: []` plus `nearest_object` /
  `nearest_gap_mm` from the pad pairs.
- Any other verdict (TOPPLED / NO_SUPPORT / STUCK) is returned as
  `result: <verdict>` — never folded into BLOCKED.
- REFUSED paths restore the mover's original RNA pose (no pose leak:
  every early-return after a pose write unwinds the write).

### D9 — physics_gate (the reject)
Flow: (1) pre-flight audit_scene (all pairs, clearance pad 100 mm) —
any PENETRATING/NESTED with severity fail/info becomes a queue item
(no sim yet — NESTED mug-in-desk must refuse BEFORE the violent
ejection). (2) If pre-flight clean: settle the bodies selected by
`lanes`: `grounded` (default) = every non-environment MESH body with
≥1 pre-flight audit pair within the clearance pad (engaged with the
scene); `all` = every non-environment MESH body. Intentional
non-grounded objects are protected: a chandelier hanging in the air
has no pairs within the pad, is never settled, and can PASS. Bodies
with location animation are skipped (`skipped_animated`), not
settled; every other non-settled body is added as PASSIVE so it
still collides. (2b) Pose policy: on PASS, gate commits every body
it settled (D3 pattern); on REJECTED it reverts every sim-moved body
to its pre-flight RNA pose (D8's no-pose-leak rule — the fix_queue
must address the scene the user actually has). (3) Post audit +
per-mover verdicts. (4) `verdict = PASS` iff zero instability AND
post-audit has no PENETRATING (severity fail) AND no
SLIPPED/TOPPLED/NO_SUPPORT/STUCK among movers. Any failure →
`verdict: REJECTED` + executable `fix_queue`: each item is an
apply_patch mutation (move_to / place_on with computed targets, or
`physics_settle` retry with upright_lock) that a consumer can apply
verbatim. A PASS with a non-empty queue is impossible by
construction (queue items only append on failure paths).

### D10 — Determinism & performance contracts
P8: same inputs → identical trajectory (same build/process). Ops are
therefore reproducible: same patch → same result. Perf contract:
`physics_settle` on 10 movers + 10 env bodies, 60 frames, ≤ 5 s
wall (gate-1 measured 0.02 s total — large headroom; the lib audit
dominates). Frame budget default 60 @ 24 fps = 2.5 s sim time;
`substeps_per_frame` 10, solver_iterations 10 (bullet defaults;
measured stable on stacks).

### D11 — apply_patch surface (JSON)
```
{"op":"physics_settle","movers":["A","B"],"environment":null,
 "frames":60,"upright_lock":false,"snap":true,"rebuild_rb":false,
 "slip_mm":5.0,"topple_deg":5.0,"snap_cap_mm":8.0,
 "capture_zone_mm":250.0,"output":"report.json"}
{"op":"physics_place","id":"Mug","target":[x,y,z],"lift":0.08,
 "environment":null,"frames":60,"upright_lock":false,"snap":true,
 "rebuild_rb":false,"slip_mm":5.0,"topple_deg":5.0,
 "snap_cap_mm":8.0,"capture_zone_mm":250.0,"output":"report.json"}
{"op":"physics_oracle","id":"Mug","target":[x,y,z],"lift":0.08,
 "environment":null,"frames":60,"arrive_xy_mm":10.0,
 "rebuild_rb":false,"output":"report.json"}
{"op":"physics_gate","lanes":"grounded","settle":true,
 "rebuild_rb":false,"slip_mm":5.0,"topple_deg":5.0,
 "snap_cap_mm":8.0,"output":"gate.json"}
```
All ops print a one-line verdict (the primary non-visual UX) and
`--save-blend` commits everything. `physics_place` = oracle + settle
semantics combined (place where asked, gravity decides final rest,
audit decides truth). Registration: settle/gate need no single `id`
→ `needs_obj=False` like `audit`; place/oracle use `id` →
`needs_obj=True`. Params not listed are fixed at the D5/D6/D7
defaults for v4.

### D12 — Non-vision-first UX (session-13 mandate)
Every op prints: op name, per-mover `verdict (key numbers)`, post
audit counts, and the fix queue as literal patch JSON lines (copy-
paste executable). The JSON report is the contract; the print is the
UX. No interpretation requires renders. (Native-vision study remains
advisory: heat/seam encodings discriminate defects for VLM/me, plain
renders do not — kit doctrine unchanged.)

## Test plan (T5, tests/test_t5_physics.py)
- a: settle single box 1 m above floor → SETTLED, TOUCHING 0.0, snap
  no-op; scene schema post-state correct.
- b: depenetration — box 50 mm into floor → REPAIRED_BY_PHYSICS,
  TOUCHING 0.0 (P2).
- c: two-mover stack settles → both SETTLED, pair TOUCHING (cross-
  mover, D4).
- d: oracle BLOCKED — mover dropped toward a target inside a walled
  pen → BLOCKED, blocked_by[0] == wall name AND floor NOT in
  blocked_by (witness support-exclusion), stopped_at sane.
- e: oracle ARRIVED — clear target → ARRIVED, post-audit clean.
- f: gate REJECTED — pre-planted 12 mm penetration + 55 mm float →
  queue non-empty, verdict REJECTED, PASS impossible.
- g: gate PASS — clean scene → PASS, queue empty.
- h: auto-env — mover alone on a desk (desk never named as
  environment) still settles ON the desk (D4); mug not its own floor.
- i: NESTED refusal — mug fully inside desk geometry → gate refuses
  pre-sim with a queue item (D9).
- j: overhang stack — 3-book stack exact after snap (D7); book1 not
  snapped against the book ABOVE it (from_z guard).
- k: upright_lock + yaw — toppled box verdict TOPPLED; yaw-only drift
  (30° yaw, up-axis preserved) stays SETTLED (D5 rotation semantics).
- l: oracle REFUSED restores pose — pre-flight-failing oracle leaves
  the mover exactly where it was (D8 no pose leak).
- m: SLIPPED single-mover settle = info/PASS; same scene through
  physics_gate = REJECTED with queue item (D5/D9 resolution).
- n: NO_SUPPORT void fall (`reason: void`); op asked to run two sims
  without discipline hits the `_sim_step` unconditional reset (D2).
- o: cross-op terrain — settle BookA in op 1; op 2 settles BookB
  above → B rests ON A at A-top (committed bodies are static
  terrain, D3).
- p: off-origin mesh mover → hull fallback, exact rest + TOUCHING
  (D6 origin guard).
- q: chandelier gate — float with no pad pairs → untouched, PASS;
  gate REJECTED leaves every pre-flight pose bit-identical (D9 both
  halves).
- r: half-on-book/half-on-desk → `skipped_multi_level`, no burying
  (D7 multi-level).

## Explicit non-goals (this iteration)
- No animated/NLA interaction (rb sim replaces keyframes while active;
  ops refuse on animated movers unless override="ignore" — the lib's
  _guard_anim is reused).
- No rotation placement (tilting objects to match slopes) — physics
  settles naturally; align_to_surface remains the analytic path.
- No soft bodies, no constraints, no baking to keyframes (a
  `bake: true` flag may come later — NOT in this round).
