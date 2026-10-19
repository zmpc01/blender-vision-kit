"""test_crowd_look.py — the crowd-nav vision lane battery (s24).

Rows (design D8 + the critique's front-loaded risk order):
  L1  input contracts: --decls N1 schema happy path; IR {"min","max"}
      shape REFUSED (teacher message); malformed pinned keys refused;
      --rects bridge-verbatim (lists, not tuples).
  L2  geometry: gap WARNs carry coordinates; the F5/N6 overlap class
      (spawn ∩ / capacity ∩ / dest.point-in-rect); the N3 grid-BFS —
      a strangle pair severs (ONE P1 row), WallHug stays WARN, gap ==
      floor stays connected, <4-cell components discarded.
  L3  cache decode probe [F9]: agent_count arm (3-comp), slot-derived
      arm (2-comp), ambiguous REFUSED; the N4 ghost rule; F19 final
      tick = the cache tick grid.
  L4  trajectory_telemetry [F8/F18]: planted numpy cache (one reaches,
      one penetrates, one parks, one ghost); penetration max matches
      the planted depth; the F11 invariant reach_capacity ≤ reach_ever.
  L5  density [F7/N6]: tick-0 + ghost exclusion, decl masking, bin
      anchor, jam centroid at the planted jam; healthy control (no
      planted jam → no saturated zone outside decls).
  L6  ortho-cam probe (Blender): a planted rect renders INTACT from the
      high ortho cam with clip_start 0.01 (the 5.2 near-plane law) —
      measured colored pixels, not object existence.
  L7  navmap overlay (Blender): per-kind outlines visible; KIT_ANNOT_
      crowd residue ZERO after the purge; label cap honored.
  L8  trajectory + density passes (Blender): beveled curves render
      visible pixels along a planted path; the Pillow density
      composite is non-empty.
  L9  CLI routing: verdict_class + exit table (0 PASS / 2 REFUSED /
      3 AUTHORING_P1) with --json written on every exit class [N5].
  L10 GATED real-cache row: a REAL bake through the vendored wheel —
      telemetry invariant holds on engine bytes (loud skip w/o wheel).

Run: ./scripts/blrun.sh --background --python tests/test_crowd_look.py --
Exit: 0 PASS / 1 FAIL (rows score on check-level failures — the s23
vacuous-score law; n0 = len(FAIL) delta per row).
"""
import json
import math
import os
import sys
import tempfile
import traceback

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, ".."))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import crowd_look as cl   # noqa: E402

FAIL = []
ROWS = {}
ROW_EXTRAS = {}

_IN_BLENDER = False
try:
    import bpy  # noqa: F401
    _IN_BLENDER = True
except Exception:
    pass


def check(tag, got, want):
    """check()-raises pattern (the s23 law): a failed check MUST fail
    its row — row() scores the FAIL-delta, never exceptions alone."""
    if got != want:
        FAIL.append(f"{tag}: got {got!r} want {want!r}")
        raise AssertionError(f"{tag}: got {got!r} want {want!r}")


def row(rid, fn):
    n0 = len(FAIL)
    try:
        fn()
        if ROWS.get(rid) == "skip":
            return                      # the row claimed its own honest-skip
        ROWS[rid] = "pass" if len(FAIL) == n0 else "fail"
    except Exception as e:  # noqa: BLE001
        if ROWS.get(rid) == "skip":
            return
        if len(FAIL) == n0:
            FAIL.append(f"{rid}: UNEXPECTED {type(e).__name__}: {e}")
        ROWS[rid] = "fail"
        if os.environ.get("KIT_TRACEBACK"):
            traceback.print_exc()


# --------------------------------------------------------------------------- #
#  Shared fixtures (planted truth — the fixtures SELF-VERIFY in-row)
# --------------------------------------------------------------------------- #

def _write(tmp, name, payload):
    p = os.path.join(tmp, name)
    with open(p, "w") as f:
        json.dump(payload, f)
    return p


def _decls():
    return {
        "walkables": [{"id": "floor", "bounds": [[-8.0, -8.0], [8.0, 8.0]]}],
        "destinations": [{"id": "far_side", "walkable_id": "floor",
                          "point": [7.5, 0.0],
                          "capacity_bounds": [[7.0, -0.5], [8.0, 0.5]]}],
        "spawn_sources": [{"id": "sp", "walkable_id": "floor",
                           "bounds": [[-7.5, -1.0], [-6.5, 1.0]]}],
        "populations": [{"id": "p", "radius_m": [0.2, 0.38]}],
    }


