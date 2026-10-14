"""tsquall_contract.py -- SQUALL's film contract (the bridge's shape).

The belt-frame grammar (chase_frame="belt" pinned in the driver):
walkable ((x_lo, -6), (x_hi, y_hi+1)) with x from CROWD_X_RANGE;
zones (y_lo, y_hi, count, min_abs_x, x_jitter); the arrival box is the
belt default hero_pos (0,0) cap (+/-5) -- THE ARCADE FLOOR (the set
roof covers it); the portal divider (scene-side, driver-attached) is
the facade line y=6 with the 10m doorway.

REV-3 design: docs/DESIGN_squall.md. N_RELEASE=135 = (44+40+36+9
verbatim 129) + 6 vendors appended by the driver (the ingest call is
count=129; the loader pin override carries 135 -- F-TS5).

Everything here is CONTRACT-AUTHORITATIVE: the scene module's cams
read CAM_KEEPOUTS_V3 (the F-TD13 coupling), the bake driver reads
SPEED_PLAN / BARRICADES / CROWD_SEED.
"""
from __future__ import annotations

# --- the timeline (the bridge's tick law pins these values) ----------
DT = 1.0 / 12.0
T_END = 45.0
N_TICKS = 541              # 45 s @ 12 Hz inclusive
FPS = 24
TOTAL_FRAMES = 1080

# --- the population (REV-3 section 4) ---------------------------------
# zone0 = the NEAREST band = the FAST population (the cap owner).
# y_lo 10.3 (the fountain wall tops at y 9.9 -- the spawn-seam law).
SPAWN_ZONES_V5 = (
    (10.3, 11.5, 44, 2.5, 0.35),   # zone0: fast band (mu 2.0)
    (11.5, 13.0, 40, 2.5, 0.35),   # zone1: middle strollers (mu 1.2)
    (13.0, 14.0, 36, 2.5, 0.35),   # zone2: far band (mu 1.35)
)
CROWD_X_RANGE = (-30.0, 30.0)
N_RELEASE = 135            # (44+40+36+9 verbatim 129) + 6 vendors
CROWD_SEED = 4242

# the per-zone speed plan (mu, sigma) -- the DRIVER applies it per
# PARSED ZONE ID and asserts the envelope: cap = zone0 mu+3sigma =
# 2.75; zone2 max 1.95; chase 0.9+0.45=1.35 (all fit, F2 law).
SPEED_PLAN = {
    "zone0": (2.0, 0.25),
    "zone1": (1.2, 0.2),
    "zone2": (1.35, 0.2),
    "chase": (0.9, 0.15),   # the queue walks calmly (the drain knob)
}

# --- set pieces the SIM must know (belt consumes BARRICADES) ----------
# (x, y, r) squares: stall counters r=0.95 (pitch 2.0 > 2r -- the
# overlap fix); the fountain basin r=2.3 (REV-3: the rim band
# 2.6-3.4m stays reachable for the slip). All >= 2m apart, >= 2.9m
# from the walkable edge (the sealed-pocket law).
BARRICADES = (
    (-26.0, 1.5, 0.95), (-26.0, 3.5, 0.95),
    (-26.0, 5.5, 0.95), (-26.0, 7.5, 0.95),
    (26.0, 1.5, 0.95), (26.0, 3.5, 0.95),
    (26.0, 5.5, 0.95), (26.0, 7.5, 0.95),
    (14.0, 7.5, 2.3),          # the fountain
)

