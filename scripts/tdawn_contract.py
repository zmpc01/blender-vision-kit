"""tdawn_contract.py -- the TERMINAL DAWN crowd contract.

Duck-typed per blender-crowd-kit scripts/crowd/previz_bridge.py
_REQUIRED_CONTRACT_ATTRS. THIS module is the ONLY place uppercase
payload-shaped constants live (the exporter's unmapped-story-constant
gate fail-closes on them in the SCENE module -- the scene imports this
module; it never star-imports it).

World (REV-2): a long concourse hall along +Y.
  x in (-10, 10) walkable (hall walls at x = +/-12)
  y in (-6, 27)  walkable (floor slab y -8..32)
  spawn zones far-band-FIRST: zones[0] hosts the chase tail's spawn
  strips (the tail-enders start deepest in the hall).
  hero_pos (0, 0)  = the GATE (the crowd's pursue target)
  flee_target (0, y_hi_all) = (0, 26), inside the far band.

Columns + carts inside the walkable are declared BARRICADES (the
bridge turns them into conservative Blocked squares).
"""
from __future__ import annotations

# --- timeline (the bridge's hard laws; all four are fail-closed) ---
CROWD_SEED = 2026          # TERMINAL DAWN identity input
DT = 1.0 / 12.0            # the 12 Hz LAW (P0-2)
TICK_HZ = 12.0
N_TICKS = 541              # 45 s @ 12 Hz inclusive -- the tick-count law
FPS = 24
TOTAL_FRAMES = 1080

# --- population ---
N_RELEASE = 129            # 120 crowd + 9 chase tail (the loader pins it)
N_CAPACITY = 200           # headroom ceiling only (never shipped)

# --- world ---
CROWD_X_RANGE = (-10.0, 10.0)

# spawn zones: (y_lo, y_hi, count, min_abs_x, x_jitter)
#   far-band-first; zone counts split 40/40/40 (largest-remainder).
#   min_abs_x keeps a 1.6 m centre corridor clear (the hall's central
#   sightline -- the camera lane down the middle stays readable).
SPAWN_ZONES_V5 = [
    (20.0, 26.0, 40, 1.6, 0.55),   # zone 0 (far): chase tail spawns here
    (14.0, 20.0, 40, 1.6, 0.55),   # zone 1 (mid)
    (8.0, 14.0, 40, 1.6, 0.55),    # zone 2 (near)
]

# camera keepouts: (name, px, py, f0_s, f1_s) -- GROUND-LEVEL cams only
# (the D6 clamp is 2D-xy: a keepout under the aerial punches a hole in
# the crowd exactly where the aerial looks). Times are SECONDS.
# iter-2: follows the reframed cameras exactly (S2 added; S5/S6/S7/S8/
# S10 moved; S5/S7/S10 became STATIC pans so the r=1.3 circle covers
# the whole shot -- a dolly exits its own circle, review).
CAM_KEEPOUTS_V3 = [
    ("CAM_S2", 3.2, 12.0, 3.5, 7.0),
    ("CAM_S4", -2.5, 29.5, 11.0, 14.5),
    ("CAM_S5", 9.8, 16.5, 14.5, 18.5),
    ("CAM_S6", -5.2, 7.0, 18.5, 22.0),
    ("CAM_S7", -9.2, 9.8, 22.0, 26.0),
    ("CAM_S8", 3.4, 5.6, 26.0, 30.0),
    ("CAM_S9", 0.4, -7.2, 30.0, 34.0),
    ("CAM_S10", -8.0, -4.0, 34.0, 38.0),
]

CAM_KEEPOUT_R = 1.3

# static obstacles inside the walkable (x, y, r): the colonnade pairs
# (x = +/-7, every 4 m of hall) -- agents route around, never through.
BARRICADES = [
    (x, y, 0.55)
    for x in (-7.0, 7.0)
    for y in (6.0, 10.0, 14.0, 18.0, 22.0, 26.0)
]
