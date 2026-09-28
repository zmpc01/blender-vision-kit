# SOP.md — Job-by-Job Standard Operating Procedures

> The distilled best-practice for every recurring "job" along this
> project's whole journey, each built around the **tight action-verify
> loop** (act → see → correct, seconds not minutes) and with explicit
> **sub-agent delegation slots** (what to delegate, what to keep).
>
> Companion docs: AGENTS.md (kit consumer guide + gotchas 1-36),
> FINDINGS.md (what actually happened), .agents/SKILL.md (meta notes).
>
> PRINCIPLES (apply to every job):
> 1. **GIT IS THE DISK** — push on every micro step; the sandbox is
>    disposable, the remote is not.
> 2. **Never trust unverified output** — every artifact gets read
>    back: programmatic probe > own pixel read > neutral VLM.
> 3. **Dumbest system that works** — primitives before rigs, direct
>    keyframes before NLA, constants before cleverness.
> 4. **Minutes not hours** — viewport quality only; a render you
>    can't re-run in <10 min is a liability, not an asset.

---

## Job 1 — Environment provisioning (fresh sandbox)

**Trigger:** new session / empty tools dir / "blender binary not found".
**Time budget:** ~5 min (download is the long pole; run detached).

1. Clone the kit: `git clone https://<PAT>@github.com/zmpc01/blender-agent-kit.git ~/blender-agent-kit`
   (add the previz project repo too if the deliverables are needed).
2. `setsid nohup bash install.sh > /tmp/install.log 2>&1 &` — download
   is resumable: if curl dies, `curl -fL -C - -o tools/<tarball> <url>`
   then re-run install.sh (idempotent).
3. Work ONLY outside the watchdog path `/home/z/my-project/` (it
   force-reverts to main every ~20 s).
