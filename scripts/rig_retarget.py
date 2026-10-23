"""rig_retarget.py — the any-rig retarget recipe, first-class (s21-D3).

Constraint-less retargeting across the three humanoid families
(mixamo65 / rigify53 / quaternius42) by armature-space delta
composition. Design: docs/DESIGN_s21_hero_lane.md REV-2 — the audit's
corrected formula set (D3a) is law here, with TWO measured
refinements both driven by family facts the audit's worked example did
not cover (documented in D-REVISION-2 at the bottom):

  R1 (height axis): the audit's height ratio reads
  bone.matrix_local.translation.z. True for identity-transform rigs
  (Quaternius / UAL), but RH Mixamo-65 armatures carry the Y-up->Z-up
  conversion in their OBJECT transform (obj rot X 90 deg — the s20
  import law): their armature-local up is +Y. The ratio therefore
  projects the hips rest translation onto the armature's LOCAL UP AXIS
  (object-rotation^-1 @ world Z) — reduces to the audit's z-projection
  for identity rigs.

  R2 (location direction): the audited location law converts the
  src-armature-space delta directly into the target bone's rest basis,
  which silently assumes both armature-local frames agree. Cross-family
  they do not (RH local up = +Y vs identity rigs' +Z). The delta is
  routed through world: d_tgt = tgt_R^-1 @ src_R @ d_src (pure
  rotations via matrix_world.to_quaternion()), THEN magnitude-scaled by
  the height ratio, THEN into the target bone's rest basis.

THE FORMULA (per mapped pair src b -> tgt t, parents FIRST):
  D_s(b)     = M_src(b,f) @ M_src_rest(b)^-1     # src armature-space delta
  M_t(t,f)   = D_s(b) @ M_tgt_rest(t)            # target armature-space pose
  D_t(t)     = M_t(t,f) @ M_tgt_rest(t)^-1       # target delta (children reuse)
  basis(t,f) = M_tgt_rest(t)^-1 @ D_t(parent(t))^-1 @ D_s(b) @ M_tgt_rest(t)
               # root: D_t(parent) := I
  ROTATION: basis.to_quaternion() -> rotation_quaternion keys (the
            target bone's QUATERNION mode is asserted); sign
            continuity at write time (dot(q, q_prev) < 0 => q := -q).
  LOCATION (REV-3, data-driven): for EVERY mapped bone whose SOURCE
            action carries location fcurves, key the conjugated basis
            delta's translation x the height ratio into
            pose.bones[t].location (BONE-LOCAL, the s20 axis law) — the
            Quaternius disconnected-leg topology moves feet via
            per-bone locations, so a hips-only policy structurally
            drops the gait. The ratio-scaled delta also composes into
            D_t so chained location sources propagate consistently
            (audit A1 P2-4). A use_connect target bone's location is
            SKIPPED and reported (rep loc_no_op): a location fcurve
            cannot drive a connected bone — the same-class channel is
            an equally dead no-op in the SOURCE rig (the UAL walk
            replays gait-class from ROTATIONS alone, measured
            2026-10-18) — so nothing is dropped and there is nothing
            to refuse (audit A1 P1-3, as measured).

The parent-cancellation identity (why this is exact):
  D(p)^-1 @ D(b) = M_rest(b) @ basis_src @ M_rest(b)^-1 — the
  armature-space composition IS the parent-relative transfer with rest
  correction; pivot artifacts cancel exactly for non-root bones.

GATES (fail-closed, on the OUTPUT — REV-3 audit A1 enforcement):
  1. coverage floor: animated DEFORM-class src bones mapped >= 0.9;
     an EMPTY transferable set refuses (no vacuous 1.0 pass)
  2. output channel census: every keyed pose path must resolve on the
     target (clean RetargetRefused — was an unguarded KeyError)
  3. DRIVE check: stored fcurve values must reach the evaluated pose
     properties — rotation AND location channels (the frozen-
     evaluation class, measured live 2026-10-18); plus the SOURCE
     anti-frozen span check (data span vs evaluated span at the hips:
     a stuck source slot bakes a rest pose that drives fine)
  4. teleport guard: per-bone per-frame quaternion |delta| < 90 deg
  5. WORLD gates at sampled frames (run_world_gates, call AFTER
     staging — the wrapper MPI carries the family rescale): feet
     world-z ground floor + gait bands; hips world-z span; the CALLER
     asserts on the returned table (the lab's two-column law)
  6. fresh-bake-only: a NEW action `<src>__rt_<tgt>`; the source
     action is never mutated; fake_user left False until bind.
  7. scale law: uniform object scale asserted on BOTH rigs (any
     value — Mixamo-65 lands at 0.01 BY LAW); bone rest scale ~ 1.

Gates 1-4 raise RetargetRefused INSIDE retarget() — a bake that
violates them cannot return a rep (the docstring's fail-closed claim
is now load-bearing, audit A1 P1-1).
"""
import math

