"""
validate_scene.py — structural validation checks for Blender scenes.

Catches the class of bugs that VLMs miss: objects intersecting in impossible
ways (e.g. table legs poking through the table top → looks upside down),
objects floating above the ground, objects below the floor, etc.

The coffee-table-upside-down bug (session 4 retro) inspired this: VLMs
catch visible issues but miss geometric ones if the camera angle hides
them. This validator runs deterministic checks on bounding boxes.

Usage:
    blrun.sh --background --python scripts/validate_scene.py -- \\
        --scene scene_interior_room --output /tmp/validation.json

    # Or validate a .blend file
    blrun.sh --background --python scripts/validate_scene.py -- \\
        --load-blend scene.blend --output /tmp/validation.json
"""
import argparse
import json
import os
import sys
from typing import List, Tuple

import bpy
from blender_kit import script_argv, clear_scene


def _object_bounds(obj) -> dict:
    """World-space bounding box for a mesh object."""
    if obj.type != 'MESH' or not obj.bound_box:
        return None
    corners = []
    for corner in obj.bound_box:
        world = obj.matrix_world @ type(obj.location)(corner)
        corners.append((world.x, world.y, world.z))
    return {
        "min": [min(c[i] for c in corners) for i in range(3)],
        "max": [max(c[i] for c in corners) for i in range(3)],
    }


def _bounds_overlap(a: dict, b: dict) -> bool:
    """Check if two 3D bounding boxes overlap (any axis)."""
    for i in range(3):
        if a["max"][i] < b["min"][i] or a["min"][i] > b["max"][i]:
            return False
    return True


def _bounds_overlap_volume(a: dict, b: dict) -> float:
    """Compute the overlap volume between two bounding boxes (m³)."""
    if not _bounds_overlap(a, b):
        return 0.0
    dx = max(0, min(a["max"][0], b["max"][0]) - max(a["min"][0], b["min"][0]))
    dy = max(0, min(a["max"][1], b["max"][1]) - max(a["min"][1], b["min"][1]))
    dz = max(0, min(a["max"][2], b["max"][2]) - max(a["min"][2], b["min"][2]))
    return dx * dy * dz


def _object_volume(b: dict) -> float:
    return ((b["max"][0] - b["min"][0]) *
            (b["max"][1] - b["min"][1]) *
            (b["max"][2] - b["min"][2]))


def _is_ground_like(b: dict) -> bool:
    """Flat, wide slab at/near the floor (the ground itself, roads, pads).
    Same shape rule as look.py's label exclusion (measured there)."""
    height = b["max"][2] - b["min"][2]
    area = (b["max"][0] - b["min"][0]) * (b["max"][1] - b["min"][1])
    return height <= 0.05 and area >= 6.0


# F22 (R8, measured on the R6/R7 loft): labels whose objects compose
# DENSELY by vendor design in authored levels. AABB overlap between two
# such objects is composition/adjacency, not collision — recorded as a
# visible P2-class advisory, never silently dropped (the mm-class truth
# for these pairs is owned by the USE audits: place_on/seat_at/nav).
# Data-derived default: the 21 distinct kit_labels present on the R6
# loft (kitchen_unit 841 ... floor_lamp 1); extendable via param.
LEVEL_FAMILIES = frozenset({
    "kitchen_unit", "partition_panel", "deco", "sofa_module",
    "pendant_light", "railing", "bed", "interior_window",
    "shelf_unit", "plant", "wall", "ceiling", "exterior_window",
    "rug", "chair", "floor", "stairs", "mezzanine", "table",
    "sideboard", "floor_lamp"})


