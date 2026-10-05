# HANDOFF.md — blender-vision-kit (immediate next-session scope)

> Session close: 2026-10-05 (session 8). Handoff-protocol audit +
> paydown (user-directed: "be extremely rigorous"), R5 real-asset
> lane, blind-agent STRESS TEST on a real polyhaven asset (protocol
> ROBUST), F17 fixed, validator v2 shipped. PLAN.md = long-horizon
> tracker. Study: docs/USABILITY_R5_polyhaven.md.

## State at handoff

- Repo: https://github.com/zmpc01/blender-vision-kit (main). GitLab
  mirror STILL BEHIND (PAT unrecoverable; GitHub = source of truth,
  /home/sync tar carries the same HEAD). NEVER force push.
- SCOPE DOCTRINE (binding, owner-ruled): kit FOR vision-native agents
  ONLY. Sub-agents: NON-VISUAL work only, and now under a WRITTEN
  EXECUTION CONTRACT (AGENTS.md D16 section): VISION-REQUIRED
  (region-cut box choice, label assignment, verdicts, delegate
  verification) vs BLIND-SAFE (loose dry-run/split, label_objects with
  GIVEN labels, manifest-derived placement, audit tools) vs
  STOP-AND-FLAG (cannot derive from manifest -> flag, never guess).
- Toolchain: NOT committed. Fresh sandbox: `bash install.sh`
  FOREGROUND. Blender 5.2.2.
- Regression battery (ALL GREEN at close): test_kit_scope (171 files),
  v1 27, v2 27, v3 20, v4 29, v5 76 (incl. L19 world_bbox + L22
  containment), v6 18 (manifest_diff, pure python), test_f17 9,
  t1–t6, t8 8/8, t9 chaos.

## Session-8 kit changes (evidence: docs/USABILITY_R5_polyhaven.md)

1. **Execution contract + verify-delegated-work checklist** (AGENTS.md
   law + kb/semantic_labeling.md): the session-7 blind handoff was
   real but implicit; delegated work was verified by eyes+claims.
   Now: baseline manifest -> delegate -> fresh look -> manifest_diff
   (every finding maps 1:1 to the task list) -> re-measure yourself ->
   closeup every touched object -> verdict last.
2. **manifest world_bbox** (look.py): every MESH row carries the
   world-space AABB — dims_m is LOCAL and lies under rotation; a
   blind consumer has no other ground truth. Caught + fixed a REAL
   stale-matrix bug en route (manifest now forces view_layer.update).
3. **manifest_diff.py** (pure python, no bpy): moved/resized/
   label_changed/added/removed/renamed(geometric twin)/nonmesh; accepts
   bare row lists AND full look_manifest.json dicts; --expect-clean
   rc=1 guard. tests/test_v6_manifestdiff.py M1-M10.
4. **F17 fixed** (placement_lib): place_on footprint grid refines ×4
   until rays hit (cap 192², sub-second) — top-onto-0.08m-legs on 2.4m
   span now solves (was: every 12×12 cell missed by 0.01m → blind
   agent had to snap_z). Report key footprint_grid_refined.
5. **Validator v2** (validate_scene): containment ≠ collision — pairs
   skip ONLY when both sides carry kit_label, shell-side label matches
   the shell vocabulary (room/shell/wall/floor/enclosure/interior/
   building), and the prop centroid is inside the shell bbox. Skips
   VISIBLE: summary.contained_pairs_skipped (pair+pct+reason). D16
   fixture demo: 2 blob P0s → 0 issues + 2 recorded skips.
6. **R5 lane scripts**: scripts/r5_polyhaven_fetch.sh (polyhaven API
   gotchas: /files/{id} NOT /download/file; textures under Models/jpg/
   <res>/<asset>/ despite gltf's textures/ URIs; undersized-file
   check) + scripts/r5_polyhaven_import.py (measure→scale 1.6m→ground
   →center, camera+sun).

## THE 456-PART LESSON (R5, print this in memory)

Real assets (polyhaven CoffeeCart_01): cart = 456 loose parts,
props = 329, mugs = 16. The D16 fixture's 10-island scale was
misleading. Blind loose-split at that count is legal and DESTRUCTIVE
(456 vision passes, source name lands on an arbitrary sliver).
**Label at VENDOR-NODE granularity; region-cut only features a
consumer must address.** Stress test: the blind agent REFUSED the
115-way split on its own (contract working) and flagged ≥3 pail
candidates for the bucket instead of guessing a cut box.

## Stress-test result (the user's rigor question, answered)

Blind agent (manifest+docs only, no hints which tasks were baits):
T1 seat mug_tray → DONE, self-verified (109.9mm clearance, 0.0mm
contact). T2 "fix floating cart_props" → WITHHELD (proved snap_z
sinks the 115-part cloud through the cart; place_on teleports it
+0.653m — gaming the gate). T3 "cut the bucket out" → PARTIAL
(dry-run yes; identity vision-required; no guess). T4 save → DONE.
Principal verification (trust nothing): manifest_diff baseline vs
assembled = **0 findings**; validator re-run by me = all pre-existing;
eyes on grid. Protocol ROBUST.

## Immediate next-session TODO (in order)

1. **F19** (R5 finding): loose `split` warn-gate — dry-run part count
   > 50 → require ack_many_parts:true; AGENTS.md line + v5 case.
