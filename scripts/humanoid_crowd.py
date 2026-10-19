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

# The chase RB placeholder slots (s25: local — was an escape-previz
# import; the audit's P1-1). loader.py renames chase[2]/[5]/[8] to
# Zed.RB.*; these anchors are physics performers, NOT cache agents.
RB_FALLS_V3 = (2, 5, 8)


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
    land in POLY_BAND. The ratio SELF-CALIBRATES arithmetically
    (ratio_next = ratio x band_mid/achieved, deterministic) with a
    FRESH IMPORT per attempt — compounding a second DECIMATE on an
    already-decimated mesh collapses it (636-vert law, measured)."""
    combined = None
    for _step in range(4):
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
        if POLY_BAND[0] <= combined <= POLY_BAND[1]:
            break
        # discard the attempt (objects + data) before re-importing
        for ob in [o for o in bpy.data.objects if o not in before]:
            bpy.data.objects.remove(ob, do_unlink=True)
        if combined > POLY_BAND[1]:
            mid = (POLY_BAND[0] + POLY_BAND[1]) / 2
            ratio = ratio * (mid / combined)
            continue
        _fail(f"decimate UNDER band ({combined} < {POLY_BAND[0]}) — "
              f"collapse risk, refusing")
    else:
        _fail(f"decimate did not converge in 4 attempts "
              f"(last {combined} @ ratio {ratio:.3f})")
    _P(f"template ready: combined {combined} verts @ ratio {ratio:.3f} "
       f"({[len(m.data.vertices) for m in meshes]})")
    return {"arm": arm, "meshes": meshes, "combined_verts": combined,
            "ratio": ratio}


def _wrap_action(base_act, new_name, phase, cyc, f0, f1):
    """WRAP law: copy + in-cycle rotation + CYCLES modifiers.

    Review r1 P0-4/T2/T5/T7: the wrap ROTATES the key array (keys that
    cross the window bottom re-enter at the top) — the co.x rewrite
    alone leaves the array UNSORTED (fcurve evaluation then binary-
    searches garbage) and the bezier handles stale. Law: shift co AND
    both handles by the same delta, then sort() + update().
    """
    a2 = base_act.copy()
    a2.name = new_name
    shift = (phase % 1.0) * cyc
    for fc in _iter_fcurves(a2):
        for kp in fc.keyframe_points:
            t = f0 + ((kp.co.x - f0 - shift) % cyc)
            dx = t - kp.co.x
            kp.co.x = t
            kp.handle_left.x += dx
            kp.handle_right.x += dx
        fc.keyframe_points.sort()
        fc.update()
        md = fc.modifiers.new('CYCLES')
        md.mode_before = 'NONE'
        md.mode_after = 'REPEAT'
        md.cycles_before = 0
        md.cycles_after = 100000
    return a2


def _iter_fcurves(action):
    """5.x slotted-action iterator (blender_kit is a HARD dependency —
    review r1 P2-11: a silent [] fallback would no-op the wrap law, so
    failure RAISES)."""
    import blender_kit
    return list(blender_kit.iter_fcurves(action))


def _trim_action(act, keep_frames):
    """Trim an action to its first `keep_frames` (index-DESC removals —
    RNA array refs go stale after each removal)."""
    f0 = act.frame_range[0]
    for fc in _iter_fcurves(act):
        doomed = [i for i, kp in enumerate(fc.keyframe_points)
                  if kp.co.x > f0 + keep_frames]
        for i in reversed(doomed):
            fc.keyframe_points.remove(fc.keyframe_points[i])


def bind_crowd(ctx, fam, group_tint=None):
    """Bind rig assemblies under the cache anchors.

    ctx: the film scene ctx (needs ctx["crowd_cache"] with n_agents,
    ctx["chars"]["zombies"]["crowd"/"chase"] — the anchors list, RB
    placeholders EXCLUDED per bake2's pairing law). The anchor
    commuters become DEGENERATE CARRIERS (1-vert, no faces) — see the
    law inside.
    group_tint: None or {"groups": [(n_in_group, rgba), ...],
    "agent_group": [group_idx per agent ordinal]} — per-OBJECT
    material-slot links (audit P2-3: zero mesh copies; one material
    datablock per group, linked per agent object).

    Gates (fail-closed): anchor count == cache n_agents; bone census
    (clip names ⊆ rig names); wrap-band assert; anchor type law.
    Returns the report dict (numbers travel).
    """
    import wrapper_rig
    from crowd_v6.contract import RB_FALLS_V3   # the pairing law's own source
    cache = ctx.get("crowd_cache")
    if cache is None:
        _fail("bind_crowd: ctx has no crowd_cache (run load_kit_cache "
              "+ bake_tier2 first)")
    zombies = (ctx.get("chars") or {}).get("zombies")
    crowd = list(zombies["crowd"])
    chase = list(zombies["chase"])
    # bake2 pairs crowd + [chase[j] for j not in RB_FALLS_V3] — the 3
    # RB placeholders are NOT cache agents (review r1 P0-2).
    # s25 (the rollout audit's P1-1): RB_FALLS_V3 is a LOCAL constant
    # now — the escape-previz import was a clone-seam hazard (the
    # film env resolved it, a fresh kit env did not). Every film in
    # the family authors the RB chase placeholders at indices
    # (2, 5, 8) (verified across all five scene modules + tform), so
    # the constant IS the family law; the Zed.RB.* census assert
    # below fail-closes the day any film moves its slots.
    rb_idx = set(RB_FALLS_V3)
    rb_named = [ob for ob in chase if ob.name.startswith("Zed.RB.")]
    if len(rb_named) != len(RB_FALLS_V3):
        _fail(f"RB placeholder census: {len(rb_named)} Zed.RB.* anchors "
              f"!= len(RB_FALLS_V3)={len(RB_FALLS_V3)} — the bake pairing "
              f"moved; update the constant WITH the film modules, never "
              f"silently")
    anchors = crowd + [ob for j, ob in enumerate(chase)
                       if j not in rb_idx]
    n = int(cache.n_agents)
    if len(anchors) != n:
        _fail(f"anchors {len(anchors)} != cache n_agents {n} "
              f"(crowd {len(crowd)} + non-RB chase "
              f"{len(chase) - len(rb_idx & set(range(len(chase))))})")
    for a in anchors:
        if a.type != 'MESH':
            _fail(f"anchor {a.name} is {a.type} — the D6-2 law requires "
                  f"MESH anchors (the hidden-commuter carrier)")

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
    _cycles_action(idle_act)
    idle_names = {fc.data_path.split('"')[1] for fc in _iter_fcurves(idle_act)
                  if '"' in fc.data_path}
    missing_i = idle_names - rig_names
    if missing_i:
        _fail(f"idle bones not on rig ({len(missing_i)}): "
              f"{sorted(missing_i)[:6]}")

    speeds = _cache_speeds(ctx, n)
    group_mats = _make_group_materials(group_tint)
    agent_group = (group_tint or {}).get("agent_group")
    # the PER-GROUP MESH DATA law: the glTF exporter resolves materials
    # from the MESH DATA slots — object-level slot links render right
    # in Cycles but do NOT export (the tform_2 GLB carried the raw
    # pink for all 102). One mesh-data copy per group, materials at
    # the data level; agents share within the group (the tfog palette
    # law's copy idiom, moved up a level).
    group_meshes = None
    if group_mats:
        n_groups = len(group_mats)
        group_meshes = []
        for gi in range(n_groups):
            gmats = [group_mats[gi]] * len(tmpl["meshes"])
            copies = []
            for j, tm in enumerate(tmpl["meshes"]):
                gme = tm.copy()
                # UNIQUE data per group — Object.copy() SHARES the data
                # and 5 clearing passes would leave ONE group's material
                # on the shared template data (the all-Group4 law,
                # measured)
                gme.data = gme.data.copy()
                gme.name = f"Hum.Group{gi}.Body{j}"
                gme.data.materials.clear()
                gme.data.materials.append(gmats[j])
                copies.append(gme)
            group_meshes.append(copies)

    # the DEGENERATE CARRIER law: the anchor keeps its object identity
    # (name, transform keys, bake2 pairing) but its mesh data becomes a
    # single-vertex mesh — no faces, renders as NOTHING, yet the GLB
    # keeps the node (gate 24's declared refs) and the exporter's TRS
    # gather finds the object (gate 17). hide_render would EXCLUDE the
    # object from the GLB and fail both gates (measured).
    import bmesh
    def _degenerate_data(name):
        me = bpy.data.meshes.new(name)
        bm = bmesh.new()
        bm.verts.new((0.0, 0.0, 0.0))
        bm.to_mesh(me)
        bm.free()
        return me
    deg_data = _degenerate_data("Hum.carrier")

    reps = []
    n_walk = n_idle = 0
    for i, anchor in enumerate(anchors):
        # the anchor stays a MESH (D6-2); its data -> the degenerate
        # carrier (the baked gait shape keys die with the old data —
        # the rigs carry the gait now; the transform keys are
        # OBJECT-level and survive the swap)
        anchor.data = deg_data
        # per-agent rig: LINK the copy before wrap (review r1 P0-1/T4)
        arm_i = tmpl["arm"].copy()
        arm_i.name = f"{anchor.name}.Rig"
        bpy.context.scene.collection.objects.link(arm_i)
        wrapper = wrapper_rig.wrap(arm_i, f"{anchor.name}.Hum",
                                   scale=FILM_HEIGHT / fam["rig_height"],
                                   facing_probe_bone=fam["probe_bone"])
        wrapper["root"].parent = anchor
        # skinned meshes: instance linked copies under THIS armature;
        # RETARGET the Armature modifier (review r1 P0-3/T3: me.copy()
        # keeps the modifier pointing at the TEMPLATE arm — without the
        # retarget every agent renders as a rigid rest-pose statue)
        gi = agent_group[i] if agent_group is not None else 0
        srcs = group_meshes[gi] if group_meshes else tmpl["meshes"]
        for j, tm in enumerate(srcs):
            me = tm.copy()
            me.name = f"{anchor.name}.Body{j}"
            me.parent = wrapper["armature"]
            bpy.context.scene.collection.objects.link(me)
            for md in me.modifiers:
                if md.type == 'ARMATURE':
                    md.object = wrapper["armature"]
        # the action: walk (per-agent wrapped phase) or shared idle;
        # the SHARED idle also gets CYCLES (review r1 P2-13 — Blender-
        # side strips must loop too, not just the web viewer)
        if speeds is not None and speeds[i] > STATIONARY_MPS:
            a2 = _wrap_action(walk_act, f"walk_{i:03d}", phases[i], cyc, f0, f1)
            n_walk += 1
        else:
            a2 = idle_act
            n_idle += 1
        wrapper["armature"].animation_data_create()
        wrapper["armature"].animation_data.action = a2
        # wrap-band gate on the per-agent actions (frame_range reads the
        # keyed span only — CYCLES does not extend it, review r1 T1)
        if a2 is not idle_act:
            lo, hi = a2.frame_range
            if lo < f0 - 1e-4 or hi >= f0 + cyc + 1e-4:
                _fail(f"wrap-band violated on agent {i}: "
                      f"{lo:.2f}..{hi:.2f} not inside [{f0},{f0 + cyc})")
        reps.append({"anchor": anchor, "ordinal": i, **wrapper})
    # quaternion modes census (the s18 law) on the shared rig data —
    # BEFORE the template removal (the object ref dies with the removal)
    bad = [pb.name for pb in tmpl["arm"].pose.bones
           if pb.rotation_mode != 'QUATERNION']
    # remove the TEMPLATE objects (review r1 P1-8: a full-height rest-
    # pose x_bot at the world origin in every render AND the GLB)
    bpy.data.objects.remove(tmpl["arm"], do_unlink=True)
    for tm in tmpl["meshes"]:
        bpy.data.objects.remove(tm, do_unlink=True)
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
    """Per-agent phase — the K1 composed PHASE channel is the AUTHORITY
    (D6-3): it lives in the SoA TICKS view (per-(tick, agent)); the
    per-agent scalar is the LAST tick's value (the accumulated stride
    phase). The ordinal-stride fallback is LOUD (review r1 P1-6: a
    silent fallback silently replaces the K1 phase)."""
    import numpy as np
    soa = ctx.get("crowd_soa")
    ticks = getattr(soa, "ticks", None)
    if ticks is not None and "phase" in ticks:
        arr = np.asarray(ticks["phase"])
        if arr.ndim == 2 and arr.shape[1] >= n:
            return [float(arr[-1, i]) for i in range(n)]
    _P(f"WARN phases: no K1 tick phase channel — falling back to the "
       f"deterministic ordinal stride (the layered-cache law is "
       f"silently OFF for this film)")
    return [(i * 0.37) % 1.0 for i in range(n)]


def _cache_speeds(ctx, n):
    """Per-agent dominant speed — the TICKS speed channel mean over
    ticks (review r1 P1-5: the real SoA surface is .ticks, shape
    (n_ticks, n_agents); .agents is per-agent CONSTANTS without a
    speed key). Falls back LOUD to None ("nobody walks" would be a
    silent film-killer otherwise)."""
    import numpy as np
    soa = ctx.get("crowd_soa")
    ticks = getattr(soa, "ticks", None)
    if ticks is not None and "speed" in ticks:
        sp = np.asarray(ticks["speed"])
        if sp.ndim == 2 and sp.shape[1] >= n:
            return sp.mean(axis=0)
    _P(f"WARN speeds: no tick speed channel — EVERY agent binds the "
       f"shared idle (motion would be silently absent)")
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
        # the WORKBENCH reads the viewport diffuse_color, not the
        # Principled node (gauntlet R4 law — workbench + glTF in sync)
        m.diffuse_color = (*rgba[:3], 1.0)
        mats.append(m)
    return mats


def _tint_object(me, group_mats, agent_i, agent_group=None):
    """Per-OBJECT material-slot links (audit P2-3). The group index
    comes from the caller's POP_PLAN mapping; None = round-robin."""
    gi = agent_group[agent_i] if agent_group is not None \
        else (agent_i % len(group_mats))
    for slot in me.material_slots:
        slot.link = 'OBJECT'
        slot.material = group_mats[gi]


