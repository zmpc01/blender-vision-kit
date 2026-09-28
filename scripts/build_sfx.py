#!/usr/bin/env python3
"""build_sfx.py -- deterministic numpy SFX synthesis from sfx_events.json.

Reads the frame-stamped event stream emitted by the scene build
(sfx_events.py) and renders a 48 kHz stereo sfx.wav, then (optionally)
muxes it with the dialog VO into anim_sfx.mp4 via ffmpeg.

Synth patches (all deterministic, no assets required):
    kd_impact      decaying low-passed noise thud (strength-scaled)
    gunshot_burst  click transient + band noise tail per shot
    splash         white noise burst w/ highpass sweep
    barricade_smash layered noise crash + low sine drop
    engine_start/rev sawtooth + sub harmonic, speed-mapped pitch
    door_slam      short thud
    lunge_grab     mid growl (band noise + AM)
    chunk_rattle   rapid tick cluster
    tire_dust      soft filtered noise swell
    dialog         (vo track, mixed from files -- mux stage only)

Isolation contract: this script NEVER runs inside the Blender session
and a failure here cannot kill a render -- it is a post-render
deliverable (anim_sfx.mp4 is additive; anim_dialog.mp4 stays canonical).

Usage:
    python3 build_sfx.py events.json --out sfx.wav [--vo dialog.wav \
        --video anim.mp4 --mux anim_sfx.mp4]
"""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import wave

import numpy as np

SR = 48000


def _noise(n, rng):
    return rng.standard_normal(n)


def _env_ad(n, a, d, sr=SR):
    t = np.arange(n) / sr
    e = np.minimum(t / max(a, 1e-6), 1.0) * np.exp(-t / max(d, 1e-6))
    return e


def _lowpass(x, cutoff, sr=SR):
    # one-pole lowpass, vectorized
    rc = 1.0 / (2 * math.pi * max(cutoff, 1.0))
    dt = 1.0 / sr
    alpha = dt / (rc + dt)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc += alpha * (x[i] - acc)
        y[i] = acc
    return y


def _highpass(x, cutoff, sr=SR):
    return x - _lowpass(x, cutoff, sr)


def patch_kd_impact(ev, rng):
    dur = 0.28 + 0.22 * float(ev.get("strength", 1.0))
    n = int(dur * SR)
    x = _noise(n, rng) * _env_ad(n, 0.002, dur * 0.35)
    x = _lowpass(x, 180.0 + 320.0 * float(ev.get("strength", 1.0)))
    side = float(ev.get("pan", 0.0))
    return x, x * (1.0 - 0.5 * side), x * (1.0 + 0.5 * side)


def patch_gunshot(ev, rng):
    n_shots = int(ev.get("n_shots", 6))
    gap = int(0.11 * SR)
    n = n_shots * gap + int(0.4 * SR)
    x = np.zeros(n)
    for i in range(n_shots):
        s = i * gap
        c = int(0.004 * SR)
        crack = _noise(c, rng) * _env_ad(c, 0.0005, 0.003)
        tail = _noise(int(0.22 * SR), rng) * _env_ad(
            int(0.22 * SR), 0.001, 0.06)
        tail = _highpass(tail, 900.0)
        x[s:s + c] += crack * 0.9
        x[s + c:s + c + len(tail)] += tail * 0.4
    return x, x * 0.85, x


def patch_splash(ev, rng):
    n = int(0.5 * SR)
    x = _noise(n, rng) * _env_ad(n, 0.004, 0.22)
    x = _highpass(x, 1400.0) * 0.8 + _lowpass(x, 400.0) * 0.4
    return x, x, x


def patch_smash(ev, rng):
    n = int(1.4 * SR)
    x = _noise(n, rng) * _env_ad(n, 0.002, 0.5)
    x = _lowpass(x, 500.0) * 1.1 + _highpass(x, 2500.0) * 0.35
    t = np.arange(n) / SR
    x += np.sin(2 * math.pi * (90.0 - 55.0 * t / 1.4) * t) * \
        _env_ad(n, 0.001, 0.4) * 0.7
    return x, x, x


def patch_engine(ev, rng):
    f0 = float(ev.get("pitch", 1.0))
    dur = float(ev.get("dur", 3.0))
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = 42.0 * f0
    x = (np.sin(2 * math.pi * f * t) * 0.5
         + np.sin(2 * math.pi * 2 * f * t) * 0.25
         + np.sin(2 * math.pi * 3 * f * t) * 0.12)
    x *= _env_ad(n, 0.08, dur)
    return x * 0.8, x * 0.8, x * 0.8


def patch_thud(ev, rng):
    n = int(0.16 * SR)
    t = np.arange(n) / SR
    x = np.sin(2 * math.pi * 70.0 * np.exp(-t * 8)) * _env_ad(n, 0.001, 0.05)
    return x, x, x


