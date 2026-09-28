#!/usr/bin/env python3
"""
vlm_critique.py -- Structured VLM critique for rendered images.

Host-side tool (no Blender needed). Wraps `z-ai vision` with critique
prompt templates and returns structured JSON:

  { "kind": "...", "images": [...], "issues": [ {"severity": "P0|P1|P2",
    "description": "..."} ], "suggestions": ["..."], "score": 0-10,
    "raw": "full VLM text" }

WHY THIS EXISTS (lessons from the escape-previz project):
  Bare "look at this image, any problems?" prompts produce noise: the VLM
  guesses the intent, invents floating/penetration claims at low resolution,
  and gives unusable feedback. Structured critique needs:
    1. INTENT: tell the VLM what the shot is SUPPOSED to show. It critiques
       against intent instead of guessing.
    2. VOCABULARY: describe the visual language (color-coding, style,
       scale references) so it interprets what it sees correctly.
    3. ONE CONCERN PER PASS: framing pass, layout pass, lighting pass...
       Multi-pass beats kitchen-sink prompts.
    4. STRUCTURED OUTPUT: severity-tagged issues + concrete fixes.
    5. AESTHETIC CLAIMS ARE TRUSTED, GEOMETRIC CLAIMS GET PROBED:
       composition feedback is VLM-authoritative; "floating/intersecting"
       claims should be verified programmatically (probe scripts) before
       acting on them.
    6. PACK FIRST (R5 doctrine, RESULTS.md): geometry/grounding/count
       questions go to a text-only LLM reading the ascii_vision pack
       (measured tables, no sycophancy); the VLM stays for semantics and
       aesthetics. --with-pack runs BOTH arms in one pass.

Usage:
  # framing critique of a shot still (what the camera work needs)
  python3 scripts/vlm_critique.py --image output/escape/shot_S2.png \
      --kind framing --intent "Side tracking shot: three figures in a
      jeep (BLUE driver, RED passenger, AMBER gunner) flee a zombie horde;
      chase pack should be visible behind" --out output/vlm/S2.json

  # layout critique of a 4-angle contact sheet
  python3 scripts/vlm_critique.py --image output/my_scene/grid.png \
      --kind layout --out output/vlm/layout.json

  # motion critique of a keyframe contact sheet (12 frames labeled)
  python3 scripts/vlm_critique.py --image output/escape/motion.png \
      --kind motion --out output/vlm/motion.json

  # custom question
  python3 scripts/vlm_critique.py --image still.png \
      --custom "Is the muzzle flash visible near the AMBER figure?" \
      --out output/vlm/custom.json

  # pack-first two-arm pass (2 API calls): pack arm answers geometry,
  # VLM pass kept as semantic/aesthetic second opinion
  python3 scripts/vlm_critique.py --image output/escape/shot_S2.png \
      --kind framing --with-pack --intent "..." --out output/vlm/S2.json

  # print the exact prompts per arm and exit; ZERO api calls
  python3 scripts/vlm_critique.py --image shot.png --kind framing \
      --with-pack --dry-run

--with-pack output keeps today's top-level keys ("parsed" switches to the
pack arm's parse, noted in parsed_source; "raw" stays the VLM raw text)
and adds:
  arms: {"pack": <pack-arm parse>, "vlm": <vlm-arm parse>},
  pack_raw: <chat raw text>,
  geometry_policy: "geometric claims resolve to the pack arm; ..."
"""
import argparse
import json
import os
import re
import subprocess
import sys

# ---------------------------------------------------------------------------
# Prompt templates. Each focuses on ONE concern (lesson 3).
# ---------------------------------------------------------------------------

