#!/bin/bash
# tfog_stills.sh -- one EEVEE process per shot (the OOM law), stills
# s25: the CYCLES ENGINE LAW (tform_2 measured: skinned crowds OOM
# EEVEE even on the knob diet) -- ENGINE defaults to cycles now;
# ENGINE=eevee keeps the legacy pre-humanoid path reproducible.
# named shot_<id>.png (the package contract), mid-shot frame each.
# Written FRESH for THE EXPRESS (the clone-seam law).
set -u
cd "$(dirname "$(dirname "$(readlink -f "$0")")")"
export CROWD_CACHE_DIR=${CROWD_CACHE_DIR:-/tmp/crowdcache_tfog}
export TFOG_HUMANOID=${TFOG_HUMANOID:-1}
export RH_ASSETS=${RH_ASSETS:-/home/z/lab/RH-3d-assets}
export RH_ANIMS=${RH_ANIMS:-/home/z/lab/RH-canvas-animations}
OUT=${OUT:-output/tfog/stills}
mkdir -p "$OUT"
declare -A FRAMES=( [S1]=50 [S2]=140 [S3]=288 [S4]=320 [S5]=470 [S6]=570 \
  [S7]=628 [S8]=740 [S9]=840 [S10]=910 [S11]=1005 [S12]=1050 )
# S5=470 (the certified verdict, commit 37c00b9: the nose enters the
# visible band ~f430 — the 430 still predated the streak; the table
# had drifted while the render used the manual override).
ONLY="${1:-}"
for SID in S1 S2 S3 S4 S5 S6 S7 S8 S9 S10 S11 S12; do
  if [ -n "$ONLY" ] && [ "$ONLY" != "$SID" ]; then continue; fi
  F=${FRAMES[$SID]}
  if [ -s "$OUT/shot_${SID}.png" ] && [ scripts/tfog_scene.py -ot "$OUT/shot_${SID}.png" ]; then echo "[stills] $SID exists (scene older), skip"; continue; fi
  echo "[stills] $SID @ f$F ..."
  ./scripts/blrun.sh --background --factory-startup \
    --python scripts/tfog_scene.py -- \
    --output output/tfog/stillwork --engine ${ENGINE:-cycles} --w 640 --h 360 \
    --still $F --samples ${SAMPLES:-32} > /tmp/still_tf_$SID.log 2>&1
  rc=$?
  if [ $rc -ne 0 ] || [ ! -s output/tfog/stillwork/still_$(printf %05d $F).png ]; then
    echo "[stills] $SID FAILED rc=$rc (see /tmp/still_tf_$SID.log)"; continue
  fi
  mv output/tfog/stillwork/still_$(printf %05d $F).png "$OUT/shot_${SID}.png"
  echo "[stills] $SID ok"
done
echo "[stills] DONE -> $OUT"
