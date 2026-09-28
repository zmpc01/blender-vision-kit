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
- `/kb/prop_carry.md` — generalized prop anchoring + clamped carry (law 110 module)
- `/kb/crowd_fields.md` — influence fields + relax PBD + gait phase engine

## VLM verification playbook (learned the hard way — escape-previz project)

The VLM is your ONLY eye, but it is sycophantic and hallucinates on
badly-fed images. These rules cost a full debugging day to learn:
(gotcha 50 update: ASCII vision packs now take geometry/grounding/
count/layout FIRST — the VLM keeps semantics/hue/gist/aesthetics.)

### 16. Validate the image BEFORE trusting the VLM
A nearly-empty, low-contrast, or silhouette render makes the VLM
hallucinate plausible-sounding feedback ("seated figure with backrest"
on an image of a dark blob). Before asking the VLM anything:
- Pixel-classify the subject (color buckets, coverage %, bbox size).
- If subject coverage < ~0.5% of frame or subject/ground contrast is
  low, fix the image (crop closer, add fill light, brighter subject
  materials) BEFORE the VLM pass.
- `scripts/vlm_critique.py` implements structured critique with
  shot-intent context; extend it, don't prompt ad-hoc.

### 17. VLM sycophancy: don't name what you want confirmed
Asking "is the BLUE-shirt man running?" gets "yes" even when the
figure is gray. Describe colors/labels as OUTPUT ("name the shirt
color"), never as input assumptions. Neutral readback prompts first;
intent-based critique second.

### 18. Feed macro crops, not wide lineups
One subject filling the frame beats four subjects at 15% each. When
verifying one actor: `hide_render = True` on the OTHERS (meshes
directly — hide_render is NOT inherited from parent empties!) and aim
a dedicated camera. Wide multi-subject frames get photobombed and the
VLM describes the wrong subject.

### 19. Single frames cannot show motion; probes can
"Is it running?" is unanswerable from one still. Probe bone positions
across N frames (oscillation amplitude) or use the keyframe contact
sheet. A mid-stride freeze-frame looks "fallen" to a VLM — that is
noise, not a bug.

### 20. Backlit subjects vanish (dusk/sunset scenes)
A low warm sun puts camera-facing sides in shadow; world ambient alone
renders figures as dark silhouettes that pixel-classifiers AND VLMs
both miss. Add a neutral fill light (~90W POINT, shadow_soft_size 2)
near the action. Verify with a color-bucket pixel probe.

## Rigged-character gotchas (CesiumMan-style glTF imports)

### 21. Stock assets ship with broken skin weights
CesiumMan.glb's right shin is weighted to LEFT-leg bones (probed via
per-vertex bone-distance). Fix headlessly: drop all vertex groups,
re-weight by proximity to bone segments (2 nearest bones,
inverse-square blend, rigid when 2nd > 0.08 farther). Verify with a
macro leg render BEFORE animating.

### 22. Bind pose is not the standing pose
The walk ACTION supplies the upright pose; quaternions near (-1,0,0,0)
are the identity convention. Poses built from a max-stride frame carry
stride contamination — graft from a NEUTRAL cycle frame instead.

### 23. Quaternion axis conventions differ per composition method
Component-SET on the base quaternion vs PRE-MULTIPLYING a pure axis
rotation give DIFFERENT motions at large angles. Derive the axis map
empirically (the derive_axes.py pattern — file lives in the PREVIZ
repo: perturb one component, read the bone-tail world delta), then verify the FINAL pose with a
side-view render (L-shaped legs read unambiguously in profile).

### 24. matrix_basis.identity() destroys glTF root orientation
Imported rigs carry the Y-up→Z-up -90-degree-X rotation on the ROOT
object's basis. Parenting + resetting basis collapses the skeleton
into the ground plane. Parent with matrix_parent_inverse =
parent.matrix_world.inverted(), then set only
matrix_basis.translation (and keyframe .location, which writes the
translation channel only).

### 25. Blender 4.4+ auto-stashes actions into NLA tracks
Assigning animation_data.action after another action was bound creates
muted NLA "stash" strips. They are usually inert but inspect
nla_tracks when poses misbehave. NLA strips DO apply fcurve CYCLES
modifiers (verified by knee-oscillation probe). NlaStrips.new
signature: (name, start, action) — then set frame_end / repeat.

### 26. Rigid bodies in 4.5: "Animated" flag = rb.kinematic
Keyframe rb.kinematic True→False for the animated→dynamic switch.
A switch with zero inherited velocity leaves the body standing: end
the kinematic keyframes with a 3-frame "launch" motion (backward +
up + tilt) so the sim inherits velocity. Bake with
bpy.ops.ptcache.bake_all(bake=True). PointCache.bake() no longer
exists; particles evaluate at render time without explicit baking.

### 27. evaluated_get().to_mesh() may not reflect armature deform
In background frame_set contexts the evaluated mesh can come back in
the bind pose while the RENDER correctly shows the posed figure.
Grounding/penetration probes on posed skinned meshes should use pose
bone positions (arm.pose.bones[...].head after frame_set +
view_layer.update() x2) or renders — not to_mesh().

## Long-render survival

### 28. Double-fork the render, poll a heartbeat
Every bash toolcall kills its whole descendant tree at exit. Long
chunked renders must be double-forked (reparent to PID 1) — see
scripts/render_daemon.py. Progress lands in a heartbeat JSON; the
agent polls between other work. NEVER run 20-minute renders inline.

### 29. Story timelines: re-derive event times after any phase change
Adding a pre-drive phase shifted every event out of its shot window
(barricade impact landing one shot late, lunge outside its closeup).
Keep one t→frame map, and assert per shot window: impact inside the
climax shot, lunge inside the closeup, dialog inside its scene.

### 30. After ANY git merge: grep for conflict markers before using the kit
A rushed `git add -A && git commit` staged unresolved conflict markers
inside `blender_kit/__init__.py` — every subsequent `blrun.sh` invocation
died with SyntaxError, silently killing 5 of 6 render-daemon chunks while
chunk logs looked "done". Protocol: `grep -rn "<<<<<<<" scripts/` after
every merge, python-AST-parse the touched files, and smoke-test one
blrun invocation BEFORE relaunching long renders. The daemon's chunk
subprocess exit codes must also be checked per chunk (a fast "chunk_done"
is a smell).

## PREVIZ DELIVERABLE POLICY (session 8 — the 3.5h-render lesson)

### 31. Previz deliverables render at VIEWPORT quality. Never EEVEE/Cycles.
In this kit, "previz" means a **raw guidance video for a video-GenAI
(vid2vid) model** — camera + motion + layout + color-coded identity, full
stop. That changes what "quality" means:
- `--quality viewport` = 960×540 Workbench, **FLAT lighting** (pure
  material albedo), no shadows, no cavity, neutral flat-gray world.
- **~0.6 s/frame** vs ~20 s/frame for EEVEE 640×360 (a 3.5 h render
  collapses to ~8 min).
