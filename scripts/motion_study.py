"""
motion_study.py — animation perception for vision agents (vision-kit M5 P3).

One invocation answers "what does this animation DO" for an agent that
understands images: renders the three representations that measured best
on native eyes (docs/TUNING_perception_v1.md, P3 lab), and prints the
numeric motion table BESIDE the images (look.py's forced-pairing rule):

  1. onion-skin ghost strip  — WINNER for rise/fall, speed, direction.
     Ghost spacing encodes speed; opacity encodes age (lightest = oldest).
     Vertical nuance that filmstrips lose reads instantly here.
  2. trajectory overlay      — WINNER for path SHAPE. Full sampled polyline
     of every tracked object + time ticks. Rendered in a 2-angle grid
     (top + front): a purely-vertical trail collapses from one angle
     (measured) — two orthogonal angles make every path readable.
  3. filmstrip               — supplementary time-ordered frames
     (translation drift over time; spin is INVISIBLE here — measured).

Numeric block: per-object sampled world positions, per-step displacement,
teleport/jump flags (step delta >> median delta = pop, the #1 transient
animation bug), and static-despite-keyed flags.

Usage (via blrun.sh --background --python scripts/motion_study.py -- ...):
  --scene mod_name | --load-blend file.blend
  --objects A,B    track only these ids (default: top-3 non-ground meshes)
  --samples 8      ghost/filmstrip sample count
  --start N --end N  frame range (default: scene range)
  --out DIR        output dir (default output/<scene>/motion)
  --res WxH        representation resolution (default 640x480)
  --no-filmstrip   skip the supplementary strip

LAW (parity with annotate.py): every helper object carries the
KIT_MOTION_ prefix and is deleted in a finally. Nothing is saved.
"""
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

MOTION_PREFIX = "KIT_MOTION_"

# Ghost age ramp: index 0 = OLDEST ghost (lightest), last = CURRENT (solid).
# Measured (P3): light-to-dark read as past->now is instantaneous; alpha
# ramp alone (transparency) is unreliable in Workbench solid shading.
_GHOST_RGB = [
    (0.82, 0.82, 0.86, 1.0),   # oldest: near-white
    (0.62, 0.62, 0.70, 1.0),
    (0.42, 0.42, 0.55, 1.0),
    (0.18, 0.18, 0.30, 1.0),   # newest ghost: dark
]
_CURRENT_RGB = (0.90, 0.15, 0.15, 1.0)  # current pose: solid red (reads "now")
_TRAJ_RGB = (0.10, 0.75, 0.25, 1.0)     # trajectory: green
_TICK_RGB = (0.95, 0.85, 0.10, 1.0)     # time ticks: yellow


def _parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--scene", default=None)
    p.add_argument("--load-blend", default=None)
    p.add_argument("--objects", default=None,
                   help="comma-separated object ids to track (default top-3)")
    p.add_argument("--samples", type=int, default=8)
    p.add_argument("--start", type=int, default=None)
    p.add_argument("--end", type=int, default=None)
    p.add_argument("--out", default=None)
    p.add_argument("--res", default="640x480")
    p.add_argument("--no-filmstrip", action="store_true")
    p.add_argument("--engine", default="workbench")
    return p.parse_args(argv)


def _make_mat(name_key: str, rgba):
    """Material with BOTH node Base Color and viewport diffuse_color set
    (kit law 6: Workbench MATERIAL reads diffuse_color, engines read nodes)."""
    mat = bpy.data.materials.new(f"{MOTION_PREFIX}mat_{name_key}")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None and "Base Color" in bsdf.inputs:
        bsdf.inputs["Base Color"].default_value = rgba
    mat.diffuse_color = rgba
    return mat


def _eval_matrix_world(obj, frame):
    """LIVE-READ world matrix at a frame (kit stale-read law: frame_set +
    double view_layer update before ANY read — prop_carry.py:53)."""
    scene = bpy.context.scene
    scene.frame_set(frame)
    scene.view_layer.update()
    scene.view_layer.update()
    return obj.matrix_world.copy()


def _world_bbox(obj, frame):
    """(min,max) world bbox of obj evaluated at frame."""
    mw = _eval_matrix_world(obj, frame)
    pts = [mw @ Vector(c) for c in obj.bound_box]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return mn, mx


def _groundlike(o):
    return o.dimensions.z <= 0.05 and (o.dimensions.x * o.dimensions.y) >= 6.0


def _pick_objects(n_target):
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH'
              and not o.name.startswith(MOTION_PREFIX) and not _groundlike(o)]
    return sorted(meshes, key=lambda o: -o.dimensions.length)[:n_target]


def _sample_positions(objs, frames):
    """{name: {frame: Vector}} world positions at each sample frame."""
    table = {}
    for o in objs:
        table[o.name] = {}
        for f in frames:
            mn, mx = _world_bbox(o, f)
            table[o.name][f] = (mn + mx) / 2.0
    return table


