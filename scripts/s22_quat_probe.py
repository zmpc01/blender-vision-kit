"""s22_quat_probe.py — D2 first-run truth measurement (Quaternius family).

Imports each vendored FBX ONCE, measures the loader's pinned constants:
  raw mesh height (world bbox of the SKINNED MESH — the armature bone-box
  lies below ground via IK helpers), feet z, top z, forward axis via
  Foot.L +Y (the D1 probe law data), mesh.parent, action diff.
Prints QPROBE lines; read-only.
"""
import bpy, os, sys, json, math
from mathutils import Vector

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(_REPO, "assets", "vendor", "quaternius")


def P(*a):
    print("QPROBE", *a, flush=True)


def probe(tag, path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    bpy.ops.import_scene.fbx(filepath=path)
    arms = [o for o in bpy.data.objects if o.type == 'ARMATURE']
    meshes = [o for o in bpy.data.objects if o.type == 'MESH']
    P(f"--- {tag} ---")
    P("objects:", [(o.name, o.type) for o in bpy.data.objects])
    for a in arms:
        P("armature:", a.name, "bones:", len(a.data.bones),
          "parent:", a.parent.name if a.parent else None)
    for m in meshes:
        arm = m.find_armature()
        P("mesh:", m.name, "verts:", len(m.data.vertices),
          "find_armature:", arm.name if arm else None,
          "parent:", m.parent.name if m.parent else None)
        # WORLD bbox from evaluated verts (the honest box)
        mw = m.matrix_world
        zs = [(mw @ v.co).z for v in m.data.vertices]
        ys = [(mw @ v.co).y for v in m.data.vertices]
        xs = [(mw @ v.co).x for v in m.data.vertices]
        P("mesh world bbox: z[%.4f, %.4f] y[%.4f, %.4f] x[%.4f, %.4f]"
          % (min(zs), max(zs), min(ys), max(ys), min(xs), max(xs)))
        P("raw_height:", round(max(zs) - min(zs), 4),
          "feet_z:", round(min(zs), 4))
        P("mesh scale:", tuple(round(v, 4) for v in m.scale),
          "obj rot:", tuple(round(math.degrees(x), 2) for x in m.rotation_euler))
    arm = arms[0]
    # facing: Foot.L local +Y mapped to world (as-imported)
    foot = arm.pose.bones.get("Foot.L")
    if foot:
        m = arm.matrix_world @ foot.matrix
        fwd = (m.to_3x3() @ Vector((0, 1, 0))).normalized()
        P("Foot.L +Y world fwd:", [round(c, 4) for c in fwd],
          "|z|:", round(abs(fwd.z), 3), "|y|:", round(abs(fwd.y), 3))
        # also -Y for the record
        fwd2 = -fwd
        P("Foot.L -Y world fwd:", [round(c, 4) for c in fwd2])
        # and local +Z (roll axis) for the record
        fwdz = (m.to_3x3() @ Vector((0, 0, 1))).normalized()
        P("Foot.L +Z world fwd:", [round(c, 4) for c in fwdz])
    # rest bone-box z range (the armature-space data extent)
    bzs = [arm.matrix_world @ b.matrix_local.translation for b in arm.data.bones]
    P("bone rest z range: [%.4f, %.4f]"
      % (min(v.z for v in bzs), max(v.z for v in bzs)))
    acts = [a.name for a in bpy.data.actions]
    P("actions:", len(acts), json.dumps(acts[:3]))
    ad = arm.animation_data
    P("arm_action_on_import:", ad.action.name if ad and ad.action else None)
    P("arm object scale:", tuple(round(v, 4) for v in arm.scale),
      "rot:", tuple(round(math.degrees(x), 2) for x in arm.rotation_euler))
    P("PROBE-DONE", tag)


for key, fn in (("male", "Male_Casual.fbx"), ("female", "Female_Casual.fbx")):
    probe(key, os.path.join(ASSETS, fn))
