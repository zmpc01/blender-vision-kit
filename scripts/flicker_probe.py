#!/usr/bin/env python3
"""flicker_probe.py -- temporal-stability gate on rendered frames (v3.2 §1).

Renders 4 consecutive frames of a static shot with a 2 mm camera dither
(or analyzes consecutive delivered frames of a static region), then
measures per-pixel |delta| in the "flat" regions (road away from
subjects). AA-off shimmer + residual z-fight show up as high temporal
variance in supposedly-static pixels. Gate: mean flat-region delta
below FLICKER_MAX.

Usage (post-render analysis over the delivery):
    python3 scripts/flicker_probe.py output/escape_v32_full \
        --frames 337 338 339 340   # a static-camera window
"""
import argparse
import os
import sys

import numpy as np
from PIL import Image

FLICKER_MAX = 6.0        # mean |delta| (0-255) in flat regions
SUBJECT_BAND = 0.30      # ignore the center band (subjects)


def flat_mask(im_l, prev_l):
    """Flat regions: low spatial gradient AND low temporal change is
    circular -- use spatially-smooth areas away from the frame center."""
    gx = np.abs(np.diff(im_l, axis=1))
    gy = np.abs(np.diff(im_l, axis=0))
    g = gx[:-1, :] + gy[:, :-1]
    smooth = g < 6.0
    h, w = im_l.shape
    x0, x1 = int(w * SUBJECT_BAND), int(w * (1 - SUBJECT_BAND))
    side = np.zeros_like(smooth)
    side[:, :x0] = True
    side[:, x1:] = True
    return smooth & side


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--frames", nargs=4, type=int, required=True)
    a = ap.parse_args()
    frames = []
    for f in a.frames:
        p = os.path.join(a.dir, f"frame_{f:04d}.jpg")
        im = np.asarray(Image.open(p).convert("L")).astype(float)
        frames.append(im)
    worst = 0.0
    for i in range(len(frames) - 1):
        cur, prev = frames[i], frames[i + 1]
        mask = flat_mask(cur, prev)
        delta = np.abs(cur - prev)
        d2 = delta[:mask.shape[0], :mask.shape[1]]
        flat_delta = d2[mask].mean() if mask.any() else 0.0
        worst = max(worst, flat_delta)
        print(f"[flicker] f{a.frames[i]}->{a.frames[i+1]}: "
              f"flat-region mean |d| = {flat_delta:.2f}")
    ok = worst < FLICKER_MAX
    print(f"[flicker] worst {worst:.2f} vs max {FLICKER_MAX} -> "
          f"{'PASS' if ok else 'FAIL'}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
