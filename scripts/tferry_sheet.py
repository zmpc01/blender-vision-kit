#!/usr/bin/env python3
"""Contact sheet for the tferry framing round (3 cols x 4 rows)."""
import sys
from PIL import Image, ImageDraw

SRC = "/home/z/work/blender-vision-kit/output/tferry/stills"
OUT = sys.argv[1] if len(sys.argv) > 1 else \
    "/home/z/work/blender-vision-kit/output/tferry/framing_sheet.png"

ids = [f"S{i}" for i in range(1, 13)]
COLS, W, H, CAP = 3, 640, 360, 26
rows = (len(ids) + COLS - 1) // COLS
sheet = Image.new("RGB", (COLS * (W + 8) + 8, rows * (H + CAP + 8) + 8),
                  (16, 16, 18))
d = ImageDraw.Draw(sheet)
for k, sid in enumerate(ids):
    im = Image.open(f"{SRC}/shot_{sid}.png").resize((W, H))
    x = 8 + (k % COLS) * (W + 8)
    y = 8 + (k // COLS) * (H + CAP + 8)
    sheet.paste(im, (x, y))
    d.text((x + 6, y + H + 6), f"{sid}", fill=(220, 220, 210))
sheet.save(OUT)
print(OUT, sheet.size)
