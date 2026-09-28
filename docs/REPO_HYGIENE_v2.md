# REPO_HYGIENE_v2 — amended after adversarial review round 1

> Supersedes REPO_HYGIENE_v1.md. All 18 amendments from review 14-b
> incorporated; round-2 (14-c) amendments ALSO incorporated (P0: shade files
> absent-in-previz mis-routed; framing_audit.sh is project-wired; mux_dialog
> unclassified; 6 COPY files present-identical; render_daemon 3-line edit
> scope; encode_deliverable.sh → fork-refresh). Routing arithmetic: 31 keep
> + 22 copy + 3 overwrite + 68 delete-only + 5 lab = 129 ✓

## Corrected measured state

| Kit path | Files | Size | Class |
|---|---|---|---|
| `project/` | 1062 | 118 MB | PROJECT → previz |
| `experiments/ascii_vision/` | 347 | 5 MB | R&D → placement-lab |
| `experiments/physics_facts/` | 4 | — | R&D → placement-lab |
| `output/` (tracked) | 10 | 2.4 MB | PROJECT evidence → previz `project/research/ual_ab/` |
| `smoke/` debris | 16 | ~2 MB | DELETE (history retains); keep smoke_render.py + cornell obj/mtl |
| `assets/characters/` | 4 | 5.4 MB | PROJECT (dup in previz ✓ → delete kit copy) |
| `assets/dialog/` | 11 | 1.4 MB | PROJECT (dup in previz ✓ → delete kit copy) |
| `scripts/` root | 129 | — | 93 → previz, 5 → lab, 31 keep |
| `.git` pack | — | 260 MB | history; NOT rewritten (D4) |

Largest blob 3.2 MB (BrainStem.glb) — no GitHub size hazard.

## D1 — Script classification (COMPLETE, review-verified)

### KIT KEEP (31 root files + blender_kit/ + ual_test/)
agent_server.py, apply_patch.py, ascii_read.py, ascii_vision.py,
audit_contacts.py, blrun.sh, calibrate_auto.py, corpus_synthetic.py,
coplanarity_audit.py, flicker_probe.py, framing_audit.py, ground_truth_export.py,
keyframe_contact_sheet.py, physics_place.py, placement_lib.py, polyhaven.py,
render_daemon.py (3-line mover-ref edit: line 11 docstring, line 43 `--scene`
default, line 116 no_physics special-case), save_blend.py, scene_cornell.py,
scene_corpus.py, scene_interior_room.py, scene_physics_usability.py,
scene_schema.py, scene_template.py, test_ascii_vision.py, test_polyhaven.py,
validate_scene.py, viewport_capture.py, vlm_critique.py

### FORK-REFRESH (kit keeps; previz fork gets current copy)
blrun.sh, render_daemon.py (after mover-ref edit), vlm_critique.py,
scene_schema.py, apply_patch.py, encode_deliverable.sh

### COPY to previz, then DELETE from kit (22)
flat_light_experiment.py, render_capsule_poses.py, s1_probe.py, pack_v32.py,
patch_v32_a.py, patch_v32_b.py, patch_v32_c.py, patch_v32_d.py,
patch_v32_e.py, patch_street_v32.py, export_v3_2_deliverables.sh,
test_mist_off.py, probe_shading.py, probe_bg.py, probe_blank_frames.py,
probe_mist.py, probe_transparent_mats.py, s8_probe_v32.py,
test_assets_capsule_actors.py, shot_pipeline.py, shade_cavity_exp.py,
shade_experiment_v3.py

### OVERWRITE in previz (kit copy newer — drifted), then DELETE from kit (3)
scene_escape_v2.py, export_v2_deliverables.sh, gen_dialog.sh

### DELETE-only (byte-identical copy already in previz; 68)
scene_escape.py, scene_escape_v3.py, scene_escape_v3_2.py, escape_lib.py,
crowd_agents.py, assets_capsule_actors.py, assets_characters.py,
assets_humanoids.py, assets_street.py, assets_vehicles.py, axis_truth.py,
bisect_pose.py, color_check.py, dump_f1.py, dump_f1_full.py,
dump_walk_keys.py, isolate_gunner.py, only_driver.py, look_cesiumman.py,
look_legs.py, look_legs2.py, list_bones.py, list_clean.py, make_clean_rig.py,
reskin_cesium.py, zed_macro.py, macro_bed.py, macro_runner.py,
tune_render_quality.py, test_rb_launch.py, derive_axes.py,
inspect_humanoids.py, preview_humanoids.py, pose_module_check.py,
pose_search.py, pose_search_aim.py, pose_search_arms.py, pose_truth2.py,
render_mangled.py, probe_actor_mesh.py, probe_anim_eval.py,
probe_barricade.py, probe_characters.py, probe_clean_knee.py,
probe_collapse.py, probe_eval_order.py, probe_far_zeds.py,
probe_fcurve_eval.py, probe_locs.py, probe_master_actors.py,
probe_master_feet.py, probe_mats.py, probe_rifle2.py, probe_rig_details.py,
probe_run_anim.py, probe_skin.py, probe_skin2.py, probe_slot.py,
probe_testctx.py, probe_rb_sim.py, test_assets_characters.py,
test_assets_humanoids.py, test_assets_street.py, test_assets_vehicles.py,
export_v3_deliverables.sh, mux_dialog.sh, vlm_shots_v2.sh, framing_audit.sh

