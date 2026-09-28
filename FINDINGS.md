
# Blender in Headless Container — Research Findings

## TL;DR

**Yes — Blender 4.2.9 LTS runs reliably in this container, fully headless, with both Cycles (CPU) and EEVEE_NEXT (with Xvfb).** The build-render-analyze-iterate loop works end-to-end: an agent can create geometry, animate it, render frames, and use a VLM to critique and iterate.

## What Was Set Up

| Component | Source | Location |
|-----------|--------|----------|
| Blender 4.2.9 LTS | Portable tarball from blender.org | `/home/z/my-project/tools/blender/` (symlink) |
| libEGL.so.1 (for EEVEE_NEXT) | Extracted from `libegl1` + `libegl-mesa0` .deb (no root needed) | `/home/z/my-project/tools/local-libs/usr/lib/x86_64-linux-gnu/` |
| Xvfb | Already installed | `/usr/bin/Xvfb` |
| Wrapper script | Custom | `/home/z/my-project/scripts/blrun.sh` |
| Scene scripts | Custom | `/home/z/my-project/scripts/scene_basic.py`, `scene_v2.py`, `save_blend.py` |
| Rendered outputs | — | `/home/z/my-project/download/` |

## Performance Benchmarks (4GB RAM, no GPU)

| Engine | Resolution | Samples | Frames | Time | Notes |
|--------|-----------|---------|--------|------|-------|
| Cycles | 480x270 | 16 | 4 | ~12s | ~3s/frame, ~30MB peak RAM |
| Cycles | 320x180 | 8 | 2 | ~2s | <1s/frame |
| Cycles | 960x540 | 64 | 1 | ~52s | High quality still, ~90MB peak |
| EEVEE_NEXT | 480x270 | 16 | 4 | ~36s | 28s first frame (shader compile cache miss), 2.5s subsequent |
| EEVEE_NEXT | 640x360 | 16 | 1 | ~11s | First-frame cost dominates |
| EEVEE_NEXT | 640x360 | 16 | 24 | ~60s | After shader cache warm, ~2s/frame |

**Recommendation:**
- **Iteration / previz**: EEVEE_NEXT at 640x360 / 16 samples. ~2s/frame after warmup.
- **Final stills**: Cycles at 960x540 / 64+ samples with denoising. ~1min/frame.
- **Final animation**: Cycles at 480x270 / 32 samples is feasible for short clips.

## How To Use

### One-liner render

```bash
/home/z/my-project/scripts/blrun.sh --background --python my_script.py -- \
    --output /home/z/my-project/output/my_scene \
    --engine BLENDER_EEVEE_NEXT \
    --frames 24 --samples 16 --w 640 --h 360
```

The `blrun.sh` wrapper:
1. Starts Xvfb on `:99` (if not already running)
2. Adds `local-libs` to `LD_LIBRARY_PATH` (so libEGL.so.1 is found)
3. Runs Blender with the given args
4. Kills Xvfb on exit (unless `KEEP_XVFB=1`)

For Cycles-only renders, Xvfb is not strictly required but the wrapper still starts it (cheap).

### Python API pattern

Inside a Blender script (`--background --python foo.py`), use `bpy` like normal:

```python
import bpy, sys, argparse

# Args after `--` on CLI are passed to the script
argv = sys.argv
if "--" in argv: argv = argv[argv.index("--")+1:]
args = argparse.ArgumentParser().parse_args(argv)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_cube_add(size=1.2, location=(0, 0, 0.6))
# ... etc.
bpy.context.scene.render.engine = 'BLENDER_EEVEE_NEXT'
bpy.context.scene.render.filepath = '/path/to/frame_####.png'
bpy.ops.render.render(animation=True)
```

## Build → Render → VLM → Iterate Loop (Validated)

End-to-end pattern proven in this session:

1. **Build v1** (`scene_basic.py`): cube, sphere, plane, sun + area light, simple camera.
2. **Render** with Cycles, 4 frames, 480x270.
3. **VLM analyze** via `z-ai vision -p "..." -i frame.png`:
   - Identified: cube floating (z=0.8 but bottom at z=0.2), flat lighting, sparse framing.
