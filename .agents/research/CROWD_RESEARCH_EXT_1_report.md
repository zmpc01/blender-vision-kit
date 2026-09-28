# CROWD-RESEARCH-EXT-1 — External Crowd Simulation Tech Survey

A survey of external crowd-sim tech the orchestrator can LEVERAGE (OSS libs,
algorithms, Blender add-ons, formats, asset sources) for a AAA-grade crowd
system that will live inside the blender-agent-kit (Blender 4.5 LTS / 5.2 LTS,
headless container, 4 GB RAM, no GPU, Python-scripted).

Prior context: see `CROWD_AUDIT_1_report.md` — kit has no existing crowd code;
the previz-only `crowd_agents.py` (756 LOC) is a pure-Python zombie FSM.

---

## 1. Executive summary (top 5 things the orchestrator needs first)

1. **A working AAA-grade reference already exists in our ecosystem.**
   `bgyss/Blender-Crowd` (GPL-3.0, last commit 2026-08-20, M0–M6 accepted) is
   a Rust-core + Blender-Python + Geometry-Nodes-presentation crowd system
   with a 100K-agent scale gate and 1K-agent 30Hz deterministic bake. It
   implements tiled navmesh, ORCA + sampled_velocity + anticipatory avoidance,
   schema-versioned cache, behavior graph (compiled to IR), stable 64-bit
   agent IDs, ABI3 PyO3 wheel — exactly the architecture the orchestrator is
   asked to design. **Read `docs/blender-crowd-1.0.md` before designing.**
   *Constraint*: macOS arm64 + Blender 5.2 only; 100K gate needed 64 GB M1
   Max. On the kit's 4 GB container we can borrow architecture + JSON
   schemas, not the binaries.

2. **For navigation, Recast & Detour is the only serious choice** — 7.9k★,
   actively maintained (Feb 2026), used by Unity and UE5. Includes
   DetourCrowd (ORCA-based local avoidance) and DetourTileCache (dynamic
   obstacles). Python bindings exist (`recast-navigation` PyPI, `DotRecast`)
   but are immature — best path is **vendor Recast C++ → PyO3/cffi shim**,
   or generate navmesh via Blender's BVH and consume in pure Python.

3. **The animation problem is solved by clip-driven blend trees + a tiny clip
   library, NOT procedural shape-keys.** The kit has Quaternius UAL (CC0,
   53 bones, 120+ locomotion clips). bgyss uses CMU mocap (rejected at 3,587
   joint-limit violations) + authored CC0 fixtures. Adopt **state-machine →
   clip graph → blend tree → retargeted to UAL rig** as the backbone.
   Houdini's "Agent Definition + State + Trigger + Transition Graph" is the
   reference architecture.

4. **Adopt context steering over weighted steering for agent-level decisions.**
   Andrew Fray's 2013/2015 model (per-behavior context maps, danger/interest
   lanes, mask-and-vote) is deterministic, debuggable, removes weighted-sum
   tuning traps, and composes cleanly with ORCA at the avoidance layer
   (steering produces preferred velocity; ORCA enforces non-penetration).
   The existing `add_shape_keys` zombie morphs are a dead end for general crowds.

5. **Mixamo + UAL + ActorCore cover the asset gap with one retargeting story.**
   Mixamo is royalty-free for CC subscribers (redistribution restricted);
   UAL is CC0 (perfect for kit); ActorCore has 4,500+ motions under permissive
   terms. Standardize on UAL's 53-bone rig; retarget everything to it via
   Blender Auto-Rig Pro's Remap or a bone-map table.

---

## 2. A. Blender-native crowd add-ons

