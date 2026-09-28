"""
previz_usd_hook.py — Blender USDHook that publishes previz:entity customData
+ previz:identityColor custom attr on every wrapper prim during USD export.

This is the carrier that makes Blender→WebPreviz lossless: the converter on
the webpreviz repo reads previz:entity verbatim and rebuilds scene.json.

Per issue #1 on github.com/zmpc01/blender-agent-kit:
  When the kit exports USD, embed the scene.json entity data as
  previz:entity customData on each wrapper prim. Additionally: publish
  Shot/Platform/Environment/Timeline data via previz:entity carrier, and
  previz:identityColor as a custom attr.

Design: docs/DESIGN_previz_usd_carrier.md
Research: docs/USD-RESEARCH-1_report.md
Review: USD-REVIEW-1 (fixed showstoppers A1/A2/A3 + F26)

Usage (standalone):
    blrun.sh --background --python scripts/previz_usd_hook.py -- \\
        --help      # show register/unregister self-test

Usage (from export_usd.py):
    import previz_usd_hook
    previz_usd_hook.register(scene_module_name="scene_escape_v4")
    try:
        bpy.ops.wm.usd_export(filepath=out_path, export_animation=False, ...)
    finally:
        previz_usd_hook.unregister()

The hook fires AFTER the native USD exporter authors all prims, BEFORE stage
save. It walks bpy.context.scene.objects, looks up each wrapper prim by name
(stage.GetPrimAtPath("/root/" + obj.name)), and writes:

  1. Stage-level previz:entity on /root (schema_version, kind, shots,
     timeline, environment, platforms, animation_presets, dialog,
     flatness_policy, blender_version, scene_name).
  2. Per-wrapper-prim previz:entity on /root/<obj.name> (blender_name,
     blender_type, anchor_to, body_type, pose_name, rig_mode,
     identity_color_rgba, kit_atmo, is_camera, camera_lens_mm, is_light,
     light_energy).
  3. Per-wrapper-prim previz:identityColor custom attr (Color3f).
"""
from __future__ import annotations

import importlib
import os
import re
import sys
import traceback
from typing import Any

import bpy

# Blender's USDHook base class — available in Blender 3.x+.
USDHook = getattr(bpy.types, "USDHook", None)
if USDHook is None:  # pragma: no cover — Blender <3.x
    print("[previz_usd_hook] WARNING: bpy.types.USDHook not available; "
          "hook will be a no-op on this Blender version")


# USD prim names must match [A-Za-z_][A-Za-z0-9_]*. Blender's USD exporter
# sanitizes any char outside this set to '_'. Verified via live probe
# (USD-REVIEW-1 A3) — 583 of 606 scene_escape_v4 objects have '.' in their
# names; the USD prim is named with '_' replacing '.'.
#
# USD-REVIEW-2 C.new2 polish: iterate UTF-8 BYTES (not codepoints) so
# multi-byte Unicode chars like 'é' get sanitized to multiple '_' (matching
# Blender's byte-level behavior). ASCII-only scenes are unaffected.
_USD_NAME_BAD_CHARS_BYTES = re.compile(rb"[^A-Za-z0-9_]")


def _sanitize_usd_name(name: str) -> str:
    """Match Blender's USD exporter name sanitization.

    Replaces any char outside [A-Za-z0-9_] with '_'. So 'T.Fill' → 'T_Fill',
    'Cube Parented' → 'Cube_Parented', 'CUBE-v2' → 'CUBE_v2', 'Café' →
    'Caf__' (the 2-byte 'é' becomes 2 underscores, matching Blender).

    USD-REVIEW-2 C.new2: operates on UTF-8 bytes to match Blender's
    actual byte-level sanitization for multi-byte Unicode chars.
    """
    if not isinstance(name, str):
        name = str(name)
    return _USD_NAME_BAD_CHARS_BYTES.sub(b"_", name.encode("utf-8")).decode("utf-8")


def _build_prim_name_map(stage, root_path: str) -> dict:
    """Walk the stage ONCE, build a map from prim.name → prim.
    The hook uses this to look up wrapper prims by sanitized name.

    Returns dict[str, pxr.Usd.Prim]. For prims with duplicate names, the
    first one encountered (depth-first) wins.
    """
    name_map = {}
    try:
        for prim in stage.Traverse():
            name = prim.GetName()
            if name and name not in name_map:
                name_map[name] = prim
    except Exception as e:
        print(f"[previz_usd_hook] WARN: stage.Traverse failed: {e}")
    return name_map


# ---------------------------------------------------------------------------
# Story-data collection (Option C: hybrid — read from scene module if importable)
# ---------------------------------------------------------------------------

