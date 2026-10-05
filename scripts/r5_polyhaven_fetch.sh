#!/usr/bin/env bash
# r5_polyhaven_fetch.sh — fetch a REAL polyhaven asset for the R5 lane.
# CoffeeCart_01 (CC0): cart frame + top + mugs — 3 mesh nodes, real
# textures, real-world scale quirks. Downloads into output/r5/assets/
# (gitignored — binaries). API: /assets, /files; textures live under
# Models/jpg/<res>/<asset>/ while the .gltf references them as
# textures/<name>.jpg — we download INTO that layout.
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$HERE/output/r5/assets"
mkdir -p "$OUT/textures"
BASE="https://dl.polyhaven.org/file/ph-assets/Models/jpg/1k/CoffeeCart_01"
GLTF="https://dl.polyhaven.org/file/ph-assets/Models/gltf/1k/CoffeeCart_01/CoffeeCart_01_1k.gltf"

[ -f "$OUT/CoffeeCart_01_1k.gltf" ] || curl -sf --max-time 60 "$GLTF" -o "$OUT/CoffeeCart_01_1k.gltf"
[ -f "$OUT/CoffeeCart_01.bin" ] || curl -sf --max-time 120 "https://dl.polyhaven.org/file/ph-assets/Models/gltf/1k/CoffeeCart_01/CoffeeCart_01.bin" -o "$OUT/CoffeeCart_01.bin"
for t in cart_diff cart_nor_gl cart_arm props_diff props_nor_gl props_arm mugs_diff mugs_nor_gl mugs_arm; do
  [ -f "$OUT/textures/CoffeeCart_01_${t}_1k.jpg" ] || \
    curl -sf --max-time 120 "$BASE/CoffeeCart_01_${t}_1k.jpg" -o "$OUT/textures/CoffeeCart_01_${t}_1k.jpg"
done
# honest download check: every referenced URI must exist and be non-trivial
python3 - "$OUT" <<'EOF'
import json, os, sys
out = sys.argv[1]
d = json.load(open(os.path.join(out, "CoffeeCart_01_1k.gltf")))
missing = [b["uri"] for b in d["buffers"] if not os.path.exists(os.path.join(out, b["uri"]))]
missing += [i["uri"] for i in d["images"]
            if not os.path.exists(os.path.join(out, i["uri"]))
            or os.path.getsize(os.path.join(out, i["uri"])) < 5000]
if missing:
    sys.exit(f"MISSING/undersized: {missing}")
print(f"[fetch] OK: {len(d['buffers'])} buffer(s), {len(d['images'])} images, "
      f"{len(d['meshes'])} meshes: {[m['name'] for m in d['meshes']]}")
EOF
