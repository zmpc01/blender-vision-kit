"""
scene_corpus.py -- Blender corpus stills + per-still ground-truth export for
the ASCII-vision experiment (experiments/ascii_vision/SPEC.md, "Blender
corpus"). Task 2-b build.

Renders 6 deterministic 640x360 stills from one controlled street layout
(BLENDER_WORKBENCH, MATERIAL color type, ~0.5 s/frame) and exports one
<still>.truth.json per still via camera projection (logic in
scripts/ground_truth_export.py, imported -- same Blender session, exported
right after each render).

Usage (ALWAYS via ./run.sh from the repo root):
    ./run.sh --background --python scripts/scene_corpus.py -- \\
        --output experiments/ascii_vision/corpus/blender --still all \\
        [--w 640 --h 360] [--seed 7]

    # single still / subset:
    ... --still C1            # or C1_wide, or comma list "C1,C4"

CLI of ground_truth_export.py --truth-only rebuilds layout + re-exports
truth JSONs without rendering.

Still inventory (names matter to the battery):
  C1_wide     street: flat gray ground, 2 gray building blocks left/right,
              khaki box jeep with tube-cage suggestion, 3 capsule actors
              BLUE/RED/AMBER on/around the jeep, 15 green zombies scattered
              ahead (+Y) and behind (-Y). Horde hidden.
  C2_closeup  AMBER gunner (standing in jeep bed) fills ~60% of frame
              height; rifle = dark box held at chest.
  C3_top      orthographic top view of the same layout (ortho_scale 40).
  C4_planted  planted-bug shot: blue2 floats 0.30 m above ground; amber1 is
              sunk 0.42 m into the jeep body (~25% of the 1.70 m actor).
  C5_dusk     same layout/camera as C1, but dusk-dim material set (near-
              monochrome dark albedos) + FLAT workbench light + near-black
              world. Deterministic low-contrast trap (S7 analogue).
  C6_tiny     horde of 40 zombies at y~45-52.5, camera 58-66 m away, 20 mm
              lens -> each horde zombie ~1.8-1.9% of frame height (<2%).
              Near zombies hidden; jeep/actors give foreground scale.

Conventions (mirrored into metadata.json "conventions"):
  - Actors: bmesh capsule body (r=0.21, depth=1.0) + sphere head (r=0.15),
    ORIGIN AT FEET (group bbox bottom = feet z); total height ~1.68 m
    (human ~1.7 m). Parts are flat top-level objects (no root empty -- these
    are static stills); truth groups union the parts' world bboxes.
  - Zombies: single capsule each (r=0.22, depth=0.7 -> 1.14 m), green-gray;
    red eyes omitted deliberately (sub-pixel at 640x360, and they would
    pollute the RED count class). Documented deviation from DEFAULT_VOCAB.
  - Ground plane + road strip = scene background, excluded from truth
    objects (like the synthetic corpus); buildings ARE tracked (GRAY).
  - No lamp objects: Workbench STUDIO/FLAT light modes are scene-independent
    -> fully deterministic lighting. Workbench render 'light' enum here is
    STUDIO/MATCAP/FLAT (VIEWPOINT/SCENE not available in 4.5.13 renders).
  - Zombie scatter is seeded (random.Random(seed), default 7).
  - The kit's `primitive_capsule_add` does NOT exist in Blender 4.5.13 ->
    capsules are built via bmesh (cone + 2 spheres in one mesh).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import time
from collections import OrderedDict

import bpy
import bmesh
from mathutils import Matrix, Vector

from blender_kit import clear_scene, make_material, script_argv
import ground_truth_export as gt

# ---------------------------------------------------------------------------
# Palette (matches scripts/vlm_critique.py DEFAULT_VOCAB color classes)
# ---------------------------------------------------------------------------
COLORS = {
    "street":   (0.32, 0.32, 0.33),
    "road":     (0.24, 0.24, 0.25),
    "building": (0.45, 0.45, 0.47),
    "khaki":    (0.56, 0.52, 0.34),
    "dark":     (0.10, 0.10, 0.11),
    "BLUE":     (0.16, 0.30, 0.72),
    "RED":      (0.75, 0.14, 0.14),
    "AMBER":    (0.85, 0.52, 0.10),
    "zombie":   (0.30, 0.38, 0.26),
}
WORLD_NORMAL = (0.45, 0.45, 0.50)     # flat light-gray world (gotcha 35)
WORLD_DUSK = (0.012, 0.013, 0.016)    # near-black dusk world

ALL_STILLS = ["C1_wide", "C2_closeup", "C3_top", "C4_planted", "C5_dusk", "C6_tiny"]

# Actor/zombie body metrics (meters, origin at feet)
ACTOR_R, ACTOR_DEPTH, HEAD_R = 0.21, 1.0, 0.15     # body capsule, head sphere
ZED_R, ZED_DEPTH = 0.22, 0.70                      # zombie capsule -> 1.14 m
AMBER_SINK = 0.42                                  # C4 planted-bug sink depth


def dusk_color(c):
    """Near-monochrome dark variant of a color for the C5_dusk material set."""
    luma = 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    g = 0.015 + luma * 0.22
    return (min(1.0, g * 0.92), min(1.0, g * 0.98), min(1.0, g * 1.10))


# ---------------------------------------------------------------------------
# Primitive helpers (bmesh -- primitive_capsule_add does not exist in 4.5.13)
# ---------------------------------------------------------------------------

def _finish_bm(bm, name, mat, location, rotation=None, scale=None, smooth=True):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if smooth:
        for poly in me.polygons:
            poly.use_smooth = True
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    if rotation is not None:
        obj.rotation_euler = rotation
    if scale is not None:
        obj.scale = scale
    if mat is not None:
        obj.data.materials.append(mat)
    return obj


def make_box(name, size, location, mat):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    return _finish_bm(bm, name, mat, location, scale=size, smooth=False)


def make_cyl(name, radius, depth, location, mat, rotation=None, segments=24):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=segments,
                          radius1=radius, radius2=radius, depth=depth)
    return _finish_bm(bm, name, mat, location, rotation=rotation)


def make_sphere(name, radius, location, mat, segments=24, rings=12):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=radius)
    return _finish_bm(bm, name, mat, location)


def make_capsule(name, radius, depth, location, mat, segments=24, rings=12):
    """True capsule (cylinder + hemisphere ends) as ONE mesh, centered at
    location; total height = depth + 2*radius."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=segments,
                          radius1=radius, radius2=radius, depth=depth)
    for z in (depth / 2.0, -depth / 2.0):
        bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings,
                                  radius=radius, matrix=Matrix.Translation((0, 0, z)))
    return _finish_bm(bm, name, mat, location)


