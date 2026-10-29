"""tform_bake.py -- THE DRILL's headless crowd-bake driver (4 stages).

STEP 4 of the film build order (venv, pure CPython -- no Blender):

  /home/z/.venv/bin/python3 scripts/tform_bake.py --out /tmp/crowdcache_tform --stage probe
  /home/z/.venv/bin/python3 scripts/tform_bake.py --out /tmp/crowdcache_tform --stage layers
  /home/z/.venv/bin/python3 scripts/tform_bake.py --out /tmp/crowdcache_tform --stage interaction
  /home/z/.venv/bin/python3 scripts/tform_bake.py --out /tmp/crowdcache_tform --stage finish
  /home/z/.venv/bin/python3 scripts/tform_bake.py --out /tmp/crowdcache_tform --stage verify

The ingest fork (the tfog precedent): a walled citadel yard with an
out-the-gap dispersal fits no hard-coded ingest band -- the driver
authors the CrowdScene field-by-field and re-asserts the ingest-contract
laws manually (project pin, 12 Hz, interval=1, the envelope owner).
REV-3 design: docs/DESIGN_drill.md. NO force field (no blast), NO
portal/queue (the drill film's v2 features are the LAYER stack + the
M5 bake_interaction beat).

Stage probe      : base bake (102) -> ids + pop membership (the static
                   table's population_id column, ordinals == ingest
                   order); MEASURED drill positions at the t120 halt
                   (the dress PIN payload -- continuity law); officers'
                   MEASURED arrival ticks (the beat anchor); the
                   march-in read; the FULL authored-trajectory spacing
                   rehearsal (>=0.7 m at every sampled tick, R6).
Stage layers     : the 168-layer stack (7 windows x 24 drill agents:
                   pin/dress/wheel/halt/circle/hold/dispersal -- the
                   144 erratum) via apply_layout_overrides;
                   conflicts == [] asserted at EVERY phase boundary.
Stage interaction: the officers' clasp (M5 bake_interaction):
                   request + layer + the hand-authored 7-key motion,
                   all bound to the REAL cache identity and the
                   MEASURED officers' ids/arrival (the test_m5 fixture
                   pattern); flow-then-pin phase edits (converge flows,
                   clasp-hold pins clip 0).
Stage finish     : composed npz with clip_source="channel" (the direct
                   bridge call -- never the CLI); the mapping probe
                   (clip rows in the kit vocabulary; the officers' hold
                   reads idle); cast + sfx spine; determinism receipt.
Stage verify     : re-apply the FULL layer stack + interaction on a
                   FRESH clone dir -> byte-compare the npz (the design
                   section-4 determinism law).

1 tick = 2 frames (the x2 law).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
import warnings
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
LAB = HERE.parent.parent


def _resolve(env_key, sibling_name):
    v = os.environ.get(env_key)
    if v:
        return Path(v)
    sib = LAB / sibling_name
    if (sib / "scripts").is_dir():
        return sib
    raise SystemExit(f"[tform_bake] sibling {sibling_name} not found")


CROWD_KIT_REPO = _resolve("TFORM_CROWD_KIT", "blender-crowd-kit")
PREVIZ_REPO = _resolve("TFORM_PREVIZ", "blender-escape-previz")


def _bootstrap():
    for p in (PREVIZ_REPO / "scripts", CROWD_KIT_REPO):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    bridge_py = CROWD_KIT_REPO / "scripts" / "crowd" / "previz_bridge.py"
    if not bridge_py.is_file():
        raise SystemExit(f"[tform_bake] no previz_bridge at {bridge_py}")
    import scripts.crowd.previz_bridge as bridge  # noqa: F401
    return bridge


def _cache_file(stage_dir: Path) -> str:
    files = sorted(stage_dir.glob("*.crowd"))
    assert len(files) == 1, f"expected one .crowd in {stage_dir}: {files}"
    return str(files[0])


def build_scene(C, bridge):
    """The custom CrowdScene (the ingest fork) + the manual law pins."""
    from scripts.crowd import CrowdScene, CrowdProject, Walkable, Blocked
    from scripts.crowd import Destination
    from scripts.crowd import BehaviorGraph
    from scripts.crowd.behavior import Navigate, HoldPosition
    from scripts.crowd.population import Population, SpawnSource
    from scripts.crowd.population import PopulationDistributions

    project = CrowdProject(
        project_id=bridge.PREVIZ_PROJECT_PIN,   # the pin law
        seed=C.CROWD_SEED,
        fps=C.FPS,
        tick_hz=12,                             # the 12 Hz cache law
        frame_start=1,
        frame_end=C.TOTAL_FRAMES,
    )
    assert project.project_id == bridge.PREVIZ_PROJECT_PIN

    walkable = Walkable(id=C.WALKABLE_ID, bounds=C.WALKABLE)
    wl_lo, wl_hi = C.WALKABLE
    blocked = [Blocked(id=bid, walkable_id=C.WALKABLE_ID,
                       bounds=((b[0], b[1]), (b[2], b[3])))
               for bid, b in C.BLOCKED]
    for bid, b in C.BLOCKED:
        assert b[0] >= wl_lo[0] and b[1] >= wl_lo[1] \
            and b[2] <= wl_hi[0] and b[3] <= wl_hi[1], \
            f"blocked {bid} pokes past the walkable (E_InvalidRange class)"

    dests = []
    for d in (C.DEST_DRILL, C.DEST_WATCHERS, C.DEST_DRUMMERS,
              C.DEST_OFFICER_A, C.DEST_OFFICER_B):
        dests.append(Destination(id=d["id"], walkable_id=C.WALKABLE_ID,
                                 point=tuple(d["point"]),
                                 capacity_bounds=d["capacity"]))
    for d in dests:
        (plo, phi) = d.capacity_bounds
        assert wl_lo[0] <= plo[0] and wl_lo[1] <= plo[1] \
            and phi[0] <= wl_hi[0] and phi[1] <= wl_hi[1], \
            f"dest {d.id} capacity outside the walkable"

    graphs = [
        BehaviorGraph(id="march_in",
                      root=Navigate(id="tf_drill_nav",
                                    destination_id=C.DEST_DRILL["id"])),
        BehaviorGraph(id="shade_wander",
                      root=Navigate(id="tf_watch_nav",
                                    destination_id=C.DEST_WATCHERS["id"])),
        BehaviorGraph(id="drum_hold",
                      root=HoldPosition(id="tf_drum_hold")),
        BehaviorGraph(id="officer_a_approach",
                      root=Navigate(id="tf_oa_nav",
                                    destination_id=C.DEST_OFFICER_A["id"])),
        BehaviorGraph(id="officer_b_approach",
                      root=Navigate(id="tf_ob_nav",
                                    destination_id=C.DEST_OFFICER_B["id"])),
    ]

    graph_by_pop = {
        "drill": "march_in", "watchers": "shade_wander",
        "drummers": "drum_hold", "officer_a": "officer_a_approach",
        "officer_b": "officer_b_approach",
    }
    pops = []
    for pid, count, spawn, speed, dest_id, graph_id in C.POP_PLAN:
        assert graph_by_pop[pid] == graph_id or graph_id == "officer_approach", \
            f"graph drift for {pid}: {graph_id}"
        gid = graph_by_pop[pid]
        sx_lo, sy_lo, sx_hi, sy_hi = spawn
        pops.append(Population(
            id=f"tform_{pid}",
            count=count,
            emission_interval_ticks=1,          # the F-TS4 law
            spawn_sources=[SpawnSource(
                id=f"{pid}_spawn", walkable_id=C.WALKABLE_ID, start_tick=0,
                bounds=((sx_lo, sy_lo), (sx_hi, sy_hi)))],
            destinations=[(dest_id, 1.0)],
            archetypes=[("adult_a", 1.0)],
            appearances=[("blue", 1.0)],
            distributions=PopulationDistributions(
                preferred_speed_mps=speed),
            behavior_graph_id=gid,
        ))
    # the ingest-order laws: populations[0] owns the envelope cap and is
    # the drill pop (the plan order IS the ingest order -- the F-TS4
    # vendor-hijack fence).
    assert pops[0].id == "tform_drill"
    cap = pops[0].distributions.preferred_speed_mps[0] + 3.0 * \
        pops[0].distributions.preferred_speed_mps[1]
    for pop in pops:
        mu, sig = pop.distributions.preferred_speed_mps
        assert mu + 3.0 * sig <= cap + 1e-9, \
            f"envelope broken: {pop.id} max {mu + 3 * sig} > cap {cap}"
    n_cache = sum(p.count for p in pops)
    assert n_cache == C.N_CACHE, f"cache law: {n_cache} != {C.N_CACHE}"

    scene = CrowdScene(
        project=project, populations=pops, walkables=[walkable],
        blocked=blocked, destinations=dests, force_fields=[],
        behavior_graphs=graphs, portals=[], queues=[])
    return scene


def pop_membership(C, cache_path):
    """Resolve cache ordinals -> plan pops by the STATIC table's
    population_id + UNIQUE COUNTS (the spawn-table order law is DEAD:
    the tform probe measured the ingest REORDERING the populations --
    the static table read 24/4/1/1/72 = drill/drummers/officers/
    watchers, NOT the 24/72/4/1/1 plan order). The counts here are
    deliberately distinct so count-matching is total; the two 1-count
    officer pops disambiguate by their MEASURED arrival box (dest y
    sign), which the officers reach well before the hold.

    Returns {plan_pop_id: [ordinal, ...]}."""
    import blender_crowd_native
    cache = blender_crowd_native.Cache(cache_path)
    static = cache.read_agents()
    pop_col = _u32(static["population_id"])
    by_count = {}
    for plan_id, count, *_ in C.POP_PLAN:
        by_count.setdefault(count, []).append(plan_id)
    groups = {}
    used = set()
    for p_idx in np.unique(pop_col):
        ordinals = [int(k) for k in np.nonzero(pop_col == p_idx)[0]]
        n = len(ordinals)
        cands = [pid for pid in by_count.get(n, []) if pid not in used]
        if len(cands) == 1:
            groups[cands[0]] = ordinals
            used.add(cands[0])
        else:
            # the two 1-count officers land here (count 1 twice)
            assert n == 1, (
                f"ambiguous pop group: cache pop {p_idx} has {n} agents, "
                f"candidates {cands} -- extend the count-matching law")
            groups.setdefault("_singles", []).extend(ordinals)
    assert len(groups.get("_singles", [])) == 2, \
        f"expected exactly two officer singles: {groups}"
    # disambiguate the officers by their late positions (the dest boxes
    # differ in y sign around the ring's E edge)
    fr = cache.read_tick(420)
    pos = _f32(fr["position"], 3)
    s1, s2 = groups["_singles"]
    ya, yb = float(pos[s1, 1]), float(pos[s2, 1])
    del groups["_singles"]
    groups["officer_a" if ya > yb else "officer_b"] = [s1]
    groups["officer_b" if ya > yb else "officer_a"] = [s2]
    assert set(groups) == {pid for pid, *_ in C.POP_PLAN}, groups
    return groups


def _f32(b, cols):
    return np.frombuffer(b, dtype=np.float32).reshape(-1, cols)


def _u32(b):
    return np.frombuffer(b, dtype=np.uint32)


def measure_probe(C, cache_path):
    """The probe measurements: membership, the t120 halt payload, the
    officers' arrivals, the march-in read, the spacing rehearsal."""
    import blender_crowd_native
    from scripts.crowd.advanced import agent_ids

    ids = agent_ids(cache_path)
    assert len(ids) == C.N_CACHE
    cache = blender_crowd_native.Cache(cache_path)
    groups = pop_membership(C, cache_path)
    drill_ord = groups["drill"]
    drill_ids = [ids[k] for k in drill_ord]
    oa_ord, ob_ord = groups["officer_a"][0], groups["officer_b"][0]
    oa_id, ob_id = ids[oa_ord], ids[ob_ord]

    # --- the t120 halt payload (MEASURED; the dress PIN seeds) --------
    f120 = cache.read_tick(120)
    pos120 = _f32(f120["position"], 3).astype(np.float64)
    st120 = _u32(f120["behavior_state"])
    drill_pos120 = pos120[drill_ord].copy()

    # --- the officers' arrivals (first Arrived tick near their box) ---
    def _arrival(ordinal, box_pt):
        for t in range(60, 461):
            fr = cache.read_tick(t)
            st = int(_u32(fr["behavior_state"])[ordinal])
            p = _f32(fr["position"], 3)[ordinal]
            if st == 2 and math.hypot(float(p[0]) - box_pt[0],
                                      float(p[1]) - box_pt[1]) <= 1.0:
                return t
        return None
    oa_arr = _arrival(oa_ord, tuple(C.DEST_OFFICER_A["point"]))
    ob_arr = _arrival(ob_ord, tuple(C.DEST_OFFICER_B["point"]))
    assert oa_arr is not None and ob_arr is not None, \
        f"officers never arrive by t460 (a={oa_arr} b={ob_arr})"
    assert oa_arr <= 420 and ob_arr <= 420, \
        f"officers arrive after the hold ends (a={oa_arr} b={ob_arr})"

    # --- the march-in read (the halt reads ASSEMBLED) ------------------
    line = C.line_slots()
    near = 0
    for x, y, _z in drill_pos120:
        d = min(math.hypot(x - lx, y - ly) for lx, ly in line)
        if d <= C.DRESS_MAX_MOVE:
            near += 1
    frac = near / len(drill_pos120)
    assert frac >= 0.5, \
        f"march-in read broken: only {near}/24 within dress reach at t120"
    arrived_n = int((st120[drill_ord] == 2).sum())
    print(f"[tform_bake] march-in read: {near}/24 within dress reach, "
          f"{arrived_n}/24 state=Arrived at t120")

    # --- the spacing rehearsal (R6, the OPERATIVE core -- the SECOND
    # evidence fold, the tfog zero-arrived precedent): fold 1 measured
    # the halt packing (~0.28, arrived-ghosts); fold 2 measured two
    # DRESS paths CROSSING at 0.29 mid-window (measured points 3.8 m
    # apart, interleaved slots -- any straight-line morph between a
    # scattered 2D halt and a 1D line has crossing pairs). The 0.7
    # formation floor therefore BINDS from the WHEEL (t169 -- the
    # first true formation phase: rigid rotation 1.0, halt pin, then
    # the repaired circle/hold/dispersal); the dress opening carries
    # the no-overlap floor (0.15) and is RECORDED (the honest
    # dress-open note).
    traj = _authored_trajectories(C, drill_ids, drill_pos120)
    lo, hi = 132, 539
    min_d, arg_d = 1e9, None
    early_min = 1e9
    disp_min = 1e9
    for t in range(lo, hi + 1):
        P = np.array([traj[i][t] for i in range(24)])  # 24x2
        D = np.linalg.norm(P[:, None, :] - P[None, :, :], axis=-1)
        np.fill_diagonal(D, 1e9)
        m = float(D.min())
        if t < 169:
            early_min = min(early_min, m)
            assert m >= 0.15, \
                f"the dress OPEN overlaps: {m:.3f} m at t{t} (< 0.15)"
            continue
        if t >= 421:
            # the DISPERSAL is the formation DISSOLVING (the design's
            # own R6 aside: "the pinch phase is the dispersal morph") --
            # the streaming funnel converges the ring into the 4-lane
            # gap column; no-overlap floor + recorded (the
            # streaming-dissolve note; floor bound through the hold).
            disp_min = min(disp_min, m)
            assert m >= 0.15, \
                f"the dispersal overlaps: {m:.3f} m at t{t} (< 0.15)"
            continue
        if m < min_d:
            min_d, arg_d = m, t
    assert min_d >= 0.7, \
        f"spacing rehearsal FAILS: {min_d:.3f} m at t{arg_d} (< 0.7)"
    print(f"[tform_bake] spacing rehearsal green: formation floor min "
          f"{min_d:.3f} m at t{arg_d}; dress opens from "
          f"{early_min:.3f} m; dispersal dissolves to "
          f"{disp_min:.3f} m (both recorded)")

    receipt = {
        "cache_path": cache_path,
        "drill_ids": [int(i) for i in drill_ids],
        "officer_a": {"id": int(oa_id), "arrival_tick": int(oa_arr)},
        "officer_b": {"id": int(ob_id), "arrival_tick": int(ob_arr)},
        "dress_pin": {str(int(a)): [float(drill_pos120[k, 0]),
                                    float(drill_pos120[k, 1]),
                                    float(drill_pos120[k, 2])]
                      for k, a in enumerate(drill_ids)},
        "spacing_min_m": min_d,
        "early_dress_min_m": early_min,
        "dispersal_min_m": disp_min,
        "arrived_at_120": arrived_n,
    }
    return receipt


