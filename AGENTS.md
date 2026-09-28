# AGENTS.md — Consumer Agent Guide

> Read this first if using the kit to make scenes. If you're the meta-agent
> working ON the kit, read `.agents/SKILL.md` instead.

## What this kit is

Headless Blender 4.x/5.x LTS previz toolkit for LLM agents in a no-root,
no-GPU, 4GB RAM container. Build scenes via `bpy` scripts or JSON patches,
render with Workbench/EEVEE/Cycles, verify with VLM + programmatic audits,
export to glTF for web preview.

## Quick start

```bash
./install.sh                    # one-time: downloads Blender 5.2 LTS, libEGL, Pillow
cp scripts/scene_template.py scripts/my_scene.py  # copy + edit build_scene()/animate()
./scripts/blrun.sh --background --python scripts/my_scene.py -- \
    --output output/my_scene --dry-run --scene-name my_scene  # validate structure
```

## The core loop: perceive → reason → act → verify

```
1. PERCEIVE: query scene state (scene_schema.py)
2. REASON:   decide what to change
3. ACT:      emit patch (apply_patch.py) or edit scene script
4. VERIFY:   viewport_capture.py → VLM critique → iterate if issues
```

Target: **<30s per iteration**. Use Workbench (`--quality previz`) for
geometry checks (~0.2s/frame). Use EEVEE/Cycles only for materials/lighting.

## Canonical workflow

```bash
# 1. Dry-run (instant, no render — validate scene builds)
./scripts/blrun.sh --background --python scripts/my_scene.py -- \
    --output output/my_scene --dry-run --scene-name my_scene

# 2. Viewport check (4-angle grid, workbench, ~2s)
./scripts/blrun.sh --background --python scripts/viewport_capture.py -- \
    --scene my_scene --output output/my_scene/grid.png \
    --angles front,side,top,persp --engine workbench --grid-cols 2

# 3. VLM critique the grid
z-ai vision -p "4-angle contact sheet. List objects per view. Top view layout. Issues?" \
    -i output/my_scene/grid.png

# 4. Patch fixes without full rebuild (~2s)
cat > /tmp/patch.json << EOF
{"scene":"my_scene","frames":24,"mutations":[
  {"op":"set_location","id":"Cube","location":[1,0,0.6]},
  {"op":"render_viewport","output":"output/my_scene/check2.png","angle":"persp","engine":"workbench"}
]}
EOF
./scripts/blrun.sh --background --python scripts/apply_patch.py -- --patch /tmp/patch.json

# 5. Structural validation (deterministic geometric checks)
./scripts/blrun.sh --background --python scripts/validate_scene.py -- \
    --scene my_scene --output output/my_scene/validation.json --fail-on-issues

# 6. Animation check (keyframe contact sheet)
./scripts/blrun.sh --background --python scripts/keyframe_contact_sheet.py -- \
    --scene my_scene --output output/my_scene/motion.png --frames 6 --grid-cols 3

# 7. Ship: full render + MP4 + glTF + .blend
./scripts/blrun.sh --background --python scripts/my_scene.py -- \
    --output output/my_scene --engine BLENDER_EEVEE_NEXT --frames 24 \
    --quality preview --encode-mp4
./scripts/blrun.sh --background --python scripts/export_gltf.py -- \
    --scene my_scene --output output/my_scene/scene.glb --frames 24
./scripts/blrun.sh --background --python scripts/save_blend.py -- \
    --scene my_scene --blend-out output/my_scene/scene.blend
cp viewer/index.html output/my_scene/  # interactive 3D preview
```

## Tool reference

