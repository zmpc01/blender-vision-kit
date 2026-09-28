"""
Iterated Blender scene — fixes issues identified by VLM analysis of v1:
  1. Cube was floating (z=0.8 with size=1.2, so bottom was at z=0.2).
     Fix: z = size/2 = 0.6, so the cube rests on the plane.
  2. Lighting was flat / no environment reflections.
     Fix: add a Sky texture to the world for HDRI-like ambient lighting.
  3. Framing was sparse, objects clustered upper-left.
     Fix: tighter camera framing, reposition objects using rule-of-thirds.
  4. Add a third object (torus) for better composition balance.

Same CLI as scene_basic.py.
"""
import argparse
import math
import os
import sys
import bpy


def parse_args():
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


def make_material(name, color, roughness=0.5, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return mat


def add_sky_world():
    """Replace the world background with a procedural Sky texture for HDRI-like ambient."""
    world = bpy.data.worlds.new("World") if not bpy.data.worlds else bpy.data.worlds[0]
    bpy.context.scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    sky = nt.nodes.new("ShaderNodeTexSky")
    sky.sky_type = 'NISHITA'
    sky.sun_elevation = math.radians(25)
    sky.sun_rotation = math.radians(45)
    sky.air_density = 1.0
    sky.dust_density = 4.0
    bg.inputs["Strength"].default_value = 1.0
    nt.links.new(sky.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])


def build_scene():
    # Ground plane
    bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, 0))
    plane = bpy.context.active_object
    plane.name = "Ground"
    plane.data.materials.append(make_material("GroundMat", (0.20, 0.22, 0.24), roughness=0.85))

    # Hero cube — RESTING on ground (z = size/2)
    cube_size = 1.2
    bpy.ops.mesh.primitive_cube_add(size=cube_size, location=(0, 0, cube_size / 2))
    cube = bpy.context.active_object
    cube.name = "HeroCube"
    cube.data.materials.append(make_material("CubeMat", (0.95, 0.35, 0.15), roughness=0.35, metallic=0.1))

    # Sphere — RESTING on ground (z = radius)
    sphere_r = 0.45
    bpy.ops.mesh.primitive_uv_sphere_add(radius=sphere_r, location=(1.8, 0.6, sphere_r))
    sphere = bpy.context.active_object
    sphere.name = "Sphere"
    # Shade smooth on the sphere
    for poly in sphere.data.polygons:
        poly.use_smooth = True
    sphere.data.materials.append(make_material("SphereMat", (0.20, 0.55, 0.95), roughness=0.25, metallic=0.4))

    # Torus — new third object for better composition
    torus_major = 0.45
    bpy.ops.mesh.primitive_torus_add(
        major_radius=torus_major, minor_radius=0.12,
        location=(-1.6, 0.4, torus_major))
    torus = bpy.context.active_object
    torus.name = "Torus"
    torus.rotation_euler = (math.radians(70), 0, math.radians(20))
    for poly in torus.data.polygons:
        poly.use_smooth = True
    torus.data.materials.append(make_material("TorusMat", (0.95, 0.85, 0.20), roughness=0.3, metallic=0.6))

    # Key sun light
    bpy.ops.object.light_add(type='SUN', location=(4, -4, 6))
    sun = bpy.context.active_object
    sun.name = "KeyLight"
    sun.data.energy = 3.0
    sun.rotation_euler = (math.radians(55), math.radians(15), math.radians(35))

    # Fill area light
    bpy.ops.object.light_add(type='AREA', location=(-3, -2, 3))
    fill = bpy.context.active_object
    fill.name = "FillLight"
    fill.data.energy = 150.0
    fill.data.size = 3.0

    # Camera — tighter framing, rule of thirds
    bpy.ops.object.camera_add(location=(4.5, -4.5, 2.8),
                              rotation=(math.radians(72), 0, math.radians(45)))
    cam = bpy.context.active_object
    cam.name = "MainCam"
    cam.data.lens = 50
    bpy.context.scene.camera = cam

    # Sky world for HDRI-like ambient
    add_sky_world()

    return cube, sphere, torus, cam


def animate(cube, sphere, torus, start_frame=1, n_frames=24):
    scene = bpy.context.scene
    scene.frame_start = start_frame
    scene.frame_end = start_frame + n_frames - 1
    scene.frame_set(start_frame)

    # Cube bounces up and rotates
    cube.keyframe_insert("location", index=2)
    cube.keyframe_insert("rotation_euler")

    mid = start_frame + n_frames // 2
    scene.frame_set(mid)
    cube.location.z = 1.8
    cube.rotation_euler = (math.radians(180), 0, math.radians(90))
    cube.keyframe_insert("location", index=2)
    cube.keyframe_insert("rotation_euler")

    end_frame = start_frame + n_frames - 1
    scene.frame_set(end_frame)
    cube.location.z = cube_size / 2 if (cube_size := 1.2) else 0.6
    cube.rotation_euler = (math.radians(360), 0, math.radians(180))
    cube.keyframe_insert("location", index=2)
    cube.keyframe_insert("rotation_euler")

    # Sphere drifts left
    sphere.keyframe_insert("location", index=0)
    scene.frame_set(end_frame)
    sphere.location.x = -1.8
    sphere.keyframe_insert("location", index=0)

    # Torus rolls
    torus.keyframe_insert("rotation_euler")
    torus.keyframe_insert("location", index=1)
    scene.frame_set(end_frame)
    torus.rotation_euler = (math.radians(70), math.radians(720), math.radians(20))
    torus.location.y = -1.0
    torus.keyframe_insert("rotation_euler")
    torus.keyframe_insert("location", index=1)

    # Bezier easing
    for obj in (cube, sphere, torus):
        if obj.animation_data and obj.animation_data.action:
            for fcurve in obj.animation_data.action.fcurves:
                for kp in fcurve.keyframe_points:
                    kp.interpolation = 'BEZIER'
                    kp.easing = 'EASE_IN_OUT'

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
        scene.eevee.taa_render_samples = args.samples
        scene.eevee.use_gtao = True
        scene.eevee.use_bloom = False
        scene.eevee.use_ssr = True

    os.makedirs(args.output, exist_ok=True)
    scene.render.filepath = os.path.join(args.output, "frame_####.png")


def main():
    args = parse_args()
    print(f"[scene_v2] engine={args.engine} frames={args.frames} samples={args.samples} size={args.w}x{args.h}")
    clear_scene()
    cube, sphere, torus, cam = build_scene()
    animate(cube, sphere, torus, start_frame=args.start, n_frames=args.frames)
    configure_render(args)

    print(f"[scene_v2] Scene objects: {[o.name for o in bpy.context.scene.objects]}")
    print(f"[scene_v2] Frame range: {bpy.context.scene.frame_start}..{bpy.context.scene.frame_end}")
    print(f"[scene_v2] Rendering {args.frames} frames to {args.output} ...")
    bpy.ops.render.render(animation=True, write_still=False)
    print(f"[scene_v2] Done. Output dir contents:")
    for fn in sorted(os.listdir(args.output)):
        full = os.path.join(args.output, fn)
        if os.path.isfile(full):
            print(f"   - {fn}  ({os.path.getsize(full)} bytes)")


if __name__ == "__main__":
    main()