def add_camera(name, loc, look_at=None, lens=50.0, ortho_scale=None, rotation=None):
    cam_data = bpy.data.cameras.new(name)
    cam = bpy.data.objects.new(name, cam_data)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = loc
    if ortho_scale is not None:
        cam_data.type = 'ORTHO'
        cam_data.ortho_scale = ortho_scale
    if rotation is not None:
        cam.rotation_euler = rotation
    elif look_at is not None:
        d = Vector(look_at) - Vector(loc)
        cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    cam_data.lens = lens
    return cam


# ---------------------------------------------------------------------------
# Layout build
# ---------------------------------------------------------------------------

def build_layout(seed: int = 7) -> dict:
    clear_scene()
    scene = bpy.context.scene
    rng = random.Random(seed)

    mats, tracked = OrderedDict(), OrderedDict()

    def reg_mat(key):
        mats[key] = make_material(f"mat_{key}", COLORS[key], roughness=0.6)

    for key in COLORS:
        reg_mat(key)

    # --- street (background: NOT tracked in truth) -------------------------
    make_box("street_plane", (240, 240, 0.1), (0, 0, -0.05), mats["street"])
    make_box("road_strip", (7, 80, 0.04), (0, 4, 0.0), mats["road"])

    # --- buildings (tracked, GRAY) -----------------------------------------
    bldg_parts = []
    bldg_parts.append(make_box("bldg_left_body", (5, 14, 9), (-7.5, 1.0, 4.5), mats["building"]))
    bldg_parts.append(make_box("bldg_right_body", (5, 12, 11), (7.5, -1.5, 5.5), mats["building"]))
    tracked["bldg_left"] = {"parts": bldg_parts[:1], "class": "GRAY",
                            "count_group": "environment"}
    tracked["bldg_right"] = {"parts": bldg_parts[1:], "class": "GRAY",
                             "count_group": "environment"}

    # --- jeep (tracked as group "jeep1", KHAKI) ----------------------------
    jeep_parts = []
    jeep_parts.append(make_box("jeep1_body", (1.7, 3.4, 0.7), (0, 0.1, 0.70), mats["khaki"]))
    jeep_parts.append(make_box("jeep1_hood", (1.6, 1.1, 0.35), (0, -1.55, 0.775), mats["khaki"]))
    for i, (wx, wy) in enumerate([(-0.85, -1.35), (0.85, -1.35), (-0.85, 1.35), (0.85, 1.35)]):
        jeep_parts.append(make_cyl(f"jeep1_wheel_{i}", 0.36, 0.22, (wx, wy, 0.36),
                                   mats["dark"], rotation=(0, math.pi / 2, 0)))
    # tube-cage suggestion: 4 posts + 2 side rails + 1 crossbar
    for i, (px, py) in enumerate([(-0.75, -1.5), (0.75, -1.5), (-0.75, 1.7), (0.75, 1.7)]):
        jeep_parts.append(make_cyl(f"jeep1_cagepost_{i}", 0.035, 1.25, (px, py, 1.675),
                                   mats["dark"]))
    for i, bx in enumerate((-0.75, 0.75)):
        jeep_parts.append(make_cyl(f"jeep1_cagerail_{i}", 0.035, 3.4, (bx, 0.1, 2.30),
                                   mats["dark"], rotation=(math.pi / 2, 0, 0)))
    jeep_parts.append(make_cyl("jeep1_cagecross_0", 0.035, 1.56, (0, 0.1, 2.30),
                               mats["dark"], rotation=(0, math.pi / 2, 0)))
    tracked["jeep1"] = {"parts": jeep_parts, "class": "KHAKI", "count_group": "main",
                        "note": "khaki box jeep; cage/wheels are DARK sub-parts"}

    # --- capsule actors (BLUE/RED/AMBER; body capsule + sphere head) -------
    def make_actor(oid, class_key, x, y, feet_z):
        parts = [
            make_capsule(f"{oid}_body", ACTOR_R, ACTOR_DEPTH,
                         (x, y, feet_z + ACTOR_DEPTH / 2 + ACTOR_R), mats[class_key]),
            make_sphere(f"{oid}_head", HEAD_R,
                        (x, y, feet_z + ACTOR_DEPTH + 2 * ACTOR_R - 0.04 + HEAD_R),
                        mats[class_key]),
        ]
        tracked[oid] = {"parts": parts, "class": class_key, "count_group": "main",
                        "note": f"capsule actor, origin/feet at z={feet_z:.2f}, "
                                f"height ~1.68 m"}
        return parts

    make_actor("blue1", "BLUE", -1.5, -1.2, 0.0)    # driver, beside jeep
    make_actor("red1", "RED", 1.5, 0.6, 0.0)        # passenger, beside jeep
    amber_parts = make_actor("amber1", "AMBER", 0.0, 0.9, 1.05)  # gunner in bed

    # rifle = dark box held by amber1 (rear just past capsule surface)
    rifle = make_box("rifle1_body", (0.07, 0.75, 0.09), (0.0, 1.495, 2.18), mats["dark"])
    tracked["rifle1"] = {"parts": [rifle], "class": "DARK", "count_group": "main",
                         "note": "rifle held by amber1 (no volume intersection)"}

    # --- blue2: planted floating actor, only visible in C4_planted ---------
    blue2_parts = make_actor("blue2", "BLUE", 2.8, 3.5, 0.30)
    tracked["blue2"]["note"] = ("planted bug actor: feet at z=0.30 (floats 0.30 m "
                                "above street); visible only in C4_planted")

    # --- 15 near zombies (ahead +Y / behind -Y), tracked GREEN --------------
    for i in range(15):
        ahead = i < 9
        x = rng.uniform(-4.5, 4.5) if ahead else rng.uniform(-4.0, 4.0)
        y = rng.uniform(4.0, 11.0) if ahead else rng.uniform(-7.5, -4.0)
        body = make_capsule(f"zed{i + 1:02d}_body", ZED_R, ZED_DEPTH, (x, y, ZED_DEPTH / 2 + ZED_R),
                            mats["zombie"])
        tracked[f"zed{i + 1:02d}"] = {"parts": [body], "class": "GREEN",
                                      "count_group": "zombies_near"}

    # --- 40 horde zombies far away (visible only in C6_tiny) ----------------
    for i in range(40):
        x = rng.uniform(-7.0, 7.0)
        y = rng.uniform(45.0, 52.5)
        body = make_capsule(f"horde{i + 1:02d}_body", ZED_R, ZED_DEPTH, (x, y, ZED_DEPTH / 2 + ZED_R),
                            mats["zombie"])
        tracked[f"horde{i + 1:02d}"] = {"parts": [body], "class": "GREEN",
                                        "count_group": "zombies_horde"}

    # --- per-still visibility ----------------------------------------------
    for oid, entry in tracked.items():
        if oid.startswith("horde"):
            entry["visible_in"] = ("C6_tiny",)
        elif oid == "blue2":
            entry["visible_in"] = ("C4_planted",)
        else:
            entry["visible_in"] = tuple(ALL_STILLS)
        for p in entry["parts"]:
            p.hide_render = False

    # --- dusk material variants + worlds ------------------------------------
    dusk_of = {}
    for key, mat in mats.items():
        dmat = make_material(f"mat_dusk_{key}", dusk_color(COLORS[key]), roughness=0.6)
        dusk_of[key] = dmat

    world_normal = bpy.data.worlds.new("WorldNormal")
    world_normal.use_nodes = False
    world_normal.color = WORLD_NORMAL
    world_dusk = bpy.data.worlds.new("WorldDusk")
    world_dusk.use_nodes = False
    world_dusk.color = WORLD_DUSK
    scene.world = world_normal

    # --- cameras (one per still) --------------------------------------------
    cams = OrderedDict()
    cams["C1_wide"] = add_camera("CAM_C1_wide", (4.5, -9.5, 2.8),
                                 look_at=(0, 0.8, 1.1), lens=35)
    cams["C2_closeup"] = add_camera("CAM_C2_closeup", (2.5, -5.5, 2.2),
                                    look_at=(0, 0.9, 2.1), lens=50)
    cams["C3_top"] = add_camera("CAM_C3_top", (0, 0.5, 30), lens=50,
                                ortho_scale=40.0, rotation=(0, 0, 0))
    cams["C4_planted"] = add_camera("CAM_C4_planted", (5.0, -8.5, 3.0),
                                    look_at=(0.5, 1.2, 1.2), lens=35)
    cams["C5_dusk"] = add_camera("CAM_C5_dusk", (4.5, -9.5, 2.8),
                                 look_at=(0, 0.8, 1.1), lens=35)
    cams["C6_tiny"] = add_camera("CAM_C6_tiny", (0, -13, 1.6),
                                 look_at=(0, 46, 0.8), lens=20)

    bpy.context.view_layer.update()

    return {
        "scene": scene, "mats": mats, "dusk_of": dusk_of,
        "tracked": tracked, "cams": cams,
        "world_normal": world_normal, "world_dusk": world_dusk,
        "amber_parts": amber_parts, "amber_base_feet_z": 1.05,
        "mat_map": [(obj, obj.data.materials[0]) for oid in tracked
                    for obj in tracked[oid]["parts"]]
        + [(obj, obj.data.materials[0]) for obj in
           bpy.data.objects if obj.name.startswith(("street_", "road_"))],
    }


