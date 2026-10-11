# DESIGN — TERMINAL DAWN iteration 2 (session 13, the refinement round)

> Input: the principal's EYES on all 12 staged tdawn_1 stills + strips
> (the QA catalog below). This doc records the iteration-1 fix set.
> Peer review: TD-REVIEW-2 (sub-agent, code-level; no vision).

## The QA catalog (what the eyes found, 12/12 stills)

- G1 **Crowd = one color.** All agents read steel-blue; the designed
  10-color muted palette is INVISIBLE. Root cause: `_anchors` calls
  `ob.data.materials.clear()` on the SHARED library mesh datablock —
  every anchor links the same mesh, so the per-index assignment
  collapses to the last write. (Fix: per-agent mesh copy + assignment
  AFTER the kit branch materializes.)
- G2 **The gate reads as a flat bright screen (S6/S10).** The throat
  glow plane sits at y=-0.15, PROUD of the void box's hall face,
  filling the whole opening — zero depth cues. (Fix: replace the
  solid void box with an open 4-wall tunnel + the glow as the BACK
  wall at y≈-1.41.)
- G3 **Pylons read as black monolith glitches** (S3/S4/S7/S11/S12).
  (Fix: lighter steel + warm emissive sign face.)
- S1: white roof arch cuts the bottom-left corner (lens clips the
  y=-4 arch); crowd reads as a regimented grid (spawn rows) — palette
  variation + a later still frame (f76) soften it; cam nudged.
- S2: the "departure board" is a flat orange slab (no rows, no
  flicker read); windows do NOT glow during their own beat (the glow
  keys start at f169, AFTER the S2 window). (Fix: rebuild the board:
  dark panel + 4 amber emissive rows, two alternating flicker
  materials dying at f233; window glow keys start at f1 and pulse
  through S2.)
- S3: beige out-of-focus band across the bottom edge (aim too low).
  (Fix: aim z 0.6 -> 1.3.)
- S5: colonnade column fills the right third of frame for half the
  shot; the Runner is a tiny teal sliver; the rest pose reads
  "backpack hunch" (arms angle too far forward + oversized shoulder
  sphere). (Fix: track moved to x=9.8, lens 34, aim leads the Runner;
  commuter mesh: arm hand y 0.17->0.09, shoulder r 0.235->0.205.)
- S6: the Master is a 2px amber dome buried in crowd backs; gate
  blown white. (Fix: cam raised to z 2.6 above head height, gate
  surround emission capped, tunnel depth replaces the flat slab.)
- S7: giant tan blur (column at the lens) left third + black pylon
  center. (Fix: cam shifted to (-9.6,12.0), pylon restyled.)
- S8 **fails its intent**: the still is an EMPTY hall — no Master, no
  gate, no Runner. (Fix: complete reframe — cam at (3.4,5.6,2.35)
  looking SW at the Master AT the gate line; the Runner reads
  left-of-him mid-approach.)
- S9 **fails its intent**: the still (f750) shows the Runner standing
  before a dead-brown wall — the dive happened at f726-745, BEFORE
  the representative frame; the doors' dark occlusion eats the glow.
  (Fix: RETIME the dive so the arc peak lands ON f750 — the still
  frame; doors close f730-800 so the Representative frame shows the
  Runner INSIDE a visibly-closing portal; emissive leading-edge
  strips on the doors keep the narrowing slit HOT and readable; the
  throat recessed glow backs the silhouette.)
- S10: ~60% blank wall. (Fix: pull back+up (-8.5,-4.5,3.2), aim the
  sealed gate + pressed crowd; the glowing center seam carries the
  "sealed" read.)
- S12 **no title**: "TERMINAL DAWN" is nowhere in frame. (Fix: text
  mesh converted to geometry, warm cream emissive keyed 0 -> 0.55 at
  the title sting f1009, floated facing CAM_S12 at z 4.2.)
- S11: reads. Keep.

## The decision set (for review)

- D-i2-1: retime the Runner tail (hold at the line t28-30.4, dive arc
  peak exactly f750, through by f767) + doors f730-800; BEATS.the_dive
  30.2 -> 31.2. Keepouts re-declared for every moved ground cam; the
  bake is re-run (deterministic, 3 s).
- D-i2-2: the gate tunnel replaces the void box (5 pieces, all
  TD.GateDark except the TD.ThroatGlow back wall); doors get emissive
  leading edges (TD.SealEdge, keyed with the seal).
- D-i2-3: crowd palette lands POST-LOAD (after bake_tier2): per-agent
  mesh copy only when data.users > 1, then palette by index — zero
  loader forks.
- D-i2-4: the commuter rest-pose edit (arms/shoulders) changes the
  shape-key BASE mesh; the geometric arm-selection contract
  (|x| .15-.55, y > .05, z < h*1.35/1.75+.02) is preserved: hand y
  0.09 > 0.05, arm x extents inside the band.
- D-i2-5: the title is a CONVERTED text mesh (curves do not export to
  glTF); no name matches the atmosphere regex; the floating-object
  validator flag is accepted noise (documented F-TD2 class).
- D-i2-6: keepout rows follow the cameras exactly (S2 added; S5/S6/S7/
  S8/S10 moved); the aerial/high cams stay keepout-free (the D6 law).
