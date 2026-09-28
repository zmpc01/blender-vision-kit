# SKILL.md — Meta-Agent Notes (for working ON the kit)

> For the orchestrating/meta-agent developing, maintaining, or extending
> the kit. If you're a CONSUMER agent making scenes, read **AGENTS.md**.
>
> This is NOT a worklog, NOT a plan tracker. It is the **distilled,
> generalized meta-knowledge** of working on this kit.

## Design philosophy

The kit uses the **hybrid architecture** (3D-Agent, DD3M, Scenethesis):
agent emits JSON patch or bpy script → blrun.sh → Blender → viewport/screenshot
→ VLM critiques → agent iterates. The iteration loop — how fast the
agent can act, see, and correct — matters more than the raw API surface.

## Core principles (internalize these)

1. **The perceive→reason→act→verify loop is the product.** Every feature
   must serve it: faster mutations, faster visualization, or more accurate
   VLM verification. Don't add features that don't serve the loop.
2. **Workbench is the fast-iteration default** (~0.2s/frame, no shader
   compile). EEVEE is 2-5s warm / 28s cold. Cycles is ~50s/frame. Use
   Workbench for "did this op look right?", EEVEE/Cycles for final.
3. **The schema layer is the agent's mental model.** Agents reason over
   `scene_schema.py` JSON, not raw bpy code. New scene elements must
   appear in the schema export.
4. **Patches avoid full rebuilds.** A small JSON patch (~2s) beats
   re-running build_scene+animate+render (~10-30s). Follow the
   handler-function + MUTATIONS-dict pattern for new ops.
5. **VLMs can't process video** — keyframe contact sheets are the
   canonical workaround. Sample N frames, stitch into a grid with labels.
6. **Multi-angle viewport capture catches spatial issues** —
   front/side/top/persp gives VLM the context to spot floating/intersecting
   objects that single-angle renders hide.
7. **Blender's bundled Python is isolated** — ignores PYTHONPATH (use
   `--python-use-system-env`), no Pillow by default (install.sh pip-installs
   it), no numpy/scipy. When adding Python deps, update install.sh.
8. **EEVEE needs three things**: Xvfb+GLX, libEGL.so.1 in LD_LIBRARY_PATH,
   shader cache warmed. Cycles needs none of these.
9. **Blender 4.x API drift is real** — Principled BSDF renamed in 4.0,
   EEVEE rewritten in 4.2, action.fcurves moved in 5.x. Always use
   `blender_kit._safe_set()` / `iter_fcurves()` / `ensure_use_nodes()` /
   `normalize_engine_id()` — never reach for raw version-specific attrs.
10. **VLMs have blind spots** — catch visible issues but miss geometric
    ones if the camera angle hides them. Defense-in-depth: multi-angle
    captures + close-up prompts + `validate_scene.py` (deterministic bbox
    checks). VLMs are reliable for composition/color, unreliable for
    precise geometry.
11. **VLM noise vs reality** — VLMs flag issues that don't exist (e.g.
    "floating zombie" when grounded at z=0). Always verify geometric
    claims programmatically before acting.
12. **Workbench MATERIAL color_type** (not OBJECT) — OBJECT shows flat
    gray, hiding material color coding. Kit defaults to MATERIAL.
13. **AgX crushes previz colors** — force `view_transform='Standard'`
    for previz/workbench. Use AgX only for final Cycles renders.
14. **Pillow must install to bundled site-packages** (not `--user`) —
    blrun.sh overrides HOME; `--user` goes to wrong location.
15. **Sub-agents time out on giant briefs** — one asset module per
    sub-agent, tight spec, <5 min each. On timeout, harvest artifacts
    (80% may be on disk). Orchestrator assembles + does master animation.
16. **`<model-viewer>` struggles with large scenes** (>100 objects) —
    SSE streaming + sidebar still work. Three.js variant needed for
    complex scenes (planned).
17. **Placement tooling** (`placement_lib.py`) — mm-exact contact states
    (PENETRATING/TOUCHING/CLEAR/NESTED/CROSSING via BVH face pairs + signed
    inside + segment-triangle crossing). One-shot placement solvers
    (place_on/seat_at/snap_z). Regression suites in `tests/`. If you touch
    BVH/contact code: bmesh normals stale after `bm.transform()` →
    `bm.normal_update()` first; float32 jitter (~60nm) needs tolerance
    guards; coplanar contact yields overlap face-pairs (pairs>0 ≠
    penetration — pair with inside-vert count + crossing test).

## Architectural decisions (don't revisit without strong reason)

| Decision | Rationale | Cost |
|----------|-----------|------|
| Direct `bpy`, NOT Blender MCP | More capable, lower latency for Python agents | Lose blender-mcp ecosystem |
| glTF (.glb) for web preview | Canonical web 3D format, `<model-viewer>` ~25 lines | Loses AREA lights, modifiers, procedural shaders |
| JSON scene schema (NOT glTF-as-schema) | Blender-aware, query/patch-friendly | Two formats to maintain |
| JSON patch protocol (NOT Python eval) | Safer, inspectable, composable | New ops need handler functions |
| Workbench as fast-iter engine | ~0.2s/frame, no shader compile | No PBR materials |
| **Ship 5.2 LTS default, keep 4.x compat shim** | 5.2 LTS until July 2028; shim handles all breaks | ~80 lines shim, zero agent-facing change |

## The 5.x compat shim (in `blender_kit/__init__.py`)

