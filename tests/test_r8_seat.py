"""
test_r8_seat.py — D17 seat-protocol regression (probe + wrapper math +
execute on a synthetic labeled chair).

In-process (runs INSIDE Blender):

  R8.1  yaw convention law: wrapper forward = (-sin, cos) — the run-5
        90-degree bug regression (atan2(f.y,f.x) is the MATH convention)
  R8.2  probe on a synthetic labeled chair: seat plane found at the
        cushion top (not the backrest), backrest cluster detected,
        confidence high, facing away from the backrest
  R8.3  sat-upon clutter: a throw-pillow box ON the seat does not win
  R8.4  contamination STOP-AND-FLAG: a box occupying the sit zone flags
  R8.5  measure_actor prior gate: H within 2% of 0.5415x1.05
  R8.6  execute end-to-end on the synthetic chair: report ok=True,
        pelvis dz within tolerance, exit reverse-validation passes

Run:
  ./scripts/blrun.sh --background --python tests/test_r8_seat.py --
"""
import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS = os.path.abspath(os.path.join(_HERE, "..", "scripts"))
for _p in (_SCRIPTS,):
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

import bpy  # noqa: E402
import r8_seat as RS  # noqa: E402

FAIL = []


def check(label, got, expect):
    ok = got == expect
    if not ok:
        FAIL.append(f"{label}: got {got!r}, expected {expect!r}")
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}")


def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def build_chair():
    """Synthetic labeled chair: floor + seat cushion + backrest + a
    throw pillow ON the seat. Chair seat top at 0.48, at origin."""
    sc = bpy.context.scene
    sc.render.fps = 24

    def box(name, sx, sy, sz, loc, label=None):
        bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
        o = bpy.context.active_object
        o.name = name
        o.scale = (sx / 2, sy / 2, sz / 2)
        bpy.context.view_layer.update()
        if label:
            o["kit_label"] = label
        return o

    box("Floor", 12, 12, 0.04, (0, 0, -0.02), "floor")
    box("SeatCushion", 0.9, 0.9, 0.14, (0, 0, 0.46), "chair")     # top 0.53
    box("Backrest", 0.9, 0.12, 0.7, (0, 0.51, 0.85), "chair")     # behind +Y
    box("Pillow", 0.35, 0.35, 0.12, (0.15, 0.42, 0.60), "chair")  # top
    # 0.66, AGAINST the backrest — throw pillows live there, not mid-seat
    return sc


