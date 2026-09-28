#!/usr/bin/env python3
"""Synthetic 640x360 corpus for the ASCII-vision experiment.

Builds the 10 scenes listed in experiments/ascii_vision/SPEC.md, section
"Synthetic (corpus/synthetic/)", with Pillow, and writes an exact
<name>.truth.json next to each PNG (schema in SPEC: bbox_frac /
centroid_frac / height_frac as FRACTIONS of frame, origin top-left, y down,
plus floating / intersects / touch_edge / visible / count_group, counts,
image_stats, notes).

Design rules:
- Supersample 4x (2560x1440), then LANCZOS-downscale to 640x360 so all edges
  are antialiased (ASCII + VLM both do better; mirrors real renders).
- Ground line at y = 0.75*H = 270; bottom 25% band is slightly darker gray.
- Capsule figure = rounded-rectangle body + circle head (kit actor style).
- Deterministic: fixed RNG seed, no clock, no hash order.
- Planted cases (per SPEC): S1 amber1 floats 0.2 frame-heights above the
  ground line; S3 blue1 half out of frame LEFT + red1 touches right edge;
  S4 four tiny (<2% frame height) objects + one ABSENT trap (red2,
  visible=false, never drawn, excluded from counts); S5 amber1 intersects
  khaki1 by ~30% of amber1 bbox area; S7 near-empty low-contrast trap.

CLI:
  python3 scripts/corpus_synthetic.py [--out experiments/ascii_vision/corpus/synthetic] [--only S1,S2]

On every run a self-audit runs after generation (bbox ranges, floating
plants, absent-trap pixel probe, centroid pixel readback, counts
consistency) and a summary table of the corpus is printed. Exit 1 on audit
failure.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageStat

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = REPO_ROOT / "experiments" / "ascii_vision" / "corpus" / "synthetic"

W, H = 640, 360
SS = 4                       # supersample factor: draw at W*SS x H*SS, LANCZOS down
SCALE = 1.0                  # runtime output scale (R5 D5 --scale): draw at
                             # W*SS*SCALE, downscale to W*SCALE x H*SCALE;
                             # scene code + truth fractions stay 640x360-space
GROUND_Y = H * 0.75          # 270: top of the darker ground band (bottom 25%)

# --- kit palette (SPEC DEFAULT_VOCAB / scene palette) -----------------------
BLUE = (61, 109, 181)
RED = (193, 68, 68)
AMBER = (217, 151, 59)
GREEN = (109, 127, 99)       # green-gray zombie
KHAKI = (115, 100, 80)
BG_GRAY = (120, 120, 120)
GROUND_GRAY = (100, 100, 100)  # slightly darker ground band

CLASS_RGB = {
    "BLUE": BLUE, "RED": RED, "AMBER": AMBER, "GREEN": GREEN, "KHAKI": KHAKI,
    "DARK": (28, 28, 28), "GRAY": (35, 35, 40),
    "CYAN": (60, 160, 200), "NAVY": (25, 35, 110), "TEAL": (50, 150, 140),
    "PURPLE": (110, 60, 180), "ROAD": (75, 75, 75), "BUILDING": None,
}

TOL_PIXEL = 60     # max per-channel deviation for the visible-object probe
TOL_TRAP = 30      # trap probe: pixel closer than this to class color = FAIL
COV_THRESH = 14    # per-channel bg deviation to count a cell as non-bg


# ---------------------------------------------------------------------------
# drawing canvas: all scene code works in 640x360 float coords
# ---------------------------------------------------------------------------
class Canvas:
    """Rasterizes at SSx (x SCALE) so the LANCZOS downscale antialiases every
    edge. All scene code draws in 640x360 float coords regardless of SCALE."""

    def __init__(self):
        self.img = Image.new("RGB", (round(W * SS * SCALE), round(H * SS * SCALE)),
                             BG_GRAY)
        self.d = ImageDraw.Draw(self.img)

    def rect(self, box, color):
        self.d.rectangle([round(v * SS * SCALE) for v in box], fill=color)

    def ellipse(self, box, color):
        self.d.ellipse([round(v * SS * SCALE) for v in box], fill=color)

    def vgradient(self, top_rgb, bottom_rgb):
        """Full-frame vertical light->dark gradient, exact per raster row."""
        hpx = self.img.size[1]
        wpx = self.img.size[0]
        for y4 in range(hpx):
            t = (y4 + 0.5) / hpx
            self.d.line([(0, y4), (wpx, y4)],
                        fill=tuple(round(top_rgb[i] + (bottom_rgb[i] - top_rgb[i]) * t)
                                   for i in range(3)))

    def capsule(self, cx, bottom, h, color):
        """Capsule figure (rounded-rect body + circle head). Returns exact
        640-space bbox [x0, y0, x1, y1] = the object's full drawn extent."""
        w = 0.45 * h
        r = 0.19 * h
        x0, x1 = cx - w / 2, cx + w / 2
        top = bottom - h
        body_top = top + 1.55 * r              # head overlaps body slightly
        rad = min(w / 2, (bottom - body_top) / 2)
        self.d.rounded_rectangle(
            [round(x0 * SS * SCALE), round(body_top * SS * SCALE),
             round(x1 * SS * SCALE), round(bottom * SS * SCALE)],
            radius=round(rad * SS * SCALE), fill=color)
        self.ellipse([cx - r, top, cx + r, top + 2 * r], color)
        return [x0, top, x1, bottom]

    def sphere(self, cx, cy, r, color):
        self.ellipse([cx - r, cy - r, cx + r, cy + r], color)
        return [cx - r, cy - r, cx + r, cy + r]


