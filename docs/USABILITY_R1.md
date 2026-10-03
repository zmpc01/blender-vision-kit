# USABILITY_R1.md — dog-food study, round 1 (session 5)

Method: the principal operates the kit AS A CONSUMER (vision-native agent
building a scene), following AGENTS.md quick start + canonical workflow
only. Every stumble, doc-lookup, guess, and wait is logged with a
friction id. Small fixes landed immediately (K-ids); larger ones were
implemented + verified within the round.

Scenario: "reading nook vignette" — floor + rug, armchair (4 composed
parts), cushion (seat_at), side table (leg+top), mug (animated slide),
book stack, floor lamp. Full arc: template copy → dry-run → look --scene
→ 5 patch chains → look --load-blend → closeup → motion_study →
transient_scan → export glTF.

## Friction log

- **F1 (doc gap)**: AGENTS.md teaches placement ONLY as apply_patch ops;
  nothing tells a scene-script author they may import placement_lib
  directly in build_scene(). Consumer followed the documented model
  (build naive → patch-place) — works, but the choice was invisible.
- **F2 (doc/template drift)**: `common_parser("desc")` — I copied a
  signature the template doesn't use (common_parser() takes 0 args).
  Template tail is the canon; my drift, but 6 scripts needed fixing.
- **F3-NIT (look)**: SUBJECT-OVERFLOW hint fires on the 16m floor plane
  inflating cluster diag (22.7m) while the real subject is ~4m. Hint is
  conservative-correct; could exclude ground-like planes.
- **F4 (K1, 3 bites!)**: `place_on` default footprint fails THE most
  common furniture stacks — tabletop-on-leg, book-on-yawed-book,
  lampshade-on-pole (ring/cone bottoms + small supports). Error message
  is excellent (names footprint='grid'), but the consumer pays 3 cold
  starts to re-learn it. → kit: auto-widen default footprint on miss.
- **F5 (K3+K4, the round's gold)**: animated mug × placement. The anim
  guard fired with an actionable message — but recommended
  `override='keyframe'` which `place_on` (a) rejected as unknown param
  (while the op still applied!) and (b) even where supported, the naive
  "insert key at current frame" left LATER keys at the pre-placement
  pose — measured: mug drifted 20mm INTO the tabletop by f24 (found by
  my own transient_scan — the doctrine loop worked end-to-end).
  → kit: place_on override pass-through + `_rebase_location_keys`
  (shift ALL location keys by the placement delta; verified 0.00mm at
  f1/f12/f24 with the path shape preserved).
- **F6 (inconsistent severity)**: add_* ops HARD-ERROR on unknown
  params; place_on/seat_at only WARN-and-ignore. Same mistake class,
  two behaviors. Also the warn text "(ignored)" was FALSE for
  rotation_deg (the add_finalize handler honors it).
- **F7 (F9, PARAM_DOCS desync)**: three disjoint sources of truth —
  add-op validator list (advertises rotation_deg), PARAM_DOCS (lacked
  it), handler (honored it). The false "unknown param" warning
  misinformed. → kit: PARAM_DOCS synced (add_empty rotation_deg,
  place_on/seat_at override).
- **F8 (consumer craft)**: yawed books interpenetrating (place_on is
  z-only by design); cushion buried 60mm into chairback; books vs
  cushion competing for seat. All correctly caught by audit; scoped
  audit (`{"op":"audit","id":X}`) is the right tool — worked.
- **F10 (K, real bug)**: `move_to` on an EMPTY (the seat_at anchor!)
  crashed: `obj.data.vertices` with data=None. → fixed (non-mesh
  guard + centroid fallback).
- **F11-NIT (motion_study)**: auto-picked objects include STATIC props
  → trajectory dots that read as noise. `--objects` filter exists; a
  static-prop de-prioritization would improve the default view.
- **F12 (K5, real design bug)**: validator intersection check used an
  ABSOLUTE volume threshold (0.001 m³ = 1 L) gating out scale-honest
  findings — a 10cm mug sunk 20% of its height was invisible (probed:
  P1=0 at f24). → kit: flag when EITHER relative pct ≥5% OR absolute
  volume large. Verified: f24 intersection now fires at 20.0%.
- **F13 (K6)**: scanner's intersection findings use bbox-volume proxy —
  false positives possible for round-vs-box corner overlaps (observed:
  Mug×Book1 TRANSIENT f1..f4 that mesh audit would clear). → kit:
  prints "(bbox-proxy; confirm with audit mesh numbers)" on finding
  lines; doctrine unchanged (scanner ranks, gates decide, eyes verdict).

## What worked flawlessly (worth keeping)

- The documented loop itself: dry-run → look → patch(save-blend) →
  look(load-blend) — 2 invocations per iteration, ids from manifest.
- look.py verdicts converged with my visual reads every time (chair
  float: flags + shadow gaps + validator numbers; composition fixes:
  closeup confirmed).
- Audit pair states + scoped audit; place_on error messages taught the
  remedy (footprint=grid) at all three misses.
- The anim guard caught the exact hazard it exists for; its message was
  the thread that unraveled F5.
- transient_scan on my own scene found my own planted-by-accident bug
  (the F5 drift) after the validator fix — full doctrine loop:
  PERSISTENT (TableTop×Mug f9..f24) classified correctly, suspects
  strip generated.
- Chain-abort UX: partial state saved + loud line + physics_gate hint.

## Kit changes landed this round (all pushed)

1. `_rebase_location_keys` + place_on/seat_at/move_to/snap_z override
   rebase semantics (F5/K3+K4)
2. move_to non-mesh guard (F10)
3. validator relative intersection threshold (F12/K5)
4. PARAM_DOCS sync (F7/F9)
5. transient_scan bbox-proxy hint (F13/K6)

## R1 verdict

The core flows (look, patch, placement, motion, transient, ship) held
up under honest consumer use. Every failure was either taught cleanly
by the tool or became a kit fix within the round. The biggest insight:
**placement ops on animated props need path-rebasing, not re-keying** —
found, fixed, and verified in one study loop.