- `EEVEE_ENGINE_ID`: auto-resolves to `BLENDER_EEVEE_NEXT` (4.x) or `BLENDER_EEVEE` (5.x)
- `normalize_engine_id()`: accepts any spelling + typos → correct id
- `iter_fcurves(action)`: 4.x `action.fcurves` ↔ 5.x `action.layers[0].strips[0].channelbag(slot).fcurves`
- `ensure_use_nodes()`: 4.x sets True; 5.x no-op (auto-created)
- `add_sky_world()`: NISHITA (4.x) ↔ MULTIPLE_SCATTERING (5.x)
- `supports_headless_gpu()`: True if `gpu.init()` available (5.2+) — but crashes on llvmpipe, Xvfb still required

A/B verified on 4.2.9 + 5.2.2: same scene renders unchanged on both.

## When extending the kit

**New scene script**: copy `scene_template.py` → edit `build_scene()` (return context dict) → edit `animate(ctx, ...)` → test with `--dry-run` first.

**New mutation op**: write `_apply_<op>(obj, params)` → register in MUTATIONS dict: `"<op>": (_apply_<op>, needs_obj)` → `needs_obj=True` if targeting an object, `False` for scene-level ops → test with patch JSON.

**New helper**: add to `blender_kit/__init__.py` → use `_safe_set()` for version-specific attrs → don't duplicate bpy.ops — wrap in context-handling helpers.

**New viewer**: self-contained HTML in `viewer/` → load .glb + metadata.json from same dir → unpkg CDN for libraries.

## Git workflow (GIT IS THE DISK)

- **Repo**: github.com/zmpc01/blender-agent-kit (primary)
- **Mirror**: gitlab.com/ansgareutychisO/blender-agent-kit (backup)
- **Push to BOTH on every micro-step** — GitLab WAF blocks ~1/3 of pushes;
  retry up to 8× with 5s sleep. Use `oauth2:TOKEN` format for GitLab.
- **NEVER force push** — local disk unreliable; force push can wipe the
  only copy. If local diverges, investigate before pushing.
- **Work on main branch only** — watchdog reverts non-main branches.
- **Rebase before every push** — a parallel session may have pushed.
- **After any merge**: `grep -rn "<<<<<<<" scripts/` + smoke-test one blrun
  invocation BEFORE relaunching long renders.

## When to delegate to sub-agents

| Task | Delegate? | Why |
|------|-----------|-----|
| Research (web search + summarize) | YES | Fresh context, dedicated focus |
| Code review / audits | YES | Catch issues orchestrator misses |
| Scene building | MAYBE | VLM-verify output; don't blindly trust |
| Well-specified implementation | YES | If spec is detailed enough |
| Decisions needing full context | NO | Sub-agents don't see history |
| Skill compliance tasks | NO | Sub-agents miss skill instructions |

## Common meta-agent mistakes

1. **Calling blender without blrun.sh** — `import blender_kit` fails (no PYTHONPATH). Always go through blrun.sh.
2. **Not warming EEVEE shader cache** — first render is 28s. `blrun.sh --warm-cache` once per container.
3. **Editing in `/home/z/my-project/`** — watchdog reverts every 20s. Work in `/home/z/blender-kit/`.
4. **Setting EEVEE attrs that don't exist** — `use_bloom` removed in 4.2+. Use `_safe_set()`.
5. **Not cleaning up temp cameras** — `viewport_capture.py` temp cameras accumulate. Use `_cleanup_temp_camera()`.
6. **Not validating render output** — EEVEE shader failures produce 0-byte PNGs with exit 0. Always `_validate_outputs()`.
7. **Writing contact sheets without Pillow** — Pillow not in bundled Python by default. install.sh pip-installs it.
8. **Forgetting `--python-use-system-env`** — if you must call blender directly (debugging), add this flag.
9. **Not exercising every gate path** — a gate that only runs at render time passes every dry-run. Always run one full pipeline pass (dry-run + render + encode + export) before shipping.
10. **Letting advisory gates stay advisory** — a gate that can't abort the build protects nothing. Flip to fail-closed the round you add it.

## Verification discipline

- **Design-audit gate BEFORE implementation** — write spec with decision IDs, hand to FRESH agent with implementing files + mandate to attack, apply required changes before coding. Catches semantic collisions code review misses.
- **Calibrate thresholds, don't guess** — measure the corpus, pick the separating statistic (dark-FRACTION beat mean-luma, strong-edge FRACTION beat mean-sobel). ±20% brightness and 2x downscale must not flip any fired rule.
- **Gates must travel with the retimed code** — every hardcoded frame in a gate is a stale-gate risk when the timeline changes. Re-derive from source tables, not hardcoded counts.
- **Test every gate on KNOWN-BAD input** — a gate reading the wrong JSON keys returns "all pass" on garbage.
- **Fixtures carrying ground truth must SELF-VERIFY** — planted bugs in fixtures make subjects report honest tool output while you debug the wrong layer. `_check(tag, measured, planted)` at build time.
- **Fresh-process-wins arbitration** — when in-process audit contradicts fresh-process schema/gate on the same file, the fresh process is right. Then hunt cache staleness.
- **A verifier must never repair** — gate raising ValueError on repair params is what makes its PASS meaningful.

## Vision + numbers division

- **Plain renders are undecidable** for vision agents at scene scale (12mm penetration, 30mm float undecidable; 55mm float readable).
- **Purpose-built encodings flip decidability** — heat maps, section pairs, ASCII vision packs.
- **Vision triages WHERE; numbers decide WHAT; never blend the two roles.**
- **ASCII vision packs** (`scripts/ascii_vision.py`): pack-first for geometry/grounding/count/layout; VLM for semantics/hue/gist/aesthetics. Disagreement = automatic programmatic probe (failure modes are opposite: false-accept vs false-reject).

## Physics layer (bullet-in-Blender headless)

