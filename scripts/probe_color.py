import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
m = bpy.data.materials.new("m_red")
m.use_nodes = True
nt = m.node_tree
print("PROBE nodes:", [(n.name, n.type) for n in nt.nodes])
print("PROBE links:", [(l.from_node.name, l.from_socket.name, l.to_node.name, l.to_socket.name) for l in nt.links])
bsdf = nt.nodes.get("Principled BSDF")
print("PROBE bsdf found:", bsdf is not None)
if bsdf:
    bsdf.inputs["Base Color"].default_value = (0.75, 0.05, 0.05, 1.0)
    bc = bsdf.inputs["Base Color"]
    print("PROBE base color now:", tuple(round(v,3) for v in bc.default_value), "linked:", bc.is_linked)
bpy.ops.mesh.primitive_cube_add(location=(0,0,0))
o = bpy.context.active_object
o.data.materials.append(m)
print("PROBE slot mats:", [s.material.name if s.material else None for s in o.material_slots])
bpy.ops.object.light_add(type='SUN', location=(3,-3,5))
bpy.ops.object.camera_add(location=(3,-3,2.5), rotation=(1.1,0,0.785))
bpy.context.scene.camera = bpy.context.active_object
bpy.context.scene.render.resolution_x = 160
bpy.context.scene.render.resolution_y = 120
bpy.context.scene.render.filepath = "/tmp/probe_red.png"
bpy.ops.render.render(write_still=True)
from PIL import Image
img = Image.open("/tmp/probe_red.png")
print("PROBE center px:", img.getpixel((80, 70)))
print("PROBE unique-ish:", sorted(set(img.getdata()))[:6], "...")
