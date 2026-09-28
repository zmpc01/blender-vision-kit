"""
scene_test_subagent.py — sub-agent test scene.

A rotating dark-wood pedestal with a bouncing gold torus on top, three
small colored spheres arranged in a triangle around the pedestal base,
a dramatic key sun + soft fill area light, a 50mm camera at (4, -4, 3),
and a procedural Nishita sky world. 24-frame animation.

Usage:
    blrun.sh --background --python scripts/scene_test_subagent.py -- \\
        --output /tmp/subagent_test --dry-run --scene-name subagent_test
"""
import math

import bpy
from mathutils import Vector

from blender_kit import (
    common_parser, script_argv, clear_scene, configure_render, render,
    make_material, shade_smooth, add_sky_world, print_scene_summary,
)


# ---------------------------------------------------------------------------
# Build the static scene (no animation). Return a context dict.
# ---------------------------------------------------------------------------

def build_scene():
    clear_scene()

    # ---- Ground plane (large, so no visible edge) -----------------------
    # An infinite-ish plane ensures the camera never sees the dark
    # below-horizon part of the world background. The sky is still active
    # (via add_sky_world) for ambient lighting even though it isn't directly
    # visible at this camera angle — see camera note below.
    bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, 0))
    plane = bpy.context.active_object
    plane.name = "Ground"
    # Slight blue tint so the ground picks up the sky ambient and reads as
    # "outdoor" rather than a neutral studio sweep. Light enough that cast
    # shadows read with strong contrast.
    plane.data.materials.append(
        make_material("GroundMat", (0.24, 0.26, 0.30), roughness=0.85))

    # ---- Rotating pedestal (cylinder, r=0.8, h=0.2, dark wood) -----------
    # Cylinder origin is at its center, so z = h/2 = 0.1 to rest on ground.
    ped_r = 0.8
    ped_h = 0.2
    bpy.ops.mesh.primitive_cylinder_add(
        radius=ped_r, depth=ped_h, vertices=64,
        location=(0, 0, ped_h / 2))
    pedestal = bpy.context.active_object
    pedestal.name = "Pedestal"
    shade_smooth(pedestal)
    pedestal.data.materials.append(
        make_material("WoodMat", (0.022, 0.011, 0.005),  # very dark wood
                       roughness=0.7, metallic=0.0))

    # ---- Bouncing torus on top of pedestal (gold) ------------------------
    # Major R=0.4, minor r=0.1. Resting on pedestal top (z=0.2) means
    # torus center z = ped_h + minor_r = 0.2 + 0.1 = 0.3.
    torus_major = 0.4
    torus_minor = 0.1
    torus_rest_z = ped_h + torus_minor   # 0.3
    bpy.ops.mesh.primitive_torus_add(
        major_radius=torus_major, minor_radius=torus_minor,
        location=(0, 0, torus_rest_z),
        major_segments=48, minor_segments=16)
    torus = bpy.context.active_object
    torus.name = "Torus"
    shade_smooth(torus)
    torus.data.materials.append(
        make_material("GoldMat", (1.00, 0.78, 0.20),
                       roughness=0.25, metallic=0.95))

    # ---- Three small spheres in a triangle around pedestal base ----------
    # Radius 0.15, resting on ground (z = 0.15), placed at radius 1.3
    # from center (outside the pedestal's 0.8 radius), 120° apart.
    sph_r = 0.15
    tri_radius = 1.3
    sphere_specs = [
        ("SphereRed",   (0.95, 0.05, 0.05), 0),
        ("SphereGreen", (0.05, 0.70, 0.15), math.radians(120)),
        ("SphereBlue",  (0.05, 0.25, 0.95), math.radians(240)),
    ]
    spheres = []
    for name, color, angle in sphere_specs:
        x = tri_radius * math.cos(angle)
        y = tri_radius * math.sin(angle)
        bpy.ops.mesh.primitive_uv_sphere_add(
            radius=sph_r, location=(x, y, sph_r))
        s = bpy.context.active_object
        s.name = name
        shade_smooth(s)
        s.data.materials.append(
            make_material(name + "Mat", color, roughness=0.35, metallic=0.2))
        spheres.append(s)

    # ---- Dramatic key sun light (above-right) ---------------------------
    # "Above-right" = screen-right of the camera (camera at (4,-4,3) looks
    # toward -X,+Y, so screen-right is toward +X,+Y). Low elevation (10°)
    # gives long dramatic shadows that fall to screen-LEFT, visible in frame.
    # For SUN, location is irrelevant — only rotation matters.
    sun_elev = math.radians(10)
    sun_azim = math.radians(45)   # 45° = screen-right
    sun_pos = Vector((math.cos(sun_elev) * math.cos(sun_azim),
                      math.cos(sun_elev) * math.sin(sun_azim),
                      math.sin(sun_elev)))
    sun_dir = -sun_pos            # direction the light travels (toward scene)
    bpy.ops.object.light_add(type='SUN', location=sun_pos * 5)
    sun = bpy.context.active_object
    sun.name = "KeyLight"
    sun.data.energy = 20.0  # very strong key for high-contrast dramatic light
    # Aim the sun so its -Z (light direction) points along sun_dir.
    sun.rotation_euler = sun_dir.to_track_quat('-Z', 'Y').to_euler()
    # Hard sun shadow + EEVEE contact shadows so small objects read as grounded.
    try:
        sun.data.shadow_soft_size = 0.0   # crisp shadow penumbra
    except AttributeError:
        pass
    try:
        sun.data.use_contact_shadow = True
    except AttributeError:
        pass  # attribute name drift across Blender versions

    # ---- Soft fill area light (from the left) ----------------------------
    # Camera looks from (4,-4,3) toward origin; "left" of camera is
    # roughly the -x,+y direction. Low energy for dramatic key:fill ratio.
    bpy.ops.object.light_add(type='AREA', location=(-4, 2, 3))
    fill = bpy.context.active_object
    fill.name = "FillLight"
    fill.data.energy = 8.0   # just enough to keep contact areas visible
    fill.data.size = 3.0
    # Aim the area light at the pedestal.
    _look_at(fill, Vector((0, 0, 0.5)))

    # ---- Camera at (4, -4, 3) looking at pedestal, 50mm -----------------
    # Aimed at the pedestal top area. NOTE: with a 50mm lens at (4,-4,3)
    # and the pedestal at z≈0, the vertical FOV (~23°) is too narrow to
    # include both the pedestal AND the horizon in frame — so the blue sky
    # is not directly visible. The sky world is still active and provides
    # ambient + sun lighting. This is a geometric consequence of the spec.
    bpy.ops.object.camera_add(location=(4, -4, 3))
    cam = bpy.context.active_object
    cam.name = "MainCam"
    cam.data.lens = 50
    _look_at(cam, Vector((0, 0, 0.5)))
    bpy.context.scene.camera = cam

    # ---- Sky world (procedural Nishita) ----------------------------------
    # Sun elevation/rotation match the key light (10° elev, 45° azim) so the
    # sky's sun is in the same place as the light. Very low strength keeps
    # shadows deep and high-contrast.
    add_sky_world(sun_elevation_deg=10.0, sun_rotation_deg=45.0, strength=0.1)

    return {
        "pedestal": pedestal,
        "torus": torus,
        "spheres": spheres,
        "torus_rest_z": torus_rest_z,
        "ped_h": ped_h,
    }


