# PLAN.md — Long-Horizon Roadmap

> This is the **multi-session task tracker** for the blender-agent-kit.
> Items here are expected to take multiple sessions to complete. For
> immediate next-session scope, see HANDOFF.md.

## Current status (Sept 13, 2026 — post session 14b, canonical redo + convergence)

**Session 14b landed (canonical-lineage deep audit + usability convergence):**
with the GitHub PAT restored, the whole round was REDone on the
canonical lineage (GitHub session-16 state, v3.4 live). The live
margin-pop dispute was SETTLED by a 16-case matrix probe
(probe_hull_pop): primitive contacts rest exact, hull contacts rest at
~SUM of body margins (hull-hull ~2x margin, compounding in stacks) —
both prior records were single layers of one law; production now
derives its pop tolerance from an explicit _RB_MARGIN (T5r). Round E
(3 fresh docs-only subjects, fresh-clone CI) + Round F (2 subjects at
the fixed HEAD) CONVERGED the physics placement lane: 5 subjects, 0
S1, zero new behavioral bugs after the round-E batch. Real bugs the
subjects caught, each verified against artifacts then fixed +
regression-locked (T5s/t/u): a P1 pre-flight regression (crossing
penetrations slipped the demand filter after the honest-field rename ->
16.4m ejections), the gate custom lane dropping supports from the
verify sim (false REJECTED), oracle rests_on reading the restored pose,
Blender's exit-0-on-crash (blrun now FAIL-CLOSED), and 6 fixture
ground-truth bugs (fixtures now SELF-VERIFY at build time). Portability
surgery: no more hardcoded sandbox paths; KIT_OUT env override.
Native vision (5th confirmation): plain renders undecidable for
sub-visible defects; the documented gate loop converges end-to-end
from a fresh clone. Known-open (design-gated, not defects): Track I
add-primitive patch ops (2 subjects hit it), oracle path-witness (lateral),
wedge pre-repair detection, FELL_BELOW/TOPPLED precedence for large-drop
combos.

## Prior: session 14-16 status (parallel stream — absorbed)

**Sessions 14-16 landed by the parallel stream on canonical GitHub:**
repo surgery (kit 1630->~86 files, two-repo contract + scope gate),
the escape-previz production repo (releases v2.2->v3.4, 1080-frame
renders, MP4 deliverables via GitHub Releases), fail-closed gate suite
(motion_frame_audit, occlusion_gate v2, render_stats_gate),
treadmill/crowd-sim laws, SOP Job 8a. Lineage reconciliation merged the
GitLab-only physics rebuild; its 22/22 probe re-run produced the
RECONCILIATION doc whose margin-pop verdict session-14b refined with
the hull layer (see the addendum).

## Prior: session 13 status (physics program — see HANDOFF history)

**Session 13 landed (physics-gated placement):** physics_place.py
(settle/place/oracle/gate) — bullet composes with the exact geometric
library under a strict division of labor (geometry owns mm, physics
owns topology + simple repairs). Design v3 via two fresh-context review
gates; measured fact base F1-F14 committed
(experiments/physics_facts/). 4-round usability program (9 fresh
docs-only subjects on fresh clones) converged the gate loop: REJECTED →
executable fix queue → PASS (empty queue), negative tests, no
corruption. placement_lib gained the crossing-ENTERING classifier
(spear vs resting overhang; X1 14/14). Native-vision study re-confirmed
plain-render undecidability; heat-map triage loop documented. Cold-clone
integration e2e green (T1-T5 + X1 + a physics_gate patch-op). Measured
laws in AGENTS.md gotchas #58-#62 + physics section (margin-pop
~2mm/level; frame_set(1) cache discipline; shape snapshot; commit
pattern).

## Session 12 status (earlier Sept 10)