4. **Build v2** (`scene_v2.py`) addressing VLM feedback:
   - Cube rests on plane (`z = size/2`)
   - Sky texture for HDRI-like ambient
   - Added torus for compositional balance
   - Tighter camera framing
5. **Re-render + VLM re-analyze**: VLM confirmed all three v1 issues fixed, then surfaced new ones (sphere-cube visual overlap at apex, cube near top edge of frame).
6. **Render animation** (24 frames EEVEE_NEXT) → encode to MP4 via ffmpeg.
7. **Save .blend** file for GUI inspection.

VLM analysis quality was high — it caught geometric issues (floating cube), lighting issues (flat shading), and compositional issues (sparse framing). Cost per analysis: a few seconds, ~600 tokens.

## MCP Server Option (Assessed, Not Used)

The `blender-mcp` package (v1.9.1 on PyPI) exists and exposes Blender as an MCP server. **For this containerized agent use case, I recommend direct `bpy` scripting instead.** Reasons:

| | Direct `bpy` scripting | blender-mcp |
|---|---|---|
| Latency | Direct subprocess call | Socket round-trip per operation |
| State | Each run is fresh, reproducible | Persistent Blender session (stateful) |
| Setup | Just run `blender --python` | Install addon in Blender, run server, configure MCP client |
| Agent control | Full Python, any logic | Restricted to MCP tool surface |
| Best for | Batch generation, scripts, CI | Natural-language driving from Claude Desktop |

If you want the MCP path anyway: install `blender-mcp` (`pip install --break-system-packages blender-mcp`), start Blender with the addon loaded, then point an MCP client at the socket. For an agent that already writes Python, direct `bpy` is strictly more capable.

## Limitations / Caveats

- **RAM**: 4GB total. Cycles peaks around 90MB for our test scenes (fine). Larger scenes with high-res textures or many objects will need careful memory management.
- **No GPU**: All rendering is CPU. A 1080p Cycles render at 256 samples would take many minutes per frame. Stick to ≤720p for animation.
- **libEGL.so.1 not installed system-wide**: We extracted it locally from .deb files. The wrapper handles `LD_LIBRARY_PATH`.
- **First EEVEE_NEXT render is slow (~28s)** due to shader compilation cache miss. Subsequent runs are much faster because the cache persists in `~/.cache/blender/`.
- **Xvfb lock files** at `/tmp/.X*-lock` can leak if a previous run was killed. The wrapper tries to clean these; if Xvfb refuses to start, `pkill -9 Xvfb && rm -f /tmp/.X*-lock /tmp/.X11-unix/X*`.
- **No audio** support tested (not relevant for previz/animation visuals).

## File Layout

```
/home/z/my-project/
├── tools/
│   ├── blender-4.2.9-linux-x64/    # extracted Blender
│   ├── blender -> blender-4.2.9-linux-x64/   # symlink
│   ├── local-libs/usr/lib/x86_64-linux-gnu/  # libEGL.so.1 etc.
│   └── *.deb                       # original deb files (kept for reference)
├── scripts/
│   ├── blrun.sh                    # Xvfb + LD_LIBRARY_PATH wrapper
│   ├── scene_basic.py              # v1 scene (cube+sphere, flat lighting)
│   ├── scene_v2.py                 # v2 scene (fixed per VLM feedback)
│   └── save_blend.py               # saves .blend file + Cycles still
├── output/                         # intermediate renders
└── download/                       # user-facing deliverables
    ├── scene_v2.blend              # open in Blender GUI
    ├── scene_v2_anim.mp4           # 24-frame animation @ 12fps
    ├── scene_v2_still_frame12.png  # high-quality Cycles still
    ├── preview_frame_0001.png      # v1 first frame (for comparison)
    └── preview_v2_frame1.png       # v2 first frame
```

## Next Steps (Suggested)

1. **Iterate v3** based on v2 VLM feedback (fix sphere-cube overlap by widening sphere drift path; lower cube bounce height; add a backdrop curve for studio look).
2. **Add a text-to-scene helper** that takes a natural-language scene description and emits a Blender script. Pattern: agent writes the script → `blrun.sh` renders → VLM critiques → agent edits.
3. **Build a small library** of reusable scene-creation helpers (materials, lights, cameras, animation primitives) to make subsequent scripts shorter.
4. **Try a longer animation** (e.g. 120 frames) to test render-time scaling and produce a more complete previz clip.
5. **Try Cycles GPU** if a GPU node is ever available — would unlock much higher quality at acceptable speed.

