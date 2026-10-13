"""tferry_contract.py -- LAST FERRY's crowd contract (D-TF1 REV-2).

The duck-typed, bridge-shaped contract module (the tdawn_contract.py
shape; uppercase = mapped vocabulary ONLY -- the exporter's
unmapped-constant gate fail-closes on everything else).

The story: a NIGHT FERRY PIER, a BOARDING convergence. The bridge's
single hardcoded pursue target (hero_pos (0,0) +-5 capacity, zero
forks) IS the converge shape -- the gangway throat is built AT (0,0)
so the density peak lands in the choke (REV-2 F2: the bridge will not
move the target; the world moves to the target).
"""
from __future__ import annotations

# --- timeline (the bridge's hard laws; all four are fail-closed) ---
CROWD_SEED = 4711          # LAST FERRY identity input (a NEW seed, not
                           # tdawn's 2026 -- REV-2 F15; ingest hard-fails
                           # without it and the pin is per-film identity)
TICK_HZ = 12               # sim ticks per second
DT = 1.0 / 12.0            # the 12 Hz LAW (P0-2; ingest fail-closes otherwise)
FPS = 24                   # export fps
TOTAL_FRAMES = 1080        # 45.0 s
N_TICKS = 541              # TOTAL_FRAMES/(FPS/TICK_HZ) + 1
N_RELEASE = 129            # 120 zone crowd + 9 crew tail (the loader pins it)

# --- walkable (REV-2 F6: the outboard margin is crowd-free BY
# CONSTRUCTION -- the x 6.2..13 margins carry rails/bollards/lamps/
# crates/the crane track/the deck-level lens, and the ±6.2 pier rails
# need NO barricade rows at all).
CROWD_X_RANGE = (-6.0, 6.0)

# --- spawn zones (y_lo, y_hi, count, min_abs_x, jitter) -- far band
# FIRST (the 9-deep tail spawns in zones[0]'s strips -- structural).
# Counts sum 120 (the verbatim-129 law: 120 zone + 9 tail).
# Nearest spawn y=6 is 1m clear of the capacity box top (y=5).
ZONES = [
    (24.0, 34.0, 44, 1.4, 0.5),   # far: the pier-head bands
    (12.0, 20.0, 40, 1.4, 0.5),   # mid
    (6.0, 10.0, 36, 1.2, 0.5),    # near pockets
]

# the bridge reads SPAWN_ZONES_V5 (the previz crowd_v6 shape name);
# ZONES is this film's authored name -- the alias is the ingest seam.
SPAWN_ZONES_V5 = ZONES

# --- speed plan (REV-2 F1: the envelope law) --
# populations[0].mu + 3*sigma is the GLOBAL max_speed for ALL agents
# (the bridge silently clamps -- measured). far (1.30,0.45) -> 2.65;
# the crew tail (2.30,0.10) -> 2.60 <= 2.65, and every tail sample is
# >= 1.8 m/s so the tail rides Sprint_Loop (crew hustling to stations).
# A boarding crowd WALKS: this is a calmer film than tdawn's flee.
SPEED_PLAN = {
    "far": (1.30, 0.45),
    "near": (1.15, 0.35),
    "crew": (2.30, 0.10),      # the 9-deep tail, one dark-blue callout
}

# --- static obstacles inside the walkable (x, y, r): the gangway
# rails' DECLARED centers sit at x=+-1.55 so the bridge's 2r-wide
# Blocked squares (r=0.55 -> 1.1m wide each) leave the 2.0m choke
# CLEAR between x=-1.0 and +1.0 (REV-2 F7; verify on the first flow
# strip). The kiosk line + the apron's south-edge line close the rest.
BARRICADES = [
    # gangway throat rails (the pinch AT the origin)
    (-1.55, 1.0, 0.55), (1.55, 1.0, 0.55),
    (-1.55, 3.0, 0.55), (1.55, 3.0, 0.55),
    # the ticket kiosk (dressing beside the throat, y≈2 is INSIDE the
    # capacity box so it MUST be declared)
    (3.1, 2.0, 0.7),
] + [
    # bollard pairs on the deck (inboard dressing, declared)
    (x, y, 0.45)
    for x in (-4.5, 4.5)
    for y in (8.0, 14.0, 20.0, 26.0)
] + [
    # the south-edge apron line (the walkable is hardcoded to y=-6;
    # the deck's landing apron spans x -2.2..2.2 only -- close the rest
    # so the box's south half is reachable THROUGH the throat, which
    # makes "boarding" literal) (REV-2 F3)
    (x, -5.0, 0.55) for x in (-5.0, -3.5, -2.0, 2.0, 3.5, 5.0)
]

# camera keepouts: (name, px, py, f0, f1) in FRAMES (the F-TD13 law
# FROM BIRTH: the bridge's clamp_keepouts int()s the fields as frame
# numbers). Ground lenses only -- the D6 clamp is 2D-xy and a keepout
# under an aerial punches a hole in the crowd exactly where it looks.
# The CRANE (S11/S12) flies over the OUTBOARD MARGIN/water at x≈-9:
# zero keepout rows, no agent ever walks there (REV-2 F8). The S11
# crane's landing pose x/y never enters the walkable.
CAM_KEEPOUTS_V3 = [
    ("CAM_S2", 1.6, -2.2, 85, 168),
    ("CAM_S3", -2.0, 30.0, 169, 264),
    ("CAM_S4", 4.0, 36.0, 265, 348),
    # S5 moved OUTBOARD (7.4,20 -- past the east rail, crowd-free by
    # construction): zero rows for it (the crane law).
    ("CAM_S6", -5.0, 8.2, 445, 528),
    # S7 + S9 moved OUTBOARD (6.6,5.2 / 7.0,6.5 -- past the east rail,
    # crowd-free by construction): zero rows (the crane law).
    # S8 also outboard now (7.2,10.5): zero rows.
    ("CAM_S10", -2.0, 3.4, 817, 912),
    # S11/S12: the crane flies the OUTBOARD margin/water (x -8.6..-9.2)
    # -- zero rows, no agent ever walks there (REV-2 F8)
]

CAM_KEEPOUT_R = 1.3

# --- hero lane keepouts (the authored heroes sweep through the crowd;
# agents push out of their lanes -- the tdawn HERO_LANE law) ---
HERO_LANES = (
    # the Latecomer's edge run: pier head (x≈4.8) down to the rail gap
    {"x0": 4.4, "x1": 5.2, "y0": 34.0, "y1": 8.0, "r": 0.9},
    # the gap crossing + choke approach
    {"x0": 4.0, "x1": 0.4, "y0": 8.0, "y1": 0.6, "r": 0.9},
)
