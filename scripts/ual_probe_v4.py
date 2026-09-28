# ual_probe_v4.py -- step-1 ground-truth probe for the v4 z-contract.
#
# Measures (single import, prints JSON):
#   * facing sign at bind (foot-tail world Y) -- decides the child-MPI
#     Rz(pi) flip (probed per import, never hard-coded -- REV3 item 6)
#   * pelvis/head/foot bone names (Rigify DEF-* conventions verified)
#   * Sitting_Enter FINAL-frame pelvis height above the feet-origin
#     -> the seated wrapper z = pan_top + 0.07 - that height
#   * Pistol_Aim_Neutral pelvis height (standing) -> sanity vs deck
#   * Sprint_Loop mid-frame pelvis height (running bounce center)
#   * action frame ranges for the beat map (11 actions)
#   * mesh name + material slot count (single-datablock law input)
#   * 8 sampled bone world matrices -> cross-process determinism file
import json
import os
import sys

import bpy
from mathutils import Vector

GLTF = "assets/vendor/ual/gltf-universal-animation-library-main/glTF/AnimationLibrary_Godot_Standard.gltf"
OUT = "output/ual_probe_v4"

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
gltf = argv[0] if argv else GLTF
out_dir = argv[1] if len(argv) > 1 else OUT
os.makedirs(out_dir, exist_ok=True)
R = {"gltf": gltf}


def upd():
    bpy.context.view_layer.update()
    bpy.context.view_layer.update()


def act(name):
    return bpy.data.actions[name]


def set_action(arm, name, frame):
    arm.animation_data.action = act(name)
    bpy.context.scene.frame_set(frame)
    upd()
    return act(name)


def bone_world(arm, bone_name):
    b = arm.pose.bones.get(bone_name)
    if b is None:
        return None
    return (arm.matrix_world @ b.matrix).translation.copy()


before = {o.name for o in bpy.data.objects}
bpy.ops.import_scene.gltf(filepath=gltf)
new = [o for o in bpy.data.objects if o.name not in before]
R["new_objects"] = sorted(o.name for o in new)
R["n_new"] = len(new)

arm = next(o for o in new if o.type == "ARMATURE")
meshes = [o for o in new if o.type == "MESH"]
R["armature"] = arm.name
R["meshes"] = [m.name for m in meshes]
skinned = [m for m in meshes if m.find_armature()]
R["skinned"] = [m.name for m in skinned]
mesh = skinned[0] if skinned else meshes[0]
R["mesh_slots"] = len(mesh.material_slots)
R["slot_datablocks"] = sorted({s.material.name for s in mesh.material_slots
                               if s.material})
R["strays"] = [m.name for m in meshes if m not in skinned]

# bone name discovery
names = [b.name for b in arm.pose.bones]
R["n_bones"] = len(names)
R["pelvis_bone"] = next((n for n in names if n.lower() in
                         ("def-hips", "def-pelvis", "hips", "pelvis")), None)
R["head_bone"] = next((n for n in names if n.lower() in
                       ("def-head", "head")), None)
R["foot_bones"] = sorted(n for n in names if "foot" in n.lower())[:4]
R["hand_bones"] = sorted(n for n in names if "hand" in n.lower())[:4]

# facing at bind (armature object untouched: identity basis)
upd()
foot = next(b for b in arm.pose.bones if "foot" in b.name.lower())
m = arm.matrix_world @ foot.matrix
fwd = (m.to_3x3() @ Vector((0, 1, 0))).normalized()
R["facing_foot_tail_world"] = [round(c, 3) for c in fwd]
R["facing_sign"] = 1 if fwd.y >= 0 else -1

# bind pose measurements
R["bind_height"] = round(max((arm.matrix_world @ v.matrix).translation.z
                             for v in arm.pose.bones), 4)
R["bind_pelvis_z"] = round(bone_world(arm, R["pelvis_bone"]).z, 4)
R["bind_head_z"] = round(bone_world(arm, R["head_bone"]).z, 4)

# action ranges (beat map)
BEATS = ["Sprint_Loop", "Jog_Fwd_Loop", "Sitting_Enter", "Sitting_Exit",
         "Sitting_Idle_Loop", "Sitting_Talking_Loop", "Driving_Loop",
         "Pistol_Aim_Neutral", "Pistol_Shoot", "Pistol_Idle_Loop",
         "Punch_Cross", "Hit_Chest", "Death01", "Walk_Loop"]
R["actions"] = {}
for nm in BEATS:
    a = act(nm)
    fa, fb = a.frame_range
    R["actions"][nm] = [int(fa), int(fb)]

# z-contract measurements
def pelvis_at(action_name, frame):
    set_action(arm, action_name, frame)
    return bone_world(arm, R["pelvis_bone"]).z

se_f, se_l = R["actions"]["Sitting_Enter"]
R["sit_enter_pelvis_first"] = round(pelvis_at("Sitting_Enter", int(se_f)), 4)
R["sit_enter_pelvis_final"] = round(pelvis_at("Sitting_Enter", int(se_l)), 4)
pa_f, pa_l = R["actions"]["Pistol_Aim_Neutral"]
R["aim_pelvis"] = round(pelvis_at("Pistol_Aim_Neutral", int(pa_f)), 4)
sp_f, sp_l = R["actions"]["Sprint_Loop"]
mid = (int(sp_f) + int(sp_l)) // 2
R["sprint_pelvis_mid"] = round(pelvis_at("Sprint_Loop", mid), 4)
dr_f, dr_l = R["actions"]["Driving_Loop"]
R["driving_pelvis_mid"] = round(pelvis_at("Driving_Loop",
                                          (int(dr_f) + int(dr_l)) // 2), 4)
si_f, si_l = R["actions"]["Sitting_Idle_Loop"]
R["sit_idle_pelvis_mid"] = round(pelvis_at("Sitting_Idle_Loop",
                                           (int(si_f) + int(si_l)) // 2), 4)

# derived z-contract numbers (jeep-local):
PAN_TOP = 1.12      # reviewer-measured seat pan top (jeep-local)
DECK_TOP = 0.72     # bed deck top
R["derived_seat_z"] = round(PAN_TOP + 0.07 - R["sit_enter_pelvis_final"], 4)
R["derived_gunner_z"] = round(DECK_TOP, 4)

# cross-process determinism sample: 8 bones x 3 actions x 2 frames
sample = {}
for aname, fr in (("Sprint_Loop", mid), ("Sitting_Enter", int(se_l)),
                  ("Pistol_Aim_Neutral", int(pa_f))):
    set_action(arm, aname, fr)
    for bn in (R["pelvis_bone"], R["head_bone"], "DEF-foot.L", "DEF-hand.L",
               "DEF-hand.R", "DEF-spine", "DEF-thigh.L", "DEF-shin.R"):
        b = arm.pose.bones.get(bn)
        if b is None:
            continue
        mw = arm.matrix_world @ b.matrix
        sample[f"{aname}@{fr}:{bn}"] = [round(v, 5) for row in
                                         mw for v in row]
R["det_sample"] = sample

path = os.path.join(out_dir, "ual_probe.json")
with open(path, "w") as f:
    json.dump(R, f, indent=1)
print(json.dumps({k: v for k, v in R.items() if k != "det_sample"}, indent=1))
print(f"PROBE_OK {path} ({len(sample)} det samples)")
