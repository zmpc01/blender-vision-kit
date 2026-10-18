"""s23_closure_diag.py — WHERE does the closure error live?

Per mapped bone, per sampled frame: translation error norm + rotation
angle between expected (D_s @ M_tgt_rest) and got (evaluated pb.matrix).
Prints CLOS lines.
"""
import bpy, os, sys, math
from mathutils import Vector

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))
import assets_ual_actors as ual        # noqa: E402
import assets_quaternius               # noqa: E402
import rig_retarget                    # noqa: E402


def P(*a):
    print("CLOS", *a, flush=True)


bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.render.fps = 30
u = ual._import_actor("Driver", ual.ACTOR_SCALE)
rep = assets_quaternius.load("male", "HeroQ")
src_arm, walk = u["armature"], u["actions"]["Walk_Loop"]
tgt_arm = rep["arm"]
r = rig_retarget.retarget(src_arm, walk, tgt_arm)
out = r["action"]

sf, tf = "rigify53", "quaternius42"
sspec, tspec = rig_retarget.FAMILIES[sf], rig_retarget.FAMILIES[tf]
pairs = {}
for cls, sb in sspec["bones"].items():
    tb = tspec.get("bones", {}).get(cls) if isinstance(tspec, dict) else None
    tb = tspec["bones"].get(cls)
    if tb and sb in src_arm.data.bones and tb in tgt_arm.data.bones:
        pairs[cls] = (sb, tb)

ad_s = src_arm.animation_data
ad_t = tgt_arm.animation_data
prev_s, prev_t = ad_s.action, ad_t.action
rig_retarget._assign_action(src_arm, walk)
rig_retarget._assign_action(tgt_arm, out)
sc = bpy.context.scene
sample = [10]
CHAIN = ["hips", "spine", "spine2", "shoulder.L", "arm.L",
         "forearm.L", "hand.L"]
for f in sample:
    sc.frame_set(f)
    bpy.context.view_layer.update()
    for cls in CHAIN:
        if cls not in pairs:
            P(f"f={f} {cls}: NOT MAPPED")
            continue
        sb, tb = pairs[cls]
        D_s = (src_arm.pose.bones[sb].matrix
               @ src_arm.data.bones[sb].matrix_local.inverted())
        expected = D_s @ tgt_arm.data.bones[tb].matrix_local
        got = tgt_arm.pose.bones[tb].matrix
        terr = (expected.translation - got.translation).length
        qe = expected.to_quaternion().rotation_difference(
            got.to_quaternion()).angle
        P(f"f={f} {cls:12s} terr={terr:8.4f} rot={math.degrees(qe):7.3f} "
          f"|Ds_t|={D_s.translation.length:7.4f} "
          f"exp_t={tuple(round(v,3) for v in expected.translation)} "
          f"got_t={tuple(round(v,3) for v in got.translation)}")
rig_retarget._assign_action(src_arm, prev_s)
rig_retarget._assign_action(tgt_arm, prev_t)
P("DIAG-DONE")
