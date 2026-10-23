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
# s25 durability: the two load-bearing clips (walk 2899 / idle 2781,
# sha-verified) are COMMITTED at vendor/rh_clips/ — a fresh sandbox
# without the RH-canvas-animations checkout still binds. The env var
# wins; the repo-local copy is the fallback when the env path lacks
# the clips (the release-volume fetch recipe lives in the worklog).
if not os.path.exists(os.path.join(RH_ANIMS, "assets", "fbx", "2899.fbx")):
    _repo_clips = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "..", "vendor", "rh_clips")
    if os.path.exists(os.path.join(_repo_clips, "assets", "fbx",
                                   "2899.fbx")):
        RH_ANIMS = os.path.abspath(_repo_clips)

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
# fix-wave-1 D3-REV2: the top speed class needs a RUN clip (the walk
# clip cannot be retimed past ~2x without looking wrong); 2850 =
# "Run forward" from the RH WALK_RUN_MOVE category.
JOG_CLIP = "2850.fbx"
# speed-class edges (mean m/s from the cache): <=0.9 stroll / <=1.6
# walk / <=2.4 brisk / rest run. The per-class retime law (D3-REV2):
#   key-time scale s = clamp((24/30) * v_nat / v_class, 0.55, 1.9)
# (24/30 = the clip timebase correction; v_nat measured from the
# clip's own hips travel per cycle, the s43 law — RH clips are NOT
# in-place).
CLASS_EDGES = (0.9, 1.6, 2.4)
NOMINAL_WALK_MPS = 1.4      # in-place-fallback cadence assumption
RETIME_CLAMP = (0.55, 1.9)
WALK_SPAN_MIN_M = 0.02      # the bind-time motion gate (D3-REV2)

# The chase RB placeholder slots (s25: local — was an escape-previz
# import; the audit's P1-1). loader.py renames chase[2]/[5]/[8] to
# Zed.RB.*; these anchors are physics performers, NOT cache agents.
RB_FALLS_V3 = (2, 5, 8)


def _fail(msg):
    raise RuntimeError(f"humanoid_crowd: {msg}")


class _fps_guard:
    """THE 24FPS TIMEBASE LAW (s25, the export-lane find): EVERY FBX
    import in this module (the rig template, the walk clip, the idle
    clip, the UAL principals) can silently flip scene.render.fps to
    the clip's own timebase (Mixamo clips carry 30). The film bakes
    key on a 24 fps timebase (crowd_v6/contract FPS law) — an fps flip
    at bind time makes the WHOLE film export 1.25x fast (the gate17
    key-interval class caught it: chase steps 2.1-2.7 m/s apparent =
    sim 3.8 x 1.25; tform_2 slipped UNDER the band at drill speeds and
    shipped playing fast — the latent look bug). Save + restore around
    every import, loudly."""

    def __enter__(self):
        self._fps = bpy.context.scene.render.fps
        return self

    def __exit__(self, exc_type, exc, tb):
        now = bpy.context.scene.render.fps
        if now != self._fps:
            _P(f"fps guard: import flipped scene.render.fps "
               f"{self._fps} -> {now}; restoring {self._fps}")
            bpy.context.scene.render.fps = self._fps
        return False


def _P(*a):
    print("HUMANCROWD", *a)


def _resolve_rig():
    """s26 rig-serving law (DESIGN_world_retune_s26 A2 — the clips'
    env-wins/repo-fallback pattern): the ORIGINAL x_bot.fbx (when the
    RH_ASSETS checkout exists) wins; else the COMMITTED reconstructed
    .blend (vendor/rh_rig/) serves — a fresh sandbox without the RH
    checkout still binds. Returns (path, provenance)."""
    orig = f"{RH_ASSETS}/assets/director/dummy-rigs/x_bot.fbx"
    if os.path.isfile(orig):
        return orig, "original-fbx"
    here = os.path.dirname(os.path.abspath(__file__))
    rec = os.path.join(here, "..", "vendor", "rh_rig",
                       "x_bot_reconstructed.blend")
    if os.path.isfile(rec):
        return os.path.abspath(rec), "reconstructed-blend"
    _fail(f"no x_bot rig: neither {orig} nor the vendored "
          f"{rec} (the s26 reconstruction is committed; do not "
          f"delete vendor/rh_rig)")


def crowd_family(name):
    if name == "rh_xbot":
        rig, prov = _resolve_rig()
        fam = {
            "name": name,
            "rig": rig,
            "rig_provenance": prov,
            "walk": f"{RH_ANIMS}/assets/fbx/{WALK_CLIP}",
            "idle": f"{RH_ANIMS}/assets/fbx/{IDLE_CLIP}",
            "jog": f"{RH_ANIMS}/assets/fbx/{JOG_CLIP}",
            "prefix": "mixamorig:",
            "probe_bone": "mixamorig:LeftFoot",
            "rig_height": RIG_HEIGHT["rh_xbot"],
            "mesh_names": XBOT_MESHES,
        }
        _P(f"family rh_xbot: rig={os.path.basename(rig)} ({prov})")
        return fam
    _fail(f"unknown family {name!r} (have: rh_xbot; ual principals go "
          f"through bind_principals)")


