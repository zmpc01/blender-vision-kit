"""
crowd_look.py — the crowd-nav vision lane (s24, DESIGN_crowd_vision_s24.md).

The s41 crowd_obstacles bridge made crowd obstacles DECLARED; nothing
made them SEEABLE. This module is the vision surface for crowd
navigation/collision: ONE invocation renders purpose-built encodings
WITH the numbers beside them (the two-column law), from the SAME bytes
the engine consumes (D1 data-source law).

Modes (via blrun.sh --background --python scripts/crowd_look.py --):
  --navmap  pre-bake: "is my declaration RIGHT?" — top-down ortho of
            the loaded scene + rect overlays (walkable green, blocked
            red, destinations blue, spawns yellow) + gap/overlap/
            severance findings.
  --traj    post-bake: "did agents behave?" — trajectory pass +
            density pass (split-passes law) + full-resolution
            telemetry (reach_capacity, reach_ever, max penetration,
            displacement, jam centroid).

Verdict/exit table (machine-routable; --json written on EVERY exit):
  0  PASS | ENGINE_GAP_JAM (jam with authoring checks CLEAN — the O11c
     law: the engine has no path planning until upstream routing lands)
  2  REFUSED (teacher-grade: bad input schema, ambiguous cache chunk)
  3  AUTHORING_P1 (strangle severance, blocked∩spawn/destination,
     dest.point covered, agent-off-walkable)
  4  READINESS_FAIL (own output failed the overlay-visibility gate)

Laws this file implements (design refs in brackets): the two-input
contract [F1/N1 — --rects bridge-verbatim + --decls exact authoring
schema; IR {"min","max"} shape REFUSED]; grid-BFS severance [N3 —
strict <f/2 walls, 4-connected, <4-cell components discarded, ONE P1
row per severance]; the ghost rule [N4 — a slot is unspawned at t iff
XY == exact float32 (0.0, 0.0)]; full-resolution telemetry [F8 — the
≤64-tick subsample feeds POLYLINES only]; dual reach definitions with
the invariant reach_capacity ≤ reach_ever [F11]; runtime cache decode
probe [F9 — agent_count arm vs slot-derived arm, components ∈ {2,3}];
masked density [F7/N6 — tick 0 + ghosts excluded, decl rects masked,
bin = floor/4 anchored at the decls-union min corner].

THE CROSS-CHECK LAW (D5): tests/test_crowd_obstacles.py O11c/O11d keep
their INDEPENDENT pins of reach/penetration; this module derives the
same quantities from decls + cache. Two derivations, one invariant:
reach_capacity ≤ reach_ever. Definitional divergence is documented;
same-definition numeric divergence between the two files is a bug.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

CROWD_PREFIX = "KIT_ANNOT_crowd_"
# annotate.delete_annotation_layer sweeps objects (via the layer dict)
# + materials (KIT_ANNOT_mat_*) + curves/meshes (KIT_ANNOT_*) — every
# datablock crowd_look creates carries one of those prefixes, so the
# ONE purge regime covers this module too [F16].
Z_LIFT = 0.004                 # m — overlay z above the floor [F6]
DEFAULT_FLOOR = 1.0            # m — corridor floor (~2× r_max 0.38 + 0.24)
MARGIN_DEFAULT = 0.15          # m — the bridge's own DEFAULT_MARGIN
GHOST_PENALTY_WARN = 0.25      # fraction of ghost samples that earns a WARN

PALETTE = {                    # saturated opaque overlay palette [F14]
    "walkable": (0.15, 0.75, 0.20),
    "blocked":  (0.95, 0.08, 0.08),
    "dest":     (0.20, 0.35, 0.90),
    "spawn":    (0.95, 0.85, 0.10),
    "traj":     (0.10, 0.90, 0.85),
    "label":    (0.95, 0.85, 0.10),
}


class CrowdLookRefused(Exception):
    """Teacher-grade refusal (fail-closed, exit 2): the message names
    the exact problem AND the fix."""


# --------------------------------------------------------------------------- #
#  Input contracts (the two-input law, F1/N1)
# --------------------------------------------------------------------------- #

def _pair_of_pairs(b, what):
    """Validate an authoring-shape bound: [[minx,miny],[maxx,maxy]]."""
    ok = (isinstance(b, (list, tuple)) and len(b) == 2
          and all(isinstance(p, (list, tuple)) and len(p) == 2 for p in b)
          and all(isinstance(v, (int, float)) and not isinstance(v, bool)
                  for p in b for v in p))
    if not ok:
        # the IR emission shape {"min": [...], "max": [...]} is the
        # predicted confusion — refuse it BY NAME with the conversion.
        if isinstance(b, dict) and "min" in b and "max" in b:
            raise CrowdLookRefused(
                f"{what}: bounds are in the IR emission shape "
                f"{{'min': [...], 'max': [...]}} — crowd_look consumes the "
                f"AUTHORING shape. One-line conversion: "
                f"[[b['min'][0], b['min'][1]], [b['max'][0], b['max'][1]]]")
        raise CrowdLookRefused(
            f"{what}: bounds must be pair-of-pairs [[minx,miny],[maxx,maxy]] "
            f"(the authoring-dataclass shape); got {type(b).__name__}: "
            f"{str(b)[:120]}")
    x0, y0 = float(b[0][0]), float(b[0][1])
    x1, y1 = float(b[1][0]), float(b[1][1])
    if not (x1 > x0 and y1 > y0):
        raise CrowdLookRefused(f"{what}: degenerate/inverted bounds {b} "
                               f"(need maxx>minx, maxy>miny)")
    return (x0, y0, x1, y1)


def load_rects(path):
    """The bridge scan output VERBATIM: {'blocked': [...], 'report': [...]}.

    Only the pinned keys are validated (id/walkable_id/bounds on each
    blocked row); unknown keys pass through — these bytes flow into
    CrowdScene authoring unchanged."""
    try:
        with open(path) as f:
            data = json.load(f)
    except Exception as e:  # noqa: BLE001
        raise CrowdLookRefused(f"--rects {path}: unreadable JSON ({e}); "
                               f"produce it with crowd_obstacles.py scan --json")
    if not isinstance(data, dict) or not isinstance(data.get("blocked"), list):
        raise CrowdLookRefused(
            f"--rects {path}: expected the bridge scan output "
            f"{{'blocked': [...], 'report': [...]}} with a blocked LIST; "
            f"got {type(data).__name__}")
    out = []
    for i, r in enumerate(data["blocked"]):
        if not isinstance(r, dict) or not all(k in r for k in
                                              ("id", "walkable_id", "bounds")):
            raise CrowdLookRefused(
                f"--rects blocked[{i}]: needs id/walkable_id/bounds; got "
                f"{str(r)[:120]}")
        b = _pair_of_pairs(r["bounds"], f"--rects blocked[{i}] '{r['id']}'")
        out.append({"id": str(r["id"]), "walkable_id": str(r["walkable_id"]),
                    "bounds": b})
    return {"blocked": out, "report": data.get("report", [])}


_POP_KEYS = ("id", "radius_m")


def load_decls(path):
    """The CrowdScene authoring JSON (N1 exact schema; unknown keys
    IGNORED — the file is shared with real bake authoring; malformed
    PINNED keys REFUSED).

      {"walkables":    [{"id", "bounds"}],
       "destinations": [{"id", "walkable_id", "point":[x,y],
                         "capacity_bounds"}],
       "spawn_sources":[{"id", "walkable_id", "bounds", "start_tick"?}],
       "populations":  [{"id", "radius_m":[min,max]?}]}
    """
    try:
        with open(path) as f:
            data = json.load(f)
    except Exception as e:  # noqa: BLE001
        raise CrowdLookRefused(f"--decls {path}: unreadable JSON ({e})")
    if not isinstance(data, dict):
        raise CrowdLookRefused(f"--decls {path}: top level must be an object")
    d = {"walkables": [], "destinations": [], "spawn_sources": [],
         "populations": []}
    for w in data.get("walkables", []) or []:
        if not isinstance(w, dict) or not all(k in w for k in ("id", "bounds")):
            raise CrowdLookRefused(f"--decls walkable row needs id/bounds; "
                                   f"got {str(w)[:120]}")
        d["walkables"].append({"id": str(w["id"]),
                               "bounds": _pair_of_pairs(w["bounds"],
                                                        f"walkable '{w['id']}'")})
    for t in data.get("destinations", []) or []:
        for k in ("id", "walkable_id", "point", "capacity_bounds"):
            if not isinstance(t, dict) or k not in t:
                raise CrowdLookRefused(
                    f"--decls destination row needs id/walkable_id/point/"
                    f"capacity_bounds; got {str(t)[:120]}")
        p = t["point"]
        if not (isinstance(p, (list, tuple)) and len(p) >= 2 and
                all(isinstance(v, (int, float)) for v in p[:2])):
            raise CrowdLookRefused(f"destination '{t['id']}': point must be "
                                   f"[x, y]; got {str(p)[:80]}")
        d["destinations"].append({
            "id": str(t["id"]), "walkable_id": str(t["walkable_id"]),
            "point": (float(p[0]), float(p[1])),
            "bounds": _pair_of_pairs(t["capacity_bounds"],
                                     f"destination '{t['id']}' capacity")})
    for s in data.get("spawn_sources", []) or []:
        if not isinstance(s, dict) or not all(k in s for k in
                                              ("id", "walkable_id", "bounds")):
            raise CrowdLookRefused(f"--decls spawn row needs id/walkable_id/"
                                   f"bounds; got {str(s)[:120]}")
        d["spawn_sources"].append({
            "id": str(s["id"]), "walkable_id": str(s["walkable_id"]),
            "bounds": _pair_of_pairs(s["bounds"], f"spawn '{s['id']}'")})
    for p_ in data.get("populations", []) or []:
        if not isinstance(p_, dict):
            raise CrowdLookRefused(f"--decls population row must be an "
                                   f"object; got {str(p_)[:80]}")
        row = {"id": str(p_.get("id", f"pop{len(d['populations'])}"))}
        if "radius_m" in p_:
            r = p_["radius_m"]
            if not (isinstance(r, (list, tuple)) and len(r) == 2 and
                    all(isinstance(v, (int, float)) for v in r) and r[1] > 0):
                raise CrowdLookRefused(
                    f"population '{row['id']}': radius_m must be [min, max] "
                    f"with max > 0 (the per-population distributions field); "
                    f"got {str(r)[:80]}")
            row["radius_m"] = (float(r[0]), float(r[1]))
        d["populations"].append(row)
    return d


def corridor_floors(decls, override=None):
    """Distinct corridor floors (N1): floor_p = 2·radius_m[1] + 0.24 per
    population (reproduces 1.0 at r_max 0.38), deduped; --corridor-floor
    overrides. Returns [(floor, provenance_str)]."""
    if override is not None:
        return [(float(override), "--corridor-floor override")]
    if not decls["populations"]:
        return [(DEFAULT_FLOOR,
                 f"default (no populations declared; ~2×r_max 0.38 + 0.24)")]
    out = []
    for p in decls["populations"]:
        if "radius_m" in p:
            f = round(2.0 * p["radius_m"][1] + 0.24, 4)
            out.append((f, f"population '{p['id']}': "
                           f"2·radius_m[1]={p['radius_m'][1]:.3f} + 0.24"))
    return out or [(DEFAULT_FLOOR, "default (populations carry no radius_m)")]


# --------------------------------------------------------------------------- #
#  Geometry: gaps, overlaps, severance (F3/N3, F5/N6)
# --------------------------------------------------------------------------- #

def _as_flat(b):
    """Accept BOTH bound shapes (flat 4-tuple from the loaders, raw
    pair-of-pairs from tests/fixtures) → flat (x0, y0, x1, y1)."""
    if len(b) == 4 and all(isinstance(v, (int, float)) for v in b):
        return (float(b[0]), float(b[1]), float(b[2]), float(b[3]))
    return _pair_of_pairs(b, "rect")


def _norm_decls(decls):
    """Normalize a decls dict that may arrive RAW (fixture/authoring
    shape: pair-of-pairs bounds, capacity_bounds key) into the loader
    shape (flat bounds, bounds key). Idempotent on loader output."""
    out = {"walkables": [], "destinations": [], "spawn_sources": [],
           "populations": list(decls.get("populations", []))}
    for w in decls.get("walkables", []):
        out["walkables"].append({"id": w["id"],
                                 "bounds": _as_flat(w["bounds"])})
    for t in decls.get("destinations", []):
        out["destinations"].append({
            "id": t["id"], "walkable_id": t["walkable_id"],
            "point": tuple(t["point"]) if not isinstance(t["point"], tuple)
            else t["point"],
            "bounds": _as_flat(t.get("bounds", t.get("capacity_bounds")))})
    for s in decls.get("spawn_sources", []):
        out["spawn_sources"].append({"id": s["id"],
                                     "walkable_id": s["walkable_id"],
                                     "bounds": _as_flat(s["bounds"])})
    return out


def _rect_gap(a, b):
    """Edge-to-edge XY gap between two AABBs (0.0 if overlapping)."""
    dx = max(a[0] - b[2], b[0] - a[2], 0.0)
    dy = max(a[1] - b[3], b[1] - a[3], 0.0)
    return math.hypot(dx, dy)


def _point_in_rect(p, r):
    return (r[0] <= p[0] <= r[2]) and (r[1] <= p[1] <= r[3])


def gap_findings(blocked, decls, floor):
    """Every rect-vs-rect and rect-vs-walkable-boundary edge gap BELOW the
    floor → WARN rows with coordinates. Gap == 0 is reported as a seam /
    wallhug (the bridge's own happy path — WARN, never P1 [F3])."""
    blocked = [{**r, "bounds": _as_flat(r["bounds"])} for r in blocked]
    decls = _norm_decls(decls)
    rows = []
    ws = {w["id"]: w["bounds"] for w in decls["walkables"]}
    for i in range(len(blocked)):
        for j in range(i + 1, len(blocked)):
            a, b = blocked[i], blocked[j]
            g = _rect_gap(a["bounds"], b["bounds"])
            if g < floor:
                kind = "adjacent-seam" if g == 0.0 else "rect-rect-gap"
                rows.append({"class": "WARN", "type": kind,
                             "gap_m": round(g, 4), "floor_m": floor,
                             "ids": [a["id"], b["id"]],
                             "at": [round((max(a["bounds"][0], b["bounds"][0])
                                           + min(a["bounds"][2], b["bounds"][2])) / 2, 3),
                                    round((max(a["bounds"][1], b["bounds"][1])
                                           + min(a["bounds"][3], b["bounds"][3])) / 2, 3)]})
    for r in blocked:
        wb = ws.get(r["walkable_id"])
        if wb is None:
            continue  # out-of-walkable is the refusal class, reported elsewhere
        # distance from the rect to each walkable boundary edge
        bx0, by0, bx1, by1 = r["bounds"]
        gaps = {"west": bx0 - wb[0], "south": by0 - wb[1],
                "east": wb[2] - bx1, "north": wb[3] - by1}
        for edge, g in gaps.items():
            if 0.0 <= g < floor:
                rows.append({"class": "WARN",
                             "type": "wallhug" if g == 0.0 else "rect-boundary-gap",
                             "gap_m": round(g, 4), "floor_m": floor,
                             "edge": edge, "ids": [r["id"], r["walkable_id"]],
                             "at": [round(bx0 if edge == "west" else
                                          (bx1 if edge == "east" else
                                           (bx0 + bx1) / 2), 3),
                                    round(by0 if edge == "south" else
                                          (by1 if edge == "north" else
                                           (by0 + by1) / 2), 3)]})
    return rows


def overlap_findings(blocked, decls):
    """The F5/N6 overlap class — P1 with both ids and coordinates:
    blocked ∩ spawn bounds, blocked ∩ destination capacity bounds, or
    dest.point inside a blocked rect (a rect can cover the goal point
    while missing the capacity box)."""
    blocked = [{**r, "bounds": _as_flat(r["bounds"])} for r in blocked]
    decls = _norm_decls(decls)
    rows = []
    for r in blocked:
        bx = r["bounds"]
        for s in decls["spawn_sources"]:
            if _rects_overlap(bx, s["bounds"]):
                rows.append({"class": "P1", "type": "exit-covered",
                             "blocked": r["id"], "decl": s["id"],
                             "at": [round((max(bx[0], s["bounds"][0]) +
                                           min(bx[2], s["bounds"][2])) / 2, 3),
                                    round((max(bx[1], s["bounds"][1]) +
                                           min(bx[3], s["bounds"][3])) / 2, 3)]})
        for t in decls["destinations"]:
            if _rects_overlap(bx, t["bounds"]) or _point_in_rect(t["point"], bx):
                rows.append({"class": "P1", "type": "declared-unreachable",
                             "blocked": r["id"], "decl": t["id"],
                             "at": [round(t["point"][0], 3),
                                    round(t["point"][1], 3)]})
    return rows


def _rects_overlap(a, b):
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


def severance_and_reachability(blocked, decls, floors):
    """The N3 grid-BFS spec, ONE implementation for CL1+CL2.

    Per walkable, per distinct floor: cell = floor/4; grid anchored at
    floor(min/cell)·cell spanning the walkable bounds + one ring; a cell
    is WALL iff the Euclidean distance from its center to the nearest
    blocked rect (closed AABB, rects matched by walkable_id) is STRICTLY
    below floor/2 (gap == floor stays passable); FREE iff the center is
    inside the walkable bounds (NO boundary erosion — rect-vs-boundary
    gaps are the WARN class); 4-connected components; components < 4
    cells discarded as rasterization noise; SEVERED iff ≥ 2 surviving
    components → ONE P1 row. Reachability on the same graph: each spawn
    must reach ≥ 1 destination component (dest.point snapped to the
    nearest FREE cell; snap distance > floor ⇒ declared-unreachable).
    """
    p1_rows = []
    info = {}
    decls = _norm_decls(decls)
    for w in decls["walkables"]:
        wrects = [_as_flat(r["bounds"])
                  for r in blocked if r["walkable_id"] == w["id"]]
        for floor, prov in floors:
            cell = floor / 4.0
            (wx0, wy0, wx1, wy1) = w["bounds"]
            gx0 = math.floor(wx0 / cell) * cell - cell
            gy0 = math.floor(wy0 / cell) * cell - cell
            nx = int(math.ceil((wx1 - gx0) / cell)) + 1
            ny = int(math.ceil((wy1 - gy0) / cell)) + 1
            free = {}
            for iy in range(ny):
                for ix in range(nx):
                    cx, cy = gx0 + (ix + 0.5) * cell, gy0 + (iy + 0.5) * cell
                    if not (wx0 <= cx <= wx1 and wy0 <= cy <= wy1):
                        continue
                    d = min(_rect_point_dist((cx, cy), rb) for rb in wrects) \
                        if wrects else float("inf")
                    if d >= floor / 2.0:          # STRICT (N3)
                        free[(ix, iy)] = True
            # 4-connected components, <4-cell noise discarded
            comp_id, comps = {}, []
            for start in sorted(free):
                if start in comp_id:
                    continue
                cid = len(comps)
                stack, cells = [start], []
                comp_id[start] = cid
                while stack:
                    c = stack.pop()
                    cells.append(c)
                    for dx_, dy_ in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        n = (c[0] + dx_, c[1] + dy_)
                        if n in free and n not in comp_id:
                            comp_id[n] = cid
                            stack.append(n)
                if len(cells) >= 4:
                    comps.append(cells)
                else:
                    for c in cells:
                        del comp_id[c]
            key = (w["id"], round(floor, 3))
            info[key] = {"components": len(comps),
                         "cells": [len(c) for c in comps],
                         "floor_m": floor, "provenance": prov}
            if len(comps) >= 2:
                # frontier rects: rects with WALL cells adjacent to ≥ 2 comps
                frontier = _frontier_rects(wrects, comps, free, comp_id,
                                           gx0, gy0, nx, ny, cell, floor)
                p1_rows.append({
                    "class": "P1", "type": "walkable-severed",
                    "walkable": w["id"], "floor_m": round(floor, 3),
                    "components": len(comps),
                    "component_cells": [len(c) for c in comps],
                    "frontier_rects": frontier,
                    "provenance": prov})
                continue
            if comps:
                members = set(comp_id.values())
                comp_of = {c: comp_id[c] for c in comp_id}

                def snap(px, py):
                    ix = int((px - gx0) / cell - 0.5 + 0.5)
                    iy = int((py - gy0) / cell - 0.5 + 0.5)
                    best, bd = None, float("inf")
                    for rix in range(max(0, ix - 2), min(nx, ix + 3)):
                        for riy in range(max(0, iy - 2), min(ny, iy + 3)):
                            if (rix, riy) in comp_of:
                                cx = gx0 + (rix + 0.5) * cell
                                cy = gy0 + (riy + 0.5) * cell
                                d = math.hypot(cx - px, cy - py)
                                if d < bd:
                                    best, bd = (rix, riy), d
                    return best, bd
                dest_cells = {}
                for t in decls["destinations"]:
                    if t["walkable_id"] != w["id"]:
                        continue
                    c, d = snap(t["point"][0], t["point"][1])
                    if c is None or d > floor:
                        p1_rows.append({"class": "P1",
                                        "type": "declared-unreachable",
                                        "walkable": w["id"], "decl": t["id"],
                                        "at": [round(t["point"][0], 3),
                                               round(t["point"][1], 3)],
                                        "reason": f"no FREE cell within "
                                                  f"{floor:.2f} m of the "
                                                  f"destination point"})
                    else:
                        dest_cells[t["id"]] = comp_of[c]
                for s in decls["spawn_sources"]:
                    if s["walkable_id"] != w["id"]:
                        continue
                    c, d = snap((s["bounds"][0] + s["bounds"][2]) / 2,
                                (s["bounds"][1] + s["bounds"][3]) / 2)
                    if c is None or d > floor:
                        p1_rows.append({"class": "P1",
                                        "type": "spawn-stranded",
                                        "walkable": w["id"], "decl": s["id"],
                                        "reason": "spawn center has no FREE "
                                                  "cell on its walkable"})
                        continue
                    sc = comp_of[c]
                    reach = [tid for tid, dc in dest_cells.items()
                             if dc == sc]
                    if dest_cells and not reach:
                        p1_rows.append({
                            "class": "P1", "type": "no-spawn-dest-path",
                            "walkable": w["id"], "decl": s["id"],
                            "reason": f"spawn component reaches none of "
                                      f"{sorted(dest_cells)} at floor "
                                      f"{floor:.2f} m"})
    return p1_rows, info


def _rect_point_dist(p, r):
    """Euclidean distance from a point to a closed AABB (0 if inside)."""
    dx = max(r[0] - p[0], 0.0, p[0] - r[2])
    dy = max(r[1] - p[1], 0.0, p[1] - r[3])
    return math.hypot(dx, dy)


def _frontier_rects(wrects, comps, free, comp_id, gx0, gy0, nx, ny, cell,
                    floor):
    """Rects whose WALL ring touches ≥ 2 surviving components (the cut's
    culprits)."""
    if len(comps) < 2:
        return []
    touching = {i: set() for i in range(len(comps))}
    for (ix, iy), cid in comp_id.items():
        for dx_, dy_ in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1),
                         (1, -1), (-1, 1)):
            n = (ix + dx_, iy + dy_)
            if n in free and comp_id.get(n) != cid:
                touching[cid].add(n)
                touching[comp_id[n]].add((ix, iy))
    out = []
    for ri, rb in enumerate(wrects):
        seen = set()
        for (ix, iy) in free:
            cx, cy = gx0 + (ix + 0.5) * cell, gy0 + (iy + 0.5) * cell
            if _rect_point_dist((cx, cy), rb) <= floor / 2.0 + cell * 0.5:
                seen.add(comp_id.get((ix, iy)))
        if len({s for s in seen if s is not None}) >= 2:
            out.append(f"rect[{ri}]")
    return out


