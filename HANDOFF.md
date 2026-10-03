# HANDOFF.md — blender-vision-kit (immediate next-session scope)

> Session close: 2026-10-03 (session 5: HANDOFF gaps C/D/A/B closed via
> test_v3_edges 20/20 + t9_chaos_fuzz; then TWO full dog-food usability
> rounds (R1 reading-nook, R2 crate-stack) producing 7 kit fixes all
> verified end-to-end. PLAN.md = long-horizon tracker. Upstream snapshot
> preserved at docs/UPSTREAM_HANDOFF_snapshot.md.

## State at handoff

- Repo: https://github.com/zmpc01/blender-vision-kit (main; session-5
  head = cb7b220 + docs commits). GitLab mirror
  gitlab.com/ansgareutychisO/blender-vision-kit (PAT namespace is
  ansgareutychisO; WAF 403s probabilistic — retry). GitHub = source of
  truth. NEVER force push.
- SCOPE DOCTRINE (binding, owner-ruled): this kit is FOR vision-native
  agents ONLY. No VLM bridges, no ascii packs. Sub-agents: NON-VISUAL
  QA only. The principal makes every visual verdict.
- Toolchain: NOT committed. Fresh sandbox: `./install.sh` (run the big
  download/extract steps in FOREGROUND — the harness reaps background
  processes; setsid/nohup did NOT survive).
- Regression battery (all green at close): test_kit_scope, test_v1_look
  27/27, test_v2_motion 27/27, test_v3_edges 20/20, t1-t6 placement
  suites, t8 8/8, t9_chaos_fuzz ALL PASS.
- Session-5 kit changes (see docs/USABILITY_R1.md + R2 for the evidence):
  1. place_on override='keyframe' + _rebase_location_keys — placement of
     ANIMATED props rebases the whole keyframe path by the delta
     (replaces current-frame re-key; killed measured 20mm@f24 drift)
  2. place_on footprint AUTO-WIDEN bottom->grid (pedestal supports)
  3. move_to works on EMPTY/non-mesh (was AttributeError)
  4. validate_scene intersection: relative pct>=5 OR absolute —
     small-object sinks now visible (mug 20% fires; was invisible)
  5. PARAM_DOCS sync (add_empty rotation_deg; place_on/seat_at override)
  6. apply_patch _get_obj available-ids hint on every raw lookup
  7. transient_scan finding lines carry "(bbox-proxy; confirm with
     audit mesh numbers)"
- Laws added: audit pairs match `state` (PENETRATING/TOUCHING/NESTED/
  CLEAR), never `verdict`; AGENTS.md placement headlines carry auto-widen
  + animation-rebase.
- Study artifacts: docs/USABILITY_R1.md, docs/USABILITY_R2.md (friction
  logs + what-worked lists); study scenes shipped as scripts/
  reading_nook.py + scripts/crate_stack.py (also edge fixtures
  scripts/edge_*.py + tests/test_v3_edges.py + tests/t9_chaos_fuzz.py).

## Immediate next-session TODO (in order)

1. Dog-food R3 (owner): EEVEE/final-render lane as consumer — the study
   rounds only exercised workbench. Copy scene_template, --engine
   BLENDER_EEVEE (warm cache first: `blrun.sh --warm-cache`), still +
   samples, verify quality presets + readiness headers from the
   consumer seat. Log frictions to docs/USABILITY_R3.md.
2. Dog-food R4 (owner): export/previz lane — export_gltf + viewer +
   export_previz_package + keyframe_contact_sheet on a small animated
   scene; verify the ship arc end-to-end.
3. Fix whatever R3/R4 surface; keep the friction-log discipline; run
   the regression battery after each kit change.
4. Milestone backup: /home/sync copy + both remotes (commands in PLAN
   M4). Session-5 close backup taken at cb7b220+docs.
5. Crowd T3 (LOW, owner-excluded until upstream stabilizes; Rust build
   network-gated).

## Known-open friction (triaged, NOT yet fixed)

- F3-NIT: look SUBJECT-OVERFLOW hint fires on large ground planes
  inflating cluster diag — could exclude ground-like planes from the
  metric.
- F11-NIT: motion_study auto-pick includes STATIC props (trajectory
  dots read as noise) — de-prioritize non-animated meshes in the
  default object pick.
- place_on auto-widen retries once; a `footprint_autowiden` note is in
  the report but NOT printed by apply_patch's OK line (only the lib
  prints) — minor; consider surfacing in the op print.
- transient_scan 1-frame timeline: clean exit but the message could say
  WHY (no adjacent pairs) — edges suite asserts no-traceback only.
- look.py on empty scene: verdict PASS with NEAR-BLACK/NEAR-EMPTY flags
  — correct, but the readiness line could suggest "scene has 0 objects".

## Worklog + artifacts

- Repo worklog.md has the session-5 record (also replicate into
  /home/z/my-project/worklog.md — harness dir does not survive resets).
- Design docs: docs/DESIGN_vision_kit_v1.md (D1-D14 FINAL + session-4
  supersession note). Wave outputs live under output/ (gitignored,
  regenerable).
- Multi-agent QA protocol: fresh-context sub-agents do NON-VISUAL review
  only (wave 5-b pattern; caught 3 real bugs last session).

## QA-LANE DISPATCH R1 (auto — from the QA/visual-review lane, session 44d598d5)
Filed to this repo:
- #1 [P2] README quickstart: examples/ scenes rejected by look.py --scene (only scripts/t0_smoke.py works)
- #2 [P2] install.sh EEVEE warm-cache SIGKILL (OOM) under 4GB sandboxes — unhandled, scary crash
- #3 [P3] Cycles verify false negative + no BLENDER_BIN reuse path (sibling-symlink trick: 57s→13s)

## QA-LANE DISPATCH R3 (auto — from the QA/visual-review lane, session 44d598d5)
- #4 [P2] cross-ref agent-kit #15: workbench MATERIAL renders node-authored colors gray (mat.diffuse_color only; comment scripts/viewport_capture.py:190-196 claims base colors) — look.py has NO color metric so the loss is undetectable downstream; suggest sync-or-warn + validator chroma line. Evidence: raw.githubusercontent.com/belram448/freshbook-clone/main/docs/qa-blender-kit/evidence/qa-r003/{ctrl_wb,ctrl_cycles,look_ab_grid}.png
- Note: EEVEE OOM (our #2) live-fired a 3rd time (R3, controls run) under 4GB — still reproducible on current HEAD.
