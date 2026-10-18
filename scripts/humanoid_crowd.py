"""humanoid_crowd.py — the D6 humanoid crowd layer (cylinder → rigged).

Implements docs/DESIGN_humanoid_crowd.md REV-2. The rig assembly hangs
BELOW the existing commuter-mesh anchor (which goes hide_render=True
and stays the bake2 transform carrier + gate surface — bake2 itself
is UNTOUCHED). Families:

  "rh_xbot"  — RH-3d-assets x_bot (mixamorig:65, DIRECT same-name bind)
               + RH-canvas-animations clips (2899 walk / 2781 idle)
  "ual"      — the vendored UAL mannequin (Rigify-53, 46 actions) via
               assets_ual_actors' _import_actor (principals only)

Motion law (D6-3): WRAP (key times mod cyc into [f0, f0+cyc)) +
CYCLES modifiers (Blender-side loop; the action's frame_range stays
the compact keyed window so the exporter samples only the cycle — the
three.js viewer LoopRepeat provides the web-side loop) + per-agent
phase from the cache PHASE channel + clip selection by the SPEED
channel (stationary -> shared trimmed idle).

Public API:
    crowd_family(name)                       -> family handle (dict)
    prepare_template(fam, ratio)             -> {"arm", "meshes", ...}
    bind_crowd(ctx, fam, group_tint=None)    -> report (gates inside)
    bind_principals(ctx, name_clip_pairs)    -> report (UAL, keyed heroes)
    motion_gates(ctx, sample=5)              -> the s20 two-column law

Every gate is fail-closed (RuntimeError); every report carries numbers
(the s20 lesson — they travel with the strips).
"""
import bpy
import os
from mathutils import Matrix

RH_ASSETS = os.environ.get("RH_ASSETS",
                           "/home/z/lab/RH-3d-assets")
RH_ANIMS = os.environ.get("RH_ANIMS",
                          "/home/z/lab/RH-canvas-animations")

FILM_HEIGHT = 1.75          # the films author commuters at 1.75 m
RIG_HEIGHT = {              # measured (s22_asset_probe receipt)
    "rh_xbot": 2.051,
}
XBOT_MESHES = ("Beta_Joints", "Beta_Surface")
POLY_BAND = (2000, 3500)    # combined verts band (D6-4)
WALK_CLIP = "2899.fbx"      # Male standard walk (38f)
IDLE_CLIP = "2781.fbx"      # Center of gravity shift standby (500f -> trim 64)
IDLE_TRIM = 64
STATIONARY_MPS = 0.05       # the K1 clip-channel threshold


def _fail(msg):
    raise RuntimeError(f"humanoid_crowd: {msg}")


def _P(*a):
    print("HUMANCROWD", *a)


def crowd_family(name):
    if name == "rh_xbot":
        return {
            "name": name,
            "rig": f"{RH_ASSETS}/assets/director/dummy-rigs/x_bot.fbx",
            "walk": f"{RH_ANIMS}/assets/fbx/{WALK_CLIP}",
            "idle": f"{RH_ANIMS}/assets/fbx/{IDLE_CLIP}",
            "prefix": "mixamorig:",
            "probe_bone": "mixamorig:LeftFoot",
            "rig_height": RIG_HEIGHT["rh_xbot"],
            "mesh_names": XBOT_MESHES,
        }
    _fail(f"unknown family {name!r} (have: rh_xbot; ual principals go "
          f"through bind_principals)")


