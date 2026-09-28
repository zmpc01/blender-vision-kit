"""
ground_truth_export.py -- camera-projection ground truth for Blender corpus
stills (ASCII-vision experiment, experiments/ascii_vision/SPEC.md).

Owned by Task 2-b. Design decision (documented per task brief): the truth
logic lives HERE as an importable module; scripts/scene_corpus.py imports it
and calls export_still_truth() inside the SAME Blender session, immediately
after rendering each still. This file can also run standalone to rebuild the
corpus layout and re-export truth WITHOUT rendering:

    ./run.sh --background --python scripts/ground_truth_export.py -- \\
        --output experiments/ascii_vision/corpus/blender --still all --truth-only

Method (SPEC "Blender corpus" + task 2-b brief), per tracked object group and
the still's active camera:
  - collect world-space bound_box corners of every mesh part (union over parts
    of the group; groups = actors [capsule body + head], jeep, rifle, zombies)
  - keep corners IN FRONT of the camera (camera-local z < 0; camera looks -Z)
  - project each kept corner via bpy_extras.object_utils.world_to_camera_view
  - bbox_frac      = min/max over projected corners, clamped to [0,1]
                     (fractions of frame, TOP-LEFT origin -- wtcv is bottom-left,
                     so y is flipped: truth_y = 1 - wtcv_y)
  - bbox_frac_raw  = same without clamping (shows out-of-frame spill)
  - centroid_frac  = projection of the mean of the in-front world corners,
                     clamped (perspective-true anchor, not bbox midpoint)
  - height_frac    = y1-y0 of the CLAMPED bbox (visible extent; matches the
                     synthetic-corpus convention and T5 height buckets)
  - visible        = any corner inside the frame AND in front of the camera
  - fully_in_frame = no corner behind the camera AND raw bbox inside [0,1]^2
  - touch_edge     = which frame edges the clamped bbox touches (eps 0.002)
  - floating / intersects flags are supplied by construction annotations from
    scene_corpus.py (planted bugs are KNOWN by construction, per brief)
  - counts         = tallied by color class over VISIBLE objects only
Ground plane + road strip are treated as scene background (excluded from
truth objects, like the synthetic corpus background).
"""
from __future__ import annotations

import argparse
import json
import math
import os

import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

from blender_kit import script_argv

EPS_EDGE = 0.002   # ~1.3 px at 640 width -- clamped-bbox edge-touch tolerance
PROJECTION_NOTE = (
    "bpy_extras.object_utils.world_to_camera_view on world-space bound_box "
    "corners (union over group parts), in-front guard camera-local z<0, "
    "y flipped to top-left origin; height_frac on clamped bbox; "
    "centroid = projection of mean of in-front corners (clamped)"
)


def _srgb_channel(c: float) -> float:
    """Linear -> sRGB (the display space the ASCII generator works in)."""
    return c * 12.92 if c <= 0.0031308 else 1.055 * (max(c, 1e-8) ** (1 / 2.4)) - 0.055


def project_group(scene, camera, parts) -> dict:
    """Project one tracked object group's world bbox into camera frame.

    Returns the projection fields shared by every truth entry (no
    annotations). All fractional coords are top-left origin.
    """
    cam_inv = camera.matrix_world.inverted()
    world_pts = []
    for part in parts:
        for corner in part.bound_box:
            world_pts.append(part.matrix_world @ Vector(corner))

    front, n_behind = [], 0
    for w in world_pts:
        if (cam_inv @ w).z < 0.0:      # camera looks along local -Z
            front.append(w)
        else:
            n_behind += 1

    if not front:
        return {
            "bbox_frac": [0.0, 0.0, 0.0, 0.0], "bbox_frac_raw": [0.0, 0.0, 0.0, 0.0],
            "centroid_frac": [0.5, 0.5], "height_frac": 0.0,
            "fully_in_frame": False, "visible": False, "touch_edge": None,
            "n_corners_total": len(world_pts), "n_corners_behind": n_behind,
        }

    xs, ys = [], []
    for w in front:
        co = world_to_camera_view(scene, camera, w)   # x,y in [0,1] in frame, y UP
        xs.append(co.x)
        ys.append(co.y)

    # flip y: wtcv origin is bottom-left, truth schema origin is top-left
    raw = [min(xs), 1.0 - max(ys), max(xs), 1.0 - min(ys)]
    clamp = lambda v: min(1.0, max(0.0, v))  # noqa: E731
    bbox = [clamp(raw[0]), clamp(raw[1]), clamp(raw[2]), clamp(raw[3])]

    center = Vector((0.0, 0.0, 0.0))
    for w in front:
        center += w
    center /= len(front)
    co = world_to_camera_view(scene, camera, center)
    centroid = [clamp(co.x), clamp(1.0 - co.y)]

    visible = any(0.0 <= x <= 1.0 and 0.0 <= y <= 1.0 for x, y in zip(xs, ys))
    fully_in_frame = (n_behind == 0 and all(-1e-9 <= v <= 1.0 + 1e-9 for v in raw))

    edges = []
    if bbox[0] <= EPS_EDGE:
        edges.append("left")
    if bbox[1] <= EPS_EDGE:
        edges.append("top")
    if bbox[2] >= 1.0 - EPS_EDGE:
        edges.append("right")
    if bbox[3] >= 1.0 - EPS_EDGE:
        edges.append("bottom")
    touch = "+".join(edges) if edges else None

    return {
        "bbox_frac": [round(v, 5) for v in bbox],
        "bbox_frac_raw": [round(v, 5) for v in raw],
        "centroid_frac": [round(v, 5) for v in centroid],
        "height_frac": round(bbox[3] - bbox[1], 5),
        "fully_in_frame": fully_in_frame,
        "visible": visible,
        "touch_edge": touch,
        "n_corners_total": len(world_pts),
        "n_corners_behind": n_behind,
    }


