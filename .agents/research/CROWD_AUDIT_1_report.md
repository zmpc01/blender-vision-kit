# CROWD_AUDIT_1 — Crowd System Capability Audit

Source: `/home/sync/blender-escape-previz/scripts/crowd_agents.py` (756 LOC),
`scene_escape_v5.py` (integration surface only), `escape_lib.py` (262 LOC),
`/home/sync/blender-agent-kit/scripts/` (kit). Kit has NO existing crowd/nav/steering/flock/boid code (grepped; only incidental comment-text hits in `framing_audit.py`).

---

## 1. Executive summary

- **What it is**: a single-file pure-Python (no numpy, `import bpy` only) per-agent zombie FSM with a uniform 2 m hash-grid neighbour lookup, OBB-vs-jeep pushout, separation + obstacle circles, and a keyframe bake step. 129 sim agents (120 crowd + 9 chase non-RB) baked over 720 frames at `dt = 2/24 s ≈ 0.083 s` with frame decimation `every=2`.
- **Strengths**: deterministic (single `random.Random(4242)`); clean separation of `Agent`/`AgentSystem`/`bake`/`audit_*`; per-agent RNG-derived traits give visible variance; the uniform hash grid is a clean, reusable neighbour primitive; baked `rec[]` records double as the audit data source.
- **Shortcomings vs. AAA-grade**: no NavMesh/A*/flow-field navigation (target is a single point); no path-following or wayfinding around obstacles (obstacles are repulsive circles only); no dynamic obstacle avoidance beyond the hero OBB; no LOD; no real animation state machine (procedural shape-key blends keyed at decimated frames — no idle/walk/run/jump transitions); no foot IK, no ragdoll; pure-Python per-step loop will not scale past ~hundreds of agents.
- **Coupling to scenario**: the FSM (`LUNGE`, `REACH`, `FLEE`, `FALLBEHIND`, `GIVEUP`, `STAGGER`) and the steering math (jeep OBB pushout, hero point-target, belt-local frame, post-drive mode switch at `t=9.55`) are baked-in zombie-chase assumptions.
- **Audit discipline is the most reusable artefact**: 4 audit functions + external gate pipeline (`axis_gate`, `occlusion_gate`, `motion_frame_audit`, `coplanarity`) form a fail-closed verification contract — the only AAA-grade aspect of the project.

---

## 2. Capability inventory

