# CROWD-DESIGN-AUDIT-1 — Adversarial Design Audit

Source under audit: `/home/sync/blender-agent-kit/docs/crowd_system/DESIGN_crowd_system_v1.md` (v1 draft, 1024 LOC).
Auditor: fresh-context senior crowd-sim engineer + Blender Python expert.
Benchmark: bgyss `docs/blender-crowd-1.0.md` (1,166 LOC, M0-M6 accepted).
Hard constraints: 4GB RAM, no GPU, Blender 4.5.13 / 5.2 LTS via shim, Python-first.

---

## 1. Executive verdict

- **Not ready for M0.** Three P0 gaps block implementation: (1) the navmesh algorithm in §6.1 is broken — `mathutils.BVH` is a raycaster, not a voxelizer, and the kit's `placement_lib.py` exposes no poly-adjacency API; (2) the cache→scene attach path is undefined (no `bpy.props` in v1 means no Blender RNA carrier for the cache pointer); (3) writing keyframes to 1K armatures at 53 bones × 240 frames × 7 channels = 89M keyframes blows the 1.5GB RAM budget — R2/GN instancing is a day-1 requirement, not an M2+ optimization.
- **Single biggest risk: the v2 rigged-character failure is silently replaying.** The kit's `kb/rigged_characters.md` documents a 10-session trap on skin weights, action slots, NLA stashes, and basis-matrix collapse. The design drops `add_shape_keys` and adopts clip-driven blend trees without naming the specific mitigations that prevent the v2 failure from recurring. The vendored UAL has **46 actions** (per `assets_ual_actors.py:9`), not the 250+ the research report claims — locomotion-state coverage is uncertain.
- **Must change before M0**: (a) rewrite §6.1 with a real voxelization/walkable-extraction algorithm; (b) ship R2/GN instancing from day 1, defer R0-only to never; (c) pin the UAL rig to the kit's already-vetted vendored copy (`assets/vendor/ual/`) and explicitly forbid new rig imports in v1.
- **Architecture is sound.** The 5-subsystem boundaries mirror bgyss §3 correctly. SoA buffers, 30Hz fixed-tick, behavior-IR-compile, chunked cache — all correct. The risks are in execution detail, not shape.
- **1K-agent gate is achievable** with the tier mix (20% S0 + 80% S1) and the per-tier neighbor/decision-frequency reduction. The 33ms tick budget is realistic for FAST mode; STRICT mode will be ~2× slower and will not hit 1mm cross-CPU tolerance without explicit reduction ordering.
- **Orchestrator's open list is mostly right** but misses 4 critical issues: cache→scene attachment seam, R0-only is infeasible, UAL clip count is wrong, behavior IR has no RUNNING state expression.

---

## 2. Decision verdicts (D1-D10)

