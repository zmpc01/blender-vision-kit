# REPO_HYGIENE_v1 — Separating the release kit from the previz project

> Design doc for the session-14 repo surgery. Status: DRAFT for adversarial
> review. Nothing below is executed until this doc passes a fresh-context
> review round.

## Problem statement

The user's audit (session 14): the **kit repo is the "final release" repo**
and must contain only core skill/script improvements born from production
stress-testing. Today it also carries the whole escape-previz PROJECT:
118 MB of render research, project scene scripts, project dialog audio,
project evidence outputs, and early-session smoke debris. Meanwhile the
**previz project repo** must be the durable home of every project artifact
(deliverables, scenes, research) — the user points at `download/` folders
that die with the sandbox; git is the only disk.

Measured state (session-14 audit):

| Kit path | Files tracked | Size | Class |
|---|---|---|---|
| `project/` | 1062 | 118 MB | PROJECT (12 design docs + research: 720 e2e frames, rig downloads, benchmark jsons) |
| `experiments/ascii_vision/` | 350 | 5 MB | R&D evidence → placement-lab |
| `experiments/physics_facts/` | 4 | — | R&D evidence → placement-lab |
| `output/` | 10 | 2.4 MB | PROJECT evidence (UAL A/B) — violates kit's own `output/` gitignore |
| `smoke/impl_bl_prep/` + exrs | 18 | 2.1 MB | session-debris; history retains |
| `assets/characters/` | 4 | 5.4 MB | PROJECT (CesiumMan UAL A/B rigs) — already in previz |
| `assets/dialog/` | 15 | 1.4 MB | PROJECT (escape dialog wavs) — already in previz |
| `scripts/` project files | ~70 | — | PROJECT (scene_escape*, assets_*, crowd_agents, probes, pose_*, patches, export scripts) |
| `.git` pack | — | 260 MB | history; NOT rewritten this session (D6) |

Previz repo state: v2/v3/v3_2 deliverables ARE tracked (verified in git
tree; v3 lives in history, v2+v3_2 at HEAD). 92 scripts present but 11
project scripts + 5 design docs + all of `research/` are missing. `blrun.sh`
fork is the pre-relocatable version.

placement-lab state: latest (638943d) already fully absorbed into kit
(b09c70e) — lib files byte-identical. No update needed this round.

## D1 — What leaves the kit HEAD (and where it goes)

MOVE → **previz repo** (project artifacts):
1. `project/` entire tree (design docs + `research/`)
2. `scripts/` project set (list in appendix A) — every file whose import
   graph roots in `escape_lib` / `assets_*` / the escape story
3. `assets/characters/`, `assets/dialog/` (already duplicated in previz —
   kit copy simply deleted)
4. `output/ual*/` evidence → previz `project/research/ual_ab/`
5. `scripts/probe_physics_api.py` → **placement-lab** (physics R&D that
   fed F1–F14; lab is the physics R&D home)
6. `experiments/ascii_vision/` + `experiments/physics_facts/` →
   **placement-lab** (R&D evidence; lab already hosts vision_flow artifacts)

DELETE from kit HEAD (recoverable from history; no destination):
7. `smoke/impl_bl_prep/` probe debris + `smoke/*.exr` outputs (keep
   `smoke_render.py`, cornell obj/mtl fixtures — they are smoke inputs)

KIT KEEPS (the release surface): install.sh, run.sh, README/AGENTS/SOP/
PLAN/HANDOFF/FINDINGS(.md), .agents/SKILL.md, worklog.md, scripts core
(blrun.sh, blender_kit/, placement_lib, physics_place, audit_contacts,
ascii_vision family, viewport_capture, keyframe_contact_sheet,
scene_schema, apply_patch, agent_server, polyhaven family, validate_scene,
vlm_critique, framing_audit, coplanarity_audit, flicker_probe,
scene_physics_usability + macro_runner, scene_cornell/corpus/template/
interior_room, save_blend, export_gltf, encode_deliverable,
tune_render_quality, ground_truth_export, render_daemon,
test_ascii_vision/test_polyhaven/test_mist_off), tests/, viewer/,
examples/, docs/, assets/vendor/ual/ (CC0), tools/ (ignored binaries).

Import-graph rule used for the script split: a script is PROJECT iff it
imports `escape_lib`/`assets_*`/`crowd_agents`/`shot_pipeline` or was
written against the escape timeline (probe/pose/patch/export families).
Verified: no KEEPER imports any MOVER.

## D2 — Previz completeness actions

1. Add the 11 missing project scripts (appendix A misses)
2. Add 5 missing design docs (README_v2/v3_2_deliverables, DESIGN_v3_color,
   DESIGN_shot_pipeline, DESIGN_capsule_actors)