# ---------------------------------------------------------------------------
# Material / lighting modes
# ---------------------------------------------------------------------------

def apply_material_mode(ctx, mode: str) -> None:
    """Swap normal <-> dusk-dim material set + world + workbench light."""
    scene = ctx["scene"]
    dusk = (mode == "dusk")
    for obj, normal_mat in ctx["mat_map"]:
        key = normal_mat.name.removeprefix("mat_")
        obj.data.materials[0] = ctx["dusk_of"][key] if dusk else normal_mat
    scene.world = ctx["world_dusk"] if dusk else ctx["world_normal"]
    sh = scene.display.shading
    sh.light = 'FLAT' if dusk else 'STUDIO'
    sh.show_shadows = not dusk
    if not dusk:
        sh.shadow_intensity = 0.35
    sh.show_cavity = not dusk


# ---------------------------------------------------------------------------
# Render configuration (workbench, MATERIAL colors, Standard view transform)
# ---------------------------------------------------------------------------

def configure_workbench(scene, w: int, h: int) -> None:
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.render.resolution_x = w
    scene.render.resolution_y = h
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.display.render_aa = '5'
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    scene.frame_start = scene.frame_end = 1
    scene.frame_set(1)
    sh = scene.display.shading
    sh.color_type = 'MATERIAL'   # gotcha 22: else everything renders gray


