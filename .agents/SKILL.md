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
- QA division of labor (session-4, owner-ruled): sub-agents do NON-VISUAL
  QA only (code review, script execution, textual assertions — wave 5-b
  caught 3 real bugs this way); the principal makes EVERY visual verdict.
  Do not rebuild VLM bridges or delegated-vision paths — retracted.
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

- **Repo**: github.com/zmpc01/blender-vision-kit (canonical — F2D-1 fix:
  SKILL used to name the UPSTREAM blender-agent-kit here, which would
  push THIS fork's work into the shared mainline)
- **Mirror**: gitlab.com/ansgareutychisO/blender-vision-kit on branch
  `github-canonical` (the session-16 raw mirror diverged in the
  push-protection history rewrite — NEVER force it; push with
  `git push gitlab main:github-canonical`)
- **GitHub push protection REJECTS commits carrying ghp_ tokens** — the
  token's home is .env (see .env.example); GitLab carries raw history
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

## Common meta-agent mistakes1. **Calling blender without blrun.sh** — `import blender_kit` fails (no PYTHONPATH). Always go through blrun.sh.
2. **Not warming EEVEE shader cache** — first render is 28s. `blrun.sh --warm-cache` once per container.
3. **Editing in `/home/z/my-project/`** — watchdog reverts every 20s. Work in a clone outside it — the session-17 standard path is `/home/z/repos/blender-vision-kit/` (older docs may say /home/z/blender-kit, /home/z/work/... or /home/z/vision-work — all mean the same law). Also: git checkout writing inside a symlinked `tools/` REPLACES the symlink (broken-symlink signature; scope-check warns).
4. **Setting EEVEE attrs that don't exist** — `use_bloom` removed in 4.2+. Use `_safe_set()`.
5. **Not cleaning up temp cameras** — `viewport_capture.py` temp cameras accumulate. Use `_cleanup_temp_camera()`.
6. **Not validating render output** — EEVEE shader failures produce 0-byte PNGs with exit 0. Always `_validate_outputs()`.
7. **Writing contact sheets without Pillow** — Pillow not in bundled Python by default. install.sh pip-installs it.
8. **Forgetting `--python-use-system-env`** — if you must call blender directly (debugging), add this flag.
9. **Not exercising every gate path** — a gate that only runs at render time passes every dry-run. Always run one full pipeline pass (dry-run + render + encode + export) before shipping.
10. **Letting advisory gates stay advisory** — a gate that can't abort the build protects nothing. Flip to fail-closed the round you add it.
11. **Inventing API return keys** — asserted `r["state"]` on a report whose real keys are `ok`/`post_contact` (T8). Read the function's return dict BEFORE writing the assert; the kit's own "check the real API first" law applies to tests too.
12. **The harness REAPS background processes** (session-5): nohup/setsid did NOT keep install.sh alive across tool-call boundaries — the log just stops mid-step and `ps` finds nothing. Long download/extract steps: run in the FOREGROUND with a generous tool timeout. A truncated install log with no error = reaped, not failed.
13. **Display-layer mangle is recurring and sneaky** (twice now): sed/Read/byte-prints sometimes DROP a `[`+following char, showing impossible syntax in valid files. The truth sequence: char-codes (hex ord) / `od` / `ast.parse` / `tokenize` — if parse OK but the printed line looks broken, BELIEVE the parser; never "fix" a phantom syntax error.
14. **Dog-food discipline beats code-reading for UX bugs** (session-5, R1+R2): operating strictly as the consumer (docs-only, real scene, honest friction log) surfaced 7 kit defects that five hardening waves missed — the deepest (animated-prop placement needs PATH REBASING, not current-frame re-keying) was only observable end-to-end. Reset-and-repeat rounds also VERIFY the fixes from the consumer seat.
15. **One CLI vocabulary, many accepted spellings** (session-6 R3 F1/F5): three engine vocabularies had evolved (docs raw enums, look-family short names, ship-family raw enums) and the docs' literal command crashed. When layers of one surface must speak different conventions (dispatch names vs Blender ids), bridge at the argparse `type=` layer with ONE normalizer per convention — never let a `choices=` list reject spellings the docs themselves teach. Note argparse DEFAULTS bypass `type=` (keep defaults in the family's native convention).
16. **A tool with zero test coverage is presumed broken** (session-6 R4 F10b): export_previz_package carried a rename-leftover NameError that crashed EVERY run of ANY scene — it simply had never been run since the refactor. Every refactor leftover is a live landmine in an unexercised path; a lane the docs ship is a lane a suite must walk.
17. **Crowd-convention tools must be lane-aware** (session-6 R4 F10): gates that index `shots[0]` or demand `ctx["scene"]` crash template-family scenes. Fail-closed gates should fire when the scene DECLARES the concept (SHOTS table, BOARD/RUN_PARAMS) and pass vacuously otherwise.
18. **Workbench looks cannot see world lighting** (session-6 R3 F6, gotcha 128): workbench ignores world/sky entirely, so sky-driven EEVEE overexposure is invisible in every previz look — only the ship-preview lane (EEVEE, 0.0 EV on purpose) tells the truth. Cross-lane blindness is a design fact: know what each render mode CANNOT reveal.
19. **Remote can move mid-session** (session-6): a parallel QA lane pushed while I worked and my push rejected non-fast-forward. Protocol held: fetch, verify their diff is non-overlapping, rebase, push. Never force; the remote is the shared disk now.## Verification discipline

