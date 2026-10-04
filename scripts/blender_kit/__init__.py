"""
blender_kit — shared helpers for headless Blender scene scripts.

Scene scripts import from this module instead of duplicating boilerplate.
A minimal scene script looks like:

    import bpy
    from blender_kit import common_parser, clear_scene, configure_render, render

    def build_scene():
        clear_scene()
        bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0.5))
        # ...
        return {"objects": ["Cube"]}

    def animate(ctx, *, start_frame=1, n_frames=24):
        # ... keyframes ...
        pass

    def main():
        p = common_parser()
        args = p.parse_args()
        ctx = build_scene()
        animate(ctx, start_frame=args.start, n_frames=args.frames)
        configure_render(args)
        render(args, scene_name="my_scene")

    if __name__ == "__main__":
        main()

All functions are safe to call from `blender --background --python script.py`.
"""
from __future__ import annotations

import argparse
import datetime
import json
import math
import os
import sys
import time
from typing import Any

import bpy


# ---------------------------------------------------------------------------
# Version compat shim (Blender 4.5 LTS ↔ 5.2 LTS)
# ---------------------------------------------------------------------------
# Lets agent-written scene scripts run on both 4.5 LTS and 5.2 LTS unchanged.
# Agents keep emitting 4.x idioms (BLENDER_EEVEE_NEXT, action.fcurves,
# mat.use_nodes = True) because that's what their training data shows.
# This shim translates those idioms at the kit boundary, so AGENTS.md
# never has to teach the 5.x API and agents never have to learn it.

BLENDER_VERSION_MAJOR = bpy.app.version[0]   # 4 or 5
_BLENDER_5 = BLENDER_VERSION_MAJOR >= 5


def is_blender_5() -> bool:
    """True if running on Blender 5.x (5.0+)."""
    return _BLENDER_5


def is_blender_4() -> bool:
    """True if running on Blender 4.x."""
    return BLENDER_VERSION_MAJOR == 4


# Single source of truth for the EEVEE engine id on THIS Blender build.
# 4.2-4.5 used 'BLENDER_EEVEE_NEXT'; 5.0+ reverted to 'BLENDER_EEVEE'.
EEVEE_ENGINE_ID = 'BLENDER_EEVEE_NEXT' if not _BLENDER_5 else 'BLENDER_EEVEE'

# Spellings an LLM is likely to emit, including the common missing-one-E typo.
_EEVEE_KEYS = frozenset({
    'eevee', 'eeveenext',
    'blendereevee', 'blendereeveenext',
    'blendereeenext',                # missing-one-E typo (BLENDER_EEE_NEXT)
})


def normalize_engine_id(name):
    """Map any EEVEE/Cycles/Workbench spelling to the id valid on this Blender.

    Accepts: 'BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE', 'eevee', 'EEVEE_NEXT',
             'eevee_next', 'BLENDER_EEE_NEXT' (typo), 'cycles', 'workbench'.
    Returns the engine id that works on the running Blender version.
    """
    if name is None:
        return EEVEE_ENGINE_ID
    key = str(name).lower().replace('_', '').replace('-', '').replace(' ', '')
    if key in _EEVEE_KEYS or 'eevee' in key or ('eee' in key and 'next' in key):
        return EEVEE_ENGINE_ID
    if 'cycles' in key:
        return 'CYCLES'
    if 'workbench' in key:
        return 'BLENDER_WORKBENCH'
    return name                     # unknown → pass through; bpy will raise


def normalize_engine(name):
    """Short engine name for viewport_capture.render_angle dispatch.

    render_angle branches on 'workbench' | 'eevee' | 'cycles' (short
    names), while agents/docs/upper layers speak raw Blender enums
    ('BLENDER_EEVEE_NEXT', 'CYCLES', ...). R3 usability F1: the CLI used
    to reject the documented enum spellings outright. This normalizer
    bridges BOTH spellings to the short dispatch name, reusing
    normalize_engine_id (so typos are tolerated too). Unknown input is
    returned unchanged — render_angle raises its clear RuntimeError.
    """
    if name is None:
        return "workbench"
    eid = normalize_engine_id(name)
    if eid == EEVEE_ENGINE_ID:
        return "eevee"
    return {"CYCLES": "cycles",
            "BLENDER_WORKBENCH": "workbench"}.get(eid, eid)


def _scaffold_5x_action(action):
    """session-24 law: a FRESH 5.x action has no slots/layers/strips/
    channelbag — action.fcurves-equivalent reads return a plain [] with
    no .new(). Creation chain (live-probed on 5.2.2):
        slots.new('OBJECT', name) -> layers.new() ->
        strips.new(type='KEYFRAME') -> channelbags.new(slot)
    NOTE: channelbag(slot) is a NULL-returning GETTER, not a creator —
    creation must go through strip.channelbags.new(slot)."""
    if not getattr(action, 'slots', None):
        slot = action.slots.new('OBJECT', action.name or 'Slot')
    else:
        slot = action.slots[0]
    if not action.layers:
        layer = action.layers.new(name="KitLayer")
    else:
        layer = action.layers[0]
    if not layer.strips:
        strip = layer.strips.new(type='KEYFRAME')   # name kwarg NOT accepted
    else:
        strip = layer.strips[0]
    # find the channelbag for this slot (getter returns None if absent)
    bag = strip.channelbag(slot)
    if bag is None:
        bag = strip.channelbags.new(slot)
    return bag