def default_bg(c, sky=BG_GRAY, ground=GROUND_GRAY, gy=GROUND_Y):
    c.rect([0, 0, W, H], sky)
    c.rect([0, gy, W, H], ground)


# ---------------------------------------------------------------------------
# truth object builder
# ---------------------------------------------------------------------------
def _fracs(b):
    return [round(b[0] / W, 5), round(b[1] / H, 5), round(b[2] / W, 5), round(b[3] / H, 5)]


def obj(oid, cls, bbox, *, floating=False, intersects=(), touch_edge=None,
        visible=True, group="main", rgb=None, extra=None):
    x0, y0, x1, y1 = bbox
    o = {
        "id": oid,
        "class": cls,
        "bbox_frac": _fracs(bbox),
        "centroid_frac": [round((x0 + x1) / 2 / W, 5), round((y0 + y1) / 2 / H, 5)],
        "height_frac": round((y1 - y0) / H, 5),
        "floating": floating,
        "intersects": list(intersects),
        "touch_edge": touch_edge,
        "visible": visible,
        "count_group": group,
    }
    if extra:
        o.update(extra)
    # audit-only planted color, stripped before writing JSON
    o["_rgb"] = rgb if rgb is not None else CLASS_RGB.get(cls)
    return o


# ---------------------------------------------------------------------------
# the 10 SPEC scenes
# ---------------------------------------------------------------------------
def scene_S1(c):
    """S1_three_figures - blue/red/amber capsules on gray ground, amber FLOATS."""
    default_bg(c)
    bb = c.capsule(140, GROUND_Y, 100, BLUE)
    br = c.capsule(320, GROUND_Y, 100, RED)
    ba = c.capsule(500, GROUND_Y - 0.2 * H, 100, AMBER)  # bottom 72px above ground line
    objs = [
        obj("blue1", "BLUE", bb),
        obj("red1", "RED", br),
        obj("amber1", "AMBER", ba, floating=True),
    ]
    return objs, {"BLUE": 1, "RED": 1, "AMBER": 1}, (
        "amber1 planted floating 0.2 frame-heights above the ground line "
        "(bottom y=198 vs ground 270); blue1/red1 stand on ground")


def scene_S2(c):
    """S2_crowd - 27 small green capsules + 3 color figures (count question)."""
    default_bg(c)
    objs = []
    for cx, cls, col in ((120, "BLUE", BLUE), (320, "RED", RED), (520, "AMBER", AMBER)):
        objs.append(obj(cls.lower() + "1", cls, c.capsule(cx, GROUND_Y, 90, col)))
    rng = random.Random(20240607)          # deterministic jitter
    for i in range(27):
        row, col_i = divmod(i, 9)
        x = 60 + col_i * 65 + rng.uniform(-14, 14)
        ybot = (292, 318, 344)[row]
        objs.append(obj(f"zombie{i + 1}", "GREEN", c.capsule(x, ybot, 22, GREEN),
                        group="crowd"))
    return objs, {"BLUE": 1, "RED": 1, "AMBER": 1, "GREEN": 27}, (
        "27 small green capsules (crowd, h=22px=6.1% frame height, jittered 9x3 grid) "
        "+ 3 color figures; zombie red eyes omitted (would pollute the RED count)")


