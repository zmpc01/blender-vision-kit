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
] + [
    # the SOUTH-EDGE WALL at y=-0.5 (the flow strip's water-walk find,
    # F-TF3): the hardcoded walkable spans the FULL x -6..6 down to
    # y=-6, so agents bled west/east of the apron and strolled ON THE
    # WATER south of the deck edge. This wall (deck-edge line, squares
    # 1.1m wide) closes x beyond the apron while leaving the boarding
    # channel (x -2..2) and the ramp (x +-1.3) clear.
    (x, -0.5, 0.55)
    for x in (-5.45, -4.35, -3.25, -2.35, 2.35, 3.25, 4.35, 5.45)
] + [
    # the FLANK WALL at y=-2.7 (the code-review find, P1-5: agents on
    # the apron could walk east/west PAST the y=-0.5 wall's south face
    # -- the band y -4.45..-1.05, x beyond the apron was still open
    # water-walk). Squares cap at |x|=4.9: the native engine REFUSES
    # blocked bounds outside the walkable (E_InvalidRange -- a 5.9
    # square spans to 6.45 > 6.0); the residual 5.45..6.0 sliver at
    # the rail line is sub-agent-width (0.55 < agent diameter) and
    # impassable in practice.
    (x, -2.7, 0.55)
    for x in (-4.9, -3.8, -2.7, 2.7, 3.8, 4.9)
] + [
    # s25 (the collision/nav round): the sodium lamp posts (tferry_world.py
    # :206-217) stand at x=+/-5.6 INSIDE the +/-6.0 walkable -- undeclared,
    # agents brushed them; r 0.35 = post 0.14 + the 0.15 personal-space
    # margin, squares (5.25..5.95) fully inside the walkable. The
    # MaintGate (tferry_world.py:247, x 6.2) needs NO row: it is OUTBOARD
    # of the walkable edge, behind the +/-6.2 rail line -- crowd-free by
    # construction, and a straddling square is refused by the native
    # engine (E_InvalidRange, measured on the smoke bake).
    (sx * 5.6, y, 0.35)
    for sx in (-1, 1)
    for y in (8.0, 12.0, 20.0, 24.0, 32.0, 34.0)
]

# camera keepouts: (name, px, py, f0, f1) in FRAMES (the F-TD13 law
# FROM BIRTH: the bridge's clamp_keepouts int()s the fields as frame
# numbers). Ground lenses only -- the D6 clamp is 2D-xy and a keepout
# under an aerial punches a hole in the crowd exactly where it looks.
# The CRANE (S11/S12) flies over the OUTBOARD MARGIN/water at x≈-9:
# zero keepout rows, no agent ever walks there (REV-2 F8). The S11
# crane's landing pose x/y never enters the walkable.
CAM_KEEPOUTS_V3 = [
    # fix-wave-2 eyepass: S2/S6/S10 moved WITH their re-framed lenses
    # (the F-TF13 coupling); S8/S9 stay zero-row (outboard x>=7.8).
    # fix-wave-2 eyepass round 2: S2/S6/S10 rows moved again with the
    # round-2 re-frames (S8 stays zero-row outboard at x6.8 past the
    # east rail; S9 xy unchanged).
    ("CAM_S2", 1.4, 7.2, 85, 168),
    ("CAM_S3", -2.0, 30.0, 169, 264),
    ("CAM_S4", 4.0, 38.0, 265, 348),
    ("CAM_S6", -1.8, 7.8, 445, 528),
    ("CAM_S10", 0.9, 4.8, 817, 912),
    # S5/S7/S8/S9: zero rows -- those lenses moved OUTBOARD (x 6.6..8.6,
    # past the east rail, crowd-free by construction: the crane law).
    # S11/S12: the crane flies the OUTBOARD margin/water (x -8.6..-9.2)
    # -- zero rows, no agent ever walks there (REV-2 F8)
]

CAM_KEEPOUT_R = 1.3

# --- HERO_LANES: REMOVED (the code-review find, P1-2: the table was
# DEAD DATA -- the kit-mode chain (bridge/loader/bake2) never consumes
# it; the hero-lane pushout is a v6-ENGINE feature (crowd_v6/sim.py)
# that kit mode does not deliver. Filed as F-TF6: the tdawn film rode
# the v6 engine's pushout; kit-mode films get the raw sim's jostle
# around heroes. The latecomer's lane READS anyway (keepouts + natural
# flow), eye-certified on the stills.)
