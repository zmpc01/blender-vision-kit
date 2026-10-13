#!/bin/bash
# tferry_stills.sh -- one EEVEE process per shot (the OOM law), stills
# named shot_<id>.png (the package contract), mid-shot frame each.
# Frames reuse tdawn's per-shot relative picks verbatim: the LAST
# FERRY shot layout (SHOTS_V3 in scene_last_ferry.py) is frame-
# identical to tdawn's, and every shot's intent matches 1:1, so the
# same absolute frames hold the same relative position per span.
set -u
cd /home/z/lab/blender-vision-kit
export CROWD_CACHE_DIR=/tmp/crowdcache_tferry
OUT=output/tferry/stills
mkdir -p "$OUT"
# span each frame was drawn from (scene_last_ferry.py SHOTS_V3):
#   S1 1-84      S2 85-168    S3 169-264   S4 265-348   S5 349-444
#   S6 445-528   S7 529-624   S8 625-720   S9 721-816   S10 817-912
#   S11 913-1008 S12 1009-1080
declare -A FRAMES=( [S1]=76 [S2]=126 [S3]=220 [S4]=300 [S5]=396 [S6]=470 \
  [S7]=580 [S8]=660 [S9]=750 [S10]=860 [S11]=960 [S12]=1044 )
ONLY="${1:-}"
for SID in S1 S2 S3 S4 S5 S6 S7 S8 S9 S10 S11 S12; do
  if [ -n "$ONLY" ] && [ "$ONLY" != "$SID" ]; then continue; fi
  F=${FRAMES[$SID]}
  if [ -s "$OUT/shot_${SID}.png" ]; then echo "[stills] $SID exists, skip"; continue; fi
  echo "[stills] $SID @ f$F ..."
  # NOTE: scene_last_ferry.py appends stillwork/ to --output itself
  # (tdawn's scene wrote straight into --output), so we pass the
  # package root and the stills land in output/tferry/stillwork/.
  ./scripts/blrun.sh --background --factory-startup \
    --python scripts/scene_last_ferry.py -- \
    --output output/tferry --engine eevee --w 640 --h 360 \
    --still $F --samples ${SAMPLES:-32} > /tmp/still_$SID.log 2>&1
  rc=$?
  if [ $rc -ne 0 ] || [ ! -s output/tferry/stillwork/still_$(printf %05d $F).png ]; then
    echo "[stills] $SID FAILED rc=$rc (see /tmp/still_$SID.log)"; continue
  fi
  mv output/tferry/stillwork/still_$(printf %05d $F).png "$OUT/shot_${SID}.png"
  echo "[stills] $SID ok"
done
ls -la "$OUT" | tail -14
