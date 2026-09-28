# prop_carry — Generalized Prop Anchoring & Clamped Carry (law 110)

## What it kills: PHANTOM OFFSETS
A prop's parent-space anchor (matrix_parent_inverse or carry-local)
captured while the scene is parked at a DIFFERENT frame than the world
placement it anchors. Session-26: a rifle's carry_local was read at
f10 while pos_c was f1-based — the 1.88 m sprint delta rode every
carry key and the gun floated ~2 m behind the gunner for 156 frames
while ALL existing export gates stayed green (the aim placement AND
the wrapper riding were each individually correct).

## API (blender_kit.prop_carry)
- `capture_anchor(anchor_obj, scene, frame)` — SAME-FRAME snapshot;
  verifies the frame park actually took. Returns a COPY.
- `anchor_local(snapshot, world_placement)` — pure math, frame-state
  FREE.
- `carry_keys(prop, scene, *, frames, desired_world, blend_from,
  blend_to, end_frame)` — generalized torso-stable clamped carry:
  W0 pass (basis==I) + blend-to-identity + terminal identity key at
  end_frame (law 106: held-state actions key the full timeline) +
  LINEAR keys + fail-closed post-verify.
- `verify_riding(prop, scene, *, anchors, frames, max_dist)` —
  sanity radius: the prop must stay within max_dist of at least one
  anchor at EVERY keyed frame (anchors may be objects or
  (armature, bone_name) tuples).

## Laws enforced
- LIVE-READ: every matrix read after frame_set + 2x view_layer.update.
- SAME-FRAME (session-26): anchor captures assert frame parity.
- FULL-TIMELINE (law 106): held-state prop actions get a terminal key.
- SANITY RADIUS: post-key verification catches any phantom class.

## Export twin
Gate 14 (`_glb_prop_proximity_audit` in export_previz_package.py):
any animated node parented to a skin JOINT must stay within 1.0 m of
some joint of its owning skin at every sampled frame. Calibration on
the session-26 broken export: legit torso carry <= ~0.7 m min-joint
distance, phantom >= 1.32 m, aimed hold 0.02 m.
