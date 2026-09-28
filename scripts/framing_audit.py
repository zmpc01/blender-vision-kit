#!/usr/bin/env python3
"""framing_audit.py -- deterministic subject-margin gate (head-crop detector).

DESIGN v3.2 §2. Projects each shot's SUBJECTS into the shot camera and
asserts margins in NDC space. NO rendering, NO VLM -- pure math at
build time, so head crops become BUILD FAILURES, not user complaints.

world_to_camera_view returns 0..1 REGION coords -- normalized here to
NDC (x_n = 2x-1, y_n = 2y-1) so both edges bind (round-1 review P1-10:
the raw 0..1 spec silently no-ops the feet/left checks).

Usage (inside a scene build, via exec or import):
    import framing_audit as FA
    issues = FA.audit(scene, shots, subjects, verbose=True)

`shots`    : list of (shot_id, f_start, f_end)
`subjects` : dict shot_id -> list of subject specs:
             ("name", getter) where getter(scene, frame) -> {
                 "head": Vector world (top of head),
                 "feet": Vector world,
                 "bbox": [Vector x8] world corners (optional; derived
                          from head/feet + radius if omitted),
                 "radius": half-width in metres (optional, default 0.3)}
The getter pattern keeps this generic: capsule actors, jeep, crowd
bands all plug in. Constraints (TRACK_TO) and parent chains are
honoured because we sample AFTER scene.frame_set + view_layer.update.
"""
import math
import os

import bpy
from mathutils import Vector

# NDC margins (round-1 review: 4% headroom, 2% footroom, 4% sides)
HEADROOM = 0.92     # head y_n must stay BELOW this
FOOTROOM = -0.96    # feet y_n must stay ABOVE this
SIDEROOM = 0.92     # |x_n| must stay BELOW this
SAMPLES = 9         # frames sampled per shot
GRACE_LO, GRACE_HI = 0.30, 0.90  # sample the middle of the window
                        # (entry/exit drift is legitimate coverage)


def _region_to_ndc(rv):
    return 2.0 * rv.x - 1.0, 2.0 * rv.y - 1.0


def _project(scene, cam, depsgraph, p):
    from bpy_extras.object_utils import world_to_camera_view
    rv = world_to_camera_view(scene, cam, p)
    return _region_to_ndc(rv)


def _default_bbox(sub):
    r = sub.get("radius", 0.30)
    head, feet = sub["head"], sub["feet"]
    mid = (head + feet) * 0.5
    return [Vector((mid.x - r, mid.y - r, mid.z)),
            Vector((mid.x + r, mid.y - r, mid.z)),
            Vector((mid.x - r, mid.y + r, mid.z)),
            Vector((mid.x + r, mid.y + r, mid.z)),
            head, feet]


