#!/usr/bin/env python3
"""audit_glb_motion.py — the deep-audit motion census over a film
package's exported GLB (fix-wave-2 verification; the audit round's
canonical probe). Commit-carried (the first copy died with an
uncommitted sandbox).

Per-agent (nodes that are ANCESTORS OF SKINNED JOINTS — the
AGENT-FILTER LAW: a 19 m/s crane is cinematography, the 30 m/s
express IS the story, rain sweeps are FX; only crowd agents count):
  [T] TELEPORT census — per-interval speed above SPEED_MAX.
  [P] BROWNIAN census — path_length / net_displacement on true movers.
  [O] ORIENTATION — median angle between the film's canonical heading
      axis and velocity over moving intervals (self-calibrated).
  [S] SPIN census — adjacent-key yaw deltas above SPIN_DEG, computed
      on UNWRAPPED yaw (THE WRAP LAW: a diff on atan2 output reads a
      10-deg turn as 350 — the probe's own round-1 false positive).

Exit 1 on any gate. Pure stdlib + numpy.
Usage: python3 audit_glb_motion.py <scene.glb>
"""
from __future__ import annotations
import json, struct, sys, math
import numpy as np

SPEED_MAX = 9.0        # m/s per interval
SPIN_DEG = 120.0       # adjacent-key yaw jump
ORIENT_MAX = 40.0      # deg median heading-vs-velocity
BROWN_RATIO = 6.0      # path/disp on true movers
MIN_SPEED = 0.5        # m/s — 'moving interval' for orientation
MIN_DISP = 1.0         # m — agents that actually travel


def read_glb(path):
    data = open(path, "rb").read()
    assert struct.unpack_from("<I", data, 0)[0] == 0x46546C67, "not a glb"
    off = 12
    js = None
    bin_chunk = None
    while off < len(data):
        clen, ctype = struct.unpack_from("<II", data, off)
        chunk = data[off + 8: off + 8 + clen]
        if ctype == 0x4E4F534A:
            js = json.loads(chunk)
        elif ctype == 0x004E4942:
            bin_chunk = chunk
        off += 8 + clen
    return js, bin_chunk


def read_accessor(js, bin_chunk, idx):
    acc = js["accessors"][idx]
    bv = js["bufferViews"][acc["bufferView"]]
    off = (bv.get("byteOffset", 0)) + (acc.get("byteOffset", 0))
    ncomp = {"SCALAR": 1, "VEC3": 3, "VEC4": 4, "MAT4": 16}[acc["type"]]
    dt = {5126: np.float32, 5123: np.uint16, 5125: np.uint32,
          5121: np.uint8}[acc["componentType"]]
    return np.frombuffer(bin_chunk, dtype=dt, count=acc["count"] * ncomp,
                         offset=off).reshape(acc["count"], ncomp).astype(np.float64)


def track_of(js, bin_chunk, anim, target_node, path):
    for ch in anim["channels"]:
        if ch["target"]["node"] == target_node and ch["target"]["path"] == path:
            smp = anim["samplers"][ch["sampler"]]
            return (read_accessor(js, bin_chunk, smp["input"]).ravel(),
                    read_accessor(js, bin_chunk, smp["output"]))
    return None


def quat_yaw(q):
    """Yaw of a quaternion in glTF Y-up convention: heading of the
    rotated +Z forward in the XZ plane."""
    w, x, y, z = q
    fx = 2 * (x * z + w * y)
    fz = 1 - 2 * (x * x + y * y)
    return math.atan2(fx, fz)


