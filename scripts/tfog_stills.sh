#!/bin/bash
# tfog_stills.sh -- one EEVEE process per shot (the OOM law), stills
# named shot_<id>.png (the package contract), mid-shot frame each.
# Written FRESH for THE EXPRESS (the clone-seam law).
set -u
cd "$(dirname "$(dirname "$(readlink -f "$0")")")"
export CROWD_CACHE_DIR=${CROWD_CACHE_DIR:-/tmp/crowdcache_tfog}
OUT=${OUT:-output/tfog/stills}
mkdir -p "$OUT"
declare -A FRAMES=( [S1]=50 [S2]=140 [S3]=270 [S4]=320 [S5]=430 [S6]=570 \
  [S7]=640 [S8]=740 [S9]=840 [S10]=910 [S11]=980 [S12]=1050 )
ONLY="${1:-}"
for SID in S1 S2 S3 S4 S5 S6 S7 S8 S9 S10 S11 S12; do
  if [ -n "$ONLY" ] && [ "$ONLY" != "$SID" ]; then continue; fi
  F=${FRAMES[$SID]}
  if [ -s "$OUT/shot_${SID}.png" ] && [ scripts/tfog_scene.py -ot "$OUT/shot_${SID}.png" ]; then echo "[stills] $SID exists (scene older), skip"; continue; fi
  echo "[stills] $SID @ f$F ..."
  ./scripts/blrun.sh --background --factory-startup \
    --python scripts/tfog_scene.py -- \
    --output output/tfog/stillwork --engine ${ENGINE:-eevee} --w 640 --h 360 \
    --still $F --samples ${SAMPLES:-32} > /tmp/still_tf_$SID.log 2>&1
  rc=$?
  if [ $rc -ne 0 ] || [ ! -s output/tfog/stillwork/still_$(printf %05d $F).png ]; then
    echo "[stills] $SID FAILED rc=$rc (see /tmp/still_tf_$SID.log)"; continue
  fi
  mv output/tfog/stillwork/still_$(printf %05d $F).png "$OUT/shot_${SID}.png"
  echo "[stills] $SID ok"
done
echo "[stills] DONE -> $OUT"
