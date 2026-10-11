import bpy, glob
out = []
for p in sorted(glob.glob("assets/loft/chunks/*.blend")):
    with bpy.data.libraries.load(p, link=False) as (src, _):
        imgs = list(src.images)
        hits = [n for n in imgs if "Book_01" in n or "Bark_Bamboo" in n]
        out.append((p.split("/")[-1], len(imgs), hits))
for o in out:
    print("CHUNK", o)
