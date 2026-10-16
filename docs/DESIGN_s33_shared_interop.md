# DESIGN s33 — Shared interop surface: vendor-sync with per-file canonical ownership

> Status: **FINAL r3** (r1: 3C+9I folded; r2: F1-F7 folded — see the
> D-revision log. Verdicts: r1 APPROVE-WITH-CHANGES, r2
> APPROVE-WITH-CHANGES, no architecture re-open.)
> Session 33, Track N. Owner: orchestrator.
> Implementation state: §6 step 1 (port-back) EXECUTED + validated
> (commit 5fc02d2).

## 0. Problem (user directive, 2026-09-30)

> "if we need a shared interop lib consider extracting that out into a
> shared lib so we can vendor that in everywhere instead of duplicating
> code that can potentially get stale or incompatible"

The kit and the previz repo share **44 files** under `scripts/`
(top-level + `blender_kit/`; extension-agnostic recount per review I1):
**23 byte-identical + 21 diverged**. The divergence has already
produced real defects (all verified by two independent review agents,
hunk-by-hunk, both directions):

| File | What the kit was MISSING | Class |
|---|---|---|
| `ual_bake.py` | the s31 laws: frozen-source blend (antipode crossing), arc-sign freeze, the `negate()`-returns-None hole, the eased f137-157 20f blend + beat-map rework | **P1** (kit reproduced the twisted-limb artifact) |
| `motion_frame_audit.py` | the 5.2 `iter_fcurves` conversion — on 5.2 `action.fcurves` is REMOVED, so the kit's copy crashed on ANY action (broader than multi-slot) + ctx-override policy resolution | **P1** (crash) |
| `framing_audit.py` | the v3.3 P0-4b behind-the-lens fix (z<=0 falsely in-frame) | **P1** (false-green gate) |
| `assets_ual_actors.py` | the s26 HeroZed zombie-family tint block (`ZOMBIE_TINT`/`TINTS`/`_tint_rgb`) — previz's copy is a strict superset; NO merge was needed (r1 correction) | P2 |
| `contact_discs.py` | the crowd v6 CrowdCache branch (`_sample_crowd`) | P2 |
| `render_daemon.py` | the v4 exit-deadlock watchdog (completion = outputs on disk) | P2 |
| `coplanarity_audit.py`, `occlusion_gate.py` | the v4 Contact.-disc exemptions | P2 (false positives) |
| `render_previz_truth.py` | `--stills-skip-existing`, `--stills-at`, `--shots`, `--crowd-mode`, the filmstrips.json merge law | P2 |
| `blrun.sh` | wording only (fail-closed gate identical) | P3 |

Conversely the kit is ahead on 10 files (apply_patch +416 lines,
viewport_capture, scene_schema, save_blend, validate_scene,
keyframe_contact_sheet, export_gltf, polyhaven, scene_template,
scene_interior_room) which previz is missing equally badly. **Both
review agents independently hunk-verified BOTH directions**: every
previz-only line in the kit-ahead 10 is the pre-catch-up idiom of a
kit feature (raw `action.fcurves` vs `iter_fcurves`, hardcoded
`'BLENDER_EEVEE_NEXT'` vs `EEVEE_ENGINE_ID`, plain importlib vs
`safe_import_scene`, direct `use_nodes` sets vs `ensure_use_nodes`) —
subsumed, safe to overwrite. Two sync-time behavior deltas for previz
to expect (documented, not losses): apply_patch auto-enables nodes on
non-node materials (previz raised), scene_schema `--output` becomes
optional (stdout mode).

## 1. Options considered (unchanged from r1 — survives review)

| | A. git submodule | B. separate interop repo | C. **kit-canonical vendor-sync** | D. pip package |
|---|---|---|---|---|
| Fresh-sandbox bootstrap | breaks (needs `--recurse-submodules`) | same as C | **unchanged** (clone + install.sh) | pip-from-git = network fragility |
| Blender import mechanics | unchanged if vendored | path churn | **unchanged** (flat `scripts/`, `sys.path[0]`) | bundled python isolated |
| GIT IS THE DISK durability | pointer refs only | content in 3 repos | **content in every repo** | package repo only |
| Change flow | bump refs everywhere | edit + sync | edit owner → sync (one command) | reinstall everywhere |

**Decision: C** — with r1 amendment: canonical ownership is **per
file**, not per repo (review I6). The kit owns the infra majority; the
previz repo owns the files whose payload is scene/choreography data.
One architecture, per-file direction.

