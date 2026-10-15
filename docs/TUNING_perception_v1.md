# TUNING_perception_v1.md — measured perception laws (the M5 campaign)

> The committed receipt behind the perception/exposure constants the kit
> ships. Cited by five code sites: scripts/look.py (`--exposure` help +
> `_default_exposure`), scripts/viewport_capture.py (`render_angle`
> docstring), scripts/motion_study.py (P3 lab), scripts/tuning_matrix.py
> (the rig). Provenance: the M5 perception campaign, sessions 2–3
> (PLAN.md "M5"; P1+P2 settled in commit 961d81d, P3/P4 session-3).
> Tuning targets what the vision-native principal actually perceives —
> the owner IS the vision agent; there is NO VLM/ascii substitute in
> this kit (scope doctrine).

## What was tuned (and why)

The blind kit's render config was inherited from tools that never had
eyes on the pixels. Three questions, each settled by rendering ONE
diagnostic scene with known ground truth (sizes/colors/positions) under
a matrix of configurations and READING the images:

- **P1 COLOR**: does color earn its keep in annotations? Can workbench
  show what authored materials actually look like?
- **P2 SHADE/LIGHT**: which workbench light/color_type/shadow/cavity ×
  view-transform × exposure combo maximizes usable contrast without
  lying about material colors?
- **P3 ANIMATION REPRESENTATION**: which image class answers "what does
  this animation DO" for an agent that understands images?

## Measured evidence (the numbers behind the defaults)

- Workbench STUDIO renders **~98% of pixels in the darkest third of the
  range** — the default look is a near-black image, and eyes (and any
  downstream audit) hallucinate on black frames.
- **+1.0 EV roughly doubles usable contrast**: stdev 42→54, edge energy
  2.3→3.2, without washing material colors.
- **AgX desaturates mid-chroma colors** (a mid-chroma green went muddy)
  and crushes low-chroma previz palettes; **Standard** keeps authored
  material colors true.
- **MATCAP kills color identity** — surfaces read as lit shading, not
  material.
- **Mono destroys the annotation layer** (labels/flags/gnomon lose
  their color coding). Mono is a legitimate GEOMETRY second-look, never
  the default path.
- **Real EEVEE is the only config where cast shadows honestly reveal
  floating** (workbench shadows are a display feature, not light
  transport).

## The chosen constants (single source of truth: the code)

| Constant | Value | Lives in |
|---|---|---|
| workbench light / color_type | STUDIO / MATERIAL (reads `diffuse_color`, NOT node Base Color — set both) | `viewport_capture.render_angle` defaults |
| workbench shadows / cavity | on / on | `viewport_capture.render_angle` defaults |
| view_transform | Standard (workbench path forces it) | `viewport_capture.render_angle` |
| exposure default | +1.0 EV workbench; 0.0 eevee/cycles | `look.py _default_exposure` |
| readiness clipped / dark | luma ≥ 0.98 / luma ≤ 0.08 | `viewport_capture.image_readiness` |
| readiness subject | RGB distance > 0.25 from corner-estimated background (luma-only missed red-on-gray) | `viewport_capture.image_readiness` |
| readiness flags | BLOWN-OUT >25% clipped · NEAR-BLACK >40% dark · NEAR-EMPTY <1.5% subject | `viewport_capture.image_readiness` |
| template sky strength | 0.5 (gotcha 128) | `scene_template.py` `add_sky_world(strength=0.5)` |
| P3 representations | onion ghosts + multi-angle trajectory + filmstrip + numeric table | `motion_study.py` |

**LAW (gotcha 128, sky×EEVEE):** `add_sky_world()` default strength 1.0
(physical sky) blows out EEVEE stills in studio setups — red reads
pink, highlights clip. Studio/product scenes pass `strength=0.35..0.5`
(the template ships 0.5); reserve 1.0 for outdoor scenes. Workbench
looks NEVER reveal this — workbench ignores world lighting; diagnose
via readiness `clipped_pct` on the EEVEE render, not the workbench one.

**P3 laws (motion_study.py, each build defect measured):** onion-skin
ghosts WIN for rise/fall, speed, direction (spacing = speed, lightness
= age, lightest = oldest); the trajectory polyline wins path SHAPE and
MUST be multi-angle (a vertical trail collapses to a stub from one
angle); filmstrips are supplementary (vertical nuance weak, spin
INVISIBLE); the numeric motion table (POP/BURST flags) rides beside the
images (forced pairing). Build lessons: solid ghosts buried polylines
→ render trajectory and onion in SEPARATE passes; ghosts coincident
with the current pose z-fight → skip <5mm; workbench shadow buffer goes
stale across in-process hide_render toggles → shadows off for the
shadowless pass; 0.1m ticks dominated the line → 0.036m.

## The invariance law (threshold discipline)

**±20%-brightness / 2×-downscale: a perceptual threshold that cannot
survive both perturbations is a knife-edge and does not ship.**
Inherited from the upstream auto-selection calibration
(docs/UPSTREAM_FINDINGS_snapshot.md, "Auto-selection"): rules from
measured lessons, thresholds from data, guard from perturbation — the
±20% brightness + 2× downscale checks caught a knife-edge mean
threshold before it shipped. Corollaries: stats must sample a canonical
grid (edge/dark fractions drift with display resolution — characterize
the IMAGE, not the requested --cols); distribution stats beat means
(dark_frac beat mean for dark; strong-edge FRACTION beat mean-sobel —
two corpus scenes are indistinguishable by mean-sobel). The kit's
readiness thresholds were calibrated on synthetic + rendered images
(test_v1_look #2) and are evaluated on actual pixels at native
resolution — same discipline.

## How to regenerate (the three `tuning_` scripts)

Measurement rigs, NOT kit tools. All three render into `output/tuning/`
and carry sandbox-absolute paths (`/home/z/bvk/output/tuning`,
`/home/z/bvk/scripts` on sys.path) — edit OUT / the sys.path line or
run in that layout:

```bash
bash scripts/blrun.sh --background --python scripts/tuning_matrix.py
bash scripts/blrun.sh --background --python scripts/tuning_exposure.py
bash scripts/blrun.sh --background --python scripts/tuning_annot.py
```

- **tuning_matrix.py** — the P1/P2 harness: the deterministic diagnostic
  scene (mid-gray ground, color-coded cube/sphere/cylinder, low-contrast
  gray/white pair, a 0.25m floater, a 0.07m small ball) rendered under
  the shading matrix (workbench FLAT/STUDIO/MATCAP × MATERIAL/SINGLE/
  OBJECT × shadows/cavity × Standard/AgX, plus an EEVEE Standard/AgX
  arm) at 640×480 + PIL grayscale mono variants.
- **tuning_exposure.py** — the exposure ladder: kit default vs
  +0.5/+1.0/+1.5 EV, plus the FLAT-light+shadows+cavity arm (the
  bright-ground hypothesis). Produced the +1.0 EV default.
- **tuning_annot.py** — the P1 decisive test: the kit's OWN annotation
  + capture code paths (build_annotation_layer → render_angle) at look
  640×480 vs previz 480×270, color vs mono, workbench vs EEVEE.
  Settled "annotations REQUIRE color".

Score each render for object identification, low-contrast edge
legibility, floater pop, small-object visibility — with your own eyes,
readiness numbers beside them. Constants change only with new
measurements; this doc is the receipt.
