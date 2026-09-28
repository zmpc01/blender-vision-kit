"""test_t3_jeep.py — T3: jeep + driver placement (seat_at / place_on /
sabotage / seam views / heat bake / previz render).

Builds a pure-primitive jeep (chassis + hood + cushion + seatback + 4
wheels) and a capsule driver per kit AGENTS.md #32 (no armatures/rigs):
cylinder torso + sphere head + 2 forward legs, JOINED into ONE mesh
"Driver" (local forward = +Y; hood faces +X).

  1. SEATED  seat_at(Driver, SeatAnchor, reference='bottom', align=True)
     -> Driver z-min == cushion top 0.77 (+-2mm); (Driver,SeatCushion)
     TOUCHING or CLEAR <=1mm; (Driver,SeatBack) not penetrating (report
     distance); (Driver,Hood) legs->hood distance reported
  2. STAND   place_on(Driver, JeepChassis, clearance=0) one-shot from a
     sunk start -> z-min == chassis top 0.65 (+-2mm), TOUCHING
  3. SABOTAGE translate Driver 0.3 along its local -Y (backward) -> torso
     inside SeatBack; audit_scene flags PENETRATING with pen_mm; then
     seam_views(Driver, SeatBack) -> 4 PNGs exist, >5KB
  4. HEAT    heat_bake(Driver, [cushion, seatback, hood]) + workbench
     VERTEX FLAT render 640x360 -> t3_heat.png
  5. VERDICT "ALL PASS" / "FAIL: ..." + JSON -> t3_results.json
  6. VIEWPORT-CHECK render: workbench MATERIAL 3/4 view -> t3_scene.png
Runs INSIDE Blender via blender-kit run.sh.
"""
import sys, os, json, math
# placement_lib lives in the kit's scripts/ (sibling of tests/); the
# PLACEMENT_LAB env fallback points at the placement-lab R&D repo. Try both.
_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS = os.path.abspath(os.path.join(_HERE, "..", "scripts"))
_LAB_LIB = os.path.join(os.environ.get("PLACEMENT_LAB", "/home/z/placement-lab"), "lib")
for _p in (_SCRIPTS, _LAB_LIB):
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)
import bpy
from mathutils import Vector
import placement_lib as PL

_REPO_ROOT = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), ".."))
_OUT_ROOT = os.environ.get("KIT_OUT",
                           os.path.join(_REPO_ROOT, "output", "tests"))
OUT = os.path.join(_OUT_ROOT, "t3_results.json")
SEAM_DIR = os.path.join(_OUT_ROOT, "t3_seam")
HEAT_PNG = os.path.join(_OUT_ROOT, "t3_heat.png")
SCENE_PNG = os.path.join(_OUT_ROOT, "t3_scene.png")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
FAILS = []


def check(label, got, expect, tol=None):
    ok = (abs(got - expect) <= tol) if tol is not None else (got == expect)
    if not ok:
        FAILS.append(f"{label}: got {got!r} expected {expect!r}")
    return ok


def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def mat_for(name, color):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1.0)   # workbench MATERIAL reads this (#34)
    return m


def box(name, size, loc, color):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc,
                                    scale=(size[0], size[1], size[2]))
    o = bpy.context.active_object
    o.name = name
    o.data.materials.append(mat_for(name + "_m", color))
    return o


def cyl(name, r, depth, loc, rot=(0, 0, 0), color=(0.5, 0.5, 0.5)):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth, location=loc,
                                        rotation=rot, vertices=32)
    o = bpy.context.active_object
    o.name = name
    o.data.materials.append(mat_for(name + "_m", color))
    return o


def sph(name, r, loc, color=(0.5, 0.5, 0.5)):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc,
                                         segments=24, ring_count=16)
    o = bpy.context.active_object
    o.name = name
    o.data.materials.append(mat_for(name + "_m", color))
    return o