Five measured laws (all verified via probes in `experiments/physics_facts/`):
1. **No `world_step` in 4.5** — sims advance via `scene.frame_set()`. Point cache SURVIVES object teardown → always `frame_set(1)` before every sim.
2. **Sim pose lives only in `matrix_world`** — RNA location keeps spawn pose. Commit: capture matrix_world → remove rb → write matrices → update → clear_bvh_cache.
3. **Collision shapes snapshot evaluated mesh at rb_add** — unapplied scale = pass-through. BOX tracks live bbox (safe for origin-centered); CONVEX_HULL is faithful; MESH pass-throughs thin shells (never use).
4. **Bullet depenetrates flat contacts to exact rest** but ejects wedged overlaps sideways — refuse-by-default, record explicit repairs.
5. **Margin pop ≈ SUM of contacting bodies' margins** (hull-hull ~2× margin, hull-primitive ~1×, primitive-primitive ~0). BOX-BOX rests exact. Guarded snap closes the residual.

**Treadmill law** (belt streams, subject world-static): world-static + visible = paces the subject ("rider"). Compose with the belt or hide. Large belt deco crosses static cameras at `dist(t) == y_belt`.

## Output organization

```
output/<scene_name>/
├── frame_0001.png ... frame_0024.png   # animation
├── still_0001.png                       # single-frame still (if --still)
├── anim.mp4                             # encoded (if --encode-mp4)
├── metadata.json                        # render provenance + scene summary
├── <scene_name>.glb                     # glTF export
├── grid.png                             # multi-angle viewport contact sheet
├── motion.png                           # keyframe contact sheet
└── scene.json                           # structured scene schema
```

For user delivery: copy whole dir to `/home/z/my-project/download/<scene_name>/` + `viewer/index.html`.

## Deliverables need three durability layers

1. **Git blobs** — force-add through gitignore, tag the commit
2. **GitHub Release** — create release, attach MP4s via `uploads.github.com` API (not `api.github.com` — returns 404 for uploads)
3. **`/home/sync` rsync** — backup after every milestone (but not durable across sessions — only GitHub/GitLab are)

## Environment constraints

- **4GB RAM, no GPU** — all CPU rendering via llvmpipe + Xvfb. EEVEE peaks at 1.6GB for 273 objects; use Workbench/Cycles for complex scenes.
- **No root** — install.sh extracts .deb files locally for libEGL.
- **Background processes die between tool calls** — long ops must run inside one Bash call with timeout, or use `render_daemon.py` (double-fork to PID 1).
- **Watchdog** reverts `/home/z/my-project/` every ~20s — work in `/home/z/blender-kit/`.

## KB entries (niche but valuable, linked from AGENTS.md)

- `/kb/placement_and_physics.md` — full placement_lib + physics_place reference
  **Headlines**: 7 placement ops (move_to/place_on/seat_at/snap_z/physics_settle/
  physics_place/physics_oracle/physics_gate); audit pair states (PENETRATING/
  TOUCHING/NESTED/CLEAR); audit only sees pairs within 100mm pad (use physics_gate
  for scene-wide floating); physics hard limits (concave receivers need compound
  shapes, BOX collision centered on ORIGIN not bbox, hull-hull rest ≈Σmargins,
  RB point cache survives teardown → always frame_set(1)).
- `/kb/rigged_characters.md` — capsule vs rigged, UAL hero-swap, rig debugging
  **Headlines**: capsule actors are the previz standard (v2 rigged attempt
  failed: skin weights broken, action slots, NLA stashes, basis-matrix collapse);
  10 rig gotchas if you go rigged (bind pose ≠ standing, quaternion axis
  conventions, action-slot law `ad.action_slot = act.slots[0]`); UAL (Quaternius
  CC0) vetted hero-swap: 42/46 actions animate, drift 0.000m.
- `/kb/ascii_vision.md` — ASCII vision pack protocol, scorecard, param rules
  **Headlines**: pack-first for geometry/grounding/count, VLM for semantics/hue;
  ASCII WINS dark/monochrome (+0.32), tiny <2% objects (+0.12); R4 decisive:
  pack found planted floater at exact coords, fabricated nothing; VLM
  hallucinated floats on grounded actors. Disagreement = automatic probe.
- `/kb/render_speed.md` — engine benchmarks, AA/cavity tradeoffs, cold-start cost
  **Headlines**: AA = 92% of Workbench wall time (OFF is 5-6× faster); cold
  start ~2.5 min dominates batch renders; EEVEE peaks 1.6GB for 273 objects
  (Cycles stable ~355MB); JPEG q85 15× smaller than PNG; re-profile after
  every speedup (bottleneck moves).
- `/kb/glTF_export.md` — export flags, three.js loader quirks, USD decision
  **Headlines**: `export_cameras` defaults False (kit sets it); ACTIONS mode
  doesn't bake constraints (TRACK_TO exports raw euler); three.js sanitizes
  node names (dots removed); `mixer.setTime` breaks LoopOnce+clamp (use
  LoopRepeat with pre-padded tracks); glTF keys are TIMELINE-ABSOLUTE at
  `t=frame/fps`; three.js physical lights divide by π + glTF punctuals are
  683× Blender watts; USD rejected (USDC crashes three.js, customData invisible).

## Crowd simulation system (session 23, planning kickoff)

> Started 2026-09-25. The crowd system is a **new major subsystem** in
> the kit — a AAA-grade crowd simulation living under
> `scripts/crowd/`. Source-of-truth documents live at
> `docs/crowd_system/` (DESIGN_crowd_system_v1.md, PLAN.md, HANDOFF.md,
> CROWD_GAP_1_analysis.md) plus audit reports in `.agents/research/`.

### Distilled meta-knowledge (recurring patterns future agents will hit)