## 2. The manifest (the contract) — schema 1

`tools/shared_manifest.json` (kit) + a synced copy
`scripts/shared_manifest.json` (each consumer — review I8: the
consumer-side check must run WITHOUT the kit present):

```json
{
  "schema": 1,
  "kit_commit": "<kit HEAD at emit>",
  "validated_blender": "5.2.2",
  "note": "Per-file canonical ownership. Fixes land in the OWNER repo
    (with a regression test), then sync_shared.py vendors them
    everywhere. The non-owner editing a manifest file must port back
    the same session (the dry-gates banner + provenance field make
    forgetting visible). previz's rollback-fallback exporter is
    deliberately NOT listed (frozen s31 state until the 3-green
    window closes).",
  "files": [
    {"path": "scripts/blender_kit/__init__.py", "owner": "kit", "sha256": "...",
     "tests": ["tests/test_export_previz_package.py::A"]},
    {"path": "scripts/ual_bake.py", "owner": "previz", "sha256": "...",
     "tests": ["scripts/test_ual_build_v4.py (previz)"],
     "note": "beat tables are choreography data (I6); engine/data
              split is the P2 path back to owner:kit"},
    ...
  ]
}
```

**Inclusion rule (r1 amendment I1, extension-agnostic):** every
regular file under `scripts/` present in BOTH repos today = the 44-file
set, minus deliberate exclusions:
- `scripts/export_previz_package.py` — previz's copy is the frozen
  rollback fallback; syncing it would defeat the rollback. Kit-only
  after the window closes; never a manifest entry.
