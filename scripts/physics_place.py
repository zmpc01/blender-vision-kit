"""physics_place.py — physics-gated placement: settle / place / oracle /
gate (design: docs/design_physics_place.md v3, gate-reviewed rounds 1-2).

Hybrid thesis (D1): GEOMETRY owns precision (placement_lib is the final
word on contact state); PHYSICS owns topology — it settles floats,
names obstructions (oracle), repairs simple penetrations (depenetration
lands at exact rest, probe: experiments/physics_facts/), and gates
whole scenes ("nothing can overlap, we simply reject").

Physics output is NEVER trusted for mm: every op ends with a
placement_lib audit of the real (committed) geometry.

Fact base F1-F14 (see design doc): frame_set stepping (no world_step in
4.5); frame_set(1) cache discipline before EVERY sim; collision shapes
snapshot the evaluated mesh at rb_add (data-bake scale + update first);
sim pose lives only in matrix_world (RNA stays at spawn) -> commit
pattern; point cache persists across teardown (fresh frame_set(1));
transform_apply zeroes RNA location in 4.5.13 (never use); non-mesh
selection aborts rb ops (deselect-all everywhere); rb RNA is read-only
(teardown via ops).
"""
import bpy, sys, json, time, math
from mathutils import Vector, Matrix, Quaternion

_HERE = __file__.rsplit("/", 1)[0]
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import placement_lib as pl  # noqa: E402


# --------------------------------------------------------------------------
# context discipline (F10/F14): deselect-all + set-active before EVERY rb op
# --------------------------------------------------------------------------

# Production collision margin for every RB body (settle/place/oracle/gate).
# This is LOAD-BEARING for rest heights: the margin-sum law (probe:
# placement-lab experiments/physics_facts/probe_hull_pop.py, session-14b)
# measures that hull contacts rest separated by ~SUM of the two bodies'
# margins (hull-hull ~2x margin, hull-primitive ~1x margin), while
# primitive (BOX) contacts rest exact. Every pop tolerance in this module
# derives from this constant — change it and the tolerances follow.
_RB_MARGIN = 0.001


def _pop_allow_mm():
    """Margin-pop allowance (round-B calibration + probe_hull_pop law):
    a rest separation up to ~SUM of the two bodies' margins is REST, not
    a defect. Computed at CALL time — tests retarget _RB_MARGIN to prove
    the law; an import-time constant would freeze the original
    calibration (T5r guards exactly this)."""
    return max(2.5, 2.0 * _RB_MARGIN * 1000.0 + 0.6)


# Above this upward-dominant motion is a sim LAUNCH, not a margin pop.
_EJECT_CAP_MM = 50.0


def _deselect_all():
    bpy.ops.object.select_all(action='DESELECT')


def _rb_add(obj, rb_type, shape, margin=None):
    """Attach a rigid-body component to one mesh object. Caller must have
    called view_layer.update() so the evaluated mesh (shape snapshot, F6)
    is current."""
    if margin is None:
        margin = _RB_MARGIN   # call-time read: tests may retarget the law
    _deselect_all()
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.rigidbody.objects_add()
    rb = obj.rigid_body
    rb.type = rb_type
    rb.collision_shape = shape
    rb.collision_margin = margin
    rb.use_margin = True
    rb.restitution = 0.0          # early-exit soundness assumes this (D8)
    rb.friction = 0.6
    rb.linear_damping = 0.04
    rb.angular_damping = 0.1
    return rb


def _ensure_world(frames):
    """Return (rigidbody_world, created_flag, frame_end_extended_flag).
    Asserts point_cache.frame_end >= frames (F13) by extending."""
    sc = bpy.context.scene
    created = False
    extended = False
    if sc.rigidbody_world is None:
        bpy.ops.rigidbody.world_add()
        created = True
    rbw = sc.rigidbody_world
    rbw.point_cache.frame_start = 1
    if rbw.point_cache.frame_end < frames + 2:
        rbw.point_cache.frame_end = frames + 2
        extended = True
    rbw.substeps_per_frame = 10
    rbw.solver_iterations = 10
    return rbw, created, extended


def _remove_rb(obj):
    _deselect_all()
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.rigidbody.objects_remove()


def _remove_world():
    sc = bpy.context.scene
    if sc.rigidbody_world is not None:
        bpy.ops.rigidbody.world_remove()


# --------------------------------------------------------------------------
# mover-set preparation (D2 / gate B3-B4)
# --------------------------------------------------------------------------

_SHAPE_CAP_VERTS = 5000


def _bbox_fill(obj):
    """Fraction of the object bbox filled by its mesh (crude: verts inside
    the mid-slab). >0.9 -> BOX-shaped for environment bodies."""
    mn, mx = pl._aabb(obj)
    dims = mx - mn
    vol_box = max(dims.x * dims.y * dims.z, 1e-12)
    import random
    random.seed(7)
    inside = 0
    n = 200
    for _ in range(n):
        p = Vector((random.uniform(mn.x, mx.x),
                    random.uniform(mn.y, mx.y),
                    random.uniform(mn.z, mx.z)))
        # point-in-mesh via ray parity (placement_lib classify is overkill;
        # a cheap 2-ray test is enough for a shape hint)
        hits = 0
        for dx in (0.017, 0.041):
            d = Vector((dx, 0.083, 1.0)).normalized()
            origin = p - d * 100.0
            loc, *_ = pl.world_bvh(obj).ray_cast(origin, d, 200.0)
            first = loc is not None
            if first:
                # count crossings: march past and cast again
                loc2, *_ = pl.world_bvh(obj).ray_cast(
                    loc + d * 1e-4, d, 200.0)
                hits = 1 if loc2 is None else 2
            if hits % 2 == 1:
                inside += 1
                break
    return inside / n


def _shape_for(obj, role):
    nverts = len(obj.data.vertices)
    # BOX is centered on the object ORIGIN, not the bbox (tiebreak TB3 /
    # gate-1 A1): an off-origin mesh gets collision geometry displaced
    # from the visual mesh (slab z 0..0.3 with origin at z=0 -> collision
    # z -0.15..+0.15; a ball rests 150 mm low and the post-audit correctly
    # reads PENETRATING). CONVEX_HULL is built from the evaluated mesh and
    # is origin-independent — always faithful. BOX only for origin-
    # centered geometry (origin within 5 mm of the bbox center).
    mn, mx = pl._aabb(obj)
    ctr = obj.matrix_world.translation
    origin_centered = all(
        abs(ctr[i] - (mn[i] + mx[i]) / 2.0) <= 0.005 for i in range(3))
    if role == 'env':
        try:
            if origin_centered and _bbox_fill(obj) > 0.9:
                return 'BOX'
        except Exception:  # noqa: BLE001 — hint only
            pass
        return 'CONVEX_HULL' if nverts <= _SHAPE_CAP_VERTS else 'BOX'
    if nverts > _SHAPE_CAP_VERTS:
        return 'BOX' if origin_centered else 'CONVEX_HULL'
    return 'CONVEX_HULL'


def _is_skinned(obj):
    for m in obj.modifiers:
        if m.type == 'ARMATURE':
            return True
    return False


