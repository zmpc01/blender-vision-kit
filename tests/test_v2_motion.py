"""
test_v2_motion.py — regression suite for the M5 motion/transient tooling.

Covers:
  1. motion_study build: trajectories + ghosts exist for T6; coincident
     ghosts skipped (GlitchBox rest ghosts); zero KIT_MOTION_ residue
  2. motion_numbers: BURST-MOTION fires on the planted sink; no false POP
  3. transient_scan._events: synthetic series clustering + MAD floor
  4. _fold_findings: duration classification (short=TRANSIENT,
     long=PERSISTENT)
  5. validator floor_penetration: half-sunk -> P1; resting -> silent;
     shallow embed -> silent; fully-sunk -> P0 below_floor
  6. transient_scan subprocess end-to-end on T6: TRANSIENT line in table,
     suspects strip written

Run:   ./scripts/blrun.sh --background --python tests/test_v2_motion.py --
"""
import os
import subprocess
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

CHECKS = {"n": 0, "fail": []}


def _check(tag, cond, detail=""):
    CHECKS["n"] += 1
    status = "PASS" if cond else "FAIL"
    print(f"  [{status}] {tag}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        CHECKS["fail"].append(tag)


def _motion_residue():
    objs = [o.name for o in bpy.data.objects
            if o.name.startswith("KIT_MOTION_")]
    meshes = [m.name for m in bpy.data.meshes
              if m.name.startswith("KIT_MOTION_")]
    mats = [m.name for m in bpy.data.materials
            if m.name.startswith("KIT_MOTION_")]
    return objs, meshes, mats


def _build_t6(n_frames=64):
    from blender_kit import safe_import_scene, clear_scene
    mod = safe_import_scene("t6_transient")
    clear_scene()
    ctx = mod.build_scene()
    mod.animate(ctx, start_frame=1, n_frames=n_frames)
    return ctx


def test_1_motion_build():
    print("== 1. motion_study build + coincident skip + residue")
    import motion_study as ms
    ctx = _build_t6()
    objs = [ctx["ball"], ctx["slider"], ctx["glitch"]]
    made = (ms.build_trajectories(objs, 1, 24, coarse=48)
            + ms.build_onion_skin(objs, [1, 4, 7, 10, 14, 17, 20, 24]))
    _check("layer objects built", len(made) > 30, f"got {len(made)}")
    traj = [o for o in made if o.name.startswith("KIT_MOTION_traj")]
    ticks = [o for o in made if o.name.startswith("KIT_MOTION_tick")]
    ghosts = [o for o in made if o.name.startswith("KIT_MOTION_ghost")]
    currents = [o for o in made if o.name.startswith("KIT_MOTION_current")]
    _check("trajectory chains exist", len(traj) > 20, f"got {len(traj)}")
    _check("time ticks exist", len(ticks) >= 21, f"got {len(ticks)}")
    _check("current copies per object", len(currents) == 3, f"got {len(currents)}")
    # GlitchBox ghosts: rest frames coincide with current pose -> skipped;
    # only the sunk mid-frames differ -> strictly fewer than 7
    gb_ghosts = [o for o in ghosts if "GlitchBox" in o.name]
    _check("coincident ghosts skipped (GlitchBox)", 0 < len(gb_ghosts) < 7,
           f"got {len(gb_ghosts)}")
    ball_ghosts = [o for o in ghosts if "Ball" in o.name]
    _check("moving object keeps all ghosts", len(ball_ghosts) == 7,
           f"got {len(ball_ghosts)}")
    # materials parity: ghost mesh copies must not touch real materials
    ball_mat_slots = len(ctx["ball"].data.materials)
    _check("real object materials untouched", ball_mat_slots >= 1,
           f"got {ball_mat_slots}")
    # cleanup
    for o in made:
        try:
            bpy.data.objects.remove(o, do_unlink=True)
        except Exception:
            pass
    for m in list(bpy.data.materials.keys()):
        if m.startswith("KIT_MOTION_mat_"):
            bpy.data.materials.remove(bpy.data.materials[m])
    for me in list(bpy.data.meshes.keys()):
        if me.startswith("KIT_MOTION_"):
            bpy.data.meshes.remove(bpy.data.meshes[me])
    o_r, m_r, mat_r = _motion_residue()
    _check("zero motion residue", not (o_r or m_r or mat_r),
           f"{o_r[:2]} {m_r[:2]} {mat_r[:2]}")


def test_2_motion_numbers():
    print("== 2. motion_numbers BURST flag")
    import motion_study as ms
    ctx = _build_t6()
    objs = [ctx["ball"], ctx["slider"], ctx["glitch"]]
    frames = [1, 4, 7, 10, 14, 17, 20, 24]
    lines = ms.motion_numbers(objs, 1, 24, frames)
    blob = "\n".join(lines)
    _check("table covers all three", all(n in blob for n in
                                         ("Ball", "Slider", "GlitchBox")))
    _check("BURST fires on planted sink", "GlitchBox" in blob
           and "BURST-MOTION" in blob)
    _check("no false POP on smooth motion",
           "Ball" in blob and "POP-FRAMES" not in
           [ln for ln in lines if "Ball" in ln][0])


def test_3_event_clustering():
    print("== 3. transient_scan._events clustering")
    import transient_scan as ts
    # quiet baseline with one hot burst at f10-12
    series = [(f, 0.001, 0.01) for f in range(2, 20)]
    for f, pk in ((10, 0.35), (11, 0.40), (12, 0.45)):  # rising peak diffs
        series[f - 2] = (f, 0.30, pk)
    evs = ts._events(series, top_k=6)
    _check("one event found", len(evs) == 1, f"got {len(evs)}")
    if evs:
        _check("event span f10..f12",
               evs[0]["start"] == 10 and evs[0]["end"] == 12,
               f"{evs[0]['start']}..{evs[0]['end']}")
        _check("peak frame f12 (max peak-diff)", evs[0]["peak_frame"] == 12)
    # empty series
    _check("empty series safe", ts._events([], 6) == [])


def test_4_fold_classification():
    print("== 4. _fold_findings duration classification")
    import transient_scan as ts
    findings = {
        5: [("P1", "floating", "A")],           # 1/20 frames -> transient
        16: [("P1", "floor_penetration", "B")],
        17: [("P1", "floor_penetration", "B")],
    }
    # persistent: floating on 'C' for 15 of 20 frames
    for f in range(3, 18):
        findings.setdefault(f, []).append(("P1", "floating", "C"))
    evs, persistent = ts._fold_findings([], findings, 6, 20)
    sigs_t = {sig for e in evs for sig, _ in e.get("transient", [])}
    _check("short-window finding -> TRANSIENT",
           ("P1", "floor_penetration", "B") in sigs_t)
    _check("isolated transient forms own event", len(evs) >= 1)
    sigs_p = {(s, t, w) for (s, t, w), _ in persistent}
    _check("long-window finding -> PERSISTENT",
           ("P1", "floating", "C") in sigs_p)
    _check("persistent NOT in events' transient",
           all(("P1", "floating", "C") not in {sig for sig, _ in
                                               e.get("transient", [])}
               for e in evs))


def test_5_floor_penetration():
    print("== 5. validator floor_penetration check")
    import validate_scene as vs
    # half-sunk box: 0.35m cube centered z=-0.05 -> 0.225 penetration (64%)
    bpy.ops.mesh.primitive_cube_add(size=0.35, location=(0, 0, -0.05))
    sunk = bpy.context.active_object
    sunk.name = "SunkBox"
    rep = vs.validate_scene()
    types = {(i["type"], i.get("object")) for i in rep["issues"]}
    _check("half-sunk -> floor_penetration P1",
           ("floor_penetration", "SunkBox") in types, str(types))
    # shallow embed: 1cm — silent (posts/rugs)
    sunk.location = (0, 0, 0.165)  # bottom at -0.01
    bpy.context.view_layer.update()
    rep = vs.validate_scene()
    _check("1cm embed silent",
           all(i["type"] != "floor_penetration" for i in rep["issues"]))
    # resting on floor: silent
    sunk.location = (0, 0, 0.175)
    bpy.context.view_layer.update()
    rep = vs.validate_scene()
    _check("resting box silent",
           all(i["type"] != "floor_penetration" for i in rep["issues"]))
    # fully-sunk -> below_floor P0 still works
    sunk.location = (0, 0, -0.4)
    bpy.context.view_layer.update()
    rep = vs.validate_scene()
    _check("fully-sunk -> below_floor P0",
           any(i["type"] == "below_floor" and i.get("object") == "SunkBox"
               for i in rep["issues"]))
    bpy.data.objects.remove(sunk, do_unlink=True)


def _run_scan_cli():
    out = "/tmp/test_v2_scan_out"
    cmd = [os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "scripts", "blrun.sh"),
        "--background", "--python",
        os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "scripts", "transient_scan.py"),
        "--", "--scene", "t6_transient", "--start", "1", "--end", "24",
        "--out", out]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=280), out