def _to_usd_safe(value, depth=0):
    """Recursively convert a Python value to a USD-customData-safe form.

    USD customData accepts:
    - scalars (int, float, str, bool)
    - dicts of safe values
    - LISTS OF SCALARS (int, float, str, bool — NOT dicts, NOT tuples)
    - None is FORBIDDEN (use empty string)

    USD customData REJECTS:
    - lists of dicts (use dict-of-dicts with stringified-int keys)
    - lists of tuples (use dict-of-dicts)
    - tuples (convert to lists of scalars or dict-of-dicts)
    - nested tuples-of-tuples (flatten or dict-of-dicts)

    This function recursively:
    - Converts tuples to lists
    - Converts list-of-non-scalars to dict-of-dicts with stringified-int keys
    - Converts None to ""
    - Passes scalars and dicts of safe values through

    USD-REVIEW-2 C.7 polish: depth limit (50) guards against theoretical
    infinite recursion on cyclic Python data (shouldn't happen with scene
    constants, but defensive).
    """
    if depth > 50:
        # Defensive: prevent infinite recursion on cyclic data.
        try:
            return str(value)
        except Exception:
            return ""
    if value is None:
        return ""  # USD rejects None
    if isinstance(value, bool):
        return value  # bool is a subclass of int; check first
    if isinstance(value, (int, float, str)):
        return value
    if isinstance(value, tuple):
        # Tuples are converted to lists for USD
        return _to_usd_safe(list(value), depth + 1)
    if isinstance(value, list):
        if not value:
            return []  # empty list is OK at any depth
        # Check element types
        all_scalars = all(isinstance(x, (int, float, str, bool, type(None)))
                         for x in value)
        if all_scalars:
            # Convert None elements to "" and return list
            return [_to_usd_safe(x, depth + 1) for x in value]
        # Otherwise: convert to dict-of-dicts with stringified-int keys
        return {str(i): _to_usd_safe(x, depth + 1) for i, x in enumerate(value)}
    if isinstance(value, dict):
        return {str(k): _to_usd_safe(v, depth + 1) for k, v in value.items()}
    # Unknown type — stringify
    try:
        return str(value)
    except Exception:
        return ""


def _list_to_dict_of_dicts(lst):
    """USD customData forbids list-of-dicts; emulate as dict-of-dicts with
    stringified-int keys. Lists of scalars (ints, strings, floats) are fine.
    Delegates to _to_usd_safe for robustness.
    """
    return _to_usd_safe(lst)


def _try_collect(mod, attr_name, transform=None):
    """Read attribute from module; return None if missing. Apply transform."""
    val = getattr(mod, attr_name, None)
    if val is None:
        return None
    if transform is not None:
        try:
            val = transform(val)
        except Exception as e:
            print(f"[previz_usd_hook] NOTE: transform on {attr_name} failed: {e}")
            return None
    return val


def _collect_shots(shots_v3):
    """SHOTS_V3 -> dict-of-dicts with shot info.
    Element shape: (id, f0, f1, description) — possibly longer."""
    out = {}
    for i, entry in enumerate(shots_v3):
        try:
            d = {
                "id": str(entry[0]) if len(entry) > 0 else "",
                "f0": int(entry[1]) if len(entry) > 1 else 0,
                "f1": int(entry[2]) if len(entry) > 2 else 0,
                "description": str(entry[3]) if len(entry) > 3 else "",
            }
            if len(entry) > 4:
                d["intent"] = str(entry[4])
            out[str(i)] = d
        except Exception as e:
            print(f"[previz_usd_hook] NOTE: SHOTS_V3[{i}] parse failed: {e}")
            continue
    return out


def _collect_speed_profile(seg):
    """_V3_SEG (list of (t0, t1, v0, v1)) -> dict-of-dicts."""
    out = {}
    for i, entry in enumerate(seg):
        try:
            out[str(i)] = {
                "t0": float(entry[0]),
                "t1": float(entry[1]),
                "v0": float(entry[2]),
                "v1": float(entry[3]),
            }
        except Exception as e:
            print(f"[previz_usd_hook] NOTE: _V3_SEG[{i}] parse failed: {e}")
            continue
    return out


def _collect_jeep_weave(jx):
    """JEEP_X_V3 (list of (t, x)) -> dict-of-dicts."""
    out = {}
    for i, entry in enumerate(jx):
        try:
            out[str(i)] = {"t": float(entry[0]), "x": float(entry[1])}
        except Exception as e:
            print(f"[previz_usd_hook] NOTE: JEEP_X_V3[{i}] parse failed: {e}")
            continue
    return out


def _collect_knockdowns(kd):
    """KNOCKDOWNS_V3 (list of (name, t_hit, x_off, style)) -> dict-of-dicts."""
    out = {}
    for i, entry in enumerate(kd):
        try:
            out[str(i)] = {
                "id": str(entry[0]),
                "t_hit": float(entry[1]),
                "x_off": float(entry[2]),
                "style": str(entry[3]),
            }
        except Exception as e:
            print(f"[previz_usd_hook] NOTE: KNOCKDOWNS_V3[{i}] parse failed: {e}")
            continue
    return out


def _collect_muzzle_bursts(mb):
    """MUZZLE_BURSTS_V3 (list of (f0, f1, every_N)) -> dict-of-dicts."""
    out = {}
    for i, entry in enumerate(mb):
        try:
            out[str(i)] = {
                "f0": int(entry[0]),
                "f1": int(entry[1]),
                "every_n": int(entry[2]),
            }
        except Exception as e:
            print(f"[previz_usd_hook] NOTE: MUZZLE_BURSTS_V3[{i}] parse failed: {e}")
            continue
    return out


