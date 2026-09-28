#!/usr/bin/env python3
"""Deterministic regression suite for scripts/ascii_vision.py (R5_SPEC D4).

Scope: the 11 D4 cases (determinism, classifier, component merge/split, tiny
speck, tile remap, edge flag, readback, auto rules, guard rails, io options,
odd inputs) plus the pack_accuracy.parse_pack row-format contract.
stdlib unittest + PIL-generated fixtures in a temp dir ONLY: no committed
corpus, no network, no Blender, no pytest. Run gate from repo root:

    python3 scripts/test_ascii_vision.py        # green + <60 s
"""
import importlib.util
import os
import re
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ascii_vision as av                      # noqa: E402
from PIL import Image, ImageDraw               # noqa: E402

# fixture colors are SCENE_PALETTE refs so classify_color matches by design
BLUE = (61, 109, 181)    # 'B'
RED = (193, 68, 68)      # 'R'
GRAY = (120, 120, 120)   # '.' achromatic background

# pack_accuracy.py is exercised for the D2 row-suffix contract (optional 1 test)
_PA = os.path.join(HERE, "..", "experiments", "ascii_vision", "pack_accuracy.py")
_spec = importlib.util.spec_from_file_location("pack_accuracy_under_test", _PA)
pack_accuracy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pack_accuracy)

# component row: id cls cells [bbox] (centroid) height [rgb= lum= fill= edge=]
# (mirrors pack_accuracy.COMP_ROW so the suite stays independent of that file)
ROW_RE = re.compile(
    r"^\s*(\d+)\s+(\S)\s+(\d+)\s+\[([\d.,eE+-]+)\]\s+\(([\d.,eE+-]+)\)\s+([\d.eE+-]+)"
    r"(?:\s+rgb=([\d.,]+))?(?:\s+lum=([\d.]+))?(?:\s+fill=([\d.]+))?(?:\s+edge=(\S+))?\s*$")


def make_png(path, size, draw_fn=None, mode="RGB", color=GRAY):
    """Solid mid-gray base + draw_fn(ImageDraw) -> saved PNG (deterministic).
    mode='P' quantizes AFTER drawing so the palette keeps the exact color."""
    im = Image.new("RGB" if mode == "P" else mode, size, color)
    if draw_fn:
        draw_fn(ImageDraw.Draw(im))
    if mode == "P":
        im = im.quantize(colors=16)
    im.save(path)
    return path


def parse_comp_rows(pack_text, region_prefix):
    """Rows of the COMPONENTS table whose header names region_prefix
    ('full frame' or 'tile[0,1]'), as dicts. Anchored on the header so guide
    prose mentioning COMPONENTS never matches."""
    lines = pack_text.splitlines()
    for i, ln in enumerate(lines):
        if ln.startswith("--- COMPONENTS fine (" + region_prefix):
            rows = []
            for ln2 in lines[i + 1:]:
                m = ROW_RE.match(ln2)
                if not m:
                    break
                rows.append({
                    "id": int(m.group(1)), "cls": m.group(2),
                    "cells": int(m.group(3)),
                    "bbox_frac": [float(v) for v in m.group(4).split(",")],
                    "centroid_frac": [float(v) for v in m.group(5).split(",")],
                    "rgb": ([int(v) for v in m.group(7).split(",")]
                            if m.group(7) else None),
                    "fill": float(m.group(9)) if m.group(9) else None,
                    "edge": m.group(10),
                })
            return rows
    raise AssertionError("no COMPONENTS table for %r in pack" % region_prefix)


