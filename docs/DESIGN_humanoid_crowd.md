# DESIGN s22-D6 — the humanoid crowd layer (cylinder → rigged, UAL + RH)

> Status: REV-2 (design audit r1 folded: NO-GO as written →
> GO-WITH-CHANGES; the 3 P0s + 6 P1s + P2s are folded below — the
> §R-revision log at the tail carries the mapping). Owner: session-22.
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

## D6-2 Architecture — the rig hangs BELOW a hidden-mesh anchor

> REV-2 (P0-1 + P1-5 folded): the anchor STAYS a mesh object carrying
> the commuter mesh. bake2's shape-key branch (bake2.py:278) crashes
> on `ob.data is None` — empty anchors are REFUSED. The commuter mesh
> instead goes RENDER-HIDDEN (hide_render=True) and becomes the pure
> transform carrier + gate surface; the rig hangs below it. Zero
> deltas outside vision-kit; zero risk to the five other films.

Today: `new_anchored_obj(name, commuter_lib, loc)` → bake2 keys the
anchor object's `location`/`rotation_euler` + gait shape-keys.

```
Zed.NNNN (MESH anchor — commuter mesh, hide_render=True;
          bake2 keys location + yaw + gait shape-keys HERE, UNCHANGED;
          the exporter excludes render-hidden → no commuter in the GLB)
  └─ <name>.Root (wrapper EMPTY — facing flip + rescale via MPI)
       ├─ <name>.Rig (ARMATURE — linked data, action = per-agent copy)
       │     └─ <name>.Body (MESH — linked data, skinned, VISIBLE)
```

- bake2 keys the anchor exactly as before. Its shape-key gait leg
  keeps keying the hidden commuter (wasted-but-deterministic work;
  the sanctioned bake2 guard `ob.type == 'MESH' and render-visible`
  is FILED DEBT, not this round). The gates that read the anchor bbox
  (floating checks, pairing) read the commuter as today — honest: it
  mirrors the cache position exactly.
- The s20 clobber law holds: object-level rotation keys land on the
  ANCHOR (grandparent); the armature carries no keys; the wrapper's
  `matrix_parent_inverse` carries the facing flip + the unit rescale
  (x_bot imports at 2.051 m; films author 1.75 m commuters → wrapper
  scale = film_height/rig_height, pinned per family, never keyed).
- Facing law (D1 of DESIGN_s21_hero_lane) is implemented FIRST as
  `scripts/wrapper_rig.py` (P0-3: it does NOT exist yet — the
  s21 lane designed it; the pattern is proven at
  assets_ual_actors.py:207-233). Build order: wrapper_rig.py →
  humanoid_crowd.py. x_bot probe bone: `mixamorig:LeftFoot`.
- LINKED DATA: all crowd agents share ONE armature datablock + ONE
  mesh datablock (probe 3's pattern — the exporter writes per-object
  copies regardless; linking keeps RAM sane at build: 4 GB sandbox).

## D6-3 The motion law (phase + LOOP + clip + speed)

> REV-2 (P0-2 folded): the raw shift broke looping AND export.
> Three-part law now:
>
> 1. **WRAP**: agent i's action = a COPY of the base clip with every
>    keyframe time wrapped into `[f0, f0+cyc)`:
>    `t' = f0 + ((t - f0 - phase_i*cyc) mod cyc)` — the phase becomes
>    an IN-CYCLE rotation; keys never leave the window.
> 2. **LOOP (Blender-side)**: every fcurve gets a CYCLES modifier
>    (extends playback across the whole film span). `action.frame_range`
>    still reads the keyed window → the exporter samples ONLY the
>    compact cycle (verified in the re-probe) → the GLB clip stays
>    ~38 frames and the VIEWER loops it (three.js LoopRepeat,
>    PrevizViewer.tsx:591-597 — the web-side loop is free).
> 3. **CLIP TRIM**: the idle clip is trimmed to ONE representative
>    cycle at bind (~64 f, measured) before any binding — the 500-f
>    raw idle would be sampled at 1-frame stride per bone per agent
>    (P1-1) and explode the GLB.

