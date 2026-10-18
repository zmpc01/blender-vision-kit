"""s22_asset_probe.py — the humanoid-upgrade recon probe (read-only).

Census of every candidate humanoid family, ONE headless run:
  A. RH-3d-assets dummy-rig FBXs (male_body / female_body / x_bot)
  B. RH-canvas-animations clips (2899 male standard walk, 2781 idle)
  C. RW character glTFs (Armor-Qin, Farmer, Police, Scholar, CW-01, Doctor-06)
  D. UAL mannequin (the vendored loader's one glTF) -- census only

Per family: object tree, armature bone census (name prefix + count),
mesh poly counts, measured height (world bbox), animation presence
(actions + frame ranges), and for imported animations the BONE NAMES
they drive (the retarget-vs-direct-bind decision data).

Prints RH-PROBE lines only (grep-able). No scene mutation survives.
"""
import bpy, os, sys, json

RH = "/home/z/lab/RH-3d-assets"
ANIM = "/home/z/lab/RH-canvas-animations"

def P(*a):
    print("RH-PROBE", *a)

def purge():
    bpy.ops.wm.read_factory_settings(use_empty=True)

def census(tag):
    P(f"--- {tag} ---")
    arms = [o for o in bpy.data.objects if o.type == 'ARMATURE']
    meshes = [o for o in bpy.data.objects if o.type == 'MESH']
    for a in arms:
        bones = a.data.bones
        prefixes = {}
        for b in bones:
            pre = b.name.split(':')[0] if ':' in b.name else (
                  b.name.split('_')[0] if b.name.startswith('DEF-') else
                  b.name.split('.')[0] if '.' in b.name and len(b.name.split('.')[0]) <= 6 else b.name)
            prefixes[pre] = prefixes.get(pre, 0) + 1
        top = sorted(prefixes.items(), key=lambda kv: -kv[1])[:4]
        P(f"{tag} ARMATURE {a.name} bones={len(bones)} prefixes={top}")
        # measured height from evaluated bbox
        bpy.context.view_layer.update()
        zs = [(a.matrix_world @ __import__('mathutils').Vector(c)) for c in a.bound_box]
        P(f"{tag} ARMATURE_H {a.name} z={min(v.z for v in zs):.3f}..{max(v.z for v in zs):.3f}")
    for m in meshes:
        me = m.data
        P(f"{tag} MESH {m.name} verts={len(me.vertices)} polys={len(me.polygons)} "
          f"mats={len(me.materials)} armature={'Y' if m.find_armature() else 'N'}")
        if me.materials:
            mt = me.materials[0]
            tex = "Y" if (mt and mt.use_nodes and any(n.type == 'TEX_IMAGE' for n in mt.node_tree.nodes)) else "N"
            P(f"{tag} TEX {m.name} imagetex={tex}")
    acts = [ac for ac in bpy.data.actions if ac.users]
    for ac in acts[:6]:
        try:
            fr = ac.frame_range
        except Exception:
            fr = ("?", "?")
        P(f"{tag} ACTION {ac.name} range={fr[0]:.0f}..{fr[1]:.0f}")
    P(f"{tag} actions_total={len(acts)}")

def probe_fbx(path, tag, do_anim=False):
    purge()
    try:
        bpy.ops.import_scene.fbx(filepath=path)
    except Exception as e:
        P(f"{tag} IMPORT_FAIL {e}")
        return
    census(tag)
    if do_anim:
        # which bones does the FIRST action drive?
        ac = next((a for a in bpy.data.actions if a.users), None)
        if ac:
            try:
                paths = sorted({fc.data_path.split('"')[1] for fc in __import__('blender_kit').iter_fcurves(ac)
                                if '"' in fc.data_path})[:80]
            except Exception:
                paths = sorted({fc.data_path.split('"')[1] for ac2 in bpy.data.actions
                                for fc in getattr(ac2, 'fcurves', []) if '"' in fc.data_path})[:80]
            P(f"{tag} ANIM_BONES n={len(paths)}")
            P(f"{tag} ANIM_BONE_NAMES {json.dumps(paths)}")

# A. dummy rigs
probe_fbx(f"{RH}/assets/director/dummy-rigs/male_body.fbx", "RH_MALE")
probe_fbx(f"{RH}/assets/director/dummy-rigs/female_body.fbx", "RH_FEMALE")
probe_fbx(f"{RH}/assets/director/dummy-rigs/x_bot.fbx", "RH_XBOT")

# B. animation clips (import alone: what rig do they assume?)
probe_fbx(f"{ANIM}/assets/fbx/2899.fbx", "CLIP_WALK2899")
probe_fbx(f"{ANIM}/assets/fbx/2781.fbx", "CLIP_IDLE2781")

# C. RW character glTFs
for name, fn in [("ARMOR_QIN", "ab0e748d-8ec0-4fef-8daf-7249d9e0da00.gltf"),
                 ("FARMER", "3dacd73f-92d0-4390-a742-3f4f5e428859.gltf"),
                 ("POLICE", "681a2195-99fb-4f89-b500-2dc5d4d886cf.gltf"),
                 ("SCHOLAR", "d563b238-a2ab-4c33-b356-c1483ed78bee.gltf"),
                 ("CW01", "14f0102a-b7bc-4ed7-a508-102259ffda15.gltf")]:
    purge()
    try:
        bpy.ops.import_scene.gltf(filepath=f"{RH}/assets/director/models/{fn}")
    except Exception as e:
        P(f"RW_{name} IMPORT_FAIL {e}")
        continue
    census(f"RW_{name}")

# D. UAL mannequin census
purge()
try:
    bpy.ops.import_scene.gltf(filepath="/home/z/lab/blender-vision-kit/assets/vendor/ual/"
                              "gltf-universal-animation-library-main/glTF/"
                              "AnimationLibrary_Godot_Standard.gltf")
    census("UAL")
except Exception as e:
    P("UAL IMPORT_FAIL", e)

P("PROBE-DONE")
