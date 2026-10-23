# DESIGN_fix_wave1.md — the universal fix wave for the 5 user issues

> Evidence chain: worklog "fix-wave-1-rca" + probes f66aa4f.
> Scope: fix-one-fix-all in the SHARED layers; then re-bake, re-render,
> re-export, re-stage every test film. The vision-kit is the film lane;
> agent-kit owns governed exporter surfaces; crowd-kit owns the bridge.

## D1 — Unique bone names per rig (kills the zero-walk class)

**Root cause (proven)**: the staged GLB carries 129 nodes named
`mixamorig:Hips` (one per wrapper). three.js `PropertyBinding` resolves
tracks BY NAME → all 129 walk actions bind to the FIRST rig → 128
statues + 1 rig torn by 129 stacked actions.

**Design**: at bind time (humanoid_crowd.bind_crowd), per agent:
1. `a2 = _wrap_action(...)` (unchanged) — per-agent copy already.
2. `arm_i.animation_data_create(); arm_i.animation_data.action = a2`
   + **pin the slot** (`ad.action_slot = a2.slots[0]` — kb law #7).
3. **Rename every pose bone on `arm_i`** with an agent-unique prefix:
   `mixamorig:Hips` → `z0007.mixamorig:Hips`. Renaming a pose bone
   AUTO-REMAPS the bound action's fcurve paths (s20-proven law), so
   `a2` (bound in step 2, per-agent copy) follows. Prefixing preserves
   the substring matches the facing probe + retarget machinery use
   (`"foot" in name.lower()`).
4. Idle agents get **per-agent copies** of the idle action too (a
   shared idle would get remapped by the first renamer and corrupt
   every other sharer — new law: NO shared actions across rigs once
   bones are per-agent-renamed).
5. `wrapper_rig.wrap()` runs AFTER the rename (its probe matches
   substrings; prefix-safe).

**Also**: the hero rigs (bind_principals) get the same treatment
(they are single, but uniqueness is cheap and future-proof: prefix
`h<name>.`).

**Gate (fail-closed, new)**: post-bind census — the set of bone names
across all wrapper armatures must be UNIQUE (assert; refuse on dup).
Plus the exporter (D4) refuses duplicate node names at export time so
no lane can reintroduce the class.

**Rejected alternative**: rename at export time in the exporter —
needs the same per-agent action isolation anyway, and the exporter is
governed (agent-kit) while the bind layer already owns per-agent
copies; bind-time is one owner, one test surface.

## D2 — Hero clip resolution + facing (kills the gun-pose + backwards classes)

**Root cause (proven)**: `bind_principals` requests `Idle_Loop`;
`BEAT_ACTIONS` pool omits it; the fallback
`clip.lower() in k.lower()` hits `Pistol_Idle_Loop` → every hero in
the static gun-hold pose. Separately the UAL actors import with
`facing −1` (visual forward = −Y) and the sign is RECORDED but never
APPLIED → heroes ride their roots ~180° backwards (measured 147°/
152°).

**Design** (humanoid_crowd.bind_principals + assets_ual_actors pool):
1. Add `Idle_Loop` (+ `Walk_Loop`, `Jog_Fwd_Loop`, `Sprint_Loop`
   already present) to `BEAT_ACTIONS` (the glTF carries 46 animations
   incl. plain `Idle_Loop` — the pool filter is the only dropper).
2. Resolution: EXACT match only. On miss: fail loud with the pool
   census (no substring scan — the pistol class dies here).
3. Pin `action_slot` on every assignment.
4. Facing: after import + floor lift, if `facing_sign == −1`, rotate
   the actor wrapper `Rz(π)` so visual forward = wrapper +Y = the hero
   root's travel direction (the same convention the crowd wrappers
   already satisfy — measured 1–10° error).
5. Hero over-speed keys (tfog 7.8 m/s passenger, tform 13.4 m/s
   bearer): film-side retime to ≤ 2.5 m/s + a hero speed gate
   (fail-closed > 3 m/s on non-chase hero paths) in the scene gate
   pack.

## D3 — Walk cadence vs anchor speed (kills the glide/foot-slide read)

**Root cause**: the walk clip is authored 30 fps, played in a 24 fps
scene (cycle 25% slow), at a FIXED cadence while anchors move
0.3–3.8 m/s. Legs cannot match the ground → gliding statues even when
the bind works.

