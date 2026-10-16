# VENDORED 2026-10-16 from mainline blender-agent-kit @6943ab5 (vision-kit s21 vendor round; zero code drift; vision deltas must land as sanctioned deltas per docs/VENDOR_LEDGER.md)
"""hero_gates.py -- session-30/31 export gates (the S30-A forensics: the
gunner twisted-rig + always-on muzzle "bullets" both shipped through
every existing gate; BOTH were structurally invisible to them).

GATE 18 -- HERO AIM COHERENCE. The wrapper-facing gate reads the
capsule/root forward (the pelvis was always square to the aim -> PASS)
and gate 14 reads prop-to-joint proximity (hands + rifle perfectly
placed -> PASS); NOTHING related the torso/head/feet frames to the
aim axis. The session-25 analytic Rifle_Aim authored every torso/leg
bone with its +Z on armature +X while the aim runs -Y -- a constant
90 deg corkscrew (spine.001 +90.0, thighs +90.0/+90.3, head 90.4 deg
off the barrel) that held through the entire 38 s aim phase of the
delivered v5_2 AND v6_0. Law (sampled across the aim window, all
angles between composed node frames inside the gunner's own rig
space -- ancestor rotation cancels, so no jeep/wrapper plumbing):
  - head +Z (face axis) vs rifle -Z (bore)  <= AIM_HEAD_MAX (35)
  - chest +Z (spine.003) vs hips +Z         <= AIM_TORSO_MAX (45)
  - thigh.L/R +Z vs hips +Z                 <= AIM_STANCE_MAX (45)

GATE 19 -- FX OFF-STATE. The muzzle-smoke quads are LINEAR-interpolated
with nonzero onset keys; between a zero key and the next burst's onset
the scale RAMPS across the whole gap (measured: 0.05 -> 0.50 over
t=1.4-14.2 s, BEFORE the first shot; quads visible 71% of the entire
timeline = the user's "bullets constantly sticking out of the gun").
The star/dark families are CONSTANT-interp and correctly 0 outside
their bursts (5.7% / 8.3% key coverage). Law: every FX.* node with an
animated scale track must hold |scale| <= FX_OFF_EPS at every sampled
time OUTSIDE its family's declared event windows (the scene declares
FX_EVENT_WINDOWS + the FX_WORLD_LITTER taxonomy -- road debris that
legitimately holds scale AFTER its event; litter is still checked
BEFORE the event). An FX family with a scale track but no declared
windows fails closed.

GATE 20 -- MOTION CONTINUITY (session-31; see the section note below
for the two shipped classes + the rejected girdle-law design).

BPY-FREE by design (the crowd_v6.gates pattern): unit-testable without
Blender -- scripts/test_hero_gates.py builds synthetic GLB fixtures
(bytes-level accessors exercised, the real code path) proving the
gates can FAIL on the shipped bug classes and PASS the fixed shapes.
The exporter imports and calls these in its gate section.
"""
from __future__ import annotations

import math

AIM_HEAD_MAX = 35.0     # deg -- head face axis vs the bore
AIM_TORSO_MAX = 45.0    # deg -- chest vs pelvis facing (shoulders vs hips)
AIM_STANCE_MAX = 45.0   # deg -- thigh forward vs pelvis facing
FX_OFF_EPS = 1e-3       # |scale| tolerance outside event windows
FX_SAMPLE_STEP_F = 1.0  # sample density (frames) for the FX law
                        # (the s30-r1 review P3: at 2-frame steps an
                        # odd-frame LINEAR spike could slip between
                        # samples; the ramps this gate hunts are long,
                        # but 1f sampling costs nothing)
AIM_SAMPLE_N = 32       # samples across the aim window

# node names (the UAL gunner chain; parameters so tests/other scenes
# can override)
AIM_NODES = {
    "rig_root": "Gunner.Rig",
    "hips": "DEF-hips",
    "chest": "DEF-spine.003",
    "head": "DEF-head",
    "thigh_l": "DEF-thigh.L",
    "thigh_r": "DEF-thigh.R",
    "rifle": "Gunner.Rifle",
}


