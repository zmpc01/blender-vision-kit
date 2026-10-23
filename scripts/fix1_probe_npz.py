"""fix1_probe_npz.py -- numeric root-cause probe for the orientation +
teleport + animation-driver classes (the user's issues 1/2/3).

Pure numpy on a baked cache_v6.npz (no Blender):

    /home/z/.venv/bin/python3 scripts/fix1_probe_npz.py /tmp/crowdcache_tdawn/cache_v6.npz

Measures (per agent, per tick @12Hz):
  A. yaw-vs-motion angle error:  wrap(yaw[t] - atan2(dy,dx)) where
     (dx,dy) = pos[t+1]-pos[t] (visible movers only, speed > 0.35).
     A healthy bridge = median |err| < 10 deg.  A 90-deg spike = the
     convention bug; a uniform spread = chaos/wrap.
  B. +-pi wrap crossings between CONSECUTIVE KEY ticks (k%2==0, the
     bake2 key grid): raw |dyaw| > pi/2 between keys = the LINEAR-interp
     long-way spin class.
  C. teleport ticks: |dpos|*12 > 2*max_speed_const (per agent).
     Correlate with keepout windows when the contract rows are passed.
  D. animation-driver stats: clip channel distribution, phase advance
     rate, speed distribution (the humanoid rate law inputs).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np


def wrap_pi(a):
    return (a + np.pi) % (2.0 * np.pi) - np.pi


def main():
    npz_path = Path(sys.argv[1] if len(sys.argv) > 1 else
                    "/tmp/crowdcache_tdawn/cache_v6.npz")
    z = np.load(npz_path, allow_pickle=False)
    meta = {k: str(z[k]) for k in z.files if z[k].dtype.kind in "US"}
    print(f"== {npz_path.name} ==")
    for k in ("format", "engine", "dt", "n_ticks", "payload_sha256"):
        if k in meta:
            print(f"  {k}: {meta[k][:24]}")
    x = np.asarray(z["x"], dtype=np.float64)      # (T, N)
    y = np.asarray(z["y"], dtype=np.float64)
    yaw = np.asarray(z["yaw"], dtype=np.float64)
    speed = np.asarray(z["speed"], dtype=np.float64)
    clip = np.asarray(z["clip"])
    phase = np.asarray(z["phase"], dtype=np.float64)
    max_speed = np.asarray(z["max_speed"], dtype=np.float64)
    T, N = x.shape
    print(f"  shape: T={T} N={N}  agents")

    # ---- A. yaw vs motion direction (visible movers) ----------------
    dx = np.diff(x, axis=0)
    dy = np.diff(y, axis=0)
    vdir = np.arctan2(dy, dx)
    mv = np.hypot(dx, dy) * 12.0                   # m/s between ticks
    movers = mv > 0.35                             # the gate-21 floor
    err = np.abs(wrap_pi(yaw[:-1] - vdir))
    err_m = err[movers]
    if err_m.size:
        pct = np.percentile(err_m, [10, 50, 90])
        print(f"\n[A] yaw-vs-motion |err| deg (movers={err_m.size}): "
              f"p10={np.degrees(pct[0]):.1f} p50={np.degrees(pct[1]):.1f} "
              f"p90={np.degrees(pct[2]):.1f}")
        hist, edges = np.histogram(np.degrees(err_m),
                                   bins=[0, 10, 30, 60, 90, 120, 180])
        print("    bins 0-10/10-30/30-60/60-90/90-120/120-180:",
              (100 * hist / err_m.size).round(1), "%")
    else:
        print("\n[A] no movers above 0.35 m/s?!")

    # ---- B. wrap crossings on the KEY grid (every 2 ticks) ----------
    key_yaw = yaw[::2]                              # keys at k%2==0
    dkey = np.abs(wrap_pi(np.diff(key_yaw, axis=0)))
    spins = dkey > (np.pi / 2)
    n_spins = int(spins.sum())
    print(f"\n[B] key-grid |dyaw|>90deg events: {n_spins} "
          f"({100.0 * spins.mean():.2f}% of keyed intervals)")
    per_agent = spins.sum(axis=0)
    worst = np.argsort(per_agent)[-5:][::-1]
    print("    worst agents (spins):",
          [(int(i), int(per_agent[i])) for i in worst])

    # ---- C. teleport ticks -------------------------------------------
    tele = mv > (2.0 * max_speed[None, :])
    n_tele = int(tele.sum())
    print(f"\n[C] teleport ticks (|v| > 2*max_speed): {n_tele}")
    if n_tele:
        idx = np.argwhere(tele)
        ticks = idx[:, 0]
        agents = idx[:, 1]
        print(f"    tick range: {ticks.min()}..{ticks.max()} "
              f"frames {ticks.min()*2+1}..{ticks.max()*2+1}")
        print(f"    agents affected: {len(np.unique(agents))}/{N}")
        big = np.argwhere(mv > 6.0)
        if len(big):
            print(f"    |v|>6 m/s events: {len(big)}; sample:",
                  [(int(t), int(a), round(float(mv[t, a]), 1))
                   for t, a in big[:8]])

    # ---- D. animation driver stats ------------------------------------
    print(f"\n[D] clip channel: vals={np.unique(clip)} "
          f"counts={np.bincount(clip.ravel())}")
    dphase = np.diff(phase, axis=0)
    adv = np.abs(dphase)[mv > 0.35]
    print(f"    phase advance/tick (movers): p50="
          f"{np.percentile(adv, 50):.4f} p90={np.percentile(adv, 90):.4f} "
          f"(stride 1.4m @1m/s -> {1.0/12.0/1.4:.4f})")
    sp = speed[speed > 0.05]
    print(f"    speed m/s: p10={np.percentile(sp, 10):.2f} "
          f"p50={np.percentile(sp, 50):.2f} p90={np.percentile(sp, 90):.2f}")
    print("    max_speed consts:",
          np.round(np.unique(max_speed), 2))

    print("\nVERDICT orientation:",
          "SYSTEMATIC-BUG" if err_m.size and np.degrees(
              np.percentile(err_m, 50)) > 30 else "check-bins")
    print("VERDICT wrap-spins:", "PRESENT" if n_spins > 20 else "minor")
    print("VERDICT teleports:", "PRESENT" if n_tele > 20 else "minor")


if __name__ == "__main__":
    main()