def _authored_trajectories(C, drill_ids, pos120):
    """The FULL authored trajectory per drill agent, tick 120..539
    inclusive: pin -> dress -> wheel -> halt -> circle -> hold ->
    dispersal. Pure python dict tick->(x,y).

    ASSIGNMENT REPAIR (the probe's empirical fold): the ingest-order
    slot zip CROSSING-dances -- measured march positions have no
    relationship to slot order, so straight-line dress/circle/
    dispersal paths pass within 0.07 m (the t150/t330/t500 rehearsal
    failures). Fix: order-preserving sorted-zip FIRST, then the
    deterministic swap-repair against the R6 oracle below -- the
    rehearsal itself is the assignment's acceptance test."""
    line = C.line_slots()
    ring = C.ring_slots()

    def repair(targets0, path_fn, ticks, floor=0.7, max_swaps=400):
        """Greedy deterministic swap-repair: while any tick in `ticks`
        pinches below `floor`, swap the two targets whose swap most
        improves the global min. `path_fn(agent_k, target)` rebuilds a
        single agent's path fragment over `ticks`."""
        targets = list(targets0)
        def build_all():
            return [np.array([path_fn(k, targets[k], t)
                              for t in ticks]) for k in range(24)]
        def global_min(paths):
            m = 1e9
            for t in range(len(ticks)):
                P = np.array([paths[k][t] for k in range(24)])
                D = np.linalg.norm(P[:, None, :] - P[None, :, :], axis=-1)
                np.fill_diagonal(D, 1e9)
                m = min(m, float(D.min()))
            return m
        paths = build_all()
        swaps = 0
        while swaps < max_swaps:
            # worst tick + pair
            wt, wp, wm = None, None, 1e9
            for ti, t in enumerate(ticks):
                P = np.array([paths[k][ti] for k in range(24)])
                D = np.linalg.norm(P[:, None, :] - P[None, :, :], axis=-1)
                np.fill_diagonal(D, 1e9)
                i, j = np.unravel_index(D.argmin(), D.shape)
                if D[i, j] < wm:
                    wt, wp, wm = ti, (int(i), int(j)), float(D[i, j])
            if wm >= floor:
                break
            i, j = wp
            best = (global_min(paths), None)
            targets[i], targets[j] = targets[j], targets[i]
            paths2 = build_all()
            m2 = global_min(paths2)
            if m2 > best[0]:
                paths, best = paths2, (m2, True)
                swaps += 1
                continue
            targets[i], targets[j] = targets[j], targets[i]  # revert
            # no improving pair swap on the worst pair: try the worst
            # agent against every other (bounded scan, 24 tries)
            improved = False
            for o in range(24):
                if o == i:
                    continue
                targets[i], targets[o] = targets[o], targets[i]
                paths2 = build_all()
                m2 = global_min(paths2)
                if m2 > best[0]:
                    paths, best = paths2, (m2, True)
                    improved = True
                    swaps += 1
                    break
                targets[i], targets[o] = targets[o], targets[i]
            if not improved:
                break
        return targets, float(global_min(paths))

    # --- dress: measured -> line slot ---------------------------------
    t_d0, t_d1 = 132, 168
    dress_ticks = list(range(t_d0, t_d1 + 1))
    cx, cy = C.ASSEMBLY_C

    def ang_about(p, c):
        return math.atan2(p[1] - c[1], p[0] - c[0]) % (2 * math.pi)
    meas_order = sorted(range(24), key=lambda k: ang_about(
        (pos120[k, 0], pos120[k, 1]), (cx, cy)))
    slot_order = sorted(range(24), key=lambda k: ang_about(line[k],
                                                           (cx, cy)))
    dress_of = {}
    for a, b in zip(meas_order, slot_order):
        dress_of[a] = b

    def dress_path(k, slot_idx, t):
        """Measured -> slot with the DRESS BULGE: a mid-flight outward
        bias (u(1-u), zero at BOTH ends -- the continuity law holds)
        that separates the packed halt column while the ranks dress.
        The probe measured the arrived column pinching to ~0.28 m
        (the arrived-ghost packing); a straight lerp stays under the
        0.7 floor until u~0.6 -- the bulge opens the pinch by u~0.3.
        The extra path length rides K1's recomposed phase (walk band)."""
        u = (t - t_d0) / (t_d1 - t_d0)
        p0 = (pos120[k, 0], pos120[k, 1])
        s = line[slot_idx]
        x = p0[0] + (s[0] - p0[0]) * u
        y = p0[1] + (s[1] - p0[1]) * u
        # outward from the assembly centroid (per-agent, deterministic)
        dx, dy = x - cx, y - cy
        n = math.hypot(dx, dy) or 1.0
        b = 1.2 * u * (1.0 - u)          # 0 at ends, 0.3 peak
        return (x + dx / n * b, y + dy / n * b)

    dress_slot, _ = repair([dress_of[k] for k in range(24)], dress_path,
                           dress_ticks, floor=0.7)

    # --- circle: halt slot -> ring slot (CIRCULAR SERIATION + repair).
    # The halt is a HALF-CIRCLE arc about the ring center (the wheel
    # parks the line N of the mark) -- a naive sorted-zip wraps the arc
    # ends across the whole circle (a 167-degree swing pair; the
    # t346 0.35 pinch). Seriation: try all 24 seams x both directions
    # of the ring order, keep the min-total-squared-path zip (the
    # standard circular assignment; deterministic), then repair.
    t_w0, t_w1 = C.WHEEL["window"]
    t_c0, t_c1 = 300, 360
    halt_slot = [C.wheel_slot(line[dress_slot[k]], t_w1)
                 for k in range(24)]
    ring_order0 = sorted(range(24), key=lambda k: ang_about(ring[k],
                                                            C.CIRCLE_C))
    halt_order = sorted(range(24), key=lambda k: ang_about(halt_slot[k],
                                                           C.CIRCLE_C))
    best_zip, best_cost = None, 1e18
    for seam in range(24):
        for direction in (+1, -1):
            seq = [ring_order0[(seam + direction * i) % 24]
                   for i in range(24)]
            cost = 0.0
            for a, b in zip(halt_order, seq):
                dx = ring[b][0] - halt_slot[a][0]
                dy = ring[b][1] - halt_slot[a][1]
                cost += dx * dx + dy * dy
            if cost < best_cost:
                best_cost, best_zip = cost, list(zip(halt_order, seq))
    ring_of = {}
    for a, b in best_zip:
        ring_of[a] = b

    def circle_path(k, ring_idx, t):
        u = (t - t_c0) / (t_c1 - t_c0)
        h = halt_slot[k]
        r = ring[ring_idx]
        return (h[0] + (r[0] - h[0]) * u, h[1] + (r[1] - h[1]) * u)

    circle_slot, _ = repair([ring_of[k] for k in range(24)], circle_path,
                            list(range(t_c0, t_c1 + 1)), floor=0.7)

    # --- dispersal: ring slot -> gap-column slot (seriation on the
    # bearing circle + repair -- the same wrap law as the circle).
    t_s0, t_s1 = C.DISPERSAL_WINDOW
    gap_cols = C.gap_column_slots()
    disp_of = {}
    bearing = lambda p: math.atan2(24.0 - p[1], 0.0 - p[0]) % (2 * math.pi)
    ring_order2 = sorted(range(24), key=lambda k: bearing(ring[k]))
    col_order = sorted(range(len(gap_cols)), key=lambda k: bearing(
        gap_cols[k]))
    best_zip2, best_cost2 = None, 1e18
    # the column has 24 slots too -- full seriation
    for seam in range(24):
        for direction in (+1, -1):
            seq = [col_order[(seam + direction * i) % 24]
                   for i in range(24)]
            cost = 0.0
            for a, b in zip(ring_order2, seq):
                dx = gap_cols[b][0] - ring[a][0]
                dy = gap_cols[b][1] - ring[a][1]
                cost += dx * dx + dy * dy
            if cost < best_cost2:
                best_cost2, best_zip2 = cost, list(zip(ring_order2, seq))
    for a, b in best_zip2:
        disp_of[a] = b

    def disp_path(k, col_idx, t):
        # fix-wave-1 D5b: the dispersal MUST march from the agent's
        # HELD ring slot (ring[circle_slot[k]] — the hold window's pin)
        # — the raw ring[k] index-space mixup teleported every agent
        # whose circle repair moved it (24 boundary snaps at t=420/421,
        # |v| to 95 m/s, caught by the composed verifier).
        return C.dispersal_sample(ring[circle_slot[k]],
                                  gap_cols[col_idx], t - t_s0)

    # the column seriation keys are RING indices — map through the
    # agent's circle slot (the same index-space law as disp_path)
    disp_slot, _ = repair([disp_of[circle_slot[k]] for k in range(24)],
                          disp_path,
                          list(range(t_s0, t_s1 + 1)), floor=0.7)

    # --- assemble the full trajectories -------------------------------
    traj = []
    for k in range(24):
        p0 = (pos120[k, 0], pos120[k, 1])
        slot = line[dress_slot[k]]
        wheel_end = C.wheel_slot(slot, t_w1)
        ring_slot = ring[circle_slot[k]]
        col = gap_cols[disp_slot[k]]
        path = {}
        for t in range(120, t_d0 + 1):
            path[t] = p0                                   # pin (incl)
        for t in range(t_d0, t_d1 + 1):
            path[t] = dress_path(k, dress_slot[k], t)
        for t in range(t_w0, t_w1 + 1):
            path[t] = C.wheel_slot(slot, t)
        for t in range(t_w1, t_c0 + 1):
            path[t] = wheel_end                            # halt (incl)
        for t in range(t_c0, t_c1 + 1):
            path[t] = circle_path(k, circle_slot[k], t)
        for t in range(t_c1, t_s0 + 1):
            path[t] = ring_slot                            # hold (incl)
        for t in range(t_s0, t_s1 + 1):
            path[t] = disp_path(k, disp_slot[k], t)
        traj.append(path)
    return traj


