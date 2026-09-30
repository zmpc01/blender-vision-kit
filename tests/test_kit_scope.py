#!/usr/bin/env python3
"""test_kit_scope.py — kit-scope guard (session-14, REPO_HYGIENE_v2 D3).

The kit repo is a RELEASE repo: it may carry only core tooling born from
production stress-testing. Project scenes, assets, research, evidence and
deliverables belong in the PROJECT repo (blender-escape-previz) or the R&D
repo (placement-lab). This gate fails the build if any forbidden path is
git-tracked here.

Rules (review-simulated: zero false positives against the kit-keep set,
zero false negatives against the removal set):
  - DIRECTORY rules for payload classes (project/, experiments/, output/, ...)
  - NAME-PREFIX rules for unambiguous project families (scene_escape, assets_,
    test_assets_, dump_, look_, pose_, probe_, shade_)
  - EXACT-NAME rules for the remainder.
Never forbid by broad prefixes like scene_/test_/render_ wholesale —
scene_template, test_polyhaven, render_daemon are kit keepers.

Run: python3 tests/test_kit_scope.py   (no Blender needed)
Exit 0 = clean; exit 1 = forbidden paths found (printed).
"""
import re
import subprocess
import sys
import os

KIT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FORBIDDEN = [
    # payload directories
    r"^project/",
    r"^experiments/",
    r"^output/",
    r"^smoke/impl_bl_prep/",
    r"^smoke/.*\.exr$",
    r"^assets/(dialog|characters)/",
    # unambiguous project families (scripts/)
    r"^scripts/(scene_escape|escape_lib|crowd_agents|shot_pipeline)",
    r"^scripts/(pack_v32|patch_v32|patch_street_v32|s1_probe|s8_probe_v32|flat_light_experiment|render_capsule_poses|render_mangled|macro_bed|macro_runner|only_driver|vision_flow_study)",
    r"^scripts/(assets_|test_assets_|dump_|look_|pose_|probe_|shade_)",
    r"^scripts/(axis_truth|bisect_pose|color_check|isolate_gunner|list_bones|list_clean|make_clean_rig|reskin_cesium|zed_macro|inspect_humanoids|preview_humanoids|derive_axes|test_mist_off|tune_render_quality|test_rb_launch)\.py$",
    r"^scripts/(export_v2_deliverables|export_v3_deliverables|export_v3_2_deliverables|gen_dialog|mux_dialog|vlm_shots_v2|framing_audit)\.sh$",
]

# VENDORED project-lineage scripts deliberately kept in the kit (the
# session-17 practice, ruled explicitly s28): production-stressed
# previz-born tooling that a KIT workflow imports or documents. This
# is an OWNER-decision set -- every entry names its consuming kit
# workflow, and the entry leaves the set when the kit grows a proper
# generalized replacement (the gait_modifiers lift is the model:
# previz code that becomes a kit engine stops being vendored).
VENDORED = {
    # the UAL actor builder -- kb/rigged_characters.md documents the
    # import path; the kit's rigged-character smoke depends on it
    "scripts/assets_ual_actors.py",
}

# Positive controls — the gate must catch these synthetic paths (proves the
# patterns are live) and must NOT catch keeper names (proves no false
# positives). If a control fails, the pattern list itself drifted.
MUST_MATCH = [
    "project/research/anything.md",
    "experiments/preview/runs/x.json",
    "output/ual/red_check.png",
    "smoke/impl_bl_prep/probe_light.py",
    "smoke/cornell_cycles.exr",
    "assets/dialog/line01_go.wav",
    "assets/characters/CesiumMan.glb",
    "scripts/scene_escape_v4.py",
    "scripts/escape_lib.py",
    "scripts/crowd_agents.py",
    "scripts/shot_pipeline.py",
    "scripts/patch_v32_f.py",
    "scripts/assets_spaceship.py",
    "scripts/test_assets_spaceship.py",
    "scripts/dump_frames.py",
    "scripts/look_moon.py",
    "scripts/pose_spin.py",
    "scripts/probe_thing.py",
    "scripts/shade_test.py",
    "scripts/macro_runner.py",
    "scripts/gen_dialog.sh",
    "scripts/mux_dialog.sh",
    "scripts/framing_audit.sh",
]
MUST_NOT_MATCH = [
    "scripts/scene_template.py",
    "scripts/scene_cornell.py",
    "scripts/transient_scan.py",
    "scripts/scene_schema.py",
    "scripts/scene_physics_usability.py",
    "scripts/scene_interior_room.py",
    "scripts/test_polyhaven.py",
    "scripts/motion_study.py",
    "scripts/render_daemon.py",
    "scripts/framing_audit.py",
    "scripts/flicker_probe.py",
    "scripts/coplanarity_audit.py",
    "scripts/physics_place.py",
    "scripts/placement_lib.py",
    "scripts/encode_deliverable.sh",
    "scripts/blender_kit/__init__.py",
    "scripts/ual_test/anything.py",
    "tests/test_kit_scope.py",
    "viewer/index.html",
    "docs/REPO_HYGIENE_v2.md",
    "smoke/smoke_render.py",
    "smoke/cornell.obj",
    "assets/vendor/ual/LICENSE",
    "worklog.md",
] + sorted(VENDORED)   # the allowlist must be live (a vendored path
#                          that also matched nothing needs no entry --
#                          the control proves the ones that DO match)