TEMPLATES = {
    "framing": """You are a cinematography reviewer for a 3D previz render.

{intent_block}

CRITIQUE THE FRAMING AND COMPOSITION ONLY. Do not comment on texture detail or render quality.
Answer with STRICT JSON (no markdown fences, no prose outside JSON):
{{
 "subjects": [{{"name": "...", "visible": true, "screen_position": "left|center-left|center|center-right|right|edge|offscreen", "size_in_frame": "too-small|small|good|large|too-large"}}],
 "issues": [{{"severity": "P0-blocks-understanding|P1-hurts-read|P2-polish", "description": "..."}}],
 "balance": "one sentence on frame balance / wasted space / horizon",
 "score": 0-10,
 "fix": "ONE concrete camera change (position/lens/angle/aim) if score<8, else 'none'"
}}""",

    "layout": """You are a 3D scene layout inspector reviewing a multi-angle contact sheet of one scene.

{intent_block}

CRITIQUE LAYOUT ONLY (object placement, grounding, intersections, scale believability).
If a top view exists, use it for placement. Answer with STRICT JSON (no fences):
{{
 "issues": [{{"severity": "P0|P1|P2", "type": "floating|intersecting|misplaced|scale|other", "description": "name the object and the view"}}],
 "score": 0-10,
 "fix": "one concrete change if score<8, else 'none'"
}}""",

    "motion": """You are an animation reviewer. The image is a keyframe contact sheet: frames sampled in time order, labeled with frame numbers.

{intent_block}

CRITIQUE MOTION ONLY: does the action arc read left-to-right / early-to-late? Does the story beat land? Are motion continuities broken (objects teleporting, popping, sliding without cause)? Answer with STRICT JSON (no fences):
{{
 "reads": "one sentence: does the intended action read?",
 "issues": [{{"severity": "P0|P1|P2", "frame": "frame number or range", "description": "..."}}],
 "score": 0-10,
 "fix": "one concrete timing/animation change if score<8, else 'none'"
}}""",

    "lighting": """You are a lighting reviewer for a 3D previz render.

{intent_block}

CRITIQUE LIGHTING/EXPOSURE ONLY: over/under-exposure, crushed blacks, blown highlights, color cast, readability of subjects against background, silhouette separation. Answer with STRICT JSON (no fences):
{{
 "issues": [{{"severity": "P0|P1|P2", "description": "..."}}],
 "exposure": "one sentence",
 "score": 0-10,
 "fix": "one concrete light change if score<8, else 'none'"
}}""",

    "readback": """You are a precise scene describer. Describe ONLY what is visibly present in this image, in terms of the known vocabulary below. Do NOT guess, do NOT infer intent, do NOT flag problems.

{intent_block}

Answer with STRICT JSON (no fences):
{{
 "objects_seen": ["..."],
 "colors_present": ["..."],
 "counts": {{"name": approximate count}},
 "text_or_labels": ["..."]
}}""",
}

DEFAULT_VOCAB = """KNOWN VISUAL VOCABULARY: low-poly previz, flat-ish colors. Humans are capsule
figures color-coded BLUE (driver), RED (female passenger), AMBER (gunner). Zombies are
green-gray capsules with tiny red glowing eyes. The vehicle is a khaki boxy jeep with a
tube cage. Street is gray asphalt with buildings/wrecks. Approximate human height 1.7 m."""


def _intent_block(intent, vocab):
    parts = []
    if intent:
        parts.append("SHOT/SCENE INTENT (what this SHOULD show): " + intent)
    if vocab:
        parts.append(vocab)
    return "\n\n".join(parts) if parts else "(no intent given - describe generally)"


# --- pack arm (R5 D3): text-only LLM reading the ascii_vision pack ---------
# Doctrine (RESULTS.md): the pack is authoritative for geometry; the VLM
# for semantics/aesthetics. Explicitly NOT default-on: doubles API cost.
GEOMETRY_POLICY = ("geometric claims resolve to the pack arm; "
                   "semantic/aesthetic claims resolve to the VLM arm")

# ONE constant so the pack-arm contract is reviewable in a single place:
# the framing paragraph replaces the image-seeing "You are a ... reviewer
# for a 3D previz render" opener, and the grounding rule is the
# anti-hallucination guard (R4: the VLM arm cites evidence that does not
# exist in its input -- a pack reader must cite the table or abstain).
PACK_TEMPLATE_ADAPTER = """\
You are reviewing a TEXT RENDERING (ASCII vision pack) of a 3D previz render \
-- the pack is generated programmatically from the image pixels; component \
tables are measured, not guessed.

EVERY geometric claim (position, size, count, floating, intersecting, \
edge-cut) MUST cite the component id(s) and/or coordinate numbers from the \
pack tables that support it. If the tables do not contain evidence for a \
claim, state it as 'not determinable from the pack' instead of guessing.
"""

