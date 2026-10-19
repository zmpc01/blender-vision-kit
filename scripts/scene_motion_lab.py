"""
scene_motion_lab.py — the s20 DOG-FOOD scene: a humanoid motion laboratory
built entirely on the vendored rh_canvas surface + the offline fixture
library (scripts/rh_fixture_lib.py -> /home/z/rh_fixture_lib).

The consumer story this module exercises (the session-20 mandate):
  catalog -> pick clips by tags/duration -> import-clip -> mannequin ->
  placement (armature-first: move_to/place_on via the placement_lib
  ARMATURE branches) -> statues as set dressing -> multi-actor union
  range -> per-actor MOTION STRIPS (the vision-native animation check)
  -> stills -> GLB.

Layout (top view, +Y north):
        z
        |   [JUMP platform @ (6, 3)]        [SIT bench @ (-3, 4)]
        |   [DANCE @ (3, 0)]  [RUN travel x 0..3]
        |   [WAVE @ (-2, 0)] [WALK @ (-6, 0)]
        |   [DIE casualty @ (5, -3)]
        |   [statue Farmer @ (-5, -4)] [statue Vendor @ (2, -5)]
        +---------------- x ----------------

Run:
  export RH_CANVAS_LIB=/home/z/rh_fixture_lib
  ./scripts/blrun.sh --background --python scripts/scene_motion_lab.py -- \
      --output output/motion_lab --engine workbench --stills wide,front,side \
      --motion-strips --strip-frames 6
Stills + strips + GLB land in --output. The strips are the
principal-eye ground truth for the session (walk gait alternates, run
travels, dance arms overhead, jump apex airborne, sit ON the bench).
"""
import json
import math
import os
import shutil
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import bpy  # noqa: E402
import rh_canvas  # noqa: E402
import placement_lib as pl  # noqa: E402
from blender_kit import (  # noqa: E402
    common_parser, script_argv, clear_scene, configure_render, render,
    make_material, add_sky_world, print_scene_summary,
)

FIXTURE_ROOT = os.environ.get("RH_FIXTURE_ROOT", "/home/z/rh_fixture_lib")
os.environ.setdefault("RH_CANVAS_LIB", FIXTURE_ROOT)

# clip plan: id -> (display name, world spot, facing deg, platform?)
PLAN = [
    ("9001", "Walk",  (-6.0, 0.0), 90.0,  None),
    ("9006", "Wave",  (-2.0, 0.0), 90.0,  None),
    ("9002", "Run",   (0.0, 0.0),  90.0,  None),   # travels +x
    ("9003", "Dance", (3.0, 0.0),  0.0,   None),
    ("9004", "Jump",  (6.0, 3.0),  0.0,   1.0),    # on a 1 m platform
    ("9005", "Sit",   (-3.0, 4.0), 180.0, "bench"),
    ("9007", "Die",   (5.0, -3.0), 0.0,   None),
]
STATUES = ["Farmer", "Vendor"]


def build_scene():
    clear_scene()
    sc = bpy.context.scene
    add_sky_world()

    # ground
    bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, 0))
    ground = bpy.context.active_object
    ground.name = "Ground"
    ground.data.materials.append(
        make_material("GroundMat", (0.18, 0.20, 0.22), roughness=0.9))

    # the JUMP platform (the elevated_root_motion pairing law: the clip
    # carries the actor up ~1 m — the platform gives it meaning)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(6, 3, 0.5))
    platform = bpy.context.active_object
    platform.name = "JumpPlatform"
    platform.data.materials.append(
        make_material("PlatMat", (0.45, 0.30, 0.14), roughness=0.7))

    # the SIT bench (place_on target for the sitting actor)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(-3, 4, 0.25))
    bench = bpy.context.active_object
    bench.name = "Bench"
    bench.scale = (1.6, 0.5, 0.5)
    bench.data.materials.append(
        make_material("BenchMat", (0.55, 0.38, 0.20), roughness=0.6))

    # lights
    bpy.ops.object.light_add(type='SUN', location=(4, -6, 8))
    sun = bpy.context.active_object
    sun.name = "KeySun"
    sun.data.energy = 3.0
    sun.rotation_euler = (math.radians(50), 0, math.radians(30))
    bpy.ops.object.light_add(type='AREA', location=(-5, -8, 5))
    fill = bpy.context.active_object
    fill.name = "Fill"
    fill.data.energy = 300
    fill.data.size = 8

    # cameras (3 angles + a 3/4)
    cams = {}
    for name, loc, rot, target in [
        # s22 v2 reframe: the hero zone (x 10-13) extended the stage
        # east — the wide cam pulls back + right to hold all 10 actors
        ("cam_wide", (4.5, -16.5, 6.0), None, (4.5, 0, 1.0)),
        ("cam_front", (0, -8, 1.7), None, (0, 0, 1.3)),
        ("cam_side", (12, 1, 1.8), None, (0, 0, 1.2)),
    ]:
        cam_data = bpy.data.cameras.new(name)
        cam_data.lens = 35
        cam = bpy.data.objects.new(name, cam_data)
        sc.collection.objects.link(cam)
        cam.location = loc
        # aim at target
        d = (target[0] - loc[0], target[1] - loc[1], target[2] - loc[2])
        import mathutils
        cam.rotation_euler = (mathutils.Vector(d).to_track_quat(
            '-Z', 'Y').to_euler())
        cams[name] = cam

    # AgX crushes previz colors (core principle 13) — the lab's signal
    # IS the 7 per-actor hues: pin Standard (the s20-A2 L-P2 fix)
    try:
        sc.view_settings.view_transform = 'Standard'
    except Exception:
        pass

    ctx = {
        "scene": sc, "cams": cams, "platform": platform, "bench": bench,
        "actors": {}, "statues": {}, "strips": {},
    }
    return ctx