import bpy
from mathutils import Matrix, Quaternion, Vector

import blender_kit

# ------------------------------------------------------------------ #
# family mapping tables (semantic class -> per-family bone name)
# ------------------------------------------------------------------ #
FAMILIES = {
    "mixamo65": {
        "prefix": "mixamorig:",
        "bones": {
            "hips": "Hips", "spine": "Spine", "spine2": "Spine1",
            "spine3": "Spine2", "neck": "Neck", "head": "Head",
            "shoulder.L": "LeftShoulder", "arm.L": "LeftArm",
            "forearm.L": "LeftForeArm", "hand.L": "LeftHand",
            "shoulder.R": "RightShoulder", "arm.R": "RightArm",
            "forearm.R": "RightForeArm", "hand.R": "RightHand",
            "upleg.L": "LeftUpLeg", "leg.L": "LeftLeg",
            "foot.L": "LeftFoot", "toe.L": "LeftToeBase",
            "upleg.R": "RightUpLeg", "leg.R": "RightLeg",
            "foot.R": "RightFoot", "toe.R": "RightToeBase",
        },
        # hips root motion only (the RH clips carry hips location)
        "location_classes": ("hips",),
    },
    "rigify53": {
        "prefix": "DEF-",
        "bones": {
            "hips": "DEF-hips", "spine": "DEF-spine.001",
            "spine2": "DEF-spine.002", "spine3": "DEF-spine.003",
            "neck": "DEF-neck", "head": "DEF-head",
            "shoulder.L": "DEF-shoulder.L", "arm.L": "DEF-upper_arm.L",
            "forearm.L": "DEF-forearm.L", "hand.L": "DEF-hand.L",
            "shoulder.R": "DEF-shoulder.R", "arm.R": "DEF-upper_arm.R",
            "forearm.R": "DEF-forearm.R", "hand.R": "DEF-hand.R",
            "upleg.L": "DEF-thigh.L", "leg.L": "DEF-shin.L",
            "foot.L": "DEF-foot.L", "toe.L": "DEF-toe.L",
            "upleg.R": "DEF-thigh.R", "leg.R": "DEF-shin.R",
            "foot.R": "DEF-foot.R", "toe.R": "DEF-toe.R",
        },
        "location_classes": ("hips",),   # the bob lives on DEF-hips
    },
    "quaternius42": {
        "prefix": "",
        "bones": {
            "hips": "Hips", "spine": "Abdomen", "spine2": "Torso",
            "neck": "Neck", "head": "Head",
            "shoulder.L": "Shoulder.L", "arm.L": "UpperArm.L",
            "forearm.L": "LowerArm.L", "hand.L": "Palm.L",
            "shoulder.R": "Shoulder.R", "arm.R": "UpperArm.R",
            "forearm.R": "LowerArm.R", "hand.R": "Palm.R",
            "upleg.L": "UpperLeg.L", "leg.L": "LowerLeg.L",
            "foot.L": "Foot.L",
            "upleg.R": "UpperLeg.R", "leg.R": "LowerLeg.R",
            "foot.R": "Foot.R",
        },
        "location_classes": ("hips",),
    },
}

# per-family NON-TRANSFERABLES (D3c): excluded from the coverage
# denominator and never mapped. Fingers: rigify53/mixamo65 carry full
# articulation, quaternius42 has 3-bone stubs (Fingers/Thumb1/Thumb2) —
# a stub cannot carry articulation (the audited finger policy), so ALL
# families' finger bones are non-transferable (reported UNMAPPED for
# the census, hands land at rest on the target — the standard
# retarget compromise).
def _mixamo_finger(n):
    return any(k in n for k in ("Thumb", "Index", "Middle", "Ring",
                                "Pinky"))


def _rigify_finger(n):
    return n.startswith(("DEF-f_", "DEF-thumb"))


def _quat_finger(n):
    return n.startswith(("Fingers.", "MiddleHand.", "Thumb1.", "Thumb2."))