- Nothing else. **43 entries.** (`blrun.sh` and
  `encode_deliverable.sh` ARE included — the r1 draft's "naturally
  excluded" claim for blrun.sh was factually wrong.)

**Ownership rule (r1 amendment I6):** `owner` defaults to `kit`.
`owner: "previz"` exactly for the two files whose payload is scene
data under review-round pressure: `scripts/ual_bake.py` (beat tables)
and `scripts/assets_ual_actors.py` (character/color tables — already
on the kit's VENDORED allowlist per `tests/test_kit_scope.py`; review
I5). The engine/data split (ual_bake engine → kit, beat tables →
previz-owned module, the crowd_v6.contract pattern) is the P2 path
that returns ual_bake to `owner: kit`.

**Test ownership (r1 amendment I4):** every entry carries a `tests`
field (test file + owning repo). Gap closed this session: the kit
gains a **bpy-free ual_bake-law test** — mechanism (r2 F6): the law
functions live inside `ual_bake.py` which imports bpy at module
level, so the test AST-EXTRACTS the pure functions (`_smoothstep`,
the arc-sign choice inside `_mix`, the frozen-source hold) into a
namespace and exercises them against hand-computed expectations in
the test_hero_gates.py model (33/33 without Blender). The ual_bake
entry's `tests` field lists BOTH previz's build test AND the kit law
test.

**Manifest ↔ kit-scope-law consistency (r1 amendment I5):**
`tests/test_shared_manifest.py` asserts every VENDORED-allowlist entry
that is a shared file appears in the manifest with `owner: "previz"`,
and no manifest entry matches a FORBIDDEN scope pattern.

## 3. The tool: `tools/sync_shared.py` (kit) — stdlib only

Three modes (hashlib, json, argparse, shutil, subprocess, ast —
sandbox 3.12 + Blender-bundled 3.11 verified):

1. **`--emit`** (kit): hash every manifest file (sha256), rewrite the
   manifest (+ `kit_commit`, `validated_blender`) and the
   machine-generated audit artifact `tools/shared_audit.json`
   (the both-repos intersection + identical/diverged classification —
   the §0 table's data, machine-counted so recount drift is
   impossible; r2 F7). **Import-closure check (r1 I3):** AST-scan
   every manifest file's local imports; a sibling module under
   `scripts/` that is absent from both the manifest and the exclusion
   list FAILS the emit (a future `blender_kit` package split can
   never ship half a package). A manifest entry whose file is
   MISSING from the owner repo fails the emit (r2 F2: owner-side
   delete/rename must go through a manifest edit first).

2. **`--check [--repo DIR]`** (anywhere; reads the VENDORED manifest
   copy — works in single-repo sessions). The classification truth
   table over {consumer file sha C, consumer record sha R, owner file
   sha O} (r2 F2 — complete):

   | C vs R | R vs O | C vs O | State | Action |
   |---|---|---|---|---|
   | == | == | == | IN-SYNC | none |
   | == | != | != | OWNER-AHEAD | run `--to` FROM THE KIT |
   | != | == | != | NON-OWNER-AHEAD | port back to the owner |
   | != | == | == | RECORD-STALE (informal sync) | `--adopt` (refresh the record) |
   | != | != | != | DIVERGED | manual merge |
   | file-exists, no record | — | — | NOT-SYNCED | `--include-new` or remove |

   In single-repo sessions O is unobservable: RECORD-STALE is
   indistinguishable from NON-OWNER-AHEAD and the banner prints BOTH
   remedies ("if these bytes came from the owner, run --adopt; else
   port back") — never a bare "port back" that would no-op (r2 F2).
   Owner file missing entirely (deleted without a manifest edit):
   OWNER-MISSING → loud error, the owner's `--emit` is the fix.
   Exit 0 clean; exit 1 with the classified report otherwise.
   `--adopt <file>`: the one-command record refresh for an informal
   sync (sets the record sha to the current file sha after confirming
   C == O when the sibling is present; refuses on divergence).

3. **`--to DIR`** (run in the kit; **bidirectional per entry** — for
   `owner: previz` entries it copies previz→kit and mutates the KIT;
   the per-file report shows the direction arrow; r2 F1). The loop is
   **copy → re-emit → vendor → check** (r2 F1): copy owner→non-owner
   for every entry (`shutil.copy2` — exec bits), **re-emit the kit's
   canonical manifest (re-hash every entry — the owner may have
   edited without emitting)**, vendor the refreshed copy to the
   consumer (the consumer's `scripts/shared_manifest.json` is
   GIT-COMMITTED — sync state must be rollback-able; r2 F3), then
   `--check`.
   **Three-way per-file guard (r1 C1):** overwrite ONLY if the
   consumer's current file sha == the consumer's own record sha
   (last-synced state) OR == the incoming owner bytes (already
   synced informally). Anything else → REFUSE with "non-owner ahead —
   port back first or --force". Never silently revert a committed
   hotfix.
   **State-file integrity (r2 F3):** before syncing, `--to` diffs the
   consumer's vendored copy against the kit's canonical manifest —
   schema mismatch or hand-edit drift → REFUSE "re-vendor the sync
   record first" (a hand-edited record can never launder a hotfix
   past the guard).
   **Deletion policy (N3):** manifest entries missing in the consumer
   are REPORTED, never created, unless `--include-new`. A record
   entry missing while the file exists → NOT-SYNCED → report/refuse
   (resolve via `--include-new`).

## 4. The sync workflow (the law — both AGENTS.md)

> **Shared-file changes land in the file's OWNER repo first** (with a
> regression test), then **`--emit`** (refresh the canonical manifest)
> **+ `tools/sync_shared.py --to <repo>`** (copy → re-emit → vendor →
> check) vendors them everywhere. Editing a manifest file in the
> non-owner repo is the EMERGENCY path only: fix there, then port
> back to the owner THE SAME SESSION — the drift surfaces (below)
> make a forgotten port-back visible in every dev loop and every
> exported package. For `owner: previz` entries the sync runs from
> the kit but pulls previz→kit — previz-only sessions make previz
> edits directly (it IS the owner) and the next joint `--to` lands
> them in the kit.

The s31 failure (laws ported to kit AGENTS.md as gotchas 111-113, code
never round-tripped) is this design's raison d'être — the mechanism,
not the convention, now carries the round-trip.

## 5. Enforcement (r1 amendment C3 — teeth on every surface)

1. **Kit side (blocking)**: `tests/test_shared_manifest.py` — (a)
   manifest shas == kit files (a forgotten `--emit` fails), (b) the
   import-closure check, (c) manifest ↔ kit-scope-law consistency
   (I5), (d) `--check --repo <previz>` with LOUD sibling discovery
   (`PREVIZ_REPO` env + heuristics; auto-skip prints why).
