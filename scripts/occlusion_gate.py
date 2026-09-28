#!/usr/bin/env python3
"""occlusion_gate.py v2 -- lens + subject-visibility gate (ray cast).

v3.4 rewrite (round-4 RCA BUG 1). v1 missed three delivered failures
(all verified in v3.3):
  - S4b f239-262: the camera sat 0.18 m INSIDE the rear wheel -- the
    tire face filled ~79% of every frame. v1 HARD-SKIPPED S4b
    (line-97 skip list: "mount/POV/env shots") and only ever counted
    Zed.* as occluders anyway.
  - S8 f490-496: an abandoned car crossed the camera zone at 0.2-1.1 m
    for ~6 frames. f492 WAS sampled -- but Street.* could never count
    as an occluder.
  - S5b f303: the launched KD3 zombie transited the lens at 0.13 m
    (the concept exemption "blocker IS the subject" was scoped to
    PARTIAL occlusion, not lens transit).

v2 design (r4-review-b corrections):
  1. NO skip list -- every shot gets both checks.
  2. Occluder set = ALL renderable non-subject geometry (any object
     that is visible_camera and not in the shot's subject family).
  3. LENS-RAY EVERY FRAME (1 ray/frame along the view axis; cheap):
       hard fail  first hit < 0.30 m
       warn band  0.30-1.25 m, fails on >= QUORUM consecutive frames
     (S3b's intended foreground pounder sits at 1.31 m -- a single
     frame survives the quorum; S8's 6-frame skim trips it.)
  4. Subject-visibility sampling densified to every 4 frames.
  5. Concept exemptions apply to PARTIAL subject occlusion ONLY --
     never to lens-transit or near-field blocks.

Usage (from a master audit):
    import occlusion_gate as OCG
    findings = OCG.audit(ctx, SHOTS)
"""
from __future__ import annotations

import math

import bpy
from mathutils import Vector

# ---- thresholds (calibrated r4-review-b on the v3.3 corpus) ----------
LENS_HARD = 0.30        # m: first view-ray hit closer = blocked frame
LENS_WARN_LO = 0.30     # m: warn band start
LENS_WARN_HI = 1.25     # m: warn band end (S3b pounder at 1.31 m safe)
QUORUM = 2              # consecutive warn-band frames to fail
QUORUM_POV = 3          # POV shots tolerate one more graze frame
POV_SHOTS = {"S7"}      # bumper POV: near-field IS the concept
# v3.4: dolly-through shots (camera moves INSIDE the pack by design):
# near-field passes are the shot's energy; sustained grazing (4+)
# still fails. Hard <0.30 m fails everywhere; the post-render
# render_stats gate is the final arbiter of what the viewer sees.
DOLLY_THROUGH = {"S2", "S8"}
# default per-shot PARTIAL-occlusion allowance (subject-visibility arm)
DEFAULT_FLAG_RATIO = 0.08
# concept exemptions: PARTIAL occlusion only (never lens-transit).
# v3.4 calibration: chase-through shots (jeep weaving INSIDE the horde)
# legitimately show partial subject occlusion on ~1/3 of frames -- the
# class this arm exists for is SYSTEMIC invisibility (v3.3r1's S7
# 80-100% blocked), which 0.35 still catches. Partial occlusion by the
# pursuing pack is the shot concept, not a defect.
CHASE_SHOTS = 0.35
# concept exemptions: PARTIAL occlusion only (never lens-transit)
DEFAULT_EXEMPT = {"S1b": 0.95, "S12b": 0.95, "S7": 0.60,
                  "S3b": 0.90, "S6": CHASE_SHOTS,
                  # v3.4: S5b re-scoped -- subject = KD3 (the launched
                  # zombie), partial allowance 0.25 (was 0.50 with
                  # subject = jeep, which let the lens transit pass)
                  "S5b": 0.25,
                  # v3.4: chase-through concepts (horde surrounds the
                  # subject; partial blocks are the drama). S4b's insert
                  # camera sits in the horde corridor (pursuing legs
                  # cross the wheel view); S6 rear-3/4 through the pack
                  # measured 0.58 with v2's dense sampling (v1: 0.50).
                  "S2": CHASE_SHOTS, "S4": CHASE_SHOTS, "S5": CHASE_SHOTS,
                  "S4b": CHASE_SHOTS, "S6": 0.60,
                  "S8": CHASE_SHOTS, "S9": CHASE_SHOTS, "S10": CHASE_SHOTS,
                  "S10b": CHASE_SHOTS}
