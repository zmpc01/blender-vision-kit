# HANDOFF.md — where we are, what's next

> Read AGENTS.md first (the 72 gotchas), then the kit's `.agents/SKILL.md`,
> then this file.

## Current state (session 18 close — PSD design REVERTED)

### Directive from the user (2026-09-15)

> we have to revert and replan above. for now remove all the design proposals
> and remove stuff from the plan or handoff, only leave research finding if
> not contradict the following. this seems not the correct decision yet and
> calling it PSD format is confusing. overall sound too complicated. possibly
> we should go with something like USD? in any case we shouldn't handroll
> foundational plumbing when i say json i was asking for things that are
> simple that we can map out as a last resort but not if we have to do bone
> tranform and other stuff lots of risk things go wrong. i am handling this
> over to the web editor team and for now just clean up and leave the above
> directive as latest context.

### What was reverted

The "PSD (Previz Sequence Document)" format design + Phase 0 bone-space
conversion prototype have been REMOVED from the kit repo. Specifically
deleted:
- `docs/DESIGN_psd_export.md` (v2 spec, 923 LOC)
- `docs/DESIGN_psd_amendments_v3.md` (12 amendments post-REVIEW-B)
- `docs/DESIGN_psd_amendments_v4.md` (4 amendments post-Phase-0, incl. the bone-space fix)
- `docs/REVIEW_A_psd_critique.md` (4 showstoppers + 8 contradictions)
- `docs/REVIEW_B_psd_critique.md` (2 NEW showstoppers + 10 sharp edges)
- `scripts/phase0_test_scene.py` (2-bone rig test scene)
- `scripts/phase0_bake.py` (the baker with bone-space conversion math)
- `scripts/phase0_verify.py` (Python-side verifier)
- `scripts/probe_bone.py` + `scripts/probe_cube.py` (Blender API probes)
- `viewer/phase0_test.html` (WebGL viewer)
- `output/phase0_test/` (test artifacts: scene.glb + tracks/*.baked.bin)
- `.agents/SKILL.md` Session 18 distillation (the bone-space conversion lesson)

The worklog.md retains its session-by-session record (RESEARCH-A audit +
REVIEW-A + REVIEW-B entries) — those are historical, not forward-facing,
and the RESEARCH-A audit is a pure audit of the existing pipeline that
doesn't contradict the new directive.

### Why reverted (the user's reasoning)

- "PSD format" name is confusing.
- The overall design is too complicated.
- Hand-rolling foundational plumbing (bone transforms, matrix_basis
  composition, column-major packing, Y-up conjugation, etc.) is too
  risky — too many things can go wrong.
- JSON is fine for SIMPLE things that we can map out as a last resort,
  but NOT for things requiring bone transforms or other complex math.
- Possibly use a standard format like USD instead of hand-rolling.

### New direction (per the user)

1. **Consider USD** (or another standard format) as the foundation —
   don't hand-roll the bone-transform / animation-channel plumbing.
2. **JSON is OK only for simple things** as a last resort — not for
   bone transforms or anything with lots of risk.
3. **Handed off to the web editor team** — they will own the
   web-side architecture decisions.
4. **Replan needed** before any further export-track work.

## What's still valid (RESEARCH-A audit findings, kept in worklog.md)

The RESEARCH-A audit (worklog Task ID: RESEARCH-A) is a pure audit of
the existing export pipeline. Its findings stand as factual observations
about the current state — they don't contradict the new directive. Key
findings (for the web editor team's reference):

- **F1**: The deliverable `.glb` is a STATIC POSE at f600; full animation
  is `.blend`-only; the web viewer can orbit a frozen frame but cannot
  play the cinematic.
- **F2**: The glTF exporter wedges at >27 min for the v4 hero-swap scene
  (4 UAL actors × 371 fcurves × 1080 keys × 602 actions).
- **F3**: `scene.blend` balloons to 251MB with the full action pool;
  `pack_v4.py` strips to fit GitHub's 100MB tree limit.
- **F4**: `shot_pipeline.py` AST-parses `SHOTS_V2` but v4 declares
  `SHOTS_V3` — tooling is stale.
- **F5**: NO web→blender round-trip code path exists; the viewer is
  read-only.
- **F6**: Audio metadata is split across 4 places (DIALOG table,
  sfx_events.json, mux_dialog.sh, finalize_v4.sh) — drift risk.
- **F7**: Three uncoordinated RNG seeds (11 / 4242 / 1234).
- **F8**: previz `blender_kit/__init__.py` + `scene_schema.py` +
  `apply_patch.py` have DRIFTED from kit.
- **F9**: Hardcoded `/home/z/` paths remain in 6 previz files.

## What the web editor team should consider

(per the user's directive — these are open questions, not decisions)

1. **USD as the foundation** — Universal Scene Description is a mature
   format with broad industry support (Pixar, NVIDIA, Apple, Blender
   has a USD exporter). It natively handles:
   - Skeletal animation (USD Skeleton + SkelAnimation)
   - Cameras, lights, materials (USD stages with kind/role metadata)
   - Time-sampled attributes (per-frame baked values, no fcurve math
     needed on the consumer side)
   - Hierarchy + instancing (good for crowd scenes)
   - Layering (good for round-trip edits — overrides don't touch base)
   Blender 4.5's USD exporter (`bpy.ops.wm.usd_export`) is reasonably
   mature. Three.js has a `USDZLoader` (limited); for full USD playback
   in WebGL, the team would need a WASM-compiled USD runtime OR convert
   USD to glTF at export time and play glTF in the browser.

2. **glTF + external tracks (the reverted PSD direction) was too
   risky** because it hand-rolled:
   - Bone-local vs world matrix conversion
   - Column-major vs row-major packing
   - Y-up vs Z-up conjugation
   - matrix_basis composition with rest_local_glb
   The math is subtle (the design failed twice before passing Phase 0).
   A standard format handles this internally.

3. **JSON is fine for simple things** (shot tables, dialog onsets, SFX
   events, story-level constants like KNOCKDOWNS_V3, MUZZLE_BURSTS_V3).
   These are flat data, no math, no bone transforms. The existing
   `sfx_events.py` + `scene_schema.py` patterns are examples.

4. **Round-trip** (web edits → blender re-bake) is a separate concern
   from the export format. The team should decide the format first,
   then design the round-trip on top.

## Session 18 v5 track (parallel work, INDEPENDENT of the reverted PSD track)

v5 ("Make It Land") is IN EXECUTION in blender-escape-previz:
PLAN_v5.md REV2 committed (fresh-eyes gap scan + 2 adversarial
reviewers, 12 P0s incorporated). STEP 0 (fork + capsule regression)
+ STEP 1 parts 1-2 done: the gun package (assets_rifle_v5.py —
joined 10-primitive rifle, authored Rifle_Aim/Shoot, post-bake
DEF-hand.R bone-parent calibration) integrated end-to-end, UAL
dry-run GREEN, capsule regression GREEN.

Laws distilled: AGENTS.md gotchas 73-78.

v5 NEXT: gun_fit_audit (mm vertex-group contact via placement_lib)
+ line_of_sight gate + burst-pop visual verify; then STEP 2 gunner
alive (S8 contact stagger + S8b camera re-aim + reload beat) per
the REV2 exact Beat list.

placement-lab assessed (user directive): directly useful —
placement_lib.pair_contact/classify_point + keyframe_contact_sheet
are the gun-fit gate instruments (already vendored in kit scripts/).

## Environment notes (unchanged from session 17)

- Blender 4.5.13 installed at `tools/blender-4.5.13-linux-x64/`
  (binary at `tools/blender/blender` symlink). Run scripts via
  `bash scripts/blrun.sh --background --python scripts/<script>.py -- <args>`.
- glTF exporter source available at
  `tools/blender-4.5.13-linux-x64/4.5/scripts/addons_core/io_scene_gltf2/`
  for reference.
- pygltflib available via `/usr/bin/python3` (Python 3.13) — useful for
  pure-Python .glb inspection.
- Watchdog: work OUTSIDE `/home/z/my-project/`. The repos at
  `/home/sync/work/` are safe.
- GIT IS THE DISK: push every micro-step. GitHub primary (`origin`),
  GitLab mirror (`gitlab` remote, oauth2 PAT format, WAF blocks ~1/3 — retry).

## Open: previz GitLab mirror divergence

The previz repo on GitLab has a parallel-lineage commit (`047b1c0
gate-integration: static frame-1 build wrapper`) that duplicates local
commit `8dcaaf4` (same content, different hash — Session-14
parallel-agent split). Per never-force-push, this requires a structural
merge next session (NOT a force push). The local GitHub origin is up to
date (no divergence there).

## Sticky rules (never break)

1. Push your work often (GIT IS THE DISK).
2. Never force push to remote — slow down and fix merge issues.
3. The watchdog force-checkouts `/home/z/my-project` — work in
   `/home/sync/work/` (or any path under `/home/z/` outside my-project).
4. The Write tool only works under `/home/z/` — stage at `/home/z/staging/`
   then `cp` to the repo dirs.
5. Background processes die between tool calls — single-bash-call with
   long timeout for any operation >2 minutes.
## Issue #1 (previz:entity USD carrier) — CLOSED ✓

**Closed 2026-09-16T13:55:09Z**. State: completed.

### What was delivered

- `scripts/previz_usd_hook.py` (~950 LOC) — `bpy.types.USDHook` subclass
  `PrevizUSDHook`. Recursive `_to_usd_safe` converter (handles
  tuples-of-tuples, lists-of-scalars, dict-of-dicts). `_sanitize_usd_name`
  (matches Blender's USD exporter byte-level sanitization).
  `_build_prim_name_map` (walks stage ONCE for O(N) prim lookup).
- `scripts/export_usd.py` (~150 LOC) — CLI mirroring `export_gltf.py`.
  RNA-verified kwargs for `bpy.ops.wm.usd_export`.
- `scripts/blender_kit/__init__.py` — new `export_usd()` helper
  alongside `export_gltf()`. Lazy-imports `previz_usd_hook`.
- `tests/test_usd_carrier.py` (~460 LOC) — round-trip test: minimal
  scene + test scene module + special-char-names coverage.

### Process (per user directive "design / impl / test / review iterations")

1. **Wave 1 — Research** (sub-agent USD-RESEARCH-1): audited kit's USD
   surface (zero existing code), researched Blender's USDHook API +
   USD customData constraints, mapped previz story-data structures,
   produced smoke test artifact.
2. **Wave 2 — Design** (`docs/DESIGN_previz_usd_carrier.md`): locked
   implementation plan per research recommendation §6.
3. **Wave 3 — Implementation** (commit 0e42c22): wrote the hook + CLI +
   helper + test.
4. **Wave 4 — Peer Review** (sub-agent USD-REVIEW-1): 4 SHOWSTOPPERS
   found — `LUNGE_V3.y_offsets` tuple-of-tuples rejected by USD
   (dropped the entire stage payload), `BOARD.run_x` 1-tuple mishandled,
   name-based prim lookup silently skipped 96% of `scene_escape_v4`
   objects (583 of 606 with `.` in names), `export_usd.py` CLI always
   tripped TypeError retry with bogus kwargs.
5. **Wave 5 — Fix + Test** (commit cb905cb): recursive `_to_usd_safe`
   converter, `_collect_board` 1-tuple unwrap, `_sanitize_usd_name` +
   `prim_name_map` for O(N) prim lookup, RNA-verified kwargs. Test suite
   extended with story-data path + special-char-names coverage.
6. **Wave 6 — Final Review** (sub-agent USD-REVIEW-2): verdict PASS.
   All 4 showstoppers + 2 test-coverage gaps resolved.
7. **Wave 7 — Polish** (commit aa76f7e): SdfPath warning guard
   (360 → 0 warnings), UTF-8 byte-level sanitization, depth limit.

### Production-scale validation (scene_escape_v4)

- 606 objects with `previz:entity` + 606 `previz:identityColor`
  (zero unmatched — 583 special-char-name objects found via
  `_sanitize_usd_name` lookup).
- 5.5s export time (vs glTF >27min — ~290x faster; bypassed the wedge).
- 16.5 MB `.usda` file.
- 0 SdfPath warnings (after polish).
- Round-trip via `pxr.Usd.Stage.Open()` confirms all data persisted.

### Open convention question for WebPreviz meta-agent

The carrier uses the NESTED `previz:entity` key-path convention
(`prim.SetCustomDataByKey("previz:entity", dict)` → nests as
`customData["previz"]["entity"]`). If the WebPreviz converter expects
a FLAT literal key (`prim.GetCustomData()["previz:entity"]`), swap to
`prim.SetCustomData({"previz:entity": dict})` — 1-line change.

Posted as a comment on the closed issue.

### Files for context recovery

- `docs/DESIGN_previz_usd_carrier.md` — design doc
- `docs/USD-RESEARCH-1_report.md` — research report (research sub-agent)
- `scripts/previz_usd_hook.py` — the hook + payload builders
- `scripts/export_usd.py` — the CLI wrapper
- `scripts/blender_kit/__init__.py` — `export_usd()` helper
- `tests/test_usd_carrier.py` — round-trip test (ALL PASS)
- `tests/usd_smoke/round_trip_smoke.usda` — smoke test artifact
- `worklog.md` Task IDs: USD-RESEARCH-1, USD-REVIEW-1, USD-REVIEW-2

### Commits (on `main`)

- `28eba07` — design: previz:entity USD carrier v1
- `caddfe4` — research: USD-RESEARCH-1 audit + smoke test
- `0e42c22` — feat(usd): previz:entity carrier — issue #1 IMPLEMENTED + TESTED
- `cb905cb` — fix(usd): USD-REVIEW-1 showstoppers A1/A2/A3/F26
- `aa76f7e` — polish(usd): USD-REVIEW-2 fixes

Issue #1 closed via GitHub API. Closing comment posted.

## Session 20 addendum — the user feedback loop (review app track)

Per the user's directive (hold previz iteration, close the missing
feedback loop): the export track now has a REVIEW PACKAGE contract and
a working web app over it.

- `scripts/export_previz_package.py` — exports `scene.glb` (all
  timeline-absolute actions + shot cameras + Aim targets) +
  `previz.json` (marker-bound shot table, ground-truth from the built
  scene) + `sfx_events.json` + stills. Fail-closed on missing cameras.
- `gitlab.com/ansgareutychisO/previz-review` — Next.js + three.js app:
  shot/frame-level playback, shot cameras (TRACK_TO rebuilt from
  exported aims), comment pins (shot+frame), JSON export back into the
  pipeline. VLM-verified framing vs ground-truth stills. GitHub push
  pending (PAT unavailable in session-20's sandbox — token was
  redacted from the persisted paste).
- The PSD revert's "possibly USD" direction stays with the web editor
  team (webpreviz); this JSON+GLB track is the SIMPLE last-resort
  mapping the user asked for, with zero hand-rolled bone math (the
  glTF exporter does all of it).
- Gotchas 83-87 (export_cameras blindness, TRACK_TO not baked, node
  name dot-stripping, mixer.setTime re-scrub law, absolute key times).

## Session 21 addendum — export-path AUDIT + USD decision (schema 2.0)

Per the user's directive (fully review the export flow, examine the USD
sync path as an alternative, audit EVERYTHING, make the review flow
robust e2e):

### USD verdict: JSON+GLB stays primary; USD is a parity-gated sidecar
Fully tackled and measured — USD cannot carry the web review flow
today:
- `export_usd.py` had an INVERTED `--export-animation` guard (gotcha
  88) — fixed; USD animation is real (1080-sample tracks, 46.8MB) and
  USD samples the depsgraph, so TRACK_TO constraints ARE baked into
  rotations (unlike glTF ACTIONS mode).
- three.js USDZLoader crashes on Blender USDC crates (gotcha 89);
  ASCII .usda parses (387 meshes / 21 cameras / 501-track clip) but
  customData is NOT exposed (gotcha 90) — the story payload is
  invisible to the web even when the geometry plays.
- Decision: JSON+GLB = source of truth for the review app; USD =
  OPTIONAL sidecar (--usd-sidecar) for USD-native consumers
  (webpreviz converter), gated by an export-time PARITY check.

### export_previz_package.py v2 (schema 2.0) — the audit closed every gap
previz.json now carries the scene module's FULL inventory (nothing
left out): 20 story collections (dialog, knockdowns w/ frames+side,
chase falls, muzzle bursts, jeep weave, speed profile, board, run
params, motion + flatness policies, lunge, rb config, drive scalars),
characters registry (identity colors from CA.Body.* materials,
boards_at), world (background + lights), 297-action manifest
(name/f0/f1/objects), camera map (optics + aim_node + parent +
CAMS_V3 motion spec), provenance (git sha, generated_at, versions,
unit_scale). FAIL-CLOSED gates: cameras-in-GLB, aims-in-GLB, shot
contiguity, every DECLARED story constant must land in the JSON,
characters non-empty, actions non-empty, USD parity (17 collections).
The gates earned their keep in-session: caught the chase_falls
list-of-dicts USD rejection (gotcha 91), a false-positive gate on
SHOTS_V3, and a usda key-parser miss (namespaced keys nest:
`dictionary previz = { dictionary entity = … }`).

### previz_usd_hook parity additions (additive, converter-safe)
`_collect_story_extras`: chase_falls (dict-of-dicts), run_params,
motion_policy, flatness_policy, run_speed, run_start_y + camera aim
kept as float lists (was lossy str(tuple)). Both collector variants
call it; the webpreviz converter reads keys verbatim.

### Review app hardened e2e (previz-review @ bcedd7d)
- Package audit banner (green/amber) + character legend + provenance
  (git sha, parity status, sidecar download) in the UI.
- Story surface: dialog onset ticks on the timeline (click-to-jump),
  per-shot beat chips (L#/KD/falls/bursts), story tab (dialog, beats,
  speed profile, characters, world, parity).
- Comments export schema 2.0 with the t = frame/fps convention FIX.
- Fail-closed loader invariant: dir name == package_id (asset/API
  routing caught mis-staging in e2e).
- E2E re-verified: framing vs ground-truth stills (f409 gunner closeup,
  hue-based 17.5k orange px — exact-RGB checks fail under ACES
  desaturation), playback cuts (S6b->S7->S8->S9), dialog jump,
  comment post/pin/export/delete, mobile, lint clean.
- Legacy schema-1.0 package kept staged (v3_4_legacy) as the
  validator's amber-state demo.

### Pushes
kit (this commit), previz (script sync + v2 export run), previz-review
(bcedd7d). GitHub still pending a fresh PAT.

## Session 22 addendum — pixel parity + NLE review UX (schema 2.1)

User feedback round on the review app (9 items) — all closed:

### Kit-side (this session)
- `blender_kit.atmo_objects()` + `export_gltf(exclude_objects=...)`:
  volume-only materials excluded from GLB + selection-state restored
  (gotcha 92 — fixes the user-reported S12a gray screen).
- `export_previz_package.py` v2.1: `atmosphere` block (bounds/density/
  color), Nishita `world.sky` capture (gotcha 93), camera shift_x/y,
  gate 8 (atmo must be OUT of the GLB and fully declared). All gates
  green; package re-exported in place as v3_4 (same id — comments
  survive).
- `render_previz_truth.py` (NEW): the canonical truth renderer —
  `--mode eevee` (anim look) / `--mode workbench` (stills look:
  studio+cavity+FlatGuidance+atmo hidden), `--stills` (shot midpoints
  from SHOTS_V3 + marker bindings), `--filmstrips` (per-shot thumbs +
  manifest), `--truth-json` (optics + projected actor fractions for
  framing-exactness checks). Sandbox OOM guard: taa 16 + 512px shadow
  cubes (llvmpipe box) — and STOP the dev server before Eevee renders.

### App-side (previz-review d323744)
- Viewer parity: flat mode (stills) MAD 5-9 / lit mode (Eevee) MAD
  8.5-27, tuned by scripts/parity_check.py (agent-browser seek ->
  screenshot -> canvas crop -> metrics + montages). Framing verified
  EXACT via NDC projection vs truth actor fractions (gotchas 94-96).
- NLE timeline (zoom/filmstrip/marker-audio/0.25-speed/pointer-capture
  drag), raycast-anchored comments (anchor_object column + export),
  dark/light theme, full keyboard map + overlay, enriched inspector
  (sfx full payloads, raw JSON per collection), mobile verified.

### Conventions locked
- The app's DEFAULT look = the stills (workbench) pipeline; "lit" is
  the aesthetic mode. Stills/filmstrips/truth all render from the
  CURRENT scene module via render_previz_truth.py (no more reusing
  stale-era stills).

---

## Session 16 (2026-09-22) — Blender 5.2 compatibility audit + usability convergence (placement lane)

Full report: placement-lab `worklog.md` + `usability/dogfood52/` +
`usability/u52a/` + `usability/u52b/` + `experiments/blender52/`.

**Compat verdict**: full kit regression (T1-T6, X1 BVH 14/14) is GREEN
on 5.2.2 UNMODIFIED; sim/rewind semantics identical 4.5<->5.2. The shim
holds end-to-end (place_on, add ops, gate, renders, ascii_vision).

**Landed this session** (d0ceccc + fece820):
- parity-verified INSIDE in classify_point (impossible 1088mm cone pen
  -> honest depth; gotcha 71)
- world_bvh depsgraph-freshen-BEFORE-key-hash (phantom 38.64mm pen on
  rotated objects; gotcha 72)
- apply_patch fresh-scene clear_scene (5.2 factory Cube leak) +
  fail_hard queue-detail print + save-blend warning + patch-json path
- viewport_capture clip warning (5.x EEVEE renders ~+4-12% brighter;
  gotcha 70) + supports_headless_gpu /dev/dri gate
- AGENTS.md front-door 4.5+5.2 framing + set-dressing verify_movers law

**Usability**: dog-food + U52-a (3 subjects) + U52-b (2 subjects) = 6/6
task success, 0 S1 across all rounds on 5.2.

**Upstream issues filed**: #2 evidence pack, #3 lean decider, #4 schema
light/camera detail, #5 machine-readable verdict, #6 argv conventions,
#7 rotated-bounds bug (S2, OPEN — first fix next session), #8
render_stats + add_light ops.

**NEXT (immediate)**:
1. Fix #7 (schema rotated-bounds: use transformed verts/BVH, not local
   bbox * matrix_world) + T-case.
2. Consider render_stats + add_light ops (#8) — high-value for the
   non-vision loop.
3. 5.2 feature leverage (queued, probe-validated): imbuf buffer APIs
   (in-memory vision loop), meshopt glTF export, Cycles maketx — see
   placement-lab experiments/blender52/PROBE_RESULTS_52.md.
4. blender-escape-previz v5 lane (skill packet at abae707) — the gate
   met v3.3 in session 15; v5 has rifle/gun-fit gates to meet.