1. **The existing `crowd_agents.py` (previz) is a scenario-specific PoC,
   NOT a general crowd sim.** It has 9 zombie-specific FSM states
   (LUNGE/REACH/FLEE/FALLBEHIND/GIVEUP/STAGGER/ALERT/PURSUE/IDLE),
   a single jeep OBB, and procedural shape-key morphs. Don't try to
   refactor it into a general system — the design audit confirmed
   only its skeleton (uniform hash grid, separation force, decimated
   bake, fail-closed gate pipeline, callable goal-source contract,
   per-step `rec[]` recording) is reusable. Everything else is
   greenfield.

2. **The bgyss/Blender-Crowd repo is the reference architecture.**
   Read `/tmp/Blender-Crowd/docs/blender-crowd-1.0.md` (1,167 lines)
   BEFORE designing or implementing anything. It's a working AAA-grade
   spec (GPL-3.0, M0-M6 accepted, Rust core + Python + GN, 1K-agent
   deterministic bake). The kit's design v1.1 adapts bgyss for the
   4GB / no-GPU / Python-first container (no Rust in v1; target 1K
   agents via NumPy SoA + tier mix).

3. **BVH is a raycaster, NOT a voxelizer.** Don't claim "voxelize
   using mathutils.BVH" — BVH raycasts are for overhang/collision
   tests, not navmesh generation. Use bmesh's `bm.edges` with
   `len(link_faces) == 2` for poly adjacency (native, no kit
   dependency). The kit's `placement_lib.py` exposes contact-state
   helpers, NOT a poly-adjacency API — don't claim otherwise.

4. **R0-only rendering at 1K agents is infeasible on 4GB RAM.** 1K ×
   53 bones × 240 frames × 7 channels = 89M keyframes ≈ 5.7GB.
   R2/GN instancing is a day-1 requirement, not M2+ optimization. The
   cache drives a single GN instance group with `crowd_*` named
   attributes (per bgyss §11.3 contract).

5. **UAL has 46 actions in the vendored kit copy, not 250+.** The
   upstream Quaternius UAL v1+v2 has 250+; the kit's vendored copy
   has 46. Always reference `assets/vendor/ual/` specifically. v1
   ships a degraded state machine (idle/walk_loop/jog only); M2
   sources missing clips (walk_start, walk_stop, turn_left/right,
   arc_left/right).

6. **The v2 rigged-character failure (skin weights, NLA stashes,
   basis-matrix collapse per `kb/rigged_characters.md`) is a recurring
   trap.** v1 mitigates by: (a) forbidding new rig imports; (b)
   reusing the vetted `assets_ual_actors.py` path (42/46 actions
   animate, drift 0.000m); (c) retarget profile stays IDENTITY
   (UAL→UAL); (d) a new `keyframe_insert_compat()` shim in
   `blender_kit/__init__.py` parallel to the existing `iter_fcurves()`
   reading shim. The crowd system NEVER calls `obj.keyframe_insert()`
   directly — always through the shim. Action-slot law (`ad.action_slot
   = act.slots[0]`) is enforced in the shim, not in the caller.

7. **Cache attaches via `scene['crowd_cache_path']` custom property,
   NOT `bpy.props` registration.** `scene[key] = value` works on any
   Blender property without registration. No `bpy.props` in v1 — that
   defers to M4+ Blender panel UI work.

8. **NumPy ORCA cross-CPU determinism is NOT achievable in STRICT
   mode.** LP-solver reduction order varies across CPUs (SIMD width,
   fast-math flags). Drop the cross-CPU bitwise claim; STRICT mode
   is same-machine regression only. Cross-machine tests use 5mm
   tolerance (relaxed from 1mm). Same machine: 1mm position, 0.001
   rad orientation. This is the bgyss §9.4 hedged position, made
   explicit.

9. **`clip_phase` should be continuous time (seconds since clip start),
   NOT normalized 0..1.** Linear interp across a 0..1 wrap (phase
   0.99 → 0.01 lerps to 0.5 mid-loop — nonsense). Use seconds;
   render-time interpolation is `phase_at_render = (sim_phase +
   (frame - tick_frame) * dt * playback_rate) % loop_duration`.

10. **Behavior IR action nodes are idempotent on re-fetch; RUNNING
    state lives in `action_state: uint8` per-agent buffer.** Don't
    try to express RUNNING via instruction pointer manipulation —
    the IR stays flat, action state is in SoA. NAVIGATE checks
    `path_status`; if FOLLOWING, returns RUNNING without recomputing
    path. WAIT tracks remaining duration in `action_state`.

11. **Per-population cache invalidation, not global.** Behavior
    graph change for population P → only P's agent range
    re-simulated. Manifest tracks per-population agent ranges. The
    kit's existing per-scene invalidation pattern is wrong for
    multi-population scenes.

12. **Cache manifest needs per-chunk byte offsets + tick ranges for
    O(1) random-access seek.** 5-second chunks at 30Hz = 150 ticks
    per chunk. Without per-chunk offsets, seeking to frame 847
    requires reading all prior chunks. Manifest must include
    `chunks: [{path, tick_start, tick_end, byte_offset, byte_length}]`.

13. **Adopt the bgyss 5-subsystem pattern: CrowdCore (clock + SoA
    + events), CrowdNav (navmesh + A* + ORCA), CrowdBrain (behavior
    IR compile + runtime), CrowdMotion (clips + state machine + blend
    tree), CrowdLayout (cache + overrides + GN presentation).** The
    ownership boundaries (per DESIGN §2.1) define the future Rust
    port seams — CrowdNav and CrowdMotion hot loops are the
    candidates for native port first when v2 needs 10K+ agents.

14. **Tier mix matters for ORCA benchmarks.** 200 S0 agents × 10
    neighbors × every tick + 200 S1 × 6 neighbors × every 4th tick
    = 2300 pairs/tick vs 10000 baseline = 4.4× speedup. Always
    benchmark with the actual tier mix, not flat 1K×10. The 1K-agent
    gate depends on this — a flat benchmark will incorrectly predict
    failure.

