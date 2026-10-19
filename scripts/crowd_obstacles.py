"""
crowd_obstacles.py — the scene-geometry -> crowd-obstacle bridge (kit).

THE GAP this closes (user-reported, s41): placed kit geometry (import-
statue statues, DJ props, JT vehicles, CJ buildings — or ANY scene
mesh) carried NO crowd-obstacle declaration, so baked crowds walked
THROUGH placed objects. Crowd authoring (CrowdScene) accepts
`blocked: List[Blocked]` (navmesh exclusion rects) but every rect was
hand-typed. This module derives the rects from the scene.

ENGINE TRUTH (live-audited + live-measured s41, reviews r2 B1 +
O11 forensics): the ONLY obstacle mechanism a bake honors today is
`Blocked` -> navmesh walls + integrate-phase wall pushout — and both
findings below are LIVE-MEASURED (5-seed bake study, tests O11):
  1. NO PATH PLANNING — their own CROWD_GAP_1_analysis.md capability
     matrix: "Path planning: None (point-target only)". An obstacle
     across the spawn->destination line = TOTAL JAM: 0/20 agents
     reach the destination across seeds 11-15. Agents need A* +
     corridor + string-pulling on the navmesh (upstream issue #1).
  2. PRESSURE-SOFT PUSHOUT — under jam pressure agents penetrate the
     obstacle up to ~0.59 m (max penetration 0.316/0.363/0.590/0.014/
     0.220 m across seeds 11-15; none fully traverse). The
     integrate-phase pushout is not a hard wall (upstream issue #2).
`CrowdScene.force_fields` are SILENTLY INERT at bake time (bake()
never calls the fields adapter — M2.5 future work, upstream issue
#3). Therefore:
  - this bridge emits Blocked rects ONLY (no disc twins);
  - ANIMATED objects are REFUSED (the engine cannot track a moving
    obstacle in a bake; upstream #3 + #6) — place a static stand-in
    or wait for the wiring.
The battery PINS both findings (O11c flips loudly when routing
lands; O11d records penetration telemetry).

  HOST-side  (no bpy — plain python3 or inside Blender):
    obstacles_from_specs(...)  spec list -> {"blocked": [...], "report": [...]}
                               (pure math + validation; the emission law)
  BLENDER-side (via blrun.sh --background --python scripts/crowd_obstacles.py --):
    scan                       --collection X [--prefixes a,b] --walkable
                               id:bounds [...] [--margin M] [--z-band lo,hi]
                               [--json] — evaluates world footprints and
                               prints the Blocked declarations

THE LAWS (fail-closed, teacher messages — CrowdObstacleRefused):
  SELECTION   the scan requires --collection and/or --prefixes (both
              empty = REFUSED — an implicit whole-scene scan would make
              cameras/lights/rigs obstacles); MESH objects only.
  Z-BAND      only objects whose world [zmin, zmax] intersects the
              caller-supplied WORLD z-band (default 0.0..1.8 m) become
              obstacles. The band is WORLD-z around scene origin (the
              engine's Walkable carries no z) — an elevated walkable
              (2nd floor) must pass its own band or every object is
              skipped. Skips are REPORTED per-object (never silent).
  MARGIN      the world-bbox XY footprint grows by `margin` (default
              0.15 m ~ half a personal-space radius), then is CLIPPED
              to the walkable (the Rust compiler requires
              blocked ⊆ walkable — InvalidRange otherwise). Rotated
              objects over-block: the v1 IR is axis-aligned only
              (upstream issue #1); margin is the tunable.
  ANIMATED    objects with any animation signal (fcurves via
              blender_kit.iter_all_fcurves — 5.x multi-slot aware —
              OR animated parents OR a frame_start-vs-frame_end bbox
              mismatch >= animated_bbox_epsilon, which catches drivers
              and constraints) are REFUSED with the upstream pointer.
  FOOTPRINT   degenerate refusals: zero/NaN extents, footprint below
              min_footprint (default 0.05 m — pebbles are steering
              noise), margin < 0.
  IDS         `obst_<slug>` prefix + deterministic collision suffixes
              (sorted -2, -3, ...): the IR id namespace is GLOBAL
              across walkable/blocked/spawn/destination/portal —
              duplicates are Rust DuplicateId errors.
  DETERMINISM objects sorted by name; stable ordering; byte-stable
              JSON emission.

Plugs into (no engine changes): CrowdScene.walkables/blocked authoring
via the kit's vendored re-export (`from scripts.crowd import Blocked,
Walkable` — the s41 19-name contract) and kit_to_bgyss_project_ir
round-trips the output (the IR's blocked input schema).

Upstream engine gaps (filed, never pushed — crowd-kit's repo):
  #1 PATH PLANNING: navmesh A* + corridor + string-pulling (their own
     gap-analysis strategy) — the headline jam finding
  #2 hard-clamp the integrate-phase pushout under pressure (0.59 m
     penetration measured)
  #3 wire the M2.5 per-tick fields hook into bake() + frame_set(t)
  #4 oriented/polygon blocked regions (v1 = AABB only)
  #5 mesh-geometry walkables (navmesh from real geometry)
  #6 moving-obstacle velocity into ORCA (anticipatory avoidance)
  #7 ForceField.t_active 45 s default contradicts the unbounded law
     (crowd_fields.py s28-a4 P3a)
  #8 environment.py Blocked "+ repulsion zone" docstring claim has no
     runtime consumer (walls only)

Design: DESIGN_s41_crowd_obstacles.md (r2, review agent-5c01693d).
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys

# --------------------------------------------------------------------------- #
#  Constants / exceptions
# --------------------------------------------------------------------------- #
DEFAULT_MARGIN = 0.15          # m — ~half a personal-space radius
DEFAULT_Z_BAND = (0.0, 1.8)    # m — WORLD z; caller matches the floor
DEFAULT_MIN_FOOTPRINT = 0.05   # m — pebbles are steering noise
DEFAULT_ANIM_EPSILON = 1e-4    # m — bbox drift across frames = animated
ID_PREFIX = "obst_"


class CrowdObstacleRefused(Exception):
    """Teacher-grade refusal (fail-closed): the message names the exact
    problem AND the fix. The CLI turns this into '[crowd-obst] REFUSED:
    ...' + exit 2 — never a traceback."""


