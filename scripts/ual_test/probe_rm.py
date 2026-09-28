# probe_rm.py -- follow-up: document the *_RM (root-motion) action variants
# found by the UAL-1 gauntlet (Roll_RM root drift 4.99 m). Confirms the
# in-place vs root-motion split so the R5 verdict can name the exact rule.
import json
import os
import sys

import bpy

DEFAULT_GLTF = os.path.join(
    "assets", "vendor", "ual", "gltf-universal-animation-library-main",
    "glTF", "AnimationLibrary_Godot_Standard.gltf")

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
gltf_path = argv[0] if argv else DEFAULT_GLTF

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=gltf_path)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
root_pb = arm.pose.bones.get("root")
ad = arm.animation_data
scene = bpy.context.scene

pairs = [("Roll", "Roll_RM"), ("Sword_Attack", "Sword_Attack_RM")]
out = {}
for base, rm in pairs:
    row = {}
    for nm in (base, rm):
        act = bpy.data.actions.get(nm)
        if not act:
            row[nm] = "MISSING"
            continue
        ad.action = act
        fa, fb = [int(f) for f in act.frame_range]
        pts = []
        for f in (fa, fb):
            scene.frame_set(f)
            bpy.context.view_layer.update()
            pts.append((arm.matrix_world @ root_pb.matrix).translation)
        d = pts[1] - pts[0]
        row[nm] = {"frames": [fa, fb],
                   "root_drift_xy_m": round((d.x ** 2 + d.y ** 2) ** 0.5, 3),
                   "root_dz_m": round(d.z, 3)}
    out[f"{base} vs {rm}"] = row
    print(f"{base:14} {row[base]}")
    print(f"{rm:14} {row[rm]}")

# also: do the 4 R1 statics apply a POSE (vs T-pose baseline)?
ad.action = bpy.data.actions["A_TPose"]
scene.frame_set(2)
bpy.context.view_layer.update()
tp = {b.name: (arm.matrix_world @ b.matrix).translation.copy()
      for b in arm.pose.bones}
statics = ["Pistol_Aim_Neutral", "Pistol_Aim_Down", "Pistol_Aim_Up"]
pose = {}
for nm in statics:
    ad.action = bpy.data.actions[nm]
    scene.frame_set(2)
    bpy.context.view_layer.update()
    dev = max(((arm.matrix_world @ b.matrix).translation - tp[b.name]).length
              for b in arm.pose.bones)
    pose[nm] = round(dev, 3)
    print(f"static {nm}: max bone displacement vs T-pose = {dev:.3f} m "
          f"{'(applies a pose)' if dev > 0.1 else '(IDENTICAL to T-pose!)'}")
out["statics_apply_pose_m"] = pose

with open("output/ual/probe_rm.json", "w") as fh:
    json.dump(out, fh, indent=1)
print("[probe_rm] -> output/ual/probe_rm.json")
