# ASCII Vision Pack Protocol

`scripts/ascii_vision.py` renders a PNG into a deterministic TEXT pack a
blind agent can read: stats flags, color-class grid, luma/edge panels,
fine connected-component table at 4x internal resolution with fractional
coordinates, and 2x2 zoom tiles.

## Quick command
```bash
python3 scripts/ascii_vision.py IMG --cols 96 --components --tiles 2 --no-header
```
`--minimal` keeps the LEGEND (mandatory) and drops the header/guide.
`--auto` codifies calibrated param rules (dark renders → `--gamma 1.8
--autocontrast`; palette must match domain; fine components at 4x make
<2% objects countable).

## Scorecard (measured, 16-image battery, blind-scored)
- VLM 0.72 vs ASCII-A3 0.66 on generic aggregate — but the aggregate
  hides the story.
- **ASCII WINS**: dark/monochrome renders (+0.32), tiny <2% objects
  (+0.12), near-empty traps, street-layout montages, gradients (+0.28),
  wide renders (+0.21).
- **VLM keeps**: semantics, crowd gist, hue nuance, many-small-object grids.
- **R4 realism** (decisive test): pack-reader found planted floating actor
  at exact truth coordinates (0.748, 0.485), cited component ids/bbox,
  DECLARED occlusion blindness, fabricated nothing. VLM under same brief
  hallucinated floats on grounded actors, diagnosed sunk actor as
  floating (proposed fix sinks further), cited non-existent "component
  table X-coordinate". **Fabricated evidence is worse than blindness.**

## Doctrine
Pack-read FIRST for geometry/grounding/count/layout; VLM only for
semantics/hue/gist/aesthetics; disagreement between the two = automatic
programmatic probe (failure modes are opposite: false-accept vs
false-reject). NEVER act on bbox-overlap hints without scene-schema probes.

## Param rules
- Palette must match domain (kit scene renders → scene palette; else
  web16: +0.19 on hue tests).
- Dark renders → `--gamma 1.8 --autocontrast` (0.38→0.60) or A1 luma-dither.
- Fine components at 4x make <2% objects countable (invisible in grids,
  present in table).
- Crowd counts from components are LOWER bounds (same-class touching
  figures merge).
- `--crop`/tile tables are ALL full-frame coordinates (never
  double-transform).
- Pack faithfulness is resolution-invariant (1280x720 == 640x360 accuracy).

## Full protocol
`experiments/ascii_vision/docs/PROTOCOL.md` — full usage + calibration.
`experiments/ascii_vision/docs/RESULTS.md` — full scorecard.
