# glTF Export Reference

## Export flags (always set via `blender_kit.export_gltf`)

```python
bpy.ops.export_scene.gltf(
    filepath=out, export_format='GLB',
    export_cameras=True,          # default False — MUST set
    export_lights=True,           # default False — MUST set
    export_animations=True,
    export_animation_mode='ACTIONS',
    export_apply=True,            # bake modifiers
    export_yup=True,
    export_materials='EXPORT',
    export_import_convert_lighting_mode='SPEC',
    use_selection=False,
)
```

## What glTF preserves
- Meshes, PBR materials (Principled BSDF only), cameras, punctual lights
  (SUN/POINT/SPOT), keyframe transform animation.

## What glTF loses
- AREA lights (WARNING: Unsupported light source AREA — accept for web
  preview; `<model-viewer>`'s `environment-image="legacy"` adds ambient)
- Modifiers (baked via `export_apply=True`)
- Procedural/node-graph shaders beyond Principled BSDF
- Collections, view layers, compositing nodes
- Ray-visibility (`hide_render`/`visible_camera=False` — kit excludes
  via `render_hidden_objects()`; export gate 9 fail-closes leaks)

## three.js loader quirks

- **Node name sanitization**: `PropertyBinding.sanitizeNodeName` removes
  `.[]:/ ` — `Aim.CAM_S6b` loads as `AimCAM_S6b`. Compare dot-free for
  node lookups.
- **`mixer.setTime` + LoopOnce+clamp breaks on re-scrub**: pre-pad every
  track with `(0, firstKeyValue)` key, stretch `clip.duration` to full
  timeline, use LoopRepeat.
- **Blender glTF action keys are TIMELINE-ABSOLUTE** at `t = frame/fps`
  (not `(frame-1)/fps`). Playing all clips on one mixer at time t
  reproduces scene state at frame `t*fps` exactly.
- **glTF ACTIONS mode doesn't bake constraints** (TRACK_TO): camera
  exports pointing at raw euler. Use SCENE bake mode for baked transforms,
  or export aim targets as separate nodes.
- **Physical lighting**: three.js divides diffuse by π; glTF punctuals are
  683× Blender watts. Viewer-side: `l.intensity /= 683`. Blender base
  colors are LINEAR — do parity math in linear.

## USD decision

USD rejected as primary web format: three.js USDLoader crashes on Blender
USDC crates (ASCII .usda parses but USDZ→web blocked); customData
invisible to loader; list-of-dicts rejected by VtDictionary. JSON stays
the story source of truth, USD as parity-gated sidecar.

## Volume materials in glTF

Principled Volume boxes (Street.Mist) export as opaque double-sided mesh
— cameras above stare at the top face (whole shot flat gray). Law:
`blender_kit.atmo_objects()` → EXCLUDE from GLB + DECLARE in previz.json
for web approximation.
