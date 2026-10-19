#!/bin/bash
# run_battery.sh — the vision-kit regression battery (the s24 restoration
# of the suite_runner that the worklog says existed at 29-40 suites but
# that the tree lost — a runner-shaped hole in the kit; every session
# re-derived a loop by hand).
#
# Usage: bash scripts/run_battery.sh [pattern]
#   pattern: optional glob filter, e.g. "test_rh*" — default all tests.
# Env: KIT_OUT (results root), BLRUN_FORCE already honored by blrun.
# Output: one line per suite + a tally; exit 0 iff no FAIL (SKIPs are
#   honest-skip exits and do not fail the battery — they print SKIP).
set -u
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"
PATTERN="${1:-test_*.py}"
LOG="${KIT_BATTERY_LOG:-/tmp/vk_battery.log}"
: > "$LOG"

SUITES=$(ls tests/${PATTERN} 2>/dev/null | sort)
PASS=0; FAIL=0; SKIP=0; FAILED_LIST=""

for t in $SUITES; do
  name=$(basename "$t")
  # Two invocation contracts live in tests/:
  #   bpy suites  -> blrun.sh (PYTHONPATH, bundled python, display lock)
  #   pure-python suites (vendored unittest, no bpy) -> host python3.
  # A bpy-less file pushed through blrun dies on unittest.main(argv)
  # consuming blrun's own flags (the s24 runner finding).
  if grep -qE "^[[:space:]]*(import bpy|from bpy)" "$t"; then
    RUNNER=(env BLRUN_FORCE=1 ./scripts/blrun.sh --background --python "tests/$name" --)
  else
    RUNNER=(python3 "tests/$name")
  fi
  # each suite gets a bounded slot; foreground (the reaping law)
  if timeout 900 "${RUNNER[@]}" > "/tmp/vk_suite_${name%.py}.log" 2>&1; then
    echo "PASS $name" | tee -a "$LOG"
    PASS=$((PASS+1))
  else
    rc=$?
    if [ $rc -eq 2 ]; then
      echo "SKIP $name (honest-skip exit 2)" | tee -a "$LOG"
      SKIP=$((SKIP+1))
    else
      echo "FAIL $name (exit $rc — log /tmp/vk_suite_${name%.py}.log)" | tee -a "$LOG"
      FAIL=$((FAIL+1)); FAILED_LIST="$FAILED_LIST $name"
    fi
  fi
done

echo "===============================" | tee -a "$LOG"
echo "BATTERY: $PASS pass / $FAIL fail / $SKIP skip  (of $(echo $SUITES | wc -w))" | tee -a "$LOG"
[ -n "$FAILED_LIST" ] && echo "failed:$FAILED_LIST" | tee -a "$LOG"
[ $FAIL -eq 0 ]
