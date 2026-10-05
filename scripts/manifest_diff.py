#!/usr/bin/env python3
"""manifest_diff — verify delegated work by DIFF, not by trust.

The D16 handoff audit (session 8) found the rigor gap: after a
non-vision sub-agent works on a labeled scene, "I checked the result"
was eyes-on-the-hero-shot + the agent's OWN claimed audit numbers. Not
enough. The principal's protocol is now:

  1. BEFORE delegating: save a look manifest (look.py writes
     look_manifest.json into --output).
  2. AFTER the delegate returns: re-render/manifest the state YOURSELF
     (fresh look.py run), then diff the two manifests with THIS tool.
  3. Every reported change must map 1:1 onto a task the delegate was
     GIVEN. Anything else is unauthorized mutation — reject the work.
  4. Re-run the physics/audit tools yourself (kit-measured, never the
     delegate's claimed numbers) and closeup every touched object.

Pure Python — reads two look_manifest.json files, no bpy. Exit code is
0 always unless --expect-clean (then 1 if ANY difference).

Usage:
  python3 scripts/manifest_diff.py before.json after.json [--tol 0.005]
         [--expect-clean] [--json report.json]
"""
import argparse
import json
import sys


def _center(row):
    bb = row.get("world_bbox")
    if bb:
        return [(a + b) / 2.0 for a, b in zip(bb["min"], bb["max"])]
    return row.get("centroid")  # legacy manifests


def _extent(row):
    bb = row.get("world_bbox")
    if bb:
        return [b - a for a, b in zip(bb["min"], bb["max"])]
    return row.get("dims_m")


def _rows(doc):
    """Accept either a bare row list or a full look_manifest.json dict
    (unwrap its 'manifest' key)."""
    if isinstance(doc, dict):
        return doc.get("manifest", [])
    return doc


def diff_manifests(before, after, tol=0.005):
    """Diff two manifest row-lists (or look_manifest dicts). Returns a
    report dict.

    Categories:
      moved          — same id, bbox center shifted > tol (world_bbox
                       compared; centroid fallback for legacy rows)
      resized        — same id, extent changed > tol on any axis
      label_changed  — same id, kit_label differs (renames WITHIN the
                       label set are the delegate's business; label
                       changes mutate durable identity — flag them)
      added/removed  — id present on only one side
      renamed        — geometric twin: extent matches <= tol on all axes
                       AND center matches <= tol, but the id differs.
                       Reported as pairs (before_id, after_id).
      unchanged      — none of the above
    The caller maps every finding onto the delegate's task list; the
    tool only surfaces what changed, with numbers.
    """
    before, after = _rows(before), _rows(after)
    b_rows = {r["id"]: r for r in before if r["type"] == "MESH"}
    a_rows = {r["id"]: r for r in after if r["type"] == "MESH"}
    b_other = {r["id"]: r for r in before if r["type"] != "MESH"}
    a_other = {r["id"]: r for r in after if r["type"] != "MESH"}

    report = {"moved": [], "resized": [], "label_changed": [],
              "added": [], "removed": [], "renamed": [],
              "nonmesh_changed": [], "unchanged": []}

    added_ids = set(a_rows) - set(b_rows)
    removed_ids = set(b_rows) - set(a_rows)

    # geometric twins across a rename: match before-rows that vanished
    # to after-rows that appeared by identical geometry
    used_after = set()
    for bid in sorted(removed_ids):
        br = b_rows[bid]
        for aid in sorted(added_ids):
            if aid in used_after:
                continue
            ar = a_rows[aid]
            ec = all(abs(x - y) <= tol for x, y in
                     zip(_extent(br) or [], _extent(ar) or []))
            cc = all(abs(x - y) <= tol for x, y in
                     zip(_center(br) or [], _center(ar) or []))
            if ec and cc and _extent(br) and _extent(ar):
                report["renamed"].append({"before": bid, "after": aid})
                used_after.add(aid)
                break

    really_added = sorted(added_ids - used_after)
    really_removed = sorted(removed_ids - {
        r["before"] for r in report["renamed"]})

    for oid in sorted(set(b_rows) & set(a_rows)):
        br, ar = b_rows[oid], a_rows[oid]
        bc, ac = _center(br), _center(ar)
        be, ae = _extent(br), _extent(ar)
        moved = bc and ac and any(
            abs(x - y) > tol for x, y in zip(bc, ac))
        if moved:
            delta = [round(y - x, 4) for x, y in zip(bc, ac)]
            mag = round(sum(d * d for d in delta) ** 0.5, 4)
            report["moved"].append({"id": oid, "delta": delta,
                                    "magnitude_m": mag})
        resized = be and ae and any(abs(x - y) > tol
                                    for x, y in zip(be, ae))
        if resized:
            report["resized"].append({
                "id": oid, "extent_before": be, "extent_after": ae})
        if br.get("kit_label") != ar.get("kit_label"):
            report["label_changed"].append({
                "id": oid, "before": br.get("kit_label"),
                "after": ar.get("kit_label")})
        if not (moved or resized) and br.get("kit_label") == \
                ar.get("kit_label"):
            report["unchanged"].append(oid)

    for oid in sorted(set(b_other) | set(a_other)):
        bo, ao = b_other.get(oid), a_other.get(oid)
        if bo != ao:
            report["nonmesh_changed"].append({
                "id": oid,
                "before": {k: bo.get(k) for k in bo} if bo else None,
                "after": {k: ao.get(k) for k in ao} if ao else None})
    report["really_added"] = really_added
    report["ok"] = True
    return report