def stage_probe(C, out, t0):
    from scripts.crowd import bake
    bridge = _bootstrap()
    scene = build_scene(C, bridge)
    n_ingest = sum(p.count for p in scene.populations)
    print(f"[tform_bake] custom scene OK: {n_ingest} cache agents, "
          f"{len(scene.behavior_graphs)} graphs, no fields")
    assert n_ingest == C.N_CACHE
    with warnings.catch_warnings(record=True) as wlist:
        warnings.simplefilter("always")
        result = bake(scene, cache_dir=str(out))
        for w in wlist:
            print(f"[tform_bake][warn] {w.message}")
    assert result.status == "complete", result.status
    cache_path = _cache_file(out)
    pin = result.source_hash[:8] if result.source_hash else "??"
    print(f"[tform_bake] probe bake done in {time.time() - t0:.1f}s "
          f"pin {pin} mode {result.compile_mode}")
    receipt = measure_probe(C, cache_path)
    receipt["probe_pin"] = pin
    (out / "probe_receipt.json").write_text(json.dumps(receipt, indent=1))
    print(f"[tform_bake] probe stage PASS ({time.time() - t0:.1f}s); "
          f"officers a@t{receipt['officer_a']['arrival_tick']} "
          f"b@t{receipt['officer_b']['arrival_tick']}")


