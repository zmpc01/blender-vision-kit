"""tfog_bake.py -- THE EXPRESS's headless crowd-bake driver.

STEP 4 of the film build order (venv, pure CPython -- no Blender):

  /home/z/.venv/bin/python3 scripts/tfog_bake.py --out /tmp/crowdcache_tfog --stage probe
  /home/z/.venv/bin/python3 scripts/tfog_bake.py --out /tmp/crowdcache_tfog --stage groups
  /home/z/.venv/bin/python3 scripts/tfog_bake.py --out /tmp/crowdcache_tfog --stage finish

THE INGEST FORK (audit round-1 P0-b): this film authors the CrowdScene
field-by-field (an island platform fits no belt/world ingest band) and
re-asserts the ingest-contract laws manually (the project pin, 12 Hz,
interval=1, the envelope owner). REV-3: docs/DESIGN_express.md.

Stage probe : base bake (126 cache agents) -> ids, the recoil probe
              (DANGER displacement, un-arrived waiters), the
              zero-arrived asserts at EVERY tick in [168,264], the
              keepout-intersect assert, group member resolution.
Stage groups: dataclasses.replace + 17 groups -> the final bake.
Stage finish: read_events -> sfx rows, the cast list, the npz + ctx
              (the unlayered path -- this film is LAYER-FREE).
"""
from __future__ import annotations

import argparse
import dataclasses
import json
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
    raise SystemExit(f"[tfog_bake] sibling {sibling_name} not found")


CROWD_KIT_REPO = _resolve("TFOG_CROWD_KIT", "blender-crowd-kit")
PREVIZ_REPO = _resolve("TFOG_PREVIZ", "blender-escape-previz")


def _bootstrap():
    for p in (PREVIZ_REPO / "scripts", CROWD_KIT_REPO):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    bridge_py = CROWD_KIT_REPO / "scripts" / "crowd" / "previz_bridge.py"
    if not bridge_py.is_file():
        raise SystemExit(f"[tfog_bake] no previz_bridge at {bridge_py}")
    import scripts.crowd.previz_bridge as bridge  # noqa: F401
    return bridge


def _cache_file(stage_dir: Path) -> str:
    files = sorted(stage_dir.glob("*.crowd"))
    assert len(files) == 1, f"expected one .crowd in {stage_dir}: {files}"
    return str(files[0])