def iter_fcurves(action):
    """Return the action's fcurves collection (iterable; supports .new/.find).

    4.x: action.fcurves
    5.x: auto-scaffolds slots/layer/strip/channelbag on fresh actions
         (session-24: the empty-list .new() trap killed the first 5.2
         export), then returns the channelbag's fcurves.
    """
    if _BLENDER_5:
        if not getattr(action, 'slots', None):
            bag = _scaffold_5x_action(action)
            if bag is None:
                return []
            return bag.fcurves
        slot = action.slots[0]
        try:
            # The actual 5.x API: layers[0].strips[0].channelbag(slot).fcurves
            fc = action.layers[0].strips[0].channelbag(slot).fcurves
            if fc is None:
                bag = _scaffold_5x_action(action)
                return bag.fcurves if bag else []
            return fc
        except (IndexError, AttributeError):
            bag = _scaffold_5x_action(action)
            return bag.fcurves if bag else []
    return action.fcurves


def iter_all_fcurves(action):
    """Chain EVERY slot's channelbag fcurves (read-only iteration).

    session-26 (the v6 KD lean hunt): 5.2 slotted actions can serve
    MULTIPLE datablocks -- a mesh's Key datablock shares the OBJECT's
    auto-named action ('Zed.0001Action') with its own SLOT, so the
    shape-key fcurves (key_blocks[...].value) live in the SECOND
    slot's channelbag. iter_fcurves returns slot[0]'s collection
    (callers need .new()/.find() on a REAL collection) and is blind
    to the rest; READ-ONLY consumers (finders, audits, merges by
    fcurve reference) must use this chain instead.

    4.x: the flat action.fcurves (single implicit slot).
    """
    import itertools
    if not _BLENDER_5:
        return action.fcurves
    if not getattr(action, 'slots', None):
        return iter_fcurves(action)
    out = []
    for slot in action.slots:
        try:
            bag = action.layers[0].strips[0].channelbag(slot)
        except (IndexError, AttributeError, RuntimeError):
            continue
        if bag is not None and bag.fcurves is not None:
            out.append(bag.fcurves)
    return itertools.chain.from_iterable(out)


def action_groups(action):
    """Same shape as iter_fcurves but for action.groups (also moved in 5.x)."""
    if _BLENDER_5:
        if not getattr(action, 'slots', None):
            bag = _scaffold_5x_action(action)
            if bag is None:
                return []
            return bag.groups
        slot = action.slots[0]
        try:
            return action.layers[0].strips[0].channelbag(slot).groups
        except (IndexError, AttributeError):
            bag = _scaffold_5x_action(action)
            return bag.groups if bag else []
    return action.groups


def fcurves_new(action, data_path, index=0, group=None):
    """Version-safe fcurve creation (session-24 spin found THREE traps):
      1. 4.x kwarg is action_group=, 5.x renamed it group_name=
      2. BOTH versions REJECT None for the group kwarg — it must be
         OMITTED entirely when there is no group
      3. 5.x fresh actions need slot/layer/strip/channelbag scaffolding
         before .new() exists at all (iter_fcurves handles that here).
    """
    fcs = iter_fcurves(action)
    if _BLENDER_5:
        if group is None:
            return fcs.new(data_path, index=index)
        return fcs.new(data_path, index=index, group_name=group)
    if group is None:
        return fcs.new(data_path, index=index)
    return fcs.new(data_path, index=index, action_group=group)


def ensure_use_nodes(mat_or_world) -> None:
    """Set use_nodes=True on 4.x; no-op on 5.x (auto-created, deprecated)."""
    if not _BLENDER_5:
        mat_or_world.use_nodes = True


def supports_headless_gpu() -> bool:
    """True if this Blender can boot a GPU context WITHOUT a display.

    5.2+ has gpu.init() which can boot the EGL backend in --background —
    but ONLY on machines with a real render node. In no-/dev/dri
    containers (llvmpipe), gpu.init boots EGL then crashes with
    EGL_BAD_PARAMETER → segfault (validated session 16, both raw
    GPUOffScreen and EEVEE). Gate on the device, not on API presence.
    """
    if not _BLENDER_5:
        return False
    import os
    if not os.path.isdir('/dev/dri'):
        return False                 # llvmpipe container: Xvfb stays required
    try:
        import gpu
        return hasattr(gpu, 'init')
    except ImportError:
        return False


# ---------------------------------------------------------------------------
# CLI parsing
# ---------------------------------------------------------------------------

def script_argv() -> list[str]:
    """Args after `--` on the `blender --background --python` CLI."""
    argv = sys.argv
    return argv[argv.index("--") + 1:] if "--" in argv else []


