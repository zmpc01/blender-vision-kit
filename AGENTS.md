# AGENTS.md — Consumer Agent Guide (VISION-FIRST VARIANT)

> Read this first if using the kit to make scenes. This is the
> **vision-capable agent** variant of blender-agent-kit: your own image
> understanding (Read a rendered PNG) is the primary eye — and the only
> eye. There is NO vision-substitute machinery in this kit (no ASCII
> packs, no external VLM): if you cannot see images natively, use
> upstream blender-agent-kit instead. If you're the meta-agent working
> ON the kit, read `.agents/SKILL.md`.
>
> Lineage: fork of zmpc01/blender-agent-kit @3c0c60d (docs condensed from
> upstream@01dd147). Upstream serves BLIND agents; this variant serves
> agents that SEE. All mechanics laws carry over — see the LAW MAP.

## What this kit is

Headless Blender 4.x/5.x LTS previz toolkit for vision-capable LLM agents
in a no-root, no-GPU, 4GB RAM Linux container. Build scenes via `bpy`
scripts or JSON patches, render with Workbench/EEVEE/Cycles, LOOK at the
renders with your own vision, verify geometry with deterministic gates,
export to glTF for web preview.

## Quick start

```bash
./install.sh                    # one-time: Blender 5.2 LTS + libEGL + Pillow
cp scripts/scene_template.py scripts/my_scene.py  # copy + edit build_scene()/animate()
./scripts/blrun.sh --background --python scripts/my_scene.py -- \
    --output output/my_scene --dry-run --scene-name my_scene   # validate structure
./scripts/blrun.sh --background --python scripts/look.py -- \
    --scene my_scene --output output/my_scene/look             # LOOK at it
```

NOTE: the script filename IS the scene name — `scripts/my_scene.py` is
addressed as `--scene my_scene` / `--scene-name my_scene` everywhere.
A static scene (no animation) is fine: make `animate()` a no-op or
delete it — look.py and the render path both handle scenes without
animation.

## THE VISION LOOP (this replaces the blind kit's perceive/critique loop)

```
1. ACT:    edit scene script OR apply_patch.py (batch mutations!)
2. STATE:  apply_patch.py --save-blend work.blend     # ← the state carrier
3. LOOK:   look.py --load-blend work.blend            # ONE invocation:
           images + validator verdict + object manifest + readiness
4. READ:   Read the grid.png your eyes; cross-check any mm-class
           impression against the verdict numbers BESIDE the images
5. REASON: decide the next patch (ids come from the manifest)
```

```bash
# The canonical edit-look cycle (2 invocations per iteration):
./scripts/blrun.sh --background --python scripts/apply_patch.py -- \
    --patch /tmp/patch.json --save-blend output/my_scene/work.blend
./scripts/blrun.sh --background --python scripts/look.py -- \
    --load-blend output/my_scene/work.blend --output output/my_scene/look

# Fresh iteration (first look at a scene script, NO patch state yet):
./scripts/blrun.sh --background --python scripts/look.py -- \
    --scene my_scene --output output/my_scene/look
```

**LAW: never rebuild a scene to inspect it after patching.** `--scene`
REBUILDS from the script and silently discards patch-applied state (RB
settle, manual edits, physics results). `--load-blend` is the state
carrier; `--scene` is for fresh iterations only.

**LAW: batch mutations.** One patch chain with many mutations (+
`render_viewport`/`audit` ops interleaved) beats five small patches —
each invocation pays a Blender cold start (~3–8s).

### look.py — what one invocation gives you (forced pairing)

look.py ALWAYS prints, beside the images it writes:
- `VERDICT: PASS|WARN|FAIL` + engine/frame/object counts + scene bounds
- validator issues P0/P1/P2 (floating / below-floor / intersections /
  above-ceiling) with object ids and mm-scale descriptions
- per-image readiness: `luma= clipped=% dark=% subject=%` + flags
  (BLOWN-OUT / NEAR-BLACK / NEAR-EMPTY) — check this BEFORE trusting
  what you see; a bad image lies
- object-id manifest (id/type/dims/centroid) — the ids your next patch
  needs; also written to `look_manifest.json`
- annotations state (render-time only, NEVER saved into any .blend)

Annotations (default ON, `--no-annotate` to strip): 1m ground grid, RGB
axis gnomon (X red / Y green / Z blue), top-8 object index labels (yellow,
`--labels N`), red bbox wireframes on validator-flagged objects.
`--closeup <id>` adds an auto-framed macro render of one object.
Exit codes: 0 = PASS/WARN clean, 3 = validator P0/P1 present —
propagated through blrun (verified); in pipelines check
`${PIPESTATUS[0]}` or grep the `VERDICT:` line.

### The two-column law (the core discipline)

**EYES TRIAGE AND COMPOSE; GATES DECIDE GEOMETRY.**

| Your eyes decide | The gates decide |
|---|---|
| composition, framing, mood | floating / penetration (mm-class) |
| "anything grossly wrong?" | exact placement, contact state |
| object identity, layout, hue | overlap volumes, support |
| does it LOOK right | is it MEASURED right |

- A visual float/penetration impression is a HYPOTHESIS until a gate
  confirms it (you are a sycophant for your own eyes — 12mm penetration
  is invisible, a grounded actor can look floating at the wrong angle).
