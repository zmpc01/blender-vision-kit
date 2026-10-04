# USABILITY_R3.md — dog-food study, EEVEE/final-render lane (session 6)

> Protocol (same as R1/R2): owner = the vision agent, CONSUMER SEAT.
> Docs-only navigation (AGENTS.md quick start + README); every friction
> logged here the moment it bites; kit fixes land as they surface, each
> with a micro-commit. Reset-restart discipline: fresh sandbox, fresh
> clone @ 67621da + session-6 QA fixes (50261a5..f33a41e).

## Scenario

"Product turntable" (`scripts/r3_turntable.py`): chrome ball, red plastic
cube, green cylinder on a studio ground, 3-point lighting + sky world,
camera orbit (turntable pivot) + an animated slider prop. Goal: exercise
the FINAL-RENDER lane — EEVEE stills, animated ship (MP4), EEVEE
perception lane (look/motion/scan with `--engine eevee`), engine parity
vs workbench, warm-cache ergonomics.

## Friction log

### F1 (R3) — THREE engine vocabularies disagreed across CLIs
AGENTS.md:182 taught `--engine BLENDER_EEVEE_NEXT` (raw enum); look.py's
argparse accepted ONLY short names (`workbench|eevee|cycles`); the
scene-template family (common_parser) accepted ONLY raw enums. So the
documented LOOK command crashed with `invalid choice` (reproduced), and
fixing it revealed you could LOOK with `eevee` but not BUILD/SHIP with
`eevee` (F5 below). Kit fix: `blender_kit.normalize_engine()` (short-name
bridge for the perception CLIs) + common_parser now normalizes through
`normalize_engine_id` (raw-id bridge for the ship family) — every CLI now
accepts every spelling, each family keeps its internal convention.
AGENTS.md examples corrected to short names + "(raw enums accepted)".

### F2 (R3) — workbench/EEVEE color parity: NOW TRUE (D15 payoff)
Same props, workbench grid vs EEVEE still: node-authored colors read the
same (red/red, green/green). Before D15 the workbench side was gray and
the lanes DISAGREED — the agent could not trust color across lanes.
Recorded as D15 acceptance evidence from the consumer seat.

### F3 (R3) — EEVEE renders dark scenes honestly; readiness flagged it
First EEVEE look on the D15 test scene (single sun pointing straight
down): grid nearly black, VERDICT still PASS — BUT readiness header +
manifest carried `NEAR-BLACK` / `dark=97.6%`. Worked as designed: flags
inform, eyes decide, and EEVEE exposure stays 0.0 EV ON PURPOSE (the
EEVEE lane must preview the SHIP render, not flatter it). No fix; the
division held. (Workbench's +1.0 EV lift is a perception default, not a
ship-preview default — the asymmetry is correct.)

### F4 (R3) — scene_template docstring still taught the enum spelling
`--engine BLENDER_EEVEE_NEXT` in the copy-me docstring. Updated to
`--engine eevee` (both spellings work post-F1; short is canonical).

### F5 (R3) — build/ship family rejected short names (mirror of F1)
`common_parser()` choices were raw-enums-only: the same workflow that
LOOKs with `eevee` could not SHIP with `eevee`. Fixed inside F1's
normalizer work. Default `CYCLES` unchanged (argparse defaults bypass
`type=`, so the raw convention is preserved).

### F6 (R3) — sky-world × EEVEE overexposure trap (cross-lane blindness)
`add_sky_world()` default strength 1.0 (physical sky) + Standard view
transform + typical 3-point lights = BLOWN-OUT EEVEE stills (red read
pink; measured twice after halving lamp powers — the sky was the
culprit, not the lamps). Workbench looks NEVER reveal this: workbench
ignores world lighting. A previz agent can pass every workbench look and
still ship an overexposed EEVEE render. Consumer remedy: sky strength
0.35 for studio scenes. Kit remedy: template docstring note + gotcha in
AGENTS.md (a changed DEFAULT would alter every existing scene's world —
not done unilaterally).

### F7 (R3) — motion_study tracked STATIC props, excluded the ONLY mover
(second consumer hit; R1's F11-NIT promoted) — `--frames 24` on the
turntable: tracked ChromeBall/GreenCyl/RedCube (static), NOT-TRACKED the
animated Slider; trajectory rows were degenerate. Kit fix:
`_pick_objects` + the dropped-list ranking are ANIMATED-FIRST (direct
keyframe action wins the cap; size breaks ties). Verified: tracked set
now leads with the Slider; POP-FRAMES correctly flag its fast travel;
v2 suite ALL PASS.

### F8 (R3) — authoring error the lane CAUGHT (doctrine demo, not a kit bug)
transient_scan flagged TRANSIENT P0 GreenCyl×Slider f17..f19 (bbox-proxy
hint); audit at f18: "overlap 96.9% of smaller object" — REAL (slider
path clipped the cylinder; bezier curvature ate my linear clearance
math). Fixed the path to a front arc; full-timeline scan then came clean
(only the camera-orbit pixel event, correctly ranked #1). The
scan→audit→fix→rescan loop worked exactly as designed on the EEVEE lane.

## What worked (kept)

- warm-cache under the new MemAvailable guard: ran at 3.5 GB available,
  EEVEE stills then rendered without cold-compile stalls.
- look.py --engine eevee: validator + readiness + annotations all work
  over EEVEE renders; grid readable (verified visually, 4 angles).
- Animated ship: `--frames 24 --encode-mp4` → 24 PNGs + valid MP4.
- motion_study POP-FRAMES + read-order hints; transient_scan event table
  + suspects strip + doctrine line — all engine-agnostic.
- The state carrier law held: no rebuilds needed to inspect (script
  scenes are deterministic; patch scenes used --load-blend in R1/R2).

## Verdict

EEVEE lane is consumer-ready after F1/F5/F7 fixes. The remaining open
item is the F6 documentation (template + gotcha) — applied in this
session's docs commit.