def _import_scene_file(py_path: str):
    """Import a scene module from an explicit file path (QA #1)."""
    import importlib.util
    mod_name = os.path.splitext(os.path.basename(py_path))[0]
    if mod_name in sys.modules:
        existing = getattr(sys.modules[mod_name], "__file__", None)
        if existing and os.path.abspath(existing) == os.path.abspath(py_path):
            return sys.modules[mod_name]
    spec = importlib.util.spec_from_file_location(mod_name, py_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


def _available_scene_files() -> list[str]:
    """Scene files present in CWD + examples/ + scripts/ (bounded hint)."""
    names: list[str] = []
    for d in (".", "examples", "scripts"):
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if f.endswith(".py") and f != "__init__.py" \
                    and f.startswith(("scene_", "t", "edge_", "demo")):
                names.append(os.path.join(d, f))
    return names[:15]


def safe_import_scene(name: str):
    """Import a scene module by NAME or PATH, with friendly error on failure.

    Accepts (QA #1 — README quickstart examples now work out of the box):
      - a bare module name importable from PYTHONPATH (e.g. 'scene_v1_basic',
        't0_smoke');
      - the same bare name searched in ./examples/ and ./ when PYTHONPATH
        lookup fails (examples/ is NOT on blrun's PYTHONPATH by design);
      - an explicit path with or without the .py suffix (relative to CWD,
        e.g. 'examples/scene_v1_basic', '/abs/path/my_scene.py').

    Catches ModuleNotFoundError, SyntaxError, and ImportError — prints a
    clean message + lists available scene files when the name can't be
    resolved. A ModuleNotFoundError for an import INSIDE the scene file is
    still reported as-is (the fallback only fires when the missing module
    is the requested name itself).
    """
    import importlib
    # 1) Explicit path form (separator or .py suffix).
    if "/" in name or "\\" in name or name.endswith(".py"):
        py = name[:-3] + ".py" if name.endswith(".py") else name + ".py"
        if os.path.isfile(py):
            return _import_scene_file(py)
        print(f"[blender_kit] ERROR: scene file not found: {py}",
              file=sys.stderr)
        print(f"[blender_kit]        scene files present: "
              f"{_available_scene_files() or '(none found)'}", file=sys.stderr)
        sys.exit(1)
    # 2) Bare module name via PYTHONPATH.
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError as e:
        # Distinguish "the scene module itself is missing" (try the
        # ./examples + ./ fallback) from "an import inside the scene
        # failed" (report honestly — path re-exec would hide the bug).
        if f"No module named '{name}'" in str(e):
            for d in ("examples", "."):
                py = os.path.join(d, name + ".py")
                if os.path.isfile(py):
                    return _import_scene_file(py)
        print(f"[blender_kit] ERROR: scene module '{name}' not found: {e}",
              file=sys.stderr)
        print(f"[blender_kit]        searched PYTHONPATH + ./examples/ + ./;"
              f" scene files present: "
              f"{_available_scene_files() or '(none found)'}", file=sys.stderr)
        sys.exit(1)
    except SyntaxError as e:
        print(f"[blender_kit] ERROR: scene module '{name}' has a syntax error: {e}",
              file=sys.stderr)
        sys.exit(1)
    except ImportError as e:
        print(f"[blender_kit] ERROR: scene module '{name}' failed to import: {e}",
              file=sys.stderr)
        sys.exit(1)


def validate_output(path: str) -> None:
    """Validate that an output path is non-empty and writable. Fail fast."""
    if not path:
        print("[blender_kit] ERROR: output path is required (got empty string)",
              file=sys.stderr)
        sys.exit(1)
    try:
        d = os.path.dirname(os.path.abspath(path))
        os.makedirs(d, exist_ok=True)
    except (PermissionError, OSError) as e:
        print(f"[blender_kit] ERROR: cannot create output dir '{d}': {e}",
              file=sys.stderr)
        sys.exit(1)


def validate_resolution(w: int, h: int, *, max_dim: int = 8192) -> None:
    """Validate render resolution. Reject < 4x4 and > max_dim (OOM guard)."""
    if w < 4 or h < 4:
        print(f"[blender_kit] ERROR: resolution {w}x{h} is too small (min 4x4)",
              file=sys.stderr)
        sys.exit(1)
    if w > max_dim or h > max_dim:
        print(f"[blender_kit] ERROR: resolution {w}x{h} exceeds {max_dim} max "
              f"(OOM risk on 4GB containers)", file=sys.stderr)
        sys.exit(1)


def parse_vec3(s: str, name: str = "target") -> tuple:
    """Parse a 'X,Y,Z' string into a 3-tuple of floats, with clean error."""
    try:
        parts = [float(v) for v in s.split(",")]
    except ValueError:
        print(f"[blender_kit] ERROR: {name} '{s}' contains non-numeric values",
              file=sys.stderr)
        sys.exit(1)
    if len(parts) != 3:
        print(f"[blender_kit] ERROR: {name} '{s}' must have 3 comma-separated values, got {len(parts)}",
              file=sys.stderr)
        sys.exit(1)
    return tuple(parts)


def common_parser(*, require_output: bool = True) -> argparse.ArgumentParser:
    """Standard CLI for scene scripts.

    Adds: --output, --engine, --frames, --start, --samples, --w, --h,
          --still, --dry-run, --quality, --encode-mp4, --fps
    """
    p = argparse.ArgumentParser()
    p.add_argument("--output", required=require_output,
                   help="Output directory for rendered frames")
    p.add_argument("--engine", default="CYCLES",
                   type=normalize_engine_id,
                   help="Render engine (any spelling: cycles|CYCLES, "
                        "eevee|BLENDER_EEVEE|BLENDER_EEVEE_NEXT — both "
                        "EEVEE ids normalized per Blender version, "
                        "workbench|BLENDER_WORKBENCH; CYCLES=photorealistic "
                        "CPU, EEVEE=real-time PBR, WORKBENCH=fast previz)")
    p.add_argument("--frames", type=int, default=24,
                   help="Number of frames to render (default: 24)")
    p.add_argument("--start", type=int, default=1,
                   help="Start frame (default: 1)")
    p.add_argument("--samples", type=int, default=None,
                   help="Render samples (overrides --quality)")
    p.add_argument("--w", type=int, default=None,
                   help="Width in pixels (overrides --quality)")
    p.add_argument("--h", type=int, default=None,
                   help="Height in pixels (overrides --quality)")
    p.add_argument("--still", type=int, default=None,
                   help="Render only this single frame (skips animation render)")
    p.add_argument("--dry-run", action="store_true",
                   help="Print scene summary and exit without rendering")
    p.add_argument("--quality", choices=["previz", "viewport", "draft",
                                        "preview", "final"],
                   default="preview",
                   help="Quality preset (previz=480x270 workbench vision check, "
                        "viewport=960x540 workbench FLAT albedo (vid2vid "
                        "guidance -- THE previz deliverable standard), "
                        "draft=320x180/8s, preview=640x360/16s, "
                        "final=960x540/64s)")
    p.add_argument("--encode-mp4", action="store_true",
                   help="After rendering frames, encode to anim.mp4 via ffmpeg")
    p.add_argument("--aa", choices=["off", "fxaa"], default=None,
                   help="Workbench anti-aliasing override (viewport quality "
                        "defaults to OFF: AA is ~92% of render time; "
                        "fxaa = cheap smoothing for human-reviewed stills)")
    p.add_argument("--shade", choices=["studio", "flat"], default=None,
                   help="Workbench lighting mode for viewport quality "
                        "(default STUDIO: greyscale normal shading on the "
                        "white world = shape readability while saturated "
                        "subject colors stay saturated -- v3 shade "
                        "experiment, DESIGN_v3 §2; flat = pure albedo)")
    p.add_argument("--png", action="store_true",
                   help="Force PNG output (viewport quality defaults to "
                        "JPEG q85: ~15x smaller, faster encode)")
    p.add_argument("--fps", type=int, default=12,
                   help="FPS for MP4 encoding (default: 12)")
    p.add_argument("--scene-name", default="unnamed",
                   help="Scene name (used in metadata.json)")
    return p


def apply_quality(args: argparse.Namespace) -> None:
    """Fill in args.samples/w/h from --quality if not explicitly set.

    For 'previz' quality, also forces the engine to BLENDER_WORKBENCH
    (ultra-fast solid-shading render, ~0.2s/frame, no shadow/GI/AA).
    """
    QUALITY = {
        "previz":  {"samples": 1,  "w": 480, "h": 270, "engine": "BLENDER_WORKBENCH"},
        "viewport": {"samples": 1, "w": 960, "h": 540, "engine": "BLENDER_WORKBENCH"},
        "draft":   {"samples": 8,  "w": 320, "h": 180},
        "preview": {"samples": 16, "w": 640, "h": 360},
        "final":   {"samples": 64, "w": 960, "h": 540},
    }
    q = QUALITY[args.quality]
    if args.samples is None:
        args.samples = q["samples"]
    if args.w is None:
        args.w = q["w"]
    if args.h is None:
        args.h = q["h"]
    # previz/viewport quality forces workbench engine (overrides --engine)
    if args.quality in ("previz", "viewport") \
            and args.engine != "BLENDER_WORKBENCH":
        print(f"[blender_kit] note: --quality {args.quality} forces engine to "
              f"BLENDER_WORKBENCH (was {args.engine})")
        args.engine = "BLENDER_WORKBENCH"


# ---------------------------------------------------------------------------
# Scene construction
# ---------------------------------------------------------------------------

def clear_scene() -> None:
    """Reset to an empty factory scene."""
    bpy.ops.wm.read_factory_settings(use_empty=True)


def make_material(name: str, color: tuple[float, float, float],
                  roughness: float = 0.5, metallic: float = 0.0) -> bpy.types.Material:
    """Create a Principled BSDF material with the given base color.

    Uses Blender 4.x input names ('Base Color', 'Roughness', 'Metallic').
    On Blender 3.x you'd need to rename 'Subsurface' -> 'Subsurface Weight'
    etc. — this helper only sets the three inputs that are stable across 3.x/4.x.
    """
    mat = bpy.data.materials.new(name)
    ensure_use_nodes(mat)
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    assert bsdf is not None, f"material {name} has no Principled BSDF node"
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    # Workbench (MATERIAL color_type) reads the viewport DISPLAY color,
    # not the Principled Base Color -- without this, workbench renders
    # node materials as flat gray (session-8 gotcha).
    mat.diffuse_color = (*color, 1.0)
    return mat


def shade_smooth(obj: bpy.types.Object) -> None:
    """Set all polygons of a mesh object to smooth shading."""
    if obj.type != 'MESH':
        return
    for poly in obj.data.polygons:
        poly.use_smooth = True


def add_sky_world(*, sun_elevation_deg: float = 25.0,
                  sun_rotation_deg: float = 45.0,
                  strength: float = 1.0) -> None:
    """Replace the world background with a procedural sky texture.

    Uses NISHITA (4.x, physically accurate) or MULTIPLE_SCATTERING (5.x,
    NISHITA removed) — auto-detects.
    """
    import math
    world = bpy.data.worlds.new("World") if not bpy.data.worlds else bpy.data.worlds[0]
    bpy.context.scene.world = world
    ensure_use_nodes(world)
    nt = world.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    sky = nt.nodes.new("ShaderNodeTexSky")
    # NISHITA was the 4.x default (physically accurate); removed in 5.0.
    # Fall back to MULTIPLE_SCATTERING on 5.x.
    available = set(sky.bl_rna.properties['sky_type'].enum_items.keys())
    if 'NISHITA' in available:
        sky.sky_type = 'NISHITA'
    else:
        sky.sky_type = 'MULTIPLE_SCATTERING'
    sky.sun_elevation = math.radians(sun_elevation_deg)
    sky.sun_rotation = math.radians(sun_rotation_deg)
    if hasattr(sky, 'air_density'):
        sky.air_density = 1.0
    if hasattr(sky, 'dust_density'):
        sky.dust_density = 4.0
    bg.inputs["Strength"].default_value = strength
    nt.links.new(sky.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])


