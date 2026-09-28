# ADR: Blender 4.5 LTS vs 5.2 LTS

**Status**: Accepted (session 6, Sept 2026) — **VALIDATED IN PRODUCTION** (session 24-25: the full previz export pipeline runs 5.2.2 end-to-end, ~2.1x faster than 4.5.14, output structurally identical — same node/animation/skin/mesh/material name sets, belt+jeep tracks byte-identical, rifle within 5.84e-06 float noise; all 13 export gates green on BOTH versions. Details: `blender-escape-previz/project/ASSESSMENT_blender_52.md`.)
**Decision**: Ship Blender 5.2 LTS as default; keep 4.x compat paths in the kit's shim so the kit runs on both unchanged.

## Context

The prior ADR (session 1-2) targeted Blender 4.5 LTS and avoided 5.x citing "breaking API changes." The user asked to re-litigate this because:
1. The kit has evolved significantly (viewport capture, apply_patch, scene_schema, validate_scene, polyhaven, e2e live viewer)
2. 5.x may have stabilized with an LTS release
3. We haven't run a full benchmark of agent usability with 5.x vs 4.5
4. The exact enhancements 5.x offers haven't been assessed

## Research (3 parallel sub-agents, verified against live sources)

### 5.x stable status (as of Sept 2026)
- **Blender 5.2 LTS** released July 14, 2026, maintained until July 2028 (2-year LTS policy)
- 5.0 (Nov 2025) and 5.1 (Mar 2026) are non-LTS, no longer supported
- 4.5 LTS still supported until July 2027 (~10 months overlap)
- Sources: developer.blender.org/docs/release_notes/, blender.org/download/releases/5.2/

### Breaking changes affecting our kit's surface
| # | Change | Touches our surface? | Severity | Mitigation |
|---|--------|---------------------|----------|------------|
| 1 | EEVEE id `BLENDER_EEVEE_NEXT` → `BLENDER_EEVEE` (5.0) | YES | P1 | `normalize_engine_id()` shim |
| 2 | `action.fcurves` → `action.layers[0].strips[0].channelbag(slot).fcurves` (5.0) | YES | P1 | `iter_fcurves()` helper |
| 3 | `NISHITA` sky type removed (5.0) | YES | P1 | Auto-fallback to `MULTIPLE_SCATTERING` |
| 4 | `mat.use_nodes = True` deprecated (5.0) | YES (pervasive) | P2 | `ensure_use_nodes()` no-op on 5.x |
| 5 | `scene.eevee.use_gtao` / `use_ssr` / `use_bloom` removed (5.0) | YES | P2 | Already handled by `_safe_set()` |
| 6 | dict-access to RNA props removed (5.0) | NO (rare in agent code) | P2 | N/A |
| 7 | `scene.node_tree` compositor removed (5.0) | NO (not used) | P2 | N/A |
| 8 | Geometry Nodes modifier API rewrite (5.2) | NO (not used) | P2 | N/A |

### LLM training affinity (key finding)
- LLMs default to 4.x API patterns regardless of target version
- Mid-2024-cutoff LLMs (Claude 3.7, GPT-5) emit `BLENDER_EEVEE_NEXT` (4.2-4.5 era) — WRONG on 5.x
- Pre-2024 LLMs (GPT-4o, Claude 3.5) emit `BLENDER_EEVEE` (3.x name, accidentally correct on 5.x)
- All LLMs emit `action.fcurves` for easing loops (broken on 5.x)
- All LLMs emit `mat.use_nodes = True` (deprecated on 5.x)
- **Shielding is essential** — agents can't be expected to know 5.x API

### Container readiness (Debian 13, 4GB RAM, no GPU)
- glibc 2.40 ≥ 2.28 required ✅
- OpenGL 4.6 via llvmpipe ≥ 4.3 required ✅
- Python 3.13 bundled ✅
- 4GB RAM < 8GB min ⚠️ (top risk, EEVEE-Next heavier memory)
- `gpu.init()` (5.2 NEW) may eliminate Xvfb — unvalidated
- Source: blender.org/download/requirements/

## Decision

**Ship 5.2 LTS as default; keep 4.x compat paths in the kit's shim.**

### Rationale
1. 5.2 LTS is stable (2-year support until July 2028)
2. Only 3 hard breaks affect our surface — all mitigated by ~80 lines of shim
3. The shim lets agent-written 4.x scripts run on 5.2 unchanged
4. LLMs default to 4.x patterns; shielding is essential regardless of target version
5. 5.2 offers `gpu.init()` (may eliminate Xvfb) + Python 3.13 + LTS stability
6. 4.5 LTS overlap (until July 2027) gives migration window

### Compat shim (in `scripts/blender_kit/__init__.py`)
```python
EEVEE_ENGINE_ID = 'BLENDER_EEVEE_NEXT' if not _BLENDER_5 else 'BLENDER_EEVEE'

def normalize_engine_id(name):
    # Accepts any spelling (BLENDER_EEVEE_NEXT, BLENDER_EEVEE, eevee, BLENDER_EEE_NEXT typo)
    # Returns the correct id for the running Blender version

def iter_fcurves(action):
    # 4.x: action.fcurves
    # 5.x: action.layers[0].strips[0].channelbag(slot).fcurves

def ensure_use_nodes(mat_or_world):
    # 4.x: sets True
    # 5.x: no-op (auto-created, deprecated)

def supports_headless_gpu():
    # True if gpu.init() available (5.2+)
```

