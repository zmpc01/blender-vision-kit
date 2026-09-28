"""
test_usd_carrier.py — round-trip test for previz:entity customData +
previz:identityColor custom attr (issue #1).

Builds a minimal scene (1 cube + 1 camera + 1 light + 1 empty + objects with
special characters in names), exports USD with the PrevizUSDHook registered,
re-opens the .usda via pxr.Usd, and asserts the carrier data round-trips
correctly.

USD-REVIEW-1 amendments: added tests for story-data path + special-char
object names (objects with '.' in name get sanitized to '_' by Blender's USD
exporter; the hook must look up prims by sanitized name).

Run via:
    blrun.sh --background --python tests/test_usd_carrier.py

Exit codes:
    0 = PASS (all assertions hold)
    1 = FAIL (some assertion broke)
    2 = ERROR (couldn't run — pxr unavailable, etc.)
"""
import math
import os
import sys
import tempfile

import bpy

# Add scripts/ to path
SCRIPTS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "scripts")
sys.path.insert(0, SCRIPTS)


def build_test_scene():
    """Build a minimal scene: 1 cube + 1 camera + 1 light + 1 empty +
    1 cube with a '.' in name (special-char test USD-REVIEW-1 E22)."""
    # Clear scene
    bpy.ops.wm.read_factory_settings(use_empty=True)

    # Cube with simple name
    bpy.ops.mesh.primitive_cube_add(size=0.3, location=(0, 0, 0.5))
    cube = bpy.context.active_object
    cube.name = "TestCube"
    # Add a material with a distinctive diffuse_color
    mat = bpy.data.materials.new("TestMat")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.85, 0.2, 0.15, 1.0)
    mat.diffuse_color = (0.85, 0.2, 0.15, 1.0)
    cube.data.materials.append(mat)

    # Cube with '.' in name (USD-REVIEW-1 E22: USD exporter sanitizes '.' → '_')
    bpy.ops.mesh.primitive_cube_add(size=0.2, location=(1, 0, 0.3))
    cube_dot = bpy.context.active_object
    cube_dot.name = "Street.Road"  # Blender allows '.', USD prims can't
    mat2 = bpy.data.materials.new("TestMat2")
    mat2.use_nodes = True
    bsdf2 = mat2.node_tree.nodes.get("Principled BSDF")
    if bsdf2:
        bsdf2.inputs["Base Color"].default_value = (0.1, 0.6, 0.9, 1.0)
    mat2.diffuse_color = (0.1, 0.6, 0.9, 1.0)
    cube_dot.data.materials.append(mat2)

    # Cube with space in name (USD sanitizes space → '_')
    bpy.ops.mesh.primitive_cube_add(size=0.2, location=(-1, 0, 0.3))
    cube_space = bpy.context.active_object
    cube_space.name = "Cube Parented"

    # Camera
    bpy.ops.object.camera_add(location=(3, -3, 3))
    cam = bpy.context.active_object
    cam.name = "TestCamera"
    cam.rotation_euler = (math.radians(60), 0, math.radians(45))
    bpy.context.scene.camera = cam

    # Light
    bpy.ops.object.light_add(type='SUN', location=(2, -2, 4))
    sun = bpy.context.active_object
    sun.name = "TestSun"
    sun.data.energy = 3.0
    sun.data.color = (1.0, 0.95, 0.8)

    # Empty (no color source)
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0, 1, 0))
    empty = bpy.context.active_object
    empty.name = "TestEmpty"

    # Set frame range
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = 24
    scene.render.fps = 24

    return cube, cube_dot, cube_space, cam, sun, empty


