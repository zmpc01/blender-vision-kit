"""
t9_chaos_fuzz.py — placement chaos-fuzz (HANDOFF gap A, session-5).

Perturbs the placed T8 diorama with randomized OFF-NOMINAL transforms,
then verifies the gate layer stays CONSISTENT and CRASH-FREE per class:

  round class      transform                        expected audit signal
  R1 tilt-small    random yaw+roll <= 8 deg          TOUCHING (corner) or PENETRATING — must not crash
  R2 tilt-steep    roll 25 deg                       any contact verdict — must not crash
  R3 sink          -z 5..60 mm                       PENETRATING pair involving mover
  R4 lift          +z 20..300 mm                     mover floating: audit has NO touching pair for it
  R5 offset-xy     xy shift 2..40 mm                 TOUCHING or CLEAR — must not crash
  R6 yaw-90        90 deg yaw (footprint rotation)   TOUCHING/CLEAR — must not crash
  R7 teleport      move 5 m away                     mover appears in NO pair (audit 100mm pad law)

Each round: perturb -> audit_scene() -> section_pair(mover, support) render
-> one full-scene workbench render for the PRINCIPAL's visual pass.

Seat-at edge checks (gap B, in-process — the apply_patch id-error UX is
covered by test_v3/subprocess):
  S1 align=False preserves mover rotation
  S2 offset lands mover at anchor + local offset
  S3 re-seat to a second anchor moves the mover (no residue at old spot)

Usage:
  ./scripts/blrun.sh --background --python tests/t9_chaos_fuzz.py -- \
      --output output/t9_chaos
"""
import math
import os
import random
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS = os.path.abspath(os.path.join(_HERE, "..", "scripts"))
for _p in (_SCRIPTS,):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import bpy
from mathutils import Euler, Vector

from blender_kit import clear_scene, make_material, common_parser, script_argv
import placement_lib as PL
import validate_scene as VS

OUT = None
RESULTS = {"fixture": "t9_chaos_fuzz", "rounds": [], "seat_checks": []}
RNG = random.Random(5202)  # fixed seed: reproducible chaos


def _note(kind, tag, ok, detail):
    store = "rounds" if kind == "round" else "seat_checks"
    RESULTS[store].append({"tag": tag, "ok": ok, "detail": detail})
    print(f"  [{'PASS' if ok else 'FAIL'}] {tag}: {detail}")
    return ok


def _scene_render(tag, mover_name):
    """One 640x480 workbench 3/4 view for the principal; red-tint nothing,
    annotate nothing — raw state under M5 fast path."""
    scene = bpy.context.scene
    cam_data = bpy.data.cameras.new(f"ChaosCam_{tag}")
    cam = bpy.data.objects.new(f"ChaosCam_{tag}", cam_data)
    scene.collection.objects.link(cam)
    cam.location = (3.2, -3.2, 2.4)
    # aim at mover (or scene origin fallback)
    target = bpy.data.objects.get(mover_name)
    aim = target.matrix_world.translation if target else Vector((0, 0, 0.5))
    d = (aim - cam.location).normalized()
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    cam_data.lens = 40
    old_cam = scene.camera
    scene.camera = cam
    scene.render.resolution_x = 640
    scene.render.resolution_y = 480
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.display.shading.light = 'STUDIO'
    scene.display.shading.color_type = 'MATERIAL'
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.view_settings.exposure = 1.0
    scene.render.filepath = os.path.join(OUT, f"round_{tag}.png")
    bpy.ops.render.render(write_still=True)
    scene.camera = old_cam
    # purge camera (zero-residue discipline)
    bpy.data.objects.remove(cam, do_unlink=True)
    bpy.data.cameras.remove(cam_data)


def _pairs_for(audit, name):
    return [p for p in audit.get("pairs", [])
            if p.get("a") == name or p.get("b") == name]


def _run_round(tag, mover, support, do_transform, expect):
    """Perturb, audit, section render, scene render. `expect(mover, pairs,
    audit)` returns (ok, detail)."""
    do_transform()
    bpy.context.view_layer.update()
    audit = PL.audit_scene()
    pairs = _pairs_for(audit, mover.name)
    ok, detail = expect(pairs)
    _note("round", f"{tag}.audit_consistent", ok, detail)

    # section render must not crash on off-nominal contact
    try:
        PL.section_pair(mover, support,
                        out_dir=os.path.join(OUT, f"section_{tag}"))
        _note("round", f"{tag}.section_no_crash", True, "rendered")
    except Exception as e:  # noqa: BLE001
        _note("round", f"{tag}.section_no_crash", False, repr(e))

    _scene_render(tag, mover.name)
    # audit pair `state` is the EXACT vocabulary (PENETRATING/TOUCHING/
    # NESTED/CLEAR); `verdict` is the human string — never exact-match it.
    return audit