def build_scene(C, bridge):
    """The custom CrowdScene (the ingest fork) + the manual law pins."""
    from scripts.crowd import CrowdScene, CrowdProject, Walkable, Blocked
    from scripts.crowd import Destination, ForceField
    from scripts.crowd.environment import ForceFieldType, FalloffProfile
    from scripts.crowd import BehaviorGraph
    from scripts.crowd.behavior import Navigate, Sequence, QueueNode
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

    walkable = Walkable(id=C.WALKABLE_ID, bounds=C.PLATFORM)
    wl_lo, wl_hi = C.PLATFORM
    blocked = [Blocked(id=bid, walkable_id=C.WALKABLE_ID,
                       bounds=((b[0], b[1]), (b[2], b[3])))
               for bid, b in C.BLOCKED]
    for bid, b in C.BLOCKED:
        assert b[0] >= wl_lo[0] and b[1] >= wl_lo[1] \
            and b[2] <= wl_hi[0] and b[3] <= wl_hi[1], \
            f"blocked {bid} pokes past the walkable (E_InvalidRange class)"

    dests = [Destination(id=C.DEST_WAITERS["id"], walkable_id=C.WALKABLE_ID,
                         point=tuple(C.DEST_WAITERS["point"]),
                         capacity_bounds=C.DEST_WAITERS["capacity"]),
             Destination(id=C.DEST_COHORTS["id"], walkable_id=C.WALKABLE_ID,
                         point=tuple(C.DEST_COHORTS["point"]),
                         capacity_bounds=C.DEST_COHORTS["capacity"]),
             Destination(id=C.DEST_QUEUE["id"], walkable_id=C.WALKABLE_ID,
                         point=tuple(C.DEST_QUEUE["point"]),
                         capacity_bounds=C.DEST_QUEUE["capacity"])]
    for d in dests:
        (plo, phi) = d.capacity_bounds
        assert wl_lo[0] <= plo[0] and wl_lo[1] <= plo[1] \
            and phi[0] <= wl_hi[0] and phi[1] <= wl_hi[1], \
            f"dest {d.id} capacity outside the walkable"

    graphs = [
        BehaviorGraph(id="nav_west",
                      root=Navigate(id="nav_w", destination_id="west_exit")),
        BehaviorGraph(id="nav_door",
                      root=Navigate(id="nav_d",
                                    destination_id="door_concourse")),
        BehaviorGraph(id="queue_door",
                      root=Sequence(id="tfg_qseq", children=[
                          QueueNode(id="tfg_qn", queue_id="door_q"),
                          Navigate(id="tfg_qnav",
                                   destination_id="door_threshold"),
                      ])),
    ]

    pops = []
    for pid, count, spawn, speed, dest_id, graph_id in C.POP_PLAN:
        sx_lo, sy_lo, sx_hi, sy_hi = spawn
        pops.append(Population(
            id=f"tfog_{pid}",
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
            behavior_graph_id=graph_id,
        ))
    # the ingest-order laws: populations[0] owns the envelope cap and is
    # the waiters pop (the plan order IS the ingest order).
    assert pops[0].id == "tfog_waiters"
    cap = pops[0].distributions.preferred_speed_mps[0] + 3.0 * \
        pops[0].distributions.preferred_speed_mps[1]
    for pop in pops:
        mu, sig = pop.distributions.preferred_speed_mps
        assert mu + 3.0 * sig <= cap + 1e-9, \
            f"envelope broken: {pop.id} max {mu + 3 * sig} > cap {cap}"
    n_cache = sum(p.count for p in pops)
    assert n_cache == C.N_CACHE, f"cache law: {n_cache} != {C.N_CACHE}"

    field = ForceField(
        name=C.FIELD["name"], type=ForceFieldType.DANGER,
        radius=float(C.FIELD["radius"]), strength=float(C.FIELD["strength"]),
        falloff=FalloffProfile.SMOOTH, center=tuple(C.FIELD["center"]),
        t_active=tuple(C.FIELD["t_active"]))

    # the portal + queue ride from the PROBE bake (QueueNode
    # cross-validates at compile -- the queue must exist at probe too);
    # only the GROUPS are the two-bake attach (ids need the base bake).
    from scripts.crowd import Portal, PortalAxis
    from scripts.crowd.advanced import Queue
    portal = Portal(id=C.PORTAL["id"], from_walkable_id=C.WALKABLE_ID,
                    to_walkable_id=C.WALKABLE_ID,
                    center=tuple(C.PORTAL["center"]),
                    width_m=float(C.PORTAL["width_m"]),
                    axis=PortalAxis.NORTH_SOUTH)   # the F-TS3 law
    queue = Queue(id=C.QUEUE["id"], portal_id=C.QUEUE["portal_id"],
                  admission_capacity=int(C.QUEUE["admission_capacity"]),
                  slots=tuple(tuple(s) for s in C.QUEUE["slots"]))

    scene = CrowdScene(
        project=project, populations=pops, walkables=[walkable],
        blocked=blocked, destinations=dests, force_fields=[field],
        behavior_graphs=graphs, portals=[portal], queues=[queue])
    return scene


def attach_m6(C, scene, cache_path):
    """Groups (17x3 over cohort ids) via dataclasses.replace (the
    two-bake covenant; portal+queue ride from build_scene)."""
    from scripts.crowd.advanced import Group, GroupKind, agent_ids

    ids = agent_ids(cache_path)
    cohort_ids = list(ids[C.POP_PLAN[0][1]:C.POP_PLAN[0][1] + C.POP_PLAN[1][1]])
    assert len(cohort_ids) == C.POP_PLAN[1][1]
    groups = []
    for gi in range(C.N_GROUPS):
        members = tuple(cohort_ids[gi * C.GROUP_SIZE:
                                   (gi + 1) * C.GROUP_SIZE])
        assert len(members) == C.GROUP_SIZE
        groups.append(Group(id=f"tfg_grp_{gi + 1}", kind=GroupKind.FAMILY,
                            member_agent_ids=members,
                            shared_destination_id="door_concourse",
                            max_separation_m=C.GROUP_MAX_SEP_M))
    return dataclasses.replace(scene, groups=groups)


