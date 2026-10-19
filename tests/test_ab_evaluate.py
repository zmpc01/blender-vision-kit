"""test_ab_evaluate.py — the blind A/B native loop + canon battery (s24).

Rows (host mode — no bpy; the lanes are bpy-free by design):
  A1  prep: builds stills + BOTH-ordering pairs + the worksheet; the
      swap law holds (a_left alternates per still); missing/unequal
      sides skip LOUD into the worksheet, never crash.
  A2  decide: planted answers -> the rule verdict (pref share,
      readability means, defect count); unanswered items count
      fail-closed ('?'/0 + exit 1), never silently dropped.
  A3  the swap law's PURPOSE: a preference that flips with ordering
      nets out (planted flip-flop -> 50%, below the 2/3 rule).
  A4  previz_canon: content_hash stability (provenance stripped) +
      the allow_nan refusal.

Run: python3 tests/test_ab_evaluate.py
Exit: 0 PASS / 1 FAIL (check()-raises scoring, the s23 law).
"""
import json
import os
import sys
import tempfile
import traceback

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, ".."))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import ab_evaluate as ab   # noqa: E402
import previz_canon as pc  # noqa: E402

FAIL = []
ROWS = {}


def check(tag, got, want):
    if got != want:
        FAIL.append(f"{tag}: got {got!r} want {want!r}")
        raise AssertionError(f"{tag}: got {got!r} want {want!r}")


def row(rid, fn):
    n0 = len(FAIL)
    try:
        fn()
        ROWS[rid] = "pass" if len(FAIL) == n0 else "fail"
    except Exception as e:  # noqa: BLE001
        if len(FAIL) == n0:
            FAIL.append(f"{rid}: UNEXPECTED {type(e).__name__}: {e}")
        ROWS[rid] = "fail"
        if os.environ.get("KIT_TRACEBACK"):
            traceback.print_exc()


def _frame_tree(root, label, shots, size=(64, 48)):
    """A tiny frame tree: <root>/<shot>/frame_<f:04d>.png with a
    per-side SOLID COLOR (so pairs are visually distinct — the fixture
    is eye-checkable)."""
    from PIL import Image
    colors = {"a": (200, 40, 40), "b": (40, 60, 200)}
    for sid, frames in shots.items():
        d = os.path.join(root, sid)
        os.makedirs(d, exist_ok=True)
        for f in frames:
            Image.new("RGB", size, colors[label]).save(
                os.path.join(d, f"frame_{f:04d}.png"))


def _setup():
    tmp = tempfile.mkdtemp(prefix="abtest_")
    a = os.path.join(tmp, "build_a")
    b = os.path.join(tmp, "build_b")
    # S1 frames cover BOTH grids used here: the default 3-frac on 10:30
    # (14/20/26) and A3's 4-frac 0.1/0.3/0.7/0.9 (12..28)
    _frame_tree(a, "a", {"S1": [14, 18, 20, 22, 26], "S2": [5, 6]})
    _frame_tree(b, "b", {"S1": [14, 18, 20, 22, 26], "S2": [5, 6]})
    return tmp, a, b


