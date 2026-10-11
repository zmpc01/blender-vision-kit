"""r7_navigate.py — R7 executor: keyframe the actor along the blind route.

Consumes route_request.json (produced by r7_route_planner.py from the
manifest ALONE — no vision) and executes it in Blender:

  1. builds a dense path from the waypoint polyline
  2. stair-ramp z refinement: downward raycast against the `stairs` mesh
     every ~2 cm of horizontal travel (tread-hug; space-saver treads are
     not expressible in the blind planner's bboxes — that refinement is
     exactly the executor's declared job)
  3. keys Driver.Root (feet-origin wrapper) per frame: location + yaw
     from the path tangent, upright (68-deg body pitch would be absurd
     for an upright walk clip)
  4. Walk_Loop on a COPY of the action with CYCLE modifiers (fresh-bake
     law: never mutate imported source actions)
  5. numeric audit: per-frame foot-gap raycast vs the walkable set
     (floor/stairs/mezzanine) — the executor's honest numbers
  6. saves output/r7/loft_nav.blend + output/r7/nav_report.json

Run:  ./scripts/blrun.sh --background --python scripts/r7_navigate.py
Pre:  output/r6/loft_compose.blend + output/r7/route_request.json
"""
import json
import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

ROOT = os.path.dirname(_HERE)
SRC = os.path.join(ROOT, "output", "r6", "loft_compose.blend")
ROUTE = os.path.join(ROOT, "output", "r7", "route_request.json")
DST = os.path.join(ROOT, "output", "r7", "loft_nav.blend")
REPORT = os.path.join(ROOT, "output", "r7", "nav_report.json")

STEP = 0.02          # horizontal densification step on the ramp (m)
FOOT_TOL = 0.03      # audit: foot gap above this = float (m)
EDGE_TOL = 0.35      # audit: excused gap within this of valid surface (m)
LABEL_FALLBACK = ("Cube.001", "Plane.003", "mezzanine_slab")


def snap_waypoint(xy, want_z, bvh, max_r=1.6, step=0.1):
    """Surface confirmation with local search (executor-side refinement).

    The blind route is bbox-based and cannot know the slab's stairwell
    OPENING (found live at x=3.398: no slab top for y 8.5..12 — the
    arrival line crosses the void). If the planned xy has no surface at
    ~want_z, spiral-search for the nearest walkable point. Returns
    (xy, got_z, amendment|None)."""
    got = ray_down(bvh, xy[0], xy[1], want_z + 0.8)
    if got is not None and abs(got - want_z) < 0.15:
        return xy, got, None
    r = step
    while r <= max_r:
        for ang in range(0, 360, 30):
            a = math.radians(ang)
            nx, ny = xy[0] + r * math.cos(a), xy[1] + r * math.sin(a)
            h = ray_down(bvh, nx, ny, want_z + 0.8)
            if h is not None and abs(h - want_z) < 0.15:
                return [round(nx, 3), round(ny, 3)], h, {
                    "planned_xy": [round(v, 3) for v in xy],
                    "amended_to": [round(nx, 3), round(ny, 3)],
                    "radius_m": round(r, 2),
                    "why": "no walkable surface at planned xy "
                           "(slab stairwell opening) — snapped to "
                           "nearest surface at route z"}
        r += step
    return xy, None, {"planned_xy": [round(v, 3) for v in xy],
                      "failed": True,
                      "why": "no surface within search radius — "
                             "route unexecutable as planned"}


def build_bvhs(labels_used):
    """Per-support (BVHTree, matrix_world) pairs, resolved BY LABEL from
    the blind route (labels_used: floor/stairs/mezzanine -> object ids).
    Label-driven supports are the protocol: the executor must not
    hardcode ids the manifest may not agree with.

    GOTCHA (caught by the W0 probe): BVHTree.FromObject builds the tree
    in the object's LOCAL space — world-space rays against it return
    garbage for any object whose origin is not at the world origin
    (Cube.001's origin sits ~0.63 m below the floor). Every ray is
    transformed into local space and the hit back into world space.
    """
    dg = bpy.context.evaluated_depsgraph_get()
    ids = [labels_used[k] for k in ("floor", "stairs", "mezzanine")
           if labels_used.get(k)]
    if not ids:
        ids = list(LABEL_FALLBACK)
    bvh = {}
    for oid in ids:
        obj = bpy.data.objects.get(oid)
        if obj is None:
            raise RuntimeError(f"support {oid} missing in {SRC}")
        bvh[oid] = (BVHTree.FromObject(obj, dg), obj.matrix_world.copy())
        print(f"[r7-nav] support: {oid}")
    return bvh


