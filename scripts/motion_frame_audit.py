#!/usr/bin/env python3
"""motion_frame_audit.py v2 -- the ATTACH / GLUED-OBJECT / RIDER gate.

Catches the round-4 class: objects that MOVE WITH THE SUBJECT (jeep)
when they should be part of the streaming world. In the treadmill
world (belt streams backward, jeep world-static):

    world-static object that stays visible = it paces the jeep
    = it "rides with the vehicle" on screen (the FX.Spark class that
    rode through S10b/S11/S12 in v3.3).

v2 (r4-review-a corrections over the v1 draft):
  - MOTION_POLICY declares intended-static objects (skyline, ground,
    mist, hidden proxies...); ANYTHING else world-static + visible =
    violation (fail-closed, no guessing).
  - Visibility test = hide_render + hide_viewport + visible_camera +
    evaluated scale (RB proxies and emitters rely on visible_camera).
  - Subject tree auto-exempt (jeep children = cargo/riders/actors).
  - Aim.* empties exempt (camera aim targets).
  - anim-end-freeze rule fires ONLY for objects OUTSIDE the belt tree
    (belt children stream post-key by construction -- verified on
    Zed.KD1-13 in the v3.3 blend).
  - FX lifecycle: TRANSIENT FX (scale-ON) must scale-OFF within 40
    frames; WORLD-LITTER must classify STREAMS after settle.

Usage (from a master audit):
    import motion_frame_audit as MFA
    findings = MFA.audit(ctx, samples=(1, 300, 701, 754, 790, 1080))
"""
from __future__ import annotations

import re

import bpy
from mathutils import Vector

TOL_RATIO = 0.08      # within 8% of the reference displacement = same
TOL_ABS = 0.35        # m -- smaller displacement = "static"
FX_OFF_MAX = 40       # frames a TRANSIENT FX may stay on after its event


def _policy(ctx):
    """Import MOTION_POLICY from the scene module (fall back empty)."""
    pol = {"intended_static": [], "intended_subject_tree": "JeepRoot",
           "aim_exempt": r"^Aim\."}
    try:
        import scene_escape_v3_3 as SC
        if hasattr(SC, "MOTION_POLICY"):
            pol.update(SC.MOTION_POLICY)
    except Exception:
        pass
    return pol


def _visible(obj):
    try:
        if obj.hide_render or obj.hide_viewport:
            return False
        if hasattr(obj, "visible_camera") and not obj.visible_camera:
            return False
        if tuple(obj.scale) < (0.01, 0.01, 0.01):
            return False
    except Exception:
        return True
    return True


def _in_belt_tree(ob):
    p = ob.parent
    while p:
        if p.name == "BeltRoot":
            return True
        p = p.parent
    return False


def _in_subject_tree(ob, subject_name):
    p = ob
    while p:
        if p.name == subject_name:
            return True
        p = p.parent
    return False


def _classify(d_obj, d_ref):
    """STREAMS (with belt) / STATIC (world) / OWN."""
    n_obj = d_obj.length
    if n_obj < TOL_ABS:
        return "STATIC"
    if d_ref.length > 0.5 and \
            (d_obj - d_ref).length < TOL_RATIO * d_ref.length + TOL_ABS:
        return "STREAMS"
    return "OWN"


def _anim_end(ob):
    """Last keyframe frame over all fcurves (None if unkeyed)."""
    ad = ob.animation_data
    if not (ad and ad.action):
        return None
    last = None
    for fc in ad.action.fcurves:
        for kp in fc.keyframe_points:
            if last is None or kp.co[0] > last:
                last = kp.co[0]
    return int(last) if last is not None else None


def _fx_off_key(ob):
    """True if a scale-OFF key exists after the scale-ON key."""
    ad = ob.animation_data
    if not (ad and ad.action):
        return False
    ons, offs = [], []
    for fc in ad.action.fcurves:
        if fc.data_path == "scale":
            for kp in fc.keyframe_points:
                (offs if kp.co[1] < 0.01 else ons).append(int(kp.co[0]))
    return bool(ons and offs and max(offs) > max(ons))


