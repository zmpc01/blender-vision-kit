"""
placement_lib — overlap-free placement + contact audit for headless Blender.

Lives in blender-agent-kit/scripts/ (imported by apply_patch.py placement
ops and audit_contacts.py). It also lives in the placement-lab R&D repo
(/home/z/placement-lab/lib) where it was developed — keep the two in sync
by re-porting from the lab after any change.

Origin: placement-lab R&D (Sept 2026), validated empirically in
experiments/r2_api_probe.py on Blender 4.5.13; regression-gated by the
T1-T4 + X1 suites (kit: tests/, lab: experiments/).

Layers:
  1. measurement : world_bvh / pair_contact / audit_scene   (mm-exact)
  2. placement   : place_on / seat_at / snap_z              (one-shot solve)
  3. visuals     : heat_bake / seam_views / ascii maps      (vision agents)
  4. (patch ops live in the kit's apply_patch.py, calling this module)

Contact state machine (R2-verified):
  overlap_pairs>0 & inside>0   -> PENETRATING  (penetration_mm, vert-sampled)
  overlap_pairs>0 & inside==0  -> CROSSING?    (segment-triangle test; else
                                  TOUCHING — coplanar contact)
  overlap_pairs==0 & inside>0  -> NESTED       (contained; pen measurable)
  else                         -> CLEAR        (clearance_mm)
Touch band: |gap| <= contact_band_mm counts as TOUCHING (float-noise guard;
prevents "fixing" a perfect placement).

Units: geometry in meters; report fields suffixed _mm are millimeters.
"""
import math
import time

import bpy
import bmesh
from mathutils import Vector, Matrix, Quaternion
from mathutils.bvhtree import BVHTree
from mathutils.geometry import intersect_ray_tri

# 5.x compat: action.fcurves moved to channelbag API. Local fallback so this
# module still imports when scripts/ isn't on PYTHONPATH (audit_contacts.py
# pattern). See blender_kit/__init__.py:iter_fcurves for the source of truth.
# F2B-9: READ-ONLY consumers (guards, finders, keyframe rebases) must use
# iter_all_fcurves — iter_fcurves probes slot[0] only (blind to 5.x
# multi-slot actions) and AUTO-SCAFFOLDS a fresh action's slot/layer/strip/
# channelbag as a read side effect. Create paths that need .new()/.find()
# keep iter_fcurves (none exist in this module).
try:
    from blender_kit import iter_fcurves, iter_all_fcurves
except ImportError:
    def iter_fcurves(action):
        return action.fcurves

    def iter_all_fcurves(action):
        # read-only fallback: 4.x flat fcurves (the full 5.x slot chain
        # lives in blender_kit; this stub keeps direct imports importable)
        return action.fcurves

# ---------------------------------------------------------------------------
# BVH cache (hardened key per design review #7)
# ---------------------------------------------------------------------------

_BVH_CACHE = {}

# Tangency ambiguity band for the sign test in classify_point (u7 lesson,
# session 11): |dotp| below this = numerically tangential -> ray parity.
# Float32 normalization noise reaches ~1e-5; 1e-3 covers it with margin
# while a physically-inside point (|dotp| ~ 1) is untouched.
EPS_TANGENT = 1e-3


def clear_bvh_cache():
    """Drop all cached BVH trees AND the world-polygon cache (F2B-30:
    _POLY_CACHE is keyed by the same _cache_key and survives
    open_mainfile in-process — an edit that preserves vert/face counts,
    frame and matrix would serve stale world polys to the CROSSING test).
    Called automatically after open_mainfile by the patch ops; call
    manually after bulk geometry edits."""
    _BVH_CACHE.clear()
    _POLY_CACHE.clear()


def _cache_key(obj):
    mw = obj.matrix_world
    try:
        mw_hash = hash(tuple(tuple(r) for r in mw))
    except Exception:
        mw_hash = id(mw)
    return (obj.name_full,
            obj.data.name_full if obj.data else None,
            len(obj.data.vertices) if obj.type == 'MESH' else 0,
            len(obj.data.polygons) if obj.type == 'MESH' else 0,
            bpy.context.scene.frame_current,
            bpy.data.filepath,
            mw_hash)


def world_bvh(obj, depsgraph=None):
    """World-space BVH tree for a mesh object (evaluated mesh, world transform
    baked via bmesh). Cached; key includes transform hash + frame + file so
    stale trees cannot survive mutation, frame changes, or file reloads."""
    # FRESHEN FIRST (session-16 subject v3, phantom 38.64mm pen):
    # matrix_world is a lazily-updated RNA cache — hashing the key BEFORE
    # the depsgraph update could hash the PRE-commit matrix, serving a
    # stale tree after a physics commit moved/rotated the object.
    dg = depsgraph or bpy.context.evaluated_depsgraph_get()
    key = _cache_key(obj)
    hit = _BVH_CACHE.get(key)
    if hit is not None:
        return hit
    ev = obj.evaluated_get(dg)
    bm = bmesh.new()
    bm.from_mesh(ev.to_mesh())
    bm.transform(obj.matrix_world)
    bm.normal_update()  # CRITICAL: transform() leaves normals stale (local
    # frame) — every rotated object then returns garbage find_nearest
    # normals -> false inside classifications (T3 lesson)
    tree = BVHTree.FromBMesh(bm)
    ev.to_mesh_clear()
    _BVH_CACHE[key] = tree
    return tree


def open_mesh(obj, tree=None):
    """True if the evaluated mesh has boundary (open) edges -> sign test
    unreliable -> parity-first inside testing."""
    if obj.type != 'MESH':
        return False
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    bm = bmesh.new()
    bm.from_mesh(ev.to_mesh())
    ev.to_mesh_clear()
    bm.transform(obj.matrix_world)
    open_edges = sum(1 for e in bm.edges if len(e.link_faces) != 2)
    bm.free()
    return open_edges > 0


def world_normal(obj, v_normal):
    """World-space normal under arbitrary object scale (inverse-transpose)."""
    n = (obj.matrix_world.inverted().transposed().to_3x3() @ v_normal)
    if n.length > 0:
        n.normalize()
    return n


# ---------------------------------------------------------------------------
# Inside/outside classification (R2-verified, review #3/#16)
# ---------------------------------------------------------------------------

def classify_point(tree, p, band_m=1e-4, parity_primary=False):
    """Classify point p against a closed-ish mesh tree.
    Returns (state, dist_m): state in {'inside','outside','touch'}.
    band_m: distances <= band count as 'touch' (float-noise guard).
    Primary: strict sign of dot(nearest-p, normal); |dot| < EPS_TANGENT
    (edge ties) or parity_primary -> ray parity.

    EPS_TANGENT (usability round-2/u7 fixture): 1e-6 was too tight. A far
    point whose nearest surface element sits on a mesh EDGE can get the
    adjacent face's normal from find_nearest — that normal can be ~90deg
    to the p->nearest direction (u7: shelf corner 0.83m from a mug, ring
    edge returned the bottom-cap normal (-z) for a horizontal approach).
    True dotp is then 0, but float32 normalization noise (~1e-6..1e-5)
    tipped the sign POSITIVE -> 'inside' with the full 0.83m distance ->
    fake 'PENETRATING 833 mm'. A physically-inside point has |dotp| ~ 1;
    anything within 1e-3 of tangency is genuinely ambiguous -> parity.

    Session-16 (subject v2, cone bowl 1088mm fake): the EPS band is not
    enough — a convex rim/adjacent-face normal can carry |dotp| well
    above tangency and still misread. INSIDE claims are therefore ALWAYS
    parity-verified (parity is ground truth for closed meshes); OUTSIDE
    claims keep the fast path. Parity cost: ~2-4 rays per claimed-inside
    point, only paid on the rare inside branch."""
    loc, normal, idx, dist = tree.find_nearest(p)
    if loc is None:
        return 'outside', None
    if dist <= band_m:
        return 'touch', dist
    if not parity_primary:
        dotp = (loc - p).normalized().dot(normal)
        if dotp < -EPS_TANGENT:
            return 'outside', dist
    # ambiguous, parity-primary, or sign-claimed-inside: verify by parity
    origin = Vector(p)
    hits = 0
    for _ in range(64):
        hloc, hnorm, hidx, hdist = tree.ray_cast(origin, Vector((0, 0, 1)),
                                                 1e4)
        if hloc is None:
            break
        hits += 1
        origin = hloc + Vector((0, 0, 1e-4))
    return (('inside', dist) if hits % 2 == 1 else ('outside', dist))


# ---------------------------------------------------------------------------
# Layer 1 — measurement
# ---------------------------------------------------------------------------

def surface_samples(obj, mode='verts', spacing=0.01, cap=20000):
    """World-space surface sample points.
    mode: 'verts' | 'verts+edges' (subdivides edges to ~spacing) | 'bottom'
    (verts whose world normal points down, normal_z < -0.3)."""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    me = ev.to_mesh()
    pts = []
    if mode == 'bottom':
        for v in me.vertices:
            if world_normal(obj, v.normal).z < -0.3:
                pts.append(obj.matrix_world @ v.co)
        if not pts:
            # fallback: bottom 5% z-band of world bbox (review #5)
            ws = [obj.matrix_world @ v.co for v in me.vertices]
            if ws:
                zs = [p.z for p in ws]
                zmin = min(zs)
                band = (max(zs) - zmin) * 0.05 + 1e-6
                pts = [p for p in ws if p.z <= zmin + band]
    elif mode == 'verts+edges':
        for v in me.vertices:
            pts.append(obj.matrix_world @ v.co)
        mw = obj.matrix_world
        for e in me.edges:
            a = mw @ me.vertices[e.vertices[0]].co
            b = mw @ me.vertices[e.vertices[1]].co
            n = max(1, int((b - a).length / spacing))
            for i in range(1, n):
                pts.append(a.lerp(b, i / n))
    else:
        for v in me.vertices:
            pts.append(obj.matrix_world @ v.co)
    ev.to_mesh_clear()
    if len(pts) > cap:
        stride = math.ceil(len(pts) / cap)
        pts = pts[::stride]
    return pts


_POLY_CACHE = {}


def _polys_world(obj):
    """[(Vector, Vector, Vector, ...), ...] world-space polygon loops."""
    key = _cache_key(obj)
    hit = _POLY_CACHE.get(key)
    if hit is not None:
        return hit
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    me = ev.to_mesh()
    mw = obj.matrix_world
    polys = [tuple(mw @ me.vertices[i].co for i in p.vertices)
             for p in me.polygons]
    ev.to_mesh_clear()
    _POLY_CACHE[key] = polys
    return polys


def _tri_fan(poly):
    for i in range(1, len(poly) - 1):
        yield (poly[0], poly[i], poly[i + 1])


def _seg_crosses_tri(a, b, tri, eps_cross=5e-6, return_depth=False):
    """Proper segment-triangle crossing: endpoints STRICTLY on opposite
    sides of the tri's plane (beyond float32 jitter — world transforms
    quantize at ~60nm, T3 lesson: a resting rim at -1e-7 read as crossing)
    AND hit point inside the tri. Coplanar / grazing segments are contacts,
    not crossings.
    return_depth=True -> (bool, depth_m) where depth = how far the deeper
    endpoint sits below the tri plane (the micro-tilt discriminator: a
    touching slab dips <= contact_band; a real spear crosses by the slab
    thickness — session-12 usability round A)."""
    t0, t1, t2 = tri
    e1, e2 = t1 - t0, t2 - t0
    n = e1.cross(e2)
    ln = n.length
    if ln < 1e-15:
        return (False, 0.0, False) if return_depth else False
    n = n / ln
    da = (a - t0).dot(n)
    db = (b - t0).dot(n)
    if abs(da) < eps_cross or abs(db) < eps_cross:
        return (False, 0.0, False) if return_depth else False  # grazing
    if (da > 0) == (db > 0):
        return (False, 0.0, False) if return_depth else False  # same side
    t = da / (da - db)
    p = a + (b - a) * t
    # barycentric inside test (shared-edge counts as inside: >= -eps)
    d00, d01, d11 = e1.dot(e1), e1.dot(e2), e2.dot(e2)
    dp0, dp1 = (p - t0).dot(e1), (p - t0).dot(e2)
    den = d00 * d11 - d01 * d01
    if abs(den) < 1e-20:
        return (False, 0.0, False) if return_depth else False
    u = (d11 * dp0 - d01 * dp1) / den
    v = (d00 * dp1 - d01 * dp0) / den
    # STRICT inside: a hit exactly on the tri's EDGE is tangency, not a
    # piercing. X1 lesson (L_contact): the resting probe's bottom edge
    # crossed the pedestal side-face plane exactly AT the shared contact
    # height (u+v == 1.0) -> boundary-inclusive test read pure edge contact
    # as "crossing" -> false PENETRATING. A genuine piercing of a closed
    # mesh also registers on the neighbour tri with an interior hit, so
    # requiring the margin loses nothing but degenerate grazes.
    eps = 1e-7
    inside = (u >= eps) and (v >= eps) and (u + v <= 1 - eps)
    if not return_depth:
        return inside
    # entering = the segment direction goes AGAINST the outward normal
    # at the crossing (da>0 -> a is outside, b inside => a->b enters).
    # Round-D discriminator: a real spear ENTERS the solid; a resting
    # overhang (L-corner, u-tilt) only EXITS past a side-face plane.
    entering = da > 0.0
    depth = max(-min(da, db), 0.0) if inside else 0.0
    return inside, depth, entering