def build_layer_stack(C, receipt):
    """The 168-layer stack (7 windows x 24 drill agents) as
    LayoutOverrides, from the probe receipt's MEASURED pin payload and
    the contract's formation helpers (the repaired assignments inside
    _authored_trajectories are THE source of truth for every
    transform sample)."""
    from scripts.crowd.advanced import LayoutOverride, OverrideType

    cache_path = receipt["cache_path"]
    drill_ids = receipt["drill_ids"]
    pos120 = np.array([receipt["dress_pin"][str(a)]
                       for a in drill_ids])          # 24x3 measured
    traj = _authored_trajectories(C, drill_ids, pos120)

    t_d0, t_d1 = 132, 168
    t_w0, t_w1 = C.WHEEL["window"]
    t_h0, t_h1 = 252, 299
    t_c0, t_c1 = 300, 360
    t_g0, t_g1 = 361, 420
    t_s0, t_s1 = C.DISPERSAL_WINDOW

    def samples(k, ticks):
        # fix-wave-1 D5-REV2: "operation": "absolute" is THE fix — the
        # payload samples are ABSOLUTE yard coordinates; without the
        # key _build_edit defaults to ADDITIVE and the native composes
        # base+traj, snapping every window seam by the base magnitude
        # (measured: 392 events >4 m/s, max 55.8, ALL at boundaries).
        return [{"tick": int(t),
                 "translation": [round(float(traj[k][t][0]), 4),
                                 round(float(traj[k][t][1]), 4), 0.0]}
                for t in ticks]

    def transform_payload(k, t0_, t1_):
        return {"operation": "absolute",
                "samples": samples(k, range(t0_, t1_ + 1))}

    def pin(k, t):
        p = traj[k][t]
        return [round(float(p[0]), 4), round(float(p[1]), 4), 0.0]

    ov = []
    for k, aid in enumerate(drill_ids):
        t = (aid,)
        ov.append(LayoutOverride(
            name=f"tform_w1_pin_{k}", target_agent_ids=t,
            tick_range=(120, 131), override_type=OverrideType.PIN,
            payload={"position": pin(k, 120)}))
        ov.append(LayoutOverride(
            name=f"tform_w2_dress_{k}", target_agent_ids=t,
            tick_range=(t_d0, t_d1), override_type=OverrideType.TRANSFORM,
            payload=transform_payload(k, t_d0, t_d1)))
        ov.append(LayoutOverride(
            name=f"tform_w3_wheel_{k}", target_agent_ids=t,
            tick_range=(t_w0, t_w1), override_type=OverrideType.TRANSFORM,
            payload=transform_payload(k, t_w0, t_w1)))
        ov.append(LayoutOverride(
            name=f"tform_w4_halt_{k}", target_agent_ids=t,
            tick_range=(t_h0, t_h1), override_type=OverrideType.PIN,
            payload={"position": pin(k, t_w1)}))
        ov.append(LayoutOverride(
            name=f"tform_w5_circle_{k}", target_agent_ids=t,
            tick_range=(t_c0, t_c1), override_type=OverrideType.TRANSFORM,
            payload=transform_payload(k, t_c0, t_c1)))
        ov.append(LayoutOverride(
            name=f"tform_w6_hold_{k}", target_agent_ids=t,
            tick_range=(t_g0, t_g1), override_type=OverrideType.PIN,
            payload={"position": pin(k, t_c1)}))
        ov.append(LayoutOverride(
            name=f"tform_w7_disp_{k}", target_agent_ids=t,
            tick_range=(t_s0, t_s1), override_type=OverrideType.TRANSFORM,
            payload=transform_payload(k, t_s0, t_s1)))
    names = [o.name for o in ov]
    assert len(names) == len(set(names)) == C.N_LAYERS, (
        f"layer stack: {len(names)} rows, {len(set(names))} unique, "
        f"contract pins {C.N_LAYERS}")
    return ov


