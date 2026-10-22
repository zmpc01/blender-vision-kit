# DESIGN — The engine-map root-cause fix + the look re-certification wave (s27)

> Status: REV-2 (audit round 1 folded — GO-WITH-CHANGES, 5 amendments).
> Audit verdict: the root-cause diagnosis + fix shape confirmed against
> the code; folded: F1 the exposure tail stays engine-unconditional +
> eevee-only knob guards; F2 case-normalize at the branch top; F3 the
> OOM knob order corrected (memory_limit > cast > resolution > samples/
> bounces — bounces are TIME levers, not memory); F4 the 3 ladder
> scripts pin EEVEE — laddering runs through the FILM LANE (module
> constants + SAMPLES env + the stills runner), not the ladder scripts;
> F5 the D2 hoist reuses blender_kit.normalize_engine_id (no new
> helper). F11 the --still 0 falsy bug aligned to `is not None`; F12
> the resolved ENUM is printed, not the CLI arg; F8 the tsquall wet
> sheen needs no SSR translation (materials carry it; Cycles glossy GI
> reads STRONGER than eevee SSR — direction-of-change note); F9 tfog
> volume_bounces 1 matches the certified single-scatter corpus; F14
> tsquall peak-RSS estimate 1.2-2.0GB (fits 4GB). Evidence chain: worklog s27 (engine-map sweep
> + the three-way tferry A/B). Mandate: fix the ROOT CAUSE of the
> 4-film look failure, then re-certify the four films' stills.

## The evidence (measured this session, receipts inline)

1. **THE ENGINE-MAP SWEEP**: all six stills runners default
   `ENGINE=cycles`. The `_set_engine` mappers: tdawn + tform have a
   real `CYCLES` branch; **tferry / tgreen / tfog / tsquall map
   `--engine cycles` to `BLENDER_WORKBENCH`** (the "eevee-or-workbench"
   two-way if/else predates the humanoid Cycles law).
2. **THE LAW IT VIOLATES**: SKILL gotcha 128 / session-6 R3 F6 —
   "workbench ignores world/sky entirely … only the ship-preview lane
   tells the truth". A workbench render CANNOT show the night sky,
   sodium pools, noon sun, fog volume, or storm sky — exactly the five
   surfaces the s26 eye gate failed the four films on.
3. **THE A/B (tferry S6, three-way)**: certified tferry_1 (EEVEE, s14)
   = night + neon + pools; staged tferry_2 ("s25 Cycles") = flat gray;
   s27 probe (sky fix + x3.5) = SAME flat class. The probe's render log
   shows no Cycles fingerprint; `_set_engine` provably resolves
   workbench for `--engine cycles`.
4. **THE s26 RCA REWRITE**: the s26 verdict ("the Cycles engine swap
   invalidated the EEVEE-era world tunes") was WRONG-SPACE — those four
   films' stills never ran Cycles. The "Nishita stays luminous" analysis
   was built on a custom cylinder repro that set the engine properly,
   while the FILM LANE silently rendered workbench. The certified two
   (tdawn/tform) were exactly the two modules WITH a Cycles branch.
   The s26 tferry "sky fix + sodium x3.5" was also judged on workbench
   probes — its constants are UNPROVEN for real Cycles.

## Decisions

### D1 — Port the tform Cycles branch to the four modules (ROOT-CAUSE FIX)
tform_scene.py's branch is the canonical measured pattern (samples,
denoise, CPU device, bounded bounces: max 4 / transmission 2 / volume 1,
the 4GB-sandbox streaming law). Port verbatim to scene_last_ferry.py /
scene_green_light.py / tfog_scene.py / scene_squall.py. The eevee and
workbench branches keep their existing knobs (SSR knob stays eevee-only;
workbench STUDIO/MATERIAL stays).

### D2 — Hoist the engine resolution BEFORE build_world (the conditional-tune enabler)
tferry_world.build_world reads `scene.render.engine` at BUILD time to
pick the engine-conditional sky (0.12 EEVEE / 0.012 Cycles) and the
practicals x3.5. In main() the engine is set only at STILL time — after
build_world — so the conditional never fires (it reads the EEVEE
default). Fix: extract `_engine_id(name)`; in main(), set
`scene.render.engine` from it BEFORE `build_scene()`; `_set_engine`
keeps applying the render-time knobs (idempotent). Applies to the four
modules (tdawn/tform worlds are engine-agnostic — no change there).

### D3 — The re-tune wave is EYE-FIRST, per film, against its certified corpus
With real Cycles running, each film's world tune is judged against its
EEVEE-era certified stills (the A12 corpus) + image_metrics, ladder by
ladder:
- tferry: the s26 constants (sky 0.012, practicals x3.5) are UNPROVEN —
  re-probe S1/S6 under real Cycles and re-ladder from measurement.
- tgreen: the noon sun (the certified AgX-noon + hard shadows) —
  tgreen_world sun block under Cycles.
- tfog: the blue-hour fog (TFG.BlueHour + fog density tfog_world:65;
  the SKY LIVES IN THE SCENE MODULE) — volume_bounces=1 is wired by D1.
- tsquall: the bright storm sky + wet-ground sheen.
Each film: 2-3 probe stills -> eye verdict vs corpus -> ladder -> full
12 -> the re-ship path (stills + canonical exporter + stage + app-repo
commit IN THE SAME MICRO-STEP + browser smoke + the eye re-gate).

### D4 — The engine-id travels with the artifact (the look-verdict law)
SKILL s26 law: "a look verdict carries its engine id". Every still
rendered this wave logs the resolved engine id in the blrun output; the
worklog receipts carry it; the eye-gate sheets' verdict rows name the
engine. A render whose engine id is not printed is not certifiable.

### D5 — What does NOT change
- The filmstrip/flowstrip lanes stay WORKBENCH (analytic overlays —
  certified surfaces, deliberately light-blind).
- The GLB export path is engine-agnostic (no change).
- tdawn_4 / tform_3 (certified, real Cycles) are NOT re-rendered unless
  the user-comment verification or the eye re-gate finds a defect
  (both green this session — 5/5 comments verified).
- The reconstruction .blend stays the fallback (the original FBX serves
  via RH_ASSETS — proven live this session: 129-rig binds, gates green).

## Risks / audit asks
- R1: does the early engine set break the WORKBENCH stills lane (the
  runner's ENGINE=workbench path) or the dry-run path? (Should not —
  the early set is the same id _set_engine would resolve.)
- R2: real-Cycles memory on the 135-rig tsquall (the biggest cast) at
  the tform bounce knobs — measure peak RSS on the first probe; if
  OOM, the bounded-bounce knobs are the lever, not a module fork.
- R3: the tfog volume under real Cycles with volume_bounces=1 — the
  s26 "white-out" claim is unproven for real Cycles; measure before
  re-tuning the density.
- R4: the exposure 0.3 (tferry) was tuned under EEVEE+AgX — under
  Cycles+AgX the same exposure may need the ladder; judge by eye vs
  the corpus, not by number.