### blrun.sh — the wrapper (always use, never call blender directly)
```bash
./scripts/blrun.sh --background --python <script.py> -- [script args after --]
./scripts/blrun.sh --warm-cache    # one-time EEVEE shader cache warmup (~30s)
./scripts/blrun.sh --help          # wrapper help
```
Env vars: `BLENDER_BIN`, `BLENDER_DISPLAY` (default `:99`), `KEEP_XVFB=1`
(reuse Xvfb across runs), `BLENDER_HOME` (caches), `BLENDER_KIT_LIBS`.
Handles: Xvfb lifecycle, libEGL `LD_LIBRARY_PATH`, `--python-use-system-env`
(so `import blender_kit` works), signal traps, stale X locks, fail-closed
gate (grep for Python errors → nonzero exit).

### scene_template.py — copy-and-edit scene template
Pattern: `build_scene()` → returns context dict; `animate(ctx, ...)` →
keyframes; `main()` → `common_parser()` + `configure_render()` + `render()`.
Shared flags (via `common_parser`, also in scene_interior_room.py etc.):
`--output DIR` (required), `--engine CYCLES|BLENDER_EEVEE_NEXT|BLENDER_EEVEE|BLENDER_WORKBENCH`,
`--frames N` (default 24), `--start N` (default 1), `--samples N`,
`--w W --h H`, `--still N` (render single frame N instead of animation),
`--dry-run` (print scene summary, no render), `--quality previz|viewport|draft|preview|final`
(sets engine+resolution+samples), `--encode-mp4` (ffmpeg after frames),
`--aa off|fxaa` (Workbench AA), `--shade studio|flat` (Workbench lighting),
`--png` (force PNG instead of JPEG), `--fps N` (MP4 framerate),
`--scene-name NAME` (in metadata.json).

### apply_patch.py — JSON patch mutations (no full rebuild)
```bash
./scripts/blrun.sh --background --python scripts/apply_patch.py -- \
    --patch /tmp/patch.json [--save-blend out.blend] [--export-schema out.json]
./scripts/blrun.sh --background --python scripts/apply_patch.py -- \
    --patch-json '{"scene":"my_scene","mutations":[...]}'  # inline
./scripts/blrun.sh --background --python scripts/apply_patch.py -- --list  # list all ops
```
Patch format: `{"scene":"module"|"load_blend":"file.blend", "frames":N, "mutations":[...]}`
Mutation ops (35): `set_location`, `set_rotation`, `set_scale`,
`set_material_color`, `set_material_roughness`, `set_material_metallic`,
`delete_object`, `duplicate_object`, `set_camera_location`, `set_camera_lens`,
`set_light_energy`, `set_light_color`, `set_world_strength`, `set_exposure`,
`set_frame`, `render_viewport`, `add_cube`, `add_sphere`, `add_cylinder`,
`add_cone`, `add_torus`, `add_plane`, `add_empty`, `move_to`, `place_on`,
`seat_at`, `snap_z`, `physics_settle`, `physics_place`, `physics_oracle`,
`physics_gate`, `audit`, `seam_views`, `heat_bake`, `clear_bvh_cache`.
Each op uses `_require()` for clean errors on missing/wrong-type keys.
Add_* ops: `id` required (refuses if name exists), `size`/`radius`/`depth`
are FINAL world dims (data-baked, object scale stays 1,1,1), `location` =
CENTER (not bottom — seat with `place_on` afterwards). Composition:
`add_*` → `place_on`/`physics_place` → `audit` in one patch chain.
See `/kb/placement_and_physics.md` for placement/physics op details. Headlines:
- `audit` op exits non-zero on penetration — chain after every placement change
- `place_on(id, supports)` = one-shot, 0.0mm error, solves Z only (keeps x/y)
- `seat_at(id, seat)` = slot seating via anchor EMPTY; `snap_z(id, z)` = exact world z
- `physics_settle/place/oracle/gate` — gravity finds the pose; oracle WITNESSES why X can't sit; gate = scene-level rejection with executable fix queue
- `audit` pair states: PENETRATING (penetration_mm) / TOUCHING / NESTED / CLEAR (clearance_mm)
- Audit only sees pairs within `clearance_pad_mm` (default 100) — floaters >300mm appear in NO pair; use `physics_gate` or `scene_schema --with-bounds` for scene-wide floating checks
- Seam verification: plain viewport 0/4 decidable; heat render 4/4 (RED contact / GREEN <5cm / GRAY far)