# ---------------------------------------------------------------------------
# Render configuration
# ---------------------------------------------------------------------------

def configure_render(args: argparse.Namespace,
                     *, filepath_pattern: str = "frame_####.png") -> None:
    """Configure the scene's render settings from CLI args."""
    apply_quality(args)
    scene = bpy.context.scene
    # Validate output dir before we start (fail fast, clean error)
    if not args.output:
        print("[blender_kit] ERROR: --output is required (got empty string)", file=sys.stderr)
        sys.exit(1)
    try:
        os.makedirs(args.output, exist_ok=True)
    except (PermissionError, OSError) as e:
        print(f"[blender_kit] ERROR: cannot create output dir '{args.output}': {e}",
              file=sys.stderr)
        sys.exit(1)
    # Validate resolution (Blender min useful is ~4x4; reject 0/1)
    if args.w < 4 or args.h < 4:
        print(f"[blender_kit] ERROR: resolution {args.w}x{args.h} is too small (min 4x4)",
              file=sys.stderr)
        sys.exit(1)
    # Normalize the engine id (accepts BLENDER_EEVEE_NEXT on 5.x, etc.)
    scene.render.engine = normalize_engine_id(args.engine)
    scene.render.resolution_x = args.w
    scene.render.resolution_y = args.h
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.film_transparent = False
    if args.quality == "viewport" and not _flag(args, "png"):
        # JPEG q85 for the guidance cut: ~23-35 ms/frame faster encode +
        # ~15x smaller files than PNG; edge quality is irrelevant for
        # vid2vid guidance (session-9 speed research). --png forces PNG.
        scene.render.image_settings.file_format = 'JPEG'
        scene.render.image_settings.quality = 85
        if filepath_pattern.endswith(".png"):
            filepath_pattern = filepath_pattern[:-4] + ".jpg"

    # Previz-correct color: 'Standard' shows authored base colors as-is.
    # Blender 4.5's default 'AgX' aggressively desaturates mid-chroma colors
    # (e.g. a muted zombie green reads as gray), which defeats color-coded
    # previz. Cinematic grading can re-enable AgX for final beauty passes.
    try:
        scene.view_settings.view_transform = 'Standard'
        scene.view_settings.look = 'None'
    except Exception as e:  # noqa: BLE001 - tolerate older view names
        print(f"[blender_kit] note: could not set Standard view transform: {e}")

    if args.engine == "CYCLES":
        scene.cycles.device = 'CPU'
        scene.cycles.samples = args.samples
        scene.cycles.use_denoising = True
    elif args.engine == "BLENDER_WORKBENCH":
        # Workbench: solid shading. MATERIAL color_type (not OBJECT) so
        # material colors are visible (session-5 worklog). NOTE: workbench
        # reads the material's VIEWPORT DISPLAY color (mat.diffuse_color),
        # not the Principled Base Color -- make_material sets both
        # (session-8 gotcha).
        scene.display.shading.color_type = 'MATERIAL'
        if args.quality == "viewport":
            # VIEWPORT quality = the vid2vid-guidance look. v3 (DESIGN_v3
            # §2, shade experiment): STUDIO lighting ON by default --
            # white surfaces shade into GREY by normal orientation
            # ("greyscale if you need shade", user directive) giving shape
            # readability, while saturated subject colors stay saturated
            # (measured: chromatic share identical flat vs studio, 25.9%).
            # FLAT remains available (--shade flat): pure albedo ladder,
            # zero shape cues -- the v2.2 look read as a wash (96.8%
            # single-class frames, luma stdev 0.05). Shadows OFF (extra
            # light-direction info vid2vid doesn't need), cavity OFF
            # (cavity lines read as toon outlines). render_aa=OFF: the
            # default '8' RE-RASTERIZES per sample = ~92% of wall time;
            # OFF is 5-6x faster. Jaggies are fine for guidance;
            # --aa fxaa restores cheap smoothing for stills.
            shade = _flag(args, "shade")
            scene.display.shading.light = 'FLAT' if shade == "flat" else 'STUDIO'
            scene.display.shading.show_shadows = False
            # v3.2 (DESIGN §9, measured): cavity ON at strong factors --
            # edge rims on every subject silhouette ("objects have
            # edges", user 8) at zero chroma cost (32.7% both ways) and
            # no measurable render-time cost. --no-cavity to disable.
            scene.display.shading.show_cavity = _flag(args, "cavity") != "off"
            scene.display.shading.cavity_type = 'BOTH'
            scene.display.shading.cavity_ridge_factor = 1.8
            scene.display.shading.cavity_valley_factor = 2.0
            aa = _flag(args, "aa")
            scene.display.render_aa = 'FXAA' if aa == 'fxaa' else 'OFF'
            w = bpy.data.worlds.new("FlatGuidance")
            w.use_nodes = False
            w.color = (0.50, 0.50, 0.52)
            scene.world = w
            # Hide atmosphere objects: volume-only materials (no surface
            # BSDF) render as OPAQUE SHELLS in workbench (volumes
            # unsupported) -- a fog box becomes a gray slab that blanks
            # whole shots when the camera is above/outside it (session-9:
            # S1 aerial + S10 crane were blank). Convention: ob["kit_atmo"]
            # = True (assets_street tags Street.Mist). Name-pattern
            # fallback catches untagged legacy scenes.
            import re as _re
            _atmo = _re.compile(r"mist|fog|haze|atmo", _re.IGNORECASE)
            n_hidden = 0
            for ob in scene.objects:
                if ob.get("kit_atmo") or _atmo.search(ob.name):
                    ob.hide_render = True
                    n_hidden += 1
            if n_hidden:
                print(f"[blender_kit] viewport preset: hid {n_hidden} "
                      f"atmosphere object(s) (workbench renders volumes as "
                      f"opaque shells)")
        else:
            # previz (op-check) look: studio light + shadows + cavity for
            # depth perception
            scene.display.shading.light = 'STUDIO'
            scene.display.shading.show_shadows = True
            scene.display.shading.show_cavity = True
    else:
        # EEVEE_NEXT — guard against attribute drift across versions
        scene.eevee.taa_render_samples = args.samples
        _safe_set(scene.eevee, "use_gtao", True)
        _safe_set(scene.eevee, "use_ssr", True)
        _safe_set(scene.eevee, "use_bloom", False)  # removed in EEVEE_NEXT 4.2+

    # Per session-5 worklog: Blender 4.5+ defaults to AgX view transform,
    # which crushes low-chroma colors (e.g. muted green zombies read as
    # gray). For color-coded previz, use Standard so authored colors read
    # true. Skip for Cycles final renders where AgX is desirable.
    if args.quality == "previz" or args.engine == "BLENDER_WORKBENCH":
        try:
            scene.view_settings.view_transform = 'Standard'
        except AttributeError:
            pass  # older Blender versions

    os.makedirs(args.output, exist_ok=True)
    scene.render.filepath = os.path.join(args.output, filepath_pattern)