4. **VERIFY:** `./run.sh --background --python smoke/smoke_render.py --
   --output smoke` — 3 engines must all report OK + timings. A broken
   kit here (e.g. conflict markers from a bad merge) must be caught
   BEFORE any long job (AGENTS.md #30).
5. **Delegation slot:** none — 3 commands, keep it in-session.

## Job 2 — Story → storyboard → shot table

**Trigger:** a new sequence to previz.
**Time budget:** 30-60 min thinking + one table.

1. Write STORYBOARD.md: shots with intent (what each shot
   COMMUNICATES), duration, camera idea, and the story beats with
   times (t, seconds) — one authoritative t→frame map (FPS=24).
2. Encode as module-level tables: SHOTS, events (falls, lunges,
   bursts), dialog (line, frame). Constants beat prose.
3. Assert events land INSIDE their shot windows (master audit).
   A phase change (adding a parked phase) shifts everything —
   re-derive, never hand-patch single numbers (AGENTS.md #29).
4. **VERIFY:** print the timeline; check every event t is inside its
   shot's [f0, f1] programmatically.
5. **Delegation slot:** LOW — story feel is the orchestrator's call.

## Job 3 — Asset module build (street / vehicles / zombies / actors)

**Trigger:** new scene content. One module per asset family.
**Time budget:** 1-3 h per module including verification.

1. Spec first: scale table (meters!), colors (bright color-coding:
   shirt per actor identity, KHAKI pants — dark vanishes on asphalt),
   audit anchors (names as anchors: `Jeep.SeatL` etc.).
2. Build with primitives; origin-at-pivot for anything that rotates.
   Materials via `make_material` (sets BOTH Base Color and
   diffuse_color — workbench reads the latter, AGENTS.md #34).
3. Module contract: `build(ctx) -> dict of named objects` +
   `audit() -> list[str]`. The audit is part of the deliverable.
4. **VERIFY (the loop):**
   a. `test_assets_<module>.py`: programmatic checks (counts, pivots,
      hierarchy, materials) → CLEAN.
   b. Macro stills (well-lit, side view, close crop, other actors
      hidden — photobombs and backlights both lie).
   c. Own pixel read FIRST (`ascii_read.py`) — free, no sycophancy.
   d. Neutral VLM readback second ("list colors you see", never "is
      the blue shirt correct?").
   e. Iterate b-d until clean. Do not proceed on "probably fine".
5. **Delegation slot:** HIGH — one module per sub-agent with a TIGHT
   spec (function signature + scale table + deliverables). Sub-agent
   must run the same verify loop and report the stills' paths. Gate
   their module exactly like your own (the module contract makes this
   mechanical).

## Job 4 — Master scene assembly

**Trigger:** modules verified, ready to compose.
**Time budget:** 1-2 h.

1. `build_scene()`: clear → world → roots (belt/jeep empties) →
   modules in dependency order → humans LAST (they parent to jeep).
2. Parenting pattern for actor roots: `root.parent = X;
   root.matrix_parent_inverse = X.matrix_world.inverted();
   root.matrix_basis.translation = slot` — ONLY translation writes.
   Never touch a glTF-imported root's basis (retired path, but the
   scar stays: AGENTS.md #24).
3. `module_audits(ctx)` runs EVERY module's audit; abort on issues.
4. **VERIFY:** dry-run (`--dry-run`) → module audits CLEAN; then a
   previz-quality (240×135) 4-angle viewport capture for gross
   layout; own pixel read for the expected color blobs.
5. **Delegation slot:** MEDIUM — assembly itself is context-heavy
   (keep it), but a fresh-context design review of the integration
   plan catches constant bugs (the seat-z bug was caught this way).

## Job 5 — Animation pass

**Trigger:** scene assembled. The performance layer.
**Time budget:** 2-4 h (the heart of the sequence).

1. Root motion first (proven spine): run paths, boarding parabolas,
   chase/lunge offsets — location/rotation keys + `linear_fcurves`.
2. Limb layer (capsules): `CA.bake_run` (oscillating LINEAR keys,
   per-actor phase stagger, taper before pose lands) + `CA.pose_key`
   (one constant key; extrapolation holds it). LINEAR explicitly —
   Blender defaults to BEZIER.
3. Treadmill convention: the world belt scrolls (-y), the jeep
   parents actors; wheels rotate from belt distance.
4. Retiming rule: any phase change → re-derive every event t from
   the single t→frame map.
5. **VERIFY (motion needs probes, not eyes):**
   a. Programmatic: fcurve key counts, amplitude windows (peak |θ|
      within ±2 frames of a check frame — never one exact frame,
      sin zero-crossings false-positive), last-key ≥ pose frame.
   b. Render a KEYFRAME CONTACT SHEET (one image, frames sampled
      across the arc, labeled) — read it yourself: the leg scissor
      must be visible as alternating khaki columns under each torso.
   c. Neutral VLM on the contact sheet: "describe the motion arc"
      — then trust probes over prose.
6. **Delegation slot:** MEDIUM — delegate the *verification tooling*
   (contact-sheet stitchers, probe scripts) and per-shot micro-fixes
   with exact specs; keep the choreography decisions in-session.

## Job 6 — Physics pass (RB + particles)

**Trigger:** impacts/falls/sparks needed. **Time:** ~1 h.

1. RB bodies: create at rest, kinematic launch keys (3-frame burst)
   right before the `rb.kinematic = False` switch so the sim inherits
   velocity (AGENTS.md #26).
2. `bpy.ops.ptcache.bake_all(bake=True)` in background mode; per-
   object `PointCache.bake()` is gone in 4.5.
3. Physics LAST in animate() (bakes over the full range).
4. **VERIFY:** probe post-switch rotation (rot.x < -0.2 by f+30 =
      fell); `--no-physics` fallback flag so animation never depends
      on sim success.
5. **Delegation slot:** LOW — subtle, stateful, keep in-session.

## Job 7 — Camera work

**Trigger:** shot table exists. **Time:** 1-2 h.

1. World cams + TrackTo aim empties; jeep-parented cams get their
   rotation set and constraint influence zeroed.
2. Markers bind cams at shot starts (marker.camera) — one source of
   truth, asserted in master_audit.
3. Shake: relative to the TRACKING base (a static base clobbers
   dolly keys — the S2 bug). Shot-window-scoped only.
4. Per-shot intent check: does the frame SHOW the beat? (S6 black
   frame = camera inside the hood; S8 barricade out of window.)
   Write the intent into the shot table and audit against it.
5. **VERIFY:** per-shot still at the shot's mid frame at viewport
   quality; own pixel read (subject present, sized >2% frame height,
   not occluded); `scene.ray_cast` from camera through frame center
   for sightline checks (VLM misses these, scorecard #4).
6. **Delegation slot:** MEDIUM — a framing-audit sub-agent with the
   shot table + stills can score shots fresh (it has no commitment
   to your camera choices).
7. **Per-shot loop (session 9):** run this as the shot-by-shot
   finalize/freeze pipeline (Job 15) — camera fixes land in batches,
   one contiguous re-render per batch, review per shot, freeze when
   the shot passes. Expect 2-3 rounds; the VLM's composition critique
   flip-flops between rounds — treat it as ADVISORY and decide with
   your own pixel reads + the story intent (document overrides in the
   ledger when force-freezing).

## Job 8 — Verification gates (the loop's formalization)

**Trigger:** before ANY deliverable leaves the session.

Gate order (cheapest first):
1. **Programmatic audits** (module + master): deterministic, catch
   geometry/timing; ~10 s.
2. **Own pixel reads** (ascii_read.py grids): identity blobs,
   composition, pathology; ~0 s.
3. **Neutral VLM** static QA: colors-as-output, placements-not-
   interpretations; ~10 s/frame. Never dynamics (scorecard: ~20%).
4. **Motion probes + contact sheet** for dynamics.
5. **The killer-frame rule:** verify the EXACT frames the deliverable
   ships (the rig failure was found only at the hero frames; earlier
   thumbnails "verified" garbage). Never verify on a friendlier frame
   than the one the user will see.
**Delegation slot:** HIGH — fresh-context review sub-agents for design
specs and final gates (they don't share your sunk costs).

## Job 9 — Render (viewport only)

**Trigger:** gates passed. **Time:** ~10 min for 720 frames.

1. `--quality viewport` (960×540 workbench FLAT, neutral world) —
   NEVER EEVEE/Cycles for the sequence (AGENTS.md #31).
2. Chunked double-fork daemon:
   `setsid nohup python3 scripts/render_daemon.py --scene <scene>
   --output <out> --quality viewport --frames N --chunks 6
   --heartbeat /tmp/hb.json &`
3. Poll heartbeat; check per-chunk rc (fast chunk_done is a smell —
   the conflict-marker incident, AGENTS.md #30).
4. **VERIFY:** frame count == N; spot-read first/mid/last frames
   (pixel grid: color blobs present, background neutral gray);
   ffmpeg encode sanity (duration exact).
5. **Delegation slot:** none — launch + poll, stay in-session.

## Job 10 — Encode + mux + package

**Trigger:** frames complete. **Time:** ~5 min.

1. `bash scripts/encode_deliverable.sh <frames_dir>`: fades +
   crf 19 MP4, then dialog mux (adelay timecodes + apad to full
   length; frame→ms from the t→frame map).
2. Regenerate per-shot stills + storyboard sheet at the SAME quality
   as the video (the deliverable is one coherent package).
3. **VERIFY:** ffprobe durations (dialog version = full length, not
   the audio's tail); watch the anim once end-to-end yourself; spot
   VLM on 2-3 hero frames post-encode.
4. **Delegation slot:** none.

## Job 11 — Publish (git as the delivery channel)

**Trigger:** deliverables exist. **Time:** ~5 min. **EVERY micro step.**

1. Kit repo: code + docs only. Project repo (previz): deliverables
   under `download/<name>/` + README (what/why/how-to-view).
   NEVER mix them (the DELETE commit lesson).
2. `.gitignore` guards: output/, tools/, *.blend caches — but the
   DELIVERABLE dir in the project repo is tracked (it IS the product).
3. Commit message = what + why + the gotcha discovered.
4. **VERIFY:** `git push` exit 0 on both remotes; `git log origin/main`
   shows the commit; ls the remote tree via `git ls-remote` /
   re-clone smoke if paranoid. The user's visibility is GitHub —
   if it's not pushed, it doesn't exist.
5. **GitHub Release = upload AND publish (two separate calls).**
   Uploading assets via the API leaves the release in DRAFT —
   invisible on the public releases page (even the owner sees it
   only in the bottom "Drafts" section). After uploads finish:
   `PATCH /repos/<owner>/<repo>/releases/<id>` with `{"draft": false}`.
   Then **VERIFY via API**: the response shows `"draft": false` AND
   the expected asset count. Only then may the worklog say
   "release live" (v3.3 lesson: worklog said live; for hours users
   saw only v3.2 because the publish call never ran — tag, commits
   and assets were all fine). Two traps on the way: a PRIVATE repo
   returns 404 to anonymous curl, so authenticate before reading
   anything into a 404; and the GitLab mirror needs
   `git push gitlab --tags` separately (WAF 403 = retry 3-5x).
6. **Delegation slot:** none.

## Job 8a — The fail-closed gate suite (v3.4 law: advisory = not a gate)

**Trigger:** before ANY delivery render. Gates that only PRINT are
decoration -- v3.3 shipped blocked lenses and riding debris through
an advisory suite. The mandatory list (all abort the build):

1. framing_audit (subject projection + auto-fit)
2. axis_gate (screen-direction continuity across cuts)
3. occlusion_gate v2: lens-ray EVERY frame (hard < 0.30 m; warn band
   0.30-1.25 m with consecutive-quorum), NO skip lists, occluders =
   all renderable geometry, atmosphere (mist/skyline/dust) never
   occludes, dep.update() per frame (stale constraint matrices lie).
4. motion_frame_audit: MOTION_POLICY-declared statics (undeclared
   world-static + visible = rider violation), anim-end freeze outside
   the belt tree, FX lifecycle (scale-ON needs OFF or belt-compose).
5. coplanarity_audit + street ground-continuity (trench/void class) +
   thin-contrast streaming guard (curb-stripe aliasing class).
6. render_stats_gate on the RENDERED frames (flatness: the viewer's
   truth; declared FLATNESS_POLICY ranges for fades).
Clean-gate hygiene: a gate's "clean" status line is NOT a finding --
filter before the fail-closed switch, or success aborts itself.

**Treadmill law (the invariants):** belt streams backward, subject is
world-static; therefore world-static+visible = paces the subject;
belt children with no local keys = streams (correct); anim that ends
leaves the object frozen in whatever frame it ended in -- compose with
the belt (follow-keys at the belt's own keyframe cadence + linear
interp) or hide it. Belt-crossing deco (abandoned cars etc.) collides
with static cameras at dist_v3(t) == y_belt -- place in crossing-safe
windows, gate the danger bands.

## Job 12 — Kit maintenance (gotchas, merges, doc updates)

**Trigger:** a new failure mode understood. **Time:** 10-20 min each.

1. New gotcha → AGENTS.md numbered section + FINDINGS.md postmortem
   (what happened, root cause, the protocol change).
2. If tooling can encode the lesson, encode it (make_material sets
   diffuse_color; the viewport preset; conflict-marker grep).
   Policy belongs in docs AND code.
3. Merges: `grep -rn "<<<<<<<" scripts/` + `python3 -m py_compile` +
   one smoke render BEFORE trusting the kit (AGENTS.md #30).
4. **Delegation slot:** HIGH — doc reviews and "write this gotcha up
   clearly" are ideal sub-agent tasks (fresh words for fresh readers).

## Job 13 — Sub-agent delegation (the meta-job)

**Trigger:** context pressure, parallelizable work, or needed
fresh-context judgment. **Rules:**

1. **Size:** one module / one review / one probe; completable <5 min.
   Giant briefs time out (session-5 lesson).
2. **Brief:** self-contained — exact file paths, function contracts,
   scale tables, the verify loop THEY must run, and the worklog
   protocol (read /home/z/<repo>/worklog.md first; append their
   record; report paths + verdicts back).
3. **Timeout ≠ failure:** check the worktree for fresh mtimes/commits
   first — a killed sub-agent often finished its writes (user-noted).
4. **Gate their output** exactly like your own (audits + truth
   renders). Sub-agent code is YOUR code once merged.
5. **Best delegation fits (measured):** asset modules with tight
   specs; fresh-context design reviews (caught the seat-z bug);
   neutral verification passes; doc writing/review; research with
   live API probes. **Worst fits:** stateful multi-step animation,
   physics debugging, anything needing the session's full context.
6. 50+ rounds are affordable when each round is small, verified, and
   logged — the spine (this orchestrator) holds the state; the
   sub-agents hold the fresh eyes.

## Job 14 — Session wrap / handoff

**Trigger:** context ceiling or task complete. **Time:** 15-20 min.

1. worklog.md: append the session's Task ID record (template in repo).
2. PLAN.md: move track items, add new ones discovered.
3. HANDOFF.md: immediate next-session scope (environment bootstrap
   commands included).
4. .agents/SKILL.md: distill RECURRING meta-lessons (not events).
5. Final push to ALL remotes + gitlab mirror; verify remote state.
6. **VERIFY:** re-clone mentally: could a fresh session reach
   working state from GitHub alone? If not, fix that before ending.

## Job 15 — Per-shot finalize/freeze (shot_pipeline.py)

> Tool location: the escape project's `shot_pipeline.py` lives in the
> PREVIZ repo (`blender-escape-previz/scripts/`), not in this kit. The
> PATTERN is kit knowledge — this job documents it.

**Trigger:** shot table + first full render exist. **Time:** ~5 min per
polish round (one contiguous 720-frame render + 10-shot review).

The camera/cinematography loop, formalized (session 9):

1. `status` — which shots are draft/reviewed/frozen, frames on disk,
   content-hash staleness (per changed file).
2. `review --shot S# [--intent]` (or `--all`) — needs frames on disk
   (else prints the exact render command; review NEVER queues renders).
   Produces: 3 stills, subject-size profile, static-only VLM critique,
   append-only ledger entry (verdict/score/notes/hashes).
3. Fix cameras in the scene script (batch all pending fixes together).
4. `render --pending` — ONE contiguous daemon run over the union range
   (frozen shots' dirs are untouched); poll the heartbeat to `done`.
5. `distribute` — moves fresh frames into non-frozen shot dirs, wipes
   targets, verifies per-shot counts.
6. `freeze --shot S#` — requires last review verdict=pass AND the
   review's scene hashes matching current (drift => refuse);
   `--force` records the agent override reason in the ledger.
7. `encode` — stitches frozen dirs in shot order (fail-closed:
   contiguity, manifests, mixed-ext, duration assert), then
   `encode_deliverable.sh` (fades + dialog mux).
8. `storyboard` — contact sheet from frozen frames for publishing.

**Rules:** frozen dirs are never modified without `--force`; every
review appends (history survives rework); re-renders batch contiguous
(cold start dominates — 2.5 min vs 46 ms/frame); VLM = static
questions only; booleans keyed with f=1 anchors + CONSTANT
interpolation; near-field lens-blockers hidden (<2.2 m, shot-specific
keep-bands).

## Job 16 — the v3 recut flow (session 11: color discipline + timeline re-arch)

When a user feedback round changes the LOOK + the TIMELINE together
(this happened for v3: white-world colors + 30s→45s):

1. **Pixel-diagnose the complaint FIRST** (ascii_vision on old vs
   praised frames — "flat" / "washed" / "can't tell X from Y" become
   stdev + class-share numbers; the delta tells you exactly what to
   change).
2. **Design doc with a COMPLETE color table** (every material in every
   file — palette, hardcoded, FX, light bases) + timeline table +
   camera table + full recompute list; 2 review rounds (adversarial
   arithmetic — shot sums, event-in-shot containment, dialog
   end-to-onset clearances, camera coverage).
3. **Shading experiment** on the NEW palette (FLAT vs STUDIO, 4
   canonical frames, one build) before committing the look.
4. **Surgical scene fork** (copy the proven script, rename constants,
   re-derive — do NOT retype validated wiring). Gates travel with the
   code: retimed master_audit probes + NEW gates for the new invariants
   (phase-A follower caps, camera-key coverage, dist runout, lurch keys).
5. **Probe stills before full renders** (s1_probe pattern: one build +
   3 stills = 3 min; a full 1080f render is 7 min — pencil FOV math
   first, THEN render).
6. **VLM advisory pass at the end** with mandatory pixel verification
   of every flag (this round: 4+ "foreground zombie blocks subject"
   complaints, all false positives — the subjects were clean at pixel
   level).
7. Deliver: encode (fades) → dialog mux (verified table) → stills +
   storyboard + README + blend/glb → BOTH repos + platform download.

Dialog regen rule: if a line must shorten to fit a window, regenerate
at higher TTS speed (L3: 2.56 s @1.2x → 1.84 s @1.5x) and re-measure
with ffprobe — never assume.

## Job 17 (session 12): v3.2 deep-refinement round (RCA-first)

1. Pixel-diagnose the complaint frames + code-side RCA BEFORE any
   design (the 9-point table in DESIGN_v3_2 §0).
2. Fork the proven scene script (scene_escape_v3_2.py — lives in the
   PREVIZ repo `blender-escape-previz/scripts/`); derive the
   shot cut FROM the event table (verify: sums, contiguity, dialog
   onsets >=4f in-shot, impacts on cuts).
3. New gates in master_audit: coplanarity_audit + framing_audit
   (subjects per shot) + penetration + crowd (liveliness, speed
   variance) + FX coverage. FAIL-CLOSED before render.
4. AUTO-FIT pass in animate() (lens -> aim assist), gate re-verifies.
5. Shade experiment (A/B/D stills, one build) -> preset default.
6. Full render: --aa fxaa DELIVERY-ONLY (--aa off for probes; FXAA
   measured 2.7x raster cost, acceptable once per delivery).
7. flicker_probe on a STATIC window (moving-camera windows conflate
   motion with flicker -- S8b-class windows only).
8. Encode 24fps (NOT the blender_kit 12fps default!), mux dialog
   (45.0s assert), export stills+storyboard, blend+glb pack.
9. Deliverables: copy to download/ AND `git add -f` them -- the
   gitignored download/ silently ate the v3 MP4s (never again).

## Job 18 (session 17): the UAL hero-swap flow (wrapper layering + bake + A/B)

The round-5 upgrade path from proxy actors to rigged characters,
converged by 4 adversarial reviewers over 2 rounds (PLAN_v4 REV3).
The law, in order:

1. FORK + HERO_MODE flag first (capsule default = the regression
   baseline + the rollback lever; v3_x.py frozen; fail-closed both
   ways: mode mismatch vs present roots aborts).
2. Import + hygiene: fresh wrapper EMPTY named exactly `<Name>.Root`
   carrying the VERBATIM capsule root key contract; the rig is a
   wrapper child with facing flip (probed at bind, never hard-coded)
   + actor scale in matrix_parent_inverse (NEVER keyed); stray import
   meshes DELETED; single material datablock; action pool recorded;
   the importer's live slot CLEARED at build.
3. Early raster benchmark BEFORE choreography (budget +25%; the
   shadow-pass check: 3.9x = rejected, use discs).
4. The bake (ual_bake.py): live-eval per beat -> matrix_basis
   location + quaternion (scale pinned; pre-flight scan) ->
   LINEAR/CONSTANT keys EVERY frame f1..TOTAL (chunk-independent: the
   daemon rebuilds per chunk) -> quaternion sign canonicalization.
   Beats are HALF-OPEN [f0, f1); blend t REACHES 1.0 at the last
   blend frame ((f-f0)/(blend-1) -- the residue-snap class); hold
   beats carry blend=0; gunner pops are gap-aware (recoil recovers to
   0 exactly at the next shot). The fidelity gate must use the bake's
   ACTUAL resolver + assert the slot (vacuous-pass guard).
5. Determinism gates: in-process rebuild + save/load + chunk
   boundaries (all 0.00e+00 or fail).
6. A/B: TWO BUILDS (frozen tag vs new build -- NEVER a single-blend
   toggle), blind pair-preference both orderings, decision rule
   written BEFORE the test (preference >= 2/3 AND readability no
   regression AND gates green AND cost <= 1.5x AND zero anatomy
   defects); REJECT path = the tag stays live, the fork parks.
7. Full render + finalize + pack (slim the blend; glb from the LIVE
   scene -- reload-then-export wedges on huge actions; static pose if
   full-animation export wedges) + the two-call release law.

Postmortems: FINDINGS.md session-17; gotchas 66-72.
