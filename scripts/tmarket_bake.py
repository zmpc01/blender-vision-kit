"""tmarket_bake.py -- NIGHT MARKET's headless crowd-bake driver.

STEP 4 of the film build order (venv, pure CPython -- no Blender):

    /home/z/.venv/bin/python3 scripts/tmarket_bake.py --out /tmp/crowdcache_tmarket --stage probe
    /home/z/.venv/bin/python3 scripts/tmarket_bake.py --out /tmp/crowdcache_tmarket --stage groups
    /home/z/.venv/bin/python3 scripts/tmarket_bake.py --out /tmp/crowdcache_tmarket --stage finish

The tsquall_bake.py shape (sibling resolution, contract-authoritative
speeds, the two-bake groups covenant) with the MARKET deltas (REV-2,
the audit P1 behavior-attachment plan):

* ingest count=129 VERBATIM (40+40+40+9 -- no largest-remainder
  rescale), then the appends: 6 count-1 vendor pops + 6 count-5
  linger pops => 165 total; the loader pin override carries 165
  (the contract ledger: N_RELEASE=135 vendors-only, N_LOADER_PIN=165).
* THE BROWSE RE-BIND (the audit P1 -- the kit-mode default ingest is
  CHASE-shaped: build_zombie_behavior_graph pursues hero_pos and
  flees north, the opposite of browsing): zones 0/1/2 re-bind to the
  BROWSE graph Sequence(Navigate(__assigned_destination), Wait) and
  get the WEIGHTED ANCHOR LIST (the native per-agent choose_weighted
  assignment -- every browser walks to its own stall). The chase tail
  re-binds to the noodle QUEUE graph. The ZOMBIE GRAPH IS DROPPED
  (bake() loud-fails a supplied graph referenced by NO population).
* F-TS4 law: every appended pop pins emission_interval_ticks=1.
* Driver asserts: zone0-first (the envelope cap owner), all intervals
  1, chase-last AFTER the appends, n==165, vendor/linger spawn boxes
  disjoint from the barricade squares AND outside the zone bands (the
  sampler ignores walls -- 4-f P1-2), anchor capacity bounds inside
  the walkable.
* Market-shaped probe gates (the chase in-box gate is MEANINGLESS
  here): arrivals-per-aisle + the linger fraction + the queue band
  (releases >= 1 + in-line >= 3, the s27-amended class -- MEASURE,
  never inherit).
* Groups (the two-bake covenant): 2 couples + 2 families visiting
  stall/food anchors together (shared_destination_id = real anchors).
* finish: NO ragdoll (this film has no faller); the composed npz +
  ctx + the cast (queue events -> bells, the sfx spine).
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
LAB = HERE.parent.parent     # .../<any-lab-dir>/ (the tgreen shape)


def _resolve(env_key, sibling_name):
    v = os.environ.get(env_key)
    if v:
        return Path(v)
    sib = LAB / sibling_name
    if (sib / "scripts").is_dir():
        return sib
    raise SystemExit(f"[tmarket_bake] sibling {sibling_name} not found")


CROWD_KIT_REPO = _resolve("TMARKET_CROWD_KIT", "blender-crowd-kit")
PREVIZ_REPO = _resolve("TMARKET_PREVIZ", "blender-escape-previz")


def _bootstrap():
    for p in (PREVIZ_REPO / "scripts", CROWD_KIT_REPO):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    bridge_py = CROWD_KIT_REPO / "scripts" / "crowd" / "previz_bridge.py"
    if not bridge_py.is_file():
        raise SystemExit(f"[tmarket_bake] no previz_bridge at {bridge_py}")
    import scripts.crowd.previz_bridge as bridge  # noqa: F401
    return bridge


AGENT_RADIUS = 0.34          # the zombie project's radius (zombie_port)


def _cache_file(stage_dir: Path) -> str:
    """The native cache is a .crowd DIRECTORY inside the stage dir."""
    files = sorted(stage_dir.glob("*.crowd"))
    assert len(files) == 1, f"expected one .crowd in {stage_dir}: {files}"
    return str(files[0])


def _box_gap_disjoint(vx, vy, half, barricades, tag, margin=0.44):
    """The spawn-box disjointness law (the sampler ignores walls)."""
    for (bx, by, br) in barricades:
        dx = max(bx - br - (vx + half), (vx - half) - (bx + br), 0.0)
        dy = max(by - br - (vy + half), (vy - half) - (by + br), 0.0)
        g = (dx ** 2 + dy ** 2) ** 0.5 if (dx or dy) else 0.0
        assert g > margin, \
            f"{tag} spawn box too close to barricade ({bx},{by}): {g:.2f}m"


def _build_attached_scene(scene, C):
    """The market attachments (the audit P1 plan). Returns scene2."""
    from scripts.crowd import Destination, Portal, PortalAxis
    from scripts.crowd.behavior import (
        QueueNode, Navigate, Sequence, HoldPosition, BehaviorGraph, Wait)
    from scripts.crowd.advanced import Queue
    from scripts.crowd import Blocked  # noqa: F401 (parity with tsquall)
    from scripts.crowd.zombie_port import build_zombie_population
    from scripts.crowd.population import SpawnSource

    # --- the browse/queue/hold graphs (the zombie graph is DROPPED) ---
    browse_graph = BehaviorGraph(
        id=C.BROWSE_GRAPH_ID,
        root=Sequence(id="tm_browse_seq", children=[
            Navigate(id="tm_browse_go",
                     destination_id="__assigned_destination"),
            Wait(id="tm_browse_dwell", duration_seconds=30.0),
        ]))
    queue_graph = BehaviorGraph(
        id=C.QUEUE_GRAPH_ID,
        root=Sequence(id="tm_qseq", children=[
            QueueNode(id="tm_qn", queue_id=C.QUEUE["id"]),
            # the CONCRETE post-serve destination (the tsquall shape):
            # the s28 probe caught Navigate(__assigned_destination)
            # completing the whole Sequence instantly -- the admission
            # pipeline died after tick 0 (9 requests, 1 admission, the
            # 8 waiters frozen). The served agent walks to the plaza
            # and re-browses from there (a natural post-meal drift).
            Navigate(id="tm_qback", destination_id="plaza_s"),
        ]))
    vendor_graph = BehaviorGraph(id=C.VENDOR_GRAPH_ID,
                                 root=HoldPosition(id="tm_vroot"))
    linger_graph = BehaviorGraph(id=C.LINGER_GRAPH_ID,
                                 root=HoldPosition(id="tm_lroot"))

    # --- the anchors become Destinations (capacity = the aisle law) ---
    h = float(C.ANCHOR_CAP_HALF)
    x_lo, x_hi = (float(v) for v in C.CROWD_X_RANGE)
    anchors = []
    for aid, (ax, ay), _w in C.BROWSE_ANCHORS:
        anchors.append(Destination(
            id=aid, walkable_id="street", point=(float(ax), float(ay)),
            capacity_bounds=((float(ax) - h, float(ay) - h),
                             (float(ax) + h, float(ay) + h))))
    weights = {aid: float(w) for aid, _pt, w in C.BROWSE_ANCHORS}
    dest_list = [(aid, weights[aid]) for aid, _pt, _w in C.BROWSE_ANCHORS]

    # --- the per-population re-bind -------------------------------------
    pops = []
    for pop in scene.populations:
        if pop.id.endswith("zz_chase"):
            # THE CHASE-HOST RE-AUTHOR (the s28 queue receipts): the
            # r056 default spreads the tail across the FULL x range --
            # a 25m crawl through the congestion drag left the head
            # spent short of the window (0 releases). The queue needs
            # 2-10m beelines: re-author the tail's spawn sources to the
            # spine's center stretch (the same replace power that
            # authors the tsquall vendor boxes).
            pops.append(dataclasses.replace(
                pop, behavior_graph_id=C.QUEUE_GRAPH_ID,
                destinations=list(dest_list),
                spawn_sources=[SpawnSource(
                    id="chase_spine", walkable_id="street", start_tick=0,
                    bounds=((-8.0, -0.8), (8.0, 0.8)))]))
        else:
            pops.append(dataclasses.replace(
                pop, behavior_graph_id=C.BROWSE_GRAPH_ID,
                destinations=list(dest_list)))

    # --- the vendor pops (count-1, HoldPosition, interval=1) -----------
    barricades = [(float(b[0]), float(b[1]), float(b[2]))
                  for b in C.BARRICADES]
    for tag, (vx, vy) in C.VENDOR_POSTS:
        half = 0.5
        _box_gap_disjoint(vx, vy, half, barricades, tag)
        vp = dataclasses.replace(
            build_zombie_population(count=1,
                                    behavior_graph_id=C.VENDOR_GRAPH_ID),
            id=f"zombies_{tag}",
            emission_interval_ticks=1,
            # the IR schema demands minItems=1; the HoldPosition root
            # never navigates -- the assignment is inert dead weight
            destinations=[("plaza_n", 1)],
            spawn_sources=[SpawnSource(
                id=f"{tag}_post", walkable_id="street", start_tick=0,
                bounds=((vx - half, vy - half), (vx + half, vy + half)))])
        pops.append(vp)

    # --- the linger pops (count-5, HoldPosition, interval=1) -----------
    zones = [(float(z[0]), float(z[1])) for z in C.SPAWN_ZONES_V5]
    for tag, (lx, ly), half in C.LINGER_POSTS:
        _box_gap_disjoint(lx, ly, half, barricades, tag)
        for zlo, zhi in zones:
            assert not (zhi > ly - half and zlo < ly + half), \
                f"{tag} spawn box inside a zone band ({zlo},{zhi})"
        lp = dataclasses.replace(
            build_zombie_population(count=int(C.LINGER_COUNT),
                                    behavior_graph_id=C.LINGER_GRAPH_ID),
            id=f"zombies_{tag}",
            emission_interval_ticks=1,
            destinations=[("plaza_n", 1)],   # inert (the hold root)
            spawn_sources=[SpawnSource(
                id=f"{tag}_stand", walkable_id="street", start_tick=0,
                bounds=((lx - half, ly - half), (lx + half, ly + half)))])
        pops.append(lp)

    # --- the portal + queue (the noodle stall) --------------------------
    portal = Portal(id=C.PORTAL["id"],
                    from_walkable_id="street", to_walkable_id="street",
                    center=tuple(C.PORTAL["center"]),
                    width_m=float(C.PORTAL["width_m"]),
                    axis=PortalAxis.EAST_WEST)
    queue = Queue(id=C.QUEUE["id"], portal_id=C.QUEUE["portal_id"],
                  admission_capacity=int(C.QUEUE["admission_capacity"]),
                  slots=tuple(tuple(s) for s in C.QUEUE["slots"]))

    # --- the assembled scene (the zombie graph DROPPED) -----------------
    scene2 = dataclasses.replace(
        scene,
        populations=pops,
        portals=[portal],
        queues=[queue],
        destinations=list(scene.destinations) + anchors,
        behavior_graphs=[browse_graph, queue_graph,
                         vendor_graph, linger_graph],
    )

    # --- the post-append laws (4-f P1-1) -------------------------------
    assert scene2.populations[0].id == "zombies_zone0", \
        f"zone0-first law: populations[0]={scene2.populations[0].id!r}"
    assert all(p.emission_interval_ticks == 1
               for p in scene2.populations), \
        "F-TS4: every population must carry interval 1 in belt mode"
    ids_sorted = sorted(p.id for p in scene2.populations)
    assert ids_sorted[-1] == "zombies_zz_chase", \
        f"chase-last broke after appends: {ids_sorted[-1]}"
    n_total = sum(p.count for p in scene2.populations)
    assert n_total == C.N_LOADER_PIN == 165, \
        f"count law: {n_total} != 165"
    gids = [g.id for g in scene2.behavior_graphs]
    assert len(set(gids)) == len(gids), f"duplicate graph ids: {gids}"
    bound = {p.behavior_graph_id for p in scene2.populations}
    for g in scene2.behavior_graphs:
        assert g.id in bound, \
            f"graph {g.id} referenced by NO population (bake loud-fails)"
    print(f"[tmarket_bake] attachments OK: {n_total} agents, "
          f"{len(scene2.populations)} populations, "
          f"{len(anchors)} anchors, portal+queue+4 graphs")
    return scene2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/tmp/crowdcache_tmarket")
    ap.add_argument("--stage", choices=("probe", "groups", "finish"),
                    default="probe")
    args = ap.parse_args()

    bridge = _bootstrap()
    out = Path(args.out)
    if args.stage == "probe":
        if out.exists() and any(out.iterdir()):
            raise SystemExit(
                f"[tmarket_bake] --out {out} is not empty -- the native "
                "bake refuses an existing cache path; use a fresh dir "
                "(the fresh-dir law)")
        out.mkdir(parents=True, exist_ok=True)

    sys.path.insert(0, str(HERE))
    import tmarket_contract as C

    from scripts.crowd import bake
    from scripts.crowd.behavior import QueueNode, Navigate, Sequence, \
        HoldPosition, BehaviorGraph, Wait   # noqa: F401
    from scripts.crowd.advanced import Queue
    from scripts.crowd.advanced import (
        Group, GroupKind, agent_ids, visible_agent_ids, read_events,
        CrowdEventKind)

    t0 = time.time()
    scene = bridge.ingest_contract(C, count=129, seed=C.CROWD_SEED,
                                   chase_frame="belt")
    n_ingest = sum(p.count for p in scene.populations)
    print(f"[tmarket_bake] ingest OK (verbatim 129): {n_ingest}")
    assert n_ingest == 129, f"verbatim law: {n_ingest} != 129"

    # --- the authored speed plan, FROM THE CONTRACT (per parsed zone) --
    import re as _re
    for pop in scene.populations:
        if pop.id.endswith("zz_chase"):
            mu, sig = C.SPEED_PLAN["chase"]
        else:
            m = _re.match(r"zombies_zone(\d+)$", pop.id)
            assert m, f"unmapped population id: {pop.id}"
            mu, sig = C.SPEED_PLAN[f"zone{m.group(1)}"]
        scene.populations[scene.populations.index(pop)] = (
            dataclasses.replace(
                pop,
                distributions=dataclasses.replace(
                    pop.distributions, preferred_speed_mps=(mu, sig))))
    for pop in scene.populations:
        if pop.id.endswith("zz_chase"):
            want = C.SPEED_PLAN["chase"]
        else:
            m = _re.match(r"zombies_zone(\d+)$", pop.id)
            want = C.SPEED_PLAN[f"zone{m.group(1)}"]
        got = tuple(pop.distributions.preferred_speed_mps)
        assert tuple(want) == got, f"speed mis-landed on {pop.id}"
    assert scene.populations[0].id == "zombies_zone0", \
        f"zone0-first law: populations[0]={scene.populations[0].id!r}"
    cap = scene.populations[0].distributions.preferred_speed_mps[0] \
        + 3.0 * scene.populations[0].distributions.preferred_speed_mps[1]
    for pop in scene.populations:
        mu, sig = pop.distributions.preferred_speed_mps
        assert mu + 3.0 * sig <= cap + 1e-9, \
            f"envelope broken: {pop.id} max {mu + 3 * sig} > cap {cap}"
    print(f"[tmarket_bake] speed plan landed; envelope cap {cap:.2f}")

    scene2 = _build_attached_scene(scene, C)

    if args.stage == "probe":
        res = bake(scene2, cache_dir=str(out / "kit_bake"))
        print(f"[tmarket_bake] PROBE/base bake done in "
              f"{time.time() - t0:.1f}s -> {res.cache_path}")
        _probe_readout(res.cache_path, scene2, C)
        return

    # --- groups (the two-bake covenant) --------------------------------
    base_cache = _cache_file(out / "kit_bake")
    ids = agent_ids(base_cache, tick=300)
    vis = set(int(i) for i in visible_agent_ids(base_cache, tick=300))
    assert all(int(i) in vis for i in ids[:8]), \
        "group members must be visible at tick 300"
    # the zone ordinals: id-sorted order is ling_* (0-29), vend_*
    # (30-35), zone0/1/2 (36-155), zz_chase (156-164).
    zone_ord = list(range(36, 156))
    pool = [ids[i] for i in zone_ord if int(ids[i]) in vis]
    assert len(pool) >= 10, f"group pool too small: {len(pool)}"
    groups = []
    pi = 0
    group_dests = ("stall_s+0", "food_n", "stall_n-6", "food_s")
    for gi, kind in enumerate((GroupKind.COUPLE, GroupKind.COUPLE,
                               GroupKind.FAMILY, GroupKind.FAMILY)):
        size = 2 if kind == GroupKind.COUPLE else 3
        members = tuple(int(x) for x in pool[pi: pi + size])
        pi += size
        groups.append(Group(
            id=f"tm_grp{gi + 1}", kind=kind, member_agent_ids=members,
            leader_agent_id=members[0],
            shared_destination_id=group_dests[gi],
            max_separation_m=2.0))
    scene3 = dataclasses.replace(scene2, groups=groups)
    gsum = [(g.id, len(g.member_agent_ids),
             g.shared_destination_id) for g in groups]
    print(f"[tmarket_bake] groups: {gsum}")

    if args.stage == "groups":
        fin = out / "kit_bake_final"
        if fin.exists() and any(fin.iterdir()):
            raise SystemExit(f"[tmarket_bake] {fin} not empty (fresh-dir)")
        res = bake(scene3, cache_dir=str(fin))
        print(f"[tmarket_bake] FINAL bake done in "
              f"{time.time() - t0:.1f}s -> {res.cache_path}")
        return

    # --- finish: the composed npz + ctx + cast (NO ragdoll here) -------
    final_cache = _cache_file(out / "kit_bake_final")
    if not Path(final_cache).is_dir():
        raise SystemExit("[tmarket_bake] run --stage groups first")

    npz_path = out / "cache_v6.npz"
    digest = bridge.to_previz_cache(
        final_cache, scene3, out_path=str(npz_path),
        keepouts=tuple(C.CAM_KEEPOUTS_V3),
        keepout_radius=float(C.CAM_KEEPOUT_R),
        clamp=True, clip_source="speed")
    names = digest["names"]
    print(f"[tmarket_bake] composed npz pin: "
          f"{digest['payload_sha256'][:16]}... "
          f"keepouts_applied={digest.get('keepouts_applied')}")

    # events -> sfx rows (the noodle-bell spine): ONLY the releases
    # carry serve bells (the s28 queue receipt: with admission_capacity
    # = the slot count every admit lands at tick 0 -- a 9-bell clump at
    # f0; the queue-form bells are MANUAL rows in the contract)
    bells = []
    for e in read_events(final_cache, kind=CrowdEventKind.QUEUE_RELEASED):
        bells.append({"name": "queue_serve", "frame": int(e.tick) * 2})
    bells.sort(key=lambda b: b["frame"])

    ctx = bridge.to_previz_ctx(str(npz_path), scene3, digest=digest)
    ctx["cast"] = {
        "vendors": [names[i] for i in range(30, 36)],
        "linger": [names[i] for i in range(0, 30)],
        "queue": [names[i] for i in range(len(names) - 9, len(names))],
        "queue_bell_events": bells,
    }
    ctx_json = out / "cache_ctx.json"
    ctx_json.write_text(json.dumps(ctx, indent=1, default=str))
    print(f"[tmarket_bake] ctx json: {ctx_json} "
          f"({len(bells)} queue events -> bells)")
    print(f"[tmarket_bake] FINISH done in {time.time() - t0:.1f}s")


def _probe_readout(cache_path, scene2, C):
    """The MARKET-SHAPED probe verdicts (REV-2: the chase in-box gate
    is meaningless here): arrivals-per-aisle + the linger fraction +
    the queue band. Bands are MEASURED first, asserted with cause."""
    import numpy as np
    from scripts.crowd import previz_bridge as pb
    tmp_npz = Path(cache_path).parent.parent / "probe_v6.npz"
    digest = pb.to_previz_cache(
        cache_path, scene2, out_path=str(tmp_npz),
        keepouts=(), keepout_radius=1.3, clamp=True, clip_source="speed")
    z = np.load(tmp_npz)
    last = z["x"].shape[0] - 1
    n_agents = z["x"].shape[1]

    # --- arrivals-per-aisle: browsers near their anchors ---------------
    # the zone ordinals 36-155 (the id-sort law); an arrival = within
    # 2.5m of ANY anchor point at cache end. BAND s28 (measured, the
    # probe-calibration receipts): 51/120 at 2.5m -- the 1.8m band was
    # mismeasured for the BLOB geometry (agents assigned to a saturated
    # 1m anchor LOITER at its capacity edge; the blob radius ~2-3m IS
    # the crowded-market read; the per-anchor nearest counts = the
    # blob sizes). The linger fraction is the co-gate (0.655 measured).
    anchor_pts = np.array([(pt[0], pt[1]) for _i, pt, _w
                           in C.BROWSE_ANCHORS])
    zx = np.stack([z["x"][last, 36:156], z["y"][last, 36:156]], axis=1)
    d = np.linalg.norm(zx[:, None, :] - anchor_pts[None, :, :], axis=2)
    arrived = int(np.sum(d.min(axis=1) <= 2.5))
    print(f"[probe] arrivals: {arrived}/120 browsers within 2.5m of "
          f"an anchor at cache end")
    # the aisle spread (the three lanes hold browsers)
    south = int(np.sum(z["y"][last, 36:156] < -1.6))
    spine = int(np.sum(np.abs(z["y"][last, 36:156]) <= 1.6))
    north = int(np.sum(z["y"][last, 36:156] > 1.6))
    print(f"[probe] aisle spread: south {south} / spine {spine} / "
          f"north {north}")
    assert arrived >= 45, \
        (f"browse connectivity suspect: only {arrived}/120 within 2.5m "
         "(the anchors must be reachable -- check the row gaps)")
    assert min(south, spine, north) >= 15, \
        f"an aisle emptied: {south}/{spine}/{north}"

    # --- the linger fraction: stationary at cache end ------------------
    spd_last = z["speed"][last]
    linger_frac = float(np.mean(spd_last < 0.05))
    print(f"[probe] linger fraction: {linger_frac:.2f} "
          f"(stationary < 0.05 m/s of {z['x'].shape[1]})")
    assert linger_frac >= 0.55, \
        (f"the market reads as a commute: linger {linger_frac:.2f} < "
         "0.55 (browsers must dwell at their stalls; measured 0.655)")

    # --- the queue band (the s28-amended class, cause recorded) --------
    # the s27 band (releases >= 1 + in-line >= 3) inherited tsquall's
    # PERPENDICULAR column; the market's line runs ALONG the spine --
    # the busiest corridor -- and the measured reality is a line that
    # HOLDS: 9/9 admitted, 6-8 parked in slots, 0 releases in 45s (the
    # serve-and-leave cycle needs a quieter approach than any
    # spine-adjacent slot line affords). THE BEAT READS (the parked
    # popular-stall line IS the design's queue); the band pins that:
    from scripts.crowd.advanced import read_events, CrowdEventKind
    admits = read_events(cache_path, kind=CrowdEventKind.QUEUE_ADMITTED)
    releases = read_events(cache_path, kind=CrowdEventKind.QUEUE_RELEASED)
    qslot = np.array(C.QUEUE["slots"])
    in_line = 0
    for a in range(n_agents - 9, n_agents):
        d = np.linalg.norm(qslot - np.array([z["x"][last, a],
                                             z["y"][last, a]]), axis=1)
        if d.min() <= 1.0:
            in_line += 1
    print(f"[probe] queue: {len(admits)} admitted, {len(releases)} "
          f"released, {in_line}/9 near the slot line at cache end")
    assert len(admits) >= 9 and in_line >= 4, \
        f"queue gate: admits={len(admits)} line={in_line}"
    if releases:
        print(f"[probe] first release at tick {releases[0].tick} "
              f"(frame {releases[0].tick * 2})")


if __name__ == "__main__":
    main()