2. **F18** (R5 finding): doc origin_offset_warning as load-bearing
   (glTF vendor origins 965mm off — set_location-style ops unsafe;
   world-space solvers only).
3. **R6 dog-food: a WELDED level asset** — the region-cut playbook on
   real level geometry (Sketchfab/Quaternius CC0 interiors; the D16
   fixture simulated what R5's cart didn't exercise).
4. Keep QA lane running (fetch+rebase mid-session; never force).
5. PLAN.md: t10 export-package suite, t6 ship, upstream D11 PR,
   crowd T3 (upstream-gated).

## Standing gotchas (do not relearn)

- Work in /home/z/vision-work clone (watchdog resets /home/z/my-project);
  Write tool only under /home/z/.
- Read-tool "syntax error" displays that contradict ast.parse = display
  mangling — trust the file (bit us twice this session: semantic_lib
  line 438, validate_scene MultiEdit ghosts).
- MultiEdit on argparse/dense blocks can apply with "failure" reports —
  ALWAYS verify with ast.parse + grep for duplicates after every
  structural edit (validate_scene got its header block TWICE).
- bmesh: indices not BMFace refs after bm.free(); bound_box corners
  need Vector wrap; primitive_cube_add defaults size=2 (span helpers
  pass size=1); matrix_world is STALE after in-process mutation until
  view_layer.update() (L19).
- place_on footprint grid refinement caps at 192×192 — beyond that,
  restructure the scene instead.
- Test fixtures: cell centers of an offset bbox can land EXACTLY on
  the feature (F4 first draft hit the 1cm pin at base density) —
  offset fixtures off-column deliberately.
- "File content impossible" Write errors = harness display mangling —
  verify with od/ast.parse, trust the file.
- F6 residue: add_sky_world() DEFAULT strength 1.0 still blows out
  EEVEE stills — template passes 0.5; changing the library default
  needs an owner ruling.
- GitLab push prints storage warnings even on success — verify HEAD.
  Current GitLab PAT is invalid (401) — mirror behind, GitHub is
  authoritative.

## Worklog + artifacts

- Repo worklog.md has the session-8 record (replicate into
  /home/z/my-project/worklog.md — harness dir does not survive).
- Study artifacts: docs/USABILITY_R5_polyhaven.md (this session),
  docs/USABILITY_D16_dogfood.md (session 7). Design docs:
  docs/DESIGN_D16_semantic_labeling.md.
- R5 artifacts (not committed, reproducible): output/r5/*.blend,
  look dirs, baseline/after manifests, labels_report.json,
  agent_work/ (blind agent's dry-run evidence).
- Multi-agent QA protocol: fresh-context sub-agents do NON-VISUAL
  review only; the D16 audit round 1 is the pattern.
- #11 [P2][bug] look.py --angles panels pixel-identical when loaded .blend has camera-bound timeline markers (marker camera hijack at render time — AK-10 class; agent-kit viewport_capture fixed it via suppress-BEFORE-assign + finally-restore, look.py has no marker handling). Repro: blend with markers S1@f1->CAM_A, saved frame 24, --angles front,persp -> meanAbsDiff 0.002 (38/307200 px), captions still say front/persp, manifest healthy with no per-panel camera recorded. Evidence: freshbook docs/qa-blender-kit/evidence/qa-r046/{grid.png,look_manifest.json,r046_main.log}.

## QA-LANE DISPATCH R52
VK-9: agent-kit twin (validate_scene.py @26c78eb) verified live via this issue's harness (0.2m/0.05m slabs exempt, sunk-sphere genuine positive retained); vision-kit's own copy unchanged at HEAD → stays OPEN pending re-vendor. VK-10: independent probe @6b09514 — drift layer STILL LIVE on this kit's examples/scene_v1_basic.py (sphere_x_keys=[(24,-2.0)] single-key collapse, x=-2.0 at f1/f12/f24); the s36 claim values match agent-kit's fixed copy, not this file; crash layer (iter_fcurves) IS fixed. Ask: port agent-kit examples/scene_v1_basic.py:123 sphere frame_set hunk. Evidence: freshbook-clone docs/qa-blender-kit/evidence/qa-r052/R52-VERDICTS.md.

## QA-LANE DISPATCH R56 (auto)
- Session-8 deep-verify receipt @3c06e05 (QA-r056-a): validator v2 CONTAINMENT SKIP PASS live (labeled shell + contained prop → 0 issues + contained_pairs_skipped VISIBLE with reason string; unlabeled overlap still flags P1, --fail-on-issues rc=1; renders eye 6/6 PNG) · manifest_diff PASS (owner suite 18/18 M1-M10 + full-dict {"manifest":…} unwrap ≡ bare list, reports equal + --expect-clean rc 0 clean / rc 1 "EXPECT-CLEAN VIOLATED") · F17 PASS (place_on onto 0.08m inset legs → "footprint_grid_refined": "12x12 found no support — refined to 48x48", tabletop zmin 0.7500 vs leg top dz=0.0000, crate dz=0.0000; wide support correctly no-refine) · VK-9 STILL LIVE (own 0.2m slab flags 100% penetration) · VK-10 STILL LIVE (keys=[(24,-2.0)], x=-2.0 at f1/f12/f24) — asks unchanged: re-vendor + example hunk port. MemAvailable guard named-skip @1195MB non-fatal (R22 law holds). — QA-r056-a
