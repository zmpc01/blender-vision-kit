"""tform_contract.py -- THE DRILL's film contract (the custom-scene fork).

Film 6: golden-hour citadel parade yard. A 24-agent drill column assembles,
wheels across the yard in formation (per-agent TRANSFORM layers), halts,
forms the circle, the officers' beat (bake_interaction), breaks off and
marches out -- the layers NEVER end mid-film (dispersal runs to tick 539;
the film ends before any layer-end exists).

This film does NOT use bridge.ingest_contract: a walled citadel yard with
an out-the-gap dispersal fits no hard-coded ingest band (the same audit
round-1 P0-b class tfog folded). The driver authors the CrowdScene
field-by-field and re-asserts the ingest-contract laws manually: project
pin, tick_hz=12, interval=1 per population, 12 Hz / 541 ticks / 24 fps /
1080 frames / seed 6150.

REV-3 design: docs/DESIGN_drill.md. Cache N = 102 (24+72+4+1+1); the
loader pin override carries 102 (F-TS5). The STANDARD-BEARER + CAPTAIN
are Blender-side keyed actors OUTSIDE the cache (branch (a)); the two
OFFICERS are cache agents (the bake_interaction pair).

DESIGN ERRATUM FOLDED (this contract is authoritative): DESIGN_drill
section 4 says "144 drill layers (6 windows x 24)" but section 3's own
phase table has SEVEN layer windows -- the halt-in-place PIN [120,131]
precedes the dress TRANSFORM [132,168]. Layers cannot span gaps (ranges
ABUT exactly), so the honest stack is 7 windows x 24 agents = 168 layers.
Filed as the 144->168 erratum; the driver asserts the abutment.

1 tick = 2 frames (the x2 law): all tick windows x2 = frames.
"""
from __future__ import annotations

import math

# --- the timeline (the x2 law: 1 tick = 2 frames) ----------------------
DT = 1.0 / 12.0
T_END = 45.0
N_TICKS = 541              # 45 s @ 12 Hz inclusive
FPS = 24
TOTAL_FRAMES = 1080

# --- the world (from tform_world.py's ACTUAL constants) ----------------
# yard plane x -28..28, y -20..20; walls N/E/W t=2.0 (N wall y 20..22
# with the 6 m gap x -3..3); colonnade 10 columns 0.8 m sq at
# COLONNADE_Y=-20 (y -20.4..-19.6, x -25..25); circle-mark ring inlay
# r=4.0 centerline (band 3.85..4.15) at the origin; dais inlay ~x 10.8
# y -0.8..0.8; 4 banner poles at (+-14, +-12); backdrop plane y 30..32.
YARD = ((-28.0, -20.0), (28.0, 20.0))
GAP_X0, GAP_X1 = -3.0, 3.0
CIRCLE_C = (0.0, 0.0)
CIRCLE_R = 4.0             # the ring band CENTERLINE (the world's inlay)
RING_BAND = 0.15
COLUMN_Y0, COLUMN_Y1 = -20.4, -19.6
COLUMN_XS = (-25.0, -19.4444, -13.8889, -8.3333, -2.7778,
             2.7778, 8.3333, 13.8889, 19.4444, 25.0)
COLUMN_HALF = 0.4
POLE_XYS = ((-14.0, -12.0), (-14.0, 12.0), (14.0, -12.0), (14.0, 12.0))
POLE_HALF = 0.3
DAIS_XY = (10.8, 0.0)      # inlay, VISUAL-ONLY (no blocked square)

# the walkable: the yard pulled short of the E/W wall inner faces (2 m
# margin), S of the colonnade faces (+0.1 inflation past the column
# squares so they sit FULLY inside -- the E_InvalidRange law), and N
# through the gap into the barracks strip (y<=29 keeps 1 m clear of the
# backdrop at y 30). The N wall segments flank the gap as Blocked.
WALKABLE = ((-26.0, -20.5), (26.0, 29.0))
WALKABLE_ID = "citadel_yard"