## Session findings: escape-previz v2 (articulated chars, physics, TTS)

### VLM-as-eye: the image quality gates the feedback quality
- The VLM (z-ai vision) hallucinated confident pose verdicts on
  nearly-empty, low-contrast renders — a full afternoon of pose
  "iterations" were against garbage images. **Pixel-validate the image
  first** (subject coverage, contrast); then VLM.
- Sycophancy is real: naming "the BLUE man" in a prompt gets blue
  confirmed on gray figures. Readback prompts (colors as output) are
  the honest ones.
- Macro crops beat wide lineups; hide the other subjects (mesh-level
  hide_render — it does NOT inherit from parent empties).
- Single stills cannot prove motion. Probe bone oscillation across
  frames or use the contact sheet.

### Skinned characters (the rigging trap field)
- Stock glTF rigs ship broken (CesiumMan R-shin on L bones). Proximity
  re-skin (host-side, deterministic) fixed it in one pass.
- Bind pose ≠ standing pose; the ACTION carries the pose. Pose via
  quaternion composition; derive axes empirically (small-delta probe)
  and read results in side view.
- glTF root basis carries the Y-up→Z-up rotation; never identity() it.
- NLA strips: NlaStrips.new(name, start, action); fcurve CYCLES
  modifiers DO apply inside strips (verified); 4.4+ auto-stashes
  previous actions into muted tracks.

### Rigid bodies headless
- rb "Animated" = rb.kinematic (4.5). Animated→dynamic switches need
  inherited velocity: end the kinematic keys with a 3-frame launch.
- ptcache.bake_all(bake=True) works in background; PointCache.bake()
  is gone; particles evaluate at render time.

### Long renders
- Double-fork (reparent to PID 1) is the ONLY way renders survive
  toolcall kills. render_daemon.py + heartbeat JSON is the pattern.
- 640×360/16-sample EEVEE on this CPU with skinned meshes: ~20 s/frame
  (vs 2 s/frame for simple previz geometry). Budget accordingly; ship
  the draft, upgrade later.

### Timeline engineering
- Adding a story phase (parked→drive) shifted every event out of its
  shot window. Keep one t→frame map; assert events INSIDE their shot
  windows (impact in the climax shot, lunge in its closeup).

## Session 8 — the honest-verification + viewport pivot

### The rigged-humanoid verdict (the user called it)
Independent final-render verification (native pixel reads + neutral VLM)
confirmed the user's suspicion: the v2 rig renders were broken —
S2 hero: all three humanoids "limbs detached and floating", red figure
"severely distorted"; S4 side seats: VLM detected NO humans at all; S7:
gunner "head bent near 90 degrees, intersecting the seat". The previous
session's "verified runners" claim was sunk-cost rationalization from
low-res thumbnails + sycophancy-primed prompts. Decisive protocol fix:
**the final-render gate uses the exact frames the deliverable ships,
read natively first (ascii_read.py pixel grids), then neutral-prompt
VLM (colors as OUTPUT), never prompt vocabulary that names what should
be there.**

### The shared root cause nobody caught: seat constants
The v2 BOARD seat z-locals (-0.10/-0.04/0.06) put ANY feet-at-origin
actor ~0.7 m UNDER the seats (v1-verified anchors: feet 0.70/0.72,
pan top 1.12). Part of the "distorted rigs intersecting seats" was
geometry buried in the jeep, not rig failure. The fresh-context design
review (sub-agent) caught this from code before a single render —
see AGENTS.md #36: design reviews pay for themselves.

### Why capsules won
- 33 objects, zero armatures/NLA/actions, direct LINEAR fcurves.
- Module + integration audits CLEAN on first run; truth renders (the
  exact killer frames) passed native + VLM on first attempt.
- The FK chain (thigh→shin parenting) delivers articulated running
  (khaki legs visibly scissoring under each torso) at zero rig risk.
- Fix cost when something is off: one constant, one re-run (~40 s),
  vs the rig path's afternoon-per-bug.