def _assert_hero_bands(name, rows):
    """The A2b P1-1 enforcement: the H5/H6-measured wrapper-scaled
    bands (tests/test_hero_lane.py) — feet floor >= -0.08, gait span
    >= 0.02, lift <= 0.6, hips within [0.5, 1.5]. Raises RuntimeError
    with the measured numbers; returns the verdict string that also
    lands in the world_table + metadata."""
    flat = [z for pair in rows["feet_z"] for z in pair]
    hz = [v for v in rows["hips_z"] if v is not None]
    floor_z, lift_z = min(flat), max(flat)
    span = lift_z - floor_z
    hips_lo, hips_hi = min(hz), max(hz)
    fails = []
    if floor_z < -0.08:
        fails.append(f"feet floor {floor_z:.3f} < -0.08 (underground)")
    if span < 0.02:
        fails.append(f"gait span {span:.3f} < 0.02 (frozen walk)")
    if lift_z > 0.6:
        fails.append(f"feet lift {lift_z:.3f} > 0.6 (launch-off)")
    if not (0.5 <= hips_lo and hips_hi <= 1.5):
        fails.append(f"hips span [{hips_lo:.3f}, {hips_hi:.3f}] outside "
                     f"[0.5, 1.5]")
    if fails:
        raise RuntimeError(
            f"[lab] hero {name} WORLD GATE FAIL: {'; '.join(fails)} — "
            f"the staged walk is broken (wrapper-MPI/staging class)")
    return (f"PASS feet [{floor_z:.3f}, {lift_z:.3f}] hips "
            f"[{hips_lo:.3f}, {hips_hi:.3f}]")