def audit(ctx, samples=(1, 300, 701, 754, 790, 1080)):
    findings = []
    scene = ctx["scene"]
    dep = bpy.context.evaluated_depsgraph_get()
    belt = ctx.get("belt") or bpy.data.objects.get("BeltRoot")
    pol = _policy(ctx)
    static_rx = [re.compile(p) for p in pol["intended_static"]]
    aim_rx = re.compile(pol["aim_exempt"])
    subject_name = pol["intended_subject_tree"]
    frames = sorted(set(int(f) for f in samples))

    def pos_at(ob, f):
        scene.frame_set(f)
        dep.update()
        return ob.matrix_world.translation.copy()

    belt_pos = {f: pos_at(belt, f) for f in frames}

    n_obj = n_vis = 0
    for ob in bpy.data.objects:
        if ob.type not in ("MESH", "EMPTY", "LIGHT"):
            continue
        if ob.name.startswith("CAM_") or aim_rx.match(ob.name):
            continue
        n_obj += 1
        if not _visible(ob):
            continue                      # hidden objects cannot ride
        n_vis += 1
        if any(rx.match(ob.name) for rx in static_rx):
            continue                      # declared backdrop
        if _in_subject_tree(ob, subject_name) or ob.name == belt.name:
            continue                      # jeep tree / the belt itself
        try:
            poses = {f: pos_at(ob, f) for f in frames}
        except Exception:
            continue
        segs = []
        for a, b in zip(frames, frames[1:]):
            d_obj = poses[b] - poses[a]
            d_ref = belt_pos[b] - belt_pos[a]
            segs.append(_classify(d_obj, d_ref))
        # the belt moves the whole time; STATIC segments while visible
        if "STATIC" in segs:
            last = _anim_end(ob)
            # world-litter FX: legal when the FINAL segment streams
            # (belt-composed at rest -- the _kf_sparks_v2 litter path)
            litter_ok = (ob.name.startswith("FX.") and segs
                         and segs[-1] == "STREAMS")
            if litter_ok:
                pass
            elif _in_belt_tree(ob):
                # belt child, static in world = frozen LOCAL keys
                if last is not None and last < frames[-1]:
                    findings.append(
                        f"[motion] {ob.name}: belt child FROZEN at f{last} "
                        f"(local keys end, world-static after) -- "
                        f"re-compose with belt-follow keys")
                else:
                    findings.append(
                        f"[motion] {ob.name}: belt child world-static "
                        f"with no local keys (never streams)")
            elif ob.name.startswith("FX."):
                if not _fx_off_key(ob):
                    findings.append(
                        f"[motion] {ob.name}: FX visible + world-static "
                        f"(scale-ON with no OFF) -- the v3.3 rider class; "
                        f"add lifecycle keys (transient OFF / litter "
                        f"belt-compose)")
            else:
                findings.append(
                    f"[motion] {ob.name}: world-static + visible while "
                    f"the world streams (rides the subject) -- parent to "
                    f"the belt, belt-compose keys, or hide")

    # FX lifecycle sweep (independent of sampling): every FX with a
    # scale-ON key must have an OFF within FX_OFF_MAX frames -- OR be a
    # belt-composed litter object (STREAMS post-settle)
    for ob in bpy.data.objects:
        if not ob.name.startswith("FX.") or ob.type != "MESH":
            continue
        ad = ob.animation_data
        if not (ad and ad.action):
            continue
        has_on = any(fc.data_path == "scale" and
                     any(kp.co[1] > 0.01 for kp in fc.keyframe_points)
                     for fc in ad.action.fcurves)
        if has_on and not _fx_off_key(ob):
            # legal only if it STREAMS after its last key (litter)
            if _in_belt_tree(ob):
                continue
            last = _anim_end(ob) or 0
            fa = min(last + FX_OFF_MAX, frames[-1])
            fb = min(last + FX_OFF_MAX + 12, frames[-1])
            if fb <= fa:
                continue                      # event too close to the end
            scene.frame_set(fa)
            dep.update()
            a = ob.matrix_world.translation.copy()
            scene.frame_set(fb)
            dep.update()
            b = ob.matrix_world.translation.copy()
            if (b - a).length < 0.05:
                findings.append(
                    f"[motion] {ob.name}: FX scale-ON with no OFF and no "
                    f"belt-compose (frozen at f{last}) -- lifecycle "
                    f"contract violation")
    scene.frame_set(1)
    if not findings:
        findings.append(f"[motion] clean: {n_vis}/{n_obj} visible "
                        f"objects, 0 riders/frozen")
    return findings