def prepare_template(fam, ratio=0.14):
    """Import + decimate the rig template ONCE. Returns the template
    records (NOT yet instanced). Decimate law: combined verts must
    land in POLY_BAND. The ratio SELF-CALIBRATES arithmetically
    (ratio_next = ratio x band_mid/achieved, deterministic) with a
    FRESH IMPORT per attempt — compounding a second DECIMATE on an
    already-decimated mesh collapses it (636-vert law, measured).
    s26 PRE-DECIMATED PATH (DESIGN_world_retune_s26 A1): if the RAW
    import is already in-band (the reconstructed rig serves the
    post-decimate bind copies), decimate is SKIPPED and the report
    records pre_decimated=True + the measured band; sub-band still
    hard-fails (collapse risk, unchanged)."""
    combined = None
    pre_decimated = False
    for _step in range(4):
        before = set(bpy.data.objects)
        if fam["rig"].endswith(".blend"):
            # s26: the LOSSLESS template path (DESIGN_world_retune_s26
            # D2) — the reconstructed rig serves as .blend because the
            # FBX round trip rotated bone frames (the wrapper facing
            # contest failed; zero-bob rigs). Append is deterministic
            # and frame-exact.
            with bpy.data.libraries.load(fam["rig"], link=False) as (data_from, data_to):
                data_to.objects = list(data_from.objects)
            for ob in data_to.objects:
                if ob is not None:
                    bpy.context.scene.collection.objects.link(ob)
        else:
            bpy.ops.import_scene.fbx(filepath=fam["rig"])
        arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'
               and o not in before][-1]
        meshes = [o for o in bpy.data.objects if o.type == 'MESH'
                  and o not in before]
        raw_combined = sum(len(m.data.vertices) for m in meshes)
        if POLY_BAND[0] <= raw_combined <= POLY_BAND[1]:
            combined = raw_combined
            pre_decimated = True
            break
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
    _P(f"template ready: combined {combined} verts "
       f"({'PRE-DECIMATED raw' if pre_decimated else f'@ ratio {ratio:.3f}'}) "
       f"({[len(m.data.vertices) for m in meshes]})")
    return {"arm": arm, "meshes": meshes, "combined_verts": combined,
            "ratio": ratio, "pre_decimated": pre_decimated}


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


def _retime_action(act, scale, f0):
    """D3-REV2: scale key times around f0 by `scale` in place (the
    handles ride the same per-key delta as _wrap_action — the proven
    approximation in this module)."""
    for fc in _iter_fcurves(act):
        for kp in fc.keyframe_points:
            t = f0 + (kp.co.x - f0) * scale
            dx = t - kp.co.x
            kp.co.x = t
            kp.handle_left.x += dx
            kp.handle_right.x += dx
        fc.keyframe_points.sort()
        fc.update()


def _clip_travel_m(act):
    """s43 law: measure the hips HORIZONTAL travel over one loop
    (RH clips are NOT in-place). Returns (travel_m, f0, f1)."""
    loc = {}
    for fc in _iter_fcurves(act):
        dp = fc.data_path
        if not dp.endswith("location") or '"' not in dp:
            continue
        bone = dp.split('"')[1]
        if "hips" not in bone.lower():
            continue
        kps = sorted(kp.co.x for kp in fc.keyframe_points)
        if not kps:
            continue
        loc.setdefault(fc.array_index, (kps[0], kps[-1],
                       fc.keyframe_points[0].co.y, fc.keyframe_points[-1].co.y))
    if 0 not in loc or 1 not in loc:
        return 0.0, 0, 0
    f0 = min(loc[0][0], loc[1][0])
    f1 = max(loc[0][1], loc[1][1])
    travel = ((loc[0][3] - loc[0][2]) ** 2 +
              (loc[1][3] - loc[1][2]) ** 2) ** 0.5
    return abs(travel), int(f0), int(f1)


def _pin_slot(ad, act):
    """kb rigged-characters law #7: EVERY action assignment pins the
    slot. The unpinned class shipped 12/129 near-frozen walks (the
    stale/legacy slot survives on copies)."""
    ad.action = act
    slots = getattr(act, "slots", None)
    if slots:
        ad.action_slot = slots[0]