2. **Previz dev loop (BLOCKING — r2 F5 amended)**: `dry_gates_s30.py`
   currently has NO exit-code logic and NO callers (r2 verified — the
> r2-draft's "already exits on findings" premise was false). It
   GAINS: exit 1 on NON-OWNER-AHEAD/DIVERGED (after the classification
   lands), and step8_export_v6.sh runs it pre-export (the
   `--allow-drift` escape hatch documents a deliberate drifted
   export). The dev-loop cadence is thereby wired: step8 IS the
>   production surface, dry_gates its pre-flight.
3. **Previz production export (visible, non-blocking)**: the exporter
   records `shared_deps_synced: true|false|unknown` (+ drift list)
   into `previz.json` provenance next to `git_sha` — a drifted export
   is permanently visible in the shipped package (the review app can
   surface it later). **Hash set (r2 F4):** the exporter computes the
   transitive local-import closure of itself + the scene modules it
   imports (reusing `--emit`'s AST closure code — same tool, same
   law), INTERSECTS with the vendored manifest (~8-file export dep
   set: blender_kit, hero_gates, ual_bake, motion_frame_audit,
   framing_audit, coplanarity_audit, assets_ual_actors, ...), and
   hashes the SCENE-REPO side bytes. All-43 hashing would cry wolf on
   files the export never touches (alert fatigue kills the tooth);
   a hardcoded subset rots with the import graph. `unknown` when the
   vendored copy is absent (pre-first-sync). The drift reporter is
   itself deliberately manifest-exempt (the rollback-exporter
   exclusion) — the exclusion is PERMANENT: after the 3-green window
   previz's copy becomes a shim in BOTH repos and the file is
>   kit-only, never a manifest entry (r2 F7).
4. **Best-effort hooks**: `--to` offers `--install-hooks` (pre-commit
   in the consumer refusing commits that touch manifest files without
   a `PORTBACK_PENDING` marker) — best-effort only (git hooks are not
   cloned); surfaces 2+3 are the durable teeth.

## 6. Implementation order (each step committed + pushed)

1. **[DONE 5fc02d2] Port-back batch** — wholesale take of previz HEAD
   for the 10 previz-newer files (both review agents verified strict
   supersets; the one planned manual merge — assets_ual_actors — was
   deleted as unnecessary per fact-check). Validated: tier-A + tier-B
   byte-pin + T1 + hero_gates 33/33 + kit_scope.
2. **The tool + manifest**: `tools/sync_shared.py` per §3; `--emit`
   over the 43 entries; the kit's bpy-free ual_bake-law test (I4).
3. **Sync out**: `--to /home/z/blender-escape-previz` (10 kit-ahead
   files land; the 10 ported-back files are no-ops). Previz surface
   re-run: crowd v6 export (params_sha pin `1f581a18` MUST hold),
   test_sim, hero gates, dry gates.
4. **Rollback drill (r1 amendment I7)**: one smoke run of previz's
   OWN frozen exporter post-sync, while the rollback window is open —
   proves the fallback path works against the synced bytes.
5. **Enforcement**: kit test_shared_manifest.py; previz blocking
   dry-gates banner; step8 banner; exporter `shared_deps_synced`
   provenance field.
6. **Docs**: kit AGENTS.md law + `docs/SHARED_SYNC.md` (this doc
   promoted); previz AGENTS.md non-owner note; HANDOFF/PLAN.

## 7. Risks + mitigations

| Risk | Mitigation |
|---|---|
| Sync reverts a committed previz hotfix | The three-way C1 guard refuses unless consumer sha == last-synced sha or == incoming bytes |
| Kit's ported ual_bake breaks kit consumers | Bytes == previz HEAD (no-op for previz); previz's test_ual_build_v4 + the tier-B byte-pin are the regression surface; the kit gains the bpy-free law test |
| apply_patch/scene_schema sync changes previz behavior | Two documented behavior deltas (§0 last para); previz dry gates + full surface re-run in step 3 |
| Manifest rot (new files never added) | Import-closure check in `--emit` + the both-repos INFO probe in `--check` |
| Kit splits blender_kit into a package | Import-closure check fails the emit until the new submodule is added |
| Consumer deletes a manifest file deliberately | Deletion policy (§3): reported, never resurrected without `--include-new` |
| Blender version skew (4.5 vs 5.2) | Manifest records `validated_blender`; tier-B already pins blender_version; the kit's compat shim covers 4.x↔5.x |
| Sync lands mid-rollback-window | Step 4 rollback drill (previz's frozen exporter smoke post-sync) |
| Same file different path across repos (kit `tests/test_hero_gates.py` vs previz `scripts/test_hero_gates.py`) | Known limitation (review N5): tests are DOCUMENTED (the `tests` field), not synced; the manifest keys kit-relative script paths only |

## 8. Out of scope (explicitly)

- previz-review's TypeScript interfaces (s32 decision stands; a
  doc↔interface drift check is a P2 candidate).
- crowd_v6 / blender-crowd-kit as a NAMESPACE (s27 law). **Third
  consumer (r1 amendment I9)**: when blender-crowd-kit graduates, it
  becomes another `--to` target with its own vendored manifest copy;
  crowd-domain files (`crowd_fields.py`, `gait_modifiers.py` + their
  tests, byte-identical today) stay `owner: kit` until the crowd kit
  graduates its own engine home (the gait_modifiers lift precedent,
  in reverse). Vendoring BYTES into consumers never violates s27 —
  the law forbids crowd code in the KIT'S namespace, not kit bytes in
  crowd-kit.
- The previz rollback exporter (frozen by design until 3-green; then
  a shim, then unmanaged).

## D-revision log (r1 → r2)

- **I1**: 42→44 files / 22→23 identical / 20→21 diverged
  (extension-agnostic recount); manifest 41→43 entries; blrun.sh +
  encode_deliverable.sh included; the false "naturally excluded"
  claim deleted.
- **I2**: the assets_ual_actors MERGE instruction deleted — previz's
  copy is a strict superset; wholesale take (already executed).
- **Fact-fix (2a)**: "cross-key quaternion sign canonicalization"
  dropped from the ual_bake row (kit has had a byte-identical
  `_canonicalize_quats` since s17); the eased-blend/beat-map rework
  added; §7's "additive guards" claim replaced with the honest
  regression-surface argument.
- **Fact-fix (2b)**: motion_frame_audit crash scope widened (any
  action on 5.2, not just multi-slot).
- **Fact-fix (4)**: `crowd/` is kit-only (previz has no scripts/crowd/);
  exclusion justification corrected.
- **C1**: three-way per-file overwrite guard (consumer sha ==
  last-synced OR == incoming) + resumable sync-state.
- **C2**: vendored consumer manifest copy = the sync-state; per-file
  classification IN-SYNC / OWNER-AHEAD / NON-OWNER-AHEAD / DIVERGED /
  NOT-SYNCED.
- **C3**: dry-gates banner BLOCKING; step8 banner non-blocking;
  `shared_deps_synced` provenance field; loud sibling discovery;
  best-effort pre-commit hooks.
- **I3**: import-closure check in `--emit`.
- **I4**: kit bpy-free ual_bake-law test; manifest `tests` field.
- **I5**: manifest ↔ test_kit_scope VENDORED consistency check.
- **I6**: per-file `owner` field (schema 1); ual_bake + 
  assets_ual_actors `owner: previz`; engine/data split = the P2 path.
- **I7**: kit-ahead-10 hunk-verification claimed (both agents);
  rollback drill step 4.
- **I8**: consumer-side vendored manifest + standalone check.
- **I9**: third-consumer subsection.
- **N2/N3/N4/N5**: copy2/exec-bit, deletion policy, Blender pin,
  path-alias limitation.
- **r2 F1**: `--to` = copy → re-emit → vendor → check; bidirectional
  per entry (direction arrows in the report); the kit's canonical
  manifest doubles as its own consumer record for owner:previz
  entries; `--emit` added to §4's law loop.
- **r2 F2**: complete classification truth table (+RECORD-STALE,
  +OWNER-MISSING); `--adopt` remedy; both-remedy banner text in
  single-repo sessions.
- **r2 F3**: `--to` cross-checks the vendored copy vs canonical
  manifest (hand-edit defense); record-entry-missing = NOT-SYNCED;
  the vendored copy is git-committed.
- **r2 F4**: `shared_deps_synced` hashes the AST-closure∩manifest on
  the scene-repo side; `unknown` pre-first-sync; the reporter's own
  exemption stated.
- **r2 F5**: the false "dry_gates already exits" premise deleted;
  dry_gates GAINS exit-1-on-drift + step8 pre-flight wiring +
  `--allow-drift` escape; exporter-exclusion disposition stated
  (permanent, shim in both repos post-window).
- **r2 F6**: the ual_bake `tests` example now includes the kit law
  test; the law test's AST-extraction mechanism specified.
- **r2 F7**: machine-generated `tools/shared_audit.json` checked in
  by `--emit`; vendored-vs-native policy sentence (VENDORED entries
  are previz-born keepers pending their lift; owner:kit entries are
  kit-native); OWNER-AHEAD remedy wording ("run --to from the kit").