def _kiosk():
    return {"id": "obst_kiosk", "walkable_id": "floor",
            "bounds": [[1.4, -0.6], [2.6, 0.6]]}


def _planted_cache(ticks=40, agents=4):
    """Planted truth (numpy only — no wheel):
    agent 0 walks -7 → 7.6 along y=0 (REACHES the destination);
    agent 1 parks at (2.05, 0) from t≥5 (PENETRATES the kiosk core);
    agent 2 wanders near the spawn (never reaches);
    agent 3 is the GHOST (exact (0,0) for all but the last tick)."""
    import numpy as np
    pos = np.zeros((ticks, agents, 2), dtype=np.float32)
    xs = np.linspace(-7.0, 7.6, ticks, dtype=np.float32)
    pos[:, 0, 0] = xs
    pos[:, 0, 1] = np.float32(0.0)
    pos[:, 1, 0] = np.float32(2.05)
    pos[:, 1, 1] = np.float32(0.0)
    pos[:5, 1, :] = np.linspace(-6.9, 2.05, 5, dtype=np.float32)[:, None]
    pos[:, 2, 0] = np.linspace(-6.5, -5.5, ticks, dtype=np.float32)
    pos[:, 2, 1] = np.float32(0.5)
    # the LAST slot is the ghost: exact (0,0) until the final tick
    pos[:-1, agents - 1, :] = np.float32(0.0)
    pos[-1, agents - 1, :] = np.float32((-5.0, 5.0))
    return pos


# --------------------------------------------------------------------------- #
#  L1 — input contracts
# --------------------------------------------------------------------------- #

def l1():
    tmp = tempfile.mkdtemp(prefix="crowdlook_l1_")
    dp = _write(tmp, "decls.json", _decls())
    decls = cl.load_decls(dp)
    check("L1 walkable parsed", len(decls["walkables"]), 1)
    check("L1 dest point tuple", isinstance(decls["destinations"][0]["point"], tuple), True)
    floors = cl.corridor_floors(decls)
    check("L1 floor from radius_m", abs(floors[0][0] - 1.0) < 1e-9, True)
    check("L1 floor provenance mentions population",
          "population 'p'" in floors[0][1], True)
    # IR emission shape refused BY NAME with the conversion
    try:
        cl._pair_of_pairs({"min": [0, 0], "max": [1, 1]}, "x")
        check("L1 IR shape refused", "no-exception", "CrowdLookRefused")
    except cl.CrowdLookRefused as e:
        check("L1 IR refusal names the conversion", "b['min'][0]" in str(e), True)
    # malformed pinned keys refused
    bad = _decls()
    bad["walkables"][0]["bounds"] = [[0, 0], [0, 0]]  # degenerate
    bp = _write(tmp, "bad.json", bad)
    try:
        cl.load_decls(bp)
        check("L1 degenerate bounds refused", "no-exception", "CrowdLookRefused")
    except cl.CrowdLookRefused:
        pass
    # unknown keys ignored (shared-with-authoring law)
    extra = _decls()
    extra["meta"] = {"anything": 1}
    extra["walkables"][0]["note"] = "hello"
    ep = _write(tmp, "extra.json", extra)
    check("L1 unknown keys ignored", len(cl.load_decls(ep)["walkables"]), 1)
    # rects verbatim: lists in, lists preserved (no tuple assertion)
    rp = _write(tmp, "rects.json", {"blocked": [_kiosk()], "report": []})
    rects = cl.load_rects(rp)
    check("L1 rects blocked count", len(rects["blocked"]), 1)
    check("L1 report passthrough", rects["report"], [])
    # missing file refused
    try:
        cl.load_rects(os.path.join(tmp, "nope.json"))
        check("L1 missing rects refused", "no-exception", "CrowdLookRefused")
    except cl.CrowdLookRefused:
        pass


# --------------------------------------------------------------------------- #
#  L2 — geometry: gaps, overlaps, severance (the N3 grid-BFS)
# --------------------------------------------------------------------------- #

