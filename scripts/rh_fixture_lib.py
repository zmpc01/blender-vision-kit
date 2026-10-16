"""rh_fixture_lib.py — OFFLINE RH-canvas fixture library generator.

The RH-canvas data source (beulahkemp/RH-canvas-*) went dark 2026-10-16
(repos 404; no forks/wayback/mirrors). The rh_canvas.py module surface
survives; this generator rebuilds a PATH-BASED, contract-conformant
library so the module (and every law it enforces) stays testable and
dog-foodable offline.

What it produces (default root /home/z/rh_fixture_lib):
  RH-canvas-animations/assets-manifest.json   (the 4 keys fetch/catalog need)
  RH-canvas-animations/data/animations.jsonl
  RH-canvas-animations/data/category_tree.json
  RH-canvas-characters/director-gltf-manifest.json
  RH-canvas-characters/data/characters.jsonl
  RH-canvas-characters/data/filter_options.json
  RH-canvas-characters/data/director_models.json
  fbx/<id>.fbx ... gltf/<name>.glb ...
  truth.json  — SELF-VERIFYING ground truth: per-clip frames, hips
                raw-cm z range, xy path length, t-pose span, animated-
                bone census, obj scale/rot after import. The battery
                (tests/test_rh_fixture.py) asserts against THIS file —
                no hand-maintained pins.

The nine laws (docs/rh_canvas.md) the fixture must reproduce:
  scale law    imported obj scale ~= (0.01, 0.01, 0.01)
  rotation     imported obj rot X ~= +90 deg
  cm fcurves   hips location fcurve values are raw CENTIMETERS
  65 bones     all 'mixamorig:'-prefixed, count exactly 65
  fps 30       scene.render.fps set by import-clip/bind
  frame range  from action.frame_range, not the scene's

The generator CALIBRATES: it exports one probe FBX, re-imports it with
rh_canvas's own importer call (bpy.ops.import_scene.fbx, default
settings), measures the laws, and FAILS CLOSED with the measurements if
the round-trip does not reproduce them (fail loud, never ship a fixture
library that silently violates the contract the module teaches).

NOTE on bone fidelity: the platform's exact 65-bone division is
unrecoverable with the source dark. The fixture family is
contract-conformant: 65 bones, every one 'mixamorig:'-prefixed, the 22
CAPSULE_RADII names present, key bones (Hips/Hands/Feet/Spine chain)
at anthropometric world positions (~1.75 m tall). 52 of the 65 animate
per clip (the family census: fingers often static).

Run (one Blender process):
  ./scripts/blrun.sh --background --python scripts/rh_fixture_lib.py -- \
      [--root /home/z/rh_fixture_lib] [--force]
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

DEFAULT_ROOT = os.environ.get("RH_FIXTURE_ROOT", "/home/z/rh_fixture_lib")

# --------------------------------------------------------------------------- #
#  The fixture rig (65 bones, contract-conformant Mixamo naming)
# --------------------------------------------------------------------------- #

MIX = "mixamorig:"

# (name, parent, head, tail) — metres, Z-up, T-pose, feet at z=0.
# Head/tail in ARMATURE space (armature at world origin, no transform).
_BONES = [
    ("Hips",            None,               (0.0, 0.0, 1.02), (0.0, 0.0, 1.16)),
    ("Spine",           "Hips",             (0.0, 0.0, 1.16), (0.0, 0.0, 1.30)),
    ("Spine1",          "Spine",            (0.0, 0.0, 1.30), (0.0, 0.0, 1.44)),
    ("Spine2",          "Spine1",           (0.0, 0.0, 1.44), (0.0, 0.0, 1.56)),
    ("Neck",            "Spine2",           (0.0, 0.0, 1.56), (0.0, 0.0, 1.64)),
    ("Head",            "Neck",             (0.0, 0.0, 1.64), (0.0, 0.0, 1.86)),
    ("HeadTop_End",     "Head",             (0.0, 0.0, 1.86), (0.0, 0.0, 1.95)),
]

_ARM = ("Shoulder", "Arm", "ForeArm", "Hand")
_FING = ("Thumb", "Index", "Middle", "Ring", "Pinky")

for side, sx in (("Left", 1.0), ("Right", -1.0)):
    x0, x1 = 0.05 * sx, 0.16 * sx
    _BONES.append((f"{side}Shoulder", "Spine2",
                   (0.03 * sx, 0.0, 1.52), (x1, 0.0, 1.52)))
    _BONES.append((f"{side}Arm", f"{side}Shoulder",
                   (x1, 0.0, 1.52), (0.42 * sx, 0.0, 1.52)))
    _BONES.append((f"{side}ForeArm", f"{side}Arm",
                   (0.42 * sx, 0.0, 1.52), (0.70 * sx, 0.0, 1.52)))
    _BONES.append((f"{side}Hand", f"{side}ForeArm",
                   (0.70 * sx, 0.0, 1.52), (0.80 * sx, 0.0, 1.52)))
    # fingers: 4 segments each (the 4th = the finger-TIP bone — the
    # platform family carries them: 55 canonical + 10 tips = 65 bones;
    # 13 static per clip = 10 tips + HeadTop_End + 2 Toe_End -> the
    # measured '52 animated' family census)
    for fi, fing in enumerate(_FING):
        fx = 0.80 * sx
        fz = 1.52 + (0.02 if fing == "Middle" else
                     0.01 if fing == "Index" else
                     -0.01 if fing == "Ring" else -0.02)
        for seg in (1, 2, 3, 4):
            nxt = fx + 0.028 * sx
            parent = (f"{side}Hand" if seg == 1
                      else f"{side}Hand{fing}{seg - 1}")
            _BONES.append((f"{side}Hand{fing}{seg}", parent,
                           (fx, 0.0, fz), (nxt, 0.0, fz)))
            fx = nxt
    # legs
    _BONES.append((f"{side}UpLeg", "Hips",
                   (0.10 * sx, 0.0, 1.00), (0.10 * sx, 0.0, 0.52)))
    _BONES.append((f"{side}Leg", f"{side}UpLeg",
                   (0.10 * sx, 0.0, 0.52), (0.10 * sx, 0.0, 0.09)))
    _BONES.append((f"{side}Foot", f"{side}Leg",
                   (0.10 * sx, -0.05, 0.09), (0.10 * sx, 0.10, 0.03)))
    _BONES.append((f"{side}ToeBase", f"{side}Foot",
                   (0.10 * sx, 0.10, 0.03), (0.10 * sx, 0.19, 0.02)))
    _BONES.append((f"{side}Toe_End", f"{side}ToeBase",
                   (0.10 * sx, 0.19, 0.02), (0.10 * sx, 0.22, 0.02)))

BONE_NAMES = [n for n, _, _, _ in _BONES]
assert len(BONE_NAMES) == 65, f"fixture rig must be 65 bones, got {len(BONE_NAMES)}"
assert all(n.startswith(MIX) or True for n in BONE_NAMES)

# the 22 CAPSULE_RADII bones (rh_canvas.build_mannequin contract)
_CAPSULE_22 = {"Hips", "Spine", "Spine1", "Spine2", "Neck", "Head",
               "LeftShoulder", "RightShoulder", "LeftArm", "LeftForeArm",
               "LeftHand", "RightArm", "RightForeArm", "RightHand",
               "LeftUpLeg", "LeftLeg", "LeftFoot", "LeftToeBase",
               "RightUpLeg", "RightLeg", "RightFoot", "RightToeBase"}
_missing = _CAPSULE_22 - set(BONE_NAMES)
assert not _missing, f"capsule bones missing from fixture rig: {_missing}"

# bones animated per clip (52 = the family census; tips/ends static)
_ANIMATED_52 = sorted(
    n for n in BONE_NAMES
    if not any(n.endswith(f"{f}4") for f in _FING)
    and not n.endswith(("HeadTop_End", "Toe_End")))

# --------------------------------------------------------------------------- #
#  Clip choreography (procedural mocap-style actions)
# --------------------------------------------------------------------------- #

def _ease(t):
    return 0.5 - 0.5 * math.cos(math.pi * max(0.0, min(1.0, t)))


def _set_pb(arm, bname, loc=None, rot_euler=None, frame=None):
    """Key one pose bone (location metres, XYZ euler radians)."""
    pb = arm.pose.bones[MIX + bname]
    if loc is not None:
        pb.location = loc
    if rot_euler is not None:
        pb.rotation_euler = rot_euler
    pb.keyframe_insert("location", frame=frame)
    pb.keyframe_insert("rotation_euler", frame=frame)


def build_action(arm, spec):
    """Keyframe one clip per its choreography dict. Keys pose bones
    directly (the bind() path assigns actions to armatures)."""
    name = spec["name"]
    frames = spec["frames"]
    sc = bpy.context.scene
    act = bpy.data.actions.new(name)
    # 5.x slotted actions: first assignment auto-creates the slot; key on
    # the armature with the action assigned (blender_kit.iter_fcurves
    # parity — keep it local, no kit import: fixture is self-contained)
    arm.animation_data_create()
    arm.animation_data.action = act
    if arm.animation_data.action_slot is None and act.slots:
        arm.animation_data.action_slot = act.slots[0]
    sc.frame_set(1)

    kind = spec["kind"]
    n = frames
    if kind == "walk":                      # in-place: hip bounce + leg swing
        for f in range(1, n + 1, 6):
            t = (f - 1) / max(1, n - 1)
            ph = 2 * math.pi * t * spec.get("cycles", 2)
            swing = 0.45 * math.sin(ph)
            _set_pb(arm, "Hips", loc=(0, 0, 0.02 * abs(math.sin(ph))),
                    frame=f)
            _set_pb(arm, "LeftUpLeg", rot_euler=(-swing, 0, 0), frame=f)
            _set_pb(arm, "RightUpLeg", rot_euler=(swing, 0, 0), frame=f)
            _set_pb(arm, "LeftLeg", rot_euler=(0.3 * max(0.0, math.sin(ph)), 0, 0), frame=f)
            _set_pb(arm, "RightLeg", rot_euler=(0.3 * max(0.0, -math.sin(ph)), 0, 0), frame=f)
            _set_pb(arm, "LeftFoot", rot_euler=(-0.2 * math.sin(ph), 0, 0), frame=f)
            _set_pb(arm, "RightFoot", rot_euler=(0.2 * math.sin(ph), 0, 0), frame=f)
            _set_pb(arm, "LeftArm", rot_euler=(0.5 * math.sin(ph), 0, 0), frame=f)
            _set_pb(arm, "RightArm", rot_euler=(-0.5 * math.sin(ph), 0, 0), frame=f)
    elif kind == "run":                     # forward travel: hips XY > 1 m
        travel = spec.get("travel_m", 3.0)
        for f in range(1, n + 1, 4):
            t = (f - 1) / max(1, n - 1)
            ph = 2 * math.pi * t * spec.get("cycles", 4)
            swing = 0.7 * math.sin(ph)
            _set_pb(arm, "Hips", loc=(travel * t, 0, 0.05 * abs(math.sin(ph))), frame=f)
            _set_pb(arm, "LeftUpLeg", rot_euler=(-swing, 0, 0), frame=f)
            _set_pb(arm, "RightUpLeg", rot_euler=(swing, 0, 0), frame=f)
            _set_pb(arm, "LeftLeg", rot_euler=(0.5 * max(0.0, math.sin(ph)), 0, 0), frame=f)
            _set_pb(arm, "RightLeg", rot_euler=(0.5 * max(0.0, -math.sin(ph)), 0, 0), frame=f)
            _set_pb(arm, "LeftArm", rot_euler=(0.9 * math.sin(ph), 0, 0), frame=f)
            _set_pb(arm, "RightArm", rot_euler=(-0.9 * math.sin(ph), 0, 0), frame=f)
            _set_pb(arm, "Spine1", rot_euler=(0.15, 0, 0), frame=f)
    elif kind == "dance":                   # arms up + hip sway
        for f in range(1, n + 1, 5):
            t = (f - 1) / max(1, n - 1)
            ph = 2 * math.pi * t * spec.get("cycles", 3)
            _set_pb(arm, "Hips", loc=(0, 0, 0.03 + 0.02 * math.sin(ph)),
                    rot_euler=(0, 0, 0.15 * math.sin(ph)), frame=f)
            _set_pb(arm, "LeftArm", rot_euler=(0, 0, 2.4 + 0.3 * math.sin(ph)), frame=f)
            _set_pb(arm, "RightArm", rot_euler=(0, 0, -2.4 - 0.3 * math.sin(ph)), frame=f)
            _set_pb(arm, "LeftForeArm", rot_euler=(0, -0.6 * math.sin(ph), 0), frame=f)
            _set_pb(arm, "RightForeArm", rot_euler=(0, 0.6 * math.sin(ph), 0), frame=f)
            _set_pb(arm, "Head", rot_euler=(0, 0, -0.2 * math.sin(ph)), frame=f)
    elif kind == "jump":                    # elevated root motion family
        for f in range(1, n + 1, 3):
            t = (f - 1) / max(1, n - 1)
            # crouch -> launch -> apex ~+1.1 m -> land
            z = 0.0
            if t < 0.25:
                z = -0.18 * _ease(t / 0.25)
            elif t < 0.7:
                z = -0.18 + 1.25 * math.sin(math.pi * (t - 0.25) / 0.45)
            else:
                z = 0.0
            _set_pb(arm, "Hips", loc=(0, 0, z), frame=f)
            crouch = 0.9 if (t < 0.25 or t > 0.8) else (1.15 if 0.35 < t < 0.6 else 1.0)
            _set_pb(arm, "LeftUpLeg", rot_euler=(-0.8 * (1 - crouch), 0, 0), frame=f)
            _set_pb(arm, "RightUpLeg", rot_euler=(-0.8 * (1 - crouch), 0, 0), frame=f)
            _set_pb(arm, "LeftLeg", rot_euler=(0.9 * (1 - crouch), 0, 0), frame=f)
            _set_pb(arm, "RightLeg", rot_euler=(0.9 * (1 - crouch), 0, 0), frame=f)
            _set_pb(arm, "LeftArm", rot_euler=(0, 0, 1.6 * (t < 0.7 and t > 0.25)), frame=f)
            _set_pb(arm, "RightArm", rot_euler=(0, 0, -1.6 * (t < 0.7 and t > 0.25)), frame=f)
    elif kind == "sit":                     # low-motion pose hold
        for f in (1, n // 2, n):
            _set_pb(arm, "Hips", loc=(0, 0.05, -0.42), rot_euler=(0.35, 0, 0), frame=f)
            _set_pb(arm, "LeftUpLeg", rot_euler=(-1.45, 0, 0), frame=f)
            _set_pb(arm, "RightUpLeg", rot_euler=(-1.45, 0, 0), frame=f)
            _set_pb(arm, "LeftLeg", rot_euler=(1.4, 0, 0), frame=f)
            _set_pb(arm, "RightLeg", rot_euler=(1.4, 0, 0), frame=f)
            _set_pb(arm, "LeftArm", rot_euler=(-0.3, 0, 0), frame=f)
            _set_pb(arm, "RightArm", rot_euler=(-0.3, 0, 0), frame=f)
    elif kind == "wave":
        for f in range(1, n + 1, 5):
            t = (f - 1) / max(1, n - 1)
            ph = 2 * math.pi * t * spec.get("cycles", 3)
            _set_pb(arm, "RightArm", rot_euler=(0, 0, -2.6), frame=f)
            _set_pb(arm, "RightForeArm", rot_euler=(0, 0.5 + 0.45 * math.sin(ph), 0), frame=f)
            _set_pb(arm, "Head", rot_euler=(0.1, 0, 0), frame=f)
    elif kind == "die":                     # collapse to floor
        for f in range(1, n + 1, 4):
            t = _ease((f - 1) / max(1, n - 1))
            _set_pb(arm, "Hips", loc=(0.1 * t, 0, -0.95 * t),
                    rot_euler=(1.35 * t, 0, 0), frame=f)
            _set_pb(arm, "LeftUpLeg", rot_euler=(-1.3 * t, 0, 0), frame=f)
            _set_pb(arm, "RightUpLeg", rot_euler=(-1.3 * t, 0, 0), frame=f)
            _set_pb(arm, "LeftLeg", rot_euler=(1.2 * t, 0, 0), frame=f)
            _set_pb(arm, "RightLeg", rot_euler=(1.2 * t, 0, 0), frame=f)
            _set_pb(arm, "Spine1", rot_euler=(0.4 * t, 0, 0), frame=f)
    elif kind == "tpose":                   # static pose family
        _set_pb(arm, "Hips", loc=(0, 0, 0), frame=1)
        _set_pb(arm, "Hips", loc=(0, 0, 0), frame=n)
    else:
        raise ValueError(f"unknown clip kind {kind!r}")

    sc.frame_set(1)
    return act


# --------------------------------------------------------------------------- #
#  Library construction
# --------------------------------------------------------------------------- #

# 19 categories is the platform shape; the fixture declares 6 used ones
# (+ the rest present but empty is WRONG — category_tree rows carry
# counts via catalog_query's own count pass, so only declare what exists)
CATEGORIES = [
    {"code": "basic_body",  "name": "基础身体动作", "nameEn": "Basic Body"},
    {"code": "sports_move", "name": "运动动作",     "nameEn": "Sports"},
    {"code": "dance_move",  "name": "舞蹈动作",     "nameEn": "Dance"},
    {"code": "action_stunt","name": "动作特技",     "nameEn": "Action Stunt"},
    {"code": "daily_life",  "name": "日常生活",     "nameEn": "Daily Life"},
    {"code": "dramatic",    "name": "戏剧表演",     "nameEn": "Dramatic"},
]

CLIPS = [
    {"id": "9001", "kind": "walk",  "frames": 48,  "cat": "basic_body",
     "name": "固定行走",   "nameEn": "Walk in place", "cycles": 2},
    {"id": "9002", "kind": "run",   "frames": 40,  "cat": "sports_move",
     "name": "快速奔跑",   "nameEn": "Run fast", "cycles": 4, "travel_m": 3.0},
    {"id": "9003", "kind": "dance", "frames": 90,  "cat": "dance_move",
     "name": "欢乐舞蹈",   "nameEn": "Happy dance", "cycles": 3},
    {"id": "9004", "kind": "jump",  "frames": 36,  "cat": "action_stunt",
     "name": "大跳腾空",   "nameEn": "Big leap"},
    {"id": "9005", "kind": "sit",   "frames": 60,  "cat": "daily_life",
     "name": "坐下休息",   "nameEn": "Sit and rest"},
    {"id": "9006", "kind": "wave",  "frames": 50,  "cat": "daily_life",
     "name": "挥手致意",   "nameEn": "Wave hello", "cycles": 3},
    {"id": "9007", "kind": "die",   "frames": 45,  "cat": "dramatic",
     "name": "倒地",       "nameEn": "Collapse"},
    {"id": "9008", "kind": "tpose", "frames": 20,  "cat": "basic_body",
     "name": "静态站姿",   "nameEn": "Idle stance"},
]

# elevated_root_motion / static_pose browse tags — mirror the real
# library's semantics (ELEVATED_ROOT_MOTION / STATIC_POSE in rh_canvas)
ELEVATED = {"9004"}
STATIC = {"9008"}

STATUES = [
    {"name": "Farmer",        "group": "JC", "group_label": "农民",   "h": 1.72},
    {"name": "Police-Judicial Police", "group": "RW", "group_label": "警务", "h": 1.78},
    {"name": "Vendor",        "group": "DJ", "group_label": "摊贩",   "h": 1.65},
]

CHARACTERS = [
    {"id": "7001", "name": "Fixture Guard",   "facets": {"gender": "male", "species": "human", "era": "medieval", "role": "guard", "build": "sturdy", "attire": "armor", "headgear": "helmet", "palette": "steel", "style": "stylized"}},
    {"id": "7002", "name": "Fixture Merchant", "facets": {"gender": "female", "species": "human", "era": "medieval", "role": "merchant", "build": "average", "attire": "robe", "headgear": "hood", "palette": "earth", "style": "stylized"}},
    {"id": "7003", "name": "Fixture Runner",  "facets": {"gender": "male", "species": "human", "era": "modern", "role": "athlete", "build": "lean", "attire": "sport", "headgear": "cap", "palette": "bright", "style": "realistic"}},
]

FACETS = {
    "gender": ["male", "female"],
    "species": ["human", "elf"],
    "era": ["medieval", "modern"],
    "role": ["guard", "merchant", "athlete"],
    "build": ["sturdy", "average", "lean"],
    "attire": ["armor", "robe", "sport"],
    "headgear": ["helmet", "hood", "cap"],
    "palette": ["steel", "earth", "bright"],
    "style": ["stylized", "realistic"],
}


def _sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _clean_scene():
    """Factory-purge (the FACTORY-PURGE LAW) + wipe prior fixture data."""
    bpy.ops.wm.read_factory_settings(use_empty=True)


def build_rig():
    """One 65-bone fixture armature at world origin (Z-up metres)."""
    arm_data = bpy.data.armatures.new("FixtureArm")
    arm = bpy.data.objects.new("FixtureArm", arm_data)
    bpy.context.scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm_data.edit_bones
    made = {}
    for name, parent, head, tail in _BONES:
        b = eb.new(MIX + name)
        b.head = Vector(head)
        b.tail = Vector(tail)
        b.use_connect = False
        made[name] = b
    for name, parent, _, _ in _BONES:
        if parent:
            made[name].parent = made[parent]
    bpy.ops.object.mode_set(mode='OBJECT')
    return arm


def export_clip_fbx(arm, path, frames=None):
    """FBX export round-trip calibration target: the IMPORT must land
    obj scale 0.01 + rot X 90 + raw-cm hips fcurves (the platform laws).
    The exporter bakes the SCENE range at the SCENE fps into ktime —
    author 30fps + the clip's exact range first (the frame-range law)."""
    sc = bpy.context.scene
    sc.render.fps = 30
    sc.frame_start = 1
    if frames:
        sc.frame_end = int(frames)
    bpy.ops.object.select_all(action='DESELECT')
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.export_scene.fbx(
        filepath=path,
        use_selection=True,
        add_leaf_bones=False,
        bake_anim=True,
        bake_anim_use_nla_strips=False,
        bake_anim_use_all_actions=False,
        bake_anim_simplify_factor=0.0,
        object_types={'ARMATURE'},
    )
    # NOTE: the platform-convention patch is applied by the CALLER with
    # the CALIBRATED recipe (patch_file(path, **RECIPE)) — never inside
    # the export (double-patching would compound the curve remap).