- A PASSING gate does not make the shot look right. Composition is still
  yours. The two columns never blend.
- `audit` (patch op) after every placement change: exits non-zero on
  penetration. `place_on` = 0.0mm one-shot rest. See Placement below.

### Vision failure-mode laws (train these in)

- **L1 IMAGE BUDGET**: the grid is ONE image; closeups only on flagged or
  ambiguous subjects; re-look instead of hoarding stale images. Your
  context floods faster than a blind agent's ever did.
- **L2 CHIRALITY**: top/front views are mirrorable in your mental model.
  Confirm handedness via the RGB gnomon before acting on any
  left/right/north/south instruction.
- **L3 OVERLAY TRUST**: annotations are render-time overlays, not scene.
  A missing red box is NOT proof of correctness (the validator only sees
  bbox pairs >5% overlap). A red box IS validator output — numbers, not
  eyes — and may be acted on.
- **L4 COLOR FROM SCHEMA**: never judge absolute color from a render;
  read material color from `scene_schema.py`. Workbench Standard/MATERIAL
  is calibrated for hue comparison, not absolute values.
- **L5 REPRESENTATION SPLIT (motion)**: no single animation image answers
  everything — trajectory grids answer PATH SHAPE, onion-skins answer
  SPEED/AGE/DIRECTION, the numeric table answers MAGNITUDE; filmstrips
  answer none of these well. Ask which question you're answering, read
  that row/cell; when in doubt run motion_study.py (one invocation, all
  of them).
- **L6 SCANNER RANKS, EYES VERDICT**: transient_scan's event table is an
  attention device, not a verdict — pixel diff finds CHANGE, the
  validator sweep names STATES, but only your eyes at full res (--frame N
  --closeup) decide what actually happened. Conversely: a clean keyframe
  sheet proves NOTHING about transients between keys.

## Canonical workflow (full arc)

```bash
# 1. Dry-run (instant, no render — validate scene builds)
./scripts/blrun.sh --background --python scripts/my_scene.py -- \
    --output output/my_scene --dry-run --scene-name my_scene

# 2. LOOK (4-angle annotated grid + verdict + manifest, ~4-8s)
./scripts/blrun.sh --background --python scripts/look.py -- \
    --scene my_scene --output output/my_scene/look

# 3. Patch fixes without full rebuild (~2s) — batch + save state
cat > /tmp/patch.json << EOF
{"scene":"my_scene","frames":24,"mutations":[
  {"op":"move_to","id":"Cube","target":[1,0,0.6]},
  {"op":"place_on","id":"Cube","supports":["Table"]},
  {"op":"audit"},
  {"op":"render_viewport","output":"output/my_scene/check2.png","angle":"persp"}
]}
EOF
./scripts/blrun.sh --background --python scripts/apply_patch.py -- \
    --patch /tmp/patch.json --save-blend output/my_scene/work.blend

# 4. LOOK the saved state (never --scene after patching)
./scripts/blrun.sh --background --python scripts/look.py -- \
    --load-blend output/my_scene/work.blend --output output/my_scene/look2

# 5. Closeup on a flagged/ambiguous subject (macro beats wide lineups)
./scripts/blrun.sh --background --python scripts/look.py -- \
    --load-blend output/my_scene/work.blend --closeup Cube \
    --output output/my_scene/look3

# 6. Animation understanding (path shape + speed/age + numeric table)
./scripts/blrun.sh --background --python scripts/motion_study.py -- \
    --load-blend output/my_scene/work.blend --out output/my_scene/motion

# 6b. Transient spot-check (issues that only exist on some frames)
./scripts/blrun.sh --background --python scripts/transient_scan.py -- \
    --load-blend output/my_scene/work.blend --out output/my_scene/scan

# 7. Ship: full render + MP4 + glTF + .blend + viewer
./scripts/blrun.sh --background --python scripts/my_scene.py -- \
    --output output/my_scene --engine eevee --frames 24 \
    --quality preview --encode-mp4
./scripts/blrun.sh --background --python scripts/export_gltf.py -- \
    --scene my_scene --output output/my_scene/scene.glb --frames 24
# patch-built scenes: export/save accept --load-blend too (ship the
# SAVED state, not a rebuild):
#   export_gltf.py --load-blend output/my_scene/work.blend --output .../scene.glb
./scripts/blrun.sh --background --python scripts/save_blend.py -- \
    --scene my_scene --blend-out output/my_scene/scene.blend
cp viewer/index.html output/my_scene/
```

## Tool reference

### blrun.sh — the wrapper (always use, never call blender directly)
```bash
./scripts/blrun.sh --background --python <script.py> -- [script args after --]
./scripts/blrun.sh --warm-cache    # one-time EEVEE shader cache warmup (~30s)
```
Env vars: `BLENDER_BIN`, `BLENDER_DISPLAY` (default `:99`), `KEEP_XVFB=1`,
`BLENDER_HOME` (caches), `BLENDER_KIT_LIBS`. Handles: Xvfb lifecycle,
libEGL `LD_LIBRARY_PATH`, `--python-use-system-env` (so `import
blender_kit` works), signal traps, stale X locks, fail-closed gate
(grep for Python errors → nonzero exit). Script exit codes ARE
propagated (verified: look.py exit 3 → blrun exit 3; the old "not
propagated" lore was a pipeline-probe artifact — `$?` after a pipe is
the LAST command's exit, not blrun's).

