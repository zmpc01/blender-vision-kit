# USD-RESEARCH-1 — USD surface + USDHook research

Research sub-agent report. Investigates Blender's USDHook API surface and
the feasibility of publishing `previz:entity` customData + `previz:identityColor`
custom attrs on per-object wrapper prims at USD export time. All findings are
backed by live probes against Blender 4.5.13 (the binary shipped in
`tools/blender-4.5.13-linux-x64/`).

## Part 1 — Audit of the kit's current USD surface

### Existing USD code in the kit repo

Greps for `USDHook|usd_export|wm\.usd|pxr|usd_` against the entire
`/home/sync/work/blender-agent-kit/` tree returned **zero** hits in `scripts/`
and only **documentation** references elsewhere:

- `HANDOFF.md:14` — user quote: "we should go with something like USD?"
- `HANDOFF.md:53,57,94-106` — "Consider USD" open design memo (Blender 4.5 USD exporter described as "reasonably mature"; warns that full WebGL USD playback needs a WASM runtime OR USD→glTF conversion at export time).
- `AGENTS.md:297` — mentions `import_model(path, location)` supports `.usd/.usda/.usdc` via `bpy.ops.wm.usd_import(filepath=path)`.
- `scripts/polyhaven.py:270` — implements the **import** side only: `bpy.ops.wm.usd_import(filepath=path)` for `.usd/.usda/.usdc` asset files.

**No `bpy.types.USDHook` subclass is registered anywhere in the kit.** The kit has **no USD export path** at all (the only export is the glTF path via `scripts/blender_kit/__init__.py:454-483` `export_gltf()` + `scripts/export_gltf.py`). The proposed change is therefore pure greenfield: no existing USDHook registration to retrofit, no USD-export flag to thread through, no existing `previz:` namespace to migrate.

### `scene_schema.py` output format — fields produced

`scripts/scene_schema.py:123-202` `export_scene_schema()` produces a dict
with `schema_version: "1.0"` and these top-level keys:

- `blender_version`, `scene_name`, `frame_range`, `fps`, `engine`, `resolution`, `world` (background_color/strength), `active_camera`.

- Per object (id, type, location, world_centroid, rotation_euler_deg, scale, matrix_world, parent, visible, materials) + type-specific:
  - `mesh` (vertex_count, polygon_count, bounds)
  - `light` (type, energy, color, size)
  - `camera` (lens_mm, sensor_width_mm, clip_start, clip_end)
  - `animation` (action_name, curves[{data_path, array_index, keyframes[{frame,value,interpolation,easing}]}])

**Fields the issue lists as missing vs the scene_schema output:** the issue's list — shots, platforms, environment, timeline.tracks, animation presets, interactive prop metadata, anchorTo, bodyType — corresponds to ZERO of the above. `scene_schema.py` is purely a per-object transform/material/camera dump — it has no story-level / shot / director / animation-event data. The story data lives in module-level constants in `scene_escape_v4.py` (Part 5 below), not in `scene_schema.py`'s output.

### `export_gltf.py` + `blender_kit/__init__.py`

`scripts/export_gltf.py` (50 LOC) is a thin CLI wrapper: argparse `--scene`, `--output`, `--frames`, `--start` → `mod.build_scene()` + `mod.animate(ctx, ...)` + `blender_kit.export_gltf(args, out_path=...)`.

`scripts/blender_kit/__init__.py:454-483` defines the `export_gltf(args, *, out_path=None) -> str` helper. It calls `bpy.ops.export_scene.gltf(filepath=..., export_format='GLB', export_cameras=True, export_lights=True, export_animations=True, export_animation_mode='ACTIONS', export_frame_range=True, export_apply=True, export_yup=True, export_materials='EXPORT', export_import_convert_lighting_mode='SPEC', use_selection=False)`.

**There is NO `export_usd()` helper in `blender_kit/__init__.py`.** The USD analogue is what the issue proposes. The natural parity would be:
- a new helper `export_usd(args, *, out_path=None) -> str` in `blender_kit/__init__.py` (alongside `export_gltf`, same return-signature: returns the path written), and
- a new thin CLI wrapper `scripts/export_usd.py` mirroring `scripts/export_gltf.py`'s shape (argparse `--scene`/`--output`/`--frames`/`--start`).

### `apply_patch.py` MUTATIONS dict

`scripts/apply_patch.py:796-833` defines `MUTATIONS` — **36 ops**, all per-Blender-object scene mutations. Categories:

- **Per-object transform/material** (13): set_location, move_to, set_rotation, set_scale, set_material_color, set_material_roughness, set_material_metallic, delete_object, duplicate_object, place_on, seat_at, snap_z, heat_bake.
- **Camera** (3): set_camera_location, set_camera_lens, set_camera_dof.
- **Light** (2): set_light_energy, set_light_color.
- **Scene** (3): set_world_strength, set_exposure, set_frame.
- **Audit/util** (4): render_viewport, audit, seam_views, clear_bvh_cache.
- **Physics** (4): physics_settle, physics_place, physics_oracle, physics_gate.
- **Add primitives** (7): add_cube, add_sphere, add_cylinder, add_cone, add_torus, add_plane, add_empty.