| Capability | Present? | Where (file:line) | Notes |
|---|---|---|---|
| Per-agent FSM | Y | `crowd_agents.py:68` (9 states: IDLE/ALERT/PURSUE/LUNGE/REACH/STAGGER/FALLBEHIND/GIVEUP/FLEE) | Hardcoded zombie-specific state names; transitions in `run()` `crowd_agents.py:173-209` and `_active_step` `:253-444` |
| Spatial acceleration | Partial | `crowd_agents.py:140-144` (`_grid_build`), `:509-515` (`_neighbors`) | Uniform 2 m hash grid, 3×3 cell lookup; no BVH/quadtree, no GPU |
| Separation | Y | `crowd_agents.py:261-277` | Soft (`SEP_R=0.9`) + hard (`SEP_HARD=0.55`, 3× weight); boids cohesion/alignment absent |
| Cohesion | N | — | Not implemented |
| Alignment | N | — | Not implemented |
| Obstacle avoidance (static) | Y | `crowd_agents.py:283-296` | Circular obstacles only; repulsion `2.5/d`; used for KD performers + barricade pack |
| Obstacle avoidance (dynamic) | Partial | `crowd_agents.py:165,217,467-507` (`_obb_pushout`) | Only the single jeep OBB; lateral-only eject while driving, shortest-exit when parked; no general moving-vehicle handling |
| Path-following / wayfinding | N | — | None; agents steer toward a point |
| NavMesh / Recast / Detour | N | — | None |
| Goal-directed navigation (A*/Dijkstra/flow fields) | N | — | Single point-target only (`hero_fn`/`jeep_fn`) |
| Force fields (attraction/repulsion zones) | Partial | `crowd_agents.py:113` (`trigger_radius` w/ `TRIGGER_SCALE=(0.67,1.33)`), `:52-66` | Awareness horizon + menace-ring (`RING_HOLD=3.0`, `RING_FAR=5.0`) `:56-59`; both scenario-shaped |
| Agent varieties / archetypes | Partial | `crowd_agents.py:39-50,88-125` | Per-instance traits via RNG (speed/accel/aggr/stamina/gait/weave); no data-driven archetype table; `kind ∈ {"crowd","chase"}` only |
| Animation state machine | N | — | Procedural shape-key blends (swing/lean/raise/lungef) keyed at decimated frames `:518-576`; no locomotion blends, no transition logic |
| Foot IK / foot placement | N | — | Lift-only bob `|sin|*0.03` `:236-240`; A2 discipline only |
| Ragdoll / death physics | N | — | RB falls handled separately in `scene_escape_v5.py:1434` (`RB_FALLS=[2,5,8]`), excluded from the sim |
| LOD (level of detail) | N | — | None |
| Multi-threading / vectorization | N | — | Pure Python, single-threaded `for a in self.agents` loop `:158` |
| Bake-to-keyframe vs real-time | Y | `crowd_agents.py:518-576` (`bake`), `:124` (`rec`) | Bake-only; records per-step `rec` then decimates `every=2` |
| Determinism (seeded RNG) | Y | `crowd_agents.py:36` (`SEED=4242`), `:130` (`random.Random(seed)`), `:579-585` (`rng_uniform`) | Single RNG; hash-free per-agent draw stable across call-site moves |
| Audit / verification gates | Y | `crowd_agents.py:643-749` (4 funcs), `scene_escape_v5.py:2336-2459` (pipeline) | Fail-closed hard gates + advisory gates |
| Camera keepout | Y | `crowd_agents.py:446-465` (`_cam_pushout`), `:283-296` (len-6 obstacle tuples) | Time-scoped world-frame circles, `w2b(t)` converter; v3.4 |
| Hero / leader / target pursuit | Y | `crowd_agents.py:1009-1009` (`hero_fn` in scene_escape), `:341-344` | Single hero point pre-drive, jeep tail post-drive |
| Group behaviors (formations, flocking) | N | — | Only informal "ring milling" `:385-402` (weave-only on `ring_band`) |
| Terrain following (slope, stairs) | N | — | Flat belt only (`escape_lib.py:80` `TOTAL_DIST`, `:85-89` BELT extents) |
| Crowd density / flow control | Partial | `crowd_agents.py:55-59` (`REACH_CAP=6`, `RING_HOLD`, `RING_FAR`) | Pounder cap + menace ring is scenario-specific density shaping |

---

## 3. Coupling map

| Capability | Classification | What to refactor/keep/drop |
|---|---|---|
| FSM scaffold (`Agent.state`, `_active_step` dispatch) | REUSABLE-WITH-REFACTOR | Keep state-machine + transition-timer pattern; replace 9 zombie states with a configurable state registry (states-as-data) |
| Uniform 2 m hash grid (`_grid_build`, `_neighbors`) | REUSABLE-CORE | Lift directly; parameterise cell size |
| Separation force (`SEP_R/SEP_HARD`) | REUSABLE-CORE | Generic; keep |
| Obstacle-circle repulsion (`:283-296`) | REUSABLE-CORE | Generic; keep — but add line/poly shapes |
| Jeep OBB pushout (`_obb_pushout`) | SCENARIO-SPECIFIC | Generalise to N moving OBBs with per-OBB policy (lateral-only, shortest-exit, clip) |
| Awareness horizon + menace ring | REUSABLE-WITH-REFACTOR | Generalise "ring" to a configurable goal-distance-hold behaviour; drop zombie framing |
| `trigger_radius`, `TRIGGER_SCALE` | REUSABLE-WITH-REFACTOR | Keep per-agent variance multiplier; rename |
| `add_shape_keys` (`:591-637`) | SCENARIO-SPECIFIC | Hardcoded arm-vertex selection on zombie variant meshes; drop or rewrite as data-driven rig-driven morphs |
| `bake()` decimation `every=2` | REUSABLE-CORE | Generic decimated keyframing |
| Per-step `rec[]` recording | REUSABLE-CORE | Clean audit data source; keep |
| `rng_uniform` hash-free per-agent draw | REUSABLE-WITH-REFACTOR | Keep determinism invariant; replace name-length hash with a stable per-agent index |
| `audit_liveliness`, `audit_speed_variance`, `audit_ground_contact`, `audit_no_riders` | REUSABLE-WITH-REFACTOR | Pattern is gold; re-target each audit's scenario predicate (`jeep_fn`, `STAND_LEGAL`, ring milling carve-out) |
| Camera keepout (`_cam_pushout` + len-6 obstacle tuples) | REUSABLE-WITH-REFACTOR | Generalise to time-scoped world-frame keepout volumes; keep `w2b` converter abstraction |
| `hero_fn`/`jeep_fn` callbacks | REUSABLE-CORE | The contract (callable returning `{pos, half, speed}`) is good — keep, just parameterise |
| `post_drive_t` mode switch | SCENARIO-SPECIFIC | Drop; replace with per-agent goal-source timeline |
| States `LUNGE`, `REACH`, `FLEE`, `FALLBEHIND`, `GIVEUP`, `STAGGER` | SCENARIO-SPECIFIC | Drop from core; provide as a scenario plugin |

