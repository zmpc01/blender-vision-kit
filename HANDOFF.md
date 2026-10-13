# HANDOFF.md — blender-vision-kit (immediate next-session scope)

> Session close: 2026-10-13 (session 16, the KIT-QUALITY wave — audit /
> test / refine the kit; NO film building per the user's course
> correction). HEAD on **GitLab** (see the PAT warning below). Read
> docs/USABILITY_S16_session16.md (the wave's ledger) +
> docs/DESIGN_D19_export_preflight.md (REV-2, implemented).

## Session-16 close state (NEWEST — read this first)

- **⚠ THE GITHUB PAT IS DEAD (401 Bad credentials)** — verified at
  session start; reads still work (public repo, anonymous) but PUSHES
  fail. **GitLab carried the session** (oauth2 PAT alive, WAF-retry
  discipline). USER ACTION NEEDED: a fresh GitHub PAT, then
  `git push origin main` from any clone to reconcile GitHub (GitLab has
  everything through session-16; GitHub is stuck at e64528f). Verify
  BOTH PATs at session start (2-line curl check) before planning pushes.
- **Lane discipline**: the parallel lane owns SCENE work (tdawn/tferry
  modules, the review app, staging). This session touched ONLY kit
  files — do not co-edit scene_*.py.
- **D19 shipped — the export lane finally has regression coverage**:
  (1) run `blrun.sh --background --python scripts/export_preflight.py --
  --module scripts/<scene>.py` BEFORE any export (exit 3 = attributed
  rejection; contract failures now surface pre-render); (2) exporter
  gate 15 fail-closes malformed sfx streams (the F-TF4 class can never
  export green again) and gate 4 rejects a BOARD that decodes to zero
  entries; (3) t10 = test_t10_preflight_prop.py (100 checks, pure
  python, 0.2 s, BOTH-direction drift property vs the REAL decoder) +
  test_t10_export.py (19 checks, ~8 s, subprocess; fixture written into
  scripts/ — a temp dir is UNREACHABLE by the exporter's name-import).
- **Battery 26/26** (output/battery_s16/RESULTS.md). Three kit fixes it
  forced: usd_export kwargs are RNA-FILTERED at runtime (the 4.5-calibrated
  set TypeErrors on 5.2.2); the four nested-blrun suites carry
  BLRUN_FORCE=1 (the F-TD10 flock had broken their documented mode);
  probe files live under smoke/, never scripts/.
- **Wave A kit fixes** (test_v9 8/8): F-TD5 ported to THIS tree (the
  hidden-sweep updates the view layer itself), scoped audits honor the
  state enum + contact band, F19 ack_many_parts gate, F20-R6 occluded-
  support hint, install.sh authoritative Pillow probe + symlink heal,
  F-TF5 wheel re-vendor 1.5.5.
- **Bootstrap that works (fresh sandbox, verified this session)**: clone
  (GitLab if GitHub auth is still dead) → `bash install.sh` (Blender
  5.2.2 + Pillow resolved authoritatively) → suites via
  `./scripts/blrun.sh --background --python tests/<suite>`. Crowd wheel:
  vendor/blender-crowd/.../wheels/1.5.5 (provenance README in-tree).
- **Next-session scope**: (1) the user review round on tdawn_3 +
  tferry_1 (the app lane — parallel lane's); (2) F-TD3 marker-hijack
  fix in viewport_capture (design first — the last silent-wrong-render
  class in the core eye); (3) port the preflight to the canonical
  agent-kit exporter via tools/sync_shared.py governed sync; (4) if a
  fresh GitHub PAT arrives, reconcile GitHub first.
- Laws distilled this session are in .agents/SKILL.md (SESSION 16).

## Session-15 addendum (the SECOND lane's completion — read with the block below)


- **The app NOW carries the FINAL composition**: the staged tferry_1
  was re-cut from vision-kit 329a9d8 (previz-review 0008cfa) — the
  flip BOARD, the gang spot + gate work light, S9 re-aimed onto the
  crossing @f735, the 420W lane lamp, on top of the east pools/fill/
  title-emission pass. 12/12 EEVEE stills eye-certified by BOTH
  lanes' contributions composed as ONE set. The "stage rev 2" note
  below is DONE.
- **The fresh-context review round consumed (Task 5-a: zero P0s,
  5 P1s)**: the count law now pins N_RELEASE (the apportionment
  tautology), HERO_LANES removed as DEAD DATA (kit mode has NO
  hero-lane pushout — filed F-TF6 in the ledger), the RB
  placeholders parked OUTBOARD, render.fps pinned in build_scene,
  the FLANK WALL at y=-2.7 (the y=-0.5 wall's south face leaked a
  water-walk band). NEW LAW learned: the native engine REFUSES
  barricade squares past the walkable edge (E_InvalidRange) — cap
  centers at walkable−r. Re-bake pin 8b7d4d8e; the contract now
  evolves AHEAD of the staged package (an honest rev 2 re-export
  picks up the review fixes + the outboard statics when the user
  round demands it).
- **The ledger: docs/USABILITY_TF1_last_ferry.md** (F-TF1..6 + the
  night laws at shot scale + the two-lane merge-cost lesson).

## Session-15 close state (NEWEST — read this first)

- **THE APP SURVIVAL KIT (verified this session)**: clone
  previz-review → `bun install` → `npx prisma generate` → `npm run
  db:push` (REPO-LOCAL db) → start via
  `python3 scripts/daemonize.py <ABSOLUTE log> bash -c "cd <repo> &&
  bun run dev"` — daemonize.py chdirs to "/", so relative log paths
  EACCES and relative commands "Script not found". Then
  `s33_restore_comments.sh` (needs the server UP first).
- **The tdawn_2 comments are recoverable from git**: the mirror
  journal had none — they were re-injected from escape 8841ee1
  (previz_comments_tdawn_2.json) via POST. The db dies with the
  sandbox; the escape-repo export is the durable copy. Keep exporting
  user comments there.
- **tferry_1 is LIVE and complete** (staged 749d0a1, module
  4ef144b+): 12 shots / 45 s / 129-agent converge crowd / 21.1MB GLB
  / 96 strips / 12 EEVEE night stills / sfx events. Export ALL GATES
  GREEN. The scene module's FINAL merged set is 329a9d8 (the parallel
  lane composed both lanes' night passes: sign_flip keys, gang spot,
  gate work light, 420W lane lamp, S9 onto the gate @f735) — the
  STAGED package predates that composition; stage rev 2 from the
  final module if the deltas matter to the user round.
- **tferry build-order laws (new, measured)**:
  - F-TF1: ingest fail-closes on contract shape names — the contract
    needs DT + N_RELEASE + SPAWN_ZONES_V5 (the slice's "dry-run
    green" was scene-side only; ingest was never exercised).
  - The bake driver asserts the REV-2 F1 envelope PRE-bake (crew
    2.60 <= far 2.65) — the bridge clamps SILENTLY otherwise.
  - F-TF5 (OPEN): the vision-kit VENDOR wheel is 1.0.0, crowd-kit's
    is 1.5.4; the bridge needs 1.5.4 (motion_matcher kwarg). Re-vendor
    via the governed sync.
  - The exporter's story contracts: build_scene MUST return
    ctx["scene"] (exporter:2736); BEATS is (id, t_seconds, label)
    with t = (f-1)/24; sfx events need {name|kind, frame} — the "id"
    key is dropped 3/3 BY THE APP (found from the in-app console).
  - The Latecomer HOLDS at (4.8,8) f444-700 — aim the shot cams at
    the HELD pose, not the intent text (S7's aim was 4.8m stale).
  - Night pools: the east band needed (5.6,17.5) + (5.6,7.0) — lamp
    gaps read as murky dead stretches on the shot cams. The title
    card needs F-TD11 emission (make_material's 3rd arg is ROUGHNESS).
  - The sandbox's headless chrome CANNOT play the 21MB GLB (software
    GL; the tab died twice) — verify packages via the API + stills;
    3D playback is the USER's real browser.
- **Chain-replay receipt** (the aborted session-14 segment): the
  committed chain inputs replayed on the rebuilt master — cuts/props/
  route/walk/SITS all matched the R6/R7/R8 records numerically (both
  sits GREEN). The chain is reproducible from committed inputs; that
  was its purpose. Queue item CLOSED.
- **Merge law learned the hard way**: in `git rebase`, `--theirs` is
  YOUR replayed commit and `--ours` is the base — resolving backwards
  silently drops the incoming work. RE-RENDER + DIFF against the
  incoming commit after every conflict resolution (the re-render
  caught the dropped F-TF3 water-wall within one round).


## Session-14 close state (NEWEST — read this first)

- **DELIVERABLE LIVE: tdawn_3** (previz-review newest-first, comments
  ON): the user's 5 tdawn_2 comments ALL fixed and eye-verified —
  S1 color discipline (neutral crowd register + ONE rust chase callout;
  the user's law: color = call-outs, not diversity), S5 reframe (RCA:
  near-field capsule flood + a 7m-stale aim; new NORTH vantage down the
  stream axis), S10 gate-wall 3/4 + pilasters/beam/exit gantry (the
  pilasters are DECLARED barricades), S12 title = export-safe SCALE
  keys (hide_render keys do not export — the "constantly visible" bug),
  + F-TD13 (the keepout rows were SECONDS-vs-FRAMES inert — now
  shot-span frames + S12's dolly row). 12/12 stills re-reviewed twice.
- **THE KIT TRIO closed** (docs/DESIGN_FTD_trio.md REV-2, 2 review
  rounds): F-TD10 (the blrun flock, all FOUR repos, exit 90 +
  LOCK-HELD marker; vendor round 40/40), F-TD11 (make_material
  emission params, both kits + the twin; tests t7/v8), F-TD12
  (look.py --probe-camera; test_v7_camprobe 14/14 incl. the animated
  occluder). agent-kit 8a93e0b; escape vendored 60abd33.
- **LAST FERRY (tferry_1) slice**: design REV-2 (the reviewer probed
  the bridge source: speed envelope 2.65 vs tail 4.60 would clamp
  SILENTLY — retuned; throat AT (0,0) (the bridge hardcodes the
  target); walkable reaches y=-6 (the apron covers it); CROWD_X_RANGE
  (−6,6); crane over water = zero keepout rows; use_raytracing is the
  5.2 SSR knob). Modules: tferry_contract.py / tferry_world.py /
  scene_last_ferry.py — dry-run green, night look PROVEN at 4 frames
  (the L-TF1..4 laws are in SKILL.md).
- **Bootstrap that works (verified twice this session)**: clone the 5
  repos (CANONICAL names), bash install.sh (Blender 5.2.2 + Pillow OK
  on fresh single-python bundle), crowd wheel → venv
  (vendor/blender-crowd/addon/blender_crowd/wheels/*.whl), bake, run.
  The dev server: scripts/daemonize.py (double-fork) ONLY; comments db
  = repo-local; s33_restore_comments.sh after db push.
- **Open**: tferry_1's bake driver + flow strip + shot cams + stills +
  export + stage (the build order = kb/tdawn_vision_film.md steps 4-8
  with tferry names); the user review round on tdawn_3 + tferry_1;
  F-TD9 (install.sh Pillow probe for the stale-4.x-tools case — the
  fresh case self-healed); the older filings — the true remainder is
  F-TD1/2/3 (the make_material default is CLOSED —
  blender_kit/__init__.py:516 make_material pins Emission Color to the
  base rgb, :549).

> The user-directed D18 lane: the 561MB loft.blend is now IN-GIT as
> 119 textures + 14 chunks + manifest; fresh-clone rebuild proven
> (manifest_diff 0 findings, renders pixel-identical). Read
> docs/USABILITY_R9.md (10 measured Blender laws) +
> docs/DESIGN_D18_asset_partition.md (REV-3) first.

## Session-13 close state (NEWEST — read this first)

- **The asset is clone-transportable now**: after cloning, run
  `bash install.sh` then
  `./run.sh --background --python scripts/r9_rebuild_asset.py` — it
  builds `assets/loft/loft_master.blend` (gitignored, rebuildable)
  from the committed chunks + manifest. No Release, no network.
- Laws that WILL bite again on any .blend-partition work are in
  docs/USABILITY_R9.md (fake_user/users, scene-anchored compositor
  trees, save re-relativization, autopack, the Area.001 double-write
  law, closure gaps, delivery-model expectations). The chunk files in
  assets/loft/chunks/ are IMMUTABLE — a changed asset means a NEW
  asset directory, never an in-place rewrite.
- Regression: tests/test_r9_chunking.py 16/16 (synthetic round-trip,
  runs the real scripts as subprocesses with --python-exit-code).
- Open queue: see PLAN.md Queue (R10 candidates, t10, VK-9, upstream
  PRs, chain-input re-point).
- Parallel-lane live coordination held all session (6 remote moves,
  fetch-rebase before every push, zero force pushes).

> Session close: 2026-10-11 (session 12, the TERMINAL DAWN build).
> The user-directed vision-native film: from-scratch previz short
> built with THIS kit + blender-crowd-kit, exported kit-mode through
> the agent-kit exporter, staged to previz-review as `tdawn_1` —
> LIVE and verified in the app. Read kb/tdawn_vision_film.md (the
> recipe) + docs/USABILITY_TD1_vision_film.md (the friction ledger)
> + docs/DESIGN_terminal_dawn.md (design + REV-2 review folds).

## Session-12 close state (NEWEST — read this first)

- **DELIVERABLE LIVE**: previz-review `public/packages/tdawn_1/`
  (12 shots / 45 s / 1080 f, 129-agent crowd via the bridge kit mode,
  21 MB GLB, 12 EEVEE stills, 96 filmstrips, previz.json schema 2.3
  with the portable story vocabulary synopsis/beats/cast). The review
  app serves it newest-first; comments API needs `bunx prisma db push`
  + dev-server restart on a fresh clone (500-on-fresh-clone class).
- **THE HEADLINE FIND (F-TD5, KIT BUG, export-blocking)**: the
  exporter's #29 sweep (blender_kit.render_hidden_objects, owner =
  blender-agent-kit) reads a STALE view-layer object list — a
  freshly-linked object (measured: Runner.Root) false-positives as
  view-layer-excluded and gate 24 rejects the export. Scene-side sync
  duty landed in my build_scene; THE KIT-SIDE FIX IS UNLANDED (owner
  repo; do NOT vendor here). Highest-value first action for any kit
  session: land `view_layer.update()` before the #29 check upstream.
- **F-TD3**: marker-camera hijack + scene.camera MUTATION on clearing
  marker bindings — look.py is still vulnerable on marker-bound
  scenes (matches QA #11 on agent-kit). My passes are marker-safe
  (tdawn_flowstrip.py / tdawn_filmstrips.py patterns).
- **AgX emission laws (5.2, measured)**: Principled Emission COLOR
  defaults WHITE (pin to base rgb — make_material does); glow keys
  >~1.0 desaturate to TAN under AgX (cap 0.95); sky 1.0 blows
  interiors (0.35-0.5 + exposure -0.5).
- **Crowd-kit integration proven end-to-end**: bake driver (venv,
  keepouts PASS-THROUGH is the driver's duty — F-TD4) → loader honesty
  asserts → bake2 → exporter kit-mode gates 15/16/17 green at N=129.
  The bridge shape (pursue-origin) was reused as a different STORY
  (gate convergence) with zero bridge forks — the pattern to copy.
- **Parallel-session races**: the remote moved twice mid-session
  (D17/F22/F20 from a parallel session); GitHub + GitLab converged via
  sync_both.sh discipline. tools/ (Blender) NOT committed; gitignore
  holds. /home/sync copy made at close.
- Open: F-TD1 (cross-kit wheel install), F-TD2 (validator structural
  noise), F-TD8 (git races — standing), the six kit improvement
  filings (USABILITY_TD1 final section), the tdawn_1 user review
  round (comments are ON — the film awaits the user's notes).


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

## QA-LANE DISPATCH R69 (auto)
- #12 [P3][polish] install.sh aborts rc=2 (dpkg-deb "failed to chdir") when tools/local-libs is a DANGLING SYMLINK — raw tool error kills the script under set -euo pipefail BEFORE the :95 teacher-grade ERROR line can print. Repro 3/3 (sibling-symlink consolidation flow); fix control: absolute-path symlinks → rc=0 (Blender already installed / libEGL already extracted / Done).
- Ask: dangling-symlink detect-and-heal guard (rm dangling + mkdir -p) before the extraction loop, or stage-extract to mktemp -d then cp -a; keep :95 teacher line reachable (|| teacher-error wrapper).
- Narrow trigger but natural workaround (re-run install) re-downloads a duplicate 1.2 GB Blender per sibling kit; QA SOP sibling-symlink law corrected on our side in parallel.
- Evidence: belram448/freshbook-clone docs/qa-blender-kit/evidence/qa-r069/ (vk_inst.txt, vk_inst2.txt rc=2) — private repo, belram448 PAT required.

## SESSION 9 — R6 CLOSE (real level: cut → label → compose → blind handoff)
State: GitHub HEAD = R6 wrap commit (verify with git log -1). Sandbox
wiped between sessions; bootstrap = clone + `./install.sh` foreground
(Blender 5.2.2, Cycles OK). The asset re-downloads via
`scripts/r6_loft_fetch.sh` into /home/z/vision-work/polyhaven_cache/loft/.

What exists now (state chain output/r6/, all reproducible):
loft_import → loft_look (lite) → loft_cut_arch (4 shell cuts) →
loft_labeled (1155/1200 kit_label) → loft_props (4 placed) →
loft_compose (2 UAL actors: Driver walking, Girl on mezzanine) →
loft_blind_work (agent additions) → loft_final (label fixes).
Manifests: handoff/ (pre-work), blind_work_manifest/ (post-work).

Verified end state (my eyes + tools):
- region cuts render-verified (stairs pre/post pair in look_cuts/)
- placements audit-clean (book TOUCHING, ball 0.0mm, lantern TOUCHING,
  mug CLEAR 5.95mm on the recessed ottoman top)
- blind agent: T1/T2 DONE audit-clean; T3 bait WITHHELD with zone
  evidence; manifest_diff independently re-run: 2 findings (additions
  only), 1209 unchanged
- pendant_light/arc-lamp/chair label corrections applied after the
  agent's spatial-anomaly report (the handoff caught MY errors)

Read FIRST for context: docs/USABILITY_R6.md (full record incl. limits
hit: OOM ×2, annotation explosion, honest validator noise on real
levels), kb/semantic_labeling.md R6 section, AGENTS.md D16 section
(mesh_prepare + FLAG_CAP law). Friction queue: F20/F21/F22 + VK-9/VK-10.
Blind-agent lessons live in .agents/SKILL.md (center-placement law,
fused-face signature, family-granularity labeling).

Delegation protocol for the next session: unchanged (AGENTS.md
EXECUTION CONTRACT) — vision-required: cut boxes, label assignment,
verdicts, delegate verification; blind-safe: placement/measurement ops
from the manifest; STOP-AND-FLAG anything underivable. The R6 run is
the reference execution of that contract on a real interior.

## SESSION 10 — R7 CLOSE (the level NAVIGATED: blind route → stair ascent)
State: GitHub HEAD = R7 wrap commit (verify with git log -1). Bootstrap
= clone + `./install.sh` foreground. The full R6 chain rebuilds from
committed scripts (verified live this session — dry-run face counts and
placement verdicts matched the R6 record exactly).

What R7 proves: a NON-VISION agent can PLAN floor-to-floor navigation
from the manifest alone (r7_route_planner.py — pure Python), the kit
EXECUTES it (r7_navigate.py: label-driven supports, tread-hug with
incremental ceiling + fall-through guard, NLA walk loop for the Blender
5.2 API), and a two-tier audit certifies it numerically (0 true floats
/ 705 frames) + renders verify it visually. Where bboxes cannot decide
(stair running UNDER the slab: abut-direction ambiguous), the blind
planner STOP-AND-FLAGS and the principal resolves via
vision_stair_override.json — recorded, not hidden.

THE BIG FIND: navigation caught a real R6 label defect — the `stairs`
label sat on a 14-face parapet fragment; the actual stair (Plane.003:
9 flat treads, +y, ~31°, under the mezzanine slab band, arriving at the
slab at y 13.8) was labeled `wall`. Schema corrected in
gen_r6_labels.py with the evidence inline; chain re-run end-to-end.
LAW: a semantic label is a hypothesis until a USE (walk/place/seat)
exercises it — navigation is the strongest label validator (F23).

Read FIRST: docs/USABILITY_R7.md (probes 3-16 narrative + gotchas:
BVH local-space rays, Blender 5.2 slotted actions / NLA looping,
texture-driven displacement vs the lite lane). Tests:
tests/test_r7_route.py (pure Python) + v1/v5/v6/f17/scope ALL PASS.
Artifacts: output/r7/{route_request.json,vision_stair_override.json,
nav_report.json,loft_nav.blend (with 2 tracking cams),look_nav/}.

Delegation protocol: unchanged (AGENTS.md EXECUTION CONTRACT). Blind
agents can now also REQUEST ROUTES (planner is pure Python on the
manifest) — but executing a route stays kit-side; verify every
delegated nav with the audit numbers, never self-reports.


## SESSION 12 — R8 CLOSE (the level INHABITED: actors SIT)
State: GitHub HEAD = R8 wrap (verify git log -1; parallel lanes may
have moved it — fetch first). Bootstrap = clone + ./install.sh
foreground; the loft asset comes from the GitHub Release
"level-asset-loft" OR scripts/r6_loft_fetch.sh (NOT in git — 100MB
blob limit; the R7 wrap commit was rewritten 0315ab8 = f7facd9 minus
the blob; polyhaven_cache/ is gitignored).

What R8 proves: the kit derives seat surfaces from LABELED furniture
by probe (region-growing, sat-upon/clutter/contamination guards,
seed-driven), measures the actor's seated pose (H/O/flesh-c with a
prior gate), executes walk->sit->idle->exit via a single NLA track,
and certifies it (sphere-proxy lane + exit reverse-validation).
Driver->sofa (rigid/high) and Girl->bed (soft/medium) both ok=True;
renders verified by the principal's eyes (profile shot settles seat
contact). test_r8_seat.py 18/18 + test_f22_levels.py 14/14 + battery.

Read FIRST: docs/USABILITY_R8.md (7 guarded probe failures = the
texture of real furniture), docs/DESIGN_R8_seat_protocol.md (D17
REV-2), .agents/SKILL.md R8 addendum (yaw law, NLA junctions, seat
math, git blob law). Friction queue: F20/F21/F22/F23 + VK-10 all
CLOSED this round; VK-9 (re-vendor) still open.

Delegation protocol unchanged (AGENTS.md EXECUTION CONTRACT). New
blind-safe surface: r8_seat.py probe on a labeled family + approach
hint (STOP-AND-FLAG exit 4 on contamination/clutter/low-confidence);
executing a sit stays kit-side; verify delegated sits with the audit
numbers (ok flag + dz + no_penetration + exit_ok), never self-reports.

## Session-13 close state (NEWEST — read this first)

- **DELIVERABLE: `tdawn_2` LIVE** in previz-review (newest-first) and
  in the served checkout — the user-directed refinement round. Every
  tdawn_1 eye-finding fixed: the varied commuter palette (G1: the
  per-agent materials land POST-bake_tier2; the lib mesh is shared so
  pre-bake assignment collapses to one color), the gate TUNNEL + the
  seal-edge slit strips (G2: the flat white screen → a receding lit
  portal), the REAL departure board (the rows were flush-mounted
  INSIDE the panel silhouette — now proud), the pylons with lit sign
  faces (G3), 7 camera reframes (S1/S5/S7/S8/S9/S10/S12 — S8's empty
  hall → the Master/Runner pairing AT the gate line; S9's south vantage
  → the hall side: the dive reads AWAY from the crowd, silhouetted
  against the vault glow through the sealing gap), the dive retimed so
  the arc peak lands EXACTLY on the S9 still frame (f750), the title
  card (converted FONT mesh, warm cream, hide_render-keyed until the
  f1009 sting), the white-out tamed (the glow-surface law: dark base +
  warm Emission Color — make_material's equal-pin design is the white
  void), the stumble moved INTO S7, the board flicker A/B anti-phase.
- **F-TD5 LANDED UPSTREAM** (agent-kit e4450a3: view_layer.update()
  before the #29 sweep; A19f red/green proven; 79/79 tier-A) and
  VENDORED DOWN (the wrapper's governed-pair guard caught the drift —
  the vendor flow: kit tools/sync_shared.py --to <consumer>, commit
  both).
- **THE SESSION-13 SURVIVAL LAWS** (SKILL.md): the factory-scene purge
  (--factory-startup loads Cube/Camera/Light into your scene), the
  glow-surface law, the recession-occlusion class ("invisible subject"
  → ray-cast through it before doubting animation), "frame-edge clip"
  can be an occluder, never run two blrun/EEVEE pipelines concurrently
  (Xvfb :99), Bfont ≈ 0.91-1.1 em/char, the comments db is repo-local
  (push the schema with the absolute URL; the harness exports a global
  DATABASE_URL the app ignores), Pillow on 5.2 = python3.13.
- New kit filings: F-TD9 (factory leak + install.sh Pillow probe),
  F-TD10 (concurrent blrun), F-TD11 (make_material emission_color
  param), F-TD12 (shot-cam occlusion probe) — docs/USABILITY_TD1*.
- Fresh sandbox bootstrap that WORKS (verified end-to-end): clone the
  4 repos with the CANONICAL dir names (blender-vision-kit,
  blender-escape-previz — the scene module's TPREVIZ_SCRIPTS default
  and the bake driver hardcode them), bash install.sh, Pillow by hand
  (py3.13), wheel into the venv
  (blender-crowd-kit/vendor/.../wheels/*.whl), bake
  (tdawn_bake.py --out /tmp/crowdcache_tdawn), stills (SAMPLES=24 for
  the S10 heavy class), export (the wrapper command in the kb, with
  KIT_EXPORTER + BLENDER_BIN exported), stage both checkouts,
  prisma db push (repo-local db!), bun dev.
- Open: the F-TD9..12 kit filings; the user review round on tdawn_2
  (comments ON); the six older filings (F-TD1/2/3 + the make_material
  default) — F-TD6 is now PARTIALLY superseded by the glow-surface law.