def _segment_hits_poly(a, b, polys, face_idx, return_depth=False):
    poly = polys[face_idx]
    seg = b - a
    if seg.length < 1e-12:
        return (False, 0.0, False) if return_depth else False
    best = 0.0
    enters = False
    for tri in _tri_fan(poly):
        if return_depth:
            hit, depth, entering = _seg_crosses_tri(a, b, tri,
                                                    return_depth=True)
            if hit:
                best = max(best, depth)
                enters = enters or entering
        elif _seg_crosses_tri(a, b, tri):
            return True
    if return_depth:
        return (best > 0.0, best, enters)
    return False


def _armature_pose_offset(arm_obj, tol=1e-4):
    """C6 decisive probe for armatures with ZERO animation data: compare
    each pose bone's evaluated matrix against its rest matrix (pb.matrix
    vs pb.bone.matrix_local — both are ARMATURE-space, so no world
    matrix is involved). Any translation OR rotation mismatch beyond
    `tol` means the rig is manually/driver-posed => 'animated' for
    guard purposes. Early-exits on the first mismatch (performance);
    one view_layer.update() first because pb.matrix is a
    DEPSGRAPH-evaluated read (a just-posed rig reads stale otherwise)."""
    if arm_obj.type != 'ARMATURE' or not arm_obj.pose.bones:
        return False
    bpy.context.view_layer.update()
    for pb in arm_obj.pose.bones:
        rest = pb.bone.matrix_local
        pose = pb.matrix
        if (pose.to_translation() -
                rest.to_translation()).length > tol:
            return True
        # rotation too: a bone rotated about its own HEAD keeps its
        # translation — translation-only probes miss the most common
        # manual pose (twist/bend in place)
        qd = pose.to_quaternion().rotation_difference(
            rest.to_quaternion())
        if abs(qd.angle) > tol:
            return True
    return False


def _skinned_guard(obj, force):
    """Refuse confident nonsense on posed/animated rigged meshes (kit
    gotcha #27: evaluated mesh can return bind pose while the render shows
    the posed figure). Armature WITHOUT animation = rest pose = safe.
    C6: 'animated' now also covers DRIVER-posed armatures (animation
    drivers, zero action/NLA) and MANUALLY-posed ones (pose_bone.matrix
    != bone.matrix_local with zero animation data) via a cheap decisive
    pose-matrix probe."""
    if obj.type != 'MESH':
        return None
    has_arm = any(m.type == 'ARMATURE' for m in obj.modifiers) or \
        (obj.parent is not None and obj.parent.type == 'ARMATURE') or \
        obj.find_armature() is not None
    if not has_arm:
        return None
    ad = getattr(obj, "animation_data", None)
    animated = bool(ad and (ad.action or
                            any(tr.strips for tr in ad.nla_tracks) or
                            ad.drivers))
    if not animated:
        # s17 (found by the test fixture): the POSE lives on the ARMATURE —
        # a skinned mesh whose armature object is animated (parent, modifier
        # target, or find_armature) is posed even when the mesh object
        # itself has no animation data. The old check read the bind pose
        # and labeled it "rest-pose" — exactly gotcha #27.
        cands = [m.object for m in obj.modifiers
                 if m.type == 'ARMATURE' and m.object]
        if obj.parent is not None and obj.parent.type == 'ARMATURE':
            cands.append(obj.parent)
        fa = obj.find_armature()
        if fa is not None:
            cands.append(fa)
        for cand in cands:
            cad = getattr(cand, "animation_data", None)
            if cad and (cad.action or
                        any(tr.strips for tr in cad.nla_tracks) or
                        cad.drivers):
                animated = True
                break
        if not animated:
            # C6: driver-posed and MANUALLY-posed armatures carry ZERO
            # animation data — the action/NLA/driver test above read them
            # as rest-pose while the evaluated mesh is posed (gotcha #27's
            # quiet twin). The pose-matrix probe is decisive.
            for cand in cands:
                if _armature_pose_offset(cand):
                    animated = True
                    break
    if animated and not force:
        raise RuntimeError(
            f"'{obj.name}' is an ANIMATED skinned mesh — evaluated mesh "
            f"geometry can lie (bind pose vs posed render, AGENTS.md #27). "
            f"Place the rest-pose figure (remove/stash actions), use a "
            f"capsule proxy (AGENTS.md #32 policy), or pass force=True to "
            f"accept an unreliable audit (result labeled "
            f"inside_test='unreliable-skinned').")
    return "unreliable-skinned" if (animated and force) else "rest-pose"


def pair_contact(a, b, *, sample='verts', cap=20000, contact_band_mm=0.1,
                 max_cross_pairs=512, force=False):
    """Full contact report for a pair of mesh objects. JSON-safe dict."""
    t0 = time.time()
    band = contact_band_mm / 1000.0
    rep = {"a": a.name, "b": b.name, "sample": sample,
           "contact_band_mm": contact_band_mm}
    sk = _skinned_guard(a, force) or _skinned_guard(b, force)
    if sk:
        rep["skinned_warning"] = sk

    # quick AABB reject
    aabb_a = _aabb(a)
    aabb_b = _aabb(b)
    rep["aabb_overlap"] = _aabb_overlap(aabb_a, aabb_b)
    if not rep["aabb_overlap"]:
        # still measure clearance (bbox apart can still be close)
        pts_a = surface_samples(a, mode=sample, cap=cap)
        pts_b = surface_samples(b, mode=sample, cap=cap)
        tree_b = world_bvh(b)
        tree_a = world_bvh(a)
        ca = _min_clear(pts_a, tree_b, band)
        cb = _min_clear(pts_b, tree_a, band)
        cl = None
        for c in (ca, cb):
            if c is not None:
                cl = c if cl is None else min(cl, c)
        # Touch-band semantic (module docstring) must hold here too: exact
        # contact lands ~60nm above the surface (float32 world transforms),
        # BVH overlap finds no face pairs, and without this a resting
        # object reported "CLEAR 90.0 mm gap" (T4 lesson).
        touching = cl is not None and cl <= band
        rep.update(state="TOUCHING" if touching else "CLEAR",
                   overlap_face_pairs=0,
                   penetration_mm=0.0 if touching else None,
                   clearance_mm=0.0 if touching else
                   (round(cl * 1000, 2) if cl is not None else None),
                   verdict=("TOUCHING (surface contact, within "
                            f"{contact_band_mm} mm band)") if touching else
                   (f"CLEAR {cl * 1000:.1f} mm gap" if cl else "CLEAR"),
                   severity="ok", inside_test="sign",
                   timings_ms=round((time.time() - t0) * 1000, 1))
        return rep

    tree_a = world_bvh(a)
    tree_b = world_bvh(b)
    pairs = tree_a.overlap(tree_b)
    rep["overlap_face_pairs"] = len(pairs)

    pts_a = surface_samples(a, mode=sample, cap=cap)
    pts_b = surface_samples(b, mode=sample, cap=cap)
    parity_a = open_mesh(a)
    parity_b = open_mesh(b)

    n_inside = 0
    pen_max = 0.0
    pen_pts = []
    cl = None
    for pts, tree_own, tree_other, par in (
            (pts_a, tree_a, tree_b, parity_a),
            (pts_b, tree_b, tree_a, parity_b)):
        for p in pts:
            state, dist = classify_point(tree_other, p, band,
                                         parity_primary=par)
            if state == 'touch':
                # on-surface vert: contact candidate within the touch band
                # (must feed the state decision below — a resting object's
                # verts sit ~60nm above the support due to float32, and
                # BVH overlap finds no face pairs, T4 lesson)
                if dist is not None:
                    cl = 0.0 if cl is None else min(cl, 0.0)
                continue  # on-surface: neither penetration nor clearance
            if state == 'inside':
                n_inside += 1
                if dist is not None and dist > pen_max:
                    pen_max = dist
                    pen_pts = [(p.x, p.y, p.z, dist)]
                elif dist is not None and dist == pen_max and len(pen_pts) < 3:
                    pen_pts.append((p.x, p.y, p.z, dist))
            else:
                if dist is not None:
                    cl = dist if cl is None else min(cl, dist)

    inside_test = "parity" if (parity_a or parity_b) else "sign"

    if pairs and n_inside > 0:
        rep.update(state="PENETRATING",
                   penetration_mm=round(pen_max * 1000, 2),
                   penetration_points_m=[
                       [round(x, 4), round(y, 4), round(z, 4),
                        round(d * 1000, 2)] for x, y, z, d in pen_pts],
                   clearance_mm=None, severity="fail",
                   inside_test=inside_test)
        rep["verdict"] = f"PENETRATING {pen_max * 1000:.1f} mm — fix"
    elif pairs and n_inside == 0:
        # spear-through / interlocked check (review blocker #2), with
        # CROSSING DEPTH discrimination (session-12 usability round A):
        # a slab resting with a ~0.03mm micro-tilt dips one corner and
        # registers face-pair crossings with zero contained verts — the
        # same signature as a real spear. A real spear crosses by the
        # slab/wall thickness; a touch dips <= contact_band. Only a
        # crossing deeper than the band is a penetration.
        crossing = False
        crossing_depth = 0.0
        crossing_enters = False
        if len(pairs) <= max_cross_pairs:
            polys_a = _polys_world(a)
            polys_b = _polys_world(b)
            for ia, ib in pairs[:max_cross_pairs]:
                pa, pb = polys_a[ia], polys_b[ib]
                best = 0.0
                enters = False
                for i in range(len(pa)):
                    seg_a = pa[i]
                    seg_b = pa[(i + 1) % len(pa)]
                    hit, depth, entering = _segment_hits_poly(
                        seg_a, seg_b, polys_b, ib, return_depth=True)
                    if hit:
                        best = max(best, depth)
                        enters = enters or entering
                if best == 0.0 or not enters:
                    for i in range(len(pb)):
                        seg_a = pb[i]
                        seg_b = pb[(i + 1) % len(pb)]
                        hit, depth, entering = _segment_hits_poly(
                            seg_a, seg_b, polys_a, ia,
                            return_depth=True)
                        if hit:
                            best = max(best, depth)
                            enters = enters or entering
                if best > 0.0:
                    crossing = True
                    crossing_depth = max(crossing_depth, best)
                    crossing_enters = crossing_enters or enters
        if crossing and crossing_enters and crossing_depth > band:
            # crossing depth = face-piercing EDGE extent (no contained
            # verts to measure a surface depth from) — it can read as a
            # large fraction of the object's extent for two crossing
            # slabs (usability round D: a 50 mm plate + 300 mm crate
            # reported "penetration_mm 280"). Keep it OUT of
            # penetration_mm (which consumers quote as a surface depth)
            # and report it as crossing_depth_mm.
            rep.update(state="PENETRATING",
                       penetration_mm=None,
                       crossing=True, crossing_enters=True,
                       crossing_depth_mm=round(crossing_depth * 1000, 2),
                       clearance_mm=None, severity="fail",
                       inside_test=inside_test)
            rep["verdict"] = (f"PENETRATING (crossing faces, extent "
                              f"{crossing_depth * 1000:.2f} mm, no "
                              f"contained verts — extent is the "
                              f"face-piercing edge length, not a "
                              f"surface depth) — fix")
        elif crossing:
            # crossings that never ENTER the solid: a resting overhang
            # passing a side-face plane (L-corner / u-tilt signature,
            # round D) — contact, not a spear
            rep.update(state="TOUCHING", penetration_mm=0.0,
                       clearance_mm=0.0, severity="ok",
                       inside_test=inside_test, crossing=True,
                       crossing_enters=False,
                       crossing_depth_mm=round(crossing_depth * 1000, 3))
            rep["verdict"] = ("TOUCHING (non-entering face crossings — "
                              "edge passes a face plane without "
                              "entering the solid)")
        else:
            rep.update(state="TOUCHING", penetration_mm=0.0,
                       clearance_mm=0.0, severity="ok",
                       inside_test=inside_test)
            rep["verdict"] = "TOUCHING (surface contact)"
    elif n_inside > 0:
        rep.update(state="NESTED",
                   penetration_mm=round(pen_max * 1000, 2),
                   clearance_mm=None, severity="info",
                   inside_test=inside_test)
        rep["verdict"] = (f"NESTED (fully contained; max depth "
                          f"{pen_max * 1000:.1f} mm)")
    else:
        cl_mm = round(cl * 1000, 2) if cl is not None else None
        if cl is not None and cl <= band:
            # documented band semantic: |gap| <= band counts as TOUCHING
            rep.update(state="TOUCHING", penetration_mm=0.0,
                       clearance_mm=0.0, severity="ok",
                       inside_test=inside_test)
            rep["verdict"] = (f"TOUCHING (gap {cl_mm} mm within band "
                              f"{contact_band_mm} mm)")
        else:
            rep.update(state="CLEAR", penetration_mm=None,
                       clearance_mm=cl_mm, severity="ok",
                       inside_test=inside_test)
            rep["verdict"] = f"CLEAR {cl_mm} mm gap" if cl_mm is not None \
                else "CLEAR (no surface within range)"
    rep["sampled"] = {"a": len(pts_a), "b": len(pts_b)}
    rep["timings_ms"] = round((time.time() - t0) * 1000, 1)
    return rep


