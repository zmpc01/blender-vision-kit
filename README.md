# blender-vision-kit

Headless Blender agent kit for containerized previz workflows — **the
vision-first variant**. Forked from
[zmpc01/blender-agent-kit](https://github.com/zmpc01/blender-agent-kit)
(`@3c0c60d`, docs base `@01dd147`), re-tuned for agents that **see**:
GLM-class models with native image understanding (Read a rendered PNG —
no ASCII packs, no external VLM API in the loop).

Same hybrid architecture as upstream (bpy script / JSON patch →
`blrun.sh` → Blender → verify → iterate), same deterministic gates, same
shared mechanics — different perception doctrine:

| | upstream (blind agents) | this kit (vision agents) |
|---|---|---|
| Primary eye | `ascii_vision.py` text packs | your own vision on rendered PNGs |
| Secondary eye | `z-ai vision` CLI API | none — numeric gates (`image_metrics.py`) complement the eyes; no external eye exists here |
| Look loop | 3 invocations (capture→validate→schema) | **`look.py` — 1 invocation**: images + verdict + manifest + readiness |
| Render defaults | 240×135 previz / 480×360 views (token economy) | 480×270 previz / 640×480 views (eyes need pixels) |
| Geometry truth | gates (unchanged) | gates (unchanged — "eyes triage and compose; gates decide geometry") |
| State carrier | implicit | `apply_patch --save-blend` → `look --load-blend` (never rebuild to inspect) |

## Quick start

```bash
./install.sh                       # Blender 5.2 LTS + libEGL + Pillow
cp scripts/scene_template.py scripts/my_scene.py
./scripts/blrun.sh --background --python scripts/my_scene.py -- \
    --output output/my_scene --dry-run --scene-name my_scene
./scripts/blrun.sh --background --python scripts/look.py -- \
    --scene my_scene --output output/my_scene/look   # annotated grid + verdict

# Or look at the shipped examples directly (bare name or path both work):
./scripts/blrun.sh --background --python scripts/look.py -- \
    --scene examples/scene_v1_basic --output output/ex1/look
```

**Placing objects exactly / checking overlaps**: `place_on` / `seat_at` /
`audit` / `physics_place` (unchanged from upstream — mm-exact, one-shot,
fail-closed). `look.py` draws red boxes on validator-flagged objects and
prints the verdict beside the images.

See **AGENTS.md** for the full consumer guide (vision loop + LAW MAP),
**docs/DESIGN_vision_kit_v1.md** for the design decisions (D1–D14),
**PLAN.md / HANDOFF.md** for the roadmap, **.agents/SKILL.md** for
meta-agent notes, and **kb/vision_loop.md** for the look.py deep reference.

## Which kit should an agent use?

- Agent reads images natively (GLM-4.6V-class, Read tool renders PNGs)
  → **this kit**.
- Agent is text-only / cannot see images → upstream blender-agent-kit.
  **This is a hard scope rule, not a preference**: this kit carries no
  vision-substitute machinery (no ascii packs, no VLM bridge) by design.
- Both kits share `blrun.sh`, `blender_kit/`, `apply_patch.py`,
  `placement_lib.py`, `physics_place.py`, export/validator surfaces —
  skills transfer.
