# Regression battery — session-16 (Task 5-b)

Run date: (auto-filled per suite below)
Machine: 2 cores, ~4 GB RAM (OOM watch active; blrun F-TD10 display lock enforces serial).
Runner: `cd /home/z/repos/blender-vision-kit && ./scripts/blrun.sh --background --python <suite> ...` (foreground, 600s timeout each).
Rules honored: serial only, no files edited, nothing committed. Logs: `output/battery_s16/logs/<name>.log`.

| # | suite | marker | verdict | notable |
|---|-------|--------|---------|---------|
| 1 | tests/test_kit_scope.py | `1 FORBIDDEN PATHS TRACKED IN KIT` (exit 1) | **FAIL** | `scripts/probe_crowd_bake.py` is git-tracked, matches forbidden prefix `^scripts/(probe_)` — repo-hygiene gate; likely added in session-16 |
| 2 | tests/test_v1_look.py | `test_v1_look: ALL PASS` (exit 0) | PASS | 27/27 checks passed |
| 3 | tests/test_v2_motion.py | `test_v2_motion: FAIL` (exit 0 w/ marker) | **FAIL** | 23/27; 4 fails all from check-6 nested `blrun.sh transient_scan` subprocess → `rc=90` (blrun F-TD10 display-lock held by the OUTER blrun). v1 avoids this by calling the blender binary directly; v2 calls nested blrun. Downstream: glitch-table/PERSISTENT/suspects-strip all unverified |
| 4 | tests/test_v3_edges.py | `EDGES: 12/20 PASS` (exit 1) | **FAIL** | 8/8 subprocess-exit checks fail with `rc=90` — every case spawns nested `blrun.sh` (C1–C4 look, D1–D4 motion/scan) which cannot take the display lock held by the outer blrun. "no traceback" halves all PASS; exit-code halves fail on rc=90 |
| 5 | tests/test_v4_colorsync.py | (no final marker; suite crashed) `FAIL-CLOSED … nonzero exit` (exit 1) | **FAIL** | S1–S7 all PASS (19 checks). S8 end-to-end spawns nested `blrun.sh look.py` → rc=90 lock → manifest missing → `FileNotFoundError: …/v4/look/look_manifest.json` → crash; same nested-blrun-lock mechanism as v2/v3 |
| 6 | tests/test_v5_labeling.py | `[test_v5] ALL PASS` (exit 0) | PASS | L1–L18, 63 per-check lines, in-process only (no nested blrun) |
| 7 | tests/test_v6_manifestdiff.py (pure python per header) | `[test_v6] ALL PASS` (exit 0) | PASS | M1–M10 incl. rotation-bbox law, nonmesh, legacy fallback |
| 8 | tests/test_v7_camprobe.py | (no final marker) `FAIL-CLOSED … nonzero exit` (exit 1) | **FAIL** | 7 [FAIL]s: every look.py probe subprocess is nested `blrun.sh` → `got=90 expect=0` (V7a/V7k/V7n exit checks + downstream V7b/c/l/m). Same display-lock mechanism; 0 explicit [PASS] lines printed before crash |
| 9 | tests/test_v8_material.py | `[V8] ALL PASS` (exit 0) | PASS | emission pin/decouple contract, _safe_socket_set — in-process |
| 10 | tests/test_v9_fixes_s16.py | `[test_v9] ALL PASS` (exit 0) | PASS | session-16 fixes green: F19 ack_many_parts, scoped-audit STATE-enum law, F-TD5 render_hidden depsgraph sweep |
| 11 | tests/t8_placement_diorama.py (--output output/battery_s16/t8_placement_diorama) | `[T8] 8/8 checks passed` (exit 0; C1–C4 green) | PASS | EEVEE renders OK, no OOM; blend + seam/heat/section diagnostics written |
| 12 | tests/t9_chaos_fuzz.py (--output output/battery_s16/t9_chaos_fuzz) | `CHAOS: 0 hard failures across 14 rounds + 4 seat checks` + `ALL PASS` (exit 0) | PASS | R1–R7 perturbation classes + S1–S3 seat-at edges all green |
| 13 | tests/test_f17_gridrefine.py | `[test_f17] ALL PASS` (exit 0) | PASS | F1–F4 incl. narrow-leg dogfood repro + 1cm pin at 48x48 |
| 14 | tests/test_f22_levels.py | `[test_f22] ALL PASS` (exit 0) | PASS | F22.1–F22.5 level-adjacency/containment/escape policy |
| 15 | tests/test_t1_states.py | `[T1] ALL PASS` (exit 0) | PASS | R2 7-state ground truth via pair_contact (t1_results.json) |
| 16 | tests/test_t2_stairs.py | `[T2] ALL PASS` (exit 0) | PASS | stair place_on exact/5mm/sabotage/height-map/multi-level |
| 17 | tests/test_t3_jeep.py | `[T3] ALL PASS` (exit 0) | PASS | seat_at/stand/sabotage/seam/heat/viewport renders all green |
| 18 | tests/test_t4_table.py | `[T4] ALL PASS` (exit 0) | PASS | table+mug classic-failure fixture incl. intentional 20mm pole bug detection |
| 19 | tests/test_t5_physics.py | `[T5] FAILURES: 0` + `[T5] ALL PASS` (exit 0) | PASS | a–g+r: settle/repair/oracle/gate/determinism/animated-refuse/margin-sum law |
| 20 | tests/test_t6_add_ops.py | `[T6] ALL PASS` (exit 0) | PASS | add-op surface + apply_patch subprocess (direct blender bin, not nested blrun) |
| 21 | tests/test_r7_route.py (pure python per header) | `ALL PASS` (exit 0) | PASS | direction-inference/vision-override/slab-clamp/bed-avoidance cases |
| 22 | tests/test_r8_seat.py | `[test_r8] ALL PASS` (exit 0) | PASS | R8 seat-protocol regressions |
| 23 | tests/test_r9_chunking.py (-- out=output/battery_s16/r9_chunking) | `ALL PASS` (exit 0) | PASS | chunked-blend carrier round-trip incl. semantics/world/compositor/collections |
| 24 | tests/test_usd_carrier.py | `[test_usd_carrier] FAIL: usd_export kwarg error … keyword "export_textures" unrecognized` (exit 1, FAIL-CLOSED) | **FAIL** | Early-abort after hook-registration check: `export_usd`/`previz_usd_hook` passes `export_textures` to `bpy.ops.wm.usd_export`, which this Blender build (5.2.2 LTS) rejects. First REAL code-level failure of the battery — candidate session-16 regression (export path) |
| 25 | tests/test_t10_preflight_prop.py (pure python, no blender) | `98 checks, 0 failed` + `[t10p] ALL PASS` (exit 0) | PASS | D19 preflight contracts incl. SHOTS_V3 row-shape reject messages |
| 26 | tests/test_t10_export.py (-- out=output/battery_s16/t10_export) | `[t10] ALL PASS` (exit 0) | PASS | 19 checks: export_previz_package end-to-end, glb_exists etc. — GLB lane green (the USD-lane kwarg failure in suite 24 did not recur here) |