# blocked squares (x_lo, y_lo, x_hi, y_hi) -- fully inside the walkable
BLOCKED = (
    ("wall_n_w", (-26.0, 20.0, -3.0, 22.0)),
    ("wall_n_e", (3.0, 20.0, 26.0, 22.0)),
) + tuple(
    (f"col{i+1}", (x - COLUMN_HALF, COLUMN_Y0, x + COLUMN_HALF, COLUMN_Y1))
    for i, x in enumerate(COLUMN_XS)
) + tuple(
    (f"pole{i+1}", (x - POLE_HALF, y - POLE_HALF, x + POLE_HALF,
                    y + POLE_HALF))
    for i, (x, y) in enumerate(POLE_XYS)
)

# --- destinations -------------------------------------------------------
# drill: the assembly area S-center-N (the base march carries them here
# during 0..119; arrival = ghost = standing = the halt read; the tick-120
# PIN payload is their MEASURED positions -- continuity law).
DEST_DRILL = {
    "id": "assembly_area",
    "point": (0.0, 6.0),
    "capacity": ((-5.5, 4.5), (5.5, 7.5)),
}
# watchers: the colonnade shade line (ONE dest, the capacity band does
# the spread; slow-mu Navigate fills the shade).
DEST_WATCHERS = {
    "id": "shade_line",
    "point": (0.0, -17.6),
    "capacity": ((-24.0, -18.6), (24.0, -16.8)),
}
# drummers: on the ground beside the dais inlay (E side), then HOLD.
DEST_DRUMMERS = {
    "id": "drum_line",
    "point": (12.6, 0.0),
    "capacity": ((12.0, -1.5), (13.5, 1.5)),
}
# officers: TWO 1-agent pops, adjacent destination boxes INSIDE the
# ring (round-5 camprobe: from every outside angle the r=4 ring slots
# screen the pair; INSIDE the circle the ring forms AROUND the
# principals -- ceremony-correct and camera-clean). 0.5 m apart (y);
# the bake_interaction clasp lives at their measured arrival.
DEST_OFFICER_A = {
    "id": "officer_w",
    "point": (1.6, 0.25),
    "capacity": ((1.3, 0.05), (1.9, 0.45)),
}
DEST_OFFICER_B = {
    "id": "officer_e",
    "point": (1.6, -0.25),
    "capacity": ((1.3, -0.45), (1.9, -0.05)),
}

# --- the population plan (cache N = 102; ingest order = the cap law) ---
# (id, count, spawn rect, speed (mu, sig), dest, graph)
# populations[0] owns the envelope cap (the F-TS4 law) -> the FASTEST
# pop leads: the drill (mu 1.3 = the walk-speed law the wheel is timed
# to).
SPAWN_GAP = (-2.0, 15.0, 2.0, 17.0)   # issuing FROM the gap (the yard
    # N band): the probe measured 8/24 within dress reach from the gap
    # MOUTH (y 18-19.5) -- the march genuinely cannot cover 12-15 m in
    # 119 ticks for the whole squad. y 15-17 keeps the gap-direction
    # read (they enter the frame from the gap side) while the worst
    # path drops to ~14.6 m and the mean ~10.6 (mean coverage 12.9:
    # the squad ARRIVES at t120, stragglers pinned mid-approach +
    # dressed -- the honest halt-trickle).
SPAWN_WATCH = (-24.0, -19.0, 24.0, -17.2)  # along the colonnade shade
SPAWN_DRUM = (12.0, -1.5, 13.5, 1.5)       # beside the dais (E)
SPAWN_OFFICERS = (-24.0, -18.8, -20.0, -17.4)  # Emerge from the W shade
POP_PLAN = (
    ("drill", 24, SPAWN_GAP, (1.30, 0.05), DEST_DRILL["id"],
     "march_in"),
    ("watchers", 72, SPAWN_WATCH, (0.75, 0.10), DEST_WATCHERS["id"],
     "shade_wander"),
    ("drummers", 4, SPAWN_DRUM, (1.00, 0.08), DEST_DRUMMERS["id"],
     "drum_hold"),
    # officers: mu 1.10 times ~34.4 m path = arrival ~tick 375 -- INSIDE
    # the hold window (361..420); the driver MEASURES and asserts it.
    ("officer_a", 1, SPAWN_OFFICERS, (1.10, 0.05),
     DEST_OFFICER_A["id"], "officer_approach"),
    ("officer_b", 1, SPAWN_OFFICERS, (1.10, 0.05),
     DEST_OFFICER_B["id"], "officer_approach"),
)
N_CACHE = 102
CROWD_SEED = 6150

