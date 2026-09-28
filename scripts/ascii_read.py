#!/usr/bin/env python3
"""ascii_read.py -- downsample a PNG into a color-quantized ASCII grid
for the orchestrator's own native-vision reading (VLM-sycophancy guard).

Usage: python3 ascii_read.py <png> [cols] [rows]
"""
import sys
from PIL import Image

# color -> char map (by nearest reference hue)
REFS = {
    '.': (120, 120, 120),   # gray bg
    ' ': (200, 200, 200),   # light bg
    'B': (60, 90, 190),     # blue
    'R': (190, 60, 60),     # red
    'A': (210, 130, 40),    # amber
    'G': (70, 140, 80),     # green
    'S': (210, 170, 130),   # skin
    'K': (115, 100, 80),    # khaki
    'Z': (150, 179, 137),   # zombie muted green
    'D': (35, 35, 40),      # dark (rifle)
    '#': (30, 120, 200),    # strong blue
}


def classify(rgb):
    best, bd = '.', 1e9
    for ch, ref in REFS.items():
        d = sum((a - b) ** 2 for a, b in zip(rgb, ref))
        if d < bd:
            best, bd = ch, d
    return best


def main():
    path = sys.argv[1]
    cols = int(sys.argv[2]) if len(sys.argv) > 2 else 64
    rows = int(sys.argv[3]) if len(sys.argv) > 3 else 40
    im = Image.open(path).convert("RGB")
    w, h = im.size
    im = im.resize((cols, rows), Image.BOX)
    px = im.load()
    print(f"== {path} ({w}x{h} -> {cols}x{rows}) ==")
    for y in range(rows):
        print("".join(classify(px[x, y]) for x in range(cols)))


if __name__ == "__main__":
    main()