def build_jeep():
    """Hood at +X. Chassis z[0.5,0.65]; cushion z[0.65,0.77] at x=-0.4;
    seatback flush against the cushion's rear edge (front face x=-0.65)."""
    box("Ground", (12, 12, 0.1), (0, 0, -0.05), (0.35, 0.4, 0.35))
    chassis = box("JeepChassis", (3.2, 1.6, 0.15), (0, 0, 0.575),
                  (0.25, 0.27, 0.30))
    hood = box("Hood", (1.0, 1.6, 0.6), (1.1, 0, 0.95), (0.75, 0.12, 0.10))
    cushion = box("SeatCushion", (0.5, 0.5, 0.12), (-0.4, 0, 0.71),
                  (0.10, 0.10, 0.12))
    seatback = box("SeatBack", (0.12, 0.5, 0.5), (-0.71, 0, 0.90),
                   (0.15, 0.15, 0.18))
    wheels = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            nm = f"Wheel{'F' if sx > 0 else 'R'}{'L' if sy > 0 else 'R'}"
            wheels.append(cyl(nm, 0.25, 0.2, (1.1 * sx, 0.75 * sy, 0.25),
                              rot=(math.pi / 2, 0, 0), color=(0.05, 0.05, 0.05)))
    return {"chassis": chassis, "hood": hood, "cushion": cushion,
            "seatback": seatback, "wheels": wheels}


def build_driver():
    """Capsule actor (kit policy #32): torso cyl r0.18 d0.6 vertical +
    sphere head r0.11 + 2 legs r0.08 pointing +Y (local forward).
    Built at staging spot (x=0, y=1.6), butt/torso bottom at z=0.9.
    ONE joined mesh; transforms applied; forward extent F=0.30 keeps the
    AABB bottom-CENTER seat_at anchor from jamming the torso into the
    seatback (torso back ends 10mm clear of the seatback front face)."""
    t = cyl("d_torso", 0.18, 0.6, (0, 1.6, 1.2), color=(1.0, 0.45, 0.1))
    h = sph("d_head", 0.11, (0, 1.6, 1.44), color=(1.0, 0.45, 0.1))
    lL = cyl("d_legL", 0.08, 0.25, (-0.09, 1.775, 0.98),
             rot=(math.pi / 2, 0, 0), color=(1.0, 0.45, 0.1))
    lR = cyl("d_legR", 0.08, 0.25, (0.09, 1.775, 0.98),
             rot=(math.pi / 2, 0, 0), color=(1.0, 0.45, 0.1))
    bpy.ops.object.select_all(action='DESELECT')  # selection-leak guard
    bpy.context.view_layer.objects.active = t
    for o in (t, h, lL, lR):
        o.select_set(True)
    bpy.ops.object.join()
    drv = bpy.context.active_object
    drv.name = "Driver"
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for o in bpy.data.objects:
        o.select_set(False)
    return drv


def make_cam(name, loc, target, lens=50):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    c = bpy.data.objects.new(name, cd)
    bpy.context.scene.collection.objects.link(c)
    c.location = loc
    d = (Vector(target) - Vector(loc)).normalized()
    c.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    return c


def wb_setup(color_type, light):
    """Workbench render config for F12 renders (display.shading worked in
    R2 on this build; render_shading set too when present, belt+suspenders)."""
    sc = bpy.context.scene
    shs = [sc.display.shading]
    rs = getattr(sc.display, "render_shading", None)
    if rs is not None:
        shs.append(rs)
    for sh in shs:
        sh.light = light
        sh.color_type = color_type
        sh.show_shadows = False
        try:
            sh.background_type = 'WORLD'
        except Exception:
            pass
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.render.resolution_x = 640
    sc.render.resolution_y = 360


def move_center_to(obj, x, y):
    """Translate obj so its world AABB xy-center lands at (x, y)."""
    bpy.context.view_layer.update()
    mn, mx = PL._aabb(obj)
    obj.location.x += x - (mn.x + mx.x) / 2
    obj.location.y += y - (mn.y + mx.y) / 2
    bpy.context.view_layer.update()


def zmin(obj):
    mn, _ = PL._aabb(obj)
    return mn.z