def _span_gate(arm, act, f0, cyc, i):
    """D3-REV2 bind-time motion gate: the bound walk action must MOVE
    (hips world-z span >= WALK_SPAN_MIN_M over its class cycle, 11
    samples — the s26 aliasing law bounds the extreme within ~2f).
    The unpinned-slot class shipped 12/129 near-frozen walks."""
    sc = bpy.context.scene
    hips = None
    for pb in arm.pose.bones:
        if pb.name.lower().endswith("mixamorig:hips"):
            hips = pb
            break
    if hips is None:
        _fail(f"span gate: agent {i} has no *mixamorig:hips bone "
              f"(census bug — the rename prefix broke the lookup?)")
    zs = []
    for j in range(11):
        f = f0 + cyc * j // 10
        sc.frame_set(f)
        bpy.context.view_layer.update()
        zs.append((arm.matrix_world @ hips.matrix).translation.z)
    sc.frame_set(1)
    span = max(zs) - min(zs)
    if span < WALK_SPAN_MIN_M:
        _fail(f"span gate: agent {i} walk action {act.name} hips span "
              f"{span:.4f} m < {WALK_SPAN_MIN_M} (frozen-walk class — "
              f"the bind or the retime is broken; refusing)")


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

    with _fps_guard():
        tmpl = prepare_template(fam)
    # the walk clip (import standalone: it brings its own armature —
    # strip it after stealing the action)
    with _fps_guard():
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
    with _fps_guard():
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

    # ---- fix-wave-1 D3-REV2: speed-class retimed bases ----------------
    # v_nat from the clip's own hips travel (s43: RH clips are NOT
    # in-place). Top class uses the RUN clip when it serves.
    speeds = _cache_speeds(ctx, n)
    # D3-REV2b: CLASS speeds are the MOVING mean (ticks > 0.3 m/s) —
    # the all-ticks mean collapses pre-spawn zero ticks and put every
    # walker in class 0 at the floor (measured: 122/122 in class 0).
    class_speeds = _moving_speeds(ctx, n, speeds)
    travel_w, tf0, tf1 = _clip_travel_m(walk_act)
    if travel_w > 0.15:
        v_nat = travel_w / (cyc / 30.0)
    else:
        v_nat = NOMINAL_WALK_MPS
        _P(f"retiming: walk clip reads in-place (travel {travel_w:.3f}m) "
            f"-> nominal cadence {NOMINAL_WALK_MPS} m/s")
    jog_act = None
    jog_cyc = None
    v_nat_top = v_nat
    if os.path.isfile(fam.get("jog", "")):
        with _fps_guard():
            before = set(bpy.data.actions)
            before_ob = set(bpy.data.objects)
            bpy.ops.import_scene.fbx(filepath=fam["jog"])
            jog_act = [a for a in bpy.data.actions if a not in before][0]
            for ob in [o for o in bpy.data.objects if o not in before_ob]:
                bpy.data.objects.remove(ob, do_unlink=True)
        travel_j, jf0, jf1 = _clip_travel_m(jog_act)
        jog_cyc = jf1 - jf0
        jog_names = {fc.data_path.split('"')[1]
                     for fc in _iter_fcurves(jog_act)
                     if '"' in fc.data_path}
        if jog_names - rig_names:
            _P("retiming: jog clip bones not on rig — top class falls "
                "back to the retimed walk")
            bpy.data.actions.remove(jog_act)
            jog_act = None
            jog_cyc = None
        elif travel_j > 0.15:
            v_nat_top = travel_j / (jog_cyc / 30.0)
        else:
            v_nat_top = 3.0   # a run clip's nominal cadence
    else:
        _P("retiming: no jog clip served — the top class retimes the "
            "walk (residual slide accepted, see DESIGN_fix_wave1 D3)")

    # per-class retimed bases: class i uses walk for i < top, the jog
    # for the top class. v_class = the members' mean speed.
    def _class_of(v):
        for ci, edge in enumerate(CLASS_EDGES):
            if v <= edge:
                return ci
        return len(CLASS_EDGES)
    n_classes = len(CLASS_EDGES) + 1
    class_members = [[] for _ in range(n_classes)]
    for i in range(n):
        if speeds is not None and speeds[i] > STATIONARY_MPS:
            class_members[_class_of(class_speeds[i])].append(i)
    class_bases = []   # per class: (act, f0, cyc) or None
    for ci in range(n_classes):
        mem = class_members[ci]
        if not mem:
            class_bases.append(None)
            continue
        v_class = max(0.35, float(sum(class_speeds[i] for i in mem))
                      / len(mem))
        use_jog = (ci == n_classes - 1) and jog_act is not None
        src = jog_act if use_jog else walk_act
        src_cyc = jog_cyc if use_jog else cyc
        src_nat = v_nat_top if use_jog else v_nat
        s = (24.0 / 30.0) * src_nat / v_class
        s = max(RETIME_CLAMP[0], min(RETIME_CLAMP[1], s))
        base = src.copy()
        base.name = f"{'jog' if use_jog else 'walk'}_c{ci}"
        src_f0 = jf0 if use_jog else f0
        _retime_action(base, s, src_f0)
        class_bases.append((base, src_f0, int(round(src_cyc * s)), s,
                            v_class, use_jog))
        _P(f"retiming: class {ci} n={len(mem)} v_class={v_class:.2f} "
            f"{'jog' if use_jog else 'walk'} s={s:.3f} "
            f"cycle={int(round(src_cyc * s))}f")
    for ci, cb in enumerate(class_bases):
        if class_members[ci] and cb is None:
            _fail(f"class {ci} has {len(class_members[ci])} members but "
                  f"no base (retime failed)")
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
                # s25 THE DATA-NAME LAW: the DATA carries the object's
                # name too — the structural lookup law: name-prefix
                # finders must resolve at the data level (6-b find:
                # objects renamed, data kept FBX names -> 0 bodies
                # matched by the strip predicate)
                gme.data.name = gme.name
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
    import collections as _collections
    bone_name_census = _collections.Counter()
    # fix-wave-1 D1-REV2: per-agent UNIQUE armature data + mesh data +
    # bone/vgroup renames + per-agent actions with pinned slots. The
    # staged GLB carried 129 nodes named mixamorig:Hips -> three.js
    # binds every walk action to the FIRST rig (128 statues + 1 rig
    # torn by 129 stacked actions). Object.copy() SHARES data — the
    # rename would cascade across every agent; vertex groups do NOT
    # follow bone renames (the unskin trap). LAW per agent: fresh
    # armature data, fresh mesh data, rename BOTH bones and vgroups
    # with the SAME prefix, bind the action and pin its slot BEFORE
    # the rename (the s20 remap fires for the bound action only).
    for i, anchor in enumerate(anchors):
        # the anchor stays a MESH (D6-2); its data -> the degenerate
        # carrier (the baked gait shape keys die with the old data —
        # the rigs carry the gait now; the transform keys are
        # OBJECT-level and survive the swap)
        anchor.data = deg_data
        # per-agent rig: LINK the copy before wrap (review r1 P0-1/T4)
        arm_i = tmpl["arm"].copy()
        # D1-REV2: the data copy is the LAW — Object.copy() shares the
        # armature data and a rename on one agent would rename every
        # agent (compounding prefixes, cross-corrupted remaps)
        arm_i.data = tmpl["arm"].data.copy()
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
        agent_meshes = []
        for j, tm in enumerate(srcs):
            me = tm.copy()
            me.name = f"{anchor.name}.Body{j}"
            # D1-REV2: per-agent MESH DATA copies — the vgroup renames
            # below must not write through to the shared group data
            # (materials ride the copy; RAM receipt printed below)
            me.data = me.data.copy()
            me.data.name = me.name
            me.parent = wrapper["armature"]
            bpy.context.scene.collection.objects.link(me)
            for md in me.modifiers:
                if md.type == 'ARMATURE':
                    md.object = wrapper["armature"]
            agent_meshes.append(me)
        # the action: per-class retimed walk/jog (per-agent wrapped
        # phase) or per-agent idle copy. NO shared actions — the
        # renames below would remap a shared action for every sharer.
        arm_i_ad = arm_i.animation_data_create()
        is_walk = speeds is not None and speeds[i] > STATIONARY_MPS
        if is_walk:
            ci = _class_of(class_speeds[i])
            base, bf0, bcyc = class_bases[ci][0], class_bases[ci][1], \
                class_bases[ci][2]
            a2 = _wrap_action(base, f"walk_{i:03d}", phases[i], bcyc,
                              bf0, bf0 + bcyc)
            n_walk += 1
        else:
            a2 = idle_act.copy()
            a2.name = f"idle_{i:03d}"
            n_idle += 1
        _pin_slot(arm_i_ad, a2)
        # D1-REV2: the rename — bind FIRST (above), then rename the
        # bones (auto-remaps THIS agent's bound action; the class bases
        # are unbound and untouched) + mirror on the vgroups (skinning
        # resolves vgroup NAME -> bone NAME at deform time)
        prefix = f"z{i:04d}:"
        vg_map = {}
        for b in list(arm_i.data.bones):
            vg_map[b.name] = prefix + b.name
            b.name = prefix + b.name
            bone_name_census[b.name] += 1
        for me in agent_meshes:
            # Blender 5.2 law: vertex_groups moved from Mesh to OBJECT
            # (probed live: mesh.vertex_groups == AttributeError)
            for vg in me.vertex_groups:
                if vg.name in vg_map:
                    vg.name = vg_map[vg.name]
        # wrap-band gate on the per-agent actions (frame_range reads the
        # keyed span only — CYCLES does not extend it, review r1 T1)
        if is_walk:
            bf0, bcyc = class_bases[ci][1], class_bases[ci][2]
            lo, hi = a2.frame_range
            if lo < bf0 - 1e-4 or hi >= bf0 + bcyc + 1e-4:
                _fail(f"wrap-band violated on agent {i}: "
                      f"{lo:.2f}..{hi:.2f} not inside "
                      f"[{bf0},{bf0 + bcyc})")
        # D3-REV2: the bind-time motion gate — every WALK-classified
        # rig's action must move (hips span >= WALK_SPAN_MIN_M over
        # its own class cycle). Kills the near-frozen-walk class.
        if is_walk:
            _span_gate(arm_i, a2, class_bases[ci][1],
                       class_bases[ci][2], i)
        reps.append({"anchor": anchor, "ordinal": i, "cycle":
                     (class_bases[ci][1], class_bases[ci][1] +
                      class_bases[ci][2]) if is_walk else (1, 1 + IDLE_TRIM),
                     "class": ci if is_walk else -1, **wrapper})
    # D1-REV2: the uniqueness census — fail-closed. No duplicated bone
    # name may leave this function (the GLB consumer binds by name).
    dupes = {nm: c for nm, c in bone_name_census.items() if c > 1}
    if dupes:
        _fail(f"bone-name census: {len(dupes)} DUPLICATES after the "
              f"per-agent renames (first: {sorted(dupes)[:4]}) — the "
              f"GLB name-binding class is back")
    # quaternion modes census (the s18 law) per agent — the data swap
    # rebuilds poses, so the census reads the INSTANCES
    bad_modes = 0
    for rep in reps:
        for pb in rep["armature"].pose.bones:
            if pb.rotation_mode != 'QUATERNION':
                bad_modes += 1
    # remove the TEMPLATE objects (review r1 P1-8: a full-height rest-
    # pose x_bot at the world origin in every render AND the GLB)
    bpy.data.objects.remove(tmpl["arm"], do_unlink=True)
    for tm in tmpl["meshes"]:
        bpy.data.objects.remove(tm, do_unlink=True)
    if bad_modes:
        _P(f"WARN quaternion modes: {bad_modes} pose-bones "
           f"non-QUATERNION — the s18 law says the loader RECORDS "
           f"and warns, fixing is per-rig")
    _P(f"bound {n} rigs: {n_walk} walk / {n_idle} idle; "
       f"combined {tmpl['combined_verts']} verts/agent; "
       f"D1-REV2 receipt: {n} armature-data + {n * len(tmpl['meshes'])} "
       f"mesh-data copies, {bone_name_census and len(bone_name_census)} "
       f"unique bone names, 0 duplicates")
    _P(f"retiming report: v_nat walk={v_nat:.2f} "
       f"top={v_nat_top:.2f} m/s; classes: " +
       "; ".join(f"c{ci}(n={len(class_members[ci])},"
                 f"v={class_bases[ci][4]:.2f},"
                 f"{'jog' if class_bases[ci][5] else 'walk'},"
                 f"s={class_bases[ci][3]:.2f})"
                 for ci in range(n_classes) if class_bases[ci]))
    return {"n": n, "n_walk": n_walk, "n_idle": n_idle,
            "verts": tmpl["combined_verts"], "reps": reps,
            "walk_cycle": (f0, f1),
            "classes": {ci: {"n": len(class_members[ci]),
                             "v_class": class_bases[ci][4],
                             "scale": class_bases[ci][3],
                             "is_jog": class_bases[ci][5],
                             "cycle": (class_bases[ci][1],
                                       class_bases[ci][1] +
                                       class_bases[ci][2])}
                        for ci in range(n_classes) if class_bases[ci]}}


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