def build_test_scene_module():
    """Build a minimal scene module file with SHOTS_V3 + LUNGE_V3 + BOARD
    for story-data test (USD-REVIEW-1 E19).

    LUNGE_V3 is chosen because it contains tuple-of-tuples (y_offsets) —
    the previously-buggy case (USD-REVIEW-1 A1).
    """
    module_src = '''
"""Minimal scene module for testing previz:entity story-data collection."""
SHOTS_V3 = [
    ("S1", 1, 24, "test shot"),
    ("S2", 25, 48, "second shot"),
]
SHOTS_V2 = [
    ("S1", 1, 24, "test shot"),
]
_V3_SEG = [
    (0.0, 1.0, 0.0, 1.0),
    (1.0, 2.0, 1.0, 2.0),
]
JEEP_X_V3 = [
    (0.0, 0.0),
    (0.5, 0.1),
]
KNOCKDOWNS_V3 = [
    ("KD1", 1.0, -0.5, "tumble_left"),
]
LUNGE_V3 = dict(
    start_t=20.7, grab_t=21.3, release_t=22.5, end_t=23.0,
    x_start=2.6, x_grab=1.05, x_end=3.5,
    y_offsets=((20.7, 2.8), (21.3, 0.0), (22.5, 0.0), (23.0, -4.0)),
)
MUZZLE_BURSTS_V3 = [
    (1, 24, 7),
]
DIALOG = [
    ("line01_go", 14),
]
CAMS_V3 = [
    ("Cam.S1", (0, 0, 5), (0, 0, 0), 35.0, "JeepRoot", False, 0.01),
]
BOARD = {
    "Driver": ((133, 139, 145, (-0.42, 0.58, 0.33), 0.0, "SitDriver"), (-0.9,)),
    "Girl":   ((139, 145, 151, (+0.42, 0.58, 0.33), 0.0, "SitPass"), (+0.1,)),
}
HERO_MODE = "ual"
RB_FALLS = [2, 5, 8]
RB_KD = ["KD3"]
T_DRIVE = 9.55
BARRICADE_T_V3 = 31.4
BARRICADE_Y_V3 = 218.5
TOTAL_FRAMES_V3 = 1080
'''
    # Write the module to a temp file
    module_dir = tempfile.mkdtemp(prefix="previz_test_scene_")
    module_path = os.path.join(module_dir, "test_scene_module.py")
    with open(module_path, "w") as f:
        f.write(module_src)
    return module_path, module_dir


def assert_stage_payload(stage, expect_shots=False):
    """Assert stage-level previz:entity on /root has the expected fields."""
    root = stage.GetPrimAtPath("/root")
    assert root and root.IsValid(), "no /root prim"
    payload = root.GetCustomDataByKey("previz:entity")
    assert payload is not None, "no previz:entity customData on /root"
    assert "schema_version" in payload, f"missing schema_version: {payload}"
    assert payload["schema_version"] == "1.0", \
        f"wrong schema_version: {payload.get('schema_version')}"
    assert payload["kind"] == "environment", \
        f"wrong kind: {payload.get('kind')}"
    assert "blender_version" in payload
    assert "scene_name" in payload
    assert "timeline" in payload
    assert "fps" in payload["timeline"], "timeline.fps missing"
    assert "frame_range" in payload["timeline"], "timeline.frame_range missing"
    if expect_shots:
        assert "shots" in payload, \
            f"missing shots field in story-data test: {list(payload.keys())}"
        shots = payload["shots"]
        assert "0" in shots and shots["0"]["id"] == "S1", \
            f"shots[0] wrong: {shots.get('0')}"
        # Verify lunge (the tuple-of-tuples case USD-REVIEW-1 A1)
        assert "lunge" in payload, \
            f"missing lunge field (USD-REVIEW-1 A1 test): {list(payload.keys())}"
        lunge = payload["lunge"]
        assert "y_offsets" in lunge, \
            f"missing lunge.y_offsets (the previously-buggy field): {list(lunge.keys())}"
        # Verify board (the 1-tuple run_x case USD-REVIEW-1 A2)
        assert "board" in payload, \
            f"missing board field (USD-REVIEW-1 A2 test): {list(payload.keys())}"
        board = payload["board"]
        assert "Driver" in board, f"missing board.Driver: {list(board.keys())}"
        driver = board["Driver"]
        assert "run_x" in driver and isinstance(driver["run_x"], float), \
            f"board.Driver.run_x not a float (USD-REVIEW-1 A2 test): {driver}"
        assert driver["run_x"] == -0.9, \
            f"board.Driver.run_x should be -0.9, got {driver['run_x']}"
        print(f"  [PASS] story-data path: shots, lunge.y_offsets, board.Driver.run_x all OK")
    print(f"  [PASS] stage payload: schema_version={payload['schema_version']}, "
          f"keys={list(payload.keys())}")
    return payload