# --- camera keepouts: (name, px, py, f0, f1) in FRAMES ----------------
# Ground lenses inside the walkable ONLY (the F20 law); aerials and
# the interior cams above agent height are row-free EXCEPT where a
# ground-level pose exists. rr = r + agent_radius = 1.64. The REV-3
# vantage table (section 6) drives these rows; any reframe moves its
# row WITH the lens (the F-TD13 coupling law).
CAM_KEEPOUTS_V3 = (
    # ground-level lenses inside the walkable ONLY (the F20 law; the
    # aerials and the above-agent-height poses are row-free -- a
    # keepout under an aerial punches a hole exactly where it looks).
    # rr = r + agent_radius = 1.98. The S6i lens (2,4,3.5) is ABOVE
    # agent height -- row-free (the stale S6 row clamped a hole
    # mid-arcade for a camera that moved: the 4-i review's P1-3).
    ("CAM_S2", -18.0, 2.0, 85, 168),      # the low W oblique
    ("CAM_S4", 5.0, -3.5, 265, 348),      # the interior press lens
    ("CAM_S7", 12.0, -1.0, 529, 624),     # the through-colonnade lens
    ("CAM_S10", -3.0, 2.5, 817, 912),     # the interior ease lens
    ("CAM_S11", 17.0, 0.5, 913, 1008),    # the axial crane loc0
)
CAM_KEEPOUT_R = 1.64

# --- the SQUALL sim-side attachments (the driver consumes) ------------
# The M6 queue + portal (REV-3 section 3): the divider wall IS the
# arcade facade line; the queue slots run along the food window.
PORTAL = {
    "id": "arcade_gate",
    "center": (0.0, 6.0),
    "width_m": 10.0,
    "axis": "NORTH_SOUTH",     # the CROSSING-direction law (4-d P0)
}
QUEUE = {
    "id": "window_q",
    "portal_id": "arcade_gate",
    "admission_capacity": 1,
    # slots[0] is the HEAD at the counter (y=-4.6), the tail 0.4m off
    # the y=6 wall; 9 slots so all 9 chase agents admit (no strays).
    "slots": tuple((6.5, y) for y in
                   (-4.6, -3.3, -2.0, -0.7, 0.6, 1.9, 3.2, 4.5, 5.6)),
}
QUEUE_GRAPH_ID = "queue_window"     # Sequence(QueueNode, Navigate)
VENDOR_GRAPH_ID = "vendor_hold"     # root=HoldPosition()
# the 6 vendor posts (one count-1 population each; spawn boxes OFFSET
# plaza-facing from the stall centers -- the sampler ignores walls,
# so the box must be DISJOINT from the barricade squares, 4-f P1-2).
VENDOR_POSTS = (
    ("stall1", (-24.0, 1.5)),
    ("stall2", (-24.0, 3.5)),
    ("stall3", (-24.0, 5.5)),
    ("stall4", (24.0, 1.5)),
    ("stall5", (24.0, 3.5)),
    ("stall6", (24.0, 5.5)),
)

# --- the film spine (the scene module reads) --------------------------
BEATS = (
    (1,   "first heavy drops; the slow bands drift"),
    (85,  "thunder hit: the stall strings flicker; the fast band shows"),
    (169, "the streams merge toward the arcade mouth"),
    (265, "the doorway choke: the press at the entrance"),
    (349, "THE BEAT: the slip-and-fall beside the fountain (f380)"),
    (445, "the queue holds at the food window"),
    (529, "the fill: under the canopy, the sheeting edge"),
    (625, "the plaza empties (the last stragglers cross north)"),
    (721, "the peak-as-equilibrium: the packed box, the fountain pair"),
    (817, "the storm eases: light warms; the last queue releases"),
    (913, "the crane rises on the east flank"),
    (1009, "title: the lightning flash ignites the neon SQUALL"),
)
# the rain-intensity arc (both sound and scene layers key on this)
RAIN_ARC = (
    (1, 0.5), (85, 1.0), (529, 1.15), (817, 0.6), (1009, 0.25),
)
# sfx: {name, frame} events (the exporter's contract: name|kind+frame)
SFX_EVENTS = (
    {"name": "rain_bed_start", "frame": 1},
    {"name": "thunder_crack_1", "frame": 85},
    {"name": "crowd_swell", "frame": 200},
    {"name": "fall_thud", "frame": 385},
    {"name": "thunder_rumble", "frame": 529},
    {"name": "thunder_crack_2", "frame": 625},
    {"name": "canopy_murmur", "frame": 640},
    {"name": "storm_ease", "frame": 817},
    {"name": "title_sting", "frame": 1009},
)
