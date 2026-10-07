#!/usr/bin/env bash
# r6_loft_fetch.sh — download the R6 real stitched-interior LEVEL asset.
#
# Source: Blender Foundation demo CDN (CC-licensed demo files):
#   https://download.blender.org/demo/cycles/loft.blend
# The "Loft" scene — a two-level loft apartment interior (walls, stairs,
# pillars, platforms, furniture, deco). Served gzip-compressed (.blend.gz
# semantics); Blender opens compressed .blend natively.
set -euo pipefail
DEST="${LOFT_SRC:-/home/z/vision-work/polyhaven_cache/loft/loft.blend}"
URL="https://download.blender.org/demo/cycles/loft.blend"
mkdir -p "$(dirname "$DEST")"
if [[ -s "$DEST" ]]; then
  echo "[r6-fetch] present: $DEST ($(stat -c%s "$DEST") bytes)"
else
  echo "[r6-fetch] downloading $URL"
  curl -s --max-time 560 -o "$DEST" "$URL"
  gzip -t "$DEST"   # integrity: the file is gzip-wrapped .blend
  echo "[r6-fetch] done: $(stat -c%s "$DEST") bytes"
fi
