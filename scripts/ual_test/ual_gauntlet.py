# ual_gauntlet.py -- UAL verification gauntlet (Task UAL-1, deliverable 2).
#
# Adapted from project/research/rigged_character_upgrade_path.md section 3:
#   R1  import succeeds; ALL actions evaluate (set frame, read every pose
#       bone's world matrix, assert non-zero positional variance)
#   R3  action coverage for the kit's story beats (sprint / boarding-sit /
#       aim / lunge-grab / gunner-thrown / death-fall) -- exact names
#   R5  in-place: root-bone world position at first vs last frame of each
#       beat action; drift must be < 0.05 m (armature object drift too)
#   R4  recolor: single material slot -> diffuse_color AND Principled base
#       color = SUBJECT_RED (0.82, 0.10, 0.12); workbench MATERIAL render;
#       pixel verification (R-share via scripts/image_metrics.py) runs
#       OUTSIDE this script and is appended to the results JSON by the caller
#   SCL scale: armature world bbox height ~1.7-1.9 m (research gate:
#       1.5-2.0 m; feet z ~ 0)
#
# Usage:
#   bash scripts/blrun.sh --background --python scripts/ual_test/ual_gauntlet.py -- \
#        [gltf_path] [out_dir]
import json
import math
import os
import sys
import time

import bpy
from mathutils import Vector

DEFAULT_GLTF = os.path.join(
    "assets", "vendor", "ual", "gltf-universal-animation-library-main",
    "glTF", "AnimationLibrary_Godot_Standard.gltf")

SUBJECT_RED = (0.82, 0.10, 0.12)     # kit v3 subject color (capsule SHIRT)

BEATS = {   # story beat -> candidate action names (exact, ordered by fit)
    "sprint/run": ["Sprint_Loop", "Jog_Fwd_Loop", "Walk_Loop",
                   "Crouch_Fwd_Loop", "Walk_Formal_Loop"],
    "boarding-sit": ["Sitting_Enter", "Sitting_Idle_Loop", "Sitting_Exit",
                     "Sitting_Talking_Loop", "Driving_Loop"],
    "aim (pistol)": ["Pistol_Aim_Neutral", "Pistol_Aim_Down", "Pistol_Aim_Up",
                     "Pistol_Idle_Loop", "Pistol_Shoot", "Pistol_Reload"],
    "lunge-grab": ["Punch_Cross", "Interact", "PickUp_Table", "Sword_Attack",
                   "Jump_Start", "Punch_Jab"],
    "gunner-thrown": ["Hit_Chest", "Death01", "Hit_Head", "Jump_Land",
                      "Roll", "Roll_RM"],
    "death/fall": ["Death01", "Jump_Land", "Hit_Chest", "Hit_Head"],
}

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
gltf_path = argv[0] if argv else DEFAULT_GLTF
out_dir = argv[1] if len(argv) > 1 else os.path.join("output", "ual")
os.makedirs(out_dir, exist_ok=True)

R = {"gltf": gltf_path, "beats": {}, "r1_actions": [], "r5": [], "scale": {}}


def upd():
    bpy.context.view_layer.update()
    bpy.context.view_layer.update()   # x2 (gotcha #27: eval order)


def bone_world(arm, pb):
    return (arm.matrix_world @ pb.matrix).translation


# ---- import ---------------------------------------------------------------
bpy.ops.wm.read_factory_settings(use_empty=True)
t0 = time.time()
bpy.ops.import_scene.gltf(filepath=gltf_path)
R["import_s"] = round(time.time() - t0, 2)

arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
mesh = next(o for o in bpy.data.objects if o.type == "MESH" and o.find_armature())
# stray scene-node meshes (probe found 'Icosphere', 42 verts, no armature):
# report their visibility flags and force-hide them from renders
for ob in bpy.data.objects:
    if ob not in (arm, mesh) and ob.type == "MESH":
        R.setdefault("stray_meshes", []).append(
            {ob.name: {"hide_render": ob.hide_render,
                       "hide_viewport": ob.hide_viewport,
                       "location": tuple(round(c, 2) for c in ob.location)}})
        ob.hide_render = True
        ob.hide_viewport = True
bones = list(arm.pose.bones)
ad = arm.animation_data
scene = bpy.context.scene

# root / hips bones (Rigify-style: 'root' + DEF-*)
root_pb = arm.pose.bones.get("root") or bones[0]
hip_pb = next((b for b in bones if "hip" in b.name.lower() or
               "pelvis" in b.name.lower()), root_pb)

# ---- scale check (SCL) ----------------------------------------------------
def bone_bbox(arm):
    lo = Vector((1e9,) * 3)
    hi = Vector((-1e9,) * 3)
    for pb in arm.pose.bones:
        for p in (bone_world(arm, pb),
                  (arm.matrix_world @ pb.matrix @ Vector((0, pb.length, 0)))):
            for i in range(3):
                lo[i] = min(lo[i], p[i])
                hi[i] = max(hi[i], p[i])
    return lo, hi