NON_TRANSFERABLE = {
    "mixamo65": lambda n: n.endswith(("_end", "Toe_End")) or _mixamo_finger(n),
    "rigify53": lambda n: ((not n.startswith("DEF-")) or n.endswith("_end")
                           or _rigify_finger(n)),
    "quaternius42": lambda n: (n.endswith("_end")
                               or n.startswith("PoleTarget")
                               or _quat_finger(n)),
}

COVERAGE_FLOOR = 0.9
TELEPORT_GUARD_DEG = 90.0
FEET_BAND = (-0.05, 0.15)
HIPS_GATE = (0.4, 1.4)



def _assign_action(arm, act):
    """The Blender 4.4+ action-slot law (ual_bake's live-probed
    precedent): `ad.action = X` alone does NOT reliably rebind — a
    legacy-slot binding stays STUCK and later assignments are silently
    ignored. Every assignment pins the slot too. The A2b P2-2 law, as
    MEASURED (the s23 fold-with-judgment form): a SLOTLESS action is a
    refusal ONLY when it would overwrite a LIVE binding (the stale-slot
    hazard is the overwrite); a FRESH binding of a slotless action is
    the legitimate fresh-bake shape (a newly baked action has no slots
    until the slotted API touches it) and proceeds with a loud print."""
    ad = arm.animation_data or arm.animation_data_create()
    had_live = ad.action is not None
    ad.action = act
    if act is not None and not act.slots:
        if had_live:
            raise RetargetRefused(
                f"_assign_action: {act.name!r} has ZERO slots and would "
                f"overwrite a LIVE binding on {arm.name} — the previous "
                f"slot stays stuck (the silent no-op drive class); clear "
                f"the binding first or fix the action")
        print(f"wrapper note: binding slotless {act.name!r} on "
              f"{arm.name} (fresh binding — no stale-slot hazard)",
              flush=True)
    if act is not None and act.slots:
        ad.action_slot = act.slots[0]
    return ad

class RetargetRefused(ValueError):
    """rig_retarget refuses — fail-closed."""


def _iter_fcurves(act):
    """blender_kit is a HARD dep (the 4.x<->5.x channelbag shim). The
    old `act.fcurves` fallback silently returned EMPTY on 5.x slotted
    actions -> src_loc_bones empty -> the location transfer silently
    dropped AND coverage vacuously 1.0 (audit A1 P2-5) — fail loudly
    instead."""
    return list(blender_kit.iter_fcurves(act))


def _animated_bones(act, exclude):
    """Bones with ANY animated channel in `act`, minus non-deforms."""
    out = set()
    for fc in _iter_fcurves(act):
        dp = fc.data_path
        if dp.startswith("pose.bones[") and '"' in dp:
            name = dp.split('"')[1]   # audit A1 P3-11: unguarded split
            if not exclude(name):
                out.add(name)
    return out


def detect_family(arm):
    """Census-based family detection (prefix + count); refuses unknown."""
    names = [b.name for b in arm.data.bones]
    for fam, spec in FAMILIES.items():
        pre = spec["prefix"]
        # fix-wave-1 D1-REV2: crowd/hero bones carry per-agent prefixes
        # (z0007:mixamorig:Hips / hmaster:DEF-head) — accept both the
        # bare prefix and the prefixed (":<prefix>" inside the name)
        hits = sum(1 for n in names
                   if (n.startswith(pre) or (":" + pre) in n) and n != pre)
        if fam == "mixamo65" and hits >= 60:
            return fam
        if fam == "rigify53" and hits >= 50:
            return fam
        if fam == "quaternius42" and hits >= len(spec["bones"]) - 6 \
                and not any(("mixamorig:" in n) or ("DEF-" in n)
                            for n in names):
            return fam
    raise RetargetRefused(
        f"cannot detect the rig family of {arm.name!r} "
        f"({len(names)} bones, sample {names[:4]}) — retargeting is "
        f"family-mapped, add the family to FAMILIES first")


def _assert_uniform_scale(arm, tag):
    s = arm.scale
    if max(s) - min(s) > 1e-3:
        raise RetargetRefused(
            f"{tag}: non-uniform object scale {tuple(s)} — the recipe "
            f"assumes uniform scale (D3e)")
    for b in arm.data.bones:
        m = b.matrix_local.to_3x3()
        # rest scale: row norms ~ 1 (audit A1 P3-10: these are ROW
        # norms — the label said columns; dead off-diagonal removed)
        lens = [math.sqrt(sum(m[i][j] ** 2 for j in range(3)))
                for i in range(3)]
        if max(abs(l - 1.0) for l in lens) > 1e-2:
            raise RetargetRefused(
                f"{tag}: bone {b.name!r} rest scale {lens} != identity "
                f"(D3e: bone rest matrices ~identity)")


