"""r6_probe2.py — bisect the silent death: replicate validator phases with prints."""
import sys
import time
import resource

sys.path.insert(0, "/home/z/vision-work/blender-vision-kit/scripts")
import bpy  # noqa: E402
import validate_scene as vs  # noqa: E402

def rss():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024

SRC = "/home/z/vision-work/blender-vision-kit/output/r6/loft_look.blend"
bpy.ops.wm.open_mainfile(filepath=SRC)
scene = bpy.context.scene
print(f"[p2] opened meshes={len([o for o in scene.objects if o.type=='MESH'])} "
      f"rss={rss()}MB", flush=True)

t0 = time.time()
meshes = [o for o in scene.objects if o.type == 'MESH']
bounds_map = {o.name: vs._object_bounds(o) for o in meshes}
bounds_map = {k: v for k, v in bounds_map.items() if v is not None}
print(f"[p2] bounds_map built n={len(bounds_map)} t={time.time()-t0:.1f}s "
      f"rss={rss()}MB", flush=True)

t0 = time.time()
names = list(bounds_map.keys())
n_pairs = 0
n_overlaps = 0
t0b = time.time()
for i in range(len(names)):
    a = bounds_map[names[i]]
    for j in range(i + 1, len(names)):
        n_pairs += 1
        b = bounds_map[names[j]]
        if vs._bounds_overlap(a, b):
            n_overlaps += 1
    if i % 300 == 0:
        print(f"[p2]   pair-scan i={i}/{len(names)} overlaps={n_overlaps} "
              f"t={time.time()-t0b:.1f}s rss={rss()}MB", flush=True)
print(f"[p2] pair scan done pairs={n_pairs} overlaps={n_overlaps} "
      f"t={time.time()-t0b:.1f}s rss={rss()}MB", flush=True)

t0 = time.time()
report = vs.validate_scene()
print(f"[p2] full validate_scene OK t={time.time()-t0:.1f}s issues={len(report['issues'])} "
      f"rss={rss()}MB", flush=True)