class AVTest(unittest.TestCase):
    """Shared PIL-built fixtures (per-class temp dir, no committed files)."""

    @classmethod
    def setUpClass(cls):
        tmp = tempfile.TemporaryDirectory(prefix="ascii_vision_test_")
        cls.addClassCleanup(tmp.cleanup)

        def fx(name, size, draw_fn=None, mode="RGB", color=GRAY):
            return make_png(os.path.join(tmp.name, name), size,
                            draw_fn, mode, color)

        def draw_edge(d):
            d.rectangle([600, 150, 639, 210], fill=BLUE)   # cut by right edge
            d.rectangle([300, 150, 360, 210], fill=RED)    # fully interior
        cls.edge640 = fx("edge640.png", (640, 360), draw_edge)
        cls.blob640 = fx("blob640.png", (640, 360),
                         lambda d: d.rectangle([460, 70, 500, 110], fill=BLUE))
        cls.solid640 = fx("solid640.png", (640, 360),
                          lambda d: d.rectangle([260, 120, 359, 239], fill=BLUE))
        cls.speck640 = fx("speck640.png", (640, 360),
                          lambda d: d.point([(400, 200), (401, 200), (402, 200)],
                                            fill=BLUE))

        def draw_dark(d):  # dark MONOchrome halves: r1 requires dark_frac>0.08,
            d.rectangle([0, 0, 159, 179], fill=(25, 25, 28))   # mean<0.40,
            d.rectangle([160, 0, 319, 179], fill=(60, 60, 66))  # stdev<0.15, not r0
        cls.dark320 = fx("dark320.png", (320, 180), draw_dark)

        def draw_achrom(d):  # only achromatic classes -> no chromatic components
            d.rectangle([80, 60, 239, 119], fill=(60, 60, 60))
        cls.achrom320 = fx("achrom320.png", (320, 180), draw_achrom)
        cls.head320 = fx("head_check.png", (320, 180))
        cls.guard160 = fx("guard160.png", (160, 90))
        cls.one1 = fx("one1.png", (1, 1), color=BLUE)
        cls.rgba80 = fx("rgba80.png", (80, 60), mode="RGBA", color=BLUE + (255,))
        cls.pmode80 = fx("pmode80.png", (80, 60), mode="P", color=BLUE)


class TestDeterminism(AVTest):
    """D4 case 1: same image + same flags -> byte-identical pack."""

    def test_two_runs_byte_identical(self):
        opts = dict(cols=96, components=True, tiles=2)
        a = av.build_pack_from_path(self.blob640, **opts)
        b = av.build_pack_from_path(self.blob640, **opts)
        self.assertEqual(a.encode("utf-8"), b.encode("utf-8"),
                         "two identical runs must produce identical bytes")
        self.assertGreater(len(a), 2000, "pack should be non-trivial")


class TestClassifier(AVTest):
    """D4 case 2: hue-dominant classifier + saturation gate."""

    def setUp(self):
        self.meta = av._palette_meta(av.SCENE_PALETTE)

    def test_dim_saturated_red_is_R(self):
        got = av.classify_color((150, 60, 60), self.meta, 0.15)
        self.assertEqual(got, "R", "dim saturated red must be R, not %r "
                         "(khaki/gray)" % got)

    def test_palette_dim_red_ref_is_R(self):
        # the palette's own dim-render ref (145,87,87) must stay eligible
        self.assertEqual(av.classify_color((145, 87, 87), self.meta, 0.15), "R")

    def test_desaturated_gray_is_achromatic(self):
        got = av.classify_color((128, 128, 128), self.meta, 0.15)
        self.assertEqual(got, ".", "gray must fall to achromatic '.', not %r" % got)

    def test_sat_gate_blocks_chromatic(self):
        # s=0.6 pixel cannot match chromatic refs at sat_thresh 0.7
        self.assertEqual(av.classify_color((150, 60, 60), self.meta, 0.7), ".")


