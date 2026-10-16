# DESIGN s21 — the hero lane: wrapper law + second rig family + the retarget recipe

> Status: DRAFT-1 for fresh-eyes design audit. Owner: session-21
> orchestrator. Scope: the vision kit's "some more humanoid rigged
> models" ask (HANDOFF open queue 1+2). Design surfaces: D1 wrapper_rig
> helper (F-RH3 landed), D2 the Quaternius casual-rig loader, D3 the
> rig_retarget recipe (the any-rig boundary), D4 motion_lab v2, D5
> (deferred) hero_gates exporter wiring.

## 0. Ground truth absorbed

- **The wrapper-empty facing pattern exists, proven, in the vendored
  `scripts/assets_ual_actors.py`** (mainline s33 5fc02d2): fresh
  `<Name>.Root` EMPTY (identity basis); armature child with
  `matrix_parent_inverse = Rz(pi)·S(scale)` (flip probed at bind,
  never hard-coded); skinned mesh kept INSIDE the wrapper tree (skin
  binding rides the armature modifier; a root-level mesh strands);
  composition law `world = parent @ MPI @ basis` (mpi_semantics_probe,
  Blender 4.5/5.2). Manual yaw on the WRAPPER survives `frame_set` —
  object-level rotation keys on the armature can NOT clobber it
  (s20 F-RH3).
