"""
export_previz_package.py — export a review-ready previz package (v2).

The "JSON + GLB" contract for the web review app (user feedback loop):
  <output>/
    scene.glb        geometry + ALL object actions + CAMERAS (shot cams
                     with their animation + parenting, so the app can
                     follow them frame-exactly) + aim targets
    previz.json      schema 2.0 — EVERYTHING the audit found in the
                     scene module + built scene: shot table (marker-
                     bound = ground truth), camera map (built-scene
                     optics + CAMS_V3 motion specs), full story block
                     (dialog, knockdowns, chase falls, muzzle bursts,
                     board, run params, motion/flatness policies, speed
                     profile, jeep weave, lunge, rb config, drive
                     scalars), characters registry (identity colors),
                     world (background + lights), actions manifest,
                     provenance (git sha, timestamps, versions)
    sfx_events.json  frame-stamped event stream (via the scene module's
                     own emit_sfx_events, when it exists)
    scene.usda       OPTIONAL USD sidecar (--usd-sidecar): the kit's USD
                     carrier (previz:entity customData + animation).
                     JSON+GLB stays the primary web contract — the USD
                     track exists for USD-native consumers (webpreviz
                     converter); the parity gate below proves the two
                     carriers agree on the story payload.
    stills/          optional ground-truth shot jpgs (--stills-dir)

FAIL-CLOSED post-checks (the "nothing left out" gate):
  1. every shot's camera node exists in the GLB
  2. every camera's Aim.* target node exists in the GLB (the app
     rebuilds TRACK_TO from them — glTF ACTIONS mode does NOT bake
     constraints, session-20 gotcha 84)
  3. shot table contiguous and spans the full frame range
  4. every story constant the scene module DECLARES lands in the JSON
     (declared-but-missing = FAIL, not a warning)
  5. characters registry non-empty, every root object exists
  6. actions manifest non-empty
  7. USD parity (with --usd-sidecar): every JSON story collection is
     present in the sidecar's previz:entity customData
  8. atmosphere (volume-only) objects are OUT of the GLB and fully
     declared in JSON (glTF has no volumes — opaque-shell law)

Usage:
    blrun.sh --background --python scripts/export_previz_package.py -- \
        --scene scene_escape_v3_3 \
        --output output/previz_v3_4 \
        --package-id v3_4 \
        --name "Last Ride Out v3.4" \
        [--stills-dir /path/to/shot_jpgs] \
        [--usd-sidecar]

Kit laws baked in (session-20/21):
  - glTF export_cameras defaults to False — always go through
    blender_kit.export_gltf (sets it). A hand-rolled export ships a
    camera-less GLB and the review app silently loses shot framing.
  - glTF action keys are ABSOLUTE t = frame/fps (not (frame-1)/fps).
  - Time->frame convention (escape_lib): frame = round(t*FPS)+FRAME_START.
"""
from __future__ import annotations

import argparse
import datetime
import importlib
import json
import os
import re
import shutil
import struct
import sys
import subprocess

import bpy

from blender_kit import script_argv, atmo_objects

# module constant -> JSON story key (the audit's full inventory; a
# constant the module declares MUST land in the JSON or the gate fails).
# SHOTS_V3 is deliberately absent: its data lands in the top-level
# shots array (marker-bound ground truth), not in the story block.
STORY_SOURCES = [
    ("CAMS_V3", "cam_specs"),
    ("DIALOG", "dialog"),
    ("KNOCKDOWNS_V3", "knockdowns"),
    ("CHASE_FALLS_V3", "chase_falls"),
    ("MUZZLE_BURSTS_V3", "muzzle_bursts"),
    ("JEEP_X_V3", "jeep_weave"),
    ("_V3_SEG", "speed_profile"),
    ("BOARD", "board"),
    ("RUN_PARAMS", "run_params"),
    ("MOTION_POLICY", "motion_policy"),
    ("FLATNESS_POLICY", "flatness_policy"),
    ("LUNGE_V3", "lunge"),
    ("RB_FALLS", "rb_falls"),
    ("RB_KD", "rb_kd"),
    ("T_DRIVE", "t_drive"),
    ("BARRICADE_T_V3", "barricade_t"),
    ("BARRICADE_Y_V3", "barricade_y"),
    ("RUN_SPEED", "run_speed"),
    ("RUN_START_Y", "run_start_y"),
    ("TOTAL_FRAMES_V3", "total_frames"),
    ("HERO_MODE", "hero_mode"),
]

# scalar story keys reported in the USD sidecar but excluded from the
# parity intersection: the two LATE-ADDED scalars from the session-21
# hook extras — they ride on the same _collect_story_extras code path
# as chase_falls/run_params/motion_policy/flatness_policy, so if those
# collections landed, these did (the original hook-owned scalars like
# t_drive/barricade_* stay checked).
PARITY_SCALARS = {"run_speed", "run_start_y"}


def _marker_bindings(scene) -> dict[int, str]:
    """frame -> camera object name, from timeline markers (ground truth)."""
    return {m.frame: m.camera.name for m in scene.timeline_markers
            if m.camera is not None}


# ---------------------------------------------------------------------------
# GLB inspection helpers (fail-closed gates read the EXPORT, not the
# scene — session-23 law: the bug can be in the exported version)
# ---------------------------------------------------------------------------

def _glb_read(glb_path: str):
    """Parse a GLB -> (gltf_json, binary_blob)."""
    with open(glb_path, "rb") as f:
        data = f.read()
    if data[:4] != b"glTF":
        raise SystemExit(f"[pkg] FAIL: {glb_path} is not a GLB")
    clen, _ = struct.unpack("<II", data[12:20])
    gltf = json.loads(data[20:20 + clen])
    blob = data[20 + clen + 8:]
    return gltf, blob


def _glb_acc(gltf, blob, acc_idx: int):
    """Read a glTF accessor as a flat list of floats (VEC3/SCALAR)."""
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


def _glb_node_parent_map(gltf):
    """node index -> parent index (from children arrays; glTF has no
    'parent' property — the hierarchy lives in children[])."""
    parent = {}
    for i, n in enumerate(gltf.get("nodes", [])):
        for c in n.get("children", []):
            parent[c] = i
    return parent


def _glb_translation_track(gltf, blob, node_name: str):
    """(times, values Nx3) of the node's OWN action translation track.

    session-25 (V34-VERIFY F1): match by TARGET NODE first — belt
    adoption renames actions (*.001), which defeated the old
    node+"Action" name convention and silently skipped the 4 rider
    nodes from the gate-12 audit. Name convention is now only the
    tie-breaker for multi-anim nodes (gate 13 forbids those anyway)."""
    idx = next((i for i, n in enumerate(gltf.get("nodes", []))
                if n.get("name") == node_name), None)
    if idx is None:
        return None
    fallback = None
    for anim in gltf.get("animations", []):
        for ch in anim.get("channels", []):
            t = ch.get("target", {})
            if t.get("node") == idx and t.get("path") == "translation":
                s = anim["samplers"][ch["sampler"]]
                times = _glb_acc(gltf, blob, s["input"]).astype(float).ravel()
                vals = _glb_acc(gltf, blob, s["output"]).astype(float)
                if anim.get("name") == node_name + "Action":
                    return times, vals      # exact convention match wins
                if fallback is None:
                    fallback = (times, vals)
    return fallback


