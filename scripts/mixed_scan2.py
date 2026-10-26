#!/usr/bin/env python3
"""mixed_scan2.py — the FULL bake-trigger census across EVERY animation
owner the glTF exporter reads: actions (object-level), material node
trees, world node trees, lights, node groups, shape keys. Reports both
trigger classes: mixed interpolation AND non-integer key times."""
import os
import sys


def rss_mb():
    with open("/proc/self/status") as f:
        for line in f:
            if line.startswith("VmRSS"):
                return int(line.split()[1]) / 1024.0
    return -1.0


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blender_kit                                      # noqa: E402
import scene_terminal_dawn as SNM                        # noqa: E402

print(f"[scan] start rss={rss_mb():.0f}MB", flush=True)
ctx = SNM.build_scene()
SNM.animate(ctx, with_crowd=True)
print(f"[scan] after animate rss={rss_mb():.0f}MB — scanning", flush=True)

import bpy                                              # noqa: E402


def fcs_of(ad):
    try:
        return list(blender_kit.iter_fcurves(ad.action))
    except Exception:
        return []


def scan(owner_name, ad):
    hits = []
    for fc in fcs_of(ad):
        modes = {kp.interpolation for kp in fc.keyframe_points}
        if len(modes) > 1:
            hits.append(("MIXED-INTERP", fc.data_path, fc.array_index,
                         sorted(str(m) for m in modes)))
        if any(abs(kp.co.x - round(kp.co.x)) > 1e-6
               for kp in fc.keyframe_points):
            hits.append(("FLOAT-TIME", fc.data_path, fc.array_index,
                         [f"{kp.co.x:.3f}" for kp in fc.keyframe_points
                          ][:4]))
    for h in hits[:6]:
        print(f"[scan] {owner_name}: {h[0]} {h[1]}[{h[2]}] {h[3]}",
              flush=True)
    return len(hits)


total = 0
for act in bpy.data.actions:
    ad = type("A", (), {"action": act})()
    total += scan(f"action {act.name!r}", ad)
for m in bpy.data.materials:
    nt = getattr(m, "node_tree", None)
    if nt and nt.animation_data and nt.animation_data.action:
        total += scan(f"mat {m.name!r}", nt.animation_data)
w = bpy.context.scene.world
if w and w.node_tree and w.node_tree.animation_data and \
        w.node_tree.animation_data.action:
    total += scan("WORLD", w.node_tree.animation_data)
for ob in bpy.data.objects:
    ad = getattr(ob, "animation_data", None)
    if ad and ad.action:
        total += scan(f"obj {ob.name!r}", ad)
    if ob.type == 'LIGHT' and ob.data.node_tree and \
            ob.data.node_tree.animation_data and \
            ob.data.node_tree.animation_data.action:
        total += scan(f"light {ob.name!r}", ob.data.node_tree.animation_data)
    sk = getattr(ob.data, "shape_keys", None)
    if sk and sk.animation_data and sk.animation_data.action:
        total += scan(f"shapekeys {ob.name!r}", sk.animation_data)
for ng in bpy.data.node_groups:
    if ng.animation_data and ng.animation_data.action:
        total += scan(f"nodegroup {ng.name!r}", ng.animation_data)
print(f"[scan] TOTAL bake-trigger channels: {total}", flush=True)
print(f"[scan] done rss={rss_mb():.0f}MB", flush=True)
