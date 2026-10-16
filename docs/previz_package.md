# previz_package.md — the previz review-package contract (authoritative)

> **Consult on demand** — when authoring story keys past the tutorial's
> examples, or when an export gate message points here. Not required
> up front: the tutorial's copy-the-shape covers the common path, and
> the gates teach the contract at failure time.

> Human-readable source of truth for the JSON+GLB previz review
> package, produced by **this kit's**
> `scripts/export_previz_package.py` (reconciled session 32, Track M).
> The TypeScript interfaces in
> `previz-review/src/lib/previz.ts` are the MACHINE-CHECKABLE source
> of truth (the review app validates against them); this doc is for
> humans and stays in sync manually. Codegen between the two is
> deliberately out of scope.
>
> Contract owners: the kit (per session-18 directive the review app's
> final UX belongs to the web editor team; the CONTRACT is what
> survives handoff). Downstream consumers: `previz-review` (the review
> app), `blender-escape-previz` (the scene repo + rollback exporter),
> the future web-editor deliverable.

## 1. Package format — `public/packages/<id>/`

| File | Contents |
|---|---|
| `scene.glb` | Geometry + ALL object actions (glTF ACTIONS mode, timeline-absolute keys `t = frame/fps`) + shot cameras (with animation + parenting) + `Aim.*` track targets. Atmosphere volumes and render-hidden helpers are EXCLUDED (gates 8/9 prove it). |
| `previz.json` | Everything else — schema 2.2 (see §2). Serialized `json.dump(previz, f, indent=1, sort_keys=True)`. |
| `sfx_events.json` | Frame-stamped event stream from the scene module's `emit_sfx_events(ctx, output_dir)`. |
| `stills/shot_<ID>.jpg` | Ground-truth rendered stills per shot (copied in via `--stills-dir`). |
| `filmstrips/` | Per-shot thumbnails + `filmstrips.json` manifest `{thumb_size, shots: {<shotId>: [{i, frame, file}]}}` (rendered by `render_previz_truth.py --filmstrips`, not the exporter). |
| `scene.usda` | OPTIONAL USD sidecar (`--usd-sidecar`): `previz:entity` customData carrier + parity gate. JSON+GLB stays the primary contract (session-21 verdict). |

The review app's loader invariant: **dir name == package_id** (asset/API
routing fails closed on mismatch). `n_sfx_events`, `stills_present`,
`usd_parity` are additive keys that appear only when their feature ran.

## 2. previz.json (schema 2.2)

Top-level keys: `schema_version`, `package_id`, `name`, `generated_at`,
`git_sha`, `shared_deps_synced`, `shared_deps_drift`, `blender_version`, `scene_module`, `fps`, `frame_start`,
`frame_end`, `render_size`, `unit_scale`, `up_axis`, `shots`,
`cameras`, `story`, `characters`, `world`, `atmosphere`, `actions`,
`sfx_events` (filename), `stills_pattern` (+ `stills_present`),
`n_sfx_events` (+ optional `usd_sidecar`, `usd_parity`), and the
**crowd block** `crowd` (v6-mode packages only — its presence bumps
`schema_version` 2.1 → 2.2; v3-mode packages are byte-for-byte
unaffected, the additive law).

### 2.1 The story block — the 24 STORY_SOURCES