- **Design-audit gate BEFORE implementation** — write spec with decision IDs, hand to FRESH agent with implementing files + mandate to attack, apply required changes before coding. Catches semantic collisions code review misses.
- **Calibrate thresholds, don't guess** — measure the corpus, pick the separating statistic (dark-FRACTION beat mean-luma, strong-edge FRACTION beat mean-sobel). ±20% brightness and 2x downscale must not flip any fired rule.
- **Gates must travel with the retimed code** — every hardcoded frame in a gate is a stale-gate risk when the timeline changes. Re-derive from source tables, not hardcoded counts.
- **Test every gate on KNOWN-BAD input** — a gate reading the wrong JSON keys returns "all pass" on garbage.
- **Fixtures carrying ground truth must SELF-VERIFY** — planted bugs in fixtures make subjects report honest tool output while you debug the wrong layer. `_check(tag, measured, planted)` at build time.
- **Fresh-process-wins arbitration** — when in-process audit contradicts fresh-process schema/gate on the same file, the fresh process is right. Then hunt cache staleness.
- **A verifier must never repair** — gate raising ValueError on repair params is what makes its PASS meaningful.
- **Bisect empirical laws before redesigning around them** — the 5.2 ortho near-plane bbox cull was pinned with 4 renders (near-z 1.20 / 0.87 / 0.802 / 0.80) before touching the diagnostic design; the redesign then targeted the real mechanism, not a guess (gotcha 125).
- **Fixtures must exercise the DIAGNOSTICS, not just the tools** — t1-t6 gated numerically for sessions while the slice renders were unrenderable slabs; T8's principal-eye pass caught it the first session it existed.

## Vision + numbers division

- **Plain renders are undecidable** for vision agents at scene scale (12mm penetration, 30mm float undecidable; 55mm float readable).
- **Purpose-built encodings flip decidability** — heat maps, section pairs, onion-skin ghosts, trajectory overlays, closeups.
- **Vision triages WHERE; numbers decide WHAT; never blend the two roles.**
- **Numeric image gates** (`scripts/image_metrics.py`): deterministic pixel stats (luma/sat/edge/range) anchor exposure/contrast verdicts and regression checkpoints. Gates complement the eyes, never substitute for them.

## Physics layer (bullet-in-Blender headless)

Five measured laws (verified via probes — the `experiments/physics_facts/`
lives in the UPSTREAM blender-agent-kit checkout, not this fork; F2D-9):
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
- **Watchdog** reverts `/home/z/my-project/` every ~20s — work in `/home/z/repos/` clones (F2D-16: one path, everywhere).

## KB entries (linked from AGENTS.md; each carries its own headlines)
vision_loop · render_speed · placement_and_physics · semantic_labeling ·
prop_carry · rigged_characters · glTF_export · tdawn_vision_film (the
film recipe + export command + crowd bridge contract) · crowd_fields ·
gait_modifiers.
## Session-12/13 meta (condensed — full: kb/tdawn_vision_film.md + docs/USABILITY_TD1* + USABILITY_R9.md)

- F-TD5 exporter view-layer sync LANDED; D18 asset-partition: 10
  measured laws in docs/USABILITY_R9.md (chunks IMMUTABLE).
- FACTORY-PURGE LAW: --factory-startup loads default Cube/Camera/Light
  into YOUR scene — purge at build_scene start.
- Glow-surface law: dark-warm Base Color + saturated Emission Color set
  independently (make_material pins them equal — F-TD11 kwargs).
- Recession occlusion: ray-cast THROUGH a "vanished" subject (look
  --probe-camera) — the fix is a viewpoint move, not a retime.
- NEVER run two blrun/EEVEE pipelines on one display (the flock makes
  it fail fast instead).

## SESSION 14/15 LAWS (condensed — full: docs/USABILITY_TD1/TF1 + HANDOFF session-14/15)

- daemonize.py (double-fork) is the ONLY background survivor; it chdirs
  "/" — absolute paths. blrun carries a per-DISPLAY flock (exit 90;
  BLRUN_FORCE=1 bypass — suites NESTING blrun MUST set it).
