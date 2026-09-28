# blender-agent-kit

Headless Blender agent kit for containerized previz workflows. Lets an LLM
agent drive Blender 4.x LTS via the `bpy` Python API in a no-root, no-GPU
Linux container, render with Cycles or EEVEE_NEXT, critique frames with a
VLM, iterate, and export interactive 3D previews to the browser.

**This is a RELEASE repo — core tooling only.** Projects that use the kit
live in their own repos (see `docs/PROJECTS.md`). Run
`bash run.sh --scope-check` before any commit that adds files — it fails
on project paths (scenes, assets, research, deliverables all belong in
the project repo).

## Quick start

```bash
./install.sh                       # provisions Blender + libEGL + warms shader cache
                                   # (skip if tools/blender/blender already exists)
./scripts/blrun.sh --help          # wrapper options (./run.sh is an equivalent alias)
cp scripts/scene_template.py scripts/my_scene.py
# edit my_scene.py to add your geometry / animation
./scripts/blrun.sh --background --python scripts/my_scene.py -- \
    --output output/my_scene --still 1 --quality previz
```

**Placing objects exactly / checking overlaps** (the #1 previz pain):
see the "Placement & overlap verification" section in AGENTS.md —
`place_on` / `seat_at` / `audit` give mm-exact, one-shot placement and
verification with no screenshot loop. Physics-settled placement:
`physics_place.py` (settle/place/oracle/gate — Bullet-integrated, see the
Physics ops section of AGENTS.md).

See **AGENTS.md** for the full meta doc, **FINDINGS.md** for the research
writeup, **PLAN.md** for the long-horizon roadmap, and **HANDOFF.md** for
immediate next-session scope.
