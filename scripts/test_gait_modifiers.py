#!/usr/bin/env python3
"""test_gait_modifiers.py -- kit gait-modifier engine tests.

Plain python3, no bpy (the layering law: the engine imports clean
under system python; nothing here may pull bpy or mathutils). Run:
    python3 /home/z/blender-agent-kit/scripts/test_gait_modifiers.py
    (the previz twin /home/z/blender-escape-previz/scripts/
    test_gait_modifiers.py is a BYTE-IDENTICAL copy -- keep it in
    sync with cp + cmp; section 10 pins the module pair)
Exit 0 = all green (fail-closed).

Sections:
  1. quat_mul   Hamilton product (identity neutral, i*j=k,
                associativity)
  2. quat_axis_angle / quat_pow (k=0/-1/180deg, sign-flip
                invariance, the fail-closed guards)
  3. quat_slerp (exact endpoints, shortest path, arc midpoint,
                parallel + antiparallel degenerate)
  4. decompose  (pure 4x4 -> (loc, quat); all four Shepperd
                branches vs independently built matrices)
  5. the delta kinds (eval_rot_delta + eval_loc_delta twins)
  6. apply_modifiers on a synthetic pose table (absent-bone skip,
                bone-local PRE-multiply, whole-quat amp, loc laws,
                additive composition ORDER, determinism, unknown
                stack name)
  7. the registration API (register / duplicate / bad kind / bad
                axis / non-finite amp AND cycles/turn / non-iterable
                table / atomicity)
  8. validate_modifiers (findings style; the shipped table clean)
  9. canonicalize_quats + the layering law
 10. copy-sync pin (the previz sibling gait_modifiers.py must be
                byte-identical when present; silent skip on
                standalone kit checkouts)
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gait_modifiers import (  # noqa: E402
    RotDelta, LocDelta, VALID_KINDS, VALID_AXES,
    GAIT_MODIFIERS, register_modifiers, validate_modifiers,
    quat_mul, quat_axis_angle, quat_pow, quat_slerp, decompose,
    canonicalize_quats, eval_rot_delta, eval_loc_delta,
    apply_modifiers,
)

FAILS = []
IDENT = (1.0, 0.0, 0.0, 0.0)


def check(name, cond, detail=""):
    if cond:
        print(f"  PASS {name}")
    else:
        print(f"  FAIL {name} {detail}")
        FAILS.append(name)


def close(a, b, tol=1e-12):
    return all(abs(v - w) <= tol for v, w in zip(a, b)) \
        and len(a) == len(b)


def canon(q):
    """Sign-canonical view (q and -q are the same rotation)."""
    return q if q[0] >= 0.0 else tuple(-v for v in q)


def mat_of(loc, q):
    """Row-major 4x4 from (loc, quat) -- the STANDARD conversion
    formula, written out independently of the engine so decompose is
    tested against a second derivation (not its own inverse)."""
    w, x, y, z = q
    return (
        (1 - 2 * (y * y + z * z), 2 * (x * y - w * z),
         2 * (x * z + w * y), loc[0]),
        (2 * (x * y + w * z), 1 - 2 * (x * x + z * z),
         2 * (y * z - w * x), loc[1]),
        (2 * (x * z - w * y), 2 * (y * z + w * x),
         1 - 2 * (x * x + y * y), loc[2]),
        (0.0, 0.0, 0.0, 1.0),
    )


def rodrigues(axis, deg):
    """Rotation matrix via Rodrigues' formula (a THIRD independent
    derivation for one compound case)."""
    n = math.sqrt(sum(v * v for v in axis))
    kx, ky, kz = (v / n for v in axis)
    th = math.radians(deg)
    c, s = math.cos(th), math.sin(th)
    return (
        (c + kx * kx * (1 - c), kx * ky * (1 - c) - kz * s,
         kx * kz * (1 - c) + ky * s, 0.0),
        (ky * kx * (1 - c) + kz * s, c + ky * ky * (1 - c),
         ky * kz * (1 - c) - kx * s, 0.0),
        (kz * kx * (1 - c) - ky * s, kz * ky * (1 - c) + kx * s,
         c + kz * kz * (1 - c), 0.0),
        (0.0, 0.0, 0.0, 1.0),
    )


print("== 1. quat_mul: the Hamilton product ==")
qi, qj, qk = (0.0, 1.0, 0.0, 0.0), (0.0, 0.0, 1.0, 0.0), \
             (0.0, 0.0, 0.0, 1.0)
check("identity neutral (both sides)",
      close(quat_mul(IDENT, qi), qi) and close(quat_mul(qi, IDENT), qi))
check("i*j = k (the Hamilton law)", close(quat_mul(qi, qj), qk))
check("j*i = -k (anticommute witness)",
      close(quat_mul(qj, qi), (0.0, 0.0, 0.0, -1.0)))
check("associative on (i*j)*k == i*(j*k)",
      close(quat_mul(quat_mul(qi, qj), qk), quat_mul(qi, quat_mul(qj, qk))))

print("== 2. quat_axis_angle + quat_pow ==")
z90 = quat_axis_angle("z", 90.0)
check("axis_angle: 90deg z components + unit norm",
      abs(z90[0] - math.cos(math.pi / 4)) < 1e-12
      and abs(z90[3] - math.sin(math.pi / 4)) < 1e-12
      and abs(sum(v * v for v in z90) - 1.0) < 1e-12)
check("axis_angle: 0deg -> identity on every axis",
      all(quat_axis_angle(ax, 0.0) == IDENT for ax in "xyz"))
qq = quat_axis_angle("x", 37.0)
half = quat_pow(qq, 0.5)
check("quat_pow: ^0 identity, ^1 verbatim, (^0.5)^2 == q",
      quat_pow(qq, 0.0) == IDENT and close(quat_pow(qq, 1.0), qq)
      and close(quat_mul(half, half), qq))
check("quat_pow: k=-1 is the INVERSE (q * q^-1 == identity)",
      close(quat_mul(qq, quat_pow(qq, -1.0)), IDENT, 1e-12))
q180a = quat_pow(quat_axis_angle("x", 90.0), 2.0)
q180b = quat_axis_angle("x", 180.0)
check("quat_pow: 90deg ^2 == the 180deg quaternion (angle scaling)",
      close(q180a, q180b), f"{q180a} vs {q180b}")
check("quat_pow: sign-flip invariance (-q powers to the SAME result, "
      "w>0 and w<0 inputs)",
      quat_pow(tuple(-v for v in qq), 0.3) == quat_pow(qq, 0.3)
      and quat_pow(tuple(-v for v in quat_axis_angle("x", 200.0)), 0.3)
      == quat_pow(quat_axis_angle("x", 200.0), 0.3))
try:
    quat_pow((0.0, 0.0, 0.0, 0.0), 1.0)
    zero_raises = False
except ValueError:
    zero_raises = True
check("quat_pow RAISES on a zero-norm quaternion (fail-closed)",
      zero_raises)
q_nu = (2.0, 0.5, 0.0, 0.0)
nrm = math.sqrt(4.25)
check("quat_pow normalizes a non-unit input",
      quat_pow(q_nu, 1.0) == (2.0 / nrm, 0.5 / nrm, 0.0, 0.0))

print("== 3. quat_slerp: endpoints, shortest path, degenerates ==")
a = quat_axis_angle("z", 30.0)
b = quat_axis_angle("z", 60.0)
check("slerp endpoints EXACT (t=0 -> a, t=1 -> b)",
      quat_slerp(a, b, 0.0) == a and quat_slerp(a, b, 1.0) == b)
check("slerp midpoint on the arc (z30/z60 -> z45)",
      close(quat_slerp(a, b, 0.5), quat_axis_angle("z", 45.0), 1e-12))
check("shortest path: slerp(a, -b, t) == slerp(a, b, t) bit-identical",
      quat_slerp(a, tuple(-v for v in b), 0.37)
      == quat_slerp(a, b, 0.37))
c = quat_axis_angle("y", 23.0)
d = quat_axis_angle("x", -41.0)
check("shortest path on a compound pair too",
      quat_slerp(c, tuple(-v for v in d), 0.61)
      == quat_slerp(c, d, 0.61))
check("parallel degenerate: slerp(q, q, t) == q (nlerp branch, no "
      "div-by-sin(0))",
      close(quat_slerp(c, c, 0.37), c, 1e-15))
check("antiparallel degenerate: slerp(q, -q, t) == q",
      close(quat_slerp(c, tuple(-v for v in c), 0.3), c, 1e-15))
mid = quat_slerp(a, b, 0.5)
check("slerp output stays on the unit sphere",
      abs(sum(v * v for v in mid) - 1.0) < 1e-12)

print("== 4. decompose: pure 4x4 -> (loc, quat) ==")
loc0, q0 = (0.0, 0.0, 0.0), IDENT
check("identity matrix -> zero loc, identity quat",
      decompose(mat_of(loc0, q0)) == (loc0, IDENT))
cases = [
    ("tr>0 branch (compound small rotation)",
     (0.11, -0.07, 0.43), quat_mul(quat_axis_angle("x", 20.0),
                                   quat_mul(quat_axis_angle("y", 30.0),
                                            quat_axis_angle("z", 10.0)))),
    ("r00-dominant branch (x 170deg)",
     (1.5, 0.0, -2.0), quat_axis_angle("x", 170.0)),
    ("r11-dominant branch (y 170deg)",
     (0.0, 0.25, 0.0), quat_axis_angle("y", 170.0)),
    ("r22-dominant branch (z 170deg)",
     (-0.4, 0.9, 0.0), quat_axis_angle("z", 170.0)),
    ("180deg exact (w == 0)",
     (0.0, 0.0, 0.0), quat_axis_angle("x", 180.0)),
]
for why, loc, q in cases:
    got_loc, got_q = decompose(mat_of(loc, q))
    check(f"decompose round-trip: {why}",
          close(got_loc, loc) and close(canon(got_q), canon(q)),
          f"{got_q} vs {q}")
# the THIRD derivation: Rodrigues on an arbitrary compound axis
axs = (0.36, 0.48, 0.8)
th = math.radians(113.0)
q_rod = (math.cos(th / 2.0),
         axs[0] / math.sqrt(sum(v * v for v in axs)) * math.sin(th / 2.0),
         axs[1] / math.sqrt(sum(v * v for v in axs)) * math.sin(th / 2.0),
         axs[2] / math.sqrt(sum(v * v for v in axs)) * math.sin(th / 2.0))
rl, rq = decompose(rodrigues(axs, 113.0))
check("decompose vs Rodrigues' formula (arbitrary axis, 113deg)",
      close(rq, q_rod) or close(canon(rq), canon(q_rod)), f"{rq}")

print("== 5. the delta kinds (eval_rot_delta / eval_loc_delta) ==")
wob = RotDelta("DEF-head", "z", "osc", 12.0, 1.0, 0.0)
tw = RotDelta("DEF-head", "y", "twitch", 10.0)
dr = RotDelta("DEF-shoulder.L", "z", "bias", 8.0)
am = RotDelta("DEF-thigh.R", "x", "amp", 0.55)
check("osc peaks at p=.25/.75 (sin phase), zero at p=0",
      abs(eval_rot_delta(wob, 0.25)[3]
          - math.sin(math.radians(12.0) / 2)) < 1e-12
      and abs(eval_rot_delta(wob, 0.75)[3]
              + math.sin(math.radians(12.0) / 2)) < 1e-12
      and eval_rot_delta(wob, 0.0) == IDENT)
check("osc cycles/turn: half-cycle bob peaks at p=.5 for cycles=0.5",
      abs(eval_rot_delta(RotDelta("DEF-head", "x", "osc", 3.0, 0.5, 0.0),
                         0.5)[1] - math.sin(math.radians(3.0) / 2)) < 1e-12)
check("bias constant at every p",
      all(eval_rot_delta(dr, p) == quat_axis_angle("z", 8.0)
          for p in (0.0, 0.3, 0.9)))
check("twitch 3-key knots (+amp @.2, -amp @.4, 0 at/after .6)",
      eval_rot_delta(tw, 0.2) == quat_axis_angle("y", 10.0)
      and eval_rot_delta(tw, 0.4) == quat_axis_angle("y", -10.0)
      and eval_rot_delta(tw, 0.0) == IDENT
      and eval_rot_delta(tw, 0.6) == IDENT
      and eval_rot_delta(tw, 0.8) == IDENT)
check("amp -> None (base-relative: needs the pose quaternion)",
      eval_rot_delta(am, 0.5) is None)
lo = LocDelta("DEF-hips", "y", "osc", 0.05, 1.0, 0.0)
lb = LocDelta("DEF-hips", "z", "bias", 0.02)
lt = LocDelta("DEF-hips", "x", "twitch", 0.03)
la = LocDelta("DEF-hips", "x", "amp", 1.5)
check("eval_loc_delta: the metre twin (osc peak, bias const, twitch "
      "knots, amp -> None)",
      abs(eval_loc_delta(lo, 0.25) - 0.05) < 1e-12
      and eval_loc_delta(lb, 0.7) == 0.02
      and eval_loc_delta(lt, 0.2) == 0.03
      and eval_loc_delta(lt, 0.4) == -0.03
      and eval_loc_delta(lt, 0.8) == 0.0
      and eval_loc_delta(la, 0.5) is None)

print("== 6. apply_modifiers on a synthetic pose table ==")
mock_pose = {
    "DEF-head": ((0.0, 0.0, 0.0), IDENT),
    "DEF-hips": ((0.10, -0.02, 0.0), quat_axis_angle("y", 8.0)),
    "DEF-upper_arm.L": ((0.1, 0.0, 0.0),
                        quat_axis_angle("x", 20.0)),
    "DEF-upper_arm.R": ((0.0, 0.1, 0.0),
                        quat_axis_angle("x", 20.0)),
}
out = apply_modifiers(dict(mock_pose), ("head_bob_drift",), 0.5)
check("kit default vocabulary applies (head_bob_drift osc @p=.5: "
      "half-cycle peak on x)",
      close(out["DEF-head"][1], quat_axis_angle("x", 3.0))
      and out["DEF-head"][0] == mock_pose["DEF-head"][0])
check("absent-bone skip: no KeyError, unlisted bones untouched",
      "DEF-spine" not in out
      and out["DEF-upper_arm.L"] == mock_pose["DEF-upper_arm.L"])
check("apply_modifiers returns the SAME table object (in-place law)",
      apply_modifiers(out, (), 0.0) is out)
out = apply_modifiers(dict(mock_pose), ("arm_swing_var",), 0.5)
check("arm_swing_var: whole-quaternion amp per side (0.85 / 1.15)",
      close(out["DEF-upper_arm.L"][1],
            quat_pow(mock_pose["DEF-upper_arm.L"][1], 0.85))
      and close(out["DEF-upper_arm.R"][1],
                quat_pow(mock_pose["DEF-upper_arm.R"][1], 1.15)))
# the additive composition ORDER: the later stack name is the
# OUTERMOST rotation; sequential single applies == the combined stack
register_modifiers(
    t_zbias=(RotDelta("DEF-head", "z", "bias", 30.0),),
    t_xosc=(RotDelta("DEF-head", "x", "osc", 20.0, 1.0, 0.0),),
    t_absent=(RotDelta("DEF-not-in-table", "z", "bias", 5.0),),
    t_loc_osc=(LocDelta("DEF-hips", "y", "osc", 0.05, 1.0, 0.0),),
    t_loc_bias=(LocDelta("DEF-hips", "z", "bias", 0.02),),
    t_loc_amp=(LocDelta("DEF-hips", "x", "amp", 1.5),),
    t_loc_twitch=(LocDelta("DEF-hips", "x", "twitch", 0.03),),
)
base_q = mock_pose["DEF-head"][1]
want_zx = quat_mul(quat_axis_angle("x", 20.0),
                   quat_mul(quat_axis_angle("z", 30.0), base_q))
want_xz = quat_mul(quat_axis_angle("z", 30.0),
                   quat_mul(quat_axis_angle("x", 20.0), base_q))
o1 = apply_modifiers(dict(mock_pose), ("t_zbias", "t_xosc"), 0.25)
o2 = apply_modifiers(dict(mock_pose), ("t_xosc", "t_zbias"), 0.25)
check("stack order law: (z, x) -> x OUTERmost (mul(dx, mul(dz, q)))",
      close(o1["DEF-head"][1], want_zx))
check("order is significant (reversed stack differs -- "
      "non-commutative witness)",
      not close(o2["DEF-head"][1], want_zx)
      and close(o2["DEF-head"][1], want_xz))
seq = dict(mock_pose)
apply_modifiers(seq, ("t_zbias",), 0.25)
apply_modifiers(seq, ("t_xosc",), 0.25)
check("sequential single applies == the combined stack (additive "
      "over the CURRENT pose)",
      close(seq["DEF-head"][1], want_zx))
o3 = apply_modifiers(dict(mock_pose), ("t_loc_osc", "t_loc_bias"), 0.25)
check("loc osc+bias ADD on their named axes (others untouched)",
      close(o3["DEF-hips"][0], (0.10, -0.02 + 0.05, 0.02))
      and o3["DEF-hips"][1] == mock_pose["DEF-hips"][1])
o4 = apply_modifiers(dict(mock_pose), ("t_loc_amp",), 0.5)
check("loc amp scales the WHOLE triple (axis documentary)",
      close(o4["DEF-hips"][0], (0.15, -0.03, 0.0)))
o5 = apply_modifiers(dict(mock_pose), ("t_loc_twitch",), 0.2)
check("loc twitch hits the +amp knot at p=.2",
      close(o5["DEF-hips"][0], (0.13, -0.02, 0.0)))
o6 = apply_modifiers(dict(mock_pose),
                     ("t_zbias", "t_loc_osc", "t_absent"), 0.25)
check("mixed stack: the rot delta (head) and the loc delta (hips) "
      "compose independently, absent bones still skipped",
      close(o6["DEF-head"][1], quat_axis_angle("z", 30.0))
      and close(o6["DEF-hips"][0], (0.10, 0.03, 0.0))
      and o6["DEF-hips"][1] == mock_pose["DEF-hips"][1]
      and "DEF-not-in-table" not in o6)
r1 = apply_modifiers(dict(mock_pose),
                     ("t_zbias", "t_xosc", "t_loc_osc", "arm_swing_var"),
                     0.25)
r2 = apply_modifiers(dict(mock_pose),
                     ("t_zbias", "t_xosc", "t_loc_osc", "arm_swing_var"),
                     0.25)
check("determinism pin: same table + same stack + same p -> "
      "IDENTICAL output (exact dict equality)",
      r1 == r2)
try:
    apply_modifiers(dict(mock_pose), ("no_such_stack",), 0.5)
    unknown_ok = False
except KeyError:
    unknown_ok = False          # the old bare-KeyError behaviour
except ValueError as e:
    unknown_ok = ("no_such_stack" in str(e)
                  and "t_zbias" in str(e)
                  and "head_bob_drift" in str(e))
check("apply_modifiers RAISES ValueError on an unknown stack name "
      "(listing the registered names, never a bare KeyError)",
      unknown_ok)

print("== 7. the registration API ==")
n_before = len(GAIT_MODIFIERS)
register_modifiers(t_reg=(RotDelta("DEF-neck", "z", "osc", 5.0),),
                   t_reg_bare=RotDelta("DEF-neck", "x", "bias", 2.0))
check("registered names land in the shared registry",
      "t_reg" in GAIT_MODIFIERS and "t_reg_bare" in GAIT_MODIFIERS
      and len(GAIT_MODIFIERS) == n_before + 2)
check("a bare delta registers as a one-entry tuple",
      GAIT_MODIFIERS["t_reg_bare"]
      == (RotDelta("DEF-neck", "x", "bias", 2.0),))
o7 = apply_modifiers({"DEF-neck": ((0.0, 0.0, 0.0), IDENT)},
                     ("t_reg",), 0.25)
check("apply_modifiers resolves registered scene names",
      close(o7["DEF-neck"][1], quat_axis_angle("z", 5.0)))
for name, kw, why in (
    ("t_reg", dict(t_reg=(RotDelta("DEF-neck", "z", "osc", 1.0),)),
     "duplicate name"),
    ("t_bad_kind", dict(t_bad_kind=(RotDelta("b", "x", "wobble", 5.0),)),
     "unknown kind"),
    ("t_bad_axis", dict(t_bad_axis=(RotDelta("b", "q", "osc", 5.0),)),
     "bad axis"),
    ("t_bad_axis_loc", dict(t_bad_axis_loc=(LocDelta("b", "w", "bias", 1.0),)),
     "bad axis (LocDelta)"),
    ("t_nonfinite", dict(t_nonfinite=(RotDelta("b", "x", "osc",
                                               float("nan")),)),
     "non-finite amp"),
    ("t_nan_cycles", dict(t_nan_cycles=(RotDelta(
        "b", "x", "osc", 5.0, float("nan"), 0.0),)),
     "NaN cycles"),
    ("t_inf_cycles", dict(t_inf_cycles=(LocDelta(
        "b", "x", "osc", 1.0, float("inf"), 0.0),)),
     "infinite cycles (LocDelta)"),
    ("t_nan_turn", dict(t_nan_turn=(RotDelta(
        "b", "z", "twitch", 5.0, 1.0, float("nan")),)),
     "NaN turn"),
    ("t_inf_turn", dict(t_inf_turn=(LocDelta(
        "b", "y", "osc", 1.0, 1.0, float("inf")),)),
     "infinite turn (LocDelta)"),
    ("t_notiter", dict(t_notiter=5), "non-iterable table (int)"),
    ("t_empty", dict(t_empty=()), "empty table"),
    ("t_notdelta", dict(t_notdelta=("nope",)), "non-delta entry"),
):
    try:
        register_modifiers(**kw)
        raised = False
    except ValueError:
        raised = True
    check(f"register_modifiers RAISES on {why}", raised)
try:
    register_modifiers()
    raised = False
except ValueError:
    raised = True
check("register_modifiers RAISES on no tables", raised)
try:
    register_modifiers(t_ok_two=(RotDelta("b", "x", "osc", 1.0),),
                       t_coll_two=(RotDelta("b", "q", "osc", 1.0),))
    atomic = False
except ValueError:
    atomic = True
check("ATOMIC: a failed multi-register inserts NOTHING (t_ok_two "
      "absent)", atomic and "t_ok_two" not in GAIT_MODIFIERS)
check("the failed register attempts left the registry size unchanged",
      len(GAIT_MODIFIERS) == n_before + 2)

print("== 8. validate_modifiers (the findings style) ==")
check("the shipped table + the test registrations are clean",
      validate_modifiers() == [])
bad = {
    "m_bad_kind": (RotDelta("b", "x", "wobble", 5.0),),
    "m_bad_axis": (RotDelta("b", "q", "osc", 5.0),),
    "m_nonfinite": (LocDelta("b", "x", "bias", float("inf")),),
    "m_empty": (),
    "m_notdelta": ("nope",),
}
f = validate_modifiers(bad)
check("a hand-built bad table yields one finding per law",
      len(f) == 5 and "modifier m_bad_kind: bad kind wobble" in f
      and "modifier m_bad_axis: bad axis q" in f
      and "modifier m_nonfinite: non-finite amp" in f
      and "modifier m_empty: empty table" in f
      and any("neither RotDelta nor LocDelta" in x for x in f),
      "; ".join(f))
bad2 = {
    "m_nan_cycles": (RotDelta("b", "x", "osc", 5.0, float("nan")),),
    "m_inf_turn": (LocDelta("b", "x", "osc", 1.0, 1.0,
                            float("inf")),),
    "m_notiter": 5,
}
f2 = validate_modifiers(bad2)
check("validate_modifiers flags non-finite cycles/turn (the "
      "NaN-poison gap) and a non-iterable table as findings, "
      "never a crash",
      len(f2) == 3
      and "modifier m_nan_cycles: non-finite cycles/turn" in f2
      and "modifier m_inf_turn: non-finite cycles/turn" in f2
      and "modifier m_notiter: table is not iterable (int)" in f2,
      "; ".join(f2))
check("VALID_KINDS / VALID_AXES are the declared vocabularies",
      VALID_KINDS == ("osc", "bias", "amp", "twitch")
      and VALID_AXES == ("x", "y", "z"))
check("the kit ships the generic funny-walk vocabulary "
      "(head-bob / arm-variance / lean / asymmetry)",
      set(GAIT_MODIFIERS) >= {"head_bob_drift", "arm_swing_var",
                              "lean_osc", "step_asym"}
      and GAIT_MODIFIERS["arm_swing_var"]
      == (RotDelta("DEF-upper_arm.L", "x", "amp", 0.85),
          RotDelta("DEF-upper_arm.R", "x", "amp", 1.15)))

print("== 9. canonicalize_quats + the layering law ==")
flip_rows = {0: {"DEF-head": ((0, 0, 0), (0.6, 0.8, 0.0, 0.0))},
             1: {"DEF-head": ((0, 0, 0), (-0.6, -0.8, 0.0, 0.0))},
             2: {"DEF-head": ((0, 0, 0), (0.6, 0.8, 0.0, 0.0))}}
canonicalize_quats(flip_rows)
check("canonicalize_quats: dot<0 -> negate (the anti-flip law), "
      "same-sign rows untouched",
      flip_rows[1]["DEF-head"][1] == (0.6, 0.8, 0.0, 0.0)
      and flip_rows[2]["DEF-head"][1] == (0.6, 0.8, 0.0, 0.0))
check("layering law: the whole suite ran with NO bpy in sys.modules "
      "(the engine imports clean under system python3)",
      "bpy" not in sys.modules and "mathutils" not in sys.modules)

print("== 10. copy-sync pin (kit/previz byte-identity) ==")


def _read_bytes(path):
    with open(path, "rb") as fh:
        return fh.read()


def _sibling_sync(sib_path):
    """None when the sibling checkout is absent (standalone kit --
    skip silently); True/False when it is present."""
    if not os.path.exists(sib_path):
        return None
    here = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "gait_modifiers.py")
    return _read_bytes(sib_path) == _read_bytes(here)


check("an ABSENT sibling skips silently (None, no raise -- "
      "standalone kit checkouts)",
      _sibling_sync("/nonexistent/scripts/gait_modifiers.py") is None)
PREVIZ_SIBLING = ("/home/z/blender-escape-previz/scripts/"
                  "gait_modifiers.py")
if os.path.exists(PREVIZ_SIBLING):
    check("copy-sync: the previz sibling gait_modifiers.py is "
          "BYTE-IDENTICAL to this checkout's (the crowd_fields.py "
          "law)",
          _sibling_sync(PREVIZ_SIBLING) is True)
else:
    print("  SKIP copy-sync pin (no previz sibling in this checkout)")

print()
if FAILS:
    print(f"FAILED: {len(FAILS)} -> {FAILS}")
    sys.exit(1)
print("ALL GREEN")
