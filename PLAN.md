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
- [x] P5 CORE-FLOW HARDENING (session-4, commits 4cdb0b5..8bfdce6): T8 placement-diorama fixture (place_on/snap_z/audit/physics drop + diagnostic gates, 8/8); placement suites t1-t6 ALL PASS on 5.2.2; PRINCIPAL visual pass on look grid/closeups/heat/seam/section — heat EXCELLENT, slices were BROKEN (measured: 5.2 ortho near-plane bbox cull) → redesigned intact seam-framed views + verified readable; install.sh Pillow retry (idempotent, 3x, fail-closed) + blrun GUI-hang guard (auto --background) — both had failed reproducibly in prior sessions
- [x] Hardening wave 5-b: fresh-context NON-VISUAL code review of the full session diff (0 blockers, 3 bugs, 6 nits) → fix batch 4 (image_metrics stdev label, _slice try/finally, section_side camera-standout, docstrings, t8 truth_state assert); full battery green (scope + t1-t6 + v1 27/27 + v2 27/27)
- [x] SESSION-5 GAPS CLOSED (2026-10-03): test_v3_edges 20/20 (empty/off-origin/wide/tall look + 1-2-frame motion/scan); t9_chaos_fuzz ALL PASS (7 perturbation classes + seat_at edge checks); apply_patch _get_obj available-ids hint on ALL raw lookups; state-vs-verdict law (t8 checker fixed + AGENTS.md)
- [x] SESSION-5 USABILITY R1+R2 (dog-food, reset-restart): docs/USABILITY_R1.md + R2 — 15 frictions, 7 kit fixes verified end-to-end: place_on override='keyframe' PATH REBASING (_rebase_location_keys; killed measured 20mm@f24 drift), move_to non-mesh guard, validator RELATIVE intersection threshold, PARAM_DOCS sync, scan bbox-proxy hint, place_on footprint AUTO-WIDEN bottom->grid, _get_obj hints; R2 physics lane clean first-try; regressions green (v1 27, v2 27, edges 20, t8 8, t9)
- [x] SESSION-6 QA-LANE FIX WAVE (2026-10-04, commits 50261a5..d342831):
  #1 path-tolerant safe_import_scene (examples/ work bare or as path,
  README example verified) + #5 T5z positive TOPPLED coverage (t5 ALL
  PASS) + #2 MemAvailable pre-check for EEVEE warm-cache (install.sh +
  blrun.sh; guard verified live by QA R22 at 2245 MB) + #3 honest Cycles
  verify (engine-assign probe; subclass-enum false negative killed) +
  BLENDER_BIN override (zero-download path) + #4/D15 display-color sync
  (workbench MATERIAL shows node-authored Base Colors; standalone
  sync/restore outside the annotation layer, per-material dedupe,
  default-gray skip, manifest color_source; test_v4_colorsync 29 checks;
  RGB cubes visually verified 4 angles) + #6 examples migrated to the
  driver convention (v2 NISHITA→version-safe sky; v1 floating cube fixed)
- [x] SESSION-6 DOG-FOOD R3 (EEVEE lane) + R4 (export/previz lane)
  (commits ed14b7d..6d41cd9): docs/USABILITY_R3.md + R4. Kit fixes:
  normalize_engine bridge (ALL CLIs accept ALL engine spellings — three
  vocabularies had disagreed), animated-first motion_study pick
  (static-props-crowd-out-mover, second consumer hit), template sky
  strength note + gotcha 128 (sky×EEVEE overexposure invisible to
  workbench), export_previz_package dual-lane (animate bridge +
  ctx-scene fallback + lane-aware gates) + pre-existing `blob`
  NameError BLOCKER (gate 14 crashed EVERY run), keyframe_contact_sheet
  MATERIAL+D15 sync (was OBJECT gray). Battery green: scope+v1 27+v2
  27+edges 20+v4 29+t1-t6+t8 8/8+t9.
- [x] D16 SEMANTIC MESH LABELING design + audit round 1 (c37cb4f):
  user-directed use case (reverse an opaque import into
  semantically-labeled objects for non-vision consumers). Design +
  amendments adopted (kit_label lowercase, idempotent two-phase rename,
  validator de-name-dependence, split_mesh preconditions).
- [x] M6 D16 IMPLEMENTED + DOGFOOD (session 7, docs/USABILITY_D16_dogfood.md):
  `label_objects` (kit_label/conf props, opt-in two-phase rename with
  whole-batch collision sim, charset law, report-before-rename),
  `split_mesh` (loose-parts dry-run/split + WELDED-geometry region cut
  mode=split-region with vision-driven world-box), validator
  de-name-dependence (kit_semantic prop; names = fallback only),
  manifest kit_label mandatory field, kb/semantic_labeling.md +
  AGENTS.md D16 ops. Tests: v5_labeling 58 checks ALL PASS, full battery
  green. Dogfood: imported-interior fixture (welded shell + props
  sheet) → LOOK→SPLIT→REGION-CUT→NAME→LABEL→LOOK→SAVE, 14/14 labeled;
  SUCCESS CRITERION met (non-vision sub-agent assembled table + seated
  ball + lamp head blind from manifest only, audit 0.0mm contacts).