def _collect_dialog(dialog):
    """DIALOG (list of (clip, onset_frame)) -> dict-of-dicts."""
    out = {}
    for i, entry in enumerate(dialog):
        try:
            out[str(i)] = {
                "clip": str(entry[0]),
                "onset_frame": int(entry[1]),
            }
        except Exception as e:
            print(f"[previz_usd_hook] NOTE: DIALOG[{i}] parse failed: {e}")
            continue
    return out


def _collect_cameras(cams):
    """CAMS_V3 (list of (name, loc0, loc1, lens_mm, aim, parent_jeep, shake_amp))
    -> dict-of-dicts. Defensive on tuple shape — handles 4-tuples to 7-tuples.
    """
    out = {}
    for i, entry in enumerate(cams):
        try:
            # Defensive: try various entry shapes
            d = {"name": str(entry[0])}
            if len(entry) > 1:
                d["loc0"] = [float(x) for x in entry[1]] if hasattr(entry[1], "__iter__") else float(entry[1])
            if len(entry) > 2:
                d["loc1"] = [float(x) for x in entry[2]] if hasattr(entry[2], "__iter__") else float(entry[2])
            if len(entry) > 3:
                d["lens_mm"] = float(entry[3])
            if len(entry) > 4:
                # Session-21 fidelity fix: keep aim as a float list when it
                # is one (was str(tuple) — lossy for the converter).
                try:
                    d["aim"] = [float(x) for x in entry[4]]
                except (TypeError, ValueError):
                    d["aim"] = entry[4] if isinstance(
                        entry[4], (str, bool, int, float)) else str(entry[4])
            if len(entry) > 5:
                d["parent_jeep"] = bool(entry[5])
            if len(entry) > 6:
                d["shake_amp"] = float(entry[6])
            out[str(i)] = d
        except Exception as e:
            print(f"[previz_usd_hook] NOTE: CAMS_V3[{i}] parse failed: {e}")
            continue
    return out


def _collect_board(board):
    """BOARD (dict actor -> ((f_run_end, f_apex, f_land, (x,y,z), yaw, pose), run_x))
    -> dict-of-dicts. Defensive on the run_x shape (can be a 1-tuple like
    (-0.9,) or a scalar like -0.9 per scene_escape_v4.py:198-203).
    """
    out = {}
    for actor, value in board.items():
        try:
            # Unpack: value is a 2-tuple (main_tuple, run_x_tuple_or_scalar)
            if isinstance(value, tuple) and len(value) >= 1:
                main_tuple = value[0]
                run_x = value[1] if len(value) > 1 else None
            else:
                main_tuple = value
                run_x = None

            # run_x might be a 1-tuple like (-0.9,) OR a scalar like -0.9
            if isinstance(run_x, (tuple, list)):
                if len(run_x) > 0:
                    run_x_val = float(run_x[0])
                else:
                    run_x_val = 0.0
            elif run_x is None:
                run_x_val = 0.0
            else:
                run_x_val = float(run_x)

            out[str(actor)] = {
                "f_run_end": int(main_tuple[0]),
                "f_apex": int(main_tuple[1]),
                "f_land": int(main_tuple[2]),
                "seat_local": [float(x) for x in main_tuple[3]],
                "yaw_end": float(main_tuple[4]),
                "pose_name": str(main_tuple[5]),
                "run_x": run_x_val,
            }
        except Exception as e:
            print(f"[previz_usd_hook] NOTE: BOARD[{actor}] parse failed: {e}")
            continue
    return out


def _collect_lunge(lunge):
    """LUNGE_V3 (dict) -> recursively USD-safe form.

    The LUNGE_V3 dict can contain nested tuples (e.g., y_offsets is a
    tuple-of-tuples like ((20.7, 2.8), (21.3, 0.0), ...)). USD customData
    REJECTS tuples-of-tuples. We recursively convert via _to_usd_safe.
    """
    if not isinstance(lunge, dict):
        return _to_usd_safe(lunge)
    out = {}
    for k, v in lunge.items():
        try:
            out[str(k)] = _to_usd_safe(v)
        except Exception as e:
            print(f"[previz_usd_hook] NOTE: LUNGE_V3['{k}'] convert failed: {e}")
            continue
    return out


