# DESIGN — blender-vision-kit v1 (vision-first variant)

> Status: DRAFT-2 — incorporates design audit 5-a (all 5 required
> amendments + per-decision verdicts). Change log vs DRAFT-1 at §4.
> Still open to critique round 2; implement only after FINAL stamp.

## 0. Context and thesis

Upstream `blender-agent-kit` was built for BLIND agents: perception ran
through `ascii_vision.py` text packs (primary eye) + `z-ai vision` CLI API
calls (secondary eye), with renders kept tiny (240×135 previz, 480×360
viewports, 320×240 motion sheets) for token economy. Its doc doctrine —
"pack-first for geometry/grounding/count/layout; VLM for semantics" — and
dozens of laws exist to stabilize a remote VLM API (sycophancy, hallucinated
geometry, black-frame audits) that the agent does not embody.

A VISION-CAPABLE agent (GLM-class, native image understanding via its Read
tool) inverts the perception economics:

- **The eye is free and embodied.** `Read(PNG)` renders the image into the
  agent's own context. No API call, no external VLM, no ASCII pack as
  primary path. The agent SEES the render it just made.
- **The failure mode flips.** The blind kit fought VLM sycophancy and
  hallucination (an untrustworthy remote eye). The vision agent's risk is
  **self-sycophancy**: trusting its own visual impression on mm-class
  geometry questions (12mm penetration is invisible; a grounded actor can
  LOOK floating at the wrong angle). The upstream law "verify geometric
  claims programmatically" becomes MORE important, not less, and must be
  enforced by the tool surface, not just the doc.
- **Resolution economics flip.** Tiny renders starve a vision agent
  (240×135 is readable but under-leveraged). Bigger, labeled, annotated
  images cost ~nothing extra to the agent but make the eye honest.
- **The loop bottleneck moves.** Perception is no longer the slow step;
  Blender cold-starts are (~3–8s per invocation). The vision agent looks
  OFTEN, so each look should cost ONE invocation, not three.

Thesis: same hybrid architecture (bpy script/JSON patch → blrun.sh →
Blender → verify → iterate), same deterministic gates, but the perception
layer, defaults, and doc doctrine are re-tuned for an agent that sees.

## 1. Decisions

### D1 — Fork vehicle: NEW REPO `blender-vision-kit`, fresh root commit
GitHub cannot fork an own-account repo; and push protection blocks
re-pushing upstream's vendored history (historical HANDOFF.md tokens).
Fresh root commit carries the exact upstream tree (`@3c0c60d`) and
references upstream as lineage holder. Rationale: this is a VARIANT
product (different doctrine), not a lineage fork; upstream keeps history.
- Upstream: https://github.com/zmpc01/blender-agent-kit (unchanged)
- Variant: https://github.com/zmpc01/blender-vision-kit + GitLab mirror

### D2 — Perception doctrine: "EYES TRIAGE AND COMPOSE; GATES DECIDE GEOMETRY"
(5-a: "primary eye" phrasing invites acting on visual float impressions —
restated; four uncovered failure modes added as laws L1–L4.)
1. Native vision (Read PNG) is the EYE for: composition, framing,
   semantics, hue, "anything grossly wrong", object identity/layout.
   A visual float/penetration impression is a HYPOTHESIS until a gate
   confirms it.
2. Programmatic gates (`validate_scene.py`, `audit`, `physics_gate`,
   `scene_schema --with-bounds`) are the ONLY deciders for mm-class
   geometry: penetration, float, contact, exact placement.
3. ASCII vision packs + z-ai VLM API are DEMOTED to escalation paths
   (kept in tree; useful for text-only sub-agents or context-blind
   handoffs), removed from the primary loop and the primary doc.
4. Anti-law: "Never trust a visual impression on a question you can
   compute; never compute a verdict on a question only vision can see."
