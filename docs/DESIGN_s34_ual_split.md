# DESIGN — ual_bake engine/data split (s34)

> Status: v3 (review r2 folded — docs/reviews/s34_ual_split_review_r2.md,
> REQUEST-CHANGES-narrowly: C1+I1-I4+N1-N4 all folded; r2 verified the
> r1 criticals genuinely dead + the migration choreography correct
> against the real tool code). Owner-track: export/interop (session 34).
> Implements the s33 design's I6/P2 path (docs/DESIGN_s33_shared_interop.md):
> "The engine/data split is the long-term fix ... returns ual_bake to
> `owner: kit`."

## 1. Problem

`scripts/ual_bake.py` (629 LOC, previz) is TWO things in one file:

- **ENGINE** (~440 LOC): the two-phase bake machinery — Beat, the
  s31 laws (eased blends, the per-bone arc-sign freeze, quaternion
  sign canonicalization, the frozen-source hold), _preflight,
  _assign_action, _record_table, _mix, _canonicalize_quats,
  _write_baked_action, _fidelity_gate (sections 1-2), _make_resolver,
  bake_actor, and the gap-aware recoil-pop resolver.
- **DATA** (~190 LOC): the escape project's choreography — the four
  beat tables (frames FROZEN to the shared sfx/dialog/event tables),
  _pop_footprints, the fidelity sample frames, the actor roster, the
  HeroZed f512 grab-reach assert (fidelity-gate section 3), and the
  bake_all composition.

Consequences of the current shape:

1. **The kit's own law test extracts from a file it does not own**
   (tests/test_ual_bake_laws.py AST-extracts `_mix`,
   `_canonicalize_quats`, `Beat`, `_make_resolver` from the manifest
   copy). The kit cannot evolve the engine without a port-back
   round-trip through previz.
2. **Choreography hotfixes under review-round pressure route through
   the infra repo** (the s33 design's I6 rationale).
3. **The third-copy drift class stays alive**: the vendored
   blender-crowd-kit carries a stale pre-s31 fork of the whole file
   (s34 audit S1 — latent, never binds; disposition stays theirs).

## 2. The split (crowd_v6.contract pattern)

### 2.1 ENGINE — kit `scripts/ual_bake.py` (owner flips to `kit`)

Keeps (byte-identical, pure move): Beat, _all_bones, _preflight,
_assign_action, _record_table, _mix, _canonicalize_quats,
_write_baked_action, _make_resolver, _SAMPLE_BONES (r1 I2 — the
Rigify DEF-* sample set is rig-family engine data; probe_v4a also
reads it), constants BLEND_DEFAULT, SCALE_TOL.

Changes (NOT byte-identical — the law TEXT inside moves verbatim,
signatures change):
- `bake_actor(ctx, name, beats, resolver, samples, total, post_check=None)`
  — `total` is a REQUIRED keyword (r1 I4: no 1080 default hiding in
  the engine); `post_check` threads to the fidelity gate.
- `_fidelity_gate(..., post_check=None)` (r1 I1 + r2 N1): sections 1-2
  (the live-reference re-eval + the vacuous-pass-guarded compare) move
  verbatim; section 3 (the HeroZed/f512/0.35 m grab-reach assert —
  actor name + sample frame + choreography threshold) is REPLACED by
  the hook, placed AFTER the compare loop and BEFORE the final
  worst-delta print (stdout order preserved):
  ```python
  if post_check is not None:
      findings.extend(post_check(name, arm, scene))
  ```
- `_gunner_resolver` is generalized to
  `pop_resolver(base, shots, hold_from, shoot, aim, src_extent=3.0,
  max_extent=6, blend_in=2)` (r1 I3 + r2 N4): takes the ALREADY-BUILT
  base resolver; the `f >= 157` hardcode becomes `hold_from`; the
  Shoot clip's source-frame span (`3.0`), the extent cap + the
  trailing-shot gap (`6` — the same constant serves both), and the
  blend-in lead (`2`, whose ramp divisor is `blend_in - 1` — a naive
  `/blend_in` halves the ramp) become explicit parameters the data
  passes. The LAW body stays: half-out/half-recover sawtooth,
  later-shot-wins overlap resolution, blend-in only when the previous
  pop settled.
- `TOTAL` and `FPS` move OUT (scene-vintage; FPS is dead code —
  no external readers, verified).
- The engine docstring's stale `[1..1080]` prose becomes `[1..total]`
  (r1 N1); the beat-map table moves to the data module.

Loses (moves to the data module): the four beat-table functions,
_pop_footprints, bake_all, the samples tuple, the actor roster, the
HeroZed section-3 assert.

`_make_resolver`'s `name` parameter is dead-but-kept (r1 N6 — used
only in error strings historically; a drive-by removal is out of
scope for a behavior-invisible change).