def summarize(report):
    lines = []
    for key, fmt in (
            ("renamed", lambda r: f"  ~ {r['before']} -> {r['after']} "
                                 "(geometric twin)"),
            ("moved", lambda r: f"  + {r['id']} moved "
                                f"{r['magnitude_m']}m d={r['delta']}"),
            ("resized", lambda r: f"  x {r['id']} extent "
                                  f"{r['extent_before']} -> "
                                  f"{r['extent_after']}"),
            ("label_changed", lambda r: f"  L {r['id']} label "
                                        f"{r['before']!r} -> "
                                        f"{r['after']!r}"),
            ("really_added", lambda i: f"  A {i}"),
            ("removed", lambda i: f"  - {i}")):
        for item in report[key]:
            lines.append(fmt(item))
    if report["nonmesh_changed"]:
        for item in report["nonmesh_changed"]:
            lines.append(f"  ? {item['id']} (non-mesh state changed)")
    n = (len(report["renamed"]) + len(report["moved"])
         + len(report["resized"]) + len(report["label_changed"])
         + len(report["really_added"]) + len(report["removed"])
         + len(report["nonmesh_changed"]))
    lines.append(f"manifest_diff: {n} finding(s), "
                 f"{len(report['unchanged'])} unchanged mesh row(s)")
    return lines, n


def main():
    ap = argparse.ArgumentParser(
        description="Diff two look_manifest.json files")
    ap.add_argument("before"), ap.add_argument("after")
    ap.add_argument("--tol", type=float, default=0.005)
    ap.add_argument("--expect-clean", action="store_true",
                    help="exit 1 if ANY difference (no-change guard)")
    ap.add_argument("--json", dest="json_out", default=None,
                    help="write the full report dict here")
    args = ap.parse_args()
    with open(args.before) as f:
        before = json.load(f)
    with open(args.after) as f:
        after = json.load(f)
    report = diff_manifests(before, after, tol=args.tol)
    lines, n = summarize(report)
    for ln in lines:
        print(ln)
    if args.json_out:
        with open(args.json_out, "w") as f:
            json.dump(report, f, indent=2)
    if args.expect_clean and n:
        print("manifest_diff: EXPECT-CLEAN VIOLATED — unauthorized "
              "mutations present", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