# ---------------------------------------------------------------------------
# glTF plumbing (minimal accessor set -- the exporter keeps its own; this
# module must stay bpy-free AND import-cheap for the unit tests)
# ---------------------------------------------------------------------------

def _acc(gltf, blob, acc_idx):
    import numpy as np
    acc = gltf["accessors"][acc_idx]
    bv = acc.get("bufferView")
    if bv is None:
        return np.array([])
    bview = gltf["bufferViews"][bv]
    off = bview.get("byteOffset", 0) + acc.get("byteOffset", 0)
    comp = {5126: (np.float32, 4), 5123: (np.uint16, 2),
            5125: (np.uint32, 4), 5121: (np.uint8, 1)}[acc["componentType"]]
    dt, sz = comp
    n = acc.get("count", 0)
    comps = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4,
             "MAT4": 16}[acc["type"]]
    stride = bview.get("byteStride", sz * comps)
    out = np.empty((n, comps), dtype=dt)
    for i in range(n):
        base = off + i * stride
        out[i] = np.frombuffer(blob[base:base + sz * comps], dtype=dt)
    return out


def _track_map(gltf, blob):
    """(node_idx, path) -> (times, values, interpolation) for every
    animated channel. Target-node-first (session-25 F1 law): the exact
    node+Action convention wins ties; one-object-one-action (gate 13)
    keeps the map single-valued anyway. Interpolation is threaded
    through because CONSTANT keys export as STEP -- sampling a STEP
    track linearly false-fires on the ramp between the frame-1 zero
    and the first burst key (the exact class gate 19 audits)."""
    tracks = {}
    for anim in gltf.get("animations", []):
        for ch in anim.get("channels", []):
            t = ch.get("target", {})
            ni, path = t.get("node"), t.get("path")
            if ni is None or path not in ("translation", "rotation", "scale"):
                continue
            s = anim["samplers"][ch["sampler"]]
            times = _acc(gltf, blob, s["input"]).astype(float).ravel()
            vals = _acc(gltf, blob, s["output"]).astype(float)
            interp = s.get("interpolation", "LINEAR")
            key = (ni, path)
            if key not in tracks or anim.get("name") == \
                    f"{gltf['nodes'][ni].get('name', '')}Action":
                tracks[key] = (times, vals, interp)
    return tracks


def _parent_map(gltf):
    parent = {}
    for i, n in enumerate(gltf.get("nodes", [])):
        for c in n.get("children", []):
            parent[c] = i
    return parent


def _chain(gltf, parent, node_idx, stop_idx):
    """[stop_idx .. node_idx] inclusive; None if node_idx is not a
    descendant of stop_idx."""
    chain = []
    i = node_idx
    while i is not None:
        chain.append(i)
        if i == stop_idx:
            chain.reverse()
            return chain
        i = parent.get(i)
    return None


def _quat_rotate(q, v):
    """q = (x, y, z, w) glTF order; v = 3-vector."""
    x, y, z, w = q
    # v' = v + 2*cross(q.xyz, cross(q.xyz, v) + w*v)
    cx = y * v[2] - z * v[1]
    cy = z * v[0] - x * v[2]
    cz = x * v[1] - y * v[0]
    tx = cx + w * v[0]
    ty = cy + w * v[1]
    tz = cz + w * v[2]
    return (v[0] + 2 * (y * tz - z * ty),
            v[1] + 2 * (z * tx - x * tz),
            v[2] + 2 * (x * ty - y * tx))


def _sample_track(ts, vs, t, interp="LINEAR"):
    """Sample at t. LINEAR (default), STEP (holds the previous key --
    CONSTANT-key Blender tracks), CUBICSPLINE treated as LINEAR (none
    in this pipeline). Holds end values outside the track span (glTF
    CONSTANT-extrapolation semantics Blender writes)."""
    n = len(ts)
    if n == 0:
        return None
    if n == 1 or t <= ts[0]:
        return vs[0]
    if t >= ts[-1]:
        return vs[-1]
    import bisect
    i = bisect.bisect_right(ts, t) - 1
    if i >= n - 1:
        return vs[-1]
    if interp == "STEP":
        return vs[i]
    t0, t1 = ts[i], ts[i + 1]
    a = (t - t0) / (t1 - t0) if t1 > t0 else 0.0
    v0, v1 = vs[i], vs[i + 1]
    out = v0 + (v1 - v0) * a
    if vs.shape[1] == 4:        # quat: normalize (nlerp ~ slerp on
        nrm = math.sqrt(sum(c * c for c in out)) or 1.0  # dense keys)
        out = out / nrm
    return out