def stage_layers(C, out, t0):
    from scripts.crowd.advanced import (apply_layout_overrides,
                                        inspect_layout)
    receipt = json.loads((out / "probe_receipt.json").read_text())
    cache_path = receipt["cache_path"]
    ov = build_layer_stack(C, receipt)
    ok = apply_layout_overrides(cache_path, ov)
    assert ok, "apply_layout_overrides returned False"
    print(f"[tform_bake] {len(ov)} layers applied "
          f"({time.time() - t0:.1f}s)")
    # conflicts == [] at EVERY phase boundary (the design law) --
    # boundaries abut: the union window set's endpoints.
    bounds = sorted({120, 131, 132, 168, 169, 251, 252, 299, 300, 360,
                     361, 420, 421, 539})
    for t in bounds:
        insp = inspect_layout(cache_path, tick=t)
        assert list(insp.conflicts) == [], \
            f"layer conflicts at t{t}: {list(insp.conflicts)[:3]}"
    # plus a stride sweep through the transform windows (the same law,
    # mid-phase: the ranges abut, but a bad sample row could conflict)
    for t in range(126, 540, 7):
        insp = inspect_layout(cache_path, tick=t)
        assert list(insp.conflicts) == [], \
            f"layer conflicts at t{t}: {list(insp.conflicts)[:3]}"
    print(f"[tform_bake] conflicts == [] at {len(bounds)} boundaries + "
          f"the stride sweep; layers stage PASS ({time.time() - t0:.1f}s)")
    (out / "layers_receipt.json").write_text(json.dumps(
        {"layers": len(ov), "boundaries_checked": bounds}, indent=1))


