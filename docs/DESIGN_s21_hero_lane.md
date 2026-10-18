# DESIGN s21 — the hero lane: wrapper law + second rig family + the retarget recipe

> Status: REV-2 (design audit r1 folded — APPROVE-WITH-CHANGES, 2 P1 +
> 9 P2 + P3s; the D-revision log is §5). The audit's corrected formula
> set + the parent-cancellation identity are §D3's law text now.
> Owner: session-21 orchestrator. Scope: the vision kit's "some more
> humanoid rigged models" ask (HANDOFF open queue 1+2). Design
> surfaces: D1 wrapper_rig helper (F-RH3 landed), D2 the Quaternius
> casual-rig loader, D3 the rig_retarget recipe (the any-rig boundary),
> D4 motion_lab v2, D5 (deferred) hero_gates exporter wiring.

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

## 5. D-revision log (design audit r1 — APPROVE-WITH-CHANGES, ALL folded)

- **D1a (P2-4) probe law hardened**: candidates are ±Y ONLY (a foot
  bone's local Z is the roll axis — also horizontal; a horizontalness
  contest across axes is silently won by a meaningless axis). The
  winner must be BOTH near-horizontal (|fwd.z| ≤ 0.5) AND
  Y-dominant (|fwd.y| ≥ 0.5) — sideways-authored imports coin-flip
  horizontalness alone. Auto-pick skips `*_end` leaves (the 42-bone
  census provably carries `Foot.L_end`); the Quaternius loader passes
  the explicit probe bone (`Foot.L`). The rep reports the WINNING
  AXIS + the measured forward.
- **D1b (P2-1b) mesh-rides-rescale**: the "unparented mesh → wrapper
  with identity MPI" branch is only safe at scale 1.0. When
  `scale ≠ 1.0`, the skinned mesh MUST be parented to the armature
  (or carry the same MPI) or the posed/rest skins diverge (rest
  renders at imported transform, posed verts follow the scaled rig).
  The loader's first-run probe records `mesh.parent` truth.
- **D2a (P2-1) UNIT_RESCALE**: the raw import is a ~5–7-unit giant
  (bbox_diag 7.165/6.919 at object scale 1.0; no importer unit
  conversion landed). Pin `UNIT_RESCALE` (expected ≈ 0.24–0.33;
  exact value = first-run height measurement) applied in the WRAPPER
  MPI (`wrap(..., scale=UNIT_RESCALE)`); the 1.2–2.2 m height gate
  runs POST-rescale; both raw + rescaled heights live in the truth
  constants. dist_m_p50 0.24 on a 941-vert mesh corroborates the
  ~4× oversizing.
- **D2b (P2-7) pool mechanics**: pools map THIS import's actions via
  the acts-before/acts-after diff (the UAL pattern) — NOT "first
  import wins" (that binds hero #2 to hero #1's datablock). "Exactly
  11 actions" is asserted against the import diff, not
  bpy.data.actions. Key rule: last pipe segment MINUS the gender
  prefix → keys {Walk, Idle, Jump, Death, Clapping, Punch, Run,
  RunningJump, Sitting, Standing, SwordSlash} (the design's earlier
  "Man_Walking"/"native Walking" constants were WRONG — probes say
  `Man_Walk`/`Female_Walk`). Per-rep pools only; a global stripped
  registry would collide (`Walk` exists in both).
- **D2c (P3)**: both FBXs name their armature `HumanArmature` —
  object-level collision on a second import is harmless (loader
  renames to `<name>.Rig`) and noted. First-run probe adds
  `mesh.parent` + imported height to the truth constants.
- **D3a (P1-1) THE CORRECTED FORMULA SET** (the audit's worked
  example is law — keying `rot(L)` bakes the target's rest-local
  orientation into every pose, a constant 45°–180° per-bone error;
  limbs render inverted):
```
for each mapped pair (src b -> tgt t), parents FIRST:
  D_s(b)     = M_src(b,f) @ M_src_rest(b)^-1          # world delta, src units
  M_t(t,f)   = D_s(b) @ M_tgt_rest(t)                 # world pose on target
  D_t(t)     = M_t(t,f) @ M_tgt_rest(t)^-1            # target's own delta (children reuse)
  basis(t,f) = M_tgt_rest(t)^-1 @ D_t(parent(t))^-1 @ D_s(b) @ M_tgt_rest(t)
               # root: D_t(parent) := I
  ROTATION: key basis(t,f).to_quaternion() into rotation_quaternion
            (target bone QUATERNION mode asserted); sign continuity
            at write time (dot(q, q_prev) < 0 => q := -q) or the
            interpolation spins the long way.
  LOCATION: root-motion bone ONLY:
            d_world = (M_src(b,f).translation - M_src_rest(b).translation)
                      * (tgt_hip_rest_z / src_hip_rest_z)
            d_local = M_tgt_rest(t).to_3x3().inverted() @ d_world   # BONE-LOCAL (the s20 axis law)
            key into pose.bones[t].location; ALL other bones at rest.
            The root chain's translation (pivot artifact) is DISCARDED.
```
  The parent-cancellation identity (why this is exact):
  `D(p)^-1 @ D(b) = M_rest(b) @ basis_src @ M_rest(b)^-1` — the
  armature-space composition IS the parent-relative transfer with
  rest correction; pivot artifacts cancel exactly for non-root bones.