def l2():
    decls = _decls()
    kiosk = _kiosk()
    # healthy layout: kiosk mid-floor, nothing within 1.0 m of anything
    check("L2 healthy gaps", cl.gap_findings([kiosk], decls, 1.0), [])
    check("L2 healthy overlap", cl.overlap_findings([kiosk], decls), [])
    p1, info = cl.severance_and_reachability([kiosk], decls,
                                             cl.corridor_floors(decls))
    check("L2 healthy severance", p1, [])
    check("L2 healthy components", info[("floor", 1.0)]["components"], 1)
    # gap WARN carries coordinates (two rects 0.5 m apart on x)
    a = {"id": "a", "walkable_id": "floor", "bounds": [[0.0, -0.5], [1.0, 0.5]]}
    b = {"id": "b", "walkable_id": "floor", "bounds": [[1.5, -0.5], [2.5, 0.5]]}
    warns = cl.gap_findings([a, b], decls, 1.0)
    check("L2 rect-rect gap WARN", len(warns), 1)
    check("L2 WARN class", warns[0]["class"], "WARN")
    check("L2 WARN has coordinates", "at" in warns[0] and
          len(warns[0]["at"]) == 2, True)
    # adjacent seam (gap == 0) is a WARN, never a P1
    c = {"id": "c", "walkable_id": "floor", "bounds": [[1.0, -0.5], [2.0, 0.5]]}
    seam = cl.gap_findings([a, c], decls, 1.0)
    check("L2 seam WARN type", seam[0]["type"], "adjacent-seam")
    # WallHug: flush to the walkable boundary stays WARN
    hug = {"id": "hug", "walkable_id": "floor", "bounds": [[7.9, -0.4], [8.0, 0.4]]}
    hw = [w for w in cl.gap_findings([hug], decls, 1.0)
          if w["type"] == "wallhug"]
    check("L2 wallhug is WARN", (len(hw), hw[0]["class"]), (1, "WARN"))
    # gap == floor stays passable (STRICT < f/2 wall test)
    g = {"id": "g", "walkable_id": "floor", "bounds": [[0.0, -0.5], [1.0, 0.5]]}
    h = {"id": "h", "walkable_id": "floor", "bounds": [[2.0, -0.5], [3.0, 0.5]]}
    p1g, ig = cl.severance_and_reachability([g, h], decls,
                                            [(1.0, "exact-gap")])
    check("L2 gap==floor connected", ig[("floor", 1.0)]["components"], 1)
    check("L2 gap==floor no P1", p1g, [])
    # THE STRANGLE PAIR: two walls 0.7 m apart across the corridor
    wa = {"id": "wa", "walkable_id": "floor",
          "bounds": [[4.0, -8.0], [4.6, -0.35]]}
    wb = {"id": "wb", "walkable_id": "floor",
          "bounds": [[4.0, 0.35], [4.6, 8.0]]}
    p1s, is_ = cl.severance_and_reachability([kiosk, wa, wb], decls,
                                             [(1.0, "strangle")])
    sev = [r for r in p1s if r["type"] == "walkable-severed"]
    check("L2 strangle severs", len(sev), 1)          # ONE row, not N
    check("L2 strangle components", sev[0]["components"], 2)
    check("L2 strangle frontier names rects",
          len(sev[0]["frontier_rects"]) >= 1, True)
    # the WARN rows still fire for the sub-floor gap between the walls
    gw = cl.gap_findings([kiosk, wa, wb], decls, 1.0)
    check("L2 strangle gap WARNs exist", len(gw) >= 1, True)
    check("L2 strangle gap WARNs are WARN",
          all(r["class"] == "WARN" for r in gw), True)
    # tiny isolated wall chunk (<4 cells) is rasterization noise
    tiny = {"id": "tiny", "walkable_id": "floor",
            "bounds": [[6.0, 6.0], [6.12, 6.12]]}
    p1t, it_ = cl.severance_and_reachability([tiny], decls, [(1.0, "tiny")])
    check("L2 tiny chunk no severance", p1t, [])


def l2b():
    # the overlap class, all three arms (F5/N6)
    decls = _decls()
    on_spawn = {"id": "os", "walkable_id": "floor",
                "bounds": [[-7.4, -0.8], [-6.6, 0.8]]}
    rows = cl.overlap_findings([on_spawn], decls)
    check("L2b exit-covered", [r["type"] for r in rows], ["exit-covered"])
    check("L2b both ids present", rows[0]["blocked"], "os")
    on_cap = {"id": "oc", "walkable_id": "floor",
              "bounds": [[6.8, -0.4], [7.4, 0.4]]}
    rows = cl.overlap_findings([on_cap], decls)
    check("L2b declared-unreachable (capacity)",
          [r["type"] for r in rows], ["declared-unreachable"])
    point_only = {"id": "op", "walkable_id": "floor",
                  "bounds": [[7.9, -0.4], [8.0, 0.4]]}  # ∩ capacity, ∌ point
    rows = cl.overlap_findings([point_only], decls)
    check("L2b capacity-overlap still fires",
          [r["type"] for r in rows], ["declared-unreachable"])
    # isolate the N6 POINT arm: capacity that does NOT contain the point
    # (legal-but-odd authoring) — a rect covering the point while missing
    # the capacity box must STILL fire
    decls2 = _decls()
    decls2["destinations"][0]["capacity_bounds"] = [[6.0, -0.5], [6.8, 0.5]]
    point_hit = {"id": "oh", "walkable_id": "floor",
                 "bounds": [[7.45, -0.2], [7.55, 0.2]]}  # contains (7.5,0)
    rows = cl.overlap_findings([point_hit], decls2)
    check("L2b dest.point-in-rect fires (N6)",
          [r["type"] for r in rows], ["declared-unreachable"])