- Baked lighting is **harmful guidance**: a vid2vid model transfers style
  from the source video. Dusk toon grading, shadows, and fog baked into
  a "final-looking" render get picked up as the target look. Pure albedo
  says nothing about lighting, so the GenAI supplies it from the prompt.
- EEVEE/Cycles remain for material/lighting checks and hero stills only
  — never for the sequence deliverable.

### 32. Capsule actors are the previz standard; rigged humans are a minefield
The v2 rigged-humanoid attempt (CC0 glTF rigs, re-skinning, NLA pose
switching) **failed final-render verification**: limbs detached/floating
in hero frames, actors missing from seats, and ~10 sessions of trap-fixing
(skin weights, action slots, NLA stashes, basis-matrix collapse, eval
deform lies). The honest postmortem (FINDINGS.md): part of the visual
failure was even a wrong seat-height constant, but the rig complexity is
what made it unfixable-in-time. Policy:
- Human actors = **capsule bodies + FK limb objects + direct
  rotation_euler keyframes** (`assets_capsule_actors.py`): plain
  primitives, origin-at-pivot limbs, shallow parenting, LINEAR fcurves.
- No armatures, no actions-as-poses, no NLA, no skin weights, no glTF
  imports for actors.
- Rigged characters only when the deliverable IS character animation
  (not previz), and budget a full session for rig validation alone.

### 33. VLM strengths/limits scorecard (measured against builder ground truth)
Session-7 measurement, 5 EEVEE frames vs known scene state:
| Dimension | VLM accuracy | Note |
|---|---|---|
| Object identity (large/near) | ~90% | reliable |
| Colors / counts | ~90% | reliable |
| Spatial placement (coarse) | ~80% | ask for left/center/right + near/far |
| **Dynamics / action reading** | **~20%** | a mid-lunge reads as "leaning on a lamp" |
| Scene semantics (in/outdoor) | ~60% | can misread street canyon as "room" |
| Small/distant identity | ~50% | <2% frame height gets generic labels |
| Hallucinated objects | ~0 | misreads, not inventions — conservative |
| Composition critique | shallow | missed barricade-blocking-lens; raycast caught it |
Practical rules:
1. Never ask "is the action working?" from one frame. Static questions
   only; verify dynamics with programmatic probes (fcurve sampling,
   `zesc_audit.py`-style position probes across frames).
2. Ask for placements, not interpretations. The failure mode is
   plausible-sounding relations ("sitting on top of" vs behind).
3. Distant objects (<2% frame height): audit programmatically.
4. Composition QA needs sightline/raycast checks, not VLM opinion
   (`scene.ray_cast` from camera through frame center).
5. VLM errors are conservative — good for "anything grossly wrong?"
   checks, bad for fine verification.
6. Cost ~1.5k tokens/frame, 5–15 s latency. Native orchestrator vision
   (pixel-grid reads via `ascii_read.py`, superseded by `ascii_vision.py`
   packs — gotcha 37) is ~free — use it first.

### 34. Workbench MATERIAL color reads mat.diffuse_color, not Base Color
Workbench `color_type='MATERIAL'` renders the **viewport display color**
(`mat.diffuse_color`). Node materials authored only via Principled Base
Color render **flat gray**. `make_material()` now sets both (session-8
gotcha — this is why some workbench renders looked colorless).

### 35. Workbench background follows the WORLD (or theme black in headless)
In `--background` mode with no world set, Workbench renders a **black**
background (dark theme). For guidance videos, set a flat neutral world
(the `viewport` preset does this automatically: `FlatGuidance` world,
`use_nodes=False`, color (0.45, 0.45, 0.50)). A black background is
itself harmful guidance ("night scene").

### 36. Sub-agent orchestration: size, verify-alive, and gate their outputs
- Task size: one asset module / one review / one probe per sub-agent;
  each completable in <5 min. Giant briefs ("build scene + animate +
  verify") time out with nothing to show.
- On timeout, the worktree may STILL be updating — check for fresh file
  mtimes/commits before declaring failure and relaunching (avoids
  clobbering finished work).
- Design reviews by fresh-context sub-agents are cheap and catch real
  bugs: the capsule-actor spec review caught seat-local z values that
  would have buried the actors 0.7 m under the jeep floor (a bug the
  rigged path had shipped with!).
- Gate sub-agent code the same as your own: audits + truth-render +
  neutral VLM readback before integration.

## Session 9 — viewport-speed, workbench volumes, per-shot pipeline

### 37. Volume-only materials render as OPAQUE SHELLS in Workbench
A material with no surface BSDF (fog boxes like `Street.Mist`,
Principled Volume only) renders as a **solid gray slab** in the
Workbench engine — volumes are unsupported. From inside the box it
reads invisible (backfaces); from above/outside it **blanks whole
shots** (S1 aerial + S10 crane rendered pure background for frames).
Fix: tag atmosphere objects `ob["kit_atmo"] = True` — the `viewport`
preset hides them (name-pattern `mist|fog|haze|atmo` as fallback).
Atmosphere is unwanted lighting guidance for vid2vid anyway.

### 38. Workbench render_aa dominates render time — AA OFF by default
`scene.display.render_aa` default `'8'` re-rasterizes the scene per
sample: **AA was 92% of wall time**. `'OFF'` is 5–6× faster (535 →
60–90 ms/frame measured; full 720-frame render: **33 s**). Jaggies are
fine for vid2vid guidance. `--aa fxaa` restores cheap smoothing for
human-reviewed stills (2.4× faster than AA 8). Never let PNG
`compression=100` leak in (+1.1–1.9 s/frame). JPEG q85 frames are
~15× smaller and 23–35 ms/frame faster than PNG (`--png` to force).
Cold start (build + RB bake ~2.5 min) now dominates — batch re-renders
into ONE contiguous range; llvmpipe default threads (= all cores) is
optimal; keep Xvfb (EGL/surfaceless crashes in epoxy).

### 39. Per-shot finalize/freeze pipeline (`shot_pipeline.py` — lives in
the PREVIZ repo; the pattern is kit knowledge)
Camera/cinematography work is SHOT-scoped: `status` / `review` /
`freeze` / `rework` / `render --pending` / `distribute` / `encode` /
`storyboard`. Ledger + frozen frames live in the deliverable repo
(git-is-disk). Reviews are append-only; `freeze` requires a passing
review (`--force` + a recorded reason for agent overrides — VLM
composition critique is advisory and flip-flops between rounds).
`review` = stills + ASCII read + subject-size profile + **static-only**
VLM. One contiguous render run per batch; frozen shot dirs are never
overwritten (moving into a frozen dir errors). Encode fails closed:
shot-table contiguity, per-shot frame manifests, mixed-extension
rejection, duration assert.

