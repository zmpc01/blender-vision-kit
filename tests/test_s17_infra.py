#!/usr/bin/env python3
"""
test_s17_infra.py — session-17 Wave-D INFRA fix regressions.

PURE python — no Blender import (the infra layer must be testable without
the 5.2.2 toolchain). Run:  python3 tests/test_s17_infra.py
Convention: [test_s17i] per check; ALL PASS at the end; exit 1 on failure.

Covers (docs/audit_s17/2e_infra.md fix list, task 3-d):
  F2E-3  scripts/daemonize.py exists and double-fork-survives the launcher
         process: the launcher exits immediately, the orphaned grandchild
         (reparented to PID 1, NOT a descendant of anything this test waits
         on) still runs its command and lands stdout/stderr in the log.
  F2E-4  render_daemon.wipe_frame_window wipes ONLY the run's frame window
         (a --first-chunk resume must not delete completed chunks' frames).
  F2E-11 scripts/suite_runner.sh --list enumerates the whole battery
         (26+ suites, per-suite invocation args) and carries the loud
         reaping-law header.
  F2E-18 tools/chunked_dl.sh tolerates missing parts (early-exit chunks on
         files smaller than 16 chunks) and cleans a stale dl_errors.log —
         exercised END-TO-END via a local file:// URL (curl ranged reads),
         no network.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(REPO, "scripts")
RESULTS = []


def check(name, cond, detail=""):
    tag = "PASS" if cond else "FAIL"
    line = "[test_s17i] %s: %s" % (name, tag)
    if detail and not cond:
        line += " — %s" % detail
    print(line)
    RESULTS.append((name, bool(cond)))


# --------------------------------------------------------------------------
def test_daemonize():
    """F2E-3: launcher exits immediately; the daemon survives it."""
    log = "/tmp/_s17_dalive.log"
    marker = "/tmp/_s17_dalive"
    for p in (log, marker, log + ".tmp", marker + ".tmp"):
        try:
            os.remove(p)
        except OSError:
            pass
    launcher = [sys.executable, os.path.join(SCRIPTS, "daemonize.py"), log,
                "bash", "-c",
                "sleep 2 && touch /tmp/_s17_dalive"
                " && echo daemon-alive >> /tmp/_s17_dalive.log"]
    t0 = time.time()
    try:
        r = subprocess.run(launcher, capture_output=True, text=True, timeout=10)
        rc, err, took = r.returncode, r.stderr, time.time() - t0
    except subprocess.TimeoutExpired:
        rc, err, took = "TIMEOUT", "launcher did not exit within 10s", 10.0
    check("daemonize.launcher_exits_immediately", rc == 0,
          "rc=%r stderr=%r took=%.1fs" % (rc, err[:200], took))
    check("daemonize.log_precreated", os.path.exists(log),
          "log must be opened BEFORE the first fork (failures pre-fork are "
          "reported to the caller's stderr)")
    deadline = time.time() + 15
    while not os.path.exists(marker) and time.time() < deadline:
        time.sleep(0.2)
    check("daemonize.daemon_survived_launcher_exit", os.path.exists(marker),
          "marker /tmp/_s17_dalive never appeared — the double fork did not "
          "survive the launcher process")
    body = ""
    if os.path.exists(log):
        with open(log) as f:
            body = f.read()
    check("daemonize.stdout_stderr_to_log", "daemon-alive" in body,
          "log=%r (expected a 'daemon-alive' line: stdout must be redirected "
          "to the ABSOLUTE log, append)" % body[:200])
    for p in (marker,):
        try:
            os.remove(p)
        except OSError:
            pass


# --------------------------------------------------------------------------
def test_render_daemon_window_wipe():
    """F2E-4: only the run's frame window is wiped."""
    sys.path.insert(0, SCRIPTS)
    import render_daemon as rd  # stdlib-only module; no bpy

    d = tempfile.mkdtemp(prefix="_s17_wipe_")
    try:
        names = ["frame_%04d.png" % i for i in range(1, 11)] \
            + ["frame_0003.jpg", "daemon_chunk1.log", "metadata.json"]
        for n in names:
            with open(os.path.join(d, n), "w") as f:
                f.write("")
        # simulate a resume of chunks covering frames 6..12 (of a nominal
        # 1..12 range): frames 1-5 belong to ALREADY-COMPLETED chunks.
        removed = rd.wipe_frame_window(d, 6, 12)
        check("wipe.window_count", removed == 5,
              "removed=%d expected=5 (frame_0006..0010 png)" % removed)
        check("wipe.keeps_completed_chunks",
              os.path.exists(os.path.join(d, "frame_0001.png"))
              and os.path.exists(os.path.join(d, "frame_0005.png")),
              "a --first-chunk resume must NOT delete completed chunks' frames")
        check("wipe.removes_window",
              not os.path.exists(os.path.join(d, "frame_0006.png"))
              and not os.path.exists(os.path.join(d, "frame_0010.png")),
              "the run's own window must be wiped (stale-scratch fix 16-b P0-1)")
        check("wipe.respects_window_on_jpg",
              os.path.exists(os.path.join(d, "frame_0003.jpg")),
              "JPEG frames outside the window must survive too")
        check("wipe.leaves_nonframes",
              os.path.exists(os.path.join(d, "daemon_chunk1.log"))
              and os.path.exists(os.path.join(d, "metadata.json")),
              "non-frame files must be untouched")
        # full-run window still wipes everything stale (1..12 covers all)
        removed2 = rd.wipe_frame_window(d, 1, 12)
        check("wipe.full_run_window", removed2 == 6,
              "removed=%d expected=6 (10-5 png remaining + 0003 jpg)" % removed2)
    finally:
        shutil.rmtree(d, ignore_errors=True)


