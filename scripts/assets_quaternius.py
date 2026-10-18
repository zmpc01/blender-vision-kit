"""assets_quaternius.py — the second rig family loader (s21-D2).

The Quaternius casual rigs (Male_Casual.fbx / Female_Casual.fbx,
vendored from previz research/_rig with import probes beside them):
42 bones (`HumanArmature`, pipe-named 11-action pool, QUATERNION
modes), skinned meshes BaseHuman/Female parented to the armature,
identity object transforms at import, mesh feet-origin.

Built ON wrapper_rig (never duplicates the wrapper math). Design:
docs/DESIGN_s21_hero_lane.md REV-2 (D2 + amendments D2a/D2b/D2c).

MEASURED TRUTH (s22 first-run probe, scripts/s22_quat_probe.py —
re-run it to re-pin; the audit's 0.24-0.33 UNIT_RESCALE guess came
from the bbox DIAGONAL 7.165 which includes the A-pose arm spread;
the HEIGHT is the right statistic):
  male   raw height 4.8413, feet 0.0034, 941 verts
  female raw height 4.6553, feet -0.0183, 1444 verts
  both: meshes parented to the armature at import, identity object
        transforms, facing -Y (Foot.L +Y world |y|=0.926, |z|=0.032)
UNIT_RESCALE pins male at 1.80 m (0.3718 = 1.80 / 4.8413); female
lands 1.731 m — both inside the 1.2-2.2 m post-rescale gate.

Action pool: the importer yields 11 pipe-named actions
(`HumanArmature|HumanArmature|Man_Walk`); pool keys = last pipe
segment MINUS the gender prefix -> {Walk, Idle, Jump, Death, Clapping,
Punch, Run, RunningJump, Sitting, Standing, SwordSlash}. Pools map
THIS import's actions via the acts-before/after diff (D2b — binding
hero #2 to hero #1's datablock is the "first import wins" bug).
"""
import os

import bpy

import wrapper_rig

_DIR = os.path.dirname(os.path.abspath(__file__))
FBX_FILES = {
    "male": os.path.join(_DIR, "..", "assets", "vendor", "quaternius",
                         "Male_Casual.fbx"),
    "female": os.path.join(_DIR, "..", "assets", "vendor", "quaternius",
                           "Female_Casual.fbx"),
}

GENDER_PREFIX = ("Man_", "Female_")
UNIT_RESCALE = 0.3718        # male 4.8413 raw -> 1.80 m (see docstring)
HEIGHT_MIN, HEIGHT_MAX = 1.2, 2.2     # post-rescale world gate (m)
FEET_BAND = 0.15             # feet-ground band (m)
BONE_CENSUS = 42
ACTION_CENSUS = 11


class LoadRefused(ValueError):
    """assets_quaternius refuses — fail-closed loader law."""


def load(key, name, scale=UNIT_RESCALE):
    """One FBX import -> discovery -> stray purge -> wrapper -> pool.

    Returns rep = {"arm", "mesh", "root", "pool", "actions", "probe",
    "height", "feet_z"} where pool maps stripped action keys to Action
    datablocks of THIS import (acts-diff law, D2b).
    """
    path = FBX_FILES.get(key)
    if not path or not os.path.isfile(path):
        raise LoadRefused(f"unknown key {key!r} (male|female) or missing "
                          f"FBX at {path}")
    if name in bpy.data.objects:
        raise LoadRefused(f"object name collision: {name!r} already in "
                          f"the scene (naming is the caller's hygiene)")

    acts_before = {a.name for a in bpy.data.actions}
    obs_before = {o.name for o in bpy.data.objects}
    bpy.ops.import_scene.fbx(filepath=path)
    new_obs = [o for o in bpy.data.objects if o.name not in obs_before]
    new_acts = [a for a in bpy.data.actions if a.name not in acts_before]

    arm = next((o for o in new_obs if o.type == 'ARMATURE'), None)
    if arm is None:
        raise LoadRefused(f"{key}: no armature in the import "
                          f"({[o.name for o in new_obs]})")
    mesh = next((o for o in new_obs
                 if o.type == 'MESH' and o.find_armature() is not None),
                None)
    # stray-object law (the UAL Icosphere class): DELETE with a report
    strays = [o for o in new_obs if o not in (arm, mesh)]
    for ob in strays:
        bpy.data.objects.remove(ob, do_unlink=True)

    rep = wrapper_rig.wrap(arm, name, scale=scale, mesh=mesh,
                           probe_bone="Foot.L")
    arm, mesh, root = rep["armature"], rep["mesh"], rep["root"]

    # loader policy (the UAL pattern): the importer leaves a LIVE
    # action slot (first pool action auto-assigned) — clear it: the
    # caller's bind owns slot assignment (fresh-bake law). The action
    # datablocks stay in the pool.
    ad = arm.animation_data
    rep["import_slot_cleared"] = None
    if ad is not None and ad.action is not None:
        rep["import_slot_cleared"] = ad.action.name
        ad.action = None

    # pool: THIS import's actions, keys = last pipe segment minus the
    # gender prefix (D2b). Duplicate stripped keys collide loudly —
    # one import carries 11 distinct actions by contract.
    pool = {}
    for a in new_acts:
        tail = a.name.split("|")[-1]
        for pre in GENDER_PREFIX:
            if tail.startswith(pre):
                tail = tail[len(pre):]
                break
        if tail in pool:
            raise LoadRefused(
                f"pool key collision {tail!r} on import {name!r} — "
                f"the 11-action contract changed, re-probe")
        pool[tail] = a
    if len(pool) != ACTION_CENSUS:
        raise LoadRefused(
            f"{key}: expected {ACTION_CENSUS} actions, import diff "
            f"yielded {len(pool)} ({sorted(pool)}) — re-probe")

    audit(rep, pool)
    return {"arm": arm, "mesh": mesh, "root": root, "pool": pool,
            "actions": sorted(pool), "probe": rep,
            "import_slot_cleared": rep.get("import_slot_cleared"),
            "height": measured_height(mesh),
            "feet_z": measured_feet(mesh)}


