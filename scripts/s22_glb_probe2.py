"""s22_glb_probe2.py — the D6 REV-2 re-probe (audit P1-1/P1-2/P2-5).

Answers with numbers:
  Q1 BOTH meshes decimated (ratio measured to land <=3.5k combined
     verts) — the REAL per-agent mesh cost + GLB size at N=50.
  Q2 CYCLES'd walk: does the exporter sample ONLY the keyed window
     (action.frame_range) — i.e. the GLB clip stays ~38 frames?
  Q3 trimmed idle (one cycle) bind cost: GLB delta at N=50 with a
     shared trimmed idle on all agents.
  Q4 idle clip in-place drift census (hips world xy/z across the
     trimmed cycle) — the P2-5 law.
  Q5 render-hidden exclusion: the commuter anchor with
     hide_render=True stays out of the GLB (node census).
"""
import bpy, os, json, sys

sys.path.insert(0, "/home/z/lab/blender-vision-kit/scripts")
import blender_kit

RH = "/home/z/lab/RH-3d-assets"
ANIM = "/home/z/lab/RH-canvas-animations"
OUT = "/tmp/rhbind"
os.makedirs(OUT, exist_ok=True)

def P(*a):
    print("RH-GLB2", *a)

def verts_of(ob):
    return len(ob.data.vertices)

def build(n, ratio=0.14, with_idle=True):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps = 24
    sc.frame_start = 1
    sc.frame_end = 1080
    bpy.ops.import_scene.fbx(filepath=f"{RH}/assets/director/dummy-rigs/x_bot.fbx")
    arm_t = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    meshes_t = [o for o in bpy.data.objects if o.type == 'MESH']
    P("template meshes:", [(m.name, verts_of(m)) for m in meshes_t])
    for m in meshes_t:
        bpy.context.view_layer.objects.active = m
        md = m.modifiers.new("DEC", 'DECIMATE')
        md.ratio = ratio
        bpy.ops.object.modifier_apply(modifier="DEC")
    P("post-decimate:", [(m.name, verts_of(m)) for m in meshes_t],
      "combined:", sum(verts_of(m) for m in meshes_t))
    # walk clip
    before = set(bpy.data.actions)
    bpy.ops.import_scene.fbx(filepath=f"{ANIM}/assets/fbx/2899.fbx")
    walk0 = [a for a in bpy.data.actions if a not in before][0]
    f0, f1 = (int(v) for v in walk0.frame_range)
    cyc = f1 - f0
    P("walk cycle:", f0, f1, "cyc:", cyc)
    # trim idle to one cycle (64f) BEFORE binding
    if with_idle:
        before2 = set(bpy.data.actions)
        bpy.ops.import_scene.fbx(filepath=f"{ANIM}/assets/fbx/2781.fbx")
        idle0 = [a for a in bpy.data.actions if a not in before2][0]
        if0, if1 = (int(v) for v in idle0.frame_range)
        # trim: delete keys beyond f0+TRIM — collect INDICES first
        # (RNA array refs go stale after a removal; remove by index DESC)
        TRIM = 64
        for fc in blender_kit.iter_fcurves(idle0):
            doomed = [i for i, kp in enumerate(fc.keyframe_points)
                      if kp.co.x > if0 + TRIM]
            for i in reversed(doomed):
                # fresh RNA reference each removal (array reallocates)
                fc.keyframe_points.remove(fc.keyframe_points[i])
        P("idle trimmed to:", TRIM, "frames (from", if0, "..", if1, ")")
        idle0.frame_range  # noqa
    # N agents
    for i in range(n):
        anchor_mesh = meshes_t[0].copy()   # stand-in for the commuter anchor
        anchor_mesh.name = f"Zed.{i+1:04d}.anchor"
        sc.collection.objects.link(anchor_mesh)
        anchor_mesh.hide_render = True     # the D6-2 law
        arm = arm_t.copy()
        arm.name = f"Zed.{i+1:04d}.Rig"
        sc.collection.objects.link(arm)
        arm.parent = anchor_mesh
        for j, mt in enumerate(meshes_t):
            me = mt.copy()
            me.name = f"Zed.{i+1:04d}.Body{j}"
            sc.collection.objects.link(me)
            me.parent = arm
        # per-agent wrapped phase walk
        a2 = walk0.copy()
        a2.name = f"walk_{i:03d}"
        phase = (i * 0.37) % 1.0
        shift = phase * cyc
        for fc in blender_kit.iter_fcurves(a2):
            for kp in fc.keyframe_points:
                t = f0 + ((kp.co.x - f0 - shift) % cyc)
                kp.co.x = t
            # CYCLES modifier for the Blender-side loop (5.x RNA:
            # mode_before/mode_after enums + cycles_before/cycles_after)
            md = fc.modifiers.new('CYCLES')
            md.mode_before = 'NONE'
            md.mode_after = 'REPEAT'
            md.cycles_before = 0
            md.cycles_after = 5000
        arm.animation_data_create()
        arm.animation_data.action = a2
        if with_idle and i % 3 == 0:      # a third parked (readers)
            arm.animation_data.action = idle0
    P(f"built {n} agents (anchor mesh hide_render=True + rig children)")
    return f0, f1

