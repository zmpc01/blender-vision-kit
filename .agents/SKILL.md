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
- Crowd sim lives in the vendored vendor/blender-crowd-kit submodule.
- Exit codes: look.py exits 3 on validator P0/P1; blrun propagates them.
- Vision regression: `tests/test_v1_look.py` (27 checks, in-Blender).

## Design philosophy (variant framing)

Same hybrid architecture (3D-Agent, DD3M, Scenethesis): agent emits JSON
patch or bpy script → blrun.sh → Blender → look.py renders+verdicts →
the agent LOOKS at the images itself → iterate. The variant's bet: an
embodied eye cuts perception latency to zero but makes self-sycophancy
the #1 failure mode — the numbers travel WITH the images (s20 proved
this extends to E2E motion claims: world-z sampling beside every strip).

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
- EEVEE_ENGINE_ID auto-resolves per version; normalize_engine_id()
  accepts typos; iter_fcurves() (4.x fcurves <-> 5.x slotted
  channelbags + the scaffold); ensure_use_nodes(); add_sky_world();
  supports_headless_gpu() (crashes on llvmpipe — Xvfb stays required).
- A/B verified 4.2.9 + 5.2.2. fcurves_new(action, path, index, group)
  is THE version-safe write path (bind-then-write on 5.x: fcurves.new
  resolves pose paths against the CONTEXT object).

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
14. **Dog-food discipline beats code-reading for UX bugs** (s5): operating as the consumer (docs-only, real scene) surfaced 7 defects five hardening waves missed — animated-prop placement needs PATH REBASING, not current-frame re-keying; reset-and-repeat rounds VERIFY fixes from the consumer seat.
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
- Five measured laws (full: the experiments/physics_facts/ in the
  UPSTREAM checkout): no world_step (frame_set advances); sim pose
  lives in matrix_world; collision shapes snapshot at rb_add
  (unapplied scale = pass-through); depenetration ejects wedges;
  margin pop = SUM of contacting margins. Treadmill law: world-static
  + visible = paces the subject.

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

## SESSION 22 LAWS (the RH real-data round — one line; full: worklog s22 + docs/RH_CROSSVAL_s22.md)
- PATs SCOPED (test-write per repo); release assets via the API
  endpoint; library-split discovery resolves THREE clones PER-KIND
  vintage; the fixture library CROSS-VALIDATED against reality (9
  laws, fail-closed on new deviations, honest-skip exits 2); the
  FROZEN-EVALUATION TRAP (DRIVE CHECK + world gates are the
  defense); stuck-pose + slot pair; 5.x fcurves.new = bind-then-
  write; loader names family_*; FBX materials by TYPE.

## KB entries (linked from AGENTS.md; each carries its own headlines)
vision_loop · render_speed · placement_and_physics · semantic_labeling ·
prop_carry · rigged_characters · glTF_export · tdawn_vision_film (the
film recipe + export command + crowd bridge contract) · crowd_fields ·
gait_modifiers.
## Session-12/13 meta (condensed to one line — full: kb/tdawn_vision_film.md)
- FACTORY-PURGE + glow law + recession occlusion + one-blrun-per-display. Full: kb.

## SESSION 14/15 LAWS (condensed to one line — full: docs/USABILITY_TD1/TF1)
- daemonize + BLRUN_FORCE; make_material(arg3); keepout rows; export-safe
  = SCALE keys; 5.x _iter_fcurves; BEATS canonical; rebase sides INVERT;
  night laws; governed-pair guard. Full: docs.

## SESSION 16 LAWS (the KIT-QUALITY wave — condensed; full: docs/USABILITY_S16 + DESIGN_D19)
- Preflight-before-export (exit 3, attributed); TWO exporters (films use
  the CANONICAL agent-kit copy); decode-parity (the decoder is the
  oracle); RNA-filter operator kwargs; battery = suite_runner.sh, fix
  waves carry PINS; audit-before-implement ROI; grep-verify anchors.

## SESSION 16 LAWS (third film — condensed; full: USABILITY_TG1)
- Capacity box = ARRIVAL TRIGGER; AgX-noon tune; clone-seam grep for the
  PARENT'S scene module.

## SESSION 17 LAWS (condensed — full: docs/USABILITY_S16 wave)
- render_angle SWEEPS marker bindings; exit 4 = unreadable image;
  per-component writes are PARENT-space; accepted-but-unimplemented
  params are fail-open lies; RNA-filter EVERY call site; _skinned_guard;
  battery fix waves carry PINS.

