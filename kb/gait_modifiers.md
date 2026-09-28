# gait_modifiers — Funny-Walk Gait Modifier Engine

Scene-agnostic funny-walk primitives (kit scripts/gait_modifiers.py;
tests: test_gait_modifiers.py). The scene contributes only DATA — its
named modifier stacks and base-clip compositions — nothing
project-specific in the engine. Lifted from the previz crowd_v6
clips.py modifier core (the crowd_fields.py precedent).

## The law: a funny walk = base clip + named modifier stack

A funny walk is NEVER a new mocap clip. Take a library base loop
(Walk_Loop), evaluate its pose per frame into a plain
`{bone: (loc, quat)}` table, and compose a stack of small per-bone
channel deltas ADDITIVELY over that base pose (the Seated_Flinch
precedent: compose source-channel deltas onto a base loop, never key
the imported sources). Stack order is significant — the later name in
the stack is the outermost rotation.

## 1. Deltas — `RotDelta` / `LocDelta`

`RotDelta(bone, axis, kind, amp_deg, cycles=1.0, turn=0.0)` —
bone-local rotation; `LocDelta(...)` the metre twin for locations.
Kinds: `"osc"` (sinusoidal over the gait cycle phase p — head
z-wobble, lean oscillation), `"bias"` (constant — shoulder droop),
`"amp"` (scale the base clip's WHOLE deviation from rest —
`quat_pow(q, amp)` for rotations, `loc * amp` for locations; the
axis field is documentary), `"twitch"` (3-key jerk pulse: 0 at p=0,
+amp at 0.2, -amp at 0.4, 0 from 0.6). CAUTION: a LocDelta on a
root/hips bone moves the character's origin — stride-feeding phase
laws assume rotation-only modifiers.

## 2. Named tables — `GAIT_MODIFIERS` + `register_modifiers(**named)`

Name -> tuple of deltas, one shared registry. The kit pre-seeds the
generic vocabulary (`head_bob_drift`, `arm_swing_var`, `lean_osc`,
`step_asym` — the asymmetry/lean/head-bob/arm-variance kinds, the
iCrowds anti-robotic variety package; bones speak the UAL/Rigify
DEF-* names). A scene registers its own names into the SAME
registry:

```python
from gait_modifiers import RotDelta, register_modifiers
register_modifiers(
    head_z_wobble=(RotDelta("DEF-head", "z", "osc", 12.0),),
    hip_hitch=(LocDelta("DEF-hips", "y", "twitch", 0.03),),
)
```

Fail-closed and atomic: duplicates, unknown kinds, bad axes,
non-finite amplitudes, empty or non-delta tables raise ValueError
BEFORE any insert. `validate_modifiers(table=None)` is the
audit-side twin (findings list, empty = clean; defaults to the whole
registry).

## 3. Composition — `apply_modifiers(table, names, p)`

In-place onto any `{bone: (loc, quat)}` pose table; "osc"/"bias"/
"twitch" PRE-multiply the bone quaternion (bone-local axis),
"amp" scales the deviation from identity (base clips are authored
from rest, so q IS the deviation); LocDelta does the same law on the
location triple. Bones absent from the table are skipped (never a
KeyError — pruning is the scene's). Build tables under system python
with `decompose(m)` (row-major 4x4 -> (loc, quat); the pure
mathutils `Matrix.decompose()` twin, scale pinned 1.0).

Quaternion core on plain (w, x, y, z) tuples: `quat_mul` (Hamilton),
`quat_axis_angle`, `quat_pow` (fail-closed unit guard), `quat_slerp`
(shortest-path, degenerate-safe), `canonicalize_quats` (the dot<0
anti-flip law across frames).

## Worked example

The previz zombie scene (blender-escape-previz scripts/crowd_v6/
clips.py) is the reference integration: it registers its §4.3
shamble building blocks (`head_z_wobble`, `shoulder_droop_l`,
`hips_drag`, `thigh_drag_r`, `spine_sway`, `head_twitch`,
`arm_pump`) into the kit registry, then stacks them per composed
clip (Shamble_A = Walk_Loop + head_z_wobble + shoulder_droop_l +
hips_drag at rate 0.72; the scene keeps the clip registry, the
composition specs and the bpy-side action authoring). The repo
carries a byte-identical copy of gait_modifiers.py in its scripts/
(the crowd_fields.py sync law, cmp-verified).

## Provenance

The modifier-composition law re-derived from public docs of iCrowds
(anti-robotic per-agent variety; GPL, product not vendored) + bgyss
Blender-Crow modifier-style variety reads. Quaternion algebra is
standard (Hamilton; Shepperd's method for decompose). Zero code
copied.
