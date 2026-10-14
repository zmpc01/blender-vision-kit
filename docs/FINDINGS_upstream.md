# FINDINGS upstream — session-17 wave-D (infra audit 2e follow-through)

Filed by: task 3-d (blender-vision-kit wave-D infra fixes), 2026 session-17.
Upstream repo: **blender-agent-kit** (owner repo of the governed-sync tooling).
`tools/sync_shared.py` is NOT vendored in blender-vision-kit (this repo's
`tools/` carries only `chunked_dl.sh` — see docs/audit_s17/2e_infra.md F2E-14),
and this session did NOT touch the upstream checkout. The findings below are
filed HERE so the variant tree carries the record; apply them from the
upstream repo in an upstream-owned session.

Line refs: from docs/audit_s17/2e_infra.md (audited @ upstream 3c0c60d);
spot-verified against the live upstream checkout during wave-D (the
copy-direction lines :581-583, the --to emit/vendor block :629-634, the emit
manifest write :296-299, the sibling NOTE :180-182, the OWNER-MISSING refuse
:212-218, and the first-sync/--bootstrap gate :536-547 all still match).

---

## F2E-5 · P1 · sync_shared `--to <non-registered consumer>` rewrites the canonical manifest and backflows owner:previz files into the kit

- **Where**: `blender-agent-kit/tools/sync_shared.py:582-583` (copy direction),
  `:629-630` (previz = "whatever --to you passed" + re-emit),
  `:296-299` (emit writes the canonical manifest), `:200-204` (unnoted
  prior entries are dropped), `:536-547` (first_sync / --bootstrap gate),
  `:633-634` (refreshed record vendored into the target).
- **Mechanism**: `"previz"` is auto-defined as *whatever `--to` target you
  passed* (`previz_root = target if os.path.basename(target) !=
  "blender-agent-kit" else None`, then `rc = emit(root, previz_root,
  DEFAULT_BLENDER)`). Pointing `--to` at any second consumer — e.g.
  blender-vision-kit, a plausible misreading of HANDOFF.md:50 ("port the
  preflight … via tools/sync_shared.py governed sync") or HANDOFF.md:555's
  generic "--to <consumer>" — performs THREE governed-state mutations at once:
  1. the canonical manifest at `tools/shared_manifest.json` is re-emitted
     describing **kit↔<that consumer>** (shared set = intersection; prior
     kit↔escape-previz entries without a `note` are DROPPED per :200-204,
     with only a console NOTE);
  2. for `owner:"previz"` entries the copy direction is consumer→kit
     (`src_root = target if owner != kit …`, :582-583) — with the vendored
     record absent in the new target (first_sync=True, :536) plus
     `--bootstrap`, the kit's own `scripts/assets_ual_actors.py` is
     **overwritten with the other consumer's bytes** (backflow into the
     owner repo);
  3. the rewritten record + checker are vendored to the target (:633-634),
     after which the REAL escape-previz consumer's vendored record can never
     classify cleanly against the canonical manifest again.
  The only gate is `--bootstrap` (:544-547), whose message (:538-543) asserts
  the operator verified *the consumer* holds no un-ported changes — it never
  discloses the backflow into the kit or the canonical-manifest rewrite.
- **Suggested fix (ready-to-apply sketch)** — pin the governed pair, refuse
  everything else, never backflow:

  ```python
  # tools/sync_shared.py — near DEFAULT_BLENDER
  REGISTERED_CONSUMERS = {
      # The ONE governed consumer pair this tool may rewrite state for.
      # Anything else must be added HERE, deliberately, by name.
      "escape-previz",
  }

  def _registered(target):
      # Match on the checkout's canonical basename, not a heuristic.
      return os.path.basename(os.path.normpath(target)) in REGISTERED_CONSUMERS

  # inside the --to command path, BEFORE any state mutation:
  if not _registered(args.to):
      print("[sync] REFUSED — %r is not a REGISTERED consumer (%s)."
            % (args.to, ", ".join(sorted(REGISTERED_CONSUMERS))))
      print("[sync]   A --to run would: (a) re-emit the canonical manifest as"
            " kit<->%s (dropping unnoted kit<->escape-previz entries),"
            % os.path.basename(os.path.normpath(args.to)))
      print("[sync]   (b) copy owner:previz files FROM %s INTO the kit"
            " (owner backflow), and" % os.path.basename(os.path.normpath(args.to)))
      print("[sync]   (c) vendor the rewritten record into %s — after which"
            " escape-previz's own record can never classify cleanly.")
      print("[sync]   To onboard a new consumer, add it to REGISTERED_CONSUMERS"
            " in a reviewed change first.")
      return 1

  # inside the copy loop, defense in depth:
  if owner == "previz" and not _registered(target):
      print(f"!! REFUSED previz-owned backflow into non-registered target: {path}")
      refused += 1
      continue
  ```

  (Also make the `--bootstrap` message at :538-543 disclose items (a)-(c)
  above for registered consumers too.)

---

## F2E-15 · P3 · sync_shared `--to` ignores `--blender`; `validated_blender` is hardcoded 5.2.2 on that path

- **Where**: `blender-agent-kit/tools/sync_shared.py:630`
  (`emit(root, previz_root, DEFAULT_BLENDER)`) vs `:836` (the `--blender`
  flag) — the flag is honored only on the `--emit` path (`:847`).
- **Fix**: `emit(root, previz_root, args.blender)` on the `--to` path too.

## F2E-16 · P3 · emit's sibling-missing NOTE promises "manifest emitted from the kit tree alone" but the run actually REFUSES (correctly) on OWNER-MISSING

- **Where**: `blender-agent-kit/tools/sync_shared.py:180-182` (NOTE) vs
  `:212-218` (refuse when `previz_root is None` and any OWNER_PREVIZ entry
  exists — `scripts/assets_ual_actors.py` always qualifies).
- **Fix**: reword the NOTE to: "sibling not found — emit will REFUSE on
  OWNER-MISSING unless no previz-owned entries exist."

---

## Note on HANDOFF.md:50 — "port the preflight via sync_shared" is the wrong tool for that direction

The planned export-preflight port (HANDOFF.md:50; also HANDOFF.md:555,
docs/DESIGN_FTD_trio.md:105,177) is a **non-owner → owner** direction:
blender-vision-kit (variant) → blender-agent-kit (owner). `sync_shared.py`
copies owner→consumer only; it cannot express a port-back. The plan should
be a **direct file copy + a test in the kit's suite**, and only afterwards
the usual governed-sync drift loop (land kit fix → `sync_shared --to
<registered consumer>` → commit BOTH). When the port happens, record it via
`--adopt` (the tool's intended owner-side intake path) rather than
repurposing `--to` — see F2E-5 above for what a misdirected `--to` costs.
