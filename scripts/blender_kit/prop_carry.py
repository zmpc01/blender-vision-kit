"""Generalized prop anchoring & carry — blender_kit (kit law 110).

THE BUG CLASS THIS MODULE KILLS: PHANTOM OFFSETS. A prop's
parent-space anchor (matrix_parent_inverse, or a carry-local matrix)
captured while the scene is parked at a DIFFERENT frame than the
world placement it anchors. Session-26: the rifle's carry_local was
read at f10 while pos_c was f1-based — the 1.88 m sprint delta rode
every carry key and the gun floated ~2 m behind the gunner for 156
frames while ALL 13 existing export gates stayed green (the aim
placement and the wrapper riding were each individually correct).

LAWS ENFORCED HERE:
- LIVE-READ (session-18): every matrix read happens after
  scene.frame_set(f) + view_layer.update() x2.
- SAME-FRAME (session-26): anchor captures assert the scene's current
  frame matches the requested one; capture helpers return SNAPSHOT
  copies so later frame_sets cannot poison them.
- FULL-TIMELINE (law 106): held-state prop actions get a terminal key
  at the scene end.
- SANITY RADIUS (session-26): post-key verification — the prop's
  composed world must stay within max_dist of at least one anchor at
  EVERY keyed frame. Catches ANY phantom/drift class, known or novel.

Scene-side usage (assets_rifle_v5 is the reference client):
    W1 = capture_anchor(wrap, scene, 1)          # SAME-FRAME snapshot
    carry_local = W1.inverted() @ desired_basis  # frame-state FREE
    issues = carry_keys(rifle, scene,
                        frames=range(1, CARRY_END + 1),
                        desired_world=lambda: wrap.matrix_world @ carry_local,
                        blend_from=CARRY_BLEND, blend_to=CARRY_END + 1,
                        end_frame=TOTAL_FRAMES)
    issues += verify_riding(rifle, scene,
                            anchors=(wrap, hand_bone_read),
                            frames=carry_window, max_dist=1.25)
Exporter-side, gate 14 enforces the same contract on the GLB
(prop min-distance to its owning skin's joints; see
export_previz_package._glb_prop_proximity_audit).
"""
from __future__ import annotations

import math
from mathutils import Matrix

# identity shorthand
_IDENTITY = Matrix()


# ---------------------------------------------------------------------------
# LIVE-READ + SAME-FRAME primitives
# ---------------------------------------------------------------------------

def live_update(scene, updates: int = 2) -> None:
    """The stale-read law: frame_set + N view-layer updates before ANY
    matrix read (N=2 empirically required; 1 leaves stale bones)."""
    import bpy
    for _ in range(max(1, updates)):
        bpy.context.view_layer.update()


def live_world(obj, scene, frame=None, *, updates: int = 2):
    """LIVE-READ world matrix of obj (optionally frame_set first).
    Returns a SNAPSHOT copy — later frame changes cannot poison it."""
    if frame is not None:
        scene.frame_set(frame)
    live_update(scene, updates)
    return obj.matrix_world.copy()


def capture_anchor(anchor_obj, scene, frame, *, updates: int = 2):
    """SAME-FRAME anchor capture: park the scene at `frame`, verify the
    park actually took (kills the parked-at-the-wrong-frame class),
    then snapshot the anchor's world matrix."""
    scene.frame_set(frame)
    if scene.frame_current != frame:
        raise RuntimeError(
            f"capture_anchor: scene.frame_set({frame}) left frame at "
            f"{scene.frame_current} — anchor reads are unreliable")
    live_update(scene, updates)
    return anchor_obj.matrix_world.copy()


def anchor_local(anchor_snapshot, world_placement):
    """Pure math: world placement -> anchor-local, from a SNAPSHOT
    (never a live matrix — live reads make this function frame-state
    dependent, the exact bug this module exists to prevent)."""
    return anchor_snapshot.inverted() @ world_placement


# ---------------------------------------------------------------------------
# Generalized clamped carry
# ---------------------------------------------------------------------------