def _thin_box(name, p0, p1, thickness, mat):
    p0, p1 = Vector(p0), Vector(p1)
    mid = (p0 + p1) / 2.0
    dims = [max(abs(p1[i] - p0[i]), thickness) for i in range(3)]
    mesh = bpy.data.meshes.new(name)
    cube = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(cube)
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bm.to_mesh(mesh)
    bm.free()
    cube.scale = dims
    cube.location = mid
    cube.data.materials.append(mat)
    return cube


# ---------------------------------------------------------------------------
# Representation 1: onion-skin ghosts (the speed/direction/rise winner)
# ---------------------------------------------------------------------------

def build_onion_skin(objs, frames):
    """Ghost copies of each object at each sampled frame. Oldest = lightest,
    current frame = solid red. Ghost SPACING encodes speed (measured P3)."""
    made = []
    mats = [_make_mat(f"ghost{i}", rgb) for i, rgb in enumerate(_GHOST_RGB)]
    cur_mat = _make_mat("current", _CURRENT_RGB)
    n = len(frames)
    for o in objs:
        for i, f in enumerate(frames[:-1]):
            # map ghost age onto the 4-step ramp (oldest sample = index 0)
            mat_i = min(3, int(i * 4 / max(n - 1, 1)))
            ghost = o.copy()
            # CRITICAL: full mesh COPY, not linked duplicate — material
            # slots live on mesh data; a linked dup shares them and
            # materials.clear() would strip the REAL object's materials.
            ghost.data = o.data.copy()
            ghost.data.name = f"{MOTION_PREFIX}mesh_{o.name}_{f}"
            ghost.name = f"{MOTION_PREFIX}ghost_{o.name}_{f}"
            ghost.matrix_world = _eval_matrix_world(o, f)
            # strip animation from the ghost so it stays put at render frame
            ghost.animation_data_clear()
            for c in list(ghost.constraints):
                ghost.constraints.remove(c)
            bpy.context.collection.objects.link(ghost)
            ghost.data.materials.clear()
            ghost.data.materials.append(mats[mat_i])
            made.append(ghost)
        # current pose (solid red = "now"; own mesh copy — see ghost note)
        cur = o.copy()
        cur.data = o.data.copy()
        cur.data.name = f"{MOTION_PREFIX}mesh_{o.name}_cur"
        cur.name = f"{MOTION_PREFIX}current_{o.name}"
        cur.matrix_world = _eval_matrix_world(o, frames[-1])
        cur.animation_data_clear()
        for c in list(cur.constraints):
            cur.constraints.remove(c)
        bpy.context.collection.objects.link(cur)
        cur.data.materials.clear()
        cur.data.materials.append(cur_mat)
        made.append(cur)
    return made


# ---------------------------------------------------------------------------
# Representation 2: trajectory polylines (the path-shape winner)
# ---------------------------------------------------------------------------