def _prep(objs, environment=(), allow_bake=False, allow_copy=False):
    """Filter/validate the mover set. Returns (movers, env_objs, excluded).

    Mover-set rules (design D2/B3/B4):
    - mesh objects only (a selected non-mesh ABORTS rb ops, F14);
    - location-animated / skinned objects are EXCLUDED (sim + fcurves
      fight; commit would be clobbered at the next frame evaluation);
    - hidden / hidden-viewport objects excluded;
    - parented parts: only ROOT movers get bodies — children of movers
      ride along (independent child bodies would separate from the
      chassis mid-sim);
    - object scale must be baked into mesh DATA (RB shapes snapshot the
      evaluated mesh — F6): scale != 1 -> excluded as scale_unbaked,
      or auto-baked when allow_bake (via mesh.transform — NEVER
      transform_apply, gotcha #58); modifiers present refuse the bake;
    - multi-user mesh data refuses the bake unless allow_copy (swaps in
      a single-user copy for the sim; restored at teardown).
    """
    movers = []
    env_objs = []
    excluded = []
    if objs is None:
        candidates = [o for o in bpy.context.scene.objects
                      if o.type == 'MESH'
                      and not o.name.startswith(("Cam", "Temp"))]
    else:
        candidates = list(objs)
    env_names = {o.name for o in environment}
    # environment objects are handled FIRST (they are not candidates):
    for o in environment:
        if o.type != 'MESH':
            excluded.append({"obj": o.name, "reasons": ["non_mesh_env"]})
        elif o.hide_get() or o.hide_render:
            # production integration (escape-previz): hidden objects are
            # rig machinery (drivers/proxies), never visible set content —
            # a hidden "terrain" body would also crash _rb_add via the
            # ops poll ("cannot edit hidden object")
            excluded.append({"obj": o.name, "reasons": ["hidden_env"]})
        elif pl._location_anim_channels(o):
            # tiebreak TB4: an animated PASSIVE body is NOT static in the
            # sim (4.5 tracks the keyed transform — ball rest moved from
            # the static 0.352 to 0.2055 with a keyed env slab). Frozen
            # colliders would rest the mover on a transient pose; excluded
            # is the honest behavior (NO_SUPPORT beats a lie).
            excluded.append({"obj": o.name, "reasons": ["animated_env"]})
        else:
            env_objs.append(o)
    candidates = [o for o in candidates if o.name not in env_names]
    for o in candidates:
        reasons = []
        if o.hide_get() or o.hide_render:
            reasons.append("hidden")
        if _is_skinned(o):
            reasons.append("skinned")
        chans = pl._location_anim_channels(o)
        if chans:
            reasons.append("animated:" + ",".join(chans[:2]))
        if any(len(m.modifiers) for m in [o] if False):  # placeholder no-op
            pass
        if o.data is None:
            # design-gate F23 (Track I rider): an explicitly-passed non-mesh
            # (e.g. an add_empty anchor) used to raise AttributeError here —
            # an honest exclusion beats a crash.
            reasons.append("non_mesh")
        elif o.data.users > 1 and not allow_copy:
            reasons.append(f"multi_user_data({o.data.users})")
        scale = o.scale
        # Tiebreak TB1 (session-13b): collision shapes honor object scale
        # in EVERY construction path measured on 4.5.13 (ops data-baked,
        # RNA-write ± update, data-created ± update; hull and BOX) — the
        # session-12/13 "stale pre-scale shape" law did not reproduce.
        # Positive-scale objects are therefore SIM-READY as-is (imported
        # GLTF assets are all scaled; excluding them was pure friction).
        # Only degenerate/non-positive scale stays excluded (mirrored
        # winding is untested).
        if any(s <= 0.0 for s in scale):
            reasons.append("degenerate_scale")
        if reasons:
            excluded.append({"obj": o.name, "reasons": reasons})
            continue
        movers.append(o)
    # root collapse: drop movers whose PARENT is also a mover (they ride)
    mover_set = {m.name for m in movers}
    roots = []
    for m in movers:
        p = m.parent
        while p is not None and p.name not in mover_set:
            p = p.parent
        if p is None:
            roots.append(m)
        else:
            excluded.append({"obj": m.name,
                             "reasons": ["child_of_mover:rides"]})
    movers = roots
    # environment objects get the same mesh-only sanity (they are chosen
    # by name; anything non-mesh here is a caller error)
    env_objs = [o for o in env_objs if o.type == 'MESH']
    return movers, env_objs, excluded


def _bake_scales(movers, env_objs, allow_bake):
    """Bake object scale into mesh data for all RB participants (F6).
    Only called when allow_bake — _prep already excluded modifier/multi-
    user cases. Returns list of baked names."""
    baked = []
    for o in movers + env_objs:
        s = o.scale
        if max(abs(v - 1.0) for v in s) > 1e-6:
            o.data.transform(Matrix.Diagonal((s.x, s.y, s.z, 1.0)))
            o.scale = (1.0, 1.0, 1.0)
            baked.append(o.name)
    if baked:
        bpy.context.view_layer.update()
    return baked


# --------------------------------------------------------------------------
# sim core (D3/D8) + teardown (D4)
# --------------------------------------------------------------------------

_QUIET_MM = 0.1        # early-exit threshold per frame
_QUIET_FRAMES = 5      # consecutive quiet frames required (x2 = creep check)


def _preflight_pens(pairs):
    """Hard-overlap pairs at the requested pose (the pre-flight filter).
    Surface penetrations carry penetration_mm; face-CROSSING penetrations
    (round-D honest fields) carry crossing_depth_mm with penetration_mm
    = None. The session-14b round-E subject caught the pre-flight missing
    crossing pairs (a demand teleported into a wall ran the sim and the
    wedged eject flung it 16.4 m — TOPPLED instead of REFUSED)."""
    out = []
    for p in pairs:
        if p.get("state") not in ("PENETRATING", "NESTED"):
            continue
        pen = p.get("penetration_mm") or 0.0
        xdepth = p.get("crossing_depth_mm") or 0.0
        if (pen > 0.1 or xdepth > 0.1
                or p.get("state") == "NESTED"):
            out.append(p)
    return out


def _sim(movers, env_objs, frames, sim_seconds=None, report=None):
    """Run the settle sim. Returns (end_matrices, sim_stats).

    F8 discipline: frame_set(1) reset before stepping (point cache
    persists across teardowns). Early exit (D8): all movers < 0.1mm for
    5 consecutive frames AND a following 5-frame creep check also quiet
    (bullet deactivation can fake the first window)."""
    rbw, created, extended = _ensure_world(frames)
    if sim_seconds is not None:
        fps = max(bpy.context.scene.render.fps, 1)
        frames = max(10, int(sim_seconds * fps))
        if rbw.point_cache.frame_end < frames + 2:
            rbw.point_cache.frame_end = frames + 2
            extended = True
    if report is not None:
        report["frame_end_extended"] = extended
    for o in movers + env_objs:
        bpy.context.view_layer.update()      # F6: evaluated mesh current
        _rb_add(o, 'PASSIVE' if o in env_objs else 'ACTIVE',
                _shape_for(o, 'env' if o in env_objs else 'mover'))
    sc = bpy.context.scene
    entry_frame = sc.frame_current
    sc.frame_set(1)                          # F8: cache discipline
    bpy.context.view_layer.update()
    start_mw = {o.name: o.matrix_world.copy() for o in movers}
    quiet_run = 0
    used = 0
    prev = {o.name: o.matrix_world.translation.copy() for o in movers}
    early_exit = False
    for f in range(2, frames + 2):
        sc.frame_set(f)
        bpy.context.view_layer.update()
        used = f - 1
        max_step = 0.0
        for o in movers:
            t = o.matrix_world.translation
            max_step = max(max_step, (t - prev[o.name]).length)
            prev[o.name] = t.copy()
        quiet_run = quiet_run + 1 if max_step * 1000 < _QUIET_MM else 0
        if quiet_run >= _QUIET_FRAMES:
            # creep check: one more quiet window before trusting rest
            creep_ok = True
            for f2 in range(f + 1, f + 1 + _QUIET_FRAMES):
                if f2 > frames + 1:
                    break
                sc.frame_set(f2)
                bpy.context.view_layer.update()
                used = f2 - 1
                step = max(((o.matrix_world.translation -
                             prev[o.name]).length for o in movers),
                           default=0.0)
                for o in movers:
                    prev[o.name] = o.matrix_world.translation.copy()
                if step * 1000 >= _QUIET_MM:
                    creep_ok = False
                    break
            if creep_ok:
                early_exit = True
            break
    end_mw = {o.name: o.matrix_world.copy() for o in movers}
    for o in env_objs:
        end_mw[o.name] = o.matrix_world.copy()
    stats = {"sim_frames_used": used, "early_exit": early_exit,
             "world_created": created, "entry_frame": entry_frame,
             "fps": sc.render.fps}
    return start_mw, end_mw, stats


def _teardown(all_rb_objs, start_mw_all, end_mw_all, entry_frame,
              world_created, apply_mode, escaped_names=()):
    """D4: unconditional teardown. Writes end matrices (apply='end') or
    start matrices (apply='none'); restores the timeline; escaped movers
    are restored even under apply='end' (they must not be left wherever
    they flew). RB components removed from movers AND environment."""
    poses = {}
    for o in all_rb_objs:
        poses[o.name] = (end_mw_all[o.name]
                         if (apply_mode == 'end' and
                             o.name not in escaped_names)
                         else start_mw_all[o.name])
        _remove_rb(o)
    if world_created:
        _remove_world()
    for o in all_rb_objs:
        o.matrix_world = poses[o.name]
    bpy.context.scene.frame_set(entry_frame)
    bpy.context.view_layer.update()
    pl.clear_bvh_cache()
    return {"rb_removed": len(all_rb_objs),
            "world_removed": bool(world_created),
            "timeline_restored_to": entry_frame,
            "escaped_restored": sorted(escaped_names)}