### 40. Boolean keyframes need f=1 anchors + CONSTANT interpolation
`hide_render` (or any boolean) keyed with default **BEZIER** and no
frame-1 anchor: a zombie whose first toggle is a mid-shot HIDE evaluates
**hidden from frame 1** (the chase pack vanished from S1's
establishing). Always anchor `frame=1` with the default state and set
`kp.interpolation = 'CONSTANT'` on every keyframe point.

### 41. Frame-state tools must count the EXTENSION THEY WROTE
`_validate_outputs`/glob counting only `.png` made every JPEG render
report `frames_done=0` and the daemon mark chunks `chunk_error` —
silent false-failures with all frames on disk. Any frame-globbing code
must accept `frame_*.png` AND `frame_*.jpg` (the viewport preset writes
JPEG).

### 42. Near-field lens-blockers: hide zombies passing < 2.2 m of the camera
Belt/crowd scenery can scroll a zombie right through the active
camera's near plane — the VLM reads "single capsule occupies the entire
half of the frame" and the shot is unusable. `_kf_nearfield_hide()`
scans per-frame (step 2) active-camera distance and keys
`hide_render` at transitions only (crowd+chase+barr; KD falls and
subject rigs are never hidden). Shot-specific keep-bands: a bumper-POV
shot KEEPS its 1.2–2.0 m near-field (that IS the shot).

### 43. A render/verification pipeline needs a provenance chain
Three proven bugs from one code review (16-b): (a) scratch dirs
carried stale-generation frames into "fresh" distributions (the
published mp4 mixed render generations); (b) freeze snapshotted
CURRENT scene hashes, masking review→render drift (the verdict
described different pixels than were frozen); (c) renders counted
stale files. Rules: wipe scratch before launch; daemon clears its
output dir; freeze copies the REVIEW's hashes and refuses on drift;
frame counts only the rendered range; heartbeat `starting` is written
by the parent BEFORE daemonize.
### 50. ASCII vision packs: the visionless first eye (measured)
`scripts/ascii_vision.py` exists and supersedes `ascii_read.py` for pack
generation (ascii_read stays for backward compat). It renders a PNG into
a deterministic TEXT pack a blind agent can read: stats flags,
color-class grid, luma/edge panels, fine connected-component table at
4x internal resolution with fractional coordinates, and 2x2 zoom tiles.
Quick command:
`python3 scripts/ascii_vision.py IMG --cols 96 --components --tiles 2 --no-header`
(--minimal keeps the LEGEND — gotcha 53 makes it mandatory — and only
 drops the header/guide. On material-less gray fixtures the ASCII grid
 is unreadable luma mush: run heat_bake on the scene and read the
 HEAT-mapped render instead — round-G/sA.)
Measured (16-image battery, blind-scored): VLM 0.72 vs ASCII-A3 0.66 on
the generic aggregate — but the aggregate hides the story. ASCII WINS
dark/monochrome renders (+0.32; the VLM scored 0.29 there), tiny <2%
objects (+0.12), near-empty traps, street-layout montages, gradients
(+0.28), and the real wide render (+0.21). VLM keeps semantics, crowd
gist, hue nuance, and many-small-object grids.
R4 realism (the operationally decisive test): a visionless pack-reader
doing the shot-QA gate found the planted floating actor at its exact
truth coordinates (0.748, 0.485), cited component ids/bbox, DECLARED
its occlusion blindness — and fabricated nothing. The VLM under the
same brief hallucinated floats on grounded actors, diagnosed a SUNK
actor as floating (its proposed fix sinks it further), and cited "the
component table's X-coordinate" — which does not exist in a VLM prompt.
Fabricated evidence is worse than blindness; pack-reads cannot
fabricate.
Doctrine: pack-read FIRST for geometry/grounding/count/layout; VLM only
for semantics/hue/gist/aesthetics; disagreement between the two =
automatic programmatic probe (their failure modes are opposite:
false-accept vs false-reject). NEVER act on bbox-overlap hints
(floating/intersecting) without scene-schema probes — including the
pack's own hints (projection ambiguity is real).
Param rules: palette must match the domain (kit scene renders → scene
palette; anything else → web16: +0.19 on hue tests); dark renders →
`--gamma 1.8 --autocontrast` (0.38→0.60) or A1 luma-dither; FINE
components at 4x are what make <2% objects countable (invisible in the
grids, present in the table); crowd counts from components are LOWER
bounds (same-class touching figures merge).
R5 additions: `--auto` codifies those param rules (calibrated, auditable
`auto=rN` echo, explicit flags always win); every component row now
carries `rgb= lum= fill= edge=` readback (full-frame edge contact — a
direct answer to edge-cut questions; rgb validated 112/112 against truth);
`--crop`/tile tables are ALL full-frame coordinates (never double-transform);
`--minimal` strips header/guide/legend for blind handoffs. Prefer
`--auto --cols 96 --components --tiles 2` as the default invocation.
Text-only QA without a VLM call: `vlm_critique.py --with-pack` runs the
pack arm (chat) first and the VLM second, in one JSON; `--dry-run`
previews both prompts with zero API. HD probe: pack faithfulness is
resolution-invariant (1280x720 == 640x360 accuracy).
Full scorecard + protocol: `experiments/ascii_vision/docs/RESULTS.md`,
`experiments/ascii_vision/docs/PROTOCOL.md`.
## Session 11 — white-world color discipline, 45s recut, UAL validation

### 51. Color discipline = the attention map (user policy, MEASURED)
For vid2vid-guidance previz: environment WHITE/grey (value ladder only),
ONE color per subject body, ~3 chromatic classes total. The v2.2 cut
measured 96.8% single-class frames (luma stdev 0.05) — an unreadable
wash for both the agent and the vid2vid model. After the discipline:
every shot 0.07-0.16 stdev, subjects at per-class floors. Full policy +
rules: the COLOR DISCIPLINE section above. The multi-color character
bug: capsule PANTS khaki (0.45,0.40,0.30) vs asphalt/jeep tones — legs
vanished (ΔRGB 0.05 from streetscape).

### 52. STUDIO beats FLAT on a white world (shade experiment, measured)
Workbench STUDIO on white surfaces = greyscale normal shading ("greyscale
if you need shade") with subject chroma IDENTICAL to FLAT (25.9% both,
measured). FLAT gives zero shape cues (buildings = flat rectangles; the
crane shot read 98% one class with the jeep at 0.1%). `--shade flat`
remains for pure-albedo needs. Viewport preset now defaults STUDIO,
shadows+cavity OFF.

### 53. Restoring "the praised version" is a camera-ANIMATION problem, not a camera-table problem
The v2.2 framing regression came from TWO layers: the static table AND
the derived animation (crane windows, dolly loops, aim tracks hardcoded
to old shot times). Restoring the table but not the loops = cranes
firing in the wrong shots (passes every content gate — only a
camera-key-coverage audit catches it: every moving cam needs location
keys INSIDE its own shot window). Pin the restore to a specific COMMIT
(dc1e3d1) — the repo holds three materially different tables.