# Marker between prompt prose and pack body (distinct from the pack's own
# "== ASCII-VISION PACK ==" header so nesting stays unambiguous).
PACK_MARKER = "== ASCII VISION PACK (text readout of the image; measured) =="


def packify_prompt(kind_prompt, pack_text, kind_used=None):
    """Adapt an image-seeing kind template into a pack-reading prompt.

    (a) swaps the "You are ..." image framing for PACK_TEMPLATE_ADAPTER,
    (c) thereby adds the cite-or-abstain grounding rule, and (b) appends
    the pack after a clear marker line. Custom prompts keep their first
    line (the framing swap only applies to the built-in kind templates)."""
    adapter = PACK_TEMPLATE_ADAPTER.strip()
    lines = kind_prompt.split("\n")
    if kind_used != "custom" and lines and lines[0].startswith("You are"):
        lines[0] = adapter  # framing swap rides with the grounding rule
        body = "\n".join(lines)
    else:  # custom prompts: prepend adapter, keep every word of the brief
        body = adapter + "\n\n" + kind_prompt
    return (body + "\n\n" + PACK_MARKER + "\n"
            + pack_text.strip())


def _extract_json_blob(text):
    """Find the outermost {...} and json.loads it, leniently."""
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                blob = text[start:i + 1]
                try:
                    return json.loads(blob)
                except json.JSONDecodeError:
                    try:
                        return json.loads(
                            blob.replace(",}", "}").replace(",]", "]"))
                    except json.JSONDecodeError:
                        return None
    return None


def _parse_llm_json(raw):
    """Shared unwrap+parse for z-ai CLI output (chat and vision).

    The CLI may print the raw API envelope {"choices":[{"message":...
    {"content": "<inner text>"}}]}. Unwrap it first, then parse the inner
    JSON from the content string."""
    envelope = _extract_json_blob(raw)
    content_text = raw
    if isinstance(envelope, dict) and "choices" in envelope:
        try:
            content_text = envelope["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            content_text = raw
    elif isinstance(envelope, dict) and "content" in envelope:
        content_text = envelope["content"]

    parsed = _extract_json_blob(content_text)
    # strip markdown fences if the model added them anyway
    if parsed is None and "```" in content_text:
        for seg in content_text.split("```"):
            seg = seg.strip()
            if seg.startswith("json"):
                seg = seg[4:].strip()
            parsed = _extract_json_blob(seg)
            if parsed is not None:
                break
    return parsed


def run_vlm(prompt, images, out_json=None, thinking=False):
    """Call z-ai vision CLI. Returns (parsed_dict, raw_text)."""
    cmd = ["z-ai", "vision", "-p", prompt]
    for img in images:
        cmd += ["-i", img]
    if thinking:
        cmd.append("-t")
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr[-500:])
        raise RuntimeError("z-ai vision CLI failed (rc=%d)" % proc.returncode)
    raw = proc.stdout.strip()
    return _parse_llm_json(raw), raw


def run_chat(prompt, out_json=None):
    """Call z-ai chat CLI (text-only). Returns (parsed_dict, raw_text).

    The pack arm's eye (D3); out_json kept for symmetry with run_vlm.
    Timeout 300 s: battery_v2's chat-on-pack calls budgeted 300 s."""
    cmd = ["z-ai", "chat", "-p", prompt]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr[-500:])
        raise RuntimeError("z-ai chat CLI failed (rc=%d)" % proc.returncode)
    raw = proc.stdout.strip()
    return _parse_llm_json(raw), raw


