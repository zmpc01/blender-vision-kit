#!/usr/bin/env bash
# suite_runner.sh — THE full-battery regression runner (session-17 wave-D).
#
# ██ REAPING LAW (SKILL.md §L181) — READ BEFORE RUNNING ██
#   Background processes are KILLED between tool calls: nohup/setsid/& DO
#   NOT survive. This runner MUST be invoked inside ONE foreground tool
#   call with a generous timeout, e.g.:
#       cd /home/z/repos/blender-vision-kit && bash scripts/suite_runner.sh
#   (4 GB box, 26+ suites × up to --timeout seconds each — size the tool
#   timeout for the FULL serial run, or run --only <suite> in batches.)
#   A run that "stops mid-suite with no error" was REAPED, not failed.
#   The old header's "fully detached-safe" claim was FALSE and is gone.
#
# What this does (replaces the stale 6-suite subset — F2E-11):
#   * enumerates the WHOLE battery: the 26 suites recorded in
#     docs/battery_s16_results.md PLUS tests/test_s17_wave_a.py,
#     tests/test_s17_wave_b.py, tests/test_s17_infra.py;
#   * runs every suite SERIALLY in the FOREGROUND with a per-suite
#     timeout (default 600s, matching the battery convention);
#   * writes per-suite logs to output/battery_<label>/logs/<name>.log;
#   * writes output/battery_<label>/RESULTS.md — a summary table in the
#     same shape as docs/battery_s16_results.md (suite / expected marker /
#     exit code / PASS-FAIL / notable).
#
# Usage:
#   bash scripts/suite_runner.sh --list            # print suites + per-suite
#                                                  # invocation args, exit 0
#   bash scripts/suite_runner.sh [--label s17] [--timeout 600]
#                                [--only NAME]... [--skip NAME]...
#
# Notes:
#   * Per-suite args are copied from the battery doc's rows (t8/t9 use
#     `-- --output output/<label>/...`, r9/t10-export use `-- out=...`);
#     expected exit + expected marker are encoded per suite below.
#   * Suites that NEST blrun already carry BLRUN_FORCE=1 in-code
#     (test_v2_motion.py:204, test_v3_edges.py:57, test_v4_colorsync.py:180,
#     test_v7_camprobe.py:106) — the battery's rc=90 failures motivated it.
#   * test_kit_scope.py: exit 0 = clean tree (its own header: "Exit 0 =
#     clean"). The battery's row 1 recorded exit 1 because a stale
#     scripts/probe_crowd_bake.py was tracked then (resolved at HEAD).
#   * A suite file that does not exist yet (e.g. test_s17_wave_b.py from a
#     parallel wave) is recorded as SKIP-NOT-FOUND, matching the battery
#     doc's verdict class — never silently dropped.
#   * Suite-requested SKIP sentinel (F7, session-19): a suite that could
#     not run must exit 2 AND print a line matching `SUITE-SKIP:` OR
#     `[<its own suite tag>] ...SKIP` — the tag is the SUITES row's name
#     (also the log basename), e.g. test_usd_carrier's
#     "[test_usd_carrier] SKIP: pxr not importable ...". The old loose
#     `] SKIP` substring match counted ANY log line (blrun's own
#     "[blrun] SKIP --warm-cache" note, a checker echoing the word) and
#     re-classed genuine FAILs as SKIP — only the sentinel counts now.

cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" || exit 1

