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


## Session-5 meta: the usability-study pattern (owner-directed)

When the kit's mechanical quality saturates (all suites green), the
highest-yield pass is DOG-FOODING: pick a demo scenario, use the kit
strictly as a consumer (AGENTS.md docs only — no source peeking), log
every friction with an id, fix small things immediately, verify each
fix end-to-end FROM THE CONSUMER SEAT, then RESET (fresh scenario,
fresh outputs) and run another round with a different exercise profile
(R1 = static composition + animation; R2 = physics lane). Artifacts:
docs/USABILITY_R{N}.md. The friction log IS the study's deliverable —
"What worked flawlessly" is equally important (protects against
regression-by-refactor).

Key measured laws from session-5 (also in AGENTS.md):
- audit pair `state` = exact vocabulary; `verdict` = human string, WILL drift
- validator intersection threshold must be RELATIVE (pct of smaller object)
  OR absolute — absolute-only is scale-biased (10cm mug sunk 20% was invisible)
- placement of animated props: override='keyframe' rebases ALL location keys
  by the placement delta (_rebase_location_keys) — a current-frame re-key
  leaves later keys at the pre-placement pose (measured 20mm drift by f24)

## Session-6 meta: lane dog-fooding + the D15 color law

- **D15 display-color sync**: workbench MATERIAL reads `mat.diffuse_color`,
  so node-authored (imported) scenes render ALL-GRAY and nothing detects it.
  `annotate.sync_display_colors()/restore_display_colors()` are STANDALONE
  (not part of the annotation layer) so `--no-annotate` looks stay honest;
  sync pre-render + restore in `finally`; per-MATERIAL dedupe (not per-slot);
  skip untouched default-gray; manifest rows carry `color_source`. Any new
  render surface must call the same pair — keyframe_contact_sheet rendered
  gray sheets until wired (R4 F11).
- **EEVEE warm-cache needs MemAvailable >= ~2.4 GB** (QA #2 kernel
  forensics: shader compile peaks ~2.07 GB RSS independent of resolution;
  4 SIGKILLs recorded). install.sh + blrun.sh --warm-cache guard now skip
  with a named note below 2400 MB. Cycles verify = engine-ASSIGN probe
  (`scene.render.engine = 'CYCLES'`), never RenderEngine subclass
  enumeration (false negative on 5.x built-ins).
- **Scene driver convention is a contract**: `build_scene()` → ctx dict,
  `animate(ctx, *, start_frame=1, n_frames=<int>)`. Tools that mean "module
  decides its timeline" (previz package) pass `n_frames=None` — which
  CRASHES the documented int-default signature. Bridge with
  `inspect.signature`: int default → call bare; else pass the sentinel.
- **D16 (semantic labeling of opaque imports)**: design + audit DONE
  (docs/DESIGN_D16_semantic_labeling.md, amendments adopted: lowercase
  `kit_label` prop, idempotent two-phase rename, validator
  de-name-dependence, split_mesh preconditions). Implementation = M6.

## Session-7 meta: semantic labeling of opaque imports (D16 shipped)

- **The labeling loop is a kit surface, not a convention**: LOOK (manifest,
  kit_label null) → SPLIT (loose parts if islands exist; WELDED geometry
  needs the vision-driven `split-region` world-box cut) → NAME (principal's
  eyes; closeups + dims + face-count agreement) → LABEL (label_objects,
  report-before-rename) → LOOK verify (manifest JSON is the artifact) →
  SAVE. A non-vision agent then works the labeled ids blind (proven:
  assembled a table + seated props, audit 0.0mm).
- **Prop laws**: `kit_label` is the durable identity — names may be
  suffixed/disambiguated, props never change meaning. Every MESH manifest
  row carries kit_label (null when unlabeled) so consumers can KEY on it.
  Gate exclusions moved to the `kit_semantic` PROP (labels containing
  ceiling/sun/light); names are fallback only — vision renames can no
  longer strip validator coverage.
- **Rename safety pattern (reusable)**: all-or-nothing validation, simulate
  the whole-batch rename against scene occupancy BEFORE mutating, two-phase
  (everything → guaranteed-fresh temps → finals), re-read to verify, report
  JSON written BEFORE mutation as the crash-resume artifact. Blender's
  silent `.001` auto-suffix is a lie in a patch context — pre-unique
  instead.
- **bmesh hygiene**: connected-components over vert/edge adjacency;
  return INDICES not BMFace refs (refs die with bm.free()); edit-mode
  selection via bmesh.from_edit_mesh + update_edit_mesh, then
  bpy.ops.mesh.separate(type='SELECTED'); bound_box corners are prop
  arrays — wrap Vector() before matrix multiply.
- **Welded-import cutting law**: "faces fully inside the box" is the honest
  cut unit (straddlers stay with the source — a straddler belongs to both
  visual parts; handing it to either silently deforms one). A welded
  feature is box-cutable only if its footprint PROTRUDES from its host.
- **Fixture authoring**: primitive_cube_add defaults size=2 (scale-span
  helpers MUST pass size=1 — the validator catches the 2× bug instantly);
  coplanar-welded features are NOT box-isolatable; --closeup is
  single-object per invocation.
- **place_on auto-widen blind spot (F17, open)**: 12×12 grid sampling
  misses small inset supports by 0.01m on large tops — the documented
  snap_z(bottom) fallback is the consumer escape hatch.
- **F17 CLOSED (grid refinement)**: place_on support sampling now
  refines 12→48→192 cells until rays hit (cap 192, "footprint_grid_refined"
  in the report); the snap_z fallback stays as the escape hatch. Edge
  law from R6: even a refined grid fails when the placed object's
  footprint overhangs the support bbox — center placements on the
  support, ≥10cm from every edge.
- **R6 real-level law (loft demo)**: huge imports need look.py's
  flag-wireframe CAP (60; 12k annotation objects OOM a 4GB box) and a
  look-lite .blend (strip packed images — workbench colors don't need
  pixels). Survey 20m interiors with aimed camera→target shots + frustum
  raycasts ("which object is that pixel"), never preset 5m offsets.
- **Fused-face signature**: region dry-run with verts_in_region > 0 but
  faces_to_cut = 0 at any box = floor/wall fused into wrapped faces →
  mesh_prepare (triangulate) then re-dry-run; and consider that the
  surface you want may live in a DIFFERENT object entirely (the real
  floor was a separate full-extent plane; survey before cutting).
- **Label at family granularity, verify per family**: 1155/1200 meshes
  in ONE label_objects patch generated from the manifest; confidence
  honest (high=render-verified, medium=name/bbox-derived); ~4% null is
  correct. Blind agents DO catch principal label errors via manifest
  consistency checks (the pendant-light catch) — ask them to report
  spatial anomalies against the task description.

## R7 addendum — route requests on labeled levels
- The route planner (scripts/r7_route_planner.py) is PURE PYTHON on the
  manifest: you may run it blind. It either returns waypoints or
  STOP-AND-FLAG (exit 4) — never guess past a flag.
- Stair direction is bbox-decidable only for outside-abut stairs. If
  the flag names a bbox-ambiguous stair, that is correct behavior —
  report it and wait for vision_stair_override.json.
- Waypoint z values are NOMINAL (bbox tops). The executor refines them
  by tread-hug raycast; trust nav_report.json's audit (true_floats must
  be 0) rather than the requested z's.
- Walk-in waypoints are clamped to the mezzanine bbox and bed-avoided
  from manifest bboxes; objects resting exactly ON the slab count as
  obstacles.
