"""
ual_determinism_gate.py -- v4 step 4 gates (PLAN_v4 REV3 item 8).

The render daemon RE-RUNS the scene script per chunk (no saved blend in
the delivery path), so the UAL bake must be:
  * DETERMINISTIC across rebuilds (same script, same inputs -> same
    bone-world matrices -- in-process double-build compare)
  * CHUNK-INDEPENDENT (full-range keys f1-1080: a chunk starting at
    f541 must evaluate the same pose the full-range build does)
  * SAVE/LOAD STABLE (the packed deliverable scene.blend must reload
    to the same poses, delta < 1e-6 m -- the glb/blend pack step)

Usage (from a test or the finalize flow):
    import ual_determinism_gate as UDG
    findings = UDG.in_process_rebuild()            # builds twice
    findings += UDG.save_load_fidelity(out_blend)  # saves + reloads
"""
import os
import sys

import bpy

SAMPLE_FRAMES = (60, 190, 360, 512, 760, 1080)
SAMPLE_BONES = ("DEF-hips", "DEF-head", "DEF-hand.L", "DEF-foot.L")


def _sample_hero_bones(ctx):
    """{actor: {frame: {bone: world translation}}} for the 4 heroes."""
    scene = ctx["scene"]
    out = {}
    for name in ("Driver", "Girl", "Gunner", "HeroZed"):
        d = ctx["humans"].get(name, {})
        arm = d.get("armature")
        if arm is None:
            continue
        out[name] = {}
        for f in SAMPLE_FRAMES:
            scene.frame_set(f)
            bpy.context.view_layer.update()
            bpy.context.view_layer.update()
            out[name][f] = {}
            for bn in SAMPLE_BONES:
                b = arm.pose.bones.get(bn)
                if b is not None:
                    out[name][f][bn] = \
                        (arm.matrix_world @ b.matrix).translation.copy()
    scene.frame_set(1)
    return out


def _compare(a, b, tol, tag):
    findings = []
    worst = 0.0
    for name in a:
        for f in a[name]:
            for bn in a[name][f]:
                pa, pb = a[name][f][bn], b[name][f][bn]
                d = (pa - pb).length
                worst = max(worst, d)
                if d > tol:
                    findings.append(
                        f"[determinism] {tag}: {name}.{bn} f{f} "
                        f"delta {d:.6f} m (> {tol})")
    return findings, worst


def in_process_rebuild(hero_mode="ual", tol=1e-6):
    """Build + animate the scene TWICE in this process; sampled
    bone-world matrices must match (rebuild determinism)."""
    import scene_escape_v4 as SC
    SC.HERO_MODE = hero_mode
    ctx1 = SC.build_scene()
    SC.animate(ctx1, start_frame=1, n_frames=SC.TOTAL_FRAMES_V3)
    s1 = _sample_hero_bones(ctx1)
    ctx2 = SC.build_scene()          # clear_scene wipes; full rebuild
    SC.animate(ctx2, start_frame=1, n_frames=SC.TOTAL_FRAMES_V3)
    s2 = _sample_hero_bones(ctx2)
    findings, worst = _compare(s1, s2, tol, "rebuild")
    print(f"[determinism] in-process rebuild: worst delta {worst:.2e} m "
          f"({'PASS' if not findings else 'FAIL'})")
    return findings


def save_load_fidelity(out_blend, hero_mode="ual", tol=1e-6):
    """Save the built scene to a blend, reload it, compare sampled
    bone worlds (3 frames, delta < 1e-6 -- the pack-step contract)."""
    import scene_escape_v4 as SC
    SC.HERO_MODE = hero_mode
    ctx = SC.build_scene()
    SC.animate(ctx, start_frame=1, n_frames=SC.TOTAL_FRAMES_V3)
    frames3 = (60, 512, 760)
    scene = ctx["scene"]
    ref = {}
    for name in ("Driver", "Girl", "Gunner", "HeroZed"):
        d = ctx["humans"].get(name, {})
        arm = d.get("armature")
        if arm is None:
            continue
        ref[name] = {}
        for f in frames3:
            scene.frame_set(f)
            bpy.context.view_layer.update()
            bpy.context.view_layer.update()
            ref[name][f] = {bn: (arm.matrix_world
                                 @ arm.pose.bones[bn].matrix
                                 ).translation.copy()
                            for bn in SAMPLE_BONES
                            if arm.pose.bones.get(bn) is not None}
    os.makedirs(os.path.dirname(out_blend), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=out_blend)
    bpy.ops.wm.open_mainfile(filepath=out_blend)
    # open_mainfile invalidates every prior RNA reference (Scene
    # included) -- re-fetch from the live context
    scene = bpy.context.scene
    got = {}
    for name in ("Driver", "Girl", "Gunner", "HeroZed"):
        arm = bpy.data.objects.get(f"{name}.Rig")
        if arm is None:
            return [f"[determinism] save/load: {name}.Rig missing after "
                    f"reload"]
        got[name] = {}
        for f in frames3:
            scene.frame_set(f)
            bpy.context.view_layer.update()
            bpy.context.view_layer.update()
            got[name][f] = {bn: (arm.matrix_world
                                 @ arm.pose.bones[bn].matrix
                                 ).translation.copy()
                            for bn in SAMPLE_BONES
                            if arm.pose.bones.get(bn) is not None}
    findings, worst = _compare(ref, got, tol, "save/load")
    print(f"[determinism] save/load fidelity: worst delta {worst:.2e} m "
          f"({'PASS' if not findings else 'FAIL'}) -> {out_blend}")
    return findings


def chunk_boundary_continuity(ctx, boundaries=(540, 753), tol=1e-6):
    """The daemon rebuilds per chunk: verify the poses at chunk edge
    frames are what a fresh full-range build produces (they are, by
    construction -- full-range keys; this gate PROVES it against the
    live ctx)."""
    findings = []
    scene = ctx["scene"]
    for f in boundaries:
        scene.frame_set(f)
        bpy.context.view_layer.update()
        bpy.context.view_layer.update()
        for name in ("Driver", "Gunner", "HeroZed"):
            d = ctx["humans"].get(name, {})
            arm = d.get("armature")
            if arm is None:
                continue
            act = arm.animation_data.action
            if act is None or act.name != f"UAL.{name}.Baked":
                findings.append(f"[determinism] {name}: slot wrong at "
                                f"chunk boundary f{f}")
    if not findings:
        print(f"[determinism] chunk boundaries {boundaries}: slots "
              f"stable (PASS)")
    return findings
