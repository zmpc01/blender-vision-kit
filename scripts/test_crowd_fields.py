#!/usr/bin/env python3
"""test_crowd_fields.py -- kit crowd_fields engine tests (T2 core).

Plain python3, no bpy. Run:
    python3 /home/z/blender-agent-kit/scripts/test_crowd_fields.py
Exit 0 = all green (fail-closed).
"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from crowd_fields import (  # noqa: E402
    FieldSpec, evaluate_fields, dominant_attractor,
    ramp_env, decay_env, event_env, relax,
    advance_phase, playback_rate,
)

FAILS = []


def check(name, cond, detail=""):
    if cond:
        print(f"  PASS {name}")
    else:
        print(f"  FAIL {name} {detail}")
        FAILS.append(name)


print("== 1. empty table no-op ==")
fx, fy, discs = evaluate_fields([0.0, 1.0], [0.0, 0.0], 1.0, [])
check("zeros", np.all(fx == 0) and np.all(fy == 0) and discs == [])

print("== 2. attract math (smooth falloff) ==")
f = FieldSpec(name="A", kind="attract", radius=10.0, strength=3.0,
              center=(10.0, 0.0))
px = np.array([0.0, 5.0, 9.9, 20.1])
py = np.zeros(4)
fx, fy, discs = evaluate_fields(px, py, 0.0, [f])
# at d=5, R=10: g = 3*(1-0.25)^2 = 1.6875 toward +x
check("falloff value", abs(fx[1] - 3.0 * (1 - 0.25) ** 2) < 1e-9,
      f"got {fx[1]}")
check("near center ~full", abs(fx[2] - 3.0 * (1 - 0.01 ** 2) ** 2) < 1e-6,
      f"got {fx[2]}")
check("outside skip", fx[3] == 0.0)

print("== 3. repel sign + linear falloff ==")
f = FieldSpec(name="R", kind="repel", radius=4.0, strength=-2.0,
              center=(0.0, 0.0), falloff="linear")
fx, fy, _ = evaluate_fields(np.array([1.0]), np.array([0.0]), 0.0, [f])
# u points toward centre (-x); s<0 flips it: force is +x (AWAY)
check("repel away", fx[0] > 0, f"got {fx[0]}")
check("linear value", abs(fx[0] - 1.5) < 1e-9, f"got {fx[0]}")

print("== 4. strength_fn envelope (REPLACES static strength) ==")
f = FieldSpec(name="J", kind="attract", radius=5.0, strength=99.0,
              falloff="linear", center=(0.0, 0.0),
              strength_fn=ramp_env(1.0, 2.0, post=3.0))
fx0, _, _ = evaluate_fields(np.array([2.5]), np.array([0.0]), 0.5, [f])
fx1, _, _ = evaluate_fields(np.array([2.5]), np.array([0.0]), 1.5, [f])
fx2, _, _ = evaluate_fields(np.array([2.5]), np.array([0.0]), 3.0, [f])
check("pre-ramp 0", fx0[0] == 0.0)
check("mid-ramp half", abs(fx1[0] + 0.75) < 1e-9, f"got {fx1[0]}")
check("post-ramp full", abs(fx2[0] + 1.5) < 1e-9, f"got {fx2[0]}")

print("== 5. t_active gating + obstacle discs ==")
f = FieldSpec(name="O", kind="obstacle", radius=1.5, strength=0.0,
              center=(2.0, 2.0), t_active=(1.0, 2.0))
fx, fy, discs = evaluate_fields([2.0], [2.0], 0.5, [f])
check("inactive no disc", discs == [])
fx, fy, discs = evaluate_fields([2.0], [2.0], 1.5, [f])
check("active disc", discs == [(2.0, 2.0, 1.5)])
check("obstacle no force", fx[0] == 0.0)
fm = FieldSpec(name="M", kind="attract", radius=8.0, strength=1.0,
               center=(0.0, 0.0), merge_obstacle=True)
_, _, discs = evaluate_fields([1.0], [0.0], 0.0, [fm])
check("merge disc", (0.0, 0.0, 8.0) in discs)

print("== 6. dominant_attractor ==")
fa = FieldSpec(name="a", kind="attract", radius=50.0, strength=1.0,
               center=(10.0, 0.0), t_active=(0.0, 5.0))
fb = FieldSpec(name="b", kind="attract", radius=50.0, strength=3.0,
               center=(0.0, 10.0), t_active=(5.0, 45.0))
d, idx = dominant_attractor(np.array([0.0]), np.array([0.0]), 2.0, [fa, fb])
check("window a", idx == 0 and abs(d[0] - 10.0) < 1e-9)
d, idx = dominant_attractor(np.array([0.0]), np.array([0.0]), 7.0, [fa, fb])
check("window b", idx == 1 and abs(d[0] - 10.0) < 1e-9)
d, idx = dominant_attractor(np.array([0.0]), np.array([0.0]), 50.0, [fa, fb])
check("none active", idx == -1 and np.isinf(d[0]))

print("== 7. relax: overlap resolution ==")
pos = np.array([[0.0, 0.0], [0.5, 0.0]])     # overlap 0.5 with r=0.5
radii = np.array([0.5, 0.5])
relax(pos, radii, iters=3)
d = float(np.hypot(*(pos[1] - pos[0])))
check("separated", d >= 1.0 - 1e-6, f"d={d}")
# symmetry: equal push both ways
check("symmetric", abs(pos[0, 0] + pos[1, 0] - 0.5) < 1e-6,
      f"com={pos[0, 0] + pos[1, 0]}")

print("== 8. relax: static disc infinite mass ==")
pos = np.array([[0.0, 0.0], [3.0, 0.0]])
radii = np.array([0.5, 0.5])
relax(pos, radii, iters=3, discs=[(0.0, 0.0, 1.0)])
d = float(np.hypot(*(pos[0] - np.array([0.0, 0.0]))))
check("pushed out of disc", d >= 1.5 - 1e-6, f"d={d}")

print("== 9. relax: determinism (same input -> same output) ==")
rng = np.random.default_rng(7)
pos_a = rng.uniform(-5, 5, (60, 2))
pos_b = pos_a.copy()
radii = np.full(60, 0.45)
relax(pos_a, radii, iters=3)
relax(pos_b, radii, iters=3)
check("bit-identical", np.array_equal(pos_a, pos_b))

print("== 10. no-penetration residual on a packed cluster ==")
rng = np.random.default_rng(11)
pos = rng.uniform(-2, 2, (40, 2))
radii = np.full(40, 0.45)
for _ in range(30):
    relax(pos, radii, iters=6)
dx = pos[:, None, 0] - pos[None, :, 0]
dy = pos[:, None, 1] - pos[None, :, 1]
dist = np.hypot(dx, dy) + np.eye(40) * 9.9
worst = float((radii[:, None] + radii[None, :] - dist).max())
check("residual small", worst <= 0.02, f"worst={worst:.5f}")

print("== 11. phase law ==")
check("advance", abs(advance_phase(0.9, 0.3, 1.0) - 0.2) < 1e-12)
check("zero stride safe", advance_phase(0.5, 1.0, 0.0) == 0.5)
check("rate clamp lo", playback_rate(0.2, 1.0) == 0.5)
check("rate clamp hi", playback_rate(9.0, 1.0) == 2.0)
check("rate nominal", playback_rate(1.0, 1.0) == 1.0)

print("== 12. envelopes ==")
e = decay_env(2.0, 0.5)
check("decay pre", e(1.9) == 0.0)
check("decay half", abs(e(2.5) - 0.5) < 1e-9)
e = event_env(1.0, 1.2)
check("pulse off", e(0.9) == 0.0)
check("pulse on", e(1.1) == 1.0)
check("pulse decay", 0.0 < e(1.35) < 1.0)

print("== 13. relax: coincident pair separates (s28-a4 P2 pin) ==")
# EXACT coincidence used to be a permanent deadlock: u = d/max(d,1e-9)
# is the ZERO vector at d == 0 -> no push, ever.
pos = np.array([[1.0, 2.0], [1.0, 2.0]])
radii = np.array([0.5, 0.5])
relax(pos, radii, iters=3)
d = float(np.hypot(*(pos[1] - pos[0])))
check("coincident pair separates", d >= 1.0 - 1e-6, f"d={d}")
pos2 = np.array([[1.0, 2.0], [1.0, 2.0]])
relax(pos2, radii, iters=3)
check("coincident fallback deterministic (i<j keyed)",
      np.array_equal(pos, pos2))
pos3 = np.zeros((3, 2))                    # a coincident clump
relax(pos3, np.full(3, 0.4), iters=6)
d3 = min(float(np.hypot(*(pos3[b] - pos3[a])))
         for a, b in ((0, 1), (0, 2), (1, 2)))
check("coincident clump separates pairwise (spread fallbacks)",
      d3 >= 0.7, f"min d={d3}")

print("== 14. relax: pair-set equivalence vs brute force (300 trials) ==")
# The spatial-hash pair set must be EXACTLY the brute-force i<j overlap
# set (the s28-a4 audit's 300-trial exact-match verification, frozen):
# any missing/spurious/duplicated pair changes the accumulated push.
# The reference mirrors the kit's accumulation SEMANTICS exactly: the
# per-iter push is accumulated with two np.add.at scatters (all i-side
# terms in lexsorted pair order, then all j-side terms), so the sums
# are bit-comparable -- a pair-set defect is NOT a rounding artifact,
# it changes which terms exist at all. Negative coords included (the
# kx*2^32+ky key must stay collision-free for negative cells).
def _brute_one_iter(pos, radii, eps):
    n = len(pos)
    push = np.zeros_like(pos)
    terms_i, terms_j = [], []
    for i in range(n):                      # i<j, lexicographic
        for j in range(i + 1, n):
            dx = pos[j, 0] - pos[i, 0]
            dy = pos[j, 1] - pos[i, 1]
            dist = float(np.hypot(dx, dy))   # np.hypot: math.hypot
            #                                 differs by 1 ulp on ~0.6%
            #                                 of inputs -- the kit
            #                                 vectorizes with np.hypot
            overlap = (radii[i] + radii[j]) - dist
            if overlap <= 0.0:
                continue
            if dist < 1e-9:                 # the same fallback law
                th = (math.pi / 32.0) * ((i * 31 + j * 17) % 64)
                u = float(np.cos(th))
                v = float(np.sin(th))
            else:
                u = dx / max(dist, 1e-9)
                v = dy / max(dist, 1e-9)
            mag = (overlap / 2.0) + eps
            terms_i.append((i, (-u * mag, -v * mag)))
            terms_j.append((j, (u * mag, v * mag)))
    for idx, (vx, vy) in terms_i:
        push[idx, 0] += vx
        push[idx, 1] += vy
    for idx, (vx, vy) in terms_j:
        push[idx, 0] += vx
        push[idx, 1] += vy
    return pos + push

rng = np.random.default_rng(2828)
bad = 0
for _trial in range(300):
    n = int(rng.integers(6, 15))
    p0 = rng.uniform(-3.0, 3.0, (n, 2))
    rr = rng.uniform(0.3, 0.6, n)
    a = p0.copy()
    relax(a, rr, iters=1)
    if not np.array_equal(a, _brute_one_iter(p0, rr, 1e-4)):
        bad += 1
check("300 trials: relax(1 iter) == brute-force pair set (bit-identical)",
      bad == 0, f"{bad} mismatched trials")

print("== 15. FieldSpec.t_active kit default is unbounded (s28-a4 P3a) ==")
f = FieldSpec(name="K", kind="attract", radius=10.0, strength=2.0,
              center=(5.0, 0.0))            # NO explicit window
check("default t_active == (0.0, inf)",
      f.t_active == (0.0, math.inf))
fx, fy, _ = evaluate_fields(np.array([0.0]), np.array([0.0]), 200.0, [f])
check("no explicit window -> still active past t=45", fx[0] > 0.0,
      f"fx={fx[0]}")

print("== 16. event_env release kwargs + strength_repr fail-closed ==")
e = event_env(1.0, 1.2, release_half_life=0.5, tail=1.0)
check("custom tail extends the pulse", e(2.1) > 0.0)
check("custom tail still bounded", e(2.3) == 0.0)
check("custom release half-life is slower (0.5 s -> ~0.29 at +0.15 s)",
      abs(e(1.35) - math.exp(-math.log(2.0) * 0.15 / 0.5)) < 1e-12)
e2 = event_env(1.0, 1.2)
check("default release half-life unchanged",
      abs(e2(1.35) - 0.5) < 1e-9)
check("default-call qualname byte-stable (hash law)",
      e2.__qualname__ == "event_env(1,1.2)")
check("kwarg qualname carries the params (params_sha law)",
      e.__qualname__ == "event_env(1,1.2,rl=0.5,tail=1)")
f_l = FieldSpec(name="L", kind="repel", radius=1.0, strength=-1.0,
                center=(0.0, 0.0), strength_fn=lambda t: -1.0)
try:
    f_l.strength_repr()
    check("anonymous strength_fn RAISES (fail-closed, s28-a4 P3d)",
          False)
except ValueError:
    check("anonymous strength_fn RAISES (fail-closed, s28-a4 P3d)",
          True)
check("stamped envelope still hashes as fn:<qualname>",
      FieldSpec(name="S", kind="repel", radius=1.0, strength=-1.0,
                center=(0.0, 0.0),
                strength_fn=decay_env(0.5, 1.5)).strength_repr()
      == "fn:decay_env(0.5,1.5)")

print()
if FAILS:
    print(f"FAILED: {len(FAILS)} -> {FAILS}")
    sys.exit(1)
print("ALL GREEN")