def validate_scene(*, ground_z: float = 0.0,
                   floating_threshold: float = 0.05,
                   overlap_volume_threshold: float = 0.001,
                   level_families=None) -> dict:
    """Run structural validation checks on the current scene.

    Checks:
      1. Floating objects: mesh objects whose bottom is >floating_threshold above ground_z
         (and aren't lights/cameras/ceilings)
      2. Below-floor objects: mesh objects whose top is below ground_z
      3. Suspicious intersections: pairs of mesh objects whose overlap volume
         exceeds overlap_volume_threshold (likely geometry bugs, not intended contact)
         - v2 containment skip: labeled prop inside a labeled shell
         - F22 containment extension: ANY object FULLY inside a room-scale
           shell (bbox-contained, volume ratio >= 50x) — the shell AABB
           swamps it; recorded visibly, reason marks 'unverified'
         - F22 level-adjacency advisory: both sides kit_labeled with
           level-family labels -> advisory (visible count + worst-N),
           not an issue; gross non-shell overlaps still flag
      4. Ceiling check: objects above 5m (likely misplaced)

    Returns a dict with issues list + summary stats.
    """
    issues = []
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    bounds_map = {o.name: _object_bounds(o) for o in meshes}
    bounds_map = {k: v for k, v in bounds_map.items() if v is not None}

    # D16 (audit HIGH #1): gate exclusions are SEMANTIC, not lexical.
    # An object carrying the kit_semantic prop (written by label_objects
    # when the vision label matches the ceiling/sun/light vocabulary) is
    # excluded by PROP — a vision rename can no longer silently strip
    # gate coverage. Legacy NAME match stays as fallback for unlabeled
    # scenes (imports/authors that never ran the label op).
    CEILING_NAMES = {"ceiling", "CeilingLight", "sun", "SunLight"}
    _legacy = {n.lower() for n in CEILING_NAMES}
    excluded = {o.name for o in meshes
                if o.get("kit_semantic") or o.name.lower() in _legacy}

    # Validator v2 (D16 dogfood follow-up): containment is not collision.
    # On imported LEVELS the room/shell object's AABB swamps every prop
    # inside it — the pair flags as a huge intersection (the D16 fixture
    # read as ONE 27m3 blob) that no transform can fix. When BOTH sides
    # ran the label op (kit_label present — prop-based, never name-based)
    # and the shell-side label carries the shell vocabulary while the
    # other side's centroid sits inside the shell's bbox, the pair is a
    # CONTAINMENT relation, not a defect — skip with a visible record.
    _SHELL_TOKENS = ("room", "shell", "wall", "floor", "enclosure",
                     "interior", "building")
    _labels = {o.name: (o.get("kit_label") or "") for o in meshes}
    _both_labeled = {n for n, lb in _labels.items() if lb}
    _shell = {n for n in _both_labeled
              if any(t in _labels[n].lower() for t in _SHELL_TOKENS)}
    skipped_contained = []
    if level_families is None:
        level_families = LEVEL_FAMILIES
    adjacency = []

    # ---- Check 1: floating objects ---------------------------------
    # Skip ceilings (excluded set above: kit_semantic prop or legacy name)
    for name, b in bounds_map.items():
        if name in excluded:
            continue
        bottom_z = b["min"][2]
        if bottom_z > ground_z + floating_threshold:
            # Check if this object is supported by another object below it
            supported = False
            for other_name, other_b in bounds_map.items():
                if other_name == name:
                    continue
                # Is the other object's top at or just below this object's bottom?
                if (abs(other_b["max"][2] - bottom_z) < floating_threshold and
                    _bounds_overlap({**b, "min": [b["min"][0], b["min"][1], -9999]},
                                   {**other_b, "max": [other_b["max"][0], other_b["max"][1], 9999]})):
                    supported = True
                    break
            if not supported:
                # wave-1 friction #7: "above ground" alone misdirects the
                # fix when the object floats above a TABLE — name the
                # nearest support below (x/y-overlapping, top under bottom)
                hint = ""
                best_gap, best_name = None, None
                for other_name, other_b in bounds_map.items():
                    if other_name == name:
                        continue
                    if other_b["max"][2] <= bottom_z and _bounds_overlap(
                            {**b, "min": [b["min"][0], b["min"][1], -9999]},
                            {**other_b, "max": [other_b["max"][0], other_b["max"][1], 9999]}):
                        gap = bottom_z - other_b["max"][2]
                        if best_gap is None or gap < best_gap:
                            best_gap, best_name = gap, other_name
                if best_name is not None:
                    hint = (f"; nearest support below: '{best_name}' "
                            f"(+{best_gap:.3f}m gap)")
                issues.append({
                    "type": "floating",
                    "severity": "P1",
                    "object": name,
                    "bottom_z": round(bottom_z, 3),
                    "ground_z": ground_z,
                    "gap_m": round(bottom_z - ground_z, 3),
                    "nearest_support": best_name,
                    "support_gap_m": round(best_gap, 3) if best_gap is not None else None,
                    "description": f"Object '{name}' is floating {bottom_z - ground_z:.3f}m above ground (no support below){hint}"
                })

    # ---- Check 2: below-floor objects ------------------------------
    for name, b in bounds_map.items():
        if name in excluded:
            continue
        top_z = b["max"][2]
        if top_z < ground_z - 0.001:
            issues.append({
                "type": "below_floor",
                "severity": "P0",
                "object": name,
                "top_z": round(top_z, 3),
                "ground_z": ground_z,
                "description": f"Object '{name}' is entirely below the floor (top at z={top_z:.3f})"
            })

    # ---- Check 2b: floor-penetration (M5, transient-scan driven) ----
    # below_floor only catches FULLY-sunk objects; a HALF-SUNK box (top
    # above floor) was invisible to every check (T6 planted glitch,
    # measured). Flag deep penetration into the ground: depth > max(5cm,
    # 20% of height) so intentional shallow embeds (posts, rugs) stay
    # silent but sunk-through-floor bugs surface as P1.
    for name, b in bounds_map.items():
        if name in excluded:
            continue
        if _is_ground_like(b):
            continue
        min_z = b["min"][2]
        height = b["max"][2] - min_z
        depth = ground_z - min_z
        if min_z < ground_z - 0.001 and depth > max(0.05, 0.2 * height):
            issues.append({
                "type": "floor_penetration",
                "severity": "P1",
                "object": name,
                "penetration_m": round(depth, 3),
                "ground_z": ground_z,
                "description": (f"Object '{name}' penetrates the floor by "
                                f"{depth:.3f}m ({depth / max(height, 1e-6) * 100:.0f}% of its height)")
            })

    # ---- Check 3: suspicious intersections -------------------------
    # Heuristic: if two objects overlap by >threshold volume, flag it.
    # Exception: objects in a known "supporting" relationship (e.g. table top
    # + legs meeting at an edge) overlap by a tiny volume which is fine.
    names = list(bounds_map.keys())
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = bounds_map[names[i]], bounds_map[names[j]]
            if not _bounds_overlap(a, b):
                continue
            overlap_v = _bounds_overlap_volume(a, b)
            if overlap_v <= 0:
                continue
            # Compute overlap as % of the smaller object's volume.
            # F12 (usability R1): the ABSOLUTE threshold alone gates out
            # scale-honest findings — a 10cm mug sunk 2cm into a tabletop
            # (20% of the mug!) passed silently under 0.001m³. Flag when
            # EITHER the relative pct is significant OR the absolute
            # volume is large (huge-object pairs).
            smaller_v = min(_object_volume(a), _object_volume(b))
            pct = (overlap_v / smaller_v * 100) if smaller_v > 0 else 0
            if pct < 5 and overlap_v < overlap_volume_threshold:
                continue
            # v2 containment skip (see note above): both labeled, one
            # shell-like, the other's centroid inside the shell bbox.
            # F22 extension: an UNLABELED object FULLY contained in a
            # room-scale shell (volume ratio >= 50x) is the same
            # swamping artifact — the shell AABB spans the room, so any
            # interior object 'overlaps' it. Recorded visibly with an
            # honest 'unverified' reason; still VISIBLE, not silent.
            _skipped = False
            for si, sj in ((names[i], names[j]), (names[j], names[i])):
                if si not in _shell or sj in _shell:
                    continue
                c = bounds_map[sj]
                sb = bounds_map[si]
                centroid_in = all(sb["min"][k] <=
                                  (c["min"][k] + c["max"][k]) / 2 <=
                                  sb["max"][k] for k in range(3))
                fully_in = all(sb["min"][k] <= c["min"][k] and
                               c["max"][k] <= sb["max"][k]
                               for k in range(3))
                ratio = (_object_volume(sb) /
                         _object_volume(c)) if _object_volume(c) > 0 else 0
                if sj in _both_labeled and centroid_in:
                    skipped_contained.append(
                        {"pair": [si, sj],
                         "overlap_pct_of_smaller": round(pct, 1),
                         "reason": f"'{sj}' is labeled and contained "
                                   f"in shell '{si}' — containment, "
                                   f"not collision"})
                    _skipped = True
                    break
                if fully_in and ratio >= 50.0:
                    _lab = "unlabeled" if sj not in _both_labeled \
                        else f"labeled '{_labels.get(sj, '')}'"
                    skipped_contained.append(
                        {"pair": [si, sj],
                         "overlap_pct_of_smaller": round(pct, 1),
                         "reason": f"'{sj}' is fully contained in "
                                   f"room-scale shell '{si}' "
                                   f"(x{ratio:.0f} volume) — containment, "
                                   f"not collision (unverified: {_lab} "
                                   f"object, run a look to confirm)"})
                    _skipped = True
                    break
            if _skipped:
                continue
            # F22 level-adjacency advisory: both sides carry level-family
            # labels — AABB overlap is vendor composition (measured corpus:
            # 2259/2499 flagged pairs on the R6 loft; median pct 100%,
            # max depth 1.79 m, ALL legitimate — walls contain stairs,
            # sofas abut walls, bed parts interpenetrate). Visible
            # advisory; the gate still bites on gross non-shell overlaps.
            l1 = _labels.get(names[i], "")
            l2 = _labels.get(names[j], "")
            if l1 in level_families and l2 in level_families:
                depth = min(min(a["max"][k], b["max"][k]) -
                            max(a["min"][k], b["min"][k]) for k in range(3))
                gross = (depth >= 0.5 and pct >= 95.0
                         and names[i] not in _shell
                         and names[j] not in _shell)
                if gross:
                    issues.append({
                        "type": "intersection",
                        "severity": "P1",
                        "objects": [names[i], names[j]],
                        "overlap_volume_m3": round(overlap_v, 5),
                        "overlap_pct_of_smaller": round(pct, 1),
                        "description": f"GROSS level-pair overlap exceeds "
                                       f"the F22 adjacency rule: "
                                       f"'{names[i]}' and '{names[j]}' "
                                       f"overlap {pct:.1f}% of smaller, "
                                       f"depth {depth:.2f}m — review"})
                else:
                    adjacency.append({
                        "type": "level_adjacency",
                        "pair": [names[i], names[j]],
                        "labels": [l1, l2],
                        "overlap_pct_of_smaller": round(pct, 1),
                        "min_axis_depth_m": round(depth, 3)})
                continue
            issues.append({
                "type": "intersection",
                "severity": "P1" if pct < 30 else "P0",
                "objects": [names[i], names[j]],
                "overlap_volume_m3": round(overlap_v, 5),
                "overlap_pct_of_smaller": round(pct, 1),
                "description": f"Objects '{names[i]}' and '{names[j]}' overlap by "
                               f"{overlap_v:.4f}m³ ({pct:.1f}% of smaller object)"
            })

    # ---- Check 4: ceiling check ------------------------------------
    for name, b in bounds_map.items():
        if name in excluded:
            continue
        if b["max"][2] > 5.0:
            issues.append({
                "type": "above_ceiling",
                "severity": "P2",
                "object": name,
                "top_z": round(b["max"][2], 3),
                "description": f"Object '{name}' extends above 5m (top at z={b['max'][2]:.3f})"
            })

    # ---- Summary ---------------------------------------------------
    summary = {
        "total_objects": len(bpy.context.scene.objects),
        "mesh_objects_checked": len(bounds_map),
        "ground_z": ground_z,
        "issues_count": len(issues),
        "issues_by_severity": {
            "P0": sum(1 for i in issues if i["severity"] == "P0"),
            "P1": sum(1 for i in issues if i["severity"] == "P1"),
            "P2": sum(1 for i in issues if i["severity"] == "P2"),
        },
        "issues_by_type": {},
        "issues": issues,
        "contained_pairs_skipped": skipped_contained,
        "adjacency_pairs_advisory": len(adjacency),
        "adjacency_worst": sorted(
            adjacency,
            key=lambda r: -r["min_axis_depth_m"])[:5],
    }
    for issue in issues:
        summary["issues_by_type"].setdefault(issue["type"], 0)
        summary["issues_by_type"][issue["type"]] += 1
    return summary