---

## 4. Hardcoded scenario assumptions

- `SEED = 4242`, `FPS = 24` — fine, but constant lives in module (`crowd_agents.py:36-37`)
- Population table `P` keys named `chase_speed_lo/hi`, `aggr_lo/hi`, `stamina_lo/hi` (`:40-50`) — zombie-chase semantics baked into param names
- State enum and names: `LUNGE, REACH, STAGGER, FALLBEHIND, GIVEUP, FLEE` (`:68-71`)
- Behaviour constants: `REACH_DIST=0.45`, `REACH_CAP=6` ("pounders"), `RING_HOLD=3.0`, `RING_FAR=5.0` (menace ring), `LUNGE_R=1.7`, `FLANK_R=2.5`, `FALLBEHIND_GAP=18.0`, `POUND_HZ=2.5`, `TRIGGER_SCALE=(0.67,1.33)` (`:52-66`)
- `Agent.kind ∈ {"crowd","chase"}` (`:89,94,97`) — two zombie roles only
- `post_drive_t=9.55` default in `run()` signature (`:146`) — the jeep-lurch time
- Driving-mode chase-the-TAIL: `ty -= jeep["half"][1] + 0.55` (`:168,343`) — assumes jeep geometry
- FLEE policy: `jeep.get("speed", 0.0) > 9.0` + `abs(a.x - jeep["pos"][0]) < 3.5` + `a.aggression < 0.55` (`:324-327`) — zombie bravery threshold
- `_obb_pushout` RIDER FIX comment block + lateral-only ejection + STAGGER clip with `clip_vx/vy` (`:165,217,467-507`)
- Hero keepout constant `0.35 + P["radius"]` and weight `4.0/d` (`:301-304`) — assumes hero radius
- `add_shape_keys` arm-vertex heuristic `0.15 < abs(v.co.x) < 0.55 and v.co.y > 0.05 and v.co.z < sh+0.02` (`:606-608`) — zombie-mesh-specific
- `bake()` keys `swing`, `lean`, `lungef`, `raise` shape keys by name (`:533,553,558,566`) — zombie morph names
- `audit_no_riders` predicate `abs(rel0) < 3.0 and abs(jy1-jy0) > 2.0` (`:743-744`) — jeep-relative
- `audit_ground_contact` `tol_hi=0.040` (`:704`) — lift-only-bob specific
- In `scene_escape_v5.py`: `_V32_CTX` global, `RB_FALLS=[2,5,8]` (`:1434`), `T_DRIVE=9.55` (`:91`), `RUN_START_Y=-27.5` (`:93`), `KNOCKDOWNS_V3` (`:331`), `MUZZLE_BURSTS_V3` (`:351`), `SHOTS_V3` (`:161`), `CAMS_V3` (`:242`) — all zombie-escape scenario tables
- `escape_lib.py`: `KNOCKDOWNS`, `CROWD_ZONES`, `CHASE_GAPS/CHASE_XS/CHASE_FALLS`, `LUNGE` dict, `BARRICADE_PACK_*`, `MUZZLE_BURSTS`, `PALETTE["zombie_body"]` (`:100-145,154-180`)