def patch_rattle(ev, rng):
    n_ticks = int(ev.get("n", 10))
    n = int(0.9 * SR)
    x = np.zeros(n)
    for i in range(n_ticks):
        s = rng.integers(0, n - 2000)
        c = int(0.003 * SR)
        x[s:s + c] += _noise(c, rng) * _env_ad(c, 0.0005, 0.002) * 0.5
    return x, x * 0.9, x


def patch_tire(ev, rng):
    n = int(1.2 * SR)
    x = _noise(n, rng) * _env_ad(n, 0.25, 0.5)
    x = _lowpass(x, 700.0) * 0.5
    return x, x, x


def patch_grab(ev, rng):
    n = int(0.6 * SR)
    t = np.arange(n) / SR
    x = _noise(n, rng) * (0.5 + 0.5 * np.sin(2 * math.pi * 23 * t))
    x = _lowpass(x, 900.0) * _env_ad(n, 0.02, 0.25) * 0.9
    return x, x, x


PATCHES = {
    "kd_impact": patch_kd_impact,
    "gunshot_burst": patch_gunshot,
    "splash": patch_splash,
    "barricade_smash": patch_smash,
    "engine_start": patch_engine,
    "engine_rev": patch_engine,
    "door_slam": patch_thud,
    "jeep_lurch": patch_thud,
    "chunk_rattle": patch_rattle,
    "tire_dust": patch_tire,
    "lunge_grab": patch_grab,
}


def build(events_path, out_wav, seed=1234):
    with open(events_path, encoding="utf-8") as fh:
        data = json.load(fh)
    fps = data.get("fps", 24)
    events = data.get("events", [])
    total_s = max((ev["frame"] / fps + 3.0 for ev in events), default=5.0)
    n = int(total_s * SR)
    L = np.zeros(n)
    R = np.zeros(n)
    rng = np.random.default_rng(seed)
    for ev in events:
        fn = PATCHES.get(ev["name"])
        if fn is None:
            if ev["name"] != "dialog":
                print(f"[sfx] no patch for {ev['name']} (skipped)")
            continue
        x, l, r = fn(ev, rng)
        s = int(ev["frame"] / fps * SR)
        e = min(n, s + len(x))
        if s < n:
            L[s:e] += l[:e - s] * 0.9
            R[s:e] += r[:e - s] * 0.9
    peak = max(np.abs(L).max(), np.abs(R).max(), 1e-9)
    if peak > 0.98:
        L *= 0.98 / peak
        R *= 0.98 / peak
    os.makedirs(os.path.dirname(out_wav) or ".", exist_ok=True)
    with wave.open(out_wav, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        inter = np.empty(n * 2)
        inter[0::2] = L
        inter[1::2] = R
        w.writeframes((inter * 32767).astype(np.int16).tobytes())
    print(f"[sfx] wrote {out_wav} ({n / SR:.1f}s, "
          f"{len(events)} events, peak {peak:.2f})")
    return out_wav


def mux(sfx_wav, vo_wav, video, out_mp4, fps=24):
    """Mix sfx + VO over the video. VO sits at unity; sfx at 0.9."""
    if not os.path.exists(video):
        print(f"[sfx] video {video} missing -- skip mux")
        return None
    inputs = ["-i", video, "-i", sfx_wav]
    filt = "[1:a]"
    if vo_wav and os.path.exists(vo_wav):
        inputs += ["-i", vo_wav]
        filt = ("[1:a]volume=0.9[a1];[2:a]volume=1.0[a2];"
                "[a1][a2]amix=inputs=2:duration=longest[aout]")
    else:
        filt = "[1:a]volume=0.9[aout]"
    cmd = (["ffmpeg", "-y", "-v", "warning"] + inputs +
           ["-filter_complex", filt, "-map", "0:v", "-map", "[aout]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", out_mp4])
    r = subprocess.run(cmd, check=False)
    if r.returncode == 0:
        print(f"[sfx] muxed {out_mp4}")
        return out_mp4
    print("[sfx] mux FAILED (non-fatal -- sfx.wav is the deliverable)")
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("events", help="sfx_events.json")
    ap.add_argument("--out", default="sfx.wav")
    ap.add_argument("--vo", default=None, help="dialog VO wav")
    ap.add_argument("--video", default=None, help="rendered mp4")
    ap.add_argument("--mux", default=None, help="output anim_sfx.mp4")
    a = ap.parse_args()
    build(a.events, a.out)
    if a.video and a.mux:
        mux(a.out, a.vo, a.video, a.mux)


if __name__ == "__main__":
    sys.exit(main())