### What AGENTS.md does NOT do
Per user constraint: AGENTS.md is NOT a 5.x API doc. Agents write 4.x idioms (`BLENDER_EEVEE_NEXT`, `action.fcurves`, `mat.use_nodes = True`) and the kit normalizes. The wrapper layer shields agents from version differences.

## A/B test results

| Test | Blender 4.2.9 | Blender 5.2.2 |
|------|---------------|---------------|
| Shim import | is_blender_5=False, EEVEE_NEXT | is_blender_5=True, EEVEE |
| normalize(BLENDER_EEVEE_NEXT) | → BLENDER_EEVEE_NEXT | → BLENDER_EEVEE ✅ |
| supports_headless_gpu() | False | True |
| Cycles still (draft) | 21140 bytes, exit 0 | 17751 bytes, exit 0 |
| EEVEE still (via BLENDER_EEVEE_NEXT) | renders OK | renders OK (normalized) |
| 24-frame EEVEE anim + MP4 | 50s warm, 15568 bytes | 92s cold, 16453 bytes |
| _safe_set skips removed EEVEE attrs | N/A | graceful skip ✅ |

Both versions render successfully with the same scene script unchanged.

## Top 5 risks
1. **4GB RAM < 8GB min** — OOM risk on EEVEE scenes (mitigate: cap samples/res, prefer Workbench for big scenes)
2. **`action.fcurves` silent break** — scenes build but easing loops wrong (mitigated by `iter_fcurves()`)
3. **`BLENDER_EEVEE_NEXT` invalid on 5.x** — warm-cache crashes (mitigated by `EEVEE_ENGINE_ID` constant)
4. **`gpu.init()`/EGL path unvalidated** — don't drop Xvfb yet (keep as fallback)
5. **`use_nodes` no-op visual regression** — Workbench bg color may shift (mitigated by `ensure_use_nodes()`)

## Top 5 opportunities
1. **`gpu.init()` (5.2)** — potentially drop Xvfb entirely (unvalidated follow-up)
2. **Python 3.13 bundled** — modern syntax, better tracebacks
3. **LTS until July 2028** — 2-year stability window
4. **Slotted-actions / channelbag API** — enables multi-actor animation in one action
5. **5.2.x patch line** — GPU/compositor crash fixes (5.2.2 current)

## Migration engineer-hours: ~12-16 (≈1.5-2 days)
- Shim implementation: ~4h (done in session 6)
- Apply to kit files: ~2h (done in session 6)
- A/B test setup: ~3h (done in session 6)
- install.sh update: ~1h (pending)
- gpu.init() validation: ~3h (follow-up)
- CI matrix (4.5 vs 5.2): ~3h (follow-up)

## Next actions
1. ✅ Land the shim in `blender_kit/__init__.py` (done)
2. ✅ Apply the 8 edits to kit files (done)
3. ✅ Update `install.sh` to default to 5.2 LTS (done — `BLENDER_VERSION=5.2.2` default)
4. ✅ Validate `gpu.init()` in no-GPU container (done, session 16 + 24: EGL boots but CRASHES without a real /dev/dri render node — llvmpipe containers keep Xvfb; `supports_headless_gpu()` gates on the device, not the API)
5. ⬜ Add CI matrix job: same scene on 4.5 + 5.2, diff render hashes (follow-up)

Session-24/25 additions the original ADR did not cover (all fixed at the
shim + call-site layer, 4.5 path still green — the dual toolchain
`tools/blender` -> 5.2.2 / `tools/blender45` -> 4.5.14 exists for exactly
this): `world.use_nodes = False` is a SILENT no-op on 5.x (build explicit
Background-node trees); NISHITA sky type removed (enum-probe sky_type);
EEVEE engine id is version-dependent (`normalize_engine_id`);
`shadow_cube_size`/`cascade_size` removed (use `shadow_resolution_scale`);
Blender --background does NOT add the --python script's dir to sys.path on
5.2 (entry scripts own their sys.path).

## Sources
- https://developer.blender.org/docs/release_notes/5.0/python_api/ — bpy.props dict removal, BGL, EEVEE id, render-pass renames, ImageFormatSettings.media_type, legacy Action API removal, use_nodes deprecation, gtao
- https://developer.blender.org/docs/release_notes/5.0/eevee/ — EEVEE id change, gtao_distance move
- https://developer.blender.org/docs/release_notes/5.0/animation_rigging/ — action API, bone visibility split
- https://developer.blender.org/docs/release_notes/5.1/python_api/ — Python 3.13
- https://developer.blender.org/docs/release_notes/5.2/python_api/ — gpu.init() background, Geometry-Nodes modifier API rewrite, Window.screenshot(), imbuf
- https://docs.blender.org/api/5.0/change_log.html — confirms SceneEEVEE only removed gtao_*; Principled/Env nodes present
- https://docs.blender.org/api/5.2/change_log.html — confirms NodesModifier.properties added
- https://www.blender.org/download/releases/5.2/ — 5.2 LTS maintained until July 2028
- https://www.strayspark.studio/blog/ai-hallucinating-blender-python-api-bpy-fix — LLM training data dominance + shielding strategy
- https://github.com/HaoooWang/llm-knowledge-cutoff-dates — LLM cutoff dates
- https://www.blender.org/download/requirements/ — 5.2 system requirements
- https://download.blender.org/release/Blender5.2/ — 5.2.2 tarball (383MB)