class TestComponentMerge(AVTest):
    """D4 case 3: same-class blobs whose bboxes are 1 cell apart (corner-
    kissing, as antialiasing splits produce) merge via merge_close(gap=1);
    a 5-empty-cell gap stays split. Tested on components() directly."""

    @staticmethod
    def grid(dots, w, h):
        g = [["."] * w for _ in range(h)]
        for x, y in dots:
            g[y][x] = "B"
        return g

    PIECE_A = [(0, 0), (1, 0), (1, 1), (2, 1), (3, 1)]       # bbox (0,0,3,1)
    PIECE_B = [(4, 3), (5, 3), (6, 3), (7, 3), (7, 2)]       # bbox (4,2,7,3)

    def test_one_cell_bbox_gap_merges(self):
        cells = self.grid(self.PIECE_A + self.PIECE_B, 9, 5)
        comps, dropped = av.components(cells, 9, 5, {"B"})
        self.assertEqual([len(comps), dropped], [1, 0],
                         "bbox-adjacent same-class pieces must merge")
        self.assertEqual(comps[0]["bbox_cells"], (0, 0, 7, 3))
        self.assertEqual(comps[0]["n_cells"], 10)

    def test_five_cell_gap_stays_split(self):
        shifted = [(x + 5, y) for x, y in self.PIECE_B]  # 5 empty cols: 4..8
        cells = self.grid(self.PIECE_A + shifted, 13, 5)
        comps, dropped = av.components(cells, 13, 5, {"B"})
        self.assertEqual(len(comps), 2, "5-cell gap must NOT merge")
        self.assertEqual(sorted(c["bbox_cells"] for c in comps),
                         [(0, 0, 3, 1), (9, 2, 12, 3)])


class TestTinySpeck(AVTest):
    """D4 case 4: 3px speck on 640x360 found by fine components."""

    def test_speck_found_at_fraction(self):
        pack = av.build_pack_from_path(self.speck640, cols=96, components=True)
        rows = parse_comp_rows(pack, "full frame")
        self.assertEqual(len(rows), 1, "expected exactly the speck, got %r" % rows)
        row = rows[0]
        self.assertEqual(row["cls"], "B")
        self.assertGreaterEqual(row["cells"], 2,
                                "3px speck must survive min_cells=2 at fine res")
        # true speck center: px x 400..402 y 200 -> (401.5/640, 200.5/360)
        # one fine cell = 1/384 in x, 1/108 in y (96x27 grid, fine_comp=4)
        truth = (401.5 / 640, 200.5 / 360)
        tol = (1 / 384 + 0.002, 1 / 108 + 0.002)  # +0.002: 3-decimal rounding
        for axis in (0, 1):
            self.assertLess(abs(row["centroid_frac"][axis] - truth[axis]),
                            tol[axis],
                            "speck centroid axis %d off by >1 fine cell: %r"
                            % (axis, row["centroid_frac"]))


class TestTileRemap(AVTest):
    """D4 case 5: overview and containing-tile tables agree on centroid_frac."""

    def test_overview_and_tile_agree(self):
        pack = av.build_pack_from_path(self.blob640, cols=96, components=True,
                                       tiles=2)
        ov = parse_comp_rows(pack, "full frame")
        tl = parse_comp_rows(pack, "tile[0,1]")  # blob at (0.75, 0.25) lives here
        self.assertEqual(len(ov), 1, "overview rows: %r" % ov)
        self.assertEqual(len(tl), 1, "tile[0,1] rows: %r" % tl)
        truth = (480.5 / 640, 90.5 / 360)
        for axis in (0, 1):
            self.assertLess(abs(ov[0]["centroid_frac"][axis]
                                - tl[0]["centroid_frac"][axis]), 0.02,
                            "overview vs tile centroid mismatch on axis %d" % axis)
            self.assertLess(abs(ov[0]["centroid_frac"][axis] - truth[axis]), 0.02,
                            "both tables wrong the same way (axis %d)" % axis)