**Session 12 landed (v3.2, the 9-point deep refinement):** every user
complaint RCA'd + fixed + GATED: coplanarity_audit (z-fight class:
bumper/bed/windshield/seatback/headlight flushes + crash-stack +
grid crossings fixed at geometry; FXAA-on-delivery for aliasing),
framing_audit + AUTO-FIT + AIM-ASSIST (head-crops are build
failures; 331->0), crowd_agents.py AI (129 agents, 9 states, unique
speeds/gaits, REACH pound, FLEE scatter, hero variance; liveliness +
speed-variance gates), loose-chunk RB barricade + jeep collider
proxy ("boxes glued to jeep" class; penetration gate), motion grid +
cavity + speed-scaled shake, 21-shot event-anchored recut (avg 2.0s,
impacts on cuts, dialog untouched), splash FX as size+strobe
starburst (workbench-visible), UAL preview delivered visibly
(ual_ab.mp4) + DELIVERY BUG FIXED (gitignored download/ had eaten
the v3 MP4s; deliverables now force-added). Blender_kit metadata
import crash fixed (render-stage only). Deliverable:
escape_sequence_v3_2 (45.0s MP4s + 21 stills + storyboard + blend/
glb + ual_preview) in previz repo + platform download. Session-12
gates caught real bugs throughout: bumper-class before render,
4-chasers-through-jeep, grid crossing z-fight, bed-rear 1700cm2.

## Session-9 status (see HANDOFF for details)

**Session 11 landed (v3 recut, user-feedback-driven):** white-world
color discipline (env white/grey value ladder; ONE color per subject
body — humans RED, zombies GREEN, jeep BLUE; white FX; taillight bases
dechromatized; palette edits across 6 files + audit enforcement),
workbench STUDIO as the viewport default (measured: subject chroma
identical to FLAT, shape readability restored; --shade flag), the 45 s
/ 12-shot recut (NEW S4 jeep-start beat: dip + pitch + dust on
"Drive!"; NEW S9 front-quarter weave; roomier boarding + dialog with
L3 regenerated; 9 s crane exhale), v2.0 camera geometry restored
(dc1e3d1-pinned) with fully re-derived animation + camera-key-coverage
gate, phase-A stalker caps (gates caught 2 real P0 bugs: RB pack
through the parked jeep; mill-bob f1 key overwrite), nearfield hide
DELETED (VLM-driven regression source), dialog end-to-onset verified.
Deliverable: escape_sequence_v3 (45.0 s MP4s + dialog + stills +
storyboard + blend/glb) in both repos + platform download. **Quaternius
UAL validated** (gauntlet PASS, A/B readability WIN vs capsules —
vendored at assets/vendor/ual/, hero-swap is the next major track).

## Session-9 status (see HANDOFF for details)

Viewport speed preset (render_aa OFF = 46 ms/frame; JPEG q85), mist
volume-shell fix (kit_atmo), per-shot finalize/freeze pipeline
(shot_pipeline.py), v2.2 deliverable (10/10 frozen).

## Older status (sessions 1-8)

**Working and validated:**
- Blender 4.2.9 LTS runs headless in Debian 13 container (no root, no GPU)
- Cycles (CPU) + EEVEE_NEXT (Xvfb-backed) both render correctly
- `blrun.sh` wrapper robust against: stale X locks, Xvfb crashes, signal
  interrupts, missing libEGL, PYTHONPATH issues
- `blender_kit` shared library with: argparse, materials, sky world,
  render config (with version-drift guarding), output validation,
  metadata.json, MP4 encoding, glTF export
- `<model-viewer>` web viewer with: animation play/pause/scrub, camera
  reset, shadow intensity, file input for loading different .glb
- Build→render→VLM→iterate loop proven end-to-end
- glTF export preserves cameras, lights, animation; loads in browser
- Private GitHub repo + GitLab mirror, both pushed
- AGENTS.md (entry-point doc) + SKILL.md (sub-agent distillation)

## Long-horizon work

### Track A: Blender version upgrade (target: Q4 2026)

- [x] ~~Validate `install.sh` works with Blender 4.5 LTS in this container~~
  (Note: tested against existing 4.2.9 install; fresh 4.5 install still
  needs validation in a truly fresh container — see HANDOFF.md)
- [ ] Run the existing scene scripts against 4.5 LTS, verify no regressions
- [ ] Update `BLENDER_VERSION` default in `install.sh` once validated
- [ ] Document any 4.2 → 4.5 migration notes in AGENTS.md
- [ ] (Stretch) Evaluate 5.x LTS when it stabilizes (est. Q1 2027)

### Track B: Scene authoring ergonomics (target: rolling)