# --- the layer phase table (ticks; x2 = frames) -------------------------
# (name, t0, t1, op) -- ranges ABUT exactly (the layer-abutment law);
# op: "base" (no layer), "pin" (measured/formation hold), "transform"
# (authored per-tick absolute samples).
DR_PHASES = (
    ("march_in",  0, 119, "base"),
    ("dress_pin", 120, 131, "pin"),       # halt-in-place at MEASURED
    ("dress",     132, 168, "transform"),  # measured -> the 2x12 line
    ("wheel",     169, 251, "transform"),  # 90 deg, centroid pivot
    ("halt",      252, 299, "pin"),        # PIN at the halt slots
    ("circle",    300, 360, "transform"),  # to the ring, monotone-angle
    ("hold",      361, 420, "pin"),        # ring hold (the officers' beat)
    ("dispersal", 421, 539, "transform"),  # out the gap, NO layer-end
)
N_LAYERS = 24 * 7          # 168 (the 144 erratum: section 4's arithmetic)

# --- the wheel spec (DESIGN_drill section 1, exact numbers) -------------
WHEEL = {
    "files": 12,             # slots along the line (spacing 1.0)
    "ranks": 2,              # deep (half 0.5)
    "half_span": 5.5,        # m (11 intervals x 1.0)
    "rank_half": 0.5,
    "spacing": 1.0,
    "window": (169, 251),    # ticks; 83 samples = 82 intervals
    "omega": (math.pi / 2) / 82.0,   # 0.019157 rad/tick (90 deg total)
    "r_max": math.hypot(5.5, 0.5),   # 5.523 m
    # per-tick displacement of the outermost slot (m/tick; 0.1058)
    "step_max": ((math.pi / 2) / 82.0) * math.hypot(5.5, 0.5),
    # seconds-converted (m/s; 1.270) -- the walk-law comparison
    "v_max_mps": ((math.pi / 2) / 82.0) * math.hypot(5.5, 0.5) * 12.0,
    "dir": +1,               # CCW seen from +z (the S6/S5 sweep reads E)
}
WALK_MU = 1.30              # the base walk law the wheel is timed to
assert WHEEL["v_max_mps"] <= WALK_MU, (
    f"wheel v_max {WHEEL['v_max_mps']:.3f} m/s violates the walk-speed "
    f"law ({WALK_MU}) -- the moonwalk fold R4")

# the assembly line (2x12) centroid: 14 m S of the gap spawn (the
# march-in covers it at walk mu inside the 119-tick window) and the
# swept wheel annulus stays clear of colonnade/dais/poles (asserted in
# the geometry gate below).
ASSEMBLY_C = (0.0, 6.0)
ASSEMBLY_LINE_HALF = WHEEL["half_span"]
ASSEMBLY_RANK_HALF = WHEEL["rank_half"]
DRESS_MAX_MOVE = 4.0   # the dress window (37 ticks) covers <= ~4 m of
                       # dressing at walk mu x 0.85 utilization

# the circle: 24 slots on the r=4 mark ring (chord 1.047 ~= the design's
# 1.05); monotone-by-angle assignment from the halt slots.
RING_SLOTS_N = 24
RING_CHORD = 2.0 * math.pi * CIRCLE_R / RING_SLOTS_N   # 1.0472