### look.py — the one vision-loop command (see THE VISION LOOP above)
```bash
... look.py -- --load-blend work.blend [--angles front,side,top,persp|none] \
    [--frame N] [--engine workbench] [--annotate|--no-annotate] \
    [--labels 8] [--closeup Obj] [--closeup-fill 1.5] [--grid-cols 2] \
    [--no-grid] [--lens 50] [--target X,Y,Z] [--w 640 --h 480] \
    [--output DIR] [--no-fail-on-issues]
```
`--angles none --closeup Obj` = closeup-only look (L1 image budget:
no grid when you already know the subject).
Defaults tuned for vision: 640×480 angles. Large scenes overflow the
fixed 5m camera offsets — aim with `--target`/`--lens`, or look at the
subject cluster (the ground overflowing the frame is fine).

### scene_template.py — copy-and-edit scene template
Pattern: `build_scene()` → context dict; `animate(ctx, ...)` → keyframes;
`main()` → `common_parser()` + `configure_render()` + `render()`.
Shared flags: `--output DIR` (required), `--engine
workbench|eevee|cycles` (raw Blender enums like `BLENDER_EEVEE_NEXT` are
accepted and normalized), `--frames N`
(24), `--start N`, `--samples N`, `--w W --h H`, `--still N`, `--dry-run`,
`--quality previz|viewport|draft|preview|final`, `--encode-mp4`, `--aa
off|fxaa`, `--shade studio|flat`, `--png`, `--fps N`, `--scene-name NAME`.

### apply_patch.py — JSON patch mutations (the act layer)
```bash
./scripts/blrun.sh --background --python scripts/apply_patch.py -- \
    --patch /tmp/patch.json [--save-blend out.blend] [--export-schema out.json]
./scripts/blrun.sh --background --python scripts/apply_patch.py -- \
    --patch-json '{"scene":"my_scene","mutations":[...]}'   # inline
./scripts/blrun.sh --background --python scripts/apply_patch.py -- --list
```
Patch format: `{"scene":"module"|"load_blend":"file.blend","frames":N,"mutations":[...]}`
35 ops: `set_location/rotation/scale`, `set_material_color/roughness/metallic`,
`delete_object`, `duplicate_object`, `set_camera_location/lens`,
`set_light_energy/color`, `set_world_strength`, `set_exposure`, `set_frame`,
`render_viewport`, `add_cube/sphere/cylinder/cone/torus/plane/empty`,
`move_to`, `place_on`, `seat_at`, `snap_z`, `physics_settle/place/oracle/gate`,
`audit`, `seam_views`, `heat_bake`, `clear_bvh_cache`.
`add_*`: `id` required (refuses duplicates), sizes are FINAL world dims,
`location` = CENTER (not bottom — seat with `place_on`).
Composition: `add_*` → `place_on`/`physics_place` → `audit` in ONE chain.
Full details: `/kb/placement_and_physics.md`. Headlines:
- `audit` exits non-zero on penetration — chain after every placement change
- `place_on(id, supports)` one-shot 0.0mm rest, solves Z only (keeps x/y)
- `seat_at(id, seat)` slot seating via anchor EMPTY; `snap_z(id, z)` exact z
- `physics_settle/place/oracle/gate` — gravity finds the pose; oracle
  WITNESSES why X can't sit; gate rejects scene-wide with a fix queue
- `audit` pair states: PENETRATING (penetration_mm) / TOUCHING / NESTED /
  CLEAR (clearance_mm); audit only sees pairs within 100mm pad — floaters
  >300mm appear in NO pair; use `physics_gate` or `look` verdict for
  scene-wide floating. **LAW: exact-match the pair's `state` field
  (PENETRATING/TOUCHING/NESTED/CLEAR) — never `verdict`, which is the
  human string ("PENETRATING 7.8 mm — fix") and WILL drift**
- **reference tokens**: `move_to` reference = `bottom-center` (default) |
  `centroid` | `origin`; `snap_z`/`seat_at` reference = `bottom`
  (default) | `origin` | `centroid`. `bottom` anchors the object's bbox
  BOTTOM to the target z — usually what you want for resting.
- **place_on: name the TOPMOST surface** the mover should rest on. The
  single-contact solver ignores interposed supports — `supports:["Floor"]`
  under a rug rests the object THROUGH the rug; name the `Rug`.
  Footprint AUTO-WIDEN: default `bottom` misses pedestal supports
  (tabletop-on-leg, lampshade-on-pole) — on no-support it retries
  `grid` automatically (report records `footprint_autowiden`).
- **Animated prop + placement**: pass `override:"keyframe"` — the op
  REBASES the whole animation path by the placement delta (every
  keyframe keeps its relative placement; a current-frame re-key leaves
  later keys at the pre-placement pose and the prop drifts into its
  support — measured 20mm by f24)
- **seat_at facing**: `align:true` (default) copies the anchor empty's
  rotation to the seated object — face a chair by rotating its anchor.
- **Furnished/set-dressed scenes**: a scene-wide `audit` fails on any
  pre-existing penetration (the shipped `scene_interior_room` fails its
  own validator baseline — window frame embedded in wall, by design as
  a test fixture). On such scenes pass `{"op":"audit",
  "fail_on_penetration":false}` for the report, or scope it:
  `{"op":"audit","id":"MyMover"}` reports only that object's pairs.