---

## 5. Performance characteristics

- **Agent count**: 129 sim agents (120 crowd + 9 chase; `scene_escape_v5.py:966,1016-1032`). Crowd zones in `escape_lib.py:114-118` sum to 86 (26+48+12) — drift between v3 lib and v5 master; v5 spawns more elsewhere.
- **Sim step**: `dt = 2/FPS = 1/12 s ≈ 0.0833 s`; `t_end = 45.0 s` → `n_steps ≈ 540` (`crowd_agents.py:129,149`).
- **Grid**: 2 m cells, 3×3 neighbour scan — O(N) per step amortised; fine at 129 agents, O(N²) cliff around ~1k.
- **Bake**: `total_frames=720` (EL.TOTAL_FRAMES), `every=2` decimation → ~360 keyframes/agent/path × 3 loc + 3 rot + up to 4 shape keys = ~5,000 keyframes/agent, ~640k total. Bake cost not measured in-file.
- **Frame-time/scalability**: pure Python single-thread; no numpy, no batched math. Per-step work per agent: 1 grid lookup + ≤9 neighbour tests + 1 OBB dist + 1 OBB pushout + state update + 1 record append. ~100k Python ops/step; ~540 steps × 129 agents. Wall-clock not recorded — likely minutes, not seconds.
- **Obvious limits**: no LOD, no vectorisation, no NavMesh; scaling beyond ~500 agents would require numpy + spatial index upgrade.

---

## 6. Integration surface

**Contract** (the only entrypoints called by `scene_escape_v5.py`):

```
class AgentSystem(seed=SEED, dt=2/FPS)
  .add_agent(obj, kind:str, x, y, height, trigger_radius=30.0) -> Agent
  .run(t_end, hero_fn, jeep_fn, obstacles=(), post_drive_t=9.55, verbose=False)
  .bake(total_frames=1080, every=2) -> dict
# module-level
add_shape_keys(obj, height) -> dict
audit_liveliness(agents, t_end, samples=10) -> [str]
audit_speed_variance(agents, t_probe) -> [str]
audit_ground_contact(agents, tol_lo=-0.010, tol_hi=0.040) -> [str]
audit_no_riders(agents, jeep_fn, dt=None) -> [str]
```

**Callback contracts** (defined in `scene_escape_v5.py:1000-1013`):
- `hero_fn(t) -> {"pos":(x,y), "speed":float}`
- `jeep_fn(t) -> {"pos":(x,y), "half":(hx,hy), "speed":float}` — `half` is the OBB half-extents
- `obstacles` entries: either `(x, y, r)` (belt-local static circle) or `(x, y, r, t0, t1, world_to_belt_fn)` (time-scoped world-frame camera keepout)

**Call sequence in `_run_crowd_sim(ctx)`** (`scene_escape_v5.py:965-1036`):
1. `import crowd_agents as CAG; AG = CAG.AgentSystem(seed=CAG.SEED)`
2. Build `obstacles` list: KD performers + barricade pack + 2 camera keepouts (`:980-998`)
3. Define `hero_fn`, `jeep_fn`
4. For each crowd/chase object: `ob.data = ob.data.copy()`, `add_shape_keys`, `AG.add_agent(...)`, set `ag.shape_ok = True`
5. `AG.run(45.0, hero_fn, jeep_fn, obstacles, post_drive_t=T_DRIVE, verbose=True)`
6. `AG.bake(EL.TOTAL_FRAMES)` — writes belt-local keys directly to each agent's `obj`
7. `return AG` — stored in `ctx["agents"]` for downstream audit and gate pipeline

---

## 7. Test / audit coverage

**In-file audit functions** (`crowd_agents.py:643-749`):