**Design**: speed-class retiming at bind time:
1. Measure the clip ONCE (s43 law): cycle frames `cyc` (already
   known), hips travel per cycle `travel_m` (measure; if ~0 treat as
   in-place with nominal 1.4 m/s cadence) → natural cadence speed
   `v_nat = travel_m / (cyc/30)`.
2. Class buckets from the cache mean speeds (already computed by
   `_cache_speeds`): e.g. ≤0.9 / ≤1.6 / ≤2.4 / rest, clamped retimes
   `scale = clamp(v_class / v_nat, 0.6, 1.8)` — PLUS the 30→24 fps
   correction factor `24/30`.
3. Per class: ONE retimed base action (key-time scale = scale), then
   the existing per-agent phase-wrap copies derive from the class
   base. 4 extra actions total.
4. Bind-time motion gate: every WALK-classified rig's action must
   show hips-z span ≥ 0.02 m over one cycle (refuse + fall back to
   the verified walk otherwise — the 12 low-span walks die or get
   replaced).

**Rejected**: per-frame clip-time driving via NLA (correct but heavy
at 129 rigs; the class approximation is measurable and the OOM law
looms). The phase channel stays the per-agent offset authority.

## D4 — Exporter duplicate-name refusal (agent-kit, governed)

New fail-closed check in `export_previz_package.py` preflight: walk
the to-be-exported node set; assert NO duplicated node names among
ARMATURE-bone nodes (and warn on any object-level dups). Any dup →
exit non-zero with the census. This makes the D1 class impossible to
re-ship from ANY lane (the stills/strips never catch it — only the
GLB consumer does).

Also tighten gate 17: the teleport-window EXEMPTION must not cover
authored-layer seam frames (the tform pins teleported INSIDE exempt
windows and shipped).

## D5 — tform pin-seam (kills the mass-teleport class)

**Root cause (proven)**: `tform_bake.py` extracts PIN/TRANSFORM layer
payloads from the PROBE bake's measured positions, then applies them
to the GROUPS-stage bake whose base trajectories differ (groups
attach → ORCA interactions differ) → every window seam snaps (measured
392 events >4 m/s, max 55.8).

**Design**: re-derive the pins from the FINAL (groups) bake: run the
groups bake FIRST, read each agent's measured base position at the
pin ticks from THAT cache, author the layers, then re-bake with
layers (deterministic — same seed → same base when layers are
position-only). Keep the design's continuity assert (position-
continuous within one tick step at EVERY boundary) and make it
fail-closed against the SHIPPED cache (not the probe).

## D6 — Keepout clamp yaw (crowd-kit bridge)

**Root cause**: `clamp_keepouts` rim-projects positions; the yaw/
speed channels keep pre-clamp values → visible sideways slides +
wrong-facing reads near cameras (2 agents/film, ~12 events).

**Design**: after the clamp pass, re-derive yaw (and speed) for the
clamped rows only, from the CLAMPED position deltas (the same
delta+carry math K1 uses for layered agents). Crowd-kit-side change
+ their battery (53/53) must stay green + the r054 bridge tests.

## D7 — Cinematography (the eyeball pass)

After D1–D6 land and the films re-bake: render all stills per film,
contact sheets, run the principal eye pass (VLM-assisted framing
audit + the framing gates), re-author the failing shots' cameras
(vantage/height/coverage), re-render. Per-film subagents audit shot
tables against the story beats; the principal (me) makes every
visual verdict.

## Execution order

D1+D2+D3 (one bind-layer commit + scene-gate additions) → D5 (tform)
→ D4 (agent-kit governed + sync) → D6 (crowd-kit) → re-bake wave →
D7 (eye pass) → export wave + stage + app smoke.

## Test matrix (per film, after fixes)

- npz probe: unchanged (cache untouched by D1–D3).
- Scene probe: heroes ≤ 10° facing; 0 frozen walk rigs; hero actions
  exact-resolved (no `Pistol_*` unless requested by name).