### 2.2 DATA — previz `scripts/ual_beats.py` (previz-only, like scene_escape_v5.py)

```python
"""ual_beats.py — the escape project's hero choreography (v4+v5 share
these tables; frames FROZEN to the shared sfx/dialog/event tables).
Engine: ual_bake (kit-owned). This module is DATA + composition."""
import bpy                     # _grab_reach_check's view_layer updates
from ual_bake import Beat      # r2 C1: the tables construct bare
                               # Beat(...) at function scope — a
                               # function-local engine import inside
                               # bake_all NEVER binds the name; the
                               # module-level import does (and makes
                               # ual_beats bpy-bound for importers —
                               # fine for scenes; the TEST extracts
                               # AST-wise, never imports)
TOTAL = 1080
ACTORS = ("Driver", "Girl", "Gunner", "HeroZed")
SAMPLES = (1, 60, 120, 133, 140, 145, 160, 174, 190, 360, 500,
           505, 512, 520, 546, 600, 760, 830, 1080)

def driver_beats(): ...      # was _driver_beats (public now)
def girl_beats(): ...
def gunner_beats(aim="Pistol_Aim_Neutral"): ...
def herozed_beats(): ...
def pop_footprints(bursts): ...   # was _pop_footprints (docstring
                                  # cleaned per r1 N4)

def _grab_reach_check(name, arm, scene):
    """The f512 hand-contact assert (was fidelity-gate section 3)."""
    ...  # returns [] unless name == "HeroZed"

def bake_all(ctx, bursts):
    """Bake all 4 actors + run gates (drop-in for the old
    ual_bake.bake_all)."""
    import ual_bake as UB          # the engine (scene-dir superset
                                   # copy; byte-identical to the kit's)
    ...  # preflight over ACTORS, specs, resolvers:
    ...  #   gunner_base = UB._make_resolver(gunner_beats(aim_act), "Gunner")
    ...  #   UB.pop_resolver(gunner_base, shots, hold_from=157,
    ...  #                   shoot=shoot_act, aim=aim_act)
    ...  # bake_actor(..., total=TOTAL, post_check=_grab_reach_check)
    ...  # + the session-23 memory law (orphans_purge per actor)
```

Not a manifest entry (present in previz only — the manifest's
inclusion rule is "files in BOTH repos"). previz owns it outright.

### 2.3 Call-site changes (previz)

| Site | Today | After |
|---|---|---|
| scene_escape_v5.py :2162 block | `import ual_bake as UB` + `UB._driver_beats` … | `import ual_beats as UB` + `UB.driver_beats` … (the audit's default-Pistol `UB._gunner_beats()` read is PRE-EXISTING benign divergence from the bake's Rifle aim — r1 N2: noted, NOT fixed mid-swap) |
| scene_escape_v5.py :2449 (bake_all) | `UB.bake_all(ctx, MUZZLE_BURSTS_V3)` | same call, `import ual_beats as UB` |
| scene_escape_v4.py :1698 + :1979 | same two shapes | same swaps |
| probe_v4a_bakeunit.py | engine fns + `_pop_footprints` + `_gunner_resolver(beats, shots)` (2-arg) + 5-positional `bake_actor` + 8 beat-table reads (:82, :222, :396-399, :419-422) + a second import site | REAL edits (r1 I4 + r2 N3): the pop call becomes `pop_resolver(_make_resolver(beats, "Gunner"), shots, hold_from=157, shoot=..., aim=...)`; `bake_actor(..., total=1080)`; `_pop_footprints` → `pop_footprints`; the 8 table reads → the public names; engine-only imports keep `ual_bake` |
| probe_v4b_dual.py | (verify at edit time) | same treatment |

## 3. Behavioral-equivalence proof (the acceptance)

- **Step 0**: tier-B green at HEAD recorded BEFORE any edit (r1 I6;
  already true this session — the re-baselined pin, code_sha
  `c6b9081e…`, is the recorded green state).
- kit `tests/test_ual_bake_laws.py` — L1–L4c pins hold UNCHANGED
  (the extraction targets `_mix`/`_canonicalize_quats`/`Beat`/
  `_make_resolver` are byte-identical moves; the header note updates
  to "the KIT'S OWN engine copy").
