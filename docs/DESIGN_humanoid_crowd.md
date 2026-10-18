# DESIGN s22-D6 — the humanoid crowd layer (cylinder → rigged, UAL + RH)

> Status: REV-1 (probe-backed; audit pending). Owner: session-22.
> The user ask: "upgrade that ridiculous cylinder character with
> humanoid models — test BOTH UAL and the recently integrated RH 3d
> models". Probes: scripts/s22_asset_probe.py (family census),
> scripts/s22_bind_probe.py (direct-bind law + world-z numerics),
> scripts/s22_glb_probe.py (export budget law).

## 0. Probe facts (the design's ground truth — all measured this session)

| family | rig | bones | verts | height | actions | bind path |
|---|---|---|---|---|---|---|
| RH x_bot | mixamorig: | 65 exact | Joints 10.5k + Surface 14.2k | 2.051 m | rest-only | DIRECT (same-name) |
| RH male_body | mixamorig: | 78 (65+13 twist) | 38.8k | 3.217 m (rescale 0.64) | none | DIRECT (superset; 13 extras stay at rest) |
| RH female_body | mixamorig: | 78 | 37.4k | 3.027 m | none | DIRECT |
| RH clip 2899 (male standard walk) | mixamorig: | 65 | — | — | 38 f @ import fps | drives x_bot EXACTLY (0 missing / 0 extra bones, probed) |
| RH clip 2781 (idle) | mixamorig: | 65 | — | — | 500 f | same |
| UAL mannequin | DEF-* Rigify | 53 | 8.5k (+42-vert Icosphere stray the loader deletes) | 1.589 m data | 46 (Walk_Loop, Idle_Loop, ...) | loader exists (assets_ual_actors.py) |
| RW character glTFs (Armor-Qin, Farmer, Police, Scholar, CW01) | **NO ARMATURE** | — | 7k–30k | posed | none | NOT crowd material — set-dressing / static heroes only |

- Walk NUMERICS on the bind: hips-z bobs 1.041→0.990 m, feet anti-phase
  (L 0.189→0.096 while R 0.108→0.182) — a real walk, numerically.
- GLB size law (probe 3): LINEAR in agents, no instancing.
  x_bot Joints-only 10.5k verts: 0.75 MB/agent. Decimated ×0.25
  (2.7k verts): **0.27 MB/agent** → a 102-agent film ≈ 28 MB GLB
  (acceptable; the staged record holds 15–21 MB films today).
- male_body/female_body = 13 EXTRA bones vs the 65-clips (twist/helpers):
  same-name transfer still binds (extras ride at rest) — hero-grade
  rigs without retargeting.

## D6-1 Family scope decision

1. **CROWD (the 90–130 mass agents): RH x_bot** decimated to the poly
   budget, bound to RH-canvas-animations clips (2899 walk / 2781 idle).
   Why: the user's named "recently integrated RH 3d models", the
   direct-bind law is PROVEN, and the decimated budget lands the GLB
   at ~28 MB. The mannequin look is film-neutral (a clean silhouette
   that takes tint well).
2. **PRINCIPALS (the 2–4 keyed heroes/officers per film): UAL
   mannequin** at full 8.5k res via the vendored loader's pool
   (Walk_Loop / Idle_Loop / the beat actions). Why: the user's named
   "UAL" test; principals sit CLOSE to camera so 8.5k is affordable
   (3 objects ≈ +2 MB); distinct silhouette separates principals from
   the mass.
3. **RW character glTFs**: statics (no armature) — NOT crowd material.
   Filed as night-market set-dressing + static-hero wardrobe (a later
   round; CJ Scenes group has market/city clusters).
4. Quaternius casual (D2 of DESIGN_s21_hero_lane) stays DEFERRED —
   third family, not in this ask.

## D6-2 Architecture — the rig assembly REPLACES the commuter mesh on the anchor

Today: `new_anchored_obj(name, commuter_lib, loc)` → bake2 keys the
anchor object's `location`/`rotation_euler` + gait shape-keys.

The humanoid layer keeps bake2 UNTOUCHED (the D3 law: bake2 is not a
touch point). The anchor becomes a parent empty; the rig hangs BELOW
it:

```
Zed.NNNN (EMPTY — bake2 keys location + yaw HERE, unchanged)
  └─ <name>.Root (wrapper EMPTY — wrapper_rig facing law, identity)
       ├─ <name>.Rig (ARMATURE — linked data, action = per-agent copy)
       │     └─ <name>.Body (MESH — linked data, skinned)
```

- bake2 keys the anchor exactly as before (it never inspects
  children). The wrapper's `matrix_parent_inverse` carries the facing
  flip + the unit rescale (x_bot imports at 2.05 m; films author at
  1.75 m commuter height → wrapper scale = film_height/2.051, pinned
  per family, never keyed).
- Facing law (D1 of DESIGN_s21_hero_lane, now landed as
  `scripts/wrapper_rig.py`): foot-bone +Y probe at bind, ±Y
  horizontalness contest, refuse fail-closed, report carries the
  winning axis + measured forward. x_bot probe bone: `mixamorig:LeftFoot`.
- LINKED DATA: all crowd agents share ONE armature datablock + ONE
  mesh datablock (probe 3's pattern — the exporter writes per-object
  copies regardless; linking keeps RAM sane at build: 4 GB sandbox).

## D6-3 The motion law (phase + clip + speed)

- **Phase**: the cache's per-agent PHASE channel (K1 composed law:
  stride φ += dist/stride mod 1.0). Agent i's action = a COPY of the
  base clip with every keyframe shifted by `-phase_i × cycle_len`
  (probe 3's shift pattern). Deterministic: re-derives from (i, φ);
  no time dependence. Agents stop marching in lockstep — the single
  most visible tell of fake crowds.
- **Clip selection**: per-agent from the cache SPEED channel at the
  agent's dominant state — speed < 0.05 m/s → idle clip (2781),
  else walk clip (2899). Jog class (speed > 1.8 m/s) → walk clip
  time-scaled is DEFERRED (no jog clip bound this round; the drill
  film's movers walk). The K1 composed clip channel (stationary 0.05
  / jog 1.8 thresholds) is the authority where present.
- **Anchor motion**: UNCHANGED bake2 (loc + yaw keys from the cache).
  The walk plays ON the armature continuously; the wrapper carries
  no keys. In-place clip law: the RH clips are in-place (hips drift
  < 0.05 m across the cycle — verified numerically at 5 samples).

## D6-4 Poly budget + the decimate law

- Budget: **≤ 3.5k verts/agent** crowd-side (GLB ≈ 0.35 MB/agent;
  130-agent ceiling ≈ 45 MB; the export gate fail-closes > 60 MB).
- x_bot: decimate BOTH meshes (Joints + Surface) ratio ≈ 0.14
  (measured at build: assert resulting verts ≤ 3.5k, ≥ 2.0k — the
  band catches a silent no-op AND an over-decimate collapse).
- Decimate runs ONCE on the template before instancing (linked data
  propagates the saving to every agent).
- Principals: UAL full res (8.5k × ≤4 = 34k verts ≈ 2 MB — fine).
- The decimate QUALITY gate is a principal-eye check on the first
  proof film's S7 closeup (the clasp beat — the closest camera).

## D6-5 Honesty gates (fail-closed, numbers travel)

1. BIND: bone-name census (target ⊇ clip names; report the delta
   count), quaternion rotation modes on all pose bones (the s18 law),
   wrapper report (facing sign, probe bone, measured forward).
2. MOTION (the s20 two-column law): per sampled agent — world hips-z
   bob ≥ 0.02 m across the cycle AND feet anti-phase (sign flip
   between L/R z-deltas); anchor world-position matches the cache
   xy at sampled ticks (±1 mm).
3. PHASE: agent[0] and agent[N-1] walk actions differ (key-x sets
   not equal); re-deriving agent[5]'s shift twice gives byte-identical
   key times (determinism probe).
4. EXPORT: GLB ≤ 60 MB; action count == agents × clips-bound +
   pre-existing; previz.json loads in the app (the staged contract).
5. FILM-LEVEL: the existing preflight (D19) + the s32 discovery gate
   + identity marker (r084#9) all run unchanged.

## D6-6 Rollout (which film proves what)

- **tform_1 rev 2 (THE DRILL, humanized)** — the proving film:
  crowd 93 watchers + 24 drill = RH x_bot decimated + walk/idle;
  officers a/b + StandardBearer + Captain = UAL mannequin (full res).
  Tests BOTH families in ONE film, exactly the user's ask. The drill
  formation's K1 composed phase channel exercises the phase law on a
  layered cache.
- **tfog_1 rev 2 (THE EXPRESS, humanized)** — the second proof: all-RH
  crowd on the platform (boarding queue + concourse), commuters in
  coats (tint palette per the existing crowd_palette law). Runs only
  if tform rev 2 lands green with context to spare.
- The older films (tdawn/tferry/tgreen/tsquall): the humanoid layer
  is KIT-LEVEL — each film opts in with a scene-side flag; rolling
  rev 3 across all six is a later round (the staged rev 1/2 packages
  stay for the open review round).

## D6-7 Scene-side integration contract

```python
# in the film scene module (tform_scene.py rev 2):
from humanoid_crowd import crowd_family, bind_crowd, bind_principals
fam = crowd_family("rh_xbot")       # or "ual"
# anchors are built as EMPTIES now (build change):
#   new_anchored_obj(name, None, loc) -> empty, no commuter mesh
# after load_kit_cache + bake_tier2:
bind_crowd(ctx, fam, walk_clip="rh_2899", idle_clip="rh_2781")
bind_principals(ctx, "ual", {"Captain": "Idle_Loop", ...})
```

- `humanoid_crowd.py` (kit-level, vision-kit scripts/): family
  registry + template builders + the bind pass + all gates. The film
  module changes are: anchor empties instead of commuters + two bind
  calls + the palette law re-targeted to the rig materials (tint via
  the UAL loader's tint / a body material swap on x_bot's single
  material slot).
- The exporter reads the anchors' children automatically (armatures
  are scene objects; CAST registry entries gain "rig": family tags —
  the exporter's character census counts meshes; verify the census
  accepts armature-children (a PROBE, not an assumption).

## D6-8 Risks / open questions for the auditor

RQ1. bake2 pairs anchors by NAME against the spawn table (§9.1). The
     anchor becomes an EMPTY — does any bake2/exporter law assume the
     anchor is a MESH (bbox reads, the floating check, the paired
     shape-key contract `add_shape_keys`)? The shape-key branch MUST
     become conditional (rig anchors carry no shape keys) — is the
     guard `ob.data.shape_keys is None` (bake2.py:278) already
     tolerant? PROBE before implementing.
RQ2. The exporter's character census: does CAST/`_collect_characters`
     accept an armature-anchored hierarchy (empty → armature → mesh)?
     The previz.json "characters" table currently lists the commuter
     meshes. PROBE.
RQ3. GLB skin joints: 65 bones × 100 agents — three.js skin uniform
     limits (some viewers cap at ~64 joints/mesh!). x_bot = 65 mixamo
     bones + 13 static tips... if the viewer clamps at 64 the crowd
     BREAKS in the browser but renders fine in Blender. Probe: load
     the 50-agent GLB in the app's viewer (a dev-side smoke) BEFORE
     the full rollout. Mitigation if hit: drop the 13 static bones
     from the export (the s19 fixture law kept them; the EXPORT can
     prune static-tip bones — evidence needed).
RQ4. Decimate ×0.14 on x_bot: does the ball-joint silhouette survive?
     Eye check at the S7 closeup framing before commit.
RQ5. Idle agents (93 watchers parked): 500-frame idle clip × 93
     actions — action-pool RAM + GLB action bloat. Mitigation: ONE
     shared idle action (no phase shift on idle — parked watchers
     share the idle cycle; the eye cannot read a shared idle at
     previz resolution). Walks get per-agent phase; idles share.
RQ6. The palette law recolors per POPULATION group (drill blue+gold,
     watchers earth, officers black+gold). x_bot has 1 material slot
     per mesh (2 slots total) — per-group tint = per-GROUP mesh
     variants (3 mesh copies, linked within group), not per-agent.
     Confirm the commuter palette law's grouping keys survive.