def _cycles_action(act):
    """Add CYCLES modifiers to an action's fcurves (the shared idle's
    Blender-side loop — review r1 P2-13)."""
    for fc in _iter_fcurves(act):
        md = fc.modifiers.new('CYCLES')
        md.mode_before = 'NONE'
        md.mode_after = 'REPEAT'
        md.cycles_before = 0
        md.cycles_after = 100000
    return act


def bind_principals(ctx, name_clip_pairs):
    """UAL principals: ONE glTF import per hero via the vendored
    loader's _import_actor (P2-4 thin caller — no JeepRoot demand).

    name_clip_pairs: {"Captain": (clip, scale, loc), ...}
    The rep's wrapper root is returned UNPARENTED; the caller parents
    it onto its keyed hero object (identity MPI + zero local = rides
    the hero exactly).

    FEET-ORIGIN LAW (self-correcting, numbers travel): the mannequin's
    world bbox min-z is measured post-import; a nonzero floor lifts
    the WRAPPER so the feet sit at z=0 (the s20 lesson: never assume
    the import's origin — measure it).
    """
    # THE CLONE-SEAM LAW (the failure that taught it): `import
    # assets_ual_actors` resolved to the ESCAPE-PREVIZ copy in the
    # film env (a parallel scripts dir on sys.path) and its loader
    # refused our names. Load THIS repo's vendored copy BY PATH.
    import importlib.util
    _here = os.path.dirname(os.path.abspath(__file__))
    _spec = importlib.util.spec_from_file_location(
        "_ual_actors_kit", os.path.join(_here, "assets_ual_actors.py"))
    UAL = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(UAL)
    out = {}
    for name, (clip, scale, loc) in name_clip_pairs.items():
        # the vendored loader demands a KNOWN actor name (its SHIRT
        # palette) — import under "Driver" and TINT to the film's
        # identity color right after (the tint_ual_actor law)
        rep = UAL._import_actor("Driver", scale)
        rep["actor_kind"] = "Driver"   # the tint/census provenance
        if loc is not None:
            rep["root"].location = loc
        bpy.context.view_layer.update()
        arm = rep["armature"]
        zs = [(arm.matrix_world @ __import__("mathutils").Vector(c)).z
              for c in arm.bound_box]
        floor = min(zs)
        rep["floor_z"] = round(floor, 4)
        if abs(floor) > 1e-3:
            rep["root"].location.z -= floor
            bpy.context.view_layer.update()
            _P(f"feet-origin lift {name}: floor {floor:+.4f} -> 0 "
               f"(wrapper z now {rep['root'].location.z:+.4f})")
        acts = rep.get("actions", {})
        act = acts.get(clip) or next(
            (a for k, a in acts.items() if clip.lower() in k.lower()), None)
        if act is None:
            _fail(f"UAL clip {clip!r} not in pool "
                  f"({sorted(acts)[:8]})")
        arm.animation_data_create()
        arm.animation_data.action = act
        out[name] = rep
        _P(f"UAL principal {name}: clip {clip} "
           f"(facing {rep.get('facing_sign', '?')}, floor {floor:+.4f})")
    return out