def export(tag):
    path = f"{OUT}/crowd2_{tag}.glb"
    import argparse
    ns = argparse.Namespace(output=OUT, scene_name=f"crowd2_{tag}")
    blender_kit.export_gltf(ns, out_path=path)
    mb = os.path.getsize(path) >> 20
    P(f"GLB2 {tag} size={mb}MB ({os.path.getsize(path)} bytes)")
    # GLB json census: animations + nodes
    import struct
    with open(path, "rb") as fh:
        magic, ver, length = struct.unpack("<III", fh.read(12))
        clen, ctype = struct.unpack("<II", fh.read(8))
        j = json.loads(fh.read(clen))
    P(f"GLB2 {tag} animations={len(j.get('animations', []))} "
      f"nodes={len(j.get('nodes', []))} meshes={len(j.get('meshes', []))} "
      f"skins={len(j.get('skins', []))}")
    # the render-hidden exclusion check (Q5): no node named *.anchor
    anchors = [n.get('name', '') for n in j.get('nodes', []) if '.anchor' in n.get('name', '')]
    P(f"GLB2 {tag} anchor-nodes-in-glb={len(anchors)} (law: 0)")
    # animation clip durations (Q2): sample the first walk animation's
    # max input accessor count
    if j.get('animations'):
        a0 = j['animations'][0]
        maxsam = 0
        for ch in a0.get('channels', [])[:5]:
            acc = j['accessors'][j['samplers'][ch['sampler']]['input']]
            maxsam = max(maxsam, acc['count'])
        P(f"GLB2 {tag} anim[0]={a0.get('name','?')} max-input-keys={maxsam} (law: ~cyc)")
    return mb

# Q1+Q2+Q3+Q5: N=50, ratio 0.14, idle on a third
f0, f1 = build(50, ratio=0.14, with_idle=True)
export("mix50")

# Q4: idle drift census (hips world xy/z across trimmed cycle)
bpy.context.view_layer.update()
_candidates = [o for o in bpy.data.objects if o.type == 'ARMATURE'
               and o.animation_data and o.animation_data.action
               and o.animation_data.action.name != 'walk_049']
arm = next(o for o in _candidates
           if 'standby' in o.animation_data.action.name.lower()
           or o.animation_data.action is not None
           and o.name != 'Zed.001.Rig' and 'walk_' not in o.animation_data.action.name)
P("idle drift on:", arm.name, arm.animation_data.action.name)
sc = bpy.context.scene
pts = []
for f in range(1, 65, 8):
    sc.frame_set(f)
    bpy.context.view_layer.update()
    hips = arm.pose.bones.get("mixamorig:Hips")
    w = arm.matrix_world @ hips.matrix
    pts.append((round(w.x, 3), round(w.y, 3), round(w.z, 3)))
P("idle hips xyz @1,9,...,57:", pts)
dx = max(p[0] for p in pts) - min(p[0] for p in pts)
dy = max(p[1] for p in pts) - min(p[1] for p in pts)
dz = max(p[2] for p in pts) - min(p[2] for p in pts)
P(f"idle drift dx={dx:.3f} dy={dy:.3f} dz={dz:.3f} (law: < 0.05 in-place)")

P("PROBE2-DONE")
