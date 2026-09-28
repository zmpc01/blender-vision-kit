#!/usr/bin/env python3
"""tuning_exposure.py — P2 follow-up: can workbench match EEVEE's dynamic
range? Cells: kit default + exposure lifts (+0.5, +1.0, +1.5), and
FLAT-light with shadows+cavity (bright ground hypothesis)."""
import bpy, os, sys
sys.path.insert(0, "/home/z/bvk/scripts")
OUT = "/home/z/bvk/output/tuning"
import tuning_matrix
import viewport_capture as vc

scn = tuning_matrix.build_scene()

def render(name, engine="workbench", light="STUDIO", shadows=True, cavity=True,
           exposure=0.0):
    scn.view_settings.exposure = exposure
    try:
        scn.view_settings.view_transform = 'Standard'
    except Exception:
        pass
    vc.render_angle("persp", f"{OUT}/{name}.png", engine=engine,
                    width=640, height=480, target=(0, 0, 0.3))

render("exp_base")            # kit default = current
render("exp_pos050", exposure=0.5)
render("exp_pos100", exposure=1.0)
render("exp_pos150", exposure=1.5)
# FLAT light with shadows: shadows are a separate display feature from light mode
render("wb_flat_sh", light="FLAT")

print("[exp] DONE")