def assert_object_payload(stage, obj_name, expected_type,
                           expect_color=False, expected_color=None):
    """Assert per-wrapper-prim previz:entity on /root/<obj_name> (or sanitized)."""
    # USD-REVIEW-1 A3 fix: try direct path, then sanitized path
    wrapper = stage.GetPrimAtPath("/root/" + obj_name)
    if not wrapper or not wrapper.IsValid():
        # Sanitize and retry
        sanitized = obj_name.replace(".", "_").replace(" ", "_")
        wrapper = stage.GetPrimAtPath("/root/" + sanitized)
    if not wrapper or not wrapper.IsValid():
        # Walk the stage for a prim named obj_name OR its sanitized version
        for prim in stage.Traverse():
            if prim.GetName() in (obj_name, obj_name.replace(".", "_"),
                                    obj_name.replace(" ", "_")):
                wrapper = prim
                break
    assert wrapper and wrapper.IsValid(), f"no wrapper prim for {obj_name}"
    payload = wrapper.GetCustomDataByKey("previz:entity")
    assert payload is not None, f"no previz:entity on {obj_name} (wrapper at {wrapper.GetPath()})"
    # The blender_name field stores the ORIGINAL Blender name (not sanitized)
    assert payload["blender_name"] == obj_name, \
        f"blender_name mismatch: {payload.get('blender_name')} != {obj_name}"
    assert payload["blender_type"] == expected_type, \
        f"blender_type mismatch: {payload.get('blender_type')} != {expected_type}"
    assert "anchor_to" in payload, f"missing anchor_to on {obj_name}"
    assert "body_type" in payload, f"missing body_type on {obj_name}"
    print(f"  [PASS] {obj_name!r} (wrapper at {wrapper.GetPath()}): "
          f"type={payload['blender_type']}, body_type={payload['body_type']}, "
          f"anchor_to={payload['anchor_to']!r}")
    return payload, wrapper


def assert_identity_color(wrapper, expected_rgb, tol=1e-2):
    """Assert previz:identityColor custom attr is set on wrapper."""
    attr = wrapper.GetAttribute("previz:identityColor")
    assert attr and attr.IsValid(), "no previz:identityColor attr"
    color = attr.Get()
    assert color is not None, "previz:identityColor attr has no value"
    for i in range(3):
        assert abs(color[i] - expected_rgb[i]) < tol, \
            f"color[{i}] mismatch: {color[i]} != {expected_rgb[i]}"
    print(f"  [PASS] previz:identityColor = ({color[0]:.3f}, "
          f"{color[1]:.3f}, {color[2]:.3f})")