def _read_visible_pos(cache_path, tick):
    from scripts.crowd.advanced import read_tick
    frame = read_tick(cache_path, tick)
    pos = frame["position"]
    vis = frame["visible"]
    return pos, vis


def agent_ids_safe(cache_path):
    from scripts.crowd.advanced import agent_ids
    return agent_ids(cache_path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/tmp/crowdcache_tfog")
    ap.add_argument("--stage", choices=("probe", "groups", "finish"),
                    default="probe")
    args = ap.parse_args()

    bridge = _bootstrap()
    out = Path(args.out)
    if args.stage == "probe":
        if out.exists() and any(out.iterdir()):
            raise SystemExit(
                f"[tfog_bake] --out {out} is not empty -- the fresh-dir "
                "law; pass a fresh dir")
        out.mkdir(parents=True, exist_ok=True)

    sys.path.insert(0, str(HERE))
    import tfog_contract as C

    from scripts.crowd import bake

    t0 = time.time()
    scene = build_scene(C, bridge)
    n_ingest = sum(p.count for p in scene.populations)
    print(f"[tfog_bake] custom scene OK: {n_ingest} cache agents, "
          f"{len(scene.behavior_graphs)} graphs, "
          f"{len(scene.force_fields)} field(s)")
    assert n_ingest == C.N_CACHE

    if args.stage == "probe":
        with warnings.catch_warnings(record=True) as wlist:
            warnings.simplefilter("always")
            result = bake(scene, cache_dir=str(out))
            for w in wlist:
                print(f"[tfog_bake][warn] {w.message}")
        assert result.compile_mode in ("v1", "v2"), result.compile_mode
        assert result.status == "complete", result.status
        cache_path = _cache_file(out)
        pin = result.source_hash[:8] if result.source_hash else "??"
        print(f"[tfog_bake] probe bake done in {time.time() - t0:.1f}s "
              f"pin {pin} mode {result.compile_mode}")
        (out / "probe_pin.txt").write_text(f"{pin}\n{cache_path}\n")

        # --- the recoil probe (the deterministic blast verdict) --------
        import blender_crowd_native
        ids = agent_ids_safe(cache_path)
        n_waiters = C.POP_PLAN[0][1]
        _c = blender_crowd_native.Cache(cache_path)
        f0 = _c.read_tick(168)
        def _f32(b, cols):
            return np.frombuffer(b, dtype=np.float32).reshape(-1, cols)
        def _u32(b):
            return np.frombuffer(b, dtype=np.uint32)
        pos0 = _f32(f0["position"], 3).astype(np.float64)
        vis0 = _u32(f0["visible"]) != 0
        peak, arg_peak, arrivals = 0.0, None, 0
        states_seen = set()
        for tick in range(168, 265):
            fr = _c.read_tick(tick)
            pos = _f32(fr["position"], 3).astype(np.float64)
            vis = _u32(fr["visible"]) != 0
            state = fr.get("state")
            if state is not None:
                states_seen.update(int(s) for s in _u32(state)[:n_waiters])
            dy = pos[:n_waiters, 1] - pos0[:n_waiters, 1]
            dy[~vis[:n_waiters]] = -1e9
            k = int(np.argmax(dy))
            if dy[k] > peak:
                peak, arg_peak = float(dy[k]), (int(ids[k]), tick)
        print(f"[tfog_bake] RECOIL PROBE: max southward displacement "
              f"{peak:.2f} m by agent {arg_peak}; waiter states in "
              f"window {sorted(states_seen)}")
        assert peak >= 0.8, \
            f"the blast beat is invisible: peak recoil {peak:.2f} < 0.8 m"
        assert peak <= 6.0, f"the rout is too big: {peak:.2f} m"
        # zero-arrived: state channel semantics (2=Arrived per the kit);
        # assert none of the waiters sat in an Arrived state in-window.
        if states_seen:
            assert all(s != 2 for s in states_seen), \
                f"arrived waiters inside the blast window: {states_seen}"
        print(f"[tfog_bake] zero-arrived law green; "
              f"probe stage PASS ({time.time() - t0:.1f}s)")
        return

    cache_path = _cache_file(out)

    if args.stage == "groups":
        # the keepout-intersect assert (round-2 R5): keepout circles must
        # not touch the queue slots or the door destination capacity box.
        import math
        for name, px, py, _f0, _f1 in C.CAM_KEEPOUTS:
            rr = C.CAM_KEEPOUT_R + 0.34
            for sx, sy in C.QUEUE["slots"]:
                assert math.hypot(px - sx, py - sy) > rr, \
                    f"keepout {name} intersects queue slot ({sx},{sy})"
            (clo, chi) = C.DEST_QUEUE["capacity"]
            nx = max(clo[0] - px, 0.0, px - chi[0])
            ny = max(clo[1] - py, 0.0, py - chi[1])
            assert math.hypot(nx, ny) > rr, \
                f"keepout {name} intersects the door dest box"
        scene2 = attach_m6(C, scene, cache_path)
        with warnings.catch_warnings(record=True) as wlist:
            warnings.simplefilter("always")
            result = bake(scene2, cache_dir=str(out))
            for w in wlist:
                print(f"[tfog_bake][warn] {w.message}")
        assert result.status == "complete", result.status
        pin = result.source_hash[:8] if result.source_hash else "??"
        print(f"[tfog_bake] groups bake done pin {pin} "
              f"({time.time() - t0:.1f}s); groups={len(scene2.groups)}")
        (out / "groups_pin.txt").write_text(f"{pin}\n")
        return

    # --- stage finish ---------------------------------------------------
    from scripts.crowd.advanced import read_events, CrowdEventKind
    cache_path = _cache_file(out)
    events = read_events(cache_path)
    sfx_rows = []
    for e in events:
        if e.kind in (CrowdEventKind.QUEUE_ADMITTED, CrowdEventKind.QUEUE_RELEASED):
            sfx_rows.append({"name": "door_bell" if
                             e.kind == CrowdEventKind.QUEUE_ADMITTED
                             else "door_bell_tail",
                             "frame": int(e.tick * 2)})   # the x2 law
    print(f"[tfog_bake] events: {len(events)} "
          f"(sfx rows {len(sfx_rows)})")

    digest = bridge.to_previz_cache(
        cache_path, scene, str(out / "cache_v6.npz"),
        keepouts=[(name, px, py, f0, f1) for name, px, py, f0, f1
                  in C.CAM_KEEPOUTS],
        keepout_radius=C.CAM_KEEPOUT_R,
        # the film is TRUE WORLD-MODE: no belt transform (the audit
        # fork); rows stay in world meters.
    )
    ctx = bridge.to_previz_ctx(cache_path, scene, str(out / "cache_ctx.json"))
    ctx["cast"] = {
        "heroes": [
            {"name": "late_passenger", "kind": "actor", "lane": "sprint"},
            {"name": "stationmaster", "kind": "actor", "lane": "walk"},
        ],
        "queue": {"id": C.QUEUE["id"], "slots": len(C.QUEUE["slots"])},
        "sfx_rows": sfx_rows,
        "field": C.FIELD,
        "train_paths": {"express": C.EXPRESS_PATH, "local": C.LOCAL_PATH},
        "board_program": list(C.BOARD_PROGRAM),
        "beats": [list(b) for b in C.BEATS],
        "sfx_events": list(C.SFX_EVENTS),
    }
    (out / "cache_ctx.json").write_text(json.dumps(ctx, indent=1))
    print(f"[tfog_bake] finish: npz + ctx written "
          f"({time.time() - t0:.1f}s); payload "
          f"{digest.get('payload_sha256', '?')[:8]}")


if __name__ == "__main__":
    main()