def face_tangent(obj, min_mps=0.5, keep_last=True):
    """fix-wave-1 D2: re-derive rotation_euler.z from the LOCATION
    path tangent at every key whose outgoing segment moves >= min_mps
    (the bake2 law: z = atan2(dy,dx) - 90deg for +Y-forward rigs).
    Standing/watch segments keep the AUTHORED yaw (a watcher faces
    their subject, not a near-zero tangent). Hand-authored hero yaws
    drifted up to ~150deg from their own path tangents (measured:
    Master 147deg, Runner 82-152deg)."""
    import math as _m
    ad = obj.animation_data
    if ad is None or ad.action is None:
        _fail(f"face_tangent: {obj.name} has no keyed action")
    locs, rots = {}, {}
    for fc in _iter_fcurves(ad.action):
        if fc.data_path == "location":
            for kp in fc.keyframe_points:
                locs.setdefault(int(round(kp.co.x)), {})[fc.array_index] = kp.co.y
        elif fc.data_path == "rotation_euler" and fc.array_index == 2:
            for kp in fc.keyframe_points:
                rots[int(round(kp.co.x))] = kp.co.y
    fs = sorted(locs)
    if len(fs) < 2:
        return 0
    changed = 0
    fps = bpy.context.scene.render.fps or 24
    for i, f in enumerate(fs):
        if i + 1 >= len(fs):
            if not keep_last:
                continue
            # the last key faces the incoming tangent
            if i == 0:
                continue
            f0, f1 = fs[i - 1], fs[i]
            p0, p1 = locs[f0], locs[f1]
        else:
            f0, f1 = fs[i], fs[i + 1]
            p0, p1 = locs[f0], locs[f1]
        if len(p0) < 2 or len(p1) < 2:
            continue
        dt = (f1 - f0) / fps
        if dt <= 0:
            continue
        vx = (p1.get(0, 0.0) - p0.get(0, 0.0)) / dt
        vy = (p1.get(1, 0.0) - p0.get(1, 0.0)) / dt
        sp = _m.hypot(vx, vy)
        if sp < min_mps:
            continue
        z = _m.atan2(vy, vx) - _m.pi / 2.0
        # write through the fcurve key (same frame)
        for fc in _iter_fcurves(ad.action):
            if fc.data_path == "rotation_euler" and fc.array_index == 2:
                for kp in fc.keyframe_points:
                    if abs(kp.co.x - f) < 0.5:
                        kp.co.y = z
                        changed += 1
                        break
    # ---- the refine pass: 12-frame tangent grid ------------------
    # Key-level tangents still drift mid-segment: within segment
    # [a,b] the rotation interpolates from tangent(a->b) toward
    # tangent(b->c), crossing the CURRENT segment's constant tangent
    # with up to half the adjacent-segment direction change (measured
    # 31-84 deg on the Runner's weave). A 12-frame tangent grid keys
    # the LOCAL tangent everywhere the hero actually moves.
    import math as _m2
    loc_fcs = [fc for fc in _iter_fcurves(ad.action)
               if fc.data_path == "location"]
    rf = next((fc for fc in _iter_fcurves(ad.action)
               if fc.data_path == "rotation_euler"
               and fc.array_index == 2), None)
    xf = next((fc for fc in loc_fcs if fc.array_index == 0), None)
    yf = next((fc for fc in loc_fcs if fc.array_index == 1), None)
    if rf is None or xf is None or yf is None:
        return changed
    fps = bpy.context.scene.render.fps or 24
    f_first, f_last = fs[0], fs[-1]
    STEP = 12
    grid = list(range(f_first, f_last + 1, STEP))
    if grid and grid[-1] != f_last:
        grid.append(f_last)
    authored = {f: float(rf.evaluate(f)) for f in grid}
    # RNA staleness law (the _trim_action class): index-DESC removals
    for _i in reversed(range(len(rf.keyframe_points))):
        rf.keyframe_points.remove(rf.keyframe_points[_i])
    n_grid = 0
    for f in grid:
        f0b = max(f_first, f - 3)
        f1b = min(f_last, f + 3)
        if f1b <= f0b:
            f1b = f0b + 1
        x0, x1 = xf.evaluate(f0b), xf.evaluate(f1b)
        y0, y1 = yf.evaluate(f0b), yf.evaluate(f1b)
        dt = max(1e-6, (f1b - f0b) / fps)
        vx, vy = (x1 - x0) / dt, (y1 - y0) / dt
        if _m2.hypot(vx, vy) >= min_mps:
            z = _m2.atan2(vy, vx) - _m2.pi / 2.0
        else:
            z = authored[f]
        kp = rf.keyframe_points.insert(float(f), float(z))
        kp.interpolation = 'LINEAR'
        n_grid += 1
    rf.keyframe_points.sort()
    rf.update()
    if changed or n_grid:
        for fc in _iter_fcurves(ad.action):
            if fc.data_path == "rotation_euler" and fc.array_index == 2:
                fc.update()
        _P(f"face_tangent: {obj.name} re-faced {changed} keys + "
           f"{n_grid} grid keys (min {min_mps} m/s)")
    return changed


