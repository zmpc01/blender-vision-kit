"""r6_look_prep.py — R6: strip packed textures to fit the 4GB box for LOOK.

The loft demo ships ~122 packed images (up to 4K). The kit's LOOK pass is
workbench + viewport display colors — image pixels are dead weight. Open
loft_import.blend, remove all image datablocks (materials keep their
node trees; texture nodes simply render blank), purge orphans, save
loft_look.blend. Vendor geometry is untouched.

Run:  ./scripts/blrun.sh --background --python scripts/r6_look_prep.py
"""
import os

import bpy

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "output", "r6")
SRC = os.path.join(OUT, "loft_import.blend")
DST = os.path.join(OUT, "loft_look.blend")

bpy.ops.wm.open_mainfile(filepath=SRC)
n_imgs = len(bpy.data.images)
for img in list(bpy.data.images):
    if img.name in ("Render Result", "Viewer Node"):
        continue
    bpy.data.images.remove(img)
bpy.data.orphans_purge(do_recursive=True)
print(f"[r6-prep] removed {n_imgs - len(bpy.data.images)} images; "
      f"objects={len(bpy.context.scene.objects)} meshes="
      f"{len([o for o in bpy.context.scene.objects if o.type == 'MESH'])}")
bpy.ops.wm.save_as_mainfile(filepath=DST, compress=True)
print(f"[r6-prep] saved {DST} ({os.path.getsize(DST) // (1 << 20)} MB)")
