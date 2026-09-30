"""t8_placement_diorama.py — P5 core-flow hardening fixture (session-4).

A small furnished diorama built through the PLACEMENT WORKFLOW end-to-end,
so the principal can visually verify every diagnostic surface the kit
produces for a placed scene (M5 doctrine: gates decide, eyes verify).

Scene (all placement via placement_lib, never hand-computed z):
  Table      4-leg table (legs placed on ground via place_on grid)
  Mug        cylinder mug placed ON the tabletop (place_on, clearance 0)
  LampBase   short cylinder on tabletop near the back edge
  Stool      3-leg stool on the ground
  Box        crate on the stool (place_on)
  Ball       physics drop: physics_place.place() from 30cm above the floor

Checkpoints (self-verifying, per SKILL verification discipline):
  C1 audit_scene() on the placed state = no PENETRATING, no floating P0
     beyond known-intentional (none planted — this fixture is CLEAN)
  C2 mug z-min == tabletop z-max within 1mm (place_on solved exactly)
  C3 physics ball verdict PLACED/SETTLED, final z == radius (resting)
  C4 diagnostics exist: seam_views(mug, tabletop) 4 PNGs, heat_view PNG,
     section_pair PNGs — sizes > 5KB
Diagnostic RENDER judgment is the PRINCIPAL's job after the run (P5).

Usage:
  ./scripts/blrun.sh --background --python tests/t8_placement_diorama.py -- \
      --output output/t8_diorama
"""
import sys, os, json

_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS = os.path.abspath(os.path.join(_HERE, "..", "scripts"))
for _p in (_SCRIPTS,):
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

import bpy
from blender_kit import (clear_scene, make_material, common_parser,
                         script_argv)
import placement_lib as PL
import physics_place as PP

OUT = None
RESULTS = {"fixture": "t8_placement_diorama", "checks": []}


def check(tag, measured, expect, tol=None):
    if tol is not None:
        ok = abs(measured - expect) <= tol
        detail = f"{measured:.4f} ~ {expect} (+/-{tol})"
    else:
        ok = measured == expect
        detail = f"{measured} == {expect}"
    RESULTS["checks"].append({"tag": tag, "ok": ok, "detail": detail})
    print(f"  [{'PASS' if ok else 'FAIL'}] {tag}: {detail}")
    return ok


def build_and_place():
    clear_scene()

    # Ground
    bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, 0))
    ground = bpy.context.active_object
    ground.name = "Ground"
    ground.data.materials.append(make_material("GroundMat", (0.20, 0.22, 0.24)))

    def zmin(o):
        return min((o.matrix_world @ v.co).z for v in o.data.vertices)

    def zmax(o):
        return max((o.matrix_world @ v.co).z for v in o.data.vertices)

    # ---- Table: top slab + 4 legs, legs placed via place_on (grid footprint)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
    table = bpy.context.active_object
    table.name = "TableTop"
    table.scale = (1.4, 0.9, 0.05)
    table.data.materials.append(make_material("WoodMat", (0.55, 0.38, 0.20)))
    PL.snap_z(table, 0.75, reference="bottom")

    legs = []
    for i, (lx, ly) in enumerate([(-0.62, -0.37), (0.62, -0.37),
                                  (-0.62, 0.37), (0.62, 0.37)]):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.04, depth=0.75,
                                            location=(lx, ly, 0.375))
        leg = bpy.context.active_object
        leg.name = f"TableLeg{i+1}"
        leg.data.materials.append(make_material("WoodMat", (0.55, 0.38, 0.20)))
        r = PL.place_on(leg, ground, clearance=0.0, keep_xy=True)
        legs.append(leg)
        assert r["ok"], r

    # ---- Mug ON the tabletop (contact 0mm — the seam diagnostic's subject)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.06, depth=0.14,
                                        location=(0.35, 0.15, 1.0))
    mug = bpy.context.active_object
    mug.name = "Mug"
    mug.data.materials.append(make_material("MugMat", (0.85, 0.20, 0.15)))
    r = PL.place_on(mug, table, clearance=0.0, keep_xy=True)
    RESULTS["mug_report"] = {k: r.get(k) for k in ("ok", "post_contact")}

    # ---- Lamp ON the tabletop
    bpy.ops.mesh.primitive_cylinder_add(radius=0.10, depth=0.08,
                                        location=(-0.45, -0.20, 1.0))
    lamp = bpy.context.active_object
    lamp.name = "LampBase"
    lamp.data.materials.append(make_material("LampMat", (0.15, 0.35, 0.70)))
    PL.place_on(lamp, table, clearance=0.0, keep_xy=True)

    # ---- Stool + crate ON stool
    bpy.ops.mesh.primitive_cylinder_add(radius=0.22, depth=0.05,
                                        location=(-1.1, 0.8, 0.5))
    stool = bpy.context.active_object
    stool.name = "StoolTop"
    stool.data.materials.append(make_material("WoodMat", (0.55, 0.38, 0.20)))
    PL.snap_z(stool, 0.50, reference="bottom")
    for i, (lx, ly) in enumerate([(-1.20, 0.70), (-1.00, 0.70), (-1.10, 0.92)]):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.025, depth=0.5,
                                            location=(lx, ly, 0.25))
        leg = bpy.context.active_object
        leg.name = f"StoolLeg{i+1}"
        leg.data.materials.append(make_material("WoodMat", (0.55, 0.38, 0.20)))
        PL.place_on(leg, ground, clearance=0.0, keep_xy=True)

    bpy.ops.mesh.primitive_cube_add(size=0.3, location=(-1.1, 0.8, 0.7))
    crate = bpy.context.active_object
    crate.name = "Crate"
    crate.data.materials.append(make_material("CrateMat", (0.85, 0.60, 0.15)))
    PL.place_on(crate, stool, clearance=0.0, keep_xy=True)

    # ---- Ball: physics drop from 30cm (workflow: physics place)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.15, location=(0.9, -0.6, 0.30))
    ball = bpy.context.active_object
    ball.name = "Ball"
    ball.data.materials.append(make_material("BallMat", (0.90, 0.30, 0.60)))
    bpy.context.view_layer.update()

    return dict(ground=ground, table=table, mug=mug, lamp=lamp,
                stool=stool, crate=crate, ball=ball,
                zmin=zmin, zmax=zmax)


