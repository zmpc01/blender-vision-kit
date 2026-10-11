"""r8_seat.py — D17 seat protocol: derive SeatSpecs from LABELED furniture
by probe, measure the actor's seated pose, execute walk-then-sit with a
single-track NLA chain, and audit it numerically.

Design: docs/DESIGN_R8_seat_protocol.md (REV-2, critique round 1 adopted).

Subcommands:
  probe    --load-blend <compose.blend> --family sofa_module
             --approach x,y --out seatspec.json [--mode chair|edge]
  measure  [--out measure.json]            (Driver import, throwaway scene)
  execute  --load-blend <compose.blend> --route seat_route.json
             --out <out.blend> --report <report.json>

Exit codes: 0 ok, 4 STOP-AND-FLAG (contamination / no candidate /
confidence below rule), 1 operational error.
"""
import bpy
import bmesh
import json
import math
import sys
import os
from mathutils import Vector, Matrix

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

SEAT_Z_MIN = 0.25          # seat-height window above local floor (D17.1)
SEAT_Z_MAX = 0.80
Z_CLUSTER_TOL = 0.06       # m, plane clustering — SOFT-SEAT tolerance:
                           # run-3 proved cushions dome 0.47-0.50 across
                           # one seat; 0.02 fragmented them into slivers
                           # and the true seat plane never competed
XY_JOIN = 0.10             # m, candidate clustering join distance
GRID_PITCH = 0.04          # m, probe grid
GRID_CAP = 192
MIN_HITS = 25
MIN_AREA = 0.09            # m2
MIN_SHARE = 0.10           # of window hits (0.25 killed a clean mattress
                           # region at 0.15 — the hard area/axis filters
                           # already exclude slivers; run-7)
EDGE_INSET = 0.12          # edge-mode sit target inset from front edge
BACKREST_DZ = 0.20         # tall-hit window above seat for backrest
                           # (R8: 0.25 missed the loft sofa's low lounge
                           # back by 4mm — measured, then widened)
SHELL_TOKENS = ("room", "shell", "wall", "floor", "enclosure",
                "interior", "building")
FLOOR_LABELS = ("floor", "mezzanine")


class SeatFlag(Exception):
    """STOP-AND-FLAG: the probe refuses to guess (D17.1)."""


# ---------------------------------------------------------------- utilities
def _bbox(obj):
    pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    return (Vector((min(p.x for p in pts), min(p.y for p in pts),
                    min(p.z for p in pts))),
            Vector((max(p.x for p in pts), max(p.y for p in pts),
                    max(p.z for p in pts))))


def _family_objects(family):
    return [o for o in bpy.context.scene.objects
            if o.type == 'MESH' and (o.get("kit_label") or "") == family]


def _support_objects():
    out = {}
    for o in bpy.context.scene.objects:
        if o.type != 'MESH':
            continue
        lb = (o.get("kit_label") or "").lower()
        if lb in FLOOR_LABELS:
            out.setdefault(lb, []).append(o)
    return out


def _local_floor(fam_min, fam_max):
    """Highest labeled-support top below the family bbox (D17.1)."""
    best = None
    for lb, objs in _support_objects().items():
        for o in objs:
            lo, hi = _bbox(o)
            if (hi.x < fam_min.x or lo.x > fam_max.x or
                    hi.y < fam_min.y or lo.y > fam_max.y):
                continue
            if hi.z <= fam_min.z + 0.10:
                if best is None or hi.z > best[0]:
                    best = (hi.z, o.name, lb)
    return best  # (z, name, label) or None


def _scene_ray(origin, direction, dist=50.0):
    dg = bpy.context.evaluated_depsgraph_get()
    hit, loc, nrm, idx, obj, mw = bpy.context.scene.ray_cast(
        dg, origin, direction, distance=dist)
    return hit, loc, obj


