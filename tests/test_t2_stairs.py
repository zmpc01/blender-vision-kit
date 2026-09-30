"""test_t2_stairs.py — T2: precise stair placement (the user's flagship
case: "riggerd humanoid on stair number 2, legs almost touching").

Builds 4 steps + a blocky humanoid figure (feet at z=0), then:
  1. place_on(Figure, Step2) with clearance=0   -> expect bottom EXACTLY at
     step-2 top (z=0.36), state TOUCHING, 0 penetration
  2. place_on with clearance=0.005 (5mm)        -> bottom at 0.365, CLEAR 5mm
  3. sabotage: move figure to z=0.34 (20mm into the step) -> audit flags
     PENETRATING ~20mm
  4. sabotage: floating 3cm -> audit flags CLEAR 30mm (touch band no-trap)
  5. ascii_height_map shows the staircase bands (numeric text-map check)
  6. multi-level support: figure straddling steps 2+3 -> multi_level flag
Runs INSIDE Blender via run.sh.
"""
import sys, json, os
# placement_lib lives in the kit's scripts/ (sibling of tests/); the
# PLACEMENT_LAB env fallback points at the placement-lab R&D repo. Try both.
_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS = os.path.abspath(os.path.join(_HERE, "..", "scripts"))
_LAB_LIB = os.path.join(os.environ.get("PLACEMENT_LAB", "/home/z/placement-lab"), "lib")
for _p in (_SCRIPTS, _LAB_LIB):
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)
import bpy
import placement_lib as PL
from mathutils import Vector as _Vector

_REPO_ROOT = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), ".."))
_OUT_ROOT = os.environ.get("KIT_OUT",
                           os.path.join(_REPO_ROOT, "output", "tests"))
OUT = os.path.join(_OUT_ROOT, "t2_results.json")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
FAILS = []


def check(label, got, expect, tol=None):
    ok = (abs(got - expect) <= tol) if tol is not None else (got == expect)
    if not ok:
        FAILS.append(f"{label}: got {got!r} expected {expect!r}")
    return ok


def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def box(name, size, loc, color=(0.6, 0.6, 0.65)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc,
                                    scale=(size[0], size[1], size[2]))
    o = bpy.context.active_object
    o.name = name
    m = bpy.data.materials.new(name + "_m")
    m.diffuse_color = (*color, 1.0)
    o.data.materials.append(m)
    return o


def build_stairs(n=4, rise=0.18, run=0.3, width=1.2):
    objs = []
    for i in range(1, n + 1):
        o = box(f"Step{i}", (width, run, rise * i),
                (0, (i - 1) * run + run / 2, rise * i / 2))
        objs.append(o)
    return objs


def build_figure(name="Figure"):
    """Blocky humanoid, ONE joined mesh, feet at z=0 (world), +Y facing."""
    torso = box("t", (0.36, 0.2, 0.55), (0, 0, 1.015))
    head = box("h", (0.18, 0.18, 0.18), (0, 0, 1.38))
    legL = box("lL", (0.12, 0.14, 0.74), (-0.09, 0, 0.37))
    legR = box("lR", (0.12, 0.14, 0.74), (0.09, 0, 0.37))
    armL = box("aL", (0.09, 0.09, 0.5), (-0.24, 0, 1.0))
    armR = box("aR", (0.09, 0.09, 0.5), (0.24, 0, 1.0))
    objs = [torso, head, legL, legR, armL, armR]
    bpy.ops.object.select_all(action='DESELECT')  # critical: steps/ground
    bpy.context.view_layer.objects.active = torso # are still selected!
    for o in objs:
        o.select_set(True)
    bpy.ops.object.join()
    fig = bpy.context.active_object
    fig.name = name
    # bake mesh into world coords (join keeps torso's offset origin which
    # would otherwise displace the figure when we set location afterwards)
    bpy.ops.object.transform_apply(location=True, scale=True)
    for o in bpy.data.objects:
        o.select_set(False)
    return fig


