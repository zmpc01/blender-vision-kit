"""s19_td3_probe.py — the F-TD3 native-vision ground-truth probe (session-19).

The silent-wrong-render class: Blender's render operator prefers a
CAMERA-BOUND TIMELINE MARKER over scene.camera. A film scene carries shot
markers, so every probe render silently showed a SHOT camera instead of
the requested one — exit 0, no hint. The s17 fix sweeps marker bindings
before rendering (render_angle) and look.py reports camera_intent rows.

This probe builds a scene where the two cameras see OPPOSITE subjects:

  CamMain   (scene.camera)  — frames the RED cube (x=+2)
  CamMarker (marker-bound)  — frames the BLUE sphere (x=-2)

Ground truth for the EYES:
  - every look.py panel MUST show the RED cube prominent (CamMain's view);
    if a panel shows the blue sphere instead, the marker hijacked the
    render (the F-TD3 regression).
  - the verdict text must carry camera_intent rows naming the sweep.
"""
import bpy


def _purge_factory():
    for name in ("Cube", "Camera", "Light"):
        o = bpy.data.objects.get(name)
        if o is not None:
            bpy.data.objects.remove(o, do_unlink=True)


def make_material(name, rgba):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = rgba
    mat.diffuse_color = rgba  # workbench reads THIS
    return mat


def build_scene():
    _purge_factory()
    scene = bpy.context.scene

    ground = bpy.data.meshes.new("Ground")
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=6)
    bm.to_mesh(ground)
    bm.free()
    go = bpy.data.objects.new("Ground", ground)
    scene.collection.objects.link(go)

    def box(name, loc, rgba, size=0.8):
        mesh = bpy.data.meshes.new(name)
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=size)
        bm.to_mesh(mesh)
        bm.free()
        ob = bpy.data.objects.new(name, mesh)
        ob.location = loc
        scene.collection.objects.link(ob)
        ob.data.materials.append(make_material(name + "_mat", rgba))
        return ob

    box("RedCube", (2.0, 0.0, 0.4), (0.85, 0.1, 0.1, 1.0))
    box("BlueSphereBox", (-2.0, 0.0, 0.4), (0.1, 0.2, 0.85, 1.0))

    def cam(name, loc, rot):
        c = bpy.data.cameras.new(name)
        co = bpy.data.objects.new(name, c)
        co.location = loc
        co.rotation_euler = rot
        scene.collection.objects.link(co)
        return co

    import math
    # CamMain: front-on at +Y, sees the RED cube (x=+2) center-frame;
    # the blue box at x=-2 sits far LEFT edge.
    cam_main = cam("CamMain", (0.0, 8.0, 2.2),
                   (math.radians(80), 0.0, 0.0))
    # CamMarker: from BEHIND (-Y), sees the BLUE box center-frame.
    cam_marker = cam("CamMarker", (0.0, -8.0, 2.2),
                     (math.radians(100), 0.0, math.radians(180)))

    scene.camera = cam_main  # the INTENDED render camera

    # the F-TD3 hijack: a marker INSIDE the render frame bound to the
    # OTHER camera. Without the sweep, bpy.ops.render.render uses
    # CamMarker here and every panel shows the blue box.
    marker = scene.timeline_markers.new("SHOT_B", frame=1)
    marker.camera = cam_marker

    return {"scene": scene, "cameras": {"main": cam_main,
                                        "marker": cam_marker}}


def animate(ctx):
    pass  # static probe
