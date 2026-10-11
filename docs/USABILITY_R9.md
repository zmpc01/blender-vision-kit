# USABILITY_R9 — the asset made durable (D18 shipped)

Session 13 (2026-10-11). Trigger: the user's GitHub-100MB question —
"check if blender has a way to break a big scene/project into smaller
files it can import". Full design: docs/DESIGN_D18_asset_partition.md
(REV-3, 2 critique rounds). This is the measured record.

## What shipped

`scripts/r9_split_asset.py` (Run A: texture externalization; Run B:
chunk writing) + `scripts/r9_rebuild_asset.py` (chunk → master) +
`tests/test_r9_chunking.py` (16/16). The 561MB loft.blend now lives
in-git as: 119 texture files (403MB, sha-deduped from 122 packed IDs,
each <44MB) + 14 chunk .blends (104MB total, largest 31.3MB) +
chunks_manifest.json. `git clone` → `install.sh` → one rebuild command
→ a master byte-parity with the source (manifest_diff 0 findings /
1200 unchanged; renders pixel-identical, meanAbsDiff ≤0.07). Proven in
a fresh clone (bvk-proof). The GitHub Release + polyhaven re-fetch
remain as compact alternatives; chunks are the clone-transport tier.

## The measured Blender laws (the value of this session)

1. **write() = downward closure only.** `bpy.data.libraries.write`
   pulls object→mesh→material→image but NOT children (subtrees must be
   enumerated); 5.2's arg 2 is a SET; collections carry NOTHING.
2. **Append has no dedup** — 2nd append → `.001`; and the low-level
   `libraries.load` append does NOT link objects to the scene (users=0!
   linking is the caller's duty) and does NOT preserve fake_user.
3. **ID.users counts the fake user** — a fake-user-only ID reads as
   users==1; the purge-vulnerability predicate is
   `users == 0 or (use_fake_user and users == 1)`.
4. **Scene-owned CompositorNodeTree IDs drag the whole Scene through
   write()** — direct, severed-user, and copy all measured. They cannot
   ride chunks; dump-to-JSON + re-create is the only faithful path.
   Socket sets drift between Blender versions (5.2 Denoise lost Normal/
   Albedo inputs) — skip links honestly, assert node-count parity.
5. **save_as_mainfile re-relativizes // paths from the OLD file's
   location** — a // path set for the NEW location gets re-based to a
   dead relative path. Use absolute paths for intermediates.
6. **Autopack**: vendor files ship with `bpy.data.use_autopack` ON;
   save then re-packs externalized images from their old // location
   and aborts. Turn it off before any save in a partition pipeline.
7. **The Area.001 law (double-write corruption)**: an object written
   into TWO chunks shifts same-named DATA identity at rebuild (batch-
   internal name collision renames the data copies; the object's
   by-name pointer then binds to the WRONG copy). Write sets must be
   pairwise-disjoint with |∪| == census — asserted at write time.
8. **Closure gaps are real and class-wide**: write() drops some edges
   (measured: a fake-user builtin material; light data via batch
   collisions). The self-verifying defense: inventory the WRITTEN
   chunk files, diff against source locals, ship the gap as an
   explicit riders chunk; and request ALL ID classes per chunk at
   rebuild (a riders chunk's payload materializes only if requested
   by class).
9. **Consolidation by suffix-search**: append artifacts' names must be
   matched back to source names (Blender rebuilds numeric suffixes:
   source "X.001" twice-appended → local "X.002"); ambiguity is
   resolved ONLY when all candidates are byte-identical (same texture
   file + colorspace), else STOP-AND-FLAG.
10. **Data-driven expectations over arithmetic**: hand-computed parity
    counts were wrong three times (179/180 materials, 165/130 images,
    20 empties); the delivery model (chunk inventories + gap) computed
    at rebuild time is the only expectation that cannot drift.

## Process notes

- Two critique rounds found 27 findings; the highest-value ones were
  the factory-startup collision (N1), the light double-count (N3,
  whose assert I skipped and paid for with the Area.001 bug), and the
  LFS-not-unlimited correction.
- The STOP-AND-FLAG design paid off twice: the compositor-tree flag
  fired live (survey said none — the survey was wrong) and the
  write-size gate fired on the first scene-chunk draft.
- The parallel-lane live coordination pattern held: fetch-rebase
  before every push, zero force pushes, 6 mid-session remote moves.