**There is NO `set_story_data`, `set_director_metadata`, `set_shot`, `set_knockdown`, `set_lunge`, `set_muzzle`, `set_dialog`, `set_rb_param`, or any other story-level op.** The patch surface is entirely scene-graph (Blender RNA state); story constants (SHOTS_V3, KNOCKDOWNS_V3, …) are mutated by editing Python source — that's the "STORY_OPS execution model" gap that REVIEW-A flagged in the parallel PSD track (worklog L2308) and that the proposed USD carrier would sidestep: the carrier is read verbatim at USD-import time by the converter, so story data never has to be a patch op at all.

### Existing `bpy.types.USDHook` subclass registrations

None. Grep for `USDHook` across both `blender-agent-kit/scripts/` and `blender-escape-previz/scripts/` returned zero hits. The proposed subclass would be the first.

## Part 2 — Blender USDHook API

Verified against the **shipped** Blender 4.5.13 at `tools/blender-4.5.13-linux-x64/` (binary `daeeeca98fb0 built 2026-08-25`) and the official docs at `https://docs.blender.org/api/current/bpy.types.USDHook.html` (cached at `/home/z/staging/usdhook_docs.html`).

### Class definition

`bpy_types.py:1048-1049` (shipped modules) defines:
```python
class USDHook(_StructRNA, metaclass=_RNAMeta):
    __slots__ = ()
```
Subclass pattern (from the official example):
```python
class PrevizUSDHook(bpy.types.USDHook):
    bl_idname = "previz_usd_hook"        # unique snake id, must not clash
    bl_label = "Previz USD Carrier"       # human label
    bl_description = "Embeds previz:entity customData on wrapper prims"

    @staticmethod
    def on_export(export_context): ...
    @staticmethod
    def on_material_export(export_context, bl_material, usd_material): ...
    @staticmethod
    def on_import(import_context): ...
    @staticmethod
    def material_import_poll(import_context, usd_material): ...
    @staticmethod
    def on_material_import(import_context, bl_material, usd_material): ...
```
Register/unregister with `bpy.utils.register_class(PrevizUSDHook)` / `bpy.utils.unregister_class(PrevizUSDHook)`. The class is **discovered by `bl_idname`** at the moment `bpy.ops.wm.usd_export` is invoked — register before, unregister after.

### `on_export()` signature and behaviour

Docs (verbatim, `bpy.types.USDHook.html`): "Called before the USD export finalizes, allowing modifications to the USD stage immediately before it is saved."

- Arg: `export_context` — an instance of `USDSceneExportContext`.
- Returns: `True` on success, `False` if bypassed/failed.
- Exceptions raised inside the hook are caught by Blender and surface as `RuntimeError: Error: An exception occurred invoking USD hook '<bl_label>'.` on `bpy.ops.wm.usd_export()`. (Confirmed live — see smoke test logs.)
- Timing: the hook runs **after** the native exporter has authored all prims/attributes on the in-memory stage, **before** the stage is saved to disk. Confirmed via the smoke test: `stage.Traverse()` in the hook sees `/root/HeroCube/Cube` (Mesh) and `/root/Camera/Camera` (Camera) already populated.

### `USDSceneExportContext` actual API surface (Blender 4.5.13)

The docs list three methods on `USDSceneExportContext`: `get_stage()`, `get_depsgraph()`, `get_prim_map()`. Live `dir()` on a real instance (smoke test `test2.usd`) returned **only**:

```
[ 'get_depsgraph', 'get_stage' ]
```

**`get_prim_map()` does NOT exist on the shipped Blender 4.5.13.** The docs are ahead of the runtime; either the method was added in 4.6+ or the docs aspirationally describe a feature that didn't make it into 4.5.13. **The orchestrator must NOT plan around `get_prim_map()`** — the hook must map Blender objects to USD prims another way.

The two methods that DO exist:
- `get_stage()` → returns `pxr.Usd.Stage` (the live in-memory stage; mutations persist to the saved file). Confirmed live: `stage.GetDefaultPrim()`, `stage.Traverse()`, `stage.GetPrimAtPath(path)` all work after the native exporter has run.
- `get_depsgraph()` → returns the Blender scene dependency graph (`bpy.types.Depsgraph`). Useful for evaluating the scene at a specific frame before the export samples it; not needed for the basic carrier.

### Mapping Blender objects → USD prims (since `get_prim_map()` is absent)

The smoke test (`/home/z/staging/usd_smoke/round_trip.usda`) shows Blender's USD exporter produces this hierarchy with the default `root_prim_path='/root'`:

```
/root                              (Xform, defaultPrim, customData={dictionary Blender={bool generated=1}})
/root/<blender_obj_name>          (Xform, "wrapper prim" — per Blender object)
/root/<blender_obj_name>/<data_name>  (Mesh|Camera|... — actual geometry/camera data)
```

So the wrapper-prim mapping is simply `stage.GetPrimAtPath("/root/" + obj.name)` for each `obj in bpy.context.scene.objects` (when `root_prim_path` is the default `/root`). The wrapper prim's child mesh/camera prim has its data name as the prim name (e.g., object `HeroCube` with mesh data `Cube` → `/root/HeroCube/Cube`). To be robust to a non-default `root_prim_path`, walk `stage.Traverse()` and match prims by `prim.GetName() == obj.name` + `prim.IsA(UsdGeom.Xformable)`.

`bpy.context.scene.objects` is reachable from inside the hook (bpy is global), so no need for the depgraph just to enumerate objects.

## Part 3 — USD customData vs primvars vs custom attributes

### USD prim customData API (verified live against pxr.Usd 25.02)

`pxr.Usd.Prim` exposes (all confirmed via `hasattr()` + live calls on Blender 4.5.13):
- `SetCustomData(VtDictionary)` — replace the whole customData dict.
- `GetCustomData() -> VtDictionary` — composed (read).
- `SetCustomDataByKey(TfToken keyPath, VtValue value)` — set a single key (key-path with `:` separators nests).
- `GetCustomDataByKey(TfToken keyPath) -> VtValue` — read a single key.
- `ClearCustomData()` and `HasAuthoredCustomData()`.

### Critical value-shape constraints (verified by direct probe)

Probed what shapes are accepted as `SetCustomDataByKey` values:

| Value shape | Result | Notes |
|---|---|---|
| Top-level dict `{"kind":"env","shots":{"0":{...}}}` | **OK** | `customData = {previz={entity={...}}}` (colon nests) |
| Top-level list of scalars `[1,2,3,4]` | **FAIL** | `Invalid value type for customData:...` — top-level value MUST be a dict |
| Top-level list of strings `["a","b","c"]` | **FAIL** | same reason |
| Top-level single string (JSON) | **OK** | workaround: store the whole entity as a JSON-encoded string |
| Nested dict containing list-of-scalars `{"tags":["a","b","c"]}` | **OK** | `Vt.StringArray` / `Vt.IntArray` |
| Nested dict containing list-of-dicts `{"shots":[{"id":"S1"}]}` | **FAIL** | `first vector/list element <VtDictionary> is not a valid scene description datatype` |
| Nested dict emulating list-of-dicts via stringified-int keys `{"shots":{"0":{"id":"S1"},"1":{"id":"S2"}}}` | **OK** | dict-of-dicts with "0"/"1"/... keys |
| `None` as any value | **FAIL** | `Invalid value type for customData:previz:entity: .` — use empty string or skip the key |
| Booleans / floats / ints / strings | **OK** | scalars fine |
| Nested VtDictionary (any depth) | **OK** | as long as no list-of-dicts inside |

### Naming convention: `previz:entity` is a key-path, not a flat key

When you call `prim.SetCustomDataByKey("previz:entity", {...})`, USD treats the `:` as a key-path separator and writes:

```
customData = {
    dictionary previz = {
        dictionary entity = { ... }
    }
}
```

The matching read is `prim.GetCustomDataByKey("previz:entity")` — symmetric.

A literal flat key `"previz:entity"` (single Sdf token, no nesting) is **only** achievable via `prim.SetCustomData({"previz:entity": {...}})` (whole-dict replacement), but then `GetCustomDataByKey("previz:entity")` returns `None` because the key-path interpretation is baked into the by-key API. **Recommendation: use `SetCustomDataByKey("previz:entity", {...})` (nested form) — it's symmetric with the by-key read the converter is most likely using, and matches the docs example's pattern (which uses `customLayerData["blenderFilepath"]` on the root layer, but the same key-path convention applies to prim customData).**

### Layer-level vs prim-level customData

The official `USDHookExample.on_export()` in the docs writes **layer-level** customData:
```python
rootLayer = stage.GetRootLayer()
customData = rootLayer.customLayerData
customData["blenderFilepath"] = data.filepath
rootLayer.customLayerData = customData
```
This attaches metadata to the **stage's root layer**, not to individual prims. The layer-level API is more permissive: `rl.customLayerData["previz:scene"] = "escape_v4"` works as a flat string key (no colon-nesting). Confirmed live.

The issue asks for **per-wrapper-prim** customData ("on each wrapper prim"), so we use `prim.SetCustomDataByKey("previz:entity", ...)` — NOT `rootLayer.customLayerData`. (Layer-level customData could ALSO carry a stage-wide `previz:entity` with schema_version + shot list; prim-level customData would carry per-object entity data — anchorTo, bodyType, interactive-prop metadata. Both can coexist.)

### Custom attributes (for `previz:identityColor`)

