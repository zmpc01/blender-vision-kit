"""gait_modifiers.py -- generalized funny-walk gait-modifier engine.

KIT-LEVEL, SCENE-AGNOSTIC (session-26 generalization law: funny-walk
pedestrians are a GENERALIZED kit capability -- "we build these not
just for this zombie scene"; the scene contributes only DATA, its
named modifier stacks and base-clip compositions). Lifted verbatim
from the previz crowd_v6/clips.py modifier core (the crowd_fields.py
precedent: the kit owns the pure engine, the scene imports it and
keeps its own tables).

Pure python, NO bpy / NO mathutils (importable by headless sims,
tests, exporters; quaternions are plain (w, x, y, z) 4-tuples).

THE LAW (a funny walk = base clip + additive per-bone deltas):
  a funny walk is NEVER a new mocap clip -- it is a library base
  clip plus a named stack of small bone-channel deltas composed
  ADDITIVELY over the base pose (the Seated_Flinch precedent:
  compose source-channel deltas onto a base loop, never key the
  imported sources). The same vocabulary builds zombie shambles,
  pedestrian variety, and any future funny walk.

THREE PRIMITIVES:

1. DELTA DATACLASSES (RotDelta / LocDelta) -- one bone-local channel
   delta with four KINDS: "osc" (sinusoidal over the gait cycle),
   "bias" (constant offset), "amp" (scale the base clip's whole
   deviation from rest), "twitch" (3-key jerk pulse).

2. NAMED MODIFIER TABLES (GAIT_MODIFIERS + register_modifiers) --
   stacks of deltas under a choosable name ("head_z_wobble",
   "arm_swing_var"). The kit ships the GENERIC vocabulary (head-bob
   drift, arm-swing variance, lean oscillation, step asymmetry);
   a scene registers its own names into the SAME registry
   (fail-closed: duplicates / bad kinds / bad axes / non-finite
   numbers / non-iterable tables raise).

3. THE COMPOSITION CORE (apply_modifiers + the quaternion math) --
   compose a named stack onto ANY {bone: (loc, quat)} pose table
   (bones absent from the table are skipped, never a KeyError; an
   unknown stack NAME raises ValueError listing the registered
   names); quat_mul / quat_axis_angle / quat_pow / quat_slerp on plain
   tuples, canonicalize_quats (the dot<0 anti-flip law across
   frames), decompose (pure row-major 4x4 -> (loc, quat); the
   mathutils Matrix.decompose twin with scale pinned 1.0).

Provenance: the modifier-composition law re-derived from public
docs of iCrowds (anti-robotic per-agent variety; GPL, product not
vendored) + bgyss Blender-Crow's modifier-style variety reads. The
quaternion algebra is standard (Hamilton product; Shepperd's method
for the matrix extraction). Zero code copied.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

__all__ = [
    "RotDelta", "LocDelta",
    "VALID_KINDS", "VALID_AXES",
    "GAIT_MODIFIERS", "register_modifiers", "validate_modifiers",
    "quat_mul", "quat_axis_angle", "quat_pow", "quat_slerp",
    "decompose", "canonicalize_quats",
    "eval_rot_delta", "eval_loc_delta", "apply_modifiers",
]


# ---------------------------------------------------------------------------
# 1. the delta dataclasses
# ---------------------------------------------------------------------------

VALID_KINDS = ("osc", "bias", "amp", "twitch")
VALID_AXES = ("x", "y", "z")


@dataclass(frozen=True)
class RotDelta:
    """One bone-local rotation delta.

    kind:
      "osc"    sinusoidal: amp_deg * sin(2*pi*(cycles*p + turn)) on the
               bone-local axis (head z-wobble, spine sway, lean osc);
      "bias"   constant: amp_deg always (shoulder droop, hips drag);
      "amp"    amplitude scale: the base clip's WHOLE deviation
               quaternion from the rest pose is re-powered --
               quat_pow(q, amp_deg) scales the full rotation ANGLE
               by amp_deg on its own (possibly compound) axis (thigh
               drag 0.55, arm pump 1.35). NOT a per-axis-component
               scale: the axis field is documentary for this kind
               (audit s28-a2 P3-4 -- the implementation has always
               powered the whole quaternion, which is the better
               visual: compound gaits scale coherently);
      "twitch" 3-key jerk: piecewise pulse over the cycle (head
               twitch): 0 at p=0, +amp at 0.2, -amp at 0.4, back to 0
               by 0.6, held 0 after (reads as a snap, not a wobble).

    p is the gait cycle phase in [0, 1). Rotation deltas never touch
    location channels -- LocDelta is the twin lever.
    """
    bone: str
    axis: str                 # "x" | "y" | "z"
    kind: str
    amp_deg: float
    cycles: float = 1.0
    turn: float = 0.0


@dataclass(frozen=True)
class LocDelta:
    """One bone-local location delta (the RotDelta twin; metres, not
    degrees -- the hip-hitch / bounce / drift lever).

    kind:
      "osc"    sinusoidal: amp_m * sin(2*pi*(cycles*p + turn)) ADDED
               on the bone-local axis (hip bob, lateral drift);
      "bias"   constant: amp_m always added (a hip hitch, a pelvis
               offset);
      "amp"    amplitude scale: the base clip's WHOLE location
               deviation is scaled -- (loc * amp_m), componentwise on
               every axis. NOT a per-axis-component scale: the axis
               field is documentary for this kind (the LocDelta twin
               of RotDelta "amp"'s whole-quaternion law);
      "twitch" 3-key jerk: the SAME pulse shape as RotDelta's, in
               metres (a step hitch that snaps, not wobbles).

    p is the gait cycle phase in [0, 1). Location deltas never touch
    rotation channels. CAUTION (the root-displacement invariance
    law): stride-feeding readers assume rotation-only modifiers -- a
    loc delta on a root/hips bone moves the character's origin, so
    keep loc deltas on non-root bones or own the phase-law
    consequences.
    """
    bone: str
    axis: str                 # "x" | "y" | "z"
    kind: str
    amp_m: float
    cycles: float = 1.0
    turn: float = 0.0


def _amp_of(d):
    """The amplitude scalar of either delta flavour (validation)."""
    return d.amp_deg if isinstance(d, RotDelta) else d.amp_m


# ---------------------------------------------------------------------------
# 2. named modifier tables (the registry + the composable API)
# ---------------------------------------------------------------------------

# The shared registry: name -> tuple of deltas. Pre-seeded with the
# GENERIC funny-walk vocabulary (bone names speak the kit's UAL/Rigify
# DEF-* vocabulary -- a scene on another rig registers its own names;
# apply_modifiers skips bones absent from the pose table, so a vocab
# entry that does not match the rig is a no-op, not a failure).
GAIT_MODIFIERS: dict[str, tuple] = {
    # --- the generalized funny-walk vocabulary (kit defaults) ---
    "head_bob_drift": (RotDelta("DEF-head", "x", "osc", 3.0, 0.5, 0.0),),
    "arm_swing_var": (RotDelta("DEF-upper_arm.L", "x", "amp", 0.85),
                      RotDelta("DEF-upper_arm.R", "x", "amp", 1.15),),
    "lean_osc": (RotDelta("DEF-spine", "x", "osc", 4.0, 1.0, 0.0),),
    "step_asym": (RotDelta("DEF-thigh.L", "x", "amp", 1.10),
                  RotDelta("DEF-thigh.R", "x", "amp", 0.90),),
}


def register_modifiers(**named) -> dict:
    """Register scene-side named modifier tables into the shared
    GAIT_MODIFIERS registry (the composable API: a scene defines its
    own funny-walk vocabulary and registers it; apply_modifiers
    resolves stack names through the SAME registry).

        register_modifiers(
            head_z_wobble=(RotDelta("DEF-head", "z", "osc", 12.0),),
            hip_hitch=(LocDelta("DEF-hips", "y", "twitch", 0.03),),
        )

    A bare RotDelta/LocDelta (not wrapped in a tuple) is accepted as
    a one-entry table. FAIL-CLOSED and ATOMIC: every entry is
    validated BEFORE any insert -- an unknown kind, a bad axis, a
    non-finite amplitude/cycles/turn (a non-finite cycle law
    silently NaN-poisons every quat downstream), a non-iterable
    table, a non-delta object, an empty table, or a DUPLICATE name
    raises ValueError and leaves the registry untouched (a silent
    re-register would be a vocabulary collision, not an override).
    Returns the registry dict.
    """
    if not named:
        raise ValueError(
            "register_modifiers: no tables given "
            "(call as name=(deltas,) kwargs)")
    staged = {}
    for nm, ds in named.items():
        if nm in GAIT_MODIFIERS:
            raise ValueError(
                f"register_modifiers: {nm!r} is already registered "
                f"(re-registering is a vocabulary collision, not an "
                f"override -- pick a new name)")
        if isinstance(ds, (RotDelta, LocDelta)):
            ds = (ds,)
        try:
            ds = tuple(ds)
        except TypeError:
            # the documented contract is ValueError on every bad
            # table: a non-iterable (an int, None, ...) used to leak
            # a bare TypeError out of tuple(ds)
            raise ValueError(
                f"register_modifiers: {nm!r} table is not iterable "
                f"({type(ds).__name__}) -- pass a tuple of deltas "
                f"or one bare RotDelta/LocDelta") from None
        if not ds:
            raise ValueError(f"register_modifiers: {nm!r} has no deltas")
        for d in ds:
            if not isinstance(d, (RotDelta, LocDelta)):
                raise ValueError(
                    f"register_modifiers: {nm!r} entry {d!r} is "
                    f"neither RotDelta nor LocDelta")
            if d.kind not in VALID_KINDS:
                raise ValueError(
                    f"register_modifiers: {nm!r} bad kind {d.kind!r} "
                    f"(valid: {VALID_KINDS})")
            if d.axis not in VALID_AXES:
                raise ValueError(
                    f"register_modifiers: {nm!r} bad axis {d.axis!r} "
                    f"(valid: {VALID_AXES})")
            if not math.isfinite(_amp_of(d)):
                raise ValueError(
                    f"register_modifiers: {nm!r} non-finite amp")
            if not (math.isfinite(d.cycles) and math.isfinite(d.turn)):
                raise ValueError(
                    f"register_modifiers: {nm!r} non-finite "
                    f"cycles/turn (sin(2*pi*(cycles*p + turn)) would "
                    f"NaN-poison every quat downstream)")
        staged[nm] = ds
    GAIT_MODIFIERS.update(staged)
    return GAIT_MODIFIERS


def validate_modifiers(table: dict | None = None) -> list:
    """Fail-closed modifier-table validation (the findings style:
    empty list = clean). table defaults to the whole registry; pass a
    plain dict to audit a hand-built table WITHOUT registering it
    (register_modifiers raises on the same laws -- this is the
    audit-side twin, the validate_registry pattern)."""
    if table is None:
        table = GAIT_MODIFIERS
    out = []
    for m, ds in table.items():
        if not ds:
            out.append(f"modifier {m}: empty table")
            continue
        try:
            entries = tuple(ds)
        except TypeError:
            # findings style: report a non-iterable table, never
            # crash out of the audit (the register_modifiers twin)
            out.append(f"modifier {m}: table is not iterable "
                       f"({type(ds).__name__})")
            continue
        for d in entries:
            if not isinstance(d, (RotDelta, LocDelta)):
                out.append(f"modifier {m}: entry is neither RotDelta "
                           f"nor LocDelta ({type(d).__name__})")
                continue
            if d.kind not in VALID_KINDS:
                out.append(f"modifier {m}: bad kind {d.kind}")
            if d.axis not in VALID_AXES:
                out.append(f"modifier {m}: bad axis {d.axis}")
            if not math.isfinite(_amp_of(d)):
                out.append(f"modifier {m}: non-finite amp")
            if not (math.isfinite(d.cycles) and math.isfinite(d.turn)):
                out.append(f"modifier {m}: non-finite cycles/turn")
    return out


# ---------------------------------------------------------------------------
# 3. the composition core (pure; plain 4-tuples, no bpy / no mathutils)
# ---------------------------------------------------------------------------

_AXIS_VEC = {"x": (1.0, 0.0, 0.0), "y": (0.0, 1.0, 0.0),
             "z": (0.0, 0.0, 1.0)}
_AXIS_IDX = {"x": 0, "y": 1, "z": 2}


def quat_mul(a, b):
    """Hamilton product of two 4-tuples (w, x, y, z)."""
    aw, ax, ay, az = a
    bw, bx, by, bz = b
    return (aw * bw - ax * bx - ay * by - az * bz,
            aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw)


def quat_axis_angle(axis: str, deg: float):
    """Unit quaternion for a bone-local rotation of deg degrees about
    the named axis."""
    v = _AXIS_VEC[axis]
    half = math.radians(deg) * 0.5
    s = math.sin(half)
    return (math.cos(half), v[0] * s, v[1] * s, v[2] * s)


def quat_pow(q, k: float):
    """Quaternion power (angle scaled by k) -- the "amp" modifier on
    the deviation-from-rest rotation. Identity-safe and k=0-safe.

    Fail-closed input guard (audit s28-a2 P3-9): the power is only
    defined on the unit sphere. A non-unit tuple used to flow
    through silently (atan2 is scale-invariant so the angle
    survived, but the contract was trust); the guard now normalizes
    explicitly, and a zero-norm tuple RAISES (no rotation to
    scale)."""
    w, x, y, z = q
    nrm = math.sqrt(w * w + x * x + y * y + z * z)
    if nrm < 1e-12:
        raise ValueError("quat_pow: zero-norm quaternion "
                         "(no rotation to scale)")
    if abs(nrm - 1.0) > 1e-12:
        w, x, y, z = w / nrm, x / nrm, y / nrm, z / nrm
    n = math.sqrt(x * x + y * y + z * z)
    if n < 1e-12 or abs(k) < 1e-12:
        return (1.0, 0.0, 0.0, 0.0)
    ang = 2.0 * math.atan2(n, w)
    # normalize into the short representation first (canonical sign)
    if w < 0.0:
        w, x, y, z = -w, -x, -y, -z
        ang = 2.0 * math.atan2(n, w)
    ang2 = ang * k * 0.5
    s = math.sin(ang2) / n
    return (math.cos(ang2), x * s, y * s, z * s)


def quat_slerp(a, b, t: float):
    """Spherical lerp between two unit quaternions (plain 4-tuples;
    the tuple twin of ual_bake._mix's mathutils slerp -- clip-switch
    blends). Shortest-path (dot < 0 -> negate b); t=0/1 and
    near-parallel degenerate cases handled explicitly."""
    d = (a[0] * b[0] + a[1] * b[1] + a[2] * b[2] + a[3] * b[3])
    bb = b
    if d < 0.0:                       # shortest path
        bb = (-b[0], -b[1], -b[2], -b[3])
        d = -d
    if d > 0.9995:                    # near-parallel: nlerp is exact
        # enough and avoids the division-by-sin(0) blowup
        o = tuple(a[j] + (bb[j] - a[j]) * t for j in range(4))
        n = math.sqrt(sum(v * v for v in o)) or 1.0
        return tuple(v / n for v in o)
    th = math.acos(max(-1.0, min(1.0, d)))
    s = math.sin(th)
    wa = math.sin((1.0 - t) * th) / s
    wb = math.sin(t * th) / s
    return tuple(a[j] * wa + bb[j] * wb for j in range(4))


def decompose(m):
    """Row-major 4x4 basis matrix -> the pose-table entry shape
    ((x, y, z), (w, x, y, z)).

    The PURE twin of the bpy-side ``matrix_basis.decompose()`` read
    (the ual_bake._record_table law): scale is pinned 1.0 and
    OMITTED -- pose tables carry (loc, quat) only, so a scene can
    build a table under system python (an exporter replaying baked
    rows, a test mock) without mathutils. m is indexed m[row][col]
    (mathutils Matrix order); the 3x3 must be a rigid rotation
    (Shepperd's method -- the branch picks the largest squared
    component so the divisor never approaches zero). q and -q are
    the same rotation: the returned sign is whichever the branch
    yields (canonicalize_quats is the cross-frame sign law).
    """
    loc = (float(m[0][3]), float(m[1][3]), float(m[2][3]))
    r00, r01, r02 = float(m[0][0]), float(m[0][1]), float(m[0][2])
    r10, r11, r12 = float(m[1][0]), float(m[1][1]), float(m[1][2])
    r20, r21, r22 = float(m[2][0]), float(m[2][1]), float(m[2][2])
    tr = r00 + r11 + r22
    if tr > 0.0:
        s = math.sqrt(tr + 1.0) * 2.0
        w, x, y, z = (0.25 * s, (r21 - r12) / s,
                      (r02 - r20) / s, (r10 - r01) / s)
    elif r00 > r11 and r00 > r22:
        s = math.sqrt(1.0 + r00 - r11 - r22) * 2.0
        w, x, y, z = ((r21 - r12) / s, 0.25 * s,
                      (r01 + r10) / s, (r02 + r20) / s)
    elif r11 > r22:
        s = math.sqrt(1.0 + r11 - r00 - r22) * 2.0
        w, x, y, z = ((r02 - r20) / s, (r01 + r10) / s,
                      0.25 * s, (r12 + r21) / s)
    else:
        s = math.sqrt(1.0 + r22 - r00 - r11) * 2.0
        w, x, y, z = ((r10 - r01) / s, (r02 + r20) / s,
                      (r12 + r21) / s, 0.25 * s)
    return loc, (w, x, y, z)


def _twitch_value(p: float, amp: float) -> float:
    """The 3-key twitch pulse: knots (0, 0), (0.2, +amp), (0.4, -amp),
    (0.6, 0), held 0 to the cycle end."""
    knots = ((0.0, 0.0), (0.2, amp), (0.4, -amp), (0.6, 0.0))
    if p <= 0.0 or p >= 0.6:
        return 0.0
    for (p0, v0), (p1, v1) in zip(knots, knots[1:]):
        if p0 <= p <= p1:
            if p1 == p0:
                return v1
            return v0 + (v1 - v0) * (p - p0) / (p1 - p0)
    return 0.0


def eval_rot_delta(d: RotDelta, p: float):
    """One rotation delta at cycle phase p -> a quaternion (or None
    for "amp", which needs the base rotation -- see apply_modifiers)."""
    if d.kind == "osc":
        ang = d.amp_deg * math.sin(2.0 * math.pi * (d.cycles * p + d.turn))
        return quat_axis_angle(d.axis, ang)
    if d.kind == "bias":
        return quat_axis_angle(d.axis, d.amp_deg)
    if d.kind == "twitch":
        return quat_axis_angle(d.axis,
                               _twitch_value(p, d.amp_deg))
    return None                      # "amp": handled by apply_modifiers


def eval_loc_delta(d: LocDelta, p: float):
    """One location delta at cycle phase p -> the metre OFFSET on the
    named axis (or None for "amp", which needs the base location --
    see apply_modifiers). The eval_rot_delta twin."""
    if d.kind == "osc":
        return d.amp_m * math.sin(2.0 * math.pi * (d.cycles * p + d.turn))
    if d.kind == "bias":
        return d.amp_m
    if d.kind == "twitch":
        return _twitch_value(p, d.amp_m)
    return None                      # "amp": handled by apply_modifiers


def apply_modifiers(table: dict, names, p: float) -> dict:
    """Apply a modifier stack to a pose table IN PLACE (and return it).

    table: {bone: (loc, quat)} -- the plain-tuple pose (the ual_bake
    _record_table shape, tuple-ized; build one under system python
    with decompose()); p: gait cycle phase in [0, 1). RotDelta
    stacks: "osc"/"bias"/"twitch" PRE-multiply the bone quaternion
    (bone-local axis rotation); "amp" scales the quaternion's
    deviation from IDENTITY (the rest pose -- the base clips are
    authored from rest, so q itself is the deviation) by the
    amplitude. LocDelta stacks do the SAME law on the location
    triple: osc/bias/twitch ADD on the named axis, "amp" scales the
    whole triple. Bones absent from the table are skipped (missing
    bones must not fail the compose); an unknown stack NAME raises
    ValueError listing the registered names (a bare KeyError would
    hide the vocabulary). Stack order is significant:
    the LATER name in the stack is the OUTERMOST rotation.
    """
    for nm in names:
        if nm not in GAIT_MODIFIERS:
            known = ", ".join(sorted(GAIT_MODIFIERS)) or "(none)"
            raise ValueError(
                f"apply_modifiers: unknown stack name {nm!r} "
                f"(registered: {known})")
        for d in GAIT_MODIFIERS[nm]:
            ent = table.get(d.bone)
            if ent is None:
                continue
            loc, q = ent
            if isinstance(d, LocDelta):
                if d.kind == "amp":
                    table[d.bone] = (
                        tuple(v * d.amp_m for v in loc), q)
                else:
                    off = eval_loc_delta(d, p)
                    if off is not None:
                        nl = list(loc)
                        nl[_AXIS_IDX[d.axis]] += off
                        table[d.bone] = (tuple(nl), q)
            elif d.kind == "amp":
                table[d.bone] = (loc, quat_pow(q, d.amp_deg))
            else:
                dq = eval_rot_delta(d, p)
                if dq is not None:
                    table[d.bone] = (loc, quat_mul(dq, q))
    return table


def canonicalize_quats(rows: dict) -> dict:
    """Quaternion sign canonicalization across frames (the ual_bake
    law: dot < 0 -> negate) -- prevents interpolation flips between
    adjacent keys. rows: {frame: {bone: (loc, quat)}} IN PLACE; the
    quats are plain (w, x, y, z) 4-tuples here."""
    prev = {}
    for f in sorted(rows):
        for bone, ent in rows[f].items():
            loc, q = ent
            pq = prev.get(bone)
            if pq is not None and (pq[0] * q[0] + pq[1] * q[1]
                                   + pq[2] * q[2] + pq[3] * q[3]) < 0.0:
                q = (-q[0], -q[1], -q[2], -q[3])
                rows[f][bone] = (loc, q)
            prev[bone] = rows[f][bone][1]
    return rows
