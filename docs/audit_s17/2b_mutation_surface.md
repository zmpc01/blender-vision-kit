# 2-b — Mutation/Patch Surface Audit (blender-vision-kit)

Scope: `scripts/apply_patch.py`, `scripts/placement_lib.py`, `scripts/semantic_lib.py`,
`scripts/scene_schema.py`, `scripts/blender_kit/__init__.py`, `scripts/scene_template.py`.
Read-only audit; every finding cites file:line + excerpt. SKILL.md was read first and
treated as untrusted (several of its laws are confirmed; several code sites violate them).

Severity rubric: P0 = crash/data-loss/silent-wrong-render on a documented path;
P1 = wrong result on plausible input or fail-open gate; P2 = friction/doc-lies/missing
coverage; P3 = nit.

---

## P0

### F2B-1 — `render_viewport`: documented key `custom_loc` is read as `custom_location` → silent wrong render / broken custom-angle path
- **File**: `scripts/apply_patch.py:267` (handler) vs `scripts/apply_patch.py:1061` (PARAM_DOCS / `--list`), `scripts/viewport_capture.py:170-172`
- **Excerpt**:
  ```python
  # PARAM_DOCS (printed by --list, the discoverable contract):
  "render_viewport": "output:path, angle?(persp|front|side|top|back|right|active|custom), engine?(workbench|eevee|cycles), width?, height?, samples?, target?, custom_loc?",
  # handler:
  custom_loc = params.get("custom_location")
  ```
  and `viewport_capture.py:171`: `if custom_location is None: raise RuntimeError("custom angle requires --custom-loc X,Y,Z")`
- **Why it matters**: two documented paths break. (a) `{"angle":"persp", "custom_loc":[x,y,z]}` → `custom_location` is `None` → the camera lands at the generic scene-center persp orbit; the render **succeeds** with readiness stats, so the agent believes it rendered the requested viewpoint — a silent wrong render. (b) `{"angle":"custom", "custom_loc":[...]}` → hard `RuntimeError` demanding the *CLI* flag even though the documented patch key was supplied. `_warn_unknown_keys` cannot help: `custom_loc` is in the allowed set parsed from PARAM_DOCS, so no warning fires in case (a).
- **Fix**: read both spellings in the handler (`params.get("custom_location", params.get("custom_loc"))`), correct PARAM_DOCS to one canonical key, and make `_warn_unknown_keys` allowed-set generation derive from the handler's real keys (or add a unit test that parses PARAM_DOCS keys against handler `params.get/params[...]` usage).

---

## P1

### F2B-2 — `audit` gate is fail-open: pair ERROR rows (severity="fail") do not set `failed`
- **File**: `scripts/placement_lib.py:610-617, 621-624`; consumer `scripts/apply_patch.py:452-453`
- **Excerpt**:
  ```python
  except Exception as e:  # noqa: BLE001
      reports.append({"a": a.name, "b": b.name, "state": "ERROR",
                      "error": repr(e), "severity": "fail", ...})
  ...
  failed = any(r.get("state") == "PENETRATING" and ... for r in reports)
  ```
  `apply_patch.py:452`: `if params.get("fail_on_penetration", True) and rep["failed"]: raise ...`
- **Why it matters**: AGENTS.md:302 promises "`audit` exits non-zero on penetration — chain after every placement change". A pair that *errors* (e.g. the documented skinned-mesh refusal in `_skinned_guard` raising on an animated crowd mesh, or a non-mesh name in explicit `pairs`) becomes a `severity:"fail"` row that `failed` ignores → audit prints `failed=False`, the chain continues, and real penetrations behind the errored pair are never gated. Violates the kit's own SKILL.md law #10 ("a gate that can't abort the build protects nothing"). The scoped path in `apply_patch.py:425-438` has the same hole (counts only `PENETRATING`).
- **Fix**: `failed = any(r.get("severity") == "fail" or (r.get("state") == "PENETRATING" and ...) for r in reports)` (and the same rule in the scoped recomputation), or make ERROR rows carry `failed=True` semantics explicitly.

### F2B-3 — `place_on` post-contact ERROR rows carry no `severity`, so `ok` stays True and the op prints "OK"
- **File**: `scripts/placement_lib.py:1121-1125`
- **Excerpt**:
  ```python
  except Exception as e:  # noqa: BLE001
      post.append({"a": obj.name, "b": s.name, "state": "ERROR",
                   "error": repr(e)})          # <-- no "severity" key
  report["ok"] = all(p.get("severity") != "fail" for p in post)
  ```
- **Why it matters**: the solver's own verification is fail-open: a post-audit exception yields `severity=None → ok=True` → `apply_patch.py:365-367` prints `place_on: X -> OK` even though the placement could not be verified. Compare `audit_scene`'s ERROR rows which *do* set `severity:"fail"` — the two call sites disagree.
- **Fix**: append `"severity": "fail"` in the except branch (and `"state": "ERROR"` is already there), or compute `ok = all(p.get("severity") != "fail" and p.get("state") != "ERROR" ...)`.

### F2B-4 — `place_on keep_xy=False` is accepted, echoed in the report, and never implemented
- **File**: `scripts/placement_lib.py:826, 884-885 (docstring), 892`; advertised by `scripts/apply_patch.py:1062`
- **Excerpt**:
  ```python
  def place_on(obj, *supports, clearance=0.0, footprint='bottom', mode='rest',
               grid_n=12, inset=0.0, keep_xy=True, ...):
      """...
      keep_xy: True (default) — solves Z ONLY, object stays at its current
      x/y. ... pass keep_xy=False to also move to the support
      height-field's centroid ..."""
  report = {..., "keep_xy": keep_xy, ...}     # only consumer: the report
  ```