# --------------------------------------------------------------------------- #
#  L3 — cache decode probe + ghost rule
# --------------------------------------------------------------------------- #

def l3():
    import numpy as np
    pos = _planted_cache()
    ticks, agents = pos.shape[0], pos.shape[1]
    # arm 1: agent_count present, 3-component chunk (the pinned wheel)
    raw3 = np.concatenate([pos, np.zeros((ticks, agents, 1), np.float32)],
                          axis=2).tobytes()
    p3, meta3 = cl.decode_positions({"position": raw3, "tick_count": ticks,
                                     "agent_count": agents})
    check("L3 agent_count arm source", meta3["source"], "agent_count")
    check("L3 agent_count arm comps", meta3["components"], 3)
    check("L3 agent_count arm XY", abs(float(p3[-1, 0, 0]) - 7.6) < 1e-5, True)
    # arm 2: no agent_count, 2-component chunk (the O11 shape)
    raw2 = pos.tobytes()
    p2, meta2 = cl.decode_positions({"position": raw2, "tick_count": ticks})
    check("L2 slot arm source", meta2["source"], "slot-derived")
    check("L3 slot arm shape", p2.shape, (ticks, agents, 2))
    # ambiguous chunks refused (teacher message)
    for bad in ({"position": raw2[:-2], "tick_count": ticks},
                {"position": raw3, "tick_count": ticks,
                 "agent_count": agents + 1}):
        try:
            cl.decode_positions(bad)
            check("L3 ambiguous refused", "no-exception", "CrowdLookRefused")
        except cl.CrowdLookRefused:
            pass
    # the N4 ghost rule: agent 3 is a ghost except the final tick
    vm = cl.ghost_mask(pos)
    check("L3 ghost at t0", bool(vm[0, 3]), False)
    check("L3 ghost at t-2", bool(vm[-2, 3]), False)
    check("L3 alive at final tick", bool(vm[-1, 3]), True)
    check("L3 real agents always valid", bool(vm[:, 0].all()), True)


# --------------------------------------------------------------------------- #
#  L4 — trajectory_telemetry (full-resolution, planted truth)
# --------------------------------------------------------------------------- #

def l4():
    import numpy as np
    decls = _decls()
    kiosk = _kiosk()
    pos = _planted_cache()
    tel = cl.trajectory_telemetry(pos, decls, [kiosk], 1.0)
    # planted: agent 0 ends INSIDE the capacity rect [[7,-.5],[8,.5]]
    check("L4 reach_capacity", tel["reach_capacity"], 1)
    check("L4 per_destination", tel["per_destination"], {"far_side": 1})
    # reach_ever: agent 0 passed within ±1.0 m of (7.5, 0) — the corridor
    # band also catches... only agent 0 (agent 2 parks at x≈-5.5)
    check("L4 reach_ever", tel["reach_ever"], 1)
    check("L4 invariant holds", tel["invariant_ok"], True)
    check("L4 invariant arithmetic", tel["reach_capacity"] <= tel["reach_ever"],
          True)
    # penetration: agent 1 parks at (2.05, 0) — depth 0.4 — BUT agent 0's
    # walk to the destination crosses the kiosk core along y=0 (the
    # no-routing walk-through class); the planted max is the WALKER's
    # deepest crossing, computed here from the fixture itself
    import numpy as np
    xs = np.linspace(-7.0, 7.6, pos.shape[0], dtype=np.float32)
    core = (1.4 + 0.15, 2.6 - 0.15)  # kiosk x-core at the bridge margin
    depth = [min(float(x) - core[0], core[1] - float(x))
             for x in xs if core[0] < float(x) < core[1]]
    want_pen = max(depth + [0.4])
    check("L4 max penetration (planted, self-computed)",
          abs(tel["max_penetration_m"] - want_pen) < 1e-3, True)
    check("L4 walker crosses deeper than the parker",
          want_pen > 0.4, True)
    # the ghost contributes to ghosts_frac but never to reach
    # (agent 3 is a ghost for ticks-1 of 40 ticks × 4 agents ≈ 0.24)
    check("L4 ghosts_frac", 0.2 < tel["ghosts_frac"] < 0.3, True)
    # median displacement (ghost agent 3 is INVALID at t0 → excluded):
    # agent 0 = 14.6, agent 1 = |(2.05,0)-(-6.9,-6.9)| ≈ 11.3, agent 2 = 1.0
    # → median ≈ 11.3
    check("L4 median displacement sane",
          10.5 < tel["median_displacement_m"] < 12.5, True)
    # F19: the final tick is the cache grid, not any scene frame count —
    # telemetry must respond to the ARRAY's tick count
    tel_short = cl.trajectory_telemetry(pos[:10], decls, [kiosk], 1.0)
    check("L4 final tick follows the array", tel_short["ticks"], 10)
    check("L4 short cache: agent0 not yet at capacity",
          tel_short["reach_capacity"], 0)