# --------------------------------------------------------------------------- #
#  Cache decode + telemetry (F9/N4, F8/F11/F18)
# --------------------------------------------------------------------------- #

def decode_positions(rng):
    """Decode a Cache.read_range dict into (ticks, agents, 2) float32 XY.

    Runtime probe [F9]: if the chunk carries 'agent_count' use it and
    derive components = floats/4 // (tick_count·agent_count) ∈ {2,3}
    (XY of a 3-float triple — the pinned wheel forces z=0.0); else
    derive the slot count per the O11 pattern (2-component chunk).
    Ambiguous chunks are REFUSED, never guessed."""
    import numpy as np
    for k in ("position", "tick_count"):
        if k not in rng:
            raise CrowdLookRefused(f"cache chunk missing '{k}' — not a "
                                   f"Cache.read_range dict")
    raw = rng["position"]
    ticks = int(rng["tick_count"])
    if ticks <= 0 or len(raw) % 4:
        raise CrowdLookRefused(f"ambiguous cache chunk: tick_count={ticks}, "
                               f"position bytes={len(raw)}")
    n_f32 = len(raw) // 4
    ac = rng.get("agent_count")
    if ac is not None and int(ac) > 0:
        n_agents = int(ac)
        if n_f32 % (ticks * n_agents):
            raise CrowdLookRefused(
                f"ambiguous cache chunk: {n_f32} floats not divisible by "
                f"tick_count({ticks}) × agent_count({n_agents})")
        comp = n_f32 // (ticks * n_agents)
        if comp not in (2, 3):
            raise CrowdLookRefused(
                f"ambiguous cache chunk: {comp} floats/agent (expected 2 or "
                f"3) — the wheel format changed; update the decoder probe")
        pos = np.frombuffer(raw, dtype=np.float32).reshape(
            ticks, n_agents, comp)[..., :2].copy()
        return pos, {"agents": n_agents, "components": comp, "source": "agent_count"}
    slots = n_f32 // (2 * ticks)
    if slots == 0 or n_f32 % (2 * ticks):
        raise CrowdLookRefused(
            f"ambiguous cache chunk: {n_f32} floats with tick_count={ticks} "
            f"does not decompose into (ticks, slots, 2) — and the chunk "
            f"carries no agent_count to probe")
    pos = np.frombuffer(raw, dtype=np.float32).reshape(ticks, slots, 2)
    return pos, {"agents": slots, "components": 2, "source": "slot-derived"}