def _node_local(gltf, tracks, node_idx, t):
    """(R 3x3-ish as quat+scale folded later, T) — returns the local
    TRS at time t as (translation 3, quat 4, scale 3)."""
    node = gltf["nodes"][node_idx]
    tr = tracks.get((node_idx, "translation"))
    rr = tracks.get((node_idx, "rotation"))
    sr = tracks.get((node_idx, "scale"))
    tv = list(node.get("translation", (0.0, 0.0, 0.0))) \
        if tr is None else list(_sample_track(tr[0], tr[1], t, tr[2]))
    rv = list(node.get("rotation", (0.0, 0.0, 0.0, 1.0))) \
        if rr is None else list(_sample_track(rr[0], rr[1], t, rr[2]))
    sv = list(node.get("scale", (1.0, 1.0, 1.0))) \
        if sr is None else list(_sample_track(sr[0], sr[1], t, sr[2]))
    return tv, rv, sv


def _dir_at(gltf, tracks, parent, node_idx, stop_idx, t, local_dir):
    """local_dir expressed in the stop_idx frame, at time t: composes
    the stop..node chain (rotations + scales; translations cancel for
    directions) and applies it to local_dir."""
    ch = _chain(gltf, parent, node_idx, stop_idx)
    if ch is None:
        return None
    # apply children-first: rotate the direction up the chain
    d = local_dir
    for i in reversed(ch[1:]):     # exclude stop_idx's own local TRS
        _, q, s = _node_local(gltf, tracks, i, t)
        d = _quat_rotate(q, d)
        d = (d[0] * s[0], d[1] * s[1], d[2] * s[2])
    return d


def _angle_deg(a, b):
    na = math.sqrt(sum(c * c for c in a)) or 1.0
    nb = math.sqrt(sum(c * c for c in b)) or 1.0
    dot = sum(x * y for x, y in zip(a, b)) / (na * nb)
    return math.degrees(math.acos(max(-1.0, min(1.0, dot))))


# ---------------------------------------------------------------------------
# the shared FX zero-baseline law (scene authoring + gate 19 read the
# SAME plan; the s30-r1 review P2: a test that hand-authors the intended
# key shape pins the gate, not the fix)
# ---------------------------------------------------------------------------

SMOKE_GAP = 4     # frames; a longer silence between keys gets an
#                 explicit pre-onset zero (kills the linear ramp)


def smoke_key_plan(events, gap=SMOKE_GAP, first_frame=1):
    """PURE (bpy-free, unit-pinned): the ordered (frame, scale) keys for
    one LINEAR-interpolated smoke quad, from its event dict {frame:
    scale} (later bursts override at the same frame -- auto-fire
    clusters keep their continuous stream). Emits an explicit
    pre-onset zero at (onset - 1) whenever the previous key is more
    than `gap` frames earlier. `first_frame` = the frame of the always
    keyed leading zero (every FX object gets scale 0 keyed at f1);
    seeding prev_f with it is LOAD-BEARING (the s30-r1 review P1-2:
    prev_f=None left the FIRST burst onset ramping from the f1 zero
    across 351 frames -- |s|=0.297 at f349, the leak halved, not
    fixed, and gate 19 would have rejected the fixed scene itself)."""
    keys = []
    prev_f = first_frame
    for fr in sorted(events):
        v = events[fr]
        if v > 0.0 and fr - prev_f > gap:
            keys.append((fr - 1, 0.0))
        keys.append((fr, v))
        prev_f = fr
    return keys


# ---------------------------------------------------------------------------
# GATE 18 -- hero aim coherence
# ---------------------------------------------------------------------------