def main():
    R = {}
    clear()
    w = bpy.data.worlds.new("World")
    w.use_nodes = False
    w.color = (0.85, 0.85, 0.85)
    bpy.context.scene.world = w

    jeep = build_jeep()
    drv = build_driver()

    # -- pre-flight: driver bottom verts (gotcha #9 origin trap check) ------
    bot = PL.surface_samples(drv, mode='bottom')
    zs = sorted({round(p.z, 4) for p in bot})
    print(f"[T3] driver bottom samples: n={len(bot)} z_levels={zs[:8]}")
    check("driver.bottom_z", round(min(zs), 4), 0.9, tol=0.0015)
    check("driver.n_bottom", len(bot) > 5, True)
    R["driver_bottom"] = {"n": len(bot), "z_levels": zs[:8]}

    # -- SeatAnchor: cushion top center, +Z up, -Y toward SeatBack ----------
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=(-0.4, 0, 0.77),
                             rotation=(0, 0, -math.pi / 2))
    anchor = bpy.context.active_object
    anchor.name = "SeatAnchor"
    ax = anchor.matrix_world.to_3x3()
    neg_y = ax @ Vector((0, -1, 0))
    pos_y = ax @ Vector((0, 1, 0))
    to_back = Vector((-0.71 - (-0.4), 0 - 0)).normalized()  # toward seatback
    d_back = Vector((neg_y.x, neg_y.y)).normalized().dot(to_back)
    d_hood = Vector((pos_y.x, pos_y.y)).normalized().dot(Vector((1, 0)))
    print(f"[T3] anchor -Y*to_seatback={d_back:.3f}  +Y*to_hood={d_hood:.3f}")
    check("anchor.negY_faces_seatback", round(d_back, 2), 1.0, tol=0.02)
    check("anchor.posY_faces_hood", round(d_hood, 2), 1.0, tol=0.02)
    R["anchor"] = {"negY_to_seatback_dot": round(d_back, 4),
                   "posY_to_hood_dot": round(d_hood, 4)}

    # == 1. SEATED via seat_at ==============================================
    r1 = PL.seat_at(drv, anchor, reference='bottom', align=True,
                    seat_mesh=jeep["cushion"])
    z = zmin(drv)
    p_cush = r1["post_contact"]
    p_back = PL.pair_contact(drv, jeep["seatback"])
    p_hood = PL.pair_contact(drv, jeep["hood"])
    cush_ok = (p_cush["state"] == "TOUCHING" or
               (p_cush["state"] == "CLEAR" and
                (p_cush["clearance_mm"] or 99) <= 1.0))
    if not cush_ok:
        FAILS.append(f"seat.cushion_state: {p_cush['state']} "
                     f"clear={p_cush['clearance_mm']}")
    if p_back["state"] == "PENETRATING":
        FAILS.append(f"seat.seatback: {p_back['state']} "
                     f"pen={p_back['penetration_mm']}")
    print(f"[T3] seat: z_min={z:.5f} (expect 0.77) "
          f"cushion={p_cush['state']}({p_cush['clearance_mm']}mm) "
          f"seatback={p_back['state']}({p_back['clearance_mm']}mm) "
          f"hood={p_hood['state']}({p_hood['clearance_mm']}mm) "
          f"seat_ms={r1['timings_ms']}")
    check("seat.z_min", round(z, 4), 0.77, tol=0.002)
    check("seat.ok", r1.get("ok"), True)
    R["seat"] = {"z_min": round(z, 5), "cushion": p_cush, "seatback": p_back,
                 "hood": p_hood, "report": {k: v for k, v in r1.items()
                                            if k != "post_contact"}}

    # == 2. STAND on chassis floor via place_on =============================
    # face -X, over open floor (clear of cushion y-band and hood), start
    # sunk 10cm low so the one-shot solver must lift to contact
    drv.rotation_euler = (0, 0, math.pi / 2)
    bpy.context.view_layer.update()
    move_center_to(drv, 0.20, -0.45)
    drv.location.z += 0.55 - zmin(drv)
    bpy.context.view_layer.update()
    PL.clear_bvh_cache()
    r2 = PL.place_on(drv, jeep["chassis"], clearance=0.0, footprint='bottom')
    z2 = zmin(drv)
    print(f"[T3] stand: z_min={z2:.5f} (expect 0.65) "
          f"state={r2['post_contact'][0]['state']} "
          f"multi_level={r2['multi_level']} "
          f"heights={r2['support_height_field']} timings={r2['timings_ms']}ms")
    check("stand.z_min", round(z2, 4), 0.65, tol=0.002)
    check("stand.state", r2["post_contact"][0]["state"], "TOUCHING")
    check("stand.ok", r2["ok"], True)
    check("stand.multi_level", r2["multi_level"], False)
    R["stand"] = r2

    # == 3. SABOTAGE: torso into SeatBack ===================================
    r3s = PL.seat_at(drv, anchor, reference='bottom', align=True)
    drv.location.x -= 0.3   # local -Y (seated backward) == world -X here
    bpy.context.view_layer.update()
    PL.clear_bvh_cache()
    a3 = PL.audit_scene()
    pair = next((p for p in a3["pairs"]
                 if {p["a"], p["b"]} == {"Driver", "SeatBack"}), None)
    print(f"[T3] sabotage: pairs={a3['pairs_checked']} "
          f"counts={a3['state_counts']} failed={a3['failed']} "
          f"Driver/SeatBack={pair['state'] if pair else 'MISSING'} "
          f"pen={pair['penetration_mm'] if pair else None}mm")
    check("sab.pair_found", pair is not None, True)
    if pair:
        check("sab.state", pair["state"], "PENETRATING")
        check("sab.pen_reported", pair["penetration_mm"] is not None, True)
    check("sab.failed", a3["failed"], True)
    R["sabotage"] = {"audit_failed": a3["failed"],
                     "state_counts": a3["state_counts"],
                     "driver_seatback": pair}

    # seam views on the sabotaged pair
    seam = PL.seam_views(drv, jeep["seatback"], out_dir=SEAM_DIR)
    sizes = {}
    for nm, path in seam["views"].items():
        sz = os.path.getsize(path) if os.path.exists(path) else 0
        sizes[nm] = sz
        if sz <= 5000:
            FAILS.append(f"seam.{nm}: size {sz} <= 5000 bytes")
    print(f"[T3] seam views: {json.dumps(seam['views'])} sizes={sizes}")
    print(f"[T3] seam cameras: {json.dumps(seam['cameras'])}")
    check("seam.n_views", len(seam["views"]), 4)
    R["seam"] = {"views": seam["views"], "sizes": sizes,
                 "cameras": seam["cameras"],
                 "contact_state": seam["contact_state"]}

    # == 4. HEAT bake + vertex render =======================================
    drv.location.x += 0.3   # restore the good seated pose
    bpy.context.view_layer.update()
    PL.clear_bvh_cache()
    spec = PL.heat_bake(drv, [jeep["cushion"], jeep["seatback"],
                              jeep["hood"]],
                        yellow_mm=15.0, green_mm=80.0)
    wb_setup('VERTEX', light='FLAT')
    cam_h = make_cam("HeatCam", (1.4, -1.4, 1.5), (-0.35, 0, 1.05), lens=50)
    bpy.context.scene.camera = cam_h
    bpy.context.scene.render.filepath = HEAT_PNG
    bpy.ops.render.render(write_still=True)
    hsz = os.path.getsize(HEAT_PNG) if os.path.exists(HEAT_PNG) else 0
    print(f"[T3] heat: {spec} png={HEAT_PNG} bytes={hsz}")
    if hsz <= 5000:
        FAILS.append(f"heat.png: size {hsz} <= 5000 bytes")
    R["heat"] = {"bands": spec, "png": HEAT_PNG, "bytes": hsz}

    # == 6. viewport-check render (MATERIAL, 3/4 view of full scene) ========
    wb_setup('MATERIAL', light='STUDIO')
    cam_s = make_cam("SceneCam", (4.6, -4.0, 2.6), (0, 0, 0.7), lens=50)
    bpy.context.scene.camera = cam_s
    bpy.context.scene.render.filepath = SCENE_PNG
    bpy.ops.render.render(write_still=True)
    ssz = os.path.getsize(SCENE_PNG) if os.path.exists(SCENE_PNG) else 0
    print(f"[T3] scene render: {SCENE_PNG} bytes={ssz}")
    R["scene_render"] = {"png": SCENE_PNG, "bytes": ssz,
                         "camera": {"loc": [4.6, -4.0, 2.6],
                                    "target": [0, 0, 0.7], "lens": 50}}

    verdict = "FAIL:\n" + "\n".join(FAILS) if FAILS else "ALL PASS"
    with open(OUT, "w") as f:
        json.dump({"fail": FAILS, "results": R}, f, indent=2, default=str)
    print(f"[T3] {verdict}")


if __name__ == "__main__":
    main()