- [x] ~~Build a `scene_primitives` helper module~~ — `blender_kit/` covers
  the core helpers (make_material, shade_smooth, add_sky_world)
- [x] ~~Add `--still` and `--dry-run` modes~~ — done in `common_parser()`
- [ ] Add `frame_camera_to_objects(objects, margin=1.2)` helper that
      computes a bounding-box-aware camera position
- [ ] Add `animate_bounce(obj, axis, height, start, end, easing='EASE_OUT')`
- [ ] Add `animate_orbit(obj, center, radius, axis, start, end)` helper
- [ ] Build a "storyboard → scene" pattern: YAML/JSON describing keyframes
      per object, compiled to a scene script

### Track C2: ASCII-vision toolchain (R5 done; rolling)

Session 9b built and measured it; session 12b hardened it to production
(R5_SPEC D1-D5: --auto, component readback rgb/lum/fill/edge, --with-pack,
35-test suite, HD invariance probe; 2 usability rounds 9/10; 2 production
audits clean). Docs: experiments/ascii_vision/{R5_SPEC,docs/RESULTS,
docs/PROTOCOL}.md, AGENTS gotcha 50.

- [x] R5: auto-variant selection, readback columns, vlm_critique
      --with-pack/--dry-run, deterministic test suite, HD probe
- [ ] Wire --with-pack into the escape-previz shot-verify SOP (SOP Job
      edit + one live production pass) once a previz session is active
- [ ] Auto-tile selection: tiles centered on component clusters instead
      of uniform NxN (cheap, testable with zero API)
- [ ] Support/grounding column: contact-shadow smudge below y1 + which
      bbox the row's bottom sits inside (U1B's top ask — makes T6
      pack-answerable instead of "not determinable")
- [ ] Generator-side blend-fragment suppression (fill=1.0 slivers with
      rgb between neighbors — currently a PROTOCOL reading rule)
- [ ] Crowd split-estimate: n_cells / per-object-area prior -> "about N"
      instead of "at least N" for merged hordes
- [ ] HD battery re-run (LLM arms at 1280x720) when API quota recovers;
      pack half already proven invariant (D5)
- [ ] Achromatic readback: luma/rgb readout for D/. classes (currently
      chromatic-only components)

### Track C: VLM integration (target: rolling)

- [x] ~~Multi-angle viewport capture for spatial verification~~ —
  `viewport_capture.py` with 6 standard angles + ring mode
- [x] ~~Keyframe contact sheet for animation verification~~ —
  `keyframe_contact_sheet.py` with frame labels + orbit camera
- [x] ~~Scene schema JSON for state query~~ — `scene_schema.py` with
  bounds, materials, animation curves
- [x] ~~Structural validator for geometric bugs VLMs miss~~ —
  `validate_scene.py` (session 4 retro: caught upside-down table class)
- [ ] Improve validate_scene.py with allowlist for intentional constructions
      (sofa parts, window frames in walls) — currently too many false positives
- [ ] Write `vlm_critique.py`: structured VLM feedback (JSON with
      `issues: [{type, severity, description}], suggestions: [str]`)
- [ ] Add `--vlm-check` flag to `blender_kit.render()` that auto-runs
      VLM analysis on the first rendered frame
- [ ] Build a "convergence detector": run VLM critique after each
      iteration, stop when no P0/P1 issues remain
- [ ] Cache VLM responses by image hash to avoid re-analyzing identical
      frames across runs

### Track D: Web viewer richness (target: Q4 2026)

- [x] ~~`<model-viewer>` basic viewer with animation controls~~ —
  `viewer/index.html` with play/pause/scrub, file input, shadow intensity
- [ ] Build `viewer-three.html` using Three.js + GLTFLoader +
      AnimationMixer for full control: custom camera scripting, multi-clip
      scrubbing, per-object visibility toggles, transform gizmos
- [ ] Use Blender camera as default view in Three.js viewer
- [ ] Add "screenshot from current camera angle" button
- [ ] Add "export current camera pose as Blender script snippet" button
- [ ] Investigate filament.js / babylon.js for Cycles-style preview

### Track E: Asset library (target: Q1 2027)

- [ ] Build a small library of reusable materials (wood, metal, glass,
      fabric, skin) as .blend files or Python helpers
