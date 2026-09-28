"""
ual_bake.py -- v4 step 3: the two-phase bake utility (PLAN_v4 REV3
item 1 + item 5, spec-verbatim).

One merged baked action per actor ("UAL.<Actor>.Baked"), replacing the
capsule limb-bake system for the UAL heroes:

  PHASE 1 (live-eval recording, REV3: slot + frame_set + double
  view_layer.update): for every output frame f in [1..1080] resolve the
  beat map -> (source action, source frame) or a BLEND of two evals;
  record per pose bone matrix_basis decomposed to location +
  rotation_quaternion (SCALE OMITTED, pinned 1.0 -- the baked action
  never carries scale channels).

  PHASE 2 (write): a FRESH action (never key into imported sources --
  the fresh-bake-only law; 4 imports duplicate all 46 actions and
  keying one would corrupt all). LINEAR keys, CONSTANT extrapolation,
  EVERY frame f1..1080 (full range regardless of chunk --start: the
  render daemon REBUILDS per chunk; a chunk-scoped bake freezes rigs
  in chunks 2+). Quaternion sign-canonicalized (dot<0 -> negate).

  GATE (bake fidelity): baked-vs-live bone delta < 1e-3 m on sampled
  frames per beat, armature-LOCAL space (the wrapper is separately
  keyed + gated; recording world would mix the two). Blend windows are
  exempt (slerp mixtures are not source poses). Includes the f512
  hand-contact assert (Punch_Cross final frame -- the grab reach).

Beat map (REV2 corrected + REV3 item 7; frame numbers are FROZEN to
the sfx/dialog/event tables):
  Driver:  sprint f1-133 (Sprint_Loop, phase 0.00)
           board  f133-145 (Sitting_Enter @2.6x, blend 4)
           drive  f145-1080 (Driving_Loop)
  Girl:    sprint f1-139 (phase 5.28)
           board  f139-151 (Sitting_Enter @2.6x, blend 4)
           idle   f151-174 (Sitting_Idle_Loop)
           talk   f174-500 (Sitting_Talking_Loop, blend 6)
           idle   f500-1080 (Sitting_Idle_Loop, blend 6)
  Gunner:  sprint f1-151 (phase 10.56)
           aim    f151-157 (Pistol_Aim_Neutral, blend 6 -- REV3 item 7)
           hold   f157-1080 + gap-aware Pistol_Shoot recoil pops at the
           FLASH STROBE frames (REV3 item 12: pops pinned to the strobe
           so audio + visual rhythms agree; recoil extent =
           min(gap_to_next_shot, 6): out 0->3 over half, recover 3->0
           over the rest -- continuous sawtooth at rapid cadences)
  HeroZed: chase  f1-497 (phase 2.4)
           lunge  f497-512 (Punch_Cross last 14f, blend 4)
           grab   f512-541 (Punch_Cross final frame frozen)
           thrown f541-550 (Hit_Chest 9f)
           rest   f550-1080 (Hit_Chest final frozen)

Pre-flight scale scan: source actions carry 159 scale fcurves each at
1.0 +/- 1.7e-06 (glTF float32 quantization noise, measured step-1).
Threshold 1e-4 (any REAL scale animation deviates 1e-2+; the REV3
1e-6 wording trips on float32 noise -- documented deviation).
"""
import math

import bpy
from mathutils import Quaternion, Vector
from blender_kit import fcurves_new, iter_fcurves

FPS = 24
TOTAL = 1080
BLEND_DEFAULT = 6

# bone set to record (all 53 pose bones; DEF-* Rigify names)
def _all_bones(arm):
    return [b.name for b in arm.pose.bones]


# ---------------------------------------------------------------------------
# beat map
# ---------------------------------------------------------------------------
class Beat:
    __slots__ = ("f0", "f1", "action", "mode", "param", "phase",
                 "blend", "src_lo", "src_hi")

    def __init__(self, f0, f1, action, mode, param=0.0, phase=0.0,
                 blend=BLEND_DEFAULT, src_lo=0.0, src_hi=None):
        self.f0, self.f1 = f0, f1
        self.action = action
        self.mode = mode            # loop | rate | hold
        self.param = param          # rate: src span / out span
        self.phase = phase          # loop: frame offset
        self.blend = blend
        self.src_lo, self.src_hi = src_lo, src_hi

    def src_at(self, f):
        """Source frame for output frame f (no clamping -- blends need
        extrapolated values; the action fcurves extrapolate CONSTANT)."""
        if self.mode == "loop":
            return (self.phase + (f - self.f0)) % self.param \
                if self.param else (self.phase + (f - self.f0)) % 16.0
        if self.mode == "rate":
            return self.src_lo + (f - self.f0) * self.param
        return self.param           # hold


def _driver_beats():
    return [
        Beat(1, 133, "Sprint_Loop", "loop", param=16.0, phase=0.0),
        Beat(133, 145, "Sitting_Enter", "rate", param=31.0 / 12.0,
             blend=6),
        Beat(145, TOTAL, "Driving_Loop", "loop", param=40.0, phase=0.0),
    ]


