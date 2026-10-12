# DESIGN F-TD trio (session 14): D-TD20/21/22 — the kit-side filings

> The user-directed round: exhaust the scoped kit items on the tdawn
> track, then a NEW scene. This doc carries the three kit-side changes
> queued by PLAN.md value order: F-TD10 (concurrent blrun), F-TD11
> (make_material emission decouple), F-TD12 (shot-cam occlusion probe).
> Review protocol: fresh-context sub-agent critique BEFORE implementation.

## D-TD20 — blrun.sh cooperative display lock (F-TD10)

### The mechanism (precise, from source)

`scripts/blrun.sh` Xvfb lifecycle has two concurrent-pipeline failure
modes, both SILENT:

- **(a) the socket-steal race**: pipeline B's `xvfb_running()` check
  races A's Xvfb startup. B starts its own Xvfb on the same display →
  Xvfb B dies ("server already active") — but B's readiness check only
  waits for `$XSOCKET` to EXIST, which A's socket already satisfies →
  B proceeds. On exit, B's cleanup() runs `rm -f "$XLOCK" "$XSOCKET"`
  (B had a non-empty XVFB_PID) — **removing the socket inode A's Xvfb
  is serving**. A's NEXT Blender client connect fails. No traceback
  anywhere (measured in session 13: the stills pipeline died while an
  A19f battery ran).