def measured_height(mesh):
    """World height of the skinned mesh (the honest box — the armature
    bone-box lies below ground via IK helpers). Depsgraph-fresh: the
    wrapper MPI is matrix data, matrix_world is STALE until
    view_layer.update() (the F2B-21 class)."""
    if mesh is None:
        return None
    bpy.context.view_layer.update()
    mw = mesh.matrix_world
    zs = [(mw @ v.co).z for v in mesh.data.vertices]
    return round(max(zs) - min(zs), 4)


def measured_feet(mesh):
    if mesh is None:
        return None
    bpy.context.view_layer.update()
    mw = mesh.matrix_world
    return round(min((mw @ v.co).z for v in mesh.data.vertices), 4)


def audit(rep, pool):
    """The D2 audit gates — RECORD-AND-WARN posture for rig-authoring
    choices, FAIL for contract violations (bone census, height band,
    feet band)."""
    arm = rep["armature"]
    n = len(arm.data.bones)
    if n != BONE_CENSUS:
        raise LoadRefused(f"bone census {n} != {BONE_CENSUS} — the "
                          f"family contract changed, re-probe")
    modes = sorted({pb.rotation_mode for pb in arm.pose.bones})
    for m in modes:
        if m != 'QUATERNION':
            print(f"[quat-loader] WARN: pose bones in {m} mode — "
                  f"the s18 law says non-QUATERNION channels are "
                  f"silently inert under quaternion-family keying; "
                  f"fixing modes is a per-rig DECISION, not silent",
                  flush=True)
    h = measured_height(rep["mesh"])
    if h is not None and not (HEIGHT_MIN <= h <= HEIGHT_MAX):
        raise LoadRefused(
            f"post-rescale height {h} m outside [{HEIGHT_MIN}, "
            f"{HEIGHT_MAX}] — UNIT_RESCALE drifted from the measured "
            f"raw heights, re-pin (see module docstring)")
    fz = measured_feet(rep["mesh"])
    if fz is not None and abs(fz) > FEET_BAND:
        raise LoadRefused(
            f"feet z {fz} m outside the ±{FEET_BAND} ground band — "
            f"the family stopped being feet-origin, re-probe")


def recolor(rep, rgb, roughness=None):
    """Single material-slot sweep (the UAL gauntlet R4 law): every slot
    of the loader's mesh via Principled Base Color + viewport
    diffuse_color (workbench + glTF stay in sync)."""
    mesh = rep["mesh"]
    for slot in mesh.material_slots:
        mat = slot.material
        if mat is None:
            continue
        if mat.use_nodes:
            bsdf = mat.node_tree.nodes.get("Principled BSDF")
            if bsdf is not None:
                bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
                if roughness is not None:
                    try:
                        bsdf.inputs["Roughness"].default_value = roughness
                    except KeyError:
                        pass
        mat.diffuse_color = (*rgb, 1.0)
    return rep
