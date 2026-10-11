# Placement & Physics Deep Reference

## apply_patch placement ops

- `move_to`: world-space, origin-safe move (reference: bottom-center/centroid/origin). `set_location` moves the ORIGIN; on origin-baked meshes that acts relative — use `move_to` for world-space placement.
- `place_on(id, supports, clearance)`: lifts mover, rests on TOP of named supports (raycast/grid from above). Solves Z ONLY (keep_xy=true default). If mover STARTS PENETRATING the support, `place_on` is UNDEFINED — repair first. `footprint`: 'bottom' (downward-facing verts), 'grid' (samples bbox bottom), 'inset' (seat lips). `align_to_surface`: true rotates onto incline.
- `seat_at(id, seat, align)`: needs an anchor EMPTY named by `seat`. `reference='bottom'` lands bbox bottom-center at anchor; `reference='origin'` lands the origin itself. Author the empty: `{"op":"add_empty","id":"Anchor","location":[...]}`.
- `snap_z(id, target_z, reference)`: exact world z placement.
- `physics_settle(objs, environment, apply, repair_penetrations)`: gravity finds the pose. Verdicts: AT_REST / SETTLED / SLIPPED / TOPPLED / REPAIRED_BY_PHYSICS / ESCAPED / PENETRATING_AT_END. `apply:"none"` = pure verifier (scene restored byte-equal).
- `physics_place(id, drop_mm, snap, apply)`: lift → settle → guarded snap → audit. Verdicts: PLACED / PLACED_OVERLAP / NO_SUPPORT / ESCAPED. Everything else is terrain automatically.
- `physics_oracle(id, target_z, tol_mm)`: the WITNESS — why can't X sit at z? Verdicts: REACHED / BLOCKED (blocked_by names) / REFUSED_PENETRATING / FELL_BELOW / SLIPPED / TOPPLED / ESCAPED. Scene always restored byte-identical.
- `physics_gate(fail_hard)`: scene-level rejection gate with executable fix queue. Each fix item is a runnable patch op. `fail_hard:true` exits non-zero for CI/shell pipelines. Set-dressing scenes MUST scope `verify_movers` (wall-mounted furniture collapses under gravity-only verify).

## audit op

`{"op":"audit","output":"path.json"}` — exits non-zero on penetration by default. Pair discovery: every mesh pair whose AABBs come within `clearance_pad_mm` (default 100). Per-pair states: PENETRATING (penetration_mm), TOUCHING, NESTED (contained — often intended), CLEAR (clearance_mm). `clearance_mm: null` on PEN/NESTED = read `penetration_mm`.

**F21 law — gap numbers against room shells are NOT contact truths**: when one side of a pair is a room-shell object (labels room/shell/wall/floor/ceiling/mezzanine), the shell's AABB spans the whole room, so `CLEAR gap` / `NESTED` / big `penetration_mm` numbers for that pair are AABB-geometry artifacts (an interior object is always "inside" the wall's box), not surface distances. The mm-class truth vs a shell comes from a raycast to the shell's actual surface (the nav/seat probe pattern), never from the pair audit. Filter shell-side pairs out of "floating/penetration" reasoning; validator v2/F22 skip them for the same reason.

**"Nothing floats" proofs**: audit only sees pairs within the pad — a 300mm floater appears in NO pair. Use `physics_gate` (scene-level) or `scene_schema --with-bounds` for scene-wide floating checks.

## seam_views / heat_bake / ascii_height_map

Visual confirmation: plain viewport 0/4 states decidable; macro ~1/4; single section 2/4; heat render 4/4 (RED contact / GREEN <5cm / GRAY far); section_pair 4/4 with exact mm.

## Physics hard limits

- **Concave receivers** (bowls, jeep interiors): Bullet uses CONVEX_HULL/BOX — hull lies about cavities. Model as compounds of convex parts. Never MESH shapes (slow, brittle).
- **Animated/skinned objects** never enter the sim (excluded with reasons). Animated PASSIVE bodies are NOT static — keyed env objects follow their keys (use `animated_env` exclusion).
- **Deep/wedged penetrations** can depencentrate sideways (uncontrolled) — settle defaults to REFUSE; `repair_penetrations:"physics"` opts into recorded repairs.
- **BOX collision centered on ORIGIN** not bbox — off-origin mesh gets displaced collision (slab z 0..0.3 with origin at z=0 gets collision z -0.15..+0.15). Use CONVEX_HULL for origin-offset geometry.
- **Hull-hull contacts** rest with ≈Σmargins gap (2mm at margin 1mm), compounding per stack level. BOX-BOX rests exact. Guarded snap closes residual (cap 8mm covers ~5 levels at 1mm margin).
- **`transform_apply(scale=True)` zeroes location** (4.5.13) — avoid. Physics ops no longer need scale baked.
- **RB point cache survives teardown** — always `frame_set(1)` before every sim.
- **RB sim pose lives only in `matrix_world`** — commit before reading geometry.

## Verification protocol

After ANY placement-affecting change, chain an `audit` into the SAME patch:
```json
{"op":"audit","output":"output/audit.json"}
```

Build order: static supports → place_on/seat_at/snap_z → audit clean → animate() → final audit at hero frames.

## One-shot fix workflow

```json
{"load_blend":"scene.blend","mutations":[
  {"op":"audit","output":"output/audit.json","fail_on_penetration":false},
  {"op":"place_on","id":"Mug","supports":["Table"],"clearance":0.0},
  {"op":"seat_at","id":"Driver","seat":"SeatAnchor","seat_mesh":"SeatCushion"},
  {"op":"audit","output":"output/audit_after.json"},
  {"op":"seam_views","a":"Driver","b":"SeatCushion","out_dir":"output/seam"},
  {"op":"render_viewport","output":"output/check.png","angle":"persp","engine":"workbench"}
]}
```