### COPY to placement-lab, then DELETE from kit (5; sys.path fixed to lib/-relative on arrival)
probe_physics_api.py, probe_rb_api.py, probe_f5_reverdict.py,
probe_t5a_debug.py (imports physics_place + placement_lib), vision_flow_study.py

### Also move: project/ tree, output/ual*/ evidence, experiments/ dirs,
assets/dialog + assets/characters (delete-only), smoke debris (delete-only)

## D2 — Previz completeness (corrected)

1. COPY the 22-file set above
2. OVERWRITE 3 drifted files
3. FORK-REFRESH 6 core files (blrun.sh relocatable; render_daemon.py with
   --start + --chunks; vlm_critique.py; scene_schema.py; apply_patch.py;
   encode_deliverable.sh) — verify blender_kit/__init__.py stays identical
   (currently true)
4. Add 5 missing design docs (README_v2_deliverables, README_v3_2_deliverables,
   DESIGN_v3_color_45s, DESIGN_shot_pipeline, DESIGN_capsule_actors)
5. Add project/research/ tree + output/ual*/ → project/research/ual_ab/
6. Tag deliverable commits: v2.2 = 272f267, v3 = 38ec80b, v3.2 = 72deed5
   (272f267 is the 10/10-frozen v2.2; 4f56398 is the earlier fast-preset
   encode)

## D3 — Prevention

1. `tests/test_kit_scope.py` with the review's forbidden-pattern list
   (zero false positives against all 1627 tracked files — simulated):
   directory rules (^project/ ^experiments/ ^output/ ^smoke/impl_bl_prep/
   ^smoke/.*\.exr$ ^assets/(dialog|characters)/) + name-prefix rules
   (scene_escape, escape_lib, crowd_agents, shot_pipeline, pack_v32,
   patch_v32_, patch_street_v32, assets_, test_assets_, dump_, look_,
   pose_, probe_, shade_) + exact-name rules for the rest. Positive
   controls embedded (synthetic forbidden paths must match; keeper names
   must not).
2. `run.sh --scope-check` mode (plain python3, no Blender needed) + SOP
   commit-checklist step. NOTE: run.sh currently has NO test loop —
   this wires one.
3. .gitignore: add project/, experiments/, assets/dialog/, assets/characters/,
   smoke/impl_bl_prep/, smoke/*.exr
4. AGENTS.md policy paragraph (two-repo contract) at top of file-layout
   section; docs/PROJECTS.md as the single pointer table for provenance.

## D4 — History: accept 260 MB pack (no rewrite; force-push forbidden).
Surface filter-repo option to user in wrap-up. Kit tag `pre-surgery-archive`
placed at the LAST commit preceding the rm commit (i.e. HEAD after step 1
completes) — the tagged tree still contains all project files, so blame
and blob recovery have a named anchor.

## D5 — Execution order (amended: receivers first)

1. Kit: gitignore + scope-guard test + run.sh --scope-check + AGENTS policy +
   docs/PROJECTS.md + doc pointer edits (SOP/AGENTS/PLAN/HANDOFF/SKILL lines
   listed in review) — the gate commits RED (forbidden paths still tracked),
   acceptable because nothing auto-runs it yet; SOP makes it mandatory from
   now on. Commit + push.
2. **Previz first**: copy/overwrite/refresh + research + evidence + docs;
   commit + push. **placement-lab**: 5 scripts + experiments dirs; commit +
   push. (Files now exist in BOTH HEADs — G3 holds at every push boundary.)
3. Kit surgery: git rm all D1 classes; scope guard must pass GREEN now;
   py_compile all kept scripts; Blender still-1 smoke via blrun.sh; commit +
   push; tag pre-surgery-archive BEFORE the rm commit actually (tag the
   pre-surgery state so blame/history is reachable by name).
4. /home/sync refresh both repos + lab.
5. Fresh-clone e2e: clone kit → scope check green, no project/; clone previz
   → py_compile scene_escape_v3_2 + shot_pipeline + dependency smoke
   (render_daemon --start path, encode_deliverable.sh presence);
   1-frame still render from previz repo if time allows.

## D6 — Gates

- G1 scope guard green on kit HEAD (and red on synthetic controls)
- G2 py_compile: all kept scripts; no kept script references a moved module
  (grep scene_escape|escape_lib|crowd_agents|assets_|shot_pipeline etc.)
- G3 exact-path reconciliation: every removed kit path exists at its mapped
  destination (path-mapping table: scripts/X → previz scripts/X or lab
  lib|experiments/X; project/ → previz project/; output/ual*/ → previz
  project/research/ual_ab/; experiments/ → lab experiments/)
- G4 previz buildability: imports resolve; shot_pipeline deps present
  (render_daemon with --start, vlm_critique, encode_deliverable.sh)
- G5 push state: GitHub both repos + lab; /home/sync; tags pushed
- G6 kit still-1 smoke render green post-surgery

## Doc edits landing with the surgery (same commits)

SOP.md:294 (Job 15), SOP.md:365 (Job 17), AGENTS.md:1134 (§39),
AGENTS.md:965 (derive_axes pattern), AGENTS.md:1307 (crowd_agents),
PLAN.md:32/71/429, HANDOFF.md:35, .agents/SKILL.md:438 — each becomes a
one-line pointer to the previz/lab repo + docs/PROJECTS.md.