def prepare_template(fam, ratio=0.14):
    """Import + decimate the rig template ONCE. Returns the template
    records (NOT yet instanced). Decimate law: combined verts must
    land in POLY_BAND (catches silent no-op AND collapse)."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=fam["rig"])
    arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'
           and o not in before][-1]
    meshes = [o for o in bpy.data.objects if o.type == 'MESH'
              and o not in before]
    if tuple(sorted(m.name for m in meshes)) != tuple(sorted(fam["mesh_names"])):
        _fail(f"x_bot mesh census drifted: {[m.name for m in meshes]}")
    for m in meshes:
        bpy.context.view_layer.objects.active = m
        md = m.modifiers.new("DEC", 'DECIMATE')
        md.ratio = ratio
        bpy.ops.object.modifier_apply(modifier="DEC")
    combined = sum(len(m.data.vertices) for m in meshes)
    if not (POLY_BAND[0] <= combined <= POLY_BAND[1]):
        _fail(f"decimate landed {combined} verts, band {POLY_BAND} "
              f"(ratio {ratio}) — adjust ratio")
    _P(f"template ready: combined {combined} verts "
       f"({[len(m.data.vertices) for m in meshes]})")
    return {"arm": arm, "meshes": meshes, "combined_verts": combined}


def _wrap_action(base_act, new_name, phase, cyc, f0, f1):
    """WRAP law: copy + in-cycle rotation + CYCLES modifiers."""
    a2 = base_act.copy()
    a2.name = new_name
    shift = (phase % 1.0) * cyc
    for fc in _iter_fcurves(a2):
        for kp in fc.keyframe_points:
            t = f0 + ((kp.co.x - f0 - shift) % cyc)
            kp.co.x = t
        md = fc.modifiers.new('CYCLES')
        md.mode_before = 'NONE'
        md.mode_after = 'REPEAT'
        md.cycles_before = 0
        md.cycles_after = 100000
    return a2


def _iter_fcurves(action):
    """5.x slotted-action iterator (blender_kit when available)."""
    try:
        import blender_kit
        return list(blender_kit.iter_fcurves(action))
    except Exception:
        return list(getattr(action, 'fcurves', []))


def _trim_action(act, keep_frames):
    """Trim an action to its first `keep_frames` (index-DESC removals —
    RNA array refs go stale after each removal)."""
    f0 = act.frame_range[0]
    for fc in _iter_fcurves(act):
        doomed = [i for i, kp in enumerate(fc.keyframe_points)
                  if kp.co.x > f0 + keep_frames]
        for i in reversed(doomed):
            fc.keyframe_points.remove(fc.keyframe_points[i])


def bind_crowd(ctx, fam, group_tint=None, sample_phase_stride=0.37):
    """Bind rig assemblies under the cache anchors.

    ctx: the film scene ctx (needs ctx["crowd_cache"] with n_agents,
    ctx["chars"]["zombies"]["crowd"/"chase"] — the anchors list).
    group_tint: None or {"groups": [(n_agents_in_group, rgba), ...]}
    — per-OBJECT material-slot links (audit P2-3: zero mesh copies;
    one material datablock per group, linked per agent object).

    Gates (fail-closed): anchor count == cache n_agents; bone census
    (clip names ⊆ rig names); wrap-band assert; quaternion modes.
    Returns the report dict (numbers travel).
    """
    import wrapper_rig
    cache = ctx.get("crowd_cache")
    if cache is None:
        _fail("bind_crowd: ctx has no crowd_cache (run load_kit_cache "
              "+ bake_tier2 first)")
    zombies = (ctx.get("chars") or {}).get("zombies")
    anchors = list(zombies["crowd"]) + list(zombies["chase"])
    n = int(cache.n_agents)
    if len(anchors) != n:
        _fail(f"anchors {len(anchors)} != cache n_agents {n}")

    tmpl = prepare_template(fam)
    # the walk clip (import standalone: it brings its own armature —
    # strip it after stealing the action)
    before = set(bpy.data.actions)
    before_ob = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=fam["walk"])
    walk_act = [a for a in bpy.data.actions if a not in before][0]
    for ob in [o for o in bpy.data.objects if o not in before_ob]:
        bpy.data.objects.remove(ob, do_unlink=True)   # the clip's skeleton
    f0, f1 = (int(v) for v in walk_act.frame_range)
    cyc = f1 - f0
    # bone census (the audit's direct-bind law)
    rig_names = {b.name for b in tmpl["arm"].data.bones}
    # the clip action's driven bones
    clip_names = {fc.data_path.split('"')[1] for fc in _iter_fcurves(walk_act)
                  if '"' in fc.data_path}
    missing = clip_names - rig_names
    if missing:
        _fail(f"clip bones not on rig ({len(missing)}): {sorted(missing)[:6]}")
    # phase source: the cache phase channel (K1) when present, else the
    # deterministic ordinal stride
    phases = _cache_phases(ctx, n)

    # the shared trimmed idle (one bpy action for ALL parked agents)
    before = set(bpy.data.actions)
    before_ob = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=fam["idle"])
    idle_act = [a for a in bpy.data.actions if a not in before][0]
    for ob in [o for o in bpy.data.objects if o not in before_ob]:
        bpy.data.objects.remove(ob, do_unlink=True)
    _trim_action(idle_act, IDLE_TRIM)
    idle_names = {fc.data_path.split('"')[1] for fc in _iter_fcurves(idle_act)
                  if '"' in fc.data_path}
    missing_i = idle_names - rig_names
    if missing_i:
        _fail(f"idle bones not on rig ({len(missing_i)}): "
              f"{sorted(missing_i)[:6]}")

    speeds = _cache_speeds(ctx, n)
    group_mats = _make_group_materials(group_tint)

    reps = []
    n_walk = n_idle = 0
    for i, anchor in enumerate(anchors):
        # the anchor stays a MESH (D6-2); it goes render-hidden
        anchor.hide_render = True
        wrapper = wrapper_rig.wrap(tmpl["arm"].copy(),
                                   f"{anchor.name}.Hum", scale=1.0,
                                   facing_probe_bone=fam["probe_bone"])
        wrapper["root"].parent = anchor
        # rescale lives in the wrapper MPI law — wrap() used scale=1.0;
        # apply the film-height rescale as a wrapper child-of scale now
        s = FILM_HEIGHT / fam["rig_height"]
        wrapper["armature"].matrix_parent_inverse = \
            wrapper["armature"].matrix_parent_inverse @ Matrix.Scale(s, 4)
        # skinned meshes: instance linked copies under THIS armature
        for j, tm in enumerate(tmpl["meshes"]):
            me = tm.copy()
            me.name = f"{anchor.name}.Body{j}"
            me.parent = wrapper["armature"]
            bpy.context.scene.collection.objects.link(me)
            if group_mats:
                _tint_object(me, group_mats, i, len(anchors))
        # the action: walk (per-agent wrapped phase) or shared idle
        if speeds and speeds[i] > STATIONARY_MPS:
            a2 = _wrap_action(walk_act, f"walk_{i:03d}", phases[i], cyc, f0, f1)
            n_walk += 1
        else:
            a2 = idle_act
            n_idle += 1
        wrapper["armature"].animation_data_create()
        wrapper["armature"].animation_data.action = a2
        # wrap-band gate on the per-agent actions
        if a2 is not idle_act:
            lo, hi = a2.frame_range
            if lo < f0 - 1e-4 or hi >= f0 + cyc + 1e-4:
                _fail(f"wrap-band violated on agent {i}: "
                      f"{lo:.2f}..{hi:.2f} not inside [{f0},{f0 + cyc})")
        reps.append({"anchor": anchor, **wrapper})
    # quaternion modes census (the s18 law) on the template rig
    bad = [b.name for b in tmpl["arm"].data.bones
           if b.rotation_mode and b.rotation_mode != 'QUATERNION'
           and len(b.name) > 0]
    if bad:
        _P(f"WARN quaternion modes: {len(bad)} bones non-QUATERNION "
           f"(first: {bad[:3]}) — the s18 law says the loader RECORDS "
           f"and warns, fixing is per-rig")
    _P(f"bound {n} rigs: {n_walk} walk / {n_idle} idle; "
       f"combined {tmpl['combined_verts']} verts/agent")
    return {"n": n, "n_walk": n_walk, "n_idle": n_idle,
            "verts": tmpl["combined_verts"], "reps": reps,
            "walk_cycle": (f0, f1)}


def _cache_phases(ctx, n):
    """Per-agent phase from the cache (K1 composed phase channel when
    the npz exposes it; else the deterministic ordinal stride)."""
    try:
        soa = ctx.get("crowd_soa")
        ph = getattr(soa, "agents", None)
        if ph is not None and "phase" in ph:
            arr = ph["phase"]
            return [float(arr[i]) for i in range(n)]
    except Exception:
        pass
    return [(i * 0.37) % 1.0 for i in range(n)]


def _cache_speeds(ctx, n):
    """Per-agent dominant speed from the cache speed channel
    (mean over ticks; None when the surface is absent)."""
    try:
        soa = ctx.get("crowd_soa")
        ag = getattr(soa, "agents", None)
        if ag is not None and "speed" in ag:
            import numpy as np
            sp = np.asarray(ag["speed"])
            if sp.ndim == 2:
                return sp.mean(axis=1)
            return sp[:n]
    except Exception:
        pass
    return None


def _make_group_materials(group_tint):
    if not group_tint:
        return None
    mats = []
    for gi, (_, rgba) in enumerate(group_tint["groups"]):
        m = bpy.data.materials.new(f"Hum.Group{gi}")
        m.use_nodes = True
        bsdf = m.node_tree.nodes.get("Principled BSDF")
        bsdf.inputs["Base Color"].default_value = (*rgba[:3], 1.0)
        if "Roughness" in bsdf.inputs:
            bsdf.inputs["Roughness"].default_value = 0.6
        mats.append(m)
    return mats


def _tint_object(me, group_mats, agent_i, n_agents):
    """Per-OBJECT material-slot links (audit P2-3). group_tint groups
    are assigned round-robin over the agent ordinals unless the caller
    supplied an explicit mapping."""
    mapping = group_tint.get("agent_group")
    gi = mapping[agent_i] if mapping else (agent_i % len(group_mats))
    for slot in me.material_slots:
        slot.link = 'OBJECT'
        slot.material = group_mats[gi]


def bind_principals(ctx, name_clip_pairs):
    """UAL principals: ONE glTF import per hero via the vendored
    loader's _import_actor (P2-4 thin caller — no JeepRoot demand).

    name_clip_pairs: {"Captain": ("Walk_Loop", scale, loc), ...}
    The hero wrapper is parented to the film's hero record root (the
    caller re-parents the returned root onto its keyed hero object).
    """
    import assets_ual_actors as UAL
    out = {}
    for name, (clip, scale, loc) in name_clip_pairs.items():
        rep = UAL._import_actor(name, scale)
        if loc is not None:
            rep["root"].location = loc
        acts = rep.get("actions", {})
        act = acts.get(clip) or next(
            (a for k, a in acts.items() if clip.lower() in k.lower()), None)
        if act is None:
            _fail(f"UAL clip {clip!r} not in pool "
                  f"({sorted(acts)[:8]})")
        rep["armature"].animation_data_create()
        rep["armature"].animation_data.action = act
        out[name] = rep
        _P(f"UAL principal {name}: clip {clip} "
           f"(facing {rep.get('facing_sign', '?')})")
    return out


def motion_gates(ctx, reps, sample=5):
    """The s20 two-column law, crowd edition: for `sample` agents —
    world hips-z bob across the cycle (>= 0.02 m for walkers) and
    feet anti-phase (L/R z-delta sign flip); anchor world xy matches
    the cache at the sampled tick (±1 mm when the cache surface is
    available)."""
    import random
    rng = random.Random(22)
    picks = rng.sample(reps, min(sample, len(reps)))
    sc = bpy.context.scene
    f0, f1 = 1, 38
    report = []
    for rep in picks:
        arm = rep["armature"]
        act = arm.animation_data.action
        hips = arm.pose.bones.get("mixamorig:Hips")
        if hips is None:
            _fail("gate rig lacks mixamorig:Hips")
        zs, lz, rz = [], [], []
        for f in (f0, (f0 + f1) // 2, f1 - 1):
            sc.frame_set(f)
            bpy.context.view_layer.update()
            w = arm.matrix_world @ hips.matrix
            zs.append(w.translation.z)
            for side, acc in (("Left", lz), ("Right", rz)):
                pb = arm.pose.bones.get(f"mixamorig:{side}Foot")
                if pb:
                    acc.append((arm.matrix_world @ pb.matrix).translation.z)
        bob = max(zs) - min(zs)
        anti = (lz[1] - lz[0]) * (rz[1] - rz[0]) < 0
        ok = (bob >= 0.02 and anti) if act.name.startswith("walk_") \
            else True
        report.append({"agent": rep["root"].name, "action": act.name,
                       "hips_bob": round(bob, 3), "feet_antiphase": anti,
                       "ok": ok})
        if not ok:
            _fail(f"motion gate FAILED on {rep['root'].name}: bob={bob:.3f} "
                  f"anti={anti} (the s20 two-column law)")
    _P("motion gates:", [(r['agent'], r['hips_bob'], r['feet_antiphase'])
                         for r in report])
    return report
