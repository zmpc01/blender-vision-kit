"""tsquall_bake.py -- SQUALL's headless crowd-bake driver.

STEP 4 of the film build order (venv, pure CPython -- no Blender):

    /home/z/.venv/bin/python3 scripts/tsquall_bake.py --out /tmp/crowdcache_tsquall --stage probe
    /home/z/.venv/bin/python3 scripts/tsquall_bake.py --out /tmp/crowdcache_tsquall --stage groups
    /home/z/.venv/bin/python3 scripts/tsquall_bake.py --out /tmp/crowdcache_tsquall --stage finish

The tgreen_bake.py shape (sibling resolution, contract-authoritative
speeds, pre-bake envelope assert) with the SQUALL deltas (REV-3):

* ingest count=129 VERBATIM (44+40+36+9 -- no largest-remainder
  rescale) THEN 6 count-1 vendor pops appended (total 135; the loader
  pin override carries 135 -- F-TS5).
* M6 attachments: ONE portal (the arcade facade divider, axis
  NORTH_SOUTH -- the crossing-direction law), ONE queue (9 slots along
  the food window, capacity 1), a second BehaviorGraph
  Sequence(QueueNode, Navigate) bound to the chase tail, and a
  HoldPosition vendor graph bound to the 6 stall pops.
* F-TS4 law: every appended pop pins emission_interval_ticks=1 (the
  native reads ONE global interval from the ID-SORTED populations[0];
  the vendor default 5 would silently re-time the whole film).
* Driver asserts: zone0-first (the envelope cap reads DECLARED list
  order), all intervals 1, chase-last AFTER the appends, n==135,
  vendor spawn boxes disjoint from the barricade squares (the sampler
  ignores walls -- 4-f P1-2).
* Two bakes (the groups covenant): base bake mints the stable ids,
  groups attach via dataclasses.replace, final bake. Fresh dirs (the
  fresh-dir law); the pin recorded per stage.
* finish: the faller pick from the flow data (the rim band law),
  the ragdoll handoff (stays down to film end), the cast list, the
  events->sfx rows, the F-TS1-composed npz + ctx.
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
    raise SystemExit(f"[tsquall_bake] sibling {sibling_name} not found")


CROWD_KIT_REPO = _resolve("TSQUALL_CROWD_KIT", "blender-crowd-kit")
PREVIZ_REPO = _resolve("TSQUALL_PREVIZ", "blender-escape-previz")


def _bootstrap():
    for p in (PREVIZ_REPO / "scripts", CROWD_KIT_REPO):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    bridge_py = CROWD_KIT_REPO / "scripts" / "crowd" / "previz_bridge.py"
    if not bridge_py.is_file():
        raise SystemExit(f"[tsquall_bake] no previz_bridge at {bridge_py}")
    import scripts.crowd.previz_bridge as bridge  # noqa: F401
    return bridge


AGENT_RADIUS = 0.34          # the zombie project's radius (zombie_port)
FALL_TICK = 190              # tick_start: the fall lands at f380-381
BASIN = (14.0, 7.5)          # the fountain center (contract BARRICADES)
RIM_LO, RIM_HI = 2.6, 3.6    # the pick band (the barricade law: >=2.6)


def _cache_file(stage_dir: Path) -> str:
    """The native cache is a .crowd DIRECTORY inside the stage dir."""
    files = sorted(stage_dir.glob("*.crowd"))
    assert len(files) == 1, f"expected one .crowd in {stage_dir}: {files}"
    return str(files[0])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/tmp/crowdcache_tsquall")
    ap.add_argument("--stage", choices=("probe", "groups", "finish"),
                    default="probe")
    args = ap.parse_args()

    bridge = _bootstrap()
    out = Path(args.out)
    if args.stage == "probe":
        if out.exists() and any(out.iterdir()):
            raise SystemExit(
                f"[tsquall_bake] --out {out} is not empty -- the native "
                "bake refuses an existing cache path; use a fresh dir "
                "(the fresh-dir law)")
        out.mkdir(parents=True, exist_ok=True)

    sys.path.insert(0, str(HERE))
    import tsquall_contract as C

    from scripts.crowd import bake
    from scripts.crowd import Portal, PortalAxis, Destination  # noqa: F401
    from scripts.crowd.behavior import (
        QueueNode, Navigate, Sequence, HoldPosition, BehaviorGraph)
    from scripts.crowd.advanced import (
        Group, GroupKind, Queue,
        agent_ids, visible_agent_ids, read_events, CrowdEventKind)
    from scripts.crowd.ragdoll import (
        RagdollHandoff, simulate_ragdoll_handoff, attach_ragdoll_to_cache)
    from scripts.crowd.advanced import clear_kit_layout_layers

    t0 = time.time()
    scene = bridge.ingest_contract(C, count=129, seed=C.CROWD_SEED,
                                   chase_frame="belt")
    n_ingest = sum(p.count for p in scene.populations)
    print(f"[tsquall_bake] ingest OK (verbatim 129): {n_ingest}")
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
    # verify the plan landed BEFORE baking -- per population (F19)
    for pop in scene.populations:
        if pop.id.endswith("zz_chase"):
            want = C.SPEED_PLAN["chase"]
        else:
            m = _re.match(r"zombies_zone(\d+)$", pop.id)
            want = C.SPEED_PLAN[f"zone{m.group(1)}"]
        got = tuple(pop.distributions.preferred_speed_mps)
        assert tuple(want) == got, f"speed mis-landed on {pop.id}"
    # the envelope law: populations[0] IS the cap owner
    assert scene.populations[0].id == "zombies_zone0", \
        f"zone0-first law: populations[0]={scene.populations[0].id!r}"
    cap = scene.populations[0].distributions.preferred_speed_mps[0] \
        + 3.0 * scene.populations[0].distributions.preferred_speed_mps[1]
    for pop in scene.populations:
        mu, sig = pop.distributions.preferred_speed_mps
        assert mu + 3.0 * sig <= cap + 1e-9, \
            f"envelope broken: {pop.id} max {mu + 3 * sig} > cap {cap}"
    print(f"[tsquall_bake] speed plan landed; envelope cap {cap:.2f}")

    # --- the M6 attachments (REV-3 section 3) --------------------------
    portal = Portal(id=C.PORTAL["id"],
                    from_walkable_id="street", to_walkable_id="street",
                    center=tuple(C.PORTAL["center"]),
                    width_m=float(C.PORTAL["width_m"]),
                    axis=PortalAxis.NORTH_SOUTH)
    queue = Queue(id=C.QUEUE["id"], portal_id=C.QUEUE["portal_id"],
                  admission_capacity=int(C.QUEUE["admission_capacity"]),
                  slots=tuple(tuple(s) for s in C.QUEUE["slots"]))
    queue_graph = BehaviorGraph(
        id=C.QUEUE_GRAPH_ID,
        root=Sequence(id="squall_qseq", children=[
            QueueNode(id="squall_qn", queue_id=C.QUEUE["id"]),
            Navigate(id="squall_qnav", destination_id="hero_pos"),
        ]))
    vendor_graph = BehaviorGraph(id=C.VENDOR_GRAPH_ID,
                                 root=HoldPosition(id="squall_vroot"))

    # the queue subset = the chase tail (9 agents, spawns in zone0's
    # strips -- the nearest band). Never rename populations.
    pops = [dataclasses.replace(p, behavior_graph_id=C.QUEUE_GRAPH_ID)
            if p.id == "zombies_zz_chase" else p
            for p in scene.populations]

    # the 6 vendor pops (count-1 each; interval=1 -- the F-TS4 hijack
    # law; spawn boxes offset plaza-facing and DISJOINT from the
    # barricade squares inflated by radius+margin -- the sampler
    # ignores walls).
    from scripts.crowd.zombie_port import build_zombie_population
    from scripts.crowd.population import SpawnSource
    barricades = [(float(b[0]), float(b[1]), float(b[2]))
                  for b in C.BARRICADES]
    stall_pops = []
    for tag, (vx, vy) in C.VENDOR_POSTS:
        half = 0.5
        box = (vx - half, vy - half, vx + half, vy + half)
        for bx, by, br in barricades:
            dx = max(bx - br - (vx + half), (vx - half) - (bx + br), 0.0)
            dy = max(by - br - (vy + half), (vy - half) - (by + br), 0.0)
            gap = (dx ** 2 + dy ** 2) ** 0.5 if (dx or dy) else 0.0
            assert gap > AGENT_RADIUS + 0.1, \
                f"vendor spawn box too close to barricade ({tag}: {gap:.2f}m)"
        vp = dataclasses.replace(
            build_zombie_population(count=1,
                                    behavior_graph_id=C.VENDOR_GRAPH_ID),
            id=f"zombies_{tag}",
            emission_interval_ticks=1,
            spawn_sources=[SpawnSource(
                id=f"{tag}_post", walkable_id="street", start_tick=0,
                bounds=((box[0], box[1]), (box[2], box[3])))])
        stall_pops.append(vp)
    pops = pops + stall_pops

    # --- s25 (the collision/nav round): the undeclared walkable
    # statics become Blocked rects. The BARRICADES squares (stall
    # counters + fountain) already ride ingest_contract; these are the
    # geometry tsquall_world.py places that agents plausibly cross:
    # the arcade walls (FacadeSeg :313-317, Shopfront :319-323,
    # BackWall :335-336), the food counter (:337-338), the 3 facade
    # benches (:399-405), the 4 planters (:407-413; the south pair
    # sits OUTSIDE the walkable y0=-6 — no rows), the 2 trash
    # cylinders (:415-416), and the 3 fountain-approach bollards
    # (:390-393; the GATE-line bollards stay undeclared — they ARE
    # the queue's entry slalom and a line of blocks on the only
    # approach would partial-jam it, the no-path-planning engine
    # truth). Rects must fit FULLY inside the walkable
    # ((-30,-6),(30,15)) — a straddling rect is natively refused
    # (E_InvalidRange); the 0.15 margin is the personal-space law.
    from scripts.crowd import Blocked
    _rects = [
        ("facade_w", (-8.0, 5.85), (-5.0, 6.15)),
        ("facade_e", (5.0, 5.85), (8.0, 6.15)),
        ("shopfront_w", (-30.0, 5.85), (-8.0, 6.15)),
        ("shopfront_e", (8.0, 5.85), (30.0, 6.15)),
        ("back_wall", (-8.0, -6.0), (8.0, -5.7)),
        ("food_counter", (5.05, -5.98), (7.95, -5.3)),
        ("bench_w1", (-14.25, 6.27), (-12.15, 7.07)),
        ("bench_w2", (-11.85, 6.27), (-9.75, 7.07)),
        ("bench_e1", (12.95, 6.27), (15.05, 7.07)),
        ("planter_nw", (-10.15, 7.05), (-9.05, 8.15)),
        ("planter_ne", (9.05, 7.05), (10.15, 8.15)),
        ("trash_w", (-25.05, 8.85), (-23.75, 10.15)),
        ("trash_e", (23.75, 8.85), (25.05, 10.15)),
        ("bollard_f1", (10.61, 2.81), (11.39, 3.59)),
        ("bollard_f2", (13.61, 2.51), (14.39, 3.29)),
        ("bollard_f3", (16.61, 2.81), (17.39, 3.59)),
    ]
    _blocked = list(scene.blocked) + [
        Blocked(id=f"sq_static_{nm}", walkable_id="street",
                bounds=(lo, hi))
        for nm, lo, hi in _rects
    ]
    print(f"[tsquall_bake] s25 static rects: +{len(_rects)} blocked "
          f"(was {len(scene.blocked)})")

    scene2 = dataclasses.replace(
        scene,
        populations=pops,
        portals=[portal],
        queues=[queue],
        blocked=_blocked,
        behavior_graphs=list(scene.behavior_graphs)
        + [queue_graph, vendor_graph],
    )

    # --- the post-append laws (4-f P1-1) -------------------------------
    assert scene2.populations[0].id == "zombies_zone0", \
        "zone0-first broke after appends (the envelope cap law)"
    assert all(p.emission_interval_ticks == 1
               for p in scene2.populations), \
        "F-TS4: every population must carry interval 1 in belt mode"
    ids_sorted = sorted(p.id for p in scene2.populations)
    assert ids_sorted[-1] == "zombies_zz_chase", \
        f"chase-last broke after appends: {ids_sorted[-1]}"
    n_total = sum(p.count for p in scene2.populations)
    assert n_total == C.N_RELEASE == 135, \
        f"count law: {n_total} != 135"
    print(f"[tsquall_bake] attachments OK: {n_total} agents, "
          f"{len(scene2.populations)} populations, portal+queue+2 graphs")

    if args.stage == "probe":
        res = bake(scene2, cache_dir=str(out / "kit_bake"))
        print(f"[tsquall_bake] PROBE/base bake done in "
              f"{time.time() - t0:.1f}s -> {res.cache_path}")
        _probe_readout(res.cache_path, scene2, agent_ids,
                       visible_agent_ids, read_events, CrowdEventKind)
        return

    # --- groups (the two-bake covenant) --------------------------------
    base_cache = _cache_file(out / "kit_bake")
    ids = agent_ids(base_cache, tick=300)
    vis = set(int(i) for i in visible_agent_ids(base_cache, tick=300))
    assert all(int(i) in vis for i in ids[:8]), \
        "group members must be visible at tick 300"
    # 4 clusters from zone1/zone2 members. Zone ordinals: zone pops in
    # ingest order are zones 0..2 then chase; vendors occupy the FIRST
    # six ordinals (id-sorted stall pops). Resolve cluster members from
    # the visible mid list, skipping ordinals 0-5 (vendors) and the
    # chase tail (queue-bound).
    n_crowd = n_total - 9 - 6                     # 120 zone agents
    zone_ord = list(range(6, 6 + n_crowd))        # vendor 6 + zones
    pool = [ids[i] for i in zone_ord if int(ids[i]) in vis]
    assert len(pool) >= 12, f"group pool too small: {len(pool)}"
    groups = []
    pi = 0
    for gi, kind in enumerate((GroupKind.COUPLE, GroupKind.COUPLE,
                               GroupKind.FAMILY, GroupKind.FAMILY)):
        size = 2 if kind == GroupKind.COUPLE else 3
        members = tuple(int(x) for x in pool[pi: pi + size])
        pi += size
        groups.append(Group(
            id=f"squall_grp{gi + 1}", kind=kind, member_agent_ids=members,
            leader_agent_id=members[0],
            shared_destination_id="hero_pos", max_separation_m=2.0))
    scene3 = dataclasses.replace(scene2, groups=groups)
    gsum = [(g.id, len(g.member_agent_ids)) for g in groups]
    print(f"[tsquall_bake] groups: {gsum}")

    if args.stage == "groups":
        fin = out / "kit_bake_final"
        if fin.exists() and any(fin.iterdir()):
            raise SystemExit(f"[tsquall_bake] {fin} not empty (fresh-dir)")
        res = bake(scene3, cache_dir=str(fin))
        print(f"[tsquall_bake] FINAL bake done in "
              f"{time.time() - t0:.1f}s -> {res.cache_path}")
        return

    # --- finish: ragdoll + cast + events + composed npz/ctx ------------
    final_cache = _cache_file(out / "kit_bake_final")
    if not Path(final_cache).is_dir():
        raise SystemExit("[tsquall_bake] run --stage groups first")
    clear_kit_layout_layers(final_cache)   # idempotent re-runs
    names = None

    # pre-ragdoll conversion: the flow pick + the base-true reference
    pre_npz = out / "cache_v6_prerg.npz"
    digest = bridge.to_previz_cache(
        final_cache, scene3, out_path=str(pre_npz),
        keepouts=tuple(C.CAM_KEEPOUTS_V3),
        keepout_radius=float(C.CAM_KEEPOUT_R),
        clamp=True, clip_source="speed")
    names = digest["names"]
    z = np.load(pre_npz)
    # the faller: grazing the rim band INSIDE the S5 window (ticks
    # 176-214 so the fall lands within f352-428), any approach arc
    # (the natural approach is from the north -- the south side is the
    # wall squeeze), speed >= 0.4 (the straggler IS the casting; the
    # 4-e F9 fold). Emit the graze point for the camera aim.
    best, best_score = None, 1e9
    for a in range(z["x"].shape[1]):
        if a < 6 or a >= z["x"].shape[1] - 9:
            continue                    # vendors and the queue are out
        for t in range(176, 215):
            dx = float(z["x"][t, a]) - BASIN[0]
            dy = float(z["y"][t, a]) - BASIN[1]
            d = (dx * dx + dy * dy) ** 0.5
            sp = float(z["speed"][t, a])
            if RIM_LO <= d <= RIM_HI and sp >= 0.4:
                # bias EARLY ticks: the fall at ~f370-390 keeps ~2.5s of
                # S5 aftermath (the 4-e F7 hold law)
                score = abs(d - 3.0) + abs(t - 185) * 0.02
                if score < best_score:
                    best_score = score
                    best = (a, t, float(z["x"][t, a]),
                            float(z["y"][t, a]), sp)
    assert best is not None, \
        "no rim-band faller in the S5 window -- widen the pool or move the beat"
    faller_ord, FALL_TICK, gx, gy, gsp = best
    print(f"[tsquall_bake] faller: ordinal {faller_ord} "
          f"({names[faller_ord]}) grazes the rim at tick {FALL_TICK} "
          f"(graze ({gx:.2f},{gy:.2f}), speed {gsp:.2f})")

    # the ragdoll handoff: the incoming velocity comes from the KIT
    # cache's velocity channel at the beat tick (the npz has no vx) --
    # the exact source, not a yaw reconstruction.
    import blender_crowd_native as _bcn
    _nc = _bcn.Cache(final_cache)
    _row = np.frombuffer(
        _nc.read_tick(int(FALL_TICK))["velocity"],
        dtype="<f4").reshape(-1, 3)[faller_ord]
    vx, vy = float(_row[0]), float(_row[1])
    kit_ids = agent_ids(final_cache, tick=50)
    faller_id = int(kit_ids[faller_ord])
    handoff = RagdollHandoff(
        transition_id="squall_slip", agent_ids=(faller_id,),
        tick_start=int(FALL_TICK), tick_end=539,
        drop_height_m=0.45, impact_vz_mps=-0.6,
        restitution_millionths=0, zero_horizontal_velocity=False,
        incoming_velocity=(vx, vy, -0.6))
    sim = simulate_ragdoll_handoff(final_cache, handoff)
    layer_ids = attach_ragdoll_to_cache(final_cache, sim)
    print(f"[tsquall_bake] ragdoll attached: {layer_ids} "
          f"(vx={vx:.2f} vy={vy:.2f})")

    # the composed conversion (F-TS1 carries the fall)
    npz_path = out / "cache_v6.npz"
    digest = bridge.to_previz_cache(
        final_cache, scene3, out_path=str(npz_path),
        keepouts=tuple(C.CAM_KEEPOUTS_V3),
        keepout_radius=float(C.CAM_KEEPOUT_R),
        clamp=True, clip_source="speed")
    zf = np.load(npz_path)
    assert float(zf["z"][FALL_TICK, faller_ord]) > 0.3, \
        "the composed npz lost the fall (F-TS1 regression)"
    print(f"[tsquall_bake] composed npz pin: "
          f"{digest['payload_sha256'][:16]}... "
          f"keepouts_applied={digest.get('keepouts_applied')} "
          f"z[fall]={float(zf['z'][FALL_TICK, faller_ord]):.2f}")

    # events -> sfx rows (the window-bell spine)
    bells = []
    for e in read_events(final_cache, kind=CrowdEventKind.QUEUE_ADMITTED):
        bells.append({"name": "window_bell", "frame": int(e.tick) * 2})
    for e in read_events(final_cache, kind=CrowdEventKind.QUEUE_RELEASED):
        bells.append({"name": "window_serve", "frame": int(e.tick) * 2})
    bells.sort(key=lambda b: b["frame"])

    ctx = bridge.to_previz_ctx(str(npz_path), scene3, digest=digest)
    ctx["cast"] = {
        "faller": names[faller_ord],
        "faller_ordinal": int(faller_ord),
        "fall_tick_frame": int(FALL_TICK * 2),
        "faller_graze": [gx, gy],
        "faller_speed": gsp,
        "vendors": [names[i] for i in range(6)],
        "queue": [names[i] for i in range(len(names) - 9, len(names))],
        "queue_bell_events": bells,
    }
    ctx_json = out / "cache_ctx.json"
    ctx_json.write_text(json.dumps(ctx, indent=1, default=str))
    print(f"[tsquall_bake] ctx json: {ctx_json} "
          f"({len(bells)} queue events -> bells)")
    print(f"[tsquall_bake] FINISH done in {time.time() - t0:.1f}s")


def _probe_readout(cache_path, scene2, agent_ids, visible_agent_ids,
                   read_events, CrowdEventKind):
    """The probe verdicts (REV-3 step 6): arrival, queue, events."""
    import numpy as np
    from scripts.crowd import previz_bridge as pb
    tmp_npz = Path(cache_path).parent.parent / "probe_v6.npz"
    digest = pb.to_previz_cache(
        cache_path, scene2, out_path=str(tmp_npz),
        keepouts=(), keepout_radius=1.3, clamp=True, clip_source="speed")
    z = np.load(tmp_npz)
    last = z["x"].shape[0] - 1
    in_box = int(np.sum((np.abs(z["x"][last]) < 5.0)
                        & (np.abs(z["y"][last]) < 5.0)))
    north = int(np.sum(z["y"][last] > 6.0))
    print(f"[probe] final-tick arrivals: {in_box} in the box, "
          f"{north} still north of the wall "
          f"(of {z['x'].shape[1]})")
    assert in_box >= 60, \
        f"doorway connectivity suspect: only {in_box} arrived in the box"
    admits = read_events(cache_path, kind=CrowdEventKind.QUEUE_ADMITTED)
    releases = read_events(cache_path, kind=CrowdEventKind.QUEUE_RELEASED)
    print(f"[probe] queue: {len(admits)} admitted, "
          f"{len(releases)} released")
    # the head-stuck gate, film-calibrated (the empirical semantics:
    # admission is slot-free-driven, not capacity-per-tick -- a release
    # frees the head slot for the next id). The LINE is the gate:
    # >=4 agents parked in the slot column at cache end + >=1 release.
    in_line = int(np.sum((np.abs(z["x"][last] - 6.5) < 1.2)
                         & (z["y"][last] > -5.2) & (z["y"][last] < 6.0)
                         & (np.arange(z["x"].shape[1])[None, :]
                            >= z["x"].shape[1] - 9)[0]))
    print(f"[probe] queue line at cache end: {in_line} agents in the "
          f"window column")
    assert len(releases) >= 1 and in_line >= 4, \
        f"queue gate: releases={len(releases)} line={in_line}"
    if releases:
        print(f"[probe] first release at tick {releases[0].tick} "
              f"(frame {releases[0].tick * 2})")


if __name__ == "__main__":
    main()