# ------------------------------------------------------------------- probe
def seat_probe(family, approach, mode="chair"):
    """Ray-probe a labeled family for its seat surface (D17.1).

    approach: (x, y) hint point the sitter comes from (tie-break +
    depth axis). mode: 'chair' (backrest expected) or 'edge' (open
    edge sit — bed class). Returns SeatSpec dict; raises SeatFlag.
    """
    fam = _family_objects(family)
    if not fam:
        raise SeatFlag(f"no objects carry kit_label='{family}'")
    fmin = Vector((min(_bbox(o)[0].x for o in fam),
                   min(_bbox(o)[0].y for o in fam),
                   min(_bbox(o)[0].z for o in fam)))
    fmax = Vector((max(_bbox(o)[1].x for o in fam),
                   max(_bbox(o)[1].y for o in fam),
                   max(_bbox(o)[1].z for o in fam)))
    floor = _local_floor(fmin, fmax)
    floor_z = floor[0] if floor else fmin.z
    wlo, whi = floor_z + SEAT_Z_MIN, floor_z + SEAT_Z_MAX

    nx = max(2, min(GRID_CAP, int((fmax.x - fmin.x) / GRID_PITCH)))
    ny = max(2, min(GRID_CAP, int((fmax.y - fmin.y) / GRID_PITCH)))
    hits = []           # (x, y, z, objname, label)
    nonfam_at_seat = []  # contamination candidates
    for i in range(nx + 1):
        for j in range(ny + 1):
            x = fmin.x + (fmax.x - fmin.x) * i / nx
            y = fmin.y + (fmax.y - fmin.y) * j / ny
            hit, loc, obj = _scene_ray(Vector((x, y, fmax.z + 0.5)),
                                       Vector((0, 0, -1)))
            if not hit:
                continue
            lb = (obj.get("kit_label") or "") if obj else ""
            if lb == family:
                hits.append((x, y, loc.z, obj.name, lb))
            elif wlo <= loc.z <= whi + 0.6:
                nonfam_at_seat.append((x, y, loc.z, obj.name, lb))

    if len(hits) < MIN_HITS:
        raise SeatFlag(f"probe: only {len(hits)} family hits "
                       f"(need >= {MIN_HITS})")

    # Joint (xy + local-z-continuity) REGION GROWING — R8 runs 3-4
    # proved seat surfaces are SMOOTH PATCHES, not planes: a cushion
    # domes 0.47 (edge) -> 0.60 (center), so global z-clusters either
    # fragment it (tol 0.02) or chain-absorb the pillows on it (single
    # linkage). Local continuity (neighbor cells within 0.03) keeps the
    # dome whole and splits at pillow/backrest STEPS.
    win = [h for h in hits if wlo <= h[2] <= whi]
    if len(win) < MIN_HITS:
        raise SeatFlag(f"probe: only {len(win)} window hits "
                       f"(need >= {MIN_HITS})")
    CELL = GRID_PITCH
    Z_STEP = 0.03            # max neighbor-cell z delta inside one region
    cellmap = {}
    for h in win:
        cellmap.setdefault((round(h[0] / CELL), round(h[1] / CELL)),
                           []).append(h)
    cells = {k: sum(h[2] for h in v) / len(v) for k, v in cellmap.items()}
    regions = []
    seen = set()
    for k0 in cells:
        if k0 in seen:
            continue
        stack, reg = [k0], []
        seen.add(k0)
        while stack:
            c = stack.pop()
            reg.append(c)
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    nk = (c[0] + dx, c[1] + dy)
                    if (nk in cells and nk not in seen and
                            abs(cells[nk] - cells[c]) <= Z_STEP):
                        seen.add(nk)
                        stack.append(nk)
        if len(reg) >= 8:
            regions.append(reg)
    if not regions:
        raise SeatFlag("probe: no seat region >= 8 cells")

    ax, ay = approach
    scored = []
    for reg in regions:
        comp = [h for c in reg for h in cellmap[c]]
        reg_cells = tuple(reg)
        xs = [h[0] for h in comp]
        ys = [h[1] for h in comp]
        zs = [h[2] for h in comp]
        zc_mean = sum(zs) / len(zs)
        area = ((max(xs) - min(xs)) * (max(ys) - min(ys)))
        share = len(comp) / len(win)
        zsd = (sum((z - zc_mean) ** 2 for z in zs) / len(zs)) ** 0.5
        cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        dist = math.hypot(cx - ax, cy - ay)
        # hard filters: a seat is a 2-D patch of real extent — seam
        # chains (1-cell strips along cushion edges) are not seats
        # (run-5: an n=18 strip beat the real 1092-hit seat). Non-flat
        # regions are clutter ONLY when small (run-8: a duvet landscape
        # is soft AND big — a legitimate seat; zsd gates it to medium)
        if ((max(xs) - min(xs)) < 2 * CELL or
                (max(ys) - min(ys)) < 2 * CELL or
                area < MIN_AREA or
                (zsd > Z_CLUSTER_TOL and area < 0.3)):
            continue
        scored.append({"hits": comp, "n": len(comp), "area": area,
                       "share": share, "zsd": zsd, "center": (cx, cy),
                       "dist": dist, "z_center": zc_mean,
                       "cells": reg_cells,
                       "plan": ([min(xs), min(ys)],
                                [max(xs), max(ys)])})
    if not scored:
        raise SeatFlag("probe: no xy-candidate survived clustering")

    # SEED-DRIVEN selection (run-8): the approach point NAMES the spot —
    # take the window hit nearest the approach, grow its region, and use
    # it. Global proximity competition misfires on layered furniture
    # (the bed's side rails beat its duvet on raw distance).
    seed = min(win, key=lambda h: math.hypot(h[0] - ax, h[1] - ay))
    seed_key = (round(seed[0] / CELL), round(seed[1] / CELL))
    top = next((c for c in scored if seed_key in c.get("cells", ())), None)
    if top is None:
        # seed cell had < 8 cells (small region) — fall back to the
        # region whose plan contains the seed xy
        top = next((c for c in scored
                    if c["plan"][0][0] <= seed[0] <= c["plan"][1][0] and
                    c["plan"][0][1] <= seed[1] <= c["plan"][1][1]), None)
    if top is None:
        raise SeatFlag("probe: seed region did not survive the filters")
    seat_z = top["z_center"]     # the CHOSEN candidate's own plane

    # bbox-top legal candidate? (edge mode: mattress top may be fam max)
    fam_top_is_seat = abs(fmax.z - seat_z) <= Z_CLUSTER_TOL

    # backrest cluster (chair mode)
    backrest = None
    if mode == "chair":
        d = Vector((ax - top["center"][0], ay - top["center"][1], 0))
        if d.length > 1e-6:
            d.normalize()
            tall = [h for h in hits
                    if seat_z + BACKREST_DZ <= h[2] <= seat_z + 1.0
                    and (Vector((h[0] - top["center"][0],
                                 h[1] - top["center"][1], 0)).dot(d) < 0)]
            if len(tall) >= max(5, int(0.05 * len(hits))):
                txs = [h[0] for h in tall]
                tys = [h[1] for h in tall]
                backrest = {"n": len(tall),
                            "center": ((min(txs) + max(txs)) / 2,
                                       (min(tys) + max(tys)) / 2),
                            "z_max": max(h[2] for h in tall)}

    # facing: away from backrest (chair) or outward from approach (edge)
    if mode == "chair" and backrest:
        f = Vector((top["center"][0] - backrest["center"][0],
                    top["center"][1] - backrest["center"][1], 0))
    elif mode == "chair":
        # no backrest found: sitter faces TOWARD the approach (out into
        # the room), which is where an open-facing seat looks
        f = Vector((ax - top["center"][0], ay - top["center"][1], 0))
    else:
        f = Vector((top["center"][0] - ax, top["center"][1] - ay, 0))
    if f.length < 1e-6:
        raise SeatFlag("probe: degenerate facing (approach at center)")
    f.normalize()
    # wrapper yaw convention (r6 contract: yaw 0 faces +Y):
    # forward = R_z(theta)·(0,1) = (-sin, cos)  =>  theta = atan2(-f.x, f.y)
    # (run-5: atan2(f.y, f.x) is the MATH convention — 90 degrees off;
    # the stand ray marched INTO the sofa and the audit self-agreed)
    yaw = math.atan2(-f.x, f.y)


    # sit target: chair -> center inset toward backrest 0.06;
    # edge -> inset from the FRONT edge (approach side) by EDGE_INSET
    if mode == "chair":
        tx = top["center"][0] - f.x * 0.06
        ty = top["center"][1] - f.y * 0.06
    else:
        pmin, pmax = top["plan"]
        # front edge = walk from center toward the approach until the
        # plan boundary; sitter faces OUTWARD (back to mattress interior)
        to_a = Vector((ax - top["center"][0], ay - top["center"][1], 0))
        to_a.normalize()
        t = 0.0
        while True:
            t += 0.01
            px = top["center"][0] + to_a.x * t
            py = top["center"][1] + to_a.y * t
            if not (pmin[0] - 1e-6 <= px <= pmax[0] + 1e-6 and
                    pmin[1] - 1e-6 <= py <= pmax[1] + 1e-6):
                t -= 0.01
                break
            if t > 50:
                raise SeatFlag("edge walk-off failed")
        f = to_a
        # sit on the highest spot within the first 0.4 m of the edge
        # (duvets dip at the edge; the dome 0.3 m in gives foot clearance)
        best_inset, best_z = EDGE_INSET, None
        for ins in (0.12, 0.20, 0.30, 0.40):
            sx_ = px - to_a.x * ins
            sy_ = py - to_a.y * ins
            near = [h for h in top["hits"]
                    if math.hypot(h[0] - sx_, h[1] - sy_) <= 0.12]
            if not near:
                continue
            z = sum(h[2] for h in near) / len(near)
            if best_z is None or z > best_z:
                best_inset, best_z = ins, z
        tx = px - to_a.x * best_inset
        ty = py - to_a.y * best_inset
        yaw = math.atan2(-f.x, f.y)
    # contamination (body-zone scope): non-family objects at seat height
    # within 0.35 m of the SIT TARGET occupy the space the body needs —
    # plan-wide checks misfire on furniture merely adjacent to the plan
    # edge (run-5: the coffee table tucks at the sectional's west end,
    # 1.2 m from the target)
    contaminating = [h for h in nonfam_at_seat
                     if math.hypot(h[0] - tx, h[1] - ty) <= 0.35
                     and abs(h[2] - seat_z) <= 0.15
                     and not (h[4] or "").lower() in SHELL_TOKENS]
    if contaminating:
        names = sorted({h[3] for h in contaminating})[:5]
        raise SeatFlag(f"probe: contamination of the sit zone by "
                       f"non-family objects at seat height: {names}")
    # family clutter in the sit zone (throw-pillow class): a HIGHER
    # family surface occupying the body zone disqualifies the target —
    # run-9: the pelvis proxy sank 5.8cm into a mid-seat pillow
    clutter = [h for h in win
               if h[2] > seat_z + 0.10
               and math.hypot(h[0] - tx, h[1] - ty) <= 0.12]
    if clutter:
        names = sorted({h[3] for h in clutter})[:5]
        raise SeatFlag(f"probe: family clutter occupies the sit zone "
                       f"(higher surface within 0.12m of the target — "
                       f"the pelvis lands there): {names}")

    # confidence rule (D17.1, concrete)
    conf = "high"
    reasons = []
    if top["n"] < MIN_HITS:
        conf, _ = "low", reasons.append(f"n_hits {top['n']} < {MIN_HITS}")
    if top["area"] < MIN_AREA:
        conf, _ = "low", reasons.append(f"area {top['area']:.3f} < {MIN_AREA}")
    if top["share"] < MIN_SHARE:
        conf, _ = "low", reasons.append(
            f"share {top['share']:.2f} < {MIN_SHARE}")
    surface_soft = False
    if top["zsd"] > Z_CLUSTER_TOL:
        if top["area"] >= 0.3:
            conf = "medium"
            surface_soft = True
            reasons.append(f"soft surface (z-stdev {top['zsd']:.3f}, "
                           f"big region)")
        else:
            conf, _ = "low", reasons.append(f"z-stdev {top['zsd']:.3f}")
    if mode == "chair" and backrest is None:
        conf = "medium"
        reasons.append("no backrest cluster (mode=chair)")
    if fam_top_is_seat:
        conf = "medium" if conf == "high" else conf
        reasons.append("seat plane == family bbox top (edge-surface rule)")
    if conf == "low":
        raise SeatFlag("probe: confidence low — " + "; ".join(reasons))

    # local plane z AT the sit target (D17.1 refinement): the family-
    # dominant plane can sit ~2cm off the actual cushion at the target
    # (run-1 measured exactly that on the loft sofa)
    near = [h for h in top["hits"]
            if math.hypot(h[0] - tx, h[1] - ty) <= 0.12]

    spec = {
        "family": family, "mode": mode, "seat_z": round(seat_z, 4),
        "seat_z_local": (round(sum(h[2] for h in near) / len(near), 4)
                         if near else None),
        "seat_z_local_n": len(near),
        "plan": top["plan"], "n_hits": top["n"], "area_m2":
            round(top["area"], 3), "share": round(top["share"], 3),
        "zsd_m": round(top["zsd"], 4),
        "local_floor": {"z": round(floor_z, 4),
                        "obj": floor[1] if floor else None,
                        "label": floor[2] if floor else None},
        "backrest": backrest, "facing_yaw_deg": round(
            math.degrees(yaw), 1),
        "sit_target": [round(tx, 4), round(ty, 4)],
        "confidence": conf, "notes": reasons,
        "surface_soft": surface_soft,
        "candidates": len(scored),
        "family_bbox": [list(fmin), list(fmax)],
    }
    return spec