def _min_clear(pts, tree, band):
    cl = None
    for p in pts:
        state, dist = classify_point(tree, p, band)
        if state == 'touch':
            # within the contact band = contact, not clearance (T4 lesson:
            # skipping these made a resting mug report "CLEAR 90 mm gap")
            cl = 0.0 if cl is None else min(cl, 0.0)
        elif state == 'outside' and dist is not None:
            cl = dist if cl is None else min(cl, dist)
    return cl


def _aabb(obj):
    ws = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    return (Vector((min(v.x for v in ws), min(v.y for v in ws),
                    min(v.z for v in ws))),
            Vector((max(v.x for v in ws), max(v.y for v in ws),
                    max(v.z for v in ws))))


def _aabb_overlap(a, b, tol=1e-4):
    """Inclusive with tolerance: float32 makes exact-contact bounds jitter
    (~60nm+), which would drop TOUCHING pairs from the prefilter (T6
    lesson: resting mug fell out of the audit). tol=0.1mm covers it."""
    return all(a[1][i] + tol >= b[0][i] and b[1][i] + tol >= a[0][i]
               for i in range(3))


def audit_scene(pairs=None, exclude=(), *, sample='verts',
                contact_band_mm=0.1, force=False,
                clearance_pad_mm=100.0):
    """All-pairs (or explicit pairs) contact audit. Worst-first sorting.
    failed = any PENETRATING with pen > contact band (NESTED is info).

    Pair discovery (when `pairs` is None): AABB overlap, INFLATED by
    `clearance_pad_mm` (default 100 mm) — so objects floating/near-contact
    within the pad still get a clearance report. Without the pad, a
    floating object produces NO pairs and a scene audit silently says
    "nothing to check" even though the mug hovers 15 mm over the desk
    (session-11 fixture round: the "nothing floating" use case needs the
    pad; 50 mm missed real 55–80 mm floats in usability rounds 1 — the
    default is now 100 mm; raise it for sparse scenes). Explicit `pairs=`
    bypasses discovery either way. Clearance is the 3D nearest-distance
    between sampled surface elements (not an axis gap).

    Returns JSON-safe dict with summary + per-pair reports."""
    t0 = time.time()
    meshes = [o for o in bpy.context.scene.objects
              if o.type == 'MESH' and o.name not in exclude
              and not o.name.startswith(("Cam", "Temp"))]
    reports = []
    if pairs:
        todo = [(bpy.data.objects[p[0]], bpy.data.objects[p[1]])
                for p in pairs]
    else:
        todo = []
        pad = max(0.0, clearance_pad_mm) / 1000.0
        aabbs = [_aabb(m) for m in meshes]
        for i in range(len(meshes)):
            for j in range(i + 1, len(meshes)):
                if _aabb_overlap(aabbs[i], aabbs[j], tol=pad):
                    todo.append((meshes[i], meshes[j]))
    for a, b in todo:
        try:
            reports.append(pair_contact(a, b, sample=sample,
                                        contact_band_mm=contact_band_mm,
                                        force=force))
        except Exception as e:  # noqa: BLE001
            reports.append({"a": a.name, "b": b.name, "state": "ERROR",
                            "error": repr(e), "severity": "fail",
                            "verdict": f"audit error: {e!r}"})
    order = {"PENETRATING": 0, "NESTED": 1, "TOUCHING": 2, "CLEAR": 3,
             "ERROR": -1}
    reports.sort(key=lambda r: order.get(r.get("state"), 9))
    # F2B-2: pair_contact raises on skinned/unguardable pairs and the
    # except-row above carries severity="fail" — but `failed` never read
    # it, so an audit whose pairs ALL errored printed failed=False (the
    # "audit exits non-zero on penetration" contract was violated exactly
    # when the audit could not look). ERROR rows fail the gate too.
    failed = (any(r.get("severity") == "fail" for r in reports) or
              any(r.get("state") == "PENETRATING" and
                  (r.get("penetration_mm") is None or
                   r["penetration_mm"] > contact_band_mm)
                  for r in reports))
    counts = {}
    for r in reports:
        counts[r.get("state", "?")] = counts.get(r.get("state", "?"), 0) + 1
    return {
        "schema": "placement_audit/1.1",
        "pairs_checked": len(reports),
        "state_counts": counts,
        "failed": failed,
        "contact_band_mm": contact_band_mm,
        "clearance_pad_mm": clearance_pad_mm,
        "pairs": reports,
        "timings_ms": round((time.time() - t0) * 1000, 1),
    }


# ---------------------------------------------------------------------------
# Layer 2 — placement solver
# ---------------------------------------------------------------------------

_ALL_TRANSFORM_PATHS = ("location", "rotation_euler",
                        "rotation_quaternion", "rotation_axis_angle",
                        "scale")


def _anim_channels(obj, paths):
    """Tagged transform fcurve/driver channels whose data_path is in
    `paths` (session-18 wave-C: one collector, three views — location /
    rotation / all-transform). Tags name the SOURCE so guards can tell
    rebasable active-action keys from NLA/driver-driven channels:
    'action:<path>[i]', 'nla:<act>:<path>[i]', 'driver:<path>[i]'.
    F2B-9: iter_all_fcurves (read-only, ALL 5.x slots) — iter_fcurves
    probed slot[0] only, and AUTO-SCAFFOLDS fresh actions as a read side
    effect."""
    chans = []
    ad = getattr(obj, "animation_data", None)
    if not ad:
        return chans
    if ad.action:
        for fc in iter_all_fcurves(ad.action):
            if fc.data_path in paths:
                chans.append(f"action:{fc.data_path}[{fc.array_index}]")
    for tr in getattr(ad, "nla_tracks", []):
        for st in tr.strips:
            act = getattr(st, "action", None)
            if act:
                for fc in iter_all_fcurves(act):
                    if fc.data_path in paths:
                        chans.append(
                            f"nla:{act.name}:{fc.data_path}"
                            f"[{fc.array_index}]")
    for dc in getattr(ad, "drivers", []):
        if dc.data_path in paths:
            chans.append(f"driver:{dc.data_path}[{dc.array_index}]")
    return chans


def _location_anim_channels(obj):
    """Location fcurves/drivers that would clobber placement writes
    (review blocker #4). F2B-9: iter_all_fcurves (read-only, ALL 5.x
    slots) — iter_fcurves probed slot[0] only, so location keys in a
    later slot were invisible and the guard passed right before a
    frame_set clobbered the placement; iter_fcurves also scaffolds fresh
    actions as a read side effect."""
    return _anim_channels(obj, ("location",))


def _rotation_anim_channels(obj):
    """Rotation fcurves/drivers (C1): seat_at(align)/place_on
    (align_to_surface) write ROTATION — a rotation-keyed object gets its
    orientation overwritten in-memory and snaps back on the next
    frame_set (hybrid pose; the tsquall faller carries object-level rot
    keys — this class is live in real films)."""
    return _anim_channels(obj, ("rotation_euler", "rotation_quaternion",
                                "rotation_axis_angle"))


def _transform_anim_channels(obj):
    """ALL transform channels incl. scale (C2): physics_place simulated a
    rotation-keyed mover then its committed pose was clobbered by its own
    keys; a rotation-keyed env passed the old location-only filter and
    froze as a static collider at a transient pose (TB4)."""
    return _anim_channels(obj, _ALL_TRANSFORM_PATHS)


def _guard_anim(obj, override):
    chans = _location_anim_channels(obj)
    if not chans:
        return None
    if override is None:
        raise RuntimeError(
            f"'{obj.name}' has location animation ({', '.join(chans[:4])}). "
            f"Placement writes would be clobbered at the next frame_set/"
            f"render. Run placement BEFORE animate(); or pass "
            f"override='keyframe' (REBASES the whole animation path by "
            f"the placement delta so EVERY keyframe keeps its relative "
            f"placement — the right choice for moving an animated prop) "
            f"or override='ignore' (at your own risk).")
    return chans


def _guard_rotation_anim(obj, override, op_name):
    """C1: ops that write ROTATION (seat_at align=True, place_on
    align_to_surface=True) must not silently clobber rotation animation.

    - default (override=None) AND override='ignore': REFUSE, naming the
      channels found — there is no safe 'ignore' for rotation writes
      (the keys WILL restore the old orientation at the next frame_set;
      the hybrid pose is exactly the class this guard exists for).
    - override='keyframe' with a QUATERNION-mode object whose rotation
      keys live in the ACTIVE action: rebaseable — returns the channel
      tags and the caller must apply _rebase_rotation_keys with the
      placement delta rotation.
    - EULER-mode (or axis-angle) rotation keys: refuse even under
      override='keyframe' — converting euler key curves is invasive; the
      error tells the consumer to switch rotation_mode to 'QUATERNION'
      (glTF-style props already are) or bake.
    - NLA/driver rotation channels: refuse even under override='keyframe'
      (the rebase only reaches the active action — the same scope as the
      location rebase)."""
    chans = _rotation_anim_channels(obj)
    if not chans:
        return None
    named = ", ".join(chans[:4])
    if override == "keyframe":
        if any(c.startswith(("nla:", "driver:")) for c in chans):
            raise RuntimeError(
                f"'{obj.name}' has rotation animation OUTSIDE the active "
                f"action ({named}) — the keyframe override can only rebase "
                f"active-action keys. Mute/consolidate the NLA strips, "
                f"remove the drivers, or bake the rotation animation "
                f"first.")
        if obj.rotation_mode != 'QUATERNION':
            raise RuntimeError(
                f"'{obj.name}' has {obj.rotation_mode}-mode rotation keys "
                f"({named}) and {op_name} writes rotation. Converting "
                f"euler key curves is invasive — switch the object's "
                f"rotation_mode to 'QUATERNION' and re-key (glTF-style "
                f"props already are), or bake the rotation animation, or "
                f"run the placement BEFORE animating.")
        return chans
    raise RuntimeError(
        f"'{obj.name}' has rotation animation ({named}). {op_name} writes "
        f"rotation, so the keys would snap the orientation back at the "
        f"next frame_set (hybrid pose). Run the placement BEFORE "
        f"animate(); or pass override='keyframe' (REBASES quaternion-mode "
        f"active-action keys by the placement delta rotation — euler-mode "
        f"keys are refused even then: switch rotation_mode to QUATERNION "
        f"or bake). override='ignore' is NOT honored for rotation writes.")


def _rebase_location_keys(obj, delta):
    """Shift ALL location fcurve keyframes channel-wise by `delta` (K4).

    The naive 'insert a key at the current frame' override left LATER
    keys holding the pre-placement pose — measured in usability R1:
    a mug re-keyed at f1 drifted 20mm INTO the tabletop by f24. Rebasing
    the path preserves the animation's shape relative to its support.
    Returns (n_keys_shifted, channels_touched)."""
    ad = getattr(obj, "animation_data", None)
    if ad is None or ad.action is None:
        return 0, []
    touched = set()
    n = 0
    # F2B-9: iter_all_fcurves is safe here despite the WRITES below — it
    # never calls .new()/.find() (the reason iter_fcurves exists), it only
    # chains EXISTING per-slot fcurve collections; the keyframe_points
    # writes go to fcurves obtained by iteration, which stay valid
    # references. Bonus: location keys in a non-[0] 5.x slot now rebase too.
    for fc in iter_all_fcurves(ad.action):
        if fc.data_path != "location" or fc.array_index not in (0, 1, 2):
            continue
        d = delta[fc.array_index]
        if abs(d) < 1e-12:
            continue
        for kp in fc.keyframe_points:
            kp.co.y += d
            n += 1
        touched.add(fc.array_index)
        try:
            fc.update()
        except AttributeError:
            pass
    if touched:
        f = bpy.context.scene.frame_current
        bpy.context.scene.frame_set(f)  # re-evaluate at the same frame
        bpy.context.view_layer.update()
    return n, [f"location[{'xyz'[i]}]" for i in sorted(touched)]


def _world_rotation_delta_to_basis(obj, q_world_offset):
    """Convert a WORLD-frame rotation delta into the object's BASIS space
    (the F2B-8/F5A-3 twin for rotation): matrix_world = A @ matrix_basis
    with A = parent.matrix_world @ matrix_parent_inverse, so a world
    pre-multiply Q corresponds to a basis pre-multiply of A^-1 Q A. The
    rotation fcurves are basis-space — feeding them the raw world delta
    would misrotate every keyed child of a rotated parent. Parentless
    objects conjugate through identity (q_basis == q_world, the C1
    design's 'world-frame' law)."""
    if obj.parent is None:
        return q_world_offset.copy()
    a = (obj.parent.matrix_world @
         obj.matrix_parent_inverse).to_quaternion()
    return a.inverted() @ q_world_offset @ a