# ---------------------------------------------------------------------------
# Stills
# ---------------------------------------------------------------------------

STILLS = OrderedDict([
    ("C1_wide", dict(
        mats="normal",
        annotations={},
        notes=("wide street: gray ground+road, 2 gray building blocks, khaki jeep "
               "with tube cage, BLUE driver / RED passenger beside jeep, AMBER "
               "gunner standing in jeep bed, 15 green zombies ahead(+Y)+behind(-Y); "
               "horde hidden"))),
    ("C2_closeup", dict(
        mats="normal",
        annotations={},
        notes=("closeup: AMBER gunner (in jeep bed) fills ~>30% of frame height; "
               "rifle = dark box held at chest"))),
    ("C3_top", dict(
        mats="normal",
        annotations={},
        notes=("orthographic top view (ortho_scale 40) of the C1 layout; "
               "+Y (ahead/horde direction) is up"))),
    ("C4_planted", dict(
        mats="normal",
        sink_amber=AMBER_SINK,
        annotations={
            "blue2": {"floating": True,
                      "note": "planted: floats 0.30 m above street"},
            "amber1": {"intersects": ["jeep1"],
                       "note": (f"planted: sunk {AMBER_SINK} m into jeep1 body "
                                f"(~{AMBER_SINK / 1.68:.0%} of 1.68 m actor height)")},
        },
        notes=("planted-bug shot: blue2 floats 0.30 m above ground; amber1 sunk "
               f"{AMBER_SINK} m into the jeep body (~25% of actor height)"))),
    ("C5_dusk", dict(
        mats="dusk",
        annotations={},
        notes=("dusk variant of C1: identical layout+camera, dusk-dim near-"
               "monochrome material set, FLAT workbench light, near-black world "
               "(deterministic low-contrast trap)"))),
    ("C6_tiny", dict(
        mats="normal",
        annotations={},
        notes=("tiny horde: 40 zombies at y 45-52.5 seen from ~58-66 m with a "
               "20 mm lens -> each <2% of frame height; near zombies hidden, "
               "jeep+actors give foreground scale"))),
])


