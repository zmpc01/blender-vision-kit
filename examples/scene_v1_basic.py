"""
Blender headless test script.
Creates a small scene (plane + cube + light + camera), animates the cube,
and renders either a single frame or a short PNG sequence.

Usage:
  blender --background --python scene_basic.py -- \\
      --output /path/to/out  \\
      --engine CYCLES|BLENDER_EEVEE_NEXT \\
      [--frames 24] [--start 1] [--samples 32] [--w 640 --h 360]
"""
import argparse
import math
import os
import sys

import bpy


def parse_args():
    # Arguments after "--" on the blender CLI are passed to the script.
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []
    p = argparse.ArgumentParser()
    p.add_argument("--output", required=True)
    p.add_argument("--engine", default="CYCLES",
                   choices=["CYCLES", "BLENDER_EEVEE_NEXT"])
    p.add_argument("--frames", type=int, default=24)
    p.add_argument("--start", type=int, default=1)
    p.add_argument("--samples", type=int, default=32)
    p.add_argument("--w", type=int, default=640)
    p.add_argument("--h", type=int, default=360)
    return p.parse_args(argv)


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    # Ensure nothing left over
    for coll in list(bpy.data.collections):
        bpy.data.collections.remove(coll)


def make_material(name, color, roughness=0.5, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return mat


def build_scene():
    # Ground plane
    bpy.ops.mesh.primitive_plane_add(size=10, location=(0, 0, 0))
    plane = bpy.context.active_object
    plane.name = "Ground"
    plane.data.materials.append(make_material("GroundMat", (0.18, 0.20, 0.22), roughness=0.9))

    # Hero cube
    bpy.ops.mesh.primitive_cube_add(size=1.2, location=(0, 0, 0.8))
    cube = bpy.context.active_object
    cube.name = "HeroCube"
    cube.data.materials.append(make_material("CubeMat", (0.95, 0.35, 0.15), roughness=0.35, metallic=0.1))

    # Secondary sphere
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.4, location=(2.0, 0, 0.4))
    sphere = bpy.context.active_object
    sphere.name = "Sphere"
    sphere.data.materials.append(make_material("SphereMat", (0.20, 0.55, 0.95), roughness=0.25, metallic=0.4))

    # Key light (sun)
    bpy.ops.object.light_add(type='SUN', location=(4, -4, 6))
    sun = bpy.context.active_object
    sun.name = "KeyLight"
    sun.data.energy = 4.0
    sun.rotation_euler = (math.radians(50), math.radians(20), math.radians(35))

    # Fill light (area)
    bpy.ops.object.light_add(type='AREA', location=(-3, -2, 3))
    fill = bpy.context.active_object
    fill.name = "FillLight"
    fill.data.energy = 200.0
    fill.data.size = 3.0

    # Camera
    bpy.ops.object.camera_add(location=(5.0, -5.0, 3.2),
                              rotation=(math.radians(65), 0, math.radians(45)))
    cam = bpy.context.active_object
    cam.name = "MainCam"
    cam.data.lens = 35
    bpy.context.scene.camera = cam

    # World background
    world = bpy.data.worlds.new("World") if not bpy.data.worlds else bpy.data.worlds[0]
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (0.04, 0.05, 0.07, 1.0)
    bg.inputs["Strength"].default_value = 1.0

    return cube, sphere, cam


def animate(cube, sphere, start_frame=1, n_frames=24):
    scene = bpy.context.scene
    scene.frame_start = start_frame
    scene.frame_end = start_frame + n_frames - 1
    scene.frame_set(start_frame)

    # Cube bounces up and rotates
    cube.keyframe_insert("location", index=2)              # z at start
    cube.keyframe_insert("rotation_euler")                  # rotation at start

    mid = start_frame + n_frames // 2
    scene.frame_set(mid)
    cube.location.z = 2.4
    cube.rotation_euler = (math.radians(180), 0, math.radians(90))
    cube.keyframe_insert("location", index=2)
    cube.keyframe_insert("rotation_euler")

    scene.frame_set(start_frame + n_frames - 1)
    cube.location.z = 0.8
    cube.rotation_euler = (math.radians(360), 0, math.radians(180))
    cube.keyframe_insert("location", index=2)
    cube.keyframe_insert("rotation_euler")

    # Make the bounce a bit snappier
    if cube.animation_data and cube.animation_data.action:
        for fcurve in cube.animation_data.action.fcurves:
            for kp in fcurve.keyframe_points:
                kp.interpolation = 'BEZIER'
                kp.easing = 'EASE_OUT'

    # Sphere drifts left
    sphere.keyframe_insert("location", index=0)
    scene.frame_set(start_frame + n_frames - 1)
    sphere.location.x = -2.0
    sphere.keyframe_insert("location", index=0)

    scene.frame_set(start_frame)


def configure_render(args):
    scene = bpy.context.scene
    scene.render.engine = args.engine
    scene.render.resolution_x = args.w
    scene.render.resolution_y = args.h
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.film_transparent = False

    if args.engine == "CYCLES":
        scene.cycles.device = 'CPU'
        scene.cycles.samples = args.samples
        scene.cycles.use_denoising = True
    else:
        # EEVEE Next
        scene.eevee.taa_render_samples = args.samples
        scene.eevee.use_gtao = True
        scene.eevee.use_bloom = False
        scene.eevee.use_ssr = True

    # Output path
    os.makedirs(args.output, exist_ok=True)
    scene.render.filepath = os.path.join(args.output, "frame_####.png")


def main():
    args = parse_args()
    print(f"[scene_basic] engine={args.engine} frames={args.frames} samples={args.samples} size={args.w}x{args.h}")
    clear_scene()
    cube, sphere, cam = build_scene()
    animate(cube, sphere, start_frame=args.start, n_frames=args.frames)
    configure_render(args)

    # Print scene summary
    print(f"[scene_basic] Scene objects: {[o.name for o in bpy.context.scene.objects]}")
    print(f"[scene_basic] Camera: {bpy.context.scene.camera.name}")
    print(f"[scene_basic] Frame range: {bpy.context.scene.frame_start}..{bpy.context.scene.frame_end}")

    # Render
    print(f"[scene_basic] Rendering {args.frames} frames to {args.output} ...")
    bpy.ops.render.render(animation=True, write_still=False)
    print(f"[scene_basic] Done. Output dir contents:")
    for fn in sorted(os.listdir(args.output)):
        full = os.path.join(args.output, fn)
        if os.path.isfile(full):
            print(f"   - {fn}  ({os.path.getsize(full)} bytes)")


if __name__ == "__main__":
    main()
