"""tfog_contract.py -- THE EXPRESS's film contract (the custom-scene fork).

This film does NOT use bridge.ingest_contract (the belt-frame grammar):
an island platform 64x8 m fits NO hard-coded ingest band (belt mode
hard-codes the walkable south edge y=-6; world mode the spawn strip
y[16,22] -- audit round-1 P0-b). The driver authors the CrowdScene
field-by-field and re-asserts the ingest-contract laws manually:
project_id=PREVIZ_PROJECT_PIN, tick_hz=12, interval=1 per population,
12Hz/541/24fps/1080/seed.

Everything here is CONTRACT-AUTHORITATIVE: the scene module reads
CAM_KEEPOUTS + the train key paths + the board program; the bake
driver reads the population plan + the field spec.

REV-3 design: docs/DESIGN_express.md. Cache N = 126 (66+51+9); the
loader pin override carries 126 (F-TS5). The two heroes (LATE
PASSENGER, STATIONMASTER) are Blender-side keyed actors OUTSIDE the
cache (the drill's branch-a law).
"""
from __future__ import annotations

# --- the timeline (the x2 law: 1 tick = 2 frames) ----------------------
DT = 1.0 / 12.0
T_END = 45.0
N_TICKS = 541              # 45 s @ 12 Hz inclusive
FPS = 24
TOTAL_FRAMES = 1080

# --- the world (z-inverted: platform top z=0, track beds z=-0.9) -------
PLATFORM = ((-32.0, -4.0), (32.0, 4.0))     # the walkable rect
WALKABLE_ID = "platform"

# blocked squares (x_lo, y_lo, x_hi, y_hi) -- fully inside the walkable
# (the E_InvalidRange law) and MATCHING the built world geometry:
# 4 benches (seat 1.8x0.5 + legs) at x={-12,12} y={-2.4,2.4}; 6 canopy
# columns (cyl r=0.32) on the center line at COL_XS; kiosk 2.6x2.0 at
# (26,-2); 6 lamp posts (cyl r=0.12) at y={-3.2,3.2}.
BLOCKED = (
    ("bench1", (-12.95, 2.12, -11.05, 2.68)),
    ("bench2", (-12.95, -2.68, -11.05, -2.12)),
    ("bench3", (11.05, 2.12, 12.95, 2.68)),
    ("bench4", (11.05, -2.68, 12.95, -2.12)),
    ("col1", (-25.34, -0.34, -24.66, 0.34)),
    ("col2", (-15.34, -0.34, -14.66, 0.34)),
    ("col3", (-5.34, -0.34, -4.66, 0.34)),
    ("col4", (4.66, -0.34, 5.34, 0.34)),
    ("col5", (14.66, -0.34, 15.34, 0.34)),
    ("col6", (24.66, -0.34, 25.34, 0.34)),
    ("kiosk", (24.6, -3.1, 27.4, -0.9)),
    ("lamp1", (-20.14, 3.06, -19.86, 3.34)),
    ("lamp2", (-0.14, 3.06, 0.14, 3.34)),
    ("lamp3", (19.86, 3.06, 20.14, 3.34)),
    ("lamp4", (-20.14, -3.34, -19.86, -3.06)),
    ("lamp5", (-0.14, -3.34, 0.14, -3.06)),
    ("lamp6", (19.86, -3.34, 20.14, -3.06)),
)

# --- destinations -------------------------------------------------------
# waiters: the W exit stair mouth (the horizon law, round-2 R1: spawn E
# x 20..30, capacity rect x -30..-26 => min(spawn->goal) = 46 m; at the
# envelope cap 1.55 m/s x 22 s = 34.1 m -- zero arrivals inside the
# blast window, asserted at EVERY tick in [168,264]).
DEST_WAITERS = {
    "id": "west_exit",
    "point": (-28.0, 0.0),
    "capacity": ((-30.5, -1.6), (-26.0, 1.6)),
}
# cohorts: waiting spots near the center door (arrival = the group
# stands -- reads as waiting to board; the door zone stays dark).
DEST_COHORTS = {
    "id": "door_concourse",
    "point": (0.0, 0.8),
    "capacity": ((-3.4, -0.6), (3.4, 2.6)),
}
# queue: admitted agents ghost AT the door threshold = boarded (the
# S11 doorway-silhouette framing law).
DEST_QUEUE = {
    "id": "door_threshold",
    "point": (0.0, 3.5),
    "capacity": ((-1.2, 2.9), (1.2, 3.9)),
}

