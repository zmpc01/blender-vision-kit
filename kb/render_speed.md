# Render Speed Reference

## Engine benchmarks (4GB RAM, no GPU, llvmpipe, warm cache)

| Engine | Resolution | Samples | ~Time/frame | Notes |
|--------|-----------|---------|-------------|-------|
| Workbench AA OFF | 960×540 | n/a | ~0.05s | vid2vid guidance default |
| Workbench AA OFF | 240×135 | n/a | ~0.2s | previz quality |
| Workbench FXAA | 960×540 | n/a | ~0.14s | human-reviewed stills |
| Workbench MSAA 8 | 960×540 | n/a | ~0.84s | final delivery (kills sub-pixel crawl) |
| EEVEE | 320×180 | 8 | ~0.5s warm | draft quality (28s cold) |
| EEVEE | 640×360 | 16 | ~2s warm | preview quality |
| Cycles | 320×180 | 8 | ~1s | draft |
| Cycles | 960×540 | 64 | ~50s | final still |

## Key findings

- **AA dominates Workbench render time**: `render_aa='8'` = 92% of wall
  time. `'OFF'` is 5-6× faster. Jaggies are fine for vid2vid guidance.
- **Cold start dominates for batch renders**: build + RB bake ~2.5 min.
  Batch re-renders into ONE contiguous range. llvmpipe default threads
  (= all cores) is optimal.
- **JPEG q85 frames ~15× smaller and 23-35ms/frame faster than PNG**.
  `--png` to force PNG.
- **Never let PNG `compression=100` leak in** (+1.1-1.9s/frame).
- **EEVEE shader compile** (~28s first frame) is one-time per container.
  `blrun.sh --warm-cache` amortizes it.
- **5.x EEVEE renders ~4-12% brighter** than 4.5 — may clip high-key
  scenes. Reduce exposure ~-0.5 EV on 5.x.

## Memory (4GB container, peaks)

| Scene | Workbench | EEVEE | Cycles |
|-------|-----------|-------|--------|
| 6 objects | 488 MB (4.2) / 516 MB (5.2) | — | 349 MB (4.2) / 365 MB (5.2) |
| 273 objects | 479 MB | **1604 MB ⚠️** | 355 MB |

**Recommendation**: Workbench for previz, Cycles for final stills (stable
~355MB regardless of object count), avoid EEVEE for 100+ objects on 4GB.

## Profiling rule
After every speedup, re-profile — the bottleneck moves. After AA was
killed, cold build + RB bake became the dominant cost.
