"""
render_previz_truth.py -- Blender ground-truth renderer for the web-review
pixel-exactness harness, stills refresh + timeline filmstrips.

Two render modes (the two looks this project ships):

  --mode eevee      Eevee NEXT + view_transform Standard + the scene's
                    Nishita sky world + atmosphere VISIBLE = the anim.mp4
                    look ("what Blender renders"). Used to tune the app's
                    'lit' viewer mode.
  --mode workbench  WORKBENCH + MATERIAL colors + STUDIO light, shadows
                    OFF, cavity BOTH (1.8/2.0), FlatGuidance world
                    (0.50,0.50,0.52), atmosphere HIDDEN = the shot-stills
                    look (the historical --quality viewport pipeline,
                    scripts/__init__.py apply_quality). Used to tune the
                    app's 'flat' viewer mode + to regenerate stills.

Outputs (any combination):
  --frames 1,180,409        truth stills  <out>/truth_f<F>.jpg
  --stills                  shot midpoints (current marker table) saved as
                            <out>/shot_<ID>.jpg -- drop-in stills refresh
  --truth-json              per-frame optics + projected-actor truth
  --filmstrips DIR          per-shot low-res thumbs for the NLE timeline
                            (filmstrips/<shot>_<k>.jpg + filmstrips.json)

Usage:
    blrun.sh --background --python scripts/render_previz_truth.py -- \
        --scene scene_escape_v3_3 \
        --mode workbench --stills --out output/stills_v34 \
        --filmstrips output/filmstrips_v34 --strip-frames 8

Truth JSON per frame:
    { frame, camera, lens_mm, sensor_mm, sensor_fit, shift, matrix,
      resolution, actors: {name: {bbox_frac, centroid_frac}} }
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

from blender_kit import normalize_engine_id, script_argv, atmo_objects


def _parse_size(s: str) -> tuple[int, int]:
    w, h = s.lower().split("x")
    return int(w), int(h)


def _marker_shots(scene, mod) -> list[tuple[str, int, int]]:
    """Shot table from the module's SHOTS_V3/SHOTS constant (ids +
    ranges), cameras bound via timeline markers — same binding the
    package exporter reads."""
    marks = {m.frame: m.camera.name for m in scene.timeline_markers
             if m.camera is not None}
    rows = getattr(mod, "SHOTS_V3", None) or getattr(mod, "SHOTS", [])
    shots = []
    for row in rows:
        sid, f0, f1 = row[0], row[1], row[2]
        shots.append((sid, f0, f1))
    if not shots:  # fallback: derive from markers alone
        ms = sorted(scene.timeline_markers, key=lambda m: m.frame)
        for i, m in enumerate(ms):
            f1 = ms[i + 1].frame - 1 if i + 1 < len(ms) else scene.frame_end
            shots.append((m.name, m.frame, f1))
    return shots


def _apply_mode(scene, mode: str) -> list:
    """Configure the engine/world for the selected look. Returns the
    list of atmo objects (callers in workbench mode hide them)."""
    atmo = atmo_objects(scene)
    if mode == "workbench":
        scene.render.engine = "BLENDER_WORKBENCH"
        scene.display.shading.color_type = 'MATERIAL'
        scene.display.shading.light = 'STUDIO'
        scene.display.shading.show_shadows = False
        scene.display.shading.show_cavity = True
        scene.display.shading.cavity_type = 'BOTH'
        scene.display.shading.cavity_ridge_factor = 1.8
        scene.display.shading.cavity_valley_factor = 2.0
        scene.display.render_aa = 'FXAA'
        w = bpy.data.worlds.new("FlatGuidance")
        # session-24 law: world.use_nodes = False is a SILENT NO-OP on
        # 5.x — the auto-created tree (a 0.05 dark-grey Background)
        # would render instead of w.color. Build the flat world as an
        # EXPLICIT Background-node tree: identical output on 4.5 & 5.2.
        w.use_nodes = True
        nt = w.node_tree
        for n in list(nt.nodes):
            nt.nodes.remove(n)
        out = nt.nodes.new("ShaderNodeOutputWorld")
        bg = nt.nodes.new("ShaderNodeBackground")
        bg.inputs["Color"].default_value = (0.50, 0.50, 0.52, 1.0)
        bg.inputs["Strength"].default_value = 1.0
        nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
        scene.world = w
        for ob in atmo:
            ob.hide_render = True
        return atmo
    # eevee (default) — engine id is version-dependent (4.x:
    # BLENDER_EEVEE_NEXT, 5.x: BLENDER_EEVEE)
    scene.render.engine = normalize_engine_id("BLENDER_EEVEE_NEXT")
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    # sandbox OOM guard (4GB box, llvmpipe software GL): 16 TAA samples +
    # 512px shadow cubes keep Eevee under ~2GB while preserving the
    # soft-shadow look (all 10 rig lights cast shadows).
    # session-24: shadow_cube_size/cascade_size were REMOVED in 5.x —
    # replaced by shadow_resolution_scale (0.5 halves shadow maps).
    try:
        scene.eevee.taa_render_samples = 16
        if hasattr(scene.eevee, "shadow_cube_size"):
            scene.eevee.shadow_cube_size = '512'
            scene.eevee.shadow_cascade_size = '1024'
        else:
            scene.eevee.shadow_resolution_scale = 0.5
    except Exception as e:
        print(f"[truth] NOTE: eevee tuning skipped: {e}", flush=True)
    return atmo


def _project_group(scene, camera, parts) -> dict:
    cam_inv = camera.matrix_world.inverted()
    world_pts = []
    for part in parts:
        for corner in part.bound_box:
            world_pts.append(part.matrix_world @ Vector(corner))
    front = [w for w in world_pts if (cam_inv @ w).z < 0.0]
    if not front:
        return {"visible": False}
    fr = [world_to_camera_view(scene, camera, w) for w in front]
    xs = [p.x for p in fr]
    ys = [1.0 - p.y for p in fr]           # top-left origin
    cl = lambda v: max(0.0, min(1.0, v))   # noqa: E731
    return {
        "visible": True,
        "bbox_frac": [cl(min(xs)), cl(min(ys)), cl(max(xs)), cl(max(ys))],
        "centroid_frac": [
            cl(sum(p.x for p in fr) / len(fr)),
            cl(sum(1.0 - p.y for p in fr) / len(fr)),
        ],
    }


def _actor_groups(scene) -> dict[str, list]:
    """Character bodies + jeep: the groups the review app tracks."""
    groups: dict[str, list] = {}
    for ob in scene.objects:
        if ob.type != 'MESH':
            continue
        key = None
        for char in ("Gunner", "Girl", "Driver", "Horde"):
            if char in ob.name:
                key = char
                break
        if ob.name.startswith("Jeep"):
            key = "Jeep"
        if key:
            groups.setdefault(key, []).append(ob)
    return groups


def main() -> None:
    p = argparse.ArgumentParser(
        description="Render Blender ground truth for the review harness.")
    p.add_argument("--scene", required=True,
                   help="Scene module name (importable from scripts/).")
    p.add_argument("--mode", default="eevee",
                   choices=["eevee", "workbench"],
                   help="Render look: eevee (anim) or workbench (stills).")
    p.add_argument("--frames", default="",
                   help="Comma-separated frames to render as truth_f<F>.jpg.")
    p.add_argument("--stills", action="store_true",
                   help="Render shot midpoints as shot_<ID>.jpg (refresh).")
    p.add_argument("--out", default="output/truth",
                   help="Output directory for stills + truth JSON.")
    p.add_argument("--size", default="960x540",
                   help="Render size WxH (default 960x540).")
    p.add_argument("--truth-json", action="store_true",
                   help="Emit per-frame optics/actor truth JSON.")
    p.add_argument("--filmstrips", default=None,
                   help="Directory for per-shot filmstrip thumbs.")
    p.add_argument("--strip-frames", type=int, default=8,
                   help="Thumbs per shot (default 8).")
    p.add_argument("--strip-size", default="96x54",
                   help="Thumb size (session-23: 96x54 -- the NLE lane "
                        "renders thumbs at ~40px tall; 192x108 was 4x "
                        "wasteful and populated slowly).")
    p.add_argument("--hero-rig", default=None, choices=("capsule", "ual"),
                   help="Override the scene module's hero system before "
                        "build_scene (pass ual for rigged heroes).")
    args = p.parse_args(script_argv())

    import importlib
    # session-25: Blender does NOT add the --python script's dir to
    # sys.path in --background mode (cwd-independent import).
    _here = os.path.dirname(os.path.abspath(__file__))
    if _here not in sys.path:
        sys.path.insert(0, _here)
    print(f"[truth] importing scene module: {args.scene}", flush=True)
    mod = importlib.import_module(args.scene)
    if args.hero_rig and getattr(mod, "HERO_MODE", None) != args.hero_rig:
        mod.HERO_MODE = args.hero_rig
        print(f"[truth] hero rig override: HERO_MODE = {args.hero_rig}",
              flush=True)
    ctx = mod.build_scene()
    if hasattr(mod, "animate"):
        mod.animate(ctx, start_frame=1, n_frames=None)
    scene = ctx["scene"]

    atmo = _apply_mode(scene, args.mode)
    print(f"[truth] mode={args.mode} atmo_objects="
          f"{[ob.name for ob in atmo]}", flush=True)

    scene.render.image_settings.file_format = 'JPEG'
    scene.render.image_settings.quality = 92
    w, h = _parse_size(args.size)
    scene.render.resolution_x = w
    scene.render.resolution_y = h
    scene.render.resolution_percentage = 100

    # record the light rig (shadow state matters for web parity)
    rig = []
    for ob in scene.objects:
        if ob.type == 'LIGHT':
            rig.append({
                "name": ob.name, "type": str(ob.data.type),
                "energy": round(ob.data.energy, 3),
                "shadow": bool(ob.data.use_shadow),
                "loc": [round(v, 3) for v in ob.matrix_world.translation],
            })

    os.makedirs(args.out, exist_ok=True)
    truth: dict = {"render_size": [w, h], "mode": args.mode,
                   "view_transform": ("Standard" if args.mode == "eevee"
                                      else "workbench-studio"),
                   "lights": rig, "frames": {}}
    groups = _actor_groups(scene)
    shots = _marker_shots(scene, mod)

    def render_frame(f: int, rel: str, collect: bool) -> dict | None:
        scene.frame_set(f)
        cam = scene.camera
        if cam is None:
            print(f"[truth] WARN: no active camera at f{f}", flush=True)
            return None
        scene.render.filepath = os.path.join(args.out, rel)
        bpy.ops.render.render(write_still=True)
        entry = {
            "camera": cam.name,
            "lens_mm": round(cam.data.lens, 3),
            "sensor_width_mm": round(cam.data.sensor_width, 3),
            "sensor_fit": str(cam.data.sensor_fit),
            "shift": [round(cam.data.shift_x, 4),
                      round(cam.data.shift_y, 4)],
            "clip": [round(cam.data.clip_start, 3),
                     round(cam.data.clip_end, 3)],
            "matrix_world": [[round(v, 4) for v in row]
                             for row in cam.matrix_world],
        }
        if collect:
            entry["actors"] = {
                k: _project_group(scene, cam, parts)
                for k, parts in sorted(groups.items())}
        print(f"[truth] f{f}: {cam.name} -> {rel}", flush=True)
        return entry

    # ---- explicit truth frames ----
    for f in [int(x) for x in args.frames.split(",") if x.strip()]:
        e = render_frame(f, f"truth_f{f}.jpg", args.truth_json)
        if e:
            truth["frames"][f] = e

    # ---- stills refresh (shot midpoints, current marker table) ----
    if args.stills:
        for sid, f0, f1 in shots:
            mid = (f0 + f1) // 2
            render_frame(mid, f"shot_{sid}.jpg", False)
        print(f"[truth] stills refreshed: {len(shots)} shots", flush=True)

    # ---- filmstrips ----
    if args.filmstrips:
        sw, sh = _parse_size(args.strip_size)
        scene.render.resolution_x = sw
        scene.render.resolution_y = sh
        os.makedirs(args.filmstrips, exist_ok=True)
        manifest: dict[str, list] = {}
        for sid, f0, f1 in shots:
            n = args.strip_frames
            span = f1 - f0 + 1
            thumbs = []
            for k in range(n):
                f = f0 + round(k * (span - 1) / max(1, n - 1))
                scene.frame_set(f)
                if scene.camera is None:
                    continue
                rel = f"{sid}_{k:02d}.jpg"
                scene.render.filepath = os.path.join(args.filmstrips, rel)
                bpy.ops.render.render(write_still=True)
                thumbs.append({"i": k, "frame": f, "file": rel})
            manifest[sid] = thumbs
            print(f"[truth] filmstrip {sid}: {len(thumbs)} thumbs "
                  f"(f{f0}-f{f1})", flush=True)
        with open(os.path.join(args.filmstrips, "filmstrips.json"),
                  "w") as f:
            json.dump({"thumb_size": [sw, sh], "shots": manifest}, f,
                      indent=1)

    if args.truth_json or truth["frames"]:
        with open(os.path.join(args.out, "truth.json"), "w") as f:
            json.dump(truth, f, indent=1)
        print(f"[truth] truth.json written ({len(truth['frames'])} frames)",
              flush=True)
    print("[truth] done", flush=True)


if __name__ == "__main__":
    main()
