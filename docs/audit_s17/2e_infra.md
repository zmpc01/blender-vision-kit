# 2e — INFRASTRUCTURE AUDIT (read-only) — blender-vision-kit @ 2c19f6c

Auditor: Task 2-e. Scope: install.sh, scripts/blrun.sh, tools/sync_shared.py (governed sync —
see F2E-14 for where it actually lives), scripts/render_daemon.py + scripts/daemonize.py,
run.sh, viewer/ contract, tests/ harness conventions, vendor/ provenance.
Constraints honored: SKILL.md laws (reaping §L181, daemonize double-fork §L271-272,
per-display flock §L274-276, watchdog revert §L247).

**Severity key**: P0 = fresh-clone bootstrap fails / documented path corrupts state ·
P1 = wrong result on plausible input / fail-open · P2 = friction / stale claims / missing
coverage · P3 = nit.

---

## P1 FINDINGS

### F2E-1 · P1 · blrun.sh read-only-checkout fallback is DEAD CODE (the U2 fallback can never fire)
- **Where**: `scripts/blrun.sh:42` vs `scripts/blrun.sh:53-56`
- **Excerpt**:
  - L42: `BLENDER_HOME="${BLENDER_HOME:-$KIT_ROOT/.blender-home}"`
  - L53: `if [[ ! -w "$KIT_ROOT" && -z "${BLENDER_HOME:-}" && ! -w "$BLENDER_HOME" ]]; then`
- **Why**: L42 has already substituted the default, so `${BLENDER_HOME:-}` is **never empty**
  by the time L53 evaluates it — `-z "${BLENDER_HOME:-}"` is unconditionally false and the
  whole fallback (`BLENDER_HOME=/tmp/blender-home`, "kit checkout not writable — using …")
  is unreachable. On a read-only checkout (the documented usability round-1/U2 scenario the
  branch was written for), `mkdir -p "$BLENDER_HOME/.cache/blender"` at L190 fails (no
  `set -e`, so it just prints), `HOME` stays pointed at an unwritable dir, and the shader
  cache is silently disabled — exactly the wave-4a "silent cache loss" symptom class the
  stale-symlink heal at L47-50 exists to kill.
- **Fix**: capture user intent *before* defaulting, e.g.
  `BLENDER_HOME_EXPLICIT="${BLENDER_HOME:+1}"` at the top; then
  `if [[ -z "${BLENDER_HOME_EXPLICIT:-}" && ! -w "$KIT_ROOT" ]] && { BLENDER_HOME=/tmp/blender-home; … }`
  — or simply test writability of the *computed* default: `[[ ! -w "$BLENDER_HOME" && ! -w "$KIT_ROOT" ]]`.

### F2E-2 · P1 · install.sh: `set -euo pipefail` × `pipefail` kills the chunked-download fallback; the empty-BL_SIZE error branch is unreachable
- **Where**: `install.sh:14` (`set -euo pipefail`), `install.sh:61-73`
- **Excerpt**:
  - L61: ``BL_SIZE="$(curl -sIL --max-time 20 "$BL_URL" | grep -i content-length | tail -1 | tr -d '\r' | awk '{print $2}')" ``
  - L66-71: `else … if [[ -z "$BL_SIZE" ]]; then echo "[install] ERROR: couldn't read Content-Length …"; exit 1; fi; bash "$TOOLS_DIR/chunked_dl.sh" …`
- **Why**: the substitution inherits `pipefail`; any HEAD failure (timeout rc=28, refused
  connection, or a 200 **without** a Content-Length header → `grep` exits 1) makes the
  assignment's status nonzero, and `set -e` aborts install.sh **before** the `[[ -z
  "$BL_SIZE" ]]` guard at L68 can run. The result: on the exact hostile/stalling network
  this section was built for (D11 comment, L57-60), bootstrap dies with **no message** and
  the chunked fallback + its loud ERROR are dead code. The design intent (empty size →
  loud error / fallback) is defeated by the shell options.
- **Fix**: make the probe failure explicit and non-fatal, e.g.
  `BL_SIZE="$(curl -sIL --max-time 20 "$BL_URL" 2>/dev/null | grep -i content-length | tail -1 | tr -d '\r' | awk '{print $2}' || true)"`
  (the `|| true` covers the whole pipe), or wrap in `if ! BL_SIZE=$(…); then BL_SIZE=""; fi`.

### F2E-3 · P1 · `scripts/daemonize.py` — the documented ONLY background survivor — does not exist in the tree
- **Where**: referenced by `.agents/SKILL.md:271` ("daemonize.py (double-fork) is the ONLY
  background survivor; it chdirs '/'"), `HANDOFF.md:119-120` ("`python3
  scripts/daemonize.py <ABSOLUTE log> bash -c "cd <repo> && bun run dev"` — daemonize.py
  chdirs to '/'…"), `HANDOFF.md:199`, `worklog.md:3415,3494,3581`.
- **Evidence**: `Glob /home/z/**/daemonize.py` → **0 hits** anywhere under /home/z (both
  repos checked); `tests/test_kit_scope.py` passes because absence matches no forbidden
  pattern. `scripts/render_daemon.py` exists and contains its own private `daemonize()`
  (render_daemon.py:27-38), but the generic launcher every doc points at is gone.
- **Why**: a fresh clone following the documented comment-db / dev-server escape path gets
  `python3: can't open file 'scripts/daemonize.py': [Errno 2] No such file or directory`.
  The skill law ("absolute paths + `bash -c`") also documents behavior (chdir "/") that no
  in-tree file performs — the ONLY double-fork that exists (render_daemon.py:27-38) does
  **not** chdir (see F2E-9 context) and is render-specific.
