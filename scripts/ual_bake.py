# VENDORED 2026-10-16 from mainline blender-agent-kit @6943ab5 (vision-kit s21 vendor round; zero code drift; vision deltas must land as sanctioned deltas per docs/VENDOR_LEDGER.md)
"""
ual_bake.py -- the two-phase hero-action bake ENGINE (kit-owned since
s34; the escape project's choreography DATA lives in previz's
scripts/ual_beats.py -- the crowd_v6.contract pattern's second
instance; see the kit's docs/DESIGN_s34_ual_split.md).

One merged baked action per actor ("UAL.<Actor>.Baked"):

  PHASE 1 (live-eval recording, REV3: slot + frame_set + double
  view_layer.update): for every output frame f in [1..total] resolve
  the beat map -> (source action, source frame) or a BLEND of two
  evals; record per pose bone matrix_basis decomposed to location +
  rotation_quaternion (SCALE OMITTED, pinned 1.0 -- the baked action
  never carries scale channels).

  PHASE 2 (write): a FRESH action (never key into imported sources --
  the fresh-bake-only law; 4 imports duplicate all 46 actions and
  keying one would corrupt all). LINEAR keys, CONSTANT extrapolation,
  EVERY frame 1..total (full range regardless of chunk --start: the
  render daemon REBUILDS per chunk; a chunk-scoped bake freezes rigs
  in chunks 2+). Quaternion sign-canonicalized (dot<0 -> negate).

  GATE (bake fidelity): baked-vs-live bone delta < 1e-3 m on the
  caller-supplied sample frames, armature-LOCAL space (the wrapper is
  separately keyed + gated; recording world would mix the two). Blend
  windows are exempt (slerp mixtures are not source poses). The
  caller may pass post_check(name, arm, scene) for per-actor
  choreography asserts (previz's ual_beats supplies the f512
  hand-contact check -- the s34 split moved scene specifics OUT of
  this engine).

The engine is scene-agnostic: the bake range (total), the beat
tables, the sample frames, the pop geometry, and every action name
arrive as parameters from the data module.
"""
import math

import bpy
from mathutils import Quaternion, Vector
from blender_kit import fcurves_new, iter_fcurves

BLEND_DEFAULT = 6

# bone set to record (all 53 pose bones; DEF-* Rigify names)
def _all_bones(arm):
    return [b.name for b in arm.pose.bones]


# ---------------------------------------------------------------------------
# beat map

class Beat:
    __slots__ = ("f0", "f1", "action", "mode", "param", "phase",
                 "blend", "src_lo", "src_hi", "ease")

    def __init__(self, f0, f1, action, mode, param=0.0, phase=0.0,
                 blend=BLEND_DEFAULT, src_lo=0.0, src_hi=None,
                 ease=False):
        self.f0, self.f1 = f0, f1
        self.action = action
        self.mode = mode            # loop | rate | hold
        self.param = param          # rate: src span / out span
        self.phase = phase          # loop: frame offset
        self.blend = blend
        self.src_lo, self.src_hi = src_lo, src_hi
        self.ease = ease            # smoothstep the blend t (C1 at both
        #                           # ends -- a linear t has peak
        #                           # velocity MID-blend: reads as a snap

    def src_at(self, f):
        """Source frame for output frame f (no clamping -- blends need
        extrapolated values; the action fcurves extrapolate CONSTANT)."""
        if self.mode == "loop":
            return (self.phase + (f - self.f0)) % self.param \
                if self.param else (self.phase + (f - self.f0)) % 16.0
        if self.mode == "rate":
            return self.src_lo + (f - self.f0) * self.param
        return self.param           # hold


# ---------------------------------------------------------------------------
SCALE_TOL = 1e-4     # measured float32 noise floor 1.67e-06 (step-1);
                     # REAL scale animation deviates 1e-2+