def ray_down(bvh, x, y, z_start):
    """Highest surface z below z_start across the walkable set, or None."""
    best = None
    origin = Vector((x, y, z_start))
    d = Vector((0.0, 0.0, -1.0))
    for tree, mw in bvh.values():
        inv = mw.inverted()
        o_l = inv @ origin
        d_l = inv.to_3x3() @ d
        hit = tree.ray_cast(o_l, d_l)
        if hit[0] is not None:
            z = (mw @ hit[0]).z
            if best is None or z > best:
                best = z
    return best


def densify(route, bvh):
    """Route waypoints -> dense [(x, y, z)] + [(seg_start_idx, speed)]."""
    wp = route["waypoints"]
    # vision amendments (evidence-based route corrections from the
    # principal; see output/r7/vision_amendments.json)
    am_path = ROUTE.replace("route_request.json", "vision_amendments.json")
    vam = {}
    if os.path.exists(am_path):
        vam = json.load(open(am_path)).get("waypoints", {})
        print(f"[r7-nav] vision amendments loaded: {sorted(vam)}")
    pts = []
    segs = []           # (start_index_in_pts, speed)
    amendments = []
    last_z = None
    held_over_void = 0
    for i, w in enumerate(wp):
        x, y = w["xy"]
        want_z = w["z"]
        if w["name"] in vam:
            x, y = vam[w["name"]]["xy"]
        if i > 0:
            # executor job: surface confirmation + local amendment
            (x, y), got, am = snap_waypoint([x, y], want_z, bvh)
            if am is not None:
                am["waypoint"] = w["name"]
                amendments.append(am)
                print(f"[r7-nav] AMEND {w['name']}: {am['why']}")
                if am.get("failed"):
                    raise RuntimeError(f"{w['name']}: route unexecutable "
                                       "— refusing to fabricate a path")
            z = got if got is not None else want_z
        else:
            got = ray_down(bvh, x, y, want_z + 0.8)
            z = got if got is not None else want_z
        if last_z is None:
            last_z = z
        segs.append((len(pts) - 1 if pts else 0, w["speed_mps"], w["name"]))
        if i == 0:
            pts.append((x, y, z))
            print(f"[r7-nav] {w['name']}: z route {want_z:.3f} "
                  f"-> surface {z:.3f} ({w['surface']})")
            continue
        px, py, pz = pts[-1]
        horiz = math.hypot(x - px, y - py)

        def hug(sx, sy, start_z):
            """Ray-down with a fall-through guard.

            A paddle-stair CENTERLINE falls BETWEEN alternating
            half-treads (ray lands on a tread ~2 steps down, -0.5 m);
            and slab voids fall to the floor (-2.9 m). Both read as a
            DROP far below the held z — a real climbing step never
            does. Treat big drops as a miss and hold last_z.
            """
            nonlocal held_over_void
            hz = ray_down(bvh, sx, sy, start_z)
            if hz is not None and last_z is not None \
                    and hz < last_z - 0.4:
                held_over_void += 1
                return None
            return hz

        if w["surface"] == "stairs":
            # ramp: densify + tread-hug. Ray ceiling is INCREMENTAL
            # (pz + 0.8): using the waypoint's route z here let early
            # samples see the slab band above the stair and teleport to
            # it (the live 2.91-teleport bug). pz+0.8 stays under the
            # slab underside while the band overlaps the stair, and the
            # slab is absent over the stair column beyond y 9.2 anyway.
            n = max(2, int(horiz / STEP) + 1)
            for k in range(1, n + 1):
                t = k / n
                sx = px + (x - px) * t
                sy = py + (y - py) * t
                hz = hug(sx, sy, last_z + 0.8)
                if hz is None:
                    hz = last_z          # bridge tread nosing gaps
                pts.append((sx, sy, hz))
                last_z = hz
        else:
            n = max(1, int(horiz / 0.25) + 1)
            for k in range(1, n + 1):
                t = k / n
                sx = px + (x - px) * t
                sy = py + (y - py) * t
                hz = hug(sx, sy, want_z + 0.8)
                if hz is None:
                    hz = last_z
                pts.append((sx, sy, hz))
                last_z = hz
        print(f"[r7-nav] {w['name']}: z route {want_z:.3f} "
              f"-> surface {z:.3f} at ({x:.2f},{y:.2f}) ({w['surface']})")
    return pts, segs, amendments, held_over_void


