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
from 640×480 cells that a 96-col ASCII pack could never carry.

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