def test_6_scan_end_to_end():
    print("== 6. transient_scan subprocess end-to-end")
    from blender_kit import safe_import_scene, clear_scene
    mod = safe_import_scene("t6_transient")
    clear_scene()
    ctx = mod.build_scene()
    mod.animate(ctx, start_frame=1, n_frames=24)  # register the scene module
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".blend", delete=False) as tf:
        blend_path = tf.name
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    proc, out = _run_scan_cli()
    blob = proc.stdout
    _check("scan subprocess completed", "DOCTRINE" in blob,
           f"rc={proc.returncode} tail={blob[-200:] if blob else 'EMPTY'}")
    _check("planted glitch in table",
           "floor_penetration" in blob and "GlitchBox" in blob)
    _check("ball flight baselined PERSISTENT", "PERSISTENT" in blob
           and "Ball" in blob)
    _check("suspects strip written",
           os.path.exists(os.path.join(out, "suspects.png")))
    try:
        os.remove(blend_path)
    except OSError:
        pass


def main():
    test_1_motion_build()
    test_2_motion_numbers()
    test_3_event_clustering()
    test_4_fold_classification()
    test_5_floor_penetration()
    test_6_scan_end_to_end()
    print("=" * 60)
    print(f"test_v2_motion: {CHECKS['n'] - len(CHECKS['fail'])}/{CHECKS['n']} "
          "checks passed")
    if CHECKS["fail"]:
        print(f"FAILED: {CHECKS['fail']}")
        print("test_v2_motion: FAIL")
        return
    print("test_v2_motion: ALL PASS")


if __name__ == "__main__":
    main()