15. **Sub-agent design audits BEFORE implementation are
    non-negotiable.** This session's CROWD-DESIGN-AUDIT-1 caught 3
    P0 blockers (broken navmesh algorithm, R0-only RAM blowup,
    undefined cache→scene seam) that would have derailed M0
    implementation. The audit pattern: write design with decision
    IDs (D1-D10), hand to FRESH sub-agent with mandate to attack,
    apply required changes before coding. 4 P0s + 9 P1s + 11 P2s
    found = ~25 issues the orchestrator missed.

16. **GitLab WAF is consistently blocking HK-based IPs (~100% block
    rate observed this session, not the documented ~1/3).** Don't
    rely on GitLab as primary backup. GitHub is the source of truth.
    Run background retry loop with 30 attempts × 30s sleep, but
    accept it may never succeed. The user explicitly said "at least
    one remote should allow you to back up" — GitHub is that remote.

### Where to look for crowd-system artifacts

- Design doc (v1.1): `docs/crowd_system/DESIGN_crowd_system_v1.md` (1,263 lines)
- Design addendum (v1.2 — FALLBACK): `docs/crowd_system/DESIGN_crowd_system_v1.2_addendum.md`
  (3,913 words — absorption strategy; kept as contingency if Rust build fails)
- Design addendum (v1.3 — CURRENT): `docs/crowd_system/DESIGN_crowd_system_v1.3_addendum.md`
  (3,700 words — vendor bgyss wholesale strategy; SUPERSEDES v1.2 §0)
- Long-horizon roadmap: `docs/crowd_system/PLAN.md`
- Immediate next-session scope: `docs/crowd_system/HANDOFF.md`
- Gap analysis: `docs/crowd_system/CROWD_GAP_1_analysis.md`
- Audit reports: `.agents/research/CROWD_AUDIT_1_report.md` (existing
  system), `.agents/research/CROWD_RESEARCH_EXT_1_report.md`
  (initial 10-repo external survey), `.agents/research/CROWD_DESIGN_AUDIT_1_report.md`
  (design v1.0→v1.1 audit), `.agents/research/CROWD_FIELDS_AUDIT_1_report.md`
  (deep audit of existing crowd_fields engine),
  `.agents/research/CROWD_GH_SCAN_1_report.md` (comprehensive GitHub
  API scan — 1053 repos → 50 in final table)
- bgyss reference: `/tmp/Blender-Crowd/docs/blender-crowd-1.0.md`
  (1,167 lines) + `/tmp/Blender-Crowd/schemas/*.json` (27 schemas,
  1,897 LOC) — may need re-clone if /tmp wiped
- Existing engine (for reference, NOT to refactor):
  `/home/sync/blender-escape-previz/scripts/crowd_agents.py` (756 LOC)
- Existing kit primitives (absorb, do NOT reinvent):
  `/home/sync/blender-agent-kit/scripts/crowd_fields.py` (387 LOC) +
  `scripts/test_crowd_fields.py` (150 LOC) + `kb/crowd_fields.md`
- Existing scenario plugin (REFERENCE only):
  `/home/sync/blender-agent-kit/scripts/blender_kit/prop_carry.py` (227 LOC) +
  `kb/prop_carry.md`

## Crowd simulation system v1.2 (session 24 — absorption strategy)

> The user directed: "leave no stones unturned" (comprehensive GitHub
> API scan, not done in session 23) + "leverage what has been validated
> so we don't throw away those learning" (reconsider absorb-vs-handroll
> for the existing crowd_fields engine). v1.2 documents the absorption
> strategy; v1.1 sections unchanged unless explicitly amended by
> `DESIGN_crowd_system_v1.2_addendum.md`.

### Distilled meta-knowledge (recurring patterns future agents will hit)

17. **`git fetch --all` BEFORE designing.** The session-23 mistake:
    designed v1 without fetching gitlab/main, assuming github/main was
    the source of truth. The parallel workstream had already implemented
    `scripts/crowd_fields.py` (387 LOC) — 30% of the v1.1 design was
    redundant. At session start, always run
    `git fetch --all && git log --all --oneline | head -20` to see all
    branches' state on both remotes.

18. **Don't write your own ORCA solver.** `sybrenstuvel/Python-RVO2`
    (242★, Apache-2.0, Cython over RVO2 C++, GIL-released `doStep()`)
    is the canonical Python ORCA binding. CROWD-RESEARCH-EXT-1 missed
    it (cited only the 14★ `mit-acl` fork); CROWD-GH-SCAN-1 surfaced
    it. v1.2 ABSORBS Python-RVO2 as direct runtime dep. Fallback if
    Cython build fails in 4GB container: NumPy port of `Muon/pyorca`
    algorithm (MIT, 36★, pure-Python, 2D only — needs 3D LP fallback
    added).

19. **`crowd_fields` engine is COMPLEMENTARY, not alternative, to ORCA.**
    `crowd_fields.relax()` is vectorized Jacobi PBD (Position-Based
    Dynamics) — handles HARD penetration constraints (post-collision
    cleanup). ORCA is velocity-based avoidance (pre-collision smooth
    flow). v1.2 §6.3 uses BOTH: ORCA produces new velocities →
    integrate positions → `relax()` cleans residual 1-5mm overlaps.
    This is the Position-Based crowds algorithm (Weiss 2019, MIG) —
    cite it in design v1.2 §6.3.2.

20. **Comprehensive GitHub API scan is feasible and worth it.** 20
    queries × 5 pages × 100 results = up to 10,000 repos scanned in
    ~30 minutes (PAT-authenticated, 30 req/min search limit + 5000
    req/hr core). CROWD-GH-SCAN-1 scanned 1,053 unique repos, surfaced
    50 in final table. Yielded 4 NEW discoveries that materially
    changed v1.2 design (Python-RVO2, dodgy, navcat, PedPy). Always
    do exhaustive GitHub API scan BEFORE designing — not just curated
    surveys.

