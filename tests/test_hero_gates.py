# VENDORED 2026-10-16 from mainline blender-agent-kit @6943ab5 (vision-kit s21 vendor round; zero code drift; vision deltas must land as sanctioned deltas per docs/VENDOR_LEDGER.md)
"""test_hero_gates.py -- session-30 pins for gates 18/19 (hero_gates.py).

Proves each gate can FAIL on the exact shipped bug classes (the S30-A
forensic numbers) and PASS the fixed shapes. Fixtures are synthetic
GLBs built at the BYTE level (float32 accessors + bufferViews into a
real blob) so the tests exercise the actual accessor/track/composition
code path the exporter uses -- not mocked pure functions.
"""
import math
import struct
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "scripts"))
import hero_gates as HG  # noqa: E402


# ---------------------------------------------------------------------------
# synthetic GLB builder (real bytes: bufferViews + float32 accessors)
# ---------------------------------------------------------------------------

class Blob:
    def __init__(self):
        self.buf = bytearray()
        self.views = []
        self.accessors = []

    def add(self, arr_flat):
        off = len(self.buf)
        self.buf += struct.pack(f"<{len(arr_flat)}f", *arr_flat)
        self.views.append({"buffer": 0, "byteOffset": off,
                           "byteLength": len(arr_flat) * 4})
        return len(self.views) - 1

    def accessor(self, arr_flat, comps, typ):
        vi = self.add(arr_flat)
        n = len(arr_flat) // comps
        self.accessors.append({"bufferView": vi, "componentType": 5126,
                               "count": n, "type": typ})
        return len(self.accessors) - 1


def rebuild_glb(nodes, anims):
    """nodes: [{name, parent (idx|None), translation/rotation/scale}].
    anims: [{name, channels: [(node_idx, path, times, vals, interp?)]}]
    -- interp defaults to LINEAR (CONSTANT Blender keys export as STEP)."""
    blob = Blob()
    gltf_nodes = []
    for i, nd in enumerate(nodes):
        g = {"name": nd["name"]}
        kids = [j for j, n2 in enumerate(nodes) if n2.get("parent") == i]
        if kids:
            g["children"] = kids
        for k in ("translation", "rotation", "scale"):
            if k in nd:
                g[k] = list(nd[k])
        gltf_nodes.append(g)
    gltf_anims = []
    for an in anims:
        channels = []
        samplers = []
        for ci, ch_spec in enumerate(an["channels"]):
            ni, path, times, vals = ch_spec[:4]
            interp = ch_spec[4] if len(ch_spec) > 4 else "LINEAR"
            comps = 4 if path == "rotation" else 3
            inp = blob.accessor(list(times), 1, "SCALAR")
            outp = blob.accessor([c for v in vals for c in v], comps,
                                 "VEC4" if comps == 4 else "VEC3")
            samplers.append({"input": inp, "output": outp,
                             "interpolation": interp})
            channels.append({"sampler": ci, "target": {"node": ni,
                                                       "path": path}})
        gltf_anims.append({"name": an["name"], "channels": channels,
                           "samplers": samplers})
    gltf = {"nodes": gltf_nodes, "animations": gltf_anims,
            "accessors": blob.accessors, "bufferViews": blob.views,
            "buffers": [{"byteLength": len(blob.buf)}]}
    return gltf, bytes(blob.buf)


def quat_x(deg):
    r = math.radians(deg) / 2.0
    return (math.sin(r), 0.0, 0.0, math.cos(r))


def quat_y(deg):
    r = math.radians(deg) / 2.0
    return (0.0, math.sin(r), 0.0, math.cos(r))


