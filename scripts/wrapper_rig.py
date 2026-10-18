"""wrapper_rig.py — the F-RH3 wrapper-empty facing law, generalized.

Implements D1 of docs/DESIGN_s21_hero_lane.md (REV-2) for ANY imported
animated armature (RH x_bot / UAL / Quaternius / future). The wrapper
EMPTY is the clobber-proof surface (s20 F-RH3: manual yaw on the
wrapper survives frame_set; object-level rotation keys on the
armature can NOT clobber it — and in the humanoid-crowd architecture
the keys land on the GRANDPARENT anchor, one step safer still).

API:
    wrap(arm, name, scale=1.0, mesh=None, facing_probe=None) -> rep
    rep = {"root", "armature", "mesh", "facing_sign", "scale",
           "probe_bone", "probe_axis", "fwd"}

Laws (each from the audited pattern):
  1. Wrapper EMPTY named exactly `<name>.Root`, fresh, identity basis.
  2. Facing probe at bind on the AS-IMPORTED armature, BEFORE any
     transform is authored. Candidates are ±Y ONLY (a foot bone's
     local Z is the roll axis — also horizontal; a horizontalness
     contest across axes is silently won by a meaningless axis).
     The winner must be BOTH near-horizontal (|fwd.z| <= 0.5) AND
     Y-dominant (|fwd.y| >= 0.5); auto-pick skips `*_end` leaves.
     REFUSE fail-closed with the measured value otherwise.
  3. arm.matrix_parent_inverse = flip @ Scale(scale) — flip (Rz(pi))
     only when the probe faces -Y. Scale NEVER keyed.
  4. Skinned mesh (arg or auto-found via find_armature()): parented
     to the ARMATURE when scale == 1.0 and it is already parented
     there; when scale != 1.0 the mesh MUST end up under the
     armature's transform chain (D1b/D2a: a wrapper-parented mesh at
     scale != 1.0 strands the rest pose) — this helper REQUIRES the
     mesh to already ride the armature and refuses otherwise, so the
     rest/posed skins can never diverge.
  5. Refusals (RuntimeError, fail-closed): non-ARMATURE arg; armature
     already parented (caller decides ordering); `<name>.Root` name
     collision; no usable foot-like probe bone.
  6. The report carries facing_sign + probe bone + winning axis + the
     measured world forward (auditable — the s20 lesson: numbers
     travel).
  7. The helper NEVER touches animation data (no action clearing —
     that is a per-loader policy).

The world = parent @ MPI @ basis composition law is probed at
mpi_semantics_probe.py (Blender 4.5/5.2).
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

    Returns (bone_name, axis_sign, fwd) where axis_sign is +1 when the
    bone's local +Y is the toe direction, -1 when -Y is.
    """
    if explicit:
        fwd = _probe_forward(arm, explicit)
        if abs(fwd.z) <= 0.5 and abs(fwd.y) >= 0.5:
            return explicit, (1 if fwd.y >= 0 else -1), fwd
        _fail(f"explicit probe {explicit!r} failed the horizontal+"
              f"Y-dominant contest (measured fwd {tuple(round(v, 3) for v in fwd)})")
    # auto-pick: first pose bone whose lowercase name contains "foot",
    # skipping *_end leaves (the 42-bone census provably carries
    # Foot.L_end leaves — a leaf's +Y points OUT of the toe, not along
    # it, and its roll axis is meaningless).
    cands = [b.name for b in arm.pose.bones
             if "foot" in b.name.lower() and not b.name.lower().endswith("_end")]
    if not cands:
        _fail(f"no foot-like probe bone on {arm.name} (pass facing_probe=)")
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
          f"+Y or -Y — a rig we do not understand; pass facing_probe=")


def wrap(arm, name, scale=1.0, mesh=None, facing_probe_bone=None):
    """Wrap an imported armature per the D1 law. Returns the rep dict."""
    if not isinstance(arm, bpy.types.Object) or arm.type != 'ARMATURE':
        _fail(f"wrap() needs an ARMATURE object, got {type(arm)}")
    if arm.parent is not None:
        _fail(f"{arm.name} is already parented to {arm.parent.name} — "
              f"the caller decides ordering; refusing to re-parent")
    root_name = f"{name}.Root"
    if root_name in bpy.data.objects:
        _fail(f"name collision: {root_name!r} already exists "
              f"(naming is the caller's hygiene)")
    bone, axis_sign, fwd = facing_probe(arm, facing_probe_bone)

    root = bpy.data.objects.new(root_name, None)
    bpy.context.scene.collection.objects.link(root)
    view_layer = bpy.context.view_layer
    view_layer.objects.active = root
    arm.select_set(True)
    root.select_set(True)
    bpy.ops.object.parent_set(type='OBJECT', keep_transform=False)
    arm.parent = root
    flip = Matrix.Rotation(3.14159265358979, 4, 'Z') if axis_sign < 0 \
        else Matrix.Identity(4)
    arm.matrix_parent_inverse = flip @ Matrix.Scale(scale, 4)

    # the skinned mesh: must already ride the armature (law 4)
    if mesh is None:
        mesh = arm.find_armature()  # no-op; meshes point AT the armature
    meshes = []
    for ob in bpy.data.objects:
        if ob.type == 'MESH' and ob.find_armature() is arm:
            meshes.append(ob)
            if scale != 1.0 and ob.parent is not arm:
                _fail(f"skinned mesh {ob.name} is not parented to the "
                      f"armature at scale != 1.0 — rest/posed skins "
                      f"would diverge (D1b law); refusing")
    view_layer.update()
    return {"root": root, "armature": arm, "mesh": meshes[0] if meshes else None,
            "facing_sign": axis_sign, "scale": scale,
            "probe_bone": bone, "probe_axis": axis_sign, "fwd": fwd}
