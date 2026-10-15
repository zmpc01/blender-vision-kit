"""_s18_filmstrip_repro.py — reproduce filmstrip() with instrumentation:
print frame_current per cell, keep the cell files, diff them."""
import bpy
import os
bpy.ops.wm.open_mainfile(filepath="output/s18_eyecert/eyecert.blend")
scene = bpy.context.scene

import sys
sys.path.insert(0, "scripts")
import motion_study as ms

frames = [1, 4, 7, 10, 14, 17, 20, 24]
os.makedirs("output/s18_eyecert/repro", exist_ok=True)
# patch filmstrip's delete step by monkeypatching os.remove for strip files
import shutil
real_remove = os.remove
kept = []
def keep_remove(p):
    kept.append(p)  # record ONLY — do not actually delete
os.remove = keep_remove
try:
    out = ms.filmstrip(frames, "output/s18_eyecert/repro", 480, 360, "workbench")
finally:
    os.remove = real_remove
print("[repro] filmstrip out:", out)
print("[repro] kept cells:", sorted(kept))
