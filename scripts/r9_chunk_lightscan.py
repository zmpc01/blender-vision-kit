import bpy, glob
for p in sorted(glob.glob("assets/loft/chunks/*.blend")):
    with bpy.data.libraries.load(p, link=False) as (src, _):
        lights = list(src.lights)
        if lights:
            print("CHUNK", p.split("/")[-1], "lights:", lights)
# now open each chunk with lights and print values
for p in sorted(glob.glob("assets/loft/chunks/*.blend")):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(p, link=False) as (src, ctx):
        ctx.lights = list(src.lights)
        ctx.objects = list(src.objects)
    for o in bpy.data.objects:
        if o.type == 'LIGHT':
            print(f"IN {p.split('/')[-1]}: OBJ {o.name} -> data {o.data.name} "
                  f"energy={round(o.data.energy, 2)} size={round(o.data.size, 3)}")
