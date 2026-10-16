# Daz3D scene modules (external scene-dir pattern)

> Pattern born in `github.com/srbuhiartur/daz-bpy-previz` (the bpy-oracle
> track). The kit stays core-tooling-only — all Daz content, builders, and
> the comply recipe live in the project repo; this doc records the
> SUPPORTED pattern for scenes that arrive as pre-built .blends.

## The pattern

`export_previz_package.py` runs in `--factory-startup` (user addons —
e.g. Diffeomorphic — disabled; core addons like io_scene_gltf2 stay on).
Scenes whose content comes from an addon pipeline (Daz3D via the
Diffeomorphic importer) cannot build in-process — the content must arrive
as a PRE-BUILT .blend, loaded by the scene module itself:

```python
def build_scene():
    bpy.ops.wm.open_mainfile(filepath=_blend_path())  # pre-built content
    scene = bpy.context.scene
    # ... add CAMS_V3 cameras, Aim.* empties, markers, CAST registry
    return {"scene": scene}
```

- The .blend path comes from an **environment variable** (e.g.
  `DAZ_SCENE_BLEND`) read inside the module. Module-level UPPERCASE
  constants are restricted to the story contract (the nothing-left-out
  naming law) — keep wiring lowercase.
- `animate(ctx)` should pin the 5.x action slots
  (`ad.action_slot = ad.action.slots[0]`) for actions that arrive ASSIGNED
  from the pre-built blend (the slotted-Actions law, kb/rigged_characters.md).
- Fail with teacher-grade `SystemExit` messages (missing env var, no
  assigned actions) — blrun's traceback gate turns silent failures into
  rc≠0 noise.

## Running it

```bash
DAZ_SCENE_BLEND=<comply.blend> bash scripts/blrun.sh --background \
    --factory-startup --python scripts/export_previz_package.py -- \
    --scene scene_daz_v1 --scene-dir <project's scene dir> \
    --output output/daz_pkg_v1 --package-id daz_pkg_v1 --name "..."
```

`--preflight` first (seconds, no writes: naming law, camera count, fps).

## Gate behavior on rigged Daz content (measured, daz-bpy-previz session 6)

A G2F figure + clothing (4 rigs, 4 assigned actions, skinned meshes,
21K-vert figure, 41 materials, 4 skins) exports ALL-GREEN first run:
gates 1/2/3/4/5/6/13/22/24 pass on content built outside the kit; the
rigged gate 10 is satisfied by the skins; gates 15-21 skip loudly
(no crowd/FX/hero markers — the additive law) while gate 12 skips
silently without `t_drive`/BeltRoot and gate 21 no-ops without Zed.*
nodes. Watch:
- **gate 13**: one assigned action per rig (ACTIONS mode gives one glTF
  animation per rig — do not stash duplicate actions).
- **gate 14**: Daz meshes are SKINNED, not bone-parented — static
  bone-children would fail closed.
- **gate 22c**: keep all coordinates within 1e4 m of the origin.
- The `> 4 joint vertex influences` exporter WARNING is expected for
  Daz triax rigs (the honest deformation budget is ~4 mm worst-case,
  measured element-wise — see the project's kb/export-workflow.md).

The upstream scene-building contract (the 5-step comply recipe: drv-chain
repair, SUBSURF prune, nla.bake visual keying, weight normalization,
bump→normal bake) lives in the project repo — `srbuhiartur/daz-bpy-previz`
`.agents/kb/export-workflow.md` — and is vendored into the web track at
`daz-web-pipeline/vendor/daz-bpy-kit/`.
