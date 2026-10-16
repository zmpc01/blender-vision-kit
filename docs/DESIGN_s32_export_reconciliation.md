# DESIGN — Session 32 export pipeline reconciliation (Track M)

> Status: FINAL — round-1 peer review complete (design auditor +
> fact-checker, reports at `docs/reviews/s32_design_review_r1.md` and
> `docs/reviews/s32_factcheck_r1.md`); 3 critical + 8 important
> findings folded in as D-revisions below.
> Supersedes the session-31 audit where the numbers below disagree.
> Kickoff: `KICKOFF_export_reconciliation.md`. Decision trail:
> `blender-agent-meta/decisions/2026-09-28_track-adjustment_v3_final.md`.

## 0. Ground truth RE-DERIVED (2026-09-29, this session)

The kickoff's LOC expectations match HEAD exactly (kit exporter 1431,
previz exporter 1927, hero_gates 711, USD hooks 1056/1056 identical,
blender_kit 986/986 identical, crowd stub 1350 bytes, STORY_SOURCES 21
entries — all verified). BUT three material facts moved since the
session-31 audit that produced the "19 gates" label:

1. **The previz exporter now has 21 numbered gates, not 19.**
   Session-31 commits (AFTER the v3 decision doc) added:
   - gate 20 MOTION CONTINUITY (bf1fc00 — gunner sprint-transition
     sweep + recoil-pop sign-flip classes)
   - gate 21 CAPSULE ORIENTATION (a33297a — the S11 "standing
     sideways, sliding without turning" class)
   Both live in `hero_gates.py` (`motion_continuity_problems`,
   `capsule_orientation_problems`). hero_gates.py grew to 711 LOC and
   gained a test file (`scripts/test_hero_gates.py`, 288 LOC).
   Gate numbering: 0 version-drift, 1-14 core, 15-17 crowd v6,
   18/19 hero aim-coherence + FX off-state, 20 motion continuity,
   21 capsule orientation.
2. **A v6_1 staged package exists** (generated 2026-09-28T06:13:39Z at
   previz git 99b3c0c — AFTER the session-31 scene/hero/crowd fixes).
   Only `.agents/SKILL.md` changed in previz since 99b3c0c, so **v6_1
   — not v6_0 — is the correct staged ground truth** for the current
   scene_escape_v5 + current exporter. v6_0 (generated at 2b69718,
   pre-session-31-fixes) is stale as a byte-comparison target.
3. **The kit's stale copy already HAS the version-drift gate, the
   pool-action purge, and `--crowd-mode`** (kickoff claimed missing).
   The true delta (diff -u = 649 lines, 514+/18−) is:
   (a) `_glb_scale_track` + `_clip_track_from_cache` helpers
   (b) belt DESCENDANT-set fix in `_glb_rider_audit` (s26 v6 fix)
   (c) gate-14 props-collection fix (parent-is-joint regardless of
       animation; static bone-child = fail-closed finding)
   (d) `problems` list hoisted before collectors (crash-class fix)
   (e) character `role` field (CHARACTER_ROLES, s26)
   (f) the crowd v6 JSON block collector (`_crowd_agent_name`,
       `_crowd_kd_rows`, previz["crowd"] + schema 2.2 bump)
   (g) gates 18/19/20/21 (hero_gates integration)
   (h) gates 15/16/17 (crowd_v6.gates integration)
   (i) docstring/schema-print updates

All 18 deleted lines in the diff are strict upgrades; **nothing
kit-specific is lost by taking the previz version wholesale.**

## 1. Decisions

### D1 — Reconcile by WHOLESALE COPY of the previz exporter into the
kit's existing file, then apply kit-specific adaptations as separate
runnable commits.

Not a piece-by-piece port into the stale base. Rationale: previz's copy
is the production code that generated v6_1 (all 21 gates green); the
kit's base is a strict ancestor; wholesale copy eliminates transcription
risk and guarantees semantic parity. The kickoff's intent — same
filename (README contract reference), all gates, contract-driven — is
honored. Commit sequence (each leaves a runnable exporter):

- **C1** (Phase 0): `scripts/scene_contract.py` — 3 Protocols + crowd
  engine registry + discovery helpers (see D3).
- **C2** (Phase 0.5): this design doc (doubles as the delta inventory).
- **C3**: `scripts/hero_gates.py` + `tests/test_hero_gates.py` verbatim
  ports from previz @ HEAD (bpy-free, self-contained).
- **C4**: exporter wholesale copy + `--scene-dir` flag (D4).
- **C5**: module-loading discipline — `--crowd-plugin` importlib load
  (D2) + hero_gates private-name deterministic load (D5).
- **C6**: STORY_SOURCES ↔ scene_contract sync check + unknown-declared-
  constant fail-closed check (D6).
- **C7** (Phase 1.5): `tests/test_export_previz_package.py` + fixture
  scene + `tests/baselines/` (D7).
- **C8** (Phase 2): previz `step8_export_v6.sh` → kit exporter with
  `--crowd-plugin`; acceptance result documented.
- **C9** (Phase 3): `docs/previz_package.md` + previz-review README
  stub + META-PLAN §6 link.
- **C10**: session-end artifacts (worklog/HANDOFF/PLAN/SKILL/meta).

### D2 — crowd_v6 loads ONLY via `--crowd-plugin <path>` (session-27
directive). Mechanism:

- Early fail-closed: `--crowd-mode v6` without `--crowd-plugin` →
  error pointing at the previz repo path. Library fallback:
  `scene_contract.CROWD_ENGINE_PATHS.get(mode)` before erroring.
- Late fail-closed: `ctx["crowd_cache"]` exists (scene ran v6) but no
  plugin was resolvable → error (future scene defaulting to v6).
- Load via `importlib.util.spec_from_file_location("crowd_v6",
  <path>/__init__.py, submodule_search_locations=[<path>])`, but
  **reuse `sys.modules["crowd_v6"]` if the scene already imported it**
  (it does, inside animate/_run_crowd) — avoids double instances of
  module-level state. WARN if the cached module's `__file__` is not
  under the given plugin path (config mistake smell).
- crowd_v6 STAYS in the previz repo. Kit's `scripts/crowd/__init__.py`
  stub untouched.

### D3 — `scripts/scene_contract.py` per the kickoff sketch, corrected
for reality:

- Gate families: core 1-14 (always) / crowd 15-17 (skip unless v6 crowd
  block present) / hero-FX 18-19 (skip unless FX_EVENT_WINDOWS; gate 18
  also needs per-character `boards_at` from the characters registry —
  NOT a module constant) / motion-continuity 20 (hero rig, boards_at) /
  capsule-orientation 21 (crowd, additive — no Zed anchors → n/a).
- Protocol method signatures match the REAL scene-module interface:
  `build_scene() -> ctx dict`, `animate(ctx, start_frame, n_frames)`,
  `emit_sfx_events(ctx, output_dir)`. (The kickoff sketch's
  `build(self, scene) -> None` does not match any real scene module.)
- `story_attribute_names()` derives the 21 attrs from
  `CoreSceneContract.__annotations__` (runtime discovery source).
- `KNOWN_NON_STORY` exemption map for module-level uppercase names that
  are NOT story payload, each with its destination documented:
  FPS, RNG, SHOTS_V3 (→ top-level shots), _V32_CTX, BOARD_UAL_Z,
  CHARACTER_ROLES (→ characters registry), CROWD_MODE (→ crowd
  contract), CROWD_TIER_PINS (→ crowd block pins), FX_EVENT_WINDOWS +
  FX_WORLD_LITTER (→ hero contract), module aliases (CA/CH/EL/ST/VE/FA/
  CPA — resolve to module objects), legacy `*_V2` names.
- Crowd engine registry: path-based, `register_crowd_engine(name, path)`.

