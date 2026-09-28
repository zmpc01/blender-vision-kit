# ual_import_probe.py -- UAL import + inventory probe (Task UAL-1, deliverable 1).
#
# Imports the Quaternius Universal Animation Library glTF headless and dumps:
#   * object hierarchy (name, type, parent, dimensions)
#   * armature stats (bone count, rotation modes, bone names)
#   * action table (name, frame range, fcurve count, animated targets)
#   * mesh stats (verts/faces, vertex groups, material slots)
#   * NLA state on import (the 4.4+ auto-stash gotcha, AGENTS.md #25)
#
# SAVES NOTHING (print-only probe). Usage:
#   bash scripts/blrun.sh --background --python scripts/ual_test/ual_import_probe.py -- \
#        [gltf_path]   (default: assets/vendor/ual/.../AnimationLibrary_Godot_Standard.gltf)
import os
import sys
import time

import bpy

DEFAULT_GLTF = os.path.join(
    "assets", "vendor", "ual", "gltf-universal-animation-library-main",
    "glTF", "AnimationLibrary_Godot_Standard.gltf")

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
gltf_path = argv[0] if argv else DEFAULT_GLTF


def rule(title):
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


# ---- import (timed, factory-empty scene) ---------------------------------
bpy.ops.wm.read_factory_settings(use_empty=True)
t0 = time.time()
import_err = ""
try:
    bpy.ops.import_scene.gltf(filepath=gltf_path)
except Exception as e:  # noqa BLE001 -- document precisely
    import_err = f"{type(e).__name__}: {e}"
    import traceback
    traceback.print_exc()
import_s = time.time() - t0

rule(f"IMPORT  path={gltf_path}")
print(f"import_time={import_s:.2f}s  error={import_err or 'none'}  "
      f"objects={len(bpy.data.objects)}  actions={len(bpy.data.actions)}  "
      f"materials={len(bpy.data.materials)}")

arm = next((o for o in bpy.data.objects if o.type == "ARMATURE"), None)
meshes = [o for o in bpy.data.objects if o.type == "MESH"]
skinned = [o for o in meshes if o.find_armature()]

# ---- object hierarchy -----------------------------------------------------
rule("OBJECT HIERARCHY (type | dims m | parent)")

def walk(ob, depth=0):
    dims = tuple(round(c, 3) for c in ob.dimensions) if ob.type != "EMPTY" else ()
    print(f"{'  ' * depth}{ob.name}  [{ob.type}]"
          + (f"  dims={dims}" if dims else "")
          + (f"  parent={ob.parent.name}" if ob.parent and depth == 0 else ""))
    for ch in bpy.data.objects:
        if ch.parent == ob:
            walk(ch, depth + 1)

roots = [o for o in bpy.data.objects if o.parent is None]
for r in sorted(roots, key=lambda o: o.name):
    walk(r)

# ---- armature -------------------------------------------------------------
if arm:
    rule(f"ARMATURE  '{arm.name}'")
    bones = list(arm.pose.bones)
    modes = sorted({b.rotation_mode for b in bones})
    print(f"bone_count={len(bones)}  rotation_modes={modes}  "
          f"object_rotation_mode={arm.rotation_mode}")
    print(f"world_location={tuple(round(c, 3) for c in arm.matrix_world.translation)}  "
          f"world_scale={tuple(round(c, 3) for c in arm.matrix_world.to_scale())}")
    names = [b.name for b in bones]
    per = 6
    print("bone names:")
    for i in range(0, len(names), per):
        print("  " + ", ".join(f"{n:<14}" for n in names[i:i + per]))
    ad = arm.animation_data
    nla = list(ad.nla_tracks) if ad else []
    muted = sum(1 for t in nla if t.mute)
    print(f"on_import: action={ad.action.name if ad and ad.action else None}  "
          f"nla_tracks={len(nla)} (muted={muted})")
    # NLA strips apply fcurve CYCLES modifiers (gotcha #25) -- document them
    cyc = [t.name for t in nla for s in t.strips
           if any(m.type == 'CYCLES' for fc in s.action.fcurves
                  for m in fc.modifiers)]
    print(f"nla_strips_with_CYCLES_modifier={cyc or 'none'}")

# ---- action table ---------------------------------------------------------
rule(f"ACTIONS ({len(bpy.data.actions)}) -- name | frames | fcurves | targets")
rows = []
for a in sorted(bpy.data.actions, key=lambda x: x.name):
    fa, fb = a.frame_range
    paths = set(fc.data_path.split('"')[0] for fc in a.fcurves)
    tgt = "+".join(sorted(p.replace("pose.bones.", "pb.")
                            .replace("position", "loc")
                            .replace("rotation_quaternion", "quat")
                            .replace("rotation_euler", "eul")[:14]
                          for p in paths))
    rows.append((a.name, int(fa), int(fb), len(a.fcurves), tgt))
w = max(len(r[0]) for r in rows) + 2
for name, fa, fb, nfc, tgt in rows:
    print(f"{name:<{w}} f{fa:>4}-{fb:<4}  fc={nfc:<4} -> {tgt}")
kinds = {}
for _, fa, fb, _, _ in rows:
    kinds["single-frame/pose" if fb - fa <= 1 else "animated"] = \
        kinds.get("single-frame/pose" if fb - fa <= 1 else "animated", 0) + 1
print(f"[summary] {len(rows)} actions: {kinds}")

# ---- mesh stats -----------------------------------------------------------
rule("MESHES")
for m in meshes:
    slots = [s.name if s else "-" for s in m.material_slots]
    print(f"'{m.name}': verts={len(m.data.vertices)}  "
          f"faces={len(m.data.polygons)}  "
          f"vgroups={len(m.vertex_groups)}  "
          f"slots={slots}  armature={m.find_armature().name if m.find_armature() else None}")
    for slot_i, slot in enumerate(m.material_slots):
        if slot and slot.material:
            ma = slot.material
            bsdf = (ma.node_tree.nodes.get("Principled BSDF")
                    if ma.use_nodes and ma.node_tree else None)
            bc = (tuple(round(c, 3) for c in
                        bsdf.inputs["Base Color"].default_value[:3])
                  if bsdf else None)
            print(f"    slot[{slot_i}] '{ma.name}' use_nodes={ma.use_nodes} "
                  f"base_color={bc} diffuse_color={tuple(round(c, 3) for c in ma.diffuse_color)}")

# ---- material inventory ---------------------------------------------------
rule(f"MATERIALS ({len(bpy.data.materials)})")
for ma in bpy.data.materials:
    print(f"'{ma.name}'  use_nodes={ma.use_nodes}  "
          f"diffuse_color={tuple(round(c, 3) for c in ma.diffuse_color)}  "
          f"users={ma.users}")

print("\n[ual_import_probe] done (nothing saved).")