## Verdict (battery s16)

- **PASS: 20 / 26** — suites 2, 6, 7, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 25, 26.
- **FAIL: 6** — suites 1, 3, 4, 5, 8, 24 (see table).
- **SKIP-not-found: 0** — all 26 suite files existed.

### Failure classes

1. **REAL regression candidate (fix me):**
   - `tests/test_usd_carrier.py` (suite 24): `usd_export` called with kwarg `export_textures` that Blender 5.2.2 LTS RNA rejects → `FAIL: usd_export kwarg error … keyword "export_textures" unrecognized`. This is a code-level break in the export path (export_usd.py / previz_usd_hook.py), not a harness artifact.

2. **Repo-hygiene gate (fix before commit):**
   - `tests/test_kit_scope.py` (suite 1): `scripts/probe_crowd_bake.py` is git-tracked in the kit repo and matches the forbidden `^scripts/(probe_)` prefix → `1 FORBIDDEN PATHS TRACKED IN KIT`, exit 1.

3. **Harness artifact — nested blrun under outer blrun display-lock (NOT session-16 code):**
   - Suites 3 (v2_motion), 4 (v3_edges), 5 (v4_colorsync S8), 8 (v7_camprobe) all spawn *nested* `blrun.sh` subprocesses. The outer `blrun.sh` holds the F-TD10 flock (fd 9) for its whole lifetime, so every nested blrun exits **rc=90 (LOCK-HELD)** with empty stdout: v2 23/27, v3 12/20 (all C/D exit-code checks), v4 S1–S7 pass then S8 crash on missing manifest, v7 0/7 subprocess probes. Suites that call the blender binary directly (v1, t6) pass under the same protocol, which isolates the cause to the lock, not the code. Historical precedent: these suites pass when the outer runner is the raw blender binary (v1-style) — rerun recommendation in next actions.
   - No OOM events; all EEVEE renders completed on the 4 GB box.

### Notes
- All 26 suites were run SERIALLY in the foreground (600s timeout each); full logs in `output/battery_s16/logs/*.log`; per-suite artifacts in `output/battery_s16/{t8_placement_diorama,t9_chaos_fuzz,r9_chunking,t10_export}/`.
- Nothing was edited in the repo, nothing committed.

