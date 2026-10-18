"""s22_crossval.py — the fixture-vs-real cross-validation probe.

The s20 fixture recipes were reverse-engineered OFFLINE (the data source
was dead). Now the real libraries are LIVE — every pinned fixture law
gets compared against what REAL platform files actually do:

  1. import REAL clips through rh_canvas.import_clip (the kit path):
     2846 (Run fast — the battery pin), 2899 (walk), 2781 (idle 500f)
  2. import the fixture run clip through the same path
  3. measure the truth dimensions on BOTH: bone census/prefix,
     obj.scale, obj rotation, world height (feet/top), fps, frame
     range, animated-bone census, hips fcurve raw unit, pose rotation
     modes
  4. print a diff table law | fixture | real | verdict + write
     output/tests/rh_crossval.json

Read-only probe (no scene mutation survives; factory start + purge).
"""
import bpy, os, sys, json, math

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))
import rh_canvas  # noqa: E402

OUT_DIR = os.environ.get("KIT_OUT", os.path.join(_REPO, "output", "tests"))
os.makedirs(OUT_DIR, exist_ok=True)
OUT = os.path.join(OUT_DIR, "rh_crossval.json")

REAL_IDS = ["2846", "2899", "2781"]     # run-fast / walk / idle
FIXTURE_RUN = "9002"                    # the fixture run clip id (快速奔跑)
FIXTURE_ROOT = "/home/z/rh_fixture_lib"


def P(*a):
    print("XVAL", *a, flush=True)


def purge():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)


def measure(tag, clip_id):
    """Import via the kit path, measure the truth dimensions."""
    purge()
    arm, _report = rh_canvas.import_clip(clip_id)
    act = arm.animation_data.action if arm.animation_data else None
    if act is None:
        raise RuntimeError(f"clip {clip_id} imported with no action")
    sc = bpy.context.scene
    prof = {
        "clip": clip_id,
        "bones": len(arm.data.bones),
        "prefix_mixamorig": sum(1 for b in arm.data.bones
                                if b.name.startswith("mixamorig:")),
        "obj_scale": tuple(round(v, 5) for v in arm.scale),
        "obj_rot_deg": tuple(round(math.degrees(a), 3) for a in arm.rotation_euler),
        "pose_rot_modes": sorted({b.rotation_mode for b in arm.pose.bones}),
        "action_range": [round(f, 2) for f in act.frame_range],
        "fps": sc.render.fps,
    }
    # animated-bone census (fcurves on the 5.x channelbag, kit iterator)
    try:
        fcs = list(blender_kit_iter(act))
    except Exception:
        fcs = []
    animated = set()
    for fc in fcs:
        if fc.data_path.startswith("pose.bones["):
            animated.add(fc.data_path.split('"')[1])
    prof["animated_bones"] = len(animated)
    # hips location fcurve RAW unit at first keyed point
    hips_raw = None
    for fc in fcs:
        if "Hips" in fc.data_path and fc.data_path.endswith(".location") \
                and fc.array_index == 2:
            kp = fc.keyframe_points[0]
            hips_raw = round(kp.co[1], 4)
            break
    prof["hips_z_firstkey_raw"] = hips_raw
    # world height via evaluated pose at frame 1
    sc.frame_set(1)
    bpy.context.view_layer.update()
    zs = []
    for pb in arm.pose.bones:
        w = arm.matrix_world @ pb.matrix
        zs.append(w.translation.z)
    prof["world_z_min"] = round(min(zs), 4)
    prof["world_z_max"] = round(max(zs), 4)
    P(tag, json.dumps(prof))
    return prof


def blender_kit_iter(act):
    """5.x slotted-action fcurve iteration (the kit's own law)."""
    import blender_kit
    if hasattr(blender_kit, "iter_fcurves"):
        return blender_kit.iter_fcurves(act)
    return act.fcurves


EXPECTED_DEVIATIONS = {
    # the s20 documented "unrecoverable offline" class — measured against
    # reality 2026-10-18 (docs/RH_CROSSVAL_s22.md): the Maya-era unit
    # baking (scale 0.01 + rot 90) and the absolute-cm curve convention
    # only exist in platform files; the fixture recipe compensates
    # behaviorally (world gates prove equivalence).
    "obj_scale",
    "obj_rot_deg",
    "hips_raw_firstkey",
}


