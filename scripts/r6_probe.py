"""r6_probe.py — find the LOOK OOM phase + honest validator baseline."""
import os
import sys
import resource

sys.path.insert(0, "/home/z/vision-work/blender-vision-kit/scripts")
import bpy  # noqa: E402
import validate_scene as vs  # noqa: E402

def rss():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024

SRC = "/home/z/vision-work/blender-vision-kit/output/r6/loft_look.blend"
bpy.ops.wm.open_mainfile(filepath=SRC)
scene = bpy.context.scene
print(f"[probe] opened; meshes={len([o for o in scene.objects if o.type=='MESH'])} "
      f"rss={rss()}MB", flush=True)

report = vs.validate_scene()
p0 = report["issues_by_severity"]["P0"]
p1 = report["issues_by_severity"]["P1"]
p2 = report["issues_by_severity"]["P2"]
print(f"[probe] validator P0={len(p0)} P1={len(p1)} P2={len(p2)} rss={rss()}MB",
      flush=True)
from collections import Counter
kinds = Counter(i["type"] for i in report["issues"])
print(f"[probe] issue kinds: {dict(kinds)}", flush=True)
flagged = set()
for i in report["issues"]:
    if i["severity"] in ("P0", "P1"):
        if "object" in i:
            flagged.add(i["object"])
        elif "objects" in i:
            flagged.update(i["objects"])
print(f"[probe] flagged unique objects: {len(flagged)}", flush=True)
for i in report["issues"][:10]:
    print(f"[probe]   [{i['severity']}] {i['type']} "
          f"{i.get('object', i.get('objects'))}: {i['description'][:90]}", flush=True)