def gunner_fixture(twist_deg):
    """The UAL gunner chain. The twist is an animated rotation track on
    DEF-spine.001 / DEF-thigh.L / DEF-thigh.R, constant across the
    timeline (exactly the baked v5_2/v6_0 hold). The shoulder.R
    subtree carries the COUNTER rotation (in the real scene the
    two-bone IK solves the hands onto fixed armature-space targets, so
    the rifle/aim stays on the aim axis no matter what the chest
    does -- the fixture mirrors that with -twist on shoulder.R). The
    rifle's static 180-deg X rotation puts its -Z (bore) onto the
    hips' +Z (a square aim): twist 0 = the fixed square stance, 90 =
    the shipped corkscrew."""
    nodes = [
        {"name": "Gunner.Rig"},
        {"name": "root", "parent": 0},
        {"name": "DEF-hips", "parent": 1},
        {"name": "DEF-spine.001", "parent": 2},
        {"name": "DEF-spine.002", "parent": 3},
        {"name": "DEF-spine.003", "parent": 4},
        {"name": "DEF-neck", "parent": 5},
        {"name": "DEF-head", "parent": 6},
        {"name": "DEF-thigh.L", "parent": 2},
        {"name": "DEF-thigh.R", "parent": 2},
        {"name": "DEF-shoulder.R", "parent": 5,
         "rotation": quat_y(-twist_deg)},
        {"name": "DEF-upper_arm.R", "parent": 10},
        {"name": "DEF-forearm.R", "parent": 11},
        {"name": "DEF-hand.R", "parent": 12},
        {"name": "Gunner.Rifle", "parent": 13,
         "rotation": quat_x(180.0)},
    ]
    times = [0.04, 22.5, 45.0]
    anims = [{
        "name": "UAL.Gunner.Baked",
        "channels": [
            (3, "rotation", times, [quat_y(twist_deg)] * 3),
            (8, "rotation", times, [quat_y(twist_deg)] * 3),
            (9, "rotation", times, [quat_y(twist_deg)] * 3),
        ],
    }]
    return nodes, anims


class TestSmokeKeyPlan(unittest.TestCase):
    """The s30-r1 review P2: pin the SCENE-DERIVED key plan (the same
    hero_gates.smoke_key_plan _kf_flash_v5 calls), built from the REAL
    MUZZLE_BURSTS_V3 table -- not a hand-authored intended shape."""

    BURSTS = ((352, 380, 7), (384, 396, 6), (470, 490, 8), (745, 770, 7),
              (397, 418, 5), (755, 768, 4))

    def _events(self, quad_i, closeup=False):
        ev = {}
        for f0, f1, every in self.BURSTS:
            k = 0.15 if (closeup and (f0, f1, every) == (397, 418, 5)) \
                else 1.0
            f = f0
            while f <= f1:
                fo = f + 1 + quad_i
                ev[fo] = 0.3 * k
                ev[fo + 4] = 0.9 * k
                ev[fo + 8] = 1.3 * k
                ev[fo + 9] = 0.0
                f += every
        return ev

    def test_no_ramp_violations_on_real_cadences(self):
        """Every nonzero-value key must follow a key <= 5 frames earlier
        (the SMOKE_GAP=4 law + 1) -- no long linear ramps anywhere,
        on every quad, wide and closeup."""
        for i in range(4):
            for closeup in (False, True):
                keys = HG.smoke_key_plan(self._events(i, closeup))
                prev_f = 1
                for fr, v in keys:
                    if v > 0.0:
                        self.assertLessEqual(
                            fr - prev_f, 5,
                            f"quad {i} closeup={closeup}: ramp gap "
                            f"{fr - prev_f}f into f{fr}")
                    prev_f = fr

    def test_first_onset_gets_prezero(self):
        """The s30-r1 P1-2 regression: the FIRST burst onset (f353 for
        quad 0) must be preceded by an explicit zero key at f352 --
        the f1 leading zero is 352 frames away on a LINEAR fcurve."""
        keys = HG.smoke_key_plan(self._events(0))
        first_onset = next(fr for fr, v in keys if v > 0.0)
        self.assertEqual(first_onset, 353)
        prior = [v for fr, v in keys if fr < first_onset]
        self.assertEqual(prior[-1], 0.0)
        self.assertEqual(max(f for f, _ in keys if f < first_onset),
                         first_onset - 1)

    def test_final_key_is_zero(self):
        for i in range(4):
            keys = HG.smoke_key_plan(self._events(i))
            self.assertEqual(keys[-1][1], 0.0)

    def test_none_prev_regression(self):
        """prev_f=None (the P1-2 bug) leaves the first onset with NO
        pre-onset key -- the 352-frame linear ramp from the f1 zero
        stands: proving the first_frame seed is load-bearing."""
        ev = self._events(0)
        keys = []
        prev_f = None          # the bug
        for fr in sorted(ev):
            v = ev[fr]
            if v > 0.0 and prev_f is not None and fr - prev_f > 4:
                keys.append((fr - 1, 0.0))
            keys.append((fr, v))
            prev_f = fr
        first_onset = next(fr for fr, v in keys if v > 0.0)
        prior = [v for fr, v in keys if fr < first_onset]
        self.assertEqual(prior, [])   # nothing breaks the f1->onset ramp