### Render economics, corrected
- EEVEE 640×360/16s with skinned meshes: ~20 s/frame → 3.5 h for 720
  frames. Workbench FLAT 960×540: **~0.6 s/frame → ~8 min** (35× faster,
  larger resolution, and *more appropriate* for the deliverable).
- Previz = vid2vid guidance: pure albedo, no lighting signature.
  The 3.5 h EEVEE render was not just slow, it was **wrong** — baked
  dusk/fog/toon grading is style guidance a vid2vid model copies.
- Workbench MATERIAL color = mat.diffuse_color (not Principled Base
  Color) — make_material now sets both (this is why earlier workbench
  renders could look colorless/gray).
- Workbench background: follows scene.world; headless with no world =
  black. The viewport preset installs a flat neutral-gray world.

### Process
- GIT IS THE DISK (again): this session started in a fresh sandbox —
  everything survived because it was pushed; uncommitted capsule work
  from the aborted session did NOT survive and had to be rebuilt.
  Push on every micro step, not at milestones.
- The tight action-verify loop's cheapest instrument is the
  orchestrator's own pixel-grid read (ascii_read.py) — free, no
  sycophancy, no latency; VLM is the second opinion, programmatic
  probes are the ground truth.

# Session 9 — speed, blank shots, per-shot pipeline

## The blank-shot bug that wasn't a camera bug
S1 (aerial) and S10 (crane) rendered pure background for their whole
shots. The camera probes ray-cast into `Street.Mist` — a volume-only
material (Principled Volume, no surface BSDF). Workbench renders
volumes as OPAQUE SHELLS: from inside the box (all tracking shots) it
reads invisible, from above/outside (the crane shots) it blanks the
frame. The old EEVEE renders showed it as proper fog — engine change,
not scene change. Fix: `kit_atmo` tag + preset hide. Meta-lesson: when
an engine swap changes behavior, suspect material classes, not camera
work; and "renders fine at f20, blank at f615" = camera-position-
relative geometry (inside vs outside a volume), not frame-dependent
corruption.

## The 92% nobody profiles
The viewport preset rendered at ~0.5 s/frame and everyone was happy
(3.5 h → 6 min). One benchmark pass found `render_aa` default '8'
re-rasterizes per sample — AA OFF = 46 ms/frame → 720 frames in 33 s.
The lesson generalizes: after a 35× win, profile AGAIN; the next
bottleneck (now the 2.5-min cold build + RB bake) is only visible
after the first one dies. llvmpipe threads default (= all cores) beat
both LP_NUM_THREADS=1 (30% slower) and =4 (8% slower) — don't tune
what you didn't measure.

## VLM composition critique flip-flops — treat as advisory
Three review rounds on the same cameras: S4 passed r1, failed r2
("near-frontal angle" contradicting r1's "too 3/4-rear"), S5
failed r2 passed r3, S3 failed on "gunner is yellow instead of
AMBER" (naming pedantry). Meanwhile the extraction bug (reading
top-level keys instead of `parsed.score`) made round 1 read "all
pass" — a false-positive gate. Two lessons: (a) wire the gate to the
actual schema, test it on a known-bad input; (b) the agent's own
pixel reads + story intent outrank VLM framing opinions — the ledger
records overrides with reasons (`freeze --force`).

## Provenance is a correctness property
Code review 16-b PROVED the published mp4 mixed render generations
(stale scratch frames distributed as fresh) and that freeze-time hash
recomputation masked review/render drift. Stateful pipelines need:
scratch wiped per launch; daemon clears its own output dir; freeze
copies the REVIEW's hashes; counts only the rendered range;
heartbeat 'starting' written by the parent pre-fork. "It looks done"
is not provenance.

