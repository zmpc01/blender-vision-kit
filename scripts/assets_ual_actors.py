"""
assets_ual_actors.py -- v4 UAL rigged hero actors (the wrapper layering).

PLAN_v4 REV2/REV3 architecture (4-reviewer converged). Replaces the
capsule actor system FOR THE HEROES ONLY when HERO_MODE == "ual" (the
crowd + KD zombies stay capsule-instanced):

  * per actor (Driver / Girl / Gunner / HeroZed): ONE glTF import of the
    vendored Quaternius UAL mannequin (46 actions, Rigify DEF-* bones,
    53 bones, feet-origin, bind height 1.651 m -- ual_probe_v4.json)
  * a FRESH wrapper EMPTY named exactly "<Name>.Root" (gotcha-#24-safe:
    identity basis; the scene script parents it to JeepRoot AT BUILD
    with matrix_parent_inverse = jeep^-1, the VERBATIM capsule contract)
  * the UAL armature becomes a wrapper CHILD with the facing flip
    (Rz(pi), probed at BIND per import -- never hard-coded) + actor
    scale baked into matrix_parent_inverse (NEVER keyed). Composition
    law (mpi_semantics_probe, Blender 4.5.13):
        matrix_world = parent.matrix_world @ matrix_parent_inverse
                       @ matrix_basis
    -> child MPI = Rz(pi) @ S(scale) gives the rig capsule-equivalent
    facing semantics (wrapper yaw 0 = actor faces +Y / jeep forward).
  * the skinned Mannequin mesh stays parented to its armature (the
    import hierarchy is preserved; only the armature is re-parented)
  * the stray Icosphere scene-node mesh is DELETED (not hidden -- REV3
    item 6: a hidden stray is still a scene-root stray)
  * ONE material datablock per actor on ALL mesh slots (the "single
    material" definition: 2 slots -> ONE datablock), v3.3 color table,
    recolor via diffuse_color AND Principled base color (gauntlet R4)
  * per-actor action POOL recorded (the 4 imports duplicate all 46
    actions with .001/.002/.003 suffixes; the pool dict maps ORIGINAL
    names -> the actual action objects so the bake never resolves names
    -- the fresh-bake-only law: NEVER key into imported source actions)
  * rifle = WRAPPER-OFFSET PROXY (REV3 item 12): the capsule rifle box
    re-created as a Gunner-wrapper child at the capsule root-local
    transform (0.18, 0.35, 1.25) + dims (0.07, 0.95, 0.11) -> the
    Muzzle.Loc chain (rifle child at (0, 0.55, 0)) lands at the exact
    capsule reference world position by construction (both roots share
    the jeep parenting + MPI + verbatim key contract) -> the
    muzzle-continuity budget (<= 0.3 m) is satisfied at ZERO drift.

API (consumed by scene_escape_v4.py in ual mode):
    humans = UA.build({"jeep": jeep, "scene": scene})
    humans[name]["root"]      -> wrapper EMPTY (exactly "<Name>.Root")
    humans[name]["armature"]  -> renamed "<Name>.Rig"
    humans[name]["mesh"]      -> renamed "<Name>.Mannequin"
    humans[name]["actions"]   -> {orig_name: action} (this import's pool)
    humans[name]["head_bone"] -> "DEF-head"   (framing getter)
    humans["rifle"]           -> wrapper-offset proxy box
    UA.audit({"humans": humans}) -> issues list (empty = clean)

The KD zombies / crowd NEVER come through this module (capsule mass
reads better for flight/tumble; raster budget: 4 rigs only).
"""
import math
import os

import bpy
from mathutils import Matrix, Vector

# vendored glTF (repo-relative, CWD-independent)
_GLTF = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                     "assets", "vendor", "ual",
                     "gltf-universal-animation-library-main", "glTF",
                     "AnimationLibrary_Godot_Standard.gltf")

# v3.3 color identity (duplicated from CA by the fork law: the capsule
# module stays frozen; ONE-COLOR-PER-BODY discipline)
SHIRT = {
    "Driver":  (0.82, 0.10, 0.12),   # RED
    "Girl":    (0.86, 0.12, 0.78),   # MAGENTA
    "Gunner":  (0.95, 0.52, 0.06),   # ORANGE
    "HeroZed": (0.08, 0.72, 0.90),   # CYAN (session-23 user note:
                   # emerald read as "zombie green" like the horde;
                   # cyan keeps the leader-pop without the class
                   # collision)
}
ACTOR_SCALE = 1.05     # gauntlet SCL: 1.651 m bind -> 1.734 m in [1.7,1.9]
HEROZED_SCALE = 1.09   # menace read (REV3 item 6: PIN constant, in the
                       # child MPI -- NEVER a keyed wrapper scale)
