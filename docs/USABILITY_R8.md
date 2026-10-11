# USABILITY_R8 — the level INHABITED (actors SIT on labeled furniture)

R8 goal (from the standing mission): complete the inhabit chain —
walk (R6) → navigate (R7) → **SIT**. A seat surface must be derivable
from LABELED furniture by probe (no manual box guessing), the kit poses
a rigged actor into it with measured math, and the result is certified
numerically + visually. Friction batch folded in per the ordered design
(F22 FIRST): F20, F21, F22, F23, VK-10. Design:
docs/DESIGN_R8_seat_protocol.md (D17 REV-2 — critique round adopted).

Run context: sandbox wiped; /home/sync survived. **The R7 wrap push had
been REJECTED by GitHub (GH001: loft.blend 535MB > 100MB blob limit) —
the "tracked since R5" belief was wrong, the blob entered at f7facd9.**
Repair: rewrite the unpushed commit excluding the blob (safe: remote's
HEAD was the parent — fast-forward, not a force), .gitignore
polyhaven_cache/, push verified on GitHub + GitLab (mirror caught up
from 132e8f4 to the R8-era HEADs), asset attached to GitHub Release
"level-asset-loft" (561,122,088 bytes verified). Chain replayed 11/11
checkpoints exact from committed scripts (free reproducibility test).

## The headline: both actors SIT, certified and seen

- **Driver → sofa_module** (rigid, conf high): walk 1.5 m → turn-sit →
  idle → exit → stand. Audit: pelvis dz 0.0 mm; sphere proxies vs seat
  BVHs — pelvis −3.3 mm (natural contact), no penetration; feet flat on
  the floor (toes −4 mm); idle drift 0.0; facing dot 1.0; **exit
  reverse-validation hips 0.923 vs standing 0.921**; upright ✓.
- **Girl → bed** (soft duvet landscape, conf medium — honest): walk on
  the mezzanine slab → edge-sit on the dome 0.30 m in (the duvet EDGE
  dips — sitting there put toes 10.8 cm through the slab; the highest
  spot within the first 0.4 m clears it). Soft-surface tolerance
  (−30 mm compression; c was measured unloaded). Exit back on the slab.
- Visuals (output/r8/r8_shots/): approach mid-stride ✓; Girl's edge-sit
  unambiguous ✓; Driver's profile-confirmed seat contact ✓; exit
  mid-rise (honest transition) ✓.
- test_r8_seat.py 18/18: yaw-convention law, synthetic-chair probe,
  sat-upon/clutter/contamination STOP-AND-FLAGs, prior gate, end-to-end
  execute, low-seat honest rejection.

## The probe earned its guards (7 guarded failures en route)

The 31-part sectional is a hostile probe target; every failure mode the
critique predicted (plus two it didn't) fired for real:
1. pillows beat the seat on raw hit count → sat-upon rule (drop a
   candidate whose plan a HIGHER candidate overlaps ≥60%);
2. cushion DOME (0.47 edge → 0.60 center) fragmented by z-clustering
   (tol 0.02) → region-growing with LOCAL z-continuity (0.03/cell);
3. single-linkage chained the dome INTO the pillows → local continuity
   fixed what global tolerance never could;
4. seam chains (1-cell strips) won proximity → hard filters (2-D axes,
   min area, flatness-for-small-regions);
5. the walk climbed the sideboard/cushions → climb guard + stand/via
   floor-clearance searches + drop guard (void);
6. the sit zone held a throw pillow → family-clutter check (0.12 m
   pelvis footprint — 0.25 m false-fired on legitimate backrest
   pillows);
7. yaw convention: atan2(f.y,f.x) is the MATH convention — the wrapper
   contract (yaw 0 = +Y) needs **atan2(−f.x, f.y)**; the 90° error
   pointed the stand ray INTO the sofa and the audit self-agreed until
   the independent backrest reference exposed it (R7's atan2(tx,ty)
   was silently correct only because its paths ran mostly ±y).

## Kit changes shipped this round

- F22 FIRST (ordered per design): validator level-aware policy —
  fam×fam AABB adjacency → visible P2 advisory (1325 on the loft;
  measured corpus 2259/2499 were composition); unlabeled full-bbox
  containment in room-scale shells (≥50×) → visible unverified skip
  (1201); gross non-shell overlaps still flag. **Loft re-baseline:
  intersections 1452→77, P0 734→52.** test_f22_levels 14/14; battery
  v1/v5(L22)/v6/f17/scope green.
- F20: AGENTS.md law — dispatch prompts show the apply_patch wrapper
  shape explicitly (save_blend is a CLI flag, not a patch key).
- F21: kb law — gap numbers against room shells are NOT contact truths.
- F23: handoff/label_use_ledger.json — floor/stairs/mezzanine_slab/
  sofa_module/bed use-verified; kitchen_unit(841)/partition_panel(145)/
  deco(63)/pendant_light(23) honestly listed as unexercised hypotheses.
- VK-10 CLOSED: agent-kit's frame_set hunk ported to
  examples/scene_v1_basic.py (sphere x read −2.0 at EVERY frame; now
  2.0/0.13/−2.0 at f1/12/24 — verified numerically).
- r8_seat.py: probe + measure + execute + CLI (probe|execute), NLA
  single-track chain, two-lane audit, STOP-AND-FLAG discipline (exit 4).

## Gotchas found this round (all in code comments + SKILL)

- GitHub's 100MB blob limit makes an over-limit commit UNPUSHABLE —
  check `git ls-tree -r -l <commit> | sort -k4 -nr` BEFORE committing
  binaries; rewriting an UNPUSHED commit whose parent == remote HEAD is
  safe (fast-forward), never force.
- The compose blend runs at 30 fps: glTF clip ranges are fps-scaled
  (Sitting_Enter 38.75f, Idle 50f, Exit 30f — the 24fps numbers ×1.25).
  Strip int() lengths; the strip maps [start,end] onto the action
  PROPORTIONALLY (a +12 frame stretch slows the clip 1.4× — key the
  wrapper at the strip's true end, not the action's).
- measure_actor must be NON-DESTRUCTIVE (restore the wrapper transform)
  or it shadows later probes with the actor's body; ground probes must
  ignore the walker's own meshes and fall back to the feet-origin law.
- Parallel-session pushes happened TWICE this session (a QA lane and a
  terminal-dawn lane); the protocol held both times: fetch → verify
  non-overlap → rebase → push; GitLab once raced a rebase (orphan
  commit) — reconciled with an empty merge node, no force.

## Replay chain (all committed)

r6_loft_fetch.sh (or the GitHub Release asset) → r6_loft_import.py →
r6_look_prep.py → look.py → patch_cuts.json (dry-run first) →
gen_r6_labels.py → gen_r6_props.py → r6_humanoid.py → look.py (handoff)
→ r7_route_planner.py (+ vision_stair_override.json) → r7_navigate.py
→ **output/r8_route.json → r8_seat.py execute** (probe first, then
measure+execute; route JSON carries actor/family/approach/mode/start)
→ r8_render.py (lite-copy, ONE render per process... two proved fine)
→ test_r8_seat.py. Tests: test_r8_seat 18/18 + test_f22_levels 14/14 +
battery (v1/v5/v6/f17/scope) ALL PASS.