# --------------------------------------------------------------------------
# neighbors / audits / verdict helpers
# --------------------------------------------------------------------------

def _neighbors(targets, others, pad_mm):
    """Mesh objects whose AABB (inflated by pad) intersects any target
    AABB — the pre-flight/final audit set (placement_lib audit_scene
    discovery is scene-wide; ops need per-mover sets)."""
    pad = pad_mm / 1000.0
    tgt_aabbs = [(t, pl._aabb(t)) for t in targets]
    out = []
    for o in others:
        if o in targets or o.type != 'MESH':
            continue
        ab = pl._aabb(o)
        for _t, ta in tgt_aabbs:
            if (ab[0].x - pad <= ta[1].x and ab[1].x + pad >= ta[0].x
                    and ab[0].y - pad <= ta[1].y
                    and ab[1].y + pad >= ta[0].y
                    and ab[0].z - pad <= ta[1].z
                    and ab[1].z + pad >= ta[0].z):
                out.append(o)
                break
    return out


def _pairs_audit(a_objs, b_objs, pad_mm=150.0):
    """audit_scene over explicit pairs (a in a_objs × b in b_objs, AABB-
    padded). Returns audit_scene dict."""
    pairs = []
    names_a = {o.name for o in a_objs}
    for a in a_objs:
        for b in _neighbors([a], b_objs, pad_mm):
            pairs.append((a.name, b.name))
    if not pairs:
        return {"pairs_checked": 0, "pairs": [], "failed": False,
                "state_counts": {}}
    return pl.audit_scene(pairs=pairs, clearance_pad_mm=pad_mm)


def _snap_supports(mover, others, pad_mm, snap_cap_mm):
    """Snap support analysis (session-13b): distinguish a legitimate
    cantilever (one contact + an unrelated far-below surface) from a
    TRUE multi-level rest (the mover contacts supports at different
    heights — snapping either way buries or floats a half).

    Support set = post-pose audit pairs within the snap band (TOUCHING
    or clearance <= snap_cap) whose object sits BELOW the mover
    (AABB-center). Multi-level iff >= 2 supports with top surfaces
    spread > 5 mm. Returns (support_objs, below_heights, multi_level).
    """
    audit = _pairs_audit([mover], others, pad_mm)
    mn, mx = pl._aabb(mover)
    mover_ctr_z = (mn.z + mx.z) / 2.0
    sup_objs = []
    for p in audit.get("pairs", []):
        other = p["b"] if p["a"] == mover.name else p["a"]
        ob = bpy.data.objects.get(other)
        if ob is None:
            continue
        if p.get("state") == "TOUCHING" or p.get("state") == "PENETRATING" \
                or (p.get("clearance_mm") is not None
                    and p["clearance_mm"] <= snap_cap_mm):
            octr = pl._aabb(ob)
            if (octr[0].z + octr[1].z) / 2.0 < mover_ctr_z:
                sup_objs.append(ob)
    pts = [(mn.x + (mx.x - mn.x) * (i + 0.5) / 8,
            mn.y + (mx.y - mn.y) * (j + 0.5) / 8)
           for i in range(8) for j in range(8)]
    multi = False
    if len(sup_objs) >= 2:
        tops = [pl._aabb(o)[1].z for o in sup_objs]
        multi = (max(tops) - min(tops)) > 0.005
    heights = []
    if sup_objs:
        hs, _d, _n = pl.support_heights(sup_objs, pts,
                                        from_z=mx.z + 0.01)
        # only surfaces at/below the mover's own bottom are snap
        # targets (a hit above belongs to a neighbour beside/above —
        # the sandwich case, round C)
        heights = [h for h in hs if h is not None and h <= mn.z + 0.001]
    return sup_objs, heights, multi


def _bottom_z(obj):
    return pl._aabb(obj)[0].z


def _rotation_delta_deg(m1, m2):
    q1 = m1.to_quaternion()
    q2 = m2.to_quaternion()
    return math.degrees(q1.rotation_difference(q2).angle)


def _tilt_deg(m):
    """Tilt of the object's local +Z away from world +Z (deg).
    TOPPLED/orientation semantics are TILT-based: yaw drift during a
    settle is harmless (an upright cube that yaws is still upright)."""
    zaxis = m.col[2].normalized()
    return math.degrees(math.acos(max(-1.0, min(1.0, zaxis.z))))


def _rest_support(obj, candidates):
    """Name of what obj currently rests on: support under the footprint
    via support_heights (placement_lib raycasts). Two guards:
    - per-candidate below-filter: raycasts start ABOVE the object, so a
      surface ABOVE the object's bottom (a bracket over the demanded
      pose) must never count as support (round-C subject F);
    - the filter applies to EACH CANDIDATE's own hit (detail), not to
      the topmost hit per point — the topmost hit for a stacked book is
      the book ABOVE it, and nulling that would discard the desk/book
      below as a support (T5c lesson).
    """
    mn, mx = pl._aabb(obj)
    pts = [(mn.x + (mx.x - mn.x) * (i + 0.5) / 4,
            mn.y + (mx.y - mn.y) * (j + 0.5) / 4)
           for i in range(4) for j in range(4)]
    _heights, detail, _ = pl.support_heights(candidates, pts,
                                             from_z=mx.z + 1.0)
    best = None
    for per in detail:
        for name, z in per.items():
            if z is not None and z <= mn.z + 0.001:
                if best is None or z > best:
                    best = z
    if best is None:
        return None, None
    per_count = {}
    for per in detail:
        for name, z in per.items():
            if z is not None and z <= mn.z + 0.001 \
                    and abs(z - best) < 1e-4:
                per_count[name] = per_count.get(name, 0) + 1
    return max(per_count, key=per_count.get), best


# --------------------------------------------------------------------------
# Op 1 — settle
# --------------------------------------------------------------------------