def stage_heroes(ctx):
    """D4: the HERO ZONE — the three-family humanoid showcase.

    H1 HeroUAL   : the UAL mannequin, native Walk_Loop (the wrapper +
                   pool path via the vendored film-lane module).
    H2 HeroQuatM : the Quaternius male, native Walk (the D2 loader).
    H3 HeroQuatF : the Quaternius female with a RETARGETED UAL
                   Walk_Loop (the D3 recipe, proven end-to-end).

    D4a laws: hero records are {arm, body, clip, rep}-shaped and BOUND
    before the union-range lines (they dereference frame_range);
    placement moves the WRAPPER (animated-armature yaws get clobbered
    — the wrapper is the clobber-proof surface); clip labels carry the
    provenance (UAL:Walk_Loop / Quat:Walk / UAL:Walk_Loop->Quat).
    """
    import rig_family_quaternius as assets_quaternius
    import assets_ual_actors as ual
    import rig_retarget

    heroes = {}

    # H1: UAL mannequin, native pool walk
    u = ual._import_actor("Girl", ual.ACTOR_SCALE)
    u["armature"].name = "HeroUAL.Rig"
    # the A2b slot law: ONE canonical assignment helper (the inline
    # `if slots:` copies were the fail-open class)
    rig_retarget._assign_action(u["armature"], u["actions"]["Walk_Loop"])
    u["root"].location = (10.0, -2.0, 0.0)
    heroes["HeroUAL"] = {"arm": u["armature"], "body": u["mesh"],
                         "clip": "UAL:Walk_Loop", "rep": u,
                         "wrapper": u["root"]}

    # H2: Quaternius male, native walk
    qm = assets_quaternius.load("male", "HeroQuatM")
    rig_retarget._assign_action(qm["arm"], qm["pool"]["Walk"])
    qm["root"].location = (10.0, 1.5, 0.0)
    heroes["HeroQuatM"] = {"arm": qm["arm"], "body": qm["mesh"],
                           "clip": "Quat:Walk", "rep": qm,
                           "wrapper": qm["root"]}

    # H3: Quaternius female with the RETARGETED UAL walk (the door,
    # not the wall — the any-rig recipe proven in-scene)
    qf = assets_quaternius.load("female", "HeroQuatF")
    rt = rig_retarget.retarget(u["armature"],
                               u["actions"]["Walk_Loop"],
                               qf["arm"])
    rig_retarget._assign_action(qf["arm"], rt["action"])
    rt["action"].use_fake_user = True     # the D5a one-process law
    qf["root"].location = (13.0, -0.2, 0.0)
    heroes["HeroQuatF"] = {"arm": qf["arm"], "body": qf["mesh"],
                           "clip": "UAL:Walk_Loop->Quat", "rep": qf,
                           "wrapper": qf["root"], "retarget": rt}
    print(f"[lab] retarget: coverage={rt['coverage']} ratio={rt['ratio']} "
          f"no_target={len(rt['no_target'])} "
          f"drives={rt['gates']['drives_ok']}", flush=True)

    # recolor the two quaternius heroes (identity at a glance)
    assets_quaternius.recolor(qm, (0.20, 0.50, 0.85))
    assets_quaternius.recolor(qf, (0.80, 0.35, 0.60))

    # numeric tables (the two-column law: the numbers travel WITH the
    # strips) — per-hero world-z behavior gates, post-staging. The A2b
    # P1-1 law: the gates are ENFORCED here, not just printed — the
    # engine printed a green lab while a staged walk went underground.
    for name, rec in heroes.items():
        act = rec["arm"].animation_data.action
        rows = rig_retarget.run_world_gates(rec["arm"], act,
                                            sample_stride=4)
        flat = [z for pair in rows["feet_z"] for z in pair]
        hz = [v for v in rows["hips_z"] if v is not None]
        print(f"[lab] hero {name} ({rec['clip']}): feet "
              f"{min(flat):.3f}..{max(flat):.3f} m, hips "
              f"{min(hz):.3f}..{max(hz):.3f} m", flush=True)
        rows["gate_verdict"] = _assert_hero_bands(name, rows)
        rec["world_table"] = rows
        # the gate verdict travels into the metadata (A2b P1-1)

    ctx["heroes"] = heroes
    # the union range covers the heroes too (D4a: bound BEFORE the
    # union lines — stage_heroes runs before stage_actors' union)
    for name, rec in heroes.items():
        ctx["actors"][name] = rec
    return ctx


def stage_actors(ctx):
    """Import clips -> mannequins -> placement (armature-first)."""
    sc = ctx["scene"]
    for cid, disp, (x, y), face_deg, support in PLAN:
        arm, rep = rh_canvas.import_clip(cid, name=f"Actor_{disp}")
        body, mrep = rh_canvas.build_mannequin(arm, f"Body_{disp}")
        # per-actor material tint (color-from-schema law: the manifest
        # carries no color — the lab assigns a stable per-actor hue)
        hues = {"Walk": (0.85, 0.30, 0.20), "Wave": (0.85, 0.60, 0.15),
                "Run": (0.20, 0.55, 0.85), "Dance": (0.70, 0.25, 0.70),
                "Jump": (0.20, 0.65, 0.35), "Sit": (0.85, 0.45, 0.55),
                "Die": (0.45, 0.45, 0.48)}
        body.data.materials.append(
            make_material(f"Mat_{disp}", hues.get(disp, (0.7, 0.7, 0.7)),
                          roughness=0.6))
        # FACING (filed F-RH3): the imported action carries OBJECT-level
        # rotation channels — a manual armature yaw is clobbered at the
        # next frame_set/rebase (probe-verified). The kit recipe for
        # facing animated actors = the UAL wrapper-empty pattern (parent
        # to an empty, yaw the wrapper; keys ride armature-local space).
        # The lab v1 ships natural facing; the wrapper pattern lands in
        # the next iteration with the usability wave.
        if support == "bench":
            # seat via the solver (the ARMATURE place_on branch). The
            # anchor law: a pose can offset the body from its origin
            # (the sit clip leans the bbox +Y of the origin) — anchor
            # the move on the BBOX BOTTOM-CENTER (what place_on's
            # raycasts actually sample), then let the solver seat z.
            pl.move_to(arm, (x, y, 0.0), reference="bottom-center",
                       override="keyframe")
            rep_seat = pl.place_on(arm, ctx["bench"],
                                   footprint='grid',
                                   override='keyframe')
            print(f"[lab] {disp} seat: z={arm.matrix_world.translation.z:.3f}")
        elif support:  # numeric platform height
            pl.move_to(arm, (x, y, support), reference="bottom-center",
                       override="keyframe")
        else:
            pl.move_to(arm, (x, y, 0.0), reference="bottom-center",
                       override="keyframe")
        ctx["actors"][disp] = {"arm": arm, "body": body,
                               "clip": cid, "rep": rep}
        # per-actor union range contribution
    # statues (set dressing, armature-free)
    for sname in STATUES:
        try:
            objs, srep = rh_canvas.import_statue(sname)
            spot = (-5.0, -4.0) if sname == "Farmer" else (2.0, -5.0)
            for o in objs:
                if o.parent is None:
                    o.location.x += spot[0]
                    o.location.y += spot[1]
            ctx["statues"][sname] = objs
        except rh_canvas.RHRefused as e:
            print(f"[lab] statue {sname} refused: {e}")
    sc.render.fps = 30
    return ctx