def ghost_mask(pos):
    """The N4 ghost rule: a slot is UNSPAWNED at tick t iff its XY equals
    the exact float32 zero pair (0.0, 0.0). Returns a valid mask
    (ticks, agents) — True means a real sample."""
    import numpy as np
    return ~((pos[..., 0] == np.float32(0.0)) &
             (pos[..., 1] == np.float32(0.0)))


def trajectory_telemetry(pos, decls, blocked, floor,
                         margin=MARGIN_DEFAULT):
    """Full-resolution telemetry [F8/F18] — pos is the DECODED array; all
    statistics compute on every valid sample (ghost-filtered [N4]).

    Returns {reach_capacity, reach_ever, per_destination, 
             max_penetration_m, median_displacement_m, ghosts_frac,
             invariant_ok, n_agents, ticks}. The invariant
    reach_capacity ≤ reach_ever is checked here and reported; the
    battery asserts it [F11]."""
    import numpy as np
    blocked = [{**r, "bounds": _as_flat(r["bounds"])} for r in blocked]
    decls = _norm_decls(decls)
    ticks, n_agents = pos.shape[0], pos.shape[1]
    valid = ghost_mask(pos)
    ghosts_frac = float((~valid).mean()) if valid.size else 0.0

    # reach_capacity: final cache tick ∩ any destination capacity bounds
    # ("final tick" = the CACHE tick grid [F19], not scene frame_end)
    reach_cap_ids = set()
    per_dest = {}
    for t in decls["destinations"]:
        b = t["bounds"]
        last = pos[-1]                       # (agents, 2)
        lastv = valid[-1]
        inside = ((last[:, 0] >= b[0]) & (last[:, 0] <= b[2]) &
                  (last[:, 1] >= b[1]) & (last[:, 1] <= b[3]) & lastv)
        ids = set(np.nonzero(inside)[0].tolist())
        per_dest[t["id"]] = len(ids)
        reach_cap_ids |= ids

    # reach_ever: ANY valid tick within dest.point ± corridor (the
    # O11c-style threshold, DERIVED from decls — not a hardcoded 6.0)
    reach_ever_ids = set()
    for t in decls["destinations"]:
        px, py = t["point"]
        hx = hy = floor  # the corridor floor is the honest threshold band
        box = (px - hx, py - hy, px + hx, py + hy)
        inside = ((pos[..., 0] >= box[0]) & (pos[..., 0] <= box[2]) &
                  (pos[..., 1] >= box[1]) & (pos[..., 1] <= box[3]) & valid)
        reach_ever_ids |= set(np.nonzero(inside.any(axis=0))[0].tolist())

    # max penetration into blocked CORES (rect shrunk by the bridge's
    # margin — the O11d formula, generalized to N rects)
    max_pen = 0.0
    for r in blocked:
        b = r["bounds"]
        x0, y0, x1, y1 = b[0] + margin, b[1] + margin, b[2] - margin, b[3] - margin
        if x1 <= x0 or y1 <= y0:
            continue
        dx = np.minimum(pos[..., 0] - x0, x1 - pos[..., 0])
        dy = np.minimum(pos[..., 1] - y0, y1 - pos[..., 1])
        inside = (dx > 0) & (dy > 0) & valid
        if inside.any():
            max_pen = max(max_pen, float(np.minimum(dx, dy)[inside].max()))

    # median displacement (valid at both ends)
    disp = []
    first_v = valid[0]
    last_v = valid[-1]
    both = first_v & last_v
    if both.any():
        d = np.linalg.norm(pos[-1][both] - pos[0][both], axis=1)
        disp = [float(np.median(d))]

    rc, re_ = len(reach_cap_ids), len(reach_ever_ids)
    return {"n_agents": int(n_agents), "ticks": int(ticks),
            "ghosts_frac": round(ghosts_frac, 4),
            "reach_capacity": rc, "reach_ever": re_,
            "per_destination": per_dest,
            "max_penetration_m": round(max_pen, 4),
            "median_displacement_m": (round(disp[0], 4) if disp else None),
            "invariant_ok": bool(rc <= re_)}


