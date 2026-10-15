# test_s18_wave_d.py — session-18 Wave-D fix regressions (MIXED).
#
# Pure-python checks run under ANY python3; the bpy-importing modules
# (blender_kit/__init__.py and export_previz_package.py import bpy at
# TOP LEVEL — no import guard) are guarded, and under a plain python3
# those sections degrade to "(source)" textual fallbacks + SKIP lines.
# The battery runs this suite UNDER BLENDER (blrun), so the behavioral
# versions are what the battery exercises.
#
# Covers the wave-1 audit's wave-D rows (docs/audit_s18/wave1_triage.md):
#   D1  agent_server: ThreadingMixIn server (SSE connect-first deadlock).
#   D3  blender_kit._resolve_bpy_op / filter_rna_kwargs: op_id is
#       LOAD-BEARING (glTF kwargs survive; was hardcoded to usd_export).
#   D4  export_previz_package._parity_count_mismatches /
#       _parity_scalar_mismatches: per-collection row-count + scalar
#       parity (was key-presence only).
#   D5  gate-5 root-existence de-tautologized: _gate5_root_problems
#       cross-checks the module's CAST registry (its own docstring
#       names THIS file as its unit-test home).
#   D6  encode_deliverable.sh: pipefail + post-encode existence/>1KB
#       abort (ffmpeg's exit used to be masked by the tail pipe).
#   D7  encode_deliverable.sh: mux_dialog.sh call guarded (WARN, not
#       exit 127 — the script is not in-tree).
#   D8  _latest_scene_module: generic scene_*.py family scan with
#       template/demo/fixture exclusions + --allow-stale flag.
#   D9  build_sfx.build rejects negative frames BEFORE the decoder
#       (CPython negative-slice wraparound); gate-15 twin textual.
#   D10 agent_server._watcher_transition two-poll size-stability
#       (bonus: the function's own docstring names this file).
#   D12 blender_kit._write_metadata writes scene.json (the live
#       viewer's Scene tab no longer 404s).
#
# Honesty convention: check names carrying "(source)" assert SOURCE
# TEXT, not behavior; everything else is a live behavioral call.
#
# Run (battery): blrun.sh --background --python tests/test_s18_wave_d.py
# Run (quick, no bpy): python3 tests/test_s18_wave_d.py  — textual
# fallbacks + SKIP lines; still ends with the ALL PASS marker iff green.
# Marker (grepped by scripts/suite_runner.sh):
#   "[S18D] ALL PASS (N checks)"

