"""r6_loft_import.py — R6 lane: import a REAL stitched interior LEVEL.

Opens the Blender Foundation "Loft" demo scene (download.blender.org,
demo/cycles/loft.blend — a two-level loft apartment: walls, stairs,
pillars, platforms, furniture) AS-IS. This is the honest import state:
vendor object names, vendor camera/lights, real-world scale. The only
normalization applied is what any agent must do with a downloaded
scene — measure it, report the ground plane, ensure a usable overview
camera for the LOOK pass. No renaming, no splitting, no relighting.

Run:  ./scripts/blrun.sh --background --python scripts/r6_loft_import.py
Requires: loft.blend downloaded (see scripts/r6_loft_fetch.sh).
"""
import mathutils
import os
import sys

import bpy

_SRC = os.environ.get("LOFT_SRC",
                      "/home/z/vision-work/polyhaven_cache/loft/loft.blend")
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "output", "r6")


def main():
    if not os.path.exists(_SRC):
        sys.exit(f"[r6] {_SRC} missing — run scripts/r6_loft_fetch.sh")
    # open the vendor scene as-is (legacy 2.9x file — Blender versions it up)
    bpy.ops.wm.open_mainfile(filepath=_SRC)
    scene = bpy.context.scene
    print(f"[r6] opened scene: {scene.name!r} unit_scale={scene.unit_settings.scale_length}")

    meshes = [o for o in scene.objects if o.type == "MESH"]
    print(f"[r6] objects: {len(scene.objects)} total, {len(meshes)} mesh")
    for o in scene.objects:
        if o.type == "MESH":
            print(f"[r6]   mesh {o.name!r} polys={len(o.data.polygons)} "
                  f"dims={[round(v, 2) for v in o.dimensions]} "
                  f"parent={o.parent.name if o.parent else None}")
        else:
            print(f"[r6]   {o.type:<6} {o.name!r}")

    # world-space bounds (honest measure, post-versioning depsgraph)
    bpy.context.view_layer.update()
    xs, ys, zs = [], [], []
    for o in meshes:
        for c in o.bound_box:
            p = o.matrix_world @ mathutils.Vector(c)
            xs.append(p.x); ys.append(p.y); zs.append(p.z)
    bb = (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))
    print(f"[r6] world bbox x[{bb[0]:.2f},{bb[1]:.2f}] y[{bb[2]:.2f},{bb[3]:.2f}] "
          f"z[{bb[4]:.2f},{bb[5]:.2f}]")
    print(f"[r6] size: {bb[1]-bb[0]:.2f} x {bb[3]-bb[2]:.2f} x {bb[5]-bb[4]:.2f} m; "
          f"ground min-z={bb[4]:.3f}")

    # ensure an overview camera (park ABOVE the level, looking straight down
    # 3/4 — the vendor camera stays untouched for the usability phase)
    if not scene.camera:
        cam_data = bpy.data.cameras.new("OverviewCam")
        cam_data.lens = 24
        cam = bpy.data.objects.new("OverviewCam", cam_data)
        scene.collection.objects.link(cam)
        cx, cy = (bb[0] + bb[1]) / 2, (bb[2] + bb[3]) / 2
        span = max(bb[1] - bb[0], bb[3] - bb[2])
        cam.location = (cx, cy - span * 0.35, bb[5] + span * 0.75)
        d = mathutils.Vector((cx, cy, (bb[4] + bb[5]) / 2)) - cam.location
        cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
        scene.camera = cam
        print(f"[r6] added OverviewCam at {[round(v, 2) for v in cam.location]}")

    # The vendor file references textures on the AUTHOR's machine (2010-era
    # paths + 3ds-max "Map #..." refs); Blender 5.2's compressed save packs
    # external images and aborts on missing ones. Honest normalization:
    # detach broken external refs (packed images are kept untouched) and
    # record it — geometry and material basecolors are unaffected.
    broken, kept_packed = 0, 0
    for img in bpy.data.images:
        if img.packed_file:
            kept_packed += 1
            continue
        p = bpy.path.abspath(img.filepath) if img.filepath else ""
        if not p or not os.path.exists(p):
            img.filepath = ""
            broken += 1
    print(f"[r6] textures: {kept_packed} packed kept, {broken} broken external refs detached")

    os.makedirs(OUT, exist_ok=True)
    dst = os.path.join(OUT, "loft_import.blend")
    bpy.ops.wm.save_as_mainfile(filepath=dst, compress=True)
    print(f"[r6] saved: {dst} ({os.path.getsize(dst) // (1 << 20)} MB)")


main()