# --------------------------------------------------------------------------- #
#  Density (F7/N6) — host math; the Pillow composite is Blender-side
# --------------------------------------------------------------------------- #

def density_histogram(pos, decls, floor, bin_size=None, blocked_bounds=None):
    """Per-agent-normalized occupancy [F7/N6]: full tick range, tick 0
    EXCLUDED (spawn burst), ghost slots EXCLUDED [N4], decl spawn +
    destination-capacity rects MASKED. Bin = floor/4 anchored at the
    decls-union min corner. Returns the masked histogram, extent, the
    jam centroid (masked argmax, world xy) and the sample denominator."""
    import numpy as np
    valid = ghost_mask(pos)[1:]          # exclude tick 0
    pts = pos[1:][valid]                 # (N, 2)
    if pts.shape[0] == 0:
        return {"hist": None, "extent": None, "jam_centroid": None,
                "denominator": 0}
    bs = bin_size or (floor / 4.0)
    decls = _norm_decls(decls)
    blocked_bounds = [_as_flat(b) for b in (blocked_bounds or [])]
    anchors = ([w["bounds"] for w in decls["walkables"]] +
               [t["bounds"] for t in decls["destinations"]] +
               [s["bounds"] for s in decls["spawn_sources"]] +
               blocked_bounds)
    ax = min(a[0] for a in anchors)
    ay = min(a[1] for a in anchors)
    bx = max(a[2] for a in anchors)
    by = max(a[3] for a in anchors)
    nx = max(1, int(math.ceil((bx - ax) / bs)))
    ny = max(1, int(math.ceil((by - ay) / bs)))
    H, _, _ = np.histogram2d(pts[:, 0], pts[:, 1],
                             bins=[nx, ny],
                             range=[[ax, ax + nx * bs], [ay, ay + ny * bs]])
    H = H / max(1, pos.shape[1])         # per-agent normalization
    # mask decl rects (spawn bounds + destination capacity bounds)
    Hm = H.copy()
    for r in ([s["bounds"] for s in decls["spawn_sources"]] +
              [t["bounds"] for t in decls["destinations"]]):
        ix0 = max(0, int((r[0] - ax) / bs))
        iy0 = max(0, int((r[1] - ay) / bs))
        ix1 = min(nx, int(math.ceil((r[2] - ax) / bs)))
        iy1 = min(ny, int(math.ceil((r[3] - ay) / bs)))
        Hm[ix0:ix1, iy0:iy1] = 0.0
    peak_idx = np.unravel_index(np.argmax(Hm), Hm.shape)
    centroid = None
    if Hm[peak_idx] > 0:
        centroid = (round(ax + (peak_idx[0] + 0.5) * bs, 3),
                    round(ay + (peak_idx[1] + 0.5) * bs, 3))
    return {"hist": Hm, "extent": (ax, ay, nx, ny, bs),
            "jam_centroid": centroid,
            "peak_per_agent": round(float(Hm[peak_idx]), 4),
            "denominator": int(pts.shape[0])}