def _flag(args: argparse.Namespace, name: str):
    """Optional extra flag parsed from --extra-style args (None-safe)."""
    return getattr(args, name, None)


def _safe_set(obj: Any, attr: str, val: Any) -> None:
    """Set obj.attr = val if it exists, else print a note and continue."""
    if hasattr(obj, attr):
        setattr(obj, attr, val)
    else:
        print(f"[blender_kit] note: {type(obj).__name__}.{attr} not available "
              f"in Blender {bpy.app.version_string}, skipping")


# ---------------------------------------------------------------------------
# Rendering & output validation
# ---------------------------------------------------------------------------

def render(args: argparse.Namespace, *, scene_name: str | None = None) -> None:
    """Render according to args (still / dry-run / animation), validate output,
    write metadata.json alongside frames, and optionally encode MP4.
    """
    scene = bpy.context.scene
    t0 = time.time()

    if args.dry_run:
        print("[blender_kit] dry-run -- scene summary:")
        print(f"  objects: {[o.name for o in scene.objects]}")
        print(f"  frame range: {scene.frame_start}..{scene.frame_end}")
        print(f"  engine: {scene.render.engine}")
        print(f"  resolution: {scene.render.resolution_x}x{scene.render.resolution_y}")
        return

    if args.still is not None:
        scene.frame_set(args.still)
        scene.render.filepath = os.path.join(
            args.output, f"still_{args.still:04d}.png")
        bpy.ops.render.render(write_still=True)
    else:
        bpy.ops.render.render(animation=True, write_still=False)

    elapsed = time.time() - t0
    _validate_outputs(args.output)
    _write_metadata(args, scene_name=scene_name or args.scene_name,
                    elapsed=elapsed, scene=scene)

    if args.encode_mp4 and args.still is None and not args.dry_run:
        _encode_mp4(args.output, fps=args.fps)