def settle(objs=None, environment=(), *, frames=45, apply='end',
           tol_mm=1.0, repair_penetrations='refuse', allow_bake=False,
           allow_copy=False, pad_mm=150.0, snap=True, snap_cap_mm=8.0,
           output=None):
    """Settle a mover set through gravity (design Op 1).

    objs: mover objects (None = all eligible mesh objects; eligibility
    filter in _prep — hidden/animated/skinned/scale-unbaked/multi-user
    objects are EXCLUDED with reasons, children of movers ride along).
    environment: objects made PASSIVE (never move).
    apply: 'end' commits the settled pose to the scene; 'none' restores
    the pre-sim scene (pure verifier).
    repair_penetrations: 'refuse' (default) aborts if any mover starts
    penetrating; 'physics' lets bullet depenetrate (REPAIRED_BY_PHYSICS
    verdicts, applied repairs only — apply='none' yields
    REPAIR_SIMULATED); 'lift' pre-lifts by pen+1mm.
    Returns a JSON-safe report."""
    t0 = time.time()
    report = {"op": "physics_settle", "apply": apply,
              "repair_penetrations": repair_penetrations,
              "tol_mm": tol_mm}
    if apply not in ('end', 'none'):
        raise ValueError(f"apply must be 'end'|'none', got {apply!r}")
    if repair_penetrations not in ('refuse', 'physics', 'lift'):
        raise ValueError("repair_penetrations must be "
                         "'refuse'|'physics'|'lift'")

    # AUTO-TERRAIN (usability round A): when the agent NAMES movers,
    # everything else is terrain by default — a named-mover sim without
    # a world void-falls (16.85 m, reported SETTLED/PASS). Explicit
    # `environment` always wins; objs=None keeps whole-scene semantics.
    if objs is None:
        report["whole_scene_warning"] = (
            "objs:null settles EVERY eligible mesh INCLUDING ground "
            "planes — the scene will free-fall as a whole (verdicts "
            "will read ESCAPED). Name your movers instead; named "
            "movers auto-treat the rest as terrain.")
    if objs is not None and not environment:
        all_mesh = [o for o in bpy.context.scene.objects
                    if o.type == 'MESH' and o not in objs]
        environment = all_mesh
        report["auto_terrain"] = True
    movers, env_objs, excluded = _prep(objs, environment, allow_bake,
                                       allow_copy)
    report["excluded"] = excluded
    report["movers"] = [m.name for m in movers]
    report["environment"] = [e.name for e in env_objs]
    if not movers:
        report.update(ok=False, verdict="NO_MOVERS",
                      verdict_reason="no eligible mover objects")
        return _finish(report, t0, output)

    baked = _bake_scales(movers, env_objs, allow_bake)
    report["scale_baked"] = baked

    others = [o for o in bpy.context.scene.objects
              if o.type == 'MESH' and o not in movers]
    # audit movers against EVERYTHING (terrain AND each other — round-A2:
    # a 3.94mm mover-on-mover gap shipped inside a PASS report)
    pre = _pairs_audit(movers, movers + others, pad_mm)
    pen_pre = _preflight_pens(pre.get("pairs", []))
    if pen_pre and repair_penetrations == 'refuse':
        report.update(ok=False, verdict="REFUSED_PENETRATING",
                      verdict_reason=(
                          "mover starts penetrating; use "
                          "repair_penetrations='physics' (recorded "
                          "repair) or fix geometrically first"))
        report["penetrating_pairs"] = pen_pre
        return _finish(report, t0, output)

    # capture pre-sim state for ALL rb participants + scene bounds
    bpy.context.view_layer.update()
    start_all = {o.name: o.matrix_world.copy() for o in movers + env_objs}
    bounds = _scene_bounds()
    pen0 = {(p["a"], p["b"]): p.get("penetration_mm") for p in pen_pre}

    start_mw, end_mw, stats = _sim(movers, env_objs, frames,
                                   report=report)
    report.update(stats)

    # classify movers BEFORE teardown (end matrices from the sim)
    per_obj = []
    lo = Vector(bounds["min"]) if bounds.get("min") else None
    hi = Vector(bounds["max"]) if bounds.get("max") else None
    for o in movers:
        m0, m1 = start_all[o.name], end_mw[o.name]
        d = m1.translation - m0.translation
        disp = d.length * 1000.0
        disp_xy = math.hypot(d.x, d.y) * 1000.0
        rot = _rotation_delta_deg(m0, m1)
        tilt = _tilt_deg(m1)
        dz = d.z * 1000.0
        # end bbox bottom: end matrix x local bbox corners (exact under
        # rotation; usability round A: the old field read the ORIGIN z)
        lb = o.bound_box
        end_bottom = min((m1 @ Vector(c)).z for c in lb)
        v = {"obj": o.name, "displacement_mm": round(disp, 2),
             "disp_xy_mm": round(disp_xy, 2),
             "disp_z_mm": round(dz, 2),
             "rotation_delta_deg": round(rot, 2),
             "rotation_tilt_deg": round(tilt, 2),
             "end_bottom_z": round(end_bottom, 4),
             "end_pos_m": [round(c, 4) for c in m1.translation]}
        started_pen = any(o.name in pair for pair in pen0)
        # ESCAPED: end pose left the pre-sim scene bounds (+1m margin),
        # or fell > 10 m (void fall — usability round A: a mover with no
        # collider under it fell 16.85 m and was reported SETTLED/PASS)
        escaped = (lo is not None and (
            m1.translation.x < lo.x or m1.translation.x > hi.x
            or m1.translation.y < lo.y or m1.translation.y > hi.y
            or m1.translation.z < lo.z or m1.translation.z > hi.z)) \
            or disp > 10000.0
        if escaped:
            v["verdict"] = "ESCAPED"
        elif started_pen and disp > tol_mm:
            if apply == 'end':
                v["verdict"] = "REPAIRED_BY_PHYSICS"
                v["start_pen_mm"] = next(
                    p for (a, b), p in pen0.items()
                    if o.name in (a, b))
                v["applied"] = True
            else:
                v["verdict"] = "REPAIR_SIMULATED"
                v["applied"] = False
                v["scene_state"] = "pre_sim_restored"
                v["start_pen_mm"] = next(
                    p for (a, b), p in pen0.items()
                    if o.name in (a, b))
        elif disp <= tol_mm and tilt <= 0.5:
            v["verdict"] = "AT_REST"
        elif tilt > 10.0:
            v["verdict"] = "TOPPLED"
        elif dz <= -tol_mm:
            v["verdict"] = "SETTLED"
        elif disp_xy > tol_mm:
            # SLIPPED is LATERAL (slid off a slope). The +2mm contact
            # margin pop of an already-resting body is vertical and is
            # sim noise, not a slip (usability round A: all six resting
            # objects read SLIPPED on a +2.0mm dz pop).
            v["verdict"] = "SLIPPED"
        else:
            v["verdict"] = "AT_REST"
            v["note"] = "sub-tolerance sim jitter"
        per_obj.append(v)
    report["objects"] = per_obj

    # teardown FIRST (commit/restore), then audit the REAL geometry
    td = _teardown(movers + env_objs, start_all, end_mw, stats["entry_frame"],
                   stats["world_created"], apply,
                   escaped_names={v["obj"] for v in per_obj
                                  if v["verdict"] == "ESCAPED"})
    report["teardown"] = td

    # guarded snap (D7, shared with place()): close hull residual gaps
    # (F4 ~1-2mm) so "settled" means EXACT contact — nothing may hover.
    # Vertical-only, gap <= snap_cap, upright movers only, re-audited.
    snaps = {}
    if snap and apply == 'end':
        bpy.context.view_layer.update()
        # bottom-up: a stack closes from its lowest member first, so
        # upper books measure their gap against already-exact supports
        snap_order = sorted(
            (v for v in per_obj
             if v["verdict"] in ("AT_REST", "SETTLED", "SLIPPED",
                                 "REPAIRED_BY_PHYSICS")
             and v.get("rotation_tilt_deg", 0) <= 10.0),
            key=lambda v: v["end_bottom_z"])
        skipped = {}
        for v in snap_order:
            o = bpy.data.objects[v["obj"]]
            # fresh trees each step: the previous snap moved its object,
            # and a stale BVH measures the gap to the PRE-snap pose
            # (round-A2: stacks shipped 1.97mm residuals this way)
            pl.clear_bvh_cache()
            bpy.context.view_layer.update()
            mn, mx = pl._aabb(o)
            sup_names = [n for n in (movers + others)
                         if n.name != o.name]
            sup_objs, below, multi = _snap_supports(o, sup_names, pad_mm,
                                                    snap_cap_mm)
            # multi-level rest (gate-1 A6 / test n): the mover contacts
            # supports at different heights — snapping to the highest
            # buries the low half, to the lowest floats the high half.
            # Keep the bullet pose (the sub-margin hull gap is
            # previz-acceptable).
            if multi:
                skipped[o.name] = "skipped_multi_level"
                continue
            gaps = [mn.z - h for h in below]
            if not gaps:
                continue
            gap = min(gaps)
            if 0 < gap * 1000 <= snap_cap_mm:
                o.matrix_world = Matrix.Translation(
                    (0, 0, -gap)) @ o.matrix_world
                snaps[o.name] = round(gap * 1000, 3)
            elif gap * 1000 > snap_cap_mm:
                skipped[o.name] = round(gap * 1000, 3)
        report["snap_skipped_mm"] = skipped
        if snaps:
            bpy.context.view_layer.update()
            pl.clear_bvh_cache()
    report["snap_applied_mm"] = snaps

    post = _pairs_audit(movers, movers + others, pad_mm)
    report["post_audit"] = post
    pen_post = [p for p in post.get("pairs", [])
                if p.get("state") == "PENETRATING"]
    for v in per_obj:
        if v["verdict"] in ("AT_REST", "SETTLED", "SLIPPED", "TOPPLED"):
            if any(o_name in (p["a"], p["b"])
                   for p in pen_post for o_name in (v["obj"],)):
                v["verdict"] = "PENETRATING_AT_END"
    failed = (any(v["verdict"] in ("ESCAPED", "PENETRATING_AT_END",
                                   "TOPPLED") for v in per_obj)
              or bool(pen_post))
    # mid-air rest check (round C: a deep-pen repair ejected the mug
    # 2.17m sideways; it ended CLEAR 55mm above the floor and the op
    # said PASS). Anything whose verdict claims rest/support must have
    # a support AT or under it; else NO_SUPPORT_AT_END.
    for v in per_obj:
        if v["verdict"] not in ("AT_REST", "SETTLED", "SLIPPED",
                                "REPAIRED_BY_PHYSICS"):
            continue
        o = bpy.data.objects[v["obj"]]
        sup_names = [n for n in (movers + others) if n.name != o.name]
        sup, sup_z = _rest_support(o, sup_names)
        # fresh post-snap bottom (v["end_bottom_z"] is PRE-snap — the
        # snap moved the object after it was recorded; round-C phantom
        # 5.97mm gaps came from comparing across the snap)
        end_bottom = pl._aabb(o)[0].z
        if sup is None or (sup_z is not None and
                           end_bottom - sup_z > 0.005):
            v["verdict"] = "NO_SUPPORT_AT_END"
            v["rests_on"] = sup
            v["rest_gap_mm"] = (round((end_bottom - sup_z) * 1000, 2)
                                if sup_z is not None else None)
            failed = True
    report["verdict"] = "FAIL" if failed else "PASS"
    report["penetrating_pairs_post"] = pen_post
    if failed:
        report["fix_queue"] = _fix_queue(per_obj, pen_post)
    report["ok"] = not failed
    return _finish(report, t0, output)


