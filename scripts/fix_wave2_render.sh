#!/bin/bash
# fix_wave2_render.sh -- the 7-film stills wave (fix-wave-2 re-render
# under the fixed bind layer). Sequential, one process per shot (the
# OOM law), resumable (the runners skip existing stills). Status
# marker file after each film for the orchestrator to poll.
set -u
cd /home/z/work/blender-vision-kit
export BLENDER_BIN=/home/z/work/bltest/blender-5.2.2-linux-x64/blender
export DISPLAY=:99
export KEEP_XVFB=1
export RH_ASSETS=/home/z/lab/RH-3d-assets
export RH_ANIMS=/home/z/lab/RH-canvas-animations
export ENGINE=cycles
STATUS=/tmp/wave2_status.txt
touch "$STATUS"   # resume-safe: APPEND only (the sandbox reaper kills
                  # the wave between orchestrator calls; relaunches
                  # skip completed stills and continue)
for FILM in tdawn tferry tgreen tsquall tfog tform tmarket; do
  echo "[$(date +%H:%M:%S)] FILM $FILM start" >> "$STATUS"
  bash scripts/${FILM}_stills.sh > /tmp/stills_${FILM}.log 2>&1
  rc=$?
  n=$(ls output/$FILM/stills/shot_S*.png 2>/dev/null | wc -l)
  echo "[$(date +%H:%M:%S)] FILM $FILM done rc=$rc stills=$n/12" >> "$STATUS"
  if [ "$n" -lt 12 ]; then
    echo "[$(date +%H:%M:%S)] FILM $FILM INCOMPLETE — retrying missing shots once" >> "$STATUS"
    bash scripts/${FILM}_stills.sh >> /tmp/stills_${FILM}.log 2>&1
    n=$(ls output/$FILM/stills/shot_S*.png 2>/dev/null | wc -l)
    echo "[$(date +%H:%M:%S)] FILM $FILM retry stills=$n/12" >> "$STATUS"
  fi
done
echo "[$(date +%H:%M:%S)] ALL FILMS COMPLETE" >> "$STATUS"
