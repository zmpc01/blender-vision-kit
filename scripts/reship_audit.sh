#!/bin/bash
# reship_audit.sh — the audit-round re-ship chain, ONE call per film,
# resumable at every stage (the sandbox reaper law; NEVER delete the
# state file mid-chain — that re-renders finished stills). Stages:
# seed -> stills (only CHANGED shots; the rest carried from the
# previous package) -> jpg -> export (gated, .export_ok) -> filmstrips.
# Env is hoisted to script level (a stage skip must not lose it).
# Usage: bash reship_audit.sh <film>
set -u
FILM=$1
cd /home/z/work/blender-vision-kit

case $FILM in
  tdawn)   SCENE=scene_terminal_dawn; OLD=tdawn_5;   CHANGED="S11" ;;
  tferry)  SCENE=scene_last_ferry;    OLD=tferry_4;  CHANGED="S2" ;;
  tfog)    SCENE=tfog_scene;          OLD=tfog_4;    CHANGED="S3 S4 S7" ;;
  tform)   SCENE=tform_scene;         OLD=tform_4;   CHANGED="S9 S10 S11 S12" ;;
  tmarket) SCENE=scene_night_market;  OLD=tmarket_2; CHANGED="S8 S9 S10" ;;
  *) echo "unknown film $FILM"; exit 2 ;;
esac

export BLENDER_BIN=/home/z/work/bltest/blender-5.2.2-linux-x64/blender
export DISPLAY=:99
export RH_ASSETS=/home/z/lab/RH-3d-assets
export CROWD_CACHE_DIR=/tmp/crowdcache_$FILM
export KIT_EXPORTER=/home/z/work/blender-agent-kit/scripts/export_previz_package.py
export PKG_FRAME_STEP=2
case $FILM in
  tferry) export TFERRY_HUMANOID=1 ;;
  tfog)   export TFOG_HUMANOID=1 ;;
  tform)  export TFORM_HUMANOID=1 ;;
  tmarket) export TMARKET_HUMANOID=1 ;;
  tdawn)  export TDAWN_HUMANOID=1 ;;
esac

STAGE=/tmp/reship_${FILM}.state
touch "$STAGE"

# --- stage 1: seed the stills dirs ------------------------------------
if ! grep -q "^seed done" "$STAGE"; then
  rm -rf output/$FILM
  mkdir -p output/$FILM/stills output/$FILM/stills_jpg
  cp /home/z/work/previz-review/public/packages/$OLD/stills/*.jpg \
     output/$FILM/stills_jpg/ 2>/dev/null || echo "WARN: no old package stills"
  echo "seed done" >> "$STAGE"
  echo "[$FILM] seeded $(ls output/$FILM/stills_jpg | wc -l) carried stills"
fi

# --- stage 2: render the CHANGED stills --------------------------------
for SID in $CHANGED; do
  if [ -s output/$FILM/stills/shot_${SID}.png ]; then continue; fi
  echo "[$FILM] still $SID @ $(date +%H:%M:%S)"
  timeout 540 bash scripts/${FILM}_stills.sh $SID 2>&1 | tail -2
done
npng=$(ls output/$FILM/stills/*.png 2>/dev/null | wc -l)
nexp=$(echo $CHANGED | wc -w)
echo "[$FILM] new stills: $npng / expected $nexp"
[ "$npng" -eq "$nexp" ] || { echo "[$FILM] STILL COUNT SHORT — check /tmp/still_S*.log"; exit 1; }
grep -q "^stills done" "$STAGE" || echo "stills done" >> "$STAGE"

# --- stage 3: convert the new pngs over the carried jpgs ---------------
if ! grep -q "^jpg done" "$STAGE"; then
  python3 - <<EOF
from PIL import Image
import glob, os
for p in glob.glob('output/$FILM/stills/shot_S*.png'):
    out = 'output/$FILM/stills_jpg/' + os.path.basename(p).replace('.png', '.jpg')
    Image.open(p).convert('RGB').save(out, quality=92)
    print('jpg:', os.path.basename(out))
EOF
  echo "jpg done" >> "$STAGE"
fi
echo "[$FILM] stills_jpg total: $(ls output/$FILM/stills_jpg | wc -l) (need 12)"

# --- stage 4: the gated export ------------------------------------------
if ! grep -q "^export done" "$STAGE"; then
  rm -rf output/$FILM/pkg
  bash /home/z/work/blender-crowd-kit/scripts/blrun.sh --background --factory-startup \
    --python /home/z/work/blender-crowd-kit/scripts/previz_kit_export_wrapper.py -- \
    --scene $SCENE --scene-dir /home/z/work/blender-vision-kit/scripts \
    --crowd-mode kit --crowd-plugin /home/z/work/blender-escape-previz/scripts/crowd_kit \
    --output output/$FILM/pkg --package-id ${FILM}_AUDIT --name "AUDIT ROUND ${FILM}" \
    --stills-dir output/$FILM/stills_jpg > /tmp/export_${FILM}.log 2>&1
  rc=$?
  tail -4 /tmp/export_${FILM}.log
  [ -f output/$FILM/pkg/.export_ok ] || { echo "[$FILM] EXPORT FAILED rc=$rc"; exit 1; }
  echo "export done" >> "$STAGE"
fi

# --- stage 5: filmstrips -------------------------------------------------
if ! grep -q "^strips done" "$STAGE"; then
  bash scripts/blrun.sh --background --factory-startup \
    --python scripts/${FILM}_filmstrips.py -- --pkg output/$FILM/pkg > /tmp/filmstrips_${FILM}.log 2>&1
  n=$(ls output/$FILM/pkg/filmstrips 2>/dev/null | wc -l)
  echo "[$FILM] filmstrips: $n"
  [ "$n" -ge 96 ] || { echo "[$FILM] STRIPS SHORT"; exit 1; }
  echo "strips done" >> "$STAGE"
fi
echo "[$FILM] RESHIP CHAIN COMPLETE"
