"""r7_route_planner.py — BLIND route planner: manifest-only level navigation.

R7 centerpiece (the user's real goal): prove a NON-VISION agent can plan
floor-to-floor navigation on the labeled level using ONLY the handoff
manifest (ids + kit_labels + world_bboxes). No bpy. No renders. If this
script cannot decide something, it does NOT guess — it appends to
stop_and_flag[] with the manifest evidence (AGENTS.md EXECUTION CONTRACT).

What it does (all derivable from labels + bboxes):
  1. finds the walkable architecture: floor / stairs / mezzanine (labels)
  2. finds the actor (Driver.Mannequin — feet at bbox min.z)
  3. infers the stair RUN AXIS (longer horizontal extent) and DIRECTION
     by adjacency: the stair end touching the mezzanine slab edge is the
     TOP (people arrive onto the slab). Ambiguous => STOP-AND-FLAG.
  4. emits a waypoint polyline: actor -> approach -> stair base -> ramp
     to stair top -> mezzanine arrival -> walk-in (bed-avoidance via
     manifest bboxes).
  5. declares assumptions + what the EXECUTOR (vision side) must refine:
     tread-hug raycast, clearance checks, final look.

Output: route_request.json (the contract the executor consumes).

Run:  python3 scripts/r7_route_planner.py [--manifest PATH] [--out PATH]
"""
import argparse
import json
import math
import os
import sys


# ---------------------------------------------------------------- helpers
def bbox_center(bb):
    return [(bb["min"][i] + bb["max"][i]) / 2 for i in range(3)]