## Near-field control is cinematography
Belt scenery scrolls objects THROUGH the camera. The VLM kept flagging
"foreground zombie completely obscures" — the fix is a per-frame
distance scan keyframing `hide_render` at transitions (crowd+chase+barr
only; KD falls and subjects stay visible), with shot-specific keep-
bands (a bumper-POV shot KEEPS near zombies — that's the content).
Booleans need f=1 anchors + CONSTANT interpolation or zombies vanish
from frame 1 (BEZIER extrapolation bug, found in review).
## Session 9b — ASCII vision vs VLM (the visionless-eye experiment; parallel with session 9)

### What was built
- **Pack generator** `scripts/ascii_vision.py`: deterministic PNG→text
  pack (stats flags, color-class grid, luma/edge panels, FINE
  connected-component table at 4x internal res with fractional
  coordinates, 2x2 zoom tiles, dither/gamma/autocontrast, scene +
  web16 palettes); supersedes `ascii_read.py` (backward compat).
- **Corpus + harness** `experiments/ascii_vision/`: 10 synthetic images
  (exact construction truth) + 6 blender renders (projection truth);
  battery.py T1-T9 question families, blind scoring, arms V (z-ai
  vision) / A1 luma-fs / A2 color / A3 color+components+tiles.

### Audit findings worth remembering (each would have silently poisoned results)
- **Inverted luma legend**: doc said light→dark, code dark→light — a
  blind reader misjudges every dark render.
- **Tile-coordinate remap**: tile component tables were tile-local but
  labeled "(full frame)"; remapped to full-frame coords, verified tile
  B (0.747,0.521) == overview blue2 (0.748,0.483).
- **Tiny-object dilution**: <2%-height objects fall below the 0.15
  sat-thresh at overview AND tile scale; the fine 4x table is the only
  place they exist (grids alone make S4/C6 structurally unanswerable).

### Measured results (final scorecard: `experiments/ascii_vision/docs/RESULTS.md`)
- Aggregate per-question credit: **A1 0.56 · A2 0.62 · A3 0.66 ·
  V 0.72** — the VLM wins the generic battery, but ASCII wins the
  QA-relevant regimes: dark/monochrome renders **+0.32** (VLM 0.29
  there), tiny <2% objects **+0.12** (A3 0.90), near-empty trap +0.08,
  street layout +0.08, gradient +0.28 (R1 battery v1 only; shrank to +0.07 under v2), real wide render +0.08 (R1: +0.21). VLM
  keeps gestalt (0.91), crowd semantics (0.81), web16 hue nuance
  (0.83), many-object grids (0.89).
- Param rules: palette must match domain vocab (scene→web16 on S8:
  +0.19); dark renders `--gamma 1.8 --autocontrast` (0.38→0.60) or A1
  luma-dither; crowd counts are LOWER bounds (same-class merges).

### R4 realism — the fabrication contrast
Same shot-QA brief on C4_planted (transcripts:
`experiments/ascii_vision/docs/R4_REALISM.md`): the pack-only arm
REJECTED, found the planted floating actor at its exact truth
coordinates (0.748, 0.485), cited component ids/bbox, ZERO fabricated
objects, and declared its occlusion blindness honestly. The VLM arm
hallucinated floats on grounded actors, diagnosed the SUNK gunner as
"floating" (its fix sinks it further), and cited "the component
table's X-coordinate" — nonexistent in a VLM prompt. Bias profiles are
opposite (false-accept vs strict-reject): run both when stakes are
high; disagreement = the probe signal.

### Threats + doctrine
- Honest threats: previz-domain corpus favors packs; chat-vs-vision
  model identity is confounded with arm; T1-T9 measure Q&A, not all
  visual work (R4 n=2 shots); blender truth is projection-bbox based
  (occlusion lenient); 429-retries may have depressed some V cells.
- Doctrine (AGENTS.md gotcha 50, supersedes "VLM is your only eye"):
  pack first for geometry/grounding/count/layout, VLM for
  semantics/hue/gist, disagreement = programmatic probe, bbox-overlap
  hints never acted on without schema probes. Protocol:
  `experiments/ascii_vision/docs/PROTOCOL.md`.
## Session 11 — white-world recut (user-feedback-driven)

### The regression was measurable before it was fixable
The v2.2 "cinematography went down" complaint mapped to hard numbers:
ascii_vision on the v2.2 S1 frame: luma stdev 0.05, chromatic 2.5%,
96.8% single-class — a wash. The praised v2.0 EEVEE frame: stdev 0.13,
chromatic 27%. The fix (white world + 3 subject colors + STUDIO grey
shading) moved every v3 shot to stdev 0.07-0.16 with clean class
separation. **Frame statistics are a regression gate** — "looks flat"
is a number, not an opinion.

### Color discipline is an attention API
The user's directive (white environment, one color per subject, colors
only for distinguished subjects) is a coherent design for BOTH
consumers: the agent (verification classes) and the vid2vid model
(attention map). Executing it required touching 6 files — the palette
is scattered (escape_lib PALETTE + hardcoded colors in assets_street
marks/debris/ground + capsule SHIRT/PANTS/SKIN + scene FX quads +
light BASE colors which workbench reads instead of emissions). The
completionist color table in DESIGN_v3 §1 is the checklist pattern.