def audit(scene, shots, subjects, verbose=False):
    """Returns list of issue strings (empty = pass)."""
    issues = []
    depsgraph = bpy.context.evaluated_depsgraph_get()
    cams = {o.name: o for o in scene.objects if o.type == 'CAMERA'}
    markers = {m.frame: m.camera for m in scene.timeline_markers}
    for row in shots:
        shot_id, f0, f1 = row[0], row[1], row[2]   # tolerate 3/4-tuples
        subs = subjects.get(shot_id)
        if not subs:
            continue  # shots without tracked subjects skip (env-only)
        # traverse tallies: subjects that legitimately sweep through the
        # frame (action beats) must be IN frame >= 60% of samples, not
        # every sample (strict stays every-sample)
        traverse_ok = {}
        traverse_tot = {}
        span = f1 - f0
        cam = None
        for k in range(SAMPLES):
            f = int(round(f0 + span * (GRACE_LO +
                     (GRACE_HI - GRACE_LO) * k / (SAMPLES - 1))))
            f = min(max(f, f0), f1)
            # active camera for this frame (marker-bound in our scenes)
            mc = markers.get(f) or markers.get(f0) or scene.camera
            cam = (mc if mc else scene.camera)
            if cam is None:
                issues.append(f"{shot_id}: no camera bound at f{f}")
                continue
            scene.frame_set(f)
            scene.view_layers[0].update()
            # v3.2r3: the EVALUATED camera's data can be a stale COW
            # copy that never sees post-bake lens edits (the auto-fit
            # changes were invisible through it). Project with the RAW
            # camera (whose data holds the current lens) after copying
            # in the constraint-solved matrix from the evaluated one.
            depsgraph = bpy.context.evaluated_depsgraph_get()
            cam_ev = cam.evaluated_get(depsgraph)
            cam.matrix_world = cam_ev.matrix_world.copy()
            cam_ev = cam
            if __debug__ and os.environ.get("FA_DEBUG"):
                print(f"    [fa-debug] {shot_id} f{f} cam={cam.name} "
                      f"lens={cam_ev.data.lens:.0f}")
            for name, getter in subs:
                try:
                    sub = getter(scene, f)
                except Exception as e:  # noqa: BLE001
                    issues.append(f"{shot_id} f{f} {name}: getter {e}")
                    continue
                if not sub or sub.get("head") is None:
                    continue  # subject not alive/present this frame
                hx, hy = _project(scene, cam_ev, depsgraph, sub["head"])
                fx, fy = _project(scene, cam_ev, depsgraph, sub["feet"])
                # in-frame check for this sample
                bad = (hy > 1.0 or hy < -1.0 or abs(hx) > 1.0
                       or hy > HEADROOM
                       or abs(hx) > SIDEROOM or abs(fx) > SIDEROOM)
                if not sub.get("feet_crop"):
                    bad = bad or fy < -1.0 or fy > 1.0 or fy < FOOTROOM
                key = (shot_id, name)
                traverse_tot[key] = traverse_tot.get(key, 0) + 1
                if not bad:
                    traverse_ok[key] = traverse_ok.get(key, 0) + 1
                if sub.get("traverse"):
                    continue          # judged by the 60% rule at the end
                if bad:
                    # report the specific margin that failed
                    if hy > 1.0 or hy < -1.0 or abs(hx) > 1.0:
                        issues.append(
                            f"{shot_id} f{f} {name}: HEAD OUT OF FRAME "
                            f"(y_n {hy:+.2f}, x_n {hx:+.2f})")
                    elif hy > HEADROOM:
                        issues.append(
                            f"{shot_id} f{f} {name}: head cropped, only "
                            f"{(1 - hy) * 50:.1f}% headroom "
                            f"(min {100 - HEADROOM * 50:.0f}%)")
                    if not sub.get("feet_crop"):
                        if fy < -1.0 or fy > 1.0:
                            issues.append(
                                f"{shot_id} f{f} {name}: FEET OUT OF "
                                f"FRAME (y_n {fy:+.2f})")
                        elif fy < FOOTROOM:
                            issues.append(
                                f"{shot_id} f{f} {name}: feet clipped "
                                f"(y_n {fy:+.2f}, min {FOOTROOM:+.2f})")
                    for tag, xn in (("head", hx), ("feet", fx)):
                        if abs(xn) > SIDEROOM:
                            issues.append(
                                f"{shot_id} f{f} {name}: {tag} at frame "
                                f"edge (x_n {xn:+.2f}, limit ±{SIDEROOM})")
        # traverse verdicts (>= 60% in-frame)
        for (sid, name), tot in traverse_tot.items():
            ok = traverse_ok.get((sid, name), 0)
            if tot >= 5 and ok < 0.6 * tot:
                issues.append(
                    f"{sid} {name}: traverse subject in frame only "
                    f"{ok}/{tot} samples (< 60%)")
    if verbose:
        if issues:
            print(f"[framing_audit] {len(issues)} issue(s):")
            for i in issues[:40]:
                print("  -", i)
        else:
            print("[framing_audit] PASS: all subject margins within "
                  "NDC limits")
    return issues