LABEL="s17"
TIMEOUT="600"
ONLY=()
SKIP=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --list) LIST=1; shift ;;
        # F3 (session-19): a value-taking flag as the LAST arg used to
        # loop forever ($2 unset, `shift 2` a no-op — verified exit 124).
        --label) [[ $# -ge 2 ]] || { echo "[suite] --label needs a value"; exit 2; }; LABEL="$2"; shift 2 ;;
        --timeout) [[ $# -ge 2 ]] || { echo "[suite] --timeout needs a value"; exit 2; }; TIMEOUT="$2"; shift 2 ;;
        --only) [[ $# -ge 2 ]] || { echo "[suite] --only needs a value"; exit 2; }; ONLY+=("$2"); shift 2 ;;
        --skip) [[ $# -ge 2 ]] || { echo "[suite] --skip needs a value"; exit 2; }; SKIP+=("$2"); shift 2 ;;
        *) echo "[suite] unknown arg: $1 (see header)"; exit 2 ;;
    esac
done

# ----------------------------------------------------------------------------
# The battery: name|path|mode|args-template|expected_exit|marker_regex|note
# mode: PY = python3 <path> (suite header documents direct python3);
#       BL = scripts/blrun.sh --background --python <path> [args]
# args-template: {label} interpolates $LABEL; empty for most suites.
# ----------------------------------------------------------------------------
SUITES=(
  "test_kit_scope|tests/test_kit_scope.py|PY||0|test_kit_scope: PASS|battery #1 (exit 1 there = stale tracked file, resolved)"
  "test_v1_look|tests/test_v1_look.py|BL||0|test_v1_look: ALL PASS|battery #2"
  "test_v2_motion|tests/test_v2_motion.py|BL||0|test_v2_motion: ALL PASS|battery #3 (rc=90 then; BLRUN_FORCE=1 in-code now)"
  "test_v3_edges|tests/test_v3_edges.py|BL||0|ALL PASS|battery #4 (rc=90 then; BLRUN_FORCE=1 in-code now)"
  "test_v4_colorsync|tests/test_v4_colorsync.py|BL||0|\\[V4\\] ALL PASS|battery #5 (S8 rc=90 then; BLRUN_FORCE=1 in-code now)"
  "test_v5_labeling|tests/test_v5_labeling.py|BL||0|\\[test_v5\\] ALL PASS|battery #6"
  "test_v6_manifestdiff|tests/test_v6_manifestdiff.py|PY||0|\\[test_v6\\] ALL PASS|battery #7 (pure python per header)"
  "test_v7_camprobe|tests/test_v7_camprobe.py|BL||0|\\[V7\\] ALL PASS|battery #8 (rc=90 then; BLRUN_FORCE=1 in-code now)"
  "test_v8_material|tests/test_v8_material.py|BL||0|\\[V8\\] ALL PASS|battery #9"
  "test_v9_fixes_s16|tests/test_v9_fixes_s16.py|BL||0|\\[test_v9\\] ALL PASS|battery #10"
  "t8_placement_diorama|tests/t8_placement_diorama.py|BL|-- --output output/{label}/t8|0|\\[T8\\] 8/8 checks passed|battery #11 (marker = the exact all-pass literal since wave-E E6 — no grep backref; suite exits 1 on failure since E5, so the exit code is authoritative too)"
  "t9_chaos_fuzz|tests/t9_chaos_fuzz.py|BL|-- --output output/{label}/t9_chaos_fuzz|0|CHAOS: 0 hard failures|battery #12"
  "test_f17_gridrefine|tests/test_f17_gridrefine.py|BL||0|\\[test_f17\\] ALL PASS|battery #13"
  "test_f22_levels|tests/test_f22_levels.py|BL||0|\\[test_f22\\] ALL PASS|battery #14"
  "test_t1_states|tests/test_t1_states.py|BL||0|ALL PASS|battery #15 (bare verdict marker; exits 1 on failure since wave-E E5)"
  "test_t2_stairs|tests/test_t2_stairs.py|BL||0|ALL PASS|battery #16 (bare verdict marker; exits 1 on failure since wave-E E5)"
  "test_t3_jeep|tests/test_t3_jeep.py|BL||0|ALL PASS|battery #17 (bare verdict marker; exits 1 on failure since wave-E E5)"
  "test_t4_table|tests/test_t4_table.py|BL||0|ALL PASS|battery #18 (bare verdict marker; exits 1 on failure since wave-E E5)"
  "test_t5_physics|tests/test_t5_physics.py|BL||0|\\[T5\\] ALL PASS|battery #19"
  "test_t6_add_ops|tests/test_t6_add_ops.py|BL||0|\\[T6\\] ALL PASS|battery #20 (direct blender bin inside; run.sh exports BLENDER_BIN)"
  "test_r7_route|tests/test_r7_route.py|PY||0|ALL PASS|battery #21 (pure python per header)"
  "test_r8_seat|tests/test_r8_seat.py|BL||0|\\[test_r8\\] ALL PASS|battery #22"
  "test_r9_chunking|tests/test_r9_chunking.py|BL|-- out=output/{label}/r9_chunking|0|ALL PASS|battery #23"
  "test_usd_carrier|tests/test_usd_carrier.py|BL||0|\\[test_usd_carrier\\] ALL PASS|battery #24 (export_textures kwarg fixed post-battery; pxr-less path exits 2 with a SKIP line since wave-E E9 → row reads SKIP, not FAIL)"
  "test_t10_preflight_prop|tests/test_t10_preflight_prop.py|PY||0|\\[t10p\\] ALL PASS|battery #25 (pure python, no blender)"
  "test_t10_export|tests/test_t10_export.py|BL|-- out=output/{label}/t10_export|0|\\[t10\\] ALL PASS|battery #26"
  "test_s17_wave_a|tests/test_s17_wave_a.py|BL||0|\\[test_s17\\] ALL PASS|session-17 wave-A regressions"
  "test_s17_wave_b|tests/test_s17_wave_b.py|BL||0|\\[test_s17b\\] ALL PASS|session-17 wave-B regressions (in-Blender)"
  "test_s17_infra|tests/test_s17_infra.py|PY||0|\\[test_s17i\\] ALL PASS|session-17 wave-D infra regressions (this repo's infra fixes)"
  "x1_detection_matrix|tests/x1_detection_matrix.py|BL||0|\\[X1\\] ALL PASS|session-18 wave-E E4: BVH contact-audit regression fixture (bbox rows are the KNOWN-bad baseline — only BVH/binary-mismatch regressions fail)"
  "test_s18_eyes|tests/test_s18_eyes.py|BL||0|test_s18_eyes: ALL PASS|session-18 wave-E E2: look exit-4 / camera_intent / build_sfx vocabulary coverage"
  "test_s18_wave_b|tests/test_s18_wave_b.py|BL||0|\\[test_s18b\\] ALL PASS|session-18 wave-B regressions (in-Blender: duplicate_object refuse, SystemExit chain-abort save, NaN param refuses, audit scope refuse, schema dof+exposure, validate_scene animate bind, split_mesh per-mode params)"
  "test_s18_wave_c|tests/test_s18_wave_c.py|BL||0|\\[S18C\\] ALL PASS|session-18 wave-C regressions (in-Blender: C1 rotation-key guard+rebase, C2 animated exclusion, C3/C4 modifiers+SimBake bake guards, C6/C7 skinned guards, C9 grid align-to-surface, C10 mode tokens, C11 contact discs, C12 prop_carry quaternion keys)"
  "test_s18_wave_d|tests/test_s18_wave_d.py|BL||0|\\[S18D\\] ALL PASS|session-18 wave-D regressions (D1 threaded server, D3 RNA-filter op ids, D4 USD parity counts, D5 gate-5 CAST root, D6/D7 encode guards, D8 staleness matcher, D9 sfx negative frames, D10 watcher stability, D12 scene.json; MIXED suite — bpy-guarded sections degrade to textual under plain python3)"
  "test_s19_wave_pins|tests/test_s19_wave_pins.py|BL||0|\\[test_s19p\\] ALL PASS|session-19 fix pins (red-by-construction; s18 A6 + s19 wave-A: NaN/_nonneg_mm/frames guards, set_rotation mode channel, override token, anim guards, align idempotence, fill_frac, heat_bake bands, sample/engine tokens, skinned snap_z, stale-depsgraph audit)"
  "test_crowd_e2e|tests/test_crowd_e2e.py|PY||0|\\[CROUDE2E\\] ALL PASS|M3 r149: crowd-kit end-to-end gate (wheel sha256+size vs README pin F2E-12, native import+version coherence, vendored submodule kit import+__version__ coherence, 5-agent bake complete into fresh tempdir; provision: blender_crowd_native importable per wheels/README law)"
  "test_rh_canvas|tests/test_rh_canvas.py|BL||0|\[rh-test\] ALL PASS|s20 vendor: RH-canvas mocap path battery R1-R8b (catalog/fetch-verify/import-clip laws/mannequin/bind channel-match+registry/G statue/GLB round-trip/armature placement e2e; graceful-skip when the RH library clones are absent)"
  "test_rh_fixture|tests/test_rh_fixture.py|BL||0|\\[test_rh_fix\\] ALL PASS|s20: the rh_canvas surface battery vs the OFFLINE fixture library (catalog/tags/frames data-driven, fetch-verify+poison-repair, import laws vs self-verifying truth.json, mannequin census, bind+playback, refusals, swap-unpin, registry fingerprint, statue ground band, GLB round-trip, placement ARMATURE branches, ensemble)"
)

loud_header() {
    cat <<'HDR'
================================================================================
██ REAPING LAW (SKILL.md §L181): background processes are KILLED between tool
██ calls. Run this runner inside ONE foreground tool call with a generous
██ timeout — a run that "just stops" mid-suite was REAPED, not failed.
================================================================================
HDR
}

# ---- --list: print the suite list + per-suite invocation args, then exit ----
if [[ "${LIST:-}" == "1" ]]; then
    loud_header
    echo "battery label: $LABEL  |  per-suite timeout: ${TIMEOUT}s  |  suites: ${#SUITES[@]}"
    echo
    n=0
    for row in "${SUITES[@]}"; do
        IFS='|' read -r name path mode args _exp _marker note <<< "$row"
        n=$((n + 1))
        args="${args//\{label\}/$LABEL}"
        if [[ "$mode" == "PY" ]]; then
            printf '%2d. %-24s [PY] python3 %s\n' "$n" "$name" "$path"
        else
            if [[ -n "$args" ]]; then
                printf '%2d. %-24s [BL] scripts/blrun.sh --background --python %s %s\n' "$n" "$name" "$path" "$args"
            else
                printf '%2d. %-24s [BL] scripts/blrun.sh --background --python %s\n' "$n" "$name" "$path"
            fi
        fi
        echo "      expect: exit ${_exp} + /${_marker}/   (${note})"
    done
    exit 0
fi

OUT_DIR="output/battery_${LABEL}"
LOG_DIR="${OUT_DIR}/logs"
RESULTS_MD="${OUT_DIR}/RESULTS.md"
mkdir -p "$LOG_DIR"

wanted() {  # --only filter (empty ONLY = all)
    local name="$1"
    [[ ${#ONLY[@]} -eq 0 ]] && return 0
    local o; for o in "${ONLY[@]}"; do [[ "$o" == "$name" ]] && return 0; done
    return 1
}
skipped() {
    local name="$1"
    local s; for s in "${SKIP[@]}"; do [[ "$s" == "$name" ]] && return 0; done
    return 1
}

loud_header
echo "[suite] label=$LABEL  per-suite timeout=${TIMEOUT}s  suites=${#SUITES[@]}  logs=${LOG_DIR}/"
echo "[suite] FULL SERIAL RUN — do not background this (see header above)"

ROWS=()
NPASS=0; NFAIL=0; NSKIP=0
n=0
for row in "${SUITES[@]}"; do
    IFS='|' read -r name path mode args exp marker note <<< "$row"
    n=$((n + 1))
    if ! wanted "$name" || skipped "$name"; then
        ROWS+=("| $n | $path | \`$marker\` | — | SKIP (requested) | --only/--skip filter |")
        NSKIP=$((NSKIP + 1))
        echo "[suite] $n/$(( ${#SUITES[@]} )) SKIP (requested): $name"
        continue
    fi
    if [[ ! -f "$path" ]]; then
        ROWS+=("| $n | $path | \`$marker\` | — | SKIP-NOT-FOUND | suite file missing (parallel wave may not have landed) |")
        NSKIP=$((NSKIP + 1))
        echo "[suite] $n/$(( ${#SUITES[@]} )) SKIP-NOT-FOUND: $path"
        continue
    fi
    args="${args//\{label\}/$LABEL}"
    log="${LOG_DIR}/${name}.log"
    echo "[suite] $n/$(( ${#SUITES[@]} )) running $name (timeout ${TIMEOUT}s) → $(basename "$log")"
    if [[ "$mode" == "PY" ]]; then
        timeout "$TIMEOUT" python3 "$path" > "$log" 2>&1
    else
        if [[ -n "$args" ]]; then
            timeout "$TIMEOUT" bash scripts/blrun.sh --background --python "$path" $args > "$log" 2>&1
        else
            timeout "$TIMEOUT" bash scripts/blrun.sh --background --python "$path" > "$log" 2>&1
        fi
    fi
    rc=$?
    rc_ok=0; marker_ok=0; notable=""
    [[ "$rc" == "$exp" ]] && rc_ok=1
    if grep -Eq "$marker" "$log" 2>/dev/null; then marker_ok=1; fi
    if [[ $rc -eq 124 ]]; then
        notable="TIMEOUT after ${TIMEOUT}s (killed by runner)"
    elif [[ $rc_ok -eq 0 ]]; then
        notable="exit=$rc expected=$exp"
    elif [[ $marker_ok -eq 0 ]]; then
        notable="exit ok but expected marker missing"
    fi
    # E9 (session-18 wave-E) + F7 (session-19): a suite that could not
    # run (pxr-less etc.) exits 2 with a dedicated skip SENTINEL — a log
    # line matching `SUITE-SKIP:` or `[<its own suite tag>] ...SKIP`
    # (see the header note). The old bare `] SKIP` substring matched ANY
    # line (e.g. blrun's warm-cache note) and re-classed FAILs as SKIP.
    if [[ $rc -eq 2 ]] && grep -Eq "SUITE-SKIP:|\[${name}\] .*SKIP" "$log" 2>/dev/null; then
        notable="suite requested SKIP (exit 2 + sentinel line: 'SUITE-SKIP:' or '[${name}] …SKIP')"
        verdict="SKIP (suite-requested)"; NSKIP=$((NSKIP + 1))
        echo "[suite]   SKIP (suite requested: exit 2 + sentinel line)"
    elif [[ $rc_ok -eq 1 && $marker_ok -eq 1 ]]; then
        verdict="**PASS**"; NPASS=$((NPASS + 1))
        echo "[suite]   PASS (exit=$rc, marker found)"
    else
        verdict="**FAIL**"; NFAIL=$((NFAIL + 1))
        echo "[suite]   FAIL — ${notable:-see log}"
    fi
    ROWS+=("| $n | $path | \`$marker\` | $rc | $verdict | ${notable:-$note} |")
done

# ---- E3 (session-18 wave-E): --only must never fake a green run ----
# An --only name that matches no SUITES row ran 0 suites; with the old
# code the run ended DONE/exit 0 — indistinguishable from all-green.
if [[ ${#ONLY[@]} -gt 0 && $((NPASS + NFAIL)) -eq 0 ]]; then
    echo "[suite] --only matched no suite: ${ONLY[*]}"
    # F6 (session-19): a stale RESULTS.md from an earlier full run sits
    # next to this dead run looking authoritative — overwrite it with a
    # tombstone pointing at stdout before the exit-2.
    {
        echo "# Regression battery — ${LABEL} (suite_runner.sh)"
        echo
        echo "Run date: $(date -Is)"
        echo "NO RESULTS — \`--only ${ONLY[*]}\` matched no suite (exit 2). See stdout."
    } > "$RESULTS_MD"
    exit 2
fi

# ---- RESULTS.md — same shape as docs/battery_s16_results.md ----
{
    echo "# Regression battery — ${LABEL} (suite_runner.sh)"
    echo
    echo "Run date: $(date -Is)"
    echo "Machine: 2 cores, ~4 GB RAM (OOM watch active; blrun F-TD10 display lock enforces serial)."
    echo "Runner: \`bash scripts/suite_runner.sh --label ${LABEL} --timeout ${TIMEOUT}\` (foreground, one tool call — REAPING LAW: SKILL.md §L181)."
    echo "Rules honored: serial only, per-suite timeout ${TIMEOUT}s. Logs: \`${LOG_DIR}/<name>.log\`."
    echo
    echo "| # | suite | expected marker | exit code | verdict | notable |"
    echo "|---|-------|-----------------|-----------|---------|---------|"
    for r in "${ROWS[@]}"; do echo "$r"; done
    echo
    echo "## Verdict (${LABEL})"
    echo
    echo "- **PASS: ${NPASS} / $(( ${#SUITES[@]} ))** — SKIP/SKIP-NOT-FOUND: ${NSKIP}, FAIL: ${NFAIL}."
    if [[ $NFAIL -gt 0 ]]; then
        echo "- FAIL rows above: read \`$LOG_DIR/<name>.log\` — a missing marker with a clean exit"
        echo "  usually means the suite crashed BEFORE its verdict (grep the log for Traceback)."
    fi
    echo
    echo "### Reminder"
    echo
    echo 'This file was written by ONE foreground tool call. If the run died mid-table,'
    echo 'the sandbox reaper killed the runner (reaping law) — re-run in --only batches.'
} > "$RESULTS_MD"

echo
echo "[suite] DONE — PASS=${NPASS} FAIL=${NFAIL} SKIP=${NSKIP}"
echo "[suite] results: $RESULTS_MD"
[[ $NFAIL -eq 0 ]] || exit 1
