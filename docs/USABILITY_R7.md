# USABILITY_R7 — the labeled level NAVIGATED (blind route + stair ascent)

R7 goal (from the standing mission): prove that a non-vision agent can
PLAN floor-to-floor navigation on the semantically labeled level, and
that the kit can EXECUTE and VERIFY it. This is the final link in the
"any agent can work this level" chain: R6 made the level labelable and
placeable; R7 makes it WALKABLE.

Run context: sandbox wiped between sessions; full R6 chain rebuilt from
committed scripts (fetch 561 MB → import → look-lite → 4 region cuts →
labels → props → 2 UAL actors → handoff manifest). The rebuild matched
the R6 record exactly (dry-run face counts 5/18/42/21; placements
TOUCHING/TOUCHING/TOUCHING/CLEAR 5.82mm) — the R6 pipeline is
reproducible from the repo alone.

## THE HEADLINE: navigation caught a real R6 label defect

Executing the nav attempt on the R6-labeled state FAILED informatively:
the raycast tread-hug found no walkable treads under the `stairs`
label. Investigation chain (probes 3-16, all committed):
- the `stairs`-labeled object is 14 faces: a low parapet (z~0.3-0.4) +
  a sloped top piece (z 2.73-2.89) — the stair-shaft SIDE WALL, not a
  stair;
- the ACTUAL stair is `Plane.003` — which the R6 schema labeled `wall`
  (stairwell-wall guess from bboxes). Mesh-verified: 9 flat treads z
  0.13 → 2.78 climbing +y from (y 8.5) to (y 13.7), rise 0.34 / run
  0.65 (~31°, NOT the "68° space-saver" recorded in R6 — that reading
  was parallax from the mislabeled fragment's bbox), width x 2.6-3.4,
  running UNDER the mezzanine slab band (headroom ~1.9 m) and arriving
  DIRECTLY onto mezzanine_slab at y 13.8.

LESSON (now law): semantic labels assigned from bbox+name reasoning are
HYPOTHESES until the geometry is USED. Navigation is the strongest
label validator we have — it exercises walkability, adjacency, and
direction, none of which rendering checks.

## Fix chain
1. Schema corrected (gen_r6_labels.py, committed with evidence comment):
   Plane.003 → stairs (high), old `stairs` → wall (medium). Chain
   re-run: labels → props → humanoid → handoff manifest.
2. Blind planner (scripts/r7_route_planner.py — PURE Python, no bpy):
   reads the handoff manifest only; finds floor/stairs/mezzanine by
   kit_label, the actor via Driver.Mannequin bbox (feet = min.z);
   infers stair run axis + direction from bbox adjacency; emits
   route_request.json (waypoints + speeds + assumptions +
   requires_executor). Direction rule HAD to be tightened: a stair
   abutting the slab from OUTSIDE its span decides by adjacency, but a
   stair whose span lies INSIDE the slab span (this one: starts at the
   slab's front edge, runs 5.3 m under it) is bbox-AMBIGUOUS — the
   blind planner now STOP-AND-FLAGS it (exit 4) with manifest evidence.
3. Vision resolution protocol: the principal supplies
   vision_stair_override.json ({top_at_max_end, evidence}) → the
   planner re-runs with --vision-override and marks the route
   vision_assisted=true with the evidence inline. Blind path stays
   pure; the resolution is recorded, not hidden.
4. Executor (scripts/r7_navigate.py): label-driven supports (BVHs built
   from route["labels_used"] — no hardcoded ids), tread-hug raycast
   with INCREMENTAL ray ceiling (last_z + 0.8 — two failed designs
   documented in comments: waypoint-z ceiling teleported onto the slab
   band; per-segment pz ceiling never climbed — the closure bug), the
   fall-through guard (a drop >0.4 m below the held z = open riser /
   void → hold; a real climbing step never does), per-frame root
   keying (location + yaw from tangent, upright — Walk_Loop on a COPY
   via NLA strip with repeat, because Blender 5.2 removed legacy
   Action.fcurves; fresh-bake law respected), and a two-tier numeric
   audit (fine r=0.06/0.12 probe excuses one-paddle-step lateral
   support; coarse r=0.35 excuses edge crossings; anything else = true
   float).

## Verified result
- 705 frames (23.7 s @ 30 fps): living floor → stair base → 9-tread
  climb → mezzanine arrival → walk-in (clamped inside the slab bbox).
- Audit: 177 samples, 0 true floats, 26 excused (all one-riser tread
  transitions, max gap 0.277 m = exactly one riser), 0 held-over-drop.
- Visuals (output/r7/look_nav/): n1 approach mid-stride, n3 ON-tread
  mid-climb under the slab, track_25 stepping onto the treads,
  track_void_75 top-of-stair from the void cam, n4 arrival foot on the
  slab edge. Tracking cams (south + void) have Track-To constraints on
  Driver.Root and are SAVED in loft_nav.blend — scene camera is live.
- manifest_diff handoff→final: 4 findings, 1207 rows unchanged — 2 are
  the intentional nav re-key of Driver's start pose, 2 are the lite-
  strip effect on a texture-driven modifier (Plane.004 evaluated
  geometry collapses when its image is stripped — geometry identical,
  verified bit-level). Zero collateral mutation.

## Gotchas found this round (all fixed in code, in comments)
- BVHTree.FromObject is LOCAL-space: world rays against objects with
  offset origins (Cube.001 origin 0.63 m under the floor) return
  garbage — transform rays in and hits back out.
- Blender 5.2: legacy Action.fcurves is GONE (slotted actions) — use
  NLA strip repeat for looping; do not mutate imported actions.
- Vendor meshes may carry texture-driven DISPLACEMENT modifiers: the
  look-lite lane (strip images) changes EVALUATED geometry — bbox
  deltas vs the full state are expected for such objects.
- A stair labeled from bbox reasoning can be entirely wrong; nav is
  the label validator. (F23: treat "label never exercised by use" as
  low-confidence in reports.)

## Friction queue updates
- F23 (new): labels never exercised by a USE (nav/place/seat) should
  report as unverified-confidence; the R6 wall/stairs confusion is the
  case study.
- F20/F21/F22 unchanged (queued). VK-9/VK-10 still live (QA asks).

## Replay chain (all committed)
r6_loft_fetch.sh → r6_loft_import.py → r6_look_prep.py → look.py
(--angles none) → patch_cuts.json (dry-run first!) → gen_r6_labels.py →
apply_patch --save-blend → gen_r6_props.py → apply_patch →
r6_humanoid.py → look.py regen (handoff) → r7_route_planner.py
(--vision-override for the ambiguous stair) → r7_navigate.py →
r7_nav_shots.py / r7_nav_shots2.py / r7_track_one.py (OOM discipline:
one render per process on the lite copy) → r7_cam_persist.py.
Tests: tests/test_r7_route.py (pure Python, 17 checks, ALL PASS) +
regression battery v1/v5/v6/f17/scope all green.