- **D3b (P2-3) location-transfer set**: the mapped hips PLUS any
  mapped ancestor carrying location fcurves (Quaternius root chain is
  `Bone → Body → Hips`; UAL's bob provably lives on DEF-hips —
  constraint-free purity — but the first-run self-verifying assertion
  pins it: "Walk_Loop carries DEF-hips location fcurves, world-z span
  ≥ 0.02 m"). RH-canvas sources carry hips location on every clip.
- **D3c (P2-2) coverage denominator**: animated DEFORM-CLASS bones
  only; per-family declared non-transferables (`*_end`, `PoleTarget.*`
  — the probe shows they are the top movers of Man_Death, variance
  6.35); finger policy rigify53→quaternius42 = EXCLUDE + report (the
  stub `Fingers`/`Thumb1/2` cannot carry finger articulation).
- **D3d (P2-5) write path**: the output action is built through
  `blender_kit.fcurves_new()` (5.2 slotted-action scaffolding; a
  fresh action has no slots and `fcurves.new` is a trap there),
  single OBJECT slot; then `rh_canvas.bind()`'s `slots[0]` auto-assign
  lands with zero extra code. Quaternion sign continuity at write
  time (D3a). Never key `rotation_euler` on QUATERNION-mode bones
  (the s18/s20 silently-inert law).
- **D3e (P2-6) scale law reworded**: assert object scale UNIFORM
  (any value — Mixamo-65 sources land at 0.01 BY LAW, rh_canvas
  import law 1) + bone rest matrices ~identity scale; never assert
  object scale == 1.0.
- **D3f (P2-9 + P3s) immunity + pins**: the math operates on
  `pose.bones[].matrix` (armature space) — wrapper MPI (facing/scale)
  is EXCLUDED by construction; world-facing consistency is the
  STAGING's job (yaw both wrappers identically — D4). Height ratio
  measured from `bone.matrix_local.translation.z` (armature-data
  space, immune to object transform, unit-consistent; T-pose vs
  A-pose is a non-issue). Hips world gate comparator per sampled
  frame: `|tgt_hips_z(f) − ratio·src_hips_z(f)| ≤ band`. Output fps
  pinned from the source. Single global ratio assumes similar
  proportions — the world gates are the catch-net.
- **D4a (P2-8) integration law**: hero records are
  `{arm, body, clip, rep}`-shaped and BOUND before the union-range
  lines (they dereference frame_range unconditionally). Hero
  placement moves the WRAPPER (v1's `pl.move_to(arm)` violates the
  wrapper law — animated-armature yaws get clobbered; the wrapper is
  the clobber-proof surface). Clip labels: `UAL:Walk_Loop`,
  `Quat:Walk`, `UAL:Walk_Loop→Quat`.
- **D5a (P3) fake-user lifecycle**: retarget + bind complete in ONE
  process (an unpinned unassigned action dies on save); the FBX
  importer's fake-user pins keep the Quaternius pool alive across
  reload (intended); the export-side purge (unassigned fake-user
  actions) is D5's when wiring lands.

## 6. D-revision 3 (s22 implementation round — measured law changes)

- **D3-REV3a (the DISCONNECTED-TOPOLOGY fact)**: the Quaternius rigs
  carry DISCONNECTED leg chains — Foot.L parents to the root Bone, not
  to LowerLeg (probed 2026-10-18, scripts/s23_eval_probe.py). Their
  clips move the feet via PER-BONE LOCATION channels. The audited
  hips-only location policy structurally drops the gait on this family
  (measured: rotation-only replay leaves the feet glued at rest height
  while the source lifts 0.24 m). THE LAW REPLACES D3b's set: location
  transfers for every mapped bone whose SOURCE ACTION carries location
  fcurves (data-driven). Mixamo-65 sources animate location on Hips
  only, so the old hips-only behavior falls out of the same rule.
  Value = the conjugated basis translation × the height ratio (the
  basis composition routes frames structurally; the separate world
  routing (R2) is retired — the measured rotation error was 0.0 deg
  through the audited formula, so only the location law needed the
  fix).
- **D3-REV3b (the FROZEN-EVALUATION trap)**: an FBX-imported rig can
  evaluate its pose FROZEN at rest (measured: manual pose property
  changes, update_tag, depsgraph_get, frame bounces — nothing moves
  pb.matrix; the UAL glTF rig evaluates fine in the same session).
  The exact-pose closure was therefore retired for a DRIVE CHECK: the
  output action's fcurve values must reach the evaluated pose
  properties at sampled frames (drives_ok + the teleport guard). The
  world gates (feet floor/lift, hips band, gait anti-phase) carry the
  behavioral verification (H5: feet 0.020→0.249 m ≈ the source's
  0.24 m lift).
- **D3-REV3c (anatomy gaps are not map failures)**: the coverage
  denominator measures the TRANSFERABLE set; bones whose class the
  target family lacks (rigify spine.003 / toes vs quaternius's
  2-spine no-toe body) are reported as no_target, not counted against
  coverage. Fingers are non-transferable everywhere (the stub cannot
  carry articulation — the audited D3c policy, now with the census to
  back it: UAL Walk_Loop animates 28 finger bones, all zero-span
  location / pure rotation).
- **D2-REV3 (the import-slot + stuck-pose pair)**: the loader clears
  the import's live action slot (the UAL pattern) AND the retarget
  resets the target's pose properties (unassigning an action leaves
  the last evaluated pose IN the properties — location/scale would
  evaluate from the stuck import pose). The 4.4+ slot law applies to
  EVERY assignment (ual_bake's _assign_action precedent; a plain
  `ad.action = X` leaves the binding stuck and the pose evaluates the
  old action silently).

