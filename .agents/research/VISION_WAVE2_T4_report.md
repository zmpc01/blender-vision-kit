# VISION WAVE 2a — T4 animated walk + export (consumer-agent report)

Date: 2026-09-28. Consumer sub-agent, brief = AGENTS.md only.
INFRA: sub-agent Read still cannot render PNGs (orchestrator is vision verifier).
Motion proven numerically: body Δ = exactly 1.200m f1→f24 (+X), legs parented
travel with body, opposite-phase ±25° swing, LINEAR confirmed; validator PASS
at f1/f24; contact sheet 6/6 cells populated.

## Friction (new)
1. [P1][doc-gap] primitive_capsule_add does NOT exist in Blender 5.2.2 — docs never list verified primitives per version (agent fell back to cylinder).
2. [P1][doc-gap] NO doc law for multi-part actors: legs must be parented to torso (leg.parent = body; leg.matrix_parent_inverse = body.matrix_world.inverted()) or the body walks away and leaves them. Cost a wasted look.
3. [P1][doc-gap] Leg SWING AXIS must be ⊥ travel direction (rotation_euler.x for +X travel) — nothing documents this; caught only by the agent's own probe.
4. [P1][doc-gap] EEVEE preview timing: docs ~2s/frame, MEASURED 8.5s/frame on this llvmpipe (24f+encode = 3m31s) — exceeds the 2-min default tool timeout; budget law needed.
5. [P2][tool-gap] Validator has no articulation awareness: healthy mid-stride scissor-pass = P0 FAIL (bbox 93.1%). Docs warn stills "read fallen" but not that GATES fail mid-stride. look.py --frame evaluates the posed frame; joints cross by design.
6. [P2][tool-gap] Contact sheet at 96-col ascii pack: actors are 3-char clusters, frame labels not detectable, workbench cells achromatic — motion truth needs the numeric probe path (law 108), docs should say so.
7. [P2][doc-gap] kb/glTF_export.md punctual-lights claim vs observed: parsed GLB has 0 lights (no KHR_lights_punctual on 5.2.2 export via kit helper) — reconcile.
8. [P2][doc-gap] frame_set() takes ints only (fractional keyframe math needs int()); --fps default is 12 (undocumented).

## Doc actions taken (orchestrator)
- AGENTS.md: EEVEE timing re-measured note; capsule-actor walk recipe box; animated-frame gate law; --fps default; frame_set int note; primitive note.