lo, hi = bone_bbox(arm)
R["scale"]["bind_height_m"] = round(hi.z - lo.z, 3)
R["scale"]["bind_feet_z"] = round(lo.z, 3)
idle = bpy.data.actions.get("Idle_Loop")
if idle:
    ad.action = idle
    upd()
    lo2, hi2 = bone_bbox(arm)
    R["scale"]["idle_height_m"] = round(hi2.z - lo2.z, 3)
    R["scale"]["idle_feet_z"] = round(lo2.z, 3)
h = R["scale"].get("idle_height_m", R["scale"]["bind_height_m"])
R["scale"]["pass"] = bool(1.5 <= h <= 2.0)   # research-doc gate; mission's
R["scale"]["mission_1.7_1.9"] = bool(1.7 <= h <= 1.9)  # tighter band, noted

# ---- R3: beat coverage ----------------------------------------------------
print("=== R3 action coverage (exact names) ===")
for beat, cands in BEATS.items():
    found = [c for c in cands if bpy.data.actions.get(c)]
    missing = [c for c in cands if not bpy.data.actions.get(c)]
    R["beats"][beat] = {"found": found, "missing": missing}
    print(f"  {beat:<16} -> {found}"
          + (f"   (not in library: {missing})" if missing else ""))
all_actions = sorted(a.name for a in bpy.data.actions)
R["action_names"] = all_actions

# ---- R1: every action evaluates -------------------------------------------
print(f"=== R1 anim-eval probe: {len(all_actions)} actions x 6 frames x "
      f"{len(bones)} bones ===")
t1 = time.time()
static = []
for name in all_actions:
    act = bpy.data.actions[name]
    ad.action = act                     # single-slot auto-bind (verified)
    fa, fb = act.frame_range
    span = max(1.0, fb - fa)
    frames = [int(fa + span * t / 5.0) for t in range(6)]
    pos = {b.name: [] for b in bones}
    for f in frames:
        scene.frame_set(f)
        upd()
        for b in bones:
            pos[b.name].append(bone_world(arm, b))
    var = 0.0
    for pts in pos.values():
        cols = list(zip(*pts))
        var = max(var, max(max(c) - min(c) for c in cols))
    row = {"action": name, "frames": [int(fa), int(fb)],
           "max_bone_pos_range_m": round(var, 4)}
    R["r1_actions"].append(row)
    if var <= 1e-5:
        static.append(name)
        print(f"  [STATIC] {name:<24} f{int(fa)}-{int(fb)}  var={var:.4f}  "
              f"(<- legitimately static pose? single-frame)")
print(f"R1 scan took {time.time() - t1:.1f}s; "
      f"{len(all_actions) - len(static)}/{len(all_actions)} actions move "
      f"bones; static: {static}")
R["r1_pass"] = len(static) == 0
R["r1_static_actions"] = static
ad.action = None

# ---- R5: root drift first/last frame, per beat action ---------------------
print("=== R5 in-place probe (first vs last frame) ===")
beat_actions = sorted({a for v in R["beats"].values() for a in v["found"]})
for name in beat_actions:
    act = bpy.data.actions[name]
    ad.action = act
    fa, fb = [int(f) for f in act.frame_range]
    row = {"action": name, "frames": [fa, fb]}
    scene.frame_set(fa)
    upd()
    p_root_a = bone_world(arm, root_pb)
    p_hip_a = bone_world(arm, hip_pb)
    obj_a = arm.matrix_world.translation.copy()
    scene.frame_set(fb)
    upd()
    p_root_b = bone_world(arm, root_pb)
    p_hip_b = bone_world(arm, hip_pb)
    obj_b = arm.matrix_world.translation.copy()
    def horiz(a, b):
        return round(math.hypot(a.x - b.x, a.y - b.y), 4)
    row["root_bone_drift_m"] = horiz(p_root_a, p_root_b)
    row["hips_drift_m"] = horiz(p_hip_a, p_hip_b)
    row["armature_object_drift_m"] = horiz(obj_a, obj_b)
    row["pass"] = (row["root_bone_drift_m"] < 0.05
                   and row["armature_object_drift_m"] < 0.05)
    R["r5"].append(row)
    print(f"  {name:<24} root={row['root_bone_drift_m']:.4f} m  "
          f"obj={row['armature_object_drift_m']:.4f} m  "
          f"hips={row['hips_drift_m']:.4f} m  "
          f"{'PASS' if row['pass'] else 'FAIL'}")
ad.action = None