def main():
    # honest-skip protocol: either library layer absent = exit 2 + sentinel
    # (zero coverage must NOT score PASS — the s20 battery law)
    libs = rh_canvas.discover_libraries()
    if not libs.get("animations"):
        print("[XVAL] SUITE-SKIP: real animations library absent "
              f"(found {libs}) — clone per docs/rh_canvas.md", flush=True)
        raise SystemExit(2)
    if not os.path.isfile(os.path.join(FIXTURE_ROOT, "truth.json")):
        print(f"[XVAL] SUITE-SKIP: fixture library absent at {FIXTURE_ROOT} "
              "— build it first (scripts/rh_fixture_lib.py)", flush=True)
        raise SystemExit(2)
    real = {}
    for cid in REAL_IDS:
        try:
            real[cid] = measure("REAL", cid)
        except Exception as e:                    # noqa: BLE001
            P("REAL", cid, "ERROR", repr(e))
            real[cid] = {"error": repr(e)}
    try:
        # pin discovery at the fixture lib (AUTHORITATIVE — the fixture ids
        # do not exist in the real catalog)
        os.environ["RH_CANVAS_LIB"] = FIXTURE_ROOT
        fix = measure("FIXTURE", FIXTURE_RUN)
    except Exception as e:                        # noqa: BLE001
        P("FIXTURE", FIXTURE_RUN, "ERROR", repr(e))
        fix = {"error": repr(e)}

    # ---- the diff table (laws, not clip identity) ----
    r0 = next((v for v in real.values() if "error" not in v), None)
    table = []
    if r0 and "error" not in fix:
        # world_z_max is CLIP pose data (each animation carries its own
        # top-of-figure height) — the family law is the human BAND, not
        # per-clip equality.
        band = (1.4 <= fix["world_z_max"] <= 2.1
                and 1.4 <= r0["world_z_max"] <= 2.1)
        rows = [
            ("bone_census_65", fix["bones"], r0["bones"]),
            ("mixamorig_prefix_all", fix["prefix_mixamorig"], r0["prefix_mixamorig"]),
            ("pose_mode", fix["pose_rot_modes"], r0["pose_rot_modes"]),
            ("fps", fix["fps"], r0["fps"]),
            ("obj_scale", fix["obj_scale"], r0["obj_scale"]),
            ("obj_rot_deg", fix["obj_rot_deg"], r0["obj_rot_deg"]),
            ("world_z_min_m", fix["world_z_min"], r0["world_z_min"]),
            ("world_z_max_human_band", band, True),
            ("hips_raw_firstkey", fix["hips_z_firstkey_raw"], r0["hips_z_firstkey_raw"]),
        ]
        for law, f, r in rows:
            match = (f == r) if not isinstance(f, float) else abs(f - r) <= 0.05
            verdict = "MATCH" if match else (
                "DEVIATION-EXPECTED" if law in EXPECTED_DEVIATIONS
                else "DEVIATION-UNEXPECTED")
            table.append({"law": law, "fixture": f, "real": r,
                          "match": bool(match), "verdict": verdict})
            P(f"LAW {law:22s} fixture={f} real={r} {verdict}")
    unexpected = [t for t in table
                  if t.get("verdict") == "DEVIATION-UNEXPECTED"]
    if not table:
        print("[XVAL] SUITE-FAIL: no law rows produced (one side errored) "
              "— zero coverage must not score PASS", flush=True)
        raise SystemExit(1)
    P(f"SUMMARY: {len(table)} laws, "
      f"{sum(1 for t in table if t['verdict'] == 'MATCH')} match, "
      f"{len([t for t in table if t.get('verdict') == 'DEVIATION-EXPECTED'])} "
      f"expected-deviation, {len(unexpected)} UNEXPECTED")
    doc = {"real": real, "fixture": fix, "laws": table}
    with open(OUT, "w") as f:
        json.dump(doc, f, indent=1)
    P("wrote", OUT)
    if unexpected:
        raise SystemExit(f"[XVAL] {len(unexpected)} UNEXPECTED law "
                         f"deviations — the fixture recipe drifted from "
                         f"the platform family")
    P("[XVAL] ALL MATCH (or expected-deviation) — fixture library "
      "remains a behavioral double of the platform family")
    P("XVAL-DONE")


main()
