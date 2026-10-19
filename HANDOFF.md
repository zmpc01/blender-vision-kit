> Session 24 close: 2026-10-19. HEAD = the SYNC + VISION-LANE +
> round (the user directive: mainline sync on 3d-asset/animation/crowd-
> nav + native-vision refinements + previz ports + the audit waves).
> The s41 crowd_obstacles bridge + scripts.crowd re-export landed here
> (the film lane's vendor was rh_canvas-only); the crowd-nav vision
> lane (crowd_look.py) was designed through two critique rounds,
> implemented, eye-certified; ab_evaluate landed in its native-vision
> form; the dog-food round found 4 blockers (all dead); AUDIT-A2
> hardened the loader/wrapper/lab. Battery 42/42. This block -> the
> session-23 block -> PLAN M15/M16 -> worklog (session-24 record).

## Session-24 close state (NEWEST — read this first)

- **Credential matrix (re-verified empirically this session)**: vision-
  kit = zmpc01/blender-vision-kit (OLD2 PAT writes zmpc01; the NEW
  beulahkemp PAT reads/writes the RH repos). The s23 summary's
  "beulahkemp/blender-vision-kit" claim was WRONG — probe before you
  clone. Both PATs live in /home/z/creds/gh.env; push helper
  /home/z/creds/push_vk.sh.
- **The battery runner exists again** (scripts/run_battery.sh): two
  invocation contracts — bpy suites via blrun, bpy-less vendored
  unittest via host python3 (test_hero_gates through blrun dies on
  unittest.main consuming blrun's flags). 42 suites at close.
- **The s41 sync**: crowd_obstacles.py + scripts/crowd/ (the 24-name
  re-export after the s24 +4) + their batteries + docs/crowd_system/
  STATUS.md — ZERO code drift except the documented sanctioned deltas
  (--blend/--json-out on the scan CLI; the +4 authoring names; O8a's
  24 pin). VK's submodule pin b4bf76e is 467 commits AHEAD of
  mainline's bc11fcb (1.6.0 wheel) — superset verified live.
- **crowd_look.py (the crowd-nav vision lane)**: the design doc
  carries the full critique trail (F1-F18 + N1-N6); the module's
  header maps every law to its decision ID. The measured render laws
  (anti-alias, self-occlusion, scale-aware bevel, hue-band matching)
  are in kb/crowd_look.md. The L10 row CROSS-CHECKS the O11c jam pin
  on real bake bytes. The N4 ghost rule + origin_junk_frac diagnostic
  answer the "why is the centroid at origin" question.
- **The U1 dog-food law**: a docs-only consumer simulation caught 4
  blockers no code audit saw (argparse vs blender argv; a CLI that
  could never see a scene; an undiscoverable answers schema; an
  ImportError in the vendored guide's own snippet). LAW: run a
  docs-only consumer wave on EVERY new CLI surface before close —
  audits read code, consumers read docs.
- **AUDIT-A2's deepest find**: the LAB's hero world gates were
  computed, printed, and stored — never enforced (the s23 fail-open
  class, third occurrence: retarget gates, then nothing, now the
  lab). LAW: a gate the caller must remember to assert is a gate
  that won't be. The fold: _assert_hero_bands raises with measured
  numbers; the verdict lands in world_table + metadata.
- **The slot law's measured form**: slotless-over-LIVE-binding
  refuses; a FRESH binding of a slotless action is the legitimate
  bake shape (the strict form over-fired on the real hero path —
  the s23 connected-location lesson repeating: fold audit findings
  WITH judgment).
- **Open queues for the next session**:
  1. THE USER REVIEW ROUND on the seven staged films — still the
     lane-level open item (the reviewer-comments protocol +
     schema are now IN the kit: docs/REVIEW_COMMENTS_PROTOCOL.md).
  2. Upstream nits (mainline-owned, tiny): the vendored guide's
     syntax errors (walkables=all] x2) + false archetype defaults
     + the 24-name re-export contract (VK carries sanctioned
     deltas; mainline's scripts.crowd still pins 20) + the ual
     slotless-over-live law (mainline's _assign_action lacks the
     zero-slots refusal). File as one upstream commit when the
     lane next pushes upstream.
  3. The blind-leak note (ab_evaluate): the worksheet records
     a_left per pair and the readability stills carry side labels
     in filenames — the blind is partial for a native agent that
     reads filenames; a hash-named redesign is queued (low
     priority: the swap law already debiases the preference).
  4. P2-7 (carried, documented in DESIGN §7): _assign_action pins
     slots[0] — revisit when a multi-slot source arrives.
  5. D9 catalog contact sheet (rh_canvas previews -> labeled
     grids): DEFERRED by critique concurrence; the design row
     exists in DESIGN_crowd_vision_s24.md.
  6. origin_junk_frac > 0 on a real bake = investigate the
     engine's near-zero writes (the N4 rule's blind spot).
  7. THE GITLAB MIRROR DIVERGED for real: github-canonical's tip
     (f546837) is the PRE-rewrite s17 lineage — the same content as
     local 5c39b86 under a different hash (the s16 push-protection
     history rewrite split the lineages; main:github-canonical now
     rejects non-fast-forward). The s24 archive lives on the branch
     github-canonical-s24 (the SKILL s21 per-round-archive law).
     Next sessions: push main:github-canonical-s<N>; do NOT force
     github-canonical; the raw lineage there is a provenance record.

# HANDOFF.md — blender-vision-kit (immediate next-session scope)

> Session 23 close: 2026-10-18. HEAD = the AUDIT-EVERYTHING round:
> the s22 AUDIT-A finally ran (scoped) and its gate-layer P1s are
> ENFORCED (the retarget docstring's fail-closed claim is now
> load-bearing); the s22 port-back booking was CLOSED BY UPSTREAM
> (mainline s41 landed a superset migration design — vendored here by
> the film lane mid-session); the post-vendor validation caught the
> VACUOUS-SCORE class live (ALL PASS with a [FAIL] on the wire) in
> both RH suites + two determinism landmines, all fixed; the residual
> port-back (the same test fixes + a docstring drift) LANDED UPSTREAM
> (agent-kit 17e3ef1) — mainline now truly 16/16 against the live
> clones. Battery 40/40 0 SKIP. This block -> the session-22 block ->
> PLAN Track TF -> worklog (session-23 record).

## Session-23 close state (NEWEST — read this first)

- **AUDIT-A verdict + fold (43f6d24)**: the retarget MATH is sound
  (conjugate-basis rotation + parent-cancellation independently
  re-derived and numpy-probed exact to 1e-9; slot discipline, frame
  freshness, unpack ordering all cleared). The GATE layer was
  fail-open: drives_ok/teleport_ok computed but never enforced; no
  source anti-frozen defense; location channels never drive-checked.
  ALL ENFORCED NOW: gates raise inside retarget(); the source
  data-vs-evaluated span check refuses the stuck-source rest-bake
  (static actions stay legal); the drive check covers locations.
- **THE CONNECTED-LOCATION LAW (as measured — the auditor's strict
  form was wrong)**: a location fcurve cannot drive a use_connect
  bone in ANY rig, and the same-class channel is an equally dead
  no-op in the SOURCE (the UAL walk replays gait from rotations
  alone). Law: SKIP + report (rep loc_no_op), NEVER refuse — the
  refusal form fired on the real hero path and would have broken a
  working bake over a channel carrying zero information.
- **THE VACUOUS-SCORE CLASS (the round's headline catch)**: a suite
  row() that scores only EXCEPTIONS prints ALL PASS with [FAIL]
  checks on the wire — caught LIVE on the vendored R10b row, and
  REPRODUCED ON MAINLINE (the same lie). Law: row scoring fails on
  check-level failures (the test_hero_lane delta pattern — n0 =
  len(FAIL) before, compare after); suites predating the pattern are
  landmines. Fixed in test_rh_canvas + test_rh_fixture, ported
  upstream.
- **Determinism preconditions must be SELF-GUARANTEED**: R10b relied
  on a fresh sandbox (R10's stub action collided -> Layer0.001 vs an
  exact-name expectation — row-ORDER dependent); R9g2 relied on a
  never-run cache path (warm from a previous RUN -> ok-cached).
  Factory-reset / purge INSIDE the row; "passed in a fresh sandbox"
  is not a result.
- **The upstream-tip law re-proven the hard way**: the s22
  "port-back queued" booking was ALREADY obsolete when this session
  started (upstream s41 aa05cf3 landed the migration fix as a
  superset; the film lane vendored it into this tree mid-session).
  Re-read origin/main after EVERY rebase; re-verify any booking
  against the current tip before working it.
- **Submodule pin hygiene (2c99697)**: the recorded gitlink pin
  (r149) was STALE vs what s22 actually tested (working tree at
  r151+, wheel 1.6.0) — a faithful re-land reproduced the drift as
  a crowd_e2e version-coherence FAIL. Pin bumped to b4bf76e. LAW:
  bump the pin at WRAP time, not re-land time.
- **The RH repos remain PRIVATE** (anonymous ls-remote fails —
  verified this session; my first ledger claim said public, it was
  WRONG and is corrected). PATs: OLD2 writes zmpc01, the beulahkemp
  PAT reads the RH repos; both in /home/z/creds/gh.env (recreate
  from this file if wiped); push helper /home/z/creds/push_vk.sh.
- **Open queues for the next session**:
  1. THE USER REVIEW ROUND now spans SEVEN packages (tform_2
     humanoid on top) — still THE lane-level open item.
  2. AUDIT-A2: the retarget MODULE is hardened; the loader
     (rig_family_quaternius) + wrapper_rig + the lab hero zone got
     lighter coverage (context files in A1) — a scoped wave each.
  3. P2-7 (deferred, documented in DESIGN §7): _assign_action pins
     slots[0] — structurally unpinned for a fresh action pre-write,
     wrong for multi-slot actions; every real path is
     fresh-single-slot today; revisit when a multi-slot source
     arrives.
  4. Upstream residual (all tiny, non-blocking): none open — the
     docstring drift + test fixes landed (17e3ef1); the PRIVATE
     note is correct as written.
  5. Film-lane queues (NOT this lane's scope): collision/navigation
     rollout, the night-market film, the humanoid rollout to the
     other five films.


> Session 22 close: 2026-10-18. HEAD = the RH REAL-DATA round: the
> asset ecosystem RETURNED (beulahkemp/RH-canvas-animations +
> RH-canvas-characters + RH-3d-assets; CDN live), the library-split
> discovery fix landed + verified against the real repos, the fixture
> library got CROSS-VALIDATED against reality (9 laws, 0 unexpected),
> and the s21-D hero lane COMPLETED (wrapper/loader/retarget/lab,
> battery row 40). This block -> the session-21 block -> PLAN Track TF.

## Session-22 close state (NEWEST — read this first)

- **The RH data layer is LIVE at both ends**: test_rh_canvas runs
  14/14 rows against the REAL clones (2,032 id-deduped clips / 19
  categories / 667 characters / 99 models — census exact; real glTF
  statue import + real CDN FBX fetch sha-verified), and the offline
  fixture library is cross-validated against that reality
  (docs/RH_CROSSVAL_s22.md; battery row 39 fail-closes on any NEW
  deviation). The s20 "single point of failure" is retired twice over.
- **Credentials** (the session's discovery): the beulahkemp PAT
  (ghp_vRRs...) is READ-ONLY on zmpc01 repos and WRITE on beulahkemp
  repos; the OLD PAT (ghp_twrZ...) still writes zmpc01. Both live in
  /home/z/creds/gh.env; /home/z/creds/push_vk.sh is the vision-kit
  push helper (fetch+rebase+push with the OLD pat). Release-asset
  downloads: the API assets endpoint with Accept: octet-stream (the
  browser_download_url 404s under fine-grained PATs).
- **The sandbox bans symlinks** — tools/blender must be the REAL
  renamed install dir (blrun wants tools/blender/blender AND the FBX
  addon resolves tools/blender/5.2/...). The re-land drill: copy
  /home/sync/blender-vision-kit/tools/blender-5.2.2-linux-x64 ->
  tools/blender (foreground; background cp gets reaped), Pillow +
  crowd-kit wheel BOTH pythons, submodule via the API tarball.
- **The hero lane is complete**: scripts/wrapper_rig.py is the FILM
  LANE'S canonical (converged after an add/add collision — do not
  re-fragment it); this lane owns scripts/rig_family_quaternius.py
  (the D2 loader, UNIT_RESCALE 0.3718), scripts/rig_retarget.py (the
  D3 engine + the REV-3 law changes in DESIGN_s21_hero_lane.md §6),
  and the motion lab hero zone. test_hero_lane 6/6 (battery row 40).
- **Cross-lane protocol that worked**: the parallel film lane landed
  its own humanoid layer mid-session (b0e6450..aedf269); zero file
  overlap except wrapper_rig.py — resolved by taking THEIRS as
  canonical (upstream-first, their humanoid_crowd depends on it) and
  porting my consumers; my battery found a REAL defect in their T4
  check (the master-collection gap) — folded inline with the finding
  documented in the code.
- **THE HUMANOID FILM IS LIVE (the film lane's close, this lane's
  convergence consumer)**: tform_2 "THE DRILL (humanized)" is STAGED
  in previz-review and serves FIRST (12 shots / 12 cams / 2 UAL
  characters / 153 actions / **104 skins** / 29MB GLB / 96 strips /
  12 Cycles stills — 12/12 eye-certified). The web viewer plays the
  skinned crowd (three.js r186 bone textures — the RQ3 perf worry
  retired empirically). The film's laws (all measured, in the code):
  the PER-GROUP MESH DATA tint law (the glTF exporter resolves
  materials from mesh DATA slots — object-level links render in
  Cycles but export raw; the unique-data-per-group trap: Object.copy
  SHARES data, 5 clearing passes left one group's material on all
  102), the DEGENERATE CARRIER law (hide_render excludes objects
  from the GLB and fails gates 17/24 — swap the anchor's data to a
  1-vert no-face mesh instead: invisible in render, present in the
  GLB), the CYCLES ENGINE LAW (102 skinned agents OOM EEVEE even on
  the diet — Cycles streams it; wired in _set_engine CPU+denoise).
- **Open queues for the next session**:
  0. THE USER REVIEW ROUND now spans SEVEN packages (tform_2
     humanoid on top; the 6 older films unchanged). The humanoid
     rollout to the other five films = flip TFORM_HUMANOID-equivalents
     per film (the layer is kit-level: humanoid_crowd.bind_crowd).
  1. AUDIT-A (the retarget-engine attack audit) timed out this
     session — re-run it against scripts/rig_retarget.py (the REV-3
     law changes + the samples-loop D_t reuse are the surfaces; the
     drive-check + world gates cover the freeze class meanwhile).
  2. Port-back to mainline: the rh_canvas library-split discovery
     (VENDOR_LEDGER carries the sanctioned-delta note; mainline's
     two-repo predicates are broken against the live repos TODAY).
  3. The COLLISION/NAVIGATION ask (the user's next frontier): the
     sim's obstacle model is crowd-kit's (environment.py Blocked
     squares + the camera keepouts are SEPARATE); the films' statics
     (colonnade walls, market stalls) are declared per-film. Split:
     film-lane contract gaps -> declare more obstacles per film;
     missing obstacle TYPES (cylinders/segments) -> upstream request.
     Then the night-market film (stall obstacles + the humanoid
     crowd are the natural proof).
  4. The QUIET anti-regression: test_rh_crossval + test_hero_lane
     need their honest-skip paths exercised in a library-less sandbox
     (they were born green with libraries present).

> Session 21 close: 2026-10-16. HEAD = the RESUME round: the wiped
> sandbox re-bootstrapped from remotes (the drill now ~20 min), the
> tform_1 re-land completed end-to-end (bake chain byte-deterministic
> at 9024057c, 12 stills eye-certified, EXPORT GREEN, staged — the
> sixth film lives), and the film-lane export compliance landed
> UPSTREAM (agent-kit 2fa345e). This block → the session-20 block →
> PLAN Track TF → worklog (session-21 record).

## Session-21 close state (NEWEST — read this first)

- **tform_1 rev 1 (THE DRILL) is STAGED** in previz-review (844ed3a)
  and the app serves it first (newest-first): 12 shots / 12 cams / 2
  characters / 110 actions / 1 atmosphere, 96 filmstrips + 12 stills
  + GLB 15MB. The bake chain re-proven BYTE-DETERMINISTIC from a
  wiped sandbox (payload 9024057c == the 5fa907b record; probe pin
  c8be30ba, officers a@t355 b@t329 — every stage receipt matched the
  commit record exactly). K1 composed-motion is live on the film.
- **The upstream fixes (agent-kit 2fa345e)**: (1) _collect_atmosphere
  VOLUME_SCATTER fallback (the tfog-era fix that died with its
  sandbox — check the CANONICAL exporter's tip BEFORE assuming a
  film-lane fix exists); (2) scene_contract.KNOWN_NON_STORY += the
  8 film-lane family names (SHOTS_V1/CAMS_V1/CACHE_DIR_DEFAULT/
  CHASE_TAIL/EXPECTED_AGENTS/DECLARED_TOTAL/TICK_HZ/TOTAL_FRAMES),
  each with a documented destination per the s32 D6 law. The
  film-SPECIFIC knobs are lowercased IN-MODULE (tform_scene is the
  worked example: KEEPOUTS→keepouts + TFORM_*→tform_*).
- **New laws this round** (SKILL carries the condensed forms):
  5.2 engine enum is BLENDER_EEVEE (NEXT is 4.x — never version-guess
  in a scene module); the wrapper's r084#9 identity marker refuses
  non-canonical exporters (KIT_EXPORTER = agent-kit's); Blender's
  render.filepath ext is REPLACED by the format's canonical ext;
  daemonize.py needs an ABSOLUTE log path; bare `npx prisma db push`
  in previz-review runs against the WRONG db — use the repo's own
  db:push contract (file:$PWD/db/custom.db).
- **GitLab posture**: vision-kit's github-canonical is non-FF by
  lineage law; the round's archive branch is github-canonical-s21
  (kept FF-current); github-canonical-s20 exists from another lane
  (b4be13cf — not ours, do not touch). agent-kit + previz-review
  mirror FF to github-canonical. The repos now exceed a 10-min
  tool-call rsync — /home/sync is done REPO-BY-REPO.
- **Open queues for the next session**:
  1. THE USER REVIEW ROUND on all six films (0 comments on the
     films — the whole lane points here; the four older films at 0
     since their close, tdawn_2/v6_0/v6_1 carry the historical
     comment threads).
  2. The diversity queue rest: interior/night-market (the regime not
     yet covered) — the SQUALL build order recipe applies as-is.
  3. Filed debt: the other five film modules fail the s32 discovery
     at their NEXT exports — apply the tform treatment only when an
     export round reopens each film (generic names → upstream
     exemptions if the vocabulary repeats; film knobs → lowercase).
  4. The s21 lane (parallel, separate): the UAL hero-swap leg + the
     rh_canvas s40 preview-data surface are NOT this lane's scope.

> Session 20 close: 2026-10-16. HEAD = the RH INTEGRATION lane complete:
> the 2k-animation + humanoid-model integration vendored from mainline
> s38/s39, an OFFLINE fixture library (the data source went dark),
> test_rh_fixture 13/13, the scene_motion_lab dog-food (7 clips + 2
> statues, strips eye-certified WITH numeric gates), four sub-agent
> audit/usability waves folded, battery 38/38. This block → the
> session-19 block → docs/rh_canvas.md (s20 amendments) + worklog.

## Session-20 close state (NEWEST — read this first)

- **What landed**: rh_canvas.py + test_rh_canvas.py + docs/rh_canvas.md
  vendored verbatim from mainline (b7c675d..6943ab5 lineage; sanctioned
  deltas only: UA/provenance/data-driven tags+frames/--tag/--max-frames);
  the placement_lib ARMATURE graft with the _ARMATURE_QUADS shared face
  table (index-aligned BVH); scripts/rh_fixture_lib.py + _fixture_fbx_patch.py
  (the offline fixture library: 8 contract-conformant Mixamo-family clips
  + 3 statues + catalogs, self-verifying truth.json); tests/test_rh_fixture.py
  (13 rows, ALL PASS); scripts/scene_motion_lab.py (the dog-food scene).
- **THE DATA SOURCE IS DEAD**: beulahkemp/RH-canvas-animations +
  RH-canvas-characters 404 (verified 2026-10-16; no forks, no wayback,
  no mirrors). The fixture library is the RH path's data layer now.
  ALSO: this round's GH PAT fails GIT auth on the sibling repos (API 200
  + git "Invalid username or token" = fine-grained-token signature) —
  provision repo trees via the API tarball endpoint
  (api.github.com/repos/<r>/tarball/<ref>) until PAT scopes are fixed.
- **THE SESSION'S LESSON (read before any motion work)**: pose-bone
  LOCATION is bone-local; vertical root motion on local Z = sideways
  hops; the per-actor-follow camera masked it and the principal
  eye-certified an illusion. Two numeric probes caught it. Every
  eye-certified motion claim needs world-space numeric corroboration.
  The generator now gates animated behavior (frame-evaluated world-z)
  fail-closed.
- **Fresh-sandbox bootstrap for this repo** (what worked):
  1. bash /home/z/my-project/scripts/setup_s20.sh (PAT sweep + clone —
     write tokens into FILE contents, never inline shell)
  2. Blender: bash /home/z/my-project/scripts/setup_s20_blender.sh
     (foreground chunked DL + tools/blender symlink — background gets
     reaped; BLENDER_BIN alone skips the symlink the battery needs)
  3. Pillow into the BUNDLED python + host python3 (strips + the PY rows)
  4. crowd-kit submodule: API tarball into vendor/blender-crowd-kit
     (git auth fails under this PAT) + pip the 1.6.0 wheel BOTH sides
     (bundled + host — test_crowd_e2e is mode PY)
  5. fixture library: ./scripts/blrun.sh --background --python
     scripts/rh_fixture_lib.py -- (idempotent; --force to rebuild)
  6. battery: suite_runner --only batches (38 suites, foreground)
- **GitLab archive branch github-canonical-s20**: the WAF 403'd EVERY
  push this session (8 retries per push, ~8 pushes). FIRST CHORE next
  session: `git push gitlab main:github-canonical-s20` (never force).
- **Open queues for the next session**:
  1. The UAL hero-swap leg (the "some more humanoid rigged models" ask):
     assets_ual_actors.py + the vendored UAL 46-action library + the
     Quaternius Male/Female_Casual.fbx (in previz research/_rig/) — the
     any-rig boundary (channel-match refusals → the retarget recipe) is
     untested ground; the kb says "hero swap is its own session".
  2. The wrapper-empty facing pattern for animated actors (F-RH3) —
     land it as a placement_lib/rh_canvas helper + lab integration.
  3. Upstream-booking: the rh_canvas s20 deltas (data-driven tags/
     frames, --tag/--max-frames) + the placement_lib vs-guard fix belong
     in mainline's ledger (docs/FINDINGS_upstream.md pattern).
  4. GitLab archive retry (above) + the next /home/sync bundle.


> Session 19 close: 2026-10-15. HEAD = the THIRD audit-exhaustion round
> (six fresh auditors + fix waves A–D + wave-2 verification, battery
> 35/35) + the principal's NATIVE-VISION e2e probes. This block → the
> session-18 gap note → the session-17b block below → docs/audit_s19/
> wave1_triage.md (with close statuses) + docs/audit_s18/wave1_triage.md
> + .agents/SKILL.md (SESSION 19 LAWS).

## Session-19 close state (NEWEST — read this first)

- **The exhaustion mandate is met at tip 84cd8d3**: wave-1 (six
  fresh-context auditors) → 6×P1 + ~17×P2 + ~30×P3; ALL ≥P2 fixed with
  the battery green (35 suites — the pin suite registered). Wave-2
  (adversarial verifier on the whole s19 diff) ruled the wave HOLDS;
  its findings (a P2 rebase-delta bug, missed twins, 6 more raw
  animate sites, the E14 drop) were closed SAME-SESSION. Honest debts
  (<P3 / lane-owned) are listed in the triage's CLOSE STATUS block.
- **The headline fixes**: E1 stale-depsgraph audit false-PASS
  ([set_location→audit] chains branched on the PRE-move pose);
  E2/E4 set_rotation/set_* write the mode's real channel + animation
  guards (the glTF silent-no-op class); E3 override-token validation;
  B1 tfog finish exported the PROBE cache (the S9 cohesion beat was
  absent from the deliverable — FILM LANE: re-run finish before
  staging); B3 queue slots off lamp2; E9 place_on align idempotence;
  E12 refine dead-math revived; test_s19_wave_pins (the s18 fixes were
  UNPINNED — reverting them failed no tests; now ~20 pins).
- **The bare-animate family is CLOSED at every site** via
  `blender_kit.call_scene_animate` (bind in try / bare fallback / the
  real call OUTSIDE the bind try — an in-body TypeError must
  propagate). Nine call sites total now use it or an equivalent
  bind-split.
- **THE 5.x NODE_OWNER LAW (the round's biggest trap resolved)**:
  material-node keyframe_insert WORKS on 5.2.2 but lands fcurves on
  the NODE_TREE's own animation_data (node_tree = an ID block; RGBA
  sockets key 4 channels). A mat-only fcurve check false-negatives —
  ALWAYS read BOTH owners (mat + node_tree). Receipt:
  smoke/s19_socket_probe.py (the film lane's "socket-level no-op"
  claim REFUTED — the three older films' emission beats are ALIVE, no
  re-bake; their landed dual-owner assert is the correct pattern).
- **The native-vision e2e lane worked**: smoke/s19_td3_probe.py (the
  F-TD3 sweep eye-verified: no panel hijack + camera_intent rows name
  the would-be hijacker) and smoke/s19_motion_probe.py (the A2
  filmstrip fix eye-verified: six cells, six distinct poses). The eye
  probes found look.py's bare-animate crash — the 5th family site —
  that BOTH audit rounds missed. KEEP this pattern: sub-agents audit
  code; the principal renders and LOOKS.
- **Fresh-sandbox traps hit this session**: install.sh's BLENDER_BIN
  override skips the `tools/blender` symlink the battery's blrun needs
  (ln -sfn the extracted dir); Edit+Bash in one parallel block races
  the file to disk (twice — serialize them); display-mangle survives
  even repr() — ast.parse is the only truth, and parse BEFORE every
  commit (one real assert-continuation syntax error survived to a
  commit because the parse check was skipped).
- **The film lane** (parallel, same repo): tfog scene module GREEN +
  flow strip GREEN (3bd04ec, 73f6633 — absorbed by rebase, zero
  force). Their new probe laws: nulled markers STILL flip scene.camera
  at frame_set (DELETE+recreate is the only safe probe path);
  scene.collection.objects is direct-members-only; workbench renders
  fog-volume surfaces opaque from above. Next for them: rebase onto
  the s19 tip, re-run tfog finish (the B1 fix), stage exports.
- **Open queues for the next session**: the un-pinned s19 fixes (the
  A6 lesson recurs — see the triage's close-status list); wave-D's
  scene-module purge-prefix finding (scene_squall/green_light/
  last_ferry broad startswith purge — film lane's files); E12's 0.05m
  refine-floor kb note; the film lane's K1 composed-motion fix
  (crowd-kit) + tform build.

## Session-18 state (the gap — folded into the s19 wrap)

The s18 session ended after its wave-3 (0edf1aa) + the tfog chain
green WITHOUT a close ceremony: no HANDOFF block, no PLAN receipts, no
worklog close, no final bundle. Its audit round: docs/audit_s18/
wave1_triage.md (six auditors on ee8034e; wave-3 commit = the close
record). Its P3 list was verified 13/14 ALREADY-CLOSED by the s19
round (only F8 had re-drifted). The s19 wrap documents both sessions.

## Session-17b close state (read second)

- **FOUR films live in previz-review** (comments ON, the server UP
  via daemonize): **tsquall_1 rev 2** (SQUALL — storm-dusk market:
  the shelter convergence, the slip-and-fall, the window queue, the
  neon title; 135 agents, the M6 queue/portal/HoldPosition + the M5
  ragdoll beat + groups + the events→sfx spine), **tgreen_1 rev 2**,
  **tferry_1 rev 2**, **tdawn_3**. THE OPEN ITEM: the user review
  round on all four.
- **The kit wave landed this session**: F-TS1 (the bridge composes
  kit layout layers into the film VIEW + real z — the ragdoll beat's
  enabler; r054 72/72 + test_ts1_composed_view 13/13), F-TS2 (the
  chase_frame="belt" pins in all four drivers — the r109 flip trap),
  F-TS5 (the loader expected_agents override), the F-TS6 paired
  tripwire fix (the layout_composed marker + the composed-aware
  ground-contact gate), the SQUALL sfx vocabulary (12 patches in
  build_sfx). Filings: F-TS3 (the portal-axis naming trap), F-TS4
  (the emission-interval hijack). Full ledger:
  docs/USABILITY_TS1_squall.md.
- **The SQUALL build order worked; reuse it** (the green-light recipe
  + the deltas): research wave → design + 2 audit rounds (4-d/4-e/4-f
  caught 4 P0s pre-code: the portal axis, the flee-is-cosmetic law,
  the interval hijack, the loader pin) → world module (sub-agent) →
  F-TS1/F-TS5 BEFORE the driver → contract → the 3-stage probe/
  groups/finish bake (3-4s bakes!) → flow strip (the --hide-roof
  flag for canopied sets) → the camprobe framing rounds → the
  storm-dusk ladder → 12 EEVEE stills (eye gate) → preflight →
  export → stage.
- **The bootstrap**: clone 5 repos → verify BOTH PATs → install.sh →
  the venv wheel (1.5.5) → the server (daemonize + the repo-local
  db + s33_restore_comments.sh). Blender 5.2.2 one-shot again.
- **Next-session scope**: (1) the USER review round on all four
  films (the whole session points here); (2) if the user prompts a
  fifth scenario, the candidate regimes: fog, blue hour, interior/
  night market — the DESIGN_squall §2 ledger lists the honest-scope
  files (SPEED/GOAL/DISABLE layers are VIEW-invisible; the escape-
  lane tripwire now exempts composed rows); (3) the standing chores:
  F-TD3 is CLOSED (the s17 lane), F-TS3/F-TS4 are filed (kb-level
  documentation in the crowd-kit lane's FEATURE_REFERENCE when that
  lane resumes).
- **The remotes posture**: GitHub canonical (main); GitLab mirrors
  the clean lineage as github-canonical (per-session archive branches
  github-canonical-sNN when non-FF; the raw pre-redaction main stays
  GitLab-only — the push-protection protocol from session 16; do NOT
  merge the two lineages).
- Laws distilled: .agents/SKILL.md SESSION 17b LAWS (29.9k/30k cap).


## Session-16 close state (the KIT-QUALITY wave — pre-session-17 baseline)

- **⚠ THE GITHUB PAT IS DEAD (401 Bad credentials)** — verified at
  session start; reads still work (public repo, anonymous) but PUSHES
  fail. **GitLab carried the session** (oauth2 PAT alive, WAF-retry
  discipline). USER ACTION NEEDED: a fresh GitHub PAT, then
  `git push origin main` from any clone to reconcile GitHub (GitLab has
  everything through session-16; GitHub is stuck at e64528f). Verify
  BOTH PATs at session start (2-line curl check) before planning pushes.
- **Lane discipline**: the parallel lane owns SCENE work (tdawn/tferry
  modules, the review app, staging). This session touched ONLY kit
  files — do not co-edit scene_*.py.
- **D19 shipped — the export lane finally has regression coverage**:
  (1) run `blrun.sh --background --python scripts/export_preflight.py --
  --module scripts/<scene>.py` BEFORE any export (exit 3 = attributed
  rejection; contract failures now surface pre-render); (2) exporter
  gate 15 fail-closes malformed sfx streams (the F-TF4 class can never
  export green again) and gate 4 rejects a BOARD that decodes to zero
  entries; (3) t10 = test_t10_preflight_prop.py (100 checks, pure
  python, 0.2 s, BOTH-direction drift property vs the REAL decoder) +
  test_t10_export.py (19 checks, ~8 s, subprocess; fixture written into
  scripts/ — a temp dir is UNREACHABLE by the exporter's name-import).
- **Battery 26/26** (output/battery_s16/RESULTS.md). Three kit fixes it
  forced: usd_export kwargs are RNA-FILTERED at runtime (the 4.5-calibrated
  set TypeErrors on 5.2.2); the four nested-blrun suites carry
  BLRUN_FORCE=1 (the F-TD10 flock had broken their documented mode);
  probe files live under smoke/, never scripts/.
- **Wave A kit fixes** (test_v9 8/8): F-TD5 ported to THIS tree (the
  hidden-sweep updates the view layer itself), scoped audits honor the
  state enum + contact band, F19 ack_many_parts gate, F20-R6 occluded-
  support hint, install.sh authoritative Pillow probe + symlink heal,
  F-TF5 wheel re-vendor 1.5.5.
- **Bootstrap that works (fresh sandbox, verified this session)**: clone
  (GitLab if GitHub auth is still dead) → `bash install.sh` (Blender
  5.2.2 + Pillow resolved authoritatively) → suites via
  `./scripts/blrun.sh --background --python tests/<suite>`. Crowd wheel:
  vendor/blender-crowd/.../wheels/1.5.5 (provenance README in-tree).
- **Next-session scope**: (1) the user review round on tdawn_3 +
  tferry_1 (the app lane — parallel lane's); (2) F-TD3 marker-hijack
  fix in viewport_capture (design first — the last silent-wrong-render
  class in the core eye); (3) port the preflight to the canonical
  agent-kit exporter via tools/sync_shared.py governed sync; (4) if a
  fresh GitHub PAT arrives, reconcile GitHub first.
- Laws distilled this session are in .agents/SKILL.md (SESSION 16).


## Session-16 addendum (GREEN LIGHT shipped — read FIRST)

- **THREE films live in previz-review** (newest-first, comments ON):
  **tgreen_1 rev 2** (GREEN LIGHT — the afternoon crossing that
  freezes; stamp 2c21c26b, git_sha 3e852da), **tferry_1 rev 2** (the
  reframed S4/S5 + the review-round crowd contract), **tdawn_3**.
  THE OPEN ITEM: the user review round on all three.
- **The Green Light build order worked; reuse it** for any fourth
  film: design doc -> 2 audit rounds + 1 research note FROM SOURCE
  (the two P0s were pre-build catches) -> world module (sub-agent,
  eye-gated) -> contract (INGEST PROBE = the round-3 test, seconds,
  no bake) -> bake driver (per-zone speed map by PARSED ZONE ID) ->
  scene module -> flow strip FIRST (the seam detector + the
  behavior read) -> camprobe framing -> the daylight ladder -> 12
  EEVEE stills (eye gate) -> in-place rev-N export (seed from the
  staged stamp) -> stage with the stamp cross-check.
- **The eye gate caught what no reviewer could**: the stills runner's
  clone seam (rendered the FERRY's shots into the tgreen dir), the
  ocean-horizon void, the invisible title (two z probes), the nadir
  palette panic (a roll ambiguity — the ortho flow strip settled it).
- **Determinism (3-h)**: same inputs -> byte-identical npz (tgreen
  9f6ea8fa reruns; tferry 8b7d4d8e cross-session). Never reuse the
  default --out across runs; uncommitted states leave no trace.
- **The standing kit chores** (UPDATED s17: F-TD9 CLOSED in-code s16;
  F-TD5/F18/F19/F20 closed; the open filings are F-TD1, F-TD2, F-TD3
  [CLOSED s17], the make_material default filing [closed-in-code],
  F-TF6 — joined by F-TG1's engine truth: arrived agents are ghosts; a
  pushout feature must define arrival semantics first):
- Bootstrap is unchanged (clone 5 repos -> install.sh -> venv wheel
  -> server via daemonize + repo-local db -> restore comments). The
  green-light module set: tgreen_{contract,world,bake}.py +
  scene_green_light.py + tgreen_{camprobe,flowstrip,filmstrips,
  ladder,stills}.py/sh.

## Session-15 addendum (the SECOND lane's completion — read with the block below)


- **The app NOW carries the FINAL composition**: the staged tferry_1
  was re-cut from vision-kit 329a9d8 (previz-review 0008cfa) — the
  flip BOARD, the gang spot + gate work light, S9 re-aimed onto the
  crossing @f735, the 420W lane lamp, on top of the east pools/fill/
  title-emission pass. 12/12 EEVEE stills eye-certified by BOTH
  lanes' contributions composed as ONE set. The "stage rev 2" note
  below is DONE.
- **The fresh-context review round consumed (Task 5-a: zero P0s,
  5 P1s)**: the count law now pins N_RELEASE (the apportionment
  tautology), HERO_LANES removed as DEAD DATA (kit mode has NO
  hero-lane pushout — filed F-TF6 in the ledger), the RB
  placeholders parked OUTBOARD, render.fps pinned in build_scene,
  the FLANK WALL at y=-2.7 (the y=-0.5 wall's south face leaked a
  water-walk band). NEW LAW learned: the native engine REFUSES
  barricade squares past the walkable edge (E_InvalidRange) — cap
  centers at walkable−r. Re-bake pin 8b7d4d8e; the contract now
  evolves AHEAD of the staged package (an honest rev 2 re-export
  picks up the review fixes + the outboard statics when the user
  round demands it).
- **The ledger: docs/USABILITY_TF1_last_ferry.md** (F-TF1..6 + the
  night laws at shot scale + the two-lane merge-cost lesson).

## Session-15 close state (NEWEST — read this first)

- **THE APP SURVIVAL KIT (verified this session)**: clone
  previz-review → `bun install` → `npx prisma generate` → `npm run
  db:push` (REPO-LOCAL db) → start via
  `python3 scripts/daemonize.py <ABSOLUTE log> bash -c "cd <repo> &&
  bun run dev"` — daemonize.py chdirs to "/", so relative log paths
  EACCES and relative commands "Script not found". Then
  `s33_restore_comments.sh` (needs the server UP first).
- **The tdawn_2 comments are recoverable from git**: the mirror
  journal had none — they were re-injected from escape 8841ee1
  (previz_comments_tdawn_2.json) via POST. The db dies with the
  sandbox; the escape-repo export is the durable copy. Keep exporting
  user comments there.
- **tferry_1 is LIVE and complete** (staged 749d0a1, module
  4ef144b+): 12 shots / 45 s / 129-agent converge crowd / 21.1MB GLB
  / 96 strips / 12 EEVEE night stills / sfx events. Export ALL GATES
  GREEN. The scene module's FINAL merged set is 329a9d8 (the parallel
  lane composed both lanes' night passes: sign_flip keys, gang spot,
  gate work light, 420W lane lamp, S9 onto the gate @f735) — the
  STAGED package predates that composition; stage rev 2 from the
  final module if the deltas matter to the user round.
- **tferry build-order laws (new, measured)**:
  - F-TF1: ingest fail-closes on contract shape names — the contract
    needs DT + N_RELEASE + SPAWN_ZONES_V5 (the slice's "dry-run
    green" was scene-side only; ingest was never exercised).
  - The bake driver asserts the REV-2 F1 envelope PRE-bake (crew
    2.60 <= far 2.65) — the bridge clamps SILENTLY otherwise.
  - F-TF5 (OPEN): the vision-kit VENDOR wheel is 1.0.0, crowd-kit's
    is 1.5.4; the bridge needs 1.5.4 (motion_matcher kwarg). Re-vendor
    via the governed sync.
  - The exporter's story contracts: build_scene MUST return
    ctx["scene"] (exporter:2736); BEATS is (id, t_seconds, label)
    with t = (f-1)/24; sfx events need {name|kind, frame} — the "id"
    key is dropped 3/3 BY THE APP (found from the in-app console).
  - The Latecomer HOLDS at (4.8,8) f444-700 — aim the shot cams at
    the HELD pose, not the intent text (S7's aim was 4.8m stale).
  - Night pools: the east band needed (5.6,17.5) + (5.6,7.0) — lamp
    gaps read as murky dead stretches on the shot cams. The title
    card needs F-TD11 emission (make_material's 3rd arg is ROUGHNESS).
  - The sandbox's headless chrome CANNOT play the 21MB GLB (software
    GL; the tab died twice) — verify packages via the API + stills;
    3D playback is the USER's real browser.
- **Chain-replay receipt** (the aborted session-14 segment): the
  committed chain inputs replayed on the rebuilt master — cuts/props/
  route/walk/SITS all matched the R6/R7/R8 records numerically (both
  sits GREEN). The chain is reproducible from committed inputs; that
  was its purpose. Queue item CLOSED.
- **Merge law learned the hard way**: in `git rebase`, `--theirs` is
  YOUR replayed commit and `--ours` is the base — resolving backwards
  silently drops the incoming work. RE-RENDER + DIFF against the
  incoming commit after every conflict resolution (the re-render
  caught the dropped F-TF3 water-wall within one round).


## Session-14 close state (NEWEST — read this first)

- **DELIVERABLE LIVE: tdawn_3** (previz-review newest-first, comments
  ON): the user's 5 tdawn_2 comments ALL fixed and eye-verified —
  S1 color discipline (neutral crowd register + ONE rust chase callout;
  the user's law: color = call-outs, not diversity), S5 reframe (RCA:
  near-field capsule flood + a 7m-stale aim; new NORTH vantage down the
  stream axis), S10 gate-wall 3/4 + pilasters/beam/exit gantry (the
  pilasters are DECLARED barricades), S12 title = export-safe SCALE
  keys (hide_render keys do not export — the "constantly visible" bug),
  + F-TD13 (the keepout rows were SECONDS-vs-FRAMES inert — now
  shot-span frames + S12's dolly row). 12/12 stills re-reviewed twice.
- **THE KIT TRIO closed** (docs/DESIGN_FTD_trio.md REV-2, 2 review
  rounds): F-TD10 (the blrun flock, all FOUR repos, exit 90 +
  LOCK-HELD marker; vendor round 40/40), F-TD11 (make_material
  emission params, both kits + the twin; tests t7/v8), F-TD12
  (look.py --probe-camera; test_v7_camprobe 14/14 incl. the animated
  occluder). agent-kit 8a93e0b; escape vendored 60abd33.
- **LAST FERRY (tferry_1) slice**: design REV-2 (the reviewer probed
  the bridge source: speed envelope 2.65 vs tail 4.60 would clamp
  SILENTLY — retuned; throat AT (0,0) (the bridge hardcodes the
  target); walkable reaches y=-6 (the apron covers it); CROWD_X_RANGE
  (−6,6); crane over water = zero keepout rows; use_raytracing is the
  5.2 SSR knob). Modules: tferry_contract.py / tferry_world.py /
  scene_last_ferry.py — dry-run green, night look PROVEN at 4 frames
  (the L-TF1..4 laws are in SKILL.md).
- **Bootstrap that works (verified twice this session)**: clone the 5
  repos (CANONICAL names), bash install.sh (Blender 5.2.2 + Pillow OK
  on fresh single-python bundle), crowd wheel → venv
  (vendor/blender-crowd/addon/blender_crowd/wheels/*.whl), bake, run.
  The dev server: scripts/daemonize.py (double-fork) ONLY; comments db
  = repo-local; s33_restore_comments.sh after db push.
- **Open**: tferry_1's bake driver + flow strip + shot cams + stills +
  export + stage (the build order = kb/tdawn_vision_film.md steps 4-8
  with tferry names); the user review round on tdawn_3 + tferry_1;
  F-TD9 (install.sh Pillow probe for the stale-4.x-tools case — the
  fresh case self-healed); the older filings — the true remainder is
  F-TD1/2/3 (the make_material default is CLOSED —
  blender_kit/__init__.py:516 make_material pins Emission Color to the
  base rgb, :549).

> The user-directed D18 lane: the 561MB loft.blend is now IN-GIT as
> 119 textures + 14 chunks + manifest; fresh-clone rebuild proven
> (manifest_diff 0 findings, renders pixel-identical). Read
> docs/USABILITY_R9.md (10 measured Blender laws) +
> docs/DESIGN_D18_asset_partition.md (REV-3) first.

## Session-13 close state (NEWEST — read this first)

- **The asset is clone-transportable now**: after cloning, run
  `bash install.sh` then
  `./run.sh --background --python scripts/r9_rebuild_asset.py` — it
  builds `assets/loft/loft_master.blend` (gitignored, rebuildable)
  from the committed chunks + manifest. No Release, no network.
- Laws that WILL bite again on any .blend-partition work are in
  docs/USABILITY_R9.md (fake_user/users, scene-anchored compositor
  trees, save re-relativization, autopack, the Area.001 double-write
  law, closure gaps, delivery-model expectations). The chunk files in
  assets/loft/chunks/ are IMMUTABLE — a changed asset means a NEW
  asset directory, never an in-place rewrite.
- Regression: tests/test_r9_chunking.py 16/16 (synthetic round-trip,
  runs the real scripts as subprocesses with --python-exit-code).
- Open queue: see PLAN.md Queue (R10 candidates, t10, VK-9, upstream
  PRs, chain-input re-point).
- Parallel-lane live coordination held all session (6 remote moves,
  fetch-rebase before every push, zero force pushes).

> Session close: 2026-10-11 (session 12, the TERMINAL DAWN build).
> The user-directed vision-native film: from-scratch previz short
> built with THIS kit + blender-crowd-kit, exported kit-mode through
> the agent-kit exporter, staged to previz-review as `tdawn_1` —
> LIVE and verified in the app. Read kb/tdawn_vision_film.md (the
> recipe) + docs/USABILITY_TD1_vision_film.md (the friction ledger)
> + docs/DESIGN_terminal_dawn.md (design + REV-2 review folds).

## Session-12 close state (NEWEST — read this first)

- **DELIVERABLE LIVE**: previz-review `public/packages/tdawn_1/`
  (12 shots / 45 s / 1080 f, 129-agent crowd via the bridge kit mode,
  21 MB GLB, 12 EEVEE stills, 96 filmstrips, previz.json schema 2.3
  with the portable story vocabulary synopsis/beats/cast). The review
  app serves it newest-first; comments API needs `bunx prisma db push`
  + dev-server restart on a fresh clone (500-on-fresh-clone class).
- **THE HEADLINE FIND (F-TD5, KIT BUG, export-blocking)**: the
  exporter's #29 sweep (blender_kit.render_hidden_objects, owner =
  blender-agent-kit) reads a STALE view-layer object list — a
  freshly-linked object (measured: Runner.Root) false-positives as
  view-layer-excluded and gate 24 rejects the export. Scene-side sync
  duty landed in my build_scene; THE KIT-SIDE FIX IS UNLANDED (owner
  repo; do NOT vendor here). Highest-value first action for any kit
  session: land `view_layer.update()` before the #29 check upstream.
- **F-TD3**: marker-camera hijack + scene.camera MUTATION on clearing
  marker bindings — look.py is still vulnerable on marker-bound
  scenes (matches QA #11 on agent-kit). My passes are marker-safe
  (tdawn_flowstrip.py / tdawn_filmstrips.py patterns).
- **AgX emission laws (5.2, measured)**: Principled Emission COLOR
  defaults WHITE (pin to base rgb — make_material does); glow keys
  >~1.0 desaturate to TAN under AgX (cap 0.95); sky 1.0 blows
  interiors (0.35-0.5 + exposure -0.5).
- **Crowd-kit integration proven end-to-end**: bake driver (venv,
  keepouts PASS-THROUGH is the driver's duty — F-TD4) → loader honesty
  asserts → bake2 → exporter kit-mode gates 15/16/17 green at N=129.
  The bridge shape (pursue-origin) was reused as a different STORY
  (gate convergence) with zero bridge forks — the pattern to copy.
- **Parallel-session races**: the remote moved twice mid-session
  (D17/F22/F20 from a parallel session); GitHub + GitLab converged via
  sync_both.sh discipline. tools/ (Blender) NOT committed; gitignore
  holds. /home/sync copy made at close.
- Open: F-TD1 (cross-kit wheel install), F-TD2 (validator structural
  noise), F-TD8 (git races — standing), the six kit improvement
  filings (USABILITY_TD1 final section), the tdawn_1 user review
  round (comments are ON — the film awaits the user's notes).


> Session close: 2026-10-05 (session 8). Handoff-protocol audit +
> paydown (user-directed: "be extremely rigorous"), R5 real-asset
> lane, blind-agent STRESS TEST on a real polyhaven asset (protocol
> ROBUST), F17 fixed, validator v2 shipped. PLAN.md = long-horizon
> tracker. Study: docs/USABILITY_R5_polyhaven.md.

## State at handoff

- Repo: https://github.com/zmpc01/blender-vision-kit (main). GitLab
  mirror STILL BEHIND (PAT unrecoverable; GitHub = source of truth,
  /home/sync tar carries the same HEAD). NEVER force push.
- SCOPE DOCTRINE (binding, owner-ruled): kit FOR vision-native agents
  ONLY. Sub-agents: NON-VISUAL work only, and now under a WRITTEN
  EXECUTION CONTRACT (AGENTS.md D16 section): VISION-REQUIRED
  (region-cut box choice, label assignment, verdicts, delegate
  verification) vs BLIND-SAFE (loose dry-run/split, label_objects with
  GIVEN labels, manifest-derived placement, audit tools) vs
  STOP-AND-FLAG (cannot derive from manifest -> flag, never guess).
- Toolchain: NOT committed. Fresh sandbox: `bash install.sh`
  FOREGROUND. Blender 5.2.2.
- Regression battery (ALL GREEN at close): test_kit_scope (171 files),
  v1 27, v2 27, v3 20, v4 29, v5 76 (incl. L19 world_bbox + L22
  containment), v6 18 (manifest_diff, pure python), test_f17 9,
  t1–t6, t8 8/8, t9 chaos.

## Session-8 kit changes (evidence: docs/USABILITY_R5_polyhaven.md)

1. **Execution contract + verify-delegated-work checklist** (AGENTS.md
   law + kb/semantic_labeling.md): the session-7 blind handoff was
   real but implicit; delegated work was verified by eyes+claims.
   Now: baseline manifest -> delegate -> fresh look -> manifest_diff
   (every finding maps 1:1 to the task list) -> re-measure yourself ->
   closeup every touched object -> verdict last.
2. **manifest world_bbox** (look.py): every MESH row carries the
   world-space AABB — dims_m is LOCAL and lies under rotation; a
   blind consumer has no other ground truth. Caught + fixed a REAL
   stale-matrix bug en route (manifest now forces view_layer.update).
3. **manifest_diff.py** (pure python, no bpy): moved/resized/
   label_changed/added/removed/renamed(geometric twin)/nonmesh; accepts
   bare row lists AND full look_manifest.json dicts; --expect-clean
   rc=1 guard. tests/test_v6_manifestdiff.py M1-M10.
4. **F17 fixed** (placement_lib): place_on footprint grid refines ×4
   until rays hit (cap 192², sub-second) — top-onto-0.08m-legs on 2.4m
   span now solves (was: every 12×12 cell missed by 0.01m → blind
   agent had to snap_z). Report key footprint_grid_refined.
5. **Validator v2** (validate_scene): containment ≠ collision — pairs
   skip ONLY when both sides carry kit_label, shell-side label matches
   the shell vocabulary (room/shell/wall/floor/enclosure/interior/
   building), and the prop centroid is inside the shell bbox. Skips
   VISIBLE: summary.contained_pairs_skipped (pair+pct+reason). D16
   fixture demo: 2 blob P0s → 0 issues + 2 recorded skips.
6. **R5 lane scripts**: scripts/r5_polyhaven_fetch.sh (polyhaven API
   gotchas: /files/{id} NOT /download/file; textures under Models/jpg/
   <res>/<asset>/ despite gltf's textures/ URIs; undersized-file
   check) + scripts/r5_polyhaven_import.py (measure→scale 1.6m→ground
   →center, camera+sun).

## THE 456-PART LESSON (R5, print this in memory)

Real assets (polyhaven CoffeeCart_01): cart = 456 loose parts,
props = 329, mugs = 16. The D16 fixture's 10-island scale was
misleading. Blind loose-split at that count is legal and DESTRUCTIVE
(456 vision passes, source name lands on an arbitrary sliver).
**Label at VENDOR-NODE granularity; region-cut only features a
consumer must address.** Stress test: the blind agent REFUSED the
115-way split on its own (contract working) and flagged ≥3 pail
candidates for the bucket instead of guessing a cut box.

## Stress-test result (the user's rigor question, answered)

Blind agent (manifest+docs only, no hints which tasks were baits):
T1 seat mug_tray → DONE, self-verified (109.9mm clearance, 0.0mm
contact). T2 "fix floating cart_props" → WITHHELD (proved snap_z
sinks the 115-part cloud through the cart; place_on teleports it
+0.653m — gaming the gate). T3 "cut the bucket out" → PARTIAL
(dry-run yes; identity vision-required; no guess). T4 save → DONE.
Principal verification (trust nothing): manifest_diff baseline vs
assembled = **0 findings**; validator re-run by me = all pre-existing;
eyes on grid. Protocol ROBUST.

## Immediate next-session TODO (in order)

1. **F19** (R5 finding): loose `split` warn-gate — dry-run part count
   > 50 → require ack_many_parts:true; AGENTS.md line + v5 case.
2. **F18** (R5 finding): doc origin_offset_warning as load-bearing
   (glTF vendor origins 965mm off — set_location-style ops unsafe;
   world-space solvers only).
3. **R6 dog-food: a WELDED level asset** — the region-cut playbook on
   real level geometry (Sketchfab/Quaternius CC0 interiors; the D16
   fixture simulated what R5's cart didn't exercise).
4. Keep QA lane running (fetch+rebase mid-session; never force).
5. PLAN.md: t10 export-package suite, t6 ship, upstream D11 PR,
   crowd T3 (upstream-gated).

## Standing gotchas (do not relearn)

- Work in /home/z/vision-work clone (watchdog resets /home/z/my-project);
  Write tool only under /home/z/.
- Read-tool "syntax error" displays that contradict ast.parse = display
  mangling — trust the file (bit us twice this session: semantic_lib
  line 438, validate_scene MultiEdit ghosts).
- MultiEdit on argparse/dense blocks can apply with "failure" reports —
  ALWAYS verify with ast.parse + grep for duplicates after every
  structural edit (validate_scene got its header block TWICE).
- bmesh: indices not BMFace refs after bm.free(); bound_box corners
  need Vector wrap; primitive_cube_add defaults size=2 (span helpers
  pass size=1); matrix_world is STALE after in-process mutation until
  view_layer.update() (L19).
- place_on footprint grid refinement caps at 192×192 — beyond that,
  restructure the scene instead.
- Test fixtures: cell centers of an offset bbox can land EXACTLY on
  the feature (F4 first draft hit the 1cm pin at base density) —
  offset fixtures off-column deliberately.
- "File content impossible" Write errors = harness display mangling —
  verify with od/ast.parse, trust the file.
- F6 residue: add_sky_world() DEFAULT strength 1.0 still blows out
  EEVEE stills — template passes 0.5; changing the library default
  needs an owner ruling.
- GitLab push prints storage warnings even on success — verify HEAD.
  (HISTORICAL, session-14: the then-current GitLab PAT read invalid —
  superseded s16/s17: GitHub canonical, GitLab archive branch.)

## Worklog + artifacts

- Repo worklog.md has the session-8 record (replicate into
  /home/z/my-project/worklog.md — harness dir does not survive).
- Study artifacts: docs/USABILITY_R5_polyhaven.md (this session),
  docs/USABILITY_D16_dogfood.md (session 7). Design docs:
  docs/DESIGN_D16_semantic_labeling.md.
- R5 artifacts (not committed, reproducible): output/r5/*.blend,
  look dirs, baseline/after manifests, labels_report.json,
  agent_work/ (blind agent's dry-run evidence).
- Multi-agent QA protocol: fresh-context sub-agents do NON-VISUAL
  review only; the D16 audit round 1 is the pattern.
- #11 [P2][bug] look.py --angles panels pixel-identical when loaded .blend has camera-bound timeline markers (marker camera hijack at render time — AK-10 class; agent-kit viewport_capture fixed it via suppress-BEFORE-assign + finally-restore, look.py has no marker handling). Repro: blend with markers S1@f1->CAM_A, saved frame 24, --angles front,persp -> meanAbsDiff 0.002 (38/307200 px), captions still say front/persp, manifest healthy with no per-panel camera recorded. Evidence: freshbook docs/qa-blender-kit/evidence/qa-r046/{grid.png,look_manifest.json,r046_main.log}.

## QA-LANE DISPATCH R52
VK-9: agent-kit twin (validate_scene.py @26c78eb) verified live via this issue's harness (0.2m/0.05m slabs exempt, sunk-sphere genuine positive retained); vision-kit's own copy unchanged at HEAD → stays OPEN pending re-vendor. VK-10: independent probe @6b09514 — drift layer STILL LIVE on this kit's examples/scene_v1_basic.py (sphere_x_keys=[(24,-2.0)] single-key collapse, x=-2.0 at f1/f12/f24); the s36 claim values match agent-kit's fixed copy, not this file; crash layer (iter_fcurves) IS fixed. Ask: port agent-kit examples/scene_v1_basic.py:123 sphere frame_set hunk. Evidence: freshbook-clone docs/qa-blender-kit/evidence/qa-r052/R52-VERDICTS.md.

## QA-LANE DISPATCH R56 (auto)
- Session-8 deep-verify receipt @3c06e05 (QA-r056-a): validator v2 CONTAINMENT SKIP PASS live (labeled shell + contained prop → 0 issues + contained_pairs_skipped VISIBLE with reason string; unlabeled overlap still flags P1, --fail-on-issues rc=1; renders eye 6/6 PNG) · manifest_diff PASS (owner suite 18/18 M1-M10 + full-dict {"manifest":…} unwrap ≡ bare list, reports equal + --expect-clean rc 0 clean / rc 1 "EXPECT-CLEAN VIOLATED") · F17 PASS (place_on onto 0.08m inset legs → "footprint_grid_refined": "12x12 found no support — refined to 48x48", tabletop zmin 0.7500 vs leg top dz=0.0000, crate dz=0.0000; wide support correctly no-refine) · VK-9 STILL LIVE (own 0.2m slab flags 100% penetration) · VK-10 STILL LIVE (keys=[(24,-2.0)], x=-2.0 at f1/f12/f24) — asks unchanged: re-vendor + example hunk port. MemAvailable guard named-skip @1195MB non-fatal (R22 law holds). — QA-r056-a

## QA-LANE DISPATCH R69 (auto)
- #12 [P3][polish] install.sh aborts rc=2 (dpkg-deb "failed to chdir") when tools/local-libs is a DANGLING SYMLINK — raw tool error kills the script under set -euo pipefail BEFORE the :95 teacher-grade ERROR line can print. Repro 3/3 (sibling-symlink consolidation flow); fix control: absolute-path symlinks → rc=0 (Blender already installed / libEGL already extracted / Done).
- Ask: dangling-symlink detect-and-heal guard (rm dangling + mkdir -p) before the extraction loop, or stage-extract to mktemp -d then cp -a; keep :95 teacher line reachable (|| teacher-error wrapper).
- Narrow trigger but natural workaround (re-run install) re-downloads a duplicate 1.2 GB Blender per sibling kit; QA SOP sibling-symlink law corrected on our side in parallel.
- Evidence: belram448/freshbook-clone docs/qa-blender-kit/evidence/qa-r069/ (vk_inst.txt, vk_inst2.txt rc=2) — private repo, belram448 PAT required.

## SESSION 9 — R6 CLOSE (real level: cut → label → compose → blind handoff)
State: GitHub HEAD = R6 wrap commit (verify with git log -1). Sandbox
wiped between sessions; bootstrap = clone + `./install.sh` foreground
(Blender 5.2.2, Cycles OK). The asset re-downloads via
`scripts/r6_loft_fetch.sh` into /home/z/vision-work/polyhaven_cache/loft/.

What exists now (state chain output/r6/, all reproducible):
loft_import → loft_look (lite) → loft_cut_arch (4 shell cuts) →
loft_labeled (1155/1200 kit_label) → loft_props (4 placed) →
loft_compose (2 UAL actors: Driver walking, Girl on mezzanine) →
loft_blind_work (agent additions) → loft_final (label fixes).
Manifests: handoff/ (pre-work), blind_work_manifest/ (post-work).

Verified end state (my eyes + tools):
- region cuts render-verified (stairs pre/post pair in look_cuts/)
- placements audit-clean (book TOUCHING, ball 0.0mm, lantern TOUCHING,
  mug CLEAR 5.95mm on the recessed ottoman top)
- blind agent: T1/T2 DONE audit-clean; T3 bait WITHHELD with zone
  evidence; manifest_diff independently re-run: 2 findings (additions
  only), 1209 unchanged
- pendant_light/arc-lamp/chair label corrections applied after the
  agent's spatial-anomaly report (the handoff caught MY errors)

Read FIRST for context: docs/USABILITY_R6.md (full record incl. limits
hit: OOM ×2, annotation explosion, honest validator noise on real
levels), kb/semantic_labeling.md R6 section, AGENTS.md D16 section
(mesh_prepare + FLAG_CAP law). Friction queue: F20/F21/F22 + VK-9/VK-10.
Blind-agent lessons live in .agents/SKILL.md (center-placement law,
fused-face signature, family-granularity labeling).

Delegation protocol for the next session: unchanged (AGENTS.md
EXECUTION CONTRACT) — vision-required: cut boxes, label assignment,
verdicts, delegate verification; blind-safe: placement/measurement ops
from the manifest; STOP-AND-FLAG anything underivable. The R6 run is
the reference execution of that contract on a real interior.

## SESSION 10 — R7 CLOSE (the level NAVIGATED: blind route → stair ascent)
State: GitHub HEAD = R7 wrap commit (verify with git log -1). Bootstrap
= clone + `./install.sh` foreground. The full R6 chain rebuilds from
committed scripts (verified live this session — dry-run face counts and
placement verdicts matched the R6 record exactly).

What R7 proves: a NON-VISION agent can PLAN floor-to-floor navigation
from the manifest alone (r7_route_planner.py — pure Python), the kit
EXECUTES it (r7_navigate.py: label-driven supports, tread-hug with
incremental ceiling + fall-through guard, NLA walk loop for the Blender
5.2 API), and a two-tier audit certifies it numerically (0 true floats
/ 705 frames) + renders verify it visually. Where bboxes cannot decide
(stair running UNDER the slab: abut-direction ambiguous), the blind
planner STOP-AND-FLAGS and the principal resolves via
vision_stair_override.json — recorded, not hidden.

THE BIG FIND: navigation caught a real R6 label defect — the `stairs`
label sat on a 14-face parapet fragment; the actual stair (Plane.003:
9 flat treads, +y, ~31°, under the mezzanine slab band, arriving at the
slab at y 13.8) was labeled `wall`. Schema corrected in
gen_r6_labels.py with the evidence inline; chain re-run end-to-end.
LAW: a semantic label is a hypothesis until a USE (walk/place/seat)
exercises it — navigation is the strongest label validator (F23).

Read FIRST: docs/USABILITY_R7.md (probes 3-16 narrative + gotchas:
BVH local-space rays, Blender 5.2 slotted actions / NLA looping,
texture-driven displacement vs the lite lane). Tests:
tests/test_r7_route.py (pure Python) + v1/v5/v6/f17/scope ALL PASS.
Artifacts: output/r7/{route_request.json,vision_stair_override.json,
nav_report.json,loft_nav.blend (with 2 tracking cams),look_nav/}.

Delegation protocol: unchanged (AGENTS.md EXECUTION CONTRACT). Blind
agents can now also REQUEST ROUTES (planner is pure Python on the
manifest) — but executing a route stays kit-side; verify every
delegated nav with the audit numbers, never self-reports.


## SESSION 12 — R8 CLOSE (the level INHABITED: actors SIT)
State: GitHub HEAD = R8 wrap (verify git log -1; parallel lanes may
have moved it — fetch first). Bootstrap = clone + ./install.sh
foreground; the loft asset comes from the GitHub Release
"level-asset-loft" OR scripts/r6_loft_fetch.sh (NOT in git — 100MB
blob limit; the R7 wrap commit was rewritten 0315ab8 = f7facd9 minus
the blob; polyhaven_cache/ is gitignored).

What R8 proves: the kit derives seat surfaces from LABELED furniture
by probe (region-growing, sat-upon/clutter/contamination guards,
seed-driven), measures the actor's seated pose (H/O/flesh-c with a
prior gate), executes walk->sit->idle->exit via a single NLA track,
and certifies it (sphere-proxy lane + exit reverse-validation).
Driver->sofa (rigid/high) and Girl->bed (soft/medium) both ok=True;
renders verified by the principal's eyes (profile shot settles seat
contact). test_r8_seat.py 18/18 + test_f22_levels.py 14/14 + battery.

Read FIRST: docs/USABILITY_R8.md (7 guarded probe failures = the
texture of real furniture), docs/DESIGN_R8_seat_protocol.md (D17
REV-2), .agents/SKILL.md R8 addendum (yaw law, NLA junctions, seat
math, git blob law). Friction queue: F20/F21/F22/F23 + VK-10 all
CLOSED this round; VK-9 (re-vendor) still open.

Delegation protocol unchanged (AGENTS.md EXECUTION CONTRACT). New
blind-safe surface: r8_seat.py probe on a labeled family + approach
hint (STOP-AND-FLAG exit 4 on contamination/clutter/low-confidence);
executing a sit stays kit-side; verify delegated sits with the audit
numbers (ok flag + dz + no_penetration + exit_ok), never self-reports.

## Session-13 close state (tdawn_2 era — historical)

- **DELIVERABLE: `tdawn_2` LIVE** in previz-review (newest-first) and
  in the served checkout — the user-directed refinement round. Every
  tdawn_1 eye-finding fixed: the varied commuter palette (G1: the
  per-agent materials land POST-bake_tier2; the lib mesh is shared so
  pre-bake assignment collapses to one color), the gate TUNNEL + the
  seal-edge slit strips (G2: the flat white screen → a receding lit
  portal), the REAL departure board (the rows were flush-mounted
  INSIDE the panel silhouette — now proud), the pylons with lit sign
  faces (G3), 7 camera reframes (S1/S5/S7/S8/S9/S10/S12 — S8's empty
  hall → the Master/Runner pairing AT the gate line; S9's south vantage
  → the hall side: the dive reads AWAY from the crowd, silhouetted
  against the vault glow through the sealing gap), the dive retimed so
  the arc peak lands EXACTLY on the S9 still frame (f750), the title
  card (converted FONT mesh, warm cream, hide_render-keyed until the
  f1009 sting), the white-out tamed (the glow-surface law: dark base +
  warm Emission Color — make_material's equal-pin design is the white
  void), the stumble moved INTO S7, the board flicker A/B anti-phase.
- **F-TD5 LANDED UPSTREAM** (agent-kit e4450a3: view_layer.update()
  before the #29 sweep; A19f red/green proven; 79/79 tier-A) and
  VENDORED DOWN (the wrapper's governed-pair guard caught the drift —
  the vendor flow: kit tools/sync_shared.py --to <consumer>, commit
  both).
- **THE SESSION-13 SURVIVAL LAWS** (SKILL.md): the factory-scene purge
  (--factory-startup loads Cube/Camera/Light into your scene), the
  glow-surface law, the recession-occlusion class ("invisible subject"
  → ray-cast through it before doubting animation), "frame-edge clip"
  can be an occluder, never run two blrun/EEVEE pipelines concurrently
  (Xvfb :99), Bfont ≈ 0.91-1.1 em/char, the comments db is repo-local
  (push the schema with the absolute URL; the harness exports a global
  DATABASE_URL the app ignores), Pillow on 5.2 = python3.13.
- New kit filings: F-TD9 (factory leak + install.sh Pillow probe),
  F-TD10 (concurrent blrun), F-TD11 (make_material emission_color
  param), F-TD12 (shot-cam occlusion probe) — docs/USABILITY_TD1*.
- Fresh sandbox bootstrap that WORKS (verified end-to-end): clone the
  4 repos with the CANONICAL dir names (blender-vision-kit,
  blender-escape-previz — the scene module's TPREVIZ_SCRIPTS default
  and the bake driver hardcode them), bash install.sh, Pillow by hand
  (py3.13), wheel into the venv
  (blender-crowd-kit/vendor/.../wheels/*.whl), bake
  (tdawn_bake.py --out /tmp/crowdcache_tdawn), stills (SAMPLES=24 for
  the S10 heavy class), export (the wrapper command in the kb, with
  KIT_EXPORTER + BLENDER_BIN exported), stage both checkouts,
  prisma db push (repo-local db!), bun dev.
- Open: the F-TD9..12 kit filings; the user review round on tdawn_2
  (comments ON); the six older filings (F-TD1/2/3 + the make_material
  default) — F-TD6 is now PARTIALLY superseded by the glow-surface law.

## Session-16 addendum 2 — THE PUSH-PROTECTION EVENT (read before
## any merge of parallel-lane work)

- A GitHub REPOSITORY RULE (push protection) now BLOCKS any push
  carrying ghp_* tokens — the parallel lane's _sess16_*.sh helpers
  embedded their (refreshed) PAT in commits that reached GitLab
  (unscanned) but can NEVER reach GitHub.
- THE PROTOCOL THAT WORKED (no force anywhere): (1) fetch the dirty
  line from GitLab; (2) filter-branch the range redacting the PAT
  PATTERN (s/ghp_[A-Za-z0-9]{30,45}/REDACTED-.../ — the LITERAL
  string fails when the lane rotated the token); (3) rebuild the
  merge commit with commit-tree on CLEAN parents (the resolved tree
  from the first merge + the redacted lane tip); (4) REDACT THE
  MERGE TREE ITSELF (the merge auto-merges the dirty tip files —
  the tip carried the PAT even though the intermediate-check said
  clean: always scan the TIP with the PATTERN, not a remembered
  literal); (5) push — a clean fast-forward, no force, both remote
  histories durable.
- CURRENT MIRROR STATE: GitHub main = 2085bba (canonical, clean);
  GitLab main = the raw lane line 78a3eaf (carries the PAT in
  history — GitLab does not scan). Do NOT merge the GitLab-only
  line into GitHub again without the redaction protocol. The lane
  must stop committing tokens (the .env pattern is the home).
- New kit tools from their lane to dog-food: export_preflight.py
  (--module <scene.py> BEFORE any export), the t10 battery.
