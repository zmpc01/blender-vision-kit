#!/usr/bin/env python3
"""sfx_events.py -- frame-stamped SFX event stream for offline mixing.

Blender's own audio surface (speakers, VSE) does not survive headless
batch renders cleanly, and per-frame programmatic synthesis inside the
session is fragile. The robust pipeline (user feedback 10):

    scene build -> events (frame, name, kwargs) -> JSON
                -> build_sfx.py (numpy synthesis) -> sfx.wav
                -> ffmpeg mux with the dialog VO -> anim_sfx.mp4

Every event carries the exact frame; the timing gate verifies each
lands inside its shot window. The same JSON carries the dialog onsets
so the mux script stops being a second source of truth.

Event vocabulary (build_sfx.py maps these to synth patches):
    engine_start, engine_rev (speed track), door_slam, jeep_lurch,
    kd_impact (side, strength), gunshot_burst (n_shots), splash,
    barricade_smash, chunk_rattle, lunge_grab, tire_dust
"""
from __future__ import annotations

import json
import os

FPS = 24


class Emitter:
    def __init__(self, fps=FPS, meta=None):
        self.fps = fps
        self.events = []
        self.meta = dict(meta or {})

    def add(self, name, frame, **kw):
        self.events.append(dict(name=name, frame=int(frame), **kw))
        return self.events[-1]

    def add_dialog(self, lines):
        """lines: [(clip_name, onset_frame), ...] -> typed events."""
        for clip, f in lines:
            self.add("dialog", f, clip=clip)

    def to_dict(self):
        return {"fps": self.fps, "meta": self.meta,
                "events": sorted(self.events, key=lambda e: e["frame"])}

    def write(self, path):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, indent=1)
        return path


def verify_timing(events_dict, shots, tol=4):
    """Every event frame must land inside SOME shot window (+- tol).
    Returns findings list (empty = clean). Shots: [(sid, f0, f1, desc)]"""
    findings = []
    windows = [(s[0], s[1] - tol, s[2] + tol) for s in shots]
    for ev in events_dict.get("events", []):
        f = ev["frame"]
        if not any(w0 <= f <= w1 for _sid, w0, w1 in windows):
            findings.append(f"[sfx] {ev['name']} @f{f} outside every "
                            f"shot window (+-{tol}f)")
    return findings


def onset_of(ev, fps=FPS):
    return ev["frame"] / fps