def _glb_scale_max(gltf, blob, node_name: str, t0: float, t1: float):
    """Max scale magnitude of the node's own action in [t0, t1] (an
    object that is scale-0 across a window is INVISIBLE there)."""
    import numpy as np
    idx = next((i for i, n in enumerate(gltf.get("nodes", []))
                if n.get("name") == node_name), None)
    if idx is None:
        return 1.0
    for anim in gltf.get("animations", []):   # target-first (session-25 F1)
        for ch in anim.get("channels", []):
            t = ch.get("target", {})
            if t.get("node") == idx and t.get("path") == "scale":
                s = anim["samplers"][ch["sampler"]]
                times = _glb_acc(gltf, blob, s["input"]).astype(float).ravel()
                vals = _glb_acc(gltf, blob, s["output"]).astype(float)
                m = (times >= t0) & (times <= t1)
                if not m.any():
                    m = np.ones(len(times), bool)
                return float(np.abs(vals[m]).max())
    return 1.0


def _glb_rider_audit(gltf, blob, fps: float, t_drive: float,
                     t_end: float) -> list[str]:
    """SESSION-23 EXPORT RIDER GATE (user: 'not just visually you can
    likely programmatically detect ... check the EXPORT version').

    In the treadmill staging (jeep world-fixed, BeltRoot streaming
    -dist(t)), any animated node that is NOT part of the jeep tree and
    holds a near-constant WORLD position near the jeep while the belt
    streams is RIDING -- it reads as 'attached to the jeep' (the
    settled-RB-corpse bug class: KD3 frozen at world -0.6 through
    S6b/S9/S11/S12b, 5 user comments). Cameras, aim targets, lights,
    the jeep tree, and scale-0 (invisible) objects are exempt.
    """
    import numpy as np
    nodes = gltf.get("nodes", [])
    if not nodes:
        return []
    belt_track = _glb_translation_track(gltf, blob, "BeltRoot")
    if belt_track is None:
        return []          # not a treadmill scene — gate not applicable
    belt_ts, belt_vs = belt_track

    # belt children set
    parent = _glb_node_parent_map(gltf)
    belt_idx = next(i for i, n in enumerate(nodes)
                    if n.get("name") == "BeltRoot")
    belt_children = set(nodes[belt_idx].get("children", []))

    def under_jeep(i):
        while i is not None:
            nm = nodes[i].get("name", "")
            if nm == "JeepRoot" or nm.startswith("Jeep."):
                return True
            i = parent.get(i)
        return False

    # sample the driving phase (post-drive, spread to t_end)
    samples = [t_drive + 2.0 + k * (t_end - t_drive - 4.0) / 7.0
               for k in range(8)]
    issues = []
    for n_i, node in enumerate(nodes):
        nm = node.get("name", "")
        if not nm:
            continue
        if (nm.startswith("CAM_") or nm.startswith("Aim.")
                or nm.startswith("FX.Dust") or nm == "BeltRoot"
                or nm.startswith("RB.") or nm.startswith("PS.")
                or under_jeep(n_i)):
            continue
        if "KHR_lights_punctual" in json.dumps(node):
            continue
        # world y: local (-glTF z) plus the belt offset IF the node
        # rides under BeltRoot (root-level nodes -- e.g. RB corpses
        # adopted... or NOT adopted -- are world-local)
        track = _glb_translation_track(gltf, blob, nm)
        if track is None:
            continue
        ts, vs = track
        if len(ts) < 4:
            continue
        tsf = ts.astype(float).ravel()
        is_belt_child = n_i in belt_children
        worlds = []
        ok = True
        for t in samples:
            if t < tsf[0] or t > tsf[-1]:
                ok = False
                break
            local_y = -float(np.interp(t, tsf, vs[:, 2]))
            if is_belt_child:
                belt_y = -float(np.interp(
                    t, belt_ts.astype(float).ravel(), belt_vs[:, 2]))
                worlds.append(local_y + belt_y)
            else:
                worlds.append(local_y)
        if not ok or not worlds:
            continue
        worlds = np.array(worlds)
        if np.any(np.abs(worlds) > 15.0):
            continue                     # not near the jeep — irrelevant
        if float(np.abs(np.diff(worlds)).max()) < 0.8:
            # near-constant world position while the belt streams:
            # check it is not simply invisible (scale-0 FX)
            smax = _glb_scale_max(gltf, blob, nm, samples[0], samples[-1])
            if smax < 0.05:
                continue
            issues.append(
                f"{nm}: rides the jeep (world y "
                f"{worlds[0]:+.1f}..{worlds[-1]:+.1f} constant while "
                f"belt streams {dist_span(belt_ts, belt_vs, samples):.0f} m)")
    return issues


def dist_span(belt_ts, belt_vs, samples) -> float:
    """How far the belt streams across the sample window."""
    import numpy as np
    tsf = belt_ts.astype(float).ravel()
    y0 = -float(np.interp(samples[0], tsf, belt_vs[:, 2]))
    y1 = -float(np.interp(samples[-1], tsf, belt_vs[:, 2]))
    return abs(y1 - y0)


# default radius for gate 14 (see _glb_prop_proximity_audit docstring
# for the calibration evidence)
PROP_PROXIMITY_MAX = 1.0