Live test:
```python
attr = root.CreateAttribute("previz:identityColor",
                            Sdf.ValueTypeNames.Color3f, custom=True)
attr.Set(Gf.Vec3f(0.85, 0.20, 0.15))
```
Produces in the .usda:
```
def Xform "root" { custom color3f previz:identityColor = (0.85, 0.2, 0.15) }
```
`attr.IsCustom()` returns `True`. The `custom=True` flag is what marks the attribute as non-built-in (i.e., not a USD-schema attribute like `xformOp:translate`). The `previz:` namespace prefix is just USD's standard namespace separator for attribute names — no special handling needed.

Supported Sdf types for color: `Color3f` (RGB, `Gf.Vec3f`), `Color4f` (RGBA, `Gf.Vec4f`), `Float3` (positional, `Gf.Vec3f` — same payload as Color3f but no color-role metadata).

### Native exporter's `export_custom_properties` ≠ customData

`bpy.ops.wm.usd_export` has `export_custom_properties=True` (default) and `custom_properties_namespace='userProperties'` (default). Per the operator docs (`bpy.ops.wm.html` cached at `/home/z/staging/bpy_ops_wm.html`):
- `export_custom_properties` — "Export Custom Properties, Export custom properties to Alembic .userProperties".
- `custom_properties_namespace` — "If set, add the given namespace as a prefix to exported custom property names. This only applies to property names that do not already have a prefix."

Live confirmation: a Blender object with custom prop `previz_color = (0.85,0.2,0.15,1)` exported with defaults produces:
```
custom double4 userProperties:previz_color = (0.85, 0.2, 0.15, 1)
custom string userProperties:previz_tag = "hero"
custom string userProperties:blender:object_name = "HeroCube"   # from author_blender_name=True
```
So the native exporter writes Blender object custom props as **USD custom ATTRIBUTES** (time-sampleable properties, namespaced `userProperties:`), NOT as prim customData. To get a BARE `previz:identityColor` custom attribute (without the `userProperties:` prefix), the USDHook must call `prim.CreateAttribute("previz:identityColor", ...)` directly — the native exporter won't do it for us.

**Conclusion**: prim customData MUST be authored via the USDHook (native exporter has no path to it). Bare-namespaced custom attributes (like `previz:identityColor`) ALSO need the USDHook if the converter expects the bare name rather than `userProperties:previz:identityColor`.

## Part 4 — Attempt to access the webpreviz design doc

Probed (no PAT available for the `laguerita648-pixel` org):