- **Fix**: restore `scripts/daemonize.py` (double-fork + `os.setsid()` + `os.chdir("/")` +
  fd closure + absolute-log enforcement) or rewrite SKILL.md/HANDOFF.md to name the actual
  survivor (`render_daemon.py`) and delete the dev-server recipe.

### F2E-4 · P1 · render_daemon.py: resuming with `--first-chunk N` destroys the already-rendered chunks
- **Where**: `scripts/render_daemon.py:96-102` (unconditional wipe) vs `:105` (resume loop) and `:130-137` (range-limited count)
- **Excerpt**:
  - L100-102: `for old in (_glob.glob(os.path.join(out_abs, "frame_*.png")) + _glob.glob(os.path.join(out_abs, "frame_*.jpg"))): os.remove(old)`
  - L105: `for i in range(args.first_chunk, args.chunks):`
- **Why**: the stale-frame cleanup was added for review 16-b P0-1 (scratch-dir mixing in
  the shot_pipeline flow), but it is applied unconditionally to `out_abs` — which per the
  module's own usage docstring (L11-13: `--output output/cornell`) is the FINAL output dir
  in standalone use. A chunk failure at chunk 3 of 4 followed by the natural resume
  (`--first-chunk 3`) deletes every frame chunks 0-2 already wrote to that dir, then the
  final heartbeat counts only `[start, start+frames-1]` — completed work silently gone,
  `status:"done"` with `frames_done` covering only the tail. Contradiction in the same
  file: L130-131 explicitly says the count must be "ONLY this run's range -- not stale
  files", while the wipe throws away exactly that distinction on disk.
- **Fix**: wipe only the frame range this run will produce, e.g. compute
  `[args.start + args.first_chunk*per, args.start+args.frames-1]` and delete only
  `frame_%08d` in that window (or wipe only when `first_chunk == 0`).

### F2E-5 · P1 · sync_shared.py `--to <non-previz consumer>` rewrites the canonical manifest and backflows owner:previz files into the kit
- **Where**: `tools/sync_shared.py` (canonical copy lives at
  `/home/z/repos/blender-agent-kit/tools/sync_shared.py` — NOT in this repo; see F2E-14):
  L582-583, L629-630, L296-299, L200-204, L536-547.
- **Excerpt**:
  - L582-583: `src_root = root if owner == "kit" else target` / `dst_root = target if owner == "kit" else root`
  - L629-630: `previz_root = target if os.path.basename(target) != "blender-agent-kit" else None` → `rc = emit(root, previz_root, DEFAULT_BLENDER)`
  - L296-299: emit **writes** `<kit>/tools/shared_manifest.json` (the canonical record).