- **The facing probe law** (`_facing_sign`): foot bone's local +Y
  (Blender bones' Y runs along the bone) mapped to world = toe
  direction; sign = +1 if world-fwd.y >= 0 else −1. Probed per import
  on the as-imported armature BEFORE any transform is authored.
- **Three rig families now in play**:
  1. Mixamo-65 (`mixamorig:` prefix, 13 static = 10 finger tips +
     HeadTop_End + 2 Toe_End; cm curves at import; rh_canvas's family).
  2. Rigify-53 DEF-* (the UAL mannequin: 46 actions, bind height
     1.651 m, feet-origin; actions keyed on QUATERNION modes).
  3. Quaternius casual 42-bone (Male_Casual.fbx / Female_Casual.fbx:
     armature `HumanArmature`, skinned meshes `BaseHuman`/`Female`,
     11 pipe-named actions `HumanArmature|HumanArmature|Man_Walking`,
     319 fcurves on the first action, QUATERNION modes, bones include
     `Bone`, `Body`, `Hips`, `Foot.L`, `Palm.L` — no mixamorig prefix,
     no DEF- prefix; import probes committed beside the FBXs).
- **rh_canvas's any-rig boundary today**: `bind()` accepts only
  Mixamo-65 rigs (count + prefix census + channel-match guard);
  non-Mixamo rigs are REFUSED with "retarget the action" — and
  retargeting is a documented non-goal (v2 spec). The refusal is
  correct; the MISSING half is a first-class recipe so the refusal is
  a door, not a wall (HANDOFF queue 1).

## D1 — scripts/wrapper_rig.py (the F-RH3 helper, generalized)

ONE kit-owned helper implementing the wrapper-empty facing law for ANY
imported animated armature (UAL / Quaternius / RH-fixture / future).

API:
```python
wrap(arm, name, scale=1.0, mesh=None, facing_probe=None) -> rep
# rep = {"root", "armature", "mesh", "facing_sign", "scale"}
```

Laws encoded (each from the audited pattern):
1. Wrapper EMPTY named exactly `<name>.Root`, fresh, identity basis.
2. Facing probe at bind on the AS-IMPORTED armature, before any
   transform is authored. Probe order: (a) caller-supplied probe;
   (b) first pose bone whose lowercase name contains "foot" — local
   +Y via `arm.matrix_world @ foot.matrix` then `to_3x3() @ Y`;
   (c) REFUSE if no foot-like bone exists (fail-closed; caller may
   pass an explicit probe bone name). SELF-CHECK added vs the UAL
   version: the probe's world forward must be near-horizontal
   (|fwd.z| <= 0.5); if not, try −Y; if neither is horizontal,
   REFUSE with the measured value (a rig whose foot +Y points up is
   a rig we do not understand — the probe must not silently pick).
3. `arm.matrix_parent_inverse = flip @ Scale(scale)`; flip only when
   the probe faces −Y. Scale NEVER keyed.
4. Skinned mesh (arg or auto-found via `find_armature()`): stays
   parented to the armature if it already is; else parented to the
   wrapper with identity MPI (keeps imported world transform).
5. Refusals: non-ARMATURE arg; armature already parented (caller
   decides ordering — the helper refuses rather than silently
   re-parenting an existing hierarchy); name collision on
   `<name>.Root` (refuses; naming is the caller's hygiene).
6. Report includes facing_sign + the probe bone name + the measured
   world forward (auditable — the s20 lesson: numbers travel).
7. The helper NEVER touches animation data (no action clearing —
   that is a per-loader policy: UAL clears the import slot, RH keeps
   its bound clip).

NOT a refactor of assets_ual_actors.py: that file stays
verbatim-mainline (film lane owns its evolution; zero-drift law).
wrapper_rig.py is the vision kit's OWN generalization; a pointer note
goes in VENDOR_LEDGER.md.

## D2 — scripts/assets_quaternius.py (the second rig family loader)

Built ON wrapper_rig (does not duplicate the wrapper math).

- `FBX_FILES = {"male": assets/vendor/quaternius/Male_Casual.fbx,
  "female": .../Female_Casual.fbx}`; `load(key, name, scale)` →
  one FBX import → armature + skinned mesh discovery (meshes with
  `find_armature()` non-None) → stray-object law (DELETE non-rig
  scene nodes with a report — the UAL Icosphere class) →
  wrapper_rig.wrap(...) → action pool.
- Action pool: the importer yields pipe-named actions
  (`HumanArmature|HumanArmature|Man_Walking`); pool keys strip to the
  trailing key (Walking, Idle, Jump, Death, Clapping, ...). Duplicate
  handling: `.001` suffixes map to the same key (first import wins;
  the loader imports ONE rig per call so no collisions expected —
  assert exactly 11 actions).
- Audit (`audit(rep)`): bone census == 42 (both rigs; probed),
  QUATERNION rotation modes on all pose bones (the s18 law — the
  loader RECORDS and WARNs if any bone is in another mode, fixing
  modes is a per-rig decision not a silent one), height gate 1.2–2.2 m
  + feet-ground band ±0.15 m (empirical: the probes recorded
  bbox_diag_local 7.165/6.919 with mesh_world_scale 1.0 — the true
  imported height is MEASURED AT FIRST RUN and pinned in the module
  docstring + truth constants; the gate then asserts the pinned
  value ±0.05 m so a unit-scale regression fails loud), single
  material-slot sweep helper (recolor law from the UAL gauntlet R4).
- Both FBXs vendored with probes; the loader ships truth.json-style
  pinned constants from the first-run measurement (self-verifying —
  the fixture discipline).

## D3 — scripts/rig_retarget.py (the any-rig recipe, first-class)

The math (constraint-less, armature-space delta composition — chosen
BECAUSE it transfers through differing rest orientations; per-bone
local-space math would NOT):

```
for each mapped pair (src bone b -> tgt bone t), parents FIRST:
  D(b)   = M_src(b, f) @ M_src_rest(b)^-1     # armature-space pose delta
  M(t,f) = D(b) @ R_rest(t)                   # compose onto target rest
  L(t,f) = M(parent(t), f)^-1 @ M(t, f)       # extract target-local
  key rotation (target bone's rotation_mode; QUATERNION families) and
  location per policy below.
```

- Location policy: ONLY the designated root-motion bone (hips class)
  takes location — source hips armature-space DELTA (M(f) minus rest
  translation) scaled by the global height ratio
  `(tgt_hip_rest_z / src_hip_rest_z)`; every other bone's location
  stays at rest (uniform humanoids; per-bone location transfer is a
  trap: unit differences corrupt it silently).
- Height ratio measured from rest matrices (hips height), never from
  bbox (bbox depends on pose).
- Mapping tables: `JOINT_MAPS` — per family pair, semantic joint
  classes (hips, spine×3, neck, head, shoulder/arm×3/hand per side,
  leg×3/foot per side, toes optional). Families: `mixamo65`,
  `rigify53` (UAL DEF-*), `quaternius42`. Unknown source bones are
  reported UNMAPPED (not silently dropped).
- Fail-closed gates on the OUTPUT action:
  1. Coverage floor: animated src bones mapped >= 0.9 (else REFUSE).
  2. Channel-match census on the target: orphaned == 0.
  3. World gates at sampled frames (frame_set evaluate — the s20 law,
     never rest-only): feet world-z band [−0.05, 0.15] m; hips world-z
     within [0.4, 1.4] × src hips height ratio; per-frame per-bone
     quaternion |Δangle| from previous sample < 90° (teleport guard).
  4. Fresh-bake-only: writes a NEW action `<src>__rt_<tgt>`; the
     source action is NEVER mutated; fake_user left False until bind.
- Scale law: uniform-scale assumption stated + asserted (both rigs'
  rest armature scale == 1.0 ± 1e-3; refuse non-uniform).
- Interpolation: bake per-frame at the source fps across the source
  range (linear keying at 1-frame stride; the source's eased curves
  are RESAMPLED by evaluation — no easing-law inheritance, documented
  deviation vs ual_bake's eased blends which is a choreography engine,
  not a family converter).

## D4 — motion_lab v2 (the dog-food integration)

- scripts/scene_motion_lab.py gains a HERO ZONE: (a) one UAL mannequin
  hero via assets_ual_actors (wrapper + pool action), (b) one
  Quaternius Male hero with its native Walking, (c) one Quaternius
  Female hero with a RETARGETED UAL action (D3 proven end-to-end).
  Existing 7 fixture actors + 2 statues stay untouched.
- Two-column law extended: per-hero strips + world-z numeric tables;
  the retargeted hero's strip must read as the same gait class as its
  source clip (eye + numeric drift table).
- No rebuild of v1's staging: additive staging + documented ctx keys.

## D5 — DEFERRED (PLAN row, not this session)

hero_gates 18-20 wiring into export_previz_package's gate section
(needs the gate-plumbing + fixture matrix). Vendored + standalone
tests run this session; wiring is a follow-up.

## Risks / open questions for the auditor

RQ1. The armature-space delta composition: is the order
     `D(b) @ R_rest(t)` correct for target-local extraction through
     hierarchy? (Attack with a concrete two-bone example.)
RQ2. The foot +Y probe on the Quaternius rig: Foot.L's +Y may not run
     toe-ward (naming suggests generic authoring). Is the
     horizontal-self-check + refuse design the right guard, or should
     the probe try +Y/−Y/Z candidates and pick by horizontalness?
RQ3. Location transfer on hips only: does the UAL walk carry real
     hip root motion in the DATA (in-place law says drift < 0.05 m
     for in-place clips) — does hips-only location transfer lose the
     gait bob for clips whose bob lives on spine bones?
RQ4. Quaternius height: probes show bbox_diag 7.165 with scale 1.0 —
     is the imported rig height-plausible (1.2–2.2 m) or is a unit
     rescale REQUIRED at load (pinned ratio)?
RQ5. 11 actions on Male but pool-key stripping assumes unique
     trailing keys — any collisions in the 11 names?