# --- the population plan (cache N = 126; ingest order = the cap law) ---
# (id, count, spawn rect, speed (mu, sig), dest, graph)
SPAWN_E = (20.0, -3.2, 30.0, 3.2)     # the E spawn band (all three pops)
POP_PLAN = (
    # populations[0] owns the envelope cap (the F2 law)
    ("waiters", 66, SPAWN_E, (1.10, 0.15), DEST_WAITERS["id"], "nav_west"),
    ("cohorts", 51, SPAWN_E, (1.05, 0.15), DEST_COHORTS["id"], "nav_door"),
    ("doorq",   9, SPAWN_E, (1.10, 0.15), DEST_QUEUE["id"], "queue_door"),
)
N_CACHE = 126
CROWD_SEED = 5150
# spawn distance pacing: the queue walks ~24-30 m to the tail first, so
# the line forms AFTER the blast window (the drain-schedule lever).

# --- M6 attachments -----------------------------------------------------
# 17 groups x 3 members over the cohorts (ids resolved from the probe
# bake; two-bake covenant).
N_GROUPS = 17
GROUP_SIZE = 3
GROUP_MAX_SEP_M = 2.4

# the portal IS the center door on the S face (the wall at constant y
# -> the crossing is N-S -> NORTH_SOUTH, the F-TS3 law).
PORTAL = {
    "id": "center_door",
    "center": (0.0, 3.0),
    "width_m": 4.0,
    "axis": "NORTH_SOUTH",
}
QUEUE = {
    "id": "door_q",
    "portal_id": "center_door",
    "admission_capacity": 1,
    # 9 slots ALONG the S face (y=3.3 on-platform): head nearest the
    # door, tail strung W. Raw meters -- authored on the platform.
    "slots": tuple((1.8 - 0.9 * i, 3.3) for i in range(9)),
}

# --- the DANGER field (the blast beat; base-bytes visible) -------------
FIELD = {
    "name": "express_pass",
    "type": "DANGER",
    "center": (0.0, -8.5),        # the N track at the S5 camera x-band
    "radius": 7.5,                # covers the platform band y -4..-1
    "strength": 3.5,              # m/s desired-velocity AT center (R2)
    "falloff": "SMOOTH",
    "t_active": (14.0, 22.0),     # SECONDS = ticks 168..264 = frames 336..528
}

# --- camera keepouts: (name, px, py, f0, f1) FRAMES --------------------
# Ground lenses inside the walkable ONLY (F20); rr = 1.3 + 0.34 (the
# R5 law: keepout circles must NOT intersect queue slots/door dests --
# the driver asserts it).
CAM_KEEPOUT_R = 1.3
CAM_KEEPOUTS = (
    ("CAM_S2", -18.0, -1.5, 0, 190),
    ("CAM_S6", -8.0, 1.2, 528, 672),
    ("CAM_S9", 4.6, 1.0, 792, 912),
)

# --- the train key paths (the scene module keys; FRAMES) ---------------
# express_root x: -200 (hidden W) -> +40 across frames 336..528 linear
# (192 m / 8 s = 24 m/s; head enters the N face at f~340, clears E by
# f528). local_root x: -120 -> -24 across 672..792 (decel), dwell to
# 984, -> +120 across 984..1080 (accel out).
EXPRESS_PATH = ((336, -200.0), (528, 40.0))
LOCAL_PATH = ((672, -120.0), (792, -24.0), (984, -24.0), (1080, 120.0))

# the board program (frame, text row content ids light up)
BOARD_PROGRAM = (
    (0,    "quiet: SERVICE SUSPENDED rows dim"),
    (192,  "EXPRESS APPROACHING"),
    (528,  "LOCAL ARRIVING"),
    (792,  "LOCAL  BOARDING"),
    (1009, "EXPRESS - PASSING WITHOUT STOP (title)"),
)

# --- the film spine (FRAMES) -------------------------------------------
BEATS = (
    (1,   "blue-hour platform; the fog pools; waiters drift W"),
    (192, "the board flips EXPRESS APPROACHING"),
    (336, "THE BLAST: headlight flares, the express passes, the crowd "
          "presses back (the DANGER window), the queue walk-in recoils"),
    (528, "exhale: fog closes, the board flips LOCAL ARRIVING"),
    (672, "the local glides in and stops"),
    (792, "boarding: the queue admits, cohorts rise"),
    (984, "the local pulls out"),
    (1009, "title: EXPRESS - PASSING WITHOUT STOP"),
)
SFX_EVENTS = (
    {"name": "station_bed_start", "frame": 1},
    {"name": "board_flip", "frame": 192},
    {"name": "express_approach", "frame": 300},
    {"name": "express_roar", "frame": 340},
    {"name": "express_pass_wind", "frame": 420},
    {"name": "board_flip", "frame": 528},
    {"name": "local_brake", "frame": 744},
    {"name": "door_bell", "frame": 792},
    {"name": "boarding_murmur", "frame": 820},
    {"name": "local_depart", "frame": 984},
    {"name": "title_sting", "frame": 1009},
)