**The minimum viable scene** (so you don't read the exporter to check):
`SHOTS_V3` + `CAMS_V3` + timeline markers binding each shot's `f0` to a
`CAM_*` object + the three functions (`build_scene` / `animate` /
`emit_sfx_events`). EVERY story key below is collected via
`getattr(mod, ...)` — declare what your story has and omit the rest;
an undeclared key simply carries no JSON key (the additive law; nothing
forces chase-lineage keys onto a non-chase scene). The only hard law on
what you DO declare: module-level UPPERCASE story-shaped names must map
to a known key (the nothing-left-out law, enforced at import with a
message naming your options).

`STORY_SOURCES` in the exporter maps scene-module constants to JSON
story keys; `scripts/scene_contract.py` (`CoreSceneContract`) is the
type contract and MUST stay in sync (the exporter fail-closes on
drift, and on any unmapped story-shaped module constant — the
nothing-left-out law that the 14 → 21 growth had been slipping
through).

`SYNOPSIS`, `BEATS` and `CAST` are the OPTIONAL members (session-33):

- `SYNOPSIS` (str) — the cut in one paragraph, exported as
  `story.synopsis`.
- `BEATS` (list of `(id, t_seconds, kind, label)`) — the GENERIC story
  vocabulary for films that aren't chases: exported as `story.beats`
  with a derived `frame`. The escape-scene's rich keys (knockdowns
  with style/x_off, muzzle bursts with cadence) remain the deep
  vocabulary; `BEATS` is the portable layer any scene can use.
- `CAST` (dict `name -> {"role": str, "root": str}`) — the semantically-neutral
  characters seed, exported as `story.cast` AND unioned into the
  top-level characters registry (BOARD/RUN_PARAMS remain the
  escape-lineage seeds). `root` is OPTIONAL and overrides the
  `<name>.Root` naming convention for characters whose root object is
  named differently (the gate still requires every character's root
  to exist in the scene).

Scenes that don't author them carry no keys and downstream consumers
must hide the surfaces when absent (the additive law).

| Scene constant | JSON key | Type / shape |
|---|---|---|
| `SYNOPSIS` | `synopsis` | str (OPTIONAL — the cut in one paragraph) |
| `BEATS` | `beats` | list of `{id, t, frame, kind, label}` (OPTIONAL, s33 r2) |
| `CAST` | `cast` + characters seed | dict `name -> {role}` (OPTIONAL, s33 r2) |
| `CAMS_V3` | `cam_specs` | list of `{name, loc0, loc1, lens_mm, aim, parent_jeep, shake_amp}` |
| `DIALOG` | `dialog` | list of `{clip, onset_frame}` |
| `KNOCKDOWNS_V3` | `knockdowns` | list of `{id, t_hit, frame, x_off, side, style}` |
| `CHASE_FALLS_V3` | `chase_falls` | dict → list of `{chase_index, t_hit, frame}` |
| `MUZZLE_BURSTS_V3` | `muzzle_bursts` | list of `{f0, f1, every_n}` |
| `JEEP_X_V3` | `jeep_weave` | list of `{t, x_off}` |
| `_V3_SEG` | `speed_profile` | list of `{t0, t1, v0, v1}` |
| `BOARD` | `board` | dict per actor `{run_end, apex, land, seat_local, yaw_end, pose_name, offset}` |
| `RUN_PARAMS` | `run_params` | dict of dicts (numbers / strings) |
| `MOTION_POLICY` | `motion_policy` | `{intended_static, intended_subject_tree}` |
| `FLATNESS_POLICY` | `flatness_policy` | dict `{f0, f1}` per object |
| `LUNGE_V3` | `lunge` | dict (`y_offsets` → `{t, y}` list + scalars) |
| `RB_FALLS` | `rb_falls` | list of ints |
| `RB_KD` | `rb_kd` | list of strings |
| `T_DRIVE` | `t_drive` | float (belt start, seconds) |
| `BARRICADE_T_V3` | `barricade_t` | float |
| `BARRICADE_Y_V3` | `barricade_y` | float |
| `RUN_SPEED` | `run_speed` | float |
| `RUN_START_Y` | `run_start_y` | float |
| `TOTAL_FRAMES_V3` | `total_frames` | int |
| `HERO_MODE` | `hero_mode` | str (`capsule` \| `ual`) |

`SHOTS_V3` is deliberately NOT in the story block — its data lands in
the top-level `shots` array, marker-bound to cameras (ground truth,
gate 3). `time → frame` convention: `frame = round(t * fps) + frame_start`.

### 2.2 The crowd block (schema 2.2, v6-mode only)