def _girl_beats():
    return [
        Beat(1, 139, "Sprint_Loop", "loop", param=16.0, phase=5.28),
        Beat(139, 151, "Sitting_Enter", "rate", param=31.0 / 12.0,
             blend=6),
        Beat(151, 174, "Sitting_Idle_Loop", "loop", param=40.0),
        Beat(174, 500, "Sitting_Talking_Loop", "loop", param=70.0,
             blend=6),
        Beat(500, TOTAL, "Sitting_Idle_Loop", "loop", param=40.0,
             blend=6),
    ]


def _gunner_beats(aim="Pistol_Aim_Neutral"):
    """v5 (session-18): the aim action is parametric -- the v5 scene
    passes Rifle_Aim (authored two-handed hold); v4 callers get the
    Pistol default verbatim (fork law: v4's release path unchanged)."""
    return [
        Beat(1, 151, "Sprint_Loop", "loop", param=16.0, phase=10.56),
        # REV3 item 7: Sprint to f151 + 6f blend -> Aim at f157
        Beat(151, 157, aim, "hold", param=0.0,
             blend=6),
        # review v4-impl-a P1-4: hold-continuation beats take NO blend
        # (same action + same extrapolated src = identity mix that only
        # ate the gate exemptions)
        Beat(157, TOTAL, aim, "hold", param=0.0,
             blend=0),
    ]


def _herozed_beats():
    return [
        Beat(1, 498, "Sprint_Loop", "loop", param=16.0, phase=2.4),
        # review v4-impl-a P2-5: lunge starts f498 (the wrapper's own
        # x-keys start at EL.frame_at(20.7) = f498); grab at f512 is
        # EXACT (frame_at(21.3)); rate 14/14 native
        Beat(498, 512, "Punch_Cross", "rate", param=1.0,
             blend=4, src_lo=10.0),
        Beat(512, 541, "Punch_Cross", "hold", param=24.0, blend=0),
        Beat(541, 550, "Hit_Chest", "rate", param=8.0 / 9.0, blend=6),
        Beat(550, TOTAL, "Hit_Chest", "hold", param=8.0, blend=0),
    ]


def _pop_footprints(bursts):
    """Gunner burst pops pinned to the FLASH STROBE frames: shot at
    f0 + k*every; footprint [s-2, s+4) (2f blend in, 2f play of Shoot
    src 0-3, 2f blend out). Later shots win overlaps (sustained recoil
    during rapid strobes)."""
    shots = []
    for f0, f1, every in bursts:
        f = f0
        while f <= f1:
            shots.append(f)
            f += every
    return shots


# ---------------------------------------------------------------------------
# pre-flight
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


