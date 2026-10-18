"""s22_glb_probe.py — the export-budget probe (GLB size law for
skinned crowds).

Builds N linked-duplicate skinned agents (ONE mesh datablock, ONE
armature datablock, per-agent phase-shifted walk actions), exports
GLB, measures. Also probes the decimate law on x_bot.

Questions answered (numbers travel):
  Q1 GLB size vs N (10/25/50 agents, x_bot full 24.7k verts)
  Q2 GLB size with DECIMATED mesh (~6k verts)
  Q3 does the exporter INSTANCE linked skinned meshes (size/N linear?)
  Q4 per-agent phase-shifted actions: do they all export?
"""
import bpy, os, json, sys

sys.path.insert(0, "/home/z/lab/blender-vision-kit/scripts")
import blender_kit

RH = "/home/z/lab/RH-3d-assets"
ANIM = "/home/z/lab/RH-canvas-animations"
OUT = "/tmp/rhbind"
os.makedirs(OUT, exist_ok=True)

def P(*a):
    print("RH-GLB", *a)

def build_crowd(n, decimate=None, clip_path=f"{ANIM}/assets/fbx/2899.fbx"):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    # the rig template
    bpy.ops.import_scene.fbx(filepath=f"{RH}/assets/director/dummy-rigs/x_bot.fbx")
    arm_t = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    mesh_t = next(o for o in bpy.data.objects if o.type == 'MESH')
    if decimate:
        md = mesh_t.modifiers.new("DEC", 'DECIMATE')
        md.ratio = decimate
        bpy.context.view_layer.objects.active = mesh_t
        bpy.ops.object.modifier_apply(modifier="DEC")
    P("template verts:", len(mesh_t.data.vertices))
    # the walk clip
    before = set(bpy.data.actions)
    bpy.ops.import_scene.fbx(filepath=clip_path)
    act0 = [a for a in bpy.data.actions if a not in before][0]
    f0, f1 = int(act0.frame_range[0]), int(act0.frame_range[1])
    cyc = f1 - f0
    # N agents: linked mesh + linked armature data, per-agent action copy
    agents = []
    for i in range(n):
        arm = arm_t.copy()          # shares .data by default
        me = mesh_t.copy()          # shares mesh data
        me.name = f"agent_{i:03d}"
        arm.name = f"agent_{i:03d}.Rig"
        sc.collection.objects.link(arm)
        me.parent = arm
        sc.collection.objects.link(me)
        # per-agent phase: copy action, shift keys by -phase*cyc (mod cyc)
        a2 = act0.copy()
        a2.name = f"walk_{i:03d}"
        shift = -((i * 0.37) % 1.0) * cyc
        for fc in blender_kit.iter_fcurves(a2):
            for kp in fc.keyframe_points:
                kp.co.x += shift
        arm.animation_data_create()
        arm.animation_data.action = a2
        agents.append((arm, me))
    P(f"built {n} agents (linked data, per-agent actions)")
    return agents

def export_and_measure(tag, n):
    path = f"{OUT}/crowd_{tag}.glb"
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB',
                              export_animations=True,
                              export_skins=True,
                              export_apply=False)
    mb = os.path.getsize(path) >> 20
    P(f"GLB {tag} N={n} size={mb}MB ({os.path.getsize(path)} bytes)")
    return mb

# Q1: full-res x_bot, 10/25/50
for n in (10, 25, 50):
    build_crowd(n)
    export_and_measure("full", n)

# Q2: decimated to ~6k (ratio 0.25)
build_crowd(50, decimate=0.25)
export_and_measure("dec25", 50)

P("PROBE-DONE")