def aim_coherence_problems(gltf, blob, fps, aim_f0, f_end,
                           nodes=None, head_max=None, torso_max=None,
                           stance_max=None):
    """GATE 18 checker (PURE; see module docstring for the law + the
    shipped-bug evidence). Returns a list of problem strings; empty =
    coherent (or the gunner chain is absent -> gate not applicable)."""
    nodes = nodes or AIM_NODES
    head_max = AIM_HEAD_MAX if head_max is None else head_max
    torso_max = AIM_TORSO_MAX if torso_max is None else torso_max
    stance_max = AIM_STANCE_MAX if stance_max is None else stance_max
    all_nodes = gltf.get("nodes", [])
    # resolve the rig root FIRST (unique name), then build the
    # name->index map RESTRICTED to its subtree -- every hero exports
    # its own DEF-hips/DEF-spine.*/DEF-thigh.* set, so a global name
    # map is ambiguous and silently audits the wrong skeleton
    root_i = next((i for i, n in enumerate(all_nodes)
                   if n.get("name") == nodes["rig_root"]), None)
    if root_i is None:
        return []                      # no UAL gunner in this package
    parent = _parent_map(gltf)
    subtree = set()
    stack = list(all_nodes[root_i].get("children", []))
    while stack:
        ci = stack.pop()
        if ci in subtree:
            continue
        subtree.add(ci)
        stack.extend(all_nodes[ci].get("children", []))
    subtree.add(root_i)
    names = {all_nodes[i].get("name", ""): i for i in sorted(subtree)}
    need = ("hips", "chest", "head", "thigh_l", "thigh_r", "rifle")
    idx = {}
    for k in need:
        i = names.get(nodes[k])
        if i is None:
            return [f"gate18: gunner rig present but {nodes[k]} "
                    "missing from the GLB (aim coherence unauditable)"]
        idx[k] = i
    tracks = _track_map(gltf, blob)

    t0 = aim_f0 / fps
    t1 = f_end / fps
    step = (t1 - t0) / max(AIM_SAMPLE_N - 1, 1)
    samples = [t0 + k * step for k in range(AIM_SAMPLE_N)]

    worst = {"head": 0.0, "torso": 0.0, "stance_l": 0.0, "stance_r": 0.0}
    for t in samples:
        hips_z = _dir_at(gltf, tracks, parent, idx["hips"], root_i, t,
                         (0.0, 0.0, 1.0))
        chest_z = _dir_at(gltf, tracks, parent, idx["chest"], root_i, t,
                          (0.0, 0.0, 1.0))
        head_z = _dir_at(gltf, tracks, parent, idx["head"], root_i, t,
                         (0.0, 0.0, 1.0))
        aim = _dir_at(gltf, tracks, parent, idx["rifle"], root_i, t,
                      (0.0, 0.0, -1.0))       # bore = rifle local -Z
        th_l = _dir_at(gltf, tracks, parent, idx["thigh_l"], root_i, t,
                       (0.0, 0.0, 1.0))
        th_r = _dir_at(gltf, tracks, parent, idx["thigh_r"], root_i, t,
                       (0.0, 0.0, 1.0))
        if any(v is None for v in (hips_z, chest_z, head_z, aim)):
            return [f"gate18: gunner chain broken under {nodes['rig_root']} "
                    "(bones are not descendants of the rig root)"]
        worst["head"] = max(worst["head"], _angle_deg(head_z, aim))
        worst["torso"] = max(worst["torso"], _angle_deg(chest_z, hips_z))
        if th_l is not None:
            worst["stance_l"] = max(worst["stance_l"],
                                    _angle_deg(th_l, hips_z))
        if th_r is not None:
            worst["stance_r"] = max(worst["stance_r"],
                                    _angle_deg(th_r, hips_z))

    problems = []
    if worst["head"] > head_max:
        problems.append(
            f"gate18: gunner head faces {worst['head']:.1f} deg off the "
            f"bore (>{head_max:.0f}) during the aim window — twisted-rig "
            "class (the face must read down the sights)")
    if worst["torso"] > torso_max:
        problems.append(
            f"gate18: gunner chest {worst['torso']:.1f} deg off the pelvis "
            f"(>{torso_max:.0f}) — corkscrew class (v5_2/v6_0 shipped "
            "90.1 deg)")
    st = max(worst["stance_l"], worst["stance_r"])
    if st > stance_max:
        problems.append(
            f"gate18: gunner stance {st:.1f} deg off the pelvis facing "
            f"(>{stance_max:.0f}) — feet-blade class (v5_2/v6_0 shipped "
            "90.0/90.3)")
    return problems


