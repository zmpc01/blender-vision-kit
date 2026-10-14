# audit_s18 wave-1 triage — six fresh-context auditors on tip ee8034e

Findings deduped. Owner wave in brackets. Status appended on close.

## P0
- A1/B1 [A] manifest_diff.py:~102-137 `really_removed` computed but never stored; `report["removed"]` stays [] → `--expect-clean` false-PASS on unauthorized deletions. Fix: store it + test with a real deletion.
- A2 [A] motion_study.py:~329-343 filmstrip() never `frame_set(f)` → every cell = last pose, labeled per-frame; default-on. Fix: frame_set+view_layer.update in loop.
- A3 [A] keyframe_contact_sheet.py:~177 raw `bpy.ops.render.render` without _marker_camera_sweep → marker-bound shot cams hijack cells on film scenes (F-TD3 sibling). Fix: sweep+restore in finally; also reuse _validate_png.

## P1
- A4 [A] framing_audit.py:47-50,114-121 `_project` discards depth; behind-camera points mirror into NDC → PASS. Fix: rv.z<=0 ⇒ bad.
- B3 [B] physics gate fail_hard sys.exit(2) (BaseException) bypasses --save-blend chain-abort save in apply_patch loop. Fix: catch SystemExit or raise RuntimeError.
- B2 [B] duplicate_object: no existence check → silent .001 rename (kit's own law forbids). Fix: refuse like _add_id.
- B4+C8 [B/C] NaN gate bypass family: seat_at.offset, physics_oracle.target, place_on.clearance/inset/grid_n, audit.contact_band_mm(NaN band false-PASS), render_viewport custom_location/lens. json accepts NaN literals. Fix: _finite_check at handler entry + library-level guards.
- C1 [C] seat_at(align)/place_on(align_to_surface) write ROTATION but _guard_anim/_rebase only handle location → hybrid pose on rotation-keyed objects (tsquall faller class). Fix: extend channel collection + rebase/refuse rotation keys.
- C2 [C] physics_place._prep animated-exclusion checks OBJECT location channels only → rotation-keyed mover simulated then clobbered by its own keys; keyed env frozen static. Fix: iter_all_fcurves all channels + parent chain.
- C3 [C] physics modifiers guard is `if False` stub; allow_bake transforms SHARED datablocks; allow_bake silently ignored in place/oracle. Fix: real guard + data.copy() when users>1 + honor/remove param.
- D2 [D] export_usd.py:91-95 animate() failure swallowed → "animated" USD ships static with exit 0. Fix: re-raise when export_animation (or no fcurves check).
- D1 [D] agent_server.py:325 TCPServer single-thread + SSE infinite loop + live.html connectSSE-first → deadlock. Fix: ThreadingTCPServer.
- E1 [E] test_v3_edges.py D1-D4 "exits cleanly" tautologies (can't fail independently). Fix: real contract (rc/traceback/one-line reason).
- E2 [E] F-TS/s17 coverage: test_ts1_composed_view exists only in sibling repo (doc claims it here); exit-4 path + camera_intent rows + build_sfx vocab: zero in-tree coverage. Fix: new tests + doc pointer note.
- E3 [E] suite_runner.sh: --only matching nothing runs 0 suites, exits 0. Fix: exit 2 when ONLY set and NPASS+NFAIL==0.
- E4 [E] x1_detection_matrix: not in battery; no fail path (exit 0 always). Fix: battery row + verdict exit.
- F1 [F] scene_template.py:162 main() calls animate() unconditionally; doc says "delete it" → NameError on first edit. Fix: hasattr guard (template) or reword doc.
- F2 [F] DESIGN_vision_kit_v1.md:114 + look.py:11 docstring teach `--annotate` (doesn't exist; AGENTS.md warns about exactly this). Fix: [--no-annotate].
- F3 [F] GitLab mirror-branch law drifted across 4 surfaces; push_both.sh pushes `main` (wrong ref, stderr swallowed). Fix: `main:github-canonical` + reconcile SKILL/HANDOFF/.env.example.

## P2
- A5 [A] occlusion_gate.py:109 tuple-lex compare exempts occluder on X<0.01 alone. Fix: all(abs(s)<0.01).
- A6 [A] axis_gate.py:52-56 view_layer.update() only → stale track-to matrix → wrong screen-direction sign. Fix: dep.update() (occlusion_gate law).
- A7 [A] viewport_capture._validate_png no resolution cross-check; border-crop renders pass; keyframe_contact_sheet existence-only check + unvalidated stitch. Fix: PIL dims == requested; reuse _validate_png.
- A8 [A] viewport_capture: temp camera created before try → unknown-engine raise leaks it. Fix: validate engine first or extend try/finally.
- A9 [A] keyframe_contact_sheet step<1 duplicates cells. Fix: dict.fromkeys dedupe + print realized count.
- A10 [A] look.py grid-path camera_intent rows reference temp files (dead refs); probe-only stamps color_source:"viewport" on node-authored mats. Fix: image:"grid.png"+panel field; color_source:null when unsynced.
- A11+B7 [A] render_angle never restores view_transform/exposure/shading/resolution → --save-blend bakes checker config. Fix: snapshot+restore in finally.
- A12 [A] look.py:392-419 sync_display_colors+build_annotation_layer outside try/finally → partial KIT_ANNOT residue on raise (in-memory only). Fix: hoist try start.
- B5 [B] move_to: unknown reference token falls through to bottom-center, report echoes requested. Fix: validate tokens like seat_at/snap_z.
- B6 [B] audit scope id typo → 0 pairs → vacuous PASS of fail_on_penetration. Fix: refuse unknown id.
- B8 [B] scene_schema: camera dof + exposure unexported (write path invisible to read path). Fix: add dof block + schema["exposure"].
- B10 [B] validate_scene.py:419 bare animate(ctx) TypeError twin (F2B-24 pattern). Fix: signature-bind split.
- C4 [C] physics allow_copy: no copy ever swapped; _bake_scales rescales SHARED mesh datablocks scene-wide. Fix: data.copy() when users>1.
- C5 [C] _shape_for env >5000-vert fallback returns BOX unconditionally (origin law violated → displaced collision terrain). Fix: mirror mover branch origin_centered check.
- C6 [C] _skinned_guard: driver-posed/manually-posed armatures read rest-pose. Fix: drivers check + pose-bone matrix compare.
- C7 [C] seat_at: only solver without _skinned_guard/force; post_contact raise leaves scene mutated with no report. Fix: guard + report-preserving raise.
- C9 [C] align_to_surface silently no-ops with footprint='grid' (footprint_pts never filled) while slope_warning advertises it. Fix: fill footprint_pts from pts_xy or use pts_xy.
- D3+B9 [D] filter_rna_kwargs hardwired to usd_export (op_id decorative); glTF call site raw with 4.x-verified kwargs. Fix: generalize to op_id lookup + route gltf.
- D4 [D] USD parity gate: key-presence only; hook NOTE-and-drops rows; FPS/FRAME_START divergence invisible. Fix: per-collection counts compared.
- D5 [D] gate 5 root-existence tautology; CAST root never cross-checked. Fix: reject root_object None for declared cast / resolve via CAST.
- D6 [D] encode_deliverable.sh: no pipefail → ffmpeg failure masked by tail; no post-encode existence abort. Fix: pipefail + checks.
- D7 [D] encode_deliverable.sh calls scripts/mux_dialog.sh which doesn't exist → exit 127 always. Fix: guard + WARN or restore script.
- D8 [D] version-drift gate regex matches only scene_escape_v* (zero today) → structurally vacuous. Fix: film-family match + git_sha compare + --allow-stale.
- D12 [D] _write_metadata claims scene.json; nothing writes it; live.html Scene tab 404s. Fix: write it or drop claim+tab.
- E5 [E] t1-t5/t8/v2/v4 never exit nonzero (runner notes missing for some). Fix: sys.exit(1) tails.
- E6 [E] t8 battery marker uses GNU grep backref (portability). Fix: exact `9/9` marker after E5 fix.
- E7 [E] t9 rounds R1/R2/R5/R6 assert no audit state (docstring table promises). Fix: state-membership predicates.
- E8 [E] test_v1:60 `_check("aim_labels_at no error", True)` vacuous. Fix: assert rotation effect or drop.
- E9 [E] test_usd_carrier pxr-less skip exits 0 without battery marker → false-FAIL row; A2 assert only behind pxr. Fix: exit 2 SKIP + regex fallback assert.
- F4 [F] kb/vision_loop.md:72-74 claims blrun does NOT propagate exit codes (opposite is true, asserted in AGENTS.md). Fix: rewrite bullet.
- F5 [F] look.py:30 + AGENTS.md:90 say exit 0 covers WARN; code exits 3 on WARN (--fail-on-issues default True). Fix: docstrings.
- F6 [F] docs/TUNING_perception_v1.md cited by 5 sites but never committed. Fix: write the doc or repoint citations.
- F7 [F] .env.example GitLab path typo (ans7gareutychisO). Fix: typo.

## P3
- B11 [B] heat_bake others str-iterate; seam_views res str; set_material_color unclamped. Fix: sibling guards.
- B12 [B] split_mesh mode-mismatched params silently ignored. Fix: per-mode extra-key refuse.
- C10 [C] place_on mode token KeyError shape. Fix: validate like footprint.
- C11 [C] contact_discs last_x read before frame_set. Fix: move reads after.
- C12 [C] prop_carry keys rotation_euler unconditionally (QUATERNION props dead-keyed). Fix: key per rotation_mode.
- D9 [D] sfx negative frame: gate 15 + decoder wraparound → mispositioned audio. Fix: reject frame<0.
- D10 [D] agent_server non-atomic artifact serving (watcher fires mid-copy). Fix: size-stable two-poll or temp+replace protocol.
- D11 [D] export_usd no carrier-landed verification. Fix: _usd_customdata_keys non-empty assert.
- E10 [E] t8 audit_verdict reads wrong keys. Fix: state_counts/failed.
- E11 [E] "P1=1" substring matches P1=12 (v1:162, v3:101). Fix: \b regex.
- E12 [E] r9 dead code; r8 header-with-no-checks; s17_wave_a custom_loc assert weak. Fix: polish batch.
- F8 [F] AGENTS.md:309 points at :577 (pad lives at :611). Fix: cite.
- F9 [F] "gnomon at origin" stale in DESIGN:141 + look.py:27 (measured SW offset). Fix: wording.
- F10 [F] look exit-4 documented nowhere in consumer docs. Fix: AGENTS.md exit-code row.

## Verified-clean hunt items (auditors, condensed)
stitching geometry, gnomon chirality math, flag-box projection, unit_scale, image_metrics purity, probe read-only state, exit-code 0/3/4 core paths, closeup math, MUTATIONS↔PARAM_DOCS AST parity, add-op refusals, physics frame/pose restore, matrix composition order, BVH freshness, float32 tolerances, rebase basis-delta law, contact classifiers edge cases, crowd_fields/gait determinism, usd_export 3 sites filtered, preflight fail-closed posture, sfx vocab enforcement, daemonize double-fork, server path traversal, viewer↔metadata parity, polyhaven fail-closed, nested-blrun stragglers (none), run-order dependence (none), verbatim quick-start commands (run green), 39 ops count, 27 v1 checks, 29 battery suites, blrun flag surface, install env vars, F-TD3 code-true, kb cross-refs.