class TestEdgeFlag(AVTest):
    """D4 case 6: frame-cut object flags its edge; interior object none."""

    def test_right_cut_vs_interior(self):
        pack = av.build_pack_from_path(self.edge640, cols=96, components=True)
        by_cls = {r["cls"]: r for r in parse_comp_rows(pack, "full frame")}
        self.assertIn("B", by_cls, "blue right-cut block missing")
        self.assertIn("R", by_cls, "red interior block missing")
        self.assertEqual(by_cls["B"]["edge"], "R",
                         "right-frame-cut block must report edge containing R")
        self.assertEqual(by_cls["R"]["edge"], "none",
                         "interior block must report edge=none")


class TestReadback(AVTest):
    """D4 case 7: rgb= readback of a solid component matches drawn color."""

    def test_solid_block_rgb_within_10(self):
        pack = av.build_pack_from_path(self.solid640, cols=96, components=True)
        rows = parse_comp_rows(pack, "full frame")
        self.assertEqual(len(rows), 1, "rows: %r" % rows)
        row = rows[0]
        self.assertIsNotNone(row["rgb"], "rgb readback missing (D2)")
        for got, want in zip(row["rgb"], BLUE):
            self.assertLessEqual(abs(got - want), 10,
                                 "readback rgb %r vs drawn %r" % (row["rgb"], BLUE))
        self.assertEqual(row["fill"], 1.0, "solid rectangle must have fill=1.0")


class TestAutoRules(AVTest):
    """D4 case 8: auto_select() rule engine, explicit precedence, e2e auto."""

    UNSET = {"gamma": None, "dither": None, "autocontrast": False}

    def select(self, stats, explicit=None):
        return av.auto_select(stats, explicit or self.UNSET)

    def test_dark_monochrome_fires_r1(self):
        stats = {"mean": 0.2, "stdev": 0.08, "dark_frac": 0.3,
                 "edge_frac": 0.01, "huebins": 1}
        changes, fired, warns = self.select(stats)
        self.assertEqual(changes, {"gamma": 1.8, "autocontrast": True})
        self.assertEqual(fired, ["r1"])
        self.assertEqual(warns, [])

    def test_near_empty_fires_r0_only(self):
        # stdev also low (S7-style) so r3 cannot co-fire
        stats = {"mean": 0.04, "stdev": 0.02, "dark_frac": 0.6,
                 "edge_frac": 0.0, "huebins": 0}
        changes, fired, warns = self.select(stats)
        self.assertEqual((changes, fired, warns), ({}, ["r0"], []))

    def test_gradient_fires_r3_dither(self):
        stats = {"mean": 0.5, "stdev": 0.23, "dark_frac": 0.0,
                 "edge_frac": 0.04, "huebins": 2}
        changes, fired, warns = self.select(stats)
        self.assertEqual(changes, {"dither": "fs"})
        self.assertEqual(fired, ["r3"])

    def test_hue_rich_warns_r2(self):
        stats = {"mean": 0.45, "stdev": 0.05, "dark_frac": 0.1,
                 "edge_frac": 0.02, "huebins": 5}
        changes, fired, warns = self.select(stats)
        self.assertEqual(changes, {})
        self.assertEqual(fired, ["r2"])
        self.assertEqual(len(warns), 1)
        self.assertIn("web16", warns[0])

    def test_normal_scene_fires_nothing(self):
        stats = {"mean": 0.45, "stdev": 0.04, "dark_frac": 0.0,
                 "edge_frac": 0.01, "huebins": 3}
        self.assertEqual(self.select(stats), ({}, [], []))

    def test_explicit_gamma_blocks_r1_change(self):
        stats = {"mean": 0.2, "stdev": 0.08, "dark_frac": 0.3,
                 "edge_frac": 0.01, "huebins": 1}
        changes, fired, _ = self.select(stats, {"gamma": 1.0, "dither": None,
                                                "autocontrast": False})
        self.assertNotIn("gamma", changes, "auto must not override explicit gamma")
        self.assertEqual(changes, {"autocontrast": True})
        self.assertIn("r1", fired)

    def test_explicit_dither_blocks_r3_change(self):
        stats = {"mean": 0.5, "stdev": 0.23, "dark_frac": 0.0,
                 "edge_frac": 0.04, "huebins": 2}
        changes, fired, _ = self.select(stats, {"gamma": None, "dither": "none",
                                                "autocontrast": False})
        self.assertNotIn("dither", changes)
        self.assertIn("r3", fired)

    def test_end_to_end_auto_on_dark_fixture(self):
        pack = av.build_pack_from_path(self.dark320, auto=True)
        params = next(ln for ln in pack.splitlines() if ln.startswith("params:"))
        self.assertIn("auto=r1", params, "rule must be auditable in params line")
        self.assertIn("gamma=1.80 autocontrast=True", params)