# the dispersal: the gap-column targets (4 abreast through the 6 m gap,
# 1.0 m spacing), nominal 1.55 m/s attention-march (R7); per-slot speed
# = max(nominal, path_len/118) capped 1.75 (the file's front rank only;
# the K1 recomposed phase stays in the walk band < 1.8 -- the honest
# stretch note). NOBODY reaches their target inside the window (min
# ring->target path 17.1 m > 1.75x9.83 = 17.2 -- re-asserted exactly in
# the geometry gate): the column is STILL MARCHING at the cut = no seam.
DISPERSAL_WINDOW = (421, 539)     # 119 samples = 118 intervals
DISPERSAL_NOMINAL = 1.55
DISPERSAL_CAP = 1.75
GAP_COLUMN_XS = (-1.5, -0.5, 0.5, 1.5)     # 4 abreast
GAP_COLUMN_Y0 = 21.0                        # head targets past the gap

# --- bake_interaction (the officers' beat; M5) ---------------------------
# The window is MEASURED (the probe resolves the arrival tick); these
# are the request/layer/motion LAWS the driver re-asserts.
INTERACTION = {
    "participants": ("officer_a", "officer_b"),   # pop ids -> ids@probe
    "protocol": "authored-paired-clip-v1",
    "root_constraints_cover_interval": True,
    "min_contacts": 1,
    "contact_label": "grip",     # the clasp IS a grip (the _LABELS law)
    "contact_distance_m": 0.15,
    "flow_then_pin": True,       # converge flows; clasp-hold pins phase
    "converge_clip": 1,          # kit walk (the clip-channel vocabulary)
    "clasp_clip": 0,             # kit idle = the held stance
    "clasp_phase": 0.35,
    "window_ticks": 23,          # [anchor, anchor+22], capped < 420
    "motion_keys": 7,
    "layer_sidecar": "2x window-ticks",
}

# --- clip law ------------------------------------------------------------
# clip_source="channel" -- the driver calls bridge.to_previz_cache(...,
# clip_source="channel") DIRECTLY (never the crowd_kit CLI -- it
# hard-codes speed_band); receipt assert digest["clip_source"]=="channel".
CLIP_SOURCE = "channel"

# --- camera keepouts: (name, px, py, f0, f1) FRAMES ---------------------
# EMPTY scaffold -- the camprobe wave adds rows with their lenses as ONE
# edit (the F-TD13 law). The count assert is contract-vs-cache agreement
# (never a literal).
CAM_KEEPOUT_R = 1.3
# fix-wave-2 audit round: the S10/S11 lenses moved onto the yard's
# south lane (the bearer's dais approach) -- ground lenses INSIDE the
# crowd's roam now carry rows (the F-TD13 law; the empty tuple predates
# lenses that all stood outside traffic). Frames, not seconds.
CAM_KEEPOUTS = (
    ("CAM_S10", 1.5, -7.5, 973, 1008),
    ("CAM_S11", 3.0, -7.0, 1009, 1044),
)

# --- the film spine (FRAMES) --------------------------------------------
BEATS = (
    (1,    "golden-hour yard; long shadows; the watchers file the "
           "shade line; banner INSPECTION DAY"),
    (192,  "the squad marches in through the north gap"),
    (264,  "the dress: halt-in-place, ranks dressed to the 2x12 line"),
    (336,  "THE WHEEL: the column wheels across the yard "
           "(drum cadence)"),
    (504,  "HALT snap at the new line"),
    (600,  "the ring re-forms around the circle mark"),
    (722,  "the officers' beat: converge, clasp hold (the ring holds)"),
    (842,  "break-off: the ring becomes the gap-column and marches OUT"),
    (1009, "title: THE DRILL (banner + drum platform, long shadows)"),
)
SFX_EVENTS = (
    {"name": "yard_drone_start", "frame": 1},
    {"name": "drum_roll", "frame": 264},
    {"name": "drum_cadence", "frame": 338},
    {"name": "halt_crack", "frame": 504},
    {"name": "drum_swell", "frame": 600},
    {"name": "clasp_beat", "frame": 780},
    {"name": "march_out_wash", "frame": 842},
    {"name": "title_sting", "frame": 1009},
)