# --------------------------------------------------------------------------
def test_suite_runner_list():
    """F2E-11: --list enumerates the battery + reaping-law header."""
    r = subprocess.run(["bash", os.path.join(SCRIPTS, "suite_runner.sh"),
                        "--list"], capture_output=True, text=True,
                       timeout=60, cwd=REPO)
    out = r.stdout
    n = len(re.findall(r"^\s*\d+\.\s+\S+", out, re.M))
    check("suite_runner.list_rc", r.returncode == 0,
          "rc=%r stderr=%r" % (r.returncode, r.stderr[:200]))
    # F10 (s19 triage): the battery-count drift law. The count went stale
    # in three documents at once (SKILL.md said 29, the runner header
    # said 26+3, the real SUITES roster had 34 rows) while THIS floor
    # (>=26) stayed green through all of it — a floor cannot catch a
    # shrinking roster either. Pin the true count (>= 34 at the s19 tip;
    # the count may legitimately GROW when a wave lands a suite) plus one
    # representative name per family below. SKILL.md's battery line is
    # the orchestrator's to fix — this test pins the roster truth.
    check("suite_runner.list_enumerates_battery", n >= 34,
          "found %d suite entries, need >= 34 (the s19 SUITES roster; "
          "raise this pin in the same commit that lands a new suite — "
          "and never let it shrink)" % n)
    _families = (
        ("core", "test_kit_scope"),
        ("look-v1", "test_v1_look"),
        ("look-v9", "test_v9_fixes_s16"),
        ("placement-t2", "test_t2_stairs"),
        ("diorama-t8", "t8_placement_diorama"),
        ("chaos-t9", "t9_chaos_fuzz"),
        ("export-t10", "test_t10_export"),
        ("gridrefine-f17", "test_f17_gridrefine"),
        ("levels-f22", "test_f22_levels"),
        ("route-r7", "test_r7_route"),
        ("seat-r8", "test_r8_seat"),
        ("chunking-r9", "test_r9_chunking"),
        ("usd-carrier", "test_usd_carrier"),
        ("s17-wave-a", "test_s17_wave_a"),
        ("s17-wave-b", "test_s17_wave_b"),
        ("s17-infra", "test_s17_infra"),
        ("x1-detection", "x1_detection_matrix"),
        ("s18-eyes", "test_s18_eyes"),
        ("s18-wave-b", "test_s18_wave_b"),
        ("s18-wave-c", "test_s18_wave_c"),
        ("s18-wave-d", "test_s18_wave_d"),
    )
    _missing = [member for _, member in _families if member not in out]
    check("suite_runner.roster_family_representatives", not _missing,
          "missing from --list: %s (a family dropped off the roster?)"
          % _missing)
    check("suite_runner.reaping_law_header",
          "REAPING" in out.upper() and "foreground" in out.lower(),
          "--list must print the loud reaping-law header (SKILL.md §L181)")
    check("suite_runner.list_shows_invocation_args",
          "--background --python" in out and "-- --output output/s17/t8" in out
          and "-- out=output/s17/r9_chunking" in out,
          "--list must show per-suite invocation args (battery-doc rows)")


# --------------------------------------------------------------------------
def test_chunked_dl_missing_parts():
    """F2E-18: early-exit chunks never create their part — concat must
    tolerate that; stale dl_errors.log is cleaned at start. End-to-end via
    curl ranged reads on a local file:// URL (no network)."""
    tmp = tempfile.mkdtemp(prefix="_s17_dl_")
    try:
        fixture = os.path.join(tmp, "fixture.bin")
        payload = b"abcdefg"  # 7 bytes -> 16 requested chunks, 9 early-exit
        with open(fixture, "wb") as f:
            f.write(payload)
        out = os.path.join(tmp, "out.bin")
        stale = os.path.join(tmp, "dl_errors.log")
        with open(stale, "w") as f:
            f.write("CHUNK 99 FAILED (stale from a killed run)\n")
        r = subprocess.run(["bash", os.path.join(REPO, "tools", "chunked_dl.sh"),
                            "file://" + fixture, out, "7"],
                           capture_output=True, text=True, timeout=120)
        check("chunked_dl.small_file_rc", r.returncode == 0,
              "rc=%r stdout=%r stderr=%r" % (r.returncode,
                                             r.stdout[:200], r.stderr[:200]))
        got = b""
        if os.path.exists(out):
            with open(out, "rb") as f:
                got = f.read()
        check("chunked_dl.concat_from_existing_parts", got == payload,
              "got %r (the old hardcoded part_00..15 cat fails as soon as one "
              "early-exit chunk creates no part)" % got[:32])
        check("chunked_dl.reports_complete", "COMPLETE" in r.stdout,
              "stdout=%r" % r.stdout[:200])
        check("chunked_dl.stale_errors_log_cleaned", not os.path.exists(stale),
              "dl_errors.log must be cleaned at start AND on success")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# --------------------------------------------------------------------------
def main():
    test_daemonize()
    test_render_daemon_window_wipe()
    test_suite_runner_list()
    test_chunked_dl_missing_parts()
    fails = [name for name, ok in RESULTS if not ok]
    print("[test_s17i] %d/%d checks passed"
          % (len(RESULTS) - len(fails), len(RESULTS)))
    if fails:
        print("[test_s17i] FAILED: %s" % fails)
        sys.exit(1)
    print("[test_s17i] ALL PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
