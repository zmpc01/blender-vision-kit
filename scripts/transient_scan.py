"""
transient_scan.py — spot-check for frame-transient issues (vision-kit M5 P4).

THE PROBLEM (user directive): some issues only occur on certain frames —
NOT necessarily at keyframes. Physics pops, sim instabilities, pose
breaks, rig glitches between keys. A keyframe contact sheet can miss them
entirely (measured: a planted 3-frame glitch bracketing f15-17 was caught
by sampled strips only by LUCK at f17).

THE METHOD: render EVERY frame in the range at previz resolution (cheap:
Workbench 480x270 ~ 0.3s/frame incl. the already-paid cold start), diff
consecutive frames pixel-wise, and RANK frames by change magnitude.
Adjacent high-diff frames cluster into EVENTS. Output:

  1. EVENT-TABLE: ranked change events (frame ranges, mean/peak diff)
     printed as text — the attention device
  2. suspects strip: grid of the top event PEAK frames for eyeball triage
  3. doctrine line: the scanner RANKS, the eyes VERDICT — confirm suspects
     at full res with look.py --frame N [--closeup <id>]

Camera is FIXED (persp orbit of scene bounds) so every pixel change is
scene change, not camera swing. No annotations (constant overlays would
pollute the diff; the scan is a change radar, not a read).

Usage (via blrun.sh --background --python scripts/transient_scan.py -- ...):
  --scene mod_name | --load-blend file.blend
  --start N --end N   frame range (default: scene range)
  --top K             events to report (default 6)
  --out DIR           output dir (default output/<scene>/scan)
  --res WxH           scan resolution (default 480x270)
  --peak-res WxH      suspect strip cell resolution (default 640x480)

Exit codes: 0 = no significant events; 0 with SUSPECTS listed otherwise
(verdict belongs to the eyes, not the scanner — a scan never fails a
scene, it aims the look).
"""
import os
import sys

import bpy
import numpy as np


def _parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--scene", default=None)
    p.add_argument("--load-blend", default=None)
    p.add_argument("--start", type=int, default=None)
    p.add_argument("--end", type=int, default=None)
    p.add_argument("--top", type=int, default=6)
    p.add_argument("--out", default=None)
    p.add_argument("--res", default="480x270")
    p.add_argument("--peak-res", default="640x480")
    p.add_argument("--engine", default="workbench")
    return p.parse_args(argv)


def _load(args):
    if args.load_blend:
        bpy.ops.wm.open_mainfile(filepath=args.load_blend)
    elif args.scene:
        from blender_kit import safe_import_scene, clear_scene
        mod = safe_import_scene(args.scene)
        clear_scene()
        ctx = mod.build_scene()
        if hasattr(mod, "animate"):
            mod.animate(ctx, start_frame=1, n_frames=64)
    else:
        print("[scan] ERROR: need --scene or --load-blend")
        sys.exit(1)


def _render_range(start, end, outdir, w, h, engine):
    """Render every frame; return list of (frame, path). Fixed persp camera
    orbiting the scene bounds (same math as render_angle('persp'))."""
    import viewport_capture as vc
    scene = bpy.context.scene
    meshes = [o for o in scene.objects if o.type == 'MESH']
    if meshes:
        pts = [o.matrix_world @ type(o.location)(c) for o in meshes
               for c in o.bound_box]
        cx = sum(p.x for p in pts) / len(pts)
        cy = sum(p.y for p in pts) / len(pts)
        cz = sum(p.z for p in pts) / len(pts)
    else:
        cx = cy = cz = 0.0
    out = []
    for f in range(start, end + 1):
        scene.frame_set(f)
        scene.view_layer.update()
        p = os.path.join(outdir, f"f{f:04d}.png")
        vc.render_angle("persp", p, engine=engine, width=w, height=h,
                        target=(cx, cy, cz))
        out.append((f, p))
    return out


def _diff_series(rendered):
    """Consecutive-frame mean pixel diff. Returns [(frame, mean, peak)]."""
    import PIL.Image as Image
    series = []
    prev = None
    for f, path in rendered:
        arr = np.asarray(Image.open(path).convert("RGB"), dtype=np.float32) / 255.0
        if prev is not None:
            d = np.abs(arr - prev)
            series.append((f, float(d.mean()), float(d.max())))
        prev = arr
    return series


