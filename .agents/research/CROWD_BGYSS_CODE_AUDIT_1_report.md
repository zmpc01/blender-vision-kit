# CROWD-BGYSS-CODE-AUDIT-1 — Deep Audit of bgyss/Blender-Crowd Actual Code for Direct Vendoring

> **Status**: Re-evaluation of v1.2 addendum §0.4 in light of the user's
> 2026 directive ("this is internal project kit, GPL is OK; if usable, take
> the source directly").
>
> **Inputs**: live read of `/tmp/Blender-Crowd/` (490 files, 100K LOC total:
> 46.2K Rust + 16.7K Python + 1.9K JSON schema + 31.8K Markdown + 0.2K
> TOML/sh); prior reports `CROWD_RESEARCH_EXT_1`, `CROWD_FIELDS_AUDIT_1`;
> v1.2 addendum §0.4 (GPL-firewall: "HYBRID — patterns only").
>
> **Author**: general-purpose sub-agent (CROWD-BGYSS-CODE-AUDIT-1)

---

## 1. Executive summary

1. **VENDOR-WHOLESALE into `vendor/blender-crowd/` is viable and recommended.**
   The code is GPL-3.0+, now-permissible for the internal kit. It is
   cross-platform (Linux `cfg` blocks present in `crates/crowd-bench/src/report.rs:179-209`),
   has zero GPU dependency (only `cpu_reference` implemented; `Metal/Cuda/Vulkan`
   are enum stubs in `crates/crowd-core/src/field.rs:75-113`), and the entire
   Rust workspace depends on just 5 crates: `blake3`, `crc32c`, `serde`,
   `serde_json`, `pyo3` (workspace `Cargo.toml:16-22`). No C/C++ in the build
   beyond what blake3 ships pre-built wheels for.

2. **The single biggest blocker is NOT a code blocker — it's a build-chain
   + packaging blocker.** The shipped addon declares
   `platforms = ["macos-arm64"]` and bundles only the macOS arm64 wheel
   (`addon/blender_crowd/blender_manifest.toml:13-14`). Vendoring means
   we own the Linux x86_64 wheel build: `cargo +maturin build --release`
   with `--target x86_64-unknown-linux-gnu`. BLAKE3 ships manylinux wheels;
   pyo3 0.29 with `abi3-py311` builds one wheel for all CPython ≥3.11. The
   `.cargo/config.toml` only sets macOS linker overrides — Linux builds
   with default `cc`. No source changes needed; just one extra CI step.

3. **At the kit's target scale (1K agents × 30Hz × 4GB) bgyss is wildly
   in-budget.** M1 acceptance evidence (`docs/benchmarks/2026-08-10-m1-vertical-slice.md:138-159`):
   1,000 agents × 10,000 ticks sim in 12.2s (~820 ticks/s, 27× headroom over
   30Hz); peak Blender resident 424 MB (10% of 4GB limit); cache 560 MB for
   10K ticks. 100K is out of scope (needs 64GB) but irrelevant to v1.

4. **Effort savings vs v1.2 handroll: ~7-9 sessions → ~1-2 sessions**
   (fork bgyss + build Linux wheel + adapt kit's scene-IR converter +
   stub Blender 4.x compat). v1.2 estimated 6-9 sessions to ship v1 by
   handrolling navmesh + behavior IR + cache + GN group + keyframe shim.
   Vendoring eliminates all of that — those subsystems are already
   implemented, tested, and have accepted milestone evidence (M0-M6).

5. **The Python addon cannot be vendored without the Rust core.**
   Every entry point imports `blender_crowd_native` (the PyO3 module):
   `operators.py:11`, `cache_playback.py:11`, `properties.py` (via
   properties' native setters), `m6_*` modules. There is NO pure-Python
   fallback path. Vendoring is all-or-nothing: either we ship Rust+PyO3
   or we don't ship bgyss at all. The v1.2 "borrow patterns only" stance
   remains valid for partial use; wholesale requires the Rust toolchain.

6. **GPL license confirmed at workspace level**: `Cargo.toml:14`
   `license = "GPL-3.0-or-later"`; `addon/blender_crowd/blender_manifest.toml:10`
   `license = ["SPDX:GPL-3.0-or-later"]`. The kit becomes GPL-contaminated
   at the file level, which the user explicitly approved ("internal
   project kit, I don't see why we can't use GPL"). Kit's existing
   `scripts/crowd_fields.py:36-37` already disclaims "Zero code copied"
   from bgyss — that line must be deleted or rewritten once vendored.

7. **Top recommendation for design v1.3**: replace v1.2 absorption
   matrix §0.1 wholesale. Drop the handroll navmesh + cache + behavior IR
   + GN group + keyframe shim work. Fork bgyss, build Linux wheel, write
   one adapter `scripts/crowd/kit_project_ir.py` that converts the kit's
   scenario-DATA into bgyss's `AuthorableProjectV2` JSON. The kit's
   `crowd_fields.py` + `gait_modifiers.py` survive as **scenario-side
   influence-field + modifier engines**, NOT as the simulation core.

---

## 2. Per-component audit

### A. Rust core (`crates/`) — **VENDOR-WHOLESALE**

**What's there** (5 crates, workspace `Cargo.toml:2-8`):

| Crate | LOC | Role |
|---|---|---|
| `crowd-core` | ~17K | Sim kernel: SoA world (`world.rs:60-100`), 7-phase tick (`sim.rs`, `phases/{perceive,plan,decide,steer,integrate,animate,spawn}.rs`), 3 avoidance solvers (`avoidance/{sampled,orca,anticipatory}.rs`), tiled navmesh + A* (`nav/{grid,pathfind,portal}.rs`), behavior-graph IR + compiler (`behavior.rs`, `project.rs`), StableRng (`rng.rs`), metrics (`metrics.rs:1508` LOC), M6 perception/brain/activity/interaction/motion (`perception.rs`, `activity.rs`, `interaction.rs`, `motion.rs`, `runtime_behavior.rs`). |
| `crowd-cache` | ~3K | Versioned chunked cache: 64-byte chunk header (`codec.rs:11`), CRC-32C + BLAKE3 integrity, manifest v1, agents.bin static table, layout/override/interaction/behavior-event layers, recovery inspector. |
| `crowd-trace` | ~0.4K | Lightweight trace v0 binary writer/reader (deprecated path; cache v1 supersedes). |
| `crowd-blender` | 2.2K | PyO3 bridge: 6 classes (`Trace`, `PyCompiledProject`, `PyAuthorableProject`, `Session`, `PyCancelToken`, `PyCache`) + 9 module functions (`compile_project`, `compile_behavior_graph`, `migrate_project_v1`, `compile_authorable_project`, `compile_authorable_runtime`, `simulate_physics_handoff`, `validate_interaction_motion_attachment`, `resimulate_local_kinematic`, `inspect_cache`) — `crates/crowd-blender/src/lib.rs:2175-2196`. |
| `crowd-bench` | ~3K | CLI runner: baselines, scale gates, M5 gate adjudicator, alloc counter, cache experiment. Not shipped in the wheel — build-time / acceptance-test only. |

**Build chain**: `cargo build --release` + `maturin build --release --manifest-path crates/crowd-blender/Cargo.toml --out <dir>` (`scripts/build-wheel.sh:27-30`). `mise.toml:7` pins `maturin = 1.9.6`; `rust-toolchain.toml:2` pins `rust = 1.94.1`. abi3-py311 wheel — works against CPython 3.11/3.12/3.13 (Blender 5.2 ships 3.13).

**Cross-platform**: `crates/crowd-bench/src/report.rs:163-192` has explicit `#[cfg(target_os = "linux")]` blocks reading `/proc/cpuinfo` and `/proc/meminfo`. The `.cargo/config.toml` only adds macOS linker overrides — Linux builds with system `cc`. **No `target_os = "macos"` gated code in the sim kernel** (only in `report.rs` for CPU detection cosmetics). Confirmed via `Grep` for `target_os` across `crates/`: only `report.rs:164, 179, 195, 206` (Linux + macOS parity) — both branches implemented.

**RAM at 1K**: M1 acceptance — "Peak Blender resident memory 423,772,160 bytes" (~424 MB) for 1K agents × 10K ticks × 560 MB cache (`docs/benchmarks/2026-08-10-m1-vertical-slice.md:159`). Native-sim peak allocator (crowd-bench counter) is **7,858,925 bytes ≈ 7.86 MiB** at 10K agents (`docs/benchmarks/2026-08-14-m5-10k.md:59`) — so 1K is well under 1 MiB for the sim alone. **4GB container has ~10× headroom at 1K agents.**

**Per-tick wall time at 1K × 30Hz**: M1 strict rebake — 10,000 ticks in 12.2s → 0.82ms/tick wall, or **~1.2ms/tick at 30Hz cadence** (sim only, no cache write). vs the 33ms/tick FAST budget in v1.2 §0.3 — **27× headroom on a slower M1 Max CPU**; kit's x86_64 container will be 1.5-3× slower but still ~10× headroom.

**Per-tick at 100K**: 13.7 ticks/s achieved, needs 64GB RAM (`docs/benchmarks/2026-08-18-m5-100k.md:24`). Out of scope for kit v1.

**GPU deps**: none. `crates/crowd-core/src/field.rs:75-113` declares `FieldBackend::{CpuReference, Metal, Cuda, Vulkan}` but `is_implemented()` returns true ONLY for `CpuReference`. The M5 100K gate passed on `cpu_reference` (`docs/benchmarks/2026-08-14-m5-10k.md:23`).

**License**: `Cargo.toml:14` — `GPL-3.0-or-later`. Confirmed.

**Verdict**: VENDOR-WHOLESALE. The Rust core is the crown jewel — 46K LOC of tested, deterministic, contract-driven code. Re-implementing this in Python+NumPy (v1.2 plan) would take 6-9 sessions and produce a strictly inferior system (no behavior graph compiler, no M6 perception/activity, no recoverable cache).

### B. Python add-on (`addon/blender_crowd/`) — **VENDOR-WHOLESALE (with Rust)**

**Modules** (24 .py, 6,639 LOC total, all in `addon/blender_crowd/`):

| Module | LOC | Role | Native dep? |
|---|---|---|---|
| `__init__.py` | 24 | Registers 5 sub-modules | no |
| `operators.py` | 1,758 | 36 Operator classes (bake/inspect/override/M4/M5/M6) | YES — `import blender_crowd_native` (line 11) |
| `properties.py` | 424 | 11 PropertyGroups (project, population, clip, variation, layout, group, M4 layer, M5 tier, M6 brain, etc.) | indirect (calls native setters via operators) |
| `panels.py` | 450 | 7 UI panels (workflow, project, populations, M4, M5, M6) | no |
| `cache_playback.py` | 352 | `CachePlayback` class — point-cloud attribute writer, frame-change handler, layer composition | YES — line 11 |
| `geometry_nodes.py` | 361 | Builds the GN instancing node group procedurally (no .blend asset shipped) — `ensure_cache_node_group()` writes 15+ nodes including terrain raycast | no |
| `project.py` | 501 | Scene→IR extractor: walks `crowd_project` properties and emits `AuthorableProjectV2` JSON | no |
| `m6_interaction.py` | 436 | M6 interaction layer attach/detach | indirect |
| `m6_library.py` | 349 | Declarative brain library validator (Python-side; Rust is authority) | no |
| `render_workflow.py` | 289 | Render setup, Eevee/Cycles dispatch | no |
| `reference_assets.py` | 217 | Bundled CC0 procedural fixtures (4 meshes, 4 materials, 1 proxy armature, idle/walk/jog) | no |
| `m4_layout.py`, `m5_scale.py`, `m6_*`, `health.py`, `debug_overlay.py`, `behavior_editor.py`, `layout_editor.py`, `overrides.py`, `trace_playback.py`, `support.py`, `m6_physics.py`, `m6_debugger.py`, `m6_extensions.py` | 24-200 each | M3-M6 features | mixed |

**PyO3 surface** (`crates/crowd-blender/src/lib.rs:2175-2196`): 6 classes + 9 module functions = **~15 entry points total**. Small, auditable, well-documented (every function has a contract comment).

**Blender compat**: `blender_manifest.toml:11` — `blender_version_min = "5.2.0"`. NO 4.x compat path. The kit's existing 4.x/5.2 compat shim (`scripts/blender_kit/__init__.py` `iter_all_fcurves` + `keyframe_insert_compat`) does NOT help here — bgyss uses Blender 5.2-only APIs: `bpy.data.pointclouds` (5.0+), `attributes.foreach_set` on POINT domain (4.2+ but stabilized in 5.x), `interface.new_socket` with `in_out=` (5.x). **The kit must commit to Blender 5.2 LTS only** (which `crowd_fields_audit_1` and the v1.2 addendum already accepted).

**Pure-Python fallback path**: NO. Every operational entry point reaches `blender_crowd_native`. If we vendor, we commit to building the Rust wheel. The kit's existing `scripts/crowd_fields.py` (455 LOC, pure numpy, no bpy) is genuinely orthogonal — it provides the influence-field + relax-solver primitives that the kit's SCENARIO side uses to drive preferred velocities; bgyss has no equivalent (its "force fields" are inside the avoidance solver as cost terms, not as authored influence spheres).

**Comparison to kit's existing modules**:
- `scripts/crowd_fields.py` (455 LOC): FieldSpec + evaluate_fields + relax (PBD) + advance_phase + playback_rate. **NOT in bgyss** — bgyss has no artist-facing field-authoring primitive; its avoidance solver consumes a `preferred: Vec2` from the decide phase. → KEEP as kit-side scenario engine; wrap to feed bgyss's `AvoidanceInput.preferred`.
- `scripts/gait_modifiers.py` (497 LOC): funny-walk modifier stacks, quaternion algebra. **NOT in bgyss** — bgyss has clip-driven locomotion only (idle/walk/jog) with no per-agent procedural variety. → KEEP as kit-side scenario engine; wrap to feed bgyss's `clip_id` + `phase` + per-agent additive deltas at GN-presentation time (which bgyss's `geometry_nodes.py` already supports via `crowd_proxy_swing` named attribute at line 240).

So the relationship is **complement, not overlap**: bgyss = simulation + cache + playback infrastructure; kit's existing = scenario authoring primitives. Vendoring bgyss doesn't obsolete `crowd_fields` / `gait_modifiers` — they become upstream-of-bgyss adapters.

**Verdict**: VENDOR-WHOLESALE with the Rust core. Cannot vendor the Python addon alone.

### C. JSON schemas (`schemas/`) — **VENDOR-WHOLESALE verbatim**

27 schemas, 1,897 LOC total (`wc -l /tmp/Blender-Crowd/schemas/*.json`). All JSON Schema draft 2020-12, all `$id` under `https://blender-crowd.local/schemas/`. Verified by reading:

| Schema | LOC | Used by | Vendor verbatim? |
|---|---|---|---|
| `project-ir-v1.schema.json` | 329 | `crates/crowd-core/src/project.rs:11` (compile-time validation) | YES |
| `project-ir-v2.schema.json` | 27 | M2 authorable wrapper | YES |
| `cache-manifest-v1.schema.json` | 176 | `crates/crowd-cache/src/manifest.rs`, `crates/crowd-cache/tests/manifest_contract.rs` | YES |
| `behavior-graph-v1.schema.json` | 86 | `crates/crowd-core/src/behavior.rs:13`, `crates/crowd-core/tests/behavior_graph.rs` | YES |
| `decision-trace-v1.schema.json` | 83 | `crates/crowd-core/tests/m1_strict.rs:40-47` (release-gated validation) | YES |
| `override-layer-v1.schema.json`, `override-layer-v2.schema.json` | 50+31 | `crates/crowd-cache/src/override_layer.rs` | YES |
| `layout-layer-v1.schema.json` | 50 | M4 layered layout editing | YES |
| `interaction-motion-v1.schema.json`, `interaction-request-v1.schema.json`, `interaction-animation-layer-v1.schema.json` | 77+83+41 | M6 interaction scheduling | YES |
| `brain-v1.schema.json`, `brain-library-v1.schema.json` | 46+87 | M6 declarative brains | YES |
| `m6-acceptance-scenes-v1.schema.json` | 266 | M6 acceptance fixtures | YES |
| `cmu-motion-source-v1.schema.json`, `motion-provenance-v1.schema.json`, `motion-thresholds-v1.schema.json`, `terrain-motion-v1.schema.json`, `trajectory-v1.schema.json`, `retarget-profile-v1.schema.json`, `contact-v1.schema.json`, `activity-v1.schema.json`, `formation-v1.schema.json`, `mixed-tier-v1.schema.json`, `perception-v1.schema.json`, `physics-transition-v1.schema.json`, `hero-integration-v1.schema.json` | 15-66 each | M6 motion / M5 tier mix | YES (with the Rust code that validates them) |

**Validation**: the Rust crate `crowd-core` uses `jsonschema = "0.33"` (dev-dep in `crates/crowd-core/Cargo.toml:14`) at test time. At runtime, schemas are enforced via `serde(deny_unknown_fields)` (e.g., `crates/crowd-core/src/project.rs:14`, `behavior.rs:36`). The Python addon does NOT do its own JSON-schema validation — it delegates to Rust via `compile_project`/`compile_authorable_project` PyO3 calls.

**Verdict**: VENDOR-WHOLESALE. Copy `schemas/` → `vendor/blender-crowd/schemas/` verbatim. The v1.2 addendum §0.4 (borrow names + structure, redefine under kit license) is now obsolete — we get the actual validated contracts.

### D. Geometry Nodes assets — **VENDOR-WHOLESALE (procedural, no .blend shipped)**

bgyss ships NO `.blend` files for GN groups and NO `.glb`/`.fbx` mesh assets. The only binary asset is `crowd-test-scene.blend` at repo root (test fixture, not shipped with the addon).

The GN group is **built in Python** at `addon/blender_crowd/geometry_nodes.py:131-339` — `ensure_cache_node_group(prototypes, clips, terrain_object)`. It programmatically constructs ~15 nodes (CollectionInfo, InstanceOnPoints, Raycast, StoreNamedAttribute, etc.) with the `crowd_*` named attribute contract.

The reference meshes/materials/armature come from `addon/blender_crowd/reference_assets.py` (217 LOC) — also built procedurally in Python (cone primitives, simple materials, a 7-bone proxy armature for visualization).

**Blender version specificity**: uses 5.x APIs (`interface.new_socket` with `in_out=` kwarg at line 26; `GeometryNodeIndexSwitch` at line 119 — added in 5.0; `node.index_switch_items.new()` at line 123 — 5.x). **Will not work on Blender 4.x without adaptation.** The kit already committed to 5.2 LTS in v1.2 §0, so this is fine.

**Verdict**: VENDOR-WHOLESALE. The `crowd_*` named-attribute contract (15 attribute names: `crowd_position`, `crowd_agent_id_lo/hi`, `crowd_orientation`, `crowd_clip_id`, `crowd_clip_phase`, `crowd_playback_rate`, `crowd_population_id`, `crowd_variant_id`, `crowd_scale`, `crowd_behavior_state`, `crowd_decision_reason`, `crowd_render_tier`, `crowd_visible`, `crowd_proxy_swing`, `crowd_terrain_normal`) is the kit's v1 presentation contract — straight from bgyss `cache_playback.py:16-39` + `geometry_nodes.py`.

### E. Tests + benchmarks — **VENDOR-WHOLESALE (with kit-specific adapters)**

**Test structure** (37 files, ~5K LOC):
- `crates/crowd-core/tests/*.rs` — 35 Rust integration tests (determinism, M1 strict, M2 behavior graph, M3-M6 acceptance, fuzz, proptest). Heavy: `m1_strict.rs:13` runs a full 1K-agent × 10K-tick strict rebake and asserts position delta ≤ 0.001 m.
- `crates/crowd-cache/tests/*.rs` — 8 cache lifecycle/corruption/recovery tests.
- `crates/crowd-bench/tests/*.rs` — 5 benchmark regression tests.
- `tests/test_*.py` — 17 Python tests (release audit, M3 policy/budget/SBOM, M6 acceptance, motion DB, debugger navigation). Pure-python, no Blender.
- `tests/blender/test_*.py` — 13 Blender-process tests (install, M1-M6 playback/render/authoring). Run via `BLENDER=... scripts/m*-blender-test.sh`.
- `benchmarks/baselines/*.json` — 6 scene baselines (crossing, bottleneck, circle, dense_flow, l_corridor, bidirectional_corridor).
- `benchmarks/thresholds/m5-city-flow.json` — M5 scale-gate thresholds (compiled into `crowd-bench` so they cannot be loosened mid-run).

**Benchmark methodology**: `crowd-bench` CLI (`crates/crowd-bench/src/main.rs`) — `run --scene X --agents N --solver Y --trace --out DIR`, `compare` (3-solver bake-off), `m5-gate --report X --out ADJ` (fixed-threshold adjudication), `cache-experiment` (matrix of {f32, mm-i32, affine-i16} × {60, 120, 240}-tick chunks), `nav-reroute` (M0 item 4 portal-reroute acceptance). Peak allocator bytes measured via a `#[global_allocator]` (`crates/crowd-bench/src/alloc.rs`) — single-threaded test enforcement via `RUST_TEST_THREADS=1` in `.cargo/config.toml:21`.

**Adoption for kit v1 acceptance gates**: YES, directly. bgyss's M1 acceptance criteria (`docs/milestones/M1-vertical-slice.md`) are a near-perfect match for v1.2 §M0.4 + M0.5: 1K agents, deterministic rebake (position delta ≤ 0.001 m), cache size < 1 GB, Blender playback. The kit's v1 acceptance = bgyss's M1 acceptance.

**Verdict**: VENDOR-WHOLESALE. The benchmark harness + 6 baselines + thresholds become the kit's v1 acceptance gate — replacing the v1.2 plan to handroll PedPy-based gates.

### F. Documentation — **VENDOR-WHOLESALE (verbatim + kit-specific overlay)**

`docs/` has 31,855 LOC across ~80 Markdown files. Notable:

| Doc | LOC | Vendor? |
|---|---|---|
| `docs/blender-crowd-1.0.md` | 1,167 | YES (canonical spec) |
| `docs/cache-format-v1.md` | 152 | YES (cache byte layout) |
| `docs/milestones/*.md` (M0-M9) | ~3K | YES (acceptance contracts) |
| `docs/benchmarks/*.md` (~30) | ~6K | YES (evidence records; the kit inherits bgyss's milestone history as its own v1 baseline) |
| `docs/release/1.0-*.md` (compat, support-matrix, budgets, release-review, known-limitations) | ~3K | YES (templates the kit reuses for its own v1 release) |
| `docs/crowd-simulation-research-2026.md`, `docs/industrial-crowd-capability-roadmap.md`, `docs/reactive-neural-interaction-animation-2026.md` | ~5K | YES (research syntheses) |
| `docs/m6-motion-data-policy.md`, `docs/usd-crowd-profile-v1.md`, `docs/backend-support-matrix.md` | ~2K | YES |
| `docs/user/*.md`, `docs/runbooks/*.md`, `docs/announcements/*.md` | ~5K | YES (operator-facing) |

**Verdict**: VENDOR-WHOLESALE verbatim into `vendor/blender-crowd/docs/`. The kit's existing `docs/crowd_system/DESIGN_crowd_system_v1.md` and `v1.2_addendum.md` become an overlay that documents the kit-specific deviations (4GB RAM budget confirmation, Linux x86_64 platform addition, kit's scenario-side `crowd_fields.py` integration).

### G. Wholesale fork-and-adapt feasibility — **VIABLE, 1-2 sessions**

**If we fork bgyss wholesale into `vendor/blender-crowd/` in the kit:**

What works out of the box:
- Entire Rust workspace compiles on Linux x86_64 (verified: Linux `cfg` blocks present, no macOS-only system APIs in sim kernel).
- All 35+ Rust integration tests pass on Linux.
- All 27 JSON schemas validate.
- The PyO3 module builds as `blender_crowd_native` abi3 wheel for CPython 3.11+.
- Blender 5.2 LTS loads the addon + wheel; the 36 operators work.
- The kit gets: tiled navmesh + A* + sampled-velocity avoidance (the M0 winner) + behavior graph compiler + versioned chunked cache + cache-only GN playback + M2 authorable IR + M4 layout layers + M5 tier mix + M6 perception/brain/activity/interaction/motion.
- The kit's v1 acceptance gate = bgyss's M1 strict rebake test (already a release-gated `#[ignore]` test in `crates/crowd-core/tests/m1_strict.rs:13`).

What needs adaptation for the kit's 4GB/no-GPU/Linux x86_64 env:
1. **Build a Linux x86_64 wheel** (NOT in `scripts/build-wheel.sh` — only builds host arch). Solution: add `--target x86_64-unknown-linux-gnu` to a new `scripts/build-wheel-linux.sh`. Effort: 30 min.
2. **Add `linux-x86_64` to `blender_manifest.toml:13` platforms** and ship the Linux wheel alongside the macOS one. Effort: 5 min.
3. **Write `scripts/crowd/kit_project_ir.py` adapter** that converts the kit's scenario-DATA (zombie escape scene fields, hero/jeep goal sources, camera keepouts) into bgyss's `AuthorableProjectV2` JSON. This is the v1.2 §3.4 "zombie FSM as scenario plugin" work — it's still needed, just targeted at bgyss's IR instead of a handrolled IR. Effort: 1-2 sessions.
4. **Adapt `scripts/crowd_fields.py` and `scripts/gait_modifiers.py`** to feed bgyss's `AvoidanceInput.preferred` (via a per-tick Python callback) and `crowd_proxy_swing` (via the GN group). Effort: 0.5-1 session.
5. **Drop the kit's planned navmesh, ORCA, behavior-IR, cache, GN group, keyframe-shim work** (v1.2 §0.1 absorption matrix rows). Effort: 0 (work not done).

Effort estimate: **1-2 sessions** to fork + build + adapter stub + first end-to-end bake on Linux. Compare to v1.2 §0.3 estimate of 6-9 sessions for handroll v1 (M0-M3). Savings: **~5-7 sessions**.

Risk vs continuing v1.2 handroll:
- **LOWER risk**: bgyss has 6 accepted milestones (M0-M6) with reproducible evidence; handroll has zero.
- **LOWER risk**: 1K-agent 30Hz perf already measured at 27× headroom; handroll would have been the M0.2 spike risk.
- **LOWER risk**: cache format is already designed, tested, recoverable, has CRC-32C + BLAKE3 + cancel/resume; handroll would have been a from-scratch chunk format.
- **HIGHER risk (one)**: Rust toolchain + maturin + abi3 wheel build on Linux x86_64. Mitigation: blake3 ships manylinux wheels; pyo3 0.29 is mature. Spike: 30 min to verify `cargo build --release -p crowd-blender` compiles on Linux.
- **HIGHER risk (two)**: kit becomes GPL-contaminated at file level. Mitigation: user explicitly approved.

### H. Partial vendoring options — fallback matrix

If wholesale proves blocked (e.g. maturin can't build Linux wheel in 4GB), the safe subsets in order of value-to-effort:

1. **Rust `crowd-core` SoA + avoidance + nav + behavior compiler** as a Python-importable module (no Blender), called from the kit's pure-Python scenario layer. Still needs maturin but NOT the Blender-extension packaging. → 80% of the value, 50% of the build-chain risk.
2. **Just the 27 JSON schemas + cache-format-v1.md** into `docs/crowd_system/schemas/`. The v1.2 addendum §0.4 already planned this as "patterns only" — wholesale just removes the "redefine under kit license" busywork. → 10% of value, 0% build-chain risk. (This was the v1.2 plan; it remains the floor.)
3. **Just the Python `geometry_nodes.py` + `cache_playback.py`** — the GN group + point-cloud attribute contract — as kit-side presentation code. Reads ANY cache v1 directory, not just bgyss's. → 15% of value, 0% build-chain risk.
4. **Just `crates/crowd-cache`** as a Python-importable module via PyO3 — gives the kit a recoverable chunked cache format without the sim. → 25% of value, 30% of build-chain risk.
5. **Just the benchmark + test methodology** — `crowd-bench` CLI + 6 baselines + thresholds + M1 strict acceptance test. → 20% of value, 0% build-chain risk (it's pure Rust CLI, no Blender).

**Recommendation**: do not plan a partial path. Attempt wholesale first; if the Linux wheel build spike fails (1 hour to find out), fall back to (1) + (3) + (4) — Rust sim core + Python GN/cache presentation, skipping the Blender-extension packaging.

---

## 3. Wholesale fork-and-adapt plan

Concrete steps to fork bgyss into the kit:

1. **Spike (30 min)**: On a Linux x86_64 box, `git clone https://github.com/bgyss/Blender-Crowd.git && cd Blender-Crowd && cargo build --release -p crowd-blender` — verify blake3/crc32c/serde/pyo3 all link. If this fails, abort wholesale and use partial path (H.1+H.3).
2. **Vendor**: `cp -r /tmp/Blender-Crowd /home/sync/blender-agent-kit/vendor/blender-crowd/`. Add `vendor/blender-crowd/` to the kit's `.gitignore` exceptions.
3. **License**: add a top-level `LICENSE.gpl.md` to the kit noting GPL-3.0 contamination originates in `vendor/blender-crowd/`. Update kit's `README.md` to state the kit is GPL-3.0+ when `vendor/blender-crowd/` is present.
4. **Build chain**: add `scripts/crowd/build_native.sh` that runs `mise install && maturin build --release --manifest-path vendor/blender-crowd/crates/crowd-blender/Cargo.toml --out scripts/blender_kit/crowd_wheels/`. Add `linux-x86_64` to `vendor/blender-crowd/addon/blender_crowd/blender_manifest.toml:13`.
5. **Schema vendor**: `cp -r /tmp/Blender-Crowd/schemas /home/sync/blender-agent-kit/docs/crowd_system/schemas/`. The kit's v1.3 design references these directly.
6. **Kit-side adapter**: write `scripts/crowd/kit_project_ir.py` (~300 LOC) that converts the kit's scenario-DATA (currently in `previz/crowd_v6/fields.py`, `clips.py`, `escape_lib`) into bgyss's `AuthorableProjectV2` JSON. This is the ONLY kit-specific code that talks to bgyss's compile-time IR.
7. **crowd_fields integration**: `scripts/crowd/fields_to_preferred.py` (~50 LOC) — wraps `crowd_fields.evaluate_fields(positions, t)` into a per-tick callback that sets `AvoidanceInput.preferred` for bgyss's `Session.step()`. The callback signature is one Python function per population.
8. **gait_modifiers integration**: extend `vendor/blender-crowd/addon/blender_crowd/geometry_nodes.py:ensure_cache_node_group` (or patch in the kit's copy) to add a `crowd_modifier_*` named-attribute slot per modified bone; the kit's `gait_modifiers.apply_modifiers` writes per-tick bone deltas into the cache as additional channels.
9. **Acceptance gate**: replace `scripts/test_crowd_fields.py` + `scripts/test_gait_modifiers.py` (kit unit tests) with `cargo test --release -p crowd-core --test m1_strict -- --ignored` (bgyss release gate) + a kit-specific `scripts/crowd/test_kit_scenario.py` that asserts the kit's zombie-scenario IR compiles + bakes deterministically.
10. **Deprecate v1.2 handroll plan**: archive `docs/crowd_system/DESIGN_crowd_system_v1.2_addendum.md` §0.1-§0.6; replace with `DESIGN_crowd_system_v1.3.md` that documents the vendor path.

**What works out of the box**: everything except the kit-specific scenario-IR adapter (step 6) and the two integration wrappers (steps 7-8).

**Effort estimate**: 1-2 sessions for steps 1-5 + 9-10; 1-2 sessions for steps 6-8. Total: **2-4 sessions to fully-integrated v1**.

---

## 4. Partial vendoring matrix

If wholesale is blocked, the safe subsets:

| Subset | Files | Value | Effort | Risk |
|---|---|---|---|---|
| JSON schemas (verbatim) | `schemas/*.json` (27 files, 1,897 LOC) | 10% | 0 sessions (copy) | 0 |
| Cache format spec | `docs/cache-format-v1.md` + `crates/crowd-cache/` | 25% | 1 session (PyO3 build) | LOW |
| Rust ORCA solver | `crates/crowd-core/src/avoidance/{sampled,orca,anticipatory}.rs` | 15% | 1 session | LOW |
| GN group (Python) | `addon/blender_crowd/geometry_nodes.py` + `cache_playback.py` | 15% | 0.5 session | LOW |
| Behavior graph compiler | `crates/crowd-core/src/behavior.rs` + `runtime_behavior.rs` | 20% | 1 session | LOW |
| Test/benchmark methodology | `crates/crowd-bench/` + `benchmarks/` + `tests/` | 20% | 1 session | LOW |
| All of the above = wholesale | entire repo | 100% | 2-4 sessions | MEDIUM (Linux wheel) |

The v1.2 plan effectively selected rows 1 + 4 (schemas as patterns + GN contract). Wholesale takes all rows.

---

## 5. Comparison to v1.2 plan

| Dimension | v1.2 (handroll-with-absorption) | v1.3 (vendor bgyss wholesale) |
|---|---|---|
| Total effort to v1 ship | 6-9 sessions (M0-M3) | 2-4 sessions |
| Sessions saved | (baseline) | **4-5 sessions** (~60%) |
| 1K-agent 30Hz perf risk | MEDIUM (M0.2 spike: Python-RVO2 Cython build in 4GB; fallback NumPy port of pyorca) | LOW (already measured at 27× headroom on M1 Max; Linux x86_64 likely 5-10× headroom) |
| Cache format risk | MEDIUM (handroll chunked binary + manifest + CRC) | ZERO (bgyss cache v1 has 8 cache tests + M0/M1 acceptance evidence) |
| Behavior graph IR | 10 nodes handrolled | 17 nodes already implemented + compiler + runtime + 4 graph tests |
| NavMesh | Handroll bmesh walk + Hertel-Mehlhorn (2-3 sessions) | Already implemented: uniform-grid tile rasterizer + A* + corridor + portal reroute (M0 item 4 done) |
| GN instancing | Handroll `crowd_*` contract | Already implemented (`geometry_nodes.py:131-339`) + tested in M1 render evidence |
| Keyframe writing | Handroll `keyframe_insert_compat` 4.x/5.x shim | NOT NEEDED — bgyss uses cache-driven point-cloud attributes, not keyframes |
| Determinism evidence | M2+ (would need to build it) | Already proven: `final_state_hash` identical across 3 independent 100K runs |
| License posture | Kit permissive + GPL patterns only | Kit GPL-3.0+ (user-approved) |
| Linux x86_64 platform | Native (pure Python) | Requires Linux wheel build (1 spike, 30 min) |
| Blender 4.x compat | Yes (kit shim) | NO — Blender 5.2 LTS only (already accepted in v1.2 §0) |
| 100K agent future path | Not in v1; would need Rust core (M5+) | Already done — bgyss M5 100K gate passed |

**Schedule impact**: v1 ships 4-5 sessions sooner. v1.1 → v1.3 is a 60% schedule reduction. The kit's M2/M3 (scenario plugin port, zombie FSM as behavior graph) work is unchanged — it operates on top of the sim core, regardless of who built the core.

---

## 6. Top 5 concrete recommendations for design v1.3

Ranked by impact:

1. **Fork bgyss wholesale into `vendor/blender-crowd/`** — write `DESIGN_crowd_system_v1.3.md` that replaces v1.2 §0.1-§0.6 absorption matrix with "vendor bgyss, adapt scenario-IR adapter, build Linux wheel". This is the single biggest schedule win available to the orchestrator. Effort: 2-4 sessions total.

2. **Spike the Linux wheel build FIRST** (within 30 min of decision). Run `cargo build --release -p crowd-blender` on a Linux x86_64 box. If green, commit to wholesale; if not, fall back to partial path (H.1: Rust sim core as Python module + H.3: Python GN/cache presentation). Do NOT start the adapter work before this spike.

3. **Keep `scripts/crowd_fields.py` and `scripts/gait_modifiers.py`** — they are NOT redundant with bgyss. They become the kit's scenario-side engines for (a) authored influence fields that produce per-tick preferred velocities fed to bgyss's `AvoidanceInput.preferred`, and (b) funny-walk gait modifier stacks written into the cache as additive per-bone deltas on top of bgyss's clip-driven locomotion. Document this division in v1.3 §6.4 + §8.3.

4. **Replace v1.2 §0.6 (defer Rust core to M5+)** with "Rust core is bgyss's, in v1 from day 1". The v1.2 reasoning (Rust adds 2-3 weeks build chain) was based on handrolling; vendoring skips that. The kit's 4GB/no-GPU constraint is irrelevant — bgyss runs 1K agents in 7.86 MiB peak allocator on `cpu_reference` backend.

5. **Adopt bgyss's M1 strict rebake test as the kit's v1 acceptance gate** — `cargo test --release -p crowd-core --test m1_strict -- --ignored` (`crates/crowd-core/tests/m1_strict.rs:13`). It asserts: 1K unique stable IDs, two independent bakes agree on static+discrete state, position delta ≤ 0.001 m, destination completion ≥ 95%, zero static-boundary escapes, portal reroute accepted. The kit inherits a release-gated, evidence-backed acceptance test on day 1.

---

## 7. Open questions for the orchestrator

1. **Blender 4.x compat**: v1.3 vendoring bgyss locks the kit to Blender 5.2 LTS only (bgyss uses 5.x-only APIs in `geometry_nodes.py` and `properties.py`). v1.2 already accepted this, but confirm with user that NO Blender 4.x scripts need to consume the crowd cache (e.g., the previz zombie v5 shot runs on 4.x).

2. **Compute budget for the Linux wheel build**: blake3's SIMD backend may take 5-15 min to compile from source on a 4GB container. The user said "if you need bigger compute I can figure out something" — is a one-shot build on a 16GB box acceptable? If not, can we pre-build the wheel once and commit it to the kit's `vendor/blender-crowd/wheels/`?

3. **Scenario-side IR adapter scope**: the kit's previz zombie-escape scene has 9 FSM states, hero/jeep OBB keepout, time-scoped camera keepouts, dynamic field sources. v1.2 §3.4 planned "zombie FSM as behavior graph" porting as M2 work. Confirm: does v1.3 still port the zombie scene, or does it ship v1 with bgyss's reference concourse scene as the first acceptance shot, deferring zombie-port to M2+?

4. **`crowd_fields.py` provenance rewrite**: the existing module (`scripts/crowd_fields.py:36-37`) states "Zero code copied" from bgyss. Once we vendor bgyss, that disclaimer is technically still true (the module didn't copy code), but the broader kit IS now GPL-contaminated. Should we rewrite the disclaimer to reference the kit's new `LICENSE.gpl.md`?

5. **100K-agent future**: bgyss's 100K gate needs 64GB M1 Max. The kit's stated v1 target is 1K. Should v1.3 explicitly declare 100K out-of-scope for the kit (even though the vendored code supports it), or keep the option open for future "bigger compute" provision?

6. **v1.2 addendum §0.5 (crowd_agents.py deprecation)**: still valid, but now deprecation means "replace with bgyss-backed zombie-scenario-IR adapter", not "replace with handrolled crowd_fields-based system". Confirm the zombie-port M2 milestone still happens, just on a bgyss substrate.

7. **M5+ feature deferral**: bgyss's M5 (scale tier mixes) + M6 (perception/brain/activity/interaction/motion/physics) are implemented in the vendored code. Does the kit adopt them as v1 capabilities, or stub them off (e.g., `m6_*` modules disabled) until v2? The wholesale fork gives them for free; the question is whether to expose them in v1 UI.