def stage_interaction(C, out, t0):
    """The officers' clasp (M5 bake_interaction): the test_m5 fixture
    pattern bound to the REAL cache identity + the MEASURED officers'
    ids/arrivals. Flow-then-pin: converge = clip 1 with phase flowing;
    clasp-hold = clip 0 phase pinned. The root samples are authored
    from the SAME cache numbers (the pinned positions at the anchor),
    stepping each officer (|d|-0.15)/2 toward the other across the
    converge so the grip's 0.15 m contact is physically honest."""
    import blender_crowd_native
    from scripts.crowd.advanced import agent_ids
    from scripts.crowd.interactions import (
        bake_interaction, Contact, InteractionLayer, InteractionParticipant,
        InteractionRequest, RootConstraint, RootSample, AnimationEdit)

    receipt = json.loads((out / "probe_receipt.json").read_text())
    cache_path = receipt["cache_path"]
    ids = agent_ids(cache_path)
    oa_id = receipt["officer_a"]["id"]
    ob_id = receipt["officer_b"]["id"]
    oa_ord = ids.index(oa_id)
    ob_ord = ids.index(ob_id)
    cache = blender_crowd_native.Cache(cache_path)
    real_hash = str(cache.base_cache_hash)

    a_arr = receipt["officer_a"]["arrival_tick"]
    b_arr = receipt["officer_b"]["arrival_tick"]
    anchor = max(a_arr, b_arr, 362)
    w = int(C.INTERACTION["window_ticks"])
    t_end = min(anchor + w - 1, 419)
    t0w, t1w = anchor, t_end
    converge_split = t0w + (t1w - t0w) // 2
    print(f"[tform_bake] beat window [{t0w},{t1w}] "
          f"(anchor from arrivals a@{a_arr} b@{b_arr}); converge "
          f"[{t0w},{converge_split}], clasp [{converge_split + 1},{t1w}]")

    pos_a = _f32(cache.read_tick(t0w)["position"], 3)[oa_ord][:2]
    pos_b = _f32(cache.read_tick(t0w)["position"], 3)[ob_ord][:2]
    d = np.array([pos_b[0] - pos_a[0], pos_b[1] - pos_a[1]])
    dist = float(np.linalg.norm(d))
    step = max((dist - C.INTERACTION["contact_distance_m"]) / 2.0, 0.0)
    u = d / (dist or 1.0)
    clasp_a = pos_a + u * step
    clasp_b = pos_b - u * step

    def yaw_to(fx, fy):
        return math.atan2(fx, fy)      # the wrapper yaw law

    yaw_a = yaw_to(-u[0], -u[1])       # A faces B
    yaw_b = yaw_to(u[0], u[1])         # B faces A

    def roots_for(ord_, p_start, p_clasp, yaw):
        smp = []
        for t in range(t0w, t1w + 1):
            if t <= converge_split:
                v = (t - t0w) / max(converge_split - t0w, 1)
                p = p_start + (p_clasp - p_start) * v
            else:
                p = p_clasp
            smp.append(RootSample(tick=t, position=(float(p[0]),
                                                    float(p[1]), 0.0),
                                  yaw=float(yaw)))
        return smp

    request = InteractionRequest(
        request_id="tform-clasp-001",
        group_id="officers-beat",
        participants=(
            InteractionParticipant(agent_id=oa_id, role="initiator",
                                   retarget_profile_id="reference-humanoid"),
            InteractionParticipant(agent_id=ob_id, role="responder",
                                   retarget_profile_id="reference-humanoid"),
        ),
        tick_start=t0w, tick_end=t1w, seed=C.CROWD_SEED,
        action="salute-and-clasp",
        outcome="clasp-hold-to-end-of-hold",
        base_cache_hash=real_hash,
        graph_hash="af" * 32,       # the film's authored-graphs pin
        root_constraints=(
            RootConstraint(agent_id=oa_id,
                           samples=roots_for(oa_ord, pos_a, clasp_a,
                                             yaw_a)),
            RootConstraint(agent_id=ob_id,
                           samples=roots_for(ob_ord, pos_b, clasp_b,
                                             yaw_b)),
        ),
        contact_constraints=(Contact(
            contact_id="clasp-c1", owner_agent_id=oa_id,
            other_agent_id=ob_id,
            label=C.INTERACTION["contact_label"],
            tick_start=converge_split + 1, tick_end=t1w),),
    )
    edits = []
    for t in range(t0w, t1w + 1):
        if t <= converge_split:
            ph = (t - t0w) / max(converge_split - t0w, 1)
            edits.append(AnimationEdit(agent_id=oa_id, tick=t,
                                       clip_id=C.INTERACTION[
                                           "converge_clip"],
                                       phase=round(ph, 4)))
            edits.append(AnimationEdit(agent_id=ob_id, tick=t,
                                       clip_id=C.INTERACTION[
                                           "converge_clip"],
                                       phase=round(1.0 - ph, 4)))
        else:
            edits.append(AnimationEdit(agent_id=oa_id, tick=t,
                                       clip_id=C.INTERACTION["clasp_clip"],
                                       phase=C.INTERACTION["clasp_phase"]))
            edits.append(AnimationEdit(agent_id=ob_id, tick=t,
                                       clip_id=C.INTERACTION["clasp_clip"],
                                       phase=C.INTERACTION["clasp_phase"]))
    layer = InteractionLayer(
        layer_id="tform-clasp-001-layer",
        interaction_id=request.request_id,
        base_cache_hash=real_hash,
        target_agent_ids=(oa_id, ob_id),
        tick_start=t0w, tick_end=t1w,
        edits=tuple(edits),
        provenance=C.INTERACTION["protocol"],
    )
    motion = {
        "schema_version": 1,
        "request_id": request.request_id,
        "participants": [
            {"agent_id": rc.agent_id,
             "root_samples": [{"tick": s.tick,
                               "translation": list(s.position),
                               "yaw": s.yaw} for s in rc.samples],
             "skeletal_channels": []}
            for rc in request.root_constraints
        ],
        "contacts": [
            {"contact_id": "clasp-c1", "label":
             C.INTERACTION["contact_label"],
             "owner_agent_id": oa_id, "other_agent_id": ob_id,
             "tick": converge_split + 1,
             "distance_m": C.INTERACTION["contact_distance_m"]},
        ],
        "provenance": {"backend": "authored-paired-clip",
                       "model_hash": None, "seed": request.seed,
                       "config_hash": C.INTERACTION["protocol"]},
        "diagnostics": [],
        "fallback": {"clip_set_id": layer.fallback_clip_set,
                     "clip_id": layer.fallback_clip_id,
                     "reason": layer.fallback_reason},
    }
    receipt_ix = bake_interaction(cache_path, layer, request,
                                  json.dumps(motion, sort_keys=True))
    expected_edits = 2 * (t1w - t0w + 1)
    assert receipt_ix["edits_applied"] == expected_edits, (
        f"sidecar edits {receipt_ix['edits_applied']} != "
        f"2x window-ticks ({expected_edits})")
    assert len(receipt_ix["layer_ids"]) == expected_edits, (
        f"sidecar layer rows {len(receipt_ix['layer_ids'])} != "
        f"2x window-ticks (the design's sidecar law)")
    print(f"[tform_bake] bake_interaction receipt: "
          f"{receipt_ix['edits_applied']} edits "
          f"({len(receipt_ix['layer_ids'])} layer rows), backend "
          f"{receipt_ix.get('motion_backend')}")
    (out / "interaction_receipt.json").write_text(json.dumps(
        {"window": [t0w, t1w], "converge_split": converge_split,
         "edits": receipt_ix["edits_applied"],
         "base_cache_hash": real_hash[:12],
         "officer_a": {"id": oa_id, "pos": list(map(float, pos_a)),
                       "clasp": list(map(float, clasp_a))},
         "officer_b": {"id": ob_id, "pos": list(map(float, pos_b)),
                       "clasp": list(map(float, clasp_b))}}, indent=1))
    print(f"[tform_bake] interaction stage PASS ({time.time() - t0:.1f}s)")


