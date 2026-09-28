"""
contact_discs.py -- v4 step 5: contact-grounding discs (PLAN_v4 A4,
REV2 item 5 + REV3 item 3, the shadow-pass fallback).

DECISION (benchmarked step 5): the Workbench shadow pass costs 3.9x
(0.97s -> 3.80s/frame at delivery settings) -- FAR over the +25%
budget -- so the plan's fallback applies: contact-shadow discs.

Classes (REV2 item 5 parenting split):
  * JEEP-STATIC (JeepRoot children, subject tree): 4 wheel discs +
    the seated-pair road discs + the standing-gunner deck disc. They
    ride the jeep's dip/jolt keys WITH the wheels (consistent: the
    wheels themselves penetrate the road stack during the 3-5f jolts).
  * BELT-FOLLOW (BeltRoot children, keyed every 6f + LINEAR at the
    belt's own cadence): the sprinting trio + HeroZed (chase/lunge/
    thrown) -- the disc follows the subject's WORLD x/y path (read
    from the wrapper's evaluated keys, composed to belt-local) and
    stays road-pinned in z. When the trio boards, their discs stop
    under the boarding spot and stream away with the world exactly
    like the ground does (the jeep-static seat discs take over).
  * KD-AT-REST (BeltRoot children): a disc at each KD's final keyed
    position, scale-ON at the rest frame (the FX taxonomy transient
    lifecycle: scale 0 before, 1 after -- no pre-landing shadow).
  * CROWD (BeltRoot children, full path copy): sampled agents get a
    disc whose x/y location fcurves are COPIED from the agent's baked
    belt-local keys (regenerate-from-bake, idempotent) -- a belt-
    static disc would depart a running agent in ~1 s (REV3 item 3).
    Sampling: within 25 m of the active camera at any shot's mid
    frame, plus 1/4 of the remainder, cap 300 discs.

Z LAW: all discs sit at world/belt z 0.033 + (i % 8) * 0.0007 (above
the road stack top 0.03; the cycling jitter avoids disc-disc z-
fighting while staying within a 5mm band -- coplanarity-exempt by
declaration, depth-math-legal 1cm-class gap).

Flat-color note: the plan's "radial-gradient quads" are not achievable
under Workbench MATERIAL color mode (single diffuse per material);
flat dark discs (0.24 grey vs the 0.5 road) carry the grounding read.
Documented deviation, measured by contact_audit (pixel transition).
"""
import math

import bpy
from mathutils import Vector
from blender_kit import fcurves_new, iter_fcurves

DISC_Z = 0.033
JITTER = 0.0007
DISC_COLOR = (0.18, 0.18, 0.20)
CROWD_CAP = 300
RADIUS = {
    "wheel": 0.45, "seat": 0.46, "gunner": 0.42, "hero": 0.42,
    "kd": 0.50, "crowd": 0.40,
}


def _disc_mesh(name, radius):
    """Flat ground quad (the FX-quad create_grid pattern -- a zero-depth
    cone self-z-fights its coincident caps and renders invisible)."""
    import bmesh
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=radius)
    bm.to_mesh(me)
    bm.free()
    return me


def _mat():
    m = bpy.data.materials.new("Mat.Contact.Disc")
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*DISC_COLOR, 1.0)
    m.diffuse_color = (*DISC_COLOR, 1.0)   # workbench reads this
    return m


def _new_disc(name, radius, parent, i, mat):
    me = _disc_mesh(name, radius)
    ob = bpy.data.objects.new(name, me)
    ob.data.materials.append(mat)
    ob.parent = parent
    ob.matrix_parent_inverse = Matrix()   # parent-local == authored
    ob.location = (0.0, 0.0, DISC_Z + (i % 8) * JITTER)
    bpy.context.scene.collection.objects.link(ob)
    return ob


from mathutils import Matrix  # noqa: E402


def _road_pin_keys(d, jeep, track_fn, i, scene, fps=24):
    """Key the disc's jeep-local transform so its WORLD position stays
    road-pinned (z = DISC_Z+jitter) while tracking the subject's world
    x/y (weave/drive). Counters the lurch pitch, which sank fixed discs
    up to 5.7 cm under the road (live-measured: Wheel.0 world z
    -0.024 at f221 = DISC_Z 0.033 - sin(2.4deg)*1.35)."""
    z_world = DISC_Z + (i % 8) * JITTER
    for f in range(1, 1081, 6):
        scene.frame_set(f)
        bpy.context.view_layer.update()
        wx, wy = track_fn(f)
        world = Vector((wx, wy, z_world))
        d.location = (jeep.matrix_world.inverted() @ world)
        d.keyframe_insert(data_path="location", frame=f)
    _linear(d)