- **Phase source**: the cache's per-agent PHASE channel (K1 composed
  law: stride φ += dist/stride mod 1.0). Deterministic: re-derives
  from (i, φ); no time dependence. Agents stop marching in lockstep.
- **Clip selection**: per-agent from the cache SPEED channel at the
  agent's dominant state — speed < 0.05 m/s → idle (trimmed), else
  walk (2899). Jog class is DEFERRED (no jog clip this round). The
  K1 composed clip channel is the authority where present.
- **Anchor motion**: UNCHANGED bake2 (loc + yaw keys from the cache).
- **Idle sharing**: parked watchers share ONE idle ACTION (bpy-level
  RAM win). The exporter still writes per-(object, action) glTF
  animations (reasoned, io_scene_gltf2 action.py:152-173) — the GLB
  cost of shared idle is measured in the re-probe; if the total blows
  the 60 MB gate, the documented fallback drops watcher idles
  entirely (rest pose; T-pose at previz distance was judge
  acceptable-vs-alternatives pending the eye check).
- **In-place law**: verified for the WALK (5-sample hips drift); the
  re-probe adds the idle's drift census (P2-5).

## D6-4 Poly budget + the decimate law

> REV-2 (P1-2 folded): the REV-1 receipt measured ONE mesh
> (Joints-only); the REAL agent carries both meshes. The re-probe
> (s22_glb_probe2) re-measures: both meshes × ratio 0.14, walk
> CYCLES'd (export-window check), trimmed idle, N=50 — the budget law
> is re-stated from THAT receipt only.

- Budget: **≤ 3.5k verts/agent** crowd-side (combined both meshes);
  the export gate fail-closes > 60 MB GLB.
- x_bot: decimate BOTH meshes (Joints + Surface), ratio measured at
  build to land ≤ 3.5k combined (assert the band: ≤ 3.5k, ≥ 2.0k —
  catches a silent no-op AND an over-decimate collapse).
- Decimate runs ONCE on the template before instancing (linked data
  propagates the saving to every agent).
- Principals: UAL full res (8.5k × ≤2 keyed heroes ≈ 17k verts —
  fine).
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
   key times (determinism probe). The WRAP law: every walk action's
   key times stay inside `[f0, f0+cyc)` (assert min ≥ f0, max < f0+cyc).
4. EXPORT: GLB ≤ 60 MB; the bpy-level action census (agents-with-walk
   × 1 + shared idle × 1 + pre-existing) is asserted BLENDER-side;
   the GLB animation count is the exporter's per-(object, action)
   law (not gated); previz.json loads in the app (the staged contract).
5. RENDER-HIDDEN LAW: the anchor commuters are hide_render=True AND
   excluded from the GLB (probe: the export excludes render-hidden —
   assert the GLB node count has NO commuter nodes).
