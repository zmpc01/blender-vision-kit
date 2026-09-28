#!/usr/bin/env python3
"""
render_daemon.py -- double-forked render daemon (survives toolcall kills).

The sandbox kills the whole bash descendant tree at toolcall end. A
double-forked process reparents to PID 1 and escapes that kill, so
long chunked renders keep running across toolcalls. Progress is written
to a heartbeat file; the parent process just launches and returns.

Usage (host side):
  python3 scripts/render_daemon.py --scene scene_cornell \\
      --output output/cornell --quality draft --frames 720 \\
      --chunks 4 --encode-mp4 --heartbeat /tmp/render_hb.json

  poll:   python3 -c "import json;print(json.load(open('/tmp/render_hb.json')))"
"""
import argparse
import fcntl
import json
import math
import os
import subprocess
import sys
import time


def daemonize():
    if os.fork():
        sys.exit(0)
    os.setsid()
    if os.fork():
        sys.exit(0)
    sys.stdout.flush()
    sys.stderr.flush()
    devnull = os.open("/dev/null", os.O_RDWR)
    os.dup2(devnull, 0)
    os.dup2(devnull, 1)
    os.dup2(devnull, 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", default="scene_cornell")
    ap.add_argument("--output", required=True)
    ap.add_argument("--quality", default="draft")
    ap.add_argument("--frames", type=int, default=720)
    ap.add_argument("--chunks", type=int, default=4)
    ap.add_argument("--encode-mp4", action="store_true")
    ap.add_argument("--extra", default="")
    ap.add_argument("--heartbeat", default="/tmp/render_hb.json")
    ap.add_argument("--no-physics", action="store_true")
    ap.add_argument("--first-chunk", type=int, default=0)
    ap.add_argument("--start", type=int, default=1,
                    help="First frame of the whole range (default 1)")
    args = ap.parse_args()

    hb = {"status": "starting", "chunk": args.first_chunk, "chunks": args.chunks,
          "frames_done": 0, "total_frames": args.frames,
          "started": time.time(), "pid": None, "output": args.output,
          "log": []}

    def write_hb(**kw):
        hb.update(kw)
        # atomic write (tmp + os.replace): the sandbox can kill bash
        # descendants mid-toolcall -- a truncated heartbeat is worse than
        # a stale one (session-9 review 16-a P0-3)
        tmp = args.heartbeat + ".tmp"
        with open(tmp, "w") as f:
            json.dump(hb, f)
        os.replace(tmp, args.heartbeat)

    # double-fork INTO the background, then do the work as PID 1's child
    # 'starting' written by the PARENT before the fork: without this the
    # heartbeat still shows the previous run's 'done' until the daemon's
    # first write -- a fast poller can act on stale state (review 16-b P1-8)
    write_hb(status="starting")
    daemonize()
    # render lock (review 16-a P0-4): two daemons on the same scene =
    # frame clobber + heartbeat ping-pong. flock for the daemon lifetime.
    lock_path = "/tmp/%s.render.lock" % os.path.basename(
        os.path.abspath(args.output))
    lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o644)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        write_hb(status="refused_lock_held")
        sys.exit(2)
    os.write(lock_fd, str(os.getpid()).encode())
    os.ftruncate(lock_fd, len(str(os.getpid())))
    write_hb(status="running", pid=os.getpid())

    kit = os.path.dirname(os.path.abspath(__file__))
    cwd = os.path.dirname(kit)
    out_abs = os.path.abspath(args.output)
    os.makedirs(out_abs, exist_ok=True)
    # clear stale frames from previous runs (review 16-b P0-1: distribute
    # trusts whatever is in scratch -- a partial re-render left old files
    # that mixed generations into shot dirs)
    import glob as _glob
    for old in (_glob.glob(os.path.join(out_abs, "frame_*.png"))
                + _glob.glob(os.path.join(out_abs, "frame_*.jpg"))):
        os.remove(old)

    per = int(math.ceil(args.frames / args.chunks))
    for i in range(args.first_chunk, args.chunks):
        f_start = args.start + i * per
        f_end = min(args.start + (i + 1) * per - 1,
                    args.start + args.frames - 1)
        if f_start > f_end:
            break
        cmd = ["./run.sh", "--background", "--python",
               "scripts/%s.py" % args.scene, "--",
               "--output", args.output, "--quality", args.quality,
               "--start", str(f_start), "--frames", str(f_end - f_start + 1),
               "--scene-name", os.path.basename(out_abs)]
        if args.no_physics:
            cmd += ["--no-physics"]
        if args.extra:
            cmd += args.extra.split()
        log = os.path.join(out_abs, "daemon_chunk%d.log" % i)
        write_hb(status="rendering", chunk=i, chunk_frames=(f_start, f_end))
        with open(log, "w") as lf:
            rc = subprocess.call(cmd, cwd=cwd, stdout=lf, stderr=subprocess.STDOUT)
        done = min(args.start + (i + 1) * per - 1, args.start + args.frames - 1)
        write_hb(status="chunk_done" if rc == 0 else "chunk_error",
                 chunk=i, frames_done=done, last_rc=rc)
        if rc != 0:
            sys.exit(1)

    # count rendered frames (ONLY this run's range -- not stale files;
    # review 16-b P0-1)
    lo, hi = args.start, args.start + args.frames - 1
    frames = [f for f in glob_frames(out_abs)
              if lo <= int(os.path.basename(f).split("_")[1].split(".")[0]) <= hi]
    # NB: status name 'done' (renamed from 'encoded' -- it was written
    # even when no --encode-mp4 was passed; review 16-a P0-4)
    write_hb(status="done", frames_done=len(frames))
    sys.exit(0)


def glob_frames(out_abs):
    import glob
    # both extensions: viewport quality writes JPEG (session-9), other
    # qualities write PNG. The old PNG-only glob made every JPEG render
    # report frames_done=0 (review 16-a P0-1).
    frames = glob.glob(os.path.join(out_abs, "frame_*.png")) \
        + glob.glob(os.path.join(out_abs, "frame_*.jpg"))
    return frames


if __name__ == "__main__":
    main()