- `apply_patch --list` prints every op's param signature — check it
  before guessing key names (a wrong key now errors with the signature).

### viewport_capture.py — multi-angle screenshots (look.py uses this)
```bash
./scripts/blrun.sh --background --python scripts/viewport_capture.py -- \
    --scene my_scene --output grid.png --angles front,side,top,persp \
    --engine workbench --grid-cols 2
... --angles custom --custom-loc "3,0,1.5" --engine workbench --no-grid
... --ring 6 --engine workbench --grid-cols 3
```
Angles: `front,side,top,persp,back,right,active,custom` or `--ring N`.
Defaults: workbench, 640×480, lens 50, target = scene bbox center.
`--no-grid` = individual files. No annotations (that's look.py's job).

### keyframe_contact_sheet.py — animation verification (superseded for understanding)
```bash
... --scene my_scene --output motion.png --frames 6 --grid-cols 3 --engine workbench
... --orbit --orbit-radius 8 --orbit-height 4
```
Samples N frames across the range, stitches a labeled grid (480×360 cells
default). Mid-stride freezes read "fallen" to your eyes — that is noise;
verify motion with fcurve probes, not one still. For UNDERSTANDING motion
use motion_study.py below; the contact sheet remains a quick eyeball of
frame states.

### motion_study.py — animation understanding (M5 P3, measured)
```bash
... --scene my_scene | --load-blend work.blend   # + --start/--end --samples 8 --objects A,B
```
ONE invocation -> numeric MOTION-TABLE + a labeled 2×2 grid
(`motion_grid.png`) + filmstrip. Read order is printed beside the images:
- **Row 1 TRAJECTORY** (top=plan, front=elevation): green polyline = path
  SHAPE, yellow ticks = time (tick spacing = speed). Shadowless by design
  (see gotcha 121).
- **Row 2 ONION-SKIN**: ghost copies at sampled frames — lightest = oldest,
  solid red = now; ghost SPACING = speed; direction unambiguous. This is
  the measured winner for rise/fall/speed/direction reads.
- **MOTION-TABLE**: per-object median step + `POP-FRAMES` (teleports) and
  `BURST-MOTION` (median≈0 but real bursts = sampled transient → run
  transient_scan.py).
Measured verdicts that shaped it: filmstrips lose vertical nuance and
hide spin; onion-skin reads rise/speed instantly; trajectory overlays are
the only honest path-shape read and MUST be multi-angle (a vertical trail
collapses from one angle); solid ghosts occlude thin polylines at slow
motion, hence the two render passes.

### transient_scan.py — spot-check for frame-transient issues (M5 P4)
```bash
... --scene my_scene | --load-blend work.blend   # + --start/--end --top 6
```
Some issues only exist on certain frames — usually BETWEEN keyframes. A
keyframe contact sheet catches them by luck. The scan renders EVERY frame
at previz res (~0.3s/frame), then combines TWO radars:
1. **change radar**: consecutive-frame pixel diff, MAD-adaptive floor,
   clustered into ranked EVENTS (catches pops, flickers, teleport bursts)
2. **state radar**: the validator run at EVERY frame — a parked wrong
   state (object sunk through the floor) has near-zero pixel diff; the
   validator names it semantically (`P1 floor_penetration (GlitchBox)
   f15..f19`)
Findings are classified by DURATION: short windows = TRANSIENT (the hunt
target); present in most frames = PERSISTENT baseline design (a jump
reads as flight-floaters on every airborne frame — listed once, not
per-frame). Reading the EVENT-TABLE: the event SPAN/peak comes from the
pixel-diff change radar, the indented `TRANSIENT <sev> <type> (<ids>)
fA..fB` lines are the validator's semantic state findings — the state
window can start AFTER the pixel peak (change and wrong-state are
different things; confirm the state frame, not just the peak). Output:
EVENT-TABLE + `suspects.png` strip (start/PEAK/end + BAD cells) +
doctrine line. **The scanner RANKS; the eyes VERDICT** —
confirm suspects at full res: `look.py --load-blend work.blend --frame N
--angles none --closeup <id>`.

### scene_schema.py — JSON scene state export
```bash
... --scene my_scene --output scene.json --with-bounds
... --load-blend scene.blend --output scene.json --with-bounds
```
Objects (id/type/location/rotation/scale/materials/mesh stats), lights,
cameras, animation, world, frame range; `--with-bounds` adds world bboxes.
THE source for absolute colors (L4) and exact numbers.

### validate_scene.py — structural validator (look.py runs it internally)
```bash
... --scene my_scene --output validation.json --fail-on-issues
```
Floating / below-floor / floor-penetration / suspicious intersections
(>5% of smaller object volume; P0 at ≥30%) / above-ceiling. Deterministic
bbox analysis. Severities: floating = P1, below-floor = P0,
floor_penetration = P1 (depth > max(5cm, 20% height); ground slabs
excluded), intersection = P1 (P0 at ≥30%), above-ceiling = P2.