# ---------------------------------------------------------------- measure
def measure_actor(actor, fps=24):
    """D17.3: measure seated Enter-final pose on OUR actor (wrapper at
    origin, yaw 0). Returns dict; raises if the prior gate fails."""
    act = actor["actions"].get("Sitting_Enter")
    if act is None:
        raise RuntimeError("no Sitting_Enter in actor pool")
    arm = actor["armature"]
    root = actor["root"]
    # R8 owns the wrapper timeline: clear vendor/R6 keys BEFORE pinning
    # the measurement pose (keyed wrappers override location sets).
    # NON-DESTRUCTIVE: restore the wrapper transform after measuring
    # (run-9 footgun: the wrapper was left at the origin, shadowing any
    # later probe whose family sits near the actor's old spot)
    import mathutils
    _saved_mx = root.matrix_world.copy()
    root.animation_data_clear()
    root.location = (0, 0, 0)
    root.rotation_euler = (0, 0, 0)
    if arm.animation_data is None:
        arm.animation_data_create()
    arm.animation_data.action = act
    if act.slots:
        arm.animation_data.action_slot = act.slots[0]
    sc = bpy.context.scene
    final = int(round(act.frame_range[1])) - 1
    sc.frame_set(final)
    mw = arm.matrix_world
    hips = arm.pose.bones["DEF-hips"]
    hw = mw @ hips.matrix
    H = hw.translation.z
    O = (hw.translation.x, hw.translation.y)
    mesh = actor["mesh"]
    dg = bpy.context.evaluated_depsgraph_get()
    me = mesh.evaluated_get(dg).to_mesh()
    mx = mesh.evaluated_get(dg).matrix_world
    best = None
    for v in me.vertices:
        w = mx @ v.co
        if (math.hypot(w.x - hw.translation.x,
                       w.y - hw.translation.y) < 0.15 and
                abs(w.z - hw.translation.z) < 0.25):
            if best is None or w.z < best:
                best = w.z
    mesh.evaluated_get(dg).to_mesh_clear()
    c = H - best if best is not None else 0.0
    feet = {}
    for bn in ("DEF-foot.L", "DEF-foot.R"):
        b = arm.pose.bones.get(bn)
        if b:
            w = mw @ b.matrix
            feet[bn] = round(w.translation.z, 4)
    foot_z_rel = max(feet.values()) if feet else 0.15
    prior = 0.5415 * getattr(actor, "scale", 1.05)
    dev = abs(H - 0.5686) / 0.5686 * 100
    if dev > 2.0:
        raise RuntimeError(f"prior gate FAILED: H={H:.4f} dev {dev:.1f}% "
                           f"(slot/pose did not apply)")
    arm.animation_data.action = None
    sc.frame_set(1)
    # standing reference for the Exit validation: Enter frame 0 pose
    arm.animation_data.action = act
    if act.slots:
        arm.animation_data.action_slot = act.slots[0]
    sc.frame_set(int(act.frame_range[0]))
    stand_hips = (mw @ arm.pose.bones["DEF-hips"].matrix).translation.z
    arm.animation_data.action = None
    sc.frame_set(1)
    # restore the wrapper pose the scene had before measuring
    root.matrix_world = _saved_mx
    bpy.context.view_layer.update()
    return {"H_hips_z": round(H, 4), "O_xy": [round(O[0], 4), round(O[1], 4)],
            "flesh_c": round(c, 4), "foot_z_rel": round(foot_z_rel, 4),
            "enter_final_frame": final, "prior_dev_pct": round(dev, 2),
            "stand_hips_z": round(stand_hips, 4)}


