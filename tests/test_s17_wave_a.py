# test_s17_wave_a.py — session-17 Wave-A fix regressions (in-Blender).
#
# Covers the wave-1 audit's P0/P1 fixes:
#   1. F-TD3 (P0): render_angle sweeps camera-bound timeline markers —
#      a panel render must show the TEMP cam (pixel-diff vs the marker
#      cam's view) and every marker binding must be restored after.
#   2. F2A-2: _validate_png refuses 0-byte and non-PNG files.
#   3. F2A-3: temp cameras get distance-scaled clip planes.
#   4. F2B-1 (P0): render_viewport accepts BOTH custom_location and the
#      documented custom_loc spelling.
#   5. F2B-5: NaN/Infinity patch params are refused at the param layer.
#   6. F2B-8 (P1): world-space solvers under a ROTATED parent move the
#      object in WORLD space (place_on/snap_z/seat_at), and the
#      keyframe rebase gets the basis-space delta.
#   7. F2B-2/F2B-3: audit ERROR rows (severity=fail) fail the gate;
#      place_on post-contact ERROR rows flip ok=False.
#   8. F2B-4: place_on keep_xy=False is refused loudly.
#   9. F2B-6: seat_at reference token validation + 'centroid' lands.
#
# Run: blrun.sh --background --python tests/test_s17_wave_a.py
# Convention: prints [test_s17] per check; "ALL PASS" at the end.

import os
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "scripts"))

import viewport_capture as vc          # noqa: E402
import placement_lib as PL             # noqa: E402

PASS = []
FAIL = []


def check(name, cond, detail=""):
    tag = "ok" if cond else "FAIL"
    print(f"[test_s17] {name}: {tag}" + (f" — {detail}" if detail and not cond else ""))
    (PASS if cond else FAIL).append(name)


def wipe():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def _pixels(path):
    img = bpy.data.images.load(path, check_existing=False)
    w, h = img.size
    ch = img.channels
    buf = np.empty(w * h * ch, dtype=np.float32)
    img.pixels.foreach_get(buf)
    bpy.data.images.remove(img)
    return buf.reshape(-1, ch)[..., :3]


# ---------------------------------------------------------------- 1. F-TD3
wipe()
scene = bpy.context.scene
# ground plane + a tall red pillar at x=+2 (only visible from the right side)
bpy.ops.mesh.primitive_plane_add(size=20)
ground = bpy.context.active_object
bpy.ops.mesh.primitive_cube_add(location=(2, 0, 1))
bpy.context.active_object.name = "Pillar"
bpy.ops.object.shade_smooth()
# marker-bound camera looking AWAY from the pillar (at f1, the default frame)
mk_cam_data = bpy.data.cameras.new("ShotCam_data")
mk_cam = bpy.data.objects.new("ShotCam", mk_cam_data)
scene.collection.objects.link(mk_cam)
mk_cam.location = (0, -8, 1)
mk_cam.rotation_euler = (1.5708, 0, 0)   # looking +Y (pillar behind camera)
m = scene.timeline_markers.new("MK", frame=1)
m.camera = mk_cam
scene.frame_set(1)

out_a = "/tmp/_s17_panel_markerfixed.png"
out_b = "/tmp/_s17_panel_marker.png"
vc.render_angle("right", out_a, engine="workbench", width=320, height=240)
# pre-fix control: the marker cam's own view (= what the old bug produced).
# NOTE: set filepath/resolution explicitly — render_angle leaves the global
# render state on its chosen values (the F2A-9 leak, unfixed by design in
# this wave), so a bare bpy.ops.render.render would clobber out_a.
scene.camera = mk_cam
scene.render.filepath = out_b
scene.render.resolution_x = 320
scene.render.resolution_y = 240
scene.render.resolution_percentage = 100
bpy.ops.render.render(write_still=True)
scene.camera = None

check("s17_1a.markers_restored", m.camera is not None and m.camera.name == "ShotCam",
      f"marker camera after render_angle: {m.camera}")
diff = float(np.abs(_pixels(out_a) - _pixels(out_b)).mean())
check("s17_1b.panel_not_marker_cam", diff > 0.01,
      f"mean abs pixel diff panel-vs-markercam = {diff:.4f} (0 == hijack)")
