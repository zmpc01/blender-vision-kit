"""
scene_schema.py — export the current scene as a structured JSON schema.

The schema is the agent-facing scene representation: stable IDs, transforms,
materials, bounding boxes, camera, lights, animation. Agents can QUERY state
as data (instead of reading bpy code) and emit PATCHES to mutate it.

This is the "Layer 1 — Agent-facing scene schema" from the hybrid
architecture: agents reason over structured state, fall back to bpy only
when the schema can't express what they need.

Usage:
    # Dump the current scene (after build_scene + animate)
    blrun.sh --background --python scripts/scene_schema.py -- \\
        --scene scene_template --output output/scene.json

    # Dump with bounding boxes (slower; computes world-space bbox per mesh)
    blrun.sh --background --python scripts/scene_schema.py -- \\
        --scene scene_template --output output/scene.json --with-bounds

    # Dump a SAVED .blend (no build needed) — file mode or stdout mode:
    blrun.sh --background --python scripts/scene_schema.py -- \\
        --load-blend scene.blend --with-bounds --output output/schema.json
    blrun.sh --background --python scripts/scene_schema.py -- \\
        --load-blend scene.blend --with-bounds   # JSON on stdout; the
        # JSON is the LAST thing printed — capture with `> file`
"""
import argparse
import json
import math
import os
import sys

import bpy
from blender_kit import script_argv, clear_scene


def _matrix_to_list(m):
    """Convert a mathutils.Matrix to a 4x4 nested list."""
    return [list(m.row[i]) for i in range(4)]


def _object_bounds(obj):
    """Compute world-space bounding box corners of a mesh object."""
    if obj.type != 'MESH' or not obj.bound_box:
        return None
    corners = []
    for corner in obj.bound_box:
        world = obj.matrix_world @ type(obj.location)(corner)
        corners.append([round(world.x, 4), round(world.y, 4), round(world.z, 4)])
    return {
        "min": [round(min(c[i] for c in corners), 4) for i in range(3)],
        "max": [round(max(c[i] for c in corners), 4) for i in range(3)],
        "size": [round(max(c[i] for c in corners) - min(c[i] for c in corners), 4)
                 for i in range(3)],
    }


def _material_to_dict(mat):
    """Extract material info from a Principled BSDF material."""
    if not mat or not getattr(mat, 'use_nodes', True) or mat.node_tree is None:
        return {"name": mat.name if mat else None, "color": None,
                "roughness": None, "metallic": None}
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is None:
        return {"name": mat.name, "color": None,
                "roughness": None, "metallic": None}
    color = bsdf.inputs["Base Color"].default_value
    return {
        "name": mat.name,
        "color": [round(color[0], 3), round(color[1], 3),
                  round(color[2], 3), round(color[3], 3)],
        "roughness": round(bsdf.inputs["Roughness"].default_value, 3),
        "metallic": round(bsdf.inputs["Metallic"].default_value, 3),
    }


def _light_to_dict(obj):
    """Extract light-specific info."""
    light = obj.data
    return {
        "type": light.type,
        "energy": round(light.energy, 3),
        "color": [round(c, 3) for c in light.color],
        "size": round(light.size, 3) if hasattr(light, "size") else None,
    }


def _camera_to_dict(obj):
    """Extract camera-specific info."""
    cam = obj.data
    return {
        "lens_mm": round(cam.lens, 2),
        "sensor_width_mm": round(cam.sensor_width, 2),
        "clip_start": round(cam.clip_start, 4),
        "clip_end": round(cam.clip_end, 4),
    }


def _animation_to_dict(obj):
    """Extract animation (keyframes) for an object."""
    if not obj.animation_data or not obj.animation_data.action:
        return None
    action = obj.animation_data.action
    curves = []
    from blender_kit import iter_fcurves
    for fc in iter_fcurves(action):
        keyframes = []
        for kp in fc.keyframe_points:
            keyframes.append({
                "frame": round(kp.co.x, 3),
                "value": round(kp.co.y, 4),
                "interpolation": kp.interpolation,
                "easing": kp.easing if hasattr(kp, "easing") else None,
            })
        curves.append({
            "data_path": fc.data_path,
            "array_index": fc.array_index,
            "keyframes": keyframes,
        })
    return {"action_name": action.name, "curves": curves}


