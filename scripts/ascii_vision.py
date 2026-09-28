#!/usr/bin/env python3
"""ascii_vision.py -- high-quality ASCII pack generator for visionless agents.

Turns an image into a text "vision pack" a plain text-only LLM can read:
color-class grid + luma grid (optional dithering) + edge grid + stats +
connected-component table (+ zoom tiles). Successor to ascii_read.py's
scene-specific 10-char palette, generalized and instrumented.

Design contract (experiments/ascii_vision/SPEC.md):
  - deterministic: same img + flags -> identical bytes
  - coords: fractions of the (cropped) frame, origin TOP-LEFT, y down
  - aspect: terminal chars ~2x taller than wide -> rows = cols*h/w*0.5
  - color panel: nearest palette ref ONLY if saturation >= --sat-thresh
    (and value in range), else luma fallback char of that cell
  - component table: 8-connectivity per class, sizes in cells + fractions
  - guard rail: > --max-cols refused unless --force

Examples:
  python3 scripts/ascii_vision.py render.png --cols 100 --components --tiles 2
  python3 scripts/ascii_vision.py render.png --mode color --cols 120
  python3 scripts/ascii_vision.py render.png --mode luma --charset blocks5 --dither fs
  python3 scripts/ascii_vision.py render.png --crop 0.5,0.0,1.0,0.5 --cols 80
"""
import argparse
import colorsys
import json
import os
import sys

from PIL import Image, ImageOps

# ---------------------------------------------------------------------------
# Charsets and palettes
# ---------------------------------------------------------------------------

CHARSETS = {
    # 10-level classic density ramp (light -> dark)
    "art10": " .:-=+*#%@",
    # 5-level unicode blocks
    "blocks5": " .:\u2591\u2592",  # space . : ░ ▒  (avoid heavy █ glare in logs)
    # binary
    "bin": " #",
    "bin01": "01",
    # 16-level fine ramp
    "ramp16": " .'\u00b0:;+=ilxft#@",
    # minimal
    "min": " .:*#@",
}

# Luma fallback chars are NOT used: achromatic palette refs (gray/light/dark)
# are always available to classify unsaturated cells, and chromatic refs are
# gated by --sat-thresh. This avoids char collisions between fallback and
# palette classes (the '#' dark-fallback vs vivid-blue bug).

# scene palette: the kit's escape-previz color language (descends from
# ascii_read.py's REFS but DIVERGES deliberately: refs are lists because
# renders drift in brightness/value, so each class carries multiple hue-tuned
# refs; the classifier is hue-dominant, unlike ascii_read's raw-RGB nearest).
SCENE_PALETTE = {
    ".": [(120, 120, 120)],          # mid-gray (street, background)
    " ": [(200, 200, 200)],          # light gray / sky
    "B": [(61, 109, 181), (84, 110, 161)],   # blue actor + dim render
    "R": [(193, 68, 68), (145, 87, 87)],     # red actor + dim render
    "A": [(217, 151, 59), (138, 112, 55)],   # amber actor + dim render
    "G": [(109, 127, 99), (70, 140, 80)],    # olive zombie + saturated green
    "S": [(210, 170, 130)],          # skin
    "K": [(115, 100, 80), (82, 80, 67)],     # khaki vehicle + dark-olive
    "D": [(35, 35, 40)],             # dark (rifle, tires, shadows)
    "#": [(30, 120, 200)],           # strong/vivid blue
}

# web16: generic 16-hue palette for non-scene images (letters, not glyph soup)
WEB16_PALETTE = {
    ".": (128, 128, 128), " ": (211, 211, 211), "o": (0, 0, 0),
    "r": (197, 60, 60), "R": (255, 120, 120),
    "g": (60, 160, 70), "G": (120, 220, 120),
    "b": (60, 90, 200), "B": (110, 150, 255),
    "y": (210, 190, 50), "Y": (255, 235, 120),
    "m": (170, 60, 170), "M": (230, 130, 230),
    "c": (60, 170, 180), "C": (130, 220, 230),
    "w": (245, 245, 245),
}

GUIDE = """HOW TO READ THIS PACK (for a text-only consumer):
- Panels are character grids. Coordinates are FRACTIONS of the frame,
  origin TOP-LEFT, x right, y down. Column ruler marks x fractions;
  left margin labels give the y fraction at each labeled row.
- color-class panel: each char is the nearest palette class for that cell
  (see legend; * classes are achromatic and always eligible, chromatic
  classes only match cells with enough saturation).
- luma panel: brightness ramp (legend), optional dithering.
- The COMPONENTS table is the most precise source for object positions,
  sizes, counts, colors (rgb/lum columns), density (fill column) and
  frame-edge contact (edge column);
  grids give shape/spatial context. All component fractions are FULL-FRAME
  (tiles/crops remap their coordinates already). Zoom tiles (if any) see
  more detail than the overview (~1.4x linear at --tiles 2; more at higher
  N); compare POSITIONS across panels, not cells/rgb (internal resolution
  differs)."""


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def luma(rgb):
    r, g, b = rgb[:3]
    return 0.299 * r + 0.587 * g + 0.114 * b