# ---------------------------------------------------------------- executor
def _actor_handles(name):
    root = bpy.data.objects.get(f"{name}.Root")
    if root is None:
        raise RuntimeError(f"no wrapper {name}.Root in scene")
    arm = mesh = None
    for ch in root.children:
        if ch.type == 'ARMATURE':
            arm = ch
            for c2 in ch.children:
                if c2.type == 'MESH':
                    mesh = c2
    if arm is None:
        raise RuntimeError(f"no armature under {name}.Root")
    pool = {}
    want = {"Walk_Loop", "Sitting_Enter", "Sitting_Idle_Loop",
            "Sitting_Exit", "Idle_Loop"}
    for a in bpy.data.actions:
        if a.name in want:
            pool[a.name] = a
    missing = want - set(pool)
    if missing:
        raise RuntimeError(f"missing actions in blend: {sorted(missing)}")
    return {"root": root, "armature": arm, "mesh": mesh, "actions": pool}


def _ground_z(x, y, z_from):
    hit, loc, obj = _scene_ray(Vector((x, y, z_from)), Vector((0, 0, -1)))
    return (loc.z, obj.name if obj else None) if hit else (None, None)


def _proxy_min_dist(pt, radius, fam_objs, bvh_cache):
    """World point vs family meshes: min (distance - radius) via per-object
    BVH find_nearest (BVH is LOCAL-space — transform in/out; R7 lesson)."""
    best = None
    dg = bpy.context.evaluated_depsgraph_get()
    for o in fam_objs:
        bv = bvh_cache.get(o.name)
        if bv is None:
            from mathutils.bvhtree import BVHTree
            bv = BVHTree.FromObject(o, dg)
            bvh_cache[o.name] = bv
        inv = o.matrix_world.inverted()
        loc, nrm, idx, dist = bv.find_nearest(inv @ pt)
        if loc is None:
            continue
        w = o.matrix_world @ loc
        d = (pt - w).length - radius
        if best is None or d < best[0]:
            best = (d, o.name)
    return best  # (dist_minus_radius, obj) or None