def main() -> int:
    # 1. self-test the pattern list
    failures = []
    for path in MUST_MATCH:
        if path in VENDORED:
            continue          # a vendored path may match FORBIDDEN by
            #                  design; the audit below skips it
        if not any(re.match(p, path) for p in FORBIDDEN):
            failures.append("CONTROL MISS: %s matched no forbidden pattern" % path)
    for path in MUST_NOT_MATCH:
        if path in VENDORED:
            # a vendored path must still MATCH a forbidden pattern --
            # an entry that matches nothing is stale (needs no
            # exception) and must be dropped from VENDORED
            if not any(re.match(p, path) for p in FORBIDDEN):
                failures.append(
                    "CONTROL STALE: %s is vendored but matches no "
                    "forbidden pattern -- drop it from VENDORED" % path)
            continue
        hits = [p for p in FORBIDDEN if re.match(p, path)]
        if hits:
            failures.append("CONTROL FP: %s matched %s" % (path, hits))
    if failures:
        print("!! test_kit_scope: PATTERN-LIST SELF-TEST FAILED")
        for f in failures:
            print("   " + f)
        return 1

    # 2. audit the real tree
    out = subprocess.run(
        ["git", "-C", KIT_ROOT, "ls-files"],
        capture_output=True, text=True, check=True,
    ).stdout
    tracked = [l for l in out.splitlines() if l.strip()]
    bad = []
    for path in tracked:
        if path in VENDORED:
            continue          # the documented vendored-tool exception
        for pat in FORBIDDEN:
            if re.match(pat, path):
                bad.append((path, pat))
                break
    if bad:
        print("!! test_kit_scope: %d FORBIDDEN PATHS TRACKED IN KIT" % len(bad))
        for path, pat in bad:
            print("   %-60s (%s)" % (path, pat))
        print("Project artifacts belong in blender-escape-previz / placement-lab.")
        print("See docs/REPO_HYGIENE_v2.md + docs/PROJECTS.md.")
        return 1

    # 3. toolchain hygiene (D12, vision-kit): tools/ may be a SYMLINK to a
    # shared provisioned toolchain, but git rewrites symlinked dirs when a
    # checkout writes inside them — leaving a REAL dir with only the two
    # tracked scripts and no blender binary (the broken-symlink signature,
    # hit twice in one session). Warn loudly; not a scope failure.
    tools = os.path.join(KIT_ROOT, "tools")
    if os.path.islink(tools):
        print("test_kit_scope: tools/ is a symlink to %s (shared toolchain OK)"
              % os.readlink(tools))
    elif os.path.isdir(tools):
        if not os.path.exists(os.path.join(tools, "blender", "blender")):
            if os.path.exists(os.path.join(tools, "chunked_dl.sh")):
                # Since the kit owned its downloader (session-3), tools/ is a
                # real dir by design; without a blender binary this is just a
                # fresh clone / mid-provision state. Normal, not an error.
                print("test_kit_scope: tools/ real dir, not yet provisioned "
                      "(fresh clone or install.sh mid-run) — normal")
            else:
                # Legacy broken-symlink signature: a real dir that carries
                # neither the downloader nor a blender binary.
                print("!! test_kit_scope WARNING: tools/ is a REAL dir with "
                      "no blender binary and no chunked_dl.sh — broken-symlink "
                      "signature. Run install.sh")
        else:
            print("test_kit_scope: tools/ is a real dir (provisioned)")

    print("test_kit_scope: PASS (%d tracked files, all kit-scope)" % len(tracked))
    return 0


if __name__ == "__main__":
    sys.exit(main())
