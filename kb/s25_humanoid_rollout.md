# kb/s25_humanoid_rollout.md — the humanoid rollout + collision/nav
# round receipts (session 25, five films + tform re-export)

The per-film detail behind the Session-25 laws (.agents/SKILL.md
"SESSION 25 LAWS") and the design doc
docs/DESIGN_humanoid_rollout_s25.md. The D6 pattern = the tform
worked example rolled to the other five films: RH x_bot rig
assemblies on the cache anchors + UAL mannequins on the keyed
heroes, env-gated per film (TDAWN/TFERRY/TGREEN/TSQUALL/TFOG_HUMANOID=1)
so prior revs stay byte-reproducible.

## The per-film POP_PLAN table (rig counts = the cache pins)

| film  | rigs | zone groups (contract order → group, n, tint)                     | ordinals law     |
|-------|------|--------------------------------------------------------------------|------------------|
| tdawn | 129  | commute_far 40 slate (0.30,0.32,0.36) / commute_near 40 (0.26,0.28,0.33) / commute_near2 40 (0.33,0.31,0.29) / chase 9 rust (0.45,0.22,0.16) | CHASE-LAST: zones in contract order, chase tail LAST (zone sizes equal, the tail is not) |
| tferry| 129  | deck_fore 44 ink (0.16,0.18,0.22) / deck_mid 40 drab (0.24,0.23,0.21) / deck_aft 36 slate (0.20,0.22,0.24) / crew 9 oilskin amber-drab (0.35,0.30,0.18) | CHASE-LAST (ZONES rows 44/40/36 + the verbatim-129 law 120 zone + 9 tail) |
| tgreen| 129  | stream_n 40 (0.28,0.30,0.34) / stream_s 36 (0.34,0.30,0.26) / cross_wait 44 (0.22,0.26,0.24) / crew 9 (0.40,0.28,0.16) | CHASE-LAST (SPAWN_ZONES_V5 rows 40/36/44) |
| tsquall| 135 | vendors 6 tarp ochre (0.45,0.30,0.14) / zone0_fast 44 (0.28,0.26,0.30) / zone1_mid 40 (0.30,0.28,0.26) / zone2_far 36 (0.26,0.28,0.27) / queue 9 (0.18,0.20,0.24) | VENDORS-FIRST: the 6 count-1 vendor pops id-sort to ordinals 0-5, then zones 6-125, chase 126-134 (the s19-B4 id-sort) |
| tfog  | 126  | waiters 66 platform drab (0.27,0.28,0.31) / cohorts 51 (0.23,0.25,0.28) / doorq 9 (0.16,0.19,0.24) | PINNED SLICES: cache ordinal order == POP_PLAN ingest order — waiters [0:66], cohorts [66:117], doorq [117:126] (tfog_bake.py:194-200) |
| tform | 102  | drill 24 / watchers 72 / drummers 4 / officer_a 1 / officer_b 1 (the s25-1 worked example, unchanged) | the group-tint split follows POP_PLAN ingest order |

Principals (bind_principals + ride_principals, UAL_SCALE
1.75/1.589): tdawn Master+Runner; tferry Deckhand+Latecomer; tgreen
Statue+Runner; tsquall Bystander (the one hero); tfog
LatePassenger+Stationmaster; tform the 2 keyed heroes. Identity
colors ride from each film's _heroes table (the branch-a law).

## The obstacle row inventories (the film-lane collision/nav round)

Engine gaps (path planning, hard walls, animated obstacles) stay
filed on upstream issue #15 — the film lane declares only WHICH
statics the sim knows about. Rows are (x, y, r) → Blocked squares
((x-r,y-r),(x+r,y+r)) unless noted; r = footprint + the 0.15 m
personal-space margin; straddling squares are E_InvalidRange-refused.

- **tdawn** (+10 rows on BARRICADES, tdawn_contract.py): 4 benches
  (±4.6, y 12/20, r 0.75) + 3 pylons (r 0.60) + 3 RB luggage carts
  (r 0.70). The perimeter walls bound the walkable already — no rows.
- **tferry** (+12 rows): the sodium lamp posts at x ±5.6 INSIDE the
  ±6.0 walkable, r 0.35 (squares 5.25..5.95), y 8/12/20/24/32/34.
  The MaintGate (x 6.2) is OUTBOARD — crowd-free by construction,
  NO row (a straddling square would be refused).