- **Why it matters**: `keep_xy` appears in the function signature, in PARAM_DOCS (`--list`), and is echoed into the report as if honored — but no code path reads it after the report write. An agent passing `keep_xy:false` to center a prop over a pedestal gets the object solved at its **current x/y** with `ok:true` — the solver reports success for a state it never achieved (fail-open per the hunt list). This is exactly the "invented API return keys / doc lies" class SKILL.md law #12 warns about, inverted: a documented *input* is a no-op.
- **Fix**: either implement the centroid x/y move when `keep_xy=False` (solve x/y from the support height-field centroid before the z solve) or reject `keep_xy=False` loudly and drop it from PARAM_DOCS.

### F2B-5 — NaN/Infinity unguarded in transform/physics ops; only `add_*` ops enforce the kit's own "json accepts NaN, scenes do not" law
- **File**: `scripts/apply_patch.py:130-131, 143-145, 157-160, 236-238`; `scripts/placement_lib.py:1286`; contrast the guarded path `scripts/apply_patch.py:613-617`
- **Excerpt**:
  ```python
  # add ops (guarded):
  if not math.isfinite(v): raise RuntimeError(f"... must be finite (got {v}) — json accepts NaN/Infinity, scenes do not")
  # set_location (unguarded):
  loc = _require(params, "location", "set_location", expected_type=list, expected_len=3)
  obj.location = tuple(loc)
  # snap_z (unguarded):
  _apply_translation(obj, target_z - cur, override, report)
  ```
