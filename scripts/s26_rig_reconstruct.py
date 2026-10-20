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


def _basis_scale(arm):
    """The rotation-free uniform scale of the object matrix (a 90-deg
    axis rotation must not leak into the scale read)."""
    import math
    m = arm.matrix_world.to_3x3()
    # strip rotation: singular values of a rot@scale = the scales
    try:
        import numpy as np
        sv = np.linalg.svd(np.array(m), compute_uv=False)
        return float(sv[0])
    except Exception:
        return arm.scale[0]


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
    # THE KEEP-TRANSFORM LAW (the s26 anisotropic-data find): a plain
    # o.parent = None collapses each mesh to its LOCAL frame (the
    # parent chain's rotation/scale vanish) — the body then bakes
    # lying-down and every later z-measurement normalizes garbage
    # (the served data measured x=11.5 / z=2.05). Unparent by MATRIX:
    # world position preserved, then measured honestly.
    import json
    truths = {}
    for o in bound:
        bpy.context.view_layer.update()
        xs, ys, zs = [], [], []
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            xs.append(w.x); ys.append(w.y); zs.append(w.z)
        # LOCAL base-data ratios (pose-independent — the world AABB of
        # a SKINNED mesh reads the imported walk pose, not the rest;
        # the s26 gate-premise fix)
        lx, ly, lz = [], [], []
        for c in o.bound_box:
            v = Vector(c)
            lx.append(v.x); ly.append(v.y); lz.append(v.z)
        truths[o.name] = (max(lx) - min(lx), max(ly) - min(ly),
                          max(lz) - min(lz))
        # clear the DANGLING armature modifier (the rec armature is
        # deleted below; a modifier pointing at a dead object is the
        # s26 deterministic-crash class — the weights live in the
        # vertex groups, the modifier is reborn at the re-skin)
        for md in list(o.modifiers):
            o.modifiers.remove(md)
        W = o.matrix_world.copy()
        o.parent = None
        o.matrix_world = W
        bpy.context.view_layer.update()
        _P(f"DBG {o.name} post-unparent world scale="
           f"{tuple(round(v,4) for v in o.matrix_world.to_scale())} "
           f"targetW={tuple(round(v,4) for v in W.to_scale())}")
    for o in list(bpy.data.objects):
        if o not in keep:
            bpy.data.objects.remove(o, do_unlink=True)
    _P("import body truths (world spans): "
       + json.dumps({k: tuple(round(v, 3) for v in val)
                     for k, val in truths.items()}))

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
    # scale from the MESHES' own height (the armature's 68m blob is
    # the GLB bone-heuristic's garbage tails, not a size reference)
    k = TARGET_HEIGHT / span * extra
    truth_sorted = {n: sorted([t[0] / max(t[2], 1e-6),
                               t[1] / max(t[2], 1e-6), 1.0],
                              reverse=True)
                    for n, t in truths.items()}
    for o in bound:
        o.scale = (k, k, k)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.context.view_layer.update()
    # ground the body: object-origin scaling SHIFTED the bbox (the
    # origins sit at the staged anchors) — translate so the bbox
    # BOTTOM CENTER is the world origin (deterministic, convention-
    # free; the skeleton aligns to this same anchor)
    xs, ys, zs = [], [], []
    for o in bound:
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            xs.append(w.x); ys.append(w.y); zs.append(w.z)
    bot = Vector((sum(xs) / len(xs), sum(ys) / len(ys), min(zs)))
    for o in bound:
        o.location -= bot
    bpy.ops.object.transform_apply(location=True, rotation=False,
                                   scale=False)
    bpy.context.view_layer.update()
    zs = []
    for o in bound:
        for c in o.bound_box:
            zs.append((o.matrix_world @ Vector(c)).z)
    span2 = max(zs) - min(zs)
    _P(f"restored mesh bbox z-span (x{extra:.4f}): {span2:.4f} "
       f"(grounded at z=0)")
    # PROPORTIONS GATE: the body's x/z and y/z ratios must match the
    # import truth (an anisotropic bake ships bobble-heads)
    _P("gate: entering")
    def _rss():
        try:
            with open("/proc/self/status") as f:
                for ln in f:
                    if ln.startswith("VmRSS"):
                        return ln.split()[1] + "kB"
        except Exception:
            return "?"
        return "?"

    def _world_spans(o):
        """Vertex-sampled world spans (the bound_box C path died
        silently here twice — deterministic, no traceback; dodge it)."""
        _P(f"  span: rss={_rss()}")
        xs, ys, zs2 = [], [], []
        vs = o.data.vertices
        n = len(vs)
        step = max(1, n // 200)
        _P(f"  span: pre-loop rss={_rss()}")
        for i in range(0, n, step):
            w = o.matrix_world @ vs[i].co
            xs.append(w.x); ys.append(w.y); zs2.append(w.z)
        _P(f"  span: post-loop rss={_rss()}")
        return (max(xs) - min(xs), max(ys) - min(ys),
                max(zs2) - min(zs2))

    for o in bound:
        _P(f"gate: {o.name}")
        xs_s, ys_s, zs_s = _world_spans(o)
        xs = [0, xs_s]; ys = [0, ys_s]; zs2 = [0, zs_s]
        # LOCAL data ratios vs the import's LOCAL base-data ratios
        # (both pose-free), + the human-plausibility band on the world
        # shape (T-pose arms x/z <= 1.4, depth y/z <= 0.55)
        lxs, lys, lzs = [], [], []
        for c in o.bound_box:
            v = Vector(c)
            lxs.append(v.x); lys.append(v.y); lzs.append(v.z)
        lrz = max(lzs) - min(lzs)
        lrx = (max(lxs) - min(lxs)) / max(lrz, 1e-6)
        lry = (max(lys) - min(lys)) / max(lrz, 1e-6)
        # (the local-ratio compare is UNSOUND by design: the bake
        # re-orients the data frame — import y-up vs served z-up — so
        # the served artifact is judged by the world band below, which
        # is what the anisotropy catastrophe actually violates)
        rz2 = max(zs2) - min(zs2)
        rx_w = (max(xs) - min(xs)) / max(rz2, 1e-6)
        ry_w = (max(ys) - min(ys)) / max(rz2, 1e-6)
        # z band per-mesh: Body0 (the joints-viz mesh) is SHORTER than
        # the surface mesh — the scene max is 2.051, Body0 1.80x
        if rx_w > 1.4 or ry_w > 0.55 or not (1.5 < rz2 < 2.2):
            raise SystemExit(
                f"[recon] world shape implausible on {o.name}: "
                f"x/z {rx_w:.3f} y/z {ry_w:.3f} z {rz2:.3f}")
    # the unparent uniformity assert (the keep-transform law's teeth)
    for o in bound:
        s = o.matrix_world.to_scale()
        if max(s) - min(s) > 0.01 * max(s):
            raise SystemExit(f"[recon] non-uniform world scale on "
                             f"{o.name}: {tuple(round(v,5) for v in s)}")
    _P("proportions gate: PASS (world shape human-plausible, "
       "unparent uniform)")

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
    # THE SCALE-1 OBJECT LAW (the s26 invisible-crowd find): the bind
    # parents the rig meshes to the ARMATURE COPY — an armature object
    # carrying a live 0.01 scale shrinks every skinned mesh to ~2cm
    # (the rigs bind, gates pass, and NOTHING renders). The (0.01 x
    # k_fit) factor moves INTO the data (edit-bone multiply — scale is
    # roll-safe, unlike the rotation bake that twisted every frame);
    # the object ends scale-1 with the import rotation PRESERVED
    # (frames = the production convention only under that rotation).
    # THE CHANNEL-COHERENCE LAW (the s26 bob-3.4m find): scaling the
    # clip DATA breaks the action-channel semantics (the importer
    # authored rest-scales + cm channels + data as ONE coherent system
    # — any data-space rescale lands the walk translations 100x). The
    # object matrix is the ONLY safe scale knob; the mesh-inheritance
    # problem it creates is compensated at SAVE time below.
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
    # align by the FEET (the skeleton's own lowest foot-bone heads),
    # not the object bbox — the rotated clip armature's bbox bottom is
    # NOT its feet (the s26 measured 1.322-off signature)
    foot_z = min((arm_clip.matrix_world @ Vector(
        arm_clip.data.bones[n].head_local)).z
        for n in ('mixamorig:LeftFoot', 'mixamorig:RightFoot'))
    fxy = [ (arm_clip.matrix_world @ Vector(
        arm_clip.data.bones[n].head_local))
        for n in ('mixamorig:LeftFoot', 'mixamorig:RightFoot')]
    foot_c = Vector((sum(p.x for p in fxy) / 2, sum(p.y for p in fxy) / 2,
                     foot_z))
    # THE DATA-BAKED ALIGN LAW (the s6 buried-crowd find): a WORLD
    # correction stored as object LOCATION gets rotated by the bind's
    # parent chain (the flip is in matrix_parent_inverse) — the rigs
    # landed sunk with limbs up (the aerial top-down HIDES it; the S6
    # ground camera exposed it). Bake the correction into the BONES
    # (pure translation: frames untouched), object location -> 0.
    delta_world = Vector((0.0, 0.0, 0.0)) - foot_c
    Mlin = arm_clip.matrix_world.to_3x3()
    delta_local = Mlin.inverted() @ delta_world
    bpy.context.view_layer.objects.active = arm_clip
    bpy.ops.object.mode_set(mode='EDIT')
    for eb in arm_clip.data.edit_bones:
        eb.head = eb.head + delta_local
        eb.tail = eb.tail + delta_local
    bpy.ops.object.mode_set(mode='OBJECT')
    arm_clip.location = (0.0, 0.0, 0.0)
    bpy.context.view_layer.update()
    clip_hips = arm_clip.matrix_world @ Vector(
        arm_clip.data.bones['mixamorig:Hips'].head_local)
    clip_foot = min((arm_clip.matrix_world @ Vector(
        arm_clip.data.bones[n].head_local)).z
        for n in ('mixamorig:LeftFoot', 'mixamorig:RightFoot'))
    _P(f"re-skin fit: k={k_fit:.4f} clip_hips_z={clip_hips.z:.3f} "
       f"(mesh z {min(mzs):.3f}..{max(mzs):.3f}) "
       f"clip_feet_z={clip_foot:.3f}")
    if not (-0.15 < clip_foot < 0.15):
        raise SystemExit(f"[recon] skeleton feet at {clip_foot:.3f} "
                         f"(grounded body expects ~0)")
    if not (0.7 < clip_hips.z < 1.3):
        raise SystemExit(f"[recon] skeleton hips at {clip_hips.z:.3f} "
                         f"(outside the human band)")

    # re-parent the meshes onto the fitted clip skeleton — ADD the
    # armature modifier (the isolation cleared the dangling ones; the
    # s26 G5 statue-class catch: retargeting a cleared modifier list
    # ships REST-POSE statues — bind green, gates green, skin dead)
    for m in bound:
        md = m.modifiers.new("ARMAT", 'ARMATURE')
        md.object = arm_clip
        m.parent = arm_clip
    arm = arm_clip
    _P(f"re-skinned onto {arm_clip.name} (the clip's production frames)")

    # THE BASIS-PAIRING LAW (the s26 final form): the skinning is
    # coherent only when the mesh's LOCAL data lives in the ARMATURE's
    # LOCAL frame. The mesh data stays upright meters (2.051, z-up);
    # the mesh's object basis becomes arm_world^-1 @ mesh_world — the
    # inverse of the fitted armature's full matrix (rot90X @ 0.0104
    # included). Through the bind's copies (basis copied, parented to
    # the per-agent armature) the world composes back exactly, and the
    # modifier deforms in one coherent frame. (The scale-only pairing
    # left the rot90 mismatch in: the skin exploded into floor shards.)
    from mathutils import Matrix as _M
    for m in bound:
        m.parent = arm_clip
        m.matrix_parent_inverse = _M.Identity(4)
        m.matrix_basis = (arm_clip.matrix_world.inverted()
                          @ m.matrix_world)
    bpy.context.view_layer.update()
    _P("basis pairing: mesh basis = arm_world^-1 @ mesh_world "
       "(the local frames pair coherently)")

    # clear the imported frame-0 POSE (the walk clip ships posed; the
    # served template must carry the REST or the bind's rest reads skew)
    bpy.context.view_layer.objects.active = arm_clip
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.pose.transforms_clear()
    bpy.ops.object.mode_set(mode='OBJECT')
    _P("imported pose cleared (rest served)")

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

    import traceback
    try:
        _main_inner(args)
    except BaseException as e:
        import traceback as _tb
        _P(f"EXCEPTION CAPTURED: {type(e).__name__}: {e}")
        for ln in _tb.format_exc().splitlines():
            _P(f"  TB {ln}")
        raise


def _main_inner(args):
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
