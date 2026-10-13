"""tferry_bake.py -- LAST FERRY's headless crowd-bake driver.

STEP 4 of the kit-mode runbook (venv, pure CPython -- no Blender):

    /home/z/.venv/bin/python3 scripts/tferry_bake.py --out /tmp/crowdcache_tferry

Chain (the tdawn_bake.py shape -- the driver owns the speed plan, the
bridge stays fork-free):

    sys.path bootstrap (crowd-kit + escape-previz scripts)
      -> bridge.ingest_contract(tferry_contract, count=129)
      -> dataclasses.replace the per-population speed distributions
         (REV-2 F1 envelope law: far (1.30,0.45) -> 2.65 global max;
         crew (2.30,0.10) -> 2.60 <= envelope -- assert BEFORE bake)
      -> bridge.bake_previz(scene, cache_dir=<out>/kit_bake)
      -> bridge.to_previz_cache(... clamp-THEN-hash, keepouts=CONTRACT ...)
      -> write <out>/cache_ctx.json (the ctx digest the loader cross-checks)

The film: a boarding CONVERGENCE (calm walk), not a flee -- the bridge's
hardcoded hero_pos (0,0) IS the gangway throat (REV-2 F2: the world moved
to the target). The crew tail is the bridge's structural 9-deep chase
population repurposed: every crew sample >= 1.8 m/s rides Sprint_Loop.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CROWD_KIT_REPO = Path("/home/z/work/blender-crowd-kit")
PREVIZ_SCRIPTS = Path("/home/z/work/blender-escape-previz/scripts")


def _bootstrap():
    for p in (PREVIZ_SCRIPTS, CROWD_KIT_REPO):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    bridge_py = CROWD_KIT_REPO / "scripts" / "crowd" / "previz_bridge.py"
    if not bridge_py.is_file():
        raise SystemExit(f"[tferry_bake] no previz_bridge at {bridge_py}")
    import scripts.crowd.previz_bridge as bridge  # noqa: F401
    return bridge


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/tmp/crowdcache_tferry")
    ap.add_argument("--count", type=int, default=129)
    args = ap.parse_args()

    out = Path(args.out)
    if out.exists() and any(out.iterdir()):
        raise SystemExit(
            f"[tferry_bake] {out} exists and is non-empty -- the "
            "fresh-dir law: rm -rf it first or pass a new --out "
            "(the native bake refuses an existing cache path)")
    out.mkdir(parents=True, exist_ok=True)

    bridge = _bootstrap()
    sys.path.insert(0, str(HERE))
    import tferry_contract as C

    plan = dict(C.SPEED_PLAN)   # far / near / crew (authored in the contract)

    t0 = time.time()
    scene = bridge.ingest_contract(C, count=args.count,
                                   seed=C.CROWD_SEED)
    print(f"[tferry_bake] ingest OK: {len(scene.populations)} populations, "
          f"{sum(p.count for p in scene.populations)} agents")

    # --- REV-2 F1: the authored speed plan (deterministic, frozen DCs) --
    # zone0 = far; zones 1+ share the near plan (the contract's mid band
    # is a DENSITY band, not a speed band); the chase tail = crew.
    zone_idx = 0
    for pop in scene.populations:
        if pop.id.endswith("zz_chase"):
            mu, sig = plan["crew"]
        else:
            mu, sig = plan["far"] if zone_idx == 0 else plan["near"]
            zone_idx += 1
        scene.populations[scene.populations.index(pop)] = (
            dataclasses.replace(
                pop,
                distributions=dataclasses.replace(
                    pop.distributions, preferred_speed_mps=(mu, sig))))
        print(f"[tferry_bake] {pop.id}: speed=({mu}, {sig})")

    # the envelope law, asserted on the AUTHORED numbers (fail loudly,
    # never bake a plan that silently clamps): tail mu+3sigma <= far
    # mu+3sigma (populations[0] == zone 0 == far).
    far_env = plan["far"][0] + 3 * plan["far"][1]
    crew_env = plan["crew"][0] + 3 * plan["crew"][1]
    assert crew_env <= far_env, (
        f"[tferry_bake] envelope violated: crew {crew_env} > far {far_env} "
        "(the bridge would clamp SILENTLY -- REV-2 F1)")
    seen = [tuple(p.distributions.preferred_speed_mps)
            for p in scene.populations]
    assert plan["crew"] in seen, f"crew plan missing: {seen}"
    assert plan["far"] in seen, f"far plan missing: {seen}"

    res = bridge.bake_previz(scene, cache_dir=str(out / "kit_bake"))
    wall = time.time() - t0
    print(f"[tferry_bake] bake OK mode={getattr(res, 'compile_mode', '?')} "
          f"wall={wall:.1f}s")

    digest = bridge.to_previz_cache(
        res.cache_path, scene, out_path=str(out / "cache_v6.npz"),
        # D6 clamp-THEN-hash lives INSIDE the bridge; the contract's
        # CAM_KEEPOUTS_V3 / CAM_KEEPOUT_R tables are the keepout
        # authority (F-TD4 law FROM tdawn: the first driver draft that
        # skipped them had agents walking through the low shot cams).
        # REV-2 F8: the crane lenses (S11/S12) need NO rows -- they fly
        # the outboard margin no agent ever enters.
        keepouts=tuple(C.CAM_KEEPOUTS_V3),
        keepout_radius=float(C.CAM_KEEPOUT_R),
        clamp=True,
        clip_source="speed")
    print(f"[tferry_bake] npz pin: {digest['payload_sha256'][:16]}… "
          f"keepouts_applied={digest.get('keepouts_applied')}")

    ctx_json = out / "cache_ctx.json"
    ctx = bridge.to_previz_ctx(str(out / "cache_v6.npz"), scene,
                               digest=digest)
    ctx_json.write_text(json.dumps(ctx, indent=1, default=str))
    print(f"[tferry_bake] ctx json: {ctx_json}")

    meta = {"n_agents": args.count, "wall_s": round(wall, 1),
            "speed_plan": plan,
            "envelope": {"far": far_env, "crew": crew_env}}
    (out / "bake_receipt.json").write_text(json.dumps(meta, indent=1))
    print(f"[tferry_bake] DONE {meta}")


if __name__ == "__main__":
    main()
