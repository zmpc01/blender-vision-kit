# PLAN.md — blender-vision-kit (long-horizon tracker)

> This repo is the VISION-FIRST VARIANT of blender-agent-kit. Upstream's
> project plan is preserved at `docs/UPSTREAM_PLAN_snapshot.md`. This
> plan tracks the VARIANT's long-horizon work across sessions.
> Companion: HANDOFF.md (immediate next-session scope only).

## Track TD: TERMINAL DAWN (session 12, DELIVERED — the review lane is open)

- [x] tdawn_1 exported (schema 2.3, all gates green) + staged to
      previz-review (newest-first) + verified in-app
- [x] vision-native build loop proven at film scale (6 camera
      reframes + flow-strip retiming + AgX emission laws, all eye-driven)
- [ ] the USER review round on tdawn_1 (comments on; A/B vs v6_1)
- [x] kit improvement filings upstream (F-TD5 view-layer sync was the
      export-blocking one; see docs/USABILITY_TD1_vision_film.md) —
      CLOSED: landed upstream (e4450a3) AND ported to THIS tree
      (session-16 — render_hidden_objects updates the view layer itself).
- [ ] optional polish: S2 board size, S6 gate glow gradient, Cycles
      keyframes for the 3 hero frames (EEVEE/AgX consistency tradeoff
      documented in the design)

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


### M12 — The RH integration lane (session 20, 2026-10-16 — COMPLETE)

- [x] Vendor rh_canvas.py + test + docs from mainline s38/s39 (zero
      code drift; data-driven deltas documented) + the placement_lib
      ARMATURE graft (index-aligned _ARMATURE_QUADS table after the
      S20-A3 audit)
- [x] THE DATA-SOURCE P1: beulahkemp/RH-canvas-* went dark — mitigated
      by the offline fixture library (scripts/rh_fixture_lib.py +
      _fixture_fbx_patch.py): 8 choreographed 65-bone clips + 3 statues
      + catalog files, recipe pinned by grid calibration against the
      import-law oracle, self-verifying truth.json, ANIMATED-BEHAVIOR
      gates (world-z) fail-closed
- [x] test_rh_fixture 13/13 (catalog/fetch-verify+repair/import laws/
      mannequin/bind+playback/refusals/swap-unpin/fingerprint/statue/
      GLB round-trip/placement e2e/ensemble)
- [x] scene_motion_lab: the dog-food humanoid scene (7 clips staged,
      per-actor motion strips, stills, GLB 928KB)
- [x] Native-vision e2e: 7/7 strips eye-certified AND the jump-apex
      illusion caught + corrected via the numeric probes (the
      self-sycophancy lesson is in SKILL s20)
- [x] Four sub-agent waves (A1/A2/A3 code audits + U1 docs-only drive)
      — every ≥P2 folded: F8 teeth, honest-skip, AgX pin, residue
      purge, union framing, metadata contract, catalog filters,
      placement vs-guards, the dead curve-stage deletion
- [x] Battery 38/38 ALL GREEN; GitLab archive BLOCKED by WAF all
      session (first chore next session); docs amendments landed


### M15 — The audit-everything round (session 23, 2026-10-18 — COMPLETE)

- [x] Sandbox re-land from remotes (the drill: ~25 min incl. the
      submodule-pin drift fix 2c99697 — r149 pin predates the 1.6.0
      wheel; s22 tested ahead of its own pin)
- [x] AUDIT-A ran (scoped A1: math + module): formula layer cleared
      by independent re-derivation (probed exact 1e-9); gate layer
      fail-open (3 P1) — ALL ENFORCED (43f6d24); the connected-
      location refusal replaced by skip+report after measurement
- [x] AUDIT-C (port-delta): sound/port-ready — then CLOSED-BY-
      UPSTREAM (mainline s41 superset design, vendored 68fbb1e by
      the film lane mid-session; ledger carries the obituary)
- [x] Post-vendor validation: the VACUOUS-SCORE class caught live +
      reproduced on mainline; two determinism landmines (R10b order
      dependency, R9g2 run-history dependency); all fixed (9d9977b);
      16/16 real + 14/14 fixture + crossval green
- [x] PORT-BACK TO MAINLINE (the user directive): the residual test
      fixes + docstring drift landed upstream (agent-kit 17e3ef1) —
      mainline TRULY 16/16 against the live clones (was 16/16 with
      a hidden FAIL)
