#!/usr/bin/env python3
"""ab_evaluate.py -- blind A/B render evaluation, the NATIVE-VISION form.

Vision-kit port (s24) of the proven previz/kit methodology (previz v4
step 6 -> kit s38 CLI). The METHOD is the product, kept verbatim:

  * extracts stills per side per window (early / mid / late fracs)
  * builds BOTH orderings of the side-by-side pair (blind: labels are
    random A/B per shot, SWAPPED between stills -- a real preference
    must survive the swap)
  * pair-preference (blind, both orderings) -> pref share >= 2/3 rule
  * readability (per side, blind-order 3-axis 1-5 scores)
  * anatomy-defect keyword scan (defect side only)
  * writes ab_decision.json with all inputs + the computed rule verdict

THE SEAM IS DIFFERENT HERE (the scope doctrine): this kit has NO VLM
bridge — the perception is the AGENT'S OWN EYES. The z-ai vlm() call is
replaced by a two-phase native loop:

  1) `prep`  — builds the stills, BOTH-ordering pairs, an
     ab_worksheet.json (the exact questions + image paths, blind
     labels seeded) AND an ab_answers.json SKELETON (the exact shape
     decide consumes — fill it in place). The agent LOOKS at each
     pair/still and records answers.
  2) `decide` — validates the answers (every pair answered; the swap
     structure preserved; inline worksheet answers also accepted),
     computes the SAME rule verdict the s38 tool computed plus a
     computed `verdict` field, and emits ab_decision.json.

A preference that flips with the ordering is an ordering artifact, not
a preference — the swap law does the debiasing the VLM-era tool got
from double-querying.

Usage:
  python3 scripts/ab_evaluate.py prep \
      --side-a /path/to/build_a --label-a capsule \
      --side-b /path/to/build_b --label-b ual \
      --windows S2:89:132,S3:133:168 \
      --defect-side b [--out DIR] [--seed 4242] [--stills 0.2,0.5,0.8]
  # ... the agent LOOKS at <out>/*_pair*.jpg and the mid stills, fills
  # ab_answers.json ...
  python3 scripts/ab_evaluate.py decide --dir <out>

Frame convention (the ONLY one prep reads):
  <side_dir>/<shot>/frame_<f:04d>.png (or .jpg)
  e.g. build_a/S2/frame_0101.png
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys

PREF_Q_DEFAULT = ("Two versions of the same storyboard shot from an animated "
                  "sequence, side by side. Which version reads BETTER as "
                  "cinema -- clearer character acting, more believable motion, "
                  "more engaging character design? Answer with exactly 'LEFT' "
                  "or 'RIGHT' followed by one short reason.")
READ_Q_DEFAULT = ("Rate this storyboard frame for READABILITY on 3 axes, each "
                  "1-5: (a) character poses/acting clarity, (b) motion legibility "
                  "(can you tell what the characters are doing), (c) overall "
                  "visual engagement. Then list any anatomy defects you see "
                  "(broken/severed/floating body parts, unnatural joint bends). "
                  "Be strict: this is a defect audit.")

DEFECT_KEYWORDS = ("defect", "severed", "floating", "broken")

ANSWERS_NAME = "ab_answers.json"
WORKSHEET_NAME = "ab_worksheet.json"
DECISION_NAME = "ab_decision.json"


def parse_windows(spec):
    """'S2:89:132,S3:133:168' -> [('S2', 89, 132), ...]"""
    out = []
    for part in spec.split(","):
        bits = part.strip().split(":")
        if len(bits) != 3:
            raise SystemExit(f"bad window {part!r} (want SHOT:F0:F1)")
        out.append((bits[0], int(bits[1]), int(bits[2])))
    if not out:
        raise SystemExit("no windows given")
    return out


def stills(side_dir, f0, f1, sid, fracs, out_dir, label):
    """Extract the fraction-stills for one side; returns [] when the
    shot dir is absent (the caller skips that side loudly)."""
    out = []
    sdir = os.path.join(side_dir, sid)
    if not os.path.isdir(sdir):
        return out
    for frac in fracs:
        f = int(f0 + (f1 - f0) * frac)
        src = None
        for ext in (".png", ".jpg"):
            cand = os.path.join(sdir, f"frame_{f:04d}{ext}")
            if os.path.exists(cand):
                src = cand
                break
        if src is None:
            continue
        dst = os.path.join(out_dir, f"{sid}_{label}_{os.path.basename(src)}")
        import shutil
        shutil.copy2(src, dst)
        out.append(dst)
    return out


def pair(a_img, b_img, dst):
    from PIL import Image
    ia, ib = Image.open(a_img), Image.open(b_img)
    w, h = max(ia.size[0], ib.size[0]), max(ia.size[1], ib.size[1])
    grid = Image.new("RGB", (w * 2, h))
    grid.paste(ia.convert("RGB"), (0, 0))
    grid.paste(ib.convert("RGB"), (w, 0))
    grid.save(dst, quality=92)


def parse_side(ans):
    a = str(ans).strip().upper()
    if a.startswith("LEFT"):
        return "L"
    if a.startswith("RIGHT"):
        return "R"
    return "?"


def parse_scores(ans):
    try:
        scores = [float(c) for c in
                  str(ans).replace("(a)", "").replace("(b)", "")
                  .replace("(c)", "").split() if
                  c and c[0].isdigit() and
                  float(c) <= 5][:3]
        return sum(scores) / len(scores) if scores else 0
    except Exception:                                       # noqa: BLE001
        return 0


def cmd_prep(args):
    for d, tag in ((args.side_a, args.label_a), (args.side_b, args.label_b)):
        if not os.path.isdir(d):
            raise SystemExit(f"--side-{tag} {d!r} is not a directory")
    out = args.out or os.path.join(os.path.dirname(os.path.abspath(
        args.side_a)), "ab_eval")
    os.makedirs(out, exist_ok=True)
    windows = parse_windows(args.windows)
    fracs = tuple(float(x) for x in args.stills.split(","))
    labels = {"a": args.label_a, "b": args.label_b}
    defect_label = labels[args.defect_side]

    rng = random.Random(args.seed)          # blind labels, deterministic
    worksheet = {"seed": args.seed, "labels": labels,
                 "defect_side": args.defect_side,
                 "pref_question": args.pref_question,
                 "read_question": args.read_question,
                 "windows": [w[0] for w in windows], "shots": {}}
    for sid, f0, f1 in windows:
        a_st = stills(args.side_a, f0, f1, sid, fracs, out, args.label_a)
        b_st = stills(args.side_b, f0, f1, sid, fracs, out, args.label_b)
        # the s38 guards verbatim: a missing side is a loud skip, never
        # an IndexError; unequal still counts cannot pair.
        if not a_st or not b_st:
            print(f"[ab] {sid}: SKIP (stills a={len(a_st)} b={len(b_st)})")
            worksheet["shots"][sid] = {"skipped": True,
                                       "stills_a": len(a_st),
                                       "stills_b": len(b_st)}
            continue
        if len(a_st) != len(b_st):
            print(f"[ab] {sid}: SKIP (stills a={len(a_st)} != b={len(b_st)})")
            worksheet["shots"][sid] = {"skipped": True, "unequal": True}
            continue
        a_left = rng.random() < 0.5
        pairs = []
        for k in range(len(a_st)):
            pair_path = os.path.join(out, f"{sid}_pair{k}.jpg")
            if a_left:
                pair(a_st[k], b_st[k], pair_path)
            else:
                pair(b_st[k], a_st[k], pair_path)
            pairs.append({"k": k, "a_left": a_left, "image": pair_path,
                          "question": args.pref_question,
                          "answer": None})
            a_left = not a_left      # swap ordering per still (the law)
        mid_a = a_st[len(a_st) // 2]
        mid_b = b_st[len(b_st) // 2]
        worksheet["shots"][sid] = {
            "pairs": pairs,
            "read": {args.label_a: {"image": mid_a,
                                    "question": args.read_question,
                                    "answer": None},
                     args.label_b: {"image": mid_b,
                                    "question": args.read_question,
                                    "answer": None}},
        }
        print(f"[ab] {sid}: {len(pairs)} pairs + 2 readability stills "
              f"-> {out}")
    with open(os.path.join(out, WORKSHEET_NAME), "w") as f:
        json.dump(worksheet, f, indent=1)
    # the answers SKELETON (the U1 finding: the schema was
    # undiscoverable — ship the exact shape, fill it in place)
    skeleton = {"shots": {}}
    n_pairs_total = 0
    for sid, shot in worksheet["shots"].items():
        if shot.get("skipped"):
            continue
        n_pairs_total += len(shot["pairs"])
        skeleton["shots"][sid] = {
            "pairs": {str(p["k"]): None for p in shot["pairs"]},
            "read": {lab: None for lab in shot["read"]},
        }
    apath = os.path.join(out, ANSWERS_NAME)
    with open(apath, "w") as f:
        json.dump(skeleton, f, indent=1)
    if n_pairs_total == 0:
        raise SystemExit(
            f"[ab] REFUSED: zero pairs built from {windows} — no frame "
            f"matched the convention <side_dir>/<shot>/frame_<f:04d>.png"
            f"(.jpg). List the side dirs and check the frame numbers "
            f"(the fractions land at int(f0+(f1-f0)*frac)).")
    print(f"[ab] worksheet -> {os.path.join(out, WORKSHEET_NAME)}")
    print(f"[ab] answers skeleton -> {apath}")
    print(f"[ab] NEXT: look at every pair image; write 'LEFT'/'RIGHT' + "
          f"reason into each pairs[k] entry and the 3-axis scores + any "
          f"defect keywords into each read entry OF {ANSWERS_NAME} "
          f"(bare '4 4 4' scores parse; 'a:4 b:4 c:4' does NOT); then "
          f"run: ab_evaluate.py decide --dir {out}")
    return 0


def cmd_decide(args):
    wpath = os.path.join(args.dir, WORKSHEET_NAME)
    apath = os.path.join(args.dir, ANSWERS_NAME)
    if not os.path.isfile(wpath):
        raise SystemExit(f"no worksheet at {wpath} — run prep first")
    with open(wpath) as f:
        ws = json.load(f)
    if os.path.isfile(apath):
        with open(apath) as f:
            ans = json.load(f)
    else:
        # the in-place worksheet answers are ALSO accepted (the U1
        # finding: prep's old instruction said 'in place' while decide
        # demanded the answers file — both shapes work now)
        ans = {"shots": {}}
        for sid, shot in ws["shots"].items():
            if shot.get("skipped"):
                continue
            ans["shots"][sid] = {
                "pairs": {str(p["k"]): p.get("answer")
                          for p in shot["pairs"]},
                "read": {lab: r.get("answer")
                         for lab, r in shot["read"].items()}}
        print("[ab] no ab_answers.json — using the INLINE worksheet "
              "answers")
    labels = ws["labels"]
    defect_label = labels[ws["defect_side"]]
    result = {"seed": ws["seed"], "labels": labels,
              "windows": ws["windows"], "shots": {}, "rule": {}}
    pref_b = 0
    pref_total = 0
    unanswered = 0
    anatomy_defects = 0
    readability = {"a": [], "b": []}
    for sid, shot in ws["shots"].items():
        if shot.get("skipped"):
            result["shots"][sid] = shot
            continue
        out_shot = {"pref": [], "read": {}, "anatomy": []}
        a_answers = ans.get("shots", {}).get(sid, {})
        for p in shot["pairs"]:
            text = (a_answers.get("pairs", {}).get(str(p["k"]))
                    or a_answers.get("pairs", {}).get(p["k"]))
            if text is None:
                unanswered += 1
                side, build = "?", "?"
            else:
                side = parse_side(text)
                build = {"L": labels["a"] if p["a_left"] else labels["b"],
                         "R": labels["b"] if p["a_left"] else labels["a"]
                         }.get(side, "?")
            out_shot["pref"].append({"k": p["k"], "a_left": p["a_left"],
                                     "side": side, "build": build,
                                     "ans": str(text)[:160]})
            if build == labels["b"]:
                pref_b += 1
            pref_total += 1
        for key in ("a", "b"):
            lab = labels[key]
            text = a_answers.get("read", {}).get(lab)
            if text is None:
                unanswered += 1
                out_shot["read"][lab] = "(unanswered)"
                readability[key].append(0)
                continue
            out_shot["read"][lab] = str(text)[:400]
            parsed = parse_scores(text)
            readability[key].append(parsed)
            # the U1 finding: self-evident score formats silently zeroed
            if str(text).strip() and parsed == 0:
                print(f"[ab] WARNING {sid} read[{lab}]: text present but "
                      f"no 1-5 scores parsed (bare '4 4 4' parses; "
                      f"'a:4 b:4 c:4' does NOT) — counting 0",
                      flush=True)
            if lab == defect_label and any(
                    kw in str(text).lower() for kw in DEFECT_KEYWORDS):
                anatomy_defects += 1
                out_shot["anatomy"].append(str(text)[:200])
        result["shots"][sid] = out_shot
    # the rule inputs (the final call also needs the gate + cost
    # numbers, merged by hand -- kept from the previz contract)
    result["rule"]["pref_b_share"] = pref_b / max(1, pref_total)
    result["rule"]["pref_required"] = 2 / 3
    ma = sum(readability["a"]) / max(1, len(readability["a"]))
    mb = sum(readability["b"]) / max(1, len(readability["b"]))
    result["rule"]["read_a"] = round(ma, 2)
    result["rule"]["read_b"] = round(mb, 2)
    result["rule"]["anatomy_defect_shots"] = anatomy_defects
    result["rule"]["unanswered"] = unanswered
    result["rule"]["gates_green"] = "TODO merge by hand"
    result["rule"]["cost_p95_ratio"] = "TODO merge by hand"
    # the computed verdict (the U1 finding: the last mile was manual)
    if pref_total == 0 or unanswered:
        result["rule"]["verdict"] = "NO_DECISION"
    elif anatomy_defects:
        result["rule"]["verdict"] = "VETO_DEFECTS"
    elif (result["rule"]["pref_b_share"] >= 2 / 3 and mb >= ma):
        result["rule"]["verdict"] = "PREFER_" + labels["b"]
    elif ((1 - result["rule"]["pref_b_share"]) >= 2 / 3 and ma >= mb):
        result["rule"]["verdict"] = "PREFER_" + labels["a"]
    else:
        result["rule"]["verdict"] = "NO_DECISION"
    with open(os.path.join(args.dir, DECISION_NAME), "w") as f:
        json.dump(result, f, indent=1)
    print(f"[ab] preference {labels['b']} {pref_b}/{pref_total} "
          f"({result['rule']['pref_b_share']:.0%}, need >= 67%)")
    print(f"[ab] readability {labels['a']} {ma:.2f} vs "
          f"{labels['b']} {mb:.2f}")
    print(f"[ab] anatomy defect shots ({defect_label}): {anatomy_defects}")
    if unanswered:
        print(f"[ab] WARNING: {unanswered} unanswered item(s) — they "
              f"count as '?' and 0 (fail-closed, never silently dropped)")
    print("[ab] -> " + os.path.join(args.dir, DECISION_NAME))
    return 1 if unanswered else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    pp = sub.add_parser("prep", help="build blind pairs + the worksheet")
    pp.add_argument("--side-a", required=True)
    pp.add_argument("--label-a", default="a")
    pp.add_argument("--side-b", required=True)
    pp.add_argument("--label-b", default="b")
    pp.add_argument("--windows", required=True, help="SHOT:F0:F1 comma list")
    pp.add_argument("--defect-side", choices=("a", "b"), default="b")
    pp.add_argument("--out", default=None)
    pp.add_argument("--seed", type=int, default=4242)
    pp.add_argument("--stills", default="0.2,0.5,0.8")
    pp.add_argument("--pref-question", default=PREF_Q_DEFAULT)
    pp.add_argument("--read-question", default=READ_Q_DEFAULT)
    pp.set_defaults(fn=cmd_prep)
    dp = sub.add_parser("decide", help="validate answers, compute the rule")
    dp.add_argument("--dir", required=True, help="the prep --out directory")
    dp.set_defaults(fn=cmd_decide)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