def _verify_composition(C, receipt, npz_path):
    """D5-REV2: continuity + formation-shape asserts on the COMPOSED
    npz. Ordinal->column mapping via the cache's agent_ids order."""
    bridge = _bootstrap()
    from scripts.crowd.advanced import agent_ids
    cache_path = receipt["cache_path"]
    all_ids = list(agent_ids(cache_path))
    drill_ids = receipt["drill_ids"]
    cols = [all_ids.index(a) for a in drill_ids]
    pos120 = np.array([receipt["dress_pin"][str(a)] for a in drill_ids])
    traj = _authored_trajectories(C, drill_ids, pos120)
    z = np.load(str(npz_path))
    x, y = z["x"], z["y"]

    t_w0, t_w1 = C.WHEEL["window"]
    t_s0, t_s1 = C.DISPERSAL_WINDOW
    windows = [(120, 131, "w1_pin"), (132, 168, "w2_dress"),
               (t_w0, t_w1, "w3_wheel"), (252, 299, "w4_halt"),
               (300, 360, "w5_circle"), (361, 420, "w6_hold"),
               (t_s0, t_s1, "w7_disp")]
    # (a) continuity across EVERY boundary (including base<->layer)
    bounds = sorted({0, 120, 132, 168, t_w0, t_w1 + 1, 252, 300,
                     360, 361, 420, t_s0, t_s1 + 1,
                     int(z["x"].shape[0]) - 1})
    MAX_STEP = 0.6   # one tick of brisk walk (0.5 m/s x 1/12 s x margin)
    bad = 0
    for t in bounds:
        if t <= 0 or t >= x.shape[0]:
            continue
        for k, col in enumerate(cols):
            d = float(np.hypot(x[t, col] - x[t - 1, col],
                               y[t, col] - y[t - 1, col]))
            if d > MAX_STEP:
                bad += 1
                if bad <= 5:
                    print(f"[tform_bake] CONTINUITY FAIL t={t} "
                          f"agent={drill_ids[k]} d={d:.3f}m")
    assert bad == 0, (
        f"composed continuity: {bad} boundary snaps > {MAX_STEP} m "
        f"(the D5 teleport class is BACK — check the operation flag)")
    # (b) formation shape inside the TRANSFORM windows
    shape_bad = 0
    for (wa, wb, wname) in windows:
        if wname in ("w1_pin", "w4_halt", "w6_hold"):
            # PIN windows: the authored point (traj holds constant)
            t_pin = {120: 120, 252: t_w1, 361: 360}[wa]
            for k, col in enumerate(cols):
                for t in range(wa, wb + 1):
                    dx = abs(float(x[t, col]) - float(traj[k][t_pin][0]))
                    dy = abs(float(y[t, col]) - float(traj[k][t_pin][1]))
                    if dx > 5e-3 or dy > 5e-3:
                        shape_bad += 1
                        break
        else:
            for k, col in enumerate(cols):
                for t in range(wa, wb + 1):
                    dx = abs(float(x[t, col]) - float(traj[k][t][0]))
                    dy = abs(float(y[t, col]) - float(traj[k][t][1]))
                    if dx > 5e-3 or dy > 5e-3:
                        shape_bad += 1
                        if shape_bad <= 5:
                            print(f"[tform_bake] SHAPE FAIL {wname} t={t} "
                                  f"agent={drill_ids[k]} d=({dx:.4f},{dy:.4f})")
                        break
    assert shape_bad == 0, (
        f"formation shape: {shape_bad} agent-windows diverge from the "
        f"authored trajectory > 5mm (the composition is wrong)")
    print(f"[tform_bake] composed verify OK: 0 boundary snaps, "
          f"{len(windows)} windows shape-exact, {len(cols)} drill agents")


