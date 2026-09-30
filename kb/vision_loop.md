# kb/vision_loop.md — the look.py protocol (vision-kit)

> Consumer entry: AGENTS.md "THE VISION LOOP". This KB is the deep
> reference: measured timings, annotation internals, readiness scores,
> failure modes found while building and testing the tool.

## Why look.py exists (measured)

The blind kit's perception round was THREE invocations (viewport_capture
→ validate_scene → scene_schema), each paying a full Blender cold start
(~3–8s: binary boot + Xvfb + bpy init + scene load). The vision agent
looks OFTEN — every look paid 10–20s of pure cold-start overhead.
look.py bundles the round into ONE invocation and prints the numbers
BESIDE the images (forced pairing — the agent cannot look without also
seeing the gates' verdict).

Measured on the sandbox (Workbench, 640×480, 4 angles + annotations):
- look.py full invocation: ~8–12s total (cold start dominates)
- the 3-invocation equivalent: ~25–35s
- annotation layer build+delete: <0.3s (51 thin-box/text objects)

## Resolution economics (D3, measured)

| Surface | Was (blind) | Now (vision) | Workbench cost |
|---|---|---|---|
| `--quality previz` | 240×135 | 480×270 | ~0.3s/frame |
| look/viewport angles | 480×360 | 640×480 | ~0.05–0.1s/frame |
| keyframe sheet cells | 320×240 | 480×360 | ~0.05s/frame |

kb/render_speed.md: AA-OFF Workbench ≈ 0.05s/frame at 960×540 — pixels
are cheap; the cold start is the budget. The vision agent reads geometry
straight from 640×480 cells with its own eyes — give the eyes pixels.

## Annotation layer internals (D5)

Built by `scripts/annotate.py` on a `KIT_ANNOT_*` name prefix, deleted in
a `finally` (render-time only, NEVER saved — look.py has no save flag):

- **1m ground grid**: thin boxes (6mm) at integer meters, bounds+1m
  margin, 4mm above floor (z-fight avoidance), gray 0.45.
- **RGB axis gnomon**: 1m × 30mm bars at (center − 1.5, −1.5, z=5mm).
  Position was MEASURED twice: at world origin it sits inside the
  centered subject (invisible); at the scene min corner it is out of
  frame for large grounds. SW-offset is inside standard framing.
- **Object labels**: top-N by bbox diagonal (default 8, `--labels N`),
  FONT text, size = clamp(diag × 0.18, 0.06, 0.4m) at bbox top + 0.9×
  size, yellow. Aimed per-angle (`aim_labels_at`); the `top` angle lays
  labels FLAT (tracked billboards go edge-on = unreadable strokes).
  Ground-like slabs (flat + ≥6m²) are EXCLUDED — a 20×20m ground label
  rendered as a giant billboard blocking the entire top view (first run,
  measured).
- **Flag boxes**: red 12-edge bbox wireframe on validator P0/P1 objects
  (12mm edges, +10mm pad). Only drawn when the validator ran in the
  same look (it always does in look.py).

## Readiness scores (D6)

Per image, printed in the verdict block (PIL+numpy, no extra invocation):
`luma= mean`, `clipped=%` (≥0.98), `dark=%` (≤0.08), `subject=%`
(RGB distance > 0.25 from corner-estimated background), flags:
- BLOWN-OUT (clipped > 25%) — reduce exposure/sun (5.x EEVEE +4-12% law)
- NEAR-BLACK (dark > 40%) — add fill light / fix world; your eyes (and
  any downstream audit) hallucinate on black frames (upstream law 77)
- NEAR-EMPTY (subject < 1.5%) — crop closer / check target; a nearly
  empty frame makes vision confidently wrong

Thresholds calibrated on synthetic + rendered images (test_v1_look #2).
Luma-only subject detection MISSED red-on-gray (luma-matched) — use RGB.

## Exit codes + markers

- 0 = clean (PASS/WARN-free), 3 = validator P0/P1 (fail-on-issues parity
  with validate_scene). RAW blender propagates; **blrun.sh does not**
  (its gate greps tracebacks only) — grep `VERDICT:` lines instead.
  Upstream gotcha: in-Blender test suites subprocessing the raw binary
  DO see real exit codes (env inherited from the blrun parent).
- Verdict text: FAIL (P0>0) / WARN (P1>0) / PASS. Severity scale:
  floating=P1, below-floor=P0, intersection=P1 (P0 at ≥30% overlap),
  above-ceiling=P2.

## State carrier doctrine (D9)

```
apply_patch --patch fix.json --save-blend work.blend   # ACT + SAVE
look --load-blend work.blend                            # LOOK
```
`--scene` REBUILDS and silently discards patch-applied state (RB settle,
manual edits). First-run mistake class: a look on the rebuilt scene shows
pre-patch state; the agent then "fixes" already-fixed objects. The
manifest ids + validator numbers come from the SAME state as the images —
one state, one truth.

## Label frame-safety (M5 label-stick fix, measured)

Labels (and flag boxes) were built from build-time evaluated state; a
`--frame 16` look on an animated scene rendered labels at stale positions
and the closeup label aim came out edge-on ("yellow stick"). Two fixes:
1. look.py re-issues `frame_set(args.frame)` + DOUBLE `view_layer.update()`
   right before annotation build (the kit's own stale-read law,
   prop_carry.py:53 — the validator runs in between and depsgraph state
   must be re-pinned).
2. `annotate.refresh_labels(layer)` re-reads each label's target object
   bbox (`KIT_ANNOT_lbl_*["kit_target"]` custom prop — name-suffix parsing
   breaks on underscored ids) at the CURRENT frame; called before EVERY
   `aim_labels_at` (grid loop + closeup). Verified: f16 closeup label "2"
   reads perfectly; flag box wraps the sunk GlitchBox at its f16 bbox.

## Animation representation (M5 P3, measured on T6 parabola/drift/sink)

| representation | answers well | fails at |
|---|---|---|
| filmstrip (frame grid) | translation drift over time | vertical nuance weak; spin INVISIBLE; samples can straddle a transient |
| onion-skin ghosts | rise/fall, speed (spacing), direction, age (lightness ramp: lightest=oldest, red=now) | path shape (overlap), absolute shape noise |
| trajectory polyline | path SHAPE (unmatched), tick spacing = speed | nothing per se — but MUST be multi-angle (a vertical trail collapses to a stub from one angle) |
| numeric motion table | magnitudes, POP/BURST flags | everything visual |

Build lessons (each measured): solid ghost spheres buried 15mm polylines
entirely at slow motion → render trajectory and onion in SEPARATE passes
(stitched 2×2: row1 traj shadowless, row2 onion with shadows); ghosts
coincident with the current pose z-fight into stripe noise → skip them
(<5mm from current); ticks at 0.1m dominated the line → 0.036m; linked
duplicate ghosts share mesh data → re-materializing them strips the REAL
object's materials → full mesh copy per ghost, `KIT_MOTION_` prefixed;
workbench shadow buffer goes stale across in-process hide_render toggles
→ shadows=off for the pass without solids.

## Transient scan (M5 P4, planted T6 sink f14-18)

A 3-frame glitch between keyframes is INVISIBLE to keyframe sheets unless
a sample lands inside it (measured: sampling caught it only by luck).
transient_scan.py renders every frame (~0.3s/frame previz) and combines:
- change radar: consecutive pixel diff, floor = median+2*MAD (MAD-robust),
  clustered events ranked by peak diff. Finds pops/flickers. CANNOT find
  a parked wrong state (the sunk state itself has near-zero diff — the
  T6 diff peak was the RECOVERY end f19, not the sunk f16).
- state radar: validator at every frame — semantic findings
  (`floor_penetration` P1 on GlitchBox f15..f19). Classified by duration:
  ≤40% of range = TRANSIENT; >60% = PERSISTENT baseline (a jump is
  "floating" on every airborne frame — design, not bug; listed once).
Output: EVENT-TABLE + suspects strip (start/PEAK/end + BAD cells) →
eyes verdict at full res (`look.py --frame N --angles none --closeup`).
The scanner ranks; the eyes verdict. A clean keyframe sheet proves
nothing about transients.

## Known limits / deferred

- Camera offsets are fixed 5m (upstream VIEW_ANGLES) — huge scenes
  overflow; aim with `--target`/`--lens`/`--closeup`. Auto-pullback was
  considered and REJECTED for v1: fitting a 20m ground shrinks the
  subject to a speck — the ground overflowing the frame is correct.
- Labels are indexes, not names (name text at previz scales is noise);
  the manifest maps index→id via the ranked order.
- Crowd instances: validator bbox overlaps fire red boxes on dense
  crowds (normal); judge crowds by density/flow, actors by id.
- Diff-look (before/after side-by-side) deferred.
