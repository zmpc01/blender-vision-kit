# USABILITY_R2.md — dog-food study, round 2 (session 5)

Method: identical to R1 (docs-only consumer mode, friction log, fix on
observation). RESET between rounds: fresh scenario, fresh outputs.

Scenario: "crate stack on a pallet" — PHYSICS LANE (R1 covered static
composition + one animated slide): composed pallet, three crates via
physics_settle, TipBox overhang witness via physics_place +
physics_oracle, physics_gate, audit, look, closeup, scene_schema export.

## Loop record

1. look --scene: 6 P1 — 4 expected floatings + **2 runner intersections
   the K5 relative-threshold fix surfaced on its first real run**
   (8.9% overlap — invisible under the old absolute gate). Consumer fix:
   delete the redundant cross runner.
2. Physics chain (settle ×3, physics_place, physics_gate, audit,
   render_viewport) — ALL CLEAN FIRST TRY. Settle verdicts SETTLED×3,
   gate fix_queue 0, audit 0 penetrating.
3. TipBox overhang intent: my dump coordinates were fully off-deck →
   physics honestly dropped it to the floor (PLACED); nudge + re-place;
   physics_oracle at the edge-top z → **TOPPLED** (the witness works:
   half-off at the COG boundary is genuinely unstable); final nudge
   in-deck → PLACED, audit clean.
4. Final look --load-blend: PASS, P0=0 P1=0. Closeup on the settled
   crates: grounded, tight contact shadows, labels legible.
5. scene_schema export: 11 objects, 0 animated — the agent's mental
   model carrier.

## Frictions (R2)

- **F14-NIT**: unknown-op error lists all 35 ops inline — noisy but
  genuinely useful for recovery; keep (logged, no action).
- **F15-NIT**: physics intent needs iterations when the dump pose is
  far from intent (floor vs edge) — that is physics being honest, not a
  kit defect; the oracle is the right witness tool (worked as
  documented).
- No new kit bugs found in the physics lane — consistent with its
  earlier hardening waves. The R1 fixes (K1/K5) proved themselves from
  the consumer seat on their first outings.

## R2 verdict

The physics lane held under honest use. The study loop (observe →
fix → re-verify from the consumer seat) closed cleanly: R1's five kit
fixes + K1 auto-widen all verified in real consumer flows, and the
relative intersection threshold immediately caught a real composition
flaw the old gate silently missed.
