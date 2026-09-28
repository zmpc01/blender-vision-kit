"""crowd_fields.py -- generalized influence-field + gait-phase engine.

KIT-LEVEL, SCENE-AGNOSTIC (session-26 generalization law: the user's
"influence spheres" and "funny walk pedestrians as generalized
modifier behaviors" live in the KIT, reusable by any project; the
zombie scene contributes only DATA -- its field table, its lanes,
its modifier specs).

Pure numpy, NO bpy (importable by headless sims, tests, exporters).

THREE PRIMITIVES:

1. SIGNED FIELDS (the influence-sphere primitive)
   Semantics adopted verbatim from abmsim (crowd survey): positive
   strength attracts, negative repels, 0 = obstacle-only,
   ``merge_obstacle`` merges the disc into the relax solver's static
   constraint set. ANIMATED attractors (``center_fn``) follow the
   iCrowds law: moving attractor = pursuit target, radius honoured
   as "what an empty's scale.x would be". Fields are DATA, never
   scene objects.

2. RELAX SOLVER (position-based personal space)
   iCrowds "personal space (min 0.5/1.0 m) + Relax Iterations
   (1-12)" re-expressed as a deterministic vectorized PBD pass:
   pair set from a spatial hash as a sorted (i, j) index array
   (i<j, lexicographic), per-iter pushes accumulated with
   np.add.at (order-independent), applied in one step. Static
   obstacle discs are infinite-mass: the AGENT is pushed fully out.

3. GAIT PHASE LAW (kills foot-slide by construction)
   phase = (phase + displacement / stride) % 1.0 -- driven by root
   DISPLACEMENT, never time; playback rate = clamp(speed/nominal,
   0.5, 2.0). Outside the clamp you switch clips, never skate.

Provenance: contracts only, re-derived from public docs of bgyss
Blender-Crowd (GPL, not vendored), abmsim (MIT), iCrowds (GPL,
product not vendored). Zero code copied.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Sequence

import numpy as np

__all__ = [
    "FieldSpec", "evaluate_fields", "dominant_attractor",
    "ramp_env", "decay_env", "event_env",
    "relax",
    "advance_phase", "playback_rate",
]


# ---------------------------------------------------------------------------
# 1. signed fields
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FieldSpec:
    """One signed influence field (the influence-sphere primitive).

    ``strength_fn`` (kit addition, session-26): optional temporal
    envelope over strength -- covers ramps (an attractor that powers
    up), decays (a transient repulsor), and event pulses. When set
    it REPLACES the static strength at evaluation time; canonical
    JSON serialization (params hashing) uses ``strength_repr``.
    """
    name: str                  # "Jeep.Tail", "Muzzle.S6", "Cam.S4b"
    kind: str                  # "attract" | "repel" | "obstacle"
    radius: float              # metres -- == review empty's scale.x
    strength: float            # desired-velocity m/s at field centre
    falloff: str = "smooth"    # (1-(d/R)^2)^2 ; or "linear"
    center: tuple[float, float] | None = None        # static, belt-local
    center_fn: Callable[[float], tuple[float, float]] | None = None
    t_active: tuple[float, float] = (0.0, math.inf)   # KIT default is
    #   UNBOUNDED (s28-a4 P3a): the old (0.0, 45.0) baked THIS scene's
    #   T_END into the scene-agnostic engine -- a 60 s project silently
    #   lost every field at t=45. A scene passes its own horizon
    #   explicitly (every row in crowd_v6/fields.py does).
    merge_obstacle: bool = False
    source: str = ""           # provenance ("jeep", "sfx:horn", ...)
    strength_fn: Callable[[float], float] | None = None

    def strength_at(self, t: float) -> float:
        """Current strength: the envelope if present, else static."""
        if self.strength_fn is not None:
            return float(self.strength_fn(t))
        return float(self.strength)

    def strength_repr(self) -> str:
        """Canonical, hashable strength description (params_sha law:
        a strength_fn that changes the sim MUST change the hash).

        FAIL-CLOSED (s28-a4 P3d): an ANONYMOUS strength_fn (a lambda,
        or any callable without a ``__qualname__``) has no stable
        identity -- every distinct anonymous envelope would hash as
        the same "fn:<lambda>" and a params_sha reuse check would
        silently miss the change. Raise instead of colliding; stamp a
        deterministic ``__qualname__`` to opt in (the ramp_env /
        decay_env / event_env builders below do this for you)."""
        if self.strength_fn is None:
            return f"const:{self.strength:g}"
        qn = getattr(self.strength_fn, "__qualname__", "") or ""
        if "<lambda>" in qn or qn.startswith("<"):
            raise ValueError(
                f"FieldSpec {self.name!r}: anonymous strength_fn is not "
                f"hashable (params_sha collision hole) -- stamp a "
                f"deterministic __qualname__ (see ramp_env/decay_env/"
                f"event_env) or use a static strength")
        return f"fn:{qn}"


def _center_of(f: FieldSpec, t: float) -> tuple[float, float]:
    if f.center is not None:
        return float(f.center[0]), float(f.center[1])
    if f.center_fn is not None:
        cx, cy = f.center_fn(t)
        return float(cx), float(cy)
    raise ValueError(
        f"FieldSpec {f.name!r}: neither center nor center_fn is set "
        f"(every field needs one)")


def evaluate_fields(px, py, t: float, fields: Sequence[FieldSpec]):
    """Vectorized field math, per tick.

    for each field k active at t:
        c   = center or center_fn(t)            # animated: jeep tail
        d   = ||c - p_i||                       (skip if d >= R_k)
        u   = (c - p_i) / max(d, 1e-6)          # unit toward centre
        g   = strength_k(t) * (1 - (d/R_k)**2)**2   # smooth falloff
                                                # "linear" = *(1-d/R)
        F_i += u * g                            # strength<0 => repels
    obstacle-only fields (strength 0): no F term, but their discs
    join the relax-solver static constraint set (merge_obstacle=True
    merges them into the same pass).

    px, py: (N,) float arrays of agent positions (sim-local, metres).
    Returns (fx, fy, obstacle_discs): (N,) accumulated desired-
    velocity contributions (m/s) + the list of (cx, cy, r) static
    constraints for relax().

    Empty table = the exact no-op (zeros, zeros, []) -- a tested
    property, not an accident.
    """
    px = np.asarray(px, dtype=np.float64)
    py = np.asarray(py, dtype=np.float64)
    fx = np.zeros_like(px)
    fy = np.zeros_like(py)
    discs = []
    for f in fields:
        t0, t1 = f.t_active
        if not (t0 <= t <= t1):
            continue
        cx, cy = _center_of(f, t)
        if f.kind == "obstacle" or f.merge_obstacle:
            discs.append((cx, cy, float(f.radius)))
        s = f.strength_at(t)
        if s == 0.0:
            continue                    # obstacle-only: no F term
        dx = cx - px
        dy = cy - py
        d = np.hypot(dx, dy)
        inside = d < f.radius           # skip if d >= R_k
        if not inside.any():
            continue
        u = dx / np.maximum(d, 1e-6)    # unit toward centre
        v = dy / np.maximum(d, 1e-6)
        if f.falloff == "linear":
            g = s * (1.0 - d / f.radius)
        else:                           # "smooth" (the default)
            q = d / f.radius
            g = s * (1.0 - q * q) ** 2
        fx = fx + np.where(inside, u * g, 0.0)
        fy = fy + np.where(inside, v * g, 0.0)
    return fx, fy, discs


def dominant_attractor(px, py, t: float, fields: Sequence[FieldSpec]):
    """Per-agent distance to the strongest ACTIVE attract field.

    The alert-transition predicate helper: ALERT iff
    d_i < eff_trigger_i (and the attractor is active). With disjoint
    activation windows (the common table shape) the argmax is
    trivial; the strength-at-t comparison keeps it honest once a
    table grows overlapping attractors.

    Returns (dist, idx): (N,) distances (np.inf where none is
    active) and the winning field INDEX (-1 when none).
    """
    px = np.asarray(px, dtype=np.float64)
    py = np.asarray(py, dtype=np.float64)
    best_d = np.full(px.shape, np.inf)
    best_idx = -1
    best_s = -np.inf
    for k, f in enumerate(fields):
        if f.kind != "attract":
            continue
        t0, t1 = f.t_active
        if not (t0 <= t <= t1):
            continue
        s = f.strength_at(t)
        if s <= 0.0:
            continue
        if s <= best_s:
            continue                    # ties: earlier field wins
        cx, cy = _center_of(f, t)
        d = np.hypot(cx - px, cy - py)
        best_d, best_idx, best_s = d, k, s
    return best_d, best_idx


# ---------------------------------------------------------------------------
# temporal envelopes (kit helpers; strength_fn builders)
# ---------------------------------------------------------------------------

def ramp_env(t_ramp0: float, t_ramp1: float, *,
             post: float = 1.0) -> Callable[[float], float]:
    """0 -> post linearly over [t_ramp0, t_ramp1], flat outside."""
    def env(t: float) -> float:
        if t <= t_ramp0:
            return 0.0
        if t >= t_ramp1:
            return float(post)
        return float(post) * (t - t_ramp0) / (t_ramp1 - t_ramp0)
    env.__qualname__ = f"ramp_env({t_ramp0:g},{t_ramp1:g},{post:g})"
    return env


def decay_env(t_event: float, half_life: float) -> Callable[[float], float]:
    """Exponential decay from 1.0 at t_event (0 before it)."""
    def env(t: float) -> float:
        if t <= t_event:
            return 0.0
        return math.exp(-math.log(2.0) * (t - t_event) / half_life)
    env.__qualname__ = f"decay_env({t_event:g},{half_life:g})"
    return env


def event_env(t_on: float, t_off: float, *,
              attack: float = 0.03,
              release_half_life: float = 0.15,
              tail: float = 0.4) -> Callable[[float], float]:
    """Bounded event pulse: fast attack from t_on, hold 1.0, release
    at t_off (muzzle strobes: the sfx burst window + decay).

    The release is an exponential with ``release_half_life`` (default
    0.15 s), exactly 0 past ``t_off + tail`` (default 0.4 s -- the
    bounded-impulse law). These were hardcoded scene numbers; they
    are kwargs now (s28-a4 P3b) with the same defaults, so existing
    pulses are bit-identical. The ``__qualname__`` stays
    "event_env(t_on,t_off)" for default calls (hash stability) and
    carries any non-default kwarg (the params_sha law)."""
    def env(t: float) -> float:
        if t < t_on or t > t_off + tail:
            return 0.0
        if t < t_on + attack:
            return (t - t_on) / attack
        if t <= t_off:
            return 1.0
        return math.exp(-math.log(2.0) * (t - t_off) / release_half_life)
    parts = [f"event_env({t_on:g},{t_off:g}"]
    if attack != 0.03:
        parts.append(f",atk={attack:g}")
    if release_half_life != 0.15:
        parts.append(f",rl={release_half_life:g}")
    if tail != 0.4:
        parts.append(f",tail={tail:g}")
    parts.append(")")
    env.__qualname__ = "".join(parts)
    return env


# ---------------------------------------------------------------------------
# 2. relax solver (deterministic vectorized PBD)
# ---------------------------------------------------------------------------

def relax(pos, radii, iters: int = 3, discs=(), *, cell: float = 2.0,
          eps: float = 1e-4) -> None:
    """In-place PBD pass (personal space + static obstacle discs).

    pos:   (N, 2) array, MODIFIED IN PLACE -- must be float64. A
           float64 ndarray is relaxed in place (asarray is a no-copy
           view); a float32 array or a nested list is COPIED by the
           dtype conversion and the caller's buffer is silently left
           untouched (s28-a4 P3c: pass
           ``np.asarray(pos, dtype=np.float64)`` first if in-place
           semantics are required -- the sim always does).
    radii: (N,) personal-space radii (metres).
    discs: sequence of (cx, cy, r) static constraints -- infinite
           mass: the AGENT is pushed fully out, the disc never moves.

    Pair set from a spatial-hash grid (cell size = max(2m, 2*max
    radius)) as a sorted (i, j) index array (i < j, lexicographic --
    deterministic). Degenerate COINCIDENT pairs (dist ~ 0, where the
    centre line has no direction) get an index-deterministic fallback
    direction keyed on the normalized i<j identity -- they MUST
    separate (the s28-a4 P2 deadlock: d/max(dist,1e-9) is the zero
    vector at dist == 0 and the pair never pushed). Per iter:
    per-pair push vectors along the centre line (overlap/2 + eps),
    accumulated with np.add.at scatter (order-INDEPENDENT -- same
    pair set + same pushes + float sum = same result every run),
    then applied in one step.

    iters is the quality knob (iCrowds relax-iterations, 1-12).
    """
    pos = np.asarray(pos, dtype=np.float64)
    radii = np.asarray(radii, dtype=np.float64)
    n = len(pos)
    if n == 0:
        return
    grid = max(cell, 2.0 * float(radii.max(initial=0.0)))

    # ---- pair set (spatial hash, lexicographic, deduped) ----
    # VECTORIZED grouped-join (session-26 perf fix: the Python bucket
    # loop measured ~1.0 ms/tick at N=129 vs the 0.4 ms budget). The
    # pair SET is bit-identical to the reference bucket builder: self
    # cells contribute i<j pairs, the 4 directional offsets (0,1),
    # (1,-1), (1,0), (1,1) visit each unordered cell-pair exactly
    # once, and the final lexsort pins the order (np.add.at is
    # order-independent regardless -- same set + same order = same
    # floats = same result; the fields-on determinism pins verify).
    keys = np.floor(pos / grid).astype(np.int64)
    kx, ky = keys[:, 0], keys[:, 1]
    _M = np.int64(1) << np.int64(32)
    key_a = kx * _M + ky                      # own cell id per agent

    def _join(key_left, key_right, *, upper_only):
        """All (i, j): key_left[i] == key_right[j], as index arrays.
        Grouped expansion: sort left, searchsorted the right values,
        repeat-run expand. upper_only keeps i < j only (the self-cell
        join is symmetric -- each unordered pair must appear ONCE,
        matching the reference builder)."""
        order = np.argsort(key_left, kind="stable")
        sorted_l = key_left[order]
        lo = np.searchsorted(sorted_l, key_right, side="left")
        hi = np.searchsorted(sorted_l, key_right, side="right")
        cnt = hi - lo
        if not cnt.any():
            return None
        j_idx = np.repeat(np.arange(n), cnt)
        # within-run offsets
        run_base = np.repeat(np.cumsum(cnt) - cnt, cnt)
        r = np.arange(cnt.sum()) - run_base
        i_idx = order[np.repeat(lo, cnt) + r]
        if upper_only:
            keep = i_idx < j_idx
            if not keep.any():
                return None
            i_idx, j_idx = i_idx[keep], j_idx[keep]
        return i_idx, j_idx

    pair_i, pair_j = [], []
    j0 = _join(key_a, key_a, upper_only=True)
    if j0 is not None:
        i0, j0v = j0
        pair_i.append(i0)
        pair_j.append(j0v)
    for ox, oy in ((0, 1), (1, -1), (1, 0), (1, 1)):
        key_shift = (kx + ox) * _M + (ky + oy)
        # pairs (a in cell c, b in cell c+o): match a's SHIFTED key
        # against b's OWN key
        jr = _join(key_shift, key_a, upper_only=False)
        if jr is not None:
            ar, br = jr
            pair_i.append(ar)
            pair_j.append(br)
    if pair_i:
        pi = np.concatenate(pair_i)
        pj = np.concatenate(pair_j)
        # normalize to i < j, lexsort for the deterministic order
        swap = pi > pj
        pi, pj = np.where(swap, pj, pi), np.where(swap, pi, pj)
        lex = np.lexsort((pj, pi))
        pi, pj = pi[lex], pj[lex]
        pairs = True
    else:
        pairs = False
    if not pairs and not discs:
        return

    for _ in range(max(1, int(iters))):
        push = np.zeros_like(pos)
        if pairs:
            d = pos[pj] - pos[pi]
            dist = np.hypot(d[:, 0], d[:, 1])
            overlap = (radii[pi] + radii[pj]) - dist
            hit = overlap > 0.0
            if hit.any():
                dh = d[hit]
                dist_h = dist[hit]
                # degenerate coincidence (dist < 1e-9): the centre
                # line has no direction -- d/max(dist,1e-9) collapses
                # to the ZERO vector at dist == 0 and the pair NEVER
                # separates (the s28-a4 P2 deadlock). Mirror of the
                # static-disc law below ("never a zero vector"),
                # index-deterministic: the fallback angle is keyed on
                # the normalized i<j pair identity (pi/pj are sorted
                # ONCE, before the iteration loop), so the same pair
                # takes the same direction every iteration and every
                # run, while distinct pairs spread over 64 angles (a
                # coincident clump does not lock into one axis).
                coinc = dist_h < 1e-9
                uv = dh / np.maximum(dist_h, 1e-9)[:, None]
                if coinc.any():
                    th = (math.pi / 32.0) * (
                        (pi[hit][coinc] * 31 + pj[hit][coinc] * 17) % 64)
                    uv[coinc] = np.stack([np.cos(th), np.sin(th)],
                                         axis=1)
                u = uv[:, 0]
                v = uv[:, 1]
                mag = (overlap[hit] / 2.0) + eps
                # i pushed toward j's opposite: push[i] -= u*mag
                np.add.at(push, pi[hit], np.stack(
                    [-u * mag, -v * mag], axis=1))
                np.add.at(push, pj[hit], np.stack(
                    [u * mag, v * mag], axis=1))
        # static discs: infinite mass, agent pushed fully out
        for (cx, cy, r) in discs:
            d = pos - np.array([cx, cy])
            dist = np.hypot(d[:, 0], d[:, 1])
            overlap = (r + radii) - dist
            hit = overlap > 0.0
            if not hit.any():
                continue
            # degenerate same-point: push along a fixed axis (never
            # a zero vector -- an agent exactly at a disc centre must
            # still be expelled)
            safe = np.maximum(dist, 1e-9)
            u = np.where((dist < 1e-9)[:, None],
                         np.array([1.0, 0.0]), d / safe[:, None])
            mag = overlap[hit] + eps
            np.add.at(push, np.nonzero(hit)[0], u[hit] * mag[:, None])
        pos += push


# ---------------------------------------------------------------------------
# 3. gait phase law
# ---------------------------------------------------------------------------

def advance_phase(phase, disp, stride):
    """phase = (phase + displacement / stride) % 1.0 -- driven by
    root DISPLACEMENT, never time (the foot-slide killer: skipping
    it for unevaluated agents would make feet slide; never skip)."""
    if stride <= 0.0:
        return float(phase)
    return float((phase + disp / stride) % 1.0)


def playback_rate(speed, nominal, *, lo: float = 0.5, hi: float = 2.0):
    """Clamped playback rate from world speed (bgyss clamp law)."""
    if nominal <= 0.0:
        return 1.0
    return float(np.clip(speed / nominal, lo, hi))
