#!/bin/bash
# tform_stills.sh -- one EEVEE process per shot (the OOM law), stills
# named shot_<id>.png (the package contract), beat-anchored frames.
# Written FRESH for THE DRILL (the clone-seam law).
#
# Frame table (beat-anchored, the certified beats):
#   S1  f60   aerial SE: the yard + the march sliver (S3 owns the march)
#   S2  f144  the colonnade shade line mid-file
#   S3  f264  the march-in convergence (the flowstrip f260 read)
#   S4  f410  THE WHEEL wide, crane well along its arc (mid-arc)
#   S5  f461  the wheel CLOSE: feet + the shadow sweep (crane 2)
#   S6  f560  HALT line vertical (the flowstrip f560 read)
#   S7  f816  mid-clasp (the beat window f794-838)
#   S8  f890  break-off reading (f860+ per the camprobe note)
#   S9  f954  the streaming column mid-funnel
#   S10 f1000 the gap funnel (the flowstrip f1000 read)
#   S11 f1020 the PLANTED banner + title settled (plants at f1009)
#   S12 f1060 the departing file PAST the wall (the flowstrip read)
set -u
cd "$(dirname "$(dirname "$(readlink -f "$0")")")"
export CROWD_CACHE_DIR=${CROWD_CACHE_DIR:-/tmp/crowdcache_tform}
OUT=${OUT:-output/tform/stills}
mkdir -p "$OUT"
declare -A FRAMES=( [S1]=60 [S2]=144 [S3]=264 [S4]=410 [S5]=461 [S6]=560 \
  [S7]=816 [S8]=890 [S9]=954 [S10]=1000 [S11]=1020 [S12]=1060 )
ONLY="${1:-}"
for SID in S1 S2 S3 S4 S5 S6 S7 S8 S9 S10 S11 S12; do
  if [ -n "$ONLY" ] && [ "$ONLY" != "$SID" ]; then continue; fi
  F=${FRAMES[$SID]}
  if [ -s "$OUT/shot_${SID}.png" ] && [ scripts/tform_scene.py -ot "$OUT/shot_${SID}.png" ]; then echo "[stills] $SID exists (scene older), skip"; continue; fi
  echo "[stills] $SID @ f$F ..."
  ./scripts/blrun.sh --background --factory-startup \
    --python scripts/tform_scene.py -- \
    --output output/tform/stillwork --engine ${ENGINE:-eevee} --w 640 --h 360 \
    --still $F --samples ${SAMPLES:-32} > /tmp/still_tm_$SID.log 2>&1
  rc=$?
  if [ $rc -ne 0 ] || [ ! -s output/tform/stillwork/still_$(printf %05d $F).png ]; then
    echo "[stills] $SID FAILED rc=$rc (see /tmp/still_tm_$SID.log)"; continue
  fi
  mv output/tform/stillwork/still_$(printf %05d $F).png "$OUT/shot_${SID}.png"
  echo "[stills] $SID ok"
done
echo "[stills] DONE -> $OUT"
