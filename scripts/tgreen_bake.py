"""tgreen_bake.py -- GREEN LIGHT's headless crowd-bake driver.

STEP 4 of the film build order (kb/tdawn_vision_film.md; venv, pure
CPython -- no Blender):

    <venv>/bin/python3 scripts/tgreen_bake.py --out /tmp/crowdcache_tgreen

The tferry_bake.py shape (sibling resolution, verbatim-129 count law,
contract-authoritative speeds, pre-bake envelope assert) with the
GREEN LIGHT deltas:

* PER-ZONE speed map (REV-3 F19): far/near1/near2/crew -- the tferry
  driver's two-key far/near map cannot express this film's three
  walking populations.
* The envelope assert is the F2 fold: chase 2.60 <= far-cap 2.62
  (the bridge applies populations[0]'s mu+3sigma to ALL agents).
* ZERO barricades pass-through: the contract carries no BARRICADES
  (the F17 fold -- the freeze line is the protection); the bridge's
  getattr default handles the absent attribute.

Arrival ledger expectation (F21): first freeze-line contacts ~f170,
the still completes through S5 (f349-444), the last arrivals ~f577.
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
LAB = HERE.parent.parent          # .../<any-lab-dir>/


def _resolve(env_key, legacy, sibling_name):
    v = os.environ.get(env_key)
    if v:
        return Path(v)
    sib = LAB / sibling_name
    if (sib / "scripts").is_dir() or (sib / "scripts" / "crowd").is_dir():
        return sib
    return Path(legacy)


CROWD_KIT_REPO = _resolve(
    "TGREEN_CROWD_KIT", "/home/z/work/blender-crowd-kit",
    "blender-crowd-kit")
PREVIZ_SCRIPTS = _resolve(
    "TGREEN_PREVIZ_SCRIPTS", "/home/z/work/blender-escape-previz/scripts",
    "blender-escape-previz") / "scripts"


def _bootstrap():
    for p in (PREVIZ_SCRIPTS, CROWD_KIT_REPO):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    bridge_py = CROWD_KIT_REPO / "scripts" / "crowd" / "previz_bridge.py"
    if not bridge_py.is_file():
        raise SystemExit(f"[tgreen_bake] no previz_bridge at {bridge_py}")
    import scripts.crowd.previz_bridge as bridge  # noqa: F401
    return bridge


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/tmp/crowdcache_tgreen")
    ap.add_argument("--count", type=int, default=129)
    ap.add_argument("--seed", type=int, default=None,
                    help="override the contract's CROWD_SEED (determinism "
                         "checks only -- the film pin is the contract's)")
    args = ap.parse_args()

    bridge = _bootstrap()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    sys.path.insert(0, str(HERE))
    import tgreen_contract as C
    assert args.count == C.N_RELEASE, (
        f"--count {args.count} != the verbatim-{C.N_RELEASE} law "
        "(the loader's honesty assert pins N_RELEASE; a different count "
        "burns the bake and dies later)")

    plan = dict(C.SPEED_PLAN)   # far / near1 / near2 / crew -- the authority
    seed = args.seed if args.seed is not None else C.CROWD_SEED

    t0 = time.time()
    scene = bridge.ingest_contract(C, count=args.count, seed=seed)
    n_agents = sum(p.count for p in scene.populations)
    print(f"[tgreen_bake] ingest OK: {len(scene.populations)} populations, "
          f"{n_agents} agents")
    assert n_agents == args.count, \
        f"count law broken: {n_agents} != {args.count} (the verbatim-129 law)"

    # --- the authored speed plan, FROM THE CONTRACT (per-zone, F19) ---
    for zone_i, pop in enumerate(scene.populations):
        if pop.id.endswith("zz_chase"):
            mu, sig = plan["crew"]
        elif zone_i == 0:
            mu, sig = plan["far"]
        elif zone_i == 1:
            mu, sig = plan["near1"]
        else:
            mu, sig = plan["near2"]
        scene.populations[scene.populations.index(pop)] = (
            dataclasses.replace(
                pop,
                distributions=dataclasses.replace(
                    pop.distributions, preferred_speed_mps=(mu, sig))))
        print(f"[tgreen_bake] {pop.id}: speed=({mu}, {sig})")

    # verify the plan landed BEFORE baking (fail loudly)
    seen = {p.id: tuple(p.distributions.preferred_speed_mps)
            for p in scene.populations}
    for key in ("far", "near1", "near2"):
        assert plan[key] in seen.values(), f"{key} plan missing: {seen}"
    assert plan["crew"] in seen.values(), f"crew plan missing: {seen}"
    # the envelope law (F2): the tail must fit populations[0]'s
    # mu+3sigma cap or the bridge SILENTLY clamps the sprint away
    far_mu, far_sig = plan["far"]
    ch_mu, ch_sig = plan["crew"]
    assert ch_mu + 3 * ch_sig <= far_mu + 3 * far_sig + 1e-9, \
        (f"envelope law broken: chase {ch_mu + 3 * ch_sig:.2f} > "
         f"cap {far_mu + 3 * far_sig:.2f} -- the bridge would clamp")
    print(f"[tgreen_bake] envelope: chase {ch_mu + 3 * ch_sig:.2f} <= "
          f"cap {far_mu + 3 * far_sig:.2f} OK")

    res = bridge.bake_previz(scene, cache_dir=str(out / "kit_bake"))
    wall = time.time() - t0
    print(f"[tgreen_bake] bake OK mode={getattr(res, 'compile_mode', '?')} "
          f"wall={wall:.1f}s")

    digest = bridge.to_previz_cache(
        res.cache_path, scene, out_path=str(out / "cache_v6.npz"),
        keepouts=tuple(C.CAM_KEEPOUTS_V3),
        keepout_radius=float(C.CAM_KEEPOUT_R),
        clamp=True,
        clip_source="speed")

    print(f"[tgreen_bake] npz pin: {digest['payload_sha256'][:16]}… "
          f"keepouts_applied={digest.get('keepouts_applied')}")

    # the loader's honesty assert reads THIS ctx (engine=kit + the
    # crowd provenance block) -- never hand-roll it (the F-TF2 law)
    ctx = bridge.to_previz_ctx(str(out / "cache_v6.npz"), scene,
                               digest=digest)
    ctx_json = out / "cache_ctx.json"
    ctx_json.write_text(json.dumps(ctx, indent=1, default=str))
    print(f"[tgreen_bake] ctx json: {ctx_json}")

    meta = {"n_agents": args.count, "wall_s": round(wall, 1),
            "speed_plan": plan, "seed": seed,
            "keepouts": len(C.CAM_KEEPOUTS_V3)}
    (out / "bake_receipt.json").write_text(json.dumps(meta, indent=1))
    print(f"[tgreen_bake] DONE {meta}")


if __name__ == "__main__":
    main()