### STUDIO vs FLAT: settled by measurement
Identical subject chroma (25.9% both modes — studio does not
desaturate), stdev 0.05→0.09-0.16, VLM read 2 figures vs 1. The
"greyscale if you need shade" directive IS workbench STUDIO with
shadows+cavity off. Speed unchanged (AA still off).

### Camera restoration is a two-layer problem
Restoring the praised v2.0 camera TABLE without re-deriving the
camera ANIMATION (crane windows, dolly loops, aim tracks) leaves
cranes firing in wrong shots — invisible to content gates, caught
only by a camera-key-coverage audit (new in master_audit). And the
praised S1 broke anyway: the longer 45s runway spread
trio/jeep/horde beyond any 28mm frame — fixed by 24mm + higher start
+ aim pan converging on the runners (2 render iterations + FOV
pencil-math). Lesson: pencil the framing math BEFORE the 7-minute
render; a timing change invalidates every camera that frames the
changed span.

### The gates earned their keep (again)
The new phase-A follower gate caught the RB chase pack running
through the parked jeep (uncapped follow formula, 17 m overshoot);
the module audit caught the mill-bob phase=0 overwrite of the f1
ground key (latent for sessions, exposed by new crowd RNG draws).
Both were P0-class silent corruptions. Gate-first design pays.

### UAL validated, capsules stay (this round)
Quaternius Universal Animation Library: vendored, gauntlet PASS
(in-place drift 0.000 m, recolor works, no NLA), A/B readability WIN
(VLM: "running, leaning forward" vs capsule "walking"). The hero-actor
swap is its own session of work (sprint→sit transitions, hop
retiming, lunge re-choreography); the crowd stays capsule-instanced
(120 zombies at ~0 raster cost). Decision recorded, not deferred
indefinitely.

### Dialog timing: end-to-onset, not onset-to-onset
The v2 dialog table had an 0.8 s L3/L4 OVERLAP that "verified"
clearances missed — because only onset-to-onset gaps were checked.
L3 had to be REGENERATED at speed 1.5 (2.56 s → 1.84 s) to fit the
boarding window. Rule: check consecutive pairs as
onset[i+1] − (onset[i] + duration[i]).

# Session 12b — ASCII vision R5: usability hardening + production readiness (parallel with session 12)

The session-9b ASCII-vision toolchain got the session-11b treatment:
design-audit gate before implementation, two rounds of fresh visionless
consumers, two adversarial production audits. Meta lessons that generalize:

### Consumers catch what authors cannot see
U1's CLI-flow consumer found in minutes what the author missed across two
sessions: `--crop` component tables printed crop-LOCAL fractions under a
"fracs are FULL-FRAME" header (the fx-remap built for tiles was never wired
for crops), and the `edge` column fired on crop edges — a text-only reader
trusting either would FABRICATE frame-cuts. The generator bug survived
because pack_accuracy only ever validated the default full-frame path.
Rule: usability-test the flag COMBINATIONS, not just the happy path.

### Display layers lie — verify bytes before believing a "bug"
A "[mostly-uniform ...]" flag appeared in tool output as "ostly-uniform";
the investigation nearly shipped a phantom-bug fix. Python's own repr +
equality check proved the string was correct — the output transport was
eating "[m"-style sequences. When text looks corrupted, compare with
`repr()`/`od` before editing the generator.

### Auto-selection: rules from measurements, thresholds from data, guard from perturbation
The auto rules are codified R1-R3 lessons, but the MEANINGFUL thresholds
(dark_frac over mean for the dark rule; strong-edge FRACTION over
mean-sobel for the gradient rule — C2 and S6 are indistinguishable by
mean-sobel) came from calibrating on the corpus, and the audit's demanded
perturbation checks (±20% brightness, 2x downscale) caught a knife-edge
mean threshold before it shipped. Stats must sample a canonical grid:
edge/dark fractions drift with display resolution, so auto must
characterize the image, not the requested --cols.