def _jeep_static(ctx, mat, counters):
    """Wheels + seated pair + gunner (JeepRoot children). Road-level
    discs (wheels + seats) get ROAD-PINNED keys (pitch/dip-safe); the
    gunner disc rides the bed deck parent-fixed (the deck tilts with
    the jeep -- correct: the gunner stands ON it)."""
    import bpy as _b
    jeep = ctx["jeep"]
    scene = ctx["scene"]
    out = []
    wheels = ctx["vehicles"]["wheels"]

    def wheel_track(i):
        def tf(f):
            # the wheel's EVALUATED world position (frame was set + the
            # view layer updated by _road_pin_keys before calling)
            wp = wheels[i].matrix_world.translation
            return wp.x, wp.y
        return tf

    for i in range(len(wheels)):
        d = _new_disc(f"Contact.Wheel.{i}", RADIUS["wheel"], jeep,
                      counters[0], mat)
        _road_pin_keys(d, jeep, wheel_track(i), counters[0], scene)
        counters[0] += 1
        out.append(d)

    def seat_track(sx, sy):
        def tf(f):
            mw = jeep.matrix_world
            p = mw @ Vector((sx, sy, 0.0))
            return p.x, p.y
        return tf

    for name, (sx, sy) in (("Driver", (-0.42, 0.58)),
                           ("Girl", (0.42, 0.58))):
        d = _new_disc(f"Contact.Seat.{name}", RADIUS["seat"], jeep,
                      counters[0], mat)
        _road_pin_keys(d, jeep, seat_track(sx, sy), counters[0], scene)
        counters[0] += 1
        out.append(d)
    # gunner: standing on the bed deck -- disc ON THE DECK (parent-
    # fixed; the deck is a jeep surface, not the road)
    d = _new_disc("Contact.Gunner", RADIUS["gunner"], jeep,
                  counters[0], mat)
    d.location = (0.0, -1.35, 0.72 + DISC_Z + (counters[0] % 8) * JITTER)
    counters[0] += 1
    out.append(d)
    return out


def _belt_follow_heroes(ctx, mat, counters, dist_fn, fps=24):
    """Sprinting trio + HeroZed: belt-local discs keyed along the
    subject's WORLD path (wrapper x/y evaluated per frame + dist(t)
    composition). Post-boarding the keys stop advancing -> the disc
    streams away with the world (the ground really does)."""
    belt = ctx["belt"]
    scene = ctx["scene"]
    out = []
    heroes = ("Driver", "Girl", "Gunner", "HeroZed")
    for name in heroes:
        root = ctx["humans"][name]["root"]
        d = _new_disc(f"Contact.Hero.{name}", RADIUS["hero"], belt,
                      counters[0], mat)
        i = counters[0]
        counters[0] += 1
        # key every 6f at the belt cadence (LINEAR, like BeltRoot)
        stop_f = {"Driver": 148, "Girl": 154, "Gunner": 160,
                  "HeroZed": 1080}[name]
        for f in range(1, min(stop_f, 1081) + 1, 6):
            scene.frame_set(f)
            bpy.context.view_layer.update()
            wp = root.matrix_world.translation
            t = (f - 1) / fps
            d.location = (wp.x, wp.y + dist_fn(t),
                          DISC_Z + (i % 8) * JITTER)
            d.keyframe_insert(data_path="location", frame=f)
        _linear(d)
        out.append(d)
    return out


def _kd_at_rest(ctx, mat, counters, knockdowns, frame_at):
    """One disc per KD at its final keyed position, scale-ON at the
    rest frame (FX taxonomy: scale 0 before, 1 after, CONSTANT)."""
    belt = ctx["belt"]
    out = []
    kd_map = {o.name: o for o in ctx["chars"]["zombies"]["kd"]}
    import random as _r
    rng = _r.Random(77)          # deterministic disc jitter
    for name, t_hit, x_off, style in knockdowns:
        ob = kd_map.get(f"Zed.{name}")
        if ob is None:
            continue
        d = _new_disc(f"Contact.KD.{name}", RADIUS["kd"], belt,
                      counters[0], mat)
        i = counters[0]
        counters[0] += 1
        # final keyed belt-local position (read the last location keys)
        ad = ob.animation_data
        last_x, last_y = ob.location.x, ob.location.y
        last_f = 1
        if ad and ad.action:
            for fc in iter_fcurves(ad.action):
                if fc.data_path == "location":
                    for kp in fc.keyframe_points:
                        if kp.co.x > last_f:
                            last_f = kp.co.x
        scene = ctx["scene"]
        scene.frame_set(int(last_f))
        bpy.context.view_layer.update()
        last_y = ob.location.y     # evaluated final belt-local y
        d.location = (last_x, last_y, DISC_Z + (i % 8) * JITTER)
        # scale-ON at the rest frame (transient lifecycle)
        f_rest = int(last_f)
        d.scale = (0.0, 0.0, 0.0)
        d.keyframe_insert(data_path="scale", frame=1)
        d.scale = (1.0, 1.0, 1.0)
        d.keyframe_insert(data_path="scale", frame=max(2, f_rest))
        if d.animation_data and d.animation_data.action:
            for fc in iter_fcurves(d.animation_data.action):
                if fc.data_path == "scale":
                    for kp in fc.keyframe_points:
                        kp.interpolation = 'CONSTANT'
        out.append(d)
        _ = rng
    return out