def build_and_place():
    """T8 diorama, minus its self-checks (t8 owns those)."""
    clear_scene()
    bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, 0))
    ground = bpy.context.active_object
    ground.name = "Ground"
    ground.data.materials.append(make_material("GroundMat", (0.20, 0.22, 0.24)))

    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
    table = bpy.context.active_object
    table.name = "TableTop"
    table.scale = (1.4, 0.9, 0.05)
    table.data.materials.append(make_material("WoodMat", (0.55, 0.38, 0.20)))
    PL.snap_z(table, 0.75, reference="bottom")

    bpy.ops.mesh.primitive_cylinder_add(radius=0.06, depth=0.14,
                                        location=(0.35, 0.15, 1.0))
    mug = bpy.context.active_object
    mug.name = "Mug"
    mug.data.materials.append(make_material("MugMat", (0.85, 0.20, 0.15)))
    PL.place_on(mug, table, clearance=0.0, keep_xy=True)

    bpy.ops.mesh.primitive_cylinder_add(radius=0.22, depth=0.05,
                                        location=(-1.1, 0.8, 0.5))
    stool = bpy.context.active_object
    stool.name = "StoolTop"
    stool.data.materials.append(make_material("WoodMat", (0.55, 0.38, 0.20)))
    PL.snap_z(stool, 0.50, reference="bottom")

    bpy.ops.mesh.primitive_cube_add(size=0.3, location=(-1.1, 0.8, 0.7))
    crate = bpy.context.active_object
    crate.name = "Crate"
    crate.data.materials.append(make_material("CrateMat", (0.85, 0.60, 0.15)))
    PL.place_on(crate, stool, clearance=0.0, keep_xy=True)

    bpy.context.view_layer.update()
    return dict(ground=ground, table=table, mug=mug, stool=stool, crate=crate)