def scene_S3(c):
    """S3_edge_cut - blue cube half out of frame LEFT; red sphere touches right edge."""
    default_bg(c)
    c.rect([-60, 150, 60, 270], BLUE)      # drawn from x=-60: half out of frame
    blue_visible = [0.0, 150, 60, 270]     # visible (frame-clamped) bbox
    red = c.sphere(W - 55, 215, 55, RED)   # right edge exactly touches x=640
    objs = [
        obj("blue1", "BLUE", blue_visible, touch_edge="left"),
        obj("red1", "RED", red, touch_edge="right"),
    ]
    return objs, {"BLUE": 1, "RED": 1}, (
        "blue1 cube drawn x=[-60,60] i.e. half out of frame LEFT; bbox_frac is the "
        "VISIBLE frame-clamped bbox; red1 sphere touches right edge (cut, not past)")


TINY_H = 6  # 6/360 = 1.67% of frame height (< 2%)


def scene_S4(c):
    """S4_tiny_distant - 4 tiny objects near horizon + 1 ABSENT trap (not drawn)."""
    default_bg(c)
    objs = []
    for cx, cls, col in ((150, "BLUE", BLUE), (260, "RED", RED),
                         (420, "AMBER", AMBER), (540, "GREEN", GREEN)):
        objs.append(obj(cls.lower() + "1", cls, c.capsule(cx, GROUND_Y, TINY_H, col),
                        group="tiny"))
    # The absent trap: truth entry only. NOT drawn anywhere. Nominal bbox marks
    # where it would have stood (x=330); excluded from counts.
    objs.append(obj("red2", "RED", [327, GROUND_Y - TINY_H, 333, GROUND_Y],
                    visible=False, group="tiny"))
    return objs, {"BLUE": 1, "RED": 1, "AMBER": 1, "GREEN": 1}, (
        f"4 tiny objects (h={TINY_H}px={TINY_H / H:.2%} < 2% frame height) near the "
        "horizon; red2 is the ABSENT TRAP: visible=false, NOT drawn, excluded from "
        "counts; its bbox_frac is the nominal would-be position")


def scene_S5(c):
    """S5_overlap - amber capsule intersects khaki box ~30%; separate red capsule."""
    default_bg(c)
    box = [300, 160, 460, 270]
    c.rect(box, KHAKI)
    ba = c.capsule(468, GROUND_Y, 90, AMBER)   # left edge bites 12.25px into box
    br = c.capsule(560, GROUND_Y, 90, RED)     # separate
    ov_w = min(box[2], ba[2]) - max(box[0], ba[0])
    ov_h = min(box[3], ba[3]) - max(box[1], ba[1])
    ratio = (ov_w * ov_h) / ((ba[2] - ba[0]) * (ba[3] - ba[1]))
    objs = [
        obj("khaki1", "KHAKI", box, intersects=["amber1"]),
        obj("amber1", "AMBER", ba, intersects=["khaki1"]),
        obj("red1", "RED", br),
    ]
    return objs, {"AMBER": 1, "RED": 1, "KHAKI": 1}, (
        f"amber1 intersects khaki1 by {ratio:.1%} of amber1 bbox area (~30% planted); "
        "red1 separate; all resting on the ground line")


def scene_S6(c):
    """S6_gradient - vertical light->dark gradient with dark disc (dither/shading test)."""
    c.vgradient((218, 218, 218), (32, 32, 32))
    disc = c.sphere(320, 140, 70, (28, 28, 28))
    objs = [obj("disc1", "DARK", disc)]
    return objs, {"DARK": 1}, (
        "vertical light->dark gradient (luma 218 top -> 32 bottom) with a dark disc "
        "(28,28,28) upper-center; dither/shading test; no ground concept, floating n/a")


def scene_S7(c):
    """S7_lowcontrast - dark gray shapes on near-black bg (VLM hallucination trap)."""
    c.rect([0, 0, W, H], (8, 8, 10))
    b1 = c.capsule(170, 250, 110, (35, 35, 40))
    b2 = [330, 140, 460, 220]
    c.rect(b2, (35, 35, 40))
    b3 = c.sphere(545, 180, 48, (35, 35, 40))
    objs = [obj("shape1", "GRAY", b1), obj("shape2", "GRAY", b2),
            obj("shape3", "GRAY", b3)]
    return objs, {"GRAY": 3}, (
        "near-empty trap: 3 dark-gray (35,35,40) shapes on near-black (8,8,10) bg, "
        "total coverage < 12% of frame")


