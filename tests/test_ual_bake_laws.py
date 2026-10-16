# VENDORED 2026-10-16 from mainline blender-agent-kit @6943ab5 (vision-kit s21 vendor round; zero code drift; vision deltas must land as sanctioned deltas per docs/VENDOR_LEDGER.md)
#!/usr/bin/env python3
"""test_ual_bake_laws.py — the s31 hero-bake laws, tested bpy-free.

ual_bake.py imports bpy at module level, so this test AST-EXTRACTS the
pure law functions (the test_hero_gates.py model — no Blender needed)
and exercises them against duck-typed quaternion/vector shims:

  L1  ARC-SIGN LAW (_mix + arc_flip): the per-bone arc sign chosen ONCE
      at blend start and held -> the quaternion path through an
      antipode crossing is CONTINUOUS (max per-frame 4D delta small);
      the naive per-frame short-arc (no arc_flip) has a single-frame
      ~2x flip at the crossing.
  L2  THE negate() HOLE: mathutils Quaternion.negate() mutates IN
      PLACE and returns None. The law's code shape (copy-then-negate,
      never assigning the return) must survive a shim that reproduces
      the mathutils behavior; the naive `q = q.copy().negate()` shape
      assigns None (demonstrated — that hole shipped two s31 export
      cycles bit-identical through an except-fallback).
  L3  SIGN CANONICALIZATION (_canonicalize_quats): adjacent keys with
      dot < 0 are negated -> every adjacent pair ends dot >= 0.
  L4  FROZEN-SOURCE LAW (the resolver): during a blend window the
      outgoing beat's source frame is HELD at prev.src_at(beat.f0)
      (constant across the window), t reaches 1.0 at the LAST blend
      frame, and ease=True applies smoothstep (zero blend-rate at both
      ends).

The extraction targets live in the KIT's copy of ual_bake.py — the
same laws exist in previz's copy (owner: previz; the sync keeps them
byte-identical — see tools/shared_manifest.json).

Run: python3 tests/test_ual_bake_laws.py     Exit: 0 PASS / 1 FAIL
"""
import ast
import math
import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.abspath(os.path.join(HERE, ".."))
UAL = os.path.join(KIT, "scripts", "ual_bake.py")

FAILURES = []


def check(label, ok, detail=""):
    tag = "PASS" if ok else "FAIL"
    print(f"[{tag}] {label}" + (f" — {detail}" if detail else ""))
    if not ok:
        FAILURES.append(label)


# ---------------------------------------------------------------------------
# duck-typed mathutils shims
# ---------------------------------------------------------------------------

class V:
    """Vector shim: lerp is all the law code uses."""
    def __init__(self, xyz):
        self.v = tuple(float(x) for x in xyz)

    def lerp(self, other, t):
        return V((a + (b - a) * t for a, b in zip(self.v, other.v)))

    def copy(self):
        return V(self.v)

    def __eq__(self, other):
        return isinstance(other, V) and self.v == other.v


class Q:
    """Quaternion shim reproducing the mathutils semantics that matter:

    - negate() mutates IN PLACE and returns None (the s31 hole)
    - dot() is the 4D dot
    - slerp(qb, t): the componentwise-NLERP approximation — it models
      the SIGN behavior exactly (interpolating to qb vs -qb takes
      opposite paths through 4D, same endpoints), which is what the
      arc-sign law is about; rotational accuracy is irrelevant here.
    """
    def __init__(self, wxyz):
        self.q = tuple(float(x) for x in wxyz)

    def copy(self):
        return Q(self.q)

    def negate(self):
        """mathutils LAW: mutates in place, returns None."""
        self.q = tuple(-x for x in self.q)
        return None

    def dot(self, other):
        return sum(a * b for a, b in zip(self.q, other.q))

    def slerp(self, other, t):
        a, b = self.q, other.q
        out = tuple(a[i] + (b[i] - a[i]) * t for i in range(4))
        n = math.sqrt(sum(x * x for x in out)) or 1.0
        return Q(tuple(x / n for x in out))

    def delta4(self, other):
        return max(abs(a - b) for a, b in zip(self.q, other.q))


def qn(w, x, y, z):
    q = Q((w, x, y, z))
    n = math.sqrt(sum(c * c for c in q.q)) or 1.0
    return Q(tuple(c / n for c in q.q))


# ---------------------------------------------------------------------------
# AST extraction of the law code
# ---------------------------------------------------------------------------

def extract(src_path, names, constants=("BLEND_DEFAULT",)):
    """Extract top-level functions/classes by name into a namespace with
    the shims pre-injected (bpy/mathutils symbols the module header
    would otherwise provide). Module-level constants used by the
    extracted defs (e.g. BLEND_DEFAULT in Beat's signature) are
    carried over verbatim."""
    tree = ast.parse(open(src_path).read())
    wanted = set(names)
    picked = [n for n in tree.body
              if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in wanted]
    found = {n.name for n in picked}
    missing = wanted - found
    if missing:
        raise SystemExit(f"[extract] missing in {src_path}: {sorted(missing)}")
    consts = [n for n in tree.body
              if (isinstance(n, ast.Assign) and len(n.targets) == 1
                  and isinstance(n.targets[0], ast.Name)
                  and n.targets[0].id in constants)]
    # constants FIRST (defs may use them in default args / class bodies)
    picked = consts + picked
    mod = types.ModuleType("ual_bake_laws")
    mod.__dict__.update({
        "bpy": None, "gc": None,  # the module header imports these
        "Quaternion": Q, "Vector": V, "math": math,
    })
    exec(compile(ast.Module(body=picked, type_ignores=[]), src_path, "exec"),
         mod.__dict__)
    return mod


