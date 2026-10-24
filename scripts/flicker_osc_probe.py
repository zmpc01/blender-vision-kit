"""flicker_osc_probe.py — issue #3 root-cause: classify the [C] teleport
ticks as FLAP (repeated in/out oscillation = the user's 'oscillating
faster than bees') vs SINGLE-POP (one displacement event per agent).

For every agent with teleport ticks in the cache:
  - count distinct teleport EVENTS (a contiguous run of teleport ticks
    = one event)
  - measure the displacement vector at each event
  - detect FLAP: >= 2 events whose displacement DOT PRODUCT < 0
    (opposite directions = pushed out then back in)
  - detect REPEAT-SAME: >= 2 events with dot > 0.8 * |a||b| (same dir)
Also dumps, for the worst flapper, the per-tick position deltas around
its events so the mechanism (clamp cycle) is visible.
"""
import sys
import numpy as np

path = sys.argv[1]
z = np.load(path, allow_pickle=True)
meta = z["meta"].item() if z["meta"].shape == () else {}
pos = np.stack([z["x"], z["y"], z["z"]], axis=-1).astype(np.float64)
ms_arr = z["max_speed"].astype(np.float64)

dt = np.diff(pos, axis=0)                      # (T-1, N, 3)
speed = np.linalg.norm(dt[:, :, :2], axis=2) * 12.0   # XY m/s @12Hz
# per-agent threshold (max_speed is per-agent)
msb = np.broadcast_to(ms_arr[None, :], speed.shape)
tele = speed > 2.0 * msb                       # teleport ticks
T, N = speed.shape
print(f"{path}: T={T} N={N} max_speed p50={np.median(ms_arr):.2f}")

flap_agents = 0
pop_agents = 0
events_total = 0
worst = []
for a in range(N):
    ticks = np.nonzero(tele[:, a])[0]
    if len(ticks) == 0:
        continue
    # contiguous runs = events
    events = []
    start = ticks[0]
    prev = ticks[0]
    for t in ticks[1:]:
        if t != prev + 1:
            events.append((start, prev))
            start = t
        prev = t
    events.append((start, prev))
    events_total += len(events)
    disps = [pos[e2, a, :2] - pos[e1, a, :2] for e1, e2 in events]
    flap = False
    for i in range(len(disps)):
        for j in range(i + 1, len(disps)):
            d = float(np.dot(disps[i], disps[j]))
            n = np.linalg.norm(disps[i]) * np.linalg.norm(disps[j])
            if n > 0 and d / n < -0.3:
                flap = True
    if flap:
        flap_agents += 1
    else:
        pop_agents += 1
    worst.append((len(events), flap, a, events))

worst.sort(reverse=True)
print(f"agents with teleports: {flap_agents + pop_agents}  "
      f"(FLAP={flap_agents}, SINGLE-POP={pop_agents})  "
      f"events_total={events_total}")
print("worst agents (events, flap?, idx, event-tick-ranges):")
for ev, fl, a, ranges in worst[:8]:
    print(f"  agent {a}: {ev} events flap={fl} "
          f"ranges={[(r[0], r[1]) for r in ranges[:6]]}")

# dump the worst flapper's deltas around its first events
for ev, fl, a, ranges in worst:
    if fl and ev >= 2:
        print(f"\n--- flapper agent {a}: per-tick XY deltas around events ---")
        t0 = max(0, ranges[0][0] - 4)
        t1 = min(T - 1, ranges[-1][1] + 5)
        for t in range(t0, t1):
            d = pos[t + 1, a, :2] - pos[t, a, :2]
            mark = " <== TELEPORT" if tele[t, a] else ""
            print(f"  t{t:3d}: d=({d[0]:+7.3f},{d[1]:+7.3f}) "
                  f"|d|={np.linalg.norm(d):6.3f}{mark}")
        break
