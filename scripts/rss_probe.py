#!/usr/bin/env python3
"""rss_probe.py — measure blender RSS at bind stages (the tmarket OOM
investigation). Build + bind only, NO render. Prints VmRSS after:
build_scene, bind_crowd, principals, and (for reference) the datablock
census of the heavy collections."""
import os
import sys


def rss_mb():
    with open("/proc/self/status") as f:
        for line in f:
            if line.startswith("VmRSS"):
                return int(line.split()[1]) / 1024.0
    return -1.0


def census(tag):
    import bpy
    parts = []
    for coll in ("meshes", "armatures", "actions", "objects"):
        n = len(getattr(bpy.data, coll))
        parts.append(f"{coll}={n}")
    # mesh-data vertex census (the live weight)
    verts = sum(len(m.vertices) for m in bpy.data.meshes)
    sk = sum(1 for m in bpy.data.meshes if m.shape_keys)
    fc = 0
    for a in bpy.data.actions:
        try:
            fc += sum(1 for _ in a.fcurves)
        except Exception:
            pass
    print(f"[rss] {tag}: rss={rss_mb():.0f}MB {' '.join(parts)} "
          f"verts={verts} shaped_meshes={sk} fcurves={fc}", flush=True)


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene_night_market as SNM          # noqa: E402

print(f"[rss] start: rss={rss_mb():.0f}MB", flush=True)
ctx = SNM.build_scene()
census("after build_scene")
SNM.animate(ctx, with_crowd=True)
census("after animate (bind+principals)")
print("[rss] DONE", flush=True)
