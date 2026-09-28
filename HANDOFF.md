# HANDOFF.md — blender-vision-kit (immediate next-session scope)

> Session close: 2026-09-28 (M0–M2 complete, M3 wave 1 complete).
> PLAN.md = long-horizon tracker. Upstream project HANDOFF preserved at
> `docs/UPSTREAM_HANDOFF_snapshot.md`.

## State at handoff

- Repo: https://github.com/zmpc01/blender-vision-kit (main) + GitLab
  mirror remote `gitlab` (oauth2 glpat; WAF-blocks ~1/3+ pushes — retry
  loop; GitHub is source of truth). Fresh-root repo: base tree =
  upstream @3c0c60d, docs synced from upstream@01dd147 (parallel session
  condensed upstream's AGENTS.md/SKILL.md mid-session — handled, merged).
- Toolchain: NOT committed. `tools/` + `.blender-home` are symlinks to
  `/home/z/work/blender-agent-kit/tools` (Blender 5.2.2 provisioned
  there by install.sh). In a FRESH sandbox: `./install.sh` (D11
  chunked-download fallback included), then re-link or let install.sh
  provision locally.
- Design: `docs/DESIGN_vision_kit_v1.md` DRAFT-2 — D1–D14 with audit
  5-a amendments. All decisions FINAL except where waves amend.
- Vision tools: `scripts/look.py` + `scripts/annotate.py` (see
  kb/vision_loop.md). Regression: `tests/test_v1_look.py` 27/27 GREEN.
- Docs: AGENTS.md is the vision-first consumer guide (LAW MAP included);
  .agents/SKILL.md has VARIANT CONTEXT up top; README frames the fork.
- Upstream snapshots: docs/UPSTREAM_{PLAN,HANDOFF,FINDINGS,SOP}_snapshot.md.

## Worklog + artifacts

- Multi-agent worklog: /home/z/work/worklog.md (NOT pushed — replicate
  key entries into the repo worklog.md if lost; repo worklog.md has the
  implementation entries).
- Wave-1 friction reports: .agents/research/VISION_WAVE1_report.md
  (T0/T1/T2 consumer-agent usability tests).
- Absorption briefs: worklog entries 2-a (demo repo) + 2-b (kit tool
  surface); design audit 5-a (DRAFT-1 critique).

## Immediate next-session scope (M3 continuation)

1. **Wave-1 fixes** (from .agents/research/VISION_WAVE1_report.md):
   triage each friction item (infra vs usability, P0–P2), fix doc/tool
   surface, re-run T0+T1 regression.
2. **Wave 2**: T4 animated (capsule walk + keyframe contact sheet +
   glTF export + viewer) + T3 crowd via sibling blender-crowd-kit
   (INFRA-GATED: provision crowd-kit toolchain first — clone, install.sh
   or symlink tools/; verify bgyss wheel builds/loads on 5.2; T3 is
   EXCLUDED from the wave-termination criterion per D14).
3. **Wave 3**: fresh-eyes validation wave (different archetype briefs);
   termination = a wave with only P2 usability friction.
4. After waves: distill learnings into AGENTS.md gotchas (continue
   numbering 117+), kb/vision_loop.md, SKILL.md; then M4 wrap-up.

## Sandbox / environment notes for the next session

- Work ONLY in /home/z/work/ (watchdog reverts /home/z/my-project/).
- Write tool works under /home/z/ only — /home/z/work/ is fine.
- Blender binary: tools/blender/blender via blrun.sh ONLY (raw runs
  lack libEGL/Xvfb env and die silently; raw binary DOES propagate
  script exit codes — blrun does not).
- EEVEE: run `./scripts/blrun.sh --warm-cache` once per container
  (~30s) before first EEVEE use; workbench needs nothing.
- Tests: `./scripts/blrun.sh --background --python tests/test_v1_look.py --`
  and `bash run.sh --scope-check`.
- Git: rebase before push (a parallel session pushed mid-session once
  already); never force; GitLab needs retry loops.

## Known gaps / open questions

- blrun.sh swallows look.py's exit 3 — acceptable (verdict lines are
  greppable) but a `--propagate-exit` blrun flag is a nice upstream PR.
- Crowd T3 infra unverified (bgyss wheel on Blender 5.2 / this sandbox).
- look.py labels are indexes; named-label mode is backlog.
- The `viewport` preset (960×540 FLAT) is unchanged for vid2vid — if a
  wave confirms vision agents misuse it for geometry checks, document
  harder or rename.
