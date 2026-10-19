# REVIEW_COMMENTS_PROTOCOL.md — the user-review round-trip (s24 adoption)

> Ported from blender-escape-previz (worklog session-14 convention;
> the schema lived in `previz_comments_*.json` files at the previz repo
> root). Zero code — a convention the review lane follows.

## The schema (v2.1)

```json
{"schema_version": "2.1",
 "package_id": "tdawn_1",
 "package_schema": "2.3",
 "fps": 30,
 "shot_count": 12,
 "comment_count": 3,
 "comments": [
   {"id": "c1", "shot": "S2", "shot_frames": [89, 132],
    "frame": 101, "time_s": 3.37,
    "anchor_objects": ["Hero", "Gate"],
    "author": "user", "body": "the gate glow reads dead here",
    "created_at": "2026-10-12T18:20:11Z"}]}
```

## The round protocol (the part that makes reviews DURABLE)

1. The review app exports the reviewer's comments for a package.
2. The comments file is committed AT THE REPO ROOT of the lane that
   owns the film (`previz_comments_<package>.json`) — a "FROM USER"
   commit. The mirror IS the durable record (GIT IS THE DISK applies
   to review input too).
3. The consuming session reads it, folds every comment into a film
   rev+1 (or files a documented refusal), and KEEPS the file (append
   `resolved: <rev>` per comment id is allowed; deletion is not —
   the trail is the provenance).
4. A film rev+1 re-stages as a NEW package (newest-first serving);
   the old package stays for A/B (previz_canon.content_hash pins the
   content identity across the rev pair).

## Worked example

`previz_comments_tdawn_2.json` in blender-escape-previz (root) is the
reference fixture — copy its shape exactly; unknown keys are preserved
by convention, the pinned keys above are the contract.