- [ ] Build a small library of reusable HDRIs (sky, studio, outdoor)
- [ ] Build a small library of primitive scenes (product shot, character
      turnaround, environment flythrough) as templates
- [x] ~~Integrate Poly Haven API for CC0 HDRI/models/materials~~ —
  `scripts/polyhaven.py` written + validated (session 4)
- [ ] Wire polyhaven.py into scene scripts (build a scene that uses
      `add_to_scene("sofa_model_id")` to fetch a real CC0 sofa)
- [ ] Test HDRI loading workflow with `load_hdri()`
- [ ] Document Poly Haven workflow in AGENTS.md
- [ ] Add "Powered by Poly Haven" credit to viewer/live.html per API terms
- [ ] Integrate BlenderKit for larger catalog (freemium, API-key, mixed licenses — low priority)
- [ ] Document the asset library in AGENTS.md

### Track F: Animation richness (target: Q1 2027)

- [ ] Add camera animation helpers (orbit, dolly, crane, follow) —
      partially done in `scene_interior_room.py` (manual dolly)
- [ ] Add `look_at_constraint(obj, target)` helper using Track To
- [ ] Add path animation (object follows a Bezier curve)
- [ ] Add shape key animation for simple morphing
- [ ] (Stretch) Add armature/rigging helpers for character previz
- [ ] (Stretch) Add Geometry Nodes helpers for procedural scenes

### Track I: UAL hero-actor upgrade (NEW, session 11 — top pick)

> NOTE (session-14b): a DIFFERENT Track I below (schema protocol
> extensions) is now the TOP next-session candidate — two independent
> usability subjects hit the missing add-primitive patch ops as their
> only S2. Priority swapped: schema extensions first.

- [x] ~~Vendor Quaternius UAL~~ (assets/vendor/ual/, CC0 mirror verified)
- [x] ~~Gauntlet + A/B validation~~ (PASS: in-place drift 0.000 m,
      recolor works, no NLA; VLM reads real running vs capsule walking)
- [ ] Hero-actor swap module (Driver/Girl/Gunner/HeroZed → UAL rigs at
      scale 1.05, one-color override, action assignment map:
      Sprint_Loop / Sitting_Enter+Driving_Loop / Pistol_Aim+Shoot /
      Punch_Cross / Hit_Chest+Death01)
- [ ] Re-choreograph the 4 hero beats (sprint cycle phases, boarding
      hops → Sitting_Enter windows, lunge → Punch_Cross timing,
      gunner-thrown → Hit_Chest + tumble)
- [ ] Action-transition handling (action switching WITHOUT the NLA
      minefield — direct strip/pose bake like the capsule system, or
      stashed-NLA with the documented guards)
- [ ] Stray Icosphere cleanup on import
- [ ] A/B the full v3 shots S2/S3/S8 capsule vs UAL; keep capsules as
      fallback (the crowd stays capsule-instanced regardless — 120
      zombies at ~0 raster cost)

### Track G: Container hardening (target: rolling)

- [ ] Test the kit in a truly fresh container (simulate session restart)
- [ ] Add CI: GitHub Action that runs `install.sh` + smoke-test scene
- [ ] Pin .deb versions in `install.sh` with checksums
- [ ] Investigate conda/nix as alternative to .deb extraction

### Track H: Persistent Blender bridge (target: Q1 2027) — NEW

