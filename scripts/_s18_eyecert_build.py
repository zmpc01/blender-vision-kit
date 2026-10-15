"""_s18_eyecert_build.py — session-18 NATIVE-VISION e2e ground-truth fixture.

Builds a scene whose ground truth is KNOWN BY CONSTRUCTION so the
orchestrator (the only vision-native agent) can verify the eye tools'
claims against reality:

  ground plane 20x20m ........................ the 1m grid is countable
  RED cube    @ ( 2,  0, 0.5)  size 1m ...... front panel: right of center
  GREEN cyl   @ (-2,  1, 0.5)  r=.4 h=1 ..... front panel: left of center
  BLUE sphere @ ( 0,  3, 0.5)  r=.5 ......... front panel: behind center
  AMBER slab  @ ( 0, -3, 0.05) 3x2x0.1 ...... seated (not floating)
  FLOAT box   @ ( 4, -4, 2.0)  1m ........... 2m ABOVE ground = validator
                                              P1 floating + red flag box
  animated marker-cone: keys z at f1/f10/f20 (filmstrip ground truth)
  CAM_MARKER  @ ( 8,  8, 4) looking at origin, bound to timeline marker
  "S1" @f1 ................ the F-TD3 hijack camera (distinctive view:
                             everything seen from the NE-high diagonal)
  scene.camera = MainCam @ (0,-9,2) looking at origin (front view)

Run:  blrun.sh --background --python scripts/_s18_eyecert_build.py --
      --out output/s18_eyecert
"""
import bpy
import sys
import os
from mathutils import Vector


def _material(name, rgb):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
    return m


def _box(name, loc, size, rgb, collection=None):
    col = collection or bpy.context.collection
    m = _material(f"Mat_{name}", rgb)
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.scale = size
    o.data.materials.append(m)
    return o


def build():
    """Build the eyecert scene. Returns ctx (scene-module contract)."""
    # factory-purge law
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)

    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'

    # ground (seated by construction)
    _box("Ground", (0, 0, -0.05), (20, 20, 0.1), (0.35, 0.35, 0.38))
    # known-color objects at known positions
    _box("RedCube", (2, 0, 0.5), (1, 1, 1), (0.75, 0.05, 0.05))
    cyl_m = _material("Mat_GreenCyl", (0.05, 0.65, 0.1))
    bpy.ops.mesh.primitive_cylinder_add(radius=0.4, depth=1.0,
                                        location=(-2, 1, 0.5))
    gc = bpy.context.active_object
    gc.name = "GreenCyl"
    gc.data.materials.append(cyl_m)
    sph_m = _material("Mat_BlueSphere", (0.05, 0.1, 0.7))
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.5, location=(0, 3, 0.5))
    bs = bpy.context.active_object
    bs.name = "BlueSphere"
    bs.data.materials.append(sph_m)
    _box("AmberSlab", (0, -3, 0.05), (3, 2, 0.1), (0.8, 0.55, 0.1))
    # THE FLOATER — 2m above ground, nothing under it (validator P1 + flag)
    _box("FloatBox", (4, -4, 2.0), (1, 1, 1), (0.9, 0.3, 0.02))

    # animated cone (filmstrip ground truth: z 1 -> 2 -> 3)
    cone_m = _material("Mat_MarkerCone", (0.9, 0.9, 0.9))
    bpy.ops.mesh.primitive_cone_add(radius1=0.3, depth=0.6,
                                    location=(0, 0, 1.0))
    cone = bpy.context.active_object
    cone.name = "MarkerCone"
    cone.data.materials.append(cone_m)
    for f, z in ((1, 1.0), (10, 2.0), (20, 3.0)):
        cone.location.z = z
        cone.keyframe_insert(data_path="location", frame=f)

    # THE F-TD3 HIJACK CAMERA: bound to a marker at f1 — a distinctive
    # NE-high diagonal. If any tool renders THIS camera when it claims a
    # front/temp view, the image is visually unmistakable (we look down
    # the +X/+Y diagonal; RedCube reads center-front, FloatBox near-left).
    mcam_data = bpy.data.cameras.new("CAM_MARKER_data")
    mcam = bpy.data.objects.new("CAM_MARKER", mcam_data)
    bpy.context.collection.objects.link(mcam)
    mcam.location = (8, 8, 4)
    direction = Vector((0, 0, 0.5)) - mcam.location
    mcam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

    mk = scene.timeline_markers.new("S1", frame=1)
    mk.camera = mcam

    # scene.camera: the honest front view
    main_data = bpy.data.cameras.new("MainCam_data")
    main = bpy.data.objects.new("MainCam", main_data)
    bpy.context.collection.objects.link(main)
    main.location = (0, -9, 2)
    d = Vector((0, 0, 0.5)) - main.location
    main.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    scene.camera = main

    # light so EEVEE/quality previews read
    light_data = bpy.data.lights.new("Key", type='SUN')
    light_data.energy = 3.0
    light = bpy.data.objects.new("Key", light_data)
    bpy.context.collection.objects.link(light)
    light.location = (3, -4, 6)
    light.rotation_euler = (0.6, 0.1, 0.5)

    scene.frame_start = 1
    scene.frame_end = 24
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.render.resolution_x = 640
    scene.render.resolution_y = 480
    print("[eyecert] scene built:", [o.name for o in scene.objects])
    print("[eyecert] marker S1 bound to CAM_MARKER; scene.camera =", scene.camera.name)
    return {"scene": scene}


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = "output/s18_eyecert"
    if "--out" in argv:
        out = argv[argv.index("--out") + 1]
    build()
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, "eyecert.blend")
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(path))
    print(f"[eyecert] saved {path}")


# scene-module alias (safe_import_scene contract) so eye tools can
# --scene this fixture directly
build_scene = build


def animate(ctx, start_frame=1, n_frames=24):
    return  # keys are planted in build()


if __name__ == "__main__":
    main()
