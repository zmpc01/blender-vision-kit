# WAVE 4A — Consumer Usability Test Findings (Task 4-c)

> **METHODOLOGY SUPERSEDED (session-4 course correction):** this wave ran
> through a VLM bridge because the consumer sub-agent could not see
> images. That pattern is RETRACTED — the kit is for vision-native
> agents only; non-visual agents belong to upstream blender-agent-kit.
> The code-level findings below (F1 --frames BLOCKER, F2+ friction) were
> produced by script execution and textual assertions and remain valid;
> any *visual* verdicts in this file are superseded by the principal's
> own eyes.

Agent: consumer vision agent (no orchestrator knowledge; AGENTS.md as sole manual).
Date: 2026-09-29. Blender 5.2.2 LTS, kit @ post-6efe702 checkout.
Scope: author+study an animated scene (Task A), debug `t7_wave4_debug` from tool
output only (Task B). Kit scripts and AGENTS.md untouched; only additions are
`scripts/w4a_scene.py` and this file. Outputs under `output/w4a_scene/` and
`output/t7_wave4/`.

---

## 1. What was done (terse command log)

### Task A — author + study `w4a_scene`
```bash
cp scripts/scene_template.py scripts/w4a_scene.py   # then edited build_scene/animate
# Scene: 3 props on a 20m ground, 24 frames (f1..f24):
#   SliderCyl (blue cylinder) slides -X->+X, LINEAR
#   BobSphere (orange sphere) bobs z+0.9 twice, BEZIER EASE_IN_OUT (keys f1,7,13,19,24)
#   SpinCube  (green cube)  spins 360deg Z in place, LINEAR
./scripts/blrun.sh --background --python scripts/w4a_scene.py -- \
    --output output/w4a_scene --dry-run --scene-name w4a_scene         # PASS, 7 objs, 1..24
./scripts/blrun.sh --background --python scripts/look.py -- \
    --scene w4a_scene --output output/w4a_scene/look                   # VERDICT: PASS, P0=0 P1=0 P2=0
z-ai vision --prompt "..." --image output/w4a_scene/look/grid.png      # VLM bridge
./scripts/blrun.sh --background --python scripts/save_blend.py -- \
    --scene w4a_scene --blend-out output/w4a_scene/w4a_scene.blend     # authored-range state carrier
./scripts/blrun.sh --background --python scripts/motion_study.py -- \
    --load-blend output/w4a_scene/w4a_scene.blend --start 1 --end 24 \
    --out output/w4a_scene/motion24                                    # correct study
z-ai vision --prompt "..." --image output/w4a_scene/motion24/motion_grid.png
```
Result: validator PASS at f1 pose; motion table (corrected run) = SliderCyl
median-step 0.522m, BobSphere 0.450m, SpinCube "static" (spin invisible to a
center-displacement table — known L5 blind spot). No POP-/BURST-MOTION lines.
VLM read of trajectory/onion views matched the numbers after cross-check
(see FRICTION F6 for what didn't match).

### Task B — debug `t7_wave4_debug` (source NOT read; tool output only)
```bash
./scripts/blrun.sh --background --python scripts/transient_scan.py -- \
    --scene t7_wave4_debug --start 1 --end 40 --out output/t7_wave4/scan
./scripts/blrun.sh --background --python scripts/motion_study.py -- \
    --scene t7_wave4_debug --start 1 --end 40 --out output/t7_wave4/motion
./scripts/blrun.sh --background --python scripts/motion_study.py -- \
    --scene t7_wave4_debug --start 1 --end 40 --objects Door,Table,Crate,Lamp,Hover \
    --out output/t7_wave4/motion5                                      # after noticing top-3 cap
./scripts/blrun.sh --background --python scripts/look.py -- \
    --scene t7_wave4_debug --frame 15 --angles none --closeup Lamp \
    --output output/t7_wave4/confirm_lamp_f15                          # VERDICT FAIL P0=1 P1=3
./scripts/blrun.sh --background --python scripts/look.py -- \
    --scene t7_wave4_debug --frame 23 --angles none --closeup Crate \
    --output output/t7_wave4/confirm_crate_f23                         # VERDICT WARN P0=0 P1=2
z-ai vision on closeup_Lamp.png, closeup_Crate.png, scan/suspects.png
```

---

## 2. Defects found in `t7_wave4_debug` (as the TOOLS reported them)

Scan: 40 frames, EVENT-TABLE (peak pixel-diff ranked) + PERSISTENT section;
cross-checked against motion-study numeric tables and two full-res closeups.

### TRANSIENT #1 — Lamp intersects Table (the big one)
- Scan EVENT #1: window f11..f20, peak f11 (diff 0.529). States:
  `P0 intersection (Table,Lamp) f12..f18`, `P1 intersection (Table,Lamp)
  f11..f19`, `P1 floating (Lamp) f11..f19`.
- Read: the Lamp falls/flies during f11..f19, lands INSIDE the table
  (overlap >=30% of the smaller volume = P0 phase f12..f18), then clears by f20.
- Confirmation (look f15, mid-P0-window): VERDICT FAIL, P0=1 P1=3; closeup
  shows yellow label "4" (Lamp) with the red validator flag wireframe forming a
  bright red rectangle around a tabletop surface that swallows the lamp —
  lamp geometry inside the table, exactly the planted state.
- Cross-tool: motion study tracked Lamp only after `--objects` override (default
  top-3 cap excluded it) → then `Lamp: median-step 0.000m BURST-MOTION
  (max-step 0.225m, rest static) <-- sampled transient, run transient_scan.py`.
  Consistent.

### TRANSIENT #2 — Crate teleport pop at f23
- Scan EVENT #3: single-frame f23, diff 0.259, no semantic state attached.
- Cross-tool: motion study numeric table flags `Crate: POP-FRAMES [(23, 2.375)]
  <-- suspect transient` (sampled 2.375m position jump ending at sample f23).
  Both tools independently name f23 — CONSISTENT.
- Confirmation (look f23 closeup): crate itself is clean and grounded at f23
  (a teleport is positional; the pop frame pose looks normal — only the
  before/after pair reveals it). Suspects strip row e2 (f23/f23/f23) shows the
  yellow object shifted right-to-left between cells.

### TRANSIENT #3 — unattributed burst f28..f30 (weakly resolved)
- Scan EVENT #2: f28..f30, peak f30 (diff 0.278), no semantic state attached.
- Motion table: `Door: median-step 1.050m` (the big mover); scan PERSISTENT
  `floating (Door) f11..f29`. Best inference: Door motion phase ending/reversal
  around f29-f30. NOT visually confirmed (not required); pixel-diff events carry
  no object attribution, so this one stays a ranked suspect, not a verdict.

### PERSISTENT (baseline design, not transients)
- `P1 floating (Hover) f1..f40` — object "Hover" floats for the entire range.
- `P1 floating (Door) f11..f29` — Door floats through most of its travel window.
- Both ignored by the EVENT-TABLE by design (present in most frames) — the
  duration classification worked as documented.

### Full-res verdicts during confirmation
- f15: FAIL (P0=1 = the Table/Lamp intersection; P1=3 = Lamp/Door/Hover floats)
- f23: WARN (P0=0; P1=2 = Door + Hover floats)

---

## 3. FRICTION LOG (brutally honest, chronological)

| # | Sev | Where | What happened |
|---|-----|-------|---------------|
| F1 | FRICTION | blrun.sh env | `.blender-home` symlink is BROKEN (targets `/home/z/work/blender-agent-kit/.blender-home`, which does not exist). EVERY blrun invocation spews 5-6 stderr lines: `mkdir ... File exists` x2, pulse secure-dir fail, shader-cache disable x2, gl-shader-cache open fail; save_blend adds a thumbnail write fail. Nothing breaks, but the noise trains you to ignore stderr, and the shader cache is silently OFF (gotcha 3's warm-cache cannot work). AGENTS.md gotcha 61b documents this exact signature but the shipped checkout still ships broken. |
| F2 | **BLOCKER** | motion_study.py `--scene` path | Rebuild hardcodes `mod.animate(ctx, start_frame=1, n_frames=64)` (line 320). My 24-frame scene was silently re-timed to 64 frames: keys re-placed (BobSphere's last bob leg stretched f19->f64), table computed over 1..64, samples [1,10,19,28,37,46,55,64] — numbers that are simply WRONG for the authored scene, with nothing in the output flagging it. I only caught it because the header said "frames 1..64" and I knew I authored 24. Same hardcoded-64 rebuild exists in transient_scan.py (line 69). AGENTS.md's tool reference shows `--scene my_scene` as a valid invocation and never warns; only the canonical workflow's `--load-blend` path is safe. A consumer who skips save_blend gets silently-wrong motion truth on a documented path. |
| F3 | FRICTION | motion_study default object cap | Default tracks top-3 non-ground meshes. t7 has 5 meshes -> Lamp and Hover silently dropped; the first motion table had NO trace of the scan's biggest transient (event #1) — looked like a cross-tool inconsistency until I re-ran with `--objects Door,Table,Crate,Lamp,Hover`. Output prints a count ("tracking 3 objects"), never the ids or who was excluded (you learn the ids only from the table rows, and absence is invisible). |
| F4 | FRICTION | VLM bridge (as eyes) | (a) On my PASS scene the VLM asserted the sphere "floats significantly above the ground with a gap" — validator said P1=0 and z=r exactly; forced pairing caught the hallucination (the floating yellow label billboard is the likely trigger). (b) Axis naming is sloppy: called the vertical axis "Y" in a front elevation and "positive Z" in a top view — L2 chirality hazards. (c) Described the red validator wireframe as physical "bright red trim/edge" geometry. (d) On the tiny suspects-strip cells it confused colors/objects (blue slab, purple sphere — no such props per manifest) and merged rows. Every disagreement was resolvable ONLY because the numbers were printed beside the images. |
| F5 | NIT | EVENT-TABLE semantics | Event #1 lists BOTH `P0 intersection (Table,Lamp) f12..f18` AND `P1 intersection (Table,Lamp) f11..f19` as separate rows with no note that these are nested severity phases of one overlap. Also "peak f11" is the PIXEL-DIFF peak while the P0 state window is f12..f18 — confirming "at the peak" would have landed one frame before the P0 phase; I confirmed at f15 instead. Doc doesn't spell out peak-vs-state-window. |
| F6 | NIT | look.py HINT | `SUBJECT-OVERFLOW (cluster diag 28.3m/34.2m > visible ~3.5m)` fires on EVERY look including `--angles none --closeup` where framing is auto and irrelevant — the 20m ground inflates the cluster diag. Doc itself says "ground overflowing the frame is fine", yet the hint counts it. Noise. |
| F7 | NIT | MOTION-TABLE expressiveness | `SpinCube: static` while the cube spins 360deg — the table is center-displacement-only and gives zero rotation signal (no rotation-delta column, no caveat in the output). Doc knows filmstrips hide spin (L5); the numeric table hides it too. |
| F8 | NIT | defaults/doc mismatch | Dry-run prints `engine: CYCLES`, `quality: preview` as script defaults, while AGENTS.md's preset table says preview = EEVEE 640x360. Harmless on the look/motion path (workbench forced) but a consumer reasoning about render cost from the summary would mis-budget. Plus a `DeprecationWarning: 'Material.use_nodes'` from motion_study.py:81 — the kit's own gotcha 18 prescribes `ensure_use_nodes`; one shipped tool doesn't follow it. |
| F9 | NIT | transient_scan `--out` vs docs | AGENTS.md tool reference writes `--out output/my_scene/scan` for transient_scan but shows no equivalent flag name for motion_study in the reference line (only in the workflow example). Both accept `--out`; the reference line for motion_study (`--start/--end --samples 8 --objects A,B`) omits `--out`/`--res` — I guessed `--out` from the sibling tool. Right guess, but it was a guess. |

Positives worth keeping: blrun cold start ~10-15s, 40-frame scan rendered in
~11s; look.py verdict/manifest/readiness/labels worked first try on both
scenes; annotations + validator numbers beside images (forced pairing) caught
every VLM error; the scan->motion_study->look.py closeup pipeline found all
planted defects without reading the fixture source; exit codes and VERDICT
lines behaved exactly as AGENTS.md claims.

---

## 4. Kit improvement suggestions (ranked)

1. **Fix the hardcoded `n_frames=64` `--scene` rebuild in motion_study.py and
   transient_scan.py** (BLOCKER F2). Rebuild scripted scenes with the module's
   own default frames (or probe-render f1 to read authored range), and/or print
   a loud `REBUILT WITH n_frames=64 — script default differs` banner. Silent
   re-timing produces confidently wrong motion numbers on a documented path.
2. **Motion study: name the tracked set and the dropped set** (F3, F7).
   Print `tracking 3: Door, Table, Crate (excluded: Lamp, Hover — pass --objects)`;
   consider auto-including scan-flagged objects; add a rotation-delta column so
   spin is not reported as "static".
3. **blrun doctor / self-heal the `.blender-home` symlink** (F1): one-time
   check at startup — recreate or re-point the symlink, mkdir the target, print
   ONE clean warning instead of six stderr lines per run, restore shader cache.
4. **(bonus) Closeup framing for interpenetrated objects + hint hygiene** (F4c,
   F6): when `--closeup` targets a validator-flagged object, frame the flagged
   PAIR (partner from the audit/validator state) so a swallowed object is
   visible; suppress SUBJECT-OVERFLOW when the ground plane dominates the bbox
   or in closeup-only mode.

---

## 5. Was the VLM bridge + numbers pairing sufficient?

Yes, with the pairing being the load-bearing half. The VLM produced one
confident hallucination (floating sphere on a PASS scene), persistent axis
sloppiness, and small-cell misreads; in every case the numeric output printed
beside the image (validator P0/P1, manifest centroids, MOTION-TABLE rows,
EVENT-TABLE windows) settled the call within seconds. Vision triage composed
the question; the gates decided the answer — the two-column law worked exactly
as advertised. A purely-visual agent without the paired numbers would have
filed at least one false defect (the "floating" sphere) and mislabeled an
annotation as geometry.
