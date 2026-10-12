"""test_v8_material.py — V8 regression (vision-kit twin of agent-kit T7): make_material emission contract
(F-TD11, D-TD21 REV-2).

Locks the glow-surface law (measured on Blender 5.2 + AgX, tdawn_1/2):
  - Principled 'Emission Color' DEFAULTS TO WHITE in 4.x/5.x; the helper
    must PIN it to the base color by default, so a caller-raised
    Emission Strength inherits the material hue instead of paper-white
  - explicit emission_color DECOUPLES (dark base + warm emission)
    while workbench diffuse_color STAYS the base color
  - emission_strength is a DIRECT write — a missing input RAISES
    (never the kit's silent-no-op class)
  - _safe_socket_set: guarded-write contract (True on set, False on
    missing socket) — the only place a KeyError may be swallowed

Runs INSIDE Blender via run.sh (T6 harness style: factory settings,
check()/FAIL, results JSON).
"""
import sys, os, json

_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS = os.path.abspath(os.path.join(_HERE, "..", "scripts"))
for _p in (_SCRIPTS,):
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

import bpy
import blender_kit as BK

_REPO_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
_OUT_ROOT = os.environ.get("KIT_OUT", os.path.join(_REPO_ROOT, "output", "tests"))
OUT = os.path.join(_OUT_ROOT, "v8_results.json")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
FAIL = []

BASE = (0.20, 0.55, 0.95)   # distinctly non-white: the 5.x default white
                            # Emission Color must not be able to fake-pass
WARM = (0.95, 0.45, 0.12)
EPS = 1e-6


def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def check(label, got, expect, tol=1e-6):
    ok = False
    if isinstance(expect, (int, float)) and isinstance(got, (int, float)):
        ok = abs(got - expect) <= tol
    elif isinstance(expect, (list, tuple)) and isinstance(got, (list, tuple)) \
            and len(expect) == len(got):
        ok = all(abs(g - e) <= tol for g, e in zip(got, expect)
                 if isinstance(g, (int, float)) and isinstance(e, (int, float))) \
            and all(g == e for g, e in zip(got, expect)
                    if not isinstance(g, (int, float)) or not isinstance(e, (int, float)))
    else:
        ok = got == expect
    if not ok:
        FAIL.append(label)
    print(f"[{'ok' if ok else 'FAIL'}] {label}: got={got} expect={expect}")
    return ok


clear()
mat = BK.make_material("V8_Pin", BASE)
bsdf = mat.node_tree.nodes.get("Principled BSDF")
check("T7a Principled node present", bsdf is not None, True)
check("T7a-pre 5.2.2 has Emission Color socket", "Emission Color" in bsdf.inputs, True)
check("T7a-pre 5.2.2 has Emission Strength socket", "Emission Strength" in bsdf.inputs, True)

pin = list(bsdf.inputs["Emission Color"].default_value)[:3]
check("T7b default pins Emission Color to base", [round(v, 5) for v in pin],
      [round(v, 5) for v in BASE], tol=EPS)
check("T7c Emission Strength untouched (0.0)",
      float(bsdf.inputs["Emission Strength"].default_value), 0.0, tol=EPS)
base_read = list(bsdf.inputs["Base Color"].default_value)[:3]
check("T7d Base Color equals argument", [round(v, 5) for v in base_read],
      [round(v, 5) for v in BASE], tol=EPS)
dc = list(mat.diffuse_color)[:3]
check("T7e workbench diffuse_color stays base", [round(v, 5) for v in dc],
      [round(v, 5) for v in BASE], tol=EPS)

clear()
mat2 = BK.make_material("V8_Decouple", BASE, emission_color=WARM)
bsdf2 = mat2.node_tree.nodes.get("Principled BSDF")
dec = list(bsdf2.inputs["Emission Color"].default_value)[:3]
check("T7f explicit emission_color honored", [round(v, 5) for v in dec],
      [round(v, 5) for v in WARM], tol=EPS)
dc2 = list(mat2.diffuse_color)[:3]
check("T7g diffuse_color STILL base when decoupled",
      [round(v, 5) for v in dc2], [round(v, 5) for v in BASE], tol=EPS)

clear()
mat3 = BK.make_material("V8_Glow", BASE, emission_color=WARM,
                        emission_strength=0.93)
bsdf3 = mat3.node_tree.nodes.get("Principled BSDF")
check("T7h emission_strength set",
      float(bsdf3.inputs["Emission Strength"].default_value), 0.93, tol=EPS)

clear()


class _FakeSocket:
    def __init__(self):
        self.default_value = None


class _FakeBsdf:
    def __init__(self, names):
        self.inputs = {n: _FakeSocket() for n in names}


fake_ok = _FakeBsdf(["Emission Color"])
check("T7i _safe_socket_set returns True on existing socket",
      BK._safe_socket_set(fake_ok, "Emission Color", 7), True)
check("T7i _safe_socket_set actually wrote",
      fake_ok.inputs["Emission Color"].default_value, 7)
fake_no = _FakeBsdf([])
check("T7j _safe_socket_set returns False on missing socket",
      BK._safe_socket_set(fake_no, "Emission Color", 7), False)

results = {"suite": "V8 make_material emission contract", "fail": FAIL,
           "n_cases": 10}
with open(OUT, "w") as f:
    json.dump(results, f, indent=2)
print(f"[V8] {'ALL PASS' if not FAIL else 'FAILURES: ' + str(FAIL)}")
print(f"[V8] wrote {OUT}")
if FAIL:
    raise SystemExit(1)
