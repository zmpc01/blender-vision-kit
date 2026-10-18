# RH cross-validation s22 — the fixture library vs the REAL platform files

> The s20 fixture recipes were reverse-engineered OFFLINE (the data
> source was dead). On 2026-10-18 the RH asset ecosystem came back
> (beulahkemp/RH-canvas-animations + RH-canvas-characters + RH-3d-assets;
> CDN live, sha-verified 2,137/2,137 FBX locally) — so every pinned
> fixture law got re-measured against REALITY. Probe:
> `scripts/s22_crossval.py` (battery row `test_rh_crossval`; honest-skips
> when either layer is absent). Raw measurements: `output/tests/rh_crossval.json`.

## Method

Import REAL clips through the kit path (`rh_canvas.import_clip`: 2846
"Run fast" — the battery pin, 2899 "male standard walk", 2781 "idle")
and the fixture run clip (9002 快速奔跑) through the same path; measure
the same truth dimensions on both; diff per law.

## The verdict table (measured 2026-10-18, Blender 5.2.2)

| law | fixture (9002) | real (2846/2899/2781) | verdict |
|---|---|---|---|
| bone census | 65 | 65 / 65 / 65 | **MATCH** |
| mixamorig: prefix | 65/65 | 65/65 | **MATCH** |
| pose rotation mode | QUATERNION | QUATERNION | **MATCH** |
| import fps | 30 | 30 | **MATCH** |
| world z min (feet) | 0.020 | 0.0325 / 0.0347 / 0.0312 | **MATCH** (±0.05 band) |
| human height band | 1.854 max | 1.629–1.785 max | **MATCH** (1.4–2.1 band; per-clip pose data) |
| obj scale | 1.0 | 0.01 | DEVIATION-EXPECTED |
| obj rot X | 0.0° | 90.0° | DEVIATION-EXPECTED |
| hips fcurve raw @first key | 0.0 (rest-delta recipe) | 0.5168–0.7725 (absolute, unit-converted) | DEVIATION-EXPECTED |

**0 UNEXPECTED deviations.** The three expected deviations are exactly
the class s20 documented as "the Maya-time unit baking is unrecoverable
offline" (obj scale 0.01 + rot 90° carry the cm→m and Y-up→Z-up
conversions in the platform files; the fixture recipe compensates by
authoring rest-defined T-pose + meter-space delta curves). Behavioral
equivalence is proven by the world-space gates (world z min within band;
the F-battery's world-z behavior gates).

## What this means

1. **The fixture library is a validated behavioral double** of the
   platform family — census, modes, fps, ground behavior, and human
   scale all hold against reality; the unit-convention differences are
   measured facts with a documented compensation recipe
   (`node_scale=100, usf=1.0, rest_mode=m_yup, node_rot=-90` in
   truth.json).
2. **The s20 "single point of failure" risk is retired twice over**:
   the real data path is live again (test_rh_canvas runs 14/14 against
   the real repos), and the offline path is now cross-validated against
   that real data (this document) instead of resting on reverse-
   engineering alone.
3. **Animated-bone census nuance**: real clips animate 52 bones (the
   "52 animated" census of s20: 65 − 10 finger tips − HeadTop_End −
   2 Toe_End); the fixture animates all 65 channels (its generator
   keys every pose bone by design). Both satisfy the kit's channel-
   match bind guard; the census difference is a recipe choice, not a
   family law — recorded here so a future reader doesn't "fix" it.
4. Real platform clips confirmed at 30 fps with frame ranges
   1..N (17/38/500); the fixture authors 2..N+1 at 30 fps — same
   class, one-frame offset from the platform's 1-start convention
   (harmless: the kit reads `frame_range`, never hardcoded frames).

## Row provenance

- REAL clips: catalog ids 2846/2899/2781 from
  `/home/z/RH-canvas-animations` (sha-verified release binaries).
- Fixture clip: id 9002 from the offline library
  (`scripts/rh_fixture_lib.py --force` rebuilds).
- The expected-deviation whitelist in `s22_crossval.py` FAILS CLOSED on
  any NEW deviation — if the platform changes its conventions or the
  fixture generator drifts, the battery goes red here first.