6. FILM-LEVEL: the existing preflight (D19) + the s32 discovery gate
   + identity marker (r084#9) all run unchanged.

## D6-6 Rollout (which film proves what)

> REV-2 (P1-6 + P3-1 folded): the officers are CACHE agents (the M5
> interaction pair — the pin must not break). They get RIG ASSEMBLIES
> exactly like the crowd (cache-driven, RH family), NOT UAL. The UAL
> principals are ONLY the keyed heroes OUTSIDE the cache
> (StandardBearer + Captain).

- **tform_1 rev 2 (THE DRILL, humanized)** — the proving film:
  the 102 cache agents (93 crowd-list + 9 paired chase; populations
  24 drill / 4 drummers / 2 officers / 72 watchers) = RH x_bot
  decimated + walk/idle with the phase law; the 2 keyed heroes
  (StandardBearer + Captain) = UAL mannequin (full res). Tests BOTH
  families in ONE film, exactly the user's ask. The drill formation's
  K1 composed phase channel exercises the phase law on a layered
  cache. The M5 interaction bake + the F-TS5 102-pin are UNTOUCHED.
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
from humanoid_crowd import crowd_family, bind_crowd, bind_principals, motion_gates
fam = crowd_family("rh_xbot")
# anchors STAY the commuter-mesh objects (D6-2: no build change)
# after load_kit_cache + bake_tier2:
rep = bind_crowd(ctx, fam, group_tint={"groups": [...],
                                       "agent_group": [...]})
motion_gates(ctx, rep["reps"], walk_cycle=rep["walk_cycle"])
principals = bind_principals(ctx, {"Captain": ("Idle_Loop", 1.0, None), ...})
```

- `humanoid_crowd.py` (kit-level, vision-kit scripts/): family
  registry + template builders + the bind pass + all gates. The film
  module changes are: the anchors gain rig children (the anchor
  itself stays a mesh object — D6-2) + two bind calls + the palette
  law re-targeted to per-OBJECT material slots on the rig body (the
  P2-3 mechanism). The census is a REGISTRY (CAST keys), not a scan
  (audit RQ2) — no exporter character-census delta is needed.

## D6-8 Risks / open questions — ANSWERED by audit r1 (evidence kept)

- RQ1 (bake2 on empties): CRASH at bake2.py:278 (`ob.data.shape_keys`
  with data None) — the architecture pivoted to hidden-mesh anchors
  (D6-2 REV-2); bake2 untouched.
- RQ2 (exporter census): registry-based (CAST/BOARD/RUN_PARAMS keys,
  export_previz_package.py:1214-1221), root lookup type-agnostic
  (:1230-1231); the GLB has NO type filter (blender_kit:1145-1160) —
  the rig hierarchy exports unconditionally; render-hidden is the
  only exclusion (which is exactly what the commuter anchor needs).
- RQ3 (viewer joints): three.js GLTFLoader r186 uses bone TEXTURES —
  the legacy ~64-joint uniform cap does not apply (reasoned from
  PrevizViewer.tsx:529 + package.json:78). Exposure is PERF, not
  correctness: ~102 concurrent clipActions + ~6.6k bone nodes; the
  dev-side smoke (load the rev-2 GLB in the app, click through) is a
  REQUIRED step before staging.
- RQ4 (decimate quality): pending the S7-closeup eye check.
- RQ5 (idle sharing): works bpy-side; GLB stays per-(object, action)
  — cost measured in the re-probe; fallback = drop watcher idles.
- RQ6 (palette): the law lives in tfog_scene.py:648-686 (count-split
  from POP_PLAN + per-anchor mesh copy); tform's copy is a STUB
  (:606-629 returns None) — the grouping keys must come from tform's
  static-table count split (the ingest reorder law), wired at bind
  time. Per-OBJECT material slots (P2-3) are the preferred mechanism
  (zero mesh copies; 3 group material datablocks linked per object).

## R-revision log (audit r1 → REV-2)

- P0-1 → D6-2 rewritten: hidden-mesh anchors (bake2 untouched,
  honestly); the bake2 type-guard filed as DEBT.
- P0-2 → D6-3 rewritten: WRAP-mod-cyc + CYCLES modifiers + idle trim;
  the re-probe verifies the export window stays compact.
- P0-3 → build order stated: wrapper_rig.py FIRST (does not exist).
- P1-1/P1-2/P2-5 → re-probe mandated (both meshes, real ratio, idle
  drift + trimmed-idle cost) before the budget law is trusted.
- P1-3 → per-entry rig tags DROPPED (module HERO_MODE stands;
  crowd rides the GLB unregistered, principals via CAST as today).
- P1-4 → palette wiring specified from the static-table count split.
- P1-5 → anchors stay mesh objects (no signature change anywhere).
- P1-6 → officers stay cache agents (RH rigs); UAL = keyed heroes only.
- P2-2 → D6-7's census claim corrected (registry, not a scan).
- P2-4 → UAL principals via a thin caller over _import_actor + a
  tform-shaped audit (no JeepRoot demand).
- P3-1 → counts fixed (102 = 93 + 9; populations 24/4/2/72).