def _glb_prop_proximity_audit(gltf, blob, fps: float,
                              max_dist: float = PROP_PROXIMITY_MAX,
                              skip: tuple = (),
                              max_samples: int = 96) -> list[str]:
    """GATE 14 (session-26, kit law 110): PHANTOM-OFFSET detection on
    the EXPORT. Any animated node parented to a JOINT of a skin (a
    bone-carried prop: rifle, tool, shield...) must stay within
    max_dist of SOME joint of that same skin at every sampled frame
    of its animation window.

    The session-26 bug this gates: the rifle's carry keys were
    anchored against a wrapper snapshot read at the wrong frame --
    every key rode a phantom 1.88 m sprint offset and the gun floated
    ~2 m behind the gunner for f1-156 while gates 1-13 were all green
    (the aim placement AND the wrapper riding were each individually
    correct; only their COMPOSITION was wrong). Calibration on that
    broken export: legit torso carry measures <= ~0.7 m min-joint
    distance, the phantom measured >= 1.32 m at every carry frame,
    the aimed hold 0.02 m -- the 1.0 m default separates both ways.

    `skip`: scene-declared node names exempted (legitimately tethered
    or thrown props). Generic contract: no scene specifics in here.

    PERF: accessor tracks are pre-parsed ONCE (the naive per-call
    _glb_acc re-read made this gate take minutes); per sample time a
    single topological sweep composes ALL node world matrices, then
    prop-vs-joint distances are O(1) lookups.
    """
    import numpy as np
    nodes = gltf.get("nodes", [])
    if not nodes or not gltf.get("skins"):
        return []
    parent = _glb_node_parent_map(gltf)

    # ---- pre-parse every sampler ONCE (per animation channel) ----
    node_tracks = {}          # node -> {path: (times, vals)}
    for an in gltf.get("animations", []):
        for ch in an.get("channels", []):
            t = ch.get("target", {})
            ni = t.get("node")
            if ni is None:
                continue
            s = an["samplers"][ch["sampler"]]
            times = _glb_acc(gltf, blob, s["input"]).astype(
                float).ravel()
            vals = _glb_acc(gltf, blob, s["output"]).astype(float)
            node_tracks.setdefault(ni, {})[t.get("path")] = (times, vals)

    # joint node index -> skin index
    joint_skin = {}
    for si, sk in enumerate(gltf.get("skins", [])):
        for j in sk.get("joints", []):
            joint_skin[j] = si

    # ---- props under audit: animated + parent is a joint ----
    props = []
    for ni, tracks in node_tracks.items():
        pname = nodes[ni].get("name", "")
        if pname in skip or ni in joint_skin:
            continue            # joints themselves are not props
        pi = parent.get(ni)
        if pi is None or pi not in joint_skin:
            continue
        joints = gltf["skins"][joint_skin[pi]].get("joints", [])
        if len(joints) < 3:
            continue
        t0 = min(tr[0][0] for tr in tracks.values())
        t1 = max(tr[0][-1] for tr in tracks.values())
        props.append((ni, pname, joint_skin[pi], joints, t0, t1))
    if not props:
        print("[pkg] gate14: no bone-carried animated props (n/a)")
        return []

    # ---- topological order (parents before children) ----
    order, seen = [], set()

    def visit(i):
        stack, local_seen = [], set()
        p = parent.get(i)
        while p is not None and p not in seen:
            if p in local_seen:
                break                     # cycle guard (bad glTF)
            local_seen.add(p)
            stack.append(p)
            p = parent.get(p)
        for j in reversed(stack):
            if j not in seen:
                seen.add(j)
                order.append(j)
        if i not in seen:
            seen.add(i)
            order.append(i)

    t_min = min(pr[4] for pr in props)
    t_max = max(pr[5] for pr in props)
    for ni, _, _, joints, _, _ in props:
        visit(ni)                 # visit() closes over ALL ancestors
        for j in joints:
            visit(j)

    def quat_mat(R):
        x, y, z, w = R / np.linalg.norm(R)
        return np.array([
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w),
             2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z),
             2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w),
             1 - 2 * (x * x + y * y)]])

    def local_mat(ni, t):
        n = nodes[ni]
        T = np.array(n.get("translation", [0, 0, 0]), dtype=float)
        R = np.array(n.get("rotation", [0, 0, 0, 1]), dtype=float)
        S = np.array(n.get("scale", [1, 1, 1]), dtype=float)
        tr = node_tracks.get(ni, {})
        for path in ("translation", "rotation", "scale"):
            if path not in tr:
                continue
            times, vals = tr[path]
            if t <= times[0]:
                v = vals[0]
            elif t >= times[-1]:
                v = vals[-1]
            else:
                k = int(np.searchsorted(times, t))
                f = (t - times[k - 1]) / (times[k] - times[k - 1])
                v = vals[k - 1] + (vals[k] - vals[k - 1]) * f
                if path == "rotation":        # nlerp
                    v = v / np.linalg.norm(v)
            if path == "translation":
                T = v
            elif path == "rotation":
                R = v
            else:
                S = v
        M = np.eye(4)
        M[:3, :3] = quat_mat(R) * S
        M[:3, 3] = T
        return M

    # ---- sweep: compose all worlds at each needed t ----
    issues = []
    # dedupe sample times across props (carry windows overlap)
    ts = set()
    for ni, pname, si, joints, t0, t1 in props:
        n = max(8, min(max_samples, int((t1 - t0) * fps / 4) + 1))
        for t in np.linspace(t0, t1, n):
            ts.add(round(float(t), 4))
    ts = sorted(ts)

    worlds_at = {}            # t -> {node: world position}
    for t in ts:
        wm = {}
        for i in order:
            M = local_mat(i, t)
            p = parent.get(i)
            if p is not None and p in wm:
                M = wm[p] @ M
            wm[i] = M
        worlds_at[t] = {i: wm[i][:3, 3].copy() for i in wm}

    for ni, pname, si, joints, t0, t1 in props:
        n = max(8, min(max_samples, int((t1 - t0) * fps / 4) + 1))
        worst, worst_t = 0.0, 0.0
        for t in np.linspace(t0, t1, n):
            tt = round(float(t), 4)
            pw = worlds_at[tt][ni]
            best = min(float(np.linalg.norm(pw - worlds_at[tt][j]))
                       for j in joints)
            if best > worst:
                worst, worst_t = best, t
            if best > max_dist:
                issues.append(
                    f"{pname}: bone-carried prop is {best:.2f} m from "
                    f"every joint of skin {si} at t={t:.2f}s "
                    f"(> {max_dist} m — phantom offset: anchor/parent "
                    f"tracks composed wrong)")
                break
        if worst <= max_dist:
            print(f"[pkg] gate14 {pname}: worst {worst:.3f} m "
                  f"(max {max_dist}) PASS")
    return issues


def _latest_scene_module(scripts_dir: str) -> str | None:
    """Newest scene_escape_vN[.M].py by version number (ignores the
    unversioned scene_escape.py base module)."""
    import glob as _glob
    best, best_key = None, (-1, -1)
    for p in _glob.glob(os.path.join(scripts_dir, "scene_escape_v*.py")):
        base = os.path.basename(p)[:-3]
        m = re.fullmatch(r"scene_escape_v(\d+)(?:_(\d+))?", base)
        if not m:
            continue
        key = (int(m.group(1)), int(m.group(2) or 0))
        if key > best_key:
            best_key, best = key, base
    return best


def _r3(x):
    return round(float(x), 3)