21. **bgyss absorption is HYBRID, never vendor.** bgyss/Blender-Crowd
    is GPL-3.0+. Vendoring CODE contaminates the kit's license.
    Borrowing ARCHITECTURE (5-subsystem decomposition, stable-identity
    contract, tier-mix gate, cache-boundary discipline) is fine —
    ideas are not copyrightable. Borrowing SCHEMA NAMES + structure
    is fine (redefine under kit's license). Borrowing the 27 JSON
    schemas verbatim is NOT fine — write our own v1 schemas using
    bgyss as reference. When the kit eventually adds a Rust core
    (M5+), use `andriyDev/dodgy` (MIT/Apache) for ORCA — NOT bgyss's
    GPL ORCA.

22. **The "absorb vs handroll" decision is per-primitive, not per-system.**
    v1.2 §0.1 has the full absorption matrix. ABSORB: ORCA (Python-RVO2),
    force fields (crowd_fields.FieldSpec), PBD cleanup (crowd_fields.relax),
    temporal envelopes (crowd_fields.ramp_env/decay_env/event_env),
    playback rate (crowd_fields.playback_rate), validation metrics (PedPy),
    UAL rig path (existing assets_ual_actors.py). WRAP: FieldSpec ←
    Blender obj `center_fn` resolution, `dominant_attractor` ← per-agent
    argmax, `advance_phase` ← `advance_phase_secs` for seconds-based
    phase. HANDROLL: navmesh (bmesh walk + Hertel-Mehlhorn), A* + funnel,
    behavior graph IR (10 nodes), cache binary chunk layout, cache→scene
    attachment, keyframe_insert_compat() writing shim, GN instance group,
    animation state machine, foot IK (M3+). REFERENCE: DotRecast C#
    source for navmesh algorithm, bgyss JSON schemas for cache format
    patterns, prop_carry as scenario plugin.

23. **Effort savings from absorption are real.** v1.2 saves ~3-4
    sessions (~25-30%) vs v1.1 handroll-everything, by absorbing
    Python-RVO2 (~1 session saved on ORCA), crowd_fields primitives
    (~1 session saved on force fields + relax + gait phase), PedPy
    (~0.5 session saved on validation), and DotRecast reference
    (~0.5 session saved on navmesh algorithm study).

24. **Existing `crowd_agents.py` (previz, 756 LOC) fate: DEPRECATE
    primitives, PORT zombie FSM as M2 regression test.** The
    primitives (uniform hash grid, separation force, gait phase) are
    REDUNDANT with `crowd_fields.py` — different APIs, different math
    (soft-force vs PBD; time-driven vs displacement-driven phase).
    Coexistence creates maintenance burden. The 9-state zombie FSM
    (LUNGE/REACH/FLEE/etc.) is scenario-specific but valuable as a
    regression test. v1.2 M2 ports the zombie FSM as a behavior-graph
    plugin that USES `crowd_fields` primitives — proves the general
    system on a hard case (pursuit, hard penetration, dynamic
    obstacles, hero OBB keepout).

25. **`prop_carry` is a SCENARIO PLUGIN, not a crowd primitive.**
    `scripts/blender_kit/prop_carry.py` (227 LOC, law 110) anchors a
    prop to an agent's bone across frames. It is NOT a crowd-sim
    concern — it's a Blender-side module. v1.2 §11.5 references it
    for crowd shots where agents carry props (rifles, bags, tools),
    but the crowd system does NOT call `prop_carry` directly. The
    scenario plugin calls it after `bake.apply_to_scene()` writes
    keyframes to the agent's armature.

26. **`iter_all_fcurves()` (law 111, parallel workstream) is the
    reading-side complement to the design's `keyframe_insert_compat()`
    writing shim.** The parallel workstream added it for 5.2 multi-slot
    actions (Key-datablock shape fcurves hidden from slot[0]-only
    iter). The crowd system uses BOTH: `iter_all_fcurves` when reading
    existing animation (UAL clip import, cache reading),
    `keyframe_insert_compat` when writing new animation (bake
    application). Never call `obj.keyframe_insert()` or iterate
    `action.fcurves` directly.

27. **Rust core decision: DEFER to M5+, conditional on 1K gate
    failure.** v1 target is 1K agents at 30Hz in pure Python+NumPy.
    With Python-RVO2 (Cython) + crowd_fields.relax (PBD post-pass),
    33ms/tick FAST is feasible — no Rust needed. A Rust core adds
    2-3 weeks of build-chain setup (PyO3, maturin, platform wheels for
    Blender 4.5/5.2 × Python 3.11/3.13). When added (M5+), use
    `andriyDev/dodgy` (MIT/Apache) for ORCA — NOT bgyss's GPL ORCA.

28. **The kit's planned crowd system has minimal OSS competition in
    the Blender-specific niche.** CROWD-GH-SCAN-1 identified 11 NEW
    Blender-crowd repos (vs EXT-1's 4: bgyss, CrowdMaster, iCrowds,
    Agents-GN), but all are abandoned, amateur, closed-source-commercial,
    or tangential. bgyss remains the only serious OSS Blender crowd
    project. This means the kit's v1 has clear greenfield space —
    and bgyss's GPL means we can't vendor it, but we can out-compete
    it on permissive licensing.

29. **Blender-crowd OSS scan is genuinely sparse.** Of the 1,053 repos
    CROWD-GH-SCAN-1 scanned, only ~50 are relevant to crowd simulation
    broadly, and only bgyss is Blender-specific and serious. The
    algorithmic primitives (ORCA, RVO, navmesh, PBD, context steering)
    are all available as permissively-licensed OSS in C++/C#/Rust/Python,
    but NOT as Blender-ready integrations. The kit's value-add is the
    Blender integration, not the algorithm invention.

## Crowd simulation system v1.3 (session 25 — vendor bgyss wholesale)

> The user directed: "this is internal project kit i don't see why we
> can't use GPL also don't struggle too hard on the cython build if
> you need bigger compute i can figure out something but now you
> should try (if this is still the right path though) i prefer we just
> take the source directly if it is usable". Two shifts: (a) GPL is
> now OK (internal kit, not redistributed); (b) prefer vendoring
> source over pip install; bigger compute available if needed.
> CROWD-BGYSS-CODE-AUDIT-1 confirmed bgyss code is directly vendorable.
> v1.3 SUPERSEDES v1.2 §0 absorption matrix with vendor-bgyss-wholesale.

### Distilled meta-knowledge (recurring patterns future agents will hit)

30. **GPL is OK for the internal kit.** The user explicitly approved:
    "this is internal project kit i don't see why we can't use GPL".
    The v1.2 GPL contamination firewall was overblown. Vendor GPL code
    directly into `vendor/` when it's the right engineering choice.
    The kit is NOT redistributed as a permissively-licensed product;
    it's an internal tool. Mixed license tree (permissive kit +
    GPL `vendor/` subdir) is standard practice.