| Function | Checks |
|---|---|
| `audit_liveliness(agents, t_end, samples=10)` | Every on-road agent must MOVE (pos + yaw) in every 0.5 s window; carve-outs for state transitions to `STAND_LEGAL={GIVEUP,IDLE,ALERT,STAGGER}` and for ring-milling (`a.ring` majority-true in window) |
| `audit_speed_variance(agents, t_probe)` | std-dev of reconstructed per-agent speeds ≥ 0.5 m/s; ≥ 8 moving agents required |
| `audit_ground_contact(agents, tol_lo=-0.010, tol_hi=0.040)` | Every agent's baked feet z stays within tolerance of `base_z` (lift-only bob discipline) |
| `audit_no_riders(agents, jeep_fn, dt=None)` | No agent tracks jeep belt-y with near-zero relative velocity over 1 s windows while driving (`|rel1-rel0|<0.05`, `|jy1-jy0|>2.0`, `|rel0|<3.0`) |

**External gate pipeline** (`scene_escape_v5.py:2336-2459`):
- Hard fail: `coplanarity_audit`, `framing_audit` (subject-margin), penetration (jeep OBB vs sim `rec` at t=29,30,31,31.4,31.8,32.6), `audit_liveliness`, `audit_speed_variance`, FX star-key coverage, Street.RoadGrid presence/z-band
- Advisory: `axis_gate`, `occlusion_gate` (every-frame lens-ray), `motion_frame_audit`, `audit_ground_contact`, `audit_no_riders`

**Tests**: no unit tests, no integration tests, no smoke tests in either repo. Verification is exclusively the post-bake gate pipeline.

---

## 8. Reusable patterns worth keeping

1. **Per-step `rec[]` recording** (`crowd_agents.py:124,242-243`): every audit runs off the recorded trajectory, not the live scene — decouples verification from frame_set / depsgraph cost. The new system should make recording mandatory.
2. **Callable goal-source contract** (`hero_fn`/`jeep_fn` returning `{pos, half, speed}`): the sim is parameterised by *what to chase*, not by hardcoded targets. This is the right seam for a general crowd system — generalise to N goal sources with arbitrary geometry.
3. **Fail-closed gate pipeline** (`scene_escape_v5.py:2336-2459`): hard gates abort, advisory gates report, every gate wrapped in try/except so a gate crash is itself a finding. Worth lifting as the verification framework.
4. **Hash-free deterministic per-agent RNG draw** (`rng_uniform`, `:579-585`): derives from stable per-agent state (`gait_phase`, `weave_phase`, `len(name)`) so determinism survives call-site moves. Pattern worth keeping (the implementation needs revision: `len(name)` is fragile).
5. **Uniform-hash-grid + 3×3 neighbour scan** (`_grid_build`, `_neighbors`, `:140-144,509-515`): the simplest correct neighbour primitive — 12 lines, no deps, O(N) build. Keep as the default spatial index for low agent counts in the new system.

---

## 9. Open questions for the orchestrator

1. **Animation**: should the new system provide a real locomotion state machine (idle/walk/run/jump transitions with blends), or keep the procedural-shape-key approach for previz-grade crowds? The current `add_shape_keys` is mesh-geometry-specific and won't generalise.
2. **Navigation**: is NavMesh/Recast in scope, or do we stay point-target + repulsion-circles? No path-following exists today.
3. **Dynamic obstacles**: how many simultaneous moving OBBs/agents-as-obstacles must the new system support? Currently 1 (the jeep). Per-agent-as-obstacle would change the neighbour query cost.
4. **Scale target**: is the goal previz-grade (≤ ~500 agents, bake-to-keyframe) or runtime-grade (1k–10k, vectorised)? The current pure-Python loop cannot do the latter; numpy/batched steering is a rewrite, not a refactor.
5. **Bake vs. real-time**: keep bake-only, or add a real-time playback path? `bake()` writes directly to `obj.keyframe_insert` — that contract is the only integration seam with the rest of the pipeline.
6. **Determinism contract across runs**: `SEED=4242` is module-level and `rng_uniform` is name-length-dependent. Should the new system require deterministic re-runs across Python/Blender versions? If yes, the name-length hash must be replaced with a stable per-agent index.
7. **Camera keepout**: is the time-scoped world-frame keepout (the v3.4 fix) a first-class concept, or scenario-specific? The pattern generalises but the `w2b(t)` converter is treadmill-specific.
8. **Audit data source**: keep `rec[]`-driven audits (cheap, deterministic) or move to scene-frame audits (post-bake `frame_set` walks, expensive but catches bake interpolation bugs the records don't)?
