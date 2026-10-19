# Crowd System Status — FORKED to blender-crowd-kit, VENDORED BACK (r043)

> **As of session 27 (2026-09-27)**, the crowd simulation system has
> been forked out of `blender-agent-kit` into a standalone repo:
> **https://github.com/zmpc01/blender-crowd-kit**

## VENDORED BACK (r043, M9.5-9.6 — 2026-10-01)

The fork's end-state is REACHED: blender-crowd-kit is vendored into this
kit as the **`vendor/blender-crowd-kit` git submodule** and
`scripts/crowd/__init__.py` re-exports its 13-name public surface (the
kit's canonical 10 + the 3 legacy names below) via a private-alias load
(`_vendored_blender_crowd_kit`). This kit's stale `crowd_fields.py` /
`gait_modifiers.py` copies (and the `prop_carry.py` + kb trio) were
REMOVED in r050 (B2 dupe-removal) — vendored code only ever resolves
kit-canonical names.

- Submodule pin: kit r050 tip `bc11fcb` (package-relative imports —
  loads under any parent package name; r045-r049 since the r043 pin:
  codec-v2, motion-DB `read_range`, vendor hardening → native wheel 1.3.0).
- Wheel pin (B1, r050 refresh): `blender_crowd_native 1.3.0`, canonical
  sha256 `18ee1fbacc12fd979bdb978c2dc095414b6f84859e956d027b350b4ef4dfed46`
  (= kit SHA256SUMS). The older `vendor/blender-crowd` 1.0.0 wheel
  (`b861b4db…`, 78 B smaller, SUPERSEDED) was REMOVED r050 (B2) —
  never install both eras; only the vendored kit's 1.3.0 wheel ships.
- Restore in a fresh sandbox (non-interactive):
  `git config --global url."https://<PAT>@github.com/".insteadOf "https://github.com/"`
  then `git submodule update --init --recursive vendor/blender-crowd-kit`
  (`.gitmodules` deliberately carries the CLEAN URL — no credentials in
  committed files).
- Fail-closed: importing `scripts.crowd` with the submodule uninitialized
  raises ImportError with the exact repair command (gated by
  `tests/test_crowd_vendor_gate.py`).

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
- `scripts/crowd_fields.py` + `test_crowd_fields.py` (force field primitives) — REMOVED r050 (B2: byte-identical dupes, canonical in blender-crowd-kit)
- `scripts/gait_modifiers.py` + `test_gait_modifiers.py` (gait modification engine) — REMOVED r050 (B2)
- `scripts/blender_kit/prop_carry.py` (prop-anchoring scenario plugin) — REMOVED r050 (B2; blender-crowd-kit carries the copy)
- `scripts/assets_ual_actors.py` + `scripts/ual_bake.py` (UAL rig vetted path)
- `kb/crowd_fields.md`, `kb/gait_modifiers.md`, `kb/prop_carry.md` — REMOVED r050 (B2: not manifest-governed dupes; kit kb carries them)
- `assets/vendor/ual/` (UAL CC0 rig + clips)

The crowd-code duplication is fully resolved (r043 vendored-back +
r050 B2 dupe-removal).

## Migration plan

1. **Now (session 27)**: fork complete; blender-crowd-kit has all crowd code; blender-agent-kit has a stub `scripts/crowd/__init__.py` pointing to the new repo.
2. **M2-M3 (next 2-5 sessions)**: develop crowd features in blender-crowd-kit. The kit's `crowd_fields.py` + `gait_modifiers.py` + `prop_carry.py` stay duplicated until v1. — **[resolved r050: duplicates removed (B2).]**
3. **v1 milestone (M3 complete)**: vendor blender-crowd-kit back into blender-agent-kit as a git submodule at `vendor/blender-crowd-kit/`. Remove the duplicated `crowd_fields.py` + `gait_modifiers.py` + `prop_carry.py` from blender-agent-kit (they'll be in blender-crowd-kit's `scripts/`). — **[r043: submodule + re-export stub landed; r050/B2: dupe-removal DONE (+ superseded 1.0.0 wheel removed).]**

## How to use the crowd system from blender-agent-kit

After the vendor-back (r043):

```bash
# One-time, in a fresh sandbox: make private-repo submodule fetches
# non-interactive (the .gitmodules URL is credential-free)
git config --global url."https://<PAT>@github.com/".insteadOf "https://github.com/"
git submodule update --init --recursive vendor/blender-crowd-kit

# Native wheel for the vendored kit (bake-time dependency)
cd vendor/blender-crowd-kit && bash scripts/setup_native.sh && cd ../..
```

```python
# Then plain package-level import (no sys.path games):
from scripts.crowd import CrowdScene, bake, attach_to_scene
# legacy names also resolve:
from scripts.crowd import CrowdProject, Population, apply_to_scene
```

`bake()` is Blender-free (pure CPython + the native wheel);
`attach_to_scene()` is the only Blender-dependent step. Scene factory
methods beyond `CrowdScene.concourse` are listed in the vendored kit's
consumer guide: `vendor/blender-crowd-kit/AGENTS.md` (+ its
`docs/crowd_system/FEATURE_REFERENCE.md`).

Submodule-level imports through this namespace (`from scripts.crowd.bake
import …`) are NOT supported — import from `scripts.crowd`.

## Cross-references

- blender-crowd-kit repo: https://github.com/zmpc01/blender-crowd-kit
- blender-crowd-kit AGENTS.md (consumer guide): https://github.com/zmpc01/blender-crowd-kit/blob/main/AGENTS.md
- blender-crowd-kit .agents/SKILL.md (meta-agent guide): https://github.com/zmpc01/blender-crowd-kit/blob/main/.agents/SKILL.md
- blender-crowd-kit design docs: https://github.com/zmpc01/blender-crowd-kit/tree/main/docs/crowd_system
- Historical context (this repo's worklog): `worklog.md` (sessions 23-26 entries)

## s41 addition — the scene→obstacle bridge + the honest engine audit

`scripts/crowd_obstacles.py` (kit-owned) derives `Blocked` declarations
from PLACED SCENE GEOMETRY (collections/prefixes selection, world
z-band filter, margin growth + clip-to-walkable, MESH-only, animated
REFUSED) — closing the "crowds walk through placed objects" gap at the
AUTHORING layer. The vendored re-export grew the authoring dataclasses
(13→20-name contract; vendor gate updated in lockstep). Battery:
tests/test_crowd_obstacles.py (O1-O11, 11/11 live incl. a REAL bake).

The ENGINE-side truth (live-measured, upstream issue #15 to
blender-crowd-kit — never pushed, filed per protocol): no path
planning (an obstacle across the path = total jam, 0/20 reach across
seeds 11-15) + pressure-soft pushout (up to 0.59 m penetration) +
force_fields silently inert at bake. O11c PINS the jam (flips loudly
when their routing lands).
