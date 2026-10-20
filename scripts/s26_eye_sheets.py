#!/usr/bin/env python3
"""s26 eye-gate: rebuild the 6 film contact sheets from the committed
app packages (the s25 sheets died with /home/sync). 12 stills per film
(shot_S1..S12), 3x4 grid, shot-ID labels. Output: /home/sync/s26_sheets/.
"""
import os
from PIL import Image, ImageDraw

PKGS = "/home/z/lab/previz-review/public/packages"
FILMS = ["tdawn_4", "tferry_2", "tgreen_2", "tsquall_2", "tfog_2", "tform_3"]
OUT = "/home/sync/s26_sheets"
COLS, ROWS = 3, 4
CELL_W = 640
PAD = 26  # label band

os.makedirs(OUT, exist_ok=True)
for film in FILMS:
    sdir = os.path.join(PKGS, film, "stills")
    files = sorted(os.listdir(sdir), key=lambda f: int(f.replace("shot_S", "").replace(".jpg", "")))
    assert len(files) == 12, f"{film}: {len(files)} stills"
    im0 = Image.open(os.path.join(sdir, files[0]))
    cw, ch = im0.size  # 640x360
    cell_h = ch * CELL_W // cw
    sheet = Image.new("RGB", (CELL_W * COLS, (cell_h + PAD) * ROWS), (16, 16, 20))
    d = ImageDraw.Draw(sheet)
    for i, f in enumerate(files):
        r, c = divmod(i, COLS)
        im = Image.open(os.path.join(sdir, f)).resize((CELL_W, cell_h), Image.LANCZOS)
        x, y = c * CELL_W, r * (cell_h + PAD)
        sheet.paste(im, (x, y + PAD))
        d.text((x + 6, y + 5), f"{film}  {f.replace('.jpg','')}", fill=(255, 220, 120))
    outp = os.path.join(OUT, f"{film}_sheet.jpg")
    sheet.save(outp, quality=90)
    print(f"{outp}  {sheet.size}")
print("sheets done")