- previz `scripts/test_ual_beats.py` (NEW, bpy-free, r1 I5 + r2
  C1/I4): a TWO-SOURCE AST extraction bound into ONE exec namespace:
  from the engine `scripts/ual_bake.py` — `Beat`, `BLEND_DEFAULT`,
  `_make_resolver`, **`pop_resolver`** (r2 I4: T3's pins ARE its law;
  without extracting it the test would re-implement the law and pin
  it against itself); from `scripts/ual_beats.py` — the four tables,
  `TOTAL`, `pop_footprints` (both bpy-free bodies). The tables'
  bare `Beat` references resolve inside the namespace; the module is
  never imported (its real `from ual_bake import Beat` binds bpy for
  scene-side importers — fine there, extraction-only here). Pins:
  - T1 contiguity: each actor's tables cover [1, TOTAL], no gaps,
    no overlaps;
  - T2 resolver totality: `_make_resolver` resolves every frame in
    [1, TOTAL] (no empty evals);
  - T3 pop geometry: shot frames == `pop_footprints(bursts)` output;
    extents obey min(gap, max_extent); hold_from gating; the blend-in
    weight curve ramped over `blend_in - 1` frames (r2 N4);
  - T4 the frozen-source hold on the REAL tables (the engine law).
- previz `test_ual_build_v4.py` + `test_sim` 307/307 + `dry_gates`
  all-empty (unchanged surfaces).
- **Tier-B byte-identical** post-split — the strongest proof: same
  beats, same resolvers, same engine → same baked actions → the pin
  holds. A delta means the composition drifted; fix before committing.

## 4. Migration (ONE cross-repo changeset, never-broken-tree)

r1 C1–C3 folded: the owner flip is a TOOL edit, the hook needs its
own marker mechanism, and the intermediate states are specified.

0. **Recorded baseline**: tier-B green at HEAD (done — code_sha
   `c6b9081e…`).
1. **KIT commit A** (one commit):
   - `tools/sync_shared.py`: remove `scripts/ual_bake.py` from
     `OWNER_PREVIZ` (the comment updates: beat tables moved to
     ual_beats.py; ual_bake is now the pure engine) — r1 C1: emit()
     recomputes owner from this set; WITHOUT this edit the flip
     never happens.
   - Author the engine per §2.1.
   - Run `tests/test_ual_bake_laws.py` (green against the engine
     alone).
   - `--emit` (the manifest's ual_bake entry flips to owner:kit with
     the new sha).
   - Commit (r2 I1: NO PORTBACK_PENDING needed — `pre_commit()`
     reads the WORKING-TREE manifest, which this commit's own `--emit`
     output already flipped to owner:kit, so staging ual_bake.py is
     the owner's own edit and the hook passes clean). Push.
   - Expected mid-state (r2 I3 corrected): previz `--check` shows
     ual_bake **OWNER-AHEAD** — consumer-mode classification reads
     the owner's bytes from the kit sibling (c=old, r=old, o=new
     engine); the remedy line says "run --to FROM THE KIT", which is
     exactly step 3. The tree is RUNNABLE everywhere (previz scenes
     still run the old full file; the kit's engine alone runs
     nothing).
2. **PREVIZ commit B** (one commit):
   - Copy the kit's engine bytes into `scripts/ual_bake.py`
     verbatim (the informal sync — previz's vendored record still
     says owner:previz, so the hook allows the owner's own edit;
     r1 C3). The other staged files (ual_beats.py, test_ual_beats.py,
     the scenes, the probes) are not manifest paths — the hook is
     indifferent to them.
   - Author `scripts/ual_beats.py` + `scripts/test_ual_beats.py`;
     swap the call sites per §2.3 (incl. the probe edits).
   - Run `test_ual_beats.py` + `test_ual_build_v4.py` + `test_sim`.
   - Commit. Push. Expected mid-state: previz `--check` shows
     RECORD-STALE on ual_bake (file==new bytes, vendored record
     still old) — the documented both-remedy state; benign, resolved
     by step 3.
