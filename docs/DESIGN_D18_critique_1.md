# D18 CRITIQUE 1 — R9-CRIT-1 (fresh-eyes design audit, pre-implementation)

Audited: `docs/DESIGN_D18_asset_partition.md` (DRAFT-1) against measured
evidence: `output/r9/d18_write_semantics.json`, `d18b_unpack_semantics.json`,
`d18c_packed_payload.json`, `chunk_probe.json`, `chunk_probe2.json`, plus the
probes' source (`scripts/r9_d18_write_semantics.py`, `r9_chunk_probe2.py`),
`scripts/manifest_diff.py`, kit doctrine (AGENTS.md / .agents/SKILL.md), and
live git state of the repo.

Audit method: adversarial trace of every pipeline stage (survey → texture
export → bin-pack → chunk write → append rebuild → verify → push) against the
probe JSONs and against what `manifest_diff` can and cannot see.

---

## FINDINGS

### 1. BLOCKER — the packing estimate contradicts the design's own probe data; STOP-AND-FLAG will misfire on ~11 roots
Attacks: §Design B ("estimated size = subtree mesh bytes + subtree unique
packed image bytes … a subtree too big for its own chunk = STOP-AND-FLAG exit
4 … (no subtree exceeds this here: largest single mesh 44MB)").

`chunk_probe.json roots_top20`: Plane.002 est **101.4MB**, kitchen.365/829/364/
828/830 **93.3–93.4MB**, kitchen.274/275/582/583 **93.1MB** — eleven roots
above the 90MB gate by the design's OWN estimate formula. The parenthetical
"no subtree exceeds this here" compares to largest MESH (44MB, probe2), not to
the estimate the gate keys on. As written, the packer halts on chunk 1 — or
worse, the implementer silently "fixes" it by raising capacity past 101MB and
blows the GitHub limit.

Root cause: the estimate counts **packed image bytes that will not be in the
chunks** (§A externalizes every packed image before chunk writes; chunks carry
`//../textures/` path refs, measured ≈0 bytes in d18b). For kitchen.365 the
estimate is ~93MB of which ~85MB is externalized images and ~8MB is mesh.
The estimate is wrong in the *dangerous* direction: massively over, which
either fires STOP-AND-FLAG or fragments the plan into ~1 object/chunk for the
entire Kitchen collection.

Amendment:
- Estimate = mesh bytes × 1.5 overhead factor + material-closure allowance
  (node trees are KBs; assert per-chunk material bytes < 2MB). Images contribute
  0 (externalized).
- The 90MB gate keys ONLY on the real written file size. Single-subtree chunk
  still >90MB on disk = STOP-AND-FLAG (expected: never fires; largest mesh 44MB).
- Specify the re-split loop for a MULTI-subtree chunk that writes over gate:
  drop the last subtree, rewrite, re-gate (currently unspecified).
- Fix `sum_root_est_mb: 0.0` in probe1 (accumulation bug) — the packer must
  compute and assert its own totals (`total_est > 0`, per-object est > 0) so a
  silent zero can never produce an empty plan.

### 2. BLOCKER — the `.001` law is applied to objects but waved away for materials/meshes/images; the rebuild's own verify gate fails on the first honest run
Attacks: §Blender-native answer ¶3, §Design D, §Risks ("Material duplication
across chunks … ~KBs each — acceptable"; "rebuild relies on append-localize
semantics which handles same-name images by name-matching within the batch").

The design itself measured append dedup semantics: `append_dedup` → second
append of the same name yields `.001`. This law does not stop at objects:
- The 838-user material (`mat_max_users`) is pulled into the closure of EVERY
  chunk containing one of its 838 objects. After N chunks append, the session
  holds N copies (`Wood`, `Wood.001`, … `Wood.00N`); each chunk's objects link
  to their own copy. Same for every material shared across chunks.
- **Mesh co-users exist**: 1200 mesh objects vs **1184 mesh datablocks**
  (probe1) — up to ~16 meshes are shared by 2+ objects. If co-users land in
  different chunks, the mesh is written twice → `sub02` + `sub02.001` on
  rebuild → any per-mesh kit op (`split_mesh` REFUSES on co-user meshes;
  D16) sees a different world than the source.
- Images shared across chunks arrive as `X` + `X.001` (both pointing at the
  same `//../textures` file — renders fine, counts wrong, pixels loaded twice
  at render).

"~KBs each, acceptable" mischaracterizes this: it is not a size cost, it is
MATERIALIZATION as `.001` duplicates — and §D's verify ("mesh/image/material
counts vs the source manifest") FAILS on the first honest run. The design has
no mechanism to reach 0 findings. This is the failure that surfaces after the
700MB push.

Amendment:
- Add a **post-append consolidation pass** to §D: for materials/meshes/images,
  remap `.001` duplicates onto the first instance by exact name (+ for images
  also require identical `filepath`) via `bpy.data.user_remap`, then
  `bpy.data.orphans_purge()`, THEN assert exact count parity with the source
  (180 / 1184 / 167). Name-keyed merging is safe ONLY under source name
  uniqueness per class.
- Extend the writer-side uniqueness assert (design currently asserts it for
  images only) to ALL ID classes: objects, meshes, materials, collections,
  lights, cameras, worlds, node groups. Names are unique per (library, class)
  in Blender, so the 35 linked images live in per-library namespaces — assert
  across the full 167, not the local subset.
- Belt-and-suspenders alternative (keep as documented fallback): make the
  bin-pack unit a **co-use-connected component** (objects sharing a mesh must
  share a chunk). Cheaper to do the consolidation pass; pick one, write it down.

### 3. BLOCKER — writing chunks whose closure contains MISSING-library linked IDs (35 images, 4 node groups) is unmeasured; the first vendor-material chunk may hard-error
Attacks: §Blender-native answer ¶7 ("Chunks must preserve these stubs without
crashing"), §A ("Library-linked images are SKIPPED"), §Risks.

The synthetic probe (test 6, `write_linked`) wrote a linked ID whose library
file **existed**. The real asset's 35 linked images + 4 linked node groups
point at `D:/Blender/addon/InteriorEssentials…` / `Botaniq` paths that do not
exist on this box. Nothing measured what `libraries.write()` does when the
closure pulls a linked ID whose LIBRARY FILE IS MISSING: silent stub copy,
or exception that kills the whole chunk write. Any chunk containing a
vendor plant/book/pot material probably contains one. If write() errors, the
entire plan stalls at the first chunk — discovered mid-implementation, not at
design time, exactly the expensive kind of surprise.

Amendment:
- One more probe BEFORE implementation: write an object whose material
  references a missing-library linked image; record behavior.
- Design the fallback now: in the split run, localize broken linked IDs to
  local placeholder datablocks (keep name + filepath + colorspace, drop the
  library ref) so chunk writes never touch a dead library. Record in the
  manifest which 35 IDs were stubbed.
- Fidelity note: stubs written from a linked context may come back LOCAL
  (library=None) after append. `look.py`'s D15 display-color sync treats
  linked data differently ("linked read-only" line); record linked-status per
  image in the manifest and assert parity in rebuild verify, so "missing by
  design" stays byte-honest (35 broken both sides, same names, same paths).

### 4. MUST-FIX — `//../textures` is chunk-relative; the appended master resolves it against the WRONG directory
Attacks: §A ("chunk-relative `//../textures/<name>` path"), §Design D (master
saved at `assets/loft/loft_master.blend`).

d18b measured that `//` paths resolve against the chunk's location when the
chunk is OPENED — but on APPEND the filepath string is copied verbatim into
the consuming file and `//` re-resolves against THE MASTER's location. Master
at `assets/loft/` + image `//../textures/x.png` → `assets/textures/x.png`
→ missing. Every texture on the rebuilt master is broken on reload; pixels
are lazy (d18b: `has_data: false, size [0,0]`), so NOTHING fails until the
first render. Counts/bbox/poly verifies are blind to it; only the step-E look
render catches it visually — too late and non-deterministic.

Amendment (pick one, specify it):
- Rebuild applies a post-append path fixup: every non-broken image gets
  `img.filepath = "//textures/<basename>"` (master-relative), OR
- save the master at `assets/loft/chunks/loft_master.blend` so `//../textures`
  resolves correctly by construction (uglier layout, zero code).
Either way add a deterministic verify: for all images not in the
broken-in-source list, `os.path.exists(bpy.path.abspath(img.filepath))` must
be True. Do not rely on eyes.

### 5. MUST-FIX — the parenting measurement is void; "no-op if intra-batch resolved" is an unverified claim, and `matrix_parent_inverse` is unrecorded
Attacks: §Design B/D ("re-apply any parent pairs (no-op if intra-batch
resolved; verified)"), §Blender-native answer ¶1.

`d18_write_semantics.json` `append_parenting: {"child_parent": null}` does NOT
measure intra-batch parent restoration. Read the probe source: test 7 requests
`["testobj", "testchild"]` from a file that only ever CONTAINED `testobj` (the
child was never in any write set — test 1's inventory proves children are not
pulled). `append_pass_1` returns one object; the "child" whose parent is null
in the JSON never existed in the session. The claim the design rests on —
parent+child in the same chunk append with the parent link intact — has ZERO
evidence behind it.

Amendment:
- Rebuild ALWAYS re-applies all 25 parent pairs from the manifest by name
  (25 ops — cheap; never trust append to do it).
- Record `matrix_parent_inverse` (4×4) per pair in the manifest and restore
  it — the kit's own law (AGENTS.md 11d): bare re-parenting without the
  inverse makes children jump. The 6 MESH-typed parents (Group001, Window)
  are regular objects; same mechanism.
- Verify: assert child world matrices (or world_bbox) match source post-rebuild;
  manifest_diff `moved` would catch a jump, but prevention beats detection here.

### 6. MUST-FIX — unmeasured ID classes: modifiers, constraints, shape keys, particle systems, geometry nodes; cross-subtree references can silently closure-pull foreign roots
Attacks: §Blender-native answer ¶1 (closure claim measured only on
object→mesh→material→image), §Design B (chunk unit = subtree set).

`chunk_probe.json` bounds the good news — object_types = MESH 1200 / LIGHT 4 /
EMPTY 20 / CAMERA 1, n_armatures 0: **no curves, no text objects, no
armatures**. But zero probe coverage for: object MODIFIERS (bevel/boolean/
array — their targets are object references), CONSTRAINTS (object targets),
mesh SHAPE KEYS (embedded, but they add bytes the estimate misses), PARTICLE
SYSTEMS and GEOMETRY NODES — and the library list includes **Botaniq plants**
(`Plant_Ficus/Pothos/RedChilli`), a vendor line famous for particle/GN
foliage. A boolean target or particle instance object living in ANOTHER
subtree gets pulled into that chunk's closure AND stays a root in its own
chunk → duplicate `.001` object on rebuild (object count 1226+, caught late
by verify) or mis-linked modifier (possibly silent).

Amendment:
- Survey probe v3 (one cheap open of loft.blend): count per-object modifiers,
  constraints, shape keys, particle systems, GN assignments; and for each,
  whether referenced objects lie OUTSIDE the object's subtree.
- If cross-subtree references exist: merge those subtrees into one bin-pack
  unit (the design already supports subtree SETS — §B), and record the merge
  in the manifest. If none exist: record the zero in the manifest as the
  assertion the rebuild verify replays (mod_count parity).
- Add shape-key bytes to the pack estimate if any exist (they ride inside the
  mesh write).

### 7. MUST-FIX — world→image closure is unmeasured and the probe structurally couldn't see the HDR user; a lost link renders a black environment
Attacks: §Design B (world ID written into chunk_00), §Design D (restore world).

`chunk_probe2.py img_users()` counts ONLY material node-tree users — the
world's 11-node tree is invisible to it. That's why `externa_hdri_4k.hdr`
shows `users: 0` while being the environment texture. Whether
`libraries.write({world})` pulls the world's node-tree image reference is
UNMEASURED (d18c proved pixels travel for a material-bound image only). If
the link is dropped, the rebuilt scene renders with no environment — Cycles
level lane loses its entire lighting.

Amendment: measure write({world}) → reopen → assert 11 nodes + image link
present. Since the HDR is packed and §A exports it, also assert the flipped
world image keeps its link (by name) through the flip. World restore in
rebuild asserts node count 11 + image link before certification.

### 8. MUST-FIX — scene-settings manifest is too thin: no color management, no compositor state; look.py's render lane depends on both
Attacks: §Design C (world/scene settings), §Design D (restore + look render).

Manifest restores fps/engine/res only. The source scene's color management
(`view_transform`, `look`, `exposure`, `display_device`) is part of the
vendor look — the kit's own law (AGENTS.md gotcha 7) forces
`view_transform='Standard'` for previz but the CYCLES level lane renders
whatever the scene carries; a rebuild that silently lands on the default
(AgX) renders the level darker than source and no gate notices. Also
unrecorded: cycles device/samples, `scene.use_nodes` (compositor — if the
vendor file has a node tree, settings restore can't rebuild it), unit scale,
view-layer list.

Amendment: enumerate the settings list in the chunk manifest —
{fps, engine, res, view_transform, look, exposure, display_device,
cycles_device, cycles_samples, use_nodes, unit_system, scale_length,
view_layers[]} — restore all, assert parity. If a compositor tree exists,
stop-and-flag it as a new measurement item before implementing.

### 9. MUST-FIX — no memory plan on a 4GB box with a documented OOM history; split the run into externalize-then-chunk
Attacks: §Design A+B (one-time split run doing textures AND chunks from one
session).

R6 evidence: the 561MB packed file KILLED look.py on this box (USABILITY_R6
OOM #1; second OOM from 12k annot objects). The split run as designed opens
the full packed file (425MB of packed buffers resident) and then exports
textures (materializing up to 43.5MB at a time) and writes ~12 chunks from
the same session. Session RSS is unmeasured; R6 says it can tip over. The
Kitchen 858-object collection is a red herring for memory — chunks are object
sets, the SESSION is the hazard.

Amendment: two-run pipeline, which the measured mechanics already support:
- Run A: open original → export textures (122 packed → `assets/loft/textures/`,
  content-hash dedup) → flip every packed image to FILE-source via
  unpack(WRITE_ORIGINAL) + `//../textures/` path → save `loft_ext.blend`
  (meshes + materials + path-ref images ≈ 135MB, no pixel payload — this is
  exactly the R6 look-lite mechanism with paths preserved).
- Run B: open `loft_ext.blend` (light session) → write all chunks →
  `orphans_purge()` between chunk writes.
- MemAvailable guard before each run (kit pattern from S6: EEVEE compile
  needed ≥ ~2.4GB; abort STOP-AND-FLAG below threshold). Bonus: `loft_ext`
  supersedes the look-lite strip for the level lane going forward.

### 10. MUST-FIX — git push batching, and the repo still carries the R7 accident's 561MB blob as unreachable garbage
Attacks: §Risks ("Repo grows ~0.6-0.8GB"), §Design E (push chunks).

Measured live: `.git` is 554MB with a **561,122,088-byte unreachable loose
blob** (`49d2043c…`, exactly loft.blend's size — the R7 wrap casualty). It is
NOT in main history (verified via `--find-object`), so pushes won't trip
GH001 from history — but it wastes 561MB locally and is one careless
`--mirror` away from trouble. Also: a single ~0.7GB push (chunks+textures in
one commit) fits under the 2GB http-body cap, but the kit's own doctrine
pushes every micro-step to BOTH remotes, and GitLab's WAF already blocks ~1/3
of ordinary pushes — a 700MB POST through it is a retry-loop economy problem.
zstd-compressed chunks and PNG/JPG textures are incompressible to git (delta
finds nothing): pack growth ≈ blob growth, so the 0.6-0.8GB estimate stands.

Amendment:
- `git gc --prune=now` before the chunk work; re-verify main history is
  clean of the 561MB blob.
- Batch pushes: ≤ ~250-300MB NEW payload per push (one commit per 3-5 chunks;
  textures in 2-3 batches), rebase before each per doctrine, GitLab retry law
  applies. The 2GB cap is not the binding constraint; WAF + retry economics
  are.
- State the immutability policy: chunks are append-only in history — any
  re-split permanently adds another ~0.6GB (git never forgets). Prefer
  re-splitting only after a failed fresh-clone proof, never cosmetically.
- Step E's "clone to a NEW directory" can be a LOCAL clone (no network,
  fast even at 0.7GB) — say so, so the proof doesn't depend on remote health.
- Nit: confirm no `.gitattributes` LFS attractors (none present today) and
  check GitLab repo quota headroom (growth doubles current .git size).

### 11. SHOULD — kit_semantic / kit_label_conf are invisible to manifest_diff; record all kit_* props in the chunk manifest
Attacks: §Design C (manifest fields), §Design D (verify).

manifest_diff catches `kit_label` changes (label_changed) — good. But the
D16 semantic system stores MORE: `kit_label_conf` and `kit_semantic` (the
gate-exclusion prop: ceilings/lights excluded from floating/below-floor/
penetration checks). `kit_semantic` loss is SILENT to manifest_diff and only
shows up as validator noise (validate_scene starts flagging the ceiling).
Custom ID properties DO serialize with their datablock through
libraries.write, but nothing verifies that.

Amendment: the chunk manifest records per-object/per-mesh/per-collection
`kit_*` props (generic `dict(id.items())` filtered to the `kit_` prefix —
~5 lines); rebuild asserts parity; collection-level props included (the 5
collections are recreated fresh, so anything stored on them must round-trip
through the manifest, not through chunks).

### 12. SHOULD — enumerate all 167 images: 4 classes, only 2 are handled today
Attacks: §A ("every packed image … Library-linked images are SKIPPED").

167 = 122 packed + 8 unpacked-file + 35 linked-missing + 2 residual
(probe2's list filters `source in ('FILE','GENERATED')`, so the residual ~2
are likely RENDER_RESULT/viewer images). §A handles packed (export) and skips
linked (correct), but never mentions the 8 unpacked FILE-source images (their
paths are probably absolute `D:/Blender/…` vendor paths — broken-in-source,
must be preserved verbatim as source truth) or the residual 2. Also exporter
mechanics worth pinning: preserve extension and `colorspace_settings` on the
flip (normal maps are Non-Color); safe_name must survive spaces
("Rope_Base Color.png"), unicode, and case-insensitive FS collisions;
content-hash dedup may collapse identical-bytes images under different names
— one file, two datablocks, both listed in the manifest texture table.

Amendment: manifest carries the full image taxonomy
{packed:122→exported, unpacked_file:8→path-preserved, linked:35→stubs,
other:2→skipped}; rebuild verify asserts class parity and that the 8+35
broken paths are broken on BOTH sides (no accidental fix, no accidental
regression).

### 13. SHOULD — cut the library-LINK secondary output (simplicity audit)
Attacks: §Rejected alternatives ("kept as an optional secondary output of
rebuild (cheap: link collections instead of append)").

It is not cheap: §B's chunk unit is an object set and the measured fact is
"collections carry NO objects when written" — so there are no collection
wrappers in the chunks to link; a link-master must link ~1200 objects
individually or add collection wrappers per chunk (new write plumbing). Its
value overlaps two existing surfaces: the append-master (edit + render lane)
and glTF export (web preview). Kit doctrine: features must serve the
perceive→reason→act→verify loop; this one doesn't and adds a second
correctness surface (link path resolution, library reload semantics) to a
durability design that should have exactly one.

Amendment: CUT it. One sentence in the doc: "link-master rejected — chunks
carry no collections to link; append-master + direct chunk-open cover local
use; revisit only if a measured need appears." (If kept anyway, the
collection-wrapper change must be specified and measured — it alters every
chunk file.)

### 14. SHOULD — verify checklist additions before certification
Attacks: §Design D (verify list).

Current list: object count, poly count, mesh/image/material counts, world
bbox, manifest_diff vs source look manifest. Gaps, each cheap:
(a) object NAME SET equality (exact, before any geometric-twin reasoning);
(b) node_group count parity (7 = 3 local + 4 linked stubs — §D's list omits
node groups entirely); (c) light/camera counts (4/1); (d) image
path-existence assert (see #4); (e) kit_* props parity (#11); (f) parent
pair world-matrix check (#5); (g) the collection TREE including the EMPTY
nested `Collection.001` (probe1: 0 objects, child of `Collection`) — the
rebuild's "recreate collections" must recreate the hierarchy and empty
children, not just membership lists; (h) the 2 scene-root Area lights are
linked to the SCENE ROOT collection (master collection), not "Collection" —
`root_level_orphans` membership must be explicit in the manifest.

### 15. NIT — smaller items
- probe1 `sum_root_est_mb: 0.0` accumulation bug (also in #1): assert packer
  totals.
- `write_linked` size 135901 with "wrote a linked ID?" — resolve this loose
  end in the write-semantics doc: linked IDs DO write (as what — stub or
  closure?) feeds #3.
- The design's zstd 2.6× claim (compress_effect 63488/166959 ≈ 2.63×) is from
  a 167KB toy payload; fine, but don't use it to predict chunk sizes — real
  gate only (#1).
- Fresh-clone proof: also run it on a machine WITHOUT the Blender cache warm
  (the kit's cold-start reality), or note the warm-cache step in the proof doc.

---

## WHAT SURVIVED SCRUTINY (for balance)
- Externalize-then-chunk (not packed chunks) is the right call; 425MB × 3-5
  duplication rejection is sound.
- Subtree as chunk unit correctly handles the 25 parent pairs structurally
  (with #5's manifest re-application on top).
- Real-size gate on top of an estimate is right (after #1 fixes the estimate).
- STOP-AND-FLAG exit 4 for un-splittable subtrees matches kit doctrine.
- The 47 missing vendor links as documented source-truth is honest (with #3's
  stub mechanics made explicit).
- GitHub 100MB per-blob constraint is genuinely satisfied: max texture 43.5MB,
  chunks gated <90MB.
- manifest_diff vs source look manifest is the right final gate — the audit
  confirms it catches kit_label loss, moves, resizes, renames (geometric
  twins), and non-mesh changes; the amendments above close what it cannot see.

## VERDICT

**SHIP-WITH-AMENDMENTS** — architecture is sound; findings 1-3 are spec-level
blockers fixable in the doc + two cheap probe rounds (missing-library write
behavior, world closure, modifier/constraint survey) before any implementation.
