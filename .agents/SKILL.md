# SKILL.md — Meta-Agent Notes (for working ON the kit) — VISION VARIANT

> For the orchestrating/meta-agent developing, maintaining, or extending
> the kit. If you're a CONSUMER agent making scenes, read **AGENTS.md**.
>
> This is NOT a worklog, NOT a plan tracker. It is the **distilled,
> generalized meta-knowledge** of working on this kit.

## VARIANT CONTEXT (read first)

This repo is **blender-vision-kit**, the vision-first VARIANT of
blender-agent-kit (upstream @3c0c60d, docs condensed from upstream
@01dd147). Upstream serves BLIND agents (ascii packs + z-ai VLM API);
this variant serves agents with NATIVE image understanding. Design doc:
`docs/DESIGN_vision_kit_v1.md` (D1–D14, audited). The vision deltas:

- `scripts/look.py` + `scripts/annotate.py` are the variant's core add:
  ONE-invocation perceive+verify (renders + validator verdict + object
  manifest + readiness headers, printed BESIDE the images), with a
  render-time-only annotation layer (grid/gnomon/labels/flag-boxes,
  `KIT_ANNOT_*` prefix, deleted in `finally`, never saved).
- Doctrine: **eyes triage and compose; gates decide geometry**. Vision
  impressions are hypotheses; mm-class claims need audit/validate/schema
  numbers. L1 image-budget, L2 chirality-via-gnomon, L3 overlay-trust,
  L4 color-from-schema laws are in AGENTS.md.
- State carrier: `apply_patch --save-blend` → `look --load-blend`.
  `--scene` REBUILDS (fresh only). Never rebuild to inspect.
- Resolution defaults re-tuned for vision: previz 480×270, look angles
  640×480, motion cells 480×360 (pixels are cheap; cold start is not).
- Blind machinery (ascii_vision.py, vlm_critique.py, z-ai CLI) was REMOVED
  in the session-4 course correction (commit ef86b85): this kit is FOR
  vision-native agents ONLY. An agent that cannot see images is upstream's
  audience. Numeric gates live in scripts/image_metrics.py.
- Crowd sim lives in sibling zmpc01/blender-crowd-kit (pre-v1); the
  in-kit stub was DELETED to avoid import shadowing.
- Exit codes: look.py exits 3 on validator P0/P1; blrun propagates them
  (wave-3 verified — the earlier "swallowed" claim was a pipeline probe
  artifact: `$?` after `cmd | grep` is grep's exit).
- Vision regression: `tests/test_v1_look.py` (27 checks, in-Blender).

## Design philosophy (variant framing)

Same hybrid architecture (3D-Agent, DD3M, Scenethesis): agent emits JSON
patch or bpy script → blrun.sh → Blender → look.py renders+verdicts →
the agent LOOKS at the images itself → iterate. The iteration loop —
how fast the agent can act, see, and correct — matters more than the
raw API surface. The variant's bet: an embodied eye cuts perception
latency to zero but makes self-sycophancy the #1 failure mode, so the
tool surface forces the numbers to travel WITH the images.

## Core principles (internalize these)

1. **The perceive→reason→act→verify loop is the product.** Every feature
   must serve it: faster mutations, faster visualization, or more honest
   verification. Don't add features that don't serve the loop.
2. **Workbench is the fast-iteration default** (~0.05–0.3s/frame, no shader
   compile). EEVEE is 2-5s warm / 28s cold. Cycles is ~50s/frame. Use
   Workbench for "did this op look right?", EEVEE/Cycles for final.
3. **The schema layer is the agent's mental model.** Agents reason over
   `scene_schema.py` JSON, not raw bpy code. New scene elements must
   appear in the schema export.
4. **Patches avoid full rebuilds.** A small JSON patch (~2s) beats
   re-running build_scene+animate+render (~10-30s). Follow the
   handler-function + MUTATIONS-dict pattern for new ops.
5. **Agents can't process video** — keyframe contact sheets are the
   canonical workaround. Sample N frames, stitch into a grid with labels.
6. **Multi-angle viewport capture catches spatial issues** —
   front/side/top/persp gives the eye the context to spot
   floating/intersecting objects that single-angle renders hide.
7. **Blender's bundled Python is isolated** — ignores PYTHONPATH (use
   `--python-use-system-env`), no Pillow by default (install.sh pip-installs
   it), no numpy/scipy. When adding Python deps, update install.sh.
8. **EEVEE needs three things**: Xvfb+GLX, libEGL.so.1 in LD_LIBRARY_PATH,
   shader cache warmed. Cycles needs none of these.
9. **Blender 4.x API drift is real** — Principled BSDF renamed in 4.0,
   EEVEE rewritten in 4.2, action.fcurves moved in 5.x. Always use
   `blender_kit._safe_set()` / `iter_fcurves()` / `ensure_use_nodes()` /
   `normalize_engine_id()` — never reach for raw version-specific attrs.
10. **Vision agents have blind spots too** — catch visible issues but miss
    geometric ones if the camera angle hides them. Defense-in-depth:
    multi-angle captures + `--closeup` + `validate_scene.py`. Eyes are
    reliable for composition/color, unreliable for precise geometry.
11. **Self-sycophancy is the vision agent's noise-vs-reality failure** —
    verify geometric claims programmatically before acting (look.py
    prints the verdict beside the images by construction).
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
| Scene building (non-visual QA) | YES | Run scripts, assert textual output; visual verdicts stay with the principal |
| Well-specified implementation | YES | If spec is detailed enough |
| Decisions needing full context | NO | Sub-agents don't see history |
| Skill compliance tasks | NO | Sub-agents miss skill instructions |
| ANY visual verdict / render judgment | NEVER | Sub-agent Read strips images in this harness; the kit is vision-native-only and does not bridge (course correction) |

## Common meta-agent mistakes

1. **Calling blender without blrun.sh** — `import blender_kit` fails (no PYTHONPATH). Always go through blrun.sh.
2. **Not warming EEVEE shader cache** — first render is 28s. `blrun.sh --warm-cache` once per container.
3. **Editing in `/home/z/my-project/`** — watchdog reverts every 20s. Work in a clone outside it (e.g. `/home/z/work/blender-vision-kit/`). Also: git checkout writing inside a symlinked `tools/` REPLACES the symlink (broken-symlink signature; scope-check warns).
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
- **Purpose-built encodings flip decidability** — heat maps, section pairs, onion-skin ghosts, trajectory overlays, closeups.
- **Vision triages WHERE; numbers decide WHAT; never blend the two roles.**
- **Numeric image gates** (`scripts/image_metrics.py`): deterministic pixel stats (luma/sat/edge/range) anchor exposure/contrast verdicts and regression checkpoints. Gates complement the eyes, never substitute for them.

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
- `/kb/vision_loop.md` — look.py protocol, annotation rules, readiness scores,
  measured timings, M5 P1–P4 perception doctrine (color / exposure / animation
  representation / transient scan)
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
- `/kb/crowd_fields.md` — influence fields, relax PBD, gait phase engine
  **Headlines**: scene-agnostic crowd primitives (FieldSpec, relax(), gait
  phase law); field tables + lane specs are DATA only (nothing project-specific
  in the engine); deterministic vectorized PBD via grouped-join expansion.
- `/kb/prop_carry.md` — generalized prop anchoring & clamped carry
  **Headlines**: PHANTOM OFFSETS law (anchor captures must be SAME-FRAME
  snapshots); capture_anchor/anchor_local/carry_keys API; held-state actions
  key the full timeline (law 106); every carry gets a sanity radius check.
