"""s22_bind_probe.py — can the RH-canvas-animations clips drive the
RH-3d-assets dummy rigs DIRECTLY (same-name mixamorig bones)?

Law under test: Mixamo-65 -> Mixamo-65 same-name action transfer.
  1. import x_bot (65 mixamorig)
  2. import clip 2899 (male standard walk, 38f)
  3. compare bone-name sets (the exact-match law)
  4. transfer the action to x_bot's armature (same paths), sample
     world hips-z + foot-z at 4 frames (the s20 numeric law), render
     a 2x2 strip to /tmp/rhbind/strip.png
  5. ALSO: male_body (78-bone) compatibility census vs the clip (the
     78 vs 65 delta = which 13 extra bones?)
Prints RH-BIND lines. Fail-closed on any mismatch.
"""
import bpy, os, json, math
from mathutils import Vector

RH = "/home/z/lab/RH-3d-assets"
ANIM = "/home/z/lab/RH-canvas-animations"
OUT = "/tmp/rhbind"
os.makedirs(OUT, exist_ok=True)

def P(*a):
    print("RH-BIND", *a)

bpy.ops.wm.read_factory_settings(use_empty=True)

# 1. x_bot
bpy.ops.import_scene.fbx(filepath=f"{RH}/assets/director/dummy-rigs/x_bot.fbx")
xb_arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
xb_bones = {b.name for b in xb_arm.data.bones}
P("xb_bot bones:", len(xb_bones))

# 2. clip
before = set(bpy.data.actions)
bpy.ops.import_scene.fbx(filepath=f"{ANIM}/assets/fbx/2899.fbx")
clip_arm = [o for o in bpy.data.objects if o.type == 'ARMATURE' and o != xb_arm][-1]
new_act = [a for a in bpy.data.actions if a not in before][0]
clip_bones = {b.name for b in clip_arm.data.bones}
P("clip bones:", len(clip_bones), "action:", new_act.name, "range:", tuple(new_act.frame_range))

# 3. name-set law
missing = clip_bones - xb_bones
extra = xb_bones - clip_bones
P("names: clip-not-in-xbot:", len(missing), "xbot-not-in-clip:", len(extra))
if missing:
    P("missing sample:", json.dumps(sorted(missing)[:8]))
if extra:
    P("extra sample:", json.dumps(sorted(extra)[:8]))

# male_body vs xbot delta
bpy.ops.import_scene.fbx(filepath=f"{RH}/assets/director/dummy-rigs/male_body.fbx")
mb_arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][-1]
mb_bones = {b.name for b in mb_arm.data.bones}
P("male_body bones:", len(mb_bones), "clip-not-in-male:", len(clip_bones - mb_bones),
  "male-not-in-clip:", len(mb_bones - clip_bones))

# 4. transfer: bind the CLIP action onto x_bot (slot copy law for 5.x)
import blender_kit  # PYTHONPATH=scripts
if xb_arm.animation_data is None:
    xb_arm.animation_data_create()
xb_arm.animation_data.action = new_act
P("bound:", xb_arm.animation_data.action.name)

sc = bpy.context.scene
sc.frame_set(1)
bpy.context.view_layer.update()

def hips_world_z(arm):
    for nm in ("mixamorig:Hips", "Hips"):
        pb = arm.pose.bones.get(nm)
        if pb:
            w = arm.matrix_world @ pb.matrix
            return w.translation.z
    return None

def foot_world_z(arm, side):
    nm = f"mixamorig:{side}Foot" if f"mixamorig:{side}Foot" in xb_arm.pose.bones else f"{side}Foot"
    pb = xb_arm.pose.bones.get(nm)
    if pb:
        w = xb_arm.matrix_world @ pb.matrix
        return w.translation.z
    return None

P("hips z @f1/f10/f20/f30:",
  [round(hips_world_z(xb_arm) or -1, 3)])
seq_h, seq_l, seq_r = [], [], []
for f in (1, 10, 20, 30, 38):
    sc.frame_set(f)
    bpy.context.view_layer.update()
    seq_h.append(round(hips_world_z(xb_arm) or -1, 3))
    seq_l.append(round(foot_world_z(xb_arm, "Left") or -1, 3))
    seq_r.append(round(foot_world_z(xb_arm, "Right") or -1, 3))
P("walk hips-z seq:", seq_h)
P("footL z seq:", seq_l)
P("footR z seq:", seq_r)

# strip render: 2x2 workbench at f1/10/20/30, camera 3/4 view
cam_data = bpy.data.cameras.new("PC"); cam = bpy.data.objects.new("PC", cam_data)
sc.collection.objects.link(cam); sc.camera = cam
cam.location = (2.2, -2.6, 1.5)
cam.rotation_euler = (math.radians(70), 0, math.radians(40))
sun = bpy.data.lights.new("S", 'SUN'); sun_ob = bpy.data.objects.new("S", sun)
sc.collection.objects.link(sun_ob); sun_ob.rotation_euler = (math.radians(50), 0, math.radians(30))
sc.render.engine = 'BLENDER_WORKBENCH'
sc.display.shading.light = 'STUDIO'
sc.display.shading.color_type = 'MATERIAL'
sc.render.resolution_x = 320; sc.render.resolution_y = 400
sc.render.image_settings.file_format = 'PNG'
cells = []
for f in (1, 10, 20, 30):
    sc.frame_set(f)
    p = f"{OUT}/c{f}.png"
    sc.render.filepath = p
    bpy.ops.render.render(write_still=True)
    cells.append(p)
P("cells:", cells)

# also render male_body bound to the clip for the 78-bone question
mb_arm.animation_data_create()
mb_arm.animation_data.action = new_act
sc.render.resolution_x = 320
cells2 = []
for f in (1, 10, 20, 30):
    sc.frame_set(f)
    p = f"{OUT}/m{f}.png"
    sc.render.filepath = p
    bpy.ops.render.render(write_still=True)
    cells2.append(p)
P("male cells:", cells2)
P("PROBE-DONE")
