#!/usr/bin/env python3
"""Calibrate auto-rule thresholds from measured corpus stats (R5 D1).

Measures per image: mean_luma, stdev, chromatic_share, dark_fraction
(luma<0.15), mean_sobel, distinct-hue-bin count (20deg bins, sat>=floor,
>=1% mass). Prints a table; thresholds get picked from this data.
"""
import glob
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from ascii_vision import luma, sat_val, sobel  # noqa: E402
from PIL import Image  # noqa: E402

def hue_bins(px, W, H, sat_floor):
    bins = [0] * 18
    n = 0
    for y in range(H):
        for x in range(W):
            r, g, b = px[x, y][:3]
            s, v = sat_val((r, g, b))
            if s >= sat_floor and v > 0.12:
                h = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)[0]
                bins[int(h * 18) % 18] += 1
                n += 1
    if n == 0:
        return 0
    return sum(1 for b in bins if b / (W * H) >= 0.01)

import colorsys  # noqa: E402

imgs = sorted(glob.glob(sys.argv[1] if len(sys.argv) > 1 else
                        "experiments/ascii_vision/corpus/*/*.png"))
print("%-22s %5s %5s %6s %6s %6s %5s" %
      ("image", "mean", "stdev", "chrom%", "dark%", "sobmean", "edge%"))
for p in imgs:
    im = Image.open(p).convert("RGB")
    W, H = 96, max(6, round(96 * im.size[1] / im.size[0] * 0.5))
    small = im.resize((W, H), Image.BOX)
    px = small.load()
    lv = [[luma(px[x, y]) / 255.0 for x in range(W)] for y in range(H)]
    n = W * H
    mean = sum(sum(r) for r in lv) / n
    stdev = (sum((v - mean) ** 2 for r in lv for v in r) / n) ** 0.5
    dark = sum(1 for r in lv for v in r if v < 0.15) / n
    sm = sobel(lv)
    sme = sum(sum(r) for r in sm) / n
    strong_edge = sum(1 for r in sm for v in r if v > 0.15) / n
    # chromatic share at default scene threshold via classify floor 0.15
    chrom = sum(1 for y in range(H) for x in range(W)
                if sat_val(px[x, y])[0] >= 0.15) / n
    hb = hue_bins(px, W, H, 0.15)
    print("%-22s %5.2f %5.2f %6.1f %6.1f %6.3f %5.1f" %
          (os.path.basename(p), mean, stdev, 100 * chrom, 100 * dark, sme, 100 * strong_edge))
