"""BOOT-BL-1 smoke test: minimal headless render via Cycles / EEVEE_NEXT / Workbench.

Builds a cube + sun light + camera, renders 64x64 PNGs with each engine,
prints per-engine wall time, and saves smoke.blend for helper-script tests.

Run via: ./scripts/blrun.sh --background --python smoke/smoke_render.py
"""
import os
import time

import bpy

OUT = os.path.dirname(os.path.abspath(__file__))


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 1))
    bpy.ops.object.light_add(type='SUN', location=(3, -2, 4), rotation=(0.6, 0, 0.5))
    bpy.context.active_object.data.energy = 3.0
    bpy.ops.object.camera_add(location=(5, -5, 3.5), rotation=(1.15, 0, 0.85))
    bpy.context.scene.camera = bpy.context.active_object


def render_once(engine, path, samples):
    scene = bpy.context.scene
    scene.render.engine = engine
    scene.render.resolution_x = 64
    scene.render.resolution_y = 64
    if engine == 'CYCLES':
        scene.cycles.device = 'CPU'
        scene.cycles.samples = samples
    elif engine == 'BLENDER_EEVEE_NEXT':
        scene.eevee.taa_render_samples = samples
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = path
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    dt = time.time() - t0
    size = os.path.getsize(path) if os.path.exists(path) else 0
    status = "OK" if size > 100 else "FAIL(empty)"
    print(f"[smoke] {engine} 64x64 samples={samples}: {dt:.2f}s -> {path} ({size} bytes) {status}")


build()
print(f"[smoke] Blender {bpy.app.version_string}, binary={bpy.app.binary_path}")
render_once('CYCLES', f"{OUT}/smoke_cycles_64.png", 16)
render_once('CYCLES', f"{OUT}/smoke_cycles_64_warm.png", 16)
render_once('BLENDER_EEVEE_NEXT', f"{OUT}/smoke_eevee_64.png", 16)
render_once('BLENDER_WORKBENCH', f"{OUT}/smoke_workbench_64.png", 16)
bpy.ops.wm.save_as_mainfile(filepath=f"{OUT}/smoke.blend")
print("[smoke] saved smoke.blend")
print("[smoke] done")
