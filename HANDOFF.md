# HANDOFF.md — blender-vision-kit (immediate next-session scope)

> Session close: 2026-09-29 (session 3+4: M5 P1–P4 SETTLED, wave 4a done,
> fix batch 3 shipped). PLAN.md = long-horizon tracker. Upstream project
> HANDOFF preserved at `docs/UPSTREAM_HANDOFF_snapshot.md`.

## State at handoff

- Repo: https://github.com/zmpc01/blender-vision-kit (main, HEAD ~72cf468)
  + GitLab mirror gitlab.com/ansgareutychisO/blender-vision-kit (PAT
  namespace is ansgareutychisO — NOT zmpc01; WAF 403s are probabilistic,
  retry; verified synced @72cf468 session-3 close). GitHub is source of
  truth.
- Toolchain: NOT committed. In a fresh sandbox: `./install.sh`
  (D11 chunked fallback; the kit now OWNS tools/chunked_dl.sh — the old
  upstream symlink is gone). Blender 5.2.2 + libEGL + Pillow.
- M5 perception campaign (all MEASURED, see PLAN + kb/vision_loop.md):
  - P1 color: annotations REQUIRE color; mono = geometry second-look
  - P2 shade: Standard/MATERIAL+shadows+cavity, exposure +1.0EV default
  - P3 animation: `motion_study.py` (2×2 grid: trajectory row +
    onion-skin row + numeric MOTION-TABLE with POP/BURST/SPIN flags)
  - P4 transient: `transient_scan.py` (change radar + validator state
    radar + duration classification + suspects strip w/ BAD cells)
  - Label-stick bug FIXED (annotate.refresh_labels + frame pinning) —
    verified visually at f16 closeup
- Fixtures: T6 `t6_transient.py` (planted sink), T7 `t7_wave4_debug.py`
  (planted intersection transient + teleport pop + persistent hover).
- Regression: test_v1_look 27/27 + test_v2_motion 27/27 (in-Blender
  suites via `blrun.sh --background --python tests/...`).
- Wave 4a: consumer agent operated the full workflow, found both planted
  defects + a REAL blocker (hardcoded n_frames=64 — fixed in batch 3).
  Findings: docs/WAVE4A_findings.md. **METHODOLOGY RETRACTED (session-4
  course correction):** the VLM-bridge pattern is gone from the kit and
  from the wave protocol — this kit is for VISION-NATIVE agents only
  (commit ef86b85 removed all VLM/ascii machinery; the wave's code-level
  findings remain valid; its visual-verdict protocol does not).

## Immediate next-session TODO (in order)

1. (DONE session-3 close) GitLab synced @72cf468. Next session: only re-push new commits.
2. P5 CORE-FLOW HARDENING (owner directive, session-4): placement
   workflow end-to-end real build with the principal making every visual
   verdict; look/annotate/motion_study/transient_scan edge cases;
   install.sh + blrun.sh robustness. Crowd EXCLUDED (pre-v1 upstream).
   Sub-agents may run non-visual QA only (code review, script execution,
   textual assertions) — NO VLM bridging, no visual delegation.
3. T3 (carried): crowd-kit Rust build is network-gated; if network
   allows, `cargo build --release` in blender-crowd-kit, then run the
   crowd workflow end-to-end and vision-verify a dense scene. (LOW
   priority — crowd excluded from hardening scope until stable upstream.)
4. Milestone backup: /home/sync copy + both remotes (see backup cmd in
   PLAN M4).

## Known-open friction (from waves, triaged, NOT yet fixed)

- motion_study filmstrip labels are frame numbers only (fine); suspects
  strip cells could carry diff magnitudes (NIT, low value).
- transient_scan on crowd-dense scenes: validator sweep cost grows
  pairwise — if a crowd wave runs one, measure and consider
  `--validate-every N` stride (N=1 default).
- blrun.sh without `--background` hangs on GUI-on-Xvfb (candidate:
  auto-inject -b with a warning; needs a decision).

## Worklog + artifacts

- Multi-agent worklog: /home/z/my-project/worklog.md (harness dir;
  REPLICATE key entries into repo worklog.md — the harness dir does not
  survive sandbox resets). Repo worklog.md has session-1 history.
- Design docs: docs/DESIGN_vision_kit_v1.md (D1–D14 FINAL) + tuning
  harness scripts (tuning_*.py) from P1/P2.
- Wave outputs: output/t6_*, output/t7_*, output/w4a_scene/ (not
  pushed; regenerable from fixtures).

## Doctrine reminders for the next session

- GIT IS THE DISK: push on every micro step (session 3 lost unpushed
  P3/P4 work to a sandbox wipe; the loss boundary was exactly the last
  push). Never force push.
- Every new tool gets an in-Blender regression test before merge.
- Eyes triage and compose; gates decide geometry (two-column law).
- Scanner ranks; eyes verdict (L6). A clean keyframe sheet proves
  nothing about transients (the reason transient_scan exists).