# --------------------------------------------------------------------------- #
#  Host-side: specs -> Blocked declarations (pure, no bpy)
# --------------------------------------------------------------------------- #
class ObstacleSpec:
    """One scanned object's world-space footprint (host-side view of a
    Blender mesh object). Immutable-by-convention."""

    __slots__ = ("name", "cx", "cy", "hx", "hy", "zmin", "zmax", "animated")

    def __init__(self, name, cx, cy, hx, hy, zmin, zmax, animated=False):
        self.name = str(name)
        self.cx = float(cx)
        self.cy = float(cy)
        self.hx = float(hx)
        self.hy = float(hy)
        self.zmin = float(zmin)
        self.zmax = float(zmax)
        self.animated = bool(animated)

    def __repr__(self):  # pragma: no cover — debugging aid
        return (f"ObstacleSpec({self.name!r}, c=({self.cx:.3f},{self.cy:.3f}), "
                f"h=({self.hx:.3f},{self.hy:.3f}), z=({self.zmin:.3f},"
                f"{self.zmax:.3f}), animated={self.animated})")


def _slug(name: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", str(name)).strip("_").lower()
    return s or "unnamed"


def _walkable_bounds(w):
    """Accept ('id', ((minx,miny),(maxx,maxy))) tuples or objects with
    .id/.bounds (the vendored Walkable dataclass)."""
    if isinstance(w, (tuple, list)) and len(w) == 2:
        return str(w[0]), w[1]
    wid = getattr(w, "id", None)
    bnd = getattr(w, "bounds", None)
    if wid is None or bnd is None:
        raise CrowdObstacleRefused(
            f"walkable entry {w!r} must be (id, ((minx,miny),(maxx,maxy))) "
            f"or a Walkable-like object with .id/.bounds")
    return str(wid), bnd


def obstacles_from_specs(specs, walkables, *, margin=DEFAULT_MARGIN,
                         z_band=DEFAULT_Z_BAND,
                         min_footprint=DEFAULT_MIN_FOOTPRINT,
                         emit_anyway=False):
    """THE EMISSION LAW: spec list + walkable list -> Blocked
    declarations + a per-object report.

    Returns {"blocked": [Blocked-like dicts...], "report": [...]} —
    each blocked dict carries id/walkable_id/bounds (the IR input
    schema); each report row carries name/decision/reason.

    Failure modes (two kinds, by design):
      REFUSED (raises CrowdObstacleRefused) — caller-level errors:
        margin < 0, NaN specs, no walkables, a degenerate-but-kept
        footprint, or an animated spec (unless emit_anyway=True —
        then it is a loud REPORTED skip instead; the escape hatch
        exists because a busy scene should not brick the scan).
      SKIP-WITH-REASON (report rows, never raises) — object-level
        non-errors: z-band miss, no walkable overlap, footprint under
        min_footprint (pebbles).
    """
    if margin < 0:
        raise CrowdObstacleRefused(
            f"margin must be >= 0 (got {margin}) — the margin GROWS the "
            f"footprint for personal space; there is no negative margin.")
    if not walkables:
        raise CrowdObstacleRefused(
            "no walkables given — every Blocked region must sit inside a "
            "walkable (the Rust compiler requires blocked ⊆ walkable). "
            "Pass (id, ((minx,miny),(maxx,maxy))) entries for each "
            "walkable region the crowd can occupy.")
    wl = [_walkable_bounds(w) for w in walkables]
    zlo, zhi = float(z_band[0]), float(z_band[1])
    if not (zlo < zhi):
        raise CrowdObstacleRefused(
            f"z_band must be (low, high) with low < high, got {z_band!r} "
            f"— the band selects which objects intersect the crowd's "
            f"floor in WORLD z.")

    blocked: list[dict] = []
    report: list[dict] = []
    used_ids: set[str] = set()

    def _next_id(base: str) -> str:
        """Deterministic collision suffixes: -2, -3, ... (sorted)."""
        if base not in used_ids:
            used_ids.add(base)
            return base
        n = 2
        while f"{base}-{n}" in used_ids:
            n += 1
        sid = f"{base}-{n}"
        used_ids.add(sid)
        return sid

    for spec in sorted(specs, key=lambda s: s.name):
        # NaN / degenerate guards (REFUSED — data corruption, not noise)
        vals = (spec.cx, spec.cy, spec.hx, spec.hy, spec.zmin, spec.zmax)
        if any(isinstance(v, float) and math.isnan(v) for v in vals):
            raise CrowdObstacleRefused(
                f"spec {spec.name!r} carries NaN geometry — the scan "
                f"produced a corrupt footprint; re-run the scan (this is "
                f"a bug in the scanner if it reproduces).")
        if spec.hx <= 0 or spec.hy <= 0:
            raise CrowdObstacleRefused(
                f"spec {spec.name!r} has non-positive half-extents "
                f"(hx={spec.hx}, hy={spec.hy}) — a zero-area footprint "
                f"cannot be an obstacle. If the object is genuinely flat "
                f"along one axis, give it min_footprint of slack; if it "
                f"is a camera/light, filter by type at scan time.")

        # animated law (B1): the engine cannot track moving obstacles
        if spec.animated and not emit_anyway:
            raise CrowdObstacleRefused(
                f"object {spec.name!r} is ANIMATED — the engine's bake "
                f"cannot track moving obstacles today (force_fields are "
                f"not wired into bake; upstream issue #0/#3). Place a "
                f"static stand-in, or re-run with emit_anyway=True to "
                f"scan the REST of the scene (this object is reported "
                f"as skipped, loudly).")
        if spec.animated:
            report.append({"name": spec.name, "decision": "skipped-animated",
                           "reason": "engine cannot track animated obstacles "
                                     "at bake time (upstream #0/#3); "
                                     "emit_anyway=True was set"})
            continue

        # z-band law (skip-with-reason: floor mismatch is scene content,
        # not corruption — the caller tunes the band)
        if spec.zmax <= zlo or spec.zmin >= zhi:
            report.append({"name": spec.name, "decision": "skipped-zband",
                           "reason": f"world z [{spec.zmin:.3f},{spec.zmax:.3f}] "
                                     f"misses the band [{zlo:.3f},{zhi:.3f}] "
                                     f"(elevated walkable? pass its band)"})
            continue

        # footprint under min (skip-with-reason: pebbles are noise)
        if max(spec.hx, spec.hy) < min_footprint:
            report.append({"name": spec.name, "decision": "skipped-small",
                           "reason": f"half-extent {max(spec.hx, spec.hy):.3f} m "
                                     f"< min_footprint {min_footprint} m "
                                     f"(steering noise, not an obstacle)"})
            continue

        # margin-grown AABB
        gx0, gx1 = spec.cx - spec.hx - margin, spec.cx + spec.hx + margin
        gy0, gy1 = spec.cy - spec.hy - margin, spec.cy + spec.hy + margin

        # per-walkable clip (B3): one Blocked per overlapping walkable
        emitted = 0
        for wid, ((wx0, wy0), (wx1, wy1)) in wl:
            cx0, cx1 = max(gx0, wx0), min(gx1, wx1)
            cy0, cy1 = max(gy0, wy0), min(gy1, wy1)
            if cx0 >= cx1 or cy0 >= cy1:
                continue
            cw, ch = (cx1 - cx0) / 2.0, (cy1 - cy0) / 2.0
            if max(cw, ch) < min_footprint:
                continue          # clipped to a sliver on THIS walkable
            blocked.append({
                "id": _next_id(f"{ID_PREFIX}{_slug(spec.name)}"),
                "walkable_id": wid,
                "bounds": ((round(cx0, 6), round(cy0, 6)),
                           (round(cx1, 6), round(cy1, 6))),
            })
            emitted += 1
        if emitted == 0:
            report.append({"name": spec.name, "decision": "skipped-nooverlap",
                           "reason": "margin-grown footprint overlaps no "
                                     "walkable (or clips to a sliver below "
                                     f"min_footprint {min_footprint} m)"})
        else:
            report.append({"name": spec.name, "decision": "blocked",
                           "reason": f"{emitted} Blocked region(s) "
                                     f"(margin {margin} m, clipped to "
                                     f"walkable(s))"})
    return {"blocked": blocked, "report": report}


# --------------------------------------------------------------------------- #
#  Blender-side: the scan (bpy; lazy import — module stays host-importable)
# --------------------------------------------------------------------------- #
def _bpy():
    try:
        import bpy  # noqa
        return bpy
    except ImportError:
        raise CrowdObstacleRefused(
            "this subcommand needs Blender — run it via "
            "./scripts/blrun.sh --background --python "
            "scripts/crowd_obstacles.py -- scan ...")


def _iter_collection_objs(coll, seen=None):
    """Recursive collection walk (children collections included)."""
    seen = seen if seen is not None else set()
    if coll.name in seen:
        return
    seen.add(coll.name)
    for o in coll.objects:
        yield o
    for c in coll.children:
        yield from _iter_collection_objs(c, seen)


def _world_footprint(obj, depsgraph=None):
    """World AABB via matrix_world x local-bbox corners (B8: evaluated
    TRANSFORM, not a full mesh eval — cheap, modifier-safe enough for
    footprints; the kit's placement_lib cache-key precedent)."""
    bpy = _bpy()
    ob = obj.evaluated_get(depsgraph) if depsgraph is not None else obj
    mw = ob.matrix_world.copy()
    bb = ob.bound_box            # 8 local corners
    xs, ys, zs = [], [], []
    for c in bb:
        v = mw @ _v3(bpy, c)
        xs.append(v.x)
        ys.append(v.y)
        zs.append(v.z)
    return (sum(xs) / 8.0, sum(ys) / 8.0,
            (max(xs) - min(xs)) / 2.0, (max(ys) - min(ys)) / 2.0,
            min(zs), max(zs))


def _v3(bpy, c):
    from mathutils import Vector
    return Vector((c[0], c[1], c[2]))


def _is_animated(obj, scene, epsilon=DEFAULT_ANIM_EPSILON):
    """Animation detection with THREE probes (B7): fcurves (multi-slot
    aware via blender_kit.iter_all_fcurves on the ACTION), animated
    parents, and a frame_start-vs-frame-end world-bbox sample (catches
    drivers, constraints, physics — the fcurve probe alone misses
    them)."""
    ad = obj.animation_data
    fcs = []
    if ad is not None and ad.action is not None:
        try:
            import blender_kit as bk
            fcs = list(bk.iter_all_fcurves(ad.action))
        except Exception:                      # noqa: BLE001 — 4.x path
            fcs = list(ad.action.fcurves)
    if fcs:
        return True
    p = obj.parent
    while p is not None:
        pad = p.animation_data
        if pad and pad.action:
            return True
        p = p.parent
    # bbox drift probe (drivers/constraints/physics)
    f0, f1 = scene.frame_start, scene.frame_end
    if f0 == f1:
        return False
    try:
        import bpy
        scene.frame_set(int(f0))
        bpy.context.view_layer.update()
        a = _world_footprint(obj)
        scene.frame_set(int(f1))
        bpy.context.view_layer.update()
        b = _world_footprint(obj)
        drift = max(abs(x - y) for x, y in zip(a[:4], b[:4]))
        scene.frame_set(int(f0))
        bpy.context.view_layer.update()
        return drift >= epsilon
    except Exception:                          # noqa: BLE001 — conservative
        return True


def scan_objects(objs, walkables, *, margin=DEFAULT_MARGIN,
                 z_band=DEFAULT_Z_BAND,
                 min_footprint=DEFAULT_MIN_FOOTPRINT,
                 emit_anyway=False):
    """MESH objects -> ObstacleSpec list -> the emission law.
    Non-MESH objects are reported as skipped-type (never obstacles)."""
    bpy = _bpy()
    scene = bpy.context.scene
    dg = bpy.context.evaluated_depsgraph_get()
    specs, type_skips = [], []
    for o in objs:
        if o.type != "MESH":
            type_skips.append({"name": o.name, "decision": "skipped-type",
                               "reason": f"type {o.type} (MESH only)"})
            continue
        cx, cy, hx, hy, zmin, zmax = _world_footprint(o, dg)
        specs.append(ObstacleSpec(o.name, cx, cy, hx, hy, zmin, zmax,
                                  animated=_is_animated(o, scene)))
    out = obstacles_from_specs(
        specs, walkables, margin=margin, z_band=z_band,
        min_footprint=min_footprint, emit_anyway=emit_anyway)
    out["report"] = type_skips + out["report"]
    return out


def scan_scene(*, collections=(), prefixes=(), walkables=(), **kwargs):
    """SELECTION LAW: collections and/or prefixes (both empty = REFUSED
    — an implicit whole-scene scan would make cameras/lights/rigs
    obstacles). Walks collections recursively; prefix = startswith."""
    if not collections and not prefixes:
        raise CrowdObstacleRefused(
            "scan needs --collection and/or --prefixes — an implicit "
            "whole-scene scan would turn cameras, lights and rigs into "
            "obstacles. Point the scan at what actually blocks the "
            "crowd (e.g. --collection Crowd.Obstacles or --prefixes "
            "Statue,Vehicle).")
    bpy = _bpy()
    objs, seen = [], set()
    for cname in collections:
        coll = bpy.data.collections.get(cname)
        if coll is None:
            raise CrowdObstacleRefused(
                f"collection {cname!r} not found (scene collections: "
                f"{[c.name for c in bpy.data.collections] or 'none'})")
        for o in _iter_collection_objs(coll):
            if o.name not in seen:
                seen.add(o.name)
                objs.append(o)
    if prefixes:
        for o in bpy.data.objects:
            if o.name.startswith(tuple(prefixes)) and o.name not in seen:
                seen.add(o.name)
                objs.append(o)
    if not objs:
        raise CrowdObstacleRefused(
            f"selection matched no objects (collections={list(collections)}, "
            f"prefixes={list(prefixes)}) — nothing to scan.")
    return scan_objects(objs, walkables, **kwargs)


# --------------------------------------------------------------------------- #
#  CLI
# --------------------------------------------------------------------------- #
def _parse_walkable(s: str):
    """'id:minx,miny:maxx,maxy' -> (id, ((minx,miny),(maxx,maxy)))."""
    try:
        wid, lo, hi = s.split(":")
        (x0, y0), (x1, y1) = (
            tuple(float(v) for v in lo.split(",")),
            tuple(float(v) for v in hi.split(",")))
        return wid.strip(), ((x0, y0), (x1, y1))
    except Exception:
        raise CrowdObstacleRefused(
            f"--walkable expects 'id:minx,miny:maxx,maxy', got {s!r} "
            f"(e.g. 'concourse:-10,-10:10,10')")


def main(argv=None) -> int:
    argv = list(sys.argv[sys.argv.index("--") + 1:]
                if argv is None and "--" in sys.argv
                else (argv if argv is not None else sys.argv[1:]))
    ap = argparse.ArgumentParser(
        prog="crowd_obstacles",
        description="scene geometry -> crowd Blocked declarations")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("scan", help="scan scene objects for obstacles")
    p.add_argument("--collection", action="append", default=[],
                   help="collection name (repeatable; recursive)")
    p.add_argument("--prefixes", default=None,
                   help="comma-separated object-name prefixes (startswith)")
    p.add_argument("--walkable", action="append", required=True,
                   help="'id:minx,miny:maxx,maxy' (repeatable)")
    p.add_argument("--margin", type=float, default=DEFAULT_MARGIN)
    p.add_argument("--z-band", default=f"{DEFAULT_Z_BAND[0]},{DEFAULT_Z_BAND[1]}",
                   help="world-z band 'lo,hi' (match the floor!)")
    p.add_argument("--min-footprint", type=float,
                   default=DEFAULT_MIN_FOOTPRINT)
    p.add_argument("--emit-anyway", action="store_true",
                   help="animated objects: report-skip instead of REFUSE")
    p.add_argument("--json", action="store_true",
                   help="machine-readable full output")
    p.add_argument("--blend", default=None,
                   help="scene .blend to open BEFORE scanning (s24 VK "
                        "sanctioned delta — without it the scan runs on "
                        "the factory scene and refuses; the raw-blender "
                        "positional form also works but was undocumented)")
    p.add_argument("--json-out", default=None,
                   help="write the scan JSON VERBATIM to this file (s24 VK "
                        "sanctioned delta — stdout is interleaved with "
                        "Blender logs; a file is pipeable)")
    args = ap.parse_args(argv)

    try:
        if getattr(args, "blend", None):
            import bpy
            bpy.ops.wm.open_mainfile(filepath=args.blend)
        walkables = [_parse_walkable(w) for w in args.walkable]
        zlo, zhi = (float(v) for v in args.z_band.split(","))
        prefixes = ([p.strip() for p in args.prefixes.split(",")]
                    if args.prefixes else [])
        out = scan_scene(collections=args.collection, prefixes=prefixes,
                         walkables=walkables, margin=args.margin,
                         z_band=(zlo, zhi),
                         min_footprint=args.min_footprint,
                         emit_anyway=args.emit_anyway)
    except CrowdObstacleRefused as e:
        print(f"[crowd-obst] REFUSED: {e}", file=sys.stderr)
        return 2

    if args.json:
        blob = json.dumps(out, indent=1)
        if getattr(args, "json_out", None):
            with open(args.json_out, "w") as f:
                f.write(blob + "\n")
            print(f"[crowd-obst] json -> {args.json_out}")
        else:
            print(blob)
    else:
        print(f"[crowd-obst] {len(out['blocked'])} Blocked region(s):")
        for b in out["blocked"]:
            (x0, y0), (x1, y1) = b["bounds"]
            print(f"  {b['id']:<28} on {b['walkable_id']:<20} "
                  f"({x0:+.2f},{y0:+.2f})..({x1:+.2f},{y1:+.2f})")
        skips = [r for r in out["report"] if r["decision"] != "blocked"]
        if skips:
            print(f"[crowd-obst] {len(skips)} skipped (see report):")
            for r in skips:
                print(f"  {r['name']:<28} {r['decision']}: {r['reason']}")
        print("[crowd-obst] paste into CrowdScene authoring: "
              "from scripts.crowd import Blocked; "
              "blocked=[Blocked(id=b['id'], walkable_id=b['walkable_id'], "
              "bounds=b['bounds']) for b in out['blocked']]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
