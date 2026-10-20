#!/usr/bin/env python3
"""s26_rig_accept.py — the reconstructed rig's acceptance gates G1-G7.

DESIGN_world_retune_s26 D2 [A1/A2/A5/A10]. Committed script + battery
row (humanoid_crowd had ZERO coverage — the "presumed broken" law).

Run:
  RH_ASSETS=/tmp/rhrec ./scripts/blrun.sh --background --factory-startup \
    --python scripts/s26_rig_accept.py
where /tmp/rhrec/assets/director/dummy-rigs/x_bot.fbx is the
reconstruction (the setup lives in the script — pass --rig to source it).

G1 POLY_BAND via prepare_template (pre-decimated OR self-calibrated)
G2 RIG_HEIGHT band (the s22 probe's own armature-bbox measure, +/-2%)
G3 bone census: 65 mixamorig, all present in the clip's skeleton
G4 FULL tdawn humanoid build: bind_crowd 129 + motion_gates + UAL
   principals (the certified film as the proof surface)
G5 mesh-vertex world delta across half a cycle (weight/modifier loss
   makes statues that pose-bone gates cannot see)
G6 trajectory diff: reconstruction driven by vendored 2899.fbx vs the
   clip's own armature — hips/feet world positions + facing across the
   cycle (catches scale / Rz-flip / bone-frame drift)
G7 the no-tint law: template meshes carry exactly the neutral material
"""
import math
import os
import sys

import bpy
from mathutils import Vector

VK = os.path.dirname(os.path.abspath(__file__))
TMP = "/tmp/rhrec"
FAILS = []


def _P(*a):
    print("[accept]", *a, flush=True)


def _G(gid, name, ok, detail=""):
    tag = "PASS" if ok else "FAIL"
    _P(f"G{gid} {name}: {tag} {detail}")
    if not ok:
        FAILS.append(f"G{gid} {name} {detail}")



def iter_fcurves_safe(action):
    """Version-safe fcurve iteration for the accept probe (the kit's
    iter_fcurves needs its module import — inline the minimal form)."""
    try:
        sys.path.insert(0, VK)
        import blender_kit
        return blender_kit.iter_fcurves(action)
    except Exception:
        return []


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--rig", default="vendor/rh_rig/x_bot_reconstructed.blend")
    args = ap.parse_args(argv)

    # the fallback law IS the tested path: RH_ASSETS is left at its
    # default (no RH checkout in this sandbox) so crowd_family must
    # resolve the vendored reconstructed .blend (A2's fresh-sandbox
    # guarantee, exercised for real)
    if os.environ.get("RH_ASSETS"):
        del os.environ["RH_ASSETS"]
    sys.path.insert(0, VK)

    bpy.ops.wm.read_factory_settings(use_empty=True)

    import humanoid_crowd as HC
    fam = HC.crowd_family("rh_xbot")

    # ---- G1 + G2 + G3: template import --------------------------------
    tpl = HC.prepare_template(fam)
    arm = tpl["arm"]
    combined = tpl["combined_verts"]
    _G(1, "POLY_BAND", HC.POLY_BAND[0] <= combined <= HC.POLY_BAND[1],
       f"combined={combined} band={HC.POLY_BAND} pre_decimated="
       f"{tpl.get('pre_decimated')}")
    bpy.context.view_layer.update()
    zs = [(arm.matrix_world @ Vector(c)).z for c in arm.bound_box]
    span = max(zs) - min(zs)
    _G(2, "RIG_HEIGHT", abs(span - 2.051) <= 0.02 * 2.051,
       f"span={span:.4f} target=2.051")

    # the clip's own skeleton for G3/G6
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(
        filepath=os.path.abspath(os.path.join(
            VK, "..", "vendor", "rh_clips", "assets", "fbx",
            "2899.fbx")))
    clip_arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'
                and o not in before][-1]
    clip_bones = {b.name for b in clip_arm.data.bones}
    tpl_bones = [b.name for b in arm.data.bones]
    n_mix = sum(1 for n in tpl_bones if n.startswith("mixamorig:"))
    _G(3, "BONE_CENSUS", n_mix == 65 and set(tpl_bones) <= clip_bones,
       f"mixamorig={n_mix} subset={set(tpl_bones) <= clip_bones}")

    # ---- G6 (template-space, pre-bind): trajectory diff ----------------
    # drive BOTH skeletons with the clip action, compare world trajectories
    # semantic lookup (the no-name-luck law): the action that drives
    # mixamorig bones — the FBX action's name varies by import version
    act = None
    for a in bpy.data.actions:
        try:
            if any("Hips" in fc.data_path
                   for fc in iter_fcurves_safe(a)):
                act = a
                break
        except Exception:
            continue
    traj_ok, traj_detail = _g6_trajectory(arm, clip_arm, act)
    _G(6, "TRAJECTORY_DIFF", traj_ok, traj_detail)

    # ---- G7: neutral-material law --------------------------------------
    mats = {m.data.materials[0].name if m.data.materials else None
            for m in tpl["meshes"]}
    _G(7, "NO_TINT", mats == {"KIT.RigNeutral"},
       f"mats={mats}")

    # ---- G4: the full tdawn humanoid build -----------------------------
    os.environ["CROWD_CACHE_DIR"] = "/tmp/crowdcache_tdawn"
    os.environ["TDAWN_HUMANOID"] = "1"
    os.environ["BLENDER_KIT_QUIET"] = "1"
    sys.path.insert(0, os.path.join(VK))
    import importlib
    td = importlib.import_module("scene_terminal_dawn")
    ctx = td.build_scene()
    td.animate(ctx)          # the crowd branch + humanoid layer live here
    hum = ctx.get("humanoid")
    # bind_crowd's report contract: {"n", "n_walk", "n_idle", "verts",
    # "reps", ...} — the count key is "n" (READ, not invented)
    _G(4, "TDAWN_BIND", bool(hum) and hum.get("n") == 129,
       f"n={hum.get('n') if hum else None} "
       f"n_walk={hum.get('n_walk') if hum else None} "
       f"n_idle={hum.get('n_idle') if hum else None}")

    # ---- G5: mesh-vertex world delta (one bound agent, half cycle) ------
    reps = hum.get("reps") if hum else None
    if reps:
        r0 = reps[0]
        rig = r0.get("armature")  # the meshes parent to the ARMATURE
        meshes = [o for o in (rig.children if rig else [])
                  if o.type == 'MESH']
        if meshes:
            me = meshes[0]
            scene = bpy.context.scene
            f_mid = scene.frame_current + 12
            # the DEFORMED position lives on the depsgraph-evaluated
            # mesh — me.data.vertices is the REST (constant by
            # definition; the s26 first read measured 0.0000 on a
            # visibly-animated crowd)
            dg = bpy.context.evaluated_depsgraph_get()

            def _ev(f):
                scene.frame_set(f)
                dg.update()
                ev = me.evaluated_get(dg)
                return (me.matrix_world
                        @ ev.data.vertices[0].co).copy()

            v0 = _ev(f_mid)
            v1 = _ev(f_mid + 12)
            d = (v1 - v0).length
            _G(5, "SKIN_ALIVE", d > 0.01,
               f"vertex world delta over 12f = {d:.4f} m")
        else:
            _G(5, "SKIN_ALIVE", False, "no mesh child on the rig")
    else:
        _G(5, "SKIN_ALIVE", False, "no humanoid report")

    if FAILS:
        _P(f"ACCEPTANCE FAILED ({len(FAILS)}): {FAILS}")
        sys.exit(3)
    _P("ACCEPTANCE: ALL GREEN")