- **Why**: "previz" is auto-defined as *whatever --to target you passed*. Pointing
  `--to` at any second consumer (e.g. `/home/z/repos/blender-vision-kit` — a plausible
  misreading of HANDOFF.md:50 "port the preflight … via tools/sync_shared.py governed
  sync", or HANDOFF.md:555's generic "--to <consumer>") does three governed-state
  mutations at once: (a) the canonical manifest is re-emitted describing **kit↔vision-kit**
  (shared set = intersection; prior kit↔escape-previz entries without a `note` are dropped
  per L200-204 with only a NOTE), (b) for `owner:"previz"` entries the copy direction is
  consumer→kit (L582), so with the vendored record absent (first_sync=True, L536) +
  `--bootstrap` the kit's `scripts/assets_ual_actors.py` is **overwritten with the
  variant's bytes**, and (c) the rewritten record is vendored to the target (L633-634),
  after which the real escape-previz consumer's record can never classify cleanly again.
  The only gate is `--bootstrap` (L544-547), whose message (L538-543) asserts the
  operator verified *the consumer* holds no un-ported changes — it never discloses the
  backflow into the kit or the canonical-manifest rewrite.
- **Fix**: pin the governed pair: refuse `--to` targets whose basename is not the
  registered consumer (a constant, not basename-detection), or add an explicit
  `--consumer <name>`; when `target !=` the registered consumer, refuse with the blast
  radius spelled out; never copy owner:`previz` files into the kit unless the target IS
  the registered consumer.

---

## P2 FINDINGS

### F2E-6 · P2 · blrun.sh never validates BLENDER_KIT_LIBS — fresh-clone EEVEE degrades with no named warning
- **Where**: `scripts/blrun.sh:63,187` (binary validated at L66-70; libs not)
- **Excerpt**: L187: `export LD_LIBRARY_PATH="$BLENDER_KIT_LIBS:${LD_LIBRARY_PATH:-}"`
- **Why**: blrun hard-fails (exit 127) when the Blender binary is missing but silently
  prepends a nonexistent `tools/local-libs/usr/lib/x86_64-linux-gnu` to LD_LIBRARY_PATH.
  A fresh clone that skips install.sh (or whose libEGL extraction half-failed — QA-R69's
  dangling-symlink signature) gets Xvfb up, blender launched, then an opaque EEVEE/EGL
  failure instead of the kit's named-error doctrine. The kit's own convention (every other
  failure here is named, exit-coded) is broken for this one input.
- **Fix**: after L63: `if [[ ! -f "$BLENDER_KIT_LIBS/libEGL.so.1" ]]; then echo "[blrun] WARN: libEGL.so.1 missing at $BLENDER_KIT_LIBS — EEVEE will fail; run install.sh" >&2; fi` (warn, don't exit — Cycles/Workbench don't need it).

### F2E-7 · P2 · install.sh header says "Downloads Blender 4.5 LTS" while the default is 5.2.2
- **Where**: `install.sh:4-5` vs `install.sh:11-12,17`
- **Excerpt**: L4-5: `# Downloads Blender 4.5 LTS (supported until July 2027)`; L17: `BLENDER_VERSION="${BLENDER_VERSION:-5.2.2}"`
- **Why**: the bootstrap surface's own header contradicts its default and
  ADR_BLENDERVERSION.md (Accepted: ship 5.2.2 LTS). An agent reading only the header may
  pin `BLENDER_VERSION=4.5.x` or mis-report the toolchain. The per-line env doc (L11-12)
  is correct, so this is precisely the "stale claim" class.
- **Fix**: update L4-5 to "Downloads Blender 5.2.2 LTS (until July 2028); BLENDER_VERSION
  override supported (compat shim covers 4.5.x)".

### F2E-8 · P2 · install.sh dangling-symlink heal can materialize real dirs inside a SHARED symlinked tools/ tree
- **Where**: `install.sh:92-96`; context `tests/test_kit_scope.py:167-171` (D12: "tools/ may be a SYMLINK to a shared provisioned toolchain")
- **Excerpt**: L92-96: `if [[ -L "$TOOLS_DIR/local-libs" && ! -e "$TOOLS_DIR/local-libs/" ]]; then rm -f "$TOOLS_DIR/local-libs"; fi; mkdir -p "$LOCAL_LIBS"`
- **Why**: when `tools/` itself is a symlink into the shared toolchain, `$TOOLS_DIR/local-libs`
  resolves inside the SHARED tree; the QA-R69 heal deletes the dangling link there and
  `mkdir -p` creates **real** directories owned by this checkout — polluting the shared
  provisioned toolchain every sibling checkout binds (the exact cross-checkout state the
  D12 note warns git checkouts create). The heal itself is right for the real-tools/ case;
  it is unguarded for the shared-symlink case. Watchdog interplay: if a checkout rewrites
  the tree mid-install (the QA-R69 trigger), the downloaded .debs and created dirs can land
  in a location a subsequent checkout reverts — idempotent on re-run, but the shared-tree
  mutation persists.
- **Fix**: heal only when `tools/` is NOT a symlink (`[[ ! -L "$TOOLS_DIR" ]]`), else print
  the D12 warning and point at the shared toolchain's own local-libs.

### F2E-9 · P2 · render_daemon.py: every post-fork failure is silent (stderr → /dev/null; heartbeat frozen); refused-lock path included
- **Where**: `scripts/render_daemon.py:35-38` (dup2 devnull), `:77` (daemonize), `:86-87` (refused path), `:62-70` (write_hb)
- **Excerpt**: L86-87: `write_hb(status="refused_lock_held"); sys.exit(2)` — executed **after** `daemonize()` at L77.
- **Why**: the 16-b P1-8 fix moved the *first* heartbeat write pre-fork (L76), but any
  post-fork failure still dies invisibly: stderr is /dev/null, so an OSError from
  `write_hb` (heartbeat dir removed by /tmp cleanup or watchdog revert mid-run) or an
  unexpected exception leaves the heartbeat frozen at `"starting"`/`"running"` forever —
  the poller's documented contract (`poll: … render_hb.json`, L15) hangs with no signal.
  The lock-refusal path is the concrete instance: if the heartbeat dir is missing, the
  `refused_lock_held` write raises and the refusal itself is never recorded.
- **Fix**: wrap the post-daemonize body in `try/except Exception` → best-effort
  `write_hb(status="daemon_error", error=repr(e))` + dump the traceback to
  `os.path.join(out_abs, "daemon_error.log")` before exiting; create the heartbeat's
  parent dir before daemonize (`os.makedirs(os.path.dirname(args.heartbeat) or "/", exist_ok=True)`).

### F2E-10 · P2 · render_daemon.py `frames_done` mixes frame-NUMBER and frame-COUNT semantics (known P2-15, still live)
- **Where**: `scripts/render_daemon.py:124-126` vs `:137`
- **Excerpt**: L126: `write_hb(status="chunk_done" …, frames_done=done, …)` where
  `done = min(args.start + (i + 1) * per - 1, …)` is a frame NUMBER; L137:
  `write_hb(status="done", frames_done=len(frames))` is a COUNT.
- **Why**: filed as P2-15 in worklog.md:960 and never fixed; any automation keying on
  progress (percent-done, ETA) computes nonsense: mid-run 432 then drops to a count.
  Two different units under one key is a fail-open telemetry bug.
- **Fix**: split keys: `frames_done` = count of rendered frames in range (glob+filter as
  L132-134 already does, per chunk), `last_frame` = number.

### F2E-11 · P2 · tests harness: no full-battery runner; suite_runner.sh is a stale 6-suite subset and its "fully detached-safe" claim contradicts the reaping law
- **Where**: `scripts/suite_runner.sh:2,5-14`; `docs/battery_s16_results.md:5` (manual convention)
- **Excerpt**: suite_runner.sh L2: `# suite_runner.sh — sequential regression runner, fully detached-safe.`; L6-8 hardcodes `test_t1_states… test_t5_physics … x1_detection_matrix` (6 suites) vs the 26-suite battery (battery_s16_results.md rows 1-26: v1-v9, f17/f22, r7/r8/r9, t10×2, usd, t8, t9, plus t1-t5/x1).
- **Why**: (a) the battery is enumerated **manually** (battery doc: "Runner: `./scripts/blrun.sh --background --python <suite>` … (foreground, 600s timeout each)") — nothing in-tree enumerates it, so every battery run re-derives the list by hand (the doc is the only source, and it already disagrees with suite_runner); (b) suite_runner's header promises detachment, but SKILL.md §L181 (the reaping law) says background processes are killed between tool calls — `touch /tmp/suite.done` (L14) as a completion sentinel only works if the runner survives, which it doesn't; the runner must be foregrounded with a long tool timeout, which the header discourages; (c) new suites never got added, so "run suite_runner" silently skips 20 suites.
- **Fix**: make suite_runner.sh enumerate the battery (explicit ordered list matching battery_s16_results.md, with per-suite expected markers), drop the detached-safe claim, document foreground + timeout in the header.

### F2E-12 · P2 · vendor wheel provenance honest but incomplete: no integrity pin, no license, unverifiable source in this sandbox, and the README's install.sh cross-reference is wrong
- **Where**: `vendor/blender-crowd/addon/blender_crowd/wheels/README.md:1-15`; wheel `blender_crowd_native-1.5.5-cp311-abi3-manylinux_2_34_x86_64.whl`
- **Evidence (measured)**:
  - sha256 `166ce6a13a0f147231f34d095029e516f381c24432108f40ae6e487befd3a151`, size 17,932,638 bytes — recorded **nowhere** (README has no hash/size).
  - Wheel dist-info METADATA (full dump): `Metadata-Version: 2.4 / Name: blender-crowd-native / Version: 1.5.5 / Classifier: Programming Language :: Rust / Requires-Python: >=3.11` — **no License, no Author, no Home-page**; WHEEL: `Generator: maturin (1.9.6)`.
  - README L4-6: "Source: blender-crowd-kit `vendor/…/wheels/` (the same relative path…)" — but no `blender-crowd-kit` checkout exists in this sandbox (`ls /home/z/repos` → only blender-agent-kit, blender-vision-kit), so the chain cannot be verified locally, and no source-repo commit is pinned.
  - README L14-15: "straight into Blender's bundled python with BLENDER_PY (install.sh resolves it)" — install.sh resolves BLENDER_PY **for Pillow only** (install.sh:141-217); it has no wheel-install step at all.
- **Why**: F-TF5's "governed re-vendor" (USABILITY_TF1_last_ferry.md:62-71, USABILITY_S16_session16.md:36-37) is governed by convention only: a corrupted or silently-swapped 17.9 MB binary wheel would pass every gate (sync_shared governs `scripts/*.py`, never the wheel — manifest at blender-agent-kit/tools/shared_manifest.json contains no wheels entry). A binary blob in git with no hash, no license statement (in README or wheel), and no upstream origin is the weakest link in an otherwise provenance-conscious kit.
- **Fix**: append to README: measured sha256 + byte size + source repo commit + the maturin/Rust origin; add a License section (or a LICENSE file beside the wheel); correct the install.sh cross-reference ("resolve the python with `BLENDER_PY=… install.sh`'s probe output" — or add an install.sh `--crowd-wheel` step so the claim becomes true).

### F2E-13 · P2 · install.sh: a set-but-not-executable BLENDER_PY silently falls through to probing a *different* python (F-TD9 class resurfaces)
- **Where**: `install.sh:157-160` vs `:161-173`
- **Excerpt**: L157: `if [[ -n "${BLENDER_PY:-}" && -x "${BLENDER_PY:-}" ]]; then` → else L161 probes `BLENDER_BIN`, else L168 probes `tools/blender`.
- **Why**: if the operator exports `BLENDER_PY` and it fails `-x` (typo, version-stale path, or pointing at a `python3.x-config` shim), the script silently probes the *blender binary* and installs Pillow into whatever that resolves — recreating the exact "Pillow lands where Blender never looks" F-TD9 failure this section was rewritten to kill (comment L148-155). The override should be authoritative-or-loud, not authoritative-or-ignored.
- **Fix**: `elif [[ -n "${BLENDER_PY:-}" ]]; then echo "[install] ERROR: BLENDER_PY=$BLENDER_PY is not executable — fix it or unset it" >&2; exit 1`.

---

## P3 FINDINGS

### F2E-14 · P3 · tools/sync_shared.py is not in this repo (docs' "kit tools/sync_shared.py" is accurate but consumer-side surfaces are absent in the variant)
- **Where**: `HANDOFF.md:50,555`, `docs/DESIGN_FTD_trio.md:105,177` say "kit tools/sync_shared.py"; this repo's `tools/` contains only `chunked_dl.sh`. The tool lives at `/home/z/repos/blender-agent-kit/tools/sync_shared.py`.
- **Why**: correct as written ("kit" = blender-agent-kit, the owner repo; vision-kit is the VARIANT per SKILL.md:11-13), but nothing in vision-kit (`scripts/check_shared_sync.py`, `scripts/shared_manifest.json` — both absent) gives a reader of this repo a drift surface for the ~dozens of script files the variant shares with the kit. The planned preflight port (HANDOFF.md:50) is also a **non-owner→owner** direction sync_shared cannot perform (it copies owner→consumer only; port-back is manual + `--emit`).
- **Fix**: one line in HANDOFF.md:50 clarifying the port is manual (sync_shared only re-vendors owner→consumer afterwards), or vendor the checker+record.

### F2E-15 · P3 · sync_shared `--to` ignores `--blender`; `validated_blender` is hardcoded 5.2.2 on that path
- **Where**: blender-agent-kit/tools/sync_shared.py:630 (`emit(root, previz_root, DEFAULT_BLENDER)`) vs :836 (`--blender` flag) — the flag is only honored on the `--emit` path (:847).
- **Fix**: `emit(root, previz_root, args.blender)`.

### F2E-16 · P3 · sync_shared emit's sibling-missing NOTE promises "manifest emitted from the kit tree alone" but the run actually REFUSES (correctly) on OWNER-MISSING
- **Where**: blender-agent-kit/tools/sync_shared.py:180-182 (NOTE) vs :212-218 (refuse when `previz_root is None` and any OWNER_PREVIZ entry exists — `scripts/assets_ual_actors.py` always qualifies).
- **Fix**: reword the NOTE to "sibling not found — emit will refuse on OWNER-MISSING unless no previz-owned entries exist".

### F2E-17 · P3 · blrun warm-cache leaks its temp script and uses a fixed collision-prone render path
- **Where**: `scripts/blrun.sh:214` (`WARM_SCRIPT="$(mktemp /tmp/blender_warm_XXXX.py)"`, never rm'd) and `:229` (`filepath = '/tmp/_blender_warm.png'`).
- **Fix**: `trap 'rm -f "$WARM_SCRIPT"' EXIT` in the warm-cache branch (before the final `exit`); render to a mktemp path.

### F2E-18 · P3 · chunked_dl.sh hardcodes 16 parts in the concat list; small files break; dl_errors.log never cleaned
- **Where**: `tools/chunked_dl.sh:26-29` (cat of exactly part_00…part_15), `:6` (rm list omits dl_errors.log), `:12` (chunks with `S > E` exit 0 **before creating their part file**, so `cat` fails for TOTAL < 16 chunks' worth).
- **Fix**: `rm -f part_* dl_errors.log "$OUT"`; build the cat list from created parts (`cat part_*` is NOT safe — use printf'd ordering of existing parts).

### F2E-19 · P3 · viewer/index.html: dead pointer to `viewer-three.html`; exporter-lane packages have no metadata.json so the info panel is always "No metadata.json found" there
- **Where**: `viewer/index.html:132` ("see `viewer-three.html` in the same directory" — no such file; viewer/ = index.html, live.html, index.html.notes.md); contract check: writer `scripts/blender_kit/__init__.py:818-839` emits exactly the keys the viewer reads at index.html:168-180 (`scene, engine, resolution, samples, frame_range, camera, camera_lens_mm, objects, render_time_seconds, blender_version`) — **the render-lane contract is CLEAN**; but the canonical export lane (`scripts/export_previz_package.py:4-27`) writes `scene.glb + previz.json (+sfx_events.json)` and **no metadata.json**, so pairing the viewer with an export package (the "standard loop", export_previz_package.py:44-46) loses the whole info panel (graceful: index.html:157-165 catch → 'No metadata.json found').
- **Fix**: drop the viewer-three.html sentence; optionally have export_previz_package emit a minimal metadata.json (or teach the viewer to render previz.json's provenance block).

### F2E-20 · P3 · test harness fragile fallbacks and naming drift
- **Where/evidence**:
  - `tests/test_t6_add_ops.py:346,369`: `[os.environ.get("BLENDER_BIN") or sys.argv[0], "--python-use-system-env", "--background", …]` — under `python3 tests/test_t6_add_ops.py` (no BLENDER_BIN), `sys.argv[0]` is the test file itself → subprocess nonsense; works only under the documented "run under blrun" convention with no error explaining that.
  - Suite naming mixes `test_*` with `t9_chaos_fuzz.py` and `x1_detection_matrix.py` — any future `tests/test_*.py` glob-based runner would silently miss 2 suites; suite_runner.sh compensates by hardcoding (see F2E-11).
  - `tests/test_usd_carrier.py:251-253,351`: conditional `SKIP: bpy.ops.wm.usd_export not available` / `SKIP: pxr not importable` — the pxr half will always skip in the bundled python on this sandbox (no BlenderUSD pxr bindings importable outside builds that ship them); printed, not silent, but the battery verdict counts the suite PASS with a permanently-skipped half — worth a "SKIPPED:" verdict class in the battery doc.
- **Fix**: fail loud when neither BLENDER_BIN nor a blender-looking argv[0]; adopt one naming convention or keep the enumerated runner authoritative.

### F2E-21 · P3 · blrun traceback gate can fail-close on honest output
- **Where**: `scripts/blrun.sh:275-280` — greps both streams for `Traceback (most recent call last|IndentationError:|SyntaxError:|NameError:|TypeError:|AttributeError:` and forces exit 1.
- **Why**: a script that *prints* an expected-error string (validators echoing a caught TypeError, docs-grep tooling) is forced nonzero despite success. Escape hatch exists (`BLRUN_NO_TRACEBACK_GATE=1`, L275) and the bias is deliberately fail-closed, but any new gate-printing script will trip it mysteriously. Consider matching only `^Traceback` at line-start in the tee'd raw stream, or requiring the pattern to appear without a preceding `[blender]`-script tag.
- **Fix**: anchor the Traceback pattern to line-start; document the false-positive class next to the escape hatch.

### F2E-22 · P3 · run.sh --scope-check passes a stray empty arg
- **Where**: `run.sh:16`: `exec python3 "$REPO/tests/test_kit_scope.py" "${2:-}"` — always passes one arg (empty string when absent); `test_kit_scope.main()` ignores argv so it's harmless, but any future argv use will see a phantom `''`.
- **Fix**: `exec python3 "$REPO/tests/test_kit_scope.py" "$@"` after shifting, or drop the arg.

### F2E-23 · P3 · install.sh install.sh's python glob fallback can pick a `python3.NN-config` shim if the bundled bin/ ships one
- **Where**: `install.sh:176`: `ls "$TOOLS_DIR"/blender/*/python/bin/python3.* | sort -V | tail -1` — the glob matches any `python3.*` entry, including `python3.NN-config` (which sorts last under `-V` and is executable). Unverified against a real 5.2.2 tarball in this sandbox (no such file observed either way), so conditional — but the failure mode (config shim "runs" `-m pip` as flag-printing shell script → 3 retries → hard ERROR exit) is a fresh-bootstrap killer if present.
- **Fix**: filter to interpreter-looking names only: `for p in …python3.[0-9]*; do [[ -x $p && $p != *-config ]] && echo $p; done | sort -V | tail -1`.

---

## WHAT I CHECKED AND FOUND CLEAN

1. **blrun.sh per-DISPLAY flock (F-TD10)** — blrun.sh:85-110: symlink refusal (L86-89), open-fd-9 + `flock -n` (L91-105), holder stamping (L106), BLRUN_FORCE bypass with a loud warning (L107-110), exit 90 on all lock paths. Matches AGENTS.md:237-243 and SKILL.md:274-276 exactly. Lock fd correctly closed in BOTH subshells (`exec 9>&-` at L138 for Xvfb and L266 for blender), so KEEP_XVFB=1 reuse and SIGKILLed-blrun cannot inherit-and-hold the lock.
2. **Xvfb lifecycle** — readiness waits on the real socket (L143-160), early-death detection, SIGKILL escalation in cleanup (L169-182), stale X-lock removal keyed on `xvfb_running()` pgrep (L121-129), trap on EXIT/INT/TERM/HUP preserving the blender exit code. Exit-code propagation via `PIPESTATUS[0]` (L269) is correct (sed/tee cannot mask it).
3. **blrun stale `.blender-home` symlink heal** (L47-50) — matches the wave-4a failure signature; heal-before-use ordering correct.
4. **`--python-use-system-env` threading and `--background` dispatch** — always injected (L266), PYTHONPATH prepended from the script dir (L194-195), HOME override to BLENDER_HOME (L190-191; the Pillow `--user` law at SKILL.md:94-95 holds); GUI-hang guard scans only pre-`--` args (L241-251) so script args can't false-positive.
5. **Warm-cache MemAvailable guards** — identical 2400 MB thresholds and named-skip messages in install.sh:122-134 and blrun.sh:204-212; consistent with QA #2; the skip is loud and non-fatal by design.
6. **install.sh Blender-binary idempotency** — L48-53: BLENDER_BIN override and installed-tree branches both verify `--version | grep` before skipping; re-runs after a completed install are true no-ops (verified live: tools/blender → blender-5.2.2-linux-x64, `Blender 5.2.2 LTS`).
7. **install.sh Pillow authoritative probe order** — BLENDER_PY override → BLENDER_BIN probe (blrun's preferred binary, L161-167, matching blrun.sh:40) → tools/blender probe → sort -V glob fallback; install is idempotent (import check first, L180), 3 retries + verify-after (L186-196), hard-fail with manual recovery on final failure (L200-204), and the can't-resolve path is a loud WARN not an exit (L207-217) — correct for pre-provisioned BLENDER_BIN setups. The multi-interpreter F-TD9 class is genuinely closed for the in-tree flows (the glob resolves through the `tools/blender` symlink, so stale 4.x sibling dirs can't win).
8. **install.sh libEGL section** — existing-file skip (L85), owner-missing final check (L106-109), pinned .deb URLs with the pool-reorg note (L28-33).
9. **run.sh** — faithful thin alias; env-var passthrough semantics match blrun defaults; `--scope-check` path works (ran it: `test_kit_scope: PASS (427 tracked files, all kit-scope)`, exit 0, at HEAD 2c19f6c).
10. **render_daemon.py double-fork core** — fork/setsid/fork ordering correct (L27-32), std streams flushed + redirected before the lock is opened (L33-38), render flock opened **after** daemonize so it lives in the daemon (L80-89, confirmed correct by worklog.md:963), heartbeat write is atomic tmp+`os.replace` (L62-70), pre-fork `"starting"` write kills the stale-heartbeat race (L76, 16-b P1-8), chunk tiling `[start, start+frames-1]` has no gap/overlap (L104-110), `--no-physics`/`--extra` threading sound, chunk subprocess runs via `./run.sh` with `cwd=` repo root (L111-123) so each chunk serializes on blrun's display lock.
11. **sync_shared.py core governance** — classification truth table complete and code-matched (L383-420); three-way guard in `--to` refuses only the unexplainable hand-edit state (L555-576); `--emit` owner-missing + import-closure refusals are fail-closed (L207-265); `--adopt` refuses non-owner bytes when the sibling is observable (L800-807); pre-commit gate is owner-aware and FAIL-CLOSED in the kit repo while best-effort in the consumer (L686-774, PX-21); hook shim is clone-durable (tracked `.githooks/pre-commit` + core.hooksPath, L639-661); `--no-renames` on the staged diff closes the rename bypass (L732-737).
12. **Viewer metadata contract (render lane)** — writer keys (blender_kit/__init__.py:818-839) ≡ reader keys (viewer/index.html:168-180); `src="scene.glb"` matches both the render lane's output conventions and the exporter's package layout; live.html ↔ agent_server.py serve the same producer file (`/api/metadata.json` → same `metadata.json`, agent_server.py:190-193).
13. **Kit-scope guard** — positive/negative pattern controls self-test (test_kit_scope.py:58-143) plus live tree audit: current run PASSES (427 tracked files); the battery's suite-1 failure (`scripts/probe_crowd_bake.py` tracked) is resolved (file now at `smoke/crowd/probe_crowd_bake.py`, outside all `^scripts/` patterns).
14. **Nested-blrun BLRUN_FORCE=1 convention** — all four suites that spawn nested blrun carry it: test_v2_motion.py:204, test_v3_edges.py:57, test_v4_colorsync.py:180, test_v7_camprobe.py:106 (the battery's rc=90 failures that motivated it are fixed in code); direct-binary suites (test_v7_camprobe.py:114, test_t10_export.py:58, test_t6_add_ops.py:346) correctly use `--python-use-system-env` with fixtures under scripts/ per the session-16 law (SKILL.md:321-325).
15. **Suite GPU/EEVEE assumptions** — no suite requires a real GPU; EEVEE suites (t3/t8/t9, v1) run under blrun's Xvfb+libEGL lane and completed on the 4 GB box per battery_s16_results.md; the only conditional skips are test_usd_carrier.py's two printed SKIPs (F2E-20). The warm-cache OOM guard protects the one known memory cliff on this sandbox.
16. **ADR_BLENDERVERSION.md** — internally consistent with install.sh's 5.2.2 default, blrun's EEVEE_ENGINE_ID shim usage (blrun.sh:223-225), and the recorded gpu.init()/Xvfb decision (ADR L125); no stale 4.x assumptions found in the infra layer beyond F2E-7's header.
17. **chunked_dl.sh main path** — per-chunk size verification with 8 retries (L13-17), wait-all + failure aggregation (L23-25), total-size gate before cleanup (L30-31), start-of-run `rm -f part_* "$OUT"` makes re-runs after a killed run safe (no append-corruption).
18. **vendor/ layout honesty** — wheels-only thin vendor claim (README L5-6) matches reality: `vendor/blender-crowd/addon/blender_crowd/wheels/` contains exactly the 1.5.5 wheel + README, no addon sources; the F-TF5 story (1.0.0 → 1.5.5, worklog.md:3708) is consistent across USABILITY_TF1_last_ferry.md:62-71, USABILITY_S16_session16.md:36-37, HANDOFF.md:40-45 — the *completeness* gaps are F2E-12, not dishonesty.

---

## SUMMARY

- **P1 (5)**: F2E-1 blrun dead RO-fallback · F2E-2 install.sh set-e/pipefail kills download fallback · F2E-3 scripts/daemonize.py missing (documented path) · F2E-4 render_daemon --first-chunk resume destroys completed chunks · F2E-5 sync_shared --to rewrites canonical manifest + backflows previz-owned files into the kit.
- **P2 (8)**: F2E-6 unvalidated BLENDER_KIT_LIBS · F2E-7 stale 4.5 header · F2E-8 symlink heal in shared tools/ · F2E-9 silent post-fork daemon death · F2E-10 frames_done unit mix (known, unfixed) · F2E-11 no battery runner / stale suite_runner + detached-safe myth · F2E-12 wheel provenance unpinned/licenseless + wrong install.sh cross-ref · F2E-13 BLENDER_PY set-but-invalid silently re-probes elsewhere.
- **P3 (10)**: F2E-14 sync_shared location/port-direction note · F2E-15 --blender ignored on --to · F2E-16 misleading emit NOTE · F2E-17 warm-cache temp leak · F2E-18 chunked_dl 16-part concat · F2E-19 viewer-three dead ptr + no metadata.json on export lane · F2E-20 test fallbacks/naming/usd skips · F2E-21 traceback-gate false positives · F2E-22 run.sh empty arg · F2E-23 python-config glob risk.
- **No P0 found**: the documented fresh-clone bootstrap (`clone → bash install.sh → blrun`) works end-to-end on this sandbox (tools/ provisioned 5.2.2, kit-scope PASS); the P1s are failure-path holes around it, not its mainline.