def _collect_story_extras(mod, story):
    """Session-21 parity additions — story collections the original
    carrier missed (found by the JSON-vs-USD audit of the export path).
    ADDITIVE only: the webpreviz converter reads keys verbatim, so new
    keys are safe while no existing key changes shape.

    Mirrors export_previz_package.py's native story collector so the
    USD sidecar and previz.json carry the same story (the v2 export's
    parity gate checks exactly this overlap).
    """
    fps = float(getattr(mod, "FPS", 24))
    frame_start = int(getattr(mod, "FRAME_START", 1))

    def _frame_at(t):
        # escape_lib convention: frame = round(t * FPS) + FRAME_START
        return int(round(t * fps)) + frame_start

    # chase falls (S6 gunner hits): {chase_index: t_hit}
    # USD customData forbids list-of-dicts (VtDictionary inside a vector
    # is not a valid scene description datatype — session-21 find: one
    # bad key kills the WHOLE stage payload); dict-of-dicts emulation,
    # same law as _collect_knockdowns.
    cf = _try_collect(mod, "CHASE_FALLS_V3")
    if cf is not None:
        try:
            story["chase_falls"] = {
                str(k): {"chase_index": int(k), "t_hit": float(v),
                         "frame": _frame_at(float(v))}
                for k, v in cf.items()
            }
        except Exception as e:
            print(f"[previz_usd_hook] NOTE: CHASE_FALLS_V3 parse failed: {e}")

    # per-actor run-cycle params
    rp = _try_collect(mod, "RUN_PARAMS")
    if rp is not None:
        try:
            story["run_params"] = {
                str(k): {str(kk): (str(vv) if isinstance(vv, str) else float(vv))
                         for kk, vv in v.items()}
                for k, v in rp.items()
            }
        except Exception as e:
            print(f"[previz_usd_hook] NOTE: RUN_PARAMS parse failed: {e}")

    # motion policy (intended-static regexes + subject tree)
    mp = _try_collect(mod, "MOTION_POLICY")
    if mp is not None:
        d = {}
        is_ = mp.get("intended_static")
        if is_ is not None:
            d["intended_static"] = [str(x) for x in is_]
        ist = mp.get("intended_subject_tree")
        if ist is not None:
            d["intended_subject_tree"] = str(ist)
        if d:
            story["motion_policy"] = d

    # flatness policy (deliberate flat/fade windows)
    fp = _try_collect(mod, "FLATNESS_POLICY")
    if fp is not None:
        try:
            story["flatness_policy"] = {
                str(k): {"f0": int(v[0]), "f1": int(v[1])}
                for k, v in fp.items()
            }
        except Exception as e:
            print(f"[previz_usd_hook] NOTE: FLATNESS_POLICY parse failed: {e}")

    # scalars the audit found missing
    rs = _try_collect(mod, "RUN_SPEED")
    if rs is not None:
        story["run_speed"] = float(rs)
    ry = _try_collect(mod, "RUN_START_Y")
    if ry is not None:
        story["run_start_y"] = float(ry)


def _collect_story(scene_module_name):
    """Try to import the scene module and collect story constants.
    Returns dict or None if module not importable. Caches the imported module
    on the PrevizUSDHook class for reuse by _build_object_payload.
    """
    if not scene_module_name:
        return None
    try:
        mod = importlib.import_module(scene_module_name)
        # Cache the module so _build_object_payload doesn't re-import per object
        PrevizUSDHook._cached_scene_module = mod
    except Exception as e:
        print(f"[previz_usd_hook] NOTE: scene module '{scene_module_name}' not "
              f"importable; story-level customData will be skipped ({e})")
        return None

    story = {}
    # Shots (try V3 then V2 fallback)
    shots = _try_collect(mod, "SHOTS_V3", _collect_shots)
    if shots is not None:
        story["shots"] = shots
    else:
        shots_v2 = _try_collect(mod, "SHOTS_V2", _collect_shots)
        if shots_v2 is not None:
            story["shots"] = shots_v2
    # Speed profile
    seg = _try_collect(mod, "_V3_SEG", _collect_speed_profile)
    if seg is not None:
        story["speed_profile"] = seg
    # Jeep weave
    jx = _try_collect(mod, "JEEP_X_V3", _collect_jeep_weave)
    if jx is not None:
        story["jeep_weave"] = jx
    # Knockdowns
    kd = _try_collect(mod, "KNOCKDOWNS_V3", _collect_knockdowns)
    if kd is not None:
        story["knockdowns"] = kd
    # Lunge (USD-REVIEW-1 A1: use _collect_lunge which handles tuple-of-tuples)
    lunge = _try_collect(mod, "LUNGE_V3", _collect_lunge)
    if lunge is not None:
        story["lunge"] = lunge
    # Muzzle bursts
    mb = _try_collect(mod, "MUZZLE_BURSTS_V3", _collect_muzzle_bursts)
    if mb is not None:
        story["muzzle_bursts"] = mb
    # Dialog
    dialog = _try_collect(mod, "DIALOG", _collect_dialog)
    if dialog is not None:
        story["dialog"] = dialog
    # Cameras
    cams = _try_collect(mod, "CAMS_V3", _collect_cameras)
    if cams is not None:
        story["cameras"] = cams
    # Board (USD-REVIEW-1 A2: _collect_board now handles 1-tuple run_x)
    board = _try_collect(mod, "BOARD", _collect_board)
    if board is not None:
        story["board"] = board
    # Hero mode
    hero_mode = _try_collect(mod, "HERO_MODE")
    if hero_mode is not None:
        story["hero_mode"] = str(hero_mode)
    # RB config
    rb_falls = _try_collect(mod, "RB_FALLS")
    if rb_falls is not None:
        story["rb_falls"] = list(rb_falls)
    rb_kd = _try_collect(mod, "RB_KD")
    if rb_kd is not None:
        story["rb_kd"] = list(rb_kd)
    # Barriers (if present)
    barricade_t = _try_collect(mod, "BARRICADE_T_V3")
    if barricade_t is not None:
        story["barricade_t"] = float(barricade_t)
    barricade_y = _try_collect(mod, "BARRICADE_Y_V3")
    if barricade_y is not None:
        story["barricade_y"] = float(barricade_y)
    t_drive = _try_collect(mod, "T_DRIVE")
    if t_drive is not None:
        story["t_drive"] = float(t_drive)
    # Total frames
    total_frames = _try_collect(mod, "TOTAL_FRAMES_V3")
    if total_frames is not None:
        story["total_frames"] = int(total_frames)
    # Session-21 parity additions (chase_falls, run_params, motion_policy,
    # flatness_policy, run_speed, run_start_y)
    _collect_story_extras(mod, story)
    return story


