"""s23_joint_probe.py — D3 mapping-table ground truth (one run).

Full bone lists for the three families + the location-fcurve census on
the gait actions (D3b's location-transfer set) + the rigify53 DEF
census. Prints JPROBE lines. Read-only.
"""
import bpy, os, sys, json

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))


def P(*a):
    print("JPROBE", *a, flush=True)


def bones_of(arm):
    return [b.name for b in arm.data.bones]


def loc_fcurves(act):
    """(data_path, array_index) tuples for location channels."""
    out = []
    try:
        import blender_kit
        fcs = blender_kit.iter_fcurves(act)
    except Exception:
        fcs = act.fcurves
    for fc in fcs:
        if fc.data_path.endswith(".location"):
            out.append((fc.data_path.split('"')[1] if '"' in fc.data_path
                        else fc.data_path, fc.array_index))
    return out


# ---- A. Quaternius male ----
bpy.ops.wm.read_factory_settings(use_empty=True)
qpath = os.path.join(_REPO, "assets", "vendor", "quaternius", "Male_Casual.fbx")
bpy.ops.import_scene.fbx(filepath=qpath)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
P("QUAT_BONES", json.dumps(bones_of(arm)))
walk = next(a for a in bpy.data.actions if a.name.endswith("Man_Walk"))
P("QUAT_WALK_LOCF", json.dumps(sorted(set(n for n, i in loc_fcurves(walk)))))
run = next(a for a in bpy.data.actions if a.name.endswith("Man_Run"))
P("QUAT_RUN_LOCF", json.dumps(sorted(set(n for n, i in loc_fcurves(run)))))
# rest translation z of the hips-class bones (armature data space)
for nm in ("Bone", "Body", "Hips", "Foot.L"):
    b = arm.data.bones.get(nm)
    if b:
        P(f"QUAT_RESTZ {nm}", round(b.matrix_local.translation.z, 4))
P("QUAT_OBJSCALE", tuple(round(v, 4) for v in arm.scale))

# ---- B. UAL mannequin (rigify53) — ONE import via _import_actor ----
bpy.ops.wm.read_factory_settings(use_empty=True)
import assets_ual_actors as ual  # noqa: E402
try:
    rep = ual._import_actor("Driver", ual.ACTOR_SCALE)
    a2 = rep["armature"]
    P("UAL_BONES", json.dumps(bones_of(a2)))
    acts = rep.get("actions") or {}
    P("UAL_POOL_KEYS", json.dumps(sorted(acts.keys())))
    wl = acts.get("Walk_Loop")
    if wl:
        P("UAL_WALK_LOCF", json.dumps(sorted(
            set(n for n, i in loc_fcurves(wl)))))
    for nm in ("DEF-hips", "DEF-spine", "DEF-thigh.L", "DEF-foot.L"):
        b = a2.data.bones.get(nm)
        if b:
            P(f"UAL_RESTZ {nm}", round(b.matrix_local.translation.z, 4))
    P("UAL_OBJSCALE", tuple(round(v, 4) for v in a2.scale))
    P("UAL_FACING", rep.get("facing_sign"))
except Exception as e:  # noqa: BLE001
    import traceback
    P("UAL_ERROR", repr(e), traceback.format_exc(limit=3))

# ---- C. blender_kit write-path helper ----
try:
    import blender_kit
    import inspect
    P("FCURVES_NEW", inspect.signature(blender_kit.fcurves_new))
    P("FCURVES_NEW_DOC", (blender_kit.fcurves_new.__doc__ or "")[:400])
except Exception as e:  # noqa: BLE001
    P("FCURVES_NEW_ERROR", repr(e))

P("PROBE-DONE")