def _preflight(pools):
    """Every source action used must carry unit scale channels only."""
    findings = []
    seen = set()
    for pool in pools.values():
        for nm, a in pool.items():
            if nm in seen or a is None:
                continue
            seen.add(nm)
            for fc in iter_fcurves(a):
                if not fc.data_path.endswith(".scale"):
                    continue
                for kp in fc.keyframe_points:
                    if abs(kp.co[1] - 1.0) > SCALE_TOL:
                        findings.append(
                            f"pre-flight: {nm} has non-unit scale key "
                            f"{kp.co[1]:.4f} at f{kp.co[0]:.0f} "
                            f"(rev3 item 1: scale must be pinned 1.0)")
                        break
                if findings and findings[-1].startswith(
                        f"pre-flight: {nm}"):
                    break
    return findings


# ---------------------------------------------------------------------------
# recording
# ---------------------------------------------------------------------------
def _assign_action(arm, act):
    """Blender 4.4+ action-slot law: `ad.action = X` alone does NOT
    reliably rebind (a legacy-slot action assigned first leaves the
    binding STUCK on it -- later source reassignments are silently
    ignored and the pose keeps evaluating the old action; live-probed
    step-3). Every assignment must pin the slot too."""
    ad = arm.animation_data
    ad.action = act
    if act is not None and act.slots:
        ad.action_slot = act.slots[0]


def _record_table(arm, pool, action_name, src_f, scene, slot_state):
    """Live-eval one pose: slot assignment (only on change) + frame_set
    + double view_layer.update; return {bone: (loc, quat)} from
    matrix_basis decompose (scale dropped)."""
    act = pool.get(action_name)
    if act is None:
        raise KeyError(f"action {action_name} not in pool")
    if slot_state.get("name") != action_name:
        _assign_action(arm, act)
        slot_state["name"] = action_name
    # review v4-impl-a P1-3: subframe evaluation -- int rounding made
    # consecutive output frames share one src frame (dead frames) on
    # sub-1x rate beats (lunge 14/15, Hit_Chest 8/9)
    sf_i = math.floor(src_f)
    scene.frame_set(sf_i, subframe=src_f - sf_i)
    bpy.context.view_layer.update()
    bpy.context.view_layer.update()
    out = {}
    for b in arm.pose.bones:
        loc, rot, _scl = b.matrix_basis.decompose()
        out[b.name] = (loc.copy(), rot.copy())
    return out


def _mix(table_a, table_b, t, arc_flip=None):
    """Per-bone basis mix: location lerp + quaternion slerp (REV3 item
    5: 'per-bone slerp(tableA extrapolated, tableB(f), t/6)').

    s31 ARC-SIGN LAW (the take-7 gate-20 fires at f144-150): when the
    MOVING table_a pose crosses the ANTIPODE of table_b's pose on a
    bone (the gunner's aim stance sits ~180 deg from the sprint on
    thigh.R/upper_arm.R/the rifle), the per-frame SHORT-ARC choice
    jumps sides at the crossing -- a single-frame ~180-deg flip (two
    per-frame continuity heuristics were tried and both failed: at
    the crossing NEITHER arc is near the previous output; the flip is
    a property of the whole blend, not of a frame pair). The fix:
    the arc sign is chosen ONCE per bone at the BLEND START
    (dot(table_a, table_b) at the first blend frame) and HELD for
    the whole window: the path may sweep the long way (>180 deg)
    but it is CONTINUOUS through the crossing -- a big readable turn,
    not a flip. Endpoints are sign-invariant (slerp(.., 1) = +-qb =
    the same rotation), so the blend still lands EXACTLY on the aim
    pose at t=1."""
    out = {}
    for bone, (la, qa) in table_a.items():
        lb, qb = table_b[bone]
        if arc_flip is not None and arc_flip.get(bone):
            # mathutils LAW: negate() mutates IN PLACE and returns
            # None -- `qb = qb.copy().negate()` assigns None (the
            # slerp then raises into the except fallback and the mix
            # silently degrades to the unflipped arc; TWO s31 export
            # cycles shipped bit-identical output through this hole)
            qb = qb.copy()
            qb.negate()
        try:
            q = qa.slerp(qb, t)
        except Exception:                               # noqa: BLE001
            q = qa if t < 0.5 else qb
        out[bone] = (la.lerp(lb, t), q)
    return out