def _moving_speeds(ctx, n, fallback):
    """D3-REV2b: per-agent mean speed over MOVING ticks only
    (>0.3 m/s) — the cadence the clip must match. Falls back to the
    all-ticks mean when an agent never crosses the floor."""
    import numpy as np
    soa = ctx.get("crowd_soa")
    ticks = getattr(soa, "ticks", None)
    if ticks is None or "speed" not in ticks:
        return fallback
    sp = np.asarray(ticks["speed"])
    if sp.ndim != 2 or sp.shape[1] < n:
        return fallback
    out = []
    for i in range(n):
        col = sp[:, i]
        mv = col[col > 0.3]
        out.append(float(mv.mean()) if mv.size >= 24 else
                   float(fallback[i]))
    return out


def _hero_path_speed(hero):
    """The hero root's MOVING mean speed from its location keys
    (segments >= 0.45 m/s) — the auto-clip selector's input.
    Returns (v, moving)."""
    import math as _m
    if hero is None or hero.animation_data is None \
            or hero.animation_data.action is None:
        return 0.0, False
    locs = {}
    for fc in _iter_fcurves(hero.animation_data.action):
        if fc.data_path == "location":
            for kp in fc.keyframe_points:
                locs.setdefault(int(round(kp.co.x)), {})[fc.array_index] = \
                    kp.co.y
    fs = sorted(locs)
    if len(fs) < 2:
        return 0.0, False
    fps = bpy.context.scene.render.fps or 24
    segs = []
    for i in range(len(fs) - 1):
        f0, f1 = fs[i], fs[i + 1]
        p0, p1 = locs[f0], locs[f1]
        if len(p0) < 2 or len(p1) < 2:
            continue
        dt = (f1 - f0) / fps
        if dt <= 0:
            continue
        v = _m.hypot((p1.get(0, 0.0) - p0.get(0, 0.0)) / dt,
                     (p1.get(1, 0.0) - p0.get(1, 0.0)) / dt)
        if v >= 0.45:
            segs.append(v)
    if not segs:
        return 0.0, False
    # distance-weighted mean (long segments weigh more is wrong for
    # speed; plain mean of moving segments is the honest cadence)
    return float(sum(segs) / len(segs)), True


