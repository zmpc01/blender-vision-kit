# USABILITY_TF1_last_ferry.md — the LAST FERRY build friction ledger
# (session 15, the second film: tferry_1)

The tdawn ledger is USABILITY_TD1_vision_film.md (its laws transfer:
factory-startup purge, the glow-surface law, one-EEVEE-process-per-shot,
marker-safe passes, the comments-db repo-local law). This file records
what the SECOND film — a NIGHT film on a different geometry — added.
Filings F-TF1..F-TF6; the night laws extend kb/tdawn_vision_film.md's
AgX section.

## F-TF1 — the hardcoded-workdir friction family (CLOSED)

Three surfaces hardcoded `/home/z/work/...` and every fresh sandbox had
to hand-patch them: the tdawn bake driver, the scene modules'
TPREVIZ_SCRIPTS default, the stills runner's `cd`. The tferry build
retired the family: sibling-of-this-repo resolution with env override
(TFERRY_CROWD_KIT / TFERRY_PREVIZ_SCRIPTS / TPREVIZ_SCRIPTS), and the
bash runner self-locates via
`cd "$(dirname "$(dirname "$(readlink -f "$0")")")"`.
LAW: a repo script must never name an absolute sandbox path — resolve
from `__file__`/`$0` or accept an env override.

## F-TF2 — "export-complete on paper" (CLOSED, the process law)

The session-14 slice's crowd branch hand-rolled a `json.load` of a
chars shape that does not exist and SKIPPED the anchor assembly +
`bake_tier2` — the scene module read as done but had never been
exercised past `--dry-run`. The first real flow-strip run failed loudly
(`'str' object has no attribute 'data'`).
LAW: a scene module is not DONE until a flow strip runs THROUGH the
kit loader (anchor rename law + bake2 pairing pre-assert + palette
post-materialize). Dry-run green only proves the build path.
The tdawn shape to copy verbatim: `_build_crowd_anchors` (120 crowd
Zed.NNNN + 12 chase Zed.ChasePNN — 3 are RB slots the loader renames;
the loader law is loader.py §9.1) → `load_kit_cache(ctx)` →
`bake_tier2(ctx)` → palette AFTER materialize.

## F-TF3 — the water-walk class + the E_InvalidRange law (CLOSED)

The bridge's hardcoded walkable is a RECTANGLE (x −6..6, y −6..42);
the physical deck south of the throat is an APRON (x ±2.2) over water.
Unbarricaded, agents strolled onto the water west/east of the apron —
found on the first flow strip, invisible to any dry-run. Closed with
TWO wall rows (y=−0.5 and y=−2.7, squares r=0.55).
NEW LAW (the hard way): the native engine REFUSES blocked squares
whose bounds exit the walkable (`E_InvalidRange blocked:barricade_N:
blocked bounds must stay inside their walkable region`) — a square at
x=5.9 (r=0.55 → span 6.45) is illegal; cap centers at 5.45 (span
exactly 6.0) and leave the sub-agent-width sliver.
LAW: the flow strip is a GEOMETRY SEAM detector, not just a retiming
tool — run it before ANY camera work.

## F-TF4 — the sfx "id"/"name" contract seam (CLOSED)

`emit_sfx_events` emitted `{"id": ...}`; the app loader silently drops
non-`{name|kind, frame}` events (the beat markers vanished from the
timeline — found by the parallel lane in-app). Scene-side fixed to
`name`. LAW: the package payload contracts are the APP's, not the
exporter's — when the app drops a key silently, diff a working
package (tdawn_3) against the broken one.

## F-TF5 — the vendor wheel version seam (CLOSED, parallel lane)

The vendored crowd wheel (1.0.0) predates the bridge's needs (1.5.4:
`create_session` motion_matcher kwarg) — the bake dies with an opaque
TypeError until the wheel is reinstalled from
`blender-crowd-kit/vendor/blender-crowd/addon/blender_crowd/wheels/`.
The bootstrap recipe (HANDOFF) carries the wheel step; keep it.

## F-TF6 — kit mode has no hero-lane pushout (OPEN, kit candidate)

`HERO_LANES` in the contract is DEAD DATA: the pushout lives in the v6
ENGINE (crowd_v6/sim.py); the kit-mode chain (bridge → loader → bake2)
never consumes it. tdawn rode the v6 engine's pushout; kit-mode films
get the raw sim's jostle around heroes. The tferry stills held anyway
(the keepouts + natural flow), so the fix is a kit-side feature
(candidate: the loader could accept HERO_LANES and emit per-hero
"soft keepout" clamps in to_previz_cache), not a scene-side hack.

## The night-light laws at shot scale (L-TF1..L-TF4 extensions)

- **The emission ceiling is DISTANCE-dependent**: a 1.9-strength neon
  bar reads saturated at 15m+ (S1 aerial) but clips to a pastel-pink
  monolith at 4m (the S2 close-up). Near-subject glow caps ~1.1-1.3.
- **Every story beat needs its own diegetic light**: the choke pile
  read as black lumps until the GANG SPOT (200W sodium over the
  gangway); the S9 gate crossing drowned until the GATE WORK LIGHT
  (140W). Emissive materials glow but do not LIGHT — at night, light
  WHERE THE BEAT HAPPENS, not where the set is decorated.
- **The pairing shot needs BOTH heroes keyed**: the Deckhand (the
  gang spot + the checkpoint lantern), the Latecomer (a hot lane lamp
  420W/110° so his hold lane is inside the pool's radius — at 95° he
  sat on the pool edge and vanished).
- **Spill discipline survives night**: mag spill 16W → 8W (the pink
  wash was painting the wrong subjects); the cyan bar's spill stays
  low + steep (the green-mush law holds).
- **Two wall rows of light beats**: L-TF4's silhouette floor ladder
  (sky 0.12 + practicals + exposure +0.3) held; the +2 east pools and
  the 70W deck fill (the parallel lane's pass 2) were the difference
  between "dark" and "night".

## The merge-cost lesson (two lanes, one film)

This session ran in PARALLEL with another session building the same
film; three remote collisions (the framing set, the night-light pass,
the sfx key) were each resolved fetch-inspect-rebase with EYE
arbitration of the competing certified sets. Cost: ~40% duplicate
work. The protocol held (zero force pushes, both sets eye-certified
before adoption), but the cheaper path is a pre-flight comment on the
app repo or a WIP branch push EARLY ("I am building tferry's night
pass") so the lanes split by SCOPE, not by file.

## What the second film proved about the kit

The kit survived a DIFFERENT film (night, converge, choke, keyed
crane, flip board, water geometry) with ZERO exporter changes and
ZERO bridge forks — the contract-shape + loader-law seams were the
only structural frictions, and both are now documented with their
fixes. The camera-probe tool (F-TD12) was NOT needed this film (no
occlusion mysteries — the flow strip caught the geometry seams
first). The review-app loop (stage → browser → comments) worked
first-try from the tdawn recipe.