def motion_gates(ctx, reps, sample=6, walk_cycle=None, exempt=()):
    """The s20 two-column law, crowd edition (review r1 P1-7/P2-10
    folded):

    - STRATIFIED picks: at least 2 walkers + 2 idlers when both
      classes exist (an all-idler draw would pass vacuously);
    - WALKERS: world hips-z bob >= 0.02 m across the cycle AND feet
      anti-phase — sampled at THREE delta pairs (f0/f_mid, f_mid/f1,
      f0/f1) with a magnitude floor; the gate needs the BEST pair to
      show the anti-phase sign (a phase aligned with one pair's
      equal-height instant must not false-fail);
    - ANCHOR-vs-CACHE: anchor world xy vs the cache tick xy at the
      last baked tick (+-1 mm) — the numbers-travel law;
    - IDLERS: hips drift < 0.05 m across the trimmed cycle.

    exempt (s25, the rollout audit's P2): root names EXCLUDED from
    the pass/fail math and reported as explicit 'exempt' rows — for
    film-keyed overlay performers whose motion the walk-cycle
    assumptions cannot judge (e.g. tsquall's slip faller, whose
    ~80-deg tumble overlay rides rot_x/rot_y on top of the cache
    walk). Exemptions are DOCUMENTED rows, never silent skips.
    """
    import random
    import numpy as np
    rng = random.Random(22)
    exempt_names = {getattr(r["root"], "name", r) if not isinstance(r, str)
                    else r for r in exempt}
    walkers = [r for r in reps
               if r["armature"].animation_data.action.name.startswith("walk_")
               and r["root"].name not in exempt_names]
    idlers = [r for r in reps if r not in walkers
              and r["root"].name not in exempt_names]
    eligible = [r for r in reps if r["root"].name not in exempt_names]
    picks = (walkers[:2] + idlers[:2]
             + rng.sample(eligible, max(0, sample - len(walkers[:2]) - len(idlers[:2]))))
    seen, uniq = set(), []
    for r in picks:
        k = r["root"].name
        if k not in seen:
            seen.add(k)
            uniq.append(r)
    picks = uniq[:max(sample, 4)]
    sc = bpy.context.scene
    f0, f1 = walk_cycle if walk_cycle else (1, 38)
    f_mid = (f0 + f1) // 2
    # the cache surface for the anchor gate
    soa = ctx.get("crowd_soa")
    ticks = getattr(soa, "ticks", None)
    n_ticks = int(ctx["crowd_cache"].n_ticks) if ctx.get("crowd_cache") else 0
    report = []
    # the documented exemption rows first (never silent skips)
    for rep in reps:
        if rep["root"].name in exempt_names:
            report.append({"root": rep["root"].name, "verdict": "EXEMPT",
                           "why": "film-keyed overlay performer — the "
                                  "walk-cycle assumptions cannot judge the "
                                  "tumble/overlay motion (s25 exempt law)"})
    for rep in picks:
        arm = rep["armature"]
        act = arm.animation_data.action
        is_walk = act.name.startswith("walk_")
        hips = arm.pose.bones.get("mixamorig:Hips")
        if hips is None:
            _fail("gate rig lacks mixamorig:Hips")
        zs, lz, rz = [], [], []
        five = [f0, f0 + (f1 - f0) // 4, f_mid, f0 + 3 * (f1 - f0) // 4,
                f1 - 1]
        for f in five:
            sc.frame_set(f)
            bpy.context.view_layer.update()
            zs.append((arm.matrix_world @ hips.matrix).translation.z)
            for side, acc in (("Left", lz), ("Right", rz)):
                pb = arm.pose.bones.get(f"mixamorig:{side}Foot")
                if pb:
                    acc.append((arm.matrix_world @ pb.matrix).translation.z)
        bob = max(zs) - min(zs)
        anti = None
        if is_walk:
            pairs = [(lz[j] - lz[0], rz[j] - rz[0]) for j in (1, 2, 3, 4)]
            pairs += [(lz[j] - lz[1], rz[j] - rz[1]) for j in (2, 3, 4)]
            anti = any((dl * dr < 0) and max(abs(dl), abs(dr)) > 0.01
                       for dl, dr in pairs)
            ok = bob >= 0.02 and anti
        else:
            ok = bob < 0.05
        # the anchor-vs-cache gate (+-1 mm)
        cache_note = None
        if ticks is not None and all(k in ticks for k in ("x", "y")) \
                and n_ticks > 0:
            i = rep["ordinal"]
            tx = float(np.asarray(ticks["x"])[n_ticks - 1, i])
            ty = float(np.asarray(ticks["y"])[n_ticks - 1, i])
            # the tick->frame law: sample the SAME instant (frame 1 vs
            # the last tick is the 5.8m false-fail class)
            dt = float(ctx["crowd_cache"].dt) or (1.0 / 12.0)
            fps = float(sc.render.fps) or 24.0
            sc.frame_set(max(sc.frame_start,
                             1 + int(round((n_ticks - 1) * dt * fps))))
            bpy.context.view_layer.update()
            ax, ay = rep["anchor"].matrix_world.translation.x, \
                rep["anchor"].matrix_world.translation.y
            dx, dy = abs(ax - tx), abs(ay - ty)
            cache_note = (round(dx, 4), round(dy, 4))
            if dx > 1e-3 or dy > 1e-3:
                _fail(f"anchor-vs-cache gate FAILED on {rep['root'].name}: "
                      f"dx={dx:.4f} dy={dy:.4f} > 1mm")
        report.append({"agent": rep["root"].name, "action": act.name,
                       "hips_bob": round(bob, 3), "feet_antiphase": anti
                       if is_walk else None,
                       "cache_xy_err": cache_note, "ok": ok})
        if not ok:
            _fail(f"motion gate FAILED on {rep['root'].name}: bob={bob:.3f} "
                  f"walk={is_walk} (the s20 two-column law)")
    _P("motion gates:", [(r['agent'], r['action'], r['hips_bob'],
                          r['cache_xy_err']) for r in report])
    n_exc = sum(1 for r in report if r.get("verdict") == "EXEMPT")
    if n_exc:
        _P(f"motion gates: {n_exc} documented exemption row(s)",
           [r['root'] for r in report if r.get('verdict') == 'EXEMPT'])
    return report
