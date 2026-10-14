# vendored crowd wheels — provenance + law

`blender_crowd_native-1.5.5-cp311-abi3-manylinux_2_34_x86_64.whl`
- Source: blender-crowd-kit `vendor/blender-crowd/addon/blender_crowd/wheels/`
  (the same relative path — this directory is a THIN VENDOR: wheels only,
  never the addon sources; the addon lives in the crowd-kit repo). This copy
  was synced from **zmpc01/blender-crowd-kit** via the governed sync
  (session-16 re-vendor, F-TF5: 1.0.0 → 1.5.5).
- **Integrity pin** (F2E-12 — verify after ANY re-vendor; a corrupted or
  silently-swapped 17.9 MB binary blob passes every other gate: sync_shared
  governs `scripts/*.py`, never this wheel):
  - sha256: `166ce6a13a0f147231f34d095029e516f381c24432108f40ae6e487befd3a151`
  - size:   `17932638` bytes (exact)
- Build origin (from the wheel's own dist-info): `WHEEL: Generator: maturin
  (1.9.6)`; `Classifier: Programming Language :: Rust`; `Requires-Python:
  >=3.11`; tag `cp311-abi3-manylinux_2_34_x86_64` — i.e. a Rust core built
  by maturin 1.9.6.
- **License: NONE RECORDED — honest gap (F2E-12).** The wheel's METADATA
  carries no License field, no Author, and no Home-page, and this thin
  vendor deliberately excludes the addon sources from which a license
  could be read. Recorded as-is; resolve with upstream blender-crowd-kit
  (add a License section or a LICENSE file beside the wheel) BEFORE any
  external distribution of this tree.
- Law (F-TF5, closed session-16): the kit-mode bridge needs the NEWEST
  native module (`create_session motion_matcher` kwarg). When a bake
  driver fails on a bridge kwarg, re-vendor from crowd-kit's tree
  FIRST before debugging anything else — wheel drift across repos is
  the recurring seam (session-15 finding). Re-verify the sha256 pin
  above as part of every re-vendor.
- Install path (corrected F2E-12 — the old sentence claimed install.sh
  resolves BLENDER_PY for this wheel; **install.sh has NO wheel step**,
  its BLENDER_PY probe exists to pip-install PILLOW into Blender's
  bundled python only): install into the **bake drivers' venv** —
  `python3 -m venv <venv> && <venv>/bin/pip install
  vendor/blender-crowd/addon/blender_crowd/wheels/*.whl`. If you ever
  need the module inside Blender's bundled python, resolve that
  interpreter yourself (`BLENDER_PY=<bundled python3.NN>`) and run
  `<BLENDER_PY> -m pip install <wheel>` explicitly — never assume
  install.sh did it.