def _rebase_rotation_keys(obj, q_basis_offset):
    """C1: pre-multiply EVERY rotation_quaternion keyframe of the active
    action by the BASIS-space placement delta rotation — the quaternion
    twin of _rebase_location_keys (K4): the naive 'key the current
    frame' override leaves LATER keys holding the pre-placement
    orientation. q_new = q_offset @ q_key at each key (the C1 design's
    world-frame law for parentless objects; the caller passes the
    conjugated basis delta for parented ones). F2B-9: iter_all_fcurves
    is safe here despite the WRITES — it never calls .new()/.find(), it
    only chains EXISTING per-slot fcurve collections (5.x slotted-action
    law). Refuses partial (1-3 channel) quaternion curves and
    non-uniform keyframe times — converting those is invasive (bake
    first). Returns (n_keypoints_rebased, channels_touched)."""
    ad = getattr(obj, "animation_data", None)
    if ad is None or ad.action is None:
        return 0, []
    fcs = {}
    for fc in iter_all_fcurves(ad.action):
        if (fc.data_path == "rotation_quaternion"
                and fc.array_index in (0, 1, 2, 3)):
            fcs[fc.array_index] = fc
    if not fcs:
        # no live quaternion curves (e.g. dead euler keys under
        # QUATERNION rotation_mode) — nothing to rebase
        return 0, []
    if len(fcs) != 4:
        missing = sorted(set(range(4)) - set(fcs))
        raise RuntimeError(
            f"'{obj.name}' has PARTIAL rotation_quaternion fcurves "
            f"(missing components {missing}) — pre-multiplying would "
            f"corrupt the curve. Bake the rotation animation first.")
    times = None
    for i in range(4):
        ts = [kp.co.x for kp in fcs[i].keyframe_points]
        if times is None:
            times = ts
        elif len(ts) != len(times) or any(
                abs(a - b) > 1e-6 for a, b in zip(ts, times)):
            raise RuntimeError(
                f"'{obj.name}' has rotation_quaternion fcurves with "
                f"non-uniform keyframe times — per-key pre-multiplication "
                f"needs all 4 components keyed together. Bake the "
                f"rotation animation first.")
    q_off = q_basis_offset.normalized()
    for j, _t in enumerate(times):
        # array_index order IS wxyz (0=w ... 3=z) for both the fcurves
        # and mathutils.Quaternion's index access
        q_key = Quaternion((fcs[0].keyframe_points[j].co.y,
                            fcs[1].keyframe_points[j].co.y,
                            fcs[2].keyframe_points[j].co.y,
                            fcs[3].keyframe_points[j].co.y))
        q_new = (q_off @ q_key).normalized()
        for i in range(4):
            fcs[i].keyframe_points[j].co.y = q_new[i]
    for i in range(4):
        try:
            fcs[i].update()
        except AttributeError:
            pass
    f = bpy.context.scene.frame_current
    bpy.context.scene.frame_set(f)  # re-evaluate at the same frame
    bpy.context.view_layer.update()
    return 4 * len(times), [f"rotation_quaternion[{'wxyz'[i]}"
                            for i in range(4)]


def _world_delta_to_local(obj, delta_world):
    """Convert a world-space translation delta into the object's BASIS
    delta — the space obj.location and its location fcurves live in
    (F2B-8: per-component location adds are PARENT-space; a rotated or
    scaled parent silently misdirected every world-space solver).

    matrix_world = A @ matrix_basis with A = parent.matrix_world @
    matrix_parent_inverse, so a world translate T(dW) conjugates to a
    basis translate T(A.lin^-1 @ dW). Parentless objects are identity."""
    d = Vector(delta_world)
    if obj.parent is None:
        return d
    a = obj.parent.matrix_world @ obj.matrix_parent_inverse
    return a.inverted().to_3x3() @ d


def _apply_translation(obj, dz, override, report):
    """Apply a WORLD-space vertical shift (place_on/snap_z semantics).

    F2B-8: this used to be `obj.location.z += dz` — a PARENT-space write.
    Under a rotated/scaled parent the shift went the wrong way AND needed
    x/y basis components that were never written. Convert the world dz to
    basis space first; the keyframe rebase gets the basis delta too (the
    fcurves are basis-space)."""
    if abs(dz) < 1e-12:
        return
    d_local = _world_delta_to_local(obj, Vector((0.0, 0.0, dz)))
    obj.location += d_local
    report["applied_dz_m"] = round(dz, 6)
    if any(abs(v) > 1e-9 for v in d_local.xy):
        report["parent_space_conversion"] = {
            "world_dz": round(dz, 6),
            "local_delta": [round(v, 6) for v in d_local],
            "note": "parented mover: the world z shift needed x/y basis "
                    "components too (F2B-8)"}
    if override == "keyframe":
        ad = getattr(obj, "animation_data", None)
        has_anim = (ad is not None and ad.action is not None)
        if has_anim:
            # K4: rebase the WHOLE path (later keys must not keep the
            # pre-placement pose — usability R1 measured the drift)
            n, chans = _rebase_location_keys(obj, d_local)
            report["keyframes_rebased"] = n
            report["rebased_channels"] = chans
        else:
            # key ALL THREE channels (round-2/U5): keying only Z left the
            # x/y fcurves holding the OLD position — the in-memory audit
            # passed, but on reload the un-keyed x/y snapped back and the
            # object teleported. A keyframe override must capture the FULL
            # current location so the saved curve == the final transform.
            f = bpy.context.scene.frame_current
            for i in range(3):
                obj.keyframe_insert(data_path="location", index=i, frame=f)
            report["keyframe_inserted"] = True
            report["keyframed_channels"] = ["location[x]", "location[y]",
                                            "location[z]"]
        ad = getattr(obj, "animation_data", None)
        if ad is not None and list(ad.nla_tracks):
            report["nla_warning"] = (
                "object has NLA strips — keyframe edits write the active "
                "action only; playing strips evaluate ON TOP and can still "
                "snap the object back. Mute/consolidate the strips or use "
                "override='ignore' deliberately (code-review gate P1).")


