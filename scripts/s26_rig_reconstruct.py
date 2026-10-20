#!/usr/bin/env python3
"""s26_rig_reconstruct.py — reconstruct x_bot.fbx from a staged scene.glb.

DESIGN_world_retune_s26 D2 [A1/A2/A5/A13]. RH-3d-assets is unreachable
(the beulahkemp PAT died with the wiped sandbox); the staged packages
carry 102-136 BOUND rig assemblies each. This extracts ONE assembly,
restores template space, clears the film tints, and exports the FBX the
crowd family serves. Run inside Blender via blrun.sh:

  ./scripts/blrun.sh --background --factory-startup \
    --python scripts/s26_rig_reconstruct.py -- \
    --glb /home/z/lab/previz-review/public/packages/tform_3/scene.glb \
    --out vendor/rh_rig/x_bot_reconstructed.fbx

THE ROUND-TRIP LAW (measured s26): the FBX export/import pair rescales
geometry by a non-obvious factor (first runs: 2.051 -> 0.0604 regardless
of apply_scale_options) — so the export step is a MEASURED LOOP: export
-> fresh re-import -> verify the world span -> correct -> repeat (max
3). No FBX-unit theory ships; the file that lands is the file that
measured 2.051 at import.

Acceptance (G1-G7) lives in scripts/s26_rig_accept.py — THIS script only
reconstructs + prints the measured numbers.
"""
import argparse
import hashlib
import os
import sys

import bpy
from mathutils import Vector

TARGET_HEIGHT = 2.051          # RIG_HEIGHT["rh_xbot"] (the s22 receipt)
NEUTRAL = (0.65, 0.65, 0.65)   # G7: no film tint may leak


def _P(*a):
    print("[recon]", *a, flush=True)


def _bake_armature_matrix(arm):
    """THE MEASURED ARMATURE-APPLY LAW (s26 probe): transform_apply on an
    ARMATURE resets the object scale to 1 WITHOUT baking the data —
    silent destruction. All armature transforms bake via edit-bone
    surgery: data' = matrix_world @ data, object -> identity."""
    from mathutils import Matrix
    M = arm.matrix_world.copy()
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='EDIT')
    for eb in arm.data.edit_bones:
        eb.head = M @ eb.head
        eb.tail = M @ eb.tail
    bpy.ops.object.mode_set(mode='OBJECT')
    arm.matrix_world = Matrix.Identity(4)
    bpy.context.view_layer.update()