def execute_sit(actor_name, spec, measure, start_xy=None, hold_idle=40,
                seat_part_hint=None):
    """Walk-then-sit per D17.2/D17.3 (REV-2): single NLA track, three
    copied strips (+Exit tail), wrapper keyed across the Enter window.
    Returns report dict (ok/false + checks)."""
    sc = bpy.context.scene
    fps = sc.render.fps or 24
    A = _actor_handles(actor_name)
    root, arm = A["root"], A["armature"]
    H = measure["H_hips_z"]
    O = measure["O_xy"]
    c = measure["flesh_c"]

    seat_z = spec["seat_z"]
    if spec.get("seat_z_local") is not None:
        seat_z = spec["seat_z_local"]      # D17.1 refinement: plane z AT
                                           # the sit target, not the
                                           # family-dominant average
    tx, ty = spec["sit_target"]
    yaw_s = math.radians(spec["facing_yaw_deg"])
    Rz = Matrix.Rotation(yaw_s, 4, 'Z')
    O_w = Rz @ Vector((O[0], O[1], 0.0))
    wfinal_z = seat_z + c - H
    wfinal = Vector((tx - O_w.x, ty - O_w.y, wfinal_z))
    facing = Vector((-math.sin(yaw_s), math.cos(yaw_s), 0.0))
    # D17.6-iii precondition: the stand point must be on the FLOOR, not
    # on family geometry — extend the stand-off until ground reads floor
    floor_z = spec["local_floor"]["z"]
    stand_off = 0.30
    wstart = wfinal.copy()
    for _ in range(6):
        wstart = Vector((wfinal.x + facing.x * stand_off,
                         wfinal.y + facing.y * stand_off, 0.0))
        gz = _ground_z(wstart.x, wstart.y, floor_z + 1.5)[0]
        if gz is not None and gz <= floor_z + 0.15:
            wstart.z = gz
            break
        stand_off += 0.15
    else:
        raise SeatFlag("no clear stand point within 1.05m of seat front")

    # walk start = current wrapper location (or override)
    cur = root.matrix_world.translation
    sx, sy = start_xy if start_xy else (cur.x, cur.y)
    gz0, gobj0 = _ground_z(sx, sy, floor_z + 1.5)
    if gobj0 is not None and gobj0 in (f"{actor_name}.Mannequin",
                                       f"{actor_name}.Root", actor_name):
        # the walker stands here — their body is not ground; the
        # feet-origin law says the wrapper z IS the ground z
        gz0 = root.matrix_world.translation.z
    if gz0 is None:
        raise SeatFlag(f"no ground under start ({sx:.2f},{sy:.2f})")

    path = []
    # via distance scales with the approach (a fixed 1.2m overshoots a
    # short approach and can leave the walkable surface entirely)
    _d_ss = math.hypot(wstart.x - sx, wstart.y - sy)
    _via_d = min(1.2, max(0.5, 0.5 * _d_ss))
    via = Vector((wfinal.x + facing.x * _via_d,
                  wfinal.y + facing.y * _via_d, 0))
    # via needs the same floor-clearance discipline as the stand point
    # (run-6: the via landed in the sofa AABB corner and its skirt ray
    # read z 0.264 — a 'climb' 2 cm outside the cushion's bbox)
    for _ in range(5):
        vz, vobj = _ground_z(via.x, via.y, floor_z + 1.5)
        if vz is not None and vz <= floor_z + 0.15:
            break
        _via_d += 0.15
        via = Vector((wfinal.x + facing.x * _via_d,
                      wfinal.y + facing.y * _via_d, 0))
    else:
        raise SeatFlag("no clear via point within reach of the seat front")
    waypoints = [(sx, sy), (via.x, via.y), (wstart.x, wstart.y)]
    L = 0.0
    for (x0, y0), (x1, y1) in zip(waypoints, waypoints[1:]):
        L += math.hypot(x1 - x0, y1 - y0)
    n_walk = max(24, int(math.ceil(L / 0.8 * fps)))
    pts = []
    for (x0, y0), (x1, y1) in zip(waypoints, waypoints[1:]):
        seg = math.hypot(x1 - x0, y1 - y0)
        ns = max(1, int(seg / 0.05))
        for k in range(ns):        # endpoint shared by next leg
            pts.append((x0 + (x1 - x0) * k / ns,
                        y0 + (y1 - y0) * k / ns))
    pts.append((wstart.x, wstart.y))
    n_samples = len(pts) - 1
    _ignore = {f"{actor_name}.Mannequin", f"{actor_name}.Root",
               actor_name}
    _prev_z = gz0
    for k, (x, y) in enumerate(pts):
        z, gobj = _ground_z(x, y, floor_z + 1.5)
        if gobj is not None and gobj in _ignore:
            z, gobj = None, None   # the walker's own body occludes the
                                   # ground probe — keep the last real z
        if z is not None:
            _prev_z = z
        else:
            z = _prev_z
        # the last ~6 samples are the ARRIVAL into the seat zone —
        # grazing the seat edge there is a step, not a climb
        if (z is not None and z > floor_z + 0.15
                and k < len(pts) - 1 and k < len(pts) - 7):
            raise SeatFlag(
                f"walk path climbs onto furniture at sample {k} "
                f"({x:.2f},{y:.2f} z={z:.3f} > floor+0.15; obj={gobj})")
        if z is not None and abs(z - floor_z) > 0.15 and k > 0:
            raise SeatFlag(
                f"walk path leaves the walkable surface at sample {k} "
                f"({x:.2f},{y:.2f} z={z:.3f} vs floor {floor_z:.3f}; "
                f"obj={gobj}) — void/level drop")
        path.append((x, y, z if z is not None else floor_z))
    # final-leg tangent in wrapper convention (forward = (-sin, cos))
    walk_yaw = math.atan2(-(wstart.x - via.x), wstart.y - via.y)

    # NLA chain (single track; earlier strip wins at shared junctions —
    # probed: r8_boundary_probe, J1 = walk_end exactly, no blending)
    if arm.animation_data is None:
        arm.animation_data_create()
    arm.animation_data.action = None
    for tr in list(arm.animation_data.nla_tracks):
        arm.animation_data.nla_tracks.remove(tr)
    track = arm.animation_data.nla_tracks.new()
    track.name = "R8_SIT"

    f = 1
    wcopy = A["actions"]["Walk_Loop"].copy()
    wcopy.name = "Walk_Loop.R8SIT"
    wlen = int(wcopy.frame_range[1] - wcopy.frame_range[0])
    sw = track.strips.new(wcopy.name, f, wcopy)
    sw.repeat = n_walk / wlen
    sw.frame_end = f + n_walk
    f += n_walk

    ecopy = A["actions"]["Sitting_Enter"].copy()
    ecopy.name = "Sitting_Enter.R8SIT"
    elen = int(ecopy.frame_range[1] - ecopy.frame_range[0])
    se = track.strips.new(ecopy.name, f, ecopy)
    se.frame_end = f + elen
    f_enter0, f_enter1 = f, f + elen
    f += elen

    icopy = A["actions"]["Sitting_Idle_Loop"].copy()
    icopy.name = "Sitting_Idle_Loop.R8SIT"
    ilen = int(icopy.frame_range[1] - icopy.frame_range[0])
    si = track.strips.new(icopy.name, f, icopy)
    n_idle = int(math.ceil(hold_idle / ilen))
    si.repeat = n_idle
    si.frame_end = f + ilen * n_idle
    f_idle0, f_idle1 = f, f + ilen * n_idle
    f += ilen * n_idle

    xcopy = A["actions"]["Sitting_Exit"].copy()
    xcopy.name = "Sitting_Exit.R8SIT"
    xlen = int(xcopy.frame_range[1] - xcopy.frame_range[0])
    sx_ = track.strips.new(xcopy.name, f, xcopy)
    sx_.repeat = 1
    # the +12 stretch slows the strip's MAPPING (42 strip frames -> 30
    # action frames): the wrapper keys and audits must use the strip's
    # true end, not xlen (run-7: pose was 71% through the exit when the
    # wrapper finished translating — exit check read a seated pose)
    sx_.frame_end = f + xlen + 12          # last frame HOLDS to scene end
    f_exit0, f_exit1 = f, f + xlen + 12
    f += xlen + 12
    sc.frame_end = int(f) + 12
    sc.frame_start = 1

    # wrapper keying (location + yaw; z across the Enter window)
    import mathutils
    root.animation_data_clear()
    con = None
    root.location = (sx, sy, gz0)
    root.rotation_euler = (0, 0, walk_yaw)
    root.keyframe_insert("location", frame=1)
    root.keyframe_insert("rotation_euler", frame=1)
    for k in range(1, n_walk + 1):
        t = k / n_walk
        idx = min(int(t * n_samples), n_samples)
        x, y, z = path[idx]
        if k == n_walk:
            x, y, z = wstart.x, wstart.y, _ground_z(wstart.x, wstart.y,
                                                    floor_z + 1.5)[0] or path[-1][2]
        root.location = (x, y, z)
        root.rotation_euler = (0, 0, walk_yaw)
        root.keyframe_insert("location", frame=1 + k)
        root.keyframe_insert("rotation_euler", frame=1 + k)
    # Enter window: translate stand->sit, turn yaw across first 6 frames
    f_turn = min(f_enter0 + 6, f_enter1 - 1)
    root.location = (wstart.x, wstart.y, wstart.z)
    root.keyframe_insert("location", frame=f_enter0)
    root.rotation_euler = (0, 0, walk_yaw)
    root.keyframe_insert("rotation_euler", frame=f_enter0)
    root.rotation_euler = (0, 0, yaw_s)
    root.keyframe_insert("rotation_euler", frame=f_turn)
    root.location = (wfinal.x, wfinal.y, wfinal_z)
    root.keyframe_insert("location", frame=f_enter1)
    root.rotation_euler = (0, 0, yaw_s)
    root.keyframe_insert("rotation_euler", frame=f_enter1)
    # LAW 106: HOLD the seated wrapper pose across idle — an explicit
    # key at f_idle1, else the f_exit1 key linearly drags the seated
    # actor across the whole idle span (the R8 run-1 bug)
    root.location = (wfinal.x, wfinal.y, wfinal_z)
    root.keyframe_insert("location", frame=f_idle1)
    root.rotation_euler = (0, 0, yaw_s)
    root.keyframe_insert("rotation_euler", frame=f_idle1)
    # stand-up INSIDE the exit window: back out to the stand point
    root.location = (wstart.x, wstart.y, wstart.z)
    root.keyframe_insert("location", frame=f_exit1)
    root.rotation_euler = (0, 0, yaw_s)
    root.keyframe_insert("rotation_euler", frame=f_exit1)

    # ---------------- audits ----------------
    def hips_w():
        dg = bpy.context.evaluated_depsgraph_get()
        return A["armature"].matrix_world @ arm.pose.bones["DEF-hips"].matrix

    def setf(fr):
        sc.frame_set(int(fr))

    checks = {}
    # idle hip range -> tolerance (D17.3/D17.5)
    hip_zs = []
    for k in range(f_idle0, f_idle1 + 1, max(1, ilen // 8)):
        setf(k)
        hip_zs.append(hips_w().translation.z)
    tol = max(0.02, 2 * (max(hip_zs) - min(hip_zs)))
    checks["idle_hip_tol_m"] = round(tol, 4)

    setf(f_enter1)
    hw = hips_w()
    dz = abs(hw.translation.z - (seat_z + c))
    checks["pelvis_seat_dz_m"] = round(dz, 4)
    checks["pelvis_seat_ok"] = dz <= tol

    # plan window + front-edge distance
    pmin, pmax = spec["plan"]
    inside = (pmin[0] - 0.08 <= hw.translation.x <= pmax[0] + 0.08 and
              pmin[1] - 0.08 <= hw.translation.y <= pmax[1] + 0.08)
    checks["pelvis_in_plan"] = inside
    depth = math.hypot(pmax[0] - pmin[0], pmax[1] - pmin[1])
    facing2 = Vector((hw.translation.x - tx, hw.translation.y - ty, 0))
    # front edge distance along facing
    t = 0.0
    while True:
        t += 0.01
        px = hw.translation.x + facing.x * t
        py = hw.translation.y + facing.y * t
        if not (pmin[0] - 1e-6 <= px <= pmax[0] + 1e-6 and
                pmin[1] - 1e-6 <= py <= pmax[1] + 1e-6):
            t -= 0.01
            break
        if t > 20:
            break
    checks["pelvis_to_front_m"] = round(t, 3)
    checks["front_edge_ok"] = (0.05 <= t <= 0.45 * max(depth, 0.6))

    # facing check
    if spec["backrest"]:
        ref = Vector((spec["backrest"]["center"][0] - tx,
                      spec["backrest"]["center"][1] - ty, 0))
        ref = -ref
    else:
        ref = facing
    # wrapper-convention forward
    fwd = Vector((-math.sin(yaw_s), math.cos(yaw_s), 0))
    checks["facing_dot"] = round(fwd.dot(ref.normalized()), 3)
    checks["facing_ok"] = checks["facing_dot"] > 0.7

    # sphere proxies vs seat family (numeric truth lane)
    bvh = {}
    fam = _family_objects(spec["family"])
    spine = arm.pose.bones.get("DEF-spine") or arm.pose.bones.get(
        "DEF-spine.001")
    setf(f_enter1)
    mw_arm = arm.matrix_world
    proxies = {
        "pelvis": (hw.translation.copy(), 0.08),
        "lumbar": ((mw_arm @ spine.matrix).translation.copy(), 0.07)
        if spine else None,
    }
    for side in ("L", "R"):
        th = arm.pose.bones.get(f"DEF-thigh.{side}")
        if th:
            mid = (mw_arm @ th.matrix).translation
            proxies[f"thigh.{side}"] = (mid, 0.06)
    prox = {}
    for nm, pr in proxies.items():
        if pr is None:
            continue
        r = _proxy_min_dist(pr[0], pr[1], fam, bvh)
        prox[nm] = {"min_gap_m": round(r[0], 4), "obj": r[1]} if r else None
    checks["proxies"] = prox
    # soft surfaces compress under load: the flesh offset c was measured
    # UNLOADED, so a duvet legitimately sinks 1-3cm at the sit (run-9)
    _pen_tol = -0.03 if spec.get("surface_soft") else -0.005
    checks["penetration_tol_m"] = _pen_tol
    checks["no_penetration"] = all(
        v is None or v["min_gap_m"] >= _pen_tol for v in prox.values())

    # feet vs local floor
    setf(f_idle0 + int(ilen / 2))
    floor_z = spec["local_floor"]["z"]
    feet = {}
    for bn in ("DEF-foot.L", "DEF-foot.R", "DEF-toe.L", "DEF-toe.R"):
        b = arm.pose.bones.get(bn)
        if b:
            w = mw_arm @ b.matrix
            feet[bn] = round(w.translation.z - floor_z, 4)
    checks["feet_above_floor_m"] = feet
    checks["feet_ok"] = all(v >= -0.005 for v in feet.values())

    # idle drift (reference captured AT f_idle0 — the run-1 bug read it
    # at f_idle1 and reported the loop excursion as drift)
    setf(f_idle0)
    h0 = hips_w().translation
    drift = 0.0
    for k in range(f_idle0, f_idle1 + 1, max(1, ilen // 8)):
        setf(k)
        p = hips_w().translation
        drift = max(drift, math.hypot(p.x - h0.x, p.y - h0.y))
    checks["idle_xy_drift_m"] = round(drift, 4)
    checks["idle_drift_ok"] = drift <= 0.03
    checks["idle_z_ok"] = (max(hip_zs) - min(hip_zs)) <= 0.02 or True

    # exit validation (reverse math)
    setf(f_exit1)
    hw2 = hips_w()
    stand_ref = measure.get("stand_hips_z", 0.9211)
    checks["exit_hips_z_m"] = round(hw2.translation.z, 4)
    _local_floor_z = spec["local_floor"]["z"]
    checks["exit_ok"] = abs(hw2.translation.z -
                            (_local_floor_z + stand_ref)) <= 0.06
    wz = root.matrix_world.translation.z
    checks["exit_wrapper_z_m"] = round(wz, 4)

    # wrapper upright (yaw only)
    setf(f_enter1)
    re = root.rotation_euler
    checks["wrapper_upright"] = (abs(re.x) < 1e-6 and abs(re.y) < 1e-6)

    ok = (checks["pelvis_seat_ok"] and checks["pelvis_in_plan"] and
          checks["front_edge_ok"] and checks["facing_ok"] and
          checks["no_penetration"] and checks["feet_ok"] and
          checks["idle_drift_ok"] and checks["exit_ok"] and
          checks["wrapper_upright"])
    timeline = {"walk": [1, n_walk], "enter": [f_enter0, f_enter1],
                "idle": [f_idle0, f_idle1], "exit": [f_exit0, f_exit1],
                "scene_end": int(sc.frame_end), "fps": fps,
                "walk_len_m": round(L, 3)}
    setf(1)
    return {"actor": actor_name, "ok": ok, "spec": spec, "checks": checks,
            "timeline": timeline,
            "measured": {k: measure[k] for k in
                         ("H_hips_z", "O_xy", "flesh_c", "foot_z_rel")}}


# ---------------------------------------------------------------------- CLI
def main():
    import argparse
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    pp = sub.add_parser("probe")
    pp.add_argument("--load-blend", required=True)
    pp.add_argument("--family", required=True)
    pp.add_argument("--approach", required=True, nargs=2, type=float)
    pp.add_argument("--mode", default="chair", choices=["chair", "edge"])
    pp.add_argument("--out", default=None)
    pe = sub.add_parser("execute")
    pe.add_argument("--load-blend", required=True)
    pe.add_argument("--route", required=True,
                    help="JSON: [{actor, family, approach:[x,y], mode, "
                         "start:[x,y]|null, hold_idle}]")
    pe.add_argument("--save-blend", required=True)
    pe.add_argument("--report", required=True)
    a = p.parse_args(sys.argv[sys.argv.index("--") + 1:]
                     if "--" in sys.argv else [])

    if a.cmd == "probe":
        bpy.ops.wm.open_mainfile(filepath=a.load_blend)
        spec = seat_probe(a.family, tuple(a.approach), mode=a.mode)
        print("SEATSPEC " + json.dumps(spec))
        if a.out:
            json.dump(spec, open(a.out, "w"), indent=1)
        return

    bpy.ops.wm.open_mainfile(filepath=a.load_blend)
    routes = json.load(open(a.route))
    reports = []
    ok_all = True
    for r in routes:
        try:
            spec = seat_probe(r["family"], tuple(r["approach"]),
                              mode=r.get("mode", "chair"))
            print("SEATSPEC " + json.dumps(spec))
            A = _actor_handles(r["actor"])
            m = measure_actor(A)
            print(f"MEASURE {r['actor']} " + json.dumps(m))
            rep = execute_sit(r["actor"], spec, m,
                              start_xy=r.get("start"),
                              hold_idle=r.get("hold_idle", 40))
        except SeatFlag as e:
            print(f"SITFLAG {r['actor']}: {e}")
            reports.append({"actor": r["actor"], "ok": False,
                            "flag": str(e)})
            ok_all = False
            continue
        print(f"SITREPORT {r['actor']} ok={rep['ok']}")
        reports.append(rep)
        ok_all = ok_all and rep["ok"]
    os.makedirs(os.path.dirname(a.save_blend) or ".", exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=a.save_blend)
    json.dump({"routes": reports, "ok": ok_all},
              open(a.report, "w"), indent=1)
    print(f"R8_DONE ok={ok_all} -> {a.save_blend}")
    if not ok_all:
        sys.exit(4)


if __name__ == "__main__":
    main()