def a1():
    tmp, a, b = _setup()
    out = os.path.join(tmp, "eval")
    rc = ab.main(["prep", "--side-a", a, "--label-a", "capsule",
                  "--side-b", b, "--label-b", "ual",
                  "--windows", "S1:10:30", "--out", out, "--seed", "7"])
    check("A1 prep exit", rc, 0)
    ws = json.load(open(os.path.join(out, "ab_worksheet.json")))
    check("A1 worksheet labels", ws["labels"], {"a": "capsule", "b": "ual"})
    shot = ws["shots"]["S1"]
    check("A1 three pairs", len(shot["pairs"]), 3)
    check("A1 swap law alternates",
          [p["a_left"] for p in shot["pairs"]],
          [shot["pairs"][0]["a_left"],
           not shot["pairs"][0]["a_left"],
           shot["pairs"][0]["a_left"]])
    check("A1 pair images exist",
          all(os.path.isfile(p["image"]) for p in shot["pairs"]), True)
    check("A1 blind images on disk",
          any(os.path.isfile(os.path.join(out, f)) for f in
              os.listdir(out) if f.endswith(".png")), True)
    # missing side -> the U1 teacher-grade refusal when NO window pairs
    # (zero-stills silently exiting 0 was the U1 finding), and a
    # PARTIAL skip stays loud in the worksheet with exit 0
    empty = os.path.join(tmp, "empty_side")
    os.makedirs(empty)
    try:
        ab.main(["prep", "--side-a", a, "--side-b", empty,
                 "--windows", "S2:5:7", "--out", os.path.join(tmp, "e2"),
                 "--seed", "7"])
        check("A1 zero-pairs refused", "no-exception", "SystemExit")
    except SystemExit as e:
        check("A1 refusal names the convention",
              "frame_<f:04d>.png" in str(e), True)
    # partial: S1 present on BOTH sides, S2 missing on side b ->
    # S2 skips loudly in the worksheet, S1 pairs, exit 0
    partial = os.path.join(tmp, "partial_side")
    _frame_tree(partial, "b", {"S1": [14, 20, 26]})
    rc = ab.main(["prep", "--side-a", a, "--side-b", partial,
                  "--windows", "S1:10:30,S2:5:7",
                  "--out", os.path.join(tmp, "e3"), "--seed", "7"])
    ws3 = json.load(open(os.path.join(tmp, "e3", "ab_worksheet.json")))
    check("A1 partial skip is loud in the worksheet",
          ws3["shots"]["S2"].get("skipped"), True)
    check("A1 S1 still pairs", len(ws3["shots"]["S1"]["pairs"]), 3)
    check("A1 partial-skip prep exits 0", rc, 0)


def _answer(ws, pref_side, read_scores, defect_text="clean"):
    """Fill answers deterministically: pref_side 'L'/'R' for EVERY pair;
    readability scores into both sides."""
    labels = ws["labels"]
    answers = {"shots": {}}
    for sid, shot in ws["shots"].items():
        if shot.get("skipped"):
            continue
        answers["shots"][sid] = {
            "pairs": {str(p["k"]): f"{pref_side} because" for p
                      in shot["pairs"]},
            "read": {labels["a"]: read_scores, labels["b"]: defect_text},
        }
    return answers


def a2():
    tmp, a, b = _setup()
    out = os.path.join(tmp, "eval2")
    ab.main(["prep", "--side-a", a, "--label-a", "capsule",
             "--side-b", b, "--label-b", "ual",
             "--windows", "S1:10:30,S2:5:7", "--out", out, "--seed", "7"])
    ws = json.load(open(os.path.join(out, "ab_worksheet.json")))
    # find which physical side label_b sits on per pair — answer 'R'
    # when b is right, 'L' when b is left → b gets 100% preference
    answers = {"shots": {}}
    for sid, shot in ws["shots"].items():
        if shot.get("skipped"):
            continue
        answers["shots"][sid] = {"pairs": {}, "read": {}}
        for p in shot["pairs"]:
            b_on_right = ((p["a_left"] and False) or
                          ((not p["a_left"]) and True))
            # a_left=True -> a is LEFT, b is RIGHT -> answer RIGHT
            answers["shots"][sid]["pairs"][str(p["k"])] = \
                "RIGHT because" if p["a_left"] else "LEFT because"
        answers["shots"][sid]["read"] = {
            ws["labels"]["a"]: "(a) 4 (b) 4 (c) 4. no defects.",
            ws["labels"]["b"]: "(a) 5 (b) 5 (c) 5. clean"}
    with open(os.path.join(out, "ab_answers.json"), "w") as f:
        json.dump(answers, f)
    rc = ab.main(["decide", "--dir", out])
    dec = json.load(open(os.path.join(out, "ab_decision.json")))
    check("A2 decide exit", rc, 0)
    check("A2 pref share 100%", dec["rule"]["pref_b_share"], 1.0)
    check("A2 readability means", (dec["rule"]["read_a"],
                                   dec["rule"]["read_b"]), (4.0, 5.0))
    check("A2 no unanswered", dec["rule"]["unanswered"], 0)
    # defect keyword fires on the DEFECT side only (b by default)
    answers["shots"]["S1"]["read"][ws["labels"]["b"]] = \
        "(a) 5 (b) 5 (c) 5. the arm looks severed at the elbow"
    with open(os.path.join(out, "ab_answers.json"), "w") as f:
        json.dump(answers, f)
    ab.main(["decide", "--dir", out])
    dec = json.load(open(os.path.join(out, "ab_decision.json")))
    check("A2 defect counted", dec["rule"]["anatomy_defect_shots"], 1)
    # unanswered -> fail-closed exit 1
    del answers["shots"]["S1"]["pairs"]["0"]
    with open(os.path.join(out, "ab_answers.json"), "w") as f:
        json.dump(answers, f)
    rc = ab.main(["decide", "--dir", out])
    dec = json.load(open(os.path.join(out, "ab_decision.json")))
    check("A2 unanswered exit 1", rc, 1)
    check("A2 unanswered counted", dec["rule"]["unanswered"], 1)


