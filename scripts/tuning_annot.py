#!/usr/bin/env python3
"""
tuning_annot.py — P1 decisive test: annotation legibility on color vs mono,
at look resolution (640x480) and previz resolution (480x270).

Uses the kit's OWN annotation + capture code paths (not a reimplementation):
build_scene -> annotate.build_annotation_layer -> viewport_capture.render_angle
Mono variants via PIL post-pass.
"""
import bpy, os, sys

sys.path.insert(0, "/home/z/bvk/scripts")
OUT = "/home/z/bvk/output/tuning"
os.makedirs(OUT, exist_ok=True)

import annotate
import viewport_capture as vc
import tuning_matrix  # reuse the diagnostic scene builder

scn = tuning_matrix.build_scene()
tuning_matrix.camera(scn, (7.5, -6.5, 4.2))

# flag the floater (red box) + label the big objects, as a consumer would
flag = ["floater"]
objs = {o.name: o for o in scn.objects}
label_ids = [(n, i + 1) for i, n in enumerate(
    ("red_cube", "green_sphere", "blue_cyl",
     "gray_box", "white_box", "floater", "small_ball"))]

layer = annotate.build_annotation_layer(flagged_ids=flag, label_ids=label_ids)

def render(name, w, h, engine="workbench"):
    vc.render_angle("persp", f"{OUT}/{name}.png", engine=engine,
                    width=w, height=h, target=(0, 0, 0.3))

render("annot_look_640", 640, 480)
render("annot_previz_480", 480, 270)
render("annot_look_640_eevee", 640, 480, engine="eevee")

annotate.delete_annotation_layer(layer)

# mono variants
from PIL import Image
for n in ("annot_look_640", "annot_previz_480", "annot_look_640_eevee"):
    p = f"{OUT}/{n}.png"
    Image.open(p).convert("L").convert("RGB").save(p.replace(".png", "_mono.png"))

print("[annot] DONE")