- **(b) the shared-display kill**: B correctly detects A's Xvfb and
  reuses it (B's XVFB_PID stays ""), but A's own cleanup kills the
  shared Xvfb when A finishes — B's display dies MID-RENDER.

### Decision

A cooperative `flock -n 9` on `/tmp/blrun_xvfb${DISPLAY_NUM}.lock`,
acquired BEFORE the stale-lock/Xvfb block, fd held for the script's
lifetime (flock auto-releases on process death — crash-safe, no stale
lock problem). On contention: exit 3 with a teacher message that names
F-TD10, prints the holder stamp, and offers the two legitimate escape
hatches: serialize, or `BLENDER_DISPLAY=:98` for a genuinely parallel
pipeline (each display number carries its own lock).

- `BLRUN_FORCE=1` bypass documented in --help (escape hatch, prints a
  loud WARN when used).
- After acquiring, write an informational holder stamp into the file
  (`pid date cmdline`) — flock remains the authority; the stamp is only
  for the error message.
- The stale-lock removal block stays INSIDE the lock (serialized).
- cleanup() unchanged (it only touches Xvfb state for the Xvfb it
  started; under the lock no concurrent peer exists).

### Ports

blrun.sh is per-repo (NOT on the vendor manifest). The same patch shape
lands in: blender-vision-kit (home), blender-agent-kit (canonical),
blender-crowd-kit (the tdawn export path's blrun), blender-escape-previz.
Four commits, one per repo, each referencing F-TD10.

### Test (shell, no Blender needed for the contention case)

Two concurrent `blrun.sh --help`+sleep-hold probes: hold the lock with a
tiny `flock` holder process; second blrun must exit 3 with the teacher
line. Plus a sequential-reuse sanity (KEEP_XVFB=1 twice in a row still
works — lock released between runs).

## D-TD21 — make_material emission params (F-TD11)

### The problem (measured)

- Blender 5.x Principled `Emission Color` DEFAULTS to white; the kit's
  `make_material` (agent-kit + vision-kit copies) sets no emission
  inputs → any consumer raising `Emission Strength` gets a paper-white
  AgX clip (tdawn_1 S6's gate throat).
- The film-side helper (tdawn_actors.py) pins Emission Color = base rgb
  (session-12 fix) — but session-13 found near-white ALBEDO + emission
  still blows out via albedo reflection → the DECOUPLE (dark base +
  warm Emission Color) is the real law, needing an explicit param.

### Decision

Extend BOTH kit copies + the film twin:

```python
def make_material(name, color, roughness=0.5, metallic=0.0, *,
                  emission_color=None, emission_strength=None):
```

- `emission_color=None` → **pin Emission Color to the base color** (the
  measured law becomes the default; non-glow consumers unaffected —
  their strength stays 0).
- `emission_color=<rgb>` → use exactly that (the decouple case).
- `emission_strength=<float>` → set it (one-call glow materials).
- Both writes guarded `try/KeyError` (3.x-compatible pass-through, the
  tdawn_actors pattern).
- Workbench `diffuse_color` stays the BASE color (workbench has no
  emission; dark-base glow reads dark in workbench — acceptable and
  documented in the docstring).
- Docstring carries the two-line law: "Emission Color defaults WHITE in
  5.x — pinned to base here; pass emission_color to decouple (dark base
  + warm emission for glow surfaces under AgX)."

tdawn_actors.py's make_material gains the SAME params (signature kept
backward-compatible: positional name/rgb/rough/metallic untouched).

### Vendor duty

agent-kit's `blender_kit/__init__.py` IS on the governed vendor
manifest → after the agent-kit commit, run the vendor round
(`tools/sync_shared.py --to <escape>`, commit both) so the
governed-pair guard stays green on the next escape-side export.
Verify the manifest entry exists first.

### Tests

agent-kit: extend the existing make_material coverage (locate it —
tests/test_*lib* or a material-scoped file) with: default call pins
Emission Color == base; explicit emission_color honored; strength set;
no Emission Color input (simulated 3.x) tolerated. vision-kit: same
shape in its own suite (next v-number).

## D-TD22 — shot-cam occlusion probe (F-TD12)

### The problem (measured, 2-hour forensic)

A depth structure built on the camera's side of an opening occludes
everything inside it (tdawn_2's S9 tunnel back wall hid the dive). The
kit had NO tool that names what a camera sees first; the recession
class was diagnosed by manual ray-cast probes written ad hoc.

### Decision

`look.py` grows `--probe-camera NAME` (repeatable/comma-separated) and
`--probe-cameras` (all cameras), evaluated at `--frame` (default: the
look frame):

- origin = camera world location; direction = camera's -Z world axis;
  `scene.ray_cast(depsgraph, origin, dir)` on the EVALUATED depsgraph.
- Print a `PROBE` row per camera: name, frame, hit object, hit distance,
  hit point — or `clear` (no hit within scene bounds). Never raises.
- Rows also land in `look_manifest.json` under `camera_probes` (the
  machine-checkable twin; manifests are already the blind-consumer
  ground truth).
- The probe MUTATES NOTHING: no camera creation/binding, no
  scene.camera writes, no marker handling needed (it does not render —
  AK-10 class cannot fire). It only READS world matrices + depsgraph.
- Placement: after build/load + frame_set, before renders; probe-only
  runs skip the render pass entirely (probe is valid standalone:
  `--probe-cameras` with `--no-grid`-style short-circuit).
- Guard: `scene.ray_cast` needs the evaluated depsgraph — fetch via
  `bpy.context.evaluated_depsgraph_get()` AFTER a `view_layer.update()`
  (the L19 staleness law).

Rejected alternative: viewport_capture.py as the host — the vision
loop's one-invocation tool is look.py; probes belong where the agent
already looks.

### Tests

`tests/test_v7_camprobe.py` (suite convention): fixture scene with a
camera + subject + occluder 1m in front → probe names the occluder
with the smaller distance; a clear camera → `clear` row; the manifest
carries the rows. Runs the real scripts as subprocesses
(`--python-exit-code` convention like test_r9_chunking).

## Value order (restated)

1. D-TD20 (protects every subsequent Blender pipeline this session)
2. D-TD21 (API for the next film's glow surfaces; vendor duty)
3. D-TD22 (kills the recession forensic class for the next film)

## REV-2 — the peer-review folds (2 fresh-context reviewers, both ADOPT-WITH-CHANGES)

### D-TD20 folds
- **[P0] fd-9 inheritance**: Xvfb + blender children must CLOSE the lock
  fd (`exec 9>&-` in a subshell around each spawn) — otherwise
  KEEP_XVFB=1 leaves the lock held by the persistent Xvfb and the next
  sequential run deadlocks-by-refusal. Acceptance gate: the
  KEEP_XVFB-twice test.
- **[P0] blrun.sh IS on the vendor manifest**
  (tools/shared_manifest.json:28-32, owner=kit, byte-identical in
  escape) — the port duty is: patch agent-kit (owner) → sync_shared.py
  --emit → --to escape → commit both. Vision/crowd edits duty-free.
- **[P1] insertion point**: immediately after `XSOCKET=…`, before the
  stale-lock block, ALL repos; agent-kit additionally moves its
  `--version` short-circuit up beside `--help` (it would otherwise
  acquire the lock pointlessly).
- **[P2] exit 90** (verified unused) + greppable marker
  `[blrun] LOCK-HELD on <display> holder=<stamp>` — exit 3 stays the
  kit's "gate failed" semantic. Tests assert the MARKER, not just rc.
- **[P2] contention test uses a real run** (--help exits pre-lock).
- **[P2] /tmp hygiene**: open failure → distinct error + hard exit
  (never confuse EBADF with contention); refuse a symlinked lockfile.
- **[P2] BLRUN_FORCE=1**: skips lock AND stamp (never clobber the real
  holder's stamp), loud WARN naming both failure modes.
- crowd-kit patch is verbatim-safe (CWD conventions verified).

### D-TD21 folds
- **[P1] no existing make_material tests** — new files:
  agent-kit tests/test_t7_material.py, vision-kit tests/test_v8_material.py
  (v7 belongs to the camprobe).
- **[P1] emission_strength is a DIRECT write** (raise if input absent —
  the 4.0/4.1 window is real per escape assets_characters.py prior art;
  a swallowed KeyError = silent glow absence, the exact anti-class).
  try/KeyError stays ONLY for "Emission Color" (genuinely absent pre-4.x).
- **[P1] drop the impossible 3.x-simulation test** — replace with a
  5.2.2 precondition assert + test the guarded helper with a plain fake.
- **[P2] assertion hygiene**: non-white base (0.20,0.55,0.95) so the
  5.x white default can't fake-pass; existence-before-read; epsilon;
  diffuse_color stays base even when emission_color differs; strength
  defaults 0.0.
- **[P2] film twin**: re-apply emission kwargs when the material
  ALREADY exists (get-or-create currently silently drops them).
- **[P2] verified no-render-change** on the default pin (all in-repo
  strength-raisers already pin/overwrite/override); escape's retired
  scripts/__init__.py shim keeps the old signature (stated, not synced).

### D-TD22 folds
- **[P0] the dep.update() ritual**: constraint-driven (track-to) cameras
  return STALE matrix_world with only view_layer.update() — the kit's
  own occlusion_gate.py:212-220 measured law. Probe ritual:
  frame_set → view_layer.update() → evaluated_depsgraph_get() →
  dep.update() → read matrix_world → scene.ray_cast(dep, …).
- **[P1] render-hidden hits are carried, not dropped** (Street.Mist
  law, contact_audit.py:158-167): each row carries render_hidden bool
  (hide_render/hide_viewport/visible_camera/scale); bounded re-cast
  (~8) from hit+eps reports the first RENDERED hit, hidden kept as
  context. The agent decides.
- **[P1] exact slot**: immediately after look.py:252 (the re-pin
  double-update), BEFORE sync_display_colors (258) and
  build_annotation_layer (280) — annotation meshes are real geometry a
  ray would hit first. Filter ANNOT_PREFIX + temp_ names defensively.
- **[P1] probe-only = probe flags + `--angles none`** (the real render
  skip; --no-grid does NOT skip renders) + guard annotation/color-sync
  on non-probe-only.
- **[P1] fixture occluder is a GROUND-STANDING wall** (a floating plane
  trips the validator's floating P1 → exit 3 breaks the test).
- **[P2] single `--probe-camera` flag, repeatable + comma-split +
  'all' sentinel** (matches --angles convention); unknown name →
  status:"missing" row, never an exit; exit codes untouched (exit 3 may
  co-occur with successful probes — documented + docstring lie fixed).
- **[P2] ray_cast contract pinned from prior art**: 6-tuple, no-hit
  sentinel maps to null fields, forward = (mw.to_3x3() @ Vector((0,0,-1))).normalized()
  (the col[2] negation trap), distance = (loc-origin).length.
- **[P2] tests**: v-series subprocess convention + --factory-startup +
  timeout >= 600; manifest schema change verified safe (no strict
  consumers; "manifest" unwrap unaffected).
