#!/usr/bin/env bash
# suite_runner.sh — sequential regression runner, fully detached-safe.
# Each test gets its own log; failures don't stop the chain.
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
rm -f /tmp/suite.done
for t in tests/test_t1_states.py tests/test_t2_stairs.py \
         tests/test_t3_jeep.py tests/test_t4_table.py \
         tests/test_t5_physics.py tests/x1_detection_matrix.py; do
  name=$(basename "$t" .py)
  echo "[suite] running $name ..."
  ./run.sh --background --python "$t" > "/tmp/${name}.log" 2>&1
  echo "[suite] $name exit=$? ($(rg -c 'ALL PASS' /tmp/${name}.log 2>/dev/null || echo 0) pass-markers)"
done
touch /tmp/suite.done
echo "[suite] DONE"
