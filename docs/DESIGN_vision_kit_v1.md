# DESIGN — blender-vision-kit v1 (vision-first variant)

> Status: DRAFT-1 (pre-critique). Decision IDs D1–D14. The critique mandate:
> attack every decision; find semantic collisions with the upstream kit's
> laws; propose amendments. Nothing here is final until the audit passes.

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
  LOOK floating at the wrong angle). The upstream law "VLM noise vs
  reality — verify geometric claims programmatically" becomes MORE
  important, not less, and must be enforced by the tool surface, not just
  the doc.
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
Cost: upstream commit graph not carried; accepted.
- Upstream: https://github.com/zmpc01/blender-agent-kit (unchanged)
- Variant: https://github.com/zmpc01/blender-vision-kit + GitLab mirror

### D2 — Perception doctrine: "EYES TRIAGE, GATES DECIDE"
Successor to upstream's "vision triages WHERE; numbers decide WHAT; never
blend the two roles" (that law stays, restated for the embodied eye):
1. Native vision (Read PNG) is the PRIMARY eye for: composition, framing,
   semantics, hue, "anything grossly wrong", object identity/layout.
2. Programmatic gates (`validate_scene.py`, `audit`, `physics_gate`,
   `scene_schema --with-bounds`) are the ONLY deciders for mm-class
   geometry: penetration, float, contact, exact placement.
3. ASCII vision packs + z-ai VLM API are DEMOTED to escalation paths
   (kept in tree; useful for text-only sub-agents or context-blind
   handoffs), removed from the primary loop and the primary doc.
Anti-law (new): "Never trust a visual impression on a question you can
compute; never compute a verdict on a question only vision can see
(does the framing FEEL right, is the mood wrong)."

### D3 — Vision-tuned output defaults (numbers changed, mechanisms reused)
| Surface | Upstream | Variant | Why |
|---|---|---|---|
| `--quality previz` | 240×135 | **480×270** | readable geometry for an embodied eye; still <1s workbench |
| viewport_capture default | 480×360 | **640×480** | grid cells the eye can actually read |
| keyframe_contact_sheet default | 320×240 | **480×360** | motion reads (mid-stride vs fallen) need pixel mass |
| render_viewport op (patch) | 480×360 | **640×480** | same |
Cost: workbench render time scales with pixels; verify ≤1s/frame at
480×270 and ≤2s at 640×480 on llvmpipe before committing. If >2s, halve.
Mechanisms (MATERIAL color, Standard view transform, AA-off default, JPEG
default) unchanged — they are render-economy truths, not blind-agent
artifacts.

### D4 — New tool `scripts/look.py` — the ONE vision-loop command
Bundles the 3-command perception round (viewport_capture +
validate_scene + scene_schema summary) into ONE blrun invocation
(one cold start instead of three; ~10–20s saved per iteration):
```
blrun.sh --background --python scripts/look.py -- \
  --scene my_scene | --load-blend s.blend \
  [--angles front,side,top,persp] [--engine workbench] \
  [--grid | --no-grid] [--annotate] [--closeup Object] \
  [--output output/scene/look]
```
Always (by construction): prints a compact text verdict — object count,
scene bounds, validator issues (P0/P1/P2), floating/penetration summary,
engine, per-image file paths — next to the images it writes. The agent
cannot look without also seeing the numbers (forced pairing, D6).
NOT a new mutation surface (apply_patch stays the act layer); look.py is
the perceive+verify layer only. Reuses viewport_capture/validate_scene
internals via imports — no logic duplication.

### D5 — Annotated renders (`--annotate` on look.py + viewport_capture)
Overlays that make the eye honest (opt-in flag, default ON in look.py):
- 1m ground-grid lines + axis gnomon at origin (scale/orientation cues)
- object index labels (billboard text, N-scaled) for meshes above a size
  threshold — kills "which blob is which" ambiguity
