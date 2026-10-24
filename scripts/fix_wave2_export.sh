#!/bin/bash
# fix_wave2_export.sh — the 7-film export + stage wave (fix-wave-2).
# Per film: s27_export_film.sh (jpg stills -> canonical export under
# the 4bece16 governed pin -> filmstrips) then stage to the app.
# Usage: bash scripts/fix_wave2_export.sh <film>   (one film at a time)
set -eu
FILM=$1
cd /home/z/work/blender-vision-kit
export BLENDER_BIN=/home/z/work/bltest/blender-5.2.2-linux-x64/blender
export DISPLAY=:99
export KEEP_XVFB=1
export RH_ASSETS=/home/z/lab/RH-3d-assets
export RH_ANIMS=/home/z/lab/RH-canvas-animations

case $FILM in
  tdawn)   PKG=tdawn_5;   SCENE=scene_terminal_dawn; NAME="TERMINAL DAWN (fix-wave-2: animated crowd, oriented heroes, no flicker)" ;;
  tferry)  PKG=tferry_4;  SCENE=scene_last_ferry;    NAME="LAST FERRY (fix-wave-2: animated crowd, oriented heroes, no flicker)" ;;
  tgreen)  PKG=tgreen_4;  SCENE=scene_green_light;   NAME="GREEN LIGHT (fix-wave-2: animated crowd, oriented heroes, no flicker)" ;;
  tsquall) PKG=tsquall_4; SCENE=scene_squall;        NAME="THE SQUALL (fix-wave-2: animated crowd, oriented heroes, no flicker)" ;;
  tfog)    PKG=tfog_4;    SCENE=tfog_scene;          NAME="THE EXPRESS (fix-wave-2: animated crowd, oriented heroes, no flicker)" ;;
  tform)   PKG=tform_4;   SCENE=tform_scene;         NAME="THE DRILL (fix-wave-2: animated crowd, oriented heroes, no flicker)" ;;
  tmarket) PKG=tmarket_2; SCENE=scene_night_market;  NAME="NIGHT MARKET (fix-wave-2: animated crowd, oriented heroes, no flicker)" ;;
  *) echo "unknown film $FILM"; exit 2 ;;
esac

N=$(ls output/$FILM/stills/shot_S*.png 2>/dev/null | wc -l)
[ "$N" -eq 12 ] || { echo "REFUSE: $FILM has $N/12 stills"; exit 3; }
bash scripts/s27_export_film.sh "$FILM" "$SCENE" "$PKG" "$NAME"
echo "=== EXPORT OK: $PKG ==="
ls output/$FILM/pkg/
