"""fix1_probe_glb.py -- dissect a previz package GLB: what does the
review app actually play?

Pure stdlib (struct+json) glTF parsing:
  - census: meshes, skins, animations, per-animation track counts +
    target nodes
  - motion sampling: for animation tracks targeting selected nodes
    (crowd anchors Zed.*, heroes), decode the translation accessor at
    first/mid/last frames -> is the crowd moving? at what apparent
    speed? any 2-frame jumps (teleport read)?
  - skin check: do the Zed rig nodes have skin+animation tracks (the
    walk cycle in the app) or nothing (frozen statues)?

Usage: python3 fix1_probe_glb.py <scene.glb> [--node Zed.0001 ...]
"""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path


def read_glb(path):
    data = Path(path).read_bytes()
    magic, ver, total = struct.unpack_from("<III", data, 0)
    assert magic == 0x46546C67, "not a glb"
    off = 12
    js = None
    binb = None
    while off < total:
        clen, ctype = struct.unpack_from("<II", data, off)
        chunk = data[off + 8: off + 8 + clen]
        if ctype == 0x4E4F534A:
            js = json.loads(chunk)
        elif ctype == 0x004E4942:
            binb = chunk
        off += 8 + clen
    return js, binb


def acc_component_count(t):
    return {5120: 1, 5121: 1, 5122: 1, 5123: 1, 5125: 1, 5126: 1,
            5127: 2, 5128: 2, 5129: 2, 5130: 4, 5131: 4, 5132: 4,
            5133: 4, 5134: 4, 5135: 4, 5136: 4, 5137: 4}[t]


def read_acc(js, binb, idx):
    a = js["accessors"][idx]
    bv = js["bufferViews"][a.get("bufferView", 0)]
    off = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    n = a["count"]
    vec = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4,
           "MAT4": 16}.get(a.get("type", "SCALAR"), 1)
    comp = acc_component_count(a["componentType"]) * vec
    fmt, sz = {5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2),
               5123: ("H", 2), 5125: ("B", 1), 5126: ("f", 4),
               5127: ("H", 2), 5128: ("H", 2), 5129: ("I", 4),
               5130: ("i", 4), 5131: ("I", 4), 5132: ("f", 4),
               5133: ("I", 4), 5134: ("f", 4), 5136: ("f", 4),
               5137: ("f", 4)}[a["componentType"]]
    comp = comp // vec
    stride = bv.get("byteStride", comp * vec * sz)
    vals = []
    end = min(n, 200000)
    for i in range(end):
        o = off + i * stride
        vals.append(struct.unpack_from(f"<{comp * vec}{fmt}", binb, o))
    return vals, a.get("min"), a.get("max"), n