# --------------------------------------------------------------------------- #
#  Blender side (imported lazily — the host core runs bpy-free)
# --------------------------------------------------------------------------- #

def _blender_deps():
    import bpy                                    # noqa: F401
    import annotate                               # noqa: F401
    return bpy, annotate


def _crowd_mat(annotate, kind):
    """Saturated opaque overlay material, named under the annotate
    material sweep prefix (KIT_ANNOT_mat_*) so the ONE purge regime
    removes it [F14/F16]. Same dual-write convention as annotate
    (Principled Base Color + diffuse_color — engine parity)."""
    import bpy
    name = f"KIT_ANNOT_mat_crowd_{kind}"
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    rgba = tuple(PALETTE[kind]) + (1.0,)
    try:
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf is not None and "Base Color" in bsdf.inputs:
            bsdf.inputs["Base Color"].default_value = rgba
    except Exception:
        pass
    mat.diffuse_color = rgba
    return mat


def _scene_max_z():
    """The scene's top geometry z (KIT_ANNOT_ excluded) — the overlay
    base z MUST clear it: the measured s24 lesson is that a blocked
    outline drawn at the floor z is OCCLUDED by the very geometry it
    declares (the kiosk box swallowed its own outline)."""
    import bpy
    from mathutils import Vector
    max_z = 0.0
    for o in bpy.context.scene.objects:
        if o.type == 'MESH' and not o.name.startswith("KIT_ANNOT_"):
            try:
                zs = [(o.matrix_world @ Vector(c)).z for c in o.bound_box]
                max_z = max(max_z, max(zs))
            except Exception:
                pass
    return max_z


def build_ortho_cam(union_bounds, name=f"{CROWD_PREFIX}cam"):
    """The crowd_look-owned ORTHO camera [F6]: ortho_scale = 1.2 ×
    max(union_dx, union_dy) [N6]; camera high above the union with a
    TINY clip_start — the measured 5.2 law says an ortho near plane
    INTERSECTING an object's bbox culls it entirely on workbench
    (placement_lib:2258-2271), so the near plane must live ABOVE every
    object (z_cam - clip_start > max_z)."""
    import bpy
    from mathutils import Vector
    (x0, y0, x1, y1) = union_bounds
    dx, dy = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    max_z = _scene_max_z()
    cam_data = bpy.data.cameras.new(name)
    cam_data.type = 'ORTHO'
    cam_data.ortho_scale = 1.2 * max(dx, dy, 1.0)
    z_cam = max_z + 2.0
    cam_data.clip_start = 0.01                    # near plane ABOVE all geometry
    cam_data.clip_end = z_cam + 50.0
    cam = bpy.data.objects.new(name, cam_data)
    cam.location = (cx, cy, z_cam)
    cam.rotation_euler = (0.0, 0.0, 0.0)          # looking straight down -Z
    bpy.context.scene.collection.objects.link(cam)
    return cam


