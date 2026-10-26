#!/bin/bash
# bake_wave_fix2.sh -- re-bake all 7 film caches (fix-wave-2 resume,
# sandbox died with all local caches). Deterministic: every pin must
# reproduce (the cross-sandbox determinism law).
# Multi-stage films run their full chain: probe -> (layers/groups ->
# interaction) -> finish. Single-stage films run once.
set -u
cd /home/z/work/blender-vision-kit
PY=/home/z/.venv/bin/python3
: > /tmp/bake_wave2.log

run() {  # run <film> <stage>
  echo "=== BAKE $1 $2 ===" >> /tmp/bake_wave2.log
  $PY scripts/${1}_bake.py --out /tmp/crowdcache_${1} --stage ${2} >> /tmp/bake_wave2.log 2>&1
  echo "[$(date +%H:%M:%S)] $1/$2 rc=$?" | tee -a /tmp/bake_wave2.log
}

# single-stage films (probe == the whole bake; pins print at the end)
for FILM in tdawn tferry tgreen; do run $FILM probe; done

# multi-stage films
run tsquall probe;  run tsquall groups;  run tsquall finish
run tfog probe;     run tfog groups;     run tfog finish
run tform probe;    run tform layers;    run tform interaction; run tform finish
run tmarket probe;  run tmarket groups;  run tmarket finish

echo "ALL BAKES DONE"
grep -aE "npz pin|payload_sha256" /tmp/bake_wave2.log
