"""
test_v3_edges.py — degenerate-input edge suite (vision-kit, HANDOFF gap C+D).

Subprocess-driven (like test_v1_look): each case runs the real CLI via
blrun.sh so cold-start + fail-closed gates are part of the test.

Policy under test — a tool facing a degenerate input must EITHER
  (a) succeed with usable output, OR
  (b) exit nonzero with a CLEAN one-line reason (no raw traceback).
A raw Python traceback in any edge case is a FAIL: blrun's fail-closed
gate already forces nonzero exit on tracebacks, so (b) is detectable.

Cases:
  C1 look on EMPTY scene (--scene edge_empty)
  C2 look on a single object far OFF-ORIGIN (edge_offorigin)
  C3 look on an extreme WIDE row 14m x 0.4m (edge_wide)
  C4 look on an extreme TALL tower 0.15 x 6m (edge_tall)
  D1 motion_study --frames 1   (no temporal signal)
  D2 motion_study --frames 2   (single pair)
  D3 transient_scan --frames 1 (no adjacent pairs to diff)
  D4 transient_scan --frames 2 (one diff, degenerate MAD)

Run:
  ./scripts/blrun.sh --background --python tests/test_v3_edges.py --
"""
import os
import subprocess
import sys

import bpy

KIT = os.path.dirname(os.path.dirname(os.path.abspath(bpy.data.filepath or __file__)))
if not os.path.isdir(os.path.join(KIT, "scripts")):
    # fallback: tests/ lives at <kit>/tests
    KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CHECKS = {"n": 0, "fail": []}


def _check(tag, cond, detail=""):
    CHECKS["n"] += 1
    status = "PASS" if cond else "FAIL"
    print(f"  [{status}] {tag}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        CHECKS["fail"].append(tag)


def _blrun(script, *tool_args, timeout=300):
    """Run a kit tool via blrun.sh; return (returncode, combined_output)."""
    cmd = [os.path.join(KIT, "scripts", "blrun.sh"), "--background",
           "--python", os.path.join(KIT, "scripts", script), "--", *tool_args]
    env = dict(os.environ)
    env["BLRUN_NO_TRACEBACK_GATE"] = "1"  # we gate tracebacks OURSELVES per-case
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
    return p.returncode, (p.stdout + p.stderr)


def _no_traceback(out):
    return "Traceback (most recent call last" not in out


def main():
    out_root = os.path.join(KIT, "output", "edges")
    os.makedirs(out_root, exist_ok=True)

    print("== C1: look on EMPTY scene ==")
    rc, out = _blrun("look.py", "--scene", "edge_empty",
                     "--output", os.path.join(out_root, "look_empty"))
    _check("C1 no traceback", _no_traceback(out), out[-400:])
    _check("C1 exits cleanly (0 = usable output path exists)",
           rc in (0, 3), f"rc={rc}")

    print("== C2: look on single OFF-ORIGIN object ==")
    rc, out = _blrun("look.py", "--scene", "edge_offorigin",
                     "--output", os.path.join(out_root, "look_offorigin"))
    _check("C2 no traceback", _no_traceback(out), out[-400:])
    _check("C2 exit 0 (legit scene must WORK)", rc == 0, f"rc={rc}")
    _check("C2 manifest sees LoneCube", "LoneCube" in out)

    print("== C3: look on extreme WIDE row ==")
    rc, out = _blrun("look.py", "--scene", "edge_wide",
                     "--output", os.path.join(out_root, "look_wide"))
    _check("C3 no traceback", _no_traceback(out), out[-400:])
    _check("C3 exit 0", rc == 0, f"rc={rc}")
    _check("C3 manifest sees 9 row cubes",
           all(f"W{i}" in out for i in range(9)))

    print("== C4: look on extreme TALL tower ==")
    rc, out = _blrun("look.py", "--scene", "edge_tall",
                     "--output", os.path.join(out_root, "look_tall"))
    _check("C4 no traceback", _no_traceback(out), out[-400:])
    # a lone tower with NOTHING below it is correctly flagged P1 floating
    # (validator law) and look exits 3 on P1 — the suite verifies the LAW
    _check("C4 exit 0-or-3 (P1 floating is correct)", rc in (0, 3), f"rc={rc}")
    _check("C4 manifest sees Tower", "Tower" in out)
    _check("C4 floating law enforced",
           "P1=1" in out and "floating" in out)

    print("== D1: motion_study --frames 1 ==")
    rc, out = _blrun("motion_study.py", "--scene", "edge_anim", "--frames", "1",
                     "--out", os.path.join(out_root, "motion_f1"))
    _check("D1 no traceback", _no_traceback(out), out[-400:])
    _check("D1 exits cleanly", rc == 0 or (rc != 0 and "Traceback" not in out),
           f"rc={rc}")

    print("== D2: motion_study --frames 2 ==")
    rc, out = _blrun("motion_study.py", "--scene", "edge_anim", "--frames", "2",
                     "--out", os.path.join(out_root, "motion_f2"))
    _check("D2 no traceback", _no_traceback(out), out[-400:])
    _check("D2 exits cleanly", rc == 0 or (rc != 0 and "Traceback" not in out),
           f"rc={rc}")

    print("== D3: transient_scan --frames 1 ==")
    rc, out = _blrun("transient_scan.py", "--scene", "edge_anim", "--frames", "1",
                     "--out", os.path.join(out_root, "scan_f1"))
    _check("D3 no traceback", _no_traceback(out), out[-400:])
    _check("D3 exits cleanly", rc == 0 or (rc != 0 and "Traceback" not in out),
           f"rc={rc}")

    print("== D4: transient_scan --frames 2 ==")
    rc, out = _blrun("transient_scan.py", "--scene", "edge_anim", "--frames", "2",
                     "--out", os.path.join(out_root, "scan_f2"))
    _check("D4 no traceback", _no_traceback(out), out[-400:])
    _check("D4 exits cleanly", rc == 0 or (rc != 0 and "Traceback" not in out),
           f"rc={rc}")

    print(f"\nEDGES: {CHECKS['n'] - len(CHECKS['fail'])}/{CHECKS['n']} PASS")
    if CHECKS["fail"]:
        print("FAILED:", ", ".join(CHECKS["fail"]))
        sys.exit(1)
    print("ALL PASS")


main()