def set_union_range(ctx):
    """Union scene range (the multi-actor recipe law) — computed AFTER
    both stagings so the hero records are bound before the range lines
    (the D4a law)."""
    sc = ctx["scene"]
    # the A2b P3-1 law: floor/ceil the range ENDS — int() truncation
    # silently dropped the tail frame of a fractional range (24fps
    # glTF: 61.958 -> 61)
    lo = min(math.floor(a["arm"].animation_data.action.frame_range[0])
             for a in ctx["actors"].values())
    hi = max(math.ceil(a["arm"].animation_data.action.frame_range[1])
             for a in ctx["actors"].values())
    sc.frame_start, sc.frame_end = lo, hi
    print(f"[lab] union range: [{lo}, {hi}] over "
          f"{len(ctx['actors'])} actors", flush=True)


def render_motion_strips(ctx, out_dir, n=6, engine='WORKBENCH'):
    """Per-actor motion strips: n cells across the actor's OWN clip
    range (the vision-native animation check — one image per actor)."""
    from blender_kit import normalize_engine_id
    from mathutils import Vector
    sc = ctx["scene"]
    eng = normalize_engine_id(engine)
    sc.render.engine = eng
    if eng in ('BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT'):
        try:
            sc.eevee.taa_render_samples = 8
        except Exception:
            pass
    sc.render.resolution_x = 480
    sc.render.resolution_y = 360
    sc.render.image_settings.file_format = 'PNG'
    cam = ctx["cams"]["cam_front"]
    sc.camera = cam
    # probe-safe: no timeline markers exist in this scene (law kept)
    import tempfile
    try:
        from PIL import Image
    except ImportError:
        print("[lab] Pillow missing — strips skipped (install.sh)")
        return {}
    strips = {}
    import mathutils
    for disp, rec in ctx["actors"].items():
        arm = rec["arm"]
        f0, f1 = [int(v) for v in
                  arm.animation_data.action.frame_range]
        frames = [round(f0 + (f1 - f0) * i / (n - 1)) for i in range(n)]
        # per-actor closeup camera (the strip verifies THIS actor — the
        # wide/front cams cannot frame a 7-actor stage at gait detail).
        # s20-A2 L-P4: traveling actors (run) leave the frame-1-framed
        # camera — frame the AABB UNION across the sampled frames.
        sc.frame_set(sc.frame_start)
        bpy.context.view_layer.update()
        frames_probe = [round(f0 + (f1 - f0) * i / max(1, n - 1))
                        for i in range(n)]
        lo = hi = None
        for f in frames_probe:
            sc.frame_set(f)
            bpy.context.view_layer.update()
            a, b = pl._aabb(arm)
            lo = (Vector((a.x, a.y, a.z)) if lo is None
                  else Vector((min(lo.x, a.x), min(lo.y, a.y),
                               min(lo.z, a.z))))
            hi = (Vector((b.x, b.y, b.z)) if hi is None
                  else Vector((max(hi.x, b.x), max(hi.y, b.y),
                               max(hi.z, b.z))))
        mn, mx = lo, hi
        ctr = (mn + mx) * 0.5
        span = max(mx.x - mn.x, mx.y - mn.y, mx.z - mn.z)
        cd = bpy.data.cameras.new(f"strip_cam_{disp}")
        cd.lens = 40
        cam2 = bpy.data.objects.new(f"strip_cam_{disp}", cd)
        sc.collection.objects.link(cam2)
        cam2.location = (ctr.x + span * 0.2, ctr.y - max(3.2, span * 2.6),
                         ctr.z + 0.35)
        d = mathutils.Vector((ctr.x, ctr.y, ctr.z)) - cam2.location
        cam2.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
        sc.camera = cam2
        cells = []
        tmpdir = tempfile.mkdtemp(prefix="labstrip_")
        try:
            for i, f in enumerate(frames):
                sc.frame_set(f)
                bpy.context.view_layer.update()
                path = os.path.join(tmpdir, f"cell_{i:02d}.png")
                sc.render.filepath = path
                bpy.ops.render.render(write_still=True)
                cells.append(path)
            # stitch 1 x n with labels
            W, H = Image.open(cells[0]).size
            sheet = Image.new("RGB", (W * n + 4 * (n - 1), H), (18, 18, 18))
            xoff = 0
            for i, p in enumerate(cells):
                im = Image.open(p)
                sheet.paste(im, (xoff, 0))
                xoff += W + 4
            out = os.path.join(out_dir, f"motion_{disp}.png")
            sheet.save(out)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
            # temp-camera residue (SKILL mistake #5): strip cams die here
            bpy.data.objects.remove(cam2, do_unlink=True)
        strips[disp] = {"frames": frames, "path": out}
        print(f"[lab] strip {disp}: frames={frames} -> {out}")
    sc.frame_set(sc.frame_start)
    return strips