### export_gltf.py / save_blend.py / agent_server.py / polyhaven.py
- `export_gltf.py --scene S --output scene.glb --frames N` — glTF for the
  web viewer; preserves meshes/PBR/cameras/punctuals/keyframes; loses AREA
  lights, modifiers, volumes (`kit_atmo` tag), render-hidden (excluded).
- `save_blend.py --scene S --blend-out s.blend [--still-frame N ...]`
- `agent_server.py --port 8765 --workdir /tmp/session` — SSE live viewer bridge
- `polyhaven.search_assets/add_to_scene/load_hdri` — ~2,400 CC0 assets,
  real-world scale, 2k default

## Quality presets

| Preset | Resolution | Engine | Use case | ~Time/frame |
|--------|-----------|--------|----------|-------------|
| `previz` | 480×270 | Workbench | vision geometry check | ~0.3s |
| `viewport` | 960×540 | Workbench | vid2vid guidance track | ~0.05s |
| `draft` | 320×180 | EEVEE | material iteration | ~0.5s warm |
| `preview` | 640×360 | EEVEE | final preview animation | ~2s (MEASURED 8.5s/frame on 4-core llvmpipe 2026-09-28 — budget 10s/frame; a 24f render ≈ 3.5min, EXCEEDS a 2-min tool timeout: run inside one long-timeout call or render_daemon) |
| `final` | 960×540 | Cycles | final still | ~50s |

look.py/viewport_capture default 640×480 workbench — the vision sweet
spot (measured: AA-OFF workbench ≈ 0.05s/frame at 960×540; the cost is
cold-start, not pixels).

## LAW MAP (upstream AGENTS.md → this variant)

| Upstream | Disposition here |
|---|---|
| 1-10 (engine/rendering) | KEPT verbatim (§ Engine & rendering) |
| 11-19 (scene building) | KEPT verbatim |
| 20-26 (VLM verification) | REWRITTEN → two-column law + L1-L4 (remote-VLM stabilization is obsolete; the underlying truth — verify geometry programmatically — kept and strengthened) |
| 27 (ASCII packs) | DEMOTED → Escalation paths (kept in tree, `/kb/ascii_vision.md`); later REMOVED entirely by the session-4 course correction — vision-native-only kit |
| 28-36 (placement & physics) | KEPT verbatim |
| 37-40 (color discipline) | KEPT verbatim |
| 41-43 (sub-agent orchestration) | KEPT verbatim |
| 44-54 (glTF/export) | KEPT verbatim |
| 55-61 (git & environment) | KEPT verbatim |
| 62-64 (Blender version compat) | KEPT verbatim |
| 104-110 (sessions 25-26 laws) | KEPT verbatim (§ Mechanics laws 104+) |
| — | NEW: vision loop laws, L1-L4, state-carrier law, annotation law |

## Gotchas (mechanics — these save hours)

### Engine & rendering
1. **Always use blrun.sh** — it handles Xvfb, libEGL, `--python-use-system-env`, signal traps. Never call `blender` directly.
2. **EEVEE needs Xvfb** — Cycles doesn't. blrun.sh always starts Xvfb.
3. **EEVEE first render is ~28s cold** — run `blrun.sh --warm-cache` once per container.
4. **EEVEE OOM risk**: peaks at 1.6GB for 273-object scenes on 5.2. Use Workbench for previz, Cycles for final.
5. **5.x EEVEE renders ~4-12% brighter** than 4.5 — reduce exposure ~-0.5 EV on 5.x high-key scenes.
6. **Workbench reads `mat.diffuse_color`** not Principled Base Color. `make_material()` sets both; `set_material_color` op sets both.
7. **AgX crushes previz colors** — kit forces `view_transform='Standard'` for previz/workbench. AgX for final Cycles only.
8. **Workbench background** = world color (or theme black headless). Set a flat neutral world (the `viewport` preset does).
9. **Volumes render as opaque shells** in Workbench — tag atmosphere `ob["kit_atmo"]=True`.
10. **AA dominates Workbench render time** — `--aa off` is 5-6× faster.

### Scene building
11. **Cube "floating"**: `primitive_cube_add(size=S, location=(0,0,Z))` puts the ORIGIN at Z. To rest on z=0: `location=(0,0,S/2)`.
11b. **Verified primitives on 5.2.2**: cube/sphere/cylinder/cone/torus/plane/empty. `primitive_capsule_add` DOES NOT EXIST — capsule = cylinder + hemisphere caps (or a scaled sphere for previz actors).
11c. **`frame_set()` takes ints only** — fractional keyframe math needs `int()` (floats raise TypeError).
11d. **Multi-part actor assembly**: child parts need `part.parent = body; part.matrix_parent_inverse = body.matrix_world.inverted()` (keep-pose parenting) or the body walks away and leaves them. Origins at the joint, mesh offset below.
11e. **Swing axis ⊥ travel**: a leg keyframed on `rotation_euler.x` swings along ±Y — walking +X needs the swing axis ⊥ the travel direction. Verify gait with matrix probes (f1 vs fN), not gates or stills.
12. **`set_location` moves the ORIGIN** — on origin-baked meshes this acts relative. Use `move_to` for world-space moves.
13. **`transform_apply(scale=True)` zeroes location** (4.5.13) — avoid it. Pass `scale=` to primitives instead.
14. **Vertex-baked origins detonate transforms** — build geometry around local (0,0,0) for anything animated/simulated.
15. **Animated location channels clobber placement** — placement ops refuse by default; `override:"keyframe"` inserts a visible key.
16. **Boolean keyframes need f=1 anchors + CONSTANT interpolation**.
17. **`action.fcurves` moved in 5.x** — use `iter_fcurves(action)` from blender_kit.
18. **`mat.use_nodes = True` deprecated in 5.x** — use `ensure_use_nodes(mat)`.
19. **`.blend` files are forward-only** — 5.2 format can't open in 4.x. Use glTF for cross-version interchange.

