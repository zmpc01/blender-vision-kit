"""tferry_sheet.py -- 2x2 contact sheets of the 12 certified stills.

Usage (any python with Pillow):
    python3 tferry_sheet.py <stills_dir> <out_prefix> [sids...]
Writes <out_prefix>_S1-S4.png etc. (3 sheets of 4) with the shot id
stamped in the corner of each cell (the eyes need the labels).
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

CELL_W, CELL_H = 640, 360
PAD = 6

def main():
    src = Path(sys.argv[1])
    out_prefix = sys.argv[2]
    sids = sys.argv[3:] or [f"S{i}" for i in range(1, 13)]
    groups = [sids[i:i + 4] for i in range(0, len(sids), 4)]
    for gi, group in enumerate(groups, 1):
        sheet = Image.new("RGB", (CELL_W * 2 + PAD * 3, CELL_H * 2 + PAD * 3),
                          (24, 24, 24))
        d = ImageDraw.Draw(sheet)
        for ci, sid in enumerate(group):
            p = src / f"shot_{sid}.png"
            if not p.is_file():
                print(f"[sheet] MISSING {p}")
                continue
            im = Image.open(p).resize((CELL_W, CELL_H))
            col, row = ci % 2, ci // 2
            x = PAD + col * (CELL_W + PAD)
            y = PAD + row * (CELL_H + PAD)
            sheet.paste(im, (x, y))
            d.rectangle([x + 2, y + 2, x + 86, y + 24], fill=(0, 0, 0))
            d.text((x + 8, y + 6), sid, fill=(255, 220, 80))
            d.rectangle([x, y, x + CELL_W, y + CELL_H], outline=(90, 90, 90))
        out = Path(f"{out_prefix}_grp{gi}.png")
        sheet.save(out)
        print(f"[sheet] {out} ({'+'.join(group)})")

if __name__ == "__main__":
    main()