def _collect_story(mod, fps: float, frame_start: int) -> dict:
    """Native JSON story collector — the module's full story inventory.

    Mirrors previz_usd_hook._collect_story_inline semantics (so the USD
    parity gate compares like with like) but reads numbers natively.
    """
    def frame_at(t):
        # escape_lib convention: frame = round(t * FPS) + FRAME_START
        return int(round(float(t) * fps)) + frame_start

    g = lambda name: getattr(mod, name, None)
    story: dict = {}

    dialog = g("DIALOG")
    if dialog is not None:
        story["dialog"] = [{"clip": str(d[0]), "onset_frame": int(d[1])}
                           for d in dialog]

    kd = g("KNOCKDOWNS_V3")
    if kd is not None:
        story["knockdowns"] = [{
            "id": str(k[0]), "t_hit": float(k[1]), "frame": frame_at(k[1]),
            "x_off": float(k[2]),
            "side": -1 if float(k[2]) <= 0 else 1,
            "style": str(k[3]),
        } for k in kd]

    cf = g("CHASE_FALLS_V3")
    if cf is not None:
        story["chase_falls"] = [{"chase_index": int(i), "t_hit": float(t),
                                 "frame": frame_at(t)}
                                for i, t in cf.items()]

    mb = g("MUZZLE_BURSTS_V3")
    if mb is not None:
        story["muzzle_bursts"] = [{"f0": int(m[0]), "f1": int(m[1]),
                                   "every_n": int(m[2])} for m in mb]

    jx = g("JEEP_X_V3")
    if jx is not None:
        story["jeep_weave"] = [{"t": float(j[0]), "x_off": float(j[1])}
                               for j in jx]

    seg = g("_V3_SEG")
    if seg is not None:
        story["speed_profile"] = [{"t0": float(s[0]), "t1": float(s[1]),
                                   "v0": float(s[2]), "v1": float(s[3])}
                                  for s in seg]

    board = g("BOARD")
    if board is not None:
        out = {}
        for name, entry in board.items():
            try:
                main, extra = entry[0], entry[1]
                out[str(name)] = {
                    "run_end": int(main[0]), "apex": int(main[1]),
                    "land": int(main[2]),
                    "seat_local": [_r3(x) for x in main[3]]
                    if main[3] is not None else None,
                    "yaw_end": float(main[4]), "pose_name": str(main[5]),
                    "offset": float(extra[0]) if extra else 0.0,
                }
            except Exception as e:
                print(f"[pkg] NOTE: BOARD[{name}] parse failed: {e}")
        story["board"] = out

    rp = g("RUN_PARAMS")
    if rp is not None:
        story["run_params"] = {
            str(k): {str(kk): (str(vv) if isinstance(vv, str) else float(vv))
                     for kk, vv in v.items()}
            for k, v in rp.items()}

    mp = g("MOTION_POLICY")
    if mp is not None:
        d = {}
        if mp.get("intended_static") is not None:
            d["intended_static"] = [str(x) for x in mp["intended_static"]]
        if mp.get("intended_subject_tree") is not None:
            d["intended_subject_tree"] = str(mp["intended_subject_tree"])
        story["motion_policy"] = d

    fp = g("FLATNESS_POLICY")
    if fp is not None:
        story["flatness_policy"] = {str(k): {"f0": int(v[0]), "f1": int(v[1])}
                                    for k, v in fp.items()}

    lu = g("LUNGE_V3")
    if lu is not None:
        d = {}
        for k, v in lu.items():
            if k == "y_offsets":
                d[k] = [{"t": float(y[0]), "y": float(y[1])} for y in v]
            elif isinstance(v, (int, float)):
                d[k] = float(v)
        story["lunge"] = d

    for attr, key in (("RB_FALLS", "rb_falls"), ("RB_KD", "rb_kd")):
        v = g(attr)
        if v is not None:
            story[key] = [str(x) if isinstance(x, str) else int(x)
                          for x in v]

    for attr, key, cast in (
            ("T_DRIVE", "t_drive", float),
            ("BARRICADE_T_V3", "barricade_t", float),
            ("BARRICADE_Y_V3", "barricade_y", float),
            ("RUN_SPEED", "run_speed", float),
            ("RUN_START_Y", "run_start_y", float),
            ("TOTAL_FRAMES_V3", "total_frames", int)):
        v = g(attr)
        if v is not None:
            story[key] = cast(v)

    hm = g("HERO_MODE")
    if hm is not None:
        story["hero_mode"] = str(hm)

    cams = g("CAMS_V3")
    if cams is not None:
        story["cam_specs"] = [{
            "name": str(c[0]),
            "loc0": [_r3(x) for x in c[1]],
            "loc1": [_r3(x) for x in c[2]],
            "lens_mm": float(c[3]),
            "aim": [_r3(x) for x in c[4]],
            "parent_jeep": bool(c[5]),
            "shake_amp": float(c[6]),
        } for c in cams]

    return story


def _collect_characters(scene, mod) -> list[dict]:
    """Characters registry: union of BOARD + RUN_PARAMS actors, identity
    colors from the built scene's CA.Body.<name> materials, boards_at =
    the BOARD land frame (when the actor actually boards)."""
    names = set()
    for attr in ("BOARD", "RUN_PARAMS"):
        d = getattr(mod, attr, None)
        if isinstance(d, dict):
            names.update(str(k) for k in d.keys())
    out = []
    for name in sorted(names):
        root = scene.objects.get(f"{name}.Root")
        color = None
        # capsule mode names materials CA.Body.<name>; UAL mode
        # Mat.UAL.<name> (session-23: HeroZed shipped color null)
        mat = bpy.data.materials.get(f"CA.Body.{name}") \
            or bpy.data.materials.get(f"Mat.UAL.{name}")
        if mat and mat.use_nodes:
            bsdf = next((n for n in mat.node_tree.nodes
                         if n.type == 'BSDF_PRINCIPLED'), None)
            if bsdf:
                c = bsdf.inputs["Base Color"].default_value
                color = [_r3(x) for x in c[:3]]
        elif mat:
            color = [_r3(x) for x in mat.diffuse_color[:3]]
        entry = {"name": name,
                 "root_object": root.name if root else None,
                 "identity_color": color,
                 # session-23: which hero system rendered this actor
                 # (ual = rigged skins; capsule = FK capsules). The
                 # review app surfaces it; gate 10 cross-checks skins.
                 "rig": str(getattr(mod, "HERO_MODE", "capsule"))}
        board = getattr(mod, "BOARD", None) or {}
        if name in board:
            try:
                entry["boards_at"] = int(board[name][0][2])  # land frame
            except Exception:
                pass
        out.append(entry)
    return out


def _collect_atmosphere(scene) -> list[dict]:
    """Atmosphere declaration for glTF-incompatible volume objects.

    These objects are EXCLUDED from the GLB (glTF has no volume
    materials — they bake to opaque shells, session-22 law) and
    declared here instead so web consumers can approximate them
    (e.g. exp fog with the volume's density + color)."""
    out = []
    for ob in atmo_objects(scene):
        entry = {"name": ob.name, "reason": "volume-only material"}
        try:
            bb = ob.bound_box
            mins = [_r3(min(c[i] for c in bb)) for i in range(3)]
            maxs = [_r3(max(c[i] for c in bb)) for i in range(3)]
            entry["bounds_min"] = mins
            entry["bounds_max"] = maxs
        except Exception:
            pass
        mat = ob.active_material
        if mat and mat.use_nodes:
            vol = next((n for n in mat.node_tree.nodes
                        if n.type == 'PRINCIPLED_VOLUME'), None)
            if vol:
                try:
                    entry["density"] = _r3(
                        vol.inputs["Density"].default_value)
                    entry["color"] = [_r3(c) for c in
                                       vol.inputs["Color"].default_value[:3]]
                except Exception:
                    pass
        out.append(entry)
    return out