### Validate the validator
The D2 readback columns silently broke pack_accuracy's $-anchored row
regex (0 rows parsed → detection would score 0% with no error). Fixed in
the same commit with a LOUD guard (matched header + zero rows + no
empty-note → raise). A scorer that fails silently poisons every downstream
number — parser drift deserves a crash, not a zero.

### Reports must not fabricate denominators
The HD probe exposed pack_accuracy printing "13/16" for a 10-image run
(hardcoded ×16). Parameterized report writers + a data-driven narrative
gate now make partial-corpus runs honest. Any report that hardcodes a
corpus size will eventually lie.

### Usability scores move: 8/7 (U1) → 9/9 (U2) with zero new features
Every U1 fix was doc/wording/flag-surface work: AGENTS fast-path pointer,
stale PROTOCOL sections, a --minimal shorthand, auto=none echo, tile-flag
rewording, blend-fragment reading rules. No new capability. The gap
between 7/10 and 9/10 was almost entirely TEXT.

## Session 12 — v3.2: nine points, nine RCAs, nine gates

- The "z-flickering EVERYWHERE" complaint decomposed into TWO
  classes with different fixes: true coplanar face pairs (bumper,
  bed-rear, crash stack, grid crossings -- geometry fixes) and AA-off
  temporal aliasing (FXAA on delivery). The z-buffer hypothesis was
  wrong (clip 0.1/100 fine) -- pixel + code RCA beats plausible
  theory.
- "Bodies cropped all the time" became a deterministic gate: NDC
  subject projection + auto-fit repair ladder (lens -> aim assist).
  The gate found 331 issues in my first pass, converged to 0 --
  including catching my own mis-aimed S6b (28 deg below the subject,
  unrecoverable by any lens).
- Crowd 1/10 -> sim: the ONE formula that mattered is the boarding
  target (parked jeep after t5.5); before that fix, chasers ran
  THROUGH the jeep chasing a phantom target 12 m past it.
- The workbench FX ceiling: white caps ~0.8 under studio, so the
  splash reads by SIZE+STROBE (x2 scale: 4k->14k bright px beat).
- Delivery discipline: gitignored download/ silently ate the v3
  MP4s; /home/sync saved them by luck. Force-add is now SOP.
- blender_kit metadata (user workstream) had missing math/datetime
  imports -- crashed ONLY at render stage (dry-runs never exercise
  it); fixed + lesson: every gate path must be exercised at least
  once by the real pipeline.

## Session 16 — the v3.3 invisible release (draft ≠ published)

**What the user saw:** the GitHub releases page showing only v3.2,
8h stale, and a pointed "where is your v3.3?" — while every internal
record (worklog, HANDOFF, commit message) claimed the release was
live with 7 assets.

**What was actually true:** tag v3.3 and all commits WERE on GitHub
(`ls-remote` proved it); all 7 release assets WERE uploaded; but the
release object sat in DRAFT state — the final `PATCH {"draft": false}`
never ran before the session died. Drafts don't appear in the main
releases list, so anyone checking the page saw v3.2 as latest.

**Why the worklog was wrong:** the upload loop's success was taken
as the whole publish's success. The verify step checked what was
easy (files exist, upload exit codes) instead of what mattered
(is the release VISIBLE to a reader?). Classic half-verified state.

**Why the anonymous 404 didn't clear it up during recovery:** the
repo is private — anonymous curl 404s even for LIVE releases, so
"404 on the release URL" carried zero information until the token
was attached. Also the GitLab mirror had no tags at all (main only)
— `git push gitlab main` doesn't move tags; needed `--tags`.

**Fixes applied:** release published via API (draft: false, verified
with asset count); GitLab tags pushed (after WAF retries); SOP Job 11
gained step 5 — "upload AND publish are two calls, verify
`draft: false` via API before the worklog says live"; AGENTS.md
gotcha #62. The meta-lesson is the same as the MP4-never-in-git
one: the delivery step's VERIFY must run against the reader's view
of the world (public page / authenticated API), not the writer's.

