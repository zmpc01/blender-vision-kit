"""r6_apply_cuts.py — replay the R6 region cuts on the imported loft.

The R6 session cut 4 regions out of the welded shell `Cube` (the only
way to break apart the fused level geometry — the loft ships as one
wrapped mesh). The cut parameters live in handoff/r6_patch_cuts.json
(reconstructed from docs/USABILITY_R6.md, session-14). This runner is
the committed, self-verifying replay primitive the R6 session lacked:
per cut it DRY-RUNS the region, asserts the captured face count against
the recorded expectation, then splits (and optionally deletes the
product). STOP-AND-FLAG (exit 4) on any mismatch — a drifted count
means the region boxes or the source state moved, and blind continuation
would poison the whole label chain downstream.

Run:
  ./run.sh --background --python scripts/r6_apply_cuts.py
  ./run.sh --background --python scripts/r6_apply_cuts.py -- --dry-run-only

Exit codes: 0 ok, 4 STOP-AND-FLAG, 1 operational error.
"""
import bpy
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import semantic_lib as SL  # noqa: E402

AUTO = "auto"
AUTO_MARGIN = 0.5


def die(msg):
    print("[STOP-AND-FLAG]", msg, flush=True)
    sys.exit(4)


def resolve_region(obj, region):
    """Materialize 'auto' axes from the source's world bbox (+margin)."""
    pts = [obj.matrix_world @ v for v in obj.bound_box]
    bb_min = [min(p[i] for p in pts) for i in range(3)]
    bb_max = [max(p[i] for p in pts) for i in range(3)]
    lo, hi = [], []
    for i in range(3):
        a, b = region["min"][i], region["max"][i]
        if a == AUTO:
            lo.append(bb_min[i] - AUTO_MARGIN)
        else:
            lo.append(float(a))
        if b == AUTO:
            hi.append(bb_max[i] + AUTO_MARGIN)
        else:
            hi.append(float(b))
    return {"min": lo, "max": hi}


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--blend", default=None,
                   help="override the cuts file's blend path")
    p.add_argument("--cuts",
                   default=os.path.join(_ROOT, "handoff",
                                        "r6_patch_cuts.json"))
    p.add_argument("--dry-run-only", action="store_true")
    a = p.parse_args(argv)

    spec = json.load(open(a.cuts))
    blend = a.blend or os.path.join(_ROOT, spec["blend"])
    if not os.path.exists(blend):
        sys.exit(f"[r6-cuts] blend missing: {blend}")
    bpy.ops.wm.open_mainfile(filepath=blend)

    report = []
    for cut in spec["cuts"]:
        name = cut["name"]
        obj = bpy.data.objects.get(cut["source"])
        if obj is None:
            die(f"cut {name}: source '{cut['source']}' not in scene")
        region = resolve_region(obj, cut["region"])
        dry = SL.analyze_region(obj, region)
        got = dry["faces_to_cut"]
        exp = cut["expect_faces"]
        print(f"[r6-cuts] {name}: dry-run faces={got} expected={exp} "
              f"captured={dry['captured_bbox']}", flush=True)
        if got != exp:
            die(f"cut {name}: dry-run captures {got} faces, the R6 record "
                f"says {exp} — the region boxes or the source state "
                f"drifted; NO mutation performed")
        row = {"cut": name, "faces": got, "captured": dry["captured_bbox"]}
        if a.dry_run_only:
            report.append(row)
            continue
        # cut product name law: split_region renames to new_id only if
        # free; the R6 record names are load-bearing downstream
        # (gen_r6_labels targets ceiling_slab/mezzanine_slab/stairs).
        taken = {o.name for o in bpy.context.scene.objects}
        if cut["new_id"] in taken:
            die(f"cut {name}: new_id '{cut['new_id']}' already exists in "
                f"the scene — refusing (silent .001 is a lie)")
        res = SL.split_region(obj, region, new_id=cut["new_id"],
                              ack_risks=True)
        if not res.get("ok"):
            die(f"cut {name}: split failed: {res}")
        if res["new_object"] != cut["new_id"]:
            die(f"cut {name}: expected product '{cut['new_id']}', got "
                f"'{res['new_object']}'")
        row["product"] = res["new_object"]
        row["product_bbox"] = res["new_object_bbox"]
        if cut.get("action") == "cut_and_delete":
            prod = bpy.data.objects[res["new_object"]]
            bpy.data.objects.remove(prod, do_unlink=True)
            row["deleted"] = True
        report.append(row)
        print(f"[r6-cuts] {name}: OK -> {res['new_object']}", flush=True)

    if a.dry_run_only:
        print("[r6-cuts] DRY-RUN-ONLY: all "
              f"{len(report)} regions verified, nothing mutated")
    else:
        bpy.ops.wm.save_as_mainfile(filepath=blend, compress=True)
        print(f"[r6-cuts] saved {blend}")
    print("[r6-cuts] REPORT " + json.dumps(report))


main()
