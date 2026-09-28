#!/usr/bin/env python3
"""coplanarity_audit.py -- detect coplanar face pairs (z-fight class).

DESIGN v3.2 §1 gate. The bumper bug: bumperF/R boxes exactly 1.9 wide =
side faces coplanar with hull sides (x ±0.95) over shared extent ->
per-pixel z-fighting shimmer that reads as "flickering everywhere".

Detection: for each visible mesh object, group polygons by plane key
(normal rounded to 5 deg, plane offset rounded to 1 mm); within a
group, pair faces whose 2D AABBs overlap by > MIN_OVERLAP m^2. Also
cross-object: faces on identical plane keys between objects whose
2D AABBs overlap and both faces face the SAME direction (the up/up
ground-contact case).

Cost: street/vehicle meshes are <= a few hundred faces each; plane
grouping + in-group AABB pairing is trivial at this scale.

Self-test included (gate sanity: must fail on a known-bad pair).
"""
import math

import os

import bpy
from mathutils import Vector

MIN_OVERLAP_M2 = 0.0004   # 4 cm^2 of true overlap -> z-fight visible
EPS = 1e-4

# object-name prefixes to skip (sources hidden from render, RB proxies
# that intentionally overlap colliders, etc.)
SKIP_PREFIXES = ("RB.", "FX.", "ZedSources")
SKIP_SUFFIXES = (".Loc",)


def _plane_key(p_co, p_normal):
    # canonical normal: flip to +hemisphere, quantize 5 deg / 1 mm
    n = Vector(p_normal)
    if (n.x, n.y, n.z) < (-n.x, -n.y, -n.z):
        n = -n
    d = n.dot(Vector(p_co))
    return (tuple(round(v, 2) for v in n), round(d, 3))


def _face_aabb_in_plane(obj, poly, mw):
    # project verts to plane-local 2D (u = major axis, v = minor)
    vs = [mw @ obj.data.vertices[i].co for i in poly.vertices]
    n = Vector(poly.normal).normalized()
    # build plane basis
    if abs(n.z) < 0.9:
        u = n.cross(Vector((0, 0, 1))).normalized()
    else:
        u = n.cross(Vector((1, 0, 0))).normalized()
    v = n.cross(u)
    pts = [(p.dot(u), p.dot(v)) for p in vs]
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    return min(xs), max(xs), min(ys), max(ys)


def _aabb_overlap(a, b):
    ow = min(a[1], b[1]) - max(a[0], b[0])
    oh = min(a[3], b[3]) - max(a[2], b[2])
    if ow <= EPS or oh <= EPS:
        return 0.0
    return ow * oh


def _iter_faces(obj, mw):
    me = obj.data
    if not me or not me.polygons:
        return
    for poly in me.polygons:
        if poly.normal.length < EPS or poly.area < MIN_OVERLAP_M2:
            continue
        world_n = (mw.to_3x3() @ poly.normal).normalized()
        key = _plane_key(obj.matrix_world @ poly.center, world_n)
        yield poly, key, world_n


def _shares_vertex(pa, pb):
    """Fan-triangulated caps/faces TILE a plane without overlapping --
    they share vertices. True z-fight faces never share topology."""
    return bool(set(pa.vertices) & set(pb.vertices))


def _same_direction(na, nb, tol=0.05):
    return (na - nb).length < tol


def _hidden_downward(wn_unflipped, d):
    """Down-facing planes within 5 cm of the ground are never visible
    from a camera above (marks' bottoms vs road top, grid bottoms)."""
    return wn_unflipped.z < -0.9 and d < 0.05