class TestGate18AimCoherence(unittest.TestCase):
    FPS = 24.0

    def test_twisted_fails_all_three_laws(self):
        """The shipped bug: +90 deg yaw on spine.001 + both thighs,
        held through the aim window."""
        gltf, blob = rebuild_glb(*gunner_fixture(90.0))
        probs = HG.aim_coherence_problems(gltf, blob, self.FPS,
                                          aim_f0=157, f_end=1080)
        self.assertEqual(len(probs), 3, probs)
        self.assertIn("head faces 90.0 deg", probs[0])
        self.assertIn("corkscrew", probs[1])
        self.assertIn("90.0 deg", probs[1])
        self.assertIn("stance", probs[2])
        self.assertIn("90.0 deg", probs[2])

    def test_coherent_square_stance_passes(self):
        gltf, blob = rebuild_glb(*gunner_fixture(0.0))
        probs = HG.aim_coherence_problems(gltf, blob, self.FPS,
                                          aim_f0=157, f_end=1080)
        self.assertEqual(probs, [], probs)

    def test_bladed_stance_within_limits_passes(self):
        """A natural ~30 deg blade (torso + feet) stays green -- the
        re-author latitude if square reads too stiff."""
        gltf, blob = rebuild_glb(*gunner_fixture(30.0))
        probs = HG.aim_coherence_problems(gltf, blob, self.FPS,
                                          aim_f0=157, f_end=1080)
        self.assertEqual(probs, [], probs)

    def test_head_off_bore_fails_head_law_only(self):
        """Head yawed 60 deg over a square body: ONLY the head law
        fires (the law-separation pin)."""
        nodes, anims = gunner_fixture(0.0)
        nodes[7]["rotation"] = quat_y(60.0)   # DEF-head local yaw
        gltf, blob = rebuild_glb(nodes, anims)
        probs = HG.aim_coherence_problems(gltf, blob, self.FPS,
                                          aim_f0=157, f_end=1080)
        self.assertEqual(len(probs), 1, probs)
        self.assertIn("head faces", probs[0])

    def test_no_gunner_chain_skips(self):
        gltf, blob = rebuild_glb([{"name": "Street"}], [])
        probs = HG.aim_coherence_problems(gltf, blob, self.FPS,
                                          aim_f0=157, f_end=1080)
        self.assertEqual(probs, [])

    def test_missing_joint_fails_closed(self):
        nodes, anims = gunner_fixture(0.0)
        del nodes[7]          # DEF-head gone
        gltf, blob = rebuild_glb(nodes, anims)
        probs = HG.aim_coherence_problems(gltf, blob, self.FPS,
                                          aim_f0=157, f_end=1080)
        self.assertEqual(len(probs), 1)
        self.assertIn("unauditable", probs[0])


