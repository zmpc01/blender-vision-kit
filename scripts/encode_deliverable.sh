#!/bin/bash
# encode_deliverable.sh -- encode the viewport-render frames into the
# deliverable MP4s (primary: anim.mp4 with fades; + dialog mux).
#
# Usage: bash scripts/encode_deliverable.sh <frames_dir> [out_dir]
set -eu
FR="${1:-output/escape_v2_vp}"
OUT="${2:-$FR}"
KIT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$KIT"

FPS=24
EXT=png
N=$(ls "$FR"/frame_*.png 2>/dev/null | wc -l)
if [ "$N" -lt 10 ]; then
  EXT=jpg
  N=$(ls "$FR"/frame_*.jpg 2>/dev/null | wc -l)
fi
if [ "$N" -lt 10 ]; then
  echo "ERROR: no frame sequence in $FR -- render incomplete?" >&2
  exit 1
fi
echo "[encode] $N frames ($EXT) @ ${FPS}fps from $FR"

# fade in over the first 12 frames, fade out over the last 12
FADE_OUT_ST=$((N - 12))

# crf 23 / preset fast: guidance-video grade (session-9: preset medium
# at crf 19 took ~5 min for 720 960x540 frames -- unnecessary for a
# vid2vid input track)
ffmpeg -y -framerate $FPS -pattern_type glob -i "$FR/frame_*.$EXT" \
  -vf "fade=t=in:st=0:d=0.5,fade=t=out:st=$(python3 -c "print($FADE_OUT_ST/$FPS)"):d=0.5" \
  -c:v libx264 -pix_fmt yuv420p -crf 23 -preset fast \
  "$OUT/anim.mp4" 2>&1 | tail -2
echo "[encode] anim.mp4 done"

# dialog mux (TTS lines at story timecodes)
bash scripts/mux_dialog.sh "$OUT/anim.mp4" "$OUT/anim_dialog.mp4"

for f in anim.mp4 anim_dialog.mp4; do
  d=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT/$f")
  echo "[encode] $OUT/$f  duration=${d}s  size=$(du -h "$OUT/$f" | cut -f1)"
done