- make_material(arg3=ROUGHNESS; emission via F-TD11 kwargs). look.py
  --probe-camera on EVERY reframe. Keepout rows (name,px,py,f0,f1
  FRAMES) — seconds INERT; verify keepouts_applied counts ROWS.
- Export-safe visibility = SCALE keys (hide_render does not export).
- 5.2 slotted actions: use _iter_fcurves (channelbags). Park vendor
  source meshes outside every frustum.
- sfx events {name|kind, frame}; BEATS=(id,t_seconds,label) is the
  CANONICAL agent-kit exporter's contract (shape-only here).
- Rebase sides INVERT: --theirs = YOUR replayed commit. Re-render +
  diff after every conflict resolution.
- Night laws: emissive materials do not LIGHT; sky ladder dead → 0.12
  + practicals; saturated neon owns local radiance; near-field
  emission ceiling is DISTANCE-dependent (~1.1-1.3 close, 1.9 far OK).
- Chrome cannot play 21MB GLBs — verify via API + stills. The FLOW
  STRIP is the geometry-seam detector — run BEFORE cameras.
- Governed-pair guard: land kit fix → tools/sync_shared.py --to
  <consumer> → commit BOTH (cross-repo drift fails loudly).

## SESSION 15 FILM LAWS (recovered; full: docs/USABILITY_TF1_last_ferry.md)

- The native engine REFUSES barricade squares past the walkable edge
  (E_InvalidRange) — cap barricade centers at walkable−r.
- F-TF6: kit mode has NO hero-lane pushout (HERO_LANES was DEAD DATA);
  any pushout feature must define arrival semantics FIRST (F-TG1:
  arrived agents are GHOSTS).
- The bridge shape is a FEATURE: N is pinned per-film — never "fix" a
  pinned N to match a stale constant.
- Camera-work budget: REFRAMES not new cams; keyed cranes must actually
  move (never-keyed loc0→loc1 = the static 'crane' class).
- Night pools: lamp gaps read as murky dead stretches; the title card
  needs F-TD11 emission (make_material arg3 is ROUGHNESS).

## SESSION 16 LAWS (the KIT-QUALITY wave — D19 export preflight + t10; full: docs/USABILITY_S16 + DESIGN_D19)

- **Lane discipline**: the parallel lane owns SCENE work unless the
  user directs films; never co-edit scene_*.py.
- **Preflight-before-export** (exit 3, attributed rejections); gate 15
  (sfx fail-closed) + gate 4 (BOARD total-decode-failure) backstop.
- **TWO exporters**: this tree's export_previz_package = escape/template
  lane; film lanes export via the CANONICAL agent-kit copy. Pin WHICH
  exporter is under test before writing suite asserts.
- **Decode-parity**: the REAL decoder is the oracle — assert both
  drift directions; the checker owns error quality, the decoder truth.
  A checker is never stricter than the decoder, but
  None-where-decoder-raises IS a rejection.
- **RNA-filter operator kwargs** (get_rna_type) — version-calibrated
  kwarg sets rot.
- **Subprocess tests**: direct binary + --python-use-system-env +
  PYTHONPATH=scripts; fixtures go INTO scripts/; suites that nest blrun
  carry BLRUN_FORCE=1.
- **Verify BOTH PATs at session start** (2-line curl).
- **Audit-before-implement ROI**: 3 cheap read-only audits → 1 real bug
  + the whole D19 spec. Cite file:line — but re-verify anchors by grep
  before batch-editing them (they shift).
## SESSION 16 LAWS (the third film — condensed; full: USABILITY_TG1 + DESIGN_green_light REV-4)

- THE CAPACITY BOX IS AN ARRIVAL TRIGGER, NOT A CONTAINER: agents
  GHOST on ENTER — design converge films FROM the box mechanics;
  plaza-scale barricades there seal a nav pocket.
- Speed envelope is PER-FILM (populations[0].mu+3σ caps ALL); NO
  delayed emission; the x-sign palette split is SCENE-SIDE.
- AgX-noon: the wash is SKY AMBIENT — tune the direct:ambient RATIO;
  white cards need a DARK field; glyph emission sweep 1.9/3.9/5.5.
- Clone-seam law: grep a sed-cloned tool for the PARENT'S scene module
  before running; dress BEYOND the walkable's tail.


## SESSION 17 LAWS (the second KIT-QUALITY wave — 88 findings, all ≥P2 fixed)

- render_angle SWEEPS camera-bound marker bindings (render prefers the
  marker over scene.camera — the F-TD3 silent-wrong-camera class);
  look exit 4 = unreadable image; PNG magic verified, not existence.
- Per-component location writes are PARENT-space: world-space solvers
  go through _world_delta_to_local; seat_at composes matrix_world;
  keyframe rebases take the BASIS delta (fcurves are basis-space).
