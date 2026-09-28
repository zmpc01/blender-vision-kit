"""
contact_audit.py -- v4 step 5 gate (PLAN A4, REV3 item 7).

At sampled frames, for each VISIBLE grounded subject, assert a
DARK-TO-BRIGHT pixel transition under its screen-space base (the
contact disc). Kills the v3.4-documented no-contact-shadow "hover"
illusion class measurably, not by eye.

Method: renders the sample frames IN-PROCESS at delivery settings
(viewport preset + msaa8 + cavity), reads the pixels from the render
result, projects each subject's GROUND POINT (the disc world center /
wheel contact) to screen via world_to_camera_view, then compares the
mean luminance of an inner disk (the contact zone) vs an outer annulus
(the surrounding road): mean_inner < mean_outer - DELTA.

Fail-closed: any finding aborts (the caller decides).
"""
import math
import os

import bpy
from mathutils import Vector

DELTA = 0.04          # luma drop required under the base
INNER_R = 6           # px (960x540 delivery)
ANNULUS_R0, ANNULUS_R1 = 14, 22

# (frame, camera, subject-classes) -- classes: hero, seat, gunner,
# wheel, kd, crowd
SAMPLES = (
    (110, "CAM_S2", ("hero",)),
    (221, "CAM_S4", ("seat", "gunner", "wheel")),
    (400, "CAM_S6b", ("gunner", "wheel")),
    (630, "CAM_S9", ("seat", "wheel")),
    (300, "CAM_S5", ("kd", "crowd")),
    (900, "CAM_S11", ("crowd", "wheel")),
)


def _luma(pixels, W, H, x, y):
    # Blender image pixels are BOTTOM-LEFT origin (OpenGL): image row
    # y (top-down) = pixels row (H-1-y)
    i = ((H - 1 - y) * W + x) * 4
    return 0.2126 * pixels[i] + 0.7152 * pixels[i + 1] \
        + 0.0722 * pixels[i + 2]


def _patch_mean(pixels, W, H, cx, cy, r0, r1):
    vals = []
    for y in range(max(0, int(cy - r1)), min(H, int(cy + r1) + 1)):
        for x in range(max(0, int(cx - r1)), min(W, int(cx + r1) + 1)):
            d = math.hypot(x - cx, y - cy)
            if r0 <= d <= r1:
                vals.append(_luma(pixels, W, H, x, y))
    return sum(vals) / len(vals) if vals else 1.0


def _ground_points(ctx, classes):
    """World-space ground contact points for the subject classes."""
    pts = []
    for ob in bpy.data.objects:
        if not ob.name.startswith("Contact."):
            continue
        cls = ob.name.split(".")[1].lower()
        if cls in ("wheel", "seat", "gunner", "kd", "crowd", "hero"):
            if cls in classes or (cls == "crowd" and "crowd" in classes) \
                    or (cls == "hero" and "hero" in classes):
                pts.append((ob.name, ob.matrix_world.translation.copy()))
    return pts


