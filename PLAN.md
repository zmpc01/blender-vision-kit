# PLAN.md — blender-vision-kit (long-horizon tracker)

> This repo is the VISION-FIRST VARIANT of blender-agent-kit. Upstream's
> project plan is preserved at `docs/UPSTREAM_PLAN_snapshot.md`. This
> plan tracks the VARIANT's long-horizon work across sessions.
> Companion: HANDOFF.md (immediate next-session scope only).

## Mission

Carve out a kit optimized for VISION-CAPABLE LLM agents: native image
understanding replaces ASCII packs + external VLM API as the primary
eye; defensive tool design targets the vision agent's OWN failure modes
(self-sycophancy, context flooding, chirality, overlay trust, color
constancy); the workflow is re-shaped around one-invocation look cycles.
**SCOPE DOCTRINE (session-4, owner-ruled): this kit is FOR agents with
native vision — period. No VLM bridges, no ascii vision packs, no
delegated-vision machinery. An agent that cannot see images natively is
upstream blender-agent-kit's audience, not ours.**
Full design: `docs/DESIGN_vision_kit_v1.md` (D1–D14, audited by 2
critique rounds — audit 5-a incorporated in DRAFT-2).

## Milestones

### M0 — Foundation (COMPLETE, 2026-09-28)
- [x] Sandbox setup, repo absorption (AGENTS.md 1384-line original + condensed base, SKILL.md, demo repo brief, kit tool surface brief)
- [x] Fork vehicle: new repo zmpc01/blender-vision-kit (GitHub push-protection forced fresh root; upstream keeps history) + GitLab mirror remote
- [x] Toolchain provisioned (Blender 5.2.2 via chunked_dl.sh — single-stream stall reproduced → D11 fix)
- [x] DESIGN DRAFT-1 → audit 5-a → DRAFT-2 (state carrier, manifest, L1–L4, LAW MAP, wave protocol)
- [x] Parallel-session event handled: upstream condensed docs synced in (6f1aca8); D10 base rebased onto condensed AGENTS.md

### M1 — Core vision tools (COMPLETE, 2026-09-28)
- [x] `scripts/annotate.py` — render-time annotation layer (D5): 1m grid, RGB gnomon (SW-offset, measured), top-N labels (per-angle aim, flat top, ground-slab exclusion — measured), red flag boxes; delete_annotation_layer with zero-residue guarantee (incl. FONT curve purge)
- [x] `scripts/look.py` — one-invocation perceive+verify (D4/D6): --load-blend default / --scene fresh-only, validator-first, readiness headers (RGB subject detection), object-id manifest, --closeup, exit 3 on P0/P1 (upstream severity parity — test-caught), verdict block
- [x] D3 vision-tuned defaults: previz 480×270, look 640×480, motion 480×360, patch render_viewport 640×480
- [x] D8: crowd stub deleted (import shadowing); D11: install.sh chunked fallback; D12: scope-check symlink warning
- [x] `tests/test_v1_look.py` — 27 checks ALL PASS (caught 5 real bugs)

### M2 — Docs rewrite (COMPLETE, 2026-09-28)
- [x] AGENTS.md full vision-first rewrite (460 lines): vision loop, L1–L4, two-column law, LAW MAP, escalation demotion, crowd composition, gotchas 111–116
- [x] kb/vision_loop.md (measured protocol + internals)
- [x] README.md variant framing; .agents/SKILL.md variant context
- [x] PLAN/HANDOFF variant docs (upstream snapshots preserved)

### M3 — Usability waves (COMPLETE except T3 infra-gate, 2026-09-28)
- [x] Wave 1: T0/T1/T2 (3 consumer agents) — 16 friction items → fix batch 1
- [x] Wave 1 regression: test_v1_look 27/27 GREEN
- [x] Wave 2a: T4 animated — 10 items → gotchas 117-119 + timing corrections
- [x] Wave 2b: T3 crowd — INFRA-GATED (crowd-kit Rust build stalls on this sandbox network; retry loop documented; rustup stable installed, vendor tree ready — resume needs network or bigger compute)
- [x] Wave 2c: T6 dense-scene proxy (120 agents, pure bpy) — floater caught 3 ways, 0 false positives; labels map + overflow hint added
- [x] Wave 3: T5 fresh-eyes doc validation — ship-arc fixed, exit-code lore corrected, error UX fixed
- [x] Orchestrator vision passes on all wave outputs (sub-agents cannot see PNGs in this harness)