- Accepted-but-unimplemented params are fail-open lies: validate tokens
  at the op layer (keep_xy/centroid/footprint/seat_mesh); the
  PARAM_DOCS↔handler parity is AST-checked in test_s17_wave_b.
- Operator kwargs: RNA-filter EVERY call site
  (blender_kit.filter_rna_kwargs) — a TypeError fallback silently drops
  settings (it dropped the previz:entity carrier).
- _skinned_guard must check the ARMATURE's animation (the rig poses the
  mesh even when the mesh object has none).
- Battery = suite_runner.sh (35 suites incl. the s19 pins); run --only
  batches in ONE foreground call. Red-by-construction fixtures surface
  when their masking failure heals — re-check expectations after
  unmasking. Fix waves carry PINS or they are UNPINNED (s18 A6: the
  whole wave was revert-silent; test_s19_wave_pins is the pattern).


## SESSION 19 LAWS (the third exhaustion round + the native-vision e2e lane)

- STALE-DEPSGRAPH PREFILTERS: every AABB prefilter that reads
  matrix_world (pair_contact / audit_scene / seam_views) needs
  view_layer.update() at entry — [set_location→audit] branched on the
  PRE-move pose and false-PASSED the gate (F2B-21 class, 3 sites).
- set_* ops now share the solver contract: write the rotation_mode's
  REAL channel (QUATERNION included), guard animation, validate
  override tokens ("rebase" was a fail-open lie). Rebases convert
  world deltas via _world_delta_to_local / _world_rotation_delta_to_basis.
- call_scene_animate is THE one animate dispatch — bind in try, bare
  fallback, the call OUTSIDE the bind try (an in-body TypeError must
  propagate; masking re-ran modules and duplicated side effects).
- 5.x NODE_OWNER LAW: material-node keys land on the NODE_TREE's
  animation_data (node_tree = an ID block; RGBA = 4 channels) — read
  BOTH owners or false-negative (socket-level keying WORKS; the
  "silent no-op" claim was a single-owner-read artifact).
- THE NATIVE-VISION E2E LANE WORKS: sub-agents audit code; the
  PRINCIPAL renders and LOOKS (smoke/s19_td3_probe, s19_motion_probe).
  The eye probes caught the 5th bare-animate site both audit rounds
  missed. Keep eye-probes standing for every silent-wrong-render fix.
- Sandbox: install.sh BLENDER_BIN override skips the tools/blender
  symlink the battery needs; Edit+Bash in one parallel block races
  files to disk (serialize); display-mangle survives even repr() —
  ast.parse before EVERY commit (a real syntax error shipped once).


## SESSION 17b LAWS (the fourth film: SQUALL — the storm-dusk regime; F-TS1..8)

- **F-TS1: the film path now COMPOSES kit layers** (sidecar-gated
  read_tick splice + real z; unlayered stays byte-identical) with the
  paired tripwire fix (the layout_composed meta marker + the
  composed-aware ground-contact gate).
- **THE MARKER-CAMERA LAW**: shot timeline markers override
  scene.camera inside their span — every probe tool nulls them in a
  finally (three ladder runs rendered one shot's pose before this
  re-landed).
- **THE AXIAL-CRANE LAW**: an opaque roof makes the packed interior
  visible ONLY along the colonnade axis — no outside-above crane can
  see under it; a wall blocks any low lens north-side too (the
  smoke-still-before-framing law).
- **THE RAGDOLL WALK-CLIP CLASS**: the physics layer moves the
  ORIGIN; the mesh keeps the walk clip — the film fix is the
  per-channel tumble overlay (rot_x/rot_y) AFTER removing bake2's
  flat whole-euler x/y fcurves via the OWNING CHANNELBAG (5.2 slotted
  actions: never action.fcurves).
- **chase_frame="belt" is now a PIN, not a default** (the r109 flip
  would silently re-band every film re-bake — F-TS2). Appended
  populations: interval=1 + zone0-first + chase-last re-asserts
  (F-TS4: the native reads ONE global interval from the ID-SORTED
  populations[0]).
- **THE SILENT-REPLACE LAW**: a python .replace() on a cam table
  drifts silently — assert-guard every replace; the keepout row and
  the camprobe cert are ONE edit (F-TS7: a stale row clamps a crowd
  hole with no camera there).
- **The portal-axis naming trap (F-TS3)**: PortalAxis names the
  CROSSING; NORTH_SOUTH = the wall at y=center.y. The emission
  hijack (F-TS4) and the loader N-pin (F-TS5, expected_agents=) are
  landed kit surfaces.
- Ledger: docs/USABILITY_TS1_squall.md; the design of record:
  docs/DESIGN_squall.md REV-3.