def _scene_bounds():
    """Scene AABB over all mesh objects (+1m margin). ESCAPED = final AABB
    outside it (design B6c)."""
    sc = bpy.context.scene
    meshes = [o for o in sc.objects if o.type == 'MESH']
    if not meshes:
        return {"min": None, "max": None, "escaped": set()}
    mns, mxs = zip(*[pl._aabb(o) for o in meshes])
    lo = Vector((min(m.x for m in mns), min(m.y for m in mns),
                 min(m.z for m in mns))) - Vector((1, 1, 1))
    hi = Vector((max(m.x for m in mxs), max(m.y for m in mxs),
                 max(m.z for m in mxs))) + Vector((1, 1, 1))
    escaped = set()
    for o in meshes:
        mn, mx = pl._aabb(o)
        if (mx.x < lo.x or mn.x > hi.x or mx.y < lo.y or mn.y > hi.y
                or mx.z < lo.z or mn.z > hi.z):
            escaped.add(o.name)
    return {"min": tuple(lo), "max": tuple(hi), "escaped": escaped}


def _fix_queue(per_obj, pen_post):
    """Executable patch fragments (gate nb-1): each item runs through
    apply_patch.apply_mutation."""
    q = []
    for p in pen_post:
        q.append({"op": "physics_settle", "objs": [p["a"]],
                  "repair_penetrations": "physics",
                  "note": f"depenetrate {p['a']} from {p['b']} "
                          f"({p.get('penetration_mm')} mm)"})
    for v in per_obj:
        if v["verdict"] == "ESCAPED":
            q.append({"note": f"{v['obj']} escaped the scene — inspect "
                              f"manually (no auto-fix)"})
        elif v["verdict"] == "TOPPLED":
            q.append({"op": "physics_settle", "objs": [v["obj"]],
                      "note": "toppled during verify — re-settle or "
                              "re-support"})
    return q


def _finish(report, t0, output=None):
    report["timings_ms"] = round((time.time() - t0) * 1000, 1)
    if output:
        pl._maybe_write(report, output)
    return report


# --------------------------------------------------------------------------
# Op 2 — place (placement through physics)
# --------------------------------------------------------------------------

def place(obj, *, drop_mm=30.0, frames=45, snap=True, snap_cap_mm=8.0,
          apply='end', tol_mm=1.0, allow_bake=False, allow_copy=False,
          pad_mm=150.0, output=None):
    """Place one object through physics over its current (x,y) (Op 2):
    pre-flight refuse on penetration -> lift -> settle -> guarded snap ->
    final audit vs the FULL neighbor set. Verdicts: PLACED /
    PLACED_OVERLAP / NO_SUPPORT / ESCAPED."""
    t0 = time.time()
    report = {"op": "physics_place", "obj": obj.name, "apply": apply,
              "drop_mm": drop_mm}
    all_mesh = [o for o in bpy.context.scene.objects
                if o.type == 'MESH' and o.name != obj.name]
    movers, env_objs, excluded = _prep([obj], environment=all_mesh,
                                       allow_bake=allow_bake,
                                       allow_copy=allow_copy)
    report["excluded"] = excluded
    if not movers:
        report.update(ok=False, verdict="REFUSED",
                      verdict_reason="object not eligible (see excluded)")
        return _finish(report, t0, output)
    mover = movers[0]
    others = [o for o in bpy.context.scene.objects
              if o.type == 'MESH' and o.name != mover.name]
    if not env_objs:
        report.update(ok=False, verdict="REFUSED_ENV",
                      verdict_reason=(
                          "no viable environment to collide against "
                          "(all other meshes excluded — see excluded); "
                          "a sim without a world free-falls"))
        return _finish(report, t0, output)
    neighbors = _neighbors([mover], others, pad_mm)
    report["neighbors"] = [n.name for n in neighbors]

    pre = _pairs_audit([mover], others, pad_mm)
    pen_pre = _preflight_pens(pre.get("pairs", []))
    if pen_pre:
        report.update(ok=False, verdict="REFUSED_PENETRATING",
                      verdict_reason=(
                          "object starts penetrating; settle with "
                          "repair_penetrations='physics' or repair "
                          "geometrically first"),
                      penetrating_pairs=pen_pre)
        return _finish(report, t0, output)

    intended, _ = _rest_support(mover, neighbors)
    report["intended_support"] = intended

    # lift clamp (gate AM5): clear the tallest neighbor support under us
    lift = drop_mm
    if neighbors:
        mn, mx = pl._aabb(mover)
        pts = [(mn.x + (mx.x - mn.x) * (i + 0.5) / 4,
                mn.y + (mx.y - mn.y) * (j + 0.5) / 4)
               for i in range(4) for j in range(4)]
        heights, _d, _n = pl.support_heights(neighbors, pts,
                                             from_z=mx.z + 1.0)
        hs = [h for h in heights if h is not None]
        if hs:
            lift = max(drop_mm, (max(hs) - mn.z) * 1000.0 + 5.0)
    report["lift_mm_used"] = round(lift, 2)

    start_all = {mover.name: mover.matrix_world.copy()}
    for e in env_objs:
        start_all[e.name] = e.matrix_world.copy()
    mover.matrix_world = Matrix.Translation((0, 0, lift / 1000.0)) \
        @ mover.matrix_world
    bpy.context.view_layer.update()

    start_mw, end_mw, stats = _sim([mover], env_objs, frames, report=report)
    report.update(stats)

    # teardown (commit), then measure on REAL geometry
    escaped = set()
    if (end_mw[mover.name].translation -
            mover.matrix_world.translation).length > 10.0:
        escaped.add(mover.name)
    td = _teardown([mover] + env_objs, start_all, end_mw,
                   stats["entry_frame"], stats["world_created"], apply,
                   escaped_names=escaped)
    report["teardown"] = td
    if escaped:
        report.update(ok=False, verdict="ESCAPED")
        return _finish(report, t0, output)

    pl.clear_bvh_cache()
    bpy.context.view_layer.update()

    # post-drop neighbor refresh (session-13b T5m lesson): neighbors/
    # intended were computed from the SPAWN pose with a 150 mm pad — a
    # mover lifted/dropped from higher up lands on support objects that
    # were NOT neighbors at spawn (the 700 mm drop read NO_SUPPORT on a
    # clean rest). Recompute from the landed pose; intended defaults to
    # what the mover actually landed on.
    neighbors = _neighbors([mover], others, pad_mm)
    report["neighbors_landed"] = [n.name for n in neighbors]
    if intended is None:
        intended, _ = _rest_support(mover, neighbors)
        report["intended_support"] = intended

    # guarded snap (D7 + R1): contact-level gap via footprint raycasts
    if snap and apply == 'end':
        mn, mx = pl._aabb(mover)
        sup_names = [o for o in others if o.name != mover.name]
        sup_objs, below, multi = _snap_supports(mover, sup_names, pad_mm,
                                                snap_cap_mm)
        if multi:
            # multi-level: never pick a plane (gate-1 A6 / test n) —
            # snapping to the high side buries the low half
            report["snap_skipped"] = "skipped_multi_level"
            below = []
        gaps = [mn.z - h for h in below]
        if gaps:
            gap = min(gaps)
            report["snap_gap_mm"] = round(gap * 1000, 3)
            if 0 < gap * 1000 <= snap_cap_mm:
                mover.matrix_world = Matrix.Translation(
                    (0, 0, -gap)) @ mover.matrix_world
                bpy.context.view_layer.update()
                report["snap_applied_mm"] = round(gap * 1000, 3)
            elif gap * 1000 > snap_cap_mm:
                report["snap_skipped"] = (
                    f"gap {gap * 1000:.2f} mm > cap {snap_cap_mm}")

    post = _pairs_audit([mover], others, pad_mm)
    report["post_audit"] = post
    pen_post = [p for p in post.get("pairs", [])
                if p.get("state") == "PENETRATING"]
    touching_non_support = [
        p for p in post.get("pairs", [])
        if p.get("state") == "TOUCHING"
        and intended not in (p["a"], p["b"])]
    report["incidental_contacts"] = [
        {"a": p["a"], "b": p["b"]} for p in touching_non_support]
    if pen_post:
        report.update(ok=False, verdict="PLACED_OVERLAP",
                      penetrating_pairs=pen_post)
    else:
        support_now, sz = _rest_support(mover, neighbors)
        report["rests_on"] = support_now
        report["rests_at_z"] = round(sz, 4) if sz is not None else None
        if support_now is None:
            report.update(ok=False, verdict="NO_SUPPORT",
                          verdict_reason="came to rest on nothing (void)")
        elif support_now != intended and intended is not None:
            # physics chose a different support than the pre-drop
            # estimate (e.g. the tray tipped onto the LOWER of two
            # books) — a clean landing on a real support is PLACED with
            # a note; NO_SUPPORT is for void rests only (round-C)
            report.update(ok=True, verdict="PLACED",
                          support_changed={"estimated": intended,
                                           "actual": support_now})
        else:
            report.update(ok=True, verdict="PLACED")
    return _finish(report, t0, output)