# --------------------------------------------------------------------------- #
#  L5 — density (masked occupancy)
# --------------------------------------------------------------------------- #

def l5():
    import numpy as np
    decls = _decls()
    kiosk = _kiosk()
    pos = _planted_cache(ticks=60)
    dens = cl.density_histogram(pos, decls, 1.0,
                                blocked_bounds=[kiosk["bounds"]])
    check("L5 denominator counts real samples", dens["denominator"] > 0, True)
    # the jam centroid lands at the kiosk (agent 1 parks INSIDE its core
    # for 56 ticks — the densest masked cell) or the agent-2 wander end —
    # NOT at the spawn/dest (masked) and NOT at (0,0) (ghost rule)
    check("L5 centroid exists", dens["jam_centroid"] is not None, True)
    cx, cy = dens["jam_centroid"]
    in_kiosk = (1.4 <= cx <= 2.6 and -0.6 <= cy <= 0.6)
    near_wander = (-6.6 <= cx <= -5.4 and 0.2 <= cy <= 0.8)
    check("L5 centroid at a real occupancy zone", in_kiosk or near_wander,
          True)
    check("L5 centroid not the origin marker", (cx, cy) != (0.0, 0.0), True)
    # healthy control: a cache with NO parking → no saturated zone far
    # from decls (peak stays modest, centroid near the spawn approach)
    import numpy as np
    healthy = np.zeros((30, 3, 2), dtype=np.float32)
    healthy[:, 0, 0] = np.linspace(-7, 7.6, 30, dtype=np.float32)
    healthy[:, 1, 0] = np.linspace(-6.5, 6.5, 30, dtype=np.float32)
    healthy[:, 1, 1] = np.float32(0.1)
    hd = cl.density_histogram(healthy, decls, 1.0,
                              blocked_bounds=[kiosk["bounds"]])
    check("L5 healthy peak modest", hd["peak_per_agent"] <= 1.0, True)


# --------------------------------------------------------------------------- #
#  Blender rows (skipped honestly when bpy is absent)
# --------------------------------------------------------------------------- #

def _mini_scene():
    """Floor plane 16x16 + a kiosk box aligned with _kiosk() — the base
    render shows geometry that matches the declaration."""
    import bpy
    bpy.ops.wm.read_homefile(use_empty=True)
    bpy.ops.mesh.primitive_plane_add(size=16, location=(0, 0, 0))
    floor = bpy.context.active_object
    floor.name = "Floor"
    bpy.ops.mesh.primitive_cube_add(size=1, location=(2.0, 0.0, 0.5))
    kiosk = bpy.context.active_object
    kiosk.name = "Kiosk"
    kiosk.scale = (1.2, 1.2, 1.0)
    return floor, kiosk


