# rh_canvas — RH-canvas mocap clips + director statues

`scripts/rh_canvas.py` integrates the RH-canvas asset family (beulahkemp
mirrors, captured 2026-10-15) into the kit:

- **2,032 unique Mixamo mocap clips** (skeleton-only FBX, 65-bone
  `mixamorig:` rig with fingers, T-pose rest, 30 fps, ranges 7-1401
  frames starting at frame 1 — median 69, p95 343; the long tail is
  real, 59% of clips exceed 57 frames) across 19 categories —
  walk/run, gun, melee, dance, hit/death, zombie, driving… (frame
  counts per clip are IN the catalog: `frames` / `duration_s`)
- **99 static director GLTF statues** (props/scenes/vehicles too) — flat
  mannequins at real-world scale, feet on z=0, upright along +Z.
- **667 character presets** with a 9-facet taxonomy (casting/reference
  data — no 3D geometry; portraits are on-demand, never bulk).

Two more things the platform itself does NOT give you, which this module
provides: a **procedural mannequin body** (the editor's `dummy/*_body.fbx`
reference rigs are not archived — 404) and **kit-side placement**
(placement_lib's armature branch).

Everything is path-based (crowd-plugin precedent — data is never vendored
into the kit) and on-demand (no bulk mirroring).

## Quickstart

```bash
# 0. one-time: clone the data repos (path-based; the kit never vendors them)
git clone https://github.com/beulahkemp/RH-canvas-animations.git
git clone https://github.com/beulahkemp/RH-canvas-characters.git
# (any sibling dir of the kit works — discovery is by dir name; or point
#  --library / env RH_CANVAS_LIB at a clone, their parent, or any sibling)

# 1. browse (no network) — START HERE to discover the 19 categories:
python3 scripts/rh_canvas.py catalog --kind categories
python3 scripts/rh_canvas.py catalog --kind categories --search climb
python3 scripts/rh_canvas.py catalog --kind animations --search "run fast"
python3 scripts/rh_canvas.py catalog --kind animations --category DANCE_PERFORMANCE
python3 scripts/rh_canvas.py catalog --kind characters --facet gender=female --facet species=elf
python3 scripts/rh_canvas.py catalog --kind models --search farmer --json

# 2. fetch (sha256-verified, idempotent, cache at $RH_CANVAS_CACHE
#    else /home/z/rh_canvas_cache — NEVER inside the clones)
python3 scripts/rh_canvas.py fetch --ids 2846,Farmer

# 3. in a scene script (the normal path — one Blender process):
import sys; sys.path.insert(0, "<kit>/scripts")
import rh_canvas, placement_lib as pl

arm,  rep = rh_canvas.import_clip("2846", name="Runner")   # fetch-if-missing
# >>> THE PLACEMENT LAW — read this before moving anything <<<
pl.move_to(arm, (4, -3, 0), reference='origin')   # place the ARMATURE...
pl.place_on(arm, ground)                          # ...BEFORE the mannequin
mesh, mrep = rh_canvas.build_mannequin(arm)       # THEN build the body
# (already bound: import_clip leaves the clip's action on the armature;
#  re-bind or swap clips with:)
rh_canvas.bind(mesh, "2076")                      # zombie run, by catalog id

# 4. one-shot CLI equivalents (single Blender invocations):
./scripts/blrun.sh --background --python scripts/rh_canvas.py -- import-clip --id 2846 --name Runner
./scripts/blrun.sh --background --python scripts/rh_canvas.py -- mannequin --armature Runner
./scripts/blrun.sh --background --python scripts/rh_canvas.py -- bind --clip 2846 --armature RHMannequin
./scripts/blrun.sh --background --python scripts/rh_canvas.py -- import-statue --model Farmer --ground-snap
```

CLI subcommands: `catalog` (**categories|**animations|characters|models,
`--category`, `--search`, `--facet facet=value`, `--json`; animation
rows carry consumer tags `<elevated_root_motion>` /
`<static_pose>` when present — see below), `fetch --ids`, `import-clip
--id N [--name X]`, `mannequin [--name X] [--armature NAME]`, `bind
--clip <id|armature|action> --armature <name|mesh>`, `import-statue
--model NAME [--ground-snap]`. `--library` / `--cache` are accepted
before or after the subcommand; ids are STRINGS in both manifests
(law 7).

**Which rigs can receive clips (the any-rig boundary)**: any
Mixamo-family armature — the 65-bone `mixamorig:` naming, which is
what every RH-canvas clip drives AND what Mixamo-rigged character
imports carry. `bind` teacher-refuses anything else (wrong bone count
or missing prefix) with the reason in the message. The kit mannequin
is one such body; bring your own Mixamo-rigged mesh and bind it the
same way. Non-Mixamo rigs need retargeting — a documented non-goal
(v2 decision doc §2).

**Test battery** (13 rows, R1-R8b): `./scripts/blrun.sh --background
--python tests/test_rh_canvas.py --` — graceful-skips whole when the
library clones are absent. **Full-library walk** (s39):
`tests/rh_fullwalk.py` — every one of the 2,032 clips imported +
bound + posed through the public API: **2,032/2,032 PASS, 0 FAIL**
(receipt: `docs/rh_fullwalk_s39.md`).

## Consumer tags (s39 full walk)

Two browse-time tags mark clip classes that APPLY fine but behave
noticeably — visible in `catalog --kind animations` output:

- **`elevated_root_motion`** (37 clips) — climb/hang/leap/jump-down/
  backflip family; root motion carries the actor up to ~4.5 m (or
  below floor for dives). Pair with set geometry (a wall / ladder /
  platform / ledge) or the actor visibly rises into the air.
- **`static_pose`** (25 clips) — posed but near-zero within-clip
  motion: the pose-hold library class (idle poses, prone casualties,
  aiming stances). Intended for a POSE library, not a defect.

## Multi-character scenes (the s39-U1 field notes)

Four traps found by a docs-only test driver — know them before
building an ensemble:

1. **Scene range: LAST import/bind WINS.** Each `import_clip` /
   `bind` sets `scene.frame_start/end` from ITS action. With several
   characters, set the scene range yourself AFTER the last bind —
   usually the union `1 .. max(f1)` (a character whose clip ends
   earlier simply holds its last pose beyond it; a character whose
   clip is longer would get CLIPPED by a too-early scene end).
2. **Locomotion direction: clips travel where the mocap actor
   travelled.** A run clip moves the character several metres along
   its facing — measure `pose.bones['mixamorig:Hips']` world position
   at f0 vs f1 and yaw the ARMATURE (before building the mannequin) so
   the travel vector points where you want. There is no auto-facing
   (yet — candidate follow-up `align_travel()`).
3. **`--factory-startup` ships a Cube/Camera/Light.** Delete them
   (or build on an empty scene) or the default cube photobombs every
   still.
4. **One-shot CLI (`blrun.sh ... import-clip`) prints the report and
   saves NOTHING** — one Blender process per call, scene discarded.
   The normal path for anything persistent is the in-scene API
   (quickstart step 3) inside YOUR scene script.
   Tip: `build_mannequin(arm, name="Guard")` names the body (default
   `RHMannequin`, then `.001/.002/...`); `import_clip` report dicts
   carry `frame_range`, `rest_feet_z_m`, `hips_location_z_raw_cm`
   telemetry.

**Action hygiene** (ensembles + swap loops): every imported clip
action arrives pinned (`fake_user`); `bind` auto-unpins the action it
replaces, and `rh_canvas.purge_unassigned()` removes leftover pinned-
but-unassigned actions — otherwise they ship in glTF ACTIONS exports
(the AGENTS.md #104/#105 "air dance" class).

## The 9 laws

These are live-verified ground truth (RH-RECON-1: 28 binaries probed on
Blender 5.2.2; REVIEW-RH-1b: mannequin/bind/round-trip/GLB/placement
probes). The module enforces them; know them anyway.

1. **Scale law.** The FBX importer lands meters/Z-up via object scale
   `(0.01, 0.01, 0.01)` + rotation Euler X ≈ +90° (Y-up→Z-up). **KEEP that
   state; NEVER `transform_apply`** — see law 5. After default import the
   skeleton stands ~1.95 m tall, feet z≈0.03. GLTF statues need no
   correction at all (meters, Z-up, feet at z=0, upright +Z).
2. **Placement law.** *Place the ARMATURE, never the skinned mesh;
   translate/snap_z the armature BEFORE building the mannequin (rest feet
   z≈0.03 → snap offset −0.03); moving the mesh after binding breaks the
   bind.* `place_on(mesh)` on a bound mannequin explodes the skin;
   `place_on(armature)` works (placement_lib's ARMATURE branch: pose-bone
   head/tail points + bound_box; a closed box BVH stands in for contact
   math). Recipe: `move_to(arm, spot)` → `place_on(arm, ground)` /
   `snap_z(arm, 0)` → `build_mannequin(arm)` → `bind(...)` if needed.
3. **Frame-range law.** Read `action.frame_range`, NOT the scene's (the
   FBX importer leaves the scene at 1..250). Clip ranges run 7-1401
   frames (median 69, p95 343 — browse-time `frames`/`duration_s` in
   the catalog) and **start at frame 1**. `import-clip` and `bind`
   auto-set `scene.frame_start/end` from the action — mandatory,
   because
   `export_frame_range=True` (the kit's glTF export) clips to the SCENE
   range.
4. **fps-30 law.** Every clip is 30 fps. `import-clip`/`bind` set
   `scene.render.fps = 30`; set it on a fresh scene BEFORE importing a GLB
   too (glTF timing = frame/fps — the round-trip duration is only correct
   at 30).
5. **cm-fcurve law.** Hips `location` fcurve values are in RAW
   CENTIMETERS (the run clip peaks at 290.13 = 2.90 m); the 0.01 object
   scale carries the conversion. Never pre-scale, never bake — applying
   the object scale would corrupt every clip.
6. **Verify law (fetch).** Cache hit → size + sha256 check → mismatch
   deletes + re-fetches (poisoned/0-byte caches self-repair). A fresh
   download STREAMS to `<dest>.part` in 1 MiB chunks (no RAM buffers —
   statues go up to 74.5 MB) and verifies BEFORE `os.replace` — a bad
   download never touches the cache path. sha256 for BOTH manifests
   (all 99 director GLTF carry one; the characters repo's own tool skips
   the check — don't inherit the bug). Idempotent: re-runs verify + skip.
   `enc()` percent-encoding on URLs; kit User-Agent.
7. **id-string law.** ids are STRINGS in both manifests — the module
   coerces `str()` everywhere. `"2846"` not `2846`.
8. **Span definition.** The T-pose span metric is
   `|mixamorig:LeftHand.head − mixamorig:RightHand.head|`
   (wrist-to-wrist ≈ **1.476 m**), NOT the knuckle span (≈1.73 m). The
   battery band is [1.40, 1.55] m.
9. **>4-influence note.** ARMATURE_AUTO skinning gives some mannequin
   vertices >4 bone influences; the glTF exporter caps at 4 (highest
   weights, normalized) — cosmetic loss on fingers, not an error. The
   exporter prints a warning; that warning is expected.

## The mannequin (the body the platform is missing)

`build_mannequin(arm)` builds 22 capsule segments (radii 0.035-0.13 m)
from `data.bones` REST positions (the pose after import is the clip's f1,
NOT rest — build from REST), **joins** them into one mesh, then
`parent_set(ARMATURE_AUTO, keep_transform=True)`, then renames. Verified
numbers: 616 verts, **65 vertex groups** (fingers incl.), **0 zero-weight
verts**, rest bbox 1.695 × 0.388 × 1.801 m, feet ≈ z 0.

`bind` assigns the action to the **ARMATURE's** `animation_data` (a MESH
arg auto-resolves `mesh.parent` or the ARMATURE modifier object). Plain
`arm.animation_data.action = act` auto-assigns `action_slot` on Blender
5.2.2 (the module also sets it explicitly for safety). Assigning an
action to the MESH's animation_data is Blender's silent-no-op class —
the module never does that and refuses ambiguous targets.

Non-goals (v2 spec): no general retarget engine (Mixamo→Mixamo only),
no statue auto-rigging (statues are 0-bone statics — an FBX clip cannot
drive them, and they are not even T-posed), no decimation pipeline for
the 8 over-budget CJ/JT/DJ models, no portrait VLM casting, no bulk
mirror of binaries.

## Gotchas & facts

- **GLB round-trip**: mannequin + clip exports at ~163 KB (band < 5 MB).
  On reimport you get the armature (65 bones), the skinned mesh, the
  slotted action — AND a phantom **`Icosphere`** mesh the Blender glTF
  exporter emits for armature objects. Filter it by armature parentage
  (mesh.parent == armature), not by name.
- **One-object-one-action** (AGENTS.md #104/#105): bind-by-id reuses the
  session's imported action (id→action registry) so `bpy.data.actions`
  stays one-per-clip; if you import extra clips by hand, purge unassigned
  actions before glTF export.
- **R5 playback bands are family-scoped**: hips world z (0.4, 1.4) m and
  xy path > 1 m hold for WALK/RUN clips (measured on the pinned clip 2846:
  z 0.896-0.938, xy 2.895 m). HIT_DEATH_FALL clips sink below the band by
  design.
- **Statue grounding pass band**: |min_z| < 10 mm (Farmer ships at 4.8 mm;
  Armor-Tang at −6.1 mm — both PASS). `--ground-snap` offsets the
  top-level root object's z (per-root subtree minimum) when a model ever
  ships ungrounded.
- **Chinese names** appear in catalog `name` fields (display) and in GLTF
  node/material names (古代农民, 法警…) — they survive export→reimport
  round-trips (R6b pins this); `nameEn` is machine translation, search-hint
  only (159/2,137 end in `.`/`!`, the category tree carries truncations).
- **Dedup**: the animations manifest has 2,137 rows, 105 of them exact
  duplicate rows (same id/name/category/sha) — dedup by `id` → **2,032
  unique files** (the module does this at load).
- **Determinism**: two identical mannequin+clip exports are byte-identical
  (R7b). Non-determinism, if it ever appears, is documented in the battery
  results, not failed.
- **Cache** defaults to `RH_CANVAS_CACHE` else `/home/z/rh_canvas_cache`
  — never inside the clones (keeps them clean). Release-volume fallback
  (`gh release download binary-v1`) exists in the repos but is not wired
  into the kit.

## Recon citations

- RH-RECON-1 report: `/home/z/rh_recon/REPORT.md` (catalog census, binary
  sampling, the scale/retarget answers, memory budget).
- REVIEW-RH-1b probes: `/home/z/rh_recon/scripts/review_rh1b_*.py` (the
  mannequin crux, bind + slot behavior, GLB round-trip, the placement
  recipe — the mannequin build, capsule radii and placement recipe in
  `rh_canvas.py` are these verified probes).
- Spec: `blender-agent-meta/decisions/2026-10-15_rh_canvas_integration_v2.md`
  (+ the v1 decision for context).
- Data: `/home/z/RH-canvas-animations` (`assets-manifest.json`,
  `data/animations.jsonl`, `data/category_tree.json`),
  `/home/z/RH-canvas-characters` (`data/characters.jsonl`,
  `data/filter_options.json`, `data/director_models.json`,
  `director-gltf-manifest.json`).


## s20 amendments (the vision-kit vendor round)

### The placement law vs ANIMATED armatures (the docs-only drive's F1, P1)

Every imported RH armature arrives ANIMATED (the action carries
object-level root-motion channels), so `move_to`/`place_on` refuse
without an override. The working recipe:

    pl.move_to(arm, spot, reference="bottom-center", override="keyframe")
    pl.place_on(arm, support, footprint="grid", override="keyframe")

- `override='keyframe'` rebases the whole key path by the placement
  delta — every frame keeps its relative placement.
- Anchor on the **bbox bottom-center**, never the origin: a pose can
  offset the body from its origin (the sit clip leans the bbox ~0.5 m
  +Y of the origin — probe-verified; the origin-anchored move leaves
  the support BEHIND the body).
- Facing an animated actor: a manual armature yaw is CLOBBERED by the
  object-level rotation channels at the next frame_set. Use the
  wrapper-empty pattern (parent to an empty, yaw the wrapper — the UAL
  actors' contract) or accept the natural facing.

### In-scene statue API (the drive's F2)

`rh_canvas.import_statue(model_name, ground_snap=False, cache=None,
explicit_lib=None)` returns **`(list_of_root_objects, report_dict)`** —
a LIST (a GLTF import may be multi-root), unlike import-clip's
`(armature, report)` tuple. Move/rotate the ROOT objects only; the
child meshes follow. `ground_snap=True` offsets each root so its
subtree's lowest vertex sits at z=0 (the platform ships |min_z| within
a 10 mm band; the snap is the no-op-class correction).

### Browse filters (the drive's F3)

`catalog --kind animations` accepts `--tag <name>` (e.g.
`elevated_root_motion`, `static_pose`) and `--max-frames <N>` (duration
cap; frames <= N). Tags/durations are DATA-DRIVEN as of s20: a
library's manifest rows may declare `tags`/`frames` per row (the
hardcoded platform walk-sets remain as the union source), so the
fixture library's tags participate in the same filters.

### The fixture library (offline stand-in)

`RH_CANVAS_LIB` may point at the OFFLINE fixture library
(`scripts/rh_fixture_lib.py` builds it) when the platform clones are
absent — the data source went dark 2026-10-16 (beulahkemp/RH-canvas-*
404; no mirrors). Fixture clips are SYNTHETIC stand-ins: they reproduce
every contract law (65 mixamorig: bones, fps 30, frame-range-from-
action, channel-match bind guard, registry fingerprint, fake-user
hygiene) but the choreography is PROCEDURAL — the import report's
`t_pose_span_m` / `hips_location_z_raw_cm` are the ground truth for
what a clip actually does. Known deviations from the platform files
(documented, asserted by the fixture's own truth.json): the imported
object scale lands 1.0 (not 0.01) and obj rot X 0 (not +90) — the
platform's Maya-time unit-baking split is unrecoverable offline; every
consumer-behavior law holds. The battery:
`tests/test_rh_fixture.py` (13 rows, self-verifying against the
generator's truth).