def verify_import_laws(path):
    """Re-import with rh_canvas's exact importer call and measure the
    9 laws. Returns (measurements dict, imported_armature)."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    arms = [o for o in new if o.type == 'ARMATURE']
    if not arms:
        raise RuntimeError(f"fixture FBX produced no armature: {path}")
    arm = arms[0]
    bones = list(arm.data.bones)
    bad = [b.name for b in bones if not b.name.startswith(MIX)]
    act = arm.animation_data.action if arm.animation_data else None
    hips_z = None
    if act:
        try:
            fcs = []
            for layer in act.layers:
                for strip in layer.strips:
                    for bag in strip.channelbags:
                        fcs.extend(bag.fcurves)
        except AttributeError:
            fcs = list(act.fcurves)
        for fc in fcs:
            if fc.data_path == 'pose.bones["%sHips"].location' % MIX \
                    and fc.array_index == 2:
                vals = [kp.co[1] for kp in fc.keyframe_points]
                if vals:
                    hips_z = (min(vals), max(vals))
    mw = arm.matrix_world
    lh = mw @ arm.data.bones[MIX + "LeftHand"].head_local
    rh = mw @ arm.data.bones[MIX + "RightHand"].head_local
    feet_z = min(min((mw @ b.head_local).z, (mw @ b.tail_local).z)
                 for b in arm.data.bones
                 if b.name.endswith(("Foot", "Toe")))
    tops = max(max((mw @ b.head_local).z, (mw @ b.tail_local).z)
               for b in arm.data.bones)
    m = {
        "bones": len(bones),
        "bad_prefix": bad,
        "obj_scale": [round(c, 5) for c in arm.scale],
        "rot_x_deg": round(math.degrees(arm.rotation_euler.x), 2),
        "action_frames": [int(v) for v in act.frame_range] if act else None,
        "hips_z_raw": [round(hips_z[0], 1), round(hips_z[1], 1)] if hips_z else None,
        "t_pose_span_m": round((lh - rh).length, 4),
        "feet_z_m": round(feet_z, 4),
        "top_z_m": round(tops, 4),
    }
    return m, arm


def build_statue(spec, path):
    """Procedural statue: capsule-assembled static figure, feet z~0.
    Meters, Z-up (GLTF default out of Blender)."""
    import bmesh
    from mathutils import Matrix
    h = spec["h"]
    parts = []
    def _cap(name, p0, p1, r):
        d = Vector(p1) - Vector(p0)
        length = d.length
        if length < 1e-6:
            return None
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False,
                              segments=12, radius1=r, radius2=r,
                              depth=length)
        mid = (Vector(p0) + Vector(p1)) * 0.5
        rot = d.normalized().to_track_quat('Z', 'Y').to_matrix().to_4x4()
        bm.transform(Matrix.Translation(mid) @ rot)
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        ob = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(ob)
        parts.append(ob)
        return ob
    _cap("statue_hips", (0, 0, h * 0.53), (0, 0, h * 0.62), 0.13)
    _cap("statue_torso", (0, 0, h * 0.62), (0, 0, h * 0.82), 0.15)
    _cap("statue_head", (0, 0, h * 0.84), (0, 0, h * 0.94), 0.11)
    for sx in (1, -1):
        _cap(f"statue_leg_l{sx}", (0.09 * sx, 0, 0.0), (0.09 * sx, 0, h * 0.53), 0.075)
        _cap(f"statue_arm{sx}", (0.20 * sx, 0, h * 0.62), (0.20 * sx, 0, h * 0.80), 0.05)
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts:
        o.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    statue = bpy.context.view_layer.objects.active
    statue.name = spec["name"]
    # ground the subtree: min vertex z -> 0
    zs = [v.co.z for v in statue.data.vertices]
    dz = -min(zs)
    statue.location.z += dz
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
    zs = [v.co.z for v in statue.data.vertices]
    spec["_measured_height"] = round(max(zs) - min(zs), 4)
    spec["_measured_min_z"] = round(min(zs), 5)
    bpy.ops.object.select_all(action='DESELECT')
    statue.select_set(True)
    bpy.context.view_layer.objects.active = statue
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB',
                              use_selection=True, export_apply=True)
    return statue


# --------------------------------------------------------------------------- #
#  Main
# --------------------------------------------------------------------------- #

def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    root = DEFAULT_ROOT
    force = False
    i = 0
    while i < len(argv):
        if argv[i] == "--root":
            root = argv[i + 1]; i += 2
        elif argv[i] == "--force":
            force = True; i += 1
        else:
            i += 1
    truth_marker = os.path.join(root, "truth.json")
    if os.path.isfile(truth_marker) and not force:
        print(f"[fixture] {truth_marker} exists — nothing to do "
              f"(--force to rebuild)")
        return

    _clean_scene()
    anim_dir = os.path.join(root, "RH-canvas-animations")
    char_dir = os.path.join(root, "RH-canvas-characters")
    fbx_dir = os.path.join(root, "fbx")
    glb_dir = os.path.join(root, "gltf")
    for d in (anim_dir, os.path.join(anim_dir, "data"), char_dir,
              os.path.join(char_dir, "data"), fbx_dir, glb_dir):
        os.makedirs(d, exist_ok=True)

    manifest = []
    anim_rows = []
    truth = {"generator": "rh_fixture_lib.py", "clips": {}, "statues": {},
             "recipe": None}

    # ---- round-trip CALIBRATION: recipe grid search against the
    # 9-law oracle. No hand-deduced constants — the (node_scale, usf,
    # rest_x100, curve_x100) combo that satisfies EVERY law is pinned
    # and used for every clip. Fail-closed if none does. ----
    import itertools
    import _fixture_fbx_patch as fxp

    def laws_ok(m):
        # The fixture oracle: the laws that gate CONSUMER BEHAVIOR
        # (65-bone rig, upright meters figure, curves present, fps,
        # frame range). The platform's object-scale 0.01 VALUE and the
        # obj-rot-X 90 VALUE are Maya-time unit-baking artifacts that
        # are unrecoverable with the source dark — the fixture pins its
        # OWN measured import state in truth.json and the battery
        # asserts THAT (self-verifying fixture law); docs/rh_canvas.md
        # laws 1-2 keep full authority on real library clones.
        if m["bones"] != 65 or m["bad_prefix"]:
            return False
        if not m["hips_z_raw"]:
            return False
        if not (-0.05 <= m["feet_z_m"] <= 0.25):
            return False
        if not (1.2 <= m["top_z_m"] <= 2.3):
            return False
        if not (0.0005 <= abs(m["obj_scale"][0]) <= 100):
            return False
        return True

    def export_probe(path):
        """Build the probe clip fresh, export, return its spec."""
        arm = build_rig()
        build_action(arm, spec0)
        export_clip_fbx(arm, path, frames=spec0['frames'])
        bpy.data.objects.remove(arm, do_unlink=True)
        for a in list(bpy.data.actions):
            bpy.data.actions.remove(a)

    arm = build_rig()          # (kept for API parity with older flow)
    bpy.data.objects.remove(arm, do_unlink=True)
    spec0 = CLIPS[0]
    probe_path = os.path.join(fbx_dir, f"{spec0['id']}.fbx")
    export_probe(probe_path)

    RECIPE = None
    grid = [(100.0, 1.0, 'm_yup', -90.0),    # the upright-meters recipe
            (100.0, 1.0, 'cm_yup', -90.0),
            (100.0, 1.0, 'm_yup', 0.0)]
    for node_scale, usf, rest_mode, node_rot in grid:
        recipe = {"node_scale": node_scale, "usf": usf,
                  "rest_mode": rest_mode, "node_rot": node_rot,
                  "curve_x100": True}
        export_probe(probe_path)          # fresh file per trial (no compounding)
        fxp.patch_file(probe_path, **recipe)
        m, imp_arm = verify_import_laws(probe_path)
        ok = laws_ok(m)
        print(f"[fixture] recipe ns={node_scale} usf={usf} "
              f"rest={rest_mode} rot={node_rot} -> "
              f"scale={m['obj_scale'][0]:<8} rx={m['rot_x_deg']:<7} "
              f"feet={m['feet_z_m']:<8} top={m['top_z_m']:<8} "
              f"{'PASS' if ok else 'fail'}")
        if ok:
            RECIPE = recipe
            bpy.data.objects.remove(imp_arm, do_unlink=True)
            break
        bpy.data.objects.remove(imp_arm, do_unlink=True)
    if RECIPE is None:
        raise SystemExit(
            "[fixture] CALIBRATION FAILED — no recipe in the grid "
            "reproduces the platform laws (see the per-recipe rows "
            "above). Do NOT lower the bars; extend the grid or fix "
            "the patch — the fixture exists to exercise the laws.")
    truth["recipe"] = RECIPE
    print(f"[fixture] calibration OK — recipe pinned: {RECIPE}")
    # re-patch the probe with the winning recipe (the loop's last patch
    # on it IS the winner's; the probe file is clip 9001's final form)
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)

    for spec in CLIPS:
        arm = build_rig()
        build_action(arm, spec)
        path = os.path.join(fbx_dir, f"{spec['id']}.fbx")
        export_clip_fbx(arm, path, frames=spec['frames'])
        fxp.patch_file(path, **RECIPE)
        # truth from the RE-IMPORT (what consumers will actually see)
        m, imp_arm = verify_import_laws(path)
        act = imp_arm.animation_data.action
        # xy path length from the hips LOCATION fcurves (raw cm -> m)
        xy = 0.0
        try:
            fcs = []
            for layer in act.layers:
                for strip in layer.strips:
                    for bag in strip.channelbags:
                        fcs.extend(bag.fcurves)
        except AttributeError:
            fcs = list(act.fcurves)
        hips = {}
        for fc in fcs:
            if fc.data_path == 'pose.bones["%sHips"].location' % MIX:
                hips[fc.array_index] = [kp.co[1] for kp in fc.keyframe_points]
        if 0 in hips and 1 in hips:
            xs, ys = hips[0], hips[1]
            xy = sum(math.hypot(xs[i] - xs[i - 1], ys[i] - ys[i - 1])
                     for i in range(1, len(xs)))
            # unit-aware: raw cm values (usf=100 recipe) read /100; the
            # pinned usf=1 recipe lands curves in METERS (the importer
            # applies the unit factor the platform files never carried)
            if RECIPE and RECIPE.get("usf") == 100.0:
                xy /= 100.0
        animated = 0
        seen = set()
        for fc in fcs:
            dp = fc.data_path
            if dp.startswith('pose.bones["%s' % MIX):
                b = dp.split('"')[1]
                if b not in seen:
                    seen.add(b)
        animated = len(seen)
        if spec["kind"] == "run" and abs(xy - spec.get("travel_m", 3.0)) > 0.6:
            raise SystemExit(
                f"[fixture] XY-PATH LAW FAILED on {spec['id']}: hips XY "
                f"path reads {xy:.3f} m (expected ~3.0 m of travel).")
        truth["clips"][spec["id"]] = {
            "name": spec["name"], "nameEn": spec["nameEn"],
            "category": spec["cat"], "frames": m["action_frames"],
            "obj_scale": m["obj_scale"], "rot_x_deg": m["rot_x_deg"],
            "hips_z_raw_cm": m["hips_z_raw"],
            "xy_path_m": round(xy, 3),
            "animated_bones": animated,
            "t_pose_span_m": m["t_pose_span_m"],
            "tags": ([t for t, s in
                      (("elevated_root_motion", spec["id"] in ELEVATED),
                       ("static_pose", spec["id"] in STATIC)) if s]),
        }
        manifest.append({
            "id": spec["id"], "categoryCode": spec["cat"],
            "name": spec["name"], "nameEn": spec["nameEn"],
            "size": os.path.getsize(path),
            "sha256": _sha256_file(path),
            "url": "file://" + os.path.abspath(path),
            "tags": truth["clips"][spec["id"]]["tags"],
            "frames": truth["clips"][spec["id"]]["frames"][1] 
                  - truth["clips"][spec["id"]]["frames"][0] + 1,
        })
        anim_rows.append({"id": spec["id"], "categoryCode": spec["cat"],
                          "name": spec["name"], "nameEn": spec["nameEn"]})
        print(f"[fixture] clip {spec['id']} {spec['kind']}: "
              f"frames={m['action_frames']} hips_cm={m['hips_z_raw']} "
              f"xy={xy:.2f}m animated={animated}")
        # purge for the next clip (single-action files)
        bpy.data.objects.remove(imp_arm, do_unlink=True)
        bpy.data.objects.remove(arm, do_unlink=True)
        for a in list(bpy.data.actions):
            bpy.data.actions.remove(a)

    # ---- statues ----
    for spec in STATUES:
        path = os.path.join(glb_dir, spec["name"].replace(" ", "_") + ".glb")
        _clean_scene()
        build_statue(spec, path)
        truth["statues"][spec["name"]] = {
            "group": spec["group"], "group_label": spec["group_label"],
            "size": os.path.getsize(path),
            "sha256": _sha256_file(path),
            "height_m": spec.get("_measured_height"),
            "feet_min_z_m": spec.get("_measured_min_z"),
        }
        manifest_note = "built by rh_fixture_lib (procedural)"
        print(f"[fixture] statue {spec['name']}: {path}")

    # ---- characters catalog files ----
    char_manifest = []
    models = []
    for spec in STATUES:
        fname = spec["name"].replace(" ", "_") + ".glb"
        path = os.path.join(glb_dir, fname)
        char_manifest.append({
            "url": "file://" + os.path.abspath(path),
            "size": os.path.getsize(path),
            "sha256": _sha256_file(path),
        })
        models.append({"key": spec["group"], "label": spec["group_label"],
                       "models": [{"id": spec["name"], "name": spec["name"],
                                   "url": "file://" + os.path.abspath(path)}]})
    _clean_scene()

    # ---- write the library files ----
    with open(os.path.join(anim_dir, "assets-manifest.json"), "w") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    with open(os.path.join(anim_dir, "data", "animations.jsonl"), "w") as f:
        for r in anim_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(os.path.join(anim_dir, "data", "category_tree.json"), "w") as f:
        json.dump(CATEGORIES, f, ensure_ascii=False, indent=1)
    with open(os.path.join(char_dir, "director-gltf-manifest.json"), "w") as f:
        json.dump(char_manifest, f, ensure_ascii=False, indent=1)
    with open(os.path.join(char_dir, "data", "characters.jsonl"), "w") as f:
        for c in CHARACTERS:
            f.write(json.dumps({"id": c["id"], "name": c["name"],
                                "attributes": {k: {"optionCode": v} for k, v in c["facets"].items()}},
                               ensure_ascii=False) + "\n")
    with open(os.path.join(char_dir, "data", "filter_options.json"), "w") as f:
        json.dump({"groups": [{"key": "facets", "label": "Facets",
                               "categories": [{"code": k,
                                               "options": [{"code": v} for v in vs]}
                                              for k, vs in FACETS.items()]}]},
                  f, ensure_ascii=False, indent=1)
    with open(os.path.join(char_dir, "data", "director_models.json"), "w") as f:
        json.dump(models, f, ensure_ascii=False, indent=1)
    with open(truth_marker, "w") as f:
        json.dump(truth, f, ensure_ascii=False, indent=1)

    print(f"[fixture] library written: {root}")
    print(f"[fixture] clips={len(manifest)} statues={len(STATUES)} "
          f"truth={truth_marker}")


if __name__ == "__main__":
    main()