### Placement & physics
28. **Use `audit` op after every placement change** — chains into the same patch, exits non-zero on penetration.
29. **`place_on` solves Z only** (keeps x/y) — `move_to` first if over the wrong spot.
30. **`place_on` is single-contact-plane** — seated figures spanning cushion+floor need `seat_at` + anchor empties.
31. **Physics ops need named movers** — `objs:["Mug"]` makes everything else terrain. `objs:null` = whole-scene free-fall (never wanted).
32. **RB sim pose lives only in `matrix_world`** — RNA `location` keeps spawn pose. Commit before reading geometry.
33. **RB point cache survives object teardown** — always `frame_set(1)` before every sim.
34. **BOX collision is centered on ORIGIN, not bbox** — off-origin mesh gets displaced collision. Use CONVEX_HULL for origin-offset geometry.
35. **Bullet depenetrates to exact rest** on flat contacts but can eject wedged overlaps sideways — refuse-by-default, `repair_penetrations:"physics"` for recorded repairs.
36. **Treadmill law**: belt streams backward, subject world-static → world-static + visible = paces the subject. Compose FX/debris with the belt or hide.

### Color discipline (vid2vid guidance)
37. **Environment = white/grey value ladder**. NO chromatic environment materials.
38. **Subjects = ONE color per body**. ~3 chromatic classes total.
39. **Light BASE colors are chromatic traps** in Workbench — keep light bases neutral.
40. **STUDIO shade beats FLAT** on white world.

### Sub-agent orchestration
41. **One asset module per sub-agent** — giant briefs time out. Each sub-agent <5 min.
42. **On timeout, harvest artifacts** — check output paths before relaunching.
43. **Gate sub-agent code** — audits + verdict + look readback before integration.

### glTF / export
44. **glTF loses AREA lights** — `<model-viewer>` `environment-image="legacy"` adds ambient.
45. **glTF exports IGNORE ray-visibility** — kit excludes `hide_render` objects; gate fail-closes the leak.
46. **glTF ACTIONS mode doesn't bake constraints** — use SCENE bake mode or export aim targets as nodes.
47. **glTF `export_cameras` defaults False** — always export through `blender_kit.export_gltf`.
48. **three.js sanitizes node names** — dot-free comparison for node lookups.
49. **`<model-viewer>` struggles with large scenes** (>100 objects) — render stills alongside .glb.
50. **100MB git limit** — big .blends ship as release assets only.
51. **glTF preserves**: meshes, PBR (Principled only), cameras, punctuals, keyframes. **Loses**: AREA lights, modifiers, procedural shaders, collections, volumes (`kit_atmo`).
52. **three.js `mixer.setTime` breaks LoopOnce+clamp** — pre-pad tracks, use LoopRepeat; glTF keys are TIMELINE-ABSOLUTE at `t=frame/fps`.
53. **three.js physical lighting**: diffuse/π; glTF punctuals are 683× Blender watts (`l.intensity /= 683`). Parity math in LINEAR.
54. **USD rejected as web format** — JSON stays story source of truth.

### Git & environment
55. **GIT IS THE DISK** — push to both GitHub + GitLab on every micro-step. Never force push.
56. **GitLab WAF blocks ~1/3 of pushes** — retry up to 8× with 5s sleep, `oauth2:TOKEN` format.
57. **Watchdog reverts `/home/z/my-project/`** — work outside it (e.g. `/home/z/work/`).
58. **Background processes die between tool calls** — long renders in ONE Bash call with timeout, or `render_daemon.py`.
59. **After ANY git merge** — `grep -rn "<<<<<<<" scripts/` + smoke one blrun invocation before long renders.
60. **GitHub Release != published** — `PATCH /releases/<id> {"draft":false}` after upload.
61. **Sync-copy clones carry origin=local** — re-point to GitHub before updates.
61b. **tools/ symlink hazard** — `tools/` may symlink to a shared provisioned toolchain, but git checkout that writes inside a symlinked dir REPLACES the symlink with a real dir (broken-symlink signature: only the two scripts, no blender). `run.sh --scope-check` warns; re-link with `ln -sfn <provisioned>/tools tools`.
61c. **Big downloads stall** — single-stream Blender downloads stall in this sandbox; install.sh falls back to `tools/chunked_dl.sh` (16 parallel ranged chunks, ~20s for 383MB).

### Blender version compat
62. **Kit runs on 4.5 and 5.2 LTS unchanged** — compat shim normalizes engine id, fcurves, sky type, use_nodes.
63. **Default install: 5.2 LTS** (until July 2028).
64. **`gpu.init()` on 5.2** crashes in no-GPU containers — Xvfb remains required on llvmpipe.