import inspect
import json
import os
import socketserver
import subprocess
import sys
import tempfile
import types

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SCRIPTS = os.path.join(REPO, "scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

PASS = []
FAIL = []
SKIPPED = []


def check(name, cond, detail=""):
    tag = "ok" if cond else "FAIL"
    print(f"[S18D] {name}: {tag}" + (f" — {detail}" if detail and not cond else ""))
    (PASS if cond else FAIL).append(name)


def skip(name, detail=""):
    print(f"[S18D] {name}: SKIP — {detail}")
    SKIPPED.append(name)


def _src(rel):
    with open(os.path.join(REPO, rel), encoding="utf-8") as f:
        return f.read()


try:
    import bpy                      # noqa: F401
    HAVE_BPY = True
except Exception:
    HAVE_BPY = False

# blender_kit and export_previz_package import bpy at top level — under
# a plain python3 both imports fail and the guarded sections below fall
# back to source asserts.
KIT = None
if HAVE_BPY:
    try:
        import blender_kit as KIT   # noqa: F401
    except Exception:
        KIT = None
EPP = None
if HAVE_BPY:
    try:
        import export_previz_package as EPP   # noqa: F401
    except Exception:
        EPP = None

# ===========================================================================
# D6/D7 — encode_deliverable.sh (pure: bash -n + source asserts)
# ===========================================================================
ENC = os.path.join(SCRIPTS, "encode_deliverable.sh")
r = subprocess.run(["bash", "-n", ENC], capture_output=True, text=True)
check("D6/D7.bash_syntax_ok", r.returncode == 0, r.stderr[:200])
enc_src = _src("scripts/encode_deliverable.sh")
check("D6 (source) pipefail_set", "set -euo pipefail" in enc_src,
      "ffmpeg's exit was masked by the tail pipe without pipefail")
check("D6 (source) post_encode_size_abort",
      '-f "$OUT/anim.mp4"' in enc_src and "1024" in enc_src,
      "no existence/>1KB abort after the encode")
check("D7 (source) mux_dialog_guarded",
      "[[ -f scripts/mux_dialog.sh ]]" in enc_src and "WARN" in enc_src,
      "mux_dialog.sh call must WARN, not die with exit 127")

# ===========================================================================
# D1 — agent_server threading (agent_server.py is stdlib-only: pure import)
# ===========================================================================
import agent_server                   # noqa: E402

srv_cls = getattr(agent_server, "ThreadedTCPServer", None)
check("D1a.threaded_server_class",
      srv_cls is not None
      and issubclass(srv_cls, socketserver.ThreadingMixIn)
      and issubclass(srv_cls, socketserver.TCPServer),
      "ThreadedTCPServer must mix ThreadingMixIn into TCPServer")
check("D1b.daemon_threads", srv_cls is not None
      and srv_cls.daemon_threads is True,
      "daemon_threads keeps SSE-tied shutdown instant")
main_src = inspect.getsource(agent_server.main)
check("D1 (source) main_uses_threaded_server",
      "ThreadedTCPServer((" in main_src
      and "socketserver.TCPServer((" not in main_src,
      "main() must instantiate the threaded subclass, not the bare TCPServer")

# ===========================================================================
# D10 — agent_server._watcher_transition (pure; docstring names this file)
# ===========================================================================
fire, ann = agent_server._watcher_transition(None, None, (1.0, 10))
check("D10a.first_poll_is_baseline", fire is False and ann is None,
      f"fire={fire} announced={ann}")
fire, ann = agent_server._watcher_transition((2.0, 99), (1.0, 10), (2.0, 99))
check("D10b.two_agreeing_polls_fire", fire is True and ann == (2.0, 99),
      f"fire={fire} announced={ann}")
fire, ann = agent_server._watcher_transition((1.0, 10), (1.0, 10), (2.0, 55))
check("D10c.mid_copy_size_mismatch_held", fire is False and ann == (1.0, 10),
      f"fire={fire} announced={ann} (size moved between polls)")
fire, ann = agent_server._watcher_transition((2.0, 99), (2.0, 99), (2.0, 99))
check("D10d.no_refire_on_announced_state", fire is False and ann == (2.0, 99),
      f"fire={fire} announced={ann}")

# ===========================================================================
# D9 — build_sfx negative-frame rejection (build_sfx.py is numpy-only: pure)
# ===========================================================================
try:
    import build_sfx                # noqa: E402
    HAVE_SFX = True
except Exception:
    HAVE_SFX = False

if HAVE_SFX:
    events = {"fps": 24, "events": [{"name": "door_slam", "frame": -5}]}
    with tempfile.TemporaryDirectory() as td:
        ev_path = os.path.join(td, "sfx_events.json")
        out_wav = os.path.join(td, "sfx.wav")
        with open(ev_path, "w", encoding="utf-8") as f:
            json.dump(events, f)
        try:
            build_sfx.build(ev_path, out_wav)
            check("D9a.negative_frame_rejected", False,
                  "frame=-5 passed the decoder boundary")
        except ValueError as e:
            check("D9a.negative_frame_rejected",
                  "negative" in str(e) and
                  ("gate 15" in str(e) or "wrap" in str(e)),
                  str(e)[:130])
else:
    skip("D9a.negative_frame_rejected", "build_sfx (numpy) unavailable")

# gate-15 twin (the exporter-side rejection is inline in main() — textual)
epp_src = _src("scripts/export_previz_package.py")
check("D9 (source) gate15_rejects_negative_frames",
      "'frame' is negative" in epp_src and "sfx" in epp_src.lower(),
      "gate 15 must name the negative frame and the wraparound class")

# ===========================================================================
# D3 — filter_rna_kwargs / _resolve_bpy_op (bpy-guarded: behavioral under
# blender; source fallback under plain python3)
# ===========================================================================
if KIT is not None:
    # legacy bare alias resolves through _RNA_OP_ALIASES
    # (s18 fix: RNA types expose .bl_rna.identifier — there is no .idname)
    check("D3a.legacy_alias_resolves",
          KIT._resolve_bpy_op("usd_export").get_rna_type().bl_rna.identifier ==
          bpy.ops.wm.usd_export.get_rna_type().bl_rna.identifier)
    check("D3b.module_path_resolves",
          KIT._resolve_bpy_op("wm.read_homefile").get_rna_type()
          .bl_rna.identifier.startswith("WM_OT"))
    try:
        KIT._resolve_bpy_op("no.such.op")
        check("D3c.unknown_op_raises", False, "no AttributeError")
    except AttributeError:
        check("D3c.unknown_op_raises", True)
    # THE D3 discriminator: kwargs that only the glTF op's RNA declares
    # SURVIVE when op_id names the glTF op (pre-fix the RNA probe was
    # hardcoded to usd_export and silently dropped them).
    gltf_props = set(
        bpy.ops.export_scene.gltf.get_rna_type().properties.keys())
    usd_props = set(
        bpy.ops.wm.usd_export.get_rna_type().properties.keys())
    gltf_only = sorted(gltf_props - usd_props - {"filepath"})
    probe = {k: True for k in gltf_only[:4]}
    probe["definitely_not_an_rna_kwarg_0987"] = 1
    filt = KIT.filter_rna_kwargs("export_scene.gltf", dict(probe),
                                 tag="s18d")
    kept = [k for k in gltf_only[:4] if k in filt]
    check("D3d.gltf_only_kwargs_survive",
          bool(gltf_only) and len(kept) == min(4, len(gltf_only)),
          f"gltf_only={gltf_only[:6]} kept={kept} "
          "(empty kept == op_id still decorative)")
    check("D3e.foreign_kwarg_dropped",
          "definitely_not_an_rna_kwarg_0987" not in filt,
          f"filt keys sample={sorted(filt)[:6]}")
    filt2 = KIT.filter_rna_kwargs("usd_export", {"filepath": "/tmp/x.usd"},
                                  tag="s18d")
    check("D3f.legacy_alias_still_filters", "filepath" in filt2)
else:
    kit_src = _src("scripts/blender_kit/__init__.py")
    check("D3 (source) resolve_uses_op_id",
          "def _resolve_bpy_op(op_id" in kit_src
          and "_RNA_OP_ALIASES.get(op_id, op_id)" in kit_src,
          "bpy unavailable — source fallback")
    check("D3 (source) filter_resolves_named_op",
          "_resolve_bpy_op(op_id).get_rna_type()" in kit_src,
          "bpy unavailable — source fallback")
    skip("D3d.gltf_only_kwargs_survive",
         "bpy unavailable — source fallbacks above")

# ===========================================================================
# D4 — USD parity counts (bpy-guarded)
# ===========================================================================
if EPP is not None:
    story = {"dialog": [{"clip": "a", "onset_frame": 1},
                        {"clip": "b", "onset_frame": 10}]}
    mism = EPP._parity_count_mismatches(story, [], {"dialog": 3})
    check("D4a.row_count_divergence_caught",
          len(mism) == 1 and "dialog" in mism[0] and "3" in mism[0],
          str(mism)[:140])
    check("D4b.matching_counts_clean",
          EPP._parity_count_mismatches(story, [], {"dialog": 2}) == [])
    # alias lane: USD "cameras" rows compare against story["cam_specs"]
    story2 = {"cam_specs": [{}, {}, {}]}
    mism_a = EPP._parity_count_mismatches(story2, [], {"cameras": 5})
    check("D4c.alias_lane_compared",
          len(mism_a) == 1 and "cameras" in mism_a[0], str(mism_a)[:140])
    check("D4d.scalar_divergence_caught",
          len(EPP._parity_scalar_mismatches(
              24, 1, 100, {"fps": 30, "frame_range": [1, 50]})) == 2,
          "fps + frame_range divergences must both be named")
    check("D4e.scalar_clean_when_matching",
          EPP._parity_scalar_mismatches(24, 1, 100, {"fps": 24}) == [])
else:
    check("D4 (source) count_parity_fn",
          "def _parity_count_mismatches" in epp_src
          and "_PARITY_COUNT_ALIASES" in epp_src,
          "bpy unavailable — source fallback")
    check("D4 (source) scalar_parity_fn",
          "def _parity_scalar_mismatches" in epp_src,
          "bpy unavailable — source fallback")
    skip("D4a.row_count_divergence_caught",
         "bpy unavailable — source fallbacks above")

# ===========================================================================
# D5 — gate-5 CAST-root cross-check (bpy-guarded; pure decision fn)
# ===========================================================================
if EPP is not None:
    stub = types.ModuleType("stub_scene")
    stub.CAST = {"Villain": {"root": "Villain.Root"}}
    chars_none = [{"name": "Villain", "root_object": None}]
    check("D5a.declared_root_resolves",
          EPP._gate5_root_problems(chars_none, stub, {"Villain.Root"}) == [],
          "a CAST-declared root that IS in the scene is collector drift, "
          "not a missing actor")
    probs = EPP._gate5_root_problems(chars_none, stub, set())
    check("D5b.unresolved_root_rejected",
          len(probs) == 1 and "Villain" in probs[0]
          and "Villain.Root" in probs[0],
          str(probs)[:160])
    plain = types.ModuleType("plain_scene")   # no CAST registry
    check("D5c.no_cast_lane_forgiving",
          EPP._gate5_root_problems(chars_none, plain, set()) == [],
          "template/fixture family without CAST must stay green")
    chars_ok = [{"name": "Hero", "root_object": "Hero.Root"}]
    check("D5d.present_collected_root_ok",
          EPP._gate5_root_problems(chars_ok, stub, {"Hero.Root"}) == [])
    probs3 = EPP._gate5_root_problems(chars_ok, stub, set())
    check("D5e.absent_collected_root_named",
          len(probs3) == 1 and "Hero.Root" in probs3[0]
          and "not in scene" in probs3[0], str(probs3)[:160])
else:
    check("D5 (source) cast_crosscheck_present",
          "_declared_cast_root" in epp_src
          and "root object unresolved" in epp_src,
          "bpy unavailable — source fallback")
    skip("D5b.unresolved_root_rejected",
         "bpy unavailable — source fallbacks above")

# ===========================================================================
# D8 — version-drift family matcher + --allow-stale (bpy-guarded)
# ===========================================================================
if EPP is not None:
    with tempfile.TemporaryDirectory() as td:
        def touch(name, t):
            p = os.path.join(td, name)
            with open(p, "w", encoding="utf-8") as f:
                f.write("# fixture\n")
            os.utime(p, (t, t))
        touch("scene_squall.py", 2_000_000_000)      # newest IN-family
        touch("scene_escape_v2.py", 1_000_000_000)   # older in-family
        touch("scene_template.py", 3_000_000_000)    # excluded (template)
        touch("scene_cli_demo.py", 3_000_000_000)    # excluded (demo)
        touch("_fixture.py", 3_000_000_000)          # never matches scene_* glob
        touch("scene_t10_fixture.py", 3_000_000_000) # excluded ('fixture' convention)
        latest = EPP._latest_scene_module(td)
        check("D8a.latest_film_module_chosen", latest == "scene_squall",
              f"latest={latest} (excluded files must never win)")
        cands = EPP._scene_module_candidates(td)
        check("D8b.exclusions_honored",
              set(cands) == {"scene_squall", "scene_escape_v2"},
              f"cands={sorted(cands)}")
        check("D8c.no_candidates_returns_none",
              EPP._latest_scene_module(os.path.join(td, "nope")) is None)
    main_src_epp = inspect.getsource(EPP.main)
    check("D8 (source) allow_stale_flag",
          '"--allow-stale"' in main_src_epp
          and "args.allow_stale" in main_src_epp,
          "the escape hatch must exist on the exporter's parser")
    check("D8 (source) stale_gate_uses_family_scan",
          "_latest_scene_module(scripts_dir)" in main_src_epp
          and "candidates[args.scene] < candidates[latest]" in main_src_epp,
          "the gate must compare the named module's mtime against the "
          "family scan, not the vacuous escape_v* regex")
else:
    check("D8 (source) allow_stale_flag",
          '"--allow-stale"' in epp_src, "bpy unavailable — source fallback")
    check("D8 (source) family_scan_present",
          "def _latest_scene_module" in epp_src
          and "_STALENESS_EXCLUDE" in epp_src,
          "bpy unavailable — source fallback")
    skip("D8a.latest_film_module_chosen",
         "bpy unavailable — source fallbacks above")

# ===========================================================================
# D12 — _write_metadata writes scene.json (bpy-guarded; cheap live call)
# ===========================================================================
if KIT is not None:
    import argparse as _ap
    with tempfile.TemporaryDirectory() as td2:
        args = _ap.Namespace(output=td2, engine="BLENDER_WORKBENCH",
                             w=64, h=64, samples=1, frames=None, start=1,
                             still=None, quality="draft")
        KIT._write_metadata(args, scene_name="s18d_probe", elapsed=0.01,
                            scene=bpy.context.scene)
        check("D12a.metadata_written",
              os.path.isfile(os.path.join(td2, "metadata.json")))
        with open(os.path.join(td2, "scene.json"), encoding="utf-8") as f:
            doc = json.load(f)
        check("D12b.scene_json_written",
              isinstance(doc, dict)
              and doc.get("scene_name") == "s18d_probe",
              f"scene.json keys={sorted(doc)[:8]}")
        check("D12c.scene_json_consumer_fields",
              "objects" in doc and "frame_range" in doc and "fps" in doc,
              "the Scene-tab consumer needs objects/frame_range/fps")
else:
    kit_src = _src("scripts/blender_kit/__init__.py")
    check("D12 (source) scene_json_write_present",
          '"scene.json"' in kit_src
          and "metadata.json + scene.json written" in kit_src,
          "bpy unavailable — source fallback")
    skip("D12b.scene_json_written", "bpy unavailable — source fallbacks above")

# ===========================================================================
print("=" * 60)
_summary = (f"test_s18_wave_d: {len(PASS)}/{len(PASS) + len(FAIL)} checks "
            f"passed (bpy={'yes' if HAVE_BPY else 'no'}")
if SKIPPED:
    _summary += f", {len(SKIPPED)} textual-only fallbacks"
print(_summary + ")")
if FAIL:
    print(f"[S18D] FAILED: {FAIL}")
    sys.exit(1)
print(f"[S18D] ALL PASS ({len(PASS)} checks)")
sys.exit(0)