# ---------------------------------------------------------------------------
# GATE 19 -- FX off-state
# ---------------------------------------------------------------------------

def fx_offstate_problems(gltf, blob, fps, fx_windows, litter, f_end,
                         f_start=1, eps=None, step_f=None):
    """GATE 19 checker (PURE). fx_windows: {family prefix: [(f0, f1),
    ...]} in FRAMES; litter: iterable of node names that legitimately
    hold scale AFTER their last window (road debris; still checked
    BEFORE the first). Samples every step_f frames; |scale| must stay
    <= eps outside the node's family windows (+-1 frame tolerance)."""
    import numpy as np
    eps = FX_OFF_EPS if eps is None else eps
    step_f = FX_SAMPLE_STEP_F if step_f is None else step_f
    litter = set(litter or ())
    windows = {fam: sorted(w) for fam, w in (fx_windows or {}).items() if w}

    def family_of(name):
        best = None
        for fam in windows:
            if name.startswith(fam) and (best is None or
                                         len(fam) > len(best)):
                best = fam
        return best

    tracks = _track_map(gltf, blob)
    names = {n.get("name", ""): i for i, n in
             enumerate(gltf.get("nodes", []))}
    problems = []
    all_ts = np.arange(f_start, f_end + 1.0, step_f) / fps
    for nm, ni in sorted(names.items()):
        if not nm.startswith("FX."):
            continue
        sc = tracks.get((ni, "scale"))
        if sc is None:
            continue                        # no animated scale — N/A
        fam = family_of(nm)
        if fam is None:
            problems.append(
                f"gate19: {nm} has an animated scale track but no "
                "FX_EVENT_WINDOWS family declares it (fail-closed: "
                "every FX family must declare its event windows)")
            continue
        wins = [(f0 - 1.0, f1 + 1.0) for f0, f1 in windows[fam]]
        if nm in litter:
            # litter: only the pre-event span must be off
            first0 = min(w[0] for w in wins)
            ts = [t for t in all_ts if t * fps < first0]
            if not ts:
                continue
        else:
            ts = all_ts
        sc_ts, sc_vs, sc_interp = sc
        for t in ts:
            f = t * fps
            if any(w[0] <= f <= w[1] for w in wins):
                continue
            v = _sample_track(sc_ts, sc_vs, t, sc_interp)
            if v is None:
                continue
            if max(abs(float(c)) for c in v) > eps:
                problems.append(
                    f"gate19: {nm} scale {max(abs(float(c)) for c in v):.3f} "
                    f"at f{f:.0f} outside its {fam} event windows — "
                    "FX must be OFF (scale <= 1e-3) outside events "
                    "(the v5_2/v6_0 'bullets sticking out' leak)")
                break                        # one hit per node is enough
    return problems


# ---------------------------------------------------------------------------
# GATE 20 -- MOTION CONTINUITY (session-31: the sprint-transition
# storm + the recoil-pop sign-flip class)
# ---------------------------------------------------------------------------
# Two shipped bug classes, one law shape -- no animated rotation
# track inside the gunner's rig subtree may step more than sweep_max
# between ADJACENT keys (frame gap <= 1.5) within the window:
#   sprint window (pre-boards), SPRINT_SWEEP_MAX 90: the take-6
#     sprint->aim transition was a 6-frame per-bone slerp between a
#     mid-stride Sprint_Loop pose and the aim stance -- DEF-thigh.L
#     flipped 176.8 deg in ONE frame at f153 and Gunner.Rifle 154.5
#     (the user's S3 f152 "whole limb twisted into body"); a
#     coherent library stride peaks 46.7 deg/frame.
#   aim window (post-boards), AIM_SWEEP_MAX 40: Rifle_Shoot's PEAK
#     key carried the opposite DOUBLE-COVER quaternion sign vs the
#     aim key (separate IK passes, no cross-key canonicalization),
#     and Blender's componentwise-LINEAR quaternion fcurves lerp
#     through the ZERO VECTOR between them -- take-6 measured
#     DEF-upper_arm.R ALTERNATING aim/anti-pose at 174-179 deg/frame
#     during rapid strobes (f381-383; the user's "transient issues
#     in a lot of frames"); legit recoil pops measure ~15 deg/frame.
# FX.* nodes are EXCLUDED: their single-frame rotation snaps ride
# scale-0 frames (invisible by construction; the FX family's
# visibility law is gate 19's scale windows, not rotation).
# DESIGN NOTE: a node-level "girdle twist" law was prototyped and
# REJECTED -- the thigh girdle line from node ORIGINS is the hip
# joint pair (static under the stride), and chest-vs-hips yaw during
# a LEGIT stride oscillates 10-34 deg, indistinguishable from the
# storm's slow component; the skinned-landmark girdle signal (71 deg
# peak vs 16.2 steady, the s31 probe) is not reproducible from node
# TRS. The flip law above is the node-measurable signature of the
# class and fires on the exact take-6 frames.
SPRINT_SWEEP_MAX = 90.0
AIM_SWEEP_MAX = 40.0


