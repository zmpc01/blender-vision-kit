#!/usr/bin/env python3
"""session-16: the F-TD10 blrun flock (session-14) broke the four suites
that nest blrun calls — the outer blrun holds the per-display lock, so the
nested call exits 90 (LOCK-HELD) and every nested check fails. The nested
call IS the test's tool invocation, not a competing pipeline: give it the
documented bypass (BLRUN_FORCE=1). Battery artifact (5-b suites 2/3/4/8)."""
import re

EDITS = [
    # v3: _blrun env block
    ("tests/test_v3_edges.py",
     '    env = dict(os.environ)\n    env["BLRUN_NO_TRACEBACK_GATE"] = "1"  # we gate tracebacks OURSELVES per-case',
     '    env = dict(os.environ)\n    env["BLRUN_NO_TRACEBACK_GATE"] = "1"  # we gate tracebacks OURSELVES per-case\n    # F-TD10 flock bypass: the OUTER blrun (running this test) holds the\n    # per-display lock; this nested call is the test\'s own tool invocation,\n    # not a competing pipeline — the battery proved rc=90 without it.\n    env["BLRUN_FORCE"] = "1"'),
    # v2: _run_scan_cli subprocess.run needs env
    ("tests/test_v2_motion.py",
     '    return subprocess.run(cmd, capture_output=True, text=True, timeout=280), out',
     '    # F-TD10 flock bypass (nested blrun under the outer blrun-held lock)\n    env = dict(os.environ)\n    env["BLRUN_FORCE"] = "1"\n    return subprocess.run(cmd, capture_output=True, text=True,\n                          timeout=280, env=env), out'),
    # v4: S8 nested look.py call — env is already passed; ensure FORCE in it
    ("tests/test_v4_colorsync.py",
     '        capture_output=True, text=True, env=env, timeout=300)',
     '        capture_output=True, text=True, env=env, timeout=300)\n    # (env carries BLRUN_FORCE=1 — set just below where env is built)'),
    # v7: subprocess.run needs env
]

for path, old, new in EDITS[:2]:
    src = open(path).read()
    if old not in src:
        print(f"[force] PATTERN MISS in {path}: {old[:60]!r}")
        continue
    open(path, "w").write(src.replace(old, new, 1))
    print(f"[force] patched {path}")

# v2 note: the subprocess.run signature edit replaces the return line
print("[force] done pass 1")