def build_packs(images, pack_cols):
    """Generate the ASCII vision pack text for the pack arm, in-process.

    Lazy import: ascii_vision.build_pack_from_path is a mandated refactor
    landing in parallel (R5 spec D3) -- importing here keeps this module
    importable/testable even while that refactor is in flight."""
    try:
        from ascii_vision import build_pack_from_path
    except ImportError as e:
        raise SystemExit(
            "ascii_vision.build_pack_from_path not available (%s); the "
            "in-process pack needs that entry point. Equivalent CLI: "
            "python3 scripts/ascii_vision.py <img> --cols %d --components "
            "--tiles 2 --no-header" % (e, pack_cols))
    # default-flag pack (scene palette): R5 pack_accuracy measures THESE
    packs = []
    for img in images:
        try:
            packs.append("== PACK FOR IMAGE: %s ==\n%s" % (
                img, build_pack_from_path(img, cols=pack_cols, tiles=2,
                                          components=True, no_header=True,
                                          palette="scene")))
        except ValueError as e:  # e.g. pack_cols > 160 guard
            raise SystemExit("--with-pack: %s (valid --pack-cols: 40-160)" % e)
    return "\n\n".join(packs)


def build_prompt(kind, intent="", custom=None, vocab=None):
    """Return (kind_used, prompt) -- shared by critique() and --dry-run."""
    vocab = vocab if vocab is not None else DEFAULT_VOCAB
    if custom:
        return "custom", custom + ("\n\n" + vocab if vocab else "")
    if kind not in TEMPLATES:
        raise SystemExit("unknown --kind %r (choose from %s or use --custom)"
                         % (kind, sorted(TEMPLATES)))
    return kind, TEMPLATES[kind].format(
        intent_block=_intent_block(intent, vocab))


def _normalize_issues(parsed):
    """Normalize issue severities in place (P0-blocks-understanding -> P0)."""
    if parsed:
        for iss in parsed.get("issues", []):
            sev = str(iss.get("severity", "P2"))
            iss["severity"] = sev.split("-")[0]


def critique(images, kind, intent="", custom=None, vocab=None, out=None,
             thinking=False, with_pack=False, pack_cols=96):
    kind_used, prompt = build_prompt(kind, intent, custom, vocab)

    if with_pack:
        # Pack arm FIRST (doctrine: pack reads geometry first; the VLM is
        # the semantic/aesthetic second opinion -- RESULTS.md "Doctrine").
        pack_parsed, pack_raw = run_chat(
            packify_prompt(prompt, build_packs(images, pack_cols), kind_used))
        vlm_parsed, raw = run_vlm(prompt, images, thinking=thinking)
        _normalize_issues(pack_parsed)
        _normalize_issues(vlm_parsed)
        # pack is authoritative for the geometry kinds this flag targets,
        # so top-level parsed points at the pack arm (parsed_source says so)
        result = {
            "kind": kind_used,
            "images": images,
            "intent": intent,
            "parsed": pack_parsed,
            "raw": raw,
            "arms": {"pack": pack_parsed, "vlm": vlm_parsed},
            "pack_raw": pack_raw,
            "geometry_policy": GEOMETRY_POLICY,
            "parsed_source": "pack",
        }
    else:
        parsed, raw = run_vlm(prompt, images, thinking=thinking)
        _normalize_issues(parsed)
        result = {
            "kind": kind_used,
            "images": images,
            "intent": intent,
            "parsed": parsed,
            "raw": raw,
        }
    if out:
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        with open(out, "w") as f:
            json.dump(result, f, indent=1)
    return result


# component ids cited in a pack-arm issue description ("id 2", "ids 2, 5",
# "component 3") -- surfaced as a line prefix in summarize()
_CITE_RE = re.compile(r"\b(?:ids?|components?)\s*[:#]?\s*([0-9][0-9,\s]*)",
                      re.IGNORECASE)


def _cited_ids(text):
    ids, seen = [], set()
    for m in _CITE_RE.finditer(text or ""):
        for tok in m.group(1).replace(",", " ").split():
            if tok not in seen:
                seen.add(tok)
                ids.append(tok)
    return ids