RIFLE_COL = (0.12, 0.12, 0.13)
RIFLE_SCALE = (0.07, 0.95, 0.11)
# review v4-impl-b P1-1: the capsule z 1.25 floats 0.23 m below the UAL
# aim-pose hands (measured hand base wrapper-z ~1.47, live-probed);
# z 1.40 puts the box 0.07 m under the hands (budget < 0.08). The
# muzzle rides in lockstep (+0.5225 y) -- total drift vs the capsule
# reference 0.09 m <= the 0.3 m budget (REV3 item 12).
RIFLE_LOC = (0.18, 0.35, 1.40)

# z-contract inputs (ual_probe_v4 live measurements)
SEATED_PELVIS = 0.5415   # Sitting_Enter FINAL frame, above feet-origin

# beat-map actions the bake needs (recorded per actor at import)
BEAT_ACTIONS = (
    "Sprint_Loop", "Jog_Fwd_Loop", "Walk_Loop",
    "Sitting_Enter", "Sitting_Exit", "Sitting_Idle_Loop",
    "Sitting_Talking_Loop", "Driving_Loop",
    "Pistol_Aim_Neutral", "Pistol_Aim_Down", "Pistol_Aim_Up",
    "Pistol_Idle_Loop", "Pistol_Shoot", "Pistol_Reload",
    "Punch_Cross", "Punch_Jab", "Interact",
    "Hit_Chest", "Hit_Head", "Death01", "Jump_Land", "Jump_Start",
)


def _upd():
    bpy.context.view_layer.update()
    bpy.context.view_layer.update()   # x2 (gotcha #27: eval order)


def _facing_sign(arm):
    """Bind facing probe (REV3 item 6: probe per import, never
    hard-code). Foot-bone tail local +Y world direction = toes."""
    foot = next(b for b in arm.pose.bones if "foot" in b.name.lower())
    m = arm.matrix_world @ foot.matrix
    fwd = (m.to_3x3() @ Vector((0, 1, 0))).normalized()
    return 1 if fwd.y >= 0 else -1


def _actor_material(name):
    mat = bpy.data.materials.new(f"Mat.UAL.{name}")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    rgb = SHIRT[name]
    bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
    try:
        bsdf.inputs["Roughness"].default_value = 0.6
    except KeyError:
        pass
    # workbench MATERIAL color reads the viewport display color
    mat.diffuse_color = (*rgb, 1.0)
    return mat


def _import_actor(name, scale):
    """One glTF import -> wrapper + reparented armature + pool dict."""
    scene = bpy.context.scene
    acts_before = {a.name for a in bpy.data.actions}
    obs_before = {o.name for o in bpy.data.objects}
    bpy.ops.import_scene.gltf(filepath=_GLTF)
    new_obs = [o for o in bpy.data.objects if o.name not in obs_before]
    new_acts = [a for a in bpy.data.actions if a.name not in acts_before]

    arm = next(o for o in new_obs if o.type == "ARMATURE")
    mesh = next(o for o in new_obs
                if o.type == "MESH" and o.find_armature() is not None)
    # stray scene-node meshes (the Icosphere): DELETE (REV3 item 6)
    for ob in new_obs:
        if ob not in (arm, mesh):
            bpy.data.objects.remove(ob, do_unlink=True)

    # facing probe at BIND (armature as-imported, nothing moved yet)
    sign = _facing_sign(arm)

    # wrapper EMPTY (fresh, identity basis, gotcha-#24-safe)
    root = bpy.data.objects.new(f"{name}.Root", None)
    root.empty_display_size = 0.15
    scene.collection.objects.link(root)

    # child MPI = FLIP @ SCALE (composition law: world = parent @ MPI
    # @ basis -- mpi_semantics_probe). FLIP only when the bind faces -Y.
    flip = Matrix.Rotation(math.pi, 4, 'Z') if sign < 0 else Matrix()
    child_mpi = flip @ Matrix.Scale(scale, 4)
    arm.parent = root
    arm.matrix_parent_inverse = child_mpi.copy()
    # the mesh must live INSIDE the wrapper tree (the glTF importer may
    # leave a skinned mesh at the scene root -- skin binding is via the
    # modifier, so a root-level mesh would NOT follow the armature
    # object transform and would strand at the world origin when the
    # wrapper moves). If it was parented to the armature, keep that
    # (it rides the flip+scale with the rig); otherwise attach it to
    # the wrapper with identity MPI (wrapper is fresh at identity ->
    # the mesh keeps its imported world transform exactly).
    if mesh.parent is None or mesh.parent.name != arm.name:
        mesh.parent = root
        mesh.matrix_parent_inverse = Matrix()

    # per-actor renames (rig hygiene, REV3 item 6: 4 imports would
    # otherwise collide as Rig/.001/.002/.003)
    arm.name = f"{name}.Rig"
    mesh.name = f"{name}.Mannequin"

    # the importer leaves a LIVE action slot (A_TPose / first stash) --
    # clear it: the bake utility owns slot assignment (REV2 playback
    # law). The 46 muted NLA stash tracks stay (audited muted).
    ad = arm.animation_data
    if ad is not None and ad.action is not None:
        ad.action = None

    # single material: ALL slots -> ONE datablock
    mat = _actor_material(name)
    for slot in mesh.material_slots:
        slot.material = mat

    # this import's action pool (original names -> action objects)
    pool = {}
    for a in new_acts:
        base = a.name
        for bn in BEAT_ACTIONS:
            if base == bn or (base.startswith(bn + ".")
                              and base[len(bn) + 1:].isdigit()):
                pool[bn] = a
                break

    _upd()
    return {"root": root, "armature": arm, "mesh": mesh,
            "actions": pool, "facing_sign": sign,
            "head_bone": "DEF-head", "pelvis_bone": "DEF-hips"}