def _render_topdown(cam, out_path, res=(640, 480)):
    """Workbench top-down render with the FULL state snapshot/restore
    discipline (the A11 law — a look must never bake render state into
    the blend): Standard transform, 0 EV [F14], shadows OFF (the s3
    overlay-pass law), one temp camera removed by the caller."""
    import bpy
    scene = bpy.context.scene
    _snap = {
        "engine": scene.render.engine,
        "rx": scene.render.resolution_x, "ry": scene.render.resolution_y,
        "pct": scene.render.resolution_percentage,
        "fmt": scene.render.image_settings.file_format,
        "filepath": scene.render.filepath,
        "vt": scene.view_settings.view_transform,
        "ev": scene.view_settings.exposure,
        "cam": scene.camera,
        "shadows": scene.display.shading.show_shadows,
        "color_type": scene.display.shading.color_type,
        "light": scene.display.shading.light,
    }

    def _restore():
        r = scene.render
        r.engine = _snap["engine"]
        r.resolution_x, r.resolution_y = _snap["rx"], _snap["ry"]
        r.resolution_percentage = _snap["pct"]
        r.image_settings.file_format = _snap["fmt"]
        r.filepath = _snap["filepath"]
        scene.view_settings.view_transform = _snap["vt"]
        scene.view_settings.exposure = _snap["ev"]
        scene.camera = _snap["cam"]
        try:
            scene.display.shading.show_shadows = _snap["shadows"]
            scene.display.shading.color_type = _snap["color_type"]
            scene.display.shading.light = _snap["light"]
        except AttributeError:
            pass

    try:
        from blender_kit import normalize_engine_id
        scene.render.engine = normalize_engine_id("workbench")
        scene.render.resolution_x, scene.render.resolution_y = res
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = 'PNG'
        scene.render.filepath = out_path
        scene.view_settings.view_transform = 'Standard'
        scene.view_settings.exposure = 0.0
        scene.camera = cam
        try:
            scene.display.shading.light = 'STUDIO'
            scene.display.shading.color_type = 'MATERIAL'
            scene.display.shading.show_shadows = False
        except AttributeError:
            pass
        bpy.ops.render.render(write_still=True)
    finally:
        _restore()
    from viewport_capture import _validate_png
    _validate_png(out_path)
    return out_path


def _rect_outline(annotate, r, z, mat, tag, thickness=0.03):
    """4 thin boxes along a rect's edges (outline-only [F15]).
    annotate._thin_box already links each object to the context
    collection — do NOT link again (double-link raises).
    Measured (s24 probe): 0.012 m lines anti-alias into the floor gray
    at scene scale; 0.03 m keeps even 1 m rects readable at 640 px."""
    (x0, y0, x1, y1) = r
    made = []
    for i, (a, b) in enumerate((
            ((x0, y0, z), (x1, y0, z)), ((x1, y0, z), (x1, y1, z)),
            ((x1, y1, z), (x0, y1, z)), ((x0, y1, z), (x0, y0, z)))):
        made.append(annotate._thin_box(f"{CROWD_PREFIX}{tag}_{i}", a, b,
                                       thickness, mat))
    return made


def build_navmap_overlay(rects, decls):
    """The CL1 overlay: per-kind outlines + capped flat labels [F15/F16/
    F17]. Returns the layer dict for annotate.delete_annotation_layer."""
    import bpy
    import annotate
    decls = _norm_decls(decls)
    rects = {"blocked": [{**r, "bounds": _as_flat(r["bounds"])}
                         for r in rects["blocked"]], "report": []}
    made = {"objects": [], "labels": []}
    mats = {k: _crowd_mat(annotate, k) for k in
            ("walkable", "blocked", "dest", "spawn", "label")}
    # overlay base z clears the SCENE's top geometry (the occlusion
    # law — an outline at floor z is swallowed by its own object)
    z = _scene_max_z() + Z_LIFT
    for w in decls["walkables"]:
        made["objects"] += _rect_outline(annotate, w["bounds"], z,
                                         mats["walkable"],
                                         f"walk_{w['id']}", thickness=0.06)
    for r in rects["blocked"]:
        made["objects"] += _rect_outline(annotate, r["bounds"], z + 0.002,
                                         mats["blocked"], f"blkd_{r['id']}")
    for t in decls["destinations"]:
        made["objects"] += _rect_outline(annotate, t["bounds"], z + 0.003,
                                         mats["dest"], f"dest_{t['id']}")
    for s in decls["spawn_sources"]:
        made["objects"] += _rect_outline(annotate, s["bounds"], z + 0.003,
                                         mats["spawn"], f"spawn_{s['id']}")
    # label cap [F17]: all ids live in the verdict block; on-image labels
    # go to at most N=8 rects, destinations/spawns first (they are small
    # and the eye needs them most).
    labelable = ([f"{t['id']}" for t in decls["destinations"]] +
                 [f"{s['id']}" for s in decls["spawn_sources"]] +
                 [r["id"] for r in rects["blocked"]])
    for lid in labelable[:8]:
        pos = None
        for t in decls["destinations"]:
            if t["id"] == lid:
                pos = ((t["bounds"][0] + t["bounds"][2]) / 2,
                       (t["bounds"][1] + t["bounds"][3]) / 2)
        for s in decls["spawn_sources"]:
            if s["id"] == lid:
                pos = ((s["bounds"][0] + s["bounds"][2]) / 2,
                       (s["bounds"][1] + s["bounds"][3]) / 2)
        for r in rects["blocked"]:
            if r["id"] == lid:
                pos = ((r["bounds"][0] + r["bounds"][2]) / 2,
                       (r["bounds"][1] + r["bounds"][3]) / 2)
        if pos is None:
            continue
        curve = bpy.data.curves.new(name=f"{CROWD_PREFIX}lbl_{lid}",
                                    type='FONT')
        curve.body = str(lid)
        curve.size = 0.32
        curve.align_x = 'CENTER'
        curve.align_y = 'CENTER'
        txt = bpy.data.objects.new(f"{CROWD_PREFIX}lbl_{lid}", curve)
        txt.location = (pos[0], pos[1], z + 0.01)
        txt.rotation_euler = (0.0, 0.0, 0.0)      # flat — a map label
        txt.data.materials.append(mats["label"])
        bpy.context.collection.objects.link(txt)
        made["labels"].append(txt)
        made["objects"].append(txt)
    return made