def main():
    p = common_parser()
    p.add_argument("--stills", default="wide,front,side",
                   help="comma list: wide|front|side")
    p.add_argument("--motion-strips", action="store_true")
    p.add_argument("--strip-frames", type=int, default=6)
    # (validated >= 2 below: n<=1 would ZeroDivision the stitch)
    p.add_argument("--export-glb", action="store_true")
    args = p.parse_args(script_argv())
    out = args.output
    os.makedirs(out, exist_ok=True)
    scene_name = "motion_lab"

    ctx = build_scene()
    stage_actors(ctx)
    stage_heroes(ctx)
    set_union_range(ctx)
    print_scene_summary(scene_name)

    if args.dry_run:
        print("[lab] dry run: build only")
        return

    strips = {}
    if args.motion_strips:
        if args.strip_frames < 2:
            parser.error("--strip-frames must be >= 2")
        strips = render_motion_strips(ctx, out, n=args.strip_frames)

    # stills (workbench fast path)
    from blender_kit import normalize_engine_id
    sc = ctx["scene"]
    sc.render.engine = normalize_engine_id(args.engine)
    sc.render.resolution_x = 640
    sc.render.resolution_y = 480
    for key in [s.strip() for s in args.stills.split(",") if s.strip()]:
        cam = ctx["cams"].get(f"cam_{key}")
        if cam is None:
            print(f"[lab] unknown still {key!r} (wide|front|side)")
            continue
        sc.camera = cam
        sc.frame_set(sc.frame_start + (sc.frame_end - sc.frame_start) // 2)
        path = os.path.join(out, f"still_{key}.png")
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        print(f"[lab] still {key} -> {path}")

    if args.export_glb:
        glb = os.path.join(out, "motion_lab.glb")
        bpy.ops.export_scene.gltf(filepath=glb, export_format='GLB')
        print(f"[lab] GLB -> {glb} ({os.path.getsize(glb)//1024} KB)")

    meta = {
        "scene": scene_name,
        "actors": {k: v["clip"] for k, v in ctx["actors"].items()},
        "statues": list(ctx["statues"]), "strips": strips,
        "frame_range": [sc.frame_start, sc.frame_end],
        "fps": 30,
        # the viewer contract (viewer/index.html reads these)
        "engine": args.engine, "resolution": [sc.render.resolution_x,
                                              sc.render.resolution_y],
        "samples": getattr(args, "samples", 0),
        "camera": "multi", "camera_lens_mm": 35,
        "objects": len(bpy.data.objects),
        "blender_version": bpy.app.version_string,
    }
    with open(os.path.join(out, "metadata.json"), "w") as f:
        json.dump(meta, f, indent=1)


if __name__ == "__main__":
    main()