def main():
    glb = sys.argv[1]
    js, binb = read_glb(glb)
    nodes = js.get("nodes", [])
    meshes = js.get("meshes", [])
    skins = js.get("skins", [])
    anims = js.get("animations", [])
    print(f"{Path(glb).name}: nodes={len(nodes)} meshes={len(meshes)} "
          f"skins={len(skins)} animations={len(anims)}")

    # node name map
    named = {i: n.get("name", f"<{i}>") for i, n in enumerate(nodes)}

    # ---- animation census ------------------------------------------
    import collections
    trk_targets = collections.Counter()
    path_census = collections.Counter()
    anim_durs = []
    for ai, an in enumerate(anims):
        chans = an.get("channels", [])
        paths = collections.Counter()
        targets = set()
        for ch in chans:
            p = ch["target"]["path"]
            paths[p] += 1
            targets.add(ch["target"].get("node"))
        path_census.update(paths)
        samp = an.get("samplers", [])
        dmax = 0.0
        for s in samp[:1]:
            ts, _, _, _ = read_acc(js, binb, s["input"])
            if ts:
                dmax = max(dmax, ts[-1][0])
        anim_durs.append(dmax)
        if ai < 3 or ai > len(anims) - 3:
            print(f"  anim[{ai}] {an.get('name','?')[:36]:36s} "
                  f"chans={len(chans):3d} paths={dict(paths)} "
                  f"dur~{dmax:.1f}s")
    print(f"  channel path census: {dict(path_census)}")
    if anim_durs:
        anim_durs.sort()
        print(f"  durations: p50={anim_durs[len(anim_durs)//2]:.1f}s "
              f"max={anim_durs[-1]:.1f}s")

    # ---- crowd + hero node census ----------------------------------
    import re
    zed = [i for i, n in named.items()
           if re.match(r"^Zed\.\d{4}$", n)]
    heroes = [i for i, n in named.items()
              if n.startswith(("Master.", "Runner.", "Driver.",
                               "Girl.", "Gunner.",
                               "StandardBearer."))]
    print(f"\ncrowd anchors (Zed.*.Root): {len(zed)}  hero nodes: "
          f"{len(heroes)} -> {[named[i] for i in heroes[:8]]}")

    # which nodes have ANIMATION channels at all?
    animated_nodes = collections.Counter()
    for an in anims:
        for ch in an.get("channels", []):
            ni = ch["target"].get("node")
            if ni is not None:
                animated_nodes[ni] += 1
    zed_animated = sum(1 for i in zed if animated_nodes.get(i))
    print(f"crowd anchors WITH animation channels: {zed_animated}/{len(zed)}")
    hero_animated = [named[i] for i in heroes if animated_nodes.get(i)]
    print(f"hero nodes WITH animation channels: {hero_animated[:10]}")

    # skins -> joints: which nodes are skinned rigs
    skin_roots = set()
    for sk in skins:
        for j in sk.get("joints", []):
            skin_roots.add(j)
    zed_skinned = sum(1 for i in zed if i in skin_roots)
    print(f"crowd anchors that are skin joints: {zed_skinned}/{len(zed)}")
    # rigs: nodes with .Rig or .Hum in name
    rigs = [i for i, n in named.items() if ".Rig" in n or ".Hum" in n]
    rigs_anim = sum(1 for i in rigs if animated_nodes.get(i))
    print(f"rig nodes ({len(rigs)}) with animation channels: {rigs_anim}")

    # ---- teleport / speed sampling on a few anchors -----------------
    print("\nmotion sampling (translation tracks):")
    # build node->anim map for translation
    node_trans = {}
    for an in anims:
        for ci, ch in enumerate(an.get("channels", [])):
            if ch["target"]["path"] != "translation":
                continue
            ni = ch["target"].get("node")
            if ni is None:
                continue
            smp = an["samplers"][ch["sampler"]]
            node_trans.setdefault(ni, []).append(
                (an.get("name", f"a{ci}"), smp))
    sample = zed[:6]
    for ni in sample:
        if ni not in node_trans:
            print(f"  {named[ni]}: NO translation track")
            continue
        aname, smp = node_trans[ni][0]
        ts, _, _, _ = read_acc(js, binb, smp["input"])
        vs, _, _, cnt = read_acc(js, binb, smp["output"])
        if len(ts) < 3:
            print(f"  {named[ni]}: keys={len(ts)}")
            continue
        # max inter-key step
        maxstep = 0.0
        maxat = 0
        for k in range(min(len(ts) - 1, len(vs) - 1)):
            dt = ts[k + 1][0] - ts[k][0]
            if dt <= 0:
                continue
            dx = vs[k + 1][0] - vs[k][0]
            dy = vs[k + 1][1] - vs[k][1]
            step = (dx * dx + dy * dy) ** 0.5 / dt
            if step > maxstep:
                maxstep, maxat = step, ts[k][0]
        span = ((vs[-1][0] - vs[0][0]) ** 2 +
                (vs[-1][1] - vs[0][1]) ** 2) ** 0.5
        print(f"  {named[ni]}: keys={len(ts)} dur={ts[-1][0]:.0f}s "
              f"path={span:.1f}m maxstep={maxstep:.2f}m/s @t={maxat:.1f}s")

    print("\n[glb probe] done")


if __name__ == "__main__":
    main()
