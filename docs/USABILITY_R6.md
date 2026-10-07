# USABILITY R6 — real stitched-interior LEVEL: cut, label, compose, hand off

Round: R6 (session 9). Asset: Blender Foundation "Loft" demo —
https://download.blender.org/demo/cycles/loft.blend (561 MB gzip-wrapped
.blend, saved ~2010, Blender 2.9x format; CC demo file, provenance noted
per the round-9 discipline). Two-level loft apartment, 6.5 x 20.0 x 6.7 m,
1200 mesh objects, 3.97M polys, vendor camera + 4 area lights.

## Why this asset
The user's standing ask: download a BIG STITCHED INTERIOR online and push
the cut/label workflow until a labeled level is usable by non-vision
agents (pillar/floor/stairs/platform/deco taxonomy). Polyhaven's model
library is furniture-only (verified: 521 models, zero room-scale
interiors — semantic + keyword surveys). The Blender demo CDN filled the
gap with a genuine two-level interior WITH stairs, mezzanine, kitchen,
partition panels — every element of the target taxonomy.

## Import lane (honest import state)
`r6_loft_fetch.sh` (gzip integrity check) → `r6_loft_import.py`: open
AS-IS, inventory 1225 objects, world bbox, add OverviewCam (vendor camera
untouched), re-save. Normalizations, all recorded:
- Blender 5.2's compressed save packs external images and ABORTS on the
  45 texture refs pointing at the author's disk (`/d/Blender/...`,
  3ds-max "Map #..." names) → detached, counted, kept 122 packed images.
- 9 missing addon libraries (Botaniq pots etc.) — vendor quirk, logged,
  harmless (linked data-blocks render as nothing).
- `bpy_prop_array` matrix-mult gotcha bit twice (bound_box corners need
  Vector wrap) — same class R5 hit; now a known law.

## LOOK on a huge scene (two measured limits + fixes)
1. OOM: the 561MB packed blend killed look.py → look-lite copy (strip
   images, orphans_purge, 561MB → 99MB) — workbench display colors don't
   need image pixels (D15 sync reads node basecolors).
2. Annotation explosion: the honest validator flagged 1198/1200 objects
   (real levels are dense AABB-overlap fields) × 12 wireframe boxes each
   = 12k annotation objects → second OOM + unreadable red spaghetti.
   Fix: FLAG_CAP=60 in look.py (P0-first ordering, printed cap note,
   full set stays in look_manifest.json).
3. Preset angle offsets (5m) land inside walls on a 20m interior →
   aimed survey shots (`r6_survey.py`, `r6_survey2.py`: 9 shots, two
   blocked by walls — repositioned) + frustum raycast grids as the
   "which object is that pixel" oracle.

## The semantic map (vision pass)
From survey renders + manifest bbox cross-reading:
- lower floor: entry/living (sofa modules Object003.*, rug Plane.002,
  arc floor lamp Cylinder.001, sideboard, coffee table Box015.017),
  dining (2 Windsor chairs Cube.004/005 facing the olive worktable
  island), country kitchen y 13.3-15.9 (kitchen.* x841: cabinets, red
  counter, sink unit, pink ladder, utensils), partition panel walls
  (Panel_* x145) with doorways.
- shell `Cube`: walls + mezzanine slab (z≈2.9, 42 slab faces) + ceiling
  (z 5.86-6.0) + a 68-deg space-saver STAIR hidden at x 3.30-3.50,
  y 7.31-8.48 (found by frustum raycast: 58 rays hit the diagonal).
- the real walkable floor: `Cube.001` — full-extent 123.7 m²
  zero-thickness plane at z 0.00, its own object all along.
- upper floor: bedroom (12-part bed assembly, lounge chair + floor lamp
  cluster = Sketchup* — later corrected, see handoff), railing band,
  interior window glazing (Window + Window Panel.*), shelf units
  (Object001-004.*), exterior curtain wall (Plane/Plane.001).

## Region cuts on the welded shell (the flagship demo)
`patch_cuts.json` — 4 dry-run-verified split-region cuts on `Cube`:
| cut | faces | captured bbox (m) | render check |
|-----|-------|-------------------|--------------|
| floor_slab | 5 | z 0.002, y 7.31-17.08 | dup band; DELETED (real floor = Cube.001) |
| ceiling_slab | 18 | z 5.86-6.00 | ok |
| mezzanine_slab | 42 | z 2.70-2.92, y 8.47-15.97 | ok |
| stairs | 14 | x 3.30-3.50, y 7.31-8.48, z 0-2.91 | pre/post renders identical context |

Cut order: floor → ceiling → mezzanine → stairs LAST (its box overlaps
the mezzanine y-range; cutting the slab first removed 7 would-be-stolen
faces — 21 dry-run faces vs 14 actually cut).

## mesh_prepare — new op (fused-face pathology)
The front floor (y<7.31) would not cut: dry-run reported verts_in_region
10-27 but faces_to_cut=0 at ANY box. Signature: faces FUSED across the
floor→wall fold ("fully inside" unsatisfiable). New op
`mesh_prepare(id, mode:"triangulate")` (semantic_lib + apply_patch +
PARAM_DOCS + AGENTS.md): converts n-gons to tris (19 on the shell,
114→163 faces). Post-prepare dry-run STILL 0 faces → the front floor
was never in the shell; the real floor was Cube.001 all along. The op
stays: fused imports are the generic case; the diagnostic signature
(verts yes, faces no) is now documented.

