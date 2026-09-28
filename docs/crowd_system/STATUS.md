# Crowd System Status — FORKED to blender-crowd-kit

> **As of session 27 (2026-09-27)**, the crowd simulation system has
> been forked out of `blender-agent-kit` into a standalone repo:
> **https://github.com/zmpc01/blender-crowd-kit**

## Why the fork

Per user directive (session 27):
> "as you are still building out i suggest you create this as a
> blender-crowd-kit first and then vendor into the actual blender kit
> once you reach usable milestone. and as you go through these make
> sure you distill both the meta agent (yourself) facing work agent
> learning into .agents/SKILL.md and also consumer agent (using this
> kit) facing AGENTS.md (once you have a stable agent usage surface)."

Benefits of the fork:
1. **Isolated development** — crowd work doesn't entangle with the kit's other subsystems
2. **Clean vendor boundary** — when crowd-kit reaches v1, it can be vendored as a git submodule or pip-install
3. **Stable consumer surface** — blender-crowd-kit has its own `AGENTS.md` (consumer-facing) + `.agents/SKILL.md` (meta-agent facing)
4. **Separate issue tracker + history** — crowd bugs don't pollute the kit's worklog

## What moved to blender-crowd-kit

- `scripts/crowd/` (8 files: adapter, bake, apply_to_scene, cli, etc.)
- `tests/crowd/` (3 tests: smoke, 1K benchmark, end-to-end in Blender)
- `examples/crowd/scene_concourse_1k.py` (1K-agent concourse reference)
- `docs/crowd_system/` (PLAN, HANDOFF, DESIGN v1.1, v1.3 addendum, GAP analysis, rust_build_spike)
- `vendor/blender-crowd/` (14MB; vendored bgyss code + pre-built wheel)

## What STAYED in blender-agent-kit

These were in blender-agent-kit BEFORE the crowd system work started
(parallel workstream s26-s28), so they stay:
- `scripts/crowd_fields.py` + `test_crowd_fields.py` (force field primitives)
- `scripts/gait_modifiers.py` + `test_gait_modifiers.py` (gait modification engine)
- `scripts/blender_kit/prop_carry.py` (prop-anchoring scenario plugin)
- `scripts/assets_ual_actors.py` + `scripts/ual_bake.py` (UAL rig vetted path)
- `kb/crowd_fields.md`, `kb/gait_modifiers.md`, `kb/prop_carry.md`
- `assets/vendor/ual/` (UAL CC0 rig + clips)

These will be vendored into blender-crowd-kit at the v1 milestone (M3
complete) — they're currently duplicated so the kit can still use them
independently.

## Migration plan

1. **Now (session 27)**: fork complete; blender-crowd-kit has all crowd code; blender-agent-kit has a stub `scripts/crowd/__init__.py` pointing to the new repo.
2. **M2-M3 (next 2-5 sessions)**: develop crowd features in blender-crowd-kit. The kit's `crowd_fields.py` + `gait_modifiers.py` + `prop_carry.py` stay duplicated until v1.
3. **v1 milestone (M3 complete)**: vendor blender-crowd-kit back into blender-agent-kit as a git submodule at `vendor/blender-crowd-kit/`. Remove the duplicated `crowd_fields.py` + `gait_modifiers.py` + `prop_carry.py` from blender-agent-kit (they'll be in blender-crowd-kit's `scripts/`).

## How to use the crowd system from blender-agent-kit

Until the v1 vendor:

```bash
# Clone blender-crowd-kit (one-time)
git clone https://github.com/zmpc01/blender-crowd-kit.git /home/sync/blender-crowd-kit

# Install its deps (one-time; installs Blender 5.2.2 LTS + bgyss wheel)
cd /home/sync/blender-crowd-kit && bash install.sh

# Use from blender-agent-kit scripts:
import sys
sys.path.insert(0, "/home/sync/blender-crowd-kit")
from scripts.crowd import CrowdProject, Population, bake, apply_to_scene
```

## Cross-references

- blender-crowd-kit repo: https://github.com/zmpc01/blender-crowd-kit
- blender-crowd-kit AGENTS.md (consumer guide): https://github.com/zmpc01/blender-crowd-kit/blob/main/AGENTS.md
- blender-crowd-kit .agents/SKILL.md (meta-agent guide): https://github.com/zmpc01/blender-crowd-kit/blob/main/.agents/SKILL.md
- blender-crowd-kit design docs: https://github.com/zmpc01/blender-crowd-kit/tree/main/docs/crowd_system
- Historical context (this repo's worklog): `worklog.md` (sessions 23-26 entries)