- **tgreen** (+17 rows): the Statue plinth (0,0) r 0.55 — the
  EMPIRICAL envelope: r 0.90 fails at 129 (E_SceneCompile), r ≥ 0.60
  near the origin kills the bake (E_UnreachableDestination — the
  hero_pos destination IS the plinth top); 0.55 + agent 0.34 = 0.89
  ≥ the 1.2×1.2 half-diagonal 0.849, so capsules cannot clip the
  granite. + NW signal pole (-4.2, 3.35) r 0.45 + 15 N bollards
  (x -28..28 step 4, r 0.30). The SE pole + S bollard line sit
  OUTSIDE the walkable (y0 = -6.0 vs lip -6.15) — no rows.
- **tsquall** (+16 EXACT rects, tsquall_bake.py `_rects`, via the
  scene2 dataclasses.replace blocked= — never fuzzy r-rows):
  facade_w/e, shopfront_w/e, back_wall, food_counter, bench_w1/w2/e1,
  planter_nw/ne, trash_w/e, bollard_f1/f2/f3. The GATE-LINE slalom
  stays UNDECLARED by the jam law (sealing it jams the flow — the
  arrival-delta gate proved the rest clean).
- **tfog** (+2 bins, blocked table now 19 rows, tfog_contract.py
  BLOCKED): bin_w (-19.15,-1.55,-17.85,-0.25) / bin_e mirrored —
  r0.56 trash bins ON the platform. The W-exit stairs straddle the
  walkable edge — no row (half-out by construction).
- **tform**: dais = floor inlay, no drum object — obstacles complete
  as-is (the cache reproduced byte-exact unchanged).

## The export receipts

- Caches (payload pins, all green): tdawn fb50b6b9 / tferry 9ae53649
  / tgreen d9e2f234 / tsquall 2457bf87 / tfog 6b5b4313 / tform
  9024057c (reproduced BYTE-EXACT from the wiped sandbox — unchanged
  inputs).
- THE 24FPS TIMEBASE LAW: the FBX imports (rig/walk/idle/UAL) flip
  scene.render.fps 24→30 silently; the GLB plays at the SCENE fps →
  a 1.25x fast film. gate17 (key-interval bands) caught it: chase
  steps 2.1-2.7 m/s apparent = sim 3.8 × 1.25. tform_2 slipped UNDER
  the band at drill speeds — the LATENT bug SHIPPED; tform_3
  re-exports the fix. humanoid_crowd._fps_guard saves/restores
  around every import (5 sites, loud); the gates probe clamps to
  frame_end + warns on non-24 fps.
- The ARRIVAL DELTA GATE: any obstacle-declaration change proves
  baseline-vs-new probe arrivals MATCH before the geometry scan is
  trusted — tsquall 84/38 IDENTICAL (1+1/tick232), zero jam.
- The ANCHOR-GATE FRAME LAW: the gate samples the loader's LAST
  keyed frame — plan_frames(n_ticks, dt)[-1] = f1080; the old
  formula landed f1079 (2/3 across the final step — the off-by-1
  class; parked-at-end films masked it reading 0.0).
- The STRIP DATA-NAME LAW: per-group tint copies name the MESH DATA
  to match the object (Hum.Group{gi}.Body{j}); Object.copy shares
  data, so the rename must land on the unique data copy — objects
  renamed with FBX data names matched 0 bodies (the 6-b find).
- The OOM LEVER: export_frame_step=2 at the bake's own 12Hz — halves
  the 28M-key animation bake; gates are interval-normalized.
- The EXEMPT ROW: the tsquall slip faller (cast.faller_ordinal →
  anchor name via the 1:1 anchors[i] ↔ ordinal i pairing) carries
  the ~80-deg tumble overlay — a documented motion-gate EXEMPT row;
  the printer is shape-agnostic (EXEMPT rows lack root/verdict/why).
- STAGING: six packages staged — tdawn_4 / tferry_2 / tgreen_2 /
  tsquall_2 / tfog_2 / tform_3 (129/129/129/135/126/102 rigs, 12
  Cycles stills + 96 filmstrips each) — app commit bab6098, stage +
  commit in the SAME micro-step (the tform_2 loss class → the
  STAGE-COMMIT law).
- THE OPEN EYE GATE: the orchestrator's vision channel was DOWN at
  close — the 72 stills await the principal's certification; sheets
  at /home/sync/s25_sheets/ (one _sheet.jpg per film).

## The next queues (from HANDOFF session-25)

browser playback smoke (true-24fps playback in the review app) ·
the lowercase sweep debt (CAST/BEATS/CAMS_V3/SYNOPSIS on the four
older films' next exports; tfog's 9 knobs are the worked example) ·
night-market · the upstream issue #15 comment (fields-seam
evidence) · the RH clip fetch recipe (vendor/rh_clips — 2899 walk /
2781 idle committed; fetch via the release-volume octet-stream law
+ zstd).
