# VISION WAVE 3 — fresh-eyes doc validation (T5) + dense-scene workflow (T6)

## T5 (doc claims verified literally)
- --list signatures: YES — 12-op batched patch applied FIRST TRY using printed signatures
- audit id-scope: YES (pairs_checked:1, single Bench×Kettle pair)
- --angles none --closeup: YES (one image, verdict+manifest still printed)
- Friendly error: PARTIAL → FIXED (missing-key error now prints the op signature)
- Misspelled optional key silently ignored → FIXED (_warn_unknown_keys parses PARAM_DOCS, warns with signature)
- SHIP ARC BROKEN for patch-built scenes (export_gltf/save_blend had no --load-blend) → FIXED (both accept --load-blend now)
- Exit-code lore WRONG ("blrun swallows") → probe artifact: $? after a pipe is the LAST command's. blrun propagates exit 3 (verified twice). Docs corrected (tool ref + gotcha 115 + SKILL.md).

## T6 (dense 120-agent scene, pure bpy crowd proxy)
- 8.99s look at 124 objects + 69 annot objects (within 8-12s band)
- Label clutter: NONE (top-8 exactly; ground slab excluded per law 112)
- Planted 0.4m floater caught 3 INDEPENDENT ways: validator (with new nearest-support hint), manifest centroid outlier, single red flag box
- Dense verdict PASS with ZERO false positives (0.36m bodies, ≥0.5m gaps)
- SUBJECT-OVERFLOW: default 5m offsets clip the 12m cluster while readiness scores clean → HINT added to look.py; 16mm re-aim made all 3 color groups readable (measured)
- Label→id mapping missing from manifest → FIXED (labels array + log line)
- dims vs dims_m key mismatch → FIXED

## Wave-3 fixes applied
apply_patch: _require signature line, _warn_unknown_keys
export_gltf/save_blend: --load-blend
look.py: labels map line + manifest labels array + SUBJECT-OVERFLOW hint + dims_m
AGENTS.md: ship-arc --load-blend, --angles none documented, exit-code lore corrected (3 places), dense-scene measured laws
Regression: test_v1_look 27/27 GREEN