def _local_up(arm):
    """The armature's LOCAL up axis = object-rotation^-1 @ world Z
    (R1: +Z for identity rigs, +Y for RH's rot-X-90 rigs)."""
    return (arm.matrix_world.to_quaternion().inverted()
            @ Vector((0, 0, 1))).normalized()


def _height_along_up(arm, bone_name):
    up = _local_up(arm)
    pos = arm.data.bones[bone_name].matrix_local.translation
    return up.dot(pos)


def height_ratio(src_arm, src_hips, tgt_arm, tgt_hips):
    srch = _height_along_up(src_arm, src_hips)
    tgth = _height_along_up(tgt_arm, tgt_hips)
    if abs(srch) < 1e-6:
        raise RetargetRefused(
            f"src hips rest height ~0 along the local up — {src_arm.name}"
            f" is not a standing rig?")
    if abs(tgth) < 1e-6:
        # audit A1 P2-8: ratio ~0 silently collapses every keyed
        # location to zero
        raise RetargetRefused(
            f"tgt hips rest height ~0 along the local up — "
            f"{tgt_arm.name} is not a standing rig?")
    ratio = tgth / srch
    if not math.isfinite(ratio):
        raise RetargetRefused("height ratio is not finite")
    return ratio


def retarget(src_arm, src_action, tgt_arm, tgt_family=None,
             src_family=None, sample_stride=1):
    """Bake `src_action` from `src_arm` onto `tgt_arm` as a NEW action.

    Returns rep = {"action", "name", "mapped", "unmapped", "ratio",
    "frames", "fps", "gates"} — gates = the measured world-gate table
    (numbers travel). REFUSES on coverage/scale/mode violations.
    """
    if src_arm.type != 'ARMATURE' or tgt_arm.type != 'ARMATURE':
        raise RetargetRefused("both rigs must be ARMATURE objects")
    _assert_uniform_scale(src_arm, "src")
    _assert_uniform_scale(tgt_arm, "tgt")
    for pb in tgt_arm.pose.bones:
        if pb.rotation_mode != 'QUATERNION':
            raise RetargetRefused(
                f"target pose bone {pb.name!r} is {pb.rotation_mode} — "
                f"the recipe keys rotation_quaternion (assert QUATERNION "
                f"first; the s18 silently-inert law)")

    sf = src_family or detect_family(src_arm)
    tf = tgt_family or detect_family(tgt_arm)
    sspec, tspec = FAMILIES[sf], FAMILIES[tf]

    # class -> (src bone, tgt bone) pairs; report unmapped src anims
    pairs = {}
    for cls, sb in sspec["bones"].items():
        tb = tspec["bones"].get(cls)
        if tb is None:
            continue
        if sb in src_arm.data.bones and tb in tgt_arm.data.bones:
            pairs[cls] = (sb, tb)
    if "hips" not in pairs:
        raise RetargetRefused(f"{sf}->{tf}: no mapped hips class — "
                              f"refusing a rootless transfer")

    src_anim = _animated_bones(src_action, NON_TRANSFERABLE[sf])
    mapped_src = {sb for sb, _ in pairs.values()}
    # D3c refined: bones whose CLASS the target family lacks (e.g.
    # rigify's spine.003 / toes vs quaternius's 2-spine no-toe body)
    # are NO-TARGET (reported, excluded from the denominator) — they
    # are anatomy gaps, not map failures. Coverage measures the
    # transferable set: mapped vs animated-in-mappable-classes.
    s_rev = {}
    for cls, sb in sspec["bones"].items():
        s_rev[sb] = cls
    no_target = set()
    for b in src_anim:
        cls = s_rev.get(b)
        if cls is not None and cls not in tspec["bones"]:
            no_target.add(b)
    transferable = src_anim - no_target
    if not transferable:
        # audit A1 P2-6: an empty/degenerate source action scored
        # coverage 1.0 and baked a vacuous rest pose, green gates
        raise RetargetRefused(
            f"source action {src_action.name!r} animates no transferable "
            f"bones under the {sf} map — degenerate/empty action, "
            f"refusing a vacuous bake")
    unmapped = sorted(transferable - mapped_src)
    coverage = (len(transferable & mapped_src) / len(transferable)) \
        if transferable else 1.0
    if coverage < COVERAGE_FLOOR:
        raise RetargetRefused(
            f"coverage {coverage:.2f} < {COVERAGE_FLOOR} "
            f"(unmapped animated: {unmapped[:8]}) — the map cannot "
            f"carry this clip, refusing (D3 gate 1)")

    # parents-first order over TARGET hierarchy (mapped bones only)
    order = sorted(pairs.values(),
                   key=lambda p: _chain(tgt_arm.data.bones[p[1]]))

    # ---- read the source across frames ----
    frames = _frame_list(src_action, sample_stride)
    fps = bpy.context.scene.render.fps   # output fps pinned from source
    src_rest = {b: src_arm.data.bones[b].matrix_local.copy()
                for b, _ in order}
    tgt_rest = {b: tgt_arm.data.bones[b].matrix_local.copy()
                for _, b in order}
    ratio = height_ratio(src_arm, pairs["hips"][0], tgt_arm,
                         pairs["hips"][1])
    # REV-3 location law (data-driven): transfer location for every
    # mapped bone whose SOURCE action carries location fcurves. The
    # measured topology fact behind this: the Quaternius rigs have
    # DISCONNECTED leg chains (Foot.L parents to the root Bone, not to
    # LowerLeg — probed 2026-10-18) so their clips move feet via
    # per-bone LOCATION channels; a hips-only policy structurally
    # drops the gait. For Mixamo-65 sources only Hips carries location
    # — the old hips-only behavior falls out of the same rule.
    src_loc_bones = set()
    for fc in _iter_fcurves(src_action):
        if fc.data_path.endswith(".location") and '"' in fc.data_path:
            src_loc_bones.add(fc.data_path.split('"')[1])

    # action slot scaffolding: assign -> evaluate -> read
    prev_src_action = (src_arm.animation_data.action
                       if src_arm.animation_data else None)
    _assign_action(src_arm, src_action)
    sc = bpy.context.scene
    # the SOURCE side of the stuck-pose law (A2b P2-3 — the s22 law
    # was implemented target-only): unassigning/clearing leaves the
    # last evaluated pose IN the properties; mapped source bones the
    # action does NOT key would bake that T-pose residue silently at
    # coverage 1.0. Reset unkeyed mapped bones to rest before sampling.
    keyed_src_bones = set()
    for fc in _iter_fcurves(src_action):
        dp = getattr(fc, "data_path", "") or ""
        if '"' in dp:
            keyed_src_bones.add(dp.split('"')[1])
    for cls in _pairs_in_order(pairs, order):
        sb = pairs[cls][0]
        if sb in keyed_src_bones:
            continue
        pb = src_arm.pose.bones.get(sb)
        if pb is None:
            continue
        pb.location = (0.0, 0.0, 0.0)
        pb.scale = (1.0, 1.0, 1.0)
        if pb.rotation_mode == 'QUATERNION':
            pb.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
        else:
            pb.rotation_euler = (0.0, 0.0, 0.0)

    samples = {}    # frame -> {tgt_bone: {"q": Quaternion, "loc": Vector}}
    for f in frames:
        sc.frame_set(f)
        bpy.context.view_layer.update()
        D_t = {}
        frame_out = {}
        for cls in _pairs_in_order(pairs, order):
            sb, tb = pairs[cls]
            M_src = src_arm.pose.bones[sb].matrix.copy()
            M_s_rest = src_rest[sb]
            M_t_rest = tgt_rest[tb]
            D_s = M_src @ M_s_rest.inverted()
            parent_tb = tgt_arm.data.bones[tb].parent
            parent_D = D_t.get(parent_tb.name) if parent_tb else None
            if parent_tb is not None and parent_D is None:
                # unmapped parent: the audited root rule (D_t := I)
                parent_D = Matrix.Identity(4)
            if parent_D is None:
                parent_D = Matrix.Identity(4)
            basis = M_t_rest.inverted() @ parent_D.inverted() @ D_s \
                @ M_t_rest
            entry = {"q": basis.to_quaternion()}
            if sb in src_loc_bones:
                # the exact conjugated delta's translation, ratio-scaled
                # (the basis composition routes frames structurally —
                # no separate world routing needed)
                loc = basis.to_translation() * ratio
                entry["loc"] = loc
                # audit A1 P2-4: the KEYED location is ratio-scaled, so
                # the delta descendants must compensate is the SCALED
                # pose — compose the effective local basis into D_t or
                # chained location sources carry a
                # (ratio-1)*parent-motion world error
                basis_eff = Matrix.Translation(loc) \
                    @ basis.to_quaternion().to_matrix().to_4x4()
            else:
                basis_eff = basis
            # identity: parent_D @ M_t_rest @ basis == D_s @ M_t_rest
            # (the unscaled composition); with basis_eff the same
            # composition matches what the keyed channels evaluate
            M_t = parent_D @ M_t_rest @ basis_eff
            D_t[tb] = M_t @ M_t_rest.inverted()
            frame_out[tb] = entry
        samples[f] = frame_out
    # restore the source's previous action (fresh-bake-only: never
    # leave the source rebound)
    _assign_action(src_arm, prev_src_action)

    # ---- write the output action ----
    out_name = f"{src_action.name}__rt_{tgt_arm.name}"
    if out_name in bpy.data.actions:
        raise RetargetRefused(
            f"output action {out_name!r} already exists — fresh-bake-"
            f"only law: rename or delete the stale bake first")
    out = bpy.data.actions.new(out_name)
    out.use_fake_user = False          # pinned at bind time (D5a)
    # THE STUCK-POSE LAW: unassigning an action leaves the last
    # evaluated pose IN the pose-bone properties. The output keys
    # rotation (+ the REV-3 data-driven locations) only — every other
    # channel must
    # evaluate from REST, not from the stuck import pose (the loader's
    # slot-clear cannot fix properties already mutated by evaluation).
    keyed = {tb for _, tb in pairs.values()}
    loc_no_op = []   # connected targets: location is an undriveable
                     # no-op in source AND target (skipped, reported)
    for pb in tgt_arm.pose.bones:
        pb.location = (0.0, 0.0, 0.0)
        pb.scale = (1.0, 1.0, 1.0)
        if pb.name not in keyed:
            pb.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
    # BIND-THEN-WRITE (the 5.x context law — probed: channelbag
    # fcurves.new() resolves pose paths against the CONTEXT object;
    # assigning the fresh action to the target gives the slot a real
    # target so the write is context-independent). Restore after.
    prev_tgt_action = (tgt_arm.animation_data.action
                       if tgt_arm.animation_data else None)
    _assign_action(tgt_arm, out)
    for cls in _pairs_in_order(pairs, order):
        sb, tb = pairs[cls]
        # rotation keys (wxyz; sign continuity per bone)
        qw = blender_kit.fcurves_new(
            out, f'pose.bones["{tb}"].rotation_quaternion', index=0)
        qxyz = [blender_kit.fcurves_new(
            out, f'pose.bones["{tb}"].rotation_quaternion', index=i)
            for i in (1, 2, 3)]
        prev = None
        for f in frames:
            q = samples[f][tb]["q"].copy()
            if prev is not None and q.dot(prev) < 0:
                q.negate()
            prev = q
            comps = [(qw, q.w)] + list(zip(qxyz, (q.x, q.y, q.z)))
            for fc, val in comps:
                fc.keyframe_points.add(1)
                fc.keyframe_points[-1].co = (f, val)
                fc.keyframe_points[-1].interpolation = 'LINEAR'
        if samples[frames[0]][tb].get("loc") is not None:
            if tgt_arm.pose.bones[tb].bone.use_connect:
                # audit A1 P1-3, as MEASURED (s23): a location fcurve
                # cannot drive a CONNECTED bone — and the same-class
                # channel is an equally dead no-op in the SOURCE rig
                # (the UAL walk replays gait-class from ROTATIONS
                # alone, measured 2026-10-18), so nothing is dropped:
                # skip the write, say so in the rep (no silent lie,
                # no refusal of the working path)
                loc_no_op.append(tb)
            else:
                for i in range(3):
                    fc = blender_kit.fcurves_new(
                        out, f'pose.bones["{tb}"].location', index=i)
                    for f in frames:
                        fc.keyframe_points.add(1)
                        fc.keyframe_points[-1].co = \
                            (f, samples[f][tb]["loc"][i])
                        fc.keyframe_points[-1].interpolation = 'LINEAR'
    _assign_action(tgt_arm, prev_tgt_action)   # slot restored

    # ---- gates (bake-time, staging-immune): census + drive + teleport
    gates = _run_closure(src_arm, src_action, tgt_arm, out, pairs,
                         frames, sample_stride)
    # audit A1 P1-1: the docstring said fail-closed; the flags were
    # computed and RETURNED but never enforced
    if not gates["drives_ok"]:
        raise RetargetRefused(
            f"drive check FAILED (err {gates['drive_err_max']:.2e} >= "
            f"1e-4): keyed fcurve values do not reach the evaluated "
            f"pose — the frozen-evaluation / stuck-slot class; "
            f"refusing a dead bake")
    if not gates["teleport_ok"]:
        raise RetargetRefused(
            f"teleport guard tripped "
            f"({gates['max_qdelta_deg']:.1f} deg > {TELEPORT_GUARD_DEG}) "
            f"— per-frame pose jump, refusing")
    rep = {"action": out, "name": out_name, "mapped": len(pairs),
           "unmapped": unmapped, "no_target": sorted(no_target),
           "loc_no_op": loc_no_op,
           "ratio": round(ratio, 4),
           "frames": [frames[0], frames[-1]], "fps": fps,
           "coverage": round(coverage, 4), "gates": gates}
    return rep