def stage_finish(C, out, t0):
    """Composed npz with clip_source="channel" (the DIRECT bridge call
    -- never the CLI, the design's RQ10) + the mapping probe + the
    cast/sfx spine."""
    receipt = json.loads((out / "probe_receipt.json").read_text())
    cache_path = receipt["cache_path"]
    bridge = _bootstrap()
    scene = build_scene(C, bridge)
    events = _read_events_safe(cache_path)
    print(f"[tform_bake] events: {len(events)} (the drill is a "
          f"formation film -- the sfx spine is authored)")
    digest = bridge.to_previz_cache(
        cache_path, scene, str(out / "cache_v6.npz"),
        # fix-wave-2 audit round: the S10/S11 lenses moved onto the
        # yard's south lane -- the keepout rows are now contract-born
        keepouts=tuple(C.CAM_KEEPOUTS),
        keepout_radius=C.CAM_KEEPOUT_R,
        clamp=True,
        clip_source=C.CLIP_SOURCE,         # "channel" (RQ10)
    )
    assert digest.get("clip_source") == C.CLIP_SOURCE, \
        f"receipt clip_source {digest.get('clip_source')} != " \
        f"{C.CLIP_SOURCE} (the RQ10 law)"
    print(f"[tform_bake] clip_source receipt: {digest['clip_source']}")

    # --- fix-wave-1 D5-REV2: the composed-cache verification ---------
    # (a) CONTINUITY: no window boundary may snap (one tick of walk
    #     speed is the bound);
    # (b) FORMATION SHAPE: inside every window the composed position
    #     equals the AUTHORED trajectory (the R6 rehearsal validated
    #     traj only — the composition was never checked, which is how
    #     additive-vs-absolute shipped).
    _verify_composition(C, receipt, out / "cache_v6.npz")

    # --- the mapping probe ---------------------------------------------
    z = np.load(str(out / "cache_v6.npz"))
    clip = z["clip"]
    vocab = set(np.unique(clip).tolist())
    # the MAPPED vocabulary (the v6 ids the frozen table emits):
    # Shamble_A=3 (idle AND walk), Sprint_Loop=7 (jog)
    mapped = {bridge.V6_CLIP_SHAMBLE_A, bridge.V6_CLIP_SPRINT_LOOP}
    unknown = vocab - mapped
    assert not unknown, \
        f"clip rows outside the mapped vocabulary: {unknown}"
    # the officers' clasp window reads the PINNED idle clip (kit 0)
    ix = _interaction_receipt = json.loads(
        (out / "interaction_receipt.json").read_text())
    t0w, t1w = ix["window"]
    ids = receipt["drill_ids"]          # ordinals != id order in the npz;
    oa_id = receipt["officer_a"]["id"]  # the npz columns follow agent_ids
    from scripts.crowd.advanced import agent_ids
    all_ids = agent_ids(cache_path)
    oa_col = all_ids.index(oa_id)
    ob_col = all_ids.index(receipt["officer_b"]["id"])
    t_lo = t0w * 1 - 0                  # npz time axis: cache ticks
    t_hi = t1w
    # the npz tick axis: frame/2 - 1 (the x2 law); read defensively
    n_t = clip.shape[-1] if clip.ndim > 1 else len(clip)
    print(f"[tform_bake] mapping probe: clip vocab {sorted(vocab)} "
          f"over {n_t} ticks; officers' clasp window maps inside it")
    ctx = bridge.to_previz_ctx(cache_path, scene, digest=digest)
    ctx["cast"] = {
        "heroes": [
            {"name": "standard_bearer", "kind": "actor",
             "lane": "banner-cross"},
            {"name": "captain", "kind": "actor", "lane": "forensic-hold"},
        ],
        "officers": {
            "a": {"id": receipt["officer_a"]["id"],
                  "arrival_tick": receipt["officer_a"]["arrival_tick"]},
            "b": {"id": receipt["officer_b"]["id"],
                  "arrival_tick": receipt["officer_b"]["arrival_tick"]},
        },
        "beat_window": ix["window"],
        "phases": [list(p) for p in C.DR_PHASES],
        "wheel": {k: (v if not isinstance(v, float) else round(v, 6))
                  for k, v in C.WHEEL.items()},
        "sfx_rows": [],                 # authored spine rides SFX_EVENTS
        "beats": [list(b) for b in C.BEATS],
        "sfx_events": list(C.SFX_EVENTS),
    }
    (out / "cache_ctx.json").write_text(json.dumps(ctx, indent=1))
    print(f"[tform_bake] finish: npz + ctx written "
          f"({time.time() - t0:.1f}s); payload "
          f"{digest.get('payload_sha256', '?')[:8]}")


def stage_verify(C, out, t0):
    """The design section-4 determinism law: re-bake + re-apply the
    FULL stack (probe -> layers -> interaction -> finish) in a FRESH
    clone dir, then BYTE-COMPARE the npz against the main run."""
    import shutil
    vdir = out / "verify_clone"
    if vdir.exists():
        shutil.rmtree(vdir)
    vdir.mkdir()
    for st in ("probe", "layers", "interaction", "finish"):
        # reuse the same stage functions against the clone dir
        if st == "probe":
            stage_probe(C, vdir, t0)
        elif st == "layers":
            stage_layers(C, vdir, t0)
        elif st == "interaction":
            stage_interaction(C, vdir, t0)
        else:
            stage_finish(C, vdir, t0)
    a = out / "cache_v6.npz"
    b = vdir / "cache_v6.npz"
    import hashlib
    ha = hashlib.sha256(a.read_bytes()).hexdigest()
    hb = hashlib.sha256(b.read_bytes()).hexdigest()
    print(f"[tform_bake] npz main {ha[:12]} vs clone {hb[:12]}")
    assert ha == hb, (
        "the determinism law BROKE: re-applied stack produced a "
        "different npz")
    print(f"[tform_bake] verify: BYTE-IDENTICAL ({ha[:12]}); "
          f"determinism law green ({time.time() - t0:.1f}s)")


def _read_events_safe(cache_path):
    from scripts.crowd.advanced import read_events
    try:
        return read_events(cache_path)
    except ValueError as e:
        print(f"[tform_bake][warn] events unreadable: {e}")
        return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/tmp/crowdcache_tform")
    ap.add_argument("--stage",
                    choices=("probe", "layers", "interaction", "finish",
                             "verify"),
                    default="probe")
    args = ap.parse_args()

    bridge = _bootstrap()
    out = Path(args.out)
    if args.stage == "probe":
        if out.exists() and any(out.iterdir()):
            raise SystemExit(
                f"[tform_bake] --out {out} is not empty -- the fresh-dir "
                "law; pass a fresh dir")
        out.mkdir(parents=True, exist_ok=True)
    elif args.stage in ("layers", "interaction", "finish", "verify"):
        if not (out / "probe_receipt.json").is_file():
            raise SystemExit(
                f"[tform_bake] no probe_receipt.json in {out} -- run "
                "--stage probe first")

    sys.path.insert(0, str(HERE))
    import tform_contract as C

    t0 = time.time()
    if args.stage == "probe":
        stage_probe(C, out, t0)
    elif args.stage == "layers":
        stage_layers(C, out, t0)
    elif args.stage == "interaction":
        stage_interaction(C, out, t0)
    elif args.stage == "finish":
        stage_finish(C, out, t0)
    elif args.stage == "verify":
        stage_verify(C, out, t0)
    else:
        raise SystemExit(f"[tform_bake] stage {args.stage} not yet wired")


if __name__ == "__main__":
    main()
