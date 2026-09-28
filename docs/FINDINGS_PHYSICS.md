# FINDINGS: physics-gated placement — usability + convergence program
(weeks of session 12; kit HEAD at writing: entering-classifier commit)

## What was built

`scripts/physics_place.py` — four ops composing bullet rigid bodies with
the exact geometric library (placement_lib), per
`docs/design_physics_place.md` v3 (two fresh-context review gates):

- `physics_settle` — gravity finds rest poses; guarded snap closes
  bullet's margin gap to EXACT contact; verdicts AT_REST / SETTLED /
  SLIPPED / TOPPLED / REPAIRED_BY_PHYSICS / REPAIR_SIMULATED /
  ESCAPED / PENETRATING_AT_END / NO_SUPPORT_AT_END.
- `physics_place` — placement through physics (lift clamp → settle →
  snap → full-neighbor audit); auto-environment terrain.
- `physics_oracle` — the jeep-door witness: move to request, settle as
  sole mover, classify REACHED / BLOCKED (blocked_by named) /
  FELL_BELOW / SLIPPED / REFUSED_PENETRATING (names the obstruction) /
  ESCAPED; scene restored byte-equal on every path (incl. refused).
- `physics_gate` — scene-level REJECTION gate: static audit +
  directional settle-verify (upward margin-pop = rest; downward/lateral
  = finding) → PASS/REJECTED with an EXECUTABLE fix queue;
  `fail_hard` exits 2.

Plus placement_lib hardening: crossing-ENTERING classifier (a spear
ENTERS the solid; a resting overhang only exits past a side-face
plane — kills both the 325mm phantom pen and keeps X1 14/14).

## The measured law that shaped everything

**Margin-pop law**: a body at rest pops UP ~2.0mm per contact level in
any sim (bullet contact margin), compounding in stacks (~8mm at level
3). Every classification in the stack now encodes it:
- settle: pop + <tol → AT_REST ("sub-tolerance sim jitter" note);
- gate verify: upward displacement is never a finding; only
  downward/lateral is;
- snap cap 8mm (closes the pop to exact 0.0mm contact);
- group settle works once snap measures against FRESH BVH per step
  (stale trees measured pre-snap poses → the 3.94mm phantom seam) with
  an 8×8 footprint grid and a support-plane filter (h ≤ own bottom —
  the sandwich case).

## Usability program (fresh-context subjects, docs-only)

- Round A (3 subjects): 2×S1 root cause = sims without world colliders
  (place/oracle/gate-lane) → 16.85m void-falls reported SETTLED/PASS;
  verdict semantics collisions; report honesty (end_bottom_z = origin).
- Round B (2 subjects): gate PASS shipped its own findings as notes;
  oracle refused-path leaked the move; snap stale-BVH residuals;
  mover-x-mover audit blindness (caught a planted pen in our own T5k!).
- Round C (2 subjects): the pop law measured independently by both;
  PASS unreachable at tol 1.0; fix queue unsafe on exact scenes.
- Round D (2 subjects): gate loop CONVERGED (REJECTED→repairs→PASS
  with empty queue; negative test works; no corruption). Remaining:
  group-settle cap override (handler 3.0 vs lib 8.0 — fixed), oracle
  NESTED blind spot (fixed), µm-coplanar crossing phantom (fixed via
  entering-classifier).

Every subject claim was re-verified against their artifacts before
fixing; several "tool bugs" were fixture bugs (the janitor desk was
itself a floating slab; T5k's book2 was planted 5mm deep) — ground
truth discipline applies to fixtures too.

## Native-vision study (vision_flow_study.py, /tmp/vision_flow)

- Plain workbench renders (before vs after repair): NOT decidable —
  even native vision cannot see 12mm penetration or 55mm float at
  scene scale. (Re-confirms the founding X2 measurement.)
- heat_view: UNMISTAKABLE — penetrating mug = bottom half RED; repaired
  = uniform grey. Vision's role: instant triage of WHERE to look.
- seam_views: mm-precise but framing-sensitive (gotcha #57 fill_frac).
- The documented vision-agent loop: heat_view triage → numeric audit /
  physics reports decide → repair → heat_view + audit re-verify.
  Vision never decides mm.

## Kit state after the program

- T1-T4 + T5 (a-k) + X1 ALL PASS from cold clone.
- AGENTS.md: physics section (loop, lanes, pop law, report access,
  env semantics, vision flow), decision-tree branches, gotchas #58-#62.
- Fact base F1-F14 committed with probes under experiments/physics_facts/.

## Remaining (deliberate) edges

- Violent depenetration of deep/wedged pens can eject sideways — loud
  (NO_SUPPORT_AT_END / ESCAPED) and recoverable via move_to+place, but
  not convergent by itself.
- oracle answers reachability only for the z-column (documented);
  lateral path-planning is out of scope.
- AGENTS.md gotcha numbering has historical duplicates (16-21 twice;
  two 50s) — cosmetic; renumber in a docs pass.