## 7. D-revision 4 (s23 audit-A1 fold — the gate layer made load-bearing)

The s22 AUDIT-A (retimed twice: context-deadline both rounds) finally
ran as the scoped A1 wave (math + module only). Verdict: the formula
layer is SOUND (the conjugate-basis rotation and the parent-
cancellation identity independently re-derived and numpy-probed exact
to 1e-9; every (src,tgt) unpack verified; frame freshness clean; no
P0). The exposure was the GATE layer: flags computed, docstring said
fail-closed, nothing enforced. Folded (all in rig_retarget.py):

- **P1-1 gates enforce**: drives_ok / teleport_ok now RAISE
  RetargetRefused inside retarget() — a dead bake cannot return a rep.
- **P1-2 source anti-frozen**: a stuck SOURCE slot bakes a rest pose
  that PASSES the output drive check (constant values drive fine) —
  new defense: source fcurve DATA span vs the EVALUATED hips span at
  the sampled frames; animated data + frozen evaluation refuses.
  Static actions (both spans ~0) stay legal.
- **P1-3 location drive + connected law (as MEASURED — the auditor's
  strict form was wrong)**: the drive check now covers LOCATION
  channels too (locf map). The proposed "refuse location keys on
  use_connect bones" fired on the REAL hero path (UAL walk carries
  location fcurves on limb classes; Quaternius LowerLeg.L is
  connected) — but a location fcurve cannot drive a connected bone in
  ANY rig, the same-class channel is an equally dead no-op in the
  SOURCE (the s22 decisive experiment: rotation-only replay lifts the
  feet the full gait). So: SKIP + REPORT (rep loc_no_op), never
  refuse. The refusal form would have broken the working path on a
  channel that carries zero information.
- **P2-4 scaled-delta propagation**: the keyed location is
  ratio-scaled, so the delta descendants compensate is the SCALED
  pose — D_t now composes basis_eff = T(loc*ratio) @ R(basis) via the
  identity parent_D @ M_t_rest @ basis == D_s @ M_t_rest (unscaled
  behavior identical for rotation-only bones, probed by the suite).
  Chained location sources no longer carry a (ratio-1)*parent-motion
  error. Not behaviorally testable today (no family pair with chained
  locations + ratio != 1 exists in the corpus) — the identity comment
  in the loop is the reviewable form.
- **P2-5** _iter_fcurves: the act.fcurves fallback (empty on 5.x
  slotted actions -> location transfer silently dropped + coverage
  vacuously 1.0) removed — blender_kit is a hard dep, loud failure.
- **P2-6** empty transferable set refuses (was: coverage 1.0 vacuous
  rest bake). Test H4 row.
- **P2-8** height_ratio bounds BOTH sides (+ finite check).
- **P2-9** output channel census: every keyed pose path must resolve
  (clean refusal; was an unguarded KeyError). Test H4 row (injection
  via blender_kit.fcurves_new — a raw action.fcurves.new lands in a
  legacy slot iter_fcurves never returns on 5.x).
- **P3**: unguarded quote-split guarded; _assert_uniform_scale dead
  vars removed + row-norms label fixed.
- **P2-7 DEFERRED (documented)**: _assign_action pins slots[0] —
  structurally unpinned for a FRESH action pre-write and wrong for
  multi-slot actions; every real path is fresh-single-slot today.
  Revisit if multi-slot sources ever arrive.

test_hero_lane 6/6 after the fold (H5 feet band + H6 hips world
band unchanged — no behavioral regression).