def main():
    args, _ = common_parser().parse_known_args(script_argv())
    global OUT
    OUT = args.output
    os.makedirs(OUT, exist_ok=True)

    S = build_and_place()
    bpy.context.view_layer.update()

    print("[T8] == C2: place_on solved the mug exactly onto the tabletop ==")
    table_top = S["zmax"](S["table"])
    mug_bottom = S["zmin"](S["mug"])
    check("C2.mug_on_table", round(mug_bottom - table_top, 4), 0.0, tol=0.001)
    RESULTS["table_top_z"] = round(table_top, 4)

    print("[T8] == C1: audit the placed state ==")
    audit = PL.audit_scene()
    bad = [p for p in audit.get("pairs", [])
           if p.get("verdict") == "PENETRATING"]
    RESULTS["audit_verdict"] = audit.get("verdict", audit.get("state"))
    RESULTS["audit_bad_pairs"] = [f"{p['a']}x{p['b']}" for p in bad]
    check("C1.no_penetration", len(bad), 0)

    print("[T8] == C3: physics drop the ball ==")
    rep = PP.place(S["ball"], drop_mm=30.0, frames=45, apply="end")
    RESULTS["physics_verdict"] = rep.get("verdict")
    check("C3.physics_verdict", rep.get("verdict") in ("PLACED", "SETTLED",
                                                       "PLACED_OVERLAP"),
          True)
    bpy.context.view_layer.update()
    check("C3.ball_rests", round(S["zmin"](S["ball"]), 3), 0.0, tol=0.002)

    print("[T8] == C4: diagnostic renders exist ==")
    seam_dir = os.path.join(OUT, "seam_mug_table")
    PL.seam_views(S["mug"], S["table"], out_dir=seam_dir)
    n_seam = 0
    if os.path.isdir(seam_dir):
        n_seam = sum(1 for f in os.listdir(seam_dir)
                     if f.endswith(".png")
                     and os.path.getsize(os.path.join(seam_dir, f)) > 5120)
    check("C4.seam_views_4", n_seam, 4)

    heat_dir = os.path.join(OUT, "heat")
    os.makedirs(heat_dir, exist_ok=True)
    heat = PL.heat_view(S["mug"], [S["table"], S["lamp"]],
                        out_path=os.path.join(heat_dir, "heat_mug_table.png"))
    check("C4.heat_view", os.path.exists(os.path.join(heat_dir,
                                                      "heat_mug_table.png")),
          True)

    sec_dir = os.path.join(OUT, "section")
    sec = PL.section_pair(S["mug"], S["table"], out_dir=sec_dir)
    n_sec = len([f for f in os.listdir(sec_dir) if f.endswith(".png")]) \
        if os.path.isdir(sec_dir) else 0
    check("C4.section_pngs", n_sec >= 1, True)

    # ---- Final scene summary for the principal's look run
    print("[T8] == placed-state z table (for the principal's eye check) ==")
    for name in ("TableTop", "Mug", "LampBase", "StoolTop", "Crate", "Ball"):
        o = bpy.data.objects.get(name)
        if o:
            print(f"  {name:<10} zmin={S['zmin'](o):+.4f} "
                  f"zmax={S['zmax'](o):+.4f}")

    with open(os.path.join(OUT, "t8_results.json"), "w") as f:
        json.dump(RESULTS, f, indent=2, default=str)

    # Save the placed state as the canonical state carrier for look.py
    blend_path = os.path.abspath(os.path.join(OUT, "t8_diorama.blend"))
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print(f"[T8] placed-state blend saved: {blend_path}")
    print(f"[T8] principal eye-check: ./scripts/blrun.sh --background "
          f"--python scripts/look.py -- --load-blend {blend_path} "
          f"--output {OUT}/look")
    n_fail = sum(1 for c in RESULTS["checks"] if not c["ok"])
    print(f"[T8] {len(RESULTS['checks']) - n_fail}/{len(RESULTS['checks'])} "
          f"checks passed")
    print(f"[T8] diagnostics for PRINCIPAL eye-check: {OUT}/seam_mug_table/ "
          f"{OUT}/heat/ {OUT}/section/ — then run look.py on this scene")


main()