## Session 16b — v3.4: three delivery escapes, closed by measurement

**User round-4:** "camera completely blocked" (3 events), "deco +
physics boxes move WITH the jeep", "pedestrian street still flickers".

**The RCA discipline paid off again** -- and the adversarial review
round caught the author's own errors twice: the z-fight RCA was
REJECTED by reviewer-c (depth math: clip 0.1/1000 + g/sin(theta)
amplification means 4mm gaps are 11-685x safe -- the real pedestrian
artifact was a 15cm trench + a 4cm Delta-0.37 curb stripe temporal-
aliasing); the barricade-chunk "misplacement" finding was false
(origin-vs-geometry read) while the REAL defect (silent empty
loose_chunks ctx key -> vacuous gates -> RB treatment never ran)
hid behind it.

**What actually shipped wrong in v3.3 and why the gates missed it:**
1. Blocked lenses: v1 occlusion gate had a hard skip list + Zed-only
   occluders; the gates ran ADVISORY (report-only) so nothing aborted.
2. Riders: FX lifecycle had no OFF; the treadmill law (world-static +
   visible = paces the subject) was not encoded anywhere.
3. Flicker: exact-coplanarity checks cannot see epsilon-band stacks,
   trenches, or thin-contrast streaming features.

**v3.4:** all gates FAIL-CLOSED (advisory mode deleted), 3 new/rewritten
gates (motion_frame_audit, occlusion v2, render_stats), street
ground-continuity + crossing-window gates, camera keepouts with HARD
post-step ejection in the crowd sim, FX taxonomy, origin-centered
chunk emission + belt-local keyed scatter. Render: 0 BLOCK / 0 WARN
on all 1080 frames (v3.3: 23); rider count 0 (two independent
fresh-eyes audits, pixel + VLM); S4b readable; debris streams past
the lens on camera.

**Residual (v4 polish list):** contact-shadow illusion class (flat
workbench has no contact shadows -- every "hover" read in the fresh-
eyes audit traces to it; fix = shadow discs or workbench shadows);
S8 lunge-camera edge mass; pursuit pacing beat ~35f; occupant idle
bob during the crane-out; KD settle rotation variety.

---

## Session 17 — v4 hero swap shipped (the rigged-actor graduation)

**Delivered**: v4.0 live (9 assets, API-verified). UAL heroes won the
A/B 94/17-18 blind; full fail-closed suite green both modes; 1080f at
0 BLOCK / 0 WARN; the v3.4 hover illusion closed by 144 contact discs
+ the pixel contact_audit.

**The three deepest traps this round** (all live-found, all now laws):

1. **The action-slot binding** (gotcha #66): the entire bake pipeline
   was "working" while silently evaluating the wrong action. The
   tell: my own fidelity gate printed 0.00e+00 — too perfect. The
   slot-drift guard + the master-audit slot probe caught it. Lesson
   repeated from v3.3: a gate that reads 0.00 on a hard problem is
   VACUOUS until you can name the mechanism.
2. **The exit deadlock** (gotcha #69): "the render finished" and
   "the process exited" are DIFFERENT events. Completion-based
   watchdogs in both daemons; the A/B and the full render would have
   stalled forever otherwise.
3. **The reviewer ecosystem earned its cost again**: v4-impl-a found
   the blend-end residue snap (a spec bug I implemented verbatim —
   REV3's own wording was wrong) with a live-measured 4-6x velocity
   spike on camera; v4-impl-b verified capsule byte-parity (the
   rollback lever is real) and caught the pre-bake auto-fit reading
   T-pose heads + the tautological muzzle assert.

**The Blender pixel-gate gauntlet** (contact_audit): headless pixel
reads, row-origin flip, atmosphere raycast blockers, self-quad
occlusion, r_px collapse from edge-probes, subject-occludes-own-disc.
Six distinct failure modes in one gate — each one found by evidence,
not theory. Pixel gates on projected geometry need the SAME
adversarial rigor as the render itself.

**Carry-forward**: GitLab PAT expired (mirror dead until re-issued);
the S6b gunner-torso occlusion hole + S8 arm/roll-cage intersection
are v5 candidates (documented, accepted by the plan).
