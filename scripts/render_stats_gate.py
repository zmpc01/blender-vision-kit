#!/usr/bin/env python3
"""render_stats_gate.py -- post-render BLOCKED-FRAME gate (flatness).

The last-line catcher that would have flagged v3.3's S4b (79% of the
shot behind a tire wall), S5b f303 (camera inside a zombie) and S8
f495 (93% single color) no matter what the geometry-level checks
missed. Runs on the RENDERED frames (png sequence or video), so it
sees exactly what the viewer sees.

Rule (calibrated by r4-review-b on the full v3.3 1080-frame corpus:
0 false positives, catches 22/23 blocked frames, spares the legit
closeups and the declared fade):

    BLOCK if  dom >= 0.80                      (WARN band 0.70-0.79)
         OR  (edge <= 1.2 AND dom <= 0.60)     (flat wall, low coverage)
         OR  tdiff <= 1.0 for >= 3 consecutive frames (frozen wall)

Deliberate fades are DECLARED in the scene module's FLATNESS_POLICY
(shot -> (f0, f1)); inside a declared range, dom>=0.80 downgrades to
WARN plus a gradual-onset check (|dom| slope <= 0.05/frame). Anything
undeclared stays fail-closed.

Usage:
    blender-agnostic (pure python):
    python3 render_stats_gate.py --dir frames/ --policy scene_escape_v3_3
    python3 render_stats_gate.py --video anim.mp4 --policy scene_escape_v3_3
Exit 1 on any BLOCK.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

import numpy as np
from PIL import Image

DOM_BLOCK, DOM_WARN = 0.80, 0.70
EDGE_BLOCK, EDGE_DOM_CAP = 1.2, 0.60
FROZEN_TDIFF, FROZEN_RUN = 1.0, 3


def load_policy(module_name):
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        mod = __import__(module_name)
        return getattr(mod, "FLATNESS_POLICY", {})
    except Exception:
        return {}


def iter_frames_dir(d):
    for f in sorted(os.listdir(d)):
        if f.lower().endswith((".png", ".jpg", ".jpeg")):
            yield int(re.sub(r"\D", "", f.split(".")[0]) or 0), \
                os.path.join(d, f)


def iter_frames_video(v):
    tmp = "/tmp/_rsg_%d" % os.getpid()
    os.makedirs(tmp, exist_ok=True)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-i", v,
                    "-vf", "scale=192:108", "-q:v", "4",
                    os.path.join(tmp, "%05d.jpg"), "-y"], check=True)
    for f in sorted(os.listdir(tmp)):
        if f.endswith(".jpg"):
            yield int(f.split(".")[0]), os.path.join(tmp, f)


def frame_stats(path):
    a = np.asarray(Image.open(path).convert("RGB"))
    g = a.mean(axis=2)
    edge = (np.abs(np.diff(g, axis=1)).sum()
            + np.abs(np.diff(g, axis=0)).sum()) / g.size
    q = (a // 16).astype(np.int64)
    key = q[..., 0] * 256 + q[..., 1] * 16 + q[..., 2]
    vals, counts = np.unique(key, return_counts=True)
    dom = counts.max() / key.size
    return float(dom), float(edge), float(g.mean())


def in_declared(f, policy):
    for sid, (a, b) in policy.items():
        if a <= f <= b:
            return sid
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir")
    ap.add_argument("--video")
    ap.add_argument("--policy", default="scene_escape_v3_3")
    ap.add_argument("--json", default="")
    args = ap.parse_args()
    if not (args.dir or args.video):
        ap.error("need --dir or --video")
    policy = load_policy(args.policy)
    src = iter_frames_dir(args.dir) if args.dir else \
        iter_frames_video(args.video)

    frames = []
    prev_arr = None
    for f, path in src:
        dom, edge, mean = frame_stats(path)
        arr = np.asarray(Image.open(path).convert("L"),
                         dtype=np.int16)
        tdiff = float(np.abs(arr - prev_arr).mean()) \
            if prev_arr is not None and arr.shape == prev_arr.shape else None
        prev_arr = arr
        frames.append({"f": f, "dom": dom, "edge": edge,
                       "mean": mean, "tdiff": tdiff})
    frames.sort(key=lambda r: r["f"])

    blocks, warns = [], []
    frozen_run, frozen_start = 0, None
    for r in frames:
        f, dom, edge = r["f"], r["dom"], r["edge"]
        sid = in_declared(f, policy)
        why = None
        if dom >= DOM_BLOCK:
            why = "dominant-color %.2f" % dom
        elif edge <= EDGE_BLOCK and dom <= EDGE_DOM_CAP:
            why = "flat wall (edge %.2f, dom %.2f)" % (edge, dom)
        if why and sid:
            slope = dom - (frames[frames.index(r) - 1]["dom"]
                           if frames.index(r) > 0 else dom)
            if abs(slope) > 0.05:
                blocks.append((f, f"{why} in DECLARED fade {sid} but "
                               f"onset is abrupt (slope {slope:+.2f}/f)"))
            else:
                warns.append((f, f"{why} inside declared fade {sid}"))
        elif why:
            blocks.append((f, why))
        elif dom >= DOM_WARN:
            warns.append((f, "dominant-color %.2f (warn band)" % dom))
        # frozen-wall detector (true pixel diff between consecutive frames)
        if r.get("tdiff") is not None and r["tdiff"] <= FROZEN_TDIFF:
            if frozen_start is None:
                frozen_start = f
            frozen_run += 1
        else:
            if frozen_run >= FROZEN_RUN and \
                    not in_declared(frozen_start, policy):
                blocks.append((frozen_start,
                               f"frozen wall: |dbright| <= "
                               f"{FROZEN_TDIFF} for {frozen_run} frames"))
            frozen_run, frozen_start = 0, None
    if frozen_run >= FROZEN_RUN and not in_declared(frozen_start, policy):
        blocks.append((frozen_start, "frozen wall at tail"))

    print(f"render_stats_gate: {len(frames)} frames, "
          f"{len(blocks)} BLOCK, {len(warns)} WARN")
    for f, w in blocks:
        print(f"  BLOCK f{f}: {w}")
    for f, w in warns[:10]:
        print(f"  warn  f{f}: {w}")
    if args.json:
        json.dump({"frames": frames, "blocks": blocks, "warns": warns},
                  open(args.json, "w"), indent=1)
    sys.exit(1 if blocks else 0)


if __name__ == "__main__":
    main()