class TestGuardRails(AVTest):
    """D4 case 9: cols > max_cols refused without force, allowed with it."""

    def test_oversize_cols_raises_without_force(self):
        with self.assertRaises(ValueError) as cm:
            av.build_pack_from_path(self.guard160, cols=200)
        self.assertIn("force", str(cm.exception),
                      "error must tell the user about force")

    def test_force_allows_oversize_cols(self):
        text = av.build_pack_from_path(self.guard160, cols=200, force=True)
        self.assertGreater(len(text), 500)
        self.assertIn("cols=200 ", text)


class TestIOOptions(AVTest):
    """D4 case 10: header/mode/empty-table output contract."""

    def test_no_header_omits_filename(self):
        full = av.build_pack_from_path(self.head320)
        self.assertTrue(full.splitlines()[0].startswith("== ASCII-VISION PACK: "))
        nh = av.build_pack_from_path(self.head320, no_header=True)
        self.assertEqual(nh.splitlines()[0], "== ASCII-VISION PACK ==")
        self.assertNotIn("head_check.png", nh,
                         "no_header packs must not leak the filename")

    def test_luma_mode_omits_color_panel(self):
        text = av.build_pack_from_path(self.head320, mode="luma")
        self.assertNotIn("PANEL color-class", text)
        self.assertIn("PANEL luma", text)

    def test_achromatic_image_prints_no_components_note(self):
        pack = av.build_pack_from_path(self.achrom320, components=True)
        self.assertIn("(no chromatic components", pack,
                      "empty table must print the explicit note")


class TestRobustInputs(AVTest):
    """D4 case 11: 1x1 and non-RGB inputs must not crash, non-empty packs."""

    def assert_healthy_pack(self, path, name):
        text = av.build_pack_from_path(path, components=True)
        self.assertGreater(len(text), 500, "%s input: pack too small" % name)
        self.assertIn("class_share: B 100.0%", text,
                      "%s input lost its solid blue through mode conversion" % name)

    def test_1x1_image(self):
        self.assert_healthy_pack(self.one1, "1x1")

    def test_rgba_image(self):
        self.assert_healthy_pack(self.rgba80, "RGBA")

    def test_p_mode_image(self):
        self.assert_healthy_pack(self.pmode80, "P-mode")


def _full_frame_rows(pack):
    """(cls, bbox_frac, edge) tuples from the overview components table
    (thin wrapper over the suite's parse_comp_rows)."""
    rows = parse_comp_rows(pack, "full frame")
    return [(r["cls"], r["bbox_frac"], r["edge"]) for r in rows]


