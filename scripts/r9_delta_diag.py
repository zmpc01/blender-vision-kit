# R9 diagnostic: Plane.004 bbox delta + Area.001 state delta between
# loft_ext (source side) and loft_master (rebuild side).
import bpy

def survey(path, tag):
    bpy.ops.wm.open_mainfile(filepath=path)
    sc = bpy.context.scene
    print(f"== {tag} frame={sc.frame_current} fps={sc.render.fps}")
    o = bpy.data.objects.get("Plane.004")
    if o:
        dg = bpy.context.evaluated_depsgraph_get()
        oe = o.evaluated_get(dg)
        me = oe.to_mesh()
        zs = [v.co.z for v in me.vertices] if me else []
        print(f"  Plane.004 loc={tuple(round(x,4) for x in o.location)} "
              f"dim={tuple(round(x,4) for x in o.dimensions)} "
              f"eval_zrange=({min(zs):.4f},{max(zs):.4f})" if zs else "  no eval mesh")
        print(f"  modifiers: {[(m.name, m.type, m.show_viewport) for m in o.modifiers]}")
        for m in o.modifiers:
            if m.type == 'DISPLACE':
                t = getattr(m, "texture", None)
                print(f"  displace tex: {t.name if t else None} "
                      f"strength={m.strength} mid={m.mid_level}")
                if t:
                    for nd in getattr(t, "node_tree", []).nodes if getattr(t, "use_nodes", False) else []:
                        pass
            if m.type == 'PARTICLE_SYSTEM':
                ps = m.particle_systems[0] if m.particle_systems else None
                print(f"  particles: n={len(m.particle_systems)}")
        if o.data and o.data.users > 1:
            print(f"  mesh co-users: {o.data.users}")
        oe.to_mesh_clear()
    a = bpy.data.objects.get("Area.001")
    if a:
        ld = a.data
        print(f"  Area.001: energy={ld.energy} color={tuple(round(c,3) for c in ld.color)} "
              f"type={ld.type} hide={a.hide_viewport} parent={a.parent.name if a.parent else None}")
        print(f"  Area.001 collections: {[c.name for c in a.users_collection]}")
    # image state for the displace texture candidates
    for imn in ("Rope_Base Color.png",):
        im = bpy.data.images.get(imn)
        if im:
            print(f"  img {imn}: source={im.source} has_data={im.has_data} path={im.filepath[:60]}")

survey("assets/loft/loft_ext.blend", "SOURCE(loft_ext)")
survey("assets/loft/loft_master.blend", "REBUILD(loft_master)")
