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
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from mathutils.geometry import intersect_ray_tri

# 5.x compat: action.fcurves moved to channelbag API. Local fallback so this
# module still imports when scripts/ isn't on PYTHONPATH (audit_contacts.py
# pattern). See blender_kit/__init__.py:iter_fcurves for the source of truth.
try:
    from blender_kit import iter_fcurves
except ImportError:
    def iter_fcurves(action):
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
    """Drop all cached BVH trees. Called automatically after open_mainfile
    by the patch ops; call manually after bulk geometry edits."""
    _BVH_CACHE.clear()


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


def _skinned_guard(obj, force):
    """Refuse confident nonsense on posed/animated rigged meshes (kit
    gotcha #27: evaluated mesh can return bind pose while the render shows
    the posed figure). Armature WITHOUT animation = rest pose = safe."""
    if obj.type != 'MESH':
        return None
    has_arm = any(m.type == 'ARMATURE' for m in obj.modifiers) or \
        (obj.parent is not None and obj.parent.type == 'ARMATURE') or \
        obj.find_armature() is not None
    if not has_arm:
        return None
    ad = getattr(obj, "animation_data", None)
    animated = bool(ad and (ad.action or
                            any(tr.strips for tr in ad.nla_tracks)))
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
    failed = any(r.get("state") == "PENETRATING" and
                 (r.get("penetration_mm") is None or
                  r["penetration_mm"] > contact_band_mm)
                 for r in reports)
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

def _location_anim_channels(obj):
    """Location fcurves/drivers that would clobber placement writes
    (review blocker #4)."""
    chans = []
    ad = getattr(obj, "animation_data", None)
    if not ad:
        return chans
    if ad.action:
        for fc in iter_fcurves(ad.action):
            if fc.data_path == "location":
                chans.append(f"action:location[{fc.array_index}]")
    for tr in getattr(ad, "nla_tracks", []):
        for st in tr.strips:
            act = getattr(st, "action", None)
            if act:
                for fc in iter_fcurves(act):
                    if fc.data_path == "location":
                        chans.append(f"nla:{act.name}:location[{fc.array_index}]")
    for dc in getattr(ad, "drivers", []):
        if dc.data_path == "location":
            chans.append(f"driver:location[{dc.array_index}]")
    return chans


def _guard_anim(obj, override):
    chans = _location_anim_channels(obj)
    if not chans:
        return None
    if override is None:
        raise RuntimeError(
            f"'{obj.name}' has location animation ({', '.join(chans[:4])}). "
            f"Placement writes would be clobbered at the next frame_set/"
            f"render. Run placement BEFORE animate(); or pass "
            f"override='keyframe' (insert a visible key at the current "
            f"frame) or override='ignore' (at your own risk).")
    return chans


def _apply_translation(obj, dz, override, report):
    if abs(dz) < 1e-12:
        return
    obj.location.z += dz
    report["applied_dz_m"] = round(dz, 6)
    if override == "keyframe":
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
                "object has NLA strips — keyframe_insert writes the active "
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
    """One-shot 'object rests on support surface' solver.

    Single-contact-plane solver (design review #1): all footprint points
    land on ONE solved plane z* + clearance. If the footprint spans
    multi-level support (butt on cushion + feet on floor), the report sets
    multi_level=true with the height distribution — use seat_at for rigs.

    mode: 'rest' (max support under footprint — stand ON), 'sink' (min —
    wells/insets; audit will report intended penetration), 'p25'/'p50'/'p75'.
    footprint: 'bottom' (downward-facing verts, w/ fallback), 'all', 'grid'.
    inset: shrink footprint to points >= inset meters inside its own bbox
    (seat lips/edges).
    keep_xy: True (default) — solves Z ONLY, object stays at its current
    x/y. To land on a DIFFERENT support, move the object over it first
    (set_location) or pass keep_xy=False to also move to the support
    height-field's centroid (usually wrong for scenes with several
    supports — prefer set_location first; usability round-1/U2).
    override: None | 'keyframe' | 'ignore' (see _guard_anim).
    Returns placement report (JSON-safe) with post-solve contact audit
    against every support."""
    t0 = time.time()
    report = {"op": "place_on", "obj": obj.name,
              "supports": [s.name for s in supports],
              "clearance_m": clearance, "footprint": footprint,
              "mode": mode, "keep_xy": keep_xy,
              "contact_band_mm": contact_band_mm}
    _skinned_guard(obj, force)
    for s in supports:
        _skinned_guard(s, force)
    _origin_centroid_warn(obj, report)
    anim = _guard_anim(obj, override)
    if anim:
        report["anim_override"] = anim
    bpy.context.view_layer.update()
    clear_bvh_cache()

    # --- footprint points -------------------------------------------------
    if footprint == 'grid':
        (mn, mx) = _aabb(obj)
        pts_xy = []
        for i in range(grid_n):
            for j in range(grid_n):
                fx = mn.x + (mx.x - mn.x) * (i + 0.5) / grid_n
                fy = mn.y + (mx.y - mn.y) * (j + 0.5) / grid_n
                pts_xy.append((fx, fy))
        z_ref = mn.z
        footprint_pts = []
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
        report["footprint_fallback"] = footprint == 'bottom' and any(
            world_normal(obj, v.normal).z >= -0.3 for v in
            obj.data.vertices) is False
        pts_xy = [(p.x, p.y) for p in pts]
        z_ref = min(p.z for p in pts)
        footprint_pts = pts

    # --- height field + solve ---------------------------------------------
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
            f"footprint='grid' which samples the whole bbox footprint.")

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
            obj.matrix_world = (Matrix.Translation(pivot) @ R @
                                Matrix.Translation(-pivot) @
                                obj.matrix_world)
            report["aligned_to_surface"] = True
            report["aligned_rotation_q"] = [round(v, 5) for v in q]
            bpy.context.view_layer.update()
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
                         "error": repr(e)})
    report["post_contact"] = post
    report["ok"] = all(p.get("severity") != "fail" for p in post)
    report["timings_ms"] = round((time.time() - t0) * 1000, 1)
    return _maybe_write(report, output)