def image_stats(png_path: str, bg_linear) -> dict:
    """Mean luma / stdev / non-bg coverage of a rendered PNG, in sRGB space.

    Blender stores image pixels LINEARLY, so values are converted back to
    sRGB (display) space to match what the ASCII generator will read.
    coverage_nonbg = fraction of pixels whose any-channel sRGB distance from
    the flat world-background color exceeds 0.08.
    """
    try:
        import numpy as np
    except ImportError:
        return {"skipped": "numpy unavailable in Blender python"}
    img = bpy.data.images.load(png_path, check_existing=False)
    try:
        w, h = img.size
        buf = np.empty(w * h * img.channels, dtype=np.float32)
        img.pixels.foreach_get(buf)
        px = buf.reshape(-1, img.channels)[:, :3]
        srgb = np.where(px <= 0.0031308, px * 12.92,
                        1.055 * np.power(np.clip(px, 1e-8, None), 1 / 2.4) - 0.055)
        luma = srgb @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
        bg = np.array([_srgb_channel(c) for c in bg_linear], dtype=np.float32)
        dev = np.abs(srgb - bg).max(axis=1)
        return {
            "mean_luma": round(float(luma.mean()), 4),
            "stdev_luma": round(float(luma.std()), 4),
            "coverage_nonbg": round(float((dev > 0.08).mean()), 4),
            "definition": ("luma in sRGB display space (pixels are linear, "
                           "converted); coverage_nonbg = any-channel |px-bg|>0.08 "
                           "vs flat world color"),
        }
    finally:
        bpy.data.images.remove(img)


def export_still_truth(*, scene, camera, tracked, visible_ids, png_path,
                       out_path, w, h, material_mode, bg_linear,
                       annotations=None, still_notes="", extra_meta=None) -> dict:
    """Build + write <still>.truth.json for one still. Returns the dict.

    tracked: OrderedDict id -> {"parts": [objs], "class": str,
                                "count_group": str, "note": opt str}
    visible_ids: ids rendered in this still (hide_render was False).
    annotations: id -> {"floating": bool, "intersects": [ids], "note": str}
    """
    annotations = annotations or {}
    stem = os.path.basename(out_path).removesuffix(".truth.json")
    objects, counts = [], {}
    for oid, entry in tracked.items():
        if oid not in visible_ids:
            continue
        proj = project_group(scene, camera, entry["parts"])
        obj_entry = {
            "id": oid,
            "class": entry["class"],
            "count_group": entry["count_group"],
            **proj,
            "floating": False,
            "intersects": [],
            "parts": [p.name for p in entry["parts"]],
        }
        note = entry.get("note", "")
        ann = annotations.get(oid, {})
        if "floating" in ann:
            obj_entry["floating"] = bool(ann["floating"])
        if "intersects" in ann:
            obj_entry["intersects"] = list(ann["intersects"])
        bits = [b for b in (note, ann.get("note")) if b]
        if bits:
            obj_entry["note"] = "; ".join(bits)
        objects.append(obj_entry)
        if proj["visible"]:  # counts tallied over visible objects only
            counts[entry["class"]] = counts.get(entry["class"], 0) + 1

    truth = {
        "image": (os.path.basename(png_path) if png_path else f"{stem}.png"),
        "camera": camera.name,
        "engine": "BLENDER_WORKBENCH",
        "material_mode": material_mode,
        "resolution": [w, h],
        "projection": PROJECTION_NOTE,
        "objects": objects,
        "counts": counts,
        "image_stats": (image_stats(png_path, bg_linear)
                        if png_path and os.path.isfile(png_path)
                        else {"skipped": "render not available"}),
        "notes": still_notes,
    }
    if extra_meta:
        truth["meta"] = extra_meta
    with open(out_path, "w") as f:
        json.dump(truth, f, indent=2)
    n_vis = sum(1 for o in objects if o["visible"])
    print(f"[truth] {os.path.basename(out_path)}: {len(objects)} tracked "
          f"({n_vis} visible), counts={counts}")
    return truth


def main() -> None:
    """Standalone entry: rebuild the corpus layout, re-export truth, no render."""
    p = argparse.ArgumentParser(
        description="Rebuild scene_corpus layout and re-export truth JSONs "
                    "(no rendering; add --truth-only explicitly for clarity)")
    p.add_argument("--output", required=True)
    p.add_argument("--still", default="all", help="C1|C2|...|all or comma list")
    p.add_argument("--w", type=int, default=640)
    p.add_argument("--h", type=int, default=360)
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--truth-only", action="store_true",
                   help="rebuild + export truth only (no renders)")
    args = p.parse_args(script_argv())
    import scene_corpus  # lazy: avoids import cycle at module load
    # Standalone mode NEVER renders (truth re-export only); --truth-only is
    # accepted for explicitness. Scene build must be deterministic (seeded).
    scene_corpus.run(args, render=False)


if __name__ == "__main__":
    main()
