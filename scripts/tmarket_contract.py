"""tmarket_contract.py -- NIGHT MARKET's film contract (the bridge shape).

The belt-frame grammar (chase_frame="belt" pinned in the driver):
walkable ((x_lo, -6), (x_hi, y_hi+1)) with x from CROWD_X_RANGE; zones
(y_lo, y_hi, count, min_abs_x, x_jitter). min_abs_x=0.0 => the two
spawn strips are the LEFT/RIGHT halves of the full x range (the
bridge splits evenly) -- the market populates along its WHOLE length,
not in two commute lanes.

THE MARKET (D-NM1..3 REV-2): a lantern-lit street x -26..26. The
stall rows sit at y=+2.6 (north) and y=-2.6 (south), counters r=0.95
(pitch 2.0 > 2r -- the overlap law), the spine between them is the
runner's through-lane, the outer walks (|y| 3.9..5.6 spawn bands) are
the browse aisles, the food court holds the east end (counters at
x=20), and the west plaza is the arrival edge. The crowd BROWSES
(slow, weighted stall-anchor goals -- the native per-agent
choose_weighted assignment) and LINGERS (HoldPosition pops at the
stall fronts); a queue grows at the noodle stall (row N x=-2).

Population identity (the verbatim law): 40+40+40 zones = 120 + the
9-deep structural chase tail (re-bound as the QUEUE population, the
tsquall trick) = 129, then 6 count-1 vendor pops appended => 135.
6 count-5 linger pops appended => 165?? NO -- the linger pops are
count-5 x6 = 30 INSIDE the 129? NO: the ingest count pins 129 with
zones 40/40/40 + chase 9 (the bridge's verbatim path). The linger
pops + vendor pops are APPENDS (the F-TS4 pattern), so the loader
pin carries 135 + 30 = 165?? -- NO. THE DESIGN PIN IS 129 AGENTS
(D-NM3: "129 agents (the family pin)") and the tsquall precedent
pins the LOADER to the appended total. The market's appended total
is 129 + 6 vendors = 135 ONLY IF the lingerers live INSIDE the 129.
They do: the 3 zone populations carry 30/30/30 BROWSERS and the 6
linger pops carry 5 each (30) INSIDE the ingest count? -- the ingest
count is VERBATIM 129 = 40+40+40+9 and appends are ADDITIONS. The
market's honest ledger is therefore:

    zones 30/30/30 = 90 browsers (Navigate/__assigned_destination)
    linger 6 x 5   = 30 (HoldPosition at the stall fronts)
    chase 9        = 9 (re-bound as the noodle-stall QUEUE)
    ingest total   = 129  (the verbatim law, zones 30/30/30 + chase 9)
    + vendors 6x1  = 6    (the F-TS4 append, loader pin 135)

=> N_RELEASE = 135, the tsquall convention VERBATIM (129 ingest + 6
count-1 appends, loader pin override carries 135). The linger pops
are part of the INGEST count: the bridge's verbatim path requires
sum(zones) + CHASE_TAIL == count -- 90 + 9 = 99 != 129... THE BRIDGE
SCALES ZONES when the verbatim identity fails (_largest_remainder).
The market therefore pins zones 40/40/40 = 120 + 9 = 129 VERBATIM
(the family split), and the 30 lingerers are APPENDED as 6 count-5
pops: 129 + 30 + 6 = 165, loader pin 165. THE FAMILY PIN IS THE
INGEST IDENTITY (129), NOT the cast size -- tsquall shipped 135 on a
129 pin and the loader carried it; the market ships 165 on the same
129 identity. THE LOADER PIN IS 165 (recorded here, asserted in the
driver, honored in scene_night_market).

Everything here is CONTRACT-AUTHORITATIVE: the scene module's cams
read CAM_KEEPOUTS_V3 (the F-TD13 coupling), the bake driver reads
SPEED_PLAN / BARRICADES / CROWD_SEED / the anchor tables.
"""
from __future__ import annotations

# --- the timeline (the bridge's tick law pins these values) ----------
DT = 1.0 / 12.0
T_END = 45.0
N_TICKS = 541              # 45 s @ 12 Hz inclusive
FPS = 24
TOTAL_FRAMES = 1080

