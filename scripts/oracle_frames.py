# VENDORED 2026-10-16 from mainline blender-agent-kit @6943ab5 (vision-kit s21 vendor round; zero code drift; vision deltas must land as sanctioned deltas per docs/VENDOR_LEDGER.md)
"""
oracle_frames.py -- the Blender-side oracle sidecar (the A' half of the
A/B oracle's stricter form; app-side spec:
webpreviz reviews/2026-10-13-r621-oracle-e2e-design.md §7).

WHAT THIS IS: a headless bpy run over the SOURCE .blend that evaluates
each scene object's ``matrix_world`` at the oracle's frame plan and
writes ``oracle_frames.json`` next to the package. The app's harness
gains a "side A'" mode comparing Blender-world vs GLB-evaluated-world
FIRST (export fidelity: catches exporter constraint-baking/order bugs
the in-package oracle cannot see -- e.g. a TRACK_TO whose Aim export is
stale), then GLB-vs-runtime as designed.

THE FRAME PLAN (mirrors the app's law, §6 -- deterministic given the
scene, so both sides re-derive the same set):
  1. every shot's f0 and f1 (the marker table, the exporter's own
     binding);
  2. every animated channel's key frames (fcurve keyframe_points),
     capped per-channel at first/mid/last + a 24-frame stride after the
     first 200 keys (LINEAR interpolation is proven at endpoints +
     midpoints by construction);
  3. a uniform 24-frame stride across the whole timeline;
  4. the tail: frame_end and frame_end - 1 (the held-last-key law);
  5. the per-shot camera plan f0, f0+1, f0+2, mid, f1-1, f1.

Output shape (oracle_frames.json):
  {
    "scene": str, "fps": int, "frame_start": int, "frame_end": int,
    "blender_version": str, "generated_at": str, "git_sha": str,
    "plan": [int, ...],
    "objects": {
      "<blender object name>": {
        "type": "MESH"|"CAMERA"|"EMPTY"|"ARMATURE"|...,
        "animated": bool,
        "frames": { "<frame>": {
            "blender": {"p":[x,y,z], "q":[x,y,z,w], "s":[x,y,z]},
            "gltf":   {"p":[x,y,z], "q":[x,y,z,w], "s":[x,y,z]}
        } }
      }
    },
    "cameras": { "<name>": { lens_mm, sensor_width_mm, sensor_fit,
                             shift_x, shift_y, clip_start_m, clip_end_m } }
  }

The "blender" rows decompose obj.matrix_world RAW (Z-up). The "gltf"
rows decompose R @ matrix_world with R = Rotation(-90 deg, X) -- the
Blender glTF exporter's Z-up -> Y-up law, the same conversion the
package's node TRS carries (the app's A' leg compares the gltf rows
against its GLB world-TRS reconstruction; the blender rows stay for
diagnosis of any systematic rotation disagreement).

Usage:
    blrun.sh --background --python scripts/oracle_frames.py -- \
        --scene scene_terminal_dawn \
        --out public/packages/tdawn_3/oracle_frames.json

Notes:
  * The census is a SUPERSET (every scene object incl. non-exported
    ones); the app's A' leg matches by its own name law and simply
    ignores rows absent from the GLB. Never a failure to have extras.
  * Static objects are evaluated at ONE frame (the plan's first) and
    repeated verbatim per plan frame -- matrix_world of a static object
    is constant, and the repetition keeps the app-side comparison
    stateless. (Set --static-once to emit a single "static" row
    instead; the app handles both shapes.)
  * Never throws on a single bad object -- the row is skipped with a
    receipt in "skipped" (the fail-soft posture).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
from datetime import datetime, timezone

import bpy
from mathutils import Matrix

# The Blender glTF exporter's Z-up -> Y-up root conversion (the law the
# package's node TRS carries). Kept as a module constant so tests can
# assert it is a pure rotation.
GLTF_AXIS = Matrix.Rotation(math.radians(-90), 4, "X")


def _git_sha() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()
    except Exception:
        return "unknown"


def _marker_shots(scene) -> list:
    """The shot table (ids + ranges) -- the same binding the package
    exporter reads (SHOTS_V3/SHOTS + timeline markers fallback)."""
    try:
        from blender_kit import script_argv  # noqa: F401  (presence probe)
    except Exception:
        pass
    # The scene module is loaded by the caller's --scene convention
    # (blrun.sh); in this script the SHOTS table arrives via the scene's
    # timeline markers or the module global the kit injects. The marker
    # fallback is authoritative here: markers bind cameras to ranges.
    ms = sorted(
        (m for m in scene.timeline_markers),
        key=lambda m: m.frame,
    )
    shots = []
    for i, m in enumerate(ms):
        f1 = ms[i + 1].frame - 1 if i + 1 < len(ms) else scene.frame_end
        shots.append((m.name, m.frame, f1))
    return shots


def _channel_key_frames(scene, cap: int = 200, stride: int = 24) -> set:
    """Every animated channel's key frames (the adjectives from §6:
    first/mid/last + a stride after the first `cap` keys)."""
    frames: set = set()
    for action in bpy.data.actions:
        for fc in action.fcurves:
            if fc is None or fc.keyframe_points is None:
                continue
            pts = [int(round(p.co.x)) for p in fc.keyframe_points]
            if not pts:
                continue
            if len(pts) <= cap:
                frames.update(pts)
            else:
                frames.update([pts[0], pts[len(pts) // 2], pts[-1]])
                frames.update(pts[::stride])
    return frames


def _decompose(matrix: Matrix) -> dict:
    loc, quat, scale = matrix.decompose()
    return {
        "p": [round(v, 9) for v in loc],
        "q": [round(v, 9) for v in quat],
        "s": [round(v, 9) for v in scale],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--scene", required=True, help="scene id (the kit convention)")
    parser.add_argument("--out", required=True, help="output oracle_frames.json path")
    parser.add_argument("--stride", type=int, default=24)
    parser.add_argument("--static-once", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv)

    scene = bpy.context.scene
    fps = scene.render.fps
    f_start, f_end = int(scene.frame_start), int(scene.frame_end)
    shots = _marker_shots(scene)

    # The frame plan (§6's law).
    plan: set = set()
    for _, f0, f1 in shots:
        plan.update((f0, f1))
        mid = (f0 + f1) // 2
        plan.update((f0 + 1, f0 + 2, mid, f1 - 1))
    plan.update(_channel_key_frames(scene))
    plan.update(range(f_start, f_end + 1, args.stride))
    plan.update((f_end, f_end - 1))
    plan = sorted(f for f in plan if f_start <= f <= f_end)

    # The census (every scene object -- the superset posture).
    objects: dict = {}
    skipped: list = []
    animated_names = set()
    for ob in scene.objects:
        if ob.animation_data and ob.animation_data.action:
            animated_names.add(ob.name)
    for ob in scene.objects:
        try:
            rows: dict = {}
            is_animated = ob.name in animated_names
            if args.static_once and not is_animated:
                scene.frame_set(plan[0])
                rows[str(plan[0])] = {
                    "blender": _decompose(ob.matrix_world.copy()),
                    "gltf": _decompose(GLTF_AXIS @ ob.matrix_world),
                }
            else:
                for f in plan:
                    scene.frame_set(f)
                    rows[str(f)] = {
                        "blender": _decompose(ob.matrix_world.copy()),
                        "gltf": _decompose(GLTF_AXIS @ ob.matrix_world),
                    }
            objects[ob.name] = {
                "type": ob.type,
                "animated": is_animated,
                "frames": rows,
            }
        except Exception as e:  # noqa: BLE001 -- fail-soft per object
            skipped.append(f"{ob.name}: {e}")
    # Restore the frame.
    scene.frame_set(f_start)

    cameras: dict = {}
    for ob in scene.objects:
        if ob.type == "CAMERA":
            d = ob.data
            fit = {"AUTO": "AUTO", "HORIZONTAL": "HORIZONTAL", "VERTICAL": "VERTICAL"}.get(
                d.sensor_fit, "AUTO"
            )
            cameras[ob.name] = {
                "lens_mm": round(float(d.lens), 6),
                "sensor_width_mm": round(float(d.sensor_width), 6),
                "sensor_fit": fit,
                "shift_x": round(float(d.shift_x), 9),
                "shift_y": round(float(d.shift_y), 9),
                "clip_start_m": round(float(d.clip_start), 9),
                "clip_end_m": round(float(d.clip_end), 9),
            }

    doc = {
        "schema": "oracle-frames/1",
        "scene": args.scene,
        "fps": int(fps),
        "frame_start": f_start,
        "frame_end": f_end,
        "shots": [{"id": s[0], "f0": s[1], "f1": s[2]} for s in shots],
        "blender_version": bpy.app.version_string,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "git_sha": _git_sha(),
        "plan": plan,
        "objects": objects,
        "cameras": cameras,
        "skipped": skipped,
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(doc, f)
    n_rows = sum(len(o["frames"]) for o in objects.values())
    print(
        f"[oracle_frames] {args.scene}: {len(objects)} objects x {len(plan)} plan "
        f"frames = {n_rows} rows ({len(skipped)} skipped) -> {args.out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