## Labeling (one patch, 1155/1200 meshes)
Generated programmatically (`gen_r6_labels.py` → patch_labels.json):
architecture (floor Cube.001, wall Cube, ceiling x3, mezzanine,
stairs) + verified families (kitchen_unit x841, partition_panel x145,
bed x12, sofa_module x31, shelf_unit x6, interior_window x7,
exterior_window x2, railing x12, lounge_chair x12*, floor_lamp x11*,
plant x5, rug x2, table x2, sideboard, deco x63, chair x2**).
Confidence: high = render-verified; medium = name-pattern/bbox-derived.
48 objects (4%) left honestly null. floor_slab dup deleted.
\* corrected after the blind handoff (see below). \** added post-handoff.

## Compose — making the level usable
Placements via kit ops on LABELED supports (patch_props.json):
- book_red → sideboard: TOUCHING
- ball → floor (Cube.001): contact 0.0mm
- lantern → mezzanine_slab: TOUCHING
- mug → table (Box015.017): F17 grid refine fired (12→192); first
  attempt PENETRATING 3.82mm (uneven recessed top) → clearance 0.006 →
  CLEAR 5.95mm. Edge-overhang lesson: first attempt xy sat 5cm from the
  support bbox edge and found NO support even at 192 samples — center
  placements are the law.
Humanoids (r6_humanoid.py, kit UAL hero lane): Driver on the living
floor with Walk_Loop treadmill keying toward the kitchen; Girl standing
on the mezzanine (z 2.91 read from the MANIFEST — the handoff protocol
working as designed). Compose verified in 3 renders (c1 living+book+
Girl-upstairs, c2 mezzanine+lantern, c3 walk corridor).

## Blind stress test (protocol v2 on the level)
Handoff: loft_compose.blend + output/r6/handoff/look_manifest.json +
AGENTS.md contract. Fresh non-vision agent, 3 tasks:
- T1 book on the upstairs bed: DONE after 2 honest failures — the bed
  is 12 stacked shells (tops 3.415-3.82); largest-footprint rule was
  ill-posed (two shells within 0.4% footprint, larger one occluded);
  resolved by topmost-surface law + align_to_surface on a 13.6-deg
  slope; audit 7 pairs all CLEAR (0.27mm on the rest surface).
- T2 cushion near the mezzanine lounge area: DONE, TOUCHING, 2.36m from
  Girl.Root; AND it flagged a REAL anomaly: the lounge_chair-labeled
  objects sit at y≈0 (not the mezzanine) — closeup confirmed the
  cluster is a PENDANT LIGHT; my labels were wrong. Corrected:
  pendant_light x23, floor_lamp → Cylinder.001 (the actual arc lamp),
  chair x2 (Cube.004/005, the dining chairs the agent had reported as
  "unlabeled pedestals"). THE HANDOFF CATCHES PRINCIPAL LABEL ERRORS.
- T3 bait "place a mug on the dining table": WITHHELD with evidence —
  exactly one table-labeled object exists (y≈2, wrong zone), the dining
  chairs were unlabeled; identity judgment = vision-required; no
  mutation, no relabel. Exactly the contract behavior.
- manifest_diff (run independently by me): 2 findings (the two
  additions), 1209 rows unchanged — zero collateral movement.

## Honest validator noise on real levels
The labeled level reports P0=742 P1=878 (look) — kitchen units 1mm
apart, panels touching, beds stacked: real dense geometry is an AABB
 false-positive field. The v2 containment filter skips shell-vs-prop
pairs, but furniture-vs-furniture adjacency stays. Queued: level-aware
thresholds (adjacency tolerance by label class). Not a blocker: the
numbers are stable and diffable (manifest_diff is the work tool).

## Friction (new, for the queue)
- F20: place_on's "no support surface found" doesn't hint the
  occluded-support case (grid retry already auto-fires); topmost-surface
  law lives only in AGENTS.md (blind agent found it — good — but the
  error could teach it).
- F21: audit's CLEAR gap numbers vs the room shell read absurd (1.8m
  "gap" for an object resting INSIDE the room) — AABB-vs-mesh sampling
  mismatch; harmless but confusing to blind consumers.
- F22: level-aware validator thresholds (see above).
- VK-9/VK-10 still live from QA lanes (unchanged).

## State chain (all in output/r6/, reproducible from the fetch script)
loft.blend (CDN) → loft_import → loft_look (lite) → loft_cut_arch →
loft_labeled → loft_props → loft_compose → loft_blind_work (agent) →
loft_final. Committed lane scripts: r6_loft_fetch/import/look_prep/
survey/survey2/compose_shots/humanoid + gen_r6_labels.py (harness side).

## Next queue
1. R7 candidate: multi-room level (stairs BETWEEN floors used by a
   walking actor — nav across the space-saver run), or Sketched-by-
   hand loft variant to test cross-asset schema reuse.
2. F20/F21/F22 friction fixes.
3. Validator level-mode (adjacency tolerance by label class).
4. VK-9 re-vendor + VK-10 example hunk port (QA asks, still live).