def _quat_angle_deg(a, b):
    d = abs(sum(x * y for x, y in zip(a, b)))
    d = max(-1.0, min(1.0, d))
    return math.degrees(2.0 * math.acos(d))


def motion_continuity_problems(gltf, blob, fps, f0, f1, sweep_max,
                               nodes=None):
    """GATE 20 checker (PURE). Every rotation track on nodes inside
    the gunner's rig subtree (FX.* excluded -- see the module note):
    the angular step between ADJACENT keys whose frame gap <= 1.5
    must stay <= sweep_max within [f0, f1]."""
    nodes = nodes or AIM_NODES
    all_nodes = gltf.get("nodes", [])
    root_i = next((i for i, n in enumerate(all_nodes)
                   if n.get("name") == nodes["rig_root"]), None)
    if root_i is None:
        return []
    subtree = set()
    stack = list(all_nodes[root_i].get("children", []))
    while stack:
        ci = stack.pop()
        if ci in subtree:
            continue
        subtree.add(ci)
        stack.extend(all_nodes[ci].get("children", []))
    subtree.add(root_i)
    tracks = _track_map(gltf, blob)
    t0, t1 = f0 / fps, f1 / fps
    problems = []
    for ni in sorted(subtree):
        nm = all_nodes[ni].get("name", "")
        if nm.startswith("FX."):
            continue                    # scale-0 rotation snaps: gate
        #                               # 19 owns FX visibility
        tr = tracks.get((ni, "rotation"))
        if tr is None:
            continue
        ts, vs, _interp = tr
        worst = 0.0
        at = None
        for k in range(len(ts) - 1):
            if not (t0 <= ts[k] and ts[k + 1] <= t1):
                continue
            if ts[k + 1] - ts[k] > 1.5:
                continue
            d = _quat_angle_deg(vs[k], vs[k + 1])
            if d > worst:
                worst, at = d, ts[k] * fps
        if worst > sweep_max:
            problems.append(
                f"gate20: {nm or f'node{ni}'} rotation steps {worst:.1f} "
                f"deg between adjacent keys at ~f{at:.0f} "
                f"(>{sweep_max:.0f}) — single-frame flip class "
                "(sign-flipped source keys / blend storm / IK branch "
                "jump; take-6: thigh.L 176.8 at f153, upper_arm.R 174 "
                "at f381)")
    return problems


