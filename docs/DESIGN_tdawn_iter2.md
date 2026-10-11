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

## REV-2 folds (peer review TD-REVIEW-2 — all adopted, with corrections)

1. **D-i2-1 retime corrected**: hold at (1.1, 1.3) not (0.4, 1.5) — the
   old hold sat behind the Master from CAM_S8 (the occlusion it was
   meant to fix); dive-arc peak (31.21, 0.4, **-0.35**, 0.38) — inside
   the portal, not 0.6 m short of it; doors **f730-780** (gap 4.08 m at
   f750, 1.77 m at f767 through; the 730-800 draft read "not closing");
   through/hold keys at y **-1.85** (the -1.6 draft chest-clips the new
   glow wall 0.08 m from f767 on). Stumble MOVED INTO S7 (t 22.3-22.95;
   the old dip keyed at f476-490 = S6 while every signal pointed at S7).
2. **Keepouts**: S7 row corrected to (−9.2, 9.8) — the draft row was
   2.24 m from its own camera; S5/S7/S10 made STATIC pans (a dolly
   exits its r=1.3 keepout circle — pre-existing flaw); S10 row
   (−8.0, −4.0); S2 (3.2, 12.0) verified out-of-frustum hole; out-of-
   walkable disc overlap on S5/S7 accepted (wall-side squeeze, 4 s).
3. **Tunnel exact dims** (all TD.GateDark, void+old throat deleted):
   sides (0.18, 0.95, 3.60) @ (±3.49, −0.975, 1.80); top (6.80, 0.95,
   0.18) @ (0, −0.975, 3.51) — 5 mm clear of the header; floor
   (6.74, 1.12, 0.06) @ (0, −0.81, 0.05) — z 0.02 base (no coplanar
   floor fight); back/glow (6.74, 0.08, 3.60) @ (0, −1.41, 1.80).
   SealEdge strips PARENTED to the doors (x-keys alone leave them
   parked). Parked-door wings (±3.4..6.8, no pocket) ACCEPTED as set
   dressing — the dim seal-edge bars telegraph the seal.
4. **Palette**: lands post-bake_tier2 (per-agent users==1 copies
   verified in crowd_v6/bake2.py:278-281; RB carts users>1 → copy
   first); mesh.copy() preserves the Key datablock; the lib keeps
   palette[0]; _anchors' shared-mesh writes REMOVED.
5. **Rest pose**: arms CONSTANT-y 0.12 (min surface y 0.055 > 0.05 →
   the whole arm selects; the tapered draft left 43% frozen and would
   tear at every swing); shoulder sphere r 0.205 @ 1.345.
6. **Title**: size 0.55 (the 1.55 draft was 2× frame width), z 3.1,
   emission keyed 0.15 → 0.55 at f1009, hide_render keyed False at
   f1009 (it photobombs S5 AND S11 at emission 0 otherwise — base
   color renders); stills-authoritative (glTF carries no material
   emission animation; gate 9 drops nothing — keyed hide is kept with
   a NOTE).
7. **Emission caps**: GateGlow seal key 1.4 → 0.95; GateLight 3000 →
   2000 W; board rows 2.4 → 1.7 peak / 0.55 low (A/B phase-offset);
   SealEdge peak 1.3 (tiny-area accent, look-verify); windows left at
   1.6; throat keys single-sourced from _seal_f0/_seal_f1.
8. **Missed-items batch**: S3 aim z 0.6 → 1.3; S8 aim (0.3, 1.2, 1.15)
   (the old aim pointed NORTH — the empty-hall still); S5 aim-track
   lead 0.35 s @ x 1.2; sfx stumble 560 → 539, vault_seal 790 → 730;
   board rebuild decision (D-i2-7) recorded; pylon restyle (G3)
   recorded: steel_light + TD.PylonFace ≤ 0.7 both Y sides.