- flagged-object bbox wireframe (validator issues get red boxes)
Plus `--closeup <obj>`: auto-framed macro render of one object (computes
world bbox, positions a temp camera at 1.5× diagonal, renders, cleans up)
— the macro-crop gotcha (upstream #22) becomes a flag instead of manual
camera math. Reuses viewport_capture's temp-camera machinery.

### D6 — Anti-self-sycophancy forced pairing
1. look.py prints validator verdicts BESIDE images (by construction).
2. Every image written gets a one-line "vision-readiness" header: luma
   mean/clipped%, subject coverage estimate, resolution — printed so the
   agent self-checks before trusting (extends upstream `_warn_if_clipped`).
3. Variant AGENTS.md core law: any mm-class claim in a vision read MUST be
   confirmed by audit/validate/schema before acting on it; conversely a
   PASSING gate does not mean the shot looks right (composition is still
   vision's job). Two columns, never blended (upstream law restated).

### D7 — Blind machinery demoted, not deleted
`ascii_vision.py`, `vlm_critique.py`, `ascii_read.py` stay in tree and
keep their tests (text-only escalation; zero regression risk). Variant
AGENTS.md moves them to an "Escalation paths" section; the z-ai VLM API
call disappears from the canonical workflow (the embodied eye replaces
it). `kb/ascii_vision.md` stays with a demotion header.

### D8 — Crowd system: compose with sibling repo `blender-crowd-kit`
Upstream forked crowd sim to zmpc01/blender-crowd-kit (M2, pre-v1);
in-kit `scripts/crowd/` is an import-error stub. Variant does NOT vendor
crowd (pre-v1 churn); it:
1. Documents the composition in AGENTS.md (clone sibling, sys.path
   insert, `from scripts.crowd import CrowdProject, Population, bake,
   apply_to_scene`).
2. Ships the crowd VISION workflow: how to look at a crowd sim — GN
   instanced renders at vision-tuned resolutions, agent-count sanity via
   components/schema, motion contact sheets for gait checks, placement
   of crowd caches in the look loop.
3. Tests crowd end-to-end in usability wave T3 (see D14) using the
   sibling repo, reporting friction back to both repos.
Revisit vendoring when crowd-kit hits v1 (upstream already plans M3
vendor-back; the variant should track that, not preempt it).

### D9 — Loop-speed doctrine documented (not new machinery)
The act layer already supports one-invocation-many-mutations patch chains
with render_viewport ops interleaved. Variant AGENTS.md promotes this to
THE canonical edit loop: `apply_patch.py` chains mutations + look ops;
`look.py` for the perceive step; never re-run a scene build to inspect.
No new orchestration code in v1 — documentation + existing op surface.

### D10 — Variant AGENTS.md structure
Full rewrite of the consumer doc, keeping upstream law NUMBERS where a
law survives (traceability), deleting sections that teach remote-VLM
stabilization (sycophancy doctrine, pack-first protocol, z-ai CLI), and
adding: "The vision loop" (top), vision-specific gotchas (new numbering
continues after upstream's last law for NEW laws), escalation section.
Target size ≤40% of upstream's 1384 lines — the vision agent needs less
perception remediation but ALL the Blender-mechanics laws (kept).
`.agents/SKILL.md` rewritten for variant work; kb/ kept + new
`kb/vision_loop.md` (look.py protocol, annotation rules, readiness
scores).

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
`.blender-home` entries; README documents the symlink option and the
git-rewrite hazard; `run.sh --scope-check` extended to WARN when tools/
is a real dir containing only the two scripts (the broken-symlink
signature).

### D13 — Identity, README, upstream relation
README: lineage (fork of blender-agent-kit @3c0c60d), what changed and
why (one paragraph + table), when to use which kit (blind agent →
upstream; vision agent → variant). Upstream gets credit + a PR for D11
+ any blind-agent-relevant fixes surfaced by usability waves. No
rebranding of shared mechanics: function names, env vars, output
layouts stay identical where possible so skills transfer between kits.

### D14 — Test protocol: usability waves (the core quality loop)
Sub-agent waves act as CONSUMER VISION AGENTS (they have the same Read
image capability). Each wave: given ONLY the variant AGENTS.md + kit
tree (no orchestrator context), build a scene to a brief, report every
friction point (doc gaps, tool confusions, false assumptions, wasted
invocations, vision misreads). Scenes simple→complex:
- T0 smoke: cube on floor (README quick-start path verbatim)
- T1 placement circuit: table + 4 chairs seated (seat_at), lamp on table
  (place_on), mug snap_z, audit chain, closeup verification (D5)
- T2 interior room: scene_interior_room pattern + physics_settle + gate
- T3 crowd: sibling crowd-kit concourse, bake, apply_to_scene, vision
  checks on instanced crowd (D8)
- T4 animated: capsule walk cycle + keyframe contact sheet review + glTF
  export + viewer handoff
Success criteria per wave: (a) zero source-reading to complete the brief
(doc sufficiency), (b) no silent failures, (c) every vision claim in the
wave report backed by a gate/number where mm-class, (d) friction list
with severity. Orchestrator fixes kit+doc between waves; re-run T0+T1 as
regression after each fix batch; waves continue until a wave completes
with only P2 friction. Minimum 3 waves even if wave-1 is clean.

## 2. Non-decisions (explicitly out of scope v1)
- No new animation/mutation ops (apply_patch surface frozen).
- No diff-look / side-by-side tooling (nice-to-have; defer).
- No crowd vendoring (D8). No new viewer work. No engine/preset matrix
  changes beyond D3 numbers. No upstream AGENTS.md edits (variant doc
  only) — upstream PRs limited to mechanical fixes (D11, test fixes).
- USD/GPB paths untouched.

## 3. Risks
| Risk | Mitigation |
|---|---|
| Vision agents over-trust renders (self-sycophancy) | D5 annotations, D6 forced pairing + readiness headers, D2 law |
| Bigger renders slow the loop | D3 cost gates measured before commit; halve if >2s |
| Doc rewrite loses upstream's hard-won laws | D10 keeps law numbers; critique wave audits for lost laws |
| look.py duplicates viewport_capture logic | D4 mandates imports, not copies |
| Crowd-kit pre-v1 churn breaks wave T3 | D8 composition documented as best-effort; T3 failure = friction report, not kit bug |
| Sub-agents lack image vision in some models | D7 keeps ASCII escalation path; wave briefs specify vision-required |
