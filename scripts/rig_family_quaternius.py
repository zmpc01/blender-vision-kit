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
import re

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
# P3-8 (the A2a audit): the census is IDENTITY, not just count — a
# renamed-clip 11-pack must not sail. Pinned from the H2 row.
EXPECTED_ACTION_KEYS = frozenset(
    {"Walk", "Idle", "Jump", "Death", "Clapping", "Punch", "Run",
     "RunningJump", "Sitting", "Standing", "SwordSlash"})


class LoadRefused(ValueError):
    """assets_quaternius refuses — fail-closed loader law."""


def load(key, name, scale=UNIT_RESCALE):
    """One FBX import -> discovery -> stray purge -> wrapper -> pool.

    Returns rep = {"arm", "mesh", "root", "pool", "actions", "probe",
    "height", "feet_z"} where pool maps stripped action keys to Action
    datablocks of THIS import (acts-diff law, D2b).

    The A2a audit law: every refusal AFTER the import ROLLS BACK the
    import (objects + actions) — a leaked rig used to trap the retry
    behind a wrapper name-collision error that blamed the wrong layer.
    """
    path = FBX_FILES.get(key)
    if not path or not os.path.isfile(path):
        raise LoadRefused(f"unknown key {key!r} (male|female) or missing "
                          f"FBX at {path}")
    if scale <= 0:
        raise LoadRefused(f"scale {scale!r} must be > 0 (a sign-blind "
                          f"rescale passes the height gate and wrecks the "
                          f"feet band — refuse before importing)")
    # P2-5: the DERIVED names must be free too (a pre-existing
    # 'X.Body' silently renamed the mesh to 'X.Body.001' and every
    # name-keyed downstream contract drifted)
    for derived in (name, f"{name}.Rig", f"{name}.Root", f"{name}.Body"):
        if derived in bpy.data.objects:
            raise LoadRefused(f"object name collision: {derived!r} already "
                              f"in the scene (the loader renames to "
                              f"<name>.Rig/.Root/.Body — all four must be "
                              f"free)")

    acts_before = {a.name for a in bpy.data.actions}
    obs_before = {o.name for o in bpy.data.objects}
    bpy.ops.import_scene.fbx(filepath=path)
    new_obs = [o for o in bpy.data.objects if o.name not in obs_before]
    new_acts = [a for a in bpy.data.actions if a.name not in acts_before]

    def _rollback(exc):
        """Remove EVERYTHING this import brought, then re-raise (the
        P1-1 law: enforcement must not cost the session). The object
        diff is RE-COMPUTED at rollback time: the wrapper's Root empty
        (created post-import) is not in the import diff."""
        now_new = [o for o in bpy.data.objects
                   if o.name not in obs_before]
        for ob in list(now_new) + list(new_obs):
            try:
                bpy.data.objects.remove(ob, do_unlink=True)
            except Exception:
                pass
        for a in list(new_acts):
            try:
                bpy.data.actions.remove(a)
            except Exception:
                pass
        return exc

    try:
        arm = next((o for o in new_obs if o.type == 'ARMATURE'), None)
        if arm is None:
            raise LoadRefused(f"{key}: no armature in the import "
                              f"({[o.name for o in new_obs]})")
        arms = [o for o in new_obs if o.type == 'ARMATURE']
        if len(arms) > 1:
            raise LoadRefused(f"{key}: ambiguous import — {len(arms)} "
                              f"armatures {[o.name for o in arms]}; the "
                              f"family contract is ONE rig per FBX")
        # P1-3: the skinned mesh is part of the family CONTRACT — a
        # mesh skinned to a DIFFERENT armature (or none) used to slip
        # through with both world gates silently vacated
        mesh = next((o for o in new_obs
                     if o.type == 'MESH' and o.find_armature() is arm),
                    None)
        if mesh is None:
            mesh_info = [
                (o.name,
                 (o.find_armature().name if o.find_armature() else None))
                for o in new_obs if o.type == 'MESH']
            raise LoadRefused(
                f"{key}: no mesh skinned to the imported armature "
                f"({mesh_info}) — the family contract is a skinned "
                f"body; refusing before the height/feet gates can "
                f"silently skip")
        # stray-object law (the UAL Icosphere class): DELETE with a
        # report (the A2a P2-4 fold: the comment promised a report the
        # code never printed)
        strays = [o for o in new_obs if o not in (arm, mesh)]
        for ob in strays:
            print(f"[quat-loader] stray removed: {ob.name!r} "
                  f"({ob.type})", flush=True)
            bpy.data.objects.remove(ob, do_unlink=True)

        # the film lane's canonical wrapper (review r1): meshes discovered
        # internally (plural rep), renames are the caller's hygiene, D1b
        # scale!=1 with an unparented skinned mesh REFUSES (the quaternius
        # meshes are armature-parented at import — rides the rescale)
        rep = wrapper_rig.wrap(arm, name, scale=scale,
                               facing_probe_bone="Foot.L")
        arm, root = rep["armature"], rep["root"]
        mesh = rep["meshes"][0] if rep["meshes"] else None
        arm.name = f"{name}.Rig"
        if mesh is not None:
            mesh.name = f"{name}.Body"

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
        # gender prefix (D2b). The DATABLOCK dedup suffix (.001 on the
        # second same-family import in one session) is stripped too —
        # the P1-2 law: import #2 must map the SAME 11 clean keys onto
        # ITS OWN .001 datablocks, or the motion-lab pattern
        # pool["Walk"] KeyErrors downstream.
        pool = {}
        for a in new_acts:
            tail = re.sub(r"\.\d{3}$", "", a.name.split("|")[-1])
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
        missing = EXPECTED_ACTION_KEYS - set(pool)
        if missing:
            raise LoadRefused(f"{key}: action-key identity drift — missing "
                              f"{sorted(missing)} (got {sorted(pool)})")
        audit(rep, pool, scale=scale)
    except LoadRefused as e:
        raise _rollback(e)
    except Exception as e:                       # noqa: BLE001
        raise _rollback(e)
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