def l6():
    """L6 ortho-cam probe: the 5.2 near-plane law is LOAD-BEARING — a
    planted rect renders INTACT from the high ortho cam (clip_start
    0.01); measured colored pixels, not object existence."""
    if not _IN_BLENDER:
        print("ero] L6: SKIP (host mode — bpy absent)")
        ROWS["L6"] = "skip"
        return
    _mini_scene()
    cam = cl.build_ortho_cam((-8.0, -8.0, 8.0, 8.0))
    check("L6 cam is ORTHO", cam.data.type, 'ORTHO')
    check("L6 ortho_scale law", abs(cam.data.ortho_scale - 1.2 * 16.0) < 1e-6,
          True)
    check("L6 near plane above geometry",
          cam.location.z - cam.data.clip_start > 1.01, True)
    out = os.path.join(tempfile.mkdtemp(prefix="crowdlook_l6_"), "ortho.png")
    cl._render_topdown(cam, out)
    cam_name = cam.name                     # save BEFORE the purge (the
    # object reference dies with the datablock — the StructRNA law)
    from PIL import Image
    import numpy as np
    im = np.asarray(Image.open(out).convert("RGB"), dtype=np.int16)
    gray = ((np.abs(im[..., 0] - im[..., 1]) < 12) &
            (np.abs(im[..., 1] - im[..., 2]) < 12) & (im[..., 0] > 40))
    check("L6 floor renders intact (near-plane law)", int(gray.sum()) > 5000,
          True)
    # cleanup: the camera must purge under the KIT_ANNOT_ regime
    import annotate
    annotate.delete_annotation_layer({"objects": [cam], "labels": []})
    import bpy
    check("L6 cam purged", bpy.data.objects.get(cam_name), None)


def l7():
    """L7 navmap overlay: per-kind outlines visible; ZERO KIT_ANNOT_crowd
    residue after the purge; label cap honored [F16/F17]."""
    if not _IN_BLENDER:
        print("ero] L7: SKIP (host mode)")
        ROWS["L7"] = "skip"
        return
    import bpy
    import annotate
    _mini_scene()
    decls = _decls()
    rects = {"blocked": [dict(_kiosk())], "report": []}
    union = cl._union_bounds(rects, decls)
    cam = cl.build_ortho_cam(union)
    layer = cl.build_navmap_overlay(rects, decls)
    n_objs = len(layer["objects"])
    check("L7 overlay objects built", n_objs > 0, True)
    check("L7 label cap", len(layer["labels"]) <= 8, True)
    out = os.path.join(tempfile.mkdtemp(prefix="crowdlook_l7_"), "navmap.png")
    annotate.aim_labels_at(layer["labels"], cam.location, flat=True)
    cl._render_topdown(cam, out)
    counts = cl.overlay_visibility(out, ("walkable", "blocked", "dest",
                                         "spawn"))
    for kind in ("walkable", "blocked", "dest", "spawn"):
        check(f"L7 {kind} overlay visible", counts[kind] >= 40, True)
    # unit-level: the caller (main() in the module contract) purges
    # layer AND cam — mirror that duty here
    annotate.delete_annotation_layer(
        {"objects": layer["objects"] + [cam], "labels": layer["labels"]})
    residue = [n for n in bpy.data.objects.keys()
               if n.startswith(cl.CROWD_PREFIX)]
    check("L7 zero object residue", residue, [])
    residue_m = [n for n in bpy.data.materials.keys()
                 if n.startswith("KIT_ANNOT_mat_crowd")]
    check("L7 zero material residue", residue_m, [])
    residue_c = [n for n in list(bpy.data.curves.keys())
                 if n.startswith(cl.CROWD_PREFIX)]
    check("L7 zero curve residue", residue_c, [])


def l8():
    """L8 trajectory + density passes: beveled curves render VISIBLE
    pixels along a planted path (F12's measured-visibility law); the
    Pillow density composite is non-empty."""
    if not _IN_BLENDER:
        print("ero] L8: SKIP (host mode)")
        ROWS["L8"] = "skip"
        return
    import bpy
    import annotate
    import numpy as np
    _mini_scene()
    decls = _decls()
    rects = {"blocked": [dict(_kiosk())], "report": []}
    pos = _planted_cache(ticks=40, agents=4)  # ghost=last slot → 3 curves
    union = cl._union_bounds(rects, decls)
    cam = cl.build_ortho_cam(union)
    layer = cl.build_trajectory_overlay(pos, decls, cam=cam)
    check("L8 curves built (non-ghost agents)", len(layer["objects"]), 3)
    out = os.path.join(tempfile.mkdtemp(prefix="crowdlook_l8_"), "traj.png")
    cl._render_topdown(cam, out)
    counts = cl.overlay_visibility(out, ("traj",))
    check("L8 trajectory pixels visible", counts["traj"] >= 100, True)
    dens = cl.density_histogram(pos, decls, 1.0,
                                blocked_bounds=[r["bounds"] for r in
                                                rects["blocked"]])
    dpng = os.path.join(os.path.dirname(out), "density.png")
    cl.composite_density(out, dpng, dens, cam, (640, 480))
    from PIL import Image
    im = Image.open(dpng)
    check("L8 density composite non-empty", im.size, (640, 480))
    import numpy as np
    arr = np.asarray(im.convert("RGB"), dtype=np.int16)
    reds = ((arr[..., 0] > arr[..., 1] + 30) &
            (arr[..., 0] > arr[..., 2] + 30))
    # one saturated bin ≈ 8×8 px at 640/19.2 m — the planted kiosk jam
    # (eye-verified s24: the red blob sits exactly at the parked agent)
    check("L8 density shows red zones", int(reds.sum()) >= 20, True)
    annotate.delete_annotation_layer(
        {"objects": layer["objects"] + [cam], "labels": layer["labels"]})
    residue = [n for n in bpy.data.objects.keys()
               if n.startswith(cl.CROWD_PREFIX)]
    check("L8 zero residue", residue, [])