def _canonicalize_quats(rows):
    """Quaternion sign canonicalization across frames (dot<0 -> negate)
    -- prevents interpolation flips between adjacent keys."""
    prev = {}
    for f in sorted(rows):
        for bone, (loc, quat) in rows[f].items():
            pq = prev.get(bone)
            if pq is not None and pq.dot(quat) < 0.0:
                quat.negate()
            prev[bone] = quat
            rows[f][bone] = (loc, quat)


# ---------------------------------------------------------------------------
# writing
# ---------------------------------------------------------------------------
def _write_baked_action(name, arm, rows, bones):
    """Fresh action 'UAL.<Name>.Baked' with LINEAR keys + CONSTANT
    extrapolation on location(3) + rotation_quaternion(4) per bone,
    EVERY frame f1..total (the caller's range). NO scale channels
    ever."""
    act_name = f"UAL.{name}.Baked"
    old = bpy.data.actions.get(act_name)
    if old is not None:
        bpy.data.actions.remove(old)
    act = bpy.data.actions.new(act_name)
    act.use_fake_user = True
    frames = sorted(rows)
    n = len(frames)
    for bone in bones:
        for arr, path in ((3, "location"), (4, "rotation_quaternion")):
            for ch in range(arr):
                fc = fcurves_new(
                    act, f'pose.bones["{bone}"].{path}', index=ch,
                    group=bone)
                fc.extrapolation = 'CONSTANT'
                fc.keyframe_points.add(n)   # NB: .add() returns None
                kps = fc.keyframe_points    # (in-place collection add)
                for i, f in enumerate(frames):
                    loc, quat = rows[f][bone]
                    v = loc[ch] if path == "location" else quat[ch]
                    kp = kps[i]
                    kp.co = (float(f), float(v))
                    kp.interpolation = 'LINEAR'
                    kp.handle_left_type = 'VECTOR'
                    kp.handle_right_type = 'VECTOR'
                fc.update()
    _assign_action(arm, act)
    return act


# ---------------------------------------------------------------------------
# fidelity gate
# ---------------------------------------------------------------------------
_SAMPLE_BONES = ("DEF-hips", "DEF-head", "DEF-foot.L", "DEF-hand.L",
                 "DEF-hand.R", "DEF-spine")


def _fidelity_gate(name, arm, scene, beats, samples, rows,
                   slot_state, pool, blend_frames, resolver,
                   post_check=None):
    """Baked-vs-live bone delta at sampled frames. Both sides read
    ARMATURE-LOCAL translations (b.matrix.translation -- pose bone
    matrix in armature object space): the wrapper transform cancels, so
    the delta measures POSE fidelity exactly (the wrapper is separately
    keyed + gated). Blend windows are exempt (slerp mixtures are not
    source poses). The caller's post_check hook (s34) carries any
    per-actor choreography asserts."""
    findings = []
    # NB: resolver must be THE resolver the bake used (the Gunner's
    # pop resolver -- a plain beat resolver would mis-eval burst frames
    # and false-fail ~0.05 m hand deltas; live-probed step 3)
    # 1) live reference: re-eval through the beat resolver; the pose is
    #    read IMMEDIATELY after record_table (scene still at the mapped
    #    src frame, source action in the slot). slot_state must be
    #    reset -- the slot now holds the BAKED action after writing.
    slot_state["name"] = None
    live = {}
    for f in samples:
        if f in blend_frames:
            continue
        evals = resolver(f)
        if not evals:
            continue
        (an, sf, _w) = evals[0]
        _record_table(arm, pool, an, sf, scene, slot_state)
        live[f] = {}
        for bn in _SAMPLE_BONES:
            b = arm.pose.bones.get(bn)
            if b is not None:
                live[f][bn] = b.matrix.translation.copy()
    # 2) restore the baked action to the slot (the live pass left a
    #    SOURCE action assigned -- comparing with it still in the slot
    #    would be a VACUOUS pass, the exact v3.3 chunk-gate failure
    #    class) + assert the slot before comparing
    act_baked = bpy.data.actions.get(f"UAL.{name}.Baked")
    if act_baked is None:
        findings.append(f"fidelity: {name}: UAL.{name}.Baked missing")
        return findings
    _assign_action(arm, act_baked)
    worst = 0.0
    _dbg = __import__("os").environ.get("UAL_BAKE_DEBUG")
    for f, ref in live.items():
        scene.frame_set(f)
        bpy.context.view_layer.update()
        bpy.context.view_layer.update()
        if arm.animation_data.action is not act_baked:
            findings.append(f"fidelity: {name}: slot drifted at f{f} "
                            f"(vacuous-pass guard)")
            break
        for bn, ref_p in ref.items():
            b = arm.pose.bones.get(bn)
            got = b.matrix.translation
            d = (got - ref_p).length
            worst = max(worst, d)
            if _dbg and d > 1e-3:
                print(f"    [fidelity-dbg] {name} {bn} f{f}: live "
                      f"{tuple(round(c,3) for c in ref_p)} baked "
                      f"{tuple(round(c,3) for c in got)} d={d:.4f}")
            if d > 1e-3:
                findings.append(
                    f"fidelity: {name} {bn} baked-vs-live {d:.4f} m "
                    f"at f{f} (> 1e-3)")
    # s34 split (design r1 I1): the per-actor choreography assert that
    # lived here (the HeroZed f512 hand-contact check) moved to the
    # DATA module; the engine calls the caller's post_check hook AFTER
    # the compare loop and BEFORE the worst-delta print (stdout order
    # preserved -- review r2 N1).
    if post_check is not None:
        findings.extend(post_check(name, arm, scene))
    print(f"[ual_bake] {name}: fidelity worst {worst:.2e} m over "
          f"{len(live)} samples")
    return findings


# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
def _make_resolver(beats, name):
    """Beats are HALF-OPEN [f0, f1): contiguous, no overlap (the
    boundary frame belongs to the NEXT beat -- the v1 spec used closed
    ranges which made boundary frames resolve to the PREVIOUS beat and
    silently killed every blend window)."""
    def resolver(f):
        beat = next((b for b in beats if b.f0 <= f < b.f1), None)
        if beat is None:
            # last beat owns its inclusive end frame
            if beats and f == beats[-1].f1:
                beat = beats[-1]
            else:
                return []
        out = [(beat.action, beat.src_at(f), 1.0)]
        if beat.blend and f < beat.f0 + beat.blend:
            prev = next((b for b in beats if b.f1 == beat.f0), None)
            if prev is not None:
                # review v4-impl-a P0-1: t must reach 1.0 at the LAST
                # blend frame -- (f-f0)/blend leaves a residue the next
                # frame snaps away (live-measured 0.265 m/frame hand
                # spike at f501, on camera in S8)
                t = (f - beat.f0) / max(1.0, beat.blend - 1.0)
                if getattr(beat, "ease", False):
                    # s31: smoothstep -- zero blend-rate at BOTH ends
                    # (the s30 take-6 sprint->aim 6f linear blend read
                    # as a violent limb sweep: shoulder-vs-thigh girdle
                    # twist peaked 71 deg, thigh.L flipped 176.8 deg in
                    # ONE frame at f153 -- the user's S3 f152 'twisted
                    # into body' flag)
                    t = t * t * (3.0 - 2.0 * t)
                # s31 FROZEN-SOURCE LAW: the outgoing beat's src is
                # held at the blend START (prev.src_at(f0), not
                # prev.src_at(f)). With a live source, a blend longer
                # than the source's cycle (the gunner's 20-frame
                # sprint->aim blend vs the 16-frame stride) sweeps the
                # moving pose through the target's ANTIPODE -- the
                # per-frame short-arc choice jumps sides at the
                # crossing (take-7: 177.6-deg single-frame flips at
                # f146/f150 through THREE failed per-frame arc
                # heuristics -- the crossing is a property of the
                # whole blend). Two FIXED poses cannot cross: the
                # slerp path is a single smooth arc, endpoints exact.
                # Visual: the stride holds its last pose while the
                # blend morphs to the incoming action -- during the
                # gunner's boarding leap (f145-157) the hold reads as
                # the tuck of the jump.
                out = [(prev.action, prev.src_at(beat.f0), 1.0 - t),
                       (beat.action, beat.src_at(f), t)]
        return out
    return resolver