### M5 — Perception tuning campaign (CURRENT, session 4, 2026-09-30)
Owner IS the vision agent; tuning targets what WE actually perceive best.
Sub-agent vision reality (re-confirmed empirically, sessions 2+3): this
harness strips images from sub-agent Read ("images not available in
sub-agent context"). Owner ruling: the kit does NOT compensate — no VLM
bridge, no ascii packs. QA division of labor: ALL visual verdicts belong
to the vision-native principal; sub-agents do NON-VISUAL QA only (code
review, script execution, textual output assertions). The VLM-bridged
consumer-wave pattern (wave 4a) is RETRACTED as a kit pattern; its
code-level finding (--frames BLOCKER) remains valid.

- [x] P1 COLOR doctrine: SETTLED (session-2, commit 961d81d) — annotations REQUIRE color (mono destroys labels/flags/gnomon); mono is a legitimate geometry second-look; workbench +1.0EV exposure default (98% dark-range fix); render_angle shading kwargs
- [x] P2 SHADE/LIGHT doctrine: SETTLED (same commit) — Standard/MATERIAL + shadows + cavity + exposure=1.0; MATCAP kills color identity; real EEVEE only config where cast shadows honestly reveal floating
- [x] P3 ANIMATION REP: SETTLED (session-3, motion_study.py) — trajectory (multi-angle) = path shape; onion-skin = speed/age/direction; filmstrip supplementary (vertical nuance weak, spin invisible); numeric table w/ POP/BURST flags; measured build defects: ghost-occlusion of polylines → split passes, coincident-ghost z-fight → skip, stale shadow buffer on hide toggles → shadows=off for traj pass; tests test_v2_motion 27/27
- [x] P4 TRANSIENT SCAN: SETTLED (session-3, transient_scan.py) — change radar (pixel diff, MAD floor) + state radar (validator per frame) + duration classification (≤40% = TRANSIENT, >60% = PERSISTENT baseline); new validator floor_penetration P1 (half-sunk was invisible); suspects strip start/PEAK/end/BAD; label-stick bug fixed (refresh_labels + frame pinning) and visually verified at f16 closeup; tests 27/27 + v1 suite 27/27
- [x] COURSE CORRECTION (session-4, commit ef86b85): all VLM/ascii vision-substitute machinery REMOVED (ascii_vision/ascii_read/vlm_critique/kb/ascii_vision + orphaned corpus line); image_metrics.py added as the numeric gate complement; scope doctrine codified
- [ ] P5 CORE-FLOW HARDENING (owner directive: placement included, crowd excluded — crowd still pre-v1 upstream): placement_lib end-to-end real build (T3-class) with visual verification by the principal; look/annotate/motion_study/transient_scan edge cases; install.sh + blrun.sh robustness (both failed reproducibly in this sandbox)
- [ ] Hardening waves: sub-agents run non-visual QA (fresh-context code review, script execution, textual assertions); principal makes every visual verdict; findings → fix batches; keep iterating
- [ ] T6 scene ships in kit (t6_transient.py) as the transient/label regression vehicle; consider --frames interplay doc (look --frames N vs animate n_frames)
- Note: blrun.sh without --background hangs silently (GUI-on-Xvfb startup) — defensive fix candidate (auto -b)

### M4 — Wrap-up & handover (complete for session 1)
- [x] Distill wave learnings into AGENTS.md/SKILL.md/kb
- [x] /home/sync backup + GitHub/GitLab final push + HANDOFF final
- [ ] Upstream PR(s): D11 install.sh chunked fallback (+ blind-agent fixes)

## Backlog (not committed to a milestone)
- Diff-look (before/after side-by-side renders in one image)
- Auto-pullback framing for large scenes (REJECTED v1 — see kb/vision_loop.md)
- Named-label mode (label text = object id, opt-in, for small scenes)
- Crowd-kit v1 vendoring decision (track upstream M3 vendor-back)
- vision-specific glTF "look-package" export (stills + glb + verdict json in one dir — partially exists via look output)

## Standing laws for this repo (sticky)
1. GIT IS THE DISK — push GitHub (+ GitLab best-effort, WAF-blocked) on every micro step. Never force push.
2. The design-audit gate: design docs get D-numbers and fresh-agent critique rounds BEFORE implementation.
3. Every new tool gets an in-Blender regression test in tests/ (suite convention: ALL PASS marker).
4. Vision claims about mm-class geometry require gate numbers (L-law discipline applies to the meta-agent too).
5. tools/ is a symlink to the shared provisioned toolchain — beware git rewrites it (scope-check warns).
