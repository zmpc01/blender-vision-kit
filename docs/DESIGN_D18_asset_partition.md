# DESIGN D18 — Asset Partition Protocol (git-durable .blend chunking)

Status: REV-2 (post-critique round 1 — 15 findings, verdict
SHIP-WITH-AMENDMENTS, all blockers/must-fixes adopted; amendments
marked [A#]). Research probes: output/r9/chunk_probe{,2,3,3b}.json,
d18_write_semantics.json, d18b_unpack_semantics.json,
d18c_packed_payload.json.
Owner: principal (session 13, R9 lane) · Date: 2026-10-11
Trigger: user directive — "check if blender has a way to break a big
scene/project into smaller files it can import" (GitHub 100MB blob
limit killed the R7 wrap once already).

## Problem

loft.blend is 561MB. GitHub rejects blobs >100MB (GH001), so the asset
can never live in git as one file; today it survives only via (a) the
GitHub Release "level-asset-loft" and (b) polyhaven re-fetch. A fresh
clone is NOT self-sufficient for the level lanes, and a Release is a
second-class git citizen (no clone transport, needs API curl).

## Blender-native answer (all measured this session)

Blender's sub-packaging IS multi-file libraries:

1. `bpy.data.libraries.write(path, {ids}, compress=True)` writes any ID
   set + the FULL DOWNWARD dependency closure (object→mesh→material→
   image measured; children NOT pulled by parents — subtree must be
   enumerated explicitly). 5.2 API: arg 2 is a SET.
2. Collections carry NO objects when written — chunk unit = object set.
3. Append has NO dedup (2nd append of the same name → `.001`) — the
   rebuild appends each object exactly once AND consolidates any
   cross-chunk datablock duplicates ([A2]).
4. PACKED pixel buffers DO travel inside written chunks (measured:
   +198KB noise payload) — packed chunking is self-contained but
   duplicates every shared image per chunk (materials have up to 838
   users; 425MB of packed images would multiply 3-5×). Externalize.
5. Unpacked FILE-source images write as PATH REFERENCES; `//`-relative
   paths resolve against the chunk file's location (measured across a
   moved directory). On APPEND the `//` re-anchors to the APPENDING
   (master) file — post-append path fixup required ([A4]).
6. zstd compress=True: ~2-3× on mesh payloads (never used for size
   prediction; the gate is the real written file size).
7. The asset references 18 external .blend libraries with 47 MISSING
   linked datablocks (35 images, 4 node groups — vendor addon paths).
   Measured [A3]: write() SUCCEEDS with these in the closure; the
   linked stubs are silently DROPPED (images:[] in the reopened
   inventory) — post-rebuild, those image nodes point at nothing,
   cosmetically equivalent to the source's dead paths (renders never
   used them: R6-R8 evidence).

## Asset survey results (the design is data-fit, not generic)

- 1225 objects (1200 MESH, 4 LIGHT, 20 EMPTY, 1 CAMERA); 1200 roots,
  25 parent pairs (Bed01 EMPTY assembly + 6 MESH-parented children).