def _collect_world(scene) -> dict:
    world = {"lights": []}
    if scene.world:
        try:
            if scene.world.use_nodes:
                bg = scene.world.node_tree.nodes.get("Background")
                if bg:
                    world["background_color"] = [
                        _r3(c) for c in bg.inputs["Color"].default_value[:3]]
                    world["background_strength"] = _r3(
                        bg.inputs["Strength"].default_value)
                    # SESSION-22 LAW: when a Nishita sky TEXTURE drives the
                    # background (scene_escape_v3_* dusk sky), the Color
                    # input's DEFAULT value (flat 0.8 gray) is meaningless
                    # — the link overrides it. A consumer that renders the
                    # flat color gets a ~2x-overexposed gray sky. Detect
                    # the sky node and export its parameters instead.
                    sky_link = next(
                        (l for l in bg.inputs["Color"].links
                         if l.from_node.type == 'TEX_SKY'), None)
                    if sky_link is not None:
                        sky = sky_link.from_node
                        import math as _math
                        # session-24: sky_type enum + air/dust densities
                        # drift across versions (5.x: NISHITA removed,
                        # dust_density gone) — read what EXISTS, export
                        # the REAL type, never hardcode "nishita".
                        _stype = getattr(sky, "sky_type", None)
                        _sky_type = {
                            'NISHITA': "nishita",
                            'MULTIPLE_SCATTERING': "multiple_scattering",
                            'SINGLE_SCATTERING': "single_scattering",
                            'PREETHAM': "preetham",
                            'HOSEK': "hosek",
                        }.get(_stype, _stype or "unknown")
                        world["sky"] = {
                            "type": _sky_type,
                            "sun_elevation_deg": _r3(_math.degrees(
                                sky.sun_elevation)),
                            "sun_rotation_deg": _r3(_math.degrees(
                                sky.sun_rotation)),
                            "air_density": _r3(getattr(sky, "air_density",
                                                       1.0)),
                            "dust_density": _r3(getattr(sky, "dust_density",
                                                        4.0)),
                            "strength": _r3(
                                bg.inputs["Strength"].default_value),
                        }
                        # the flat fallback is NOT the real background
                        # when a sky drives it — mark it clearly
                        world["background_color_note"] = (
                            "overridden by sky texture — use world.sky")
            else:
                world["background_color"] = [
                    _r3(c) for c in scene.world.color[:3]]
                world["background_strength"] = 1.0
        except Exception as e:
            print(f"[pkg] NOTE: world collection failed: {e}")
    for obj in scene.objects:
        if obj.type == 'LIGHT':
            ld = obj.data
            world["lights"].append({
                "name": obj.name, "type": str(ld.type),
                "energy": _r3(ld.energy),
                "color": [_r3(c) for c in ld.color[:3]],
            })
    return world


def _collect_actions(scene) -> list[dict]:
    """Actions manifest: every action in the file + which scene objects
    it drives (empty objects = orphaned/action on removed data)."""
    by_action: dict[str, list[str]] = {}
    for obj in scene.objects:
        ad = obj.animation_data
        if ad and ad.action:
            by_action.setdefault(ad.action.name, []).append(obj.name)
    out = []
    for act in bpy.data.actions:
        f0, f1 = act.frame_range
        out.append({"name": act.name,
                    "f0": int(round(f0)),
                    "f1": int(round(f1)),
                    "objects": sorted(by_action.get(act.name, []))})
    return sorted(out, key=lambda a: a["name"])


def _git_sha() -> str | None:
    try:
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                           capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            return r.stdout.strip()
    except Exception:
        pass
    return None


def _strip_usda_strings_comments(text: str) -> str:
    """Blank out quoted strings + # comments (keeps offsets) so brace
    scanning can't be fooled by braces inside values."""
    out = list(text)
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch == '"':
            j = i + 1
            while j < n:
                if text[j] == '\\':
                    j += 2
                    continue
                if text[j] == '"':
                    break
                j += 1
            for k in range(i, min(j + 1, n)):
                out[k] = ' '
            i = j + 1
        elif ch == '#':
            j = text.find('\n', i)
            j = n if j == -1 else j
            for k in range(i, j):
                out[k] = ' '
            i = j
        else:
            i += 1
    return ''.join(out)


def _usd_customdata_keys(usda_path: str) -> list[str]:
    """Top-level keys of the STAGE previz:entity customData in a .usda.

    Finds the previz:entity block that carries schema_version (the
    stage payload on /root — per-object payloads don't have it) and
    extracts its depth-1 keys with a brace scanner (strings/comments
    blanked so nested braces in values can't fool the depth count).
    """
    text = open(usda_path, "r", encoding="utf-8", errors="replace").read()
    stripped = _strip_usda_strings_comments(text)
    # usda writes the namespaced key "previz:entity" as a NESTED dict:
    #   dictionary previz = { dictionary entity = { ... } }
    # so match the inner entity block (schema_version discriminates the
    # stage payload from the per-object payloads, which lack it).
    for m in re.finditer(r"\bentity\s*=\s*\{", stripped):
        start = m.end() - 1
        depth = 0
        end = None
        for i in range(start, len(stripped)):
            if stripped[i] == '{':
                depth += 1
            elif stripped[i] == '}':
                depth -= 1
                if depth == 0:
                    end = i
                    break
        if end is None:
            continue
        block = stripped[start + 1:end]
        if "schema_version" not in block:
            continue  # per-object payload — keep scanning
        # depth of every char in the block interior (0 = top level)
        depths = []
        d = 0
        for ch in block:
            if ch == '{':
                depths.append(d)
                d += 1
            elif ch == '}':
                d -= 1
                depths.append(d)
            else:
                depths.append(d)
        keys = set()
        for km in re.finditer(r"([A-Za-z_][\w:\[\]]*)\s*(?==)", block):
            if depths[km.start(1)] == 0:
                keys.add(km.group(1))
        if keys:
            return sorted(keys)
    return []


def _export_usd_sidecar(scene, mod, scene_module_name: str,
                        out_path: str) -> None:
    """In-process USD export with the previz carrier hook (same kwargs
    as scripts/export_usd.py, animation ON)."""
    import sys
    sys_path = os.path.dirname(os.path.abspath(__file__))
    if sys_path not in sys.path:
        sys.path.insert(0, sys_path)
    import previz_usd_hook
    previz_usd_hook.register(scene_module_name=scene_module_name)
    # register() resets the cache — set it AFTER (the already-imported
    # module is the exact one the JSON collector read)
    previz_usd_hook.PrevizUSDHook._cached_scene_module = mod
    try:
        bpy.ops.wm.usd_export(
            filepath=out_path,
            export_animation=True,
            export_meshes=True, export_lights=True, export_cameras=True,
            export_curves=True, export_points=True, export_volumes=False,
            export_materials=True, export_hair=False, export_uvmaps=True,
            export_mesh_colors=True, export_normals=True,
            export_armatures=True, only_deform_bones=False,
            export_shapekeys=True, use_instancing=False,
            evaluation_mode='RENDER',
            generate_preview_surface=False, generate_materialx_network=False,
            export_textures=True, export_custom_properties=True,
            custom_properties_namespace="userProperties",
            author_blender_name=True,
            selected_objects_only=False, visible_objects_only=False,
            triangulate_meshes=False,
        )
    finally:
        previz_usd_hook.unregister()


