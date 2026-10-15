# USABILITY_TS1_squall.md — the SQUALL ledger (the fourth film)

> Session 17b (2026-10-14). The film: docs/DESIGN_squall.md REV-3.
> Staged: tsquall_1 rev 2. The kit dog-food: M6 Queue/Portal/HoldPosition
> + M5 ragdoll + Groups + read_events→sfx + the bridge composition law.

## The frictions

- **F-TS1 the layer-invisible film path (the enabling fix, landed)**:
  the film npz VIEW read BASE cache bytes only — kit layout layers
  (ragdoll physics, PIN, …) never reached the film, and the z channel
  was hard-coded zeros. Fix: the sidecar-gated composition post-pass in
  `to_previz_cache` (set_layout_layers + read_tick splice over the
  union of layer tick ranges, BEFORE the pre-spawn hold/keepout/world
  transform) + real z from composed rows. Unlayered caches stay
  byte-identical (r054 72/72 held). Test: test_ts1_composed_view
  13/13. (test_ts1_composed_view lives in the blender-escape-previz
  checkout — the loader/composed-view code is sibling-repo; this kit's
  tree carries no copy. Don't hunt for it here.)
  The 4-h review's paired fix: the `layout_composed`
  provenance marker in the npz meta + the composed-aware ground-contact
  gate (crowd_kit/gates.py) — the ballistic rows are exempt INSIDE the
  declared range, the planar law keeps its teeth outside.
- **F-TS2 the r109 default-flip determinism trap (landed)**:
  ingest_contract's chase_frame default flipped to "world" (r109) —
  a re-bake of any belt-frame film silently re-bands the zones and
  moves the destination. Fix: chase_frame="belt" pinned EXPLICITLY in
  all four film drivers.
- **F-TS3 the portal-axis naming trap (filed)**: PortalAxis names the
  CROSSING direction — NORTH_SOUTH builds the wall running E-W at
  y=center.y. EAST_WEST would have built a wall at x=0 THROUGH the
  arrival box. (nav/portal.rs:20-28; caught by audit 4-d before code.)
- **F-TS4 the emission-interval hijack (filed, driver-guarded)**: the
  native reads ONE global interval from the ID-SORTED populations[0]
  — an appended low-id population with build_zombie_population's
  default interval 5 silently re-times the whole film. Driver law:
  interval=1 on every appended pop + the all-intervals assert.
- **F-TS5 the loader N-pin (landed)**: load_kit_cache hard-pinned
  n_agents == crowd_v6.contract.N_RELEASE (129). Parameterized via
  expected_agents= (the default keeps the 129 anchor law verbatim;
  the kwarg threads through _honesty_asserts).
- **F-TS6 the tripwire/pipeline seam (the 4-h ship blocker, fixed in
  pair with F-TS1)**: the escape lane's ground-contact gate would
  fail-closed on any composed ballistic row (z 0.45 vs the ±1cm band)
  — the film lane's exporter never runs it, but the kit's own
  delivery pipeline refuses the beat. Fixed by the provenance marker
  + the composed-aware gate.
- **F-TS7 the keepout-drift class (the 4-i P1-3, fixed in rev 2)**:
  the S6 keepout row survived the S6i reframe — a stale row clamps a
  crowd hole mid-arcade with NO camera there. Law: the camprobe
  certification and the contract's keepout row are ONE edit (and the
  silent-replace class nearly shipped it — assert-guard every
  string-replace on a cam table).
- **F-TS8 the declared-but-unimplemented class (the 4-i P1 sweep,
  fixed in rev 2)**: the rain wrap froze after f55 (three keys), the
  RAIN_ARC had zero consumers, the bystander keys were literals
  desynced from the fall frame, the sfx vocabulary was all-unknown
  (a near-silent soundtrack). Law: every contract-declared behavior
  gets a consumer or gets deleted before the ship.

## The tool laws (new, generalizing)

- **The marker-camera law**: shot timeline markers override
  scene.camera inside their span — every probe/ladder tool must null
  them (the flowstrip knew; three ladder runs rendered CAM_S7's pose
  before the lesson re-landed).
- **The axial-crane law**: an opaque roof makes the packed interior
  visible ONLY through the colonnade axis — no outside-above crane
  can see under it; the S11d cert is the pattern.
- **The ragdoll walk-clip class**: the physics layer moves the
  ORIGIN; the mesh keeps the walk clip — the film fix is the
  per-channel tumble overlay (rot_x/rot_y keyed AFTER removing
  bake2's flat whole-euler x/y fcurves via the owning channelbag —
  5.2 slotted actions never touch action.fcurves).
- **The wall-occlusion probe class**: a camera south of a 3m facade
  cannot see a north-rim beat (the S5 smoke still caught what the
  audits missed) — low cameras near set walls get a smoke still
  BEFORE the framing round.

## The receipts

- The probe verdicts: the doorway ROUTES (92/135 in the box), the
  queue line exists (6 in the window column at cache end, head
  released t=218), vendors hold their posts, bakes 3-4s.
- Determinism: the v2 re-bake reproduced the faller (Zed.0050, graze
  t=186) and the arrival counts exactly.
- The trilogy → quadrilogy: tdawn_3 (dawn) / tferry_1 rev 2 (night) /
  tgreen_1 rev 2 (noon) / tsquall_1 rev 2 (storm dusk — rain, wet
  ground, thunder flashes, the neon title).