# ---------------------------------------------------------------------------
# Per-object payload
# ---------------------------------------------------------------------------

def _build_object_payload(obj, scene_module=None):
    """Build per-wrapper-prim previz:entity payload for one bpy object.

    Args:
        obj: bpy.types.Object
        scene_module: optional cached scene module (used to resolve pose_name
            and rig_mode). If None, pose_name and rig_mode will be "" — the
            per-object payload still has all the other fields.
    """
    # Try to resolve pose_name from BOARD (if scene module available).
    pose_name = ""
    rig_mode = ""
    if scene_module is not None:
        try:
            board = getattr(scene_module, "BOARD", None)
            hero_mode = getattr(scene_module, "HERO_MODE", "")
            if board and obj.name in board:
                entry = board[obj.name]
                main_tuple = entry[0] if isinstance(entry, tuple) and len(entry) > 0 else entry
                if hasattr(main_tuple, "__len__") and len(main_tuple) > 5:
                    pose_name = str(main_tuple[5])
            rig_mode = str(hero_mode) if hero_mode else ""
        except Exception:
            pass

    # Resolve identity color
    color_rgba = _resolve_identity_color(obj)

    payload = {
        "blender_name": obj.name,
        "blender_type": str(obj.type),
        "anchor_to": obj.parent.name if obj.parent else "",
        "body_type": "mesh" if obj.type == "MESH" else str(obj.type).lower(),
        "pose_name": pose_name,
        "rig_mode": rig_mode,
        "identity_color_rgba": list(color_rgba) if color_rgba else [],
        "kit_atmo": bool(obj.get("kit_atmo", False)),
        "is_camera": obj.type == "CAMERA",
        "camera_lens_mm": float(obj.data.lens) if obj.type == "CAMERA" else 0.0,
        "is_light": obj.type == "LIGHT",
        "light_energy": float(obj.data.energy) if obj.type == "LIGHT" else 0.0,
    }
    return payload


def _resolve_identity_color(obj):
    """Return (r, g, b, a) tuple from obj's color source, or None.

    Priority:
      1. obj["previz_identity_color"] custom prop (if set, RGBA).
      2. First material's diffuse_color for meshes (RGBA linear).
      3. obj.data.color for lights (RGB, alpha=1).
      4. obj.color (viewport display color, RGBA).
      5. None.
    """
    # 1. Custom prop override
    custom = obj.get("previz_identity_color")
    if custom is not None:
        try:
            c = list(custom)
            if len(c) >= 3:
                return (float(c[0]), float(c[1]), float(c[2]),
                        float(c[3]) if len(c) > 3 else 1.0)
        except Exception:
            pass

    # 2. Mesh: first material's diffuse_color
    if obj.type == 'MESH':
        try:
            mats = obj.data.materials
            if mats and len(mats) > 0 and mats[0] is not None:
                dc = mats[0].diffuse_color
                if dc and len(dc) >= 3:
                    return (float(dc[0]), float(dc[1]), float(dc[2]),
                            float(dc[3]) if len(dc) > 3 else 1.0)
        except Exception:
            pass

    # 3. Light: obj.data.color
    if obj.type == 'LIGHT' and hasattr(obj.data, "color"):
        try:
            c = obj.data.color
            if c and len(c) >= 3:
                return (float(c[0]), float(c[1]), float(c[2]), 1.0)
        except Exception:
            pass

    # 4. obj.color (viewport display color, RGBA)
    try:
        c = obj.color
        if c and len(c) >= 3:
            return (float(c[0]), float(c[1]), float(c[2]),
                    float(c[3]) if len(c) > 3 else 1.0)
    except Exception:
        pass

    return None


# ---------------------------------------------------------------------------
# Stage-level payload
# ---------------------------------------------------------------------------

