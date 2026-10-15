#!/bin/bash
# encode_deliverable.sh -- encode the viewport-render frames into the
# deliverable MP4s (primary: anim.mp4 with fades; + dialog mux).
#
# Usage: bash scripts/encode_deliverable.sh <frames_dir> [out_dir]
#
# D6/D7 (session-18): pipefail (ffmpeg's exit used to be masked by the
# `tail` pipe — a failed encode printed "done"), a post-encode
# existence/>1KB abort BEFORE anything consumes anim.mp4, and a guarded
# mux_dialog call (the script is not in-tree — WARN, not exit 127).
set -euo pipefail
FR="${1:-output/escape_v2_vp}"
OUT="${2:-$FR}"
KIT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$KIT"

FPS=24
EXT=png
# `|| true` guards the ls|wc pipelines: with pipefail a no-match ls (the
# jpg fallback probe) would otherwise kill the script under set -e.
N=$(ls "$FR"/frame_*.png 2>/dev/null | wc -l || true)
if [ "$N" -lt 10 ]; then
  EXT=jpg
  N=$(ls "$FR"/frame_*.jpg 2>/dev/null | wc -l || true)
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

# D6: with pipefail a real ffmpeg failure now aborts at the pipe above;
# this existence/size check catches the silent class (exit 0 but an
# empty/truncated file) BEFORE the mux step consumes the deliverable.
if [[ ! -f "$OUT/anim.mp4" ]] || (( $(wc -c < "$OUT/anim.mp4") <= 1024 )); then
  echo "ERROR: encode failed -- $OUT/anim.mp4 missing or <=1KB" \
       "(ffmpeg exit was masked by the tail pipe before pipefail)" >&2
  exit 1
fi
echo "[encode] anim.mp4 done ($(wc -c < "$OUT/anim.mp4") bytes)"

# dialog mux (TTS lines at story timecodes) -- D7: the script is not in
# tree; WARN loudly instead of dying with exit 127 on every run.
if [[ -f scripts/mux_dialog.sh ]]; then
  bash scripts/mux_dialog.sh "$OUT/anim.mp4" "$OUT/anim_dialog.mp4"
else
  echo "[encode] WARN: mux_dialog.sh not present — skipping dialog mux" >&2
fi

for f in anim.mp4 anim_dialog.mp4; do
  [[ -f "$OUT/$f" ]] || continue   # D7: the dialog mux may be skipped
  d=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT/$f")
  echo "[encode] $OUT/$f  duration=${d}s  size=$(du -h "$OUT/$f" | cut -f1)"
done