def _build_rifle(gunner_root):
    """Wrapper-offset proxy (REV3 item 12): the capsule rifle box at the
    capsule root-local transform. Muzzle.Loc (parented by the scene
    script at rifle-local (0, 0.55, 0)) lands at the exact capsule
    reference world position -- zero muzzle drift by construction."""
    scene = bpy.context.scene
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
    rifle = bpy.context.active_object
    rifle.name = "Gunner.Rifle"
    rifle.data.name = "Gunner.Rifle.Mesh"
    rifle.scale = RIFLE_SCALE
    rifle.location = RIFLE_LOC
    mat = bpy.data.materials.new("CA.Rifle.UAL")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*RIFLE_COL, 1.0)
    mat.diffuse_color = (*RIFLE_COL, 1.0)
    rifle.data.materials.append(mat)
    rifle.parent = gunner_root
    rifle.matrix_parent_inverse = Matrix()   # wrapper-local == capsule
    return rifle


def build(ctx=None):
    """Build the 4 UAL hero actors + rifle proxy. Returns the humans
    dict (HU-shaped for the scene script; NO 'parts'/'poses' keys --
    the capsule-only branches in scene_escape_v4 never run in ual
    mode)."""
    humans = {}
    specs = (("Driver", ACTOR_SCALE), ("Girl", ACTOR_SCALE),
             ("Gunner", ACTOR_SCALE), ("HeroZed", HEROZED_SCALE))
    for name, scale in specs:
        humans[name] = _import_actor(name, scale)
    humans["rifle"] = _build_rifle(humans["Gunner"]["root"])
    n_acts = len(humans["Driver"]["actions"])
    print(f"[ual_actors] 4 UAL imports: 4 wrappers + 4 rigs + 4 mannequins"
          f" + rifle proxy; {n_acts} beat actions pooled per actor"
          f" (fresh-bake-only law)")
    return humans