def _validate_outputs(outdir: str) -> None:
    """Raise RuntimeError if any output file is empty or missing."""
    files = [f for f in os.listdir(outdir)
             if os.path.isfile(os.path.join(outdir, f))
             and (f.endswith('.png') or f.endswith('.jpg'))]
    if not files:
        raise RuntimeError(
            f"[blender_kit] no PNG/JPEG outputs in {outdir} -- render "
            f"failed silently")
    empty = [f for f in files
             if os.path.getsize(os.path.join(outdir, f)) == 0]
    if empty:
        raise RuntimeError(
            f"[blender_kit] {len(empty)} empty render(s) in {outdir}: "
            f"{empty[:3]}... (EEVEE shader compile likely failed)")
    print(f"[blender_kit] wrote {len(files)} frame file(s) to {outdir}")


def _write_metadata(args: argparse.Namespace, *, scene_name: str,
                    elapsed: float, scene: bpy.types.Scene) -> None:
    """Write metadata.json alongside renders, plus scene.json (structured
    scene context for any consumer -- validator pairing, diffing, QA)."""
    import datetime
    meta = {
        "scene": scene_name,
        "blender_version": bpy.app.version_string,
        "engine": args.engine,
        "resolution": [args.w, args.h],
        "samples": args.samples,
        "frames": args.frames,
        "start": args.start,
        "still": args.still,
        "quality": args.quality,
        "rendered_at": datetime.datetime.now().isoformat(timespec='seconds'),
        "render_time_seconds": round(elapsed, 2),
        "objects": [
            {"name": o.name, "type": o.type,
             "location": [round(v, 3) for v in o.location],
             "rotation_euler_deg": [round(math.degrees(v), 3) for v in o.rotation_euler]}
            for o in scene.objects
        ],
        "camera": scene.camera.name if scene.camera else None,
        "camera_lens_mm": scene.camera.data.lens if scene.camera else None,
        "frame_range": [scene.frame_start, scene.frame_end],
    }
    with open(os.path.join(args.output, "metadata.json"), "w") as f:
        json.dump(meta, f, indent=2)
    print(f"[blender_kit] metadata.json written ({len(meta['objects'])} objects)")