- [x] SESSION 8 — handoff-protocol audit + paydown (docs/USABILITY_R5_polyhaven.md):
  audit found the vision->blind protocol was real but only implicit, and
  delegated work was verified by eyes+claims, not by diff. Paydown:
  EXECUTION CONTRACT law (AGENTS.md + kb: VISION-REQUIRED vs BLIND-SAFE
  vs STOP-AND-FLAG), verify-delegated-work checklist (kb),
  manifest world_bbox law + stale-matrix fix (L19), manifest_diff tool
  (v6 M1-M10, --expect-clean), region-cut report auditability verified.
  STRESS TEST on a REAL asset: blind agent correctly WITHHELD both
  vision-required tasks with evidence (floating cloud can't be fixed
  blind; bucket identity among >=3 candidates not derivable) and did
  the safe work; principal verified by diff (0 findings) + own
  re-measure + eyes. Protocol ROBUST now that the contract is written.
- [x] R5 polyhaven real-asset lane (session 8): fetch script (API gotchas:
  /files not /download/file; textures under Models/jpg/), import module
  (measure->scale->ground->center), look, region cut (espresso machine
  out of props — vision proposes -> dry-run verifies -> scratch cut ->
  eyes confirm), labels coffee_cart/espresso_machine/cart_props/
  mug_tray. THE 456-PART LESSON: real assets have hundreds of loose
  parts — label at vendor-node granularity, never blind loose-split
  high-part-count meshes (F19). Tests: f17 9 checks, v5 76, v6 18.
- [x] F17 FIXED (b8ca792): place_on footprint grid refines x4 until rays
  hit (cap 192x192); top-onto-narrow-legs repro passes; t8 8/8.
- [x] Validator v2 (5ee3a92): containment != collision — shell-vocabulary
  + both-labeled + centroid-inside pairs skip, visibly
  (summary.contained_pairs_skipped). D16 fixture: 2 blob P0s -> 0
  issues + 2 recorded skips. L22 regression.
- [ ] F18: place_on/snap_z on glTF vendor origins (origin >> centroid):
  doc the origin_offset_warning as load-bearing; set_location-style ops
  unsafe (R5 finding).
- [ ] F19: loose `split` on high-part-count meshes is blind-legal but
  semantically destructive — warn gate (dry-run N > 50 ->
  ack_many_parts:true) + AGENTS.md line.
- [ ] F20: dispatch prompts must show the apply_patch wrapper shape
  ({load_blend, mutations}) explicitly — the stress-test agent had to
  read the script to recover (handled, but don't rely on it).
- [ ] Candidate next: R6+ dog-food rounds (a WELDED level asset — the
  region-cut playbook on real level geometry; t10 export-package
  regression suite), crowd T3 (upstream-gated), upstream PR for D11
  install fallback
- [ ] T6 scene ships in kit (t6_transient.py) as the transient/label regression vehicle; consider --frames interplay doc (look --frames N vs animate n_frames)
- Note: blrun.sh without --background hangs silently (GUI-on-Xvfb startup) — FIXED session-4 (auto-inject --background guard)

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

## Session 9 — R6 (real stitched-interior level) SHIPPED
- Real level: Blender loft demo (561MB, 1200 meshes, 3.97M polys) —
  polyhaven has NO room-scale interiors (verified: 521 models surveyed).
- Region-cut playbook on the welded shell: floor/ceiling/mezzanine/
  stairs cuts, dry-run → split-region → render-verified; stairs (a 68°
  space-saver run) found by frustum raycast, extracted from the shell.
- NEW op `mesh_prepare` (triangulate) for the fused-face pathology
  (signature: verts_in_region>0, faces_to_cut=0 at any box).
- look.py FLAG_CAP=60 (12k annotation objects OOMed 4GB box) + look-lite
  .blend lane (strip packed images).
- 1155/1200 meshes kit_labeled (one programmatic patch, honest conf).
- Compose: 4 place_on on labeled supports + 2 rigged UAL actors (walk +
  mezzanine). Blind stress test: T1/T2 done (audit-clean), T3 bait
  withheld with evidence, manifest_diff 2/1209 — AND the handoff caught
  two wrong principal labels (pendant light, arc lamp) → fixed + chair x2.
- Full R6 record: docs/USABILITY_R6.md. New friction: F20 (place_on
  occluded-support hint), F21 (audit room-shell gap numbers), F22
  (level-aware validator thresholds).

### Session 10 — R7 (the level NAVIGATED) SHIPPED
- Blind route planner (pure Python, manifest-only): floor→stairs→
  mezzanine waypoints from labels+bboxes; direction inference with the
  outside-abut rule; bbox-ambiguous stair → STOP-AND-FLAG (exit 4);
  vision_stair_override.json resolves with recorded evidence.
- Executor: label-driven BVH supports, incremental-ceiling tread-hug,
  fall-through guard, NLA walk loop (Blender 5.2 API), two-tier audit:
  0 true floats over 705 frames / 23.7 s, 0 held samples.
- NAVIGATION CAUGHT A REAL R6 LABEL DEFECT: the `stairs` label sat on a
  parapet fragment; the real stair (Plane.003, 9 treads +y, 31°, under
  the slab band) was labeled `wall`. Schema fixed with evidence; chain
  re-run. Law: labels are hypotheses until a USE exercises them (F23).
- Tracking cams (south + void, Track-To Driver.Root) persisted in
  loft_nav.blend. Tests: test_r7_route.py 17 checks + v1/v5/v6/f17/
  scope battery ALL PASS. Full record: docs/USABILITY_R7.md.

### Queue (next)
1. R8 candidates: second-interior schema-reuse test; humanoid SIT/seat
   on labeled furniture; crowd lane on the level.
2. F20/F21/F22 + F23 (unexercised-label confidence) fixes. 3. t10
   export suite. 4. VK-9 re-vendor + VK-10 example hunk port (QA asks).
5. GitLab mirror catch-up (PAT still 401).