def audit(ctx, verbose=True):
    findings = []
    scene = ctx["scene"]
    tmpdir = "/tmp/contact_audit"
    os.makedirs(tmpdir, exist_ok=True)
    ctx["_contact_tmpdir"] = tmpdir
    # delivery settings (viewport preset replica)
    scene.render.resolution_x = 960
    scene.render.resolution_y = 540
    scene.render.image_settings.file_format = 'PNG'
    scene.render.engine = 'BLENDER_WORKBENCH'
    try:
        scene.view_settings.view_transform = "Standard"
    except AttributeError:
        pass
    sh = scene.display.shading
    sh.light = 'STUDIO'
    sh.color_type = 'MATERIAL'
    sh.show_shadows = False
    sh.show_cavity = True
    sh.cavity_type = 'BOTH'
    sh.cavity_ridge_factor = 1.8
    sh.cavity_valley_factor = 2.0
    scene.display.render_aa = '8'
    import re as _re
    _atmo = _re.compile(r"mist|fog|haze|atmo", _re.IGNORECASE)
    for ob in scene.objects:
        if ob.get("kit_atmo") or _atmo.search(ob.name):
            ob.hide_render = True

    from bpy_extras.object_utils import world_to_camera_view
    W, H = 960, 540   # delivery resolution (set above)
    deps = bpy.context.evaluated_depsgraph_get()
    n_checked = n_skipped = 0
    for f, cam_name, classes in SAMPLES:
        info = ctx["cams"].get(cam_name)
        if info is None:
            findings.append(f"[contact] camera {cam_name} missing")
            continue
        cam = info["cam"]
        scene.camera = cam
        scene.frame_set(f)
        bpy.context.view_layer.update()
        bpy.context.view_layer.update()
        # headless: Render Result pixels are not readable in background
        # mode -- write to a temp file and load it back
        tmp = os.path.join(ctx.get("_contact_tmpdir", "/tmp"),
                           f"contact_f{f}.png")
        scene.render.filepath = tmp
        scene.render.image_settings.file_format = 'PNG'
        bpy.ops.render.render(write_still=True)
        img = bpy.data.images.load(tmp)
        img_p = list(img.pixels)
        pixels = img_p
        bpy.data.images.remove(img)
        if len(pixels) < W * H * 4:
            findings.append(f"[contact] f{f}: no render pixels "
                            f"(loaded {len(pixels)})")
            continue
        camw = cam.matrix_world.translation
        for ob_name, gp in _ground_points(ctx, classes):
            # GROUNDED filter: KD discs scale-ON at their land frame
            # (the FX taxonomy) -- a disc that is still scale-OFF means
            # the subject is IN FLIGHT at this frame, not grounded
            dobj = bpy.data.objects.get(ob_name)
            if dobj is not None:
                ev = dobj.evaluated_get(deps)
                if ev.scale.x < 0.5:
                    n_skipped += 1
                    continue
            # in-frustum: require the whole annulus safely inside (a
            # ground disc near the frame bottom reads partially clipped
            # and the road behind it poisons the outer mean)
            ndc = world_to_camera_view(scene, cam, gp)
            if not (0.15 < ndc.x < 0.85 and 0.12 < ndc.y < 0.88
                    and ndc.z > 0.5):
                n_skipped += 1
                continue
            # OCCLUSION: skip subjects whose ground patch is blocked
            # (a crowd zombie between the camera and the point read as
            # a false failure -- zombie-green luma ~0.61 == road)
            direction = (gp - camw)
            dist = direction.length
            direction = direction.normalized()
            hit = scene.ray_cast(deps, camw + direction * 0.2,
                                 direction, distance=dist - 0.15)
            # the ray legitimately hits the disc's OWN quad before its
            # center (self-occlusion at steep angles), and the
            # atmosphere box (Street.Mist) blocks EVERY ray while being
            # render-hidden -- reuse the occlusion gate's NON_OCCLUDERS
            # law + the Contact exemption
            from occlusion_gate import NON_OCCLUDERS
            blocker = hit[4] if (hit and hit[0]) else None
            if blocker is not None and \
                    not blocker.name.startswith("Contact.") and \
                    not blocker.name.startswith(NON_OCCLUDERS):
                n_skipped += 1
                continue
            cx, cy = ndc.x * W, (1.0 - ndc.y) * H
            if os.environ.get("CONTACT_DEBUG"):
                print(f"    [contact-dbg] f{f} {ob_name}: px ({cx:.0f},"
                      f"{cy:.0f}) ndc ({ndc.x:.3f},{ndc.y:.3f})")
            # disc screen radius from CAMERA MATH (world-axis edge
            # probes collapse to ~0 when the disc is near edge-on --
            # the +X edge points AT the camera; live-measured r_px
            # falling to the 4px clamp made every window tiny)
            lens = cam.data.lens
            sensor = cam.data.sensor_width \
                if cam.data.sensor_fit != 'VERTICAL' \
                else cam.data.sensor_height
            half_fov = math.atan(sensor / (2.0 * lens))
            r_px = 0.42 * (W / 2.0) / (max(0.5, ndc.z)
                                       * math.tan(half_fov))
            r_px = max(4.0, min(90.0, r_px))
            # THE SUBJECT OCCLUDES ITS OWN DISC CENTER (it stands ON
            # the disc): the visible dark part can be the center (high
            # angles), the far rim, or an off-center sliver (low-angle
            # occlusion shapes). Inner = the DARKEST QUARTILE of the
            # disc's screen REGION (wherever the disc shows); a missing
            # disc leaves the region pure road (p25 ~ road -> no
            # transition -> FAIL -- the class detection holds).
            x0 = int(max(0.0, cx - r_px * 0.95))
            x1 = int(min(W - 1.0, cx + r_px * 0.95))
            y0 = int(max(0.0, cy - r_px * 1.05))
            y1 = int(min(H - 1.0, cy + r_px * 0.15))
            region = sorted(_luma(pixels, W, H, x, y)
                            for y in range(y0, max(y0 + 1, y1))
                            for x in range(x0, max(x0 + 1, x1)))
            inner = region[len(region) // 4] if region else 1.0
            outer = _patch_mean(pixels, W, H, cx, cy,
                                r_px * 1.15, r_px * 1.6)
            n_checked += 1
            # distance-aware threshold: perspective + AA + cavity shrink
            # the observable contrast of FAR discs (a fixed 0.04
            # false-fails 10-15 m crowd discs that ARE rendering dark)
            delta_req = DELTA if ndc.z < 8.0 else 0.02
            if inner > outer - delta_req:
                findings.append(
                    f"[contact] f{f} {ob_name}: no dark-to-bright "
                    f"transition under base (inner {inner:.3f} vs "
                    f"outer {outer:.3f}, delta {outer - inner:.3f} < "
                    f"{delta_req})")
    if verbose:
        print(f"[contact_audit] {n_checked} grounded subjects checked "
              f"({n_skipped} occluded/out-of-frame skipped) across "
              f"{len(SAMPLES)} frames -> "
              f"{len(findings)} finding(s)")
    return findings