def _mix(table_a, table_b, t):
    """Per-bone basis mix: location lerp + quaternion slerp (REV3 item
    5: 'per-bone slerp(tableA extrapolated, tableB(f), t/6)')."""
    out = {}
    for bone, (la, qa) in table_a.items():
        lb, qb = table_b[bone]
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
    EVERY frame f1..1080. NO scale channels ever."""
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
                   slot_state, pool, blend_frames, resolver):
    """Baked-vs-live bone delta at sampled frames. Both sides read
    ARMATURE-LOCAL translations (b.matrix.translation -- pose bone
    matrix in armature object space): the wrapper transform cancels, so
    the delta measures POSE fidelity exactly (the wrapper is separately
    keyed + gated). Blend windows are exempt (slerp mixtures are not
    source poses). Includes the f512 hand-contact assert (HeroZed)."""
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
    # 3) f512 hand-contact assert (HeroZed only): Punch_Cross final
    #    frame -- arms extended for the grab (armature-local distance
    #    hand->hips; wrapper/scale independent)
    if name == "HeroZed":
        scene.frame_set(512)
        bpy.context.view_layer.update()
        bpy.context.view_layer.update()
        hips = arm.pose.bones.get("DEF-hips")
        reach = 0.0
        for hn in ("DEF-hand.L", "DEF-hand.R"):
            hb = arm.pose.bones.get(hn)
            if hb is None:
                continue
            d = (hb.matrix.translation
                 - hips.matrix.translation).length
            reach = max(reach, d)
        if reach < 0.35:
            findings.append(
                f"fidelity: HeroZed f512 hand reach {reach:.3f} m < 0.35 "
                f"(grab pose not extended -- Punch_Cross mapping wrong?)")
        else:
            print(f"[ual_bake] HeroZed f512 hand reach {reach:.3f} m "
                  f"(grab extended, PASS)")
    print(f"[ual_bake] {name}: fidelity worst {worst:.2e} m over "
          f"{len(live)} samples")
    return findings


# ---------------------------------------------------------------------------
# resolver: output frame -> list of (action, src_f, weight)
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
                out = [(prev.action, prev.src_at(f), 1.0 - t),
                       (beat.action, beat.src_at(f), t)]
        return out
    return resolver


def _gunner_resolver(beats, shots, shoot="Pistol_Shoot",
                     aim="Pistol_Aim_Neutral"):
    """Gap-aware burst pops (review v4-impl-a P1-2, redesigned):
    each shot's recoil extent = min(gap_to_next_shot, 6) frames:
      [s, s+dur/2):   Pistol_Shoot src 0 -> 3   (recoil OUT after the
                      flash -- causality: the shot fires AT s)
      [s+dur/2, s+dur): src 3 -> 0              (recover, landing at 0
                      exactly when the NEXT shot fires -- continuous
                      sawtooth at rapid cadences, never a blink to the
                      AIM pose between shots)
    Blend-in [s-2, s) from Aim only when the previous pop has fully
    ended (gap >= 8); the FIRST shot of an isolated burst eases in."""
    base = _make_resolver(beats, "Gunner")
    shots_sorted = sorted(shots)

    def extent(i):
        s = shots_sorted[i]
        nxt = shots_sorted[i + 1] if i + 1 < len(shots_sorted) else None
        gap = (nxt - s) if nxt is not None else 6
        return min(gap, 6)

    def resolver(f):
        owner = None
        for i, s in enumerate(shots_sorted):
            d = extent(i)
            if s <= f < s + d:
                owner = i            # later shots win overlaps
        if owner is not None and f >= 157:
            s = shots_sorted[owner]
            dur = extent(owner)
            half = dur / 2.0
            k = f - s
            if k < half:
                src = 3.0 * (k / half if half > 0 else 0.0)
            else:
                src = 3.0 * (1.0 - (k - half) / half if half > 0 else 0.0)
            return [(shoot, max(0.0, min(3.0, src)), 1.0)]
        # blend-in zone [s-2, s) only when the previous pop ended
        for i, s in enumerate(shots_sorted):
            if s - 2 <= f < s and f >= 157:
                prev_end = shots_sorted[i - 1] + extent(i - 1) \
                    if i > 0 else 0
                if f >= prev_end:
                    t = min(1.0, max(0.0, (f - (s - 2)) / 1.0))
                    return [(aim, 0.0, 1.0 - t),
                            (shoot, 0.0, t)]
        return base(f)

    return resolver



def bake_actor(ctx, name, beats, resolver, samples):
    scene = ctx["scene"]
    d = ctx["humans"][name]
    arm, pool = d["armature"], d["actions"]
    bones = _all_bones(arm)

    slot_state = {"name": None}
    rows = {}
    blend_frames = set()
    for f in range(1, TOTAL + 1):
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
            rows[f] = _mix(ta, tb, w2)
    _canonicalize_quats(rows)
    act = _write_baked_action(name, arm, rows, bones)
    print(f"[ual_bake] {name}: {act.name} written "
          f"({len(bones)} bones x 7 ch x {len(rows)} frames, "
          f"{len(blend_frames)} blend frames)")
    return _fidelity_gate(name, arm, scene, beats, samples, rows,
                          slot_state, pool, blend_frames, resolver)


def bake_all(ctx, bursts):
    """Bake all 4 actors + run gates. Returns findings (empty = clean;
    NON-empty = fail-closed abort upstream)."""
    findings = _preflight({n: ctx["humans"][n]["actions"]
                           for n in ("Driver", "Girl", "Gunner",
                                     "HeroZed")})
    if findings:
        return findings
    shots = _pop_footprints(bursts)
    # v5 (session-18): UAL-mode action overrides via ctx (Rifle_Aim /
    # Rifle_Shoot authored by assets_rifle_v5); v4 callers unset ->
    # Pistol defaults verbatim.
    aim_act = ctx.get("gunner_aim_action", "Pistol_Aim_Neutral")
    shoot_act = ctx.get("gunner_shoot_action", "Pistol_Shoot")

    specs = (
        ("Driver", _driver_beats(), _make_resolver(_driver_beats(),
                                                   "Driver")),
        ("Girl", _girl_beats(), _make_resolver(_girl_beats(), "Girl")),
        ("Gunner", _gunner_beats(aim_act),
         _gunner_resolver(_gunner_beats(aim_act), shots,
                          shoot=shoot_act, aim=aim_act)),
        ("HeroZed", _herozed_beats(), _make_resolver(_herozed_beats(),
                                                     "HeroZed")),
    )
    # review v4-impl-a P1-4: added interior samples for the previously
    # zero-sample beats (Sitting_Enter mid, gunner aim land, lunge mid,
    # grab hold, Hit_Chest mid)
    samples = (1, 60, 120, 133, 140, 145, 160, 174, 190, 360, 500,
               505, 512, 520, 546, 600, 760, 830, 1080)
    for name, beats, resolver in specs:
        findings.extend(bake_actor(ctx, name, beats, resolver, samples))
        # SESSION-23 MEMORY LAW: the bake peaks across the 4-actor loop
        # (4x imported action libraries + per-actor pool copies alive at
        # once OOM-killed the export mid-HeroZed). Free each actor's
        # pool remnants as soon as its bake is verified.
        try:
            import bpy as _bpy
            _bpy.data.orphans_purge(do_local_ids=True, do_recursive=True)
        except Exception:
            pass
        import gc
        gc.collect()
    if not findings:
        print("[ual_bake] ALL ACTORS BAKED + FIDELITY CLEAN")
    return findings