def _arm_lines(tag, parsed, raw=None, is_pack=False):
    if not parsed:
        head = ("UNPARSED: " + (raw or "")[:200]) if raw else "UNPARSED"
        return ["  %s %s" % (tag, head)]
    lines = []
    for iss in parsed.get("issues", []):
        t = tag
        if is_pack:  # surface the citations the grounding rule demanded
            ids = _cited_ids(iss.get("description", ""))
            if ids:
                t = "%s ids:%s" % (tag, ",".join(ids))
        lines.append("  %s [%s] %s" % (t, iss.get("severity", "?"),
                                       iss.get("description", "")))
    if "reads" in parsed:
        lines.insert(0, "  %s reads: %s" % (tag, parsed["reads"]))
    if "score" in parsed:
        lines.append("  %s score: %s" % (tag, parsed["score"]))
    if "fix" in parsed:
        lines.append("  %s fix: %s" % (tag, parsed["fix"]))
    if not lines and parsed:  # parsed but schema-less (readback kinds etc.)
        lines.append("  %s %s" % (tag, json.dumps(parsed)[:200]))
    return lines


def summarize(result):
    if "arms" in result:  # --with-pack run: both arms, tagged
        lines = []
        for arm in ("pack", "vlm"):
            raw = result.get("pack_raw" if arm == "pack" else "raw")
            lines += _arm_lines("[%s]" % arm, result["arms"].get(arm), raw,
                                is_pack=(arm == "pack"))
        return "\n".join(lines) if lines else "UNPARSED"
    p = result.get("parsed")
    if not p:
        return "UNPARSED: " + (result["raw"] or "")[:300]
    lines = []
    for iss in p.get("issues", []):
        lines.append("  [%s] %s" % (iss.get("severity", "?"),
                                    iss.get("description", "")))
    if "score" in p:
        lines.append("  score: %s" % p["score"])
    if "fix" in p:
        lines.append("  fix: %s" % p["fix"])
    if "reads" in p:
        lines.insert(0, "  reads: %s" % p["reads"])
    return "\n".join(lines) if lines else json.dumps(p)[:300]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--image", "-i", action="append", required=True,
                    help="image path (repeatable)")
    ap.add_argument("--kind", "-k", default="framing",
                    choices=sorted(TEMPLATES))
    ap.add_argument("--intent", default="",
                    help="what the shot/scene SHOULD show (critiqued against this)")
    ap.add_argument("--vocab", default=None,
                    help="override visual-vocabulary description")
    ap.add_argument("--custom", default=None,
                    help="custom prompt; bypasses --kind")
    ap.add_argument("--out", "-o", default=None, help="output JSON path")
    ap.add_argument("--thinking", "-t", action="store_true")
    ap.add_argument("--quiet", "-q", action="store_true")
    ap.add_argument("--with-pack", action="store_true",
                    help="add a text-only pack arm (ascii_vision pack via "
                         "z-ai chat) run BEFORE the VLM second opinion; "
                         "geometry claims resolve to the pack. 2 API calls "
                         "-- the operator decides per pass")
    ap.add_argument("--pack-cols", type=int, default=96,
                    help="pack width for --with-pack (default 96)")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the exact prompts per arm and exit 0; "
                         "zero subprocess calls (zero-API test path)")
    args = ap.parse_args()

    for img in args.image:
        if not os.path.exists(img):
            raise SystemExit("missing image: " + img)

    if args.dry_run:
        # zero-API path: render exactly what would be sent, send nothing
        kind_used, prompt = build_prompt(args.kind, args.intent, args.custom,
                                         args.vocab)
        if args.with_pack:
            print("=== PROMPT (arm: pack) ===")
            print(packify_prompt(prompt, build_packs(args.image,
                                                     args.pack_cols),
                                 kind_used))
            print()
        print("=== PROMPT (arm: vlm) ===")
        print(prompt)
        return

    res = critique(args.image, args.kind, args.intent, args.custom,
                   args.vocab, args.out, args.thinking,
                   with_pack=args.with_pack, pack_cols=args.pack_cols)
    if not args.quiet:
        print(summarize(res))


if __name__ == "__main__":
    main()