### Vision-loop gotchas (new, variant-discovered)
111. **Annotations are render-time only** — look.py builds a `KIT_ANNOT_*` layer (grid/gnomon/labels/flags) and deletes it in a `finally`. There is NO way to save it into a .blend. A stray `KIT_ANNOT_*` object in a scene means an aborted look — delete it, and re-run the look for honest images.
112. **Ground planes don't get labels** — a 20×20m ground "label" renders as a giant billboard blocking the top view (measured, first run). Ground-like slabs (flat + ≥6m² footprint) are excluded from labeling. If you label a huge flat object deliberately, do it in your own scene code, not via look.
113. **The gnomon sits SW of scene center** (center −1.5m, −1.5m) — inside standard framing but off the subject. At world origin it sits INSIDE the centered subject (invisible); at the scene corner it's out of frame. Both measured.
114. **Camera offsets are FIXED 5m** in the standard angles — big scenes overflow the frame (ground overflow is fine; the subject cluster should fit). Aim with `--target`/`--lens` or `--closeup`.
115. **blrun propagates exit codes; pipelines don't** — look.py exit 3 arrives at blrun's caller intact (verified twice). The earlier "swallowed" claim was a probe error: `$?` after `blrun ... | grep ...` is GREP's exit, not blrun's. In pipelines check `${PIPESTATUS[0]}` or grep the `VERDICT:` line.
116. **Trusting a look without readiness** — a BLOWN-OUT/NEAR-BLACK/NEAR-EMPTY flag means your eyes have nothing to work with; fix the render (exposure/fill/crop) before reasoning about the scene. The flag is printed BESIDE the image; read it first.
117. **Animated scenes: the look verdict evaluates the `--frame` POSE** — jointed actors legitimately FAIL P0 at mid-stride scissor-pass frames (leg bboxes cross by design). Verify gait with matrix probes across frames (law 108), not with the frame verdict or a single still. `--no-fail-on-issues` keeps exit codes clean for probe loops.
118. **Contact sheets are for EYES, not for text probing** — pixel-level text dumps lose actors and achromatic cells; motion truth comes from numeric probes (manifest f1 vs fN, fcurve sampling) and your own eyes on the sheet. "Labeled grid" means visual-only labels.
119. **Verified primitives on 5.2.2**: cube/sphere/cylinder/cone/torus/plane/empty — `primitive_capsule_add` DOES NOT EXIST (capsule = cylinder + caps, or a scaled sphere for previz). **`frame_set()` takes ints only.** **Multi-part actors**: `part.parent = body; part.matrix_parent_inverse = body.matrix_world.inverted()` (keep-pose) or the body walks away and leaves them; origins at the joint; swing axis ⊥ travel direction.
120. **Blender 5.2 slotted actions: `Action.fcurves` is GONE** — use the kit's `iter_fcurves(action)` compat helper (handles 4.x/5.x). Same class of trap: `scene.view_layer` DOES NOT EXIST (`AttributeError`) — it's `bpy.context.view_layer`.
121. **Workbench shadow buffer goes stale across in-process `hide_render` toggles** — objects hidden between renders still CAST SHADOWS in the next render (measured in motion_study: ghost shadows with no ghosts). If you toggle visibility for multi-pass rendering, disable shadows for the passes that shouldn't have them; don't trust shadow absence/presence after a toggle.
122. **Solid overlays occlude thin overlays** — onion ghost spheres buried the 15mm trajectory polylines entirely when motion was slow (n64 bisect, green=0). Render competing representation layers in SEPARATE passes and stitch, or shrink/alpha the dominant layer.
123. **`mats = other.data.materials` on a LINKED duplicate strips the ORIGINAL's materials** — material slots live on mesh data; a `.copy()` object shares the mesh. For re-materialized copies use `obj.data = original.data.copy()` and name the copy (`KIT_*` prefix so cleanup finds it).
124. **below_floor only catches FULLY-submerged objects** — a half-sunk box (top above floor) was invisible to every validator check (T6 measured). The `floor_penetration` P1 check (depth > max(5cm, 20% height)) now covers it; ground-like slabs are excluded so roads/rugs stay silent.
125. **ORTHO NEAR-PLANE BBOX CULL (5.2 workbench, measured)** — a near plane that INTERSECTS an object's bbox culls the object's below-plane geometry ENTIRELY (bisection: mug visible at near-z 1.20, vanished at 0.87 = the first plane cutting its bbox). Any 'clip-slice' diagnostic built by parking the near plane on a measured surface is UNRENDERABLE. section_pair/seam_views slices therefore render INTACT geometry (seam-framed plan + elevation); mm truth stays numeric. Never clip through geometry you want to see.
126. **Never edit a script while it is executing in background** — bash reads scripts incrementally by byte offset; an Edit mid-run desyncs the interpreter and kills it silently (burned an install run this way). Kill the process first, edit, re-run. Also true for any long-running generator script.
127. **Diagnostic images carry the WHERE; verdicts carry the HOW-MUCH** — after the 5.2 near-cull discovery, every placement diagnostic (section_pair, seam_views) renders intact seam-framed views for the eyes and leaves mm decisions to the numeric report. Don't reintroduce pixel-measured verdicts, and don't trust a flat featureless render as 'nothing there' — it may be the cull (gotcha 125).
128. **Sky world × EEVEE overexposure (R3 F6)** — `add_sky_world()` default strength 1.0 (physical sky) blows out EEVEE stills in studio setups: red reads pink, highlights clip. Workbench looks NEVER reveal this (workbench ignores world lighting). For studio/product scenes pass `strength=0.35..0.5`; reserve the default for outdoor scenes. Diagnose via look readiness `clipped_pct` on the EEVEE render, not the workbench one.