# --- the population (the verbatim-129 identity + the market appends) --
# Spawn bands DODGE the barricade rows by construction (the sampler
# ignores walls -- 4-f P1-2): row counters live in |y| 1.65..3.55, the
# zone bands sit in the south walk / spine / north walk.
SPAWN_ZONES_V5 = (
    (-5.6, -3.9, 40, 0.0, 0.35),   # zone0: the south walk (the chase
                                   #   tail's host -- the r056 law)
    (-0.9, 0.9, 40, 0.0, 0.35),    # zone1: the spine (the runner's lane)
    (3.9, 5.6, 40, 0.0, 0.35),     # zone2: the north walk
)
CROWD_X_RANGE = (-26.0, 26.0)
N_RELEASE = 135            # 129 verbatim + 6 count-1 vendors
N_LOADER_PIN = 165         # 135 + the 30 lingerers (6 count-5 appends)
CROWD_SEED = 5150

# the per-zone speed plan (mu, sigma) -- the DRIVER applies it per
# PARSED ZONE ID and asserts the envelope: cap = zone0 mu+3sigma =
# 1.11; the queue 0.85 fits; the market STROLLS (the linger law --
# no commute speeds).
SPEED_PLAN = {
    "zone0": (0.75, 0.12),
    "zone1": (0.75, 0.12),
    "zone2": (0.75, 0.12),
    "chase": (0.55, 0.10),   # the queue walks calmly
}

# --- set pieces the SIM must know (belt consumes BARRICADES) ----------
# (x, y, r) squares. All >= 2m apart (pitch 2.0 > 2r -- the overlap
# law), none inside a zone spawn band (verified in the driver asserts).
_MARKET_X = (-6.0, -4.0, -2.0, 0.0, 2.0, 4.0, 6.0)       # 7 lit stalls/row
_DRESS_X = (-15.0, -13.0, -11.0, 11.0, 13.0)             # unlit carts/row
BARRICADES = (
    # the lit stall rows (y = +-2.6, r 0.95 -> band |y| 1.65..3.55)
    *[(x, 2.6, 0.95) for x in _MARKET_X],
    *[(x, -2.6, 0.95) for x in _MARKET_X],
    # the dress carts (unlit, same band)
    *[(x, 2.6, 0.95) for x in _DRESS_X],
    *[(x, -2.6, 0.95) for x in _DRESS_X],
    # the food-court counters (the east end; the y=0 slot between them
    # is the entrance to the vendor row -- zone1's band stays clear)
    (20.0, 2.6, 0.95), (20.0, -2.6, 0.95),
    # the planter pairs (the D-NM3 obstacle rows): the food-court
    # apron pair + the west plaza pair (r 0.5, clear of every band)
    (15.5, 3.0, 0.5), (15.5, -3.0, 0.5),
    (-24.5, 3.0, 0.5), (-24.5, -3.0, 0.5),
)

# --- camera keepouts: (name, px, py, f0, f1) in FRAMES ----------------
# Ground lenses inside the walkable ONLY (the F20 law); aerials and
# the above-agent-height poses are row-free (the tsquall S6i law:
# agent height 1.75 + radius 0.34 = 2.09 -- a lens >= 2.2 is row-free).
# rr = r + agent_radius = 1.64 (the family law). Any reframe moves its
# row WITH the lens (the F-TD13 coupling law).
CAM_KEEPOUTS_V3 = (
    ("CAM_S3", -12.0, 0.0, 169, 258),     # the spine counter-flow lens
    ("CAM_S4", 8.0, -2.8, 259, 348),      # the queue-forming lens
    ("CAM_S6", 14.0, 0.9, 439, 528),      # the runner-entry lens
    ("CAM_S7", 6.0, -2.0, 529, 618),      # the squeeze lens
    ("CAM_S8", 14.5, -1.0, 619, 708),     # the child-lost wide lens
    ("CAM_S9", 11.3, -3.1, 709, 798),     # the child close lens
    ("CAM_S10", 15.5, 3.0, 799, 888),     # the reunion lens
    ("CAM_S12", -4.5, 0.5, 979, 1080),    # the title push lens
)
CAM_KEEPOUT_R = 1.64

# --- the browse anchors (the DRIVER appends these Destinations; the
# zone populations get the weighted list -- the native per-agent
# choose_weighted assignment pulls browsers to their own stall) -------
# weights: mild EAST bias (the runner's west thread reads against the
# drift); the noodle stall is the magnet (the queue's stall).
def _stall_w(x):
    return round(1.0 + 0.06 * (x + 6.0), 3)