def resolve_stills(token: str) -> list[str]:
    token = (token or "all").strip()
    if token.lower() == "all":
        return list(ALL_STILLS)
    out = []
    for part in token.split(","):
        part = part.strip()
        match = [s for s in ALL_STILLS if s == part or s.split("_")[0] == part
                 or s.startswith(part)]
        if not match:
            raise SystemExit(f"[scene_corpus] unknown --still {part!r} "
                             f"(choose from {ALL_STILLS} or 'all')")
        out.append(match[0])
    return out


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="Blender corpus stills + per-still ground truth "
                    "(ASCII-vision experiment)")
    p.add_argument("--output", required=True,
                   help="output directory (e.g. experiments/ascii_vision/corpus/blender)")
    p.add_argument("--still", default="all", help="C1|C2|...|all or comma list")
    p.add_argument("--w", type=int, default=640)
    p.add_argument("--h", type=int, default=360)
    p.add_argument("--seed", type=int, default=7,
                   help="seed for zombie scatter (deterministic)")
    p.add_argument("--truth-only", action="store_true",
                   help="export truth JSONs only, skip rendering")
    return p.parse_args(script_argv() if argv is None else argv)


def run(args, render: bool = True) -> None:
    t_start = time.time()
    ctx = build_layout(seed=args.seed)
    scene = ctx["scene"]
    configure_workbench(scene, args.w, args.h)
    os.makedirs(args.output, exist_ok=True)
    stills = resolve_stills(args.still)
    print(f"[scene_corpus] layout built: {len(ctx['tracked'])} tracked groups, "
          f"{sum(len(e['parts']) for e in ctx['tracked'].values())} mesh parts, "
          f"stills={stills}, render={render}")

    per_still = OrderedDict()
    for name in stills:
        spec = STILLS[name]
        cam = ctx["cams"][name]

        # per-still visibility
        visible_ids = []
        for oid, entry in ctx["tracked"].items():
            show = name in entry["visible_in"]
            for part in entry["parts"]:
                part.hide_render = not show
            if show:
                visible_ids.append(oid)

        # planted-bug mutation: sink amber1 into the jeep body
        sink = spec.get("sink_amber")
        if sink:
            for part in ctx["amber_parts"]:
                part.location.z -= sink
            bpy.context.view_layer.update()

        apply_material_mode(ctx, spec["mats"])
        scene.camera = cam
        png_path = os.path.join(args.output, f"{name}.png")

        render_s = None
        if render:
            scene.render.filepath = png_path
            t0 = time.time()
            bpy.ops.render.render(write_still=True)
            render_s = round(time.time() - t0, 2)
            size = os.path.getsize(png_path)
            if size < 5000:
                raise RuntimeError(f"[scene_corpus] {name}.png suspiciously small "
                                   f"({size} B) -- render likely failed")
            print(f"[scene_corpus] rendered {name}.png in {render_s}s ({size} B)")

        truth = gt.export_still_truth(
            scene=scene, camera=cam, tracked=ctx["tracked"], visible_ids=visible_ids,
            png_path=png_path if render else None,
            out_path=os.path.join(args.output, f"{name}.truth.json"),
            w=args.w, h=args.h, material_mode=spec["mats"],
            bg_linear=WORLD_DUSK if spec["mats"] == "dusk" else WORLD_NORMAL,
            annotations=spec.get("annotations", {}), still_notes=spec["notes"],
            extra_meta={"seed": args.seed, "render_s": render_s},
        )

        if sink:  # restore amber1 AFTER truth export
            for part in ctx["amber_parts"]:
                part.location.z += sink
            bpy.context.view_layer.update()

        per_still[name] = {
            "png": os.path.basename(png_path), "render_s": render_s,
            "truth": f"{name}.truth.json",
            "n_objects": len(truth["objects"]),
            "counts": truth["counts"],
        }

    meta = {
        "scene": "scene_corpus",
        "purpose": "ASCII-vision Blender corpus (SPEC.md 'Blender corpus')",
        "blender_version": bpy.app.version_string,
        "engine": "BLENDER_WORKBENCH",
        "view_transform": "Standard",
        "resolution": [args.w, args.h],
        "seed": args.seed,
        "rendered": render,
        "total_s": round(time.time() - t_start, 2),
        "stills": per_still,
        "conventions": {
            "actors": ("capsule body r=0.21 depth=1.0 + sphere head r=0.15, "
                       "origin at feet, height ~1.68 m; flat parts, truth = "
                       "union of part world bboxes"),
            "zombies": ("single capsule r=0.22 depth=0.7 (1.14 m), green-gray; "
                        "red eyes omitted (sub-pixel at 640x360, keeps RED "
                        "count class clean)"),
            "background": "street plane + road strip excluded from truth objects",
            "lighting": ("no lamp objects; Workbench STUDIO light (FLAT for "
                         "C5_dusk); render 'light' enum here = STUDIO/MATCAP/FLAT"),
            "capsule_primitive": ("bmesh-built (primitive_capsule_add does not "
                                  "exist in Blender 4.5.13)"),
            "truth_projection": gt.PROJECTION_NOTE,
            "dusk": ("C5_dusk = dark near-monochrome albedo set (g=0.015+0.22*luma) "
                     "+ FLAT light + world (0.012,0.013,0.016); swapped per still"),
        },
        "object_inventory": {
            oid: {"class": e["class"], "count_group": e["count_group"],
                  "n_parts": len(e["parts"]),
                  "visible_in": list(e["visible_in"])}
            for oid, e in ctx["tracked"].items()
        },
    }
    meta_path = os.path.join(args.output, "metadata.json")
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)
    print(f"[scene_corpus] metadata.json written; total {meta['total_s']}s")


def main() -> None:
    args = parse_args()
    run(args, render=not args.truth_only)


if __name__ == "__main__":
    main()
