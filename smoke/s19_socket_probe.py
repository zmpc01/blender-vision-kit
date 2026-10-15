"""s19_socket_probe.py — confirm/refute the film lane's NEW LAW (5.x):
socket-level keyframe_insert silently no-ops on material trees (returns
True, creates NO action); the node_tree-rooted explicit data_path is the
reliable form. Runs bare (30s)."""
import bpy

scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end = 24

mat = bpy.data.materials.new("Probe")
mat.use_nodes = True
nt = mat.node_tree
bsdf = nt.nodes.get("Principled BSDF")

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from blender_kit import iter_all_fcurves


def n_fcurves(tag):
    # s19 lesson: in 5.x the node_tree is its OWN ID block — the action
    # lands on nt.animation_data, NOT mat.animation_data (the film lane's
    # assert reads BOTH owners for exactly this reason).
    n_mat = 0
    ad = mat.animation_data
    if ad and ad.action:
        n_mat = len(list(iter_all_fcurves(ad.action)))
    n_nt = 0
    paths = []
    adnt = getattr(nt, "animation_data", None)
    if adnt and adnt.action:
        fcs = list(iter_all_fcurves(adnt.action))
        n_nt = len(fcs)
        paths = [fc.data_path for fc in fcs][:3]
    print(f"[probe] {tag}: mat-owner={n_mat} node_tree-owner={n_nt} "
          f"paths={paths}")
    return n_mat + n_nt


# form A: socket-level (the law: silently no-ops on 5.x — ret=True, no action)
sock = bsdf.inputs["Emission Color"]
r = sock.keyframe_insert("default_value", frame=1)
n_a = n_fcurves(f"A socket.keyframe_insert (ret={r})")

# form C: node_tree-rooted explicit data_path (the film lane's _em_keys form)
sock2 = bsdf.inputs["Emission Strength"]
idx = list(bsdf.inputs).index(sock2)
path = f'nodes["{bsdf.name}"].inputs[{idx}].default_value'
r = nt.keyframe_insert(data_path=path, frame=12)
n_c = n_fcurves(f"C node_tree.keyframe_insert (ret={r})")

verdict = ("CONFIRMED" if (n_a == 0 and n_c > 0) else
           "REFUTED" if n_a > 0 else "BOTH-DEAD")
print(f"[probe] VERDICT: A contributed {n_a}, C contributed {n_c} — law {verdict}")