def main():
    R = {}
    clear()
    ground = box("Ground", (12, 12, 0.1), (0, 0, -0.05), (0.35, 0.4, 0.35))
    steps = build_stairs()
    step2_top = 2 * 0.18  # 0.36
    fig = build_figure()
    fig.location = (0, 0.45, 0.0)   # feet over step 2 (y in [0.3,0.6])
    bpy.context.view_layer.update()

    # -- 1. one-shot: rest on step 2, exact contact ------------------------
    r1 = PL.place_on(fig, steps[1], clearance=0.0, footprint='bottom')
    mn, _ = PL._aabb(fig)
    print(f"[T2] place_on rest: z_bottom={mn.z:.5f} (expect {step2_top}) "
          f"ok={r1['ok']} state={r1['post_contact'][0]['state']} "
          f"multi_level={r1['multi_level']} timings={r1['timings_ms']}ms")
    check("rest.bottom_z", round(mn.z, 4), round(step2_top, 4), tol=0.0015)
    check("rest.state", r1["post_contact"][0]["state"], "TOUCHING")
    check("rest.ok", r1["ok"], True)
    check("rest.multi_level", r1["multi_level"], False)
    R["rest"] = r1

    # -- 2. 5mm clearance ---------------------------------------------------
    fig.location.z -= 0.2  # start below, solver must recover
    bpy.context.view_layer.update()
    PL.clear_bvh_cache()
    r2 = PL.place_on(fig, steps[1], clearance=0.005, footprint='bottom')
    mn, _ = PL._aabb(fig)
    print(f"[T2] place_on 5mm: z_bottom={mn.z:.5f} (expect {step2_top + 0.005}) "
          f"state={r2['post_contact'][0]['state']} "
          f"clear={r2['post_contact'][0]['clearance_mm']}mm")
    check("clear5.bottom_z", round(mn.z, 4), round(step2_top + 0.005, 4),
          tol=0.0015)
    check("clear5.state", r2["post_contact"][0]["state"], "CLEAR")
    R["clear5"] = r2

    # -- 3. sabotage: 20mm into the step ------------------------------------
    fig.location.z = 0.34
    bpy.context.view_layer.update()
    PL.clear_bvh_cache()
    a3 = PL.audit_scene(pairs=[["Figure", "Step2"]])
    p3 = a3["pairs"][0]
    print(f"[T2] sabotaged pen: {p3['state']} pen={p3['penetration_mm']}mm "
          f"failed={a3['failed']}")
    check("sab.state", p3["state"], "PENETRATING")
    check("sab.pen", p3["penetration_mm"], 20.0, tol=0.5)
    check("sab.failed", a3["failed"], True)
    R["sabotage_pen"] = p3

    # -- 4. sabotage: floating 30mm -----------------------------------------
    fig.location.z = 0.39
    bpy.context.view_layer.update()
    PL.clear_bvh_cache()
    a4 = PL.audit_scene(pairs=[["Figure", "Step2"]])
    p4 = a4["pairs"][0]
    print(f"[T2] sabotaged float: {p4['state']} clear={p4['clearance_mm']}mm")
    check("float.state", p4["state"], "CLEAR")
    check("float.clear", p4["clearance_mm"], 30.0, tol=1.0)
    R["sabotage_float"] = p4

    # -- 5. ascii height map (numeric text-map check) -----------------------
    txt, legend = PL.ascii_height_map(
        region=((-0.8, -0.2), (0.8, 1.5)), supports=[ground] + steps, grid=40)
    print(f"[T2] height map:\n{txt}\n{legend}")
    check("asciimap.staircase", ("5" in txt or "6" in txt), True)
    R["ascii"] = {"map": txt, "legend": legend}

    # -- 6. multi-level: figure straddles steps 2 and 3 ---------------------
    fig.location = (0, 0.6, 0.3)   # feet over the step2/step3 boundary
    bpy.context.view_layer.update()
    PL.clear_bvh_cache()
    r6 = PL.place_on(fig, steps[1], steps[2], clearance=0.0,
                     footprint='bottom')
    mn, _ = PL._aabb(fig)
    print(f"[T2] straddle: multi_level={r6['multi_level']} "
          f"z_bottom={mn.z:.4f} (expect ~0.54 on step3) "
          f"states={[p['state'] for p in r6['post_contact']]}")
    R["straddle"] = r6

    # -- 7. slope align orientation (code-review gate P0 regression) --------
    # A tilted ramp + align_to_surface: the object's world +Z must END UP
    # aligned with the surface normal (the '-Z' track quat flipped objects
    # upside-down while contact checks false-passed).
    import math as _m
    from mathutils import Matrix as _Matrix
    ramp = box("RampSlope", (1.2, 1.2, 0.08), (4.0, 4.0, 0.14))
    ramp.rotation_euler = (0, _m.radians(15), 0)
    bpy.context.view_layer.update()
    crate = box("CrateSlope", (0.4, 0.4, 0.4), (4.0, 4.0, 1.2))
    bpy.context.view_layer.update()
    PL.clear_bvh_cache()
    r7 = PL.place_on(crate, ramp, clearance=0.0, align_to_surface=True)
    wz = (crate.matrix_world.to_3x3() @ _Vector((0, 0, 1))).normalized()
    dotp = wz.dot(_Vector(r7.get("surface_normal", (0, 0, 1))))
    ok7 = dotp > 0.9 and r7.get("aligned_to_surface") is True
    if not ok7:
        FAILS.append(f"slope align: +Z.normal={dotp:.3f} aligned={r7.get('aligned_to_surface')}")
    print(f"[T2] slope_align: +Z.normal={dotp:.3f} "
          f"state={[p['state'] for p in r7['post_contact']]} "
          f"({'PASS' if ok7 else 'FAIL'})")
    R["slope_align"] = r7

    verdict = "FAIL:\n" + "\n".join(FAILS) if FAILS else "ALL PASS"
    with open(OUT, "w") as f:
        json.dump({"fail": FAILS, "results": R}, f, indent=2, default=str)
    print(f"[T2] {verdict}")


main()