S8_PATCHES = [  # reading order: row 0 then row 1
    ("blue1", "BLUE", (40, 80, 200)),
    ("cyan1", "CYAN", (60, 160, 200)),
    ("navy1", "NAVY", (25, 35, 110)),
    ("teal1", "TEAL", (50, 150, 140)),
    ("purple1", "PURPLE", (110, 60, 180)),
    ("green1", "GREEN", (70, 140, 80)),
]


def scene_S8(c):
    """S8_hues - 6 same-size square patches of similar hues (palette-resolution test)."""
    default_bg(c)
    size, gapx, gapy = 110, 45, 40
    x0 = (W - (3 * size + 2 * gapx)) / 2      # 110
    y0 = (H - (2 * size + gapy)) / 2          # 50
    objs = []
    for i, (oid, cls, col) in enumerate(S8_PATCHES):
        r, cc = divmod(i, 3)
        bx = [x0 + cc * (size + gapx), y0 + r * (size + gapy),
              x0 + cc * (size + gapx) + size, y0 + r * (size + gapy) + size]
        c.rect(bx, col)
        objs.append(obj(oid, cls, bx, rgb=col, group="patch"))
    return objs, {"BLUE": 1, "CYAN": 1, "NAVY": 1, "TEAL": 1, "PURPLE": 1,
                  "GREEN": 1}, (
        "6 same-size (110px) square patches of similar hues; note patch BLUE is the "
        "SPEC hue (40,80,200), not kit BLUE (61,109,181)")


def scene_S9(c):
    """S9_street - montage: road + 2 buildings + 3 capsule figures + khaki jeep box."""
    sky, road_c = (135, 135, 135), (75, 75, 75)
    c.rect([0, 0, W, H], sky)
    road = [0, GROUND_Y, W, H]
    c.rect(road, road_c)
    b1, b2 = [80, 120, 220, 270], [420, 90, 560, 270]
    c.rect(b1, (100, 100, 110))
    c.rect(b2, (86, 86, 96))
    objs = [
        obj("road1", "ROAD", road, rgb=road_c),
        obj("bldg1", "BUILDING", b1, rgb=(100, 100, 110)),
        obj("bldg2", "BUILDING", b2, rgb=(86, 86, 96)),
    ]
    for cx, cls, col in ((245, "BLUE", BLUE), (295, "RED", RED), (395, "AMBER", AMBER)):
        objs.append(obj(cls.lower() + "1", cls, c.capsule(cx, 330, 80, col)))
    jeep = [480, 270, 600, 330]
    c.rect(jeep, KHAKI)
    objs.append(obj("jeep1", "KHAKI", jeep))
    return objs, {"BLUE": 1, "RED": 1, "AMBER": 1, "KHAKI": 1, "ROAD": 1,
                  "BUILDING": 2}, (
        "montage: road band (bottom 25%) + 2 building blocks on the horizon + 3 "
        "capsule figures standing on the road + khaki jeep-ish box (plain box, no "
        "wheels, so truth stays exact)")


S10_CYCLE = ("BLUE", "RED", "AMBER")


def scene_S10(c):
    """S10_grid_positions - 9 objects, one per 3x3 cell, colors cycling B/R/A."""
    default_bg(c)
    objs = []
    r_c = 26
    for i in range(9):
        r, cc = divmod(i, 3)
        cx, cy = W * (cc + 0.5) / 3, H * (r + 0.5) / 3
        cls = S10_CYCLE[i % 3]
        objs.append(obj(f"obj_r{r}c{cc}", cls, c.sphere(cx, cy, r_c, CLASS_RGB[cls]),
                        group="grid", extra={"grid_cell": f"r{r}c{cc}"}))
    return objs, {"BLUE": 3, "RED": 3, "AMBER": 3}, (
        "9 objects, one per 3x3 cell (cell centers), colors cycling BLUE/RED/AMBER "
        "in reading order; abstract grid, floating n/a (all false)")