- GLB probe: unique bone names; walk actions bind per-rig (verify by
  sampling two rigs' bone tracks target distinct nodes); teleport
  census: tform ≤ 2 agents/≤ 8 events, others ≤ current.
- Eye pass: 12/12 stills per film certified.

---

# REV-2 — the audit fold (agent-7291cfbc, GO-WITH-CHANGES)

The audit's four P0s + P1s folded. Supersedes the affected sections:

## D1-REV2 (unique bones — the audit's blockers fixed)
- **Per-agent DATA copies**: `arm_i = tmpl["arm"].copy()` shares the
  armature DATA across all agents — renames cascade + cross-corrupt
  bound actions. LAW: `arm_i.data = tmpl["arm"].data.copy()` per agent
  BEFORE link/wrap/bind/rename; re-run the quaternion census per agent.
- **Vertex groups follow**: bone rename does NOT rename vgroups →
  unskinned statues. LAW: per-agent mesh-data copies +
  `me.data = me.data.copy()`, then rename every vgroup matching a bone
  with the SAME prefix. Supersedes the s25 per-group data sharing
  (materials ride the copy; RAM receipt logged per the OOM law).
- **Separator**: use `:` not `.` (`z0007:mixamorig:Hips` — dot is a
  three.js track-name reserved char; the colon family is proven
  through the app sanitizer).
- **Order LAW**: wrap() BEFORE rename (the explicit probe bone +
  motion_gates read exact names; the auto-scan is substring-safe) —
  then bind action, pin slot, THEN rename bones (the s20 remap fires
  for the bound action only; modifiers survive — one-line probe
  asserts it).
- **Consumer census**: motion_gates' `mixamorig:Hips`/`Foot` lookups
  become prefix-tolerant (endswith/contains); rig_retarget family
  detection gets suffix-awareness OR the hero rename is scoped out of
  retarget lanes (chosen: suffix-aware `endswith("mixamorig:Hips")`).
- Post-rename skin-deform smoke in the test matrix (vgroup/bone match
  assert per rig).

## D2-REV2 (facing — kill the double-flip)
- The RCA premise was WRONG: the vendored loader ALREADY applies the
  facing flip (`matrix_parent_inverse`, assets_ual_actors.py:214-217).
  The actual defect: `_facing_sign` probes the POSED foot while the
  import action is still assigned (the A2b class).
- FIX: `_facing_sign` reads REST (bone.matrix_local, ±Y contest,
  refuse-on-ambiguous — reuse wrapper_rig.facing_probe semantics).
  ONE flip surface (the loader's child MPI). NO wrapper Rz(π) step.
- Gate: measured hero facing ≤ 10° (fix1_probe_chain).
- Clip resolution half VERIFIED-CORRECT as designed (exact match,
  Idle_Loop added to the pool, slot pins, fail-loud).

## D3-REV2 (retiming — formula fixed)
- **s = clamp((24/30) · v_nat / v_class, s_min, s_max)** as the
  key-time multiplier (the design's v_class/v_nat was INVERTED).
- Per-class (f0, f1_class) threaded through the bind report;
  motion_gates samples each rep's own class cycle.
- The chase bucket (~3.8 m/s) exceeds any single walk clip: add a
  JOG/RUN clip for the top class (from the RH library, vendored
  fallback like 2899/2781). Residual slide stated + accepted per band.
- The 12 low-span walks are most plausibly unpinned-slot binds — the
  slot pin + the ≥0.02 m span gate kill that class.

## D5-REV2 (tform — the real root cause)
- There IS NO groups bake in tform (stages: probe→layers→interaction→
  finish; the groups covenant is tFOG's). The defect: the four
  TRANSFORM payloads omit `"operation"`, `_build_edit` defaults to
  ADDITIVE, the native composes base+traj while the samples are
  ABSOLUTE yard coordinates. Boundary jumps == base magnitude
  (measured on the shipped GLB; the t=120 pin onset — measured on the
  same cache — shows ZERO events: the additive signature).
- FIX: `"operation": "absolute"` ×4 + the continuity assert against
  the COMPOSED npz + a formation-shape assert (composed == authored
  traj inside windows; the R6 rehearsal validated traj only).

## D6-REV2 (clamp-yaw placement)
- Inside `to_previz_cache`, AFTER the belt shift, BEFORE the payload
  hash (clamp→re-derive→hash; an npz post-pass would desync
  payload_sha256).
- `clamp_keepouts` returns a touched-(tick,agent) MASK; re-derivation
  fires only on touched rows (untouched films stay byte-identical);
  skip already-K1'd rows; speed re-derived too.
- Expect keepout-fixture byte updates in the 53/53 battery.

## D4-REV2 (gate-17 boundary channel)
- Emit the authored-layer boundary tick list into the npz meta;
  `phase_slide_problems` REFUSES (not exempts) at boundary ticks.
- The duplicate-node-name refusal stands (verified live: tdawn_4 GLB
  118 dup names; tform_1 capsule-era 0).

## Rejected alternatives (recorded)
- App-side index-based binding / per-rig mixer scoping: fixes the
  consumer but leaves the GLB non-portable (any external viewer still
  breaks); export must be self-consistent.
