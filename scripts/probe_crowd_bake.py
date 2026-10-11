"""Probe: crowd-kit bake via the escape-previz bridge, small count.

Verifies the full STEP-1 chain works in this sandbox with OUR layout:
  bridge.ingest_contract(contract, count) -> bake_previz -> to_previz_cache
Duck-typed contract: minimal attributes the bridge consumes.
"""
import sys, os, json, time

CROWD_KIT = "/home/z/work/blender-crowd-kit"
PREVIZ = "/home/z/work/blender-escape-previz/scripts"

for p in (CROWD_KIT, PREVIZ):
    if p not in sys.path:
        sys.path.insert(0, p)

from scripts.crowd import previz_bridge  # noqa: E402

class MiniContract:
    """Duck-typed minimal contract for a bake probe.

    Mirrors the attribute surface crowd_v6.contract exposes that
    previz_bridge.ingest_contract actually reads. Rect concourse world
    40m x 24m, spawns on one side, attract at the far end.
    """
    CROWD_SEED = 777
    DT = 1.0 / 12.0
    TICK_HZ = 12.0
    N_TICKS = 121          # 10 s inclusive
    N_RELEASE = 40
    N_CAPACITY = 200
    FPS = 24
    TOTAL_FRAMES = 240
    # world bounds (x0,x1,y0,y1)
    WORLD = (-20.0, 20.0, -12.0, 12.0)
    SPAWN_RECT = (-19.0, -10.0, -11.0, 11.0)
    GOAL_RECT = (17.0, 19.0, -4.0, 4.0)
    # zones for the bridge's zone-proportional spawns
    ZONES = []
    KEEPOUTS = []
    TIER1_BUDGET = 0
    TIER_MAP_MODE = "single"


c = MiniContract()
t0 = time.time()
scene = previz_bridge.ingest_contract(c, count=c.N_RELEASE)
print("[probe] ingest OK:", type(scene).__name__)
res = previz_bridge.bake_previz(scene, cache_dir="/tmp/probe_bake/kit_bake")
print("[probe] bake OK:", getattr(res, "compile_mode", "?"),
      "wall %.1fs" % (time.time() - t0))
out = previz_bridge.to_previz_cache(
    res.cache_path, scene, out_path="/tmp/probe_bake/cache_v6.npz")
print("[probe] npz:", out)
ctx = previz_bridge.to_previz_ctx(
    "/tmp/probe_bake/cache_v6.npz", scene,
    json.load(open("/tmp/probe_bake/cache_ctx.json")) if os.path.exists(
        "/tmp/probe_bake/cache_ctx.json") else None)
print("[probe] ctx keys:", sorted(ctx.keys())[:20] if isinstance(ctx, dict) else type(ctx))
print("[probe] ALL OK")