3. **KIT commit C**: `--to <previz>` (vendors the refreshed record +
   checker; ual_bake bytes already match → no-op copy; the r2-F3
   guard PASSES because the consumer file == incoming bytes — the
   "explainable" state the guard's third condition excludes).
   r2 I3: this commit is NEVER empty — the `--to` re-emit stamps
   `kit_commit` and rewrites `tools/shared_audit.json`; commit those.
   Push.
4. **PREVIZ commit D**: commit the vendored record/checker bytes
   from step 3 (`--check` 39/39 IN-SYNC both sides now).
5. **Tier-B byte-pin run** → GREEN = payload-invisible. Commit the
   receipt (worklog line; no file change expected).

Rollback: `git revert` of commits A+B (+C/D). The revert of A
restores the OLD manifest (owner:previz) AND the old ual_bake bytes
in one commit — but pre-commit reads the WORKING TREE at staging
time, which during a revert-in-progress still holds... concretely:
the revert stages old-manifest + old-ual_bake together, so the
manifest the hook reads says owner:previz while ual_bake.py is
staged → BLOCKED. Plant `PORTBACK_PENDING` naming `scripts/ual_bake.py`
for the revert commit (r1 C2/r2 I1: the marker's ONLY real use is
this rollback path).

## 5. Risks + mitigations

| Risk | Mitigation |
|---|---|
| `hold_from=157` / `src_extent=3.0` / `max_extent=6` / `blend_in=2` transcribed wrong | T3 + the byte-pin (a wrong value shifts pops or aim-hold → tier-B fails loudly) |
| The v4 scene silently diverges | v4+v5 call the SAME tables today (verified at both sites); test_ual_build_v4 runs in step 2 |
| Probes rot | probe_v4a's real edits enumerated (r1 I4); probe_v4b verified at edit time |
| Mid-migration hook/guard refusals | Commit A needs NO marker (the hook reads the working-tree manifest its own --emit already flipped — r2 I1); the informal-copy-then-vendor order satisfies the F3 guard (r1 C3); PORTBACK_PENDING is rollback-only (r2 I1); expected `--check` states documented per step (r2 I3) |
| Parallel-session collision on ual_bake.py | Fetch-before-push; the file's content history ends at the s31 commits (99b3c0c-era — r2 N2: no later commit touches it at all); low-activity surface |
| The vendor's stale copy looks more legit post-split | The checker's VENDOR-COPY-DIVERGES info line already reports it; disposition stays the crowd-kit repo's cleanup (s34 audit S1) |

## 6. What this does NOT change

- The bake laws, the beat values, the fidelity-gate law text
  (sections 1-2), the memory law, the scene-facing API shape
  (`bake_all(ctx, bursts)`).
- The kit's hero_gates / the exporter surface (tier-B byte-pin is
  the proof).
- crowd_v6 ownership (session-27 law untouched).

## 7. Doc updates riding this change

- kit AGENTS.md / SHARED_SYNC.md: ual_bake owner flips to kit;
  ual_beats.py = the previz-only data module (the crowd_v6.contract
  pattern's second instance).
- previz AGENTS.md: the ual_beats.py law (choreography edits land in
  ual_beats.py; engine fixes go kit-first through the manifest).
- Test-surface documentation lives HERE (r2 I2: the manifest has NO
  `tests` field — schema 1 entries are {path, owner, sha256} only;
  the s33 design's schema example carried one, but emit() rebuilds
  entries without it, so a hand-added field would be wiped by the
  next re-emit): ual_bake's regression surface = kit
  tests/test_ual_bake_laws.py + previz scripts/test_ual_beats.py +
  scripts/test_ual_build_v4.py + the tier-B byte-pin.

## 8. LANDING (2026-10-03, s34)

Complete, payload-invisible. The migration ran exactly as §4
prescribes (A: kit engine + OWNER_PREVIZ edit + emit; B: previz data
+ swaps; C: --to; D: vendored record), with the r2-verified
state-machines holding at every step (commit A's mid-state read
OWNER-AHEAD on previz exactly as predicted).

ONE defect escaped the design's own review rounds and was live-caught
by the acceptance gate itself: `_fidelity_gate`'s SIGNATURE was never
edited to accept `post_check=None` (the implementation edited the
call site and the hook body but missed the def line) — bake_actor
passed the kwarg into the old signature and the tier-B run died at
the Gunner bake with a TypeError. Fixed both sides; the consumer-side
fixup exercised the hook's designed vendor path in production
(PORTBACK_PENDING naming the file — gotcha 114's mechanism).

Receipts:
- kit tests/test_ual_bake_laws.py L1–L4c ALL PASS (owner-side engine)
- previz scripts/test_ual_beats.py 17/17 (T1–T4)
- previz test_ual_build_v4 ALL PROBES PASS; test_sim 307/307
  (parity pin 45ac606f holds)
- kit tier-A ALL PASS (incl. the s34 resume teeth A8b–A10c)
- **kit tier-B BYTE-IDENTICAL to the pre-split baseline** — the
  strongest proof: same beats, same resolvers, same engine laws →
  the same baked actions → the same previz.json (params_sha
  1f581a18… pinned)
- shared-sync 39/39 IN-SYNC both sides; ual_bake owner:kit
  (engine sha 4b632562); ual_beats.py previz-only, no manifest
  surface

The engine's law surface is now kit-owned and directly testable; the
choreography hotfix path is previz-local (no manifest round-trip);
the vendor's stale third copy remains an informational checker line
(disposition: the crowd-kit repo's cleanup).