def pop_resolver(base, shots, hold_from, shoot, aim,
                  src_extent=3.0, max_extent=6, blend_in=2):
    """Gap-aware burst pops (review v4-impl-a P1-2, redesigned;
    s34-generalized from _gunner_resolver -- every scene constant is
    now a parameter): each shot's recoil extent =
    min(gap_to_next_shot, max_extent) frames:
      [s, s+dur/2):   shoot src 0 -> src_extent   (recoil OUT after
                      the flash -- causality: the shot fires AT s)
      [s+dur/2, s+dur): src src_extent -> 0       (recover, landing
                      at 0 exactly when the NEXT shot fires --
                      continuous sawtooth at rapid cadences, never a
                      blink to the AIM pose between shots)
    Blend-in [s-blend_in, s) from Aim only when the previous pop has
    fully ended (f >= the previous shot's end frame); the FIRST shot
    of an isolated burst eases in. `hold_from` gates the pop zone (the
    actor's aim-hold start frame -- v5's gunner: 157). The LAW body
    (sawtooth shape, later-shot-wins, settle-gated blend-in) is engine;
    the numbers are the data's."""
    shots_sorted = sorted(shots)

    def extent(i):
        s = shots_sorted[i]
        nxt = shots_sorted[i + 1] if i + 1 < len(shots_sorted) else None
        gap = (nxt - s) if nxt is not None else max_extent
        return min(gap, max_extent)

    def resolver(f):
        owner = None
        for i, s in enumerate(shots_sorted):
            d = extent(i)
            if s <= f < s + d:
                owner = i            # later shots win overlaps
        if owner is not None and f >= hold_from:
            s = shots_sorted[owner]
            dur = extent(owner)
            half = dur / 2.0
            k = f - s
            if k < half:
                src = src_extent * (k / half if half > 0 else 0.0)
            else:
                src = src_extent * (1.0 - (k - half) / half
                                    if half > 0 else 0.0)
            return [(shoot, max(0.0, min(src_extent, src)), 1.0)]
        # blend-in zone [s-blend_in, s) only when the previous pop ended
        for i, s in enumerate(shots_sorted):
            if s - blend_in <= f < s and f >= hold_from:
                prev_end = shots_sorted[i - 1] + extent(i - 1) \
                    if i > 0 else 0
                if f >= prev_end:
                    t = min(1.0, max(0.0, (f - (s - blend_in))
                                     / max(1.0, blend_in - 1.0)))
                    return [(aim, 0.0, 1.0 - t),
                            (shoot, 0.0, t)]
        return base(f)

    return resolver

def bake_actor(ctx, name, beats, resolver, samples, total,
                post_check=None):
    scene = ctx["scene"]
    d = ctx["humans"][name]
    arm, pool = d["armature"], d["actions"]
    bones = _all_bones(arm)

    slot_state = {"name": None}
    rows = {}
    blend_frames = set()
    arc_flip = None            # the s31 per-bone arc-sign map (first
    #                          # blend frame freezes it; None until then
    #                          # and reset per ACTOR bake)
    for f in range(1, total + 1):
        evals = resolver(f)
        if not evals:
            continue
        if len(evals) == 1:
            an, sf, _w = evals[0]
            rows[f] = _record_table(arm, pool, an, sf, scene, slot_state)
        else:
            blend_frames.add(f)
            (an1, sf1, w1), (an2, sf2, w2) = evals
            ta = _record_table(arm, pool, an1, sf1, scene, slot_state)
            tb = _record_table(arm, pool, an2, sf2, scene, slot_state)
            # the s31 arc-sign law: on the FIRST blend frame, freeze
            # the per-bone arc choice (negate the target where the
            # blend starts on the far side) and hold it for the whole
            # window -- see _mix
            if arc_flip is None:
                arc_flip = {bone: (ta[bone][1].dot(tb[bone][1]) < 0.0)
                            for bone in ta}
            rows[f] = _mix(ta, tb, w2, arc_flip=arc_flip)
    _canonicalize_quats(rows)
    act = _write_baked_action(name, arm, rows, bones)
    print(f"[ual_bake] {name}: {act.name} written "
          f"({len(bones)} bones x 7 ch x {len(rows)} frames, "
          f"{len(blend_frames)} blend frames)")
    return _fidelity_gate(name, arm, scene, beats, samples, rows,
                          slot_state, pool, blend_frames, resolver,
                          post_check=post_check)