def a3():
    """The swap law's purpose: a flip-flop 'preference' (answers follow
    the POSITION, not the content) nets to 50% — below the 2/3 rule."""
    tmp, a, b = _setup()
    out = os.path.join(tmp, "eval3")
    ab.main(["prep", "--side-a", a, "--side-b", b,
             "--windows", "S1:10:30", "--out", out, "--seed", "7",
             "--stills", "0.2,0.4,0.6,0.8"])  # 4 pairs: the swap makes
    # an always-RIGHT position bias net to exactly 50%
    ws = json.load(open(os.path.join(out, "ab_worksheet.json")))
    answers = {"shots": {}}
    # always answer RIGHT — half the pairs have b on the right, half on
    # the left (the swap) → b share ≈ 50% regardless of content
    for sid, shot in ws["shots"].items():
        if shot.get("skipped"):
            continue
        answers["shots"][sid] = {
            "pairs": {str(p["k"]): "RIGHT because" for p in shot["pairs"]},
            "read": {ws["labels"]["a"]: "(a) 3 (b) 3 (c) 3 x",
                     ws["labels"]["b"]: "(a) 3 (b) 3 (c) 3 x"}}
    with open(os.path.join(out, "ab_answers.json"), "w") as f:
        json.dump(answers, f)
    ab.main(["decide", "--dir", out])
    dec = json.load(open(os.path.join(out, "ab_decision.json")))
    check("A3 position-bias nets out", 0.3 <= dec["rule"]["pref_b_share"]
          <= 0.7, True)
    check("A3 below the rule threshold",
          dec["rule"]["pref_b_share"] < dec["rule"]["pref_required"], True)


def a4():
    payload = {"generated_at": "t1", "git_sha": "aaa", "revision": 3,
               "content_sha256": "x", "shots": [{"id": "S1"}],
               "fps": 30}
    h1 = pc.content_hash(payload)
    payload["generated_at"] = "t2"
    payload["revision"] = 4
    check("A4 hash stable across provenance", pc.content_hash(payload), h1)
    payload["shots"][0]["id"] = "S2"
    check("A4 hash moves with content", pc.content_hash(payload) != h1,
          True)
    try:
        pc.content_hash({"bad": float("nan")})
        check("A4 NaN refused", "no-exception", "ValueError")
    except ValueError:
        pass


def main() -> int:
    print("[ab-eval-test] battery start", flush=True)
    for rid, fn in (("A1", a1), ("A2", a2), ("A3", a3), ("A4", a4)):
        row(rid, fn)
        print(f"[row] {rid}: {ROWS[rid]}", flush=True)
    n_fail = sum(1 for v in ROWS.values() if v == "fail")
    if FAIL:
        print(f"[ab-eval-test] FAILURES: {FAIL}", flush=True)
    if n_fail:
        return 1
    print("[ab-eval-test] ALL PASS", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