def export_scene_schema(*, with_bounds: bool = False) -> dict:
    """Build a JSON-serializable dict describing the current scene."""
    scene = bpy.context.scene
    schema = {
        "schema_version": "1.0",
        "blender_version": bpy.app.version_string,
        "scene_name": scene.name,
        "frame_range": [scene.frame_start, scene.frame_end],
        "fps": scene.render.fps,
        "engine": scene.render.engine,
        "resolution": [scene.render.resolution_x, scene.render.resolution_y],
        "world": None,
        "objects": [],
        "active_camera": scene.camera.name if scene.camera else None,
    }

    # World
    if scene.world and scene.world.node_tree is not None:
        bg = scene.world.node_tree.nodes.get("Background")
        if bg:
            schema["world"] = {
                "background_color": [round(v, 3) for v in bg.inputs["Color"].default_value],
                "background_strength": round(bg.inputs["Strength"].default_value, 3),
            }

    # Objects
    for obj in scene.objects:
        # world_centroid (round-2/U5): `location` is the ORIGIN's position,
        # which on origin-baked meshes is far from the geometry — agents
        # emitted set_location targets from `location` and teleported the
        # mesh. world_centroid is the vertex-mean in world space: use it
        # (or bounds) as the geometry's actual position.
        world_centroid = None
        if obj.type == 'MESH' and len(obj.data.vertices):
            mw = obj.matrix_world
            vs = obj.data.vertices
            step = max(1, len(vs) // 500)
            cx = cy = cz = 0.0
            m = 0
            for i in range(0, len(vs), step):
                w = mw @ vs[i].co
                cx += w.x; cy += w.y; cz += w.z; m += 1
            world_centroid = [round(cx / m, 4), round(cy / m, 4),
                              round(cz / m, 4)]
        entry = {
            "id": obj.name,  # stable ID — agents reference objects by name
            "type": obj.type,
            "location": [round(v, 4) for v in obj.location],
            "world_centroid": world_centroid,
            "rotation_euler_deg": [round(math.degrees(v), 4)
                                   for v in obj.rotation_euler],
            "scale": [round(v, 4) for v in obj.scale],
            "matrix_world": _matrix_to_list(obj.matrix_world),
            "parent": obj.parent.name if obj.parent else None,
            "visible": obj.visible_get(),
            "materials": [_material_to_dict(m) for m in obj.data.materials]
                         if obj.type == 'MESH' and hasattr(obj.data, "materials")
                         else [],
        }

        if obj.type == 'MESH':
            entry["mesh"] = {
                "vertex_count": len(obj.data.vertices),
                "polygon_count": len(obj.data.polygons),
            }
            if with_bounds:
                entry["bounds"] = _object_bounds(obj)
        elif obj.type == 'LIGHT':
            entry["light"] = _light_to_dict(obj)
        elif obj.type == 'CAMERA':
            entry["camera"] = _camera_to_dict(obj)

        # Animation
        anim = _animation_to_dict(obj)
        if anim:
            entry["animation"] = anim

        schema["objects"].append(entry)

    return schema


def main():
    p = argparse.ArgumentParser(
        description="Export the current scene as a structured JSON schema.")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--scene",
                       help="Scene module name (e.g. scene_template)")
    group.add_argument("--load-blend",
                       help="Load this .blend file and export its state "
                            "(parity with apply_patch/validate_scene CLIs; "
                            "usability round-1/U3)")
    p.add_argument("--output", default=None,
                   help="Output JSON path")
    p.add_argument("--with-bounds", action="store_true",
                   help="Include world-space bounding boxes for mesh objects (slower)")
    p.add_argument("--frames", type=int, default=24,
                   help="Animation frame range (passed to scene's animate())")
    args = p.parse_args(script_argv())

    if args.load_blend:
        print(f"[scene_schema] loading blend: {args.load_blend}")
        bpy.ops.wm.open_mainfile(filepath=args.load_blend)
    else:
        print(f"[scene_schema] importing scene: {args.scene}")
        import importlib
        from blender_kit import safe_import_scene
        mod = safe_import_scene(args.scene)
        clear_scene()
        ctx = mod.build_scene()
        if hasattr(mod, "animate"):
            mod.animate(ctx, start_frame=1, n_frames=args.frames)

    print(f"[scene_schema] exporting schema (with_bounds={args.with_bounds})...")
    schema = export_scene_schema(with_bounds=args.with_bounds)
    n_objs = len(schema["objects"])
    n_anims = sum(1 for o in schema["objects"] if "animation" in o)

    if args.output is None:
        # stdout mode (usability round-D F-02): print the schema JSON
        # LAST — anything after it corrupts a `> file` capture (round-E
        # subject B hit exactly that)
        print(json.dumps(schema, indent=2, default=str))
        return
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(schema, f, indent=2)
    print(f"[scene_schema] wrote {args.output}  "
          f"({os.path.getsize(args.output)} bytes, {n_objs} objects, {n_anims} animated)")


if __name__ == "__main__":
    main()