- [x] Honest-skip exercise (queue 4): crossval exit 2 + sentinel;
      hero_lane library-INDEPENDENT by design (premise corrected)
- [x] AUDIT-B survival: all folds verified (1 by supersession)
- [x] FULL BATTERY 40/40 PASS 0 SKIP; GitLab archive + sync bundle

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
- [x] F18: place_on/snap_z on glTF vendor origins (origin >> centroid):
  doc the origin_offset_warning as load-bearing; set_location-style ops
  unsafe (R5 finding). CLOSED — law + warning shipped (AGENTS.md
  origin_offset_warning marked LOAD-BEARING;
  placement_lib._origin_centroid_warn emits it — cited by symbol,
  not line, after the anchor re-drifted; s19).
- [x] F19: loose `split` on high-part-count meshes is blind-legal but
  semantically destructive — warn gate (dry-run N > 50 ->
  ack_many_parts:true) + AGENTS.md line. CLOSED session-16:
  ack_many_parts gate in apply_patch.py + test coverage
  (tests/test_v9_fixes_s16.py).
- [x] F20: dispatch prompts must show the apply_patch wrapper shape
  ({load_blend, mutations}) explicitly — the stress-test agent had to
  read the script to recover (handled, but don't rely on it). CLOSED:
  the F20 law is taught in AGENTS.md (dispatch-prompts blockquote).
  NOTE: F20 is a colliding ID — the R6 record also files "F20
  (place_on occluded-support hint)"; that one closed with the R8 doc
  laws (F20/F21 doc laws, session 11).
- [ ] Candidate next: R6+ dog-food rounds (a WELDED level asset — the
  region-cut playbook on real level geometry; t10 export-package
  regression suite), crowd T3 (upstream-gated), upstream PR for D11
  install fallback
- [x] T6 scene ships in kit (t6_transient.py) as the transient/label regression vehicle — CLOSED: scripts/t6_transient.py is in-tree; consider --frames interplay doc (look --frames N vs animate n_frames)
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

### Session 11 — R8 (the level INHABITED) SHIPPED
- Seat protocol D17 (design REV-2 + critique round): region-growing
  probe on labeled furniture (sat-upon/clutter/contamination guards),
  measured seat math (H/O/flesh-c, prior gate), single-track NLA sit
  chain (walk/enter/idle/exit, boundary-probed), two-lane audit +
  exit reverse-validation. Driver->sofa + Girl->bed both ok=True on
  the real loft; profile-verified renders; test_r8_seat 18/18.
- F22 shipped FIRST (level-aware validator: fam-fam advisories 1325,
  unlabeled containment skips 1201, intersections 1452->77, P0
  734->52) + F20/F21 doc laws + VK-10 ported+verified + F23 ledger
  (handoff/label_use_ledger.json).
- Infra: GH blob-limit repair (R7 wrap had been silently unpushable;
  0315ab8 rewrite, release asset for loft.blend), GitLab mirror
  caught up, chain replayed 11/11 from committed scripts.
- Full record: docs/USABILITY_R8.md.

### Session 13 — R9 (the asset made durable: D18 shipped) COMPLETE
- Asset partition protocol (D18 REV-3, 2 critique rounds, 27 findings
  adopted): loft.blend 561MB -> 119 textures (403MB) + 14 chunks
  (104MB) + manifest, ALL IN-GIT, each blob <100MB. Fresh-clone proof
  passed (clone -> install -> rebuild -> manifest_diff 0 findings /
  1200 unchanged; renders pixel-identical). 10 measured Blender laws
  in docs/USABILITY_R9.md; regression tests/test_r9_chunking 16/16.
- The GitHub Release "level-asset-loft" + polyhaven re-fetch remain as
  compact alternatives; chunks are the clone-transport tier now.
- Kit files untouched this session (all new r9_* scripts + test);
  scope test clean except the pre-existing foreign-lane flag.

### Queue (next)
1. R10 candidates: second-interior schema-reuse test (label ledger as
   the yardstick); crowd lane on the level; prop CARRY during
   navigation (kb/prop_carry.md meets r7_navigate).
2. Sitting_Exit->walk-away chaining (full inhabit loop); third seat
   (chair x2) if the probe generalizes free.
3. t10 export suite — SHIPPED session-16 (D19: preflight + t10
   two-tier; extended session-17: prop 124 / export 25 checks).
   4. VK-9 re-vendor — DONE session-16 (wheel 1.5.5, provenance README
   completed s17 with sha256/size/origin). 5. Upstream PR: D11 install
   fallback + VK-10 hunk — still open (upstream-owned; see also
   docs/FINDINGS_upstream.md F2E-5 sync_shared guard). 6. CLOSED in
   the session-15 receipts (committed chain inputs replay
   R6→R7→R8 on the rebuilt master; both sits GREEN).

## Session-13 receipts (the tdawn iteration round — 2026-10-11)

- tdawn_1 → **tdawn_2** (staged, live, comments on): the eyes-driven
  refinement round — 12/12 stills re-reviewed twice, 2 look-rounds,
  8 forensic probes. The eye findings (clone crowd / white-void gate /
  flat board / empty S8 / pre-dive S9 / blank S10 / missing title /
  monolith pylons) ALL fixed and re-verified by eyes.
- **F-TD5 closed upstream + vendored down + red/green proven** (A19f).
- New filings: F-TD9 (factory leak; install.sh Pillow probe py3.13),
  F-TD10 (concurrent blrun → Xvfb :99 death), F-TD11 (make_material
  emission_color decouple — the glow-surface law), F-TD12 (shot-cam
  occlusion probe).
- Next-session candidates, in value order: (1) the user review round
  on tdawn_2 (comments ON — the db is repo-local; the schema push gotcha
  is in HANDOFF); (2) F-TD11 kit-side (make_material emission_color
  param, both copies); (3) F-TD12 (a shot-cam occlusion probe in the
  look tooling — the recession class is a recurring eye-trap);
  (4) install.sh: the Pillow py3.13 probe + a --blender-python flag
  (F-TD1/9); (5) the S10-class OOM: a look at EEVEE sample budgets for
  the heavy framings (SAMPLES override ships in tdawn_stills.sh).

## Session-14 receipts (the review round + the trio + the second film)

- tdawn_2 → **tdawn_3** (staged, live, comments ON): the user's five
  in-flight comments consumed — color discipline (their law: color =
  call-outs), the S5 north reframe (RCA: near-field capsules + stale
  aim), the S10 gate-wall 3/4 + dressing, the export-safe title
  (hide_render → scale keys), F-TD13 (keepout seconds-vs-frames).
- **F-TD10/11/12 CLOSED** (design REV-2 → implement → tests → vendor
  round): the blrun flock (4 repos), make_material emission params
  (both kits + twin), the look.py camera probe (14/14 incl. the
  animated-occluder class). F-TD13 filed+fixed scene-side.
- **LAST FERRY designed (REV-2) + sliced**: contract/world/scene
  modules in-tree, dry-run green, the night look proven at 4 frames;
  the build order (bake → strips → cams → stills → export) is the
  next session's first block.
- Next-session candidates, in value order: (1) finish tferry_1 (the
  bake driver + pipeline + stage — the contract/world are
  export-shaped); (2) the user review round on tdawn_3 + tferry_1
  (comments ON); (3) F-TD9 (install.sh stale-tools probe); (4) the
  S10-class OOM note for the heavy framings (SAMPLES override law).

## Session-15 receipts (the app restored + LAST FERRY end-to-end)

- **tferry_1 LIVE** (staged, audit-ok, comments ON): the full build
  order executed — bake (129 agents, envelope asserted) → flow strip
  → 3 workbench framing rounds → 2 EEVEE night passes → export (all
  gates green, 21.1MB GLB, 135 actions) → filmstrips → stage. The
  review app serves BOTH films (tdawn_3 + tferry_1) with the comment
  loop verified on tferry_1 itself.
- **The review-app continuity lane is now a solved problem**: the
  bootstrap kit (bun/prisma/db:push/daemonize-absolute-paths/
  s33-restore) + the tdawn_2 comment recovery path (escape 8841ee1)
  are documented in HANDOFF. The db dies with sandboxes; the export
  file in the escape repo is the durable user-voice copy.
- **F-TF1/2/3 consumed + F-TF5 filed** (vendor wheel 1.0.0 vs 1.5.4 —
  the bridge needs 1.5.4). The sfx {name,frame} contract, the
  exporter ctx["scene"]/BEATS shapes, and the rebase --theirs
  direction lesson are recorded in HANDOFF.
- **Chain-replay queue item CLOSED**: the committed chain inputs
  replay the R6→R7→R8 chain on the rebuilt master (cuts/props/route/
  walk/sits all matched the records; both sits GREEN).
- Next-session candidates, in value order: (1) the USER review round
  on tdawn_3 + tferry_1 (comments ON — the whole session pointed
  here); (2) stage tferry_1 rev 2 from the final merged module
  (329a9d8) if the user round wants the newest light composition;
  (3) F-TF5 re-vendor (the governed sync); (4) F-TD9 (install.sh
  stale-tools Pillow probe — the fresh case self-healed again this
  session); (5) the older filings — the true remainder is F-TD1/2/3
  (the make_material default is CLOSED — blender_kit.make_material
  pins Emission Color to the base rgb via its guarded socket write,
  and only touches Emission Strength when the caller asks).

## Session-16 receipts (the KIT-QUALITY wave — audit/test/refine, no film building)

- **Course correction honored**: the user ruled the parallel lane owns
  scene building; this session went back to the kit itself. Target
  chosen by audit evidence: the export/package lane (0 tests, recurring
  landmine class).
- **D19 SHIPPED** (design REV-2 + critique round + implementation +
  two-tier suite): `scripts/export_preflight.py` (the pre-export
  contract gate — attributed rejections, decode-parity guard with
  differential attribution) + `tests/test_t10_preflight_prop.py`
  (100 checks, 0.2 s, both-direction drift property) +
  `tests/test_t10_export.py` (19 checks, 7.5 s, subprocess) + exporter
  gate 15 (sfx conformance fail-closed) + gate 4 strengthening.
- **Wave A kit fixes** (test_v9 8/8): F-TD5 view_layer.update() port,
  scoped-audit state fix, F19 ack_many_parts gate, F20-R6 hint, F-TD9 +
  QA-R69 install.sh, F-TF5 wheel re-vendor 1.5.5.
- **Wave C docs**: AGENTS.md 9 code-verified fixes + the Ship & verify
  section + doc-debt sweep (F18/F19/F20/F-TD5/T6/Queue-6 closed with
  evidence; the true older-filings remainder is F-TD1/2/3).
- **Wave D QA**: full battery 26/26 after fixes (usd_export RNA-filter,
  probe file scope move, BLRUN_FORCE for nested-blrun suites, 2 P1 +
  11 P2 review findings all consumed).
- **ENVIRONMENT**: the GitHub PAT died (401) — GitLab carried the
  session as the authoritative target. A fresh GitHub PAT is the
  user-side blocker for restoring the dual-remote backup.
- Next-session candidates, in value order: (1) the USER review round on
  tdawn_3 + tferry_1 (comments ON — the app lane); (2) F-TD3
  (marker-camera hijack in viewport_capture — the last known
  silent-wrong-render class in the core eye); (3) port the preflight to
  the canonical agent-kit exporter via the governed sync (the film lane
  gets the same pre-render gate); (4) F-TD2 validator structural
  vocabulary; (5) R10 candidates (second-interior schema-reuse, crowd
  lane on the level, prop-carry).

## Session-16 receipts (GREEN LIGHT: the third film + the daylight regime)

- **tgreen_1 rev 2 LIVE** (the noon-afternoon crossing that freezes):
  two opposing streams (the x-sign palette split), the freeze as the
  third act (the capacity-box arrival law embraced), the statue+runner
  hero pair, the green/orange signal spine (f85/f445/f1009), the
  sun5/sky0.15 ratio rig. Export all gates green (140 actions); the
  in-app verification done.
- **The design process held**: 2 audit rounds + 1 research note FROM
  SOURCE before build — the two P0s (the freeze law, the per-film
  envelope) + the plaza triple-refusal were pre-build catches; the
  ingest probe was the round-3 empirical test.
- **The review wave** (4 parallel reviewers): zero P0s, 3 P1s
  consumed; determinism re-proven; the doc mapped to REV-4.
- **The daylight law family captured** (F-TG4): the ratio lever, the
  disc innocence, the noon card-contrast inversion, the emission
  transfer failure.
- Next-session candidates, in value order (s17 NOTE: (2) was stale —
  F-TD9 had already closed in-code; the filings resolved s17): (1) the
  USER review round on all three films (comments ON — everything else
  was prologue); (2) the filings F-TD1/F-TD2 (+F-TD3, closed s17);
  (3) a fourth film candidate: the queue/formation stories (M6) or the
  hero-lane pushout (F-TF6 + F-TG1's arrival semantics) — design-first,
  same discipline.

---

## Session-17 receipts (the second KIT-QUALITY wave — 2026-10-14)

- **The deep audit delivered its mandate**: 5 read-only auditors on the
  merged tip → 88 findings (2 P0, 13 P1, ~30 P2, rest P3) → ALL ≥P2
  fixed across four waves with regression coverage; battery 29/29
  (docs/battery_s17_results.md); P3 residue documented in
  docs/audit_s17/ as open-P3 (the seed for any future exhaustion pass).
- **F-TD3 closed** (timeline-marker override of scene.camera in
  render_angle — the corrected mechanism, the sweep fix, the
  camera_intent manifest rows).
- **Kit-quality class kills**: the PARAM_DOCS↔handler parity class
  (AST-checked), the unfiltered-operator-kwargs class (shared
  filter_rna_kwargs, all 3 usd twins), the silent-degradation fallback
  class (loud NOTEs), the parent-space solver class
  (_world_delta_to_local), the accepted-but-unimplemented param class
  (keep_xy=False, centroid, footprint, seat_mesh — all validated now).
- **Infra truth restored**: daemonize.py exists (was documented-absent),
  suite_runner enumerates the REAL battery, render_daemon resumes
  without destroying completed work, blrun's fallbacks all reachable
  (proven live), wheel provenance measurable (sha256/size/origin).
- **Value order for the next sessions**: (1) wave-2 audit only if the
  user asks (open-P3 seed is in the audit files); (2) upstream guard
  landing (FINDINGS_upstream.md) when an upstream-owned session opens;
  (3) lane discipline holds — the film lane's fourth film (DESIGN_squall
  REV-2) consumes the kit; this lane audits/refines/stress-tests it.

## Track TS: SQUALL (session 17b, DELIVERED — the review lane is open)

- [x] tsquall_1 rev 2 exported (all gates) + staged + verified in-app
      — the fourth film: storm-dusk regime (rain / wet ground /
      thunder flashes / the neon title), the M6 queue/portal/
      HoldPosition + the M5 ragdoll slip beat + groups + the
      events→sfx spine, 135 agents
- [x] the F-TS kit wave: F-TS1 (the bridge composition + real z),
      F-TS2 (the belt pins), F-TS5 (the loader override), the F-TS6
      tripwire pair, the SQUALL sfx vocabulary; F-TS3/F-TS4 filed
      (docs/USABILITY_TS1_squall.md)
- [ ] the USER review round on all FOUR films (tdawn_3 / tferry_1
      rev 2 / tgreen_1 rev 2 / tsquall_1 rev 2)
- [ ] the next-regime candidates (diversity queue): fog volumetrics,
      blue hour, interior/night-market queues, a two-film round if
      the review round lands clean
- [ ] the honest-scope files (when a scenario needs them): SPEED/
      GOAL/DISABLE layers are VIEW-invisible (the F-TS1 ledger); a
      VIEW channel extension is a previz-side pinned-contract change

## Track TF: THE EXPRESS + THE DRILL (the fifth + sixth films — DELIVERED, the review lane is open)

- [x] tfog_1 rev 1 (THE EXPRESS — blue-hour fog rail platform, 129
      agents): staged + verified in-app (previz-review c6b2f40); the
      bake pin 19a93975 reproduced cross-machine; payload f5387e4a
      (the S9+S10 clamp-split era); 12 certified stills (blue-hour
      verdict sky1.0/lamps0.40/strips0.50, fog 0.05->0.028) + 96
      filmstrips
- [x] tform_1 rev 1 (THE DRILL — golden-hour citadel formation
      drill, 102 agents): staged + verified in-app (previz-review
      844ed3a); the FULL CROWD-KIT V2/V3 STACK on film — 168 layout
      layers (7 windows x 24) + bake_interaction (the officers'
      clasp, 46 authored rows) + K1 composed-motion live (26 layered
      agents recomposed over [120,539], authored rows exempt) +
      channel clips; payload 9024057c BYTE-DETERMINISTIC (re-proven
      twice, incl. once from a wiped sandbox); 12 certified stills
      (the golden-hour ladder verdict: sun e14 + dust 0.004 — the
      authored 6-deg axis was pre-visual, the 6 m walls shadow the
      whole 56 m yard at 6 deg)
- [x] the export-compliance round landed UPSTREAM (agent-kit
      2fa345e): the s32 discovery gate's KNOWN_NON_STORY now carries
      the 8-name film-lane family vocabulary + the _collect_atmosphere
      VOLUME_SCATTER fallback (the tfog-era fix that died with its
      sandbox — the second GIT-IS-THE-DISK lesson for agent-kit)
- [ ] the USER review round on all SIX films (0 comments on the
      films — the whole lane points here)
- [ ] filed debt: the OTHER film modules fail the s32 discovery at
      their NEXT exports (tfog 13 extras; squall/green/ferry/tdawn
      TBD) — generic vocabulary joins the upstream exemptions,
      film-specific knobs lowercase (tform_scene is the worked
      example); churn only when an export round reopens each film
- [ ] the diversity queue rest: interior/night-market queues (the
      regime not yet covered); a two-film round if the review round
      lands clean

## Session-19 receipts (the THIRD audit-exhaustion round + native-vision e2e — 2026-10-15)

- Wave-1: SIX fresh-context auditors on 0edf1aa → docs/audit_s19/wave1_triage.md (6×P1, ~17×P2, ~30×P3). Auditor-D verified the s18 P3 list 13/14 already closed (F8 re-drifted; symbol-cites now the law).
- Waves A(me)/B(tests+pins)/C(infra)/D(docs+worlds) closed every ≥P2; wave-2 adversarial verification ruled the wave HOLDS and its findings were closed same-session; battery 35/35 (first receipt incl. the pin suite).
- The 5.x NODE_OWNER law (smoke/s19_socket_probe.py): material-node keys land on the NODE_TREE's animation_data — read BOTH owners; the film lane's no-op claim refuted, the three older films need no re-bake.
- Native-vision e2e (the new mandate): F-TD3 sweep + A2 filmstrip eye-verified via smoke/s19_td3_probe.py + smoke/s19_motion_probe.py; the eye probes found look.py's bare-animate crash that both audit rounds missed.
- The bare-animate family closed at ALL sites via blender_kit.call_scene_animate.
- Coordination: the film lane's tfog scene + flow strip (3bd04ec, 73f6633) rebased under twice, zero force; the lane needs the B1 finish fix + 126-pin docs before staging.
- Debts → next session: un-pinned s19 fixes; scene-module purge-prefix class; E12 kb note; K1 + tform (film lane).

## Session-22 receipts (the RH real-data round + the hero lane — 2026-10-18)

- THE RH ECOSYSTEM RETURNED (the user pointed at the relocation): the
  three beulahkemp clones verified live, 2,137 real FBX sha-verified
  locally, the CDN serving. The library-split discovery landed
  (756fd45) — test_rh_canvas 14/14 against REAL data (was graceful-
  skip since s20). THE S20 P1 IS RETIRED.
- Track RH-XVAL (DELIVERED): the fixture library cross-validated
  against reality — 9 family laws, 6 MATCH / 3 expected-deviation / 0
  UNEXPECTED (docs/RH_CROSSVAL_s22.md + battery row 39 + suite 40).
  The s20 reverse-engineered laws are now measured facts; the 3
  documented unit-baking deviations survived contact with the real
  files exactly as predicted.
- Track s21-D (DELIVERED, the hero lane): D1 converged on the film
  lane's canonical wrapper; D2 rig_family_quaternius (measured pins);
  D3 rig_retarget with the REV-3 law changes (the disconnected-
  topology location law, the frozen-evaluation drive check, the
  anatomy-gap coverage split); D4 the motion lab hero zone — the
  retargeted UAL->Quaternius walk eye-certified by the principal
  (strips + wide reframe + numeric tables agreeing). test_hero_lane
  6/6 = battery row 40.
- Track AUDIT (PARTIAL): AUDIT-B folded (0 P0/P1; 3 P2 + 3 P3 all
  fixed — c81f4e7). AUDIT-A (retarget engine) timed out — QUEUED for
  the next session (HANDOFF queue 1).
- Battery 40/40 PASS. The next-session queues live in HANDOFF (the
  port-back to mainline + AUDIT-A + the diversity queue rest).