def carry_keys(prop, scene, *, frames, desired_world, blend_from,
               blend_to, end_frame, updates: int = 2, log=None):
    """Torso-stable clamped carry, generalized (no scene specifics).

    Contract:
    - desired_world() -> Matrix: called with the scene ALREADY parked
      at each key frame (LIVE-READ); returns the desired WORLD
      transform of the prop at that frame (e.g. wrapper @ carry_local).
    - The prop must be parented (any parent type) with its
      post-parenting basis == identity at call time; W0(f) (the world
      read with basis == I) is sampled per frame BEFORE any key exists.
    - basis(f) = W0(f)^-1 @ desired(f); over [blend_from, blend_to]
      desired lerps toward W0(f) so basis -> identity exactly at
      blend_to (the hand CATCHES the prop — a visible draw).
    - Terminal identity key at end_frame (law 106: held-state actions
      must span the full timeline or range-gated consumers read the
      node's base TRS = the carry offset).
    - All keys LINEAR (carry counter-animation must not ease).

    Returns issues (empty = clean; NON-empty = fail-closed upstream).
    """
    issues = []
    import bpy  # noqa: F401  (keyframe_insert is on the RNA object)
    frames = list(frames)
    if not frames:
        return ["carry_keys: empty frame window"]
    if not (frames[0] <= blend_from <= blend_to):
        return [f"carry_keys: blend window [{blend_from},{blend_to}] "
                f"outside frame window [{frames[0]},{frames[-1]}]"]

    # pass 1: W0 reads (basis == I, no keys yet)
    W0 = {}
    for f in frames:
        scene.frame_set(f)
        live_update(scene, updates)
        W0[f] = prop.matrix_world.copy()

    # pass 2: compose + key (frames, then blend_to with exact identity
    # if it is not already the last frame — the catch frame MUST be
    # keyed even when it lies outside the caller's frame window)
    span = float(blend_to - blend_from)
    keyed = list(frames)
    if keyed[-1] < blend_to:
        keyed.append(blend_to)
    for f in keyed:
        scene.frame_set(f)
        live_update(scene, updates)
        if f == blend_to and f not in frames:
            prop.matrix_basis = _IDENTITY     # the exact catch state
            prop.keyframe_insert(data_path="location", frame=f)
            prop.keyframe_insert(data_path="rotation_euler", frame=f)
            continue
        des = desired_world()
        t = 0.0 if f <= blend_from else min(1.0, (f - blend_from) / span)
        if t > 0.0:
            des = des.lerp(W0.get(f, prop.matrix_world.copy()), t)
        prop.matrix_basis = W0[f].inverted() @ des
        prop.keyframe_insert(data_path="location", frame=f)
        prop.keyframe_insert(data_path="rotation_euler", frame=f)

    # terminal identity key: pin the range + the held state (law 106)
    scene.frame_set(end_frame)
    live_update(scene, updates)
    prop.matrix_basis = _IDENTITY
    prop.keyframe_insert(data_path="location", frame=end_frame)
    prop.keyframe_insert(data_path="rotation_euler", frame=end_frame)

    ad = prop.animation_data
    if ad and ad.action:
        from . import iter_fcurves
        for fc in iter_fcurves(ad.action):
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'

    # post-verify at the blend end: basis must be EXACTLY identity
    scene.frame_set(blend_to)
    live_update(scene, updates)
    dm = sum(abs((prop.matrix_basis - _IDENTITY)[i][j])
             for i in range(4) for j in range(4))
    if dm > 1e-4:
        issues.append(f"carry_keys: basis != identity at blend_to "
                      f"f{blend_to} (delta {dm:.2e} — keys corrupted "
                      f"the catch placement)")
    if log:
        log(f"[prop_carry] keyed {len(frames)} carry frames + terminal "
            f"identity at f{end_frame}")
    return issues


# ---------------------------------------------------------------------------
# SANITY RADIUS gate (Blender-side; exporter gate 14 is the GLB twin)
# ---------------------------------------------------------------------------

def verify_riding(prop, scene, *, anchors, frames, max_dist,
                  updates: int = 2, label=None):
    """Fail-closed: at EVERY frame in `frames`, the prop's composed
    world position must be within max_dist of at least ONE anchor's
    world position. `anchors` may contain objects OR (armature, bone)
    tuples (bone reads go through armature.matrix_world @ pb.matrix).

    Catches any phantom offset/drift: a stale anchor capture, a
    rewritten parent track, a wrong-space offset — regardless of the
    mechanism, the prop ends up far from the body it should ride.
    """
    label = label or prop.name
    issues = []

    def _world(a):
        if isinstance(a, tuple):
            arm, bone = a
            pb = arm.pose.bones.get(bone)
            if pb is None:
                return None
            return (arm.matrix_world @ pb.matrix).copy()
        return a.matrix_world.copy()

    worst = 0.0
    worst_f = None
    for f in frames:
        scene.frame_set(f)
        live_update(scene, updates)
        p = prop.matrix_world.translation
        best = min(((p - _world(a).translation).length
                    for a in anchors if _world(a) is not None),
                   default=1e9)
        if best > worst:
            worst, worst_f = best, f
        if best > max_dist:
            issues.append(
                f"verify_riding: {label} is {best:.2f} m from ALL "
                f"anchors at f{f} (max {max_dist} m) — phantom offset?")
    if not issues:
        print(f"[prop_carry] {label}: riding verified, worst "
              f"{worst:.3f} m @ f{worst_f} (max {max_dist}) PASS")
    return issues
