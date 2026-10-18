"""wrapper_rig.py — the F-RH3 wrapper-empty facing law, generalized.

Implements D1 of docs/DESIGN_s21_hero_lane.md (REV-2) for ANY imported
animated armature (RH x_bot / UAL / Quaternius / future). The wrapper
EMPTY is the clobber-proof surface (s20 F-RH3: manual yaw on the
wrapper survives frame_set; object-level rotation keys on the
armature can NOT clobber it — and in the humanoid-crowd architecture
the keys land on the GRANDPARENT anchor, one step safer still).

API:
    wrap(arm, name, scale=1.0, facing_probe_bone=None) -> rep
    rep = {"root", "armature", "meshes", "facing_sign", "scale",
           "probe_bone", "probe_axis", "fwd"}

Laws (each from the audited pattern; review r1 findings folded):
  1. Wrapper EMPTY named exactly `<name>.Root`, fresh, identity basis.
  2. Facing probe at bind on the AS-IMPORTED armature, BEFORE any
     transform is authored. Candidates are ±Y ONLY (a foot bone's
     local Z is the roll axis — also horizontal; a horizontalness
     contest across axes is silently won by a meaningless axis).
     The winner must be BOTH near-horizontal (|fwd.z| <= 0.5) AND
     Y-dominant (|fwd.y| >= 0.5); auto-pick skips `*_end` leaves.
     REFUSE fail-closed with the measured value otherwise.
  3. Parenting is DIRECT ASSIGNMENT ONLY (review r1 T8/T9: the
     parent_set operator adopts the whole SELECTION — a bystander
     hazard — and contributes nothing the direct law doesn't):
         arm.parent = root
         arm.matrix_parent_inverse = flip @ Scale(scale)
     flip (Rz(pi)) only when the probe faces -Y. Scale NEVER keyed.
     Composition law: world = root @ MPI @ arm_basis (mpi_semantics_probe).
  4. The armature MUST already be linked into the scene (review r1
     T4: select/eval on an unlinked object raises; an orphan rig
     would also never export). Refuse loudly when unlinked.
  5. Refusals (RuntimeError, fail-closed, BEFORE any mutation):
     non-ARMATURE arg; unlinked armature; armature already parented;
     `<name>.Root` name collision; scale != 1.0 with a skinned mesh
     NOT parented to the armature (D1b: rest/posed skins diverge).
  6. The report carries facing_sign + probe bone + the measured
     world forward (auditable — the s20 lesson: numbers travel).
  7. The helper NEVER touches animation data (no action clearing —
     that is a per-loader policy).
"""
import bpy
from mathutils import Matrix, Vector


def _fail(msg):
    raise RuntimeError(f"wrapper_rig: {msg}")


def _probe_forward(arm, bone_name):
    """World-space +Y of the pose bone, as a unit vector."""
    pb = arm.pose.bones.get(bone_name)
    if pb is None:
        _fail(f"probe bone {bone_name!r} not in {arm.name}")
    M = arm.matrix_world @ pb.matrix
    return (M.to_3x3() @ Vector((0.0, 1.0, 0.0))).normalized()


