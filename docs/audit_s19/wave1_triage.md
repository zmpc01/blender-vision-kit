# audit_s19 wave-1 triage — six fresh-context auditors on tip a3e9a7a

Round 3 of the exhaustion mandate (s17: 88 findings; s18: ~40; s19: below).
Findings deduped by owner wave. Owner: A=orchestrator (core files),
B=tests, C=infra, D=docs+world modules. Status appended on close.

## P1 (6)
- E1 [A] placement_lib.py:438-468,671-685,1912/1998 — stale-depsgraph AABB prefilter: pair_contact/audit_scene/seam_views read matrix_world BEFORE the first depsgraph flush; a [set_location → audit] chain branches on the pre-move pose → moved-into-wall classifies CLEAR → fail_on_penetration FALSE-PASS. Fix: view_layer.update() at entry of the three (F2B-21 precedent).
- E2 [A] apply_patch.py:184-190 — set_rotation writes rotation_euler unconditionally; QUATERNION-mode objects (every glTF import) silently no-op (kit's own prop_carry.py:137 law, s18-C12 twin). Fix: rotation_mode branch / refuse non-EULER with guidance.
- E3 [A] placement_lib.py:792-805 — _guard_anim override token never validated: any junk ≠ None passes and silently selects 'ignore' semantics → override:"rebase" (the docs' own verb) = placement clobbered by keys, ok=True. The rotation guard (808-855) validates — location guard is the fail-open twin. Fix: validate in (None,"keyframe","ignore").
- A1 [A] export_usd.py:143-151 — s18 bind-split catches its own call's TypeError → module re-run (markers/keyframes duplicate) and genuine in-body TypeErrors masked with NO note. Diverged from its own twins (validate_scene.py:428-434, apply_patch._animate_scene_module:1651). Fix: bind in try, call in else. UNPINNED by tests (9a-9f test validate_scene, not export_usd).
- C1 [B-doc] examples/scene_subagent_test.py:219 — raw obj.animation_data.action.fcurves → AttributeError on kit-default Blender 5.2 (slotted actions; gotcha 120). Fix: blender_kit.iter_fcurves.
- B1 [A-film] tfog_bake.py:302,339 — finish stage exports the PROBE (pre-groups) cache: _cache_file(out) reads root while groups bake lands in out/groups_fresh/; the film's S9 cohesion beat silently absent from the deliverable (silent-wrong-content on the GREEN-claimed path). Fix: prefer groups_fresh when groups_pin.txt exists.

## P2 (~17)
- A2 [C] viewport_capture.py:339-351 — light/color_type pre-validation runs AFTER temp-camera creation → bad value leaks temp_*_cam+target (A8 class re-opened on the fix's own path); configure block outside try/finally leaks engine/shading state too. Fix: trial-write before camera section / wrap configure.
- A3 [C] look.py:440-446 — A12 mid-build purge removes OBJECTS only; zero-user KIT_ANNOT_mat_*/curves/meshes residue left on raise path (F2A-4 half-fix). Fix: call annotate.delete_annotation_layer after object sweep.
- A4+E19 [A] apply_patch.py:934 + placement_lib.py:2009 — seam_views fill_frac=0 passes _nonneg_mm → ZeroDivisionError mid-shoot; message mislabels fill_frac as mm. Fix: strict (0,1] bound + own message; route sibling raw writes through _require shape checks (set_camera_location, set_light_color, duplicate transforms, set_frame).
- A5 [A] export_gltf.py:65 — missed bind-split twin (4th call site of the F2B-24 family). Fix: copy _animate_scene_module pattern.
- A6 systemic [B] — s18 fix wave almost entirely UNPINNED (reverting most of 0edf1aa fails no test): _nonneg_mm guards, fstop>0, eevee/cycles snapshot, A12 sweep, shape_keys bake, SSE OSError, chain-abort memory-only, manifest added key. Fix: tests/test_s19_wave_pins.py with per-fix red-by-construction checks.
- A10 [A] manifest_diff.py:63 — docstring drift ("added/removed on only one side" — now excludes rename twins). Fix: reword.
- B2 [A-film] tfog_bake.py:279,295-297 — zero-arrived gate fail-open on missing 'state' channel (states_seen empty → assert never runs → law green on garbage). Fix: assert state is not None.
- B3 [A-film] tfog_contract.py:118,77-81 vs :51 — queue slot i=2 at (0.0,3.3) and DEST_QUEUE capacity sit inside lamp2's blocked square (0.14-pad). No slots∩BLOCKED gate exists. Fix: shift slot row off x=0 + add the two asserts.
- B4 [A-film] tfog_bake.py:191,281 — cohort-id slices [66:117]/[:66] assume cache ordinal == POP_PLAN emission order; no namespace fence. Fix: assert sliced ids carry cohort prefix.
- B5 [A-film] tfog_bake.py:351-359 — bridge call diverges from all four prior drivers: no clamp=True/clip_source="speed", ctx built from .crowd path (prior: npz), keepouts_applied never printed. Fix: restore pinned call shape (verify against crowd-kit sibling once provisioned).
- B6 [D] DESIGN_express.md:60-64 — counts/pin contradict tfog_contract (135/42/18 vs 126/51/9) → F-TS5 loader-pin trap for the next agent. Fix: doc-only update.
- E4 [A] apply_patch.py:175-195 — set_location/set_rotation/set_scale have NO animation guard (C1-class siblings the fix never covered) → hybrid pose silent. Fix: probe anim channels, warn or refuse.
- E5 [A] apply_patch.py:275-303 — duplicate_object copies share the source's ACTION (Blender semantics) → transform params clobbered at next eval. Fix: warn/refuse when keyed + transform params present.
- E6 [A] placement_lib.seam_views:1983-1989 — leaks resolution/engine/color_type/filepath into scene+.blend (A11 class; finally restores camera only). Fix: render_angle-style snapshot/restore.
- E7 [A] seam_views engine param fail-open (only workbench implemented; typos render current engine). Fix: normalize + refuse non-workbench.
- E8 [A] audit sample token falls through silently to 'verts' (apply_patch.py:712 → surface_samples:230 else). Fix: validate in ("verts","verts+edges","bottom").
- E9 [A] place_on(align_to_surface=True) not idempotent — second call rotates AGAIN (absolute premultiply; seat_at IS idempotent). Fix: delta rotation compose + tolerance skip.
- F1 [B] tests/test_t2_stairs.py:159-169 — multi-level TRUE case (the feature's whole point) asserts NOTHING; can regress to always-False green. Fix: add check + z/support expectations.
- F2 [B] tests/test_usd_carrier.py:389-402 — identityColor asserts WARN-gated try/except → can never fail (only color roundtrip assert). Fix: drop try/excepts.
- F3 [C] scripts/suite_runner.sh:51-60 — --label/--timeout/--only/--skip as last arg = infinite loop (verified exit 124). Fix: value guards.
- C2 [D] examples/scene_subagent_test.py:2,10 — docstring teaches nonexistent scripts/scene_test_subagent.py. Fix: correct path.
- C3 [D] AGENTS.md:713 — "this kit ships no crowd code" contradicts crowd_fields.py/gait_modifiers.py (kit's own kb links them). Fix: reword.
- C4 [D] kb/render_speed.md:8 — 240×135 labeled as variant's previz quality (variant is 480×270). Fix: relabel.

## P3 (closing batch)
- A7 [A] _nonneg_mm OverflowError on huge int (apply_patch.py:131). A8 [A] set_camera_dof mutates before validating (:336). A9+E11 [A] heat_bake yellow>=green silently inverts bands + empty others vacuous gray. A11 [C] agent_server sibling handlers BrokenPipe (optional wrap).
- E10 [A] physics frames unvalidated (<=0 → zero-frame verification; NaN raw TypeError) — require >=10. E12 [A] place_on refine slope-correction math dead (clamp always ≥ residual*__corr). E13 [A] add_* self-verify failure leaves lying primitive under requested id (rename before verify). E14 [A] footprint='grid' silently ignores inset. E15 [A] snap_z is the only solver without _skinned_guard. E16 [A] pair_contact silently skips CROSSING beyond 512 pairs — no report flag. E17 [A] audit silently excludes user meshes named Cam*/Temp*. E18 [A] keyframe rebases shift co.y not handle_y (FREE handles corrupt easing). E20 [A] render_viewport engine alias-miss renders current engine (normalize_engine_id unused).
- B7 [D] tfog_world._fog_material returns stale cached density (sibling _dust_material re-applies). B8 [D] departure-board glyph rows invert module's own N/S law (latent). B9 [D] keepout asserts run only in groups stage. B10 [D] tfog_bake dead code (_read_visible_pos, vis0; pins never cross-checked). B11 [D] comment/arithmetic drift (192m/8s vs 240m; f~340 vs 369; express span/head-tail). B12 [D] unrecorded contract deviations (S-face strips, doorway framing). B13 [D] tform yard consts arm the E_InvalidRange trap (columns ON the edge) — fix docstring before tform contract authored. B15 [D] hygiene: tform factory-purge prefix breadth, look drivers hardcode BLENDER_EEVEE, import-time mkdir, dead -0.0, magic 800.0.
- C5 [D] AGENTS.md:216 stale exporter anchor (→1510). C6=F8-s18 [D] AGENTS.md:313 pad cite re-drifted (:611 → :654; symbol-form fix) + PLAN.md:157 (:775 → :1044). C7 [D] AGENTS.md:37 "hasattr" → 'in globals()'.
- D11-pin [B] test_s18_wave_d lacks the D11 fail-closed pin (only fixed item with no pin). F4 [B] test_s18_eyes D9 PENDING hatch dead-but-armed → real assert. F5 [B] t9:309 re-plants the 25mm penetration R5 fixed. F6 [C] E3 exit-2 leaves stale RESULTS.md. F7 [C] SKIP convention loose substring. F8 [B] test_v7 stale-manifest hazard. F9 [B] asciimap near-vacuous check. F10 [B] battery-count drift (SKILL says 29, runner says 26+3, actual 34; test_s17_infra floors at 26).
- B14 [env] film-bake lane unrunnable in sandbox — provision blender-crowd-kit + blender-escape-previz siblings (available at /home/sync/repos).

## Coverage gaps (auditor F — decide owners)
- 10 MUTATIONS ops zero tests: set_rotation, set_scale, set_material_roughness/metallic, set_camera_location/lens, set_light_color, set_world_strength, set_frame, mesh_prepare → param-parity suite in test_s19_wave_pins.
- 10 look flags never exercised; gates 1,2,7,8,9,10,12,13,14 zero direct refs; standalone tools zero-tested: motion_frame_audit, occlusion_gate, axis_gate, image_metrics, keyframe_contact_sheet, export_gltf, polyhaven, crate_stack, audit_contacts.

## Verified-clean highlights (auditors)
- PARAM_DOCS↔handler parity 39/39 (live AST replica); NaN finite-guard family CLOSED on the finite dimension; token validation family nearly complete (gaps: sample/override/engines); parent-space + basis-delta laws correct; channelbag law clean; snapshot/restore pairing sound except the two windows (A2/E6); classifier/float32 guards sound; marker-camera/axial-crane/keepout/sfx/BEATS contracts verified across all six film modules; battery roster 34 rows no dups, all suites independent fail paths.

---
## CLOSE STATUS (appended session-19 wrap)

All P1 + P2 fixed and battery-green (35/35) unless noted. P1s: E1/E2/E3/A1/C1/B1 — all fixed (C1 via wave-D's example fix; B1 via the finish groups-cache fix, re-runnable by the film lane pre-stage). P2s: A2/A3/A4/A5/A6/A10/B2/B3/B4(fence documented — ids are 64-bit hashes, no namespace exists)/B5(bridge defaults verified: matched; call shape now explicit + keepouts_applied counts-ROWS assert)/B6/E4/E5/E6/E7/E8/E9/F1/F2/F3/C2/C3/C4 — fixed. P3s: A7/A8/A9/A11/E10/E11/E12/E13/E15/E16/E17/E18/E19/E20/B7/B8/B10/B11/B13/B15/C5/C6(F8 symbol-cited + PLAN siblings)/C7/D11-pin/F4/F5/F6/F7/F8/F9/F10 — fixed. E14: REFUSED (footprint='grid'+inset raises until the grid branch insets — caught as DROPPED by wave-2). B12: closed by contract-owner note (film lane).

Wave-2 verification (fresh-context agent on the whole s19 diff): wave HOLDS — parity 39/39, E9/E12 math sound, pins honest. Its findings closed same-session: P2 set_location rebase now converts via _world_delta_to_local (the parented case); AXIS_ANGLE duplicate twin; the bare-animate family closed at ALL sites via blender_kit.call_scene_animate (6 raw sites survived the waves).

THE EMISSION-LAW PROBE (smoke/s19_socket_probe.py) resolved wave-2's P1 as REFUTED-with-a-better-law: socket-level keyframe_insert WORKS on 5.2.2 (ret=True) but lands fcurves on the NODE_TREE's own animation_data (5.x node_tree = an ID block; RGBA sockets key 4 channels). The three older films' beats are ALIVE — no re-bake. Durable law: material-node animation reads MUST check BOTH owners (mat + node_tree) — a single-owner read false-negatives (the same class as gotcha 11).

Still-open (honest debts, <P3-class or lane-owned): E12's 0.05m unconditional refine floor on huge flat supports (kb note owed); B5's cosmetic ctx first-arg divergence (traceability-only per the bridge); the un-pinned s19 fixes (A2/A3/A5/A11/E5/E6/E7/E12/E13/E16-E19 + all film/infra rows) — the A6 lesson recurs; wave-D's scene-module purge-prefix finding (scene_squall/green_light/last_ferry share the broad startswith purge — film lane's files).