class TestCropRemap(AVTest):
    """U1-A friction 3 regression: --crop component tables must print
    FULL-FRAME fractions (matching the overview rows), not crop-local ones,
    and edge flags must be judged against the FULL frame (interior crops
    must not fire edge flags at their own borders)."""

    def test_crop_fractions_match_overview(self):
        full = _full_frame_rows(av.build_pack_from_path(self.solid640, components=True))
        self.assertTrue(full, "overview components missing")
        croppack = av.build_pack_from_path(
            self.solid640, components=True, crop="0.3,0.3,0.7,0.7")
        crop = [(r["cls"], r["bbox_frac"], r["edge"])
                for r in parse_comp_rows(croppack, "crop=")]
        self.assertTrue(crop, "crop components missing")
        # the blob is the same object: bboxes agree within fine-cell tolerance
        for fb, cb in zip(sorted(r[1] for r in full),
                          sorted(r[1] for r in crop)):
            for a, b in zip(fb, cb):
                self.assertAlmostEqual(a, b, delta=0.01,
                                       msg="crop frac %s vs full %s" % (cb, fb))

    def test_crop_interior_edge_is_none(self):
        croppack = av.build_pack_from_path(
            self.solid640, components=True, crop="0.3,0.3,0.7,0.7")
        rows = [(r["cls"], r["bbox_frac"], r["edge"])
                for r in parse_comp_rows(croppack, "crop=")]
        self.assertTrue(rows, "crop components missing")
        self.assertTrue(all(r[2] == "none" for r in rows),
                        "interior crop must not claim frame contact: %s" % rows)

    def test_crop_plus_tiles_interaction(self):
        """Audit-A: tiles of a CROPPED frame — the exact combo that regressed
        in U1. A tile row must equal the overview bbox CLIPPED to the tile's
        crop box (full-frame coords, no double transform)."""
        base = av.build_pack_from_path(self.solid640, components=True)
        over = {r["cls"]: r["bbox_frac"] for r in parse_comp_rows(base, "full frame")}
        combo = av.build_pack_from_path(self.solid640, components=True,
                                        crop="0.3,0.3,0.7,0.7", tiles=2)
        lines = combo.splitlines()
        checked = 0
        for i, ln in enumerate(lines):
            if not ln.startswith("--- COMPONENTS fine (tile["):
                continue
            crop_box = [float(v) for v in
                        re.search(r"crop=([\d.]+),([\d.]+),([\d.]+),([\d.]+)", ln).groups()]
            for r in parse_comp_rows(combo, "tile[%s" % ln.split("(tile[")[1][:3]):
                if r["cls"] not in over:
                    continue
                ov = over[r["cls"]]
                expect = [max(ov[0], crop_box[0]), max(ov[1], crop_box[1]),
                          min(ov[2], crop_box[2]), min(ov[3], crop_box[3])]
                for a, b in zip(expect, r["bbox_frac"]):
                    self.assertAlmostEqual(a, b, delta=0.02,
                                           msg="tile row %s vs clipped overview %s"
                                               % (r["bbox_frac"], expect))
                checked += 1
        self.assertGreater(checked, 0, "no tile row matched an overview object")


