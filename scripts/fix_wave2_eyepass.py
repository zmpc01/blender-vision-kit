#!/usr/bin/env python3
"""fix_wave2_eyepass.py — the per-film VLM framing audit (issue #4,
cinematography). For every still in output/<film>/stills/, audit the
frame against the shot's authored intent (the SHOTS table text from
the scene module): framing, subject visibility, crowd read, glitches.

Writes output/<film>/eyepass.json + a labeled contact sheet. The
principal (orchestrator) adjudicates FAILs and re-authors cameras.
"""
import json
import os
import re
import subprocess
import sys
from PIL import Image, ImageDraw

FILM = sys.argv[1]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STILLS = os.path.join(ROOT, "output", FILM, "stills")

SCENE_MODULES = {
    "tdawn": ("scene_terminal_dawn.py", "SHOTS_V3"),
    "tferry": ("scene_last_ferry.py", "SHOTS_V3"),
    "tgreen": ("scene_green_light.py", "SHOTS_V3"),
    "tsquall": ("scene_squall.py", "SHOTS_V3"),
    "tfog": ("tfog_scene.py", "SHOTS_V3"),
    "tform": ("tform_scene.py", "SHOTS_V3"),
    "tmarket": ("scene_night_market.py", "SHOTS_V3"),
}

PROMPT = """You are auditing one still frame from a previs film shot. The shot's authored intent is:
"{intent}"

Answer in exactly this format (be strict but fair — previs quality, not final VFX):
FRAMING: <GOOD|WEAK|BAD> — one sentence on composition/vantage
SUBJECT: <CLEAR|PARTIAL|MISSING> — is the shot's subject readable?
CROWD: <NATURAL|ODD|BROKEN> — do the background figures read as a believable crowd?
GLITCH: <NONE|MINOR|MAJOR> — torn/duplicated/frozen bodies, facing wrong way, floating, black frame
VERDICT: <PASS|FIX> — one line summary
"""


def shot_intents(film):
    mod, tbl = SCENE_MODULES[film]
    src = open(os.path.join(ROOT, "scripts", mod)).read()
    m = re.search(rf"{tbl}\s*=\s*\[(.*?)\n\]", src, re.S)
    if not m:
        raise SystemExit(f"no {tbl} in {mod}")
    out = {}
    for line in m.group(1).splitlines():
        mm = re.match(r"\s*\(\"(S\d+)\",\s*(\d+),\s*(\d+),\s*\"(.*)\"\),?\s*$",
                      line)
        if mm:
            out[mm.group(1)] = mm.group(4)
    return out


def vlm(prompt, image):
    r = subprocess.run(
        ["z-ai", "vision", "-p", prompt, "-i", image, "-o", "/tmp/eyepass_vlm.json"],
        capture_output=True, text=True, timeout=180)
    try:
        d = json.load(open("/tmp/eyepass_vlm.json"))
        return d["choices"][0]["message"]["content"]
    except Exception:
        return f"VLM-ERROR rc={r.returncode}: {r.stdout[-200:]} {r.stderr[-200:]}"


def main():
    intents = shot_intents(FILM)
    files = sorted(f for f in os.listdir(STILLS) if f.startswith("shot_S"))
    if not files:
        raise SystemExit(f"no stills in {STILLS}")
    results = {}
    for f in files:
        sid = f.replace("shot_", "").replace(".png", "")
        intent = intents.get(sid, "(unknown shot)")
        ans = vlm(PROMPT.format(intent=intent),
                  os.path.join(STILLS, f))
        results[sid] = {"intent": intent, "answer": ans,
                        "verdict": "FIX" if "VERDICT: FIX" in ans
                        or "VERDICT:FIX" in ans else
                        ("PASS" if "VERDICT: PASS" in ans
                         or "VERDICT:PASS" in ans else "UNCLEAR")}
        print(f"{sid}: {results[sid]['verdict']}")
    out = os.path.join(ROOT, "output", FILM, "eyepass.json")
    json.dump(results, open(out, "w"), indent=1)
    n_fix = sum(1 for r in results.values() if r["verdict"] == "FIX")
    print(f"\n{FILM}: {len(results)} shots audited, "
          f"{n_fix} FIX, {len(results) - n_fix} pass/unclear -> {out}")

    # labeled contact sheet (3x4)
    COLS, ROWS, CW, PAD = 3, 4, 640, 26
    im0 = Image.open(os.path.join(STILLS, files[0]))
    ch = im0.size[1] * CW // im0.size[0]
    sheet = Image.new("RGB", (CW * COLS, (ch + PAD) * ROWS), (16, 16, 20))
    d = ImageDraw.Draw(sheet)
    for i, f in enumerate(files):
        r, c = divmod(i, COLS)
        im = Image.open(os.path.join(STILLS, f)).resize((CW, ch), Image.LANCZOS)
        x, y = c * CW, r * (ch + PAD)
        sheet.paste(im, (x, y + PAD))
        sid = f.replace("shot_", "").replace(".png", "")
        col = (120, 255, 120) if results[sid]["verdict"] == "PASS" else \
              (255, 210, 90) if results[sid]["verdict"] == "UNCLEAR" else \
              (255, 110, 110)
        d.text((x + 6, y + 5), f"{FILM} {sid} [{results[sid]['verdict']}]",
               fill=col)
    sp = os.path.join(ROOT, "output", FILM, "eyepass_sheet.jpg")
    sheet.save(sp, quality=88)
    print(f"sheet: {sp}")


if __name__ == "__main__":
    main()
