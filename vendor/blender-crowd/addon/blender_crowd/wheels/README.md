# vendored crowd wheels — provenance + law

`blender_crowd_native-1.5.5-cp311-abi3-manylinux_2_34_x86_64.whl`
- Source: blender-crowd-kit `vendor/blender-crowd/addon/blender_crowd/wheels/`
  (the same relative path — this directory is a THIN VENDOR: wheels only,
  never the addon sources; the addon lives in the crowd-kit repo).
- Law (F-TF5, closed session-16): the kit-mode bridge needs the NEWEST
  native module (`create_session motion_matcher` kwarg). When a bake
  driver fails on a bridge kwarg, re-vendor from crowd-kit's tree
  FIRST before debugging anything else — wheel drift across repos is
  the recurring seam (session-15 finding).
- Install path: `python3 -m venv <venv> && <venv>/bin/pip install
  vendor/blender-crowd/addon/blender_crowd/wheels/*.whl` (the bake
  drivers' venv), or straight into Blender's bundled python with
  BLENDER_PY (install.sh resolves it).