def _build_stage_payload(scene_module_name=None, scene_module=None):
    """Build the stage-level previz:entity payload (on /root).

    Args:
        scene_module_name: name of the scene module (for story data collection)
        scene_module: cached module instance (if already imported by caller)
    """
    scene = bpy.context.scene
    payload = {
        "schema_version": "1.0",
        "kind": "environment",
        "blender_version": str(bpy.app.version_string),
        "scene_name": str(scene.name),
        "fps": int(scene.render.fps),
        "frame_range": [int(scene.frame_start), int(scene.frame_end)],
    }

    # Story-level (from scene module if available)
    if scene_module is None and scene_module_name:
        # Try the cached module first
        scene_module = getattr(PrevizUSDHook, "_cached_scene_module", None)
        if scene_module is None:
            try:
                scene_module = importlib.import_module(scene_module_name)
                PrevizUSDHook._cached_scene_module = scene_module
            except Exception as e:
                print(f"[previz_usd_hook] NOTE: scene module '{scene_module_name}' "
                      f"not importable; story-level customData will be skipped ({e})")
                scene_module = None

    if scene_module is not None:
        story = _collect_story_inline(scene_module)
        for key, value in story.items():
            payload[key] = value

    # Timeline block (combines fps, frame_range, t_drive, speed_profile,
    # barricade_t, barricade_y).
    timeline = {
        "fps": int(scene.render.fps),
        "frame_range": [int(scene.frame_start), int(scene.frame_end)],
    }
    if "t_drive" in payload:
        timeline["t_drive"] = payload["t_drive"]
    if "speed_profile" in payload:
        timeline["speed_profile"] = payload["speed_profile"]
    if "barricade_t" in payload:
        timeline["barricade_t"] = payload["barricade_t"]
    if "barricade_y" in payload:
        timeline["barricade_y"] = payload["barricade_y"]
    if "total_frames" in payload:
        timeline["total_frames"] = payload["total_frames"]
    payload["timeline"] = timeline

    # World / environment
    env = {}
    if scene.world:
        try:
            if scene.world.use_nodes:
                bg = scene.world.node_tree.nodes.get("Background")
                if bg:
                    color = bg.inputs["Color"].default_value
                    strength = bg.inputs["Strength"].default_value
                    env["background_color"] = [round(float(c), 4) for c in color[:3]]
                    env["background_strength"] = round(float(strength), 4)
            else:
                env["background_color"] = [round(float(c), 4) for c in scene.world.color[:3]]
                env["background_strength"] = 1.0
        except Exception:
            pass
    payload["environment"] = env

    return payload


def _collect_story_inline(mod):
    """Collect story constants from an already-imported module.
    Inline version of _collect_story that doesn't re-import (used by
    _build_stage_payload when the module is already cached).
    """
    story = {}
    shots = _try_collect(mod, "SHOTS_V3", _collect_shots)
    if shots is None:
        shots = _try_collect(mod, "SHOTS_V2", _collect_shots)
    if shots is not None:
        story["shots"] = shots
    seg = _try_collect(mod, "_V3_SEG", _collect_speed_profile)
    if seg is not None:
        story["speed_profile"] = seg
    jx = _try_collect(mod, "JEEP_X_V3", _collect_jeep_weave)
    if jx is not None:
        story["jeep_weave"] = jx
    kd = _try_collect(mod, "KNOCKDOWNS_V3", _collect_knockdowns)
    if kd is not None:
        story["knockdowns"] = kd
    lunge = _try_collect(mod, "LUNGE_V3", _collect_lunge)
    if lunge is not None:
        story["lunge"] = lunge
    mb = _try_collect(mod, "MUZZLE_BURSTS_V3", _collect_muzzle_bursts)
    if mb is not None:
        story["muzzle_bursts"] = mb
    dialog = _try_collect(mod, "DIALOG", _collect_dialog)
    if dialog is not None:
        story["dialog"] = dialog
    cams = _try_collect(mod, "CAMS_V3", _collect_cameras)
    if cams is not None:
        story["cameras"] = cams
    board = _try_collect(mod, "BOARD", _collect_board)
    if board is not None:
        story["board"] = board
    hero_mode = _try_collect(mod, "HERO_MODE")
    if hero_mode is not None:
        story["hero_mode"] = str(hero_mode)
    rb_falls = _try_collect(mod, "RB_FALLS")
    if rb_falls is not None:
        story["rb_falls"] = list(rb_falls)
    rb_kd = _try_collect(mod, "RB_KD")
    if rb_kd is not None:
        story["rb_kd"] = list(rb_kd)
    barricade_t = _try_collect(mod, "BARRICADE_T_V3")
    if barricade_t is not None:
        story["barricade_t"] = float(barricade_t)
    barricade_y = _try_collect(mod, "BARRICADE_Y_V3")
    if barricade_y is not None:
        story["barricade_y"] = float(barricade_y)
    t_drive = _try_collect(mod, "T_DRIVE")
    if t_drive is not None:
        story["t_drive"] = float(t_drive)
    total_frames = _try_collect(mod, "TOTAL_FRAMES_V3")
    if total_frames is not None:
        story["total_frames"] = int(total_frames)
    # Session-21 parity additions (same as _collect_story)
    _collect_story_extras(mod, story)
    return story


# ---------------------------------------------------------------------------
# USDHook subclass
# ---------------------------------------------------------------------------

