# RH-canvas FULL-library validation — s39 receipt

**Date**: 2026-10-15 · **Battery**: `tests/rh_fullwalk.py` ·
**Verdict**: **2,032 / 2,032 PASS — 0 WARN — 0 FAIL**

## What was validated (and how)

The user's s39 ask: *"do validate (not just guess) fully these
animation / pose can all apply"*. The s38 battery (R1-R8b) pinned the
pipeline mechanics on a handful of clips; this walk runs EVERY clip in
the catalog through the REAL public API, one Blender process:

1. `rh_canvas.import_clip(id)` — fetch-if-missing (sha256 verify law) →
   FBX import → 65-bone `mixamorig:` check → action extracted →
   fps-30 + scene-range laws applied.
2. `rh_canvas.bind(mesh, id)` — action assigned to the ONE mannequin
   built at start (slot auto-assign verified per clip).
3. `frame_set(f0 / mid / f1)` → posed key-bone world sampling
   (11 key bones: Hips/Head/Hands/Feet/Arms/Legs/Spine):
   displacement-vs-rest, within-clip motion, head-z band.

Per-clip rows also record: frames, obj_scale (the 0.01 law), animated-
bone census (52 on every clip — fingers carried but often static),
hips-location fcurve presence (root motion marker), bind slot.

**Runtime**: 2,032 clips in 152 s (13.4 clips/s, one Blender process;
memory held by per-clip armature/action purge + orphan sweep every 50).

## Aggregate

| metric | value |
|---|---|
| clips walked | 2,032 (the full id-deduped catalog) |
| import + 65-bone check | 2,032 / 2,032 ok |
| bind (slot assigned) | 2,032 / 2,032 ok |
| applied with real motion/pose | 2,032 / 2,032 |
| FAIL (apply failure) | **0** |
| animated-bone census | 52 bones on every clip |
| obj_scale (0.01 law) | held on every clip |
| hips location fcurve | present on every clip |

## Consumer tags (surfaced at browse time in `catalog`)

- **`elevated_root_motion` (37 clips)** — head leaves the
  [-0.3 m, 2.4 m] band: the climb / hang / leap / jump-down / backflip
  family. The clips APPLY fine; their root motion legitimately carries
  the actor up to ~4.5 m (or below floor — the dive clips). Pair them
  with set geometry (wall / ladder / platform / ledge / water level).
  Two extremes (3094 arm-swing-to-platform, 4126 fall-into-pool) were
  additionally VLM-verified coherent on rendered strips:
  `elevated_3094.png`, `elevated_4126.png` (strip f0/mid/f1) —
  "coherent humanoid, no broken data" both.
- **`static_pose` (25 clips)** — posed but < 5 mm within-clip motion:
  the pose-hold library class (basic idle poses, prone casualties,
  aiming stances). Intended behavior for a POSE library, not a defect.

The tag sets live in `scripts/rh_canvas.py`
(`ELEVATED_ROOT_MOTION` / `STATIC_POSE`); regenerate by re-running the
walk if the library snapshot ever updates.

## Method notes (for a re-run)

```bash
# 0. bulk-fetch the full library (14 s at 141/s, 1.2 GB, all sha256-
#    verified through rh_canvas.fetch_verified — the cache repairs
#    itself on mismatch)
python3 tests/rh_bulkfetch.py (s39 maintenance driver)            # s39 scratch driver

# 1. the walk (fits ONE blrun call; --chunk i/n also available)
./scripts/blrun.sh --background --factory-startup \
    --python tests/rh_fullwalk.py -- --chunk 1/1
# -> /home/z/rh_fullwalk/walk_chunk1of1.jsonl (per-clip rows)
```

First-run verdict rules were deliberately strict (head band ±3 m);
12 clips tripped it and INVESTIGATION (not assumption) showed they were
all climb/hang/leap root-motion clips — programmatic motion evidence
(52 bones, 1.7-5.8 m displacement, hips fcurves) + VLM visual reads on
the two extremes. The v2 rules encode that evidence: FAIL = apply
failure only; the elevated/static classes are TAGS, not defects.

## The s39 usability round (sub-agent test drives) + fixes

Two docs-only-onboarding agents drove the library cold (reports:
`/home/z/s39_agents/U{1,2}/REPORT.md` — preserved in the session
scratch; the fixes below carry the findings). U1 built a 3-character
animated shot (VLM-verified); U2 ran the any-rig boundary + ensemble +
swap + coexistence drives. Fixes landed from their findings, all
re-verified by a SECOND full walk (2,032/2,032 PASS again) 
  verified by tests/rh_decoy_probe.py (D1 decoy refused / D2 partial-rename warns / D3 clean 520-520 / D4 swap-unpin) + a decoy
probe battery:

- **P1 (U2)**: silent zero-motion binds on count+prefix-correct,
  name-wrong rigs → `bind()` now channel-match validates every fcurve
  data_path against the target's pose bones (0/N matched = REFUSED;
  partial = bound with `orphaned_channels` + warning in the rep).
- **P2 (U2, found by the decoy probe)**: the clip-action registry
  mis-bound after scene resets (every Mixamo FBX action shares the
  name 'Armature|mixamo.com|Layer0') → frame-range FINGERPRINT
  validation on registry hits.
- **P2 (U2)**: FBX-importer fake_user pins leaked into glTF ACTIONS
  exports ('air dance') → `bind()` auto-unpins the replaced action +
  `purge_unassigned()` hygiene helper.
- **P2 (U1)**: no browse-time duration → per-clip `frames` /
  `duration_s` in the catalog (the CLIP_FRAMES table, s39 walk data);
  frame-range doc claim "17-57" corrected to the measured 7-1401
  (median 69, p95 343).
- **Docs (U1)**: multi-character recipe section (union scene range,
  travel-direction law, factory-stage purge, one-shot CLI persistence
  note) + mannequin naming/telemetry tips; kb/rigged_characters.md
  policy updated (the RH path is now the third sanctioned actor path).
- Verified-but-rejected: U2's `UA.Build` docstring finding was a
  misread (the docstring reads `UA.build` — repo-wide grep confirms);
  the s37 lesson (verify agent findings before fixing) held.