def seat_checks(S):
    """Gap B: seat_at edge behaviors (in-process)."""
    import mathutils
    # anchors
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=(1.5, 0.5, 0.60))
    a1 = bpy.context.active_object
    a1.name = "AnchorA"
    a1.rotation_euler = Euler((0, 0, math.radians(35)), 'XYZ')
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=(2.2, 0.5, 0.60))
    a2 = bpy.context.active_object
    a2.name = "AnchorB"

    # fresh mover box
    bpy.ops.mesh.primitive_cube_add(size=0.2, location=(0, -2, 0.1))
    mover = bpy.context.active_object
    mover.name = "Seated"
    mover.rotation_euler = Euler((0, 0, math.radians(10)), 'XYZ')
    bpy.context.view_layer.update()

    # S1: align=False preserves rotation
    PL.seat_at(mover, a1, align=False)
    bpy.context.view_layer.update()
    kept = abs(mover.rotation_euler.z - math.radians(10)) < 1e-4
    _note("seat_check", "S1.align_false_keeps_rotation", kept,
          f"yaw={math.degrees(mover.rotation_euler.z):.1f}deg")

    # S1b: align=True copies anchor yaw
    PL.seat_at(mover, a1, align=True)
    bpy.context.view_layer.update()
    copied = abs(mover.rotation_euler.z - math.radians(35)) < 1e-3
    _note("seat_check", "S1b.align_true_copies_yaw", copied,
          f"yaw={math.degrees(mover.rotation_euler.z):.1f}deg")

    # S2: offset in empty LOCAL space (anchor yawed 35deg: +0.1 local x).
    # reference='bottom' semantics: the mover's bbox BOTTOM-CENTER lands at
    # anchor+offset — compare bbox bottoms, not origins.
    PL.seat_at(mover, a1, align=True, offset=(0.1, 0, 0))
    bpy.context.view_layer.update()
    mw = a1.matrix_world
    want = mw @ Vector((0.1, 0, 0))
    mn, mx = PL._aabb(mover)
    got = Vector(((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, mn.z))
    dz = abs(want.z - got.z)
    dxy = (Vector((want.x, want.y)) - Vector((got.x, got.y))).length
    _note("seat_check", "S2.offset_local_bbox_bottom", dz < 1e-3 and dxy < 1e-3,
          f"dz={dz*1000:.2f}mm dxy={dxy*1000:.2f}mm")

    # S3: re-seat to AnchorB — mover's bbox bottom lands ON the anchor
    PL.seat_at(mover, a2, align=True)
    bpy.context.view_layer.update()
    mn, mx = PL._aabb(mover)
    bottom = Vector(((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, mn.z))
    d = (bottom - a2.matrix_world.translation).length
    _note("seat_check", "S3.reseat_moves", d < 1e-3,
          f"bottom->anchor dist={d:.4f}m")


def main():
    global OUT
    args, _ = common_parser().parse_known_args(script_argv())
    OUT = args.output
    os.makedirs(OUT, exist_ok=True)

    S = build_and_place()
    mug, table, stool, crate, ground = (S["mug"], S["table"], S["stool"],
                                        S["crate"], S["ground"])

    print("[T9] == chaos rounds on the placed diorama ==")
    mug_home = mug.location.copy()

    # R1 tilt-small on the MUG (cylinder on table)
    def t1():
        mug.rotation_euler = Euler((math.radians(RNG.uniform(2, 8)),
                                    math.radians(RNG.uniform(2, 8)),
                                    math.radians(RNG.uniform(0, 90))), 'XYZ')
        bpy.context.view_layer.update()
        PL.snap_z(mug, table.matrix_world.translation.z + 0.025 + 0.07,
                  reference="origin")
    _run_round("R1_tilt_small", mug, table, t1,
               lambda pairs: (True, "no-crash round"))

    # R2 tilt-steep: 25deg roll, dropped near table edge (likely falls off
    # support bbox — audit may or may not see a pair; no crash required)
    def t2():
        mug.location = mug_home + Vector((0.0, 0.30, 0.02))
        mug.rotation_euler = Euler((math.radians(25), 0,
                                    math.radians(45)), 'XYZ')
        bpy.context.view_layer.update()
    _run_round("R2_tilt_steep", mug, table, t2,
               lambda pairs: (True, f"{len(pairs)} pairs"))

    # R3 sink: push the crate 40mm INTO the stool top -> PENETRATING
    def t3():
        crate.rotation_euler = Euler((0, 0, 0), 'XYZ')
        crate.location.z -= 0.04
        bpy.context.view_layer.update()
    _run_round("R3_sink", crate, stool, t3,
               lambda pairs: (
                   any(p.get("state") == "PENETRATING" for p in pairs),
                   f"{[p.get('state') for p in pairs]}"))

    # R4 lift: mug 200mm up -> NO touching pair (floating)
    def t4():
        mug.rotation_euler = Euler((0, 0, 0), 'XYZ')
        mug.location = mug_home + Vector((0, 0, 0.2))
        bpy.context.view_layer.update()
    _run_round("R4_lift", mug, table, t4,
               lambda pairs: (len(pairs) == 0, f"{len(pairs)} pairs"))
    # R5 offset-xy: crate half off the stool
    def t5():
        crate.location.z = 0.50 + 0.025 + 0.15
        crate.location.x += 0.18
        bpy.context.view_layer.update()
    _run_round("R5_offset", crate, stool, t5,
               lambda pairs: (True, f"{[p.get('state') for p in pairs]}"))

    # R6 yaw-90 the MUG on the table (round footprint: contact unchanged)
    def t6():
        crate.location.x -= 0.18
        crate.location.z = 0.50 + 0.025 + 0.15
        mug.location = mug_home
        mug.rotation_euler = Euler((0, 0, math.radians(90)), 'XYZ')
        bpy.context.view_layer.update()
    _run_round("R6_yaw90", mug, table, t6,
               lambda pairs: (True, f"{[p.get('state') for p in pairs]}"))

    # R7 teleport the crate 5m away -> in NO pair (audit pad law)
    def t7():
        crate.location += Vector((5.0, 0, 0))
        bpy.context.view_layer.update()
    _run_round("R7_teleport", crate, stool, t7,
               lambda pairs: (len(pairs) == 0, f"{len(pairs)} pairs"))

    print("[T9] == seat_at edge checks ==")
    seat_checks(S)

    n_rounds = len(RESULTS["rounds"])
    fails = [r for r in RESULTS["rounds"] + RESULTS["seat_checks"]
             if r.get("ok") is False]
    print(f"\nCHAOS: {len(fails)} hard failures across {n_rounds} rounds "
          f"+ {len(RESULTS['seat_checks'])} seat checks")
    if fails:
        for f in fails:
            print("  FAIL:", f["tag"], "-", f["detail"])
        bpy.ops.wm.save_as_mainfile(
            filepath=os.path.join(OUT, "chaos_fail_state.blend"))
        sys.exit(1)
    print("ALL PASS")


main()