- `https://api.github.com/repos/laguerita648-pixel/webpreviz` → **HTTP 404** (repo is private or doesn't exist with that exact name)
- `https://raw.githubusercontent.com/laguerita648-pixel/webpreviz/main/docs/designs/core-110-usd-vs-glb-spike.md` → **HTTP 404**
- `https://raw.githubusercontent.com/laguerita648-pixel/webpreviz/master/...` → **HTTP 404**
- `https://api.github.com/repos/laguerita648/webpreviz` → HTTP 403 (rate limit)
- `https://api.github.com/repos/webpreviz/webpreviz` → HTTP 404

**§8.3 is not accessible.** Schema is inferred from the issue body + USD conventions (Parts 3 + 5 below). The orchestrator should request explicit §8.3 content from the WebPreviz meta-agent before locking the schema; the research here establishes what USD can carry, not what the converter's exact field expectations are.

## Part 5 — Examine the previz repo for existing story-data structures

`/home/sync/work/blender-escape-previz/scripts/scene_escape_v4.py` (2520 LOC) holds ALL of the candidate "entity data" as module-level constants. The kit-research round (RESEARCH-A, worklog L2276-2320) already inventoried most of these — this section maps them onto the issue's vocabulary (shots / platforms / environment / timeline.tracks / animation presets / interactive prop metadata / anchorTo / bodyType).

| Issue vocabulary | Source constant (file:line) | Structure | Mapping notes |
|---|---|---|---|
| **shots** | `SHOTS_V3` (scene_escape_v4.py:156-178) | 21 tuples `(id:str, f0:int, f1:int, description:str)` | Direct 1:1 — list of shot windows over the 1080-frame timeline. Convert to dict-of-dicts with stringified-int keys for USD customData. |
| **platforms** | `JEEP_X_V3` (L181-193) + `CAMS_V3` (L237-321) | `JEEP_X_V3`: 28 tuples `(t:float, x:float)` (jeep weave path). `CAMS_V3`: 21 tuples `(name, loc0, loc1, lens_mm, aim, parent_jeep:bool, shake_amp)` | "platform" = the jeep (the camera/actor carrier). Cameras with `parent_jeep=True` are jeep-platformed. Per-shot `CAMS_V3[i]` ↔ `SHOTS_V3[i]` by index. |
| **environment** | `MOTION_POLICY` (L136-149) + scene world config (`add_sky_world()` calls in `build_scene`) | `MOTION_POLICY`: dict `intended_static` (list of regex patterns), `intended_subject_tree` ("JeepRoot"), `aim_exempt` (regex). World: Nishita sky params (sun_elevation_deg, sun_rotation_deg, air_density, dust_density, strength). | The "what stays static vs moves" + the lighting/atmosphere. The `kit_atmo` Blender object custom prop (kit `blender_kit/__init__.py:288`) marks atmosphere objects to hide in workbench — same flag could carry into USD as `previz:atmosphere=true`. |
| **timeline.tracks** | `_V3_SEG` (L91-102) + `JEEP_X_V3` (L181) + `DIALOG` (L358-363) + `FLATNESS_POLICY` (L150-152) + `FPS`/`TOTAL_FRAMES_V3`/`T_DRIVE`/`RUN_SPEED`/`RUN_START_Y`/`BARRICADE_T_V3`/`BARRICADE_Y_V3` (L82-126) | `_V3_SEG`: 10 tuples `(t0,t1,v0,v1)` piecewise-linear jeep-speed profile. `DIALOG`: 9 tuples `(line_id:str, onset_frame:int)`. `FLATNESS_POLICY`: dict of deliberate-flat ranges. | All the per-frame timeline anchors. These are scalar tables — list-of-scalars works in USD customData. |
| **animation presets** | `KNOCKDOWNS_V3` (L326-340) + `LUNGE_V3` (L341-345) + `MUZZLE_BURSTS_V3` (L346-354) + `CHASE_FALLS_V3` (L325) + `RB_FALLS=[2,5,8]`/`RB_KD=["KD3"]` (L1368-1369) + `RUN_PARAMS` (L227-232) + `BOARD_UAL_Z` (L216) | `KNOCKDOWNS_V3`: 13 tuples `(id, t_hit, x_off, style:str)`. `LUNGE_V3`: dict of `start_t/grab_t/release_t/end_t/x_start/x_grab/x_end/y_offsets`. `MUZZLE_BURSTS_V3`: 6 tuples `(f0, f1, count)`. | These are the keyframe recipes. Their STYLE strings (`tumble_left`/`big_launch`/`brush_left`/`clip_spark_right`) are the "presets" — the named animation templates. |
| **interactive prop metadata** | `BOARD` (L198-203) + `BOARD_UAL_Z` (L216) | `BOARD`: dict-of-tuples per actor `((f_run_end, f_apex, f_land, (x,y,z), yaw_end, pose_name), (offset,))`. `BOARD_UAL_Z`: dict of seat-z per actor in UAL mode. | Boarding is the interactive prop interaction (actors boarding the jeep). Per-actor boarding recipe. |
| **anchorTo** | `BOARD`'s `(x,y,z)` seat_local + `parent_jeep` flag in `CAMS_V3` | per-actor seat-local offset + per-camera parent flag | "anchor to" = either boarding (actor→jeep seat) or camera parent (camera→jeep). Direct. |
| **bodyType** | `BOARD`'s `pose_name` field (`SitDriver`/`SitPass`/`Aim`) + `obj.type` (Blender RNA: `MESH`/`CAMERA`/`LIGHT`/`EMPTY`/`ARMATURE`) + `HERO_MODE` (`capsule`/`ual`) (L62) | pose_name is a string per actor; obj.type is Blender RNA; HERO_MODE is a global mode selector | "body type" is overloaded — could mean pose (SitDriver/Aim), rig type (capsule vs UAL), or Blender object type. Recommend: emit ALL THREE as separate fields (`pose_name`, `rig_mode`, `blender_type`) under `previz:entity`. |

**Note**: `RB_FALLS`/`RB_KD`/`HERO_MODE` are module globals; per REVIEW-B B-NEW-3 (worklog L2316), `importlib.reload(SC)` resets these — the JSON-canonical refactor (Phase 1 step 1 of the PSD plan) omits them. For the USD carrier path, this is irrelevant: the USDHook reads them at export time directly from the live module instance, so they're captured verbatim regardless of importlib state.

## Part 6 — Recommended implementation approach

### 6.1 Where the USD export code should live

**Two new files**, mirroring the glTF parity:

1. **`scripts/export_usd.py`** (thin CLI, ~50 LOC) — sibling to `scripts/export_gltf.py`. argparse `--scene`/`--output`/`--frames`/`--start` → import scene module → `mod.build_scene()` + `mod.animate(ctx, ...)` → `blender_kit.export_usd(args, out_path=args.output)`.

2. **`scripts/previz_usd_hook.py`** (~150-200 LOC) — the `bpy.types.USDHook` subclass + a `register()`/`unregister()` pair + the entity-data builder. Imported by `export_usd.py` and registered around the `bpy.ops.wm.usd_export()` call. (Keeping the hook in its own module lets future callers — `apply_patch.py` `export_usd` op, `agent_server.py` USD endpoint — register it transiently without re-importing the entire CLI.)

3. **`scripts/blender_kit/__init__.py`** — add a new `export_usd(args, *, out_path=None) -> str` helper alongside `export_gltf` (~30 LOC). It registers `previz_usd_hook.PrevizUSDHook` (idempotent if already registered), calls `bpy.ops.wm.usd_export(filepath=..., export_animation=True, export_cameras=True, export_lights=True, export_armatures=True, evaluation_mode='RENDER', author_blender_name=True, root_prim_path='/root', export_custom_properties=True, custom_properties_namespace='userProperties')`, then unregisters the hook. Returns the path written (matching `export_gltf`'s return contract).

The `export_custom_properties=True` default stays ON — it writes any Blender object custom props the user set as `userProperties:*` USD custom attributes (a parallel sidechannel), which the converter can optionally read. The hook ADDITIONALLY writes `previz:entity` customData + bare `previz:identityColor` attr.

### 6.2 USDHook subclass structure

```python
# scripts/previz_usd_hook.py
import bpy

class PrevizUSDHook(bpy.types.USDHook):
    bl_idname = "previz_usd_hook"
    bl_label = "Previz USD Carrier"
    bl_description = "Embeds previz:entity customData + previz:identityColor attr on wrapper prims"

    @staticmethod
    def on_export(export_context):
        # Lazy import pxr (only available inside Blender with expose_bundled_modules)
        bpy.utils.expose_bundled_modules()
        import pxr.Usd as Usd
        import pxr.Sdf as Sdf
        import pxr.Gf as Gf

        stage = export_context.get_stage()
        if stage is None:
            return False
        root = stage.GetDefaultPrim()
        if not root or not root.IsValid():
            return False

        # 1. Stage-wide previz:entity on /root (story-level data)
        story = _build_stage_entity_payload()
        root.SetCustomDataByKey("previz:entity", story)

        # 2. Per-wrapper-prim previz:entity (per-object data)
        #    Walk bpy scene objects; map to USD prim by /<root_prim>/<obj.name>
        root_path = stage.GetDefaultPrim().GetPath().pathString  # "/root"
        for obj in bpy.context.scene.objects:
            wrapper = stage.GetPrimAtPath(root_path + "/" + obj.name)
            if not wrapper or not wrapper.IsValid():
                continue
            wrapper.SetCustomDataByKey("previz:entity",
                                       _build_object_entity_payload(obj))

        # 3. previz:identityColor custom attr (per-wrapper-prim, bare namespace)
        for obj in bpy.context.scene.objects:
            wrapper = stage.GetPrimAtPath(root_path + "/" + obj.name)
            if not wrapper or not wrapper.IsValid():
                continue
            color = _resolve_identity_color(obj)  # Gf.Vec3f or None
            if color is not None:
                attr = wrapper.CreateAttribute(
                    "previz:identityColor",
                    Sdf.ValueTypeNames.Color3f, custom=True)
                attr.Set(color)
        return True


def register():
    if not hasattr(bpy.types, "PREVIZ_USD_HOOK_REGISTERED"):
        bpy.utils.register_class(PrevizUSDHook)
        bpy.types.PREVIZ_USD_HOOK_REGISTERED = True


def unregister():
    if hasattr(bpy.types, "PREVIZ_USD_HOOK_REGISTERED"):
        bpy.utils.unregister_class(PrevizUSDHook)
        del bpy.types.PREVIZ_USD_HOOK_REGISTERED
```

`_build_stage_entity_payload()` and `_build_object_entity_payload(obj)` are pure-Python builders (see §6.4 schema). `_resolve_identity_color(obj)` reads the object's viewport display color (`obj.color` RGBA → drop alpha → `Gf.Vec3f`) or a `previz_identity_color` custom prop if set.

### 6.3 Data flow — Option C (hybrid) recommended

The issue presents three options:

- **Option A**: hook reads `scene_schema.py` output (JSON). Pros: schema is already JSON-serializable; the hook is dumb. Cons: `scene_schema.py` doesn't currently emit any of the story data (Part 1) — it only emits per-object transforms/materials/cameras. Would need to extend `scene_schema.py` to emit story constants. Also requires the JSON file to exist on disk at hook fire time (intermediate write).
- **Option B**: hook builds the data inline from `bpy` objects + module-level constants. Pros: no intermediate file; hook is self-contained; captures the live bpy state (latest mutations applied). Cons: the hook needs to import the scene module (`scene_escape_v4`) to read its constants — fragile if the module wasn't loaded by the caller (e.g., when USD-exporting a `.blend` saved from a different scene).
- **Option C (recommended, hybrid)**: hook reads story constants from the scene module IF importable, falls back to layer-level customData-only payload if not; per-object entity data always built inline from `bpy.context.scene.objects` (always available). Stage-level payload uses a small `_collect_story()` helper that tries `importlib.import_module(scene_module_name)` and pulls `SHOTS_V3`, `CAMS_V3`, etc. as plain-Python data, with try/except per constant (skip if missing).

Rationale: Option C makes the hook robust to "export a saved .blend without rebuilding the scene" (the `scene_schema.py --load-blend` parity case) — the per-object carrier still works, even if the story constants are unavailable. The orchestrator should pass the scene module name via a module-level variable on the hook class (`PrevizUSDHook.scene_module_name = "scene_escape_v4"`) set by `export_usd.py` before registering.

### 6.4 `previz:entity` customData schema

Stage-level (on `/root`):
```python
{
    "schema_version": "1.0",      # bump when fields change
    "kind": "environment",
    "shots": {                    # dict-of-dicts (USD forbids list-of-dicts)
        "0": {"id": "S1a", "f0": 1,   "f1": 48,  "intent": "aerial establish"},
        "1": {"id": "S1b", "f0": 49,  "f1": 88,  "intent": "street-level obverse"},
        # ...21 shots total
    },
    "timeline": {
        "fps": 24,
        "total_frames": 1080,
        "t_drive": 9.55,
        "speed_profile": {        # _V3_SEG emulated as dict-of-dicts
            "0": {"t0":0.0, "t1":9.55, "v0":0.0, "v1":0.0},
            # ...
        },
        "barricade_t": 31.4,
        "barricade_y": 218.5,
    },
    "environment": {
        "intended_static": ["Street.Skyline\\d+.*", "Street.GroundStatic", ...],
        "intended_subject_tree": "JeepRoot",
        "world": {"sun_elevation_deg": 25.0, "sun_rotation_deg": 45.0, ...},
    },
    "platforms": {                # the jeep weave path
        "0": {"t":0.0,  "x":0.0},
        # ... JEEP_X_V3 entries
    },
    "animation_presets": {
        "knockdowns": {"0": {"id":"KD1","t":11.0,"x_off":-0.6,"style":"tumble_left"}, ...},
        "lunge": {"start_t":20.7, "grab_t":21.3, "release_t":22.5, "end_t":23.0, ...},
        "muzzle_bursts": {"0": {"f0":352, "f1":380, "count":7}, ...},
        "chase_falls": {"2":14.5, "5":15.3, "8":16.1},  # dict-of-floats
        "rb_falls": [2, 5, 8],   # list-of-ints OK
        "rb_kd": ["KD3"],         # list-of-strings OK
    },
    "dialog": {                   # DIALOG table
        "0": {"id":"line01_go", "onset_frame":14},
        # ...9 entries
    },
    "flatness_policy": {           # FLATNESS_POLICY
        "S12b": {"f0": 961, "f1": 1080},
    },
    "blender_version": bpy.app.version_string,
    "scene_name": bpy.context.scene.name,
}
```

Per-object wrapper prim (on `/root/<obj.name>`):
```python
{
    "blender_name": obj.name,
    "blender_type": obj.type,                  # MESH/CAMERA/LIGHT/EMPTY/ARMATURE
    "anchor_to": obj.parent.name if obj.parent else "",   # NEVER None (USD rejects None)
    "body_type": "mesh" if obj.type == "MESH" else obj.type.lower(),
    "pose_name": <from BOARD[actor][0][5] if obj.name in BOARD>,  # SitDriver/SitPass/Aim
    "rig_mode": <HERO_MODE module global if available>,  # "capsule"/"ual"
    "identity_color_rgba": [r,g,b,a],          # from obj.color (Blender viewport display color)
    "kit_atmo": bool(obj.get("kit_atmo", False)),
    "is_camera": obj.type == "CAMERA",
    "camera_lens_mm": <obj.data.lens if CAMERA>,
    "is_light": obj.type == "LIGHT",
    "light_energy": <obj.data.energy if LIGHT>,
}
```

### 6.5 `previz:identityColor` custom attribute schema

```python
attr = wrapper.CreateAttribute("previz:identityColor",
                               Sdf.ValueTypeNames.Color3f, custom=True)
attr.Set(Gf.Vec3f(r, g, b))    # linear; values typically in [0,1]
```

- **USD type**: `Color3f` (matches USD's color role metadata; consumer-side `attr.Get()` returns a `Gf.Vec3f`).
- **Value source**: the Blender object's viewport display color `obj.color` (RGBA, linear), drop alpha → `Gf.Vec3f(obj.color[0], obj.color[1], obj.color[2])`. This is the same color that `make_material()` sets on `mat.diffuse_color` (kit `blender_kit/__init__.py:170`) — i.e., the authored base color that workbench reads. For multi-material mesh objects, use the first material's diffuse_color; for lights, use `obj.data.color`; for cameras/empties, omit the attr.
- **Custom flag**: `custom=True` so USD treats it as a non-schema attribute (not `xformOp:` or `primvars:`).
- **Variability**: default (no `SetVariability` call) → uniform/time-sampleable as needed. For a per-object constant color, calling `attr.SetVariability(Sdf.VariabilityUniform)` is optional but recommended to make the intent explicit.

### 6.6 How to test (round-trip)

Already proven in smoke test (`/home/z/staging/usd_smoke/round_trip.usda`):

1. **Export**: register `PrevizUSDHook`, run `bpy.ops.wm.usd_export(filepath=..., export_animation=False)`. Hook fires after native authoring, before save.
2. **Re-import + verify**: open the .usda with `pxr.Usd.Stage.Open(path)` (no Blender needed — pure pxr). For each `prim` in `stage.Traverse()`:
   - `prim.GetCustomDataByKey("previz:entity")` should return a dict matching what we set (with `Vt.StringArray` instead of Python lists for the `tags` field — convert with `list(arr)`).
   - `prim.GetAttribute("previz:identityColor").Get()` should return `Gf.Vec3f(r,g,b)`.
3. **Assert**: stage root's `previz:entity.schema_version == "1.0"`; shot count == `len(SHOTS_V3)` (21 for v4); at least one wrapper prim has `previz:identityColor` close to its Blender object's `obj.color`.

A minimal in-tree test (`tests/test_usd_carrier.py`, ~80 LOC) could run via `blrun.sh --background --python tests/test_usd_carrier.py` and assert:
- `bpy.ops.wm.usd_export` does not raise when the hook is registered.
- The output .usda contains `dictionary previz = { dictionary entity =` (text-grep) — proves the customData block is written.
- Re-import with `pxr.Usd.Stage.Open` and read `root.GetCustomDataByKey("previz:entity")` — assert `"schema_version" in result`.
- Walk prims; assert at least one non-root prim has `previz:entity.blender_name` matching a `bpy.context.scene.objects` name.

### 6.7 Known gotchas (must be in the design doc)

1. **`USDSceneExportContext.get_prim_map()` is absent on Blender 4.5.13.** Don't plan around it. Map Blender objects to USD prims by name via `stage.GetPrimAtPath(<root_path> + "/" + obj.name)`.
2. **USD customData forbids list-of-dicts.** Lists of scalars (ints, strings, floats) are fine; list-of-dicts must be emulated as dict-of-dicts with stringified-int keys (`{"0": {...}, "1": {...}}`). The webpreviz converter must convert back.
3. **`None` is not a valid customData value.** Use empty string `""` or omit the key.
4. **Top-level customData value must be a dict.** `prim.SetCustomDataByKey("previz:entity", [...])` fails — must wrap in a dict.
5. **The `previz:entity` key is interpreted by `SetCustomDataByKey` as a key-path** (colon = path separator) — produces nested `customData["previz"]["entity"]`. Symmetric with `GetCustomDataByKey("previz:entity")`. If the converter expects a flat single-token literal key, use `prim.SetCustomData({"previz:entity": {...}})` (whole-dict replacement) and have the converter read `prim.GetCustomData()["previz:entity"]` instead. **Confirm the converter's expectation before locking the API** — the §8.3 design doc would resolve this (Part 4 found it inaccessible).
6. **The native exporter writes Blender object custom properties as USD custom attributes (not customData) under `userProperties:` namespace** (default `export_custom_properties=True`, `custom_properties_namespace='userProperties'`). If the converter also reads `userProperties:previz:*`, that path is FREE (no hook needed for those). The hook is required only for: (a) prim customData (`previz:entity`), (b) bare-namespaced custom attrs (`previz:identityColor` without the `userProperties:` prefix).
7. **Hook registration must happen before `bpy.ops.wm.usd_export` is called.** It's discovered by `bl_idname` at operator-call time. Unregister after to avoid leaking into the next export.
8. **Exceptions inside `on_export` are caught by Blender and surface as `RuntimeError` on `bpy.ops.wm.usd_export`** — the export is aborted, no file is written. The hook must be defensive: `try/except` around each prim, log + continue, never raise.
9. **USDC binary vs USDA text**: file extension determines format (`.usd` → USDC binary; `.usda` → ASCII text; `.usdz` → packaged archive). The webpreviz converter reads via `pxr.Usd.Stage.Open` which handles all three transparently. No format-preference implication for the carrier.
10. **`bpy.utils.expose_bundled_modules()` must be called inside the hook before `import pxr.*`** — otherwise `pxr` is not on sys.path. (This is in the official example.)

### 6.8 Out-of-scope for this research (orchestrator decides)

- Exact field names + types for the `previz:entity` payload (the §8.3 design doc would lock this).
- Whether to ALSO publish layer-level `stage.GetRootLayer().customLayerData["previz:scene"]` for stage-wide metadata (no per-prim overhead) vs prim-level customData for everything.
- Whether to add an `export_usd` op to `apply_patch.py`'s `MUTATIONS` dict (Part 1 lists 36 ops; an `export_usd` op would be op #37, taking `out_path` + optional `scene_module` params — but it's a NON-mutating op like `render_viewport`).
- Whether to add a `POST /api/usd` endpoint to `agent_server.py` (mirroring `/api/scene.glb` GET) for the web viewer to fetch the USD.
- The webpreviz converter's exact read convention (nested-by-key vs flat single-token) — confirm with WebPreviz meta-agent.
