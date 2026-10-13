"""tgreen_contract.py -- GREEN LIGHT's previz contract (the single
authority for the crowd story: zones, speeds, keepouts, timeline).

REV-3 of docs/DESIGN_green_light.md is the design of record; the
round-2 source probe (task 3-d) fixed the geometry:

* walkable y ceiling 5.0 (zone2 y_hi 4.0 + the bridge's +1.0 law) --
  the hardcoded hero_pos capacity box (-5,-5)..(5,5) is INCLUSIVE-
  LEGAL against it (contains_bounds inner.max <= outer.max).
* ZERO sim barricades: arrived agents freeze at the ±5 box edge and
  become steering-ghosts (the two-rank ghost freeze) -- the freeze
  line, not a blocked square, protects the statue. Any plaza-scale
  barricade seals a nav pocket and the bake refuses
  (UnreachableDestination, scene.rs:335-358).
* keepout rows are FRAMES (the F-TD13 law from birth) and ONLY for
  ground lenses inside the walkable (the hole law keeps aerials
  row-free).
* the speed envelope is PER-FILM: max_speed = populations[0]'s
  mu+3sigma (the bridge applies zone0's envelope to ALL agents) --
  chase 2.60 <= far-cap 2.62, asserted by the bake driver pre-bake.

Timeline: 12 Hz ticks, 541 ticks, 24 fps, 1080 frames -- the kit
laws (DT/N_TICKS/FPS/TOTAL_FRAMES fail-closed at ingest).
"""
from __future__ import annotations

DT = 1.0 / 12
N_TICKS = 541
FPS = 24
TOTAL_FRAMES = 1080
N_RELEASE = 129          # the loader pins this (loader.py:234-243)
CROWD_SEED = 8123        # new seed (tdawn 2026, tferry 4711)

# street runs EAST-WEST; every zone row spawns HALF its count on each
# side of the |x| center exclusion (the bridge strip law) -- the two
# curbs are two halves of the same populations; east/west identity is
# a SCENE-SIDE palette split by the sign of the spawn x.
CROWD_X_RANGE = (-30.0, 30.0)

# (y_lo, y_hi, count, min_abs_x, x_jitter)
# zone2's y_hi 4.0 is LOAD-BEARING: walkable y_hi = 4.0 + 1.0 = 5.0
# >= the hardcoded capacity box max.y 5.0 (the F17 fold -- raising it
# was the only way the box ingest survives; do not lower it).
SPAWN_ZONES_V5 = [
    (-1.6, 1.6, 40, 20.0, 0.35),   # zone0: the near lanes (fast steppers)
    (-1.0, 1.0, 36, 23.0, 0.35),   # zone1: the center-of-curb mass
    (0.2, 4.0, 44, 25.0, 0.35),    # zone2: north-edge drift (y_hi 4.0
                                   #  = the walkable-ceiling load)
]

# camera keepouts: (name, px, py, f0, f1) in FRAMES. Ground lenses
# inside the walkable ONLY (the F20 ledger; the aerials S1/S4/S5/
# S11/S12 are row-free -- a keepout under an aerial punches a hole
# exactly where it looks). rr = r + agent_radius = 1.64.
CAM_KEEPOUTS_V3 = [
    ("CAM_S2",  -4.4,  1.2,  85, 168),
    ("CAM_S3",  -2.0,  4.6, 169, 264),
    ("CAM_S6",   0.0, -5.2, 445, 528),
    ("CAM_S10", -1.5, -3.8, 817, 912),
    # S7/S9: the cams moved OUTBOARD (y 5.5/6.0 > walkable 5.0) --
    # rows dropped. Aerials row-free (the hole law): S1/S4/S5/S11/S12.
]

CAM_KEEPOUT_R = 1.3

# --- SPEED_PLAN (the driver's single authority; the driver adds NO
# numbers of its own). Envelope law: the bridge pins max_speed =
# populations[0]'s mu+3sigma on EVERY agent -- far's envelope is the
# film's cap. chase 2.30+3(0.10) = 2.60 <= far 1.42+3(0.40) = 2.62.
# Sprint band: VIEW speed >= 1.8 -> Sprint_Loop (chase samples
# 2.0-2.6 sprint; far's sigma 0.40 lets ~10% of civilians cross 1.8
# -- accepted, eye call). Native clamps: samples in [0.4, 2*mu],
# playback <= 1.5*preferred.
SPEED_PLAN = {
    "far":   (1.42, 0.40),   # zone0
    "near1": (1.30, 0.12),   # zone1
    "near2": (1.18, 0.10),   # zone2
    "crew":  (2.30, 0.10),   # the chase 9 = the sprint wave (F5:
                             # stream-toned, NOT red; they reach the
                             # freeze line FIRST ~f300)
}

# Arrival ledger (F21, approximate -- the bake is the truth):
#   sprint wave  ~f300 (first freeze-line contacts)
#   zone0        f170-560   zone1  f333-577   zone2  f406-560
# The still completes ON CAMERA through S5 (349-444).

# BEATS: (id, t_seconds, label) with t = (f-1)/24 (the exporter law).
BEATS = [
    ("b_pour",    0.0,  "the pour ignites with the light"),
    ("b_call",   3.50,  "the green MAN ignites (f85)"),
    ("b_freeze",  7.25, "the first rank freezes (f175)"),
    ("b_still",  14.5,  "the still completes (f349)"),
    ("b_flip",   18.5,  "the hand blinks against them (f445)"),
    ("b_break",  22.0,  "the runner gambles (f529)"),
    ("b_hesitate", 30.0, "the hesitate at the plaza edge (f721)"),
    ("b_reach",  33.5,  "he reaches the statue (f805)"),
    ("b_reset",  42.0,  "the light resets (f1009)"),
]
