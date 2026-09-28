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

### M3 — Usability waves (IN PROGRESS)
- [x] Wave 1: T0 smoke + T1 placement circuit + T2 interior room (vision consumer agents, friction report)
- [ ] Fixes from wave 1 + regression (T0+T1 re-run)
- [x] Wave 2: T4 animated + T3 crowd (infra-gated, excluded from termination)
- [ ] Wave 3: fresh-eyes validation wave (archetypes varied) — ONLY-P2 gate
- [ ] Minimum 3 waves even if clean (D14); T3 excluded from termination

### M4 — Wrap-up & handover
- [ ] Distill wave learnings into AGENTS.md/SKILL.md/kb
- [ ] Upstream PR(s): D11 install.sh chunked fallback (+ any blind-agent-relevant fixes surfaced)
- [ ] /home/sync backup + GitHub/GitLab final push + HANDOFF final
- [ ] Release tag v0.1.0-vision

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