### Mechanics laws 104-110 (kept from upstream sessions 25-26)
104. **Bake-input pools are NOT export payload** — purge unassigned actions before glTF (one-object-one-action contract).
105. **ONE-OBJECT-ONE-ACTION on the export** — count DISTINCT animations per node, not channels.
106. **Actions that HOLD a state past their window must key the FULL timeline** — terminal key at scene end.
107. **Entry scripts OWN their sys.path** — Blender --background does not add the --python script's dir (cwd-independent insert from `__file__`).
108. **Numeric ground truth FIRST; vision second** — matrix/track-delta numbers come first; visual confirmation on ZOOMED crops; never file a first-pass visual flag without a definition-tight recheck. (Vision agents: this law is MORE true for you — your first-pass flags are your own eyes.)
109. **Stale build caches impersonate reverts** — on sandbox boot, kill + nuke + restart dev servers; treat single-digit-ms compiles as cache hits.
110. **PHANTOM OFFSETS: anchor captures must be SAME-FRAME snapshots; every carry gets a sanity radius** — live-read (frame_set + 2× update) before ANY matrix read.

## Numeric image gates (the complement to your eyes)

- **`scripts/image_metrics.py`**: deterministic pixel statistics
  (luma / saturation / Sobel edge energy / dynamic-range usage incl.
  `p_dark`). Use to anchor exposure and contrast verdicts in numbers
  (the +1.0EV workbench default was chosen with exactly these) and for
  regression checkpoints that must not depend on subjective reading.
  `python3 scripts/image_metrics.py render.png [...]` prints a one-line
  summary per image.
- Doctrine: eyes triage and compose; gates decide geometry. A numeric
  gate NEVER substitutes for looking (that was the blind kit's way) —
  and looking never overrides a failing gate without a measured reason.
- Sub-agents WITHOUT vision: this kit is not for them (upstream's
  audience). In QA waves they may still run scripts and assert textual
  output, but every visual verdict belongs to the vision-native agent.

## Crowd system (sibling repo composition)

The crowd simulation lives in **zmpc01/blender-crowd-kit** (pre-v1, M2);
this kit ships no crowd code. Composition:
```bash
git clone https://github.com/zmpc01/blender-crowd-kit.git <sibling>
# in your scene script, BEFORE importing crowd:
import sys; sys.path.insert(0, "<sibling>")
from scripts.crowd import CrowdProject, Population, bake, apply_to_scene
```
The variant's own `scripts/crowd/` stub was DELETED so the sibling import
cannot be shadowed. Vision workflow for crowds: look.py grids at default
resolutions for layout/density; keyframe contact sheets for gait motion;
manifest/validator for agent counts and ground contact. NOTE: a red flag
box storm on instanced crowd agents usually means validator bbox overlaps
— normal for dense crowds; judge crowds by density/flow, gate individual
actors by id.

## What's NOT in this kit

- No GPU support (all CPU rendering, ≤720p for animation)
- No Blender MCP server (direct bpy is more capable for Python agents)
- No rigged character helpers. **Capsule actors are the previz standard** —
  the v2 rigged attempt failed (~10 sessions of trap-fixing). UAL
  (Quaternius CC0) is the vetted hero-swap path. See `/kb/rigged_characters.md`.
- No geometry nodes helpers; no Grease Pencil.
- No external-VLM or ascii-pack machinery AT ALL — not even as
  escalation. Vision-native agents don't need it; agents that do need
  it belong to upstream blender-agent-kit. (Disagreement between your
  eyes and a gate = automatic programmatic probe; the gates win ties.)

## Shipped scenes (test fixtures — know their baseline)

- `scene_template` — cube+sphere+ground; validator PASS. The copy-and-edit base.
- `scene_interior_room` — furnished living room; **validator baseline FAILS**
  (P0=4/P1=12: window frame embedded in wall, TV/sofa overlaps — fixture
  geometry, not your bug). Gate only YOUR movers (`physics_gate
  verify_movers:[...]`) and scope audits (see Placement headlines).
- `scene_cornell` — Cornell box; render/engine smoke fixture.
- `scene_scenarios`, `scene_physics_usability` —
  physics/gate test fixtures (see tests/).

## When to ask for clarification

If "make a scene" is ambiguous, ask: type? focus? output? specific
objects/colors/style? Building the wrong scene wastes more time than one
batched question round.

## KB entries (linked, niche but valuable)

- `/kb/vision_loop.md` — look.py protocol, annotation rules, readiness scores, measured timings (VARIANT)
- `/kb/placement_and_physics.md` — placement_lib + physics_place deep reference
- `/kb/rigged_characters.md` — why capsule actors, UAL hero-swap path
- `/kb/render_speed.md` — engine benchmarks, AA/cavity tradeoffs
- `/kb/glTF_export.md` — export flags, three.js loader quirks
- `/kb/crowd_fields.md` — influence fields, relax PBD, gait phase engine
- `/kb/prop_carry.md` — generalized prop anchoring & clamped carry