| Add-on | License | Lang | Algorithmic approach | Animation system | Maintenance | Use-for | Risks |
|---|---|---|---|---|---|---|---|
| **bgyss/Blender-Crowd** | GPL-3.0-or-later | Rust + Py | Tiled navmesh + corridor; ORCA/sampled/anticipatory avoidance (3-solver comparison); behavior graph compiled to IR; SoA agent buffers; uniform-grid spatial index | Clip-driven locomotion state machine (idle/walk/run/turn/arc/stop); CMU mocap pipeline (rejected at 3,587 joint violations) + CC0 authored fixtures; foot-planting & terrain adaptation in M6 | Active; last commit 2026-08-20; M0–M6 accepted, M7–M9 planned | Architecture template; borrow schemas + cache format + behavior-IR design | macOS-arm64 only; 64 GB M1 Max for 100K; requires Blender 5.2 LTS |
| **iCrowds 2.21** (Parametra/iCity creator) | Commercial ($19, Blender 4.5 ext) | Py + Geo Nodes | "7 crowd-generation systems" (point/scatter/stadium/street/queue/park/line); procedural; ragdoll added in v2.0 (Mar 2026) | Procedural + clip library; ragdoll for action shots | Active; 400+ sales, 4 ratings, v2.0 released Mar 2026 | Feature ideas (ragdoll handoff, "static systems" for ambient crowds); confirm any system handles chase/pursuit | Closed source; can't audit; paywalled; no real navmesh/behavior graph evidence |
| **CrowdMaster** (John Roper) | GPL-3.0 (free) | Py (Blender 2.7x–2.8) | Boids-like + node graph; emulates Golaem core; no real navmesh | Shape-key animation + action clips per agent | **Abandoned**; last release v1.3.2 (Aug 2017); 2.8 port incomplete | Historical reference only; Golaem-emulation ideas | Unmaintained; pre-2.8 codebase; no Blender 4.5 compat without rewrite |
| **Agents** (Polycount, Dec 2024) | Free | Geo Nodes | Pure Geometry Nodes — wrap-around of native instancing + clip selection | Clip library + offset; no behavior | Recent (Dec 2024) | Reference for "GN-as-presentation-layer" pattern (also bgyss §3.1) | No sim; purely for static/looping ambient crowds |

**Deeper commentary.**