## SESSION 19 LAWS (the third exhaustion round + the native-vision e2e lane)

- STALE-DEPSGRAPH PREFILTERS: every AABB prefilter that reads
  matrix_world needs view_layer.update() at entry (F2B-21 class).
- set_* ops share the solver contract: write the rotation_mode's REAL
  channel, guard animation, validate override tokens; rebases convert
  world deltas via _world_delta_to_local.
- call_scene_animate is THE one animate dispatch (bind in try / bare
  fallback / the call OUTSIDE the bind try).
- 5.x NODE_OWNER LAW: material-node keys land on the NODE_TREE's
  animation_data (node_tree = an ID block; RGBA = 4 channels) — read
  BOTH owners or false-negative (socket-level keying WORKS; the
  "silent no-op" claim was a single-owner-read artifact).
- THE NATIVE-VISION E2E LANE WORKS: sub-agents audit code; the
  PRINCIPAL renders and LOOKS — the eye probes caught the 5th
  bare-animate site both audits missed. Keep eye-probes standing.
- Sandbox: BLENDER_BIN override skips the tools/blender symlink the
  battery needs; Edit+Bash in one parallel block races files (serialize);
  display-mangle survives repr() — ast.parse before EVERY commit.


## SESSION 20 LAWS (the RH lane — condensed to the laws; full: docs/rh_canvas.md s20 amendments)

- **THE SELF-SYCOPHANCY CATCH**: pose-bone LOCATION is BONE-LOCAL —
  "vertical" root motion on local Z hops SIDEWAYS; the follow-cam
  masked it and the eye certified an illusion; TWO numeric probes
  caught it. LAW: every eye-certified motion claim needs world-z
  numeric corroboration — the numbers travel WITH the strips.
- The RH source went dark s20 -> the OFFLINE FIXTURE LIBRARY
  (rh_fixture_lib.py) via STRUCTURED FBX REWRITE (parse_fbx ->
  encode_bin tree -> patch -> encode; bone rests read the A-FLAGGED
  CURVES, not P records; unit-baking deviations pinned in truth.json).
- GATE ANIMATED BEHAVIOR, not rest state (frame-evaluated WORLD hips
  z, fail-closed). placement ARMATURE law: _ARMATURE_QUADS shared face
  table; bound_box corner order i&1->z, i&2->y, i&4->x; type-check
  'MESH' not truthiness. Imported RH armatures are ANIMATED OBJECTS
  (override='keyframe'; bbox bottom-center anchors; object-level
  rotation keys clobber yaw). Renaming a pose bone AUTO-REMAPS fcurve
  paths — a decoy needs a DIFFERENT clip.
- Battery honest-skip protocol: exit 2 + SUITE-SKIP marker. PAT
  signature: API 200 + git 401 -> provision via the API tarball.

## SESSION 21 LAWS (re-land round — condensed; full: docs/USABILITY_TF1)

- Re-land drill ~20 min: chunked_dl Blender → wheel from the vendored
  crowd-kit wheels → install.sh BLENDER_BIN → warm cache → server
  (bun install + the REPO'S db:push contract; daemonize needs an
  ABSOLUTE log path). 5.2 engine enum BLENDER_EEVEE (NEXT is 4.x).
- THE CANONICAL EXPORTER is agent-kit's (r084#9 marker refused
  otherwise); s32 discovery gate taxonomy (generic → KNOWN_NON_STORY
  with destination; film knobs lowercase in-module); render.filepath
  ext is REPLACED by the canonical ext — derive manifests from FILES.
- Check the UPSTREAM TIP before re-deriving (GIT IS THE DISK applies
  to agent-kit too). GitLab: per-round archive branches; /home/sync
  is REPO-BY-REPO.



## SESSION 27 LAWS (the engine-map round — condensed; full: worklog s27 + HANDOFF s27 block)

- **THE ENGINE-MAP LAW**: a film module's _set_engine MUST carry an
  explicit CYCLES branch — a two-way eevee/workbench map silently
  renders workbench stills for --engine cycles, and WORKBENCH IS
  LIGHT-BLIND (gotcha 128): the "look regression" it produces is
  indistinguishable from an engine-swap tune loss. Four of six films
  shipped light-blind stills for two sessions; the certified two were
  exactly the two WITH a branch. AUDIT THE MAP whenever a film fails
  a LOOK gate with "everything flat".