class PrevizUSDHook(USDHook):
    if USDHook is not None:
        bl_idname = "previz_usd_hook"
        bl_label = "Previz USD Carrier"
        bl_description = ("Publish previz:entity customData + "
                          "previz:identityColor custom attr on every "
                          "wrapper prim during USD export")

    # Set this before registering to pass the scene module name.
    scene_module_name: str | None = None
    # Cached scene module — avoids re-importing per object (USD-REVIEW-1 C13)
    _cached_scene_module = None

    @staticmethod
    def on_export(export_context):
        """Blender calls this AFTER native USD authoring, BEFORE stage save.
        Returns True on success, False to abort the export.
        """
        try:
            # Required: expose bundled modules so pxr is importable.
            try:
                bpy.utils.expose_bundled_modules()
            except AttributeError:
                # Older Blender (<3.4?) — pxr is on sys.path by default.
                pass
            except Exception as e:
                # Some Blender versions have a different signature; tolerate.
                print(f"[previz_usd_hook] NOTE: expose_bundled_modules failed: {e}")

            from pxr import Usd, Sdf, Gf

            stage = export_context.get_stage()
            if stage is None:
                print("[previz_usd_hook] ERROR: stage is None; abort")
                return False

            # Find the root prim (Blender's USD exporter names it "/root").
            root_path = "/root"
            root_prim = stage.GetPrimAtPath(root_path)
            if not root_prim or not root_prim.IsValid():
                # Try the stage's default prim path.
                default_prim = stage.GetDefaultPrim()
                if default_prim and default_prim.IsValid():
                    root_prim = default_prim
                    root_path = str(default_prim.GetPath())
                else:
                    print("[previz_usd_hook] ERROR: no /root prim and no default prim; abort")
                    return False

            scene_module_name = PrevizUSDHook.scene_module_name
            # Use the cached module if available
            scene_module = getattr(PrevizUSDHook, "_cached_scene_module", None)
            if scene_module is None and scene_module_name:
                try:
                    scene_module = importlib.import_module(scene_module_name)
                    PrevizUSDHook._cached_scene_module = scene_module
                except Exception as e:
                    print(f"[previz_usd_hook] NOTE: scene module not importable "
                          f"({e}); story-level customData will be skipped")

            # Build a name → prim map ONCE (USD-REVIEW-1 C12: was O(N²) per-object
            # Traverse fallback). Now we walk the stage once.
            prim_name_map = _build_prim_name_map(stage, root_path)
            # Also build a /root/<sanitized_name> direct lookup
            direct_lookup_cache = {}

            def lookup_wrapper(obj):
                """Look up a bpy object's USD wrapper prim.

                Strategy (USD-REVIEW-1 A3 fix + USD-REVIEW-2 C.new1 polish):
                1. ONLY try /root/<obj.name> directly IF the name doesn't need
                   sanitization (no special chars). This avoids the 360
                   SdfPath "Ill-formed path" warnings on production scenes
                   (USD-REVIEW-2 C.new1).
                2. Try /root/<sanitized_name> (Blender sanitizes '.', ' ', etc.
                   to '_').
                3. Look up by sanitized name in the prim_name_map (built once
                   from stage.Traverse).
                4. Look up by original name in the prim_name_map (rare case where
                   Blender didn't sanitize).
                """
                obj_name = obj.name
                sanitized = _sanitize_usd_name(obj_name)
                needs_sanitization = (sanitized != obj_name)

                # Fast path: direct /root/<name> — ONLY if name is already USD-safe
                # (USD-REVIEW-2 C.new1: skip if needs sanitization to avoid SdfPath warnings)
                if not needs_sanitization:
                    path = root_path + "/" + obj_name
                    prim = stage.GetPrimAtPath(path)
                    if prim and prim.IsValid():
                        return prim
                # Sanitized path
                if needs_sanitization:
                    path = root_path + "/" + sanitized
                    prim = stage.GetPrimAtPath(path)
                    if prim and prim.IsValid():
                        return prim
                # Name map lookup (sanitized)
                prim = prim_name_map.get(sanitized)
                if prim and prim.IsValid():
                    return prim
                # Name map lookup (original) — only try if different from sanitized
                if needs_sanitization:
                    prim = prim_name_map.get(obj_name)
                    if prim and prim.IsValid():
                        return prim
                return None

            # 1. Stage-level previz:entity on root
            try:
                stage_payload = _build_stage_payload(scene_module_name, scene_module)
                # Verify the payload is USD-safe before setting (defensive —
                # _to_usd_safe should already handle this)
                root_prim.SetCustomDataByKey("previz:entity", stage_payload)
                print(f"[previz_usd_hook] root previz:entity keys: "
                      f"{list(stage_payload.keys())}")
            except Exception as e:
                print(f"[previz_usd_hook] WARN: stage-level payload failed: {e}")
                print(traceback.format_exc())

            # 2 + 3. Per-wrapper-prim previz:entity + previz:identityColor
            n_obj_payload = 0
            n_color_attr = 0
            n_no_wrapper = 0
            for obj in bpy.context.scene.objects:
                try:
                    wrapper = lookup_wrapper(obj)
                    if not wrapper or not wrapper.IsValid():
                        n_no_wrapper += 1
                        continue

                    # Per-object previz:entity
                    obj_payload = _build_object_payload(obj, scene_module)
                    wrapper.SetCustomDataByKey("previz:entity", obj_payload)
                    n_obj_payload += 1

                    # Per-object previz:identityColor custom attr
                    color = _resolve_identity_color(obj)
                    if color is not None:
                        try:
                            attr = wrapper.CreateAttribute(
                                "previz:identityColor",
                                Sdf.ValueTypeNames.Color3f, custom=True)
                            attr.Set(Gf.Vec3f(float(color[0]), float(color[1]),
                                              float(color[2])))
                            n_color_attr += 1
                        except Exception as e:
                            print(f"[previz_usd_hook] NOTE: identityColor "
                                  f"for {obj.name} failed: {e}")
                except Exception as e:
                    print(f"[previz_usd_hook] NOTE: object {obj.name} "
                          f"payload failed: {e}")
                    print(traceback.format_exc())
                    continue

            print(f"[previz_usd_hook] wrote {n_obj_payload} object "
                  f"previz:entity customData + {n_color_attr} identityColor "
                  f"attrs ({n_no_wrapper} objects had no matching wrapper prim)")
            return True

        except ImportError as e:
            # pxr import failure — abort cleanly
            print(f"[previz_usd_hook] ERROR (pxr import failed): {e}")
            return False
        except Exception as e:
            # Defensive: NEVER raise from on_export — Blender aborts the
            # whole export on raise.
            print(f"[previz_usd_hook] ERROR (caught, returning False): {e}")
            print(traceback.format_exc())
            return False