def main():
    laws = extract(UAL, ["_mix", "_canonicalize_quats", "Beat", "_make_resolver"])

    # ---- L1: arc-sign law -----------------------------------------------
    # bone "arm": the moving pose sweeps PAST table_b's ANTIPODE
    # (qa rotates 0 -> 190 deg while qb sits at 0 deg: dot(qa,qb) =
    # cos(da/2) goes negative once da passes 180 — the crossing).
    # The naive per-frame short-arc flips sides exactly there.
    n = 20
    table_b = {"arm": (V((0, 0, 0)), qn(1, 0, 0, 0))}   # angle 0
    def pose(f):
        ang = math.radians(f * 10.0)  # 0 -> 190 deg over the window
        return V((0, 0, 0)), qn(math.cos(ang / 2), math.sin(ang / 2), 0, 0)

    naive_path, law_path = [], []
    law_flip = None
    for f in range(n):
        ta = {"arm": pose(f)}
        # the law: arc sign chosen at the FIRST blend frame, held
        if f == 0:
            qa = ta["arm"][1]
            qb = table_b["arm"][1]
            law_flip = {"arm": qa.dot(qb) < 0.0}
        law_path.append(laws._mix(ta, table_b, (f + 1) / n, arc_flip=law_flip)["arm"][1])
        # the naive PRE-s31 heuristic: the short-arc decision recomputed
        # PER FRAME — when qa sweeps through qb's antipode the decision
        # flips sides and the target jumps qb -> -qb (the 177-deg class)
        naive_flip = {"arm": ta["arm"][1].dot(table_b["arm"][1]) < 0.0}
        naive_path.append(laws._mix(ta, table_b, (f + 1) / n, arc_flip=naive_flip)["arm"][1])

    def max_step(path):
        return max(path[i].delta4(path[i + 1]) for i in range(len(path) - 1))
    naive_step, law_step = max_step(naive_path), max_step(law_path)
    check("L1a arc-sign law: held-sign path is continuous",
          law_step < 0.12, f"max step {law_step:.4f}")
    check("L1b naive short-arc flips at the antipode crossing",
          naive_step > 2 * law_step,
          f"naive max step {naive_step:.4f} vs law {law_step:.4f}")

    # ---- L2: the negate() hole -------------------------------------------
    q = qn(0.9, 0.1, 0.1, 0.1)
    qb = q.copy()
    qb.negate()                    # the LAW's shape: copy, then negate
    check("L2a law shape survives negate()-returns-None", qb.q[0] < 0)
    naive = q.copy().negate()      # the HOLE's shape
    check("L2b the naive shape assigns None (the demonstrated hole)",
          naive is None)

    # ---- L3: sign canonicalization ----------------------------------------
    rows = {
        1:  {"arm": (V((0, 0, 0)), qn(0.9, 0.1, 0.1, 0.1))},
        2:  {"arm": (V((0, 0, 0)), qn(-0.9, -0.1, -0.1, -0.1))},  # dot < 0
        3:  {"arm": (V((0, 0, 0)), qn(0.8, 0.2, 0.2, 0.2))},
    }
    laws._canonicalize_quats(rows)
    dots = [rows[1]["arm"][1].dot(rows[2]["arm"][1]),
            rows[2]["arm"][1].dot(rows[3]["arm"][1])]
    check("L3 _canonicalize_quats: adjacent dots all >= 0",
          all(d >= 0 for d in dots), f"dots {[round(d, 3) for d in dots]}")

    # ---- L4: the frozen-source resolver -----------------------------------
    class Act:  # minimal action stand-in (identity is all we need)
        def __init__(self, name):
            self.name = name

        def __eq__(self, other):
            return isinstance(other, Act) and other.name == self.name

    B = laws.Beat
    beats = [
        B(f0=1, f1=137, action=Act("sprint"), mode="loop", param=16.0, phase=0.0),
        B(f0=137, f1=541, action=Act("aim"), mode="hold", param=0, phase=0.0,
          blend=20, ease=True),
    ]
    resolve = laws._make_resolver(beats, "test")
    window = [resolve(f) for f in range(137, 157)]
    srcs = {w[0][1] for w in window}  # the outgoing (frozen) src frames
    # prev.src_at(beat.f0) = (0 + (137-1)) % 16 = 8 — a SINGLE value held
    # across the whole window is the law (the live source would vary per f)
    check("L4a frozen-source: the outgoing src frame is HELD at "
          "prev.src_at(beat.f0) across the window",
          srcs == {8.0}, f"srcs {sorted(srcs)}")
    last_t = window[-1][1][2]
    check("L4b t reaches 1.0 at the LAST blend frame",
          abs(last_t - 1.0) < 1e-9, f"t={last_t}")
    # smoothstep: zero blend-rate at both ends — t(1) and t(19) barely move
    t0 = window[0][1][2]
    t1 = window[1][1][2]
    t18 = window[18][1][2]
    t19 = window[19][1][2]
    edge_rate = max(t1 - t0, t19 - t18)
    mid_rate = window[10][1][2] - window[9][1][2]
    check("L4c ease=True applies smoothstep (edge rate << mid rate)",
          edge_rate < 0.25 * mid_rate,
          f"edge {edge_rate:.4f} vs mid {mid_rate:.4f}")

    print()
    if FAILURES:
        print(f"RESULT: {len(FAILURES)} FAILURE(S): {FAILURES}")
        return 1
    print("RESULT: ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