# ---------------------------------------------------------------------------
# audit (module_audits ual branch; runs PRE-animate, post-build)
# ---------------------------------------------------------------------------
def audit(ctx):
    """Structural + hygiene audit. FAIL-CLOSED: any issue aborts the
    build before animation. Checks the wrapper layering invariants,
    rig purity (no drivers/shapekeys/constraints), single-material
    law, color identity, action pool coverage, NLA stash state, and
    the no-strays law."""
    issues = []
    humans = ctx["humanoids"] if "humanoids" in ctx else ctx.get(
        "humans", {})
    scales = {"Driver": ACTOR_SCALE, "Girl": ACTOR_SCALE,
              "Gunner": ACTOR_SCALE, "HeroZed": HEROZED_SCALE}

    # scene-root strays forbidden (they would become the hero's own
    # occluder + a motion rider finding -- REV2)
    for ob in bpy.data.objects:
        if ob.name.startswith("Icosphere"):
            issues.append(f"stray import artifact present: {ob.name}")

    for name in ("Driver", "Girl", "Gunner", "HeroZed"):
        d = humans.get(name)
        if not d or "root" not in d:
            issues.append(f"{name}: missing actor dict/root")
            continue
        root, arm, mesh = d["root"], d["armature"], d["mesh"]

        # wrapper: EMPTY, parented to JeepRoot (scene script did it)
        if root.type != 'EMPTY':
            issues.append(f"{name}: root is {root.type}, not EMPTY")
        if root.parent is None or root.parent.name != "JeepRoot":
            pn = root.parent.name if root.parent else None
            issues.append(f"{name}: wrapper not parented to JeepRoot "
                          f"(parent={pn})")
        # wrapper keys must be TRANSFORM-only (scale PIN 1.0 -- the
        # menace scale lives in the child MPI, never keyed)
        if tuple(round(c, 4) for c in root.scale) != (1.0, 1.0, 1.0):
            issues.append(f"{name}: wrapper scale {tuple(root.scale)} "
                          f"!= 1.0 (scale must live in the child MPI)")

        # armature: wrapper child, IDENTITY basis (all transform in MPI)
        if arm.parent is not root:
            issues.append(f"{name}: armature parent is "
                          f"{arm.parent.name if arm.parent else None}, "
                          f"not the wrapper")
        basis = arm.matrix_basis
        loc, rot, scl = basis.decompose()
        if (loc.length > 1e-6 or abs(rot.angle) > 1e-6
                or abs(scl.x - 1.0) > 1e-6 or abs(scl.y - 1.0) > 1e-6
                or abs(scl.z - 1.0) > 1e-6):
            issues.append(f"{name}: armature basis not identity (the "
                          f"flip/scale must live in matrix_parent_inverse)")

        # rig purity: no drivers / shapekeys / constraints (round-2
        # live-verified state must survive the reparent)
        if arm.animation_data and arm.animation_data.drivers:
            issues.append(f"{name}: armature has drivers")
        if mesh.data.shape_keys is not None:
            issues.append(f"{name}: mesh has shape keys")
        for c in arm.constraints:
            issues.append(f"{name}: armature constraint {c.name}")
        for c in mesh.constraints:
            issues.append(f"{name}: mesh constraint {c.name}")

        # mesh: skinned to THIS armature; single material datablock
        if mesh.find_armature() is not arm:
            issues.append(f"{name}: mesh not skinned to its own rig")
        mats = {s.material for s in mesh.material_slots if s.material}
        if len(mats) != 1:
            issues.append(f"{name}: {len(mats)} material datablocks "
                          f"(single-material law: all slots -> ONE)")
        else:
            m = next(iter(mats))
            got = tuple(round(c, 3) for c in m.diffuse_color[:3])
            exp = tuple(round(c, 3) for c in SHIRT[name])
            if any(abs(a - b) > 0.02 for a, b in zip(got, exp)):
                issues.append(f"{name}: color {got} != v3.3 table {exp}")

        # action slot EMPTY at build (no live action until the bake)
        ad = arm.animation_data
        if ad is not None and ad.action is not None:
            issues.append(f"{name}: live action at build time "
                          f"({ad.action.name}) -- bake assigns the slot")
        # NLA stash tracks: all muted (the import leaves 46 muted
        # stashes; a LIVE track would fight the bake)
        if ad is not None:
            for tr in ad.nla_tracks:
                if not tr.mute and len(tr.strips):
                    issues.append(f"{name}: UNMUTED NLA track {tr.name}")

        # action pool coverage
        missing = [bn for bn in BEAT_ACTIONS
                   if bn not in d.get("actions", {})]
        if missing:
            issues.append(f"{name}: action pool missing {missing[:4]}")

        # child MPI sanity: the rig's MESH must sit on the wrapper origin
        # plane at rest (feet-origin contract, gauntlet bind_feet_z 0.0;
        # ankle bones ride ~0.11 m above ground by anatomy -- measuring
        # the bone would false-fail). bound_box is mesh-LOCAL (rest
        # geometry): map through the object's pre-modifier world matrix.
        _upd()
        bb = [root.matrix_world.inverted() @ mesh.matrix_world @ Vector(v)
              for v in mesh.bound_box]
        mz = min(v.z for v in bb)
        if abs(mz) > 0.05 * scales[name]:
            issues.append(f"{name}: rig mesh bottom {mz:+.3f} m off the "
                          f"wrapper origin plane (z-contract broken)")

    # rifle proxy: Gunner wrapper child at the capsule transform
    rifle = humans.get("rifle")
    gunner_root = humans.get("Gunner", {}).get("root")
    if rifle is None or gunner_root is None:
        issues.append("rifle proxy missing")
    else:
        if rifle.parent is not gunner_root:
            issues.append("rifle proxy not parented to Gunner wrapper")
        if tuple(round(c, 3) for c in rifle.location) != \
                tuple(round(c, 3) for c in RIFLE_LOC):
            issues.append(f"rifle proxy loc {tuple(rifle.location)} != "
                          f"capsule reference {RIFLE_LOC}")
        if tuple(round(c, 3) for c in rifle.scale) != RIFLE_SCALE:
            issues.append(f"rifle proxy scale {tuple(rifle.scale)} != "
                          f"{RIFLE_SCALE}")
    return issues