def audit(scene, verbose=False):
    issues = []
    for obj in scene.objects:
        if obj.type != 'MESH' or obj.hide_render or obj.get("kit_atmo"):
            continue  # atmo objects are hidden by the viewport preset
        if obj.name.startswith(SKIP_PREFIXES) or obj.name.endswith(SKIP_SUFFIXES):
            continue
        mw = obj.matrix_world
        planes = {}
        for poly, key, wn in _iter_faces(obj, mw):
            planes.setdefault(key, []).append(
                (poly, _face_aabb_in_plane(obj, poly, mw), wn))
        for key, entries in planes.items():
            if len(entries) < 2:
                continue
            if _hidden_downward(entries[0][2], key[1]):
                continue
            for i in range(len(entries)):
                for j in range(i + 1, len(entries)):
                    pa, boxa, na = entries[i]
                    pb, boxb, nb = entries[j]
                    if _shares_vertex(pa, pb):
                        continue      # fan tiling, not a fight
                    if _hidden_downward(na, key[1]) and \
                            _hidden_downward(nb, key[1]):
                        continue      # both hidden under the ground
                    if not _same_direction(na, nb):
                        continue      # contact faces (hidden), not a fight
                    if na.z < -0.7 and nb.z < -0.7:
                        continue      # down/down: contact or interior
                        # (a surface pair both facing DOWN is never
                        # visible from the camera-above regime; the bed/
                        # bench and crash-stack contact planes are this
                        # class)
                    ov = _aabb_overlap(boxa, boxb)
                    if ov > MIN_OVERLAP_M2:
                        issues.append(
                            f"{obj.name}: coplanar faces overlap {ov*1e4:.1f} cm^2 "
                            f"(plane n={key[0]} d={key[1]}) -- z-fight class")
                        if __debug__ and os.environ.get("CPA_DUMP"):
                            va = [tuple(round(c, 3) for c in
                                        (mw @ obj.data.vertices[j].co))
                                  for j in pa.vertices[:4]]
                            vb = [tuple(round(c, 3) for c in
                                        (mw @ obj.data.vertices[j].co))
                                  for j in pb.vertices[:4]]
                            print(f"    [cpa-dump] {obj.name} A={va}")
                            print(f"    [cpa-dump] {obj.name} B={vb}")
    # cross-object: same plane key, same-facing, overlapping
    objs = [o for o in scene.objects
            if o.type == 'MESH' and not o.hide_render
            and not o.name.startswith(SKIP_PREFIXES)
            and not o.name.endswith(SKIP_SUFFIXES)
            and not o.get("kit_atmo")]
    by_plane = {}
    for obj in objs:
        mw = obj.matrix_world
        for poly, key, wn in _iter_faces(obj, mw):
            by_plane.setdefault(key, []).append(
                (obj.name, _face_aabb_in_plane(obj, poly, mw), wn))
    for key, entries in by_plane.items():
        if len(entries) < 2:
            continue
        if _hidden_downward(entries[0][2], key[1]):
            continue
        for i in range(len(entries)):
            for j in range(i + 1, len(entries)):
                n1, b1, wn1 = entries[i]; n2, b2, wn2 = entries[j]
                if n1 == n2:
                    continue  # same-object handled above
                if _hidden_downward(wn1, key[1]) and \
                        _hidden_downward(wn2, key[1]):
                    continue
                # opposite-facing = contact faces (hidden inside each
                # other); same-facing = coincident surfaces -> fight.
                # e.g. lane-mark bottoms (down) vs road top (up): SAFE.
                if not _same_direction(wn1, wn2):
                    continue
                if wn1.z < -0.7 and wn2.z < -0.7:
                    continue      # down/down contact (invisible)
                ov = _aabb_overlap(b1, b2)
                if ov > MIN_OVERLAP_M2:
                    issues.append(
                        f"{n1} vs {n2}: coplanar faces overlap {ov*1e4:.1f} "
                        f"cm^2 (plane n={key[0]} d={key[1]}) -- z-fight class")
    if verbose:
        if issues:
            print(f"[coplanarity_audit] {len(issues)} issue(s):")
            for i in issues[:30]:
                print("  -", i)
        else:
            print("[coplanarity_audit] PASS: no coplanar face pairs")
    return issues


def _selftest():
    import json
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    # KNOWN-BAD: two boxes whose +x faces are COINCIDENT and both face
    # +x (the bumper class: flush same-facing surfaces). Back-to-back
    # contact faces (opposite normals) are SAFE -- hidden inside each
    # other (the original selftest was that class and is NOT a fight).
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0.0, 0, 0.5))
    bpy.context.object.name = "BadA"          # x -0.5..+0.5
    bpy.ops.mesh.primitive_cube_add(size=0.8, location=(0.1, 0, 0.5))
    bpy.context.object.scale = (1.0, 1.2, 1.0)
    bpy.context.object.name = "BadB"          # x -0.3..+0.5 same +x face
    issues = audit(sc)
    ok = any("BadA vs BadB" in i for i in issues)
    print("[coplanarity_audit] SELFTEST:",
          "PASS (known-bad flush pair caught)" if ok
          else "FAIL (flush pair not detected!)")
    return ok


if __name__ == "__main__":
    print('{"selftest": "%s"}' % ("PASS" if _selftest() else "FAIL"))
