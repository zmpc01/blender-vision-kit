"""tdawn_bake.py -- the TERMINAL DAWN headless crowd-bake driver.

STEP 1 of the kit-mode runbook (venv, pure CPython -- no Blender):

    /home/z/.venv/bin/python3 scripts/tdawn_bake.py --out /tmp/crowdcache_tdawn

Chain (my driver owns it -- that is what lets the distributions be
authored WITHOUT forking the bridge):

    sys.path bootstrap (crowd-kit + escape-previz scripts)
      -> bridge.ingest_contract(tdawn_contract, count=129)
      -> dataclasses.replace the per-population speed distributions
         (D-TD2 REV-2: frozen dataclasses; hard-coded deterministic
         constants -- an unseeded RNG would drift params_sha)
      -> bridge.bake_previz(scene, cache_dir=<out>/kit_bake)
      -> bridge.to_previz_cache(... clamp-THEN-hash ...)
      -> write <out>/cache_ctx.json (the ctx digest the loader
         cross-checks)

The distribution plan (the 1.8 m/s clip band decides walk vs sprint):
  far zone   (2.00, 1.00)  -- ~66% walk: the surge still building
  near zones (1.75, 0.75)  -- ~47% walk: jostling pack at the plaza
  chase tail (3.80, 0.40)  -- all sprint, mu+3sigma = 5.0
  max_speed envelope = populations[0].mu + 3*sigma = 5.0 >= chase 5.0
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
LAB = HERE.parent.parent


def _resolve(env_key, legacy):
    """s25: the family bootstrap law (tferry/tgreen/tsquall/tfog all
    resolve this way) — env var wins, else the LAB sibling, else the
    legacy /home/z/work path. tdawn hardcoded the legacy path and a
    fresh sandbox has no /home/z/work — the bake could never boot."""
    env = os.environ.get(env_key)
    if env and (Path(env) / "scripts" / "crowd" / "previz_bridge.py").is_file():
        return Path(env)
    sibling = LAB / legacy
    if (sibling / "scripts" / "crowd" / "previz_bridge.py").is_file():
        return sibling
    return Path("/home/z/work") / legacy


CROWD_KIT_REPO = _resolve("TDAWN_CROWD_KIT", "blender-crowd-kit")
PREVIZ_SCRIPTS = _resolve("TDAWN_PREVIZ", "blender-escape-previz") / "scripts"

# deterministic distribution plan (never unseeded -- D-TD2 REV-2)
SPEED_PLAN = {
    # population id prefix -> (mu, sigma). Zone populations are named
    # zombies_zone{i}; the chase tail is zombies_zz_chase.
    "far": (2.00, 1.00),    # populations[0] == zone 0 == the far band
    "near": (1.75, 0.75),
    "chase": (3.80, 0.40),
}


def _bootstrap():
    for p in (PREVIZ_SCRIPTS, CROWD_KIT_REPO):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    bridge_py = CROWD_KIT_REPO / "scripts" / "crowd" / "previz_bridge.py"
    if not bridge_py.is_file():
        raise SystemExit(f"[tdawn_bake] no previz_bridge at {bridge_py}")
    import scripts.crowd.previz_bridge as bridge  # noqa: F401
    return bridge


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/tmp/crowdcache_tdawn")
    ap.add_argument("--count", type=int, default=129)
    args = ap.parse_args()

    out = Path(args.out)
    if out.exists() and any(out.iterdir()):
        raise SystemExit(
            f"[tdawn_bake] {out} exists and is non-empty -- the "
            "fresh-dir law: rm -rf it first or pass a new --out "
            "(the native bake refuses an existing cache path)")
    out.mkdir(parents=True, exist_ok=True)

    bridge = _bootstrap()
    sys.path.insert(0, str(HERE))
    import tdawn_contract as C
    n_agents = int(args.count)
    if n_agents != int(C.N_RELEASE):
        raise SystemExit(
            f"[tdawn_bake] count law broken: {n_agents} != "
            f"N_RELEASE {C.N_RELEASE} (the verbatim-129 law — the s25 "
            f"family assert; tdawn was the one driver without it)")

    t0 = time.time()
    # F-TS2: chase_frame pinned EXPLICITLY — the r109 bridge default
    # flipped to "world"; a re-bake without this pin would silently
    # re-band the belt-shaped zones and move the destination (the
    # determinism trap; the film pins ARE the belt frame).
    scene = bridge.ingest_contract(C, count=args.count,
                                   seed=C.CROWD_SEED,
                                   chase_frame="belt")
    print(f"[tdawn_bake] ingest OK: {len(scene.populations)} populations, "
          f"{sum(p.count for p in scene.populations)} agents")

    # --- D-TD2: the authored speed plan (deterministic, frozen DCs) --
    zone_idx = 0
    for pop in scene.populations:
        if pop.id.endswith("zz_chase"):
            mu, sig = SPEED_PLAN["chase"]
        else:
            mu, sig = SPEED_PLAN["far"] if zone_idx == 0 \
                else SPEED_PLAN["near"]
            zone_idx += 1
        scene.populations[scene.populations.index(pop)] = (
            dataclasses.replace(
                pop,
                distributions=dataclasses.replace(
                    pop.distributions, preferred_speed_mps=(mu, sig))))
        print(f"[tdawn_bake] {pop.id}: speed=({mu}, {sig})")

    # the bake law assert needs tick_hz=12 pinned by ingest -- verify
    # the plan actually landed BEFORE baking (fail loudly, never bake
    # a plan the driver did not author)
    seen = [tuple(p.distributions.preferred_speed_mps)
            for p in scene.populations]
    assert SPEED_PLAN["chase"] in seen, f"chase plan missing: {seen}"
    assert SPEED_PLAN["far"] in seen, f"far plan missing: {seen}"

    res = bridge.bake_previz(scene, cache_dir=str(out / "kit_bake"))
    wall = time.time() - t0
    print(f"[tdawn_bake] bake OK mode={getattr(res, 'compile_mode', '?')} "
          f"wall={wall:.1f}s")

    digest = bridge.to_previz_cache(
        res.cache_path, scene, out_path=str(out / "cache_v6.npz"),
        # D6 clamp-THEN-hash lives INSIDE the bridge; the contract's
        # CAM_KEEPOUTS_V3 / CAM_KEEPOUT_R tables are the keepout
        # authority (the plugin bake.py:193-198 pattern -- MY first
        # driver draft skipped them and agents walked through the
        # low shot cams; F-TD4)
        keepouts=tuple(C.CAM_KEEPOUTS_V3),
        keepout_radius=float(C.CAM_KEEPOUT_R),
        clamp=True,
        clip_source="speed")
    print(f"[tdawn_bake] npz pin: {digest['payload_sha256'][:16]}… "
          f"keepouts_applied={digest.get('keepouts_applied')}")

    ctx_json = out / "cache_ctx.json"
    ctx = bridge.to_previz_ctx(str(out / "cache_v6.npz"), scene,
                               digest=digest)
    ctx_json.write_text(json.dumps(ctx, indent=1, default=str))
    print(f"[tdawn_bake] ctx json: {ctx_json}")

    meta = {"n_agents": args.count, "wall_s": round(wall, 1),
            "speed_plan": SPEED_PLAN}
    (out / "bake_receipt.json").write_text(json.dumps(meta, indent=1))
    print(f"[tdawn_bake] DONE {meta}")


if __name__ == "__main__":
    main()