- **Why it matters**: `json.loads` happily parses `NaN`/`Infinity`. A single NaN coordinate in `set_location`/`set_scale`/`move_to.target`/`snap_z.target_z`/`set_camera_dof` writes NaN into `obj.location` / `matrix_world` with **no error**; every downstream number (schema bounds, `_aabb`, BVH raycasts, physics, renders) becomes garbage silently. The kit's own add-op docstring states the threat model ("NaN silently passes naive tolerance checks") — the defense was never extended to the ops most likely to receive computed values.
- **Fix**: route all numeric params in mutation handlers through a shared `_finite(v, op, key)` validator (reuse `_add_num`'s isfinite check); reject NaN/Inf at `_require` time with the existing friendly-error style.

### F2B-6 — `seat_at` silently treats any unknown `reference` (incl. documented `centroid`) as origin-anchoring
- **File**: `scripts/placement_lib.py:1162-1171`; docstring `1130-1140`; promised token set `AGENTS.md:314-317`
- **Excerpt**:
  ```python
  if reference == 'bottom':
      ...  # bbox bottom-CENTER lands at the anchor
  else:
      delta = target_loc - obj.matrix_world.translation
      obj.location += delta        # origin path — for EVERYTHING else
  ```
  AGENTS.md:316: "`snap_z`/`seat_at` reference = `bottom` (default) | `origin` | `centroid`."
- **Why it matters**: an agent following AGENTS.md emits `seat_at` with `reference:"centroid"`; there is no validation, so the object is seated by its **origin** while the report records `"reference": "centroid"` — a silent wrong placement with a green report (`ok` only exists when `seat_mesh` is given, and `apply_patch.py:384-385` prints `OK` via `rep.get("ok", True)`). Compare `snap_z`, which at least raises on unknown tokens (see F2B-12).
- **Fix**: validate `reference in ("bottom", "origin", "centroid")` and implement `centroid` (vertex-mean anchor) or reject the token loudly; never fall through silently.

### F2B-7 — `seam_views` PARAM_DOCS signature (`id, supports`) is wrong on every key; the op is unusable from its own documented interface
- **File**: `scripts/apply_patch.py:1067` (PARAM_DOCS) vs `:556-565` (handler); op advertised in `AGENTS.md:296`
- **Excerpt**:
  ```python
  "seam_views": "id, supports",
  ...
  def _apply_seam_views(obj, params):
      a = _get_obj(params["a"], "seam_views")
      b = _get_obj(params["b"], "seam_views")
      rep = _PL.seam_views(a, b, out_dir=params["out_dir"], ...)
  ```
- **Why it matters**: an agent running `--list` (AGENTS.md:344 tells it to) emits `{"op":"seam_views","id":"A","supports":["B"]}` → `KeyError: 'a'` → the friendly converter replies "op 'seam_views' missing/invalid param 'a'; signature: id, supports" — actively pointing the agent back at the wrong keys. Three required keys (`a`, `b`, `out_dir`) are undiscoverable; two documented keys are unused. The handler ignores `obj` while the dispatcher's needs_obj bookkeeping suggests `id` matters.
- **Fix**: correct PARAM_DOCS to `a, b, out_dir, res?, engine?, contact_band_mm?, fill_frac?` (and accept `id`+`supports` as aliases if backward compat matters); add a test asserting every PARAM_DOCS entry names the keys its handler actually reads.

### F2B-8 — World-space solvers still write parent-space deltas (`place_on`/`snap_z`/`seat_at`), the exact defect move_to was already fixed for
- **File**: `scripts/placement_lib.py:718-721` (`_apply_translation`), `:1166-1168` + `:1158` (`seat_at`), `:684-715` (`_rebase_location_keys`); contrast the fixed site `:1249-1251`
- **Excerpt**:
  ```python
  # _apply_translation (place_on/snap_z/refine all go through this):
  obj.location.z += dz
  # move_to's own comment at :1249-1251:
  # world-space write (code-review gate P1: per-component location adds
  # are PARENT-space — a rotated parent silently redirects the move)
  obj.matrix_world = Matrix.Translation(delta) @ obj.matrix_world
  ```
- **Why it matters**: on any parented mover (vendor imports, armature-parented rest-pose figures — `_skinned_guard` only blocks *animated* ones), `location.z += dz` moves along the parent's z, not world z; `seat_at`'s per-component adds and its `rotation_euler = seat_mw.to_euler()` (parent-space write of a world euler) misdirect the same way, and `_rebase_location_keys` then applies a world-space delta to parent-space fcurve values. The post-contact audit catches gross results as `ok:false`, but `apply_patch.py:365-369` only *prints* CONTACT-ISSUES — the patch still exits 0 and `--save-blend` persists the broken state.
- **Fix**: use the move_to pattern (`obj.matrix_world = Matrix.Translation(delta) @ obj.matrix_world`) in `_apply_translation` and `seat_at`; compute rotation writes via `matrix_world` composition; rebase fcurves in parent space or convert the delta first.

---

## P2

### F2B-9 — 5.x multi-slot actions blind the animation guard and the schema; `iter_fcurves` also mutates actions as a read side effect
- **File**: `scripts/blender_kit/__init__.py:148-173` (`iter_fcurves` = `slots[0]` only), `:121-145` (`_scaffold_5x_action` creates slot/layer/strip/channelbag); consumers `scripts/placement_lib.py:644-665, 697`, `scripts/scene_schema.py:106-107`
- **Excerpt**:
  ```python
  slot = action.slots[0]
  fc = action.layers[0].strips[0].channelbag(slot).fcurves   # slot[0] only
  ```
- **Why it matters**: the repo's own session-26 note (`iter_all_fcurves` docstring) says 5.2 slotted actions can serve multiple datablocks with per-slot channelbags. `_guard_anim`/`_location_anim_channels` probe **slot[0]** only, so location keys living in a later slot are invisible → the "placement writes would be clobbered" guard passes and the placement is silently overwritten at the next `frame_set` — the exact failure the guard exists to prevent (fail-open gate, edge input). Separately, calling the read-only-looking `iter_fcurves` on a fresh 5.x action *creates* slot/layer/strip/channelbag as a side effect (e.g. from `_location_anim_channels`), mutating scene state from a getter. `scene_schema._animation_to_dict` is slot[0]-blind too.
- **Fix**: make the guard use `iter_all_fcurves` (read-only, all slots) for *detection*; keep the scaffolding only in explicit creation helpers (`fcurves_new`); document `iter_fcurves` as create-path-only.

### F2B-10 — Systemic: `_warn_unknown_keys` derives "allowed" from stale PARAM_DOCS, printing "(ignored — check spelling)" for params that ARE applied
- **File**: `scripts/apply_patch.py:1086-1105` (mechanism) vs the stale entries it parses: `:1052` (duplicate_object), `:1062` (place_on), `:1066` (audit), `:1069-1072` (physics_*), `:1074/:1076` (add_sphere/add_cone), and the live handlers `:187-192, 357-363, 397-406, 477-547`
- **Excerpt**:
  ```python
  unknown = [k for k in mut if k not in allowed]
  if unknown:
      print(f"[apply_patch] WARNING: op '{op}' got unknown param(s) "
            f"{sorted(unknown)} (ignored — check spelling); ...")
  ```
  e.g. PARAM_DOCS `duplicate_object: "id, new_id"` while the handler honors `location/rotation_deg/scale` (`:187-192`); `place_on` doc omits `grid_n/inset/contact_band_mm` honored at `:357-361`; `physics_settle` doc omits `tol_mm/allow_bake/allow_copy/pad_mm/snap_cap_mm`; `audit` doc omits `sample/contact_band_mm/clearance_pad_mm/force`; `add_sphere` doc omits `ring_count`; `add_cone` doc omits `vertices`.
- **Why it matters**: the warning text asserts the param was **ignored** when it was in fact applied (the module's own top docstring documents `duplicate_object` with `location`!). An agent that trusts the warning removes a live parameter and changes placement semantics silently. The `physics_oracle` case is worse: PARAM_DOCS omits `intended_support`/`frames`/`tol_mm` — all live.
- **Fix**: generate the allowed-key set from a real per-op schema (dict, not prose), share it between `--list`, `_warn_unknown_keys`, and `_require`; or at minimum fix the warning text to "not in the documented signature — it may still be applied; check the handler".

### F2B-11 — `add_torus` `--list` signature says `radius_major/radius_minor`; the handler only accepts `major_radius/minor_radius`
- **File**: `scripts/apply_patch.py:1077` vs `:815-819`; module docstring `:47-48` already uses the correct names
- **Excerpt**:
  ```python
  "add_torus": "id, radius_major, radius_minor, location?(CENTER!), color?",
  ...
  R = _add_num(params, "major_radius", positive=True) or 1.0
  r = _add_num(params, "minor_radius", positive=True) or 0.25
  ```
- **Why it matters**: following `--list` verbatim produces a guaranteed `unknown param(s) ['radius_major','radius_minor']` refusal (loud, and `_add_id` does print the valid set — the only reason this is not P1). PARAM_DOCS also contradicts the module docstring on the same file.
- **Fix**: `PARAM_DOCS["add_torus"] = "id, major_radius, minor_radius, location?(CENTER!), color?"`.

### F2B-12 — `snap_z` reference token `centroid` is documented (AGENTS.md + PARAM_DOCS) but the code implements `center`
- **File**: `scripts/apply_patch.py:1064`; `scripts/placement_lib.py:1284-1285, 1290-1291`; `AGENTS.md:315-316`
- **Excerpt**:
  ```python
  cur = {"bottom": mn.z, "center": (mn.z + mx.z) / 2,
         "origin": obj.matrix_world.translation.z}[reference]
  ```
- **Why it matters**: `{"op":"snap_z","reference":"centroid"}` → `KeyError('centroid')` → converted by `apply_mutation` into "op 'snap_z' missing/invalid param 'centroid'; signature: id, target_z:float, reference?(bottom|origin|centroid)" — the error message re-asserts the token that just failed. Note `move_to` *does* use `centroid` (`placement_lib.py:1229`), so the token sets are inconsistent across sibling ops.
- **Fix**: alias `centroid`→`center` in the two dicts (or rename to `centroid` and fix PARAM_DOCS/AGENTS.md), and validate the reference up front with a kit-style error.

### F2B-13 — `set_material_roughness`/`set_material_metallic` lack every guard their sibling `set_material_color` has
- **File**: `scripts/apply_patch.py:165-174` vs `:148-156`
- **Excerpt**:
  ```python
  def _apply_set_material_roughness(obj, params):
      mat = obj.data.materials[0]                 # no MESH/type/material check
      bsdf = mat.node_tree.nodes.get("Principled BSDF")
      bsdf.inputs["Roughness"].default_value = params["roughness"]
  ```
- **Why it matters**: (a) on a non-mesh (`obj.data` for a light has no `.materials`) → raw `AttributeError`; (b) a material with `use_nodes=False` (4.x default per the kit's own note at `:723` — imports, label flows) has `node_tree is None` → raw `AttributeError: 'NoneType' object has no attribute 'nodes'`; (c) no `ensure_use_nodes` call although the color op calls it; (d) no range check (negative roughness/metallic accepted into the BSDF silently). All four produce raw tracebacks or silent bad values where the color sibling raises clean kit errors.
- **Fix**: mirror `_apply_set_material_color`'s guards (type check, materials check, `ensure_use_nodes`, bsdf None → RuntimeError) and clamp/validate `[0,1]`.

### F2B-14 — needs_obj dispatcher hole: missing `id` calls the handler with `obj=None`; the guard that was written to catch it is dead code
- **File**: `scripts/apply_patch.py:1113-1116`; crash sites e.g. `:130-131`, `:177-178`
- **Excerpt**:
  ```python
  obj = _get_obj(mut["id"]) if needs_obj and "id" in mut else None
  if needs_obj and obj is None and "id" in mut:   # can NEVER fire: _get_obj
      raise RuntimeError(...)                      # raises instead of returning None
  ```
- **Why it matters**: `{"op":"set_location","location":[...]}` (no id) → `_apply_set_location(None, ...)` → `_origin_centroid_warn` swallows the AttributeError internally (`placement_lib.py:781-782`), then `obj.location = tuple(loc)` → raw `AttributeError: 'NoneType' object has no attribute 'location'`. `delete_object` → `remove(None)` TypeError. The user gets an unhelpful traceback instead of the intended "op requires object id" kit error, and `_get_obj` is called without the `op` argument so even the *not-found* errors read "op '?'". Only the error message quality is hit (chain still aborts exit 1), hence P2.
- **Fix**: `if needs_obj and obj is None: raise RuntimeError(f"op '{op}' requires key 'id'")` and pass `op` to `_get_obj`.

### F2B-15 — Plausible bad inputs to audit/pairs/supports raise raw misleading errors instead of kit errors
- **File**: `scripts/apply_patch.py:399-400, 456-458`; `scripts/placement_lib.py:598-599, 785-793, 934-953`
- **Excerpt**:
  ```python
  # apply_patch._apply_audit
  pairs = [tuple(p.split(",")) for p in params["pairs"]]
  # placement_lib.audit_scene
  todo = [(bpy.data.objects[p[0]], bpy.data.objects[p[1]]) for p in pairs]
  ```
  plus `place_on` with `supports=[]` → `max()` on empty sequence (`:793`), `supports` given as a string → iterates characters (`apply_patch.py:351`), `physics_settle objs:"Cube"` → iterates characters (`:456-458`).
- **Why it matters**: `bpy.data.objects["Nope"]` raises `KeyError` which `apply_mutation`'s KeyError converter mislabels as "op 'audit' missing/invalid param 'Nope'" — pointing the agent at a *missing parameter* when the real problem is an unknown object name (the `_get_obj` hint list is exactly what's needed and is bypassed). `place_on` with no supports surfaces as `ValueError: max() arg is an empty sequence`. None of these are silent, but all are friction on the primary gate/ops.
- **Fix**: resolve pair names via `_get_obj` in the op layer before calling `audit_scene`; validate `pairs`/`supports`/`objs` are lists of strings and non-empty where required; give `place_on` a "no supports given" kit error.

### F2B-16 — `footprint` value is unvalidated; documented `footprint:"inset"` silently behaves as whole-verts sampling with inset=0
- **File**: `scripts/placement_lib.py:934-936, 952-953`; documented value in `kb/placement_and_physics.md:6`
- **Excerpt**:
  ```python
  pts = surface_samples(obj, mode=('bottom' if footprint == 'bottom' else 'verts'))
  ...
  pts_xy = [(p.x, p.y) for p in pts]     # inset param is separate & defaults 0
  ```
  kb: "`footprint`: 'bottom' (downward-facing verts), 'grid' (samples bbox bottom), 'inset' (seat lips)."
- **Why it matters**: any unrecognized footprint string (`"inset"`, `"grids"`, `"Bottom"`) falls into the `else` → `'verts'` mode **silently** — different sampling semantics, green report (`report["footprint"]` echoes the input verbatim). The kb-documented `'inset'` value does not exist (the real API is the separate `inset=<meters>` param), so an agent following the kb gets lip-placement behavior without the inset they asked for.
- **Fix**: validate `footprint in ("bottom","all","grid")` with a kit error listing valid values (and the `inset` param hint); fix kb.

### F2B-17 — `report["footprint_fallback"]` condition is inverted; the bbox-band fallback it is supposed to flag is unreportable
- **File**: `scripts/placement_lib.py:949-951`
- **Excerpt**:
  ```python
  report["footprint_fallback"] = footprint == 'bottom' and any(
      world_normal(obj, v.normal).z >= -0.3 for v in obj.data.vertices) is False
  ```
- **Why it matters**: `any(z >= -0.3) is False` ≡ *all* vertex normals point down — essentially never true. The actual fallback in `surface_samples` (`:197-204`) fires when **no** vert has `normal_z < -0.3` (the negation of the other half-space). So the flag is (almost) always `False`, including exactly when the fallback fired; consumers can never tell that their footprint came from the bottom-5%-z-band instead of downward-facing verts (which changes which points drive the solve). It also samples `obj.data.vertices` (base mesh) while the sampler used the evaluated mesh.
- **Fix**: `report["footprint_fallback"] = (footprint == 'bottom' and not any(world_normal(obj, v.normal).z < -0.3 for v in obj.data.vertices))` — or better, have `surface_samples` return whether the fallback fired.

### F2B-18 — `seam_views` leaks its `SeamCam` object into the scene (and therefore into `--save-blend`'s state carrier)
- **File**: `scripts/placement_lib.py:1429-1431, 1536`; contrast the clean pattern `:1795-1806` (`section_pair` removes its cameras in `finally`)
- **Excerpt**:
  ```python
  cam = bpy.data.objects.new("SeamCam", cam_data)
  scene.collection.objects.link(cam)
  ...
  scene.camera = old_cam        # pointer restored, object never removed
  return {"contact_state": ..., ...}
  ```
- **Why it matters**: every `seam_views` mutation leaves a `SeamCam` (then `SeamCam.001`, …) object in the .blend. It pollutes the state carrier that AGENTS.md declares canonical (`--save-blend` → `look --load-blend`), shows up as an object row in schema/manifests, and accumulates across a patch chain. `section_pair` right below demonstrates the intended discipline (temp camera removed in `finally`), so this is an inconsistency, not a design choice.
- **Fix**: wrap the seam_views shooting in `try/finally` and `bpy.data.objects.remove(cam, do_unlink=True); bpy.data.cameras.remove(cam_data)` (keep the `scene.camera` restore).

### F2B-19 — `physics_gate` REJECTED is invisible to `--fail-on-physics-failure` (only settle/place/oracle are wired to `_physics_warn`)
- **File**: `scripts/apply_patch.py:538-553` vs `:461-474, 492-498, 515-517, 533-535`; flag promise `:1140-1143`
- **Excerpt**:
  ```python
  def _apply_physics_gate(obj, params):
      rep = _PP.gate(...)
      _LAST_REPORTS["physics_gate"] = rep
      print("[apply_patch] physics_gate:", rep.get("verdict"), ...)
      for _q in rep.get("fix_queue", [])[:8]: ...
      # <-- no _physics_warn(rep)
  ```
  physics_place.py:1493-1494: `report["verdict"] = "REJECTED" if rejected else "PASS"; report["ok"] = not rejected`
- **Why it matters**: the CLI help promises "`--fail-on-physics-failure`: exit 3 if **any physics_*** mutation ended with `ok=false`". `physics_gate` with `fail_hard:false` (the default) ends REJECTED/`ok:false` but never appends to `_PHYSICS_FAILURES`, so the flag exits 0 — a fail-open on an opt-in exit-code gate whose entire purpose is pipeline enforcement.
- **Fix**: call `_physics_warn(rep)` in `_apply_physics_gate` (it appends to `_PHYSICS_FAILURES` when `ok is False`).

### F2B-20 — scene_schema (the agent's mental model) is blind to the kit's own durable state: labels, semantics, render-visibility, modifiers, real world content
- **File**: `scripts/scene_schema.py:141-147, 168-201`
- **Excerpt**:
  ```python
  entry = { "id": obj.name, "type": obj.type, "location": ..., "parent": ...,
            "visible": obj.visible_get(), "materials": [...] }   # no custom props anywhere
  if scene.world and scene.world.node_tree is not None:
      bg = scene.world.node_tree.nodes.get("Background")
      if bg: schema["world"] = {"background_color": [...default_value...], ...}
  ```
- **Why it matters**: (a) `kit_label`/`kit_label_conf`/`kit_semantic` — which D16/AGENTS.md:383-394 declare "durable identity" that gates *read by prop* — are absent, so a patch author querying the schema cannot see or preserve labeling state (the look manifest has it; the two state exports disagree). (b) `visible_get()` is viewport visibility; `hide_render` (the flag `render_hidden_objects`/glTF/`configure_render` act on) is not exported — schema says visible for objects that will not render. (c) an `add_sky_world`/HDRI world reports the Background node's *default* grey `default_value` (the color socket is linked) — the actual sky/HDRI is invisible. (d) modifiers/armature/constraints (which change evaluated geometry that placement audits measure) are absent. (e) materials resolve only a node literally named "Principled BSDF" (`:64`) — renamed/imported node names export `color: None` on the L4 "read color from schema" path.
- **Fix**: export `dict(obj.items())` (custom props, filtered to kit_*) per object; add `hide_render`; export world type (sky/HDRI/strength/sky texture pointer or texture name); add a `modifiers` name/type list; match Principled by type (`node.type == 'BSDF_PRINCIPLED'`) not by label.

### F2B-21 — `export_scene_schema` never depsgraph-updates; after in-process mutations the schema can report a pre-mutation `matrix_world`
- **File**: `scripts/scene_schema.py:124-137` (no `view_layer.update()`); the hazard is documented and guarded in the kit's own measurement layer at `scripts/placement_lib.py:86-94`
- **Excerpt**:
  ```python
  def export_scene_schema(*, with_bounds: bool = False) -> dict:
      scene = bpy.context.scene
      schema = {...}            # straight to obj.matrix_world / bound_box reads
  ```
- **Why it matters**: on the documented `apply_patch --export-schema` path, a preceding `set_location` writes `obj.location` (fresh RNA) while `matrix_world`/`bound_box`-derived fields (`world_centroid`, `bounds`) can still hold the pre-move evaluated cache — the schema self-inconsistently shows the new `location` next to the old `matrix_world`. placement_lib's `world_bvh` comment spells out this exact staleness ("matrix_world is a lazily-updated RNA cache — hashing the key BEFORE the depsgraph update could hash the PRE-commit matrix").
- **Fix**: call `bpy.context.view_layer.update()` at the top of `export_scene_schema`.

### F2B-22 — DoF CLI shortcut without a patch clears the scene and then always fails; the code comment claims the patch is optional
- **File**: `scripts/apply_patch.py:1177-1196, 1226-1228, 1250-1261`
- **Excerpt**:
  ```python
  # CLI shortcut: ... the patch itself is optional when only the shortcut is used.
  ...
  else:
      patch = {}
  if dof_shortcut: patch.setdefault("mutations", []).append(dof_shortcut)
  ...
  else:   # no load_blend, no scene
      _clear_scene()   # clears the factory Camera the shortcut then targets
  ```
- **Why it matters**: `apply_patch.py -- --focus-distance 2.5` (shortcut only) → factory contents cleared → `set_camera_dof` on `Camera` → "object 'Camera' not found" → exit 1. The path is *guaranteed* to fail and the comment explicitly says it is supported; the shortcut is only usable in combination with `load_blend`/`scene`, which the comment denies.
- **Fix**: when `dof_shortcut` and no load/scene key, error out with "DoF shortcut requires --patch/--patch-json with load_blend/scene" instead of clearing; or skip the fresh-scene clear when the only mutation is the shortcut and fail with the same message.

### F2B-23 — `physics_settle` with `objs: []` silently means "whole scene" (the mode the docs call "almost never wanted")
- **File**: `scripts/apply_patch.py:456-458, 478-480`; `scripts/physics_place.py:596-606`
- **Excerpt**:
  ```python
  def _resolve_objlist(names, op="?"):
      return [_get_obj(n, op) for n in names] if names else None   # [] -> None
  ...
  objs=_resolve_objlist(params.get("objs"), "physics_settle") or None,
  ```
- **Why it matters**: an agent emitting `"objs": []` to mean "no movers" gets `objs=None` = settle **every eligible mesh** (the free-fall mode). The `whole_scene_warning` lands only inside the report JSON (`physics_place.py:597-601`) — `apply_patch`'s stdout path prints only the verdict/per-object lines, and the failure mode (everything ESCAPED) arrives after the sim has run. Empty list and null should not be synonyms.
- **Fix**: distinguish `None` (whole scene) from `[]` (explicit error "objs must name at least one mover, or omit the key for whole-scene") in the op layer; print `whole_scene_warning` to stdout in `apply_patch`.

### F2B-24 — apply_patch `--scene` rebuild breaks the exporter's own bare-`animate(ctx)` contract
- **File**: `scripts/apply_patch.py:1247-1249` vs `scripts/export_preflight.py:300-314` and `scripts/export_previz_package.py:1043-1048`
- **Excerpt**:
  ```python
  ctx = mod.build_scene()
  if hasattr(mod, "animate"):
      mod.animate(ctx, start_frame=1, n_frames=patch.get("frames", 24))
  ```
  preflight S1 explicitly validates both branches: `mod.animate(ctx)` and `mod.animate(ctx, start_frame=1, n_frames=None)`.
- **Why it matters**: a scene module that passes preflight with the bare `def animate(ctx)` branch (documented as the exporter's sentinel dispatch, the "P0-5 class") crashes `apply_patch --scene` with `TypeError: animate() takes 1 positional argument but 3 were given` *before* any mutation runs. Two kit entry points enforce different contracts for the same module shape.
- **Fix**: mirror the exporter dispatch (inspect.signature, try/except TypeError, fall back to `mod.animate(ctx)`), or have preflight reject bare-animate modules.

### F2B-25 — `seat_mesh` name that doesn't exist silently skips the requested post-audit; `seat_at` then prints "OK"
- **File**: `scripts/apply_patch.py:380, 384-385`
- **Excerpt**:
  ```python
  seat_mesh=bpy.data.objects.get(params["seat_mesh"]) if params.get("seat_mesh") else None,
  ...
  print("[apply_patch] seat_at:", rep["obj"], "->",
        "OK" if rep.get("ok", True) else "CONTACT-ISSUES")
  ```
- **Why it matters**: `bpy.data.objects.get` returns `None` for a typo'd `seat_mesh`, so the agent's explicitly requested verification silently never happens, the report has no `post_contact`/`ok`, and the default-True print says OK — a quiet fail-open of the only verification `seat_at` can perform. (`seat_at` itself never sets `ok` without a seat_mesh, so the print's `True` default is a second, related lie.)
- **Fix**: raise a kit error when `params["seat_mesh"]` is given but not found; print `OK(unverified)` when no seat_mesh was provided.

---

## P3

### F2B-26 — Misc raw-error / param-format nits on documented ops
- **File**: `scripts/apply_patch.py:400, 258-263, 1236, 1264-1266`; `scripts/scene_schema.py:49`
- Details: `audit.pairs` splits on `","` so object names containing commas/spaces (`" A , B "`) become phantom ids (see F2B-15's mislabel); `render_viewport` `samples/width/height` are unvalidated (negative → raw operator error), `target` given as a string is garbled by `tuple(target_str)` into chars; `bpy.ops.wm.open_mainfile` on a missing path raises a raw operator error (no friendly "file not found"); a patch whose JSON root is a list crashes with `AttributeError: 'list' object has no attribute 'get'` at `patch.get("mutations")`; `scene_schema.py:49` uses `type(obj.location)(corner)` (works, but obscure).
- **Fix**: validate list-ness/length/finiteness at the op layer; wrap `open_mainfile` in an existence check; add a top-level `isinstance(patch, dict)` check.

### F2B-27 — Docstring/param drift inside apply_patch
- **File**: `scripts/apply_patch.py:45 vs 838` (docstring says `add_plane` takes `[x,y(,z)]`; code takes exactly 2 → a 3-vector is refused); `:1048` (PARAM_DOCS advertises `match?(name-regex)` for `set_material_color` — no handler reads it); `:1074` (`add_sphere` `radius` implied required, actually defaults 0.5); `scripts/scene_schema.py:128` (`schema_version` hardcoded "1.0" regardless of content changes).
- **Fix**: sync docstring/PARAM_DOCS with handlers; version the schema string when fields change.

### F2B-28 — `label_objects` availability hint always prints "…" even with < 15 objects
- **File**: `scripts/semantic_lib.py:89-92`
- Excerpt: `avail = sorted(o.name for o in bpy.data.objects)[:15]; raise RuntimeError(f"... scene objects: {avail} …")`
- **Fix**: append "…" only when truncating.

### F2B-29 — viewport-quality preset hides any object whose *name* matches mist|fog|haze|atmo
- **File**: `scripts/blender_kit/__init__.py:707-717`
- Excerpt: `if ob.get("kit_atmo") or _atmo.search(ob.name): ob.hide_render = True`
- **Why it's only P3**: deliberate, documented in-code as a legacy fallback, and scoped to the `--quality viewport` preset — but a legit prop named e.g. `Fog_Machine` silently disappears from guidance renders while `scene_schema` still reports `visible: true` (F2B-20b).
- **Fix**: restrict the fallback to volume-only materials (the triple-check already implemented in `atmo_objects`, `:876-909`) instead of bare name matching, or log each hidden name.

### F2B-30 — `clear_bvh_cache()` doesn't clear `_POLY_CACHE` (asymmetric cache hygiene)
- **File**: `scripts/placement_lib.py:61-64` vs `:225-242`
- Excerpt: `_BVH_CACHE.clear()` only; `_POLY_CACHE` is keyed by `_cache_key` (name/counts/frame/filepath/matrix-hash) and survives `open_mainfile` in-process.
- **Why it's only P3**: the key usually changes after mesh edits (vert/face counts shift) and per-invocation lifetimes are short, but an edit that preserves both counts (e.g. a swap-style script edit) at the same frame/matrix would serve stale world polys to the CROSSING test.
- **Fix**: clear both caches in `clear_bvh_cache()` (rename or add `clear_caches`).

---

## Checked and CLEAN

- **Dispatch table arity/needs_obj** (`apply_patch.py:998-1038`): all 39 handlers have the `(obj, params)` signature; needs_obj flags match handler usage for every op (scene-level ops ignore `obj`; object ops use it); no op silently no-ops on its success path; unknown ops raise with the known-list.
- **add_* ops** (`:601-872`): duplicate-id refusal (anti-.001 law), isfinite/positive/nonneg validation incl. the bool-is-int trap, `size` scalar-or-vector semantics, data-baked dims via `data.transform` (object scale stays 1, object-scale gotcha #58 respected), pre-rotation self-verify with chord-aware tolerances (F14 truncated-cone max-radius handled), torus self-intersection refusal, `add_empty` type/self-verify, workbench `diffuse_color` dual-write (gotcha #56), material get-or-create keyed on id (no .001 leak).
- **Placement contact state machine** (`placement_lib.py:19-28, 349-543`): PENETRATING/TOUCHING/CROSSING→PEN/NESTED/CLEAR transitions match the documented machine; the 0.1 mm touch band is applied consistently in the AABB-reject fast path, the main path, and `_min_clear`; coplanar contact correctly yields TOUCHING via the grazing guards (`eps_cross=5e-6` > documented float32 ~60 nm jitter, T3/T4 lessons present); CROSSING requires `enters` + depth > band (round-D micro-tilt discriminator); strict triangle-inside margin (X1 edge-contact lesson); inside claims always parity-verified with EPS_TANGENT=1e-3 (u7/session-16 lessons); `bmesh.normal_update()` after transform present (`:99`, matches SKILL.md law); BVH cache key carries matrix-hash + frame + filepath; skinned-mesh guard; multi-level/slope warnings; `align_to_surface` +Z fix (P0-flip regression note) present; refine under-correction clamps; grid refinement F17 and footprint autowiden present and reported (`footprint_autowiden`, `footprint_grid_refined` keys match AGENTS.md promises).
- **audit_scene mechanics** (`:575-637`): 100 mm clearance pad documented and implemented; worst-first ordering; sub-band penetration advisory rule identical between unscoped and apply_patch's scoped recomputation (session-16 fix verified at `apply_patch.py:418-438`); `state` vs `verdict` split honored (AGENTS.md law).
- **mm claims vs tolerance**: penetration/clearance claims are vert-sampled float32 BVH distances reported at 0.01 mm with a 0.1 mm advisory band — the band is ≥ the documented float32 jitter, so no claim exceeds the measured tolerance.
- **semantic_lib** (`:41-244, 495-613`): charset law + KIT_ANNOT rejection, all-or-nothing batch validation with object-existence checks, two-phase rename with temp-name collision refusal and re-read verification, report written **before** mutation (crash-resume), semantic-marker cleanup on relabel (stale `kit_semantic` deleted), confidence cleanup, split risk refusals (library/co-users/modifiers/shape-keys/armature), F19 >50-part refusal, region-cut "exactly 1 new object" verification and `_unique_name` anti-.001 naming — all as documented.
- **scene_template contract**: `build_scene()` → ctx dict (no `scene` key needed; exporter falls back to `bpy.context.scene`), `animate(ctx, *, start_frame, n_frames)` binds under **both** exporter dispatch branches, `main()` wiring (common_parser → build → animate → configure_render → render) is correct; ctx keys self-consistent. Template drift vs exporter/preflight: none found (the bare-animate mismatch in F2B-24 is apply_patch-side, not the template's).
- **blender_kit shim, remaining surface**: `clear_scene` (factory-empty), `make_material` (F-TD11 emission pinning; unguarded `Emission Strength` is deliberate and commented), `add_sky_world` (NISHITA/MULTIPLE_SCATTERING autodetect via enum probe), **`normalize_engine_id` — no real-id collisions found** (the typo set covers the documented spellings; substring matches are loose but cannot mis-map cycles/workbench/eevee among themselves; unknown passes through to a loud bpy error as documented), `ensure_use_nodes` (4.x-only write), `supports_headless_gpu` (device-gated, matches the SKILL.md warning), `_safe_set` (prints a note; loud setattr), `script_argv`, `safe_import_scene` (friendly errors, honest inner-import reporting), `export_gltf` (selection-based exclusion with restore in `finally`, depsgraph-fresh render-hidden sweep), USD kwarg retry fallback, `_validate_outputs`/metadata.
- **apply_patch main flow** (`:1131-1316`): JSON decode errors clean; `--patch-json` file-path fallback (D1); `load_blend` → `clear_bvh_cache`; chain-abort saves partial state only with `--save-blend` and says so; physics exit-code 3 wiring works for settle/place/oracle; `--list` prints all 39 ops.
- **physics op call signatures**: apply_patch's settle/place/oracle/gate kwargs match `physics_place.py` definitions exactly (no arity drift).
- **render_viewport internals**: engine alias table covers the documented enums; `render_angle` raises loudly on unknown engine/angle; temp-camera cleanup present in `viewport_capture.py:232-237`; readiness stats printed (D6 pairing).

## Suggested next actions (for the fixing lane)

1. P0/P1 batch: F2B-1 (custom_loc), F2B-2/3 (ERROR-row fail-opens — two one-line fixes), F2B-4 (keep_xy: implement or refuse), F2B-5 (finite-validator shared by all ops), F2B-6 (seat_at reference validation), F2B-7 (seam_views signature), F2B-8 (matrix_world writes in solvers).
2. Add a contract test that parses every PARAM_DOCS entry and asserts the keys match the handler's actual `params[...]`/`params.get(...)` reads — this mechanically kills the F2B-10/11/12/7 class permanently.
3. Schema parity test: build a labeled scene (label_objects + add_sky_world + hide_render) and assert the schema export carries labels/world/hide_render (F2B-20/21).
