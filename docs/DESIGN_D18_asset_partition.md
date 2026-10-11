# DESIGN D18 — Asset Partition Protocol (git-durable .blend chunking)

Status: REV-3 FINAL (critique round 1: 15 findings adopted [A#];
critique round 2: N1–N12 adopted [R2#]). Reviews:
docs/DESIGN_D18_critique_1.md + output/r9/D18_critique_2.md.
Research probes: output/r9/chunk_probe{,2,3,3b}.json,
d18_write_semantics.json, d18b_unpack_semantics.json,
d18c_packed_payload.json.
Owner: principal (session 13, R9 lane) · Date: 2026-10-11
Trigger: user directive — "check if blender has a way to break a big
scene/project into smaller files it can import" (GitHub 100MB blob
limit killed the R7 wrap once already).

## SCOPE: WHICH FILE IS CHUNKED [R2#N4]

The chunked source is the PRISTINE Blender Foundation demo file
`polyhaven_cache/loft/loft.blend` (561,122,088 bytes; provenance
download.blender.org/demo/cycles/loft.blend via
scripts/r6_loft_fetch.sh — the "polyhaven" name is an R6 misnomer).
It carries NO kit_* props: labels (1155/1200), shell cuts, props and
actors are DERIVED states applied downstream by the R6–R8 chain and
are reproducible from committed scripts against the rebuilt master.
loft_master.blend therefore REPLACES the GitHub Release + re-fetch as
the chain's input. kit_* manifest fields stay as forward-compat
(expected-empty for this source). The manifest_diff certification
baseline is a look manifest of the PRISTINE source — never the R6
handoff manifests (those carry labels; diffing against them explodes
with ~1155 false label_changed findings).

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
  `assets/loft/textures/<safe_name>` (sanitizer [R2#N8]: extension
  preserved, charset `[A-Za-z0-9._ -]` else `_`, length ≤120,
  CASE-INSENSITIVE collision → hash suffix; sha256 dedup — identical
  bytes collapse to one file with two manifest entries) → flip image
  to FILE-source with path `//textures/<file>` — correct at loft_ext's
  OWN location (assets/loft/) [R2#N5 flip-twice] → record colorspace
  → save `assets/loft/loft_ext.blend` (compress=True; if the 8
  dead-path stubs abort the compressed save [R2#N6 — R6 recorded
  such behavior], detach them in loft_ext and re-create the stubs on
  rebuild from the manifest; parity 130 unchanged) — intermediate,
  gitignored, rebuildable from the original. MemAvailable guard
  before open.
- **Run B (write chunks)**: open loft_ext → IMMEDIATELY re-point all
  122 images to `//../textures/<file>` (the chunk-baked form — every
  session is resolution-correct by construction) → live pre-flight
  asserts (survey invariants: no constraints/shape keys/cross-subtree
  refs, co-user groups intact, LOCAL-ID name uniqueness per class
  [R2#N9 — per-library namespaces legally collide; the 4 linked NGs
  have no local referencers], light census, compositor tree empty
  [R2#N10], user-less rider enumeration) → bin-pack → write chunks +
  manifest → **mutation guard**: per-class ID counts identical
  before/after all write() calls [R2#N12].

**Bin packing** ([A1] amended + [R2#N11]): unit = a ROOT SUBTREE,
merged with any mesh-co-user groups it touches ([A6]). Estimate per
unit = subtree mesh bytes × 1.5 (images excluded — externalized;
materials are KBs). Greedy first-fit-decreasing into bins with budget
60MB; the packer asserts its own totals (total_est > 0, per-unit est
> 0) and writes them to the manifest. The REAL gate is the written
file <90MB on disk, checked after every write. NO automatic re-split:
an over-gate MULTI-subtree chunk is an operator re-bin (STOP-AND-FLAG
exit 4); a single unit over the gate alone is likewise exit 4
(largest single mesh 44MB raw — no expected trigger).
**chunk_00_scene carries EXACTLY** [R2#N3]: objects {Area, Area.002,
<the camera>} + the world ID + user-less rider IDs (see below) + the
scene-settings record. The 2 collection-resident lights ride their
collection's normal bin — chunk_00 does NOT re-enumerate them.
Pre-flight asserts the light census (2 root orphans + 2 elsewhere =
4 total) and that chunk write sets are PAIRWISE DISJOINT with
|∪| = 1225 — asserted on the manifest object lists at write time
(post-append consolidation must never be the thing that masks a
double-enumeration).

**User-less riders** [R2#N2]: in Run B, every LOCAL user-less ID
(material/image/mesh/node_group with zero users — probe1 shows 179/180
materials used, so ≥1 orphan material exists; the 8 verbatim image
stubs may also be orphans) is written EXPLICITLY into chunk_00's set
with `use_fake_user = True` set immediately before the write
(fake_user survives write+append and makes them purge-immune), and
recorded in the manifest. Rebuild ordering: append chunk_00 FIRST,
assign scene.world immediately (gives the world a live user before
any purge), append remaining chunks, consolidate, THEN orphans_purge,
then parity. Expected parity counts are thereby mechanical, not
hoped-for: objects 1225, meshes 1184, materials 180, images 130
(122 externalized + 8 verbatim stubs), node_groups 3, lights 4,
cameras 1.

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

**Rebuild** (`rebuild_asset.py`) [R2#N1, R2#N7 amended]:
step 0: `bpy.ops.wm.read_factory_settings(use_empty=True)` + assert
the session is truly empty (bpy.data.objects == [] and
bpy.data.collections == []) — the factory-startup Cube/Camera/Light/
Collection would otherwise collide with same-named source IDs and the
consolidation pass would silently SWAP GEOMETRY (the factory Cube is
a mesh co-user group name!). Exact-name consolidation is therefore
safe ONLY under the empty-session law; any pre-append local ID of a
consolidated class = STOP-AND-FLAG. Then: recreate the collection
TREE (incl. nested "Collection.001"; scene-root objects → scene root)
→ append chunk_00 FIRST + assign scene.world → append remaining
chunks' objects exactly once → **consolidation pass** [A2]:
`old_id.user_remap(new_id)` any `.001` duplicate onto the first
instance (match by exact name; images additionally by identical
filepath), then bpy.data.orphans_purge() (safe: chunk_00 riders carry
fake_user, world assigned before purge), then exact count parity vs
manifest INCLUDING POLY PARITY (Σ verts, Σ polygons per class — the
only deterministic gate for a same-name data swap) → re-apply ALL 25
parent pairs by name + restore matrix_parent_inverse → assign kit_*
props (no-op, expected-empty) → **image path fixup** [A4 + R2#N8]:
MANIFEST-KEYED — for each texture-table entry set
`img.filepath = "//textures/<file>"` (cross-check assert: exactly 122
images carry the `//../textures/` prefix, 8 stubs carry verbatim dead
paths, 0 others) → restore world (assert 11 nodes + HDR link) +
scene settings → save `assets/loft/loft_master.blend` (gitignored —
rebuildable) → **image existence verify AFTER save** [R2#N7]:
`bpy.path.abspath(img.filepath, start=master_dir)` — LAW: never
resolve a `//` path before the session file is saved at its final
location, or pass `start` explicitly (unsaved `//` falls back to CWD
and the verify can never pass) → **verify**: object name-SET equality
(exact), count parity (incl. poly parity), light/camera counts,
parent world-matrix check, kit_* parity (expected-empty), image path
existence (122 expected-present; 8 stubs expected-dead, counted),
node_group count; plus the kit's manifest_diff vs the pristine-source
look manifest (0 findings = certified).

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
