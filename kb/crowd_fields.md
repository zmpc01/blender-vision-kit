# crowd_fields — Influence Fields + Relax PBD + Gait Phase Engine

Scene-agnostic crowd primitives (kit scripts/crowd_fields.py; tests:
test_crowd_fields.py). The scene contributes only DATA (field tables,
lane specs, modifier stacks) — nothing project-specific in the engine.

## 1. Signed fields (the influence-sphere primitive)
`FieldSpec(name, kind, radius, strength, falloff, center |
center_fn, t_active, merge_obstacle, source, strength_fn)` —
positive strength attracts, negative repels, 0 = obstacle-only;
`merge_obstacle` adds the disc to the relax static set. Animated
attractors (`center_fn`) follow the iCrowds law: moving attractor =
pursuit target. Temporal envelopes: `ramp_env`, `decay_env`,
`event_env` (attach via `strength_fn`; `strength_repr()` keeps params
hashes honest). `evaluate_fields(px, py, t, fields)` -> (fx, fy,
discs). `dominant_attractor(...)` -> alert-transition predicate.

## 2. relax() — deterministic vectorized PBD
Personal space + static obstacle discs. Pair set from a spatial hash
via grouped-join expansion (np.argsort + searchsorted + repeat-run;
bit-identical to the reference bucket builder; ~0.3 ms/tick at
N=129). np.add.at accumulation is order-independent; static discs
are infinite mass (the agent is pushed fully out).

## 3. Gait phase law (kills foot-slide by construction)
`advance_phase(phase, disp, stride)` = (phase + disp/stride) % 1.0 —
driven by root DISPLACEMENT, never time. `playback_rate(speed,
nominal)` clamped [0.5, 2.0]. Outside the clamp you switch clips,
never skate.

## Provenance
Contracts re-derived from public docs of bgyss Blender-Crowd (GPL,
not vendored), abmsim (MIT), iCrowds (GPL, product not vendored).
Zero code copied.