`{engine, seed, dt, cache_sha, params_sha, code_sha, n_agents,
n_ticks, clips, fields, knockdowns, tiers: {t1, windows, pins}}` —
cache digests prove sim/code/params identity; `tiers.windows` is the
per-shot foreground map the review-app chips read. Produced only when
the scene ran crowd v6 (loaded via `--crowd-plugin`, see §4).

### 2.3 characters registry

Per character: `{name, root_object, identity_color (CA.Body.<name> /
Mat.UAL.<name> material), rig (capsule|ual), boards_at? (the BOARD
land frame), role? (CHARACTER_ROLES, s26)}`. `boards_at` is
PER-CHARACTER — never a scene-module constant.

## 3. The 22 fail-closed gates (export post-checks)

Execution order in the exporter is gates 18/19/20/21 then 15/16/17 —
numbering is historical. All gates read the EXPORT (the GLB/JSON), not
the scene.

| # | Gate | Skip condition |
|---|---|---|
| 0 | version-drift: scene must be the newest `scene_escape_v*` in the resolved scene dir | `--allow-stale` (on purpose) |
| 1 | every shot's camera node exists in the GLB | never (core) |
| 2 | every camera's `Aim.*` target node exists in the GLB | never |
| 3 | shot table contiguous + spans the full frame range | never |
| 4 | every DECLARED story constant landed in the JSON | never (declared-but-missing = FAIL) |
| 5 | characters registry non-empty, root objects exist | never |
| 6 | actions manifest non-empty | never |
| 7 | USD story parity | only with `--usd-sidecar` |
| 8 | atmosphere objects OUT of the GLB + fully declared | never |
| 9 | render-hidden helpers OUT of the GLB | never |
| 10 | rigged heroes arrive RIGGED (skins present) | no armatures in scene |
| 11 | crane/dolly cameras actually MOVE in the export | static cams (spec loc0 == loc1) |
| 12 | belt-rider audit (treadmill staging) | no `t_drive` in story, or no `BeltRoot` translation track |
| 13 | one-object-one-action (no node in >1 distinct animation) | never |
| 14 | bone-carried-prop phantom-offset proximity (static bone-children FAIL) | no bone-carried props |
| 15 | crowd twin coverage incl. the `.Skin` presence law | no crowd block (v3 lineage) |
| 16 | tier exclusivity (capsule/RigWrap flips exactly on cuts) | no crowd block |
| 17 | phase-slide speed-band + lift-only bob + teleport bounds | no crowd block |
| 18 | hero aim coherence (head/chest/stance vs bore) | no "Gunner" character with `boards_at`, or `hero_gates.py` missing (WARN, never silent) |
| 19 | FX off-state (FX.* scale OFF outside declared windows) | no `FX_EVENT_WINDOWS`; FX nodes present without windows → WARN |
| 20 | motion continuity (sprint/aim sweep maxima, s31 sign-flip classes) | no Gunner `boards_at` / hero_gates missing |
| 21 | capsule orientation (belt-local heading law, s31) | no `Zed.*` capsule anchors (regex matches nothing) |

Plus the session-32 kit-side fail-closed checks: scene_contract ↔
STORY_SOURCES sync; unmapped story-shaped constants; shadowed scene
import (`mod.__file__` must resolve under `--scene-dir`); crowd v6
without `--crowd-plugin`; plugin path mismatch vs the engine the scene
loaded.

## 4. The scene-module contract + the crowd plugin law

`scripts/scene_contract.py` defines three Protocols (documentation +
`__annotations__` registry; the exporter duck-types, never
isinstance-checks):

- **CoreSceneContract** — the 21 constants + `build_scene() -> ctx`,
  `animate(ctx, start_frame, n_frames)`, `emit_sfx_events(ctx, output_dir)`
- **CrowdSceneContract** — `CROWD_MODE: 'v3' | 'v6'`
- **HeroSceneContract** — `FX_EVENT_WINDOWS: dict`, `FX_WORLD_LITTER: tuple`

