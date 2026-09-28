#!/usr/bin/env python3
"""sheet.py — build labeled contact sheets from output/tuning PNGs."""
from PIL import Image, ImageDraw
import os, sys

OUT = "/home/z/bvk/output/tuning"

def sheet(names, cols, out_path, cell_w=640, cell_h=480):
    rows = (len(names) + cols - 1) // cols
    pad = 4
    label_h = 26
    W = cols * (cell_w + pad) + pad
    H = rows * (cell_h + label_h + pad) + pad
    canvas = Image.new("RGB", (W, H), (18, 18, 18))
    d = ImageDraw.Draw(canvas)
    for i, n in enumerate(names):
        r, c = divmod(i, cols)
        x = pad + c * (cell_w + pad)
        y = pad + r * (cell_h + label_h + pad)
        d.text((x + 4, y + 4), n, fill=(255, 255, 80))
        img = Image.open(os.path.join(OUT, n + ".png")).resize((cell_w, cell_h))
        canvas.paste(img, (x, y + label_h))
        d.rectangle([x, y + label_h, x + cell_w, y + label_h + cell_h], outline=(60, 60, 60))
    canvas.save(out_path)
    print("sheet:", out_path, canvas.size)

if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("color", "all"):
        sheet(["wb_flat_mat", "wb_studio_mat", "wb_studio_mat_cav", "wb_studio_mat_sh",
               "wb_flat_single", "wb_studio_object", "wb_matcap_mat",
               "wb_studio_mat_sh_agx", "eevee_std", "eevee_agx"],
              2, f"{OUT}/_sheet_color.png", 640, 480)
    if which in ("mono", "all"):
        sheet(["wb_flat_mat_mono", "wb_studio_mat_mono", "wb_studio_mat_sh_mono",
               "wb_flat_single_mono", "wb_studio_object_mono", "wb_matcap_mat_mono",
               "wb_studio_mat_sh_agx_mono", "eevee_std_mono", "eevee_agx_mono"],
              2, f"{OUT}/_sheet_mono.png", 640, 480)