SCENES = [
    ("S1_three_figures", scene_S1),
    ("S2_crowd", scene_S2),
    ("S3_edge_cut", scene_S3),
    ("S4_tiny_distant", scene_S4),
    ("S5_overlap", scene_S5),
    ("S6_gradient", scene_S6),
    ("S7_lowcontrast", scene_S7),
    ("S8_hues", scene_S8),
    ("S9_street", scene_S9),
    ("S10_grid_positions", scene_S10),
]


# ---------------------------------------------------------------------------
# image stats (informational, from actual pixels)
# ---------------------------------------------------------------------------
def bg_image(name):
    """Exact per-scene background model as an image (for coverage stats)."""
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    if name == "S6_gradient":
        for y in range(H):
            t = (y + 0.5) / H
            l = round(218 + (32 - 218) * t)
            d.line([(0, y), (W, y)], fill=(l, l, l))
    elif name == "S7_lowcontrast":
        d.rectangle([0, 0, W, H], fill=(8, 8, 10))
    elif name == "S9_street":
        d.rectangle([0, 0, W, H], fill=(135, 135, 135))
        d.rectangle([0, GROUND_Y, W, H], fill=(75, 75, 75))
    else:
        d.rectangle([0, 0, W, H], fill=BG_GRAY)
        d.rectangle([0, GROUND_Y, W, H], fill=GROUND_GRAY)
    return img


def image_stats(img, name):
    m = ImageStat.Stat(img).mean
    mean_luma = (0.2126 * m[0] + 0.7152 * m[1] + 0.0722 * m[2]) / 255
    small = img.resize((160, 90), Image.Resampling.BOX)
    bgsm = bg_image(name).resize((160, 90), Image.Resampling.BOX)  # same averaging
    sp, bp = small.load(), bgsm.load()
    cov = sum(
        1 for j in range(90) for i in range(160)
        if max(abs(sp[i, j][k] - bp[i, j][k]) for k in range(3)) > COV_THRESH)
    return {"mean_luma": round(mean_luma, 4), "coverage_nonbg": round(cov / 14400, 4)}


# ---------------------------------------------------------------------------
# self-audit (quality gate) + summary table
# ---------------------------------------------------------------------------
def audit(built):
    fails = []
    floating_seen = []
    n_vis = n_invis = 0
    for b in built:
        name, truth = b["name"], b["truth"]
        img = Image.open(b["png"]).convert("RGB")
        iw, ih = img.size  # scale-aware probing (640x360 at SCALE=1)
        for o in truth["objects"]:
            x0, y0, x1, y1 = o["bbox_frac"]
            if not (0 <= x0 <= 1 and 0 <= y0 <= 1 and 0 <= x1 <= 1 and 0 <= y1 <= 1):
                fails.append(f"{name}/{o['id']}: bbox_frac outside [0,1]: {o['bbox_frac']}")
            if o["visible"]:
                n_vis += 1
                if not (x1 > x0 and y1 > y0):
                    fails.append(f"{name}/{o['id']}: visible but empty bbox")
            else:
                n_invis += 1
            if o["floating"]:
                floating_seen.append((name, o["id"]))

        recomputed = {}
        for o in truth["objects"]:
            if o["visible"]:
                recomputed[o["class"]] = recomputed.get(o["class"], 0) + 1
        if recomputed != truth["counts"]:
            fails.append(f"{name}: counts {truth['counts']} != visible objects {recomputed}")

        # pixel probe at every visible object's bbox center (deep inside solid fill)
        for o in truth["objects"]:
            if not o["visible"]:
                continue
            cx = min(round(o["centroid_frac"][0] * iw), iw - 1)
            cy = min(round(o["centroid_frac"][1] * ih), ih - 1)
            px = img.getpixel((cx, cy))
            exp = b["rgb"][o["id"]]
            if max(abs(px[k] - exp[k]) for k in range(3)) > TOL_PIXEL:
                fails.append(f"{name}/{o['id']}: pixel@{cx},{cy}={px}, expected ~{exp}")

        # absent-trap probe: nominal bbox center must NOT match the class color
        for o in truth["objects"]:
            if o["visible"]:
                continue
            cx = min(round((o["bbox_frac"][0] + o["bbox_frac"][2]) / 2 * iw), iw - 1)
            cy = min(round((o["bbox_frac"][1] + o["bbox_frac"][3]) / 2 * ih), ih - 1)
            px = img.getpixel((cx, cy))
            exp = b["rgb"][o["id"]]
            if max(abs(px[k] - exp[k]) for k in range(3)) <= TOL_TRAP:
                fails.append(f"{name}/{o['id']}: TRAP but pixel@{cx},{cy}={px} "
                             f"matches class color {exp} (something was drawn?)")

    if floating_seen != [("S1_three_figures", "amber1")]:
        fails.append(f"floating flags do not match SPEC plants: {floating_seen}")

    for b in built:
        if b["name"] == "S7_lowcontrast":
            cov = b["truth"]["image_stats"]["coverage_nonbg"]
            if cov >= 0.12:
                fails.append(f"S7 coverage {cov} >= 0.12 (near-empty trap broken)")
        if b["name"] == "S4_tiny_distant":
            traps = [o for o in b["truth"]["objects"] if not o["visible"]]
            if len(traps) != 1 or traps[0]["id"] != "red2":
                fails.append(f"S4 absent-trap entry wrong: {[o['id'] for o in traps]}")
            for o in b["truth"]["objects"]:
                if o["visible"] and o["height_frac"] >= 0.02:
                    fails.append(f"S4/{o['id']}: height_frac {o['height_frac']} >= 0.02")
    return fails, n_vis, n_invis