def main() -> None:
    p = argparse.ArgumentParser(
        description="Export a previz review package (GLB + previz.json v2).")
    p.add_argument("--scene", required=True,
                   help="Scene module name (importable from scripts/).")
    p.add_argument("--output", required=True, help="Output directory.")
    p.add_argument("--package-id", required=True,
                   help="Stable package id for the review app (e.g. v3_4).")
    p.add_argument("--name", default=None, help="Human package name.")
    p.add_argument("--stills-dir", default=None,
                   help="Directory of shot_<ID>.jpg stills to copy in.")
    p.add_argument("--usd-sidecar", action="store_true",
                   help="Also export scene.usda (USD carrier) and run the "
                        "story parity gate against it.")
    p.add_argument("--allow-stale", action="store_true",
                   help="Skip the version-drift gate (DEBUG ONLY: export "
                        "an older scene module on purpose).")
    p.add_argument("--hero-rig", default=None,
                   choices=("capsule", "ual"),
                   help="Override the scene module's hero system BEFORE "
                        "build_scene (the v5 default is capsule; the "
                        "review package wants the RIGGED heroes -- pass "
                        "--hero-rig ual unless deliberately rolling back).")
    p.add_argument("--crowd-mode", default=None,
                   choices=("v3", "v6"),
                   help="Override the scene module's crowd engine BEFORE "
                        "build_scene (default: keep the scene module's "
                        "own CROWD_MODE, which is v3 -- the frozen "
                        "crowd_agents.py regression path). Pass "
                        "--crowd-mode v6 to build the crowd_v6 A/B "
                        "package from one tree (P2-12; v6 mode needs "
                        "STEP 1+ implemented to run).")
    args = p.parse_args(script_argv())

    # ---- 0. VERSION-DRIFT GATE (session-23: the app was served a "v3_4"----
    # package exported from scene_escape_v3_3 while the repo was at v5
    # -- two major versions of fixes (UAL rigged heroes, rifle, contact
    # grounding) never reached the reviewer because the export docstring
    # example said v3_3 and nobody re-checked. The reviewer's 'crappy
    # version' + 'rigged character falls back to cylinder' were 100%
    # this gap. Fail-closed unless explicitly allowed.
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    latest = _latest_scene_module(scripts_dir)
    if latest and args.scene != latest and not args.allow_stale:
        raise SystemExit(
            f"[pkg] FAIL: VERSION DRIFT -- exporting {args.scene} but "
            f"the newest scene module in {scripts_dir} is {latest}. "
            f"The review package must be built from the current scene "
            f"(or pass --allow-stale to export the old one on purpose "
            f"-- and say why in the package name).")
    if latest and args.scene != latest:
        print(f"[pkg] WARN: --allow-stale: exporting {args.scene} "
              f"(newest is {latest})", flush=True)

    # session-25: Blender does NOT add the --python script's dir to
    # sys.path in --background mode — the scene module import below
    # depends on it. Insert OURSELVES (cwd-independent; the daemonized
    # launcher chdirs to /).
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)

    print(f"[pkg] importing scene module: {args.scene}", flush=True)
    mod = importlib.import_module(args.scene)
    if args.hero_rig and getattr(mod, "HERO_MODE", None) != args.hero_rig:
        mod.HERO_MODE = args.hero_rig
        print(f"[pkg] hero rig override: HERO_MODE = {args.hero_rig}",
              flush=True)
        # re-run any module-level dispatch that captured the old value
        if hasattr(mod, "apply_hero_mode"):
            mod.apply_hero_mode(args.hero_rig)

    # v6 STEP 0 (DESIGN_crowd_v6.md §9 P2-12): crowd engine override,
    # mirroring --hero-rig. CROWD_MODE is read inside animate()'s
    # _run_crowd dispatcher (not at import), so setting it before
    # build_scene is sufficient; no module-level re-dispatch needed.
    if args.crowd_mode and getattr(mod, "CROWD_MODE", None) != args.crowd_mode:
        mod.CROWD_MODE = args.crowd_mode
        print(f"[pkg] crowd mode override: CROWD_MODE = {args.crowd_mode}",
              flush=True)
        # re-run any module-level dispatch that captured the old value
        if hasattr(mod, "apply_crowd_mode"):
            mod.apply_crowd_mode(args.crowd_mode)

    ctx = mod.build_scene()
    if hasattr(mod, "animate"):
        mod.animate(ctx, start_frame=1, n_frames=None)
    scene = ctx["scene"]
    fps = scene.render.fps
    f_start, f_end = scene.frame_start, scene.frame_end

    # ---- 0b. POOL-ACTION PURGE (session-25 law, the V5 'air dance'
    # RCA): glTF ACTIONS mode exports EVERY bpy.data.actions entry.
    # The UAL bake leaves the per-actor library POOLS (Sprint_Loop,
    # A_TPose, Pistol_*, Rifle_Aim source actions, ~188 full-rig
    # clips) alive via fake users — they all target the SAME actor
    # bones as the baked actions. In Blender they are inert (only the
    # ASSIGNED action evaluates), but glTF viewers that play every
    # clip (ours does) blend ~141 weight-1 actions per bone into mush:
    # garbled arm poses, the rifle riding a mushed hand = 'air dance'.
    # LAW: bake inputs are NOT export payload. Keep exactly the
    # actions ASSIGNED to objects (one-object-one-action contract) and
    # delete the rest. Purge BEFORE glTF export AND manifest collect.
    _assigned = set()
    for ob in bpy.data.objects:
        ad = ob.animation_data
        if ad and ad.action is not None:
            _assigned.add(ad.action.name)
    _pools = [a for a in bpy.data.actions if a.name not in _assigned]
    if _pools:
        _pool_names = sorted(a.name for a in _pools)
        for a in _pools:
            bpy.data.actions.remove(a)
        print(f"[pkg] pool-action purge: removed {len(_pools)} "
              f"unassigned actions (bake inputs, not payload)", flush=True)
        # re-run the orphan sweep so bindings/users clean up too
        try:
            bpy.data.orphans_purge(do_local_ids=True, do_recursive=True)
        except Exception as _e:  # noqa: BLE001
            print(f"[pkg] NOTE: post-purge orphan sweep failed: {_e}",
                  flush=True)
    _kept = sorted(a.name for a in bpy.data.actions)
    print(f"[pkg] actions kept (assigned-only): {len(_kept)}", flush=True)

    os.makedirs(args.output, exist_ok=True)
    glb_path = os.path.join(args.output, "scene.glb")

    # ---- 1. GLB via the kit helper (cameras=True is load-bearing) ----
    # Atmosphere (volume-only) objects are EXCLUDED — glTF has no volume
    # materials; they bake to opaque shells that blank shots (session-22
    # user-reported: S12a crane fully blocked by the Street.Mist shell).
    atmo = _collect_atmosphere(scene)
    atmo_names = {a["name"] for a in atmo}
    from blender_kit import export_gltf
    export_gltf(args, out_path=glb_path,
                exclude_objects=[ob for ob in scene.objects
                                 if ob.name in atmo_names])
    if atmo:
        print(f"[pkg] atmosphere excluded from GLB (declared in JSON): "
              f"{sorted(atmo_names)}", flush=True)

    # ---- 2. read the GLB (json + binary blob, for the fail-closed
    # gates — session-23: gates read the EXPORT, not the scene) ----
    gltf, glb_blob = _glb_read(glb_path)
    glb_node_names = {nd.get("name", "") for nd in gltf.get("nodes", [])}
    glb_cam_nodes = [nd.get("name", "") for nd in gltf.get("nodes", [])
                     if nd.get("camera") is not None]

    # ---- 3. previz.json schema 2.0 ----
    marks = _marker_bindings(scene)
    shots = []
    shots_table = getattr(mod, "SHOTS_V3", None) or getattr(mod, "SHOTS", [])
    for row in shots_table:
        sid, f0, f1, intent = row[0], row[1], row[2], row[3]
        cam = marks.get(f0)
        if cam is None:
            raise SystemExit(f"[pkg] FAIL: no timeline marker at f{f0} "
                             f"for shot {sid} — cannot bind a camera")
        if not cam.startswith("CAM_"):
            raise SystemExit(f"[pkg] FAIL: marker at f{f0} binds {cam!r} "
                             f"(expected a CAM_* object)")
        shots.append({"id": sid, "f0": f0, "f1": f1,
                      "intent": intent, "camera": cam})

    # camera map: built-scene optics + CAMS_V3 motion spec merge
    cams_spec = {c[0]: c for c in (getattr(mod, "CAMS_V3", None) or [])}
    cams_meta = {}
    for obj in scene.objects:
        if obj.type != 'CAMERA':
            continue
        cd = obj.data
        meta = {
            "lens_mm": _r3(cd.lens),
            "sensor_width_mm": _r3(cd.sensor_width),
            "sensor_fit": str(cd.sensor_fit),
            "clip_start_m": _r3(cd.clip_start),
            "clip_end_m": _r3(cd.clip_end),
            # lens shift (sensor-shift framing; 0 unless the scene sets it)
            "shift_x": _r3(cd.shift_x),
            "shift_y": _r3(cd.shift_y),
        }
        # TRACK_TO target (the exported Aim.* node the app re-aims with)
        for c in obj.constraints:
            if c.type == 'TRACK_TO' and c.target is not None:
                meta["aim_node"] = c.target.name
        if obj.parent is not None:
            meta["parent"] = obj.parent.name
        spec = cams_spec.get(obj.name)
        if spec is not None:
            meta.update({
                "loc0": [_r3(x) for x in spec[1]],
                "loc1": [_r3(x) for x in spec[2]],
                "aim": [_r3(x) for x in spec[4]],
                "parent_jeep": bool(spec[5]),
                "shake_amp": float(spec[6]),
            })
        cams_meta[obj.name] = meta

    story = _collect_story(mod, float(fps), int(f_start))
    characters = _collect_characters(scene, mod)
    world = _collect_world(scene)
    actions = _collect_actions(scene)

    previz = {
        "schema_version": "2.1",
        "package_id": args.package_id,
        "name": args.name or args.package_id,
        "scene_module": args.scene,
        "blender_version": bpy.app.version_string,
        "generated_at": datetime.datetime.now(datetime.timezone.utc)
                          .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "git_sha": _git_sha(),
        "fps": int(fps),
        "frame_start": int(f_start),
        "frame_end": int(f_end),
        "render_size": [int(scene.render.resolution_x),
                        int(scene.render.resolution_y)],
        "unit_scale": _r3(scene.unit_settings.scale_length) or 1.0,
        "up_axis": "Y_UP (glTF convention; Blender Z-up converted "
                   "by the exporter)",
        "shots": shots,
        "cameras": cams_meta,
        "characters": characters,
        "story": story,
        "world": world,
        "atmosphere": atmo,
        "actions": actions,
        "sfx_events": "sfx_events.json",
        "stills_pattern": "stills/shot_{id}.jpg",
    }

    # ---- 4. sfx events (module's own emitter, when present) ----
    if hasattr(mod, "emit_sfx_events"):
        mod.emit_sfx_events(ctx, args.output)
        sfx_path = os.path.join(args.output, "sfx_events.json")
        try:
            with open(sfx_path) as f:
                previz["n_sfx_events"] = len(
                    json.load(f).get("events", []))
        except Exception:
            previz["n_sfx_events"] = 0
        print(f"[pkg] sfx_events.json emitted", flush=True)

    # ---- 5. stills (optional copy) ----
    stills_present = []
    if args.stills_dir and os.path.isdir(args.stills_dir):
        stills_out = os.path.join(args.output, "stills")
        os.makedirs(stills_out, exist_ok=True)
        n = 0
        for s in shots:
            src = os.path.join(args.stills_dir, f"shot_{s['id']}.jpg")
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(stills_out,
                                               f"shot_{s['id']}.jpg"))
                stills_present.append(s["id"])
                n += 1
        previz["stills_present"] = stills_present
        print(f"[pkg] stills copied: {n}/{len(shots)}", flush=True)
        if n < len(shots):
            print(f"[pkg] WARN: {len(shots) - n} stills missing from "
                  f"{args.stills_dir}", flush=True)

    # ---- 6. USD sidecar + parity gate (optional) ----
    if args.usd_sidecar:
        usd_path = os.path.join(args.output, "scene.usda")
        print(f"[pkg] exporting USD sidecar (animation ON)…", flush=True)
        _export_usd_sidecar(scene, mod, args.scene, usd_path)
        previz["usd_sidecar"] = "scene.usda"
        usd_keys = _usd_customdata_keys(usd_path)
        # story keys as the USD carrier names them (shots/cameras live in
        # its story dict; the JSON keeps them structural + cam_specs)
        universe = set(story) | {"shots", "cameras"}
        usd_story_keys = sorted(set(usd_keys) & universe)
        missing = sorted(k for k in story
                         if k not in PARITY_SCALARS and k != "cam_specs"
                         and k not in usd_keys)
        checked = sorted((set(story) & set(usd_story_keys)) - PARITY_SCALARS)
        previz["usd_parity"] = {
            "status": "ok" if not missing else f"missing: {missing}",
            "checked_keys": checked,
            "usd_story_keys": usd_story_keys,
        }
        print(f"[pkg] USD sidecar: {os.path.getsize(usd_path)/1e6:.1f}MB, "
              f"story keys {len(usd_story_keys)}, parity "
              f"{'OK' if not missing else 'MISSING ' + str(missing)}",
              flush=True)

    json_path = os.path.join(args.output, "previz.json")
    with open(json_path, "w") as f:
        json.dump(previz, f, indent=1, sort_keys=True)
    print(f"[pkg] previz.json (schema 2.1): {len(shots)} shots, "
          f"{len(cams_meta)} cameras, {len(story)} story collections, "
          f"{len(characters)} characters, {len(actions)} actions, "
          f"{len(atmo)} atmosphere entries -> {json_path}", flush=True)

    # ---- 7. FAIL-CLOSED gates ----
    problems = []

    # gate 1: shot cameras in the GLB
    missing_cams = [s["camera"] for s in shots
                    if s["camera"] not in glb_cam_nodes]
    if len(gltf.get("cameras", [])) == 0 or missing_cams:
        problems.append(f"shot cameras missing from GLB: "
                        f"{missing_cams or 'ALL'}")

    # gate 2: aim targets in the GLB (app rebuilds TRACK_TO from them)
    missing_aims = [m["aim_node"] for m in cams_meta.values()
                    if "aim_node" in m and m["aim_node"] not in glb_node_names]
    if missing_aims:
        problems.append(f"aim target nodes missing from GLB: {missing_aims}")

    # gate 3: shot table contiguity + full span
    if shots[0]["f0"] != f_start or shots[-1]["f1"] != f_end:
        problems.append(f"shot table does not span f{f_start}–{f_end}")
    for i in range(1, len(shots)):
        if shots[i]["f0"] != shots[i - 1]["f1"] + 1:
            problems.append(f"shots not contiguous at {shots[i]['id']} "
                            f"(f{shots[i]['f0']} after "
                            f"f{shots[i-1]['f1']})")

    # gate 4: every DECLARED story constant landed in the JSON
    for attr, key in STORY_SOURCES:
        if getattr(mod, attr, None) is None:
            continue
        k = key or attr.lower()
        if k not in story:
            problems.append(f"module declares {attr} but JSON story is "
                            f"missing '{k}'")

    # gate 5: characters + root objects
    if not characters:
        problems.append("characters registry is empty")
    for ch in characters:
        if ch["root_object"] and ch["root_object"] not in scene.objects:
            problems.append(f"character {ch['name']}: root object "
                            f"{ch['root_object']} not in scene")

    # gate 6: actions manifest
    if not actions:
        problems.append("actions manifest is empty")

    # gate 7: USD parity
    if args.usd_sidecar and previz["usd_parity"]["status"] != "ok":
        problems.append(f"USD parity: {previz['usd_parity']['status']}")

    # gate 8: atmosphere objects are OUT of the GLB and fully declared
    # (volume-only materials bake to opaque shells — the S12a blank-shot
    # bug this gate exists to catch)
    leaked = sorted(n for n in atmo_names if n in glb_node_names)
    if leaked:
        problems.append(f"atmosphere objects leaked into GLB: {leaked}")
    for a in atmo:
        for field in ("bounds_min", "bounds_max", "density", "color"):
            if field not in a:
                problems.append(f"atmosphere {a['name']}: missing {field}")

    # gate 9 (session-23): render-hidden helpers are OUT of the GLB.
    # Blender ray-visibility (visible_camera/hide_render) is the scene's
    # own 'never in a render' declaration; the glTF exporter ignores
    # it, so physics hulls/emitters/proxy planes leak and show up in
    # the web review (user: collider 'doing its own drifting', emitter
    # 'following the jeep!', coplanar RB.Ground z-fighting the street).
    from blender_kit import render_hidden_objects
    hidden_names = {ob.name for ob in render_hidden_objects(scene)}
    leaked_helpers = sorted(n for n in hidden_names if n in glb_node_names)
    if leaked_helpers:
        problems.append(f"render-hidden objects leaked into GLB: "
                        f"{leaked_helpers}")

    # gate 10 (session-23): rigged heroes must arrive RIGGED. If the
    # built scene has ARMATURE objects driving meshes, the GLB must
    # carry skins — otherwise the heroes silently degraded to unskinned
    # meshes/capsules in the review (the user's P0: 'why is the rigged
    # character now fallback to cylinder again?').
    armatures = [ob for ob in scene.objects if ob.type == 'ARMATURE']
    if armatures:
        n_skins = len(gltf.get("skins", []))
        if n_skins == 0:
            problems.append(
                f"scene has {len(armatures)} armature(s) but the GLB "
                f"has NO skins — rigged characters were not exported "
                f"as skinned meshes")

    # gate 11 (session-23): crane/dolly cameras must actually MOVE in
    # the export. The v3.3 shake system keyed noise on the STATIC loc0
    # spec, overwriting the crane keys every 2 frames — S1a/S11/S12a/
    # S12b cranes froze at loc0 for the whole shot (user: 'i recall
    # there's some camera movement for this shot but here it is
    # fixed?'). A cam whose spec says loc0 != loc1 must show a
    # translation span >= 50% of the spec delta.
    for cname, spec in cams_spec.items():
        l0, l1 = spec[1], spec[2]
        dy = abs(l1[1] - l0[1]) + abs(l1[0] - l0[0]) + abs(l1[2] - l0[2])
        if dy < 1.0:
            continue                      # static cam — nothing to check
        track = _glb_translation_track(gltf, glb_blob, cname)
        if track is None:
            problems.append(f"{cname}: spec moves (loc0->loc1 delta "
                            f"{dy:.1f} m) but the GLB has NO translation "
                            f"track")
            continue
        ts_, vs_ = track
        span = (float(vs_[:, 0].max() - vs_[:, 0].min())
                + float(vs_[:, 1].max() - vs_[:, 1].min())
                + float(vs_[:, 2].max() - vs_[:, 2].min()))
        if span < 0.5 * dy:
            problems.append(f"{cname}: crane/dolly frozen in export "
                            f"(span {span:.2f} m < 50% of spec "
                            f"{dy:.2f} m) — shake-clobber class")

    # gate 12 (session-23): EXPORT RIDER AUDIT — no animated node may
    # hold a near-constant world position near the jeep while the belt
    # streams (the settled-RB-corpse rider class behind 5 user
    # comments). See _glb_rider_audit for the staging math.
    t_drive = story.get("t_drive")
    if t_drive is not None:
        rider_issues = _glb_rider_audit(gltf, glb_blob, float(fps),
                                        float(t_drive),
                                        float(f_end) / float(fps))
        problems.extend(rider_issues)

    # gate 13 (session-25): ONE-OBJECT-ONE-ACTION — no node in the
    # exported GLB may be targeted by more than one DISTINCT animation
    # (a multi-channel clip — translation+scale — legally targets the
    # same node twice; count DISTINCT animation indices, not channels).
    # The V5 'air dance' class: glTF ACTIONS mode had exported the UAL
    # library pools (188 full-rig clips), and a viewer that plays every
    # clip blended ~141 weight-1 actions per bone into pose mush
    # (garbled arms, rifle riding a mushed hand). The pool purge keeps
    # only ASSIGNED actions; this gate proves it on the EXPORT.
    _node_anim_ids: dict[int, set[int]] = {}
    for _ai, _an in enumerate(gltf.get("animations", [])):
        for _ch in _an.get("channels", []):
            _ni = _ch.get("target", {}).get("node")
            if _ni is not None:
                _node_anim_ids.setdefault(_ni, set()).add(_ai)
    _conflicts = {ni: ids for ni, ids in _node_anim_ids.items()
                  if len(ids) > 1}
    if _conflicts:
        _sample = "; ".join(
            f"{gltf['nodes'][ni].get('name', '?')}<-"
            f"{[gltf['animations'][i].get('name') for i in list(ids)[:3]]}"
            for ni, ids in list(_conflicts.items())[:6])
        problems.append(
            f"{len(_conflicts)} node(s) targeted by >1 distinct animation "
            f"(one-object-one-action violated — pool/blend leak): "
            f"{_sample}")

    # gate 14 (session-26, kit law 110): PHANTOM-OFFSET audit — any
    # bone-carried animated prop (child of a skin joint) must stay
    # within PROP_PROXIMITY_MAX of some joint of its owning skin at
    # every sampled frame. Validated on the session-26 broken export
    # (rifle 1.32+ m from all joints through the carry window — this
    # gate fires; the fixed export reads <= 0.7 m).
    problems.extend(
        _glb_prop_proximity_audit(gltf, blob, fps))

    print(f"[pkg] GLB check: cameras={len(gltf.get('cameras', []))} "
          f"cam_nodes={len(glb_cam_nodes)} "
          f"animations={len(gltf.get('animations', []))} "
          f"skins={len(gltf.get('skins', []))}", flush=True)
    if problems:
        for pb in problems:
            print(f"[pkg] FAIL: {pb}", flush=True)
        raise SystemExit("[pkg] EXPORT REJECTED — fix the problems above")
    print(f"[pkg] OK: all gates green "
          f"(cameras in GLB, aims in GLB, contiguous shots, "
          f"{len(story)} story collections, {len(characters)} characters, "
          f"{len(actions)} actions, {len(atmo)} atmosphere declared+excluded, "
          f"helpers excluded, "
          f"{len(gltf.get('skins', []))} skins"
          + (", USD parity ok" if args.usd_sidecar else "") + ")",
          flush=True)


if __name__ == "__main__":
    main()