# --- formation geometry helpers (pure math; the driver consumes) --------
def line_slots(centroid=ASSEMBLY_C, half_span=ASSEMBLY_LINE_HALF,
               rank_half=ASSEMBLY_RANK_HALF, files=WHEEL["files"],
               ranks=WHEEL["ranks"]):
    """The 2x12 assembly line: files along x (spacing 1.0), ranks along
    y (+-0.5). Returns 24 (x, y) slots, file-major (file 0 = -x end)."""
    out = []
    for f in range(files):
        x = centroid[0] - half_span + f * 1.0
        for r in range(ranks):
            y = centroid[1] + (rank_half if r == 0 else -rank_half)
            out.append((x, y))
    return out


def wheel_slot(slot_xy, tick, pivot=ASSEMBLY_C, omega=None):
    """Slot position at `tick` under the wheel (rigid rotation about the
    formation CENTROID -- the R4 fold; a slot pivot breaks the walk law).
    Absolute transform; angles monotone in the window."""
    om = WHEEL["omega"] if omega is None else omega
    t0, _t1 = WHEEL["window"]
    ang = WHEEL["dir"] * om * (tick - t0)
    ca, sa = math.cos(ang), math.sin(ang)
    dx, dy = slot_xy[0] - pivot[0], slot_xy[1] - pivot[1]
    return (pivot[0] + dx * ca - dy * sa,
            pivot[1] + dx * sa + dy * ca)


def ring_slots():
    """24 ring slots at r=4 on the mark centerline, angle 0 = +x, CCW."""
    return [(CIRCLE_C[0] + CIRCLE_R * math.cos(2 * math.pi * k / 24),
             CIRCLE_C[1] + CIRCLE_R * math.sin(2 * math.pi * k / 24))
            for k in range(24)]


def monotone_ring_assignment(from_slots):
    """Monotone-by-angle: sort both the from-slots and the ring slots by
    polar angle about the ring center and zip (order-preserving -> no
    path crossings; RQ7's 'ring faces center for free' via radial
    approach)."""
    cx, cy = CIRCLE_C
    def key(p):
        return math.atan2(p[1] - cy, p[0] - cx) % (2 * math.pi)
    src = sorted(from_slots, key=key)
    dst = sorted(ring_slots(), key=key)
    return list(zip(src, dst))


def gap_column_slots():
    """The dispersal gap-column targets: 4 abreast x 6 deep through the
    gap (24 slots), head row at GAP_COLUMN_Y0, file-major."""
    out = []
    for row in range(6):
        y = GAP_COLUMN_Y0 + row * 1.0
        for x in GAP_COLUMN_XS:
            out.append((x, y))
    return out


def dispersal_assignment():
    """Monotone funnel ring->gap-column: sort ring slots by the bearing
    toward the gap center (0, 24) and zip with the column slots sorted
    by approach bearing -- order-preserving (no crossings)."""
    gx, gy = 0.0, 24.0
    def bearing(p):
        return math.atan2(gy - p[1], gx - p[0])
    src = sorted(ring_slots(), key=bearing)
    dst = sorted(gap_column_slots(), key=bearing)
    return list(zip(src, dst))


def dispersal_sample(src, dst, k):
    """Position at interval k (0..118) marching src->dst at the per-slot
    speed law: max(nominal, path/118) capped 1.75 (the honest stretch;
    nobody arrives -- asserted in the geometry gate)."""
    t0, t1 = DISPERSAL_WINDOW
    n_int = t1 - t0                       # 118
    path = math.hypot(dst[0] - src[0], dst[1] - src[1])
    v = min(DISPERSAL_CAP, max(DISPERSAL_NOMINAL, path / n_int))
    step = min(v * k / 12.0, path)        # ticks -> s: /tick_hz
    f = step / path if path > 0 else 0.0
    return (src[0] + (dst[0] - src[0]) * f,
            src[1] + (dst[1] - src[1]) * f)