Vision-agent failure-mode laws (new, trained into every workflow section):
- **L1 Image budget**: context flooding is the vision agent's version of
  the blind kit's token economy. Default look = ONE grid image, not N
  files; closeups only on flagged subjects; stale look images are
  discarded from the loop (re-look, don't hoard).
- **L2 Chirality**: top/front views are mirrorable in an agent's mental
  model. Confirm handedness via the axis gnomon before acting on any
  left/right instruction.
- **L3 Overlay trust**: annotations (red boxes, grids, labels) are
  RENDER-TIME OVERLAYS, not scene state. A missing red box is NOT proof
  of correctness (the validator only sees bbox pairs >5% overlap); a red
  box IS validator output — numbers, not eyes — and may be acted on.
- **L4 Color from schema**: never judge absolute color from a render;
  read material color from scene_schema. (Workbench Standard/MATERIAL is
  calibrated for hue comparison, not absolute values; EEVEE shifts more.)

### D3 — Vision-tuned output defaults (numbers changed, mechanisms reused)
| Surface | Upstream | Variant | Why |
|---|---|---|---|
| `--quality previz` | 240×135 | **480×270** | readable geometry for an embodied eye |
| viewport_capture default | 480×360 | **640×480** | grid cells the eye can actually read |
| keyframe_contact_sheet default | 320×240 | **480×360** | motion reads need pixel mass |
| render_viewport op (patch) | 480×360 | **640×480** | same |
Cost margin verified in audit 5-a via kb/render_speed.md: Workbench
AA-OFF at 960×540 ≈0.05s/frame — targets (≤1s @480×270, ≤2s @640×480)
sit far under the proven ceiling. Still measure at implementation and
record in kb/vision_loop.md. Mechanisms (MATERIAL color, Standard view
transform, AA-off default) unchanged — render-economy truths, not
blind-agent artifacts. File format: look.py defaults PNG (the Read tool
is format-agnostic; PNG stays lossless for annotation overlays).

### D4 — New tool `scripts/look.py` — the ONE vision-loop command
Bundles the perception round (viewport_capture + validate_scene +
schema manifest) into ONE blrun invocation (one cold start instead of
three; ~10–20s saved per iteration):
```
blrun.sh --background --python scripts/look.py -- \
  --load-blend s.blend | --scene my_scene \
  [--angles front,side,top,persp] [--engine workbench] [--frame N] \
  [--grid | --no-grid] [--annotate | --no-annotate] [--labels N] \
  [--closeup Object] [--output output/scene/look]
```
- **Default state carrier is `--load-blend`** (5-a Q7-1: `--scene`
  REBUILDS and silently discards patch-applied state — RB settle, manual
  edits). `--scene` mode is documented as "fresh iteration only".
- **Object-id manifest in every verdict** (5-a): id/type/dims/world
  centroid per mesh — the ids the next patch needs, without a second
  schema call. This is what makes the bundle complete.
- **`--frame N`** single-frame evaluation (capture/schema only take
  counts; animation looks need a frame).
- **Exit-code semantics**: P0 validator issues → exit 3 (blrun's
  fail-closed gate passes it through); success → 0. A look that sees a
  P0 FEELS like a failure to the shell.
- Always (by construction): compact text verdict — engine, frame, scene
  bounds, validator issues (P0/P1/P2), floating/penetration summary,
  per-image paths + vision-readiness header (D6) — printed BESIDE the
  images. Forced pairing is structural, not disciplinary.
- NOT a new mutation surface (apply_patch stays the act layer).
- Implementation: imports `viewport_capture.render_angle`,
  `validate_scene.validate_scene`, schema internals — all verified
  importable (no module-level side effects, argparse gated in main()).
  No logic duplication.

### D5 — Annotated renders (default ON in look.py; `--no-annotate` to strip)
(5-a amendments: labels capped; boxes tied to validator run; overlay
persistence banned.)
- 1m ground-grid lines + axis gnomon at origin — real thin-box geometry
  (~50 LOC; empties don't render in workbench). Kills chirality/scale
  misreads (pairs with L2).
- Object index labels: **top-N by bbox diagonal (default 8, `--labels N`
  to tune)** — FONT text objects, billboarded via TRACK_TO, N-scaled
  from scene diagonal (~120 LOC). No hundred-label clutter on crowds.
- Validator-flagged objects get red bbox wireframes (~40 LOC; edge-loop
  mesh from the validator issue list). Only drawn when the validator
  actually ran in the same look (else silently omitted — the verdict
  header says which).
- `--closeup <obj>`: auto-framed macro render (world bbox → temp camera
  at 1.5× diagonal, renders, cleans up). Upstream gotcha 22 becomes a
  flag instead of manual camera math.
- **Law: annotations are render-time-only and NEVER saved** — a
  `--save-blend` in the same process must not persist grid/label/box
  geometry (build annotations on a discardable layer; delete before any
  blend write).

### D6 — Anti-self-sycophancy forced pairing
1. look.py prints validator verdicts BESIDE images (by construction).
2. Every image gets a one-line "vision-readiness" header: luma
   mean/clipped %, subject-coverage estimate, resolution — extends
   upstream `_warn_if_clipped`; printed for EVERY render so the agent
   self-checks before trusting.
3. Two-column law (restated): a mm-class claim needs a number; a
   PASSING gate doesn't make the shot LOOK right. Composition stays
   vision's job; geometry stays the gates' job.

### D7 — Blind machinery demoted, not deleted
`ascii_vision.py`, `vlm_critique.py`, `ascii_read.py` stay in tree and
keep their tests (text-only escalation; zero regression risk). Variant
AGENTS.md moves them to an "Escalation paths" section; the z-ai VLM API
call disappears from the canonical workflow. `kb/ascii_vision.md` gets a
demotion header.

### D8 — Crowd system: compose with sibling repo `blender-crowd-kit`
Upstream forked crowd sim to zmpc01/blender-crowd-kit (M2, pre-v1).
(5-a amendments: stub-shadowing and toolchain facts fixed; T3 excluded
from termination rule.)
1. **Delete the variant's `scripts/crowd/` ImportError stub** so the
   documented import cannot shadow the sibling repo's real package
   (5-a Q5: `from scripts.crowd import …` resolves by sys.path order
   and the stub wins otherwise). Composition recipe pins the import to
   an explicit sibling path inserted at sys.path[0].
2. AGENTS.md documents the composition (clone sibling, sys.path insert,
   `from scripts.crowd import CrowdProject, Population, bake,
   apply_to_scene`).
3. Crowd VISION workflow shipped: how to look at a crowd sim — GN
   instanced renders at vision-tuned resolutions, agent-count sanity
   via schema/components, motion contact sheets for gait checks.
4. Infra prerequisites for wave T3 (done BEFORE the wave, so it tests
   usability, not infra): crowd-kit toolchain provisioned via D12's
   shared symlink; bgyss wheel availability verified (rebuild via
   crowd-kit's own build path if the prebuilt wheel is absent).
5. T3 is excluded from the wave-termination criterion (D14) — a T3
   infra failure is reported to BOTH repos, never blocks kit waves.

### D9 — Canonical state-carrying loop (5-a Q7-1: the big missing decision)
THE loop, stated in doc + tool help:
```
apply_patch.py --patch fix.json --save-blend work.blend   # ACT (one cold start)
look.py --load-blend work.blend                            # PERCEIVE+VERIFY
```
- `--scene` rebuild mode is for FRESH iterations only; never rebuild to
  inspect after patches (rebuilds discard RB settle + manual edits).
- Batched mutations in ONE patch chain beat many small patches (cold
  start per invocation dominates).
- `look.py --closeup` after a look verdict answers WHAT; the grid
  answers WHERE (binds upstream gotcha 22 to the new surface).

### D10 — Variant AGENTS.md structure + LAW MAP
Full rewrite of the consumer doc. (5-a: "keep numbers" alone is
unauditable — require a LAW MAP table.) Contents:
- "The vision loop" top section (D9 loop, look.py, image budget L1).
- LAW MAP table: upstream law # → variant disposition (kept-same-number
  / renumbered / deleted + one-line reason / superseded by which variant
  law). Mechanics laws (Blender API, physics, glTF, git) kept; remote-VLM
  stabilization laws deleted or compressed into L1–L4; placement/physics
  laws kept verbatim.
- Vision-specific gotchas continue numbering after upstream's last law.
- TARGET REBASED (parallel-session event 2026-09-28): upstream condensed
  AGENTS.md to 29K chars (454 lines) + SKILL.md to 16K and synced both
  into this repo (commit 6f1aca8, upstream@01dd147). The variant rewrite
  starts from THAT condensed base: keep its tool reference + mechanics
  laws; rewrite the perception sections (canonical workflow steps 3/5,
  gotchas 20-27) into the vision loop; add L1–L4 + law map.
`.agents/SKILL.md` rewritten for variant work; new `kb/vision_loop.md`
(look.py protocol, annotation rules, readiness scores, measured timings).

### D11 — install.sh defensive fix: chunked download fallback
This session reproduced upstream's stall: single-stream curl hung at 0%
for minutes; the kit's own `tools/chunked_dl.sh` (16 parallel ranged
chunks) assembled 383MB in ~20s. Variant install.sh detects a stalled
(<1% in 60s) or failed download and falls back to chunked_dl.sh
automatically. Upstream-worthy fix; submit PR upstream after validation.

### D12 — Toolchain symlink hygiene (sandbox reality)
blrun.sh resolves REPO from its own script path; `tools/` can be
symlinked to a shared provisioned toolchain, BUT git operations rewrite
symlinked dirs (checkout of paths under a symlink replaced it with a
real dir twice this session). Variant: `.gitignore` carries `tools/` +
`.blender-home`; README documents the symlink option and the git-rewrite
hazard; `run.sh --scope-check` WARNs when `tools/` is a real dir
containing only the two scripts (the broken-symlink signature).

### D13 — Identity, README, platform scope, upstream relation
README: lineage (fork of blender-agent-kit @3c0c60d), what changed and
why (one paragraph + table), when to use which kit (blind agent →
upstream; vision agent → variant). **Platform scope stated: Linux
x86_64 only** (manylinux wheel, Debian amd64 libEGL debs, Xvfb — same
as upstream; not a variant regression). Upstream gets credit + a PR for
D11 + any blind-agent-relevant fixes surfaced by usability waves. No
rebranding of shared mechanics: function names, env vars, output layouts
stay identical where possible so skills transfer between kits.

### D14 — Test protocol: usability waves (the core quality loop)
Sub-agent waves act as CONSUMER VISION AGENTS (they have the same Read
image capability). Each wave: given ONLY the variant AGENTS.md + kit
tree (no orchestrator context), build a scene to a brief, report every
friction point. Ladder:
- T0 smoke: cube on floor (README quick-start path verbatim)
- T1 placement circuit: table + 4 chairs seated (seat_at), lamp on
  table (place_on), mug snap_z, audit chain, closeup verification
- T2 interior room: scene_interior_room pattern + physics_settle + gate
- T3 crowd (INFRA-GATED, excluded from termination): sibling crowd-kit
  concourse, bake, apply_to_scene, vision checks on instanced crowd
- T4 animated: capsule walk cycle + keyframe contact sheet review +
  glTF export + viewer handoff
Friction taxonomy (5-a): each item tagged `infra` (env/toolchain) or
`usability` (doc/tool surface), plus class tags: doc-gap / tool-gap /
vision-misread (agent saw wrong, gate corrected) / invocation-waste /
false-assumption. Severity P0 (blocked) / P1 (workaround existed) /
P2 (polish).
Wave variance (5-a): each wave varies the scene archetype; at least one
wave must run the README quick-start VERBATIM before any other brief.
Termination: waves continue until a wave completes with only P2
usability friction (T3 excluded). Minimum 3 waves even if wave-1 is
clean. Orchestrator fixes kit+doc between waves; re-run T0+T1 as
regression after each fix batch.

## 2. Non-decisions (explicitly out of scope v1)
- No new animation/mutation ops (apply_patch surface frozen).
- No diff-look / side-by-side tooling (defer).
- No crowd vendoring (D8). No new viewer work. No engine/preset matrix
  changes beyond D3 numbers. No upstream AGENTS.md edits (variant doc
  only) — upstream PRs limited to mechanical fixes (D11, test fixes).
- USD paths untouched.

## 3. Risks
| Risk | Mitigation |
|---|---|
| Vision agents over-trust renders (self-sycophancy) | D5 annotations, D6 forced pairing + readiness headers, D2 law + L1–L4 |
| Bigger renders slow the loop | D3 measured before commit (audit shows huge margin) |
| Doc rewrite loses upstream's hard-won laws | D10 LAW MAP auditable line-by-line |
| look.py duplicates viewport_capture logic | D4 imports verified feasible (5-a Q1) |
| Annotation geometry leaks into saved .blend | D5 render-time-only law + delete-before-save |
| State loss via silent scene rebuild | D9 canonical load-blend loop; --scene documented as fresh-only |
| Crowd-kit pre-v1 churn breaks T3 | D8 infra pre-provisioned; T3 excluded from termination (D14) |
| Sub-agents lack image vision in some models | D7 ASCII escalation path; wave briefs specify vision-required |

## 4. Change log vs DRAFT-1 (from audit 5-a)
- D2 restated ("triage and compose"), + L1–L4 failure-mode laws.
- D4: object-id manifest, `--frame`, `--no-annotate`, exit-code 3 on P0,
  `--load-blend` default; import feasibility verified.
- D5: labels top-N capped, red boxes only when validator ran,
  annotations-never-saved law.
- D8: stub deletion, pinned import, infra pre-provision, T3 excluded
  from termination.
- D9: canonical patch→save-blend→look(--load-blend) loop pinned.
- D10: LAW MAP required.
- D13: Linux-only platform scope stated.
- D14: friction taxonomy (infra vs usability + class tags), wave
  variance spec, explicit termination rule.