def build_trajectories(objs, start, end, coarse=48):
    """Dense polyline of each object's center path + yellow time ticks.
    Tick spacing = speed (denser ticks = slower); polyline = path shape."""
    made = []
    traj_mat = _make_mat("traj", _TRAJ_RGB)
    tick_mat = _make_mat("tick", _TICK_RGB)
    frames = [start + int(i * (end - start) / max(coarse - 1, 1))
              for i in range(coarse)]
    for o in objs:
        pts = []
        for f in frames:
            mn, mx = _world_bbox(o, f)
            pts.append((mn + mx) / 2.0)
        # polyline as chained thin boxes (kit convention: geometry, not curves)
        for i in range(len(pts) - 1):
            a, b = pts[i], pts[i + 1]
            if (b - a).length < 1e-4:
                continue
            made.append(_thin_box(
                f"{MOTION_PREFIX}traj_{o.name}_{i}", a, b, 0.015, traj_mat))
        # time ticks: every coarse/8-th sample point, small yellow cubes
        step = max(coarse // 8, 1)
        for i in range(0, len(pts), step):
            p = pts[i]
            s = 0.05
            made.append(_thin_box(
                f"{MOTION_PREFIX}tick_{o.name}_{i}",
                (p.x - s, p.y - s, p.z - s), (p.x + s, p.y + s, p.z + s),
                0.02, tick_mat))
    return made


# ---------------------------------------------------------------------------
# Numeric block: the motion table (printed beside the images)
# ---------------------------------------------------------------------------

def motion_numbers(objs, start, end, frames):
    """Per-object per-step displacement + pop/static flags. Printed as text
    so the agent gets NUMBERS with its pictures (forced pairing)."""
    scene = bpy.context.scene
    step_frames = [start + int(i * (end - start) / max(len(frames) - 1, 1))
                   for i in range(len(frames))]
    lines = []
    for o in objs:
        deltas = []
        prev = None
        for f in step_frames:
            mn, mx = _world_bbox(o, f)
            c = (mn + mx) / 2.0
            if prev is not None:
                deltas.append((f, (c - prev).length))
            prev = c
        if not deltas:
            continue
        mags = [d for _, d in deltas]
        med = sorted(mags)[len(mags) // 2]
        # pop = step >> median (teleport / sim instability)
        pops = [(f, round(d, 3)) for f, d in deltas if med > 0 and d > max(4 * med, 0.25)]
        static = all(d < 1e-4 for d in mags)
        arc = "static" if static else f"median-step {med:.3f}m"
        line = (f"  {o.name}: start {step_frames[0]} end {step_frames[-1]}, "
                f"{arc}")
        if pops:
            line += f"  POP-FRAMES {pops}  <-- suspect transient"
        lines.append(line)
    return lines


# ---------------------------------------------------------------------------
# Filmstrip (supplementary)
# ---------------------------------------------------------------------------

def filmstrip(frames, outdir, w, h, engine, cols=4):
    import viewport_capture as vc
    paths = []
    for f in frames:
        p = os.path.join(outdir, f"strip_f{f:04d}.png")
        vc.render_angle("persp", p, engine=engine, width=w, height=h)
        paths.append(p)
    sheet = os.path.join(outdir, "filmstrip.png")
    vc.stitch_contact_sheet(paths, sheet, grid_cols=cols)
    for p in paths:
        try:
            os.remove(p)
        except OSError:
            pass
    return sheet


# ---------------------------------------------------------------------------

def main():
    args = _parse_args()
    if args.load_blend:
        bpy.ops.wm.open_mainfile(filepath=args.load_blend)
    elif args.scene:
        from blender_kit import safe_import_scene, clear_scene
        mod = safe_import_scene(args.scene)
        clear_scene()
        ctx = mod.build_scene()
        if hasattr(mod, "animate"):
            mod.animate(ctx, start_frame=1, n_frames=64)
    scene = bpy.context.scene
    if not args.load_blend and not args.scene:
        print("[motion] ERROR: need --scene or --load-blend")
        sys.exit(1)
    start = args.start if args.start is not None else scene.frame_start
    end = args.end if args.end is not None else scene.frame_end
    if end <= start:
        print(f"[motion] ERROR: frame range {start}..{end} is empty — "
              "this scene has no animation to study")
        sys.exit(1)

    w, h = (int(x) for x in args.res.lower().split("x"))
    n = max(args.samples, 2)
    frames = [start + int(i * (end - start) / max(n - 1, 1)) for i in range(n)]

    objs = ([bpy.context.scene.objects.get(nm.strip()) for nm in args.objects.split(",")]
            if args.objects else None)
    objs = [o for o in (objs or []) if o] or _pick_objects(3)
    print(f"[motion] tracking {len(objs)} objects over frames {start}..{end} "
          f"(samples {frames})")

    outdir = args.out or os.path.join(
        "output", args.scene or os.path.basename(args.load_blend or "motion"),
        "motion")
    os.makedirs(outdir, exist_ok=True)

    import viewport_capture as vc

    made = []
    try:
        # --- numbers FIRST (forced pairing: numbers beside images) --------
        print("[motion] MOTION-TABLE (center displacement per step)")
        for ln in motion_numbers(objs, start, end, frames):
            print(ln)

        # --- trajectories + onion-skin in ONE state, 2 angles -------------
        # Trajectory needs the DENSE path; onion needs the SAMPLED ghosts.
        # Build both into the same scene: trajectory polylines from dense
        # sampling, ghosts from the sample frames, then render top+front.
        # The onion read needs the ghosts NEAR the path — same frame state.
        made += build_trajectories(objs, start, end, coarse=48)
        made += build_onion_skin(objs, frames)
        bpy.context.view_layer.update()

        # hide the REAL objects: their current pose is the red ghost copy
        real_hidden = []
        for o in objs:
            o.hide_render = True
            real_hidden.append(o)

        grid = os.path.join(outdir, "onion_traj.png")
        tmp = []
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            for lbl in ("top", "front"):
                p = os.path.join(td, f"{lbl}.png")
                vc.render_angle(lbl, p, engine=args.engine, width=w, height=h)
                tmp.append(p)
            vc.stitch_contact_sheet(tmp, grid, grid_cols=2)
        print(f"[motion] onion+trajectory grid: {grid}")

        # restore reals, strip the motion layer, filmstrip the raw scene
        for o in real_hidden:
            o.hide_render = False
        strip = None
        if not args.no_filmstrip:
            strip = filmstrip(frames, outdir, w, h, args.engine)
            print(f"[motion] filmstrip: {strip}")
    finally:
        for o in made:
            try:
                bpy.data.objects.remove(o, do_unlink=True)
            except Exception:
                pass
        for m in list(bpy.data.materials.keys()):
            if m.startswith(f"{MOTION_PREFIX}mat_"):
                bpy.data.materials.remove(bpy.data.materials[m])
        for me in list(bpy.data.meshes.keys()):
            if me.startswith(MOTION_PREFIX):
                bpy.data.meshes.remove(bpy.data.meshes[me])

    print("[motion] READ-ORDER: 1) trajectory grid for path SHAPE "
          "(top=plan view, front=elevation), 2) ghost spacing for SPEED, "
          "3) ghost lightness for AGE (lightest=oldest, red=now), "
          "4) POP-FRAMES in the table above = transient suspects -> "
          "transient_scan.py / look.py --frame N --closeup")


if __name__ == "__main__":
    main()