check("s17_1c.marker_count_intact", len(scene.timeline_markers) == 1)

# ---------------------------------------------------------------- 2. F2A-2
wipe()
open("/tmp/_s17_empty.png", "wb").close()
for name, path in [("zero_byte", "/tmp/_s17_empty.png"),
                   ("not_png", "/tmp/_s17_notpng.png")]:
    with open("/tmp/_s17_notpng.png", "wb") as f:
        f.write(b"GIF89a not a png at all....")
    try:
        vc._validate_png(path)
        check(f"s17_2.{name}_refused", False, "no exception raised")
    except RuntimeError:
        check(f"s17_2.{name}_refused", True)

# ---------------------------------------------------------------- 3. F2A-3
wipe()
cam, tgt = vc._add_temp_camera("c1", (40, 0, 0), (0, 0, 0), 50)
check("s17_3a.clip_far_scaled", abs(cam.data.clip_end - 120.0) < 1e-6,
      f"clip_end={cam.data.clip_end} (expect 3x dist=120, over the 100 floor)")
check("s17_3b.clip_near_scaled", abs(cam.data.clip_start - 0.8) < 1e-6,
      f"clip_start={cam.data.clip_start} (expect 2% of 40 = 0.8)")
cam2, _ = vc._add_temp_camera("c2", (0.03, 0, 0.02), (0, 0, 0), 50)
check("s17_3c.clip_near_floor", cam2.data.clip_start >= 0.001,
      f"closeup clip_start={cam2.data.clip_start}")
vc._cleanup_temp_camera(cam, tgt)
vc._cleanup_temp_camera(cam2, None)

# ---------------------------------------------------------------- 4. F2B-1
import apply_patch as AP               # noqa: E402  (bpy present here)
wipe()
bpy.ops.mesh.primitive_cube_add(size=0.5)
bpy.context.active_object.name = "Box"
out = "/tmp/_s17_customloc.png"
rep = {"op": "render_viewport"}
AP._apply_render_viewport(None, {"output": out, "angle": "custom",
                                 "custom_loc": [3, -3, 2]})
check("s17_4.custom_loc_accepted", os.path.getsize(out) > 0,
      "the documented spelling must render, not silently no-op")

# ---------------------------------------------------------------- 5. F2B-5
try:
    AP._require({"location": [0.0, float("nan"), 0.0]}, "location",
                "set_location", expected_type=list, expected_len=3)
    check("s17_5.nan_refused", False, "NaN passed through _require")
except RuntimeError as e:
    check("s17_5.nan_refused", "NaN" in str(e), str(e)[:60])
try:
    AP._require({"energy": float("inf")}, "energy", "set_light_energy")
    check("s17_5.inf_refused", False, "inf passed through _require")
except RuntimeError:
    check("s17_5.inf_refused", True)

# ------------------------------------------------------------- 6. F2B-8
# rotated parent: parent rotated 90 deg about Z — a naive parent-space
# z write would move the child along the parent's LOCAL z (world X here).
wipe()
bpy.ops.mesh.primitive_cube_add(size=0.4)
mover = bpy.context.active_object
mover.name = "Mover"
bpy.ops.object.empty_add(location=(0, 0, 0))
parent = bpy.context.active_object
parent.name = "Rig"
parent.rotation_euler = (1.5708, 0, 0)   # 90 deg about X — mixes world z into parent-local y
mover.parent = parent
mover.matrix_parent_inverse = parent.matrix_world.inverted()
bpy.ops.mesh.primitive_plane_add(size=8)
ground = bpy.context.active_object
ground.name = "Ground"
bpy.context.view_layer.update()

before = Vector(mover.matrix_world.translation)
rep = {}
PL._apply_translation(mover, 0.5, None, rep)
bpy.context.view_layer.update()
after = Vector(mover.matrix_world.translation)
wdelta = after - before
check("s17_6a.world_z_under_rotated_parent",
      abs(wdelta.z - 0.5) < 1e-5 and abs(wdelta.x) < 1e-5 and abs(wdelta.y) < 1e-5,
      f"world delta {tuple(round(v, 5) for v in wdelta)} (expect ~[0,0,0.5])")