# --------------------------------------------------------------------------- #
#  L9 — CLI routing (in-process main(); --json on every exit [N5])
# --------------------------------------------------------------------------- #

def l9():
    tmp = tempfile.mkdtemp(prefix="crowdlook_l9_")
    dp = _write(tmp, "decls.json", _decls())
    rp = _write(tmp, "rects.json", {"blocked": [dict(_kiosk())], "report": []})
    jout = os.path.join(tmp, "v.json")
    if _IN_BLENDER:
        # F2: the CLI REQUIRES a scene source — save the mini scene and
        # pass --load-blend (the state-carrier law, exercised for real)
        _mini_scene()
        blend = os.path.join(tmp, "mini.blend")
        import bpy
        bpy.ops.wm.save_as_mainfile(filepath=blend)
        # navmap happy path: PASS (exit 0)
        rc = cl.main(["--navmap", "--rects", rp, "--decls", dp,
                      "--load-blend", blend,
                      "--out", os.path.join(tmp, "ok"),
                      "--json", jout])
        v = json.load(open(jout))
        check("L9 navmap verdict_class", v["verdict_class"], "PASS")
        check("L9 navmap exit", rc, 0)
        # overlap P1 → AUTHORING_P1 (exit 3)
        bad = dict(_kiosk())
        bad["id"] = "os"
        bad["bounds"] = [[-7.4, -0.8], [-6.6, 0.8]]
        rp2 = _write(tmp, "rects_bad.json", {"blocked": [bad], "report": []})
        rc = cl.main(["--navmap", "--rects", rp2, "--decls", dp,
                      "--load-blend", blend,
                      "--out", os.path.join(tmp, "p1"),
                      "--json", jout])
        v = json.load(open(jout))
        check("L9 authoring verdict_class", v["verdict_class"], "AUTHORING_P1")
        check("L9 authoring exit", rc, 3)
        check("L9 findings carry the overlap",
              any(f["type"] == "exit-covered" for f in v["findings"]), True)
        # THE MODULE RESIDUE CONTRACT: main() purges its own layers AND
        # cams — zero KIT_ANNOT_crowd residue after real invocations
        residue = [n for n in bpy.data.objects.keys()
                   if n.startswith(cl.CROWD_PREFIX)]
        check("L9 zero residue after main()", residue, [])
    else:
        print("ero] L9: SKIP (host mode — Blender rows need bpy)")
        ROWS["L9"] = "skip"
        return
    # refusal: --decls missing (exit 2, json STILL written [N5])
    rc = cl.main(["--navmap", "--out", os.path.join(tmp, "ref"),
                  "--json", jout])
    v = json.load(open(jout))
    check("L9 refusal verdict_class", v["verdict_class"], "REFUSED")
    check("L9 refusal exit", rc, 2)
    # refusal: IR-shape decls
    ir = {"walkables": [{"id": "w", "bounds": {"min": [0, 0], "max": [1, 1]}}]}
    irp = _write(tmp, "ir.json", ir)
    rc = cl.main(["--navmap", "--decls", irp,
                  "--out", os.path.join(tmp, "ref2"), "--json", jout])
    v = json.load(open(jout))
    check("L9 IR-shape verdict", v["verdict_class"], "REFUSED")
    check("L9 IR-shape exit", rc, 2)


# --------------------------------------------------------------------------- #
#  L10 — GATED real-cache row (the vendored wheel; loud skip w/o it)
# --------------------------------------------------------------------------- #