def _origin_centroid_warn(obj, report, tol_m=0.05):
    """Non-fatal warning when object origin and mesh centroid disagree
    (usability round-1/U3): location writes move the ORIGIN, so meshes
    baked at world coords (origin far from geometry, common in scripts
    that skip transform_apply) make ops like set_location look like a
    RELATIVE world move. Placement ops are origin-safe (they solve from
    world-space geometry), but the warning tells the agent WHY a later
    set_location may surprise them."""
    try:
        mw = obj.matrix_world
        vs = obj.data.vertices
        n = len(vs)
        if n == 0:
            return
        step = max(1, n // 500)
        cx = cy = cz = 0.0
        m = 0
        for i in range(0, n, step):
            w = mw @ vs[i].co
            cx += w.x; cy += w.y; cz += w.z; m += 1
        d = (Vector((cx / m, cy / m, cz / m)) - mw.translation).length
        if d > tol_m:
            report["origin_offset_warning"] = (
                f"object origin is {d * 1000:.0f} mm from the mesh "
                f"centroid — location writes move the origin, so on this "
                f"object set_location shifts world position by the origin "
                f"offset. Prefer place_on/snap_z/seat_at (world-space "
                f"solvers) or run Origin-to-Geometry first.")
    except Exception:  # noqa: BLE001 — warning must never break an op
        pass


def support_heights(supports, pts_xy, from_z=None):
    """Topmost support surface z under each (x, y), via -Z raycasts against
    the supports' world BVH trees (cannot hit the placed object itself).
    Returns (heights, detail, normals) — heights[i] is float or None
    (void); normals[i] is the hit face normal (or None) for slope
    awareness (round-2/U5: axis-aligned place_on on a slope leaves a
    wedge gap under the up-slope half with a green report)."""
    from_z = from_z if from_z is not None else max(
        _aabb(s)[1].z for s in supports) + 1.0
    trees = [(s, world_bvh(s)) for s in supports]
    heights, detail, normals = [], [], []
    for x, y in pts_xy:
        best = None
        best_n = None
        per = {}
        for s, tr in trees:
            loc, nrm, idx, dist = tr.ray_cast(Vector((x, y, from_z)),
                                              Vector((0, 0, -1)), 1e4)
            per[s.name] = round(loc.z, 4) if loc else None
            if loc is not None and (best is None or loc.z > best):
                best = loc.z
                best_n = Vector(nrm).normalized() if nrm else None
        heights.append(best)
        normals.append(best_n)
        detail.append(per)
    return heights, detail, normals


def _percentile(vals, p):
    if not vals:
        return None
    s = sorted(vals)
    k = (len(s) - 1) * p / 100.0
    f = math.floor(k)
    c = min(f + 1, len(s) - 1)
    if f == c:
        return s[int(k)]
    return s[f] * (c - k) + s[c] * (k - f)


def place_on(obj, *supports, clearance=0.0, footprint='bottom', mode='rest',
             grid_n=12, inset=0.0, keep_xy=True, override=None,
             contact_band_mm=0.1, output=None, force=False,
             align_to_surface=False):
    """One-shot 'object rests on support surface' solver with FOOTPRINT
    AUTO-WIDEN (usability R1/F4, three bites: tabletop-on-leg,
    book-on-yawed-book, lampshade-on-pole): the default 'bottom'
    footprint raycasts only downward-facing verts — a small/pedestal
    support misses every ray. On 'no support found' with footprint=
    'bottom', the solve RETRIES with footprint='grid' (whole-bbox
    sampling) and the report records footprint_autowiden. Pass
    footprint explicitly to opt out."""
    try:
        rep = _place_on_impl(obj, *supports, clearance=clearance,
                             footprint=footprint, mode=mode, grid_n=grid_n,
                             inset=inset, keep_xy=keep_xy, override=override,
                             contact_band_mm=contact_band_mm, output=None,
                             force=force, align_to_surface=align_to_surface)
    except RuntimeError as e:
        if footprint == 'bottom' and 'no support surface found' in str(e):
            rep = _place_on_impl(obj, *supports, clearance=clearance,
                                 footprint='grid', mode=mode, grid_n=grid_n,
                                 inset=inset, keep_xy=keep_xy,
                                 override=override,
                                 contact_band_mm=contact_band_mm,
                                 output=None, force=force,
                                 align_to_surface=align_to_surface)
            rep["footprint_autowiden"] = (
                "bottom found no support — retried with footprint='grid' "
                "(pedestal/overhang support); pass footprint explicitly "
                "to opt out")
            print(f"[place_on] {obj.name}: footprint auto-widened "
                  f"bottom->grid (support missed by downward-facing-vert "
                  f"rays)")
        else:
            raise
    return _maybe_write(rep, output)


def _place_on_impl(obj, *supports, clearance=0.0, footprint='bottom',
                   mode='rest', grid_n=12, inset=0.0, keep_xy=True,
                   override=None, contact_band_mm=0.1, output=None,
                   force=False, align_to_surface=False):
    """One-shot 'object rests on support surface' solver.

    Single-contact-plane solver (design review #1): all footprint points
    land on ONE solved plane z* + clearance. If the footprint spans
    multi-level support (butt on cushion + feet on floor), the report sets
    multi_level=true with the height distribution — use seat_at for rigs.

    footprint: 'bottom' (downward-facing verts, w/ fallback), 'all', 'grid'.
    mode tokens are validated (C10 — a typo used to surface as a raw
    dict-lookup KeyError); align_to_surface engages on grid footprints
    too (C9) and the report always carries explicit aligned_to_surface /
    align_skip_reason fields. Rotation-writing runs (align) refuse
    rotation-keyed objects unless override='keyframe' can rebase the
    quaternion keys (C1).
    inset: shrink footprint to points >= inset meters inside its own bbox
    (seat lips/edges).
    keep_xy: True (default) — solves Z ONLY, object stays at its current
    x/y. keep_xy=False is REFUSED (F2B-4): the docstring promised a move
    to the support height-field's centroid but the code never implemented
    it — it was accepted, echoed in the report, and returned ok=True for
    an unachieved state. To land on a DIFFERENT support, move the object
    over it first (move_to / set_location), then place_on.
    override: None | 'keyframe' | 'ignore' (see _guard_anim).
    Returns placement report (JSON-safe) with post-solve contact audit
    against every support."""
    if not supports:
        # F2B-15: an empty support list used to surface as
        # "max() arg is an empty sequence" from support_heights.
        raise RuntimeError(
            "place_on: no supports given — name at least one support "
            "object (the TOPMOST surface under the mover)")
    if footprint not in ('bottom', 'all', 'grid'):
        # F2B-16: any unrecognized token (kb-documented 'inset', 'Bottom',
        # 'grids') used to fall into the else branch = silent whole-vert
        # sampling with the report echoing the bogus token and ok=True.
        raise RuntimeError(
            f"place_on: unknown footprint {footprint!r} — valid values: "
            f"'bottom' (downward-facing verts, default), 'all' (every "
            f"vert), 'grid' (samples the bbox bottom). 'inset' is NOT a "
            f"footprint value — pass the numeric inset=<meters> param "
            f"instead (it shrinks the footprint inside its own bbox for "
            f"seat lips).")
    if mode not in ('rest', 'sink', 'p25', 'p50', 'p75'):
        # C10: the mode token used to surface as a raw dict-lookup
        # KeyError at the solve step (unhelpful shape, F2B-16 pattern).
        raise RuntimeError(
            f"place_on: unknown mode {mode!r} — valid values: 'rest' "
            f"(max support height under the footprint, default), 'sink' "
            f"(min — wells/insets; the audit will report the intended "
            f"penetration), 'p25', 'p50', 'p75' (support-height "
            f"percentiles).")
    if keep_xy is not True:
        raise RuntimeError(
            "place_on: keep_xy=False is refused (F2B-4: accepted-but-"
            "never-implemented — it returned ok=True for an unachieved "
            "state). Move the object over the support first with move_to "
            "or set_location, then place_on with the default keep_xy.")
    t0 = time.time()
    report = {"op": "place_on", "obj": obj.name,
              "supports": [s.name for s in supports],
              "clearance_m": clearance, "footprint": footprint,
              "mode": mode, "keep_xy": keep_xy,
              "contact_band_mm": contact_band_mm,
              "aligned_to_surface": False}
    _skinned_guard(obj, force)
    for s in supports:
        _skinned_guard(s, force)
    _origin_centroid_warn(obj, report)
    anim = _guard_anim(obj, override)
    if anim:
        report["anim_override"] = anim
    # C1: align_to_surface MAY write rotation — a rotation-keyed object
    # is refused up front (or the quaternion keys are marked rebaseable
    # under override='keyframe')
    rot_chans = (_guard_rotation_anim(obj, override, "place_on")
                 if align_to_surface else None)
    if rot_chans:
        report["rotation_anim_override"] = rot_chans
    bpy.context.view_layer.update()
    clear_bvh_cache()

    # --- footprint points -------------------------------------------------
    heights = detail = hit_normals = None
    if footprint == 'grid':
        (mn, mx) = _aabb(obj)
        # F17: fixed cell centers miss narrow inset supports — a 0.08m
        # table leg on a 2.4m top falls between 12×12 columns. Refine
        # density ×4 until rays hit something (cap 192² = 36864 rays,
        # still sub-second on a BVH). The refine is the fix for the
        # auto-widen path too: bottom->grid retry now actually finds
        # inset legs instead of failing at 12×12.
        n = grid_n
        while True:
            pts_xy = []
            for i in range(n):
                for j in range(n):
                    fx = mn.x + (mx.x - mn.x) * (i + 0.5) / n
                    fy = mn.y + (mx.y - mn.y) * (j + 0.5) / n
                    pts_xy.append((fx, fy))
            z_ref = mn.z
            heights, detail, hit_normals = support_heights(supports, pts_xy)
            if any(h is not None for h in heights) or n >= 192:
                break
            n *= 4
        # C9: grid footprints fill footprint_pts exactly like the vert
        # paths do — the empty list used to make align_to_surface
        # silently no-op on grid (and the refine pass never ran) because
        # both gate on footprint_pts truthiness.
        footprint_pts = [Vector((x, y, z_ref)) for x, y in pts_xy]
        if n != grid_n:
            report["footprint_grid_refined"] = (
                f"{grid_n}x{grid_n} found no support — refined to "
                f"{n}x{n} (narrow inset support, F17)")
            print(f"[place_on] {obj.name}: footprint grid refined "
                  f"{grid_n}->{n} (narrow supports missed at base density)")
    else:
        pts = surface_samples(obj, mode=('bottom' if footprint == 'bottom'
                                         else 'verts'))
        if inset > 0:
            xs = [p.x for p in pts]
            ys = [p.y for p in pts]
            mnx, mxx = min(xs) + inset, max(xs) - inset
            mny, mxy = min(ys) + inset, max(ys) - inset
            pts = [p for p in pts
                   if mnx <= p.x <= mxx and mny <= p.y <= mxy]
        if not pts:
            raise RuntimeError(
                f"place_on: empty footprint for '{obj.name}' "
                f"(footprint={footprint}, inset={inset}). Try footprint="
                f"'all' or 'grid', or inset=0.")
        report["footprint_fallback"] = footprint == 'bottom' and not any(
            world_normal(obj, v.normal).z < -0.3 for v in
            obj.data.vertices)
        pts_xy = [(p.x, p.y) for p in pts]
        z_ref = min(p.z for p in pts)
        footprint_pts = pts

    # --- height field + solve ---------------------------------------------
    if heights is None:  # 'grid' already computed (maybe refined) above
        heights, detail, hit_normals = support_heights(supports, pts_xy)
    hit_supports = sorted({name for per in detail
                           for name, z in per.items() if z is not None})
    report["support_found"] = hit_supports
    good = [h for h in heights if h is not None]
    good_normals = [n for h, n in zip(heights, hit_normals)
                    if h is not None and n is not None]
    if not good:
        raise RuntimeError(
            f"place_on: no support surface found under '{obj.name}' "
            f"(check support objects / from_z). If the object OVERHANGS "
            f"its support (every bottom vert hangs off the edge — "
            f"common for plants on stands, trays on lips), retry with "
            f"footprint='grid' which samples the whole bbox footprint. "
            f"If the support is OCCLUDED below a taller object on the "
            f"same spot (stacked/nested supports — the ray hits the "
            f"upper item first), pass only the TOPMOST support as the "
            f"support list, or check look --closeup for what actually "
            f"sits under the target (F20-R6: the occluded-support class).")

    # --- slope awareness (round-2/U5) --------------------------------------
    # Mean support normal under the footprint; a sloped support means an
    # axis-aligned object rests corner-first with a wedge air gap under
    # the up-slope half — while the audit still reads TOUCHING (min gap
    # 0). Report it, and optionally rotate the object to the surface.
    mean_n = None
    if good_normals:
        acc = Vector((0.0, 0.0, 0.0))
        for n in good_normals:
            acc += n
        if acc.length > 1e-9:
            mean_n = acc.normalized()
    if not align_to_surface:
        # C9: explicit field — a non-aligned solve can never pass silently
        report["align_skip_reason"] = (
            "align_to_surface=False — not requested")
    if mean_n is not None:
        slope = round(math.degrees(math.acos(
            min(1.0, max(-1.0, mean_n.z)))), 2)
        report["surface_normal"] = [round(v, 4) for v in mean_n]
        report["slope_deg"] = slope
        if slope > 5.0 and not align_to_surface:
            report["slope_warning"] = (
                f"support slopes {slope:.1f} deg from horizontal — the "
                f"object is left axis-aligned, so it rests corner-first "
                f"(wedge air gap under the up-slope half even though the "
                f"contact audit reads TOUCHING). Pass align_to_surface="
                f"true to rotate the object onto the incline, or accept "
                f"it deliberately.")
        if align_to_surface and slope > 0.5 and footprint_pts:
            # maps the object's +Z onto the surface normal, so the object's
            # -Z (its bottom) lies flat on the incline. ('-Z' here was a P0
            # flip — code-review gate, session 11: '-Z' points the object's
            # DOWN-side at the sky; re-measure+solve then seats it inverted
            # and the contact check false-passes. Regression: T2 asserts
            # world +Z . normal > 0.9 after align.)
            q = mean_n.to_track_quat('Z', 'Y')
            mn, mx = _aabb(obj)
            pivot = Vector(((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, mn.z))
            R = q.to_matrix().to_4x4()
            q_world_before = obj.matrix_world.to_quaternion().copy()
            obj.matrix_world = (Matrix.Translation(pivot) @ R @
                                Matrix.Translation(-pivot) @
                                obj.matrix_world)
            report["aligned_to_surface"] = True
            report["aligned_rotation_q"] = [round(v, 5) for v in q]
            bpy.context.view_layer.update()
            if rot_chans:
                # C1: rebase the quaternion keys by the ACTUAL world
                # rotation delta the align just applied (conjugated into
                # basis space for parented movers) — otherwise the next
                # frame_set restores the pre-align orientation (hybrid
                # pose).
                q_offset_world = (obj.matrix_world.to_quaternion() @
                                  q_world_before.inverted())
                nrot, rchans = _rebase_rotation_keys(
                    obj,
                    _world_rotation_delta_to_basis(obj, q_offset_world))
                report["rotation_keyframes_rebased"] = nrot
                report["rebased_rotation_channels"] = rchans
            clear_bvh_cache()
            # re-measure footprint in the new orientation
            pts = surface_samples(obj, mode=('bottom' if footprint == 'bottom'
                                             else 'verts'))
            if not pts:
                pts = footprint_pts
            pts_xy = [(p.x, p.y) for p in pts]
            z_ref = min(p.z for p in pts)
            footprint_pts = pts
            heights, detail, hit_normals = support_heights(supports, pts_xy)
            good = [h for h in heights if h is not None]
            good_normals = [n for h, n in zip(heights, hit_normals)
                            if h is not None and n is not None]
            if not good:
                raise RuntimeError(
                    f"place_on: no support surface found after align "
                    f"(object '{obj.name}').")
        elif align_to_surface and slope <= 0.5:
            # C9: requested but nothing to do — say so explicitly
            report["align_skip_reason"] = (
                f"support slope {slope:.2f} deg is below the 0.5 deg "
                f"align threshold — already flat")
        elif align_to_surface:
            # defensive: the truthiness gate above no longer trips for
            # grid (footprint_pts is always filled) but stay explicit
            report["align_skip_reason"] = (
                "empty footprint points — nothing to align")
    elif align_to_surface:
        # C9: no normals under the footprint -> align is impossible;
        # record it instead of leaving the field silently False
        report["align_skip_reason"] = (
            "no support normals under the footprint — cannot align")
    dist_report = {"n": len(good), "n_void": len(heights) - len(good),
                   "min_m": round(min(good), 4), "max_m": round(max(good), 4),
                   "p25_m": round(_percentile(good, 25), 4),
                   "median_m": round(_percentile(good, 50), 4),
                   "p75_m": round(_percentile(good, 75), 4)}
    report["support_height_field"] = dist_report
    spread = max(good) - min(good)
    report["multi_level"] = spread > 0.025
    if report["multi_level"]:
        report["multi_level_note"] = (
            f"support height spread {spread * 1000:.1f} mm under footprint; "
            f"place_on solves a single contact plane — for multi-level rigs "
            f"(seated figure) use seat_at or split the placement.")

    hsel = {"rest": max(good), "sink": min(good), "p25": _percentile(good, 25),
            "p50": _percentile(good, 50), "p75": _percentile(good, 75)}[mode]
    target = hsel + clearance
    dz = target - z_ref
    _apply_translation(obj, dz, override, report)
    bpy.context.view_layer.update()
    clear_bvh_cache()

    # --- refine (review #6: deterministic, mode-gated, clamped) -----------
    # Target state: worst bottom-vert gap == requested clearance (NOT 0 —
    # a plain "shift down by gap" would destroy the requested clearance,
    # T2 lesson). Penetration shifts up; residual-vs-clearance shifts
    # symmetrically; both clamped.
    if mode != 'sink' and footprint_pts:
        bot = surface_samples(obj, mode='bottom') or footprint_pts
        tree_others = [world_bvh(s) for s in supports]
        band = contact_band_mm / 1000.0
        pen, gap = 0.0, None
        for p in bot:
            for tr in tree_others:
                state, dist = classify_point(tr, p, band)
                if state == 'inside' and dist:
                    pen = max(pen, dist)
                elif state == 'touch':
                    # touching verts DEFINE the contact plane — count as
                    # gap 0, never skip them (T2 lesson: skipping let a
                    # high vert's gap drive a burying shift)
                    gap = 0.0 if gap is None else min(gap, 0.0)
                elif state == 'outside' and dist is not None:
                    gap = dist if gap is None else min(gap, dist)
        # clamp guards pathological loops; but a MEASURED first-pass error
        # (e.g. the aligned-slope error = tan(slope)*extent, round-2/U5)
        # must be correctable in one shot.
        # Gap metrics are 3D nearest-distances; the shift is VERTICAL. On
        # a slope those differ by cos(slope) (round-2/U5: a single 0.1125
        # vertical shift closed only cos(15°) of a normal-direction gap,
        # leaving 3.8mm) — correct the residual into vertical units.
        _slope_rad = math.radians(report.get("slope_deg", 0.0))
        _corr = 1.0 / max(0.2, math.cos(_slope_rad))
        clamp = max((max(good) - min(good)) * 5, 0.05,
                    (pen or 0.0) * _corr, (gap or 0.0) * _corr)
        # under-correct, never overshoot (code-review gate P1: near-vertical
        # support faces inflate the cos correction up to 5x — capping the
        # shift at the measured error guarantees a conservative result)
        if pen > band:
            shift = min(pen * _corr, clamp, max(pen, band))
            _apply_translation(obj, shift, override, report)
            report["refine"] = {"reason": "penetration",
                                "shift_m": round(shift, 6)}
        elif gap is not None:
            residual = gap - clearance
            if residual > band:
                shift = -min(residual * _corr, clamp, max(residual, band))
                _apply_translation(obj, shift, override, report)
                report["refine"] = {"reason": "gap above clearance",
                                    "shift_m": round(shift, 6)}
            elif residual < -band:
                shift = min(-residual * _corr, clamp, max(-residual, band))
                _apply_translation(obj, shift, override, report)
                report["refine"] = {"reason": "gap below clearance",
                                    "shift_m": round(shift, 6)}
        bpy.context.view_layer.update()
        clear_bvh_cache()

    # --- post-solve audit vs every support --------------------------------
    post = []
    for s in supports:
        try:
            post.append(pair_contact(obj, s, contact_band_mm=contact_band_mm,
                                     force=force))
        except Exception as e:  # noqa: BLE001
            post.append({"a": obj.name, "b": s.name, "state": "ERROR",
                         "error": repr(e), "severity": "fail"})
    report["post_contact"] = post
    report["ok"] = all(p.get("severity") != "fail" for p in post)
    report["timings_ms"] = round((time.time() - t0) * 1000, 1)
    return _maybe_write(report, output)


def seat_at(obj, seat_empty, *, reference='bottom', offset=None, align=True,
            override=None, seat_mesh=None, contact_band_mm=0.1, output=None,
            force=False):
    """CAD-mate style seating: place obj relative to a named anchor empty
    (kit convention e.g. 'Jeep.SeatL'; figure faces the empty's +Y, sits
    along -Y, empty +Z is up).

    reference: 'bottom' — obj's bbox bottom-CENTER lands at the anchor
    (plus offset); 'origin' — obj's origin lands at the anchor; 'centroid'
    — the vertex centroid lands at the anchor (non-mesh objects fall back
    to origin, reported). Any other token is REFUSED (F2B-6: unknown
    tokens used to fall through to origin-anchoring while the report
    echoed the requested token back).
    offset: (dx, dy, dz) interpreted in the EMPTY's local space.
    seat_mesh: optional mesh object to post-audit against (e.g. cushion).
    force: passthrough to _skinned_guard (C7 — seat_at was the only
    solver without it); force=True labels the post-contact audit
    'unreliable-skinned' instead of refusing.
    align=True writes ROTATION — rotation-keyed objects are refused
    unless override='keyframe' can rebase quaternion-mode keys (C1;
    euler-mode keys are refused even then).
    Returns placement report with post_contact when seat_mesh given.

    F2B-8: all writes are composed in WORLD space via matrix_world (the
    move_to pattern). The old per-component `obj.location += delta` and
    the bare `rotation_euler =` write are PARENT/BASIS-space — a rotated
    or scaled parent silently redirected the seating; the keyframe rebase
    gets the exact BASIS delta (fcurves are basis-space)."""
    t0 = time.time()
    report = {"op": "seat_at", "obj": obj.name, "seat": seat_empty.name,
              "reference": reference}
    if reference not in ('bottom', 'origin', 'centroid'):
        raise RuntimeError(
            f"seat_at: unknown reference '{reference}' — valid tokens: "
            f"'bottom' (bbox bottom-center), 'origin', 'centroid'")
    # C7: seat_at was the only solver with no _skinned_guard/force
    # (place_on:997, move_to, pair_contact all guard)
    _skinned_guard(obj, force)
    if seat_mesh is not None:
        _skinned_guard(seat_mesh, force)
    _origin_centroid_warn(obj, report)
    anim = _guard_anim(obj, override)
    if anim:
        report["anim_override"] = anim
    # C1: align=True writes ROTATION — refuse rotation-keyed objects up
    # front (or mark the quaternion keys rebaseable under keyframe)
    rot_chans = (_guard_rotation_anim(obj, override, "seat_at")
                 if align else None)
    if rot_chans:
        report["rotation_anim_override"] = rot_chans
    bpy.context.view_layer.update()
    clear_bvh_cache()

    pre_bbox = _aabb(obj)
    report["pre_bbox_min_m"] = [round(v, 4) for v in pre_bbox[0]]
    report["pre_bbox_max_m"] = [round(v, 4) for v in pre_bbox[1]]

    _basis_before = obj.matrix_basis.translation.copy()
    q_world_before = obj.matrix_world.to_quaternion().copy()
    seat_mw = seat_empty.matrix_world.copy()
    target_loc = seat_mw.translation.copy()
    if align:
        # world-rotation ABSOLUTE via matrix_world (F2B-8 parent-safety:
        # the old basis write `rotation_euler = seat_mw.to_euler()` let
        # parent rotation leak into world orientation). Wave A first tried
        # a RELATIVE premultiply (R_seat @ R_old) — that STACKED the
        # mover's existing yaw on the anchor's (t9 S1b: 10deg + 35deg =
        # 45deg) instead of COPYING it, breaking the documented absolute
        # contract ("figure faces the empty's +Y"). Set the world rotation
        # to the anchor's exactly; the anchor translation below
        # re-positions the object.
        # F5A-2: preserve the mover's WORLD SCALE — a pure-rotation linear
        # part silently rescaled any non-unit-scaled mover (the old
        # rotation_euler write preserved scale; this must too). to_scale()
        # is Blender's decompose — approximate under shear, which kit
        # movers don't carry.
        S = obj.matrix_world.to_3x3().to_scale()
        L4 = (seat_mw.to_euler().to_matrix() @
              Matrix.Diagonal(S)).to_4x4()
        obj.matrix_world = Matrix.Translation(
            obj.matrix_world.translation) @ L4
        bpy.context.view_layer.update()
    q_delta_basis = None
    if align and rot_chans:
        # C1: the align write just changed the world rotation by
        # q_offset = q_after @ q_before^-1; the keys must be rebased by
        # the same delta (conjugated into basis space for parented
        # movers) or the next frame_set restores the old orientation.
        q_offset_world = (obj.matrix_world.to_quaternion() @
                          q_world_before.inverted())
        q_delta_basis = _world_rotation_delta_to_basis(obj, q_offset_world)
    if offset:
        target_loc = seat_mw @ Vector(offset)
    if reference == 'bottom':
        mn, mx = _aabb(obj)
        anchor_obj = Vector(((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, mn.z))
        delta = target_loc - anchor_obj
    elif reference == 'centroid':
        vs = obj.data.vertices if getattr(obj, 'data', None) is not None else None
        if vs is None:
            report["reference_fallback"] = (
                "centroid requested on non-mesh object — used origin")
            ref_pt = obj.matrix_world.translation.copy()
        else:
            step = max(1, len(vs) // 500)
            cx = cy = cz = 0.0
            m = 0
            mw = obj.matrix_world
            for i in range(0, len(vs), step):
                w = mw @ vs[i].co
                cx += w.x; cy += w.y; cz += w.z; m += 1
            ref_pt = Vector((cx / m, cy / m, cz / m))
        delta = target_loc - ref_pt
    else:  # 'origin'
        delta = target_loc - obj.matrix_world.translation
    obj.matrix_world = Matrix.Translation(delta) @ obj.matrix_world
    report["applied_translation_m"] = [round(v, 5) for v in delta]
    bpy.context.view_layer.update()
    post_bbox = _aabb(obj)
    report["post_bbox_min_m"] = [round(v, 4) for v in post_bbox[0]]
    report["post_bbox_max_m"] = [round(v, 4) for v in post_bbox[1]]
    if reference == 'bottom':
        report["landed_semantic"] = (
            "bbox bottom-CENTER (world x/y midpoint of the bbox, mesh "
            "min z) now sits at the anchor — NOT the object origin; for "
            "asymmetric meshes (legs forward) the origin ends up offset "
            "from the anchor. Use reference='origin' to land the origin.")
    if override == "keyframe":
        ad = getattr(obj, "animation_data", None)
        if ad is not None and ad.action is not None:
            # F2B-8: the fcurves live in BASIS space — rebase by the exact
            # basis translation change, not the world delta.
            d_local = obj.matrix_basis.translation - _basis_before
            n, chans = _rebase_location_keys(obj, d_local)
            report["keyframes_rebased"] = n
            report["rebased_channels"] = chans
        else:
            obj.keyframe_insert(data_path="location",
                                frame=bpy.context.scene.frame_current)
            report["keyframe_inserted"] = True
        if q_delta_basis is not None:
            # C1: quaternion twin of the location rebase (rotation keys
            # can only exist when the action does — the guard above
            # refused NLA/driver rotation channels)
            nrot, rchans = _rebase_rotation_keys(obj, q_delta_basis)
            report["rotation_keyframes_rebased"] = nrot
            report["rebased_rotation_channels"] = rchans
    bpy.context.view_layer.update()
    clear_bvh_cache()
    if seat_mesh is not None:
        try:
            report["post_contact"] = pair_contact(
                obj, seat_mesh, contact_band_mm=contact_band_mm,
                force=force)
            report["ok"] = report["post_contact"].get("severity") != "fail"
        except Exception as e:  # noqa: BLE001 — C7: wrap, never hide
            # C7: the move already committed — the raised error must
            # carry the applied placement fields so the consumer can see
            # what state the scene is in (the partial report is also
            # persisted to `output` when one was requested).
            _maybe_write(report, output)
            raise RuntimeError(
                f"seat_at: post-contact audit failed AFTER the placement "
                f"committed — the scene now holds the seated pose. "
                f"anchor='{report['seat']}' "
                f"reference='{report['reference']}' "
                f"applied_translation_m="
                f"{report.get('applied_translation_m')} "
                f"post_bbox_min_m={report.get('post_bbox_min_m')} "
                f"post_bbox_max_m={report.get('post_bbox_max_m')} "
                f"(partial report: "
                f"{output if output else 'no output path requested'}) — "
                f"original error: {e}") from e
    report["timings_ms"] = round((time.time() - t0) * 1000, 1)
    return _maybe_write(report, output)


def move_to(obj, target, *, reference='bottom-center', override=None,
            output=None):
    """World-space move: put obj's REFERENCE point exactly at `target`
    (world xyz). The kit op that set_location should have been for
    baked-world meshes (usability rounds 1-2): set_location moves the
    ORIGIN, which on origin-baked meshes acts like a relative shift and
    silently misplaces the geometry. move_to solves from the mesh's
    world-space geometry, so it is origin-independent.

    reference: 'bottom-center' (bbox bottom-xy-center — the natural
    'put it HERE' anchor), 'centroid' (vertex centroid), 'origin'.
    Returns placement report (JSON-safe)."""
    t0 = time.time()
    report = {"op": "move_to", "obj": obj.name, "target": list(target),
              "reference": reference}
    _skinned_guard(obj, False)
    _origin_centroid_warn(obj, report)
    anim = _guard_anim(obj, override)
    if anim:
        report["anim_override"] = anim
    bpy.context.view_layer.update()
    _clear = clear_bvh_cache()
    mw = obj.matrix_world
    # empties/other non-mesh objects have obj.data=None (F10: move_to on a
    # seat_at ANCHOR is a legitimate operation — the anchor is the target)
    vs = obj.data.vertices if getattr(obj, 'data', None) is not None else None
    if reference == 'centroid':
        if vs is None:
            report["reference_fallback"] = (
                "centroid requested on non-mesh object — used origin")
            ref_pt = mw.translation.copy()
        else:
            step = max(1, len(vs) // 500)
            cx = cy = cz = 0.0
            m = 0
            for i in range(0, len(vs), step):
                w = mw @ vs[i].co
                cx += w.x; cy += w.y; cz += w.z; m += 1
            ref_pt = Vector((cx / m, cy / m, cz / m))
    elif reference == 'origin':
        ref_pt = mw.translation.copy()
    else:  # bottom-center
        mn, mx = _aabb(obj)
        ref_pt = Vector(((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, mn.z))
    tgt = Vector(target)
    delta = tgt - ref_pt
    _basis_before = obj.matrix_basis.translation.copy()
    # world-space write (code-review gate P1: per-component location adds
    # are PARENT-space — a rotated parent silently redirects the move)
    obj.matrix_world = Matrix.Translation(delta) @ obj.matrix_world
    report["applied_translation_m"] = [round(v, 5) for v in delta]
    if override == "keyframe":
        ad = getattr(obj, "animation_data", None)
        if ad is not None and ad.action is not None:
            # F5A-3: rebase by the BASIS-space delta (fcurves are basis
            # space) — move_to was the missed twin of F2B-8; under a
            # rotated parent the world delta displaced keys wrongly (the
            # R1 mug-drift class).
            d_local = obj.matrix_basis.translation - _basis_before
            n, chans = _rebase_location_keys(obj, d_local)
            report["keyframes_rebased"] = n
            report["rebased_channels"] = chans
        else:
            f = bpy.context.scene.frame_current
            for i in range(3):
                obj.keyframe_insert(data_path="location", index=i, frame=f)
            report["keyframe_inserted"] = True
            report["keyframed_channels"] = ["location[x]", "location[y]",
                                            "location[z]"]
    bpy.context.view_layer.update()
    post = _aabb(obj)
    report["post_bbox_min_m"] = [round(v, 4) for v in post[0]]
    report["post_bbox_max_m"] = [round(v, 4) for v in post[1]]
    report["ok"] = True
    report["timings_ms"] = round((time.time() - t0) * 1000, 1)
    return _maybe_write(report, output)


def snap_z(obj, target_z, *, reference='bottom', override=None, output=None):
    """Put obj's bottom (or 'origin'/'centroid') at an exact world z.

    F2B-12: AGENTS.md/PARAM_DOCS document 'centroid' but the lookup table
    only had 'center' — the documented token raised a KeyError that the
    friendly converter re-asserted ("signature: ...centroid"). 'centroid'
    now aliases 'center' (report carries the EFFECTIVE token plus the
    requested one); unknown tokens get a clean kit error listing the
    valid set."""
    if reference not in ('bottom', 'origin', 'centroid', 'center'):
        raise RuntimeError(
            f"snap_z: unknown reference {reference!r} — valid tokens: "
            f"'bottom' (default), 'origin', 'centroid' (alias 'center')")
    ref_used = 'center' if reference == 'centroid' else reference
    # F5A-1: library-level finite gate (the wave-1 audit's own named
    # example — abs(nan) < 1e-12 is False, so a NaN target_z used to
    # write a NaN location and exit 0).
    if not math.isfinite(target_z):
        raise RuntimeError(
            f"snap_z: target_z is {target_z} (not finite) — refusing to "
            f"write a non-finite location.")
    report = {"op": "snap_z", "obj": obj.name, "target_z": target_z,
              "reference": ref_used}
    if ref_used != reference:
        report["reference_requested"] = reference
    anim = _guard_anim(obj, override)
    if anim:
        report["anim_override"] = anim
    bpy.context.view_layer.update()
    mn, mx = _aabb(obj)
    cur = {"bottom": mn.z, "center": (mn.z + mx.z) / 2,
           "origin": obj.matrix_world.translation.z}[ref_used]
    _apply_translation(obj, target_z - cur, override, report)
    bpy.context.view_layer.update()
    clear_bvh_cache()
    mn2, mx2 = _aabb(obj)
    got = {"bottom": mn2.z, "center": (mn2.z + mx2.z) / 2,
           "origin": obj.matrix_world.translation.z}[ref_used]
    report["result_z"] = round(got, 6)
    return _maybe_write(report, output)


def _maybe_write(report, output):
    import json
    if output:
        import os
        os.makedirs(os.path.dirname(os.path.abspath(output)), exist_ok=True)
        with open(output, "w") as f:
            json.dump(report, f, indent=2)
    return report


# ---------------------------------------------------------------------------
# Layer 3 — verification visuals
# ---------------------------------------------------------------------------

def heat_bake(obj, others, *, yellow_mm=10.0, green_mm=50.0,
              attr_name="contact_heat"):
    """Posterized proximity heat colors on obj's vertices (Workbench
    color_type='VERTEX' renders them at previz speed).
    RED = penetrating or touching; YELLOW = < yellow_mm; GREEN = <
    green_mm; GRAY = farther. Returns band spec for the report.
    """
    bpy.context.view_layer.update()
    clear_bvh_cache()
    trees = [world_bvh(o) for o in others]
    me = obj.data
    attrs = {ca.name: ca for ca in me.color_attributes}
    if attr_name in attrs:
        me.color_attributes.remove(attrs[attr_name])
    ca = me.color_attributes.new(name=attr_name, type='FLOAT_COLOR',
                                 domain='POINT')
    n = len(me.vertices)
    try:
        import numpy as np
        verts = np.empty(n * 3, dtype=np.float32)
        me.vertices.foreach_get("co", verts)
        mw = obj.matrix_world
        verts = verts.reshape((n, 3))
        hloc = mw.to_translation()
        out = np.empty((n, 4), dtype=np.float32)
        mw3 = mw.to_3x3()
        for i in range(n):
            p = mw @ __import__("mathutils").Vector(verts[i])
            best = None
            for tr in trees:
                st, d = classify_point(tr, p)
                if st in ('inside', 'touch'):
                    best = -1.0  # red
                    break
                if d is not None:
                    best = d if best is None or d < best else best
            if best is None:
                out[i] = (0.3, 0.3, 0.3, 1.0)          # gray: far/none
            elif best < 0:
                out[i] = (1.0, 0.0, 0.0, 1.0)          # red: pen/touch
            elif best * 1000 < yellow_mm:
                out[i] = (1.0, 1.0, 0.0, 1.0)          # yellow
            elif best * 1000 < green_mm:
                out[i] = (0.0, 1.0, 0.0, 1.0)          # green
            else:
                out[i] = (0.3, 0.3, 0.3, 1.0)          # gray
        ca.data.foreach_set("color", out.ravel())
    except ImportError:
        for i, v in enumerate(me.vertices):
            p = obj.matrix_world @ v.co
            best = None
            for tr in trees:
                st, d = classify_point(tr, p)
                if st in ('inside', 'touch'):
                    best = -1.0
                    break
                if d is not None:
                    best = d if best is None or d < best else best
            if best is None:
                c = (0.3, 0.3, 0.3, 1.0)
            elif best < 0:
                c = (1.0, 0.0, 0.0, 1.0)
            elif best * 1000 < yellow_mm:
                c = (1.0, 1.0, 0.0, 1.0)
            elif best * 1000 < green_mm:
                c = (0.0, 1.0, 0.0, 1.0)
            else:
                c = (0.3, 0.3, 0.3, 1.0)
            ca.data[i].color = c
    me.update()
    return {"attr": attr_name,
            "bands": {"RED": "penetrating-or-touching",
                      "YELLOW": f"< {yellow_mm} mm",
                      "GREEN": f"< {green_mm} mm", "GRAY": "farther"}}


def seam_views(a, b, *, out_dir, res=(640, 360), engine='workbench',
               contact_band_mm=0.1, fill_frac=0.6):
    """Render the four seam-inspection views for a pair:
      macro          — persp close-up of the seam region (fills
                       `fill_frac` of the frame; raise to 0.9 for
                       sub-2mm gaps — round-2/U7: the old fixed
                       union-diagonal framing put a 1.2mm gap at ~1.3px,
                       unresolvable)
      three_quarter  — context view (both subjects identifiable)
      section_top    — INTACT ortho top-down plan of the contact,
                       seam-framed (no clip — near planes that cut an
                       object's bbox cull it whole on 5.2 workbench)
      section_side   — INTACT ortho side elevation, seam-framed (the
                       view where gap/penetration depth is visible)
    a/b: objects OR their string names (patch-op style; round-2/U7).
    Returns dict with paths + exact camera coords for re-shoots."""
    import os
    if isinstance(a, str):
        a = bpy.data.objects[a]
    if isinstance(b, str):
        b = bpy.data.objects[b]
    os.makedirs(out_dir, exist_ok=True)
    contact = pair_contact(a, b, contact_band_mm=contact_band_mm)
    cam_coords = {}

    # contact centroid + normal estimate (from worst penetration point or
    # nearest pair midpoint)
    if contact.get("penetration_points_m"):
        px, py, pz, _ = contact["penetration_points_m"][0]
        centroid = Vector((px, py, pz))
    else:
        # non-penetrating: anchor at the NEAREST-PAIR midpoint (X2 lesson:
        # bbox-union center slices mid-object, useless for CLEAR states)
        centroid = nearest_pair_midpoint(a, b) or             ((_aabb_union(a, b)[0] + _aabb_union(a, b)[1]) / 2)
    normal = Vector((0, 0, 1))
    try:
        tr_b = world_bvh(b)
        loc, nrm, idx, dist = tr_b.find_nearest(centroid)
        if nrm is not None:
            normal = Vector(nrm).normalized()
    except Exception:
        pass
    scene = bpy.context.scene
    cam_data = bpy.data.cameras.new("SeamCam")
    cam = bpy.data.objects.new("SeamCam", cam_data)
    scene.collection.objects.link(cam)
    old_cam = scene.camera
    # F2B-18: the SeamCam object+data used to leak into the scene (and
    # therefore into --save-blend's state carrier) — every seam_views call
    # left one behind, accumulating across a patch chain. Mirror the
    # section_pair discipline: remove camera+data in finally (render
    # exceptions included), keep the scene.camera restore.
    try:
        rep_views = _seam_views_shoot(a, b, out_dir=out_dir, res=res,
                                      engine=engine,
                                      contact_band_mm=contact_band_mm,
                                      fill_frac=fill_frac, contact=contact,
                                      centroid=centroid, normal=normal,
                                      cam=cam, cam_data=cam_data,
                                      cam_coords=cam_coords)
    finally:
        scene.camera = old_cam
        bpy.data.objects.remove(cam, do_unlink=True)
        bpy.data.cameras.remove(cam_data)
    return {"contact_state": contact["state"],
            "centroid": [round(v, 3) for v in centroid],
            "normal_est": [round(v, 3) for v in normal],
            "views": rep_views, "cameras": cam_coords}


def _seam_views_shoot(a, b, *, out_dir, res, engine, contact_band_mm,
                      fill_frac, contact, centroid, normal, cam, cam_data,
                      cam_coords):
    """seam_views' four renders (F2B-18 split: the caller owns camera
    lifecycle so a render exception cannot leak the temp camera)."""
    import os
    scene = bpy.context.scene

    def shoot(name, loc, target, lens=50, ortho=None, clip_start=None,
              cam_type='PERSP'):
        scene.camera = cam
        cam.location = loc
        d = (Vector(target) - Vector(loc)).normalized()
        cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
        cam_data.type = cam_type
        if ortho:
            cam_data.ortho_scale = ortho
        if clip_start is not None:
            cam_data.clip_start = clip_start
        else:
            cam_data.clip_start = 0.001
        cam_data.clip_end = 1000
        cam_data.lens = lens
        scene.render.resolution_x, scene.render.resolution_y = res
        scene.render.engine = ('BLENDER_WORKBENCH' if engine == 'workbench'
                               else scene.render.engine)
        scene.display.shading.color_type = 'MATERIAL'
        path = os.path.join(out_dir, f"seam_{name}.png")
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        cam_coords[name] = {"loc": [round(v, 3) for v in loc],
                            "target": [round(v, 3) for v in target],
                            "lens": lens, "ortho_scale": ortho,
                            "clip_start": clip_start}
        return path

    # Macro frames the SEAM REGION (smaller-object extent around the
    # contact centroid), not the whole pair — round-2/U7 lesson.
    aabb_a, aabb_b = _aabb(a), _aabb(b)
    seam_ext = max(
        min(aabb_a[1][i], aabb_b[1][i]) - max(aabb_a[0][i], aabb_b[0][i])
        for i in range(3))
    if seam_ext <= 0.0:  # non-overlapping: frame the smaller object
        ext_a = (aabb_a[1] - aabb_a[0]).length
        ext_b = (aabb_b[1] - aabb_b[0]).length
        small = aabb_a if ext_a <= ext_b else aabb_b
        seam_ext = min((small[1] - small[0]).length / 3.0, 0.2)
    import math as _math
    dist_macro = max(
        seam_ext / (2 * _math.tan(_math.radians(18)) * fill_frac), 0.12)
    paths = {}
    if abs(normal.z) > 0.7:
        # planar/horizontal contact: side profile at ~15-20 deg elevation
        az = Vector((1, 0, 0))
        loc = centroid + az * dist_macro + Vector((0, 0, dist_macro * 0.3))
        paths["macro"] = shoot("macro", loc, centroid, lens=50)
        loc_q = centroid + Vector((1, -1, 0.8)).normalized() * dist_macro * 1.4
        paths["three_quarter"] = shoot("three_quarter", loc_q, centroid,
                                       lens=35)
    else:
        side = Vector((normal.x, normal.y, 0))
        if side.length < 1e-3:
            side = Vector((1, 0, 0))
        side.normalize()
        loc = centroid + side * dist_macro
        paths["macro"] = shoot("macro", loc, centroid, lens=50)
        loc_q = centroid + (side + Vector((0, 0, 0.5))).normalized() \
            * dist_macro * 1.4
        paths["three_quarter"] = shoot("three_quarter", loc_q, centroid,
                                       lens=35)

    # section_top: INTACT plan view of the contact, seam-framed.
    # Session-4 T8: (1) seam-region scale, not the union diagonal (a 12cm
    # mug on a 2.8m table was an ~18px dot); (2) NO near-plane clip — an
    # ortho near plane intersecting an object's bbox culls the object
    # entirely on 5.2 workbench (measured), so the old 'clip just above
    # contact' slice rendered nothing. The mm truth is in the returned
    # contact_state; this view shows WHERE the contact is.
    h = 1.0
    sec_ortho = max(seam_ext * 3.0, 0.15)
    paths["section_top"] = shoot("section_top", Vector((centroid.x,
                                                        centroid.y,
                                                        centroid.z + h)),
                                 Vector((centroid.x, centroid.y,
                                         centroid.z)),
                                 ortho=sec_ortho,
                                 clip_start=0.01, cam_type='ORTHO')
    # section_side: INTACT side elevation of the seam region (no front
    # clip — same per-object near-cull). This is the view where gap/pen
    # DEPTH is visible to the eye. Camera stands OUTSIDE the union bbox
    # along `side` (session-4 QA #11: a fixed 1m standoff puts the camera
    # INSIDE a large support's bbox — its own near plane then culls the
    # support from the elevation).
    side = Vector((0, -1, 0)) if abs(normal.z) > 0.7 else \
        Vector((normal.x, normal.y, 0)).normalized()
    if side.length < 1e-3:
        side = Vector((0, -1, 0))
    umn, umx = _aabb_union(a, b)
    # distance from centroid along `side` that exits the union bbox
    d_exit = 0.0
    for i in range(3):
        if side[i] > 1e-6:
            d_exit = max(d_exit, (umx[i] - centroid[i]) / side[i])
        elif side[i] < -1e-6:
            d_exit = max(d_exit, (umn[i] - centroid[i]) / side[i])
    paths["section_side"] = shoot(
        "section_side", centroid + side * (d_exit + 0.15), centroid,
        ortho=sec_ortho, clip_start=0.01,
        cam_type='ORTHO')
    return paths


def _aabb_union(a, b):
    amn, amx = _aabb(a)
    bmn, bmx = _aabb(b)
    mn = Vector((min(amn.x, bmn.x), min(amn.y, bmn.y), min(amn.z, bmn.z)))
    mx = Vector((max(amx.x, bmx.x), max(amx.y, bmx.y), max(amx.z, bmx.z)))
    return mn, mx


# ---------------------------------------------------------------------------
# Text maps (numeric ground truth -- gates, not eyes)
# ---------------------------------------------------------------------------

_HEIGHT_CHARS = "0123456789ABCDEF"


def ascii_height_map(region=None, *, supports=None, grid=48, scene=None):
    """Top-down height map. Each cell = topmost support surface z under the
    cell center, quantized to 16 bands over the region's z range.
    '.' = void (no surface). Returns (text, legend) — legend gives the z
    range per char so a text-only agent can read absolute heights."""
    import bpy as _bpy
    scene = scene or _bpy.context.scene
    meshes = supports or [o for o in scene.objects if o.type == 'MESH']
    if not meshes:
        return "(no meshes)", ""
    mn = Vector((min(_aabb(o)[0].x for o in meshes),
                 min(_aabb(o)[0].y for o in meshes),
                 min(_aabb(o)[0].z for o in meshes)))
    mx = Vector((max(_aabb(o)[1].x for o in meshes),
                 max(_aabb(o)[1].y for o in meshes),
                 max(_aabb(o)[1].z for o in meshes)))
    if region:
        mn.x, mn.y = region[0][0], region[0][1]
        mx.x, mx.y = region[1][0], region[1][1]
    zmin, zmax = mn.z, mx.z
    if zmax - zmin < 1e-9:
        zmax = zmin + 1e-9
    rows = max(6, int(grid * 0.5))
    lines = []
    for j in range(rows):
        y = mx.y - (mx.y - mn.y) * (j + 0.5) / rows
        line = []
        for i in range(grid):
            x = mn.x + (mx.x - mn.x) * (i + 0.5) / grid
            h, _det, _nrm = support_heights(meshes, [(x, y)], from_z=mx.z + 1)
            hv = h[0]
            if hv is None:
                line.append('.')
            else:
                band = int((hv - zmin) / (zmax - zmin) * 15)
                line.append(_HEIGHT_CHARS[max(0, min(15, band))])
        lines.append("".join(line))
    legend = (f"height bands over z=[{zmin:.3f}, {zmax:.3f}] m: "
              f"'{_HEIGHT_CHARS[0]}'={zmin:.3f}m ... "
              f"'{_HEIGHT_CHARS[15]}'={zmax:.3f}m; '.'=void; "
              f"region x[{mn.x:.2f},{mx.x:.2f}] y[{mn.y:.2f},{mx.y:.2f}]")
    return "\n".join(lines), legend


def ascii_pair_map(a, b, *, grid=32):
    """Footprint occupancy map for a pair (XY overlap check):
    'A'=a only, 'B'=b only, 'X'=both, '.'=neither. Returns (text, legend)."""
    mn, mx = _aabb_union(a, b)
    amn, amx = _aabb(a)
    bmn, bmx = _aabb(b)
    rows = max(8, int(grid * 0.5))
    lines = []
    for j in range(rows):
        y = mx.y - (mx.y - mn.y) * (j + 0.5) / rows
        line = []
        for i in range(grid):
            x = mn.x + (mx.x - mn.x) * (i + 0.5) / grid
            ina = (amn.x <= x <= amx.x and amn.y <= y <= amx.y)
            inb = (bmn.x <= x <= bmx.x and bmn.y <= y <= bmx.y)
            line.append('X' if ina and inb else 'A' if ina else
                        'B' if inb else '.')
        lines.append("".join(line))
    legend = (f"A={a.name} z[{amn.z:.3f},{amx.z:.3f}]  B={b.name} "
              f"z[{bmn.z:.3f},{bmx.z:.3f}]  X=XY-overlap")
    return "\n".join(lines), legend


def heat_view(a, others, *, out_path, res=(640, 360), densify=0.03,
              yellow_mm=10.0, green_mm=50.0, azim_deg=35, elev_deg=18):
    """Non-destructive verification render: duplicate `a`, subdivide the copy
    so heat bands are crisp (sparse meshes blend), bake heat colors, render
    ISOLATED (others hidden via hide_render) in Workbench VERTEX mode, then
    remove the copy. Returns the report dict."""
    import os, math
    from mathutils import Euler
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    bpy.context.view_layer.update()
    scene = bpy.context.scene
    dup = a.copy()
    dup.data = a.data.copy()
    scene.collection.objects.link(dup)
    # hide everything else in RENDER (incl. originals of `a`)
    hidden = []
    for o in scene.objects:
        if o.type == 'MESH' and o is not dup:
            hidden.append((o, o.hide_render))
            o.hide_render = True
    # subdivide for crisp bands
    bm = bmesh.new()
    bm.from_mesh(dup.data)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=1,
                              use_grid_fill=True)
    # grid-fill can leave dense-but-uneven; a second pass by length would be
    # nicer but one cut pass on previz meshes is enough for banding
    bm.to_mesh(dup.data)
    bm.free()
    rep = heat_bake(dup, others, yellow_mm=yellow_mm, green_mm=green_mm)

    # camera framing the duplicate's bbox
    mn, mx = _aabb(dup)
    ctr = (mn + mx) / 2
    diag = (mx - mn).length
    d = max(diag * 1.1, 0.5)
    az = math.radians(azim_deg)
    el = math.radians(elev_deg)
    cam_loc = ctr + Vector((d * math.cos(el) * math.cos(az),
                            d * math.cos(el) * math.sin(az),
                            d * math.sin(el)))
    cd = bpy.data.cameras.new("HeatCam")
    cam = bpy.data.objects.new("HeatCam", cd)
    scene.collection.objects.link(cam)
    cam.location = cam_loc
    dirn = (ctr - cam_loc).normalized()
    cam.rotation_euler = dirn.to_track_quat('-Z', 'Y').to_euler()
    cd.lens = 50
    old_cam = scene.camera
    scene.camera = cam
    old_engine = scene.render.engine
    old_ct = scene.display.shading.color_type
    old_res = (scene.render.resolution_x, scene.render.resolution_y)
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.display.shading.color_type = 'VERTEX'
    scene.display.shading.light = 'FLAT'
    scene.display.shading.show_shadows = False
    scene.render.resolution_x, scene.render.resolution_y = res
    try:
        scene.view_settings.view_transform = 'Standard'
    except Exception:
        pass
    scene.render.filepath = out_path
    bpy.ops.render.render(write_still=True)
    # restore
    scene.camera = old_cam
    scene.render.engine = old_engine
    scene.display.shading.color_type = old_ct
    scene.render.resolution_x, scene.render.resolution_y = old_res
    for o, prev in hidden:
        o.hide_render = prev
    bpy.data.objects.remove(dup, do_unlink=True)
    rep["png"] = out_path
    return rep


def nearest_pair_midpoint(a, b, sample_cap=4000):
    """Midpoint of the closest vert-to-surface pair between two objects
    (None if no surface found). Robust seam anchor for non-penetrating
    pairs."""
    tr_b = world_bvh(b)
    tr_a = world_bvh(a)
    pts_a = surface_samples(a, mode='verts', cap=sample_cap)
    pts_b = surface_samples(b, mode='verts', cap=sample_cap)
    best = None
    for p, tr in ((p, tr_b) for p in pts_a):
        loc, nrm, idx, dist = tr.find_nearest(p)
        if loc is not None and (best is None or dist < best[0]):
            best = (dist, (p + loc) / 2)
    for p in pts_b:
        loc, nrm, idx, dist = tr_a.find_nearest(p)
        if loc is not None and (best is None or dist < best[0]):
            best = (dist, (p + loc) / 2)
    return best[1] if best else None


def section_pair(a, b, *, out_dir, band_mm=2.0, res=(640, 360)):
    """Seam-bracketing pair of PLAN views + exact numeric verdict.

    Session-4 T8 redesign: the original near-plane clip 'sandwich' is
    UNRENDERABLE on Blender 5.2 workbench — an ortho near plane that
    intersects an object's bbox culls the object's below-plane geometry
    ENTIRELY (measured bisection: mug visible at near-z 1.20, vanished at
    0.87 = the first plane cutting its bbox). The slices therefore render
    INTACT geometry, seam-framed:
      slice_below — B ALONE (A hidden): the bare support reference
      slice_above — A + B intact: A's footprint at the support plane
    The readable difference IS A's occupancy at the plane. The mm truth
    (penetrating / within-band / floating) stays NUMERIC below — never
    read off the images.
    a/b: objects OR their string names (round-2/U7)."""
    import os, math as _m
    if isinstance(a, str):
        a = bpy.data.objects[a]
    if isinstance(b, str):
        b = bpy.data.objects[b]
    os.makedirs(out_dir, exist_ok=True)
    scene = bpy.context.scene
    contact = pair_contact(a, b)
    seam = nearest_pair_midpoint(a, b)
    if seam is None:
        return {"error": "no surface pair found"}
    # anchor planes on B's SURFACE point (not the pair midpoint — midpoint
    # halves the measured distances, X2 lesson)
    tr_b = world_bvh(b)
    loc, nrm, idx, dist = tr_b.find_nearest(seam)
    surf = loc if loc is not None else seam
    normal = Vector(nrm).normalized() if nrm else Vector((0, 0, 1))
    off = band_mm / 1000.0

    # Frame the SEAM REGION, not the union bbox (session-4 T8: a 12cm mug
    # on a 2.8m table rendered as an ~18px disc — the diagnostic showed a
    # featureless table corner). Scale = the bbox-intersection extent (the
    # seam neighborhood), floored to a sane minimum.
    aabb_a, aabb_b = _aabb(a), _aabb(b)
    seam_ext = max(
        min(aabb_a[1][i], aabb_b[1][i]) - max(aabb_a[0][i], aabb_b[0][i])
        for i in range(3))
    if seam_ext <= 0.0:
        ext_a = (aabb_a[1] - aabb_a[0]).length
        ext_b = (aabb_b[1] - aabb_b[0]).length
        small = aabb_a if ext_a <= ext_b else aabb_b
        seam_ext = min((small[1] - small[0]).length / 3.0, 0.2)
    ortho = max(seam_ext * 3.0, 0.15)

    hide_a = a.hide_render

    def _slice(tag, hide_a_):
        a.hide_render = hide_a_
        cam_d = bpy.data.cameras.new(f"SliceCam_{tag}")
        cam = bpy.data.objects.new(f"SliceCam_{tag}", cam_d)
        scene.collection.objects.link(cam)
        cam_d.type = 'ORTHO'
        cam_d.ortho_scale = ortho
        h = 1.0
        cam.location = surf + normal * h
        dirv = -normal
        cam.rotation_euler = dirv.to_track_quat('-Z', 'Y').to_euler()
        cam_d.clip_start = 0.01   # nothing clipped — intact plan view
        cam_d.clip_end = h + 50
        old_cam = scene.camera
        scene.camera = cam
        old_engine = scene.render.engine
        old_res = (scene.render.resolution_x, scene.render.resolution_y)
        scene.render.engine = 'BLENDER_WORKBENCH'
        scene.display.shading.color_type = 'MATERIAL'
        scene.display.shading.light = 'FLAT'
        scene.render.resolution_x, scene.render.resolution_y = res
        path = os.path.join(out_dir, f"slice_{tag}.png")
        scene.render.filepath = path
        try:
            bpy.ops.render.render(write_still=True)
        finally:
            # session-4 QA (#10): a render exception must not leave A
            # hidden / the temp camera leaked — a later look in the same
            # process would silently show a false-CLEAR scene.
            scene.camera = old_cam
            scene.render.engine = old_engine
            scene.render.resolution_x, scene.render.resolution_y = old_res
            a.hide_render = hide_a
            bpy.data.objects.remove(cam, do_unlink=True)
            bpy.data.cameras.remove(cam_d)
        return path

    p_below = _slice("below", True)    # A hidden: bare support reference
    p_above = _slice("above", False)   # intact: A's footprint at the plane

    # A's lowest extent along the support normal, relative to the seam:
    #   bottom < -off  -> penetrates more than band below the surface
    #   |bottom| <= off -> within band (touching / shallow)
    #   bottom > +off  -> floating more than band above
    pts = surface_samples(a, mode='verts', cap=2000)
    bottom = min((p - surf).dot(normal) for p in pts)
    if bottom < -off:
        verdict = (f"PENETRATING: A extends {abs(bottom) * 1000:.1f} mm "
                   f"below the support surface (> {band_mm} mm band)")
    elif bottom <= off:
        verdict = (f"WITHIN BAND: A's lowest point is {bottom * 1000:.1f} mm "
                   f"from the surface (touching or shallow, "
                   f"band {band_mm} mm)")
    else:
        verdict = (f"CLEAR: A floats {bottom * 1000:.1f} mm above the "
                   f"surface (> {band_mm} mm band)")
    return {"verdict": verdict, "truth_state": contact["state"],
            "slices": {"below": p_below, "above": p_above},
            "seam": [round(v, 4) for v in seam],
            "ortho_scale_m": round(ortho, 3),
            "band_mm": band_mm}