class TestGate19FxOffState(unittest.TestCase):
    FPS = 24.0
    WINDOWS = {
        "FX.Muzzle": [(352, 366), (359, 373), (745, 759)],
        "FX.Spark": [(755, 780)],
    }

    def _fx_glb(self, tracks):
        """tracks: [(name, times_sec, scale_vals Nx3, interp?)]"""
        nodes = [{"name": "Muzzle.Loc"}]
        anims = []
        for tr in tracks:
            name, times, vals = tr[0], tr[1], tr[2]
            interp = tr[3] if len(tr) > 3 else "LINEAR"
            nodes.append({"name": name, "parent": 0})
            anims.append({"name": name + "Action",
                          "channels": [(len(nodes) - 1, "scale",
                                        times, vals, interp)]})
        return rebuild_glb(nodes, anims)

    def test_leaking_smoke_fails(self):
        """The shipped bug: LINEAR ramp 0 -> 0.3 across a long pre-burst
        gap (smoke visible before the first shot at f352)."""
        t = [0.04, 5.0, 10.0, 14.6]
        v = [(0.0, 0.0, 0.0), (0.1, 0.1, 0.1), (0.2, 0.2, 0.2),
             (0.3, 0.3, 0.3)]
        gltf, blob = self._fx_glb([("FX.MuzzleSmoke.0", t, v)])
        probs = HG.fx_offstate_problems(gltf, blob, self.FPS,
                                        self.WINDOWS, [], f_end=1080)
        self.assertEqual(len(probs), 1, probs)
        self.assertIn("FX.MuzzleSmoke.0", probs[0])
        self.assertIn("outside its FX.Muzzle event windows", probs[0])

    def test_gated_star_passes(self):
        """CONSTANT-style step gating (the real star/dark quads): STEP
        interpolation holds 0 outside the burst windows -- the gate
        must NOT false-fire on the linear read of a step track."""
        t = [0.04, 352 / 24, 354 / 24, 359 / 24, 361 / 24, 45.0]
        v = [(0.0, 0.0, 0.0), (1.8, 1.8, 1.8), (0.0, 0.0, 0.0),
             (2.2, 2.2, 2.2), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)]
        gltf, blob = self._fx_glb([("FX.MuzzleStar.0", t, v, "STEP")])
        probs = HG.fx_offstate_problems(gltf, blob, self.FPS,
                                        self.WINDOWS, [], f_end=1080)
        self.assertEqual(probs, [], probs)

    def test_step_track_sampled_linearly_would_false_fire(self):
        """The same star keys declared LINEAR DO leak (a slow ramp to
        the first burst) -- proves the STEP/LINEAR distinction is
        load-bearing, not decorative."""
        t = [0.04, 352 / 24, 354 / 24, 359 / 24, 361 / 24, 45.0]
        v = [(0.0, 0.0, 0.0), (1.8, 1.8, 1.8), (0.0, 0.0, 0.0),
             (2.2, 2.2, 2.2), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)]
        gltf, blob = self._fx_glb([("FX.MuzzleStar.0", t, v, "LINEAR")])
        probs = HG.fx_offstate_problems(gltf, blob, self.FPS,
                                        self.WINDOWS, [], f_end=1080)
        self.assertEqual(len(probs), 1, probs)

    def test_fixed_smoke_passes(self):
        """The fix shape: explicit pre-onset zero key one frame before
        the puff onset -- no long ramps."""
        t = [0.04, 351 / 24, 352 / 24, 356 / 24, 360 / 24, 361 / 24,
             45.0]
        v = [(0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.3, 0.3, 0.3),
             (0.9, 0.9, 0.9), (1.3, 1.3, 1.3), (0.0, 0.0, 0.0),
             (0.0, 0.0, 0.0)]
        gltf, blob = self._fx_glb([("FX.MuzzleSmoke.0", t, v)])
        probs = HG.fx_offstate_problems(gltf, blob, self.FPS,
                                        self.WINDOWS, [], f_end=1080)
        self.assertEqual(probs, [], probs)

    def test_world_litter_exemption(self):
        """FX.Spark08 (road debris) holds scale 1 AFTER its event (by
        design) but must be 0 BEFORE it."""
        t = [0.04, 754 / 24, 755 / 24, 45.0]
        v = [(0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (1.0, 1.0, 1.0),
             (1.0, 1.0, 1.0)]
        gltf, blob = self._fx_glb([("FX.Spark08", t, v)])
        probs = HG.fx_offstate_problems(gltf, blob, self.FPS,
                                        self.WINDOWS, ["FX.Spark08"],
                                        f_end=1080)
        self.assertEqual(probs, [], probs)
        # WITHOUT the exemption the hold fails (exemption is
        # load-bearing, not a blanket pass)
        probs = HG.fx_offstate_problems(gltf, blob, self.FPS,
                                        self.WINDOWS, [], f_end=1080)
        self.assertEqual(len(probs), 1, probs)

    def test_litter_pre_event_must_still_be_off(self):
        t = [0.04, 20.0, 45.0]
        v = [(0.0, 0.0, 0.0), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0)]
        gltf, blob = self._fx_glb([("FX.Spark08", t, v)])
        probs = HG.fx_offstate_problems(gltf, blob, self.FPS,
                                        self.WINDOWS, ["FX.Spark08"],
                                        f_end=1080)
        self.assertEqual(len(probs), 1, probs)
        self.assertIn("FX.Spark08", probs[0])

    def test_undeclared_family_fails_closed(self):
        t = [0.04, 10.0, 45.0]
        v = [(0.0, 0.0, 0.0), (0.5, 0.5, 0.5), (0.5, 0.5, 0.5)]
        gltf, blob = self._fx_glb([("FX.CoolNew.0", t, v)])
        probs = HG.fx_offstate_problems(gltf, blob, self.FPS,
                                        self.WINDOWS, [], f_end=1080)
        self.assertEqual(len(probs), 1, probs)
        self.assertIn("no FX_EVENT_WINDOWS family", probs[0])

    def test_static_scale_node_skipped(self):
        """FX nodes without an animated scale track (e.g. the light)
        are not the gate's business."""
        nodes = [{"name": "FX.SparkLight", "scale": (1.0, 1.0, 1.0)}]
        gltf, blob = rebuild_glb(nodes, [])
        probs = HG.fx_offstate_problems(gltf, blob, self.FPS,
                                        self.WINDOWS, [], f_end=1080)
        self.assertEqual(probs, [])