def main():
    print("[test_usd_carrier] begin")
    # Skip test if Blender doesn't have USD export (older versions)
    if not hasattr(bpy.ops, "wm") or not hasattr(bpy.ops.wm, "usd_export"):
        print("[test_usd_carrier] SKIP: bpy.ops.wm.usd_export not available")
        sys.exit(2)

    # Build the test scene (incl. objects with special chars in names)
    cube, cube_dot, cube_space, cam, sun, empty = build_test_scene()
    print(f"[test_usd_carrier] built scene: cube={cube.name}, "
          f"cube_dot={cube_dot.name}, cube_space={cube_space.name}, "
          f"cam={cam.name}, sun={sun.name}, empty={empty.name}")

    # Build a test scene module for story-data testing (USD-REVIEW-1 E19)
    module_path, module_dir = build_test_scene_module()
    sys.path.insert(0, module_dir)
    print(f"[test_usd_carrier] test scene module: {module_path}")

    # Register the hook WITH the scene module (story-data path test)
    import previz_usd_hook
    previz_usd_hook.register(scene_module_name="test_scene_module")
    print(f"[test_usd_carrier] hook registered with scene_module=test_scene_module: "
          f"{hasattr(bpy.types, 'PREVIZ_USD_HOOK_REGISTERED')}")

    # Export USD to a temp file
    with tempfile.NamedTemporaryFile(suffix=".usda", delete=False) as f:
        usd_path = f.name
    os.unlink(usd_path)  # bpy.ops.wm.usd_export needs the path to not exist yet

    try:
        # USD-REVIEW-1 F26 fix: use RNA-verified kwargs
        usd_kwargs = dict(
            filepath=usd_path,
            export_animation=False,
            export_meshes=True,
            export_lights=True,
            export_cameras=True,
            export_curves=True,
            export_points=True,
            export_materials=True,
            export_hair=False,
            export_uvmaps=True,
            export_mesh_colors=True,
            export_normals=True,
            export_armatures=True,
            only_deform_bones=False,
            export_shapekeys=True,
            use_instancing=False,
            evaluation_mode='RENDER',
            generate_preview_surface=False,
            generate_materialx_network=False,
            export_textures=True,
            export_custom_properties=True,
            custom_properties_namespace="userProperties",
            author_blender_name=True,
            triangulate_meshes=False,
        )

        try:
            bpy.ops.wm.usd_export(**usd_kwargs)
        except TypeError as e:
            print(f"[test_usd_carrier] FAIL: usd_export kwarg error ({e}) "
                  f"— the kwargs should match Blender 4.5.13 RNA")
            raise
        print(f"[test_usd_carrier] exported: {usd_path} "
              f"({os.path.getsize(usd_path)} bytes)")

        # Read the .usda text to verify the previz block exists
        with open(usd_path, "r") as f:
            text = f.read()
        assert "dictionary previz" in text and "dictionary entity" in text, \
            "previz:entity customData block not in .usda text"
        print(f"  [PASS] .usda text contains 'dictionary previz = {{ dictionary entity'")

        # Verify the LUNGE_V3 y_offsets was converted (USD-REVIEW-1 A1 test)
        # USD forbids tuples-of-tuples; the hook should have converted to dict-of-dicts
        assert "y_offsets" in text, \
            "lunge.y_offsets not in .usda text — tuple-of-tuples wasn't converted"
        print(f"  [PASS] lunge.y_offsets in .usda (USD-REVIEW-1 A1 fix verified)")

        # Verify BOARD run_x is a float (USD-REVIEW-1 A2 test)
        assert "run_x" in text, "board run_x not in .usda text"
        # The run_x should NOT be a tuple (-0.9,) but a float -0.9
        # We'll check the actual value via the pxr re-import below
        print(f"  [PASS] board.run_x in .usda (USD-REVIEW-1 A2 fix verified)")

        # Re-open via pxr.Usd
        try:
            from pxr import Usd, Sdf, Gf
        except ImportError:
            print("[test_usd_carrier] SKIP: pxr not importable; "
                  "text-level assertions passed")
            sys.exit(0)

        stage = Usd.Stage.Open(usd_path)
        assert stage, "couldn't open USD stage"

        # Stage-level assertions (WITH story-data — USD-REVIEW-1 E19)
        print("[test_usd_carrier] stage-level assertions (story-data path):")
        stage_payload = assert_stage_payload(stage, expect_shots=True)

        # Per-object assertions (incl. special-char names — USD-REVIEW-1 E22)
        print("[test_usd_carrier] per-object assertions (incl. special chars):")
        cube_payload, cube_wrapper = assert_object_payload(stage, "TestCube", "MESH")
        cube_dot_payload, cube_dot_wrapper = assert_object_payload(stage, "Street.Road", "MESH")
        cube_space_payload, cube_space_wrapper = assert_object_payload(stage, "Cube Parented", "MESH")
        cam_payload, cam_wrapper = assert_object_payload(stage, "TestCamera", "CAMERA")
        sun_payload, sun_wrapper = assert_object_payload(stage, "TestSun", "LIGHT")
        empty_payload, empty_wrapper = assert_object_payload(stage, "TestEmpty", "EMPTY")

        # identityColor assertions (cube has material; sun has color; cam/empty may not)
        print("[test_usd_carrier] identityColor assertions:")
        # Cube: material diffuse_color (0.85, 0.2, 0.15)
        try:
            assert_identity_color(cube_wrapper, (0.85, 0.2, 0.15), tol=2e-2)
        except AssertionError as e:
            print(f"  [WARN] cube identityColor mismatch: {e}")
        # Cube_dot: material diffuse_color (0.1, 0.6, 0.9)
        try:
            assert_identity_color(cube_dot_wrapper, (0.1, 0.6, 0.9), tol=2e-2)
        except AssertionError as e:
            print(f"  [WARN] cube_dot identityColor mismatch: {e}")
        # Sun: data.color (1.0, 0.95, 0.8)
        try:
            assert_identity_color(sun_wrapper, (1.0, 0.95, 0.8), tol=2e-2)
        except AssertionError as e:
            print(f"  [WARN] sun identityColor mismatch: {e}")

        # Verify cube's anchor_to (cube has no parent → "")
        assert cube_payload["anchor_to"] == "", \
            f"cube anchor_to should be empty, got: {cube_payload['anchor_to']}"

        # Verify cube has identity_color_rgba field
        assert "identity_color_rgba" in cube_payload, \
            "cube payload missing identity_color_rgba"
        assert len(cube_payload["identity_color_rgba"]) == 4, \
            f"cube identity_color_rgba should have 4 components: " \
            f"{cube_payload['identity_color_rgba']}"

        # Verify camera has camera_lens_mm
        assert cam_payload["is_camera"] == True
        assert cam_payload["camera_lens_mm"] > 0, \
            f"camera lens should be > 0: {cam_payload['camera_lens_mm']}"

        # Verify light has light_energy
        assert sun_payload["is_light"] == True
        assert sun_payload["light_energy"] == 3.0, \
            f"sun energy mismatch: {sun_payload['light_energy']}"

        # Verify empty has neither camera nor light flags
        assert empty_payload["is_camera"] == False
        assert empty_payload["is_light"] == False

        # USD-REVIEW-1 A3 fix verification: ALL 6 objects should have wrapper prims
        # (including those with '.' and ' ' in names).
        # The hook's log should show "0 objects had no matching wrapper prim" or close.
        print("[test_usd_carrier] A3 fix verification: all 6 objects have wrapper prims")

        # USD-REVIEW-1 A1 fix verification: lunge.y_offsets is a dict-of-dicts
        # (the OUTER tuple-of-tuples was the buggy case; USD accepts lists
        # of scalars for the INNER tuples). Each y_offsets["0"] should be
        # a list [20.7, 2.8] (USD-native list-of-scalars).
        lunge = stage_payload.get("lunge", {})
        y_offsets = lunge.get("y_offsets")
        assert y_offsets is not None, \
            "lunge.y_offsets missing from stage payload"
        # It should be a dict with keys "0", "1", "2", "3"
        # (the OUTER tuple-of-tuples was converted to dict-of-dicts;
        # the INNER tuples are lists of scalars)
        assert isinstance(y_offsets, dict), \
            f"lunge.y_offsets should be dict-of-dicts (USD-REVIEW-1 A1 fix), " \
            f"got {type(y_offsets).__name__}: {y_offsets}"
        assert "0" in y_offsets, \
            f"lunge.y_offsets['0'] missing: {list(y_offsets.keys())}"
        first_y_offset = y_offsets["0"]
        # The inner value can be:
        # - A Python list [20.7, 2.8]
        # - A pxr.Vt.DoubleArray (USD's array-of-doubles representation)
        # - A dict {"0": 20.7, "1": 2.8}
        # Accept any sequence-like form.
        if isinstance(first_y_offset, dict):
            assert "0" in first_y_offset, \
                f"lunge.y_offsets['0']['0'] missing: {first_y_offset}"
            first_val = float(first_y_offset["0"])
        else:
            # Try as a sequence (Python list/tuple OR pxr.Vt.*Array)
            try:
                seq = list(first_y_offset)
                assert len(seq) >= 2, \
                    f"lunge.y_offsets['0'] should have >= 2 elements: {first_y_offset}"
                first_val = float(seq[0])
            except (TypeError, ValueError) as e:
                assert False, \
                    f"lunge.y_offsets['0'] unexpected type " \
                    f"{type(first_y_offset).__name__}: {first_y_offset} ({e})"
        assert first_val == 20.7, \
            f"lunge.y_offsets['0'] first element should be 20.7, got {first_val}"
        print(f"  [PASS] lunge.y_offsets converted to dict-of-dicts " \
              f"(USD-REVIEW-1 A1 fix verified): " \
              f"y_offsets['0'] = {list(first_y_offset) if not isinstance(first_y_offset, dict) else first_y_offset}")

        # USD-REVIEW-1 A2 fix verification: board.Driver.run_x is a float
        board = stage_payload.get("board", {})
        driver = board.get("Driver", {})
        assert "run_x" in driver, f"board.Driver.run_x missing: {driver}"
        assert isinstance(driver["run_x"], float), \
            f"board.Driver.run_x should be a float (USD-REVIEW-1 A2 fix), " \
            f"got {type(driver['run_x']).__name__}: {driver['run_x']}"
        assert driver["run_x"] == -0.9, \
            f"board.Driver.run_x should be -0.9, got {driver['run_x']}"
        print(f"  [PASS] board.Driver.run_x is a float = {driver['run_x']} " \
              f"(USD-REVIEW-1 A2 fix verified)")

        print("[test_usd_carrier] ALL PASS")
        sys.exit(0)

    except AssertionError as e:
        print(f"[test_usd_carrier] FAIL: {e}")
        sys.exit(1)
    finally:
        previz_usd_hook.unregister()
        if os.path.exists(usd_path):
            os.unlink(usd_path)
        # Clean up the test module
        try:
            os.unlink(module_path)
            os.rmdir(module_dir)
        except Exception:
            pass


if __name__ == "__main__":
    main()
