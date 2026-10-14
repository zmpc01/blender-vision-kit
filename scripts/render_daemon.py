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

Heartbeat key semantics (F2E-10 — one key, one unit; the old code wrote a
frame NUMBER into frames_done mid-run and a COUNT at done):
  frames_done   COUNT of frames rendered within this run's window so far
  last_frame    frame NUMBER of the highest frame this run has completed
  total_frames  COUNT of frames the WHOLE range (--frames) will produce
  counted_range [lo, hi] frame numbers the done/chunk_done counts cover —
                on a --first-chunk resume this is the RESUMED window only,
                which is why frames_done may be < total_frames honestly.
"""
import argparse
import fcntl
import json
import math
import os
import subprocess
import sys
import time
import traceback


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


def frame_num(path):
    """'frame_0007.png' -> 7; None for anything not shaped like a frame."""
    base = os.path.basename(path)
    try:
        return int(base.split("_")[1].split(".")[0])
    except (IndexError, ValueError):
        return None


def glob_frames(out_abs):
    import glob
    # both extensions: viewport quality writes JPEG (session-9), other
    # qualities write PNG. The old PNG-only glob made every JPEG render
    # report frames_done=0 (review 16-a P0-1).
    frames = glob.glob(os.path.join(out_abs, "frame_*.png")) \
        + glob.glob(os.path.join(out_abs, "frame_*.jpg"))
    return frames


def count_frames_in(out_abs, lo, hi):
    """COUNT of rendered frames whose NUMBER lies in [lo, hi] (F2E-10)."""
    n = 0
    for f in glob_frames(out_abs):
        num = frame_num(f)
        if num is not None and lo <= num <= hi:
            n += 1
    return n


def wipe_frame_window(out_abs, lo, hi):
    """Remove only the frame files this run will (re)produce.

    F2E-4: the old unconditional `rm frame_*` meant a `--first-chunk N`
    resume DELETED every completed chunk's frames from the FINAL output
    dir before re-rendering the tail — status "done" then honestly
    counted a range that had just been thrown away on disk. Review
    16-b P0-1's stale-scratch concern still holds for a full run, so we
    wipe exactly the [lo, hi] window and touch nothing outside it.
    Returns the number of files removed.
    """
    import glob as _glob
    removed = 0
    for old in (_glob.glob(os.path.join(out_abs, "frame_*.png"))
                + _glob.glob(os.path.join(out_abs, "frame_*.jpg"))):
        num = frame_num(old)
        if num is not None and lo <= num <= hi:
            os.remove(old)
            removed += 1
    return removed


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
          "frames_done": 0, "last_frame": None, "total_frames": args.frames,
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

    # F2E-9: create the heartbeat dir PRE-fork. Post-fork, stderr is
    # /dev/null and every write_hb OSError would be invisible — a missing
    # heartbeat dir used to freeze the heartbeat at "starting" forever.
    hb_dir = os.path.dirname(os.path.abspath(args.heartbeat)) or "/"
    try:
        os.makedirs(hb_dir, exist_ok=True)
    except OSError as e:
        print("render_daemon: cannot create heartbeat dir %s: %r" % (hb_dir, e),
              file=sys.stderr)
        sys.exit(2)

    # double-fork INTO the background, then do the work as PID 1's child
    # 'starting' written by the PARENT before the fork: without this the
    # heartbeat still shows the previous run's 'done' until the daemon's
    # first write -- a fast poller can act on stale state (review 16-b P1-8)
    write_hb(status="starting")
    daemonize()

    # F2E-9: EVERY post-fork failure used to die silently (stderr ->
    # /dev/null, heartbeat frozen at "starting"/"running", the documented
    # poller hanging with no signal). Fail LOUDLY instead: best-effort
    # daemon_error heartbeat + traceback file. (SystemExit — the lock
    # refusal and chunk-failure exits — passes through untouched.)
    out_abs = None
    try:
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

        # F2E-4: wipe ONLY the frame window this run will produce —
        # [start + first_chunk*per, start + frames - 1] — never the
        # completed chunks a resume must preserve.
        per = int(math.ceil(args.frames / args.chunks))
        run_lo = args.start + args.first_chunk * per
        run_hi = args.start + args.frames - 1
        wipe_frame_window(out_abs, run_lo, run_hi)

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
            # F2E-10: frames_done = COUNT within this run's window so far;
            # last_frame = the frame NUMBER just completed. One key, one unit.
            so_far = count_frames_in(out_abs, run_lo, f_end)
            write_hb(status="chunk_done" if rc == 0 else "chunk_error",
                     chunk=i, frames_done=so_far, last_frame=f_end, last_rc=rc)
            if rc != 0:
                sys.exit(1)

        # count rendered frames (ONLY this run's window -- not stale files;
        # review 16-b P0-1). On a --first-chunk resume the window is the
        # resumed range only; counted_range discloses that explicitly.
        n_done = count_frames_in(out_abs, run_lo, run_hi)
        # NB: status name 'done' (renamed from 'encoded' -- it was written
        # even when no --encode-mp4 was passed; review 16-a P0-4)
        write_hb(status="done", frames_done=n_done, last_frame=run_hi,
                 counted_range=[run_lo, run_hi])
        sys.exit(0)
    except Exception as e:  # F2E-9: never die silently post-fork
        try:
            write_hb(status="daemon_error", error=repr(e))
        except Exception:
            pass
        # best-effort traceback file: prefer the output dir, fall back to
        # the heartbeat dir (the output dir itself may be the thing that
        # failed — e.g. makedirs raised on it).
        tb = traceback.format_exc()
        for tb_dir in (out_abs, hb_dir):
            if not tb_dir:
                continue
            try:
                with open(os.path.join(tb_dir, "daemon_error.log"), "w") as f:
                    f.write(tb)
                break
            except Exception:
                continue
        sys.exit(3)


if __name__ == "__main__":
    main()