def l10():
    try:
        import blender_crowd_native as bcn  # noqa: F401
    except Exception:
        print("ero] L10: SKIP LOUD (native wheel absent — the gated row "
              "refuses to count as green coverage)")
        ROWS["L10"] = "skip"
        return
    if not _IN_BLENDER:
        ROWS["L10"] = "skip"
        return
    # a REAL mini bake through the bridge emission (the O11 scene shape)
    from crowd import (CrowdScene, CrowdProject, Population, SpawnSource,
                       Destination, Walkable, Blocked, bake)
    decls = _decls()
    kiosk = _kiosk()
    blocked = [Blocked(id=kiosk["id"], walkable_id="floor",
                       bounds=((kiosk["bounds"][0][0], kiosk["bounds"][0][1]),
                               (kiosk["bounds"][1][0], kiosk["bounds"][1][1])))]
    scene = CrowdScene(
        project=CrowdProject(seed=24, frame_end=120),
        populations=[Population(
            id="p", count=12,
            spawn_sources=[SpawnSource(id="sp", walkable_id="floor",
                                       bounds=((-7.5, -1.0), (-6.5, 1.0)))],
            destinations=[("far_side", 1.0)],
            archetypes=[("adult_a", 1.0)],
            appearances=[("blue", 1.0)])],
        walkables=[Walkable(id="floor", bounds=((-8.0, -8.0), (8.0, 8.0)))],
        blocked=blocked,
        destinations=[Destination(id="far_side", walkable_id="floor",
                                  point=(7.5, 0.0),
                                  capacity_bounds=((7.0, -0.5), (8.0, 0.5)))])
    import tempfile
    cache_dir = tempfile.mkdtemp(prefix="crowdlook_l10_")
    result = bake(scene, cache_dir=cache_dir)
    check("L10 bake complete", result.status, "complete")
    cache = bcn.Cache(result.cache_path)
    rng = cache.read_range(cache.tick_start, cache.tick_end)
    pos, meta = cl.decode_positions(rng)
    tel = cl.trajectory_telemetry(pos, decls,
                                  [{"id": kiosk["id"], "walkable_id": "floor",
                                    "bounds": ((kiosk["bounds"][0][0],
                                                kiosk["bounds"][0][1]),
                                               (kiosk["bounds"][1][0],
                                                kiosk["bounds"][1][1]))}],
                                  1.0)
    check("L10 invariant on ENGINE bytes", tel["invariant_ok"], True)
    # THE O11c CROSS-CHECK (the s41 engine-gap law, now through the
    # crowd_look pipeline): the kiosk sits ON the spawn→destination
    # beeline and the engine has NO routing — 0 reach is the EXPECTED
    # engine truth (O11 measured 0/20 on the same layout). crowd_look's
    # two derivations must AGREE with the O-battery's pins on the same
    # bytes: reach 0 + pressure-soft penetration > 0.
    check("L10 engine-gap jam reproduced (O11c agreement)",
          tel["reach_ever"], 0)
    # penetration is STOCHASTIC under jam pressure (seed-dependent — the
    # O11d precedent: REPORTED, never asserted); recorded in extras
    ROW_EXTRAS["L10_telemetry"] = {k: tel[k] for k in
                                   ("n_agents", "ticks", "reach_capacity",
                                    "reach_ever", "max_penetration_m",
                                    "ghosts_frac")}
    print(f"[crowd-look-test] L10 telemetry (REPORTED, not asserted): "
          f"{ROW_EXTRAS['L10_telemetry']}", flush=True)


def main() -> int:
    print("[crowd-look-test] battery start", flush=True)
    rows = (("L1", l1), ("L2", l2), ("L2b", l2b), ("L3", l3), ("L4", l4),
            ("L5", l5), ("L6", l6), ("L7", l7), ("L8", l8), ("L9", l9),
            ("L10", l10))
    for rid, fn in rows:
        row(rid, fn)
        print(f"[row] {rid}: {ROWS[rid]}", flush=True)
    n_pass = sum(1 for v in ROWS.values() if v == "pass")
    n_skip = sum(1 for v in ROWS.values() if v == "skip")
    n_fail = sum(1 for v in ROWS.values() if v == "fail")
    print(f"\n[crowd-look-test] battery: {n_pass} pass / {n_skip} skip / "
          f"{n_fail} fail", flush=True)
    if FAIL:
        print(f"[crowd-look-test] FAILURES: {FAIL}", flush=True)
    if n_fail:
        return 1
    print("[crowd-look-test] ALL PASS (non-skip)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
