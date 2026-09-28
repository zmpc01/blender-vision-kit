# mpi_semantics_probe.py -- resolve the matrix_parent_inverse composition
# law for Blender 4.5 empirically (the v4 z-contract depends on it).
import bpy
from mathutils import Matrix, Vector

scene = bpy.context.scene
p = bpy.data.objects.new("P", None)
scene.collection.objects.link(p)
p.location = (0.0, 0.0, -0.06)

c = bpy.data.objects.new("C", None)
scene.collection.objects.link(c)
c.location = (0.0, 0.0, 0.06)          # basis T(0,0,0.06)

c.parent = p
c.matrix_parent_inverse = p.matrix_world.inverted()   # T(0,0,+0.06)
bpy.context.view_layer.update()
bpy.context.view_layer.update()

z_mpi = c.matrix_world.translation.z
# Formula A: world = parent @ MPI @ basis        -> -0.06+0.06+0.06 = +0.06
# Formula B: world = parent @ MPI.inverted() @ basis -> -0.06-0.06+0.06 = -0.06
print(f"MPI-direct probe: z = {z_mpi:+.4f} "
      f"(A=+0.06 parent@MPI@basis, B=-0.06 parent@MPIinv@basis)")

# second probe: child MPI carrying a rotation+scale (the v4 child law):
# desired child world = Rz(pi) @ S(1.05) with wrapper identity
w = bpy.data.objects.new("W", None)
scene.collection.objects.link(w)                 # identity wrapper
ch = bpy.data.objects.new("CH", None)
scene.collection.objects.link(ch)
ch.parent = w
FLIP = Matrix.Rotation(3.14159265, 4, 'Z')
SCALE = Matrix.Scale(1.05, 4)
# variant A: MPI = FLIP @ SCALE
ch.matrix_parent_inverse = (FLIP @ SCALE).copy()
bpy.context.view_layer.update(); bpy.context.view_layer.update()
# mark a local +Y point: child world of basis Y-axis
va = (ch.matrix_world @ Vector((0.0, 1.0, 0.0)))
# variant B: MPI = (FLIP @ SCALE).inverted()
ch.matrix_parent_inverse = (FLIP @ SCALE).inverted()
bpy.context.view_layer.update(); bpy.context.view_layer.update()
vb = (ch.matrix_world @ Vector((0.0, 1.0, 0.0)))
print(f"child MPI variant A (MPI=FLIP@SCALE): local +Y -> world "
      f"({va.x:+.3f},{va.y:+.3f},{va.z:+.3f})  "
      f"[bind -Y means local -Y -> +{va.y*-1:+.3f} Y... facing = "
      f"{'-Y' if (ch.matrix_world @ Vector((0,-1,0))).y < 0 else '+Y'}]")
print(f"child MPI variant B (MPI=inv): local +Y -> world "
      f"({vb.x:+.3f},{vb.y:+.3f},{vb.z:+.3f})")
print("PROBE_DONE")
