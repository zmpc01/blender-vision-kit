# D16 dogfood — semantic labeling of an imported interior (session 7)

Fixture: `scripts/d16_interior_fixture.py` → `output/d16/interior_import.blend`.
Simulates a downloadable level/interior asset: `Mesh.000` (welded room
shell: floor grid + 3.5 walls + lintel + engaged pillar, ONE component
after remove_doubles), `Mesh.001` (props sheet: 10 disconnected islands
in one object), `Mesh.002` (lamp: 2 islands). Zero semantic names.

## The pass, measured

| Step | Command surface | Result |
|---|---|---|
| LOOK | `look.py --load-blend interior_import.blend` | 4-angle grid + manifest (3 opaque ids, kit_label null); validator caught a REAL fixture bug on first fire (box() double-size → walls 2×, sunk 1.25m — P0s honest, fixed in fixture) |
| SPLIT dry-run | `split_mesh` ×3 | shell = **1 component** (welded — loose split correctly refuses to help), props = **10**, lamp = **2**; zero residue |
| REGION cut | `split_mesh` mode=split-region, region box read off the closeup | engaged pillar out of the welded shell: 6 faces, bbox exact, walls intact (the loose-parts-no-op case the user flagged) |
| SPLIT | `split_mesh` mode=split ×2 | 10 + 2 parts; largest keeps source id (`Mesh.001` = ball); `_pNNN` naming deterministic; materials inherited |
| NAME | 3 macro closeups (barrel/cone/pillar) + dims/face-count cross-check | 14 parts identified; evidence = angle + geometry agreement |
| LABEL | `label_objects` rename:true, 14 ids, report `output/d16/labels_report.json` | 13 renamed (duplicate `table_leg` → `_2.._4` via suffix law); props-first writes |
| LOOK verify | re-look + manifest JSON | 14/14 rows carry kit_label, all set; names semantic |
| SAVE | `--save-blend interior_labeled.blend` | deliverable state |

## Success criterion (D16 doc) — MET

Non-vision sub-agent (zero renders, zero images) received ONLY the
manifest JSON + AGENTS.md/kb docs. It then: grounded the 4 floating
table legs (`snap_z bottom`), seated `table_top` on them, seated the
`ball` on the tabletop (move_to first — it predicted the keep_xy trap
from docs), lowered `lamp_head` onto `lamp_post`. Final audit:
18 pairs, 15 TOUCHING / 3 CLEAR, **zero penetrating**, every goal
contact 0.0mm. Principal's eyes confirmed the assembled scene renders
as reported (ball on table, legs grounded).

## Frictions found (new)

- **F17 (K1 follow-up)**: `place_on` footprint auto-widen `grid` (12×12)
  misses small inset supports — leg spans [0.11,0.19]/[0.81,0.89] on a
  2.4m top fall between sample columns by 0.01m. Sub-agent used the
  documented `snap_z` fallback. Fix idea: footprint grid density ∝
  support-size estimate, or raycast the mover's own bottom perimeter
  downward instead of sampling.
- **Validator on room interiors**: the shell's AABB contains every prop
  → P0 "intersection" spam is inherent to AABB checks (pre-split it was
  ONE useless 27m³ blob; post-split each pair is at least per-part
  interpretable). Candidate v2: skip pairs where one object's label is
  shell/room-like AND the other is inside it (containment ≠ collision).

## Fixture authoring gotchas (for future import fixtures)

- `primitive_cube_add()` defaults to size=2 — a scale-span box() helper
  MUST pass size=1 (first fixture had 2× walls sunk 1.25m; validator
  caught it immediately — good loop).
- Coplanar-adjacent welded features (lintel flush with wall tops) are
  NOT box-isolatable: "faces fully inside" captures wall-top faces too.
  Box-cutable features need a protruding footprint (the engaged pillar).
- `--closeup` is single-object per invocation (last one wins).
