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

# camera keepouts: (name, px, py, f0, f1) in FRAMES -- GROUND-LEVEL cams only
# (the D6 clamp is 2D-xy: a keepout under the aerial punches a hole in
# the crowd exactly where the aerial looks). Row shape: (name, x, y,
# f0, f1) -- FRAMES. F-TD13 (session-14): the tdawn_1/2 rows carried
# SECONDS here per the old docstring while the bridge's clamp_keepouts
# int()s the fields as FRAME numbers -- every tdawn camera keepout was
# inert outside f3-38 (the v6-belt schema seam; the values were shot
# spans in seconds). Now in the bridge's de-facto unit: shot spans.
# iter-3: follows the reframed cameras (S5's north vantage, S10's 3/4)
# + S12's dolly (the r=1.65 circle at the dolly midpoint covers both
# poses; the S12 row is NEW -- the title-shot lens was never kept out).
CAM_KEEPOUTS_V3 = [
    ("CAM_S2", 3.2, 20.0, 85, 168),
    ("CAM_S4", -2.5, 29.5, 265, 348),
    ("CAM_S5", 0.5, 20.8, 349, 444),
    ("CAM_S6", -5.2, 7.0, 445, 528),
    ("CAM_S7", -9.2, 9.8, 529, 624),
    ("CAM_S8", -4.5, 4.0, 625, 720),
    ("CAM_S9", 1.6, 7.0, 721, 816),
    ("CAM_S10", -8.5, -3.2, 817, 912),
    ("CAM_S12", 7.7, 16.75, 1009, 1080),
]

CAM_KEEPOUT_R = 1.3

# static obstacles inside the walkable (x, y, r): the colonnade pairs
# (x = +/-7, every 4 m of hall) -- agents route around, never through.
BARRICADES = [
    (x, y, 0.55)
    for x in (-7.0, 7.0)
    for y in (6.0, 10.0, 14.0, 18.0, 22.0, 26.0)
] + [
    # session-14: the gate-wall pilasters (tdawn_world gate dressing) sit
    # ON the converge line at y=0 — undeclared, the crowd clips them
    (x, 0.0, 0.55)
    for x in (-8.0, -5.2, 5.2, 8.0)
]