def ride_principals(ctx, pr, hero_rgb, roughness=0.5):
    """The s25 rollout's shared principal-riding block (was inline in
    tform_scene._humanoid_layer; every film repeats it — the D6
    branch-a law):

    - the UAL wrapper RIDES the film's keyed hero root exactly
      (identity parent-inverse + zero local; the loader's own facing
      flip lives inside the wrapper hierarchy);
    - the identity colors ride the UAL actor (tint_ual_actor — the
      tint module loads BY PATH, the clone-seam law);
    - the hero commuter mesh -> degenerate carrier (the GLB node must
      SURVIVE for the exporter's declared refs; hide_render excludes
      it — the carrier law).

    hero_rgb: {hero_name: (r, g, b)}; heroes missing from ctx die
    loud (a silently-unparented principal floats at the origin).
    Returns {name: {"wrapper", "hero"}} (numbers travel).
    """
    import importlib.util
    import bmesh
    _here = os.path.dirname(os.path.abspath(__file__))
    _spec = importlib.util.spec_from_file_location(
        "_ual_actors_tint", os.path.join(_here, "assets_ual_actors.py"))
    UALM = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(UALM)
    heroes = ctx.get("heroes") or ctx.get("humans") or {}
    # (tdawn is the family's "humans" outlier — both keys checked)
    out = {}
    for name, rep in pr.items():
        hero = heroes.get(name)
        if hero is None:
            _fail(f"ride_principals: no hero object {name!r} in "
                  f"ctx['heroes'] ({sorted(heroes)})")
        wrapper = rep["root"]
        wrapper.parent = hero
        wrapper.matrix_parent_inverse = Matrix.Identity(4)
        wrapper.location = (0.0, 0.0, 0.0)
        rgb = hero_rgb.get(name)
        if rgb is not None:
            UALM.tint_ual_actor(rep, rgb, roughness=roughness)
        me = bpy.data.meshes.new(f"{name}.carrier")
        bm = bmesh.new()
        bm.verts.new((0.0, 0.0, 0.0))
        bm.to_mesh(me)
        bm.free()
        hero.data = me
        out[name] = {"wrapper": wrapper, "hero": hero}
        _P(f"UAL principal {name} riding {hero.name} (tinted {rgb})")
    return out