| Decision | Verdict | Rationale | Proposed action |
|---|---|---|---|
| **D1** No Rust, 1K-agent gate | CONFIRM | 1K matches bgyss M0; NumPy ORCA + tier-mix is the right CPU-only bet. No native build keeps the kit shippable. | Add a 500-agent intermediate checkpoint in M0 (not a gate — a measurement) to retire risk before committing to 1K. |
| **D2** Blender-native navmesh, no Recast | CHALLENGE | §6.1 algorithm is broken — BVH doesn't voxelize; `placement_lib.py` has no poly-adjacency API (only contact-state helpers, see J1). The "use kit's BVH face-pair helpers for adjacency" claim is false. | Replace §6.1 with: (1) `bmesh` walk collecting polys whose `normal.z > 0.707` (walkable) and not under `Blocked` geometry within `agent_height`; (2) build adjacency from `bm.edges` with exactly 2 `link_faces` (already in bmesh, no new code); (3) convex decomposition via Hertel-Mehlhorn on the triangle mesh. Recast binding remains a M4+ option. |
| **D3** NumPy ORCA, no RVO2 Cython | CONFIRM | RVO2 reference impl: ~3ms for 1K×12 neighbors in C++; NumPy overhead 10× → ~30ms. With tier mix (200 S0 × 10 neighbors + 200 S1 × 6 neighbors every 4th tick = 3200 effective pairs vs 10000 baseline), 10-15ms is realistic. | M0 benchmark must use the actual tier mix, not a flat 1K×10. Document SIMD dependence explicitly. |
| **D4** Drop `add_shape_keys`, UAL rig + clips | REFINE | Correct direction but (a) vendored UAL has 46 actions, not the 250+ claimed by CROWD-RESEARCH-EXT-1 §6; (b) the v2 rigged failure (skin weights, NLA stashes, basis-matrix collapse) has no named mitigation. | §8 must (a) list the 46 available UAL actions + flag which locomotion states are missing (likely walk_start, walk_stop, turn_left/right, arc_left/right); (b) forbid new rig imports in v1 — reuse the kit's already-vetted `assets_ual_actors.py` path (42/46 animate, drift 0.000m); (c) retarget profile stays IDENTITY (UAL→UAL) in v1. |
| **D5** 7-node behavior IR | REFINE | Cannot express zombie-escape FSM (LUNGE/REACH/FLEE/FALLBEHIND/GIVEUP/STAGGER) — D7 conflicts with this. Also has no RUNNING-state expression (see E2) and no blackboard-less state mechanism (see E3). | Add 3 nodes in v1: `MarkVisited(region)`, `IsVisited(region)`, `SetMode(mode)` (a single uint8 blackboard slot). Total 10 nodes. Document the zombie-port migration path in §3.4: each zombie state = a separate behavior graph, top-level Selector reads `mode` blackboard. |
| **D6** Cache matches bgyss v1 | REFINE | "Independent schema or borrow verbatim" is undecided. bgyss schemas (27 files in `/tmp/Blender-Crowd/schemas/`) are battle-tested; borrowing names gives cross-compat; file format should be simpler. | Borrow schema field NAMES (cache-manifest-v1, project-ir-v1, layout-layer-v1) for cross-compat. Define own v1 binary chunk layout (simpler than bgyss). Add per-chunk byte offsets in manifest for O(1) seek (currently missing). |
| **D7** Zombie-escape port in M3 | CONFIRM | High value as a generality proof + API-gap finder. But M3 is "1.0 hardening" — the port is a heavy lift (state translation + parity assertions). | Move zombie port to M2 (authorable MVP, where typed behavior graph lands). M3 retains the regression-test gating. Success criterion = functional parity only ("agents reach destinations + 6 audit gates pass"), not behavioral parity with LUNGE/REACH. |
| **D8** Defer Blender panel UI to M4+ | CONFIRM | Python API matches the kit's existing authoring style (`scene_escape.py`, `apply_patch.py`). No `bpy.props` registration is the right call. | Add a v1 stub `crowd/panel.py` that imports cleanly (no-op) so M4 panels drop in without import surgery. |
| **D9** STRICT tolerance 1mm/0.001rad | CHALLENGE | NumPy LP-solver reduction order varies across CPUs (SIMD width, fast-math). 1mm cross-CPU is NOT achievable without explicit ordering. bgyss §9.4 explicitly hedges: "Exact cross-CPU floating-point identity is not promised until demonstrated." | Three options, pick one: (a) STRICT mode disables NumPy fast-math, sorts LP constraints by stable key before reduction, accepts ~2× slowdown — tolerance stays 1mm but only intra-machine; (b) STRICT mode runs pure-Python ORCA fallback (100× slower, infeasible at 1K — reject); (c) drop cross-CPU claim, document STRICT as "same-machine regression only". Recommend (a)+(c). |
| **D10** Foot IK in v1, terrain-follow in M3+ | REFINE | Foot IK at render time requires recomputing clips every render frame (cache stores `clip_id+clip_phase`, not bone matrices). 1K × 240 × 2 feet = 480K raycasts per render pass — feasible but not free. The bigger issue: foot IK without terrain-follow is just "lock foot at clip-extracted contact point" — marginal value over no-IK. | Defer ALL foot IK to M3+ (both foot-planting AND terrain-follow together). v1 ships root-motion + clip phase only — same effective quality as the existing `add_shape_keys` lift-only bob, but data-driven. Simpler v1, cleaner M3 boundary. |

---