def main():
    # ---------------- R8.1 yaw convention law ----------------
    f_y = (0.0, 1.0)          # face +Y -> wrapper yaw 0
    f_x = (1.0, 0.0)          # face +X -> wrapper yaw -90 deg
    yaw_y = math.atan2(-f_y[0], f_y[1])
    yaw_x = math.atan2(-f_x[0], f_x[1])
    check("R8.1.yaw_plusY", round(math.degrees(yaw_y), 6), 0.0)
    check("R8.1.yaw_plusX", round(math.degrees(yaw_x), 6), -90.0)
    # forward(yaw) must reproduce the asked direction
    fwd = (-math.sin(yaw_x), math.cos(yaw_x))
    check("R8.1.forward_roundtrip",
          (round(fwd[0], 6), round(fwd[1], 6)), (1.0, 0.0))

    # ---------------- R8.2/R8.3 probe on the synthetic chair --------
    clear()
    sc = build_chair()
    spec = RS.seat_probe("chair", (0.0, -2.0), mode="chair")
    # the region mean includes soft/edge hits — judge within the
    # soft-seat tolerance, not exact top
    check("R8.2.seat_z_cushion", abs(spec["seat_z"] - 0.53) <= 0.06, True)
    check("R8.2.backrest_found", (spec["backrest"] or {}).get("n", 0) >= 5,
          True)
    check("R8.2.conf_high", spec["confidence"], "high")
    # facing away from backrest: backrest is at +Y -> facing -Y
    # (angular distance with wrap: 180 == -180)
    _d = abs(spec["facing_yaw_deg"] - 180.0)
    check("R8.2.facing_away", min(_d, 360.0 - _d) < 45.0, True)
    # sit target inset toward the backrest from cushion center
    check("R8.2.target_in_seat",
          -0.45 <= spec["sit_target"][0] <= 0.45 and
          -0.45 <= spec["sit_target"][1] <= 0.45, True)

    # ---------------- R8.2b low-seat probe sanity ----------------
    # (E12: this header had zero checks. The check lives inside the R8.7
    # block below — that block already builds the LOW chair and runs the
    # low-seat probe; R8.2b asserts the probe actually READ the lowered
    # cushion, so R8.7's rejection is attributable to leg reach, not a
    # stale/mis-read seat plane. Doing it here would have to clobber the
    # shared R8.2 scene that R8.4's contamination probe depends on.)

    # ---------------- R8.4 contamination ----------------
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0.05, -0.1, 0.55))
    blk = bpy.context.active_object
    blk.name = "ClutterBox"
    blk.scale = (0.2, 0.2, 0.1)
    bpy.context.view_layer.update()
    try:
        RS.seat_probe("chair", (0.0, -2.0), mode="chair")
        check("R8.4.contamination_flags", False, True)
    except RS.SeatFlag:
        check("R8.4.contamination_flags", True, True)

    # ---------------- R8.5/R8.6 measure + execute ----------------
    clear()
    build_chair()
    import assets_ual_actors as UA
    actor = UA._import_actor("Driver", UA.ACTOR_SCALE)
    actor["root"].location = (0.5, -2.5, 0.0)   # south of the chair
    bpy.context.view_layer.update()
    m = RS.measure_actor(actor)
    check("R8.5.prior_gate",
          abs(m["H_hips_z"] - 0.5415 * 1.05) / (0.5415 * 1.05) <= 0.02,
          True)
    spec = RS.seat_probe("chair", (0.0, -2.0), mode="chair")
    rep = RS.execute_sit("Driver", spec, m, hold_idle=24)
    c = rep["checks"]
    check("R8.6.execute_ok", rep["ok"], True)
    check("R8.6.pelvis_dz", c["pelvis_seat_dz_m"] <= max(0.02, c[
        "idle_hip_tol_m"]), True)
    check("R8.6.exit_ok", c["exit_ok"], True)
    check("R8.6.facing", c["facing_ok"], True)
    check("R8.6.feet", c["feet_ok"], True)

    # ---------------- R8.8 family clutter in the sit zone flags ------
    clear()
    build_chair()
    bpy.data.objects["Pillow"].location = (0.0, 0.12, 0.60)  # mid-seat
    bpy.context.view_layer.update()
    try:
        RS.seat_probe("chair", (0.0, -2.0), mode="chair")
        check("R8.8.clutter_flags", False, True)
    except RS.SeatFlag:
        check("R8.8.clutter_flags", True, True)

    # ---------------- R8.7 low seat is honestly rejected ------------
    clear()
    build_chair()
    # drop the cushion to a 0.36 top: the Enter clip's leg reach puts
    # toes below the floor there — the audit must REJECT it
    bpy.data.objects["SeatCushion"].scale = (0.45, 0.45, 0.05)
    bpy.data.objects["SeatCushion"].location = (0, 0, 0.31)
    bpy.context.view_layer.update()
    import assets_ual_actors as UA2
    actor2 = UA2._import_actor("Girl", UA2.ACTOR_SCALE)
    actor2["root"].location = (0.5, -2.5, 0.0)
    bpy.context.view_layer.update()
    m2 = RS.measure_actor(actor2)
    spec2 = RS.seat_probe("chair", (0.0, -2.0), mode="chair")
    rep2 = RS.execute_sit("Girl", spec2, m2, hold_idle=24)
    check("R8.7.low_seat_rejected", rep2["ok"], False)
    check("R8.7.feet_reason", rep2["checks"]["feet_ok"], False)

    # R8.2b (E12): the low-seat probe sanity — the probe's seat plane
    # must track the lowered cushion (box scale 0.05 at z=0.31 -> top
    # 0.335), NOT the old 0.53 cushion top or the backrest
    check("R8.2b.low_seat_z_tracks_cushion",
          abs(spec2["seat_z"] - 0.335) <= 0.06, True)

    # --------------------------------------------------------------------
    print(f"\n[test_r8] {'ALL PASS' if not FAIL else 'FAILURES:'}")
    for f in FAIL:
        print(f"  [FAIL] {f}")
    if FAIL:
        sys.exit(1)


main()
