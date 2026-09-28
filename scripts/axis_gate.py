#!/usr/bin/env python3
"""axis_gate.py -- 180-degree-rule / screen-direction continuity gate.

For each shot in a cut, project the dominant TRAVEL direction onto the
camera's screen-right axis. Between consecutive shots that both carry
lateral travel information, the sign must NOT flip (the classical axis
jump: the camera crossed the action line between cuts).

Travel model (treadmill worlds): the subject moves +y in the BELT frame;
cameras are world-static unless mounted on the subject (parent flag in
the cam table). Mounted/POV cameras and near-on-axis views carry no
lateral sign and are exempt.

Usage (from a master audit):
    import axis_gate as AXG
    findings = AXG.audit(ctx, CAMS_TABLE, SHOTS)   # list[str]

Standalone (bpy scene from a saved blend):
    blrun.sh --background --python axis_gate.py -- scene.blend
"""
from __future__ import annotations

import math

import bpy
from mathutils import Vector

# shots whose concept DEPENDS on axis-breaking or occlusion (per-shot
# policy -- extend per project): none by default; the caller passes
# exemptions.
DEFAULT_EXEMPT = set()

# |lateral| below this reads as on-axis (vertical flow only -- no sign)
LATERAL_EPS = 0.22


def _shot_travel_signs(ctx, cams_table, shots):
    """(sid, lateral_sign, mounted) per shot, evaluated at mid-frame."""
    scene = ctx["scene"]
    cam_map = ctx["cams"]
    # cam table rows: (name, loc0, loc1, lens, aim, parent_jeep, shake)
    mounted = {c[0]: bool(c[5]) for c in cams_table} if cams_table else {}
    out = []
    for sid, f0, f1, _d in shots:
        key = f"CAM_{sid}"
        info = cam_map.get(key)
        if info is None:
            out.append((sid, None, None))
            continue
        cam = info["cam"]
        f_mid = (f0 + f1) // 2
        scene.frame_set(f_mid)
        bpy.context.view_layer.update()
        mw = cam.matrix_world
        # camera right axis = +X of the camera in world
        right = (mw.to_3x3() @ Vector((1.0, 0.0, 0.0))).normalized()
        travel = Vector((0.0, 1.0, 0.0))      # belt-frame travel dir
        lateral = travel.dot(right)
        is_mounted = bool(mounted.get(key, False))
        out.append((sid, lateral, is_mounted))
    return out


def audit(ctx, cams_table, shots, exempt=DEFAULT_EXEMPT, verbose=False):
    """Return a list of axis-violation findings (advisory-friendly)."""
    findings = []
    signs = _shot_travel_signs(ctx, cams_table, shots)
    if verbose:
        for sid, lat, mnt in signs:
            print(f"[axis] {sid}: lateral={lat:+.3f} "
                  f"{'(mounted/POV)' if mnt else ''}")
    prev_lat = None
    prev_sid = None
    for sid, lat, mnt in signs:
        if sid in exempt or mnt or lat is None or abs(lat) < LATERAL_EPS:
            # no lateral information -- cannot violate; but also cannot
            # carry continuity ACROSS itself: keep the last lateral ref
            continue
        if prev_lat is not None and prev_lat * lat < 0:
            findings.append(
                f"[axis] SCREEN-DIRECTION FLIP at cut {prev_sid}->{sid}: "
                f"travel {prev_lat:+.2f} -> {lat:+.2f} (camera crossed "
                f"the action line between cuts)")
        prev_lat, prev_sid = lat, sid
    if not findings:
        findings.append("[axis] clean: no consecutive-cut screen-"
                        "direction flips")
    return findings


def _cli():
    import sys
    argv = sys.argv[sys.argv.index("--") + 1:]
    if not argv:
        print("usage: blrun.sh --background --python axis_gate.py -- "
              "scene.blend")
        return
    bpy.ops.wm.open_mainfile(filepath=argv[0])
    ctx = {"scene": bpy.context.scene,
           "cams": {o.name: {"cam": o} for o in bpy.data.objects
                    if o.type == 'CAMERA'}}
    # standalone mode has no cam table; treat all as world cams
    shots = [(m.camera.name.replace("CAM_", ""), m.frame, m.frame + 24, "")
             for m in bpy.context.scene.timeline_markers if m.camera]
    for s in audit(ctx, [], shots, verbose=True):
        print(s)


if __name__ == "__main__":
    _cli()
