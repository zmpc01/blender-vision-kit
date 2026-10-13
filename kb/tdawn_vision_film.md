# kb/tdawn_vision_film.md — the from-scratch film build with the
# vision kit + crowd kit (session 12, TERMINAL DAWN / tdawn_1)

The full recipe for building a previz FILM (not a fixture scene) with
this kit, exporting through the agent-kit exporter in kit crowd mode,
and staging it to previz-review. The friction findings live in
docs/USABILITY_TD1_vision_film.md; the design decisions in
docs/DESIGN_terminal_dawn.md. This file is the HOW.

## The repo constellation (who provides what)

- THIS kit: the scene module + contract + bake driver + stills/strip
  tools (the film's home; `--scene-dir` points here).
- blender-escape-previz (PATH-LOADED, read-only): `scripts/crowd_kit/`
  (the `kit`-mode plugin: ENGINE record, loader, gates, clips) +
  `scripts/crowd_v6/` (shared sim loader, cache naming, gates) +
  `scripts/crowd_agents.py` (the FROZEN shape-key bases bake2 uses).
- blender-crowd-kit: `scripts/crowd/previz_bridge.py` (the bake chain)
  + `scripts/previz_kit_export_wrapper.py` (the binding-law wrapper).
- blender-agent-kit: `scripts/export_previz_package.py` (the
  canonical exporter; KIT_EXPORTER env points here).
- previz-review: `public/packages/<id>/` + `scripts/s29_rebuild_
  filmstrips.py`.

## The build order that worked (vision-first, D-TD7)

1. contract module (duck-typed, bridge-shaped; uppercase ONLY there)
2. world/actor modules (self-contained bpy; no blender_kit imports)
3. scene module: build_scene (world+anchors+heroes+cams+markers) →
   look.py EARLY (before any crowd) — framing errors are cheapest here
4. bake driver (venv, no Blender): ingest_contract → dataclasses
   .replace the speed plan → bake_previz → to_previz_cache WITH THE
   CONTRACT'S KEEPOUTS → to_previz_ctx(digest) → cache_ctx.json
5. look at the flow: top-down ortho strip (marker-safe pattern!) at
   f1/200/400/700/1000 → retime hero paths against the REAL stream
6. shot-cam stills at representative frames (workbench, 480x270) →
   reframe cameras (expect 2-3 rounds)
6b. PREFLIGHT before ANY export: `./scripts/blrun.sh --background
   --python scripts/export_preflight.py -- --module
   scripts/scene_<film>.py` — replays the exporter's REAL consumption
   (contract shapes, sfx keys, fps pins, marker bindings) and exits 3
   with attributed messages (constant, row index, expected vs got, fix
   hint). The tferry session's three landmines would all have been
   caught pre-bake. `--skip-build` = static phase only.
7. EEVEE lighting pass (32 samples 640x360) → emission/exposure laws
8. stills (one EEVEE process per shot!) → export → filmstrips → stage

## The export command (verbatim, the binding law)

```bash
cd <vision-kit>                       # CWD = provenance
export CROWD_CACHE_DIR=/tmp/crowdcache_tdawn RB_CACHE_DIR=/tmp/rbcache
export KIT_EXPORTER=<agent-kit>/scripts/export_previz_package.py
export BLENDER_BIN=<vision-kit>/tools/blender/blender   # crowd-kit blrun has no own Blender
bash <crowd-kit>/scripts/blrun.sh --background --factory-startup \
  --python <crowd-kit>/scripts/previz_kit_export_wrapper.py -- \
  --scene scene_terminal_dawn --scene-dir <vision-kit>/scripts \
  --crowd-mode kit --crowd-plugin <escape-previz>/scripts/crowd_kit \
  --output output/tdawn/pkg --package-id tdawn_1 --name "..."
```
The wrapper anchors the PREVIZ superset blender_kit (print confirms);
hero_gates 18-21 skip (loud, non-blocking); gate 24 needs the scene's
view_layer synced (see F-TD5).

## The scene-module export-contract checklist (all load-bearing)

- SHOTS_V3 rows (id, f0, f1, intent); CAMS_V3 rows are 7-TUPLES
  (name, loc0, loc1, lens, aim, parent_jeep, shake_amp)
- a timeline MARKER per shot at f0, camera-bound (marker_camera
  pattern) — the exporter hard-fails without them
- CAST entries with explicit root ("Master.Root") + materials named
  CA.Body.<name> (the identity-color registry reads that prefix)
- UPPERCASE names in the SCENE module = mapped vocabulary ONLY
  (SHOTS_V3/CAMS_V3/CAST/BEATS/SYNOPSIS/CROWD_TIER_PINS) — the
  unmapped-constant gate fail-closes on everything else (F-TD7: it is
  a GOOD gate; internal wiring goes lowercase)
- every camera needs an Aim.<CAM> empty (gate 2); TRACK_TO aims
- animate(ctx, start_frame=1, n_frames=None) signature (look.py calls
  it with kwargs); auto-detect the crowd cache so PRE-BAKE looks work
- build_scene MUST end with bpy.context.view_layer.update() (F-TD5:
  the exporter's #29 sweep reads a stale view-layer list otherwise and
  gate 24 rejects the package — measured on Runner.Root)
- emit_sfx_events(ctx, out_dir) writes {"fps","meta","events":[...]}

## The crowd bridge contract (what is hard-pinned)

12 Hz sim / N_TICKS 541 / FPS 24 / TOTAL_FRAMES 1080 (all fail-closed);
N_RELEASE 129 pinned by the loader's honesty assert (the anchor
arithmetic: 120 Zed.NNNN + 12 chase, 9 non-RB); the crowd PURSUES
hero_pos (0,0) capacity ±5 m; flee_target = (0, y_hi_all); zones are
(y_lo, y_hi, count, min_abs_x, jitter) rows, far-band-FIRST (the chase
tail spawns in zones[0]'s strips); optional BARRICADES (x,y,r) become
Blocked squares — DECLARE columns/carts or agents walk through them.
Speed plan: populations are FROZEN dataclasses → dataclasses.replace
distributions.post-ingest; (mu, sigma) only; max_speed envelope =
populations[0] mu+3sigma (keep chase mu+3sigma <= it); the 1.8 m/s
band flips walk/sprint clips (mu 1.75/0.75 ≈ 47% sprint — a crowd
texture, not a uniform gait).

## The AgX emission laws (5.x EEVEE, measured)

- Principled Emission COLOR defaults to WHITE: any glow material with
  strength > 0 adds pure white and clips paper-white under AgX. Pin
  Emission Color = base rgb (make_material does this now).
- AgX desaturates hot emission to TAN before clipping: warm glow keys
  must stay <= ~0.95 strength (0.93 read cream, 1.35 read brown slab).
- interior + sky strength 1.0 blows out: 0.35-0.5 + exposure -0.5.

## The render-pass patterns (marker-bound animated scenes)

- ANY custom render pass must suppress marker cameras
  (`m.camera = None` each) AND RE-ASSERT scene.camera after the sweep
  (clearing markers MUTATES scene.camera — observed fallback to the
  last shot cam) AND restore in finally. See tdawn_flowstrip.py.
- Stills: one EEVEE process per shot (the OOM law as a script:
  tdawn_stills.sh). Filmstrips: one workbench process for all shots,
  8 frames each, {sid}_{k:02d}.jpg, f(k) = f0 + round(k*(span-1)/7);
  rebuild the manifest with previz-review's s29_rebuild_filmstrips.py.
- Readiness: check luma/clipped/dark on every still (look.py prints
  them; image_metrics.py for standalone renders).

## Staging (the last mile)

cp the pkg into previz-review/public/packages/<id>/, run
s29_rebuild_filmstrips.py <dir>/filmstrips <dir>/previz.json, commit +
push the app repo; ALSO copy into /home/z/my-project/public/packages/
and commit there (the served checkout). The app lists newest-first.
Comments API needs `bunx prisma db push` + a dev-server restart
(the 500-on-fresh-clone class).