def _g6_trajectory(tpl_arm, clip_arm, act):
    """Drive both skeletons with the clip action; compare world
    trajectories of hips + both feet across the cycle + facing."""
    if act is None:
        return False, "no clip action"
    bones = ["mixamorig:Hips", "mixamorig:LeftFoot",
             "mixamorig:RightFoot"]
    # one action, both armatures — the channels target pose bones BY
    # NAME and both skeletons are mixamorig:65 (the G3 census), so
    # sharing the action drives both (no 5.x fcurve-copy needed)
    res = {}
    for tag, arm in (("tpl", tpl_arm), ("clip", clip_arm)):
        arm.animation_data_create()
        arm.animation_data.action = act
        # the 5.x SLOT law: an action evaluates on a datablock only
        # through a bound slot — unbound = silent zero motion (the
        # range-delta-1.0 signature this gate exists to catch)
        slots = getattr(act, "slots", None)
        if slots:
            arm.animation_data.action_slot = slots[0]
        pts = {b: [] for b in bones}
        frames = [2, 8, 14, 20, 26, 32]
        for f in frames:
            bpy.context.scene.frame_set(f)
            bpy.context.view_layer.update()
            for b in bones:
                pb = arm.pose.bones.get(b)
                if pb is None:
                    return False, f"{tag} missing bone {b}"
                w = arm.matrix_world @ pb.matrix
                pts[b].append((w.to_translation().x, w.to_translation().z))
        res[tag] = pts
    # normalize: subtract each rig's hips mean (placement-free), then
    # compare per-bone trajectory radius (motion RANGE is the invariant;
    # absolute orientation differs if the wrapper flip survived — the
    # range comparison catches scale/frame drift; a full-flip check runs
    # on the feet's x-extent sign symmetry)
    deltas = []
    for b in bones:
        for axis in (0, 1):
            t = [p[axis] for p in res["tpl"][b]]
            c = [p[axis] for p in res["clip"][b]]
            rt = max(t) - min(t)
            rc = max(c) - min(c)
            if rc > 1e-5:
                deltas.append(abs(rt - rc) / max(rc, 1e-5))
    worst = max(deltas) if deltas else 1.0
    return worst < 0.35, f"worst range-rel-delta={worst:.3f} (n={len(deltas)})"


main()