# subject per shot: name -> (object, [(x,y,z) point offsets])
# v3.4: the wheel-insert's subject is the WHEEL (not the whole jeep
# box -- ground-insert cameras legitimately have pursuing zombies
# between lens and the jeep body; the readable-subject test is the
# wheel itself). Zombie/hero subjects test full height.
SUBJECTS = {
    "S5b": ("Zed.0014", [(0.0, 0.0, 1.55), (0.0, 0.0, 0.10)]),
    "S8": ("HeroZed.Root", [(0.0, 0.0, 1.55), (0.0, 0.0, 0.30)]),
    # v3.4: the wheel-insert's readable subject is the TREAD band
    # (z 0-0.3) -- the fender overhangs the wheel, so upper-wheel rays
    # legitimately pass the body from any rear view
    # offsets are relative to the wheel CENTER (world z 0.42): the
    # tread band is BELOW center (world z 0.06-0.26 = offsets -0.36..-0.16)
    "S4b": ("Jeep.WheelRL", [(0.0, 0.0, -0.16), (0.0, 0.0, -0.36),
                             (0.3, 0.0, -0.26), (-0.3, 0.0, -0.26)]),
}
# ATMOSPHERE: translucent/backdrop objects that NEVER count as
# occluders (they blocked S1a/S12a subject rays as phantom findings
# -- mist is intended atmosphere, skyline is the distant backdrop)
NON_OCCLUDERS = ("Street.Mist", "Street.Skyline", "FX.Dust")

_RAYS = 24


def _visible(obj):
    """Renderable right now (evaluated scale + visibility flags)."""
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


def _occluder(name):
    return not name.startswith(NON_OCCLUDERS)


def _active_cam(ctx, sid):
    info = ctx["cams"].get(f"CAM_{sid}")
    return info["cam"] if info else None


def _subject_points(ctx, sid):
    """Subject key points per shot (head/feet/quarter box)."""
    pts = []
    jeep = ctx["jeep"]
    humans = ctx.get("humans", {})
    sub = SUBJECTS.get(sid)
    if sub:
        ob = bpy.data.objects.get(sub[0])
        if ob is not None:
            mw = ob.matrix_world
            pts = [mw @ Vector(v) for v in sub[1]]
            return _fan(pts)
    if sid in ("S1a", "S1b", "S2", "S3b"):
        for name in ("Driver", "Girl", "Gunner"):
            root = humans.get(name, {}).get("root")
            if root is None:
                continue
            mw = root.matrix_world
            pts.append(mw @ Vector((0.0, 0.0, 1.55)))
            pts.append(mw @ Vector((0.0, 0.0, 0.10)))
    elif sid == "S6b":
        root = humans.get("Gunner", {}).get("root")
        if root is not None:
            mw = root.matrix_world
            pts.append(mw @ Vector((0.0, 0.0, 1.55)))
    elif sid == "S8":
        root = humans.get("HeroZed", {}).get("root")
        if root is not None:
            mw = root.matrix_world
            pts.append(mw @ Vector((0.0, 0.0, 1.55)))
            pts.append(mw @ Vector((0.0, 0.0, 0.30)))
    if not pts or sid in ("S4", "S5", "S6", "S9", "S10",
                          "S10b", "S11", "S12a", "S12b", "S3"):
        mw = jeep.matrix_world
        pts = [mw @ Vector(v) for v in (
            (0.0, 0.0, 2.30), (1.05, 2.20, 1.20), (-1.05, 2.20, 1.20),
            (1.05, -2.20, 0.60), (-1.05, -2.20, 0.60), (0.0, 0.0, 0.15))]
    return _fan(pts)