31. **bgyss/Blender-Crowd code is directly vendorable, not just
    reference.** CROWD-BGYSS-CODE-AUDIT-1 read the actual Rust + Python
    + GN code (not just docs) and confirmed: cross-platform Linux
    (cfg blocks exist; sim kernel platform-neutral), zero-GPU (only
    cpu_reference implemented), 5 Rust deps only (blake3, crc32c,
    serde, serde_json, pyo3), 1K-agent gate has 27× perf headroom
    (12.2s for 1K × 10K ticks; 424MB peak Blender; 7.86MB native at
    10K agents), M0-M6 milestones accepted (code is tested + proven).
    The Python add-on CANNOT be vendored without the Rust core — it's
    all-or-nothing (every operator imports `blender_crowd_native`).

32. **The single biggest blocker to vendoring bgyss is the Rust build
    chain, not the code.** bgyss ships macOS arm64 wheel only
    (`blender_manifest.toml:13-14`). The kit runs Linux x86_64. Need
    to build the Linux wheel via `maturin develop --release` (PyO3
    abi3-py311 for Blender 4.5 Python 3.11, or abi3-py313 for
    Blender 5.2 Python 3.13). 30-min spike: `cargo build --release
    -p crowd-blender`. If red after 1 hour → escalate to user for
    bigger compute (user offered). If bigger compute doesn't help →
    fall back to v1.2 (Python-RVO2 + handroll).

33. **Vendoring wholesale saves ~55% of v1 effort vs v1.2 absorption.**
    v1.3 estimate: 3-6 sessions to v1 ship (was 6-9 in v1.2, 9-13 in
    v1.1). The savings come from eliminating handroll of: navmesh,
    A* + funnel, behavior graph IR, cache binary chunk layout,
    cache→scene attachment, keyframe_insert_compat() shim, GN instance
    group, animation state machine, foot IK. bgyss has all of these,
    tested and proven.

34. **The kit's existing engines SURVIVE bgyss vendoring as
    scenario-side engines.** `scripts/crowd_fields.py` (387 LOC +
    s28 extensions) is the authoring surface for force fields —
    the kit user authors `FieldSpec` dataclasses; the adapter
    converts them to bgyss's `AvoidanceInput.preferred` per-tick.
    `scripts/gait_modifiers.py` (497 LOC, s28) authors gait mods;
    the adapter feeds bgyss's `crowd_proxy_swing` GN attribute.
    `scripts/blender_kit/prop_carry.py` (227 LOC, law 110) anchors
    props to agent bones — unchanged. `scripts/assets_ual_actors.py`
    is the UAL rig vetted path — unchanged. These are COMPLEMENT,
    not overlap, with bgyss.

35. **The "Zero code copied from bgyss" disclaimer must be deleted
    once bgyss is vendored.** `scripts/crowd_fields.py:36-37` currently
    says "Zero code copied from bgyss". Once bgyss is vendored into
    `vendor/blender-crowd/`, this disclaimer is FALSE. Delete it
    (or rewrite to acknowledge bgyss as the source of the crowd
    simulation primitives). Per D21.

36. **The single integration point is `scripts/crowd/kit_project_ir.py`.**
    The kit's user-facing API stays Python dataclasses (CrowdProject,
    Population, Destination, ForceField). The adapter converts them to
    bgyss's `project_ir_v1` schema (per
    `vendor/blender-crowd/schemas/project-ir-v1.schema.json`). This
    is the SINGLE integration point — everything else is vendored
    verbatim. ~200-400 LOC of mechanical field-by-field mapping.

37. **bgyss IS the Rust core (no deferral).** v1.2 said "DEFER Rust
    to M5+" (D15). v1.3 SUPERSEDES this: bgyss IS the Rust core, and
    we vendor it NOW. The Rust build chain is the only risk; if it
    fails, we fall back to v1.2 (no Rust). But the primary path is
    Rust-from-day-1, not deferral.

38. **bgyss's 100K-agent gate needs 64GB RAM — irrelevant to v1.**
    CROWD-BGYSS-CODE-AUDIT-1 confirmed bgyss's 1K-agent gate fits in
    424MB Blender resident (10% of 4GB). The 100K gate is a marketing
    claim that needs 64GB M1 Max — out of scope for the kit's 4GB
    container. Don't be intimidated by the 100K number; v1 targets 1K.

