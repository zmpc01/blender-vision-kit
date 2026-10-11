import bpy

def survey(path, tag):
    bpy.ops.wm.open_mainfile(filepath=path)
    print(f"== {tag}")
    print("  LIGHT DATA:", [(l.name, l.type, round(l.energy, 2),
                             tuple(round(c, 3) for c in l.color),
                             l.users)
                            for l in bpy.data.lights])
    for o in bpy.data.objects:
        if o.type == 'LIGHT':
            print(f"  OBJ {o.name} -> data {o.data.name} "
                  f"energy={round(o.data.energy, 2)} "
                  f"col={tuple(round(c, 3) for c in o.data.color)} "
                  f"size={round(o.data.size, 3)}")
    # the displace texture chain
    for t in bpy.data.textures:
        print(f"  TEXTURE {t.name} type={t.type} "
              f"image={t.image.name if t.image else None} "
              f"users={t.users}")

survey("assets/loft/loft_ext.blend", "SOURCE")
survey("assets/loft/loft_master.blend", "REBUILD")