- 5 top-level collections: Collection(19, +1 nested empty "Collection
  .001"), Living(96), Kitchen(858), Bad room(248), Blue hour(2) + 2
  scene-root orphans (Area lights).
- Images: 167 IDs = 122 packed (incl. the world's 24.78MB EasyHDR) +
  8 FILE-unpacked vendor stubs (dead paths, preserved verbatim) +
  35 linked missing (dropped on write, recorded) + 2 internal
  (RENDER_RESULT/Viewer, skipped). Names unique EXCEPT Metal09_met/
  nrm/rgh (×2 each — both linked stubs; no packed collision; exporter
  still hash-guards names).
- Mesh datablocks: 1184 (7 co-user groups: Cube.008×2, Cube×4,
  Mesh.002×5, Mesh.007×4, Plane.010×4, Plane06×2, Plane08×2 — co-user
  groups share one bin-unit so they never split [A6]).
- NO constraints, NO shape keys, NO curve/text/armature objects.
  Modifiers: 22 NODES (all the same no-input "Auto Smooth" group),
  3 SOLIDIFY, 1 DISPLACE, 1 SUBSURF, 1 PARTICLE_SYSTEM (no instancing
  targets). NO cross-subtree ID references (modifier props, GN node
  graphs, particles — all measured; NodesModifier idprops are not
  enumerable in 5.2, noted as an unscannable residual).
- World: EasyHDR (11 nodes, pulls the packed HDR — measured closure).
- Scene: 30fps, CYCLES, 1080×1350 + color management to be captured.
- kit_* custom props: object/mesh/collection kit_label, kit_semantic,
  kit_label_conf must round-trip (R6 chain depends on them).
- Memory: MemAvailable 1684MB after opening the packed original —
  two-run pipeline mandatory ([A9]).

## Design (REV-2)

Goal: `git clone` → `rebuild_asset.py` → working loft scene, no
Release, no network. Committed artifacts: texture files (each
<100MB), chunk .blend files (each <90MB), chunks_manifest.json.

**Two-run pipeline** ([A9], MemAvailable ≥2.4GB guard before each):

- **Run A (export textures)**: open the packed original → for each of
  the 122 packed images write `img.packed_file.data` to
  `assets/loft/textures/<safe_name>` (extension preserved, sha256
  dedup — identical bytes collapse to one file with two manifest
  entries, name-collision → hash suffix) → flip image to FILE-source
  with path `//../textures/<name>` relative to the FUTURE chunk dir →
  record colorspace → save `assets/loft/loft_ext.blend`
  (compress=True; expected ~100-150MB — intermediate, gitignored,
  rebuildable from the original). MemAvailable guard before open.
- **Run B (write chunks)**: open loft_ext (~135MB session) → live
  pre-flight asserts (the survey invariants above: no constraints/
  shape keys/cross-subtree refs, co-user groups intact, name
  uniqueness per ID class) → bin-pack → write chunks + manifest.

**Bin packing** ([A1] amended): unit = a ROOT SUBTREE, merged with any
mesh-co-user groups it touches ([A6]). Estimate per unit = subtree
mesh bytes × 1.5 (images excluded — externalized; materials are KBs).
Greedy first-fit-decreasing into bins with budget 60MB (estimate
deliberately conservative; the REAL gate is the written file <90MB on
disk, checked after every write). A unit whose WRITTEN chunk exceeds
90MB → STOP-AND-FLAG exit 4 (largest single mesh is 44MB raw — no
expected trigger). chunk_00_scene carries: the 4 lights + camera + 2
orphan Area lights, the world ID, and the scene-settings record.

**Chunk manifest** (`assets/loft/chunks_manifest.json`): per chunk —
file, bytes, object list (name, collection path, kit_* props), parent
pairs (child, parent, parent_inverse 4×4) [A5], world + ~12 scene
settings (fps, engine, res, view_transform, look, exposure,
display_device, cycles device/samples/adaptive, use_nodes, unit
system+scale, view layers) [A8], texture list (name→file sha256,
colorspace), dropped-stub list (35 linked IDs + the 8 verbatim dead
paths) [A3, A12], source asset sha256, expected rebuild counts
(objects 1225, meshes 1184, materials 180, images 130, node_groups 3,
lights 4, cameras 1).

**Rebuild** (`rebuild_asset.py`): empty file → recreate the collection
TREE (incl. nested "Collection.001"; scene-root objects → scene root)
→ append each chunk's objects exactly once → **consolidation pass**
[A2]: user_remap any `.001` duplicate datablock onto the first
instance (match by exact name; images additionally by identical
filepath), bpy.data.orphans_purge(), then exact count parity vs
manifest → re-apply ALL 25 parent pairs by name + restore
matrix_parent_inverse → assign kit_* props → **image path fixup** [A4]:
re-point `//../textures/*` to master-relative `//textures/*`,
then verify `os.path.exists(bpy.path.abspath(img.filepath))` for the
122 externalized images (the 8 verbatim stubs are expected dead —
counted, not errors) → restore world (assert 11 nodes + HDR link)
+ scene settings → save `assets/loft/loft_master.blend` (gitignored —
rebuildable, kept out of git to avoid content duplication) →
**verify**: object name-SET equality (exact), count parity, light/
camera counts, parent world-matrix check, kit_* props parity,
image path existence, node_group count; plus the kit's manifest_diff
vs a source look manifest (0 findings = certified).

**Fresh-clone proof**: clone to a NEW directory (local clone is
sufficient proof; no network dependency), run rebuild + manifest_diff
+ one look render on the rebuilt scene. Cold-start documented.

**Git mechanics** [A10]: `git gc --prune=now` FIRST (a 561MB
unreachable loose blob from the R7 accident sits in .git — verified
not reachable from main, so pushes are safe, but gc reclaims the
disk). Batch commits ≤~250-300MB of new payload per push (textures in
2 batches, chunks in 3-4 batches), rebase between. Chunk files are
IMMUTABLE once pushed: any re-split permanently adds another ~0.6GB
of history — the manifest records source sha256 so a changed asset
means a NEW asset directory (assets/loft_v2/...), never an in-place
rewrite. Library-LINK master output CUT [A13] (chunks carry no
collections; link-master needs per-object plumbing and overlaps the
append-master + glTF preview paths — one artifact, one correctness
surface).

## Rejected alternatives

- Packed chunks only: 425MB × 3-5 duplication — rejected on size.
- GitHub LFS: free tier is 1GB storage / 1GB-mo bandwidth; NOT
  unlimited (corrected from the user's worst-case assumption). Release
  assets (2GB each) dominate LFS for this repo; in-git chunks dominate
  both for clone-transport.
- Byte-level gz-splitting: not Blender-native (no partial import
  value, byte-splice reassembly) — rejected.

## Risks / honest limits

- The 35 missing vendor image stubs become None links (source-asset
  truth preserved; documented, not fixed).
- NodesModifier idprops unscannable in 5.2 — the pre-flight records
  this residual honestly (all 22 GN modifiers are the no-input Auto
  Smooth group; risk accepted as negligible for THIS asset).
- Repo grows ~0.6-0.8GB. Release + polyhaven fetch remain as compact
  alternatives; chunks are the clone-transport tier.
- Manifest_diff twin-matching: rebuilt object names are exact-equal,
  so the diff's geometric-twin logic should never fire; any finding
  is a real defect.