def _encode_mp4(outdir: str, *, fps: int = 12) -> None:
    """Encode frame_####.png/.jpg sequence to anim.mp4 via ffmpeg."""
    import glob as _glob
    import subprocess
    mp4_path = os.path.join(outdir, "anim.mp4")
    ext = "png" if _glob.glob(os.path.join(outdir, "frame_*.png")) \
        else "jpg"
    cmd = ["ffmpeg", "-y", "-framerate", str(fps),
           "-i", os.path.join(outdir, f"frame_%04d.{ext}"),
           "-c:v", "libx264", "-pix_fmt", "yuv420p",
           "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
           mp4_path]
    print(f"[blender_kit] encoding MP4: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"[blender_kit] wrote {mp4_path} "
              f"({os.path.getsize(mp4_path)} bytes)")
    except subprocess.CalledProcessError as e:
        print(f"[blender_kit] ffmpeg failed: {e.stderr[-500:]}")
        raise


# ---------------------------------------------------------------------------
# glTF export
# ---------------------------------------------------------------------------

# Name-pattern fallback for untagged legacy atmosphere objects (the
# assets-side convention tags volume-only objects with ob["kit_atmo"]).
_ATMO_NAME_RE = None


def atmo_objects(scene):
    """Objects that CANNOT be represented in glTF and must be excluded.

    Law (session-9 + session-22): volume-only materials (Principled
    Volume, no surface BSDF) bake to OPAQUE SHELLS in glTF — a fog box
    becomes a gray slab that blanks whole shots when the camera is
    above/outside it (S1 aerial / S10 crane / S12a crane were blank in
    the web viewer). Detection (same triple-check as the viewport
    quality preset): kit_atmo custom-prop OR name pattern OR a linked
    volume output with no linked surface output.
    """
    global _ATMO_NAME_RE
    if _ATMO_NAME_RE is None:
        import re as _re
        _ATMO_NAME_RE = _re.compile(r"mist|fog|haze|atmo", _re.IGNORECASE)
    out = []
    for ob in scene.objects:
        if ob.type != 'MESH':
            continue
        if ob.get("kit_atmo") or _ATMO_NAME_RE.search(ob.name):
            out.append(ob)
            continue
        mat = ob.active_material
        if mat is None or not mat.use_nodes:
            continue
        nt = mat.node_tree
        out_node = nt.nodes.get("Material Output")
        if out_node is None:
            continue
        vol_linked = out_node.inputs["Volume"].is_linked
        surf_linked = out_node.inputs["Surface"].is_linked
        if vol_linked and not surf_linked:
            out.append(ob)
    return out


def render_hidden_objects(scene):
    """Objects the scene marks as NOT camera-visible (session-23 law).

    Blender ray-visibility flags (visible_camera / hide_render) are the
    scene's own declaration of 'this object never appears in a render'
    -- physics hulls, particle emitters, proxy planes. The glTF
    exporter IGNORES them (it exports data, not render state), so
    without an explicit exclusion every helper leaks into the review
    GLB and the web viewer shows colliders drifting next to the jeep
    (user: 'i don't know what is this but it SHOULD NOT be visible')
    and coplanar physics planes z-fight the visible street (user:
    'these are what's causing flickering!')."""
    return [ob for ob in scene.objects
            if ob.visible_camera is False or ob.hide_render is True]


