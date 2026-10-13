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

- `EEVEE_ENGINE_ID`/`normalize_engine_id()` (spelling-tolerant),
  `iter_fcurves()` (4.x fcurves ↔ 5.x channelbags), `ensure_use_nodes()`,
  `add_sky_world()` (NISHITA 4.x ↔ MULTIPLE_SCATTERING 5.x),
  `supports_headless_gpu()` (llvmpipe crashes — Xvfb still required).

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
12. **Inventing API return keys** — asserted `r["state"]` on a report whose real keys are `ok`/`post_contact` (T8). Read the function's return dict BEFORE writing the assert; the kit's own "check the real API first" law applies to tests too.
15. **The harness REAPS background processes** (session-5): nohup/setsid did NOT keep install.sh alive across tool-call boundaries — the log just stops mid-step and `ps` finds nothing. Long download/extract steps: run in the FOREGROUND with a generous tool timeout. A truncated install log with no error = reaped, not failed.
16. **Display-layer mangle is recurring and sneaky** (twice now): sed/Read/byte-prints sometimes DROP a `[`+following char, showing impossible syntax in valid files. The truth sequence: char-codes (hex ord) / `od` / `ast.parse` / `tokenize` — if parse OK but the printed line looks broken, BELIEVE the parser; never "fix" a phantom syntax error.
17. **Dog-food discipline beats code-reading for UX bugs** (session-5, R1+R2): operating strictly as the consumer (docs-only, real scene, honest friction log) surfaced 7 kit defects that five hardening waves missed — the deepest (animated-prop placement needs PATH REBASING, not current-frame re-keying) was only observable end-to-end. Reset-and-repeat rounds also VERIFY the fixes from the consumer seat.
18. **One CLI vocabulary, many accepted spellings** (session-6 R3 F1/F5): three engine vocabularies had evolved (docs raw enums, look-family short names, ship-family raw enums) and the docs' literal command crashed. When layers of one surface must speak different conventions (dispatch names vs Blender ids), bridge at the argparse `type=` layer with ONE normalizer per convention — never let a `choices=` list reject spellings the docs themselves teach. Note argparse DEFAULTS bypass `type=` (keep defaults in the family's native convention).
19. **A tool with zero test coverage is presumed broken** (session-6 R4 F10b): export_previz_package carried a rename-leftover NameError that crashed EVERY run of ANY scene — it simply had never been run since the refactor. Every refactor leftover is a live landmine in an unexercised path; a lane the docs ship is a lane a suite must walk.
20. **Crowd-convention tools must be lane-aware** (session-6 R4 F10): gates that index `shots[0]` or demand `ctx["scene"]` crash template-family scenes. Fail-closed gates should fire when the scene DECLARES the concept (SHOTS table, BOARD/RUN_PARAMS) and pass vacuously otherwise.
21. **Workbench looks cannot see world lighting** (session-6 R3 F6, gotcha 128): workbench ignores world/sky entirely, so sky-driven EEVEE overexposure is invisible in every previz look — only the ship-preview lane (EEVEE, 0.0 EV on purpose) tells the truth. Cross-lane blindness is a design fact: know what each render mode CANNOT reveal.
22. **Remote can move mid-session** (session-6): a parallel QA lane pushed while I worked and my push rejected non-fast-forward. Protocol held: fetch, verify their diff is non-overlapping, rebase, push. Never force; the remote is the shared disk now.

## Verification discipline

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

## KB entries (linked from AGENTS.md; each carries its own headlines)
vision_loop · render_speed · placement_and_physics · semantic_labeling ·
prop_carry · rigged_characters · glTF_export · tdawn_vision_film (the
film recipe + export command + crowd bridge contract) · crowd_fields ·
gait_modifiers.
## Session-5 meta (condensed — full record docs/USABILITY_R5.md)

DOG-FOOD when quality saturates: consume via AGENTS.md only, id every
friction, fix from the consumer seat. Relative intersection thresholds;
animated-prop placement rebases ALL keys (override='keyframe').

## Session-6/7 meta (condensed; full records docs/USABILITY_R5-R7.md + kb/semantic_labeling.md)

- D15 display sync (workbench reads diffuse_color); EEVEE warm-cache
  MemAvailable >= ~2.4 GB; driver contract build_scene->ctx +
  animate(ctx,*,start_frame,n_frames); D16 vendor-node granularity +
  STOP-AND-FLAG (full: docs/USABILITY_R5-R7.md).

## R7/R8 addenda (condensed — full records docs/USABILITY_R7.md + R8.md + D17)

Route planner = PURE PYTHON on the manifest (waypoints or STOP-AND-FLAG
exit 4, never a guess); stairs are bbox-decidable only for OUTSIDE-ABUT;
a label is a hypothesis until a USE exercises it (navigation = the
strongest label validator). Seat protocol D17: region-growing probe on
labeled furniture with sat-upon/clutter/contamination guards; NLA
walk->sit->idle->exit on ONE track; verify delegated sits by the audit
numbers, never self-reports.