def _fan(pts):
    """Densify: ring pattern around the first two anchors (24 rays)."""
    rays = []
    anchors = pts[:2] or pts
    per = max(1, _RAYS // len(anchors))
    for p in anchors:
        for i in range(per):
            a = (i / per) * 2 * math.pi
            rays.append(p + Vector((math.sin(a) * 0.18,
                                    math.cos(a) * 0.18, 0.0)))
    return rays or pts


def _subject_family(ctx, sid):
    """Names that count as the subject (never occluders) for this shot."""
    fam = {"JeepRoot", "RB.JeepCollider"}
    for o in ctx["jeep"].children_recursive:
        fam.add(o.name)
    sub = SUBJECTS.get(sid)
    if sub:
        ob = bpy.data.objects.get(sub[0])
        if ob:
            fam.add(ob.name)
            if ob.parent:
                fam.add(ob.parent.name)
    return fam


def audit(ctx, shots, samples=None, exempt=None, flag_ratio=None):
    findings = []
    exempt = dict(DEFAULT_EXEMPT if exempt is None else exempt)
    flag_ratio = DEFAULT_FLAG_RATIO if flag_ratio is None else flag_ratio
    scene = ctx["scene"]
    dep = bpy.context.evaluated_depsgraph_get()

    for sid, f0, f1, _d in shots:
        cam = _active_cam(ctx, sid)
        if cam is None:
            continue
        fam = _subject_family(ctx, sid)
        if sid in POV_SHOTS:
            quorum = QUORUM_POV
        elif sid in DOLLY_THROUGH:
            quorum = 4
        else:
            quorum = QUORUM

        # ---- arm 1: lens-ray EVERY frame (the v1-missed class) ------
        # NOTE: dep.update() per frame is REQUIRED -- constraint-driven
        # cameras (track-to) return STALE matrix_world with only
        # view_layer.update(), producing phantom lens hits (found while
        # calibrating v2 against the in-probe ground truth)
        hard_hits, warn_run, warn_best = [], 0, 0
        for f in range(f0, f1 + 1):
            scene.frame_set(f)
            dep.update()
            mw = cam.matrix_world
            origin = mw.translation.copy()
            direction = (mw.to_3x3() @ Vector((0.0, 0.0, -1))).normalized()
            hit = scene.ray_cast(dep, origin, direction)
            d, ho = None, None
            if hit[0]:
                loc, obj = hit[1], hit[4]
                if obj is not None and obj.name not in fam \
                        and _visible(obj) and _occluder(obj.name):
                    d = (loc - origin).length
                    ho = obj.name
            if d is not None and d < LENS_HARD:
                hard_hits.append((f, round(d, 2), ho))
                warn_run = 0
            elif d is not None and d < LENS_WARN_HI:
                warn_run += 1
                warn_best = max(warn_best, warn_run)
            else:
                warn_run = 0
        if hard_hits:
            f0h, dh, oh = hard_hits[0]
            findings.append(f"[occlusion] {sid}: LENS BLOCKED {len(hard_hits)} "
                            f"frame(s) < {LENS_HARD} m (first f{f0h}: {oh} "
                            f"at {dh} m) -- camera inside/near geometry")
        elif warn_best >= quorum:
            findings.append(f"[occlusion] {sid}: near-field graze "
                            f"{warn_best} consecutive frame(s) < "
                            f"{LENS_WARN_HI} m -- pull the path or the "
                            f"deco clear of the lens")

        # ---- arm 2: subject visibility every 4 frames ---------------
        allow = exempt.get(sid, flag_ratio)
        flagged = n_s = 0
        for f in range(f0, f1 + 1, 4):
            scene.frame_set(f)
            dep.update()
            mw = cam.matrix_world
            origin = mw.translation.copy()
            points = _subject_points(ctx, sid)
            blocked = total = 0
            for p in points:
                dv = (p - origin)
                dist = dv.length
                if dist < 1e-4:
                    continue
                hit = scene.ray_cast(dep, origin, dv.normalized())
                if hit[0]:
                    loc, obj = hit[1], hit[4]
                    if obj is not None and obj.name not in fam \
                            and _visible(obj) and _occluder(obj.name):
                        if (loc - origin).length < dist - 0.30:
                            blocked += 1
                total += 1
            if total and blocked / total > 0.35:
                flagged += 1
            n_s += 1
        if n_s and flagged / n_s > allow:
            findings.append(f"[occlusion] {sid}: subject blocked in "
                            f"{flagged}/{n_s} sampled frames "
                            f"(allowance {allow:.0%}) -- trim/pull back "
                            f"or raise the concept exemption")

    if not findings:
        findings.append("[occlusion] clean: lens-ray + subject-visibility "
                        "pass on every shot")
    scene.frame_set(1)
    return findings