def _chain(bone):
    n, c = bone, 0
    while n.parent is not None:
        n, c = n.parent, c + 1
    return c


def _pairs_in_order(pairs, order):
    """Yield classes in the parents-first order (order carries tuples)."""
    cls_by_tgt = {tb: cls for cls, (sb, tb) in pairs.items()}
    for sb, tb in order:
        yield cls_by_tgt[tb]


def _frame_list(action, stride):
    lo, hi = action.frame_range
    f0, f1 = int(math.ceil(lo)), int(math.floor(hi))
    return list(range(f0, f1 + 1, max(1, stride)))


def run_world_gates(tgt_arm, action, sample_stride=2):
    """The D3 gate-3 WORLD gates — call AFTER staging (the wrapper MPI
    carries the family rescale; the bake-time gates are staging-immune
    by design). Feet world-z band + hips world-z span, frame-evaluated
    (the s20 law). Returns the measured table; the CALLER asserts the
    bands against its staging context (the lab's two-column law)."""
    sc = bpy.context.scene
    prev = (tgt_arm.animation_data.action
            if tgt_arm.animation_data else None)
    _assign_action(tgt_arm, action)
    hips = next((pb for pb in tgt_arm.pose.bones
                 if pb.name.lower().split('.')[-1] == 'hips'
                 or pb.name.lower().endswith('hips')), None)
    feet = [pb for pb in tgt_arm.pose.bones
            if 'foot' in pb.name.lower() and not
            pb.name.lower().endswith('_end')]
    lo, hi = action.frame_range
    frames = list(range(int(math.ceil(lo)), int(math.floor(hi)) + 1,
                        max(1, sample_stride)))
    rows = {"frames": [], "feet_z": [], "hips_z": []}
    for f in frames:
        sc.frame_set(f)
        bpy.context.view_layer.update()
        rows["frames"].append(f)
        rows["feet_z"].append([
            round((tgt_arm.matrix_world @ pb.matrix).translation.z, 4)
            for pb in feet])
        rows["hips_z"].append(
            round((tgt_arm.matrix_world @ hips.matrix).translation.z, 4)
            if hips else None)
    _assign_action(tgt_arm, prev)
    return rows