**Crowd engines load ONLY via `--crowd-plugin <path>`** (dir or
`__init__.py`; the path-based registry in scene_contract.py also
accepts programmatic registrations). Per the session-27 directive,
crowd code lives in `blender-crowd-kit` (now VENDORED back as the
`vendor/blender-crowd-kit` git submodule, r043) or the
previz repo (`crowd_v6`) — NEVER in this kit's namespace
(`scripts/crowd/` is a vendored re-export stub over the submodule).
`--crowd-mode v6`
without a resolvable plugin fails closed before the build. `hero_gates`
(gates 18-21) loads from the kit's own scripts under a private module
name — the scene repo's copy can never shadow it.

**`--scene-dir`** (explicit, or derived from `--crowd-plugin`'s parent)
goes to `sys.path[0]` before the kit's own scripts — the scene repo's
sibling deps must never be shadowed by the kit's copies.

## 5. The comment contract (bidirectional feedback loop)

**In-app storage** (Prisma/SQLite, `CommentDto`): `{id, packageId,
shotId, frame, anchorObject?, anchorObjects?, author, body, createdAt}`.

**Pipeline export** (`project/previz_comments_<pkg>.json` in the scene
repo, via the app's export API — the shape the scene author consumes):
`{schema_version: "2.1", package_id, package_schema, exported_at, fps,
shot_count, comment_count, comments: [{shot, shot_frames: [f0, f1],
frame, time_s (t = frame/fps), anchor_objects, anchor_object, author,
body, created_at}]}`.

**3-layer durability** (session-30, after a sandbox reset ate 23 rows):
1. Prisma/SQLite (the live DB; dies with the sandbox — `db/` is gitignored)
2. `db/mirror/comments_journal.jsonl` (append-only GitLab-tracked audit
   trail: one create/delete/restore event per line) + per-package
   snapshots `db/mirror/comments_<packageId>.json` (atomic tmp+rename,
   self-healing on read)
3. Browser localStorage mirror (`comment-backup.ts`) — the reviewer's
   own copy survives even if both server layers die

Proven by 6 user comments on v6_0 (drove the session-31 gate-20/21
fixes) — the loop closes: comment → export → scene fix → re-export →
re-review.

## 6. Export pipeline topology (session-32 reconciliation)

- **THIS KIT** (`scripts/export_previz_package.py`) is the production
  exporter — schema 2.2, 22 gates, `--crowd-plugin`, `--scene-dir`,
  contract checks. Regression suite: `tests/test_export_previz_package.py`
  (tier A fixture + tier B real-scene byte-pin against
  `tests/baselines/v6_1_previz.json`, params_sha pin `1f581a18…`).
- **blender-escape-previz** keeps its own exporter as the ROLLBACK
  FALLBACK for the 3-export window; `step8_export_v6.sh` already calls
  the kit's exporter. Only after 3 consecutive green kit exports does
  the previz copy reduce to a shim.
- Kit-side runs record the CWD repo's `git_sha` (run from the scene
  repo for scene-lineage provenance).

## 7. Schema changelog

- **2.0** (session 21): full story inventory + characters + world +
  actions manifest + camera map + provenance; fail-closed gates 1-8.
- **2.1** (session 22): `atmosphere` block, Nishita `world.sky`,
  camera shift_x/y, gate 8.
- **2.2** (session 28): the crowd v6 block (cache digests, clip
  registry, KD manifest with per-beat coverage, tier map + pins) —
  v6-mode packages only; gates 15-17. Sessions 30/31 added gates
  18-21 + the character `role` key (additive).
- **2.2 + s33 provenance** (session 33, additive): `shared_deps_synced`
  (`true|false|unknown`) + `shared_deps_drift` in the provenance block
  (the shared-interop sync state at export time —
  `docs/SHARED_SYNC.md`); `sfx_events` is written ONLY when the scene
  module has an sfx emitter; the exporter stamps `.export_ok` in the
  output dir after all gates pass (staging asserts it); `story.synopsis`
  (the SYNOPSIS constant, optional). NOTE: the GLB is per-process
  index-order-nondeterministic (~0.016% of bytes, structure-identical,
  gate-proven equivalent) — byte-parity claims apply to previz.json +
  sfx_events.json only.