def seat_at(obj, seat_empty, *, reference='bottom', offset=None, align=True,
            override=None, seat_mesh=None, contact_band_mm=0.1, output=None):
    """CAD-mate style seating: place obj relative to a named anchor empty
    (kit convention e.g. 'Jeep.SeatL'; figure faces the empty's +Y, sits
    along -Y, empty +Z is up).

    reference: 'bottom' — obj's bbox bottom-CENTER lands at the anchor
    (plus offset); 'origin' — obj's origin lands at the anchor.
    offset: (dx, dy, dz) interpreted in the EMPTY's local space.
    seat_mesh: optional mesh object to post-audit against (e.g. cushion).
    Returns placement report with post_contact when seat_mesh given."""
    t0 = time.time()
    report = {"op": "seat_at", "obj": obj.name, "seat": seat_empty.name,
              "reference": reference}
    _origin_centroid_warn(obj, report)
    anim = _guard_anim(obj, override)
    if anim:
        report["anim_override"] = anim
    bpy.context.view_layer.update()
    clear_bvh_cache()

    pre_bbox = _aabb(obj)
    report["pre_bbox_min_m"] = [round(v, 4) for v in pre_bbox[0]]
    report["pre_bbox_max_m"] = [round(v, 4) for v in pre_bbox[1]]

    seat_mw = seat_empty.matrix_world.copy()
    target_loc = seat_mw.translation.copy()
    if align:
        obj.rotation_euler = seat_mw.to_euler()
        bpy.context.view_layer.update()
    if offset:
        target_loc = seat_mw @ Vector(offset)
    if reference == 'bottom':
        mn, mx = _aabb(obj)
        anchor_obj = Vector(((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, mn.z))
        delta = target_loc - anchor_obj
        obj.location.x += delta.x
        obj.location.y += delta.y
        obj.location.z += delta.z
    else:
        delta = target_loc - obj.matrix_world.translation
        obj.location += delta
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
        obj.keyframe_insert(data_path="location",
                            frame=bpy.context.scene.frame_current)
        report["keyframe_inserted"] = True
    bpy.context.view_layer.update()
    clear_bvh_cache()
    if seat_mesh is not None:
        report["post_contact"] = pair_contact(obj, seat_mesh,
                                              contact_band_mm=contact_band_mm)
        report["ok"] = report["post_contact"].get("severity") != "fail"
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
    vs = obj.data.vertices
    if reference == 'centroid':
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
    # world-space write (code-review gate P1: per-component location adds
    # are PARENT-space — a rotated parent silently redirects the move)
    obj.matrix_world = Matrix.Translation(delta) @ obj.matrix_world
    report["applied_translation_m"] = [round(v, 5) for v in delta]
    if override == "keyframe":
        f = bpy.context.scene.frame_current
        for i in range(3):
            obj.keyframe_insert(data_path="location", index=i, frame=f)
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
    """Put obj's bottom (or 'origin'/'center') at an exact world z."""
    report = {"op": "snap_z", "obj": obj.name, "target_z": target_z,
              "reference": reference}
    anim = _guard_anim(obj, override)
    if anim:
        report["anim_override"] = anim
    bpy.context.view_layer.update()
    mn, mx = _aabb(obj)
    cur = {"bottom": mn.z, "center": (mn.z + mx.z) / 2,
           "origin": obj.matrix_world.translation.z}[reference]
    _apply_translation(obj, target_z - cur, override, report)
    bpy.context.view_layer.update()
    clear_bvh_cache()
    mn2, mx2 = _aabb(obj)
    got = {"bottom": mn2.z, "center": (mn2.z + mx2.z) / 2,
           "origin": obj.matrix_world.translation.z}[reference]
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
      section_top    — ortho top-down, clip plane just above contact z
                       (interference outline slice)
      section_side   — ortho side, clip plane through contact centroid
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
    diag = (_aabb_union(a, b)[1] - _aabb_union(a, b)[0]).length

    scene = bpy.context.scene
    cam_data = bpy.data.cameras.new("SeamCam")
    cam = bpy.data.objects.new("SeamCam", cam_data)
    scene.collection.objects.link(cam)
    old_cam = scene.camera

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

    # section_top: ortho down, clip just above contact z
    top_z = centroid.z + max(0.002, contact_band_mm / 1000.0 * 2)
    h = 5.0
    paths["section_top"] = shoot("section_top", Vector((centroid.x,
                                                        centroid.y, top_z + h)),
                                 Vector((centroid.x, centroid.y, top_z)),
                                 ortho=max(diag * 1.2, 0.3),
                                 clip_start=h, cam_type='ORTHO')
    # section_side: ortho horizontal, clip through centroid depth
    side = Vector((0, -1, 0)) if abs(normal.z) > 0.7 else \
        Vector((normal.x, normal.y, 0)).normalized()
    if side.length < 1e-3:
        side = Vector((0, -1, 0))
    d_to_centroid = (centroid - (centroid + side * 5)).length
    paths["section_side"] = shoot(
        "section_side", centroid + side * 5.0, centroid,
        ortho=max(diag * 1.2, 0.3), clip_start=d_to_centroid,
        cam_type='ORTHO')

    scene.camera = old_cam
    return {"contact_state": contact["state"],
            "centroid": [round(v, 3) for v in centroid],
            "normal_est": [round(v, 3) for v in normal],
            "views": paths, "cameras": cam_coords}


def _aabb_union(a, b):
    amn, amx = _aabb(a)
    bmn, bmx = _aabb(b)
    mn = Vector((min(amn.x, bmn.x), min(amn.y, bmn.y), min(amn.z, bmn.z)))
    mx = Vector((max(amx.x, bmx.x), max(amx.y, bmx.y), max(amx.z, bmx.z)))
    return mn, mx


# ---------------------------------------------------------------------------
# ASCII maps (VLM-blind workflow)
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
    """The two-slice 'sandwich' that visually brackets contact within
    band_mm: slice BELOW the support top (presence there = penetrating
    beyond band) and slice ABOVE it (presence = object's lowest point below
    the plane). Decides: penetrating>band / within-band-or-touching /
    floating>band. Returns verdict + paths (X2 lesson: a single slice
    cannot separate touching from shallow penetration).
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

    def _slice(tag, plane_pt):
        cam_d = bpy.data.cameras.new(f"SliceCam_{tag}")
        cam = bpy.data.objects.new(f"SliceCam_{tag}", cam_d)
        scene.collection.objects.link(cam)
        cam_d.type = 'ORTHO'
        diag = (_aabb_union(a, b)[1] - _aabb_union(a, b)[0]).length
        cam_d.ortho_scale = max(diag * 1.3, 0.25)
        h = 4.0
        cam.location = plane_pt + normal * h
        dirv = -normal
        cam.rotation_euler = dirv.to_track_quat('-Z', 'Y').to_euler()
        cam_d.clip_start = h          # near plane exactly at the slice
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
        bpy.ops.render.render(write_still=True)
        scene.camera = old_cam
        scene.render.engine = old_engine
        scene.render.resolution_x, scene.render.resolution_y = old_res
        bpy.data.objects.remove(cam, do_unlink=True)
        bpy.data.cameras.remove(cam_d)
        return path

    p_below = _slice("below", seam - normal * off)
    p_above = _slice("above", seam + normal * off)

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
            "band_mm": band_mm}