# ---------------------------------------------------------------------------
# GATE 21 -- CROWD CAPSULE ORIENTATION (session-31: the user's S11
# f819 "orientation is not set right again crowd behavior issue")
# ---------------------------------------------------------------------------
# take-6 measured EVERY standing capsule rendering exactly 90 deg off
# its heading: the sim's yaw is the heading in atan2(vy, vx)
# convention (yaw 0 = +X belt-local) while the FROZEN v3 spawn
# capsule mesh faces +Y at euler 0; bake2 keyed the heading verbatim
# (VLM on the S11 still: figures "standing perfectly sideways,
# sliding without turning"). The fix is bake2's YAW_VISUAL_OFFSET;
# THIS gate pins the class at the exported bytes:
#   for every Zed.NNNN / Zed.ChaseNN capsule anchor that is STANDING
#   (its long axis -- node-local +Y -- within CAPS_STANDING_MAX of
#   world up; lying corpses/ragdolls are excluded, their facing is
#   legitimately arbitrary) and MOVING in BELT-LOCAL terms (the
#   street-relative speed from the node's own translation track --
#   the belt is the treadmill, world speed is dominated by the
#   BeltRoot scroll and is NOT the orientation reference), the
#   mesh-forward direction (node-local -Z: the head-offset axis the
#   capsule geometry carries) must stay within CAPS_ORIENT_MAX of the
#   belt-local velocity direction.
CAPS_ORIENT_MAX = 100.0    # deg, AGENT-MEDIAN law: an agent fires
#                          # when the MEDIAN of its in-band moving
#                          # samples exceeds this. Calibrated on the
#                          # take-6 vs take-7 pair: the systematic
#                          # convention class (bake2 pre-fix) put 21
#                          # agents at >=100 and 98 at >=60; the
#                          # post-fix build puts 0 at >=100 and 10 at
#                          # 60-95. The 60-99 band is the sim's
#                          # BY-DESIGN jostle class (relax-solver
#                          # shoves + stagger impulses + weave vs the
#                          # desired-heading yaw -- a dense panicked
#                          # crowd lurches) + the milling yaw-hunt;
#                          # documented for the replacement crowd
#                          # system, deliberately below the gate's
#                          # detection threshold. A regression of the
#                          # YAW_VISUAL_OFFSET class puts the whole
#                          # population at ~180 median -> ~100 fires.
CAPS_SPEED_MIN = 0.35      # m/s, belt-local NET over CAPS_VBASE_F
#                          # frames (below this the heading is
#                          # ill-defined -- milling/weaving; the
#                          # take-7 tail proved short baselines read
#                          # the FSM weave oscillation as motion:
#                          # Zed.0009's +/-0.35 m weave at ~2 s
#                          # period read as sustained 155-180 deg
#                          # misalignment on 2- and 6-frame baselines)
CAPS_STANDING_MAX = 25.0   # deg off world up (lying corpses exempt)
CAPS_STEP_F = 2.0          # the bake key grid
CAPS_VBASE_F = 48.0        # the velocity baseline (frames = 2 s):
#                          # LONGER than the FSM weave period (~2 s)
#                          # so oscillation cancels and only NET
#                          # travel reads; real walking (>= 0.35 m/s
#                          # net) survives, millers drop below the
#                          # speed gate
CAPS_MIN_SAMPLES = 10      # an agent needs this many audited samples
#                          # to have a median at all (off-camera /
#                          # always-lying agents are N/A)
CAPS_BAND_R = 40.0         # m: audit only capsules within this world
#                          # z-band of the JEEP (the action anchor --
#                          # the cameras follow the jeep; the
#                          # treadmill hinterland at belt-y 200+ mills
#                          # off-camera and is noise, not signal)

import re as _re

CAPS_NAME_PAT = _re.compile(r"^Zed\.(\d{4}|Chase\d{2})$")


def _world_dir_full(gltf, tracks, parent, node_idx, local_dir, t):
    """local_dir expressed in WORLD (scene-root) terms at time t:
    composes the full ancestor chain's rotations (translations cancel
    for directions)."""
    d = local_dir
    i = node_idx
    while i is not None:
        _, q, _s = _node_local(gltf, tracks, i, t)
        d = _quat_rotate(q, d)
        i = parent.get(i)
    return d


def _quat_mul(a, b):
    """(x, y, z, w) quaternion product -- applies b THEN a."""
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw,
            aw * bw - ax * bx - ay * by - az * bz)


def _world_pos_full(gltf, tracks, parent, node_idx, t):
    """Node ORIGIN in world (scene-root) terms at time t (forward
    position composition of the full ancestor chain)."""
    chain = []
    i = node_idx
    while i is not None:
        chain.append(i)
        i = parent.get(i)
    chain.reverse()
    p = (0.0, 0.0, 0.0)
    rq = (0.0, 0.0, 0.0, 1.0)
    for i in chain:
        tv, q, _s = _node_local(gltf, tracks, i, t)
        pv = _quat_rotate(rq, tv)
        p = (p[0] + pv[0], p[1] + pv[1], p[2] + pv[2])
        rq = _quat_mul(rq, q)
    return p