def main():
    glb = sys.argv[1]
    js, bin_chunk = read_glb(glb)
    nodes = js["nodes"]
    name2idx = {n.get("name", f"__{i}"): i for i, n in enumerate(nodes)}

    # THE AGENT-FILTER LAW: agents are ANCESTORS OF SKINNED JOINTS.
    parent = {}
    for i, n in enumerate(nodes):
        for c in n.get("children", []):
            parent[c] = i
    agent_nodes = set()
    for skin in js.get("skins", []):
        stack = list(skin["joints"])
        while stack:
            j = stack.pop()
            if j in agent_nodes:
                continue
            agent_nodes.add(j)
            p = parent.get(j)
            while p is not None and p not in agent_nodes:
                agent_nodes.add(p)
                p = parent.get(p)

    agents = {}
    for anim in js["animations"]:
        nm = anim.get("name", "")
        if not nm.endswith("Action"):
            continue
        base = nm[: -len("Action")]
        if base not in name2idx:
            continue
        nidx = name2idx[base]
        if nidx not in agent_nodes:
            continue  # camera / FX / vehicle — not a crowd agent
        tr = track_of(js, bin_chunk, anim, nidx, "translation")
        rot = track_of(js, bin_chunk, anim, nidx, "rotation")
        if tr is not None:
            agents.setdefault(base, {})["t"] = tr
        if rot is not None:
            agents.setdefault(base, {})["r"] = rot

    if not agents:
        print("NO AGENT ROOT ACTIONS FOUND — structural fail")
        return 1

    teleports, spins, brownian = [], [], []
    orient_err = {k: [] for k in ("+Z", "-Z", "+X", "-X")}

    for name, d in agents.items():
        if "t" not in d:
            continue
        times, xyz = d["t"]
        if len(times) < 2:
            continue
        dt = np.diff(times)
        dxyz = np.diff(xyz, axis=0)
        planar = dxyz[:, [0, 2]]
        dist = np.linalg.norm(dxyz, axis=1)
        speed = np.where(dt > 0, dist / np.maximum(dt, 1e-9), 0.0)
        for i, sv in enumerate(speed):
            if sv > SPEED_MAX:
                teleports.append((name, float(times[i + 1]), float(sv)))
        path = float(np.linalg.norm(planar, axis=1).sum())
        disp = float(np.linalg.norm(planar[-1] - planar[0])) if len(planar) else 0.0
        if disp >= MIN_DISP and path > 0 and path / disp > BROWN_RATIO:
            brownian.append((name, path / disp))
        if "r" in d:
            rtimes, rq = d["r"]
            yaws_raw = np.array([quat_yaw(q) for q in rq])
            yaws = np.unwrap(yaws_raw)   # THE WRAP LAW
            for i, dy in enumerate(np.diff(yaws)):
                adeg = abs(math.degrees(dy))
                if adeg > SPIN_DEG:
                    spins.append((name, float(rtimes[i + 1]), adeg))
            if len(rtimes) == len(times):
                for i in range(len(times) - 1):
                    if speed[i] < MIN_SPEED or dt[i] <= 0:
                        continue
                    v = planar[i] / max(np.linalg.norm(planar[i]), 1e-9)
                    vh = math.atan2(v[0], v[1])
                    y = yaws[i]
                    for axis, off in (("+Z", 0.0), ("-Z", math.pi),
                                      ("+X", math.pi / 2), ("-X", -math.pi / 2)):
                        err = abs(math.degrees(math.atan2(
                            math.sin(y + off - vh), math.cos(y + off - vh))))
                        orient_err[axis].append(err)

    n_agents = len(agents)
    print(f"[census] agents with root actions: {n_agents}")
    print(f"[T] teleport intervals > {SPEED_MAX} m/s: {len(teleports)}")
    for t in teleports[:8]:
        print(f"     {t[0]} @f{t[1]*24:.0f} {t[2]:.1f} m/s")
    print(f"[S] spin events > {SPIN_DEG} deg/key: {len(spins)}")
    for s in spins[:8]:
        print(f"     {s[0]} @f{s[1]*24:.0f} {s[2]:.0f} deg")
    print(f"[P] brownian movers (path/disp > {BROWN_RATIO}): {len(brownian)}")
    for b in brownian[:8]:
        print(f"     {b[0]} ratio={b[1]:.1f}")
    best_axis, best_med = None, 1e9
    for axis, errs in orient_err.items():
        if len(errs) >= 20:
            med = float(np.median(errs))
            print(f"[O] axis {axis}: n={len(errs)} median {med:.1f} deg")
            if med < best_med:
                best_axis, best_med = axis, med
    fail = bool(teleports or spins or len(brownian) > max(2, n_agents // 50)
                or best_axis is None or best_med > ORIENT_MAX)
    if best_axis is not None and best_med <= ORIENT_MAX:
        print(f"[O] PASS: best axis {best_axis} median {best_med:.1f} deg")
    print("VERDICT:", "FAIL" if fail else "PASS")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