def _run_closure(src_arm, src_action, tgt_arm, out_action, pairs,
                 frames, stride):
    """The DRIVE CHECK + teleport guard. The exact-pose closure was
    retired with REV-3: the ratio-scaled location transfer is not the
    identity reproduction (the pose is a scaled copy of the source, by
    design). What must hold — and what the live failure class violates
    — is that the OUTPUT ACTION actually DRIVES every keyed bone: the
    fcurve's stored value at frame f must reach the evaluated pose
    property. Catches the frozen-evaluation class measured live
    2026-10-18 (an FBX-imported rig evaluates its pose FROZEN at rest
    under certain action/slot states — rotations never reach the
    figure) and the stuck-slot class."""
    sc = bpy.context.scene
    # GATE 2 (output channel census, audit A1 P2-9): every keyed pose
    # path must resolve on the target — the lookups below were an
    # unguarded KeyError, violating the no-traceback contract
    keyed_paths = {fc.data_path for fc in _iter_fcurves(out_action)
                   if fc.data_path.startswith("pose.bones[")
                   and '"' in fc.data_path}
    for dp in sorted(keyed_paths):
        if dp.split('"')[1] not in tgt_arm.pose.bones:
            raise RetargetRefused(
                f"keyed path {dp!r} does not resolve on target "
                f"{tgt_arm.name!r} — stale bake or name drift")
    # fcurve lookup: per keyed bone, the quat-w curve (every keyed
    # bone has one) + the location curves (REV-3: location channels
    # are load-bearing — they get the same drive law, audit A1 P1-3)
    qw = {}
    locf = {}
    for fc in _iter_fcurves(out_action):
        if '"' not in fc.data_path:
            continue
        bn = fc.data_path.split('"')[1]
        if fc.data_path.endswith(".rotation_quaternion") \
                and fc.array_index == 0:
            qw[bn] = fc
        elif fc.data_path.endswith(".location"):
            locf.setdefault(bn, {})[fc.array_index] = fc
    # SOURCE anti-frozen defense (audit A1 P1-2): if the source
    # assignment silently failed to rebind (the stuck-slot class),
    # every sample reads REST -> a rest-pose bake DRIVES fine (its
    # constant values reach the properties) and teleports never — the
    # output gates cannot see it. Compare the source action's DATA
    # span (fcurve values) vs the EVALUATED hips span at the same
    # frames: animated data with a frozen evaluation refuses.
    prev_src = (src_arm.animation_data.action
                if src_arm.animation_data else None)
    src_fc = [fc for fc in _iter_fcurves(src_action)
              if '"' in fc.data_path
              and fc.data_path.split('"')[1] == pairs["hips"][0]]
    src_data_lo, src_data_hi = math.inf, -math.inf
    for fc in src_fc:
        for f in frames[::max(1, (len(frames) // 12) or 1)]:
            v = fc.evaluate(f)
            src_data_lo, src_data_hi = min(src_data_lo, v), \
                max(src_data_hi, v)
    _assign_action(src_arm, src_action)
    hips_pb = src_arm.pose.bones[pairs["hips"][0]]
    eval_chans = []
    for f in frames[::max(1, (len(frames) // 12) or 1)]:
        sc.frame_set(f)
        bpy.context.view_layer.update()
        eval_chans.append(list(hips_pb.rotation_quaternion)
                          + list(hips_pb.location))
    _assign_action(src_arm, prev_src)
    if src_fc:
        eval_lo = [min(c[i] for c in eval_chans)
                   for i in range(len(eval_chans[0]))]
        eval_hi = [max(c[i] for c in eval_chans)
                   for i in range(len(eval_chans[0]))]
        eval_span = max(hi - lo for lo, hi in zip(eval_lo, eval_hi))
        data_span = src_data_hi - src_data_lo
        if data_span > 1e-4 and eval_span < 1e-4:
            raise RetargetRefused(
                f"source {src_arm.name!r} evaluates FROZEN at rest "
                f"while {src_action.name!r} carries motion (data span "
                f"{data_span:.2e}, evaluated {eval_span:.2e}) — the "
                f"stuck-source-slot class; refusing a rest-pose bake")
    prev_tgt = (tgt_arm.animation_data.action
                if tgt_arm.animation_data else None)
    _assign_action(tgt_arm, out_action)
    sample = frames[::max(1, (len(frames) // 12) or 1)]
    rows = {"frames": sample, "drive_err_max": 0.0,
            "max_qdelta_deg": 0.0}
    prev_q = {}
    for f in sample:
        sc.frame_set(f)
        bpy.context.view_layer.update()
        for tb, fc in qw.items():
            # stored value at f (fcurve evaluation at the key)
            stored = fc.evaluate(f)
            got_w = tgt_arm.pose.bones[tb].rotation_quaternion.w
            rows["drive_err_max"] = max(rows["drive_err_max"],
                                        abs(stored - got_w))
            q = tgt_arm.pose.bones[tb].rotation_quaternion
            if tb in prev_q:
                ang = q.rotation_difference(prev_q[tb]).angle
                rows["max_qdelta_deg"] = max(rows["max_qdelta_deg"],
                                             math.degrees(ang))
            prev_q[tb] = q.copy()
        for tb, by_idx in locf.items():
            pb = tgt_arm.pose.bones[tb]
            for i, fc in by_idx.items():
                stored = fc.evaluate(f)
                rows["drive_err_max"] = max(rows["drive_err_max"],
                                            abs(stored - pb.location[i]))
    _assign_action(tgt_arm, prev_tgt)
    rows["drives_ok"] = rows["drive_err_max"] < 1e-4
    rows["teleport_ok"] = rows["max_qdelta_deg"] < TELEPORT_GUARD_DEG
    return rows