def print_summary(built):
    print("\n=== corpus summary " + "=" * 90)
    hdr = (f"{'scene':<20}{'objs':>5}{'vis':>4}  {'counts':<40}"
           f"{'luma':>5}{'cov%':>6}  notes")
    print(hdr)
    print("-" * len(hdr))
    for b in built:
        t = b["truth"]
        counts = ",".join(f"{k}:{v}" for k, v in t["counts"].items())
        vis = sum(1 for o in t["objects"] if o["visible"])
        st = t["image_stats"]
        print(f"{b['name']:<20}{len(t['objects']):>5}{vis:>4}  {counts:<40}"
              f"{st['mean_luma']:>5.2f}{st['coverage_nonbg'] * 100:>6.1f}  {t['notes']}")


# ---------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Generate the synthetic 640x360 corpus + exact truth.json "
                    "(experiments/ascii_vision/SPEC.md).")
    ap.add_argument("--out", default=str(DEFAULT_OUT),
                    help="output directory (default: %(default)s)")
    ap.add_argument("--only", default="",
                    help="comma list of scenes to build: S1,S2 or full names")
    ap.add_argument("--scale", type=float, default=1.0,
                    help="output scale multiplier (R5 D5: 2.0 -> 1280x720 HD "
                         "set); truth fractions are scale-invariant")
    args = ap.parse_args(argv)

    global SCALE
    SCALE = float(args.scale)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    only = [t.strip() for t in args.only.split(",") if t.strip()] or None

    built = []
    for name, fn in SCENES:
        if only and not any(name == t or name.split("_", 1)[0] == t for t in only):
            continue
        c = Canvas()
        objs, counts, notes = fn(c)
        out_wh = (round(W * SCALE), round(H * SCALE))
        img = c.img.resize(out_wh, Image.Resampling.LANCZOS)
        png = out / f"{name}.png"
        img.save(png)
        truth = {
            "image": png.name,
            "objects": objs,
            "counts": counts,
            "image_stats": image_stats(img, name),
            "notes": notes,
        }
        rgb = {o["id"]: o.pop("_rgb") for o in objs}   # strip audit-only key
        tj = out / f"{name}.truth.json"
        tj.write_text(json.dumps(truth, indent=2) + "\n")
        built.append({"name": name, "png": png, "truth": truth, "rgb": rgb})
        print(f"wrote {png.name} + {tj.name}  objects={len(objs)}  "
              f"stats={truth['image_stats']}")

    if not built:
        print("no scenes matched --only; nothing generated", file=sys.stderr)
        return 2

    fails, n_vis, n_invis = audit(built)
    print_summary(built)
    print(f"\n=== self-audit: {len(built)} scenes, {n_vis} visible + {n_invis} "
          f"absent-trap objects")
    if fails:
        for f in fails:
            print("FAIL:", f)
        print(f"AUDIT: FAIL ({len(fails)} problems)")
        return 1
    print("AUDIT: PASS (bbox ranges, floating plants, absent-trap pixel probe, "
          "centroid pixel readback, counts consistency, S4 <2% heights, S7 <12% cov)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