## 3. Risk verdicts (R1-R8)

| Risk | Verdict | Additional mitigation? |
|---|---|---|
| **R1** NumPy ORCA > 33ms | CONFIRM + refine | Tier mix must be measured, not assumed. M0 benchmark MUST use 20% S0 + 80% S1, not flat 1K×10. Add: FAST-mode tolerance = 5mm; STRICT-mode = 1mm but ~2× slower (not 33ms — ~60ms). |
| **R2** Blender navmesh low quality | CHALLENGE | The mitigation in the design doesn't address the real risk: the algorithm itself is broken (BVH ≠ voxelizer). Replace §6.1 first, then benchmark. |
| **R3** UAL clip gaps | CONFIRM + escalate | Vendored UAL = 46 actions (not 250+). Missing clips likely include walk_start, walk_stop, turn_left/right. v1 must either (a) source missing clips, (b) design locomotion set around what exists, or (c) accept a degraded state machine (idle/walk_loop/jog only, no start/stop transitions). |
| **R4** 7-node IR too restrictive | CONFIRM + fix | Add 3 nodes (MarkVisited, IsVisited, SetMode) per D5. Document zombie-port migration path. |
| **R5** Cache format breaking changes | CONFIRM | `schema_version` field from day 1 (already in design). Add: golden migration tests in M3. |
| **R6** 4GB RAM for 1K×240 | CONFIRM + escalate | The 1.5GB sim budget is achievable. The REAL risk is the SCENE side: 1K armature objects with R0-only rendering blows the budget (89M keyframes). R2/GN instancing is a day-1 requirement, not M2+. See C3. |
| **R7** Foot IK raycasts expensive | CONFIRM | Design already says "render-time only". Defer ALL foot IK to M3+ per D10. |
| **R8** Determinism across CPUs | CHALLENGE | Pure-Python ORCA fallback (the design's stated mitigation) is 100× slower — infeasible at 1K. The real fix is explicit reduction ordering in NumPy ORCA + dropping the cross-CPU bitwise claim. See D9. |

---

## 4. Beyond-orchestrator findings (A-J)

### A. Architectural soundness

| Finding | Sev | Proposed fix |
|---|---|---|
| A1: Behavior IR runtime is per-agent Python dispatch (`instruction_ptr[agent]`, `node_id`). Breaks the "SoA vectorized end-to-end" story. The hot loop touches Python for every agent whose decision interval is due. | P1 | Acceptable IF tier mix is honored: 200 S0 + 200 S1 (every 4th tick) = 250 agents/tick → 25% of full dispatch. Add to §5.1: "Behavior IR runs as sparse per-agent dispatch only on agents whose decision interval is due; the 1K-agent gate depends on the tier mix." |
| A2: 30Hz sim / 24fps render = 1.25 ticks/frame. Cache interpolates linearly between ticks. Fine for continuous channels (position, orientation), but `clip_phase` normalized 0..1 wraps at loop boundaries — linear interp across a wrap produces nonsense (e.g. phase 0.99 → 0.01 lerp = 0.5 mid-loop). | P1 | Store `clip_phase` as continuous monotonic time (seconds since clip start, modulo loop_duration), not normalized 0..1. Render-time interpolation = `phase_at_render = (sim_phase + (frame - tick_frame) * dt * playback_rate) % loop_duration`. |
| A3: 5-second chunk boundaries. 7200 ticks / 150 ticks-per-chunk = 48 chunks. Random access at frame 847 → chunk index `floor(847 * 1.25 / 150)` = 7. Seek latency = 1 file read of ~5MB = ~5ms. | P3 | Manifest must include per-chunk byte offsets + tick ranges for O(1) seek. Currently not specified. |

### B. Algorithm feasibility on 4GB / no GPU

| Finding | Sev | Proposed fix |
|---|---|---|
| B1: NumPy ORCA at 30Hz for 1K×10. Math: RVO2 C++ = 3ms → NumPy 10× = 30ms. With tier mix (3200 effective pairs vs 10000 baseline), 10-15ms realistic. | P2 | CONFIRM design's 5-15ms estimate is correct IF tier mix is honored. M0 benchmark must use the mix. |
| B2: Navmesh voxelization gap. §6.1 says "Voxelize at agent_radius*2 using mathutils.BVH" — BVH is a raycaster, not a voxelizer. | P0 | Replace §6.1 with bmesh walk (see D2 proposed action). The actual algorithm: (1) collect polys whose `normal.z > 0.707`; (2) reject polys under `Blocked` geometry within `agent_height` (use BVH raycast `find_ray` for this — that's what BVH is for); (3) build adjacency from `bm.edges` with `len(link_faces)==2`; (4) convex decomposition via Hertel-Mehlhorn on triangle mesh. |
| B3: A* + funnel in pure Python at 1K agents. Design amortizes to N=50 replans/tick. With ~1000 polys and ~20-poly avg path, A* expands ~200 nodes/search → 10K nodes/tick × 1µs/node = 10ms/tick. | P2 | CONFIRM feasible. Add path cache keyed by `(start_poly, goal_poly)`; invalidate per-population on navmesh rebuild (not global). Expected hit rate >80% in concourse scenes (shared goals). |

### C. Blender API surface

| Finding | Sev | Proposed fix |
|---|---|---|
| C1: Cache attachment seam undefined. "No `bpy.props` in v1" — so how does the cache attach to the scene? Custom property? Separate .crowd file? Data-block? | P1 | Single `scene["crowd_cache_path"]` custom property (string path to `shot.crowd/`). Bake.apply_to_scene() reads this + manifest.json. No `bpy.props` registration needed — `scene[key] = value` works on any Blender property without registration. Document in §11. |
| C2: 1K agents × 240 frames × 9 keyframe channels = 2.16M keyframes. Memory ~138MB for fcurves alone. Acceptable. BUT the kit's `iter_fcurves()` shim handles READING (4.x `action.fcurves` ↔ 5.x `action.layers[0].strips[0].channelbag(slot).fcurves`). Writing fcurves is a separate path. | P0 | Design must specify a `keyframe_insert_compat(obj, data_path, frame, value)` helper that uses `action.fcurves.new()` on 4.x and the slot/channelbag API on 5.x. Add to §11.1 public API. The kit's existing `assets_ual_actors.py` already navigates the action-slot law (`ad.action_slot = act.slots[0]`) — reference that pattern. |
| C3: R0-only in v1 means EVERY agent is full-fidelity armature. 1K × 53 bones × 240 frames × 7 channels = 89M keyframes. At ~64 bytes/keyframe that's 5.7GB — exceeds 4GB container. | P0 | R2/GN instancing is a day-1 REQUIREMENT. v1 cache drives a single GN instance group with `crowd_*` named attributes (bgyss §11.3 contract). R0-only is feasible only for ≤100 hero agents. Move R2 from "M2+" to "v1 day-1". |

### D. Animation approach

| Finding | Sev | Proposed fix |
|---|---|---|
| D1: v2 rigged-character failure (skin weights, NLA stashes, basis-matrix collapse — per `kb/rigged_characters.md`) has no named mitigation in the new design. Same risks recur for clip-driven blend trees. | P1 | §8 must explicitly forbid new rig imports in v1. Reuse `assets_ual_actors.py`'s vetted path (42/46 actions animate, drift 0.000m). Retarget profile stays IDENTITY. Action-slot law (`ad.action_slot = act.slots[0]`) enforced via a `keyframe_insert_compat()` helper. |
| D2: UAL has 46 actions in the kit (per `assets_ual_actors.py:9`), not the 250+ claimed by CROWD-RESEARCH-EXT-1 §6 (which cites upstream v1+v2 = 250+). Locomotion state coverage is uncertain. | P1 | §8.1 must enumerate the 46 available UAL actions and flag missing locomotion states. Likely missing: walk_start, walk_stop, turn_left, turn_right, arc_left, arc_right. v1 either sources these or accepts a degraded state machine (idle/walk_loop/jog only). |
| D3: Foot IK at render time. Cache stores `clip_id+clip_phase`, not bone matrices. Foot IK recomputes clip + raycasts every render frame: 1K × 240 × 2 = 480K raycasts per render pass. | P2 | Defer ALL foot IK (planting + terrain) to M3+ per D10. v1 ships root-motion + clip phase only. |

### E. Behavior IR

| Finding | Sev | Proposed fix |
|---|---|---|
| E1: 7-node IR can't express zombie FSM (LUNGE/REACH/FLEE/FALLBEHIND/GIVEUP/STAGGER). Conflicts with D7 (zombie port in M3). | P2 | Migration path: each zombie state = a separate behavior graph; top-level Selector reads a `mode` blackboard slot to pick which sub-graph to run. Requires `SetMode` node + the M2 blackboard. Document in §3.4. |
| E2: RUNNING states. A NAVIGATE action takes 30 ticks to complete. The IR has no "in-progress" expression — every fetch re-evaluates. `poll_interval` defers the next fetch but doesn't preserve in-progress state. | P1 | The `action_state: uint8` buffer (already in §4.2) holds running state. NAVIGATE checks `path_status`; if FOLLOWING, returns RUNNING without recomputing path. WAIT tracks remaining duration in `action_state`. Add to §7.2: "Action nodes are idempotent on re-fetch — RUNNING state is preserved in `action_state`." |
| E3: Blackboard deferred to M2, but many v1 behaviors need state ("have I visited this interest point?"). No expression without blackboard. | P1 | v1 ships a minimal blackboard: per-agent `visited_set` (columnar uint32 array) + `mode` (uint8). Two extra IR ops: `IsVisited(region_id)`, `MarkVisited(region_id)`. 4 extra ops total. The full typed blackboard defers to M2. |

### F. Cache format

| Finding | Sev | Proposed fix |
|---|---|---|
| F1: 50MB cache for 1K×240×8 channels. Raw = 1K × 7200 ticks × 8 ch × 4B = 230MB. zstd-3 on quantized (1mm pos, 0.001 rad) ≈ 4-6× compression → ~50MB. CONFIRMED generous. | P3 | Informational. Tighten budget to 30MB; document that debug channels (desired_velocity, decision_code) are NOT in final caches. |
| F2: Chunked format (5s = 150 ticks). Random access at frame 847 → chunk 7. No manifest-level index specified. | P2 | Manifest must include per-chunk byte offset + tick range for O(1) seek. Currently missing from §9.1. |
| F3: Invalidation "Behavior graph change → sim invalidated" — but what if ONE population's graph changes? Global invalidation wastes work. | P1 | §9.3 must specify per-population invalidation scope. Cache tracks per-population agent ranges; only the affected population's range is re-simulated. |

### G. Determinism

| Finding | Sev | Proposed fix |
|---|---|---|
| G1: NumPy LP-solver reduction order varies across CPUs. 1mm cross-CPU is NOT achievable without explicit ordering. | P1 | See D9 proposed action. STRICT mode: disable fast-math, sort LP constraints by stable key, document ~2× slowdown, drop cross-CPU bitwise claim. |
| G2: Stable agent IDs derive from `(project_seed, population_id, spawn_source_id, spawn_ordinal)`. If archetypes list is reshuffled, does `spawn_ordinal` shift? | P2 | spawn_ordinal is per-spawn-source, sampled independently from archetypes (archetype choice is a weighted draw from a separate RNG stream keyed by `(agent_id, "archetype")`). Reshuffling archetypes changes which archetype each ordinal gets but NOT the ordinal itself. Document this in §4.1. |
| G3: Event ordering `(tick, type, emitter_id)`. Simultaneous events from same emitter — no tiebreaker. | P2 | Add `sequence_number` as 4th sort key (per-emitter monotonic counter). Two extra bytes per event. |

### H. Test pyramid

| Finding | Sev | Proposed fix |
|---|---|---|
| H1: Missing gate "no agent crosses a Blocked region". | P1 | Add `crowd_audit_no_blocked_crossing` — sample agent positions at N frames, raycast to nearest `Blocked` geometry, fail if penetration > 1mm. |
| H2: Missing gate "path corridor doesn't pass through walls". | P1 | Add `crowd_audit_corridor_validity` — for each agent, sample corridor polys; fail if any poly is not in navmesh. |
| H3: Zombie-port success criterion undefined. | P2 | Functional parity only: "agents reach destinations + 6 audit gates pass". Behavioral parity (LUNGE/REACH/etc.) requires M2 blackboard — defer to M3+. |
| H4: Smoke test should test recast/detour binding if added later. | P3 | Add a `test_optional_recast.py` smoke test stubbed in v1 (skips if import fails). |

### I. Scope and phasing

| Finding | Sev | Proposed fix |
|---|---|---|
| I1: Phase 0 (M0) "1-2 sessions" for "1K-disc ORCA benchmark". 1-2 sessions = ~4 hours. Deliverable unclear. | P2 | Specify deliverable: `benchmarks/orca_numpy_bench.py` + `NUMPY_ORCA_BENCH.md` report (wall-time/tick, peak RAM, tier-mix breakdown, SIMD dependence notes). |
| I2: Phase 1 (M1) "Fixed 3-node commuter graph" — but §3.4 lists 7 nodes for v1. Phase 1 = subset? | P2 | §13 must explicitly state "Phase 1 ships 3 of the 7 v1 nodes (Selector, Sequence, Navigate); Phase 2 completes the set." Currently ambiguous. |
| I3: Phase 3 (M3) zombie port — D7 confirms valuable, M3 required. | P2 | See H3 — narrow the success criterion. |

### J. Hidden assumptions

| Finding | Sev | Proposed fix |
|---|---|---|
| J1: `placement_lib.py` BVH face-pair helpers for navmesh adjacency — FALSE. `placement_lib.py` exposes `pair_contact`, `audit_scene`, `_polys_world` (private), `world_bvh` — all contact-state, no poly-adjacency API. | P0 | §6.1 must use bmesh's native `bm.edges` with `len(link_faces)==2` for adjacency (already in bmesh, no kit dependency). Don't claim `placement_lib` provides this. |
| J2: `physics_place.py` for ragdoll handoff — PARTIAL. `physics_place` exposes `settle/place/oracle/gate` (verdict-based, no state-transition hook). The M4+ ragdoll handoff is a NEW primitive, not a direct reuse. | P2 | §13.4 must specify the new state-transition primitive (event: `physics_handoff_start` → `physics_place.settle` → cache recovery → `physics_handoff_end`). Reference `kb/placement_and_physics.md`'s verdict vocabulary. |
| J3: UAL "canonical rig" per SKILL.md — CONVENTION, not formal contract. Kit's vendored UAL has 46 actions, 53 bones (per `assets_ual_actors.py:9`), NOT the upstream 250+ clips. | P1 | §8.1 must reference the vendored version at `assets/vendor/ual/` specifically. List the 46 actions. Flag missing locomotion states. |
| J4: Blender 4.5 LTS target. HANDOFF.md confirms 4.5.13 installed at `tools/blender-4.5.13-linux-x64/`. SKILL.md says "Ship 5.2 LTS default, keep 4.x compat shim". Shim handles EEVEE id, fcurves, NLA, sky type. | P3 | New system works on both via shim. Document in §11. Must specify `keyframe_insert_compat()` for the fcurve writing path (the shim only handles reading). |

---

## 5. Top 5 concrete revisions to the design doc (ranked by impact)

1. **Replace §6.1 navmesh algorithm entirely.** New text:

   > "Voxelize at agent_radius*2 resolution using a custom bmesh walk: (1) collect polygons whose `normal.z > 0.707` (walkable slope threshold); (2) reject polys under `Blocked` geometry within `agent_height` (use `mathutils.BVH.find_ray` for the overhang test — that is the correct BVH use); (3) build poly adjacency from `bm.edges` with `len(link_faces) == 2` (native bmesh, no kit dependency); (4) convex-decompose via Hertel-Mehlhorn on the triangle mesh. Spatial hash over poly centroids for O(1) neighbor lookup. Recast binding remains a M4+ option for higher-quality meshes."

2. **Move R2/GN instancing from "M2+" to "v1 day-1"** in §9.4 and §10.2. New text:

   > "v1 ships R0 (hero ≤100 agents) AND R2 (GN instancing for the remaining ≥900 agents). The 1K-agent gate is infeasible with R0-only — 1K × 53 bones × 240 frames × 7 channels = 89M keyframes exceeds the 4GB container. The cache drives a single GN instance group with `crowd_*` named attributes (bgyss §11.3 contract). R1 (reduced bones) and R3 (impostor) defer to M4+."

3. **Rewrite §8.1 LocomotionSet to ground in the vendored UAL.** New text:

   > "v1 uses the kit's vendored UAL at `assets/vendor/ual/` — 46 actions, 53 Rigify DEF-* bones, 1.651m bind height, gauntlet PASS (42/46 actions animate, drift 0.000m). Available clips (enumerated): [list]. Missing locomotion states: walk_start, walk_stop, turn_left, turn_right, arc_left, arc_right. v1 ships a degraded state machine (idle/walk_loop/jog only) until M2 sources missing clips. Retarget profile stays IDENTITY (UAL→UAL). No new rig imports in v1 — reuses the vetted `assets_ual_actors.py` path."

4. **Add §4.5 (Blackboard) minimal v1 surface.** New text:

   > "v1 ships a minimal blackboard: per-agent `mode` (uint8) and `visited_set` (columnar uint32 array, sparse). Two extra IR ops: `SetMode(mode)`, `IsVisited(region_id)`, `MarkVisited(region_id)`. The full typed columnar blackboard (boolean, integer, float, vector, entity ID, enum) defers to M2. This allows the zombie-port migration path (§3.4): each zombie state = a sub-graph, top-level Selector reads `mode`."

5. **Add §11.4 cache→scene attachment + keyframe writing.** New text:

   > "Cache attaches via `scene['crowd_cache_path']` custom property (string path to `shot.crowd/`). No `bpy.props` registration required. `bake.apply_to_scene()` reads this + manifest.json. Keyframe writing uses a kit shim `keyframe_insert_compat(obj, data_path, frame, value)` that calls `action.fcurves.new()` on 4.x and the slot/channelbag API on 5.x (parallel to the existing `iter_fcurves()` shim for reading). Action-slot law enforced: `ad.action = act; ad.action_slot = act.slots[0]` (per `kb/rigged_characters.md` gotcha #7)."

---

## 6. Open questions for the orchestrator

1. **STRICT mode cross-CPU tolerance**: drop the cross-CPU bitwise claim entirely (option c in D9), or invest in explicit reduction ordering (option a)? The latter is ~2× STRICT slowdown but preserves interchange. Recommend (a)+(c) — explicit ordering AND drop cross-CPU claim.

2. **UAL missing clips**: source the missing locomotion clips (walk_start, walk_stop, turn_left/right, arc_left/right) in M2, OR accept the degraded state machine (idle/walk_loop/jog only) for v1? The degraded machine is shippable; full locomotion transitions are M2 work.

3. **R2/GN instancing day-1**: confirm the GN instance group is in v1 scope. Without it, the 1K-agent gate is infeasible on 4GB. This is the single biggest scope change.

4. **Per-population cache invalidation**: is the additional complexity worth it for v1? If a single population changes, do we re-simulate everything (simpler) or just that population (faster iteration)? Recommend per-population from day 1 — the cost is small (manifest tracks per-population agent ranges).

5. **Zombie-port success criterion**: functional parity only ("agents reach destinations + gates pass") for M2, OR behavioral parity (LUNGE/REACH/etc. states reproduced) which requires the full M2 blackboard? Recommend functional parity.

6. **D7 zombie-port placement**: move to M2 (where the typed behavior graph lands) or keep in M3? Recommend M2 — that's where the migration-path complexity is cheapest to absorb.

7. **Phase 1 node count**: explicitly state "Phase 1 ships 3 of the 7 v1 nodes (Selector, Sequence, Navigate); Phase 2 completes the set"? Currently §13 is ambiguous.

8. **D5 expanded IR (10 nodes)**: confirm the 3 added nodes (SetMode, IsVisited, MarkVisited) are acceptable, or stick to the original 7 and accept that v1 cannot express stateful behaviors?

---

*End of audit. Report length: ~3,250 words. Ready for orchestrator review.*