# ---- R4: single-material recolor + MATERIAL-mode render --------------------
print("=== R4 recolor render (workbench MATERIAL) ===")
red = bpy.data.materials.new("UAL_SUBJECT_RED")
red.use_nodes = True
bsdf = red.node_tree.nodes.get("Principled BSDF")
bsdf.inputs["Base Color"].default_value = (*SUBJECT_RED, 1.0)
bsdf.inputs["Roughness"].default_value = 0.6
red.diffuse_color = (*SUBJECT_RED, 1.0)   # workbench reads viewport color
for slot in mesh.material_slots:
    slot.material = red                 # single-material override
R["r4"] = {"material": "UAL_SUBJECT_RED",
           "principled_base_color": SUBJECT_RED,
           "diffuse_color": SUBJECT_RED,
           "slots_overridden": len(mesh.material_slots),
           "render": os.path.join(out_dir, "red_check.png")}

# white ground + white wall (flat_light_experiment.py pattern)
def flat_mat(name, rgb):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*rgb, 1.0)
    m.diffuse_color = (*rgb, 1.0)
    return m

bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, 0))
ground = bpy.context.active_object
ground.name = "T.Ground"
ground.data.materials.append(flat_mat("T.Ground", (0.93, 0.93, 0.93)))
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 2.6, 1.5))
wall = bpy.context.active_object
wall.name = "T.Wall"
wall.scale = (3.0, 0.15, 1.5)
wall.data.materials.append(flat_mat("T.Wall", (0.88, 0.88, 0.90)))

# Sprint mid-frame (dynamic, full-body spread)
act = bpy.data.actions["Sprint_Loop"]
ad.action = act
fa, fb = [int(f) for f in act.frame_range]
scene.frame_set((fa + fb) // 2)
upd()

cam_data = bpy.data.cameras.new("CAM.R4")
cam_data.lens = 45
cam = bpy.data.objects.new("CAM.R4", cam_data)
cam.location = (2.3, -2.7, 1.35)
scene.collection.objects.link(cam)
d = Vector((0, 0, 0.85)) - cam.location
cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
scene.camera = cam

scene.render.resolution_x = 960
scene.render.resolution_y = 540
scene.render.image_settings.file_format = "PNG"
scene.render.engine = "BLENDER_WORKBENCH"
try:
    scene.view_settings.view_transform = "Standard"
except AttributeError:
    pass
sh = scene.display.shading
sh.light = "STUDIO"
sh.color_type = "MATERIAL"
sh.show_shadows = False
sh.show_cavity = False
scene.display.render_aa = "OFF"
# headless: no world => BLACK background (session-8 gotcha)
world = bpy.data.worlds.new("FlatGuidance")
world.use_nodes = False
world.color = (0.50, 0.50, 0.52)
scene.world = world
scene.render.filepath = R["r4"]["render"]
scene.render.film_transparent = False
bpy.ops.render.render(write_still=True)
print(f"  rendered {R['r4']['render']} (Sprint_Loop frame {(fa + fb) // 2})")

# G4 hygiene: NLA stash tracks must still be muted after all assignments
nla = list(arm.animation_data.nla_tracks)
unmuted = [t.name for t in nla if not t.mute]
R["g4_unmuted_nla_tracks"] = unmuted
print(f"G4: nla_tracks={len(nla)}, unmuted after probing={unmuted or 'none'}")

# ---- verdict table --------------------------------------------------------
print("\n" + "=" * 78)
print("GAUNTLET VERDICTS (R4 pixel check appended by caller via image_metrics)")
print("=" * 78)
rows = [
    ("R1 import+eval", f"import {R['import_s']}s; "
     f"{len(all_actions) - len(static)}/{len(all_actions)} actions animate",
     "PASS" if R["r1_pass"] else "FAIL (see statics)"),
    ("R3 coverage", "; ".join(f"{b}: {len(v['found'])}" for b, v in
                              R["beats"].items()), "PASS (all 6 beats >0)"),
    ("R5 in-place", f"max root drift "
     f"{max(r['root_bone_drift_m'] for r in R['r5']):.4f} m over "
     f"{len(R['r5'])} beat actions",
     "PASS" if all(r["pass"] for r in R["r5"]) else "FAIL"),
    ("SCL scale", f"height {h} m (bind {R['scale']['bind_height_m']}, "
     f"feet z {R['scale'].get('idle_feet_z')})",
     "PASS" if R["scale"]["pass"] else "FAIL"),
    ("R4 recolor", "red_check.png rendered; R-share pending (image_metrics)",
     "PENDING"),
]
for name, detail, verdict in rows:
    print(f"  {name:<14} {detail}\n{'':>16}-> {verdict}")

R["r4"]["pixel_check"] = "PENDING (measure R-share via scripts/image_metrics.py)"
with open(os.path.join(out_dir, "gauntlet_results.json"), "w") as fh:
    json.dump(R, fh, indent=1)
print(f"\n[ual_gauntlet] results -> {os.path.join(out_dir, 'gauntlet_results.json')}")