## Session-12 meta: the vision-native FILM (TERMINAL DAWN)

Deep recipe: kb/tdawn_vision_film.md; frictions: docs/USABILITY_TD1*
; design: docs/DESIGN_terminal_dawn.md. Survival laws:

- F-TD5 LANDED UPSTREAM (view_layer.update before the #29 sweep).
- Marker-camera hijack: custom passes suppress → RE-ASSERT scene.camera.
- **5.2 AgX emission laws**: pin Emission COLOR; hot keys <= 0.95; sky
  0.35-0.5 + exposure -0.5 (day films: the session-16 ratio law).
- **the bridge shape is a FEATURE**: converge stories re-author with
  ZERO bridge forks; N pinned 129; density via GEOMETRY; re-author
  zones/keepouts/speed-plan (dataclasses.replace), never the bridge.
- **the vision loop pays for camera work**: expect 2-3 reframe rounds;
  check cams at REPRESENTATIVE frames; "invisible subject" = ray-cast
  through it first.
- **the unmapped-constant gate is a feature**: uppercase = mapped
  vocabulary only; internal wiring lowercase.

## D18 ASSET PARTITION LAWS (session 13; full: docs/USABILITY_R9.md)

- `libraries.write(path, {ids}, compress=True)`: DOWNWARD closure only.
- Append: NO dedup, NO scene linking (link yourself); fake_user does
  NOT survive; purge-vulnerable = users==0 or (fake_user and users==1).
- Scene-owned compositor trees drag the SCENE through write() — dump
  to JSON + re-create. save_as_mainfile re-relativizes // paths;
  vendor files ship autopack ON — disable first.
- Write sets pairwise-disjoint, |union| == census (asserted); a
  double-write corrupts same-named DATA at rebuild.
- Expectations must be DATA-DERIVED, never hand arithmetic.

## SESSION 13 LAWS (the tdawn iteration round — refined by 12+ eye loops)

- **THE FACTORY-SCENE PURGE LAW**: `--factory-startup` loads the
  default Cube+Camera+Light INTO YOUR SCENE. PURGE the trio at
  build_scene start (a stray cube sat in the gate mouth for 2h).
- **GLOW-SURFACE LAW**: emission on near-white ALBEDO = a white void;
  decouple (dark base + saturated Emission Color, set independently).
- **RECESSION OCCLUSION**: a recessed structure on the CAMERA'S side
  occludes everything inside it; when a subject "vanishes" ray-cast
  THROUGH it first — the fix is a viewpoint, not a retime. "Frame-edge
  clip" that resists resizing is occlusion too.
- **NEVER run two blrun/EEVEE pipelines concurrently** (Xvfb :99 —
  the second kills the first SILENTLY). Serialize all Blender work.
- **Bfont advance ≈ 0.91-1.1em/char**; check occluders, not just FOV.
- **The governed-pair guard** catches cross-repo drift LOUDLY: land
  the kit fix → tools/sync_shared.py --to <consumer> → commit BOTH.
- **Pillow on 5.2 = python3.13** (install.sh's probe misses it).
- **Palette per-agent = post-materialize only** (bake2 gives private
  meshes users==1; RB carts copy-first; earlier assignment mutates
  the SHARED lib datablock and collapses the crowd to one color).

## SESSION 14 LAWS (the review round + the trio + the SECOND film)

- **daemonize.py (double-fork)** is the ONLY durable background
  pattern — setsid/nohup/backgrounded jobs die with the harness's
  tool-call process group. daemonize chdirs to / — absolute log +
  `bash -c "cd <repo> && cmd"`.
- **blrun CARRIES A LOCK (F-TD10)**: exit 90 + LOCK-HELD; BLRUN_FORCE=1
  bypasses; BLENDER_DISPLAY=:98 runs a real second pipeline.
- **make_material emission params (F-TD11)**: (name, rgb, rough,
  emission_color=, emission_strength=) — dark base + saturated color;
  strength is a DIRECT write.
- **look.py --probe-camera (F-TD12)** names each camera's center-ray
  hit — USE IT ON EVERY REFRAME.
- **The keepout seam (F-TD13)**: rows are (name, px, py, f0, f1)
  FRAMES; seconds are INERT; rows are lens-coupled; keepouts_applied
  counts ROWS not effect.
- **hide_render keys do not export** — the export-safe visibility
  pattern is SCALE keys (0.001 → 1.0 at the beat).
- **The night-light laws (LAST FERRY slice)**: (1) emissive materials
  glow but do not LIGHT — every neon/lamp/window needs a real light
  object; (2) the sky ladder: 0.04 DEAD → 0.12 + practicals; (3) a
  saturated neon bar owns its local radiance — a warm hero under a
  cyan bar goes GREEN: give him a diegetic warm anchor (checkpoint
  lantern) and keep the deck fill neutral-cool (a blue fill makes it
  worse); (4) 5.2 SSR knob = `scene.eevee.use_raytracing` (use_ssr
  does not exist — probed).
- **5.2 slotted actions: `.fcurves` is NOT on the Action** — use the
  vetted `_iter_fcurves` helper (channelbags) in every new scene
  module; direct `action.fcurves` raises AttributeError.
- **The unparked lib mesh stands in frame**: build_commuter_mesh
  leaves a scene-linked source object — PARK it outside every frustum
  (tdawn: y=-41) or it photobombs as a WHITE figure at the origin.
- **The second-film pattern (zero-fork reuse)**: converge stories fit
  the bridge's hardcoded (0,0) target natively — build the choke AT
  the origin, never move the target. Copy the tdawn module SHAPE
  (contract/world/actors/scene), change the STORY not the bridge.

## SESSION 15 LAWS (the app lane + LAST FERRY build)

- daemonize.py chdirs to "/": absolute log + `bash -c "cd <repo> && cmd"`.
- Comments db dies with sandboxes; durable copy = escape export file, re-inject via POST.
- sfx events: {name|kind, frame} or the app drops them (console find).
- Exporter: ctx["scene"] load-bearing; BEATS=(id,t_s,label).
- make_material arg3=ROUGHNESS; emission via F-TD11 kwargs.
- Aim cams at hero HOLD poses; stills catch the BEAT frame (S9 = f735).
- Rebase sides INVERT on replay: --theirs = YOUR commit, --ours = remote.
- Sandbox chrome can't play 21MB GLBs — verify via API + stills only.
- Crowd wheels drift across repos: the bridge pins the NEWEST.
- Barricade squares past the walkable edge = E_InvalidRange (cap at
  walkable−r). The FLOW STRIP is the geometry-seam detector — run
  BEFORE cameras (caught water-walking invisible to dry-runs). A
  scene module is DONE only when a flow strip runs THROUGH the kit
  loader. Night close-up emission ceiling is DISTANCE-dependent (1.9
  far OK, ~1.1-1.3 near). No absolute sandbox paths in repo scripts.
  Kit mode has NO hero-lane pushout (HERO_LANES dead data).
- Git discipline held through 3 two-lane collisions: fetch-inspect-
  rebase + eye-arbitration of certified sets; never force.

## SESSION 16 LAWS (the THIRD film: GREEN LIGHT — the daylight regime)

- **THE CAPACITY BOX IS AN ARRIVAL TRIGGER, NOT A CONTAINER**: an
  agent freezes (velocity 0, GHOST — no neighbor risk) the moment it
  ENTERS x ±5; the crowd never piles INSIDE. Design converge films
  FROM the box mechanics; any plaza-scale barricade there seals a
  nav pocket → UnreachableDestination. Embracing the two-rank ghost
  freeze AS the story was the trilogy's best design move.
- **The speed envelope is PER-FILM**: max_speed = populations[0]'s
  mu+3σ applied to ALL agents (no global cap). The film's zone0 plan
  IS the cap; the tail must fit it.
- **NO delayed emission exists**: every population spawns at t0 —
  "a crowd waits for the light" is unauthorable; open with motion.
- **AgX-noon laws**: the pastel wash is the SKY AMBIENT (p95−p50
  0.07), not the sun disc (disc-off changed nothing) and not
  exposure (no clipping) — tune the direct:ambient RATIO (won
  sun5/sky0.15/1°). White cards need a DARK field at noon (the
  night cream-on-dark law INVERTED); glyph emission sweep 1.9/3.9/
  5.5 (the night ceiling does not transfer).
- **The x-sign palette split**: the V5 zone row spawns symmetric E+W
  strips (asymmetric x is inexpressible) — two-stream identity is a
  SCENE-SIDE palette keying on spawn-x sign at f1; value-split
  tones (not hue) read at 640×360.
- **The clone-seam law**: a tool clone that seds names misses the
  scene-module path — the stills runner rendered the FERRY's shots
  into the tgreen dir; only the eye gate caught it. Grep the clone
  for the PARENT'S scene module before running; the review wave is
  never a substitute for eyes.
- **The spawn-band vs dressing seam**: set geometry must clear the
  spawn strips (CROWD_X_RANGE ends) — facades at |x| 28 swallowed the strip end (~30 agents inside
  buildings, walking out through walls in the GLB). Dress BEYOND the
  walkable, not inside its tail.
- **The seed override must move the CONTRACT attr** (the bridge
  compares int(contract.CROWD_SEED) == int(seed) at ingest).
- **Determinism hygiene**: never reuse the default --out across
  runs (it destroyed the run-1 evidence); uncommitted states leave
  no git trace; the pin law held when truly same-input (byte-
  identical reruns, tferry 8b7d4d8e cross-session).
- Ledger: docs/USABILITY_TG1_green_light.md (F-TG1..8); design
  REV-4 = built truth.
