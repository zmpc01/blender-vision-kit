#!/usr/bin/env python3
"""previz_canon.py — the bpy-free canonical form of a previz payload
(design: docs/DESIGN_s35_revision_manifest.md §D0, kit issue #9).

WHY THIS MODULE EXISTS: the canonical-payload strip-set must have ONE
definition shared by (a) the exporter (inside Blender, computes
content_sha256 at emit time) and (b) the regression tests + any
consumer tooling (plain python3, no bpy). Two hand-kept copies WILL
drift (the v1 design review's I5); this module is the single source.

The canonical form: the payload dict minus every top-level key that
legitimately MOVES between exports of the same content (provenance)
or is derived from the hash itself, serialized indent=1 sort_keys=True
(the exporter's existing dump config).

content_sha256 = sha256(canon_form(payload)) where the canon form
strips `content_sha256` itself — compute-then-insert, no regress.
"""
from __future__ import annotations

import hashlib
import json

# Everything that legitimately moves between two exports of IDENTICAL
# content (timestamps, VCS state, package naming, sync-state provenance,
# the revision counter) — plus the hash field itself (stripped from its
# own preimage).
PROVENANCE_FIELDS = (
    "generated_at",
    "git_sha",
    "name",
    "package_id",
    "shared_deps_synced",
    "shared_deps_drift",
    "revision",
    "content_sha256",
)


def canon_form(payload: dict) -> str:
    """The canonical serialization: provenance-stripped, sorted, indented.

    [KX-1 s37r-3] allow_nan=False mirrors the exporter's payload
    finiteness sweep: a NaN/Inf in the payload is invalid JSON
    (RFC 8259) and the content hash refuses to certify it (raw
    ValueError naming the refusal, instead of hashing a token no
    strict consumer can parse)."""
    d = {k: v for k, v in payload.items() if k not in PROVENANCE_FIELDS}
    return json.dumps(d, indent=1, sort_keys=True, allow_nan=False)


def content_hash(payload: dict) -> str:
    """The content identity: sha256 of the canonical form. Identical
    content ⇒ identical hash across re-exports (time/git/revision
    stripped; the hash field stripped from its own preimage)."""
    return hashlib.sha256(canon_form(payload).encode("utf-8")).hexdigest()