def key_navigation(actor_root, pts, segs, fps):
    # clear the R6 treadmill keys on the wrapper (fresh nav keys)
    if actor_root.animation_data is not None:
        actor_root.animation_data_clear()
    actor_root.rotation_euler = (0.0, 0.0, 0.0)

    # arc length per point + segment frame spans
    cum = [0.0]
    for i in range(1, len(pts)):
        a, b = pts[i - 1], pts[i]
        cum.append(cum[-1] + math.dist(a, b))
    # time per segment = length / speed; map frames
    frame_t = []        # per timeline frame -> arc position
    t_total = 0.0
    seg_times = []
    for si in range(len(segs)):
        i0 = segs[si][0]
        i1 = segs[si + 1][0] if si + 1 < len(segs) else len(pts) - 1
        seg_len = cum[i1] - cum[i0]
        seg_times.append((i0, i1, seg_len / segs[si][1], segs[si][1]))
        t_total += seg_len / segs[si][1]
    n_frames = int(math.ceil(t_total * fps)) + 1
    for si, (i0, i1, dt, sp) in enumerate(seg_times):
        print(f"[r7-nav]   seg {si}: pts {i0}..{i1} "
              f"len {cum[i1] - cum[i0]:.2f} m @ {sp} m/s = {dt:.1f}s")

    def arc_at(t):
        acc = 0.0
        for i0, i1, dt, _sp in seg_times:
            if t <= acc + dt or (i0, i1, dt) == seg_times[-1][:3]:
                u = 0.0 if dt == 0 else min(1.0, (t - acc) / dt)
                return cum[i0] + (cum[i1] - cum[i0]) * u
            acc += dt
        return cum[-1]

    def point_at(s):
        # binary search over cum
        lo, hi = 0, len(cum) - 1
        while lo < hi - 1:
            mid = (lo + hi) // 2
            if cum[mid] <= s:
                lo = mid
            else:
                hi = mid
        if cum[hi] <= s:
            return pts[hi]
        a, b = pts[lo], pts[hi]
        u = 0.0 if cum[hi] == cum[lo] else (s - cum[lo]) / (cum[hi] - cum[lo])
        return (a[0] + (b[0] - a[0]) * u,
                a[1] + (b[1] - a[1]) * u,
                a[2] + (b[2] - a[2]) * u)

    for f in range(1, n_frames + 1):
        s = arc_at((f - 1) / fps)
        p = point_at(s)
        actor_root.location = (p[0], p[1], p[2])
        # tangent for yaw (wrapper yaw 0 faces +Y): theta = atan2(tx, ty)
        p2 = point_at(min(cum[-1], s + 0.05))
        tx, ty = p2[0] - p[0], p2[1] - p[1]
        if abs(tx) > 1e-6 or abs(ty) > 1e-6:
            yaw = math.atan2(tx, ty)
        else:
            yaw = actor_root.rotation_euler.z
        actor_root.rotation_euler = (0.0, 0.0, yaw)
        actor_root.keyframe_insert("location", frame=f)
        actor_root.keyframe_insert("rotation_euler", frame=f)
    return n_frames, t_total


def cyclic_walk(arm, n_frames):
    """Walk gait for the whole nav via an NLA strip with repeat.

    Blender 5.2 removed legacy Action.fcurves (slotted-actions rewrite),
    so CYCLE fmodifiers are out; an NLA strip repeating a COPY of the
    walk action is version-stable and keeps the fresh-bake law (the
    imported source action is never touched). The armature's base
    action (R6 idle) is cleared so only the strip drives the rig.
    """
    act = arm.animation_data.action if arm.animation_data else None
    if act is None or "walk" not in act.name.lower():
        cands = [a for a in bpy.data.actions if "walk" in a.name.lower()]
        if not cands:
            raise RuntimeError("no Walk action found for the actor")
        act = cands[0]
    copy = act.copy()                      # fresh-bake law: never mutate
    copy.name = f"{act.name}.NAV"
    act_len = act.frame_range[1] - act.frame_range[0]
    n_loops = max(1, math.ceil((n_frames + 2) / act_len))
    if arm.animation_data is None:
        arm.animation_data_create()
    arm.animation_data.action = None       # strip-only driving
    track = arm.animation_data.nla_tracks.new()
    track.name = "NAV_walk"
    strip = track.strips.new(copy.name, 1, copy)
    strip.repeat = float(n_loops)
    strip.frame_end = 1 + act_len * n_loops
    return copy, n_loops