# --------------------------------------------------------------------------
# Op 3 — oracle (the jeep-door witness)
# --------------------------------------------------------------------------

def oracle(obj, *, target_z=None, target=None, frames=45, pad_mm=150.0,
           tol_mm=1.0, intended_support=None, allow_bake=False,
           allow_copy=False, output=None):
    """Place obj at its requested pose (current pose, target_z via
    move_to bottom-center, or a full xyz `target`), settle it as sole
    mover, then classify the outcome (Op 3):
    REACHED / BLOCKED (blocked_by named) / FELL_BELOW / SLIPPED.
    requested_z and settled_z are the object's world bbox BOTTOM."""
    t0 = time.time()
    report = {"op": "physics_oracle", "obj": obj.name, "tol_mm": tol_mm}
    all_mesh = [o for o in bpy.context.scene.objects
                if o.type == 'MESH' and o.name != obj.name]
    movers, env_objs, excluded = _prep([obj], environment=all_mesh,
                                       allow_bake=allow_bake,
                                       allow_copy=allow_copy)
    report["excluded"] = excluded
    if not movers:
        report.update(ok=False, verdict="REFUSED",
                      verdict_reason="object not eligible")
        return _finish(report, t0, output)
    mover = movers[0]
    others = [o for o in bpy.context.scene.objects
              if o.type == 'MESH' and o.name != mover.name]
    if not env_objs:
        report.update(ok=False, verdict="REFUSED_ENV",
                      verdict_reason=(
                          "no viable environment to collide against "
                          "(all other meshes excluded — see excluded); "
                          "a sim without a world free-falls"))
        return _finish(report, t0, output)
    neighbors = _neighbors([mover], others, pad_mm)

    # WITNESS contract: the scene must be restored to the PRE-ORACLE
    # pose (usability round A: the target move leaked keys + left the
    # object displaced, poisoning chained ops). Capture BEFORE moving.
    pre_move_mw = {o.name: o.matrix_world.copy()
                   for o in movers + env_objs}
    pre_move_frame = bpy.context.scene.frame_current
    if target is not None:
        # full xyz request (session-13b UA-UB A2): bottom-center lands
        # at the requested world xyz
        pl.move_to(mover, target, reference='bottom-center', override=None)
    elif target_z is not None:
        pl.move_to(mover, (mover.matrix_world.translation.x,
                           mover.matrix_world.translation.y, target_z),
                   reference='bottom-center', override=None)
    bpy.context.view_layer.update()
    requested_z = pl._aabb(mover)[0].z
    report["requested_z"] = round(requested_z, 4)

    # intended support = the surface under the REQUESTED pose (recomputed
    # AFTER the target move — round-B T5p: computing it at the spawn pose
    # named the ground for a crate demanded onto a shelf plate, pushing
    # the plate into blocked_by and misreading a margin-pop rest as
    # BLOCKED)
    if intended_support is None:
        neighbors = _neighbors([mover], others, pad_mm)
        intended, _ = _rest_support(mover, neighbors)
    else:
        intended = intended_support
    report["intended_support"] = intended

    pre = _pairs_audit([mover], others, pad_mm)
    pen_pre = _preflight_pens(pre.get("pairs", []))
    if pen_pre:
        # WITNESS contract includes the refused path: undo the target
        # move (round-B subject: the refused pose leaked into the scene,
        # leaving the driver teleported inside the door panel)
        for o in movers + env_objs:
            o.matrix_world = pre_move_mw[o.name]
        bpy.context.scene.frame_set(pre_move_frame)
        bpy.context.view_layer.update()
        pl.clear_bvh_cache()
        report["scene_state"] = "pre_oracle_restored"
        report.update(ok=False, verdict="REFUSED_PENETRATING",
                      penetrating_pairs=pen_pre)
        return _finish(report, t0, output)

    start_all = {mover.name: mover.matrix_world.copy()}
    for e in env_objs:
        start_all[e.name] = e.matrix_world.copy()
    start_mw, end_mw, stats = _sim([mover], env_objs, frames, report=report)
    report.update(stats)
    # WITNESS fix (session-13b/UA-UB): the witness lists must describe
    # the SETTLED pose, not the restored original pose — auditing after
    # the pre-move restore named whatever touched the mover at its
    # ORIGINAL location (subject B: blocked_by = ["Ground"] for a crate
    # 1.6 m away from the shelf). Order: commit the settled pose (rb
    # stripped) -> audit the witness -> restore the pre-oracle scene.
    _teardown([mover] + env_objs, start_all, end_mw,
              stats["entry_frame"], stats["world_created"], 'end')
    bpy.context.view_layer.update()
    pl.clear_bvh_cache()

    # measure the settled bottom EXACTLY from the committed pose (the
    # mover sits at the settled pose right now; the old end-matrix
    # estimate underestimated for rotated settles)
    settled_z = pl._aabb(mover)[0].z
    report["settled_z"] = round(settled_z, 4)
    disp = (end_mw[mover.name].translation -
            start_all[mover.name].translation)
    report["disp_xy_mm"] = round(
        math.hypot(disp.x, disp.y) * 1000, 2)
    report["disp_z_mm"] = round(disp.z * 1000, 2)
    report["rotation_delta_deg"] = round(_rotation_delta_deg(
        start_all[mover.name], end_mw[mover.name]), 2)
    report["rotation_tilt_deg"] = round(_tilt_deg(end_mw[mover.name]), 2)
    # settled support captured BEFORE the restore — the round-E subject
    # caught rests_on naming the SPAWN-pose support (Floor) because the
    # FELL_BELOW branch read the scene after pre_oracle_restored
    settled_rests_on, _sz = _rest_support(mover, others)
    report["settled_rests_on"] = settled_rests_on

    # witness lists (D6, re-scoped session-13b): ranked contacts AT THE
    # SETTLED POSE (full evidence, including the intended support);
    # blocked_by = obstruction candidates only — pairs actually at/below
    # contact distance (TOUCHING / PENETRATING / clearance <= 10 mm).
    # Round-B subject D: ranking every neighbor by clearance turned
    # blocked_by into a nearest-neighbour directory (objects 52 mm to
    # 1 m away listed as "obstructions" while the report showed all
    # CLEAR — the rest was a 2 mm margin pop, not a block).
    post = _pairs_audit([mover], others, pad_mm)
    ranked = []
    for p in post.get("pairs", []):
        other = p["b"] if p["a"] == mover.name else p["a"]
        cl = p.get("clearance_mm")
        pen = p.get("penetration_mm")
        if p["state"] == "PENETRATING":
            score = (0, pen if pen is not None else 1e6)
        elif p["state"] == "TOUCHING":
            score = (1, 0.0)
        else:
            score = (2, cl if cl is not None else 1e9)
        ranked.append((score, other, p["state"], cl, pen))
    ranked.sort(key=lambda r: (r[0][0], r[0][1]))
    report["contacts_lateral"] = [
        {"obj": r[1], "state": r[2],
         "clearance_mm": r[3], "penetration_mm": r[4]}
        for r in ranked]
    # obstruction candidates: at/below contact distance; measured-depth
    # penetrations rank before crossing (crossing depth is not
    # vert-measurable — round-B F-003)
    blocked = [r[1] for r in ranked
               if (r[2] in ("TOUCHING", "PENETRATING")
                   or (r[3] is not None and r[3] <= 10.0))
               and (intended is None or r[1] != intended)]

    # restore the pre-oracle scene NOW (witness contract: the scene the
    # user has is the scene they had — the fix-queue/verdict text below
    # refers to numbers already recorded)
    for o in movers + env_objs:
        o.matrix_world = pre_move_mw[o.name]
    bpy.context.scene.frame_set(pre_move_frame)
    bpy.context.view_layer.update()
    pl.clear_bvh_cache()
    report["scene_state"] = "pre_oracle_restored"

    if disp.length > 1000.0:
        # runaway depenetration (requested pose inside solid geometry
        # that slipped past the pre-flight): report the ejection, never
        # dress it up as a pose verdict (round D: 14.5m read "TOPPLED")
        report.update(ok=False, verdict="ESCAPED",
                      verdict_reason=(
                          "verify sim displaced the object > 1 m — the "
                          "requested pose is inside solid geometry; "
                          "see contacts_lateral for the suspected "
                          "obstruction"))
    elif report["rotation_tilt_deg"] > 10.0:
        report.update(ok=True, verdict="TOPPLED",
                      verdict_reason="orientation changed > 10deg")
    elif abs(settled_z - requested_z) * 1000 <= tol_mm and \
            report["disp_xy_mm"] <= tol_mm:
        report.update(ok=True, verdict="REACHED")
    elif settled_z > requested_z + tol_mm / 1000.0:
        # margin-pop guard (round-B subject D): a rest ~2 mm above the
        # request with NO contact-distance pair is the bullet hull
        # margin pop (gotcha #61), not a block — physics_place's snap
        # closes it. Real blocks have a witness pair at contact
        # distance (or a rest far above the request).
        # Threshold derives from the margin-sum law (probe_hull_pop):
        # hull-hull rest separation ~= SUM of the two bodies' margins;
        # all production bodies use _RB_MARGIN, so worst case is 2x
        # margin + measurement noise. Floor 2.5mm = round-B calibration.
        pop_mm = (settled_z - requested_z) * 1000.0
        pop_tol_mm = _pop_allow_mm()  # call-time read (tests retarget the law)
        if pop_mm <= pop_tol_mm and not blocked:
            report.update(ok=True, verdict="REACHED",
                          margin_pop_mm=round(pop_mm, 2),
                          verdict_reason=(
                              f"rests {pop_mm:.2f} mm above the request "
                              f"— bullet hull-margin pop (gotcha #61), "
                              f"no obstruction within contact distance; "
                              f"physics_place closes this to exact"))
        else:
            report.update(ok=True, verdict="BLOCKED",
                          blocked_by=blocked[:3],
                          verdict_reason=(
                              f"rests {settled_z - requested_z:.4f} m "
                              f"above the requested pose; something is "
                              f"in the way"))
    elif report["disp_z_mm"] < -25.0:
        # a fall is never a slip (round-C subject F: a 498 mm mid-air
        # free-fall read SLIPPED on 3 mm lateral jitter) — anything that
        # dropped > 25 mm below the request landed somewhere else
        # entirely; FELL_BELOW takes precedence over the SLIPPED branch
        report.update(ok=True, verdict="FELL_BELOW",
                      verdict_reason=(
                          f"fell {abs(report['disp_z_mm']):.0f} mm below "
                          "the requested pose (was floating or slid "
                          "off); support named in rests_on"))
        report["rests_on"] = settled_rests_on
    elif report["disp_xy_mm"] > tol_mm and intended and \
            _rest_support_name(mover, others, post) == intended:
        report.update(ok=True, verdict="SLIPPED")
    else:
        report.update(ok=True, verdict="FELL_BELOW",
                      verdict_reason=(
                          "ended lower than requested (was floating or "
                          "slid off); support named in rests_on"))
        report["rests_on"] = settled_rests_on
    return _finish(report, t0, output)