def dist2d(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def find_by_label(manifest, label):
    rows = [r for r in manifest
            if r.get("kit_label") == label and r["type"] == "MESH"]
    if not rows:
        return None
    if len(rows) > 1:
        # deterministic: largest footprint (walkable surfaces dominate)
        rows.sort(key=lambda r: (r["world_bbox"]["max"][0]
                                 - r["world_bbox"]["min"][0])
                 * (r["world_bbox"]["max"][1] - r["world_bbox"]["min"][1]),
                 reverse=True)
    return rows[0]


def find_actor(manifest, name="Driver"):
    meshes = [r for r in manifest
              if r["type"] == "MESH" and r["id"].startswith(name + ".")
              and "Mannequin" in r["id"]]
    return meshes[0] if meshes else None


def infer_stair_direction(stair, slab):
    """Which horizontal axis is the run, and which end is the TOP?

    Rule: run axis = the stair's longer horizontal extent. The stair end
    ADJACENT to the mezzanine slab's span on that axis (gap < 0.2 m) is
    the TOP (arrival). Returns (axis, top_is_max_end) or (None, None).
    """
    ext = {i: stair["world_bbox"]["max"][i] - stair["world_bbox"]["min"][i]
           for i in range(2)}
    axis = 0 if ext[0] > ext[1] else 1
    smin = stair["world_bbox"]["min"][axis]
    smax = stair["world_bbox"]["max"][axis]
    kmin = slab["world_bbox"]["min"][axis]
    kmax = slab["world_bbox"]["max"][axis]
    tol = 0.2
    # Decide ONLY when the stair abuts the slab from OUTSIDE its span:
    # the touching end is then necessarily the TOP (arrival). A stair
    # whose span overlaps/lies inside the slab span is bbox-ambiguous —
    # an abutting end could equally be its BASE (R7 live case:
    # Plane.003 starts at the slab's front edge and runs 5.3 m under
    # it) — return None so the principal resolves it (STOP-AND-FLAG or
    # vision_stair_override.json).
    if smax <= kmin + tol:
        return axis, True          # abuts slab from -side; top at +end
    if smin >= kmax - tol:
        return axis, False         # abuts slab from +side; top at -end
    return None, None              # overlapping/inside: ambiguous


# ---------------------------------------------------------------- planner
def plan(manifest, actor_name="Driver", vision_override=None):
    route = {
        "requested_by": "r7_route_planner (BLIND — manifest-only, no vision)",
        "labels_used": {},
        "waypoints": [],
        "ramp_model": ("linear z between stair base and stair top; the "
                       "EXECUTOR must tread-hug via downward raycast "
                       "against the stairs mesh (tread profile is not "
                       "expressible in bboxes)"),
        "assumptions": [
            "upright walk gait (Walk_Loop) on the stair run; "
            "feet do NOT per-tread match — nav-follow approximation, "
            "cosmetic slide tolerated",
            "route crosses open labeled floor between actor and stair "
            "base; clearance is vision-side verification, not a blind "
            "guarantee",
        ],
        "requires_executor": [
            "tread-hug raycast (z refinement on the stair ramp)",
            "surface z confirmation at approach + mezzanine waypoints",
            "per-frame foot-gap audit (numerical) + renders (visual)",
        ],
        "stop_and_flag": [],
        "vision_assisted": False,
    }

    floor = find_by_label(manifest, "floor")
    stair = find_by_label(manifest, "stairs")
    slab = find_by_label(manifest, "mezzanine")
    actor = find_actor(manifest, actor_name)
    for name, row in (("floor", floor), ("stairs", stair),
                      ("mezzanine", slab), ("actor", actor)):
        route["labels_used"][name] = row["id"] if row else None

    if not all((floor, stair, slab, actor)):
        missing = [n for n, r in (("floor", floor), ("stairs", stair),
                                  ("mezzanine", slab),
                                  ("actor", actor)) if r is None]
        route["stop_and_flag"].append({
            "why": "missing labeled walkable architecture or actor",
            "missing": missing,
            "evidence": "kit_label scan over manifest rows",
        })
        return route

    fz = floor["world_bbox"]["max"][2]          # floor top (walk surface)
    mz = slab["world_bbox"]["max"][2]           # mezzanine top
    if mz - fz < 1.5:
        route["stop_and_flag"].append({
            "why": "mezzanine rise implausible for a storey",
            "evidence": f"mezz top {mz:.2f} vs floor top {fz:.2f}"})
        return route

    sbb = stair["world_bbox"]
    # tolerance 0.25: the final tread-to-slab step-up can be ~0.15 m
    if not (sbb["min"][2] <= fz + 0.1 and sbb["max"][2] >= mz - 0.25):
        route["stop_and_flag"].append({
            "why": "stair z-span does not connect floor to mezzanine",
            "evidence": (f"stairs z [{sbb['min'][2]:.2f},{sbb['max'][2]:.2f}]"
                         f" vs floor {fz:.2f} mezz {mz:.2f}")})
        return route

    axis, top_is_max = infer_stair_direction(stair, slab)
    if axis is None and vision_override:
        # VISION RESOLUTION of a bbox-ambiguous stair (recorded, not
        # hidden): the principal supplies the top end with evidence.
        axis = 0 if (sbb["max"][0] - sbb["min"][0]) \
            > (sbb["max"][1] - sbb["min"][1]) else 1
        top_is_max = vision_override.get("top_at_max_end")
        route["vision_assisted"] = True
        route["stair_direction_inference"] = {
            "run_axis": "xyz"[axis], "top_at_max_end": top_is_max,
            "rule": "VISION OVERRIDE (bbox case ambiguous): "
                    + vision_override.get("evidence", "unspecified"),
        }
    if axis is None:
        route["stop_and_flag"].append({
            "why": ("stair is not adjacent to the mezzanine slab on its "
                    "run axis — arrival edge cannot be derived from "
                    "bboxes alone (VISION-REQUIRED; supply "
                    "--vision-override json to resolve)"),
            "evidence": {"stairs": sbb, "mezzanine": slab["world_bbox"]}})
        return route
    if "stair_direction_inference" not in route:
        route["stair_direction_inference"] = {
            "run_axis": "xyz"[axis], "top_at_max_end": top_is_max,
            "rule": "stair end adjacent to mezzanine slab edge = TOP",
        }

    sxy = bbox_center(sbb)
    run_xy = [sxy[0], sxy[1]]
    # top_is_max: base at the MIN end, top at the MAX end, walk +dir
    base_y = sbb["min"][axis] if top_is_max else sbb["max"][axis]
    top_y = sbb["max"][axis] if top_is_max else sbb["min"][axis]
    d = 1.0 if top_is_max else -1.0             # walk direction along run
    base_pt = list(run_xy)
    base_pt[axis] = base_y
    top_pt = list(run_xy)
    top_pt[axis] = top_y

    ab = actor["world_bbox"]
    actor_xy = bbox_center(ab)[:2]
    actor_z = ab["min"][2]                      # feet

    approach = list(base_pt)
    approach[axis] = base_y - d * 0.8           # 0.8 m back from base

    # waypoints (executor refines z by raycast; ramp z here is nominal)
    wp = [
        {"name": "W0_actor", "xy": [round(v, 3) for v in actor_xy],
         "z": round(actor_z, 3), "surface": "floor",
         "speed_mps": 1.0, "note": "current actor feet position"},
        {"name": "W1_approach",
         "xy": [round(v, 3) for v in approach],
         "z": round(fz, 3), "surface": "floor", "speed_mps": 1.0,
         "note": "line up with the stair run"},
        {"name": "W2_stair_base", "xy": [round(v, 3) for v in base_pt],
         "z": round(fz, 3), "surface": "stairs", "speed_mps": 0.5,
         "note": "first tread"},
    ]
    ramp = {"name": "W3_stair_top", "xy": [round(v, 3) for v in top_pt],
            "z": round(mz - 0.01, 3), "surface": "stairs",
            "speed_mps": 0.5,
            "note": "top tread; z nominal — executor tread-hugs"}
    wp.append(ramp)

    arrive = list(top_pt)
    arrive[axis] = top_y + d * 1.2              # step onto the slab
    wp.append({"name": "W4_mezzanine",
               "xy": [round(v, 3) for v in arrive],
               "z": round(mz, 3), "surface": "mezzanine",
               "speed_mps": 1.0, "note": "arrival on the upper level"})

    # walk-in: 1.2 m deeper, clamped inside the mezzanine bbox (a walk
    # off the slab end is not derivable-safe from bboxes alone), with
    # bed-avoidance from manifest bboxes
    walkin = list(arrive)
    if top_is_max:
        walkin[axis] = min(arrive[axis] + d * 1.2,
                           slab["world_bbox"]["max"][axis] - 0.3)
    else:
        walkin[axis] = max(arrive[axis] - d * 1.2,
                           slab["world_bbox"]["min"][axis] + 0.3)
    blocked = False
    for r in manifest:
        if r.get("kit_label") in ("bed", "floor_lamp", "pendant_light") \
                and r["type"] == "MESH":
            bb = r["world_bbox"]
            if (bb["min"][0] - 0.3 < walkin[0] < bb["max"][0] + 0.3
                    and bb["min"][1] - 0.3 < walkin[1] < bb["max"][1] + 0.3
                    and bb["min"][2] < mz + 0.05 < bb["max"][2] + 0.3):
                blocked = True
                break
    if blocked:
        # fall back: stop 0.3 m past arrival
        walkin[axis] = arrive[axis] + d * 0.3
        note = "walk-in shortened (bed/lamp bbox in the way — manifest)"
    else:
        note = "walk-in into the upper room"
    wp.append({"name": "W5_walkin", "xy": [round(v, 3) for v in walkin],
               "z": round(mz, 3), "surface": "mezzanine",
               "speed_mps": 1.0, "note": note})

    route["waypoints"] = wp
    return route


def main():
    ap = argparse.ArgumentParser()
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument("--manifest",
                    default=os.path.join(root, "output/r6/handoff/"
                                              "look_manifest.json"))
    ap.add_argument("--out",
                    default=os.path.join(root, "output/r7/route_request.json"))
    ap.add_argument("--vision-override", default=None,
                    help="json file {top_at_max_end: bool, evidence: str} "
                         "resolving a bbox-ambiguous stair direction")
    args = ap.parse_args()

    data = json.load(open(args.manifest))
    manifest = data["manifest"] if isinstance(data, dict) else data

    override = None
    if args.vision_override and os.path.exists(args.vision_override):
        override = json.load(open(args.vision_override))

    route = plan(manifest, vision_override=override)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(route, open(args.out, "w"), indent=2)

    print(f"[r7-planner] route -> {args.out}")
    for k, v in route["labels_used"].items():
        print(f"[r7-planner]   {k:10s} = {v}")
    if route.get("stair_direction_inference"):
        si = route["stair_direction_inference"]
        print(f"[r7-planner]   stair runs along {si['run_axis']}, "
              f"top at {'max' if si['top_at_max_end'] else 'min'} end")
    for w in route["waypoints"]:
        print(f"[r7-planner]   {w['name']:14s} xy={w['xy']} z={w['z']} "
              f"({w['surface']}, {w['speed_mps']} m/s)")
    for f in route["stop_and_flag"]:
        print(f"[r7-planner]   STOP-AND-FLAG: {f['why']}")
    if route["stop_and_flag"]:
        sys.exit(4)
    print("[r7-planner] route is COMPLETE (no flags)")


if __name__ == "__main__":
    main()