- **bgyss/Blender-Crowd** is the standout: only open-source Blender crowd
  system with a 1K-agent deterministic gate, a 100K-agent scale gate,
  schema-versioned JSON project files (brain, perception, activity, motion,
  physics-transition, formation, override-layer, retarget-profile), and an
  explicit M0→M9 milestone contract. `docs/blender-crowd-1.0.md` (1,167 lines)
  is effectively the spec for what we're being asked to build. It forbids
  per-agent Python in hot loops ("Rust owns hot loops; Python orchestrates
  coarse operations") — the correct posture for the kit's 4 GB container.
  CMU-mocap rejection at 3,587 joint-limit violations is cautionary:
  off-the-shelf mocap needs validation before adoption.

- **iCrowds 2.0** is marketing-light on the algorithmic side — the
  superhivemarket page is mostly CSS and the substantive feature claims live
  in cgchannel news coverage (Mar 12, 2026): "7 crowd-generation systems", a
  new ragdoll system for action shots, $19, Blender 4.5 Extension. The
  ragdoll handoff is the most borrowable idea — the kit's current
  `RB_FALLS=[2,5,8]` + `RB_KD=["KD3"]` pattern is the same idea, expressed
  ad hoc. The "static systems" framing (stadiums, parks, lines) is a useful
  product vocabulary for distinguishing ambient crowds from agent-driven
  crowds.

- **CrowdMaster** is dead code. Its Golaem-emulation intent is the right idea
  (Golaem's open-sourcing on Aug 3, 2026 means the actual Golaem source is
  now available — see §3). Skip CrowdMaster.

- **Agents (GN-based)** validates bgyss's "Geometry Nodes is a presentation
  layer, not the authoritative simulator" — same conclusion from two
  independent projects.

---

## 3. B. Standalone OSS crowd simulation libraries

| Library | License | Lang | Approach | Last commit | Blender integration path | Use-for | Risks |
|---|---|---|---|---|---|---|---|
| **Recast & Detour** (`recastnavigation/recastnavigation`) | Zlib | C++ | Navmesh build (voxel→polygon), A* pathfind, string-pulling, DetourCrowd (ORCA-based), DetourTileCache (dynamic obstacles) | Feb 27, 2026 (active); 7.9k stars, 1.8k forks | Vendor as git submodule; build with CMake; expose via PyO3/cffi shim OR use `recast-navigation` PyPI (immature). Blender has BVH but no navmesh — this is the missing piece | Navmesh generation + pathfinding + local avoidance | C++ build chain in 4 GB container; PyPI bindings laggy; ABI drift across Blender Python versions |
| **RVO2 / Python-RVO2** (`mit-acl/Python-RVO2`) | Apache-2.0 | C++ + Cython | ORCA reference implementation by van den Berg; 2D n-body reciprocal collision avoidance | Active; Cython bindings | pip installable on Linux; pure CPU; no Blender deps | Reference ORCA solver; benchmark against own impl | 2D only (3D needs extension); single-file, not full stack |
| **OpenSteer** (Craig Reynolds) | MIT | C++ | Steering behaviors library (seek/flee/arrive/wander/avoid/path-follow); demo app | Last release 2008; **abandoned** | None natively; rewrite in Python (the math is ~200 LOC) | Algorithm reference only | Dead; pre-C++11; would need full port |
| **SteerLite / SteerSuite** (`SteerSuite/SteerLite`) | MIT | C++ | Academic steering testbed; test cases + recorder + evaluator | Last commit Dec 2015 (3 stars, 58 forks; effectively dead) | None; use as test-case inspiration only | Test-case taxonomy for steering behavior validation | Inactive; depends on Qt/OpenGL |
| **Menge** (Oregon State) | BSD-3 | C++ | Full academic crowd-sim framework: FSM behaviors, perception, navmesh, ORCA, social models | Repo not directly searchable; academic project; MengeROS fork exists (2017) | None realistic (C++ framework, not a lib) | Algorithm reference; pedestrian behavior models | Likely dormant; no recent activity; framework lock-in |
| **JuPedSim / JPScore** (`PedestrianDynamics/jupedsim`) | GPL-3.0 | C++ | Microscopic pedestrian dynamics for evacuation; social-force + GCFM models; bottleneck/corridor/egress test cases | Active (arxiv 1907.09520, 119 cites); Forschungszentrum Jülich | Could be a sub-process for evacuation sim only | Evacuation/pedestrian validation baselines | Niche (egress); not general-purpose crowd; C++/CMake |
| **Golaem (now open source)** | Apache-2.0 (Aug 2026) | C++ (Maya/Houdini plugin) | Maya-native crowd: behaviors, navigation, ragdoll, layout editing; layout tool for post-sim adjustment | Open-sourced Aug 3, 2026 by Autodesk | Indirect — Maya/Houdini, not Blender; borrow patterns & data formats | Architectural reference for layout/override/shot-edit layer | No Blender port; Maya-centric RNA |
| **Harfang3D** | GPL-3.0 | C++ + Py/Lua/Go | 3D engine wrapping Recast/Detour | Active | None — too heavy | Reference for binding patterns | Engine, not a lib |

**Deeper commentary.**

- **Recast & Detour is the de-facto standard** (Unity, UE5, Godot).
  `DetourCrowd` already implements ORCA. Cleanest kit path: PyO3 wheel
  wrapping Recast/Detour/DetourCrowd/DetourTileCache as a coarse API
  (build → find_path → crowd_step). 4 GB constraint: navmesh builds are
  voxelization-heavy; 100m×100m × 0.5m voxels ≈ 100 MB peak — feasible.
  Larger scenes use tiled builds.

- **RVO2 is the ORCA reference impl** — port to NumPy for ≤1K agents;
  above 1K switch to C++ RVO2 or DetourCrowd. bgyss did this in Rust.

- **Menge** (OSU academic framework): worth reading but not adopting.
  `BaseAgent` hierarchy + FSM behavior model documented in OSU pubs;
  bgyss's behavior-graph is a more rigorous Menge successor. Read papers;
  skip the code.

- **Golaem's open-sourcing (Aug 3, 2026) is a major event.** Maya/Houdini-bound
  but the C++ source now exposes their agent representation, behavior graph,
  layout-editing patterns, and cache format — direct AAA reference.

---

## 4. C. Proprietary AAA systems (feature reference only)

| System | Owner | Target industry | Standout feature to borrow | Open-source equivalent |
|---|---|---|---|---|
| **Massive** (Multiple Agent Simulation System in Virtual Environment) | Massive Software (Stephen Regelous, originally Weta) | Film VFX | **Fuzzy-logic brain** with stereo-vision perception → motion-tree clip selection; agents as brain+skeleton+body; pre-built agent libraries (stadium, riot, walk-and-talk) | None — but bgyss/Blender-Crowd explicitly aims at "MASSIVE-style authorable agency" |
| **Golaem** | Autodesk (open-sourced Aug 2026) | Film/TV | **Layout tool** for shot-level post-sim adjustment without re-baking; Maya-native integration; ragdoll + traffic + plane crowds | Now Apache-2.0 (C++ source) — direct reference |
| **Miarmy** | Basefount | Film/TV (Maya) | "Human logic engine" + integration with Maya particles/fields/fluids; fuzzy logic; creature physical simulation | None direct; bgyss pattern matches |
| **Houdini Crowds** | SideFX (Solaris/USD-native) | Film/VFX | **State + Trigger + Transition-Graph** animation model; Agent Definition as data; Vellum cloth on agents; fuzzy logic node; terrain adaptation with foot planting; Crowd Procedural for render-time optimization | Houdini Apprentice free; bgyss mirrors the State/Trigger/TransitionGraph pattern |
| **UE5 Mass Entity** | Epic Games | Games | **Data-oriented ECS** for crowds (fragments + tags + behaviors + mass signals); handles 10K+ AI agents at 60 FPS on high-end HW; ZoneGraph for navmesh; StateTree for behavior | UE5 source available under EULA; not OSS |
| **Unity ECS / DOTS (Megacity Metro)** | Unity Technologies | Games | **DOTS ECS** with subscene streaming; 150+ players/Megacity demo; entity-querying for crowds | Megacity Metro is OSS (github.com/Unity-Technologies/megacity-metro); DOTS itself is OSS |

**Architectural patterns worth borrowing.**

- **From Massive**: fuzzy-logic perception → motion-tree selection. Agents
  as brain+skeleton+body. Motion trees (not blend trees) for clip
  composition under perception-driven selection.
- **From Golaem**: post-sim **Layout tool** — artists adjust characters in
  viewport without re-baking. This is the bgyss "Shot overrides" layer (§4.5). Borrow verbatim.
- **From Houdini Crowds**: Agent Definition as data (clip library,
  transition graph, state, trigger); foot planting via IK foot-lock;
  fuzzy logic as a node type; ragdoll as a state transition, not a separate sim.
- **From UE5 Mass Entity**: data-oriented SoA agent storage;
  fragment/tag/processor separation (no per-agent objects); ZoneGraph
  (lane-aware navmesh). For ≤1K agents, pure-Python equivalent is NumPy
  SoA arrays; above 1K, native core (bgyss pattern).
- **From Unity DOTS**: subscene streaming for bake/playback separation;
  entity archetypes (fragment combos → archetype → specialized processor).
  For the kit: cache files are the "subscene"; Blender streams cache chunks.

---

## 5. D. Algorithm catalog

1. **Reciprocal Velocity Obstacles (RVO)** — *van den Berg, Lin, Manocha 2008, [paper](https://gamma.cs.unc.edu/RVO/)*. O(N²) per step (with neighbor pruning O(N·k)). First-order collision avoidance via velocity cones; each agent assumes others are equally responsible. **When**: baseline local avoidance, ≤2K agents, no global coordination needed.
2. **ORCA (Optimal Reciprocal Collision Avoidance)** — *van den Berg, Guy, Lin, Manocha 2011, [paper](https://gamma.cs.unc.edu/ORCA/)*. O(N·k) per step with spatial hash. Closed-form 2D LP per agent pair; collision-free under reasonable assumptions; basis of DetourCrowd and RVO2. **When**: default local avoidance for any serious crowd sim.
3. **Continuum Crowds** — *Treuille, Cooper, Popović 2006, [paper](https://grail.cs.washington.edu/projects/crowd-flows/continuum-crowds.pdf)*. O(N) per step after O(grid) potential-field solve. Density + velocity field → global navigation with moving obstacles; solves a dynamic potential field. **When**: large homogeneous flows (10K+ agents) where global coordination matters more than per-agent identity.
4. **Social Force Model** — *Helbing & Molnár 1995 (cited 6564×); see also Moussaïd et al. 2011 [paper](https://www.pnas.org/doi/10.1073/pnas.1016507108)*. O(N·k) per step. Pedestrian-as-particle subject to social forces (attraction to goal, repulsion from others, lane-formation emergent). **When**: pedestrian/evacuation realism; calibration is hard.
5. **Hierarchical Pathfinding A* (HPA*)** — *Botea, Müller, Schaeffer 2004, J. Game Dev 1(1):7–28*. Near-optimal (<10% suboptimal) with O(log N) clusters; pre-compute cluster graph then A* on clusters. **When**: large static maps where navmesh tile-level A* is too slow; alternative to Recast's tiled A*.
6. **A* + Jump Point Search (JPS)** — *Harabor & Grastien 2011, AAAI; Harabor 2014 JPS+ variant*. O(N·k) but with 10–20× fewer node expansions than A* on uniform grids; JPS+ precomputes jump points for further speedup. **When**: grid-based pathfinding on uniform grids (not navmesh); alternative to HPA*.
7. **Boids** — *Reynolds 1987, SIGGRAPH*. O(N·k) per step with neighbor pruning. Three rules: separation, alignment, cohesion. **When**: flocking ambient wildlife (birds, fish, low-density ambient crowds); not for goal-directed pedestrian flow.
8. **Steering Behaviors** — *Reynolds 1999, GDC; [red3d.com/cwr/steer/](https://www.red3d.com/cwr/steer/)*. O(1) per behavior per agent. Seek, flee, arrive, wander, obstacle avoidance, path following, separation, queue. **When**: simple agent AI; building blocks for richer behavior — but read Fray's critique below.
9. **Context Steering** — *Fray 2013/2015, [andrewfray.wordpress.com](https://andrewfray.wordpress.com/2013/05/15/context-behaviours-digest/); GDC 2015 talk*. O(B·d) per agent where B=behaviors, d=context-map resolution (typically 8–16). Replaces weighted-sum steering with per-behavior context maps (interest + danger lanes), combined via mask-and-vote. Deterministic, debuggable, composable. **When**: **default agent-level steering for our system** — supersedes weighted Reynolds steering.
10. **Motion Trees / Blend Trees** — *Massive (motion tree); Unity Mecanim (blend tree)*. O(1) per agent per frame once clip graph compiled. State machine → clip selection → blend (1D/2D Cartesian or polar) by speed/turn. **When**: locomotion state machine with idle/walk/run transitions; the right animation backbone for our system.
11. **Sub-stepping / fixed-timestep integration** — *standard game-physics practice*. O(N·s) per render frame, where s = substeps. Decouples sim rate from render rate; bgyss uses 30Hz sim tick independent of Blender frame rate. **When**: any crowd sim — non-negotiable for determinism.
12. **LOD strategies for crowds** — *Beacco Porres 2016 survey, [upcommons.upc.edu](https://upcommons.upc.edu)*. Three tiers: polygon-skeletal (close), point-cloud (mid), impostor billboard (far); bgyss uses S0/S1/S2/S3/R0–R4 tiers. **When**: any scene with >1K visible agents; bake LOD into cache channels (per-agent tier per frame).
13. **Tiled NavMesh + Corridor** — *Recast/Detour pattern; bgyss follows it*. O(N) build, O(log N) pathfind. Bake navmesh per tile; build corridors of polys; string-pull waypoints. Dynamic obstacles invalidate only affected tiles via DetourTileCache. **When**: standard nav — adopt for our system.
14. **Behavior Tree / Utility AI / FSM trichotomy** — *Mark 2014 GDC; bgyss §4.4*. FSM for mode-switching (readable), utility scoring for competing goals, behavior tree for ordered actions + fallbacks. **When**: agent decision layer — adopt all three as compiled IR nodes (bgyss pattern), not arbitrary Python callbacks.
15. **Fuzzy Logic Perception** — *Massive; Houdini fuzzy-logic node*. O(N) per agent. Membership functions over perception inputs (near, fast, hostile) → behavior selection via fuzzy rules. **When**: hero-tier agents needing nuanced reactions; defer to M6+ (per bgyss roadmap).

---

## 6. E. Asset / animation sources

| Source | License | Rig format | Retargeting story | Locomotion clip count | Notes |
|---|---|---|---|---|---|
| **Mixamo** (Adobe) | Royalty-free *if* downloaded with active CC subscription; redistribution restricted | Mixamo Humanoid (~24 joints; FBX) | Auto-Rig Pro Remap or Blender's Rigify→Mixamo bone-map; Unreal Mannequin auto-maps | 2,500+ mocap clips (incl. locomotion, combat, idle, gesture) | Most clips free; **risk**: subscription tied, can't redistribute raw clips in kit; vet each clip's commercial-use terms |
| **AccuRIG / ActorCore** (Reallusion) | Free AccuRIG tool; ActorCore motions are per-item licensed (royalty-free for end-use) | HumanIK-compatible (~50+ bones; FBX) | Auto-mapped via HumanIK; Blender needs bone-map; Unreal/Unity native | 4,500+ motions; deep locomotion library | Strong for hero/secondary; **risk**: license complexity per item; commercial use allowed but check each asset |
| **UAL — Universal Animation Library** (Quaternius) | CC0 | 53-bone universal humanoid rig (UE5/Godot/Unity/Blender native) | Already the kit standard per SKILL.md; bgyss retarget profile schema compatible | 120+ (v1) + 130+ (v2 = 250+ total) locomotion/idle/combat clips | **Best default for kit**: CC0, redistribute freely, 53 bones sufficient for crowd-grade motion |
| **Auto-Rig Pro** (Chumbucket Studio) | Commercial (~$40) | Proprietary "ARP" rig (also exports to UE/Unity/Maya FBX) | Best-in-class "Remap" operator for any custom rig → ARP; retargets Mixamo/Mocap cleanly | n/a (rig tool, not clip lib) | Recommend purchasing for hero-rig retargeting; for crowd-tier, a one-shot bone-map table is enough |
| **Mixamo Auto-Retargetor** | Commercial (Blender add-on) | Mixamo-only | Mixamo clip → custom rig auto-retarget | n/a | Niche; superseded by Auto-Rig Pro |
| **Cadnav / Sketchfab / Poly Haven characters** | Mixed (CC0 / CC-BY / editorial) | Per-asset; inconsistent | Manual bone-map per asset; one-off scripts | Per-asset | Useful for variety (a few "named" NPCs); not scalable for crowds |
| **CMU Mocap** (Carnegie Mellon) | Free for research/commercial (with attribution) | CMU ASF/AMC format; ~38 bones | bgyss wrote `m6_cmu_motion_ingest.py`; rejected at 3,587 joint-limit violations | ~2,500 clips, huge locomotion coverage | **High value but needs validation pipeline**; bgyss's M6 rejection is a cautionary data point |
| **Universal Base Characters** (Quaternius) | CC0 | Same 53-bone UAL rig | Same as UAL; one rig for all chars | n/a (characters only) | Pairs with UAL; 20 hairstyles + clothing variants for crowd diversity |

**Recommendation**: standardize on **UAL 53-bone rig** for crowd-tier
agents (CC0, redistributable); use Auto-Rig Pro for hero-tier (3 survivors +
HeroZed). For animation, use UAL clips as baseline locomotion; optionally
augment with vetted CMU clips via a `m6_cmu_motion_ingest.py`-style validator.

---

## 7. Top 3 architectural recommendations

1. **Adopt the bgyss/Blender-Crowd architecture as the reference, adapted
   for the kit's 4 GB container.** Specifically: (a) authoring in Blender
   Python, (b) authoritative sim state in NumPy SoA arrays (not per-agent
   Python objects — the existing `crowd_agents.py` per-agent loop is wrong
   for ≥500 agents), (c) fixed-step 30Hz sim tick decoupled from render
   frame rate, (d) versioned chunked cache (binary transforms + JSON
   manifest) as bake output, (e) Geometry Nodes for cache visualization
   only. Borrow bgyss JSON schemas (brain, perception, activity, formation,
   override-layer, retarget-profile) — they are battle-tested. **For the 4 GB
   RAM constraint**: target ≤1K active sim agents at 30Hz in pure
   Python+NumPy; defer 10K+ scale to a future Rust core (the bgyss path).

2. **Use Recast & Detour (vendored C++ via PyO3/cffi) for navmesh + A* +
   corridor + ORCA-based DetourCrowd for local avoidance; layer Context
   Steering (Fray 2013/2015) on top for agent decisions.** Recast is the
   only mature OSS industry-standard navmesh library; DetourCrowd gives
   ORCA-based avoidance for free. Context steering produces the preferred
   velocity that ORCA consumes — clean separation. Avoid reimplementing
   ORCA in pure Python (bgyss did it in Rust; RVO2 reference impl is
   canonical C++). For ≤1K agents, a NumPy ORCA reimplementation is a
   feasible fallback if the C++ shim can't be built.

3. **Generate locomotion from a small clip library + state-machine + blend
   tree, NOT procedural shape-keys.** Adopt the Houdini State + Trigger +
   Transition-Graph pattern (also bgyss §7): per-agent locomotion state
   (idle/walk-start/walk-loop/walk-stop/turn/jog) → clip graph → 1D/2D blend
   tree keyed on speed & turn rate → retargeted onto the UAL 53-bone rig.
   Drop `add_shape_keys` (zombie-specific, mesh-geometry-specific).
   Foot-planting + terrain adaptation via IK constraint (Houdini pattern).
   For hero-tier, allow ragdoll handoff (bgyss M6 physics-transition
   schema; iCrowds 2.0 ragdoll pattern).

---

## 8. Open questions for the orchestrator

1. **Can the 4 GB container build Recast & Detour from source via PyO3?**
   Unverified. Alternative: pre-build wheels and vendor. If neither works,
   fall back to pure-Python/NumPy ORCA + grid A* (existing hash grid scales to
   ~1K agents).
2. **bgyss schemas as hard dependency or inspiration?** Borrowing verbatim
   gets free interop with bgyss; borrowing *patterns* keeps us decoupled.
   Recommend: patterns, define our own v1 schemas (bgyss v1/v2 migration
   history warns against premature schema lock-in).
3. **Golaem Apache-2.0 audit**: high-value reading but Maya/Houdini-bound;
   layout tool and agent representation are most directly portable.
4. **CMU mocap**: bgyss rejected CMU at 3,587 joint-limit violations.
   Adopt their `m6_cmu_motion_ingest.py` validator as a gate, or skip CMU
   entirely and rely on UAL + ActorCore?
5. **Unity DOTS-style archetype dispatch** implies NumPy SoA + archetype
   hashes — non-trivial. For ≤1K agents a flat SoA buffer is enough;
   archetypes pay off only above ~5K. Defer until scale beyond previz.
6. **Ragdoll handoff**: iCrowds 2.0 + bgyss M6 + Houdini converge on
   "state transition → RB sim → cache" — generalize the kit's existing
   RB_FALLS/RB_KD + bpy.ops.ptcache.bake_all pattern into the new system, or
   keep as a separate scenario plugin per CROWD-AUDIT-1?
7. **Fuzzy-logic perception**: defer to M6+ per bgyss, or include a
   minimal fuzzy-node in v1 behavior graph?
8. **GPU continuous-flow tier (Lombardo 2024)**: out of scope for 4 GB
   no-GPU container — confirm orchestrator agrees upper bound is "CPU bake
   at 30Hz for ≤1K hero agents + ≤10K LOD-impostor background".

---

## Sources

- bgyss/Blender-Crowd: <https://github.com/bgyss/Blender-Crowd> — cloned, README + `docs/blender-crowd-1.0.md` + `docs/crowd-simulation-research-2026.md` + Cargo.toml + nav/avoidance source inspected
- iCrowds: <https://superhivemarket.com/products/icrowds/>; cgchannel coverage Mar 12, 2026
- CrowdMaster: blenderartists.org v1.1.0 (2016), blendernation v1.3.2 (2017)
- Recast & Detour: <https://github.com/recastnavigation/recastnavigation> (7.9k★, Feb 2026)
- Python-RVO2: <https://github.com/mit-acl/Python-RVO2>; RVO2 ref: <https://gamma.cs.unc.edu/RVO2/>
- ORCA: <https://gamma.cs.unc.edu/ORCA/> (van den Berg 2011); RVO: <https://gamma.cs.unc.edu/RVO/> (2008)
- Continuum Crowds: <https://grail.cs.washington.edu/projects/crowd-flows/continuum-crowds.pdf> (Treuille 2006)
- Social Force Model: <https://arxiv.org/abs/cond-mat/9805244> (Helbing & Molnár 1995)
- HPA*: Botea, Müller, Schaeffer 2004 J. Game Dev 1(1):7–28
- Boids: Reynolds 1987 SIGGRAPH; Steering Behaviors: <https://www.red3d.com/cwr/steer/> (Reynolds 1999 GDC)
- Context Steering: <https://andrewfray.wordpress.com/2013/05/15/context-behaviours-digest/> (Fray 2013; GDC 2015)
- SteerSuite: <https://github.com/SteerSuite/SteerLite>; JuPedSim: arxiv 1907.09520 (2019)
- Massive: <https://en.wikipedia.org/wiki/MASSIVE_(software)>; Golaem: <https://www.cgchannel.com/> Aug 3, 2026
- Houdini Crowds: <https://www.sidefx.com/docs/houdini/crowds/index.html>
- UE5 Mass Entity: <https://dev.epicgames.com>; Unity Megacity Metro: <https://github.com/Unity-Technologies/megacity-metro>
- Mixamo: charios.com 2026; AccuRIG/ActorCore: <https://www.reallusion.com>
- UAL: <https://quaternius.com/packs/universalanimationlibrary.html>; LOD survey: Beacco Porres 2016, <https://upcommons.upc.edu>
