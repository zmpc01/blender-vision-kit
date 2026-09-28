# Rigged Characters — Capsule vs Rigged, UAL Hero-Swap

## Why capsule actors (the previz standard)

The v2 rigged-humanoid attempt (CC0 glTF rigs, re-skinning, NLA pose
switching) FAILED final-render verification: limbs detached/floating
in hero frames, actors missing from seats, ~10 sessions of trap-fixing
(skin weights, action slots, NLA stashes, basis-matrix collapse, eval
deform lies).

**Policy**: Human actors = capsule bodies + FK limb objects + direct
`rotation_euler` keyframes. No armatures, no actions-as-poses, no NLA,
no skin weights, no glTF imports for actors. Rigged characters only
when the deliverable IS character animation (not previz).

## Rigged-character gotchas (if you go there)

1. **Stock assets ship with broken skin weights** — CesiumMan.glb's right
   shin weighted to LEFT-leg bones. Fix: drop vertex groups, re-weight by
   proximity (2 nearest bones, inverse-square blend).
2. **Bind pose ≠ standing pose** — walk ACTION supplies upright pose.
   Quaternions near (-1,0,0,0) are identity. Graft from NEUTRAL cycle frame.
3. **Quaternion axis conventions differ per composition method** —
   component-SET vs PRE-MULTIPLY give different motions at large angles.
   Derive empirically (perturb one component, read bone-tail world delta).
4. **`matrix_basis.identity()` destroys glTF root orientation** — imported
   rigs carry Y-up→Z-up -90°X on ROOT. Parent with
   `matrix_parent_inverse = parent.matrix_world.inverted()`, set only
   `matrix_basis.translation`.
5. **Blender 4.4+ auto-stashes actions into NLA tracks** — assigning
   `animation_data.action` after another action was bound creates muted NLA
   "stash" strips. Inspect `nla_tracks` when poses misbehave.
6. **`evaluated_get().to_mesh()` may not reflect armature deform** — in
   background `frame_set` contexts the evaluated mesh can come back in
   bind pose while the render shows posed figure. Use pose bone positions
   or renders.
7. **Action-slot law (4.4+)**: `ad.action = X` does not rebind after a
   legacy-slot action was assigned. EVERY assignment must pin the slot:
   `ad.action = act; ad.action_slot = act.slots[0]`. Actions created via
   `bpy.data.actions.new()` have 0 slots until first assignment.
8. **Pose-bone composition**: `pb.matrix = parent_pose @ parent_rest^-1 @
   bone_rest @ matrix_basis`. ASSIGNED `pb.matrix` does NOT survive
   re-evaluation (translations land, rotations explode with compounding
   scale). Use the writer: `basis = (parent_pose @ parent_rest^-1 @
   bone_rest)^-1 @ M`, with `view_layer.update()` x2 BETWEEN chain levels.
9. **`bpy.ops.object.join` leaves active part's scale AND origin** —
   `transform_apply(location=True, rotation=True, scale=True)` after join
   or later parenting seats the wrong end.
10. **Bone-parent calibration**: for `parent_type='BONE'`, effective parent
    transform is a Blender internal (rest-roll contributes ~90° vs naive
    `arm.matrix_world @ pb.matrix`). `MPI_{i+1} = MPI_i @ W_i^-1 @ M_target`
    converges in ONE step IF W_i reads are live (refresh via
    `scene.frame_set()` + double update). Gate on the FULL matrix.

## Quaternius UAL (vetted hero-actor upgrade path)

Vendored at `assets/vendor/ual/` (CC0 mirror). Gauntlet PASS (42/46
actions animate, in-place drift 0.000m, recolor works, scale 1.651m →
1.05 rescale). A/B vs capsules: VLM reads UAL as "running, leaning
forward" vs capsule "walking". Action map: Sprint_Loop / Sitting_Enter+
Driving_Loop / Pistol_Aim_Neutral+Shoot / Punch_Cross / Hit_Chest+Death01.

NOT yet integrated — hero swap is its own session; crowd stays
capsule-instanced. One import artifact: stray Icosphere at origin —
delete on use.