# --- the geometry gate (import-time; pure python, no bpy) ---------------
def _geometry_gate():
    wx0, wy0 = WALKABLE[0]
    wx1, wy1 = WALKABLE[1]

    def inside(rect):
        return (rect[0] >= wx0 and rect[1] >= wy0
                and rect[2] <= wx1 and rect[3] <= wy1)

    # blocked fully inside walkable (E_InvalidRange law)
    for name, r in BLOCKED:
        assert inside(r), f"blocked {name} escapes the walkable: {r}"
    # the colonnade squares really match the world's constants
    for i, x in enumerate(COLUMN_XS):
        assert BLOCKED[2 + i][1][1] == COLUMN_Y0
    # walkable short of the E/W wall inner faces (x=+-28) by the margin
    assert wx1 <= 26.0 and wx0 >= -26.0
    # 1 m clear of the backdrop plane (y 30..32)
    assert wy1 <= 29.0

    # the swept wheel annulus: >=1.5 m clear of the colonnade shade
    # line, the dais inlay, and the poles (design section 1)
    cx, cy = ASSEMBLY_C
    rmax = WHEEL["r_max"] + 0.35          # agent radius pad
    assert cy - rmax > (-19.6) + 1.5, "wheel annulus vs colonnade"
    dais_clear = math.hypot(DAIS_XY[0] - cx, DAIS_XY[1] - cy) - rmax
    assert dais_clear >= 1.5, f"wheel annulus vs dais: {dais_clear:.2f}"
    for px, py in POLE_XYS:
        d = math.hypot(px - cx, py - cy) - rmax
        assert d >= 0.35, f"wheel annulus vs pole: {d:.2f}"

    # the assembly line inside the walkable, clear of every blocked sq
    for x, y in line_slots():
        assert wx0 < x < wx1 and wy0 < y < wy1
        for _n, r in BLOCKED:
            if (r[0] - 0.35 < x < r[2] + 0.35 and r[1] - 0.35 < y
                    < r[3] + 0.35):
                raise AssertionError(f"assembly slot ({x},{y}) "
                                     f"collides with a blocked square")
    # the march-in: the WORST spawn->slot path must fit mean walk
    # coverage + the dress slack (the stragglers get pinned mid-approach
    # at t120 and dressed -- halt-in-place IS freezing the pose; the
    # 3-sigma agent trail reads as the file halting last).
    worst = 0.0
    for x, y in line_slots():
        for sx in (SPAWN_GAP[0], SPAWN_GAP[2]):
            for sy in (SPAWN_GAP[1], SPAWN_GAP[3]):
                worst = max(worst, math.hypot(x - sx, y - sy))
    assert worst <= WALK_MU * (119 / 12.0) + DRESS_MAX_MOVE, (
        f"march-in worst path {worst:.1f} m exceeds walk coverage "
        f"+ dress slack")

    # the ring: chord law + the hold ring clear of the officers' boxes
    assert abs(RING_CHORD - 1.05) < 0.01, "ring chord drifts from spec"
    # the officers' approach: the W-shade spawn to the beat boxes at
    # mu 1.10 must land them POSTED before the hold ENDS (the beat
    # anchor = max(arrival_a, arrival_b, 362); the driver MEASURES and
    # re-asserts on the cache truth).
    oa = DEST_OFFICER_A["point"]
    ob = DEST_OFFICER_B["point"]
    for p in (oa, ob):
        d_off = math.hypot(p[0] - SPAWN_OFFICERS[0],
                           p[1] - SPAWN_OFFICERS[3])
        t_off = d_off / 1.10 * 12.0
        assert t_off <= 420, (
            f"officer arrival ~tick {t_off:.0f} misses the hold window")

    # dispersal: NOBODY arrives inside the window (the no-seam law) and
    # per-slot speeds stay <= the cap
    for src, dst in dispersal_assignment():
        path = math.hypot(dst[0] - src[0], dst[1] - src[1])
        v = path / 118.0
        assert v <= DISPERSAL_CAP or DISPERSAL_NOMINAL * 118 / 12.0 * 1.0 \
            >= path, (
            f"slot reaches its target (v={v:.2f}); the column would "
            f"arrive+ghost mid-window")
        end = dispersal_sample(src, dst, 118)
        remain = math.hypot(dst[0] - end[0], dst[1] - end[1])
        assert remain > 0.05, "a slot lands ON its target at the cut"

    # the wheel-window per-tick outer-slot step stays sub-stride
    assert WHEEL["step_max"] < 0.12, "wheel step breaks the cadence"


_geometry_gate()