### D4 — `--scene-dir <path>` flag: where to import the scene module
from. Default: the exporter's own scripts dir (kit-local scenes). When
absent but `--crowd-plugin` given: derive `dirname(<crowd-plugin>)`
(crowd_v6 lives in the scene repo's scripts/). This makes the
kickoff's acceptance command work verbatim while keeping an explicit
override. The derived path is printed. Scene modules insert their own
dir into sys.path themselves (law 107 unchanged).

### D5 — hero_gates loads from the KIT's own scripts dir under a
PRIVATE module name (`_kit_hero_gates`) via importlib — NOT a bare
`import hero_gates`. Why: the scene module (previz side) does
`from hero_gates import smoke_key_plan` inside its FX build and caches
previz's copy in `sys.modules["hero_gates"]`; a bare import in the
exporter would silently run the PREVIZ copy, defeating the
kit-as-source-of-truth goal (identical today, drift hazard tomorrow).
Private-name load = deterministic, no clobber, no ordering dependence.
If `hero_gates.py` is missing from the kit's scripts dir → gates 18-21
skip with a WARN (fail-closed per kickoff: loud, never silent).

### D6 — STORY_SOURCES stays the runtime (attr → JSON key) table, and
gains two contract checks:
1. Import-time sync: attrs in `CoreSceneContract.__annotations__` ==
   attrs in STORY_SOURCES (fail-closed with a clear message — adding a
   contract attr requires adding its mapping, and vice versa).
2. Unknown-declared-constant check: any module-namespace uppercase
   name that is not a contract attr, not in KNOWN_NON_STORY, and not a
   module object → fail-closed ("scene declares X but STORY_SOURCES has
   no mapping — the nothing-left-out law"). This automates the audit
   that the 14→21 growth had been slipping through.

### D7 — Acceptance test + regression baseline:

- **Ground truth = staged v6_1** (current exporter + current scene;
  only a docs commit landed in previz since). Compare kit export vs
  v6_1; expected deltas ONLY: `git_sha` (kit repo vs previz repo —
  _git_sha reads CWD), `generated_at`, `package_id`, `name`.
- If other deltas: classify (1) provenance (2) bug — fix before
  continuing (3) new key — decide + document. Triangulate with a fresh
  previz-repo export if needed.
- **Checked-in baseline = the kit's first green export** (minus
  provenance fields), per the v3 decision doc ("first migrated export
  IS the new baseline"). The kickoff's "use v6_0 as baseline" is
  stale — session-31 scene fixes make current output ≠ v6_0; pinning
  v6_0 would fail the suite on first run.
- 3-layer pin: byte-identical previz.json (json.dump indent=1
  sort_keys=True) + crowd params_sha unchanged (f6850b78 for v6_0 /
  1f581a18 for v6_1 lineage — the CURRENT scene pins v6_1's) + all 21
  gates green.
- Rollback: previz repo's exporter stays the production fallback for 3
  consecutive green kit exports (untouched this session except
  step8_export_v6.sh).

### D8 — Phase 3 docs corrected for 21 gates; TypeScript interfaces in
`previz-review/src/lib/previz.ts` STAY the machine-checkable source of
truth (no codegen). previz-review README contract section replaced
wholesale with a stub + link. META-PLAN §6 links to the kit doc.

## 2. Risks

- **R1 Export runtime** on this box (2 cores / 3.9GB): scene build +
  crowd sim + UAL bake + glTF + 21 gates. Prior sessions: glTF ~2.3min
  post-purge; full pipeline unknown here, budget 10-40 min, single
  long bash call. Split trigger per kickoff if Phase 1 exceeds budget.
- **R2 cache_sha reproducibility**: crowd sim is seed-pinned and
  deterministic in principle; if the fresh export's cache_sha differs
  from v6_1, investigate before relaxing anything.
- **R3 double-module hazards**: handled by D2 (sys.modules reuse) and
  D5 (private name).
- **R4 blender_kit drift**: identical at HEAD both repos; my changes
  don't touch it; re-verify at session end.

## 4. Round-1 peer review outcome (folded in — FINAL revisions)

**C1 (critical) — version-drift gate repoint**: `_latest_scene_module()`
must scan the RESOLVED scene dir (from --scene-dir / plugin derivation),
not the exporter's own dir (kit/scripts has no scene_escape*.py → the
gate would silently no-op). Landed in C4.

**C2 (critical) — sys.path precedence + shadowing surface**: 7 local
modules the scene transitively imports DIFFER between kit/scripts and
previz/scripts (assets_ual_actors, contact_discs, coplanarity_audit,
framing_audit, motion_frame_audit, occlusion_gate, ual_bake — previz is
newer in all). Resolution order in the kit exporter: resolved scene dir
at `sys.path[0]`, kit's own scripts dir AFTER it; fail-closed assertion
post-import that `mod.__file__` is under the scene dir. blender_kit
stays the kit's copy via the sys.modules cache (top-level import from
blrun.sh PYTHONPATH; byte-identical both repos).

**C3 (critical) — two-tier test design**: `test_export_previz_package.py`
has (a) a FIXTURE-scene structural tier (own mini baseline; proves gate
run/skip laws + contract checks + JSON shape on a scene we control) and
(b) a REAL-scene tier (previz repo present → export + compare against
the checked-in first-green-export baseline modulo provenance; auto-skip
when the previz repo is absent). No single baseline confusion.

**I1/F — KNOWN_NON_STORY redesigned**: the unknown-declared-constant
check triggers ONLY on names bound to story-DATA types
(list/dict/tuple/str/int/float) — modules (CA/CH/EL/ST/VE/FA/CPA/UA),
classes (mathutils.Vector), callables and instances (random.Random RNG)
auto-pass. Explicit exemptions: FPS, SHOTS_V3 (→ top-level shots),
BOARD_UAL_Z, CHARACTER_ROLES (→ characters registry), CROWD_MODE,
CROWD_TIER_PINS (→ crowd block), FX_EVENT_WINDOWS, FX_WORLD_LITTER
(→ hero contract), plus legacy names: `*_V2` suffix + v1's CAMS/JEEP_X.
Verified complete against all 7 scene_escape*.py modules (AST scan in
`docs/reviews/s32_factcheck_r1.md`).

**I2 — plugin path mismatch upgraded from WARN to fail-closed ERROR**
(gates would run plugin code X against scene-engine data Y — silent
wrong results otherwise). The resolved engine is auto-registered into
`scene_contract.CROWD_ENGINE_PATHS` at export time (the registry
becomes real, not decorative). Late fail-closed retained: crowd cache
present but no plugin resolvable → error. Fact-check precision: v5
imports crowd_v6.contract at MODULE level (line 387) — sys.modules
always has crowd_v6 after scene import; the loader's reuse path is the
normal path, cold-load only for plugin-without-scene flows.

**I3 — importlib package-load order**: create module → register in
sys.modules["crowd_v6"] → exec_module (the package eagerly imports its
own contract submodule; registration must precede exec). All 4 bare
import sites (crowd_v6, .clips, .contract, .gates) rewire through the
loader.

**I4 — acceptance run pattern**: nohup + poll (tool calls cap at 10
min; the full pipeline is 10-40 min).

**I5 — acceptance env mirrors step8**: CROWD_CACHE_DIR, RB_CACHE_DIR,
BLENDER_BIN exported for the acceptance run (production-path parity).

**I6 — previz_usd_hook same hazard class as hero_gates** (loads
previz's copy post-scene-import with --usd-sidecar; byte-identical
today). Documented; fix deferred (sidecar off by default).

**I7 — number corrections**: previz exporter docstring says "17
numbered gates" (stale — the kit port's docstring says 21);
test_hero_gates.py is 670 LOC (not 288); diff stat 513+/17−.

**I8 — plugin path accepts dir OR .py file** (file → its dir's parent
is the package dir; dir → itself). Derived scene dir adjusts
accordingly.

**Fact-check confirmations (no change needed)**: kit STORY_SOURCES
already 21/21 byte-identical with previz (kickoff's "may be shorter"
caution moot); gate run order is 18/19/20/21 THEN 15/16/17 (numbering
≠ execution order — port keeps both verbatim); hero_gates import fires
during animate's FX keyframing (the sys.modules trap is real and
doubly locked); all 9 crowd ctx keys stashed by the scene; test_hero_gates.py
33/33 green under plain python3 (numpy 2.1.3); --factory-startup
verified non-issue (live-probed); blrun.sh copies identical modulo one
log string.


## 5. Out of scope (unchanged)

- Phase 4 viewer (session-18 directive — dev-only forever).
- Vendoring crowd_v6 (session-27 directive — plugin pattern only).
- previz-review app UX (web editor team's deliverable).
- Codegen from TypeScript interfaces.
- Reducing previz's exporter to a shim (only after 3 green exports,
  a later session).