def audit(root, bvh, n_frames, fps):
    """Foot-gap audit that honestly separates support-boundary
    crossings (the intentional tread->slab edge step over the stairwell
    opening edge) from genuine mid-void floats."""
    gaps = []
    floats = []
    paddle = 0
    excused = 0
    for f in range(1, n_frames + 1, 4):    # every ~1/6 s
        bpy.context.scene.frame_set(f)
        loc = root.matrix_world.translation
        hz = ray_down(bvh, loc.x, loc.y, loc.z + 0.08)
        if hz is None:
            continue
        gap = loc.z - hz
        gaps.append(round(gap, 4))
        if gap > FOOT_TOL:
            # supported nearby? two tiers:
            #  fine r in {0.06, 0.12}, tol 0.25: paddle-stair CENTERLINE
            #    — the 0.2 m-wide stair's half-treads meet AT x=3.40, so
            #    the centerline ray grazes the shared edge crack, and
            #    the nearest tread top sits one paddle step (0.2 m)
            #    above/below the body center (one foot up, one down —
            #    the defining paddle gait). Supported = lateral treads.
            #  coarse r=0.35, tol 0.1: support-boundary edge crossing
            #    (the intentional tread->slab step)
            near = False
            for pr in (0.06, 0.12):
                for ang in range(0, 360, 45):
                    a = math.radians(ang)
                    nx, ny = loc.x + pr * math.cos(a), \
                        loc.y + pr * math.sin(a)
                    nh = ray_down(bvh, nx, ny, loc.z + 0.4)
                    if nh is not None and abs(nh - loc.z) < 0.25:
                        near = True
                        paddle += 1
                        break
                if near:
                    break
            if not near:
                for ang in range(0, 360, 45):
                    a = math.radians(ang)
                    nx, ny = loc.x + EDGE_TOL * math.cos(a), \
                        loc.y + EDGE_TOL * math.sin(a)
                    nh = ray_down(bvh, nx, ny, loc.z + 0.4)
                    if nh is not None and abs(nh - loc.z) < 0.1:
                        near = True
                        excused += 1
                        break
            if not near:
                floats.append({"frame": f, "gap_m": round(gap, 3),
                               "xy": [round(loc.x, 2), round(loc.y, 2)]})
    bpy.context.scene.frame_set(1)
    if not gaps:
        return {"foot_gaps": [], "note": "no raycast hits — audit void"}
    return {
        "samples": len(gaps),
        "max_gap_m": max(gaps),
        "mean_gap_m": round(sum(gaps) / len(gaps), 5),
        "over_tolerance": len([g for g in gaps if g > FOOT_TOL]),
        "tolerance_m": FOOT_TOL,
        "paddle_centerline_excused": paddle,
        "boundary_crossings_excused": excused,
        "true_floats": floats[:20],
        "true_float_count": len(floats),
        "foot_gaps_sample": gaps[::12],
    }


def main():
    bpy.ops.wm.open_mainfile(filepath=SRC)
    scene = bpy.context.scene
    route = json.load(open(ROUTE))
    if route["stop_and_flag"]:
        raise RuntimeError("route has STOP-AND-FLAG entries — refuse to "
                           "execute (contract)")
    fps = scene.render.fps

    bvh = build_bvhs(route["labels_used"])
    pts, segs, amendments, held = densify(route, bvh)
    print(f"[r7-nav] dense path: {len(pts)} samples, "
          f"{len(segs)} segments, {len(amendments)} amendment(s), "
          f"{held} held-over-drop samples")

    root = bpy.data.objects.get("Driver.Root")
    if root is None:
        raise RuntimeError("Driver.Root wrapper missing")
    arm = bpy.data.objects.get("Driver.Rig")
    if arm is None:
        raise RuntimeError("Driver.Rig armature missing")

    n_frames, t_total = key_navigation(root, pts, segs, fps)
    walk, n_loops = cyclic_walk(arm, n_frames)
    scene.frame_start, scene.frame_end = 1, n_frames
    scene.frame_set(1)
    print(f"[r7-nav] keyed {n_frames} frames ({t_total:.1f}s @ {fps}fps); "
          f"walk action {walk.name} (cycled)")

    rep = {
        "route": ROUTE,
        "frames": n_frames,
        "duration_s": round(t_total, 2),
        "fps": fps,
        "segments": [{"name": s[2], "speed_mps": s[1]} for s in segs],
        "amendments": amendments,
        "held_over_drop_samples": held,
        "walk_action": walk.name,
        "walk_loops": n_loops,
        "audit": audit(root, bvh, n_frames, fps),
    }
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    json.dump(rep, open(REPORT, "w"), indent=2)
    a = rep["audit"]
    print(f"[r7-nav] audit: {a['samples']} samples, max gap "
          f"{a.get('max_gap_m', '?')} m, over-tolerance "
          f"{a.get('over_tolerance', '?')}")

    bpy.ops.wm.save_as_mainfile(filepath=DST, compress=True)
    print(f"[r7-nav] saved {DST}")


main()