def _sample_crowd(ctx, cams_table, shots, dist_fn, fps=24):
    """Agents within 25 m of the active camera at any shot's mid frame
    (+ 1/4 of the rest), capped. Returns the sampled agent objects."""
    scene = ctx["scene"]
    agents = [a for a in ctx["agents"].agents
              if getattr(a, "obj", None) is not None]
    if not agents:
        return []
    near = set()
    for sid, f0, f1, _d in shots:
        f_mid = (f0 + f1) // 2
        info = cams_table.get(f"CAM_{sid}")
        if info is None:
            continue
        cam = info["cam"]
        scene.frame_set(f_mid)
        bpy.context.view_layer.update()
        cw = cam.matrix_world.translation
        for a in agents:
            wp = a.obj.matrix_world.translation
            if (wp - cw).length <= 25.0:
                near.add(a.name)
    import random as _r
    rng = _r.Random(78)
    rest = [a.name for a in agents if a.name not in near]
    sampled = sorted(near) + rng.sample(rest, min(len(rest), len(rest) // 4))
    sampled = sampled[:CROWD_CAP]
    by_name = {a.name: a for a in agents}
    return [by_name[n] for n in sampled if n in by_name]


def _crowd_discs(ctx, mat, counters, sampled):
    """Full path copy: each disc's x/y location fcurves are copies of
    the agent's baked belt-local keys (regenerate-from-bake)."""
    belt = ctx["belt"]
    out = []
    for k, a in enumerate(sampled):
        d = _new_disc(f"Contact.Crowd.{k:03d}", RADIUS["crowd"], belt,
                      counters[0], mat)
        i = counters[0]
        counters[0] += 1
        d.location = (a.obj.location.x, a.obj.location.y,
                      DISC_Z + (i % 8) * JITTER)
        ad = a.obj.animation_data
        if ad and ad.action:
            # build the action + fcurves FIRST, assign + PIN THE SLOT
            # LAST (the action-slot law: a fresh action left unbound
            # evaluates NOTHING -- the disc sits at its basis, 12m from
            # its agent mid-timeline; live-probed step 5)
            act = bpy.data.actions.new(f"Contact.Crowd.{k:03d}.Act")
            act.use_fake_user = True
            for fc in iter_fcurves(ad.action):
                if fc.data_path == "location" \
                        and fc.array_index in (0, 1):
                    nfc = fcurves_new(act, "location",
                                          index=fc.array_index)
                    nfc.extrapolation = 'CONSTANT'
                    pts = [(kp.co.x, kp.co.y) for kp in
                           fc.keyframe_points]
                    nfc.keyframe_points.add(len(pts))
                    kps = nfc.keyframe_points
                    for j, (fx, fy) in enumerate(pts):
                        kps[j].co = (float(fx), float(fy))
                        kps[j].interpolation = 'LINEAR'
                        kps[j].handle_left_type = 'VECTOR'
                        kps[j].handle_right_type = 'VECTOR'
                    nfc.update()
            nd = d.animation_data_create() if \
                d.animation_data is None else d.animation_data
            nd.action = act
            if not act.slots:
                # force the auto legacy-slot creation, then bind
                nd.action = None
                nd.action = act
            if act.slots:
                nd.action_slot = act.slots[0]
        out.append(d)
    return out


def _linear(ob):
    ad = ob.animation_data
    if ad and ad.action:
        for fc in iter_fcurves(ad.action):
            if fc.data_path == "location":
                for kp in fc.keyframe_points:
                    kp.interpolation = 'LINEAR'


def build_contact_discs(ctx, *, dist_fn, shots, knockdowns, frame_at,
                        fps=24):
    """Idempotent: removes any existing Contact.* objects first."""
    for ob in list(bpy.data.objects):
        if ob.name.startswith("Contact."):
            bpy.data.objects.remove(ob, do_unlink=True)
    mat = bpy.data.materials.get("Mat.Contact.Disc") or _mat()
    counters = [0]
    made = []
    made += _jeep_static(ctx, mat, counters)
    made += _belt_follow_heroes(ctx, mat, counters, dist_fn, fps)
    made += _kd_at_rest(ctx, mat, counters, knockdowns, frame_at)
    sampled = _sample_crowd(ctx, ctx["cams"], shots, dist_fn, fps)
    made += _crowd_discs(ctx, mat, counters, sampled)
    print(f"[contact_discs] {len(made)} discs (jeep-static "
          f"{7}, hero-follow 4, KD {len(knockdowns)}, crowd "
          f"{len(sampled)}) -- shadow pass rejected at 3.9x cost")
    ctx["contact_discs"] = made
    return made