- **THE ENGINE-CONDITIONAL TUNE IS INERT WITHOUT THE D2 HOIST**: a
  build-time `scene.render.engine` read sees the FACTORY default
  unless main() sets the engine BEFORE build_world
  (normalize_engine_id, the 3-line hoist). The tferry sky mirror
  never fired until s27.
- **THE BOTH-ENGINE MIRRORS (measured, s27)**: tferry/tgreen
  corpus-matched UNTOUCHED under real Cycles (the s26 ladders were
  chasing workbench ghosts); tsquall storm sky x3.0; tfog volume
  0.028 EEVEE / 0.040 CYCLES via fog_density_for_engine (Cycles
  single-scatter reads THINNER — the Cycles value is the HIGHER one).
  Copy the tferry_world mirror pattern; never a bare constant swap.
- **THE PREFLIGHT ORDER LAW**: span/animation-dependent gates run
  POST-animate (the exporter's real order); a pre-animate REJECT that
  skips the animate-dry check DEADLOCKS the preflight. And the
  animate-dry check must use the exporter's REAL dispatch
  (n_frames=None) — a truncation breaks the humanoid anchor-vs-cache
  gate's frame coherence (the dx=18.6m false-fail class).
- **THE GOVERNED EXPORT PIN**: the kit-export wrapper sha-pins
  agent-kit's blender_kit against shared_manifest.json — a moved
  agent-kit HEAD refuses the export. The s27 export vintage is
  fca46ca; ASSERT the pin in the export script.
- **THE FILMSTRIPS RESUME + FORMAT LAW**: 96-strip runs span tool-call
  windows — skip existing non-empty files (idempotent resume); pin
  image_settings.file_format="JPEG" or Blender replaces the .jpg ext
  with .png (the tsquall class).
- **THE BAND-AMEND RECEIPT LAW (re-proven)**: an engine move can land
  a calibrated gate one step off (tsquall in-line 4->3 at the pinned
  engine); amend the band WITH the recorded cause + the fresh receipts,
  never silently.
- **THE OOM KNOB ORDER** (the audit's correction): memory_limit >
  cast reduction > resolution > samples/bounces — bounces are TIME
  levers, not memory levers.

## SESSION 26 LAWS (the eye-gate verdict + the rig reconstruction — condensed; full: worklog s26 + HANDOFF s26 block)

- **THE ENGINE-SWAP LOOK LAW**: a render-engine swap INVALIDATES every
  pinned look tune — a look verdict carries its engine id; swapping
  the engine re-opens the tune (the s25 Cycles swap silently broke 4
  of 6 films; the eye gate caught what the gates could not).
- **THE ARMATURE APPLY SILENT-RESET**: transform_apply on an ARMATURE
  resets the object scale WITHOUT baking the data — all armature
  transforms go through edit-bone surgery (a probe-proven law).
- **THE OBJECT-LEVEL FIT LAW**: baking an imported armature's object
  matrix (rot+scale) into data TWISTS every bone frame (roll does not
  follow a data rotation) — fit imported rigs at OBJECT level only.
- **THE CHANNEL-COHERENCE LAW**: an imported clip skeleton's rest-
  scales + cm channels + data are ONE coherent system — data-space
  rescale lands the action translations 100x; the object matrix is
  the only safe scale knob.
- **THE BASIS-PAIRING LAW**: skinned meshes ride coherent skinning
  only when mesh basis = arm_world^-1 @ mesh_world (the rot90X cm
  import convention included) — scale-only pairings leave the
  rotation mismatch and explode the skin.
- **THE DANGLING-MODIFIER STATUE CLASS**: clearing an armature
  modifier at isolation and then "retargeting" it ships REST-POSE
  statues — bind green, gates green, skin dead; the multi-vertex
  evaluated-mesh probe (G5) is the catcher.
- **THE ALIASING GATE LAW**: sparse gate sampling lies about
  oscillating signals (5 samples read hips bob 0.018; the TRUE
  excursion 0.045 across 37 frames) — sample dense enough to bound
  the extremes before believing a FAIL.
- **THE WOLD-SPACE-CORRECTION LAW**: a world-space correction stored
  as an object LOCATION gets rotated by downstream parent chains —
  corrections bake into the DATA (and a round-trip assert on the
  re-appended artifact must confirm the world effect BEFORE saving).
- **THE SYSTEMEXIT SWALLOW**: Blender swallows SystemExit messages —
  a "silent crash" with no traceback may be your OWN gate firing;
  wrap main in a traceback-to-stdout dump while iterating.
- **THE STALE-ARTIFACT LAW**: every intermediate render made with a
  since-replaced artifact is STALE — re-render after the artifact
  lands, never certify mid-ladder frames.
- **THE RIG-SERVING FALLBACK LAW**: load-bearing assets serve through
  env-wins/repo-fallback (the clips' pattern generalized): the rig
  lives at vendor/rh_rig/ (a lossless .blend, committed + sha'd);
  RH_ASSETS wins when the checkout exists.
- **THE EYE-GATE SHEET PIPELINE**: scripts/s26_eye_sheets.py rebuilds
  the per-film sheets from the COMMITTED packages (the /home/sync
  copies die with the sandbox — the app repo is the durable source).

## SESSION 25 LAWS (the humanoid rollout + collision/nav round — condensed; full: kb/s25_humanoid_rollout.md)

- **THE 24FPS TIMEBASE LAW**: the FBX imports (rig/walk/idle/UAL)
  SILENTLY flip scene.render.fps 24→30 — the GLB plays at the SCENE
  fps, so the film exports playing 1.25x fast. _fps_guard
  saves+restores around EVERY import; the gate that catches it:
  key-interval bands (apparent speed = sim × 1.25 — tform_2 slipped
  UNDER the band at drill speeds and SHIPPED the latent look bug;
  tform_3 re-export carries the fix).
- **THE DATA-NAME LAW**: structural finders must resolve at the
  mesh-DATA level — per-group copies rename BOTH object and data
  (Object.copy SHARES data; the rename happens on the unique data
  copy, else the finder matches 0 bodies).
- **THE ARRIVAL-DELTA GATE**: any obstacle-declaration change proves
  baseline-vs-new probe arrivals MATCH before the geometry scan is
  trusted — a sealing rect jams silently (tsquall 84/38 identical).
- **THE ANIMATION-BAKE OOM LEVER**: export_frame_step=2 at the
  bake's own 12Hz halves the 28M-key bake; gates are interval-
  normalized.
- **THE STAGE-COMMIT LAW**: stage and the app-repo commit in the
  SAME micro-step — the tform_2 loss class (a staged package without
  its commit is unreproducible; the sandbox wipe proved it).
- **THE EXEMPT-ROW LAW**: film overlay performers (the tsquall slip
  faller's tumble) get documented EXEMPT rows, never silent skips;
  the report printer is shape-agnostic (the 5-d KeyError class).

## SESSION 24 LAWS (the sync + vision-lane round — condensed)

- **Probe before you clone**: the credential matrix AND the repo
  locations drift between sessions (vision-kit is zmpc01's, not
  beulahkemp's — a lossy summary said otherwise; the direct API probe
  settled it in one call). Re-verify every "known" fact against the
  remote.
- **A runner-shaped hole is a tool**: the suite_runner the worklog
  recorded was absent from the tree — every re-land re-derived the
  loop by hand. Restored as scripts/run_battery.sh with BOTH
  invocation contracts (bpy suites via blrun; bpy-less vendored
  unittest via host python3 — unittest.main consumes blrun's flags).
  Sweep tests/ for bpy-less files before trusting a blrun-only runner.
- **The sync law bites on PARTIAL vendors**: a lane's "kit s41
  wholesale" vendor carried rh_canvas only — the crowd_obstacles
  bridge never arrived. Diff the SOURCE commit's file list against
  the vendored tree, never trust the vendor message's scope claim.
- **Submodule pin supersets are safe to vendor against**: VK's pin
  (b4bf76e) is 467 commits AHEAD of mainline's — the vendor gate +
  battery verify the superset live. Newer-pin vendors need a gate run,
  not a pin downgrade.
- **AUDITS read code; CONSUMERS read docs** (the U1 law): four
  blockers no code audit saw (argparse vs blender argv — always
  script_argv(); a CLI that cannot see a scene; an undiscoverable
  answers schema; an ImportError in the vendored guide's own
  snippet). Run a docs-only consumer wave on EVERY new CLI surface.
- **The fail-open class recurs wherever gates meet callers** (third
  occurrence): computed-printed-never-enforced (the lab's world
  gates). The fix is ALWAYS the same shape: assert at the collection
  site, carry the verdict into the artifact.
- **A gate's strict form is falsified by the happy path** (second
  proof): slotless-over-LIVE refuses, but a FRESH slotless bind is
  the legitimate bake shape. Measure the refusal against the real
  path before landing it (the connected-location lesson, again).
- **Render-encoding laws are measured, never assumed**: 0.012m
  outlines anti-alias away; an outline at floor z is OCCLUDED by its
  own object; a fixed bevel is 0.5px at 19m ortho; RGB-distance
  visibility never fires on AA-blended pixels (hue bands do). Probe
  render, LOOK at the probe, then pin the law in the module.
- **Sanctioned deltas travel in lockstep**: the +4 re-export names
  touched the re-export, BOTH gate tests (count pins), the ledger
  row, and the O8a pin — one contract, N pins, update N sites or
  the battery lies.

## SESSION 23 LAWS (the audit-everything round — one line each; full: worklog s23)
- THE VACUOUS-SCORE CLASS (caught live in BOTH rh suites): a suite
  row() scoring only EXCEPTIONS prints ALL PASS with [FAIL] on the
  wire — row scoring fails on check-level failures; sweep every
  suite's row() before trusting its green.
- Determinism preconditions are SELF-GUARANTEED: row state from a
  fresh sandbox (name registries, cache dirs) fails on re-land —
  factory-reset INSIDE the row.
- Gates must be ENFORCED, not returned (computed-printed-never-
  raised is fail-open); fold audit findings WITH judgment — the
  connected-location refusal was wrong vs measurement (skip+report
  beat refuse on a zero-information channel).
- Check the upstream tip before porting (re-proven x2); bump the
  submodule pin at WRAP time (the working tree drifts); a booking's
  obituary goes in the ledger (CLOSED-BY-UPSTREAM + what replaced
  what).

## S28 LAWS (the night-market build — sim + eye + ship)

- **CONCOURSE POISON LAW**: a destination capacity box overlapping a
  blocked square fails the WHOLE scene compile (UnknownNamedPortal +
  UnreachableDestination cascades far from the cause). Keep anchor
  capacity boxes clear of every block; bisect at the REAL layer
  (compiled.create_session — compile_authorable_runtime does NOT
  build the concourse).
- **QUEUE-PORTAL LAW**: a portal resolves from its point/width alone;
  a point ON a wall face has walkable tiles on ONE side only ->
  portals_named empty -> UnknownNamedPortal. Rails-as-walls FLIP
  reachability pairs red — serving-window rails stay DRESS.
- **ADMISSION-CAP LAW**: admission_capacity=1 admits exactly ONE
  agent ever (9 requested, the node decisive every tick). Pin cap =
  the slot count.
- **CHASE-HOST LAW**: the bridge spawns the 9-deep tail in
  zones[0]'s strips — order the zones so the queue's host is zone0,
  then re-author its spawn_sources (a narrow box near the beat).
- **CONGESTION-DRAG LAW**: the realized mean speed decays as the
  aisles pack (0.36 -> 0.12 measured) — start the plan ABOVE the
  target pace; the hold-class behaviors (Wait/Hold) do the lingering.
- **RELEASE-CYCLE FINDING**: a queue line ALONG a busy corridor HOLDS
  (0 releases in 45 s) — the parked line IS the beat; amend the gate
  band with the recorded cause (the s27 band-amendment pattern).
- **EYE-LADDER LAWS**: practicals ride the BOTH-ENGINE mirror
  (_lw = 3.5 under Cycles) INCLUDING lanterns; the aerial reads with
  exposure ~0.85 + canopies smaller than the light spread; _kf
  PRESERVES z (cranes/cams need a _kf_loc3 full-location key); EVERY
  moving lens gets keys (the exporter's translation-track gate); the
  CAST carriers must NOT be hide_render (the exporter excludes them —
  ride_principals degenerates the mesh instead); the stills runner
  needs the FULL env (CROWD_CACHE_DIR / RH_ASSETS / <FILM>_HUMANOID).
- **GOVERNED-COPY LAW**: governed-copy syncs are COMMITS (an
  uncommitted sync dies with the sandbox and re-breaks the export
  pair); NEVER rsync --delete into a superset dir (prop_carry.py
  class).
- **MARKET-SHAPED GATES**: a film whose behavior is not the commute
  default re-authors its probe gates from the MEASUREMENT
  (arrivals-within-r, the aisle spread, the linger fraction, the
  queue admits/in-line) — the chase in-box gate is meaningless there.
