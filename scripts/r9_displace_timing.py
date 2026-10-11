# R9: is the Plane.004 delta an evaluation-timing artifact (lazy image
# load) or a data defect? Load the displacement image EXPLICITLY, then
# evaluate — both files should then agree.
import bpy

IMG = "ujlndfvn_2K_Displacement.jpg"

def probe(path, tag, preload):
    bpy.ops.wm.open_mainfile(filepath=path)
    if preload:
        im = bpy.data.images.get(IMG)
        if im is not None:
            _ = len(im.pixels)  # force pixel load
            print(f"  [{tag}] preloaded {IMG}: has_data={im.has_data} "
                  f"size={list(im.size)}")
        else:
            print(f"  [{tag}] {IMG} MISSING")
    o = bpy.data.objects["Plane.004"]
    dg = bpy.context.evaluated_depsgraph_get()
    oe = o.evaluated_get(dg)
    me = oe.to_mesh()
    zs = [v.co.z for v in me.vertices]
    print(f"  [{tag}] preload={preload} eval_zrange="
          f"({min(zs):.4f},{max(zs):.4f})")
    oe.to_mesh_clear()

probe("assets/loft/loft_ext.blend", "SOURCE", preload=False)
probe("assets/loft/loft_ext.blend", "SOURCE", preload=True)
probe("assets/loft/loft_master.blend", "REBUILD", preload=False)
probe("assets/loft/loft_master.blend", "REBUILD", preload=True)
