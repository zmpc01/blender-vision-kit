# DESIGN_previz_usd_carrier.md — previz:entity USD carrier for issue #1

> **Status**: v1, ready for implementation.
> **Grounds**: `docs/USD-RESEARCH-1_report.md` (smoke test PROVEN).
> **Issue**: github.com/zmpc01/blender-agent-kit/issues/1

## 1. Goal (per issue #1)

When the kit exports USD, embed `previz:entity` customData on each
wrapper prim + `previz:identityColor` custom attr. This makes
Blender→WebPreviz lossless: the converter reads `previz:entity` verbatim
and rebuilds scene.json without dropping director metadata (shots,
platforms, environment, timeline.tracks, animation presets, interactive
prop metadata, anchorTo, bodyType, etc.).

## 2. Implementation (per research §6)

### 2.1 New files

1. **`scripts/previz_usd_hook.py`** (~200 LOC) — `bpy.types.USDHook`
   subclass `PrevizUSDHook`:
   - `bl_idname = "previz_usd_hook"`, `bl_label = "Previz USD Carrier"`.
   - `@staticmethod on_export(export_context)` returns `True` on success.
   - Inside `on_export`:
     1. `bpy.utils.expose_bundled_modules()` (required before `import pxr`).
     2. `from pxr import Usd, Sdf, Gf`.
     3. `stage = export_context.get_depsgraph().scene` for the bpy scene.
        Actually: `stage = export_context.get_stage()` (the USD stage).
     4. Build stage-level payload on `stage.GetPrimAtPath("/root")` via
        `prim.SetCustomDataByKey("previz:entity", _build_stage_payload())`.
     5. For each `obj in bpy.context.scene.objects`: get
        `wrapper = stage.GetPrimAtPath("/root/" + obj.name)`; if valid,
        `wrapper.SetCustomDataByKey("previz:entity",
        _build_object_payload(obj))`.
     6. For each obj: `wrapper.CreateAttribute("previz:identityColor",
        Sdf.ValueTypeNames.Color3f, custom=True).Set(Gf.Vec3f(r,g,b))`
        if obj has a color (mesh with first material.diffuse_color, light,
        or obj.color); skip cameras/empties without color.
   - Module-level functions:
     - `_build_stage_payload(scene_module_name: str | None) -> dict` —
       reads story constants from the scene module IF importable; falls
       back to layer-level-only payload if not (Option C).
     - `_build_object_payload(obj) -> dict` — per-wrapper-prim data.
     - `_resolve_identity_color(obj) -> tuple[float, float, float] | None`.
     - `_collect_story(module_name) -> dict | None` — try/except per
       constant (SHOTS_V3, BOARD, _V3_SEG, KNOCKDOWNS_V3, LUNGE_V3,
       MUZZLE_BURSTS_V3, DIALOG, CAMS_V3, JEEP_X_V3, HERO_MODE,
       RB_FALLS, RB_KD).
     - `_list_to_dict_of_dicts(lst)` — convert list-of-dicts to
       `{"0": {...}, "1": {...}}` (USD forbids list-of-dicts).
   - `register(scene_module_name: str | None = None)` /
     `unregister()` — set `PrevizUSDHook.scene_module_name` before
     registering.

2. **`scripts/export_usd.py`** (~60 LOC, mirrors `export_gltf.py`):
   - CLI: `--scene <module> --output <path> [--frames N --start F
     --hero-rig ual|capsule]`.
   - Imports scene module, calls `build_scene()` + `animate()`.
   - Calls `previz_usd_hook.register(scene_module_name=args.scene)`.
   - Calls `bpy.ops.wm.usd_export(filepath=args.output,
     export_animation=False, export_cameras=True, export_lights=True,
     export_materials=True)`.
   - Calls `previz_usd_hook.unregister()` in a `finally` block.

3. **`scripts/blender_kit/__init__.py`** — add `export_usd(args, *,
   out_path: str | None = None, scene_module: str | None = None) -> str`
   helper alongside `export_gltf()`:
   - Imports `previz_usd_hook` lazily (so non-USD kit users don't pay
     the pxr import cost).
   - Registers hook, calls `bpy.ops.wm.usd_export`, unregisters in
     `finally`.
   - Returns the output path.

### 2.2 Stage-level `previz:entity` schema (on `/root`)

```python
{
    "schema_version": "1.0",
    "kind": "environment",
    "blender_version": bpy.app.version_string,
    "scene_name": bpy.context.scene.name,
    "shots": {  # dict-of-dicts (USD forbids list-of-dicts)
        "0": {"id": "S1a", "f0": 1, "f1": 48, "intent": "aerial establish"},
        # ...one entry per SHOTS_V3 element
    },
    "timeline": {
        "fps": scene.render.fps,
        "total_frames": scene.frame_end - scene.frame_start + 1,
        "frame_range": [scene.frame_start, scene.frame_end],
        "t_drive": 9.55,  # if available
        "speed_profile": {  # _V3_SEG emulated as dict-of-dicts
            "0": {"t0": 0.0, "t1": 9.55, "v0": 0.0, "v1": 0.0},
            # ...
        },
        "barricade_t": 31.4,  # if available
        "barricade_y": 218.5,  # if available
    },
    "environment": {
        "intended_static": [...],  # list-of-strings OK
        "intended_subject_tree": "JeepRoot",  # if available
        "world": {...},  # if scene.world exists
    },
    "platforms": {  # JEEP_X_V3 as dict-of-dicts
        "0": {"t": 0.0, "x": 0.0},
        # ...
    },
    "animation_presets": {
        "knockdowns": {"0": {"id": "KD1", "t_hit": 11.0, "x_off": -0.6, "style": "tumble_left"}, ...},
        "lunge": {"start_t": 20.7, "grab_t": 21.3, "release_t": 22.5, "end_t": 23.0, ...},
        "muzzle_bursts": {"0": {"f0": 352, "f1": 380, "every_n": 7}, ...},
        "rb_falls": [2, 5, 8],     # list-of-ints OK
        "rb_kd": ["KD3"],          # list-of-strings OK
    },
    "dialog": {  # DIALOG as dict-of-dicts
        "0": {"clip": "line01_go", "onset_frame": 14},
        # ...
    },
    "flatness_policy": {  # FLATNESS_POLICY
        "S12b": {"f0": 961, "f1": 1080},
    },
}
```