# ---------------------------------------------------------------------------
# Register / unregister
# ---------------------------------------------------------------------------

def register(scene_module_name=None):
    """Register the USDHook. Call BEFORE bpy.ops.wm.usd_export.
    Set scene_module_name to enable story-level customData (Option C).
    """
    if USDHook is None:
        print("[previz_usd_hook] USDHook base class not available — skipping register")
        return
    PrevizUSDHook.scene_module_name = scene_module_name
    PrevizUSDHook._cached_scene_module = None  # reset cache
    if not hasattr(bpy.types, "PREVIZ_USD_HOOK_REGISTERED"):
        try:
            bpy.utils.register_class(PrevizUSDHook)
            bpy.types.PREVIZ_USD_HOOK_REGISTERED = True
            print(f"[previz_usd_hook] registered (scene_module={scene_module_name})")
        except Exception as e:
            print(f"[previz_usd_hook] register failed: {e}")


def unregister():
    """Unregister the USDHook. Call AFTER bpy.ops.wm.usd_export (in finally)."""
    if hasattr(bpy.types, "PREVIZ_USD_HOOK_REGISTERED"):
        try:
            bpy.utils.unregister_class(PrevizUSDHook)
            del bpy.types.PREVIZ_USD_HOOK_REGISTERED
            PrevizUSDHook._cached_scene_module = None  # clear cache
            print("[previz_usd_hook] unregistered")
        except Exception as e:
            print(f"[previz_usd_hook] unregister failed: {e}")


# ---------------------------------------------------------------------------
# Self-test main (smoke test — register, do a no-op export, unregister)
# ---------------------------------------------------------------------------

def main():
    """Self-test: register + unregister + dry-run collect_story.
    Does NOT call bpy.ops.wm.usd_export (call export_usd.py for the real thing).
    """
    import argparse
    p = argparse.ArgumentParser(
        description="previz_usd_hook self-test (register/unregister cycle)")
    p.add_argument("--scene-module", default=None,
                   help="Scene module name (e.g., scene_escape_v4) for "
                        "story-data collection self-test")
    args = p.parse_args(sys.argv[sys.argv.index("--") + 1:]
                         if "--" in sys.argv else [])

    print("[previz_usd_hook] self-test begin")
    register(scene_module_name=args.scene_module)
    print(f"[previz_usd_hook] registered: "
          f"{hasattr(bpy.types, 'PREVIZ_USD_HOOK_REGISTERED')}")

    # Dry-run collect_story
    if args.scene_module:
        print(f"[previz_usd_hook] collect_story({args.scene_module}):")
        story = _collect_story(args.scene_module)
        if story is None:
            print("  (no story data — module not importable)")
        else:
            for k, v in story.items():
                if isinstance(v, dict):
                    print(f"  {k}: dict with {len(v)} entries")
                elif isinstance(v, list):
                    print(f"  {k}: list with {len(v)} entries")
                else:
                    print(f"  {k}: {type(v).__name__} = {v}")

    # Per-object payload (no objects in this self-test unless scene built)
    scene_module = PrevizUSDHook._cached_scene_module
    for obj in list(bpy.context.scene.objects)[:3]:
        payload = _build_object_payload(obj, scene_module)
        print(f"[previz_usd_hook] {obj.name} payload: {list(payload.keys())}")
        color = _resolve_identity_color(obj)
        print(f"  color: {color}")

    unregister()
    print(f"[previz_usd_hook] registered after unregister: "
          f"{hasattr(bpy.types, 'PREVIZ_USD_HOOK_REGISTERED')}")
    print("[previz_usd_hook] self-test done")


if __name__ == "__main__":
    main()