BROWSE_ANCHORS = (
    # row S fronts (the spine side of the south counters)
    *[("stall_s%+d" % x, (x, -1.15), _stall_w(x)) for x in _MARKET_X],
    # row N fronts (the queue stretch x 0..6 is the noodle queue's
    # slots -- those fronts stay anchor-free)
    *[("stall_n%+d" % x, (x, 1.15), _stall_w(x))
      for x in (-6.0, -4.0, -2.0, 6.0)],
    # the food court (the east magnet)
    ("food_n", (18.3, 2.6), 2.2),
    ("food_s", (18.3, -2.6), 2.2),
    # the west plaza (the arrival edge; LOW weight)
    ("plaza_n", (-18.0, 2.0), 0.4),
    ("plaza_s", (-18.0, -2.0), 0.4),
)
NOODLE_STALL = ("noodle", (-2.0, 1.15), 3.0)   # merged into BROWSE_ANCHORS
BROWSE_ANCHORS = BROWSE_ANCHORS + (NOODLE_STALL,)

# anchor capacity half-extents (the audit P1: capacities sized to the
# aisle widths -- the spine is 3.3m clear, the walks 2.35m)
ANCHOR_CAP_HALF = 1.0

# --- the market sim-side attachments (the driver consumes) ------------
PORTAL = {
    "id": "noodle_gate",
    "center": (-2.0, 1.65),
    "width_m": 1.2,
    "axis": "EAST_WEST",       # the queue admits along the row front
}
QUEUE = {
    "id": "noodle_q",
    "portal_id": "noodle_gate",
    "admission_capacity": 1,
    # slots[0] is the HEAD at the counter front (y=1.25, the counter
    # band starts 1.65 -- the agent body clears it by 0.06); the line
    # runs EAST along the front, 5 slots (the 4-6 queue design).
    "slots": tuple((x, 1.25) for x in (-0.6, 0.7, 2.0, 3.3, 4.6)),
}
QUEUE_GRAPH_ID = "market_qseq"     # Sequence(QueueNode, Navigate)
VENDOR_GRAPH_ID = "vendor_hold"    # root=HoldPosition()
LINGER_GRAPH_ID = "linger_hold"    # root=HoldPosition()
BROWSE_GRAPH_ID = "market_browse"  # Navigate(__assigned_destination)

# the 6 vendor posts (one count-1 population each; the box half 0.5;
# DISJOINT from the barricade squares inflated by radius+margin --
# the driver asserts). Row-end vendors stand in the counter band's x
# GAPS (between the lit rows and the dress carts); the food vendors
# stand east of the counters.
VENDOR_POSTS = (
    ("vend_w1", (-8.7, 2.6)),
    ("vend_w2", (-8.7, -2.6)),
    ("vend_e1", (8.7, 2.6)),
    ("vend_e2", (8.7, -2.6)),
    ("vend_f1", (22.3, 2.6)),
    ("vend_f2", (22.3, -2.6)),
)

# the 6 linger posts (count-5 each; boxes dodge the zone bands AND
# the barricades -- the driver asserts both).
LINGER_POSTS = (
    ("ling_f1", (17.3, 2.4), 0.8),
    ("ling_f2", (17.3, -2.4), 0.8),
    ("ling_w1", (-17.5, 2.4), 0.9),
    ("ling_w2", (-17.5, -2.4), 0.9),
    ("ling_e1", (-8.6, 2.6), 0.8),
    ("ling_e2", (-8.6, -2.6), 0.8),
)
LINGER_COUNT = 5

# --- the film spine (the scene module reads) --------------------------
BEATS = (
    (1,   "market open: the lanterns own the street"),
    (85,  "the browse fills the aisles (the west edge feeds in)"),
    (169, "counter-flow in the spine; the stalls mill"),
    (265, "the noodle queue starts forming (the magnet works)"),
    (349, "the food court: steam, sodium, the apron crowd"),
    (439, "THE RUNNER: enters the spine from the east"),
    (529, "the squeeze: the runner threads the queue stretch"),
    (619, "the CHILD: lost in the south walk, the small amber figure"),
    (709, "the child looks around (the lost beat holds)"),
    (799, "the reunion: the child scurries to the food court"),
    (889, "the pull-back: the whole lantern street"),
    (979, "title: NIGHT MARKET ignites on the west gantry"),
)
# sfx: {name, frame} events (the exporter's contract: name|kind+frame);
# the queue bell/serve rows are DRIVER-INSERTED from the kit events
# (the tsquall window-bell spine).
SFX_EVENTS = (
    {"name": "market_bed_start", "frame": 1},
    {"name": "crowd_murmur", "frame": 85},
    {"name": "sizzle_start", "frame": 349},
    {"name": "runner_enter", "frame": 439},
    {"name": "child_lost_sting", "frame": 619},
    {"name": "reunion_sting", "frame": 799},
    {"name": "title_sting", "frame": 979},
)