def build_trajectory_overlay(pos, decls, cam=None, max_ticks=64):
    """Beveled poly curves [F12] — one per agent with ≥2 valid points;
    bevel_depth is SCALE-AWARE (the measured s24 lesson: a fixed 0.015
    bevel is 0.5 px at a 19 m ortho_scale and anti-aliases away — the
    line needs ~3 px: ortho_scale/240), z-lift clears the scene.
    Ghost slots [N4] and invalid agents are skipped. Subsample feeds
    GEOMETRY only — telemetry never sees it [F8]."""
    import bpy
    import numpy as np
    valid = ghost_mask(pos)
    made = {"objects": [], "labels": []}
    mat = _crowd_mat(_blender_deps()[1], "traj")
    bevel = 0.015
    if cam is not None:
        bevel = max(0.015, float(cam.data.ortho_scale) / 240.0)
    z = _scene_max_z() + Z_LIFT + 0.004
    n_agents = pos.shape[1]
    step = max(1, pos.shape[0] // max(1, max_ticks))
    for a in range(n_agents):
        idx = np.nonzero(valid[:, a])[0]
        if idx.size < 2:
            continue
        idx = idx[::step]
        if idx[-1] != valid[:, a].nonzero()[0][-1]:
            idx = np.append(idx, valid[:, a].nonzero()[0][-1])
        curve = bpy.data.curves.new(name=f"{CROWD_PREFIX}traj_{a}",
                                    type='CURVE')
        curve.dimensions = '3D'
        sp = curve.splines.new('POLY')
        sp.points.add(len(idx) - 1)
        for k, ti in enumerate(idx):
            sp.points[k].co = (float(pos[ti, a, 0]), float(pos[ti, a, 1]),
                               z, 1.0)
        curve.bevel_depth = bevel
        curve.bevel_resolution = 2
        obj = bpy.data.objects.new(f"{CROWD_PREFIX}traj_{a}", curve)
        obj.data.materials.append(mat)
        bpy.context.collection.objects.link(obj)
        made["objects"].append(obj)
    return made


def world_to_pixel(wx, wy, cam, res):
    """The named world→pixel affine [F6] — shared by the density
    composite and any label math. Ortho cam at (cx, cy, z) looking -Z:
    world-per-pixel = ortho_scale / max(res); y flips (image top = +y)."""
    cx, cy = cam.location.x, cam.location.y
    scale = cam.data.ortho_scale
    wpp = scale / max(res)
    return (res[0] / 2.0 + (wx - cx) / wpp,
            res[1] / 2.0 - (wy - cy) / wpp)


def composite_density(base_png, out_png, dens, cam, res,
                      alpha_max=0.65):
    """The DENSITY pass [F4/F7]: Pillow pixel-space composite of the
    masked histogram over the base render — dark→red single-hue
    monotonic ramp, NO Blender objects (the ghost-occlusion law)."""
    from PIL import Image
    import numpy as np
    if dens["hist"] is None:
        return None
    ax, ay, nx, ny, bs = dens["extent"]
    H = dens["hist"]
    peak = float(H.max())
    if peak <= 0:
        return None
    base = Image.open(base_png).convert("RGBA")
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    px = np.array(layer)
    for ix in range(nx):
        for iy in range(ny):
            v = float(H[ix, iy])
            if v <= 0:
                continue
            wx, wy = ax + (ix + 0.5) * bs, ay + (iy + 0.5) * bs
            u, vv = world_to_pixel(wx, wy, cam, res)
            # bin footprint in pixels
            u0, v1 = world_to_pixel(wx - bs / 2, wy - bs / 2, cam, res)
            u1, v0 = world_to_pixel(wx + bs / 2, wy + bs / 2, cam, res)
            iu0, iu1 = max(0, int(u0)), min(res[0], int(math.ceil(u1)))
            iv0, iv1 = max(0, int(v0)), min(res[1], int(math.ceil(v1)))
            frac = v / peak
            a = int(255 * alpha_max * frac)
            col = (int(60 + 195 * frac), int(10 + 20 * (1 - frac)),
                   int(10 * (1 - frac)), a)
            if iu1 > iu0 and iv1 > iv0:
                px[iv0:iv1, iu0:iu1] = col
    layer = Image.fromarray(px)
    out = Image.alpha_composite(base, layer)
    out.convert("RGB").save(out_png)
    return out_png


def overlay_visibility(png_path, kinds, min_pixels=40):
    """The N2 positive arm: ≥ min_pixels within each kind's palette HUE
    BAND (measured, not assumed). Hue matching, not RGB distance — the
    measured lesson (probe /tmp, s24): 0.012 m anti-aliased lines blend
    with the gray floor and RGB distance never fires; hues are far
    apart (red/green/blue/yellow/cyan) and survive the blend. Requires
    saturation (excludes the gray floor) + value (excludes black)."""
    from PIL import Image
    import colorsys
    import numpy as np
    im = np.asarray(Image.open(png_path).convert("RGB"),
                    dtype=np.float32) / 255.0
    mx = im.max(axis=2)
    mn = im.min(axis=2)
    delta = mx - mn
    sat = np.where(mx > 0, delta / np.maximum(mx, 1e-6), 0.0)
    # hue in degrees
    r, g, b = im[..., 0], im[..., 1], im[..., 2]
    hue = np.zeros_like(mx)
    m = (mx == r) & (delta > 0)
    hue[m] = (60 * ((g[m] - b[m]) / delta[m])) % 360
    m = (mx == g) & (delta > 0)
    hue[m] = (60 * ((b[m] - r[m]) / delta[m]) + 120) % 360
    m = (mx == b) & (delta > 0)
    hue[m] = (60 * ((r[m] - g[m]) / delta[m]) + 240) % 360
    KIND_HUE = {"walkable": 130, "blocked": 0, "dest": 225,
                "spawn": 55, "traj": 175, "label": 55}
    out = {}
    for kind in kinds:
        h0 = KIND_HUE[kind]
        dh = np.minimum(np.abs(hue - h0), 360 - np.abs(hue - h0))
        n = int(((dh < 18) & (sat > 0.25) & (mx > 0.15)).sum())
        out[kind] = n
    return out


# --------------------------------------------------------------------------- #
#  CLI (the one invocation; verdict/exit/JSON table [D7/F13/N5])
# --------------------------------------------------------------------------- #

def _union_bounds(rects, decls):
    decls = _norm_decls(decls)
    bs = ([w["bounds"] for w in decls["walkables"]] +
          [t["bounds"] for t in decls["destinations"]] +
          [s["bounds"] for s in decls["spawn_sources"]] +
          [_as_flat(r["bounds"]) for r in rects["blocked"]])
    if not bs:
        raise CrowdLookRefused("no rects of any kind to frame")
    return (min(b[0] for b in bs), min(b[1] for b in bs),
            max(b[2] for b in bs), max(b[3] for b in bs))


def _write_json(path, payload):
    if path:
        with open(path, "w") as f:
            json.dump(payload, f, indent=2, default=str)


def main(argv=None):
    if argv is None:
        # the kit convention (blender_kit.script_argv): args after '--' on
        # the blrun CLI — argparse must NEVER see Blender's own flags
        # (the U1 finding: raw sys.argv made every documented invocation
        # die with 'unrecognized arguments' before doing any work)
        try:
            from blender_kit import script_argv
            argv = script_argv()
        except Exception:
            argv = None
    ap = argparse.ArgumentParser(
        prog="crowd_look.py",
        description="the crowd-nav vision lane (navmap + trajectory "
                    "encodings; numbers beside the images)")
    ap.add_argument("--navmap", action="store_true")
    ap.add_argument("--traj", action="store_true")
    ap.add_argument("--rects", help="bridge scan output (--json), VERBATIM")
    ap.add_argument("--decls", help="CrowdScene authoring JSON (N1 schema)")
    ap.add_argument("--load-blend")
    ap.add_argument("--scene", help="scene module (fresh-only)")
    ap.add_argument("--bake-cache", help="BakeResult.cache_path")
    ap.add_argument("--corridor-floor", type=float, default=None)
    ap.add_argument("--out", default="output/crowd_look")
    ap.add_argument("--json", dest="json_out", help="verdict artifact path "
                    "(written on EVERY exit class [N5])")
    ap.add_argument("--telemetry", default="full", choices=("full", "none"),
                    help="'none' degrades explicitly and prints WHICH "
                         "stats were dropped [F10]")
    args = ap.parse_args(argv)

    os.makedirs(args.out, exist_ok=True)
    verdict = {"verdict_class": "REFUSED", "findings": [],
               "telemetry": None, "image_paths": [], "modes": []}

    def _refuse(msg):
        verdict["verdict_class"] = "REFUSED"
        verdict["findings"].append({"class": "REFUSED", "reason": msg})
        print(f"[crowd-look] REFUSED: {msg}", flush=True)
        _write_json(args.json_out, verdict)
        return 2

    try:
        if not (args.navmap or args.traj):
            return _refuse("pass --navmap and/or --traj (nothing to look at)")
        if not args.decls:
            return _refuse("--decls is REQUIRED (the authoring surface: "
                           "walkables/destinations/spawns/populations)")
        decls = load_decls(args.decls)
        rects = load_rects(args.rects) if args.rects else \
            {"blocked": [], "report": []}
        floors = corridor_floors(decls, args.corridor_floor)
        floor = floors[0][0]
        print(f"[crowd-look] corridor floor(s): "
              f"{[f'{f} ({p})' for f, p in floors]}", flush=True)

        # authoring findings run in BOTH modes (the F5/N3 classes are
        # declaration-level truth, not render-level)
        p1_rows = (overlap_findings(rects["blocked"], decls) +
                   severance_and_reachability(rects["blocked"], decls,
                                              floors)[0])
        warn_rows = gap_findings(rects["blocked"], decls, floor)
        verdict["findings"] = p1_rows + warn_rows

        import bpy  # noqa: F401 — Blender-side from here
        if args.load_blend:
            bpy.ops.wm.open_mainfile(filepath=args.load_blend)
        elif args.scene:
            import importlib
            importlib.import_module(args.scene)
        else:
            return _refuse("--load-blend PATH (primary, state-carrier law) "
                           "or --scene MODULE is required — an empty "
                           "factory scene renders a void")

        if args.navmap:
            verdict["modes"].append("navmap")
            union = _union_bounds(rects, decls)
            cam = build_ortho_cam(union)
            layer = build_navmap_overlay(rects, decls)
            try:
                from mathutils import Vector
                import annotate as _annot
                _annot.aim_labels_at(layer["labels"], cam.location, flat=True)
                png = os.path.join(args.out, "navmap.png")
                _render_topdown(cam, png)
                verdict["image_paths"].append(png)
                counts = overlay_visibility(png, ("walkable", "blocked",
                                                  "dest", "spawn"))
                verdict["overlay_pixels"] = counts
                missing = [k for k, n in counts.items()
                           if n < 40 and (k != "blocked" or rects["blocked"])
                           and (k != "dest" or decls["destinations"])
                           and (k != "spawn" or decls["spawn_sources"])]
                if missing:
                    verdict["verdict_class"] = "READINESS_FAIL"
                    print(f"[crowd-look] READINESS: overlay kinds not "
                          f"visible: {missing} (counts {counts})",
                          flush=True)
                    _write_json(args.json_out, verdict)
                    return 4
            finally:
                # the module's residue contract: layer + cam both purge
                import annotate as _annot
                _annot.delete_annotation_layer(
                    {"objects": layer["objects"] + [cam],
                     "labels": layer["labels"]})
            print("[crowd-look] navmap verdict:", flush=True)
            print(f"  blocked={len(rects['blocked'])} "
                  f"walkables={len(decls['walkables'])} "
                  f"dests={len(decls['destinations'])} "
                  f"spawns={len(decls['spawn_sources'])}", flush=True)
            for row in verdict["findings"]:
                print(f"  [{row['class']}] {row['type']} "
                      f"{row.get('ids', row.get('decl', ''))} "
                      f"{row.get('at', '')}", flush=True)

        if args.traj:
            verdict["modes"].append("traj")
            if not args.bake_cache:
                return _refuse("--traj needs --bake-cache (BakeResult."
                               "cache_path)")
            import numpy as np
            import blender_crowd_native as bcn
            cache = bcn.Cache(args.bake_cache)
            rng = cache.read_range(cache.tick_start, cache.tick_end)
            pos, meta = decode_positions(rng)
            print(f"[crowd-look] decoded {pos.shape[0]} ticks × "
                  f"{pos.shape[1]} slots ({meta['source']}, "
                  f"{meta['components']}-comp)", flush=True)
            if args.telemetry == "none":
                print("[crowd-look] --telemetry none: reach/penetration/"
                      "density DROPPED (no rects/decls math requested)",
                      flush=True)
                verdict["telemetry"] = {"dropped": ["reach_capacity",
                                                    "reach_ever",
                                                    "max_penetration_m",
                                                    "density"]}
            else:
                tel = trajectory_telemetry(pos, decls, rects["blocked"],
                                           floor)
                verdict["telemetry"] = tel
                dens = density_histogram(pos, decls, floor,
                                         blocked_bounds=[r["bounds"]
                                                         for r in
                                                         rects["blocked"]])
                verdict["jam_centroid"] = dens["jam_centroid"]
                union = _union_bounds(rects, decls)
                cam = build_ortho_cam(union)
                layer = build_trajectory_overlay(pos, decls, cam=cam)
                try:
                    base = os.path.join(args.out, "traj.png")
                    _render_topdown(cam, base)
                    verdict["image_paths"].append(base)
                    counts = overlay_visibility(base, ("traj",))
                    verdict["overlay_pixels_traj"] = counts
                    if dens["hist"] is not None:
                        dpng = os.path.join(args.out, "density.png")
                        composite_density(base, dpng, dens, cam,
                                          (640, 480))
                        if os.path.isfile(dpng):
                            verdict["image_paths"].append(dpng)
                finally:
                    import annotate as _annot
                    _annot.delete_annotation_layer(
                        {"objects": layer["objects"] + [cam],
                         "labels": layer["labels"]})
                print("[crowd-look] telemetry:", flush=True)
                for k in ("n_agents", "ticks", "ghosts_frac",
                          "reach_capacity", "reach_ever",
                          "per_destination", "max_penetration_m",
                          "median_displacement_m", "invariant_ok"):
                    print(f"  {k}: {tel[k]}", flush=True)
                jc = dens["jam_centroid"]
                jc_fmt = ([round(float(jc[0]), 3), round(float(jc[1]), 3)]
                          if jc else None)
                print(f"  jam_centroid: {jc_fmt} "
                      f"(peak/agent {dens['peak_per_agent']}, denominator "
                      f"{dens['denominator']})", flush=True)
                # verdict class (D7/F13): authoring P1s dominate; the
                # ENGINE-GAP JAM is the expected no-routing truth ONLY
                # when the authoring checks are clean [O11c law]
                if p1_rows or not tel["invariant_ok"]:
                    verdict["verdict_class"] = "AUTHORING_P1"
                elif tel["reach_ever"] == 0:
                    verdict["verdict_class"] = "ENGINE_GAP_JAM"
                else:
                    verdict["verdict_class"] = "PASS"

        if verdict["verdict_class"] == "REFUSED":
            # modes ran without refusals and without a traj class —
            # authoring P1s (found in BOTH modes) decide the verdict
            verdict["verdict_class"] = "AUTHORING_P1" if p1_rows else "PASS"
        _write_json(args.json_out, verdict)
        print(f"[crowd-look] verdict_class: {verdict['verdict_class']}",
              flush=True)
        if verdict["verdict_class"] == "AUTHORING_P1":
            return 3
        return 0
    except CrowdLookRefused as e:
        return _refuse(str(e))


if __name__ == "__main__":
    sys.exit(main())