def _look_at(obj, target):
    """Set obj.rotation_euler so its local -Z (camera/light forward) points
    at `target`. Uses the standard mathutils to_track_quat trick so the
    rotation is baked (keyframeable, glTF-exportable)."""
    direction = target - obj.location
    rot_quat = direction.to_track_quat('-Z', 'Y')
    obj.rotation_euler = rot_quat.to_euler()


# ---------------------------------------------------------------------------
# Animation. Use ctx dict from build_scene().
# ---------------------------------------------------------------------------

def animate(ctx, *, start_frame=1, n_frames=24):
    scene = bpy.context.scene
    scene.frame_start = start_frame
    scene.frame_end = start_frame + n_frames - 1
    scene.frame_set(start_frame)

    pedestal = ctx["pedestal"]
    torus = ctx["torus"]
    torus_rest_z = ctx["torus_rest_z"]
    end_frame = start_frame + n_frames - 1
    mid = start_frame + n_frames // 2

    # ---- Pedestal: rotates 360° around vertical (Z) over the full range -
    pedestal.rotation_euler = (0, 0, 0)
    pedestal.keyframe_insert("rotation_euler", index=2)
    scene.frame_set(end_frame)
    pedestal.rotation_euler = (0, 0, math.radians(360))
    pedestal.keyframe_insert("rotation_euler", index=2)

    # ---- Torus: bounces up at mid-frame and tumbles 360° around X -------
    scene.frame_set(start_frame)
    torus.location = (0, 0, torus_rest_z)
    torus.rotation_euler = (0, 0, 0)
    torus.keyframe_insert("location", index=2)
    torus.keyframe_insert("rotation_euler", index=0)

    scene.frame_set(mid)
    torus.location = (0, 0, torus_rest_z + 0.8)   # apex 0.8 units above rest
    torus.rotation_euler = (math.radians(180), 0, 0)
    torus.keyframe_insert("location", index=2)
    torus.keyframe_insert("rotation_euler", index=0)

    scene.frame_set(end_frame)
    torus.location = (0, 0, torus_rest_z)
    torus.rotation_euler = (math.radians(360), 0, 0)
    torus.keyframe_insert("location", index=2)
    torus.keyframe_insert("rotation_euler", index=0)

    # ---- Bezier easing on all keyframes ---------------------------------
    for obj in (pedestal, torus):
        if obj.animation_data and obj.animation_data.action:
            for fcurve in obj.animation_data.action.fcurves:
                for kp in fcurve.keyframe_points:
                    kp.interpolation = 'BEZIER'
                    kp.easing = 'EASE_IN_OUT'

    scene.frame_set(start_frame)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main():
    p = common_parser()
    args = p.parse_args(script_argv())
    print(f"[scene_test_subagent] args: {args}")
    ctx = build_scene()
    animate(ctx, start_frame=args.start, n_frames=args.frames)
    configure_render(args)
    print_scene_summary(args.scene_name)
    render(args, scene_name=args.scene_name)


if __name__ == "__main__":
    main()