def sat_val(rgb):
    r, g, b = [c / 255.0 for c in rgb[:3]]
    return colorsys.rgb_to_hsv(r, g, b)[1:3]


def parse_crop(s):
    try:
        x0, y0, x1, y1 = [float(v) for v in s.split(",")]
    except ValueError:
        raise SystemExit("--crop expects fx0,fy0,fx1,fy1 (fractions)")
    if not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):
        raise SystemExit("--crop values must satisfy 0<=x0<x1<=1, 0<=y0<y1<=1")
    return x0, y0, x1, y1


BAYER4 = [
    [0, 8, 2, 10],
    [12, 4, 14, 6],
    [3, 11, 1, 9],
    [15, 7, 13, 5],
]


def bayer_matrix(n):
    """n=4 -> BAYER4; n=8 -> 4x4 Kronecker product (values 0..63)."""
    if n == 4:
        return BAYER4
    return [[BAYER4[y % 4][x % 4] + BAYER4[y // 4][x // 4] * 16
             for x in range(n)] for y in range(n)]


def dither_luma(vals, levels, mode):
    """vals: HxW floats 0..1. Returns HxW ints (ramp indices 0..levels-1)."""
    h, w = len(vals), len(vals[0])
    out = [[0] * w for _ in range(h)]
    if mode == "none":
        for y in range(h):
            for x in range(w):
                out[y][x] = min(levels - 1, int(vals[y][x] * levels + 0.5))
        return out
    if mode in ("bayer4", "bayer8"):
        n = 4 if mode == "bayer4" else 8
        bm = bayer_matrix(n)
        for y in range(h):
            for x in range(w):
                t = (bm[y % n][x % n] + 0.5) / (n * n)
                out[y][x] = min(levels - 1, int((vals[y][x] + (t - 0.5) / levels) * levels))
        return out
    if mode == "fs":
        buf = [[vals[y][x] for x in range(w)] for y in range(h)]
        for y in range(h):
            for x in range(w):
                old = buf[y][x]
                new = min(levels - 1, max(0, int(old * levels)))
                out[y][x] = new
                err = old - (new + 0.5) / levels
                if x + 1 < w:
                    buf[y][x + 1] += err * 7 / 16
                if y + 1 < h:
                    if x > 0:
                        buf[y + 1][x - 1] += err * 3 / 16
                    buf[y + 1][x] += err * 5 / 16
                    if x + 1 < w:
                        buf[y + 1][x + 1] += err * 1 / 16
        return out
    raise SystemExit("unknown dither mode " + mode)


def sobel(vals):
    """vals: HxW floats 0..1 -> HxW edge magnitude 0..1 (normalized)."""
    h, w = len(vals), len(vals[0])
    mag = [[0.0] * w for _ in range(h)]
    for y in range(1, h - 1):
        for x in range(1, w - 1):
            gx = (vals[y - 1][x + 1] + 2 * vals[y][x + 1] + vals[y + 1][x + 1]
                  - vals[y - 1][x - 1] - 2 * vals[y][x - 1] - vals[y + 1][x - 1])
            gy = (vals[y + 1][x - 1] + 2 * vals[y + 1][x] + vals[y + 1][x + 1]
                  - vals[y - 1][x - 1] - 2 * vals[y - 1][x] - vals[y - 1][x + 1])
            mag[y][x] = min(1.0, (gx * gx + gy * gy) ** 0.5 / 4.0)
    return mag


# ---------------------------------------------------------------------------
# Components
# ---------------------------------------------------------------------------

def components(cells, W, H, chromatic_set, min_cells=2, top=40, px=None):
    """cells: HxW color-class chars. Only CHROMATIC classes form components
    (achromatic cells are usually ground/sky/shadow and would merge into one
    giant blob). 8-connectivity within same class. Returns (comps, dropped):
    sorted by size desc, capped at `top`, plus count of dropped smaller ones.
    px: optional pixel accessor px[x,y] (fine-res image); when given, each
    component accumulates sum_rgb/sum_luma over its cells for readback."""
    labels = [[None] * W for _ in range(H)]
    comps = []
    for y in range(H):
        for x in range(W):
            ch = cells[y][x]
            if ch not in chromatic_set or labels[y][x] is not None:
                continue
            # BFS 8-connectivity within same class
            stack = [(x, y)]
            labels[y][x] = ch
            pix = []
            sr = sg = sb = 0
            while stack:
                cx, cy = stack.pop()
                pix.append((cx, cy))
                if px is not None:
                    r, g, b = px[cx, cy][:3]
                    sr += r
                    sg += g
                    sb += b
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        nx, ny = cx + dx, cy + dy
                        if (0 <= nx < W and 0 <= ny < H and labels[ny][nx] is None
                                and cells[ny][nx] == ch):
                            labels[ny][nx] = ch
                            stack.append((nx, ny))
            if len(pix) < min_cells:
                continue
            xs = [p[0] for p in pix]
            ys = [p[1] for p in pix]
            comps.append({
                "cls": ch,
                "n_cells": len(pix),
                "bbox_cells": (min(xs), min(ys), max(xs), max(ys)),
                "centroid_cells": (sum(xs) / len(xs), sum(ys) / len(ys)),
                "sum_rgb": (sr, sg, sb) if px is not None else None,
            })
    comps = merge_close(comps, gap=1)
    comps.sort(key=lambda c: (-c["n_cells"], c["bbox_cells"]))
    return comps[:top], max(0, len(comps) - top)



def merge_close(comps, gap=1):
    """Merge same-class components whose bboxes are within `gap` cells
    (antialiasing splits one object into a few components)."""
    changed = True
    while changed:
        changed = False
        out = []
        while comps:
            c = comps.pop()
            merged = False
            for i, o in enumerate(out):
                if o["cls"] != c["cls"]:
                    continue
                ox0, oy0, ox1, oy1 = o["bbox_cells"]
                cx0, cy0, cx1, cy1 = c["bbox_cells"]
                if (cx0 <= ox1 + gap and ox0 <= cx1 + gap
                        and cy0 <= oy1 + gap and oy0 <= cy1 + gap):
                    xs, ys = [], []
                    n = o["n_cells"] + c["n_cells"]
                    # weighted centroid
                    ocx = (o["centroid_cells"][0] * o["n_cells"]
                           + c["centroid_cells"][0] * c["n_cells"]) / n
                    ocy = (o["centroid_cells"][1] * o["n_cells"]
                           + c["centroid_cells"][1] * c["n_cells"]) / n
                    srgb = None
                    if o.get("sum_rgb") is not None and c.get("sum_rgb") is not None:
                        srgb = tuple(a + b for a, b in zip(o["sum_rgb"], c["sum_rgb"]))
                    out[i] = {"cls": o["cls"], "n_cells": n,
                              "bbox_cells": (min(ox0, cx0), min(oy0, cy0),
                                             max(ox1, cx1), max(oy1, cy1)),
                              "centroid_cells": (ocx, ocy),
                              "sum_rgb": srgb}
                    merged = True
                    changed = True
                    break
            if not merged:
                out.append(c)
        comps = out
    return comps

def comp_fracs(c, W, H):
    bx0, by0, bx1, by1 = c["bbox_cells"]
    cx, cy = c["centroid_cells"]
    return {
        "bbox_frac": [round(bx0 / W, 3), round(by0 / H, 3),
                      round((bx1 + 1) / W, 3), round((by1 + 1) / H, 3)],
        "centroid_frac": [round((cx + 0.5) / W, 3), round((cy + 0.5) / H, 3)],
        "height_frac": round((by1 + 1 - by0) / H, 3),
    }


# ---------------------------------------------------------------------------
# Panel rendering
# ---------------------------------------------------------------------------

def render_grid_panel(title, grid, cols, rows, ylabels=True):
    out = ["--- PANEL %s ---" % title]
    out.append("    x: 0.0%s1.0" % (" " * max(1, cols - 8)))
    # ruler with tenths; 5-char prefix aligns marks with grid columns
    marks = [" "] * cols
    for f in range(11):
        x = int(round(f / 10 * (cols - 1)))
        marks[x] = "." if f % 2 else "|"
    out.append("     " + "".join(marks))
    for y in range(rows):
        if ylabels and (y % 5 == 0):
            pre = "%.2f " % (y / rows)
        else:
            pre = "     "
        out.append(pre + grid[y])
    return out


def classify_color(rgb, palette_meta, sat_thresh, w=None):
    """Hue-dominant classifier.

    palette_meta: list of (char, ref_rgb, chromatic_bool). Chromatic refs are
    only eligible when pixel saturation >= sat_thresh. Distances:
      chromatic ref:  w_h*hue_circ + w_s*|ds| + w_v*|dv|
      achromatic ref: w_v*|dv| + achr_pen*s_p   (saturated pixels sit far from gray)
    w = dict(w_h, w_s, w_v, achp). Returns class char."""
    w = w or {"w_h": 2.0, "w_s": 0.5, "w_v": 0.25, "achp": 0.5}
    h, s, v = colorsys.rgb_to_hsv(rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0)
    best, bd = None, None
    for ch, ref, chromatic in palette_meta:
        rh, rs, rv = colorsys.rgb_to_hsv(ref[0] / 255.0, ref[1] / 255.0,
                                         ref[2] / 255.0)
        if chromatic:
            if s < sat_thresh:
                continue
            dh = abs(h - rh)
            dh = min(dh, 1.0 - dh)  # circular hue, turns 0..1
            d = w["w_h"] * dh + w["w_s"] * abs(s - rs) + w["w_v"] * abs(v - rv)
        else:
            d = w["w_v"] * abs(v - rv) + w["achp"] * s
        if bd is None or d < bd:
            best, bd = ch, d
    return best


def build_cells_small(im, args, W, H, sat_floor=None):
    """Return (color_cells, luma_idx, luma_vals, edge_vals) small-grid data."""
    small = im.resize((W, H), Image.BOX)
    px = small.load()
    luma_vals = [[luma(px[x, y]) / 255.0 for x in range(W)] for y in range(H)]
    color_cells = [[classify_color(px[x, y], args._palette_meta,
                                   sat_floor if sat_floor is not None else args.sat_thresh)
                    for x in range(W)] for y in range(H)]
    inv = [[1.0 - v for v in row] for row in luma_vals]
    luma_idx = dither_luma(inv, len(args._ramp), args.dither)
    edge_vals = sobel(luma_vals)
    return color_cells, luma_idx, luma_vals, edge_vals


def fine_components(im, args, region_label=None, fx=None):
    """Component table at --fine-comp x internal resolution with a lowered
    saturation floor, so objects that dilute below threshold at display
    resolution (tiny/distant figures) still register. fx = (x0,y0,x1,y1)
    full-frame fractions of this region: when given (tiles/crops), component
    coordinates are REMAPPED to full-frame fractions so consumers never
    juggle coordinate frames. Each row carries readback: rgb (mean color of
    the component's cells, post-transform), lum (mean luma), fill (cells /
    bbox area; 1.0 = solid, low = sparse/elongated), edge (which FULL-FRAME
    edges the bbox touches after remap -- a tile-internal cut reports none).
    Returns (lines, )."""
    if region_label is None:
        region_label = getattr(args, "_region_label", "full frame")
    f = args.fine_comp
    W, H = args._W * f, args._H * f
    small = im.resize((W, H), Image.BOX)
    px = small.load()
    sat_floor = min(0.08, args.sat_thresh * 0.6)
    cells = [[classify_color(px[x, y], args._palette_meta, sat_floor)
              for x in range(W)] for y in range(H)]
    chromatic_set = {ch for ch, ref, chrom in args._palette_meta if chrom}
    comps, dropped = components(cells, W, H, chromatic_set, px=px)
    lines = ["--- COMPONENTS fine (%s, internal %dx, sat>=%.2f; fracs are "
             "FULL-FRAME): id cls cells bbox_frac[x0,y0,x1,y1] centroid_frac "
             "height_frac rgb lum fill edge ---"
             % (region_label, f, sat_floor)]
    if not comps:
        lines.append("(no chromatic components >= 2 cells even at fine "
                     "resolution -> no colored objects detected)")
        return lines
    for i, c in enumerate(comps, 1):
        fr = comp_fracs(c, W, H)
        if fx:
            fx0, fy0, fx1, fy1 = fx
            fr["bbox_frac"] = [round(fx0 + v * (fx1 - fx0), 3) if k % 2 == 0
                               else round(fy0 + v * (fy1 - fy0), 3)
                               for k, v in enumerate(fr["bbox_frac"])]
            fr["centroid_frac"] = [round(fx0 + fr["centroid_frac"][0] * (fx1 - fx0), 3),
                                   round(fy0 + fr["centroid_frac"][1] * (fy1 - fy0), 3)]
            fr["height_frac"] = round(fr["height_frac"] * (fy1 - fy0), 3)
        # readback fields (D2)
        edges = ""
        EPS = 0.002  # bbox border flush with the FULL-FRAME edge (post-remap)
        bx = fr["bbox_frac"]
        if bx[0] <= EPS:
            edges += "L"
        if bx[2] >= 1 - EPS:
            edges += "R"
        if bx[1] <= EPS:
            edges += "T"
        if bx[3] >= 1 - EPS:
            edges += "B"
        if c.get("sum_rgb") is not None:
            n = c["n_cells"]
            mr, mg, mb = [round(v / n) for v in c["sum_rgb"]]
            ml = round(luma((mr, mg, mb)) / 255.0, 2)
            area = max(1, (c["bbox_cells"][2] - c["bbox_cells"][0] + 1)
                       * (c["bbox_cells"][3] - c["bbox_cells"][1] + 1))
            fill = round(c["n_cells"] / area, 2)
            rb = "rgb=%d,%d,%d lum=%.2f fill=%.2f edge=%s" % (
                mr, mg, mb, ml, fill, edges or "none")
        else:  # no pixel accessor (direct components() callers)
            rb = "edge=%s" % (edges or "none")
        lines.append("%2d %s %5d [%s] (%s) %s %s"
                     % (i, c["cls"], c["n_cells"],
                        ",".join(str(v) for v in fr["bbox_frac"]),
                        ",".join(str(v) for v in fr["centroid_frac"]),
                        fr["height_frac"], rb))
    if dropped:
        lines.append("(+%d smaller components dropped)" % dropped)
    return lines


# ---------------------------------------------------------------------------
# Main pack builder
# ---------------------------------------------------------------------------

def build_pack(im, args, region_label=None, fx=None):
    """Build pack text for PIL image `im` (already cropped). fx: full-frame
    fractional crop of this region (tiles/crops) for component remapping."""
    if region_label is None:
        region_label = getattr(args, "_region_label", "full frame")
    W, H, cols, rows = args._W, args._H, args._cols, args._rows
    color_cells, luma_idx, luma_vals, edge_vals = build_cells_small(im, args, W, H)
    meta = {ch: (ref, chrom) for ch, ref, chrom in args._palette_meta}
    out = []

    # stats
    n = W * H
    mean_l = sum(sum(r) for r in luma_vals) / n
    var = sum((v - mean_l) ** 2 for r in luma_vals for v in r) / n
    class_count = {}
    for r in color_cells:
        for ch in r:
            class_count[ch] = class_count.get(ch, 0) + 1
    chromatic_share = sum(v for k, v in class_count.items() if meta[k][1]) / n
    stdev = var ** 0.5
    near_empty = mean_l < 0.12 or stdev < 0.035
    low_color = chromatic_share < 0.015
    share = ", ".join("%s %.1f%%" % (k, 100.0 * v / n)
                      for k, v in sorted(class_count.items(), key=lambda kv: -kv[1])[:12])
    out.append("--- STATS (%s) ---" % region_label)
    flags = []
    is_tile = region_label.startswith("tile")
    if near_empty:
        if is_tile:
            flags.append("mostly-uniform region (tile-local: little content "
                         "here is normal for background tiles; the STOP gate "
                         "is the FULL-FRAME stats only)")
        else:
            flags.append("very-dark-or-near-constant image: expect little content")
    if low_color:
        flags.append("low color diversity (achromatic image)")
    out.append("mean_luma=%.2f stdev=%.2f chromatic=%.1f%% %s"
               % (mean_l, stdev, 100.0 * chromatic_share,
                  ("[" + "; ".join(flags) + "]") if flags else ""))
    out.append("class_share: " + share)

    if args.mode in ("color", "all"):
        out += render_grid_panel("color-class (%s palette)" % args.palette,
                                 ["".join(r) for r in color_cells], cols, rows)
    if args.mode in ("luma", "all"):
        ramp = args._ramp
        grid = ["".join(ramp[i] for i in row) for row in luma_idx]
        out += render_grid_panel("luma (%s, dither=%s; ' '=light ... '%s'=dark)"
                                 % (args.charset, args.dither, args._ramp[-1]),
                                 grid, cols, rows)
    if args.mode == "edge":
        eramp = " .#"
        grid = ["".join(eramp[min(2, int(v * 3))] for v in row) for row in edge_vals]
        out += render_grid_panel("edges (sobel)", grid, cols, rows)
    if args.mode == "all" and not getattr(args, "_no_edge", False):
        eramp = " .#"
        grid = ["".join(eramp[min(2, int(v * 3))] for v in row) for row in edge_vals]
        out += render_grid_panel("edges (sobel)", grid, cols, rows)

    if args.components and args.fine_comp > 1:
        out += fine_components(im, args, region_label, fx)
    return out


# ---------------------------------------------------------------------------
# Auto variant selection (R5 D1) -- thresholds calibrated on the 16-image
# corpus (scripts/calibrate_auto.py), traced to measured R1->R3 lessons:
#   R0 near-empty (S7): no param change, STATS flag already warns
#   R1 dark-monochrome (C5_dusk A3 0.38 -> A3gamma 0.60; VLM 0.29 there):
#      dark_frac>0.08 AND mean<0.40 AND stdev<0.15 -> gamma 1.8+autocontrast
#   R2 hue-collision (S8 0.53 -> 0.72 with web16): >=5 occupied 20-deg hue
#      bins (sat>=floor, >=1% mass each) -> WARNING only (palette is domain
#      vocabulary; the tool must not switch it silently)
#   R3 smooth gradient (S6): NOT R1 AND stdev>0.06 AND strong-edge
#      fraction<0.05 -> fs dither on the luma panel
# Rules never override explicit flags (see auto_select docstring).
# ---------------------------------------------------------------------------

def sample_stats(im, W, H, sat_floor):
    """Display-res BOX downscale stats for auto_select (pre-transform)."""
    small = im.resize((W, H), Image.BOX)
    px = small.load()
    lv = [[luma(px[x, y]) / 255.0 for x in range(W)] for y in range(H)]
    n = W * H
    mean = sum(sum(r) for r in lv) / n
    stdev = (sum((v - mean) ** 2 for r in lv for v in r) / n) ** 0.5
    dark = sum(1 for r in lv for v in r if v < 0.15) / n
    ed = sobel(lv)
    edge_frac = sum(1 for r in ed for v in r if v > 0.15) / n
    bins = [0] * 18
    for y in range(H):
        for x in range(W):
            s, v = sat_val(px[x, y][:3])
            if s >= sat_floor and v > 0.12:
                h = colorsys.rgb_to_hsv(px[x, y][0] / 255.0,
                                        px[x, y][1] / 255.0,
                                        px[x, y][2] / 255.0)[0]
                bins[int(h * 18) % 18] += 1
    huebins = sum(1 for b in bins if b / n >= 0.01)
    return {"mean": mean, "stdev": stdev, "dark_frac": dark,
            "edge_frac": edge_frac, "huebins": huebins}


def auto_select(stats, explicit):
    """Pure rule engine. stats: sample_stats dict. explicit: dict of
    user-set params that auto must NOT override (gamma/dither None means
    unset; autocontrast False means unset). Returns (changes, fired, warns):
    changes only carries fills for unset params, fired is the rule-id list,
    warns are stderr advisories."""
    mean, stdev = stats["mean"], stats["stdev"]
    fired, warns = [], []
    changes = {}
    r0 = mean < 0.12 or stdev < 0.035
    r1 = (not r0 and stats["dark_frac"] > 0.08 and mean < 0.40
          and stdev < 0.15)
    if r0:
        fired.append("r0")
    if r1:
        fired.append("r1")
        if explicit["gamma"] is None:
            changes["gamma"] = 1.8
        if not explicit["autocontrast"]:
            changes["autocontrast"] = True
    if stats["huebins"] >= 5:
        fired.append("r2")
        warns.append("r2: hue-diverse image (%d hue bins) -- if hue nuance "
                     "matters, consider --palette web16" % stats["huebins"])
    if not r0 and not r1 and stdev > 0.06 and stats["edge_frac"] < 0.05 \
            and explicit.get("_mode", "all") in ("all", "luma"):
        fired.append("r3")
        if explicit["dither"] is None:
            changes["dither"] = "fs"
    return changes, fired, warns


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------

def build_pack_from_path(path, **opts):
    """Full pipeline: image path -> pack text. The stable programmatic entry
    point (vlm_critique.py --with-pack imports this). See main() for the
    option names and defaults; explicit opts always win over --auto."""
    o = {
        "cols": 96, "rows": 0, "mode": "all", "charset": "art10",
        "dither": None, "gamma": None, "autocontrast": False,
        "palette": "scene", "sat_thresh": 0.15, "crop": None, "tiles": 0,
        "components": False, "fine_comp": 4, "no_header": False,
        "no_guide": False, "no_legend": False, "minimal": False,
        "max_cols": 160,
        "force": False, "auto": False, "header_text": None,
    }
    unknown = set(opts) - set(o)
    if unknown:
        raise TypeError("unknown options: %s" % sorted(unknown))
    o.update(opts)
    if o["minimal"]:
        # round-G sB: --minimal stripped the legend, but gotcha #53
        # says the legend is MANDATORY for blindness-safe reading —
        # minimal now keeps it (drops header/guide only)
        o["no_header"] = o["no_guide"] = True
    if o["cols"] > o["max_cols"] and not o["force"]:
        raise ValueError("cols=%d > max_cols %d (pass force=True to override)"
                         % (o["cols"], o["max_cols"]))

    try:
        im = Image.open(path)
        im = im.convert("RGB")
    except FileNotFoundError:
        raise SystemExit("image not found: %s" % path)
    except Exception as e:
        raise SystemExit("cannot read image %s: %s" % (path, e))
    sw, sh = im.size
    crop = parse_crop(o["crop"]) if o["crop"] else (0.0, 0.0, 1.0, 1.0)
    im = im.crop((int(crop[0] * sw), int(crop[1] * sh),
                  int(crop[2] * sw), int(crop[3] * sh)))
    if im.size[0] < 1 or im.size[1] < 1:
        raise ValueError("--crop yields an empty region at this image size "
                         "(%dx%d source, crop %s)" % (sw, sh, o["crop"]))

    args = argparse.Namespace(**o)
    args._palette = _load_palette(o["palette"])
    args._ramp = CHARSETS[o["charset"]]
    args._palette_meta = _palette_meta(args._palette)

    def set_dims(aspect_wh):
        args._cols = o["cols"]
        args._rows = o["rows"] if o["rows"] else max(
            6, round(o["cols"] * aspect_wh * 0.5))
        args._W, args._H = args._cols, args._rows

    set_dims(im.size[1] / im.size[0])

    # auto variant selection on POST-CROP, PRE-TRANSFORM pixels (D1).
    # Stats use a CANONICAL 96-wide grid (not the requested --cols): rule
    # thresholds were calibrated at that size and edge/dark fractions drift
    # with grid resolution -- auto must characterize the image, not the
    # display grid.
    auto_token = ""
    explicit = {"gamma": o["gamma"], "dither": o["dither"],
                "autocontrast": o["autocontrast"], "_mode": o["mode"]}
    if o["auto"]:
        aw = 96
        ah = max(6, round(aw * im.size[1] / im.size[0] * 0.5))
        st = sample_stats(im, aw, ah, o["sat_thresh"])
        changes, fired, warns = auto_select(st, explicit)
        for k, v in changes.items():
            setattr(args, k, v)
        for w in warns:
            sys.stderr.write("ascii_vision: %s\n" % w)
        if fired:
            auto_token = " auto=%s" % "+".join(fired)
        else:
            auto_token = " auto=none"  # explicit echo: auto ran, nothing fired
    args.gamma = 1.0 if args.gamma is None else args.gamma
    args.dither = "none" if args.dither is None else args.dither

    if args.autocontrast:
        im = ImageOps.autocontrast(im, cutoff=1)
    if args.gamma != 1.0:
        lut = [min(255, int(255 * ((i / 255.0) ** (1.0 / args.gamma)))) for i in range(256)]
        im = im.point(lut * 3)

    args._region_label = ("full frame" if o["crop"] is None
                          else "crop=%s" % o["crop"])
    if o["header_text"] is not None:
        head0 = o["header_text"]
    elif o["no_header"]:
        head0 = "== ASCII-VISION PACK =="
    else:
        head0 = "== ASCII-VISION PACK: %s (%dx%d) ==" % (
            os.path.basename(path), sw, sh)
    head = [head0,
            "params: cols=%d rows=%d mode=%s charset=%s dither=%s gamma=%.2f "
            "autocontrast=%s sat_thresh=%.2f palette=%s crop=%s tiles=%d "
            "components=%s fine_comp=%d%s"
            % (args._cols, args._rows, args.mode, args.charset, args.dither,
               args.gamma, args.autocontrast, args.sat_thresh, args.palette,
               args.crop or "full", args.tiles, args.components,
               args.fine_comp, auto_token)]
    if not o["no_guide"]:
        head += GUIDE.split("\n")

    body = build_pack(im, args, fx=(crop if o["crop"] else None))

    # zoom tiles
    if o["tiles"]:
        N = o["tiles"]
        ox0, oy0, ox1, oy1 = crop
        fw, fh = (ox1 - ox0), (oy1 - oy0)
        ov = 0.10  # 10% context bleed
        for ty in range(N):
            for tx in range(N):
                cx0 = ox0 + fw * tx / N
                cy0 = oy0 + fh * ty / N
                cx1 = ox0 + fw * (tx + 1) / N
                cy1 = oy0 + fh * (ty + 1) / N
                # bleed, clamped to the outer crop
                bx0 = max(ox0, cx0 - fw * ov / N)
                by0 = max(oy0, cy0 - fh * ov / N)
                bx1 = min(ox1, cx1 + fw * ov / N)
                by1 = min(oy1, cy1 + fh * ov / N)
                tim = im.crop((int((bx0 - ox0) / fw * im.size[0]),
                               int((by0 - oy0) / fh * im.size[1]),
                               int((bx1 - ox0) / fw * im.size[0]),
                               int((by1 - oy0) / fh * im.size[1])))
                sub = argparse.Namespace(**vars(args))
                sub._cols = max(40, sub.cols * 3 // 4)
                sub._rows = max(6, round(sub._cols * tim.size[1] / tim.size[0] * 0.5))
                sub._W, sub._H = sub._cols, sub._rows
                sub._no_edge = True
                lbl = ("tile[%d,%d] full-frame crop=%.3f,%.3f,%.3f,%.3f"
                       % (ty, tx, bx0, by0, bx1, by1))
                body += [""] + build_pack(tim, sub, lbl,
                                          fx=(bx0, by0, bx1, by1))

    if not o["no_legend"]:
        legend = ["--- LEGEND ---"]
        pal = args._palette
        descs = {" ": "light-gray/sky*", ".": "mid-gray/street*", "B": "blue", "R": "red",
                 "A": "amber", "G": "green", "S": "skin", "K": "khaki", "D": "dark*",
                 "#": "vivid blue"}
        legend.append("color classes (* = achromatic, always eligible): " + "  ".join(
            "%s=%s" % (ch, descs.get(ch, "rgb%s" % (pal[ch],))) for ch in pal))
        legend.append("luma ramp '%s': ' '=light ... '%s'=dark; edges: ' .#' weak->strong"
                      % (args._ramp, args._ramp[-1]))
        body += legend

    return "\n".join(head + body) + "\n"


def _load_palette(name):
    if name == "scene":
        return SCENE_PALETTE
    if name == "web16":
        return WEB16_PALETTE
    try:
        with open(name) as f:
            pal = json.load(f)
    except FileNotFoundError:
        raise SystemExit("palette file not found: %s" % name)
    except json.JSONDecodeError as e:
        raise SystemExit("palette file is not valid JSON (%s): %s" % (name, e))
    if not pal:
        raise SystemExit("palette %s is empty (needs at least one class)" % name)
    return {k: tuple(v) for k, v in pal.items()}


def _palette_meta(palette):
    """Per-ref chromaticity: refs with saturation >= 0.18 need the pixel to
    pass --sat-thresh; achromatic refs (grays/black/white/dark) always
    compete."""
    pal = {ch: ([v] if v and isinstance(v[0], int) else list(v))
           for ch, v in palette.items()}
    meta = []
    for ch, refs in pal.items():
        for ref in refs:
            meta.append((ch, ref, sat_val(ref)[0] >= 0.18))
    return meta


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image")
    ap.add_argument("--cols", type=int, default=96)
    ap.add_argument("--rows", type=int, default=0, help="0 = auto (aspect*0.5)")
    ap.add_argument("--mode", choices=["luma", "color", "edge", "all"], default="all")
    ap.add_argument("--charset", choices=sorted(CHARSETS), default="art10")
    ap.add_argument("--dither", choices=["none", "fs", "bayer4", "bayer8"],
                    default=None,
                    help="None = unset (auto may choose; explicit 'none' blocks auto)")
    ap.add_argument("--gamma", type=float, default=None,
                    help="None = unset (auto may choose; explicit 1.0 blocks auto)")
    ap.add_argument("--autocontrast", action="store_true")
    ap.add_argument("--auto", action="store_true",
                    help="auto-variant selection: apply calibrated param rules "
                         "(R5_SPEC D1); explicit flags always win")
    ap.add_argument("--palette", default="scene",
                    help="scene|web16|path to JSON {char:[r,g,b]}")
    ap.add_argument("--sat-thresh", type=float, default=0.15)
    ap.add_argument("--crop", type=str, default=None)
    ap.add_argument("--tiles", type=int, default=0, help="N -> overview + NxN zoom tiles")
    ap.add_argument("--components", action="store_true")
    ap.add_argument("--fine-comp", type=int, default=4,
                    help="internal resolution multiplier for the components "
                         "pass (default 4; values < 2 disable the components "
                         "pass); lets tiny/distant "
                         "objects that dilute at display resolution register")
    ap.add_argument("--no-header", action="store_true",
                    help="omit the filename header line (blindness-safe packs)")
    ap.add_argument("--no-guide", action="store_true")
    ap.add_argument("--no-legend", action="store_true")
    ap.add_argument("--minimal", action="store_true",
                    help="shorthand for --no-header --no-guide --no-legend "
                         "(minimal blindness-safe pack: params + panels + "
                         "components tables only)")
    ap.add_argument("--max-cols", type=int, default=160)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--out", default=None, help="also write pack to file")
    a = ap.parse_args()

    opts = dict(cols=a.cols, rows=a.rows, mode=a.mode, charset=a.charset,
                dither=a.dither, gamma=a.gamma, autocontrast=a.autocontrast,
                auto=a.auto, palette=a.palette, sat_thresh=a.sat_thresh,
                crop=a.crop, tiles=a.tiles, components=a.components,
                fine_comp=a.fine_comp,
                no_header=a.no_header or a.minimal,
                no_guide=a.no_guide or a.minimal,
                no_legend=a.no_legend or a.minimal,
                max_cols=a.max_cols, force=a.force)
    try:
        text = build_pack_from_path(a.image, **opts)
    except ValueError as e:
        raise SystemExit(str(e))
    sys.stdout.write(text)
    if a.out:
        try:
            with open(a.out, "w") as f:
                f.write(text)
        except OSError as e:
            raise SystemExit("cannot write --out %s: %s" % (a.out, e))


if __name__ == "__main__":
    main()