def strip_dot_override(mat, anchor_prefix="Zed."):
    """The s25 strip law (the rollout audit's P1-2): post-bind, the
    strip-visible crowd surface is the RIG BODIES — the Zed.* anchors
    are 1-vert degenerate carriers (no faces) and a strip override
    that only dots the anchors renders an EMPTY crowd.

    Applies `mat` at the MESH-DATA level to:
      1. every mesh object that carries an ARMATURE modifier (the
         skinned bodies; structurally found — no naming convention
         to drift). The bodies share data PER GROUP (the tint law's
         copies), so one data write retints the whole group;
      2. the anchor carrier data (harmless: no faces to shade) so a
         pre-bind build keeps its legacy anchor-dot behavior.

    Returns the census {"bodies": n_data, "anchors": n_data} — the
    caller prints it (numbers travel).
    """
    # the WORKBENCH law (gotcha #56 / gauntlet R4): MATERIAL color_type
    # shades the viewport diffuse_color, NOT the Principled Base Color —
    # an unsynced override dot renders the 0.8 gray default and lands
    # INVISIBLE on the 0.8-gray yard. Sync from the node so the dots
    # carry their authored color (measured in the 6-c lane).
    if mat.use_nodes:
        _nb = mat.node_tree.nodes.get("Principled BSDF")
        if _nb is not None:
            _bc = _nb.inputs["Base Color"].default_value
            mat.diffuse_color = (_bc[0], _bc[1], _bc[2], 1.0)
    bodies, anchors, seen = set(), set(), set()
    for ob in bpy.data.objects:
        if ob.type != 'MESH' or ob.data.name in seen:
            continue
        seen.add(ob.data.name)
        has_arm = any(md.type == 'ARMATURE' for md in ob.modifiers)
        if has_arm and ob.data.name.startswith("Hum."):
            # the RH crowd bodies only — the UAL principals deform via
            # armature too but carry their own (non-Hum.) data; the
            # strips keep their identity colors (s25 scope law)
            bodies.add(ob.data.name)
        elif ob.name.startswith(anchor_prefix):
            anchors.add(ob.data.name)
    for name in bodies | anchors:
        me = bpy.data.meshes.get(name)
        if me is None:
            continue
        me.materials.clear()
        me.materials.append(mat)
    _P(f"strip_dot_override: {len(bodies)} rig-body data(s) + "
       f"{len(anchors)} anchor data(s) <- {mat.name}")
    return {"bodies": len(bodies), "anchors": len(anchors)}


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
        with _fps_guard():
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
        # fix-wave-1 D2: EXACT match only — the substring fallback hit
        # Pistol_Idle_Loop for the films requesting Idle_Loop and every
        # hero shipped the gun-point pose. A miss is LOUD.
        # clip=None -> AUTO: measure the hero root's keyed path speed,
        # pick Idle/Walk/Jog and retime the copy to the path (a Runner
        # gliding on a standing idle is the moonwalk class).
        retime_s = None
        if clip is None:
            hero = (ctx.get("heroes") or ctx.get("humans") or {}).get(name)
            v_path, moving = _hero_path_speed(hero)
            if not moving:
                clip = "Idle_Loop"
            elif v_path < 1.1:
                clip = "Walk_Loop"
            elif v_path < 2.6:
                clip = "Jog_Fwd_Loop"
            else:
                clip = "Sprint_Loop"
            nominal = {"Walk_Loop": 1.4, "Jog_Fwd_Loop": 3.0,
                       "Sprint_Loop": 5.0}.get(clip)
            if moving and nominal:
                retime_s = max(0.6, min(1.7, nominal / max(0.4, v_path)))
            _P(f"auto hero clip {name}: {clip} (v_path {v_path:.2f} m/s, "
               f"retime {retime_s and round(retime_s, 3)})")
        act = acts.get(clip)
        if act is None:
            _fail(f"UAL clip {clip!r} not in pool "
                  f"({sorted(acts)}) — the substring fallback is "
                  f"REMOVED (the Pistol_Idle_Loop class); add the clip "
                  f"to BEAT_ACTIONS or request an existing name")
        # ALWAYS a per-hero copy + CYCLES REPEAT — the pool actions
        # are ~22-frame one-shots: without looping the hero animates
        # for under a second then freezes for the rest of the film
        # (the "heroes do nothing" amplifier, measured: zspan 0.0 past
        # f38 on the retimed Jog).
        if retime_s is not None and retime_s != 1.0:
            act = act.copy()
            act.name = f"{clip}.rt{name}"
            f0r = int(act.frame_range[0])
            _retime_action(act, retime_s, f0r)
        else:
            act = act.copy()
            act.name = f"{clip}.{name}"
        _cycles_action(act)
        ad = arm.animation_data_create()
        _pin_slot(ad, act)
        # D1-REV2: per-hero unique bone names (prefix h<name>:) + the
        # vgroup mirror — the same GLB name-binding law as the crowd.
        # Bind FIRST (above), rename SECOND (the s20 remap law).
        prefix = f"h{name.lower()}:"
        vg_map = {}
        for b in list(arm.data.bones):
            vg_map[b.name] = prefix + b.name
            b.name = prefix + b.name
        mesh = rep.get("mesh")
        if mesh is not None and mesh.type == 'MESH':
            # 5.2 law: object-level accessor
            for vg in mesh.vertex_groups:
                if vg.name in vg_map:
                    vg.name = vg_map[vg.name]
        out[name] = rep
        _P(f"UAL principal {name}: clip {clip} "
           f"(facing {rep.get('facing_sign', '?')}, floor {floor:+.4f}, "
           f"bones prefixed {prefix!r})")
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
    # s25: the film layer knows the faller by its ANCHOR name (the
    # cache ordinal pairing); the reps know it by the wrapper root
    # name — match either (the exemption is by PERFORMER, not by
    # naming convention).
    def _is_exempt(r):
        return (r["root"].name in exempt_names
                or getattr(r.get("anchor"), "name", None) in exempt_names)
    walkers = [r for r in reps
               if r["armature"].animation_data.action.name.startswith("walk_")
               and not _is_exempt(r)]
    idlers = [r for r in reps if r not in walkers and not _is_exempt(r)]
    eligible = [r for r in reps if not _is_exempt(r)]
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
        if _is_exempt(rep):
            report.append({"root": rep["root"].name, "verdict": "EXEMPT",
                           "why": "film-keyed overlay performer — the "
                                  "walk-cycle assumptions cannot judge the "
                                  "tumble/overlay motion (s25 exempt law)"})
    for rep in picks:
        arm = rep["armature"]
        act = arm.animation_data.action
        is_walk = act.name.startswith("walk_")
        # D1-REV2: bones are per-agent prefixed (z0007:mixamorig:Hips)
        hips = arm.pose.bones.get("mixamorig:Hips")
        if hips is None:
            hips = next((b for b in arm.pose.bones
                         if b.name.lower().endswith("mixamorig:hips")),
                        None)
        if hips is None:
            _fail("gate rig lacks mixamorig:Hips")
        zs, lz, rz = [], [], []
        # s26 ALIASING LAW (measured): 5 samples across a 37-frame
        # 2-bob-per-cycle walk read hips bob at 0.018 while the TRUE
        # excursion is 0.045 (probe: 37 frames, all phases 0.045-0.046)
        # — the 5-grid misses both extremes. 11 samples bound the
        # extreme within ~1.9 frames; the band stays 0.02 (no relief —
        # the measurement was wrong, not the rig).
        # D3-REV2: sample the rep's OWN class cycle when it carries
        # one (per-class retimed cycles differ from the film default)
        cf0, cf1 = rep.get("cycle", (f0, f1))
        frames_s = [cf0 + (cf1 - cf0) * j // 10 for j in range(11)]
        for f in frames_s:
            sc.frame_set(f)
            bpy.context.view_layer.update()
            zs.append((arm.matrix_world @ hips.matrix).translation.z)
            for side, acc in (("Left", lz), ("Right", rz)):
                pb = arm.pose.bones.get(f"mixamorig:{side}Foot")
                if pb is None:
                    pb = next((b for b in arm.pose.bones
                               if b.name.lower().endswith(
                                   f"mixamorig:{side}foot".lower())),
                              None)
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
            # the tick->frame law: sample the frame the BAKE keyed the
            # final tick on. plan_frames (crowd_v6.bake2) decimates the
            # key grid to EVERY=2 (keys at EVEN ticks only: f1, f5, ...
            # f1077) and the law-106 hold forces the LAST tick onto
            # total_frames — so tick n_ticks-1 is keyed at frame_end
            # (f1080), NOT at 1+round((n_ticks-1)*dt*fps) (f1079: an
            # UNKEYED frame whose linear ride f1077->f1080 lands 2/3
            # across the final step — the tsquall Zed.0064 dx=5.9mm
            # dy=9.4mm drift class: any sampled agent still walking at
            # the last tick fails it; parked-at-end films read 0.0 and
            # masked the bug). Import the plan itself: the law stays
            # single-sourced with the bake, and the 5-r fps-warn +
            # frame_end clamp semantics are preserved.
            dt = float(ctx["crowd_cache"].dt) or (1.0 / 12.0)
            fps = float(sc.render.fps) or 24.0
            if fps != 24:
                _P(f"WARN gates: scene fps is {fps} (expected 24 — "
                   f"the timebase law); the probe window may be off")
            from crowd_v6.bake2 import plan_frames
            probe = int(plan_frames(n_ticks, dt)[-1][0])
            sc.frame_set(max(sc.frame_start,
                             min(int(sc.frame_end), probe)))
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
    _P("motion gates:", [
        (r.get("agent", r.get("root")), r.get("action", r.get("verdict")),
         r.get("hips_bob"), r.get("cache_xy_err"))
        for r in report])
    n_exc = sum(1 for r in report if r.get("verdict") == "EXEMPT")
    if n_exc:
        _P(f"motion gates: {n_exc} documented exemption row(s)",
           [r['root'] for r in report if r.get('verdict') == 'EXEMPT'])
    return report