def audit(rep, pool, scale=None):
    """The D2 audit gates — RECORD-AND-WARN posture for rig-authoring
    choices, FAIL for contract violations (bone census, height band,
    feet band). The A2a law: a MISSING mesh is a contract violation,
    not a skip (the height/feet gates used to vacate silently); the
    height refusal names the CALLER's scale when a non-default scale
    was chosen ("UNIT_RESCALE drifted" lied about who chose it)."""
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
    mesh0 = rep["meshes"][0] if rep["meshes"] else None
    h = measured_height(mesh0)
    if h is None:
        raise LoadRefused("audit: no mesh to measure — the height/feet "
                          "gates cannot pass vacuously (P1-3)")
    if not (HEIGHT_MIN <= h <= HEIGHT_MAX):
        if scale is not None and scale != UNIT_RESCALE:
            raise LoadRefused(
                f"post-rescale height {h} m outside [{HEIGHT_MIN}, "
                f"{HEIGHT_MAX}] with the CALLER-SUPPLIED scale={scale} "
                f"(the family default is {UNIT_RESCALE}) — the caller's "
                f"scale is the variable here, not UNIT_RESCALE")
        raise LoadRefused(
            f"post-rescale height {h} m outside [{HEIGHT_MIN}, "
            f"{HEIGHT_MAX}] — UNIT_RESCALE drifted from the measured "
            f"raw heights, re-pin (see module docstring)")
    fz = measured_feet(mesh0)
    if fz is None or abs(fz) > FEET_BAND:
        raise LoadRefused(
            f"feet z {fz} m outside the ±{FEET_BAND} ground band — "
            f"the family stopped being feet-origin, re-probe")


def recolor(rep, rgb, roughness=None):
    """Single material-slot sweep (the UAL gauntlet R4 law): every slot
    of the loader's mesh via Principled Base Color + viewport
    diffuse_color (workbench + glTF stay in sync)."""
    # accepts BOTH dict shapes: the loader's return ("mesh") and the
    # canonical wrap rep ("meshes") — the H2 sweep caught the silent
    # no-op (a shape mismatch must not skip the sweep silently)
    mesh = (rep.get("mesh") if rep.get("mesh") is not None
            else (rep["meshes"][0] if rep.get("meshes") else None))
    if mesh is None:
        raise LoadRefused("recolor: no mesh in the rep dict")
    for slot in mesh.material_slots:
        mat = slot.material
        if mat is None:
            continue
        # ADR-tracked shim (5.2 deprecation-warns on raw use_nodes —
        # Blender 6.0 removal already announced); idempotent
        from blender_kit import ensure_use_nodes
        ensure_use_nodes(mat)
        # FBX imports name the bsdf node differently than glTF —
        # find by TYPE, never by name (the H2 sweep caught it)
        bsdf = next((n for n in mat.node_tree.nodes
                     if n.type == 'BSDF_PRINCIPLED'), None)
        if bsdf is not None:
            bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
            if roughness is not None:
                try:
                    bsdf.inputs["Roughness"].default_value = roughness
                except KeyError:
                    print("[quat-loader] WARN: no Roughness socket on "
                          "this material — the roughness arg is a "
                          "silent no-op otherwise (A2a P3-9)", flush=True)
        mat.diffuse_color = (*rgb, 1.0)
    return rep