def facing_probe(arm, explicit=None):
    """The facing law: pick the probe bone, contest +Y vs -Y, refuse
    if neither candidate is both horizontal and Y-dominant.

    Order: the explicit bone first; on its failure the auto-scan (all
    foot/toe-named bones x +-Y) still runs before any refusal (the
    x_bot law: its LeftFoot's +Y points down-back — the TOE bones
    carry the horizontal toe direction; a failed explicit must not
    mask a working auto-pick).

    Returns (bone_name, axis_sign, fwd) — axis_sign +1 when the bone's
    local +Y is the toe direction, -1 when -Y is.
    """
    if explicit:
        fwd = _probe_forward(arm, explicit)
        if abs(fwd.z) <= 0.5 and abs(fwd.y) >= 0.5:
            return explicit, (1 if fwd.y >= 0 else -1), fwd
        print(f"wrapper_rig: explicit probe {explicit!r} failed the "
              f"contest (fwd {tuple(round(v, 3) for v in fwd)}) — "
              f"falling through to the auto-scan")
    # auto-pick: foot/toe-named pose bones, skipping *_end leaves
    cands = [b.name for b in arm.pose.bones
             if ("foot" in b.name.lower() or "toe" in b.name.lower())
             and not b.name.lower().endswith("_end")]
    if not cands:
        _fail(f"no foot-like probe bone on {arm.name} (pass explicit=)")
    for nm in cands:
        for sign in (1.0, -1.0):
            pb = arm.pose.bones[nm]
            M = arm.matrix_world @ pb.matrix
            fwd = (M.to_3x3() @ Vector((0.0, sign, 0.0))).normalized()
            if abs(fwd.z) <= 0.5 and abs(fwd.y) >= 0.5:
                return nm, int(sign), fwd
    fwd = _probe_forward(arm, cands[0])
    _fail(f"facing probe refused: {arm.name} foot bone {cands[0]!r} "
          f"forward {tuple(round(v, 3) for v in fwd)} is neither "
          f"horizontal (|z|<=0.5) nor Y-dominant (|y|>=0.5) on either "
          f"+Y or -Y — a rig we do not understand; pass explicit=")


def wrap(arm, name, scale=1.0, facing_probe_bone=None):
    """Wrap an imported armature per the D1 law. Returns the rep dict.

    The armature must ALREADY be linked into the scene (law 4). Skinned
    meshes are discovered by their Armature modifier/find_armature
    pointing at `arm`; at scale != 1.0 any skinned mesh not parented to
    the armature is a refusal (the check runs BEFORE any mutation).
    """
    if not isinstance(arm, bpy.types.Object) or arm.type != 'ARMATURE':
        _fail(f"wrap() needs an ARMATURE object, got {type(arm)}")
    root_name = f"{name}.Root"
    if root_name in bpy.data.objects:
        _fail(f"name collision: {root_name!r} already exists "
              f"(naming is the caller's hygiene)")
    if arm.parent is not None:
        _fail(f"{arm.name} is already parented to {arm.parent.name} — "
              f"the caller decides ordering; refusing to re-parent")
    # hero-lane battery catch (s22 cross-lane fold): the master
    # collection's OWN objects were missed — children_recursive covers
    # child collections only, so an FBX import linked at the scene
    # root false-refused (tests/test_hero_lane.py H1).
    coll = bpy.context.scene.collection
    in_scene = (arm.name in coll.objects
                or any(arm.name in c.objects
                       for c in getattr(coll, "children_recursive", [])))
    if not in_scene:
        _fail(f"{arm.name} is not linked into the scene collection — "
              f"link it first (review r1 T4: an orphan rig never "
              f"exports and cannot be evaluated)")

    # skinned meshes + the D1b scale law, BEFORE any mutation (r1 P2-12)
    meshes = [ob for ob in bpy.data.objects
              if ob.type == 'MESH' and ob.find_armature() is arm]
    if scale != 1.0:
        for ob in meshes:
            if ob.parent is not arm:
                _fail(f"skinned mesh {ob.name} is not parented to the "
                      f"armature at scale != 1.0 — rest/posed skins "
                      f"would diverge (D1b law); refusing")

    bone, axis_sign, fwd = facing_probe(arm, facing_probe_bone)

    root = bpy.data.objects.new(root_name, None)
    bpy.context.scene.collection.objects.link(root)
    # DIRECT assignment law (r1 T9) — no parent_set ops (r1 T8 hazard)
    arm.parent = root
    flip = Matrix.Rotation(3.14159265358979, 4, 'Z') if axis_sign < 0 \
        else Matrix.Identity(4)
    arm.matrix_parent_inverse = flip @ Matrix.Scale(scale, 4)

    bpy.context.view_layer.update()
    return {"root": root, "armature": arm, "meshes": meshes,
            "facing_sign": axis_sign, "scale": scale,
            "probe_bone": bone, "probe_axis": axis_sign, "fwd": fwd}