def auto_fit(scene, shots, subjects, rounds=3, verbose=False):
    """Iterative camera fitting (the systemic head-crop fix): for every
    shot whose subjects violate the margins, first WIDEN the lens (keeps
    composition center; works for jeep-parented cams), then if still
    violating DOLLY the static camera back along its aim axis. Re-runs
    the audit each round; returns (n_fixed, remaining_issues).
    This is the 'never prompt for zoom-outs again' mechanism: the gate
    DETECTS, auto-fit REPAIRS, the gate VERIFIES."""
    import math as _m
    fixed = []
    for r in range(rounds):
        issues = audit(scene, shots, subjects)
        if not issues:
            break
        by_shot = {}
        for i in issues:
            # "S1a f12 Driver: head cropped, only 3% headroom (min 8%)"
            parts = i.split(" ")
            sid = parts[0]
            by_shot.setdefault(sid, []).append(i)
        progressed = False
        for sid, shot_issues in by_shot.items():
            shot = next(s for s in shots if s[0] == sid)
            f0, f1 = shot[1], shot[2]
            cam = _shot_cam(scene, shots, sid)
            if cam is None:
                continue
            # derive the worst NDC value from the issue strings
            worst = 0.0
            for i in shot_issues:
                for tok in i.replace("(", " ").replace(")", " ").split():
                    try:
                        v = float(tok)
                    except ValueError:
                        continue
                    if 1.0 < abs(v) < 3.0:
                        worst = max(worst, abs(v))
            if worst <= 1.0:
                # margin-only violations (headroom %): widen one step
                worst = 1.05
            scale = 0.88 / worst           # target NDC 0.88 with margin
            scale = max(0.55, min(0.95, scale))
            if scale >= 0.97:
                continue
            cam_data = cam.data
            new_lens = max(18.0, cam_data.lens * scale)
            if abs(new_lens - cam_data.lens) > 0.5:
                fixed.append(f"{sid}: lens {cam_data.lens:.0f} -> "
                             f"{new_lens:.0f} mm (round {r + 1})")
                cam_data.lens = new_lens
                cam_data.update_tag()
                bpy.context.view_layer.update()
                progressed = True
        if not progressed:
            break
    # v3.2r3 AIM-ASSIST (round 4+): lens widening cannot recover an
    # aim that pitches away from the subject (S6b class: aim 28 deg
    # below a standing figure). Bend the TRACK target 50% toward the
    # violated subject's head at the shot midpoint.
    for r in range(rounds):
        issues = audit(scene, shots, subjects)
        if not issues:
            break
        by_shot = {}
        for i in issues:
            sid = i.split(" ")[0]
            by_shot.setdefault(sid, []).append(i)
        progressed = False
        for sid, shot_issues in by_shot.items():
            shot = next(s for s in shots if s[0] == sid)
            cam = _shot_cam(scene, shots, sid)
            if cam is None:
                continue
            tgt = None
            for c in cam.constraints:
                if c.type == 'TRACK_TO' and c.target is not None:
                    tgt = c.target
                    break
            if tgt is None:
                continue
            subs = subjects.get(sid) or []
            if not subs:
                continue
            f_mid = (shot[1] + shot[2]) // 2
            scene.frame_set(f_mid)
            scene.view_layers[0].update()
            # average subject head world pos
            from mathutils import Vector as _V
            heads = []
            for _name, getter in subs:
                try:
                    sub = getter(scene, f_mid)
                except Exception:                     # noqa: BLE001
                    continue
                if sub and sub.get("head"):
                    heads.append(_V(sub["head"]))
            if not heads:
                continue
            center = sum(heads, _V((0, 0, 0))) / len(heads)
            new_aim = _V(tgt.location) * 0.5 + center * 0.5
            if (new_aim - _V(tgt.location)).length < 0.05:
                continue
            fixed.append(f"{sid}: aim assist -> "
                         f"({new_aim.x:.1f},{new_aim.y:.1f},{new_aim.z:.1f}) "
                         f"@f{f_mid} (round {rounds + r + 1})")
            tgt.location = new_aim
            tgt.keyframe_insert(data_path="location", frame=f_mid)
            progressed = True
        if not progressed:
            break

    remaining = audit(scene, shots, subjects)
    if verbose:
        for f in fixed:
            print(f"[framing_auto_fit] {f}")
        if remaining:
            print(f"[framing_auto_fit] {len(remaining)} issues remain "
                  f"after {rounds} rounds")
        else:
            print("[framing_auto_fit] all shots fit after auto-fit")
    return fixed, remaining


def _shot_cam(scene, shots, sid):
    markers = {m.frame: m.camera for m in scene.timeline_markers}
    shot = next(s for s in shots if s[0] == sid)
    mc = markers.get(shot[1])
    if mc:
        return mc
    return scene.objects.get(f"CAM_{sid}")


# self-test on a synthetic KNOWN-BAD scene (gate sanity: every gate must
# fail on known-bad input before trusting it on good ones -- SKILL.md)
def _selftest():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    bpy.ops.object.camera_add(location=(0, -6, 1.2), rotation=(1.2, 0, 0))
    cam = bpy.context.object
    cam.data.lens = 50
    sc.camera = cam
    # subject: head at z 1.9 => projects HIGH in frame at this angle
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.1, location=(0, 0, 1.9))
    head_obj = bpy.context.object

    def getter(scene, f):
        mw = head_obj.matrix_world
        return {"head": mw @ Vector((0, 0, 0.1)),
                "feet": mw @ Vector((0, 0, -1.8))}

    sc.frame_start, sc.frame_end = 1, 24
    shots = [("T1", 1, 24)]
    issues = audit(sc, shots, {"T1": [("bad", getter)]})
    # a 2.0 m subject 6 m from a 50 mm camera aimed at z=1.2 WILL crop
    # the head -- if the gate reports nothing, the gate is broken.
    ok = len(issues) > 0 and any("HEAD" in i or "headroom" in i for i in issues)
    print("[framing_audit] SELFTEST:", "PASS (known-bad caught)" if ok
          else "FAIL (gate is a no-op on known-bad input!)")
    return ok


if __name__ == "__main__":
    import json
    print(json.dumps({"selftest": _selftest()}))
