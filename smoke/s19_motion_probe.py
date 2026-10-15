"""s19_motion_probe.py — the A2 filmstrip native-vision probe (session-19).

The s18-A2 bug: motion_study.filmstrip() never frame_set(f), so EVERY cell
showed the LAST pose while being LABELED per-frame — a default-on lie
(n-cell strip of identical images). The fix sets the frame + updates the
depsgraph per cell.

Ground truth for the EYES: the subject MOVES diagonally (+x, +z) and
SPINS across 24 frames — every cell in the strip must show a DIFFERENT
pose, left-to-right progression, growing rotation. Two identical adjacent
cells = the A2 regression.
"""
import bpy
import math


def _purge_factory():
    for name in ("Cube", "Camera", "Light"):
        o = bpy.data.objects.get(name)
        if o is not None:
            bpy.data.objects.remove(o, do_unlink=True)


def build_scene():
    _purge_factory()
    scene = bpy.context.scene

    import bmesh
    mesh = bpy.data.meshes.new("Mover")
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bm.to_mesh(mesh)
    bm.free()
    mover = bpy.data.objects.new("Mover", mesh)
    scene.collection.objects.link(mover)
    mat = bpy.data.materials.new("Mover_mat")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = (0.9, 0.5, 0.1, 1.0)
    mat.diffuse_color = (0.9, 0.5, 0.1, 1.0)
    mover.data.materials.append(mat)

    cam = bpy.data.cameras.new("Cam")
    co = bpy.data.objects.new("Cam", cam)
    co.location = (2.0, -7.0, 2.0)
    co.rotation_euler = (math.radians(80), 0.0, 0.0)
    scene.collection.objects.link(co)
    scene.camera = co

    light = bpy.data.lights.new("Sun", type='SUN')
    light.energy = 3.0
    lo = bpy.data.objects.new("Sun", light)
    lo.rotation_euler = (math.radians(45), 0.0, math.radians(30))
    scene.collection.objects.link(lo)

    # a static reference post so the eyes can see the motion against it
    post_mesh = bpy.data.meshes.new("Post")
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bm.to_mesh(post_mesh)
    bm.free()
    post = bpy.data.objects.new("Post", post_mesh)
    post.scale = (0.1, 0.1, 2.0)
    post.location = (0.0, 2.0, 1.0)
    scene.collection.objects.link(post)

    scene.frame_start = 1
    scene.frame_end = 24
    mover.location = (-2.0, 0.0, 0.5)
    mover.keyframe_insert("location", frame=1)
    mover.keyframe_insert("rotation_euler", frame=1)
    mover.location = (2.0, 0.0, 2.5)
    mover.rotation_euler = (0.0, 0.0, math.radians(270))
    mover.keyframe_insert("location", frame=24)
    mover.keyframe_insert("rotation_euler", frame=24)

    return {"scene": scene}


def animate(ctx, start_frame=1, n_frames=24):
    pass  # the keys are absolute in build_scene