class TestOutParity(AVTest):
    """D4 case 10 (audit gap c): --out file content == stdout bytes."""

    def test_out_file_matches_stdout(self):
        out_path = os.path.join(tempfile.mkdtemp(prefix="av_out_"), "p.txt")
        cli = os.path.join(HERE, "ascii_vision.py")
        img = self.blob640
        r = subprocess.run(
            [sys.executable, cli, img, "--cols", "48", "--components",
             "--minimal", "--out", out_path],
            capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(out_path) as f:
            self.assertEqual(f.read(), r.stdout, "--out file != stdout bytes")


class TestAutoPerturbation(AVTest):
    """R5_SPEC D1 perturbation checks (fixture-based, self-contained):
    +-20% brightness and 2x downscale must not flip fired rules."""

    def _rules(self, img):
        pack = av.build_pack_from_path(img, auto=True, minimal=True)
        m = re.search(r"auto=([a-z0-9+]*)", pack)
        return m.group(1)

    def test_dark_image_perturbations_keep_r1(self):
        base = self._rules(self.dark320)
        self.assertEqual(base, "r1", "dark320 baseline must fire r1")
        im = Image.open(self.dark320)
        # +20% brightness
        bright = im.point([min(255, int(v * 1.2)) for v in range(256)] * 3)
        p1 = os.path.join(tempfile.gettempdir(), "avtest_dark_bright.png")
        bright.save(p1)
        self.assertIn("r1", self._rules(p1), "+20% brightness flipped r1")
        # -20% brightness
        dark = im.point([int(v * 0.8) for v in range(256)] * 3)
        p2 = os.path.join(tempfile.gettempdir(), "avtest_dark_dim.png")
        dark.save(p2)
        self.assertIn("r1", self._rules(p2), "-20% brightness flipped r1")
        # 2x downscale
        p3 = os.path.join(tempfile.gettempdir(), "avtest_dark_half.png")
        im.resize((160, 90), Image.BOX).save(p3)
        self.assertIn("r1", self._rules(p3), "2x downscale flipped r1")

    def test_normal_scene_stays_quiet(self):
        base = self._rules(self.blob640)
        self.assertNotIn("r1", base, "blob640 must not fire r1: %s" % base)
        self.assertNotIn("r3", base, "blob640 must not fire r3: %s" % base)
        im = Image.open(self.blob640)
        p = os.path.join(tempfile.gettempdir(), "avtest_blob_bright.png")
        im.point([min(255, int(v * 1.2)) for v in range(256)] * 3).save(p)
        self.assertEqual(self._rules(p), base,
                         "+20%% brightness flipped fired rules: %s -> %s"
                         % (base, self._rules(p)))


class TestMinimalFlag(AVTest):
    """U1-A friction 6: --minimal == no header + no guide + no legend."""

    def test_minimal_strips_head_and_tail(self):
        text = av.build_pack_from_path(self.head320, components=True,
                                       minimal=True)
        self.assertNotIn("HOW TO READ THIS PACK", text)
        self.assertNotIn("head_check.png", text)
        self.assertNotIn("--- LEGEND ---", text)
        self.assertIn("params: cols=96", text)
        # CLI spell routes through the same opt
        tmpd = tempfile.mkdtemp(prefix="av_min_")
        p = make_png(os.path.join(tmpd, "min_cli.png"), (160, 90),
                     lambda d: d.rectangle([0, 0, 159, 89], fill=BLUE))
        cli = os.path.join(HERE, "ascii_vision.py")
        out = subprocess.run(
            [sys.executable, cli, p, "--minimal", "--components"],
            capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertNotIn("HOW TO READ", out.stdout)
        self.assertIn("COMPONENTS fine", out.stdout)


class TestPackParser(AVTest):
    """Optional: pack_accuracy.parse_pack reads the D2 readback suffix, and
    pre-R5 suffix-less rows still parse (groups stay None)."""

    SYNTH = (
        "== ASCII-VISION PACK ==\n"
        "--- COMPONENTS fine (full frame, internal 384x, sat>=0.08; fracs are "
        "FULL-FRAME): id cls cells bbox_frac[x0,y0,x1,y1] centroid_frac "
        "height_frac rgb lum fill edge ---\n"
        " 1 B   24 [0.5,0.4,0.6,0.5] (0.55,0.45) 0.1 "
        "rgb=61,109,181 lum=0.45 fill=0.85 edge=none\n"
        " 2 R   10 [0.1,0.1,0.2,0.2] (0.15,0.15) 0.1\n"
    )

    def test_parse_pack_reads_new_and_old_rows(self):
        res = pack_accuracy.parse_pack(self.SYNTH)
        self.assertEqual(len(res["comps"]), 2, "both rows must parse")
        c1, c2 = res["comps"]
        self.assertEqual(c1["rgb"], [61, 109, 181])
        self.assertEqual(c1["lum"], 0.45)
        self.assertEqual(c1["fill"], 0.85)
        self.assertEqual(c1["edge"], "none")
        self.assertIsNone(c2["rgb"], "suffix-less row must yield None fields")
        self.assertIsNone(c2["edge"])
        self.assertEqual(res["sat_floor"], 0.08)


if __name__ == "__main__":
    unittest.main(verbosity=2)