The current architecture restarts Blender on every `blrun.sh` invocation
(~1-2s startup overhead). A persistent Blender process driven via TCP
socket (per 3D-Agent research: "TCP socket > HTTP for 30+ back-and-forth
ops") would enable sub-second iteration.

- [ ] Design the bridge protocol (JSON over TCP, one connection per session)
- [ ] Implement `blender_bridge.py` — long-running Blender script that
      listens on a TCP port, accepts patch JSON, returns scene JSON +
      rendered PNG bytes
- [ ] Implement client-side helpers in `blender_kit/` for agents to use
      the bridge transparently (fall back to subprocess if bridge down)
- [ ] Handle session lifecycle (bridge start/stop, crash recovery)
- [ ] Document the bridge in AGENTS.md + .agents/SKILL.md
- [ ] Benchmark: subprocess vs bridge iteration speed

### Track I: Schema protocol extensions (target: rolling) — **ELEVATED session-14b (top next-session candidate)**

Two independent usability subjects (round-E sB on seat_at anchors,
round-F sF2 on primitives) hit the SAME gap as their only S2: the
patch protocol cannot CREATE geometry (scenes come from scene modules
or saved .blend files; a fresh agent must read apply_patch.py source
to learn the surface). Design-gate then implement:
- [ ] `add_cube/add_sphere/add_cylinder/add_plane/add_cone/add_torus`
      (with material + size semantics matching the fixture builders:
      data-baked, origin-centered — NEVER transform_apply)
- [ ] `add_empty` (anchor authoring for seat_at — round-E sB)
- [ ] Add mutations: `add_camera`, `add_sun_light`, `add_area_light`,
      `add_point_light`
- [ ] Add mutations: `apply_modifier` (subsurf, bevel, mirror, array,
      boolean, solidify)
- [ ] Add mutations: `set_parent`, `add_constraint` (track_to, copy_location)
- [ ] Add `apply_patch.py --exec` escape hatch for arbitrary Python (with
      safety checks)
- [ ] Add patch reversal (`--revert` to undo last N mutations)

### Track J: Documentation (target: rolling)

- [x] ~~AGENTS.md + .agents/SKILL.md role split~~ — done (AGENTS.md is
  consumer-facing, SKILL.md is meta-agent notes)
- [ ] Add `docs/` directory with deeper guides:
  - `docs/scene-authoring.md` — patterns for common scene types
  - `docs/vlm-prompts.md` — prompt library for common VLM critiques
  - `docs/troubleshooting.md` — expanded gotchas with debug steps
  - `docs/api-reference.md` — full `blender_kit` API docs
- [ ] Add inline API docs (docstrings) to `blender_kit/__init__.py` and
  generate docs with `pdoc`
- [ ] Add a `CONTRIBUTING.md` for future agents adding to the kit

## Decisions log

### 2026-09-08: Use Blender 4.5 LTS for fresh installs, 4.2.9 OK for existing
**Context**: 4.2.9 LTS reached EOL July 2026; 4.5 LTS supported until July 2027.
**Decision**: `install.sh` defaults to 4.5 LTS. Existing 4.2.9 installs
continue to work. Migration is low-risk (same OpenGL reqs, same engine id,
no breaking API changes for previz use case).
**Rationale**: Research sub-agent verified via Blender release notes that
4.2 → 4.5 has no API breaks affecting the kit's surface area.

### 2026-09-08: Use glTF (.glb) + `<model-viewer>` for web preview
**Context**: Need a 3D format consumable in browser with camera + animation.
**Decision**: glTF (.glb) is the export format; `<model-viewer>` is the
default viewer (Three.js + GLTFLoader as a richer alternative).
**Rationale**: glTF is the canonical web 3D format; `.glb` is the single-file
binary variant. `<model-viewer>` is declarative (~25 lines HTML) with
autoplay animation. Three.js gives full control for ~60-80 lines.
USDZ is Apple-only; FBX/Alembic have no native web path.

### 2026-09-08: Direct `bpy` scripting over Blender MCP server
**Context**: `blender-mcp` v1.9.1 on PyPI exposes Blender as an MCP server.
**Decision**: Use direct `bpy` scripting via `blrun.sh`; do not bundle MCP.
**Rationale**: For an agent that already writes Python, direct `bpy` is
strictly more capable (full Python vs restricted MCP tool surface) and
lower-latency (subprocess vs socket round-trip). MCP makes sense only for
natural-language-only clients like Claude Desktop.

### 2026-09-08: Work in `/home/z/blender-kit/` not `/home/z/my-project/`
**Context**: The watchdog reverts `/home/z/my-project/` to main every ~20s.
**Decision**: Clone the kit repo to `/home/z/blender-kit/` (outside the
watchdog path). Symlink `tools/` and `output/` to `/home/z/my-project/`
for compatibility with the existing Blender install.
**Rationale**: The `Write` tool only works under `/home/z/`, so the clone
must live there. `/home/z/blender-kit/` is outside the watchdog's scope.

### 2026-09-08 (session 3): Hybrid architecture — Blender as engine + JSON schema as protocol
**Context**: User research summary highlighted that every working agent-driven
3D system (3D-Agent, DD3M, Scenethesis, ThreeJSON) converges on a hybrid
architecture: structured scene schema as agent protocol, Blender as
geometry/animation engine, viewport screenshots as vision feedback loop.
**Decision**: Implement the hybrid architecture in the kit:
- Layer 1: `scene_schema.py` — JSON scene state for agent reasoning
- Layer 2: `apply_patch.py` — JSON patch protocol for mutations
- Layer 3: `viewport_capture.py` + `keyframe_contact_sheet.py` — vision feedback
- Layer 4: Existing scene_*.py + blender_kit/ as the engine
- Layer 5: `viewer/index.html` for human-in-the-loop preview
**Rationale**: Pure bpy code-gen produces "geometry soup" after 3-4 steps
without visual verification (3D-Agent learning). Structured schema lets
agents query/patch state as data, falling back to bpy only when needed.

### 2026-09-08 (session 3): SKILL.md vs AGENTS.md role split
**Context**: User clarified that SKILL.md is for the meta-agent working ON
the kit, AGENTS.md is for consumer agents USING the kit.
**Decision**: Rewrote both docs with the correct role split:
- `.agents/SKILL.md` — meta-agent notes (design philosophy, architectural
  decisions, when to extend, common meta-agent mistakes, git workflow)
- `AGENTS.md` — consumer guide (perceive→reason→act→verify loop, tool
  reference, gotchas, file layout, when to ask for clarification)
**Rationale**: Different audiences need different docs. A consumer agent
doesn't need to know about git workflow or architectural rationale; a
meta-agent doesn't need to re-read the 12 gotchas every session.

### 2026-09-08 (session 3): Workbench as fast-iteration default
**Context**: EEVEE_NEXT cold-start is 28s; warm is 2-5s. Cycles is 50s/frame.
For "did this op look right?" checks, all are too slow.
**Decision**: Use Workbench engine (solid shading, ~0.8s render, no shader
compile) as the default for viewport captures and iteration loops. EEVEE
for material/lighting verification, Cycles for final stills.
**Rationale**: Workbench doesn't render PBR materials, but for spatial
verification (layout, intersections, scale) it's strictly faster. The
research consensus is that iteration speed matters more than render quality
for the agent loop.

### Track K: E2E live viewer enhancements (target: Q4 2026) — NEW (session 4)

The e2e live viewer (`agent_server.py` + `viewer/live.html`) is functional
but has room to grow:

- [x] ~~Basic SSE event streaming + auto-refresh .glb~~ — done (session 4)
- [x] ~~File watcher on scene.glb for auto-notify~~ — done (session 4)
- [x] ~~Progress tab with event log + progress bar~~ — done (session 4)
- [x] ~~Scene tab with metadata from scene.json~~ — done (session 4)
- [x] ~~Screenshots tab with viewport captures~~ — done (session 4)
- [ ] Add "live Blender viewport" mode: stream viewport screenshots every
      N seconds while the agent works (not just on explicit screenshot events)
- [ ] Add VLM critique panel: show the VLM's analysis of the current frame
      alongside the rendered image
- [ ] Add "agent decision log" panel: show what the agent is reasoning about
      (would require agent to POST reasoning events)
- [ ] Add ability for user to draw annotations on the 3D view + send back
      to agent as feedback (e.g. "fix this" circle on a floating object)
- [ ] Add multi-session support (one server, multiple agent sessions)
- [ ] Add authentication for multi-user deployment
- [ ] Build the Three.js variant (Track D) that uses Blender camera as default

### Track L: Render performance optimization (target: rolling) — NEW (session 4)

- [x] ~~Add 'previz' quality preset (BLENDER_WORKBENCH, ~0.2s/frame)~~ — done (session 4)
- [x] ~~Benchmark Workbench vs EEVEE vs Cycles at various resolutions~~ — done (session 4)
- [ ] Investigate Workbench matcap mode for material-like preview without PBR cost
- [ ] Add a "previz animation" workflow: render at 12fps instead of 24fps
      (halves render time, sufficient for previz)
- [ ] Test rendering with reduced bounces for Cycles (previz quality)
- [ ] Investigate persistent Blender bridge (Track H) for sub-second iteration
- [ ] Add adaptive sampling: render at 1 sample, identify noisy regions,
      re-render only those at higher samples

### 2026-09-08 (session 4): Defense-in-depth verification (VLM + structural validator + multi-angle)
**Context**: VLM missed an upside-down coffee table in wide-angle renders.
The bug was geometric (legs poking through table top) and not visible from
the default camera angle.
**Decision**: Use three-layer defense for scene verification:
1. Multi-angle viewport capture (front/side/top/persp) — see all sides
2. Close-up views + specific VLM prompts — catch visible issues
3. Structural validator (validate_scene.py) — catch geometric issues
**Rationale**: VLMs are good at visible issues but bad at geometric ones.
Deterministic bounding-box checks catch the class of bugs VLMs miss.

### 2026-09-08 (session 4): Workbench 'previz' as default iteration engine
**Context**: EEVEE_NEXT cold-start is 28s; warm is 2-5s. Cycles is 50s/frame.
For "did this op look right?" checks, all are too slow.
**Decision**: Added 'previz' quality preset that forces BLENDER_WORKBENCH
(solid shading, ~0.2s/frame, 14× faster than draft EEVEE).
**Rationale**: For previz, we don't need PBR materials/lighting — just
geometry verification. Workbench is strictly faster. Switch to draft/
preview/final only when PBR is needed.

### 2026-09-08 (session 4): E2E live viewer via SSE + file watcher
**Context**: User wanted the 3D preview to be "e2e working" — connected to
the agent environment, showing live updates as the agent works.
**Decision**: Built agent_server.py (HTTP + SSE + file watcher) + viewer/live.html
(3-tab interface with progress, scene, screenshots). Agent just copies .glb
to workdir + POSTs events; file watcher auto-notifies viewers of .glb changes.
**Rationale**: Zero agent overhead beyond what it's already doing. The viewer
is the user's window into the agent's work — no manual refresh needed.

### 2026-09-08 (session 4): Poly Haven direct API integration (not mirror, not paid addon)
**Context**: Need CC0 assets (HDRIs, models, textures) for previz scenes.
Poly Haven has ~2,400 CC0 assets + a public key-less API.
**Decision**: Built polyhaven.py that calls the Poly Haven API directly
from bpy. No mirroring, no paid addon. Cache to POLYHAVEN_CACHE dir,
md5-verified. Default 2k resolution (safe for 4GB RAM).
**Rationale**: API is free, key-less, CC0. Mirroring 2,400 assets is
wasteful. The paid addon is GUI-only (not headless-friendly). Direct API
calls from bpy give the agent full programmatic control.

### Track P: physics layer (opened session 13, rolling)

- [x] ~~physics_place module (settle/place/oracle/gate) + design doc v3~~
- [x] ~~Usability program to convergence (4 rounds, 9 subjects)~~
- [x] ~~Crossing entering-classifier in placement_lib~~
- [x] ~~Usability convergence RE-PROVEN on canonical HEAD (session-14b
      rounds E+F: 5 subjects, 0 S1; round-E bug batch regression-locked
      T5r/s/t/u)~~
- [ ] Geometric pre-lift repair mode refinement (deep/wedged pens eject
      sideways today; loud + recoverable, but not convergent alone).
      Session-14b v1 rule sketch: refuse when up AND down ejection
      windows are blocked (raycast both ways at pen depth); both round-E
      wedge sightings traced to fixture bugs — real-build demand still
      to be demonstrated before designing the gate
- [ ] Oracle lateral reachability (path-witness) — round-E subject B
      independently hit it (workaround: move_to approach plane + audit;
      now documented in AGENTS). Natural v2
- [ ] FELL_BELOW/TOPPLED precedence: a large drop that also tips reads
      TOPPLED (tilt checked first); consider FELL_BELOW precedence when
      disp_z dominates (round-F subject F2 sighting, semantics choice)
- [ ] Compound-concave receiver helpers (auto-decompose bowls/cabins
      into convex colliders for honest oracle/settle inside cavities)
- [ ] AGENTS.md gotcha renumber pass (cosmetic duplicates)
- [ ] Gate as a standard finalize gate in build SOPs (shot_pipeline —
      PREVIZ repo — / build scripts run physics_gate fail_hard at the end)
