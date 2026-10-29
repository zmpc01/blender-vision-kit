#!/bin/bash
# s27_export_film.sh -- the re-ship path for ONE film (the s27 re-look
# wave): jpg stills -> canonical export (_3) -> filmstrips -> stage dir.
# Usage: bash scripts/s27_export_film.sh <film> <scene_module> <pkg_id> <name>
#   e.g. bash scripts/s27_export_film.sh tferry scene_last_ferry tferry_3 "LAST FERRY (humanoid, s27 re-cert)"
set -euo pipefail
FILM=$1; SCENE=$2; PKG=$3; NAME=$4
cd /home/z/work/blender-vision-kit
export BLENDER_BIN=/home/z/work/bltest/blender-5.2.2-linux-x64/blender
export DISPLAY=:99
export RH_ASSETS=/home/z/lab/RH-3d-assets
export CROWD_CACHE_DIR=/tmp/crowdcache_$FILM
export KIT_EXPORTER=/home/z/work/blender-agent-kit/scripts/export_previz_package.py
# the governed export pin (the fix-wave-1 record): agent-kit must be at
# 4bece16 — the s27 fca46ca record SUPERSEDED by the wave's exporter
# commits: 71018c2 (frame_step=1, the tier-B B1 law) + 4bece16 (gate 25
# duplicate-bone-name refusal + gate 17 layer-boundary wiring — both
# born FOR this wave's exports)
# the governed pin (fix-wave-2 advance, RE-LANDED): the film-lane
# frame-step law — PKG_FRAME_STEP=2 on the package path (the 129-rig
# OOM; gates 18/19 skip on films by the additive law), default 1 for
# the escape lane. The original b4468f6 was stranded on a detached
# HEAD (never reached origin/main); 7754f78 is the SAME change landed
# on main — never commit pin-checkout clones on detached HEADs.
export PKG_FRAME_STEP=2
( cd /home/z/work/blender-agent-kit && [ "$(git rev-parse HEAD)" = "96ce728a4f559531463b4646607830ba5363cf59" ] ) || {
  echo "GOVERNED PIN FAIL: agent-kit HEAD is not 96ce728 (the s46 advance: the bare-animate bind-split two-way merge, frame-step KEPT; action_ops vendored; tier-B B2 re-baselined at c51bb2a)"; exit 3;
}
# per-film humanoid env (the s25 contract)
case $FILM in
  tferry) export TFERRY_HUMANOID=1 ;;
  tgreen) export TGREEN_HUMANOID=1 ;;
  tfog)   export TFOG_HUMANOID=1 ;;
  tsquall) export TSQUALL_HUMANOID=1 ;;
  tmarket) export TMARKET_HUMANOID=1 ;;
  tdawn)  export TDAWN_HUMANOID=1 ;;
  tform)  export TFORM_HUMANOID=1 ;;
  *) echo "unknown film $FILM"; exit 2 ;;
esac
# 1. jpg stills (the exporter contract: shot_<ID>.jpg)
mkdir -p output/$FILM/stills_jpg
python3 - <<EOF
from PIL import Image
import glob, os
for p in glob.glob('output/$FILM/stills/shot_S*.png'):
    out = 'output/$FILM/stills_jpg/' + os.path.basename(p).replace('.png', '.jpg')
    Image.open(p).convert('RGB').save(out, quality=92)
print('jpg stills:', len(glob.glob('output/$FILM/stills_jpg/shot_S*.jpg')))
EOF
# 2. canonical export
rm -rf output/$FILM/pkg
bash /home/z/work/blender-crowd-kit/scripts/blrun.sh --background --factory-startup \
  --python /home/z/work/blender-crowd-kit/scripts/previz_kit_export_wrapper.py -- \
  --scene $SCENE --scene-dir /home/z/work/blender-vision-kit/scripts \
  --crowd-mode kit --crowd-plugin /home/z/work/blender-escape-previz/scripts/crowd_kit \
  --output output/$FILM/pkg --package-id $PKG --name "$NAME" \
  --stills-dir output/$FILM/stills_jpg > /tmp/export_${FILM}.log 2>&1
tail -3 /tmp/export_${FILM}.log
ls output/$FILM/pkg/ 2>/dev/null
# 3. filmstrips into the pkg (the workbench analytic lane)
bash /home/z/work/blender-vision-kit/scripts/blrun.sh --background --factory-startup \
  --python scripts/${FILM}_filmstrips.py -- --pkg output/$FILM/pkg > /tmp/filmstrips_${FILM}.log 2>&1 || \
python3 scripts/${FILM}_filmstrips.py --pkg output/$FILM/pkg > /tmp/filmstrips_${FILM}.log 2>&1
echo "filmstrips: $(ls output/$FILM/pkg/filmstrips 2>/dev/null | wc -l)"
echo "stills: $(ls output/$FILM/pkg/stills 2>/dev/null | wc -l)"
echo "EXPORT DONE: $PKG"