### 54. A longer runway breaks a praised establishing shot (geometry, not taste)
v2.0's S1 worked because the 20 m runway put the trio AT the aim point
mid-shot. The v3 27.5 m runway spread trio/jeep/horde 87 m apart — no
28mm frame holds them (computed + two render rounds verified). Fix:
higher start + WIDER lens (24mm) + an aim PAN converging on the runners.
Lesson: when a timing constant changes, re-derive every camera that
frames the affected span — FOV math is cheap (pencil it BEFORE the
7-minute re-render).

### 55. Mill/idle animations can overwrite frame-1 ground keys
A bob phase of ~0 puts the first mill key AT frame 1, silently
overwriting the pinned ground-contact key (a zombie evaluated +0.04 m
at f1 and failed the ground audit). The bug was latent for sessions —
new crowd-zone RNG draws exposed it. Fix: phase = uniform(0.5, half),
never (0, half). Audit derivations should use the zone table
(sum of n), not hardcoded counts.

### 56. Quaternius UAL is a VETTED hero-actor upgrade path
Vendored at assets/vendor/ual/ (CC0 mirror, access verified). Gauntlet
PASS (42/46 actions animate, in-place drift 0.000 m, recolor works —
character-region R share 25.2%, no NLA tracks, scale 1.651 m → 1.05
rescale). A/B vs capsules: VLM reads UAL as "running, leaning forward"
vs capsule "walking"; UAL anatomy fully distinguishable. Action map:
Sprint_Loop / Sitting_Enter+Driving_Loop / Pistol_Aim_Neutral+Shoot /
Punch_Cross / Hit_Chest+Death01. NOT yet integrated (hero swap = its
own session; crowd stays capsule-instanced). One import artifact: a
stray Icosphere at origin — delete on use.

### 57. Coplanar face pairs are the z-fight class (gate: coplanarity_audit)
"flickering everywhere" decomposed: (a) TRUE z-fights = same-plane,
same-direction overlapping faces (bumper/hull flush 31 cm2, bed-rear
1700 cm2, crash-stack 4.4 m2, grid crossings); (b) AA-off temporal
aliasing on thin lines. The coplanarity_audit gate catches (a) at
build time; FXAA-on-delivery treats (b). False-positive classes to
NOT "fix": fan-tiling triangles (share vertices), contact faces
(opposite normals), down/down pairs near ground (invisible from
above), kit_atmo objects (hidden by the preset).

### 58. The framing gate must project, the auto-fit must repair (user: "what about next time")
Head crops become BUILD FAILURES via framing_audit (NDC margins from
world_to_camera_view -- 0..1 REGION coords, normalize x_n=2x-1 or the
feet/left checks silently no-op). Repair ladder: lens widening ->
AIM ASSIST (lens cannot recover an aim that pitches away from the
subject -- S6b aimed 28 deg below a standing figure). Camera
evaluated-data gotcha: the COW copy can serve STALE lens values --
project with the RAW camera after copying in the evaluated matrix.
Action beats need traverse subjects (>=60% in-frame) + closeups need
feet_crop (heads ALWAYS strict).

### 59. Crowd realism = per-agent simulation, not shared formulas
"Runs exactly at hero speed" + "wood sticks" fixed by crowd_agents.py (lives in the PREVIZ repo; the
laws are kit knowledge): unique speed/reaction/aggression/gait per agent, states
IDLE->ALERT->PURSUE->LUNGE->REACH(pound)->FLEE(scatter)->FALLBEHIND
->GIVEUP. Shape-key gait on per-instance mesh COPIES (arms pump +
lean + lunge + raise). The boarding-window target must be the PARKED
JEEP after t5.5 -- linear extrapolation of the run formula drags
chasers THROUGH it. Speed-variance gate reads RECONSTRUCTED
velocities from records (a.state is the END state, not at-t state).

### 60. FX in Workbench reads by SIZE+STROBE, not brightness
Studio shading caps white near 0.8 -- a flash cannot out-bright the
environment; it reads by size (x2 burst scale: 4k->14k->16k bright
px) + 1-frame strobe + smoke. Emission/point-lights are INVISIBLE in
workbench (the v1 splash died exactly there). Dim the env ladder so
FX is uniquely bright.

### 61. Belt-treadmill artifacts look like parenting bugs
Objects belt-keyframed THROUGH the static jeep read as "glued boxes".
Fix class: loose individual objects + the KD-recipe RB handoff
(world-follow keys -> 3-5f launch velocity -> kinematic->False at
impact) + a collider PROXY (never the animated parent -- a body
handing off INSIDE the collider detonates; window-scope rb.enabled).

### 62. A GitHub Release upload is not a publish (draft = invisible)
All 7 v3.3 assets uploaded, tag pushed, commits pushed, worklog said
"release v3.3 live" — but the release object was still DRAFT, so the
public releases page showed only v3.2 for hours. Owner-side it hides
in the bottom "Drafts" section, so even a logged-in spot-check can
miss it. Fix class: after upload, ALWAYS `PATCH /releases/<id>`
`{"draft": false}` and verify via API (`"draft": false` + asset
count) BEFORE writing "live" anywhere. Related traps: a private repo
404s anonymous curl (404 ≠ absent — authenticate first); the GitLab
mirror does not get tags with `git push gitlab main` — needs
`git push gitlab --tags` (WAF 403 → retry).

### 63. FX scale-ON without OFF = the frozen rider (treadmill law)
In a treadmill world (belt streams, subject world-static), any object
that is world-static AND visible PACES THE SUBJECT on screen. The v3.3
smash FX had scale 0->1 at event onset with no OFF and location keys
ending f775 -- the debris "rode the jeep" through 4 shots. Fix class:
FX taxonomy -- TRANSIENT fx must scale-OFF within 40f of event end;
WORLD-LITTER must belt-compose at rest (follow-keys at the belt's own
6-frame cadence + linear interpolation = exact streaming). Encoded in
motion_frame_audit (fail-closed): undeclared world-static + visible =
violation; anim-end freeze outside the belt tree = violation.

### 64. A skip list in a gate is a hole with a signature
occlusion_gate v1 hard-skipped ("concept") shots S4b/S7/S8b/S9b --
S4b delivered with the camera INSIDE the rear wheel for 79% of the
shot. v1 also counted only Zed.* as occluders, so an abandoned car
crossing the lens at 0.2m could never register. Fix class: gates check
EVERY shot; concept exemptions belong in THRESHOLD tables (documented,
per-arm), never in coverage. And: ray-based gates MUST dep.update()
per frame -- view_layer.update() alone leaves constraint-driven
cameras with STALE matrices (phantom lens hits).

### 65. Vertex-baked origins detonate transforms (the 218m COM class)
Meshes whose geometry is baked far from the object origin make every
transform operate 218m away: RB COM swings huge arcs, rotation keys
swing the mesh around the world origin, location reads lie. Fix class:
ORIGIN-CENTERED emission (build geometry around local (0,0,0), set
loc=) for anything that will ever be animated or simulated. The
loose_chunks ctx key must match the builder's return shape -- an
silently-empty list made the v3.3 chunk gates VACUOUS ("CLEAN" on a
check that checked nothing).

