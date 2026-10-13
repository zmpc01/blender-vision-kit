"""tferry_bake.py -- LAST FERRY's headless crowd-bake driver.

STEP 4 of the film build order (kb/tdawn_vision_film.md; venv, pure
CPython -- no Blender):

    /home/z/.venv/bin/python3 scripts/tferry_bake.py --out /tmp/crowdcache_tferry

Chain (the tdawn_bake.py shape; the driver owns the distribution
authoring -- that is what lets the SPEED_PLAN live in the CONTRACT
without forking the bridge):

    sys.path bootstrap (crowd-kit + escape-previz scripts; sibling
      resolution -- env overrides, NOT hardcoded /home/z/work paths:
      the tferry fix for the tdawn bootstrap friction)
      -> bridge.ingest_contract(tferry_contract, count=129)
      -> dataclasses.replace the per-population speed distributions
         FROM THE CONTRACT (C.SPEED_PLAN is the single authority:
         far/near zone bands + the crew tail; the driver adds NO
         numbers of its own)
      -> bridge.bake_previz(scene, cache_dir=<out>/kit_bake)
      -> bridge.to_previz_cache(... clamp-THEN-hash ... keepouts from
         the contract, FRAMES per the F-TD13 law)
      -> write <out>/cache_ctx.json (the ctx digest the loader
         cross-checks)

The plan (D-TF1 REV-2): a BOARDING crowd, not a flee --
  far  (1.30, 0.45) -> envelope mu+3sigma = 2.65 (the GLOBAL cap)
  near (1.15, 0.35)
  crew (2.30, 0.10) -> 2.60 <= 2.65; every sample >= 1.8 so the
  9-deep tail rides Sprint_Loop (crew hustling to stations).
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

# Repo resolution: env override -> sibling of THIS repo -> the legacy
# /home/z/work convention (tdawn-era). Sibling resolution is the point:
# the tdawn driver hardcoded /home/z/work and every fresh sandbox had
# to hand-patch it (the bootstrap friction this driver retires).


def _resolve(env_key, legacy, sibling_name):
    v = os.environ.get(env_key)
    if v:
        return Path(v)
    sib = LAB / sibling_name
    if (sib / "scripts").is_dir() or (sib / "scripts" / "crowd").is_dir():
        return sib
    return Path(legacy)


CROWD_KIT_REPO = _resolve(
    "TFERRY_CROWD_KIT", "/home/z/work/blender-crowd-kit",
    "blender-crowd-kit")
PREVIZ_SCRIPTS = _resolve(
    "TFERRY_PREVIZ_SCRIPTS", "/home/z/work/blender-escape-previz/scripts",
    "blender-escape-previz") / "scripts"


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
    # the count law against the CONTRACT (ingest apportionment makes
    # n_agents == count for ANY count -- the assert must pin the film's
    # verbatim-129 identity, not the apportionment tautology)
    assert args.count == C.N_RELEASE, (
        f"--count {args.count} != the verbatim-{C.N_RELEASE} law "
        "(the loader's honesty assert pins N_RELEASE; a different count "
        "burns the bake and dies later)")

    plan = dict(C.SPEED_PLAN)          # far / near / crew -- the authority
    plan_for_pops = {"far": plan["far"], "near": plan["near"],
                     "chase": plan["crew"]}   # bridge names the tail
                                             # zombies_zz_chase

    t0 = time.time()
    scene = bridge.ingest_contract(C, count=args.count,
                                   seed=C.CROWD_SEED)
    n_agents = sum(p.count for p in scene.populations)
    print(f"[tferry_bake] ingest OK: {len(scene.populations)} populations, "
          f"{n_agents} agents")
    assert n_agents == args.count, \
        f"count law broken: {n_agents} != {args.count} (the verbatim-129 law)"

    # --- REV-2: the authored speed plan, FROM THE CONTRACT (deter-
    # ministic constants; frozen dataclasses -> dataclasses.replace) --
    zone_idx = 0
    for zone_i, pop in enumerate(scene.populations):
        if pop.id.endswith("zz_chase"):
            mu, sig = plan_for_pops["chase"]
        else:
            mu, sig = plan_for_pops["far"] if zone_i == 0 \
                else plan_for_pops["near"]
        scene.populations[scene.populations.index(pop)] = (
            dataclasses.replace(
                pop,
                distributions=dataclasses.replace(
                    pop.distributions, preferred_speed_mps=(mu, sig))))
        print(f"[tferry_bake] {pop.id}: speed=({mu}, {sig})")

    # verify the plan actually landed BEFORE baking (fail loudly --
    # never bake a plan the driver did not author)
    seen = [tuple(p.distributions.preferred_speed_mps)
            for p in scene.populations]
    assert plan_for_pops["chase"] in seen, f"crew plan missing: {seen}"
    assert plan_for_pops["far"] in seen, f"far plan missing: {seen}"
    # the envelope law (REV-2 F1): the tail must fit populations[0]'s
    # mu+3sigma cap or the bridge SILENTLY clamps the sprint away
    far_mu, far_sig = plan_for_pops["far"]
    ch_mu, ch_sig = plan_for_pops["chase"]
    assert ch_mu + 3 * ch_sig <= far_mu + 3 * far_sig + 1e-9, \
        (f"envelope law broken: crew {ch_mu + 3 * ch_sig:.2f} > "
         f"cap {far_mu + 3 * far_sig:.2f} -- the bridge would clamp")
    print(f"[tferry_bake] envelope: crew {ch_mu + 3 * ch_sig:.2f} <= "
          f"cap {far_mu + 3 * far_sig:.2f} OK")

    res = bridge.bake_previz(scene, cache_dir=str(out / "kit_bake"))
    wall = time.time() - t0
    print(f"[tferry_bake] bake OK mode={getattr(res, 'compile_mode', '?')} "
          f"wall={wall:.1f}s")

    digest = bridge.to_previz_cache(
        res.cache_path, scene, out_path=str(out / "cache_v6.npz"),
        # D6 clamp-THEN-hash lives INSIDE the bridge; the contract's
        # CAM_KEEPOUTS_V3 table is the keepout authority and is
        # FRAMES-denominated FROM BIRTH (the F-TD13 law -- the tdawn
        # rows were seconds and were silently inert)
        keepouts=tuple(C.CAM_KEEPOUTS_V3),
        keepout_radius=float(C.CAM_KEEPOUT_R),
        clamp=True,
        clip_source="speed")
    print(f"[tferry_bake] npz pin: {digest['payload_sha256'][:16]}… "
          f"keepouts_applied={digest.get('keepouts_applied')}")

    ctx = bridge.to_previz_ctx(str(out / "cache_v6.npz"), scene,
                               digest=digest)
    ctx_json = out / "cache_ctx.json"
    ctx_json.write_text(json.dumps(ctx, indent=1, default=str))
    print(f"[tferry_bake] ctx json: {ctx_json}")

    meta = {"n_agents": args.count, "wall_s": round(wall, 1),
            "speed_plan": plan, "seed": C.CROWD_SEED,
            "keepouts": len(C.CAM_KEEPOUTS_V3)}
    (out / "bake_receipt.json").write_text(json.dumps(meta, indent=1))
    print(f"[tferry_bake] DONE {meta}")


if __name__ == "__main__":
    main()
