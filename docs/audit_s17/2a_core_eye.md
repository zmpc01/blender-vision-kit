# 2-a — Core Eye Audit (look.py / annotate.py / viewport_capture.py / image_metrics.py / blrun.sh)

Repo: /home/z/repos/blender-vision-kit · Auditor: Task 2-a (READ-ONLY) · Scope: the render/verify "core eye" pipeline + blrun.sh interplay.
Method: full read of the five scoped files; cross-reads of `validate_scene.py`, `blender_kit/__init__.py`, `tests/test_v1_look.py`, the F-TD3 ledger (HANDOFF.md, USABILITY_TD1_vision_film.md, PLAN.md, worklog.md), the in-lane marker-safe tools (`tdawn_flowstrip.py` et al.), and the marker-creating film modules. No files were modified except this report.

Severity: P0 = crash/data-loss/silent-wrong-render on a documented path · P1 = wrong result on plausible input, or gate that fails open · P2 = friction/doc-lies/missing coverage/stale claims · P3 = nit.

---

## P0

### F2A-1 — F-TD3 marker-camera hijack: look.py / viewport_capture.py render the WRONG camera on marker-bound scenes, silently, exit 0
**Where:** `scripts/viewport_capture.py:228-237` (the unprotected camera swap; reached from every `look.py` render: `scripts/look.py:443-446, 461-464, 489-493`).
**Code:**
```python
# Temporarily swap the scene's active camera
orig_camera = scene.camera
scene.camera = cam
try:
    bpy.ops.render.render(write_still=True)
finally:
    scene.camera = orig_camera
    if cleanup:
        cleanup()
```
**Exact mechanism (verified, corrected vs. the lead):** Blender's render pipeline resolves the render camera from **camera-bound timeline markers** — the marker at-or-before the render frame wins over `scene.camera`. `render_angle()` swaps `scene.camera` to the temp cam but performs **zero marker suppression**, so on any scene with bound markers every "front/side/top/persp" panel silently renders the marker's shot camera instead. The hijack is not name-based: creation/cleanup of temp cams is strictly **by object reference** (`viewport_capture.py:85-99, 102-129`), and no code in the kit looks objects up by the `temp_` pattern in order to *delete or bind* them (only exclusion, see F2A-5). The real marker vector is:
- Marker-creating scene modules (documented `--scene` targets and canonical `--save-blend` → `--load-blend` carriers): `scripts/scene_terminal_dawn.py:225-226` (11 × `CAM_S*` markers, first at frame 1 — look.py's default frame is `scene.frame_start`, so **every panel** resolves to CAM_S1), `scripts/scene_last_ferry.py:246-247`, `scripts/scene_green_light.py:285-286`.
- Ledger corroboration: HANDOFF.md:260-263 ("F-TD3 … look.py is still vulnerable on marker-bound scenes"), HANDOFF.md:417 (QA #11: measured `meanAbsDiff 0.002` between the "front" and "persp" panels — pixel-identical — captions still say front/persp, manifest healthy, no per-panel camera recorded), docs/USABILITY_TD1_vision_film.md:52-61 ("look.py REMAINS VULNERABLE"), plus the `scene.camera`-mutation wrinkle: clearing `marker.camera` mutates `scene.camera` (tdawn_flowstrip.py:61-63 "observed: it fell back to the last shot cam").
**Why it matters:** the multi-angle grid is the kit's spatial ground truth; on the film modules it is silently one (or several wrong) shot cams with healthy readiness/validator headers and exit 0 — the exact "silent-wrong-render on a documented path" class, flagged OPEN by two ledger docs.
**Fix design (minimal, in-repo proven pattern from `tdawn_flowstrip.py:54-63`):** in `render_angle`, before the swap:
```python
saved_marks = [(m, m.camera) for m in scene.timeline_markers if m.camera]
for m, _c in saved_marks:
    m.camera = None
orig_camera = scene.camera
scene.camera = cam            # re-assert AFTER the sweep (marker clearing mutates scene.camera)
try:
    bpy.ops.render.render(write_still=True)
finally:
    scene.camera = orig_camera
    for m, c in saved_marks:  # restore bindings
        m.camera = c
    if cleanup: cleanup()
```
Add observability so a future hijack is detectable: record the intended camera name per panel in `look_manifest.json` (QA #11 noted "no per-panel camera recorded"). Optional hardening against the residual name-collision class: module-level registry of created temp cams + random-UUID name suffix (see F2A-5).

---

## P1

### F2A-2 — 0-byte / truncated PNG + exit 0: the eye's only write guard is `os.path.exists`, and readiness errors don't gate the exit code
**Where:** `scripts/viewport_capture.py:239-240` (guard), `scripts/look.py:497, 533-541` (error printed), `scripts/look.py:581-582` (exit gated **only** on validator P0/P1 counts).
**Code:**
```python
if not os.path.exists(out_path):
    raise RuntimeError(f"Render failed silently — no output at {out_path}")
```
and in look.py, readiness rows that failed to open are printed but never affect the exit:
```python
for r in ready:
    ...
    if "error" in r:
        print(f"[look] image {r['path']} readiness-error: {r['error']}")
    else:
        print(f"[look] image ...")
...
if (p0 or p1) and args.fail_on_issues:
    sys.exit(3)
```
**Why it matters:** the exact "0-byte PNG + exit 0" class. A render whose file is *created* but fails mid-write (ENOSPC, killed writer, `bpy.ops.render.render` returning CANCELLED after printing `Error:` rather than raising) passes the exists-only guard; `image_readiness()` then returns `{"path", "error"}` (viewport_capture.py:305-306), look.py prints one readiness-error line among many, the verdict block still prints, `look_manifest.json` is written, and the run **exits 0** with an unreadable image on disk. A downstream agent treats the look as authoritative. Grid mode partially self-defends (PIL raises inside `stitch_contact_sheet`), but `--no-grid`, single-angle, and closeup paths do not.
**Fix:** (a) in `render_angle`, after the render require `os.path.getsize(out_path) > 0` and a PNG magic header (`\x89PNG\r\n\x1a\n`), raising otherwise; (b) in `look.py`, treat any readiness row containing `"error"` as a hard failure → exit non-zero (suggest 4, distinct from 3), and record `"write_verified": true` in the manifest.

### F2A-3 — Temp cameras never configure clip planes: `--closeup` of small props renders near-plane-clipped geometry (and large scenes can far-clip), silently
**Where:** `scripts/viewport_capture.py:80-99` (`_add_temp_camera` sets only `lens`; factory defaults `clip_start=0.1m`, `clip_end=100m` stand), `scripts/look.py:481-483` (closeup distance math).
**Code:**
```python
cam_data = bpy.data.cameras.new(name=f"{name}_data")
cam_data.lens = lens
...
diag = obj.dimensions.length or 0.5
dist = diag * args.closeup_fill                     # default fill 1.5
closeup_loc = (cx + dist*0.85, cy - dist*0.85, cz + dist*0.6)   # |offset| ≈ 1.344·dist ≈ 2.02·diag
```
**Why it matters:** camera-to-nearest-surface for the closeup ≈ `2.02·diag − diag/2 ≈ 1.5·diag`; with the untouched 0.1 m near clip, any object with diagonal ≲ 7 cm (screws, gems, handles, board-game props — plausible `--closeup` targets) has its near side **behind the near plane**: the "macro" render shows a cut-open/inside-out object with a healthy verdict and exit 0 (readiness only flags if the result is near-black/near-empty). Symmetrically, `clip_end=100m` is never widened, so scenes with >100 m camera-to-far-edge spans lose far geometry (no in-repo scene demonstrably exceeds 100 m — noted as hardening, not measured loss).
**Fix:** set clip planes on the temp camera from the distance: `cam_data.clip_start = max(0.001, 0.02 * dist_to_target)` and `cam_data.clip_end = max(100.0, 3 * (origin - target).length)`; alternatively floor the closeup distance (e.g. `max(dist, 0.35m)`) *and* scale `clip_start`.

---

## P2

### F2A-4 — Annotation layer leaks its MESH datablocks: `delete_annotation_layer` purges objects/materials/curves but not meshes; the zero-residue test's docstring claims it checks meshes and doesn't
**Where:** `scripts/annotate.py:165` (mesh creation), `scripts/annotate.py:340-367` (deletion), `tests/test_v1_look.py:5` vs `:33-40, 64-66` (coverage gap).
**Code:**
```python
mesh = bpy.data.meshes.new(name)      # name = "KIT_ANNOT_grid_x0" etc.   (annotate.py:165)
...
for mat_name in list(bpy.data.materials.keys()):     # materials purged (353-358)
...
for curve_name in list(bpy.data.curves.keys()):      # curves purged (361-366)
```
`_annot_residue()` in the test returns `(names, mats, curves)` — `bpy.data.meshes` is never checked, though the test docstring promises "objects, meshes, materials, curves".
**Why it matters:** a 20 m scene leaves ~40+ zero-user `KIT_ANNOT_*` mesh datablocks per look run, in-session forever. The D5 law ("render-time only, never saved") currently holds only because no kit flow builds annotations and then saves in one process (`apply_patch.py` renders via `render_angle` only, no annotation build; `apply_patch.py:245-273` vs saves at `:1280/:1290`). The first consumer that does both inherits a saved-blend annotation residue. The test also documents coverage it does not have (doc-lies class).
**Fix:** add to `delete_annotation_layer`: purge `bpy.data.meshes` keys starting with `ANNOT_PREFIX` (same pattern as the curve loop), and extend `_annot_residue()` to include `bpy.data.meshes`.

### F2A-5 — Prefix-marker identity collisions (residual F-TD3 name-marker class): objects named `temp_*` or `KIT_ANNOT_*` vanish from manifest/labels/flags/probe while still rendering — image/manifest divergence
**Where:** `scripts/look.py:139` (probe), `scripts/look.py:154, 405-406, 501-502` (manifest/labels/verdict), `scripts/annotate.py:200-201` (annotation build), contrast `scripts/semantic_lib.py:79-81` (namespace already declared reserved).
**Code:**
```python
# look.py:137-141 — probe 'all' silently skips ANY camera whose name starts with "temp_"
cams = [o for o in scene.objects if o.type == 'CAMERA'
        and not o.name.startswith("temp_")
        and not o.name.startswith(annotate.ANNOT_PREFIX)]
# look.py:154 — manifest: annotation layer is render-time only, never manifest
if o.name.startswith(annotate.ANNOT_PREFIX): continue
```
**Why it matters:** a user camera literally named `temp_front_cam` (plausible: agents copy kit naming conventions) is silently excluded from `--probe-camera all`; a user mesh named `KIT_ANNOT_foo` renders in every image but is absent from the manifest, label ranking, flag boxes, and the verdict object count — the manifest the next patch keys on diverges from the image the agent sees. No deletion/binding hijack exists today (cleanup is by reference — verified `viewport_capture.py:102-129`), but identity-by-prefix is the same root pattern the ledger files as F-TD3/AK-10.
**Fix:** replace prefix matching with side-data/registry: `viewport_capture` keeps a module-level `_TEMP_CAMERAS` set of created camera objects (and `annotate` already returns its exact object list in `layer["objects"]`) consumed by look.py's probe/manifest filters; add a random-UUID suffix to temp-cam names (`temp_front_cam_<8hex>`) to make accidental collision-to-exclusion implausible; keep the prefix only as a debug greppability aid.

### F2A-6 — Readiness thresholds are hardcoded and uncalibrated, and the grid image's readiness header is meaningless: flags flip on plausible correct renders (calibration-law miss)
**Where:** `scripts/viewport_capture.py:288-298` (`image_readiness`), `scripts/look.py:497` (readiness computed on the **stitched grid**, not the per-angle files).
**Code:**
```python
clipped = float((luma >= 0.98).mean() * 100.0)
dark    = float((luma <= 0.08).mean() * 100.0)
corners = (a[2,2] + a[2,-3] + a[-3,2] + a[-3,-3]) / 4.0
subj    = float((np.abs(a - corners).sum(axis=2) > 0.25).mean() * 100.0)
...
if clipped > 25.0: flags.append("BLOWN-OUT")
if dark > 40.0:    flags.append("NEAR-BLACK")
if subj < 1.5:     flags.append("NEAR-EMPTY")
```
**Why it matters:** (a) `look.py` grid mode computes readiness **only on `grid.png`** (look.py:450-469 builds tmp per-angle files, then discards them) whose corner pixels are the sheet's navy background `(20,20,24)` — `subject_pct` is inflated toward 100% and per-angle BLOWN-OUT/NEAR-EMPTY never reach the agent; (b) the constants flip on correct content: workbench STUDIO + the default +1.0 EV on a high-key interior can legitimately exceed 25% clipped (`_warn_if_clipped` already documents 5.x EEVEE brightness drift vs. 4.5 at viewport_capture.py:245-249), night/dawn scenes (tdawn is literally one) legitimately exceed 40% dark, and legitimately sparse scenes trip NEAR-EMPTY. These are advisory (never gate the exit — correct), but the kit's own doctrine (L3 overlay-trust, "readiness headers printed BESIDE the images") makes uncalibrated flags friction that pushes agents to "fix" correct exposure.
**Fix:** compute per-angle readiness inside the grid-mode `TemporaryDirectory` block and include per-angle rows in `look_manifest.json` (keep the grid row for continuity); make thresholds engine/exposure-aware (e.g. raise the clipped bar by the applied EV, or gate BLOWN-OUT on `clipped > 25 AND luma_mean > 0.9`); skip subject-coverage on stitched composites.

### F2A-7 — viewport_capture's fresh-build path violates the kit's own stale-depsgraph law: no `view_layer.update()` before `_compute_scene_center` → the whole capture can orbit a stale target
**Where:** `scripts/viewport_capture.py:67-77` (no update), `:434-447` (called directly after `build_scene()`/`animate()`), contrast `scripts/look.py:148-151` ("matrices/bound_box are evaluated lazily — right after in-process mutation they are STALE") and `scripts/look.py:349-355` (the double-update ritual).
**Code:**
```python
def _compute_scene_center() -> Tuple[float, float, float]:
    """Compute the bounding-box center of all mesh objects in the scene."""
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    ...
    for corner in o.bound_box:                       # lazy-evaluated, may be stale
        world = o.matrix_world @ type(o.location)(corner)
```
**Why it matters:** `bpy.ops`-driven builds happen to flush the depsgraph, but any scene module that finishes via the data API (`bpy.data.objects.new` + `matrix_world`/ parenting / `keyframe_insert` in `animate()`) leaves `bound_box`/`matrix_world` lazy-stale — the kit's own law and look.py's in-file citations (`prop_carry.py:53`, world_bbox law) say exactly this. Result: `target` is wrong → every temp camera and the track-to empty aim at the wrong point → all panels misframed with healthy headers. `look.py`'s path is safe (frame_set flush at `:299-302` + double update at `:352-355`); only `viewport_capture.py` main is exposed.
**Fix:** begin `_compute_scene_center` with `bpy.context.view_layer.update()` (double, per the kit law) before reading matrices.

### F2A-8 — blrun's fail-closed traceback gate: incomplete pattern list (fails open for non-traceback script failures) and false-positive-prone patterns
**Where:** `scripts/blrun.sh:270-280`.
**Code:**
```bash
if [[ -z "${BLRUN_NO_TRACEBACK_GATE:-}" ]] \
        && { grep -qE "Traceback \(most recent call last|IndentationError:|SyntaxError:|NameError:|TypeError:|AttributeError:" "$BLRUN_OUT" \
          || grep -qE "...same list..." "$BLRUN_ERR"; }; then
    echo "[blrun] FAIL-CLOSED: Python error in output — forcing nonzero exit" >&2
    [[ "$EXIT_CODE" -eq 0 ]] && EXIT_CODE=1
fi
```
**Why it matters:** (a) fails open for the plausible script-failure shapes that don't print a traceback: an uncaught `ValueError`/`KeyError`/`RuntimeError` *are* caught (any raised exception prints a `Traceback (most recent call last` header — that first alternative covers all raises), but bpy-op failures return CANCELLED and print `Error: ...` with **no traceback**, and a script that catches exceptions and exits 0 prints nothing matchable — both exit 0. The eye pipeline patches its own critical instances (F2A-2's exists-guard, exit-3 contract), but general consumer scripts still get a green exit on cancelled-op flows. (b) fails closed wrongly: any legit printed payload containing e.g. `TypeError:` (a validator description, a logged repr) flips a 0 to 1 — annoying, currently no in-repo payload matches.
**Fix:** gate additionally on lines matching `^Error: ` *from the script's own stderr* plus a sentinel protocol (scripts print `KIT_RC=<n>`; blrun takes max(blender rc, KIT_RC)); or at minimum add the remaining builtin exception names to the alternation and document the `Error:`-without-traceback gap in the header comment.

---

## P3

### F2A-9 — `render_angle` mutates global render/shading state and never restores it (only the camera is restored)
**Where:** `scripts/viewport_capture.py:188-226` (engine, resolution, image_settings, workbench `light/color_type/shadows/cavity`, `view_transform='Standard'`, `exposure`, eevee samples, cycles device/samples, `render.filepath`), camera restore alone at `:234-237`.
**Why/fix:** within look.py (single engine per run) this is benign, but `render_angle` is library API (apply_patch.py:268, film tools): a workbench render leaves `view_transform='Standard'` + `exposure` set for every later eevee/cycles render in the same process — silent look shift. Save/restore the touched fields around the render (or expose an explicit context manager), matching the camera-swap discipline.

### F2A-10 — FLAG_CAP comment lies about ordering
**Where:** `scripts/look.py:324-337` — comment says "issue order: P0 first, then largest overlap"; code is `sorted(flagged, key=lambda n: n not in sev0)` over an alphabetically pre-sorted set: P0s first, then **alphabetical**, never overlap-ranked. Fix: sort the P1 tier by the issue's overlap metric or fix the comment.

### F2A-11 — `--angles` help claims `'ring:N'` support that the code doesn't implement
**Where:** `scripts/viewport_capture.py:389-393` ("Or 'ring:N' for N cameras around the scene") vs `:450-462` (only the `--ring N` flag builds a ring); `--angles ring:6` → "unknown angle" exit 1. Fix the help string (module docstring at `:24-26` uses the flag correctly).

### F2A-12 — blrun temp-file leaks: output/error logs not removed on the signal path; warm-cache script never removed
**Where:** `scripts/blrun.sh:169-183` (`cleanup` kills Xvfb but never `rm -f "$BLRUN_OUT" "$BLRUN_ERR"`, which are removed only on the normal path at `:281`), `:214` (`mktemp /tmp/blender_warm_XXXX.py` is never deleted). Fix: trap-safe rm in cleanup; rm the warm script after the run.

### F2A-13 — `look.py` accepts `--angles custom` then emits a misleading error referencing `--custom-loc`, an option look.py does not have
**Where:** `scripts/look.py:426-429` (allows "custom") → `viewport_capture.py:170-172` (`RuntimeError("custom angle requires --custom-loc X,Y,Z")`). look.py's closeup flow is the custom path; the angle loop should reject `custom` with a look-specific message.

### F2A-14 — Annotation grid/gnomon hardcode a z=0 floor and ±1.5 m center offsets
**Where:** `scripts/annotate.py:208-242` (`z_floor = 0.0`, margin 1.0, gnomon at `center - 1.5`). Scenes whose floor is not at z≈0 (floating platforms, elevated decks) get a grid slicing through geometry or hanging in air — an aid that misreads against law L3 (overlay-trust). Fix: anchor the grid to the scene's min-z (or `ground_z` param) and document the assumption.

### F2A-15 — Subject-overflow hint math: `atan` where `tan` is exact; hardwired 5 m offset couples it to VIEW_ANGLES
**Where:** `scripts/look.py:563-572` — `visible = 2*5.0*atan(18.0/lens)` vs. exact `2*d*tan(atan(18/lens))` = `2*d*18/lens` (≈4% underestimate at 50 mm — conservative, benign) — and the literal `5.0`/`18` silently assume the 5 m VIEW_ANGLES radius + 36 mm sensor. Fix: `2*5.0*18.0/lens` and derive both constants from `VIEW_ANGLES`/`camera.sensor_width`.

### F2A-16 — Angle→camera-location math is duplicated in three places that can drift
**Where:** `scripts/look.py:198-208` (`_camera_loc_for_angle`, which annotate's label aim mirrors), `scripts/viewport_capture.py:176-182` (`render_angle`), `scripts/viewport_capture.py:474-477` (vc main). Fix: single helper in viewport_capture used by all three.

### F2A-17 — Stitch/naming nits
`scripts/viewport_capture.py:328` — `imgs = [im.resize((w, h)) ...]` resizes to the first cell **ignoring aspect ratio** (benign for kit uniform renders, distorting for mixed-size inputs). `:487-489` — `--no-grid` with >1 angle and an `output.png`-style path creates a **directory named `output.png`** silently. Fix: aspect-preserving thumbnail; append `_cells/` or error when the multi-file output path looks like a file.

### F2A-18 — No end-to-end test of blrun.sh exit-code propagation (the SKILL.md claim is only half-tested)
**Where:** `.agents/SKILL.md:40` ("look.py exits 3 … blrun propagates them") vs `tests/test_v1_look.py:135-145` — `_run_look` invokes **raw `blender`**, never `blrun.sh`; the wrapper's `PIPESTATUS[0]` + traceback-gate path (blrun.sh:253-280) is untested with a look exit-3 payload. Fix: one subprocess test through `blrun.sh` asserting rc==3 (and rc==90 on a deliberately held display lock).

---

## Checked and CLEAN (coverage for the orchestrator)

- **blrun.sh F-TD10 display lock**: correct — symlink refusal (86-89), fail-fast `flock -n` → **exit 90** with LOCK-HELD holder info (90-105), lock file write for diagnostics (106), BLRUN_FORCE escape with explicit warning (107-110); stale X-lock handling for cases A/B/C (117-129); Xvfb readiness waits on the real socket with 5 s timeout + early-death detection (131-161); fd-9 closed in both the Xvfb subshell (138) and the blender subshell (266) so KEEP_XVFB reuse can't inherit-hold the lock; KEEP_XVFB cleanup guarded so a reuser can't kill a shared Xvfb (169-181); SIGKILL escalation (172-178). Two-pipelines-one-display fails fast at 90 as required.
- **blrun.sh exit-code propagation**: `EXIT_CODE=${PIPESTATUS[0]}` through the `tee|sed` pipeline is correct; traceback gate only ever converts 0→1 (cannot mask a script's exit 3); `--background` injection scans only pre-`--` args, so script args survive intact (241-251).
- **blrun.sh env**: HOME/BLENDER_HOME hygiene incl. dangling-symlink replacement (47-50) and read-only-checkout /tmp fallback (51-56); PYTHONPATH injection (195); LD_LIBRARY_PATH prep (187); `--python-use-system-env` (266).
- **look.py exit-3 contract**: P0 **or** P1 → 3 by default (`--fail-on-issues` default True, 266-271); manifest written before `sys.exit(3)` (575-582); WARN verdict on P1-only; raw-blender rc==3 propagation proven by test_v1_look test_4; operational errors exit 1 with printed reasons (281-282, 427-429, 473-476); no path prints images and returns 0 on validator failure; `--no-fail-on-issues` opt-out is explicit and documented.
- **Annotation lifecycle on all documented paths**: build→render→`finally` delete covers exit 3, sys.exit(1), unknown-angle, and render exceptions (421, 583-587); scene.camera restore in `render_angle`'s finally; display-color sync is standalone (works with `--no-annotate`) and restored unconditionally with originals-gating (392-399, 590-592); zero residue for objects/materials/curves proven by test_v1_look test_1 (meshes: see F2A-4); no save/export path exists in look/vc/annotate; `apply_patch.py`'s render op builds no annotations (no KIT_ANNOT leak into `--save-blend`); `export_preflight.py:994-999` explicitly exempts KIT_ANNOT from the hidden-object gate; `semantic_lib.py:79-81` rejects KIT_ANNOT labels (namespace reservation exists).
- **Camera occlusion probe (F-TD12)**: read-only by construction — no camera creation, no `scene.camera` write (comment 85-88 accurate); depsgraph `dep.update()` **before** the matrix read (91-97); bounded (≤8) re-casts past render-hidden hits that keep the hidden hit as context (107-122); never affects exit codes; `--probe-camera` unknown names become `status:missing` rows, not exits (128-143, 368-372); probe runs after the re-pin double-update and **before** the annotation build (slot law honored, 352-385).
- **Stale-depsgraph discipline on the look path**: `frame_set` + double `view_layer.update()` before annotation/matrix reads (349-355); validator runs after frame_set; `_manifest` re-updates and excludes the annotation layer (146-155); per-row `world_bbox` + always-present `kit_label` (D15/D16 laws, 164-177).
- **Temp camera hygiene**: creation/cleanup strictly by reference — no name-based lookup or deletion anywhere in the kit (grep-verified); camera data removed at 0 users (102-129); cleanup in `finally` even on render exceptions (232-237); original camera always restored.
- **image_metrics.py**: pure functions only (luma/sat_val/sobel_energy/range_stats); **no gates and no hardcoded thresholds** — `p_dark` is relative (`max/3`), denominators guarded; nothing a plausible input "flips". The only flippable constants in the eye live in `image_readiness`/`_warn_if_clipped` and are advisory (F2A-6).
- **stitch_contact_sheet**: deterministic grid math; label strip; PIL→ImageMagick fallback is fail-closed (`subprocess.run(check=True)` propagates); runs inside `tempfile.TemporaryDirectory` (look.py grid mode) so per-angle tmp files are auto-cleaned.
- **CLI validation**: `validate_output` (mkdir + writability) and `validate_resolution` (4×4 min, 8192 max OOM guard) fail fast at entry in both look.py (283, 346) and viewport_capture.py (420-422); `normalize_engine` accepts raw Blender enums and EEVEE typos on both 4.x/5.x (blender_kit/__init__.py:82-118).
- **Validator interplay**: `vs.validate_scene()` is read-only (no frame_set/ray_cast/mutation); `issues_by_severity` keys match look.py's usage; flagged-id extraction covers both `object` and `objects` issue shapes (316-323); FLAG_CAP=60 prevents the measured 4 GB OOM on huge flagged sets (R6).
- **Scene film modules (parallel lane)**: not audited per scope; only KIT-side defects they expose were filed (F2A-1 marker bindings, F2A-6 night-scene threshold flips).