### 66. The action-slot law (Blender 4.4+): `ad.action = X` does not rebind
After a legacy-slot action has been assigned, later `ad.action = other`
assignments are SILENTLY IGNORED at the binding level — the pose keeps
evaluating the old action while every read looks fine (v4 session-17:
poses froze mid-bake; the fidelity gate's live pass read stale values
and would have passed vacuously). EVERY assignment must pin the slot:
`ad.action = act; ad.action_slot = act.slots[0]`. Actions created via
`bpy.data.actions.new()` have 0 slots until first assignment (the
auto legacy slot appears then) — build actions + fcurves FIRST, assign
+ pin LAST. Symptom signature: "frozen pose" + identical readings
across frames + a vacuous-looking gate pass.

### 67. `img.pixels` is BOTTOM-LEFT origin (OpenGL convention)
Pixel gates indexing `pixels[(y*W + x)*4]` with top-down image rows
sample a VERTICALLY FLIPPED location — dark discs read as bright road
(v4 contact_audit: inner 0.612 at a point that measured 0.266). Always
`((H-1-y)*W + x)*4`. PIL/numpy reads are top-down — the mismatch only
appears when mixing Blender pixel arrays with projected coordinates.

### 68. `keyframe_points.add(n)` returns None
The collection adds in place; `kps = fc.keyframe_points.add(n)` gives
kps = None → `kps[i]` explodes with "'NoneType' object is not
subscriptable". Correct: `fc.keyframe_points.add(n); kps =
fc.keyframe_points`. Bulk-filling after add + `fc.update()` is the
fast write path (400k keys in seconds).

### 69. The UAL-build exit deadlock: completion = outputs, not process exit
A Blender process can hang in futex_wait AFTER completing all work
(metadata.json written, all frames saved) — capsule builds never hung,
the rigged build did. Any daemon that `subprocess.call`s the scene
script must use a completion-based watchdog: poll for the expected
frame count + metadata.json on disk, then kill the process and treat
it as success. Budget-capped kill for the real-failure case.

### 70. matrix_parent_inverse composition: world = parent @ MPI @ basis
Probe-verified in 4.5.13 (mpi_semantics_probe.py): the transform
composes with MPI DIRECTLY, not inverted. "Keep-transform" parenting
sets MPI = parent^-1; child MPI = FLIP @ SCALE yields capsule-parity
facing semantics. Stale matrix_world reads (right after setting
.location without an update) poison MPI capture — capture after a
depsgraph-flushing op.

### 71. Raycast occlusion filters need atmosphere + self-quad exemptions
`scene.ray_cast` hits render-hidden atmosphere boxes (Street.Mist
blocks EVERY ray) and the subject's own ground disc before its center
(steep angles). Occlusion-aware pixel gates must exempt
NON_OCCLUDERS-prefix objects and the disc's own Contact. prefix.

### 72. 100MB git tree limit: big blends ship as release assets only
A baked-action blend hits 167-251MB (GitHub rejects >100MB tree
files; release assets allow 2GB). Law: git-is-the-disk — the blend is
byte-reproducible from HEAD via the deterministic pack script
(rebuild determinism 0.00e+00), so the tree carries the scripts + the
small glb; the blend rides the release. Slim what you can first
(strip unused source actions: 602 -> 417, still over — the baked
actions ARE the deliverable).

### 73. mathutils `Vector.to_4d()` appends w=1 (POINT semantics), not w=0
Building a 4x4 basis via rows of `to_4d()` vectors produces a last row
of (1,1,1,2) — the matrix is projective garbage and every
conjugation/product explodes (poses 49m off). Construct affine matrices
explicitly: basis columns w=0, origin column w=1. (session-18 v5,
debug_rifle6.)

### 74. Pose-bone composition law + the writer formula (assignment does not hold)
`pb.matrix = parent_pose @ parent_rest^-1 @ bone_rest @ matrix_basis`
(probe_pbmatrix [C]). ASSIGNED `pb.matrix` does NOT survive
re-evaluation: translations land but rotations explode with compounding
scale (hold delta 7-25 per chain level). Use the writer:
`basis = (parent_pose @ parent_rest^-1 @ bone_rest)^-1 @ M`, with
`view_layer.update()` x2 BETWEEN chain levels — a stale parent pose
explodes the children. INDEPENDENTLY CONVERGED: the parallel PSD-export
track's Phase-0 finding (bake `pose_bone.matrix_basis`, bone-local
space is portable Blender->glTF) is the same law from the other side.

### 75. `bpy.ops.object.join` leaves the ACTIVE part's object scale on the result
Joined primitives carry the active part's object-scale; the vertex data
is authored for it, so any later `matrix_basis` reset (e.g. a
parenting calibration) renders the mesh at 40+ m. Law:
`transform_apply(location=False, rotation=True, scale=True)` right
after join. (session-18 v5 rifle mesh.)

### 76. Bone-parent calibration: exact MPI fixed point, LIVE reads only
For `parent_type='BONE'`, the effective parent transform is a Blender
internal (rest-roll contributes ~90 deg world rotation vs the naive
`arm.matrix_world @ pb.matrix`). With basis=I: `W_i = P @ MPI_i`, so
`MPI_{i+1} = MPI_i @ W_i^-1 @ M_target` converges in ONE step IF `W_i`
reads are live — refresh via `scene.frame_set()` + double update and
gate on the FULL matrix (translation-only gates passed while the rifle
pointed 90 deg off). (session-18 v5.)

### 77. VLM audits hallucinate off BLACK frames — check luma first
A test scene with no lights rendered as near-black (mean luma 0.1); the
VLM produced detailed, partially-critical audits from the prompt alone.
Law: verify image luma/mean before trusting any visual audit; use
zoomed crops for sub-100px features (full-frame queries under-report
borderline FX). (session-18 v5.)

### 78. Sync-copy clones carry origin=local-sync
`git clone /home/sync/<repo>` sets origin to the LOCAL stale copy — a
fetch "succeeds" while showing 0-behind. Re-point origin to GitHub
(token from the sync remote) before any update check. (session-18.)

### 79. Animated-property live overrides are clobbered by the fcurve
Setting an ANIMATED property (e.g. `ob.rotation_euler = ...`) holds only
until the next depsgraph evaluation — the fcurve re-asserts. A parametric
probe that overrides such a property silently measures the SAME keyed
value for every candidate. Detach the object action (`ad.action = None`;
setting `action_slot` with no action raises — action=None auto-clears)
before live-basis probing. (session-19, previz carry sweep.)

### 80. Static carry angles cannot clear converging-sprint geometry
When two actors' runs converge (measured ~0.2 m between the carrier's
swinging hand line and the adjacent torso, same z-band), NO static
rotation of a ~1 m prop clears the swept volume — a 16-candidate
(yaw, pitch) grid proved it. The physical model is a TORSO-STABLE
CLAMPED carry: per-frame basis keys `basis(f) = W0(f)^-1 @ desired(f)`
where `W0(f)` = the prop's parent-bone world read with basis == I
(ALL W0 reads must happen BEFORE any key exists — keys change later
reads), `desired(f) = wrapper(f) @ CARRY_LOCAL` (the torso frame has
no limb swing). Blend desired toward W0(f) over the last ~8 frames so
basis reaches identity exactly at the action blend end — the hand
CATCHES the prop. (session-19, previz rifle carry.)

### 81. `join` leaves the object ORIGIN at the ACTIVE part's location
Beyond the known active-part SCALE retention: after `bpy.ops.object.join`
the result's origin sits at the active part's center (e.g. Stock.Butt),
so local coordinates are NOT authored part-space — any parenting that
places the ORIGIN at a target (bone-parent calibration) seats the wrong
end. `transform_apply(location=True, rotation=True, scale=True)` bakes
origin -> world 0, making local == authored part-space. Symptom class:
a long prop whose far end lands ~its own length off target. (session-19,
previz rifle: butt seated at the hand, muzzle anchor 20 cm inside the
barrel.)

### 82. Shot-aware FX scale: closeup cameras in the line of fire
A closeup camera placed ~1 m from an FX anchor (toward-lens framing —
e.g. looking back at a gunner from where he aims) turns wide-shot FX
sizes into frame-walls: a 0.45 m muzzle-flash quad at ~0.9 m covered
72.4% pure-white, hiding the subject entirely ("the gunner vanished").
Fix: per-burst FX scale keyed by camera distance (compact ~0.15 m pop),
plus a DARK backdrop icosphere behind the flash (studio-lit 0.22
material reads ~140 luma — a grey halo giving white-on-bright-sky
contrast; offset it back along the FX axis or it ENCLOSES and hides the
bright element). (session-19, previz S6b.)

### 83. glTF `export_cameras` defaults False — hand-rolled exports ship blind GLBs
The glTF operator's `export_cameras` is False by default; any export
path that doesn't go through `blender_kit.export_gltf` (which sets it)
produces a GLB the web viewer cannot frame — the v3.4 outputs GLB had
0 cameras while every earlier package had them (a one-off hand-rolled
command dropped the flag). Always export through the kit helper or set
the flag; `scripts/export_previz_package.py` fail-closes on missing
shot cameras after export. (session-20, review-app package export.)

### 84. glTF ACTIONS mode does NOT bake object constraints (TRACK_TO)
With `export_animation_mode='ACTIONS'` node rotations come from the
keyed/basis values — a camera aimed with a TRACK_TO constraint exports
pointing wherever its raw euler says (identity: straight down). The
constraint TARGETS export fine as their own nodes (animated where the
scene animates them), so the viewer can rebuild the aim exactly:
camera node -> position/fov, `Aim.<cam>` node -> lookAt target. Use
SCENE bake mode only if you need fully-baked transforms (heavier).
(session-20, previz-review shot cameras.)

### 85. THREE GLTFLoader strips `.` from node names
`PropertyBinding.sanitizeNodeName` removes `.[]:/ ` (reserved for
track-binding syntax): Blender's `Aim.CAM_S6b` loads as `AimCAM_S6b`.
Any node-lookup by name in the viewer must compare dot-free (cameras
like `CAM_S6b` are safe; `Aim.*`, `FX.*`, `CA.*` are not).
(session-20, previz-review aim reconstruction.)

### 86. `mixer.setTime` + LoopOnce+clamp BREAKS on re-scrub (three.js)
Once a LoopOnce action with clampWhenFinished has finished, subsequent
`mixer.setTime(t)` calls evaluate it at time 0 — it falls back to the
FIRST key even for t inside the key range (probe_mixer2.mjs). The
scrub-safe pattern for timeline-absolute glTF clips: pre-pad every
track with a `(0, firstKeyValue)` key, stretch `clip.duration` to the
full timeline, use LoopRepeat — interpolants hold the last key past
the final keyframe, so playback and arbitrary scrubbing are both exact.
(session-20, previz-review playback.)

### 87. Blender glTF action keys are TIMELINE-ABSOLUTE at t = frame/fps
Multi-action GLBs key every clip in absolute scene time (`f8 -> 0.333s`
at 24 fps, NOT (f-1)/fps): playing ALL clips on one mixer at time t
reproduces the scene state at frame t*fps exactly — no per-clip
offsets needed. Frame->time conversion in any viewer must be
`t = frame / fps`. (session-20, previz-review playback.)

### 88. export_usd.py had an INVERTED animation guard — "animated" USD shipped static
`if hasattr(mod, "animate") and not args.export_animation:` meant
animate() NEVER ran when --export-animation was passed — the export
sampled a scene with zero keyframes (31MB of frame-1 statics; the
"fix" grew it to 46.8MB with 1080-sample tracks). Guard conditions
on action flags must be tested BOTH ways; a flag that silently
no-ops is worse than a crash. (session-21, USD spike.)

### 89. three.js USDZLoader CRASHES on Blender USDC crates; ASCII .usda parses
Current three.js USDLoader `applyTransform` gets `undefined` for
time-sampled xformOps (`_buildTransformAnimations` exists but the
static path was never taught about timeSamples) — a fresh loader
regression. The same scene as ASCII `.usda` parses fine (387 meshes,
21 cameras, 45s / 501-track TransformAnimation). USDZ archives crate
to USDC, so USDZ->web is blocked until the loader fix lands. Web USD
consumption: .usda only. (session-21, USD-vs-JSON+GLB decision.)

### 90. three.js USDLoader does NOT expose customData — story payloads are invisible
Even where a .usda parses and plays, `previz:entity` customData (the
USD carrier's whole story payload) is dropped by the loader — no API
surface to read it. USD alone can therefore never drive the review
app's shot/story layer today; JSON must stay the story source of
truth, with USD as a parity-gated sidecar for USD-native consumers.
(session-21, USD-vs-JSON+GLB decision.)

### 91. USD customData REJECTS list-of-dicts — and ONE bad key kills the WHOLE payload
`VtDictionary` inside a vector is "not a valid scene description
datatype": a single list-of-dicts story key (chase_falls as a list)
made `root_prim.SetCustomDataByKey("previz:entity", payload)` raise,
so the stage lost ALL story customData (per-object payloads
survived). Emulate lists-of-dicts as dict-of-dicts keyed by index
(same law as _collect_knockdowns). Fail-closed parity gates are what
caught this — the export was rejected, not silently degraded.
(session-21, export_previz_package v2.)

### 92. glTF bakes volume-only materials to OPAQUE SHELLS — exclude + declare them (schema 2.1)
A Principled Volume box (Street.Mist, density 0.01) exports to glTF
as a double-sided opaque mesh with no base color: in three.js it is a
gray slab. Cameras INSIDE the box see through (backface luck), but
any crane/aerial camera above it stares at its top face — the whole
shot renders flat gray (user-reported: "s12a is fully blocked by a
gray screen"). glTF has NO volume materials. Law:
blender_kit.atmo_objects() (kit_atmo tag OR mist|fog|haze|atmo name
OR volume-linked-no-surface material) -> EXCLUDE from the GLB
(export_gltf exclude_objects) + DECLARE in previz.json
(atmosphere: bounds/density/color) for web approximation. Gate 8
fail-closes this (session-22; the workbench preset had the same law
since session-9 — the GLB path just never applied it).

### 93. A linked Nishita sky makes Background.Color defaults LIES — detect TEX_SKY
scene_escape_v3_* uses add_sky_world (Nishita dusk). The world
collector read bg.inputs["Color"].default_value (flat 0.8 gray) —
but the sky TEXTURE LINK overrides it, so consumers rendered a
~2x-wrong flat sky (a co-conspirator of the web overexposure).
Law: when a TEX_SKY node drives Background.Color, export
world.sky {sun_elevation_deg, sun_rotation_deg, air/dust_density,
strength} and mark background_color as overridden (session-22).

### 94. WORKBENCH is DISPLAY-REFERRED — flat parity needs sRGB constants, not linear
The stills pipeline (viewport quality) renders the FlatGuidance
world color (0.50,0.50,0.52) as sRGB ~127, NOT linear 0.5 (=187
after the sRGB transfer). three.js flat mode must set the background
with setRGB(..., SRGBColorSpace), swap PBR standards for Lambert
(albedo-exact), and approximate the view-locked studio light
(hemi ~0.54 + camera-relative key ~0.74). Tuned via the
parity harness: MAD 5-9 vs the Blender stills (session-22).

### 95. three.js physical lighting divides diffuse by pi; glTF punctuals are 683x Blender
Two unit-law traps when matching Blender renders in three.js:
(a) three.js PHYSICAL lights multiply albedo by intensity/pi —
Blender doesn't — so a Blender sky-lit surface (radiance = albedo)
needs a hemispheric ambient at intensity ~pi (x1.12 tuned).
(b) The glTF exporter converts Blender light WATTS to photometric
candela (x683/4pi: 90W -> 4892cd) while Blender itself renders
radiometrically — a physical glTF viewer burns 683x brighter than
Blender's own render. Viewer-side fix: l.intensity /= 683 (keeps
the GLB standards-compliant). Also: Blender base colors are LINEAR
(asphalt 0.62 -> display 209) — do parity math in linear.
(session-22, lit-mode parity: MAD 8.5-27 vs Eevee truth frames.)

### 96. CSS aspect-ratio + width:100% + max-height does NOT letterbox
A div with aspect-ratio 16/9, width 100% and max-height clamps the
HEIGHT but keeps the width — the ratio silently breaks (measured
2.94:1). For camera-exact letterboxing compute the fitted box in JS
(ResizeObserver: w = mw, h = mw/ar, clamp by mh) and size the canvas
to that; the render camera then ALWAYS uses the package render
aspect (session-22, framing exactness).

### 26. Blender version: 4.5 or 5.2 LTS — the kit shields you (session 6)
The kit runs on both **Blender 4.5 LTS** and **5.2 LTS** unchanged. You don't
need to know which version is installed — the kit's compat shim handles
all the differences:
- Write `--engine BLENDER_EEVEE_NEXT` or `--engine BLENDER_EEVEE` (both work)
- Write `action.fcurves` in your scene scripts (the kit's `iter_fcurves()` helper handles 5.x)
- Write `mat.use_nodes = True` (the kit's `ensure_use_nodes()` handles 5.x)
- The sky world (`add_sky_world()`) auto-selects NISHITA (4.x) or MULTIPLE_SCATTERING (5.x)

**Default install**: 5.2 LTS (supported until July 2028). If your container
has 4.5 LTS, the kit still works — no changes needed.

**What changed in 5.x** (you don't need to memorize this — the kit handles it):
- `BLENDER_EEVEE_NEXT` → `BLENDER_EEVEE` (engine id renamed back)
- `action.fcurves` → `action.layers[0].strips[0].channelbag(slot).fcurves`
- `mat.use_nodes = True` → no-op (auto-created, deprecated)
- `NISHITA` sky type removed → `MULTIPLE_SCATTERING`
- `gpu.init()` new in 5.2 — boots EGL headless, but in no-`/dev/dri`
  containers (llvmpipe) it **crashes** (EGL_BAD_PARAMETER → segfault,
  validated session 16). Xvfb remains required there; on real-GPU
  machines gpu.init may drop Xvfb. The kit's `supports_headless_gpu()`
  is being hardened to gate on `/dev/dri` — don't trust API presence.

**When writing scene scripts**: just use the kit's helpers
(`make_material`, `add_sky_world`, `configure_render`, `iter_fcurves`).
Don't reach for raw `action.fcurves` or `mat.use_nodes = True` — the helpers
are version-agnostic.


### 27. .blend files are forward-only across major versions (session 7)
Blender 5.2 saves .blend files with format version `1701` (Zstd compression
by default — 5× smaller than 4.x). Blender 4.2.9 **cannot open** 5.2 .blend
files (format version mismatch). 5.2 **can open** 4.2 .blend files
(forward-only compat by design).

**For cross-version interchange**: use glTF (`.glb`) or USD — both are
version-agnostic. The kit's `export_gltf.py` produces byte-identical output
on 4.2.9 and 5.2.2 (verified: 30516 bytes on both).

**For archival**: save .blend with the consumer's Blender version, or keep
both versions installed if you need to open legacy files.

### 28. EEVEE memory on 5.2 — 1.6GB for 273-object scenes (session 7)
EEVEE on 5.2 peaks at **1.6GB RSS** for the 273-object interior room scene
(40% of 4GB total). Cycles peaks at 355MB for the same scene. Workbench
peaks at 479MB.

**Recommendation**:
- **Workbench** for previz iteration (fast, low RAM, ~480MB for 273 objects)
- **Cycles** for final stills (stable ~355MB regardless of object count)
- **EEVEE** only for ≤50-object scenes or when you have >8GB RAM
- Avoid EEVEE for 100+ object scenes on 4GB containers — OOM risk

### 29. set_material_color now works in Workbench (session 7 fix)
`apply_patch.py`'s `set_material_color` op previously only set the Principled
BSDF `Base Color` input — but Workbench engine reads `mat.diffuse_color`,
not the BSDF. The op now sets BOTH, so color changes are visible in
Workbench renders (verified: VLM confirms green cube after patch on 5.2.2).

### 97. glTF exports IGNORE ray-visibility — render-hidden helpers leak into review GLBs
visible_camera=False / hide_render are the scene's own "never in a
render" declaration (physics hulls, particle emitters, proxy planes),
but the glTF exporter ships data, not render state. Without an
explicit exclusion the review GLB shows colliders drifting beside the
subject ("i don't know what is this but it SHOULD NOT be visible"),
emitter boxes riding the camera-facing action, and coplanar physics
planes z-fighting the visible ground at range (user-reported
"flickering on BOTH sides"). Law: blender_kit.render_hidden_objects()
+ export_gltf always excludes them; export gate 9 fail-closes the
leak (session-23).

### 98. Settled rigid bodies come to rest in WORLD space — on a treadmill stage they RIDE the subject forever
Any staging where the WORLD streams under a fixed subject (treadmill
belt, conveyor, scrolling room) inverts the rest contract: a
world-static corpse keeps a constant gap to the subject while the
ground slides under it = "attached to the jeep" (user: 5 anchored
"following in exact same speed" notes). Bullet friction drag on a
kinematic ground is NOT reliable coupling, and point-cache motion is
not portable to glTF ACTIONS mode anyway. Law: after the physics
bake, ADOPT every settled body to the streaming frame — re-author
its sampled trajectory as belt-local fcurves (local = world +
stream(t)), parent it to the belt root with identity MPI (belt at
origin at t0), and drop the rigid body. Deterministic, export-port,
render-port (session-23; measured: KD3 frozen at world y -0.6 from
f361 to f1080, Chase03 -8.0, Chase06 -12.2).

### 99. Keyframe noise systems must sample the ANIMATED base, never the static spec
A shake/handheld pass keyed on top of the spec's loc0 constant
OVERWRITES the crane/dolly keys every step (last writer wins) — the
camera freezes at the start position for the whole shot and teleports
on the final hold key (user: "i recall there's some camera movement
for this shot but here it is fixed?"). Law: read the base from the
object's OWN fcurves (fc.evaluate(frame)) at each step before adding
noise, so noise rides the animation instead of replacing it; export
gate 11 asserts moving-spec cameras show a real translation span
(session-23).

### 100. Review exports MUST gate against SCENE MODULE VERSION DRIFT
The single most expensive class of review-app feedback is invisible:
the app serving a package exported from an OLD scene module while the
repo is versions ahead (app: "v3_4" exported from scene_escape_v3_3
while the repo was at v5 — every UAL/rifle/contact fix missing,
capsule heroes, frozen cranes, stale stills; the reviewer's "are you
even using the same version????" was 100% correct). Law:
export_previz_package FAILS when --scene is not the newest
scene_* module in scripts/ unless --allow-stale is passed with a
reason. Characters registry carries a "rig" field; gate 10 asserts
skins exist when the scene has armatures (the silent
rigged->capsule degradation class).

### 101. Validate the EXPORT, not the scene — rider/behavior gates read the GLB
Sim-side audits (speed variance, no-riders, ground contact) verify
the SIMULATION, but the review consumer sees the EXPORTED glTF where
bake paths, unit conversions, name sanitization and action binding
can each silently diverge (user: "not just visually you can likely
programmatically detect ... check the EXPORT version"). Law: parse
the GLB itself (glTF has no node.parent — the hierarchy lives in
children[]!) and run behavior gates on exported samplers: constant
world-gap riders near the streaming frame, camera motion spans,
skins presence, helper leaks (session-23 gates 9-12;
scripts/glb_rider_scan.py is the standalone probe).

### 102. glTF node names get SANITIZED by consumers — anchor identity must map raw<->loaded
three.js GLTFLoader renames animated nodes (PropertyBinding rules)
and raycasts report geometry/mesh names, so DB anchors recorded from
a loaded scene can be mesh names with mangled separators
("ZedVarBMesh_8") that resolve to nothing later. Law: parse the glTF
JSON chunk from the same ArrayBuffer BEFORE GLTFLoader, build
alias->raw maps for every node name AND the mesh names its nodes use
(all separator variants), and resolve every pick through it. Store
RAW exporter names as anchors (session-23).

### 103. UAL/rig exports peak memory across the bake loop — purge per actor, drop the RB world after adoption
A 4-rig UAL build + 4x imported action libraries + per-actor pool
copies + a 1080-frame point cache exceeds small-container cgroup
limits mid-bake (OOM-killed three times at 2.2-2.5GB). Law:
orphans_purge + gc.collect() after EACH actor's bake (not only at
the end), remove the rigidbody world once every body is fcurve-
adopted, and keep the heavy render/export phases in separate
processes from the build when the budget is tight (session-23).

### 70. 5.x EEVEE renders brighter than 4.5 on identical scenes (session 16)
A/B-verified (minimal sun+sky scene): 5.2.2 mean luma ~+4-12% vs 4.5.13,
compounding on high-key scenes (white materials + sun + sky world) until
they clip to full white — subject v1's bedroom went 97% clipped white on
5.2 while readable on 4.5. viewport_capture now warns with the clipped %
+ the fix (set_exposure ~-0.5 EV on 5.x, or -20% light energy). When you
must match a 4.5-authored look on 5.x, re-balance exposure deliberately.

### 71. Sign-test INSIDE claims are parity-verified (session 16, v2)
The cheap sign test (dot of p->nearest vs face normal) can misclassify
closed CONVEX meshes near rim/adjacent-face geometry: subject v2's closed
cone bowl read a counter corner 'inside' at the FULL distance — an
impossible "PENETRATING 1088.7 mm" (deeper than the object's 354mm bbox
diagonal). classify_point now parity-verifies every sign-test INSIDE
claim (parity = ground truth for watertight meshes); OUTSIDE keeps the
fast path. Sanity law for reading audits: a penetration depth exceeding
the pair's bbox diagonal is impossible — treat it as a tool bug, not a
scene bug, and say so.

### 72. In-process BVH cache: freshen depsgraph BEFORE hashing (session 16, v3)
matrix_world is a lazily-updated RNA cache. world_bvh() hashes the cache
key AFTER evaluated_depsgraph_get() now — hashing before it served a
pre-commit tree after physics commits moved/rotated an object, and the
in-process audit then reported a phantom "PENETRATING 38.6mm" (fresh
processes read exact contact on the same file). Tool-disagreement rule:
when an in-process audit contradicts a fresh-process schema/gate, the
FRESH process wins — then suspect cache staleness in the old process.

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
2x view_layer.update() before ANY matrix read; (2) SAME-FRAME — anchor
captures assert scene.frame_current == the requested frame and return
SNAPSHOT copies so later frame_sets cannot poison them
(anchor_local() is pure math on snapshots); (3) FULL-TIMELINE —
held-state prop actions get the terminal key (law 106); (4) SANITY
RADIUS — post-key verification that the prop's composed world stays
within max_dist of an anchor at EVERY keyed frame, catching any
phantom/drift class known or novel. Exporter twin: gate 14 keeps
bone-carried props within 1.0 m of some joint of their owning skin
(calibrated on the broken export: legit carry <= ~0.7 m, the phantom
>= 1.32 m at every carry frame, the aimed hold 0.02 m).