check("s17_6b.report_notes_conversion", "parent_space_conversion" in rep)

# snap_z under the same rotated parent must land the WORLD bottom at z
PL.snap_z(mover, 2.25, reference="bottom")
bpy.context.view_layer.update()
mn, mx = PL._aabb(mover)
check("s17_6c.snap_z_world", abs(mn.z - 2.25) < 1e-4, f"bottom z={mn.z:.5f}")

# seat_at under a rotated parent: bottom-center must land at the anchor
bpy.ops.object.empty_add(location=(1, 2, 3))
anchor = bpy.context.active_object
anchor.name = "SeatAnchor"
anchor.rotation_euler = (0.3, 0.2, 0.7)
bpy.context.view_layer.update()
rep = PL.seat_at(mover, anchor, reference="bottom")
bpy.context.view_layer.update()
mn2, mx2 = PL._aabb(mover)
landed = Vector(((mn2.x + mx2.x) / 2, (mn2.y + mx2.y) / 2, mn2.z))
want = Vector(anchor.matrix_world.translation)
err = (landed - want).length
check("s17_6d.seat_at_parented_lands", err < 1e-3,
      f"landed bottom-center off anchor by {err*1000:.2f} mm")
try:
    PL.seat_at(mover, anchor, reference="bogus")
    check("s17_6e.reference_validated", False, "bogus token accepted")
except RuntimeError:
    check("s17_6e.reference_validated", True)
rep_c = PL.seat_at(mover, anchor, reference="centroid")
check("s17_6f.centroid_implemented", "reference_fallback" not in rep_c)

# ------------------------------------------------------------- 7. F2B-2/3
wipe()
bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
a = bpy.context.active_object
a.name = "SolidA"
# ANIMATED skinned mover makes _skinned_guard RAISE inside pair_contact
# (force=False) -> audit_scene's except-row -> severity=fail -> failed=True
arm = bpy.data.armatures.new("Arm")
arm_obj = bpy.data.objects.new("ArmRig", arm)
bpy.context.collection.objects.link(arm_obj)
arm_obj.location = (0, 0, 5)
arm_obj.keyframe_insert(data_path="location", frame=1)
bpy.ops.mesh.primitive_cube_add(location=(0.2, 0, 0))
b = bpy.context.active_object
b.name = "SkinnedB"
b.parent = arm_obj
vg = b.vertex_groups.new(name="g")
vg.add(list(range(len(b.data.vertices))), 1.0, 'REPLACE')
mod = b.modifiers.new("Arm", 'ARMATURE')
mod.object = arm_obj
rep = PL.audit_scene(pairs=[["SolidA", "SkinnedB"]], force=False)
err_rows = [r for r in rep["pairs"] if r.get("state") == "ERROR"]
check("s17_7a.error_row_present", len(err_rows) == 1,
      f"rows={[(r.get('state'), r.get('severity')) for r in rep['pairs']]}")
check("s17_7b.error_row_fails_gate", rep["failed"] is True,
      f"failed={rep['failed']} (pre-fix: False)")
check("s17_7c.error_row_severity", err_rows and err_rows[0].get("severity") == "fail")

# ------------------------------------------------------------- 8. F2B-4
wipe()
bpy.ops.mesh.primitive_cube_add(location=(0, 0, 2))
obj = bpy.context.active_object
obj.name = "Falling"
bpy.ops.mesh.primitive_plane_add(size=6)
sup = bpy.context.active_object
sup.name = "Floor"
try:
    PL.place_on(obj, sup, keep_xy=False)
    check("s17_8.keep_xy_false_refused", False, "accepted silently")
except RuntimeError as e:
    check("s17_8.keep_xy_false_refused", "F2B-4" in str(e), str(e)[:60])

# ---------------------------------------------------------------- summary
print(f"[test_s17] {len(PASS)} passed, {len(FAIL)} failed")
if FAIL:
    print(f"[test_s17] FAILED: {FAIL}")
    sys.exit(1)
print("[test_s17] ALL PASS")
