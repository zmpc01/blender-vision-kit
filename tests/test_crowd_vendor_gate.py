#!/usr/bin/env python3
"""test_crowd_vendor_gate.py — crowd vendor-back gate (r043, M9.5-9.6).

Verifies the vendored blender-crowd-kit integration end to end, in
fresh subprocesses (no sys.modules pollution of THIS process):

  PROBE 1 (vendor OK): `from scripts.crowd import <13 names>` works from
          the repo root; every kit class carries an alias-qualified
          __module__ (proves kit-canonical resolution — NOT this kit's
          stale top-level crowd_fields/gait_modifiers copies); the
          package exposes __crowd_kit_version__.
  PROBE 2 (fail-closed): with vendor/blender-crowd-kit temporarily
          renamed, importing scripts.crowd raises ImportError whose
          text contains the exact repair command.

Run: python3 tests/test_crowd_vendor_gate.py   (exit 0 = green)
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
VENDOR = os.path.join(ROOT, "vendor", "blender-crowd-kit")
VENDOR_BAK = VENDOR + ".gate-bak"

NAMES = [
    "CrowdScene", "bake", "BakeResult", "attach_to_scene",
    "detach_from_scene", "BehaviorGraph", "ForceField", "load_scenario",
    "list_scenarios", "cancel_bake",
    "CrowdProject", "Population", "apply_to_scene",
    # s41 authoring-surface extension (crowd_obstacles bridge)
    "Blocked", "Walkable", "Destination", "SpawnSource",
    "ForceFieldType", "FalloffProfile", "kit_to_bgyss_project_ir",
]

PROBE_OK = (
    "import sys; sys.path.insert(0, %r); "
    "from scripts.crowd import (%s, __crowd_kit_version__); "
    "import scripts.crowd as _sc; "
    "assert len(_sc.__all__) == 20, _sc.__all__; "
    "_names = [CrowdScene, CrowdProject, Population, ForceField, "
    "BehaviorGraph, BakeResult, Blocked, Walkable, Destination, "
    "SpawnSource, ForceFieldType, FalloffProfile, "
    "kit_to_bgyss_project_ir]; "
    "assert all(getattr(n, '__module__', '').startswith("
    "'_vendored_blender_crowd_kit.') for n in _names), "
    "[n.__module__ for n in _names]; "
    "print('VENDOR-PROBE-OK', __crowd_kit_version__)"
    % (ROOT, ", ".join(NAMES))
)

PROBE_FAIL_CLOSED = (
    "import sys; sys.path.insert(0, %r)\n"
    "try:\n"
    "    import scripts.crowd\n"
    "except ImportError as _e:\n"
    "    assert 'submodule update --init' in str(_e), str(_e)\n"
    "    print('FAIL-CLOSED-OK')\n"
    "else:\n"
    "    raise AssertionError('expected ImportError, import succeeded')"
    % (ROOT,)
)


def _run(code: str) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=120,
    )


def main() -> int:
    # Clean stale bytecode so the probes cannot read a cached stub.
    stub_pycache = os.path.join(ROOT, "scripts", "crowd", "__pycache__")
    if os.path.isdir(stub_pycache):
        shutil.rmtree(stub_pycache)

    failures = []

    r1 = _run(PROBE_OK)
    if r1.returncode == 0 and "VENDOR-PROBE-OK" in r1.stdout:
        print("[1/2] vendor probe: %s" % r1.stdout.strip())
    else:
        failures.append("vendor probe rc=%d\nstdout:%s\nstderr:%s"
                        % (r1.returncode, r1.stdout, r1.stderr))

    # Fail-closed probe: hide the submodule, prove the actionable error.
    renamed = False
    try:
        if os.path.isdir(VENDOR):
            os.rename(VENDOR, VENDOR_BAK)
            renamed = True
        r2 = _run(PROBE_FAIL_CLOSED)
        if r2.returncode == 0 and "FAIL-CLOSED-OK" in r2.stdout:
            print("[2/2] fail-closed probe: %s" % r2.stdout.strip())
        else:
            failures.append("fail-closed probe rc=%d\nstdout:%s\nstderr:%s"
                            % (r2.returncode, r2.stdout, r2.stderr))
    finally:
        if renamed and os.path.isdir(VENDOR_BAK):
            os.rename(VENDOR_BAK, VENDOR)

    if failures:
        print("test_crowd_vendor_gate: FAIL")
        for f in failures:
            print("-" * 60)
            print(f)
        return 1
    print("test_crowd_vendor_gate: ALL GREEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
