#!/usr/bin/env python3
"""
tuning_matrix.py — P1(color)/P2(shade-light) perception measurement harness.

NOT a kit tool: this is the committed measurement rig behind the doctrine
in docs/TUNING_perception_v1.md. It renders ONE diagnostic scene under a
matrix of shading configurations (workbench light/color_type/shadow/cavity
x view transforms x EEVEE), writes each to output/tuning/<cfg>.png, and
makes color + mono (grayscale) variants of every config.

The scene is designed with known ground truth (sizes/colors/positions) so
each render can be scored for: object identification, low-contrast edge
legibility, floater pop, small-object visibility.

Run:  bash scripts/blrun.sh --background --python scripts/tuning_matrix.py
"""
import bpy, os, sys, math

OUT = "/home/z/bvk/output/tuning"
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------------------
# 1. Diagnostic scene (deterministic, known ground truth)
# ---------------------------------------------------------------------------
def build_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scn = bpy.context.scene

    def mat(name, rgb, rough=0.8):
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        bsdf = m.node_tree.nodes["Principled BSDF"]
        bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
        bsdf.inputs["Roughness"].default_value = rough
        # kit law 6 parity: workbench MATERIAL color_type reads the Viewport
        # Display diffuse_color, NOT node Base Color. Set BOTH.
        m.diffuse_color = (*rgb, 1.0)
        return m

    def box(name, size, loc, m):
        bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
        o = bpy.context.active_object
        o.name = name
        o.scale = (size[0] / 2, size[1] / 2, size[2] / 2)
        bpy.ops.object.transform_apply(scale=True)
        o.data.materials.append(m)
        return o

    def sphere(name, r, loc, m):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc)
        o = bpy.context.active_object
        o.name = name
        bpy.ops.object.shade_smooth()
        o.data.materials.append(m)
        return o

    def cyl(name, r, depth, loc, m):
        bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth, location=loc)
        o = bpy.context.active_object
        o.name = name
        bpy.ops.object.shade_smooth()
        o.data.materials.append(m)
        return o

    # ground: mid-gray, big
    box("ground", (14, 14, 0.1), (0, 0, -0.05), mat("m_ground", (0.35, 0.35, 0.35)))
    # saturated color-coded objects (P1: does color earn its keep?)
    box("red_cube", (0.8, 0.8, 0.8), (-2.2, 0, 0.4), mat("m_red", (0.75, 0.05, 0.05)))
    sphere("green_sphere", 0.5, (2.2, 0.6, 0.5), mat("m_green", (0.05, 0.55, 0.08)))
    cyl("blue_cyl", 0.35, 1.0, (0.4, -2.2, 0.5), mat("m_blue", (0.08, 0.15, 0.7)))
    # low-contrast geometry (P2: luminance edge readability)
    box("gray_box", (1.0, 1.0, 0.6), (-0.6, 1.6, 0.3), mat("m_gray", (0.42, 0.42, 0.42)))
    box("white_box", (0.7, 0.7, 0.45), (-1.2, -1.6, 0.225), mat("m_white", (0.85, 0.85, 0.85)))
    # floater: 0.25m above ground — should VISUALLY POP (or not)
    box("floater", (0.6, 0.6, 0.6), (1.5, -1.2, 0.55), mat("m_orange", (0.9, 0.45, 0.05)))
    # small object at 640x480
    sphere("small_ball", 0.07, (0.9, 1.0, 0.07), mat("m_purple", (0.45, 0.1, 0.6)))

    # one sun for SCENE-light + eevee configs
    bpy.ops.object.light_add(type='SUN', location=(4, -4, 6))
    sun = bpy.context.active_object
    sun.data.energy = 5.0
    sun.rotation_euler = (math.radians(50), 0, math.radians(30))

    return scn


# ---------------------------------------------------------------------------
# 2. Render matrix
# ---------------------------------------------------------------------------
def render(scn, name, engine="workbench", light=None, color_type=None,
           shadows=None, cavity=None, transform="Standard", samples=8):
    if engine == "workbench":
        scn.render.engine = 'BLENDER_WORKBENCH'
        shd = scn.display.shading
        shd.light = light or 'STUDIO'
        shd.color_type = color_type or 'MATERIAL'
        shd.show_shadows = shadows if shadows is not None else False
        shd.show_cavity = cavity if cavity is not None else False
        # mirror contact-shadow behavior of kit default when shadows off
        shd.shadow_intensity = 0.5
    elif engine == "eevee":
        import blender_kit
        scn.render.engine = blender_kit.EEVEE_ENGINE_ID
        scn.eevee.taa_render_samples = samples
    else:
        raise ValueError(engine)

    try:
        scn.view_settings.view_transform = transform
    except Exception:
        print(f"[matrix] transform {transform} unavailable, keeping default")

    scn.render.resolution_x = 640
    scn.render.resolution_y = 480
    scn.render.resolution_percentage = 100
    scn.render.image_settings.file_format = 'PNG'
    scn.render.image_settings.color_mode = 'RGB'
    scn.render.filepath = f"{OUT}/{name}.png"
    bpy.ops.render.render(write_still=True)
    print(f"[matrix] wrote {name}.png")


def camera(scn, loc, target=(0, 0, 0.3), lens=50):
    bpy.ops.object.camera_add(location=loc)
    cam = bpy.context.active_object
    direction = (target[0] - loc[0], target[1] - loc[1], target[2] - loc[2])
    import mathutils
    rot_quat = mathutils.Vector(direction).to_track_quat('-Z', 'Y')
    cam.rotation_euler = rot_quat.to_euler()
    cam.data.lens = lens
    scn.camera = cam
    return cam


# ---------------------------------------------------------------------------
# 3. Mono variants (grayscale via PIL — same luminance model my eye uses)
# ---------------------------------------------------------------------------
def mono_variants():
    from PIL import Image
    for f in sorted(os.listdir(OUT)):
        if not f.endswith(".png") or f.endswith("_mono.png"):
            continue
        img = Image.open(os.path.join(OUT, f)).convert("L")
        out = os.path.join(OUT, f.replace(".png", "_mono.png"))
        img.convert("RGB").save(out)
    print("[matrix] mono variants done")


def main():
    scn = build_scene()
    camera(scn, (7.5, -6.5, 4.2))

    # ---- workbench matrix (P2) ----
    render(scn, "wb_flat_mat",      light='FLAT',   color_type='MATERIAL')
    render(scn, "wb_studio_mat",    light='STUDIO', color_type='MATERIAL')
    render(scn, "wb_studio_mat_cav", light='STUDIO', color_type='MATERIAL', cavity=True)
    render(scn, "wb_studio_mat_sh", light='STUDIO', color_type='MATERIAL', shadows=True, cavity=True)  # kit default
    render(scn, "wb_flat_single",   light='FLAT',   color_type='SINGLE', cavity=True)
    render(scn, "wb_studio_object", light='STUDIO', color_type='OBJECT', shadows=True)
    render(scn, "wb_matcap_mat",    light='MATCAP', color_type='MATERIAL', shadows=True)
    # ---- view transform on the kit default config ----
    render(scn, "wb_studio_mat_sh_agx", light='STUDIO', color_type='MATERIAL', shadows=True, cavity=True, transform='AgX')
    # ---- eevee (appearance truth arm) ----
    render(scn, "eevee_std", engine="eevee", transform='Standard')
    render(scn, "eevee_agx", engine="eevee", transform='AgX')

    mono_variants()
    print("[matrix] DONE — output/tuning/")


main()
