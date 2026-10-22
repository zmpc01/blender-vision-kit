#!/bin/bash
# tmarket_stills.sh -- one process per shot (the OOM law), stills named
# shot_<id>.png (the package contract), mid-shot frame each.
# The s27 engine-map law: ENGINE defaults to cycles and the scene
# module's Cycles branch is the CANONICAL path (this film is born
# under the corrected engine map).
set -u
cd "$(dirname "$(dirname "$(readlink -f "$0")")")"
export CROWD_CACHE_DIR=${CROWD_CACHE_DIR:-/tmp/crowdcache_tmarket}
export TMARKET_HUMANOID=${TMARKET_HUMANOID:-1}
export RH_ASSETS=${RH_ASSETS:-/home/z/lab/RH-3d-assets}
OUT=output/tmarket/stills
mkdir -p "$OUT"
declare -A FRAMES=( [S1]=42 [S2]=126 [S3]=220 [S4]=300 [S5]=400 [S6]=470 \
  [S7]=580 [S8]=660 [S9]=760 [S10]=860 [S11]=960 [S12]=1044 )
ONLY="${1:-}"
for SID in S1 S2 S3 S4 S5 S6 S7 S8 S9 S10 S11 S12; do
  if [ -n "$ONLY" ] && [ "$ONLY" != "$SID" ]; then continue; fi
  F=${FRAMES[$SID]}
  if [ -s "$OUT/shot_${SID}.png" ]; then echo "[stills] $SID exists, skip"; continue; fi
  echo "[stills] $SID @ f$F ..."
  ./scripts/blrun.sh --background --factory-startup \
    --python scripts/scene_night_market.py -- \
    --output output/tmarket/stillwork --engine ${ENGINE:-cycles} --w 640 --h 360 \
    --still $F --samples ${SAMPLES:-24} > /tmp/still_$SID.log 2>&1
  rc=$?
  if [ $rc -ne 0 ] || [ ! -s output/tmarket/stillwork/still_$(printf %05d $F).png ]; then
    echo "[stills] $SID FAILED rc=$rc (see /tmp/still_$SID.log)"; continue
  fi
  mv output/tmarket/stillwork/still_$(printf %05d $F).png "$OUT/shot_${SID}.png"
  echo "[stills] $SID ok"
done
ls -la "$OUT" | tail -14