def _events(series, top_k):
    """Cluster consecutive frames into events; rank by peak diff.
    An event = maximal run of frames with mean diff above the adaptive
    floor (median + 2*MAD, MAD-robust so quiet scenes still surface)."""
    if not series:
        return []
    means = sorted(s[1] for s in series)
    med = means[len(means) // 2]
    mad = sorted(abs(m - med) for m in means)[len(means) // 2]
    floor = med + 2.0 * max(mad, 1e-4)
    hot = [s for s in series if s[1] >= floor]
    if not hot:
        return []
    # cluster consecutive frames (gap <= 1 frame joins an event)
    clusters = []
    cur = [hot[0]]
    for s in hot[1:]:
        if s[0] - cur[-1][0] <= 2:
            cur.append(s)
        else:
            clusters.append(cur)
            cur = [s]
    clusters.append(cur)
    evs = []
    for c in clusters:
        frames = [s[0] for s in c]
        peak = max(c, key=lambda s: s[2])
        evs.append({
            "start": frames[0], "end": frames[-1],
            "mean": sum(s[1] for s in c) / len(c),
            "peak_frame": peak[0], "peak_diff": peak[2],
        })
    evs.sort(key=lambda e: -e["peak_diff"])
    return evs[:top_k]


def _suspect_strip(evs, outdir, w, h, engine):
    """Re-render each event's peak frame at read resolution (fixed camera
    parity with the scan — same target math)."""
    import viewport_capture as vc
    scene = bpy.context.scene
    meshes = [o for o in scene.objects if o.type == 'MESH']
    pts = [o.matrix_world @ type(o.location)(c) for o in meshes
           for c in o.bound_box] if meshes else []
    cx = sum(p.x for p in pts) / len(pts) if pts else 0
    cy = sum(p.y for p in pts) / len(pts) if pts else 0
    cz = sum(p.z for p in pts) / len(pts) if pts else 0
    import tempfile
    cells = []
    with tempfile.TemporaryDirectory() as td:
        for i, e in enumerate(evs):
            scene.frame_set(e["peak_frame"])
            scene.view_layer.update()
            p = os.path.join(td, f"peak{i}.png")
            vc.render_angle("persp", p, engine=engine, width=w, height=h,
                            target=(cx, cy, cz))
            cells.append(p)
        strip = os.path.join(outdir, "suspects.png")
        vc.stitch_contact_sheet(cells, strip, grid_cols=min(len(cells), 3))
    return strip


def main():
    args = _parse_args()
    _load(args)
    scene = bpy.context.scene
    start = args.start if args.start is not None else scene.frame_start
    end = args.end if args.end is not None else scene.frame_end
    if end - start < 1:
        print(f"[scan] ERROR: frame range {start}..{end} too short to scan")
        sys.exit(1)

    outdir = args.out or os.path.join(
        "output", args.scene or os.path.basename(args.load_blend or "scan"),
        "scan")
    os.makedirs(outdir, exist_ok=True)
    w, h = (int(x) for x in args.res.lower().split("x"))

    print(f"[scan] frames {start}..{end} at {w}x{h} — rendering all "
          f"{end - start + 1} frames (previz rate ~0.3s/frame)")
    rendered = _render_range(start, end, outdir, w, h, args.engine)
    series = _diff_series(rendered)
    evs = _events(series, args.top)

    print("[scan] EVENT-TABLE (ranked by peak pixel-diff; floor = "
          "median+2*MAD)")
    if not evs:
        print("[scan] no significant change events — motion is smooth or "
              "below scan resolution; widen range or raise --res if in doubt")
    for i, e in enumerate(evs):
        span = (f"f{e['start']}" if e['start'] == e['end']
                else f"f{e['start']}..f{e['end']}")
        print(f"  #{i + 1}: {span}  peak f{e['peak_frame']} "
              f"(diff {e['peak_diff']:.3f}, mean {e['mean']:.3f})")

    strip = None
    if evs:
        pw, ph = (int(x) for x in args.peak_res.lower().split("x"))
        strip = _suspect_strip(evs, outdir, pw, ph, args.engine)

    # cleanup scan frames (the diff already consumed them)
    for _, p in rendered:
        try:
            os.remove(p)
        except OSError:
            pass

    if strip:
        print(f"[scan] suspects strip: {strip}")
    print("[scan] DOCTRINE: the scanner RANKS, the eyes VERDICT — look at "
          "the suspects strip, then confirm each suspect at full res: "
          "look.py --load-blend <state> --frame <peak> --angles none "
          "--closeup <id>. Transients hide BETWEEN keyframes; a clean "
          "keyframe sheet proves nothing about them.")


if __name__ == "__main__":
    main()