def _rest_support_name(obj, neighbors, post):
    for p in post.get("pairs", []):
        if p.get("state") in ("TOUCHING", "PENETRATING"):
            if obj.name == p["a"]:
                return p["b"]
            if obj.name == p["b"]:
                return p["a"]
    s, _z = _rest_support(obj, neighbors)
    return s


# --------------------------------------------------------------------------
# Op 4 — gate (scene-level rejection gate)
# --------------------------------------------------------------------------

def gate(*, tol_mm=1.0, frames=45, apply='none', fail_hard=False,
         pad_mm=100.0, audit_pad_mm=100.0, verify_movers=None, output=None):
    """Whole-scene REJECTION gate (Op 4): "nothing can overlap, we
    simply reject". Static audit (pad) -> settle-verify on the pen-free
    subset (apply='none', repair forced 'refuse') -> PASS/REJECTED with
    an executable fix queue. fail_hard=True exits non-zero for shell
    pipelines."""
    t0 = time.time()
    if apply != 'none':
        raise ValueError("gate is a pure verifier: apply must be 'none'")
    report = {"op": "physics_gate", "tol_mm": tol_mm}
    # Production law (escape-previz integration): the gate audits and
    # simulates what the CAMERA can see — hidden objects are rig
    # machinery (drivers/proxies), not previz content. They produce no
    # audit pairs, never become terrain, and are recorded for transparency.
    hidden = {o.name for o in bpy.context.scene.objects
              if o.type == 'MESH' and (o.hide_get() or o.hide_render)}
    if hidden:
        report["hidden_excluded"] = sorted(hidden)
    static = pl.audit_scene(clearance_pad_mm=audit_pad_mm,
                            exclude=hidden)
    report["static_audit"] = static
    pen_pairs = [p for p in static.get("pairs", [])
                 if p.get("state") == "PENETRATING"]
    # NESTED (fully contained) pairs REJECT too — the gate's mission is
    # "absolutely nothing can overlap"; a mug fully inside a desk is
    # overlapping even though no face-pair overlaps. Intentional nesting
    # (sockets, drawers) uses the verify_movers custom lane.
    nested_pairs = [p for p in static.get("pairs", [])
                    if p.get("state") == "NESTED"]
    custom_lane = verify_movers is not None
    static_pen_set = {(p["a"], p["b"]) for p in pen_pairs}
    if custom_lane:
        # REST-VERIFY GATE (production semantics, escape-previz
        # integration): the wanted movers are judged by the SETTLE SIM
        # (do they rest where they were authored?), NOT by the
        # whole-scene overlap audit — productions contain BY-DESIGN
        # overlaps (an occupant inside the vehicle, mist volumes,
        # parallax backdrop layers, debris fields crossing curbs). The
        # full static audit stays in report["static_audit"] for review;
        # rejection comes from sim instability only (a real defect — a
        # jeep floating over the road, a prop sinking — destabilizes the
        # sim and rejects through the same instability path).
        report["gate_semantics"] = "rest_verify_custom"
        pen_pairs, nested_pairs = [], []
    def _smaller(pair):
        a = bpy.data.objects.get(pair["a"])
        b = bpy.data.objects.get(pair["b"])
        if not a or not b:
            return pair["a"]
        va = abs((pl._aabb(a)[1] - pl._aabb(a)[0]).length) ** 3
        vb = abs((pl._aabb(b)[1] - pl._aabb(b)[0]).length) ** 3
        return pair["a"] if va <= vb else pair["b"]

    fixq = []
    for p in pen_pairs:
        target = _smaller(p)
        pen = p.get("penetration_mm")
        fixq.append({"op": "physics_settle", "objs": [target],
                     "repair_penetrations": "physics",
                     "note": f"depenetrate {target} from "
                             f"{p['b'] if target == p['a'] else p['a']} "
                             f"({pen if pen is not None else 'crossing'} "
                             f"mm)"})
    for p in nested_pairs:
        target = _smaller(p)
        other = p['b'] if target == p['a'] else p['a']
        fixq.append({"note": f"{target} is fully contained (NESTED in "
                             f"{other}) — separate the objects or lift "
                             f"the inner one out; use verify_movers to "
                             f"exempt intentional nesting"})

    pen_objs = {p["a"] for p in pen_pairs} | {p["b"] for p in pen_pairs}
    movers, env_objs, excluded = _prep(None)
    movers = [m for m in movers if m.name not in pen_objs]
    # AUTO-LANE (round A: with everything a mover, the floor fell and
    # PASS was vacuous). Ground plane = the top of the lowest objects;
    # anything RESTING at that level is terrain (PASSIVE), everything
    # above is verified as a mover — a floating desk/rug/panel is above
    # ground level and still gets verified. Pen-objects are already
    # REJECTED statically; they act as terrain for the rest of the
    # verify (round A2: floaters otherwise "drop past" them and the
    # note numbers lie 10x).
    bottoms = {o.name: pl._aabb(o)[0].z for o in movers + env_objs}
    min_bottom = min(bottoms.values(), default=0.0)
    ground_top = max(
        (pl._aabb(o)[1].z for o in movers + env_objs
         if abs(bottoms[o.name] - min_bottom) <= 0.005),
        default=min_bottom)
    grounded, airborne = [], []
    for m in movers:
        # terrain = the ground plane itself (bottom at scene min) AND
        # anything resting at ground-top level (round C: the floor's
        # own bottom is below its top — it must not verify as a mover)
        is_ground = bottoms[m.name] <= min_bottom + 0.005
        at_ground_top = abs(bottoms[m.name] - ground_top) <= 0.005
        (grounded if (is_ground or at_ground_top)
         else airborne).append(m)
    custom_lane = verify_movers is not None
    if custom_lane:
        # Round-E subject B: the custom lane used to verify ONLY the
        # wanted movers against env+grounded — non-wanted AIRBORNE
        # objects (the cabin pan the driver rests on) vanished from the
        # sim entirely, so the driver free-fell 400 mm and the gate
        # falsely REJECTED a TOUCHING-0.0mm rest. Correct semantics =
        # physics_settle's named-mover law ("movers auto-treat the rest
        # as terrain"): wanted movers ACTIVE, EVERYTHING else PASSIVE,
        # minus the _prep-excluded (animated env must stay out — TB4).
        want = {o.name for o in verify_movers}
        movers = [m for m in movers if m.name in want]
        kept = {m.name for m in movers}
        excluded_names = {e["obj"] for e in excluded}
        env_objs = [
            o for o in bpy.context.scene.objects
            if o.type == 'MESH' and o.name not in kept
            and o.name not in excluded_names]
    else:
        env_objs = env_objs + grounded + [
            bpy.data.objects[n] for n in pen_objs
            if bpy.data.objects.get(n) and
            bpy.data.objects[n] not in env_objs + grounded]
        movers = airborne
    report["excluded"] = excluded
    report["settle_verify_movers"] = [m.name for m in movers]
    report["settle_verify_terrain"] = [e.name for e in env_objs]
    report["settle_verify_lane"] = ("custom" if custom_lane
                                    else "auto")
    if custom_lane and not movers:
        report["settle_verify_skipped"] = True

    instability = []
    if movers:
        others = [o for o in bpy.context.scene.objects
                  if o.type == 'MESH' and o not in movers
                  and o.name not in hidden]  # hidden = not previz content
        bpy.context.view_layer.update()
        start_all = {o.name: o.matrix_world.copy() for o in movers + env_objs}
        start_mw, end_mw, stats = _sim(movers, env_objs, frames,
                                       report=report)
        report.update(stats)
        _teardown(movers + env_objs, start_all, end_mw,
                  stats["entry_frame"], stats["world_created"], 'none')
        post = _pairs_audit(movers, others, pad_mm)
        report["post_audit"] = post
        pen_post = [p for p in post.get("pairs", [])
                    if p.get("state") == "PENETRATING"]
        for p in pen_post:
            # "NEW" means the SIM created this overlap — pairs already
            # penetrating in the static audit are by-design (production
            # assemblies: occupants, wheel arches, seats) and must not
            # reject a rest-verify. Compared against the FULL static
            # audit (both lanes — the custom lane empties pen_pairs for
            # the verdict but not for this comparison).
            if (p["a"], p["b"]) not in static_pen_set:
                instability.append(p)
                fixq.append({"op": "physics_settle",
                             "objs": [p["a"]],
                             "note": f"sim-induced new penetration "
                                     f"{p['a']} x {p['b']}"})
        # DIRECTIONAL finding rule (round C, measured law): a body at
        # rest POPS UP ~2mm per contact level (bullet contact margin,
        # compounding in stacks) — an upward pop is REST, never a
        # defect. Floating/unsupported bodies move DOWN or sideways.
        for o in movers:
            m0, m1 = start_all[o.name], end_mw[o.name]
            d = m1.translation - m0.translation
            disp = d.length * 1000.0
            disp_xy = math.hypot(d.x, d.y) * 1000.0
            dz = d.z * 1000.0
            tilt = _tilt_deg(m1)
            if disp > 1000.0:  # left the ~scene
                instability.append({"obj": o.name,
                                    "displacement_mm": round(disp, 2),
                                    "verdict": "ESCAPED"})
                fixq.append({"note": f"{o.name} escaped during verify — "
                                     f"inspect manually"})
            elif tilt > 10.0:
                instability.append({"obj": o.name,
                                    "rotation_tilt_deg": round(tilt, 2),
                                    "verdict": "TOPPLED"})
                fixq.append({"op": "physics_settle", "objs": [o.name],
                             "note": f"toppled during verify "
                                     f"({tilt:.0f} deg tilt) — re-support"})
            elif dz > 0.0 and disp_xy > tol_mm and dz >= disp_xy:
                # Upward-DOMINANT ejection (round-H h1 deadlock): a part
                # wedged at EXACT lateral contact between neighbors is
                # margin-inflated ~2mm too wide — bullet ejects it
                # UP+SIDEWAYS. Floats and slide-offs never move UP; this
                # is the gotcha-#61 margin law, not a defect — the mesh
                # state (TOUCHING, no penetration) is the previz truth,
                # and the fix queue CANNOT fix a wedge (settle re-commits
                # the same contact -> infinite REJECT loop). Record
                # loudly, don't REJECT (unless it is a real launch).
                eject = {"obj": o.name,
                         "disp_z_mm": round(dz, 2),
                         "disp_xy_mm": round(disp_xy, 2),
                         "note": "upward-dominant ejection — over-tight "
                                 "exact-contact fit vs bullet margins "
                                 "(gotcha #61); loosen the fit by >= 2x "
                                 "margin or accept as-is"}
                if dz > _EJECT_CAP_MM:
                    eject["verdict"] = "LAUNCHED"
                    instability.append(eject)
                    fixq.append({"note": f"{o.name} launched upward "
                                         f"({dz:.0f} mm) during verify "
                                         f"— inspect the fit"})
                else:
                    report.setdefault("sim_ejections", []).append(eject)
                    print(f"[physics_gate] sim_ejection (non-rejecting): "
                          f"{o.name} dz={dz:.1f}mm xy={disp_xy:.1f}mm "
                          f"— margin-law wedge pop, see sim_ejections")
            elif dz < -tol_mm:
                # moved DOWN — float/unsupported, a genuine finding
                instability.append({"obj": o.name,
                                    "displacement_mm": round(disp, 2),
                                    "disp_z_mm": round(dz, 2)})
                fixq.append({"op": "physics_settle", "objs": [o.name],
                             "note": f"floating/unsupported "
                                     f"({disp:.1f} mm moved at verify)"})
            elif disp_xy > tol_mm + 2.0 * _RB_MARGIN * 1000.0:
                # slid sideways beyond the margin-squeeze allowance —
                # a genuine slide finding (level-or-down motion only:
                # upward-dominant motion was handled above)
                instability.append({"obj": o.name,
                                    "displacement_mm": round(disp, 2),
                                    "disp_xy_mm": round(disp_xy, 2)})
                fixq.append({"op": "physics_settle", "objs": [o.name],
                             "note": f"slid sideways "
                                     f"({disp_xy:.1f} mm at verify)"})
            # else: at rest (upward pop / lateral margin jitter) — not a finding

    rejected = bool(pen_pairs or nested_pairs or instability)
    report["verdict"] = "REJECTED" if rejected else "PASS"
    report["ok"] = not rejected
    report["nested_pairs"] = nested_pairs
    report["fail_hard"] = fail_hard
    report["fix_queue"] = fixq
    report["instability_pairs"] = instability
    report["exit_code"] = 2 if (rejected and fail_hard) else 0
    _finish(report, t0, output)
    if rejected and fail_hard:
        print("[physics_gate] REJECTED — fix queue:", len(fixq), "items")
        # fail_hard exits HERE, before the patch-level printer can run —
        # print the detail now or the consumer sees only the verdict line
        for _q in fixq[:12]:
            print("[physics_gate]   queue:", _q.get("op", "(manual)"),
                  _q.get("objs", ""), "-", _q.get("note", ""))
        if not output:
            print("[physics_gate]   (re-run with output= to persist the "
                  "full report JSON)")
        sys.exit(2)
    return report



