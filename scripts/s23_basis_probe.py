"""s23_basis_probe.py — empirically pin Blender's pose composition.

At rest, then with ONE keyed quaternion on arm.L, measure which
identity Blender 5.2 actually evaluates:
  I1: pb.matrix == parent.matrix @ parent_rest^-1 @ bone_rest @ basis
  I2: pb.matrix == parent.matrix @ bone.matrix_local @ basis  (no rest corr)
  I3: pb.matrix == parent.matrix @ parent_rest^-1 @ bone.matrix_local @ basis
Prints BPROBE lines.
"""
import bpy, os, sys, math
from mathutils import Matrix, Quaternion, Vector

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))
import assets_quaternius  # noqa: E402


def P(*a):
    print("BPROBE", *a, flush=True)


bpy.ops.wm.read_factory_settings(use_empty=True)
rep = assets_quaternius.load("male", "HeroQ")
arm = rep["arm"]
sc = bpy.context.scene
sc.frame_set(1)
bpy.context.view_layer.update()

bone = arm.pose.bones["UpperArm.L"]
db = arm.data.bones["UpperArm.L"]
parent = bone.parent
P("bone:", bone.name, "parent:", parent.name if parent else None)

# --- rest state (basis identity) ---
I = Matrix.Identity(4)
p_rest = arm.data.bones[parent.name].matrix_local.copy()
b_rest = db.matrix_local.copy()
ppr = p_rest.inverted() @ b_rest          # parent-relative rest
def maxelem(m):
    return max(abs(v) for row in m for v in row)


P("rest check: pb.matrix == matrix_local, maxelem:",
  maxelem(bone.matrix - b_rest))

# --- keyed state: rotate UpperArm.L 90 deg about its local Y ---
q = Quaternion((0.7071, 0.0, 0.7071, 0.0))
bone.rotation_quaternion = q
sc.frame_set(1)
bpy.context.view_layer.update()

got = bone.matrix.copy()
R = q.to_matrix().to_4x4()
basis = R                                  # loc 0, scale 1
cands = {}
if parent:
    p_pose = parent.matrix.copy()
    cands["I1 parent@ppr@R"] = p_pose @ ppr @ R
    cands["I2 parent@brest@R"] = p_pose @ b_rest @ R
    cands["I3 parent@ppr_atBONE@R"] = p_pose @ ppr @ R
else:
    cands["I-root brest@R"] = b_rest @ R
for name, exp in cands.items():
    P(f"{name}: maxelem err {maxelem(exp - got):.6f}")
# what transformation IS got vs parent?
P("got rot part det:", round(got.to_3x3().determinant(), 4))
P("got translation:", tuple(round(v, 4) for v in got.translation))
P("exp I1 translation:",
  tuple(round(v, 4) for v in cands["I1 parent@ppr@R"].translation)
  if parent else None)
P("PROBE-DONE")