def _reconstruct_scene(glb, pick, clip_fbx, extra=1.0):
    """Deterministic: import the GLB, isolate the assembly, restore
    template space (x extra), merge seams, neutral mats. Returns
    (arm, meshes, info dict). Factory-resets first — safe to loop."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=glb)
    objs = list(bpy.data.objects)

    arm = None
    for o in objs:
        if (o.type == 'ARMATURE'
                and o.name.startswith(pick)
                and any('mixamorig' in b.name for b in o.data.bones)):
            arm = o
            break
    if arm is None:
        raise SystemExit(f"[recon] no mixamorig armature prefixed "
                         f"{pick!r} in the GLB")
    bound = [o for o in objs if o.type == 'MESH'
             for m in o.modifiers
             if m.type == 'ARMATURE' and m.object == arm]
    if len(bound) != 2:
        raise SystemExit(f"[recon] expected 2 skinned meshes on "
                         f"{arm.name}, got {len(bound)}")
    _P(f"assembly: {arm.name} bones={len(arm.data.bones)} "
       f"meshes={[(m.name, len(m.data.vertices)) for m in bound]}")

    keep = list(bound)
    for o in bound:
        o.parent = None
    for o in list(bpy.data.objects):
        if o not in keep:
            bpy.data.objects.remove(o, do_unlink=True)

    # meshes: transform_apply is mesh-safe — bake the wrapper chain,
    # then restore template scale from the MESH span (the body IS the
    # ground truth; the rec armature is gone)
    bpy.ops.object.select_all(action='DESELECT')
    for o in bound:
        o.select_set(True)
    bpy.context.view_layer.objects.active = bound[0]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.context.view_layer.update()
    xs, ys, zs = [], [], []
    for o in bound:
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            xs.append(w.x); ys.append(w.y); zs.append(w.z)
    span = max(zs) - min(zs)
    _P(f"post-apply raw mesh bbox z-span: {span:.4f} "
       f"(target {TARGET_HEIGHT})")
    k = TARGET_HEIGHT / span * extra
    for o in bound:
        o.scale = (k, k, k)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.context.view_layer.update()
    zs = []
    for o in bound:
        for c in o.bound_box:
            zs.append((o.matrix_world @ Vector(c)).z)
    span2 = max(zs) - min(zs)
    _P(f"restored mesh bbox z-span (x{extra:.4f}): {span2:.4f}")

    # drop the staged GLB's imported actions BEFORE the re-skin (the
    # clip import below brings its own action, which we also drop —
    # the served template carries NO animation)
    for ac in list(bpy.data.actions):
        bpy.data.actions.remove(ac)

    # merge the glTF seam-split duplicates (round-trip artifacts)
    import bmesh
    for m in bound:
        pre = len(m.data.vertices)
        bm = bmesh.new()
        bm.from_mesh(m.data)
        bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-6)
        bm.to_mesh(m.data)
        bm.free()
        m.data.update()
        _P(f"merge-by-distance {m.name}: {pre} -> {len(m.data.vertices)}")

    # ---- THE RE-SKIN (the s26 frame-drift fix) -------------------------
    # Measured (s26 skel_compare2): the GLB import inverted the
    # bone-chain direction convention (median 172.6-deg direction flip,
    # local frames preserved except the Hips root at ~175-deg) — the
    # wrapper's facing contest fails and the rig bakes zero-bob. The
    # clip's own skeleton carries the production frame convention, so
    # the meshes RE-SKIN onto it: fit the clip skeleton to this
    # assembly (hips-align + span-scale + optional 180-deg Z — the
    # T-pose is left-right symmetric so the fit is near-exact), then
    # parent the meshes to it. Weights transfer 1:1 by bone name.
    before2 = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=clip_fbx)
    arm_clip = [o for o in bpy.data.objects if o.type == 'ARMATURE'
                and o not in before2][-1]
    for o in list(bpy.data.objects):
        if o not in before2 and o is not arm_clip:
            bpy.data.objects.remove(o, do_unlink=True)   # clip's extras
    for ac in list(bpy.data.actions):
        bpy.data.actions.remove(ac)
    # THE OBJECT-LEVEL FIT LAW (the s26 bake-twist find): the clip
    # armature imports with object matrix Rot(90X) @ Scale(0.01) — its
    # DATA frames are the production convention ONLY under that object
    # matrix. NEVER bake it (baking rotated every frame — the roll does
    # not follow a 90-deg data rotation, and the facing contest read
    # fwd z=-0.888). The fit is OBJECT-LEVEL: multiply the object scale,
    # translate the object — frames untouched, exactly how production
    # served the original FBX template.

    def _span(arm):
        zs = [(arm.matrix_world @ Vector(c)).z for c in arm.bound_box]
        return max(zs) - min(zs)

    def _hips_w(arm):
        return arm.matrix_world @ Vector(
            arm.data.bones['mixamorig:Hips'].head_local)

    # fit the clip skeleton to the MESH (the body is the ground truth):
    # span-scale + bottom-center align; sanity = the skeleton's feet
    # heads land inside the mesh's foot band and its hips inside the
    # mesh. (The joints need not coincide exactly — the armature
    # modifier is identity at rest and the weights are name-keyed; the
    # REAL proof is G4's motion gates + G5 + the eye pass.)
    span_rec = span2
    base = tuple(arm_clip.scale)
    k_fit = span_rec / _span(arm_clip)
    arm_clip.scale = tuple(s * k_fit for s in base)
    bpy.context.view_layer.update()
    mzs, mxs, mys = [], [], []
    for o in bound:
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            mzs.append(w.z); mxs.append(w.x); mys.append(w.y)
    bot = Vector((sum(mxs) / len(mxs), sum(mys) / len(mys), min(mzs)))
    bzs = [(arm_clip.matrix_world @ Vector(c)).z
           for c in arm_clip.bound_box]
    bxs = [(arm_clip.matrix_world @ Vector(c)).x
           for c in arm_clip.bound_box]
    bys = [(arm_clip.matrix_world @ Vector(c)).y
           for c in arm_clip.bound_box]
    botc = Vector((sum(bxs) / len(bxs), sum(bys) / len(bys), min(bzs)))
    arm_clip.location += (bot - botc)
    bpy.context.view_layer.update()
    clip_hips = arm_clip.matrix_world @ Vector(
        arm_clip.data.bones['mixamorig:Hips'].head_local)
    clip_foot = min((arm_clip.matrix_world @ Vector(
        arm_clip.data.bones[n].head_local)).z
        for n in ('mixamorig:LeftFoot', 'mixamorig:RightFoot'))
    _P(f"re-skin fit: k={k_fit:.4f} clip_hips_z={clip_hips.z:.3f} "
       f"(mesh z {min(mzs):.3f}..{max(mzs):.3f}) "
       f"clip_feet_z={clip_foot:.3f}")
    if not (min(mzs) - 0.1 < clip_foot < max(mzs)):
        raise SystemExit("[recon] skeleton feet outside the mesh band")

    # re-parent the meshes onto the fitted clip skeleton
    for m in bound:
        for md in m.modifiers:
            if md.type == 'ARMATURE':
                md.object = arm_clip
        m.parent = arm_clip
    arm = arm_clip
    _P(f"re-skinned onto {arm_clip.name} (the clip's production frames)")

    bound.sort(key=lambda m: len(m.data.vertices))
    bound[0].name = "Beta_Joints"
    bound[0].data.name = "Beta_Joints"
    bound[1].name = "Beta_Surface"
    bound[1].data.name = "Beta_Surface"

    # G7: clear the film's per-group tint materials -> ONE shared
    # neutral (two same-name materials made KIT.RigNeutral.001 — the
    # accept gate reads the SET of names)
    mat = bpy.data.materials.new("KIT.RigNeutral")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*NEUTRAL, 1.0)
    for m in bound:
        m.data.materials.clear()
        m.data.materials.append(mat)


    names = sorted(m.name for m in bound)
    assert names == ["Beta_Joints", "Beta_Surface"], names
    bones = [b.name for b in arm.data.bones]
    assert sum(1 for n in bones if n.startswith("mixamorig:")) == 65, \
        f"bone census {sum(1 for n in bones if n.startswith('mixamorig:'))}"
    combined = sum(len(m.data.vertices) for m in bound)
    _P(f"combined verts post-merge: {combined}")
    return keep, arm, combined


def _verify_roundtrip_blend(path):
    """Fresh factory + APPEND; return the armature's world z-span
    (the .blend round trip must be lossless)."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(path, link=False) as (df, dt):
        dt.objects = list(df.objects)
    for ob in dt.objects:
        if ob is not None:
            bpy.context.scene.collection.objects.link(ob)
    arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][-1]
    bpy.context.view_layer.update()
    zs = [(arm.matrix_world @ Vector(c)).z for c in arm.bound_box]
    span = max(zs) - min(zs)
    meshes = [o for o in bpy.data.objects if o.type == 'MESH']
    _P(f"round-trip verify (append): span={span:.4f} "
       f"meshes={[(m.name, len(m.data.vertices)) for m in meshes]}")
    return span


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--glb", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--pick", default="Zed.0001")
    args = ap.parse_args(argv)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    # s26 FRAME-DRIFT LAW (measured): the FBX round trip rotated the
    # reconstruction's bone frames (the wrapper facing contest failed
    # with fwd z=-0.632 and the auto-scan mapped to a zero-bob rig) —
    # the artifact is therefore a LOSSLESS .blend (bpy.data append in
    # prepare_template), not an FBX. The GLB-imported frames ARE the
    # staged rigs' frames = the ORIGINAL template's frames (the staged
    # rigs were bound from it), so no frame reconstruction happens.
    keep, arm, combined = _reconstruct_scene(
        args.glb, args.pick,
        os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     '..', 'vendor', 'rh_clips', 'assets',
                                     'fbx', '2899.fbx')), 1.0)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args.out))
    span = _verify_roundtrip_blend(args.out)
    if abs(span - TARGET_HEIGHT) > 0.02 * TARGET_HEIGHT:
        raise SystemExit(f"[recon] .blend round-trip span {span:.4f} "
                         f"out of band (lossless append expected)")
    sha = hashlib.sha256(open(args.out, 'rb').read()).hexdigest()
    size = os.path.getsize(args.out)
    _P(f"WROTE {args.out} ({size} bytes)")
    _P(f"sha256 {sha}")
    _P(f"DONE combined={combined} roundtrip_span={span:.4f}")


main()