def export_gltf(args: argparse.Namespace, *, out_path: str | None = None,
                exclude_objects: list | None = None) -> str:
    """Export the current scene as a .glb file with cameras, lights, and animation.

    exclude_objects: objects to leave OUT of the GLB (e.g. atmo_objects()
    — volume-only materials have no glTF representation; declare them in
    the consumer's JSON metadata instead). render-hidden objects
    (visible_camera=False / hide_render=True) are ALWAYS excluded on
    top (session-23 law — see render_hidden_objects). Exclusion is
    implemented via selection (use_selection=True) and the prior
    selection state is restored afterwards.

    Returns the path to the exported file. The file is suitable for direct
    loading in <model-viewer> or Three.js GLTFLoader.
    """
    out_path = out_path or os.path.join(args.output, f"{args.scene_name}.glb")
    if not out_path.endswith(".glb"):
        out_path = os.path.splitext(out_path)[0] + ".glb"

    # export_scene.gltf operator parameter names verified against Blender 4.x API
    # docs: https://docs.blender.org/api/current/bpy.ops.export_scene.html
    exclude = list(exclude_objects or [])
    exclude.extend(render_hidden_objects(bpy.context.scene))
    exclude = list({ob.name: ob for ob in exclude}.values())
    prev_selected = set()
    if exclude:
        # Deterministic exclusion: select everything except the excluded
        # set and export with use_selection=True. Prior selection restored.
        # bpy.data.objects covers every scene (background mode has one).
        for ob in bpy.data.objects:
            if ob.select_get():
                prev_selected.add(ob.name)
            ob.select_set(ob not in exclude)
    try:
        bpy.ops.export_scene.gltf(
            filepath=out_path,
            export_format='GLB',
            export_cameras=True,        # default False -- MUST set
            export_lights=True,         # default False -- MUST set
            export_animations=True,
            export_animation_mode='ACTIONS',
            export_frame_range=True,
            export_apply=True,          # bake modifiers
            export_yup=True,
            export_materials='EXPORT',
            export_import_convert_lighting_mode='SPEC',
            use_selection=bool(exclude),
        )
    finally:
        if exclude:
            for ob in bpy.data.objects:
                try:
                    ob.select_set(ob.name in prev_selected)
                except RuntimeError:
                    pass  # object may have been removed mid-export
    size = os.path.getsize(out_path)
    print(f"[blender_kit] exported glTF: {out_path} ({size} bytes, "
          f"{size/1024:.1f} KB)")
    return out_path


# ---------------------------------------------------------------------------
# USD export (with previz:entity carrier — issue #1)
# ---------------------------------------------------------------------------

def export_usd(args: argparse.Namespace | None = None, *,
               out_path: str | None = None,
               scene_module: str | None = None,
               export_animation: bool = False) -> str:
    """Export the current scene as a USD file with previz:entity customData
    + previz:identityColor custom attr on every wrapper prim.

    The PrevizUSDHook (scripts/previz_usd_hook.py) is registered before
    bpy.ops.wm.usd_export and unregistered in a finally block. The hook
    reads story-level constants from the scene module (SHOTS_V3, BOARD,
    _V3_SEG, etc.) and embeds them in the previz:entity customData on
    the /root prim; per-object data (blender_name, blender_type,
    anchor_to, body_type, pose_name, rig_mode, identity_color_rgba,
    kit_atmo, is_camera, camera_lens_mm, is_light, light_energy) is
    embedded on each /root/<obj.name> wrapper prim.

    Per issue #1: github.com/zmpc01/blender-agent-kit/issues/1
    Design: docs/DESIGN_previz_usd_carrier.md
    """
    # Lazy-import previz_usd_hook so non-USD kit users don't pay the
    # pxr import cost on every blender_kit import.
    import sys as _sys
    _scripts_dir = os.path.dirname(os.path.abspath(__file__))
    if _scripts_dir not in _sys.path:
        _sys.path.insert(0, _scripts_dir)
    import previz_usd_hook

    # Resolve out_path
    if out_path is None:
        if args is not None and hasattr(args, "output"):
            out_path = args.output
        else:
            raise ValueError("export_usd requires out_path or args.output")

    # Coerce extension
    if not out_path.lower().endswith((".usd", ".usda", ".usdc", ".usdz")):
        out_path = out_path + ".usda"

    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)

    # Resolve scene_module name (for story-data collection in the hook)
    if scene_module is None and args is not None:
        scene_module = getattr(args, "scene", None) or getattr(args, "scene_module", None)

    # Register the hook
    previz_usd_hook.register(scene_module_name=scene_module)

    try:
        # USD-REVIEW-1 F26 fix: kwargs verified against Blender 4.5.13
        # WM_OT_usd_export RNA (op.get_rna_type().properties).
        usd_kwargs = dict(
            filepath=out_path,
            export_animation=export_animation,
            export_meshes=True,
            export_lights=True,
            export_cameras=True,
            export_curves=True,
            export_points=True,
            export_volumes=False,
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
            # Older Blender versions may not have all kwargs; retry with minimum.
            print(f"[blender_kit] note: usd_export kwarg error ({e}); retrying")
            bpy.ops.wm.usd_export(
                filepath=out_path,
                export_animation=export_animation,
                export_cameras=True,
                export_lights=True,
            )
    finally:
        previz_usd_hook.unregister()

    size = os.path.getsize(out_path)
    print(f"[blender_kit] exported USD (with previz carrier): {out_path} "
          f"({size} bytes, {size/1024:.1f} KB)")
    return out_path


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def print_scene_summary(label: str = "scene") -> None:
    """Print a human-readable summary of the current scene."""
    scene = bpy.context.scene
    print(f"[blender_kit] {label} summary:")
    print(f"  objects ({len(scene.objects)}):")
    for o in scene.objects:
        loc = ", ".join(f"{v:.2f}" for v in o.location)
        print(f"    - {o.name:20s} type={o.type:8s} loc=({loc})")
    if scene.camera:
        print(f"  camera: {scene.camera.name} (lens={scene.camera.data.lens}mm)")
    print(f"  frame range: {scene.frame_start}..{scene.frame_end}")
    print(f"  engine: {scene.render.engine}")