39. **Vendor as git submodule, not flat copy, for upstream updates.**
    `git submodule add https://github.com/bgyss/Blender-Crowd.git
    vendor/blender-crowd` allows `git submodule update --remote` to
    pull bgyss upstream. Flat copy gives v1 stability without drift
    but loses upstream updates. Choose submodule unless v1 stability
    is critical. bgyss is actively developed (last commit 2026-09);
    upstream updates may bring fixes + features.

40. **bgyss Blender version compat (5.2 LTS only?) is an open risk.**
    bgyss's `blender_manifest.toml` targets 5.2 LTS. The kit supports
    4.5 + 5.2. M0.2 verifies whether bgyss's add-on works on 4.5 too,
    OR whether we need to drop 4.5 support for the crowd system, OR
    backport the add-on to 4.5. Per R15.

## Crowd simulation system v1.3 — M0 COMPLETE (session 26)

> User directive: "ok continue to next session and progress as much
> as possible". M0 Proving Grounds landed with ALL 5 tasks GREEN
> (vendor bgyss, Rust build, adapter, smoke test, 1K-agent gate).
> v1.3 vendor-bgyss-wholesale strategy is PROVEN end-to-end.

### Distilled meta-knowledge (recurring patterns future agents will hit)

41. **The Rust build chain is a non-issue.** M0.2 was budgeted at
    30 min — 1 hour (with bigger-compute fallback if red). Actual:
    4 minutes total. rustup user-space install (no root) + bgyss
    shallow clone + `cargo build --release --features extension-module`
    + `maturin build --release`. The "single biggest blocker" (per
    CROWD-BGYSS-CODE-AUDIT-1) was no blocker at all on Linux x86_64.

42. **bgyss's 1K-agent gate has 50× perf headroom over DESIGN v1.3 targets.**
    Target: ≤33ms/tick FAST. Actual: 0.65ms/tick (1,542 ticks/s).
    Peak RSS: 43MB (3% of the 1.5GB budget). Cache: 53MB (slightly over
    the 30MB target but under 50MB v1.1 limit). The 1K-agent gate is
    not a constraint — v1.3 can ship at 1K without perf optimization.

43. **The bgyss Rust core's nav validation IS working.** M0.4 smoke
    test's first run was rejected: `E_UnreachableDestination
    population:commuters: an assigned destination is unreachable from
    an assigned spawn`. bgyss's nav validator caught that the
    west_platform spawn couldn't reach east_exit destination (no portal).
    Fixed by adding 2 portals. This proves the Rust core is doing
    real navmesh + portal connectivity validation, not just shape-checking
    the IR.

44. **The single adapter is ~600 LOC, not 200-400 as estimated.** The
    v1.3 §2 estimate was for `kit_project_ir.py` only (~400 LOC). The
    actual adapter is 6 files: `__init__.py` + `project.py` +
    `population.py` + `environment.py` + `behavior.py` +
    `kit_project_ir.py`. The extra 200 LOC is the kit's authoring
    dataclasses (CrowdProject, Population, etc.) — kit value-add, not
    bgyss adapter boilerplate.

45. **`encode_ir()` must use `sort_keys=True, separators=(",", ":")`.**
    bgyss's `_encode_ir()` in `addon/blender_crowd/operators.py:1401`
    uses compact JSON with sorted keys for stable hashing. The kit's
    adapter must match this exactly — bgyss's `compile_project()`
    hashes the JSON string for `source_hash`; if keys aren't sorted,
    the hash won't match across runs (breaks cache invalidation).

46. **bgyss's `commuter_program: "commuter_v1"` field is required by
    the schema but its function is unclear.** The kit's adapter passes
    it through verbatim. May be a legacy field from bgyss's early
    milestones. Investigate in M1; for now, leave it as the literal
    string `"commuter_v1"`.

47. **Wheel installation paths are tricky in this sandbox.** The
    default `python3` is Python 3.12 from `/home/z/.venv/bin/python3`;
    `pip install --break-system-packages` goes to Python 3.13's
    user-site. To install into the venv's Python, use
    `/home/z/.venv/bin/python3 -m pip install <wheel>`. Blender's
    bundled Python is yet another path — M1 verifies.

48. **M0 results were wildly better than v1.3 targets.** Per
    CROWD-BGYSS-CODE-AUDIT-1, bgyss's M1 measured 820 ticks/s for 1K ×
    10K ticks. The kit's M0.5 measured 1,542 ticks/s for 1K × 1K
    ticks. The 2× speedup is likely because (a) fewer ticks amortize
    per-tick overhead differently, (b) the kit's IR is simpler (no
    portal_events, no behavior graph). M1.5 will re-measure with the
    full 10K-tick bake inside Blender to confirm.

49. **The 53MB cache size is over the 30MB target but under the 50MB
    v1.1 limit.** bgyss includes debug channels (per DESIGN v1.1 §9.2)
    that can be omitted from final caches. M3 hardening disables them.
    v1 ships with 53MB cache; not a blocker.

50. **bgyss's native API surface is fully verified.** `import
    blender_crowd_native` exposes: `AuthorableProject`, `Cache`,
    `CancelToken`, `CompiledProject`, `Session`, `Trace` classes +
    `compile_authorable_project`, `compile_authorable_runtime`,
    `compile_behavior_graph`, `compile_project`, `inspect_cache`,
    `migrate_project_v1`, `resimulate_local_kinematic`,
    `simulate_physics_handoff`, `validate_interaction_motion_attachment`
    functions. CompiledProject has `agent_count`, `agent_ids`,
    `create_session`, `project_id`, `source_hash`. Session has
    `bake(path, ticks, cancel_token)`, `step`, `tick`, `query_agent`,
    `state_hash`. Cache has `status`, `agent_count`, `tick_start`,
    `tick_end`, `read_tick`, `read_agents`, `scan_ticks`, etc.