def capsule_orientation_problems(gltf, blob, fps, f_end, f_start=1,
                                 mis_max=None, speed_min=None,
                                 step_f=None):
    """GATE 21 checker (PURE). The AGENT-MEDIAN orientation law:
    an agent fires when the MEDIAN of its in-band, moving, standing
    samples' misalignment (mesh-forward vs belt-local net motion)
    exceeds mis_max. Scoped to the ACTION BAND (world z within
    CAPS_BAND_R of the jeep -- the cameras follow the jeep; the
    treadmill hinterland mills off-camera). Empty = coherent / no
    crowd capsules / no action anchor."""
    mis_max = CAPS_ORIENT_MAX if mis_max is None else mis_max
    speed_min = CAPS_SPEED_MIN if speed_min is None else speed_min
    step_f = CAPS_STEP_F if step_f is None else step_f
    all_nodes = gltf.get("nodes", [])
    tracks = _track_map(gltf, blob)
    parent = _parent_map(gltf)
    up = (0.0, 1.0, 0.0)
    jeep_i = next((i for i, n in enumerate(all_nodes)
                   if n.get("name") == "JeepRoot"), None)
    if jeep_i is None:
        return []          # no action anchor -- not applicable
    problems = []
    for ni, n in enumerate(all_nodes):
        nm = n.get("name", "")
        if not CAPS_NAME_PAT.match(nm):
            continue
        tr = tracks.get((ni, "translation"))
        if tr is None:
            continue                    # static spawn prop, not a mover
        ts, vs, _interp = tr
        mis_list = []
        f = float(f_start)
        while f + CAPS_VBASE_F <= f_end:
            t0, t1 = f / fps, (f + CAPS_VBASE_F) / fps
            p0 = _sample_track(ts, vs, t0)
            p1 = _sample_track(ts, vs, t1)
            if p0 is None or p1 is None:
                break
            vx = (p1[0] - p0[0]) * fps / CAPS_VBASE_F
            vz = (p1[2] - p0[2]) * fps / CAPS_VBASE_F
            vm = math.hypot(vx, vz)
            if vm < speed_min:
                f += step_f
                continue
            # action-band check: the capsule's WORLD z within the
            # jeep's band (the cameras follow the jeep)
            cp = _world_pos_full(gltf, tracks, parent, ni, t0)
            jp = _world_pos_full(gltf, tracks, parent, jeep_i, t0)
            if abs(cp[2] - jp[2]) > CAPS_BAND_R:
                f += step_f
                continue
            # standing check: the capsule long axis (local +Y)
            yaw_dir = _world_dir_full(gltf, tracks, parent, ni,
                                      (0.0, 1.0, 0.0), t0)
            yn = math.sqrt(sum(c * c for c in yaw_dir)) or 1.0
            tilt = _angle_deg(tuple(c / yn for c in yaw_dir), up)
            if tilt > CAPS_STANDING_MAX:
                f += step_f
                continue
            fwd = _world_dir_full(gltf, tracks, parent, ni,
                                  (0.0, 0.0, -1.0), t0)
            fn = math.sqrt(sum(c * c for c in fwd)) or 1.0
            fwd_h = (fwd[0] / fn, fwd[2] / fn)
            vel_h = (vx / vm, vz / vm)
            mis_list.append(_angle_deg(fwd_h, vel_h))
            f += step_f
        if len(mis_list) < CAPS_MIN_SAMPLES:
            continue                    # off-camera / always-lying
        mis_list.sort()
        med = mis_list[len(mis_list) // 2]
        if med > mis_max:
            problems.append(
                f"gate21: {nm} mesh-forward MEDIAN {med:.1f} deg off "
                f"its belt-local motion over {len(mis_list)} in-band "
                f"samples (>{mis_max:.0f}) — capsule orientation "
                "class (take-6: 21 agents >=100, 98 >=60; the bake2 "
                "YAW_VISUAL_OFFSET fix)")
    return problems