### viewport_capture.py — multi-angle viewport screenshots
```bash
./scripts/blrun.sh --background --python scripts/viewport_capture.py -- \
    --scene my_scene --output grid.png \
    --angles front,side,top,persp --engine workbench --grid-cols 2
# Single close-up:
... --angles custom --custom-loc "3,0,1.5" --engine workbench --no-grid
# Ring of 6 cameras:
... --ring 6 --engine workbench --grid-cols 3
# Load existing .blend:
... --load-blend scene.blend --output grid.png --angles persp
```
Angles: `front,side,top,persp,back,right,active,custom` or `--ring N`.
Engines: `workbench` (default, ~0.8s), `eevee` (~2s warm), `cycles` (~50s).
`--target X,Y,Z` (look-at; default = scene bounding box center).
`--lens MM` (default 50). `--w W --h H` (default 480×360).
`--no-grid` = individual files (output is a file for single angle, dir for multi).
`--samples N` (for eevee/cycles).

### keyframe_contact_sheet.py — animation verification
```bash
./scripts/blrun.sh --background --python scripts/keyframe_contact_sheet.py -- \
    --scene my_scene --output motion.png --frames 6 --grid-cols 3 --engine workbench
# With orbit camera:
... --orbit --orbit-radius 8 --orbit-height 4
```
Samples N frames evenly across the animation range, renders each at low
quality, stitches into a grid with frame number labels. `--start`/`--end`
override range (default = scene's frame_start/frame_end). `--orbit` =
revolving camera. Engines same as viewport_capture.

### scene_schema.py — JSON scene state export
```bash
./scripts/blrun.sh --background --python scripts/scene_schema.py -- \
    --scene my_scene --output scene.json --with-bounds
# Or load existing .blend:
... --load-blend scene.blend --output scene.json --with-bounds
```
Exports: objects (id, type, location, rotation, scale, materials, mesh
stats), lights, cameras, animation (keyframes with interpolation), world,
frame range. `--with-bounds` adds world-space bounding boxes.
Use to query state as data ("where is the cube?") instead of reading bpy.

### export_gltf.py — export scene as .glb for web preview
```bash
./scripts/blrun.sh --background --python scripts/export_gltf.py -- \
    --scene my_scene --output scene.glb --frames 24
```
Preserves: meshes, PBR materials (Principled BSDF), cameras, punctual
lights (SUN/POINT/SPOT), keyframe animation. Loses: AREA lights, modifiers
(baked), procedural shaders, volume materials (tag `kit_atmo` to exclude),
ray-visibility (kit excludes `hide_render` objects). See gotchas #44-54.

### save_blend.py — save .blend + optional high-quality still
```bash
./scripts/blrun.sh --background --python scripts/save_blend.py -- \
    --scene my_scene --blend-out scene.blend \
    --still-frame 12 --still-out still_12.png --still-samples 32
```
`--still-frame N` renders frame N with Cycles at `--still-samples` (default
64) and `--still-w`×`--still-h` (default 960×540).

### validate_scene.py — structural validator
```bash
./scripts/blrun.sh --background --python scripts/validate_scene.py -- \
    --scene my_scene --output validation.json --fail-on-issues
```
Checks: floating objects (no support below), below-floor, suspicious
intersections (overlap >5% of smaller object), above-ceiling. Deterministic
bounding-box analysis — no rendering needed. `--fail-on-issues` exits
non-zero if P0/P1 found. Warns on empty/light-only scenes.

### agent_server.py — live viewer bridge (SSE)
```bash
python3 scripts/agent_server.py --port 8765 --workdir /tmp/session
```
`GET /api/events` (SSE stream), `POST /api/event` (push progress events),
`GET /api/scene.glb` (auto-detects file changes), `GET /api/scene.json`,
`GET /api/status`. File watcher on scene.glb auto-publishes `scene_updated`.
Agent copies .glb to workdir + POSTs events; viewer auto-refreshes.

### polyhaven.py — Poly Haven CC0 assets (HDRIs, models, textures)
```python
from polyhaven import search_assets, add_to_scene, load_hdri
results = search_assets("sofa", type="models", limit=5)  # semantic search
add_to_scene("modern_sofa_01")  # download + import (md5-verified cache)
load_hdri("/cache/outdoor_sun_01_2k.hdr", strength=1.0, rotation_z=0)
```
~2,400 CC0 assets (993 HDRIs, 857 textures, 521 models). Keyless API
(unique `User-Agent` required). Real-world scale in meters (no rescale).
Default 2k resolution (safe for 4GB RAM). Cache to `POLYHAVEN_CACHE` env.

## Quality presets

| Preset | Resolution | Engine | Use case | ~Time/frame |
|--------|-----------|--------|----------|-------------|
| `previz` | 240×135 | Workbench | Ultra-fast geometry check | ~0.2s |
| `viewport` | 960×540 | Workbench | vid2vid guidance track | ~0.05s |
| `draft` | 320×180 | EEVEE | VLM iteration | ~0.5s warm |
| `preview` | 640×360 | EEVEE | Final preview animation | ~2s |
| `final` | 960×540 | Cycles | Final still | ~50s |

**Key speed facts** (full benchmarks: `/kb/render_speed.md`):
- **AA dominates Workbench render time** — `render_aa='8'` = 92% of wall time;
  `'OFF'` is 5-6× faster (60-90ms/frame at 960×540). Jaggies are fine for previz.
- **Cold start dominates batch renders** — build + RB bake ~2.5 min.
  Batch re-renders into ONE contiguous range. llvmpipe default threads optimal.
- **JPEG q85** frames ~15× smaller and 23-35ms/frame faster than PNG (`--png` to force).
- **EEVEE memory**: peaks at 1.6GB for 273-object scenes on 5.2 (40% of 4GB).
  Cycles is stable ~355MB regardless of object count. Workbench ~480MB.
- **After every speedup, re-profile** — the bottleneck moves.

## Gotchas (read these — they save hours)

### Engine & rendering
1. **Always use blrun.sh** — it handles Xvfb, libEGL, `--python-use-system-env`, signal traps. Never call `blender` directly.
2. **EEVEE needs Xvfb** — Cycles doesn't. blrun.sh always starts Xvfb.
3. **EEVEE first render is ~28s cold** — run `blrun.sh --warm-cache` once per container.
4. **EEVEE OOM risk**: peaks at 1.6GB for 273-object scenes on 5.2. Use Workbench for previz, Cycles for final. Avoid EEVEE for 100+ objects on 4GB.
5. **5.x EEVEE renders ~4-12% brighter** than 4.5 — may clip high-key scenes. Reduce exposure ~-0.5 EV on 5.x.
6. **Workbench reads `mat.diffuse_color`** not Principled Base Color. `make_material()` sets both; `set_material_color` op sets both.
7. **AgX crushes previz colors** — kit forces `view_transform='Standard'` for previz/workbench. Use AgX only for final Cycles.
8. **Workbench background** = world color (or black if no world). Set a flat neutral world for previz (the `viewport` preset does this).
9. **Volumes render as opaque shells** in Workbench — tag atmosphere objects `ob["kit_atmo"]=True` (preset hides them).
10. **AA dominates Workbench render time** — `--aa off` is 5-6× faster. Use `--aa fxaa` only for human-reviewed stills.

### Scene building
11. **Cube "floating"**: `primitive_cube_add(size=S, location=(0,0,Z))` puts the ORIGIN at Z. Bottom = Z - S/2. For a cube to rest on z=0: `location=(0,0,S/2)`.
12. **`set_location` moves the ORIGIN** — on origin-baked meshes (world coords in vertex data) this acts relative. Use `move_to` for world-space moves.
13. **`transform_apply(scale=True)` zeroes location** (4.5.13) — avoid it. Pass `scale=` to primitives instead.
14. **Vertex-baked origins detonate transforms** — build geometry around local (0,0,0) for anything that will be animated/simulated.
15. **Animated location channels clobber placement** — placement ops refuse by default; `override:"keyframe"` inserts a visible key.
16. **Boolean keyframes need f=1 anchors + CONSTANT interpolation** — a mid-shot HIDE without f=1 anchor evaluates hidden from frame 1.
17. **`action.fcurves` moved in 5.x** — use `iter_fcurves(action)` from blender_kit (handles 4.x/5.x).
18. **`mat.use_nodes = True` deprecated in 5.x** — use `ensure_use_nodes(mat)` from blender_kit.
19. **`.blend` files are forward-only** — 5.2 saves format 1701; 4.x can't open. Use glTF for cross-version interchange.

### VLM verification
20. **VLM is your only eye but sycophantic** — describe colors as OUTPUT ("name the shirt color"), never as input assumptions.
21. **Validate image BEFORE trusting VLM** — empty/low-contrast/silhouette renders make VLM hallucinate. Pixel-classify subjects first.
22. **Feed macro crops, not wide lineups** — one subject filling the frame beats four at 15% each. `hide_render=True` on others.
23. **VLM can't show motion** — "is it running?" is unanswerable from one still. Use keyframe contact sheets or programmatic probes.
24. **Backlit subjects vanish** — add neutral fill light (~90W POINT) for dusk/sunset scenes.
25. **VLM noise vs reality** — VLMs flag geometric issues that don't exist (e.g. "floating" when grounded at z=0). Verify with `validate_scene.py` or `scene_schema.py --with-bounds` before acting.
26. **VLM audits hallucinate off BLACK frames** — verify image luma/mean before trusting any visual audit.
27. **ASCII vision packs** (`scripts/ascii_vision.py`) — turns renders into
    text a blind agent can read: stats flags, color-class grid, luma/edge
    panels, connected-component table with fractional coordinates, zoom tiles.
    **Pack-first for geometry/grounding/count/layout; VLM for semantics/hue/gist.**
    Measured scorecard: ASCII WINS dark/monochrome renders (+0.32), tiny <2%
    objects (+0.12), near-empty traps; VLM keeps semantics, crowd gist, hue.
    Decisive R4 test: pack-reader found planted floater at exact truth
    coordinates, fabricated nothing; VLM hallucinated floats on grounded
    actors, cited non-existent evidence. **Fabricated evidence > blindness.**
    Disagreement between pack and VLM = automatic programmatic probe.
    Quick: `python3 scripts/ascii_vision.py IMG --auto --cols 96 --components --tiles 2`
    Full protocol: `/kb/ascii_vision.md`

### Placement & physics
28. **Use `audit` op after every placement change** — chains into the same patch, exits non-zero on penetration.
29. **`place_on` solves Z only** (keeps x/y) — move_to first if the object is over the wrong spot.
30. **`place_on` is single-contact-plane** — seated figures spanning cushion+floor need `seat_at` + anchor empties.
31. **Physics ops need named movers** — `objs:["Mug"]` makes everything else terrain. `objs:null` = whole-scene free-fall (almost never wanted).
32. **RB sim pose lives only in `matrix_world`** — RNA `location` keeps spawn pose. Commit before reading geometry.
33. **RB point cache survives object teardown** — always `frame_set(1)` before every sim.
34. **BOX collision is centered on ORIGIN, not bbox** — off-origin mesh gets displaced collision. Use CONVEX_HULL for origin-offset geometry.
35. **Bullet depenetrates to exact rest** on flat contacts but can eject wedged overlaps sideways — refuse-by-default, use `repair_penetrations:"physics"` for recorded repairs.
36. **Treadmill law**: belt streams backward, subject world-static → world-static + visible = paces the subject ("rider"). Compose FX/debris with the belt or hide them.

### Color discipline (vid2vid guidance)
37. **Environment = white/grey value ladder** (road 0.62, sidewalk 0.78, buildings 0.92). NO chromatic environment materials.
38. **Subjects = ONE color per body** (head, torso, arms, legs all take the actor color). ~3 chromatic classes total.
39. **Light BASE colors are chromatic traps** in Workbench (reads diffuse_color, not emission) — keep light bases neutral.
40. **STUDIO shade beats FLAT** on white world — greyscale normal shading gives shape readability; subject chroma identical.

### Sub-agent orchestration
41. **One asset module per sub-agent** — giant briefs ("build scene + animate + verify") time out. Each sub-agent <5 min.
42. **On timeout, harvest artifacts** — sub-agent may have delivered 80% of work on disk. Check output paths before relaunching.
43. **Gate sub-agent code** — audits + truth-render + neutral VLM readback before integration.

### glTF / export
44. **glTF loses AREA lights** — accept for web preview; `<model-viewer>`'s `environment-image="legacy"` adds ambient.
45. **glTF exports IGNORE ray-visibility** — `hide_render`/`visible_camera=False` helpers leak into GLB. Kit excludes them; `export_previz_package` gates this.
46. **glTF ACTIONS mode doesn't bake constraints** — TRACK_TO cameras export pointing at raw euler. Use SCENE bake mode for baked transforms, or export aim targets as separate nodes.
47. **glTF `export_cameras` defaults False** — always export through `blender_kit.export_gltf` (sets it) or set the flag.
48. **three.js sanitizes node names** — `Aim.CAM_S6b` loads as `AimCAM_S6b`. Dot-free comparison for node lookups.
49. **`<model-viewer>` struggles with large scenes** (>100 objects) — render stills alongside .glb as fallback.
50. **100MB git limit** — big .blend files ship as release assets only. The blend is reproducible from HEAD via the pack script.
51. **glTF preserves**: meshes, PBR materials (Principled BSDF only), cameras, punctual lights (SUN/POINT/SPOT), keyframe animation. **Loses**: AREA lights, modifiers (baked), procedural shaders, collections, compositing nodes, volume materials (opaque shells — tag `kit_atmo` to exclude).
52. **three.js `mixer.setTime` breaks LoopOnce+clamp on re-scrub** — pre-pad tracks with `(0, firstKeyValue)`, use LoopRepeat. Blender glTF keys are TIMELINE-ABSOLUTE at `t = frame/fps` (not `(frame-1)/fps`).
53. **three.js physical lighting**: divides diffuse by π; glTF punctuals are 683× Blender watts. Viewer-side: `l.intensity /= 683`. Do parity math in LINEAR.
54. **USD rejected as web format** — three.js USDLoader crashes on USDC crates; ASCII .usda parses but customData invisible. JSON stays story source of truth; USD as parity-gated sidecar.
Full export reference: `/kb/glTF_export.md`

### Git & environment
55. **GIT IS THE DISK** — push to both GitHub + GitLab on every micro-step. Never force push.
56. **GitLab WAF blocks ~1/3 of pushes** — retry up to 8× with 5s sleep. Use `oauth2:TOKEN` format (not `TOKEN` as username).
57. **Watchdog reverts `/home/z/my-project/` every ~20s** — work in `/home/z/blender-kit/` (outside watchdog scope).
58. **Background processes die between tool calls** — long renders must run inside one Bash call with timeout, or use `render_daemon.py` (double-fork to PID 1).
59. **After ANY git merge** — `grep -rn "<<<<<<<" scripts/` + smoke-test one blrun invocation BEFORE relaunching long renders.
60. **GitHub Release != published** — `PATCH /releases/<id> {"draft":false}` after upload. Verify via API before saying "live".
61. **Sync-copy clones carry origin=local** — `git clone /home/sync/<repo>` sets origin to stale local copy. Re-point to GitHub before updates.

### Blender version compat
62. **Kit runs on 4.5 and 5.2 LTS unchanged** — compat shim normalizes engine id, fcurves API, sky type, use_nodes. Write 4.x idioms; kit translates.
63. **Default install: 5.2 LTS** (supported until July 2028). If container has 4.5, kit still works.
64. **`gpu.init()` on 5.2** boots EGL headless BUT crashes in no-GPU containers (EGL_BAD_PARAMETER → segfault). Xvfb remains required on llvmpipe.

### 104. Bake-input pools are NOT export payload — purge unassigned actions before glTF (session 25)
glTF ACTIONS mode exports EVERY `bpy.data.actions` entry. The UAL bake
leaves the per-actor library POOLS (Sprint_Loop, A_TPose, Pistol_*,
Rifle_Aim source clips — ~188 full-rig actions) alive via fake users;
in Blender they are inert (only the ASSIGNED action evaluates), but a
viewer that plays every clip blended ~141 weight-1 actions per bone
into pose mush: garbled arms, the rifle riding a mushed hand — the v5
"air dance" (user: "gun doing air dance, not attached"). Law: bake
inputs are not export payload. Keep exactly the actions ASSIGNED to
objects (one-object-one-action contract), delete the rest BEFORE glTF
export AND manifest collection, then re-run orphans_purge. It pays for
itself: 598 -> 414 actions, GLB 26MB -> 21MB, and the historical
~50-minute exports (598 actions force-sampled) dropped to ~2.3 min.

### 105. ONE-OBJECT-ONE-ACTION on the export — and count DISTINCT animations, not channels (session 25)
Gate 13 proves the pool purge on the GLB itself: no node may be
targeted by more than one DISTINCT animation. The first version of the
gate counted CHANNELS and false-rejected a legal multi-channel clip
(translation+scale inside one animation targets the same node twice) —
the v5_1_b52 run 3 was rejected spuriously until the gate learned to
count distinct animation indices per node. Law: viewers that play all
clips cannot render two weight-1 actions on one bone; assert the
contract on the export with per-node DISTINCT-animation sets, and
never confuse channel counts with animation counts.

### 106. Actions that HOLD a state past their window must key the FULL timeline (session 25)
The rifle carry action's manifest range ended at f157; the review app's
range-gating dropped it during S6 (f337+) and the rifle node fell back
to its BASE TRS — the f1 carry offset, 1.6 m up/back from the hand =
the other half of the "air dance". Blender masked the bug: fcurve
CONSTANT extrapolation holds the last key; glTF + range-gating
consumers do not. Law: any action that holds a state (carry, grip,
seat) gets a terminal key at the scene end so the manifest range covers
every shot; carry counter-animation keys are LINEAR. Verified at four
layers (scene matrix 0.020 m rifle-to-hand, raw-GLB composition 0.019 m,
live viewer eval 0.02 m, VLM zoomed crop).

### 107. Entry scripts OWN their sys.path — Blender --background does not add the --python script's dir (session 25)
The exporter's `import scene_escape_v5` worked when launched from the
scripts/ cwd but died once the daemonized launcher (which chdirs to /)
ran it — on 5.2 Blender no longer implies the script's dir on sys.path
(it worked implicitly on 4.5 via cwd). This cost one of the three fix
iterations on the v5_1_b52 spin. Law: every entry script inserts its
own directory into sys.path (cwd-independent, absolute path from
`__file__`) and imports `sys` itself; same for the truth renderer.

### 108. Numeric ground truth FIRST; VLM second — definition-tight, zoomed, and re-checked (session 25)
The gun-fix verification chain: the first live-viewer eval FALSE-
alarmed (a `/DEF-handR/` regex matched ANOTHER actor's hand — the
gunner's is `DEF-handR_2` post-sanitization), and across the 23-comment
verification EVERY first-pass VLM flag was a low-res misread (muzzle
flash read as a "floating gun", thin low-poly arms as "arms down")
cleared by a definition-tight second pass. Session-26 echo: verify
EVERY user-flagged frame, not just the canonical shot (S6 was fine;
the S1a/S3 carry window was broken). Law: matrix-composition and
track-delta numbers come first; VLM serves as visual confirmation on
ZOOMED crops with prompts that NAME the expected composition and ask
to distinguish adjacent elements; never file a first-pass VLM flag
without the definition-tight recheck.

### 109. A fresh sandbox that "reverted the UI" = stale build cache — nuke .next on boot (session 25)
The sandbox reset preserved the app directory INCLUDING a stale .next
build cache from a pre-session-22 build; the auto-restarted dev server
served cached chunks (GET / compile: 26 ms = cache hit) — old sort, old
default package, no dark mode, no filmstrip (user: "reverted to old
version, no dark mode / filmstrip"). Fix: pkill dev server + `rm -rf
.next` + restart (fresh compile 15.3 s) — dark boots, current package
default. Law: on sandbox boot, kill + nuke + restart the dev server;
treat single-digit-ms compiles as a cache-hit smell. Same healing
pattern for mid-session Turbopack panics (compiler, not app code).

### 110. PHANTOM OFFSETS: anchor captures must be SAME-FRAME snapshots, and every carry gets a sanity radius (session 26)
The rifle floated ~2 m behind the gunner for f1-156 (user comments
S1a/f10 + S3/f155) while ALL 13 export gates stayed green: the aim
placement and the wrapper riding were each individually correct, only
their COMPOSITION was wrong. RCA: `calibrate_rifle` parked the scene at
f10 to read the run direction, then computed `carry_local = wrap.
matrix_world.inverted() @ pos_c` with `pos_c` f1-based — the 1.88 m
sprint delta |wrapper(f10) − wrapper(f1)| was baked into every carry
key. Law (blender_kit/prop_carry.py): (1) LIVE-READ — frame_set +

## What's NOT in this kit

- No GPU support (all CPU rendering, ≤720p for animation)
- No Blender MCP server (direct bpy is more capable for Python agents)
- No rigged character helpers. **Capsule actors are the previz standard** —
  the v2 rigged-humanoid attempt failed (limbs detached, ~10 sessions of
  trap-fixing: skin weights, action slots, NLA stashes, basis-matrix
  collapse, eval deform lies). Use `assets_capsule_actors.py` (capsule +
  FK limbs + `rotation_euler` keyframes). Rigged only when the deliverable
  IS character animation — budget a full session for rig validation.
  UAL (Quaternius CC0) is the vetted hero-swap path (42/46 actions animate,
  drift 0.000m). See `/kb/rigged_characters.md`.
- No geometry nodes helpers (procedural scene generation is future work)
- No Grease Pencil (4.3 rewrote GP v3; API unstable)

## When to ask for clarification

If "make a scene" is ambiguous, ask: type? focus? output? specific objects/colors/style?
Building the wrong scene wastes more time than one batched question round.

## KB entries (linked, niche but valuable)

- `/kb/placement_and_physics.md` — placement_lib + physics_place deep reference (ops, verdicts, report format)
- `/kb/rigged_characters.md` — why capsule actors, UAL hero-swap path, rig debugging
- `/kb/ascii_vision.md` — ASCII vision pack protocol, scorecard, param rules
- `/kb/render_speed.md` — Workbench vs EEVEE vs Cycles benchmarks, AA/cavity tradeoffs
- `/kb/glTF_export.md` — export flags, three.js loader quirks, USD decision
- `/kb/crowd_fields.md` — influence fields, relax PBD, gait phase engine
- `/kb/prop_carry.md` — generalized prop anchoring & clamped carry (phantom offset law)