class TestGate20MotionContinuity(unittest.TestCase):
    """s31 pins: the sprint-transition storm + the recoil-pop sign-flip
    class. Fixtures reuse the gunner_fixture chain (rig root + bones +
    rifle) with per-frame rotation tracks around the flagged frames."""

    FPS = 24.0

    def _glb(self, tracks_spec):
        """tracks_spec: [(node_name, [(frame, quat), ...])] -- builds
        per-frame rotation keys on the gunner chain."""
        nodes, _anims = gunner_fixture(0.0)
        anims = [{
            "name": "UAL.Gunner.Baked",
            "channels": [
                (next(i for i, n in enumerate(nodes)
                      if n["name"] == nm), "rotation",
                 [f / self.FPS for f, _q in keys],
                 [q for _f, q in keys])
                for nm, keys in tracks_spec
            ],
        }]
        return rebuild_glb(nodes, anims)

    def test_sprint_storm_flip_fires(self):
        """thigh.L flipping 176.8 deg in ONE frame at f153 (the exact
        take-6 S3 class) must fire the sprint-window law (>90)."""
        q0 = quat_y(20.0)
        q1 = quat_y(196.8)          # 176.8 deg from q0
        gltf, blob = self._glb([
            ("DEF-thigh.L", [(150, q0), (153, q0), (154, q1), (160, q1)])
        ])
        probs = HG.motion_continuity_problems(
            gltf, blob, self.FPS, 1, 156, HG.SPRINT_SWEEP_MAX)
        self.assertEqual(len(probs), 1, probs)
        self.assertIn("DEF-thigh.L", probs[0])
        self.assertIn("176.8", probs[0])

    def test_legit_stride_speed_passes(self):
        """A coherent library stride peaks 46.7 deg/frame -- under the
        90 sprint threshold."""
        # a staircase advancing exactly 46.7 deg every frame -- the
        # library stride's measured PEAK per-frame speed, sustained
        # (a square wave would step 93 deg at each phase turn -- a
        # fixture bug the first version of this test shipped with)
        keys = [(f, quat_y(((f - 1) * 46.7) % 360.0 - 180.0))
                for f in range(1, 157)]
        gltf, blob = self._glb([("DEF-thigh.R", keys)])
        probs = HG.motion_continuity_problems(
            gltf, blob, self.FPS, 1, 156, HG.SPRINT_SWEEP_MAX)
        self.assertEqual(probs, [])

    def test_aim_window_sign_flip_fires(self):
        """upper_arm.R alternating between the aim pose and a mirrored
        garbage pose -- the BAKED shape of the f381 class (the source
        sign-flip makes Blender's componentwise lerp pass through the
        zero vector; the normalized midpoint lands ~174 deg from aim.
        NOTE: the negated quaternion alone is NOT a rotation delta
        (2*arccos(|dot|) = 0 -- double cover); the fixture must bake
        the GENUINE post-normalization step, exactly what take-6
        shipped)."""
        qa = quat_y(0.0)
        qb = quat_y(174.0)
        keys = [(f, qa if (f // 2) % 2 == 0 else qb)
                for f in range(157, 400)]
        gltf, blob = self._glb([("DEF-upper_arm.R", keys)])
        probs = HG.motion_continuity_problems(
            gltf, blob, self.FPS, 157, 1080, HG.AIM_SWEEP_MAX)
        self.assertEqual(len(probs), 1, probs)
        self.assertIn("DEF-upper_arm.R", probs[0])
        self.assertIn("174.0", probs[0])

    def test_legit_recoil_pops_pass(self):
        """Recoil pops of ~15 deg/frame in the aim window pass."""
        keys = []
        for f in range(157, 500):
            # sawtooth: +15 for 3 frames, -15 for 3 (the pop shape)
            k = (f - 157) % 6
            ang = 15.0 if k < 3 else -15.0
            keys.append((f, quat_y(ang)))
        gltf, blob = self._glb([("DEF-forearm.R", keys)])
        probs = HG.motion_continuity_problems(
            gltf, blob, self.FPS, 157, 1080, HG.AIM_SWEEP_MAX)
        self.assertEqual(probs, [])

    def test_fx_nodes_excluded(self):
        """FX.* rotation snaps ride scale-0 frames (invisible; gate 19
        owns FX visibility) -- the continuity gate must NOT fire on
        them (the take-6 MuzzleSmoke 90-deg onsets)."""
        nodes, _anims = gunner_fixture(0.0)
        fx_node = {"name": "FX.MuzzleSmoke.0", "parent": 13}
        nodes.append(fx_node)
        fxi = len(nodes) - 1
        qa = quat_y(0.0)
        qb = quat_y(90.0)
        anims = [{
            "name": "FX.Action",
            "channels": [(fxi, "rotation",
                          [f / self.FPS for f in (350, 351, 352)],
                          [qa, qb, qa])],
        }]
        gltf, blob = rebuild_glb(nodes, anims)
        probs = HG.motion_continuity_problems(
            gltf, blob, self.FPS, 157, 1080, HG.AIM_SWEEP_MAX)
        self.assertEqual(probs, [])

    def test_rifle_flip_fires_sprint_law(self):
        """Gunner.Rifle flipping 154.5 deg at f153 (the measured take-6
        storm co-victim) fires the sprint-window law."""
        q0 = quat_y(10.0)
        q1 = quat_y(164.5)
        gltf, blob = self._glb([
            ("Gunner.Rifle", [(150, q0), (153, q0), (154, q1), (160, q1)])
        ])
        probs = HG.motion_continuity_problems(
            gltf, blob, self.FPS, 1, 156, HG.SPRINT_SWEEP_MAX)
        self.assertEqual(len(probs), 1, probs)
        self.assertIn("Gunner.Rifle", probs[0])

    def test_no_rig_skips(self):
        """No Gunner.Rig in the package (v3 lineage / capsule-only
        scenes): the gate is not applicable."""
        gltf, blob = rebuild_glb([{"name": "Zed.0001"}], [])
        probs = HG.motion_continuity_problems(
            gltf, blob, self.FPS, 1, 1080, 40.0)
        self.assertEqual(probs, [])

    def test_sparse_keys_outside_gap_tolerance_skipped(self):
        """Keys farther than 1.5 frames apart (e.g. a 2-key static
        hold spanning the window) are not per-frame steps."""
        gltf, blob = self._glb([
            ("DEF-hand.R", [(100, quat_y(0.0)), (500, quat_y(179.0))])
        ])
        probs = HG.motion_continuity_problems(
            gltf, blob, self.FPS, 1, 1080, HG.AIM_SWEEP_MAX)
        self.assertEqual(probs, [])


class TestGate21CapsuleOrientation(unittest.TestCase):
    """s31 pins: the crowd capsule orientation class (the S11 f819
    flag). Fixtures are pure-glTF capsule anchors: a translation track
    (belt-local motion) + a rotation track, all in glTF space."""

    FPS = 24.0

    def _glb(self, nodes, channels):
        blob = Blob()
        gltf_nodes = []
        for i, nd in enumerate(nodes):
            g = {"name": nd["name"]}
            kids = [j for j, n2 in enumerate(nodes)
                    if n2.get("parent") == i]
            if kids:
                g["children"] = kids
            gltf_nodes.append(g)
        samplers, chans = [], []
        for ci, (ni, path, times, vals) in enumerate(channels):
            comps = 4 if path == "rotation" else 3
            inp = blob.accessor(list(times), 1, "SCALAR")
            outp = blob.accessor([c for v in vals for c in v], comps,
                                 "VEC4" if comps == 4 else "VEC3")
            samplers.append({"input": inp, "output": outp,
                             "interpolation": "LINEAR"})
            chans.append({"sampler": ci, "target": {"node": ni,
                                                   "path": path}})
        gltf = {"nodes": gltf_nodes,
                "animations": [{"name": "A", "channels": chans,
                                "samplers": samplers}],
                "accessors": blob.accessors, "bufferViews": blob.views,
                "buffers": [{"byteLength": len(blob.buf)}]}
        return gltf, bytes(blob.buf)

    def test_backward_capsule_fires(self):
        """A standing capsule moving +X belt-locally while its mesh
        forward (local -Z) points -X (180 deg off -- the take-6
        systematic class, agent-median 100+) must fire. (A 90-deg
        sideways case is BELOW the calibrated median threshold -- the
        sim's jostle band -- and must NOT fire: see
        test_sideways_jostle_below_threshold.)"""
        import math as _m
        r = _m.radians(90.0) / 2.0      # -Z -> -X needs a +90 Y-rot
        qy = (0.0, _m.sin(r), 0.0, _m.cos(r))
        nodes = [{"name": "Zed.0038"},
                 {"name": "JeepRoot"}]
        frames = [f / self.FPS for f in range(1, 1080, 2)]
        locs = [(0.05 * k, 0.0, 0.0) for k in range(len(frames))]
        rots = [qy] * len(frames)
        gltf, blob = self._glb(
            nodes, [(0, "translation", frames, locs),
                    (0, "rotation", frames, rots)])
        probs = HG.capsule_orientation_problems(
            gltf, blob, self.FPS, 1080)
        self.assertEqual(len(probs), 1, probs)
        self.assertIn("Zed.0038", probs[0])
        self.assertIn("180.0", probs[0])

    def test_sideways_jostle_below_threshold(self):
        """A sustained 90-deg-sideways capsule (the sim's by-design
        jostle band, median < 100) must NOT fire the calibrated
        gate."""
        nodes = [{"name": "Zed.0038"},
                 {"name": "JeepRoot"}]
        frames = [f / self.FPS for f in range(1, 1080, 2)]
        locs = [(0.05 * k, 0.0, 0.0) for k in range(len(frames))]
        rots = [(0.0, 0.0, 0.0, 1.0)] * len(frames)  # -Z stays -Z
        gltf, blob = self._glb(
            nodes, [(0, "translation", frames, locs),
                    (0, "rotation", frames, rots)])
        probs = HG.capsule_orientation_problems(
            gltf, blob, self.FPS, 1080)
        self.assertEqual(probs, [])

    def test_forward_capsule_passes(self):
        """Same motion, mesh forward ON the velocity: the local -Z
        rotated to point +X (a -90-deg Y rotation) passes."""
        import math as _m
        r = _m.radians(-90.0) / 2.0
        qy = (0.0, _m.sin(r), 0.0, _m.cos(r))
        nodes = [{"name": "Zed.0001"}, {"name": "JeepRoot"}]
        frames = [f / self.FPS for f in range(1, 40, 2)]
        locs = [(0.05 * k, 0.0, 0.0) for k in range(len(frames))]
        rots = [qy] * len(frames)
        gltf, blob = self._glb(
            nodes, [(0, "translation", frames, locs),
                    (0, "rotation", frames, rots)])
        probs = HG.capsule_orientation_problems(
            gltf, blob, self.FPS, 40)
        self.assertEqual(probs, [])

    def test_lying_corpse_exempt(self):
        """A capsule pitched 80 deg (lying) moving belt-locally with
        its forward sideways: exempt (a ragdoll's facing is
        legitimately arbitrary)."""
        import math as _m
        r = _m.radians(80.0) / 2.0
        qx = (_m.sin(r), 0.0, 0.0, _m.cos(r))
        nodes = [{"name": "Zed.0002"}, {"name": "JeepRoot"}]
        frames = [f / self.FPS for f in range(1, 40, 2)]
        locs = [(0.05 * k, 0.0, 0.0) for k in range(len(frames))]
        rots = [qx] * len(frames)
        gltf, blob = self._glb(
            nodes, [(0, "translation", frames, locs),
                    (0, "rotation", frames, rots)])
        probs = HG.capsule_orientation_problems(
            gltf, blob, self.FPS, 40)
        self.assertEqual(probs, [])

    def test_slow_mover_exempt(self):
        """Below CAPS_SPEED_MIN the heading is ill-defined: exempt."""
        nodes = [{"name": "Zed.0003"}, {"name": "JeepRoot"}]
        frames = [f / self.FPS for f in range(1, 40, 2)]
        locs = [(0.001 * k, 0.0, 0.0) for k in range(len(frames))]
        rots = [(0.0, 0.0, 0.0, 1.0)] * len(frames)
        gltf, blob = self._glb(
            nodes, [(0, "translation", frames, locs),
                    (0, "rotation", frames, rots)])
        probs = HG.capsule_orientation_problems(
            gltf, blob, self.FPS, 40)
        self.assertEqual(probs, [])

    def test_non_crowd_names_ignored(self):
        """Hero/twin/FX names don't match the capsule pattern."""
        nodes = [{"name": "Gunner.Root"},
                 {"name": "Zed.0038.RigWrap"},
                 {"name": "FX.Dust.0"}]
        gltf, blob = self._glb(nodes, [])
        probs = HG.capsule_orientation_problems(
            gltf, blob, self.FPS, 40)
        self.assertEqual(probs, [])

    def test_chase_anchor_audited(self):
        """Zed.ChaseNN anchors are crowd capsules too (the 180-deg
        backward shape fires for them the same as Zed.NNNN)."""
        import math as _m
        r = _m.radians(90.0) / 2.0
        qy = (0.0, _m.sin(r), 0.0, _m.cos(r))
        nodes = [{"name": "Zed.Chase01"}, {"name": "JeepRoot"}]
        frames = [f / self.FPS for f in range(1, 1080, 2)]
        locs = [(0.05 * k, 0.0, 0.0) for k in range(len(frames))]
        rots = [qy] * len(frames)
        gltf, blob = self._glb(
            nodes, [(0, "translation", frames, locs),
                    (0, "rotation", frames, rots)])
        probs = HG.capsule_orientation_problems(
            gltf, blob, self.FPS, 1080)
        self.assertEqual(len(probs), 1, probs)
        self.assertIn("Zed.Chase01", probs[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