def main():
    p = argparse.ArgumentParser(
        description="Structural validation checks for Blender scenes.")
    p.add_argument("--scene", default=None,
                   help="Scene module name to build before validating")
    p.add_argument("--load-blend", default=None,
                   help="Load a .blend file before validating")
    p.add_argument("--output", required=True,
                   help="Output JSON path for validation report")
    p.add_argument("--frames", type=int, default=24,
                   help="Animation frames to pass to scene's animate()")
    p.add_argument("--ground-z", type=float, default=0.0,
                   help="Z coordinate of the ground plane (default: 0.0)")
    p.add_argument("--floating-threshold", type=float, default=0.05,
                   help="Objects floating >this above ground with no support are flagged (m)")
    p.add_argument("--overlap-volume-threshold", type=float, default=0.001,
                   help="Overlap volume >this triggers intersection check (m³)")
    p.add_argument("--fail-on-issues", action="store_true",
                   help="Exit with non-zero code if any P0/P1 issues found")
    args = p.parse_args(script_argv())

    # Load or build scene
    if args.load_blend:
        print(f"[validate] loading .blend: {args.load_blend}")
        bpy.ops.wm.open_mainfile(filepath=args.load_blend)
    elif args.scene:
        import importlib
        from blender_kit import safe_import_scene
        print(f"[validate] building scene: {args.scene}")
        mod = safe_import_scene(args.scene)
        clear_scene()
        ctx = mod.build_scene()
        if hasattr(mod, "animate"):
            mod.animate(ctx, start_frame=1, n_frames=args.frames)
    else:
        print("[validate] using currently-loaded scene")

    print(f"[validate] running checks (ground_z={args.ground_z})")
    report = validate_scene(
        ground_z=args.ground_z,
        floating_threshold=args.floating_threshold,
        overlap_volume_threshold=args.overlap_volume_threshold,
    )

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(report, f, indent=2)

    # Print summary
    print(f"[validate] {report['issues_count']} issue(s) found:")
    if report['mesh_objects_checked'] == 0:
        print(f"          WARNING: no mesh objects to validate (scene may be empty or lights-only)")
    print(f"          P0={report['issues_by_severity']['P0']}, "
          f"P1={report['issues_by_severity']['P1']}, "
          f"P2={report['issues_by_severity']['P2']}")
    for issue in report["issues"][:10]:
        obj = issue.get("object", " & ".join(issue.get("objects", [])))
        print(f"          [{issue['severity']}] {issue['type']:15s} {obj}: {issue['description']}")
    if len(report["issues"]) > 10:
        print(f"          ... and {len(report['issues']) - 10} more (see {args.output})")
    print(f"[validate] report: {args.output}")

    if args.fail_on_issues and (report["issues_by_severity"]["P0"] > 0 or
                                 report["issues_by_severity"]["P1"] > 0):
        sys.exit(1)


if __name__ == "__main__":
    main()
