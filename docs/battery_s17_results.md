# battery_s17 — session-17 full regression receipt (29 suites)

> Ran 29/29 PASS across 4 foreground batches (suite_runner.sh,
> per-suite timeout 600 s). One mid-run fix pair (look.py F2A-15 hint
> distance; edge_tall.py red-by-construction hover) — the affected suite
> (test_v3_edges) was re-run post-fix (batch b1r). All rows at tip 91aa854.

| # | suite | expected marker | exit | verdict | notable |
|---|-------|-----------------|------|---------|---------|
| 1 | tests/t8_placement_diorama.py | `\[T8\] ([0-9]+)/\1 checks passed` | 0 | **PASS** | battery #11; marker needs N/N equal (suite always exits 0) |
| 2 | tests/t9_chaos_fuzz.py | `CHAOS: 0 hard failures` | 0 | **PASS** | battery #12 |
| 3 | tests/test_f17_gridrefine.py | `\[test_f17\] ALL PASS` | 0 | **PASS** | battery #13 |
| 4 | tests/test_f22_levels.py | `\[test_f22\] ALL PASS` | 0 | **PASS** | battery #14 |
| 5 | tests/test_kit_scope.py | `test_kit_scope: PASS` | 0 | **PASS** | battery #1 (exit 1 there = stale tracked file, resolved) |
| 6 | tests/test_r7_route.py | `ALL PASS` | 0 | **PASS** | battery #21 (pure python per header) |
| 7 | tests/test_r8_seat.py | `\[test_r8\] ALL PASS` | 0 | **PASS** | battery #22 |
| 8 | tests/test_r9_chunking.py | `ALL PASS` | 0 | **PASS** | battery #23 |
| 9 | tests/test_s17_infra.py | `\[test_s17i\] ALL PASS` | 0 | **PASS** | session-17 wave-D infra regressions (this repo's infra fixes) |
| 10 | tests/test_s17_wave_a.py | `\[test_s17\] ALL PASS` | 0 | **PASS** | session-17 wave-A regressions |
| 11 | tests/test_s17_wave_b.py | `\[test_s17b\] ALL PASS` | 0 | **PASS** | session-17 wave-B regressions (in-Blender) |
| 12 | tests/test_t10_export.py | `\[t10\] ALL PASS` | 0 | **PASS** | battery #26 |
| 13 | tests/test_t10_preflight_prop.py | `\[t10p\] ALL PASS` | 0 | **PASS** | battery #25 (pure python, no blender) |
| 14 | tests/test_t1_states.py | `ALL PASS` | 0 | **PASS** | battery #15 (bare verdict marker; suite always exits 0) |
| 15 | tests/test_t2_stairs.py | `ALL PASS` | 0 | **PASS** | battery #16 (bare verdict marker; suite always exits 0) |
| 16 | tests/test_t3_jeep.py | `ALL PASS` | 0 | **PASS** | battery #17 (bare verdict marker; suite always exits 0) |
| 17 | tests/test_t4_table.py | `ALL PASS` | 0 | **PASS** | battery #18 (bare verdict marker; suite always exits 0) |
| 18 | tests/test_t5_physics.py | `\[T5\] ALL PASS` | 0 | **PASS** | battery #19 |
| 19 | tests/test_t6_add_ops.py | `\[T6\] ALL PASS` | 0 | **PASS** | battery #20 (direct blender bin inside; run.sh exports BLENDER_BIN) |
| 20 | tests/test_usd_carrier.py | `\[test_usd_carrier\] ALL PASS` | 0 | **PASS** | battery #24 (export_textures kwarg fixed post-battery; pxr half may print SKIP) |
| 21 | tests/test_v1_look.py | `test_v1_look: ALL PASS` | 0 | **PASS** | battery #2 |
| 22 | tests/test_v2_motion.py | `test_v2_motion: ALL PASS` | 0 | **PASS** | battery #3 (rc=90 then; BLRUN_FORCE=1 in-code now) |
| 23 | tests/test_v3_edges.py | `ALL PASS` | 0 | **PASS** | battery #4 (rc=90 then; BLRUN_FORCE=1 in-code now) |
| 24 | tests/test_v4_colorsync.py | `\[V4\] ALL PASS` | 0 | **PASS** | battery #5 (S8 rc=90 then; BLRUN_FORCE=1 in-code now) |
| 25 | tests/test_v5_labeling.py | `\[test_v5\] ALL PASS` | 0 | **PASS** | battery #6 |
| 26 | tests/test_v6_manifestdiff.py | `\[test_v6\] ALL PASS` | 0 | **PASS** | battery #7 (pure python per header) |
| 27 | tests/test_v7_camprobe.py | `\[V7\] ALL PASS` | 0 | **PASS** | battery #8 (rc=90 then; BLRUN_FORCE=1 in-code now) |
| 28 | tests/test_v8_material.py | `\[V8\] ALL PASS` | 0 | **PASS** | battery #9 |
| 29 | tests/test_v9_fixes_s16.py | `\[test_v9\] ALL PASS` | 0 | **PASS** | battery #10 |

- **PASS: 29 / 29** — FAIL: 0.
- New session-17 suites: test_s17_wave_a (21 checks), test_s17_wave_b,
  test_s17_infra (18); t10 prop grew 100→124 checks; t10 export 19→25
  (adds the --usd-sidecar RNA-filter proof on 5.2.2).
- Logs: output/battery_{b1,b1r,b2,b3,b4}/logs/ (sandbox-local); this file
  is the durable copy (F2D-6: the s16 receipt only had the pre-fix run).

## Addendum — wave-2 verification round (post-receipt)

The wave-2 fresh-context audit (docs/audit_s17/5a_wave2_verification.md)
found 4× P2 "twins" + 1 real regression (seat_at scale). Wave F fixed
all of them; the affected suites re-ran GREEN: test_s17_wave_a (25/25,
extended), s17b, s17i, t10p, t8, t3, t5, v9, f17, t9 — 10 suites, 0
failures. The 29/29 table above therefore holds for the final tip
(post-5c39b86); the two mid-session fix pairs (b1r, wave F) are the
documented exceptions to the single-run receipt. Open P3 residue is
definitively listed in the 5a file (10 items — below the exhaustion
bar per the session mandate).
