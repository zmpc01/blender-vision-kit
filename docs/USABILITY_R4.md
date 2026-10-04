# USABILITY_R4.md — dog-food study, export/previz lane (session 6)

> Same protocol as R1–R3: owner = vision agent, consumer seat, docs-only
> navigation, frictions logged as they bite, kit fixes land immediately.
> Ran after the R3 (EEVEE lane) fixes on the same sandbox.

## Scenario

Ship arc on the R3 turntable scene (animated, EEVEE-verified):
`export_gltf` → viewer HTML → `keyframe_contact_sheet` →
`export_previz_package`. Goal: the #7 "Ship" step of the AGENTS.md
workflow, end to end, with my eyes on every artifact.

## Friction log

### F9 (R4) — required-arg discovery
`export_previz_package --help` prints in-Blender; the missing
`--package-id` error is fine, but nothing in AGENTS.md documents the
previz-package lane at all (only glTF/viewer/save_blend appear in the
ship arc). Logged as a DOC GAP; the tool reference in AGENTS.md gained a
pointer. (Minor.)

### F10 (R4, MAJOR) — export_previz_package was crowd-only and half-broken
Three distinct defects surfaced on the first template-family scene:
1. `animate(ctx, start_frame=1, n_frames=None)` — an explicit None
   crashes the documented template contract
   (`animate(ctx, *, start_frame=1, n_frames=24)` → TypeError). Fixed
   with an inspect-based bridge: integer default → call bare (module's
   own timeline wins, the tool reads frame_start/end after); otherwise
   pass the crowd sentinel.
2. `ctx["scene"]` — crowd modules add a scene key to their ctx dict;
   template-family ctx dicts carry object refs only → KeyError. Fixed:
   `ctx.get("scene") or bpy.context.scene`.
3. Fail-closed gates assumed crowd artifacts: gate 3 indexed `shots[0]`
   (IndexError when the scene declares no SHOTS table — template scenes
   never do); gate 5 demanded a characters registry unconditionally.
   Both are now lane-aware: gates fire when the scene DECLARES the
   corresponding concept (SHOTS/BOARD/RUN_PARAMS), pass vacuously
   otherwise.
VERDICT after fixes: `OK: all gates green` on the turntable scene —
previz.json (1 camera, 2 actions) + scene.glb produced. The tool is now
dual-lane (crowd + template).

### F10b (R4, BLOCKER — pre-existing, bit every run of ANY scene)
Gate 14 called `_glb_prop_proximity_audit(gltf, blob, fps)` but the
variable is `glb_blob` (refactor leftover): NameError on EVERY
execution, crowd scenes included. The tool could not have completed a
single run since that rename. Fixed (`glb_blob`). Lesson: the tool had
no regression suite and no consumer since session-26 — the "0 shots"
path and the gate tail were both unexercised. R4's dog-food pass IS the
coverage that was missing; a t10 package-export suite is now a
candidate.

### F11 (R4, visual, D15 parity gap) — contact sheet stripped ALL color
`keyframe_contact_sheet` workbench path used `color_type='OBJECT'`
(shows obj.color — default white-gray) so every prop rendered the same
gray regardless of materials; the D15 sync lives only in look.py.
Fixed to the kit doctrine (MATERIAL + sync_display_colors/restore).
Visual verify: red/green/yellow/chrome all read true across the 6
sampled frames; orbit + slider motion legible.

## What worked (kept)

- `export_gltf --scene r3_turntable --frames 24` — one shot, 59 KB GLB
  with camera + both animations; no surprises.
- Viewer pattern (`cp viewer/index.html`) + GLB — standard model-viewer,
  worked as documented.
- export_previz_package's fail-closed gate philosophy held up: after the
  lane-compat fixes, the gate tail reads clean and names every check.
- keyframe_contact_sheet's sampling + labeling + PIL stitch — solid.

## Ship-arc verdict

The AGENTS.md #7 ship arc is now consumer-complete for template-family
scenes. The one structural gap left is coverage (F10b lesson): the
export/previz tools have no in-Blender regression suite — candidate
t10 for a future session (small: turntable scene → package export →
assert gates green + artifacts exist).
