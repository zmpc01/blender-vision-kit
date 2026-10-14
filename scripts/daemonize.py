#!/usr/bin/env python3
"""
daemonize.py — the ONLY sanctioned background survivor (double-fork).

The sandbox reaps the whole bash descendant tree between tool calls
(SKILL.md §L181 reaping law). A double-forked grandchild reparents to
PID 1 and escapes that reaping, so long-lived processes (dev servers,
comment-db apps) keep running across tool-call boundaries.

Usage:
    python3 scripts/daemonize.py <ABSOLUTE log path> <cmd> [args...]

The documented invocation (SKILL.md §271 / HANDOFF.md:119-120):
    python3 scripts/daemonize.py /tmp/devserver.log \\
        bash -c "cd /home/z/repos/blender-vision-kit && python3 -m http.server 8000"

Semantics (per the documented law):
  * double-fork: fork → setsid → fork. The launcher (this script's
    original process) exits IMMEDIATELY — callers must NOT wait for the
    command; poll the log instead.
  * the daemon chdirs("/") — relative paths die at the first fork. The
    log path is therefore ENFORCED absolute (a relative log path EACCES's
    or lands somewhere surprising); commands should be wrapped in
    `bash -c "cd <repo> && cmd"` with an absolute repo path.
  * stdin ← /dev/null; stdout AND stderr → the log path (APPEND — restarts
    keep their history).
  * best-effort os.setsid() on the middle fork (new session, controlling
    tty dropped; tolerated to fail since the second fork re-detaches).
  * exec's the command via os.execvp — no wrapper process remains.
  * stdlib only (no dependencies); failures opening the log are reported
    to the CALLER's stderr BEFORE the first fork, so an unwritable log
    path fails loudly at the call site instead of vanishing.
"""
import os
import sys


def _die(msg):
    # Called PRE-fork only: stderr still belongs to the caller.
    sys.stderr.write("daemonize: %s\n" % msg)
    sys.exit(1)


def main():
    if len(sys.argv) < 3:
        _die("usage: daemonize.py <ABSOLUTE log> <cmd> [args...] "
             "(e.g. bash -c 'cd <repo> && cmd')")
    log = sys.argv[1]
    cmd = sys.argv[2:]
    if not os.path.isabs(log):
        _die("log path must be ABSOLUTE (the daemon chdirs '/'): %r" % log)

    # Open the log BEFORE the first fork: an unwritable path must be
    # reported to the caller's stderr, not silently swallowed by the
    # daemon's fd redirection.
    try:
        log_fd = os.open(log, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    except OSError as e:
        _die("cannot open log %s: %s" % (log, e))
    devnull = os.open(os.devnull, os.O_RDWR)

    # ---- first fork: the parent exits immediately ----
    if os.fork():
        os.close(log_fd)
        os.close(devnull)
        sys.exit(0)

    # ---- middle fork: new session, lose the controlling terminal ----
    try:
        os.setsid()
    except OSError:
        pass  # best-effort: the second fork still detaches the daemon

    # ---- second fork: the grandchild is the daemon (reparented to PID 1) ----
    if os.fork():
        os._exit(0)  # middle process: no atexit/flush machinery wanted here

    # ---- daemon (grandchild) ----
    try:
        os.chdir("/")
    except OSError:
        pass  # "/" is always valid; guard for exotic environments anyway
    # Redirect FIRST, close originals AFTER — dup2 needs the source fd open.
    os.dup2(devnull, 0)   # stdin  <- /dev/null
    os.dup2(log_fd, 1)    # stdout -> ABSOLUTE log (append)
    os.dup2(log_fd, 2)    # stderr -> ABSOLUTE log (append)
    if devnull > 2:
        os.close(devnull)
    if log_fd > 2:
        os.close(log_fd)

    try:
        os.execvp(cmd[0], cmd)
    except Exception as e:  # noqa: BLE001 — last resort before death
        # stderr is the log now; record why the daemon never started.
        os.write(2, ("daemonize: exec %r failed: %r\n" % (cmd, e)).encode())
        os._exit(127)


if __name__ == "__main__":
    main()