3. Add `project/research/` tree + `output/ual*/` evidence
4. Refresh kit-fork core files to current kit state: `blrun.sh`
   (relocatable paths), spot-diff `blender_kit/__init__.py` (currently
   identical — verify, don't blind-copy)
5. Tag the deliverable commits: `v2.2`, `v3`, `v3.2` (download durability:
   a tag is a named, permanent pointer the user can fetch)

## D3 — Prevention (the user's standing requirement: never again)

1. `tests/test_kit_scope.py` — FAILS if `git ls-files` contains any path on
   the forbidden list (project/, assets/dialog, assets/characters,
   experiments/, output/, smoke debris, escape script names). Runs in the
   standard `bash run.sh` test loop; docs tell future agents to run it
   before any kit commit that adds files.
2. `.gitignore` hardening: `project/`, `experiments/`, `assets/dialog/`,
   `assets/characters/`, `output/` (already), `smoke/impl_bl_prep/`
3. AGENTS.md policy section: "kit = tools only; projects fork the kit repo
   and add their scenes/assets there; sync improvements back as lib/script
   PRs" — the two-repo contract, one paragraph, at the top of the file
   layout section.

## D4 — History weight (the 260 MB pack)

Removing files from HEAD does not shrink history. Fresh clones still pull
260 MB. Options were: (a) accept — history is the archive of every
stress-test learning; (b) orphan `release/*` branch as clean default view;
(c) history rewrite (git filter-repo) — requires force-push, forbidden
without explicit user permission. **Decision: (a) accept now, surface (c)
as a user decision in the wrap-up.** The HEAD tree is what a fresh clone
checks out; that is what "clean" means for the release surface.

## D5 — Execution order (atomic-ish, push per step)

1. Kit: gitignore + scope-guard test + AGENTS policy (prevention first —
   so the surgery itself is already covered by the gate)
2. Kit: git rm the D1 classes; run scope guard; run kit smoke (blender
   --version once provisioned) + `python -m py_compile` over kept scripts;
   commit + push
3. Previz: add missing scripts/docs/research/evidence; refresh fork core;
   commit + push; tag v2.2/v3/v3.2
4. placement-lab: add ascii_vision experiments + physics_facts +
   probe_physics_api; commit + push
5. /home/sync refresh (both repos)
6. Fresh-clone e2e: clone kit to a scratch dir → scope guard green, tree
   lean (no project/); clone previz → scene script imports resolve
   (py_compile) → build a 1-frame still if Blender is provisioned

## D6 — Verification gates for this surgery

- G1 scope guard: kit `git ls-files` ∩ forbidden-list = ∅
- G2 import integrity: every KEPT script py_compiles; no kept script
  references a moved module
- G3 previz completeness: every file removed from kit exists in
  previz or placement-lab (reconciled by exact path)
- G4 previz buildability: previz scene script compiles; (if Blender ready)
  renders a still from the v3_2 script
- G5 push state: both remotes + /home/sync updated; tags pushed

## Appendix A — script classification (project set to move)

Already in previz (kit copy deleted only): scene_escape{,_v2,_v3,_v3_2},
assets_{capsule_actors,characters,humanoids,street,vehicles}, crowd_agents,
escape_lib, shot_pipeline, axis_truth, bisect_pose, color_check,
dump_f1{,_full}, dump_walk_keys, isolate_gunner, look_{cesiumman,legs,legs2},
list_bones, list_clean, make_clean_rig, reskin_cesium, zed_macro,
macro_bed, pose_{module_check,search,search_aim,search_arms,truth2},
render_mangled, probe_* (escape/rig/pose families, NOT physics_api),
test_assets_*, test_rb_launch, export_v2/v3_deliverables.sh, gen_dialog.sh,
mux_dialog.sh, vlm_shots_v2.sh, framing_audit.sh, probe_f5_reverdict,
s8_probe_v32, probe_barricade, probe_far_zeds, probe_actor_mesh,
probe_anim_eval, probe_bg, probe_blank_frames, probe_eval_order,
probe_fcurve_eval, probe_locs, probe_master_actors, probe_master_feet,
probe_mats, probe_mist, probe_rifle2, probe_rig_details, probe_run_anim,
probe_skin{,2}, probe_slot, probe_t5a_debug, probe_testctx,
probe_transparent_mats, probe_collapse, probe_clean_knee, probe_chars

Missing in previz (copy then delete from kit): flat_light_experiment,
render_capsule_poses, s1_probe, pack_v32, patch_v32_[a-e],
patch_street_v32, export_v3_2_deliverables.sh

To placement-lab: probe_physics_api, probe_rb_api, probe_rb_sim,
experiments/ascii_vision/, experiments/physics_facts/

Kit keep (scripts root): agent_server, apply_patch, ascii_read,
ascii_vision, audit_contacts, blrun.sh, calibrate_auto, corpus_synthetic,
encode_deliverable.sh, export_gltf, flicker_probe, framing_audit,
ground_truth_export, keyframe_contact_sheet, macro_runner, physics_place,
placement_lib, polyhaven, render_daemon, save_blend, scene_cornell,
scene_corpus, scene_interior_room, scene_physics_usability, scene_schema,
scene_template, shade experiments → move (project research), test_ascii_vision,
test_mist_off, test_polyhaven, tune_render_quality, validate_scene,
viewport_capture, vision_flow_study → placement-lab, vlm_critique,
scripts/blender_kit/, scripts/ual_test/ (kit-level UAL validation harness)

Open questions for the reviewer: (Q1) does shade_cavity_exp /
shade_experiment_v3 / flat_light_experiment belong in kit as shading
experiments or previz as project research? (my call: previz — they tuned
the escape look; the RESULT — cavity default — already lives in
blender_kit). (Q2) is worklog.md itself kit-scope? (my call: yes — it is
the kit's own history). (Q3) should the kit keep a pointer doc
`docs/PROJECTS.md` listing repos that stress-tested it? (my call: yes,
one short table — provenance without payload).
