"""Headless validation for polyhaven.py. Run with blrun.sh:
    blrun.sh --background --python test_polyhaven.py
Checks: metric units, HDRI world load, glTF model import (metres, Z-up),
and material append from a downloaded texture .blend."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("POLYHAVEN_CACHE", "/tmp/polyhaven_cache")

import bpy
import polyhaven as ph

ph.ensure_metric_units()
us = bpy.context.scene.unit_settings
assert us.system == "METRIC" and abs(us.scale_length - 1.0) < 1e-6
print("OK units:", us.system, us.scale_length, flush=True)

hdri = ph.download_asset("sunset_jhbcentral", fmt="hdri", resolution="1k", ext="hdr")
ph.load_hdri(hdri, strength=1.2, rotation_z=1.0)
env = next(n for n in bpy.context.scene.world.node_tree.nodes if n.type == "TEX_ENVIRONMENT")
assert env.image.size[0] == 1024
print("OK hdri:", env.image.name, env.image.size[0], "x", env.image.size[1], flush=True)

before = set(bpy.data.objects)
ph.import_model(ph.download_asset("dirty_football", fmt="gltf", resolution="1k"))
new = [o for o in bpy.data.objects if o not in before]
assert new, "no object imported"
o = new[0]
bb = [o.matrix_world @ v.co for v in o.data.vertices]
zs = [v.z for v in bb]
span = max(zs) - min(zs)
assert 0.20 < span < 0.24, f"unexpected soccer-ball size {span} (expect ~0.22 m)"
print(f"OK model: {o.name} height={span:.3f} m (sits at z={min(zs):.3f})", flush=True)

mat = ph.apply_texture_material(ph.download_asset("concrete_floor_01", fmt="blend", resolution="1k"))
assert mat and mat.name == "concrete_floor_01"
print("OK material appended:", mat.name, flush=True)

print("ALL VALIDATION PASSED", flush=True)