### 2.3 Per-wrapper-prim `previz:entity` schema (on `/root/<obj.name>`)

```python
{
    "blender_name": obj.name,
    "blender_type": obj.type,             # MESH/CAMERA/LIGHT/EMPTY/ARMATURE
    "anchor_to": obj.parent.name if obj.parent else "",  # NEVER None
    "body_type": "mesh" if obj.type == "MESH" else obj.type.lower(),
    "pose_name": <from BOARD[actor][0][5] if obj.name in BOARD>,  # "" if not
    "rig_mode": <HERO_MODE module global if available>,  # "" if not
    "identity_color_rgba": [r, g, b, a],  # from obj.color RGBA
    "kit_atmo": bool(obj.get("kit_atmo", False)),
    "is_camera": obj.type == "CAMERA",    # bool
    "camera_lens_mm": <obj.data.lens if CAMERA else 0.0>,
    "is_light": obj.type == "LIGHT",     # bool
    "light_energy": <obj.data.energy if LIGHT else 0.0>,
}
```

### 2.4 `previz:identityColor` custom attribute

```python
attr = wrapper.CreateAttribute("previz:identityColor",
                               Sdf.ValueTypeNames.Color3f, custom=True)
attr.Set(Gf.Vec3f(r, g, b))  # linear, [0,1]
```

Value source priority:
1. `obj["previz_identity_color"]` (custom prop, if set) — lets agents
   override per-object.
2. First material's `diffuse_color` (RGB, drop alpha) for meshes.
3. `obj.data.color` for lights.
4. `obj.color` (viewport display color) for other types.
5. Skip the attr if no color source.

## 3. Gotchas (per research §6.7)

1. `USDSceneExportContext.get_prim_map()` is absent on Blender 4.5.13 —
   match prims by name via `stage.GetPrimAtPath("/root/" + obj.name)`.
2. USD customData forbids list-of-dicts — use `{"0": {...}, "1": {...}}`
   dict-of-dicts with stringified-int keys. The webpreviz converter
   must convert back on read.
3. `None` is not a valid customData value — use `""` or omit the key.
4. Top-level customData value must be a dict.
5. `previz:entity` key-path convention: `SetCustomDataByKey("previz:entity",
   dict)` nests as `customData["previz"]["entity"]` (colon = key-path
   separator). Symmetric with `GetCustomDataByKey("previz:entity")`. **This
   is the chosen convention**; will confirm with WebPreviz meta-agent
   after implementation.
6. Hook fires AFTER native exporter authors all prims, BEFORE stage save.
7. Hook registration MUST happen before `bpy.ops.wm.usd_export`. Unregister
   in `finally` after.
8. Exceptions inside `on_export` abort the export — must be defensive:
   `try/except` per prim, log + continue, never raise.
9. `bpy.utils.expose_bundled_modules()` must be called inside `on_export`
   before `import pxr.*`.

## 4. Test plan (per research §6.6)

`tests/test_usd_carrier.py` (~120 LOC):
1. Build a minimal scene: 1 cube + 1 camera + 1 light + 1 empty.
2. Register `PrevizUSDHook`.
3. `bpy.ops.wm.usd_export(filepath=tmp_path, export_animation=False,
   export_cameras=True, export_lights=True)`.
4. Unregister hook.
5. Open the .usda via `pxr.Usd.Stage.Open(path)`.
6. Assert: stage root's `previz:entity` has `schema_version == "1.0"`.
7. Assert: each wrapper prim has `previz:entity.blender_name` matching
   the corresponding bpy object's name.
8. Assert: at least one wrapper prim has `previz:identityColor` close
   to the object's color.
9. Assert: the .usda text contains `dictionary previz = { dictionary entity`.

Run via: `bash scripts/blrun.sh --background --python tests/test_usd_carrier.py`.

## 5. Out-of-scope (open questions for WebPreviz meta-agent)

- Exact field names + types for `previz:entity` payload — the §8.3 design
  doc on webpreviz repo (private) would lock this. Current schema is
  inferred from the issue body + USD conventions.
- Whether to also publish `stage.GetRootLayer().customLayerData["previz:scene"]`
  for stage-wide metadata.
- Whether to add an `export_usd` op to `apply_patch.py` MUTATIONS.
- Whether to add a `POST /api/usd` endpoint to `agent_server.py`.

These can be addressed in follow-up commits after the initial carrier
is working.

## 6. Open convention to confirm with WebPreviz meta-agent

The research flagged that the `previz:entity` key-path convention is
ambiguous without §8.3 of `core-110-usd-vs-glb-spike.md`. The chosen
convention (nested via `SetCustomDataByKey("previz:entity", dict)`)
matches the standard USD colon-as-path-separator convention. If the
webpreviz converter expects a flat literal key, swap to
`prim.SetCustomData({"previz:entity": {...}})` (whole-dict replacement).

After implementation lands, comment on issue #1 to ask WebPreviz meta-agent
to confirm the convention.
